# 🐧🔥 NUXEL A44 — OPERATION KEYBOARD DOMINANCE

## CRITICAL REPAIR: WAYLAND KEYBOARD, FOCUS, CARET & APPLICATION STACKING

**TARGET:** Samsung Galaxy S10+ SM-G975F · Exynos 9820 · Fedora ARM64 · Nuxel · Phoc/Wayland · WebKitGTK

**EXECUTOR:** Local coding agent with live USB access.

**MISSION:** Fix Nuxel's virtual keyboard and application stacking properly at the compositor, input-method and application levels.

### CURRENT FAILURES

1. The virtual keyboard is not usable for typing inside graphical applications.
2. Keyboard input currently works through the live console, but not reliably through the touchscreen UI.
3. Tapping an input field does not produce a visible blinking cursor.
4. The keyboard can be obscured by application windows.
5. The Hide Keyboard control is unreliable.
6. Application windows overlap the wrong launcher elements.
7. Applications should cover the four-app shortcut dock but NEVER obscure the persistent Back/Penguin Home/Recents navigation dock.

This is a **root-cause engineering mission**, not a cosmetic CSS exercise.

---

## PHASE 1 — DISCOVER THE ACTUAL LIVE INPUT ARCHITECTURE

First inspect the current repository and running S10+.

Identify:

- Active Wayland compositor and version.
- Whether Phoc actually owns the display.
- Running Wayland display socket and session.
- Current virtual keyboard implementation and executable.
- Whether Squeekboard, another Wayland OSK, or a custom Nuxel keyboard is active.
- Whether the OSK is a native Wayland surface or WebKit HTML component.
- Actual launcher WebKitGTK process.
- Actual application window ownership and focus manager.
- `zwp_text_input_manager_v3` or legacy text-input protocol availability.
- `zwp_input_method_manager_v2` or compatible implementation availability.
- `zwlr_layer_shell_v1` support.
- Wayland seat and keyboard capabilities.
- libinput touchscreen events.
- Relevant compositor, keyboard, WebKit and application logs.

Use available read-only diagnostics such as:

`ps`, `systemctl`, `journalctl`, `loginctl`, `wayland-info`, `wev`, `libinput`, `busctl`, and process environment inspection.

Do not assume all named protocols are available. Inspect actual protocol registry and runtime behavior.

### Important distinction

Working keyboard input over a USB serial/live console proves that the kernel can receive text through that console.

**It does NOT prove that graphical applications receive Wayland keyboard events, text-input commits, or correct compositor focus.**

Identify the exact missing link:

`Touchscreen → focused editable widget → compositor text-input state → OSK activation → input-method commit/key events → target application → visible caret and inserted text`

Trace every stage with timestamps.

Do not implement another OSK until the existing implementation has been audited.

---

## PHASE 2 — FIX WAYLAND FOCUS AND TEXT INPUT

Implement a reliable, unified graphical text-input pipeline.

### On tapping an editable field

1. Detect the actual editable widget.
2. Give its containing application the correct compositor-level keyboard focus.
3. Establish text-input focus for the selected field.
4. Enable the relevant Wayland text-input protocol where supported.
5. Show a real editable text caret.
6. Activate the OSK where appropriate.
7. Preserve focus on the original input while interacting with the keyboard.
8. Deliver actual text to the focused application.

Supported fields must include:

- HTML `<input>` and `<textarea>`.
- Contenteditable fields.
- Settings text fields.
- Browser address/search bar.
- Calendar event fields.
- File Explorer rename input.
- Launcher search.
- Supported native GTK editable widgets.

Handle password fields without logging their contents.

### Real blinking caret

Ensure the native or browser-rendered caret:

- Appears inside the selected editable field.
- Blinks when the field is focused.
- Has visible contrast against Nuxel themes.
- Moves as characters are inserted or removed.
- Supports selection and cursor repositioning.
- Disappears or deactivates when focus genuinely leaves the field.

Inspect CSS `caret-color`, focus styling, editable state, viewport positioning, and compositor focus.

**Do not fake the caret using a decorative blinking CSS element.**

### Actual text insertion

Verify these work:

- Letters.
- Uppercase/lowercase.
- Numbers.
- Space.
- Backspace.
- Enter.
- Shift.
- Symbols.
- Cursor movement.
- Repeated typing.
- Long-press where supported.
- Text selection.

Do not mistake generated JavaScript events for trusted native input. If the OSK and application are separate Wayland surfaces, use the compositor-supported input-method protocol, not untrusted synthetic browser key events.

Do not create an unrestricted privileged input-injection service accessible to arbitrary webpages.

---

## PHASE 3 — KEYBOARD MUST ALWAYS BE ABOVE APPLICATION CONTENT

Implement proper compositor-managed keyboard stacking.

### Required layering

The virtual keyboard must appear above:

- Browser.
- Calendar.
- Settings.
- File Explorer.
- App drawer.
- Launcher.
- Other standard app windows.

It must never appear behind an ordinary application window.

