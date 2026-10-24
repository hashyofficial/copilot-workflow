# HyperOS 1 Global — Build 1 (131 APK targets)

**Offline image build SUCCEEDED; physical device boot NOT YET TESTED.**

Source: Redmi Pad (yunluo), Global `OS1.0.9.0.ULYMIXM`, Android 14.

- GitHub Actions run: https://github.com/hashyofficial/copilot_workflow/actions/runs/40101727831
- Binary image artifact (14-day retention): https://github.com/hashyofficial/copilot_workflow/actions/runs/40101727831/artifacts/12562774122
- Verification report artifact (30-day retention): https://github.com/hashyofficial/copilot_workflow/actions/runs/40101727831/artifacts/12563348069
- Original user manifest: [config/Apps_Remove.txt](config/Apps_Remove.txt)
- Source stock inventory: [results/APKS_ALL.tsv](results/APKS_ALL.tsv)
- Builder: [build_images.py](build_images.py)

## Exactly what changed

- `super.img`: Rebuilt original HyperOS EROFS partitions, retaining original logical partition geometry/metadata.
- `vbmeta.img`: Original stock AVB0 flags changed from `0` to `3` (disables verification/verity).
- **130 dedicated app directories omitted entirely.**
- **One standalone APK** `product_a:/overlay/MiuiThemeManagerGlobalOverlayTest.apk` omitted without deleting the shared `/overlay` directory and its unrelated files.
- `mi_ext_a`: 20 targets.
- `product_a`: 58 targets (57 directories, one shared-overlay file).
- `system_a`: 27 targets.
- `system_ext_a`: 26 targets.
- **131 target APK entries total.** No other APK requests and no APK additions.

## Exact image checksums

| Object | SHA-256 |
|---|---|
| Original stock raw `super.img` | `965f791ef796d4346b4abf95fad216a90084ed869ef2b6fbae1993d5683c686c` |
| Modified raw `super.img` (9,126,805,504 bytes) | `1ecd1d4317b5bc7ee3a8b1d488acee34d7e360e03619d86c048194998f4c11c4` |
| Modified **sparse** `super.img` (3,549,796,820 bytes) | `ac003fea8fd6fb40ae8ba1ebdfbb8062dcc0f64a2723cc2bff50c897116bd12d` |
| Original stock `vbmeta.img` | `cc34aa04532fc46f70558d0cd98bc4a4f008e9aa795ac9762cec220fd52c80a0` |
| Modified `vbmeta.img` | `38585268437dbf1d68c6fae61020701e99ffff7b4786c19462a0ec4db9e979d5` |

The modified sparse super is split into **five** files to stay within convenient artifact-file sizes; the modified vbmeta is a separate 8,192-byte file. Their SHA-256 values are in `MANIFEST.json` inside the artifact.

To reconstruct the **single sparse `super.img`** on Linux in the folder containing all five parts:

```bash
cat super.img.part-000 super.img.part-001 super.img.part-002 super.img.part-003 super.img.part-004 > super.img
sha256sum super.img vbmeta.img
```

The printed hashes must match the modified **sparse** super and modified vbmeta values above. Do not mix these with MIUI 14 parts.

## Validations that succeeded

1. Clean original Xiaomi HyperOS fastboot firmware MD5 check.
2. Complete allowlist matches original stock APK inventory exactly.
3. All four source partitions unpacked as EROFS and rebuilt without oversized extents.
4. Retained file contents and metadata verified within all four rebuilt partitions.
5. Both LP metadata slots exactly matched the stock super image.
6. Every byte outside the selected logical partition extents stayed unchanged.
7. Sparse-to-raw round-trip matched the modified super SHA-256.
8. Patched vbmeta changes only AVB0 flags.

**Important:** Several selected APKs are system services/providers. Offline consistency checks do not prove the modified firmware can boot or that all device functions will work. The modified `vbmeta.img` invalidates Xiaomi's original AVB signature. An unlocked bootloader is necessary; never relock with modified partitions. No full fastboot firmware ZIP or flash operation was performed.

The GitHub Actions downloadable wrapper is an artifact ZIP holding **only the image parts, vbmeta, and manifests**. It is **not** a reconstructed full Xiaomi fastboot ZIP.

