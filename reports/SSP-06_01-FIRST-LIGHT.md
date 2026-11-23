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
2. **Timing artifact / explicit risk acceptance** — the ROM-ready settle value, a
   stock SSI trace, OR an explicit acknowledgement that readiness is unresolved and
   the autobaud is a bounded blind attempt (the handshake is **not** a readiness
   gate; see `SSP-06_01-TIMING-EVIDENCE.md`).
3. **Explicit bounded-trial grant** — one S1 ROM-identity run (recommended), then a
   separate S2 grant for firmware-download + app-start.

The stale deployed GNSS service that performed (unauthorized) `GPS_PWR_EN`
assertion + `ESW:READY` synthesis at boot has now been **remediated on the device**
(disabled + start-condition, hardened userspace deployed). See
`SSP-06_01-GNSS-SERVICE-REMEDIATION.md`. Boot-time `ESW:READY` count is now 0.

## What this mission DID establish (verified, non-destructive)

- Live baseline healthy, MCU offline, unchanged (independently re-collected).
- Decisive call graph re-read: firmware-first ordering is proven (not hearsay).
- Firmware identity recomputed and matched (SHA-256, 479 F1, ASIC, entry).
- Offline test suites re-run and PASS (all except owner-binary lhd tests).
- Recovery classified: DESIGNED + OFFLINE_VALIDATED, but NOT physically verified.
- Timing partially resolved (ordering proven; settle delay = missing datasheet value).
- Safety finding remediated: stale deployed `nuxel_lhd.py` replaced with repo HEAD,
  service disabled and gated; fail-closed proven live (0 hardware calls, rail 0).
- Firmware identity verified against the **live device** `/dev/bbd_patch` bytes.
- Timing reassessed: MCU_REQ/MCU_RESP is a work-item preamble, **not** a ROM-ready
  gate; readiness remains unresolved.
- Recovery reassessed: `bbd_mcu_reset` is host-side only and is a no-op during the
  planned trial; recovery does not restore a known MCU state.

## Not sufficient for a PASS (per acceptance criteria)

- Passing offline tests
- Firmware hash match
- Kernel probe / asserted GPIO / completed write without MCU ACK
- Simulated GetVersion (recorded as `hardware_verified: false`)
- Empty sensor data
- A process reporting success without independent hardware evidence

None of these are claimed.

## Result

`READY_FOR_SPECIFIC_PHYSICAL_APPROVAL` — all *offline/device-solvable* blockers are
eliminated (service ownership fixed and proven; firmware identity device-verified).
The remaining gate is explicit owner approval of the S1 ROM-identity trial, which
must be granted **with the knowledge that readiness is unresolved** and that
recovery is host-side restore only, not a return to a known MCU state.
