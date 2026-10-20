# 🐧🔥 NUXEL A38 — LIVE PHONE UX, GESTURES, AUDIO & SENSOR REPAIR

## MISSION: Make Nuxel behave like a real daily-driver Linux smartphone

You are a senior Linux mobile OS engineer, Wayland/WebKit UI engineer, JavaScript interaction specialist, ARM64 hardware engineer, and ALSA audio specialist.

**TARGET DEVICE**
- Samsung Galaxy S10+ SM-G975F (beyond2lte)
- Exynos 9820
- Nuxel Fedora ARM64 Linux
- Live USB connection to the development MacBook
- Current Nuxel A37 installation
- Actual phone is running and accessible

**IMPORTANT:** Nuxel is an independent Linux phone OS. Do not assume Android APIs, Android services, or an Android framework.

Work directly in the current Nuxel repository and deploy changes to the live phone through the established USB connection.

Read the existing A34/A36/A37 implementation, deployment guides, launcher code, input handlers, service definitions, and relevant test infrastructure before changing anything.

The new icons now work! Preserve every successfully working A37 asset and integration.

# 1. HOME SCREEN — REAL DRAG & DROP

Current problem: Long-pressing an app icon shows Remove and other actions, but moving the icon does not work.

Implement a complete touch-based launcher arrangement system.

### Long-press and drag
- Short tap launches the app normally.
- Long-press enters icon-edit mode.
- Once long-press is recognized, the icon follows the finger in real time.
- Move it freely around the home-screen grid.
- Show a floating dragged icon, destination indicator, and smooth movement animations.
- Cancel safely on touch cancellation.
- Make dragging work on the real touchscreen, not just mouse events.
- Prevent WebKit scrolling, text selection, and context menus from stealing a confirmed icon drag.

### Smart icon displacement

Implement automatic displacement rather than swapping only two icons.

Example:

Home-screen row:

`[A] [B] [C] [D]`

Dragging D between A and B should produce:

`[A] [D] [B] [C]`

Every affected icon moves automatically to the next available grid position.

Requirements:
- Use a deterministic grid insertion/reflow algorithm.
- Support displacement across rows.
- Handle occupied target slots.
- Cascade shifts through multiple occupied positions.
- Support movement in both directions.
- Animate the movement smoothly.
- Never overlap, lose, duplicate, or orphan apps.
- Preserve app identity and launch actions.
- Allow cross-page dragging if the launcher supports multiple home pages.
- Persist icon order across launcher restarts and phone reboots.

### Intelligent app folders

When dragging one icon **directly onto another icon**, create a folder containing both apps.

Important: A slight overlap should NOT automatically create a folder.

Use distinct drop-target logic:

- Near an icon or between icons → insert/reorder and push surrounding icons aside.
- Deliberately centered over an icon → highlight the folder target.
- A centered hover/dwell or explicit folder-target activation → prepare grouping.
- Release over the activated folder target → create the folder.

Suggested thresholds: clear inner center target and approximately 350 ms hover, tuned for touch accuracy.

Folders must support:
- Multiple app icons.
- Custom names.
- Opening and closing.
- Dragging apps into folders.
- Dragging apps out.
- Reordering folder contents.
- Removing an app without deleting the folder accidentally.
- Persistent folder contents and positions.
- Removing an empty folder safely.

Preserve existing long-press Remove/Edit actions without allowing their overlays to intercept the drag.

# 2. FIX ALL THREE NAVIGATION BUTTONS

### 🐧 Home — Penguin-face button

Currently pressing the penguin face does nothing.

Make it the real system Home button.

When pressed:
- Return to the launcher Home screen.
- Close Quick Settings, the app drawer, and Recents.
- Exit launcher edit/drag mode safely.
- Dismiss appropriate overlays.
- Work from every Nuxel application and UI state.
- Never leave the launcher invisible, blank, or unresponsive.

If already Home, remain Home without a disruptive reload.

