# Combined preflight — review status

This repository now contains `.github/workflows/combined-preflight.yml`, `scripts/combined_preflight.py`, and `config/first-pass-33.txt`.

## Already verified against the earlier successful APK artifact
- All 33 selected APK paths exist in the MIUI 14 Global original inventory.
- APK UID/GID: 0:0; mode: 0644; SELinux label: u:object_r:system_file:s0.
- Affected partitions: product_a (23), system_a (9), system_ext_a (1).
- The original firmware uses EROFS and contains a populated, smaller `system_b` image.

## Current limitations — DO NOT treat as flash clearance
- The first combined preflight was triggered by commit `5436d71` and **succeeded**: [Actions run #39908359257](https://github.com/hashyofficial/copilot-workflow/actions/runs/39908359257). The run found 33 candidates, 319 APKs, 8 source EROFS images, 6,590 baseline metadata entries, 49 config references, and 0 structural blockers. Its status remains `flash_ready: false`. See [the detailed findings](COMBINED_PREFLIGHT_FINDINGS.md).
- The inactive smaller `system_b` is explicitly marked NOT_ASSESSED for the A-slot AVB bounds comparison (fixed in commit `4fd8d8e`). Its own source EROFS integrity is checked separately.
- Audit results are read-only. They cannot prove rebuilt UID/GID, SELinux labels, capabilities, compression settings, AVB validity, or boot compatibility.
- No modified `super.img`, altered vbmeta, or automatic flashing mechanism has been produced.
- Stock AVB descriptors have hashtree coverage for `product`, `system`, and `system_ext`; modifying these partitions requires a separately evaluated, compatible verified-boot strategy.

The existing `Redmi Pad APK inventory` and `Redmi Pad vbmeta audit` workflows were completed successfully in earlier GitHub Actions runs. The combined preflight is now also successful as a **source audit**, not as a rebuild or flash validation.

## Combined checks included in the new run
- APK identities, manifest-declared required libraries, and surviving-package cross references.
- Exact location validation for all 33 candidates, with a report of non-APK metadata and additional APKs in their installation directories.
- Filesystem identification, read-only EROFS `fsck.erofs` checks, and full source metadata snapshot for potentially affected partitions.
- 3 original vbmeta headers, AVB hashtree bounds for the relevant A-slot partitions, and LP metadata from two slots.
- Explicit `flash_ready: false` in the output regardless of a successful inspection.
- Raw original firmware, super, and vbmeta binaries are not committed or uploaded.
