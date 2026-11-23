# SSP Stage-05 — TWRP Live Evidence Capture (2026-11-22)

**Generated:** 2026-11-22T18:03:00+01:00 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking (Stage-05 session)
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X
**Device state at session start:** TWRP recovery (NOT normal Nuxel boot)

## Summary
This Stage-05 session began with the device in a TWRP recovery session
(`TWRP 3.7.0_9-2-ddaccbe7`, recovery kernel `4.14.113-g55f042627`,
`crash_counter=0`, `ro.twrp.boot=1`). The normal Nuxel userspace
(SSH root@10.11.12.99) was therefore DOWN, as expected while in recovery.

The correct Stage-05 path remains **SOFTWARE-ONLY first light** through the
running Nuxel kernel's existing SSP/BBD passthrough (`/dev/ttyBCM`,
`/dev/bbd_sensor` 236,1, `/dev/bbd_control` 236,2, `/dev/bbd_patch` 236,3,
`nuxel_bringup` sysfs). **No BOOT flash is justified** (carried forward from
Stage-04_5 `NO_FLASH_NEEDED` / `READY_FOR_STAGE_05_SOFTWARE_ONLY`).

The TWRP session was used **read-only + rollback staging only**. No partition
was written. The independently-accessible second rollback copy was established
on the `/cache` (sda28) partition, which TWRP can read independent of Nuxel.

## TWRP by-name partition mapping (fresh, this session)
Verified against `/dev/block/platform/13d60000.ufs/by-name/*`:

| Name      | Device       | Sectors   | Bytes          | Status vs Stage-01 |
|-----------|--------------|-----------|----------------|--------------------|
| dtb       | /dev/sda12   | 16384     | 8,388,608      | matches            |
| dtbo      | /dev/sda13   | 16384     | 8,388,608      | matches            |
| boot      | /dev/sda14   | 112640    | 57,671,680     | matches            |
| recovery  | /dev/sda15   | 132096    | 67,633,152     | matches            |
| system    | /dev/sda25   | 11673600  | ~1.68 GB       | (Nuxel rootfs)     |
| cache     | /dev/sda28   | 1228800   | 629,145,600    | rollback staging   |
| userdata  | /dev/sda31   | 232669184 | ~119 GB        | (Nuxel data)       |

## Immutable partition hashes (fresh TWRP read-only, this session)
| Partition | Device | SHA-256                                            | vs Baseline   |
|-----------|--------|----------------------------------------------------|---------------|
| dtb       | sda12  | abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780 | UNCHANGED ✅ |
| dtbo      | sda13  | de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23 | UNCHANGED ✅ |
| boot      | sda14  | 0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c | UNCHANGED ✅ |
| recovery  | sda15  | 4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87 | UNCHANGED ✅ |

## Rollback staging (second TWRP-accessible copy) — ESTABLISHED this session
- **TWRP copy:** `/cache/nuxel-ssp-rollback/boot-sda14-known-good.img` (partition sda28)
  - Size: 57,671,680 bytes (55 x 1 MiB records, verified)
  - SHA-256: `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c`
  - Matches live sda14 donor identity exactly ✅
- **Immutable hashes staged alongside:** `/cache/nuxel-ssp-rollback/immutable-hashes.sha256`
- **Host seed 1:** `/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img` (57,671,680 B, SHA `0e6aa34c...`) ✅
- **Host seed 2:** `/tmp/nuxel-ssp-baseline/boot-sda14.img` (57,671,680 B, SHA `0e6aa34c...`) ✅

Three independent copies all match. Rollback readiness now dual-endpoint verified.

## Decision
- **Stage-04 historical receipt:** `NO_FLASH` (preserved unchanged) ✅
- **Stage-04_5 revalidated receipt:** `NO_FLASH_NEEDED` / `READY_FOR_STAGE_05_SOFTWARE_ONLY` ✅
- **Stage-05 next step:** Reboot into normal Nuxel, then run the separately
  reviewed, bounded software-only MCU first-light trial through existing
  `/dev/ttyBCM` + `/dev/bbd_*` nodes (one MCU init attempt per trial, no
  power-rail/reset experiments, no partition writes).
- **No BOOT flash performed or planned.** No authorizing gate set met for flash.
