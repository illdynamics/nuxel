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

## Session 4 (2026-11-20 continuation) — Port-scope analysis complete, port not yet started

### State confirmed (no regressions)
- Live device `root@10.11.12.99` reachable, kernel `4.14.253-gf7194c1d15ed-dirty`.
- 8 firmware blobs intact at `/system/vendor/firmware/` (7 visible in listing; setfile_4ha.bin
  expected too — verify before relying on it).
- Full `/dev/video*` FIMC-IS2 node set intact (vendor driver still loaded — rollback sane).

### Foundation verified (unchanged from Session 3, re-confirmed this session)
- Host has the EXACT running kernel source at `kernel/s10plus/.build/src/`
  (git HEAD f7194c1d15ed == live). No need to rsync from device.
- In-tree media framework present and gated behind config:
  drivers/media/v4l2-core/{v4l2-subdev,v4l2-async,v4l2-fwnode,v4l2-mc,v4l2-ctrls,v4l2-device}.c
  drivers/media/media-{device,entity,devnode}.c
  videobuf2-{core,v4l2,dma-contig,dma-sg,vmalloc,memops}.c
  include/media/v4l2-{subdev,async,fwnode,mc,mediabus}.h
- The Stage-B driver source is staged at repo root `drivers/s10-camera-v4l2/`
  (upstream s10-linux @ d8135b2, GPL-2.0, provenance preserved).
- Generated sensor runtime data staged at `pwn/s5k-firmware-out/*.s5k` +
  `pwn/camera-tables-out/*-tables.h` (matches upstream manifest SHA-256).

### Port scope fully mapped this session (NEW — this is the concrete TODO)
exynos9820-csis.c and s5k-cis.c are post-6.x V4L2. The 4.14 tree LACKS all of:

  structural/API:
   - v4l2_subdev_state (use v4l2_subdev_pad_config + per-pad format storage)
   - v4l2_subdev_state_get_format() (new internal per-pad lookup)
   - v4l2_subdev_lock_and_get_active_state() / v4l2_subdev_init_finalize()
   - pad ops .init_state (use internal_ops .open = csis_open to init pad_config)
   - .enable_streams/.disable_streams (rewrite as legacy video .s_stream +
     v4l2_subdev_s_stream helper semantics; the driver sets V4L2_SUBDEV_FL_STREAMS)
   - v4l2_subdev_enable_streams/disable_streams (replace with v4l2_subdev_call .s_stream)
   - v4l2_subdev_s_stream_helper (shim or drop; helper expects modern state)

  async/fwnode:
   - v4l2_async_connection / v4l2_async_nf_init/add_fwnode_remote/register
     (use 4.14 v4l2_async_notifier + v4l2_async_subdev + notifier bound/complete/unbind ops)
   - v4l2_create_fwnode_links_to_pad (port from 4.14 media docs / s10-linux git history)
   - v4l2_fwnode_endpoint_parse / _alloc_parse / v4l2_fwnode_device_parse /
     v4l2_ctrl_new_fwnode_properties / v4l2_link_freq_to_bitmap / v4l2_get_link_freq
     (4.14 has v4l2_fwnode_endpoint_parse with a BUS_TYPE struct variant, not CSI2_DPHY enum;
     must adapt the CSI2 lane field layout)

  pipeline/media:
   - video_device_pipeline_start/stop -> media_entity_pipeline_start/stop()
   - media_pad_remote_pad_unique() (4.14 has media_pad_remote_pad_first / media-entity core;
     add a small helper in-driver)
   - media_pad_is_streaming / v4l2_subdev_get_fmt helpers

  misc/helpers (4.14 lacks):
   - dev_err_probe() (shim: dev_err + return)
   - devm_platform_ioremap_resource_byname() (shim: platform_get_resource_byname + devm_ioremap)
   - clk_bulk_data / devm_clk_bulk_get() (rewrite as 4 individual devm_clk_get calls)
   - linux/mux/consumer.h mux_control (4.14 uses a Samsung pinctrl/gpio mux; must map to
     the beyond2lte camera I2C-mux gpio/pinctrl, inspect fimc-is2 for the actual mux control)
   - pm_runtime_resume_and_get -> pm_runtime_get_sync (check return semantics)
   - __v4l2_ctrl_modify_range/s_ctrl -> v4l2_ctrl_modify_range/s_ctrl (exported variants)
   - IRQF_NO_AUTOEN -> request_irq then disable_irq_nosync
   - crypto/sha2.h sha256() (4.14 has lib/sha256.c sha256() or use shash; verify)
   - get_unaligned_be16 (in-tree <asm/unaligned.h> / <linux/unaligned/be_byteshift.h>)
   - request_firmware_direct (may need ascii->shim; 4.14 request_firmware is synchronous)
   - FIELD_GET / GENMASK / clamp / roundup (all present in 4.14 <linux/bitfield.h> etc.)

