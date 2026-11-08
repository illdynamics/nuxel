# PWNAGE-35000 — NUXEL BUTTERSMOOTH PERFORMANCE, HAPTICS, NAVIGATION, REBOOT & WI-FI RELIABILITY

## Mission and execution requirements

You are working on Nuxel, a custom Fedora-based ARM64 Linux phone OS. Your current target device is the Samsung Galaxy S10+ SM-G975F (`beyond2lte`), using the existing Fedora 43-based userspace and the currently installed Linux 4.14.253 kernel, unless inspection proves the current environment differs.

The phone has become more responsive through previous improvements, but several fundamental problems remain. This mission is a serious performance and reliability pass across the UI, input, application lifecycle, reboot sequence, networking stack, and quick-settings controls.

Your objective is to make Nuxel feel **buttersmooth, immediate, predictable, and lightweight** on the real device.

This is an implementation mission, not a brainstorming exercise. Investigate the current code, reproduce the failures, identify root causes, implement fixes, test them, deploy safely, and document results.

Do not stop at a plan or a list of suggestions. Do not report a fix as complete merely because the code compiles or an icon changes.

### Non-negotiable constraints

- Preserve the existing 8-bit arcade aesthetic. Nuxel does not need expensive transparency, blur, complex compositing, or GPU-heavy visual effects.
- Optimize actual responsiveness, not just perceived responsiveness.
- Preserve working functionality and existing user preferences.
- Do not flash the phone, change partitions, modify the bootloader, replace the kernel, or perform a destructive reset.
- Do not disable important security, filesystem, or service shutdown behavior merely to make the phone appear faster.
- Do not introduce a new heavyweight runtime, desktop environment, rendering engine, or major dependency without demonstrating necessity.
- Preserve USB console, serial console, and WLAN recovery access wherever currently supported.
- Do not disable touch input when a charger or USB cable is connected.
- Do not fake haptic feedback, Wi-Fi readiness, successful app minimization, or successful reboot.
- Back up any existing configuration before changing it. Make changes reversible.
- Test on the actual S10+ where hardware behavior is involved. If physical-device access is unavailable, distinguish code-level verification from unverified hardware behavior.
- Preserve the existing service/dashboard bind defaults and unrelated networking configuration. Do not change network exposure as part of this mission.
- Never kill essential processes, suppress errors, or shorten every service timeout indiscriminately to make benchmarks look better.

Create or update `docs/pwnage-35000.md` with the investigation, implementation details, test evidence, and remaining limitations.

---

# PHASE 0 — ESTABLISH A BASELINE

Before changing code, understand the current implementation.

## 0.1 Inspect the repository

Inspect:

- Repository structure and current Git status.
- Existing mission documentation, especially `docs/pwnage-35000.md` if it exists.
- Current UI architecture, event loop, rendering path, navigation handlers, app registry, and app lifecycle.
- Keyboard implementation, input events, haptic configuration, and any existing vibration service or daemon.
- Power-menu actions, shutdown/reboot commands, systemd units, and service dependencies.
- Wi-Fi controls, quick-settings actions, NetworkManager integration, supplicant/backend configuration, and startup logic.
- Existing logging, diagnostics, watchdogs, and health-check infrastructure.
- Existing test suites, launch scripts, deployment procedure, and rollback mechanism.

Determine which components are authoritative. Avoid adding duplicate services or competing implementations when a canonical component already exists.

## 0.2 Record a reproducible baseline

Where supported, measure and record:

- Time from touch to visible response.
- Time to open an app and return to the desktop.
- Frame pacing, dropped frames, and UI event-loop stalls.
- Idle and interaction CPU consumption.
- Memory consumption and any swapping or memory pressure.
- Keyboard haptic behavior.
- Back-button behavior in at least three different applications.
- Time from selecting Reboot to actual reboot initiation and subsequent boot progress.
- Time from requesting Wi-Fi activation to radio readiness, association, DHCP completion, and usable connectivity.
- Time for each quick-settings control to acknowledge input and complete its action.

Use existing profiling tools where available. Record how each timing was measured and distinguish measurement overhead from the actual result.

Do not invent baseline values. If a measurement cannot be obtained, record that limitation and use logs or targeted instrumentation to locate the bottleneck.

---

# PHASE 1 — PERFORMANCE: MAKE THE WHOLE PHONE FEEL IMMEDIATE

## 1.1 Profile before optimizing

