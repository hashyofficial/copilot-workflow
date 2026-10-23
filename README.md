# Redmi Pad (yunluo) — MIUI 14 Global super.img laboratory

**Status: Phase 1 (read-only inventory). No images are modified or flashed.**

This project targets the *last MIUI 14 Global Stable* fastboot ROM for the original Redmi Pad **yunluo** (Android 13):
- Version: `V14.0.4.0.TLYMIXM` (not newer HyperOS/Android 14).
- File: `yunluo_global_images_V14.0.4.0.TLYMIXM_20231207.0000.00_13.0_global_4003dcb1a4.tgz`
- Published MD5: `4003dcb1a4db404e2768801fdb429c4a`
- Official Xiaomi CDN: `https://bigota.d.miui.com/V14.0.4.0.TLYMIXM/yunluo_global_images_V14.0.4.0.TLYMIXM_20231207.0000.00_13.0_global_4003dcb1a4.tgz`

Sources: https://xmfirmwareupdater.com/miui/yunluo/stable/V14.0.4.0.TLYMIXM/ and https://source.android.com/docs/core/ota/dynamic_partitions/implement

## Run Phase 1

Go to **Actions → Redmi Pad APK inventory → Run workflow**. Before the firmware download, the job only runs Python syntax and disk availability checks (no mass deletion of preinstalled SDKs). The workflow benchmarks short byte-range responses from Azure CDN, Singapore Alibaba OSS, Xiaomi CDNORG, Xiaomi BN, and Xiaomi BIGOTA, then downloads from the fastest responsive server using segmented aria2 transfers. A source under 400 KiB/s fails the benchmark, avoiding a multi-day download. The workflow downloads and verifies the vendor ROM, enumerates **every archive member** with sizes, extracts the super image and relevant *small* flashing metadata, records flash scripts and their references to `super`, detects Android sparse versus raw, captures both LP metadata slots, unpacks logical partitions *one at a time*, probes their actual filesystem type, mounts them read-only, and inventories all APKs. No device is connected.

The workflow uploads `yunluo-miui14-inventory` with:
- `apks.txt`: exact `<logical partition>:/<path>` locations, one per line.
- `apks-detailed.tsv`: per-APK owner (UID:GID), mode, size, and SELinux label if readable.
- `filesystems.tsv`: actual filesystem type for each logical partition.
- `archive-members.tsv`: all packaged files and sizes (not just `super.img`).
- `flashing-clues.txt`: extracts from Xiaomi flash scripts and other small configs.
- `lpdump-slot0.txt` and `lpdump-slot1.txt`: logical-partition layouts, groups, extents, sizes, slot metadata.
- `super-source.txt`, `tools.txt`, `checksums.txt`, `warnings.txt`.
- `download-sources.json`: per-CDN probe throughput, status, selected source (when successful).

Only text reports are uploaded. **The proprietary firmware and partition images stay off GitHub artifacts**. The workflow uses Ubuntu GitHub-hosted runners, whose disk is limited; large work may require a self-hosted runner with ≥40 GiB free. It deletes partition extraction buffers after each logical partition, but never performs slow blanket SDK cleanup.

## Before Phase 2 (modification)

Provide the `apks.txt` artifact and identify packages to remove. The safest unit of removal is generally the **entire dedicated app directory** (for example `/product/app/ExampleApp/`), including base/split APKs and bundled native libraries—**not** an arbitrary shared parent such as `/system/app`, `/product/app` or `/priv-app`. Exceptions must be inspected individually. For APEX, framework apps, privileged services, shared libraries and update-critical components, removing them can break boot or Android features.

Phase 2 is intentionally blocked until the *actual* super layout, EROFS/ext4 format, verified boot descriptors, and flash script semantics from Phase 1 are reviewed. Merely preserving UID/GID and SELinux labels is insufficient: rebuilding must retain permissions, xattrs (including file capabilities and `security.selinux`), symlinks, hardlinks, timestamps where applicable, partition sizing, AVB hashtree/footer/signature compatibility, and exact logical partition metadata. Only the super image should change, but whether a modified super can boot with existing vbmeta depends on the actual verified-boot configuration; **never assume it can**. Do not disable verification, re-lock the bootloader, or flash an unverified rebuilt image.

**Important:** `fastboot Sending sparse ... 21/21` is a transfer-progress counter, *not* an image-format rule. A raw `super.img` may be accepted by fastboot under supported device/host combinations; on others, host-side sparse conversion or fastbootd may be necessary. A matching super-device byte size and valid metadata matter, not preserving 21 sends. Never infer safe flashing solely from a log counter.

## Safety / non-goals

- No automatic download of newer HyperOS in a workflow meant for MIUI 14.
- No changes to boot, vbmeta, userdata, or unrelated partition images.
- No automatic flash, no unconditional repack, no undocumented "super build" switch.
- Read-only images are always unmounted even if inventory collection fails.
- A modified image can brick a device or fail verified boot. Confirm `fastboot getvar product`, lock state, active slot, installed build, and anti-rollback implications independently before any flash. Downgrading from HyperOS to MIUI 14 may be unsafe.

## Tools

`simg2img`, `lpunpack`, `lpdump` are Android partition tools. The workflow fetches the fixed `36.0.1` release of https://github.com/meator/android-tools-static and checks each release artifact's published SHA256 digest. Read-only image detection is performed with `blkid`/`file`; Linux kernel handles ext4 / EROFS mounts. `erofs-utils`, `e2fsprogs`, `attr`, and `util-linux` are installed for diagnosis. Future builds will need `lpmake`, `mkfs.erofs` or ext4 creation tools **only after** the real filesystem has been confirmed.

The firmware is fetched at run time; it is not downloaded/inspected from within this chat. The alternate servers use the same Xiaomi firmware path, not a different ROM version. The full archive must pass the pinned MD5 check before inspection. A 512-KiB range benchmark is only a short performance sample, not a guarantee of sustained download rate. Standard GitHub-hosted Ubuntu runners cannot be placed in Singapore just by setting a workflow property; faster local CDN access is determined from the runner's network. If all candidates are slow or unavailable, the workflow fails fast with a report instead of hanging for hours.
