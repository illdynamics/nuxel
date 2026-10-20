# 🐧🔥 NUXEL A40 — OPERATION PENGUIN RESURRECTION

## LIVE S10+ — COMPLETE SYSTEM REPAIR & UX STABILIZATION

**AGENT:** GPT-5.6 Sol  
**TARGET:** Samsung Galaxy S10+ SM-G975F (beyond2lte)  
**OS:** Nuxel — Independent Fedora ARM64 Linux Phone OS  
**CONNECTION:** Live USB console via MacBook  
**BASELINE:** Current A39 installation and latest available Nuxel repository

**MISSION: ROOT-CAUSE ANALYSIS → IMPLEMENT → TEST → LIVE DEPLOY → PHYSICAL VERIFY → REPAIR.**

You are acting as a senior Linux phone OS engineer, Wayland/X11 compositor engineer, WebKit/JavaScript specialist, Linux input engineer, ARM64 hardware specialist, systemd boot engineer, and ALSA audio engineer.

We have made significant progress. The phone boots into Nuxel, its launcher and custom icons work, and many parts of the touchscreen UI are operational.

However, several core interactions remain defective.

**DO NOT merely patch visible symptoms. Determine which underlying subsystems are causing these failures and repair them systematically.**

Do not stop at code changes or simulated tests. Deploy changes to the actual USB-connected Galaxy S10+ and verify them.

---

# PHASE 0 — BASELINE, DIAGNOSTICS & ROOT-CAUSE INVESTIGATION

Before editing anything:

1. Inspect the current repository, current deployment documentation and live S10+ installation.
2. Determine exactly which A37/A38/A39 changes are present on the device.
3. Identify the actual compositor, window manager, launcher and WebKit runtime.
4. Map input-event flow from Linux hardware through the input manager to the launcher and applications.
5. Identify the navigation button controller and its event consumers.
6. Identify who owns application windows, focus, keyboard presentation and overlay visibility.
7. Capture service logs, timestamps, runtime process state and existing diagnostic failures.
8. Back up changed files and configuration.
9. Verify the USB recovery console remains available.
10. Preserve current Home layouts, application preferences, dock backgrounds and working assets.

Create an internal problem matrix linking each symptom to its likely owning subsystem.

**Investigate shared root causes first.**

For example, Recents flashing, Home failing, Back failing, invisible application launches and an inaccessible keyboard may involve the same focus/stacking/event-dispatch architecture.

Do not implement five separate temporary workarounds for a single underlying problem.

# 1. FIX EXCESSIVELY SLOW REBOOTS

Current problem: Rebooting Nuxel takes far too long.

Measure the actual shutdown and startup paths.

Inspect:

- `systemd-analyze`
- `systemd-analyze blame`
- `systemd-analyze critical-chain`
- `journalctl -b`
- `journalctl -b -1`
- Systemd unit dependencies and ordering
- Repeated service failures/restarts
- Blocking network-online waits
- Excessive device probing
- Audio/sensor initialization timeouts
- Launcher and compositor startup
- USB console initialization
- Filesystem mount delays
- Shutdown stop-job timeouts
- Boot animation → launcher handoff

Distinguish kernel startup, userspace startup, launcher readiness and shutdown latency.

Repair unnecessary dependencies, blocking operations, repeated failures and misconfigured timeouts.

Parallelize safe independent initialization where possible.

Do not arbitrarily disable essential services or hide failures by shortening all timeouts.

Make the launcher become usable as early as safely possible, with nonessential services continuing asynchronously.

**Acceptance:** Measure before/after reboot times and demonstrate a meaningful reduction without compromising services, storage integrity or USB recovery.

# 2. FIX ALL THREE NAVIGATION BUTTONS — SYSTEM-WIDE

The three custom navigation icons are:

- **LEFT:** Back
- **MIDDLE:** Penguin Home
- **RIGHT:** Tabs / Recents

Their images already exist. Preserve their artwork.

## 2A — Recents / Tabs button

**CURRENT FAILURE:** A single tap shows Recents for approximately half a second before it disappears. Double-tapping sometimes keeps it open.

This is unacceptable.

Investigate:

- Pointer-down/pointer-up duplication
- Touch versus synthetic click events
- Capture/bubble event propagation
- Outside-click dismissal
- Focus-loss dismissal
- Gesture ownership
- Overlay stacking
- Window-manager focus changes
- Competing event listeners
- State resets and re-renders
- Repeated initialization of event handlers

