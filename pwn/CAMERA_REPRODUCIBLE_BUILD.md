# NUXEL S10+ Camera — Reproducible Build

**Date:** 2026-11-20

## Host toolchain

- Cross compiler: `aarch64-linux-gnu-gcc` (GCC 15.2.0), present at
  `/opt/homebrew/bin/aarch64-linux-gnu-gcc`.
- V4L2 UAPI headers: vendored at `tools/s10plus/v4l2-uapi/` (4.14 ioctl/videodev2).

## Build the capture tools

```sh
cd tools/s10plus/fimc-capture
aarch64-linux-gnu-gcc -O2 -Wall -std=gnu99 -I../v4l2-uapi -static -o nuxel-fimc-leader-capture2 nuxel-fimc-leader-capture2.c
```

Or via Makefile:
```sh
make S10PLUS=1   # cross-build with aarch64-linux-gnu-, static link
```

Deploy (userspace only):
```sh
scp -i ~/.ssh/wicked_wqn_id_rsa nuxel-fimc-leader-capture2 root@10.11.12.99:/usr/local/bin/
```

## Kernel build (only if Strategy B is chosen — requires flash)

```sh
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone --cross aarch64-linux-gnu-
```

- Authoritative source: `https://github.com/Linux4/android_kernel_samsung_exynos9820`
  @ commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253).
- Defconfig: `exynos9820-beyond2lte_defconfig` + `nuxel-drm-kbase.fragment`.
- Patches applied lexically from `kernel/s10plus/patches/`.
- Output: `kernel/s10plus/.build/out/arch/arm64/boot/Image.gz` + beyond2lte DTB.

## Strategy B port inputs (s10-linux reference)

- Reference: `butztill/s10-linux` @ commit `d8135b2465b3a9f1c0e7f1f6be71451ad185b303`.
- Driver: `drivers/s10-camera-v4l2/{exynos9820-csis.c,s5k-cis.c,ak7374.c,s5k-fw.h,s5k-fw-manifest.h}` (~3000 lines).
- Sensor register tables (GPL): already present in our on-device kernel source at
  `drivers/media/platform/exynos/fimc-is2/sensor/module_framework/cis/fimc-is-cis-{2l4,3m3,3p9,3j1}-setA.h`.
- libcamera patches: `patches/libcamera/` (software ISP).

## Provenance / licensing

- s10-linux: GPL-2.0-only (multi-license collection); sensor tables are GPL from
  LineageOS android_kernel_samsung_exynos9820 @ `4bcfb0263b21`.
- Do NOT commit proprietary firmware/setfiles/public color tuning data to the public tree.
