# FULL-PWNAGE-43000
# NUXEL — BOOT SPEED, LOCKSCREEN, UI RESPONSIVENESS, APPLICATIONS & USB FILE TRANSFER

## COMPLETE IMPLEMENTATION, OPTIMIZATION AND DEVICE-VERIFICATION MISSION

**Mission ID:** PWNAGE-43000  
**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820  
**OS:** Nuxel — custom Fedora-based ARM64 Linux phone OS  
**Connection:** Existing Wi-Fi SSH  
**Objective:** Faster boot, clean transitions, responsive UI, functional touchscreen while charging, real Linux application installation and working USB file transfer.

---

# 0. MISSION OBJECTIVE

The phone is making good progress, but several areas still need substantial work.

This mission covers:

1. Boot speed, especially the spinning penguin stage.
2. Slow reboot initiation and black-screen delay.
3. Broken transition after the preloading video.
4. Unwanted LPM/charging-mode restrictions on touchscreen interaction.
5. Slow Quick Settings open/close performance.
6. Sluggish Home Settings.
7. Lockscreen responsiveness.
8. Home button keyboard dismissal.
9. Installation and integration of native Linux and Flatpak applications.
10. Functional USB Charging/File Transfer mode from the lockscreen.

This is a real implementation mission.

Do not simply produce recommendations.

Inspect the actual running system and source code, identify the causes, implement corrections, test them, deploy them and verify them on the physical phone.

**Preserve the recent improvements to general application performance. Do not make already-fast applications slower to optimize the few problematic screens.**

---

# 1. EXECUTION ORDER

Create a TODO checklist and evidence directory before making changes.

Use this order:

```text
INITIAL INVENTORY AND BACKUPS
           |
           v
BOOT AND REBOOT PERFORMANCE ANALYSIS
           |
           v
FIX BOOT CRITICAL PATH
           |
           v
FIX REBOOT BLACK-SCREEN DELAY
           |
           v
FIX PRELOADING VIDEO -> LOCKSCREEN TRANSITION
           |
           v
FIX LPM / CHARGING TOUCHSCREEN BEHAVIOR
           |
           v
OPTIMIZE QUICK SETTINGS
           |
           v
OPTIMIZE HOME SETTINGS
           |
           v
FIX HOME KEYBOARD DISMISSAL
           |
           v
OPTIMIZE LOCKSCREEN
           |
           v
INSTALL AND VERIFY APPLICATIONS
           |
           v
IMPLEMENT LOCKSCREEN USB MODES
           |
           v
TEST REAL USB FILE TRANSFER
           |
           v
RUN FULL REGRESSION TESTS
           |
           v
FINAL REBOOT
           |
           v
VERIFY COMPLETE SYSTEM
```

Do not jump to changing boot splash artwork or removing boot stages before measuring what is taking the time.

Do not remove required system initialization merely to make the penguin animation shorter.

---

# 2. INITIAL SYSTEM INVENTORY

Inspect the current repository and live S10+.

Record:

- Git branch and commit.
- Uncommitted changes.
- Kernel version.
- OS version.
- Display backend.
- UI renderer.
- Session manager.
- Systemd boot targets.
- Relevant service units.
- Current boot configuration.
- Preloading-video implementation.
- Lockscreen initialization.
- Quick Settings implementation.
- Home Settings implementation.
- Input-method/keyboard implementation.
- Charging and LPM services.
- USB gadget configuration.
- Installed packages.
- Flatpak remotes and installed applications.
- Mounted filesystems.
- USB controller and UDC state.
- Current file-transfer implementation.
- Current system and UI logs.

Create:

`docs/beta-finalization/live/PWNAGE-43000-TODO.md`

Create:

`docs/beta-finalization/live/evidence/pwnage-43000/`

Record the starting measurements before changes.

Do not assume that Nuxel is using a particular compositor, display manager or audio/video player without checking the live system.

Preserve the actual current USB console/recovery functionality.

Do not overwrite unrelated user changes.

---

# 3. P0 — OPTIMIZE BOOT SPEED, ESPECIALLY THE SPINNING PENGUIN

## 3.1 Reported behavior

The biggest perceived delay occurs during the spinning penguin boot stage.

The phone spends too long showing the spinning penguin before reaching the preloading video or next boot stage.

The objective is to reduce the actual elapsed time until the phone becomes usable.

Do not simply make the animation disappear sooner while the system is still unavailable.

## 3.2 Measure the actual boot timeline

Capture:

- Power-on start, where measurable.
- Kernel start.
- Root filesystem availability.
- systemd initialization.
- Critical hardware initialization.
- NetworkManager readiness.
- WLAN readiness.
- Display readiness.
- UI runtime readiness.
- Nuxel session readiness.
- Preloading-video start.
- Preloading-video finish.
- Lockscreen ready.
- Touch input ready.
- Home desktop ready.

Use:

- `systemd-analyze`
- `systemd-analyze blame`
- `systemd-analyze critical-chain`
- `journalctl -b`
- Service-specific timestamps.
- Existing Nuxel boot event logging.

Where the platform permits, use monotonic timestamps for each stage.

Do not assume that `systemd-analyze blame` alone gives the complete critical path.

A service can run slowly without delaying the final target if it is not on the boot-critical path.

Identify actual dependency chains.

## 3.3 Identify why the spinning penguin stays visible

Locate the actual spinning-penguin animation implementation.

Inspect:

- Boot-stage state machine.
- Animation start and stop conditions.
- Any fixed minimum animation duration.
- Any fixed timeout waiting for services.
- Polling frequency.
- Readiness conditions.
- Display update loop.
- Frame rendering.
- Video preparation.
- Filesystem access.
- Image decoding.
- Any subprocess started by the boot animation.

