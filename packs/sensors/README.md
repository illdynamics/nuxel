# S10+ SSP / BBD runtime acquisition pack

**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**Sensor hub:** Broadcom BCM47752KUB1G (`ssp,BCM4773`)  
**Physical accel/gyro:** STM LSM6DSO (reported by the Nuxel hardware audit)

## What this pack is

This is a **read-only extractor and verifier** for the exact Samsung vendor runtime from the owner's own S10+ vendor/system partitions. It deliberately does **not** contain Samsung proprietary runtime binaries or a guessed sensor-hub patch. The uploaded Nuxel repository does not contain the actual `lhd`, `sensors.sensorhub.so`, or sensor-hub firmware payload, and its `bcm4773_sensorhub.patch` test fixture is only two bytes.

The repository's live-device investigation reports that `/vendor/bin/hw/lhd` and `/vendor/lib64/sensors.sensorhub.so` exist on the handset's read-only vendor partition. The blocker is that Nuxel lacks the Android/Bionic runtime and compatible execution environment required by the vendor components. Recover these exact target-device files rather than using a generic BCM4775x binary.

## Run it

1. Boot the **SM-G975F / beyond2lte** into TWRP and connect USB. In TWRP, ensure the **Vendor** partition is mounted read-only. Mount **System** read-only too if available. This pack never mounts partitions itself.
2. On the Mac/Linux host, install Android platform-tools (`adb`) and Python 3. The extractor is written for Bash 3.2+ (including the stock macOS Bash) and avoids GNU-only `sort -z`/`sha256sum` requirements.
3. Extract this archive and run:

   ```sh
   cd S10Plus-SSP-Runtime-Acquisition-Pack
   chmod +x scripts/extract-s10plus-ssp-runtime.sh
   ./scripts/extract-s10plus-ssp-runtime.sh --out ./S10Plus-SSP-Runtime
   ```

   When more than one ADB device is connected, pass `--serial SERIAL`.
4. The script creates `S10Plus-SSP-Runtime-extracted.zip` and an uncompressed evidence directory. Give the **extracted ZIP** to the Nuxel agent alongside `AGENT-HANDOFF.md`.

If TWRP does not expose `/vendor` or `/system`, do not let the script guess or mount partitions. Mount the correct partition read-only in TWRP's Mount UI and rerun. If the exact lhd/HAL files are absent, stop and obtain them from the matching official stock firmware image for this phone/region/build; do not substitute files from another model.

## What is collected

The extractor attempts to collect, where present:

- `/vendor/bin/hw/lhd`
- `/vendor/etc/sensor/lhd.conf`
- `/vendor/etc/sensors/hals.conf`
- 32/64-bit `sensors.sensorhub.so`
- 32/64-bit Exynos sensor HAL
- relevant vendor init rc files and VINTF sensor manifests
- a separately stored `SensorHub.patch` only if the target vendor partition actually contains one
- `/system/bin/linker64` / `linker` and the recursive ELF `DT_NEEDED` library closure for the collected vendor executables/libraries

It does **not** read `/efs`, `/data`, calibration/NV storage, modem data, EFS identifiers, user data, or private GPS storage. It does not execute the vendor daemon, change permissions, write sysfs, flash partitions, or reboot the phone.

## Important technical interpretation

The S10+ vendor configuration published for `beyond2lte` uses `LhePatch=/dev/bbd_patch`, `LheBbdPacket=/dev/ttyBCM`, `LheBbdControl=/dev/bbd_control`, and `LheBbdSensor=/dev/bbd_sensor`. `/dev/bbd_patch` is a kernel character-device endpoint, not a normal filesystem firmware file path. The agent must inspect the **exact on-device lhd binary/config/kernel ABI** to determine where patch bytes originate and how the daemon uploads them.

A Google Pixel `SensorHub.patch` for a BCM47765 platform is not a safe replacement for the S10+'s BCM47752. Do not copy it into Nuxel.

## Safety

- Acquisition only. No device writes, no flash, no reboot.
- Do not flash the extracted binaries.
- Do not run `lhd` on the Fedora host directly.
- Do not copy Bionic libraries into `/usr/lib` or overwrite Fedora's glibc.
- Keep the recovered Android runtime isolated until its ABI, dependencies, device-node access, SELinux assumptions, and kernel protocol are understood.
- Do not claim auto-rotation works until real, changing accelerometer and gyro readings are recorded during physical motion.
