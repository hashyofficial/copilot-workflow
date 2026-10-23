#!/usr/bin/env python3
"""Build 5: preserve all 107 Build 4 removals, plus exact Xiaomi Gallery folder.

There is NO APK installation in Build 5. The package is intentionally debloat-only.
"""
from pathlib import PurePosixPath

GALLERY_LOCATION = "product_a:/priv-app/Gallery_T_Global/Gallery_T_Global.apk"

def targets_from_build4():
    from pack_super_build4 import build4_targets
    original, expected_packages, protected, added = build4_targets()
    if GALLERY_LOCATION in original or GALLERY_LOCATION in protected:
        raise RuntimeError("Gallery already excluded or protected")
    partition, path = GALLERY_LOCATION.split(":", 1)
    pp = PurePosixPath(path)
    if (partition, str(pp.parent)) != ("product_a", "/priv-app/Gallery_T_Global"):
        raise RuntimeError("Unexpected Gallery source directory")
    targets = {**original, GALLERY_LOCATION: (partition, pp)}
    folders = [(part, apk.parent) for part, apk in targets.values()]
    if len(targets) != 108 or len(set(folders)) != 108:
        raise RuntimeError("Expected 108 unique complete APK folder removals")
    for i, (part, folder) in enumerate(folders):
        for other_part, other_folder in folders[i+1:]:
            if part == other_part and (folder in other_folder.parents or other_folder in folder.parents):
                raise RuntimeError("Nested app-directory deletion")
    if set(targets).intersection(protected):
        raise RuntimeError("Protected package targeted for removal")
    if len(added) != 14:
        raise RuntimeError("Build 4 inheritance did not include the original fourteen additional removals")
    return targets, expected_packages, protected, {**added, GALLERY_LOCATION: (partition, pp)}
