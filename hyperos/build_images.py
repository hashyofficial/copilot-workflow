#!/usr/bin/env python3
"""HyperOS 1 yunluo: rebuild ONLY super.img and vbmeta.img from fresh Xiaomi stock.

The 131 exact user APK paths are removed as 130 whole app directories and one
standalone file from the *shared* /overlay folder. No firmware ZIP, flash action
or extra APK additions. Mirrors the proven MIUI Build 5 in-place EROFS method,
using measured HyperOS extents instead of MIUI's hard-coded partition geometry.
"""
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from erofs_trial import tree_map, compare_trees, read_uuid, mount_readonly, run_checked
from inventory import TOOLS, sha, fstype

MANIFEST = ROOT / "hyperos/config/Apps_Remove.txt"
INVENTORY = ROOT / "hyperos/results/APKS_ALL.tsv"
SOURCE_REPORT = ROOT / "hyperos/results/SUMMARY.json"
WORK = Path(os.environ.get("HYPEROS_BUILD_WORK", "/tmp/yunluo-hyperos-build"))
RESULT = Path(os.environ.get("HYPEROS_BUILD_RESULT", str(ROOT / "hyperos-build-result")))
EXPECTED_SOURCE_RAW_SHA256 = "965f791ef796d4346b4abf95fad216a90084ed869ef2b6fbae1993d5683c686c"
EXPECTED_SOURCE_VBMETA_SHA256 = "cc34aa04532fc46f70558d0cd98bc4a4f008e9aa795ac9762cec220fd52c80a0"
PARTITIONS = {"mi_ext_a", "product_a", "system_a", "system_ext_a"}
COUNTS = {"mi_ext_a": 20, "product_a": 58, "system_a": 27, "system_ext_a": 26}
OVERLAY_PATH = "product_a:/overlay/MiuiThemeManagerGlobalOverlayTest.apk"
PART_SIZE = 700 * 1024 * 1024
COPY_BUFFER = 8 * 1024 * 1024

def emit(name, data):
    RESULT.mkdir(parents=True, exist_ok=True)
    (RESULT / name).write_text(data, encoding="utf8")

def load_manifest():
    lines = [s.strip() for s in MANIFEST.read_text().splitlines() if s.strip() and not s.lstrip().startswith("#")]
    if len(lines) != 131 or len(lines) != len(set(lines)):
        raise RuntimeError("Exactly 131 distinct APK paths are required")
    with INVENTORY.open(newline="", encoding="utf8") as handle:
        stock = {r["full_location"]: r for r in csv.DictReader(handle, delimiter="\t")}
    if len(stock) != 336:
        raise RuntimeError("Pinned source inventory is not the 336-APK HyperOS source")
    targets = {}
    counts = dict.fromkeys(PARTITIONS, 0)
    for location in lines:
        part, path = location.split(":", 1)
        posix = PurePosixPath(path)
        if part not in PARTITIONS or location not in stock or not posix.is_absolute() or ".." in posix.parts or posix.suffix.lower() != ".apk":
            raise RuntimeError("Unrecognized APK target: " + location)
        if len(posix.parts) < 3:
            raise RuntimeError("Refusing top-level/system directory selection")
        if not posix.name == stock[location]["apk_filename"]:
            raise RuntimeError("APK filename differs from the stock inventory")
        if location == OVERLAY_PATH:
            excluded = str(posix)  # shared /overlay: exclude the user-selected APK, not unrelated overlays
        else:
            excluded = str(posix.parent)
            if excluded in ("/", "/app", "/priv-app", "/data-app", "/overlay", "/system/app", "/system/priv-app", "/system_ext/app", "/system_ext/priv-app", "/product/app", "/product/priv-app", "/product/data-app"):
                raise RuntimeError("Refusing shared parent folder: " + location)
        targets[location] = {"partition": part, "apk": str(posix), "exclude": excluded, "mode": "file" if location == OVERLAY_PATH else "folder"}
        counts[part] += 1
    if counts != COUNTS:
        raise RuntimeError("Unexpected partition counts in selected 131 targets: " + str(counts))
    folderpaths = [(x["partition"], x["exclude"]) for x in targets.values()]
    if len(folderpaths) != len(set(folderpaths)):
        raise RuntimeError("Two user requests share an exclusion")
    for i, (part, base) in enumerate(folderpaths):
        for othpart, othbase in folderpaths[i+1:]:
            if part == othpart and (PurePosixPath(base) in PurePosixPath(othbase).parents or PurePosixPath(othbase) in PurePosixPath(base).parents):
                raise RuntimeError("Overlapping user removal paths: " + base)
    return targets

