# SSP-05_14 — ROM Endpoint Identity

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

The ROM GetVersion probe (bcm477x_rpc_get_version()) targets the GNSS boot-ROM,
serial-over-SPI via /dev/ttyBCM (SSI/HSI).  It requires the GNSS domain
(GPS_PWR_EN, gpg0-2) to be HIGH.

The sensor-hub MCU (vdd_mcu_1p8) is a SEPARATE domain using the BBD/SSP packet
protocol over the same physical SPI — gated by the regulator alone.

Endpoint = GNSS boot-ROM (bcm477x ROM), power-gated by GPS_PWR_EN.  This
session's 0029 deployment does NOT change endpoint identity; it only corrects
the regulator cold-cycle symmetry for the sensor-hub MCU rail.

`ROM_ENDPOINT_IDENTITY` remains NOT_RUN for live confirmation (no GPS_PWR_EN
assertion performed; ROM GetVersion still blocked by the GNSS power-gate).
