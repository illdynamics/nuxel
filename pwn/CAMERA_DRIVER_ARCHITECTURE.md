# NUXEL S10+ Camera Driver Architecture — Decision Record (updated)

**Date:** 2026-11-20 (continuation)
**Target:** SM-G975F beyond2lte, Exynos9820, kernel 4.14.253-gf7194c1d15ed-dirty
**Author:** Nuxel camera engineering agent

## DECISION: Strategy B — port the s10-linux custom native V4L2 driver

## New decisive evidence (this continuation)

1. The 4.14.253 Samsung downstream kernel **already contains the complete
   mainline-style V4L2/media framework**, just disabled in config:
   - `drivers/media/v4l2-core/v4l2-subdev.c`, `v4l2-async.c`, `v4l2-fwnode.c`,
     `v4l2-mc.c`, `v4l2-device.c`, `v4l2-ctrls.c`, `v4l2-mem2mem.c` — all present.
   - `drivers/media/media-device.c`, `media-entity.c`, `media-devnode.c` present.
   - `videobuf2-core.c`, `videobuf2-v4l2.c`, `videobuf2-dma-contig.c`,
     `videobuf2-dma-sg.c` — all present in-tree (`drivers/media/v4l2-core/`).
   - `include/media/v4l2-subdev.h`, `v4l2-async.h`, `v4l2-fwnode.h`, `v4l2-mc.h`,
     `v4l2-mediabus.h` — all present.
   - Kconfig symbols `MEDIA_CONTROLLER`, `VIDEO_V4L2_SUBDEV_API`,
     `MEDIA_CONTROLLER_DVB` exist in `drivers/media/Kconfig`.
   - Source is fully `#ifdef CONFIG_MEDIA_CONTROLLER` / `CONFIG_VIDEO_V4L2_SUBDEV_API`
     gated, i.e. it is the *complete* mainline implementation, not a Samsung stub.
   - Older Exynos MIPI CSIS reference driver exists in-tree:
     `drivers/media/platform/exynos4-is/mipi-csis.c` (Exynos4 register layout;
     Exynos9820 CSIS differs and needs the s10-linux `exynos9820-csis.c` ported).

   Disabled config to enable:
   - `CONFIG_MEDIA_CONTROLLER=n` -> `=y`
   - `CONFIG_VIDEO_V4L2_SUBDEV_API=n` -> `=y`
   - `CONFIG_VIDEOBUF2_DMA_CONTIG=n` (not set) -> `=y` (or `=m`)
   - `CONFIG_VIDEOBUF2_V4L2=n` (not set) -> `=y`

2. Sensor register tables are GPL-available on-device (not proprietary runtime):
   `drivers/media/platform/exynos/fimc-is2/sensor/module_framework/cis/fimc-is-cis-{2l4,3m3,3p9,3j1}-setA.h`
   — exactly what s10-linux's `scripts/prepare-s5k-tables.py` consumes.

3. Stage A (FIMC-IS2 vendor userspace HAL reimplementation) confirmed high-risk:
   - `sensor_module_s_format()` (fimc-is-device-module-base.c:1067) requires
     `device->cfg->mode` set by the proprietary ischain path; S_FMT alone cannot
     establish it (verified source-level, matches live -EINVAL on /dev/video101).
   - No public precedent for driving FIMC-IS2 from native Linux userspace.
   - Already 2+ sessions stalled; further effort is undirected reverse engineering.

## Chosen architecture

Port `s10-linux`'s `drivers/s10-camera-v4l2/` (GPLv2, ~3000 lines) to the
4.14.253 Samsung vendor kernel, enabling the in-tree media framework, and expose
standard V4L2 (RAW10 Bayer) capture nodes for the rear-main 2L4 first, then 3M3/
3P9/3J1, with a libcamera software-ISP pipeline for color/preview/video.

## Required changes (bounded)

1. Enable `CONFIG_MEDIA_CONTROLLER=y`, `CONFIG_VIDEO_V4L2_SUBDEV_API=y`,
   `CONFIG_VIDEOBUF2_DMA_CONTIG=y`, `CONFIG_VIDEOBUF2_V4L2=y` in the Nuxel
   kernel defconfig/fragment.
2. Port `s10-camera-v4l2/` (exynos9820-csis.c, s5k-cis.c, ak7374.c) to 4.14:
   - Adapt modern `v4l2_async`/`v4l2_fwnode`/`device_link`/`pinctrl`/GPIO consumer
     APIs to the 4.14 equivalents present in-tree.
   - Wire the Exynos9820 CSIS clock/regulator/PMU sequences from the s10-linux
     DTS and the `fimc-is2` CAMIF/FLITE hardware knowledge into the driver.
3. Generate `*-tables.h` from the in-tree GPL `fimc-is-cis-*-setA.h` headers.
4. Add beyond2lte DTS camera nodes (or a new DTBO overlay) describing the 5 sensors,
   CSIS, clocks, regulators, GPIO/reset, and I2C addresses captured from the
   current beyond2lte overlay DTS.
5. Build via `kernel/s10plus/build-kernel.sh`, flash via TWRP (authorized, see
   `cam.md`), preserving the last-known-good boot image.
6. libcamera software-ISP pipeline handler + PipeWire producer.

## Rollback plan

- Vendor `fimc-is2` driver remains in-tree; re-select it in config to roll back.
- Preserve last-known-good boot image + its SHA-256; TWRP/USB recovery path stands.
- Stage A tools/binaries remain as reference, not removed.

## Alternatives considered

- **Stage A (complete vendor HAL)** — fastest if it worked, but no public precedent
  and the sensor mode is set only via the undocumented ischain path. Rejected as
  primary; vendor driver retained as rollback/reference.
- **gangg111/S10Plus_Linux (Droidian)** — Camera2/libhybris = Android userspace
  dependency; violates zero-Android requirement. Hardware/topology reference only.

## Reusable components

- s10-linux `s10-camera-v4l2/` driver (exynos9820-csis.c, s5k-cis.c, ak7374.c,
  s5k-fw.h/manifest, prepare-s5k-tables.py).
- In-tree GPL sensor tables `fimc-is-cis-2l4/3m3/3p9/3j1-setA.h`.
- In-tree media framework (vb2, v4l2-subdev, media controller, v4l2-async/fwnode).
- Existing firmware (8 blobs at /system/vendor/firmware preserved).
- Existing capture probes as reference (nuxel-ion-capture.c etc.).
