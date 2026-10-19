# QONQRETE — OPERATION TOUCHDOWN
## Nuxel Galaxy S10+ · Emergency Input and Interaction Finalization
### Autonomous Engineering Mission · Fedora Development Host · Live USB Console
### REAL TOUCHSCREEN FIRST · USB HID SECOND · POWER-BUTTON CORRECTIONS · NO FLASHING

**NUXEL OPERATION TOUCHDOWN — CRITICAL NEW DIAGNOSTIC DIRECTION**

New observation: the system reportedly recognizes hardware input, but physical tapping does not activate launcher applications, the top notification bar cannot be pulled down, and UI updates sometimes appear only after Power-button activity.

**DO NOT ASSUME THIS IS STILL A TOUCHSCREEN HARDWARE DRIVER FAILURE.**

First distinguish actual touchscreen contact events from Power/Volume/Bixby hardware-key events.

If real physical finger contacts produce `ABS_MT_POSITION_X/Y`, tracking IDs and `SYN_REPORT`, treat the kernel/evdev layer as provisionally functional and IMMEDIATELY investigate the GUI pipeline.

Prioritize:

1. Confirm a real finger produces raw touchscreen events.
2. Confirm libinput receives those same contacts.
3. Trace whether Phoc receives and forwards Wayland touch events.
4. Determine whether the active WebKitGTK surface receives touchstart/pointerdown/click events.
5. Check for invisible fullscreen splash overlays, stale WebKit windows or incorrect focus.
6. Verify touchscreen coordinate mapping against the current Wayland output.
7. Instrument a launcher icon's actual event handler and determine whether it executes.
8. If app actions execute without visible updates, investigate blocked GUI loops, missing Wayland frame callbacks, screencopy stalls and stale framebuffer presentation.
9. Investigate why volume overlays and launcher startup appear to redraw only after Power-button events.
10. Verify the notification pull-down gesture is actually implemented and wired; don't mistake a missing gesture handler for a driver failure.

**Use the existing launcher. Do not redesign or recreate it.**

Add timestamped diagnostic markers at every stage and correlate ONE physical tap from evdev all the way to the application action and framebuffer update.

Use a temporary visual input-debug indicator only if it can be added to the existing UI without interfering with input.

Do not declare touchscreen success because interrupts fire. Do not declare GUI success because synthetic events pass.

**TARGET: One physical tap → WebKit receives it → correct app handler executes → visible app opens immediately, without pressing Power to force a redraw.**

Keep the live console working. No flashing. Fix the first failing layer and continue end-to-end until owner verification or a precisely proven blocker.

I just pressed touch screen and you recognized it so that means the touch screen works but the whole GUI is frozen/not working as I cannot click anything nothing happens.

# 0. ABSOLUTE DIRECTIVE

You are QonQrete, operating as an autonomous embedded Linux input engineer, Samsung Exynos kernel specialist, Linux compositor engineer, WebKitGTK developer, hardware-debugging engineer and regression-test engineer.

Your only major engineering objective is:

**MAKE THE PHYSICAL SAMSUNG GALAXY S10+ TOUCHSCREEN WORK IN NUXEL.**

The user has already spent many development cycles receiving reports that the touchscreen should work.

IT STILL DOES NOT WORK.

Previous claims based on driver registration, interrupt activity, libinput discovery or compilation are no longer sufficient.

Do not declare success until the entire input pipeline is proven.

Your immediate additional objectives are:

1. Establish a working external USB keyboard/mouse input path where the existing kernel supports it.
2. Fix Power-button handling that interferes with input and display state.
3. Fix startup/display refresh problems that prevent interaction.
4. Implement a usable long-press Power menu for normal reboot and shutdown.

These are tightly scoped supporting tasks.

Do not spend time on unrelated features.

Do not rewrite the launcher.

Do not redesign the interface.

Do not implement applications unrelated to input.

Do not work on the modem, Wi-Fi, app store, camera, GPS, audio codecs or other beta features.

**TOUCHSCREEN FUNCTIONALITY IS THE TOP PRIORITY UNTIL PROVEN ON PHYSICAL HARDWARE.**

---

# 1. CURRENT HARDWARE AND ENVIRONMENT

Device:

- Samsung Galaxy S10+.
- SM-G975F.
- Codename beyond2lte.
- Exynos 9820.
- ARM64.
- Samsung downstream Linux 4.14.253.
- Fedora 43.
- Samsung DECON framebuffer.
- Existing Nuxel graphical interface.
- Existing Phoc/WebKitGTK integration work.
- Working USB CDC-ACM live console.

Development machine:

- Fedora Linux laptop.
- QonQrete is running on the Fedora laptop.
- Samsung phone is physically connected over USB.
- UTM reference VM is not available.

Project:

`~/x/nuxel`

Important areas:

`tools/s10plus/`

`tools/s10plus/a29/`

`tools/s10plus/a30/`

`tools/s10plus/a31/`

`tools/s10plus/a32/`

`pwa/nuxel-home/`

