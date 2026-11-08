√# FULL-PWNAGE-44000
# NUXEL — HOME ICON DRAG, PIXMAN/FBDEV PERFORMANCE, EXTENDED POWER MENU, SCREENSHOT, GALLERY, FILE SHARING, NOTES WIDGETS & SYSTEM STATUS

## COMPLETE SOURCE-LEVEL REPAIR, IMPLEMENTATION, OPTIMIZATION, TESTING AND SAFE S10+ DEPLOYMENT MISSION

**Mission ID:** PWNAGE-44000  
**Target device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel — custom Fedora-based ARM64 Linux phone OS  
**Primary deployment target:** Existing Nuxel S10+ installation, reached through the operator's already-configured Wi-Fi SSH connection when available  
**UI runtime:** Nuxel Home PWA and application PWAs, hosted by the Nuxel PWA host  
**Display path:** Phoc/Wayland headless + Pixman + shared-memory screencopy + the Nuxel framebuffer presentation bridge  
**Mission classification:** Repair and integrate existing implementations; add missing end-to-end behavior; optimize for the actual software-rendered handset; prove the results.

---

# 0. MISSION OBJECTIVE

The Nuxel S10+ is already a substantial, booting Linux phone port. This mission is a quality and integration pass over the Home shell, hardware-button manager, system status, Files, Gallery and Notes widgets.

The requested features are not all missing from scratch. Several already have partial UI, backend or state-machine implementations that are disconnected, incomplete or tested against the wrong source generation. The task is to identify the actual active path, repair the source of truth, connect the pieces and prove the behavior on the physical device.

This mission must deliver all of the following:

1. Home-screen icons can be long-pressed, picked up, dragged and moved/reordered reliably.
2. Lockscreen, app drawer/window, Quick Settings, Home Settings and Files render and scroll faster on the S10+ fbdev/Pixman path.
3. Holding Power opens the full extended power menu, including restart, poweroff and the existing reboot modes.
4. Power + Volume Down takes a real screenshot, acknowledges it visually and saves it in Gallery.
5. Gallery shows real still thumbnails for video files, rather than presenting a browser decoder failure as the thumbnail.
6. Files scrolls efficiently and has a working Send → Bluetooth flow for selected files, with honest transfer feedback and disabled future options.
7. Notes can save durably; Notes widgets can be added, removed, selected, moved and resized; the actual sticky note appears on desktop 2.
8. Flashlight is a functional, safely arbitrated hardware action, or reports physical hardware absence accurately.
9. Top bar status shows Location state, silent/vibrate mode and wired USB state accurately.
10. Expanded Quick Settings displays charging, USB and console/file-transfer indicators using the existing canonical system-indicator model.
11. The battery icon displays a lightning bolt only while actively charging.

This is an implementation mission. Do not stop after writing findings or a proposed plan. Make changes, add tests, run the project’s regression suites and deploy safely where the existing live SSH target is available.

**Do not regress Nuxel’s working Home/app launch behavior, lock/unlock gesture, button chords, existing USB console, charging-mode handling, file transfer mode, or unrelated applications.**

---

# 1. SOURCE TREE AND ARCHITECTURE — ESTABLISH THE REAL ACTIVE PATH FIRST

The repository contains multiple generations of S10+ sources. Do not assume that the highest-numbered directory is active or that a test of A33 validates an A34 image.

## 1.1 Main implementation areas

Inspect these as one end-to-end system:

```text
pwa/nuxel-home/
  index.html
  js/launcher.js
  js/widgets.js
  js/home-settings.js
  js/lockscreen.js
  js/lockscreen-indicators.js
  js/qs.js
  js/status-bar.js
  js/osd.js
  css/launcher.css
  css/lockscreen.css
  css/status-bar.css
  css/widgets.css
  tests/

pwa/nuxel-apps/
  notes/
  files/
  photos/
  media/
  settings/

services/nuxel-bridge/src/
  api.py
  bridge.py
  hw_providers.py
  system_indicators.py
  pwa_store.py
  media_store.py
  usb_mode.py
  tri_link_status.py

services/nuxel-session/systemd/
  nuxel-button-manager.service
  nuxel-wl-fb.service
  nuxel-wayland.service
  related host/session units

tools/s10plus/a34/
  nuxel-button-manager.c
  nuxel-button-fsm.h
  nuxel-wl-fb.c
  nuxel-wl-snapshot.c
  tests/

tools/s10plus/a45/
  nuxel-pwa-host.c
  nuxel-button-manager.c

tools/s10plus/a68/
  nuxel-screenshot.c

images/s10plus/
  build-phone-rootfs-inside-fedora.sh

configs/nuxel/
  input/button-fsm.json
  buttons/reboot-gate.json
  power/power-menu.json
  leds/leds.json
  capabilities/
```

Also inspect the repo’s PWNAGE-40000 through PWNAGE-43000 history where it explains an active contract, but treat the checked-in current code and the rootfs builder as authoritative for what the current image actually runs.

## 1.2 Active S10+ build path — critical

The current image builder is:

`images/s10plus/build-phone-rootfs-inside-fedora.sh`

The build script compiles these current phone binaries from source:

- A34 `nuxel-button-manager` from `tools/s10plus/a34/nuxel-button-manager.c`.
- A45 `nuxel-pwa-host` from `tools/s10plus/a45/nuxel-pwa-host.c`.
- A34 `nuxel-wl-fb` from `tools/s10plus/a34/nuxel-wl-fb.c`.
- A34 `nuxel-wl-snapshot` from `tools/s10plus/a34/nuxel-wl-snapshot.c`.

It installs the button manager and PWA host under `/usr/lib/nuxel/`, installs the snapshot utility at `/usr/local/bin/nuxel-wl-snapshot`, and installs `services/nuxel-session/systemd/nuxel-button-manager.service`, whose `ExecStart` is `/usr/lib/nuxel/nuxel-button-manager`.

Therefore the A34 button manager is the active source compiled for the S10+ image. Do not only patch A33 and call it fixed. Do not change the build to a third implementation without understanding why.

## 1.3 The power-menu parity defect

A concrete source/test mismatch has already been found:

- `configs/nuxel/input/button-fsm.json` defines **15** entries.
- `tools/s10plus/a33/nuxel-button-fsm.h` mirrors those 15 entries.
- `tools/s10plus/a34/nuxel-button-fsm.h`, used by the active A34 manager, defines only **11** entries.
- The four missing A34 entries are `Back`, `Forward`, `Stop loading` and `Reload launcher`.
- `tools/s10plus/a33/tests/test-button-fsm.py` tests A33. Its passing result does not prove the image’s A34 menu matches the JSON.

The shared visible power menu is rendered in `pwa/nuxel-home/js/osd.js` from the OSD document published by the hardware-button manager. The A34 source and the `configs/nuxel/input/button-fsm.json` document must agree entry-by-entry, as must the tests and the action dispatcher.

The user requested the extended legacy menu back. Restore the full configured menu in the active A34 build, rather than quietly accepting the 11-entry subset. Ensure every entry has an actual host/manager action or a clear disabled/refused state. Do not invent a success path for unsupported actions.

## 1.4 Screenshot packaging mismatch

The A45 PWA host defines:

`SHOT_BIN "/usr/lib/nuxel/nuxel-screenshot"`

and invokes it with a destination PPM path. It converts the resulting PPM to PNG with zlib and saves it under:

`/home/nuxel/Gallery/nuxel-screenshot-<UTC timestamp>.png`

However, the S10+ rootfs builder currently compiles and installs `nuxel-wl-snapshot` at `/usr/local/bin/nuxel-wl-snapshot`; it does not compile/install a binary at the exact `SHOT_BIN` path. The repository contains `tools/s10plus/a68/nuxel-screenshot.c` and A34 `tools/s10plus/a34/nuxel-wl-snapshot.c` as possible Wayland screencopy helpers. Compare their arguments, Wayland runtime expectations, output format and exit behavior. Do not simply symlink two programs without checking compatibility.

The physical Power + Volume Down chord is already mapped to `screenshot` in the FSM. The host already contains PNG conversion and Gallery-save code. The mission must close the compile/install/runtime gap and verify it on-device.

## 1.5 Launcher drag architecture

`pwa/nuxel-home/js/launcher.js` already contains a 450 ms long-press drag implementation:

- `_bindPointerEvents()` binds pointerdown/move/up/cancel at document level.
- `_onPointerDown()` tracks `pointerId`, start position, `dragTarget`, `hasMoved`, a long-press timer and edit mode.
- `_onPointerMove()` cancels a pending long press after a movement threshold and updates an active drag.
- `_startDrag()` creates drag model state and a ghost.
- `_updateDrag()` tracks drop/edge targets.
- `_endDrag()` commits or cancels and persists the layout.

