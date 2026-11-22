# SSP-ROLLBACK-READINESS — Stage 01 status

**Date:** 2026-11-22
**Status:** `ROLLBACK_SEED_CAPTURED` (one verified host copy). **NOT yet `ROLLBACK_READY`** — second TWRP-accessible copy + dual-endpoint byte verify deferred to Stage 04/05 (no recovery boot performed in read-only Stage 01).

## Verified facts
- Live donor BOOT (`/dev/sda14`, 57,671,680 B) captured read-only to host:
  - Path: `/tmp/nuxel-ssp-baseline/boot-sda14.img`
  - SHA256: `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c`
  - Verified equal to live partition hash (independent `dd | sha256sum` on device).
- Reconciled running kernel = **0020 + 0023** only. kallsyms has `nuxel_ssp_bringup_hw` and related native peer/transport symbols; **no** firmware-downloader (`nuxel_ssp_dl_*`) symbols → 0027 is NOT deployed.
- Recovery partition `/dev/sda15` hash captured: `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87`.
- External dtb (`sda12`) and dtbo (`sda13`) hashes captured and MUST remain byte-identical.

## What is still required before ANY BOOT write (Stage 04/05 gates)
1. A **second**, independently-accessible known-good BOOT copy in a TWRP-reachable location (e.g. microSD/EFS-safe external storage or a TWRP-mounted path), byte-for-byte verified (size + SHA-256) on BOTH host and recovery endpoints.
2. TWRP accessibility re-confirmed on a *later* physical session (Stage 05) — NOT triggered now.
3. Full `SSP-CANDIDATE-PREFLIGHT.json` passing (Stage 04) with:
   - BOOT v1 header fields intact except required kernel-length/offset changes;
   - ramdisk bytes byte-identical to donor (kernel-only repack);
   - NO appended DT tail to preserve (verified count=0) and sda12/sda13 untouched;
   - candidate `Image` load address + bounds within partition; readback byte-verify recipe dry-run.
4. Explicit owner acknowledgment for the bounded hardware trial and BOOT-only TWRP write (within the established agreement; no new consent needed for BOOT-only itself, but consent required for any new/unbounded physical risk or other-partition action).

## Decision
`ROLLBACK_READY = PENDING`. Do **not** flash until both copies exist and dual-verify passes. Current device is safely booted and untouched.