Instrument each Recents open/close state transition with its exact reason and originating event.

**Implement:**

- One tap opens Recents.
- It stays open indefinitely until intentionally dismissed.
- A second tap may close Recents.
- App selection restores the selected running application.
- Home closes Recents and returns to Desktop 1.
- Back closes Recents.
- Swipe-to-dismiss application cards works safely.
- No phantom open/close events.
- No double-tap tricks.
- No arbitrary delay-based workaround.

Recents must reflect actual application processes/windows, not only an artificial list of launcher clicks.

## 2B — Penguin Home button

**CURRENT FAILURE:** Home frequently does nothing, including from applications.

**REQUIRED CONTRACT: ONE PRESS ALWAYS RETURNS TO PRIMARY HOME.**

From any app or system screen:

1. Minimize/hide currently visible application windows.
2. Preserve running applications in the background.
3. Restore launcher visibility and focus.
4. Close application drawer, Recents, overlays and transient menus.
5. Return to primary Desktop 1.
6. Leave wallpaper and fixed dock stationary.
7. Never terminate the application simply because Home was pressed.

If on Desktop 2 or another desktop, smoothly return to Desktop 1.

Implement this at the appropriate compositor/window-manager level rather than only changing a launcher JavaScript variable.

Also fix any Home controls inside application UI that are intended to return to the launcher.

**Acceptance:** One Penguin press works from Calendar, Settings, applications, Recents and secondary desktops.

## 2C — Back button: short press

**CURRENT FAILURE:** Back does not navigate out of apps or to previous pages.

Make Back context-aware.

- Inside a web application: navigate its actual history where supported.
- Inside native apps: dispatch the appropriate application/window navigation action.
- Inside Calendar: navigate back through Calendar views.
- At an application's root: return to the previous window or launcher according to Nuxel policy.
- Inside a folder: close the folder.
- Inside Settings: go to its previous page.
- Inside app drawer: close drawer.
- Inside expanded Quick Settings: collapse, then close.
- Inside Recents: dismiss Recents.

Avoid relying on Escape events unless the target application actually handles them.

Implement one centralized navigation policy with clear ownership and fallback behavior.

## 2D — Back button: LONG PRESS = CLOSE APP

**NEW REQUIRED FUNCTIONALITY.**

Holding the LEFT Back navigation button must close the foreground application rather than minimize it.

Implement:

- Short press = navigate backward.
- Long press (suggest approximately 700 ms) = close foreground application.
- Long-press action suppresses the corresponding short-press action.
- First request graceful window/application termination.
- If graceful termination fails, use a bounded, process-specific escalation without killing unrelated processes.
- Remove the closed app from active Recents.
- Return to primary Home.
- Keep other applications running.
- Never kill system-critical services, launcher, compositor, input manager or keyboard service.

Use verified application/window identities, not broad process-name matching.

If there is no safe foreground app to close, do nothing destructive.

**Acceptance:** Long-press Back closes Calendar; Calendar disappears from active Recents and its window/process is gone when appropriate.

# 3. FIX APPLICATION LAUNCHING & COMPOSITOR REPAINTING

**CURRENT FAILURE:** Tapping an app in All Applications sometimes appears to do nothing. Later, when switching away, the app seems to have started invisibly.

Investigate:

- Window creation and mapping
- Surface commit timing
- Compositor repaint/surface damage
- Focus transfer
- Window stacking order
- Application visibility states
- WebKit and native application lifecycle
- Window activation events
- Blank or stale surfaces
- CSS overlays obscuring windows
- Launcher accidentally retaining foreground status
- GPU versus software rendering issues

Implement a reliable application activation transaction:

1. Resolve selected application.
2. Launch or restore its real process/window.
3. Wait for meaningful mapped/ready state.
4. Bring the correct window to foreground.
5. Assign keyboard/input focus.
6. Close the app drawer appropriately.
7. Ensure a compositor repaint occurs through the correct supported mechanism.
8. Confirm the app is actually visible.
9. Record useful failure information if activation fails.

Do not mark an application successfully opened just because its process started.

Preserve background applications and their state.

Test switching repeatedly between Calendar, Settings and multiple apps.

# 4. BEAUTIFUL, SMOOTH NUXEL ANIMATIONS

Add polished animations throughout the interface.

### Home desktops

- Horizontal swipe transitions with smooth sliding.
- Stable wallpaper.
- Stationary dock.
- Moving app grids.
- Page indicators transitioning elegantly.

### Quick Settings

