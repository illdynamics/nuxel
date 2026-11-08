# 🐧🔓📸 NUXEL A61 — OPERATION PENGUIN EYES & UNLOCK RECOVERY
## Emergency camera-escape, native/custom Camera repair, and draggable lockscreen recovery

**Execution agent:** GPT-5.6 Sol (High) preferred; DeepSeek-v4-pro-thinking acceptable.  
**Target:** Owner's *current* Nuxel on Samsung Galaxy S10+ **SM-G975F / beyond2lte / Exynos 9820**, Fedora ARM64, Samsung-derived 4.14 kernel, Phoc/Wayland, WebKitGTK/PWA shell, Nuxel bridge, USB Live Console.  
**Host:** Fedora laptop or MacBook using the *already proven* live console.  
**Scope:** (1) Restore reliable lockscreen drag-to-unlock; (2) make the Camera app always escapable, even if its initialization stalls; (3) repair/complete the custom Nuxel Camera and native GNOME Snapshot installation and lifecycle; (4) investigate physical camera frame capture honestly without hardware-risky experiments.  
**Out of scope:** Rewriting Nuxel Home, Wi-Fi, rotation, performance governor tuning, other PWAs, other navigation visual design, MOSS/boot images, Android apps, kernel migration, bootloader, flashing, TWRP.

## 0. Exact current owner symptoms / required outcomes

The owner reports:

- Tapping the Camera app starts a **permanent loading state**.
- Once Camera loads/hangs, **Back and/or Penguin Home cannot return to Home**; the user is effectively trapped in Camera.
- The custom **penguin lockscreen renders but no longer unlocks when its lockhead is dragged upward**, despite having worked in a previous A45/A45.1 version.
- Previously delivered A52 camera work reported the **rear sensor enumerates** but **real frames, photos, front camera, video, and mic audio remain blocked** by the Exynos FIMC-IS/ISP pipeline. Snapshot installation/camera availability is not proof of real capture.

**The first deliverable is a fully usable phone again.** Do not spend hours on an unsupported camera driver while the user is trapped behind an app or lockscreen.

Hard acceptance:

1. Swipe penguin lockhead upward and **really unlock** the authoritative graphical session, restoring touch/focus and Home. Small swipe does *not* unlock.
2. Camera opens a responsive UI immediately with Back/Close/Home always available, even if no camera devices/frames exist; camera detection cannot block the UI/event loop.
3. In Camera: short Back returns appropriately, Penguin Home always switches to Nuxel Home Desktop 1, and an explicit Close/Exit action works. Lock/Power and wake remain safe. No persistent touch-blocking transparent surface.
4. Installed native Camera **GNOME Snapshot** opens as a genuine native application or gives a clear, actionable compatibility error. Its process must be controllable and escapable.
5. Nuxel's own Camera offers controls, capability/error states, bounded preview initialization, eventual real capture only if the hardware pipeline exists, and persistent photo integration without fake frames.
6. Restart of the relevant services and approved cold boot do *not* reintroduce either lockscreen or Camera hang.

## 1. Emergency device safety and recovery before coding

- Confirm device is the owner's SM-G975F and identify the current running Nuxel revision. Work with the current repository and deployed filesystem; prior A45, A52, A54, A59 and A60 prompts are historical hints, **not** proof of current implementation.
- Establish **working USB Live Console** before touching lockscreen, compositor, launcher, keyboard, or camera services. If the phone is locked and touchscreen unlock is broken, use this *already-authorized owner recovery interface* for diagnosing and repairing the lock-manager service. Do not bypass a separate PIN/password or alter platform security policies.
- Confirm owner can still recover to stock recovery/TWRP if needed, without booting it or flashing. Back up the exact known-good live service units, app bundles, compositor config, bridge API/schema, camera binaries, lockscreen files, lock state and deployment checksums to an off-device directory.
- Capture logs **before** restarting processes; avoid losing the useful first exception. Include `systemctl --user`, system-wide units where appropriate, service journal, WebKit console if available, app-launch receipts, process tree, compositor connection state, and input seat diagnostics. Use permissions appropriate to session owner, not a generic root GUI launcher.
- Establish deterministic rollback that restores exact deployed files and restart order. Do not kill the only USB console process; do not restart the whole desktop just to re-open Camera.
- Before running high-load camera tests, assess temperature and avoid repeated camera polling/streaming if the S10+ becomes hot.
- **Never flash partitions, replace kernel/boot/recovery/rootfs, run register pokes, fetch proprietary blobs from arbitrary sources, modify Knox, or disable camera privacy enforcement.**
- Avoid simultaneous agents operating on the physical phone. Work in dedicated `a61-camera-unlock` Git branch/worktree, merge onto current code without resetting prior fixes.

