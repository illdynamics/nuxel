# Repository findings — rotation / SSP / sensor hub

Source archive: `nuxel-main (5).zip` (20,497 entries; 738,484,173 uncompressed bytes; archive file ~365 MB).

## Findings from the repo

### Hardware and first failure

`REPORT-ROTATION.md` identifies the device as SM-G975F `beyond2lte`, Exynos 9820. It reports a Broadcom BCM47752-family SSP/BBD sensor hub (`ssp,BCM4773` binding), with an STM LSM6DSO accelerometer/gyro behind it. The report places the first failure at the sensor-hub runtime: `/sys/class/sensors/accelerometer_sensor/raw_data` stays `0,0,0`, `ssp_sensor/enable` reads `0`, and the kernel logs show SSP/BBD down or MCU-not-ready messages.

`docs/a69/ROTATION-HARDWARE-BOUNDARY.md` records the more specific hub part as Broadcom BCM47752KUB1G and the physical sensor as STM LSM6DSO. It also reports that `/vendor/bin/hw/lhd` and `/vendor/lib64/sensors.sensorhub.so` exist on the read-only vendor partition, but are not executable from the Fedora Nuxel rootfs because the Android/Bionic runtime is missing.

### The runtime Nuxel already has

- `services/nuxel-orientation/nuxel_orientation/sensors.py` already has a `SensorHubControl` path for `/dev/bbd_control`, `/sys/class/sensors/ssp_sensor/enable`, `/sys/class/sensors/accelerometer_sensor/raw_data`, and `/sys/class/sec/sensorhub/mcu_power`.
- It deliberately waits for real samples and refuses to synthesize data.
- `nuxel-orientationd` already has the seven orientation modes and policy; manual/locked rotation is reported as working.
- Diagnostics enumerate IIO and sensor class stubs, but those do not prove readable samples.
- `docs/beta-finalization/manual-proof/14-sensors.md` defines the required physical tilt/rotation proof.

### Firmware tree is not populated with SSP payloads

- `firmware/s10plus/blobs/README.md` says proprietary blobs are not committed; the directory contains only `.gitkeep` and the README in this source archive.
- `firmware/s10plus/manifest.yml` contains firmware entries for NFC, MFC, audio, camera, Wi-Fi and other vendor components, but no verified BCM47752 SSP patch entry.
- `firmware/s10plus/fetch-vendor-blobs.sh` fetches vendor firmware directories from a pinned public proprietary-vendor mirror, but its listed firmware-tree prefixes do not establish a matching sensor-hub patch payload. It does not fetch `lhd` or the sensor HAL.
- `tools/s10plus/a33/tests/hw-subsystems/fixtures/gnss-ready/lib/firmware/gnss/bcm4773_sensorhub.patch` is exactly **2 bytes**, a fixture placeholder. It is not firmware and must never be installed.

### Vendor runtime identifiers

The public `beyond2lte-vendor.mk` file lists `vendor/etc/sensor/lhd.conf`, packages `sensors.sensorhub` and `lhd`, and copies the device-specific sensor HAL and vendor firmware. The corresponding published `lhd.conf` uses:

- `LheName=bbd`
- `LhePatch=/dev/bbd_patch`
- `LheBbdPacket=/dev/ttyBCM`
- `LheBbdControl=/dev/bbd_control`
- `LheBbdSensor=/dev/bbd_sensor`
- `GpioNPowerPath=/sys/class/sec/sensorhub/mcu_power`
- `GpioNStdbyPath=/sys/class/sec/gps/GPS_PWR_EN/value`

This points to a **device-node patch transport**. The payload source/format still has to be determined from the exact target vendor daemon/build and driver ABI. Do not substitute a Google Pixel BCM47765 `SensorHub.patch`.

## Reflash-plan implication

`REFLASH-PLAN.md` labels rotation as `PARTIAL / YES`: userspace/runtime belongs in the system image; a boot/kernel change is conditional on SSP driver/device-tree changes. That is consistent with the failure boundary above. Do not promise that a kernel-only reflash can fix rotation while the vendor runtime is missing.

## Confidence

- High: exact target codename/SoC, SSP/BBD binding, presence of hub device interfaces, zero accelerometer samples, existing orientation policy and manual modes.
- High: repo contains no actual SSP runtime binary or verified patch; the named fixture is only 2 bytes.
- Medium/high: published matching vendor metadata includes `lhd`, `sensors.sensorhub`, and `lhd.conf`; exact binary version on the physical handset still needs hashing and provenance.
- Unknown: exact on-device lhd build, embedded/externally sourced patch bytes, all transitive Android dependencies, required Android services/properties, SSP firmware version, and complete sensor scale/mount calibration.
