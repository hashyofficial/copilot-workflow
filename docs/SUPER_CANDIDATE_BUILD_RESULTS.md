# Redmi Pad yunluo — completed slot-A super candidate

**Workflow:** [Successful build #39917200399](https://github.com/hashyofficial/copilot-workflow/actions/runs/39917200399).

**Binary artifact:** [yunluo-miui14-slot-a-super-candidate](https://github.com/hashyofficial/copilot-workflow/actions/runs/39917200399/artifacts/12486420691) (~4.85 GB; expires after 14 days).

**Validation artifact:** [yunluo-super-build-results](https://github.com/hashyofficial/copilot-workflow/actions/runs/39917200399/artifacts/12486530685).

## Verified build results

- Target ROM: MIUI Global `V14.0.4.0.TLYMIXM`, Redmi Pad `yunluo`, slot A.
- 24 complete dedicated app folders omitted: 18 from `product_a`, 6 from `system_a`.
- 5,409 retained filesystem paths matched original file content and metadata.
- Both original LP metadata slots and all bytes outside the two modified partition regions preserved.
- Both new EROFS partitions passed `fsck.erofs` and were extracted/mounted/read back.
- Android sparse-image round trip recreated the same raw-super SHA256.
- Result contains seven numbered sparse-image parts and a `manifest.json` with every part's SHA256.

### Checksums

- Reconstructed raw super SHA256: `c66dd65e547f35e52587a42feea9d56446925e864733fd1b77b17a74654d0bb5`
- Reassembled sparse super SHA256: `f58f417a6badfa61d7d5a3d052bfcecc6647da9248441431fe7ae7d9fb59a8ce`

### Reassembly on a computer

Extract the GitHub artifact ZIP, then in a Linux/macOS shell, from the directory containing the numbered parts:

```sh
cat super.sparse.img.part-0* > super.sparse.img
sha256sum super.sparse.img
```

The resulting digest must match the sparse SHA256 above. The parts are *segments of one sparse image*, not separate partition images.

**Not verified for flashing:** Original `vbmeta` was not altered; stock AVB hash trees do not match the modified partitions. The image is an offline-validated firmware *candidate*, not a boot-tested ROM. No device operations were performed. Do not relock the bootloader on modified system images.