Trace the main UI path from physical input to the resulting visual update.

Identify actual causes of sluggishness, such as:

- Blocking operations on the UI thread.
- Synchronous filesystem access or subprocess execution during interaction.
- Slow application discovery or metadata scanning.
- Repeated reparsing or reconstruction of the same UI state.
- Unnecessary layout recalculation or complete-screen redraws.
- Excessive timers, polling, or repeated health checks.
- Duplicate event handlers.
- Excessive logging in hot paths.
- Unnecessary image decoding or asset loading during interaction.
- CPU-heavy animations or continuous rendering while the screen is idle.
- Startup tasks competing with user interaction.
- Memory pressure, excessive allocations, garbage collection, or process churn.
- Excessive service restarts or competing background workers.
- Network calls that block quick-settings controls.
- Unnecessary IPC round trips or subprocess startup overhead.

Do not assume any one cause without evidence. Profile the actual architecture and fix the bottlenecks it reveals.

## 1.2 Prioritize the user's perception of speed

Optimize in this order:

1. Touch and button input response.
2. Immediate feedback when an action is accepted.
3. Stable frame pacing and reduced visible stutter.
4. Fast app switching, minimizing, and returning home.
5. Responsive scrolling, keyboard interaction, and menus.
6. Fast quick-settings interaction.
7. Background initialization that does not interfere with foreground use.
8. Idle efficiency and memory stability.

The UI must not freeze while performing a slow operation. Where an operation genuinely takes time, acknowledge the input immediately and update the result when the operation completes. Do not falsely indicate that the operation itself has already succeeded.

## 1.3 Preserve the 8-bit arcade design

Nuxel should remain visually distinctive without requiring expensive effects.

Prefer:

- Pixel-art assets and existing optimized sprites.
- Lightweight transitions.
- Simple transforms or opacity changes where the rendering backend supports them efficiently.
- Reuse of decoded images and cached metadata.
- Small, predictable redraw regions where practical.
- Reduced unnecessary animation and rendering when the screen is idle.
- Consistent animation durations and frame pacing.
- Efficient event-driven updates instead of excessive polling.

Avoid introducing:

- Large blurred backdrops.
- Full-screen transparency layers where not necessary.
- Repeated expensive image filters.
- Continuous animation loops for static elements.
- Full-screen redraws for every small status change.
- New graphical dependencies solely for decorative effects.

Do not remove useful animations blindly. Retain the animations that contribute to Nuxel's personality, but ensure they do not interfere with input or performance.

## 1.4 Startup contention and background work

Inspect whether startup services, hardware detection, app discovery, Wi-Fi initialization, status polling, and UI rendering are competing for resources.

Separate critical readiness from noncritical initialization. Start essential interaction paths as early as is safely possible and defer unrelated work when appropriate.

Do not delay the UI until every background service is ready.

Do not use arbitrary sleep calls as synchronization. Use actual service readiness, events, or bounded state transitions.

Do not start multiple copies of a service to make it seem faster. Check for duplicate processes, duplicated timers, and repeated initialization.

## 1.5 Performance acceptance criteria

After optimization:

- The UI remains interactive during background initialization.
- Touch and button actions do not wait for unrelated filesystem, network, or subprocess work.
- No new sustained CPU usage is introduced to maintain cosmetic smoothness.
- Memory usage remains stable during repeated app switching.
- Animations remain lightweight and do not block input.
- No functionality is sacrificed merely to improve a benchmark.
- Before/after measurements are included wherever practical.

If a particular improvement is impossible because of the current rendering backend, driver, or hardware, document the limiting factor rather than hiding it.

---

# PHASE 2 — RESTORE REAL KEYBOARD HAPTIC FEEDBACK

## 2.1 Trace the complete haptic path

The keyboard currently does not provide the expected physical vibration on keypresses.

Investigate the entire path:

1. Does the keyboard emit the expected keypress callback or input event?
2. Is the haptic setting enabled, if such a setting exists?
3. Does the keyboard invoke the intended haptic API or service?
4. Does the service exist and run under the expected user or system account?
5. Are permissions, device nodes, udev rules, or D-Bus access preventing access?
6. Does the relevant Linux input device expose a supported force-feedback or vibration capability?
7. Does the device have an appropriate vibrator driver and a functioning hardware control path?
8. Are the necessary kernel interfaces and device-tree configuration present in the existing kernel?
9. Are errors being swallowed or incorrectly reported as success?
10. Is the haptic request being throttled, canceled, or overwritten by another component?

