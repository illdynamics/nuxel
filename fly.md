# 🐧🔥 NUXEL A39 — SMART DOCK, MULTI-DESKTOP & SYSTEM UX REFINEMENT

## MISSION: Upgrade the live Nuxel phone into a polished, fully interactive mobile Linux environment

You are a senior Linux mobile OS engineer, Wayland compositor specialist, WebKit/JavaScript UI engineer, Linux input engineer, ALSA hardware audio specialist, and performance optimization engineer.

### Target environment

- **Device:** Samsung Galaxy S10+ SM-G975F (beyond2lte)
- **Hardware:** Samsung Exynos 9820
- **OS:** Nuxel — custom Fedora-based ARM64 Linux
- **Connection:** Live USB-connected phone
- **Development:** MacBook with the current Nuxel repository
- **Current baseline:** Latest deployed Nuxel A38 changes, where present

**MISSION TYPE: IMPLEMENT → BUILD → TEST → DEPLOY → PHYSICAL VERIFY → REPAIR.**

You have permission to use the connected development machine and live USB console to perform this mission.

Inspect the current source tree and live deployment before changing anything. Do not assume all previous A38 changes have been deployed successfully.

Preserve working functionality, icons, haptics, keyboard, launcher, Quick Settings, gestures, and existing application behavior.

---

# 1. CUSTOM FOUR-ICON BOTTOM DOCK

Use the supplied asset:

`./assets/nuxel-bottom-bar.jpg`

This image must become the background of the fixed four-application dock on the Home screen.

### Requirements

- Display the supplied artwork behind the four dock icons.
- Preserve the original image rather than approximating it with CSS.
- Maintain correct proportions and transparency behavior where applicable.
- Scale cleanly to the Galaxy S10+ screen dimensions.
- Preserve the existing four icon positions and app-launch behavior.
- Ensure icon alignment and touch-target sizes remain correct.
- Respect screen safe areas and the bottom three-button navigation.
- Keep the dock visually consistent across both Home desktops.
- The dock itself stays fixed while changing desktops.
- Never allow the wallpaper or dock background to capture icon taps.
- Avoid stretched, tiled, or cropped artwork unless explicitly necessary for the layout.

Resolve the actual browser asset path, deploy the image to the active phone webroot, and invalidate relevant caches.

Verify the real JPG appears on the live screen.

# 2. APP DRAWER — LONG-PRESS TO ADD TO HOME

Currently the All Applications drawer displays installed applications.

Upgrade it to support proper touch-based app placement.

### Long-press and drag

When the user long-presses an application icon inside the app drawer:

1. Recognize the long-press.
2. Create a floating representation of the selected icon.
3. Close the app drawer while retaining the drag session.
4. Reveal the current Home desktop.
5. Keep the selected icon attached to the user's finger.
6. Allow immediate dragging across the Home grid.
7. Show valid placement locations.
8. Releasing the finger places the application on Home.

**Critical:** Do not destroy the active pointer/drag session when the app drawer closes or unmounts. Use a shared launcher-level drag controller capable of surviving the UI transition.

### App drawer context menu

On long-press, also provide a usable action menu containing:

**Add to Home screen**

Use a clear distinction between dragging and choosing an action. A long-press may open the menu initially, but moving the finger beyond touch slop must transition into a real drag without requiring a second long-press.

Selecting Add to Home should:
- Add the selected app to the first suitable available Home slot.
- Prefer the currently selected desktop.
- Create or use another desktop only according to configured behavior.
- Preserve existing icon order.
- Prevent accidental duplicate shortcuts unless explicitly supported.
- Confirm placement visually.

Integrate with the existing A38 folder creation and icon displacement system.

# 3. LOCK / UNLOCK HOME SCREEN

Implement a real Home layout lock.

### Home Settings access

Long-pressing an empty wallpaper area must open the Home customization menu.

Include:

- Home Settings
- Wallpaper options where already supported
- Home screen lock/unlock
- Desktop/page configuration
- Battery indicator preferences

### Home screen lock

When Home is locked:
- Icons cannot be rearranged.
- No accidental folder creation.
- Icons cannot be removed by dragging.
- App drawer shortcuts cannot be dropped onto Home.
- Existing applications still launch normally.
- Desktop swiping continues working.
- Dock icons continue launching normally.
- Navigation and gestures keep working.

When attempting prohibited editing, show a subtle message:

**"Home screen locked — unlock in Home Settings."**