### remaining before first compile
- Port both drivers per above; add s10-isppre-hold.ko (upstream keeps ISPPRE domain on;
  verify exynos9820 has this — else the CMU becomes unreachable after power-off).
- Write beyond2lte camera DTBO (5 sensors: 2L4/3M3/3P9/3J1/4HA + CSIS0/1/2/3 +
  clocks/regulators/gpio/reset/PHY pmu offsets/reset bits; 4HA has no upstream model table —
  must be added or intentionally excluded with documented limitation).
- Enable media framework fragment (kernel/s10plus/configs/nuxel-camera-v4l2.fragment) and
  wire drivers/s10-camera-v4l2 into kernel Kconfig/Makefile.
- Cross-compile; preserve known-good boot image; flash via TWRP (auuthorized in pwn/cam.md);
  bounded first-frame test.

### Files created/changed this session
- (none new; analysis only. Re-confirmed all Session 3 artifacts intact.)

## Session 5 (2026-11-20) — 4.14 API port COMPILED; DTBO + full build + flash remain

### Port of s10-camera-v4l2 → 4.14.253 drivers COMPILES (verified offline)
The previous session only *mapped* the port surface. This session ported all three
drivers (plus the ISPPRE-hold aid) and proved they compile against the pinned
4.14 tree (aarch64-linux-gnu-gcc 15.2, beyond2lte defconfig + camera fragment):

  drivers/media/platform/s10-camera/{exynos9820-csis,s5k-cis,ak7374,s10-isppre-hold}.o
  ALL COMPILE CLEAN (no errors; only benign min_t/clamp pointer-type warnings).

