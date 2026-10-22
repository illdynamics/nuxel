# A50 — Future renderer migration (not performed)

The hard ceiling of this device's display path is the absence of DRM/GPU:
`CONFIG_DRM` is unset on the vendor 4.14.253 kernel, so every stage
(compositor, WebKit paint, upscale/convert, framebuffer commit) is CPU work.

## Dependencies for a real hardware-accelerated path
1. **Kernel 6.x migration** (or a vendor kernel rebuild with `CONFIG_DRM`,
   `DRM_SAMSUNG`/`exynos_drm` + DECON/DSIM + Mali Bifrost `panfrost`/G3D).
   This is a kernel/boot-image change — **out of scope and not authorised** in
   this userspace mission.
2. **DRM/KMS panel bridge** (exynos DECON-F over DRM instead of raw fbdev),
   including the command-mode panel commit path that currently uses
   `FBIOPAN_DISPLAY`.
3. **GPU userspace**: Mali Bifrost userspace driver + Mesa `panfrost` (or the
   vendor DDK) for EGL/GBM; then wlroots `WLR_RENDERER=gles2` +
   `WLR_BACKENDS=drm` and WebKitGTK hardware compositing become possible.

## Interim, userspace-only improvements (in descending payoff)
1. Recover the exact live `nuxel-wl-fb` source (it is an uncommitted build newer
   than a34), then add a **NEON 2×-upscale + XRGB→ABGR inner loop** to shave
   ~10–15 ms/frame off the 74–79 ms changed-frame cost.
2. Remove software-rendered `backdrop-filter: blur()` (status bar 12 px, QS
   20 px) and replace with semi-opaque solid backgrounds (owner visual A/B).
3. Resize the 1.0–1.14 MB nav-button PNGs and 0.9 MB dock art to the effective
   360 px-viewport size (keep originals in source).
4. A/B the compositor buffer 720×1520 → 540×1140 only if the owner accepts
   reduced readability and revalidates safe-zones/keyboard/touch calibration.

With the current framebuffer architecture (software compositor + screencopy +
CPU upscale/convert + fbdev commit), **~13 FPS is the measured ceiling for
continuously-changing full-screen content**; 30/60 FPS require the DRM/GPU path
above.
