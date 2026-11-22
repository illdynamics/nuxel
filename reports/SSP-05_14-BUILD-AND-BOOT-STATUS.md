# SSP-05_14 — Build & Boot Status

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X

## Build (clean, case-sensitive)

| Field | Value |
|---|---|
| Source repo | Linux4/android_kernel_samsung_exynos9820 |
| Pinned commit | f7194c1d15eded1c2a1a4dc63825b26103435cc0 |
| Filesystem | Case-sensitive APFS sparse bundle (/Volumes/kernelbuild) |
| Toolchain | aarch64-linux-gnu-gcc 15.2.0 |
| Patch series | 0020 + 0023 + 0025 + 0028 + 0029 (0027 EXCLUDED) |
| Patch receipts | APPLIED_AND_VERIFIED (all 5), 0027 SKIP excluded |
| Image SHA-256 | 90265d386683b86519a46326082accb02555995ca8e1ea9a24e0fdcf91fb9ccd |
| Image.gz SHA-256 | 0ed91005555a179fa84e9886a371030443f9eb651f930a53bd917d0adcad664a |
| vmlinux SHA-256 | 0470ed7800e160560d99a85736b9ad4115a1917d1debe5b641c2dd42fef706ce |
| regulator_force_enable | present in System.map (0028 + 0029 corrected) |

## Regulator 0029 validation

The 0028 `regulator_force_enable()` was audited and found to corrupt
`rdev->open_count` and recurse into `rdev->supply`.  Patch 0029 removes that
tail.  Regression coverage (9/9 PASS) proves:
- no `open_count--` drain
- no `rdev->supply` recursion
- still calls `_regulator_do_enable(rdev)` (physical primitive)
- symbol declared in consumer.h and exported
- both call sites (set_mcu_power, nuxel_ssp_bringup_hw) use it

## BOOT candidate

| Field | Value |
|---|---|
| File | evidence/pwnage-ssp-05_14/boot-0029-candidate.img |
| SHA-256 | 1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599 |
| Size | 57,671,680 (partition-sized) |
| Donor | 760c0e44 (0028 deployed) |
| Kernel | 90265d38 (new 0029-corrected) |
| Ramdisk | 0dd0fb5a (preserved) |
| Appended DTB | 0 (separate DT partitions) |

## Status

`BUILD_OK` — awaiting BOOT-only flash + TWRP reboot agreement.
