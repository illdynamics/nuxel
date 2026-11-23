# SSP-05_11 — ROM First-Light Readiness

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Status:** `ROM_FIRST_LIGHT_NOT_YET_ATTEMPTED`

## Why no genuine ROM GetVersion yet

A genuine framed, length+CRC-valid RPC-0 GetVersion requires, in order:

1. A deployed 0025 kernel (cold-cycle regulator_force_disable) — **DONE this session** (boot verified).
2. A bounded, separately-authorized MCU power transition — **NOT authorized/executed**.
3. The tested userspace `--rom-probe` (autobaud + GetVersion).

Only step 1 is complete. Steps 2 and 3 are upstream of ROM first light.

## Deployed-but-unprobed state (read-only)

- mcu_power sysfs node live (0025 deployed).
- BBD raw transport nodes present.
- Corrected userspace BBD tooling present.
- Regulator vdd_mcu_1p8 still enabled with num_users=0.

## Offline gate status (all PASS, prior sessions)

- nuxel_bbd_flash framing + F1 + RX decode, negative cases, embedded patch.
- --rom-probe structurally incapable of MemoryWrite/StartScratchApp/ServiceStart.
- Orientation 77/77, recovery 14/14, boot packer 9/9, kernel source audit 4/4.
- Firmware downloader offline checks pass.

## Required device evidence for ROM first light (none yet)

- Raw received bytes (non-zero; not silent).
- Valid protocol framing.
- Correct response length and CRC.
- Expected GetVersion identity.
- No synthetic success indicators.

## Stage 06 readiness unmet gates (exact)

| Gate | Status |
|---|---|
| Nuxel boots normally with intended kernel | PASS (this session) |
| Recovery baseline valid | PASS |
| BOOT/DTB/DTBO integrity verified | PASS |
| Corrected raw BBD transport works | PASS (nodes present; device traffic not yet exercised) |
| Genuine ROM GetVersion validated | NOT RUN |
| Firmware downloader offline checks | PASS (offline) |
| MCU power transition separately authorized + safe | NOT AUTHORIZED |

## Decision

`ROM_READY = FALSE` — `BOOT_DEPLOYED_POWER_TRIAL_PENDING` upstream. No physical
ROM probe may run until a separately-authorized, bounded MCU power transition is
completed and the shared-rail question is resolved.
