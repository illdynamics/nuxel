# A50 — 03: Root cause and profiles

## Frame lifecycle (measured)
The live bridge's per-second `FRAMES_OK` line gives the end-to-end changed-frame
cost (`blit_avg_ms`) and the capture-loop rate (`fps_1s`), plus
`blits`/`present_skipped`/`idle_ms`:

| Metric | Samples | Meaning |
|---|---|---|
| `blit_avg_ms` | **74 / 76 / 79** | time from loop-top (screencopy request) through ready → upscale/convert → `FBIOPAN_DISPLAY`. This is the full per-changed-frame cost. |
| `fps_1s` | 8 / 19 / 25 | capture-loop iterations in the last second (varies with compositor activity) |
| `present_skipped` vs `blits` | ~93 % skipped | damage-skip: unchanged frames are captured but **not** re-upscaled/re-panned |
| `idle_ms` | 83–571 | pacing sleep in the last second |
| `decon_pan_failed` | 0 | commits healthy |

`blit_avg_ms ≈ 74–79 ms` is the hard number. Budgets: 30 FPS = 33.3 ms,
45 = 22.2 ms, 60 = 16.7 ms. **Every continuously-changed frame costs ~4.5× the
30 FPS budget**, so the ceiling for full-screen motion is ≈ 1/0.077 ≈ **13 FPS**.
30 FPS and 60 FPS are **impossible** on the current all-software path.

## Where the time goes (per-process CPU, screen-on, locked/idle)
`/proc/<pid>/stat` utime+stime deltas over ~50 s vs `/proc/stat` aggregate:

| Process | % of one core | Role in the path |
|---|---|---|
| phoc (pixman) | 31.4 % | software-composites the 720×1520 scene |
| WebKitWebProcess | 28.5 % | JS/layout/paint of the launcher |
| nuxel-wl-fb | 21.4 % | screencopy + 2× upscale + XRGB→ABGR convert + panel write + FBIOPAN |
| nuxel-pwa-host | 5.0 % | WebKitGTK host |
| **Total** | **~86 % of one core** | cost of keeping the panel on with a mostly-static lockscreen |

No GPU stage exists; all three hot stages are CPU. The 74–79 ms/frame is split
roughly between **compositor software render**, **screencopy/upscale/convert**,
and **WebKit software paint** — all CPU.

## Bottleneck verdict (evidence-backed)
The bottleneck is the **software compositor + wlr-screencopy + CPU
format-conversion/upscale + fbdev commit** path, exactly as hypothesised in the
prompt. The PWA UI is **not** the dominant cost: WebKit is only ~1/3 of the
hot path, and the bridge's damage-skip already removes most redundant work
(93 % of captured frames are skipped). The framebuffer write is fixed
1440×3040×4 = 17.5 MB/frame regardless of compositor resolution.

## Optimisation levers, ranked by measured payoff vs risk
1. **NEON inner-loop for the 2× upscale + XRGB→ABGR convert** (nuxel-wl-fb).
   Directly attacks ~21 % of the hot path; could plausibly shave 10–15 ms/frame.
   **Blocked in this mission**: the live source is uncommitted, so a safe
   incremental rebuild is impossible without first recovering that exact source
   (it is newer than repo a34 and adds damage-skip/screen-off capture-stop).
2. **Remove `backdrop-filter: blur()`** on the status bar (12 px) and Quick
   Settings shade (20 px) — see `status-bar.css:10,193`. Software-rendered
   backdrop blur is very expensive every frame those surfaces are visible/
   animating. Preserve look with a semi-opaque solid background. Needs an
   owner-verified visual A/B; not deployed unattended.
3. **Resize oversized assets**: nav-button PNGs are 1.0–1.14 MB each and the
   dock art 0.9 MB, for a 360 px CSS viewport. Resize to effective display size
   (keep originals). Needs visual verification; not deployed unattended.
4. **Resolution A/B (720 → 540)** — only if the owner accepts reduced
   readability; see `02-…`.
5. **`void grid.offsetWidth` (launcher.js:721)** — audited: it is a forced
   synchronous layout, but **once per completed swipe** (touch-end), not
   per-move; impact is small. Correct fix is double-rAF transition restart,
   not blind removal. Low priority.

## Touch → glass note
No synthetic touch was injected and no high-frame-rate camera was available.
Software timestamps alone cannot prove glass photon latency. Touch-to-glass
latency is therefore **not claimed** here; the per-frame presentation cost
(74–79 ms) is the software-visible component of it.
