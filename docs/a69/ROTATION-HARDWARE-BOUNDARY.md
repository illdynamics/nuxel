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
- All seven orientation policies are implemented, selectable, persisted, and
  validated offline with the owner-facing labels `Auto (FULL)`, `Auto (PT)`,
  `Auto (LS)`, `Locked (PT)`, `Locked (LS)`, `Locked (RPT)`, `Locked (RLS)`.
- Forced (manual) modes do not require a sensor.
- Honest status reporting: auto modes report `sensor_unavailable`, never fake a flip.


## PWNAGE-54000 update (2026-11-01)

Re-probed the live device. The hardware boundary is unchanged: IIO has no
readable accelerometer scale, `raw_data` is `0,0,0`, iio-sensor-proxy is absent,
and dmesg still reports `ssp_down` / `ssp_send_cmd ... failed -1`. Auto modes
therefore remain honestly degraded. The daemon now also probes the Samsung
sensor-hub sysfs node (`/sys/class/sensors/accelerometer_sensor/raw_data`) as a
real production source: a non-zero vector is normalized to 1 g and can drive
Auto; a zero vector is reported as "MCU not streaming", never as a manual
sensor. `nuxel-orientationd sensor --json` exposes the MCU power, accelerometer
enable bit and raw sample. Fixed modes do not need the sensor and are
now verified live: `HEADLESS-1` accepts `normal/2`, `270/1`, `180/2`, `90/1` for
0/90/180/270 respectively. The presenter records `presenter_rotation=0` and
`double_rotation=0`.

Touch has one owner, and it is not wlroots: Phoc 0.54 passes raw `wlr_touch`
coordinates to `wlr_cursor_absolute_to_layout_coords()` without applying the
output transform. `libnuxel-libinput-path.so` is the single input owner and
applies the matching libinput calibration matrix from
`/run/nuxel-orientation/input.json`. Live read-back is recorded in
`/run/nuxel-touch-calibration.state`; no second input or framebuffer transform is
permitted.

## PWNAGE-55000 Auto follow-up (2026-11-01, live re-probe)

The owner reported that all four Locked modes work while Auto does not move the
screen. The Locked result was reproduced; the Auto failure was traced to two
separate facts, one software and one hardware.

### Software defect: the hub was never started

`nuxel-orientationd` only *read* `/sys/class/sensors/accelerometer_sensor/raw_data`.
It never performed either of the kernel operations required before that node can
stream:

1. `ESW:READY` on `/dev/bbd_control` (wake the BBD/SSP bridge), and
2. set bit 0 (accelerometer) in `/sys/class/sensors/ssp_sensor/enable`
   while preserving the other sensor bits.

`sensors.SensorHubControl` now performs both operations, verifies with a real
non-zero `raw_data` sample, and never synthesizes a reading. It is invoked when
an Auto mode is selected, at daemon startup in an Auto mode, and during the
Auto supervision tick. A 30 s retry throttle prevents log/control spam. The
Bridge `sensor --start` diagnostic uses the same path.

### Hardware blocker that remains

On the live SM-G975F the two control writes are accepted, but the MCU still
does not answer:

```
[SSPBBD] Sensors of MCU are not ready!
[SSPBBD] bbd_do_transfer(): completion is timeout!
[SSP] MCU device ID = 85, reading ID = -1
[SSP]: initialize_mcu - MCU is not working : 0xffffffff
[SSP] lhd is NULL or resetting
```

`/vendor/bin/hw/lhd` and `/vendor/lib64/sensors.sensorhub.so` exist on the
read-only vendor partition, but the Android runtime they need
(`/system/bin/linker64` and Bionic libs) is not installed in the Nuxel rootfs.
Consequently no userspace can load the embedded BBD/LHD patch into the
BCM47752 MCU, the accelerometer bit never produces data, and `raw_data` remains
`0,0,0` even after an MCU power cycle and `ESW:READY`.

This is not a policy failure: the same seven-mode policy and the same
hysteresis/auto transaction path pass deterministic tests with a real-shaped
gravity stream. Auto will become operational on this image only when a working
LHD-compatible runtime (or a lawful native BBD/LHD implementation) is present;
Locked modes remain fully functional without it.

### Verification commands

```sh
sudo /usr/libexec/nuxel/nuxel-orientationd sensor --start --json
sudo /usr/libexec/nuxel/nuxel-orientationd status --json
sudo dmesg | grep -E 'SSP|BBD|MCU' | tail -30
```

Expected while the blocker remains: `sensor.available=false`,
`auto_state=blocked_sensor_unavailable`, and
`sensor.hub.auto_blocked_reason` naming the missing vendor LHD runtime. It must
not show a green Auto or a fabricated angle.
