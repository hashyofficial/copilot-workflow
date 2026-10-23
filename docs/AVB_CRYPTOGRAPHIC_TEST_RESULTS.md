# Redmi Pad yunluo — cryptographic AVB results

Verified by [GitHub Actions run #39916083642](https://github.com/hashyofficial/copilot-workflow/actions/runs/39916083642), [artifact #12485127560](https://github.com/hashyofficial/copilot-workflow/actions/runs/39916083642/artifacts/12485127560), on Xiaomi Global `V14.0.4.0.TLYMIXM`.

This is an actual cryptographic and AOSP avbtool verification, not merely structural analysis.

| Test | Observed |
|---|---|
| Original firmware MD5 | Matched Xiaomi stock checksum |
| Original `vbmeta.img` SHA256_RSA2048 signature | Valid |
| Original `vbmeta_system.img` SHA256_RSA2048 signature | Valid |
| Original `vbmeta_vendor.img` SHA256_RSA2048 signature | Valid |
| `avbtool verify_image` against stock `vbmeta_system.img` and stock `product.img`, `system.img`, `system_ext.img` | Exit 0, all verified |
| Repeat with 18 app folders excluded from rebuilt `product_a` | Exit 1, `hashtree of .../product.img does not match descriptor` |
| Repeat with 6 app folders excluded from rebuilt `system_a` | Exit 1, `hashtree of .../system.img does not match descriptor` |
| Modified vbmeta image produced | No |
| Complete modified `super.img` produced | No |
| Device boot-tested | No |

**Conclusion:** The stock Xiaomi AVB signatures and original hashtrees are valid. The modified EROFS content deliberately differs, so **the stock hashtree descriptors do not verify either rebuilt partition**. This tests the exact 24-folder exclusion plan using source and rebuilt EROFS bytes. It does not predict the device's behavior with any future alternate AVB configuration.

The bootloader-unlocked and slot-A state was reported by the user, not independently measured. No flashing took place. See `scripts/avb_rebuild_verify.py` for the reproducible check.
