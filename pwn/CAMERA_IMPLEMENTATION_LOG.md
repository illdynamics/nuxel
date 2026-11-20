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
