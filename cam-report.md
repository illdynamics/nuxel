# NUXEL S10+ Camera Recovery — Progress Report

**Date:** 2026-11-20  
**Author:** Automated camera recovery agent  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos9820, kernel `4.14.253-gf7194c1d15ed-dirty`

## Executive summary

The **primary camera blocker is RESOLVED and verified live**: the `-EIO` / `Camera: Failed open phone firmware` failure at `fimc_is_sec_fw_sel_eeprom:3244` was caused by the camera firmware blobs being absent from the Android firmware search path `/system/vendor/firmware/` on the Nuxel rootfs. After deploying the eight owner-stock `G975FXXS9DTK9` firmware blobs (hash-verified), the kernel now loads them cleanly (`fimc_is_sec_run_fw_sel rom id[0] 1`, `rta name is fimc_is_rta.bin`) and the rear 2L4 sensor initializes fully (SAK2L4, OIS, actuator, sensor rev 0xA102) with no firmware error.

**The remaining blocker** to a full physical frame is the Samsung FIMC-IS2 vendor driver's proprietary streaming state machine, which standard V4L2 cannot drive (detailed below). This matches the independent finding that the closest successful native Linux S10 port (`butztill/s10-linux`) also abandoned the FIMC-IS2 vendor driver and wrote a **complete custom camera driver** (`s10-camera-v4l2` + libcamera patches) instead.

---

## 1. Root cause of the firmware `-EIO` (DEFINITIVELY RESOLVED)

### Diagnosis (source-level, verified against the running kernel's exact source)

The running kernel source is present on-device at `/root/kbuild/src` (git HEAD `f7194c1d15eded1c2a1a4dc63825b26103435cc0`, matching the live kernel `4.14.253-gf7194c1d15ed-dirty`).

The failure path (from `drivers/media/platform/exynos/fimc-is2/vendor/mcd/fimc-is-sec-define.c`):

```
fimc_is_sec_sensorid_find()  ->  load_fw_name = FIMC_IS_DDK = "fimc_is_lib.bin"
fimc_is_sec_run_fw_sel()     ->  fimc_is_sec_fw_sel_eeprom(dev, rom_id, false)
fimc_is_sec_fw_sel_eeprom()  ->  snprintf(fw_path, "%s%s", FIMC_IS_FW_PATH, load_fw_name)
                                  fp = filp_open(fw_path, O_RDONLY, 0)   // FAILS
                                  -> "Camera: Failed open phone firmware" -> return -EIO
```

Where `FIMC_IS_FW_PATH = "/system/vendor/firmware/"` (from `fimc-is-binary.h`).

**Critical finding:** this path uses `filp_open()` directly and does **NOT** go through `request_binary()` (the function patch 0022 modified). Therefore patch 0022's `/lib/firmware` `/usr/lib/firmware` fallback was never reached for this specific failure. The firmware selections (`fimc_is_lib.bin` DDK + `fimc_is_rta.bin` RTA + setfiles) are read by `filp_open(FIMC_IS_FW_PATH + name)`.

### Fix applied (userspace-only, reversible, no flashing)

Created `/system/vendor/firmware/` and copied the 8 verified blobs there (and mirrored to `/usr/lib/firmware/`):

| File | SHA-256 | Owner-stock manifest |
|---|---|---|
| `fimc_is_lib.bin` (DDK) | `e0bb2c36bf43e9a864037552640be4b7b57e5944a0c86f8485900152bd5fbbcd` | ✅ match |
| `fimc_is_rta.bin` (RTA) | `9ca4668a2be85edd8c14b5243db235fd145db526915216dab17fae2c8e3ffc30` | ✅ match |
| `fimc_is_fw_mcu.bin` (MCU) | `0887a6c5f2ad8b4d261473889b3b4c5e44497df4b487775e86ae9cf9e535acdf` | ✅ match |
| `setfile_2l4.bin` (rear main) | `bd32765a5afea316e6e4a5dc466ee07e7f4767d90c4a07ea9823fd85d7e86863` | ✅ match |
| `setfile_3m3.bin` (rear tele) | `a696783eec88515b2e14e21c1288baeb61e402ec245a9b2a7e88084139cd0abf` | ✅ match |
| `setfile_3p9.bin` (rear UW) | `226987e49b416ad6a5548069a6abe370ddd8b1ab49bf5005731950fca450100f` | ✅ match |
| `setfile_3j1.bin` (front main) | `dc352608088d409dfc9faf3c5475d045220f5316f49cee4d6619dd98ce076876` | ✅ match |
| `setfile_4ha.bin` (front depth) | `dc352608088d409dfc9faf3c5475d045220f5316f49cee4d6619dd98ce076876` | ✅ match |

