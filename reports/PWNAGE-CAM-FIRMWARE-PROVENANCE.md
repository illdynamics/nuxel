# PWNAGE-CAM — FIMC-IS firmware provenance and load path

Status: **BLOCKED_FIRMWARE** (device offline at time of writing — see §7).
This document records exactly which files the pinned kernel loads, where it
looks on Nuxel, and where the genuine SM-G975F blobs come from. Nothing here
is downloaded, patched, re-signed or fabricated by Nuxel.

## 1. What the pinned kernel actually requests

Pinned tree: `Linux4/android_kernel_samsung_exynos9820`
`f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253),
`CONFIG_VIDEO_EXYNOS_FIMC_IS2=y`, `CONFIG_EXYNOS_FIMC_IS=y`,
`CONFIG_CAMERA_CIS_{2L4,3J1,3M3,3P9,4HA}_OBJ=y`.

| Consumer (source) | Name requested | Blob? |
|---|---|---|
| `vendor/mcd/fimc-is-sec-define.c` (`finfo->load_fw_name`) | `FIMC_IS_DDK` = `fimc_is_lib.bin` | **yes** |
| same, `load_rta_fw_name` | `FIMC_IS_RTA` = `fimc_is_rta.bin` | **yes** |
| `vendor/mcd/fimc-is-device-ois_mcu.c` | `FIMC_MCU_FW_NAME` = `fimc_is_fw_mcu.bin` | yes (OIS cameras) |
| `fimc-is-device-ischain.c` | `FD_SW_BIN_NAME` = `fimc_is_fd.bin` | optional (FD) |
| `vendor/mcd/fimc-is-companion*.c` | companion ISP image | optional |
| `sensor/module_framework/cis/fimc-is-cis-*.c` | **no file** — per-mode register setfiles are compiled into the kernel (`sensor_2l4_setfiles_A`, …) | no |

Consequences for older reports:

- `s5k2l4_setfile.bin`, `s5k3m3_setfile.bin`, `s5k3p9_setfile.bin`,
  `s5k3j1_setfile.bin`, `s5k4h7_setfile.bin`, `setfile.bin`,
  `exynos9820_camera.bin`, `is-camera*.bin`, `camera_calibration.bin` are **not
  requested by this kernel**. They were guesses; the repository copy of
  `s5k2l4_setfile.bin` is a 3-byte placeholder. `configs/nuxel/camera/camera.json`
  now lists only the real requests and rejects any file below `min_size`.
- Calibration lives in the sensor EEPROM and is read by the EEPROM/ROM driver
  (`fimc_is_sec_readcal_eeprom`), not from a file. Nuxel must never dump or
  overwrite raw EEPROM.

## 2. Where the kernel looks (after patch 0022)

`request_binary()` order, unchanged for stock:

1. `<path1><name>` — Android `/system/vendor/firmware/` (or `/data/` variant)
2. `<path2><name>` — Android dump path, only when a dump exists
3. **NEW (0022):** `/lib/firmware/<name>`, `/usr/lib/firmware/<name>`
4. `request_firmware(name)` (modern firmware loader: `/lib/firmware`)

The boot rootfs must contain `/lib/firmware` (an empty directory is enough)
before the camera group starts. Without it step 3 returns `ENOENT` there but
step 4 still works when udev/firmware_class is available — the patch makes the
cause visible either way (`path-linux load(/lib/firmware/fimc_is_lib.bin) ret(…)`).

## 3. Genuine blob source (owner's own hardware family)

The exact SM-G975F (`beyond2lte`) vendor blobs are published by the
open-source Exynos9820 device community. Canonical source used for identity and
expected sizes:

- repo: `TheMuppets/proprietary_vendor_samsung_beyond2lte`
- path: `proprietary/vendor/firmware/`
- import commit: `509928ee97076773b6d3668d8fbd8566e1a087aa`
  ("Import beyond2lte from lineage-19.1 (e300002)", 2022-09-20)

| file | size (bytes) | git blob sha1 |
|---|---:|---|
| `fimc_is_lib.bin` | 4 432 944 | `2f1a628c3182ec923038a4e02b5a7d49ca4aad72` |
| `fimc_is_rta.bin` | 3 986 368 | `5b8088f9b631344fea04ae6d021b6242692e140b` |
| `fimc_is_fw_mcu.bin` | 34 348 | `1bb49094b79fd5e0850ddd6e6abf11417ca8da33` |
| `setfile_2l4.bin` (reference only — not requested by this kernel) | 4 080 120 | `6b01bed75b9370011e822456258e4ccfc1ff6529` |

Acquisition: either pull these exact files from the owner's **stock Android**
system image for this family, or take the identical files from the published
vendor blobs at the commit above, then verify size + SHA-256 locally before
installing. Record the SHA-256 of the installed copies in the deploy log
(`node identity`, `path`, `sha256`, `size`, `source commit`). Do not mix blobs
from another model (A52/other Exynos) and do not edit or re-sign them.

## 4. What is explicitly NOT installed

`libexynoscamera3.so`, `camera.exynos9820.so` and any Android camera provider
(see `configs/nuxel/camera/camera.json` `never_install`). No Android HAL is
needed or used: the pinned kernel drives the ISP itself and exposes the
FIMC-IS nodes directly.

## 5. Measuring the pipeline (authoritative tool)

`tools/s10plus/fimc-capture/nuxel-fimc-capture` (static aarch64) drives the
EXACT ioctls the vendor nodes implement:

```
QUERYCAP → S_INPUT → S_FMT(MPLANE) → REQBUFS → QUERYBUF → QBUF
        → STREAMON → DQBUF → STREAMOFF
```

Generic `v4l2-ctl --stream-mmap` never selects the MPLANE ioctl path on these
nodes and returns `ENOTTY`/`EINVAL`. That result was repeatedly mis-read as
"camera impossible"; it only proved the wrong library was used.

Build: `make -C tools/s10plus/fimc-capture CROSS=aarch64-linux-gnu-`
Install (live): `/usr/libexec/nuxel/nuxel-fimc-capture`, mode 0755, owner root.

Probe one candidate node:

```
nuxel-fimc-capture --node /dev/video<N> --input 0 --probe-only --json
```

Result vocabulary: `PROBE_OK`, `S_FMT_FAILED` (wrong fourcc/size),
`REQBUFS_FAILED` (queue/framemgr not ready), `NO_FRAME_TIMEOUT` (ISP/sensor
not producing — firmware/power), `FRAMES_CAPTURED` (real driver buffers).

## 6. Device tree facts confirmed from the pinned DTS

`arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_17.dts`:

- `fimc-is-2l4@10`, `compatible = "samsung,exynos5-fimc-is-cis-2l4"`,
  `id = <0>`, `setfile = "default"` — rear main S5K2L4 (the driver selects its
  compiled-in `setfile_A` tables). I2C address here is `0x10`; a historically
  logged `@20` must be re-checked on the live device, not assumed.
- `camera_info0..4` valid, `internal_id` 0,1,4,3,2 → five lenses present.
- `max_supported_camera = <9>`, `supported_cameraId = <0 1 0x14 0x15 0x16 0x17 0x32 0x33 0x34>`.

## 7. Honest status of this run

- 2026-11-14: the S10+ was NOT reachable — `192.168.178.167` absent from
  ARP/ICMP, no `adb` device, no USB Samsung device attached to the
  workstation. Therefore no live probe, no flash, no frame.
- Offline work completed (see `PWNAGE-CAM-REPORT.md`).
- Remaining acceptance is `NOT_TESTED` until the handset is back on the
  network or USB.
