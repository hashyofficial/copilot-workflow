# Redmi Pad Build 3 — 93 dedicated app folders, fresh stock source

**Status:** Offline image reconstruction and artifact upload successful. **Device boot not tested.**

- [Successful GitHub Actions run #39936003360](https://github.com/hashyofficial/copilot-workflow/actions/runs/39936003360)
- [Full Build 3 sparse super artifact #12494337333](https://github.com/hashyofficial/copilot-workflow/actions/runs/39936003360/artifacts/12494337333) (five numbered files and manifest, about 3.86 GB compressed-by-archive metadata)
- [Validation and checksum artifact #12494790444](https://github.com/hashyofficial/copilot-workflow/actions/runs/39936003360/artifacts/12494790444)

## Provenance

The Build 3 process downloaded **fresh, original Xiaomi MIUI Global V14.0.4.0.TLYMIXM firmware**; it did not use either Build 1 or Build 2 modified super image as a source.

- Original ROM MD5: `4003dcb1a4db404e2768801fdb429c4a`
- Source raw super SHA256: `2c61eddca409fdb6dca1cb448f991d6bc911355a5f247c742f3fae0fdacce6ef`

## Removed dedicated app folders

- Build 1: 24 folders
- Build 2 additions: 42 folders
- Build 3 additions: 27 folders, requested for the Wi-Fi-only tablet
- **Total: 93 entire app directories**.

| Partition | Removed complete folders | Retained paths validated |
|---|---:|---:|
| `product_a` | 43 | 1809 |
| `system_a` | 47 | 3408 |
| `system_ext_a` | 3 | 1080 |
| **Total** | **93** | **6297** |

## Three apps deliberately retained

- `com.android.provision`: `system_ext_a:/priv-app/Provision/Provision.apk`
- `com.android.statementservice`: `system_a:/system/priv-app/StatementService/StatementService.apk`
- `com.mediatek.location.lppe.main`: `system_a:/system/priv-app/LPPeService/LPPeService.apk`

The build verified the source APK package identities for the Build 3 additions and all three protected apps. All 93 directory exclusions were validated, all retained source files and metadata matched, LP metadata was unmodified, outside-target `super` bytes were unchanged, and converting sparse→raw reproduced the completed raw image.

## Not removed by this artifact

The user requested deleting all other entries in the uploaded 88-app list, except the three above. This build **does not achieve complete removal of every listed item**:

- **12 overlay APKs** are files directly inside the shared `/product/overlay` folder. The attempted overlay-removal configuration was blocked before commit. **0 overlays deleted.**
- **3 APEX-mounted APK paths** are runtime mounts; the underlying package/container removal was **not** performed. **0 APEX modules deleted.**
- **Netflix** was installed under the live tablet's `/data/app`; that userdata app **cannot be removed by changing stock `super.img`**. **0 userdata apps deleted.**

No attempt was made to falsely mark these 16 entries as removed.

## Reassemble

Download and extract the GitHub binary artifact, then concatenate the five numbered `super.sparse.img.part-*` files in lexicographic order to reconstruct a single sparse `super.sparse.img` image.

- Full modified raw super SHA256: `bf2d71ddbb0a57b19c06d6fa5f7bb813999b8219b816750fb49373c1731e2163`
- Sparse super SHA256: `71a455535164d053c2733b9f905e8de8e3649c7e38f743a863adf1ee9410f9fe`
- Sparse super total bytes: `3860019696`
- Five parts, individually SHA256-pinned in the artifact `manifest.json`

## Important functional warning

**Build 3 is not known to boot.** Additional removals include `ContactsProvider`, Android telephony framework components, supervision/safety and broadcast-related services. A Wi-Fi-only hardware configuration does **not** prove these components have no software dependencies. Failure to boot and loss of functions remain real possibilities. This artifact contains no patched vbmeta or bootloader commands. Do not relock the bootloader with modified system software.
