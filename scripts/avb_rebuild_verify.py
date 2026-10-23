#!/usr/bin/env python3
"""Cryptographic AVB check: signed stock vs 24-app rebuilt EROFS (no flashing)."""
import hashlib, json, os, struct, subprocess, shutil, tempfile, traceback
from pathlib import Path
from inventory import ROOT, NAME, MD5, TOOLS, sha, command
from combined_preflight import extract_archive, avb_checks, SUPER_RAW_SIZE
from vbmeta_audit import HEADER, audit_one
from erofs_trial import (SOURCE_SUPER_SHA256, proposed, exclusions, check_folders,
                         mkfs_report, mount_readonly, read_uuid, run_checked, find_aapt)

OUT=ROOT/"reports-avb-rebuilt"
OUT.mkdir(exist_ok=True)
DIGESTINFO=bytes.fromhex("3031300d060960864801650304020105000420")

def report(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf8")

def verify_signature(name,blob):
    """Independent RSA PKCS#1 v1.5 verification of the original AVB header."""
    h=struct.unpack_from(HEADER,blob)
    auth,aux=h[3],h[4]
    if h[5]!=1:raise RuntimeError(name+": expected SHA256_RSA2048")
    ho,hs,so,ss,ko,ks=h[6:12]
    if hs!=32 or ss!=256 or ks!=520:raise RuntimeError(name+": unexpected AVB signature/key sizes")
    key=blob[256+auth+ko:256+auth+ko+ks]
    bits=int.from_bytes(key[:4],"big")
    if bits!=2048:raise RuntimeError(name+": unexpected RSA key length")
    modulus=int.from_bytes(key[8:264],"big")
    message=blob[:256]+blob[256+auth:256+auth+aux]
    digest=hashlib.sha256(message).digest()
    if blob[256+ho:256+ho+hs]!=digest:raise RuntimeError(name+": signed header hash is invalid")
    signature=blob[256+so:256+so+ss]
    clear=pow(int.from_bytes(signature,"big"),65537,modulus).to_bytes(256,"big")
    expected=b"\x00\x01"+b"\xff"*(256-3-len(DIGESTINFO)-32)+b"\x00"+DIGESTINFO+digest
    if clear!=expected:raise RuntimeError(name+": original RSA signature INVALID")
    return {"vbmeta":name,"signature_valid":True,"algorithm":"SHA256_RSA2048",
            "sha256":hashlib.sha256(blob).hexdigest(),
            "header_flags":audit_one(name,blob)["flags"]}

def avbtool_check(tool,meta,folder):
    p=subprocess.run(["python3",str(tool),"verify_image","--image",str(meta)],
                     text=True,capture_output=True,timeout=600,cwd=folder)
    return {"exit_code":p.returncode,"stdout":p.stdout[-2500:],
            "stderr":p.stderr[-2500:]}

def one_part(source,part,workspace,tool,meta):
    """Build a disposable modified EROFS and test stock root-digest mismatch."""
    source_file=source/(part[:-2]+".img")
    size=source_file.stat().st_size
    mount=workspace/("mount-"+part)
    mount_readonly(source_file,mount)
    try:
        trial,_=proposed()
        removal=exclusions(part,trial)
        checked=check_folders(mount,part,removal,find_aapt())
        uuid,_=read_uuid(source_file)
        rebuilt=workspace/(part+".erofs")
        mkfs_report(rebuilt,mount,[folder for _,folder in removal],uuid)
        run_checked("fsck.erofs",rebuilt)
    finally:
        subprocess.run(["umount",str(mount)],check=True)
    original=source/(part[:-2]+".img")
    backup=source/(part[:-2]+".stock.img")
    original.rename(backup)
    try:
        shutil.copyfile(rebuilt,original)
        with original.open("ab") as f:f.truncate(size)
        observed=avbtool_check(tool,meta,source)
        # Signed original vbmeta still requires the OLD Merkle root.
        if observed["exit_code"]==0:
            raise RuntimeError("Unexpected stock AVB verification PASS for changed "+part)
        messages=observed["stdout"]+"\n"+observed["stderr"]
        if "hashtree" not in messages.lower() and "digest" not in messages.lower():
            raise RuntimeError("AVB tool failed for another reason, not hashtree digest: "+messages[-600:])
        return {"partition":part,"whole_app_directories_removed":len(checked),
                "stock_avb_verification_pass":False,"expected_failure":"root digest/hash tree mismatch",
                "original_full_partition_bytes":size,"rebuilt_erofs_bytes":rebuilt.stat().st_size,
                "avbtool":observed}
    finally:
        original.unlink(missing_ok=True)
        backup.rename(original)
        rebuilt.unlink(missing_ok=True)

def main():
    proposed()
    with tempfile.TemporaryDirectory(prefix="yunluo-avb-cryptographic-") as d:
        tmp=Path(d)
        archive=tmp/NAME
        tool=Path(os.environ["AVBTOOL_PATH"])
        subprocess.run(["python3",str(ROOT/"scripts/download.py"),"--output",str(archive),
                        "--report",str(OUT/"download-probes.json")],check=True)
        if sha(archive,"md5")!=MD5:raise RuntimeError("Xiaomi ROM checksum mismatch")
        image,originals=extract_archive(archive,tmp)
        archive.unlink()
        signatures=[verify_signature(name,data) for name,data in originals.items()]
        audited,hashtrees=avb_checks(originals)
        if len(signatures)!=3:raise RuntimeError("Missing signed AVB images")
        for part in ("product","system","system_ext"):
            if part not in hashtrees:raise RuntimeError("No stock AVB descriptor "+part)
        raw=tmp/"super.raw.img"
        with image.open("rb") as f: sparse=f.read(4)==bytes.fromhex("3aff26ed")
        if sparse:
            run_checked(TOOLS/"simg2img",image,raw)
            image.unlink()
        else:image.rename(raw)
        if raw.stat().st_size!=SUPER_RAW_SIZE or sha(raw)!=SOURCE_SUPER_SHA256:
            raise RuntimeError("Original super bytes differ from pinned firmware")
        part_dir=tmp/"avb"
        part_dir.mkdir()
        # AVB descriptor names are suffix-free; exact active A-slot images are used.
        for part in ("product","system","system_ext"):
            temp_out=tmp/("extract-"+part)
            temp_out.mkdir()
            run_checked(TOOLS/"lpunpack","--slot=0","--partition="+part+"_a",raw,temp_out)
            (temp_out/(part+"_a.img")).rename(part_dir/(part+".img"))
            shutil.rmtree(temp_out)
        meta=part_dir/"vbmeta_system.img"
        meta.write_bytes(originals["vbmeta_system.img"])
        stock=avbtool_check(tool,meta,part_dir)
        if stock["exit_code"]!=0:
            raise RuntimeError("Original signed vbmeta_system did not verify source partitions: "+
                               (stock["stdout"]+"\n"+stock["stderr"])[-1200:])
        print("Stock signatures: 3 valid. Stock system/product/system_ext AVB hashtrees: valid.",flush=True)
        changed=[one_part(part_dir,p,tmp,tool,meta) for p in ("product_a","system_a")]
        result={"source_archive_md5_verified":True,"original_signatures":signatures,
                "stock_vbmeta_system_and_three_partitions_verified":True,
                "stock_verification_detail":stock,
                "changed_partition_avb_results":changed,
                "stock_avb_matches_rebuild":False,"flash_ready":False,
                "patched_vbmeta_produced":False,"device_tested":False}
        report("RESULTS.json",result)
        (OUT/"SUMMARY.md").write_text(
            "# Cryptographic stock and modified AVB tests\n\n"+
            "The three original AVB0 SHA256_RSA2048 signatures passed independent verification.\n"+
            "AOSP avbtool verifies stock system, product, and system_ext against signed vbmeta_system.\n"+
            "After removing the 24 dedicated app directories, stock AVB fails on product_a and system_a "+
            "because their content no longer matches the stock root digest.\n\n"+
            "This result DOES NOT mean an unlocked device was boot tested; no vbmeta was patched or flashed.\n",
            encoding="utf8")
        print("Completed AVB cryptographic checks: original PASS; both modifications fail stock root digests (expected).",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as ex:
        report("FAILURE.json",{"error":str(ex),"traceback":traceback.format_exc(),"flash_ready":False})
        raise
