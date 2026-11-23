# NUXEL SSP — 06_01 FINAL UNBLOCK AND TRIAL READINESS

The previous 06_01 investigation completed with `READY_FOR_SPECIFIC_PHYSICAL_APPROVAL`, commit `6ac11293`.

Do not repeat broad reverse engineering or existing offline tests without a specific reason. Concentrate on the remaining actionable blockers.

## Task A — Correct stale deployed GNSS service

1. Verify the deployed `/usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py` against the hardened repository implementation.
2. Inspect the `nuxel-gnss-lhd.service` unit and dependencies.
3. Confirm which version is authoritative.
4. Safely prevent the stale service from asserting `GPS_PWR_EN` or issuing `ESW:READY` at boot.
5. Deploy the previously validated hardened userspace implementation if compatible with the current installation.
6. Verify service ownership, permissions, file hashes and rollback.
7. Verify that the hardened service fails closed without explicit authorization.
8. Preserve GNSS functionality and configuration for later restoration.
9. Do not alter MCU power or perform firmware startup during this task.

## Task B — Resolve ROM-ready timing

Reassess whether the documented MCU_REQ/MCU_RESP handshake provides a defensible readiness condition for the subsequent autobaud operation.

Use actual source, protocol and vendor evidence.

Distinguish handshake readiness from ROM-autobaud readiness.

Do not invent a delay or treat an unverified assumption as a safety guarantee.

If unresolved, identify the exact missing timing evidence.

## Task C — Validate recovery independently

Review whether the planned recovery genuinely returns the hardware to a known state.

Do not treat `bbd_mcu_reset` as a physical reset unless independently demonstrated.

Confirm the intended inactive GPIO states, transport cleanup, service ownership and recovery verification criteria.

Use offline validation and existing evidence only.

## Task D — Final trial authorization package

Update `reports/SSP-06_01-PHYSICAL-TRIAL-AUTHORIZATION.md` with:

- Verified deployed GNSS service state.
- Verified exclusive hardware ownership.
- Timing/readiness evidence.
- Recovery evidence and limitations.
- Firmware identity.
- Exact proposed trial scope.
- Failure termination criteria.
- Physical-operation risks.
- Specific owner approvals still required.

Do not execute a physical firmware trial under this prompt.

## Task E — Final report

Return one of:

- `READY_FOR_SPECIFIC_PHYSICAL_APPROVAL`
- `BLOCKED_TIMING_EVIDENCE`
- `BLOCKED_RECOVERY_SAFETY`
- `BLOCKED_SERVICE_OWNERSHIP`
- `BLOCKED_OTHER`

Explain precisely what was fixed and what still prevents MCU first light.

Preserve the working Nuxel boot, kernel, device trees and recovery images.

Do not proceed to accelerometer/gyroscope validation until genuine MCU first light has been physically verified.