Unlocking restores all drag, drop, folder, removal, and arrangement functionality.

Persist this preference across launcher and device restarts.

Do not lock the entire phone or alter the security lock screen. This setting controls only Home layout editing.

# 4. MULTIPLE HOME DESKTOPS

Implement fully functional multi-page Home desktops.

**Default: TWO desktops.**

Allow configuration of the number of desktops in Home Settings.

Start with a minimum of 1 and a reasonable maximum based on launcher capabilities, such as 8.

### Desktop navigation

- Desktop 1 is the primary Home screen.
- Swipe horizontally left on Desktop 1 to reveal Desktop 2 on the right.
- Swipe right on Desktop 2 to return to Desktop 1.
- Extend the same behavior to additional configured pages.
- Animate transitions smoothly.
- Preserve icon positions independently on every desktop.
- Support dragging icons between desktops using edge-hover/auto-scroll.

### Static wallpaper — IMPORTANT

**The wallpaper must remain absolutely stationary.**

Only the application icons and desktop contents should move horizontally.

The wallpaper:
- Must not scroll.
- Must not parallax.
- Must not stretch during swipes.
- Must not reload between desktops.
- Must remain aligned with the screen.

The four-icon bottom dock also stays stationary.

### Desktop page indicator

Add a small, elegant, semitransparent page indicator above the dock.

For two desktops, use two subtle dots.

Examples:

`● ○` — Desktop 1

`○ ●` — Desktop 2

Requirements:
- Small and unobtrusive.
- Semi-transparent.
- Active page clearly indicated.
- Updates during desktop transitions.
- Does not obscure icons.
- Matches the Nuxel design language.
- Supports configurable page counts.

### Desktop Settings

Allow:
- Changing desktop count.
- Adding/removing desktops.
- Selecting primary desktop (default desktop 1).
- Viewing desktop count.
- Preserving layouts across reboots.

When reducing desktop count, never silently delete apps or folders.

Move affected shortcuts to available pages only with safe, deterministic migration; if capacity is insufficient, require confirmation and preserve recoverable layout data.

# 5. PENGUIN HOME BUTTON — TRUE SYSTEM HOME

The middle navigation button, using the Nuxel penguin face, must function as the actual system-wide Home button.

**One press ALWAYS returns to the primary desktop.**

### Required behavior

When any application is open:
- Minimize or hide the active application window.
- Return focus to the launcher.
- Display primary Home desktop.
- Preserve application state and process execution.
- Do not kill the application.

When multiple applications are open:
- Return the visible window stack to the launcher.
- Ensure no application remains obscuring Home.
- Preserve running applications for Recents.

When on Desktop 2:
- Smoothly return to Desktop 1.
- Keep the wallpaper fixed.
- Keep the dock stationary.

When inside:
- App drawer → close it and return Home.
- Settings → minimize/leave Settings and return Home.
- Quick Settings → dismiss it and return Home.
- Recents → close Recents and return Home.
- Folder → close folder and return Home.

Do not make Home dependent on app-specific browser history.

Implement the necessary interaction with the actual compositor/window manager and launcher state.

**Acceptance:** No matter what is currently visible, pressing the penguin once brings up the primary Home desktop.

# 6. FIX BACK BUTTON — REAL WINDOW / APPLICATION BACK

The bottom Back button must perform context-aware navigation.

### Expected hierarchy

Inside an application:
- Navigate backward within the application where supported.
- Use the application's actual navigation interface or web history where appropriate.
- If the app has no applicable back action, return to the launcher or previous window according to the defined Nuxel window-navigation policy.

Inside Settings:
- Go to the previous Settings page.
- At the root, return to the previous appropriate screen.

Inside an open folder:
- Close the folder first.

Inside Quick Settings:
- Collapse expanded shade first.
- Close compact shade next.

Inside Recents:
- Close Recents and return to the preceding screen.

Inside App Drawer:
- Close the drawer.

### Engineering requirements

Inspect the existing:
- Button manager
- WebKit navigation
- Window/compositor state
- Application lifecycle
- Focus handling
- Back event dispatch

Avoid sending ineffective or duplicate Escape key events.

Implement a centralized navigation policy with clearly defined event ownership.

Do not terminate processes just because Back is pressed.

Home and Back must behave differently.

# 7. IMPROVE SCROLLING SMOOTHNESS

Current issue: Scrolling in Settings occasionally appears glitchy or laggy.

Investigate before optimizing.

