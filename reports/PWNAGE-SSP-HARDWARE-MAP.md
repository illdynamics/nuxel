# PWNAGE-SSP — Hardware map (measured, not assumed)

| Item | Value | How verified |
|---|---|---|
| Device | SM-G975F `beyond2lte`, Exynos 9820 | `ro.product.device/model` in TWRP; DT board string |
| Sensor hub | Broadcom **BCM47752KUB1G** | `mcu_name` sysfs, live |
| Hub firmware string | `BR0121080900,BR010` | `mcu_rev` sysfs, live |
| Accel + gyro | STM **LSM6DSO** behind the hub | `/sys/class/sensors/{accelerometer,gyro}_sensor/name` = `LSM6DSO` |
| DT node | `BCM4773@0`, compatible `ssp,BCM4773`, SPI7 (`spi@10970000`) | `exynos9820-beyond2lte_eur_open_04.dts` |
| Host-request line | `ssp-host-req` → GPIO IRQ `ttyBCM` | `/proc/interrupts` |
| Data-ready line | `ssp-shub-int` → IRQ 443 (GIC 443) | `/proc/interrupts`, `nuxel_hub_diag shub_irq=443` |
| MCU handshake | `ssp-mcu-req` / `ssp-mcu-resp` | DT + `bcm477x_hello()` |
| MCU rail | `vdd_mcu_1p8` | DT + `mcu_power` sysfs = 1 |
| SPI mode | full-duplex stream, 2-byte length, flow control, frame 8192 | dmesg `SPI @ 12000: Full Duplex Strm mode …` |
| Sensor mount position | `ssp-acc-position = 7` (DT fragment 112) | DT |
| Data path | SPI7 ⇄ BBD driver (`bbdpl/`) ⇄ `/dev/ttyBCM` + `/dev/bbd_sensor` ⇄ SSP state machine ⇄ `/sys/class/sensors/*` | reading drivers + live dmesg |
| Firmware source | kernel-embedded BBD patch, `AsicVersion=0x004775B0`, `BlobLength=438895`, CRC-32 `0x93D3F2B4`, served on `/dev/bbd_patch` | parsed header + on-device read (897 113 bytes) |

## Device nodes

| Node | Direction | Purpose |
|---|---|---|
| `/dev/ttyBCM` | R/W | SSI stream to the hub (kernel de-frames it) |
| `/dev/bbd_sensor` | R/W (Nuxel) | AP→MCU frames out, MCU→AP frames in to the SSP state machine |
| `/dev/bbd_control` | W | text control (`ESW:READY`, `SSI:PassThru=1`, debug) |
| `/dev/bbd_patch` | R | kernel-served sensor-hub patch image |

## Interfaces the vendor adds and Nuxel does not need

`/vendor/bin/hw/lhd` (Bionic daemon) and `sensors.sensorhub.so` / the Exynos sensor
HAL.  `lhd` requires `liblog libutils libz libhardware_legacy libc++ libc libm libdl`
from the Android runtime and is the only implementation of the MCU patch-download
RPC.  Nuxel speaks the BBD ABI directly; the missing piece is exactly that RPC.

## Unsafe substitutions rejected

* No firmware from another hub model (e.g. BCM47765 `SensorHub.patch`) was used.
* No DT/GPIO/IRQ/rail value was changed or guessed.
* No EFS/NV/calibration partition was read.