The problem is not absence of drag source code. Inspect the full path with physical touch on WebKitGTK. In particular inspect pointer capture, pointer cancellation, touch-action, target removal during render, hit testing, overlay z-order, long-press timer ownership and layout insertion/reordering. Preserve the existing add/remove behavior.

## 1.6 Widget page-index defect

`launcher.currentPage` is zero-based and starts at `0`. A desktop displayed to the user as “Desktop 2” is therefore `currentPage === 1`.

The Home Settings Notes widget selector stores a human-facing desktop number starting at `1`, and currently defaults to `2`. `widgets.js` stores `item.desktop` as `2` and compares it directly against `launcher.currentPage`. `NuxelWidgets.add()` also re-renders using `launcher.currentPage`, which makes a widget assigned to the second desktop fail to appear on the actual second desktop.

The current `pwa/nuxel-home/tests/test-widgets.js` manually does `launcher.currentPage = 2; W.renderPage(2)`. This does not exercise the actual second launcher desktop; it masks the indexing defect. Fix the data contract and rewrite the tests around the real launcher lifecycle.

Use one canonical representation internally. A recommended model is one-based persisted `desktop` values `1..desktopCount`, with rendering comparing `item.desktop === launcher.currentPage + 1`, and all user selectors explicitly one-based. Another consistent zero-based schema is acceptable, but add a migration for existing saved widgets and test it. Never mix the two conventions.

## 1.7 Other concrete findings

- `pwa/nuxel-home/js/home-settings.js` reconstructs the settings panel using `innerHTML` each time it opens. It repeatedly creates controls and handlers instead of preserving a cached panel instance.
- `pwa/nuxel-home/js/widgets.js` currently renders only a basic Notes card. It has no real resize/reposition/editor lifecycle.
- `pwa/nuxel-apps/notes/js/notes.js` uses Bridge `storage.read` / `storage.write` plus localStorage fallback, with one-second autosave and truthful save-failure messaging. Preserve data on failed writes and make the widget consume the same saved document.
- `pwa/nuxel-apps/files/js/files.js` replaces the entire file grid through `innerHTML` and binds a click handler to each `.file-item`. It has no Send button or Bluetooth action.
- The actual Gallery app is `pwa/nuxel-apps/photos`, registry ID `org.nuxel.Photos`. `photos.js` renders a `<video preload="metadata">` element in each video grid cell and replaces it with “Video could not be decoded” on browser decode error. `pwa_store.storage_media_list()` currently returns metadata only; no real thumbnail endpoint is present.
- `services/nuxel-bridge/src/system_indicators.py:get_indicators()` already returns canonical provider data for charging, USB data connection, live console, console transports, file transfer, connection mode and Bluetooth. Reuse it. Do not build a competing set of guessed sysfs predicates in the PWA.
- `services/nuxel-bridge/src/usb_mode.py` and `system_indicators.connection_mode_state()` distinguish selected file-transfer mode from the endpoint actually active. Show `file` only when `file_transfer.active` is true.
- `pwa/nuxel-home/js/lockscreen-indicators.js` already polls and normalizes system indicators for the lockscreen. Reuse its provider contract or extract a shared read-only client model; do not start another high-frequency bridge poller for expanded Quick Settings.
- `pwa/nuxel-home/js/qs.js` supports Wi-Fi, Bluetooth, mobile, Location, DND, flashlight, rotation and settings tiles. Its generic `_toggle()` reports Flashlight as unavailable. Location is already backed by the bridge.
- The status bar currently has no Location, sound-mode or USB cells. It adds `.charging` to `.battery-icon`, but `status-bar.css` does not provide a lightning glyph. `_acceptBatteryLevel()` sets `batteryCharging` true when status is `full`, contradicting the surrounding code comment that Full is not active charging. Correct this state bug.
- Button-manager sound mode cycles `normal → vibrate → silent` and persists `/var/lib/nuxel/audio/sound-mode`. The mixer switch is enabled only for normal. The source explicitly records that vibrate is not yet proof of a working haptic path. The top icon must reflect the selected mode, but do not tell the user that the handset physically vibrates unless the vibrator path is verified.
- Button-manager flashlight handling currently writes `/run/nuxel/flashlight.request` and sends `action flashlight` to the PWA host. It explicitly says that the camera/flashlight arbitration path owns the LED. No complete active flashlight consumer has been established by this audit. The Quick Settings tile itself is unimplemented. `tools/s10plus/a33/nuxel-led-diag.sh` and `configs/nuxel/leds/leds.json` are the diagnostic/policy starting points.
- `nuxel-led-diag` offline tests pass, but the capability manifest marks visible physical torch proof as `NEEDS_OWNER_TEST`; an offline fixture does not prove that the physical S10+ flashlight illuminates.
- The S10+ GNSS path has caveats. `services/nuxel-s10/bin/nuxel-gps-status` documents BCM4773’s Broadcom BBD/LHD firmware path as blocked. A Location service being enabled is not necessarily a GNSS satellite fix. Show Location-service state, and show a separate fix state only if the provider supplies real fix evidence.
- The rootfs package list includes `bluez` and `bluez-deprecated`, but do not assume an OBEX object-push daemon or a compatible Bluetooth transfer service is installed. Detect and add the correct Fedora package/service if the configured repository provides it.
- The rootfs currently installs `mpv`; it does not prove that the `ffmpeg` CLI is installed. Check available decoders and package sources before choosing the thumbnail generator. Do not assume browser `canPlayType()` proves that every video is decodable.

---

# 2. HARD RULES — SAFETY, PRESERVATION AND TRUE HARDWARE OWNERSHIP

These are non-negotiable.

## 2.1 No flashing / no bootloader operations

This mission is not a kernel migration or device flashing mission.

Forbidden:

- Heimdall, Odin, fastboot, bootloader entry or bootloader flashing.
- Recovery or Download Mode execution.
- Raw partition writes or direct block-device changes.
- `dd` to a block device.
- `reboot -f`, sysrq-trigger reboot, or forced reset commands.
- Disabling or weakening the existing reboot gate to make a test pass.

The power-menu Recovery and Download Mode entries remain visible only as safely refused entries if the existing UX expects them. Preserve the code’s `NO_FLASH_INVARIANT`.

## 2.2 Keep the existing reboot gate

All restart and poweroff actions must remain through the current gated userspace manager. Preserve every applicable condition:

- Gate enabled.
- Per-action `allow_restart` / `allow_poweroff` permission.
- The 1800-second minimum interval, unless a configuration migration explicitly preserves the current value.
- The maximum of one reboot/power-off per hour, unless configuration explicitly and safely changes it with owner approval.
- Verified rollback path.
- The AND relationship with `/var/lib/nuxel/reboot/policy.json` if that policy exists.
- Existing audit log and state record.

Do not bypass the manager by calling `systemctl reboot` directly from JavaScript or the PWA host. A gate refusal is a correct safety result, not a reason to patch around it.

## 2.3 One framebuffer owner only

The S10+ uses the software-rendered Wayland/Pixman/shared-memory display path. `nuxel-wl-fb` owns `/dev/fb0` and commits frames through the Samsung DECON behavior.

- Do not open `/dev/fb0` in a PWA, screenshot helper, media helper or second display service.
- Do not add another framebuffer daemon.
- Do not remove the Wayland screencopy path for screenshots.
- Do not assume `/dev/dri`, DRM/KMS, EGL/GBM or a hardware GPU exists.
- Keep the current `nuxel-wl-fb` ownership lock/handoff behavior intact.

“fbdev-friendly” means optimizing the UI and software rasterization pipeline, not bypassing Wayland or introducing a competing scanout writer.

## 2.4 Preserve user data and SSH

- Never delete user photos, videos, notes, media, saved layouts, application data or configuration as part of a fix.
- Migrate existing formats in place, with backups and rollback.
- Preserve the active SSH path and network configuration.
- Do not invent an SSH IP, password or host alias. Use the already configured deployment target if present. If it is unavailable, finish local repo work and produce exact deployment commands for the operator.
- Keep all changes within the Nuxel source/release workflow. Do not patch only the live device and leave the repository stale.

## 2.5 Truthful state

Use the distinction between `UNKNOWN`, `OFF`, `ON/selected`, and `ACTIVE/verified`.

Examples:

- File Transfer mode selected is not file transfer active.
- USB cable present is not necessarily an active USB file-transfer endpoint.
- Charging is not the same as externally powered but battery full.
- Location service enabled is not the same as a satellite GPS fix.
- Sound mode selected as vibrate is not proof that the vibrator has physically actuated.
- A flashlight request is not proof that the LED lit.
- A thumbnail poster is not proof that the video codec can play.