### Performance diagnosis

Measure:
- UI frame times
- Long JavaScript tasks
- Excessive DOM updates
- Layout recalculations
- Paint/compositing overhead
- Expensive CSS effects
- Settings-page rendering cost
- Debug console/log component overhead
- CPU consumption and memory pressure
- Input event latency
- Software versus GPU-assisted rendering

Identify whether the debug-console screens are contributing to the issue.

### Implement optimizations

Where appropriate:
- Batch DOM updates.
- Reduce unnecessary re-renders.
- Throttle high-frequency debug updates.
- Limit retained log entries.
- Virtualize large scrolling debug/log lists.
- Avoid synchronous work during touchmove.
- Use compositor-friendly CSS transforms.
- Avoid expensive full-page repaints.
- Preserve native kinetic/momentum scrolling.
- Remove conflicting touch handlers.
- Reduce unnecessary gesture-listener interference.
- Limit animations to necessary layers.

Target consistent 60 FPS where the device and compositor support it.

Never solve performance issues by disabling critical logs, breaking scroll input, or hiding actual errors.

Measure before and after and report results.

# 8. MAKE ALL SCROLLBARS 2–3× THINNER

The current white/blue horizontal and vertical scrollbars are too thick.

Reduce their visible thickness to approximately **one-third to one-half of the existing value**.

Apply to:
- Launcher pages where applicable
- Settings
- Applications drawer
- Debug consoles
- Other Nuxel scrollable areas

Requirements:
- Thin, elegant indicator.
- Subtle white/blue appearance consistent with Nuxel.
- Works vertically and horizontally.
- Does not capture taps or drags.
- Does not block content.
- Scrolling must happen by finger movement.
- No interactive desktop-style scrollbar handles.

Where native WebKit scrollbars remain interactive, replace them with lightweight noninteractive overlay indicators using `pointer-events: none`, while preserving native content scrolling.

Verify that the scrollbars do not obscure app icons or navigation controls.

# 9. TOP STATUS BAR — ELIMINATE ICON OVERLAPS

Current problems:
- Two Wi-Fi icons appear on top of each other.
- Something is visually overlapping or appearing behind the battery icon.
- Battery percentage currently appears outside or incorrectly relative to the battery.

Inspect the real status-bar component tree and CSS.

### Fix duplicate Wi-Fi icons

Determine whether duplication is caused by:
- Two independent renderers.
- Duplicate event subscriptions.
- Repeated DOM insertion.
- Old status-bar components surviving reloads.
- Incorrect positioning.
- Multiple network indicators representing the same interface.
- Unremoved legacy icons.

Fix the actual root cause.

There must be exactly one primary Wi-Fi status indicator representing the actual Wi-Fi state.

Do not hide the symptom with arbitrary z-index changes.

### Proper icon spacing

Implement a predictable status-indicator layout.

Requirements:
- No icon overlaps.
- No invisible elements occupying incorrect positions.
- Proper spacing around battery, Wi-Fi, signal, and other indicators.
- Correct sizing on the S10+.
- Responsive behavior for screen rotation.
- Correct notch/cutout/safe-area handling.
- Stable layout as status values change.
- No duplicate subscriptions during repeated component initialization.

# 10. BATTERY DISPLAY MODES — HOME SETTINGS

Add an option in Home Settings:

**Battery indicator style**

The user can choose between exactly three modes.

### Mode A — Battery icon with percentage inside

Default recommended mode.

Render a battery icon with the actual percentage **inside the icon**.

Example: `100%` inside the battery outline.

Requirements:
- Text fully contained in the battery body.
- Correct horizontal/vertical centering.
- Readable at real phone screen size.
- Charging indication without obscuring the percentage.
- Accurate percentage from real battery data.

### Mode B — Percentage only

Show only the numeric battery percentage.

Examples:
- `100%`
- `67%`
- `12%`

No battery-shaped icon.

### Mode C — Battery bar only

Show the battery shape with a fill indicator representing actual charge level.

Examples:
- 100% → Completely filled.
- 75% → Approximately three-quarters filled.
- 50% → Exactly half filled.
- 25% → Quarter filled.
- 10% → Approximately one-tenth filled.

Do not display percentage text in this mode.

### Battery data integration

Read live battery information from the existing Nuxel power-management service or Linux power_supply/UPower interfaces, as appropriate.

