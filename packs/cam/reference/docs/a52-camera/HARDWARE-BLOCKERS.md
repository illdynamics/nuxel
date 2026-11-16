# A52 Hardware Blockers — camera capture

## Verdict

**HARDWARE_BLOCKED — Scenario E.** The built-in S10+ cameras are enumerated and
driver-bound, but no real frame can be captured through a standard Linux path.

## Reproducible failure evidence

1. **`VIDIOC_S_FMT` returns ENOTTY (errno 25)** on every FIMC-IS capture node
   (`/dev/video110`–`/dev/video114`, `/dev/video160`, …). This is the first
   failing stage.
2. **`V4L2_CAP_EXT_PIX_FORMAT` (0x00200000)** is set on those nodes — the Samsung
   vendor extension signalling a private pixel-format path.
3. **No `/dev/media*` and no `/dev/v4l-subdev*`** → no media-controller graph for
   libcamera to walk.
4. **No camera setfiles / ISP firmware** on the rootfs (`/vendor` missing;
   `/lib/firmware` has only Wi-Fi + regulatory blobs).
5. **No userspace capture stack** — `v4l2src` (GStreamer good) absent,
   libcamera absent, PipeWire/WirePlumber absent, xdg-desktop-portal absent,
   and no Samsung camera HAL (`libexynoscamera`) present.

Reproduce on the device:

```sh
python3 tools/s10plus/a52/nuxel-v4l2-capture-test.py /dev/video111
#   S_FMT    FAILED errno=25 (Inappropriate ioctl for device)
```

## Root cause (precise)

The downstream 4.14 Samsung FIMC-IS driver streams only via the proprietary
Samsung camera userspace (Android `libexynoscamera` + camera providers). That
component is Android-framework-bound and proprietary; it is not installed and
cannot be lawfully extracted from another phone or installed "by stealth" into
Fedora ARM64.

## Closest feasible non-destructive next step (unverified estimate)

A **libcamera pipeline handler for Exynos FIMC-IS** that implements the vendor's
private format/stream ioctls. This is new driver-adjacent work, cross-buildable
for aarch64 on a Fedora host, and does **not** require flashing the phone:

1. Document the FIMC-IS private ioctl surface (from the 4.14 vendor source).
2. Write a pipeline-handler skeleton mapping sensor slot → V4L2 nodes → ISP.
3. Cross-build and unit-test against recorded fixtures off-device.
4. Only after that, attempt a bounded on-device stream (owner-assisted).

Alternative kernel rework (expose a standard V4L2/MC surface) requires a kernel
replacement — out of scope and explicitly disallowed here (no flashing).

## Explicitly NOT attempted / NOT done

- No kernel/DT/boot/recovery/partition flashing.
- No proprietary firmware extraction or unlicensed blob substitution.
- No blind I²C/register writes, no Android HAL/Magisk/TWRP.
- No fake green status: no frame was captured, so no hardware success is claimed.
