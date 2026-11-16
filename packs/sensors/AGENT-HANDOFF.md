# Agent handoff — bring up S10+ SSP/BBD runtime for Nuxel

Read this and the accompanying `REPO-FINDINGS.md` before changing the device.

## Target and known state

- Phone: Samsung Galaxy S10+ SM-G975F, codename `beyond2lte`, Exynos 9820.
- Sensor hub: Broadcom BCM47752KUB1G; downstream DT compatible is `ssp,BCM4773`.
- Accelerometer/gyroscope: STM LSM6DSO behind the SSP hub.
- Kernel transport already enumerates: `/dev/bbd_control`, `/dev/ttyBCM`/SSP paths, Samsung sensor class, IIO stubs.
- Sensor values are not streaming: accelerometer `raw_data=0,0,0`; SSP log reports `ssp_down` / MCU not ready.
- The Nuxel repository reports `/vendor/bin/hw/lhd` and `/vendor/lib64/sensors.sensorhub.so` present on the source handset's read-only vendor partition, but no usable Android/Bionic userspace runtime in Nuxel.

## Step 1 — acquire exact vendor runtime

Ask the operator to run `scripts/extract-s10plus-ssp-runtime.sh` from the host while the exact S10+ is connected over ADB. The script is read-only and does not mount partitions itself. Inspect the extracted archive, generated manifest, checksums and ELF report.

Required exact-target evidence:

1. `vendor/bin/hw/lhd` (or establish the actual alternate path).
2. `vendor/etc/sensor/lhd.conf`.
3. `vendor/lib64/sensors.sensorhub.so` (and 32-bit counterpart if present).
4. Matching `vendor/etc/init/*.rc` startup definition.
5. Bionic linker and exact transitive `DT_NEEDED` dependencies from the same Android vendor/system build.
6. Actual device nodes and driver ABI from the Nuxel kernel.
7. Any explicitly referenced patch file found on the target image. Do not infer a missing patch file from a fixture.

## Step 2 — resolve the real patch-loading path

The `beyond2lte` vendor config reference identifies `LhePatch=/dev/bbd_patch`; it also references `/dev/ttyBCM`, `/dev/bbd_control`, `/dev/bbd_sensor`, `/sys/class/sec/sensorhub/mcu_power`, and `/sys/class/sec/gps/GPS_PWR_EN/value`.

This means the patch upload endpoint is likely a kernel character device. Do not assume `SensorHub.patch` is a standalone file or that `/dev/bbd_patch` is a pathname to one. Inspect the exact target lhd binary, embedded resources/strings, `lhd.conf`, startup rc, kernel BBD/SSP driver implementation, ioctl/write protocol, and any vendor-specific urgent patch lookup. Do not read or alter `/efs/sec_efs` or private `/data/vendor/gps` NV/calibration storage as part of this acquisition.

The small `bcm4773_sensorhub.patch` in the repository's `gnss-ready` test fixture is **2 bytes** and is not firmware. Do not use it.

## Step 3 — build a compatibility strategy, not a blind copy

`lhd` is an Android vendor executable. Determine:

- ELF class, machine, interpreter and ABI version.
- Complete dynamic dependency closure.
- Whether it requires Android properties, Binder/HIDL, Android logging, wakelocks, service manager, or GNSS-specific services.
- Which capabilities are strictly required for SSP patch upload vs optional GNSS operation.
- Whether the daemon can run in a tightly isolated Bionic root/prefix using the extracted matching linker and libraries, or whether a small native implementation of the documented BBD/SSP ABI is safer.
- Whether the Android sensor HAL is needed for sensor data or whether the existing Nuxel kernel sysfs/IIO ABI can remain the data path after LHD brings the MCU up.

Never replace Fedora glibc or install Android libraries into `/usr/lib`. Keep all vendor files in an isolated prefix. Start with read-only diagnostics and a bounded, reversible prototype. Preserve the existing manual rotation modes and the one existing `nuxel-orientationd` owner.

## Step 4 — validate the actual hardware chain

Use the existing service/control paths already present in Nuxel, but do not keep retrying MCU reset/power commands indefinitely. Capture before/after logs and the hub power/enable state.

The order is:

1. lhd/patch runtime starts in a controlled, isolated environment.
2. BBD control handshake succeeds.
3. SSP MCU identifies itself and reaches ready state.
4. Accelerometer enable bit is set without clobbering other sensor bits.
5. `accelerometer_sensor/raw_data` becomes non-zero and changes with real tilt.
6. Gyroscope outputs become non-zero during rotation and return near zero at rest.
7. Determine scales, sign, timestamp, mount matrix and calibration from actual evidence.
8. Feed the existing orientation policy; do not create a competing daemon.
9. Test all four orientations, touch remapping, lock/wake and suspend/resume.

Do not synthesize samples, gravity vectors, gyro rates or a green auto-capability flag.

## Flashing/reflash boundary

This acquisition kit never flashes anything. Do not reflash merely to copy userspace vendor files. The repository's reflash plan says SSP runtime belongs primarily in the system image; boot/kernel changes are needed only if the existing SSP driver/DT must change. NFC/USBNET kernel changes can be batched separately only after each component has passed its gates. Use the user's separate controlled-reflash agreement only for a validated combined image.

## Acceptance

`FULLY_DONE` requires real motion data, not merely `lhd` process startup or an MCU-ready string:

- Non-zero accelerometer samples change in expected directions with physical tilt.
- Non-zero gyro rates appear during physical rotation and return toward zero at rest.
- Scale, mounting and axis mapping are understood and documented.
- Auto rotation transitions to all four poses reliably, with touch aligned.
- Manual/locked modes continue working.
- Suspend/resume and reboot retain operation.
- Logs, checksums, exact vendor build provenance, dependency closure, tests and limitations are recorded.

If the recovered vendor runtime cannot be safely executed or the correct patch payload is not present, report the exact blocker and keep auto-rotation `PARTIAL/BLOCKED_VENDOR_RUNTIME`.
