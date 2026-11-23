# SSP-06_01 — Stage 06 Handoff (final unblock)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01 (final unblock pass)

## Final Result

```
MCU_FIRST_LIGHT = NOT_RUN
DECISION        = READY_FOR_SPECIFIC_PHYSICAL_APPROVAL
```

The MCU has NOT reached a verified operational state. Accelerometer/gyroscope
validation remains **BLOCKED** until genuine MCU first light is physically verified.
No sensor success is claimed.

## What this pass actually did

### Task A — stale deployed GNSS service (fixed)

- Confirmed the deployed `nuxel_lhd.py` (`6d90a2c0…`) was byte-identical to an older
  commit (`a654d754`), not to repo HEAD, and that it asserted `GPS_PWR_EN=1` and
  wrote `ESW:READY` at every boot (verified in boots `-1`…`-4`).
- Deployed the hardened repo HEAD files (`aeed416d…`, `085096a9…`, `72679d2e…`),
  `root:root 0755`; removed stale bytecode.
- Disabled `nuxel-gnss-lhd.service` and added a start-condition drop-in
  (`/run/nuxel/ssp-06_01/gnss-owner-authorized` must exist) as a second barrier.
- Proved fail-closed live: exit 2, `INITIALIZATION_PROTOCOL_UNVERIFIED`, zero
  hardware calls, rail `0` — including a forced start.
- Saved a hash-verified rollback bucket and a documented runbook.

### Task B — ROM-ready timing (reassessed, still unresolved)

- MCU_REQ/MCU_RESP (`bcm477x_hello`, `bcm_gps_spi.c:496-537`) is a per-burst work
  preamble, not a readiness gate. Live counter-evidence recorded.
- No kernel ROM path exists (`bcm477x_rpc_get_version` has zero callers).
- Exact missing evidence listed in `SSP-06_01-TIMING-EVIDENCE.md`.

### Task C — recovery (reassessed, limitations stated)

- `bbd_mcu_reset` is host-side only and is a **no-op** during the planned trial.
- Recovery does not return the MCU to a known state; it restores host outputs.
- Added a validated host watchdog as a compensating control.

### Task D — authorization package

`reports/SSP-06_01-PHYSICAL-TRIAL-AUTHORIZATION.md` now separates:
- **S1** ROM identity only (recommended first grant), and
- **S2** firmware + app start (separate grant).
It lists verified preconditions, the readiness caveat, recovery limits, firmware
identity, exact scope, termination criteria, risks, and the owner approvals still
required (A1–A8).

### Task E — evidence

`evidence/pwnage-ssp-06_01/post-hardening-live.txt` (post-change live snapshot),
plus the pre-existing `deployed-lhd-revision.txt` and `live-baseline.txt`.

## Handoff gate to accel/gyro

Do not start accelerometer/gyroscope validation until:

1. An owner-approved S1 run returns a valid id-3 GetVersion from the ROM, **and**
2. An owner-approved S2 run returns a post-download GetVersion with `w0 == 0x4775b0`,
   **and**
3. The operator physically confirms the handset is healthy and the services are as
   expected afterwards.

Anything less (framework success, a GPIO, a file parse, a simulated replay) is not
first light.
