# Redmi Pad MIUI 14 — rebuilt partition AVB compatibility gate

Evidence:
- [Original AVB audit, successful run #39904922539](https://github.com/hashyofficial/copilot-workflow/actions/runs/39904922539)
- [Successful 24-app EROFS reconstruction, run #39911010096](https://github.com/hashyofficial/copilot-workflow/actions/runs/39911010096)
- User-reported device state: bootloader unlocked, active slot A (not independently verified)

## Cross-check results

| Check | Result |
|---|---|
| Firmware MD5 | Verified against Xiaomi source: `4003dcb1a4db404e2768801fdb429c4a` |
| Original `vbmeta.img` algorithm | SHA256_RSA2048 |
| Original `vbmeta.img`, `vbmeta_system.img`, `vbmeta_vendor.img` flags | All 0: hashtree/verification enabled |
| Top-level vbmeta chain to `vbmeta_system` | Present |
| `vbmeta_system.img` hashtrees for product and system | Present |
| Changed EROFS data for `product_a` and `system_a` | **Yes, both source and rebuilt SHA256 hashes differ** |
| Original hashtree image-size bounds | Rebuilt images fit within both original AVB payload bounds |
| Old hashtree descriptors accept rebuilt content | **No; descriptors are for the unmodified firmware** |
| Direct `avbtool verify_image` of rebuilt image | **Not performed**; rebuilt images were temporary and not retained |
| RSA signature cryptographically verified | **Not performed** in prior structural audit |
| Modified or resigned vbmeta prepared | **No** |
| On-device boot tested | **No** |
| Flash ready | **BLOCKED** |

## Partition fingerprints

| Partition | Stock EROFS SHA256 | Rebuilt EROFS SHA256 | Rebuilt bytes | Original AVB payload bytes |
|---|---|---|---:|---:|
| `product_a` | `17c956a7917343a6aebe5bf70391f71e91f7aa858e5979a7abce9c4ad2493002` | `fa526d4c2e15fc9adcacfc69bec592b71147953377528277bf05fea3ac19983d` | 2,344,132,608 | 2,808,532,992 |
| `system_a` | `fbbad016659b088c1abc04ccb4ac10252c7cfccc9a30191824f322878156a430` | `a1581507cccebba98d9d29f02d3ffca9264ddf69f5c411ebd9aed9ac49d57c02` | 903,012,352 | 906,498,048 |

## Decision

The original signed AVB chain describes the unmodified system and product Merkle trees, not the rebuilt partition contents. The source EROFS trees changed when the 24 complete app folders were omitted; preserving the original AVB descriptors does not restore integrity. Even though the rebuilt EROFS images passed filesystem checks and fit in their original partitions, **stock AVB compatibility is not established and should be treated as failed**.

An unlocked bootloader can allow some verified-boot configurations, but the device-specific accepted configuration and complete boot-chain behavior are not proved by these artifacts. Modifying only vbmeta header flags would invalidate its existing RSA signature. No new vbmeta image or flashing instructions are included.

This is an **evidence-based compatibility gate from saved, successful artifacts**, not a fresh cryptographic `verify_image` run. No ROM was redownloaded; no device was connected or flashed.
