# CYBER-TIEL 35B — NUXEL OPERATION TOUCHABLE
## Ultimate Physical Touchscreen, Application Clickability & Gesture Repair Mission
### Samsung Galaxy S10+ · Fedora 43 ARM64 · MacBook M1 Max
### ONE MISSION: MAKE THE PHONE COMPLETELY INTERACTIVE BY TOUCH

# 0. ABSOLUTE MISSION DIRECTIVE

You are Cyber-Tiel-Coder-35B-A3B, acting as the lead engineer responsible for finishing Nuxel's physical touchscreen interaction system.

Nuxel is an independent Fedora-based Linux phone operating system running on a Samsung Galaxy S10+ SM-G975F.

The phone boots successfully.

The graphical launcher renders.

Previous engineering runs have reported that physical touchscreen events reach various layers of the input stack, including WebKitGTK in some tests.

However, the owner still cannot reliably tap icons and open applications.

**YOUR ONLY MISSION IS TO MAKE THE TOUCHSCREEN CONTROL NUXEL.**

Implement and verify:

1. **TAP:** Touch an app icon and the application actually opens.
2. **HORIZONTAL SWIPE:** Swipe left/right to navigate between two home-screen desktop pages.
3. **SWIPE DOWN:** Open the top notification/Quick Settings panel with a downward gesture from anywhere on the interactive screen.
4. **SWIPE UP:** Open the applications drawer with an upward gesture from anywhere on the interactive screen.
5. **CLOSE:** Dismiss either panel and return to the current desktop.
6. **HOME:** Return from an application to the home screen.
7. **RESPONSIVENESS:** UI changes appear immediately without pressing Power to refresh the display.

These are functional requirements, not suggestions.

Do not declare success until the owner physically confirms them.

# 1. MODEL CONFIGURATION

Local model:

Cyber-Tiel-Coder-35B-A3B.

Requested settings:

- Context window: 131072 tokens.
- Maximum output tokens: 65536.
- Temperature: 0.0.
- Inference concurrency: 1.
- Reasoning: Maximum available within the runtime.
- Persistent execution state: Enabled through repository files.

Verify the inference server actually supports those limits.

These are runtime ceilings, not requirements to fill the context or generate an enormous response.

Prefer focused source inspection, executable tests and small code patches over large speculative reasoning dumps.

# 2. TARGET ENVIRONMENT

Development machine:

- MacBook M1 Max.
- macOS.
- Nuxel source repository: `~/x/nuxel`.
- Physical Galaxy S10+ connected over USB.
- Existing Mac-compatible live console.

Target phone:

- Samsung Galaxy S10+ SM-G975F.
- Codename: beyond2lte.
- Exynos 9820.
- Samsung Linux 4.14.253.
- Fedora 43 ARM64.
- sec_ts Samsung touchscreen.
- Phoc/Wayland compositor.
- WebKitGTK application host.
- Nuxel Home PWA.
- Wayland-to-Samsung-framebuffer rendering bridge.

Relevant source areas include:

`pwa/nuxel-home/`

`pwa/nuxel-home/js/`

`pwa/nuxel-common/`

`pwa/nuxel-apps/`

`tools/s10plus/a33/`

`tools/s10plus/a34/`

`services/`

`docs/s10plus-autonomous-boot-repair/TOUCHDOWN/`

`scripts/s10plus-debug-pack/`

Also inspect newer files and changes created by Codex and previous Cyber-Tiel sessions.

Do not assume these paths represent the newest implementation without checking.

# 3. HARD RULES

DO NOT:

- Rewrite the entire launcher.
- Replace WebKitGTK.
- Replace Fedora.
- Flash partitions.
- Rewrite the kernel.
- Modify bootloader state.
- Touch EFS or radio firmware.
- Enter TWRP or Download Mode.
- Run Heimdall/Odin.
- Run unrelated release-engineering tasks.
- Change the whole application's design.
- Introduce a second competing compositor.
- Spawn multiple framebuffer owners.
- Claim synthetic touch events prove physical functionality.

