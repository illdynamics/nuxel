# PWNAGE-32000 — NUXEL RESURRECTION & PERFORMANCE WARFARE

**Project:** Nuxel Linux phone OS  
**Target device:** Samsung Galaxy S10+ SM-G975F, Exynos 9820, `beyond2lte`  
**Known environment:** Fedora-based ARM64 userspace; kernel previously reported as Linux 4.14.253. Verify the running environment.  
**Mission:** Restore keyboard and haptics, repair navigation, eliminate boot-time regression, improve responsiveness and remove unwanted charging-related touch lockout.

## 0. MISSION OBJECTIVES

Fix all five regressions:

1. The wrong keyboard was removed. Restore the intended grey/black/white keyboard, make it the default across the system and ensure haptic feedback works.
2. Back works in the browser but fails in other apps, sometimes bringing the four desktop dock icons above the foreground app. Fix global navigation and application lifecycle behaviour.
3. Boot time has increased to several minutes. Find and fix the actual cause.
4. The phone is sluggish. Identify measurable bottlenecks and fix them.
5. Booting with a charging cable connected can trigger an unwanted LPM/charging mode that disables touch. Remove this behaviour.

These are implementation requirements, not a request for an audit alone.

### Safety constraints

- No kernel replacement, firmware flashing, partition writes, bootloader changes or repartitioning.
- No destructive reset or factory reset.
- Preserve the independent USB/serial recovery route.
- Preserve existing working lockscreen, Home, Recents, browser, desktop, dock and applications.
- Do not disable thermal, battery or electrical safety protections.
- Do not overwrite unrelated user changes.
- Back up live configuration before replacing it and provide rollback instructions.
- Do not hide failures or claim unperformed tests passed.
- Prefer minimal, reversible userspace changes where possible.
- Do not reboot automatically if doing so risks losing an active recovery session.

---

# 1. BASELINE AND FORENSIC INVESTIGATION

Before changing code:

1. Record the repository root, branch, HEAD commit and `git status`.
2. Inspect recent commits, relevant diffs and `git log`/`git blame` for keyboard, haptics, navigation, boot, power-management and input handling.
3. Identify the actual framework and architecture in use. Do not assume UI components, init system or input stack without checking.
4. Locate keyboard implementations, theme files, input-method registration, haptic services, Back handlers, window lifecycle, dock layering, boot services and charging/LPM policies.
5. Capture baseline startup timings, CPU and memory usage, logs and UI responsiveness where available.
6. Identify when each regression was introduced and whether several symptoms share a root cause.
7. Create `docs/beta-finalization/live/evidence/pwnage-32000/` for sanitized logs, timings, test output and verification evidence.

Preserve unrelated changes and establish a recoverable baseline before editing.

---

# 2. FIX A — RESTORE THE CORRECT KEYBOARD AND HAPTICS

## 2.1 Recover the original keyboard

The required keyboard is the **grey/black/white keyboard that existed before the wrong keyboard was removed**.

Do not simply recolour the remaining unwanted keyboard and call it fixed.

Investigate:

- Deleted or replaced keyboard files in Git history.
- Existing keyboard implementations, themes, layouts and assets.
- Application registration and default input-method configuration.
- Previous commits that removed, disabled or replaced the intended keyboard.
- Screenshots, documentation and regression tests that identify the original design.

Use the original implementation wherever recoverable. Correct the registration and default selection so the intended keyboard is actually used.

If it cannot be recovered, document the evidence and searches performed. Do not claim the original keyboard has been restored when it has not.

## 2.2 Make it the consistent system keyboard

Verify keyboard invocation in:

- Native applications.
- Browser forms.
- Search and settings fields.
- Dialogs and other standard text-entry contexts.
- Login/unlock fields where keyboard input is expected.

Use the existing input-method mechanism. Remove conflicting defaults without breaking supported layouts or languages.

Test focus handling, typing, backspace, shift/caps, symbols, enter, dismissal and switching between text fields.

## 2.3 Restore the visual design

Restore the original grey, black and white appearance using the recovered implementation or assets.

Ensure legible labels, appropriate key sizes, sufficient contrast, correct placement and no obstruction of essential navigation controls. Do not redesign unrelated UI.

## 2.4 Restore real physical haptics

Trace the path from a keyboard keypress to the device vibrator.

Inspect:

- Existing haptic API and service.
- Device vibrator nodes and permissions.
- Input-method callbacks.
- User vibration settings.
- Device-specific driver availability.
- Duplicate or missing event handlers.
- Blocking calls and errors.

Use the existing abstraction where possible. Provide short keypress feedback, respect user preferences and avoid continuous or excessive vibration.

Haptics must not stall typing or introduce noticeable lag. Use asynchronous execution when appropriate to the architecture.

Distinguish a software defect from a missing device driver or unavailable hardware. Never simulate success.

## 2.5 Tests

Verify that:

- The intended keyboard is the actual default.
- The unwanted keyboard is not selected by mistake.
- The keyboard opens across several applications.
- Text input and dismissal work.
- Haptics follow the user preference.
- Disabling haptics prevents vibration.
- Missing vibrator hardware does not crash or stall input.
- Keyboard responsiveness remains acceptable.

---

# 3. FIX B — BACK BUTTON AND FOREGROUND APP NAVIGATION

## 3.1 Reproduce the failure

Browser Back currently works, but other apps may display the four bottom desktop dock icons over the foreground application instead of navigating back or minimizing correctly.

Reproduce this in at least two non-browser apps. Record the event sequence and inspect application/window state before and after the press.

Do not break the browser's working behaviour.

## 3.2 Establish consistent Back semantics

Follow the existing application lifecycle model and implement a single coherent fallback:

1. If the active app has a valid internal Back action, let it handle the press.
2. Otherwise, use the established app/window dismissal or minimization behaviour.
3. Ensure the desktop and dock do not appear above a still-foreground application.
4. Prevent duplicate handlers, double-minimization and partially dismissed states.
5. Preserve correct focus when restoring an application.

Do not blindly destroy every app or force every Back press to minimize an app. Use the project's intended behaviour.

## 3.3 Investigate the root cause

Inspect:

- Global Back-button dispatch.
- Event bubbling and propagation.
- Duplicate listeners and stale callbacks.
- Active-app and keyboard focus ownership.
- Window-manager or compositor transitions.
- App lifecycle and restoration.
- Desktop visibility and dock stacking order.
- Overlay containers and z-index/stacking contexts.
- Handlers that consume Back without actually handling it.

Fix the root cause. Avoid per-app hacks and arbitrary z-index escalation.

## 3.4 Layering requirements

When an app is foregrounded, it must appear above the desktop and dock. The dock should be visible in the intended desktop state, not because an app receives Back.

Preserve the lockscreen, dialogs, quick settings, Recents and other intended overlays.

## 3.5 Regression tests

Test:

- Browser internal navigation and existing fallback.
- Back from at least two non-browser apps.
- Nested views and dialogs.
- Apps without internal navigation history.
- Repeated or rapid Back presses.
- Switching apps, minimizing and restoring.
- Home and Recents after Back.
- Dock visibility and stacking throughout transitions.

A single Back press must never accidentally display dock icons over the foreground application.

---

# 4. FIX C — ELIMINATE THE MINUTES-LONG BOOT REGRESSION

## 4.1 Measure boot stages

Define and measure the boot timeline using the available init system and tools:

- Kernel-to-userspace handoff.
- Core service startup.
- Display and touchscreen readiness.
- UI shell startup.
- Preloading screen or boot animation.
- Lock-screen readiness.
- First successful touch interaction.
- Completion of nonessential services.

Use relevant tools such as `systemd-analyze`, journal timestamps, service logs, application instrumentation or the actual init-system equivalent.

Record real timings. Do not fabricate a previous baseline.

## 4.2 Find the regression

Inspect changes to:

- Service ordering and dependencies.
- NetworkManager and Wi-Fi readiness waits.
- USB gadget initialization.
- Hardware probes and device discovery.
- Battery and charging detection.
- Display and touchscreen initialization.
- Lock-screen and shell startup.
- Preloading video and media decoding.
- Asset loading and configuration parsing.
- Retry loops, service restarts and timeouts.
- Filesystem checks, blocking I/O and excessive logging.
- Recovery-console initialization.
- Fixed sleeps and waits for unavailable hardware.

Look for services that wait for optional hardware or retry for minutes before allowing the UI to become usable.

## 4.3 Fix the actual cause

For each delay:

