# NUXEL A72 / 21000 — 03-HARDWARE-DRIVER-MATRIX (fresh)

| subsystem | DT/kernel probe | /dev & sysfs | firmware | status |
|---|---|---|---|---|
| Audio codec | `sound` compatible `samsung,beyond-madera`; ABox `abox@18c50000` | card 0 `beyond-madera`, RDMA0-11/WDMA0-7/DP PCM | `cs47l93-dsp*.wmfw/.bin`, `cs35l40-dsp*.wmfw/.bin` ABSENT | BLOCKED_FIRMWARE |
| Speaker amps | Cirrus CS35L40×2 (DT under Madera) | no writable codec controls probed (audio-diag) | dsp blobs absent | BLOCKED_FIRMWARE |
| BT radio | `bcm43xx` rfkill0 | no /dev/hci* | BCM43xx HCD absent | BLOCKED_DEPENDENCY (soft=1 hard=0) |
| Wi-Fi | `phy0` + `brcmfmac-wifi` rfkill | wlan0 connected | bcmdhd_sta.bin_b1 present | WORKING (owner baseline) |
| Sensors SSP | `ssp,BCM4773` BCM47752KUB1G | sensors_class accel/gyro/etc, raw `0,0,0` | SSP firmware absent | BLOCKED_FIRMWARE (ssp_down) |
| Accel/gyro | STM LSM6DSO behind SSP | iio:device1/4 timestamp-only | n/a | BLOCKED (SSP down) |
| GNSS | SSP GPS | no /dev/gnss*/gps* | n/a | BLOCKED (SSP down, GPS:false) |
| NFC | `sec-nfc@27` @ hsi2c@108E0000 | /sys/class/nfc/nfc_support empty, no NCI | absent | BLOCKED_FIRMWARE/DRIVER |
| USB | CDC-ACM gadget (Live Console) | /dev/cu.usbmodem101 (host) | n/a | WORKING |
| Battery | max77705 fuelgauge | /sys/class/power_supply/battery capacity=100 | n/a | WORKING |
| Display | DECON/AMOLED via nuxel-wl-fb | /dev/fb0 (never opened by agent) | n/a | WORKING |

## Distinction (per mission)
- userspace package missing  -> install signed RPM (audio server, BlueZ, tools)
- firmware/DSP missing       -> BLOCKED_FIRMWARE (audio, BT HCD, SSP) unless owner
  supplies licensed/provenanced files
- driver not bound           -> BLOCKED_KERNEL (NFC has driver registered but no
  bound device; needs DT/power/GPIO/firmware investigation, not an app)