You MAY:

- Inspect logs.
- Inspect current running processes.
- Modify existing PWA JavaScript/CSS.
- Modify the WebKitGTK host.
- Fix libinput/Wayland event routing.
- Fix compositor focus.
- Fix touch transforms.
- Fix UI gesture handling.
- Fix click handlers.
- Fix application lifecycle.
- Add a second home-screen page.
- Add necessary gesture animations.
- Add instrumentation.
- Write tests.
- Deploy validated userspace changes through the live USB console.
- Restart affected services.
- Use normal Nuxel reboot if necessary and recoverable.

Preserve all existing working functionality.

# 4. FIRST TASK — READ THE ACTUAL CURRENT STATE

Before making changes:

1. Read the latest TODO and RESUME files.
2. Read the newest touchscreen engineering reports.
3. Inspect uncommitted changes and current Git history.
4. Inspect current PWA and WebKitGTK sources.
5. Determine which fixes are deployed to the real phone.
6. Compare repository source and installed hashes.
7. Confirm the physical boot mode.
8. Confirm the live-console connection.
9. Confirm currently active input devices.
10. Confirm actual launcher and window processes.
11. Confirm that only one service owns the graphical presentation path.
12. Identify all currently registered application input handlers.

Previous work includes A33/A34 and later Codex repairs.

Do not repeat earlier investigations unless the current evidence contradicts their conclusions.

**A historical successful finger event does not prove today's physical interface works.**

Create:

`docs/touchable/BASELINE.md`

`docs/touchable/TODO.md`

`docs/touchable/RESUME.md`

Immediately proceed to fixing the first proven issue.

Do not stop after preparing documentation.

# 5. ABSOLUTE PRIORITY — MAKE APP ICONS CLICKABLE

This is your FIRST functional objective.

The owner must physically touch an application icon.

The correct application must open.

The interface must immediately display the application.

Do not implement fancy gestures while this basic interaction remains broken.

Trace the complete pipeline:

PHYSICAL FINGER

→ Samsung sec_ts

→ evdev

→ libinput

→ Phoc

→ Wayland

→ WebKitGTK

→ DOM event

→ Nuxel icon handler

→ application launch

→ visible application window.

Identify the first stage where events disappear or become incorrect.

## Touch event diagnostics

Instrument:

- EV_ABS.
- ABS_MT_SLOT.
- ABS_MT_TRACKING_ID.
- ABS_MT_POSITION_X.
- ABS_MT_POSITION_Y.
- BTN_TOUCH where applicable.
- SYN_REPORT.
- libinput touch events.
- Wayland touch events.
- WebKit touchstart/touchend.
- pointerdown/pointerup.
- click.
- DOM target element.
- App-launch callback.
- Window creation.
- Application frame presentation.

Correlate timestamps.

Distinguish actual finger contacts from Power, Volume and Bixby events.

DO NOT report touchscreen success from unrelated EV_KEY hardware-button activity.

## Specific suspects

Inspect:

- Invisible fullscreen overlays.
- Incorrect `pointer-events`.
- Incorrect z-index.
- Stale boot splash elements.
- App windows intercepting input.
- Native Terminal left open.
- WebKit window focus.
- App icon hitboxes.
- Incorrect coordinate scaling.
- Incorrect screen orientation.
- Touch input classified as mouse incorrectly.
- Duplicate compatibility events.
- Touch release not reaching WebKit.
- Missing click-handler registration.
- Service-worker serving outdated JavaScript.
- JavaScript runtime exceptions.
- App bridge failures.
- Application creation without actual visible presentation.

Treat these as hypotheses.

Prove the root cause before modifying the relevant subsystem.

# 6. FIX APPLICATION LIFECYCLE

The owner previously experienced what appeared to be a frozen launcher when applications opened into empty or unclosable surfaces.

Investigate whether that problem still exists.

Required invariant:

**NO APPLICATION MAY LEAVE AN INVISIBLE OR UNRECOVERABLE INPUT-BLOCKING SURFACE ABOVE NUXEL HOME.**

Fix:

- Application activation.
- Focus transfer.
- App window creation.
- App close.
- Home navigation.
- Iframe cleanup.
- Native window cleanup.
- Terminal window lifecycle.
- Error-state recovery.
- Application reopening.

When an application is opened:

- It must become visibly active.
- It must receive input.
- A clear Home/Close mechanism must be available.
- Returning Home must restore launcher interaction.

Test multiple sequential launches.

Do not stop after a single successful tap.

# 7. SECOND HOME-SCREEN DESKTOP

Once basic icon clickability works, add a second desktop page within the EXISTING Nuxel Home launcher.

Do not create a separate operating-system session or Wayland compositor.

Implement two home-screen pages:

DESKTOP 1 — Existing Nuxel Home.

DESKTOP 2 — Additional home-screen page.

Preserve the original wallpaper and visual styling.

Use existing launcher components.

Keep the existing application registry.

Desktop 2 may initially contain additional app shortcuts or a minimal empty home page with a clear indication that the user is on page two.

Do not invent new installed applications.

## Horizontal swipe behavior

On the home-screen workspace:

- Swipe LEFT: Desktop 1 → Desktop 2.
- Swipe RIGHT: Desktop 2 → Desktop 1.
- Swipe beyond either end: remain on the nearest page.
- Short taps: open icons normally.
- Horizontal dragging: show smooth page movement.
- Release: settle on the appropriate page.

Implement a small page indicator:

`● ○`

for Desktop 1, and:

`○ ●`

for Desktop 2.

The indicator should update immediately.

Save the active page state when appropriate.

Ensure app icons on BOTH desktops are clickable.

Do not let horizontal gesture detection suppress ordinary taps.

# 8. GLOBAL VERTICAL SWIPE GESTURES

Implement reliable swipe gestures for:

**SWIPE DOWN → TOP PANEL**

**SWIPE UP → APPLICATION DRAWER**

These gestures must be recognized from anywhere on the home-screen workspace, not just a tiny edge activation zone.

When an application is open, support the same global navigation gestures through the appropriate input-routing layer wherever technically possible.

A gesture beginning on a native window or independent WebKit view may not reach the home PWA. Determine the correct common routing layer rather than installing listeners only in the launcher DOM.

## Swipe down

A deliberate downward swipe should:

1. Be recognized.
2. Open the existing top panel / notification shade / Quick Settings.
3. Animate it downward into view.
4. Allow interaction with its controls.
5. Allow dismissal by swiping upward.
6. Return cleanly to the previous desktop/application when closed.

Use the existing top panel.

Do not create a second, competing Quick Settings implementation.

## Swipe up

A deliberate upward swipe should:

1. Be recognized.
2. Open the applications drawer.
3. Animate the application window/drawer upward.
4. Show the actual installed application shortcuts.
5. Permit scrolling.
6. Permit tapping any app.
7. Close when swiping down or using Home.

Use the current application registry as the source of truth.

Do not show noninstalled apps as though they're installed.

## Gesture conflict rules

Global swipes must not break ordinary app interaction.

Implement a gesture state machine with:

- Touch-down position.
- Touch-down time.
- Movement distance.
- Horizontal versus vertical intent.
- Gesture activation threshold.
- Gesture ownership.
- Touch cancel/release.
- Pointer capture handling.
- Edge/bounds behavior.
- Duplicate event suppression.

Use a modest movement threshold so a normal tap never accidentally opens a panel.

Choose the dominant axis and lock direction once sufficient movement occurs.

Prevent a vertical scroll inside an app from unexpectedly opening Quick Settings or the app drawer. Where both operations would conflict, provide a deterministic arbitration rule, such as recognizing intentional system navigation gestures before passing them to an application, while preserving ordinary scrolling within its content.

Do not break pinch/multitouch interaction.

Do not accidentally open both the top panel and app drawer.

