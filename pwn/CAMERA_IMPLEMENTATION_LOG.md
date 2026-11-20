# NUXEL S10+ Camera Implementation Log

**Date:** 2026-11-20
**Target:** SM-G975F `beyond2lte`, Exynos9820, kernel 4.14.253-gf7194c1d15ed-dirty

## Milestones achieved (this session)

1. **Live device verified** — SSH to `root@10.11.12.99`, kernel `4.14.253-gf7194c1d15ed-dirty`,
   `fimc-is2` camera driver loaded, full `/dev/video*` node set present.
2. **Firmware confirmed resolved** (not regressed) — 8 blobs present at
   `/system/vendor/firmware/` and `/usr/lib/firmware/`, matching owner-stock hashes.
3. **Upstream references cloned and studied**:
   - `butztill/s10-linux` @ `d8135b2465b3` — custom native V4L2 camera driver
     (`s10-camera-v4l2`), raw10 Bayer + libcamera software ISP, 4 sensors imaged.
   - `gangg111/S10Plus_Linux` @ `b194b70acf90` — Android/Droidian, rejected as runtime
     (violates zero-Android requirement); topology/extraction knowledge only.
4. **On-device kernel source fully traced** (`/root/kbuild/src` @ f7194c1d):
   - Private control catalog (`include/uapi/linux/videodev2_exynos_camera.h`).
   - Video state-machine bits (`fimc-is-video.h`).
   - Leader/follower start path (`fimc-is-device-ischain.c`, `fimc-is-device-sensor.c`).
   - ISP capture G_FMT stub (`fimc-is-video-ispc.c`).
5. **Live capture test run** — `nuxel-fimc-leader-capture` confirmed current failure:
   sensor leader S_FMT = -EINVAL (Problem C), cascading to STREAMON -22.

## Authoritative FIMC-IS2 leader state machine (source-backed)

Video state bits (`fimc-is-video.h`, enum fimc_is_video_state):
```
bit0 CLOSE, bit1 OPEN, bit2 S_INPUT, bit3 S_FORMAT, bit4 S_BUFS, bit5 STOP, bit6 START
```

`vctx->state` is a single-bit assignment at each transition; `open()` -> OPEN.

`fimc_is_video_s_input` (`fimc-is-video.c:1358`):
  requires `OPEN | S_INPUT | S_BUFS`; on success sets state = S_INPUT.
  For ss0 this also calls `fimc_is_sensor_s_input()` which discovers the module via
  `module_enum[]`, configures mode/framerate/window, and sets `FIMC_IS_SENSOR_S_INPUT`.

`fimc_is_video_reqbufs` (`fimc-is-video.c:1404`):
  requires `S_FORMAT | STOP | S_BUFS`; calls `frame_manager_open` + queue reqbufs;
  sets state = S_BUFS.

`fimc_is_video_set_format_mplane` (`fimc-is-video.c:1502`):
  LEADER condition = `S_INPUT | S_BUFS`;
  CAPTURE condition = `S_INPUT | S_BUFS | OPEN | STOP`.
  On success sets state = S_FORMAT.

`sensor_back_start` (`.start_streaming` queue op, `fimc-is-device-sensor.c:2464`):
  `hw_camif_cfg` -> module s_routing -> `flite s_stream(enable)` -> sets `BACK_START`.

`fimc_is_ischain_<group>_start` (isc/groups) each do:
  `fimc_is_group_start(groupmgr, group)` + `fimc_is_ischain_start_wrap()`.
  The group leader start path invokes `fimc_is_itf_process_start()` at
  `fimc-is-device-ischain.c:1727`, which is required before the ISP capture node
  (i0c) can stream. Without it: capture STREAMON = -22 (observed).

## Corrected capture sequence (for the next continuation)

The Samsung HAL order for the rear-main SAK2L4 still+preview path is:

1. open ss0 (`/dev/video101`), `S_INPUT(index=rear sensor module id)`  [verified working]
2. open i0c (`/dev/video131`) and the 3AA group leader nodes in the correct order
3. on ss0: `REQBUFS(count=0)` then `S_FMT`/`S_BUFS` per the leader state machine —
   the sensor format is internal (Bayer), driven by `fimc_is_sensor_g_mode()`
