# NUXEL S10+ Camera — Reproducible Build

**Date:** 2026-11-20
**Target:** SM-G975F beyond2lte, Exynos9820, kernel 4.14.253-gf7194c1d15ed-dirty

## Pinned upstream sources

| Component | Repository | Commit | License |
|---|---|---|---|
| Vendor kernel | Linux4/android_kernel_samsung_exynos9820 | f7194c1d15eded1c2a1a4dc63825b26103435cc0 | GPL-2.0 |
| Custom camera driver (reference) | butztill/s10-linux drivers/s10-camera-v4l2 | d8135b2465b3 | GPL-2.0-only |
| Sensor register tables | in-tree fimc-is-cis-{2l4,3m3,3p9,3j1}-setA.h | (vendor kernel) | GPL-2.0 (Samsung) |
| s10-linux media framework notes | butztill/s10-linux docs + patches | d8135b2465b3 | GPL-2.0-only |

## Kernel build (host: macOS, toolchain aarch64-linux-gnu-gcc 15.2.0)

```sh
# 1. Clone + checkout the exact vendor kernel
git clone --filter=blob:none https://github.com/Linux4/android_kernel_samsung_exynos9820 \
  kernel/s10plus/.build/src
git -C kernel/s10plus/.build/src checkout f7194c1d15eded1c2a1a4dc63825b26103435cc0

# 2. Apply Nuxel patches + capability fragment + build (existing wrapper)
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone --jobs 4 \
  --cross aarch64-linux-gnu-
# Output: kernel/s10plus/.build/out/arch/arm64/boot/Image.gz + beyond2lte DTBs

# 3. Camera media-framework fragment (Strategy B)
# kernel/s10plus/configs/nuxel-camera-v4l2.fragment adds:
#   CONFIG_MEDIA_CONTROLLER=y, CONFIG_VIDEO_V4L2_SUBDEV_API=y (+ selects
#   CONFIG_V4L2_FWNODE, CONFIG_VIDEOBUF2_DMA_CONTIG via the camera driver Kconfig)
```

Offline framework-compile check (already VERIFIED):
```sh
cd kernel/s10plus/.build/src
make O=OUT ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- exynos9820-beyond2lte_defconfig
# add CONFIG_MEDIA_CONTROLLER=y CONFIG_VIDEO_V4L2_SUBDEV_API=y, then:
make O=OUT ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make O=OUT ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- drivers/media/
# -> media-device/entity/devnode, v4l2-subdev/async/mc/ctrls, videobuf2-* all build
```

## Driver port (remaining, bounded)

Port `s10-camera-v4l2/` (exynos9820-csis.c, s5k-cis.c, ak7374.c) to this 4.14 tree:
rewrite post-6.x APIs to the 4.14 equivalents present in-tree:
- v4l2_subdev_state -> v4l2_subdev_pad_config
- .enable_streams/.disable_streams -> .s_stream (video op)
- v4l2_async_connection/nf_init -> v4l2_async_subdev + notifier bound/complete
- v4l2_fwnode_endpoint_alloc_parse -> v4l2_fwnode_endpoint_parse
- video_device_pipeline_start -> media_entity_pipeline_start (4.14 exists)
- __v4l2_ctrl_modify_range/s_ctrl -> v4l2_ctrl_modify_range/s_ctrl
- pm_runtime_resume_and_get -> pm_runtime_get_sync
- mux_control -> Samsung mux or pinctrl-based MIPI lane mux

Generate sensor register tables (GPL) with:
```sh
python3 pwn/upstream-camera-research/s10-linux/scripts/prepare-s5k-tables.py \
  --reference-dir <in-tree fimc-is2 sensor cis dir> \
  --output-dir <driver dir>
```

## Firmware (external, NOT committed)

The driver's custom S5K runtime tables are GPL-generated from the in-tree
Samsung setfile headers (no proprietary payload in the open tree). The vendor
FIMC-IS2 firmware blobs (8) already deployed to /system/vendor/firmware remain
for the rollback vendor path; they are never committed to public git.