- First downward swipe → compact shade slides down.
- Second downward swipe → expanded shade slides farther down.
- Upward swipes reverse these transitions.

### Applications drawer

- Opens smoothly from the bottom.
- Closes downward.
- App selection transitions naturally to the application window.

### Recents

- Smooth entrance and exit.
- App cards animate during selection and dismissal.

### General requirements

- Prefer compositor-friendly `transform` and `opacity` animations.
- Use consistent motion duration, approximately 180–300 ms where appropriate.
- Natural acceleration/deceleration.
- Avoid blocking input during animations.
- Keep navigation responsive under load.
- Respect reduced-motion preferences.
- Avoid expensive full-screen repaints.
- Never use animations to conceal application-focus bugs.

Profile frame timing on the real S10+; aim for smooth 60 FPS where supported, without claiming it if unmeasured.

# 5. FIX ICON DRAGGING ON HOME

**CURRENT FAILURE:** Long-press selects an icon, but moving the finger causes the icon to drop prematurely.

Investigate pointer ownership and event lifecycle.

Potential causes include losing pointer capture, state changes, overlays intercepting movement or treating drag movement as release.

Implement robust drag state management:

`IDLE → PRESS_PENDING → DRAGGING → DROP_TARGET → COMMIT/CANCEL`

Requirements:

- Icon follows finger continuously.
- Drag remains active until the actual finger release.
- No accidental release during motion.
- Prevent native WebKit drag interference and conflicting scroll gestures.
- Support repositioning into empty spaces.
- Support cascading icon displacement.
- Support folder creation when deliberately dropped onto an icon.
- Persist the resulting layout.
- Respect Home layout lock.
- Support Desktop 1 and Desktop 2.
- Support cross-desktop edge dragging if enabled.

Use a launcher-level pointer/drag controller and stable icon IDs.

Do not drop the icon because its source DOM element was re-rendered.

# 6. APP DRAWER → DRAG DIRECTLY TO HOME

When the user long-presses an application in All Apps:

1. Begin a persistent drag session.
2. Show a floating icon following the finger.
3. Close the app drawer without destroying the drag session.
4. Reveal the current Home desktop.
5. Continue dragging with the same touch.
6. Permit placement into a valid Home slot.
7. Commit on actual finger release.

**Critical:** Pointer state must survive closing/unmounting the app drawer.

Also preserve the existing **Add to Home screen** context-menu action as a reliable alternative.

Ensure neither method silently loses the application or duplicates it accidentally.

# 7. REPAIR VIRTUAL KEYBOARD COMPLETELY

**CURRENT FAILURE:**

- Cannot type using the virtual keyboard.
- Keyboard is sometimes behind other windows.
- Hide Keyboard button does not work.
- No visible blinking cursor in text fields.
- No keypress haptics.

These are critical usability blockers.

Investigate the actual keyboard architecture, compositor input-method protocol, WebKit focus behavior, text-input protocol and installed OSK.

Do not assume Android IME APIs.

## 7A — Keyboard input

When selecting any editable field:

- Correct text-input focus is established.
- A visible blinking caret appears.
- The virtual keyboard opens.
- Pressing keys actually inserts characters.
- Backspace, Space, Enter and Shift work.
- Text selection works.
- Focus transitions work between inputs.
- Keyboard input works in Calendar, Settings, search and other supported apps.

Distinguish DOM focus from compositor keyboard focus and actual text-input delivery.

## 7B — Keyboard always on top

The OSK must occupy the appropriate top system/input-method layer.

- Never hide behind application surfaces.
- Never be obscured by the Home dock.
- Adjust viewport or content insets where needed.
- Keep focused text input visible.
- Restore normal layout on dismissal.
- Do not steal text-input focus from the target field.

## 7C — Hide Keyboard button

The existing Hide Keyboard control must:

- Actually dismiss the OSK.
- Update keyboard visibility state.
- Restore the viewport.
- Avoid immediately reopening due to stale focus events.
- Permit opening again when an input is selected.

## 7D — Blinking caret

Ensure focused editable fields show a visible blinking text cursor.

Inspect CSS, text focus, caret color, compositor input focus and WebKit text-editing state.

Do not implement a decorative fake cursor that cannot accept text.

## 7E — Keyboard haptics

Each virtual keypress should request a subtle haptic pulse.

- Use existing Nuxel haptic integration.
- Keep one vibrator controller.
- No overlapping excessive pulses.
- Avoid unnecessary long vibrations.
- Respect haptics settings.
- Ensure key events still type text correctly.

