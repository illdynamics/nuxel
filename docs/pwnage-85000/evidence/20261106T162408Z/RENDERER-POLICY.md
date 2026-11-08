# Renderer Policy — PWNAGE-85000

## Principle

The S10+ exposes Mali kbase but not a standard DRM render node to the Flatpak runtime. Software rendering was the previously verified path, but it must not be injected blindly into every app. PWNAGE-85000 introduces an explicit per-app policy with a conservative default.

| Mode | Behavior |
|---|---|
| `auto` | No renderer env injected; app/runtime chooses. Only after an on-device window/input check. |
| `software-fallback` | Injects `LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`, `MESA_LOADER_DRIVER_OVERRIDE=llvmpipe`, `GSK_RENDERER=cairo`. Default. |
| `verified-hardware` | Reserved; none promoted. No `/dev/mali0`/`--device=all` grant was added. |

## Decisions

| App | Mode | Reason |
|---|---|---|
| `org.gnome.TextEditor` | **auto** | GTK4/libadwaita; production window presented and closed; Wayland connection verified; renderer env empty |
| `io.mpv.Mpv` | software-fallback | mpv Wayland; untested runtime EGL avoided |
| `org.videolan.VLC` | software-fallback | KDE/Qt; conservative |
| `org.mozilla.firefox` | software-fallback | Gecko software path verified; GPU path unproven in sandbox |
| `app.legcord.Legcord` | software-fallback | Electron/Chromium; no DRM render node |
| `dev.vencord.Vesktop` | software-fallback | Electron/Chromium; GPU process blocks first window |
| `com.stremio.Stremio` | software-fallback | Electron; conservative |
| `org.signal.Signal` | software-fallback | Electron; conservative |

## What was not done

- No `flatpak override --filesystem=host`
- No `flatpak override --device=all`
- No `--no-sandbox`
- No setuid bwrap or namespace weakening
- No host EGL library injection into all Flatpaks
- No `LD_PRELOAD` blanket workaround
- No claim of GPU acceleration

The `/dev/fuse` permission is consumed by `xdg-document-portal`, not by the app sandbox; it is needed for the portal's own FUSE mount and does not grant application filesystem/device access.