---

# 3. P0 — FIX HOME ICON LONG-PRESS DRAG AND REORDER

## 3.1 Observed behavior

Adding an application from the drawer and removing it from Home works. The user can hold an application icon, but cannot successfully pick it up and move it from its location.

The existing implementation is in `pwa/nuxel-home/js/launcher.js`; relevant methods include `_bindPointerEvents`, `_onPointerDown`, `_onPointerMove`, `_onPointerUp`, `_cancelPointer`, `_startDrag`, `_updateDrag` and `_endDrag`. CSS is primarily in `pwa/nuxel-home/css/launcher.css`.

## 3.2 Trace the entire event lifecycle

Before editing, instrument and observe a real device touch sequence:

1. `pointerdown` on a normal Home icon.
2. 450 ms stationary hold.
3. Long-press timer fires exactly once.
4. Edit mode appears.
5. Drag ghost attaches to a stable parent.
6. `pointermove` continues after leaving the icon’s original bounds.
7. Drop target is found by live coordinates.
8. `pointerup` commits exactly once.
9. Layout is persisted and the icon remains in its new position after a Home restart.

Record `pointerId`, `pointerType`, `isPrimary`, target, current target, pointer-capture owner, drag state, event timestamps and pointer-cancel reason. Use logs only during diagnostics; remove or gate high-volume production logging after the defect is fixed.

Inspect these likely failure surfaces rather than guessing:

- The long-press timer closes over the original pointer event; ensure no state assumes an event object remains live after dispatch.
- Pointer capture is not clearly owned by a stable element for the complete drag lifecycle.
- The icon may be removed or re-rendered while drag state still points at the original element.
- The `.app-grid` / `#app-grid` / `#app-list` touch-action and momentum-scroll rules may let WebKit take over the gesture and dispatch `pointercancel`.
- Global `touchstart` / `touchend` page-swipe handlers may compete with pointer drag.
- `_cancelPointer()` must cancel pending timers and roll back a started drag without accidentally committing.
- The ghost/drop preview may be covered by the app list, QS, navigation or drawer layers.
- `_updateDrag()` must locate the drop target using the pointer coordinates, not rely only on `event.target`, because the target changes during a drag.
- A drag started from a drawer item has different behavior from a Home reordering drag; preserve both.

## 3.3 Required input model

Keep one authoritative pointer interaction state machine. Use explicit states such as:

```text
IDLE
  -> PRESS_PENDING
  -> LONG_PRESS_READY / EDITING
  -> DRAGGING
  -> DROP_COMMIT
  -> IDLE

Any active state -> CANCELLED -> IDLE
```

Requirements:

- Track the initiating `pointerId` and reject secondary contacts.
- Acquire pointer capture on an element that remains mounted for the gesture, such as a stable grid/root interaction surface. Do not capture solely on an icon that may be replaced during rerender.
- Release capture on every completion and cancellation path.
- Start the long-press timer only for a valid primary pointer.
- Cancel the timer when movement exceeds the deliberate hold slop before long press; do not mistake ordinary taps/swipes for a drag.
- Once a long press has entered edit/drag state, keep receiving pointer moves outside the source tile.
- Do not allow scroll/pan recognition to steal an active drag. Use an appropriate touch-action policy established before pointerdown; if necessary, put `touch-action:none` on draggable app tiles and preserve page swipes through the launcher’s own gesture code on non-tile areas.
- Avoid passive and active duplicate processing of the same finger through pointer and touch handlers. Use a single pointer source for icon drag.
- Preserve app tap-to-launch, accessibility keyboard activation, drawer long-press Add-to-Home context menu and the fixed dock’s existing behavior.
- Show a clear edit/drag affordance and a ghost that follows the finger without blocking hit-testing (`pointer-events:none`).
- Support reordering before, between and after icons; same-page drop; cross-page drop; and edge-hover page switching with a bounded timer.
- A drop outside a valid target must have a defined safe outcome: return to the previous location unless the current existing behavior specifies a valid append target.
- A pointercancel, lostpointercapture, navigation or hidden screen must cancel and restore the original layout.
- Persist only on a successful drop; do not save every move event.
- Keep existing add/remove and hidden-app restore behavior unchanged.

## 3.4 Regression tests

Add browser-level pointer-event tests using the same event route as the physical WebKitGTK browser. DOM-light unit tests are useful but cannot be the only evidence.

Cover:

- Short tap launches once.
- Stationary 450 ms hold enters edit/drag once.
- Moving before 450 ms cancels the hold and preserves swipe behavior.
- Long press followed by move reorders an icon.
- Reorder first-to-last and last-to-first on the same page.
- Cross-page move commits to the intended page.
- Edge-hover changes page without losing pointer ownership.
- `pointercancel` and `lostpointercapture` restore the original layout.
- Secondary pointer cannot end or hijack the primary drag.
- Releasing over another app does not launch it.
- Drawer Add-to-Home still works.
- Remove from Home still works.
- Layout survives a launcher reload/restart.
- Home-locked mode refuses reordering and leaves positions unchanged.

Record a physical on-device proof sequence. A green synthetic test without a physical touch test is not complete.

---

# 4. P0 — NOTES APP, STICKY NOTES WIDGETS AND DESKTOP-2 FIX

## 4.1 Current architecture

- Notes application: `pwa/nuxel-apps/notes/js/notes.js`.
- Home widgets: `pwa/nuxel-home/js/widgets.js` and `css/widgets.css`.
- Home Settings: `pwa/nuxel-home/js/home-settings.js`.
- Widget rendering integrates into `launcher.js` after each grid render.
- Notes app saves via Bridge `storage.read` / `storage.write` under the key `nuxel-notes` and also updates localStorage as a fallback.

Preserve the current note model and existing saved notes. Do not replace it with a new unrelated data store.

## 4.2 Fix persistence and synchronization

Inspect the exact Bridge reply shape for `storage.read` and `storage.write` through `services/nuxel-bridge/src/api.py` and `pwa_store.py`. Verify the deployed Bridge protocol version and app ID requirements.

Requirements:

- Creating a note, editing title/body, Save/Done and autosave must persist successfully to the canonical Bridge store.
- Do not show “Saved” before the Bridge operation has succeeded. A local-only/offline save must be labelled accurately, and content must never be thrown away on failure.
- Avoid concurrent saves racing: use a save sequence/revision or a serialized queue so an earlier completion cannot mark newer text as saved.
- Keep localStorage as a deliberate offline/cache layer, not an independent competing source of truth.
- Make the Home widget receive the latest note after a successful save. Do not rely only on `storage` events if the Home host/WebKit contexts do not share an event lifecycle. Publish a same-window custom event or use a shared Notes document adapter/store that notifies both apps.
- Handle note deletion: widgets referencing a deleted note should become a clear empty/reselect state, not display stale body data or crash.
- Handle missing/invalid data and schema migration without deleting user data.

## 4.3 Fix one-based/zero-based desktop mapping

This defect is confirmed:

- `launcher.currentPage` is zero-based (`0` is the first visible desktop).
- Home Settings uses human-facing desktop numbers starting at `1`.
- Widget documents currently use the same `desktop` field for both concepts.
- The default selector uses desktop `2`, but rendering compares the stored `2` directly with the active page index. The actual second desktop is index `1`.
- Existing `test-widgets.js` manually sets `currentPage = 2`, so it does not exercise the actual second page.

Select one canonical data contract and document it. Recommended:

- Persist widget `desktop` as a one-based desktop number (`1..desktopCount`) for readable saved data.
- In `renderPage(pageIndex)`, compare `widget.desktop === pageIndex + 1`.
- In `add()`, default to `launcher.currentPage + 1`.
- Home Settings selector values remain one-based.
- Add a migration for old stored entries, if their meaning can be established; do not silently shift all old widgets onto a different page.

Alternatively use zero-based persisted values, but convert at every UI boundary and test migration. Never use a mixture.

## 4.4 Implement a real Notes widget lifecycle

The requested result is an actual sticky note on the second desktop, not just a text block that may render in tests.

Implement:

- “Enable widgets” setting that works and persists.
- Add Notes widget button that is disabled with a clear reason when no note exists.
- Note selector containing the real Notes list, with safe text rendering (no HTML injection).
- Add widget to the chosen desktop; default initial widget placement should be desktop 2 if that page exists, otherwise a valid visible page.
- A widget with visible note title and body snippet, updated when the note is saved.
- Tap widget opens the correct note in Notes, not merely an arbitrary note list. Pass a selected note ID/deep link or add a Notes open-note contract.
- Remove widget.
- Resize widget (minimum/maximum columns and rows bounded by the actual Home grid).
- Reposition widget by drag, using a pointer-safe interaction model that does not conflict with app-icon movement or Home page swipes.
- Persist widget position, dimensions, note ID and desktop; restore after reload/reboot.
- Clear handles or a context menu for edit/remove/resize. Keep widget editing separate from application icon editing.
- Prevent overflow of large notes; clamp rendered body text and keep scrolling intentional.
- Keep sticky-note appearance legible on the actual low-resolution/soft-rendered panel. Avoid backdrop blur and heavy shadows.

## 4.5 Home Settings widget UI

Fix Home Settings so it is usable and quick:

- Avoid rebuilding the entire modal HTML on every open if the existing panel can be cached.
- Bind handlers once or use delegated events.
- Load notes and widget state asynchronously without blocking the first paint.
- Show the selected desktop and selected note clearly.
- Update the actual widget list/state after add/remove/resize.
- Do not add a widget when there is no selected or available note and then alert after inserting an empty widget.
- Do not retain stale note options when Notes changes; refresh via the shared notes event/store.

## 4.6 Widget tests

Rewrite/extend `pwa/nuxel-home/tests/test-widgets.js` to test the real launcher convention:

- Actual `launcher.currentPage = 0` renders desktop 1 only.
- Actual `launcher.currentPage = 1` renders desktop 2 only.
- An item created through Home Settings with `desktop=2` appears when `currentPage=1`, not page index 2.
- Default desktop mapping uses `currentPage + 1`.
- Saved widgets migrate and remain on their intended desktop.
- Add, remove, enable/disable and reload persistence.
- Resize and move persist across rerender.
- Note edits notify and update widget content.
- Note deletion does not leave stale text.
- Add with no notes does not create a broken empty item.
- Tapping opens the chosen note ID.
- HTML-like note text is rendered safely.

Add a Notes-app persistence test with Bridge success, Bridge failure, offline fallback and a save race.

---

# 5. P0 — SPEED UP THE LOCKSCREEN, APP DRAWER/WINDOW AND HOME SETTINGS

## 5.1 Optimize for the actual display, not a hypothetical GPU

This device uses a software-rendered Wayland path. The repository’s `nuxel-wl-fb.c` comments document a headless Phoc/wlroots Pixman path using shared-memory screencopy. The phone kernel has no normal DRM/KMS device path. `nuxel-wl-fb` is the sole `/dev/fb0` writer and presents paced frames to the Samsung DECON panel.

Therefore:

- Keep UI rendering compatible with WebKitGTK and Pixman/software rasterization.
- Do not add a dependency on GPU compositing, WebGL, EGL effects or DRM.
- Do not bypass Wayland by writing framebuffer pixels from the PWA.
- Minimize the amount of CSS/DOM work that must be rasterized every frame.
- Keep pointer/touch interactions responsive at the real presentation cadence.

## 5.2 Measure before editing

For each surface, capture a repeatable baseline and post-change result:

- Lockscreen initial paint/readiness after lock and wake.
- Lockhead pickup, drag and unlock feedback.
- App drawer open/close, first icon paint and scroll.
- App window open/close, transition and return Home.
- Quick Settings compact open/close and expanded open/close.
- Home Settings open/close and control response.
- Files directory load/scroll for small and large directories.
- Gallery grid first paint with many photos/videos.

Record:

- `performance.now()` marks around interaction start and render completion.
- Approximate input-to-first-visible-feedback latency.
- `requestAnimationFrame` frame-time samples during animation/scroll.
- Long tasks over 50 ms.
- WebKit process CPU and memory where the running environment exposes them.
- Number of simultaneous timers, Bridge requests and DOM nodes for each visible surface.

Do not insert a heavy telemetry loop into production. Keep a dev-only profiling mode or bounded diagnostics and remove noisy logs from normal use.

Target at least a 25–30% reduction in the measured slow paths, stable scrolling and immediate input acknowledgement. Aim for the frame cadence the actual S10+ pipeline can sustain. Record any screen where hardware/system constraints prevent the target; do not invent performance claims.

## 5.3 Lockscreen

Inspect:

- `pwa/nuxel-home/js/lockscreen.js`
- `pwa/nuxel-home/js/lockscreen-indicators.js`
- `pwa/nuxel-home/css/lockscreen.css`
- `pwa/nuxel-home/index.html`

The lockscreen CSS already documents a previous measurement: removing costly alpha-image/indicator filters reduced WebKit software-renderer CPU from roughly 440% to 78% in the earlier test. Preserve those wins.

Tasks:

- Profile the clock, battery updates, touch-warning poll, indicator poll, wake events, lockhead wiggle and unlock gesture.
- Stop or slow polling when lockscreen is not visible/locked, and resume with one immediate bounded refresh on lock/wake.
- De-duplicate indicator reads; `NuxelLockscreenIndicators` already has in-flight/pending logic and a bounded 3-second safety interval. Do not create another poller that makes the same request.
- Ensure the lockhead’s short idle wiggle is not an infinite CSS animation. Respect `prefers-reduced-motion`.
- Remove any remaining software-expensive idle filters, repeated blur/shadow effects or large repaint surfaces.
- Use transforms only for the moving handle. Avoid layout changes on every pointermove.
- Batch geometry reads before writes; avoid reading layout after writing style in the same interaction frame.
- Keep the unlock threshold, pointer capture, connection-mode buttons and visible indicator states intact.
- Do not remove useful lockscreen indicator feedback just to reduce CPU; make it static or event-driven instead.

## 5.4 App drawer and app/window surfaces

Inspect `launcher.js`, launcher CSS, app registry, navigation/recents integration and any iframe/window transitions.

- Profile opening/closing and app activation, including first render.
- Avoid rebuilding the same registry/icon DOM unnecessarily if it has not changed.
- Use a stable fragment or cached representation for drawer content; invalidate when app registry changes.
- Keep app labels, icons, hidden-app behavior, folder behavior and keyboard access.
- Do not introduce a large image preload storm when opening the drawer. Lazy-load nonvisible icon art where safe; retain the icons required for first paint.
- Limit animation to short opacity/translate transforms; avoid filters, blur, large shadows and width/height animation.
- Avoid synchronous repeated geometry reads.
- Keep one visible active app surface and preserve existing Home/background/recents semantics.
- If virtualization is needed, implement it with stable keys and preserve scroll position/focus; do not virtualize a tiny app list needlessly.
- Ensure application windows do not flash white/black during transitions due to full DOM/iframe teardown.

## 5.5 Quick Settings

Inspect `pwa/nuxel-home/js/qs.js`, its markup and CSS.

- Profile `_render`, `_syncState`, `_syncBluetooth`, `_syncLocation`, verbose boot state, rotation state and open/expand/close transitions.
- Ensure no duplicated bridge calls on open.
- Use one in-flight read per provider and discard stale responses after the panel closes.
- Stop all repeated polling when closed. Use a bounded low-frequency refresh while visible and refresh immediately on a real wake/state event.
- Update only changed tile labels/classes instead of rewriting the whole panel.
- Preserve current wifi/BT/mobile/Location/DND/rotation behavior.
- Make flashlight real as described in section 10.
- Add expanded connection indicators as described in section 12.
- Use compact tile artwork with no heavy filter/blur.
- Keep rotation long-press behavior and verbose-boot tile working.

## 5.6 Home Settings

`home-settings.js` currently reconstructs the panel via `innerHTML` on each `open()`. Optimize this concrete path:

- Build/cache the panel DOM once where possible.
- Use one set of event listeners; avoid handler accumulation.
- Separate initial panel paint from async provider hydration.
- Avoid repeated `NuxelWidgets.notes()` JSON parsing for each selector update.
- Avoid layout thrash while previewing wallpaper/dock artwork.
- Keep wallpaper, dock background, grid columns/rows, desktop count, home lock, battery style, system monitor, widget, lock timeout, restore hidden apps and reset layout settings working.
- Do not introduce expensive wallpaper filters.
- Close/hide the modal without deleting its controls or losing focus state.
- Make long-press on wallpaper open Settings once; do not let the same pointer trigger a Home icon drag.

## 5.7 Performance acceptance

- No unbounded polling while hidden.
- No duplicate high-frequency `system/indicators` polling for lockscreen and QS.
- No continuous full-screen CSS animations while idle.
- No expensive filters/backdrop filters in the main interactive screens.
- All state updates are bounded and stale network/Bridge responses are ignored after a surface closes.
- At least 25–30% measurable improvement on the initially slow surfaces, or a documented hardware ceiling with a concrete measured improvement.
- No feature regressions or loss of touch interactions.

---

