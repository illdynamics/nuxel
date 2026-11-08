# 🐧📸 NUXEL A52 — OPERATION PENGUIN VISION
## Samsung Galaxy S10+ camera bring-up + complete Nuxel Camera and Photos application

**Executor:** DeepSeek-v4-pro-thinking or equivalent strong engineering agent.  
**Platform:** Nuxel, Fedora ARM64 / Linux on Samsung Galaxy S10+ **SM-G975F**, codename **beyond2lte**, Exynos 9820, legacy downstream **4.14.x kernel**.  
**Run context:** Current owner's Nuxel repository, connected S10+ running Nuxel, proven USB Live Console; preferably Fedora laptop for offline native development, retaining known-good MacBook recovery access.  
**Scope:** REAL device camera capture, media stack, finished Camera UI, persistent photo/video storage, Photos/Gallery integration, security, performance, integration, testing and honest status reporting.  
**Priority:** Rear/main camera → working viewfinder → actual saved photo → Photos opens it → video → front camera → advanced capabilities.  
**Stop conditions:** Hardware cannot safely stream; target identity uncertain; any action requires flashing/kernel replacement, unapproved reboot, unlicensed proprietary files or risky raw I²C/register writes. In that case **finish the independently testable userspace/app pieces** and present precise hardware blockers rather than pretending the integrated camera works.

---

## 0. OUTCOME CONTRACT — WHAT “CAMERA DONE” MEANS

The owner should eventually be able to:

1. Tap **Camera** from Nuxel Home / app drawer and get a real viewfinder sourced from an **actual S10+ physical camera**, never a mocked/generated video.
2. Grant/deny camera access with a reliable, revocable permission flow. See a clear camera-active indicator.
3. Select the **rear primary camera** and, if the respective hardware pipelines work, switch to **front** and available rear wide/tele sensors. Unsupported lenses must not display fake working switches.
4. Focus and capture a photo, see a thumbnail immediately, find the real image in user storage and open it in the standalone **Photos** app after reboot.
5. Record a real video to a playable standard media file; attach real microphone audio **only when microphone permission and a functional microphone capture path are verified**.
6. Switch Photo/Video, select supported resolution, aspect, timer, flash/torch, exposure/focus options where real hardware supports them; no fake HDR, zoom or stabilization claims.
7. Rotate the device, preserve correct preview and capture orientation, work with Nuxel A49 orientation logic, and survive suspend, wake, lock, navigation and app switching without keeping the camera powered.
8. Delete, view, share/export, import (when practical) and inspect photo/video metadata in Photos without using browser localStorage as the authoritative photo database.
9. Close camera and **release all camera resources** promptly, without overheating the phone or monopolizing the media graph.
10. Reboot the phone and confirm correct service startup, permissions policy, capture files, photo index and application launch registration are persistent.

**ACCEPTANCE IS HARDWARE-EVIDENCE-BASED.** A synthetic `videotestsrc`, color bars, demo footage, a V4L2 node merely existing, a successful libcamera install or a window displaying is NOT a functioning integrated S10+ camera. The goal is genuine hardware functionality, with an honestly documented blockers report if the 4.14 vendor stack cannot deliver it safely in this mission.

Do not declare the mission complete in the ordinary sense if no physical S10+ camera frame has actually been captured. You may deliver a completed *application/backend integration* with a distinctly named **HARDWARE_BLOCKED** verdict.

---

## 1. PROTECT THE CURRENT WORKING PHONE AND PARALLEL MISSIONS

Before changes:

- Record `git status`, current branch and commit, live Nuxel release, installed camera components and service unit files. Establish which tree and binaries run on the handset; do **not** assume old ZIPs reflect current state.
- Capture known-good device state: touch, Home, apps, working Wi-Fi, USB console, lockscreen, native keyboard, navigation, boot splash, thermal idle behavior, resource meters and volume/speaker status (if functional).
- Work in a dedicated **A52 Git branch/worktree**; do not overwrite an A50 performance or A51 Wi-Fi/Flatpak run. If those agents are active, avoid shared service restarts and coordinate device ownership. Avoid changing bridge ABI incompatibly with other apps.
- Back up existing camera configs, installed units, Camera/Photos files, bridge data/schema and user media index. Never delete actual media during migration.
- No kernel flashing, boot/recovery writing, partition writes, Magisk/Android HAL installation, TWRP use or bootloader/security alteration.
- No unsolicited reboot or global graphical restart. Every system-level service replacement must have a tested rollback and known working USB recovery access.
- Device thermal/voltage warnings: if phone is already overheating, **stop camera streaming**, note sensor readings and diagnose before further load testing. Never disable thermal trip protection, overclock, or pin CPU frequencies for this mission.