Determine whether the animation remains visible because:

1. Boot really is taking a long time.
2. The animation has a fixed duration.
3. The UI waits for an unnecessary service.
4. The UI does not receive a readiness notification.
5. A slow polling loop delays the transition.
6. The renderer is not ready.
7. The video is decoded only after the animation completes.
8. Another service is repeatedly restarting.
9. A blocking synchronous operation is executing on the UI thread.

Fix the actual cause.

## 3.4 Remove unnecessary boot dependencies

Inspect the critical boot path.

Look for:

- Unnecessary `After=` and `Requires=` dependencies.
- Services waiting for optional devices.
- Serial-console waits.
- Network-online waits that should not block the lockscreen.
- Repeated hardware probes.
- Redundant configuration parsing.
- Slow package-manager or filesystem scans.
- Excessive service retries.
- Long fixed sleeps.
- Blocking script execution.
- UI processes waiting synchronously for applications that are not needed for the lockscreen.

Only decouple services that do not need to block the user-visible boot path.

Do not remove dependencies required for safe hardware initialization.

Examples of services that may be possible to start in the background, subject to actual dependency analysis:

- Application catalog refresh.
- Flatpak inventory refresh.
- NuXtore metadata.
- Optional GPS provider.
- Nonessential application indexing.
- Unused hardware discovery.
- Background asset cache preparation.

Preserve mandatory:

- Display initialization.
- Input device availability.
- Battery and charging information.
- Lock-screen security.
- Storage mounting.
- Core Nuxel session.
- Necessary USB recovery access.
- Required audio initialization where part of the current boot contract.

Wi-Fi should not be required to finish displaying the lockscreen.

## 3.5 Preload startup assets intelligently

The following resources should be prepared before the UI needs them:

- Lockscreen background.
- Penguin lockhead.
- Bottom navigation images.
- Boot animation resources.
- Preloading video.
- Necessary fonts.
- Top-bar icons.

Inspect their actual sizes and load costs.

Requirements:

- Avoid decoding the same image repeatedly.
- Avoid repeated video probing.
- Cache decoded resources appropriately.
- Avoid filesystem scans during animation frames.
- Do not preload every application icon or every large asset into RAM.
- Release large startup-only buffers after use.

Do not create memory pressure on the S10+ to optimize boot.

## 3.6 No arbitrary sleeps

Remove unnecessary fixed waits from startup.

Do not replace a 10-second service wait with a different arbitrary 3-second wait.

Use:

- Real readiness events.
- D-Bus signals.
- Systemd dependency completion.
- File/socket readiness.
- Process state.
- Bounded retries with explicit conditions.

Use timing only when an actual hardware limitation requires it, and document why.

## 3.7 Boot speed acceptance

Measure a baseline and a new boot.

Record:

- Time to lockscreen.
- Time to usable touchscreen.
- Time to desktop.
- Time to Wi-Fi SSH availability.
- Time spent in the spinning penguin stage.

The main target is to reach an interactive, secure lockscreen as quickly as safely possible.

Do not claim a speed improvement based only on reducing animation duration.

---

# 4. P1 — FIX THE LONG BLACK SCREEN WHEN REBOOTING

## 4.1 Reported behavior

Selecting Reboot from the power menu still causes a long black screen before the phone actually starts rebooting.

This is separate from the boot-time spinning-penguin delay.

Investigate the full shutdown sequence.

## 4.2 Trace the reboot path

Inspect:

- Power menu UI handler.
- Reboot button callback.
- Confirmation dialog.
- Privilege escalation.
- D-Bus request.
- systemd-logind interaction.
- `systemctl reboot` invocation.
- Custom reboot wrappers.
- Shutdown hooks.
- Service stop ordering.
- Filesystem sync.
- Display-session termination.
- Compositor shutdown.
- Kernel reboot.

Capture monotonic timestamps for:

1. Reboot tapped.
2. UI acknowledges reboot.
3. Reboot request submitted.
4. systemd accepts request.
5. UI session terminates.
6. Shutdown begins.
7. Kernel reboot begins.

Determine the exact location of the long delay.

## 4.3 Improve UI behavior

When Reboot is selected:

- Give immediate visual acknowledgement.
- Show an appropriate rebooting screen or animation.
- Avoid an extended frozen or empty black screen.
- Do not leave the user wondering whether the button registered.
- Do not block the UI event loop.
- Issue the actual reboot request promptly.

Do not make the UI appear to reboot while the underlying reboot operation has not been requested.

## 4.4 Repair shutdown delays

Inspect systemd shutdown timing and relevant service hooks.

Look for:

- Services waiting for network shutdown.
- Audio cleanup waits.
- USB gadget shutdown waits.
- Application shutdown handlers.
- Deadlocked subprocesses.
- Excessive stop timeouts.
- Services waiting on a missing device.
- Blocking UI session termination.

Fix the specific source of delay.

Do not disable filesystem sync.

Do not skip safe unmounting.

Do not forcibly kill essential storage or system services to save a few seconds.

Do not remove important hardware cleanup.

The objective is a prompt, clean reboot.

---

# 5. P2 — FIX THE BLACK SCREEN AND WHITE FLASH BETWEEN PRELOADING VIDEO AND LOCKSCREEN

## 5.1 Reported behavior

The boot sequence currently behaves like:

```text id="qxz0cz"
SPINNING PENGUIN
       |
       v
PRELOADING VIDEO
       |
       v
BLACK SCREEN
       |
       v
FLASHING WHITE
       |
       v
LOCKSCREEN
```

Previously, the transition did not have this black/white flash.

The objective is a clean, uninterrupted transition.

## 5.2 Inspect actual video implementation