# 6. P0 — FILE EXPLORER RENDERING AND SCROLLING PERFORMANCE

## 6.1 Current cost center

`pwa/nuxel-apps/files/js/files.js` currently:

- Retrieves a directory listing from Bridge `storage.list-dir`.
- Replaces the complete `#file-grid` content using `innerHTML` for every render/selection change.
- Creates a per-item click listener for every `.file-item` after each render.

This is unnecessarily expensive for large directories and repeated selection changes.

## 6.2 Requirements

- Keep the existing Files API operations and directory semantics: list, navigate, refresh, create folder, rename, delete, copy, cut, paste, archive and extract.
- Use safe text/attribute escaping or DOM APIs; no path/name HTML injection.
- Use one delegated click listener on the grid and resolve the clicked item with `closest('.file-item')`.
- Render with a `DocumentFragment` or small DOM batches.
- For large directories, use progressive batches or windowed/virtualized rendering with a stable scroll container and a correct total scroll range. Do not render hundreds/thousands of heavy nodes in one synchronous long task.
- Preserve selection by canonical path across rerender and refresh; clear entries that have genuinely disappeared.
- Keep selection-toolbar enabled/disabled state synchronized without rebuilding every tile.
- Avoid full list redraw when only selection styling changes; toggle the affected tile classes and update summary controls.
- Lazy-load any future file preview/thumbnail and only for visible items.
- Preserve folder-first order and deterministic sorting.
- Avoid `will-change` on every tile; avoid large shadows and filters.
- Keep touch momentum scrolling and make tap targets comfortable on the handset.
- Add a clear empty state and incremental loading/error state for slow Bridge operations.

Add regression/performance tests for 0, 30, 250 and 1000 entries, plus select/deselect all, multiple selection, scroll-position retention after rename/delete and no duplicate item actions.

---

# 7. P0 — RESTORE THE FULL EXTENDED POWER MENU IN THE ACTIVE A34 BUILD

## 7.1 Required behavior

A long Power hold must open the complete extended Nuxel power menu. The user specifically requests the old extended menu back, with Restart, Power off and all existing reboot modes.

The menu is driven by the hardware FSM and OSD document, not by the separate Settings power screen.

Relevant files:

- `tools/s10plus/a34/nuxel-button-manager.c`
- `tools/s10plus/a34/nuxel-button-fsm.h`
- `configs/nuxel/input/button-fsm.json`
- `configs/nuxel/buttons/reboot-gate.json`
- `configs/nuxel/power/power-menu.json`
- `services/nuxel-session/systemd/nuxel-button-manager.service`
- `tools/s10plus/a45/nuxel-pwa-host.c`
- `pwa/nuxel-home/js/osd.js`

## 7.2 Restore A34/config/test parity

The checked-in config contains these 15 entries:

1. Cancel
2. Lock screen
3. Take screenshot
4. Restart
5. Power off
6. Reboot Verbose
7. Safe Mode
8. Reboot Diag
9. Reboot Debug
10. Back
11. Forward
12. Stop loading
13. Reload launcher
14. Recovery (Samsung)
15. Download Mode (Odin)

The active A34 header currently compiles only 11 and omits the four browser-control entries. Fix the active implementation so the menu table exactly matches the authoritative JSON, or update a canonical shared definition so there can be no silent generation drift. Prefer one source of truth over manually duplicated arrays.

Crucially, add a test that compiles/inspects the actual A34 FSM source used by `build-phone-rootfs-inside-fedora.sh`. The existing A33-only `test-button-fsm.py` is not enough. Keep A33 parity if it remains supported, but make the build target the test’s explicit input.

## 7.3 Validate each menu action end-to-end

- Cancel: closes menu safely.
- Lock screen: invokes the existing lock path and returns to the real lockscreen.
- Screenshot: uses the repaired capture helper and reports success/failure.
- Restart: goes through A34 button manager’s reboot gate; never direct from PWA JavaScript.
- Power off: uses the per-action gate.
- Reboot Verbose: writes the correct one-shot flag before starting the gated reboot.
- Safe Mode: same verified one-shot sequence.
- Reboot Diag: same verified one-shot sequence.
- Reboot Debug: same verified one-shot sequence.
- Back: performs the defined foreground-app/browser back behavior; if there is no valid back target, return a truthful no-op/refusal.
- Forward: works only when a real forward target exists; otherwise visibly disabled or reports unavailable.
- Stop loading: stops an actual foreground PWA/native browser load through the host contract; do not kill unrelated processes.
- Reload launcher: reloads the launcher safely without killing the host/compositor or losing persistent user state.
- Recovery and Download Mode: remain hard-refused by `NO_FLASH_INVARIANT`. Do not wire a bootloader operation.

If an action depends on foreground state, make the state visible and keep the menu safe when there is no foreground app.

## 7.4 OSD interaction

`pwa/nuxel-home/js/osd.js` renders the entries/index published to `/runtime/osd.json`. Verify:

- Menu opens and remains visible until an action, Cancel, second hold or configured timeout.
- Initial selection is safe (Cancel as defined by the source/config).
- Volume-key navigation follows the manager’s selected index.
- Touching a row dispatches the same manager action as the hardware navigation path.
- Gated/refused actions show a clear refusal reason, not a blank screen or silent failure.
- Menu scrolls on the actual 360 CSS-pixel viewport.
- The OSD polling interval is bounded; when the menu is open it follows state changes quickly and backs off when the menu is closed.
- The menu is not clipped behind QS/navigation/app surfaces and does not cause heavy full-screen blur.

## 7.5 Hardware key arbitration must remain correct

Preserve existing behavior:

- Power short: display toggle.
- Power long: power menu.
- Power double: camera.
- Power + Volume Up: sound-mode cycle.
- Power + Volume Down: screenshot.
- The screenshot chord is decided before long/very-long Power action; it must suppress the single-key classes for that hold.
- Samsung emergency hardware combinations continue to be delivered to the kernel/bootloader because the manager does not `EVIOCGRAB` the key/touch device.
- No second button manager is started.

Add A34 tests proving chord arbitration and menu selection. Do not break the existing FSM trace semantics.

---

# 8. P0 — REPAIR POWER + VOLUME DOWN SCREENSHOT AND GALLERY SAVE

## 8.1 Fix the helper path mismatch

Audit:

- Host `SHOT_BIN` and the exact `execl()` arguments.
- A68 `nuxel-screenshot.c` CLI/output contract.
- A34 `nuxel-wl-snapshot.c` CLI/output contract.
- Rootfs build compile and install loops.
- Runtime user/session permissions and Wayland socket environment.

Choose one correct solution:

**Option A:** compile `tools/s10plus/a68/nuxel-screenshot.c` in the ARM64 image builder, install it at `/usr/lib/nuxel/nuxel-screenshot`, verify its screencopy interface and output PPM contract, and include it in architecture/file/checksum build checks.

**Option B:** refactor the host to execute the already-installed `/usr/local/bin/nuxel-wl-snapshot` only after confirming that its arguments and output format exactly match what the host expects. Update the path constant, package tests, dependencies and documentation.

Do not ship an executable path that does not exist. Do not depend on a previous live deployment’s stray helper.

## 8.2 Capture requirements

- Preserve Power + Volume Down mapping in the active A34 FSM and config.
- Capture the current Wayland-composited frame through `zwlr_screencopy_manager_v1` (or the project’s existing equivalent). Never read `/dev/fb0` directly.
- Validate the output PPM/PNG dimensions, pixel format and successful completion.
- Convert to a genuine PNG with correct row lengths, color format and CRC/chunks if the host continues its built-in conversion.
- Save to `/home/nuxel/Gallery/` with a collision-resistant timestamp/name. Use atomic temp-file then rename so Gallery cannot read a partially written file.
- Set correct `nuxel` ownership/group and safe permissions. Ensure folder exists.
- Return a structured result with `success`, exact path and dimensions on success; a structured error on failure.
- Bound helper execution time; terminate only the helper child that was started if it exceeds its timeout.
- Clean temp PPM/temp PNG files in success and error paths.
- Do not acknowledge screenshot success until the PNG is fully written and indexed path is valid.

## 8.3 On-screen acknowledgement

Show a clear, transient OSD/toast such as “Screenshot saved to Gallery” after successful completion. On failure show a short, human-readable reason such as “Screenshot failed: capture helper unavailable”.

- The visual acknowledgement must not steal the next touch or block Home.
- Avoid double OSDs from the button manager and PWA host.
- Give feedback for both hardware chord and power-menu screenshot action.
- A failed screenshot must not display a success toast.

## 8.4 Verification

