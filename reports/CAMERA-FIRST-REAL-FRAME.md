# Camera first-real-frame bring-up — 2026-11-17

## Outcome

**First physical frame: BLOCKED.** No frame was requested, dequeued, saved, or
claimed. The earliest measured gate is the vendor firmware selection invoked by
the Samsung sensor `VIDIOC_S_INPUT` path: `Camera: Failed open phone firmware`,
then `fimc_is_sec_run_fw_sel ... (-5)`. This happened after successful EEPROM
calibration read on the physical rear-main module.

## Evidence classification

| Finding | Classification | Evidence |
|---|---|---|
| Handset/kernel | PROVED_LIVE | `4.14.253-gf7194c1d15ed-dirty`, 2026-11-17T12:52:20+01:00 |
| Board/revision | PROVED_LIVE | kernel command line: `SM-G975F`, revision `26`, EUR/OPEN |
| Running-config SHA-256 | PROVED_LIVE | `/proc/config.gz`: `5aebd0711ac9cf7383c7d8a185826256a382fce111d064bd53f47909ee885583` |
| Local build Image SHA-256 | HISTORICAL_LIVE | `/root/kbuild/out/arch/arm64/boot/Image`: `e42813084477c71a45415466b4bf469e22f5c4ab45b078bb5c9d992148d5d3ff`; this is not represented as a BOOT-partition readback |
| BOOT-partition SHA-256 | UNKNOWN | no partition read was performed; no flash was contemplated |
| FIMC-IS topology | PROVED_LIVE | 68 `/dev/video*` entries; no `/dev/media*` or `/dev/v4l-subdev*` |
| Five module drivers | PROVED_LIVE | sysfs binds `FIMC-IS-SENSOR-MODULE-{2L4,3M3,3P9,3J1,4HA}` |
| Main rear sensor selection | PROVED_LIVE | `/dev/video101`, sensor enum `37` (`SENSOR_NAME_SAK2L4`) accepted by `S_INPUT` |
| EEPROM/calibration | PROVED_LIVE | kernel logged ROM 0, `cal_size:65536`, map `V010` during the owner-authorized bounded probe; no EEPROM writes occurred |
| Firmware request/load | PROVED_LIVE (failure) | kernel logged `Failed open phone firmware` and vendor selection error `-5` |
| `/lib/firmware` fallback patch in source | PROVED_IN_PINNED_SOURCE | pinned `f7194c1d15eded1c2a1a4dc63825b26103435cc0`, `fimc-is-binary.c` / `fimc-is-binary.h` |
| Linux firmware fallback in running BOOT | UNKNOWN | live `firmware_class.path` is `/vendor/firmware`; no accepted FIMC-IS binary has been observed |
| Supplied camera blobs | PRESENT_IN_ZIP | eight blobs exist, but their hashes disagree with the manifest for `fimc_is_lib.bin`, `fimc_is_rta.bin`, and all five setfiles; `setfile_3j1.bin` == `setfile_4ha.bin` |
| Real camera frame | NOT_TESTED / BLOCKED | no `REQBUFS`, `QBUF`, `STREAMON`, or `DQBUF` was performed |
| Camera daemon binary | PROVED_LIVE (absent) | no live `nuxel-fimc-capture` binary was installed; the portal unit is `disabled` / `inactive` |

## Actual node and ABI results

The supplied capture client was not a valid first-light client for this ABI:

| Node type | Live examples | `QUERYCAP` result | Meaning |
|---|---|---|---|
| Sensor endpoint | `video101`–`video106` (`ss0`–`ss5`) | `0x84202002`, multi-planar output | Must receive the Samsung numeric sensor enum through `S_INPUT` before the ISP chain |
| ISP/output endpoint | `video111`, `112`, `113`, `114`, `121`… | `0x84201001`, multi-planar capture | Nominal `S_FMT` returned success but `G_FMT` was all zero, so no usable format exists yet |

The corrected client rejects a zeroed `G_FMT` as `FORMAT_UNCOMMITTED` instead
of reporting `PROBE_OK`. It also requires `--allow-sensor-init` for a sensor
probe: Samsung's `S_INPUT` is not read-only; it reads calibration and can toggle
retention even without user-space streaming.

## Candidate decision

| Candidate | Result | Reason |
|---|---|---|
| Existing multipanar client + small backend | BLOCKED | Useful only after a real configured ISP format; it previously omitted the sensor endpoint and falsely passed zero format |
| Dedicated Exynos9820 libcamera handler | DEFERRED | libcamera has no listed FIMC-IS2/Exynos9820 pipeline and this kernel has no media graph; it cannot bypass the missing accepted firmware |
| Matching Android vendor HAL bridge | DEFERRED | Requires exact matching Android/Bionic/vendor runtime and licensed blobs; not installed or substituted |
| Kernel V4L2/media adaptation | DEFERRED | Larger invasive work; cannot make an unverified firmware bundle acceptable |
| New code in this change | SELECTED | Harden the bounded diagnostic to fail closed, preserving the live image and privacy policy |

Official references: [libcamera supported-platform FAQ](https://libcamera.org/faq.html),
[pipeline-handler guide](https://docs.libcamera.org/master/guides/pipeline-handler.html),
and [LineageOS Exynos9820 proprietary-file inventory](https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/proprietary-files.txt).

## Deployment and rollback

No persistent handset files, firmware, system image, BOOT image, DTB, partition,
calibration, or service state was modified. The temporary diagnostic binary was
uploaded only to `/tmp` and removed after the test. Thus no reflash or reboot is
needed and rollback is not applicable. Existing recovery/BOOT state was left
untouched.

## Required next artifact

Obtain an owner-authorized, lawful package for **this G975F EUR OPEN revision
26 firmware/DDK ABI** containing the vendor-selected phone firmware file(s),
with original source path, source build fingerprint, hash, license/redistribution
status, and any paired RTA/lib/setfile metadata. The current supplied bundle
cannot be installed because its manifest hashes are inconsistent and the 3J1/4HA
identity is unexplained. After provenance is established, stage it in an
isolated system-image payload, prove the exact requested basename and accepted
loader response, then request a new owner-authorized physical capture session.

## Recovery correction — 2026-11-17

See [continued source and firmware investigation](CAMERA-RECOVERY-2026-11-17.md).
The owner AP has now been recovered and all eight bundled camera files match
it. The direct failing open is `/system/vendor/firmware/fimc_is_lib.bin`.
The running sensor-group ABI decodes the former input value 37 as rear position
zero, not a sensor enum; its earlier enum interpretation above is superseded.
No new physical camera test has occurred.