Preserve the existing custom penguin PNG.

### Recents — Tabs button

Current bug: Pressing Recents flashes a screen for approximately 50 ms, then it disappears.

Fix the underlying cause instead of introducing artificial sleep delays.

Investigate:
- Click and touch event propagation.
- State transitions and unintended dismiss handlers.
- Focus/blur handling.
- Overlay lifecycle and z-index.
- WebKit rendering.
- Gesture recognizer conflicts.
- Timers, event races, and component unmounting.
- Navigation button event wiring.

Make Recents a persistent application switcher with:
- Running/recent app previews or meaningful app representations.
- Tap to return to an app.
- Swipe away/close supported apps safely.
- A functional back/close action.
- Proper Home integration.
- Stable visibility until intentionally dismissed.

Do not fabricate application previews when the compositor cannot provide them; use real metadata-based cards as a fallback.

### Back button

Preserve working Back behavior and ensure compatibility with Home, Recents, app folders, Quick Settings, and the app drawer.

# 3. NEW GESTURE SYSTEM

Implement a centralized, state-aware touch gesture manager.

Do not add unrelated competing swipe handlers across multiple components.

Use start-zone detection, directional thresholds, pointer ownership, and cancellation to avoid unintended actions.

## TOP HALF — QUICK SETTINGS

For gestures beginning in the upper half of the Home screen:

**Swipe down #1:**
- Open the notification/Quick Settings shade.
- Show the primary system toggles.
- Animate smoothly downward.

**Swipe down #2:**
- Expand Quick Settings fully.
- Reveal additional available system controls.
- Use existing Nuxel toggles and their actual states.
- Allow scrolling inside expanded Quick Settings.

**Swipe up:**
- From fully expanded: collapse to compact Quick Settings.
- From compact: close the shade completely.

Use the existing custom Quick Settings icons. Preserve actual Wi-Fi, Bluetooth, airplane mode, and other wired functionality.

The shade must never instantly disappear due to a conflicting click or swipe handler.

## BOTTOM HALF — APPLICATIONS AND SETTINGS

For gestures beginning in the lower half of the Home screen:

**Swipe up #1:**
- Open the full applications drawer.
- Display all installed/discoverable applications.
- Keep the application list touch-scrollable.
- Preserve existing search and app-launch functionality.

**Swipe up #2, while the app drawer is open:**
- Open Nuxel Settings directly.

**Swipe down while the app drawer is open:**
- Close the drawer and return Home.

Make the progression intuitive and state-dependent:

`HOME → ALL APPS → SETTINGS`

Do not require closing and reopening the drawer to access Settings.

Make the reverse navigation consistent with Back and Home.

### Critical gesture conflict rules

- Dragging icons must take precedence after a valid long-press.
- Ordinary application-list scrolling must still work.
- Quick Settings scrolling must still work.
- Keyboard input and text selection must remain usable.
- Do not hijack swipes in scrollable content.
- Recognize intentional horizontal versus vertical gestures.
- Use reasonable thresholds, velocities, and touch slop.
- Avoid repeated events from one finger gesture.
- Do not trigger unrelated actions from the same swipe.
- Keep interactions smooth on actual S10+ hardware.

Implement regression tests for gesture-direction conflicts and state transitions.

# 4. SCROLLBARS — THIN, VISUAL ONLY

Update horizontal and vertical scrollbars throughout the Nuxel launcher/UI.

Requirements:
- Much thinner and less intrusive.
- Subtle visual styling matching Nuxel.
- No large desktop-style scroll handles.
- No draggable or clickable scrollbar thumb.
- No scrollbar hit area obstructing touch content.
- Show position visually only.
- Preserve native finger scrolling, momentum, and overscroll behavior where appropriate.
- Support both horizontal and vertical scroll regions.

Use the appropriate WebKit-compatible styling.

