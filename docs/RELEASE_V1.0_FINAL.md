# Release V 1.0 Final — Final Fastboot Image

**Redmi Pad (yunluo) | MIUI 14 Global | Android 13 | V14.0.4.0.TLYMIXM**

The first final release of the custom-debloated Redmi Pad fastboot firmware, based on Xiaomi's original `yunluo_global_images_V14.0.4.0.TLYMIXM_20231207.0000.00_13.0_global_4003dcb1a4.tgz` (source MD5 `4003dcb1a4db404e2768801fdb429c4a`).

**Status:** Build 5 passed offline image, checksum and package checks. The project owner subsequently flashed it and confirmed that it booted successfully on the Redmi Pad. The release remains device-specific; this does not constitute a guarantee for every device or flashing environment.

## Changelog

- **Build 1:** Removed 24 complete preinstalled-app directories.
- **Build 2:** Removed 42 additional complete app directories (66 total).
- **Build 3:** Removed 27 more complete app directories (93 total).
- **Build 4:** Removed 14 additional complete app directories (107 total); Build 4 was independently confirmed booting.
- **Build 5 — final:** Removed the entire `product_a:/priv-app/Gallery_T_Global/` folder (108 total), *including its APK and any other files in that dedicated folder*. No new system APKs were installed.
- Protected components retained, including the prior Provision, StatementService and LPPeService exceptions. Cell Broadcast Service APEX was left unchanged.
- Rebuilt the slot-A `super.img` from independently checksum-verified original Xiaomi stock images and preserved logical-partition metadata, extents, and all non-target super regions.
- Replaced the original `images/vbmeta.img` with a modified main AVB0 image with **flags = 3** (verification and verity checks disabled). This invalidates Xiaomi's original cryptographic signature and **requires an unlocked bootloader**.
- Updated *only* the corresponding checksum entries in `images/crclist.txt` (`vbmeta_a`) and `images/sparsecrclist.txt` (`super`).
- Kept the rest of the Xiaomi fastboot firmware intact, including original `flash_all.sh`, original scatter `.txt`/`.xml` partition descriptions, and other images such as `vbmeta_system.img` and `vbmeta_vendor.img`.
- Verified SHA-256 hashes for Build 5's sparse super image, patched vbmeta image, the complete fastboot firmware ZIP, and the release's uploaded transfer segments.

## Verified final image

`yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip`

- **Complete ZIP size:** `3,697,320,245` bytes (about 3.70 GB).
- **Complete ZIP SHA-256:** `c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c`
- **Patched vbmeta SHA-256:** `11322edca2df064b4d7b790bd2fb278c6083e8bec8cd47f4d5774d34ae3e4af9`
- **Patched vbmeta AVB0 flags:** `3`.

## Download: ONE full ZIP (non-expiring Actions-artifact alternative)

GitHub Release attachments are limited to files under **2 GiB**, so this **3.70 GB** complete ZIP cannot be attached directly to a GitHub Release. The complete, **unsplit** ZIP is hosted at GitHub Container Registry (GHCR) instead:

```text
ghcr.io/hashyofficial/redmi-pad-yunluo-miui-project-firmware:v1.0
```

GitHub Actions successfully verified the ZIP SHA-256 and internal files, pushed the **one full 3,697,320,245-byte ZIP** into this package, and verified its one-blob registry manifest. A separate anonymous access check also succeeded.

Install the [official ORAS CLI](https://oras.land/docs/installation/) and run:

```bash
oras pull ghcr.io/hashyofficial/redmi-pad-yunluo-miui-project-firmware:v1.0
echo "c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c  yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip" | sha256sum -c -
```

Alternatively, download and run `download_full_zip.sh` from [Release v1.0](https://github.com/hashyofficial/copilot-workflow/releases/tag/v1.0) after installing ORAS. **Do not mistake GitHub's automatically generated repository "Source code (zip)" for the full firmware.**

GHCR packages have no automatic GitHub Actions artifact expiry date. Continued availability is subject to the owner retaining the package and GitHub hosting policies.

## Flashing warnings

**REDMI PAD (yunluo) ONLY. UNLOCKED BOOTLOADER REQUIRED. DO NOT RUN `flash_all_lock.sh` OR RELOCK THE BOOTLOADER.**

The unmodified Xiaomi `flash_all.sh` flashes `vbmeta.img` to `vbmeta_ab` and `super.img` to `super`, selects slot A and may erase/overwrite userdata and other partitions. Back up important data. Only use files after the checksum check reports success. This is an experimental device modification, even though this exact build has been reported to boot successfully.