The gesture must work from any starting position on the Home workspace. For other applications, implement global recognition in the shared input host if needed, and document any unavoidable conflicts.

# 9. GESTURE ANIMATIONS AND RESPONSIVENESS

Keep animations lightweight because the current Galaxy S10+ uses a nonstandard framebuffer presentation path.

Prefer compositor-friendly transforms.

Implement:

- Smooth horizontal home-screen transition.
- Top panel sliding downward.
- App drawer sliding upward.
- Immediate response to touch movement.
- Correct final position on release.
- Cancellation when a gesture is incomplete.

Do not require expensive blurs or graphical effects.

Prefer reliability to decoration.

Ensure animations finish correctly even under reduced frame rates.

Never leave an invisible overlay blocking subsequent taps.

Check display updates without pressing Power.

# 10. THE MANDATORY 90-SECOND LIVE TEST SYSTEM

This is the MOST IMPORTANT operational change.

The owner is physically present and willing to interact with the S10+ during testing.

You must actively coordinate tests.

**DO NOT JUST SAY "PLEASE VERIFY LATER."**

Prepare instruments, announce the test, wait exactly 90 seconds, collect evidence, inspect the results, fix what failed, then prepare the next test.

Create a persistent script such as:

`tools/touchable/nuxel-touch-90s-test.py`

The script must:

1. Check that the live console is reachable.
2. Ensure exclusive serial-console ownership.
3. Start bounded input diagnostics.
4. Record device timestamps.
5. Record actual evdev contacts.
6. Record WebKit DOM events when possible.
7. Record application state transitions.
8. Record compositor/frame presentation state.
9. Print instructions before capture begins.
10. Announce when capture starts.
11. Capture for 90 seconds using a monotonic clock.
12. Stop diagnostic collection automatically.
13. Save logs and machine-readable results.
14. Print a concise result summary.
15. Return a meaningful exit code.
16. Restore normal input handling if diagnostics altered it.

Do not block the graphical application by grabbing the touchscreen exclusively.

Do not launch two programs that fight for the same USB serial port.

Do not rely on a manual Ctrl+C to end testing.

If diagnostics can only be captured by restarting a service, do so safely with rollback prepared.

# 11. LIVE TEST ROUND 1 — APP CLICKABILITY

Once diagnostics are armed, display the following clear announcement:

==================================================
NUXEL — PHYSICAL TOUCH TEST 1
90 SECONDS — STARTING NOW
==================================================

PLEASE USE YOUR FINGER ON THE PHONE.

1. Tap the Settings icon five times, allowing it to open if possible.
2. Tap another visible application icon.
3. Tap the center of the screen five times.
4. Try to return Home.
5. Repeat whichever action appears unresponsive.

I am recording the touchscreen, compositor, WebKit and application events for 90 seconds.

DO NOT unplug the USB cable.

When the timer ends, I will analyze the results and automatically continue.

==================================================

Start the actual bounded test.

Wait the full 90-second capture window.

Collect evidence.

Correlate physical input with application response.

Determine:

- Whether fingers were detected.
- Whether coordinates were correct.
- Whether the intended DOM elements were hit.
- Whether click handlers ran.
- Whether applications opened.
- Whether visible frames were presented.

Then FIX the first failing stage.

Deploy the repair.

Run regressions.

Proceed to another live test.

# 12. LIVE TEST ROUND 2 — HORIZONTAL DESKTOP SWIPES

Once application clickability is repaired and the second page exists, announce:

==================================================
NUXEL — PHYSICAL TOUCH TEST 2
90 SECONDS — STARTING NOW
==================================================

PLEASE:

1. Swipe LEFT across the middle of the screen.
2. Swipe RIGHT to return.
3. Repeat five times.
4. Tap an icon on Desktop 1.
5. Return Home.
6. Swipe to Desktop 2.
7. Tap an icon on Desktop 2.
8. Return Home.

I will capture gesture direction, distance, page state and app-launch events.

==================================================

