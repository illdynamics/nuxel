# SSP-05_10 — BOOT-ONLY FLASH AUTHORIZATION RECEIPT

**Date:** 2026-11-22 (Europe/Amsterdam)
**Status:** `AWAITING_FLASH_AUTHORIZATION` — no flash performed yet.

This receipt presents the exact, verified BOOT-only flash plan for owner approval.
Approving this receipt authorizes ONLY the single BOOT-partition write below.
No DTB, DTBO, recovery, bootloader, or unrelated partition write is authorized.

## Exact BOOT target

| Field | Value |
|---|---|
| Partition | **`/dev/block/sda14`** (by-name `boot`) |
| Size | 112,640 sectors = 57,671,680 B |

## Candidate

| Field | Value |
|---|---|
| File | `evidence/pwnage-ssp-05_9/candidate-boot-0020-0023-0025.img` |
| SHA-256 | `9805d519b61c38a960158753679e1e2af0cf1783ce4f4c6e3c8b0ba6be5fbca7` |
| Size | 57,671,680 B |
| Kernel | 4.14.253-gf7194c1d15ed-dirty |
| Patch set | 0020 + 0023 + 0025 (0027 excluded) |

## Known-good BOOT (rollback source)

| Field | Value |
|---|---|
| SHA-256 | `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c` |
| Live partition | currently matches known-good (re-verified this session) |

## Rollback copy verification (re-verified this session)

| Copy | Location | SHA-256 | Verified |
|---|---|---|---|
| Host | `/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img` | `0e6aa34c...` | YES |
| Device sda31 | `/data/media/nuxel-boot/boot-sda14-known-good-0e6aa34c-20261122.img` | `0e6aa34c...` | YES |
| Device sda28 | `/cache/nuxel-ssp-rollback/boot-sda14-known-good.img` | `0e6aa34c...` | YES |

Three genuine physical storage locations. Device copies TWRP-accessible without a
Nuxel boot. Free: /data 49.0 GB, /cache 513.1 MB.

## DTB/DTBO/Recovery baseline (must remain unchanged)

| Partition | SHA-256 |
|---|---|
| dtb (sda12) | `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780` |
| dtbo (sda13) | `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23` |
| recovery (sda15) | `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87` |

## Mandatory gate results — ALL PASS

G_KERNEL_BUILD · G_SSP_PATCH_SET · G_SSP_SYMBOL_PRESENCE · G_BOOT_PACKAGE ·
G_BOOT_INDEPENDENT_UNPACK · G_BOOT_DONOR_IDENTITY · G_BOOT_TAIL_BYTEEXACT ·
G_BOOT_DTB_DTBO_UNCHANGED · G_RECOVERY_PARTITION · G_NATIVE_BBD_TESTS ·
G_ORIENTATION_TESTS 77/77 · G_RECOVERY_TESTS 14/14 · G_BOOT_PACKER_TESTS 9/9 ·
G_KERNEL_SOURCE_AUDIT 4/4 · G_LIVE_DEVICE_HEALTH · G_LIVE_PARTITION_HASHES ·
G_TWRP_ROLLBACK_COPY.

## Flash procedure (executed ONLY after explicit owner approval)

1. Reconfirm `/dev/block/sda14` target and candidate SHA-256 `9805d519b...`.
2. `adb push` candidate to device temp; re-verify device-side sha256.
3. `dd if=<candidate> of=/dev/block/sda14 bs=4096` (BOOT only).
4. `sync`.
5. Read back full sda14; `sha256sum` must equal `9805d519b...`.
6. Re-hash sda12/sda13/sda15; must equal baseline (unchanged).
7. Reboot normal into Nuxel.

---

**OWNER APPROVAL REQUIRED.**

Please confirm: **"Approve BOOT-only flash of candidate
`9805d519b61c38a960158753679e1e2af0cf1783ce4f4c6e3c8b0ba6be5fbca7` to
`/dev/block/sda14`."**

Being in TWRP does not waive this authorization requirement. If denied, stop before
flashing.
