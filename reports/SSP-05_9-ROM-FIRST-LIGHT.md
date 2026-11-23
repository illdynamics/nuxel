# SSP-05_9 — ROM First Light Status

**Date:** 2026-11-22 (Europe/Amsterdam)
**Status:** `ROM_FIRST_LIGHT_NOT_YET_ATTEMPTED` — prerequisite kernel build is now
complete, but no authorized physical ROM probe has been run.

## Why no genuine ROM GetVersion yet

ROM first light (a genuine, framed, length+CRC-valid RPC-0 GetVersion from the
BCM47752 boot ROM over the SSI link) requires, in order:

1. **A deployed 0025 kernel** (the `regulator_force_disable` cold-cycle fix) → this
   requires a BOOT-only flash of the candidate above (NOT yet authorized/executed).
2. **A bounded, separately-authorized MCU power transition** (force-disable → the
   boot-ROM autobaud window reopens) → blocked by the unresolved MCU–GNSS
   shared-rail question (see below). NOT executed.
3. The tested userspace `nuxel_bbd_flash --rom-probe` (bounded autobaud + GetVersion).

None of these physical steps were performed this prompt. No firmware MemoryWrite
or application-start was executed.

## MCU power-transition safety gate (unresolved — do not proceed blindly)

The 0025 correction changes `set_mcu_power` case 0 to `regulator_force_disable`,
which detaches ALL references and physically drops `vdd_mcu_1p8`. Before any such
transition on the live device, we MUST establish whether `vdd_mcu_1p8` is shared
with GNSS or any other active consumer. Live-verified evidence to date:

- `vdd_mcu_1p8`: `state=enabled`, `num_users=0` (bootloader left it up, no kernel refs).
- Declared consumer (source): `ssp_dev.c` only.
- Shared with GNSS? **UNRESOLVED.** `GPS_PWR_EN` (gpio-145) is the GNSS stand-by
  GPIO, which is a distinct control from the rail, but physical rail sharing
  cannot be excluded from source alone.

**Conclusion:** the physical `regulator_force_disable` transition must NOT be run
automatically. It requires a separate bounded power-transition plan with
driver-owned operation, source-backed expected effect, shared-consumer assessment,
max attempts, timeout, abort conditions, recovery, and GNSS/device-health checks —
and **explicit authorization** for that specific transition.

## What this prompt did achieve

- Repaired and completed the full kernel build (the prerequisite blocker).
- Produced and independently verified the BOOT-only 0025 candidate.
- Passed all mandatory offline regression tests.
- Confirmed the ROM-probe path is intact and tested offline.

## Next decision gate

Once (a) the candidate is flashed under separate BOOT-only authorization, (b) the
power-transition safety question is resolved and the bounded transition is
separately authorized and completed safely, and (c) the device is healthy — only
then run `--rom-probe` and require a genuine framed/CRC'd RPC-0 GetVersion.

A genuine GetVersion response is required for `READY_FOR_06`. It has not been
obtained yet.
