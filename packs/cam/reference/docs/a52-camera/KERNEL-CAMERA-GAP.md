# A52 Kernel / Camera Gap Analysis

## What the 4.14.253 kernel already provides (observed)

- Samsung Exynos 9820 FIMC-IS driver loaded (`exynos-fimc-is`, `exynos-fimc-is-sensor`).
- 5 sensor modules bound (`2l4`, `3m3`, `3p9`, `3j1`, `4ha`) via `FIMC-IS-SENSOR-MODULE-*`.
- OIS actuators (`ak737x`) ×3 and OIS controller bound.
- Camera EEPROM drivers probed (calibration data present).
- MIPI CSI phys, GDC, ION camera heaps, reserved memory all initialised.
- `SMC_SECCAM_SETENV/INIT` secure-camera TrustZone handshake completed (no error).

## The gap (precise, non-destructive)

The FIMC-IS capture nodes are exposed through the vendor's private V4L2 extension:

1. `V4L2_CAP_VIDEO_CAPTURE_MPLANE` + `V4L2_CAP_EXT_PIX_FORMAT` set on `exynos-fimc-is-*` nodes.
2. Standard `VIDIOC_S_FMT` returns `ENOTTY`; `ENUM_FMT` yields nothing; `REQBUFS`/`QUERYBUF`
   return `EINVAL` without the vendor's private format/stream setup.
3. No media-controller device (`/dev/media*`) and no `v4l-subdev` nodes → libcamera cannot
   construct a pipeline.
4. No camera sensor "setfile" firmware blobs or ISP firmware on the rootfs (`/vendor` missing).
   (Setfiles on this platform are normally supplied by the vendor HAL, not the generic firmware
   loader; their absence on Fedora is expected, not a simple missing-file bug.)

## What is required to close the gap (qualified, unverified)

- **Option A (upstream/native):** a `libcamera` pipeline handler for the Samsung FIMC-IS
  (Exynos 9820) that speaks the vendor's private ioctls — substantial new driver work; no such
  handler exists upstream today.
- **Option B (vendor):** port the proprietary `libexynoscamera` + camera providers to Fedora
  ARM64 — **blocked**: proprietary, Android-framework-bound, cannot be lawfully installed.
- **Option C (kernel):** rework the downstream FIMC-IS driver to expose a standard V4L2/media
  controller surface — large, risky, requires kernel replacement (out of scope; no flashing).

## Explicit non-goals honoured

- No kernel/DTS/boot/recovery/partition flashing (mission stop condition).
- No extraction of proprietary firmware from other phones, no unlicensed blob substitution.
- No blind I²C/register writes.
- No Android HAL / Magisk installation.

## Recommendation

Deliver the userspace/app/backend work (done, see sibling docs) and record this as
**HARDWARE_BLOCKED** pending a lawful FIMC-IS libcamera pipeline handler (Option A). The first
feasible non-destructive next step is Option A: an off-device, buildable libcamera pipeline
handler skeleton against the documented vendor ioctl surface, cross-built for aarch64 on a
Fedora host — not a device-side kernel flash.
