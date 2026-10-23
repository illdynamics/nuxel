# A51 — Native GUI Compatibility (Wayland / GTK / Qt / WebKitGTK)

## Live session facts
- Compositor: **phoc 0.54.0** running as **root**, `XDG_RUNTIME_DIR=/run/nuxel-wayland`,
  socket `wayland-0`, `XDG_SESSION_TYPE=wayland`.
- Session script (`/usr/lib/nuxel/nuxel-session.sh`) forces software rendering
  (no DRM/EGL device on the 4.14 kernel): `GDK_BACKEND=wayland`,
  `WEBKIT_DISABLE_COMPOSITING_MODE=1`, `LIBGL_ALWAYS_SOFTWARE=1`, `GSK_RENDERER=cairo`.
- Native OSK is Stevia (`phosh-osk-stevia`, via `dbus-run-session`); dock is
  `nuxel-navdock`. The launcher itself is a WebKitGTK view (`nuxel-pwa-host`).

## Native app launch (verified)
`adwaita-1-demo` (a genuine AArch64 GTK4 Wayland demo app, already installed)
launched under the live session and stayed running until a bounded `timeout 8`
killed it (rc 143 = SIGTERM, i.e. it did **not** crash or exit with a Wayland
error). This proves a separate native GTK4 app opens a window on the physical
display under Phoc with the correct env:

```
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
XDG_SESSION_TYPE=wayland GDK_BACKEND=wayland LIBGL_ALWAYS_SOFTWARE=1 \
GSK_RENDERER=cairo timeout 8 adwaita-1-demo   # rc=143 (ran until timeout)
```

## Runtime inventory
| Present (aarch64) | Absent |
|---|---|
| gtk3 3.24.52, gtk4 4.20.4, gtk4-launch/gtk-launch, adwaita-1-demo | qt6-qtbase / qt6-qtwayland / qt5-qtwayland |
| webkit2gtk4.1 2.52.5, webkitgtk6.0 2.52.5, javascriptcoregtk4.1/6.0 | epiphany (GNOME Web) |
| libwayland-client/server/cursor/egl, mesa-libEGL/GL/gbm, mesa-dri-drivers | weston, sway |
| xorg-x11-server-Xwayland, ca-certificates, fontconfig | — |

**Qt is not installed.** GTK3/GTK4 and WebKitGTK are fully usable; a Qt6 app
(Ladybird's frontend) cannot run until Qt6 is installed — which itself needs a
working network (see LADYBIRD-AARCH64-BUILD.md).

## Launcher / input integration
A reusable native-app launcher must run with exactly the session env above
(`XDG_RUNTIME_DIR=/run/nuxel-wayland`, `WAYLAND_DISPLAY=wayland-0`,
`GDK_BACKEND=wayland`, software GL) as the session user (root on this image),
without globally overriding `QT_QPA_PLATFORM` or hardcoding root's runtime dir.
Touch/keyboard reuse the existing touch-arm + Stevia OSK pipeline; Back dismisses
the OSK first, Home returns Home, and no launcher window may draw over full-screen
apps. This launcher is the next deploy step once a native app/browser is
installed (blocked on network for package installation, see below).