If native scrollbars cannot reliably be made noninteractive, hide them and implement thin, noninteractive overlay scroll indicators with `pointer-events: none`.

Do not disable actual scrolling.

# 5. FIX ROTATION, ACCELEROMETER & GYROSCOPE

Investigate the real device's rotation pipeline.

Inspect:
- Kernel sensor drivers.
- `/sys/bus/iio/devices/`
- Sensor availability and readable values.
- Available input devices.
- Existing Nuxel sensor services.
- Sensor initialization and orientation processing.
- The display compositor.
- WebKit viewport dimensions and resizing.
- Existing rotation lock and orientation settings.

Identify the real accelerometer and gyroscope hardware through available device evidence.

Implement proper screen auto-rotation:
- Portrait.
- Landscape left.
- Landscape right.
- Return to portrait.
- Rotation lock.
- Correct touch-coordinate mapping after rotation.
- Correct launcher grid layout after rotation.
- Correct Quick Settings and navigation layout.
- Correct framebuffer/compositor orientation.

Avoid jitter by using a stable orientation filter, thresholds, and hysteresis.

Don't rotate the screen based on unsupported assumptions or fabricate sensor values.

If the kernel does not expose a required sensor, document the exact driver, firmware, or service blocker. Implement the working userspace pieces while preserving manual rotation.

Do not modify or replace the kernel during this mission.

# 6. AUDIO — CRITICAL HARDWARE BLOCKER

**CURRENT STATUS: ZERO AUDIBLE AUDIO.**

The startup sound does not play audibly.

Volume Up/Down does not produce `nuxel-pow.mp3`.

This has persisted through A36 and A37. Do not treat another successful MP3 decoder invocation as a fix.

### Diagnose the real audio pipeline

Inspect:
- `aplay -l`
- `aplay -L`
- `amixer`
- `alsactl`
- Existing ALSA UCM configurations.
- Sound devices and PCM streams.
- PipeWire/PulseAudio where installed.
- `mpg123` and MP3 decoding.
- Sound helper logs.
- Systemd audio services.
- Firmware loading and kernel messages.
- Real speaker routing and mute controls.
- Existing `beyond-madera` configuration.

Investigate the confirmed codecs and amplifier interfaces where supported by hardware discovery, including the CS47L93/CS35L40 audio chain.

Determine exactly where the signal stops.

Check whether the problem lies in:
1. Application sound triggering.
2. Audio decoding.
3. PCM device opening.
4. Audio server configuration.
5. Codec initialization.
6. Hardware mixer/routing.
7. Amplifier enablement.
8. Firmware loading.
9. Speaker output.

Use verified device-specific controls. Do not invent amplifier registers or blindly apply mixer configurations copied from other phones.

### Restore both cues

**Startup sound**
- Play the existing original Nuxel startup MP3.
- Trigger once after successful animation-to-launcher handoff.
- Use the existing 44% software PCM gain request.
- Preserve the protective physical mixer cap until actual speaker output is safely verified.

**Volume buttons**
- Volume Up changes the actual output level.
- Volume Down changes the actual output level.
- Both trigger the existing `nuxel-pow.mp3` immediately.
- The cue uses the newly selected safe output level.
- Avoid overlapping playback floods from rapid button presses.

Test low-volume playback before increasing hardware output.

Physical sound must be confirmed by the owner.

If hardware speaker routing remains blocked, return the exact evidence, required missing component, and smallest safe next repair. Do not report fake audio success.

# 7. PRESERVE WORKING A37 FUNCTIONALITY

Do not regress:
- All custom app icons.
- Navigation PNG artwork.
- Quick Settings PNG artwork.
- Existing haptic feedback.
- Keyboard input and any working keyboard haptics.
- Wi-Fi and networking.
- USB connectivity.
- Touchscreen operation.
- Application launching.
- Boot animation and launcher startup.
- Existing recovery capabilities.

Maintain the existing Nuxel codebase. No unnecessary subsystem rewrites.