Create `docs/a52-camera/EVIDENCE-INDEX.md` with timestamps, command receipts and expected vs observed distinction.

---

## 2. HISTORICAL NUXEL SOURCE AUDIT — REUSE, DO NOT REINVENT

The older **v0.6.3-beta full drop-in ZIP** included:

- `configs/nuxel/camera/camera.json` and `configs/nuxel/camera/README.md` — S10+ camera inventory, firmware candidates, policy and expected pipeline.
- `tools/s10plus/a33/nuxel-camera-diag.sh` — `status [--json]`, `list`, `fw`, `pipeline`, `portal`, `capture --yes`, `selftest`; simulated fixture test suite.
- `docs/beta-finalization/manual-proof/15-camera.md` — explicit manual proof gates and camera privacy requirements.
- `shell/nuxel-camera-portal/nuxel_camera_portal.py` and accompanying user systemd unit — experimental camera publisher/portal.
- `pwa/nuxel-apps/camera-gallery/{index.html,js/camera.js,css/camera.css,manifest.json}` — camera UI/PWA.
- `pwa/nuxel-apps/photos/{index.html,js/photos.js,css/photos.css,manifest.json,app.json}` — separate Photos app.
- Shared bridge/permission infrastructure and app registry.

**Known historical technical defects to check for in current code:**

1. `camera.js` calls `navigator.mediaDevices.getUserMedia()`, uses `canvas.drawImage()` then encodes JPEG to a **data URL**, inserts images into an in-memory array, saves entire images to `localStorage` and trims photo count. This is not suitable as the authoritative long-term storage architecture. It even catches quota errors by silently discarding older photos. **Never lose media because browser storage is full**.
2. `camera.js` front/rear toggle calls `_stopCamera()` **before** reading `this.stream?.getVideoTracks()[0]`, so it loses the previous `facingMode` and may continually choose the same camera. Persist the selected device independently of stream lifetime; use actual enumerated device IDs with stable permission-safe labels.
3. `camera.js` has Photo/Video mode selection but the capture button historically runs only `_capturePhoto()`. A mode toggle is not working video recording.
4. A historical `getUserMedia` request uses dimensions `1440x3120` as an *ideal*, not measured camera capabilities. Never confuse screen resolution with sensor/capture resolutions.
5. The historical custom D-Bus “camera portal” advertises `AvailableCameras` / `RunCamera` / `Release` and returns a path carrying a PipeWire node number. This is **not the standard** `org.freedesktop.portal.Camera` API expected by current XDG portal clients. Its actual interface has **`AccessCamera(options)` → request handle**, **`OpenPipeWireRemote(options)` → Unix FD**, plus `IsCameraPresent` and `version`. Investigate before deciding whether to replace it with a genuine xdg-desktop-portal integration or rename/restrict it as a *private Nuxel camera broker*. **Never hijack the standard D-Bus name with incompatible methods.**
6. The historical camera portal defaults to **synthetic** unless `--hardware`; test mode may be helpful, but device-visible app defaults must never silently show synthetic content as a real camera.
7. The policy lists prospective sensor names and firmware filenames. **Those are hints from a historical manifest, not proof of which sensors or firmware the running S10+ binds.** Never fabricate observations or assume that the sample `s5k2l4_setfile.bin` in a test fixture is usable firmware.
8. The Photos app can display metadata without pixel data and reports that state honestly; complete it with real file-backed media access and thumbnails.

Inspect the current repository and deployed files yourself. If code has already been fixed in newer commits, keep it. Create `docs/a52-camera/BASELINE-CODE-AUDIT.md` listing: observed problem, file/line, impact, owner, safest change, and regression tests.

---

## 3. READ-ONLY HARDWARE DISCOVERY: S10+ SENSOR → ISP → VIDEO NODE

Do not start by changing Camera UI CSS. First determine if hardware can produce actual frames.

### Identity + kernel

Capture:

```sh
uname -a
cat /proc/cmdline
cat /proc/device-tree/model 2>/dev/null || true
ls -l /dev/video* /dev/v4l-subdev* /dev/media* 2>/dev/null || true
find /sys/class/video4linux -maxdepth 2 -type f -name name -print -exec cat {} \; 2>/dev/null
```

Use `nuxel-camera-diag.sh status --json`, `list`, `fw`, `pipeline`, `portal` from the active deployed version; verify actual command capabilities. Report whether a result comes from on-device hardware, a VM fixture, policy expectations or synthetic video.

Use installed utilities if available, or offline-install through Fedora repo **only if Wi-Fi/USB internet and package management work**:

```sh
v4l2-ctl --list-devices
media-ctl --print-topology -d /dev/media0
v4l2-ctl --device=/dev/video0 --all
v4l2-ctl --device=/dev/video0 --list-formats-ext
dmesg | grep -Ei 'fimc|exynos|is[ -]?camera|camera|sensor|v4l2|media|mipi|csi|isp|i2c|firmware' | tail -200
```

These are **examples, not evidence** `/dev/video0` or `/dev/media0` is a usable camera. Enumerate actual nodes, `VIDIOC_QUERYCAP` caps, media entity graph, link enablement, formats, IO modes and sensor subdevices. Distinguish memory-to-memory codecs, output-only nodes, ISP statistics, capture nodes and UVC video devices.

Inventory exact rear and front camera module identities **from running kernel, DTS/DTB, and proven hardware evidence**. The old camera policy may suggest rear main/tele/ultrawide and front sensors, but vendor module variants exist. Capture actual drivers, I²C addresses only for read-only evidence, sensor clock/regulator/power-domain states, MIPI CSI/receiver, Exynos ISP/FIMC-IS camera stack, firmware/setfile dependencies, and OIS/actuator if present.

### Camera stack decision matrix

- **Scenario A:** usable V4L2 capture node that streams real frames → prototype bounded still and preview; advance to PipeWire/libcamera.
- **Scenario B:** media graph and sensor driver exist but capture fails → inspect entity links, compatible formats, power, ISP firmware, DMA buffers, memory allocator, dmesg; repair only verified source/config defects without blind register writes.
- **Scenario C:** expected nodes exist but are codecs/test artifacts → do not misclassify as sensor frames; diagnose absent driver or incomplete ISP.
- **Scenario D:** no camera nodes or missing camera/ISP drivers → deliver upstream/downstream source audit, specific required kernel config / DT / driver / firmware / pipeline design, isolated buildable patches if possible, test evidence and **HARDWARE_BLOCKED**. Do not invent a functioning capture stack.
- **Scenario E:** vendor camera stack demands Samsung Android proprietary interfaces → research lawful/native Linux integration paths, identify precise gaps, and document as a blocker rather than installing an Android framework into Fedora by stealth.

Never extract proprietary firmware from unrelated phones, obtain unknown binaries, fabricate calibration blobs, or write EFS/calibration/OTP partitions. Check licenses and model compatibility for available firmware. Avoid I²C pokes and disabling safety/thermal controls. No direct kernel flash, DTB replacement or reboot without explicit separate owner approval.

Deliver: `A52-HARDWARE-INVENTORY.md`, `A52-MEDIA-TOPOLOGY.txt`, `A52-KERNEL-CAMERA-GAP.md`, `A52-BASELINE-CAPTURE.json`.

---

## 4. PROVE A REAL FRAME INDEPENDENTLY OF THE UI

Prove a camera pipeline **before** showing a “working camera” badge:

1. Open the actual physical capture node with a supported tool/API. Respect discrete supported pixel formats, sizes and strides. Configure one real mode; avoid assuming MJPEG/YUYV/NV12 is provided.
2. If ISP offers raw Bayer only, use a documented compatible processing path. Raw bytes without exposure, demosaicing, color correction or valid calibration are not a usable finished Camera experience. But preserve raw evidence and identify the remaining ISP gap.
3. Obtain bounded frames, timestamps, exact byte counts and negotiated pixel formats; validate real non-test frames with owner-directed physical scene changes (e.g., move hand in front of camera). Prove luma/color variation and distinct frames from real exposure, not an encoded static placeholder.
4. Save one owner-consented still into a private temporary test directory. Generate checksum, dimensions, capture timestamp, pipeline and device identity metadata. Check actual image decode via an independent viewer/decoder.
5. Stop stream promptly and prove camera clocks/stream resources go idle.
6. Record front and rear results separately; unsupported lenses receive truthful `NOT_AVAILABLE`/`BLOCKED` status.

Use GStreamer (`v4l2src`, `libcamerasrc`, encoders and sinks), libcamera tools, or a small diagnostic V4L2 app appropriate for the **proven device nodes**. Do not blindly launch multiple conflicting capture tools at the same time. The `libcamera` pipeline handler only works if the kernel exposes a compatible underlying media graph and handler; installing libcamera by itself does **not** create a camera driver.

A USB/UVC webcam may be useful to independently validate userspace, but its success **must not be reported as success of the integrated S10+ cameras**. Clearly label source: `rear-main`, `front-main`, `usb-uvc`, or `synthetic-test`.