Capture for 90 seconds.

Verify:

- Left goes to Desktop 2.
- Right goes to Desktop 1.
- Page indicators change.
- Apps remain clickable.
- No ghost gestures.
- No display stalling.

Repair and retest if any functional requirement fails.

# 13. LIVE TEST ROUND 3 — VERTICAL SYSTEM SWIPES

Announce:

==================================================
NUXEL — PHYSICAL TOUCH TEST 3
90 SECONDS — STARTING NOW
==================================================

PLEASE:

1. Swipe DOWN from the center of the Home screen.
2. Confirm the top panel appears.
3. Swipe UP to dismiss it.
4. Swipe UP from the center to open Applications.
5. Tap an application icon in the drawer.
6. Return Home.
7. Repeat from different areas of the screen.
8. If available, repeat while an application is open.

I will record gesture classification, panel state, app activation and visible rendering.

==================================================

Capture for 90 seconds.

Verify that the intended panels respond and do not block the next input.

Repair and retest.

# 14. OWNER VERIFICATION — PASS OR FAIL

After each physical test window, the user must be able to report whether the expected visible actions occurred.

Implement a simple terminal feedback mechanism.

Example:

`touchable-owner PASS`

or:

`touchable-owner FAIL "Settings still does not open"`

These commands should write owner feedback to a mission-specific file.

The autonomous agent must read that feedback.

A missing PASS is NOT a PASS.

If the owner doesn't provide feedback, mark the visual acceptance as pending, but continue work that can still be verified.

Never infer that UI interaction works solely from a logged click handler.

# 15. REPEAT THE FIX → TEST LOOP

Follow this procedure:

REPRODUCE

→ RECORD PHYSICAL EVENTS

→ FIND FIRST FAILING STAGE

→ PATCH MINIMALLY

→ RUN AUTOMATED TESTS

→ DEPLOY VERIFIED USERSPACE FILES

→ RUN NEW 90-SECOND OWNER TEST

→ COLLECT PASS/FAIL FEEDBACK

→ VERIFY

→ REPEAT IF NEEDED.

Do not finish the mission after one unsuccessful round.

Do not return a generic recommendation to test manually.

Do not simply generate another plan.

Do not mark a bug fixed because the code compiles.

If three attempts produce the same failure with no new evidence, change the diagnostic approach rather than repeating the same patch.

If the next step genuinely needs unavailable hardware, a prohibited kernel replacement, or an owner action, preserve the exact blocker and executable checkpoint. Continue any independently actionable touch-UI work.

No false success and no unbounded destructive retry loops.

# 16. SAFE LIVE DEPLOYMENT

Use the existing Mac-compatible USB live-console tools.

For each deployment:

1. Verify console reachability.
2. Record current device state.
3. Back up the target file.
4. Record original checksum.
5. Build the new artifact for Fedora ARM64 if necessary.
6. Run tests.
7. Verify architecture and dependencies.
8. Transfer files safely.
9. Verify destination checksums.
10. Atomically install.
11. Restart only the necessary component.
12. Verify the component starts.
13. Verify the graphical system remains usable.
14. Run physical input testing.
15. Roll back if the patch causes a regression.

Do not stop after a dry run.

Confirm that the changes actually reached the phone.

Preserve the original functioning live console and framebuffer bridge.

# 17. REQUIRED AUTOMATED TESTS

Implement or extend tests for:

## Taps

- Touch down/up.
- No false swipe classification.
- Correct icon hit testing.
- Click callback invocation.
- Application launch.
- Application close.
- Repeated icon taps.

## Horizontal navigation

- Left swipe.
- Right swipe.
- Boundary clamping.
- Page selection.
- Page indicator update.
- App clickability on both pages.
- Incomplete swipe cancellation.

## Vertical navigation

- Downward swipe to top panel.
- Upward swipe to application drawer.
- Reverse swipe to dismiss.
- Swipe from center.
- Swipe from left.
- Swipe from right.
- Overlay cleanup.
- App opening from drawer.

