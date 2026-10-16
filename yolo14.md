# NUXEL — GALAXY S10+ BETA HARDWARE & LAUNCHER FINALIZER
## DeepSeek V4 Flash Thinking HIGH · CodeSeeQ · Autonomous LIVE Engineering
### TOUCHSCREEN → EXACT UTM LAUNCHER → COLORS & WALLPAPER → HARDWARE BUTTONS → BETA QUALITY

# 1. THE MISSION

You are the autonomous lead engineer responsible for completing Nuxel, our Fedora-based Linux PHONE operating system, on the physical Samsung Galaxy S10+.

**NUXEL ALREADY BOOTS. FEDORA RUNS. THE AMOLED WORKS. THE ORIGINAL BOOT ANIMATION PLAYS. WE HAVE A LIVE USB CONSOLE.**

We're beyond initial bring-up.

The current physical phone has a launcher, but:

- Touchscreen interaction does not work.
- The launcher still differs from the one running in the UTM VM.
- The graphical color palette and wallpaper do not match expectations.
- The status bar overlaps the dual-camera cutout.
- The Power button does not provide normal short-press screen on/off behavior.
- Volume-button behavior and audio need verification and repair.
- The Bixby button must open the Nuxel Terminal application.
- Hardware-button remapping needs to be available in Nuxel Settings.
- Previous boot-animation flicker/bleed-through requires regression verification.

You must solve these problems through actual engineering.

Do not produce another alternative launcher.

Do not create fake app icons.

Do not create another simplified debugging dashboard.

Do not claim a component works merely because a process exists or a service reports active.

## STRICT USER PRIORITIES

**PRIORITY 1 — PHYSICAL TOUCHSCREEN WORKING.**

**PRIORITY 2 — EXACT SAME LAUNCHER AS THE RUNNING UTM VM.**

**PRIORITY 3 — CORRECT COLORS AND THE ORIGINAL NUXEL WALLPAPER.**

**PRIORITY 4 — POWER, VOLUME, AUDIO AND BIXBY HARDWARE CONTROLS.**

The configurable status-bar camera cutout feature is mandatory and must be implemented as part of the launcher/settings integration.

Complete all four priorities before claiming beta readiness.

---

# 2. IMPORTANT — THE UTM VM IS ALREADY RUNNING

The user has the Nuxel UTM virtual machine open and running on the MacBook.

**YOU ARE EXPLICITLY ALLOWED TO INSPECT AND INTERACT WITH THE RUNNING UTM VM THROUGH TERMINAL, UTM CONTROL INTERFACES, SSH AND AVAILABLE HOST COMPUTER TOOLS.**

Do not ask the user to start the VM unless it is actually stopped.

The VM contains the CORRECT launcher.

The physical Samsung currently displays a launcher that does not match it.

Your job is to determine the exact runtime differences and eliminate them.

## STRICT NO-SCREENSHOT-ANALYSIS RULE

You cannot reliably interpret images in your current execution environment.

Do not:

- Open user screenshots to inspect their appearance.
- Attempt OCR.
- Use screenshot-analysis tools.
- Infer the intended UI from photographic content.
- Generate a new UI based on screenshot descriptions.
- Create another launcher implementation because the existing one looks different.

Instead, compare:

- Running executables.
- Services and their startup arguments.
- Launcher URLs.
- Source paths.
- HTML/CSS/JavaScript.
- Application manifests.
- Installed packages.
- Asset hashes.
- Computed browser styles.
- JavaScript runtime state.
- WebKit logs.
- Wayland compositor configuration.
- HTTP resource responses.

The actual running UTM implementation is the authority.

The user will perform visual acceptance testing.

---

# 3. HARDWARE AND PROJECT

Hardware:

- Samsung Galaxy S10+
- SM-G975F
- Codename beyond2lte
- Exynos 9820
- ARM64
- Samsung Linux 4.14.253
- Fedora 43 ARM64
- systemd 258 with previous compatibility fixes
- Samsung DECON/DSIM AMOLED
- Physical framebuffer approximately 1440 × 3040
- Existing live USB CDC-ACM console

Project root:

`~/x/nuxel`

Important directories:

`pwa/nuxel-home/`

`pwa/nuxel-common/`

`pwa/nuxel-apps/`

`shell/`

`services/`

`vm/`

`assets/`

`tools/s10plus/a27/`

`tools/s10plus/a28/`

`tools/s10plus/a29/`

`tools/s10plus/a30/`

`docs/s10plus-autonomous-boot-repair/`

Known relevant code:

`tools/s10plus/a29/nuxel-touch-arm.c`

`tools/s10plus/a29/nuxel-pwa-host.c`

`tools/s10plus/a29/nuxel-wl-fb.c`