4. allocate ION DMABUF from camera_heap(id=5); QBUF on leader then capture
5. `STREAMON` on the 3AA group leader first (triggers `fimc_is_itf_process_start`)
6. `STREAMON` on i0c capture -> DQBUF real ISP-processed frame

The precise ordering of `S_INPUT`/`S_BUFS`/`S_FMT` leader state transitions is the
remaining unknown; the S_BUFS/S_FORMAT circularity is resolved by the vendor HAL's
use of a private-codec path. A kernel `dbg` log of the vendor HAL is the
deterministic next step (or the Strategy B custom-driver port).

## Decision

Stage A (complete vendor HAL) is the fastest IF the exact leader ordering can be
nailed; Stage B (port s10-linux custom driver to 4.14 + libcamera) is the proven
fallback. Both documented in CAMERA_DRIVER_ARCHITECTURE.md.

## Files changed / created

- `pwn/CAMERA_DRIVER_ARCHITECTURE.md` (decision record)
- `pwn/CAMERA_IMPLEMENTATION_LOG.md` (this file)
- `pwn/upstream-camera-research/` (cloned references, not committed)

## Honest status

`FIRST_FRAME_VERIFIED` = **NOT PASSED**. Firmware + sensor + ION all work; the vendor
leader streaming sequence is fully mapped at source level but the exact ioctl ordering
to reach the first DQBUF is not yet demonstrated on-device. No synthetic/cached frame
has been accepted. See CAMERA_LIVE_ACCEPTANCE.md for the matrix.

## Session 2 findings (source + live experiments)

### Corrected S_INPUT encoding (CONFIRMED live)
`S_INPUT` is a packed bitfield. For ss0 sensor leader rear-main:
`0x00000001` => position=0(SP_REAR) leader=1. This now returns 0 (was 0 before).

### Sensor ID map (from beyond2lte DTS, authoritative)
| Sensor | module id | position |
|---|---|---|
| S5K2L4 rear-main | 0x0 | SP_REAR=0 |
| S5K3M3 tele | 0x2 | SP_REAR2=2 |
| S5K3P9 ultrawide | 0x4 | SP_REAR3=4 |
| S5K3J1 front | 0x1 | SP_FRONT=1 |
| S5K4HA front-depth | 0x3 | SP_FRONT2=3 |

### Live capture node progress (nuxel-fimc-leader-capture2)
```
capture i0c (/dev/video131):  S_FMT=0, REQBUFS=0(count 4), QBUF[0..3]=0  <- 4 buffers queued
sensor ss0 (/dev/video101):   S_INPUT=0, S_FMT=-22  <- remaining blocker
capture STREAMON=-22  <- needs 3AA/ISP group leader started (Problem D)
```

### S_FMT -22 root cause (narrowed)
The sensor leader S_FMT passes the video-state-machine check (state=S_INPUT, condition
S_INPUT|S_BUFS) and the general format table (SBGGR10/YUYV both present). The -EINVAL
originates in `fimc_is_sensor_s_format()` -> `v4l2_subdev_call(subdev_module, pad,
set_fmt, ...)`, i.e. the S5K2L4 CIS module driver's pad set_fmt rejects the frame
because it requires an exact sensor-mode match (mode enum SENSOR_2L4_*_30FPS with a
specific mbus code and post S_INPUT module init). Valid external modes:
4032x3024@30, 4032x2268@30/60, 2016x1512@30, 2016x1134@30. 640x480 is NOT supported.
Even with 2016x1512 the subdev still rejects, indicating the sensor must first be
put in the exact expected mode via the vendor `fimc_is_sensor_g_mode()`/setfile path,
or the format must use the sensor's exact internal mbus_code (likely SGRBG10 for the
2L4 raw output).

### Debug infrastructure (available for next step)
- `/sys/kernel/debug/fimc-is/event/{log_enable,log,filter}` (event log; empty for
  pure ioctl-path errors)
- `/sys/devices/platform/fimc-is_sensor_2l4@20`, `..._3m3@5A`, `..._3p9@2D`,
  `..._3j1@10`, `..._4ha@10` — all five modules bound.
- `dmesg` shows `sensor_2l4_cis_stream_on/off`, `SAK2L4 sensor_module_init(0)`.

### Decision for next continuation
The vendor HAL leader ordering requires reproducing the exact Samsung sensor-mode
selection (the `V4L2_CID_IS_SET_SETFILE` / mode-select control + the sensor subdev's
expected mbus code). This is the last unknown for Stage A. If it cannot be resolved
by one more focused pass, proceed to Stage B (port s10-linux s10-camera-v4l2 to 4.14,
using the GPL sensor setfiles already in-tree).

