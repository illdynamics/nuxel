# PWNAGE-34000 — NUXEL CONNECTION MODES, CONSOLE DETECTION & INTERFACE RELIABILITY

**Project:** Nuxel Linux phone OS  
**Repository:** `github.com/illdynamics/nuxel`  
**Primary test device:** Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820  
**Known environment:** Fedora-based ARM64 userspace; the running kernel has previously been reported as Linux 4.14.253. Verify the actual runtime rather than assuming it has changed or remained unchanged.

**Mission:** Fix inconsistent bottom navigation rendering, identify active console transports independently, add accurate file-transfer status, introduce a lockscreen connection-mode selector, and implement safe laptop-accessible file transfer.

---

# 0. NON-NEGOTIABLE REQUIREMENTS

Implement all of the following:

1. Back, Home and Tabs navigation icons render correctly and consistently across cold boots and repeated application launches.
2. Console transport icons reflect actual active connections for serial, USB and WLAN, including simultaneous connections.
3. The file-transfer indicator uses `./assets/nuxel-file-transfer.png` and appears only when transfer mode is active.
4. The lockscreen exposes a connection-mode button using `./assets/nuxel-connection-mode.png`.
5. Pressing the button opens a Charging/File Transfer selector.
6. Charging mode preserves normal charging and supported console access.
7. File Transfer mode enables real laptop-to-phone file access through a safe supported protocol.
8. Switching modes updates the actual system state and indicators, not just the UI.
9. Existing USB, serial and WLAN recovery mechanisms remain available wherever technically compatible with the selected USB mode.

## Safety constraints

- Do not flash firmware or partitions.
- Do not replace the kernel or modify the bootloader.
- Do not repartition storage or perform a destructive reset.
- Do not expose an actively mounted writable filesystem as raw USB Mass Storage.
- Do not silently disable a console transport or recovery path.
- Do not report successful activation until the underlying system confirms it.
- Do not invent hardware capabilities, connection state or test results.
- Preserve unrelated user changes and the existing lockscreen design.
- Back up live configuration before changing it and document rollback.
- Never leave the phone in a state where a failed USB mode switch disables all usable recovery routes.

# 1. INITIAL FORENSIC INVESTIGATION

Before editing anything:

1. Inspect `git status`, branch, HEAD commit, recent commits and relevant diffs.
2. Preserve uncommitted work.
3. Inspect the current lockscreen implementation and how it renders the Nuxel logo, connection indicators, charging state and bottom navigation.
4. Locate the source assets for Back, Home and Tabs. Determine whether the navigation bar uses PNGs, SVGs, fonts, CSS drawing, native widgets or a mixture.
5. Locate the existing USB-connected, charging and live-console indicators.
6. Locate the console startup services and their transport configuration.
7. Inspect the actual USB gadget implementation, including configfs or legacy gadget configuration if used.
8. Determine the running kernel's available USB gadget functions and relevant configuration options.
9. Inspect the storage layout, mounted filesystems, user home directory, and whether any dedicated storage volume can safely be exported.
10. Identify the current charging-mode implementation and any existing low-power or cable-connected behaviour.
11. Review previous USB, networking, touch and boot regressions before modifying shared components.
12. Record a baseline of working connections and existing indicator behaviour.

Create the evidence directory:

`docs/beta-finalization/live/evidence/pwnage-34000/`

Record sanitized diagnostic output, test results and relevant before/after screenshots where available.

Do not assume that an icon is broken because its artwork is bad. First establish whether the defect originates in the source asset, asset loading, transparency, rendering, layout, scaling, caching or asynchronous startup.

---

# 2. FIX A — CONSISTENT BACK, HOME AND TABS ICON RENDERING

## 2.1 Reproduce the intermittent defect

The three-button navigation bar sometimes displays visibly corrupted artwork: the Back arrow may be incomplete, outlines may be missing, or parts of an icon may look chopped away. Other boots display the same icon correctly.

Investigate whether the variation correlates with:

- Cold boot versus warm restart.
- First rendering versus subsequent rendering.
- Different screen dimensions or display scaling.
- GPU/compositor initialization timing.
- Theme initialization.
- Asynchronous asset loading.
- Cached or stale assets.
- Different rendering paths used during boot.
- CSS clipping, masking or overflow.
- Transparent pixels or incorrect alpha handling.
- Incorrect intrinsic dimensions or device pixel ratio.
- Repeated scaling and resampling.
- Race conditions between layout calculation and asset readiness.
- Incorrect icon state changes during navigation transitions.

Reproduce the problem when possible and capture evidence before changing anything.

## 2.2 Audit the actual artwork

Inspect the current canonical assets for Back, Home and Tabs.

Check:

- File format and dimensions.
- Alpha channel and transparency.
- Whether the artwork is already cropped in the source file.
- Whether the visible drawing touches the image boundary.
- Whether the intended icon is different from an older duplicate.
- Whether the source contains unexpected transparent regions.
- Whether different app contexts reference different asset versions.

Do not arbitrarily replace the artwork with a generic icon set or redraw the Nuxel navigation design.

If the canonical source artwork is valid, preserve it and fix the rendering path.

If the source itself is defective, recover the intended artwork from Git history or other existing canonical assets before creating a replacement.

## 2.3 Establish one deterministic rendering path

Implement a single authoritative asset and rendering path for the three navigation icons.

Requirements:

- All navigation contexts reference the intended canonical assets.
- Use consistent intrinsic dimensions, aspect ratio and scaling.
- Preserve alpha transparency correctly.
- Prevent unintended clipping by parent containers or masks.
- Avoid repeated resampling and unnecessary conversions.
- Ensure icons are not rendered before their dimensions and asset data are available.
- Prevent stale cached assets from overriding the current canonical assets.
- Ensure theme or display changes cannot leave the navigation bar in a partially initialized state.
- Keep hit targets independent from decorative icon dimensions.
- Keep the navigation controls aligned and accessible.
- Preserve existing Home, Back and Tabs functionality.

If an asset fails to load, use a deliberate fallback that remains legible and functional. Do not leave partially rendered or broken image fragments.

Avoid random cache-busting, arbitrary boot delays and forced redraw loops as permanent solutions.

## 2.4 Rendering and regression tests

Test:

- Cold boot.
- Warm restart where safe.
- Repeated lock/unlock.
- Repeated app opening and closing.
- Browser, Camera, Weather and other app contexts.
- Display resizing or rotation where supported.
- Theme changes if applicable.
- Asset-load failure.
- Slow asset loading.
- Repeated navigation transitions.

Where possible, automate screenshots and compare the visible icon region against a known-good baseline. Use sensible tolerance for anti-aliasing differences; do not require identical GPU pixels when the rendering environment varies.

Report whether the defect was reproduced and what evidence identifies the root cause.

**Acceptance criterion:** The same canonical navigation icons render fully and consistently across tested boots and UI contexts, without broken outlines or cropped artwork.

---

# 3. FIX B — REAL-TIME CONSOLE TRANSPORT DETECTION

## 3.1 Required assets

Use the supplied assets:

- Serial console: `./assets/nuxel-console-serial.png`
- USB console: `./assets/nuxel-console-usb.png`
- WLAN console: `./assets/nuxel-console-wlan.png`

Do not invent alternative filenames. Confirm that the assets exist and are valid before integrating them.

## 3.2 Required behaviour

Show the relevant icon whenever its corresponding live console transport is actually active.

Examples:

| Actual connection state | Expected console indicators |
|---|---|
| Serial console only | Serial icon |
| USB console only | USB icon |
| WLAN console only | WLAN icon |
| WLAN and serial | WLAN and serial icons |
| USB and serial | USB and serial icons, if both are active |
| USB, WLAN and serial | All three icons, if all are active |
| No live console | No transport-specific console icons |

The existing generic live-console indicator must continue to work according to its existing meaning. The new icons supplement it by identifying transport types.

The existing charging and computer-connected indicators must remain independent.

## 3.3 Determine what counts as connected

Do not infer an active console merely from:

- A configured service file.
- A network interface being present.
- A WLAN interface having an IP address.
- USB being physically connected.
- A serial device node existing.
- A console service being installed.
- A service having started in the past.

Determine the real connection semantics for each transport.

### Serial

Inspect the actual serial console configuration and session handling. Depending on the implementation, distinguish between an available serial device, a listening service and an established active console session.

### USB

Inspect the actual USB console function and its runtime state. Determine whether the relevant USB gadget function is configured, bound and available to the host, and whether a live console session is active.

USB physical connection, USB charging and USB console availability are related but different states.

### WLAN

Inspect the configured WLAN console server, listener and session tracking. Determine whether an active authenticated console session exists or whether the product intentionally defines a live WLAN console as a listening, reachable service.

Use the project's actual intended definition and document it. If the existing design considers a listening endpoint to be active, keep that meaning consistent and do not falsely label it as an established remote session.

## 3.4 Implement a shared connection-state model

Create or extend a central service/module that reports independent transport states, such as:

- `serial_active`
- `usb_active`
- `wlan_active`

Use the actual naming conventions of the project where possible.

Requirements:

- Each transport has an independent state.
- Multiple transports can be active simultaneously.
- One transport disconnecting must not clear another active transport.
- State updates are driven by real service, session or device events wherever possible.
- Reconciliation after startup or a missed event corrects stale state.
- A dead or disconnected session is removed promptly.
- The system handles reconnects and rapid connection changes.
- Failed optional status queries do not crash the lockscreen.
- The UI never treats a configured but unavailable service as a successful connection.

Avoid brittle parsing of human-readable terminal output if a reliable API, socket, system service or structured status source is available.

Avoid polling so frequently that status detection itself contributes to system sluggishness.

## 3.5 Render all active transport icons

Display every active transport icon, not only the last one that connected.

Use a responsive horizontal status row or another compact layout that fits the existing Nuxel design.

Requirements:

- Icons remain legible at phone resolution.
- Multiple icons can appear simultaneously.
- Each icon has a meaningful accessibility label.
- Tooltips or accessible descriptions distinguish Serial, USB and WLAN where supported.
- The row does not overlap the Nuxel logo, battery, time, charging indicator or navigation.
- If space is limited, use a deliberate responsive layout rather than silently suppressing active transports.
- The generic live-console indicator remains logically consistent with the transport-specific indicators.

## 3.6 Tests

Test transitions through:

1. No console active.
2. Serial connects and disconnects.
3. USB console becomes available and disconnects.
4. WLAN console becomes available and disconnects.
5. WLAN and serial active simultaneously.
6. USB and another transport active simultaneously, where supported.
7. All three transports active, where supported.
8. One transport disconnecting while the others remain active.
9. A console service failing to start.
10. A stale session disappearing after a disconnect or timeout.
11. A UI restart while console sessions remain active.
12. A system restart with the relevant console services configured.

Use mocked connection events for automated tests and real transport sessions for hardware verification.

Do not claim simultaneous physical connections were verified unless they were actually tested.

---

# 4. FIX C — FILE-TRANSFER STATUS INDICATOR

## 4.1 Asset

Use:

`./assets/nuxel-file-transfer.png`

Inspect its transparency, dimensions, visual appearance and intended scale. Preserve the original pixel-art style and transparency.

## 4.2 Placement

The preferred placement is immediately beneath the Nuxel text logo if it fits cleanly.

Inspect the actual lockscreen and status-bar layout before choosing.

Compare at least these possibilities:

1. A small indicator beneath the Nuxel logo.
2. An indicator alongside the existing status icons.
3. A dedicated compact row that adapts to the available screen width.

Choose the placement that is visually coherent and does not overlap the logo, clock, lockhead, battery, charging indicator or console icons.

Do not cram the indicator into a row if doing so makes existing indicators unreadable.

Do not move unrelated elements unnecessarily.

## 4.3 State-dependent visibility

The file-transfer icon represents the real file-transfer state, not merely the user's selection in the mode overlay.

Show it when:

- The selected mode is File Transfer.
- The relevant USB transfer service or gadget function has been successfully activated.
- The transfer endpoint is ready according to the chosen implementation.

