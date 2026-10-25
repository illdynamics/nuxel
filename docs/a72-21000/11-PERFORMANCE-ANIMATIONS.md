# NUXEL A72 / 21000 — 11-PERFORMANCE-ANIMATIONS

## Baseline (measured live, not fabricated)
- load average 14.13/13.12/12.70; memory 7420 MB total / ~854 used / 0 swap.
- CPU snapshot: phoc 14.1%, nuxel-pwa-host 11.6%, WebKitWebProcess 26.7%,
  nuxel-wl-fb 8.9% (software-rendered WebKitGTK/Phoc path, no DRM/EGL).
- Thermal: BIG 62°C, MID/LITTLE 53°C, battery 36°C (normal).

## Plan
- Capture p50/p95/p99 frame interval + input-to-screen for app drawer open/launch,
  browser HTTPS scroll, workspace swipe, quick settings, Maps pan/zoom before/after.
- Optimize only measurable bottlenecks (full-frame copies, layout thrash, blocking
  DBus/HTTP in the UI loop); no placebo knobs, no Mesa/kernel change.
- Preserve existing restrained CSS animations (~0.20–0.22 s cubic-bezier) and
  `prefers-reduced-motion`; keep penguin pixel-art and the 19000/20000 icon placements.
- A real before/after table requires an owner touch-interactive session + frame-capture;
  nothing here is fabricated.
