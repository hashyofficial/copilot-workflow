#!/usr/bin/env python3
"""Build a disposable slot-A super.img candidate from the verified 24-app plan.

Preserve Xiaomi's LP metadata and every non-target partition. Reuse the
previously validated EROFS exclusion process. No bootloader or flash actions.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from inventory import ROOT, NAME, MD5, TOOLS, sha, command, fstype
from combined_preflight import extract_archive, SUPER_RAW_SIZE
from erofs_trial import (SOURCE_SUPER_SHA256, proposed, exclusions,
                         check_folders, tree_map, compare_trees,
                         mkfs_report, mount_readonly, read_uuid,
                         run_checked, find_aapt)

RESULTS = ROOT / "reports-super"
BINARIES = ROOT / "super-artifact"
RESULTS.mkdir(exist_ok=True)
# Offset and number of 512-byte sectors, taken from the signed-off source LP audit.
REGIONS = {"product_a": (4096,5590248), "system_a": (5595136,1804456)}
CHUNK = 768 * 1024 * 1024

def report(name,text):
    (RESULTS/name).write_text(text, encoding="utf8")

def digest_span(file,offset,length):
    h=hashlib.sha256()
    with file.open("rb") as stream:
        stream.seek(offset)
        while length:
            data=stream.read(min(length,8*1024*1024))
            if not data: raise RuntimeError("Truncated super image")
            length-=len(data)
            h.update(data)
    return h.hexdigest()

def unpack(raw,partition,directory):
    directory.mkdir()
    run_checked(TOOLS/"lpunpack","--slot=0","--partition="+partition,raw,directory)
    image=directory/(partition+".img")
    if fstype(image)!="erofs": raise RuntimeError(partition+" is not EROFS")
    return image

def replace_region(raw,offset,capacity,newimage):
    length=newimage.stat().st_size
    if length>capacity or length%4096:
        raise RuntimeError("EROFS does not fit allocated extent")
    with raw.open("r+b") as target,newimage.open("rb") as original:
        target.seek(offset)
        shutil.copyfileobj(original,target,8*1024*1024)
        blank=b"\0"*(8*1024*1024)
        left=capacity-length
        while left:
            n=min(left,len(blank))
            target.write(blank[:n])
            left-=n

def build():
    trial,_=proposed()
    with tempfile.TemporaryDirectory(prefix="yunluo-super-candidate-") as td:
        temp=Path(td);archive=temp/NAME
        subprocess.run(["python3",str(ROOT/"scripts/download.py"),
                        "--output",str(archive),
                        "--report",str(RESULTS/"download.json")],check=True)
        if sha(archive,"md5")!=MD5: raise RuntimeError("ROM MD5 mismatch")
        sparse,vbmeta=extract_archive(archive,temp)
        archive.unlink()
        original=temp/"original.raw.img"
        with sparse.open("rb") as stream: is_sparse=stream.read(4)==bytes.fromhex("3aff26ed")
        if is_sparse:
            run_checked(TOOLS/"simg2img",sparse,original)
            sparse.unlink()
        else: sparse.rename(original)
        if original.stat().st_size!=SUPER_RAW_SIZE or sha(original)!=SOURCE_SUPER_SHA256:
            raise RuntimeError("Original super SHA256 mismatch")
        source_layout=[run_checked(TOOLS/"lpdump","-s",n,original).stdout for n in (0,1)]
        for name,(sector,count) in REGIONS.items():
            if "Name: "+name not in source_layout[0] or "linear super "+str(sector) not in source_layout[0]:
                raise RuntimeError("Unrecognized source extent "+name)
        candidate=temp/"candidate.raw.img"
        subprocess.run(["cp","--reflink=auto","--sparse=always",str(original),str(candidate)],check=True)
        aapt=find_aapt();rows=[]
        for name,(sector,count) in REGIONS.items():
            print("Rebuilding "+name+" (whole app directories)...",flush=True)
            src=unpack(original,name,temp/("orig-"+name))
            if src.stat().st_size!=count*512:raise RuntimeError("Original LP extent mismatch")
            run_checked("fsck.erofs",src)
            uuid,_=read_uuid(src)
            mount=temp/("mount-"+name)
            mount_readonly(src,mount)
            try:
                excluded=exclusions(name,trial)
                files=check_folders(mount,name,excluded,aapt)
                before=tree_map(mount)
                rebuilt=temp/(name+"-rebuilt.erofs")
                mkfs_report(rebuilt,mount,[path for _,path in excluded],uuid)
                run_checked("fsck.erofs",rebuilt)
            finally:
                subprocess.run(["umount",str(mount)],check=True)
            replace_region(candidate,sector*512,count*512,rebuilt)
            out=unpack(candidate,name,temp/("check-"+name))
            run_checked("fsck.erofs",out)
            verified_mount=temp/("verified-"+name)
            mount_readonly(out,verified_mount)
            try:
                diff=compare_trees(before,tree_map(verified_mount),[p for _,p in excluded])
                if not diff["passed"]:raise RuntimeError("Retained files changed in "+name)
                rows.append({"partition":name,"directories_removed":len(files),
                             "retained_paths_matched":diff["expected_retained"],
                             "reconstructed_erofs_bytes":rebuilt.stat().st_size})
            finally:
                subprocess.run(["umount",str(verified_mount)],check=True)
        for slot in (0,1):
            if run_checked(TOOLS/"lpdump","-s",slot,candidate).stdout!=source_layout[slot]:
                raise RuntimeError("LP metadata was modified")
        intervals=sorted((sector*512,(sector+count)*512) for sector,count in REGIONS.values())
        cursor=0
        for start,end in intervals+[(SUPER_RAW_SIZE,SUPER_RAW_SIZE)]:
            if cursor<start and digest_span(original,cursor,start-cursor)!=digest_span(candidate,cursor,start-cursor):
                raise RuntimeError("Unexpected modifications outside target partitions")
            cursor=end
        if sum(x["retained_paths_matched"] for x in rows)!=5409:
            raise RuntimeError("Source retained file count changed")
        sparse_out=temp/"candidate.sparse.img"
        run_checked(TOOLS/"img2simg",candidate,sparse_out)
        check=temp/"roundtrip.raw.img"
        run_checked(TOOLS/"simg2img",sparse_out,check)
        if check.stat().st_size!=SUPER_RAW_SIZE or sha(check)!=sha(candidate):
            raise RuntimeError("Sparse image round-trip failed")
        BINARIES.mkdir(exist_ok=True)
        parts=[]
        with sparse_out.open("rb") as stream:
            i=0
            while True:
                data=stream.read(CHUNK)
                if not data: break
                name=f"super.sparse.img.part-{i:03d}"
                (BINARIES/name).write_bytes(data)
                parts.append({"file":name,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)})
                i+=1
        manifest={"slot":"a","model":"yunluo","modified_partitions":rows,
                  "original_super_sha256":SOURCE_SUPER_SHA256,
                  "modified_super_sha256":sha(candidate),
                  "sparse_sha256":sha(sparse_out),
                  "parts":parts,"lp_metadata_preserved":True,
                  "other_regions_unchanged":True,
                  "avb_compatible_with_stock_vbmeta":False,
                  "flash_tested":False}
        text=json.dumps(manifest,indent=2)+"\n"
        report("manifest.json",text)
        (BINARIES/"manifest.json").write_text(text)
        report("result.txt","Offline candidate assembled: 24 folders excluded; 5409 paths verified.\n"+
               "No vbmeta image has been modified. Stock AVB is incompatible.\n")
        print("Sparse super package completed and checksums written.",flush=True)

if __name__=="__main__":
    build()