Create a stable, bounded `nuxel-camera-diag` command that can produce `CAPTURED_REAL_FRAME`, `TEST_SOURCE_ONLY`, `NO_CAPTURE_DEVICE`, `DRIVER_MISSING`, `FIRMWARE_MISSING`, `ISP_PIPELINE_BLOCKED`, `PERMISSION_DENIED`, `FORMAT_NEGOTIATION_FAILED` or `CAPTURE_FAILED` with first failing stage.

---

## 5. PRODUCTION-CORRECT NATIVE CAMERA SERVICE AND SESSION OWNERSHIP

Build/refine **one** authoritative, privilege-minimized camera integration path; never spawn duplicate daemons to fight over the same camera.

Suggested architecture (adapt to repository realities):

```text
Physical S10+ camera sensor(s)
  → kernel driver / MIPI CSI / ISP / V4L2 media graph
  → libcamera OR direct V4L2 (whichever is verified)
  → PipeWire / WirePlumber camera source
  → standard xdg-desktop-portal Camera (for sandboxed apps)
  → WebKitGTK getUserMedia or native Nuxel Camera broker
  → Nuxel Camera / Photos
```

Implement a **private** broker when necessary for still-image quality, capture settings, file saving and app integration. Name it under the Nuxel namespace (not `org.freedesktop.portal.Camera`) and expose only narrowly scoped capture controls. Use the standard portal for generic Linux/Flatpak applications. If `xdg-desktop-portal` is unavailable or its selected backend lacks a Camera implementation, adapt or implement a standards-compatible backend where technically justified, with actual D-Bus signatures/FD passing/permission persistence; do not simply claim a custom `RunCamera` API is the portal.

Check on phone:

- PipeWire and WirePlumber version and active units, monitor configuration (`monitor.libcamera`, `monitor.v4l2`), source enumeration via `wpctl`/`pw-cli` and camera node properties.
- Whether XDG desktop portal already owns the standard bus name and which backend implements Camera. Avoid service-name collisions, private buses masquerading as portal and duplicate PipeWire camera nodes.
- Whether the WebKitGTK version/runtime has enabled `getUserMedia` and needed camera permissions/features. Determine actual secure origins or native WebKit permission callbacks. Do not open broad network listeners or disable WebKit security.
- Suitable negotiated video formats and DMA-BUF/zero-copy support, software conversion fallback and clear error propagation.
- Structured client authorization by app ID, bounded sessions, signal cleanup, disconnection handling, per-device arbitration and cancellation.
- Camera lease lifecycle: `CLOSED → AUTHORIZING → OPENING → STREAMING → CAPTURING/RECORDING → STOPPING → CLOSED`, with explicit ERROR states and recovery.
- No root-owned unlimited web API that allows untrusted webpages to silently activate camera/microphone.

Unit design: depend on required user-session services; guard restart loops; explicit permissions and minimal device group access; disable streaming until a user gesture/authorized app request. Camera resources must not remain open at boot, after leaving camera, after lock, or with the screen off unless there is a **visible, explicitly user-enabled recording** mode supported by policy.

---

## 6. CAMERA AND MICROPHONE PERMISSIONS (PRIVACY IS A HARD GATE)

- First use: real, clear permission dialog. Deny → no sensor activation, no file created, no blank spoofed capture. Allow → capture only when user triggers it.
- Persist permissions in a user-scoped permission store; provide **Settings → Privacy → Camera / Microphone** granting/revoking and per-app status. Respect A51 Flatpak sandbox and standard portal rules when integrated.
- Distinct camera and microphone permission; video-without-audio must work when microphone is denied. Never silently open mic.
- Front/rear device selection remains scoped to the granted app.
- Show an always-visible camera-active indicator during preview/capture, recording indicator with timer during video; under lock/background, only run recording when explicitly supported and with a continuing indicator and accessible stop control. For initial release, prefer **automatically stop video when locked** rather than implement unsafe invisible background recording.
- Close camera on lockscreen, power off, app terminate, bridge crash, WebKit navigation/visibility loss and owner permission revocation. Clean up device file handles and subscriptions.
- Expose clear `NO_CAMERA`, `DRIVER_UNAVAILABLE`, `CAMERA_BUSY`, `PERMISSION_DENIED`, `MICROPHONE_UNAVAILABLE`, `LOW_STORAGE`, `THERMAL_PAUSE` errors with recovery guidance.
- Do not store or transmit captured photos by default, no analytics upload, no hidden snapshots, and no EXIF GPS without separate opt-in. Keep captured media owner-private with appropriate file permissions.

---

## 7. FINISH NUXEL CAMERA APPLICATION (REAL FRONTEND, NOT A MOCKUP)

Existing application: `pwa/nuxel-apps/camera-gallery/`. Keep the Nuxel visual language, touch targets, bottom navigation compatibility and narrow S10+ aspect ratio. Restore rather than rebuild where feasible.

