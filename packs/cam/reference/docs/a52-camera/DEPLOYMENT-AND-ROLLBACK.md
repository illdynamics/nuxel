# A52 Deployment & Rollback

## What changed (branch `nuxel/A52-penguin-camera`)

| Path | Change |
|---|---|
| `services/nuxel-bridge/src/media_store.py` | NEW — file-backed media store |
| `services/nuxel-bridge/src/bridge.py` | camera D-Bus verbs (`CameraStatus/ListCaptures/Capture/Open/Delete`) |
| `services/nuxel-bridge/src/api.py` | camera verb map + arg builders; honest `CameraCapture` mock |
| `shell/nuxel-camera-portal/nuxel_camera_portal.py` | renamed to private `org.nuxel.Camera`; `IsCameraPresent`; synthetic opt-in |
| `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service` | no `--synthetic` default |
| `pwa/nuxel-apps/camera-gallery/js/camera.js` | full rewrite (file-backed, facingMode fix, MediaRecorder) |
| `pwa/nuxel-apps/camera-gallery/index.html`, `css/camera.css`, `manifest.json` | UI + verb set + scope fix |
| `pwa/nuxel-apps/photos/js/photos.js`, `index.html`, `css/photos.css`, `manifest.json` | file-backed gallery |
| `configs/nuxel/camera/camera.json` | front sensor s5k3j1; private broker contract; synthetic opt-in |
| `tools/s10plus/a52/nuxel-v4l2-probe.py`, `nuxel-v4l2-capture-test.py` | NEW — device diagnostics |
| `tests/a52/*`, `services/nuxel-bridge/test-media-store.py`, `test-camera-bridge.py` | NEW — offline suite |
| `docs/a52-camera/*` | NEW — evidence/analysis/report |

## Live deployment (safe, userspace-only, incremental)

Deployment requires owner authorization and a maintenance window; **do not** do
it unattended. Order and gates:

1. **Gate 0** — snapshot: record running units, file hashes, and current media
   (none exists yet). Keep USB console reachable.
2. **Gate 1** — deploy `media_store.py` + updated `bridge.py`/`api.py` to
   `/usr/lib/nuxel/nuxel-bridge/`; restart **only** `nuxel-bridge` and
   `nuxel-http-bridge`; `systemctl status` + `journalctl -u nuxel-bridge`.
3. **Gate 2** — deploy the renamed portal backend + unit; do **not** enable it on
   the phone (no capture backend to serve); verify `org.freedesktop.portal.Camera`
   is NOT claimed.
4. **Gate 3** — deploy the Camera/Photos PWA trees to the static webroot; verify
   the app registry still resolves both apps once.
5. **Gate 4** — manual smoke: Camera opens with an honest `NO_CAMERA` banner;
   Photos opens empty and shows the honest empty state; no bridge regressions
   (Home/status bar/Wi-Fi still work).
6. **Gate 5** — owner-assisted `capture` smoke with a USB-UVC webcam if desired,
   **labelled `usb-uvc`**, never reported as the integrated S10+ camera.

## Rollback

Each step is atomic (file replace). Restore the pre-deploy file backups and
`systemctl restart nuxel-bridge nuxel-http-bridge`. The media store is additive:
no existing media is deleted by any of these changes, and the old localStorage
photo keys are left untouched (migration is a separate owner-approved step).

Exact per-file rollback = restore the prior SHA-256 from the pre-deploy snapshot
(recorded at Gate 0), then restart the affected service. No reboot is required
for any of these userspace changes; a reboot is only for the persistence gate and
requires separate explicit owner authorization.

## Hash / identity recording

At Gate 0, record: `git rev-parse HEAD` of the deployed tree, `sha256sum` of each
installed file, `systemctl list-units --type=service --state=running`, and the
USB console node. This branch's HEAD hash is the rollback reference.
