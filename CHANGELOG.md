# Changelog

## Release V1.0 Final — Fastboot Image (2026-10-23)

**Device:** Xiaomi Redmi Pad (codename `yunluo`)  
**Base:** MIUI 14 Global Stable `V14.0.4.0.TLYMIXM`, Android 13  
**Base firmware:** `yunluo_global_images_V14.0.4.0.TLYMIXM_20231207.0000.00_13.0_global_4003dcb1a4.tgz`  
**Source firmware MD5:** `4003dcb1a4db404e2768801fdb429c4a`  
**Status:** Successfully booted on the project's Redmi Pad. Offline rebuild, firmware package, and checksum validation passed. No claim of broad device compatibility.

### Changes

- **108 complete preinstalled application directories removed**, including the APK and other files within each selected folder:
  - Build 1: 24 folders.
  - Build 2: 42 additional folders (66 cumulative).
  - Build 3: 27 additional folders (93 cumulative).
  - Build 4: 14 additional folders (107 cumulative).
  - Build 5: **Gallery** (`product_a:/priv-app/Gallery_T_Global/`) removed as one additional complete folder (108 cumulative).
- **No extra APKs installed.** In particular, there is **no KernelSU Next app** in this final release.
- Retained the specifically protected `LPPeService`, `StatementService`, and `Provision` packages. Cell Broadcast Service APEX and unselected logical partitions were kept as they were in the original Xiaomi ROM.
- Rebuilt the modified logical-partition filesystems within **`images/super.img`**, preserving the original dynamic-partition layout and metadata for slots.
- Patched stock **`images/vbmeta.img`** (AVB0 header flags `0 → 3`) to disable verification and hashtree checking. Its original signature is no longer valid; an **unlocked bootloader is required**.
- Updated **`images/crclist.txt`** (the `vbmeta_a` CRC32 row) and **`images/sparsecrclist.txt`** (the `super` sparse-image CRC32 values).
- Preserved stock **`flash_all.sh`**, which already flashes `vbmeta_ab` and `super`, plus the original scatter `.txt`/`.xml` partition definitions and all other original firmware images.
- Validated all firmware-partition references, source/image checksums, CRC values, source-file preservation, and the final ZIP.
- **Complete fastboot firmware** rather than a standalone `super.img`. For GitHub's per-asset size limit, the unchanged verified firmware ZIP is presented as **two equal-size chunks**. Rejoining them creates exactly the same ZIP that was successfully built and validated as Build 5.

### Download and extract (Linux)

Download both `.zip.001` and `.zip.002` assets **from this same V1.0 release**, along with `PARTS_SHA256.txt` and `V1_FINAL_SHA256.txt`. They are **two halves of ONE ZIP**, not independently extractable ZIPs.

```bash
ZIP="Redmi_Pad_Yunluo_MIUI14_V1.0_Final_Fastboot.zip"
sha256sum -c PARTS_SHA256.txt
cat "$ZIP.001" "$ZIP.002" > "$ZIP"
sha256sum -c V1_FINAL_SHA256.txt
unzip -t "$ZIP"
unzip "$ZIP"
```

**Expected complete ZIP SHA-256 (same already-verified Build 5 archive):**
`c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c`.

For convenience, the release also provides `EXTRACT_LINUX.sh` to join, validate and extract both halves in one step: `bash EXTRACT_LINUX.sh`.

### Flashing and safety

- **Redmi Pad (`yunluo`) only.** This is not firmware for another Xiaomi tablet.
- Keep the **bootloader unlocked**. Never run `flash_all_lock.sh` or re-lock with this modified firmware.
- The original `flash_all.sh` overwrites userdata and other partitions. **Back up your files before flashing.**
- Verify the ZIP checksum **before** using any flash script. The project's Redmi Pad booted successfully with these firmware contents, but installation on other devices and configurations is not guaranteed.
- This is a community-modified project and is not an official Xiaomi firmware release.

### Asset retention

GitHub **Release assets** have **no scheduled GitHub Actions artifact expiration**. They stay downloadable while the repository and release assets are kept online; they can still be removed by the repository owner or GitHub under its policies.

### Provenance

The original five-part Build 5 Release was created by [successful GitHub Actions run #39970696830](https://github.com/hashyofficial/copilot-workflow/actions/runs/39970696830). This V1.0 package **does not rebuild or modify the firmware bytes**; it verifies the five original ZIP chunks, reconstructs the identical full ZIP, and splits it into two download halves.
