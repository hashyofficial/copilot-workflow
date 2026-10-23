# Redmi-Pad-Yunluo-Miui-Project

**Community-maintained debloated fastboot firmware for Xiaomi Redmi Pad (codename: `yunluo`).**

## Release V 1.0 Final — Final Fastboot Image

**Base firmware:** MIUI 14 Global `V14.0.4.0.TLYMIXM` · Android 13.  
**Status:** successfully boot-tested on the owner's Redmi Pad; full ZIP checksum and firmware structure verified offline.  
**Latest stable release:** [v1.0 Final](https://github.com/hashyofficial/copilot-workflow/releases/tag/v1.0)  
**Full changelog:** [RELEASE_NOTES_V1.md](RELEASE_NOTES_V1.md)

### Changes in the final firmware

Build 5 is based on fresh Xiaomi stock firmware, preserving the 107 whole-folder app removals from Builds 1–4 and adding the Gallery directory as removal #108. **All 108 selected app folders and their contents are removed**, with no new APKs added.

The firmware bundle contains the rebuilt `images/super.img` and patched `images/vbmeta.img` (AVB flags = 3), and recalculated `crclist.txt` and `sparsecrclist.txt` entries. Stock flash scripts, scatter files, and all remaining firmware images are preserved. Protected Provision, StatementService, LPPeService, and Cell Broadcast Service remain untouched.

### Download ONE complete ZIP

**Filename:** `yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip`

**Size:** 3,697,320,245 bytes (3.44 GiB)  
**SHA-256:**
```text
c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c
```

GitHub Releases restricts individual asset files to under 2 GiB, so the **single full ZIP** is hosted as a **single OCI artifact** in GitHub Container Registry instead of temporary GitHub Actions artifacts. No multipart files are attached to **v1.0 Final**.

With [ORAS](https://oras.land/docs/installation/) installed:
```bash
oras pull ghcr.io/hashyofficial/redmi-pad-yunluo-miui-project-firmware:v1.0
sha256sum -c ZIP_SHA256.txt
unzip -t yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip
```

Or download `download_full_zip.sh` and `ZIP_SHA256.txt` from the [v1.0 Final GitHub Release](https://github.com/hashyofficial/copilot-workflow/releases/tag/v1.0), then run `bash download_full_zip.sh`.

**Important:** GitHub creates container packages with private visibility initially. For anonymous download, the owner needs to set [the firmware container package](https://github.com/users/hashyofficial/packages/container/redmi-pad-yunluo-miui-project-firmware) to **Public** from its package settings.

### Flashing safety

- **Device:** Xiaomi Redmi Pad `yunluo` only; confirm codename and base firmware.
- **Bootloader:** must remain **unlocked**. Do not use `flash_all_lock.sh` or relock the bootloader.
- **Data:** Xiaomi's original `flash_all.sh` may erase personal data. Back up first.
- **Integrity:** check ZIP SHA-256 before extraction or flashing.
- **Source:** the custom firmware is unofficial and not affiliated with Xiaomi.

### Build notes

All source reconstruction, APK-folder exclusion checks, EROFS integrity validation, preservation of logical partition metadata, sparse image verification, and fastboot archive repacking are implemented in `scripts/` and `.github/workflows/`. The final release is promoted from successful **Build 5 Gallery-only** and intentionally contains **no injected KernelSU manager APK**.

Original Xiaomi firmware MD5: `4003dcb1a4db404e2768801fdb429c4a`.
