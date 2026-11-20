# NUXEL S10+ Camera — Live Physical Acceptance Matrix

**Date:** 2026-11-20
**Device:** SM-G975F beyond2lte, kernel 4.14.253-gf7194c1d15ed-dirty (live SSH root@10.11.12.99)

## Result table (honest, as of session 3)

| Test | Required | Observed | Status |
|---|---|---|---|
| Firmware selection | PASS | rom id[0] 1, rta=fimc_is_rta.bin, SAK2L4 rev 0xA102 | ✅ PASS |
| Rear sensor initialization | PASS | SAK2L4 sensor_module_init(0), OIS, actuator 0xE | ✅ PASS |
| Rear sensor S_FMT (format negotiation) | PASS | S_FMT=0 at 2016x1512 SBGGR10 after S_SENSOR_SIZE ctrl | ✅ PASS (NEW) |
| Rear sensor REQBUFS/QBUF | PASS | REQBUFS=0, QBUF[0..3]=0 (2-plane dmabuf) | ✅ PASS (NEW) |
| Rear physical frame (DQBUF) | PASS | STREAMON causes watchdog panic; no DQBUF | ❌ NOT PASS |
| Front physical frame capture | PASS | not reached | ❌ NOT PASS |
| Rear/front live preview | PASS | not reached | ❌ NOT PASS |
| Rear/front JPEG/photo saved | PASS | not reached | ❌ NOT PASS |
| Rear/front video recording | PASS | not reached | ❌ NOT PASS |
| Recorded microphone audio | — | existing mic verified separately | — |
| Audio/video sync | PASS | not reached | ❌ NOT PASS |
| Gallery playback | PASS | not reached | ❌ NOT PASS |
| Flash/torch | PASS | not reached (flash-gpio device present) | ❌ NOT PASS |
| Native Nuxel Camera | PASS | not reached | ❌ NOT PASS |
| Native GTK camera (Fedora) | PASS | not reached | ❌ NOT PASS |
| Flatpak camera | PASS | not reached | ❌ NOT PASS |
| Camera permissions | PASS | not reached | ❌ NOT PASS |
| Repeated switching | PASS | not reached | ❌ NOT PASS |
| Camera cleanup on exit | PASS | clean deinit (sensor power off, regulators released) | ✅ PASS |
| Kernel stability after capture | PASS | streaming attempt = watchdog panic; device auto-rebooted to Nuxel | ⚠️ PARTIAL |

## Live evidence 2026-11-20 (nuxel-fimc-capture3)

```
[sensor S_INPUT] 0x00000001 ret=0
[sensor S_SENSOR_SIZE 2016x1512] ret=0                 <-- THE missing control
[sensor S_FMT] ret=0 (SBGGR10, planes=2)               <-- was -EINVAL in all prior work
  dmesg: sensor mode(2016x1512@30) = 5 (lane:4)
[sensor REQBUFS] ret=0 count=4
[sensor QBUF 0..3] ret=0
[sensor STREAMON] -> hardware watchdog panic (pstore Panic#2), reboot
```

## Root cause of the remaining blocker (source-authoritative)

The sensor leader `.start_streaming` (fimc_is_sensor_back_start) starts MIPI CSI
FLITE DMA, but the ISP ischain is not initialized. The ISP init
(fimc_is_itf_process_start) only runs inside the 3AA group-leader start path
(fimc_is_ischain_3aa_start -> fimc_is_ischain_start), which requires dozens of
Samsung ISP-firmware parameters. Reproducing this is reimplementing the
proprietary libexynoscamera HAL. No public native-Linux precedent exists.

## Engineering decision (see CAMERA_DRIVER_ARCHITECTURE.md)

Port s10-linux's custom native V4L2 driver (Strategy B). Feasibility VERIFIED:
the 4.14.253 in-tree media framework compiles cleanly with MEDIA_CONTROLLER +
VIDEO_V4L2_SUBDEV_API enabled. This is the only publicly-documented path that
produced physical stills on Exynos9820.

## Honest conclusion

FIRST_FRAME_VERIFIED = NOT PASS. Firmware, sensor init, sensor format
negotiation and buffer queueing are all verified live. The vendor ISP ischain
streaming is a kernel-crashing dead-end. Strategy B kernel-driver port + flash
is the remaining bounded path, developed offline to avoid further live crashes.