## Gesture conflicts

- Ordinary tap must not open panels.
- Scroll must not accidentally navigate away.
- Horizontal swipe must not open the drawer.
- Vertical swipe must not change desktop page.
- Double delivery of pointer/touch events must not trigger duplicate actions.
- Gesture must release ownership after touch-up/cancel.

## Rendering

- Application launch causes a new visible frame.
- Panel open causes a new frame.
- Desktop page change causes a new frame.
- Closing a panel restores the underlying UI.
- No stale fullscreen window captures input.
- No dependency on a Power-button refresh.

Run existing repository tests first.

Preserve passing tests.

# 18. OBSERVABILITY AND PERSISTENCE

Write all current mission data into:

`docs/touchable/`

Include:

- `TODO.md`
- `RESUME.md`
- `BASELINE.md`
- `TOUCH-EVENTS.md`
- `APP-CLICKABILITY.md`
- `GESTURE-ENGINE.md`
- `DESKTOP-PAGES.md`
- `DEPLOYMENTS.md`
- `TEST-RESULTS.md`
- `OWNER-ACCEPTANCE.md`
- `FINAL-VERDICT.md`

Store raw trace captures in dated evidence directories.

Use exact timestamps, hashes, exit codes and test results.

If execution ends because of the inference runtime or context budget, leave a precise continuation point so the next run can immediately resume.

Do not overwrite original diagnostic evidence.

# 19. STRICT COMPLETION CRITERIA

The mission is complete only when the following are true:

- [ ] Physical taps open applications.
- [ ] Applications respond to touch.
- [ ] Applications can be closed.
- [ ] Home navigation works.
- [ ] Swipe LEFT moves to Desktop 2.
- [ ] Swipe RIGHT returns to Desktop 1.
- [ ] Both desktops have clickable icons.
- [ ] Swipe DOWN opens the top panel.
- [ ] Swipe UP opens the app drawer.
- [ ] These gestures work from anywhere on the Home workspace.
- [ ] Shared global gesture handling works across application surfaces as implemented and verified.
- [ ] Panels can be dismissed.
- [ ] App drawer icons open applications.
- [ ] No invisible fullscreen overlay intercepts touches.
- [ ] Normal app scrolling remains usable.
- [ ] GUI refreshes without Power-button intervention.
- [ ] Multiple 90-second physical test rounds completed.
- [ ] Owner confirms successful interaction.
- [ ] All related regression tests pass.
- [ ] Working userspace changes are actually deployed to the S10+.
- [ ] Evidence is saved and accurate.

Do not declare full success if any required item fails or remains unverified.

Report partial progress honestly.

# 20. FINAL EXECUTION DIRECTIVE

START NOW.

FIRST:

Fix actual application icon clickability.

SECOND:

Make every application escapable.

THIRD:

Implement and verify the second desktop page.

FOURTH:

Implement global swipe-down and swipe-up navigation.

FIFTH:

Run real physical 90-second test windows.

SIXTH:

Fix every reproducible issue found.

SEVENTH:

Repeat testing until the owner can operate the interface reliably.

DO NOT REWRITE NUXEL.

DO NOT FLASH ANYTHING.

DO NOT WORK ON UNRELATED FEATURES.

DO NOT RETURN ONLY A PLAN.

DO NOT DECLARE SYNTHETIC SUCCESS.

**REAL FINGER → REAL APP OPENS.**

**SWIPE LEFT → DESKTOP 2.**

**SWIPE RIGHT → DESKTOP 1.**

**SWIPE DOWN → QUICK SETTINGS.**

**SWIPE UP → APPLICATION DRAWER.**

**ALL FROM THE EXISTING NUXEL INTERFACE.**

**NO POWER-BUTTON REDRAW TRICKS.**

**90-SECOND TEST → ANALYZE → FIX → DEPLOY → 90-SECOND RETEST.**

## CYBER-TIEL 35B — OPERATION TOUCHABLE. 🐧🔥
