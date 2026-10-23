# Combined preflight findings — run 39908359257

Source: [Redmi Pad combined preflight run #39908359257](https://github.com/hashyofficial/copilot-workflow/actions/runs/39908359257) and its `yunluo-miui14-combined-preflight` artifact.

## Verified facts (source-derived)

- Exact MIUI Global `V14.0.4.0.TLYMIXM` archive passed expected MD5.
- All 33 reviewed candidate APK locations were present and package manifests readable; there are 319 APKs in total.
- 8 EROFS logical partitions scanned; `fsck.erofs` returned 0 for each.
- 6,590 source filesystem metadata entries recorded across the three candidate-bearing partitions.
- Three original AVB images parsed; all original header flags are zero.
- A-slot AVB hashtree descriptor bounds pass for product, system, system_ext, vendor, mi_ext, odm_dlkm, and vendor_dlkm.
- `system_b` is separately labelled NOT_ASSESSED for A-slot descriptor bounds; it passed source EROFS integrity.
- 0 structural/manifest blocking errors according to current checks.
- 49 text references to candidates were found across 14 configuration files. These references are not proof of runtime dependency.
- No rebuild was performed and `flash_ready` remains false.

## Nine candidates requiring extra review

The following candidate package identifiers appear in at least one **privapp-permissions** XML. They were not automatically excluded or changed by this read-only audit:

| APK / package ID | Source permission configuration |
|---|---|
| EngineerMode / `com.mediatek.engineermode` | `system/etc/permissions/privapp-permissions-mediatek.xml` |
| YGPS / `com.mediatek.ygps` | `system/etc/permissions/privapp-permissions-mediatek.xml` |
| MusicFX / `com.android.musicfx` | `system/etc/permissions/privapp-permissions-platform.xml` |
| Sound Recorder / `com.android.soundrecorder` | `system/etc/permissions/privapp-permissions-mediatek.xml` |
| Photos / `com.google.android.apps.photos` | `product/etc/permissions/privapp-permissions-google-product.xml` |
| Meet / `com.google.android.apps.tachyon` | `product/etc/permissions/privapp-permissions-google-product.xml` |
| Wellbeing / `com.google.android.apps.wellbeing` | `product/etc/permissions/privapp-permissions-google-product.xml` |
| Google Calendar / `com.google.android.calendar` | `product/etc/permissions/privapp-permissions-google-product.xml` |
| GoogleFeedback / `com.google.android.feedback` | `product/etc/permissions/privapp-permissions-google-product.xml` and `system_ext/etc/permissions/privapp-permissions-google-system-ext.xml` |

A config entry pointing to a missing package is not by itself evidence that boot will fail; however privileged-permission XML is boot-relevant enough to inspect before finalizing an image. Do not remove entire shared permission XML files when deleting one app.

## Other references

- Xiaomi `device_features/yunluo.xml`, display preferences and fixed-orientation lists reference MIUI Cit, Notes, Sound Recorder, and Screen Recorder.
- `removable_apk_info.xml` explicitly lists several original preload/removable apps.
- Google `sysconfig/google.xml`, `preferred-apps/google.xml`, and hidden-API allowlists reference various selected Google apps.
- Vendor camera booster JSON references Screen Recorder.

These entries should be retained or selectively reviewed; blanket removal of shared configuration files is NOT safe.

## What has NOT been proved

- That removing the 33 apps is guaranteed boot-safe. Android and MIUI package dependencies can be implicit rather than declared in manifests.
- That any rebuilt image retains every ownership, SELinux, extended attribute and EROFS compression characteristic.
- That an AVB-disabling or resigning method works on the user's actual unlocked/locked bootloader state.
- That the rebuilt super image passes mount/fsck and descriptor/size checks, since no rebuilt image exists.

**Flash readiness remains NOT APPROVED.** The sensible next operation is an offline, non-flashable trial reconstruction of ONLY the affected partitions, followed by a complete retained-file comparison. Device flashing requires separate explicit review.