If the user selects File Transfer but activation fails, show a clear error/status state and do not display the normal active indicator as though the connection succeeded.

If the laptop disconnects, handle the state according to the actual mode design. If File Transfer mode remains selected and the endpoint is still configured, the UI may distinguish “mode enabled, host disconnected” from “host connected”; document the exact semantics and keep the indicator truthful.

Hide or change the indicator when:

- The user switches back to Charging.
- The transfer service stops.
- The transfer endpoint fails.
- The mode is cancelled.
- A required gadget function becomes unavailable.

Avoid stale indicators after reboot or service restart.

## 4.4 Preserve existing status indicators

Do not replace or break:

- Charging indicator.
- USB-connected-to-computer indicator.
- Generic live-console indicator.
- Serial/USB/WLAN transport icons.
- Battery percentage or existing system status.

Define independent state variables for independent concepts. Do not conflate a charging cable, a USB host connection, an active USB console and file-transfer mode into one boolean.

## 4.5 Tests

Verify that the file-transfer icon:

- Is absent in normal Charging mode.
- Appears after successful File Transfer activation.
- Disappears after switching to Charging.
- Updates after service failure or host disconnect according to documented semantics.
- Does not appear on a failed activation.
- Does not overlap other status indicators at supported screen sizes.

---

# 5. FIX D — LOCKSCREEN CONNECTION-MODE BUTTON

## 5.1 Asset and placement

Use:

`./assets/nuxel-connection-mode.png`

This is the connection-mode selector button, not the file-transfer-active indicator.

Inspect the existing lockscreen artwork and interactive layout.

Place the button where it fits the current design. Prefer a position on the right side within comfortable thumb reach if the centre conflicts with the lockhead, clock or primary lockscreen interaction.

Requirements:

- Preserve the existing lockscreen background and lockhead.
- Preserve the lockhead's existing interaction and animation.
- Do not cover the time, essential status icons or unlock interaction.
- Ensure the button has an adequate touch target.
- Provide an accessible label such as “Connection mode”.
- Keep it visible and usable across supported screen dimensions and orientations.
- Do not display desktop navigation controls over the lockscreen unless that is already intended.

## 5.2 Mode selector overlay

Pressing the button opens a compact, mobile-friendly overlay with two clearly differentiated choices:

- **Charging**
- **File Transfer**

The overlay must show the current mode and explain the practical difference without overwhelming the lockscreen.

Use the existing design system and colour palette.

Requirements:

- Clear title and descriptions.
- Distinct selected/current state.
- Clear cancellation or dismissal.
- Touch-friendly controls.
- Correct stacking above the lockscreen content.
- No accidental unlocking or desktop exposure.
- No duplicate overlays after repeated taps.
- Correct behaviour if a mode change is already in progress.
- Accessible focus and labels where supported.

Do not create a decorative overlay whose buttons only change UI state.

## 5.3 Security boundary

The mode selector is a limited system action available from the lockscreen. It must not grant unrestricted access to the phone.

When the phone is locked:

- File Transfer mode must not expose personal files until the intended secure access mechanism is satisfied.
- Charging mode must not unlock the desktop.
- Mode switching must not bypass authentication.
- Sensitive account data must not be placed into the overlay.
- A connected laptop must not gain access to private user storage merely because a cable is connected.

If the existing lockscreen security model cannot safely support unlocked access to personal files, use an authenticated or restricted transfer policy and explain it clearly in the UI.

The mode selector itself must not weaken the existing lockscreen.

---

# 6. FIX E — CONNECTION MODE STATE MACHINE

Implement an explicit, shared mode state rather than a collection of unrelated booleans.

Use the project's existing conventions, but represent at least:

- Current selected mode.
- Mode transition in progress.
- USB host/device connection state.
- Transfer endpoint state.
- Active console transports.
- Charging status.
- Last activation error, if any.

The intended user-facing modes are:

## Charging mode

- Normal charging remains available.
- Existing supported console functionality remains available.
- The file-transfer indicator is not shown as active.
- No storage export is active.
- USB networking or console functions are preserved where compatible with the existing implementation.
- Touch input and ordinary lockscreen use remain available.

