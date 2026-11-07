# PWNAGE-80000 — Nuxel Desktop, Navigation and Application Lifecycle Repair
## Zoom lock, Back/keyboard behavior, invisible overlays, Calendar, Doom, rotated app drawer, power menu and reboot

**Target:** Nuxel on Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**OS:** Fedora-based Nuxel ARM64  
**Deployment:** Wi-Fi SSH, root console  
**SSH identity:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Priority:** Critical  
**TWRP:** Not required for initial work. Do not flash the kernel for userspace problems.

### 1. Connect to the actual phone

Start with Nuxel booted normally.

Discover the current Wi-Fi SSH address from the existing Nuxel deployment/debug scripts, SSH configuration, known_hosts and device diagnostics. Do not invent or guess an address.

Use the existing key:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  root@<DISCOVERED_NUXEL_WIFI_HOST>
```

Verify that the key is readable without displaying its contents. Do not copy the private key to Nuxel.

Preserve SSH host-key verification. Do not disable `StrictHostKeyChecking` to bypass an identity mismatch.

Use the existing `nuxel-live-ssh.sh` Wi-Fi workflow if it is the established way to locate and connect to the phone. Confirm that the remote shell is actually root before making system changes.

Keep the existing Wi-Fi connection working. Do not change networking, sshd or firewall configuration unnecessarily.

### 2. Mission

Fix all the following issues as one coherent desktop/input/application-lifecycle task.

1. Disable gesture-based zoom throughout Nuxel by default.
2. Repair single-press Back behavior.
3. Repair the invisible overlay/input-blocking bug after leaving apps.
4. Implement graceful app closing and explicit force-kill gestures.
5. Fix Calendar navigation buttons and numeric time input.
6. Ensure Back and swipe-down dismiss the keyboard.
7. Ensure force-killing an app also closes its keyboard.
8. Make Nuxel Doom independently installable through NuXtore, including legal WAD handling.
9. Fix the rotated app drawer layout/zoom problem.
10. Fix the temporary blue rectangle after launcher reload, app exit or lockscreen transition.
11. Repair the power menu so every option is genuinely tappable.
12. Prevent duplicate power menus.
13. Fix intermittent power-menu gating.
14. Remove the unexplained 30+ second black screen delay before reboot is issued.

### 3. Audit before editing

Inspect the actual repository and running phone.

Locate the active implementations for:

- Phoc/Wayland desktop shell.
- Home/launcher.
- Lock screen.
- App drawer.
- Settings.
- Quick Settings.
- Navigation dock: Back, Home and Tabs.
- Keyboard/input-method integration.
- Calendar.
- Doom/Nuxel Doom.
- NuXtore.
- Permission manager.
- Power menu.
- Reboot/shutdown backend.
- Framebuffer presentation bridge.

Search for duplicated overlays, gesture handlers, event listeners, navigation state, modal state and process lifecycle implementations.

Do not patch a stale or unused source file. Prove which source is built and deployed.

Back up affected files, preserve user settings and work in a tracked branch or reversible patch set.

### 4. Disable zoom by default everywhere

Disable pinch-to-zoom, double-tap zoom, trackpad pinch zoom, Ctrl+wheel zoom and shell-level zoom gestures in:

- Desktop.
- Lockscreen.
- App drawer.
- Settings.
- Quick Settings.
- Nuxel applications.
- WebKit/PWA applications.
- Other app surfaces managed by the Nuxel shell.

Use a centralized zoom policy with default denial. Prepare the policy integration point for a future Permission Manager `zoom` permission, but do not expose a new permission toggle yet.

Prevent accidental visual scaling or viewport changes after device rotation.

Do not break ordinary scrolling, dragging, touch input, text selection, application controls or accessibility text sizing.

Use appropriate WebKit gesture settings and application viewport configuration. Do not rely on a single CSS `user-scalable=no` rule as the complete solution.

Existing app-level zoom permissions must default to disabled.

### 5. Repair Back behavior

Implement one central Back dispatcher with deterministic precedence:

1. If the keyboard is open, dismiss the keyboard.
2. Otherwise, if the foreground app can navigate back, dispatch Back into that app.
3. If no further Back navigation is possible, request a graceful application close.
4. Never force-kill on a normal single Back press.

For a PWA/WebKit app, respect its actual history stack and modal/navigation state.

For a native app, use its supported window-close or application lifecycle mechanism first. Use a bounded graceful termination fallback if required.

Do not merely hide an app window while leaving an invisible modal layer or input grab behind.

Holding Back must continue to provide the explicit force-kill action for the foreground app.

### 6. Tabs gestures and application lifecycle

Implement the requested gesture model:

- Open Tabs to see running/background applications.
- Swipe left on an app card to request graceful close/stop.
- Show a closing state and allow a bounded grace period.
- If an app remains hung or refuses to stop, swipe right on that app card to force-kill it.
- Force-kill must behave like holding the Back button on the foreground app.

Keep swipe gestures scoped to app cards. Do not turn every horizontal application swipe into a termination action.

Use one process/window lifecycle manager and synchronize its state with the compositor and launcher.

Handle PWA processes, native processes, windows and background activities correctly.

### 7. Fix the invisible overlay bug

The symptom:

- A user leaves an app with one Back press.
- The app appears gone.
- The desktop is visible.
- The app drawer and other desktop controls cannot be opened.
- Holding Back to force-kill the foreground app clears the problem.

Investigate stale:

- Modal overlays.
- Popup surfaces.
- Layer-shell surfaces.
- Full-screen surfaces.
- Input grabs.
- Focus locks.
- Touch/pointer grabs.
- Event-capture overlays.
- Transparent webviews.
- App containers.
- Transition shields.
- Compositor surface ownership.
- Navigation state.

The app close operation must release every associated overlay, keyboard, focus, pointer, modal and compositor resource.

Do not mask the problem by adding a delayed shell reload.

After graceful app exit, the launcher must immediately accept touch and navigation input.

### 8. Keyboard behavior

When the keyboard is visible:

- First Back press closes the keyboard, not the application.
- Swiping down from the top of the keyboard closes it.
- The gesture must work reliably without blocking typing or ordinary keyboard interactions.
- The gesture must not accidentally trigger the system top bar.

When an application is gracefully closed or force-killed:

- Hide the keyboard.
- Release the input method surface.
- Clear stale text-input focus.
- Clear the app's input context.
- Release keyboard-related input grabs.
- Restore desktop input.

Ensure a new application does not inherit stale keyboard state from a killed app.

### 9. Calendar fixes

Calendar must show the Nuxel triple navigation buttons by default:

- Back.
- Home.
- Tabs.

When the keyboard is open, the navigation buttons must still be accessible, including through the requested swipe-up gesture.

Fix time fields to request the numeric/time-entry keyboard instead of the general typing keyboard.

Use the actual Nuxel input-method API and appropriate numeric/time input type. Provide a suitable time keypad that supports the digits and required time separator.

When Calendar is force-killed, its keyboard must close and its input focus must be released immediately.

Test:

- Opening Calendar.
- Switching views.
- Selecting a date.
- Selecting start/end time.
- Entering time.
- Opening and closing keyboard.
- Back navigation.
- Home.
- Tabs.
- Graceful close.
- Force kill.
- Relaunch.

### 10. Nuxel Doom / Chocolate Doom / NuXtore

Inspect the actual Nuxel Doom architecture.

Determine whether Chocolate Doom is:

- A separately exposed application.
- The engine used internally by Nuxel Doom.
- A required runtime dependency.
- A redundant duplicate launcher entry.

Do not blindly uninstall a runtime dependency.

The desired user experience is that Nuxel Doom can be installed completely from NuXtore without requiring the user to discover and separately install Chocolate Doom.

If Chocolate Doom is needed as the engine, package it as a private dependency/runtime of Nuxel Doom or otherwise integrate it invisibly into the user-facing app.

Remove the duplicate standalone Chocolate Doom app entry/package only if it is not required by other applications and Nuxel Doom has its own complete engine dependency.

Ensure NuXtore handles:

- Nuxel Doom application.
- Compatible engine.
- Required runtime libraries.
- WAD selection and installation.
- App icon/desktop entry.
- Controls and small-screen UI.
- Correct launch command.
- Uninstall and upgrade.

WAD licensing must be handled correctly:

- Bundle only WADs that are legally redistributable.
- Check the actual license of Freedoom or any replacement WAD.
- Do not bundle commercial copyrighted DOOM IWADs without permission.
- Provide an import flow for the user's own legally obtained WADs.
- Verify that NuXtore reports exactly which WADs are available and required.

The owner expects the original Doom graphics and a usable mobile interface. Do not replace the original graphics with a simplified pixel-art recreation.

Test a fresh NuXtore installation from an empty app state, not only a development machine with preinstalled files.

### 11. Rotated app drawer

The configured default grid is three columns.

After rotating the phone, the drawer appears zoomed/cropped and some icons are outside the screen.

Fix the actual cause.

Inspect:

- Visual viewport.
- Device pixel ratio.
- WebKit page scale.
- CSS transforms.
- Zoom state.
- Output logical dimensions.
- Safe-area insets.
- Grid width.
- Column configuration.
- Overflow.
- Cached dimensions after rotation.

Preserve the configured three-column default.

After an orientation change, recalculate dimensions and layout. Do not hardcode portrait-only sizing.

Do not fix this by switching to one column or shrinking every icon.

Verify that all icons are visible and correctly touchable in portrait, landscape, reverse portrait and reverse landscape.

### 12. Blue rectangle after reload/exit/lockscreen

A blue rectangle temporarily appears at the top of the display after:

- Reload launcher.
- Leaving an app.
- Entering the lockscreen while the app is stuck.

It disappears after approximately ten seconds.

Investigate:

- Compositor scene graph.
- Stale app surfaces.
- Layer-shell surfaces.
- Popup/overlay cleanup.
- WebKit rendering surfaces.
- CSS transition artifacts.
- Framebuffer damage tracking.
- Partial updates.
- Stale frame buffers.
- Lock-screen transitions.
- Launcher reload ordering.

Capture diagnostic evidence immediately after the event and during the period before it disappears.

Determine which component owns the blue surface or stale region.

Do not add a ten-second timer to hide it.

Do not add arbitrary sleeps or forced full-screen reloads as the primary fix.

Ensure the compositor and framebuffer bridge receive a complete valid redraw after app close, launcher reload, orientation change and lockscreen transition.

### 13. Power menu

Fix both the UI and the actual backend.

Every visible option must be tappable and execute its intended action:

- Restart.
- Power off.
- Suspend, if supported.
- Lock.
- Other existing Nuxel power options.

Inspect why some options intermittently appear gated or unavailable.

Check:

- UI permission state.
- Lock state.
- User identity.
- D-Bus authorization.
- systemd/logind availability.
- Privileged helper state.
- Backend command result.
- Overlay/input blockers.

Do not blindly disable security or authorization checks.

The power menu must have exactly one active instance.

Prevent:

- Duplicate menus.
- Stacked overlays.
- Multiple click handlers.
- Duplicate event listeners.
- Multiple modal roots.
- Old menu instances surviving reload.

Ensure the visible menu receives pointer and touch events and that its options have real backend callbacks.

Do not report an action as successful until the backend accepts it.

### 14. Reboot delay

The phone currently displays a black screen for over 30 seconds before the reboot operation is actually issued.

Determine where the delay occurs:

- Power-menu UI.
- Frontend callback.
- App shutdown.
- Launcher shutdown.
- Privileged helper.
- D-Bus call.
- systemd job.
- Inhibitors.
- Service stop operations.
- Kernel restart sequence.

Add timestamped diagnostics from user selection to reboot request acceptance.

The reboot command must be submitted promptly and correctly through the supported systemd/logind path.

Do not blank the display for 30 seconds before sending the reboot request.

Do not wait synchronously for every application to exit before asking systemd to reboot.

Use bounded graceful shutdown where appropriate.

Do not globally remove all systemd inhibitors or kill critical services.

Make the UI report when the reboot request has actually been accepted.

### 15. Regression tests

Test every area in:

- Portrait.
- Landscape.
- Reverse portrait.
- Reverse landscape.
- With keyboard open.
- With keyboard closed.
- From lockscreen.
- From desktop.
- From app drawer.
- From Settings.
- With a foreground PWA.
- With a foreground native app.
- With an app that has internal Back history.
- With an app that has no Back history.
- With a deliberately unresponsive test app.

Mandatory acceptance:

- [ ] Zoom gestures disabled throughout Nuxel by default.
- [ ] Future Permission Manager zoom policy has a central default-deny integration point.
- [ ] Single Back navigates inside the app first.
- [ ] Back closes keyboard before app navigation.
- [ ] Back gracefully closes an app when no further Back is possible.
- [ ] Holding Back force-kills foreground app.
- [ ] Tabs swipe left gracefully closes app.
- [ ] Tabs swipe right force-kills a hung app.
- [ ] App exit releases every overlay and input grab.
- [ ] Desktop remains interactive immediately after app close.
- [ ] Calendar navigation triple buttons are visible by default.
- [ ] Calendar time fields invoke numeric/time input.
- [ ] Calendar keyboard closes on force kill.
- [ ] Swipe-down dismisses keyboard.
- [ ] Rotated app drawer remains three columns and fully visible.
- [ ] Blue rectangle no longer appears.
- [ ] Power menu is single-instance and clickable.
- [ ] Power options are genuinely functional.
- [ ] Power menu is not intermittently gated without reason.
- [ ] Reboot request is issued promptly.
- [ ] Doom is installable completely through NuXtore.
- [ ] Chocolate Doom is not exposed as a redundant standalone requirement.
- [ ] Doom WAD licensing is respected.
- [ ] Existing native apps continue working.
- [ ] Existing fixed rotation behavior remains intact.

### Deployment and safety

Use the existing Wi-Fi SSH connection and root key.

Do not reflash the kernel for these userspace defects.

Back up modified files and preserve SSH access.

Perform changes in small reversible stages.

Reboot only after verifying that the normal boot path and recovery access remain available.

### Deliverables

- Root-cause report for each issue.
- Modified source files and build/deploy integration.
- Application lifecycle design and tests.
- Keyboard/navigation tests.
- Calendar fixes.
- Zoom policy implementation.
- Doom/NuXtore packaging and licensing report.
- Power menu and reboot diagnostics.
- Full four-orientation regression matrix.

**Definition of done:** Nuxel behaves consistently as a touch-first mobile desktop, with no accidental zoom, no invisible input-blocking surfaces, reliable app lifecycle and keyboard behavior, a functional power menu, correct reboot behavior and a complete NuXtore Doom installation.