`pwa/nuxel-common/`

`services/`

`configs/s10plus/`

`docs/s10plus-autonomous-boot-repair/`

Live console tools:

`scripts/s10plus-debug-pack/nuxel-live.sh`

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

Discover current actual paths and binaries before making changes.

Do not assume historic source versions match the running phone.

---

# 2. LATEST PHYSICAL OBSERVATIONS — USER-REPORTED FACTS

The user has now observed:

## Touchscreen

- Physical finger taps do not control Nuxel.
- Physical swipes do not navigate Nuxel.
- Applications cannot be manually opened through touch.
- The touchscreen has repeatedly been described as working in agent reports despite being unusable.

## USB keyboard

- A Keychron keyboard connected directly through USB-C has not operated Nuxel.
- Determine whether the keyboard is in wired mode.
- Determine whether the phone switches from USB device mode to host mode.
- Determine whether the keyboard enumerates.
- Determine whether USB HID events reach Nuxel.

## USB mouse

- A standard mouse connected through a USB-A-to-USB-C adapter has not operated Nuxel.
- The adapter's exact role negotiation has not been verified.
- Determine whether the port enters host mode.
- Determine whether the mouse enumerates.
- Determine whether motion/button events reach the input stack.

## Power button

- Pressing Power once does not fully turn off the display.
- Pressing Power twice can unexpectedly change the visible UI state.
- Double Power press sometimes opens the Terminal application or another mode.
- This is NOT the required behavior.

## Display updates

- Volume-button input appears to be processed.
- Volume overlays sometimes become visible only after pressing Power twice.
- This suggests that event/state updates may be occurring without being rendered immediately, although the root cause remains unproven.

## Startup

- Boot can apparently remain on the static wallpaper rather than transitioning visibly to a ready launcher.
- Pressing Power twice sometimes causes the launcher to appear.
- The startup sequence may be experiencing a presentation/refresh/ownership problem.

## Terminal

An unwanted Terminal window has displayed:

`Nuxel host unavailable — this build has no terminal backend.`

This is not proof that the touchscreen works.

Investigate why Power is launching Terminal when it should not.

Do not attempt a full Terminal backend rewrite during this mission.

## Current launcher

The currently visible Nuxel interface is not yet the exact UTM reference launcher.

**DO NOT FIX THAT NOW.**

Only ensure the existing visible interface can receive working physical input.

The correct-launcher project can resume after the input system is proven.

---

# 3. STRICT NO-FLASH AND RECOVERY POLICY

All permitted repairs must be performed through live Nuxel userspace.

You may:

- Inspect kernel information.
- Inspect driver source.
- Inspect input devices.
- Inspect interrupts.
- Inspect sysfs.
- Trace evdev events.
- Trace libinput events.
- Modify existing userspace software.
- Build ARM64 userspace binaries.
- Deploy using the proven live console.
- Restart affected userspace services.
- Modify device permissions.
- Repair Phoc input configuration.
- Repair WebKit event integration.
- Repair service ordering.
- Repair button-manager userspace code.
- Test USB host support without unsafe hardware operations.
- Perform normal OS reboot if genuinely necessary and recovery is prepared.

You may NOT:

- Flash BOOT.
- Flash recovery.
- Flash rootfs images.
- Write raw partitions.
- Rewrite the device tree on the phone.
- Flash or replace modem/firmware partitions.
- Modify EFS.
- Change bootloader state.
- Run Heimdall/Odin.
- Reboot into TWRP.
- Reboot into Samsung Download Mode.
- Load an unverified replacement kernel module.
- Perform undocumented hardware-register writes.
- Repeatedly power-cycle hardware without bounded tests.

If the missing functionality is conclusively caused by a kernel driver or device-tree limitation, create an offline source patch and tests.

Do not attempt to install that patch on the physical phone.

Report the kernel blocker accurately.

---

# 4. VERY IMPORTANT — NO MORE FAKE TOUCHSCREEN SUCCESS

Implement a strict evidence ladder.

A touchscreen can be in one of these states:

T0 — DEVICE ABSENT

T1 — KERNEL DEVICE REGISTERED

T2 — TOUCH INTERRUPTS OBSERVED

T3 — RAW EVDEV CONTACT EVENTS OBSERVED

T4 — LIBINPUT CONTACT EVENTS OBSERVED

T5 — COMPOSITOR RECEIVES PHYSICAL TOUCH

T6 — WEBKIT RECEIVES PHYSICAL TOUCH

T7 — NUXEL APPLICATION HANDLER RECEIVES TOUCH

T8 — PHYSICAL TAP CAUSES THE CORRECT APPLICATION ACTION

T9 — USER PHYSICALLY CONFIRMS NORMAL TOUCHSCREEN OPERATION

**ONLY T9 IS FULL PHYSICAL TOUCHSCREEN SUCCESS.**

T1 is not success.

T2 is not success.

T3 is not success.

T4 is not success.

A synthetic click is not success.

A registered touchscreen driver is not success.

