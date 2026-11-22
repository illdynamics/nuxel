# SSP-05_14 — Stage 06 Handoff

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X

## Mission outcome

The authorized **BOOT-only deployment of the 0029-corrected SSP kernel** is
COMPLETE and VERIFIED.  Nuxel boots normally with the corrected regulator core.

```
BOOT_NUXEL = PASS
REGULATOR_CORE_SAFETY = PASS
READY_FOR_06 = FALSE  (two gates remain: POWER_TRANSITION_SAFETY, ROM_GETVERSION)
```

## What was done (this mission)

1. Reconstructed the exact pinned Samsung kernel source (f7194c1d15ed) on a
   case-sensitive APFS filesystem.
2. Regenerated canonical 0028 and 0029 patches (the originals had corrupt/stale
   hunks); all 5 SSP patches (0020+0023+0025+0028+0029) now apply deterministically.
3. Fixed the build script to honor NUXEL_SSP_EXCLUDE_0027=1 at the apply stage
   (previously 0027's .required sidecar aborted the build despite exclusion).
4. Audited + validated the 0029 regulator-core fix (open_count/supply removal).
   Added focused regression coverage (test_regulator_0029.py, 9/9 PASS).
5. Clean full kernel build (case-sensitive, GCC 15.2.0).
6. Packed the BOOT candidate (kernel 90265d38, ramdisk preserved, no appended DTB).
7. Full preflight + 5 verified rollback copies (2 host, 2 device + 1 older).
8. Authorized BOOT-only flash to /dev/block/sda14 (dd, single write) + post-write readback.
9. Normal Nuxel boot verified (kernel 4.14.253-gf7194c1d15ed-dirty, systemd running).

## Deployment identity (recorded for the flash contract)

| Field | Value |
|---|---|
| BOOT partition | /dev/block/sda14 (by-name boot) |
| Candidate SHA-256 | 1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599 |
| Kernel SHA-256 | 90265d386683b86519a46326082accb02555995ca8e1ea9a24e0fdcf91fb9ccd |
| Running kernel | 4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT Nov 23 00:43:30 CET 2026 |

## Rollback (preserved, byte-verified)

- host:/tmp/nuxel-boot/boot-0028-current.img = 760c0e44 (0028)
- host:evidence/pwnage-ssp-05_12/boot-0028-candidate.img = 760c0e44
- device:/cache/nuxel-ssp-rollback/boot-sda14-known-good-760c0e44.img = 760c0e44
- device:/cache/nuxel-ssp-rollback/boot-sda14-known-good-9805d519.img = 9805d519
- host:evidence/pwnage-ssp-05_9/candidate-boot-0020-0023-0025.img = 9805d519

## Remaining blocker for READY_FOR_06 (single minimum intervention)

The ONLY remaining blocker is the **S0→S1 transition**: asserting `GPS_PWR_EN`
(gpg0-2) HIGH to power the GNSS boot-ROM for ROM first light.  This is:
- NOT authorized by the BOOT-flash mandate (Section 0.2/10).
- Requires vendor-sequence evidence (Broadcom datasheet / gpsd disassembly) for
  safe post-power timing and RF-safety.
- Requires separate owner sign-off.

The single minimum intervention required is: **owner approval of a bounded,
supervised GPS_PWR_EN assertion trial** (with the vendor timing evidence, or an
explicit safety grant), after which the ROM GetVersion probe can be run.

## Current live state

Nuxel is healthy and running the 0029-corrected kernel.  systemd running, 0
failed units, SSP/BBD transport present, regulator framework clean.  No GPS_PWR_EN
assertion, no new regulator transition, no unrelated partition writes performed.

## Next stage (Stage 06) readiness

With the GPS_PWR_EN assertion approved+performed, ROM first light can proceed via
the existing bcm477x_rpc_get_version() / nuxel_bbd_flash --rom-probe path.
