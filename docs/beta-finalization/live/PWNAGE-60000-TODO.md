# PWNAGE-60000 — remaining work / owner handoff

Status as of 2026-11-03.  The production GPU path and its fallback are complete;
the items below are the honest remaining gaps.

## Owner / physical-hardware tests

1. **USB-C → HDMI**
   - Use a known adapter and record its chipset/power behavior.
   - Keep Wi-Fi SSH available before connecting.
   - Capture `nuxel-typec-diag.sh status --json`, `dmesg -w`, and
     `nuxel-gpu-status --json` before/after.
   - Do not write mux/PMIC/PHY/regulator state.  No support claim without a
     real connector/EDID and visible Nuxel pixels.
2. **Touch / rotation / suspend**
   - Exercise physical touch, rotation, screen off/on, suspend/resume.
   - The bridge rotation/touch code was not modified, but this run did not
     exercise those physically.
3. **Miracast / LAN screen share**
   - Requires real P2P + RTSP + capture + encoder + receiver proof.
   - No Cast UI exists yet.  LAN sharing must be authenticated, user-started,
     stoppable and lockscreen-redacted.
4. **Cold-boot observation**
   - Confirm Settings launches and scrolls normally after an owner reboot.
   - Run `/usr/lib/nuxel/nuxel-gpu-status --deep` and keep the JSON.

## Engineering work still blocked

1. **WebKit DMA-BUF / zero-copy**
   - Blocked by absence of a real DRM/GBM device (`drmMainDevice()` null).
   - Would require a separately approved kernel/display project (Exynos DRM/KMS
     + kbase export + panel integration), not a fake node or a WebKit bypass.
2. **Exynos MFC hardware decode**
   - Blocked by missing `mfc_fw.bin` and the unsafe
     `request_firmware()`/user-helper fallback path.
   - Keep `nuxel-gstreamer-guard.sh` installed.  Do not open `/dev/video*` from
     the desktop or from GStreamer's scanner.
   - A future project needs matching firmware provenance, an audited bounded
     open path, 100 open/close cycles and real V4L2 M2M playback.
3. **Full release image build**
   - The fail-closed GPU verifier and synthetic-stage tests pass; a complete
     rootfs image build was not run in this mission.  Run the image builder with
     `NUXEL_RELEASE=1` and confirm the final verifier gate before publishing.

## Do not do

- Do not flash boot/recovery/EFS/modem/partition/firmware.
- Do not enable `CONFIG_DRM_EXYNOS` as an experiment.
- Do not create `/dev/dri` or symlink `/dev/mali0`.
- Do not add a second `/dev/fb0` writer.
- Do not advertise ARM tiled/AFBC modifiers.
- Do not remove the GStreamer guard based on plugin enumeration.
- Do not label SHM presentation, CPU scanout, stock Samsung DeX or a Miracast
  capability probe as working acceleration/HDMI/casting.