An agent-generated event is not success.

An active Phoc service is not success.

Persist these states and their supporting evidence.

No optimistic interpretation.

---

# 5. FIRST ACTION — FREEZE THE BASELINE

Before editing any files:

1. Verify Fedora host access.
2. Verify Nuxel live console access.
3. Record current uptime.
4. Record exact kernel revision.
5. Record `/proc/cmdline`.
6. Record currently running graphical processes.
7. Record launcher/service versions.
8. Record touchscreen device state.
9. Record USB controller state.
10. Record hardware-button device state.
11. Record systemd service status.
12. Record recent kernel errors.
13. Record exact existing userspace binary hashes.
14. Back up current input-related configurations.
15. Preserve known-working deployment versions.

Create:

`docs/s10plus-autonomous-boot-repair/TOUCHDOWN/BASELINE.md`

Do not start patching until the baseline is captured.

Preserve the live console throughout the initial investigation.

---

# 6. INVESTIGATE THE SAMSUNG TOUCHSCREEN DRIVER

The Samsung kernel uses the `sec_ts` touchscreen driver family.

Earlier A29/A32 records establish several important behaviors.

## Previous evidence

The touchscreen has previously emitted:

- IRQ activity.
- Touch count changes.
- EV_ABS data.
- Multitouch contact events.

A32 also identified an important failure mode:

`androidboot.mode=charger`

can result in:

`lpcharge=1`

Under that mode, the downstream touchscreen driver may deliberately skip normal initialization.

A normal Nuxel boot previously caused `sec_touchscreen` to appear again.

This is historical evidence.

The current running state must be verified independently.

## Required initial investigation

Inspect:

`/proc/cmdline`

`/proc/bus/input/devices`

`/proc/interrupts`

`/sys/class/input/`

`/sys/class/sec/tsp/`

`/dev/input/event*`

Relevant kernel and system journals.

Determine:

- Whether the kernel booted in charger mode.
- Whether sec_ts initialized.
- Whether the correct I2C/SPI device probed.
- Whether the input device registered.
- Whether the touchscreen interrupt is enabled.
- Whether physical contact changes the IRQ count.
- Whether runtime suspend leaves the controller disabled.
- Whether framebuffer notifier events affect touchscreen state.
- Whether the previous touch-arm helper is running.
- Whether the helper is repeatedly resetting the controller.
- Whether display blanking stops input delivery.
- Whether touchscreen recovery is tied to Power-button display events.

Do not change several things simultaneously.

---

# 7. AUDIT THE EXISTING TOUCH-ARM HELPER

Investigate:

`tools/s10plus/a29/nuxel-touch-arm.c`

and any newer replacements.

Determine the actual currently deployed implementation.

Review:

- Driver initialization sequence.
- Sysfs controls.
- Start/stop behavior.
- Error handling.
- IRQ enabling.
- Display notifier integration.
- Startup dependencies.
- Repeated invocation.
- Idempotence.
- Logging.
- Recovery behavior.

Previous engineering records identified a condition where `sec_ts_start_device()` could return early when internal state already indicated POWER_ON.

That could leave the actual interrupt disabled.

Determine if this is happening on the CURRENT boot.

Do not assume it is.

Avoid the historically problematic `module_on_master` sequence unless new source-level evidence establishes a safe correction.

Do not repeatedly trigger framebuffer blank/unblank merely to force touch recovery.

Repeated panel blanking may explain some of the user's display abnormalities.

If the helper is responsible for interfering with the display, repair its startup ordering and ensure it only performs verified necessary operations.

---

# 8. CREATE A RELIABLE RAW TOUCH TEST

Create a small, deterministic touchscreen diagnostic utility.

Suggested name:

`nuxel-touch-trace`

It must:

- Discover touchscreen devices by identity and event capabilities.
- Avoid hard-coded event node numbers.
- Print device name.
- Print input properties.
- Print supported ABS axes.
- Print coordinate ranges.
- Print tracking IDs.
- Print event timestamps.
- Print touch-down/move/release.
- Print read errors.
- Print IRQ changes where available.
- Produce machine-readable JSONL.
- Exit automatically after a bounded duration.
- Avoid exclusive input grabs by default.

Do not use `EVIOCGRAB` merely to observe input.

Do not accidentally steal events from the compositor.

Validate all ioctl values against the target Linux UAPI headers.

Test both Type B slot-based multitouch and any driver-specific behavior found in source.

## Physical capture

Prepare a capture session lasting approximately 20 seconds.

Tell the user:

"Tap the top-left, center, and bottom-right of the screen, then make one swipe."

Capture genuine physical input.

If events arrive, move to the next layer.

If no events arrive, do not waste time debugging JavaScript first.

Investigate kernel/driver/IRQ/input registration.

Use evidence to isolate the first failing stage.

---

# 9. TRACE EVDEV → LIBINPUT

If raw touch events work, investigate libinput immediately.

Check the version and build.

Inspect device classification.

Determine whether the touchscreen is incorrectly categorized as:

- Unknown input device.
- Mouse.
- Keyboard.
- Unassociated touch device.
- Disabled device.

Check:

- Input properties.
- udev attributes.
- Permissions.
- Seat assignment.
- Device ownership.
- Input event capabilities.

Historical Nuxel runs masked or altered parts of normal udev behavior as a compatibility workaround for systemd 258 on kernel 4.14.

Determine whether this breaks libinput device discovery or hotplug.

Do not blindly unmask udev if that could restore the previous worker storm.

Instead, identify the minimum missing input-device classification or initialization behavior.

Add a correct persistent input configuration where required.

Ensure restarting the compositor does not lose the touchscreen.

---

# 10. TRACE LIBINPUT → PHOC

The phone has used Phoc in headless mode with a Wayland-to-framebuffer bridge.

This is not the normal DRM/KMS-backed Phoc setup.

Investigate whether input is actually connected to the headless compositor.

Verify:

- Running Phoc instance.
- Wayland socket.
- Seat.
- Touchscreen registration.
- Output dimensions.
- Output scale.
- Output transform.
- Touch-device mapping.
- Client focus.
- Current active surface.
- Compositor input handlers.

Determine whether Phoc receives physical touch events.

A working libinput event stream is not proof that Phoc forwards it.

Do not add a second compositor.

Do not start another framebuffer-owning GUI.

Do not recreate the launcher.

Fix the actual compositor input path.

---

# 11. TRACE PHOC → WEBKITGTK → NUXEL

If Phoc receives physical touch, verify WebKitGTK receives it.

Inspect the running:

`nuxel-pwa-host`

and launcher JavaScript.

Instrument:

- Wayland touch-down.
- Wayland touch-motion.
- Wayland touch-up.
- WebKit touchstart.
- WebKit touchmove.
- WebKit touchend.
- pointerdown.
- pointerup.
- click.
- App tile selection.
- Search focus.
- Button activation.

Use temporary low-overhead event logging.

Record correlated timestamps for a single contact.

If WebKit receives events but the app does not respond, inspect:

- Invisible overlays.
- Fullscreen splash remnants.
- CSS pointer-events.
- Touch-action styles.
- Window focus.
- Stale cached JavaScript.
- Hit testing.
- Wrong logical coordinates.
- Wrong application root element.
- Incorrect touch/click event suppression.
- WebKit input permissions.
- Device scale factor.

Do not interpret a synthetic event as physical proof.

Do not rewrite the PWA.

Only fix its existing input integration.

---

# 12. CHECK FOR STALE OVERLAYS BLOCKING TOUCH

Earlier versions of Nuxel Home had a fullscreen boot-splash video overlay.

Even if an overlay becomes visually transparent, it may still intercept pointer/touch events.

Inspect the current DOM and CSS programmatically.

Check:

- Splash overlay state.
- Display property.
- Visibility property.
- Opacity.
- z-index.
- pointer-events.
- Bounding rectangle.
- Attached event listeners.
- Loaded page state.

Ensure that any finished splash/animation overlay is removed from interaction and no longer blocks the home screen.

Do not merely set opacity to zero while leaving a full-screen input-intercepting layer.

This check must be performed even if earlier agents claimed the splash was fixed.

---

# 13. TEST INPUT COORDINATE TRANSFORMS

The physical S10+ framebuffer is approximately:

`1440 × 3040`

The headless Wayland output may be smaller.

Inspect the actual resolution.

Do not assume historic 720×1520 or 720×1440 settings remain correct.

Determine:

- Raw touchscreen X min/max.
- Raw touchscreen Y min/max.
- Screen orientation.
- Wayland logical dimensions.
- Output scale.
- Rotation.
- Margins.
- Safe-area transform.
- Buffer scaling.

Verify:

- Top-left physical touch maps to logical top-left.
- Center maps to center.
- Bottom-right maps to bottom-right.
- Horizontal/vertical movement is not reversed.
- Portrait orientation uses the correct matrix.

A working touch device mapped outside the client surface can appear completely nonfunctional.

Implement calibration based on measured ABS ranges and actual output geometry.

Avoid hard-coded model-specific magic numbers when runtime information is available.

---

# 14. TEST APPLICATION INTERACTION

Once events reach WebKit:

Use the existing launcher.

Required input actions:

1. Select an app tile.
2. Close or return Home.
3. Open Settings.
4. Scroll a list.
5. Focus a text field.
6. Show the virtual keyboard.
7. Type several characters.
8. Dismiss the keyboard.
9. Swipe a list.
10. Repeat with no ghost touches.

Do not stop when the first click handler logs an event.

Ensure the click causes a real visible application-state change.

For manual acceptance, ask the owner to perform these actions.

If the owner is not available, mark T8/T9 unverified and continue deterministic work, but do not announce the touchscreen is fixed.

---

# 15. SECONDARY MISSION — USB-C KEYBOARD AND MOUSE

External input is an important backup.

The phone should support ordinary USB HID input whenever the hardware and running kernel provide USB host functionality.