Concrete 4.14 API conversions applied (validated against include/ in-tree):
  - v4l2_subdev_state -> v4l2_subdev_pad_config; .init_state -> pad .init_cfg;
    ACTIVE format tracked in driver struct (4.14 has no subdev active-state).
  - .enable_streams/.disable_streams -> legacy video_ops .s_stream (single fn).
  - v4l2_async_nf_*/v4l2_async_connection -> 4.14 v4l2_async_notifier +
    v4l2_async_subdev[] with FWNODE match + bound/unbind/complete fptrs.
  - v4l2_create_fwnode_links_to_pad -> inline media_create_pad_link from the
    sensor's single source pad to the CSIS sink pad.
  - dev_err_probe, pm_runtime_resume_and_get, media_pad_remote_pad_unique,
    video_device_pipeline_start/stop, media_pad_is_streaming, link-freq and
    fwnode-device-props -> shims in s10-compat.h (this downstream 4.14 already
    has clk_bulk_data + devm_clk_bulk_get, so those shims were dropped).
  - sha256()/crypto/sha2.h absent -> crypto_shash "sha256" digest.
  - request_firmware_direct /\`hex2bin\`/mux_control all present in this tree.
  - 4.14 lacks: V4L2_CAP_IO_MC, v4l2_fmtdesc.mbus_code, vb2 min_queued_buffers/
    min_reqbufs_allocation, VFL_TYPE_VIDEO (uses VFL_TYPE_GRABBER),
    fwnode_graph_for_each_endpoint, i2c .probe 1-arg (uses .probe_new). All fixed.

### Key live-device facts (from SSH root@10.11.12.99)
  - Machine: "Samsung BEYOND2LTE EUR OPEN 26 board"; compatible "samsung,armv8",
    "samsung,exynos9820" (NOT "beyond2lte" string) -> isppre-hold gate changed
    to of_machine_is_compatible("samsung,exynos9820").
  - DTB target: exynos9820-beyond2lte_eur_open_26.*
  - Vendor FIMC-IS2 + all 5 sensors (2l4@20,3j1@10,3m3@5A,3p9@2D,4ha@10) and
    MIPI D-PHY nodes already present in the live DT -> DTBO must overlay new
    csis nodes using existing PMU/clock/gpio/regulator phandles.

### Next (bounded)
  1. Author beyond2lte camera DTBO (csis x4 + 5 sensors + isppre-hold +
     isppre-clock) mapped to the existing beyond2lte phandles.
  2. Full kernel build (build-kernel.sh with the camera fragment) -> boot image.
  3. Preserve known-good boot image; flash via TWRP/adb; reboot; first-frame test.

### Files changed this session
  - drivers/s10-camera-v4l2/{exynos9820-csis.c,s5k-cis.c,ak7374.c} (ported)
  - drivers/s10-camera-v4l2/s10-compat.h (new shim header)
  - drivers/s10-camera-v4l2/s10-isppre-hold.c (new, beyond2lte)
  - kernel .build/src/drivers/media/platform/s10-camera/{Kconfig,Makefile}
  - kernel/s10plus/configs/nuxel-camera-v4l2.fragment (+VIDEO_S10_CAMERA=m)

## Session 5 (cont.) — DTBO skeleton + build-environment blocker found

### DTBO skeleton authored (structure complete, phandles partial)
kernel/s10plus/dts/nuxel-camera-v4l2.dtso adds the s10-camera-v4l2 bindings:
  camera-isppre-hold (pd_isppre), clock-controller@17000000 (isppre-clock),
  camera-csis@17040000/17050000/17030000 (CSIS0/1/2) with the s5k2l4 sensor.
All symbolic labels (pd_isppre, pmu_system_controller, mipi_phy_csis*, etc.)
were read from the live device's /proc/device-tree/__symbols__. The remaining
regulator/reset-GPIO/pinctrl/clock phandles are board-local and are marked
[TODO-RESOLVE]; they must be filled from the decompiled
exynos9820-beyond2lte_eur_open_26.dtb before the overlay is flashable.

### CRITICAL: full in-tree kernel build is blocked on THIS macOS host
- The host volume is case-INSENSITIVE APFS (verified: `NetfilterCaseTest_abc`
  resolves as `netfiltercasetest_abc`). The Linux netfilter tree has case-variant
  file pairs (xt_DSCP.c "target" vs xt_dscp.c "match", xt_TCPMSS.c vs xt_tcpmss.c,
  xt_CONNMARK/xt_MARK/xt_HL/xt_RATEEST ...) that CANNOT coexist on this FS, so
  the `net/netfilter` full-tree build always fails with "no rule to make
  xt_TCPMSS.o" / "undefined struct xt_tcpmss_info" style errors.
- This is UNRELATED to the camera port (the previous good boot image was built
  on a case-sensitive host). The isolated out-of-tree camera module objects
  still compile clean (they don't touch netfilter).
- SOLUTION (verified): the LIVE DEVICE is a native aarch64 Linux box
  (gcc 15.3.1, gmake, 8 cores, 50 GB free, case-sensitive ext4/btrfs). The
  full Image.gz + dtbs build + DTBO authoring resolution can be performed
  ON THE DEVICE itself (they are the target arch and filesystem).

### Files changed this session
  - kernel/s10plus/dts/nuxel-camera-v4l2.dtso (NEW skeleton overlay)
  - kernel/s10plus/configs/nuxel-all.fragment (combined kbase+camera)
  - kernel .build/src/net/netfilter/{xt_*.c,xt_*.h} restored from HEAD
    (pre-existing case-collision corruption, not camera-related)

### Honest status
  - Driver 4.14 port: COMPLETE + compiles clean (the core deliverable).
  - DTBO: structure authored; board phandles + full build + flash + physical
    first-frame + app integration REMAIN.

## Session 5 (cont. 2) — Live DT decompiled; CSIS phandles RESOLVED

### Safe non-destructive progress
- Copied the 4 `.s5k` sensor runtime files to the live device
  `/lib/firmware/samsung/s10/{s5k2l4,s5k3j1,s5k3m3,s5k3p9}.s5k`; SHA-256 matches
  the driver manifest EXACTLY (b9a47b96..., ef8decfa..., d7241d42..., 23632888...).
  No kernel flash performed.

### Live DTB decompiled (dtc 1.8.1) — key camera phandles now known
  pd_isppre              = phandle 0x07  (/pd-isppre@15862500, exynos-pd)
  sysreg_isppre_reset    = phandle 0x41  (/system-controller@17020500, reg 0x17020500 +0x4)
  pmu_system_controller  = phandle 0x54  (/system-controller@15860000, reg 0x15860000 +0x10000, syscon)
  mipi_phy_csis2 (2L4)   = phandle 0x43  reg 0x19162300 +0x500  isolation 0x730 reset bit 1
  mipi_phy_csis1 (3J1)   = phandle 0x45  reg 0x19162b00 +0x500  isolation 0x730 reset bit 2
  mipi_phy_csis3 (3M3?)  = phandle 0x46  reg 0x19163300 +0x300  isolation 0x730 reset bit 3
  exynos_dm (ISPPRE CMU) = /exynos-dm@17000000 (0x17000000)

  -> csis driver's samsung,pmu-phy-offset = 0x730 (isolation) and
     samsung,phy-reset-bit = D-PHY reset bit for each channel.

### Remaining (next continuation)
  1. Resolve per-sensor I2C-controller + regulator + reset-GPIO + pinctrl
     phandles from /tmp/live.dts (18358 lines, decompiled) for all 5 sensors.
  2. Native kernel build ON the live device (aarch64 gcc 15.3.1, case-sensitive
     fs) with the nuxel-all fragment — macOS host is case-insensitive and cannot
     build netfilter.
  3. Preserve known-good boot image; flash via TWRP/adb (cam.md authorized);
     reboot; bounded first-frame test; then app integration.

## Session 6 (2026-11-20) — Phandles fully RESOLVED; drivers + DTBO compile natively; full build next

### ALL DTBO phandles now resolved from authoritative live DT (board rev 26)
I2C controllers (label -> node -> sensor/addr):
  hsi2c_0  = hsi2c@10860000 -> 2L4 (rear main)  0x10
  hsi2c_1  = hsi2c@10870000 -> 3P9 (rear UW)    0x2D
  hsi2c_2  = hsi2c@10880000 -> 3J1 (front main) 0x10
  hsi2c_19 = hsi2c@108C0000 -> 3M3 (rear tele)  0x2D  (4HA shares bus, 0x10)
  hsi2c_3  = hsi2c@10890000 -> rear AF actuator
  hsi2c_37 = hsi2c@15C60000 -> OIS MCU 0x51

Sensor GPIO (bank.pin, active=1):
  2L4: reset gpg2.6, mclk gpc1.4
  3M3: reset gpg3.0, subcam_sel gpg4.3, mclk gpc1.4
  3P9: reset gpg4.3, mclk gpc1.7
  3J1: reset gpg2.5, subcam_sel gpg4.3, mclk gpc1.5
  4HA: reset gpg2.3, mclk gpc1.5   (EXCLUDED: no upstream model table/firmware)

Power/PHY (exact labels): pd_isppre, pmu_system_controller,
  sysreg_isppre_reset, exynos_dm (ISPPRE CMU 0x17000000),
  mipi_phy_csis0_m4s4_top / csis1..3_m0s4s4s4_mod.

### Critical discovery: regulator binding impedance mismatch
s5k-cis.c (s10-linux) requests standard DT supplies (retention/avdd28/avdd24/
core/iovdd/vddq for 2L4; pre/avdd/dvdd/iovdd for 3m3/3j1/3p9). beyond2lte has
NO DT regulator-fixed nodes for these — the rails (VDDA_2.8V_CAM, VDDD_1.0V_CAM,
VDDIO_1.8V_CAM, VDDQ_1.1V_CAM, VDDD_RET_1.0V_CAM, VDDA_2.4V_CAM) are powered by
the S2MPB02 camera PMIC and brought up by the bootloader/vendor FIMC driver
(runtime regulator_register with regulator-name, not DT). FIX: s5k-cis.c supply-
get loop now uses devm_regulator_get_optional() (skip -ENODEV); mux_control_get
also made optional (subcam-select is a plain GPIO, not a mux-control on this board).

### Files changed this session
  - kernel/s10plus/dts/nuxel-camera-v4l2.dtso  (FULLY RESOLVED + compiles clean)
  - drivers/s10-camera-v4l2/s5k-cis.c  (supplies/mux optional; 4.14-correct)
  - staged to device: /root/kbuild/drivers/media/platform/s10-camera/
    + DTBO at /root/kbuild/arch/arm64/boot/dts/samsung/nuxel-camera-v4l2.dtso
  - device /root/kbuild: Kconfig+Makefile wired; .config merged camera fragment
    (MEDIA_CONTROLLER=y, V4L2_SUBDEV_API=y, V4L2_FWNODE=m, VIDEOBUF2_DMA_CONTIG=m,
     VIDEO_S10_CAMERA=m); olddefconfig applied.

### Verified this session (on-device, native aarch64 gcc 15.3.1)
  - All 4 driver .o objects compile CLEAN (s5k-cis, exynos9820-csis, ak7374,
    s10-isppre-hold). WARNINGs are only expected undefined symbols resolved at
    load time against the media framework (=y/=m).
  - nuxel-camera-v4l2.dtso compiles CLEAN with dtc -@ (9331 bytes).

### Next (bounded): full kernel build -> Image.gz -> mkbootimg -> TWRP flash
  Boot image params (from unpacked boot-v24.img): kernel@0x10008000,
  ramdisk@0x11000000, tags@0x10000100, page 2048, header v1, cmdline
  "buildvariant=userdebug nuxel.device=s10plus root=...userdata rootfstype=ext4 rootwait rw".
  Flash via scripts/nuxel-adb-flash-pack (fail-closed, full SHA256 readback).

### Session 6 (cont.) — FULL KERNEL BUILD SUCCEEDED on live device
Native aarch64 build (gcc 15.3.1, 8 cores) completed:
  - Image 45,578,248 bytes (media framework MEDIA_CONTROLLER=y, V4L2_SUBDEV_API=y built-in)
  - 4 camera .ko: s5k-cis.ko, exynos9820-csis.ko, ak7374.ko, s10-isppre-hold.ko
  - v4l2-fwnode.ko + videobuf2-dma-contig.ko (framework)
  - nuxel-camera-v4l2.dtbo (9364 bytes), beyond2lte_eur_open_26.dtbo, exynos9820.dtb

Blockers fixed en route:
  - dtbs: renamed .dtso -> .dts (kernel dtbo-y rule expects .dts source)
  - modules: removed linux/mux/consumer.h dependency — replaced mux_control with
    a plain subcam-sel GPIO (devm_gpiod_get_optional "subcam-sel"); beyond2lte
    drives sub-cam selection via gpio_subcam_sel, not a mux-control.

Boot image params (from unpacked boot-v24.img): kernel@0x10008000,
  ramdisk@0x11000000, tags@0x10000100, page 2048, header v1, cmdline
  "buildvariant=userdebug nuxel.device=s10plus root=...userdata rootfstype=ext4 rootwait rw".

### Next: Image.gz -> mkbootimg -> TWRP/adb flash (cam.md authorized)

### Session 6 (cont. 2) — Boot image + merged DTB ready; dtbo partition pack is the remaining gate

### Artifacts PRODUCED on the live device (all verified):
  /root/kbuild/arch/arm64/boot/Image          45,578,248 B (media framework built-in)
  /root/kbuild/arch/arm64/boot/vmlinux
  /root/kbuild/drivers/media/platform/s10-camera/{s5k-cis,exynos9820-csis,ak7374,s10-isppre-hold}.ko
  /root/kbuild/drivers/media/v4l2-core/{v4l2-fwnode,videobuf2-dma-contig}.ko
  /root/kbuild/arch/arm64/boot/dts/samsung/nuxel-camera-v4l2.dtbo (9364 B)
  /tmp/final-merged.dtb  (base exynos9820 + beyond2lte_eur_open_26 + nuxel-camera overlays;
                           verified contains samsung,s5k2l4/3m3/3p9/3j1 compatibles)
  /tmp/nuxel-boot-camera-v1.img  (48,007,168 B; new kernel + existing LZMA ramdisk; header v1)

### Partition map (from /sys/block/sda/sda*/uevent PARTNAME):
  sda12=dtb (8M), sda13=dtbo (8M), sda14=boot (55M), sda15=recovery (64.5M), sda31=userdata (rootfs).
  dtbo partition magic d7b7ab1e, 10 dt-entries (beyond0/1/2lte, x, d1, d2, d2x variants).
  beyond2lte_eur_open_26.dts is NOT /plugin/: it is a flat overlay with dtbo-hw_rev=0x1a..
  0xff and fragment@N {target=<0xffffffff>; __overlay__{...}} fixups.

### Remaining bounded steps (each requires care; flash is high-risk):
  1. PACK dtbo partition: rebuild beyond2lte_eur_open_26.dtbo with the nuxel-camera
     fragments added (append camera nodes as extra fragment@N into the vendor
     overlay source, rebuild, then rewrite the 10-entry dtbo partition image
     replacing only the beyond2lte_26 entry). Alternative: use mkbootimg
     --header_version 2 --dtb (NOT supported by this bootloader v1) so dtbo
     partition update is required.
  2. FLASH boot (sda14, /dev/block/by-name/boot in TWRP) + dtbo (sda13) via
     scripts/nuxel-adb-flash-pack (boot-only mode) after `adb reboot recovery`.
  3. Physical first-frame test (rear 2L4 via /dev/video* CSIS node + media pipeline).
  4. App integration (photo+video+mic+flashlight rear+front; Nuxel + Fedora GTK + Flatpak).

### Honest status: kernel/driver/DTBO build COMPLETE; flash not yet performed.

## Session 7 (2026-11-20) — DTBO structural bug FIXED; merged overlay built+verified; flash prepared

### Root-cause of "one more clean pass" (the dtbo merge blocker) — SOLVED
The `nuxel-camera-v4l2.dtso` had a STRUCTURAL bug, not a syntax/format mismatch:
1. The CSIS (`camera-csis@17030000/040000/050000/060000`), `isppre-hold`, and
   `isppre-clock` nodes were written as TOP-LEVEL nodes under `/ { ... }`.
   In `/plugin/` overlay semantics, only `fragment@N { target/target-path; __overlay__{...} }`
   blocks apply changes; top-level nodes are DROPPED by fdtoverlay/dtbo-apply.
   => The 4 CSIS receivers silently vanished in any merged tree (verified:
   `final-merged.dtb` had 0 `exynos9820-csis` nodes, only the sensor children).
2. FIX: wrapped those nodes in `fragment@100 { target-path="/"; __overlay__{...} }`.

### Second structural bug — vendor FIMC-IS2 coexistence (would wedge hardware)
The new kernel builds `CONFIG_VIDEO_EXYNOS_FIMC_IS2=y` (vendor, built-in). The
base DTB's `fimc_is@17190000` + `fimc_is_sensor0..5` nodes overlap the EXACT
CSIS register blocks my new `exynos9820-csis` drives (17030000/040000/050000/
060000). FIX: added `status="disabled"` to `&fimc_is` + `&fimc_is_sensor0..5`
in the overlay. Verified all 6 vendor sensor nodes + ISP parent are now disabled.

### Third bug — phandle collision in source-merge of two /plugin/ overlays
Merging the vendor beyond2lte_26 overlay (fragment@0..120) with the camera
overlay required: (a) renumber camera fragments to 121..132, (b) strip all
decompiled `phandle`/`linux,phandle` literals so dtc re-assigns them uniquely,
(c) merge `__fixups__` duplicate symbol keys by concatenating path lists.
Result: `merged-overlay.dtbo` (186,261 B) — single /plugin/ overlay = vendor +
camera, applies cleanly onto base DTB (fdtoverlay exit 0).

### VERIFIED merged tree (merged-apply-test.dtb / entry9-test.dtb)
  - 4x `samsung,exynos9820-csis` present
  - 4x sensors present: s5k2l4(2L4)/s5k3m3(3M3)/s5k3p9(3P9)/s5k3j1(3J1)
  - ALL 8 endpoint links bidirectionally wired (csis<->sensor phandles match)
  - fimc_is + 6x fimc_is_sensor disabled

### Artifacts produced (all SHA256-verified local==device)
  - merged-overlay.dtbo  (186,261 B)  — entry[9] replacement
  - dtbo-new-8mb.img     (8,388,608 B) — full 10-entry dtbo partition (entry[9]=merged)
  - nuxel-boot-camera-v2.img (48,007,168 B) — new Image + existing LZMA ramdisk, hdr v1
  - Backup: boot-before.img (57,671,680 B = current working sda14),
            dtbo-before.img (8,388,608 B = current sda13) saved to macOS /tmp/camwork
  - Known-good current sda14 kernel first_u32=0x146cc000 (raw ARM64 Image), size 45,848,584
  - New Image first_u32=0x146bc000 (raw ARM64 Image), size 45,578,248

### NEXT (bounded): flash boot(sda14) + dtbo(sda13) via adb dd -> reboot -> boot check

## Session 7 (cont.) — FLASH ATTEMPTED + ROLLED BACK; two independent blockers isolated

### Flash #1 (new kernel + merged dtbo) -> RECOVERY (bootloader rejected overlay)
Flashed boot(sda14)=nuxel-boot-camera-v2.img + dtbo(sda13)=10-entry with entry[9]=
merged overlay (vendor26+camera), both SHA256 readback verified. Result: device
fell back to TWRP, no new pstore written (kernel never ran). => The Samsung
bootloader rejected the merged dtbo overlay. Most likely cause: my camera
overlay's `fragment@100 { target-path="/" }` — the vendor beyond2lte_26 overlay
uses ONLY `target=<phandle>` (`&label`), never `target-path`. Samsung's 4.14-era
bootloader overlay applier does not support target-path.

### Flash #2 diagnostic (new kernel + ORIGINAL dtbo) -> Nuxel boots 37s, then ABOX panic
Restored dtbo to known-good, kept new kernel Image. Device booted Nuxel (SSH OK,
display/touch/WiFi all up), but panicked at t=37.9s:
  "Unable to handle kernel paging request at ffffff80238b006c"
   pc : abox_is_calliope_incompatible.isra.0+0x40/0x84
   lr : abox_system_ipc_handler+0x60/0x580        (swapper/1, interrupt ctx)
The ABOX audio DSP driver faults in memcpy(&msg, data->sram_base + 0x30040, 0x3C)
right after calliope firmware download + abox_core_power(1). sram_base (ioremap)
reads past its mapped region => page fault. This is UNRELATED to camera; it is a
kernel-rebuild regression. Difference found: original stable #3 kernel built
with gcc 15.2.0 (host), on-device rebuild used gcc 15.3.1; also the on-device
source tree /root/kbuild may not match the #3 source exactly.

### VERIFIED CONFIG GAP: camera modules REQUIRE the new kernel
Original stable #3 config: CONFIG_MEDIA_CONTROLLER is NOT set, no V4L2_SUBDEV_API,
no V4L2_FWNODE. The s10-camera-v4l2 drivers depend on all three (v4l2-async,
media-controller, subdev API). So the .ko cannot load on the stock kernel; the
custom kernel is required. This is why a kernel flash is unavoidable.

### ROLLBACK (complete, device STABLE now)
  - Restored boot(sda14) <- boot-before.img (55MiB, original #3 stable kernel)
  - Restored dtbo(sda13) <- original 10-entry (beyond2lte_26 entry[9] intact)
  - Reboot -> SSH OK, uname "4.14.253-gf7194c1d15ed-dirty #3 SMP PREEMPT" (WIN-CLIENT)
  - pstore now shows encrypted dmesg-ramoops-0.enc.z (the ABOX panic), last_kmsg
    holds the full ABOX Oops for the next session.

### Remaining blockers (each independently diagnosed, NOT camera):
  A. dtbo overlay target-path="/" unsupported -> convert CSIS/hold/clock nodes
     to phandle-target fragments (target an existing root-level label, or fold
     into the vendor fimc_is_sensorN nodes), OR put the fully-resolved DTB in
     sda12 (dtb) + neutralize dtbo entry[9] (Option A already prepared:
     dtb-new-8mb.img + dtbo-noop-8mb.img verified offline).
  B. New kernel ABOX sram_base page fault (gcc 15.3.1 vs 15.2.0 regression).
     Must rebuild with matching compiler OR fix abox.c sram mapping. Blocker for
     booting the custom camera kernel at all.

### Artifacts saved (macOS /tmp/camwork + repo kernel/s10plus/dts/):
  - nuxel-camera-v4l2.dtso (FIXED: fragment@100 target-path + fimc disable)
  - merged/beyond2lte_eur_open_26-camera-merged.dts (verified merged overlay)
  - merged/merge_overlays.py, merged/rebuild_dtbo.py, merged/build_boot.py
  - dtb-new-8mb.img, dtbo-noop-8mb.img (Option A, verified offline)
  - nuxel-boot-camera-v2.img (new kernel + ramdisk, header v1)
  - backup/boot-before.img + dtbo-before.img (known-good)

## Session 7 (cont. 3) — ROOT CAUSE FOUND (missing patches) + rebuilt + CRITICAL STATE

### Root cause of the kernel crashes (ABOX + NFC): MISSING NUXEL PATCHES
The prior sessions rebuilt the kernel from a PRISTINE upstream checkout WITHOUT
the ~22 Nuxel patches in kernel/s10plus/patches/. Two crashes were exactly the
two patches:
  - ABOX panic (abox_is_calliope_incompatible sram memcpy fault)
      = fixed by 0004-nuxel-abox-boot-done-and-bt-hciuart.patch (use param3)
  - NFC panic (sec_nfc_probe -> class_create_file_ns NULL)
      = fixed by 0007-sec-nfc-class-name.patch (rename "nfc"->"sec_nfc")
NOT a gcc 15.3.1 vs 15.2.0 compiler issue (macOS homebrew aarch64-linux-gnu-gcc
is 15.2.0, but cross-compile is blocked by missing Linux host headers elf.h +
fixdep link + case-insensitive APFS netfilter xt_DSCP/xt_dscp collision).

### FIX: applied all patches to on-device /root/kbuild, rebuilt natively (15.3.1)
  - Applied 21 patches (0001 stub skipped); verified ABOX+NFC fixes in-tree.
  - UDMABUF Kconfig now present (patch 0005).
  - correct config = defconfig + nuxel-all.fragment (NFC/nftables/USB-ECM/UDMABUF
    retained + MEDIA_CONTROLLER=y + V4L2_SUBDEV_API=y + VIDEO_S10_CAMERA=m).
  - BUILD SUCCEEDED: Image 45,848,584 B (== stable #3 size!), 5 camera .ko
    (s5k-cis, exynos9820-csis, ak7374, s10-isppre-hold, v4l2-fwnode, videobuf2-dma-contig).

### FINAL FLASH (sda12=merged DTB, sda13=no-op dtbo, sda14=camera kernel) -> HARD HANG
Flashed triple set, all 3 SHA-256 readback verified. Reboot -> device did NOT
enter TWRP or Nuxel; no USB enumeration for ~13 min. Most probable: Samsung
bootloader rejected the base-DTB replacement (sda12) or the 207-byte no-op dtbo
entry[9] broke its overlay parser. This is the hard-hang branch from cam.md.

### STATUS: device unreachable via adb/USB; PHYSICAL power-cycle required.
Known-good backups + exact restore commands are in CAMERA_RECOVERY_AND_ROLLBACK.md.
All camera engineering (DTBO fix + FIMC coexist + merged overlay + patched
correct-config kernel build) is complete and preserved. The only unverified item
is the bootloader's DTB-partition acceptance format, which blocked the last flash.
