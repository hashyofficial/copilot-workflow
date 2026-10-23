# Redmi Pad yunluo Build 4 Experimental — successful fresh-firmware rebuild

**Build status:** Offline verified and GitHub artifact published successfully on 2026-10-23. **NOT yet boot-tested on the physical tablet.**

- [Completed GitHub Actions run #39946438276](https://github.com/hashyofficial/copilot-workflow/actions/runs/39946438276)
- [Full Build 4 sparse `super.img` download artifact #12498457873](https://github.com/hashyofficial/copilot-workflow/actions/runs/39946438276/artifacts/12498457873) — approximately 3.67 GB, five numbered image parts and `manifest.json` (14-day artifact retention)
- [Build 4 verification report artifact #12499105812](https://github.com/hashyofficial/copilot-workflow/actions/runs/39946438276/artifacts/12499105812) — original source checksum evidence, all 107 exclusions, partition verification, source package identities

## Source

The builder independently re-downloaded the **original Xiaomi MIUI Global V14.0.4.0.TLYMIXM fastboot firmware**, verified its MD5 `4003dcb1a4db404e2768801fdb429c4a`, extracted the original stock `super.img`, and verified the unmodified raw super SHA-256 `2c61eddca409fdb6dca1cb448f991d6bc911355a5f247c742f3fae0fdacce6ef`.

**No Build 1, 2, or 3 modified super image or artifact was used as a source.**

## Dedicated APK directories omitted

| Source removal list | New whole app directories | Cumulative |
|---|---:|---:|
| Build 1 | 24 | 24 |
| Build 2 | 42 | 66 |
| Build 3 | 27 | 93 |
| Build 4 | 14 | **107** |

**Build 4 additions:** Cast (`MiLinkGlobal`), Cloud Backup (`MIUICloudBackupGlobal`), Find Device (`FindDevice`), Frequent Phrases (`MIUIFrequentPhrase`), Mi Share (`MIShareGlobal`), MiCloudSync (`MIUIMiCloudSync`), Recording Assistant (`MiuiAudioMonitor`), Service & Feedback (`MIServiceGlobalPad`), SIM Toolkit (`Stk1`), Work Setup (`ManagedProvisioning`), Xiaomi Account (`MIUIXiaomiAccountGlobal`), Xiaomi Cloud (`MIUICloudServiceGlobal`), Clock (`MIUIDeskClockPadGlobal`), Mi Video (`MIUIVideoPlayer`).

The Build 4 executable target list is `config/build4-additional-14.txt`. Historical target lists for Builds 1–3 are read and merged from source in `scripts/pack_super_build4.py`. The downloadable artifact `manifest.json` contains every exact removed APK folder.

## Preserved

**As specifically requested, Cell Broadcast Service was not added to Build 4 removals.** The stock `system_a:/system/apex/com.google.android.cellbroadcast.apex` container remains in the source EROFS and matched preserved content during validation. Note: Build 3 had already omitted `CellBroadcastLegacyApp`, a different legacy APK; that prior omission is carried into Build 4.

Three previously protected APKs were checked and preserved: `Provision`, `StatementService`, and `LPPeService`.

No runtime APEX modules, shared overlay APKs, or separate userdata APK installations were targeted for additional removal.

## Offline verification

| Partition | Whole app folders removed | Retained paths matched | New EROFS bytes |
|---|---:|---:|---:|
| `product_a` | 53 | 1,765 | 1,398,194,176 |
| `system_a` | 50 | 3,402 | 745,680,896 |
| `system_ext_a` | 4 | 1,074 | 396,136,448 |
| **Total** | **107** | **6,241** | |

Validation succeeded for EROFS image checks, re-extraction and retained path/metadata comparison, all original LP metadata slots, unchanged other super regions, and full sparse-to-raw round-trip SHA-256 equality.

### Image digests

- **Complete raw modified super SHA-256:** `6612533df7e9a7720785be36f79c32a3e953053037a7984f839bac68d261359f`
- **Combined sparse super SHA-256:** `83d456809ce1782c7a1df1ac8ab29ecef87f6ae818316df16c3144a537d8f6e0`
- **Combined sparse file bytes:** `3670329848`
- **Image parts:** 5, each hashed separately inside the artifact's `manifest.json`

### Reassembly on Linux

Extract the binary GitHub Actions artifact ZIP and, from its directory:

```bash
cat super.sparse.img.part-* > super.sparse.img
sha256sum super.sparse.img
```

Confirm SHA-256 matches `83d456809ce1782c7a1df1ac8ab29ecef87f6ae818316df16c3144a537d8f6e0` before testing.

## Device-testing and functional caveats

This is an **unboot-tested experimental image**, not proof that all functions work. The Build 4 exclusions deliberately remove Xiaomi Account, Find Device, Xiaomi Cloud and Cloud Backup, Clock/alarms and Work Setup. Android device administration, account-based services, cloud sync, casting, sharing, and alarm behavior may be affected. Build 3 also omitted ContactsProvider and other Android services.

Stock vbmeta's cryptographic hashtrees are incompatible with the modified partitions; the build does not patch vbmeta. Keep the successful Build 3 image and original ROM available for recovery. Do not relock the bootloader while using modified system images.