- Host-side helper test with fake Wayland/screencopy transport where possible.
- ARM64 build smoke test for the exact installed path.
- Live capture on the phone.
- Check PNG signature, dimensions, ownership, file size and decodability.
- Open Gallery and confirm the screenshot appears as a photo without manual refresh, or after one normal refresh if the gallery is not live-watched.
- Reboot/restart the PWA host and confirm the screenshot remains.

---

# 9. P1 — GALLERY VIDEO THUMBNAILS AND PLAYBACK BEHAVIOR

## 9.1 Current cause

`pwa/nuxel-apps/photos/js/photos.js` currently:

- Requests real media metadata through Bridge `storage.media-list` and `camera.list-captures`.
- Gets a storage file URL for each storage entry.
- Builds a `<video>` element with `preload='metadata'` in video grid cells.
- Replaces the element with the string “Video could not be decoded” after a browser media `error` event.

This means the gallery grid asks WebKit to instantiate decoders for video items even though the user only needs a still thumbnail. A browser codec error should not prevent showing a poster frame or static video thumbnail.

The current storage listing in `services/nuxel-bridge/src/pwa_store.py:storage_media_list()` scans `Gallery`, `Pictures`, `Videos` and `DCIM` and returns metadata. It is not a thumbnail generator.

## 9.2 Implement server-side thumbnail generation

Add a bounded, cacheable thumbnail service that runs on the phone, not inside the browser grid.

- Detect which media decoder is actually installed in the target image. `mpv` is present in the current package list, but an `ffmpeg` CLI is not guaranteed. Inspect available tools and libraries.
- Prefer a maintained decoder/tool available from the configured Fedora package source. Add the necessary package to the S10+ rootfs manifest if required and verify it resolves in a clean image build.
- Use a subprocess argument array with `shell=False`; never interpolate user file paths into a shell command.
- Restrict input paths to the canonical media root (`/home/nuxel` media directories or the existing MediaStore root). Resolve/validate symlinks; reject traversal and paths outside allowed roots.
- Set a strict decode timeout, output dimensions, memory/CPU bounds and file-size guard.
- Seek to a useful early frame (not necessarily time zero when there is a black lead-in); do not decode the entire video.
- Generate small WebP/JPEG/PNG stills sized for the Gallery grid; avoid serving full-resolution frames.
- Cache by stable file identity and modification metadata (e.g. canonical path + size + mtime_ns, or content hash where bounded). Invalidate when the source changes or is deleted.
- Use atomic writes and safe permissions for cached thumbnails.
- Do not overwrite source video files.
- For unsupported/corrupt/unreadable video, return a truthful “thumbnail unavailable” status and a generic video icon; never claim to have generated a frame.

Add a Bridge/API route or a typed storage RPC such as `storage.thumbnail`. It must be authenticated consistently with existing API calls, return a controlled image MIME type, and not expose arbitrary filesystem read/decode access.

## 9.3 Frontend Gallery behavior

- The grid must use `<img>` elements for still thumbnails, with `loading="lazy"`, `decoding="async"` and bounded concurrency.
- Do not instantiate an HTML `<video>` element for every grid card.
- Video cards should show the generated still frame, a video/play badge and a readable filename.
- Use IntersectionObserver or a bounded visible-item queue. If IntersectionObserver is unavailable, load only a small first batch and queue subsequent cards.
- Cancel stale thumbnail requests when a card is removed, filtered or the Gallery closes.
- Keep the full viewer separate from the grid. The viewer may create a single `<video controls>` on demand.
- If the current WebKit decoder cannot play that particular codec, keep the still poster visible, show the real playback error, and offer a compatible native playback path only if one exists and is verified (e.g. a proper mpv integration). Do not mark a video as decoded merely because a thumbnail exists.
- Ensure screenshot PNGs and camera photos continue to load as images.
- Preserve album/search/delete/export behavior.

## 9.4 Video/thumbnail tests

Use real test media where licensing permits and keep fixtures small. Cover:

- Supported MP4/H.264 sample.
- Supported WebM sample if available.
- A valid video with a codec unsupported by WebKit but supported by the server decoder.
- A corrupt/truncated video.
- Zero-byte file.
- Very large video timeout/size guard.
- Path traversal attempt and symlink escape.
- Changed source invalidates cache.
- Deleted source removes/invalidates cache.
- Gallery grid creates images, not N video decoder instances.
- Viewer uses only one active video element.
- Thumbnail endpoint rejects unauthenticated/invalid requests.

---

# 10. P1 — FLASHLIGHT: COMPLETE THE SAFE HARDWARE PATH

## 10.1 Current incomplete behavior

- Quick Settings contains a `flashlight` tile, but `qs.js` generic toggle handler reports that this control is unavailable.
- The A34 button manager’s Bixby double-press route calls `flashlight_request()`.
- That function writes `/run/nuxel/flashlight.request` and sends `action flashlight` to the PWA host.
- The manager’s own comment explicitly says it does not write the LED node because camera flash is shared with camera control and must have thermal/camera arbitration.
- The LED diagnostic/policy path is `tools/s10plus/a33/nuxel-led-diag.sh` + `configs/nuxel/leds/leds.json`.
- The `hardware-subsystems.json` capability entry marks visible physical torch proof as `NEEDS_OWNER_TEST`.

Do not “fix” this by writing an arbitrary `/sys/class/leds/*/brightness` node from JavaScript or by bypassing camera arbitration.

## 10.2 Implement one owner/provider

First inspect live hardware and existing camera flash ownership. Identify:

- Real flashlight/torch LED class path (if any).
- Correct brightness/torch control semantics.
- Device support on this S10+ kernel.
- Whether the LED is camera-owned or available through an existing camera service/provider.
- Existing `nuxel-led-diag.sh` policy: max on time, off behavior, capability and thermal constraints.
- Any camera-active state that must block flashlight activation.

Then implement a single privileged, auditable provider/service/API that owns flashlight state. The PWA and hardware key manager send requests to it; they do not write the device node directly.

Requirements:

- Toggle on/off only through this owner.
- Verify an actual supported hardware endpoint before returning ON.
- Enforce the policy’s maximum on duration (currently documented as 60 seconds unless the canonical config says otherwise).
- Ensure an unconditional explicit OFF after timeout, shutdown, service error or loss of ownership.
- Do not auto-enable torch at boot.
- Respect thermal and camera arbitration.
- Do not leave the LED lit after a client disappears.
- Expose `UNKNOWN`, `OFF`, `ON`, `UNSUPPORTED`, `BLOCKED_CAMERA`, `THERMAL_LIMIT` and provider error distinctly where useful.
- Audit who requested the change and why it was refused.
- Add an idempotent off action.
- Provide haptic/OSD feedback only after the owner reports the result.

If the target has no usable torch class, report `NOT_SUPPORTED_ON_DEVICE`, leave the button and tile safely disabled with an explanation, and keep the diagnostic output truthful. Do not simulate light.

## 10.3 Wire all existing controls

- Quick Settings flashlight tile.
- Existing Bixby double-press path.
- Any Settings flashlight control if one exists.

All must use the same provider/service and report the same state. Toggling from one surface must update the others without duplicated backend polls.

## 10.4 Tests / physical proof

- Unit tests for missing LED class, valid fixture, permission denial, timeout, explicit off, camera-busy, thermal block and provider crash.
- Verify no raw LED write exists in JS/PWA code.
- Test repeated on/off requests and race conditions.
- Physical torch ON for a brief bounded interval, confirm actual light visually, then OFF.
- Confirm OFF after process restart / timeout.
- Record manual proof. Offline fixture PASS is not a physical hardware PASS.

---

# 11. P1 — TOP STATUS BAR: LOCATION, SOUND MODE, USB LABEL AND CHARGING BOLT

## 11.1 Add a collision-safe status model

Current status bar markup is in `pwa/nuxel-home/index.html`; status rendering is in `js/status-bar.js`; CSS is in `css/status-bar.css`.

The existing right cluster includes signal, Wi-Fi, Bluetooth and battery, with an overlap assertion in `_assertNoOverlap()`. Extend that model to include the requested indicators without allowing them to overlap on the 360 CSS-pixel viewport, cutout-safe layout or rotation.

Add status cells with stable IDs, for example:

- `status-location`
- `status-sound-mode`
- `status-usb`

Add these IDs to the overlap assertion and safe-zone/layout calculation. Do not hard-code offsets that only work in one orientation.

Prefer small local SVG icons or existing Nuxel icon assets with `currentColor`/CSS state classes. Provide accessible title/label text. Avoid emoji or fonts that may be missing in the embedded runtime.

## 11.2 Location icon

Use the same canonical Location provider already used by QS through Bridge `location/get-status` / `LocationGetStatus`.

