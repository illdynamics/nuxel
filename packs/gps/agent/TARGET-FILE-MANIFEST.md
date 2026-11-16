# S10+ GNSS runtime file manifest

The paths below are target-relative Android vendor/system paths. The extractor copies only files it finds; absence is reported. This is an acquisition manifest, **not** an assertion that every item is mandatory or that any extracted item is compatible with Nuxel.

| Path | Role | Confidence for beyond2lte | Notes |
|---|---|---:|---|
| `vendor/bin/hw/lhd` | Broadcom LHD/BBD bridge | High | Named in S10+ vendor package recipe; Android executable |
| `vendor/bin/hw/gpsd` | Samsung GPS daemon | High | Named in S10+ vendor package recipe; inspect exact startup args |
| `vendor/bin/hw/vendor.samsung.hardware.gnss@2.0-service` | Samsung GNSS HIDL service | High | Named in S10+ package recipe |
| `vendor/etc/gnss/gps.xml` | GNSS policy/config | High | Named in S10+ vendor recipe |
| `vendor/etc/gnss/gps.cer` | GNSS certificate/assistance configuration | Medium | Seen in S10-family proprietary-file manifest; confirm exact beyond2lte image |
| `vendor/etc/init/init.gps.rc` | GPS daemon init rules | High | Named in S10+ vendor recipe |
| `vendor/etc/init/vendor.samsung.hardware.gnss@2.0-service.rc` | HAL service init rules | High | Named in S10+ vendor recipe |
| `vendor/etc/sensor/lhd.conf` | LHD transport/patch config | High | Named in S10+ vendor recipe; fetched excerpt says `LhePatch=/dev/bbd_patch` and `LheBbdPacket=/dev/ttyBCM` |
| `vendor/lib64/hw/gps.default.so` | GPS HAL module | Medium | Seen in S10-family list; confirm exact image and SONAME |
| `vendor/lib64/hw/android.hardware.gnss@2.0-impl.so` | Android GNSS HIDL implementation | High | Named in S10+ package recipe; exact path may be produced by build package, verify in extracted image |
| `vendor/lib64/hw/vendor.samsung.hardware.gnss@2.0-impl.so` | Samsung GNSS HAL implementation | High | S10-family manifest; verify exact target path |
| `vendor/lib64/vendor.samsung.hardware.gnss@2.0.so` | Samsung GNSS vendor library | High | S10-family manifest; check actual exported SONAME |
| `vendor/lib64/libwrappergps.so` | GPS wrapper library | High | Named in S10+ package recipe |
| `vendor/lib64/sensors.sensorhub.so` | Sensor-hub integration | Medium | Product package `sensors.sensorhub` is listed; include only if present and dependency-relevant |
| `vendor/lib/*` equivalents | 32-bit variants | Medium | Extract if present; S10+ is ARM64, but 32-bit helper/daemon dependencies may exist |
| `system/bin/linker64`, Bionic libraries | Android execution environment | High as dependency class | Do not blindly copy to Nuxel. Inventory exact `PT_INTERP` and `DT_NEEDED`; Android init, HIDL, Binder/VNDK may also be required |

## Firmware candidates — never auto-promote to verified

The following names/locations are searched and copied, if found, only under `payload/unverified-firmware-candidates/`:

- `SensorHub.patch` / `sensorhub*.patch`
- `bcm_sensorhub_a1.patch`
- `bcm4773*.patch`
- `bcm47752*.patch`
- `sensorhub*.bin`

These are search patterns, not a validated list of required S10+ firmware filenames. The supplied Nuxel repo has an empty verified SHA-256 allowlist and no exact patch hash. The exact firmware identity must be established from the `SM-G975F` stock build and target kernel driver before it is loaded.
| `vendor/etc/vintf/manifest.xml` and GNSS-related fragments | Android HAL declaration | Medium | Extracted when present; required to understand Android service registration, not directly usable by native Linux |
| `vendor/etc/permissions/*gps*.xml` / `*gnss*.xml` | Android feature/HAL permissions | Low–medium | Optional metadata; do not copy blindly into Nuxel |