## File Transfer mode

- A real supported transfer endpoint is activated.
- The laptop can access the intended phone files.
- The file-transfer indicator reflects the actual service state.
- Charging continues if the USB hardware and selected gadget configuration support it.
- WLAN and serial console sessions remain available.
- USB console is preserved where the gadget supports a compatible composite configuration; otherwise, handle the conflict explicitly and preserve an alternative recovery route.

## Mode transition rules

1. Validate the requested transition.
2. Determine whether the host is connected.
3. Check the required kernel/gadget functions and services.
4. Preserve unrelated console transports.
5. Perform the transition safely.
6. Wait for actual service or gadget readiness, with a bounded timeout.
7. Verify the endpoint state.
8. Update the persisted mode and UI only according to the real result.
9. If activation fails, restore a safe state and report the failure.
10. Avoid leaving the system half-configured.

Do not use long fixed sleeps as a substitute for readiness checks.

Repeated requests must be idempotent. Selecting Charging while already in Charging mode must not disrupt existing services. Selecting File Transfer repeatedly must not create duplicate gadget functions or mount operations.

Handle rapid mode changes and cable removal during activation.

---

# 7. FIX F — REAL LAPTOP FILE TRANSFER AND USB STORAGE

This is the most important safety-critical part of the mission.

The objective is to let the user connect Nuxel to a laptop and access the intended phone files through a normal file manager, while preserving the phone's own filesystem integrity and recovery access.

Do not assume that the existing kernel or gadget configuration supports every USB mode.

## 7.1 Inspect actual USB gadget capabilities

Determine:

- Whether Nuxel uses configfs, legacy gadget setup or another mechanism.
- Which USB device controller and gadget driver are active.
- Which gadget functions are available in the running kernel.
- Whether USB Mass Storage is available.
- Whether MTP or another file-transfer service is installed or supported.
- Whether USB ACM/serial console is active.
- Whether USB networking is in use.
- Whether composite gadget configurations are supported.
- Which USB function combinations work on the actual device.
- Whether charging remains available when data functions change.
- Whether the phone can safely switch configurations without rebooting.

Inspect actual runtime state and kernel configuration where available. Do not infer capability solely from the existence of a configuration file.

Do not compile or replace a kernel in this mission. If a required function is unavailable, report the exact blocker and implement the safest supported alternative.

## 7.2 Understand the difference between Mass Storage and MTP

USB Mass Storage presents a block device to the host. The host typically mounts the filesystem and expects to control filesystem access.

MTP exposes files through a protocol, allowing the phone's filesystem to remain mounted and managed by the phone.

These approaches are not interchangeable at the storage layer.

**Never expose the same writable block device or filesystem to both the phone and laptop as independently writable mounts.** Doing so can corrupt directory metadata, lose writes or damage the filesystem.

In particular, do not expose the active root filesystem, active home filesystem or a mounted loop-backed image as raw Mass Storage.

## 7.3 Preferred implementation decision

Inspect the actual Nuxel storage layout and select the safest implementation.

### Option A — True USB Mass Storage

Use this only if a suitable dedicated exportable volume or backing store is available and can be safely handed off.

Requirements:

- The exported volume is not mounted for writing by Nuxel while the host owns it.
- All local writers are stopped or disconnected before the volume is exported.
- Any filesystem flush and unmount completes successfully.
- The host can detect and mount the exported volume.
- The phone does not continue writing to the same filesystem during host access.
- On disconnect, the host is detached safely and the filesystem is checked or remounted only according to the actual storage design.
- Error handling prevents accidental simultaneous ownership.
- A dedicated partition must not be created by repartitioning the device during this mission.

Do not export the whole active phone storage simply because a block device exists.

If a dedicated safe volume already exists, evaluate whether it can hold the intended transferable files and how those files are synchronized with the user's home directory.

### Option B — MTP or another supported file-transfer protocol

Use this when the intended user files live on a filesystem that must remain mounted and writable by Nuxel.