### Main camera screen

Implement:
- Real live preview with correct proportions, crop mode and rotation; support portrait and landscape when A49 available; no arbitrary stretch.
- Foreground Photo / Video selector; actual distinct behaviors.
- Main shutter button with disable/busy state, real completion/error feedback, optional subtle configurable haptic.
- Camera switch button: remember device **before** closing active stream and wait for proper release before opening new device. Display only working cameras; enumerate safely after permission.
- Thumbnail preview opening most recent real capture, then Photos; never stale data-url cache.
- Capture timer 0/3/10 s, cancellable on Back/lock/app close.
- Resolution/aspect-ratio list populated from actual supported capture modes; start with conservative stable defaults, increase only after hardware measurements.
- Flashlight/flash control only if a verified appropriate LED/flash interface exists. No torch driver guesswork, unsafe current/thermal duration, or pretending display brightness is real flash.
- Focus/tap-to-focus and exposure only when supported by actual V4L2/libcamera controls. If not supported, show disabled/unavailable with reason, not a decorative button.
- Video recording timer, red recording state, Stop, actual playable output and storage/errors.
- Zoom controls only with true supported lens selection or correct labeled digital crop. Never falsely advertise Samsung optical zoom if the sensor is unavailable.
- Accessibility labels and touch ergonomics; hardware Back should leave nested Gallery, then dismiss overlays, then close app as appropriate; Penguin Home returns Home; long Back kill releases stream correctly.

### Correct camera app state and events

Use a single state owner, explicit async cancellation/token, no UI toggling against a stale permission request, no race when switching Photo/Video or front/back. Handle double shutter taps, rapid app switching, rotation while recording, users opening Camera twice, and sudden device-loss during suspend. Prevent use-after-stop of `MediaStream`.

Camera-preview render path must avoid making a browser canvas copy for every frame if the native preview can directly display the stream. Avoid blocking JS event loop or full-resolution re-encode on every preview frame.

If no hardware camera exists, finish UI and tests with a separately configurable development test source, but **default to honest unavailable state on real phone**. A test image must never be silently substituted as actual scene input.

---

## 8. RELIABLE STILL IMAGE PIPELINE AND ON-DISK MEDIA STORAGE

Replace localStorage-as-photo-database with real persistent files; migration must not erase prior saved images:

- Determine actual user/home and XDG directories from running Nuxel; prefer `~/Pictures/Nuxel Camera/`, `~/Videos/Nuxel Camera/`, user-private directories, with service/state metadata outside the media content and no hard-coded username. If owner prefers another path, persist the preference.
- Save real image bytes as JPEG, PNG or DNG only if formats truly supported. Stable predictable naming with local ISO date/time and collision-safe suffix; separate canonical ID from filename. Atomic temp file → complete encode → fsync where appropriate → rename, prevent overwrites.
- Verify final file is decodable, dimensions and format correct; include real capture time, orientation, focal properties/exposure *where supported*, camera identity, and opt-in location. No fabricated EXIF values.
- For WebKit capture, transfer a bounded binary blob/stream to a broker/file API; **do not send an ever-growing photo array of base64 data through the bridge**. Avoid excessive RAM copies; support cancellation and sensible size caps.
- Use per-user storage ownership and restrictive permissions; no root-owned owner photos. Handle disk-full/readonly filesystem gracefully without deleting old media.
- Generate thumbnail cache separately, lazy-load and prune cache rather than user photos.
- Validate existing historical localStorage `nuxel-camera-photos` entries and migrate only parseable owner-created images, with preserved original backup and dedup IDs; never discard existing localStorage without an approved migration.
- File index/database must be rebuildable by scanning media directories and withstand reboot, crash, partial write and deletion. Provide reconciliation and duplicate detection.
- Photo app, Photos app and file manager must agree on canonical locations and any safe capability-based `open-file`/`share-file` APIs.

---

## 9. REAL VIDEO RECORDING PIPELINE

Implement native/GStreamer or working WebKit MediaRecorder pipeline, based on actual capture and encoder support. Do not only toggle icon state.

- Detect available encoders/muxers and frame formats. Prefer a widely playable MP4 (H.264/AAC only where legally and technically available), or WebM with actually available codecs. Never assign `.mp4` extension to non-MP4 bytes.
- Capture video at a **verified sustainable resolution and FPS**; 720p/24 or 720p/30 may be an excellent first target, 1080p only if capture/encoder/thermal budget can sustain it. No assumption of 4K or 60 FPS.
- Use hardware encoder only if verified working on Exynos 9820; identify V4L2 M2M codec nodes correctly. Otherwise use a bounded software path and report throughput/CPU/heat.
- Optional audio: source must be the actual mic, with separate permission, selected audio route, actual correct codec and A/V timestamps. If speaker/mic routing remains broken from earlier missions, output **video-only** rather than falsely claim with-audio recording.
- Graceful stop/finalize on owner action, app close, lock, storage-full, device removal and power events. Test crash recovery; don't leave unplayable half-written video falsely indexed as finished.
- Thumbnails and duration/fps/size metadata derived from actual finalized file; no made-up values.
- A 10-second recording must play in Nuxel's video viewer or a known compatible external player and remain available after reboot.