Investigate why the user's existing equipment fails.

The equipment:

- Keychron USB-C keyboard.
- Standard USB-A mouse.
- USB-A-female to USB-C-male adapter.

Do not assume the adapter is defective.

Do not assume the port is already operating in host mode.

## Critical USB architecture

The current Nuxel live console uses the phone as a USB gadget/device.

USB keyboards and mice require the phone to act as USB host.

On this single physical port, those configurations cannot normally be used simultaneously.

Do not blindly switch the controller into host mode while relying on the same USB port for the only live debugging session.

## Investigate first, switch later

Inspect:

- USB controller driver.
- DWC3 support.
- Device-tree `dr_mode`.
- Host-controller registration.
- xHCI availability.
- USB PHY.
- Type-C/extcon role switching.
- `/sys/class/typec/` where available.
- `/sys/class/usb_role/` where available.
- USB gadget/UDC status.
- USB device enumeration.
- USB HID module support.
- HID input device creation.

Inspect actual kernel options where available:

- CONFIG_USB_DWC3.
- CONFIG_USB_DWC3_DUAL_ROLE.
- CONFIG_USB_XHCI_HCD.
- CONFIG_USB_OTG.
- CONFIG_USB_ROLE_SWITCH.
- CONFIG_USB_HID.
- CONFIG_HID.
- CONFIG_INPUT.
- CONFIG_INPUT_EVDEV.

Exact option names and availability depend on the 4.14 Samsung tree.

Missing sysfs interfaces are not by themselves proof USB host mode is impossible.

Check source and compiled configuration.

## Keychron test

Require the keyboard to be in its wired USB mode.

Test with an appropriate data-capable USB-C cable.

If host mode works, the keyboard should enumerate as one or more HID interfaces.

Verify:

- USB device identity.
- HID binding.
- evdev event device.
- Physical keypress events.
- libinput recognition.
- Phoc delivery.
- WebKit text input.

## Mouse test

Verify that the adapter properly supports a USB host connection.

Inspect enumeration and power delivery.

Verify:

- Mouse VID/PID.
- HID driver.
- EV_REL motion events.
- BTN_LEFT/BTN_RIGHT events.
- Compositor pointer movement.
- Actual application clicking.

Do not claim mouse success because `/dev/input/mice` exists.

## Safe testing without USB console

Before unplugging the Fedora laptop:

1. Save diagnostic commands.
2. Enable bounded persistent logging.
3. Arrange a safe local automatic test window.
4. Verify the logs survive disconnect.
5. Confirm that ordinary reconnect returns USB device/gadget mode.
6. Tell the owner exactly when to swap cables.

Avoid making permanent USB role changes during initial testing.

Do not sacrifice the only working development connection.

If host support is absent from the kernel, prepare an offline source/configuration patch and mark it as requiring future kernel deployment.

---

# 16. CREATE A DETERMINISTIC INPUT CAPABILITY MATRIX

Produce a matrix covering:

- Built-in Samsung touchscreen.
- USB-C wired keyboard.
- USB-A mouse through adapter.
- Virtual keyboard.
- Power key.
- Volume Up.
- Volume Down.
- Bixby key.

For each track:

- Hardware detection.
- Kernel driver.
- evdev.
- libinput.
- Compositor.
- WebKit.
- Nuxel action.
- Owner confirmation.

Example:

TOUCHSCREEN:

Kernel device: YES

IRQ: YES

evdev: YES

libinput: YES

Phoc: UNKNOWN

WebKit: UNKNOWN

Nuxel click: NO

Physical confirmation: FAILED

Overall: NOT WORKING

Use actual evidence rather than this example.

---

# 17. SUPPORTING FIX — POWER BUTTON MISBEHAVIOR

The user reports:

- One press does not fully blank the screen.
- Two presses unexpectedly change the launcher state.
- Terminal may open.
- Volume overlays appear after Power activity.
- Startup screen sometimes updates only after Power presses.

These failures may interact with touchscreen initialization or UI event handling.

They are therefore in scope.

## Trace physical Power events

Inspect raw EV_KEY events from the actual Power button.

Determine whether the system receives:

- KEY_POWER.
- KEY_WAKEUP.
- Duplicate key events.
- KEY_ASSISTANT/Bixby misidentification.
- Key autorepeat.
- Multiple handlers consuming the same press.

Check whether:

- systemd-logind handles Power.
- Nuxel button manager handles Power.
- Phoc handles Power.
- WebKit receives Power as a keyboard event.
- Bixby and Power are incorrectly mapped to the same logical action.

Log a single physical press with timestamps across all handlers.

## Correct behavior

Short Power press:

DISPLAY_ON → DISPLAY_OFF.

Another short Power press:

DISPLAY_OFF → DISPLAY_ON.

Short Power must not:

- Open Terminal.
- Open the application switcher.
- Change launcher mode.
- Trigger Camera.
- Replay boot animation.
- Restart WebKit.
- Restart Phoc.
- Reinitialize the entire display unless genuinely necessary.

