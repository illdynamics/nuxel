# NUXEL A72 / 21000 — 08-SSP-ROTATION-GNSS-NFC

## Rotation / sensors (A69-04)
- Sensor hub: Broadcom BCM47752KUB1G (`ssp,BCM4773`), physical accel/gyro STM LSM6DSO behind it.
- Fresh proof: dmesg `[SSPBBD]: ssp_down == true`, `ssp_send_cmd - command 0xd1 failed -1`;
  `/sys/class/sensors/accelerometer_sensor/raw_data` = `0,0,0`; IIO exposes only timestamps.
- `nuxelctl orientation status`: sensor available=false, auto_capable=false, 7 policies intact.
- Unblock: owner SSP firmware + a lawful sensor-hub protocol daemon on the existing 4.14 kernel. NOT a kernel swap.

## GNSS (A69-05)
- No `/dev/gnss*`/`/dev/gps*`; GNSS rides the down SSP (`[SSP] GPS: false`).
- Network/IP geolocation (geoclue2) is a separately-labelled fallback, never GPS.

## NFC (A69-06)
- DT `sec-nfc@27` @ `hsi2c@108E0000` (compatible `hrm_max sec-nfc`).
- Driver registered but no bound device; `/sys/class/nfc/nfc_support` empty; no NCI node.
- Unblock requires controller firmware + power/GPIO/I2C bring-up investigation, not an app.
