# Redmi Pad Build 2 — offline-verified slot-A super image

**GitHub Actions:** [successful run #39933188306](https://github.com/hashyofficial/copilot-workflow/actions/runs/39933188306).

**Binary artifact:** [yunluo-build2-super-sparse-66-folders](https://github.com/hashyofficial/copilot-workflow/actions/runs/39933188306/artifacts/12491714748) (3.96 GB, 5 numbered chunks, retained 14 days).

**Validation artifact:** [yunluo-build2-fresh-stock-validation](https://github.com/hashyofficial/copilot-workflow/actions/runs/39933188306/artifacts/12492283218).

## Original source, not Build 1

This build **re-downloaded and verified the original Xiaomi MIUI Global firmware** `V14.0.4.0.TLYMIXM` for Redmi Pad `yunluo`. Its source ROM archive MD5 was `4003dcb1a4db404e2768801fdb429c4a` and the raw original `super.img` SHA-256 was `2c61eddca409fdb6dca1cb448f991d6bc911355a5f247c742f3fae0fdacce6ef`.

It did **not** use the modified Build 1 binary as an input.

## Actual removal scope

- Build 1 removals: 24 whole dedicated app folders, same manifest as successful Build 1
- Newly selected Build 2 removals: 42 whole dedicated app folders, from `config/build2-additional-42.tsv`
- Total: **66 whole app folders**

| Partition | Folders removed | Retained paths verified | New EROFS bytes |
|---|---:|---:|---:|
| product_a | 40 | 1,823 | 1,594,929,152 |
| system_a | 25 | 3,452 | 772,874,240 |
| system_ext_a | 1 | 1,092 | 461,377,536 |
| **Total** | **66** | **6,367** | |

All three rebuilt EROFS images passed filesystem checks, were extracted back from the completed super image, and retained-file content/metadata comparison passed. Both original LP metadata slots remained unchanged. All bytes outside the three selected partition regions were unchanged. The sparse-image conversion round trip reproduced the same complete raw image.

## Checksums and reassembly

- Complete raw modified super SHA-256: `db3d5a0fde7a9577a39ab3dec9da9bf1562984a2b0c689a7df450618f60fda55`
- Combined sparse super SHA-256: `5d9cb880adfde28a894eb69509fef285d237e223e105b4f97e020e88462f4917`

Extract the artifact ZIP on your computer and reassemble:

```bash
cat super.sparse.img.part-* > super.sparse.img
sha256sum super.sparse.img
```

The resulting SHA-256 must equal `5d9cb880adfde28a894eb69509fef285d237e223e105b4f97e020e88462f4917`.

## Other requested apps (not removed)

The input had 88 additional app entries: 42 with unique original-firmware folders were removed, 30 system/safety/infrastructure entries were protected, 12 overlay APKs are directly under a shared overlay directory, 3 entries are under runtime-mounted APEX paths, and 1 Netflix package was not in the original stock super image.

**This is not a claim that all 88 uploaded entries have been removed.** The 42 selected APKs were positively matched against fresh firmware package identities. Some originally preloaded apps might also have separate installations in userdata, which rebuilding `super.img` does not remove.

## Important limitation

Build 2 is fully validated **offline, not boot-tested on the tablet**. It removes additional components including the MIUI updater, backup app, TalkBack, and Google speech services, so associated functions may be unavailable. Original AVB metadata is incompatible with the modified partitions, and no vbmeta image was patched or uploaded. Do not relock the bootloader on modified firmware.

Preserve a complete original firmware recovery path and user-data backups before testing any further image on the tablet.
