# Flatpak Launch Timeline — PWNAGE-85000

Production path: Home → `POST /api/v1/apps/exec` → provider `launch_argv()` → `systemd-run --no-block --uid=nuxel` → `flatpak run` → bwrap → app → Wayland surface.

| Marker | Before | After | Evidence |
|---|---:|---:|---|
| T0 UI tap / API request | — | — | automation |
| T1 bridge receives request | — | — | bridge journal |
| T2 app-id/installed lookup | ≈16 s (user inventory via transient unit) | **0.3 ms warm / 195.5 ms cold** | provider measurement |
| T3 transient unit requested | — | — | `timing_ms` |
| T4 unit accepted | — | **36–40 ms total request→accepted** | API response |
| T5 Flatpak CLI starts | — | included in 2.6 s | `/proc` |
| T6 bwrap namespace setup | — | included | `nuxel-bwrap-compat` |
| T7 D-Bus proxy/document portal | **~15 s NoReply** | **no error** | flatpak stderr |
| T8 runtime entry | — | included | flatpak run |
| T9 app process starts | not reached quickly | **2.329–2.872 s** (p50 2.596) | `/proc/*/comm` |
| T10 Wayland surface | — | **window present** | close action title |
| T11 first visible change | — | **~2.4 s** (one instrumented run) | screencopy FNV change |
| T12 first input | not measured | **NOT_TESTED** | owner physical test |

## Samples

Provider lookup (`/api/v1/flatpak/launch`): `0.538, 0.020, 0.015, 0.017, 0.693 s` → p50 0.020 s, p95 0.662 s.  
Sandbox init (`--command=true`, as nuxel): `0.795, 0.728, 0.710, 0.687, 0.759 s` → p50 0.728 s, p95 0.788 s.  
App process start (production API): `2.329, 2.445, 2.596, 2.855, 2.872 s` → p50 2.596 s, p95 2.869 s.  
API accepted: `36.157, 39.895 ms`.  
Close: `56 ms`.

## Second apps

`flatpak run --command=true` as nuxel, 3 runs each:

| App | Runs (s) | Result |
|---|---|---|
| `org.gnome.TextEditor` | 0.645, 0.628, 0.722 | `rc=0` |
| `io.mpv.Mpv` | 0.531, 0.530, 0.444 | `rc=0` |
| `org.videolan.VLC` | 0.583, 0.503, 0.579 | `rc=0` |
| `org.mozilla.firefox` | 0.545, 0.545, 0.500 | `rc=0` |

No document-portal or a11y `NoReply` errors remained. mpv production launch was accepted in 35.6 ms; it exited without media (expected). VLC production launch was blocked by the then-active session lock (`session_locked`), not by Flatpak.
