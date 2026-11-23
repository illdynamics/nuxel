# SSP-05_11 — MCU Power-Safety Review

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Scope:** Read-only. **No MCU power transition performed this session.**

## Status

**`BLOCKED_POWER_SAFETY`** (automatic/cyclic rail discharge forbidden).
No rail transition and no `GPS_PWR_EN` manipulation was performed.

## Live observation (post-boot, read-only)

- `vdd_mcu_1p8` regulator: `state=enabled`, `num_users=0`.
- 0025 `mcu_power` sysfs node present at `/sys/devices/virtual/sec/sensorhub/mcu_power`, current value `1`.

This confirms the 0025 correction (mcu_power case 0 -> regulator_force_disable) is
deployed and available. The rail still shows the historical bootloader-left-up /
zero-kernel-reference state (`num_users=0`), which is the cold-start blocker.

## Unresolved shared-rail question (still gates any physical transition)

- `vdd_mcu_1p8` (MCU 1.8 V rail) vs `GPS_PWR_EN` (gpio-145, GNSS standby GPIO).
- `num_users=0` does NOT prove the rail has no other physical consumers.
- A `regulator_force_disable` could briefly cycle any GNSS sharing the rail.

## Pre-transition requirements (all must hold before ANY trial)

1. Establish the regulator's actual ownership and consumers (live read).
2. Confirm a forced disable cannot interrupt other hardware.
3. Review the driver-owned initialization sequence.
4. Identify the minimum bounded operation (echo 0 -> poll disabled -> echo 1 -> poll enabled -> --rom-probe, single cycle).
5. Document abort and recovery conditions.
6. Obtain SEPARATE owner authorization for this specific transition.

## Decision rule

- Automatic / periodic / service-retry cold-cycle: FORBIDDEN.
- Bounded operator-supervised cold-cycle: only under separate owner authorization.
- `GPS_PWR_EN`: never touched.

## Status

`BLOCKED_POWER_SAFETY` (auto) / `AWAITING_POWER_TRIAL_AUTHORIZATION` (bounded, supervised).