`tools/s10plus/a29/nuxel-session.sh`

`pwa/nuxel-home/js/apps.js`

`pwa/nuxel-home/js/app.js`

`pwa/nuxel-home/js/launcher.js`

`pwa/nuxel-home/css/style.css`

Wallpaper:

`assets/nuxel-background.png`

Live tools:

`scripts/s10plus-debug-pack/nuxel-live.sh`

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

The actual current repository state may differ from older engineering notes. Inspect current files and installed binaries before patching.

---

# 4. LIVE DEVELOPMENT ONLY — NO PLANNED TWRP

The phone is currently booted into Nuxel.

Keep it running.

The normal workflow is:

INSPECT → DIAGNOSE → PATCH → BUILD → LIVE DEPLOY → VERIFY → TEST → ROLLBACK IF NECESSARY

Do not reboot for normal changes to:

- Launcher code.
- CSS/JavaScript.
- Wallpaper.
- Icons.
- WebKit host.
- Phoc userspace configuration.
- Input mapping.
- Hardware-button handlers.
- Audio services.
- Application registry.
- Local Nuxel Settings.
- Systemd application services.

Do not flash BOOT or USERDATA for ordinary userspace modifications.

Preserve the last known working launcher and live-console connection.

If a real kernel driver deficiency is demonstrated, prepare a separate source-level fix with tests. Do not try unsafe live raw-kernel patching or speculative partition writes.

TWRP remains a recovery fallback, but it is not required for the initial work in this mission.

---

# 5. PHASE ZERO — VERIFY BOTH LIVE TARGETS

Before applying patches:

## Physical S10+

Verify:

- Live console executes commands and returns correct exit statuses.
- Device identity.
- Fedora release.
- Kernel.
- PID 1.
- Current uptime.
- Current launcher process.
- WebKit processes.
- Phoc process.
- Wayland framebuffer bridge.
- Touchscreen helper.
- Active animation process, if any.
- Current input devices.
- Current audio devices.
- Hardware-button input devices.

Preserve installed executable hashes and current service configurations.

## Running UTM VM

Inspect the VM using available host/guest control mechanisms.

Discover its actual IP address or shell-access method.

Do not assume historical addresses remain correct.

Identify:

- Graphical session.
- Launcher executable.
- WebKitGTK host.
- Launcher URL.
- Web-server docroot.
- PWA code version.
- Launcher CSS.
- App registry.
- Launcher assets.
- Desktop application definitions.
- Graphical output backend.
- Application activation bridge.
- Running services.

Record what is different between the UTM VM and S10+.

Do not attempt visual screenshot interpretation.

---

# 6. PRIORITY ONE — FIX TOUCHSCREEN END TO END

**THIS IS YOUR FIRST HARDWARE TASK.**

Previous A29b logs provided evidence that the Exynos touchscreen hardware could emit real contact events.

Recorded evidence included:

- Increasing sec_ts IRQ counters.
- Physical contact-count changes.
- EV_ABS input data.
- `TOUCH_POINT` reports.
- Successful event collection after the controller was correctly armed.

Despite this, the user still cannot control the launcher.

The current boot state must be tested again.

Do not assume earlier hardware success remains true in the current runtime.

## 6.1 Build an end-to-end touch diagnostic

Trace an actual physical touch through:

1. Samsung sec_ts controller.
2. Kernel IRQ handler.
3. Linux evdev.
4. libinput.
5. Phoc input backend.
6. Wayland touch/pointer protocol.
7. WebKitGTK event processing.
8. Nuxel PWA event handlers.
9. Application activation.

Find the FIRST stage where real touch events stop.

Do not stop at finding `/dev/input/event2`.

Do not stop at receiving `EV_ABS`.

Do not stop at a successful synthetic click.

The acceptance target is a real finger opening a launcher application.

## 6.2 Check actual kernel state

Inspect:

`/proc/cmdline`

`/proc/bus/input/devices`

`/proc/interrupts`

`/sys/class/input/`

`/dev/input/event*`

`/sys/class/sec/tsp/`

Relevant dmesg and persistent logs.

Check:

- `sec_touchscreen` registration.
- Charger mode versus normal boot mode.
- IRQ enablement.
- Controller power status.
- Driver open/resume behavior.
- Multitouch capabilities.
- Firmware initialization.
- Device permissions.

Previous Samsung driver investigations identified a condition where `sec_ts_start_device()` could return early when the internal power status was already `POWER_ON`, without enabling the IRQ.

Inspect whether that still occurs.

## 6.3 Verify the existing touch-arm helper

Inspect:

`tools/s10plus/a29/nuxel-touch-arm.c`

Check its actual current deployment.

Verify:

- Controller initialization.
- Stop/start behavior.
- IRQ state.
- Startup ordering.
- Driver return codes.
- Relevant sysfs state.
- Single-run behavior.
- Error handling.

Previous attempts involving `module_on_master` sometimes left the touchscreen unable to communicate.

Do not repeat a known failing sequence.

Avoid repeatedly blanking the framebuffer or resetting the panel merely to arm the touchscreen.

If a one-time notifier operation is needed, place it at the correct startup stage and prove it works.

Do not change raw power regulators blindly.

## 6.4 Verify evdev ioctl correctness

Review the touchscreen code and any remaining legacy native UI input code.

Verify:

- `EVIOCGBIT`
- `EVIOCGABS`
- `EVIOCGNAME`
- `EVIOCGPROP`

Use Linux UAPI headers and ABI-correct ioctl encoding.

Incorrect ioctls must return explicit errors, not silently classify a working touchscreen as absent.

Test Linux multitouch Type B behavior:

- ABS_MT_SLOT
- ABS_MT_TRACKING_ID
- ABS_MT_POSITION_X
- ABS_MT_POSITION_Y
- SYN_REPORT
- BTN_TOUCH where applicable

Track contact lifecycle correctly.

Avoid stale coordinates and ghost taps.

## 6.5 Verify libinput and Phoc

Check that the real touchscreen is associated with the correct Wayland seat and output.

Inspect:

- libinput device registration.
- Input permissions.
- Seat assignment.
- Phoc device discovery.
- Output mapping.
- Touch-device transform.
- Wayland output dimensions.
- Input-device rotation.

The physical S10+ framebuffer and headless Phoc logical output may have different dimensions.

Map coordinates correctly.

Do not confuse portrait/landscape display rotation with the input transform.

## 6.6 Verify WebKit events

Instrument the current WebKit host and Nuxel launcher as necessary.

Trace:

- touchstart
- touchmove
- touchend
- pointerdown
- pointerup
- click
- application tile selection

Check whether a fullscreen or transparent overlay intercepts input.

Check whether the previous PWA boot-splash overlay remains active.

Check actual focus and hit testing.

Use console logs and deterministic event tracing, not image analysis.

## 6.7 Real hardware test

Arm a bounded capture window.

Ask the user to physically:

1. Tap top left.
2. Tap center.
3. Tap bottom right.
4. Swipe vertically.
5. Tap one launcher icon.

The user has already authorized autonomous development; this request is only for necessary physical test input.

Correlate each contact through the whole pipeline.

**P1 IS COMPLETE ONLY WHEN REAL FINGER INPUT OPERATES THE ACTUAL NUXEL LAUNCHER.**

---

# 7. PRIORITY TWO — IDENTIFY AND ENABLE THE EXACT UTM LAUNCHER

The correct launcher has already been implemented.

Previous investigations identified:

`pwa/nuxel-home/`

as the Nuxel Home PWA running inside UTM with WebKitGTK.

The S10+ also has a WebKit-based bring-up path, including:

- Phoc headless.
- Wayland output.
- WebKitGTK host.
- Wayland-to-framebuffer bridge.

But the physical launcher still differs in application selection, graphics and styling.

**DO NOT ASSUME A DIFFERENT-LOOKING PAGE NECESSARILY MEANS A DIFFERENT EXECUTABLE.**

It may be:

- The wrong frontend.
- A different PWA mode.
- Stale installed assets.
- Cached old JavaScript.
- A different application manifest.
- Missing CSS.
- An incorrect HTTP document root.
- Missing SVG/icon assets.
- Incomplete shared JavaScript.
- A fallback launcher activated by service failure.
- Different runtime configuration.

Determine which one.

## 7.1 Compare exact UTM and S10+ launch paths

Compare:

- Launcher process executable and arguments.
- Loaded URL.
- PWA source revision.
- HTML hash.
- CSS hashes.
- JavaScript hashes.
- Application registry.
- Shared modules.
- Application icons.
- Browser storage/cache.
- Service-worker version.
- Runtime feature flags.
- Current orientation.
- Window size.
- User agent and viewport scaling.

Use the running UTM instance as authoritative.

Do not rebuild a new app grid.

## 7.2 Verify complete PWA deployment

Require successful loading of all required assets.

Inspect HTTP status, MIME types, module-loading failures, browser logs and source paths.

Ensure the phone serves the entire required PWA tree, including shared components.

Check for stale service-worker caches and cached frontend bundles.

Implement versioned asset deployment and controlled cache invalidation.

Do not delete unrelated user data merely to fix a stale frontend.

## 7.3 Restore original app definitions

Reuse the actual UTM registry from:

`pwa/nuxel-home/js/apps.js`

Preserve the original:

- Application IDs.
- App names.
- Categories.
- Icon references.
- Search behavior.
- Dock entries.
- App ordering.
- Launch handlers.