Double Power press must not accidentally route to Terminal.

If a double-press Camera gesture exists, disable it temporarily during this input stabilization mission or ensure it is isolated from short-press display toggling.

Do not let two independent services process the same gesture.

---

# 18. SUPPORTING FIX — FULL SCREEN BLANKING

The user reports that screen-off only partially darkens the display.

Investigate actual display power management.

Determine whether the current implementation:

- Draws a black rectangle.
- Reduces brightness.
- Blanks the framebuffer.
- Calls FBIOBLANK.
- Controls panel power.
- Modifies backlight brightness.
- Suspends the compositor.
- Stops the bridge.
- Changes framebuffer ownership.

A black image is not necessarily a physically powered-off AMOLED display.

Implement the strongest safe display-off behavior supported by the existing kernel and panel driver.

Do not repeatedly toggle kernel display state while a live framebuffer writer is active without ownership coordination.

Preserve:

- Touchscreen driver state where required for wake.
- Power-button wake path.
- Live console.
- Kernel thermal safety.
- Correct framebuffer restoration.

Verify the display can be awakened without requiring multiple keypresses.

If full panel power-off is not safe with the current userspace/kernel architecture, document the precise restriction instead of claiming success.

---

# 19. SUPPORTING FIX — FROZEN STARTUP WALLPAPER

The user reports that Nuxel sometimes appears stuck on the static wallpaper after boot.

Pressing Power twice causes the launcher to appear.

This is NOT acceptable.

Investigate the actual cause.

Potential categories:

- Launcher first frame never submitted.
- Wayland screencopy stalls.
- Phoc startup race.
- WebKit load completion race.
- Framebuffer bridge stalled.
- Dirty-region tracking broken.
- Panel redraw only occurs on a hardware event.
- Stale display page selected.
- Framebuffer pan missing.
- Event loop blocked.
- Animation ownership never released.
- Missing compositor frame callback.
- Graphics presentation dependent on a Power-key event.

Treat these as hypotheses, not established causes.

Use:

- Timestamps.
- Frame counters.
- Process state.
- Thread stack inspection.
- Wayland callback traces.
- Render loop tracing.
- Display ownership logs.
- Systemd startup ordering.

Find why Power activity changes the presentation.

Fix the state machine or redraw scheduling.

Do not introduce a synthetic Power keypress at boot as a workaround.

Do not fix the symptom with an arbitrary repeated screen blank/unblank timer.

The launcher must become visible automatically after startup without physical intervention.

---

# 20. SUPPORTING FIX — STALE VOLUME OVERLAY

The user reports that Volume Up/Down appears to affect internal volume state, but its overlay only becomes visible after pressing Power twice.

Trace:

Volume EV_KEY

→ Nuxel button manager

→ audio state

→ overlay update

→ WebKit/Phoc frame

→ framebuffer presentation.

Determine whether:

- Overlay callbacks execute.
- GUI redraws are requested.
- Phoc produces a frame.
- Bridge commits it.
- The overlay is hidden behind a stale display page.

This may be the same underlying issue as the frozen wallpaper.

If so, fix the common root cause rather than adding separate hacks.

Do not undertake broader audio driver development during this task.

---

# 21. SUPPORTING FIX — LONG-PRESS POWER MENU

After touchscreen investigation and input path stabilization, implement or repair long-press Power.

Required behavior:

- Short press: display on/off.
- Long press: show Nuxel Power Menu.

The menu should contain:

- Cancel.
- Power Off.
- Restart Nuxel.
- Recovery (TWRP).
- Download Mode.

Power Off and Restart require explicit user confirmation.

Recovery and Download Mode must not be invoked autonomously.

They may remain disabled pending verification of the proper Samsung reboot interface.

Do not guess low-level Samsung reboot commands.

## Menu without touchscreen

Until the touchscreen is fully proven, provide keyboard-based navigation where available and a physical-button navigation fallback if safe:

- Volume Up/Down: move selection.
- Short Power: confirm selection when menu is open.
- Bixby: cancel/back, where not conflicting with recovery combinations.

Do not hijack Samsung hardware emergency sequences.

The normal Restart action should request an orderly systemd reboot back into Nuxel.

No recovery reboot.

No flashing.

No unattended reboot loops.

---

# 22. AVOID REGRESSING EXISTING SERVICES

During this mission, preserve:

- Fedora startup.
- USB console.
- Nuxel launcher.
- Original wallpaper.
- Animation.
- Network services.
- Existing app files.
- User settings.
- Button mappings outside identified defects.
- Camera cutout settings.
- Rootfs data.

Do not turn this into a full system upgrade.

Do not run `dnf upgrade` as a troubleshooting shortcut.

Do not rebuild the complete rootfs just to modify touchscreen userspace.

Keep changes narrowly scoped.

---

# 23. QONQRETE AGENT ROLES

Use the available agent architecture deliberately.

## Qlarifier — DeepSeek V4 Flash High

