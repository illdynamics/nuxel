# NUXEL S10+ Camera Driver Architecture — Final Decision Record

**Date:** 2026-11-20 (session 3, definitive)
**Target:** SM-G975F beyond2lte, Exynos9820, kernel 4.14.253-gf7194c1d15ed-dirty

## FINAL DECISION: Strategy B — port s10-linux s10-camera-v4l2 native V4L2 driver

## Why Stage A (vendor FIMC-IS2) is terminally impractical (now proven, not assumed)

Session 3 cracked the last "simple" blocker but exposed the true depth:

1. S_FMT -EINVAL root cause = missing private V4L2_CID_IS_S_SENSOR_SIZE control.
   FIXED and verified live (sensor S_FMT/REQBUFS/QBUF now all succeed).

2. But sensor leader STREAMON triggers a HARDWARE WATCHDOG KERNEL PANIC
   ("Panic#2", pstore ramoops) and reboot. Verified live.

3. Source root cause of the panic: fimc_is_sensor_back_start() starts the MIPI
   CSI FLITE DMA, but the ISP chain is not initialized. fimc_is_itf_process_start()
   only runs inside fimc_is_ischain_start(), reached via the 3AA group-leader's
   .start_streaming -> fimc_is_ischain_3aa_start -> groupmgr_start ->
   fimc_is_ischain_start(), which requires:
     - FIMC_IS_ISCHAIN_INIT state (set during ischain init sequence)
     - fimc_is_hw_ischain_cfg, fimc_is_ischain_s_sensor_size,
       fimc_is_itf_sensor_mode, fimc_is_ischain_s_path, fimc_is_itf_s_param,
       fimc_is_itf_f_param, fimc_is_itf_sys_ctl, fimc_is_itf_init_process_start
     - dozens of ISP-firmware parameters (setfile, path, exposure/gain, etc.)
   This is effectively reimplementing Samsung's proprietary libexynoscamera HAL,
   which programs the FIMC-IS2 ISP firmware via the itf_* interface. No public
   native-Linux precedent exists. Every wrong live attempt risks a kernel crash.

VERDICT: Stage A is high-risk, undocumented, crash-prone reverse engineering with
no success precedent. Not a viable primary path.

## Why Strategy B is the correct choice

1. s10-linux's `drivers/s10-camera-v4l2/` is a clean, self-contained, GPLv2,
   standard-V4L2 driver (~3000 lines: exynos9820-csis.c + s5k-cis.c + ak7374.c).
   It is the ONLY publicly documented native-Linux path that produced physical
   still images on Exynos9820 (4 sensors, documented in s10-linux STATUS.md).

2. The 4.14.253 Samsung kernel ALREADY contains the complete mainline V4L2/media
   framework (just disabled):
   - drivers/media/v4l2-core/{v4l2-subdev,v4l2-async,v4l2-fwnode,v4l2-mc,
     v4l2-device,v4l2-ctrls,v4l2-mem2mem}.c — all present
   - drivers/media/{media-device,media-entity,media-devnode}.c — present
   - videobuf2-{core,v4l2,dma-contig,dma-sg}.c — all present in-tree
   - include/media/v4l2-{subdev,async,fwnode,mc,mediabus}.h — all present
   - Kconfig MEDIA_CONTROLLER / VIDEO_V4L2_SUBDEV_API / MEDIA_CONTROLLER_DVB exist
   - fully #ifdef CONFIG_MEDIA_CONTROLLER gated = complete mainline impl

   Only these are disabled and need enabling:
     CONFIG_MEDIA_CONTROLLER=n -> y
     CONFIG_VIDEO_V4L2_SUBDEV_API=n -> y
     CONFIG_VIDEOBUF2_DMA_CONTIG=n -> y
     CONFIG_VIDEOBUF2_V4L2=n -> y

3. Sensor register tables are GPL and already in-tree:
   fimc-is-cis-{2l4,3m3,3p9,3j1}-setA.h under sensors/module_framework/cis/
   — exactly what s10-linux's prepare-s5k-tables.py consumes to generate the
   driver's runtime register tables (no proprietary firmware needed).

4. The 4.14 kernel has the Exynos MIPI PHY driver (exynos-mipi-phy, probing
   csis0/1/2/3 PHYs as seen in boot log) and the Exynos9820 CSIS register info
   can be derived from s10-linux's exynos9820-csis.c + the in-tree CAMIF/FLITE
   knowledge in fimc-is-device-csi_v4.c.

5. Strategy B is developed OFFLINE (cross-compile + static analysis) — no repeated
   live-device kernel crashes during bring-up. Flash only once a verified build is
   ready, with a rollback boot image preserved.

## Gap / effort (honest)

- s10-linux targets Linux 7.2-rc2 with post-6.x APIs (v4l2_subdev_enable_streams,
  v4l2_subdev_state, device_link, modern pinctrl/GPIO consumer, clk_bulk).
  These must be rewritten to the 4.14-era APIs that ARE present in-tree
  (v4l2_subdev_pad_config, .s_stream video op, media_entity_pipeline_start,
  legacy pinctrl/gpiod, singular clk_prepare_enable).
- Exynos9820 CSIS register/clock/PHY programming must be ported from s10-linux
  + validated against the 4.14 tree's in-tree CAMIF/FLITE/csi_v4 code.
- Produces RAW10 Bayer only; requires a libcamera software-ISP pipeline handler
  for color preview/still/video.
- 4HA front-depth (5th S10+ sensor) must be added (s10-linux only covers 4).

## Rollback plan (unchanged, safe)
- Vendor fimc-is2 driver stays in-tree; re-select config to roll back.
- Preserve last-known-good boot image + SHA-256; TWRP/USB recovery stands.
- Stage A tools remain as reference.

## Next concrete actions
1. Enable the 4 media-framework config options in a Nuxel kernel fragment; do a
   baseline offline build to confirm the in-tree framework compiles on 4.14.
2. Port s10-camera-v4l2 → 4.14 (rewrite post-6.x APIs to in-tree 4.14 APIs).
3. Generate *-tables.h from in-tree GPL fimc-is-cis-*-setA.h.
4. Add beyond2lte camera DTBO (5 sensors, CSIS0/1/2/3, clocks/regulators/gpio).
5. Cross-compile; verify; preserve rollback image; flash via TWRP; bounded test.