Inspect available hardware interfaces before choosing an implementation. Do not assume a generic Android vibrator API is available on this Linux system.

## 2.2 Implement the correct hardware integration

Use the existing Nuxel haptic abstraction if it is functional. If it is broken, repair it rather than introducing a competing system.

If no abstraction exists, implement a small, well-defined haptic interface appropriate for the actual hardware and current userspace.

Requirements:

- A real keypress should produce a short, subtle physical vibration.
- Haptic requests must not block the keyboard's input path.
- Repeated keypresses must not create a backlog of delayed vibrations.
- Rapid typing must remain responsive.
- The implementation must handle missing hardware or permissions gracefully.
- Do not create a fake vibration animation or a status indicator that claims success without hardware feedback.
- Avoid excessive vibration intensity or duration.
- Keep haptics isolated so they can be disabled through a setting if Nuxel already supports that preference.

Do not change the kernel or flash anything in this mission. If the existing kernel or hardware configuration lacks the required support, report the exact missing capability and the evidence supporting that conclusion.

## 2.3 Test

Test:

- Individual keypresses.
- Rapid typing.
- Repeated presses and key holds.
- Keyboard dismissal and reopening.
- Haptic service restart or failure.
- Typing while CPU usage is elevated.
- Behavior when haptics are disabled, if supported.

Confirm actual physical vibration on the S10+. A successful API call alone is insufficient.

---

# PHASE 3 — FIX THE GLOBAL BACK BUTTON AND APP LIFECYCLE

## 3.1 Reproduce the exact failure

The bottom navigation bar contains Back, Home, and Tabs.

Current Back behavior is incorrect:

- In the browser, Back appears to minimize the browser.
- In other applications, pressing Back causes the four bottom desktop apps to move over the foreground app instead of properly dismissing or minimizing it.

This suggests that the Back action may be incorrectly routed to desktop layout logic, that app and desktop state are mixed, or that the app lifecycle and navigation history are not properly separated.

Inspect the actual implementation. Do not merely change icon positions, z-index values, or animation order to hide the issue.

## 3.2 Establish distinct navigation semantics

Implement or repair a single authoritative navigation controller with clearly separated actions.

**Back:**

1. If the foreground application has an internal navigation stack and can handle Back, dispatch Back to that application.
2. If an overlay, dialog, menu, or other dismissible transient UI is active, dismiss the appropriate topmost element according to the established interaction model.
3. If the application has no further internal Back action, follow Nuxel's intended app-level Back policy.
4. If that policy is to minimize the application, minimize it correctly and restore the desktop without moving desktop icons over the application.
5. If no app is foregrounded, Back must not corrupt desktop layout or create duplicate app instances.

Do not assume every app should behave identically internally. The navigation controller should honor an application's legitimate Back handler before applying a default app-level action.

**Home:**

- Return to the primary desktop.
- Minimize or background the foreground app using the existing app lifecycle mechanism.
- Preserve application state where intended.
- Restore the proper desktop and dock layout.
- Never confuse Home with an internal Back action.

**Tabs:**

- Open the intended task/app switcher.
- Display actual running or retained applications according to Nuxel's app model.
- Allow selecting an app without creating duplicate instances.
- Keep foreground/background state consistent.

If Nuxel already has a documented navigation contract, preserve it and fix the implementation. Do not invent a new UX model unnecessarily.

## 3.3 Fix the underlying state and rendering bug

Inspect:

- App registry and foreground-app state.
- App window or view ownership.
- Desktop z-order and visibility.
- Dock and bottom navigation z-order.
- Minimize and restore methods.
- Back-event propagation.
- App-specific navigation handlers.
- Duplicate event listeners.
- State updates that occur before or after animations.
- Race conditions during rapid repeated input.
- Whether desktop shortcuts are being rendered in the wrong layer or incorrectly rebound to the foreground app.
- Whether the browser has a special-case implementation that other apps do not use.

The desktop, dock, navigation bar, and application view must remain separate layers with deterministic ownership and visibility.

A minimized app must not remain above the desktop. Desktop icons must never be moved or duplicated to simulate minimization.

If the UI uses a WebView or web-based event system, inspect event propagation, focus, default browser behavior, and duplicate handlers. If it uses another toolkit, investigate its corresponding navigation and focus mechanisms instead.

## 3.4 Regression tests