Identify the actual preloading-video asset.

Possible filenames may include:

- `./assets/nuxel-preloading-screen.mp4`
- `./assets/boot-preloading-screen.mp4`

Do not assume either exists.

Locate the deployed video and the actual player.

Inspect:

- Codec.
- Resolution.
- Frame rate.
- Pixel format.
- Duration.
- Audio track.
- Decoder.
- Hardware acceleration.
- Rendering surface.
- Display backend.
- Player exit callback.
- Video surface destruction.
- Lock-screen process initialization.

Determine whether the black/white flash is caused by:

- Player process termination.
- Surface destruction.
- Framebuffer reset.
- Display-mode switch.
- Compositor startup.
- Incorrect alpha/opacity state.
- Lock-screen background loading.
- A white WebView/body default background.
- Video element teardown.
- Window recreation.
- GPU/rendering initialization.
- A temporary panel backlight/power state transition.

Do not simply add a fade animation over an actual display reset.

Fix the source of the transition.

## 5.3 Seamless handoff

Requirements:

1. Preload the lockscreen background before the video ends.
2. Prepare the lockscreen UI while the video plays, where safe.
3. Keep a valid rendered frame visible during handoff.
4. Avoid destroying the display surface prematurely.
5. Avoid changing resolution unnecessarily.
6. Avoid toggling display output or backlight.
7. Avoid setting the WebView background to white.
8. Ensure the first lockscreen frame is ready before hiding the video.
9. Avoid waiting several seconds after the video completes.
10. Preserve lockscreen security and input behavior.

Use a controlled transition:

- Video finishes.
- Lockscreen is ready.
- Video layer is removed or hidden.
- Lockscreen becomes visible.
- Input becomes active.

The system should never expose an empty white WebView frame.

If the current architecture requires a separate process, implement an explicit handoff rather than a blind process termination.

## 5.4 Preserve the boot artwork

Do not redesign the boot animation or preloading video unless a technical format issue requires it.

Preserve the Nuxel artwork.

The task is performance and transition quality.

---

# 6. P3 — REMOVE UNWANTED LPM / CHARGING TOUCHSCREEN RESTRICTION

## 6.1 Reported behavior

When a USB-C charger is connected and the phone is powered on, Nuxel enters or exposes an unwanted LPM/charging-mode behavior.

This currently interferes with normal touchscreen operation.

The owner does not want a touchscreen-blocking charging mode.

The acceptable outcomes are:

1. Remove/deactivate the unwanted LPM charging mode; or
2. Retain any necessary power-management behavior but remove the notification and do not block touchscreen operation.

**The touchscreen must remain usable while the phone is powered on and connected to USB-C power.**

## 6.2 Find the actual responsible component

Search the repository and live system for:

- LPM.
- Low Power Mode.
- Charging mode.
- Charger connected.
- USB connected.
- Touchscreen disable.
- Touch suspend.
- `power_supply`.
- `input`.
- `evdev`.
- `suspend`.
- `panel/bl_power`.
- Charging notification.
- Screen lock triggered by charger state.

Inspect:

- Services.
- Systemd units.
- Timers.
- Udev rules.
- Input-device management.
- Touchscreen driver interfaces.
- Power-mode scripts.
- Notification handlers.
- Lockscreen state machine.
- USB connection handlers.

Determine exactly which component disables touch or blocks interaction.

Do not assume it is only a notification.

## 6.3 Required behavior

While the phone is powered on:

- Charger connected: touchscreen works.
- USB data cable connected: touchscreen works.
- Screen unlocked: touchscreen works.
- Screen locked: normal lockscreen touch gestures work.
- Charging status: accurately displayed.
- Normal thermal protections remain active.

Do not disable the touchscreen merely because external power is present.

## 6.4 If LPM must remain

If a lower-level charging mode is genuinely needed for safe battery management:

- Keep its required thermal/battery behavior.
- Remove the unwanted user-visible LPM notification if it is misleading.
- Ensure the powered-on normal Nuxel session can use the touchscreen.
- Do not disable all input to save power.
- Do not make the touchscreen unusable while connected to USB-C.

If actual hardware/firmware LPM is engaged only when the main OS is not running, do not conflate that with a normal powered-on Nuxel session.

## 6.5 Do not break input power safety

Avoid directly writing to input-driver sysfs attributes or disabling kernel input devices unless the actual driver documentation confirms the behavior.

Preserve touchscreen functionality after suspend/resume.

Test both normal charging and data-transfer cable connections.

---

# 7. P4 — IMPROVE QUICK SETTINGS OPEN/CLOSE PERFORMANCE

## 7.1 Reported behavior

Quick Settings is functional but still feels slow when opening and closing.

Other applications and settings screens are generally much faster.

Investigate Quick Settings specifically.

## 7.2 Profile the panel

Inspect:

- Quick Settings component initialization.
- Panel creation.
- Open/close callbacks.
- Animation.
- DOM/component tree size.
- CSS effects.
- Blur.
- Transparency.
- Shadow.
- Icon loading.
- Status queries.
- Event listeners.
- Battery/network/Bluetooth state refresh.
- Layout recalculation.
- Repeated DOM updates.
- Main-thread blocking.
- Duplicate timers.
- Excessive polling.

Measure:

- Tap-to-visible latency.
- Full animation duration.
- Tap-to-interactive latency.
- Close latency.
- CPU/rendering activity.
- Number of backend requests.
- Number of DOM/state updates.

## 7.3 Avoid unnecessary initialization on every opening

Quick Settings should not rebuild everything each time.

Cache stable UI elements and assets.

Refresh dynamic status using appropriate state subscriptions.

On opening:

- Use the most recent valid state.
- Refresh only the fields that may have changed.
- Avoid making the panel wait for several slow services.
- Never block panel opening on GPS, Flatpak, modem or other unrelated state.
- Update fields asynchronously.
- Prevent stale asynchronous responses from overwriting newer state.

## 7.4 Optimize the panel transition

Preserve Nuxel's current visual design.

Optimize expensive:

- Backdrop blur.
- Large box shadows.
- Transparent overlapping layers.
- Image scaling.
- Repeated transforms.
- Forced synchronous layout.
- Continuous animation loops.

Avoid introducing unnecessary transparency or glow.

Where possible, use a lightweight transform-based panel transition.

The panel should become interactive immediately, not after the animation fully completes.

Do not remove working settings to save rendering cost.

## 7.5 Keep state updates efficient

- Reuse the existing status service.
- Do not create duplicate polling loops.
- Debounce unnecessary UI updates.
- Subscribe to backend state changes.
- Remove listeners when the panel is destroyed, if it is dynamically created.
- Avoid excessive network or D-Bus requests.

Quick Settings should feel immediate.

---

# 8. P5 — FIX HOME SETTINGS PERFORMANCE

## 8.1 Reported behavior

Home Settings is sluggish while most other Nuxel applications and Settings screens are fast.

This suggests a local bottleneck rather than a general hardware limitation.

Inspect the Home Settings application independently.

## 8.2 Profile the actual causes

Investigate:

- Initial rendering.
- Large image assets.
- Wallpaper thumbnails.
- Icon rendering.
- Background previews.
- Repeated settings reads.
- Filesystem scans.
- Asset decoding.
- CSS blur/shadow.
- Large forms.
- Excessive event listeners.
- Whole-page re-rendering.
- Synchronous file access.
- Saving settings on every input event.
- Repeated background requests.

Capture:

- Initial load time.
- First interactive time.
- Tab switching time.
- Opening and closing dropdowns.
- Wallpaper/background preview latency.
- Settings save latency.

Compare its behavior with the already-fast Settings screens.

## 8.3 Optimize Home Settings

Potential improvements:

- Cache decoded image assets.
- Use small cached thumbnails.
- Load full-resolution background previews only when requested.
- Defer non-visible settings tabs.
- Avoid reinitializing every settings control.
- Avoid repeated filesystem enumeration.
- Batch settings reads.
- Debounce settings writes.
- Use event-based updates.
- Reduce expensive CSS effects.
- Avoid rebuilding the whole interface after a single option changes.

Preserve existing settings and functionality.

Do not delete settings because they are expensive to render.

## 8.4 Verify behavior

Home Settings must:

- Open quickly.
- Respond immediately to input.
- Switch tabs smoothly.
- Update previews without freezing.
- Save settings reliably.
- Preserve choices after reboot.

---

# 9. P6 — HOME BUTTON MUST CLOSE THE KEYBOARD

## 9.1 Reported behavior

When the keyboard is open and the user presses the Penguin Home button, the keyboard remains visible or interferes with the transition.

The Home button should close the active keyboard as part of the navigation action.

## 9.2 Inspect current navigation and keyboard architecture

Identify:

- The Penguin Home button handler.
- Bottom navigation implementation.
- Active application state.
- Virtual keyboard/input-method process.
- Focused control.
- WebView focus.
- Keyboard visibility events.
- Navigation/minimize behavior.

Do not assume that the keyboard is always an external process.

It could be a native virtual keyboard, a WebView keyboard overlay, or a separate Nuxel application.

Determine which one is active.

## 9.3 Required Home behavior

When Penguin Home is pressed:

1. Detect whether a keyboard is visible.
2. Immediately request keyboard dismissal through the actual input-method API.
3. Clear or transfer focus appropriately.
4. Prevent the keyboard from remaining above the Home desktop.
5. Continue the normal Home action.
6. Return the app to the correct background/minimized state.
7. Restore the appropriate desktop focus.
8. Ensure the next application receives keyboard input correctly when needed.

The user should not need to press Back a second time just to remove the keyboard.

## 9.4 No fake visual hiding

Do not merely hide the keyboard with CSS while leaving the input method active.

Do not leave invisible keyboard windows intercepting touch events.

Do not destroy text input state unnecessarily.

Do not clear the content being typed.

Do not break the Back button's separate keyboard-dismissal behavior.

Test with:

- Notes Title field.
- Text field in Home Settings.
- Search field.
- Another open application.
- Multiple focus transitions.

---

# 10. P7 — OPTIMIZE LOCKSCREEN PERFORMANCE

## 10.1 Reported behavior

Lockscreen interaction is still noticeably sluggish.

The screen should be responsive immediately when the display wakes.

## 10.2 Profile the lockscreen

Inspect:

- Lock-screen process start time.
- Background image loading.
- Penguin lockhead loading.
- Gesture handlers.
- Drag interaction.
- Animations.
- Clock updates.
- Status-bar updates.
- Battery polling.
- Wi-Fi status updates.
- Time/date formatting.
- Lock/unlock event handlers.
- Input focus.
- Display wake transition.
- Asset decoding.
- WebView startup.
- Background service calls.

The lockscreen is security-critical.

Do not weaken or bypass authentication.

## 10.3 Optimize lockscreen rendering

Requirements:

- Preload its background and lockhead assets.
- Cache decoded resources.
- Avoid decoding the same PNG/JPEG each time the screen wakes.
- Avoid a large synchronous startup task.
- Update clock/date efficiently.
- Do not poll battery and network excessively.
- Do not initialize every application while the phone is locked.
- Use efficient animation scheduling.
- Avoid expensive blur/transparency effects.
- Avoid continuous background rendering when nothing changes.

Keep the established Nuxel lockscreen visual identity.

