# NUXEL A69 — ROTATION HARDWARE BOUNDARY

## Result: BLOCKED_HARDWARE (sensor-hub firmware + userspace daemon absent)

## Proven device facts
- Sensor hub MCU: **Broadcom BCM47752KUB1G** (DT compatible `ssp,BCM4773`).
- Physical accel/gyro behind the SSP: **STM LSM6DSO** (`/sys/class/sensors/
  accelerometer_sensor/name`, vendor `STM`).
- Samsung `sensors` class exposes `accelerometer_sensor`, `gyro_sensor`, etc.
- `raw_data` of `accelerometer_sensor` reads `0,0,0` (no streaming).
- dmesg: `[SSPBBD]: ssp_down == true` and `ssp_send_cmd - command 0xd1/d2 failed -1`
  (sensor hub never brought up).
- IIO stubs (`iio:device1 accelerometer_sensor`, `iio:device4 gyro_sensor`) expose
  only `in_timestamp_*` scan elements — no raw x/y/z channels, no `in_accel_scale`.
- No BCM4775x sensor-hub firmware anywhere under `/lib/firmware` (only WiFi
  `bcmdhd` blobs present). No Samsung `libsensorhub` userspace daemon.
- `nuxel-orientationd status`: `auto_capable: false`, only `manual` source
  available. Its 7-policy state machine is intact and selftests pass (40 tests).

## Failure stage
1. Physical LSM6DSO present and enumerated — OK.
2. SSP/BCM47752 transport — **DOWN** (no firmware boot, no streaming).
3. Raw gravity vector — unavailable (`0,0,0`).
4. Normalized orientation event — cannot be produced from real data.
5. Compositor/Phoc transform + touch remap — present in code, never exercised by a
   real auto event on this device.

## What would unblock it
1. Owner-supplied BCM4775x SSP sensor-hub firmware (provenance + license verified)
   installed under `/lib/firmware` with owner approval, AND
2. a supported sensor-hub userspace (Samsung `libsensorhub`-compatible) or a
   lawful re-implementation of the SSP protocol on the existing 4.14 kernel —
   **no kernel v6 migration** (out of scope), no random binary HAL.

## What is NOT broken / what still works
- All seven orientation policies (Forced Portrait, Forced Portrait Inverted,
  Forced Landscape Left, Forced Landscape Right, Auto All, Auto Portrait,
  Auto Landscape) are implemented, selectable, persisted, and validated offline.
- Forced (manual) modes do not require a sensor.
- Honest status reporting: auto modes report `sensor_unavailable`, never fake a flip.
