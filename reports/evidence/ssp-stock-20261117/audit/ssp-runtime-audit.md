# Nuxel SSP Android runtime: OFFLINE audit

**Status:** `STATIC_ELF_DEPENDENCIES_FOUND_NOT_RUNTIME_VERIFIED`

- Available source files: **28**
- Missing root executables/HALs: **0**
- Direct/recursive unresolved DT_NEEDED entries: **0**
- Interpreter `/system/bin/linker64` missing: **False**
- Invalid/wrong architecture: **0**
- Local staging performed: **True**

## Unresolved ELF dependencies

- None under this static scan (Android services / linker namespaces remain unverified)

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
