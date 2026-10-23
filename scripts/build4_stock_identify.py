#!/usr/bin/env python3
"""Read-only Build 4 target identification on the untouched Xiaomi fastboot ROM."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from inventory import ROOT, NAME, MD5, TOOLS, sha
from combined_preflight import extract_archive, SUPER_RAW_SIZE, apk_identity
from erofs_trial import SOURCE_SUPER_SHA256, run_checked, mount_readonly, find_aapt

REPORT=ROOT/"reports-build4-preflight"
REPORT.mkdir(exist_ok=True)
TARGETS = {
    "Cast": ("product_a","/app/MiLinkGlobal/MiLinkGlobal.apk"),
    "Cloud backup": ("product_a","/priv-app/MIUICloudBackupGlobal/MIUICloudBackupGlobal.apk"),
    "Find Device": ("system_ext_a","/priv-app/FindDevice/FindDevice.apk"),
    "Frequent phrases": ("product_a","/app/MIUIFrequentPhrase/MIUIFrequentPhrase.apk"),
    "Mi Share": ("product_a","/priv-app/MIShareGlobal/MIShareGlobal.apk"),
    "MiCloudSync": ("product_a","/app/MIUIMiCloudSync/MIUIMiCloudSync.apk"),
    "Recording assistant": ("system_a","/system/app/MiuiAudioMonitor/MiuiAudioMonitor.apk"),
    "Service & Feedback": ("product_a","/priv-app/MIServiceGlobalPad/MIServiceGlobalPad.apk"),
    "Sim Toolkit": ("system_a","/system/priv-app/Stk1/Stk1.apk"),
    "Work setup": ("system_a","/system/priv-app/ManagedProvisioning/ManagedProvisioning.apk"),
    "Xiaomi Account": ("product_a","/app/MIUIXiaomiAccountGlobal/MIUIXiaomiAccountGlobal.apk"),
    "Xiaomi Cloud": ("product_a","/app/MIUICloudServiceGlobal/MIUICloudServiceGlobal.apk")
}
def main():
    with tempfile.TemporaryDirectory(prefix="yunluo-build4-stock-identify-") as d:
        wd=Path(d);arch=wd/NAME
        subprocess.run(["python3",str(ROOT/"scripts/download.py"),
                        "--output",str(arch),
                        "--report",str(REPORT/"download.json")],check=True)
        if sha(arch,"md5")!=MD5:
            raise RuntimeError("Stock archive MD5 mismatch")
        source,_=extract_archive(arch,wd)
        arch.unlink()
        raw=wd/"super.raw.img"
        with source.open("rb") as s:
            sparse=s.read(4)==bytes.fromhex("3aff26ed")
        if sparse:
            run_checked(TOOLS/"simg2img",source,raw)
        else:
            source.rename(raw)
        if raw.stat().st_size!=SUPER_RAW_SIZE or sha(raw)!=SOURCE_SUPER_SHA256:
            raise RuntimeError("Original super.img SHA256 mismatch")
        aapt=find_aapt();results=[];apex=[]
        for part in ("product_a","system_a","system_ext_a"):
            targetdir=wd/(part+"-unpacked");targetdir.mkdir()
            run_checked(TOOLS/"lpunpack","--slot=0","--partition="+part,raw,targetdir)
            fs=targetdir/(part+".img")
            mount=wd/(part+"-mounted")
            mount_readonly(fs,mount)
            try:
                for label,(p,path) in TARGETS.items():
                    if p!=part:continue
                    apk=mount/path.lstrip("/")
                    if not apk.is_file():
                        raise RuntimeError(f"Original APK missing for {label}: {part}:{path}")
                    pkg,_=apk_identity(aapt,apk)
                    results.append(dict(label=label,partition=part,apk=path,
                                        folder=str(Path(path).parent),package_id=pkg))
                for top in (mount/"apex",mount/"system"/"apex"):
                    if top.is_dir():
                        for entry in sorted(top.iterdir()):
                            if "broadcast" in entry.name.lower() or "adservices" in entry.name.lower():
                                apex.append(dict(partition=part,source_path="/"+str(entry.relative_to(mount)),
                                                 bytes=entry.stat().st_size if entry.is_file() else None,
                                                 is_directory=entry.is_dir()))
            finally:
                subprocess.run(["umount",str(mount)],check=True)
        if len(results)!=12:raise RuntimeError("Expected 12 identified apps")
        (REPORT/"stock-12-apk-targets.json").write_text(json.dumps(results,indent=2)+"\n")
        (REPORT/"cellbroadcast-apex-source.json").write_text(json.dumps(apex,indent=2)+"\n")
        print(json.dumps(dict(source_verified=True,targets=results,apex_candidates=apex),indent=2),flush=True)

if __name__=="__main__":
    main()
