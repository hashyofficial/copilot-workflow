#!/usr/bin/env python3
"""Publish already-built yunluo slot-A sparse super image from GitHub to R2.

Reads seven existing GitHub artifact parts without creating a second 4.85GB file.
No firmware rebuilding, vbmeta modification, or device operations.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

EXPECTED_BUILD_SHA256 = "f58f417a6badfa61d7d5a3d052bfcecc6647da9248441431fe7ae7d9fb59a8ce"
EXPECTED_TOTAL_BYTES = 4846549456
EXPECTED_COUNT = 7
CHUNK = 8 * 1024 * 1024

def fail(message):
    raise RuntimeError(message)

def cli(*args, capture=False):
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else None

def verify(source):
    manifest_path = source / "manifest.json"
    if not manifest_path.is_file():
        fail("Source GitHub artifact lacks manifest.json")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("slot") != "a" or manifest.get("model") != "yunluo":
        fail("Source artifact is not the expected yunluo slot-A build")
    if manifest.get("sparse_sha256") != EXPECTED_BUILD_SHA256:
        fail("Source artifact sparse SHA-256 differs from the tested build")
    if manifest.get("lp_metadata_preserved") is not True or manifest.get("other_regions_unchanged") is not True:
        fail("Source artifact not marked as fully checked")
    parts = manifest.get("parts", [])
    if len(parts) != EXPECTED_COUNT:
        fail("Unexpected number of sparse image parts")
    total = 0
    combined = hashlib.sha256()
    for idx, part in enumerate(parts):
        name = "super.sparse.img.part-%03d" % idx
        if part["file"] != name:
            fail("Unexpected part order/filename: " + str(part["file"]))
        path = source / name
        if path.stat().st_size != part["bytes"]:
            fail("Source part byte size mismatch: " + name)
        h = hashlib.sha256()
        with path.open("rb") as f:
            while data := f.read(CHUNK):
                h.update(data)
                combined.update(data)
                total += len(data)
        if h.hexdigest() != part["sha256"]:
            fail("Source part SHA-256 mismatch: " + name)
    if total != EXPECTED_TOTAL_BYTES or combined.hexdigest() != EXPECTED_BUILD_SHA256:
        fail("Combined image bytes/checksum differ from successful GitHub build")
    return parts, manifest_path

def main():
    source = Path(os.environ["SOURCE_DIR"]).resolve()
    account = os.environ["R2_ACCOUNT_ID"].strip()
    bucket = os.environ["R2_BUCKET"].strip()
    key = os.environ["R2_OBJECT_KEY"].strip().lstrip("/")
    if not re.fullmatch(r"[a-fA-F0-9]{32}", account):
        fail("Invalid Cloudflare account ID")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket):
        fail("Invalid R2 bucket name")
    if not key or ".." in key.split("/") or "\n" in key or "\r" in key:
        fail("Invalid R2 object key")
    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        fail("Missing GitHub Actions R2 credentials secrets")
    if not source.is_dir():
        fail("GitHub artifact was not downloaded")

    parts, manifest = verify(source)
    endpoint = f"https://{account}.r2.cloudflarestorage.com"
    dest = f"s3://{bucket}/{key}"
    print(f"All {len(parts)} image parts verified: {EXPECTED_TOTAL_BYTES} bytes.")
    print("Uploading combined sparse image to R2 with multipart transfer...", flush=True)
    args = ["aws", "s3", "cp", "-", dest, "--endpoint-url", endpoint,
            "--region", "auto", "--expected-size", str(EXPECTED_TOTAL_BYTES),
            "--no-progress", "--content-type", "application/octet-stream",
            "--metadata", "sha256="+EXPECTED_BUILD_SHA256]
    proc = subprocess.Popen(args, stdin=subprocess.PIPE)
    try:
        assert proc.stdin is not None
        for part in parts:
            with (source / part["file"]).open("rb") as stream:
                while data := stream.read(CHUNK):
                    proc.stdin.write(data)
        proc.stdin.close()
    except Exception:
        proc.kill()
        proc.wait()
        raise
    if proc.wait() != 0:
        fail("R2 upload failed; no success reported")

    header = json.loads(cli("aws", "s3api", "head-object", "--bucket", bucket,
                            "--key", key, "--endpoint-url", endpoint,
                            "--region", "auto", capture=True))
    if header["ContentLength"] != EXPECTED_TOTAL_BYTES:
        fail("R2 object size differs from expected upload")
    if header.get("Metadata", {}).get("sha256") != EXPECTED_BUILD_SHA256:
        fail("R2 object checksum metadata missing")
    cli("aws", "s3", "cp", str(manifest), dest + ".manifest.json",
        "--endpoint-url", endpoint, "--region", "auto", "--no-progress",
        "--content-type", "application/json")
    print(f"R2 upload verified: {dest}")
    print(f"Size: {EXPECTED_TOTAL_BYTES} bytes")
    print(f"SHA-256 verified locally before upload: {EXPECTED_BUILD_SHA256}")
    print("A manifest was uploaded as " + key + ".manifest.json")
    print("The R2 bucket remains private unless you enable a public hostname.")
    print("The image is NOT boot-tested and stock AVB is incompatible with it.")

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print("UPLOAD NOT CONFIRMED: " + str(ex), file=sys.stderr)
        sys.exit(1)