Do not create a new list of fake icons.

Verify application icons actually decode and display through the installed graphics stack.

Distinguish actual installed applications from unsupported hardware-dependent functionality.

## 7.4 Complete launcher startup

Ensure the working boot sequence ends at the actual UTM Nuxel Home implementation.

Retain fallback UI only for error recovery.

Do not allow the A27/A28 diagnostic frontend to remain the default when the original PWA has started successfully.

**P2 COMPLETE: THE REAL PWA, ITS REAL APP REGISTRY, ITS REAL STYLING AND ITS REAL APPLICATION ACTIVATION PATH ARE RUNNING ON THE S10+.**

---

# 8. PRIORITY THREE — CORRECT COLORS AND NUXEL WALLPAPER

The user reports that the S10+ background appears discolored compared with expectations.

The required asset is:

`assets/nuxel-background.png`

Use exactly that file.

Do not generate or redesign a replacement.

## 8.1 Fix path and packaging

Earlier investigation showed that the PWA stylesheet referenced a wallpaper inside the PWA asset directory, while the original image lived under the repository root assets directory.

Verify the current deployment.

Check:

- Source path.
- Deployed path.
- SHA-256.
- HTTP response.
- MIME type.
- Image dimensions.
- Browser decoding.
- Computed CSS background-image URL.
- Cache behavior.

Fix the asset staging or URL.

Keep the correct reference in the reproducible Fedora image builder.

## 8.2 Diagnose actual color corruption

Do not assume the wallpaper source itself is incorrectly colored.

Investigate each stage:

Original image decode

→ WebKitGTK rendered surface

→ Wayland buffer

→ screencopy format

→ `nuxel-wl-fb` conversion

→ Samsung framebuffer

→ AMOLED output

Verify:

- RGBA/BGRA/ARGB/ABGR ordering.
- Pixel byte order.
- Alpha channel handling.
- Premultiplication.
- Color range.
- Pixel stride.
- Wayland buffer formats.
- Framebuffer channel bitfields.
- Accidental double conversion.
- Uninitialized alpha.
- Transparent surfaces exposing previous frames.

Previous investigations identified Samsung framebuffer ABGR_8888 behavior.

Reverify the actual running framebuffer format rather than relying on historical labels.

Use deterministic known-color buffer tests and numeric channel comparisons.

Your environment cannot visually interpret the screenshots, so the user will confirm the corrected colors on hardware.

## 8.3 Correct background compositing

Ensure the launcher has a fully defined, consistent static background.

The boot animation must not be visible beneath transparent launcher regions.

Clear or replace stale framebuffer pages appropriately.

Ensure a stopped animation cannot resume writing behind the UI.

Do not disable intended wallpaper transparency or redesign existing layers unnecessarily.

**P3 COMPLETE: THE ORIGINAL STATIC WALLPAPER IS LOADED CORRECTLY, COLORS ARE CONVERTED CORRECTLY, AND NO ANIMATION REMAINS VISIBLE THROUGH THE LAUNCHER.**

---

# 9. MANDATORY FEATURE — CONFIGURABLE CAMERA CUTOUT / STATUS-BAR SAFE ZONES

The S10+ has two front-facing cameras near the top-right corner in portrait orientation.

The current status bar allows icons to occupy that physical area.

This causes items such as the battery indicator to be partially hidden by the camera cutout.

We need a reusable Nuxel solution, NOT an S10+-only hardcoded offset.

It must also support future Pixel phones with centered camera cutouts.

## 9.1 Status-bar zone editor

Add a new Settings section:

**Settings → Display → Status Bar → Camera & Cutout Areas**

Divide the full status-bar width into **10 selectable zones**.

Number them 1 through 10, left to right.

Each zone represents approximately 10% of the logical status-bar width.

Display an interactive row of ten boxes.

The user can tap any box to mark that portion as:

- AVAILABLE
- BLOCKED

Support multiple blocked zones.

For example:

Galaxy S10+ portrait preset: likely rightmost zones.

Pixel center-camera preset: likely center zones.

These presets are starting points only, not claims of exact physical camera dimensions.

Allow the user to adjust them manually.

## 9.2 Presets

Implement:

- No cutout.
- Right-side camera cutout.
- Center camera cutout.
- Left-side camera cutout.
- Custom/manual.

Provide separate stored selections for:

- Portrait.
- Landscape-left.
- Landscape-right.

Support device-specific profiles keyed to actual hardware identity where appropriate.

Do not make one S10+ setting globally affect all future Nuxel devices.

## 9.3 Actual layout behavior

A blocked zone is not merely a painted warning rectangle.

**NO STATUS ITEM MAY BE PLACED INSIDE A BLOCKED ZONE.**

