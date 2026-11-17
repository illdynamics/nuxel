# SENSORS-FIRST-LIGHT — verified successor, 2026-11-16 CET

## Result

**FAIL — no real accelerometer or gyroscope samples.** The first failing stage
is the BCM47752 BBD application/runtime handshake. At 18:15 CET the MCU rail
was on, SSP was down, and both physical LSM6DSO exports were 0,0,0. No GPIO,
reset, BBD control write, firmware download, boot image, or persistent handset
state was changed in this run.

## Evidence

| Finding | Classification | Evidence |
|---|---|---|
| Running kernel | PROVED_LIVE | 4.14.253-gf7194c1d15ed-dirty #3, built 2026-11-14 |
| DT / BBD device | PROVED_LIVE | Samsung BEYOND2LTE; spi17.0 spi:BCM4773 |
| SSP config | PROVED_LIVE | SSP, BBD, LSM6DSO, and BEYOND all enabled |
| Sensor state | PROVED_LIVE | accel=0,0,0; gyro=0,0,0; enable=0; ssp_down=true |
| Embedded patch | PROVED_LIVE | 897113 B; SHA-256 0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72 |
| Patch metadata | PROVED_LIVE | ASIC 0x004775b0, blob 438895 B, address 0x00800161 |
| Historic #48 / #78 | HISTORICAL_LIVE | November reports; neither is current |

The patch header Crc field is 0x000000c1; its algorithm is UNKNOWN. The
decoded-content IEEE CRC-32 is 0x93d35bb4. Earlier reporting of 0x93D3F2B4 is
contradicted by this read-only measurement and is superseded.

## Failure and decision

The chain is rail -> SSI/TL/BBD -> version/autobaud -> patch -> service ->
interrupt -> SSP enable -> samples. It stops before a validated version
response. There is only ADC IIO; zero vectors are a hard failure.

| Candidate | Decision |
|---|---|
| Native glibc downloader | Read-only verifier/query scaffold only; upload disabled |
| Exact lhd in constrained Bionic prefix | Best path; BLOCKED on matching runtime |
| libhybris / Halium | BLOCKED and not least-invasive |
| Kernel/DT/GPIO change | Rejected; no evidence and GPIO 145 is unsafe |
| New protocol implementation | Deferred pending source-verified ACK rules |

Pinned source f7194c1d15eded1c2a1a4dc63825b26103435cc0 establishes the
kernel BBD parser as a receive bridge and bbd_patch as read-only. The vendor
partition matches the acquired lhd/config/HAL pack but has no linker64,
libutils, libhardware_legacy, liblog, libc++, libc, libm, or libdl. Required
owner artifact: matching Android system/runtime image or an authorized complete
linker/dependency extraction; do not use a generic Android runtime.

Public corroboration: [vendor makefile](https://raw.githubusercontent.com/Evolution-X-Devices/vendor_samsung_beyond2lte/bka/beyond2lte-vendor.mk),
[lhd.conf](https://raw.githubusercontent.com/Evolution-X-Devices/vendor_samsung_beyond2lte/bka/proprietary/vendor/etc/sensor/lhd.conf),
and [libhybris](https://github.com/libhybris/libhybris).

## Delivered and tested

The downloader now bounds patch reads, detects the driver EOF rewind, validates
header fields and decoded blob length, exposes read-only verify-patch, requires
explicit live query, and refuses the unvalidated upload path. SIMULATED
fixtures pass for fragmented escaped TL, sequence wrap, CRC rejection, valid
metadata, and invalid blob length. An AArch64 verifier ran once from run and
was deleted; it was not installed.

| Test | Result |
|---|---|
| Version response / patch start ACK | BLOCKED |
| Changing accel and gyro samples | FAIL |
| Six-face / gyro rotation | NOT TESTED |
| Suspend/resume / thermals | NOT TESTED |
| Wi-Fi / touch / display integrity | PASS; no persistent deployment |

No flash occurred, so current BOOT is untouched and no new rollback image
exists. Prompt 4 has no calibration contract: auto-rotate must remain blocked
and must not consume zero vectors.
