# A52 Camera — Evidence Index

**Date:** 2026-10-22 (Europe/Amsterdam)
**Host:** macOS (Apple T6000), USB Live Console at `/dev/cu.usbmodem201`
**Device:** Samsung Galaxy S10+ SM-G975F "beyond2lte", Exynos 9820, Linux 4.14.253 aarch64
**Branch:** `nuxel/A52-penguin-camera` (created from `nuxel/A50-operation-smooth-penguin` @ 9fe0ebc)
**Method:** read-only hardware discovery first; every device command executed over the
serialised USB console with SHA-256-verified framing (`nuxel-live.sh --run` / `--batch`).

## Receipts (command → key observation)

| # | Command (abridged) | Observation | Verdict |
|---|---|---|---|
| 1 | `uname -a; cat /proc/cmdline; /proc/device-tree/model` | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820`, kernel `4.14.253`, bootloader `G975FXXSEFUL1`, `firmware_class.path=/vendor/firmware`, `reserve-fimc=` | identity confirmed |
| 2 | `ls /dev/video*; cat /sys/class/video4linux/*/name` | ~74 video nodes: `s5p-mfc-*` (codec), `exynos-jpeg` (codec), `exynos5-scaler:m2m`, `camerapp-gdc:m2m`, `exynos-fimc-is-*` (camera ISP). No `/dev/v4l-subdev*`, no `/dev/media*` | nodes present |
| 3 | `ls /sys/devices/platform/fimc-is_sensor_*` | `fimc-is_sensor_2l4@20`, `_3m3@5A`, `_3p9@2D`, `_3j1@10`, `_4ha@10` all bound | sensors bound |
| 4 | `journalctl -k -b0 | grep fimc_is` | `fimc_is_probe:end`, `SMC_SECCAM_*` OK, `sensor_ak737x_actuator_probe done` ×3, `fimc_is_eeprom_i2c … probed` ×3, `cis_4ha_probe sensor_id 3` | ISP+OIS+EEPROM probed |
| 5 | `ls /vendor/firmware /lib/firmware` | `/vendor` does not exist; `/lib/firmware` = `bcmdhd_*`, `nvram.txt`, `regulatory.db` only | **no camera setfiles** |
| 6 | `command -v v4l2-ctl media-ctl pipewire wireplumber pw-cli wpctl libcamera-hello cam` | all absent | **no capture tooling** |
| 7 | `command -v gst-launch-1.0; gst-inspect-1.0 | grep v4l2` | `gst-launch-1.0` present; `v4l2src` element **absent** (only `videotestsrc`) | **no GStreamer V4L2 source** |
| 8 | `command -v python3` | Python 3.14.7 present | usable for diagnostics |
| 9 | `nuxel-v4l2-probe.py` (QUERYCAP) | nodes report `driver=exynos-fimc-is-`, `caps=0x8420xxxx` = `DEVICE_CAPS|STREAMING|EXT_PIX_FORMAT|…_MPLANE`; ENUM_FMT yields nothing | **vendor MPLANE + EXT_PIX_FORMAT** |
| 10 | `nuxel-v4l2-capture-test.py` (S_FMT/REQBUFS/QUERYBUF) | `S_FMT` → **ENOTTY (errno 25)**, `REQBUFS`/`QUERYBUF` → EINVAL on video110/111/112/160 | **no standard V4L2 streaming** |
| 11 | `systemctl list-units` | running: `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-portal`, `nuxel-wayland`, `nuxel-wl-fb`, …; **no camera service, no PipeWire/portal** | userspace media chain absent |
| 12 | `cat /sys/class/thermal/thermal_zone*/temp` | 21.3–27.0 °C | cool, no thermal risk |
| 13 | `cat /proc/loadavg` | 11.88 (pre-existing; `exynos-pcie` link-retraining loop in dmesg, unrelated to camera) | noted, not caused by this work |

## Expected vs observed (hardware)

- **Expected (shipped S10+ hardware, from spec):** rear 12 MP `s5k2l4`, 12 MP tele `s5k3m3`,
  16 MP UW `s5k3p9`; front 10 MP `s5k2l4sx`-class + 8 MP depth `s5k4h7`.
- **Observed (running kernel):** rear main `2l4@0x20`, rear tele `3m3@0x5A`, rear UW `3p9@0x2D`,
  front `3j1@0x10` (NOT `s5k2l4sx` — corrected), front IR/depth `4ha@0x10`.
  Module IDs: `SVC_rear_module=OVMED0EDF080101`, `SVC_rear_module2=CVME80C33005701`,
  `SVC_front_module=PVMFF02C2030F04`.

## Verdict

**HARDWARE_BLOCKED — Scenario E.** All camera hardware (5 sensors + ISP + OIS + EEPROM) is
enumerated and bound at the driver level, but the vendor FIMC-IS driver exposes a proprietary
capture interface (`V4L2_CAP_EXT_PIX_FORMAT`, `VIDIOC_S_FMT → ENOTTY`) that requires the
proprietary Samsung camera HAL (libexynoscamera) and Android framework, which are not installed
and cannot be lawfully/cleanly installed into Fedora ARM64. No real frame was captured.
