# Camera Prompt 02 source readiness — qualification addendum (2026-11-22, redacted)

**Entry gate: Prompt00 PASS + Prompt01 real golden no-op PASS. Current: NOT MET.**
**No flash. No reboot. No STREAMON. Offline source inventory only.**

## Source prerequisites (verified against host tree)

| Requirement | Status |
|---|---|
| `drivers/s10-camera-v4l2/{exynos9820-csis.c,s5k-cis.c,ak7374.c}` | **ABSENT** |
| Complete `Linux4` / `android_kernel_samsung_exynos9820` checkout @ `f7194c1d15eded1c2a1a4dc63825b26103435cc0` | **ABSENT** |
| Upstream camera reference `butztill/s10-linux` @ `d8135b2465b3` | not checked out locally; provenance unverified |
| Actual module build artifacts / Module.symvers proving native camera build | **ABSENT** |
| Live `.config` (captured this session) | present (private dir; 176,632 bytes) |
| Sensor table headers (`s5k2l4/3j1/3m3/3p9-tables.h`) | present under `pwn/camera-tables-out/` (runtime `.s5k` data external/prprivate, not in tree) |

## Live kernel config facts affecting Prompt 02 (fresh `.config`)

```
CONFIG_SOC_EXYNOS9820=y
CONFIG_MEDIA_SUPPORT=y
# CONFIG_MEDIA_CONTROLLER is not set          <-- key gap
# CONFIG_VIDEO_V4L2_SUBDEV_API (not present)  <-- not set
CONFIG_VIDEO_V4L2=y
CONFIG_VIDEOBUF2_CORE=y
CONFIG_VIDEOBUF2_MEMOPS=y
CONFIG_VIDEOBUF2_DMA_SG=y
CONFIG_EXYNOS_FIMC_IS=y
CONFIG_VIDEO_EXYNOS_FIMC_IS2=y              <-- vendor driver built-in
```

The native CSIS/V4L2 subdev driver requires `CONFIG_MEDIA_CONTROLLER=y` and the
V4L2 subdev API, which are currently NOT enabled. Prompt 02 must integrate the
native driver as a NEW module and guarantee it never binds a CSIS/sensor/controller
that the built-in FIMC-IS2 driver also claims (coexistence/ownership gate).

## Prompt 02 dependency verdict

Even after Prompt00/Prompt01 gates pass (still blocked on owner signing), Prompt 02
cannot begin until the exact 4.14 kernel checkout (@f7194c1d...) and the native
driver source are located and provenance-pinned. The uploaded public ZIP did not
include them. No camera driver probe, streaming test, BOOT/DT write, or flash
occurred in this session.

## Declaration

- PROMPT02_SOURCE_READY = NO (kernel tree + native driver sources absent; also gated on 00/01)
- DEVICE_PARTITION_WRITES = 0
- DEVICE_REBOOTS = 0
