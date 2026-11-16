# NUXEL A53 — Camera Pipeline Blockers (fresh live evidence)

## Verdict: `BLOCKED_HARDWARE` — vendor FIMC-IS private V4L2 extension (unchanged from A52)

Re-confirmed live this session (not copied from A52 notes):

```
# python3 /usr/libexec/nuxel/nuxel-v4l2-capture-test.py /dev/video111
node: /dev/video111
1. S_FMT   FAILED errno=25 (Inappropriate ioctl for device)
2. REQBUFS FAILED errno=22 (Invalid argument)
3. QUERYBUF FAILED errno=22 (Invalid argument)
```

`/dev/video111` is an `exynos-fimc-is-30c` sensor-slot-0 pipeline node. It advertises
`V4L2_CAP_VIDEO_CAPTURE_MPLANE` + `V4L2_CAP_EXT_PIX_FORMAT` (the Samsung private pixel-format
extension) but does **not** implement the standard `VIDIOC_S_FMT`/`REQBUFS`/`QUERYBUF` path.

## Root cause (precise)

The downstream 4.14 Samsung FIMC-IS driver streams only through the proprietary Samsung camera
userspace (`libexynoscamera` + camera providers). There is no `/dev/media*` / `/dev/v4l-subdev*`,
no libcamera, no `v4l2src`, no PipeWire, and no camera setfile/ISP firmware on the rootfs. The
standard Linux capture stack has nothing to attach to.

## Enumeration is not capture

All five sensors remain driver-bound (`fimc-is_sensor_2l4@20`, `_3m3@5A`, `_3p9@2D`, `_3j1@10`,
`_4ha@10`), and the ISP/OIS/EEPROM probed. **Enumeration ≠ frames.** No USB-UVC webcam or test
pattern was used to upgrade the verdict.

## Non-destructive future remediation (NOT performed — out of scope, no flashing)

- Option A: a libcamera pipeline handler for Exynos FIMC-IS speaking the vendor ioctls
  (cross-buildable off-device, no flash).
- Option B (vendor `libexynoscamera`): blocked (proprietary, Android-framework-bound).
- Option C (kernel rework to standard V4L2/MC): requires kernel replacement — forbidden here.

The exact A52 `BASELINE-CAPTURE.json` and `HARDWARE-BLOCKERS.md` remain authoritative; this document
re-proves the first failing stage on today's boot.
