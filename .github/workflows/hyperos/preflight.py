#!/usr/bin/env python3
"""Inspect stock HyperOS super.img and vbmeta.img: no modifications or flashing."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent
ROM = json.loads((ROOT / "firmware.json").read_text())
CHUNK = 8 * 1024 * 1024
IMAGES = {"images/super.img", "images/vbmeta.img"}
DIAGNOSTICS = {
    "flash_all.sh", "images/crclist.txt", "images/sparsecrclist.txt",
    "images/MT6789_Android_scatter.txt", "images/MT6789_Android_scatter.xml",
}
MAX_SUPER = 12 * 1024**3

def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()

def report_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")

def execute(*argv):
    p = subprocess.run([str(a) for a in argv], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError("Command failed: %s\n%s" % (" ".join(map(str, argv)), p.stderr[-2000:]))
    return p.stdout

def extract(args):
    archive, work, reports = Path(args.archive), Path(args.work), Path(args.reports)
    if archive.name != ROM["archive_name"]:
        raise ValueError("Wrong stock firmware archive name")
    actual_md5 = digest(archive, "md5")
    if actual_md5 != ROM["archive_md5"]:
        raise ValueError("Wrong stock firmware MD5; refusing image extraction")
    work.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    found, members = set(), []
    with tarfile.open(archive, "r|gz") as stream:
        for member in stream:
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts or member.issym() or member.islnk() or member.isdev():
                raise ValueError("Unsafe source archive member")
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError("Unknown archive member type")
            if len(p.parts) < 2 or not p.parts[0].startswith("yunluo_global_images_OS1.0.9.0.ULYMIXM"):
                raise ValueError("Unexpected source firmware root")
            relative = "/".join(p.parts[1:])
            if relative not in IMAGES and relative not in DIAGNOSTICS:
                continue
            if relative in found:
                raise ValueError("Duplicate firmware member: " + relative)
            found.add(relative)
            maximum = MAX_SUPER if relative == "images/super.img" else (1024 * 1024 if relative == "images/vbmeta.img" else 4 * 1024 * 1024)
            if member.size <= 0 or member.size > maximum:
                raise ValueError("Unexpected firmware component size: " + relative)
            destination = (work / relative) if relative in IMAGES else (reports / "original-text" / relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with stream.extractfile(member) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst, CHUNK)
            if destination.stat().st_size != member.size:
                raise ValueError("Truncated firmware member")
            members.append({"name": relative, "bytes": member.size, "sha256": digest(destination)})
    if not IMAGES.issubset(found):
        raise ValueError("Missing stock super.img or vbmeta.img")
    report_json(reports / "01-source.json", {
        "rom_version": ROM["os_version"], "archive": archive.name,
        "verified_archive_md5": actual_md5, "members": members,
        "modified_images": 0, "firmware_zip_built": False
    })
    print("Verified stock HyperOS archive MD5; extracted original super.img and vbmeta.img.")

def inspect(args):
    work, reports, tools = Path(args.work), Path(args.reports), Path(args.tools)
    sparse, raw, vbmeta = work / "images/super.img", work / "super.raw.img", work / "images/vbmeta.img"
    if not (reports / "01-source.json").exists() or not sparse.is_file() or not vbmeta.is_file():
        raise ValueError("Missing verified extraction - run extract first")
    with sparse.open("rb") as f:
        sparse_header = f.read(28)
    if len(sparse_header) != 28:
        raise ValueError("Truncated sparse header")
    magic, major, minor, hsize, csize, block_size, blocks, chunks, checksum = struct.unpack("<I4H4I", sparse_header)
    raw_size = blocks * block_size
    if (magic, major, minor, hsize, csize) != (0xED26FF3A, 1, 0, 28, 12):
        raise ValueError("Unrecognized stock super sparse format")
    if block_size % 4096 or not 1024**3 < raw_size <= MAX_SUPER:
        raise ValueError("Unexpected super logical size")
    if raw.exists():
        raise ValueError("Refusing to overwrite raw image")
    execute(tools / "simg2img", sparse, raw)
    if raw.stat().st_size != raw_size:
        raise ValueError("Stock sparse-to-raw conversion size mismatch")
    sparse.unlink()  # Free multi-GB sparse copy after source SHA was recorded.
    partitions = {}
    for slot in (0, 1):
        layout = execute(tools / "lpdump", "-s", slot, raw)
        (reports / ("02-lpdump-slot-%d.txt" % slot)).write_text(layout)
        names = sorted(set(re.findall(r"(?m)^\s*Name:\s*([A-Za-z0-9_]+)\s*$", layout)))
        if not names:
            raise ValueError("Cannot parse HyperOS lpdump slot %d" % slot)
        partitions[str(slot)] = names
    expected = {"product_a", "system_a", "system_ext_a"}
    if not expected.issubset(partitions["0"]):
        raise ValueError("HyperOS LP layout differs; inspect raw reports before rebuilding")
    header = vbmeta.read_bytes()
    if len(header) < 256 or header[:4] != b"AVB0":
        raise ValueError("Unexpected HyperOS vbmeta image format")
    flags = struct.unpack_from(">I", header, 120)[0]
    algo = struct.unpack_from(">I", header, 28)[0]
    report_json(reports / "03-image-audit.json", {
        "rom": ROM["os_version"], "stock_raw_super_sha256": digest(raw),
        "raw_super_size": raw_size, "sparse_block_size": block_size,
        "sparse_chunks": chunks, "partitions_by_slot": partitions,
        "stock_vbmeta_sha256": digest(vbmeta), "vbmeta_bytes": len(header),
        "stock_vbmeta_avb0_flags": flags, "stock_vbmeta_avb0_algorithm": algo,
        "lp_metadata_preservation_not_yet_verified": True,
        "new_super_built": False, "new_vbmeta_built": False,
        "flash_ready": False
    })
    raw.unlink()  # Report only: do not upload source or modified images.
    print("Stock super/vbmeta audit complete - no images modified and no ZIP built.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("extract", "inspect"))
    ap.add_argument("--archive")
    ap.add_argument("--work", required=True)
    ap.add_argument("--reports", required=True)
    ap.add_argument("--tools", default=".tools/android-tools-static")
    args = ap.parse_args()
    if args.stage == "extract":
        if not args.archive:
            ap.error("extract requires --archive")
        extract(args)
    else:
        inspect(args)

if __name__ == "__main__":
    main()