Responsibilities:

- Classify observations.
- Identify first failing input layer.
- Compare current logs to A29/A32.
- Track evidence ladder.
- Reject unproven success.
- Maintain persistent issue queue.

## InstruQtor — DeepSeek V4 Flash Thinking Max

Responsibilities:

- Analyze Samsung driver behavior.
- Analyze USB role switching.
- Diagnose event delivery.
- Diagnose compositor/display race conditions.
- Design minimal fixes.
- Identify kernel-only blockers.

## ConstruQtor — DeepSeek V4 Flash High

Responsibilities:

- Build diagnostic tools.
- Implement narrow source patches.
- Write regression tests.
- Build ARM64 artifacts.
- Deploy userspace fixes.
- Maintain rollback packages.

## InspeQtor — DeepSeek V4 Flash Thinking Max

Responsibilities:

- Review every claimed fix.
- Confirm evidence chain.
- Detect shortcuts and false positives.
- Verify no hidden kernel/flash operations.
- Review display/USB recovery safety.
- Reject incomplete physical acceptance.

Only ONE agent may control the phone's serial console or perform a live deployment at any time.

Other agents may analyze copies of logs/source concurrently without writing to the live device.

Persist work after each repair attempt.

---

# 24. NO MORE ENDLESS UNPRODUCTIVE LOOPS

The mission must keep pursuing touchscreen functionality while meaningful diagnostic or implementation work remains.

Do not stop simply because:

- A file compiles.
- A service becomes active.
- A device node exists.
- One interrupt fires.
- An evdev test returns events.
- A synthetic click succeeds.

However, do not enter infinite retry loops.

For each failure:

1. Record the observation.
2. Identify the first failing stage.
3. Form a falsifiable hypothesis.
4. Make one targeted change.
5. Run a discriminating test.
6. Record the result.
7. Keep or revert the change.
8. Update the evidence ladder.

If three attempts reach an identical failure without new evidence, stop repeating that approach.

Escalate to deeper source analysis.

If the remaining blocker is a kernel limitation that cannot be repaired live, produce the exact offline patch and declare the LIVE mission blocked.

Do not pretend it works.

If physical owner input is required, prepare a bounded test request, preserve all diagnostic state, and continue any remaining safe work.

Owner silence does not count as a passing physical test.

---

# 25. REQUIRED PHYSICAL TEST REQUESTS

The user is available to perform short, specific physical checks.

Do not repeatedly ask for vague confirmation.

Use short test requests such as:

## Test A — Touchscreen raw input

"Please tap top-left, center, bottom-right and swipe once during the next 20 seconds."

## Test B — Touchscreen application input

"Please tap the Settings icon, return Home and open Terminal."

## Test C — Power

"Please press Power once and wait three seconds, then press once again."

## Test D — Keyboard

"Please disconnect the Fedora USB console and connect your Keychron in wired mode for 20 seconds; then reconnect the Fedora laptop."

Only request these when the agent has armed appropriate diagnostics.

For USB tests, ensure reconnect recovery is planned before asking the user to unplug the debug connection.

Do not ask the user to inspect kernel logs manually if QonQrete can collect them.

---

# 26. AUTOMATED TESTS

Create deterministic tests for:

- Correct touchscreen device discovery.
- Correct ioctl values.
- ABS axis parsing.
- Type B contact tracking.
- Coordinate transforms.
- Seat assignment.
- Input permission.
- Phoc input event delivery.
- WebKit input event logging.
- App click-handler behavior.
- USB role discovery.
- USB HID configuration.
- Button event classification.
- Single/double/long-press arbitration.
- Power-key Terminal misrouting.
- Display blank/wake.
- Render callbacks.
- Framebuffer ownership.
- Startup launcher readiness.
- Overlay redraw timing.
- Serial reconnect.
- Userspace deployment rollback.

For each test record:

- Command.
- Exit code.
- Timestamp.
- Source revision.
- Device state.
- Expected result.
- Actual result.
- Verdict.

No invented measurements.

---

# 27. DELIVERABLES

Create:

`docs/s10plus-autonomous-boot-repair/TOUCHDOWN/`

Required files:

- `BASELINE.md`
- `TOUCHSCREEN-DRIVER-STATE.md`
- `TOUCHSCREEN-IRQ-EVIDENCE.md`
- `TOUCHSCREEN-EVDEV-EVIDENCE.md`
- `LIBINPUT-TRACE.md`
- `PHOC-INPUT-TRACE.md`
- `WEBKIT-INPUT-TRACE.md`
- `TOUCH-COORDINATE-MAPPING.md`
- `USB-C-HOST-CAPABILITY.md`
- `USB-KEYBOARD-TESTS.md`
- `USB-MOUSE-TESTS.md`
- `POWER-BUTTON-ROOT-CAUSE.md`
- `DISPLAY-REFRESH-ROOT-CAUSE.md`
- `POWER-MENU.md`
- `SOURCE-PATCHES.md`
- `LIVE-DEPLOYMENTS.md`
- `REGRESSION-TESTS.md`
- `OWNER-PHYSICAL-ACCEPTANCE.md`
- `FINAL-VERDICT.md`

