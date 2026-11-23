# SSP-05_9 — BOOT Recovery Readiness

**Date:** 2026-11-22 (Europe/Amsterdam)
**Status:** `ROLLBACK_SEED_CAPTURED` — one verified host copy. **NOT `ROLLBACK_READY`** —
second TWRP-accessible copy + live dual-endpoint byte-verify still required (device
not connected this session).

## Verified facts

| Item | Value | Hash / Size | Status |
|---|---|---|---|
| Known-good BOOT donor | `/dev/sda14` | `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c` (57,671,680 B) | VERIFIED (host) |
| Host seed copy 1 | `/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img` | same as donor | VERIFIED |
| Legacy host seed | `/tmp/nuxel-ssp-baseline/boot-sda14.img` | same as donor | VERIFIED (Stage-01) |
| External DTB | `/dev/sda12` | `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780` | UNCHANGED (baseline) |
| External DTBO | `/dev/sda13` | `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23` | UNCHANGED (baseline) |
| Recovery | `/dev/sda15` | `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87` | UNCHANGED (baseline) |
| TWRP-accessible rollback copy 2 | — | NOT ESTABLISHED | REQUIRED pre-flash |

BOOT partition mapping (established, prior live sessions):
- `boot = /dev/sda14` (112,640 sectors = 57,671,680 B)
- `dtb  = /dev/sda12` (8,192 sectors)
- `dtbo = /dev/sda13` (8,192 sectors)
- `recovery = /dev/sda15` (132,096 sectors)

## Rollback independence

The two host seeds (`/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img` and
`/tmp/nuxel-ssp-baseline/boot-sda14.img`) are **not** treated as independent
rollback copies: they reference the same logical BOOT content on the host. The
prompt's rule — "do not treat two filenames pointing to the same storage object
as independent recovery copies" — is honored. A genuinely independent second copy
must live on a **TWRP-reachable device path** (microSD or an external recovery
mount), byte-verified (`size + sha256`) from both host and recovery endpoints.

## Pre-flash recovery checklist (MUST all pass before ANY BOOT write)

1. Device connected + normal Nuxel boot confirmed healthy (`uname -a`, no bootloop).
2. Live read-only `dd+sha256` of sda12/sda13/sda14/sda15 equals the baseline above.
3. TWRP entered via established procedure; BOOT partition (`/dev/block/...sda14`)
   mapped/confirmed inside TWRP.
4. Second TWRP-accessible rollback copy written + byte-verified (both endpoints).
5. Candidate SHA-256 (`9805d519b61c38a960158753679e1e2af0cf1783ce4f4c6e3c8b0ba6be5fbca7`)
   and rollback SHA-256 (`0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c`)
   re-verified on-host before write.
6. Explicit BOOT-only flash authorization obtained for THIS specific candidate.

## Rollback procedure (to be used only on authorized flash failure)

1. Re-enter TWRP.
2. `dd` the verified known-good BOOT seed back to `/dev/sda14` (write BOOT only).
3. Read back + `sha256sum`; confirm equals `0e6aa34c...`.
4. Reboot normal; confirm Nuxel boots (`uname -a` = healthy).

Never write DTB, DTBO, recovery, bootloader, or any unrelated partition.

---

Decision: **`ROLLBACK_READY = PENDING`** — do not flash until the second
TWRP-accessible copy exists and all live hashes are re-confirmed.
