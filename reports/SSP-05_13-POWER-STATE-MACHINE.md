# SSP-05_13 — Power & Communication State Machine

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## State set

| # | State | Meaning |
|---|---|---|
| S0 | MAIN_RAIL_ON | `vdd_mcu_1p8` (LDO21M) available |
| S1 | GNSS_DOMAIN_ON | `GPS_PWR_EN` (gpg0-2) asserted HIGH |
| S2 | MCU_AWAKE | MCU_REQ/RESP handshake completed (sensor-hub core) |
| S3 | SPI_READY | SPI controller + `/dev/ttyBCM` misc device live |
| S4 | ROM_AUTOBAUD | boot-ROM autobaud exchanged |
| S5 | ROM_GETVERSION | GetVersion RPC answered & validated |
| S6 | FW_RUNNING | firmware application started (out of scope) |

## Transition table

| From→To | Precondition | Owner | Observable | Vendor evidence | Failure | Recovery |
|---|---|---|---|---|---|---|
| boot→S0 | LDO21M always-on DT | regulator core / SSP driver | `regulator state=enabled` (num_users=0) | `ssp_dev.c:462` reads `ssp-vdd-mcu-1p8` | rail off | `regulator_force_enable()` (0028) |
| boot→S3 | `bcm_spi_probe` registered misc ttyBCM | GPS driver | `/dev/ttyBCM` exists | `bcm_gps_spi.c:1269-1280` | -EINVAL GPIO | probe err_exit |
| S0→**S1** | **gpsd asserts gpg0-2** | **userspace gpsd (missing in Nuxel)** | **GPS_PWR_EN readback = 1** | `bcm_gps_spi.c:1222` export; commented "GPS_PWR_ON" | **stuck LOW → MISO 0xFF** | **assert GPS_PWR_EN (NOT YET AUTHORIZED)** |
| S1→S4 | GNSS ROM waiting for autobaud after power | chip | MISO no longer all-ones | Broadcom datasheet (absent) | never reaches | — |
| S3→S2 | hello toggles mcu_req, polls mcu_resp | `bcm477x_hello()` | mcu_resp rises ≤100 ms | `bcm_gps_spi.c:496-538` | RESP timeout | `bcm477x_bye()` + retry |
| S4→S5 | autobaud 32×0x80, GetVersion RPC | `bcm477x_rpc_get_version()` | valid framed reply, CRC ok | `bcm_gps_regs.c:46-158` | rx=0 / NACK / CRC | bounded 2-attempt (32,36) |
| S5→S6 | MemoryWrite + ServiceStart | downloader | out of scope | 0027 excluded | — | — |

## Key invariant

**A powered regulator (S0) does NOT imply the GNSS core is running.**  The GNSS
boot-ROM is gated by a *separate* domain enable `GPS_PWR_EN` (S1), which is the
missing transition in Nuxel.  This reconciles the `05_12` observation: the rail
cold-cycle succeeded (S0 restored) yet ROM first-light still failed because S1
was never taken.

## Current reachable state (live, from 05_12)

`S0 ✓  S1 ✗ (stuck LOW)  S3 ✓  S2 ✗  S4 ✗  S5 ✗`

The blocker is exclusively the S0→S1 transition, which requires either the
proprietary gpsd power sequence or an explicitly-authorized, safety-validated
assertion of `GPS_PWR_EN`.