When a keyboard is active, allocate appropriate bottom space for it and avoid obscuring the focused text field.

### Native Wayland keyboard

If the keyboard is native:

- Use the compositor's supported input-method integration.
- Use a suitable OSK/system layer when supported.
- Preserve the target application's keyboard focus.
- Configure the OSK as non-activating where appropriate.
- Reserve or communicate keyboard geometry to the compositor/applications.
- Use compositor-managed stacking, not HTML z-index.

Do not arbitrarily place an OSK above security-sensitive lock-screen or authentication surfaces.

### HTML/WebKit keyboard

If the keyboard is implemented inside WebKit:

- Determine whether it belongs to the launcher or a separate window.
- Fix ownership and stacking so it is usable across applications.
- Do not rely on browser DOM z-index to position it above unrelated native Wayland windows.
- If cross-process focus requires compositor integration, implement the correct bridge.

### Keyboard geometry

When OSK appears:

- Keep focused input visible.
- Resize, pan, or scroll content appropriately.
- Avoid covering text fields.
- Avoid blocking bottom navigation.
- Respect screen dimensions, rotation, and safe areas.
- Restore original geometry when OSK closes.
- Prevent viewport oscillation or repeated resizes.

---

## PHASE 4 — CORRECT APPLICATION AND DOCK STACKING

There are TWO different dock systems.

### Dock A — Four application shortcuts

This is the Home shortcut dock with BG1/BG2 custom backgrounds.

When an application is opened:

**The application window must render ABOVE this dock.**

Requirements:

- Four-app dock visible on Home.
- Hidden or covered when foreground application occupies that region.
- No dock icons floating over Calendar, Browser, Settings, or File Explorer.
- No accidental dock hitboxes intercepting foreground application touch input.
- Dock remains intact when Home is restored.
- Dock backgrounds still switch between BG1/BG2.
- No unwanted transparent gaps.

Do not destroy/recreate the dock unnecessarily during application transitions.

### Dock B — Three-button system navigation

Contains:

**BACK | PENGUIN HOME | RECENTS**

This dock MUST remain visible and interactive over ordinary application windows.

Required:

- Standard applications cannot cover it.
- It always retains a usable touch region.
- Applications are constrained to the available work area above it.
- Applications cannot draw through the reserved navigation strip.
- Home works from every normal application.
- Back works for internal navigation.
- Long-press Back retains its intended close-app behavior.
- Recents remains open after one tap.
- The dock's original artwork remains visible.
- Keyboard appearance must not remove the navigation dock.

Use appropriate compositor-layer placement, exclusive-zone/work-area geometry, or equivalent verified window constraints.

**Do not solve this with only CSS z-index: a native application window can exist in an entirely different compositor surface.**

### Required active-window hierarchy

When Home is active:

- Home content and four-app dock are visible.
- Navigation dock is visible.

When an application is active:

- Application covers Home content and the four-app dock.
- Navigation dock remains visible.
- Virtual keyboard appears over the application's content when requested.
- Navigation controls remain accessible.

If keyboard and navigation occupy the same bottom region, use a deliberate layout where the keyboard sits immediately above the navigation dock, without overlapping its hitboxes.

---

## PHASE 5 — FIX HIDE KEYBOARD

The existing Hide Keyboard button must actually dismiss the OSK.

Requirements:

1. Tap Hide Keyboard.
2. OSK disappears promptly.
3. Focus state remains coherent.
4. The target input does not receive unintended characters.
5. Application geometry returns to normal.
6. Navigation dock remains accessible.
7. Keyboard does not immediately reopen because of stale text-input activation state.
8. Tapping a field again reopens it reliably.

Do not terminate the keyboard daemon just to hide its surface.

Implement a proper show/hide lifecycle.

Handle input focus changes, app switching, Home/Back navigation, screen rotation and suspend/resume.

---

## PHASE 6 — RESTORE KEYBOARD HAPTICS

Use Nuxel's existing vibration service.

Each virtual keypress should request a subtle tactile pulse.

Requirements:

- Configurable keyboard haptics.
- No vibration on touch movement without an accepted keypress.
- One vibration request per committed keypress.
- Short, low-latency pulse.
- No excessive queued vibrations.
- Respect Silent/Vibrate policy and independent haptic settings.
- Preserve existing navigation haptics.
- Ensure only one userspace subsystem owns the vibrator output.

If no real vibration occurs, inspect the live kernel vibrator device and report evidence.

Haptics must not delay text insertion.

---

## PHASE 7 — PERFORMANCE AND INPUT LATENCY

Measure actual touch-to-character latency.

Investigate:

- Touch-event dispatch latency.
- Compositor focus latency.
- OSK rendering delay.
- Key event delivery.
- Text commit latency.
- WebKit main-thread blocking.
- Duplicate event handlers.
- Focus-loss/refocus loops.
- Window-stack recomputation.
- Excessive logging.
- Main-loop stalls.

Optimize measurable bottlenecks.

Prioritize responsiveness and correctness over decorative animation.

