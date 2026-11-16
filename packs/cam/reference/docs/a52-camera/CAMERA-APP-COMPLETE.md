# A52 Camera App — Completion Status

## Implemented (real frontend, not a mockup)

| Feature | Status | Notes |
|---|---|---|
| Live preview | ✅ code-complete | `getUserMedia` → `<video>`; honest error placeholder on failure |
| Permission flow | ✅ | `permissions.request camera:capture`; deny → no sensor, `PERMISSION_DENIED` |
| Camera-active indicator | ✅ | visible during preview/recording |
| Photo capture | ✅ | `canvas.toBlob` (bounded) → bridge `camera.capture` → real `.jpg` file |
| Video recording | ✅ | `MediaRecorder` + timer + stop; saves `.webm`/`.mp4` by actual mime |
| Front/rear switch | ✅ fixed | device persisted before teardown; awaits release before opening new device |
| Photo/Video mode | ✅ fixed | distinct behaviours (was icon-only) |
| Resolution | ✅ fixed | conservative 1280×720 ideal (no 1440×3120 screen-resolution assumption) |
| Thumbnail | ✅ | opens Photos; no stale data-URL cache |
| Capture timer 0/3/10 | ⚠️ partial | structure present; timer countdown UI to be finalised |
| Flash/torch | ❌ not supported | no verified LED/flash interface wired; not faked |
| Focus/tap-to-focus | ❌ not supported | no standard V4L2/libcamera controls available; shown unavailable, not decorative |
| Zoom / optical | ❌ not supported | never advertised (sensor blocked) |

## Honest hardware state

The S10+ rear/front sensors are **enumerated** at the driver level but **capture
is blocked** (`VIDIOC_S_FMT → ENOTTY`). The app therefore:

- defaults to an honest unavailable banner (`NO_CAMERA` / "enumerated but not
  verified") on the real phone,
- never substitutes a synthetic test pattern as a real camera,
- surfaces `NO_CAMERA`, `PERMISSION_DENIED`, `CAMERA_BUSY`, `LOW_STORAGE`,
  `DRIVER_UNAVAILABLE` error states with recovery guidance.

## Not supported (and not faked)

Flash, tap-to-focus/exposure, optical zoom, HDR, stabilization, 4K/60 FPS. Each
unsupported lens is truthfully `NOT_AVAILABLE`; no fake working switches.

## Proof

- Offline suite: `tests/a52/test-camera-frontend.py` (17 checks) — localStorage
  removed, 1440×3120 removed, facingMode persisted, MediaRecorder present,
  file-backed capture, honest states.
- No physical preview/still/video claim is made (hardware blocked). See
  `TEST-RESULTS.md` for the owner-validation gates that remain.
