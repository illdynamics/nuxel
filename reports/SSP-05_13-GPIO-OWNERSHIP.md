# SSP-05_13 — GPIO Ownership & Signal Semantics (definitive)

**Date:** 2026-11-23 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F `beyond2lte` (Exynos 9820)

## 1. Summary verdict

The BCM47752 has **two independent power/communication domains** with **two
independent owners** in the stock Samsung kernel.  The prior agent (`05_12`)
conflated the GNSS domain-enable (`GPS_PWR_EN`) with the sensor-hub MCU power
gate.  Source analysis shows these are distinct signals on distinct physical
pins, owned by distinct drivers, and the reconciliation is:

- `GPS_PWR_EN` (gpg0-2) is the **GNSS/RF+logic domain enable**, owned by the
  GPS SPI driver (`bcm_gps_spi.c`), set LOW at probe and delegated to
  userspace `gpsd` for assertion.  It is **NOT** the MCU/sensor-hub power gate.
- The sensor-hub MCU is powered by the `vdd_mcu_1p8` regulator (LDO21M),
  owned by the SSP driver (`ssp_dev.c` / `ssp_sysfs.c`), gated by `shub_en`
  (`ssp-pwr-en`) which is **absent** on beyond2lte.

Both can be true simultaneously because the BCM4773/47752 is a single
integrated die with **functionally separate GNSS and sensor-hub power domains**.

## 2. Signal ownership table

| Signal | DTS property | Physical pin | Flash flag | Direction | Owner | Role |
|---|---|---|---|---|---|---|
| `GPS_PWR_EN` | `ssp-gps-pwr-en` | **gpg0-2** | GPIO_ACTIVE_HIGH (0) | output | `bcm_gps_spi.c` (GPIO driver) | GNSS logic/RF domain enable |
| `MCU_REQ` | `ssp-mcu-req` | gpg4-1 | ASIS (0xffffffff) | output | BCM4773 virtual `gpio-controller` (`ssp-gpio`) | wake request to MCU |
| `MCU_RESP` | `ssp-mcu-resp` | gpg4-2 | ASIS | input | BCM4773 virtual `gpio-controller` | wake ack from MCU |
| `HOST_REQ` | `ssp-host-req` | (gpa1 bank) | ASIS | input | BCM4773 virtual gpio (→ AP IRQ) | data-ready interrupt |
| `SHUB_EN` | `ssp-pwr-en` | ABSENT (= -2) | — | — | `ssp_dev.c` | sensor-hub rail gate (not present) |
| `vdd_mcu_1p8` | `ssp-vdd-mcu-1p8` | LDO21M | — | regulator | `ssp_dev.c` | 1.8 V MCU core rail |

## 3. Critical correction to prior report (`05_12`)

The `05_12` report asserted `GPS_PWR_EN = gpio-145` and (implicitly) that it is
the chip power gate "gpg4".  Both are imprecise:

1. **Physical pin identity** — the Exynos 9820 pinctrl reverse-DTS shows the
   `ssp-gps-pwr-en` node binds to `samsung,pins = "gpg0-2"`:

   `kernel/s10plus/.build/out/arch/arm64/boot/dts/samsung/exynos9820-beyond1lte_eur_open_23.dtbo.reverse.dts:44-53`
   ```
   ssp-gps-pwr-en {
       samsung,pins = "gpg0-2";
       samsung,pin-function = <0x1>;   // output
       samsung,pin-pud      = <0x1>;   // pull-down
       ...
   ```
   So `GPS_PWR_EN` = **gpg0-2** (PERIC0, bank `gpg0`, `eint_off=0x10`,
   `nr_pins=8`, per `pinctrl-exynos-arm64.c:488`).  `MCU_REQ`/`MCU_RESP` are on
   a *different* bank `gpg4` (PERIC0, `eint_off=0x1C`, `nr_pins=4`,
   `pinctrl-exynos-arm64.c:490`).  GPIO number 145 is the runtime number for
   gpg0-2, but the physical identity is gpg0-2, not gpg4.

2. **Signal semantics** — the source shows `bcm_spi_probe()` requests GPS_PWR_EN
   under the label "GPS_PWR_ON" (the commented block) then "GPS_PWR_EN",
   configures it as **output LOW**, and exports it to userspace:
   `bcm_gps_spi.c:1204-1225`.  It is never toggled HIGH by any kernel code
   (`grep` across `drivers/sensorhub/` returns only these probe lines), and is
   never stored in `struct bcm_spi_priv` (which holds only `host_req`,
   `mcu_req`, `mcu_resp` — `bcm_gps_spi.h:154-157`).

