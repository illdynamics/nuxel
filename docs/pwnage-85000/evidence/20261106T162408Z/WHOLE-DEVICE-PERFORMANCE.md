# Whole-Device Performance — PWNAGE-85000

## Bridge / launch path

| Metric | Before | After |
|---|---:|---:|
| `list_installed()` cold | ≈16 s (user scope transient) | **195.5 ms** |
| `list_installed()` cached | — | **0.0 ms** |
| `is_installed()` | ≈16 s | **0.3 ms** |
| provider launch endpoint p50 | ≈16 s | **0.020 s** (p95 0.662 s) |
| user-scope flatpak list jobs | 5 / ~20 s | **1–2 / 2 min** |
| bridge API CPU | 13.1% | **0.0% after 10 s screen-off indicator cache** |
| bridge helper CPU | 0.7% | **0.3%** |
| indicator projection scan while off | every 1 Hz request | **10 s TTL** |

## Frame / compositor

The launcher orientation reflow re-entered its own `resize` listener. Each pass called `NuxelHost.action('reset-zoom')`, which wrote `repaint` to `/run/nuxel-wl-fb.cmd`, forcing full-frame repaints and overwriting the display state document. With the guard:

| Metric | Before | After |
|---|---:|---:|
| `repaint` writes from `nuxel-pwa-host` | **32 / 6 s** | **0 / 6 s** |
| WebKit `ThreadedCompositor` thread (screen off) | **74.67%** | **~10%** |
| WebKit main (screen off) | ~18–20% | **~2.7% host + ~10% WebKit total** |
| phoc (screen off) | — | **1.3%** |
| `nuxel-wl-fb` (screen off) | — | **0.1%** |
| total four processes (screen off) | ≈95–100% | **≈14%** |
| total four processes (screen on idle) | — | **≈17%** |
| wl-fb state while off | `REPAINT_REQUEST` | **`DISPLAY_SLEEP display=off capture=stopped`** |

Final screen-on frame state: `FRAMES_OK`, `failures=0`, `decon_pan_failed=0`, `blit_avg_ms=4`, `pan_avg_ms=9`, `present_skipped=69` in the sample. Damage skipping and screen-off capture-stop are preserved; single `/dev/fb0` owner remains `nuxel-wl-fb`.

## Memory / thermal / idle

| Metric | Value |
|---|---:|
| Memory (screen off) | 1.3 GiB used / 5.9 GiB available / 0 swap |
| Thermal zones (screen off) | 43/41/40 °C (0/1/2), full range 26.6–43.0 °C |
| Battery | 11%, discharging |
| Prewarm | one-shot at boot, exited success, no resident memory |
| nuxel-perf-tune | inactive; no tuning applied |

## Residual

The lockscreen indicator class still polls `/api/v1/system/indicators` about once per second while the panel is off (6 requests / 5 s). The server-side projection is cached for 10 s while the panel is off, so bridge CPU is ~0%. The new `lockscreen-indicators.js` stops the timer on `display_off:true`; it is deployed, but the currently running locked page needs a Home reload/reboot to load it. WebKit therefore still spends ~10% on the old client-side poll. The repaint storm and the 75% compositor loop are gone; the remaining poll is a follow-up requiring a host-side display-off event or a guaranteed `body.display-off` propagation. No screen-off thermal or memory regression was observed.