- Show enabled state distinctly from disabled.
- Represent `UNKNOWN` or provider error distinctly; do not render UNKNOWN as OFF.
- Optionally distinguish a real fix only when provider data explicitly proves it.
- Do not call the icon “GPS fix” just because location service is enabled.
- Preserve the existing Location toggle/capability flow.
- Avoid an extra fast poller: reuse the current shared status model or a bounded update event.

The BCM4773 GNSS firmware caveat must remain visible in diagnostics. A Wi-Fi/IP GeoClue location may be a Location result but not proof of satellite lock.

## 11.3 Speaker / vibrate mode icon

The hardware chord is already defined:

`Power + Volume Up` → `sound-mode-cycle`

The button manager cycles:

`normal → vibrate → silent → normal`

and writes:

`/var/lib/nuxel/audio/sound-mode`

The top bar must reflect that same authoritative mode:

- `normal`: normal speaker indication (or no special badge if the design reserves the slot for exceptions).
- `silent`: muted speaker icon.
- `vibrate`: vibrate/bell-with-vibration icon.
- missing/unreadable mode file: unknown state, not a guessed normal mode.

Requirements:

- Add a read-only Bridge/status contract for sound mode, or include it in the canonical system-indicator response. Do not let the PWA become a second writer.
- Refresh promptly after the physical chord, with a bounded fallback poll when the Home shell is visible.
- Update the icon and tooltip only when mode changes.
- Ensure no duplicate OSDs from the manager and host.
- A vibrate icon may truthfully denote the **selected sound mode**, but the tooltip/diagnostics must not claim physical haptics until vibrator hardware/driver behavior is verified.
- Where a real vibrator exists, connect the selected vibrate mode to the existing haptics owner rather than direct sysfs writes from UI code.

## 11.4 USB cable glyph and short state label

Add a small USB cable glyph with an optional text tag inside/alongside it.

Required labels:

- `file` — only while the file-transfer endpoint is actually active (`system_indicators.file_transfer.active === true`). A requested/selected file-transfer mode alone does not count.
- `term` — when the USB console transport is actually active. Do not show `term` for an unrelated WLAN-only console unless the product UI explicitly labels that separately.
- `chrg` — when active charging is confirmed and there is no higher-priority active file-transfer or USB-terminal state.
- Cable-only/connected state — when wired USB data/power is present but none of the above applies; use the icon without a misleading tag.
- Hidden/unknown — when no wired link evidence is available, or provider state is unknown.

Use a deterministic display precedence. Recommended:

```text
if file_transfer.active:                    label = "file"
else if console_transports.usb.active:       label = "term"
else if charging.charging && usb_data present: label = "chrg"
else if usb_data.pc_connected:              show USB icon, no tag
else:                                        hide or UNKNOWN as provider warrants
```

If the charging state must also cover a charger that does not expose a host/data link, use a separate charging state/indicator; do not call a power-only charger a USB data connection.

Update immediately when a real state change arrives; otherwise use a bounded, shared poll. Avoid flashing between labels while backend data is temporarily incomplete; use last-known-good with a stale timestamp and then UNKNOWN after a defined timeout.

## 11.5 Battery lightning bolt

`status-bar.js` already adds class `charging` to the `.battery-icon`, but `status-bar.css` has no visual lightning bolt rule. Add a clear, compact lightning glyph inside the battery body (SVG or CSS mask/pseudo-element) when the battery is actively charging.

Fix the data bug:

`_acceptBatteryLevel()` currently uses logic equivalent to `!!charging || status === 'charging' || status === 'full'`. This makes `Full` look like active charging. Change it so the charge animation/glyph is true only for a genuine active `Charging` state or a canonical provider `charging === true`; `Full` means externally powered/full, not currently charging.

Requirements:

- Bolt is visible and centred inside the battery body without covering the percentage legibility.
- Bolt disappears immediately on stop charging/full/unplug.
- Preserve low-battery warning/critical fill color and current percentage display settings.
- Use a small static bolt; do not add an infinite high-cost animation.
- Battery percentage and capacity behavior remain unchanged.
- Test `Charging`, `Full`, `Discharging`, `Not charging`, unknown status, stale status and missing sysfs values.

## 11.6 Status-bar tests

- Geometry/overlap test with all icons active simultaneously.
- 360 × 760 CSS viewport with safe zones and simulated rotation.
- Location on/off/unknown/fix states.
- Normal/vibrate/silent/unknown sound modes.
- USB data, console USB, file transfer active/inactive, charger-only, full and detached states.
- Label precedence `file` > `term` > `chrg` and clear behavior on disconnect.
- Battery lightning is on only for actual Charging, not Full.
- No status label indicates an active endpoint based only on selected mode.

---

# 12. P1 — EXPANDED QUICK SETTINGS: CHARGING, USB AND CONSOLE CONNECTION STATUS

## 12.1 Existing state provider

Use:

`services/nuxel-bridge/src/system_indicators.py:get_indicators()`

Its structured contract currently includes:

- `charging.external_power`
- `charging.charging`
- `charging.battery_level`
- `usb_data.pc_connected`
- `live_console.active`
- `console_transports.serial.active`
- `console_transports.usb.active`
- `console_transports.wlan.active`
- `file_transfer.active`
- `file_transfer.selected`
- `file_transfer.endpoint_state`
- `connection_mode.selected`
- `connection_mode.transition_in_progress`
- Bluetooth state and source metadata.

Reuse the same semantics as `lockscreen-indicators.js`. The backend deliberately distinguishes an armed console daemon from a real connected session and a requested connection mode from an actually active USB file-transfer endpoint.

## 12.2 Expanded UI behavior

Keep the existing compact QS tile surface fast. Add a separate expanded detail strip/section below the normal quick tiles.

The section should display independent, compact indicators for:

- Charging / external power.
- USB data connection to a host.
- Active File Transfer endpoint.
- Live Console active state.
- USB / Serial / WLAN console transports where useful and space allows.

Use the existing assets when suitable, particularly the already-installed Nuxel charging, connected-PC, console-transport and file-transfer icon assets. Avoid downloading new art during the first panel paint.

The user describes opening Quick Settings “long” to see the expanded information. Implement an intuitive, testable expansion interaction that fits the existing behavior:

- Normal top-bar pull-down opens the compact QS panel.
- A deeper pull/second pull or an explicit long-press on the QS header/handle expands the panel to reveal the status detail row.
- Repeated input must not toggle twice or leave an unowned timer.
- The existing `expand()`/`collapseOrClose()` API should remain coherent.
- Back/collapse behavior should close expanded detail first, then close the panel.
- Do not make a long press on a tile accidentally toggle it.

If the existing UI has an established expand gesture, preserve that and wire the details to it rather than inventing an incompatible gesture.

## 12.3 State, update and accessibility

- One canonical read path, with in-flight/pending request deduplication.
- Immediate refresh on opening/expanding and on device state-change events where available.
- Bounded periodic refresh only while QS is visible.
- Stop polling and discard stale responses when QS closes.
- Distinguish “Charging” from “External power, not actively charging”.
- Distinguish “USB connected” from “File Transfer active”.
- Distinguish “Console service armed” from “Live Console connected/active”.
- Use accessible labels and tooltip details; do not rely only on color or animation.
- State changes should update individual indicators rather than rebuild the whole panel.
- Keep the strip legible on a 360 CSS-pixel viewport; wrap cleanly or use a compact two-row layout.

## 12.4 Tests

Use fixture-driven `system_indicators` responses for:

1. Battery charging, no USB.
2. External power + Full, no active charge.
3. USB host connected in charging mode.
4. File Transfer selected but endpoint inactive.
5. File Transfer endpoint active.
6. USB console active.
7. Live Console service armed but not connected.
8. WLAN-only console.
9. Serial console.
10. USB detach while daemon remains armed.
11. Provider failure/unknown.

Verify the exact visible labels and ensure no stale “file” or “term” remains after detach.

---

# 13. P1 — FILE EXPLORER SEND BUTTON AND REAL BLUETOOTH TRANSFER

## 13.1 User-facing workflow

Add a **Send** button to `pwa/nuxel-apps/files/index.html` and wire it in `files.js`.

- It is disabled when no valid file is selected.
- It becomes enabled for one or more selected files.
- Tapping it opens a compact “Send” sheet/modal.
- The first working method is **Bluetooth**.
- Other methods can be shown as disabled entries with “Coming soon”.
- The sheet must be usable with the physical touchscreen and not force a desktop file-picker workflow.

The Files app already supports multi-selection. Use that selected-path model; do not send every file in the current directory accidentally.

## 13.2 Backend investigation