This applies to:

- Time.
- Battery icon.
- Battery percentage.
- Signal indicator.
- Wi-Fi indicator.
- Notifications.
- Charging state.
- Bluetooth.
- Other status items.

Convert selected logical zones into excluded horizontal intervals.

Add configurable safety padding around those intervals.

Use a constraint-aware status-bar layout that places items into the remaining available regions.

If a region is too narrow, regroup items or prioritize essential indicators.

Never blindly draw an icon beneath the cutout.

Never silently hide battery/time solely to make layout math easier; define clear priority and overflow behavior.

## 9.4 Dynamic preview

When a zone is toggled:

1. Save the new selection to a temporary preview state.
2. Immediately recalculate the status-bar layout.
3. Update the preview.
4. Allow Save or Cancel.
5. Persist confirmed settings.

Changes must not require a full OS reboot.

Prefer hot reload of the UI layout.

## 9.5 Persistent configuration

Use the existing Nuxel Settings/configuration architecture.

If no suitable key exists, introduce a structured config such as:

`/etc/nuxel/display/statusbar-safezones.json`

or an appropriate writable per-device settings path.

Example structure:

```json
{
  "schema_version": 1,
  "zones": 10,
  "profiles": {
    "s10plus": {
      "portrait": [9, 10],
      "landscape_left": [],
      "landscape_right": []
    },
    "pixel_center": {
      "portrait": [5, 6],
      "landscape_left": [],
      "landscape_right": []
    }
  },
  "padding_dp": 6
}
```

Treat these as sample values, not verified physical measurements.

Persist the actual selected configuration.

Never overwrite manually customized settings during ordinary upgrades.

## 9.6 Console fallback

Because touchscreen support is still being repaired, provide a temporary command-line way to configure these same settings through the live console.

For example, a Nuxel Settings command may accept a list of blocked zones.

Use the same underlying configuration as the graphical editor.

Do not create two independent settings systems.

## 9.7 Acceptance

The user can select blocked zones in Settings.

Status icons move out of those zones.

Settings persist after reboot.

The S10+ battery indicator is completely visible outside the camera cutout.

The same feature can be configured for a centered Pixel camera.

---

# 10. PRIORITY FOUR — HARDWARE BUTTONS

The Samsung's physical buttons must work as normal phone controls.

Do not treat all hardware keys as generic keyboard input.

Enumerate the real kernel input devices and keycodes first.

Inspect:

- `/proc/bus/input/devices`
- `/dev/input/event*`
- Relevant `EV_KEY` events.
- Samsung key driver.
- Existing key mappings.
- systemd-logind configuration.
- Phoc key handling.
- Existing Nuxel hardware-button services.

Do not assume Bixby, Power or Volume keycodes without measurement.

Build a single Nuxel hardware-button manager or integrate with the appropriate existing input service.

Prevent duplicated handling between logind, the compositor and Nuxel.

---

# 11. POWER BUTTON — SHORT PRESS SCREEN OFF/ON

Required behavior:

**One quick Power-button press turns the display off.**

**Another quick Power-button press turns the display back on.**

A quick press must NOT shut down Fedora or reboot the phone.

Implement an explicit display state:

`DISPLAY_ON`

↔ `DISPLAY_OFF`

## Requirements

When turning off:

- Stop or pause visible frame presentation.
- Blank or disable the panel through a supported driver path.
- Preserve Fedora processes.
- Preserve application state.
- Preserve the Nuxel USB console where hardware allows.
- Avoid unnecessary reboot.
- Avoid repeatedly opening/closing `/dev/fb0`.
- Avoid triggering Samsung DECON release problems.
- Avoid breaking charging or thermal protection.

When waking:

- Detect the Power-button event.
- Restore the panel using supported APIs.
- Reinitialize display state only if required.
- Restore correct framebuffer output.
- Restore launcher interaction.
- Avoid replaying the entire boot animation.
- Avoid launching a second framebuffer owner.

## Critical power-off/wake issue

The Power key must remain capable of waking the device after the screen turns off.

Test whether the button event remains deliverable through the actual kernel/input path in the chosen display-off state.

Do not implement a one-way screen blank that requires TWRP or reboot to recover.

Test a short display-off interval with the live console remaining available.

If the kernel cannot wake the display reliably using the existing driver, document the exact blocker and keep a recoverable implementation.

## Short versus long press

Handle:

- Short press: toggle display.
- Long press: power menu or existing configured action.
- Hard-reset combinations: preserve the Samsung hardware recovery behavior.

Do not interfere with physical Download Mode or recovery key combinations.

Debounce repeated key events and key autorepeat.

---

# 12. VOLUME BUTTONS — REAL AUDIO CONTROL