The battery UI must:
- Reflect real charge level.
- Update when percentage changes.
- Reflect charging state.
- Avoid unnecessary rapid polling.
- Survive UI restarts.
- Never fabricate a fixed 100% value.

Persist the chosen display mode across reboots.

Settings changes must immediately update the top status bar.

Keep the existing custom icon styling where possible.

# 11. AUDIO — STILL NOT AUDIBLE

**CRITICAL: Physical audio remains unverified/nonfunctional.**

Despite previous attempts, we still do not hear:
- Nuxel startup sound.
- `nuxel-pow.mp3` when adjusting volume.
- Other expected speaker audio.

This requires deeper hardware-level investigation, not merely another MP3 helper modification.

### Required investigation

Inspect the entire chain:

Application/event → decoder → PCM stream → ALSA device → codec → amplifier → physical speaker.

Read:
- `aplay -l`
- `aplay -L`
- `amixer`
- `alsactl`
- `journalctl`
- Kernel sound-related logs
- Existing Nuxel audio diagnostics
- `/proc/asound/`
- `/sys/class/sound/`
- ALSA UCM configuration
- Relevant device tree evidence
- Firmware-loading results
- Device-specific audio routing

Investigate the actual audio implementation on the Galaxy S10+ Exynos 9820, including the Madera codec and speaker-amplifier path as verified from available hardware information.

Determine whether the actual problem is:
- Missing firmware
- Missing or incorrect ALSA UCM verbs
- Disabled amplifier
- Incorrect PCM device
- Missing codec routing
- Incorrect DAPM routing
- Audio service permissions
- Missing hardware initialization
- Unsupported/missing kernel functionality

### Safety

Do not guess speaker-amplifier mixer values.

Do not disable protection circuits.

Do not blindly copy mixer values from unrelated devices.

Preserve the existing conservative hardware-volume limits.

Test using low-volume output, gradually, with explicit hardware verification.

If existing kernel drivers cannot produce speaker output, document the exact missing capability and implement only safe supporting fixes.

**Success means I actually hear sound from my S10+.**

A zero exit code is not proof of audible output.

# 12. DEPLOY TO THE LIVE S10+

This is not merely a coding assignment.

You must execute the changes on the USB-connected Nuxel phone.

### Deployment procedure

1. Inspect the latest working repository and running device.
2. Confirm live USB connection and shell access.
3. Record baseline state and active services.
4. Back up all affected phone files.
5. Preserve current launcher layouts and Home settings.
6. Implement source changes.
7. Add regression tests.
8. Run available source tests.
9. Build any required Linux ARM64 components.
10. Deploy to the active phone filesystem, not an unused staging webroot.
11. Verify hashes for deployed artwork and changed binaries.
12. Invalidate relevant WebKit caches.
13. Restart only affected services.
14. Preserve USB console recovery.
15. Verify the running launcher actually uses the updated files.
16. Diagnose runtime errors.
17. Conduct physical acceptance tests.
18. Repair failures.
19. Perform one controlled normal reboot only after stability is confirmed.
20. Verify all persistent preferences and application layouts survive reboot.

Do not overwrite the user's existing Home layout accidentally.

Maintain rollback instructions and a deploy receipt containing timestamps, hashes, service states, and test results.

# 13. PHYSICAL ACCEPTANCE TEST

After deployment, announce that physical testing is ready.

Ask me to perform these tests on the actual S10+:

**Dock**
- Confirm the custom `nuxel-bottom-bar.jpg` artwork appears behind the four dock icons.

**App drawer**
- Open All Apps.
- Hold an app icon.
- Drag it directly to Home.
- Test Add to Home from the context menu.

**Home settings**
- Long-press the wallpaper.
- Lock Home.
- Confirm icons cannot be rearranged.
- Unlock Home.
- Confirm icons can move again.

**Desktops**
- Swipe to Desktop 2.
- Verify the page indicator changes.
- Verify the wallpaper does not move.
- Verify the dock stays fixed.
- Drag an icon between desktops.
- Press Penguin Home and confirm it returns to Desktop 1.

**Navigation**
- Open an app and press Home.
- Confirm the app is minimized, not killed.
- Open Recents and return to the app.
- Press Back inside an app and confirm meaningful backward navigation.

**Scrolling**
- Scroll Settings rapidly.
- Scroll the debug console.
- Confirm smooth gestures and thinner, noninteractive indicators.

**Status bar**
- Verify only one Wi-Fi icon.
- Verify icons never overlap.
- Test all three battery display modes.
- Confirm battery data corresponds to the real battery state.

