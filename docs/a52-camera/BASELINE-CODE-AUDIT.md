# A52 Baseline Code Audit

Audit of the historical defects listed in the mission spec, against the CURRENT repository
(branch `nuxel/A52-penguin-camera`, base commit 9fe0ebc). Each item records: observed state,
impact, owner, safest change, regression test.

## 1. `getUserMedia` + canvas→dataURL + `localStorage` photo database — CONFIRMED PRESENT

- **File:** `pwa/nuxel-apps/camera-gallery/js/camera.js` (`_capturePhoto`, `_saveGallery`, `_loadGallery`).
- **Observed:** captures encode JPEG to a `dataURL`, store the full image in `this.photos`,
  persist to `localStorage['nuxel-camera-photos']`, and trim to 50 photos; on quota error it
  `slice(0, 10)` and retries (silently discarding older photos).
- **Impact:** browser storage quota is the authoritative photo database; media is silently lost.
- **Owner:** Camera app + bridge (`camera.capture`/`camera.list-captures` verbs).
- **Fix:** replace with file-backed storage (bridge writes real JPEG files under
  `~/Pictures/Nuxel Camera/`; app never sends base64 arrays). Implemented this cycle.
- **Test:** `services/nuxel-bridge/test-media-store.py` (atomic write, no quota loss, decode verification).

## 2. Front/rear toggle loses `facingMode` — CONFIRMED PRESENT

- **File:** `camera.js` `switch-camera` handler.
- **Observed:** calls `_stopCamera()` **before** reading `this.stream?.getVideoTracks()[0]?.getSettings()`,
  so `currentFacing` is always `undefined` and `newFacing` is always `'user'`.
- **Impact:** switch always re-selects the same camera; never actually toggles.
- **Fix:** persist selected device independently of stream lifetime; enumerate devices after
  permission; read `facingMode`/deviceId before teardown; await release before opening new device.
- **Test:** `tests/a52/test-camera-frontend.py` (device selection persists independently of stream).

## 3. Photo/Video mode with no video capture — CONFIRMED PRESENT

- **File:** `camera.js` (`_toggleMode`, capture-button handler).
- **Observed:** mode toggles the button icon; capture handler runs only `_capturePhoto()` in
  `photo` mode and does nothing in `video` mode. No `MediaRecorder`, no recording timer, no stop.
- **Fix:** implement `MediaRecorder`-based video capture (bounded, honest) with recording state,
  timer, stop, and file persistence via bridge.
- **Test:** `tests/a52/test-camera-frontend.py` (MediaRecorder present; no icon-only toggle).

## 4. `1440x3120` ideal dimensions — CONFIRMED PRESENT

- **File:** `camera.js` `_startCamera` constraints.
- **Observed:** uses `width:{ideal:1440}, height:{ideal:3120}` — screen resolution, not sensor modes.
- **Fix:** use conservative defaults (1280×720) with no fake claim of sensor capability; enumerate
  `mediaDevices.getCapabilities()` when available; never assume sensor resolution.
- **Test:** `tests/a52/test-camera-frontend.py` (1280×720 conservative ideal, not 1440×3120).

## 5. Non-standard "camera portal" on `org.freedesktop.portal.Camera` — CONFIRMED PRESENT

- **File:** `shell/nuxel-camera-portal/nuxel_camera_portal.py`.
- **Observed:** claims `org.freedesktop.portal.Camera` with methods `AvailableCameras`, `RunCamera`,
  `Release`, `Subscribe`, `Unsubscribe` — NOT the standard `AccessCamera(options)→request handle`,
  `OpenPipeWireRemote(options)→Unix FD`, `IsCameraPresent`, `version`.
- **Impact:** hijacks the standard D-Bus name with incompatible methods; standard portal clients
  would break; the real portal (if ever installed) would collide.
- **Fix:** rename to a private Nuxel broker `org.nuxel.Camera` with narrowly-scoped capture verbs;
  never claim the freedesktop portal name. Implemented this cycle.
- **Test:** `tests/a52/test-portal-contract.py` (private bus name, IsCameraPresent, no freedesktop collision).

## 6. Synthetic default in the camera portal — CONFIRMED PRESENT

- **File:** `nuxel_camera_portal.py` (`main`, systemd unit `ExecStart=… --synthetic`).
- **Observed:** defaults to `--synthetic` (videotestsrc) unless `--hardware`; the systemd unit
  hard-codes `--synthetic`.
- **Impact:** device-visible default would silently show colour bars as a "camera".
- **Fix:** broker reports honest `NO_CAMERA` when no capture device exists; synthetic test source
  only behind an explicit `--test-source` flag and always labelled. Implemented this cycle.

## 7. Firmware names treated as facts — CONFIRMED (policy) / AUDITED (device)

- **File:** `configs/nuxel/camera/camera.json` `firmware_blobs.candidates`, `expected_sensors`.
- **Observed:** policy lists `s5k2l4_setfile.bin` etc. as *hints*, and correctly marks them as
  `expected_on_s10plus` (not observations). Device audit confirmed the front sensor is `s5k3j1`
  (policy said `s5k2l4sx_front`), and no setfiles exist on disk.
- **Fix:** corrected `camera.json` front sensor name; documented the real enumeration.
- **Test:** `tests/a52/test-camera-inventory.py` (front sensor s5k3j1 corrected; synthetic opt-in).

## 8. Photos app shows metadata without pixels — CONFIRMED PRESENT

- **File:** `pwa/nuxel-apps/photos/js/photos.js` (`noImage()`, `normalise()`).
- **Observed:** renders `metadata only` placeholder when `item.url` is absent; relies on
  `camera.list-captures` via bridge; never reads real files.
- **Impact:** Photos cannot show real thumbnails/images without a data-URL from the bridge.
- **Fix:** extend bridge with a file-backed `photos.list` + thumbnail/file serving path; Photos
  renders real thumbnails and full images. Implemented this cycle.
- **Test:** `tests/a52/test-camera-frontend.py` (Photos file-backed open/delete verbs, lazy load).

## Audit conclusion

All eight historical defects are **still present** at the baseline commit and were repaired in
this cycle. See `CAMERA-APP-COMPLETE.md`, `PHOTOS-MEDIA-STORAGE.md`, `CAMERA-SERVICE-API.md`.
