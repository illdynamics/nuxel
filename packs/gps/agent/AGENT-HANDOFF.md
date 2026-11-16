# Agent handoff — bring up S10+ BCM4773 GNSS for Nuxel

## Objective

Get **receiver-originated GNSS fixes** working on Samsung Galaxy S10+ `SM-G975F` (`beyond2lte`, Exynos 9820) under Nuxel/Fedora ARM64. A network/IP/GeoClue fallback is not success. A detected SPI node, open character device, raw byte stream, or `GPS: true` label without position data is not success.

## Ground truth from the supplied Nuxel repository

1. `REPORT-GPS.md` records:
   - live SPI modalias `spi:BCM4773`, binding at `spi17.0` under `brcm gps spi`;
   - `/dev/ttyBCM`, `/dev/bbd_patch`, `/dev/bbd_control`, `/dev/bbd_sensor`, `/dev/bbd_urgent_patch` exist;
   - `/dev/ttyBCM` is a Broadcom BBD packet transport, **not NMEA**;
   - current rootfs has no `lhd`, `gpsd`, Android linker, Samsung GNSS config, or GNSS HIDL implementation;
   - no verified sensor-hub patch is present; no receiver-reported fix exists.
2. `34-vendor-binary-analysis.txt` records `GPS_PWR_EN=0`, `GPS: false`, and an `lhd.conf` source-of-record of:

   ```ini
   PortName=tcp:127.0.0.1:300; LheName=bbd; LhePatch=/dev/bbd_patch; LheBbdPacket=/dev/ttyBCM
   ```

   This is useful evidence of the BBD interfaces, but it is a fetched config excerpt, not a proof of the correct firmware blob or a complete runtime.
3. `31-gnss-bounded-powered-probe.txt` did not activate the GPS rail or open `/dev/ttyBCM`; it returned `UNSUPPORTED_PROTOCOL` because the patch was absent. Do not describe this as a successful powered receiver test.
4. The repo's GNSS inventory is diagnostic-only. It has an empty `VERIFIED_PATCH_SHA256` allowlist; a basename match is not identity verification. Its current `READY_FOR_SKY`/ready classification can overstate readiness if it relies only on a matching filename plus device node. Tighten this before using it as a release gate.
5. `REFLASH-PLAN.md` correctly groups GPS payloads into the planned system image; boot/kernel changes are conditional on loader/DT changes.

## What public S10+ vendor metadata establishes

The public Evolution-X `vendor_samsung_beyond2lte` build recipe for the exact `beyond2lte` target lists:

- package names `lhd`, `gpsd`, `gps.default`, `android.hardware.gnss@2.0-impl`, `vendor.samsung.hardware.gnss@2.0-impl`, `vendor.samsung.hardware.gnss@2.0-service`, and `libwrappergps`;
- files `vendor/etc/gnss/gps.xml`, `vendor/etc/init/init.gps.rc`, `vendor/etc/init/vendor.samsung.hardware.gnss@2.0-service.rc`, and `vendor/etc/sensor/lhd.conf`.

That proves the stack is present in a known S10+ Android vendor build recipe. It does **not** prove those files are in this Nuxel repo, nor does it prove their ABI is usable in Fedora, nor does it identify the correct BBD patch binary.

## Do this in order

### Phase A — acquire exact stock payloads

1. Use only a stock image / vendor partition for `SM-G975F` and record exact Samsung build string, Android release, CSC, and vendor fingerprint.
2. Run the accompanying extractor against a read-only extracted filesystem.
3. Inspect `out/extraction-report.txt`, `out/SHA256SUMS`, and `out/elf-report.txt`.
4. Do not accept files from `SM-G975N` or another Exynos device without a hardware/ABI diff. Do not accept Broadcom patches from Pixel/BCM47765 or other Broadcom chip generations.
5. The extractor stores possible `SensorHub*.patch`, `bcm4773*.patch`, `bcm47752*.patch`, and sensorhub `.bin` files under `payload/unverified-firmware-candidates/`. These are **candidates only**. Establish provenance and compatibility using the stock build's init/config references, the device's firmware revision, file metadata/hash, and (ideally) a controlled stock boot capture. A filename match is insufficient.

### Phase B — determine Android runtime feasibility