**Acceptance:** Open Calendar, tap a text field, see the caret blink, type a sentence, delete characters, hide the keyboard and reopen it, with tactile key feedback.

# 8. AUDIO — STILL COMPLETELY SILENT

**ZERO audible speaker output so far.**

Startup MP3 and Volume Up/Down cue still cannot be heard.

Stop treating successful MP3 decoding as proof of working audio.

Trace the entire physical pipeline:

`Button/Event → Sound helper → Decoder → ALSA PCM → Codec → Amplifier → Speaker`

Inspect:

- ALSA card/device enumeration
- `/proc/asound/`
- `/sys/class/sound/`
- UCM profiles and active verb
- `aplay`, `speaker-test`, `amixer`, `alsactl`
- Actual selected PCM device
- Kernel audio logs
- Codec initialization
- Amplifier and speaker routing
- Firmware availability and load failures
- Samsung Exynos/Madera-specific audio components supported by current hardware evidence
- DAPM routing and power state
- Sound service permissions

Determine whether audio fails before PCM transmission, at codec routing, amplifier enablement or speaker output.

Repair verified software routing and configuration where safe.

**Never guess amplifier register values, disable speaker protection or force unverified mixer settings.**

Preserve protective volume limits.

Test with safe, low-volume audio and obtain the owner's audible PASS/FAIL confirmation.

If the current kernel cannot drive the speaker, report the precise driver/firmware/route blocker with evidence.

Do not falsely report success.

# 9. VOLUME BUTTONS — FIX LATENCY AND INPUT BEHAVIOR

**CURRENT FAILURE:** Hardware volume buttons react slowly or unpredictably.

Trace button events from kernel input to the volume manager.

Measure:

- Event generation latency
- Input listener processing
- Debouncing
- Repeated events
- Volume service request latency
- Mixer updates
- Audio cue invocation
- UI feedback timing

Requirements:

- Single tap = one predictable volume step.
- Holding button = controlled repeated steps.
- No missed inputs.
- No excessive delayed repeat.
- No double-processing by competing services.
- UI slider updates promptly.
- Mixer and displayed volume stay synchronized.
- `nuxel-pow.mp3` plays when hardware audio becomes functional.
- Audio cue decoding must not block handling the next volume event.

Preserve safe volume caps until physical speaker verification.

# 10. FIX FLASHLIGHT / TORCH

**CURRENT FAILURE:** Flashlight toggle does nothing.

Inspect actual hardware support:

- Available LED class devices
- Kernel LED/torch drivers
- Relevant V4L2 flash controls
- Current flashlight service implementation
- Camera/flash resource ownership
- Device permissions
- Torch power and timeout limits
- Hardware thermal protection

Find the proper verified torch interface for the Galaxy S10+.

Wire Quick Settings flashlight toggle to that interface.

Requirements:

- Toggle ON enables continuous torch mode.
- Toggle OFF disables it.
- UI reflects actual physical state.
- Failure produces an accurate error rather than fake success.
- Torch turns off on service failure, shutdown or timeout when appropriate.
- Avoid excessive brightness and unsafe operating modes.
- Preserve thermal and hardware safeguards.

Do not write arbitrary kernel registers or blindly use camera-flash strobe mode.

If required kernel support is absent, report the exact blocker rather than faking the toggle.

# 11. CALENDAR — NAVIGATION AND BACK REPAIR

**CURRENT FAILURE:** Cannot leave Calendar using the left navigation button.

Investigate how Calendar is launched and managed.

Determine whether it is a native window, WebKit app, embedded view or another application type.

Ensure:

- Back inside Calendar navigates its supported views.
- Back at the root leaves Calendar appropriately.
- Penguin Home immediately minimizes Calendar and returns to Desktop 1.
- Recents can restore Calendar.
- Long-press Back actually closes Calendar.
- Calendar does not retain inappropriate focus over the launcher.
- Keyboard works in Calendar's editable fields.
- No blank or invisible surfaces after returning.

Test the actual calendar, not a generic mock app.

# 12. FIX CUSTOM BOTTOM DOCK BACKGROUND

**CURRENT FAILURE:** Neither selectable background appears despite Home Settings showing BG1 and BG2.

Assets:

- BG1: `./assets/nuxel-bottom-bar.jpg`
- BG2: `./assets/nuxel-bottom-bar2.png`

**DEFAULT MUST BE BG2.**

