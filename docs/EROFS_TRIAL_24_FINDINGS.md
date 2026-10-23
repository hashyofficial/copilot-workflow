# Redmi Pad MIUI 14 — offline 24-app EROFS reconstruction trial

Scope: original `yunluo` Global `V14.0.4.0.TLYMIXM` source. This document records the first full offline image reconstruction in [Actions run #39910441354](https://github.com/hashyofficial/copilot-workflow/actions/runs/39910441354) and its [report artifact](https://github.com/hashyofficial/copilot-workflow/actions/runs/39910441354/artifacts/12482527241).

## Verified final green run

The clean [Actions run #39911010096](https://github.com/hashyofficial/copilot-workflow/actions/runs/39911010096) completed **successfully** after the reporting fix. [Final 11-file report artifact](https://github.com/hashyofficial/copilot-workflow/actions/runs/39911010096/artifacts/12483325517).

Its saved `status.json` confirms:

- `source_verified: true` — pinned firmware archive checksum and raw super SHA256 matched.
- `trial_directories_removed: 24`.
- `reconstructed_partitions: 2`.
- `offline_comparisons_pass: true` — all 5,409 retained paths matched, with zero missing, added, or changed entries.
- `errors: []` and `blockers.txt`: no retained-file differences.
- `flash_ready: false`, `avb_stock_valid_for_modified_images: false`, `binary_images_uploaded: false`.

All results below were reproduced in that clean run. The reconstructed partition images were temporary, used only to verify the effect of whole-directory exclusion; they were removed with the runner workspace and were not uploaded.

## Image reconstruction results captured before a reporting-only failure

The firmware archive passed MD5 and the exact raw `super.img` SHA256 matched the previous verified source. The `mkfs.erofs` fixture proved that `--exclude-path` (relative to the filesystem root) omits an entire directory, including compiled artifacts, without changing an unrelated file or its SELinux extended attribute.

| Partition | Whole app folders omitted | Retained paths matched | Missing | Extra | Changed content/metadata | Original EROFS bytes | Rebuilt trial bytes |
|---|---:|---:|---:|---:|---:|---:|---:|
| product_a | 18 | 1,903 | 0 | 0 | 0 | 2,862,206,976 | 2,344,132,608 |
| system_a | 6 | 3,506 | 0 | 0 | 0 | 923,881,472 | 903,012,352 |
| **Combined** | **24** | **5,409** | **0** | **0** | **0** | | |

All 24 requested dedicated folders (and their contents) were absent from their respective disposable reconstructed EROFS images. 68 product filesystem entries and 15 system entries were excluded. The exact original/after path sets and content SHA256, numeric owners, modes, timestamps, symlink targets, and all readable extended attributes matched for the 5,409 retained entries. Both reconstructed EROFS images passed `fsck.erofs`; both were mounted read-only for path comparison. The original 9 held APKs were retained.

**Why the first complete run was marked failure:** after both partitions passed, the summary attempted `mkfs.erofs -V` as a command required to return zero. The installed `mkfs.erofs` displays usage and exits nonzero on that option. The reporting-only call failed after the report JSON files had been written; it did not indicate a filesystem rebuilding error. The version display has been removed in commit `f21a1da` and a new [verification run #39911010096](https://github.com/hashyofficial/copilot-workflow/actions/runs/39911010096) was started.

## What this does NOT show

- There is **no verified flashable modified super.img**. The binary reconstructed EROFS files were temporary and deliberately not uploaded.
- The stock AVB hashtrees for `product` and `system` do not cover rebuilt filesystems.
- EROFS filesystem integrity and retained-file equivalence do not prove the ROM will finish booting, or that every MIUI framework dependency was recognized.
- Logical-partition metadata and an actual repacked super image have not been constructed/validated.
- Bootloader status and usable device-specific AVB compatibility remain unverified.

**FLASH READINESS: NOT APPROVED.** Retain the original full fastboot firmware and only proceed to flash-readiness review after the independent checks above.
