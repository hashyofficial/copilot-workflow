#!/usr/bin/env python3
"""Build 5 exact Gallery target and signed KernelSU Next manager installation."""
import hashlib
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import subprocess

from combined_preflight import apk_identity
from erofs_trial import compare_trees,tree_map
from inventory import sha

GALLERY_LOCATION="product_a:/priv-app/Gallery_T_Global/Gallery_T_Global.apk"
MANAGER_PATH="/system/app/KernelSUNextSpoofed/KernelSUNextSpoofed.apk"
MANAGER_PACKAGE="kqvdie.zeykvw.hpbcyd"
MANAGER_VERSION="v3.4.2-spoofed"
MANAGER_SHA256="e27ad21204e8f58a4268c41725de97341c62a2f4acca7fa4dda256e9d7863d01"
MANAGER_SIZE=16684355
MANAGER_ASSET="KernelSU_Next_v3.4.2-spoofed_33355-release.apk"

def targets_from_build4():
    from pack_super_build4 import build4_targets
    original,packages,protected,added=build4_targets()
    if GALLERY_LOCATION in original or GALLERY_LOCATION in protected:
        raise RuntimeError("Gallery already removed/protected")
    part,path=GALLERY_LOCATION.split(":",1)
    pp=PurePosixPath(path)
    if (part,str(pp.parent))!=("product_a","/priv-app/Gallery_T_Global"):
        raise RuntimeError("Gallery folder map unexpected")
    trial={**original,GALLERY_LOCATION:(part,pp)}
    if len(trial)!=108 or len(set((p,q.parent) for p,q in trial.values()))!=108:
        raise RuntimeError("Build 5 requires exactly 108 distinct folders")
    return trial,packages,protected,{**added,GALLERY_LOCATION:(part,pp)}

def verify_apk(apk,aapt):
    apk=Path(apk)
    if not apk.is_file() or apk.stat().st_size!=MANAGER_SIZE or sha(apk)!=MANAGER_SHA256:
        raise RuntimeError("Official spoofed manager APK SHA256/size mismatch")
    observed,_=apk_identity(aapt,apk)
    if observed!=MANAGER_PACKAGE:
        raise RuntimeError("Official manager package ID mismatch: "+observed)

def is_injected(path):
    root=MANAGER_PATH.rsplit("/",1)[0]
    return path==root or path.startswith(root+"/")

def stage_apk(original_mount,staging,apk,aapt,before):
    verify_apk(apk,aapt)
    if staging.exists():raise RuntimeError("Staging directory already exists")
    staging.mkdir(parents=True)
    subprocess.run(["cp","-a","--reflink=auto",str(original_mount)+"/.",str(staging)+"/"],check=True)
    installed=staging/MANAGER_PATH.lstrip("/")
    if installed.exists():raise RuntimeError("KernelSU manager path already exists in original image")
    parent=installed.parent
    root_apps=staging/"system/app"
    if not root_apps.is_dir():raise RuntimeError("Stock system app directory is missing")
    example_dirs=sorted(x for x in root_apps.iterdir() if x.is_dir() and not x.is_symlink())
    if not example_dirs:raise RuntimeError("No original system app directory for SELinux label")
    example_apks=sorted(x for x in root_apps.rglob("*.apk") if x.is_file() and not x.is_symlink())
    if not example_apks:raise RuntimeError("No original system APK for SELinux label")
    ctx_dir=os.getxattr(example_dirs[0],"security.selinux")
    ctx_apk=os.getxattr(example_apks[0],"security.selinux")
    parent.mkdir(mode=0o755)
    shutil.copyfile(apk,installed)
    for path,mode,label in [(parent,0o755,ctx_dir),(installed,0o644,ctx_apk)]:
        os.chown(path,0,0)
        os.chmod(path,mode)
        os.setxattr(path,"security.selinux",label)
    # Creating the new subdirectory changes /system/app's mtime.
    # Restore it exactly; all original filesystem paths must remain unchanged.
    if "/system/app" not in before:raise RuntimeError("Missing original /system/app metadata")
    parent_stat=root_apps.stat()
    os.utime(root_apps,ns=(parent_stat.st_atime_ns,before["/system/app"]["mtime_ns"]))
    staged=tree_map(staging)
    original_only={k:v for k,v in staged.items() if not is_injected(k)}
    diff=compare_trees(before,original_only,[])
    if not diff["passed"]:
        raise RuntimeError("System staging copy changed original paths or metadata: "+
                           str({k:diff[k][:3] for k in ["missing_retained","different_retained","unexpected_paths"]}))
    return {"image_path":MANAGER_PATH,"android_package_id":MANAGER_PACKAGE,
            "version":MANAGER_VERSION,"apk_sha256":MANAGER_SHA256,
            "apk_bytes":MANAGER_SIZE,"official_release_asset":MANAGER_ASSET,
            "directory_selinux":ctx_dir.decode().rstrip("\0"),
            "apk_selinux":ctx_apk.decode().rstrip("\0")}

def verify_installed(mount,apk_info,aapt):
    app=mount/MANAGER_PATH.lstrip("/")
    if not app.is_file() or app.is_symlink() or sha(app)!=MANAGER_SHA256:
        raise RuntimeError("New manager APK missing or SHA256 differs in repacked EROFS")
    observed,_=apk_identity(aapt,app)
    if observed!=MANAGER_PACKAGE:
        raise RuntimeError("Rebuilt APK package identity mismatches official upstream")
    for path,mode,ctx in [
        (app.parent,0o755,apk_info["directory_selinux"]),
        (app,0o644,apk_info["apk_selinux"])
    ]:
        st=path.stat()
        if st.st_uid or st.st_gid or stat.S_IMODE(st.st_mode)!=mode:
            raise RuntimeError("Wrong manager system app owner/mode: "+str(path))
        if os.getxattr(path,"security.selinux").decode().rstrip("\0")!=ctx:
            raise RuntimeError("Manager SELinux label did not survive EROFS rebuild")
    return True