---

## 10. FINISH PHOTOS / GALLERY AS A REAL APPLICATION

Existing `pwa/nuxel-apps/photos/` and the Camera embedded Gallery should share **one verified library/index**.

Complete:

1. Grid view with real file-backed thumbnails, newest first; quick incremental refresh after capture.
2. Fullscreen photo viewer, swipe next/previous, pinch-zoom/pan where possible, landscape/portrait handling, Back closes viewer before app exit.
3. Video thumbnails, play/pause/scrubbing through a working media player, duration, muted/mic status.
4. Albums by actual folders/date and Camera/Screenshots/Imported categories (when present); no invented galleries.
5. Real metadata pane: dimensions, type, captured/modified timestamp, size, optional GPS only when stored.
6. Delete with confirmation and safe file operation; optional Trash/undo where supported; never merely remove an index entry while leaving original file without a stated reason.
7. Import/export/share to the Nuxel Files app and standard Linux file dialogs/portals as supported. Avoid unsafe arbitrary filesystem paths in a web bridge.
8. Search/filter and stable pagination for hundreds/thousands of media items; no loading hundreds of base64 full-res images in RAM.
9. Empty, permissions-denied, disconnected media service and corrupt-file states clearly displayed.
10. Persistent photo and video files across app/browser restart and phone reboot.

Inspect legacy `camera`, `capture`, `list-captures`, `delete`, `open` bridge verbs: maintain compatibility where practical, but replace insecure bulk-payload APIs and align declared manifests, backend handlers, unit tests and application registry. Protect all other Nuxel apps from breakage.

---

## 11. INTEGRATE WITH NUXEL HOME, SETTINGS AND NATIVE LINUX ECOSYSTEM

- Ensure Camera is registered once and launchable from Home/app drawer without a duplicate icon or broken dock. Photos likewise.
- Hardware Back closes popovers/viewers first; Home minimizes/returns to Home and releases preview; Recents restores app gracefully with fresh permission and no stuck camera device.
- Lock screen must never display a stale camera frame behind it, leak preview and re-activate sensor without unlock/consent.
- Support A49 rotation policy when installed and correct EXIF orientation, front-camera preview mirror versus saved result. Distinguish preview mirroring from actual stored image mirroring.
- Add Nuxel Settings → Apps → Camera: preferred lens (if available), still quality/resolution, video quality, shutter sound where permitted, location metadata opt-in, preferred save folder, and `Open camera permissions`. Settings persisted properly across restart without storing sensitive raw filenames in world-readable config.
- Keep Nuxel's gray/black/blue working keyboard as the only OSK; no camera UI overlay over bottom navigation or lockscreen.
- When A51 native/Flatpak app support is ready, test a separate native camera client such as **GNOME Camera / Snapshot (`org.gnome.Snapshot`)** only against actually recognized devices. This is an optional interoperability test, not a replacement for completing Nuxel Camera.
- Provide documented camera APIs for future chat/video-call applications via correct PipeWire/portal, rather than binding them to one PWA's globals.

---

## 12. FRAME RATE, MEMORY, ENERGY AND THERMAL OPTIMIZATION

A50 is optimizing the presentation path; avoid competing hacks. Record baseline and after:

- Camera cold-start time from tap → first **real** frame.
- Preview FPS and P50/P95 frame interval, dropped frames; distinguish camera sensor FPS from display FPS.
- Shutter-to-photo-written P50/P95, UI response time and capture success under repeated uses.
- CPU%, total RAM/RSS/PSS for relevant processes, buffer memory, GPU conversion cost (if measureable), PipeWire and WebKit cost.
- Locked/screen-off idle power/thermal trends and camera-open temperature rise.

Optimizations: choose a sustainable low-latency preview stream independent of full photo resolution; avoid redundant RGB conversions and copying full-screen buffers where safe zero-copy is supported; do not load all captured images as data URLs; do not busy-poll a missing camera; only start the camera at the moment it is needed; completely stop clocks/stream on close; use async file writes, cached thumbnails and bounded queues; do not leave `videotestsrc` running perpetually on phone.