Inspect actual active launcher DOM, CSS, image paths, deployment webroot, service-worker caching and background layering.

Determine why the background is not visible.

Verify whether it is:

- Wrong runtime URL
- Asset absent from active phone webroot
- Stale cached stylesheet
- CSS background overwritten by another rule
- Transparent or hidden element
- Incorrect stacking layer
- Zero-size container
- Dock background behind opaque UI layer
- Mis-sized or clipped background

Requirements:

- BG2 visible by default.
- BG1 selectable.
- Immediate visual switching.
- Original JPG/PNG artwork.
- PNG transparency preserved.
- Four dock icons remain interactive.
- Image remains stationary between desktops.
- Preference survives reboot.
- Home Settings preview reflects actual selection.

Validate source and deployed SHA-256 hashes.

**Success requires seeing the artwork on the actual phone, not merely finding it in the repository.**

# 13. FIX BATTERY PERCENTAGE DISPLAY

**CURRENT FAILURE:** Percentage mode displays something resembling a line instead of readable percentage text.

Inspect battery rendering, CSS sizing, font sizing, positioning and layout collisions.

Preserve the three A39 modes:

**A — Icon with percentage inside**
- Percentage clearly visible inside the battery outline.
- Text centered.
- Actual battery charge displayed.
- No overlapping symbols.

**B — Percentage only**
- Display readable text such as `74%`.
- No battery icon.
- No clipped or collapsed typography.

**C — Battery bar only**
- Real proportional fill.
- 50% charge = half filled.
- No percentage text.

Read actual charge from the device's battery service/sysfs/UPower integration.

Don't substitute fixed or fabricated values.

Ensure status icons do not overlap.

Test live mode switching and persistence.

# 14. CENTRALIZE INPUT & WINDOW LIFECYCLE

This is an architecture requirement, not a cosmetic enhancement.

Many symptoms indicate potentially conflicting control paths.

Audit for duplicate:

- Navigation handlers
- Pointer/touch listeners
- Input managers
- Keyboard-focus controllers
- Window activation functions
- Overlay dismissal handlers
- Gesture handlers
- App lifecycle managers
- Volume/haptic consumers

Where justified, consolidate into clear ownership boundaries:

**Navigation controller:** Back/Home/Recents behavior.

**Window controller:** Launch, minimize, restore, close, focus and stacking.

**Gesture controller:** Swipes, drags, pointer ownership and cancellation.

**Keyboard controller:** OSK presentation and text-input state.

**Audio controller:** Volume changes and audio cue requests.

**UI state controller:** Desktop, drawer, shade, overlays and preferences.

Integrate with actual Nuxel components instead of unnecessarily replacing working subsystems.

Document event contracts and state transitions.

Avoid duplicate listeners and ownership conflicts.

# 15. AUTOMATED REGRESSION TESTS

Extend existing test suites to cover:

- Recents stays open after one tap.
- Double-tap is not required.
- Short Back navigation.
- Long Back terminates foreground app safely.
- Home minimizes apps and returns to Desktop 1.
- Home works from Calendar.
- Application activation brings its window to foreground.
- Repaint and focus on app switching.
- Continuous icon dragging until real pointer release.
- Drawer-to-Home drag across unmount.
- Add to Home.
- Keyboard input and actual text insertion.
- Keyboard top-layer behavior.
- Hide Keyboard.
- Focus and blinking caret.
- Keyboard haptic requests.
- Volume event latency and repeat behavior.
- Flashlight state and failure reporting.
- BG1/BG2 actual asset resolution.
- Battery percentage and fill modes.
- Desktop, Quick Settings and drawer animations.
- Systemd boot dependency regressions.
- Audio route errors and safe fallbacks.

Do not count a mocked event as proof that physical hardware works.

# 16. SAFE LIVE USB DEPLOYMENT

Deploy this release to the actual live S10+.

### Execution sequence

1. Confirm the correct USB-connected device.
2. Confirm the live shell and recovery path.
3. Capture baseline and diagnostic evidence.
4. Back up active binaries, launcher files, services and configuration.
5. Preserve Home layout/preferences and user data.
6. Patch the actual repository.
7. Run syntax, unit and integration tests.
8. Build any required Linux AArch64 components.
9. Verify generated artifacts.
10. Deploy through the existing documented userspace deployment mechanism.
11. Verify actual installed file hashes.
12. Invalidate relevant launcher code caches, preserving user preferences.
13. Restart only required services in a safe order.
14. Confirm compositor, launcher and USB console remain operational.
15. Run live runtime verification.
16. Conduct physical user acceptance tests.
17. Repair observed failures.
18. Perform one controlled reboot if the device is stable.
19. Measure startup/shutdown time and verify persistence.
20. Produce deployment receipts and rollback instructions.