Keep the lockhead animation.

Do not remove the penguin personality to gain performance.

## 10.4 Wake responsiveness

When the display wakes:

- Show the lockscreen quickly.
- Accept touch input immediately when hardware is ready.
- Avoid a black delay.
- Avoid a white intermediate frame.
- Avoid losing the first drag/tap.
- Preserve lockscreen security.

Test repeated screen off/on cycles.

---

# 11. P8 — INSTALL AND INTEGRATE NATIVE LINUX APPLICATIONS

The user wants a small but useful selection of native Linux apps, alongside the requested Flatpak applications.

First inspect the actual package-management setup.

Determine:

- Fedora version.
- ARM64/aarch64 architecture.
- Enabled RPM repositories.
- Available storage.
- Existing graphical libraries.
- Current Nuxel application-launcher integration.
- Existing installed applications.
- Flatpak installation mode.

Do not install an entire desktop environment just to obtain a few applications.

## 11.1 Select lightweight native applications

Install a small, sensible selection of useful native Linux applications compatible with the S10+ ARM64 environment.

Examples to investigate:

- A lightweight archive manager.
- A lightweight image viewer.
- A terminal application with a mobile-friendly interface, if not already available.
- A small system information/monitoring application.
- A lightweight document/PDF viewer.

These are candidates, not mandatory package names.

Inspect actual availability, dependencies and UI suitability before installing.

Prefer applications with:

- ARM64 packages.
- Reasonable memory use.
- Functional keyboard/touch interaction.
- Desktop files.
- Icons.
- No dependency on a complete GNOME/KDE desktop stack.

Do not install duplicate tools that Nuxel already provides.

## 11.2 Native app integration

For every installed application:

- Verify RPM installation.
- Verify actual executable.
- Verify desktop entry.
- Verify icon.
- Verify application launches.
- Add to the Nuxel launcher.
- Correct any unsuitable desktop category/name where appropriate.
- Test on the phone's portrait display.

Do not create fake shortcuts to absent executables.

Do not report successful installation without checking that the program starts.

---

# 12. P9 — INSTALL FLATPAK APPLICATIONS

The requested applications are:

1. Mozilla Firefox.
2. VLC media player.
3. Signal.
4. Stremio.

## 12.1 Audit Flatpak first

Inspect:

- Flatpak installation.
- Flathub remote.
- Remote URL.
- Remote trust configuration.
- Installed runtimes.
- Available ARM64 builds.
- Disk space.
- Existing applications.
- User versus system installation.

Do not add duplicate remotes.

Do not remove existing applications.

Do not install x86_64 binaries on ARM64.

Do not assume all four applications have official native ARM64 Flatpak packages.

## 12.2 Firefox

Candidate application ID:

`org.mozilla.firefox`

Verify:

- The ID exists in the configured remote.
- An ARM64 build exists.
- Required runtime is available.
- Application is compatible with Nuxel's display environment.
- Sandbox permissions are appropriate.

Install through Flatpak.

Verify that Firefox:

- Appears in the launcher.
- Displays the correct icon.
- Opens a usable window.
- Accepts touch interaction.
- Accesses the network.
- Survives reboot.

## 12.3 VLC

Candidate application ID:

`org.videolan.VLC`

Verify compatible ARM64 availability and runtime.

Install through Flatpak.

Verify:

- Application launches.
- Media file selection works.
- Video playback works.
- Basic audio playback works where the route is currently available.
- App appears in the launcher.
- Application survives reboot.

Do not claim Nuxel audio is fixed just because VLC opens.

## 12.4 Signal

Investigate the actual available Signal distribution.

Candidate Flatpak ID to verify:

`org.signal.Signal`

Important:

- Confirm whether the current Flatpak is official, verified, community-maintained or an independent packaging project.
- Check package origin and publisher.
- Check ARM64 availability.
- Check the current upstream-supported Linux distribution/runtime requirements.
- Inspect permissions and network sandbox access.

Do not silently install an unofficial repackaged client while calling it the official Signal package.

If an ARM64 Flatpak package is unavailable or not trustworthy, investigate a compatible native ARM64 installation route.

Do not install a fake icon or web shortcut and call it the Signal desktop application.

## 12.5 Stremio

Candidate Flatpak ID to verify:

`com.stremio.Stremio`

Verify:

- Current remote identity.
- Package provenance.
- ARM64 availability.
- Runtime.
- Required multimedia dependencies.
- Video hardware acceleration behavior.
- Network permissions.
- UI compatibility.

Install only if a compatible genuine build is available.

If the application is unavailable on ARM64, report it as BLOCKED and identify the actual limitation.

Do not install an x86_64 package or unsupported binary.

## 12.6 Installation and launcher verification

For each app:

1. Resolve the actual Flatpak reference.
2. Check architecture.
3. Inspect runtime dependencies.
4. Install.
5. Verify with `flatpak info`.
6. Verify desktop entry.
7. Verify icon.
8. Verify launcher discovery.
9. Launch the application.
10. Confirm an actual usable UI.
11. Reboot and verify persistence.

Do not mark an app installed simply because Flatpak created a database record.

## 12.7 Flatpak integration and resources

Use the existing Nuxel application discovery system.

Ensure that:

- Flatpak user exports are scanned.
- System exports are scanned.
- Application ID is handled correctly.
- Icon paths resolve.
- Duplicates are avoided.
- Application inventory is cached.
- Changes refresh the launcher.
- Application launch commands use `flatpak run` where appropriate.

Do not re-scan every Flatpak remote every time the application drawer opens.

Do not run Flatpak inventory scans continuously.

Use a cached inventory refreshed after actual install/uninstall events.

Avoid exhausting the phone's limited RAM with several large applications simultaneously.

