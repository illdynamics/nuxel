# SSP-06_01 — First-Light Status

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01

## MCU First Light: NOT RUN

`MCU_FIRST_LIGHT = NOT_RUN`

No physical trial was performed. No GPS_PWR_EN assertion, no MemoryWrite, no
StartScratch/ServiceStart, no firmware execution, no post-download GetVersion.

## Why not run

The physical trial is gated on three owner decisions that are NOT satisfied by an
agent prompt:

1. **RF authorization** — `GPS_PWR_EN=1` energises the GNSS radio domain.
2. **Timing artifact** — `GPS_PWR_EN`→ROM-ready settle value, OR acceptance of
   handshake-gated readiness + bounded timeouts.
3. **Explicit bounded-trial grant** — for the firmware-download + app-start
   sequence.

Additionally, this mission surfaced a stale deployed GNSS service that already
performs the (unauthorized) RF assertion + ESW:READY synthesis at boot; that
should be remediated (mask service or deploy hardened binary) as a precondition
so the trial's device ownership is exclusive.

## What this mission DID establish (verified, non-destructive)

- Live baseline healthy, MCU offline, unchanged (independently re-collected).
- Decisive call graph re-read: firmware-first ordering is proven (not hearsay).
- Firmware identity recomputed and matched (SHA-256, 479 F1, ASIC, entry).
- Offline test suites re-run and PASS (all except owner-binary lhd tests).
- Recovery classified: DESIGNED + OFFLINE_VALIDATED, but NOT physically verified.
- Timing partially resolved (ordering proven; settle delay = missing datasheet value).
- New safety finding: deployed `nuxel_lhd.py` stale → unauthorized RF assertion
  + ESW:READY synthesis at boot (repo already contains the fix).

## Not sufficient for a PASS (per acceptance criteria)

- Passing offline tests
- Firmware hash match
- Kernel probe / asserted GPIO / completed write without MCU ACK
- Simulated GetVersion (recorded as `hardware_verified: false`)
- Empty sensor data
- A process reporting success without independent hardware evidence

None of these are claimed.

## Result

`READY_FOR_SPECIFIC_PHYSICAL_APPROVAL` — all offline-solvable blockers are
eliminated; the remaining gate is the explicit owner decision on the physical
trial document.