Avoid blocking shell commands in keypress handlers.

Prevent duplicate keyboard instances and duplicate key events.

---

## PHASE 8 — IMPLEMENT ROBUST REGRESSION TESTS

Add automated tests appropriate to the real stack.

### Required cases

- Tap input → keyboard opens.
- Tap input → real focused editable state.
- Caret is visible.
- Typing inserts characters.
- Backspace removes characters.
- Shift/caps works.
- Enter works.
- Switching inputs preserves correct focus.
- Switching applications transfers keyboard focus.
- Keyboard remains above application windows.
- App windows cover four-app dock.
- Navigation dock remains visible and clickable.
- Hide Keyboard dismisses OSK.
- Keyboard reopens when input is selected.
- Home minimizes foreground app without terminating it.
- Back navigation continues to work.
- Long Back closes only the foreground application.
- Recents works with keyboard hidden and visible.
- Keyboard haptics trigger without duplicate requests.
- Rotation handles OSK geometry.
- No focus loop on app opening or closing.

Distinguish mocked protocol tests from actual integration tests against Phoc and WebKitGTK.

---

## PHASE 9 — DEPLOY ON LIVE GALAXY S10+

**DO NOT STOP AT SOURCE CODE OR MOCK TESTS.**

### Deployment sequence

1. Verify the USB live console.
2. Identify actual active services and deployed binaries.
3. Back up affected files and current service configurations.
4. Record hashes and service states.
5. Implement repairs in the current repository.
6. Compile native components for actual Linux AArch64.
7. Validate protocols, runtime dependencies and binary architecture.
8. Run unit/integration tests.
9. Stage deployable artifacts.
10. Deploy using the existing Nuxel live USB mechanism.
11. Keep console recovery available.
12. Restart only affected services.
13. Verify compositor and launcher remain running.
14. Confirm the correct patched files are loaded.
15. Inspect graphical-input runtime logs.
16. Announce physical testing to owner.
17. Fix failures and retest.
18. Verify one controlled reboot if safe and authorized.

Do not restart or replace the compositor without first confirming that doing so will not strand the live USB session.

### 90-second real-device test

Tell the owner:

**"Keyboard and stacking test ready. Please test now."**

Ask owner to:

1. Open Calendar.
2. Tap a text field.
3. Confirm visible blinking cursor.
4. Type `Nuxel keyboard is alive 123`.
5. Delete and retype characters.
6. Hide keyboard.
7. Reopen keyboard.
8. Confirm keyboard always remains above Calendar.
9. Open Browser and type a URL.
10. Open File Explorer and rename a file.
11. Verify four-app dock is not visible over running apps.
12. Verify Back/Penguin Home/Recents dock remains visible.
13. Press Home and return to Desktop 1.
14. Return to app using Recents.
15. Confirm subtle keyboard haptic feedback.

Collect timestamps/logs and correlate with the owner's answers.

**Never claim hardware success without physical verification.**

---

## PHASE 10 — ACCEPTANCE & REPORTING

Produce a final matrix:

| Feature | Source | Live deployment | Physical verification |
|---|---|---|---|
| Wayland input-method integration | | | |
| Text caret | | | |
| Actual text insertion | | | |
| Keyboard stacking | | | |
| App-over-shortcut-dock stacking | | | |
| Persistent navigation dock | | | |
| Hide Keyboard | | | |
| Keyboard haptics | | | |
| App switching and focus restoration | | | |
| Screen rotation with OSK | | | |

Record:

- Actual compositor and protocol implementation.
- Exact source paths changed.
- Exact deployed paths.
- Git commit hashes.
- Test commands and results.
- Relevant logs.
- Before/after latency measurements.
- Screenshots or compositor surface evidence.
- Device-side installation receipts.
- Rollback commands.
- Remaining blockers.

If Phoc or the existing OSK does not support a needed protocol, document the exact limitation and implement a compatible solution without inventing protocol support.

## ABSOLUTE SAFETY RULES

- NO FLASHING.
- NO RAW PARTITION WRITES.
- NO KERNEL REPLACEMENT.
- NO BOOTLOADER CHANGES.
- NO UNVERIFIED INPUT INJECTION INTO PRIVILEGED SESSIONS.
- NO KILLING THE ONLY RECOVERABLE USB CONSOLE.
- NO FAKE CARET.
- NO FAKE KEYBOARD SUCCESS.
- NO CSS-ONLY SOLUTION TO CROSS-WINDOW STACKING.
- DO NOT REGRESS EXISTING HAPTICS OR NAVIGATION.

## FINAL OBJECTIVE

A real Linux smartphone input experience:

**Tap field → blinking cursor → keyboard appears above app → type immediately → Hide Keyboard works → navigation remains accessible.**

Applications cover the Home shortcut dock but never cover the system navigation dock.

**EXECUTE, DEPLOY, VERIFY AND REPAIR ON THE LIVE S10+ NOW. 🐧🔥**

and the home button the penguinface still doesnt go to the home launcher page.
