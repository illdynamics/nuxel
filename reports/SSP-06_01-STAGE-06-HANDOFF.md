# SSP-06_01 — Stage 06 Handoff

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01

## Final Result

```
MCU_FIRST_LIGHT = READY_FOR_SPECIFIC_PHYSICAL_APPROVAL
```

The MCU has NOT reached a verified operational state. Accelerometer/gyroscope
testing remains BLOCKED until genuine MCU operation is demonstrated. No sensor
success is claimed.

## What was actually done this mission

1. Re-audited the entire SSP state independently (live read-only + source re-read
   + independent firmware recompute + offline test re-run).
2. Confirmed every prior Stage 06_00 finding by reading the actual kernel source
   (`bcm_gps_spi.c`, `bcm_gps_regs.c`, `bbd.c`) and recomputing firmware facts.
3. Surfaced ONE new, source-proven, safely-resolvable issue (below).
4. Produced the physical-trial authorization document for explicit owner decision.

## The one new finding (worth acting on)

The **deployed** `nuxel_lhd.py` (`/usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py`,
sha256 `6d90a2c0…`, dated Nov 13) is a stale revision that, at every boot:

- asserts `GPS_PWR_EN=1` (GNSS RF energisation, **without owner RF authorization**), and
- writes `ESW:READY` (synthesized readiness, **without any confirmed MCU identity**).

The repository HEAD already contains the correct hardening (`4175b949`; sha256
`aeed416d…`) whose `run_session()` refuses with `INITIALIZATION_PROTOCOL_UNVERIFIED`
before any power/device access.

**Recommended owner action:** either mask `nuxel-gnss-lhd.service` or deploy the
hardened repo HEAD binary, before any physical trial, so the trial's GPS_PWR_EN
ownership is exclusive.

## Handoff to the accelerometer/gyroscope Stage 06 workflow

Held until the physical firmware-download trial demonstrates:

1. MCU reaches ESW:READY (verified post-download GetVersion `w0==0x4775b0`).
2. Genuine SSP handshake.
3. Sensor enumeration (non-empty, verified as physical).
4. Genuine accel + gyro samples (not `0,0,0` placeholder).

The next stage should then validate (only after MCU first light):
normal SSP handshake, sensor enumeration, genuine accel/gyro samples, timestamp
continuity, axis orientation/calibration, native sensor interfaces, orientation
processing, autorotation, suspend/resume + repeated-startup stability.

None of these are reported successful until measured.

## Preserved evidence

`evidence/pwnage-ssp-06_01/live-baseline.txt`
`evidence/pwnage-ssp-06_01/deployed-lhd-revision.txt`