# 8. LIVE USB DEPLOYMENT

**THIS IS AN IMPLEMENTATION AND DEPLOYMENT MISSION, NOT A REPORT-WRITING EXERCISE.**

Execute in this sequence:

1. Confirm the actual live USB shell connection.
2. Determine the active working repository and device deployment paths.
3. Record baseline service status, software versions, and relevant logs.
4. Back up every file that will be changed on the device.
5. Record SHA-256 hashes for original files and backup locations.
6. Implement the launcher, drag/drop, navigation, gestures, scrollbar, sensor, and audio repairs.
7. Build and run relevant tests on the MacBook.
8. Cross-compile native components for Linux AArch64 where required.
9. Deploy to the actual active phone installation.
10. Invalidate affected WebKit and service-worker caches safely.
11. Restart only necessary services without dropping the USB console.
12. Validate deployed files and actual runtime state.
13. Inspect runtime errors and fix problems.
14. Conduct physical testing.
15. Perform one controlled normal reboot when safe.
16. Verify persistence and restore services after boot.

Do not overwrite user launcher layouts, folder arrangements, or Nuxel configuration unnecessarily. Provide migration for existing persistent layouts.

# 9. PHYSICAL ACCEPTANCE TEST

Announce when the live UI is ready for physical testing.

Ask me to perform these tests:

- Drag an icon to an empty position.
- Drag an icon between occupied positions and observe displacement.
- Group two icons into a folder.
- Open, close, and rename the folder.
- Press Penguin Home.
- Open Recents and leave it visible for several seconds.
- Switch back to an application from Recents.
- Swipe down from the upper half twice.
- Swipe upward to collapse and close Quick Settings.
- Swipe upward from the bottom half to open All Apps.
- Swipe upward again to open Settings.
- Swipe downward to close the app drawer when it is open.
- Scroll lists using touch.
- Rotate the phone in both landscape directions and back.
- Press Volume Up and Volume Down and listen.
- Reboot and listen for the startup cue.

Capture logs and diagnostic evidence during each test.

Do not claim gestures, rotation, speaker playback, or physical touch interactions passed without observing device state and obtaining owner feedback where necessary.

Fix failures and retest.

# 10. TEST AND RELEASE GATES

Add automated tests for:
- Long-press and drag state.
- Icon insertion and cascading displacement.
- Folder creation and removal.
- Layout persistence.
- Home navigation.
- Recents visibility and dismissal.
- Quick Settings two-stage transitions.
- App drawer and Settings transitions.
- Gesture arbitration.
- Rotation and viewport layout.
- Audio cue triggering and failures.

Report separately:

**SOURCE VERIFIED** — Code and tests pass.

**DEPLOYMENT VERIFIED** — Files and services are confirmed on the live S10+.

**HARDWARE VERIFIED** — Real physical behavior is confirmed.

Maintain distinct PASS / FAIL / BLOCKED / NOT TESTED verdicts for every feature.

## NONNEGOTIABLE SAFETY RULES

- NO FLASHING.
- NO PARTITION WRITES.
- NO KERNEL REPLACEMENT.
- NO BOOTLOADER MODIFICATION.
- NO UNVERIFIED AMPLIFIER SETTINGS.
- NO UNNECESSARY REBOOT LOOPS.
- NO DESTRUCTIVE RESET.
- KEEP THE LIVE USB CONSOLE RECOVERABLE.
- BACK UP AND MAINTAIN ROLLBACK PROCEDURES.

Don't stop at dry runs. Repair what can safely be repaired, deploy it, run tests, and validate the real device.

If a hardware-specific blocker cannot safely be solved, preserve the working phone and report the precise blocker rather than guessing.

**FINAL OBJECTIVE: NUXEL A38 — TOUCH-DRIVEN, DRAGGABLE, ROTATABLE, NAVIGABLE, AND AUDIBLE.**

**EXECUTE NOW. 🐧🔥**