Use an atomic/staged deployment wherever practical.

Never replace the actively functioning launcher with untested files without a recoverable rollback route.

# 17. PHYSICAL ACCEPTANCE SESSION

After live deployment, tell me exactly when to interact with the phone.

Conduct a guided physical test covering:

1. One tap Recents → remains open.
2. One tap Penguin Home → Desktop 1.
3. Launch Calendar → short Back navigates correctly.
4. Long Back → Calendar really closes.
5. Launch multiple apps → Home minimizes them.
6. Recents → restores previously running apps.
7. App drawer → immediately displays selected launched app.
8. Drag an icon between occupied Home slots.
9. Long-press an app in drawer → drag directly to Home.
10. Select an editable input → see blinking cursor and type using OSK.
11. Hide/reopen OSK, verify keyboard stays above apps.
12. Feel keyboard key haptics.
13. Switch BG1/BG2 and visually confirm backgrounds.
14. Test each battery indicator mode.
15. Press Volume Up and Volume Down; verify response timing and listen for audio.
16. Toggle flashlight and verify physical LED.
17. Swipe desktops, Quick Settings and app drawer; inspect animations.
18. Perform one controlled reboot; confirm improved startup and persistence.

Collect logs during testing, correlate with owner feedback and repair failures.

# 18. RELEASE SUCCESS CRITERIA

Produce a feature matrix with separate verdicts:

- **SOURCE VERIFIED:** Implementation and automated tests pass.
- **DEPLOYMENT VERIFIED:** Correct files/services are installed and active on the S10+.
- **HARDWARE VERIFIED:** Actual phone behavior has been physically confirmed.
- **BLOCKED:** Exact blocker identified with evidence.
- **FAILED:** Reproduced failure remains.
- **NOT TESTED:** No verification was performed.

Provide before/after metrics for boot performance, volume input latency and UI smoothness when measurable.

Never label sound, keyboard, torch or compositor functions as hardware-verified solely because commands returned exit code 0.

## ABSOLUTE SAFETY REQUIREMENTS

- NO FLASHING.
- NO PARTITION WRITES.
- NO KERNEL REPLACEMENT.
- NO BOOTLOADER MODIFICATION.
- NO DESTRUCTIVE FACTORY RESET.
- NO BLIND AUDIO AMPLIFIER CHANGES.
- NO DISABLING HARDWARE PROTECTION.
- NO KILLING CRITICAL SYSTEM PROCESSES THROUGH LONG BACK.
- NO BREAKING THE LIVE USB CONSOLE.
- NO DELETING USER LAUNCHER LAYOUTS.
- NO FALSE SUCCESS REPORTS.

Maintain a usable phone and rollback path during every repair phase.

If a hardware problem cannot be resolved safely without kernel work, isolate it and report the exact missing capability rather than performing forbidden changes.

---

# FINAL DIRECTIVE

**STOP ADDING WORKAROUNDS ON TOP OF BROKEN SUBSYSTEMS.**

Make the underlying application/window/focus/input architecture reliable.

Prioritize implementation in this order:

1. Live USB recovery and baseline.
2. Window/compositor and navigation correctness.
3. Virtual keyboard, text focus and input.
4. Application activation and launcher repaint.
5. Icon drag/drop and app-drawer placement.
6. Volume button handling and hardware audio diagnosis.
7. Flashlight integration.
8. Dock backgrounds and battery UI.
9. Smooth animations and performance.
10. Reboot-time optimization and final verification.

Do not abandon the other features because one physical hardware dependency is blocked. Complete independent repairs and report hardware blockers separately.

**DELIVER NUXEL A40 — STABLE NAVIGATION, WORKING APPS, FUNCTIONAL KEYBOARD, REAL HARDWARE INTEGRATION AND POLISHED ANIMATIONS.**

**EXECUTE ON THE LIVE USB-CONNECTED S10+ NOW. 🐧🔥**

oh and more:

# 🐧 NUXEL — LIVE HOME HARDWARE METERS
## Mission: Replace the Blue NUXEL Header with CPU / MEM / GPU Monitoring

You are the senior Fedora ARM64, Linux kernel instrumentation, WebKitGTK, JavaScript and Nuxel Home UI engineer.