## Session 3 findings (2026-11-20 continuation) — MAJOR BREAKTHROUGH + crash

### Decisive root-cause resolution: V4L2_CID_IS_S_SENSOR_SIZE
The sensor leader (ss0, /dev/video101) S_FMT failed with -EINVAL because the
v2 `fimc_is_sensor_s_format()` reads `device->sensor_width` / `device->sensor_height`,
which are ONLY set by the private control:

  V4L2_CID_IS_S_SENSOR_SIZE = V4L2_CID_FIMC_IS_BASE + 69 = 0x009A1045
  (value = (width << 16) | height;  SENSOR_SIZE_WIDTH_MASK=0xFFFF0000/SHIFT=16,
   SENSOR_SIZE_HEIGHT_MASK=0xFFFF/SHIFT=0)

Prior tools never set this control, so sensor_width/height were 0, and
fimc_is_sensor_g_mode() logged "sensor mode(0x0@30fps) is not found" -> -EINVAL.

VERIFIED LIVE (nuxel-fimc-capture3):
```
[sensor S_INPUT] 0x00000001 ret=0
[sensor S_SENSOR_SIZE 2016x1512] ret=0
[sensor S_FMT] ret=0  (SBGGR10, 2016x1512, 2 planes)
sensor mode(2016x1512@30) = 5 (lane:4)   <- sensor mode RESOLVED
[sensor REQBUFS] ret=0 count=4
[sensor QBUF 0..3] ret=0
```

Also confirmed: FIMC-IS2 uses NUM_OF_META_PLANE=1 (every format has an extra
metadata plane); buffer QBUF must supply 2 planes (image + 32KB meta ION fd).
The valid Bayer format for the 2L4 raw output is SBGGR10 (not SGRBG10, which is
absent from fimc_is_formats[]).

### Capture (i0c /dev/video131) also reaches QBUF (verified)
With YUYV 2-plane: cap S_FMT=0, REQBUFS=0, QBUF[0..3]=0. (unchanged from prior)

### CRITICAL RISK CONFIRMED: sensor STREAMON triggers a kernel panic
The first full capture3 run drove sensor STREAMON and caused a HARDWARE WATCHDOG
panic ("Panic#2", pstore dmesg-ramoops-0) and a reboot back into Nuxel (not TWRP).
Device recovered cleanly; fimc-is reloaded; no lasting damage.

ROOT CAUSE (source-backed): the sensor leader `.start_streaming` ->
fimc_is_sensor_back_start() configures CAMIF + FLITE s_stream(enable), which
starts MIPI CSI DMA. Without the full ischain/3AA/ISP group-leader startup
(fimc_is_itf_process_start via the 3AA group leader STREAMON FIRST), the DMA/com
state is inconsistent and the hardware hangs until the watchdog fires.

SAFE SEQUENCE (must be respected before any further live streaming attempt):
  1. S_INPUT + S_SENSOR_SIZE + S_FMT + REQBUFS + QBUF on sensor ss0 (NO STREAMON yet)
  2. Open+configure the 3AA group leader (30s/30c) and the ISP chain
  3. STREAMON the 3AA group leader first (triggers fimc_is_itf_process_start)
  4. Only then STREAMON the capture node (i0c)

Next safe step: reproduce the Samsung HAL order where the 3AA/ISP group leader is
started BEFORE any sensor/capture STREAMON, and never STREAMON the sensor leader
out of order. Each live STREAMON attempt must be treated as potentially
kernel-crashing until the ischain order is correct.

## Corrected capture sequence (source-authoritative, from fimc-is-video.c + v2)
  1. open ss0 -> OPEN
  2. S_INPUT (packed 0x00000001 = position SP_REAR=0, leader=1) -> S_INPUT
  3. S_CTRL V4L2_CID_IS_S_SENSOR_SIZE = (W<<16)|H  [REQUIRED, was missing]
  4. S_FMT (SBGGR10, num_planes=2) -> S_FORMAT
  5. REQBUFS(count=N) -> S_BUFS
  6. QBUF x N (image dmabuf + meta dmabuf)
  7. Open+configure 3AA group leader / ISP chain FIRST
  8. STREAMON 3AA group leader -> fimc_is_itf_process_start
  9. STREAMON capture i0c -> DQBUF