---

# 13. P10 — LOCKSCREEN USB CONNECTION MODE

This is a major functional deliverable.

The lockscreen needs a visible control that allows the user to choose between normal charging and file transfer.

## 13.1 Required assets

Use the exact repository assets:

`./assets/nuxel-connection-mode.png`

`./assets/nuxel-file-transfer.png`

Locate and verify both assets.

Do not substitute random icons.

Do not stretch or crop them.

Preserve aspect ratio and transparency.

## 13.2 Connection-mode button

Add the connection-mode icon to the bottom-right corner of the lockscreen.

Requirements:

- Always visible when the device is in the appropriate USB-connected/usable state.
- Properly positioned.
- Not hidden behind the lockscreen background.
- Not clipped.
- Has a suitable touch target.
- Preserves existing lockhead gesture interactions.
- Works without requiring the user to unlock the main desktop.

The icon must remain consistent across portrait resolution and lockscreen scaling.

## 13.3 Popup

Pressing the button opens a compact popup with:

- Charging Mode.
- File Transfer Mode.
- Cancel/close.

Use the Nuxel visual style.

Each option must have a real action.

Do not simply change the selected mode label.

## 13.4 Charging Mode

Charging Mode should:

- Allow normal charging.
- Avoid exposing storage.
- Preserve the existing USB console/recovery path where configured.
- Keep touchscreen operation available.
- Maintain actual charging state reporting.

Do not disable touch.

Do not change USB role unnecessarily.

## 13.5 File Transfer Mode

When File Transfer Mode is selected:

1. Verify a physical USB-C data connection exists.
2. Configure a real supported USB gadget/file-transfer function.
3. Expose the intended Nuxel user-storage area.
4. Make the device visible from the connected computer.
5. Allow the computer to browse folders.
6. Allow files to be copied to the phone.
7. Allow files to be copied from the phone.
8. Reflect actual transfer state in Nuxel.
9. Show the file-transfer icon on the lockscreen.
10. Maintain the icon while file transfer mode is genuinely active.

The owner expects to connect the phone to a computer and see it appear as an accessible phone/storage device.

Do not settle for a status label saying File Transfer when the computer cannot detect anything.

## 13.6 Exact lockscreen indicator

Display:

`./assets/nuxel-file-transfer.png`

while genuine file-transfer mode is active.

The indicator should:

- Appear only after the USB file-transfer function is actually configured and active.
- Disappear when the mode is disabled.
- Disappear after disconnect.
- Reflect host eject/disconnect where supported.
- Never remain visible after the gadget has stopped.
- Update when switching back to Charging Mode.

Do not base the icon solely on a frontend boolean.

Use actual gadget/transfer daemon state.

---

# 14. USB FILE TRANSFER SAFETY

This section is mandatory.

Do not expose the actively mounted writable root filesystem as USB Mass Storage.

That can corrupt the filesystem.

Inspect:

- USB UDC availability.
- USB gadget configuration.
- ConfigFS support.
- Available gadget functions.
- Existing USB serial/console configuration.
- Existing charging behavior.
- Current USB role.
- Storage layout.
- Mounted filesystems.
- USB gadget permissions.
- File-transfer daemon availability.
- Current kernel support.

## 14.1 Preferred protocol

Prefer MTP where supported.

MTP permits controlled file access without exporting the same mounted filesystem as a raw writable block device.

Implement a suitable Linux USB gadget/FunctionFS MTP arrangement only after verifying that the kernel and userspace support it.

If MTP is not available, investigate other safe approaches based on the existing kernel and USB gadget support.

Do not pretend that MTP is a raw mounted disk.

## 14.2 USB Mass Storage restriction

Raw USB Mass Storage is only permitted if there is an independently exportable storage target that Nuxel is not simultaneously mounting or modifying.

No repartitioning is authorized.

Do not expose:

- Root filesystem.
- Active `/home` filesystem.
- Active `/var`.
- Any writable mounted filesystem.

If a suitable dedicated exportable target does not already exist, do not implement raw UMS.

Use MTP or another safe protocol.

## 14.3 Computer compatibility

Test with an actual host computer.

Where possible, verify compatibility with:

- Linux.
- Windows.
- macOS.

The PC must genuinely identify the Nuxel phone/file-transfer device.

Test:

- Browse folders.
- Copy a file from PC to phone.
- Copy a file from phone to PC.
- Open the copied file on Nuxel.
- Verify checksums for test files.
- Handle filenames with spaces and Unicode.
- Handle a reasonably sized file.
- Disconnect without corruption.

Do not mark file transfer complete based solely on successful USB gadget configuration.

## 14.4 Preserve console/recovery access

The current USB functions may include debugging and console access.

Inspect how they coexist with file transfer.

Do not blindly overwrite the complete USB gadget configuration.

If functions are mutually exclusive:

- Implement an explicit reversible transition.
- Preserve Wi-Fi SSH as the active management channel.
- Preserve a recovery path.
- Restore the original USB configuration when leaving File Transfer Mode.

Do not leave the phone trapped in a broken USB mode.

---

# 15. USB MODE STATE MACHINE

Implement a real state machine.

Suggested model:

```text id="kfxh47"
NO USB DATA CONNECTION
          |
          v
   CHARGING / NORMAL
          |
          | User presses connection-mode button
          v
       MODE POPUP
          |
          +-------- CHARGING MODE
          |              |
          |              v
          |      CHARGING FUNCTION ACTIVE
          |              |
          |              v
          |      NO TRANSFER INDICATOR
          |
          +-------- FILE TRANSFER MODE
                         |
                         v
                 CHECK USB DATA LINK
                         |
                         v
                 CONFIGURE GADGET
                         |
                         v
                  START MTP SERVICE
                         |
                         v
                  VERIFY ACTIVE DEVICE
                         |
                         v
                  VERIFY SESSION READY
                         |
                         v
              DISPLAY TRANSFER INDICATOR
                         |
                         v
               PC BROWSES PHONE STORAGE
                         |
              +----------+----------+
              |                     |
              v                     v
          HOST EJECT           USER SWITCHES
              |                     |
              +----------+----------+
                         |
                         v
                STOP / RELEASE SESSION
                         |
                         v
                RESTORE USB CONFIG
                         |
                         v
                   CHARGING MODE
```

Use explicit states such as:

- `disconnected`
- `charging`
- `selecting`
- `transfer_preparing`
- `transfer_active`
- `transfer_error`
- `transfer_stopping`

The UI must derive its state from the real backend.

Do not display `transfer_active` until the real gadget and transfer endpoint are ready.

---

# 16. LOCKSCREEN CONNECTION-MODE IMPLEMENTATION

Inspect existing lockscreen layers and touch input.

Do not build an unrelated second lockscreen.

Requirements:

- Reuse the existing lockscreen state machine.
- Reuse the existing asset-loading conventions.
- Add the connection-mode button as an independent layer.
- Give it an appropriate touch target.
- Prevent taps from triggering the lockhead drag gesture.
- Prevent underlying widgets from stealing its touch events.
- Keep the popup visually stable.
- Handle outside tap/cancel.
- Provide accessible labels.
- Ensure the icon does not interfere with the bottom three navigation buttons when unlocked.
- Ensure no connection-mode popup appears unexpectedly during ordinary charging.

The popup is available from the lockscreen as requested.

The actual USB configuration must be handled through a backend service, not directly from JavaScript.

Use authenticated IPC with defined commands.

Do not allow arbitrary USB gadget writes from the WebView.

---

# 17. GENERAL PERFORMANCE RULES

The S10+ has constrained resources.

Optimize the actual bottlenecks.

Do not use brute force by loading every asset, application, service and model simultaneously.

## 17.1 UI rendering

- Cache images.
- Cache decoded assets.
- Avoid duplicate image decoding.
- Avoid repeatedly rebuilding entire UI trees.
- Reduce unnecessary CSS compositing.
- Avoid heavy blur.
- Avoid continuous animations when off-screen.
- Avoid large transparent layers.
- Use event-driven updates.
- Debounce input where appropriate.
- Keep touch handlers lightweight.
- Keep expensive work out of the UI thread.

## 17.2 Memory

Measure:

- RSS.
- Peak memory.
- Swap activity.
- OOM events.
- Browser/WebView memory.
- Flatpak runtime overhead.
- UI asset cache use.

Do not optimize responsiveness by causing memory pressure.

Keep caches bounded.

Release resources when applications are closed.

## 17.3 Performance measurements

For each target screen, record:

- Cold launch time.
- Warm launch time.
- Time to first visible content.
- Time to interactive.
- Input-to-response latency.
- CPU usage during transitions.
- Memory usage.
- Any blocking subprocesses.
- Number of backend requests.

Compare before and after.

---

# 18. REQUIRED TEST MATRIX

All applicable tests must be recorded as PASS / FAIL / BLOCKED / NOT TESTED.

| ID | Test | Required result |
|---|---|---|
| BOOT-01 | Spinning penguin stage | Shorter measured duration |
| BOOT-02 | Lock screen readiness | Fast and secure |
| BOOT-03 | Touch readiness | Available immediately when ready |
| BOOT-04 | Boot asset loading | No repeated decoding |
| REBOOT-01 | Reboot tap acknowledgement | Immediate |
| REBOOT-02 | Shutdown start | No unexplained black delay |
| REBOOT-03 | System reboot | Safe and successful |
| VIDEO-01 | Preloading MP4 | Plays correctly |
| VIDEO-02 | Video-to-lockscreen | No black/white flash |
| VIDEO-03 | First lockscreen frame | Ready before video removal |
| LPM-01 | Charger connected | Touch works |
| LPM-02 | USB-C data cable | Touch works |
| LPM-03 | LPM notification | Removed if unwanted |
| QS-01 | Quick Settings open | Faster measured response |
| QS-02 | Quick Settings close | Faster measured response |
| QS-03 | State refresh | No blocking waits |
| HOME-SET-01 | Home Settings cold launch | Improved |
| HOME-SET-02 | Home Settings warm launch | Responsive |
| HOME-SET-03 | Settings saves | Correct and persistent |
| NAV-01 | Home button with keyboard open | Keyboard dismissed |
| NAV-02 | Home navigation | Correct minimize/home action |
| LOCK-01 | Lockscreen launch | Faster |
| LOCK-02 | Lockscreen touch | Responsive |
| LOCK-03 | Repeated screen wake | No sluggish accumulation |
| APP-01 | Firefox | Installed and launchable |
| APP-02 | VLC | Installed and launchable |
| APP-03 | Signal | Compatible genuine build installed or honestly blocked |
| APP-04 | Stremio | Compatible build installed or honestly blocked |
| APP-05 | Native apps | Installed and launchable |
| APP-06 | Launcher integration | Correct icons and entries |
| APP-07 | Reboot persistence | Applications remain installed |
| USB-01 | Connection-mode icon | Visible bottom-right |
| USB-02 | Mode popup | Charging/File Transfer options |
| USB-03 | Charging mode | Actual charging configuration |
| USB-04 | File-transfer setup | Real gadget starts |
| USB-05 | PC detection | Host identifies the device |
| USB-06 | PC-to-phone copy | File received |
| USB-07 | Phone-to-PC copy | File received |
| USB-08 | File checksums | Match |
| USB-09 | Transfer indicator | Only shown when active |
| USB-10 | Host eject | Correct cleanup |
| USB-11 | Return to charging | Works |
| USB-12 | USB console recovery | Preserved/recoverable |
| FINAL-01 | Final reboot | Successful |
| FINAL-02 | All major UI functions | Working |
| FINAL-03 | USB modes | Verified again |