**Target:** Samsung Galaxy S10+ SM-G975F · Exynos 9820 · Fedora 43 · Nuxel Home · Linux 4.14.253.

**MISSION:** Remove the existing blue "NUXEL" text above the Home screen application icons and replace that entire horizontal area with beautiful, functional, real-time CPU, memory and GPU utilization meters.

This is a real implementation mission. Inspect the existing code, implement the changes, test them, and safely deploy them to the live phone.

## 1. Replace the existing Home header

Find the component that renders the blue "NUXEL" text directly above the application icons.

- Remove that text from this specific position.
- Preserve the existing Nuxel branding everywhere else.
- Reuse the full available width of its former container.
- Do not unnecessarily increase the container's height.
- Do not push the app icons out of view.
- Preserve the existing two Home desktops, navigation buttons, gestures, Quick Settings and application drawer.
- Keep the layout usable in both portrait and landscape orientations.

Create a compact horizontal performance-monitoring widget containing three live meters.

### Visual design

Use the existing Nuxel pixel-art / futuristic cyber-terminal visual language.

Suggested compact layout:

```text
┌──────────────────────────────────────┐
│ CPU  12%    MEM  43%    GPU   8%     │
│ ███░░░░░░   █████░░░░   ██░░░░░░     │
└──────────────────────────────────────┘
```

Requirements:

- Three equally spaced monitoring sections.
- Small pixel-style labels: CPU, MEM, GPU.
- Real percentage values.
- Tiny pixelated progress bars.
- Subtle transitions when values change.
- Theme-aware colors and good contrast.
- Avoid unnecessary animations, gradients or blur effects that cause extra GPU work.
- Keep the widget readable on the S10+ display.
- Match existing Nuxel iconography and styling.

Use existing UI components wherever appropriate.

## 2. Implement real system measurements

**No fake values. No placeholder percentages.**

### CPU utilization

Read `/proc/stat`.

Calculate CPU usage from differences between two successive cumulative counter samples.

Use the total aggregate CPU counters and account for idle/iowait consistently.

- Display overall CPU utilization as a percentage.
- Avoid reporting cumulative CPU time as usage.
- Handle initialization and counter resets.
- Smooth extreme single-sample fluctuations lightly if useful.
- Do not execute `top`, `htop` or other heavyweight tools every refresh.

### RAM utilization

Read `/proc/meminfo`.

Use:

- `MemTotal`
- `MemAvailable`

Calculate:

`used_percent = 100 × (MemTotal - MemAvailable) / MemTotal`

This avoids treating reclaimable cache as permanently consumed memory.

Optionally show used/total RAM in a small tooltip or expanded details view.

Do not mistake process RSS for overall system memory utilization.

### GPU utilization — Exynos Mali

Research the **actual available Mali GPU driver and runtime sysfs/debugfs interfaces on the live S10+**.

Possible sources to investigate:

- `/sys/class/devfreq/`
- `/sys/devices/platform/`
- Mali driver-specific utilization counters
- Available GPU busy/idle time counters
- Existing kernel instrumentation interfaces

Only use a metric if its meaning is verified.

Important:

- GPU clock frequency is NOT GPU utilization.
- GPU temperature is NOT GPU utilization.
- GPU availability does not prove that usage percentage is measurable.
- Do not invent GPU usage from CPU load.
- Do not add expensive polling, tracing or kernel patches just to populate this field.

If the installed Mali driver exposes an accurate low-overhead usage metric, implement it.

If not, display `GPU N/A` or `GPU --` with a suitable indication that utilization telemetry isn't available.

Document the missing kernel interface so GPU monitoring can be enabled later when supported.

## 3. Lightweight system metrics service

Inspect Nuxel's existing monitoring APIs, system services, frontend bridges and status telemetry before implementing a new service.

Prefer extending an existing lightweight telemetry service.

Otherwise, create a minimal unprivileged metrics collector using the most suitable existing project language.

Requirements:

- Read kernel-provided counters directly.
- Expose a small JSON payload to Nuxel Home through the existing local IPC/API mechanism.
- Bind locally only; do not expose metrics to the network.
- Do not require root unless a verified GPU interface genuinely requires privileges; avoid privileged GPU access by default.
- Reuse persistent file descriptors if beneficial.
- No subprocess per sampling interval.
- No Python process spawning every refresh.
- No large resident service for three numbers.
- Handle unavailable sources without crashing.
- Start only when the monitoring feature is enabled, if architecture permits.