Output `docs/a61/00-baseline-and-rollback.md` with actual hashes, commands, identified units, and no secrets.

## 2. Trace the REAL lockscreen event → unlock protocol

The current lockscreen artwork is:

- `./assets/nuxel-lockscreen.jpg` — custom wallpaper;
- `./assets/nuxel-lockhead.png` — glowing draggable penguin padlock face;
- the lockhead MUST rest **below the penguin illustration**, not cover it.

Preserve the existing lockscreen visuals, icon location, glow, wiggle animation where present, background, power handling, and intended **swipe-only convenience** authentication policy. Do not introduce an unrelated PIN or redesign.

### Diagnose *each* edge

`screen wake → lock surface visible → trusted lock manager owns LOCKED → pointerdown on lockhead → pointer capture → pointermove → distance threshold → pointerup → unlock request → lock-manager acknowledged transition → compositor session unlock → lock surface removed → application/input focus restored`

Record bounded diagnostics for: `pointerId`, starting/current clientY, actual upward delta, threshold, DOM element bounds, CSS transform and device scale, `pointerup`/`pointercancel`, JavaScript exceptions, WebKit bridge availability, IPC request/response, `locked` state, stale overlay surfaces, compositor locked/unlocked status, focus restored. No privacy-sensitive logging.

Investigate these regression classes explicitly:

- Touch listener lost during UI bundle update, duplicate listeners, non-passive `touchmove` interfering with pointer capture, WebKit changed touch-action/CSS hit test, overlay intercepting gesture, widget `pointer-events` unexpectedly disabled.
- Lockhead animation/wiggle overwrites its drag `transform` each frame; maintain independent animation and translation layers, or compose transform safely so wiggle never cancels displacement.
- Threshold computed in physical pixels but motion in CSS pixels; threshold not reachable in portrait/landscape; `pointerup` occurs on a different element due to capture loss; CSS animation resets position before threshold check.
- `touchend` and `pointerup` firing duplicate requests; an old lockscreen script loaded from stale cache; lock manager renamed or missing D-Bus/IPC method; frontend state flips but compositor remains session-locked.
- Competing lock services, startup readiness race, display suspend/resume losing lock-client protocol object, idle timer immediately re-locking, lock overlays persisting after apparent unlock.
- If session locking uses **`ext-session-lock-v1`**, follow its actual protocol: only call `unlock_and_destroy` in the legitimate locked state after the trusted unlock action, ensure the compositor processes it (including a sync when necessary). Never simply hide HTML to impersonate unlock. Confirm what protocol the *current* Phoc actually supports; do not assume it implements this extension.

### Implement stable gesture state machine

`LOCKED_IDLE → DRAGGING → THRESHOLD_READY → UNLOCK_REQUESTED → UNLOCKED`; and `DRAGGING → CANCELLED → RESET`.

- Upward distance: `startY - currentY` in one consistent coordinate system.
- Make threshold reachable in visible travel; a starting tuning target is ~20–25% of usable viewport height, clamped to the actual lockhead travel.
- Use pointer capture and explicit `pointerup`, `pointercancel`, `lostpointercapture` fallback; guard duplicate events/gesture races.
- Once the threshold is met, release triggers a **single** trusted backend unlock request. Wait for authoritative success before hiding lock surface. On error, show recoverable lockscreen/error rather than a black screen.
- A short swipe snaps back; a full swipe reliably unlocks; locks again on intended Power/timeout; wake and re-unlock work repeatedly.
- The standard triple-button navigation and OSK must NOT appear on the lockscreen; input from ordinary apps must remain blocked while actually locked. Treat lockscreen as convenience-only security—do not expose a privileged global unlock API to arbitrary apps.
- Use a safe watchdog/status mechanism to detect a crashed lock UI and restore the trusted **lock client**, but **never auto-unlock because of crash or timeout**. Repair/restart the owner lock application through the authorized live-console route if UI recovery fails.

