# HyperOS 1 Global - Redmi Pad (yunluo)

This workspace is **isolated from the boot-confirmed MIUI 14 Build 5 project**. We are staying in the same repository to preserve the working history and reusable verification logic.

## Pinned firmware
- HyperOS 1: OS1.0.9.0.ULYMIXM, Android 14, Global.
- Fastboot file: yunluo_global_images_OS1.0.9.0.ULYMIXM_20250416.0000.00_14.0_global_f8dbb84a10.tgz
- Published MD5: f8dbb84a10dc96a9d3ce9e78883e87f3
- Reference: https://xmfirmwareupdater.com/hyperos/yunluo/stable/OS1.0.9.0.ULYMIXM/

## Scope: super.img and vbmeta.img ONLY
- **No full-firmware ZIP, no reassembled release, no flashing or bootloader operations**.
- The proven MIUI 14 Build 5 implementation is the *methodological reference*: fresh verified Xiaomi source, extract original super, preserve LP metadata and non-target regions, rebuild EROFS with carefully audited exclusions, verify filesystem/metadata/round-trip and independent AVB checks.
- Do not copy the MIUI 14 hardcoded sector offsets, UUIDs, EROFS parameters, 108 removal paths, vbmeta hashes, CRC files, or flash scripts into Android 14.
- HyperOS needs a new app inventory and review of critical services. Never assume the same removals remain safe.
- When image-building work is enabled, the outputs will be **modified super.img, modified vbmeta.img, and integrity reports only**. Keep the bootloader unlocked for modified AVB images.

## First milestone: stock image preflight
A manually dispatched GitHub Actions workflow at ../hyperos-super-preflight.yml downloads and validates *clean HyperOS* firmware, extracts stock super.img/vbmeta.img, inspects both stock logical partition slots and the AVB0 header, and uploads **only small reports**.

GitHub Actions discovers YAML entrypoints only immediately inside .github/workflows, which is why the entrypoint is alongside this folder and the HyperOS script/configuration remain inside it.

This is **not yet a modified HyperOS super.img build**. We must validate the fresh Android 14 partition extents and file systems before making any changes. Do not flash anything from the preflight.

Reference: https://github.com/hashyofficial/copilot_workflow/actions/runs/39970696830 (MIUI 14 Build 5 successful super/vbmeta packaging run, subsequently confirmed booting by owner).