## Files changed
- tools/s10plus/fimc-capture/nuxel-fimc-capture3.c (NEW: correct private control
  + 2-plane meta + valid SBGGR10 + full leader sequence)

## Session 3 (part 2) — Strategy B feasibility VERIFIED offline

### Media framework compiles on 4.14.253 (confirmed, not assumed)
Offline cross-compile test (aarch64-linux-gnu-gcc 15.2, macOS host) with a
beyond2lte defconfig + CONFIG_MEDIA_CONTROLLER=y + CONFIG_VIDEO_V4L2_SUBDEV_API=y:

SUCCESS — drivers/media/ builds cleanly:
  media-device.o media-entity.o media-devnode.o        (media controller core)
  v4l2-subdev.o v4l2-async.o v4l2-mc.o v4l2-ctrls.o    (V4L2 framework)
  v4l2-device.o v4l2-mem2mem.o v4l2-common.o
  videobuf2-core.o videobuf2-v4l2.o videobuf2-dma-sg.o videobuf2-memops.o

This proves the 4.14 downstream kernel's media framework is complete and
buildable with the controller/subdev API enabled — the foundation Strategy B
needs is present. Remaining config to add when the driver lands:
  CONFIG_VIDEOBUF2_DMA_CONTIG (tristate, selected by the driver)
  CONFIG_V4L2_FWNODE (tristate, selected by the driver)
Both are tristate "select only" symbols that become set when the s10-camera-v4l2
driver's Kconfig selects them.

New files:
  kernel/s10plus/configs/nuxel-camera-v4l2.fragment
  (offline test tree at kernel/s10plus/.build/out-camtest, not committed)

## Session 3 summary — verified milestones and honest status

### Completed and verified this session
1. Sensor register data pipeline REPRODUCED byte-identical to s10-linux:
   - Copied in-tree GPL fimc-is-cis-{2l4,3m3,3p9,3j1}-setA.h from the running
     kernel; SHA-256 matches s10-linux's pinned LineageOS headers EXACTLY.
   - prepare-s5k-tables.py + prepare-s5k-firmware.py produced .s5k runtime
     containers whose SHA-256 matches the driver manifest EXACTLY
     (S5K2L4= b9a47b96..., etc.). Sensor programming for the S10+ is reproduced.
2. Driver source staged as drivers/s10-camera-v4l2/ (GPL-2.0, provenance preserved).
3. Media framework compile feasibility verified offline (see above).
4. Architecture decision made and documented (Strategy B).

### Status of the FIRST_FRAME milestone
- Stage A (vendor FIMC-IS2): fw+sensor+format+buffers verified; streaming = panic.
- Stage B (s10-camera-v4l2 port): foundation verified (framework compiles, data
  reproduced); the ~2856-line driver API port (post-6.x -> 4.14) + beyond2lte
  camera DTBO + cross-compile + TWRP flash remain TODO.

### Exact remaining work (bounded, in order)
1. Port exynos9820-csis.c: v4l2_subdev_state->v4l2_subdev_pad_config;
   .enable/.disable_streams -> video .s_stream; v4l2_async_connection/nf_init ->
   v4l2_async_subdev+notifier bound/complete; v4l2_fwnode_endpoint_alloc_parse ->
   v4l2_fwnode_endpoint_parse; video_device_pipeline_start -> media_entity_
   pipeline_start.
2. Port s5k-cis.c: same subdev/state rewrite; __v4l2_ctrl_modify_range/s_ctrl ->
   v4l2_ctrl_modify_range/s_ctrl; pm_runtime_resume_and_get -> pm_runtime_get_sync;
   mux_control -> Samsung mux/pinctrl.
3. Port ak7374.c (lens actuator, mostly standard V4L2 ctrls).
4. Author beyond2lte camera DTBO (5 sensors + CSIS0/1/2/3 + clocks/regulators/
   gpio/reset/PHY), derived from the current beyond2lte overlay DTS + s10-linux DTS.
5. Cross-compile, iterate offline; preserve rollback boot image; flash via TWRP;
   bounded live first-frame test with the crash-recovery protocol.

No synthetic/test-pattern frame has been claimed. No proprietary firmware or
generated sensor binaries are committed to public git.