1. Identify the blocking operation.
2. Establish why it blocks.
3. Determine whether it is essential before the lockscreen becomes interactive.
4. Remove unnecessary dependencies and duplicated work.
5. Use bounded waits and appropriate retry policies.
6. Start independent, noncritical work asynchronously when safe.
7. Prevent retry storms and redundant hardware scans.
8. Ensure optional hardware failures do not block core phone usability.
9. Preserve dependencies required for secure lockscreen and input readiness.

Do not hide the delay by removing the splash screen. Do not replace readiness checks with arbitrary sleeps. Do not disable essential services without understanding their role.

## 4.4 Preloading video

If the preloading video is present in the current boot flow, verify that it:

- Runs concurrently with independent service initialization.
- Does not block the UI thread or essential input startup.
- Handles missing, corrupt or unsupported media gracefully.
- Does not impose an unnecessary wait after the system is ready.
- Does not interfere with the secure lockscreen handoff.

## 4.5 Acceptance criteria

- Record before/after timings using the same method.
- Identify the largest contributors to boot delay.
- Demonstrate measured improvement.
- Verify secure, interactive lockscreen readiness.
- Verify that touch and essential UI remain usable.
- Verify that optional hardware failures do not stall boot.
- Reboot-test when safe and practical.

Set a concrete target from the actual baseline and device constraints. The goal is to eliminate the minutes-long regression, not to invent an arbitrary benchmark.

---

# 5. FIX D — PROFILE AND IMPROVE SYSTEM RESPONSIVENESS

## 5.1 Profile before optimizing

Investigate:

- CPU usage and per-process hotspots.
- RAM pressure, zRAM/swap and OOM events.
- GPU/compositor workload and rendering stalls.
- UI-thread blocking and frame pacing.
- Storage I/O latency.
- Slow services, repeated restarts and blocked tasks.
- Excessive logs or retry loops.
- Input-event handling latency.
- Network and hardware-discovery delays.
- Media decoding and animation workload.
- Background applications and redundant processes.
- Thermal throttling, where safely observable.

Use tools supported by the actual device. Do not assume desktop-only utilities are installed or work on the phone.

## 5.2 Produce an evidence-based bottleneck list

For each significant finding, document:

- Affected component.
- Observable symptom.
- Measurement/log evidence.
- Root cause or best-supported diagnosis.
- Minimal proposed fix.
- Regression risk.
- Before/after result.

Rank the issues by impact. Separate measurable problems from cosmetic complaints and unsupported guesses.

## 5.3 Implement targeted fixes

Where evidence supports it:

- Remove redundant work from rendering and input handlers.
- Avoid blocking the UI thread on disk, network or hardware discovery.
- Correct service restart loops and retry storms.
- Cache expensive immutable assets where safe.
- Avoid repeated asset loads and configuration parsing.
- Correct inefficient polling and refresh loops.
- Reduce unnecessary rendering and animation workload.
- Fix memory leaks and needless allocations.
- Remove duplicate event handlers.
- Cancel obsolete asynchronous work and clean up resources.

Do not disable essential services or globally degrade the interface as the first resort.

Do not overclock, undervolt, disable thermal protections or apply risky kernel tuning as a shortcut.

## 5.4 Responsiveness verification

Measure or otherwise verify:

- Physical tap-to-response latency.
- Keyboard opening and typing.
- Back, Home and Recents transitions.
- Desktop and dock interaction.
- Lockscreen input.
- App launch and restoration.
- Idle CPU load and memory use.
- Stability during repeated app switching.

If exact frame timing is unavailable, clearly label the proxy used. Do not claim FPS or latency improvements without evidence.

---

# 6. FIX E — REMOVE CHARGING-RELATED TOUCH LOCKOUT

## 6.1 Required behaviour

**Booting with a charging cable connected must not disable touch input.**

Cable connection or charging detection must not by itself:

- Disable the touchscreen.
- Set a persistent touch-unavailable state.
- Prevent unlocking or ordinary UI interaction.
- Block keyboard, Back, Home or Recents.
- Leave the device trapped in an unusable charging-only mode.

The user did not request this behaviour.

## 6.2 Trace the source

Search the codebase and Git history for:

- `LPM`
- `low power`
- `charging`
- `charger`
- `touch unavailable`
- `touch disabled`
- `input disabled`
- `suspend`
- `power mode`
- `battery mode`
- Touchscreen and input-device enable/disable logic.

Trace the complete transition from cable detection through power policy to actual input state.