### Verification (live)

```
# Before (previous audit):
fimc_is_sec_run_fw_sel rom id[0] 0        <- failed
fimc_is_sec_fw_sel_eeprom:3244: Camera: Failed open phone firmware
fimc_is_vender_fw_prepare: fimc_is_sec_run_fw_sel is fail1(-5)

# After (this run):
fimc_is_resource_get: fimc-is secure state has reset
fimc_is_sec_run_fw_sel rom id[0] 1        <- SUCCESS
fimc_is_sec_fw_find rta name is fimc_is_rta.bin
Sensor[id = 37] use retention mode.
sensor_cis_check_rev : Sensor version. Rev. 0xA102
sensor_2l4_cis_select_setfile 3 stack sensor revision
fimc_is_ois_init_mcu gyro init data applied
[sensor_ak737x_actuator_init] product_id=0xE
[MOD:SAK2L4] sensor_module_init(0)
```

The `nuxel-fimc-capture` sensor probe returns `{"ok":true,"verdict":"SENSOR_BOUND",...}`.

---

## 2. Capture buffer path (ION DMABUF — established and verified)

The FIMC-IS2 driver uses `CONFIG_DMA_BUF_CONTAINER` and manages capture buffers as **ION-allocated DMABUF fds**, not standard V4L2 mmap. A standard mmap-based `VIDIOC_QBUF` fails with `is_dbufcon_prepare: failed to get dmabuf of fd: 0`.

I established the correct path with a new tool (`tools/s10plus/fimc-capture/nuxel-ion-capture.c`):

1. `open("/dev/ion")`, `ION_IOC_ALLOC` (0xC0184900) from `camera_heap` (id 5) → DMABUF fd
2. `VIDIOC_REQBUFS` + `VIDIOC_QBUF` with `V4L2_MEMORY_DMABUF` and `m.planes[].m.fd` = ION fd
3. mmap the same ION fd to read pixels back

**Verified result:** `[QBUF 0..3] OK` on the ISP capture node `/dev/video131` (`exynos-fimc-is-i0c`). This was previously the hard `-EIO`-adjacent `is_dbufcon_prepare` failure.

Ion heaps observed on-device:
```
camera_contig_heap id=4 type=2 (14.6 MB, contiguous; ION_IOC_ALLOC returns ENODEV on this kernel)
camera_heap        id=5 type=6 (works for capture)
secure_camera_heap id=3 type=2
ion_system_heap    id=0
```

---

## 3. Remaining blocker — Samsung FIMC-IS2 streaming state machine

Standard V4L2 capture cannot complete because the vendor driver requires a proprietary leader/follower streaming sequence. Verified findings (source-annotated):

### 3a. Capture-node G_FMT is a stub
`fimc_is_ixc_video_get_format_mplane()` in `fimc-is-video-ispc.c` returns `0` **without** populating the format struct. Standard `G_FMT` validation therefore reports "uncommitted" even after a successful `S_FMT`.

### 3b. Capture-node S_FMT requires a strict state machine
`fimc_is_video_set_format_mplane()` requires `S_INPUT | S_BUFS` (leader) state, and `fimc_is_video_reqbufs()` requires `S_FORMAT | STOP | S_BUFS`. These bits are set in a specific order by the vendor HAL.

### 3c. The sensor leader node rejects S_FMT entirely
The sensor node `ss0` (`/dev/video101`, `VFL_DIR_M2M` under `CONFIG_USE_SENSOR_GROUP`, advertises `VIDEO_OUTPUT_MPLANE`) returns **EINVAL for every `VIDIOC_S_FMT`** regardless of pixel format (YUYV, NV12/NV21, and all SRGGB/SGRBG/SBGGR/SGBRG 8/10/12 variants were tested). Its format is set internally via `S_INPUT` + private controls, not via `S_FMT`.

### 3d. STREAMON on the capture node requires the group leader to be running first
`fimc_is_itf_process_start()` (which starts the ISP firmware processing) is invoked inside the group-leader start path (`fimc-is-device-ischain.c:2917`). The capture node's `start_streaming` fails with:

```
fimc_is_queue_start_streaming:1180: [I0C] start_streaming is fail(-22)
fimc_is_subdev_buffer_finish:944: frame(0) is not com state(1)
```