**Audio**
- Test safe low-volume speaker playback.
- Test volume feedback.
- Verify startup audio after one controlled reboot.

Collect relevant live logs and ask me for PASS/FAIL feedback.

Do not classify a feature as physically verified without evidence from the device and, where needed, my confirmation.

# 14. QUALITY GATES

Implement or extend automated coverage for:

- Dock background asset loading
- App drawer drag ownership across overlay transitions
- Add to Home
- Home layout locking
- Multi-desktop persistence
- Desktop count changes and migrations
- Primary Home navigation
- Application minimization and restoration
- Context-sensitive Back navigation
- Scroll responsiveness regressions
- Scrollbar noninteraction
- Status-bar singleton rendering
- Battery mode changes and real data binding
- Audio pipeline error handling

Produce final results with distinct statuses:

- **SOURCE VERIFIED**
- **DEPLOYMENT VERIFIED**
- **HARDWARE VERIFIED**
- **BLOCKED**
- **NOT TESTED**

Include remaining blockers and their exact supporting evidence.

# NONNEGOTIABLE RESTRICTIONS

- NO FLASHING.
- NO PARTITION WRITES.
- NO KERNEL REPLACEMENT.
- NO BOOTLOADER MODIFICATIONS.
- NO DESTRUCTIVE REINSTALL.
- NO UNVERIFIED SPEAKER-AMPLIFIER SETTINGS.
- NO FALSE PASS RESULTS.
- DO NOT BREAK THE LIVE USB CONSOLE.
- DO NOT REGRESS WORKING A37/A38 FEATURES.
- ALWAYS KEEP ROLLBACK CAPABILITY.

Implement fixes and deploy them to the live phone. Do not stop after source changes or simulations.

## FINAL OBJECTIVE

Deliver **NUXEL A39**, with:

- Custom graphical dock
- App drawer-to-Home dragging
- Configurable Home lock
- Two independent desktops by default
- Fixed wallpaper
- Functional system Home and Back
- Smoother touch scrolling
- Ultra-thin scroll indicators
- Clean, nonoverlapping status icons
- Three configurable live battery display modes
- Verified audio repairs or a precise hardware-level blocker

**EXECUTE NOW — MAKE THE PENGUIN FLY! 🐧🔥**

# A39 ADDITION — SWITCHABLE BOTTOM DOCK BACKGROUNDS

Extend **Home Settings** with a new option:

**Dock Background**

Initially support two selectable backgrounds:

- **BG1 — Classic:** `./assets/nuxel-bottom-bar.jpg`
- **BG2 — Alternative:** `./assets/nuxel-bottom-bar2.png`

**DEFAULT: BG2 (`nuxel-bottom-bar2.png`).**

### Requirements

1. Add a Dock Background selector in Home Settings with BG1 and BG2.
2. Display a thumbnail preview of each background.
3. Highlight the currently selected background.
4. Switch backgrounds immediately when selected, without restarting the launcher.
5. Persist the selected background across application restarts and phone reboots.
6. Use BG2 on fresh installations.
7. For existing installations without a saved preference, initialize to BG2.
8. Keep the four dock app icons and their positions unchanged when switching backgrounds.
9. Preserve PNG transparency in BG2, without introducing an opaque container behind it.
10. Maintain correct image proportions and responsive sizing.
11. Keep the dock stationary when switching between Home desktops.
12. Ensure the dock background never intercepts touch events.
13. Resolve assets through the actual active Nuxel webroot.
14. Verify both backgrounds load successfully and match the source files by SHA-256.
15. Ensure Home layout locking does not prevent changing the dock background through Home Settings.

### UI behavior

Home Settings → Dock Background → BG1 / BG2

Changing the selection must update the dock instantly.

### Acceptance criteria

- Fresh A39 installation starts with BG2.
- Selecting BG1 immediately shows `nuxel-bottom-bar.jpg`.
- Selecting BG2 immediately shows `nuxel-bottom-bar2.png`.
- Both backgrounds retain their intended appearance.
- All four dock icons remain functional.
- Switching desktops does not change the dock background.
- Selected background survives a normal reboot.
- Missing or corrupt artwork produces a safe fallback without breaking the dock.

Add automated tests and verify both backgrounds on the live USB-connected S10+.

**Integrate this directly into A39. Do not treat it as a separate feature branch or release. Deploy and physically verify it alongside the other A39 changes. 🐧🔥**