Test Back, Home, and Tabs from:

- Browser.
- Files.
- Settings or quick settings.
- Contacts or another ordinary application.
- A dialog or nested application view.
- The keyboard-open state.
- A slow-loading app.
- An app that has been opened, minimized, restored, and switched repeatedly.

Also test rapid repeated Back/Home/Tabs presses.

Pass conditions:

- Back never moves the four desktop apps over the foreground application.
- The foreground app's state is correct after navigation.
- The desktop remains usable.
- No duplicate app instances appear unexpectedly.
- Dock and navigation bar remain in their correct layers.
- No navigation action hangs the UI.
- Browser behavior remains correct without being a special-case substitute for global navigation.

---

# PHASE 4 — ELIMINATE THE REBOOT BLACK-SCREEN DELAY

## 4.1 Reproduce and time the full sequence

When Reboot is selected in the power menu, the phone often goes to a black screen for approximately one or two minutes before it actually starts rebooting.

Determine precisely what happens during that interval.

Record separate timestamps for:

1. Reboot selected.
2. Reboot request accepted.
3. Shutdown/reboot command executed.
4. UI shutdown or display blanking.
5. systemd shutdown sequence begins.
6. Any blocking service or process stops.
7. Filesystems and other system resources are prepared for shutdown.
8. Kernel reboot is initiated.
9. Hardware begins the next boot.
10. Nuxel boot UI and lockscreen become available.

Use available logs and timestamps, including systemd journal output, unit stop times, kernel messages, and power-menu/application logs.

Determine whether the long black screen is caused by:

- The UI going black too early.
- A blocking subprocess or shell wrapper.
- A service waiting indefinitely or hitting a long timeout.
- A stuck shutdown hook.
- A NetworkManager or Wi-Fi shutdown delay.
- A filesystem or mount teardown issue.
- An app or background worker that does not terminate.
- A command that waits for the wrong process.
- Incorrect reboot authorization or D-Bus handling.
- A bootloader or hardware transition delay.

These are hypotheses to investigate, not presumed causes.

## 4.2 Fix the root cause

Inspect the power-menu reboot implementation and trace the actual command path. Check for nested scripts, duplicate reboot requests, synchronous waits, arbitrary sleep calls, and UI logic that waits for an event that never arrives.

Use the existing system reboot mechanism with appropriate privileges and error handling. Avoid replacing a correct systemd reboot flow with a dangerous direct kernel command.

The UI should acknowledge the reboot request promptly. It must then communicate the true state as well as the existing design allows.

Do not keep the screen black while a long-running pre-reboot operation is silently blocking. If the display must be blanked, provide a clear reason and meaningful progress where technically feasible.

Do not bypass essential filesystem synchronization, clean unmounting, critical service shutdown, or security checks just to reduce the time.

Do not shorten every systemd service timeout indiscriminately. Identify the specific blocking unit or process and correct its behavior.

If the actual delay occurs inside a hardware or firmware stage that cannot safely be changed in this mission, separate it from the userspace delay and document the evidence.

## 4.3 Error handling and safety

- If the reboot request fails, report the error and preserve a usable UI where possible.
- Prevent accidental multiple simultaneous reboot requests.
- Do not leave the UI permanently disabled if authorization or command execution fails.
- Preserve recovery and console access.
- Do not modify bootloader settings or firmware.
- Do not silently force-kill essential services.

## 4.4 Reboot tests

Perform multiple controlled reboot tests when the device is available.

Measure the time from selection to actual reboot initiation, and the total time to the next usable lockscreen. Report these separately.

Also test shutdown/reboot when Wi-Fi is connected and when applications are open. Compare the logs to establish whether the same bottleneck remains.

The acceptance criterion is the removal of the unexplained one-to-two-minute black-screen delay, not a promise that every hardware boot stage can be instantaneous.

---

# PHASE 5 — FIX WI-FI STARTUP, AUTOCONNECT, AND QUICK-SETTINGS READINESS

## 5.1 Investigate the actual S10+ networking stack

Wi-Fi can take a long time to become usable after Nuxel has booted. The UI may remain on “Wi-Fi unavailable,” then suddenly show a working connection several minutes later.

Investigate the complete path:

- Physical Wi-Fi device discovery.
- Kernel driver and device binding.
- Firmware loading and firmware readiness.
- rfkill state and unblock operations.
- NetworkManager startup and device management.
- Supplicant/backend readiness and communication.
- Scanning and access-point discovery.
- Saved connection profiles and autoconnect priority.
- Association and authentication.
- DHCP address acquisition.
- Route, DNS, and connectivity checks.
- Nuxel quick-settings state synchronization.

The current S10+ environment has previously shown a NetworkManager failure resembling:

`org.freedesktop.NetworkManager.Device.SpecificObjectNotFound: access point ... was not in scan list`

There has also been a prolonged “Associating DHCP...” state. Check whether either issue remains in the current build and determine whether they share a cause.

Inspect the actual hardware identity, kernel logs, loaded modules, firmware files, device binding, rfkill state, NetworkManager version, configuration, and service logs. Do not assume the device uses a particular chipset or firmware file until verified.

The existing kernel is old, but **do not upgrade or replace it as part of this mission**. First determine whether the problem is caused by userspace initialization, firmware packaging, driver binding, rfkill, service ordering, scan races, or another fixable issue.

## 5.2 Trace the timeline

Collect timestamps for:

1. Nuxel UI ready.
2. Wi-Fi service requested.
3. Physical Wi-Fi device discovered.
4. Driver bound.
5. Firmware loaded and device ready.
6. rfkill checked and device unblocked, if required.
7. NetworkManager reports Wi-Fi enabled.
8. Scan begins and completes.
9. Target access point appears in the scan results.
10. Association/authentication succeeds.
11. DHCP completes.
12. Route and DNS are available.
13. Nuxel reports connected and usable.

Compare successful and failed attempts.

Determine whether the long delay comes from the hardware driver, missing/late firmware, service dependencies, repeated scans, a stale access-point object, authentication retries, DHCP timeout/retry, connectivity checks, or incorrect UI state handling.

## 5.3 Correct startup ordering and readiness

Ensure the Wi-Fi UI distinguishes meaningful states, for example:

- Wi-Fi disabled.
- Wi-Fi being enabled.
- Hardware or driver not ready.
- Scanning.
- Connecting.
- Obtaining network configuration.
- Connected.
- Connection failed, with an actionable reason.

Use the project's existing terminology and UI conventions if these states already exist.

Do not mark Wi-Fi unavailable merely because NetworkManager has not finished initialization if the hardware is still starting. Conversely, do not report Connected until the network is genuinely connected.

Use the authoritative networking API and event-driven state updates where possible. Avoid repeated subprocess polling and arbitrary sleeps.

If the hardware is not yet ready, use bounded readiness checks or existing NetworkManager signals rather than attempting connection against a nonexistent or stale access-point object.

Do not create competing Wi-Fi management systems. NetworkManager should remain authoritative if it is the system's designated manager.

## 5.4 Firmware and driver investigation

Check whether:

- Required firmware is installed and present at the expected path.
- Firmware loading errors appear in the kernel log.
- The driver binds promptly or repeatedly resets.
- The device remains blocked by rfkill.
- Wi-Fi power-management behavior causes the delay.
- A module or device initialization race exists.
- Multiple components attempt to control the radio.
- NetworkManager or the supplicant is restarted unnecessarily.
- Startup services wait for connectivity in a way that blocks unrelated UI initialization.

Make only evidence-based changes.

Do not download random firmware, change kernel modules blindly, disable security checks, or alter unrelated modem/Bluetooth components.

If a specific firmware file or driver feature is missing, document the exact finding and whether it can be resolved safely within the existing userspace and kernel.

## 5.5 Autoconnect reliability

Test saved network profiles and ensure autoconnect starts when the actual Wi-Fi device becomes ready.

Avoid:

- Repeatedly attempting to connect before a scan has completed.
- Using stale access-point identifiers after a new scan.
- Recreating saved profiles on every boot.
- Restarting NetworkManager whenever the UI reports a delay.
- Infinite retry loops.
- Blocking the UI until the connection succeeds.
- Losing the user's saved credentials or network settings.

Use bounded retries with appropriate backoff and clear error reporting where necessary.

When a connection fails, the user must be able to retry without rebooting the entire phone.

## 5.6 Quick-settings functions

The same perceived delay affects more than Wi-Fi.

Inventory every quick-settings control in the current implementation. Determine which controls are slow because of shared initialization, synchronous command execution, blocking IPC, excessive polling, or incorrect readiness assumptions.

For each control:

1. Trace the click/event path.
2. Identify the authoritative system API or service.
3. Measure the immediate response and the actual operation duration.
4. Remove unrelated waits from the input path.
5. Acknowledge input immediately.
6. Update the control from actual operation state.
7. Report errors and provide a retry path.

Do not assume every toggle is a Wi-Fi issue. Test the other controls individually.

Do not create a fake fast UI that changes a switch visually before knowing whether the requested action was accepted. Optimistic UI updates are acceptable only if they are clearly reversible and reconciled with the authoritative state.

A slow hardware operation may still take time, but the quick-settings interface must remain interactive and accurately communicate its progress.

## 5.7 Wi-Fi and quick-settings acceptance tests

Test cold boot, warm reboot, manual Wi-Fi activation, automatic reconnection, and repeated toggling.

Include:

- A previously saved network in range.
- A network that is not in range.
- A failed connection followed by retry.
- A slow or failed DHCP response where safely reproducible.
- Rapid toggling of Wi-Fi.
- Opening and closing quick settings during initialization.
- Navigating away from quick settings while a connection is pending.
- Testing other quick-settings functions while Wi-Fi is connecting.

Record actual times and relevant logs. Do not promise a fixed number of seconds unless repeated measurements support it.

Pass conditions:

- Wi-Fi readiness is detected correctly.
- Autoconnect begins when the device is genuinely ready.
- A stale scan result does not permanently prevent connection.
- The UI does not remain stuck on “Wi-Fi unavailable” after Wi-Fi is operational.
- The phone does not require several minutes of unexplained waiting before the connection works.
- Other quick-settings controls remain responsive while Wi-Fi is initializing.
- Failures are recoverable without a full reboot.

---

# PHASE 6 — CROSS-SYSTEM RACE CONDITIONS AND REGRESSIONS

Once the individual fixes are implemented, look for interactions between them.

For example:

- Does a CPU-heavy startup task cause slow keyboard or navigation input?
- Does Wi-Fi initialization block the UI event loop?
- Does the power menu wait for NetworkManager shutdown?
- Does app minimization trigger unnecessary application restarts?
- Does the haptic service block keypress handling?
- Do quick-settings timers keep running after the panel is closed?
- Do repeated app switches leak memory or create duplicate processes?
- Does a reboot request leave a background worker waiting indefinitely?

Fix shared root causes where appropriate rather than adding separate workarounds to each symptom.

Do not merge unrelated behavior into one giant handler or introduce a global lock that serializes every interaction.

Maintain clear ownership of state and use appropriate asynchronous boundaries.

---

# PHASE 7 — IMPLEMENTATION QUALITY

For every fix:

1. Identify the relevant source files and the failure mechanism.
2. Record the baseline behavior.
3. Implement the smallest reliable architectural fix.
4. Add a regression test where practical.
5. Run relevant existing tests.
6. Inspect logs and errors after testing.
7. Check for regressions in related functionality.
8. Document deployment and rollback.

Avoid:

- Broad refactors unrelated to these goals.
- Replacing working components merely to simplify implementation.
- Suppressing exceptions instead of fixing the cause.
- Infinite loops or high-frequency polling.
- Arbitrary sleeps used as synchronization.
- Duplicate event handlers or services.
- UI-only fixes for system-level problems.
- Claims of physical-device validation without physical-device evidence.

If a necessary change is outside the safe scope of this mission, complete all safe parts first and clearly identify what remains.

---

# PHASE 8 — REQUIRED TEST MATRIX

Create a test matrix with these columns:

- Test ID.
- Scenario.
- Preconditions.
- Action.
- Expected behavior.
- Actual behavior.
- Pass/fail.
- Evidence or log reference.

At minimum, cover:

### Performance
- Cold start to usable lockscreen.
- UI interaction during background initialization.
- Repeated app launch and minimization.
- Rapid navigation.
- Repeated scrolling and keyboard use.
- Memory stability across repeated app switching.
- Idle CPU usage.

### Keyboard haptics
- Single keypress.
- Rapid typing.
- Repeated keypresses.
- Haptics disabled, if supported.
- Haptic service unavailable.
- Physical vibration confirmed on hardware.

### Navigation
- Back inside an app.
- Back when no internal history remains.
- Home from an ordinary app.
- Tabs/app switching.
- Dialog dismissal.
- Keyboard-open navigation.
- Repeated rapid Back/Home/Tabs input.
- Browser regression test.
- Desktop/dock layering test.