1. Use `readelf -h -l -d` (or the verifier output) on `lhd`, `gpsd`, the Samsung GNSS service, and GNSS libraries.
2. Record ELF class, machine, interpreter (likely Android linker), `DT_NEEDED`, SONAME, and any vendor-specific dependencies. Inspect extracted VINTF XML to determine declared HAL instances and service version.
3. Compare against the target Nuxel rootfs. Expect Android Bionic + Android service/HIDL/Binder dependencies. Do not simply copy Android executables into `/usr/bin` or symlink `/system/bin/linker64` to a glibc loader.
4. If testing the vendor stack, create a throwaway, isolated Android userspace/container/chroot with the exact matching vendor/system dependencies and binder/HIDL support. Never make it the default Nuxel GPS design until its security and lifecycle are understood.
5. In parallel, define a native Nuxel service for BBD patch loading, BBD handshake/RPC, location solution decoding, and a GeoClue provider. Use a vendor stack only as a reference where legally and technically permitted.

### Phase C — firmware loader audit

1. Read the exact target kernel source for the `brcm gps spi` / Broadcom BBD code and record the ioctl/write/read ABI for `/dev/bbd_patch`, `/dev/bbd_control`, and `/dev/ttyBCM`.
2. Trace the exact stock init rules and `lhd.conf` to establish the required patch path and loader semantics. The repo evidence says `LhePatch=/dev/bbd_patch`, i.e. the config's `LhePatch` is the loader device; it does not itself prove that a file named `/system/bin/bcm_sensorhub_a1.patch` is correct.
3. Compare candidate patch metadata/hash/revision against the exact stock image. Keep a `verified-firmware.json` containing device model, build fingerprint, chip/board IDs, file path, byte size, SHA-256, provenance, and verification method. Until then, mark `firmware_identity=UNVERIFIED`.
4. Determine how GPS power is sequenced. Current evidence showed `GPS_PWR_EN=0`. Do not hand-toggle the GPIO/rail; implement the vendor-matched power sequence in a guarded service only after reviewing kernel/regulator dependencies, reset/IRQ, and suspend/resume.
5. Do not treat a working SPI binding as proof that the sensor hub is up.

### Phase D — Nuxel service and API

1. Implement a supervised service with explicit states: `ABSENT`, `TRANSPORT_READY`, `FIRMWARE_UNVERIFIED`, `PATCH_LOADED`, `BBD_HANDSHAKE_OK`, `SOLUTION_STREAMING`, `FIX_VALID`, `FAULT`.
2. Do not label `READY`, `READY_FOR_SKY`, `GPS enabled`, or `fix_supported=true` based solely on file existence.
3. Export actual fix fields: latitude, longitude, altitude (if supported), UTC time, horizontal accuracy, fix type, satellite count/used-in-fix if available, and age. Preserve source attribution `GNSS` vs `NETWORK`.
4. Do not parse NMEA from `/dev/ttyBCM` unless a separate, documented NMEA endpoint is proven. It is BBD packet transport in the current evidence.
5. Make cold start, warm start, assistance data, privacy denial, suspend/resume, no-fix timeout, and service restart explicit.

## Acceptance gate before any reflash

- Exact stock source/build identified and documented.
- Patch hash/provenance and hardware compatibility verified; no name-only match.
- Kernel loader ABI and power sequencing audited against exact target kernel.
- Daemon/service starts under Nuxel with bounded resource use and clean shutdown.
- BBD handshake demonstrably succeeds; receiver produces valid position/measurement messages.
- GeoClue receives an actual receiver-originated fix; network fallback remains separately labelled.
- Outdoor test obtains a stable fix, with timestamps/accuracy and satellites/quality metrics captured; test cold-start and warm-start.
- Suspend/resume, reboot, no antenna/no sky, permission denied, and service crash/restart do not wedge SSP or leave GPS power enabled.
- No broad `chmod 666` on `/dev/ttyBCM` or BBD nodes; use a dedicated group/udev rule and least privilege.
- Rollback system image available; do not flash solely because files were extracted.

## Expected next deliverable from the agent

Return a technical report, not a claim of completion:

1. source image fingerprint/build and device model evidence;
2. exact extracted file list + SHA256;
3. ELF/dependency report for each binary and library;
4. exact sensor-hub patch candidate inventory with hashes and compatibility confidence;
5. loader ioctl/file protocol findings from the kernel tree;
6. architecture decision: native implementation vs isolated Android runtime;
7. code changes, test evidence, remaining blockers, and reflash partition impact.

**No flash operations are authorized by this handoff.**