Also produce working diagnostic scripts:

`nuxel-touch-trace`

`nuxel-usb-input-audit`

`nuxel-button-trace`

`nuxel-display-frame-trace`

Names may be adapted to existing project conventions.

Avoid duplicate tools when existing tools already provide the required capabilities.

---

# 28. FINAL VERDICT REQUIREMENTS

At the end, produce one of these explicit outcomes:

## TOUCHSCREEN_VERIFIED

All evidence stages through actual user-confirmed interaction pass.

## TOUCHSCREEN_READY_FOR_OWNER_TEST

The full software/input event pipeline is proven, but the user has not yet completed physical acceptance.

## TOUCHSCREEN_PARTIALLY_WORKING

Some physical input reaches the system, but interaction is incomplete.

Identify exactly which layer fails.

## TOUCHSCREEN_BLOCKED_KERNEL

The current kernel/driver/device tree cannot provide the necessary functionality without a kernel update.

Include an offline source patch and verification plan if feasible.

## TOUCHSCREEN_FAILED_UNRESOLVED

The defect is not solved.

Include evidence, attempted fixes, reasons for failure and next discriminating tests.

Do not turn unresolved into verified.

For the USB keyboard/mouse and Power button, use corresponding independent verdicts.

Do not imply external USB HID functionality is required to declare the built-in touchscreen working.

---

# 29. FINAL EXECUTION ORDER

**EXECUTE NOW.**

PHASE 1 — TOUCHSCREEN HARDWARE

1. Freeze baseline.
2. Verify normal versus charger boot.
3. Verify sec_ts probe.
4. Verify controller state.
5. Verify IRQ behavior.
6. Review touch-arm helper.
7. Capture physical evdev events.
8. Fix any proven driver-state issue that is safely repairable in userspace.

PHASE 2 — TOUCHSCREEN SOFTWARE

9. Verify libinput.
10. Verify Phoc device registration.
11. Verify Wayland touch delivery.
12. Verify WebKit touch events.
13. Verify application handlers.
14. Fix coordinate transforms.
15. Eliminate invisible overlays intercepting touches.
16. Physically test tapping an app.
17. Physically test swipes and text entry.

PHASE 3 — EXTERNAL INPUT

18. Inspect USB host configuration.
19. Inspect role negotiation.
20. Inspect USB HID support.
21. Prepare persistent diagnostics.
22. Test Keychron keyboard safely.
23. Test USB mouse safely.
24. Verify keyboard/mouse app input.
25. Restore reliable gadget-console behavior after testing.

PHASE 4 — POWER/DISPLAY

26. Trace Power button events.
27. Find why double Power opens Terminal.
28. Remove the incorrect mapping/duplicate handling.
29. Fix display blanking.
30. Fix display wake.
31. Diagnose why startup sticks on wallpaper.
32. Fix stale volume overlay rendering.
33. Implement/test long-press Power menu.
34. Preserve safe normal reboot functionality.

PHASE 5 — VALIDATION

35. Run deterministic tests.
36. Deploy only validated userspace patches.
37. Verify no launcher/console regression.
38. Run physical touch acceptance.
39. Run Power-button acceptance.
40. Record USB-host results.
41. Run an authorized normal-boot persistence test when safe.
42. Produce exact final verdicts and evidence.

---

# 30. FINAL ORDER

**THE USER NEEDS TO BE ABLE TO INTERACT WITH THE PHONE.**

We have built an OS that boots.

We have built a GUI that renders.

We have working Fedora.

We have a live development console.

We have input drivers that previously produced touchscreen events.

But the user still cannot tap the screen.

THIS IS THE BLOCKER.

Stop saying it should work.

Prove which layer receives real input.

Find the first layer where the events disappear.

Fix that layer.

Continue to the next layer.

Repeat until a physical tap causes the intended application action.

**DO NOT ACCEPT COMPILATION AS PROOF.**

**DO NOT ACCEPT LIBINPUT ENUMERATION AS PROOF.**

**DO NOT ACCEPT SYNTHETIC CLICKS AS PROOF.**

**DO NOT REWRITE THE LAUNCHER.**

**DO NOT DO UNRELATED DEVELOPMENT.**

**DO NOT FLASH ANYTHING.**

Keep the Fedora laptop connected through the live console whenever possible.

Keep Nuxel recoverable.

Fix the incorrect Power-button actions and screen refresh behavior that interfere with testing.

Produce precise hardware acceptance requests when actual human input is necessary.

# THE ONLY VALID FINAL TOUCHSCREEN SUCCESS:

**OWNER PUTS FINGER ON NUXEL → APP OPENS → OWNER SWIPES → UI MOVES → OWNER TYPES → INPUT APPEARS.**

Everything short of that is partial progress.

## QONQRETE — OPERATION TOUCHDOWN. EXECUTE. 🐧🔥