### Locked acceptance

10 consecutive swipe-unlock cycles, including at least 3 lock/wake cycles; short drag cancels; repeated fast upward swipe succeeds once; wiggle continues when idle but never hijacks drag; no ghost overlays and Home/app touch works after unlock. One wake following a permitted timeout. If unverified, mark BLOCKED.

## 3. Stop Camera from holding Nuxel hostage — fix this BEFORE sensor work

Identify which UI the launcher actually opens:

- `pwa/nuxel-apps/camera-gallery/` or updated custom Nuxel Camera;
- GNOME Snapshot (`org.gnome.Snapshot`, or actual `.desktop` ID);
- stale app-registry entry, wrapper, WebKit shell or mixed mode.

Trace:

`home icon tap → registry lookup → launcher → actual process/surface → responsive first paint → camera permission/detection → preview initialization → frame arrival OR error → user Back/Home/Close`.

Find the **first event that blocks**. Diagnose synchronous `getUserMedia()` assumptions, unresolved permission promise, media graph polling, a forever spinner, blocking D-Bus method, GTK main-loop startup, foreground surface lifetime, Home event not forwarded, visual overlay intercepting taps, stale/cached JS, bad native `.desktop` Exec, DBusActivation, or orphaned surface.

### Non-negotiable app UX

- Render application chrome/title/controls immediately **without awaiting a camera**. Async detect/open may run in background, never on UI main thread.
- Show clear **"Looking for cameras…"** with short phase-specific visible progress; after a **bounded** initialization timeout (suggest 5–8 seconds for user-visible first result, configurable), transition to actionable failure: "Camera hardware detected, but no usable video stream" or accurate actual failure stage. Do not reset timer indefinitely.
- Always show working **Back / Exit / Close**; a persistent exit control remains actionable while modal/loading/error is shown.
- Trusted hardware/navigation **Penguin Home** must switch to Home Desktop 1 regardless of whether Camera is loading, awaiting permission, or showing error. Home should **not** kill the app by default. The system long-Back kill action (if configured) must still terminate the *foreground Camera process only*, leaving shell/bridge/compositor unaffected. Short Back dismisses OSK/dialog before navigating out.
- Native Snapshot must also be controlled by the **system-level window/application manager**, not by custom JavaScript inside Nuxel Camera.
- Implement a bounded cancel signal/controller. On navigating away, cancel pending UI operations and release locks/streams/timers/background polling. Do not globally kill `pipewire`, NetworkManager, compositor, input service or system dbus.
- Handle camera permission refusal and failure without blocking Home, Back, Power, and lockscreen. On lock, stop preview and release camera resource, do not show captured frames behind lock surface.
- If camera app WebKit content renderer becomes unresponsive, offer a shell-level escape/recovery and bounded process termination of **only that app renderer**. No compositor restart as normal exit path.
- Ensure application layering: Home/nav system surfaces not trapped underneath a fullscreen unresponsive camera overlay. Use authoritative focused window/surface routing and correct `app_id`, geometry and input region.

### Escape tests

From Home: open camera → press Home during immediate loading → Home. Repeat with Back. Repeat when native Snapshot displays no camera, after permission denied, after 8-second no-frame timeout, from a simulated stalled camera service, and after launching Camera multiple times. Lock while Camera open, wake/unlock, confirm Camera does not remain atop the lockscreen and Home works. No processes left spinning/hot.

## 4. Repair native GNOME Snapshot app installation and window management

On the **phone**, not only on Fedora laptop:

1. Audit the actual installed `snapshot` RPM or Flatpak, binary, `.desktop`, icon, GSettings/schema/runtime, package architecture (`aarch64`), PipeWire/GStreamer/GTK/libadwaita/portal dependencies, and package transaction receipts. Do not assume app installed because Nuxel lists an icon.
2. If missing, install compatible Fedora package from configured trusted repo (`dnf install snapshot` only after validating repo/version/available space/network) or supported Flatpak if sandbox/portals genuinely work. Keep authenticated package signature and provenance checks.
3. Verify launching inside the **actual Wayland user session** with correct `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, session D-Bus, PipeWire socket and app permissions. A root USB console alone does not automatically inherit these values.
4. Register proper app identity and icon with Nuxel application registry / `.desktop` discovery; avoid duplicate "Camera" shortcuts pointing to mutually different broken apps. Distinguish entries explicitly as **Nuxel Camera** vs **GNOME Camera**, if offering both.
5. Start Snapshot with a captured process receipt and visible native window; if no usable camera is found, display its actual native no-device result rather than spinning invisibly. Demonstrate **Home/Back/Close** for native GTK surface.
6. If Snapshot is blocked by old kernel camera/portal support, document exact logs, keep native app launchable if possible and finish escape/lockscreen repairs independently.

Never report `CAMERA_CAPTURE_PASS` merely because Snapshot installed or launched.

## 5. Finish the custom Nuxel Camera app without inventing hardware capability

Reuse the implemented A52 pieces if present on the **current deployed device**:

- Durable `media_store.py` file-backed media backend under `/var/lib/nuxel/media` (verify actual user-owned location, perms and privacy).
- Camera bridge `status`, `list-captures`, `capture`, `open`, `delete` with clean capability gating.
- Private `org.nuxel.Camera` service, **not** a fake implementation impersonating `org.freedesktop.portal.Camera`.
- Existing Camera PWA `getUserMedia` handling, capture via `canvas.toBlob`, `MediaRecorder`, correct facing-mode persistence, and Photos PWA thumbnail/load/delete integration.

Ensure:

- Proper responsive empty/error/no-camera state, working close/Back/Home.
- Camera source enumeration and supported modes don't freeze the interface.
- Permissions reflect real granted/denied state and no fake active indicator.
- Photo and video buttons disabled with reason when no real stream exists, but app remains fully navigable.
- When a frame stream exists: preview renders real hardware images, on-demand JPEG actually saved to durable storage, Photos opens it; video/recording with correct encoded extension and mic only where verified.
- Saved captures survive restart; no unbounded data URLs in localStorage, no media loss when quota exceeded.
- Never use `videotestsrc`, pre-recorded video, synthetic test patterns, USB webcam footage or cached frame to assert integrated S10+ camera capture. Clearly labeled developer fixtures are allowed **only in tests**.
- Photo/video support is gated to real camera capabilities; show exact hardware blocker in UI and diagnostic report.
- Stop camera clocks/pipelines/timers on Home, lock, sleep, close, crash or app death; do not keep ISP power or spin in background.
- Native and PWA clients cannot take exclusive camera locks forever. Coordinate via PipeWire/session management where supported, with bounded open/close requests.

### Camera portals and actual interfaces

The standardized XDG portal (if implemented/needed for Flatpak) defines **`org.freedesktop.portal.Camera`** with **`AccessCamera(options)`** and **`OpenPipeWireRemote(options)`**; merely adding a service/property or using an incompatible private method name is not equivalent. Do not hijack that well-known name with a custom incomplete service. Keep private Nuxel API private, integrate with standards via a real compatible backend only where feasible.

References for agent to read when relevant:
- https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Camera.html
- https://libcamera.org/getting-started.html
- https://apps.gnome.org/Snapshot/

## 6. Find the first missing *real* camera frame in the S10+ media pipeline

Prior A52 end status (OWNER-REPORTED; verify live): rear sensor enumerated, but capture blocked by absent/nonfunctional Exynos FIMC-IS libcamera pipeline. Do not try random vendor-only APIs or claim that driver exists without proof.

Read-only evidence path:

1. Device identity and driver/kernel config; all relevant `/dev/video*`, `/dev/media*`, `/dev/v4l-subdev*`, relevant sysfs, runtime device permissions.
2. `media-ctl -p` / topology per media node, if tools installed and topology supported. Record entity/pad/link graph. Sensor enumeration alone != a complete image pipeline.
3. `v4l2-ctl --all`, `--list-formats-ext` against correctly identified capture node; distinguish metadata-only or output nodes. Avoid assuming `/dev/video0` is camera.
4. `cam -l`, and **only if real camera fully advertises usable libcamera pipeline**, bounded `cam -c 1 --capture=... --file` to save a real frame. Do not hammer capture if device cannot configure stream.
5. Inspect PipeWire `pw-cli`, `wpctl`, `pw-dump` camera nodes and running services where relevant; GStreamer element presence and pipeline errors without indefinite busy-poll.
6. Inspect kernel messages and service receipts for missing FIMC-IS ISP firmware/driver, sensor I²C, CSI, memory allocation, media entity linkage, pipeline handler registration, timeout. Redact personal identifiers.
7. Correlate sensor nodes → ISP/media graph → buffer allocation → stream start → first delivered frame → JPEG encoder → saved file. Report **FIRST FAILED STAGE** and evidence.
8. If driver/ISP firmware absent, emit precise `HARDWARE_BLOCKED` with short source/ABI upgrade plan; do not perform kernel writes or uncontrolled reverse engineering against hardware in this mission.

**Camera app/escape/lockscreen can pass while camera hardware capture remains blocked.** Report those as separate outcomes.

## 7. Cross-component races: camera, lockscreen, focus and compositor

Explicitly investigate whether the current Camera hang and lockscreen regression share a root cause:

- One fullscreen surface or input region grabs all touch events, including lockscreen drag.
- A native Camera or embedded WebKit process receives focus while lockscreen should own input.
- The app-launcher and lock manager both modify window layers or renderer state.
- Long-running camera initialization holds a shared bridge/event loop or D-Bus callback, preventing unlock dispatch.
- A stale app service or cached JS bundle has mismatched method/ABI signatures.
- A camera-stream lock or permission dialog remains modal while the screen locks.
- A camera app death leaves a phantom compositor surface/input grab.

If shared cause exists, fix it once in appropriate shared ownership code, with targeted tests, instead of adding two unrelated timeouts. Keep camera initialization off the shared UI/lock IPC critical path.

## 8. Tests — no green status from mocks alone

### A. Automated / simulated tests

- Lock small drag resets, full upward drag only one unlock request; pointer capture lost/cancel; wiggle transform doesn't override drag; wrong active lock session rejected; backend denial preserves lock; no ghost overlay after success.
- Lock lifecycle startup, Power wake, idle timer, app open at lock time; session-lock API mocked for states but physically checked later.
- Camera delayed permission, denied permission, stalled first frame, absent media device, duplicate launch, cancelled init, native UI no-device exit, rapid Home while opening, camera close while capture attempts, repeated locks, timeout and stale response ignored.
- Native app Home/Back navigation independent of WebKit content; no application process leakage; high-level bridge failures cannot block lockscreen IPC.
- PWA no-camera state has visible and accessible Back/Close; photo actions correctly disabled; durable store doesn't delete old images on error; previous A52 suites remain passing.

### B. Physical S10+ acceptance matrix — REQUIRED

| Gate | Required on-phone result | Terminal verdict |
|---|---|---|
| `LOCK-DRAG` | Drag lockhead upward → real session unlocks | PASS/BLOCKED |
| `LOCK-REPEAT` | ≥10 unlock gestures incl. lock/wake and one timeout | PASS/BLOCKED |
| `CAMERA-OPEN` | Tap custom Camera → immediate interactive UI | PASS/BLOCKED |
| `CAMERA-ERROR-EXIT` | No camera stream → truthful error and working Exit/Back | PASS/BLOCKED |
| `CAMERA-HOME` | Penguin Home leaves custom Camera at any init state | PASS/BLOCKED |
| `SNAPSHOT-INSTALLED` | Actual native package, desktop file, binary | PASS/BLOCKED |
| `SNAPSHOT-LAUNCH-EXIT` | Native window opens and can return Home / close | PASS/BLOCKED |
| `LOCK-WITH-CAMERA` | Lock, unlock, no captured frame leak or input hijack | PASS/BLOCKED |
| `REAL-REAR-FRAME` | Actual Exynos sensor frame saved/readable | PASS/HARDWARE_BLOCKED |
| `CAMERA-PHOTO` | Actual JPEG saved to durable media directory | PASS/HARDWARE_BLOCKED |
| `CAMERA-PHOTOS` | Photos opens captured photo | PASS/HARDWARE_BLOCKED |
| `RESTART-REGRESSION` | Service restart preserves both lock and app escape | PASS/BLOCKED |
| `REBOOT-REGRESSION` | Owner-approved cold boot maintains both | PASS/NOT_RUN |
| `NO-REGRESSION` | Home, keyboard, Wi-Fi, SnekByte, recovery console still work | PASS/BLOCKED |

**Never mark hardware camera PASS for synthetic content, previously saved image, device-node enumeration or Camera UI working.**

### C. Live verification sequence

1. Verify USB Live Console remains usable.
2. Deploy lockscreen patch atomically with version/hash verification; owner demonstrates unlock reliably **before** touching Camera.
3. Deploy Camera exit/navigation patch; owner launches it, returns Home immediately; repeat under no-device failure.
4. Install/repair native Snapshot, launch and escape; verify actual `app_id` and process identity.
5. Inspect hardware media graph, bounded frame attempt only where safe; avoid overheating.
6. Confirm lock with Camera open; unlock restores Home/previous app without blocking.
7. Restart affected processes in minimal dependency order; rerun tests.
8. Ask owner before reboot; on consent, perform one cold boot; test lockscreen *first*, Camera second, then general regressions. If no permission, report NOT_RUN; do not automatically reboot or say it passed.
9. If lockscreen fails after deployment, roll back only lockscreen/bridge changes using owner console. If Camera traps again, roll back only Camera/launcher changes. Never remove the working USB console.

## 9. Implementation and release discipline

- Start with a source/deployed divergence report (`git rev-parse HEAD`, tracked asset hashes, installed WebKit bundle version/cache, actual process binary paths, active service definition). Stale runtime artifacts frequently cause regressions in this project.
- Use minimal patchsets: **A61a lockscreen**, **A61b Camera escape**, **A61c native/custom Camera**, **A61d optional read-only hardware diagnostics**. Keep each independently testable and reversible. Do not blindly run old A45/A52/A59 scripts that overwrite newer code.
- For privileged service changes, use least-privilege command receipts, staged files and atomic replacement, restore original owner/mode/context, service restart and readback.
- Avoid global script modifications, kernel headers or rootfs remaster; do not recompile Phoc if a frontend/bridge fix is sufficient.
- No arbitrary sleep as a substitute for correct readiness. Timeouts are bounded safety/UX behavior, not a device driver repair.
- Never hide debug failures by returning success from exceptions or marking all features available.
- Preserve original penguin lockscreen graphics, lockhead wiggle, native dark keyboard, bottom nav semantics, SnekByte, currently working Wi-Fi and screen-off power behavior.

## 10. Final deliverables and status

Produce actual diff/commits plus:

- `docs/a61/00-baseline-and-rollback.md`
- `docs/a61/01-lockscreen-unlock-root-cause.md`
- `docs/a61/02-camera-hang-and-escape-root-cause.md`
- `docs/a61/03-native-snapshot-install-and-launch.md`
- `docs/a61/04-custom-camera-fixes.md`
- `docs/a61/05-exynos-camera-media-pipeline.md`
- `docs/a61/06-tests-and-live-device-receipts.md`
- `docs/a61/07-final-acceptance-matrix.md`

For each gate include: **REPRODUCED / FIXED_IN_SOURCE / TESTED_OFFLINE / DEPLOYED / PHYSICALLY_VERIFIED / BLOCKED / NOT_RUN**, exact first failure, logs and return codes, current and deployed commit hash, rollback command, and any unverified camera capability. Never use “PASS” based only on reading source or unit tests.

## Final agent directive

**GET THE OWNER BACK INTO NUXEL FIRST.** Restore actual penguin drag-unlock. **MAKE CAMERA IMPOSSIBLE TO GET TRAPPED IN.** Then make both real camera applications install, open, respond, exit and report capability truthfully. Attempt actual Exynos image capture only after proving the hardware pipeline supports it; if FIMC-IS is still unavailable, give an evidence-backed blocker and preserve the otherwise working phone.

**NO FLASHING. NO FAKE CAMERA FRAMES. NO GHOST OVERLAYS. NO DEAD PENGUIN LOCKHEAD. 🐧🔓📸🔥**
