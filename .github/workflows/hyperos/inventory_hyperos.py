#!/usr/bin/env python3
"""Read-only complete APK inventory of stock HyperOS yunluo super.img."""
import csv
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent))
from preflight import ROM, digest, parse_sparse_header

WORK = Path(os.environ["HYPEROS_WORK"])
OUT = Path(os.environ["HYPEROS_REPORT"])
TOOLS = Path(os.environ["HYPEROS_TOOLS"])

def command(*args):
    p=subprocess.run([str(a) for a in args],capture_output=True,text=True)
    if p.returncode: raise RuntimeError("Command failed: "+" ".join(map(str,args))+"\n"+p.stderr[-2000:])
    return p.stdout

def partitions(dump,slot):
    if "Partition table:" not in dump or "Block device table:" not in dump:
        raise RuntimeError("Unknown LP metadata layout in slot "+str(slot))
    table=dump.split("Partition table:",1)[1].split("Block device table:",1)[0]
    result=[]
    for block in table.split("------------------------"):
        name=re.search(r"(?m)^\s*Name:\s*([A-Za-z0-9_.-]+)\s*$",block)
        if name and re.search(r"(?m)^\s*\d+\s*\.\.\s*\d+\s+(linear|zero)\b",block):
            result.append((slot,name.group(1)))
    return result

def file_system(path):
    with path.open("rb") as f: h=f.read(1100)
    if h[1024:1028]==bytes.fromhex("e2e1f5e0"):return "erofs"
    if h[1080:1082]==bytes.fromhex("53ef"):return "ext4"
    return "unknown"

def find_aapt():
    home=Path(os.environ.get("ANDROID_HOME","/usr/local/lib/android/sdk"))
    matches=list((home/"build-tools").glob("*/aapt2"))
    matches+=list((home/"build-tools").glob("*/aapt"))
    for path in sorted(matches,reverse=True):
        if path.is_file() and os.access(path,os.X_OK):return str(path)
    return shutil.which("aapt2") or shutil.which("aapt")

def package_id(aapt,apk):
    if not aapt:return ""
    try:
        p=subprocess.run([aapt,"dump","badging",str(apk)],capture_output=True,text=True,timeout=15)
        m=re.search(r"(?m)^package:\s+name='([^']+)'",p.stdout) if p.returncode==0 else None
        return m.group(1) if m else ""
    except (OSError,subprocess.TimeoutExpired):
        return ""