## 4. Signal semantics per signal

### 4.1 GPS_PWR_EN (gpg0-2)
- **Role:** GNSS domain enable (logic + RF).  Active-HIGH (DT flag 0x0 =
  `GPIO_ACTIVE_HIGH`; kernel drives a raw `1`/`0`).
- **Evidence of semantics:** the commented request is labeled "GPS_PWR_ON";
  the driver exposes it under `/sys/class/sec/gps/GPS_PWR_EN` precisely so the
  proprietary userspace `gpsd` can assert it.  It is never asserted by kernel.
- **NOT** an MCU/sensor-hub wake or reset (those are `MCU_REQ`/`MCU_RESP`,
  which are virtual GPIOs exported by the BCM4773's own gpio-controller).

### 4.2 MCU_REQ / MCU_RESP (gpg4-1 / gpg4-2)
- **Role:** MCU wake handshake.  `bcm477x_hello()` (`bcm_gps_spi.c:496-538`)
  asserts `mcu_req=1` and polls `mcu_resp` (up to 100 ms) to confirm the MCU is
  awake; `bcm477x_bye()` asserts `mcu_req=0`.
- These are the **only** GPIOs toggled by the kernel during ROM first-light.
  `GPS_PWR_EN` is not part of this handshake.

### 4.3 SHUB_EN (ssp-pwr-en)
- **Role:** sensor-hub rail gate (would gate `vdd_mcu_1p8`).  **Absent** on
  beyond2lte (`of_get_named_gpio(...,"ssp-pwr-en")` returns -2, confirmed by
  `05_12` dmesg).  Therefore the sensor-hub MCU is powered directly by the
  regulator with no GPIO gate.

## 5. Do GNSS and sensor-hub share hardware dependencies?

They share the same die and the same SPI bus controller, but have **separate
power gates**:
- GNSS domain: `GPS_PWR_EN` (gpg0-2) — asserted by gpsd.
- Sensor-hub MCU domain: `vdd_mcu_1p8` (LDO21M) with no GPIO gate on this
  board (SHUB_EN absent).

The ROM GetVersion probe targets the **GNSS boot-ROM** (SSI/HSI serial-over-SPI
via `/dev/ttyBCM`), so it requires the **GNSS domain** to be powered, i.e.
`GPS_PWR_EN` asserted.  The sensor-hub SSP path is a different protocol
(BBD/SSP packets over the same physical SPI) and is gated by the regulator
alone.

## 6. Boot-ROM wake vs power-enable

The boot-ROM does **not** require an additional "wake handshake" beyond power;
`bcm477x_rpc_get_version()` (`bcm_gps_regs.c:46-158`) sends autobaud (32 ×
0x80) then GetVersion RPC (14-byte frame) and polls for a response.  The
`bcm477x_hello()` MCU_REQ/RESP handshake happens at the **transport open**
level (`bcm_on_packet_received`/stream path), not inside the ROM GetVersion
itself.  With `GPS_PWR_EN=0` the ROM never runs, so MISO reads `0xFF`
(bus not driven), SSI TX overflows, and GetVersion returns nothing — exactly
the `05_12` observations.

## 7. Source references

- `drivers/sensorhub/brcm/bbdpl/bcm_gps_spi.c:1155-1225` (probe GPIO parsing +
  GPS_PWR_EN request/export LOW)
- `drivers/sensorhub/brcm/bbdpl/bcm_gps_spi.c:496-544` (hello/bye MCU handshake)
- `drivers/sensorhub/brcm/bbdpl/bcm_gps_spi.h:140-168` (priv struct, no gps_pwr_en)
- `drivers/sensorhub/brcm/bbdpl/bcm_gps_regs.c:46-158` (ROM GetVersion autobaud)
- `drivers/sensorhub/brcm/ssp_dev.c:462-491` (vdd_mcu_1p8 + shub_en parse)
- `drivers/sensorhub/brcm/ssp_sysfs.c:534-592` (mcu_power sysfs)
- `drivers/pinctrl/samsung/pinctrl-exynos-arm64.c:488,490` (gpg0/gpg4 banks)
- `kernel/.../exynos9820-beyond1lte_eur_open_23.dtbo.reverse.dts:44-53,93-111`
  (ssp-gps-pwr-en = gpg0-2; MCU req/resp on gpg4)