def parse_regions(dump):
    """Read exact one-extent LP regions; do not use MIUI 14 sector offsets."""
    if "Partition table:" not in dump or "Block device table:" not in dump:
        raise RuntimeError("Unexpected HyperOS LP metadata")
    table = dump.split("Partition table:",1)[1].split("Super partition layout:",1)[0]
    regions = {}
    for section in table.split("------------------------"):
        matched = re.search(r"(?m)^\s*Name:\s*([A-Za-z0-9_]+)\s*$", section)
        if not matched or matched.group(1) not in PARTITIONS:
            continue
        extents = re.findall(r"(?m)^\s*0 \.\. (\d+) linear super (\d+)\s*$", section)
        if len(extents) != 1:
            raise RuntimeError("Expected one contiguous original extent for " + matched.group(1))
        length, start = map(int, extents[0])
        regions[matched.group(1)] = (start * 512, (length + 1) * 512)
    if set(regions) != PARTITIONS:
        raise RuntimeError("Incomplete original HyperOS region layout: " + str(regions))
    intervals = sorted((start, start+length) for start,length in regions.values())
    if any(end > nextstart for (_,end),(nextstart,_) in zip(intervals, intervals[1:])):
        raise RuntimeError("Logical partition extents overlap")
    return regions

def replace_extent(candidate, start, capacity, rebuilt):
    length = rebuilt.stat().st_size
    if length > capacity or length % 4096:
        raise RuntimeError("New EROFS overflows its original extent or is misaligned")
    with candidate.open("r+b") as dest, rebuilt.open("rb") as src:
        dest.seek(start)
        shutil.copyfileobj(src, dest, COPY_BUFFER)
        left = capacity-length
        zero = b"\0" * COPY_BUFFER
        while left:
            n=min(left,len(zero))
            dest.write(zero[:n])
            left -= n

def digest_span(path, start, length):
    h=hashlib.sha256()
    with path.open("rb") as f:
        f.seek(start)
        while length:
            part=f.read(min(length,COPY_BUFFER))
            if not part: raise RuntimeError("Truncated super image")
            h.update(part)
            length-=len(part)
    return h.hexdigest()

def patch_vbmeta(stock, output):
    source = stock.read_bytes()
    if sha(stock) != EXPECTED_SOURCE_VBMETA_SHA256:
        raise RuntimeError("Wrong stock HyperOS vbmeta checksum")
    if len(source) != 8192 or source[:4] != b"AVB0":
        raise RuntimeError("Unexpected stock vbmeta header/size")
    if struct.unpack_from(">I", source, 120)[0] != 0:
        raise RuntimeError("Unexpected original AVB flags")
    edited = bytearray(source)
    struct.pack_into(">I", edited, 120, 3)
    delta=[n for n,(a,b) in enumerate(zip(source,edited)) if a!=b]
    if delta != [123]:
        raise RuntimeError("AVB flags patch unexpectedly changed header bytes")
    if edited[:4] != b"AVB0" or struct.unpack_from(">I",edited,120)[0] != 3:
        raise RuntimeError("Patched AVB flags are not as requested")
    output.write_bytes(edited)
    return {"original_sha256": sha(stock), "modified_sha256": sha(output),
            "changed_offsets": delta, "original_flags": 0, "modified_flags": 3,
            "original_signature_valid_for_modified_image": False}

def check_retained(original, rebuilt, exclusions):
    # Dedicated folders are omitted wholesale. The root of the shared overlay
    # directory remains; just the explicitly listed APK is excluded.
    diff=compare_trees(original,rebuilt,exclusions)
    if not diff["passed"]:
        raise RuntimeError("Unwanted changes to retained file content or metadata: "+
                           str({k:diff[k][:4] for k in ("missing_retained","unexpected_paths","different_retained")}))
    return {"source_entries":diff["source_entries"],"retained_entries":diff["expected_retained"],
            "removed_tree_entries":diff["source_entries_excluded"], "comparison_passed":True}