Requirements:

- The laptop can discover Nuxel through the actual protocol.
- The user can browse and transfer files using a supported host file manager.
- Only intended directories are exposed.
- Filesystem permissions and access controls remain enforced.
- The phone continues managing the filesystem normally.
- The endpoint reports its actual state.
- Host disconnects and interrupted transfers are handled safely.
- The implementation does not depend on an unavailable kernel feature.
- The UI clearly describes the protocol if the user expects a raw mounted disk.

Do not claim MTP is a raw mounted hard disk. It is a file-transfer device that may appear in the host's file manager as a phone or storage device.

### Option C — No safe supported endpoint available

If neither approach is supported without risky kernel or partition changes:

- Do not fake storage activation.
- Do not create a dummy USB disk that does not contain the intended data.
- Do not create a loopback filesystem and present it as the user's full storage.
- Do not change the kernel or repartition storage.
- Report the precise missing capability.
- Complete the safe mode selector and error reporting.
- Preserve Charging mode and all working console access.
- Document the smallest future change that would safely enable the requested behaviour.

## 7.4 Define what “full storage” means

Before implementation, inspect how Nuxel stores user data and identify the intended export scope.

The goal is access to the user's intended files, including appropriate directories such as:

- `~/Desktop`
- `~/Gallery`
- `~/Documents`
- `~/Downloads`
- `~/Music`
- `~/Videos`, if used
- `~/VoiceRecordings`

Do not automatically expose system configuration, secrets, credentials, private application databases or the entire root filesystem.

If the chosen transfer mechanism exports only a subset of files, document the exact scope and why. Do not claim all storage is available if only one dedicated volume is exported.

## 7.5 USB console coexistence

The user currently relies on console access for recovery and development.

Inspect whether the existing USB console and transfer endpoint can coexist in one composite gadget configuration.

If they can coexist safely:

- Preserve the console function.
- Add the file-transfer function without breaking console enumeration.
- Verify that the host recognises both functions.
- Verify that transfer mode does not change unrelated console state.

If they cannot coexist:

- Do not silently replace USB console with Mass Storage.
- Preserve WLAN and serial console access.
- Clearly explain the limitation.
- Use the safest supported configuration.
- Make mode transitions reversible.
- Ensure a failed transition cannot leave the user without a recovery route.

Do not reintroduce the previous USB networking/NCM regression or change unrelated networking functions without evidence.

## 7.6 Host-side verification

Where a laptop is available, test the actual host side.

Verify:

1. Nuxel enumerates over USB in the selected mode.
2. The intended transfer protocol is visible to the host.
3. The laptop can browse the intended files.
4. A test file can be copied from Nuxel to the laptop.
5. A test file can be copied from the laptop to Nuxel if bidirectional transfer is supported.
6. The resulting file contents and sizes match.
7. File changes are visible on the phone after the transfer is completed.
8. The host disconnects without corrupting phone storage.
9. The phone remains usable throughout the process.
10. The user can return to Charging mode.
11. The existing console connections remain functional wherever supported.

Use disposable test files in a designated test directory. Do not test with valuable personal files.

If no laptop is available, run the tests supported by the development environment and mark host-side verification as `BLOCKED`, not `PASS`.

---

# 8. FIX G — CHARGING MODE AND POWER BEHAVIOUR

Charging mode must preserve the existing charging and console behaviour.

Requirements:

- A connected cable can charge the phone.
- Charging detection remains functional.
- The existing charging indicator remains accurate.
- Supported console functions remain available.
- Touchscreen input is not disabled simply because the cable is connected.
- The lockscreen remains usable.
- Selecting Charging disables the file-transfer endpoint safely.
- Any host-owned storage is released before Nuxel resumes ownership.
- USB gadget functions return to the intended safe Charging configuration.
- WLAN and serial consoles are not unnecessarily stopped.
- The file-transfer indicator is cleared only when transfer mode has actually ended.

Do not implement Charging mode by disabling the entire USB subsystem or turning off all data interfaces indiscriminately.

Charging and data mode are separate concerns. Keep the power-management policy independent from the data-transfer policy.

