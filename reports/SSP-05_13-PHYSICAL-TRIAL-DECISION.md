# SSP-05_13 — Physical First-Light Decision

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## A. Hardware confidence

| Item | Conclusion |
|---|---|
| Power dependency (rail) | `vdd_mcu_1p8` (LDO21M) — CONFIRMED (`ssp_dev.c:462`, DT `ssp-vdd-mcu-1p8`) |
| Power dependency (domain gate) | `GPS_PWR_EN` = **gpg0-2** (GNSS domain) — CONFIRMED (`bcm_gps_spi.c:1169`, reverse-DTS `samsung,pins="gpg0-2"`) |
| GPIO ownership | gpg0-2 = `bcm_gps_spi.c` (exported, never asserted); MCU_REQ/RESP = virtual `ssp-gpio` |
| Signal semantics | `GPS_PWR_EN` = GNSS domain enable (active-HIGH); NOT MCU power; NOT reset/standby |
| Initialization order | rail ON → `GPS_PWR_EN` HIGH (gpsd) → autobaud → GetVersion |
| Uncertainties | (a) GPS_PWR_EN rise→ROM-ready delay (no vendor value in tree); (b) whether asserting GPS_PWR_EN energises GNSS RF unsafely |

## B. Proposed first-light mechanism

- **Interface:** the existing exported sysfs symlink `/sys/class/sec/gps/GPS_PWR_EN`
  (created by `bcm_gps_spi.c:1223`), driven high via a **single bounded write**.
- **Why appropriate:** it is the exact control the stock `gpsd` uses; it gates
  the GNSS boot-ROM that the ROM GetVersion probe (`bcm477x_rpc_get_version()`)
  targets.
- **Affected components:** BCM47752 GNSS core (logic + RF), the SSP/SPI slave
  for the GNSS ROM path.  The sensor-hub MCU (`vdd_mcu_1p8`) is unaffected.
- **Health observation:** monitor `GPS_PWR_EN` readback, MISO transition from
  `0xFF`, `HSI_CTRL` from `0xFFFFFFFF`, and the ROM GetVersion reply framing.
- **Failure recovery:** write `GPS_PWR_EN` back LOW (assert/restore previous
  `0` state), then re-run rail cold-cycle (S0) to return to the known baseline.

## C. Safety assessment

**NOT established safe for an unconditional trial.**  The two documented
uncertainties (§A) are material:

1. Asserting `GPS_PWR_EN` energises the **GNSS RF domain** together with logic;
   in a native-Linux context without the proprietary gpsd power-sequencing and
   RF control, this is an **unresolved shared-rail/domain hazard** (the prior
   `05_12` report explicitly flagged it as a reboot/RF risk).
2. No vendor evidence exists for the post-power delay or any required RF
   sequencing before the boot-ROM is safe to talk to.

Therefore the trial **cannot** be justified as safe on current evidence.

## D. Authorization

A bounded physical trial is **NOT authorized/requested** at this time.  The
minimum additional evidence required to justify it is:

1. Broadcom BCM47752 datasheet power domain & `GPS_PWR_EN` assertion sequence
   (logic-vs-RF domain separation, post-power timing).
2. Samsung `gpsd`/`lhd` disassembly showing the exact `GPS_PWR_EN` assertion
   order, post-power delay, and any RF de-energisation step.
3. Owner confirmation that energising the GNSS domain (logic+RF) on this
   device is acceptable and bounded.

Until ≥1 of these is available, the correct record is: **do not perform the
trial**.
