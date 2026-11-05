# FULL PWNAGE-80000 — Nuxel Mobile Desktop Reliability and UX Completion
## System-wide zoom prohibition, navigation/back semantics, application lifecycle, keyboard/input, Calendar, Doom packaging, app drawer geometry, compositor artifacts, power menu and reboot reliability

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**Platform:** Fedora-based Nuxel ARM64, Phoc/Wayland, custom Nuxel desktop and framebuffer presentation bridge  
**Deployment:** Wi-Fi SSH, root console  
**SSH identity:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Priority:** Critical  
**Starting device state:** Nuxel booted normally  
**TWRP required:** No, not for initial work  
**Kernel flash:** Not authorized or expected for these userspace issues  
**Main goal:** Make Nuxel's desktop, navigation, application lifecycle, keyboard, launcher and power controls reliable under normal mobile use.

---

# 0. Executive mission

Repair the current collection of mobile desktop behavior defects and make the shared system architecture reliable.

Do not treat these as isolated visual tweaks.

Several symptoms are likely related to the same underlying problems:

- Back handling is not respecting app navigation history.
- App close does not consistently release the shell's modal/input state.
- Keyboard focus and input-method state survive application termination.
- Transparent or stale surfaces remain above the desktop.
- The launcher and compositor do not always agree about the active app.
- Orientation changes and WebKit viewport scaling leave stale layout geometry.
- Power-menu instances or callbacks are being duplicated or gated.
- Reboot flow appears to hide the display before the actual system reboot request is issued.

The objective is to repair the shared lifecycle, focus, input, overlay and privileged-action mechanisms rather than add unrelated workarounds.

The user-facing outcome should feel like one coherent Nuxel mobile operating system.

The task includes:

1. Disable zoom everywhere by default.
2. Make Back navigate inside the app first.
3. Close an app gracefully only when no further Back action is possible.
4. Preserve explicit force-kill through holding Back.
5. Implement Tabs swipe-left graceful close and swipe-right force-kill.
6. Remove invisible overlays/input grabs after application exit.
7. Fix keyboard dismissal and cleanup.
8. Fix Calendar navigation and numeric time entry.
9. Keep the navigation triple buttons visible in Calendar.
10. Fix the rotated app drawer so all icons are visible in its three-column layout.
11. Fix blue rendering artifacts after reload/exit/lockscreen.
12. Repair power-menu interactions and duplicate instances.
13. Remove intermittent power-menu gating.
14. Fix the delayed reboot request.
15. Package Nuxel Doom fully through NuXtore without requiring a separate user-installed Chocolate Doom application.
16. Preserve existing Nuxel native applications, display, touch, SSH and working rotation.

---

# 1. SSH connection — mandatory first step

The phone must be booted normally into Nuxel.

Do not begin in TWRP.

Connect over Wi-Fi SSH using the exact existing identity.

## 1.1 Required SSH key

Use:

```text
~wicked/.ssh/wicked_wqn_id_rsa
```

Do not generate a new key.

Do not copy the private key to the phone.

Do not print it or include its contents in logs.

## 1.2 Discover the current phone address

Do not invent an IP address or assume the previous address is still valid.

Discover the current Wi-Fi SSH host using:

- Existing SSH config.
- Existing known_hosts entries.
- Existing deployment scripts.
- Nuxel debug scripts.
- Current device diagnostics.
- Existing connection records.

A known Nuxel helper is:

```text
scripts/s10plus-debug-pack/nuxel-live-ssh.sh
```

Inspect its supported arguments and existing Wi-Fi transport workflow.

Use its status/discovery behavior if appropriate:

```bash
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport wlan \
    --status
```

Use the actual repository path and supported CLI syntax.

Do not infer the host from a stale prior session.

## 1.3 SSH command

Once the actual host is identified:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
    -o IdentitiesOnly=yes \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=15 \
    root@<DISCOVERED_NUXEL_WIFI_HOST>
