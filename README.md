# Redmi-Pad-Yunluo-Miui-Project

**Release V1.0 Final — Fastboot Image**  
Xiaomi Redmi Pad (`yunluo`) · **MIUI 14 Global `V14.0.4.0.TLYMIXM`** · Android 13

This community project provides a debloated full **fastboot firmware** package built from Xiaomi's verified original ROM. The author successfully booted the final Build 5 firmware on a Redmi Pad, after offline verification of the logical-partition contents, fastboot flashing files, and ZIP integrity.

**[Download V1.0 Final](https://github.com/hashyofficial/copilot-workflow/releases/tag/v1.0.0)** · **[Full changelog](CHANGELOG.md)**

## What changed?

- **108 complete preinstalled APK folders removed** (24 + 42 + 27 + 14 + **Gallery**). The complete `Gallery_T_Global` folder is excluded, not just its APK.
- **No APKs added** to the firmware; KernelSU Next is **not** included.
- The verified `images/super.img` contains the debloated logical-partition filesystems while retaining Xiaomi's dynamic-partition layout.
- `images/vbmeta.img` is patched with **AVB flags = 3**, disabling verification and dm-verity checks. The original signed AVB signature is invalidated, so the bootloader **must remain unlocked**.
- `images/crclist.txt` and `images/sparsecrclist.txt` include recomputed values for the modified images.
- `flash_all.sh`, both original scatter files and other firmware images are unchanged.
- Specifically retained: Cell Broadcast Service APEX, `LPPeService`, `StatementService` and `Provision`.

## Download

GitHub has a per-asset size limit, so the final complete ZIP is published in **two halves**, each under 2 GB:

```text
Redmi_Pad_Yunluo_MIUI14_V1.0_Final_Fastboot.zip.001
Redmi_Pad_Yunluo_MIUI14_V1.0_Final_Fastboot.zip.002
PARTS_SHA256.txt
V1_FINAL_SHA256.txt
EXTRACT_LINUX.sh
V1_DOWNLOAD_MANIFEST.json
```

Download **both** ZIP halves and the checksum files into the same directory. The two halves are **not independent ZIPs**: they form **one complete full-firmware ZIP** when joined.

On Linux:

```bash
bash EXTRACT_LINUX.sh
```

The included script checks both parts, joins them, verifies the complete ZIP and extracts all firmware files. Alternatively:

```bash
ZIP="Redmi_Pad_Yunluo_MIUI14_V1.0_Final_Fastboot.zip"
sha256sum -c PARTS_SHA256.txt
cat "$ZIP.001" "$ZIP.002" > "$ZIP"
sha256sum -c V1_FINAL_SHA256.txt
unzip "$ZIP"
```

**Final full ZIP SHA-256:** `c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c`

**Original vendor ROM MD5:** `4003dcb1a4db404e2768801fdb429c4a`

The V1.0 release uses GitHub **Release assets**, not short-lived GitHub Actions artifacts. There is **no preset expiration date** for these release downloads, although repository owners or GitHub can remove them later.

## Important flashing warnings

**Only for Xiaomi Redmi Pad (`yunluo`); an unlocked bootloader is required.** Check the product/device identity before flashing. **Never use `flash_all_lock.sh` or relock the bootloader with this modified firmware.**

The stock `flash_all.sh` writes the images from the extracted firmware to their intended partitions (`super`, `vbmeta_ab`, etc.) and **overwrites userdata**. Back up everything important before flashing. The final firmware booted on the project's device, but compatibility on other devices/configurations is not guaranteed.

## Development provenance

V1.0 uses **exactly the same verified firmware ZIP bytes** as the [successful Build 5 packaging release](https://github.com/hashyofficial/copilot-workflow/releases/tag/yunluo-miui14-build5-complete-firmware) from [Build 5 run #39970696830](https://github.com/hashyofficial/copilot-workflow/actions/runs/39970696830). V1.0 simply redistributes the same complete ZIP using **two equal-sized chunks** and improved instructions; there are no additional image or firmware changes.

This is an independent community-modified fastboot ROM, not an official Xiaomi release.