The rootfs package list includes BlueZ packages but does not prove that `obexd` / Object Push is installed or running. Inspect the target and Fedora package repositories.

Implement a genuine BlueZ OBEX Object Push flow using the installed/supported BlueZ D-Bus APIs and daemon. Depending on the Fedora release, the package/service may be named differently; resolve the actual package rather than guessing.

Do not invent your own raw Bluetooth file-transfer protocol, write to Bluetooth rfkill or bypass pairing.

## 13.3 Required transfer flow

1. Validate each selected source path against the Files app’s allowed root.
2. Confirm the file exists, is readable and has a permitted size/type.
3. Check the Bluetooth adapter is powered and supported.
4. Discover/list paired or available devices through the supported BlueZ API. Do not silently switch the user’s adapter state without consent.
5. Let the user choose the receiving device. Require normal pairing/authorization confirmation where BlueZ requires it.
6. Create an OBEX session to the chosen peer and issue Object Push transfer(s).
7. Display queued/sending/progress/completed/failed states. Use the transfer object’s real status/progress/size values where available.
8. Support cancellation; cancel the actual transfer session and close its D-Bus object/session.
9. For multiple selected files, send sequentially or with a conservative bounded queue; do not flood OBEX or memory.
10. Report which files succeeded/failed. Never report success only because a D-Bus method returned an object path; wait for actual transfer completion.

Use a backend service or bridge provider to own the D-Bus access. Do not expose raw D-Bus to the PWA.

## 13.4 Security and failure behavior

- No arbitrary filesystem path acceptance.
- No shell command interpolation.
- Bounded transfer count, file size, timeout and D-Bus calls.
- Reject symlink escapes outside the user’s file root.
- Preserve source files; send is copy-only.
- Handle no adapter, Bluetooth off, no paired device, discovery failure, peer rejected, transfer aborted, disconnected peer and partial multi-file success.
- Do not silently trust a new peer; use normal pairing UX and visible target name/address.
- Do not leave an OBEX session open after completion/failure/cancel.
- Audit failures without logging file contents or secrets.

## 13.5 Tests

- Mock BlueZ Object Push service for device list, session creation, successful transfer, progress, cancellation, rejection, disconnected peer and daemon unavailable.
- Validate safe-path and symlink traversal rejection.
- Ensure selected items map exactly to transfer requests.
- Ensure no selection disables Send.
- Ensure “Coming soon” methods cannot be activated.
- Physical device-to-device send of a small file and a larger test file; confirm actual received bytes and hash on the receiving device.

---

# 14. P2 — FLASHLIGHT QUICK SETTINGS CONTROL AND PHYSICAL BUTTON INTEGRATION

This section is fully required even if the flashlight hardware turns out to be unsupported. The UI must be correctly wired and truthful.

- Replace the generic unavailable branch in `qs.js` with a call to the safe flashlight provider.
- Read state through that same provider.
- Use one owner for Quick Settings, Bixby double press and any Settings tile.
- Never write a sysfs LED path from JS.
- Use `configs/nuxel/leds/leds.json` as the policy source.
- Respect camera ownership and thermal bounds.
- Add visible state and an error/unsupported reason.
- Keep the tile unknown/disabled until provider truth is available; do not paint ON optimistically.
- Stop requests after a surface closes or a request becomes stale.

If no flash/torch LED class is bound on the actual S10+, the correct finished behavior is a clear `NOT_SUPPORTED_ON_DEVICE` state and safe refusal. Do not claim the flashlight has been fixed unless physical light is visible during a bounded manual proof.

---

# 15. P2 — GENERAL UI CONSISTENCY AND CACHE / VERSIONING

After editing JS/CSS/HTML/assets:

- Update the PWA version/cache version in `pwa/nuxel-home/manifest.json` and service worker as required by the repo’s single-source/cache-version contract.
- Update app-specific manifest/service worker caches for changed Files, Photos or Notes assets.
- Do not leave old JS running from a service-worker cache while testing the new code.
- Do not use cache-busting query strings inconsistently. Follow the existing project pattern.
- Ensure changed assets are included in the install/rootfs image and served from the expected docroot.
- Verify every precached asset exists. The baseline launcher-registry test currently reported `assets/nuxel-background.png` absent; determine whether that is a real missing asset, stale manifest entry or a test-root mismatch, and correct/document it rather than hiding the failure.
- Ensure no duplicate stale copy under `pwa/nuxel-home/` silently overrides the active file.
- Keep `manifest.json`, service-worker cache revision and JS version strings in sync.

---

# 16. REQUIRED TEST STRATEGY — DO NOT TRUST MISALIGNED TESTS

## 16.1 Baseline observations from this repository snapshot

The following baseline checks were run during the audit:

- `node pwa/nuxel-home/tests/test-widgets.js`: passes, but its desktop-2 test manually calls `renderPage(2)` and does not exercise the actual launcher page index. Rewrite it so the real second desktop is `currentPage === 1` under the chosen mapping.
- `node pwa/nuxel-home/tests/test-qs-wifi-state.js`: passes the current Wi-Fi/Bluetooth state mapping tests. It does not cover flashlight or expanded system indicators.
- `bash tools/s10plus/a34/tests/run-a34-tests.sh`: all A34 tests passed at baseline. Extend the suite with the new pointer, OSD, status, performance and active-menu regression tests.
- `python3 tools/s10plus/a33/tests/test-button-fsm.py`: existing A33 FSM tests pass, but it is not enough to validate the A34 FSM compiled by the S10+ image builder.
- `python3 tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py`: offline LED policy/fixture tests pass, while physical visible-light proof remains `NEEDS_OWNER_TEST`.
- `node tools/s10plus/a33/tests/launcher-registry-test.js`: one pre-existing failure reported the absent/stale precached asset `assets/nuxel-background.png`; the other emitted checks passed. Track and resolve the real cache/asset mismatch.

Re-run these after changes. Record command, exit code and output summary in the evidence directory.

## 16.2 New test files expected

Create focused tests as appropriate, with the active code path explicit:

- Home drag pointer state-machine tests (unit + browser/physical touch sequence).
- Widget desktop-index migration/lifecycle tests.
- Notes Bridge persistence and cross-PWA sync tests.
- Widget resize/reposition tests.
- A34 active power-menu table parity test against the config JSON.
- A34 active button chord and screenshot dispatch test.
- Screenshot helper build/install/path/argument test.
- Screenshot PPM→PNG and Gallery indexing test.
- Gallery thumbnail generation/cache/API security tests.
- Files large-directory rendering and selection tests.
- Bluetooth OBEX service/provider tests with mocked BlueZ D-Bus.
- Flashlight provider and safe-off tests.
- System-indicator fixture tests for charging/USB/console/file transfer.
- Status-bar battery/full/sound/location/USB tests.
- Expanded QS lifecycle/poll cancellation tests.
- Performance regression test for large file/Photos collections and launcher open/close timing.

## 16.3 Run the existing and new suites

At minimum run:

```bash
node pwa/nuxel-home/tests/test-widgets.js
node pwa/nuxel-home/tests/test-qs-wifi-state.js
node tools/s10plus/a33/tests/launcher-registry-test.js
bash tools/s10plus/a34/tests/run-a34-tests.sh
python3 tools/s10plus/a33/tests/test-button-fsm.py
python3 tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py
```

Also run the repository’s applicable Python/JS tests, syntax checks, packaging checks and the clean ARM64 S10+ rootfs build when the build environment is available. Add the active A34 FSM test to the release gate; do not replace it with the A33 check.

Run lint/type/syntax checks appropriate to the project for modified JS, Python and C. Build all touched C sources with the project’s `-Wall -Wextra` flags. Do not suppress warnings broadly to make the build green.

---

# 17. ON-DEVICE VALIDATION PLAN

When the existing Wi-Fi SSH target is discoverable from the operator’s configuration, inspect the live device before deployment. Do not scan random networks and do not guess credentials/IPs.

## 17.1 Before deployment

Record:

- Current git branch/commit and working tree.
- Current live Nuxel version and PWA/service-worker cache version.
- Kernel/OS/userspace versions.
- Current active units and their executable paths.
- `/usr/lib/nuxel/nuxel-button-manager` and `nuxel-pwa-host` versions/build IDs.
- Whether `/usr/lib/nuxel/nuxel-screenshot` exists; whether the installed snapshot binary exists and is compatible.
- Button-manager journal/log state.
- Reboot gate configuration and current state (read only).
- Framebuffer owner/Wayland/Phoc state; confirm the one-writer lock.
- Current USB and console indicators.
- Current LED classes/torch capability.
- Current Bluetooth adapter and OBEX daemon availability.
- Current media/notes/widget data and representative test media.
