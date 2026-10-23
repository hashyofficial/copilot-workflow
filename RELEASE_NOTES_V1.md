# Release V 1.0 Final — Final Fastboot Image

**Redmi Pad (yunluo) · MIUI 14 Global · Android 13**  
**Base version:** `V14.0.4.0.TLYMIXM`  
**Release status:** Final, user-confirmed boot on Redmi Pad (unlocked bootloader)  
**Version:** `v1.0` — based on successfully booted Experimental Build 5 (Gallery-only)

## Changelog

- **Debloated 108 complete preinstalled application directories** across all five builds, with all APKs and other files inside each selected folder removed:
  - Build 1: 24 folders
  - Build 2: +42 folders (66 total)
  - Build 3: +27 folders (93 total)
  - Build 4: +14 folders (107 total)
  - Build 5: +1 folder — **Gallery** (`product_a:/priv-app/Gallery_T_Global/`) (108 total)
- **No new system APKs or root managers injected** into this final firmware.
- Kept previously protected services (Provision, StatementService and LPPeService) and the Cell Broadcast Service APEX intact.
- Rebuilt the verified slot-A `super.img` from the pinned, checksum-checked original Xiaomi fastboot firmware; logical partition geometry preserved.
- Replaced `images/vbmeta.img` with the patched top-level AVB image (**flags = 3**, verification and hashtree/verity disabled). **Bootloader must remain unlocked.**
- Recalculated the modified `vbmeta_a` entry in `images/crclist.txt` and the `super` sparse entries in `images/sparsecrclist.txt`.
- **Original `flash_all.sh` retained**: it already flashes `vbmeta_ab` using `images/vbmeta.img`, flashes `super` using `images/super.img`, and selects slot A.
- Original scatter `.txt`/`.xml`, all remaining firmware images, and other stock flashing files preserved.
- Full fastboot firmware verified offline (original firmware MD5, modified image SHA-256, ZIP integrity and all five-part source checks).
- **Boot successfully confirmed by the project owner on the actual Redmi Pad.**

## Download — ONE full ZIP (not multipart)

`yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip`  
**Size:** 3,697,320,245 bytes (approximately 3.44 GiB)  
**SHA-256:**
```text
c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c
```

GitHub Release asset files have a **2 GiB per-file limit**, so this 3.44 GiB ZIP cannot be attached directly to a GitHub Release. Instead, **the complete, unsplit ZIP is stored as ONE artifact in GitHub Container Registry**, alongside this versioned GitHub release. It is **not** a time-limited GitHub Actions artifact.

Container registry reference: `ghcr.io/hashyofficial/redmi-pad-yunluo-miui-project-firmware:v1.0`

Download as a single ZIP with the open-source ORAS CLI (see https://oras.land/docs/installation/):
```bash
oras pull ghcr.io/hashyofficial/redmi-pad-yunluo-miui-project-firmware:v1.0
sha256sum -c ZIP_SHA256.txt
unzip -t yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip
```

Or download `download_full_zip.sh` and `ZIP_SHA256.txt` from this release and run `bash download_full_zip.sh` after installing ORAS.

**Note:** Newly published GHCR packages default to private; the repository owner must switch this firmware package's visibility to **Public** in GitHub Packages settings for anonymous downloads. If a pull says unauthorized, check package visibility. GitHub does not guarantee indefinite hosting against owner deletion or service policy changes, but this package is not subject to GitHub Actions artifact expiry.

## Flashing and safety

- **Only for Xiaomi Redmi Pad `yunluo` / Android 13 MIUI base shown above.**
- **Unlocked bootloader required. Never use `flash_all_lock.sh` or relock the bootloader.**
- Check device codename, model and the firmware SHA-256 before flashing.
- The original Xiaomi `flash_all.sh` overwrites userdata and can erase your data; **back up first**.
- Although the exact image boots on the owner's device, no guarantee is given for other devices or modifications.
- This is a community-modified firmware, **not an official Xiaomi release**.

---

*Build 5 Gallery-only complete fastboot archive promoted to stable Release V 1.0 without changing its firmware contents.*
