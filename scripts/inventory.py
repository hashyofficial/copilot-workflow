#!/usr/bin/env python3
"""Read-only Xiaomi fastboot archive and dynamic-partition APK inventory."""
import hashlib, json, os, pathlib, re, shutil, stat, subprocess, tarfile, urllib.request

ROOT=pathlib.Path(os.environ.get("GITHUB_WORKSPACE",pathlib.Path(__file__).resolve().parents[1]))
OUT=ROOT/"reports"; TMP=pathlib.Path("/tmp/yunluo-inventory"); TOOLS=ROOT/".tools/android-tools-static"
VER="V14.0.4.0.TLYMIXM"
NAME="yunluo_global_images_V14.0.4.0.TLYMIXM_20231207.0000.00_13.0_global_4003dcb1a4.tgz"
URL=f"https://bigota.d.miui.com/{VER}/{NAME}"
MD5="4003dcb1a4db404e2768801fdb429c4a"

def write(name,text):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(text,encoding="utf8")

def sha(path,algorithm="sha256"):
    h=hashlib.new(algorithm)
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
    return h.hexdigest()

def command(*args):
    return subprocess.run([str(x) for x in args],capture_output=True,text=True,check=False)

def install():
    TOOLS.parent.mkdir(parents=True,exist_ok=True)
    api="https://api.github.com/repos/meator/android-tools-static/releases/tags/36.0.1"
    req=urllib.request.Request(api,headers={"User-Agent":"yunluo-inventory","Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=60) as r:release=json.load(r)
    assets=[x for x in release["assets"] if re.search(r"linux-standardlayout-extra-x86_64\\.tar\\.gz$",x["name"])]
    if len(assets)!=1:raise RuntimeError("No unique pinned Linux tools asset: "+str([x["name"] for x in release["assets"]]))
    asset=assets[0];digest=asset.get("digest") or ""
    if not digest.startswith("sha256:"):raise RuntimeError("Release asset lacks verifiable SHA256")
    tarpath=TOOLS.parent/asset["name"]
    urllib.request.urlretrieve(asset["browser_download_url"],tarpath)
    got=sha(tarpath)
    if got!=digest.split(":",1)[1]:raise RuntimeError("Tools SHA256 mismatch")
    with tarfile.open(tarpath) as tf:
        for m in tf:
            p=pathlib.PurePosixPath(m.name)
            if m.issym() or m.islnk() or p.is_absolute() or ".." in p.parts:raise RuntimeError("Unsafe tools archive")
        tf.extractall(TOOLS.parent,filter="data")
    tarpath.unlink()
    for tool in ("simg2img","lpunpack","lpdump","lpmake","img2simg"):
        if not (TOOLS/tool).is_file():raise RuntimeError("Missing "+tool)
    write("tools.txt",f"{api}\n{asset['name']}\nSHA256: {got}\n")

def archive_inspect(archive):
    entries=["path\ttype\tbytes"];clues=[];superfile=None
    with tarfile.open(archive,"r:gz") as tf:
        for m in tf:
            p=pathlib.PurePosixPath(m.name)
            if p.is_absolute() or ".." in p.parts or m.issym() or m.islnk() or m.isdev():raise RuntimeError("Unsafe vendor archive path "+m.name)
            entries.append(f"{m.name}\t{'file' if m.isfile() else 'other'}\t{m.size}")
            if not m.isfile():continue
            base=p.name.lower()
            if base=="super.img":
                if superfile is not None:raise RuntimeError("Multiple super.img files")
                superfile=TMP/"super.img"
                with tf.extractfile(m) as inp,open(superfile,"wb") as dest:shutil.copyfileobj(inp,dest,8*1024*1024)
            elif m.size<2_000_000 and base.endswith((".sh",".bat",".xml",".txt",".cfg",".ini",".json",".cmd")):
                clues.append(f"===== {m.name} =====\n"+tf.extractfile(m).read().decode("utf8","replace")[:120000])
    write("archive-members.tsv","\n".join(entries)+"\n")
    write("flashing-clues.txt","\n".join(clues)+"\n")
    if not superfile:raise RuntimeError("No super.img in archive")
    return superfile

def fstype(p):
    with open(p,"rb") as f:header=f.read(1100)
    if header[1024:1028]==bytes.fromhex("e2e1f5e0"):return "erofs"
    if header[1080:1082]==bytes.fromhex("53ef"):return "ext4"
    r=command("blkid","-p","-o","value","-s","TYPE",p)
    return r.stdout.strip() or "unknown"

def scan_mount(mount,part,paths,details):
    for directory,_,files in os.walk(mount,followlinks=False):
        for name in files:
            if not name.lower().endswith(".apk"):continue
            p=pathlib.Path(directory)/name;st=p.lstat()
            if not stat.S_ISREG(st.st_mode):continue
            rel="/"+str(p.relative_to(mount))
            try:ctx=os.getxattr(p,"security.selinux",follow_symlinks=False).decode("utf8","replace").strip("\0")
            except OSError:ctx="xattr-unavailable-or-policy-derived"
            paths.add(f"{part}:{rel}")
            details.append(f"{part}\t{rel}\t{st.st_uid}\t{st.st_gid}\t{oct(stat.S_IMODE(st.st_mode))}\t{st.st_size}\t{ctx}")

def inspect():
    OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
    archive=TMP/NAME
    apks=set();rows=["partition\tpath\tuid\tgid\tmode\tbytes\tselinux_xattr"]
    fss=["partition\tfilesystem\timage_bytes\tmetadata_slot"];errors=[]
    try:
        subprocess.run(["curl","-fL","--retry","4","--retry-delay","10","--connect-timeout","30","-o",str(archive),URL],check=True)
        md5=sha(archive,"md5")
        write("checksums.txt",f"URL: {URL}\nExpected MD5: {MD5}\nActual MD5: {md5}\n")
        if md5!=MD5:raise RuntimeError("Firmware MD5 mismatch")
        superfile=archive_inspect(archive)
        archive.unlink()
        with open(superfile,"rb") as f:sparse=f.read(4)==bytes.fromhex("3aff26ed")
        if sparse:
            raw=TMP/"super.raw.img"
            r=command(TOOLS/"simg2img",superfile,raw)
            if r.returncode:raise RuntimeError("simg2img failed: "+r.stderr)
            superfile.unlink();superfile=raw
        write("super-source.txt",f"Sparse source: {sparse}\nRaw size bytes: {superfile.stat().st_size}\nSHA256: {sha(superfile)}\n")
        parts=[]
        for slot in (0,1):
            r=command(TOOLS/"lpdump","-s",slot,superfile)
            write(f"lpdump-slot{slot}.txt",r.stdout+"\nSTDERR:\n"+r.stderr+f"\nExit: {r.returncode}\n")
            if r.returncode==0:
                for n in dict.fromkeys(re.findall(r"^\\s*Name:\\s*([A-Za-z0-9_.-]+)\\s*$",r.stdout,re.M)):
                    parts.append((slot,n))
        if not parts:raise RuntimeError("lpdump did not report logical partitions")
        for slot,part in parts:
            out=TMP/"unpacked";out.mkdir(exist_ok=True)
            try:
                r=command(TOOLS/"lpunpack","-S",slot,"-p",part,superfile,out)
                if r.returncode:raise RuntimeError("lpunpack: "+r.stderr)
                image=out/(part+".img")
                if not image.is_file():raise RuntimeError("lpunpack did not create "+str(image))
                fs=fstype(image);fss.append(f"{part}\t{fs}\t{image.stat().st_size}\t{slot}")
                if fs not in ("ext4","erofs"):raise RuntimeError("Unsupported filesystem: "+fs)
                mnt=TMP/"mount";mnt.mkdir(exist_ok=True)
                opts="ro,loop,noload" if fs=="ext4" else "ro,loop"
                r=command("mount","-t",fs,"-o",opts,image,mnt)
                if r.returncode:raise RuntimeError("Read-only mount failed: "+r.stderr)
                try:scan_mount(mnt,part,apks,rows)
                finally:subprocess.run(["umount",str(mnt)],check=True)
            except Exception as ex:
                errors.append(f"slot{slot} {part}: {ex}")
            finally:shutil.rmtree(out,ignore_errors=True)
        write("apks.txt","\n".join(sorted(apks))+"\n")
        write("apks-detailed.tsv","\n".join(rows)+"\n")
        write("filesystems.tsv","\n".join(fss)+"\n")
        write("warnings.txt","\n".join(errors)+"\n" if errors else "No inventory warnings.\n")
        if errors:raise RuntimeError("Incomplete inventory: see warnings.txt")
    finally:
        if archive.exists():archive.unlink()
        write("status.txt","Inventory attempted. See Actions logs for completion status.\n")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--install-tools",action="store_true");g.add_argument("--inspect",action="store_true")
    a=p.parse_args()
    install() if a.install_tools else inspect()