```

Preserve SSH host-key checking.

If the host key is new or changed, verify the device identity and fingerprint using the existing trusted workflow. Do not bypass host-key verification with `StrictHostKeyChecking=no`.

Verify the session is genuinely root:

```bash
id
whoami
hostname
uname -a
```

If root SSH is not available, inspect the existing supported Nuxel root-access workflow rather than weakening SSH security.

Keep the current SSH path working throughout the task.

Do not modify Wi-Fi, networking, sshd or firewall configuration unless a demonstrated issue requires it.

---

# 2. Initial system inventory

Before editing source, establish the actual running architecture.

Inspect:

- Nuxel release/version.
- Current Git branch and commit.
- Working-tree changes.
- Running kernel.
- Phoc version.
- Wayland session.
- Framebuffer bridge.
- WebKitGTK version.
- Nuxel Bridge.
- Navigation implementation.
- Keyboard/input method.
- Launcher and app drawer.
- Lock screen.
- Calendar.
- NuXtore.
- Nuxel Doom.
- Permission manager.
- Power-menu backend.
- systemd/logind.
- Existing root services.
- Current running applications.

The previous Nuxel source inspections identified useful paths such as:

```text
pwa/nuxel-home/js/qs.js
pwa/nuxel-apps/settings/settings.js
services/nuxel-bridge/src/bridge.py
tools/s10plus/a45/nuxel-navdock.c
```

These are starting points only.

Inspect the actual active source and build/install paths.

Do not assume the files in a previous source archive are still the active implementations.

## 2.1 Establish source-of-truth ownership

For every affected feature, identify:

- Source file.
- Owning service.
- Runtime process.
- Systemd unit.
- Frontend component.
- IPC/Bridge contract.
- Build target.
- Installed location.
- Runtime configuration.
- Relevant logs.

A patch to an uninstalled or unused file is not a fix.

## 2.2 Establish a baseline

Before changing anything, capture current behavior and useful diagnostics.

At minimum:

- Screenshot of the normal desktop.
- Screenshot of app drawer.
- Screenshot of Settings.
- Screenshot of lockscreen.
- Calendar with keyboard closed.
- Calendar with keyboard open.
- Power menu.
- App after navigation inside it.
- App after a single Back press.
- App after a long Back press.
- Tabs view.
- Rotated app drawer in each orientation.
- Blue rectangle event after launcher reload.
- Reboot timing.

Use existing screen capture mechanisms or compositor diagnostics.

Do not rely on a screenshot alone to diagnose invisible input grabs.

## 2.3 Preserve the known working behavior

Known prior behavior that must not regress:

- Physical fixed rotations work.
- Correct transform mappings have been verified.
- The Nuxel desktop and native applications work.
- The keyboard works in normal use.
- Back/Home/Tabs controls exist.
- The app drawer has a configured three-column default.
- Doom has an existing Nuxel implementation.
- Wi-Fi SSH is working.
- The current system boots and can be recovered normally.

Do not rewrite these systems unnecessarily.

---

# 3. One central input and navigation architecture

Several requested issues involve input precedence and shell ownership.

Implement or repair a centralized input/navigation coordinator.

Do not create competing JavaScript listeners and native handlers that each consume the same Back, swipe or keyboard event independently.

The coordinator must understand:

- Current application.
- Current app navigation history.
- Current modal state.
- Current keyboard state.
- Current shell overlay state.
- Current orientation.
- Current focus owner.
- Current process/window lifecycle.
- Whether the desktop is currently locked.
- Whether a system power menu is open.

All relevant surfaces must use a consistent event contract.

## 3.1 Input priority

Use a deterministic priority order.

For Back:

1. System modal/power confirmation, if applicable.
2. Visible keyboard dismissal.
3. App-level navigation/back handling.
4. App graceful close when no internal Back action exists.
5. Desktop-level fallback, if appropriate.

Do not let a foreground app consume Back indefinitely when it has no further navigation state.

Do not let a shell close action destroy an application when its own history can still navigate backward.

## 3.2 Event consumption

Define clearly when an event is consumed.

Avoid:

- Duplicate Back delivery.
- Multiple app close callbacks.
- Multiple keyboard hide calls with racing state.
- Repeated surface destruction.
- Old listeners surviving app reload.
- A stale app object remaining in foreground state.

Use explicit ownership and event cleanup.

---

# 4. System-wide zoom prohibition

The owner wants zoom disabled everywhere by default.

This applies to gesture-driven UI/content zoom across:

- Desktop.
- Lockscreen.
- App drawer.
- Settings.
- Quick Settings.
- Nuxel shell surfaces.
- Nuxel PWA applications.
- WebKit-backed applications.
- Native apps where Nuxel controls gesture dispatch.

The future Permission Manager will eventually have an explicit zoom permission.

For this task, default zoom permission must be denied.

Do not expose a new user-facing permission toggle yet.

## 4.1 Define one central zoom permission/policy

Add or repair a central permission key, conceptually:

```text
zoom
```

Default:

```text
denied
```

Design it so that a future Permission Manager can grant/revoke it without rewriting every application.

The policy must be consumed by the shell and app environment.

Do not create dozens of unrelated hardcoded app exceptions.

## 4.2 Disable all relevant zoom gestures

Investigate every zoom route:

- Touchscreen pinch.
- Multi-touch pinch.
- Double-tap zoom.
- Trackpad pinch.
- Ctrl+wheel.
- Ctrl+plus/minus where considered a gesture zoom.
- WebKit page-scale changes.
- Browser viewport zoom.
- Shell gesture zoom.
- App-drawer zoom.
- Desktop zoom.
- Lock-screen zoom.

Disable accidental zoom in all default Nuxel UI contexts.

## 4.3 WebKit/PWA behavior

Inspect:

- WebKitGTK gesture configuration.
- Page scale APIs.
- Viewport metadata.
- PWA viewport.
- CSS transforms.
- Touch-action settings.
- Pinch event handling.
- Double-tap event handling.
- Device pixel ratio.
- Orientation-change handling.

Use the appropriate WebKit and viewport controls.

A viewport setting such as:

```html
<meta name="viewport"
      content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