def rebuild_partition(raw, candidate, name, start, capacity, targets):
    temp = WORK / ("work-" + name)
    temp.mkdir()
    unpack = temp/"source";unpack.mkdir()
    run_checked(TOOLS/"lpunpack","--slot=0","--partition="+name,raw,unpack)
    source = unpack/(name+".img")
    if not source.is_file() or source.stat().st_size != capacity:
        raise RuntimeError("Stock partition size differs from lpdump extent: " + name)
    if fstype(source) != "erofs":
        raise RuntimeError("Expected EROFS in HyperOS partition: " + name)
    run_checked("fsck.erofs",source)
    uuid, features = read_uuid(source)
    mounted = temp/"mounted"
    mount_readonly(source,mounted)
    try:
        before=tree_map(mounted)
        excluded=[]
        local = []
        for location, rec in targets.items():
            if rec["partition"] != name:continue
            apk=mounted/rec["apk"].lstrip("/")
            if not apk.is_file() or apk.is_symlink():
                raise RuntimeError("Requested stock APK absent or not a regular file: "+location)
            path=mounted/rec["exclude"].lstrip("/")
            if rec["mode"] == "folder":
                if not path.is_dir() or path.is_symlink():
                    raise RuntimeError("Requested whole folder is not a directory: "+location)
                apks=sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower()==".apk")
                if apks != [apk]:
                    raise RuntimeError("Folder has unrequested APK(s), stopping: "+location+" "+str(apks))
            elif not path.is_file():
                raise RuntimeError("Shared-overlay file missing: "+location)
            excluded.append(rec["exclude"])
            local.append({"apk":location,"excluded":rec["exclude"],"mode":rec["mode"]})
        if len(excluded) != COUNTS[name]:
            raise RuntimeError("Did not map exactly the requested number of targets in "+name)
        timestamps={v["mtime_ns"] for v in before.values()}
        build_time = next(iter(timestamps))//1000000000 if len(timestamps)==1 else None
        output = temp/"new.erofs"
        cmd=["mkfs.erofs","-z","lz4hc,9","-U",uuid]
        if build_time is not None: cmd+=["-T",str(build_time)]
        cmd += ["--exclude-path="+p.lstrip("/") for p in excluded]
        run_checked(*(cmd+[output,mounted]))
        run_checked("fsck.erofs",output)
    finally:
        run_checked("umount",mounted)
    replace_extent(candidate,start,capacity,output)
    checkdir=temp/"rebuilt";checkdir.mkdir()
    run_checked(TOOLS/"lpunpack","--slot=0","--partition="+name,candidate,checkdir)
    rebuilt=checkdir/(name+".img")
    run_checked("fsck.erofs",rebuilt)
    aftermount=temp/"verified"
    mount_readonly(rebuilt,aftermount)
    try:
        compared=check_retained(before,tree_map(aftermount),excluded)
    finally:
        run_checked("umount",aftermount)
    record={"partition":name,"removed_apk_entries":len(local),"folder_exclusions":sum(x["mode"]=="folder" for x in local),
            "single_file_exclusions":sum(x["mode"]=="file" for x in local),
            "bytes_original":capacity, "bytes_rebuilt":output.stat().st_size,
            "original_uuid":uuid,"mtime_uniform":build_time is not None,
            "comparison":compared,"removed":local}
    shutil.rmtree(temp)
    return record