Example payload:

```json
{
  "cpu_percent": 12.4,
  "memory_percent": 43.2,
  "gpu_percent": null,
  "gpu_status": "unavailable",
  "timestamp_ms": 123456789
}
```

Treat this as an interface example, not an instruction to invent readings.

## 4. Refresh policy and performance

**Default polling interval: 3 seconds.**

Add configurable refresh intervals:

- 1 second
- 2 seconds
- 3 seconds (default)
- 5 seconds
- 10 seconds

Use one shared polling loop, never three independent timers if one snapshot suffices.

Critical performance rules:

1. Do not refresh when the Home screen is hidden, unless an existing shared metrics consumer requires the samples.
2. Pause frontend polling when the screen is locked or blanked.
3. Stop polling completely when the user disables the feature.
4. Resume cleanly when Home becomes active.
5. Avoid DOM rebuilds; update only the affected labels and meter values.
6. Do not accumulate intervals after navigation or WebKit page reloads.
7. Prevent stale async responses from overwriting newer samples.
8. Avoid wakeups during system suspend.
9. Do not keep the phone awake for this feature.
10. Measure actual CPU overhead and memory footprint.

If 1-second polling significantly affects performance, show a warning in Settings and retain 3 seconds as the recommended interval.

The monitoring system must not meaningfully reduce battery life or launcher responsiveness.

## 5. Add controls to Home Settings

Locate the existing Nuxel Home Settings UI.

Add a section:

**Home Settings → System Monitor**

Controls:

**Show hardware meters**
- Toggle ON/OFF.
- **Default: ON.**
- OFF restores the Home layout without the meter widget.
- OFF also stops unnecessary sampling.

**Refresh interval**
- Selector for 1 / 2 / 3 / 5 / 10 seconds.
- Default 3 seconds.
- Apply changes without restarting Home.

Optional:

**Show detailed metrics**
- OFF by default.
- On tapping the compact meters, show expanded details if implemented.

Persist preferences using the existing Nuxel settings mechanism.

Defaults must apply correctly for new users and existing installations that have never set this preference.

An explicit OFF choice must persist across Home restarts and device reboots.

## 6. Correct deployment

Deploy the actual changed launcher files and any required telemetry service through the existing Nuxel live-USB deployment workflow.

Pay attention to previous asset and cache issues:

- Verify the active Home webroot.
- Update cache/service-worker versions if necessary.
- Verify actual running files match the source.
- Ensure the phone does not continue displaying an old cached launcher.
- Do not overwrite unrelated Home settings.
- Do not reset the user's application layout.

Before changing phone files, make a rollback backup.

**No flashing, partition writes, recovery modification or kernel replacement.**

## 7. Tests and acceptance criteria

Implement automated tests covering:

- Correct CPU delta calculation.
- Correct memory usage using `MemAvailable`.
- Accurate handling of missing GPU counters.
- Zero-divisor and malformed kernel data.
- Polling pause/resume lifecycle.
- Switching refresh intervals without duplicate timers.
- Toggle ON/OFF persistence.
- No lingering sampling when disabled.
- Launcher regression checks.

Then perform the live S10+ test:

1. Confirm the blue NUXEL text has disappeared from above the app icons.
2. Confirm CPU / MEM / GPU meters are visible across the full intended width.
3. Verify CPU responds to genuine system activity.
4. Verify RAM readings against `/proc/meminfo`.
5. Verify GPU readings against an actual supported counter, or honestly show N/A.
6. Turn the widget OFF in Home Settings and confirm sampling stops.
7. Turn it back ON and confirm it updates again.
8. Change the interval to 5 seconds and verify the cadence.
9. Navigate between desktops, applications and Quick Settings.
10. Confirm the launcher remains responsive.

Announce a 90-second owner test if physical interaction is required.

Collect meaningful service and application logs.

If something fails, fix it and repeat the relevant test.

## 8. Finish

Commit your implementation to the current dedicated feature branch and push that branch if remote access is configured.

Provide:

- Changed files.
- Metrics collector architecture.
- Real CPU/RAM/GPU source details.
- Measured refresh overhead.
- Automated test results.
- Live-phone verification results.
- Any limitations or remaining hardware blockers.

**SUCCESS = The previous blue NUXEL header becomes a compact live CPU / MEM / GPU monitor, enabled by default, configurable in Home Settings, and genuinely lightweight on the S10+.**

Do not stop at mockups. Implement, deploy, test and verify.

GO! 🐧🔥
