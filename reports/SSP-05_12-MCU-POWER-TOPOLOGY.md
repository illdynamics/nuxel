# SSP-05_12 — MCU Power Topology (corrected, hardware-verified)

**Date:** 2026-11-22/23 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), Exynos 9820
**Scope:** Source inspection + live hardware power-cycle testing (authorized)

---

## 1. Verdict: the BCM47752 power gate is GPS_PWR_EN, NOT just the rail

The prior `SSP-05_12-MCU-POWER-TOPOLOGY.md` concluded that `vdd_mcu_1p8`
(LDO21M) is the *sole* power rail and that `GPS_PWR_EN` is "a standby GPIO,
not a rail".  **This was incorrect.**  A live, symmetric cold-cycle (enabled →
disabled → enabled) on `vdd_mcu_1p8` was completed in-place, yet the chip's SPI
remained dead (MISO `0xFF`, `HSI_CTRL=FFFFFFFF`, SSI TX overflows).  The chip is
held POWERED DOWN by `GPS_PWR_EN` (gpio-145) = LOW, which the Nuxel SSP driver
drives to `0` at probe and never asserts.

## 2. Complete power topology (live + source evidence)

| Control | GPIO/Regulator | Live state | Role | Evidence |
|---|---|---|---|---|
| `vdd_mcu_1p8` | S2MPS19 LDO21M | enabled (num_users=0) | 1.8 V core rail | `/sys/.../regulator.62/state=enabled` |
| `GPS_PWR_EN` | `ssp-gps-pwr-en`=145 | **0 (LOW)** | chip logic power gate | `dmesg: ssp-gps-pwr-en=145`; sysfs value=0 |
| `ssp-pwr-en` (shub_en) | `-2` (ENOENT) | n/a | NOT present on SSP node | `dmesg: ssp-pwr-en=-2` |
| `ssp-mcu-req` | gpio-167 | 0 (LOW) | wake request line | `nuxel diag: mcu_req=0` |
| `ssp-mcu-resp` | gpio-168 | 1 (HIGH) | wake ack line | `nuxel diag: mcu_resp=1` |
| `ssp-host-req` | gpio-15 | 0 | host data-ready IRQ | `nuxel diag: host_req=0` |

### 2.1 `bcm_spi_probe` drives GPS_PWR_EN LOW (source)

`drivers/sensorhub/brcm/bbdpl/bcm_gps_spi.c:1287-1290`:
```c
if (gpio_request(gps_pwr_en, "GPS_PWR_EN")) { WARN(1, ...); }
ret = gpio_direction_output(gps_pwr_en, 0);   /* GPS_PWR_EN := 0 */
gpio_export(gps_pwr_en, 1);
gpio_export_link(gps_dev, "GPS_PWR_EN", gps_pwr_en);
```
Immediately above, the historical power-on request block is COMMENTED OUT:
```c
/*
if(gpio_request(gps_pwr_en, "GPS_PWR_ON")) { ... }
*/
```

### 2.2 DT evidence

`/sys/firmware/devicetree/base/spi@10970000/BCM4773@0/`:
- `ssp-gps-pwr-en` present (gpio phandle → 145); `samsung,pin-function=1` (output).
- `ssp-pwr-en` ABSENT (hence `of_get_named_gpio(...,"ssp-pwr-en")` = `-2`).
- `ssp-vdd-mcu-1p8` present (regulator name).

## 3. Why the rail cold-cycle alone is insufficient

The BCM47752 logic (boot-ROM, SPI slave, sensor hub) is powered by the 1.8 V
rail **AND** gated by `GPS_PWR_EN`.  With `GPS_PWR_EN=0` the chip stays in
power-down: the SPI MISO reads `0xFF` and SSI TX overflows with `Nread 65535`,
exactly as observed after a successful rail off→on cycle.  This is the real
reason the boot-ROM never answers GetVersion — it is not running.

## 4. Consumer matrix (corrected)

| Component | Power dependency | Evidence | Impact of rail cycle |
|---|---|---|---|
| BCM47752 MCU (sensor hub) | `vdd_mcu_1p8` + `GPS_PWR_EN` | source + live MISO 0xFF | rail cycle insufficient alone |
| BCM47752 GNSS RF | same die, same gates | single integrated die | same |
| SPI/SSI interface | gated by `GPS_PWR_EN` | `rx stat 0xff(PE)` | stays dead while GPS_PWR_EN=0 |

## 5. Not done / safety boundary

No write to `GPS_PWR_EN`/`MCU_REQ`/`MCU_RESP` was performed.  The only power
operation was the authorized `vdd_mcu_1p8` cold-cycle (now symmetric via 0028).