because the 3AA/ISP group leader (`FIMC_IS_GROUP_START`) was never started.

### 3e. The full correct sequence (what Samsung's libexynoscamera HAL does)

```
1. open sensor ss0 + S_INPUT(rear)                      [verified working]
2. drive the ischain via private controls:
   - V4L2_CID_IS_S_STREAM (base 0x009A1000 + 14)         [verified: EINVAL on ss0 — needs chain pre-setup]
   - V4L2_CID_IS_S_BNS, S_SENSOR_SIZE, SET_SETFILE, etc.
3. STREAMON sensor leader (fimc_is_sensor_back_start)   [blocked: S_FMT rejected on leader]
4. STREAMON 3AA group leader
5. STREAMON ISP capture (i0c) -> DQBUF real frame
```

This is a full reimplementation of Samsung's proprietary `libexynoscamera` userspace HAL, which is (a) substantial multi-day work, and (b) precisely why the independent `butztill/s10-linux` project did NOT use FIMC-IS2 — it wrote a **completely custom `s10-camera-v4l2` kernel driver plus libcamera patches** instead.

---

## 4. Files created/modified this session

### On-device (userspace, reversible)
- `/system/vendor/firmware/{fimc_is_lib,fimc_is_rta,fimc_is_fw_mcu,setfile_2l4,setfile_3m3,setfile_3p9,setfile_3j1,setfile_4ha}.bin` (8 blobs, hash-verified)
- `/usr/lib/firmware/` (same 8 blobs mirrored)
- `/usr/local/bin/nuxel-fimc-capture` (existing probe tool, cross-built)
- `/usr/local/bin/nuxel-fimc-capture2` (MPLANE probe, G_FMT-stub-aware)
- `/usr/local/bin/nuxel-ion-capture` (ION DMABUF capture — QBUF verified)
- `/usr/local/bin/nuxel-fimc-full-capture` (sensor + capture orchestration attempt)
- `/usr/local/bin/nuxel-fimc-leader-capture` (leader+follower orchestration attempt)

### In repo (`/Users/wicked/x/nuxel`)
- `tools/s10plus/fimc-capture/nuxel-fimc-capture2.c`
- `tools/s10plus/fimc-capture/nuxel-ion-capture.c`
- `tools/s10plus/fimc-capture/nuxel-fimc-full-capture.c`
- `tools/s10plus/fimc-capture/nuxel-fimc-leader-capture.c`
- `tools/s10plus/v4l2-uapi/linux/videodev2_exynos_camera.h` (copied from device kernel headers)

---

## 5. Component gates status

| Gate | Status | Evidence |
|---|---|---|
| `FIRMWARE_SELECTED` | ✅ **PASSED** | `rom id[0] 1`, `rta name is fimc_is_rta.bin`, clean SAK2L4 init |
| `FIRST_FRAME_VERIFIED` | ❌ blocked | Requires FIMC-IS2 ischain leader streaming (Samsung HAL reimplementation) |
| `CAMERAS_SUPPORTED_MATRIX_PASSED` | ❌ blocked | Same as above |
| `CAMERA_APP_INTEGRATION_PASSED` | ❌ blocked | No physical frame source yet |
| `CAMERA_FULLY_FUNCTIONAL` | ❌ blocked | Same as above |

---

## 6. Honest next-step options (ranked)

1. **Custom camera driver (recommended, matches proven approach):** Port/write a mainline-style Exynos9820 CSI + sensor + ISP driver exposed as standard V4L2 (like `butztill/s10-linux`'s `s10-camera-v4l2` + `libcamera` patches). This is a large (many-day) kernel-development effort and would need a kernel rebuild + flash. The firmware fix above is still required for the sensor EEPROM/calibration data via the vendor path.

2. **Complete the FIMC-IS2 userspace HAL reimplementation:** Implement the full private-control + leader streaming sequence (about a day given the source is fully mapped now). Risky: the vendor driver may have hidden assumptions that only Samsung's HAL satisfies.

3. **Keep the vendor FIMC-IS2 but expose a userspace daemon** that speaks the private ioctls and publishes a PipeWire node. This inherits the same ischain-blocker as option 2.

---

## 7. Reversibility / rollback

All changes are userspace-only (file copies to `/system/vendor/firmware`, `/usr/lib/firmware`, and new tools in `/usr/local/bin`). No kernel, boot, partition, EEPROM, or firmware-content modification was performed. Rollback = `rm` the created directories/tools. The original phone partitions are untouched.
