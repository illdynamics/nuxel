# 01 — Visual diagnosis

## Owner reference photo
`./evidence/launcher-regression-reference.jpg` is **absent from the repository**
and was not found on the host. The owner's described broken state is reproduced
instead from the measured live facts below. (The physical on-device evidence and
an on-device framebuffer capture are used as the source of truth.)

## Measured live viewport / renderer
- WebKitGTK viewport: `w=360 h=760 dpr=2` (reported by the injected input diag).
- `nuxel-wl-fb` output pipeline: `out=720x1520 src=720x1520 scale=2 panel=1440x3040`.
- Wallpaper decode: `assets/nuxel-background.png decoded=1 natural=941x1672`.

## Root-cause evidence
| Check | Broken (before) | Fixed (after) |
|---|---|---|
| `/usr/share/nuxel/nuxel-home/css/launcher.css` size/hash | `0` / `e3b0c442…` | `12764` / `9d56a005…` |
| HTTP `GET /pwa/nuxel-home/css/launcher.css` | `200 0` | `200 12764` |
| `index.html` HTTP | `200 13339` | `200 13339` |
| Status bar overlap | — | `STATUSBAR_OVERLAP_CHECK cells=2 overlaps=none` |
| Lockscreen unlock | `locked=1 visible=1` (stuck) | `unlock:complete locked=0 visible=0` |

`launcher.css` contains the only rules for `.app-list` grid columns,
`.app-icon` sizing, `.system-monitor` compact layout and `.dock` placement.
With it empty, WebKit rendered the fallback: block-flow app list (one column),
unbounded `<img>` intrinsic sizes (512 px icons), unstyled telemetry text, and an
unstyled dock background (the large dark circular `button-middle` artwork).

## Classification
`DEPLOYMENT_MISMATCH` / `STALE_UI_BUNDLE` — a mixed deploy state: the A63 runtime
apply installed `index.html`, `manifest.json` and `sw.js` (`v34-a63-runtime`), then
failed at `launcher.css` (`PREV=e3b0c442…`, rollback) and aborted before the rest
of the CSS/JS group. The on-disk `launcher.css` had been empty since Oct 14 and was
previously masked by the in-memory/cached page; the A63 service-worker upgrade
(`skipWaiting`+`clients.claim`+cache purge) surfaced it.

## Non-launcher finding (documented, not expanded)
Kernel-side TrustZone/RPMB tasks (`tz_iwsock`, `scsi_srpmb_work`, `ree_time`) show
D-state hung-task warnings and contribute to a high load average (~11–13). This is
a pre-existing kernel/vendor issue, out of scope for a UI-only repair (no flashing
allowed), and is recorded here as a separate observation.
