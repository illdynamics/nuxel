# PWNAGE-60000 — Kickstart prompt

You are taking over the Nuxel Samsung Galaxy S10+ GPU acceleration mission. Read `full-pwnage-60000.md` first and treat it as the detailed contract. This file is the execution kickoff: start implementing, not merely researching.

## Mission

Finish and harden the partially working Mali-G76 acceleration pipeline on the physical Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820). Make the proven GPU-rendered profile the normal Home/Settings path with reliable software fallback, reduce the remaining CPU presentation overhead where safely possible, and investigate hardware video decode, USB-C HDMI and wireless casting as separate capabilities.

## Known starting point — verify it again

PWNAGE-53000 already proved on the phone:

- Phoc rendering through the ARM kbase Mali-G76 path;
- Mesa EGL/GLES 3.2 and a working EGL Wayland surface;
- GTK3 `GtkGLArea` on Mali;
- wlroots linux-dmabuf v3 importing tested LINEAR buffers;
- WebKitGTK GPU compositing and kbase job submissions, but SHM presentation;
- a stable `nuxel-wl-fb` final CPU-copy/scale/pan path;
- one `/dev/fb0` writer and healthy DECON/DPU20 panel output.

The report measured active UI userspace CPU use dropping from 47.0% of one core on llvmpipe to 27.8–31.3% with Mali enabled: approximately 33–41% less CPU used by those measured UI processes, not a 33–41% whole-phone speedup.

The current `graphics-profile.json` still defaults to `software-safe`; only the diagnostic app selects `gpu-rendered-shm-presented`. Fix this production gap after revalidation.

## Execute in this order

1. Read `docs/beta-finalization/live/PWNAGE-53000-GRAPHICS-REPORT.md`, `full-pwnage-60000.md`, the graphics profile/helper/session launcher, A67 GPU sources, rootfs builder and live kernel config.
2. Re-run the physical-phone baseline. Prove the live Phoc and production Home/Settings processes map the intended Mesa driver and submit kbase jobs. Confirm there are no llvmpipe threads.
3. Make `gpu-rendered-shm-presented` the production default only after successful repeated live tests. Keep `software-safe` as an automatic per-process fallback. Do not call the current SHM path DMA-BUF or zero-copy.
4. Make the image builder require the pinned GPU library set and SHA-256 manifest for release images. Fail loudly if it would silently ship stock Mesa/software GL.
5. Add structured diagnostics separating Mali rendering, GTK3/GTK4, WebKit rendering, SHM vs DMA-BUF transport, and final framebuffer presentation.
6. Investigate WebKit 2.54.1's real GBM/`drmMainDevice()` DMA-BUF gate. Prototype only in isolation. No fake `/dev/dri`, no `/dev/mali0` symlink, and no assumption that `CONFIG_DRM_VGEM=y` alone solves allocation/export.
7. Optimize `nuxel-wl-fb` damage, compare, NEON conversion and pacing only where measured. Preserve the one-writer `/dev/fb0` contract and working rotation/touch path.
8. Investigate the Exynos MFC driver/firmware ABI before touching `/dev/video*`. Keep `nuxel-gstreamer-guard.sh` active until a safe, repeatable V4L2 M2M decode pipeline is proven.
9. Run read-only Type-C and casting diagnostics. Treat HDMI and Miracast as separate projects; do not expose UI controls until real external pixels/receiver streaming is proven.
10. Run matched A/B benchmarks, all regression tests, a cold-boot smoke test, staged deployment and rollback verification.

## Non-negotiable constraints

- No bootloader, recovery, EFS, modem, partition, firmware or kernel flashing.
- Do not enable the conflicting Exynos DRM output driver in the live kernel as an experiment.
- Do not remove the single framebuffer presenter or introduce a second `/dev/fb0` writer.
- Do not advertise ARM tiled/AFBC modifiers unless the allocator truly produces them.
- Do not remove the GStreamer guard based on plugin enumeration alone; MFC `open()` has previously blocked in firmware loading.
- Do not confuse GPU rendering with hardware video decoding.
- Do not confuse stock Samsung DeX support with a working Nuxel Linux HDMI/Miracast stack.
- Preserve a known-good software fallback, atomic deploy and tested rollback.
- No fake benchmark, fake utilization number, or unsupported “fully accelerated” label.

## Must-have acceptance

- Normal Home/Settings demonstrably use Mali on the live phone after a cold boot.
- GPU startup failure returns to `software-safe` without a blank screen or manual SSH repair.
- Release image verifies pinned Mesa/wlroots/EGL assets and profile config.
- GPU status reports renderer, WebKit transport and final panel path separately.
- DMA-BUF LINEAR import tests remain green; malformed clients cannot crash Phoc.
- Any WebKit DMA-BUF claim is backed by genuine exported/imported buffer FDs and lifecycle evidence.
- Framebuffer optimizations improve measured timings without visual, touch, rotation or stability regressions.
- Hardware video decode is proven by the actual MFC driver/caps and real playback, or remains safely disabled with a precise blocker.
- HDMI and casting are proven end-to-end or honestly marked not yet supported.
- All changes have tests, evidence, deploy and rollback instructions.

## Deliverables

- Implemented code and updated config/build integration.
- Pin manifest for GPU binaries and build source commits.
- Updated GPU diagnostic/API output.
- Automated regression tests and exact test results.
- `evidence/pwnage-60000/` with raw matched A/B measurements from the S10+.
- `docs/beta-finalization/live/PWNAGE-60000-REPORT.md` with PASS / PARTIAL / BLOCKED / NOT TESTED for GPU, DMA-BUF, scanout, video, HDMI and casting.
- Safe deployment/rollback scripts and an owner handoff for any physical cable/receiver tests.

Start with baseline verification, then fix production profile selection. Do not disappear into speculative kernel work while the already-proven Mali path is still disabled for normal Home/Settings.
