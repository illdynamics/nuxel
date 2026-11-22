# SSP-05_14 — Hardware Model (consolidated)

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), Exynos 9820, BCM47752

This model carries forward the 05_13 consolidated analysis (which is correct) and
adds no new claims.  The BCM47752 has two functionally separate power/comm domains:

| Domain | Power gate | Owner | Live state |
|---|---|---|---|
| Sensor-hub MCU | vdd_mcu_1p8 (LDO21M, always-on) | SSP driver (ssp_dev.c) | enabled, num_users=0 |
| GNSS (logic+RF) | GPS_PWR_EN (gpg0-2, active-HIGH) | bcm_gps_spi.c → gpsd (userspace) | LOW (never asserted) |

Signals (definitive, from 05_13 GPIO-OWNERSHIP.md):
- GPS_PWR_EN = gpg0-2 (NOT gpg4), GNSS domain enable.
- MCU_REQ = gpg4-1, MCU_RESP = gpg4-2 (wake handshake, virtual ssp-gpio).
- SHUB_EN (ssp-pwr-en) ABSENT on beyond2lte (regulator-only MCU rail).
- vdd_mcu_1p8 = LDO21M (no GPIO gate on this board).

## This session's delta

The 0029-corrected regulator core is now DEPLOYED and BOOTED.  The regulator
cold-cycle (S0 state machine) is symmetric and framework-safe.  The GNSS-domain
gate (S0→S1, GPS_PWR_EN) remains the single un-resolved hardware blocker for ROM
first light, and is NOT part of this BOOT-only deployment.
