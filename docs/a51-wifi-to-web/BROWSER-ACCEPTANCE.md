# A51 — Browser Acceptance (fallback path)

## Chosen fallback: Epiphany (GNOME Web) — WebKitGTK native browser

Ladybird is blocked (see LADYBIRD-AARCH64-BUILD.md), so the guaranteed practical
path is a genuine WebKitGTK browser. The device already has the full WebKitGTK
runtime (`webkit2gtk4.1 2.52.5`, `javascriptcoregtk4.1`, GTK3/GTK4, Wayland,
Mesa-software, ca-certificates, fontconfig). **Epiphany itself is not installed**
and installing it requires the network that the Wi-Fi fix is meant to provide —
a chicken-and-egg resolved by the owner connecting Wi-Fi first.

## Exact install (run only AFTER Wi-Fi is joined and DNS/HTTPS verified)
```
dnf -y install epiphany      # aarch64, from the signed Fedora 43 repos
```
View the exact transaction first; exclude kernel/firmware/bootloader/critical
display-stack packages. Epiphany is the maintained GNOME WebKitGTK browser and
the correct native-browser fallback.

## Acceptance checklist (to record here once Wi-Fi + install complete)
1. Launch `epiphany` under the session env
   (`XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 GDK_BACKEND=wayland
   LIBGL_ALWAYS_SOFTWARE=1 GSK_RENDERER=cairo`).
2. Load `https://example.org` with valid TLS (no `--ignore-certificate-errors`),
   then a second real site; follow a redirect.
3. Tap the address bar → **Stevia OSK types** → Enter navigates → Back/Home/close
   work; no focus trap; no window hidden under an overlay; bottom dock not drawn
   over the browser.
4. Scroll, pinch/pan, and read are usable on the tall screen; record any
   software-rendering limitations honestly.
5. Register the `.desktop` entry in Nuxel Home/Browser shortcut; keep it the
   default only with deliberate owner preference; keep any partial Ladybird as
   `Experimental`.

## Do not mistake these for a native browser
- A PWA browser view (`pwa/nuxel-apps/browser/`) inside `nuxel-pwa-host` is a
  WebKitGTK-embedded page, **not** a separately installable browser with its own
  window/lifecycle; it is not equivalent to Epiphany and is not claimed as such.
- `curl` success is network proof, not graphical-browser proof.

## Current status
WebKitGTK rendering is already proven on the device (the Home screen is a live
WebKitGTK view). Browser **install/launch is pending network**, which is pending
the owner entering the Wi-Fi password. This is reported as a blocker, not a pass.