Performance objectives are **targets, not assumed results**: responsive shutter, preview that feels smooth at the highest verified sustainable FPS, no runaway thermal load, negligible camera-related wakeups with the screen off, and no regression to A50's working Home/swipe performance.

---

## 13. TESTS — STATIC, UNIT, INTEGRATION, FAULT INJECTION, PHYSICAL

### Automated tests

- Hardware inventory parser: missing nodes, partial graphs, bogus codec-only nodes, firmware absent, synthetic test source, real camera present, malformed device properties.
- Standard camera portal interface signatures: `AccessCamera`, request response signal and Unix FD `OpenPipeWireRemote` where installed; reject incompatible provider collisions.
- Permission denial/revocation, multiple apps, double capture, aborted permission prompt, app close while streaming, camera-switch rapid tap, selected-device state, duplicate clicks.
- Real media backend: supported formats, clean stop, finite recordings, full file decoding, no extension/codec mismatch, atomic writes, partial write recovery, out-of-space, access denial.
- Capture file persistence and legacy localStorage migration with rollback.
- Gallery: real content, delete behavior, thumbnails, video playback, metadata and media-index reconciliation.
- Orientation: portrait, landscape, inverse supported modes; mirrored preview and EXIF handling.
- Suspend/lock/Home/Recents/long Back: no dangling camera file descriptors; camera-active indicator accurate.
- Privacy: no camera at boot, no invisible capture, mic denied means no audio, location off means no coordinates.
- UI interactions and keyboard/nav remain working.
- Performance telemetry baseline/after; frame capture/source labeling rigorous.

Use prerecorded fixtures to test algorithms, clearly segregated from hardware acceptance. Produce test receipts, failures, logs and rerun steps; never mark owner-only physical tests PASS from mocks.

### Physical handset acceptance (owner-assisted, only if hardware path is available)

1. Cold boot Nuxel; confirm no camera activity by default.
2. Open Camera → ask permission → deny → verify no preview; reopen/grant.
3. Point rear camera at an obviously changing real scene; prove new frames and no synthetic banner.
4. Tap shutter → verify actual file created and decodes → open it in standalone Photos → inspect dimensions and EXIF.
5. Switch front/back and take another photo **only where supported**. No UI pretense for missing sensors.
6. Rotate phone and verify preview, stored image and viewer orientation.
7. Start video, record ≥10 seconds with moving scene → stop → reopen stored file and playback. Repeat with microphone denied if audio is working.
8. Home, Recents, Back, lock and wake; check camera release/no accidental resuming.
9. Start/stop Camera 10 times; no leaked file handles, stale PipeWire nodes, phantom indicators, crashes or rapidly rising memory.
10. Reboot only when explicitly authorized. Verify images/videos still present, permissions/settings persisted, Camera/Photos open, no camera starts on boot.
11. Monitor idle/screen-off thermals after stopping camera.

Show actual owner-provided camera scene photos only in locally private evidence, not public logs. If one or both internal sensors are unsupported, report exactly which stage failed and demonstrate working app/USB-UVC separately with explicit labels.

---

## 14. DEPLOYMENT, SERVICES AND ROLLBACK

- Prefer **Fedora laptop** for V4L2, kernel source, GStreamer, PipeWire/libcamera cross-build investigations; use correct target **aarch64** builds and dependencies. Known-good MacBook USB console remains valid for safe live deployment.
- Capture host/device identity, active binaries/config hashes and service state before changing them.
- Deploy in small steps, gate each: device diagnostics → camera service backend → permission/portal → Camera UI → save path → Photos → video → settings → performance.
- Make atomic file replacements, check ownership/modes, systemd user versus system units, restart **only affected services** and inspect logs immediately. Never break USB console/network stack in the middle of camera work.
- If needed kernel/DT/firmware support cannot be safely deployed as userspace only, produce a separate patch series and a precise required-owner-approval plan. Do **not** flash kernel or reboot on your own.
- Run static/CI tests on host, integration tests on phone, and physical proof. No “works” assertion from fake data.
- Record exact rollback commands restoring file backups, service units, prior permissions and media index **without losing real photos/videos**.

---

## 15. DELIVERABLES

Produce in `docs/a52-camera/`:

1. `EVIDENCE-INDEX.md` — device/host, timestamps, commit, command receipts, logs and measured observations.
2. `BASELINE-CODE-AUDIT.md` — source audit including current state of historical bugs above.
3. `HARDWARE-INVENTORY.md` — identity, camera nodes, media graph, bound drivers, firmware/calibration status; expected vs observed clearly separated.
4. `MEDIA-PIPELINE-ANALYSIS.md` — functioning/blocked pipeline and first failing subsystem; any kernel/firmware work needed.
5. `CAMERA-SERVICE-API.md` — chosen native/portal architecture, security policy, D-Bus/API signatures and lifecycle.
6. `CAMERA-APP-COMPLETE.md` — UI functions and proof; real vs not supported.
7. `PHOTOS-MEDIA-STORAGE.md` — file paths, persistence, album/index schema, migrations, media-handling guarantees.
8. `TEST-RESULTS.md` — actual automated test counts and physical owner validation separately.
9. `PERFORMANCE-THERMALS.md` — launch/preview/shutter timings and offscreen behavior.
10. `DEPLOYMENT-AND-ROLLBACK.md` — hashes, exact live deployment actions and validated restoration.
11. `HARDWARE-BLOCKERS.md` — if camera remains blocked, reproducible failure evidence, closest feasible non-destructive next step, dependencies and estimations qualified as unverified.

Also deliver the actual source changes, tests, systemd/portal/bridge integration, app registry updates, and optional host-side diagnostic scripts. Commit a reviewable A52 branch. Do not overwrite simultaneous A50/A51 work.

### Required final status table

| Gate | Status | Proof |
|---|---|---|
| S10+ rear sensor enumerated | PASS / BLOCKED | device-derived node + driver |
| Real rear preview frames | PASS / BLOCKED | measured moving scene |
| Real JPEG still saved | PASS / BLOCKED | file + decode + user photo |
| Front camera | PASS / BLOCKED / NOT_AVAILABLE | separate observation |
| Working 10s video | PASS / BLOCKED | actual playable output |
| Microphone audio in video | PASS / BLOCKED / NOT_AVAILABLE | permission + audio track |
| Permissions and camera indicator | PASS / FAIL | deny/allow/revoke |
| Photos opens persisted capture | PASS / BLOCKED | real file on disk |
| Media survives reboot | PASS / BLOCKED | authorized reboot, same files |
| Releases camera on Home/lock | PASS / FAIL | no lingering streaming |
| Smooth preview / acceptable thermals | PASS / FAIL / UNVERIFIED | actual measurements |

**Overall verdict:** `HARDWARE_VERIFIED_FULL`, `HARDWARE_VERIFIED_PARTIAL`, `APPLICATION_READY_HARDWARE_BLOCKED`, `BLOCKED_ENVIRONMENT`, or `FAILED_REGRESSION`. Never call the first two unless real **built-in S10+** frames were observed. Never substitute a USB webcam or test pattern to upgrade the hardware verdict.

---

## 16. EXECUTION ORDER — NO STOPPING AT A PRETTY APP

1. Inspect current repo and actual device.
2. Enumerate sensor/media topology and kernel support.
3. Capture **one real physical frame** if possible.
4. Make the camera publisher + standard portal/private broker correct and secure.
5. Repair and complete Camera app preview/photo capture with physical proof.
6. Implement robust file-backed Photos/Gallery and migrate existing media safely.
7. Add working video and conditional microphone support.
8. Finish front/rear, flash/focus/resolution/timer/settings as supported.
9. Test navigation, rotation, permissions, wake/lock, resource release and thermals.
10. Deploy incremental live userspace changes, verify physically, run regression suite and persist across owner-authorized reboot.
11. If the vendor camera stack blocks hardware bring-up, still deliver fully testable honest app/backend work and an actionable driver/ISP blocker dossier. Do not claim complete hardware functionality.

### FINAL INSTRUCTION TO THE EXECUTOR

**The owner's objective is a real, working camera on an independent Fedora Linux phone—not a cosmetic camera mockup.** Keep the working Nuxel penguin experience intact, repair the camera plumbing and UI correctly, create real durable photo/video files, and prove each hardware claim on the Galaxy S10+. If firmware/kernel support prevents actual capture, identify the first real blocker precisely, deliver safe source-only groundwork and a clear future hardware plan.

**GO GIVE THE PENGUIN EYES. 🐧📸🔥**

---

### Authoritative engineering references to consult and reconcile with current phone

- Existing repo: `configs/nuxel/camera/README.md`, `configs/nuxel/camera/camera.json`, `docs/beta-finalization/manual-proof/15-camera.md`, `tools/s10plus/a33/nuxel-camera-diag.sh`, `shell/nuxel-camera-portal/`, `pwa/nuxel-apps/camera-gallery/`, `pwa/nuxel-apps/photos/`.
- libcamera: https://docs.libcamera.org/master/ and https://docs.libcamera.org/master/guides/pipeline-handler.html
- XDG camera portal: https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Camera.html
- WirePlumber camera monitors: https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/video.html
- postmarketOS `beyond2lte` device status: https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_%28samsung-beyond2lte%29
- GNOME Camera (optional interoperability client): https://apps.gnome.org/Snapshot/
