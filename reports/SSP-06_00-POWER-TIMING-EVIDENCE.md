# SSP-06_00 — Power & Timing Evidence

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06 preflight
**Scope:** Reconcile the observed `GPS_PWR_EN` assertion with the earlier reboot
hazard, and determine exactly what timign evidence exists vs what is missing.

## 0. Verdict

`TIMING = PARTIALLY_RESOLVED` — ordering is source-proven; the **exact
GPS_PWR_EN-rise → ROM-autobaud-ready settle delay is UNKNOWN** and is reported as
missing evidence rather than substituted with an arbitrary value.

## 1. The two different hazards (now cleanly separated)

| Hazard | Nature | Status |
|---|---|---|
| Sensor-hub rail cold-cycle | regulator force-disable/enable (patches 0025/0028/0029) | FIXED — `vdd_mcu_1p8` live `enabled`, `num_users=0`, stable |
| `GPS_PWR_EN` GPIO assertion | gpio145 output-write (userspace) | REVERSIBLE — bounded ~23.7 s window in SSP-05_15, NO reboot |

The prior "reboot hazard" was the *regulator* cold-cycle. The `GPS_PWR_EN` assertion
was a *GPIO* write to a distinct domain and produced NO reboot, NO cross-subsystem harm,
and did NOT disturb the MCU rail. This is re-confirmed this mission (gpio145 val=0,
rail stable, systemd `running`, 0 failed units).

## 2. Live electrical state (re-collected this mission, read-only)

| Item | Value |
|---|---|
| `GPS_PWR_EN` | gpio145 (`gpg0-2`), direction=out, value=**0** |
| MCU handshake | gpio167 (`mcu_req`) out, gpio168 (`mcu_resp`) in |
| Host IRQ | gpio15 (`ssp-host-req`) input |
| Sensor-hub rail | `vdd_mcu_1p8` regulator.62, enabled, num_users=0 |
| MCU power | `mcu_power=1` |
| Hub diag | `mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0` |

`GPS_PWR_EN` and `vdd_mcu_1p8` are **distinct domains**. `bcm477x_hello()` toggles only
MCU_REQ/MCU_RESP; it never touches GPS_PWR_EN. GPS_PWR_EN is asserted only by userspace
GNSS bring-up, which (repo HEAD) now refuses before a verified protocol contract.

## 3. What IS known (source-proven readiness signals)

- The authoritative MCU-readiness signal is the **MCU_REQ→MCU_RESP handshake
  succeeding** (`bcm477x_hello` polls `mcu_resp` up to 100 count). This is observable,
  not an invented sleep.
- Ordering is fully recovered: rail on → MCU out of reset (probe) → MCU handshake →
  autobaud + GetVersion → MemoryWrite×479 → StartScratch(40 ms) → ServiceStart(100 ms) →
  post-download GetVersion.
- The two fixed delays inside the sequence (40 ms after StartScratch, 100 ms after
  ServiceStart) are recovered from the lhd encoders, NOT invented.

## 4. What is UNKNOWN (reported, not substituted)

- **`GPS_PWR_EN` rise → ROM autobaud-ready settle duration.** This is a Broadcom
  datasheet value, not derivable from GPL source or the lhd binary without the vendor
  datasheet. It is explicitly NOT guessed.
- **Whether the MCU handshake alone is sufficient** to gate the trial, or whether the
  GNSS domain (GPS_PWR_EN) must be energized *before* the MCU handshake for the GNSS ROM
  autobaud to respond. Stage 05_16 leans "GNSS ROM shares the MCU SSI slave select"; this
  is INFERRED, not directly asserted on-wire.

Because these are unknown, the trial specification (authorization doc) makes the
readiness gate the **observable MCU handshake**, bounds every step with explicit
timeouts, and does NOT hard-code a speculative power-settle delay. A conservative,
explicit, bounded settle wait may be added only if the owner provides the datasheet value
or an explicit instruction; absent that, no arbitrary delay is introduced.

## 5. Impact on the Stage 06 decision

Timing is **NOT** treated as fully resolved. It is the one externally-authored evidence
gap carried into the authorization boundary. The trial remains executable with the
handshake-as-gate approach, but the authorization document records the settle-delay gap
as a residual risk requiring either (a) owner provision of the datasheet value, or (b)
acceptance of handshake-gated readiness with bounded timeouts.