The user wants the physical Volume Up and Volume Down keys working.

Required behavior:

- Volume Up increases output volume.
- Volume Down decreases output volume.
- A visible Nuxel volume indicator appears.
- Values remain within supported limits.
- Current volume persists according to the audio stack's normal settings.

But do not fake audio functionality.

## Inspect the real audio backend

Determine what exists on the running S10+:

- ALSA devices.
- Sound card enumeration.
- Mixer controls.
- Samsung codec drivers.
- Speaker output.
- Headphone output if available.
- PulseAudio/PipeWire compatibility.
- Session audio permissions.
- Audio routing.
- Volume range.

Previous Fedora userspace packaging does not prove the S10+ audio hardware works.

If the audio backend is functional, wire hardware keys to the actual mixer.

If the backend is not functional, investigate its kernel/userspace dependencies and keep the unsupported state explicit.

## Testing

Verify:

1. Volume Up event.
2. Volume Down event.
3. Mixer level changes.
4. Volume OSD updates.
5. No volume beyond safe defined bounds.
6. Actual quiet audio playback, when a working output path exists.
7. No uncontrolled loud playback during testing.

Ask the user for a listening confirmation only when required.

If sound hardware remains blocked, provide a precise engineering diagnosis and do not call sound fully working.

---

# 13. BIXBY BUTTON — TERMINAL BY DEFAULT

The Samsung Galaxy S10+ has a dedicated Bixby button.

**THE USER WANTS ONE QUICK BIXBY PRESS TO OPEN NUXEL TERMINAL BY DEFAULT.**

Use the ACTUAL Terminal/Console application from the authoritative UTM launcher registry.

Do not invent another terminal frontend.

Determine the Bixby key's actual evdev code from the physical device.

Implement a mapping:

`BIXBY_SHORT_PRESS → OPEN_NUXEL_TERMINAL`

If Terminal is already open, define consistent behavior such as focusing the existing instance.

Do not create endless duplicate terminal processes with repeated presses.

## Remappable in Settings

Add:

**Settings → Buttons & Gestures → Bixby Button**

Allow the user to choose:

- Terminal (default).
- Any installed supported Nuxel application.
- Home.
- Search.
- Settings.
- Disabled.

Use the existing application registry as the source of available apps.

Avoid arbitrary shell command execution from untrusted launcher content.

If custom commands are eventually supported, gate them through an explicitly trusted administrative configuration.

Persist the selected action.

Changes must take effect without reboot.

## Future extensibility

Build button mapping so it can support other phones.

Do not hardcode every feature to Samsung Bixby.

Use logical actions separated from physical keycodes.

Example:

`KEY_SOURCE → LOGICAL_ACTION → APPLICATION_OR_SYSTEM_ACTION`

Future hardware may have an Action button, assistant key or other configurable input.

Make the architecture reusable.

## Acceptance

A physical quick Bixby press launches the actual Nuxel Terminal.

Changing the Settings selection changes what the button does.

The setting survives reboot.

---

# 14. ENSURE THE REAL LAUNCHER SUPPORTS THESE SETTINGS

Do not create a separate unrelated settings dashboard.

Integrate the new features into the authoritative UTM Nuxel Settings application or its existing configuration backend.

Required Settings areas:

**Display**
- Screen on/off behavior.
- Status bar.
- Camera cutout safe zones.
- Orientation.
- Brightness if supported.

**Sound**
- Output volume.
- Audio device selection if available.
- Relevant sound settings.

**Buttons & Gestures**
- Power behavior.
- Bixby action.
- Supported hardware-key mappings.

**Developer**
- Live-console status.
- Input-event diagnostics.
- Display-driver status.
- Hardware service health.

Reuse existing Nuxel app activation, settings persistence and service APIs.

Do not replace the real Settings app with a small mock page.

---

# 15. BOOT ANIMATION AND DISPLAY REGRESSION FIXES

Previous cycles showed:

- Animation flashing during second-stage playback.
- Animation frames visible through the launcher.
- Competing framebuffer writers.
- Incomplete handoff acknowledgment.
- Redundant fullscreen PWA boot video.

Verify these remain corrected.

Check active animation and launcher processes.

Ensure:

1. One framebuffer owner at a time.
2. The animation stops before the launcher takes ownership.
3. A stop acknowledgment is actually received.
4. Stale animation pages are cleared or replaced.
5. The launcher displays a fully defined background.
6. No second PWA splash video obscures the launcher.
7. No periodic framebuffer reconfiguration causes flicker.
8. No unrelated framebuffer client shuts down the panel.

Do not regress the now-working first-light splash.

Do not rebuild BOOT to solve a userspace player bug.

The desired transition is:

NUXEL ORIGINAL BOOT ANIMATION

