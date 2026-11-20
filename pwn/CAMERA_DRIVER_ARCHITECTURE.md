# NUXEL S10+ Camera Driver Architecture — Decision Record

**Date:** 2026-11-20
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos9820, kernel 4.14.253-gf7194c1d15ed-dirty
**Author:** Nuxel camera engineering agent

## Chosen architecture

**Two-stage strategy, decisive-first:**

1. **Stage A (attempt first, bounded): complete the existing Samsung FIMC-IS2 vendor
   pipeline via a userspace-native control layer.** The firmware problem is already
   resolved (8 blobs deployed and hash-verified), the rear 2L4 sensor binds and
   initializes, and ION DMA-BUF capture buffers can be queued on the ISP capture
   node `/dev/video131` (i0c). The remaining work is reconstructing the vendor
   driver's proprietary leader/follower streaming sequence (S_INPUT -> sensor
   leader start -> 3AA/ISP group leader start -> ISP capture stream-on -> DQBUF).

2. **Stage B (fallback, authorized): port the proven custom native V4L2 driver
   (`s10-camera-v4l2`) from butztill/s10-linux** to the running 4.14.253 kernel,
   with libcamera software-ISP pipeline. This is the only publicly documented
   native-Linux capture path that produced physical still images on Exynos9820.

## Evidence supporting the choice

### Stage A viability
- Firmware loads cleanly (`rom id[0] 1`, `rta name is fimc_is_rta.bin`), confirmed live.
- SAK2L4 sensor initializes (`Sensor version. Rev. 0xA102`, OIS, actuator product_id 0xE).
- ION `camera_heap` (id 5) DMABUF allocation + `VIDIOC_QBUF` succeed on i0c (4 buffers).
- The vendor driver already contains the complete hardware-specific ISP implementation
  (DDK/RTA firmware, AF/AE/AWB, OIS, actuator) — no new kernel driver needed if the
  userspace sequence can be reconstructed.

### Stage A risk
- `fimc_is_ixc_video_get_format_mplane()` is a literal stub (`return 0` without
  populating the format struct) — ISP capture format is never exposed via G_FMT.
- Sensor leader `/dev/video101` (`ss0`) rejects every `VIDIOC_S_FMT` (format is set
  internally via private controls + S_INPUT, not S_FMT).
- ISP capture start requires the 3AA/ISP group leader to be started first
  (`fimc_is_itf_process_start()` runs in the group-leader start path); otherwise
  `start_streaming` fails with -22.
- Reconstructing this is effectively reimplementing Samsung's undocumented
  proprietary `libexynoscamera` HAL. No public reference demonstrates success.

### Stage B viability
- s10-linux `drivers/s10-camera-v4l2/` is a clean, GPLv2, standard-V4L2 driver:
  CSI receiver (`exynos9820-csis.c`, 1380 lines) + sensor subdev (`s5k-cis.c`, 1115
  lines) + lens actuator (`ak7374.c`, 361 lines). ~3000 lines total.
- It produces RAW10 Bayer via the CSIS write-DMA directly (media graph sensor->csis->video).
- Documented: four sensors produced still images (STATUS.md, 2026-10-31).
- The sensor register tables (the raw material) are GPL-available as
  `fimc-is-cis-{2l4,3m3,3p9,3j1}-setA.h` — **already present in our on-device kernel
  source** at `drivers/media/platform/exynos/fimc-is2/sensor/module_framework/cis/`.
- s10-linux uses libcamera with a software ISP (patches/libcamera/*) + Plasma Camera.

### Stage B risk / cost
- s10-linux targets Linux **7.2-rc2**; our kernel is **4.14.253**. The driver uses
  modern media/videobuf2/V4L2-async APIs that must be backported to 4.14.
- Produces **raw Bayer only**; requires libcamera software ISP for color/preview/video
  (no hardware ISP, AF/AE/AWB must be implemented in software or via V4L2 controls).
- s10-linux does NOT support the S10+'s 5th sensor (4HA front depth) — must be added.
- Requires a kernel rebuild + flash (authorized via TWRP recovery).

## Alternatives considered

- **Complete FIMC-IS2 vendor HAL (pure Stage A)** — fastest if it worked, but the ISP
  G_FMT stub and undocumented leader/follower protocol make it a high-risk reverse
  engineering effort with no public success precedent.
- **gangg111/S10Plus_Linux Droidian port** — uses Android Camera2/libcamx (libhybris).
  Violates the zero-Android-userspace requirement. Extracted hardware/topology knowledge
  only; not a runtime dependency.

## Reusable components

- Stage A: existing `nuxel-ion-capture.c`, `nuxel-fimc-full-capture.c`,
  `nuxel-fimc-leader-capture.c`, `videodev2_exynos_camera.h` (private control IDs),
  deployed firmware blobs (`/system/vendor/firmware/`), patch 0022.
- Stage B: `s10-camera-v4l2/` driver sources, `s5k-fw.h`/`s5k-fw-manifest.h` loader,
  `prepare-s5k-tables.py` generator, libcamera patches, DTS camera topology, ak7374 lens.

## Required changes (staged)

1. Stage A: reconstruct the leader streaming sequence and attempt first frame
   (no kernel change).
2. If Stage A fails: backport s10-camera-v4l2 to 4.14, add 4HA, build, flash via TWRP.
3. libcamera software-ISP pipeline + PipeWire producer.
4. Portal/broker fixes; Nuxel Camera app; GTK + Flatpak validation.

## Rollback plan

- Stage A changes are userspace-only (reversible by rm).
- Stage B: preserve last-known-good boot image; record flash provenance + SHA-256;
  TWRP recovery path available; `fimc-is2` vendor driver remains in-tree as rollback.