```

may be part of the implementation, but is not sufficient as the only control.

Prevent pinch and double-tap page scaling at the actual input/rendering level where supported.

## 4.4 Preserve ordinary interactions

Disabling zoom must not disable:

- Scrolling.
- Dragging.
- Lists.
- Sliders.
- Keyboard input.
- Text selection where intentionally supported.
- Buttons.
- Navigation gestures.
- App-specific controls.
- Accessibility text sizing.

Do not implement a global event cancellation that swallows all multi-touch input.

## 4.5 Zoom acceptance

Test in every required orientation.

Attempt pinch, double-tap and other zoom gestures on:

- Home.
- Lock screen.
- App drawer.
- Settings.
- Calendar.
- WebKit-backed apps.
- Doom.
- Other representative native/Flatpak apps where applicable.

The UI must not change page scale or desktop zoom.

Record any application-level zoom that cannot be controlled centrally and implement the narrowest compatible default policy.

---

# 5. Fix single-press Back behavior

This is a major behavioral correction.

The intended behavior is:

**A single Back press should go back inside the app first. If the app cannot go back any further, it should close gracefully.**

Holding Back remains the explicit force-kill action.

## 5.1 Required Back sequence

When the user single-presses Back:

### Case A — keyboard open

Dismiss the keyboard first.

Do not close the app.

Do not navigate its history.

### Case B — app has internal navigation history

Send Back to the foreground app.

Examples:

- Navigate back in WebKit history.
- Dismiss the app's current subview.
- Close an app-local modal/dialog when that is the app's own intended Back behavior.
- Return to the previous app screen.

Keep the app open.

### Case C — no further app navigation possible

Request graceful app close.

The app must receive its normal close lifecycle event where supported.

Do not force-kill it on a normal Back press.

## 5.2 Determine whether an app can go back

Use the actual app capability/state.

For WebKit:

- Inspect history length/index.
- Use correct WebKit navigation capability.
- Respect app-owned route state.
- Do not infer history solely from the number of URL changes.

For PWA applications:

- Respect their actual router.
- Do not allow the outer Nuxel shell to close an app while the app still has a valid internal Back action.

For native apps:

- Use supported window/application close semantics.
- If the app has its own navigation protocol, send the correct request.

Implement a reliable response to indicate whether Back was consumed.

Avoid time-based guesses that cause an app to exit when it actually navigated.

## 5.3 Graceful close

When no further Back action is possible:

1. Mark app as closing.
2. Release or close app-local modal surfaces.
3. Hide keyboard.
4. Clear app text-input focus.
5. Release input and pointer grabs.
6. Send normal close request.
7. Allow a bounded exit interval.
8. Confirm actual process/window exit.
9. Clean up shell state.
10. Return focus to the Nuxel desktop.

If the app refuses to close, do not silently kill it.

Leave the explicit force-kill action available.

## 5.4 Long-press Back

Holding Back must keep its existing force-kill role.

The force-kill action should:

- Identify the real foreground application.
- Confirm its process/window ownership.
- Hide keyboard.
- Clear modal and focus state.
- Terminate the correct app process or app process group.
- Use SIGKILL only for the explicit force-kill behavior.
- Clean up all shell/compositor references.
- Return control to the desktop.

Do not accidentally kill:

- Phoc.
- Nuxel shell.
- Keyboard process.
- Nuxel Bridge.
- System services.
- The wrong foreground process.

Use explicit app ownership, not broad process-name matching.

---

# 6. Tabs app lifecycle gestures

The Tabs button remains the app-switcher/lifecycle entry point.

Add the requested two-stage gesture behavior.

## 6.1 Swipe left — graceful stop

In Tabs view:

- Swipe left on an application card to request graceful close.
- Show a clear closing visual state.
- Prevent repeated close requests.
- Send the normal app close lifecycle event.
- Hide the keyboard if it belongs to that app.
- Release modal/input state.
- Remove the card only after the app has actually exited or the shell has verified its window/process lifecycle.

Do not instantly SIGKILL an app on left swipe.

## 6.2 Swipe right — force kill

Swipe right on an app card to explicitly force-kill an app that is still running or hung.

Use the same verified force-kill implementation as holding Back on the foreground application.

The gesture must be unambiguous.

Do not make a short accidental horizontal swipe kill an application.

Use a deliberate threshold, gesture direction lock and optional visual confirmation state.

## 6.3 Hung apps

If an app receives graceful close but remains alive:

- Retain its Tabs card.
- Mark it as closing/stuck.
- Allow swipe right to force-kill.
- Provide useful status.
- Do not remove it from the UI until it is actually terminated.

Do not block the entire shell while waiting for one application.

## 6.4 App states

Use an explicit lifecycle model:

```text
launching
running
background
foreground
close-requested
closing
stuck
force-killing
exited
failed
```

A process that is still alive must not be represented as fully exited merely because its visible window disappeared.

The shell's application registry and the actual process/compositor state must remain synchronized.

---

# 7. Fix the invisible desktop overlay/input blocker

This issue is high priority because it makes the desktop unusable.

## 7.1 Observed symptom

The owner reports:

1. Open an app.
2. Leave it using a single Back press.
3. The app appears to disappear.
4. The desktop is visible.
5. The app drawer and other desktop controls cannot be opened.
6. Holding Back to kill the foreground application clears the blockage.

This suggests that the visible app may have disappeared while something else remains active.

Possible candidates:

- Transparent overlay.
- Modal shield.
- WebKit surface.
- Hidden app container.
- Layer-shell popup.
- Surface with incorrect z-order.
- Pointer grab.
- Touch grab.
- Keyboard focus lock.
- Event-capturing rectangle.
- Window-manager state not cleared.
- Stale foreground application registry.
- Animation overlay.
- Delayed shell transition object.

Do not assume which one is responsible.

## 7.2 Inspect the actual scene

Capture the compositor/Wayland surface state before and after a failing transition.

Inspect:

- Surface tree.
- Layer-shell surfaces.
- Popup surfaces.
- Transient parents.
- Input regions.
- Opaque regions.
- Pointer focus.
- Keyboard focus.
- Active input grabs.
- App modal state.
- Visibility.
- Z-order.
- Surface mapping.
- Window ownership.

Identify the object that remains.

If the compositor exposes diagnostic tools or internal state, use them.

The objective is to find the invisible object that blocks input.

## 7.3 Unified app-close cleanup

Every graceful and force-kill path must call a single cleanup routine.

The cleanup routine must release:

- App modal overlays.
- App popups.
- App-owned shell surfaces.
- Touch/pointer grabs.
- Keyboard focus.
- Text-input context.
- App foreground state.
- Navigation lock.
- Transition shield.
- Temporary app container.
- App-specific event listeners.
- Shell reference ownership.

Do not duplicate cleanup logic across Back, Tabs, launcher reload and force-kill.

## 7.4 Desktop recovery

After a normal app exit:

- Desktop receives pointer and touch input immediately.
- App drawer opens.
- Home navigation works.
- Quick Settings opens.
- Tabs opens.
- Settings opens.
- Lock screen can be invoked.
- No hidden surface consumes input.

Do not add arbitrary 1–10 second delays.

---

# 8. Keyboard lifecycle and dismissal

Keyboard behavior must be consistent throughout Nuxel.

## 8.1 Back priority

When the keyboard is open, the first Back press must dismiss it.

Only the next Back press may navigate the app or close it.

This behavior must be centrally enforced.

An application must not be able to accidentally bypass keyboard dismissal through its own Back handler.

## 8.2 Swipe down to dismiss

When the keyboard is visible, the user must be able to swipe down from the top of the keyboard to dismiss it.

Implement the gesture in the keyboard region.

Requirements:

- Gesture starts inside a defined upper keyboard region.
- Vertical downward motion is measured.
- A deliberate threshold is required.
- Normal typing is unaffected.
- Key gestures are not swallowed.
- Scrolling in app content is unaffected.
- Nuxel top-bar gestures are unaffected.

Use one keyboard-dismiss gesture owner.

## 8.3 Force kill cleanup

When an app is force-killed:

- Immediately hide its keyboard.
- Remove the keyboard surface.
- Clear text-input focus.
- Clear active text-input context.
- Release any input-method grab.
- Reset stale app references.
- Restore shell input.

Do not leave the keyboard attached to a dead application.

## 8.4 Graceful close cleanup

The same keyboard cleanup must occur when an app closes normally through Back or Tabs.

If another application receives focus, initialize its own text-input context.

---

# 9. Calendar-specific completion

The Calendar application requires explicit mobile navigation and time-entry fixes.

## 9.1 Triple navigation buttons visible by default

The expected triple navigation buttons are the Nuxel system controls:

- Back.
- Home.
- Tabs.

For Calendar, ensure the three buttons are visible by default, not hidden until a gesture.

Reserve the correct screen space.

Do not let Calendar content render behind or over the navigation controls.

Use the existing Nuxel navigation implementation.

Do not create a second Calendar-specific set of buttons.

## 9.2 Keyboard-open behavior

When the Calendar keyboard is open:

- Triple navigation buttons must remain reachable.
- The user must be able to swipe up to reveal them.
- The keyboard must not permanently cover navigation.
- Back must dismiss keyboard before navigating the Calendar view.
- Home and Tabs must remain usable.

Do not disable the general keyboard merely to show the navigation controls.

## 9.3 Numeric time entry

Time fields currently show the typing keyboard instead of the numeric/time keyboard.

Inspect the Calendar implementation and input method.

Use an appropriate time-entry input type and the Nuxel input-method API.

Depending on the actual framework:

- A native time picker.
- A numeric input.
- A custom numeric/time keypad.
- An HTML `input type="time"`.
- Appropriate `inputmode` hints.

Time entry must support:

- Digits.
- Time separator.
- Valid hour range.
- Valid minute range.
- Cursor/editing behavior.
- 24-hour/12-hour presentation as appropriate to current Nuxel settings.

If the normal numeric keyboard lacks a time separator, provide a suitable time-specific keypad.

Do not use the general text keyboard for a simple time field.

## 9.4 Calendar force-kill

When Calendar is force-killed:

- Keyboard disappears immediately.
- Input context is released.
- Calendar surface is removed.
- No invisible overlay remains.
- Desktop input is restored.
- The app can be launched again normally.

Test with keyboard open, focused time field and a pending input operation.

---

# 10. Nuxel Doom and Chocolate Doom integration

The owner wants Doom installable completely from NuXtore.

The intended experience should not require separately installing a visible Chocolate Doom application.

However, distinguish the engine from the game data.

## 10.1 Audit the actual architecture

Inspect:

- Nuxel Doom application.
- Existing launcher entry.
- Existing executable.
- Engine dependency.
- Chocolate Doom package.
- WAD directory.
- NuXtore manifest.
- Install scripts.
- Runtime dependencies.
- Existing app data.
- Original graphics assets.
- Small-screen controls.
- D-pad/touch mapping.

Determine whether Chocolate Doom is currently:

1. A separate user-facing app.
2. The actual engine used by Nuxel Doom.
3. A runtime package dependency.
4. An accidental duplicate.
5. A development-only dependency.

Do not uninstall an engine binary that Nuxel Doom requires.

## 10.2 Desired packaging

The user's desired experience:

- Open NuXtore.
- Install Nuxel Doom.
- Receive all legally distributable required components.
- Complete WAD setup.
- Launch Doom.
- No separate manual Chocolate Doom installation.
- No missing binary/runtime errors.
- No manual terminal command.

Package the engine as a private dependency or include it in the application package if licensing and maintenance permit.

If another application also needs Chocolate Doom, preserve the shared engine package.

If Chocolate Doom is not required elsewhere, remove the redundant standalone launcher entry.

The user should experience one cohesive Nuxel Doom installation.

## 10.3 WADs and legal distribution

WADs are game data, separate from the engine.

Do not bundle copyrighted commercial DOOM IWADs without permission.

Inspect the actual license for any WAD packaged by NuXtore.

Possible approaches:

- Bundle a legally redistributable Freedoom WAD after verifying the exact project's license.
- Offer a compatible shareware WAD only if redistribution terms permit it.
- Provide an import flow for the user's legally obtained commercial WADs.
- Clearly identify which WADs are installed and which are needed.

Do not label a missing WAD as installed.

Do not download pirated game data.

## 10.4 Fresh-install verification

Test from a clean installation state.

The NuXtore package must declare and resolve:

- Engine.
- Required runtime libraries.
- Data directory.
- Legally distributable WAD, if included.
- User WAD import capability.
- Launcher metadata.
- Icon.
- Controls/configuration.
- Required permissions.

A developer machine with previously installed Chocolate Doom must not be used as the only proof.

## 10.5 Mobile controls and appearance

Preserve the existing Nuxel Doom goal:

- Original Doom graphics.
- Playable on S10+ screen.
- Mobile D-pad/touch controls.
- Usable buttons.
- Correct scaling.
- No accidental zoom.
- Correct landscape/portrait behavior as designed.
- Clean exit and process management.

Do not replace original graphics with blocky Minecraft-style graphics or unrelated asset recreations.

Test install, launch, play, close and relaunch.

---

# 11. Fix rotated app drawer geometry and zoom

The app drawer has a configured default three-column grid.

After rotation, it appears zoomed/cropped and some icons fall outside the visible screen.

The owner originally suspected a one-column regression, but the more recent diagnosis is that the drawer appears zoomed in and content is clipped.

Do not solve this by reducing the column count.

## 11.1 Inspect actual geometry

After each orientation transition inspect:

- Logical output dimensions.
- Viewport width/height.
- Visual viewport.
- Device pixel ratio.
- WebKit page scale.
- CSS scale/transform.
- Safe-area insets.
- Grid dimensions.
- Container width.
- Column count.
- Cell size.
- Icon size.
- Scroll height.
- Overflow.
- Keyboard viewport changes.

Determine whether the cause is:

- Accidental zoom.
- A stale viewport.
- Incorrect CSS transform.
- Fixed portrait dimensions.
- Orientation event arriving before final output geometry.
- Safe-area calculation.
- Cached app drawer dimensions.
- Incorrect device scale.
- Double application of a transform.

## 11.2 Preserve the three-column configuration

The default grid is three columns.

Keep it.

Do not override it to one column.

Ensure the configured row count and column count are used consistently by:

- App drawer.
- Desktop icons.
- Settings.
- App discovery.
- User-configured layout.

Do not hardcode separate values in CSS and JS.

## 11.3 Recalculate after orientation changes

After Phoc reports the new stable logical output geometry:

1. Update the app shell viewport.
2. Recalculate safe area.
3. Reset any accidental page scale.
4. Recalculate grid dimensions.
5. Reflow icons.
6. Restore scroll position safely.
7. Verify all icons are within the visible/scrollable area.
8. Re-enable interaction.

Do not run repeated resize timers.

Use the real output/viewport change event.

## 11.4 Test all orientations

Verify three columns in:

- Locked (PT).
- Locked (LS).
- Locked (RPT).
- Locked (RLS).

Also test after:

- Opening keyboard.
- Closing keyboard.
- Leaving an app.
- Locking/unlocking.
- Reloading launcher.

All icons must be visible and touchable.

---

# 12. Blue rectangle after reload/exit/lockscreen

A blue rectangle appears briefly near the top of the screen after certain transitions, then disappears after roughly ten seconds.

Observed triggers:

- Reload launcher.
- Leave an application.
- Enter lockscreen while an app is stuck.

Do not add a timer to hide it.

Find the source.

## 12.1 Capture the artifact

Reproduce the bug.

Capture:

- Screenshot immediately after it appears.
- Screenshots at short intervals.
- Actual surface tree.
- Compositor layer state.
- Active app/window.
- Surface ownership.
- Buffer contents if available.
- Framebuffer bridge status.
- Damage information.
- System log timestamps.

Determine whether it is:

- A stale app surface.
- Transparent/modal overlay.
- Lock screen transition surface.
- Status bar layer.
- Popup.
- WebKit surface.
- Uninitialized buffer.
- Blue-cleared region.
- Incorrect damage rectangle.
- Framebuffer stale pixels.
- Compositor output reconfiguration artifact.

The fact that the rectangle disappears later suggests a lifecycle/redraw problem, but it does not identify which component owns it.

## 12.2 Inspect surface cleanup

Inspect:

- Phoc layer-shell surfaces.
- Popup lifecycle.
- Transient surfaces.
- Subsurfaces.
- Input regions.
- Opaque regions.
- Visibility.
- Surface destruction.
- Surface buffer release.
- Lock-screen overlay.
- Launcher reload behavior.

Ensure every old surface is correctly unmapped/destroyed.

## 12.3 Inspect framebuffer damage path

The known Nuxel physical path is:

```text
Phoc / Wayland
      |
      v
