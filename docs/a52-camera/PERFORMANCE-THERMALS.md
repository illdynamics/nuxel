# A52 Performance & Thermals

## Measured (device, read-only)

| Metric | Value | When |
|---|---|---|
| Thermal zones | 21.3–27.0 °C | idle, screen on, camera closed |
| Load average | 11.88 | pre-existing; `exynos-pcie` link-retraining loop in dmesg (not camera) |
| Camera processes | none running | no camera service, no PipeWire/portal |

## Not measurable (honest)

- Camera cold-start → first **real** frame: **not measured** (no capture path).
- Preview FPS / frame interval / dropped frames: **not measured**.
- Shutter-to-photo-written P50/P95: **not measured**.
- Camera-open temperature rise: **not measured** (no streaming possible).

These are deliberately left UNVERIFIED rather than filled with synthetic numbers.

## Design commitments (enforced in code)

- No busy-poll of a missing camera (`camera.status` gates activation; no
  perpetual `videotestsrc`).
- Camera closed on `visibilitychange`/`pagehide`/lock; recording auto-stops on lock.
- Bounded payloads and lazy thumbnails avoid loading all images as data URLs.
- No regression to A50 Home/swipe performance is expected (no display-pipeline
  changes were made).