---

# 19. DEPLOYMENT SAFETY

Before deployment:

1. Record the Git state.
2. Preserve uncommitted work.
3. Back up affected files and configurations.
4. Review every changed file.
5. Run unit tests.
6. Run UI checks.
7. Validate systemd units.
8. Validate USB configuration.
9. Verify application package sources and architecture.
10. Deploy only the necessary files.
11. Verify installed hashes.
12. Preserve Wi-Fi SSH.
13. Keep rollback commands and backups.

Do not:

- Flash firmware.
- Replace the kernel.
- Modify bootloader settings.
- Repartition storage.
- Format user data.
- Replace an entire USB gadget configuration without understanding it.
- Export active writable filesystems.
- Disable thermal protections.
- Disable touchscreen input while charging.
- Remove important boot/recovery services.

If a hardware or kernel limitation blocks a feature, document it precisely instead of faking success.

---

# 20. FINAL REBOOT

After implementation and regression tests:

1. Check the TODO.
2. Verify all modified files.
3. Confirm app installations.
4. Confirm the charging/touchscreen fix.
5. Confirm lockscreen and UI performance.
6. Confirm boot-transition fixes.
7. Confirm USB gadget configuration.
8. Confirm MTP or chosen transfer service.
9. Back up final settings.
10. Initiate normal reboot.
11. Allow Wi-Fi SSH to disconnect.
12. Reconnect through the existing WLAN management route.
13. Verify the phone booted successfully.
14. Observe the spinning penguin stage.
15. Observe the preloading video.
16. Observe the transition into lockscreen.
17. Verify there is no black/white flash.
18. Verify lockscreen touch.
19. Verify Quick Settings.
20. Verify Home Settings.
21. Verify Home button keyboard dismissal.
22. Verify installed applications persist.
23. Verify touchscreen while connected to USB-C.
24. Verify File Transfer Mode with an actual connected PC.
25. Verify a file copy in both directions.

Do not claim completion until this final reboot and test have been performed.

---

# 21. EVIDENCE AND REPORTS

Create:

`docs/beta-finalization/live/PWNAGE-43000-TODO.md`

Create:

`docs/beta-finalization/live/PWNAGE-43000-REPORT.md`

Store evidence under:

`docs/beta-finalization/live/evidence/pwnage-43000/`

Include:

- Initial system inventory.
- Boot baseline.
- Boot critical chain.
- Per-stage boot timings.
- Reboot delay trace.
- Preloading video/player diagnostics.
- Video-to-lockscreen transition evidence.
- Charging/LPM/input diagnostics.
- Quick Settings timing results.
- Home Settings timing results.
- Lockscreen timing results.
- Keyboard dismissal tests.
- Installed application references and versions.
- ARM64 compatibility results.
- Launcher integration.
- USB gadget configuration.
- PC device-detection evidence.
- File-transfer logs.
- File checksum comparisons.
- Final reboot verification.

Do not log user credentials or file contents.

---

# 22. FINAL REPORT FORMAT

## Boot performance

- Original boot time.
- New boot time.
- Spinning penguin time.
- Main bottleneck.
- Changes made.

## Reboot

- Original black-screen delay.
- New delay.
- Exact root cause and repair.

## Video-to-lockscreen

- Original transition defect.
- Fix.
- Final physical result.

## Touchscreen/LPM

- Actual cause.
- Service or script changed.
- Charging and data-cable results.

## UI performance

- Quick Settings before/after.
- Home Settings before/after.
- Lockscreen before/after.
- Keyboard dismissal results.

## Applications

For every requested app:

- Package source.
- App ID/package name.
- Architecture.
- Installed version.
- Launcher entry.
- Launch test.
- Limitations.

## USB File Transfer

- Actual protocol.
- Gadget mode.
- Host detection.
- PC-to-phone test.
- Phone-to-PC test.
- Eject behavior.
- Charging-mode restoration.

## Final reboot

- Successful or unsuccessful.
- Wi-Fi SSH reconnected.
- Final user-visible verification.

## Remaining blockers

List every unresolved hardware or software limitation.

---

# FINAL NON-NEGOTIABLE EXECUTION RULES

1. Diagnose before optimizing.
2. Measure boot time before and after.
3. Do not conceal slow boot by shortening the animation only.
4. Fix the actual reboot delay.
5. Eliminate the black/white preloading-video handoff flash.
6. Do not block touchscreen operation while powered on and connected to USB-C.
7. Optimize Quick Settings independently.
8. Optimize Home Settings independently.
9. Optimize lockscreen independently.
10. Home button must dismiss the keyboard.
11. Install only compatible, verified ARM64 packages.
12. Integrate all applications into the real Nuxel launcher.
13. Implement actual lockscreen Charging/File Transfer controls.
14. Prefer safe MTP-style transfer.
15. Never export a mounted writable filesystem as raw USB Mass Storage.
16. Preserve existing USB console/recovery.
17. Keep user data and existing work intact.
18. Reboot at the end.
19. Test the complete system after reboot.
20. Provide evidence instead of assumptions.

**The goal is a phone that boots quickly, transitions cleanly, responds instantly, works while charging, runs real Linux applications, and can genuinely transfer files to a computer.**

# PWNAGE-43000 — MAKE NUXEL FEEL LIKE A FINISHED PHONE. 🐧
