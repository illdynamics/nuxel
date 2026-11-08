# Flatpak App Matrix — live, 2026-11-06

| App ID | Name | Version | Branch | Arch | Origin | Scope | Runtime |
|---|---|---|---:|---|---|---|---|
| `org.gnome.TextEditor` | Text Editor | 51.0 | stable | aarch64 | flathub | system | `org.gnome.Platform/aarch64/51` |
| `io.mpv.Mpv` | mpv | 0.41.0 | stable | aarch64 | flathub | system | `org.freedesktop.Platform/aarch64/26.08` |
| `org.videolan.VLC` | VLC | 3.0.24 | stable | aarch64 | flathub | system | `org.kde.Platform/aarch64/5.15-25.08` |
| `org.mozilla.firefox` | Firefox | 159.0 | stable | aarch64 | flathub | system | `org.freedesktop.Platform/aarch64/25.08` |
| `app.legcord.Legcord` | Legcord | 1.3.1 | stable | aarch64 | flathub | system | `org.freedesktop.Platform/aarch64/26.08` |
| `dev.vencord.Vesktop` | Vesktop | 1.6.8 | stable | aarch64 | flathub | system | `org.freedesktop.Platform/aarch64/26.08` |
| `com.stremio.Stremio` | Stremio | 1.2.2 | stable | aarch64 | flathub | system | `org.gnome.Platform/aarch64/50` |
| `org.signal.Signal` | Signal Desktop | 8.33.0 | stable | aarch64 | flathub | system | `org.freedesktop.Platform/aarch64/26.08` |

Flatpak 1.16.6. No user-scope apps. No system or per-app overrides.

## Tested

| App | Sandbox init | Renderer | Window | CPU/RSS | Notes |
|---|---:|---|---|---|---|
| TextEditor | 0.687–0.795 s | auto | **present**, title `New Document (Draft) - Text Editor` | RSS ≈188 MB at 1 s, CPU 32–44% during GTK startup | production API, close 56 ms |
| mpv | 0.444–0.531 s | software-fallback | exited without media | — | production request accepted 35.6 ms |
| VLC | 0.503–0.583 s | software-fallback | not tested (session locked) | — | sandbox init clean |
| Firefox | 0.500–0.545 s | software-fallback | not tested | — | sandbox init clean |
| Legcord/Vesktop/Signal/Stremio | not launched | software-fallback | not tested | — | no credentials touched |

Permissions were inspected, not changed. TextEditor upstream permissions include `devices=dri` and `filesystems=host`; mpv upstream includes `devices=all`. These are pre-existing Flathub manifests and were not modified by PWNAGE-85000. `flatpak override --system --show org.gnome.TextEditor` is empty.
