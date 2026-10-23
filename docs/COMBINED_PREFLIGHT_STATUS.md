# Combined preflight — review status

This repository now contains `.github/workflows/combined-preflight.yml`, `scripts/combined_preflight.py`, and `config/first-pass-33.txt`.

## Already verified against the earlier successful APK artifact
- All 33 selected APK paths exist in the MIUI 14 Global original inventory.
- APK UID/GID: 0:0; mode: 0644; SELinux label: u:object_r:system_file:s0.
- Affected partitions: product_a (23), system_a (9), system_ext_a (1).
- The original firmware uses EROFS and contains a populated, smaller `system_b` image.

## Current limitations — DO NOT treat as flash clearance
- The new combined workflow has **not yet run successfully**.
- Its current AVB-bounds loop incorrectly compares the smaller `system_b` against `system_a`'s descriptor and can emit a false failure. Correct this distinction before interpreting the report.
- Audit results are read-only. They cannot prove rebuilt UID/GID, SELinux labels, capabilities, compression settings, AVB validity, or boot compatibility.
- No modified `super.img`, altered vbmeta, or automatic flashing mechanism has been produced.
- Stock AVB descriptors have hashtree coverage for `product`, `system`, and `system_ext`; modifying these partitions requires a separately evaluated, compatible verified-boot strategy.

The existing `Redmi Pad APK inventory` and `Redmi Pad vbmeta audit` workflows were completed successfully in earlier GitHub Actions runs. The new combined preflight is a separate, unvalidated audit.
