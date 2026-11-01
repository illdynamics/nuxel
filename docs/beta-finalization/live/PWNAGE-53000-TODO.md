# PWNAGE-53000 — FINISH MALI-G76 ACCELERATION (graphics) — task tracker

Live target: SM-G975F (`beyond2lte`), Fedora 43 ARM64, Exynos 9820, Mali-G76 MP12.
Kernel: `4.14.253-gf7194c1d15ed-dirty #5` (2026-11-01 13:38:15 CET).
Compositor: Phoc 0.54.0 + patched wlroots 0.19.3.
Full write-up: `PWNAGE-53000-GRAPHICS-REPORT.md`.
Evidence: `evidence/pwnage-53000/{baseline,crash,dmabuf,egl,gtk,webkit,performance,deployment}/`.

> Note: this file previously tracked the *other* PWNAGE-53000 run (NFC,
> microphone, Flatpak, clean rootfs). That work is preserved in
> `PWNAGE-53000-REPORT.md`; this file now tracks the graphics mission.

| # | Task | Status | Evidence |
|---|---|---|---|
| 1 | Re-probe baseline; identify real renderer | **PASS** | Phoc was **llvmpipe**, not Mali: stock EGL symlink, `libgallium-25.3.6`, 8 llvmpipe threads. `baseline/top.txt`, `baseline/graphics.txt` |
| 2 | Hash-verified backup before changes | **PASS** | `/var/backups/nuxel/p53000-20261101T143813`, `...152336`; `deployment/backup-sha256.txt` |
| 3 | Reproduce exact failure with a non-WebKit client | **PASS** | ARM modifier `0x0800000000000062` selected for a LINEAR udmabuf; client stalls, Phoc alive. `crash/` |
| 4 | Separate Phoc crash vs client protocol failure | **PASS** | Phoc PID unchanged through malformed/disconnect tests; no core in this repro |
| 5 | Stop advertising unproven tiled/AFBC modifiers | **PASS** | `wlroots-kbase-linear-dmabuf.patch`; `dmabuf/formats.txt` shows LINEAR only |
| 6 | Validate planes/offset/stride/dimensions before import | **PASS** | valid 20/20 accepted; malformed offset/dim disconnect only that client; Phoc survives |
| 7 | EGL surfaceless on Mali | **PASS** | `GL_RENDERER=Mali-G76 MC12 (Panfrost)`, GLES 3.2 |
| 8 | EGL_PLATFORM_WAYLAND window surface + swap | **PASS** | `egl/egl-wayland-live.log` → `PASS` |
| 9 | Phoc on real kbase Mali | **PASS** | maps `libgallium_dri.so`, 3× `/dev/mali0`, 0 llvmpipe threads |
| 10 | linux-dmabuf v3 global with RGB LINEAR | **PASS** | AB24/XB24/AR24/XR24 + `MOD_LINEAR` |
| 11 | GTK3 GtkGLArea renders on Mali | **PASS** | `gtk/gtk3-live.log` 3× PASS |
| 12 | GTK4 | **PARTIAL** | 4.20.4 installed; GSK stays `auto`/cairo fallback, no DMA-BUF claim |
| 13 | WebKit web process on Mali | **PASS** | 3× `/dev/mali0`, `libgallium_dri.so`, 4 `ThreadedCompositor` threads |
| 14 | WebKit GPU job submission proof | **PASS** | 186 × `KBASE_IOCTL_JOB_SUBMIT` in 3 s (`_IOW(0x80,0x02,0x10)`) |
| 15 | WebKit accelerated compositing mode | **PASS (GPU-SHM)** | `WEBKIT_FORCE_COMPOSITING_MODE=1`; 0 udmabuf/dmabuf FDs |
| 16 | WebKit DMA-BUF export/import | **BLOCKED_KERNEL_ABI** | `drmMainDevice()` null; `CONFIG_DRM_VGEM` unset; no `/dev/dri` |
| 17 | True zero-copy presentation | **BLOCKED_KERNEL_ABI** | no DRM/KMS scanout; `/dev/fb0` cannot import DMA-BUF |
| 18 | Per-app truthful profiles | **PASS** | schema 2: `software-safe`, `gpu-rendered-shm-presented`, `gpu-rendered-dmabuf-presented` (unavailable), `fully-accelerated` (unavailable) |
| 19 | Keep Home/Settings/lockscreen safe | **PASS** | default profile remains `software-safe` |
| 20 | High CPU reduction | **PASS** | one-core userspace 47.0% → 27.8–31.3%; blit 45→30-38 ms; static capture 24→1 fps |
| 21 | Explain load average 12+ | **PASS** | 11 Samsung TrustZone/secure D-state kthreads, not CPU |
| 22 | Idle bridge pacing | **PASS** | adaptive 24/10/3/1 fps; verified 10 captures/10 s when static |
| 23 | Single `/dev/fb0` writer | **PASS** | `fuser` shows only `nuxel-wl-fb` |
| 24 | `FRAMES_OK` / `decon_pan_failed=0` / 1440×6080 | **PASS** | `performance/final.txt`, `deployment/live-test-output.txt` |
| 25 | Rollback tested live | **PASS** | restored llvmpipe set, panel healthy, then redeployed accelerated set |
| 26 | Reproducible packaging | **PASS** | `build-wlroots-kbase-linear.sh`, `deploy-pwnage53000.sh`, `rollback-pwnage53000.sh`, rootfs builder updated |
| 27 | Automated regression tests | **PASS** | `tests/pwnage53000/test_graphics_linear_dmabuf.py` (8 passed) + on-device `pwnage53000-live-test.sh` |
| 28 | Reboot and re-verify | **PENDING** | final step; persistent diagnostics installed under `/usr/lib/nuxel` |

## Remaining blockers (honest)

1. **WebKit DMA-BUF / fully-accelerated** — requires a DRM/GBM allocation node.
   The current kernel has `CONFIG_DRM=y`, `CONFIG_MODULES=y`, but
   `CONFIG_DRM_VGEM` unset, no `/dev/dri`, and `CONFIG_MODVERSIONS=y` without
   the exact `Module.symvers`, so an out-of-tree vgem module cannot be loaded
   safely. This is a separate owner-approved kernel build, not a userspace fix.
2. **GTK4 DMA-BUF import** — not claimed; GTK4 GSK remains auto/cairo.
3. **CPU scanout copy** — `nuxel-wl-fb` still copies/scales into `/dev/fb0` on
   the CPU; measured and disclosed, not called zero-copy.
4. **Load average** — kernel TrustZone worker threads keep it ~12; userspace
   CPU is low. Changing those is outside this mission.

## Rollback

```sh
tools/s10plus/a67/rollback-pwnage53000.sh root@192.168.178.167 \
  /var/backups/nuxel/p53000-20261101T143813
```

Then redeploy with:

```sh
STAGE=build/out/s10plus/pwnage53000 \
  tools/s10plus/a67/deploy-pwnage53000.sh root@192.168.178.167
```
