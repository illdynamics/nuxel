# Nuxel SSP Android runtime: OFFLINE audit

**Status:** `INCOMPLETE`

- Available source files: **4**
- Missing root executables/HALs: **0**
- Direct/recursive unresolved DT_NEEDED entries: **28**
- Interpreter `/system/bin/linker64` missing: **True**
- Invalid/wrong architecture: **0**
- Local staging performed: **False**

## Unresolved ELF dependencies

- `vendor/bin/hw/lhd` needs `liblog.so`
- `vendor/bin/hw/lhd` needs `libutils.so`
- `vendor/bin/hw/lhd` needs `libz.so`
- `vendor/bin/hw/lhd` needs `libhardware_legacy.so`
- `vendor/bin/hw/lhd` needs `libc++.so`
- `vendor/bin/hw/lhd` needs `libc.so`
- `vendor/bin/hw/lhd` needs `libm.so`
- `vendor/bin/hw/lhd` needs `libdl.so`
- `vendor/lib64/sensors.sensorhub.so` needs `android.frameworks.schedulerservice@1.0.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libcutils.so`
- `vendor/lib64/sensors.sensorhub.so` needs `liblog.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libbase.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libhidlbase.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libhidltransport.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libutils.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libhardware.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libhardware_legacy.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libc++.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libc.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libm.so`
- `vendor/lib64/sensors.sensorhub.so` needs `libdl.so`
- `vendor/lib64/hw/sensors.exynos9820.so` needs `liblog.so`
- `vendor/lib64/hw/sensors.exynos9820.so` needs `libcutils.so`
- `vendor/lib64/hw/sensors.exynos9820.so` needs `libhardware.so`
- `vendor/lib64/hw/sensors.exynos9820.so` needs `libc++.so`
- `vendor/lib64/hw/sensors.exynos9820.so` needs `libc.so`
- `vendor/lib64/hw/sensors.exynos9820.so` needs `libm.so`
- `vendor/lib64/hw/sensors.exynos9820.so` needs `libdl.so`

## Missing root files

- None

## Relevant lhd config endpoint names

- `LhePatch`: present
- `LheBbdPacket`: present
- `LheBbdControl`: present
- `LheBbdSensor`: present
- `GpioNPowerPath`: present
- `GpioNStdbyPath`: present

## Boundaries

- This tool NEVER connects to the phone, writes partitions, runs lhd, toggles GPIO, or uploads firmware.
- Do not run the staged Android binaries on Fedora directly; obtain exact matching runtime and test in a separately reviewed isolated environment.
- These findings cannot establish that the sensor hub's ACK/boot handshake succeeds.
- Do not run GNSS power/standby controls as a workaround; past repo reports describe unexpected device resets.
- Proven success requires physically changing accelerometer and gyroscope samples and reliable resume/reboot behaviour.
