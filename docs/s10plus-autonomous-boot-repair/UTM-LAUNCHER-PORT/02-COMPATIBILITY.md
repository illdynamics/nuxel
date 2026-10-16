# 02 — COMPATIBILITY: can the UTM launcher run on the S10+?

## 1. The two runtimes, side by side

| Requirement | UTM VM (works) | S10+ (measured) | Verdict |
|---|---|---|---|
| Kernel | 6.17.1-300.fc43.aarch64 | **4.14.253** Samsung vendor tree (`#13 SMP PREEMPT`) | older, but userspace runs |
| GPU / display API | `virtio-gpu-gl-pci`, DRM/KMS | DECON **fbdev** (`/dev/fb0` `crw------- 29,0`), **`# CONFIG_DRM is not set`** | **no KMS** |
| `/dev/dri/*` | present (virtio-gpu) | **absent** | no GBM, no EGL-PLATFORM_GBM, no render node |
| Compositor | `phoc` (wlroots) + `phosh 0.54.0` | none possible (wlroots needs DRM) | **no Wayland session** |
| Browser engine | WebKitGTK 4.1 (`epiphany`) | none in the image (`pwa/flatpak`/WPE never built) | **PWA cannot be displayed** |
| GTK4 / libadwaita | 4.20.4 / 1.8.7 | installed as phosh dependencies, but no display server to draw on | unusable |
| Panel | Virtual-1 720x1440 | 1440x3040 AMOLED, ABGR_8888 on the wire | different geometry (handled) |
| Input | libinput under Wayland | `sec_touchscreen` evdev, Type B multitouch (`event2`, PROP=DIRECT) | usable directly |
| Fedora userspace | Fedora 43 | Fedora 43 (systemd 258 as PID 1, graph completes) | equal |

The phone's own repository already reached this conclusion for Phosh
(`PHOSH-ASSESSMENT.md`: *"PHOSH_WAYLAND_PHONE_UI_READY … a kernel/display-porting
project, not a config flag"*). The same facts decide the launcher question.

## 2. Decision order, applied

**Option A — run the original launcher directly.** *Not possible.* The launcher
is a web application; it needs a browser engine, and a browser engine on this
board needs a display API. Measured: no `/dev/dri`, no DRM/KMS in the kernel, no
WebKitGTK/WPE/Chromium/Firefox in the S10+ image. Nothing about "install a
package" can create a scanout path the kernel does not implement.

**Option B — add a compatibility layer.** *Not available today; the requirement
is now written down instead of guessed.* The established components that could
theoretically bridge this are:

| Candidate | Why it is not a solution here |
|---|---|
| `Xorg` + `xf86-video-fbdev` | not installed; installing it needs the phone's package mirror (no network on this device: no wlan/radio driver) and pulls a large dependency closure that cannot be staged over the CDC-ACM console; and it would still need a browser engine on top |
| `weston --backend=fbdev` | not installed (same problem), and a Wayland compositor without a browser engine still displays nothing but a desktop shell |
| a bespoke fbdev Wayland compositor | explicitly what the mission forbids ("prefer established, maintainable components over custom display-server rewrites") |
| DRM/KMS port for DECON/DSIM + GBM/EGL + Phoc/Phosh | a **kernel project** (port the Exynos DECON/DSIM drivers to modern DRM or back-port DRM into 4.14), then a userspace follow-up; `PHOSH-ASSESSMENT.md` §2 lists the seven steps in dependency order |

**Option C — reuse the original implementation with a minimal platform
adapter.** *Chosen.* The launcher's application model, ordering, docking,
colours, geometry, icons and asset paths are compiled in from its own files; the
adapter only replaces the HTML/CSS renderer with the fbdev renderer the board
already has (the A23..A27 freestanding UI), and the browser-launched app windows
with the registry's own launch commands.

## 3. What the adapter deliberately does NOT change

* no new app, no removed app, no re-ordering (`apps.js` order, name sort);
* no new colour: the palette is parsed from `style.css` `:root`, and the tile
  compositing is `launcher.js`'s `background: <color>33; color: <color>`;
* no new geometry: grid 4 columns / `16px 8px` gaps / **56px** icons (the
  effective `--app-icon-size` inside `@media (max-width: 480px)`, measured on the
  VM's live DOM) / 11px labels / `--grid-padding` 12px, dock 80px with 56px icons
  and 20px gaps, status bar 36px (padding 16px, a literal in `status-bar.css`)
  with a 22x11 battery;
* no new icon: the grid glyphs are the registry's emoji codepoints, rasterised
  from Noto Emoji because the launcher tints them with the app's colour (a
  colour-emoji font would ignore that `color:` and be *less* faithful);
* no new background: `assets/nuxel-background.png` is decoded at runtime from
  the Fedora rootfs, with `style.css`'s own `background-color:#1a1a2e` as the
  documented fallback if the asset is missing or unreadable.

## 4. Documented presentation differences (forced by the backend)

| # | Difference | Why |
|---|---|---|
| 1 | Text is rasterised from DejaVu Sans (A27 atlas), not the browser's system font stack | no font stack without a browser; the CSS fallback list (`-apple-system, Segoe UI, Roboto, …` then `sans-serif`) has no free copy of the first five |
| 2 | Emoji glyphs are monochrome, tinted by the app colour | matches `launcher.js` exactly; the VM image has **no** emoji font installed (`fc-match emoji` -> `Noto Sans`; `google-noto-color-emoji-fonts` is not installed), so this cannot be compared 1:1 against the VM |
| 3 | The status-bar centre cluster (signal/Wi-Fi) is drawn only when a real value exists | this phone has no radio and no wlan driver; the A27 layout also forbids status-bar ink in the punch-hole band (design x 118..242) |
| 4 | Search text is entered on the console (`search <text>`) | the on-screen keyboard is a Wayland client (stevia); there is no Wayland on this kernel |
| 5 | The wallpaper is cover-fitted with bilinear sampling once at startup | the CSS does `background-size: cover` in the browser; this reproduces it (verified byte-exact against an independent reference) |
| 6 | Responsive tokens are frozen at the phone's CSS width (360px) | the phone cannot be resized, and 360 CSS px is the band the VM renders in; the media query is evaluated at build time and the applied condition is printed into `generated/nuxel-launcher.h` |
