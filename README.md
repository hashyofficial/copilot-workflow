# Redmi-Pad-Yunluo-Miui-Project

**Release V 1.0 Final — Final Fastboot Image**  
**Xiaomi Redmi Pad (`yunluo`) · MIUI 14 Global V14.0.4.0.TLYMIXM · Android 13**

**[Download Release V 1.0 Final](https://github.com/hashyofficial/copilot-workflow/releases/tag/v1.0)** · **[Full changelog](RELEASE_NOTES_V1.md)**

The original Build 5 complete fastboot ZIP passed offline integrity tests and **booted successfully on the project owner's real Redmi Pad**.

## Changelog

- **108 entire preinstalled-app directories removed:** Build 1 (24), Build 2 (+42), Build 3 (+27), Build 4 (+14), and Build 5 (+1 complete **Gallery_T_Global** folder).
- **No APKs added** in the final firmware, including no KernelSU manager.
- Preserved Cell Broadcast Service APEX and previously protected services (`LPPeService`, `StatementService`, `Provision`).
- Rebuilt `images/super.img` with the original Xiaomi logical-partition layout intact.
- Modified main `images/vbmeta.img` with **AVB flags = 3** to disable verification and verity (unlocked bootloader required).
- Updated `images/crclist.txt` and `images/sparsecrclist.txt` for the two changed images.
- Kept original `flash_all.sh`, scatter XML/TXT, and all other firmware images unchanged.

## Get ONE complete firmware ZIP

The verified firmware ZIP is **3,697,320,245 bytes (3.70 GB)**, too large for GitHub's **2 GiB limit per Release attachment**. The exact complete ZIP is therefore published as a **single public GitHub Container Registry (GHCR) artifact** for the stable v1.0 release — **not multipart**, and not a short-lived GitHub Actions artifact.

With the [ORAS CLI](https://oras.land/docs/installation/) installed:

```bash
oras pull ghcr.io/hashyofficial/redmi-pad-yunluo-miui-project-firmware:v1.0
echo "c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c  yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip" | sha256sum -c -
```

This downloads **one normal firmware ZIP**, containing the entire Xiaomi fastboot folder with `flash_all.sh`, `images/super.img`, and `images/vbmeta.img`. A Linux convenience script, `download_full_zip.sh`, and `ZIP_SHA256.txt` are available directly from the [v1.0 Release](https://github.com/hashyofficial/copilot-workflow/releases/tag/v1.0).

**Complete ZIP SHA-256:** `c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c`.

The GHCR package has passed anonymous read-access and manifest hash/size checks. GitHub Packages do not have the automatic expiry of Actions artifacts, although packages and release assets can still be removed by repository owners or GitHub.

## Flashing warnings

**Only for Redmi Pad `yunluo`. Keep the bootloader unlocked. Never run `flash_all_lock.sh` or relock the bootloader.** The original `flash_all.sh` can erase userdata. Back up important files before flashing. This is a community-modified firmware, not an official Xiaomi release.

## Project provenance

The final ZIP is the **same checksum-verified Build 5 firmware** produced in [successful packaging run #39970696830](https://github.com/hashyofficial/copilot-workflow/actions/runs/39970696830). The [stable GHCR publishing run](https://github.com/hashyofficial/copilot-workflow/actions/runs/39978631837) reassembled that ZIP, tested its contents and SHA-256, and published it unchanged as one complete artifact.