Determine whether the behaviour originates in a userspace charging screen, power-management policy, touchscreen service, boot-mode flag, permissions, stale state or hardware/driver limitation.

Do not simply hide the warning text while leaving touch disabled.

## 6.3 Correct the policy

Remove the unwanted policy that disables touch solely because external power is connected.

Retain legitimate low-power features such as display-off and genuine suspend behaviour where safe, but decouple them from ordinary charging and interactive use.

Requirements:

- Touchscreen initializes normally during cable-connected boot.
- Lockscreen remains interactive.
- Unlocking and navigation work while charging.
- Connecting or disconnecting a cable does not disable touch.
- Charging indicators and battery reporting continue to work.
- Failed optional charger-status queries do not disable input.
- No stale input state remains after a mode transition.
- Thermal, battery and electrical protections remain intact.

If a kernel driver is actually responsible, provide evidence and report the limitation rather than claiming a userspace-only fix.

## 6.4 Test matrix

Test:

1. Boot without a cable.
2. Boot with a cable connected.
3. Connect a cable while the phone is interactive.
4. Disconnect a cable while the phone is interactive.
5. Lock and unlock while charging.
6. Open the keyboard and type while charging.
7. Use Back, Home and Recents while charging.
8. Test ordinary screen-off and wake behaviour where supported.

Verify that touch remains available whenever the phone should be interactive.

---

# 7. CROSS-FEATURE REGRESSION TESTS

Test the fixes together, not just in isolation.

Required scenarios:

- Boot without a cable.
- Boot with a cable.
- Grey/black/white keyboard selected by default.
- Real haptic feedback, where supported by hardware.
- Browser navigation.
- Back from multiple non-browser apps.
- Home and Recents transitions.
- Correct dock layering during app transitions.
- Keyboard input while charging.
- Touchscreen operation after locking and unlocking.
- Idle responsiveness and repeated app switching.
- Recovery when optional hardware or services are unavailable.

Add automated tests for the software logic and physical-device tests for hardware-dependent behaviour. Do not delete or weaken existing tests to make the suite pass.

---

# 8. SAFE IMPLEMENTATION AND DEPLOYMENT

Before changing files:

1. Record the current state and preserve unrelated changes.
2. Keep changes minimal and reversible.
3. Add tests for the defects being corrected.
4. Run relevant unit tests, integration tests, linting and static checks.
5. Inspect the diff for unintended changes.
6. Keep rollback patches or backups for changed live configuration.
7. Deploy only to the intended userspace components.
8. Verify the deployed version and runtime behaviour.

Do not flash an image, write partitions, replace the kernel, modify firmware or change bootloader settings.

Do not reboot automatically if doing so could interrupt an active recovery session. Establish that the independent USB/serial recovery path is available before any reboot that is necessary for testing.

Never equate a successful build or service start with a verified functional fix.

---

# 9. EVIDENCE AND FINAL REPORT

Store sanitized logs, timing data, test results and verification evidence in:

`docs/beta-finalization/live/evidence/pwnage-32000/`

Avoid committing credentials, unnecessary device identifiers or sensitive logs.

For each of the five issues, report:

- Root cause.
- Changed files.
- Fix implemented.
- Automated test results.
- Physical-device test results.
- Before/after measurements, where applicable.
- Status: `FIXED`, `PARTIALLY FIXED`, `BLOCKED` or `NOT REPRODUCED`.

### Keyboard and haptics

Identify the restored keyboard implementation and the evidence used to establish its identity. State whether physical vibration was verified.

### Navigation

List the apps tested and the observed Back behaviour. Explicitly verify that the dock no longer overlays foreground applications.

### Boot performance

Provide measured startup stages before and after the changes, identify the largest contributors and explain what improved. Clearly label any hardware testing that could not be performed.

### System performance

List the measured bottlenecks, changes made and verified improvements. Separate measurements from subjective observations.

### Charging and touch

Report cable-connected boot results, touch availability, lockscreen interaction, keyboard behaviour and cable connect/disconnect tests.

### Safety and rollback

Document the preserved recovery mechanism, rollback instructions and confirmation that no kernel replacement, firmware flashing, partition writes or bootloader changes were performed.

### Completion standard

Do not mark the mission fully complete if a critical defect remains broken or untested. Explain every remaining blocker, its evidence and the next safe action.

**Start with forensic investigation, then implement the fixes in order. Execute the work rather than returning only a plan.**
