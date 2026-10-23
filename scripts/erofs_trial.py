#!/usr/bin/env python3
"""Non-flashable EROFS trial: omit 24 reviewed app *directories* and verify.

Source super/vbmeta images are only read. No super.img, vbmeta image,
fastboot command, or rebuilt filesystem bytes are uploaded. The output
is a report of a disposable local reconstruction, never flash approval.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import traceback

from inventory import ROOT, TOOLS, NAME, MD5, VER, sha, command, fstype
from combined_preflight import extract_archive, parse_partitions, avb_checks, SUPER_RAW_SIZE, apk_identity, find_aapt

REPORT = ROOT / "reports-trial"
TRIAL_FILE = ROOT / "config/optional-trial-24.txt"
SOURCE_FILE = ROOT / "config/first-pass-33.txt"
ALLOWED_PARTITIONS = {"product_a", "system_a"}
EXPECTED_PARTITION_COUNTS = {"product_a": 18, "system_a": 6}
SOURCE_SUPER_SHA256 = "2c61eddca409fdb6dca1cb448f991d6bc911355a5f247c742f3fae0fdacce6ef"
REQUIRED_TIME = 1230768000
REPORT.mkdir(parents=True, exist_ok=True)

def output(name, data):
    (REPORT/name).write_text(data, encoding="utf-8")

def run_checked(*argv):
    p = command(*argv)
    if p.returncode:
        raise RuntimeError(str(argv[0])+" failed: "+(p.stderr or p.stdout)[-1500:])
    return p

def load_list(file):
    entries={}
    for raw in file.read_text(encoding="utf-8").splitlines():
        line=raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError("Unqualified APK target: "+line)
        part,path=line.split(":",1)
        posix=PurePosixPath(path)
        if not posix.is_absolute() or ".." in posix.parts or posix.suffix.lower()!=".apk":
            raise ValueError("Unsafe/non-APK target: "+line)
        if len(posix.parts)<4:
            raise ValueError("Too-broad path: "+line)
        if line in entries:
            raise ValueError("Duplicate target: "+line)
        entries[line]=(part,posix)
    return entries

def proposed():
    trial=load_list(TRIAL_FILE)
    full=load_list(SOURCE_FILE)
    if len(trial)!=24 or len(full)!=33:
        raise RuntimeError("Candidate manifests must have 24 and 33 exact entries")
    if not set(trial).issubset(full):
        raise RuntimeError("Trial list has an entry outside the 33 reviewed candidates")
    counts=Counter(part for part,_ in trial.values())
    if counts!=EXPECTED_PARTITION_COUNTS:
        raise RuntimeError("Unexpected partition count in trial: "+str(counts))
    for location,(part,path) in trial.items():
        if part not in ALLOWED_PARTITIONS:
            raise RuntimeError("Disallowed partition: "+location)
        if path.parent in (PurePosixPath("/"),PurePosixPath("/app"),PurePosixPath("/system/app"),PurePosixPath("/priv-app"),PurePosixPath("/data-app")):
            raise RuntimeError("Refusing shared parent directory: "+location)
    parents=[(part,path.parent) for part,path in trial.values()]
    if len(set(parents))!=24:
        raise RuntimeError("Multiple targets in same folder need manual review")
    for a in parents:
        for b in parents:
            if a!=b and a[0]==b[0] and a[1] in b[1].parents:
                raise RuntimeError("Nested removal directories not allowed")
    return trial,full

def fingerprint(path):
    info=path.lstat()
    mode=info.st_mode
    if stat.S_ISREG(mode): kind="file"
    elif stat.S_ISDIR(mode):kind="directory"
    elif stat.S_ISLNK(mode):kind="symlink"
    else:kind="special"
    attr=[]
    for name in sorted(os.listxattr(path,follow_symlinks=False)):
        value=os.getxattr(path,name,follow_symlinks=False)
        attr.append((name,hashlib.sha256(value).hexdigest()))
    record={"kind":kind, "uid":info.st_uid, "gid":info.st_gid,
            "mode":stat.S_IMODE(mode), "mtime_ns":info.st_mtime_ns,
            "xattr":attr}
    if kind=="file":
        record["bytes"]=info.st_size
        record["sha256"]=sha(path)
    elif kind=="symlink":
        record["link"]=os.readlink(path)
    elif kind=="special":
        record["rdev"]=info.st_rdev
    return record

def tree_map(mount):
    entries={}
    for dirpath, subdirs, names in os.walk(mount,followlinks=False):
        root=Path(dirpath)
        for target in [root]+[root/x for x in names]+[root/x for x in subdirs if (root/x).is_symlink()]:
            key="/"+str(target.relative_to(mount)) if target!=mount else "/"
            if key in entries:
                raise RuntimeError("Duplicate filesystem path: "+key)
            entries[key]=fingerprint(target)
    return entries

def exclusions(part, trial):
    return [(location,str(posix.parent)) for location,(p,posix) in trial.items() if p==part]

def check_folders(original,part,targets,aapt):
    removal=[]
    for location,folder in targets:
        real=original/folder.lstrip("/")
        if real.is_symlink() or not real.is_dir():
            raise RuntimeError("Selected app folder is missing or a symlink: "+location)
        expected=original/location.split(":",1)[1].lstrip("/")
        if not expected.is_file() or expected.is_symlink():
            raise RuntimeError("APK is missing/not regular: "+location)
        found=[p for p in real.rglob("*") if p.is_file() and p.suffix.lower()==".apk"]
        if found!=[expected]:
            raise RuntimeError("App directory has extra or missing APKs: "+location+" found "+str(found))
        package,_=apk_identity(aapt,expected)
        items=sum(1 for _ in real.rglob("*"))
        bytes_total=sum(p.stat().st_size for p in real.rglob("*") if p.is_file() and not p.is_symlink())
        removal.append({"location":location,"folder":folder,"android_package_id":package,
                        "entries_inside":items,"file_bytes":bytes_total})
    return removal

def is_removed(path,folders):
    return any(path==folder or path.startswith(folder+"/") for folder in folders)

def compare_trees(before,after,folders):
    expected={p:info for p,info in before.items() if not is_removed(p,folders)}
    removed=set(before)-set(expected)
    missing=sorted(set(expected)-set(after))
    extras=sorted(set(after)-set(expected))
    mismatches=[]
    for path in set(expected)&set(after):
        if expected[path]!=after[path]:
            differences={key:(expected[path].get(key),after[path].get(key)) for key in set(expected[path])|set(after[path]) if expected[path].get(key)!=after[path].get(key)}
            mismatches.append({"path":path,"difference":differences})
    return {"source_entries":len(before),"expected_retained":len(expected),
            "source_entries_excluded":len(removed),
            "rebuilt_entries":len(after),
            "missing_retained":missing,"unexpected_paths":extras,
            "different_retained":sorted(mismatches,key=lambda x:x["path"]),
            "passed":not(missing or extras or mismatches)}

def mount_readonly(image,directory):
    directory.mkdir(exist_ok=True)
    run_checked("mount","-t","erofs","-o","ro,loop",image,directory)

def mkfs_report(image,mount,excluded,uuid):
    # -T recreates original UNIX 2009 timestamp: verified in source baseline.
    cmd=["mkfs.erofs","-z","lz4hc,9","-T",str(REQUIRED_TIME),
         "-U",uuid]
    for folder in excluded:
        cmd+=["--exclude-path="+folder.lstrip("/")]
    cmd+=[str(image),str(mount)]
    return run_checked(*cmd)

def read_uuid(image):
    p=run_checked("dump.erofs","-s",image)
    found=re.search(r"(?m)^Filesystem UUID:\s*([a-fA-F0-9-]{36})\s*$",p.stdout)
    if not found:
        raise RuntimeError("Original EROFS UUID missing")
    return found.group(1),p.stdout

def test_exclude():
    """Offline fixture proves tool really excludes a *directory*, not only APK."""
    proposed()
    with tempfile.TemporaryDirectory(prefix="erofs-mkfs-fixture-") as temp:
        root=Path(temp)
        staging=root/"input"
        kept=staging/"app/Keep"
        removed=staging/"app/Remove"
        kept.mkdir(parents=True)
        (removed/"oat").mkdir(parents=True)
        (kept/"Keep.apk").write_bytes(b"preserve")
        (removed/"Remove.apk").write_bytes(b"remove")
        (removed/"oat/Remove.odex").write_bytes(b"remove compiled")
        ctx=b"u:object_r:system_file:s0\0"
        os.setxattr(kept/"Keep.apk","security.selinux",ctx)
        for folder,subfolders,files in os.walk(staging):
            for name in subfolders+files:
                os.utime(Path(folder)/name,ns=(REQUIRED_TIME*10**9,)*2,follow_symlinks=False)
            os.utime(folder,ns=(REQUIRED_TIME*10**9,)*2,follow_symlinks=False)
        img=root/"test.erofs"
        mkfs_report(img,staging,["/app/Remove"],"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        run_checked("fsck.erofs",img)
        mounted=root/"mount"
        mount_readonly(img,mounted)
        try:
            if (mounted/"app/Remove").exists():
                raise RuntimeError("EROFS exclusion test failed: folder remains")
            if (mounted/"app/Keep/Keep.apk").read_bytes()!=b"preserve":
                raise RuntimeError("EROFS exclusion test failed: retained APK changed")
            if os.getxattr(mounted/"app/Keep/Keep.apk","security.selinux")!=ctx:
                raise RuntimeError("EROFS exclusion test failed: SELinux label changed")
        finally:
            subprocess.run(["umount",str(mounted)],check=True)
    print("EROFS fixture: excluded entire directory, retained other files and SELinux xattr",flush=True)

def source_and_trial():
    trial,full=proposed()
    errors=[]
    output("TRIAL_POLICY.txt","NON-FLASHABLE, TWO-EROFS-PARTITION OFFLINE TRIAL ONLY\n"
           "Exclude exactly 24 dedicated app folders; preserve nine held APKs and all other partitions.\n"
           "Never patch vbmeta; never produce super.img or a flash command.\n")
    with tempfile.TemporaryDirectory(prefix="yunluo-erofs-trial-") as tempdir:
        working=Path(tempdir)
        archive=working/NAME
        print("Downloading original MIUI 14 firmware once...",flush=True)
        subprocess.run(["python3",str(ROOT/"scripts/download.py"),"--output",str(archive),
                        "--report",str(REPORT/"download-sources.json")],check=True)
        actual=sha(archive,"md5")
        output("archive-md5.txt","Expected: "+MD5+"\nActual: "+actual+"\n")
        if actual!=MD5:
            raise RuntimeError("Original ROM archive MD5 mismatch")
        source_sparse,vbmeta=extract_archive(archive,working)
        archive.unlink()
        avb,hashtrees=avb_checks(vbmeta)
        if len(avb)!=3 or any(item["flags"]!=0 for item in avb):
            raise RuntimeError("Unexpected original AVB flags; stop")
        for part in ALLOWED_PARTITIONS:
            base=part.removesuffix("_a")
            if base not in hashtrees:
                raise RuntimeError("No original hashtree for "+part)
        with source_sparse.open("rb") as stream:
            sparse=stream.read(4)==bytes.fromhex("3aff26ed")
        raw=working/"original-super.raw.img"
        if sparse:
            run_checked(TOOLS/"simg2img",source_sparse,raw)
            source_sparse.unlink()
        else:
            source_sparse.rename(raw)
        if raw.stat().st_size!=SUPER_RAW_SIZE or sha(raw)!=SOURCE_SUPER_SHA256:
            raise RuntimeError("Unexpected original super.img bytes/size")
        output("super-checksum.txt",SOURCE_SUPER_SHA256+"\n")
        layouts=[]
        for slot in (0,1):
            dump=run_checked(TOOLS/"lpdump","-s",slot,raw)
            layouts.append(dump.stdout)
            output("lpdump-slot"+str(slot)+".txt",dump.stdout)
        present={part for slot,part in parse_partitions(layouts[0],0)}
        if not ALLOWED_PARTITIONS.issubset(present):
            raise RuntimeError("Required partition absent from original LP metadata")
        aapt=find_aapt()
        records=[]
        validations=[]
        removals=[]
        for part in sorted(ALLOWED_PARTITIONS):
            print("Building and validating disposable "+part+" trial...",flush=True)
            folder=working/("unpacked-"+part)
            folder.mkdir()
            run_checked(TOOLS/"lpunpack","--slot=0","--partition="+part,raw,folder)
            source_image=folder/(part+".img")
            if fstype(source_image)!="erofs":
                raise RuntimeError("Source partition is not EROFS: "+part)
            original_bytes=source_image.stat().st_size
            run_checked("fsck.erofs",source_image)
            uuid,source_features=read_uuid(source_image)
            original_mount=working/"mount-original"
            mount_readonly(source_image,original_mount)
            try:
                subset=exclusions(part,trial)
                local_removals=check_folders(original_mount,part,subset,aapt)
                folders=[folder for _,folder in subset]
                original=tree_map(original_mount)
                if set(x["mtime_ns"] for x in original.values())!={REQUIRED_TIME*10**9}:
                    raise RuntimeError("Nonuniform original timestamps; rebuilding with -T would change metadata")
                for location,(p,path) in full.items():
                    if p==part and location not in trial:
                        held=original_mount/str(path).lstrip("/")
                        if not held.is_file():
                            raise RuntimeError("One of the protected/held APKs is absent: "+location)
                trial_image=working/(part+"-TRIAL-UNFLASHABLE.erofs")
                mkfs_report(trial_image,original_mount,folders,uuid)
                run_checked("fsck.erofs",trial_image)
                rebuilt_bytes=trial_image.stat().st_size
                # The original AVB descriptor's payload size is a conservative
                # capacity ceiling; not a claim that the AVB digest still matches.
                avb_owner,descriptor=hashtrees[part.removesuffix("_a")]
                ceiling=descriptor["image_size"]
                if rebuilt_bytes>ceiling or rebuilt_bytes>original_bytes:
                    raise RuntimeError("Rebuilt EROFS exceeds original payload/partition allowance: "+part+
                                       ": "+str(rebuilt_bytes)+" > "+str(min(ceiling,original_bytes)))
                rebuilt_mount=working/"mount-rebuilt"
                mount_readonly(trial_image,rebuilt_mount)
                try:
                    rebuilt=tree_map(rebuilt_mount)
                    comparison=compare_trees(original,rebuilt,folders)
                    if not comparison["passed"]:
                        errors.append(part+": retained-file or metadata differences: "+
                                      str(len(comparison["missing_retained"]))+" missing / "+
                                      str(len(comparison["unexpected_paths"]))+" extra / "+
                                      str(len(comparison["different_retained"]))+" mismatched")
                    for location,(p,path) in full.items():
                        if p==part and location not in trial:
                            if str(path) not in rebuilt or rebuilt[str(path)]!=original[str(path)]:
                                errors.append("Held app missing or changed in rebuilt EROFS: "+location)
                finally:
                    subprocess.run(["umount",str(rebuilt_mount)],check=True)
                features=run_checked("dump.erofs","-s",trial_image).stdout
                # Structural feature changes are reported, not silently glossed over.
                validations.append({"partition":part,"source_image_bytes":original_bytes,
                                    "rebuilt_trial_bytes":rebuilt_bytes,
                                    "source_uuid":uuid,
                                    "source_erofs_superblock":source_features,
                                    "trial_erofs_superblock":features,
                                    "source_erofs_sha256":sha(source_image),
                                    "trial_erofs_sha256":sha(trial_image),
                                    "avb_descriptor_image":avb_owner,
                                    "stock_hashtree_matches_trial":False,
                                    "comparison":comparison})
                removals+=local_removals
                print(part+" checked: "+str(rebuilt_bytes)+" bytes; "+str(len(folders))+
                      " app directories absent; "+str(comparison["expected_retained"])+
                      " retained paths compared; changed="+str(len(comparison["different_retained"])),flush=True)
            finally:
                subprocess.run(["umount",str(original_mount)],check=True)
                shutil.rmtree(folder,ignore_errors=True)
        output("removed-directory-manifest.json",json.dumps(removals,indent=2)+"\n")
        output("retained-file-and-metadata-comparison.json",json.dumps(validations,indent=2)+"\n")
        output("blockers.txt","\n".join(errors)+"\n" if errors else "No trial EROFS retained-file differences were found.\n")
        lines=["# Redmi Pad offline EROFS rebuild trial","",
               "ROM: "+VER+" (MD5 matched; original super SHA256 pinned)",
               "Status: "+("FAILED" if errors else "TWO REBUILT PARTITIONS VERIFIED OFFLINE"),
               "",
               "24 dedicated app folders intentionally omitted: product_a=18, system_a=6.",
               "9 higher-uncertainty held APKs remain in their unchanged source partitions.",
               "AVB: all three source vbmeta images unchanged; stock hashtrees will not match rebuilt partitions.",
               "EROFS tool: "+run_checked("mkfs.erofs","-V").stdout.strip(),
               ""]
        for item in validations:
            c=item["comparison"]
            lines+=["## "+item["partition"],
                    "- Before: "+str(item["source_image_bytes"])+" bytes; trial: "+str(item["rebuilt_trial_bytes"])+" bytes",
                    "- Retained paths checked: "+str(c["expected_retained"]),
                    "- Missing retained: "+str(len(c["missing_retained"]))+
                    "; extra paths: "+str(len(c["unexpected_paths"]))+
                    "; metadata/content differences: "+str(len(c["different_retained"]))]
        lines+=["","**FLASH READINESS: NO.** This is an offline reconstruction test, not a valid super.img.",
                "No rebuilt image bytes, patched vbmeta, or flashing instructions were uploaded.",
                "Matching retained source files does not prove MIUI startup compatibility or AVB acceptance.",
                "A future super.img build requires independent LP metadata, full-image, and device-specific AVB validation.",""]
        output("SUMMARY.md","\n".join(lines))
        output("status.json",json.dumps({"source_verified":True,"trial_directories_removed":len(removals),
                                        "reconstructed_partitions":len(validations),
                                        "offline_comparisons_pass":not errors,"flash_ready":False,
                                        "avb_stock_valid_for_modified_images":False,
                                        "binary_images_uploaded":False,"errors":errors},indent=2)+"\n")
        print("\n".join(lines),flush=True)
        if errors:
            raise RuntimeError("Offline image comparison has blockers; see reports-trial/blockers.txt")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    try:
        if args.self_test:test_exclude()
        else:source_and_trial()
    except Exception as exc:
        output("FAILED.txt",str(exc)+"\n"+traceback.format_exc())
        output("status.json",json.dumps({"flash_ready":False,"error":str(exc)},indent=2)+"\n")
        raise

if __name__=="__main__":
    main()