### Reboot
- Reboot from the power menu.
- Reboot with apps open.
- Reboot while connected to Wi-Fi.
- Reboot after a quick-settings operation.
- Multiple controlled runs with timing evidence.
- Failed or denied reboot request where safely testable.

### Networking and quick settings
- Cold-boot Wi-Fi initialization.
- Saved-network autoconnect.
- Manual Wi-Fi activation.
- Retry after connection failure.
- Access-point scan/association handling.
- DHCP completion and usable connectivity.
- Wi-Fi toggling during initialization.
- Other quick-settings controls during Wi-Fi startup.
- Accurate error states and retry behavior.

Use automated tests for state transitions and event routing wherever possible. Physical hardware tests remain necessary for actual vibration and real radio behavior.

---

# PHASE 9 — DEPLOYMENT AND ROLLBACK

Inspect the project's established build and deployment process before executing it.

- Preserve existing local changes.
- Do not overwrite unrelated user work.
- Back up configuration files before modification.
- Build and run the relevant tests.
- Deploy only using the established safe method.
- Preserve a working console or recovery route.
- Avoid destructive operations.
- Do not flash a kernel, firmware, or partition.
- Verify that the deployed version is the version that was tested.

If the phone cannot safely be reached or the current deployment method is unclear, stop before the risky step, complete non-destructive testing, and provide exact safe deployment instructions.

---

# PHASE 10 — REQUIRED FINAL REPORT

Save a detailed report to:

`docs/pwnage-35000.md`

If the project uses an established evidence directory, also store relevant logs and test output under:

`docs/beta-finalization/live/evidence/pwnage-35000/`

Do not create fake evidence or claim that files exist if they were not generated.

The report must include:

## A. Root-cause summary
- One entry for each of the five priority areas.
- The actual root cause, if established.
- The evidence supporting the diagnosis.
- Any unresolved hypotheses.

## B. Changed files
- File paths.
- Purpose of each change.
- Important behavioral or architectural decisions.

## C. Before-and-after results
Include measured values where available:

- Input latency and UI responsiveness.
- CPU and memory usage.
- App switching and navigation.
- Haptic behavior.
- Reboot initiation and total reboot timing.
- Wi-Fi activation, association, DHCP, and usable connectivity.
- Quick-settings response times.

Clearly distinguish measured results from estimates.

## D. Tests
- Tests run.
- Pass/fail results.
- Physical-device tests performed.
- Automated tests performed.
- Relevant logs and evidence references.

## E. Deployment status
- Whether the changes were built.
- Whether the tests passed.
- Whether the changes were deployed.
- Which version or commit is running.
- Any steps that remain for the user.

## F. Remaining blockers
For every unresolved issue, explain:

- What is still broken.
- Why it remains unresolved.
- What evidence supports that conclusion.
- Whether the limitation is in the UI, userspace, firmware, driver, kernel, or hardware.
- The safest next step.

## G. Rollback
Provide the exact rollback procedure for the changes made.

---

# DEFINITION OF DONE

PWNAGE-35000 is complete only when the evidence supports all applicable items below:

- [ ] The phone is measurably more responsive, with fewer stalls and smoother input handling.
- [ ] The lightweight 8-bit design is preserved without expensive visual effects.
- [ ] Keyboard keypresses produce real, physical haptic feedback on the S10+.
- [ ] Back works correctly across applications and no longer moves the four desktop apps over the foreground app.
- [ ] Home, Tabs, app minimization, and restoration maintain consistent app and desktop state.
- [ ] The unexplained one-to-two-minute black-screen delay during reboot has been eliminated or its exact non-fixable cause has been established with evidence.
- [ ] Wi-Fi initialization and autoconnect are reliable, with no unexplained multi-minute delay.
- [ ] Wi-Fi scanning, association, DHCP, and connectivity states are correctly represented.
- [ ] Quick-settings controls respond immediately to input and remain interactive during slow operations.
- [ ] Relevant regression tests pass.
- [ ] Physical-device validation is explicitly documented.
- [ ] Deployment and rollback status are clear.
- [ ] No kernel, firmware, bootloader, or partition flashing was performed as part of this mission.

**Final instruction:** Prioritize correctness and responsiveness over superficial speed. Find the real causes, fix them at the right layer, and prove the results. Nuxel should feel like a lightweight, responsive arcade-style Linux phone, not a heavy desktop environment squeezed onto a phone and not a UI that looks responsive while the underlying system is still stuck.