If the cable is unplugged during a transition, move to a safe state and reconcile the actual mode after the device reconnects.

---

# 9. FIX H — RESPONSIVE LOCKSCREEN STATUS LAYOUT

Review the full lockscreen layout with every indicator active at once.

The interface must account for:

- Nuxel text logo.
- Charging indicator.
- USB-connected indicator.
- Generic live-console indicator.
- Serial console indicator.
- USB console indicator.
- WLAN console indicator.
- File-transfer indicator.
- Battery status and percentage.
- Time/date.
- Connection-mode button.
- Lockhead and its existing interaction.

Do not assume only one console transport can be active.

Implement a deliberate responsive layout:

- Keep indicators at a consistent visual scale.
- Maintain adequate spacing and contrast.
- Preserve pixel-art crispness where applicable.
- Avoid overlapping text and artwork.
- Avoid clipping at supported screen sizes.
- Ensure the lockhead and unlock interaction remain usable.
- Do not let indicator expansion push critical controls off-screen.
- Use sensible wrapping, grouping or a second compact row where necessary.

The file-transfer indicator should be near the logo if visually appropriate, but the actual screen layout takes priority over forcing it into a particular position.

Verify the interface using the actual device resolution and any supported rotation modes.

---

# 10. FIX I — PERSISTENCE, RECOVERY AND ERROR HANDLING

Inspect the existing persistence mechanism and choose a safe, consistent policy.

Requirements:

- The selected mode is represented accurately after a service restart.
- Reboot does not falsely claim a transfer endpoint is active before it has been initialized.
- An unplugged host does not leave a stale connected state.
- A service crash clears or reconciles its active indicator.
- A failed mode switch returns to a safe state.
- The UI remains responsive if a gadget operation times out.
- Errors are actionable and do not expose secrets.
- Repeated button presses do not race mode transitions.
- A failed transfer setup does not break charging.
- A failed USB transition does not disable WLAN or serial recovery.
- Existing touch input and lockscreen behaviour remain intact.

Persist the user's preferred mode only if that is consistent with the existing product design and safe boot behaviour. On reboot, distinguish the preferred mode from a successfully active USB endpoint.

Do not blindly reactivate storage export on every boot without checking the connected host, storage ownership and security policy.

---

# 11. TEST PLAN

## 11.1 Navigation rendering

- Cold boot and inspect all three navigation icons.
- Repeatedly lock and unlock.
- Open and close multiple applications.
- Test browser, Camera and Weather.
- Trigger repeated Back, Home and Tabs transitions.
- Test asset-load failure and delayed loading.
- Check for incomplete outlines, clipping and inconsistent scaling.

## 11.2 Console detection

- Serial only.
- USB only, where supported.
- WLAN only.
- WLAN plus serial.
- USB plus serial, where supported.
- All three, where supported.
- Disconnect each transport independently.
- Restart the UI while connections remain active.
- Stop or fail a console service.
- Verify that only genuine active transports are indicated.

## 11.3 File-transfer indicator

- Charging mode: inactive indicator.
- Successful File Transfer activation: visible indicator.
- Failed activation: no false active indicator.
- Switch to Charging: indicator cleared after successful shutdown.
- Disconnect host: state reconciled.
- Restart transfer service: state recovered accurately.
- Verify no overlap with the logo, charging status or console icons.

## 11.4 Mode selector

- Open overlay from the lockscreen.
- Select Charging.
- Select File Transfer.
- Cancel the overlay.
- Tap rapidly and repeatedly.
- Trigger a mode switch with no cable attached.
- Disconnect the cable during activation.
- Test a failed service start.
- Confirm that the desktop never becomes exposed by the mode selector.

## 11.5 Storage integrity

- Verify the chosen storage architecture.
- Verify no active filesystem is exported as a simultaneously writable block device.
- Verify host file discovery.
- Copy disposable test files in both directions where supported.
- Verify file contents.
- Disconnect safely.
- Reconnect and repeat.
- Verify phone storage remains healthy.
- Verify recovery console availability.

## 11.6 Charging and recovery

