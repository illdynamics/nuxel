# Evidence audit — uploaded `nuxel-main (2).zip` vs new agent report

## Archive inspection
- Archive index showed **21,469 entries** and about **991 MiB uncompressed**.
- Target is SM-G975F / `beyond2lte` / Exynos 9820; archive reports Broadcom BCM47752KUB1G sensor hub and STM LSM6DSO motion sensor.
- The uploaded archive includes `packs/sensors/acquired/` with:
  - `vendor-bin-hw-lhd` (318,024 B), SHA256 `6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`.
  - `vendor-etc-sensor-lhd.conf` (1,264 B), SHA256 `1660da1b4f024e4ed6fd4b99e62145747d6eb27a7fe84ad58af240b7edd46bc4`.
  - `vendor-lib64-sensors.sensorhub.so` (212,192 B), SHA256 `de0110a7065f39723fc7436f4d5451d92572d87fe9a3ae8550cc4e88f3cd5718`.
  - `vendor-lib64-hw-sensors.exynos9820.so` (15,336 B), SHA256 `44b26ae85510b2c4147d0ff8a518211e8a475fd29c002922f53b5a726e4d2ef0`.
- Both `packs/sensors/scripts/` and `packs/ssp/scripts/` contain `extract-s10plus-ssp-runtime.sh`, `collect-elf-deps.py`, and `verify-s10plus-ssp-runtime.py`. **Those ADB tools already exist; avoid duplicating them.**
- `tools/s10plus/ssp-native/nuxel_bbd_download.c`, `nuxel_bbd_host.c` and their binaries exist in the ZIP. `tools/s10plus/ssp-native/Makefile` and `SENSORS-FIRST-LIGHT.md` were **not found** in this snapshot.
- The uploaded repo includes `reports/SSP-CONTINUATION-20261113-2130.md` and older first-light experiments; it does not itself prove that the user's newer claimed commit `3d34aef8` or branch `codex/ssp-first-light-20261116` has been incorporated.
- The older report describes live kernel `#78` on Nov 13; the user-supplied newer agent message describes `#3` on Nov 14. Neither establishes today's live kernel. Check over SSH/ADB.
- The archive's `lhd.conf` has `LhePatch=/dev/bbd_patch`, `LheBbdPacket=/dev/ttyBCM`, `LheBbdControl=/dev/bbd_control`, `LheBbdSensor=/dev/bbd_sensor`, `GpioNPowerPath=/sys/class/sec/sensorhub/mcu_power`, and `GpioNStdbyPath=/sys/class/sec/gps/GPS_PWR_EN/value`. Its `LheMaxMcuResetTries` is duplicated; avoid assuming which setting is honored without checking parser semantics.

## Direct ELF evidence (readelf + original offline parser)

`lhd` is **ELF64 AArch64**, interpreter `/system/bin/linker64`; direct `DT_NEEDED`:
```
liblog.so
libutils.so
libz.so
libhardware_legacy.so
libc++.so
libc.so
libm.so
libdl.so
```
The vendor HALs add e.g. `libcutils.so`, `libbase.so`, `libhidlbase.so`, `libhidltransport.so`, `libhardware.so`, `android.frameworks.schedulerservice@1.0.so`.

No matching `system/bin/linker64` and no source of these runtime libraries were included among the four acquired vendor components. The baseline run therefore reports **14 distinct unresolved direct library basenames (28 dependency occurrences)**, with no complete transitive closure attempted because prerequisites are absent.

Having the vendor daemon file is **not** the same as being able to run it under Fedora. Even resolving the direct+recursive ELF closure is insufficient if Android's binder, property service, APEX/VNDK linker namespace, and system calls need emulation or isolation.

## Reconciliation with newest report (user-provided, not independently run)

The user's latest agent message claims:
- branch `codex/ssp-first-light-20261116`, commit `3d34aef8` and later first-light files not in this ZIP;
- embedded patch SHA-256 `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72`;
- ASIC `0x004775b0`, 438,895 bytes, patch destination `0x00800161`;
- header `Crc=0xC1` is NOT IEEE CRC-32 and decoded blob's IEEE CRC-32 is `0x93d35bb4`;
- simulated transport tests and AArch64 build passed, but real accel/gyro are `0,0,0`, `enable=0`, `ssp_down=true`.

Those are **agent-reported observations**; this chat did not access a live phone to confirm them. Use their actual commit/report to reproduce before an on-device change.

## Practical conclusion

The next missing reusable component is **the exact vendor-matched Android system runtime**, not a newly invented sensor-hub firmware. A small helper can stage it and produce dependency/evidence reports, which is what the included Python code does. The actual hardware fix needs either (1) proven safe isolated execution of the compatible Samsung `lhd` and successful MCU boot or (2) completion of the native downloader's ACK state machine from the exact vendor protocol, followed by real sensor/auto-rotation verification. Neither path is yet proven.

## Verification

Seven tests for this new Python tool pass offline. They are not evidence of hardware working. No boot flash, GPIO operation, firmware download, vendor binary execution, or connection to the actual phone was performed.
