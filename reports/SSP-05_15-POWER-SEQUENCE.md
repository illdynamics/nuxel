# SSP-05_15 — Power-Sequence Evidence (final reconciliation)

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Objective

Verify the exact physical GPIO mapping, signal polarity, ownership, power-domain
dependencies, whether the ROM endpoint needs GNSS-domain init, the stock init
sequence, the safe transition mechanism, and current owner — using source, not
prior reports as substitutes.

## 1. Signal table (source-verified this mission)

| Signal | DT prop | Physical pin | Polarity | Direction | Kernel owner | Live value |
|---|---|---|---|---|---|---|
| GPS_PWR_EN | `ssp-gps-pwr-en` | gpg0-2 = **gpio145** | active-HIGH | output | `bcm_gps_spi.c` (exported to `/sys/class/sec/gps/GPS_PWR_EN`) | **0** (LOW) |
| MCU_REQ | `ssp-mcu-req` | gpg4-1 = gpio167 | — | output | virtual `ssp-gpio` | 0 |
| MCU_RESP | `ssp-mcu-resp` | gpg4-2 = gpio168 | — | input | virtual `ssp-gpio` | 1 |
| HOST_REQ | `ssp-host-req` | gpa1 bank (data-ready) | — | input | `bcm_gps_spi.c` (IRQ `ttyBCM`) | 0 |
| vdd_mcu_1p8 | `ssp-vdd-mcu-1p8` | LDO21M | — | regulator | `ssp_dev.c` | enabled, num_users=0 |

Live evidence: `GPS_PWR_EN -> .../gpiochip50/gpio/gpio145`, direction=out,
value=0. `vdd_mcu_1p8` regulator.62 state=enabled num_users=0.
`mcu_power` sysfs = 1.

The prior 05_13/05_14 finding is **confirmed and refined**: GPS_PWR_EN is gpg0-2
(gpio145), NOT gpg4. Polarity is active-HIGH. Ownership is the `bcm_gps_spi.c`
driver which sets it output-LOW at probe and exports it for userspace.

## 2. Power-domain dependencies

Two functionally separate gates on the single BCM47752 die:

- **Sensor-hub MCU**: `vdd_mcu_1p8` (LDO21M) — no GPIO gate on beyond2lte; owned by SSP driver. Enabled.
- **GNSS (logic+RF)**: `GPS_PWR_EN` (gpg0-2) — asserted by userspace gpsd/lhd. Currently LOW.

Asserting `GPS_PWR_EN` energises the GNSS domain (logic + RF). It does NOT
energise the sensor-hub MCU (that is the regulator, already on).

## 3. Does the ROM endpoint require GNSS-domain init?

**Yes.** The GNSS boot-ROM is power-gated by `GPS_PWR_EN`. With it LOW, MISO
reads 0xFF (idle), SSI TX overflows, and no ROM reply is possible — exactly the
historical rx=0 observations.

However — **new evidence this mission** — `nuxel-gnss-lhd.service` DID assert
`GPS_PWR_EN=1` at boot (`power={'success': True, 'enabled': True}`) and the
receiver was STILL silent (handshake `gps: False`). So GPS_PWR_EN is **necessary
but not sufficient**: the sensor-hub MCU/BBD app bring-up (the vendor `lhd` patch
download) is the additional missing step (see GPS-BLOCKERS.md B0).

## 4. Stock initialization sequence (source-verified)

Recovered from `bcm_gps_spi.c` probe and `bcm_gps_regs.c`:

1. `vdd_mcu_1p8` rail on (regulator / SSP driver). — present in Nuxel.
2. `GPS_PWR_EN=HIGH` (gpg0-2) — performed by userspace `gpsd`/`lhd`, NOT kernel. — Nuxel asserts it at boot via nuxel-gnss-lhd, but no position decode follows.
3. GNSS boot-ROM autobaud window (32 × 0x80).
4. MCU_REQ/RESP hello handshake (`bcm477x_hello`) at transport open.
5. GetVersion RPC → valid framed reply (performed by proprietary lhd).

The `bcm477x_rpc_get_version()` in the tree is **dead code** (no callers); the
live ROM GetVersion is done by lhd over BBD RPC. Nuxel's native bridge reaches
step 2 (transport ready) but has no equivalent for the proprietary lhd RPC map
(step 5) and does not perform the sensor-hub patch download.

## 5. Known safe transition mechanism

The vendor mechanism is a **GPIO sysfs write** to `GPS_PWR_EN` (the
`gpio_export(gps_pwr_en,1)` in probe makes `/sys/class/gpio/gpio145/value`
writable to root). `nuxel_control.py` already wraps this as
`GpsPowerControl.set_power()` with readback + lease semantics, and it has been
demonstrated safe at boot (bounded, restored in `finally`/`cleanup` via
`GPSD:CORE_OFF` + power release).

No regulator power-cycle, no reboot, and no raw register poke is required for
the GNSS-domain transition. The sensor-hub rail cold-cycle (0025/0028/0029) is a
**separate** mechanism for a halted MCU and is not part of the GNSS GPS_PWR_EN
transition.

## 6. Current owner of the signal

- **Kernel**: `bcm_gps_spi.c` holds the GPIO (requested as "GPS_PWR_EN"), currently driven LOW.
- **Userspace**: no process currently owns it. `nuxel-gnss-lhd.service` is inactive (it releases the rail in cleanup). `/sys/class/sec/gps/GPS_PWR_EN` and `/sys/class/gpio/gpio145` are root-writeable.

No other kernel or userspace component currently holds GPS_PWR_EN. A single
bounded trial can therefore exclusively own it without conflict.

## 7. Conclusion

The power-sequence evidence is **now complete on every point required by Section
3**: exact pin (gpg0-2/gpio145), polarity (active-HIGH), ownership (kernel
exported, userspace-delegated, currently unowned), domain dependency (GNSS logic
+ RF), stock sequence (recovered), safe transition (GPIO sysfs write with
readback, already wrapped), and current owner (none). The only remaining
non-source-verifiable item is the proprietary lhd post-power timing and the
GNSS RF-safety policy, which is an owner authorization matter, documented in the
physical-trial-decision report.