- Boot with no cable.
- Boot with a cable connected.
- Charge while the phone remains interactive.
- Switch between modes.
- Verify touch input.
- Verify WLAN and serial console.
- Verify USB console where supported.
- Confirm a failed transition does not leave the device inaccessible.

Use automated tests for state transitions and mocked services, plus real hardware tests for USB enumeration, console transport and laptop file access.

Do not substitute mocked tests for physical verification.

---

# 12. IMPLEMENTATION AND DEPLOYMENT

Before editing:

- Record the baseline.
- Preserve unrelated changes.
- Create backups for live configuration.
- Establish rollback steps.
- Keep the changes focused and reversible.

During implementation:

- Use the existing Nuxel architecture.
- Avoid duplicate services and competing state sources.
- Prefer structured status APIs and event-driven updates.
- Keep UI work asynchronous and nonblocking.
- Validate all user-controlled paths and transfer operations.
- Do not introduce arbitrary sleeps or aggressive polling.
- Do not weaken security to make a demo appear successful.

Before deployment:

- Run all relevant tests.
- Run linting and static checks.
- Inspect the final diff.
- Verify asset paths and packaging.
- Validate USB gadget configuration before applying it.
- Ensure the recovery route is available.
- Deploy safe userspace changes to the intended environment.
- Verify the running implementation, not just the build output.

Do not reboot automatically if it could interrupt the only active recovery session. Do not modify partitions, firmware, bootloader or kernel.

---

# 13. EVIDENCE AND FINAL REPORT

Store sanitized evidence under:

`docs/beta-finalization/live/evidence/pwnage-34000/`

Provide a separate result for each major requirement.

## A. Navigation artwork

- Root cause.
- Canonical asset paths.
- Rendering changes.
- Boot and UI contexts tested.
- Before/after evidence.
- Remaining intermittent defects, if any.

## B. Console indicators

- Detection source for each transport.
- Meaning of “active” for each transport.
- Single and simultaneous transport test results.
- Evidence of real connections.
- Any unsupported combinations.

## C. File-transfer indicator

- Placement chosen and why.
- State source.
- Visibility behaviour during activation, failure and disconnect.
- Confirmation that it is not a decorative or manually forced indicator.

## D. Lock-screen mode selector

- Button placement.
- Overlay behaviour.
- Mode transitions.
- Lock-screen security behaviour.
- Error and recovery handling.

## E. USB file transfer

- Actual implementation: Mass Storage, MTP or another supported protocol.
- Why it is safe for the current storage layout.
- Actual host operating system used for testing.
- Device enumeration result.
- Copy-to-phone and copy-from-phone results where supported.
- Evidence that file contents match.
- Evidence that storage remained healthy.
- USB console coexistence results.
- Any missing kernel capability or other blocker.

## F. Charging and recovery

- Charging behaviour.
- Touchscreen behaviour.
- Console access in each mode.
- Recovery route preserved.
- Failed-transition tests.

## G. Deployment

- Changed files.
- Tests run and actual outcomes.
- Deployed version.
- Rollback instructions.
- Any work not completed.

Classify each requirement as `FIXED`, `PARTIALLY FIXED`, `BLOCKED` or `NOT REPRODUCED`.

Do not mark the mission complete if laptop storage access has not been tested on a real host. Distinguish implementation complete from physical verification complete.

# 14. DEFINITION OF DONE

PWNAGE-34000 is complete only when:

- Navigation artwork is consistently rendered and functional.
- All active console transports are identified independently.
- Simultaneous console connections display all applicable icons.
- File-transfer status accurately reflects the underlying service.
- The lockscreen mode selector works without bypassing security.
- Charging mode preserves charging and supported console access.
- File Transfer mode provides genuine, tested host access using a safe supported protocol.
- No mounted writable filesystem is simultaneously exposed as raw writable USB storage.
- The phone remains recoverable if USB mode switching fails.
- Tests, evidence and rollback instructions are supplied.

**Begin with repository and hardware-capability inspection, then implement and verify the complete mission. Do not stop at a plan, a mock-up or an icon that merely looks active.**
