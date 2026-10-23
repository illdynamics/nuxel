# A52 Hardware Inventory — Samsung Galaxy S10+ (beyond2lte) Camera

All entries below are **observed** on the running device (read-only sysfs/ioctl), with
expected-shipped hardware clearly separated.

## Identity

| Field | Value |
|---|---|
| Device tree model | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` |
| Compatible | `samsung,armv8`, `samsung,exynos9820` |
| Kernel | `Linux fedora 4.14.253 #15 SMP PREEMPT aarch64` |
| Bootloader | `G975FXXSEFUL1` |
| Serial | `R58M75KDB2X` |
| Firmware class path | `/vendor/firmware` (path does NOT exist on this rootfs) |

## Camera sensor modules (observed, from `/sys/devices/svc/Camera/`)

| Role | SVC module string | Sensor (kernel device) | I²C |
|---|---|---|---|
| Rear main | `SVC_rear_module = OVMED0EDF080101` | `fimc-is_sensor_2l4@20` → `FIMC-IS-SENSOR-MODULE-2L4` | cis @ bus2 |
| Rear tele | `SVC_rear_module2 = CVME80C33005701` | `fimc-is_sensor_3m3@5A` → `FIMC-IS-SENSOR-MODULE-3M3` | cis |
| Rear UW | (in rear module2) | `fimc-is_sensor_3p9@2D` → `FIMC-IS-SENSOR-MODULE-3P9` | cis |
| Front | `SVC_front_module = PVMFF02C2030F04` | `fimc-is_sensor_3j1@10` → `FIMC-IS-SENSOR-MODULE-3J1` | cis @ bus6 |
| Front IR/depth | (in front module) | `fimc-is_sensor_4ha@10` → `FIMC-IS-SENSOR-MODULE-4HA` | cis |

> **Correction vs historical policy** (`configs/nuxel/camera/camera.json`): the front main
> sensor is **`s5k3j1`** (10 MP, ISOCELL 3J1), not the `s5k2l4sx_front` name in the old
> manifest. The front depth sensor matches `s5k4h7` (kernel device `4ha`).

## ISP / support devices (observed)

- FIMC-IS core: `170e0000.fimc_is` (`/sys/bus/platform/drivers/exynos-fimc-is`), probe `end`.
- FIMC-IS sensor controllers: `17030000`, `17040000`, `17050000`, `17050000.fimc_is_sensor2`,
  `17060000`, `17090000` (`exynos-fimc-is-sensor`).
- OIS/actuator: `sensor_ak737x_actuator_probe done` ×3 (I²C `3-000c`, `3-000f`, `8-000c`),
  OIS controller `10-0051 = exynos5-fimc-is-ois`.
- Calibration EEPROM: `fimc_is_eeprom_i2c 1-0051[2]`, `3-0050[0]`, `8-0051[1]` probed.
- MIPI CSI PHYs: `dphy_m4s4_csis0`, `dphy_m0s4s4s4_csis1/2/3`, `csis3_1` created.
- GDC (geometric distortion correction): `camerapp-gdc 17530000.gdc` (M2M), probed.
- Reserved memory: `secure_camera`, `camera_contig`, `camera` ION heaps; `fimc-is library/DDK/RTA` memory.

## V4L2 node classes (observed)

| Class | Nodes | Role |
|---|---|---|
| `s5p-mfc-dec0/enc0` (+secure) | video6-11 | MFC video codec (M2M) — NOT camera |
| `exynos-jpeg` | video12 | JPEG codec (M2M) — NOT camera |
| `exynos5-scaler:m2m` | video50 | scaler (M2M) — NOT camera |
| `camerapp-gdc:m2m` | video155 | GDC warp (M2M) — camera post-process |
| `exynos-fimc-is-ss0..ss5` | video101-106 | sensor sub-stream |
| `exynos-fimc-is-30{s,c,p,f,g}` | video110-114 | sensor-slot 0 pipeline |
| `exynos-fimc-is-31{s,c,p,f,g}` | video120-124 | sensor-slot 1 pipeline |
| `exynos-fimc-is-32{s,p}` | video250-251 | sensor-slot 2 pipeline |
| `exynos-fimc-is-i0{s,c,p}`, `i1{s,c,p}` | video130-142 | ISP input |
| `exynos-fimc-is-me0c`, `me1c` | video148-149 | |
| `exynos-fimc-is-m0s..m5p`, `vra` | video160-180 | metadata / VRA |
| `exynos-fimc-is-ssinstancevc0..vc3` ×6 | video210-233 | virtual channels |

## Firmware / calibration status

- **No camera setfiles or ISP firmware on disk.** `/vendor` does not exist;
  `/lib/firmware` contains only Wi-Fi (`bcmdhd_*`, `nvram.txt`) and `regulatory.db`.
- Firmware-load failures observed at boot are audio/vibration only:
  `vts.bin` (samsung-vts), `calliope_sram.bin` / `calliope_sram_2.bin` (ABOX audio DSP).
- No camera `s5k*_setfile.bin`, `is_fw.bin`, `exynos9820_camera.bin`, `camera_calibration.bin`.
- Boot log warning: `[WRN]invalid fimc-is library memory address, use default` (non-fatal).
- Boot log errors (non-fatal to enumeration): `rear_tof_sensor_id read is fail`,
  `front_tof_sensor_id read is fail`, `use_ois_hsi2c not use(0)`, `3J1 power_seq_id read is fail`.

## Verdict

Hardware **present and driver-enumerated** (all 5 sensors bound, ISP probed, OIS/EEPROM present),
but **no capture is possible** through the standard V4L2 interface (see
`MEDIA-PIPELINE-ANALYSIS.md` and `HARDWARE-BLOCKERS.md`).