def scan(raw,slot,part,aapt):
    unpack=WORK/"unpacked"
    unpack.mkdir(exist_ok=True)
    image=unpack/(part+".img")
    rows=[]
    try:
        command(TOOLS/"lpunpack","--slot="+str(slot),"--partition="+part,raw,unpack)
        if not image.is_file():raise RuntimeError("No image extracted for "+part)
        fstype=file_system(image)
        if fstype not in ("erofs","ext4"):raise RuntimeError("Unsupported "+part+" filesystem "+fstype)
        mount=WORK/"mounted"
        mount.mkdir(exist_ok=True)
        opts="ro,loop" if fstype=="erofs" else "ro,loop,noload"
        command("mount","-t",fstype,"-o",opts,image,mount)
        try:
            for base,dirs,files in os.walk(mount,followlinks=False):
                dirs.sort()
                for filename in sorted(files):
                    if not filename.lower().endswith(".apk"):continue
                    path=Path(base)/filename
                    st=path.lstat()
                    if not stat.S_ISREG(st.st_mode):continue
                    rel="/"+path.relative_to(mount).as_posix()
                    label=""
                    try:label=os.getxattr(path,"security.selinux",follow_symlinks=False).decode("utf8","replace").rstrip("\0")
                    except OSError:pass
                    rows.append({
                        "partition":part,"slot":slot,"filesystem":fstype,
                        "apk_filename":filename,"partition_path":rel,
                        "full_location":part+":"+rel,
                        "device_destination":"/"+part.rsplit("_",1)[0]+rel,
                        "package_id":package_id(aapt,path),"bytes":st.st_size,
                        "selinux_context":label
                    })
        finally:
            command("umount",mount)
        return rows,{"partition":part,"slot":slot,"filesystem":fstype,"apk_count":len(rows),"image_bytes":image.stat().st_size}
    finally:
        shutil.rmtree(unpack,ignore_errors=True)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sparse=WORK/"images/super.img"
    vbmeta=WORK/"images/vbmeta.img"
    raw=WORK/"super.raw.img"
    if not (OUT/"01-source.json").is_file() or not sparse.is_file() or not vbmeta.is_file():
        raise RuntimeError("Verified HyperOS stock image extraction is missing")
    if raw.exists():raise RuntimeError("Unexpected existing raw super")
    with sparse.open("rb") as f:info=parse_sparse_header(f.read(28))
    command(TOOLS/"simg2img",sparse,raw)
    if raw.stat().st_size!=info["raw_size"]:raise RuntimeError("Bad raw super size")
    sparse.unlink()
    all_partitions=[];done=set()
    for slot in (0,1):
        dump=command(TOOLS/"lpdump","-s",slot,raw)
        (OUT/("LP_SLOT_"+str(slot)+".txt")).write_text(dump)
        for pair in partitions(dump,slot):
            if pair[1] not in done:
                done.add(pair[1]);all_partitions.append(pair)
    if not all_partitions:raise RuntimeError("No populated logical partitions")
    aapt=find_aapt()
    rows=[];summary=[]
    for slot,name in all_partitions:
        print("Inspecting",name,flush=True)
        records,detail=scan(raw,slot,name,aapt)
        rows.extend(records);summary.append(detail)
        print("APK files:",name,len(records),flush=True)
    rows.sort(key=lambda x:(x["partition"],x["partition_path"]))
    if not rows:raise RuntimeError("Inventory unexpectedly empty")
    fields=["partition","slot","filesystem","apk_filename","partition_path","full_location","device_destination","package_id","bytes","selinux_context"]
    for filename,delimiter in (("APKS_ALL.tsv","\t"),("APKS_ALL.csv",",")):
        with (OUT/filename).open("w",encoding="utf8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter=delimiter)
            w.writeheader();w.writerows(rows)
    (OUT/"APKS_ALL.txt").write_text("\n".join(r["full_location"] for r in rows)+"\n")
    report={
       "device":"Redmi Pad (yunluo)","firmware":ROM["os_version"],"android":ROM["android"],
       "total_apk_files":len(rows),"partition_counts":summary,
       "package_id_resolved":sum(bool(r["package_id"]) for r in rows),
       "stock_super_raw_sha256":digest(raw),"stock_vbmeta_sha256":digest(vbmeta),
       "modified_images":0,"firmware_zip_created":False
    }
    (OUT/"SUMMARY.json").write_text(json.dumps(report,indent=2)+"\n")
    md=["# Complete HyperOS 1 stock APK inventory","",
        "Device: Redmi Pad (yunluo); source: "+ROM["os_version"]+" Android 14.",
        "","**Total APK files: "+str(len(rows))+"**","","| Logical partition | APK files |",
        "|---|---:|"]
    md += ["| "+r["partition"]+" | "+str(r["apk_count"])+" |" for r in summary]
    md += ["","Full names and destinations: [APKS_ALL.tsv](APKS_ALL.tsv), [APKS_ALL.csv](APKS_ALL.csv), or [APKS_ALL.txt](APKS_ALL.txt).",
           "The destination field is derived from the source logical-partition mount path.",
           "This was a read-only stock scan, not a modified image or full firmware ZIP."]
    (OUT/"SUMMARY.md").write_text("\n".join(md)+"\n")
    raw.unlink()
    print("HYPEROS_TOTAL_APK_FILES",len(rows),flush=True)

if __name__=="__main__":
    main()