def build():
    targets=load_manifest()
    source_report=json.loads(SOURCE_REPORT.read_text())
    if source_report["stock_super_raw_sha256"]!=EXPECTED_SOURCE_RAW_SHA256 or source_report["stock_vbmeta_sha256"]!=EXPECTED_SOURCE_VBMETA_SHA256:
        raise RuntimeError("Unexpected firmware provenance: inventory is not the pinned stock HyperOS 1")
    work_source = WORK/"stock"
    sparse=work_source/"images/super.img"
    vbmeta=work_source/"images/vbmeta.img"
    if not sparse.is_file() or not vbmeta.is_file():
        raise RuntimeError("Missing clean HyperOS super/vbmeta from verified source archive")
    WORK.mkdir(parents=True,exist_ok=True)
    RESULT.mkdir(parents=True,exist_ok=True)
    raw=WORK/"source-super.raw.img"
    with sparse.open("rb") as f:
        signature=f.read(4)
    if signature != bytes.fromhex("3aff26ed"): raise RuntimeError("Expected sparse original super")
    run_checked(TOOLS/"simg2img",sparse,raw)
    sparse.unlink()
    if sha(raw) != EXPECTED_SOURCE_RAW_SHA256:
        raise RuntimeError("Original HyperOS super SHA256 mismatch")
    print("Original HyperOS raw super verified, rebuilding requested 131 APK targets",flush=True)
    layout=[run_checked(TOOLS/"lpdump","-s",slot,raw).stdout for slot in (0,1)]
    for slot,text in enumerate(layout):emit("original-lpdump-slot"+str(slot)+".txt",text)
    regions=parse_regions(layout[0])
    candidate=WORK/"candidate-super.raw.img"
    subprocess.run(["cp","--reflink=auto","--sparse=always",str(raw),str(candidate)],check=True)
    records=[]
    for part in ("mi_ext_a","product_a","system_a","system_ext_a"):
        print("Rebuilding HyperOS EROFS:",part,flush=True)
        start,capacity=regions[part]
        record=rebuild_partition(raw,candidate,part,start,capacity,targets)
        records.append(record)
        print("Retained paths verified:",part,record["comparison"]["retained_entries"],flush=True)
    for slot in (0,1):
        if run_checked(TOOLS/"lpdump","-s",slot,candidate).stdout!=layout[slot]:
            raise RuntimeError("Candidate changed LP metadata slot "+str(slot))
    raw_size=raw.stat().st_size
    intervals=sorted((start,start+cap) for start,cap in regions.values())
    cursor=0
    for start,end in intervals+[(raw_size,raw_size)]:
        if end > raw_size:
            raise RuntimeError("Candidate partition outside super")
        if cursor < start and digest_span(raw,cursor,start-cursor)!=digest_span(candidate,cursor,start-cursor):
            raise RuntimeError("Unexpected bytes modified outside requested partitions")
        cursor=end
    if sum(r["removed_apk_entries"] for r in records)!=131 or sum(r["folder_exclusions"] for r in records)!=130:
        raise RuntimeError("All 131 selected targets were not removed exactly")
    raw_digest=sha(candidate)
    modified_vbmeta=RESULT/"vbmeta.img"
    avb=patch_vbmeta(vbmeta,modified_vbmeta)
    sparse_output=WORK/"super.sparse.img"
    run_checked(TOOLS/"img2simg",candidate,sparse_output)
    # Save space before sparse roundtrip; raw provenance and modified digests already captured.
    raw.unlink()
    candidate.unlink()
    roundtrip=WORK/"roundtrip-super.raw.img"
    run_checked(TOOLS/"simg2img",sparse_output,roundtrip)
    if roundtrip.stat().st_size!=raw_size or sha(roundtrip)!=raw_digest:
        raise RuntimeError("Modified sparse image failed its raw SHA256 roundtrip")
    roundtrip.unlink()
    parts=[]
    with sparse_output.open("rb") as f:
        i=0
        while True:
            block=f.read(PART_SIZE)
            if not block:break
            dest=RESULT/("super.img.part-%03d"%i)
            dest.write_bytes(block)
            parts.append({"filename":dest.name,"bytes":len(block),"sha256":hashlib.sha256(block).hexdigest()})
            i+=1
    total=sum(x["bytes"] for x in parts)
    if not parts or total!=sparse_output.stat().st_size:
        raise RuntimeError("Modified super multipart size mismatch")
    summary={
       "device":"Redmi Pad yunluo","os":"OS1.0.9.0.ULYMIXM","android":14,
       "source_super_raw_sha256":EXPECTED_SOURCE_RAW_SHA256,"source_vbmeta_sha256":EXPECTED_SOURCE_VBMETA_SHA256,
       "modified_super_raw_sha256":raw_digest,"modified_super_sparse_sha256":sha(sparse_output),
       "modified_super_sparse_bytes":total,"split_files":parts,
       "patched_vbmeta":avb,"removed_apk_entries":131,"whole_folders_removed":130,
       "standalone_shared_overlay_apks_removed":1, "unrequested_apks_removed":0,
       "modified_partitions":records,"metadata_slot_0_unchanged":True,"metadata_slot_1_unchanged":True,
       "non_target_super_bytes_unchanged":True,"retained_erofs_content_and_metadata_verified":True,
       "sparse_raw_roundtrip_verified":True,"fastboot_zip_produced":False,
       "new_apks_added":0,"physical_device_boot_tested":False,
       "avb_signature_invalidated":True
    }
    emit("MANIFEST.json",json.dumps(summary,sort_keys=True,indent=2)+"\n")
    lines=["# HyperOS 1 yunluo Build 1 - 131 user-selected APK removals","",
           "Original Xiaomi OS1.0.9.0.ULYMIXM, Android 14.",
           "130 dedicated app folders excluded; one user-targeted APK excluded from shared /overlay.",
           "Original LP metadata in both slots, all non-target bytes and retained EROFS contents checked.",
           "Only super.img (sparse, multipart) and vbmeta.img produced; no full firmware ZIP.",
           "Modified vbmeta signature is invalid; unlocked bootloader is required, do not relock.",
           "This image has NOT been tested on a physical Redmi Pad.",
           "",
           "To reconstruct sparse super.img, concatenate super.img.part-000, -001, etc. in numeric order.",
           "Verify SHA256 values in MANIFEST.json before any use.",
           "",
           "| Partition | APK targets |",
           "|---|---:|"]
    lines += ["| "+r["partition"]+" | "+str(r["removed_apk_entries"])+" |" for r in records]
    emit("SUMMARY.md","\n".join(lines)+"\n")
    print("HYPEROS_131_APP_REMOVALS_SUPER_VBMETA_BUILD_SUCCEEDED",flush=True)

if __name__=="__main__":
    try:
        build()
    except Exception as exc:
        emit("FAILED.txt",str(exc)+"\n")
        raise