→ PWA READY

→ ANIMATION STOPS CLEANLY

→ STATIC NUXEL WALLPAPER

→ FULL LAUNCHER

No ghost frames.

No black flashes.

No double animations.

---

# 16. LIVE DEPLOYMENT AND ROLLBACK

Every change must be deployed safely.

Before replacing a component:

1. Record installed version.
2. Record SHA-256.
3. Preserve the working file.
4. Build updated ARM64 artifact.
5. Run offline tests.
6. Transfer in bounded verified chunks.
7. Verify destination hash.
8. Atomically activate.
9. Restart only affected services.
10. Confirm service health.
11. Confirm console remains connected.
12. Roll back if verification fails.

Avoid concurrent processes opening the same serial device.

Avoid simultaneous framebuffer owners.

Do not overwrite running executables in place.

Update the source repository and reproducible Fedora image builder after successful live fixes.

No phone-only hotfixes that disappear on a full rebuild.

---

# 17. QUALITY AND TEST COVERAGE

Create deterministic tests for:

## Touchscreen
- Evdev device discovery.
- Correct ioctl values.
- Contact tracking.
- Coordinate transforms.
- Wayland touch delivery.
- WebKit event dispatch.
- Application selection.

## Launcher
- Exact authoritative PWA code.
- VM/S10+ asset parity.
- App registry consistency.
- CSS/JS loading.
- Search.
- Application activation.
- Navigation.

## Wallpaper/colors
- Correct asset hash.
- Correct HTTP response.
- Correct CSS URL.
- Pixel-channel conversions.
- Alpha handling.
- Opaque background.
- No stale frame content.

## Status bar
- Ten-zone editor.
- Multiple blocked zones.
- Center cutout preset.
- Right cutout preset.
- Portrait/landscape profiles.
- Runtime reflow.
- Configuration persistence.
- No item intersects a blocked zone.

## Buttons
- Power short/long press separation.
- Screen on/off state transitions.
- Wake reliability.
- Volume up/down.
- Mixer changes.
- Bixby short press.
- Application launch.
- Remapping persistence.
- Debouncing and autorepeat.

## Runtime
- Systemd service health.
- Console reconnect.
- Process restart behavior.
- No render-loop runaway.
- No input-worker storm.
- No unexpected reboot.
- Rollback functionality.

---

# 18. REQUIRED PHYSICAL ACCEPTANCE TESTS

The final result must be tested on the real Samsung.

## Touchscreen

The user taps Settings, returns Home, scrolls, opens another app, and navigates back.

No console-injected substitute is allowed as proof.

## Launcher

The actual UTM PWA implementation is running and its real application list is loaded.

The user confirms the intended interface.

## Wallpaper/colors

The specified wallpaper is used and the user confirms the color appearance.

## Camera cutout

The user selects blocked zones in Settings.

Battery, signal and time indicators remain outside the selected zones.

## Power

Short press turns display off.

Another short press wakes it.

Fedora and the live console survive.

## Volume/audio

Hardware presses produce correct volume changes.

Actual audio output is verified separately.

## Bixby

Physical Bixby press launches the existing Terminal application.

Remapping works through Settings.

## Boot

Nuxel starts normally, shows its intended boot animation and reaches the correct launcher without flicker or overlay artifacts.

---

# 19. PERSISTENT ENGINEERING DOCUMENTATION

Create:

`docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/`

Documents:

- `00-BASELINE.md`
- `01-TOUCHSCREEN-ROOT-CAUSE.md`
- `02-INPUT-PIPELINE-TRACE.md`
- `03-UTM-LAUNCHER-PARITY.md`
- `04-WALLPAPER-AND-COLOR-PIPELINE.md`
- `05-STATUSBAR-SAFE-ZONES.md`
- `06-POWER-BUTTON.md`
- `07-VOLUME-AND-AUDIO.md`
- `08-BIXBY-MAPPING.md`
- `09-ANIMATION-REGRESSION.md`
- `10-LIVE-DEPLOYMENTS.md`
- `11-BETA-ACCEPTANCE.md`
- `12-REMAINING-HARDWARE-BLOCKERS.md`

Each report must distinguish:

- Implemented.
- Offline tested.
- Deployed.
- Tested on the physical phone.
- Confirmed by the user.
- Not yet working.

Do not fabricate hardware results.

Do not claim beta readiness based only on successful compilation.

---

# 20. EXACT EXECUTION ORDER

## PRIORITY ONE — TOUCHSCREEN

1. Verify the live console.
2. Identify current touchscreen input devices.
3. Inspect sec_ts state.
4. Verify IRQs from physical touches.
5. Verify evdev events.
6. Verify libinput events.
7. Verify Phoc input delivery.
8. Verify WebKit events.
9. Verify launcher click handling.
10. Fix the first broken link.
11. Physically test taps and swipes.

