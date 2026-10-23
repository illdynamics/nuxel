# NUXEL A59 — BASELINE AND ROOT CAUSES

Generated: 2026-10-22 (Europe/Amsterdam), by GPT-5.6 Sol (A59 agent launcher).

## Target identity (verified live, read-only)
- Samsung Galaxy S10+ SM-G975F `beyond2lte`, Exynos 9820.
- Fedora Linux 43 (Forty Three), aarch64, kernel `4.14.253` (#15 SMP PREEMPT).
- USB CDC-ACM live console: `/dev/cu.usbmodem201`, VID 0x18d1, PID 0x4ee7,
  serial `NUXEL-S10PLUS-0001`. Reachable root shell + /dev/kmsg mirror.
- Session is NOT logind: custom seatd + `nuxel-wayland.service` (phoc headless
  + pixman, output HEADLESS-1 720x1520 scale 2 -> 360 CSS px).
- Graphical stack: `phoc` (0.54.0) -> `nuxel-pwa-host` (WebKitGTK host) ->
  `nuxel-navdock` (native layer-shell Back/Home/Recents) + `phosh-osk-stevia`
  (OSK) + `nuxel-wl-fb` (wlr-screencopy -> /dev/fb0) + `nuxel-button-manager`
  (physical power/volume/assistant) + `nuxel-bridge`/`nuxel-portal`/`nuxel-http-bridge`.

## Current deployed source state (not assumed from v0.6.3-beta)
- Git HEAD: `00422fb` on branch `nuxel/A55-pwnage-4000`.
- Deployed binaries under `/usr/lib/nuxel/` include `nuxel-pwa-host`,
  `nuxel-navdock`, `nuxel-wl-fb`, `nuxel-button-manager` (Oct 21 08:37).
- Native browser source `shell/nuxel-browser-native/nuxel_browser_native.py`
  deployed to `/usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py`
  (Oct 22 16:26) — GTK3 + WebKit2 4.1 top-level WebView.
- Native camera source `shell/nuxel-camera-native/nuxel_camera_native.py`
  deployed to `/usr/lib/nuxel/nuxel-camera-native/nuxel_camera_native.py`
  (Oct 22 15:15) — GTK4 + libadwaita honest status card.
- Canonical app registry: `pwa/nuxel-common/app-registry.json` (v4), consumed by
  `pwa/nuxel-home/js/apps.js`, `shell/nuxel-home-native/nuxel_home/app_registry.json`,
  and `services/nuxel-bridge/src/api.py` (HTTP /api/v1/apps/*).

## Network (Phase 1) — PASS
- wlan0 ACTIVE, SSID `Ziggo5501109`, IPv4 192.168.178.167/24, default route via
  192.168.178.1, DNS 62.179.104.196 / 213.46.228.196 / IPv6.
- On-device validated TLS HTTPS: `https://www.google.nl` HTTP/2 200, and
  `https://www.eff.org` HTTP/2 200; `ssl_verify_result=0` (certificate verified).
- Clock correct (Europe/Amsterdam CEST); NTP service inactive but time accurate.
- Root cause for any residual browser-only failure is therefore NOT L3/L4/network.

## Packages (Phases 3/4) — critical constraint
- Installed: gtk4 4.20.4, gtk3 3.24.52, webkit2gtk4.1 2.52.5, webkitgtk6.0 2.52.5,
  python3 + PyGObject (Gtk3/Gtk4/Adw/WebKit2-4.1/WebKit-6.0 typelibs present).
- NOT installed: snapshot, firefox, chromium, epiphany, ladybird, flatpak,
  libcamera, pipewire, wireplumber, gstreamer1-plugins-bad-free.
- **`dnf`/`dnf5`/`microdnf`/`yum`/`pkcon` are NOT installed.** Only `/usr/sbin/rpm`
  and `/etc/yum.repos.d/*.repo` exist. 455 RPMs total. This is the binding
  constraint for installing external browsers/camera via the normal package path.

## Storage / RAM
- Rootfs `/dev/sda31` 3.9G, 1.7G free (55% used). RAM 7420M, ~6.1G available. No swap.

## Root causes identified (to be addressed in later phases)
1. **Browser is a blocked iframe PWA, not a top-level browser.** The deployed
   `org.nuxel.Browser` surface (`/usr/share/nuxel/pwa/nuxel-apps/browser/index.html`)
   is an `<iframe sandbox=...>` page that BLOCKS external navigation by default.
   A genuine top-level WebKitGTK browser exists at `/usr/lib/nuxel/nuxel-browser-native/`
   but is NOT registered in the app drawer/registry.
2. **Native app launch is a stub.** `pwa/nuxel-home/js/app.js` `_launchNative()`
   only shows a "not implemented yet" toast. The bridge resolves native descriptors
   (`exec` + `native_binary`) but the PWA host never actually execs them (only the
   Terminal has a spawn path).
3. **Home button is launcher-DOM-only.** `action home` -> JS `nuxel.home()` resets
   the launcher/iframes, but external native GTK windows (browser/camera/Firefox)
   are separate Wayland clients that a DOM handler cannot lower/focus.
4. **App drawer omits authored native apps.** Native browser/camera are deployed
   on disk but absent from the registry/apps.js, so they are invisible.
5. **Camera "No native camera app installed".** The message conflates
   "application not installed" with "Exynos ISP image pipeline not ready". Both the
   native Snapshot (not installed) and the custom camera (deployed but unregistered)
   need to be separated from the hardware-pipeline blocker.

## Evidence artifacts (Phase 0)
- `docs/a59/BASELINE-AND-ROOT-CAUSES.md` (this file).
- Live screenshot of Nuxel Home: captured via `nuxel-wl-snapshot`
  (720x1520, `/tmp/a59-home.ppm` on device; local PNG `.scratch/a59/a59-home.png`).
- Service list, process list, network state, package state captured in this session.

## Rollback discipline
- Per-target backups `.nuxel-rollback` and `tools/beta/rollback.sh` available.
- All changes below are staged files first, sha256-verified, atomically installed,
  and rolled back on any verification failure.