zwlr_screencopy
      |
      v
nuxel-wl-fb
      |
      v
/dev/fb0
      |
      v
Samsung DECON / AMOLED
```

`nuxel-wl-fb` remains the sole `/dev/fb0` writer.

Inspect:

- Screencopy damage.
- Buffer reuse.
- Partial repaint.
- Stride.
- Region clipping.
- Transform handling.
- Frame submission.
- Old frame clearing.
- Repaint after lock/unlock.
- Repaint after launcher reload.
- Black/blue placeholder frames.

A stale framebuffer region may remain after a surface is unmapped if the correct damage region is not redrawn.

Prove whether this path is involved before modifying it.

## 12.4 Correct behavior

After:

- App exit.
- Launcher reload.
- Lock-screen transition.
- Unlock.
- Orientation change.

The display must immediately contain the correct complete frame.

No blue rectangle.

No stale pixels.

No ten-second wait.

Do not add unnecessary full-screen CPU redraws on every frame. Use correct damage/repaint logic.

---

# 13. Power menu — one visible instance, fully interactive

The power menu sometimes:

- Shows duplicate overlapping menus.
- Looks like two menus stacked.
- Has options that cannot be tapped.
- Becomes unexpectedly gated/unavailable.

Repair its ownership and backend.

## 13.1 One power menu instance

Use a single centralized power-menu controller.

Ensure only one menu root can exist at a time.

Prevent:

- Duplicate DOM roots.
- Multiple event listeners.
- Duplicate native overlays.
- Reentrant opening.
- Repeated button click handlers.
- Old menu instances after launcher reload.
- Overlapping system surfaces.

Give the controller explicit state:

```text
closed
opening
open
action-pending
action-accepted
closing
failed
```

Only one instance may own the menu overlay and input region.

## 13.2 Make each option genuinely tappable

Test all displayed actions:

- Restart.
- Power off.
- Suspend, if supported.
- Lock.
- Existing Nuxel power actions.

Check:

- Hitbox.
- Pointer events.
- Touch events.
- Z-order.
- Overlay ownership.
- Focus.
- Accessibility action.
- Click callback.
- Bridge request.
- Privileged backend.
- Completion/error response.

A visible button with no actual backend callback is not functional.

## 13.3 Fix intermittent gating

Determine why the power menu sometimes becomes unavailable.

Inspect:

- Permission manager.
- Current user.
- Root service.
- D-Bus authorization.
- systemd/logind.
- Polkit, if used.
- Session lock state.
- App modal state.
- Input grab.
- Overlay state.
- Busy-action guard.
- Power backend service.
- Cached permission result.

Do not disable security checks globally.

Do not grant every process power-management permission.

Power actions must remain available to the intended authorized Nuxel owner/admin context, including the expected root-backed desktop session.

If gating is intentional for a particular session state, report why and make the UI state consistent. The menu must not randomly become unavailable.

## 13.4 Action execution

Use the established systemd/logind interface or a narrowly scoped Nuxel privileged helper.

Do not make each UI component execute arbitrary root shell commands.

For every action:

1. Validate request.
2. Validate current authorization.
3. Acquire single-action lock.
4. Close/disable duplicate menu interaction.
5. Submit action to backend.
6. Wait for acceptance response, not full shutdown.
7. Update UI status.
8. Close menu appropriately.

Do not report success before the backend accepts the request.

---

# 14. Fix delayed reboot request

The current behavior is:

- User selects reboot.
- Screen goes black.
- The device waits more than 30 seconds.
- Only then does the actual reboot appear to be issued.

The first task is to determine precisely where this delay occurs.

## 14.1 Instrument the timeline

Record timestamps for:

1. Tap on Restart.
2. UI callback.
3. Bridge request.
4. Privileged helper entry.
5. Authorization.
6. systemd/logind call.
7. Systemd reboot job acceptance.
8. Display blank/lock.
9. Service shutdown start.
10. Kernel reboot.

Distinguish between:

- Delay before reboot request acceptance.
- Delay while systemd stops services.
- Delay during kernel reboot.

The user specifically observes a delay before the reboot is actually issued.

Do not assume all time is due to systemd shutdown.

## 14.2 Do not blank the screen too early

The user should not see a black screen for 30 seconds while the reboot request remains unissued.

The UI should enter the transition state only when the backend has accepted the reboot request or when a known immediate transition point is reached.

If the current shell blanks the screen before submitting the system action, fix the order.

## 14.3 Investigate inhibitors and service shutdown

Inspect:

- systemd inhibitor locks.
- logind.
- Reboot helper.
- Service stop dependencies.
- `ExecStop`.
- Shutdown hooks.
- Application lifecycle handlers.
- Blocking synchronous calls.
- Timeouts.
- Wait loops.
- Restart/reboot scripts.
- Filesystem synchronization.

Do not remove all inhibitors.

Determine whether one service blocks reboot and whether it has a legitimate requirement.

Use bounded shutdown timeouts.

Do not let an ordinary UI process wait indefinitely for apps to close.

## 14.4 Submit reboot promptly

The reboot request should be issued promptly using the correct systemd/logind path.

Where appropriate, use an asynchronous/nonblocking job submission so the UI does not synchronously wait for the entire reboot.

Verify the semantics of the installed systemd version.

Do not rely on a shell command that only starts after a long UI cleanup delay.

Do not use forced reboot as the normal path.

Do not kill filesystem, block-device or system-critical services to accelerate reboot.

Keep enough time for orderly shutdown and data integrity.

## 14.5 Power action acceptance

Test the complete chain.

The reboot UI should:

- Respond immediately.
- Prevent repeated presses.
- Submit one backend request.
- Show accepted state promptly.
- Not leave the display black while still doing unrelated app cleanup.
- Reboot reliably.

Perform the actual reboot test after all other changes are stable.

---

# 15. Application launch and exit architecture

All the fixes depend on a reliable app lifecycle.

Build or repair one source of truth for:

- App launch.
- Foreground state.
- Background state.
- Modal state.
- Keyboard ownership.
- Graceful close.
- Force kill.
- Surface unmap.
- Process exit.
- Launcher refresh.
- Tabs card state.

Do not implement different close semantics in Calendar, Doom, Settings and every other app.

## 15.1 PWA applications

Inspect:

- WebKit views.
- PWA routes.
- Browser history.
- App container ownership.
- Window lifecycle.
- Modal handling.
- Close behavior.
- App process reuse.
- Service worker lifecycle, where relevant.

On app close:

- Navigate to the app's actual final state if needed.
- Remove the PWA surface.
- Release app modal overlays.
- Clear focus.
- Hide keyboard.
- Release input grabs.
- Notify shell of close completion.

Do not kill the shared WebKit process if other apps depend on it.

Do not remove another app's webview.

## 15.2 Native applications

For native apps:

- Identify actual process.
- Identify app-owned windows.
- Identify transient dialogs.
- Request normal termination.
- Wait a bounded period.
- Escalate only through explicit force-kill behavior.

Do not terminate a process by a broad shared process name if it could affect unrelated Nuxel components.

## 15.3 Foreground ownership

At all times, Nuxel must know which app owns:

- Keyboard focus.
- Pointer focus.
- Modal state.
- Back handling.
- Navigation context.
- Window/surface.

If a foreground app exits, ownership must return to the shell atomically.

Do not leave a dead app as the foreground owner.

---

# 16. Lock-screen transitions

The owner reports the blue rectangle can also happen when switching to lockscreen while stuck inside an app.

Test lock/unlock through:

- Running PWA.
- Running native app.
- Keyboard open.
- App modal open.
- Tabs view.
- Power menu open.
- App closing.
- Hung app.

On lock:

- Prevent app input.
- Hide or securely cover sensitive app content as intended.
- Clear transient UI overlays.
- Preserve or suspend app lifecycle according to current Nuxel design.
- Avoid destroying unrelated processes.
- Ensure full screen redraw.

On unlock:

- Restore correct window/launcher state.
- Restore appropriate focus.
- Do not revive stale input grabs.
- Ensure keyboard remains hidden unless an intended text field is focused.
- Ensure display geometry is current.

Do not leave transparent lock layers above the unlocked desktop.

---

# 17. Orientation and rotation regression

The four fixed rotations are already proven:

| Mode | Angle | Transform | Logical |
|---|---:|---|---:|
| Locked (LS) | 90 | `270` | 1520×720 |
| Locked (RLS) | 270 | `90` | 1520×720 |
| Locked (RPT) | 180 | `180` | 360×760 |
| Locked (PT) | 0 | `normal` | 360×760 |

Preserve them.

After app lifecycle and drawer fixes, verify that:

- The shell receives correct output dimensions.
- The viewport resets after rotation.
- The drawer does not stay zoomed.
- The Calendar triple navigation remains visible.
- Keyboard placement updates.
- Power menu placement updates.
- Modal overlays use current geometry.
- App close releases old orientation-dependent surfaces.

Do not introduce a second screen rotation implementation.

Do not write directly to `/dev/fb0`.

`nuxel-wl-fb` remains the sole framebuffer writer.

---

# 18. Automated tests

Create tests at the correct source/service level.

Do not rely only on physical manual checks.

## 18.1 Back dispatcher

Test:

- Keyboard open.
- Keyboard closed.
- App with history.
- App without history.
- App modal open.
- App navigation consumed Back.
- App refuses close.
- Graceful close succeeds.
- Graceful close hangs.
- Force kill.
- Foreground app exits during Back.
- Rapid repeated Back presses.

Expected:

- Keyboard closes first.
- App navigation works before closing.
- Graceful close is default.
- Force kill only occurs from explicit action.

## 18.2 Tabs gestures

Test:

- Left swipe requests graceful close.
- Repeated left swipe does not duplicate requests.
- Right swipe force-kills a stuck app.
- Gesture threshold rejects accidental touches.
- Correct app identity is targeted.
- App card disappears only after verified exit.
- Other apps remain untouched.

## 18.3 Overlay cleanup

Simulate:

- PWA close.
- Native app close.
- Force kill.
- App crash.
- Launcher reload.
- Lock/unlock.
- Keyboard close.
- Modal close.
- Orientation change.

Verify no hidden surface blocks the desktop.

## 18.4 Keyboard

Test:

- Back closes keyboard.
- Swipe down closes keyboard.
- Typing is unaffected.
- Scroll is unaffected.
- System top-bar gesture is unaffected.
- Force kill closes keyboard.
- App exit clears focus.
- Reopen app starts in a clean input state.

## 18.5 Zoom

Test:

- Pinch.
- Double tap.
- Ctrl+wheel.
- Trackpad pinch.
- WebKit page scale.
- Rotation.
- Lock screen.
- App drawer.
- Calendar.
- Settings.

Page/desktop scale must remain fixed.

## 18.6 App drawer

Test:

- Three columns in portrait.
- Three columns in landscape.
- Three columns in reverse portrait.
- Three columns in reverse landscape.
- After keyboard.
- After app close.
- After lock/unlock.
- After launcher reload.

Every icon must be visible and touchable.

## 18.7 Power menu

Test:

- Open once.
- Open repeatedly.
- Close.
- Reopen.
- Tap every option.
- Rapid taps.
- Lock/unlock.
- After app close.
- With keyboard open.
- With no foreground app.
- With stale modal state.

Verify exactly one menu instance and one action callback per tap.

Test non-destructive actions first.

Perform reboot and shutdown acceptance last.

## 18.8 Reboot timing

Record timestamped events.

The reboot request must be accepted promptly after selection.

Do not use the full time from click to completed boot as the only measure.

Separate request-acceptance latency from shutdown/reboot duration.

---

# 19. Physical-device acceptance matrix

Use the actual S10+.

Test normal and reverse orientations.

| Scenario | Expected |
|---|---|
| Desktop pinch | No zoom |
| Lockscreen pinch | No zoom |
| App drawer pinch | No zoom |
| Settings pinch | No zoom |
| PWA pinch | No zoom |
| Single Back in app | App goes back |
| Back with keyboard open | Keyboard closes |
| Back with no app history | Graceful app close |
| Hold Back | Force-kills foreground app |
| Tabs swipe left | Graceful close |
| Tabs swipe right on stuck app | Force kill |
| Close app | Desktop remains interactive |
| Calendar launch | Triple navigation visible |
| Calendar time field | Numeric/time keyboard |
| Calendar keyboard open | Triple buttons reachable |
| Calendar force kill | Keyboard closes |
| App drawer after rotation | Three columns, no clipped icons |
| Launcher reload | No blue rectangle |
| Leave app | No blue rectangle |
| Lock while app stuck | No blue rectangle |
| Power menu | One menu, all options tappable |
| Power menu reopen | No duplicates |
| Power menu after app close | Still usable |
| Reboot | Request issued promptly |
| Doom fresh install | Complete NuXtore installation |

Also test native and Flatpak apps separately if both types use different process/window paths.

---

# 20. Staged deployment strategy

Do not change everything in a single untestable patch.

Use staged, reversible work.

## Stage 1 — Read-only audit

- SSH/root connection.
- Source mapping.
- Runtime process mapping.
- Log collection.
- Baseline screenshots.
- Existing bug reproduction.

No modifications.

## Stage 2 — Central lifecycle and input design

Implement:

- Back dispatcher.
- App lifecycle manager.
- Overlay/focus cleanup.
- Keyboard ownership.
- Tabs gesture routing.

Test these before other UI work.

## Stage 3 — Zoom policy

Implement:

- Central default-deny zoom policy.
- Shell/WebKit enforcement.
- Permission Manager integration point.
- App-level default enforcement.

Test all views.

## Stage 4 — Calendar

Implement navigation triple visibility, numeric time entry and keyboard cleanup.

## Stage 5 — App drawer and blue artifact

Fix viewport geometry and compositor/framebuffer stale rendering.

Test all four orientations.

## Stage 6 — Power menu and reboot

Fix single-instance ownership, callbacks, access policy and action backend.

Instrument reboot timing.

Test non-destructive actions first.

Reboot last.

## Stage 7 — Doom/NuXtore

Make Nuxel Doom installable from a fresh NuXtore state.

Resolve engine packaging, WADs, permissions and launcher metadata.

Test install/play/close/uninstall.

## Stage 8 — Full regression

Run every acceptance test with SSH access preserved.

Only report final success after physical phone testing.

---

# 21. Deployment and recovery safeguards

This task is primarily userspace.

Do not reflash the kernel.

Do not enter TWRP for routine changes.

Use Wi-Fi SSH and the specified root key.

Before each stage:

- Save the current source changes.
- Back up files being replaced.
- Preserve active user configuration.
- Check syntax/build.
- Check service dependencies.
- Prepare a rollback command.

After deployment:

- Confirm UI starts.
- Confirm input works.
- Confirm SSH remains connected.
- Confirm Home and Back work.
- Confirm the phone is still recoverable.

Avoid a simultaneous restart of Phoc, Bridge, keyboard and launcher unless a tested deployment sequence requires it.

Do not restart SSH.

Do not destroy the only active recovery path.

If a change causes the desktop to become unusable, use the root SSH session to roll it back.

If the kernel or hardware unexpectedly appears to require modification, stop and report the evidence. Do not decide to flash without a separate validated kernel plan.

---

# 22. Root-cause reporting

For every issue, report:

- Observed symptom.
- Reproduction steps.
- Root cause.
- Owning component.
- Source files changed.
- Runtime component changed.
- Test evidence.
- Regression risks.
- Remaining limitations.

Do not use generic statements such as:

- Fixed Back.
- Fixed power menu.
- Zoom disabled.
- Keyboard fixed.

Explain exactly what was wrong.

For the invisible overlay, identify the actual surface or input grab.

For the blue rectangle, identify the actual source or damage/rendering failure.

For reboot, show the timestamp between UI action and systemd/logind request.

For power menu gating, identify the actual authorization/state reason.

For the Calendar keyboard, prove the field now requests the correct input mode.

For Doom, show the complete clean installation and WAD resolution.

---

# 23. Final deliverables

The implementation agent must provide:

1. Root-cause report.
2. Source-of-truth file map.
3. Architecture/lifecycle changes.
4. Zoom policy changes.
5. Back navigation changes.
6. Tabs gesture changes.
7. Overlay/focus cleanup changes.
8. Keyboard/input-method changes.
9. Calendar changes.
10. Doom packaging and WAD licensing report.
11. NuXtore changes.
12. App drawer geometry changes.
13. Blue rectangle diagnosis and fix.
14. Power menu implementation and authorization results.
15. Reboot timing evidence.
16. Automated test results.
17. Physical four-orientation regression results.
18. Deployment and rollback commands.
19. List of remaining issues.

Do not claim the phone passed a test that was not performed on the physical device.

---

# 24. Definition of done

### Zoom

- [ ] Zoom is disabled throughout Nuxel by default.
- [ ] Future Permission Manager integration point exists.
- [ ] No accidental WebKit viewport zoom.
- [ ] No accidental desktop/app-drawer zoom.
- [ ] Text scaling and normal gestures still work.

### Back and lifecycle

- [ ] Single Back navigates inside the app.
- [ ] Keyboard is dismissed first.
- [ ] App gracefully closes only when no Back navigation is possible.
- [ ] Holding Back force-kills foreground app.
- [ ] Tabs swipe left gracefully closes.
- [ ] Tabs swipe right force-kills a stuck app.
- [ ] App state and compositor state remain synchronized.
- [ ] Hidden input-blocking surfaces are released.

### Keyboard and Calendar

- [ ] Back closes keyboard.
- [ ] Swipe down closes keyboard.
- [ ] Force kill closes keyboard.
- [ ] Calendar shows Back/Home/Tabs by default.
- [ ] Calendar keyboard-open navigation works.
- [ ] Calendar time fields invoke numeric/time input.
- [ ] Calendar app exit clears focus.

### Drawer and rendering

- [ ] Three-column app drawer works in all four orientations.
- [ ] No clipped icons.
- [ ] No unwanted page scale.
- [ ] No blue rectangle on launcher reload.
- [ ] No blue rectangle after app exit.
- [ ] No blue rectangle after lockscreen transition.
- [ ] Framebuffer bridge remains stable.

### Doom

- [ ] Nuxel Doom installs through NuXtore.
- [ ] Engine dependency is included/managed.
- [ ] No separate user-installed Chocolate Doom requirement.
- [ ] Legal WAD path works.
- [ ] User-owned WAD import works.
- [ ] Original graphics remain intact.
- [ ] Controls work on the S10+.
- [ ] App closes cleanly.

### Power/reboot

- [ ] Power menu has one instance.
- [ ] All displayed options are tappable.
- [ ] Backend actions work.
- [ ] Gating is understood and corrected.
- [ ] No stacked menus.
- [ ] Reboot request is issued promptly.
- [ ] Shutdown remains orderly.
- [ ] Phone returns to Nuxel normally.

### General

- [ ] Native apps remain functional.
- [ ] SSH remains available.
- [ ] Existing fixed rotation remains functional.
- [ ] No unintended kernel reflash.
- [ ] No TWRP/recovery modification.
- [ ] No user data loss.

---

# 25. Final instruction

Treat this as a coordinated Nuxel desktop reliability release.

Do not solve each symptom with a separate workaround.

The most important shared fixes are:

1. One central input/navigation dispatcher.
2. One reliable application lifecycle manager.
3. Complete surface/focus/input-grab cleanup.
4. One keyboard ownership and dismissal mechanism.
5. One centralized zoom policy.
6. One power-menu controller and authorized action backend.

Repair these foundations first, then fix Calendar, app drawer, compositor artifacts, Doom packaging and power behavior on top.

Use the existing root Wi-Fi SSH identity:

```text
~wicked/.ssh/wicked_wqn_id_rsa
```

Start with Nuxel running normally.

Preserve the current working kernel and display system.

Make small reversible changes and verify each stage on the actual phone.

**PWNAGE-80000 is finished only when the S10+ behaves like a reliable touch-first Nuxel mobile desktop: no accidental zoom, correct Back behavior, no invisible overlays, clean app/keyboard lifecycle, usable Calendar, working Doom installation, correct rotated app drawer, clean rendering transitions and a genuinely functional power/reboot path.**
