# A50 — 02: Display resolution and rendering truth

All values measured live (not assumed).

## Physical panel
- `/dev/fb0` → `19030000.decon_f` (primary DECON-F). `FBIOGET`/sysfs:
  - `xres=1440 yres=3040`, `xres_virtual=1440 yres_virtual=6080` (double-buffered),
  - `bits_per_pixel=32`, `stride=5760` (= 1440 × 4 B), `smem` covers both pages.
- Panel identity from `/etc/nuxel/orientation/orientation.json`:
  `S6E3HA9 Dynamic AMOLED 3040x1440 (portrait scanout 1440x3040)`.
- `/dev/fb1` → `19050000.decon_t` (DECON-T, 640×960, stride 2560) — secondary.

## Compositor (live)
- phoc runs **headless + pixman** (`WLR_BACKENDS=headless,libinput`,
  `WLR_RENDERER=pixman`, `WLR_HEADLESS_OUTPUTS=1`, `LIBSEAT_BACKEND=noop`,
  `LD_PRELOAD=libnuxel-libinput-path.so`).
- `/etc/nuxel/phoc-phone.ini`: `[output:HEADLESS-1] mode = 720x1520 scale = 2`.
  - Compositor **buffer = 720×1520 (1.09 Mpx)**, scale 2 → 360×760 logical,
    360 px CSS viewport width (the same band as the UTM VM).
- WebKitGTK forced to software rendering by `nuxel-session.sh`:
  `WEBKIT_DISABLE_COMPOSITING_MODE=1`, `LIBGL_ALWAYS_SOFTWARE=1`,
  `GDK_BACKEND=wayland`, `GSK_RENDERER=cairo`.

## Bridge (live, measured from `/run/nuxel-wl-fb.state` FRAMES_OK)
`out=720x1520 src=720x1520 scale=2 panel=1440x3040 src_format=0x00000001(XRGB8888)
colour=R@0,G@8,B@16_abgr8888_override=1`

So the **compositor already renders at 720×1520** (the historic "720p-class"
configuration) and the bridge 2× nearest-neighbour-upscales to the native
1440×3040 panel, converting XRGB8888 → the panel's ABGR8888 order and forcing
opaque alpha. `decon_pan_failed=0` across all samples (commits healthy).

## GPU / DRM truth
- `CONFIG_DRM` unset: no `/dev/dri`, no `/sys/class/drm`, no render nodes,
  no EGL/GBM device. Confirmed live.
- Consequently there is **no hardware acceleration anywhere** in the display
  path: phoc pixman render, WebKit software paint, and the bridge's CPU
  upscale/convert are all CPU work.

## Resolution candidates (truth, not promises)
| Candidate | Compositor buffer | Verdict vs current |
|---|---|---|
| Current deployed | 720×1520 (scale 2) | baseline — this is what runs |
| 1080-class | 1080×2280 (2.46 Mpx) | would *increase* software render + upscale cost; rejected on theory, not tested (higher risk, no upside expected) |
| Native-class | 1440×3040 (4.38 Mpx) | substantially slower on CPU; rejected on theory |
| 540-class | 540×1140 (0.62 Mpx) | **only** candidate that could reduce the per-frame CPU cost; would reduce readability and change safe-zones/touch calibration — deferred, requires on-device visual A/B by owner |

The historic hypothesis "lower resolution helps" is **already the deployed
state**: compositor is 720×1520. The remaining per-frame cost is dominated by
software compositing + the 720→1440 upscale + 4.38 Mpx panel write + fbdev
commit, so further lowering the compositor buffer only helps the (smaller)
compositor/upscale halves while the 1440×3040 panel write stays constant
(~17.5 MB/frame). It is **not** expected to be a silver bullet; it was not
tested because it requires a phoc config change + graphics restart and an
owner-verified visual/readability A/B.
