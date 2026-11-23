# SSP-05_10 — TWRP BOOT-ONLY FLASH PREFLIGHT

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** Samsung Galaxy S10+ (SM-G975F / beyond2lte / Exynos 9820)
**Prompt:** 05_10 — TWRP BOOT-ONLY FLASH, VERIFIED RECOVERY & NUXEL BOOT

## Overall verdict

`AWAITING_FLASH_AUTHORIZATION` — every mandatory preflight gate PASS, re-verified
live against the TWRP device this session. BOOT-only flash is fully prepared and
ready for explicit owner authorization. No partition has been written and no power
transition has been performed.

## 1. Recovery environment (live-verified this session)

| Item | Value |
|---|---|
| ADB transport | `R58M75KDB2X` |
| ADB state | `recovery` |
| Recovery | TWRP `3.7.0_9-2` |
| Recovery kernel | `4.14.113-g55f042627` (TWRP's own, NOT the Nuxel boot kernel) |
| Shell uid | root (uid=0) |

## 2. Device identity (live)

Serial `R58M75KDB2X` · Galaxy S10+ · beyond2lte · exynos9820

## 3. Partition mapping (live by-name symlinks)

| Logical | Block device | Bytes |
|---|---|---|
| dtb | /dev/block/sda12 | 8,388,608 |
| dtbo | /dev/block/sda13 | 8,388,608 |
| **boot** | **/dev/block/sda14** | **57,671,680** |
| recovery | /dev/block/sda15 | 67,633,152 |

BOOT target confirmed `/dev/block/sda14`. Candidate size == partition size (exact match).

## 4. Live partition hashes (read-only, twice this session)

| Partition | SHA-256 | vs baseline |
|---|---|---|
| dtb (sda12) | `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780` | MATCH |
| dtbo (sda13) | `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23` | MATCH |
| **boot (sda14)** | **`0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c`** | **MATCH (known-good)** |
| recovery (sda15) | `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87` | MATCH |

## 5. Candidate identity (host, re-verified this session)

File: `evidence/pwnage-ssp-05_9/candidate-boot-0020-0023-0025.img`

| Field | Value |
|---|---|
| SHA-256 | `9805d519b61c38a960158753679e1e2af0cf1783ce4f4c6e3c8b0ba6be5fbca7` (MATCH) |
| Size | 57,671,680 B (MATCH partition) |
| Patch set | 0020 + 0023 + 0025 (0027 excluded) |
| Kernel | 4.14.253-gf7194c1d15ed-dirty |
| Magic | `ANDROID!` |
| Page size / header ver | 2048 / 1 |
| kernel_size / addr | 45,848,584 / 0x10008000 |
| ramdisk_size / addr | 2,424,832 / 0x11000000 |
| second_size | 0 |

## 6. Candidate independent unpack verification (this session)

| Component | Offset | Size | SHA-256 | Match |
|---|---|---|---|---|
| Kernel | 2048 | 45,848,584 | `8dae55e28a0ce5b173860d0dc8c52a1022a0cedcc214d009fc8d4fd1108dfdcb` | MATCH |
| Ramdisk | 45,852,672 | 2,424,832 | `0dd0fb5a3d6895f28d8861d967382a0b87182d0f9c63b1d560393818b290f407` | MATCH |
| Appended DTB | — | — | 0 (no `d00dfeed` magic, tail all-zero) | PASS |
| Trailing slack | — | 9,394,176 B | 100% zero | PASS |

## 7. Mandatory gate results (all PASS, this session)

G_KERNEL_BUILD · G_SSP_PATCH_SET · G_SSP_SYMBOL_PRESENCE · G_BOOT_PACKAGE ·
G_BOOT_INDEPENDENT_UNPACK · G_BOOT_DONOR_IDENTITY · G_BOOT_TAIL_BYTEEXACT ·
G_BOOT_DTB_DTBO_UNCHANGED · G_RECOVERY_PARTITION · G_NATIVE_BBD_TESTS ·
G_ORIENTATION_TESTS (77/77) · G_RECOVERY_TESTS (14/14) · G_BOOT_PACKER_TESTS (9/9) ·
G_KERNEL_SOURCE_AUDIT (4/4) · G_LIVE_DEVICE_HEALTH · G_LIVE_PARTITION_HASHES ·
G_TWRP_ROLLBACK_COPY — **all PASS**.

## 8. Rollback (re-verified this session)

Three genuine physical copies of known-good BOOT (`0e6aa34c...`):
1. Host: `/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img`
2. Device sda31: `/data/media/nuxel-boot/boot-sda14-known-good-0e6aa34c-20261122.img`
3. Device sda28: `/cache/nuxel-ssp-rollback/boot-sda14-known-good.img`

All byte-verified from their own endpoints. Both device copies are TWRP-accessible
via direct ext4 mount (no decryption required). Free space: /data 49.0 GB, /cache 513.1 MB.

## 9. No writes performed

Read-only `dd`+`sha256sum` only. No DTB/DTBO/recovery/bootloader writes. No power
transition. No flash.

## Decision

**`AWAITING_FLASH_AUTHORIZATION`** — all gates pass; awaiting owner approval of the
exact BOOT-only flash (receipt in SSP-05_10-BOOT-FLASH-RECEIPT.md).

---
Machine-readable: `reports/SSP-05_10-PREFLIGHT-RESULT.json`