## PRIORITY TWO — CORRECT LAUNCHER

12. Inspect the running UTM VM.
13. Identify its exact WebKit launcher process and URL.
14. Inspect the S10+ launcher process.
15. Compare service, frontend, registry and asset versions.
16. Fix stale or wrong frontend selection.
17. Restore correct CSS, JavaScript and app definitions.
18. Verify the real Nuxel launcher and application activation.

## PRIORITY THREE — COLORS AND WALLPAPER

19. Verify original wallpaper asset.
20. Fix asset path and deployment.
21. Trace pixel formats through WebKit, Wayland and framebuffer.
22. Fix any proven channel-order/alpha errors.
23. Ensure static wallpaper covers the home background.
24. Verify no animation bleeds into the launcher.

## STATUS BAR SAFE-ZONE FEATURE

25. Implement ten-zone selection.
26. Implement cutout presets.
27. Implement dynamic icon reflow.
28. Implement persistent per-device orientation profiles.
29. Add live-console configuration fallback.
30. Integrate into the original Settings app.
31. Verify battery indicators avoid the S10+ camera area.

## PRIORITY FOUR — HARDWARE CONTROLS

32. Enumerate physical key input events.
33. Implement short Power press screen-off.
34. Implement Power press wake.
35. Preserve long-press recovery/power behavior.
36. Wire Volume Up/Down to actual audio controls.
37. Add a volume display indicator.
38. Verify real audio where hardware supports it.
39. Map Bixby to the actual Nuxel Terminal.
40. Implement Settings-based button remapping.

## FINAL BETA STABILIZATION

41. Verify animation ownership.
42. Verify no flickering or stale frames.
43. Verify no duplicate graphical processes.
44. Verify Fedora service health.
45. Verify live console survives UI updates.
46. Verify input and button behavior after service restarts.
47. Persist all changes in build sources.
48. Run regression tests.
49. Perform a controlled normal reboot only when necessary.
50. Verify settings and launcher persist.
51. Produce evidence-backed beta release notes.

---

# 21. BETA COMPLETION GATES

Do NOT declare the S10+ beta ready until:

- Physical touchscreen navigation works.
- The actual UTM launcher implementation runs.
- The correct application registry loads.
- Original wallpaper is applied correctly.
- Color conversion is correct.
- Camera cutout areas can be configured.
- Status indicators avoid blocked zones.
- Short Power press toggles the display.
- Volume buttons operate the supported audio control path.
- Bixby launches Terminal.
- Bixby mapping can be changed in Settings.
- Animation and launcher handoff is clean.
- Fedora and the live console remain stable.
- Changes persist and can be rolled back.

If audio hardware or another required function proves impossible with the current kernel, document the exact evidence and separate the kernel repair from the working userspace. Do not fake a pass.

Do not label unsupported hardware as working.

---

# 22. FINAL DIRECTIVE

**STOP BUILDING LAUNCHERS.**

THE RIGHT ONE IS RUNNING IN UTM.

USE IT.

**STOP GUESSING AT TOUCHSCREEN DRIVERS.**

TRACE THE ACTUAL PHYSICAL EVENTS ALL THE WAY INTO THE APPLICATION.

**STOP PUTTING STATUS ICONS BEHIND CAMERA CUTOUTS.**

BUILD A CONFIGURABLE TEN-ZONE SAFE-AREA SYSTEM.

**MAKE THE S10+ HARDWARE BUTTONS ACT LIKE PHONE BUTTONS.**

POWER SHORT PRESS → SCREEN OFF/ON.

VOLUME UP/DOWN → AUDIO VOLUME.

BIXBY → NUXEL TERMINAL.

BIXBY REMAPPING → NUXEL SETTINGS.

**KEEP THE ORIGINAL NUXEL WALLPAPER AND BOOT ANIMATION.**

MAKE EVERYTHING WORK TOGETHER.

## THE WoNQ BETA MISSION

NUXEL BOOTS

→ ORIGINAL ANIMATION

→ CORRECT UTM LAUNCHER

→ CORRECT WALLPAPER

→ TOUCHSCREEN WORKS

→ CAMERA CUTOUT RESPECTED

→ POWER AND VOLUME WORK

→ BIXBY OPENS TERMINAL

→ FEDORA REMAINS STABLE

**ALL THROUGH THE LIVE NUXEL CONSOLE WHERE TECHNICALLY POSSIBLE.**

NO UNNECESSARY TWRP.

NO EXTRA LAUNCHERS.

NO FAKE HARDWARE SUCCESS.

**DELIVER A REAL, USABLE NUXEL PHONE BETA.**

🐧🔥 EXECUTE.
