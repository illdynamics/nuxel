# 🐧🔐🔥 NUXEL A45 — OPERATION KEYBOARD RESURRECTION & PENGUIN LOCKSCREEN

## FULL ENGINEERING MISSION — RESTORE WORKING SMARTPHONE KEYBOARD, IMPLEMENT PENGUIN DRAG-TO-UNLOCK, SCREEN TIMEOUT, POWER MANAGEMENT AND BOOT LOCK

**Project:** Nuxel — Linux on the Google Pixel

**Target hardware:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820

**System:** Fedora ARM64, Phoc/Wayland, WebKitGTK, Nuxel Home

**Execution environment:** Local development machine with live USB console access to the running S10+.

**Mode:** AUTONOMOUS IMPLEMENTATION, BUILD, TEST, SAFE LIVE DEPLOYMENT, PHYSICAL ACCEPTANCE AND REPAIR.

**Priority:** CRITICAL.

---

# 0. MISSION OBJECTIVE

Deliver two major functional improvements to Nuxel:

**MISSION A — KEYBOARD RESURRECTION**

Recover the previously observed working black/blue/grey smartphone keyboard, make it the default graphical keyboard, eliminate the broken keyboard, and ensure actual text insertion works inside graphical applications.

**MISSION B — PENGUIN LOCKSCREEN**

Implement Nuxel's first real graphical lockscreen, using the original owner-supplied artwork:

- Lockscreen wallpaper: `./assets/nuxel-lockscreen.jpg`
- Draggable unlock icon: `./assets/nuxel-lockhead.png`

The user must physically touch and drag the **penguin lockhead PNG upward** to unlock.

The lockhead must be positioned so that it does **NOT obscure or overlap the penguin already illustrated in the lockscreen wallpaper**.

Additionally:

- Boot into the lockscreen.
- Lock when the screen turns off.
- Show the lockscreen after waking.
- Automatically switch the display off after 60 seconds of inactivity.
- Add configurable timeout settings to Nuxel Home Settings.
- Preserve running applications.
- Preserve the persistent Back/Penguin Home/Recents navigation system.
- Maintain working live USB console recovery.

This is NOT a mockup mission.

Implement real behavior, deploy it, test the physical phone, repair failures and provide evidence.

---

# PART A — RESTORE THE WORKING KEYBOARD

## 1. INVESTIGATE THE SECOND KEYBOARD THAT ACTUALLY WORKED

During the previous A44 repair attempt, a SECOND keyboard briefly appeared above the existing Nuxel keyboard.

The user observed:

- Black and grey keys.
- Blue accents.
- Smartphone/Gboard-like appearance.
- Proper touchscreen responsiveness.
- Correct typing into graphical text fields.
- It appeared ABOVE the old keyboard.
- The existing broken keyboard remained underneath.

**This is the keyboard we want to restore permanently.**

Do not write a third keyboard without first identifying the working implementation.

### 1.1 Identify its origin

Inspect the live graphical environment, running services, installed packages, A44 logs, and repository.

Check candidate implementations:

- Squeekboard
- wvkbd
- maliit-keyboard
- GTK/Phosh-related OSK components
- Phoc-compatible input methods
- Existing custom Nuxel keyboard
- Any temporary OSK installed or activated during A44

These are discovery candidates, not assumptions.

Determine:

1. Which executable displayed the working keyboard.
2. Which process or service launched it.
3. Which environment variables or D-Bus mechanisms activated it.
4. Which Wayland protocols it used.
5. Why it appeared above the existing keyboard.
6. Why its keys actually inserted text.
7. Why it disappeared.
8. Why the original keyboard failed.
9. Whether two input-method owners were fighting for focus.
10. Whether the working keyboard survived in an installed but disabled state.

Inspect journal logs, package histories, systemd units, compositor logs, Wayland protocol support and source changes from A44.

If logs do not identify it conclusively, test available candidate keyboards one at a time with reversible changes.

Ask for owner confirmation of its appearance before selecting the replacement.

**Do not identify a keyboard solely because its colors resemble Gboard.**

## 2. MAKE THE WORKING KEYBOARD NUXEL'S DEFAULT

Once identified:

- Enable the correct keyboard at session startup.
- Configure the actual Wayland input-method integration.
- Ensure it uses the correct Wayland display and seat.
- Ensure it can activate when an editable widget receives focus.
- Ensure it can send text to the real focused application.
- Ensure it survives launcher reloads.
- Ensure it survives app switching.
- Ensure it remains usable after lock/unlock.
- Ensure it works after a full reboot.

Use the appropriate supported text-input/input-method protocol.

Do not assume Phoc implements a specific version without verifying it.

Only one OSK may own the active graphical input-method role.

## 3. DISABLE THE OLD BROKEN KEYBOARD

Identify the old keyboard's:

- Source code.
- Activation hooks.
- UI overlay.
- CSS and JavaScript.
- Systemd or session startup configuration.
- Input event listeners.
- Haptic hooks.
- Focus handlers.

Remove it from the ACTIVE runtime.

Do not merely conceal the old keyboard with a higher z-index.

There must be:

- One visible keyboard.
- One active input-method owner.
- No duplicated keypresses.
- No invisible keyboard overlay.
- No old keyboard intercepting touch.
- No competing focus controllers.
- No simultaneous keyboard haptic events.

Preserve a rollback copy until the working keyboard passes physical acceptance.

Do not delete valuable historical source or assets prematurely.

## 4. REAL GRAPHICAL TEXT INPUT

The restored keyboard must type correctly into:

- Browser address bar.
- Browser search fields.
- Calendar event input.
- Nuxel Settings.
- Home search.
- Wi-Fi password input.
- File Explorer rename dialogs.
- Textareas.
- Contenteditable elements.
- Supported GTK editable controls.

Required keys:

- Letters.
- Numbers.
- Shift.
- Caps Lock where supported.
- Space.
- Backspace.
- Enter.
- Punctuation.
- Symbols.
- Cursor navigation where supported.

The input must result in real character insertion.

Generating synthetic untrusted JavaScript keyboard events is not a substitute for genuine native text input.

Do not expose a privileged input-injection API to arbitrary webpages.

## 5. REAL VISIBLE BLINKING CURSOR

When the user taps a text field:

1. Field receives actual focus.
2. Caret becomes visible.
3. Keyboard opens.
4. Caret remains visible.
5. Typing inserts text.
6. Caret moves with the text.
7. Selection and deletion work.
8. Caret deactivates when focus genuinely changes.

Inspect:

- GTK/WebKit focus.
- Wayland seat focus.
- CSS `caret-color`.
- Text-field contrast.
- Actual editable state.
- Selection state.
- OSK activation.
- Window focus ownership.

**Do not simulate the caret with a fake blinking CSS rectangle.**

## 6. KEYBOARD STACKING

When unlocked, the required hierarchy is:

**Working virtual keyboard**

Above:

**Active application window**

Above:

**Four-app Home shortcut dock**

With:

**Back / Penguin Home / Recents navigation dock always accessible at the bottom.**

The virtual keyboard must never appear underneath Calendar, Browser, Settings or File Explorer.

Applications must cover the four-app Home shortcut dock.

Applications must NEVER obscure the persistent three-button system navigation dock.

The keyboard should occupy space immediately above the three-button navigation region, rather than covering its controls.

Use native compositor layer/work-area behavior and supported keyboard geometry interfaces.

Do not rely on HTML z-index to reorder unrelated native Wayland windows.

## 7. SHOW/HIDE AND FOCUS MANAGEMENT

Implement reliable keyboard lifecycle handling.

On field selection:

- Activate OSK.
- Preserve application focus.
- Keep the field visible.
- Avoid duplicate activation.

On Hide Keyboard:

- Dismiss the OSK.
- Do not close the application.
- Restore content geometry.
- Avoid reopening automatically due to stale focus events.

On Home:

- Minimize the current application.
- Hide OSK.
- Return to Home Desktop 1.

On Back:

- Preserve the normal navigation behavior.
- Do not accidentally kill an application.

On Recents:

- Hide the keyboard where appropriate.
- Preserve the intended application state.

On lock:

- Dismiss OSK.
- Prevent underlying field interaction.

On unlock:

- Restore normal OSK availability.

## 8. KEYBOARD HAPTICS

Integrate with the existing Nuxel vibration subsystem.

Requirements:

- Subtle feedback per accepted keypress.
- No duplicate vibrations.
- No vibration on ordinary pointer movement.
- Nonblocking operation.
- Respect Home Settings keyboard-haptic preference.
- Preserve working navigation haptics.

If the working keyboard does not expose a compatible haptic callback, use a safe supported integration.

Do not sacrifice working text input to obtain optional haptics.

---

# PART B — NUXEL PENGUIN LOCKSCREEN

## 9. USE THE TWO EXACT OWNER-SUPPLIED ASSETS

**MANDATORY — DO NOT SUBSTITUTE THESE IMAGES.**

### Lockscreen background

`./assets/nuxel-lockscreen.jpg`

### Draggable penguin lockhead

`./assets/nuxel-lockhead.png`

Both are original Nuxel artwork.

Locate them in the actual repository, verify their file types and dimensions, inspect their contents, and ensure they are deployed to the active S10+ asset directory.

Preserve the original images and PNG transparency.

Use proper resource URLs and image scaling.

Do not replace the lockhead with:

- A generic padlock.
- An emoji.
- A CSS-drawn icon.
- A Unicode penguin.
- A substitute PNG.
- Text saying "Swipe to unlock."

**THE ACTUAL `nuxel-lockhead.png` IMAGE MUST BE THE DRAGGABLE UNLOCK HANDLE.**

---

# 10. VISUAL COMPOSITION — DO NOT COVER THE WALLPAPER PENGUIN

This requirement is extremely important.

The lockscreen background, `nuxel-lockscreen.jpg`, already contains a penguin illustration.

The `nuxel-lockhead.png` icon is a separate penguin-shaped unlock handle.

**The unlock handle must not overlap, obscure or visually interfere with the wallpaper penguin.**

### Implementation requirements

1. Inspect the actual wallpaper image.
2. Identify the approximate visible bounds of the penguin illustration within the wallpaper.
3. Identify the transparent and opaque bounds of `nuxel-lockhead.png`.
4. Establish safe screen regions for the lockhead.
5. Position the lockhead BELOW the wallpaper penguin, closer to the bottom of the screen.
6. Maintain visible spacing between both penguins.
7. Ensure the draggable handle remains easy to touch.
8. Ensure the icon remains entirely inside the visible lockscreen.
9. Preserve its aspect ratio and transparent background.
10. Check portrait scaling and screen rotation.
11. Verify the final composition on the physical S10+ display.

### Recommended initial position

Start with the lockhead centered horizontally in approximately the bottom 15–25% of the usable display.

Adjust its vertical position using the actual image composition, not an arbitrary fixed pixel offset.

Keep enough separation that the lockhead clearly reads as a separate interactive control.

Aim for at least 16–32 logical pixels of visible spacing between the lockhead's opaque artwork and the wallpaper penguin at the final displayed scale.

If the wallpaper penguin extends low enough to make the default position overlap, move the lockhead into a verified clear region rather than shrinking it until it becomes unusable.

### Responsive layout

The wallpaper may be rendered using cover/crop behavior.

Therefore, image-space coordinates and screen-space coordinates are not necessarily identical.

Compute or inspect the visible crop at the real S10+ aspect ratio.

Verify the placement at the actual deployed display resolution and compositor scaling.

Do not claim nonoverlap based only on CSS declarations.

### Final composition

The screen should visually communicate:

- Nuxel wallpaper.
- Main penguin illustration unobstructed.
- Current time and date.
- Separate penguin lockhead near the bottom.
- Small upward swipe hint.
- Clean spacing and polished alignment.

**TWO PENGUINS. ZERO OVERLAP.**

---

# 11. THE LOCKHEAD ITSELF MUST MOVE WHEN DRAGGED

**This is not a swipe-anywhere screen.**

The user must interact with the actual penguin lockhead.

### Required behavior

1. Display `nuxel-lockhead.png` at its resting position.
2. User touches the lockhead.
3. Start a drag session.
4. The lockhead follows the finger upward in real time.
5. Optionally increase glow/brightness subtly as progress increases.
6. When moved past the unlock threshold, complete unlock.
7. Animate the lockhead and lockscreen out smoothly.
8. Reveal the unlocked Nuxel session.

### Unsuccessful drag

If the user:

- Releases too early.
- Moves sideways without enough upward travel.
- Cancels the touch.
- Drags only a few pixels.

Then:

- Do NOT unlock.
- Animate the lockhead smoothly back to its resting position.
- Reset the drag state.
- Wait for the next valid gesture.

### Technical details

Implement a dedicated drag state machine:

`IDLE → TOUCH_CAPTURED → DRAGGING → THRESHOLD_REACHED → UNLOCKING → UNLOCKED`

And cancellation:

`DRAGGING → CANCELLED → RETURN_TO_REST → IDLE`

Use pointer capture or the appropriate compositor-level touch ownership mechanism.

Do not lose the drag because the finger leaves the icon's original rectangle.

Prevent duplicate unlock triggers.

Prevent application, Home and drawer swipe handlers from processing the lockhead gesture.

Use a physically tested upward threshold, initially around 20–25% of usable display height.

Tune for reliable one-handed operation.

### Important visual behavior

The resting lockhead must not cover the wallpaper penguin.

During a deliberate upward unlock drag, transient overlap may occur as the icon follows the finger; apply the designed animation so the moving icon remains clear and readable.

The resting position, which the user sees every time they wake the phone, must remain visually unobstructed and properly composed.

---

# 12. LOCKSCREEN UI

Create a polished Nuxel lockscreen containing:

- Full-screen `nuxel-lockscreen.jpg` wallpaper.
- Current time.
- Current date.
- Battery percentage.
- Charging indication.
- Real Wi-Fi/connection state where available.
- `nuxel-lockhead.png` draggable unlock handle.
- Subtle swipe-up hint.

No generic mobile theme replacements.

Keep the Nuxel visual identity.

Avoid unnecessary overlays that darken or obscure the artwork.

The clock and date should remain readable.

Do not place large UI elements over the wallpaper penguin.

The lockhead should look like an integral part of Nuxel's artwork.

---

# PART C — REAL LOCK STATE AND SCREEN POWER

## 13. IMPLEMENT AN ACTUAL LOCK STATE

Introduce a coherent graphical lock lifecycle.

Required states:

- `BOOT_LOCKED`
- `LOCKED_SCREEN_ON`
- `LOCKED_SCREEN_OFF`
- `UNLOCKING`
- `UNLOCKED`

The application launcher and foreground windows must not receive ordinary graphical touch input while locked.

This must be enforced at the supported compositor/session input layer, not merely by placing an HTML overlay above Home.

Prevent:

- Touch-through to applications.
- Home button bypass.
- Recents bypass.
- Back button bypass.
- App drawer gesture bypass.
- Keyboard input reaching hidden application fields.
- An unlocked Home frame appearing briefly during boot.

If the compositor exposes native session-lock support, investigate and use a suitable supported approach.

Do not invent protocol support or weaken existing authenticated system security.

### Security model

This first unlock method is SWIPE ONLY.

It provides accidental-interaction protection and a mobile-style lockscreen.

It does NOT provide user authentication.

Design for future PIN/password/biometric authentication without pretending those methods already exist.

---

# 14. BOOT INTO LOCKSCREEN

**DEFAULT: LOCKED AT BOOT.**

After starting Nuxel:

1. Start required low-level services.
2. Initialize compositor and graphical session.
3. Establish the locked state before user-interactive Home becomes accessible.
4. Show the Nuxel lockscreen.
5. Display the correct wallpaper and lockhead.
6. Wait for a valid upward drag.
7. Unlock.
8. Show Nuxel Home Desktop 1.

Do not automatically unlock after the boot animation.

Do not briefly show Home before presenting the lockscreen.

Do not automatically unlock because a launcher service restarts.

Do not let a UI crash cause an unintentional unlock.

Preserve a documented, authorized USB recovery route.

---

# 15. POWER BUTTON LOCK AND WAKE

When the screen is ON and unlocked:

**Power button → Lock → Display OFF.**

When the screen is OFF:

**Power button → Display ON → Lockscreen.**

Do not return directly to an unlocked application.

Required sequence:

1. Receive Power event.
2. Establish graphical lock state.
3. Hide OSK.
4. Block underlying graphical input.
5. Request real display power-down.
6. Preserve application processes.
7. Wait for wake.
8. Power the display on.
9. Show the lockscreen.
10. Unlock only after a valid lockhead drag.

Preserve existing long-press Power behavior and approved hardware shortcuts.

Avoid double-processing Power events from multiple input daemons.

---

# 16. REAL AUTOMATIC SCREEN TIMEOUT

**DEFAULT TIMEOUT: 60 SECONDS.**

After one minute of genuine user inactivity:

1. Enter the locked state.
2. Hide OSK.
3. Preserve running applications.
4. Physically turn the display off through a supported display-power mechanism.
5. Remain locked.
6. Wake to lockscreen after Power press.

Do not fake a screen-off event using a black CSS rectangle.

Investigate supported Phoc/Wayland, logind, DRM, backlight and power-management interfaces.

Use the safest existing supported mechanism.

Do not disable the only working display output without a recovery path.

Do not suspend the entire device unless an explicitly supported suspend policy requests it.

---

# 17. IDLE TIMER OWNERSHIP

Implement ONE authoritative screen-idle manager.

Reset the idle timer upon real activity:

- Touch.
- Drag.
- Scroll.
- Keyboard input.
- Navigation input.
- Supported physical buttons.

Do NOT reset it because of:

- Background animations.
- System-monitor updates.
- Network polling.
- JavaScript interval timers.
- Logs.
- Inactive app rendering.
- Internal telemetry.

Use monotonic timing.

Avoid multiple independent timeout services competing to turn the screen on/off.

Prevent race conditions between Power events and timeout expiry.

Do not waste battery with constant high-frequency polling.

---

# 18. HOME SETTINGS — DISPLAY AND LOCKSCREEN

Add a real Settings section:

**Home Settings → Display & Lockscreen**

### Screen Timeout

Options:

- 15 seconds
- 30 seconds
- **1 minute — default**
- 2 minutes
- 5 minutes
- 10 minutes
- Never, if supported, with a power-consumption warning

When changed:

- Persist the preference.
- Apply the new timeout immediately.
- Update the actual idle manager.
- Maintain the setting across reboots.
- Display the active selected value.

### Lockscreen

Provide:

- Lockscreen: Enabled by default.
- Unlock method: Swipe Penguin Up.
- Lockscreen wallpaper: Nuxel Default.
- Show Clock: ON.
- Show Date: ON.
- Show Battery: ON.

Do not present nonexistent PIN/biometric methods as functional.

If a lockscreen-disable option is implemented, treat it only as a convenience-lock setting and never permit it to bypass real authenticated session security.

---

# 19. UNLOCK DESTINATION AND SESSION PRESERVATION

### After boot

Unlock → Nuxel Home Desktop 1.

### After normal sleep or timeout

Unlock → Restore the previous application and UI state where supported.

Do not kill apps because the screen is locked.

Do not reload Browser, Calendar or Settings unnecessarily.

Do not forget open app state or erase fields when locking unless privacy/security handling requires it.

Ensure the keyboard can be reactivated normally after unlocking.

Do not leave the previous keyboard visible on the lockscreen.

---

# PART D — SURFACE STACKING

## 20. EXACT REQUIRED LAYERING

### When unlocked and using Home

- Normal Home content.
- Four-app shortcut dock.
- Persistent three-button navigation dock.
- No OSK unless editable content requires one.

### When unlocked and using an application

- Foreground application covers Home and four-app shortcut dock.
- Three-button navigation dock remains persistent and usable.
- Virtual keyboard displays above the application's editable content.
- Keyboard stops above the reserved navigation area.

### When locked and screen ON

- Lockscreen is the topmost ordinary-user interaction surface.
- Owner-supplied wallpaper visible.
- Draggable lockhead visible.
- Underlying applications cannot receive touch.
- Existing normal navigation does not bypass locking.
- Virtual keyboard is hidden.

### When locked and screen OFF

- Physical display blanked.
- Graphical session still locked.
- Apps preserved.
- USB recovery still available.

Solve stacking using actual compositor and supported graphical-session mechanisms.

Do not rely solely on CSS z-index where native Wayland surfaces are involved.

---

# PART E — TESTING AND LIVE DEPLOYMENT

## 21. AUTOMATED REGRESSION TESTS

Add tests covering:

### Keyboard

- Correct working OSK selected.
- Old OSK disabled.
- Single active keyboard instance.
- Real text insertion.
- Real blinking caret.
- Shift/Space/Backspace/Enter.
- Password field focus.
- Browser URL typing.
- Hide/reopen.
- Keyboard/app stacking.
- App/shortcut dock stacking.
- Navigation-dock accessibility.
- Keyboard haptics.

### Lockscreen

- Wallpaper asset loads.
- Exact lockhead PNG loads.
- Correct PNG transparency.
- Resting lockhead is below wallpaper penguin.
- No overlap at target display scaling.
- Dragging moves the actual lockhead.
- Incomplete drag snaps back.
- Cancelled drag does not unlock.
- Valid upward drag unlocks.
- App input blocked while locked.
- Home/Recents cannot bypass lock.
- Boot starts locked.
- Power wake starts locked.

### Timeout

- Default 60 seconds.
- Configurable timeout.
- Persistence.
- Real idle event ownership.
- Display power-off.
- Wake-to-lockscreen.
- Apps preserved after locking.
- No duplicate timeout handlers.
- No screen-off caused by background animations.
- No USB-console regression.

Distinguish unit tests from actual device integration and physical confirmation.

---

# 22. SAFE LIVE USB DEPLOYMENT

The phone is already running Nuxel.

Use the existing live USB console.

**DO NOT FLASH.**

### Required deployment order

1. Inspect repository state.
2. Identify active services.
3. Confirm USB session recovery.
4. Back up current OSK, graphical-session, launcher and settings files.
5. Record rollback commands and hashes.
6. Recover working keyboard.
7. Implement its permanent activation.
8. Deploy keyboard changes.
9. Verify actual typing.
10. Only then deactivate the old keyboard.
11. Implement lockscreen UI and input isolation.
12. Verify exact original artwork.
13. Verify lockhead positioning visually.
14. Verify actual drag-to-unlock.
15. Implement idle manager and screen power control.
16. Verify screen-off/wake behavior.
17. Enable boot-to-lockscreen once the unlock path is proven.
18. Test startup and service recovery.
19. Restart only affected services.
20. Carry out owner physical acceptance.
21. Perform an authorized reboot after recoverability is verified.
22. Confirm boot-to-lockscreen.
23. Fix any failures before marking complete.

Avoid losing the live USB console.

Avoid modifying boot-critical services without an independent recovery mechanism.

---

# 23. PHYSICAL ACCEPTANCE — KEYBOARD

Announce:

**"NUXEL A45 KEYBOARD TEST READY."**

Request owner verification:

1. Open Calendar.
2. Tap an editable field.
3. Confirm only the working black/grey/blue keyboard appears.
4. Confirm the old broken keyboard is gone.
5. Confirm real blinking cursor.
6. Type `NUXEL PENGUIN KEYBOARD WORKS 123`.
7. Test Shift, Space, Backspace and Enter.
8. Hide the keyboard.
9. Open it again.
10. Open Browser and type a URL.
11. Confirm navigation buttons remain accessible.
12. Confirm keyboard appears above application content.
13. Confirm key haptics if supported.

Record each actual result.

---

# 24. PHYSICAL ACCEPTANCE — PENGUIN LOCKSCREEN

Announce:

**"NUXEL A45 PENGUIN LOCKSCREEN TEST READY."**

Request the following physical test:

1. Turn the screen off.
2. Wake the screen.
3. Confirm `nuxel-lockscreen.jpg` displays correctly.
4. Confirm the background penguin is completely visible.
5. Confirm `nuxel-lockhead.png` appears lower on the display.
6. Confirm the lockhead does NOT cover the penguin illustration.
7. Touch the actual lockhead.
8. Drag it a short distance upward and release.
9. Confirm it returns smoothly to its resting position.
10. Drag the lockhead far enough upward.
11. Confirm the lockscreen unlocks.
12. Confirm Home or the previous application appears as appropriate.
13. Press Power to lock and switch off the display.
14. Wake and confirm lockscreen returns.
15. Unlock again.
16. Configure 1-minute timeout.
17. Wait 60 seconds without touching the phone.
18. Confirm the actual display turns off.
19. Wake and confirm lockscreen appears.
20. Unlock and verify application state survived.
21. Test that the working keyboard still types after unlocking.
22. Reboot safely.
23. Confirm Nuxel boots into the lockscreen.
24. Unlock by dragging the penguin lockhead upward.

Collect live graphical logs and owner feedback.

Repair failures and retest the affected behavior.

---

# 25. REQUIRED ACCEPTANCE REPORT

Produce this matrix:

| Component | Source implemented | Live tested | Owner confirmed |
|---|---|---|---|
| Previously working OSK identified | | | |
| Working OSK restored | | | |
| Broken OSK disabled | | | |
| Actual text insertion | | | |
| Blinking caret | | | |
| Keyboard above applications | | | |
| App above four-icon dock | | | |
| Three-button dock accessibility | | | |
| OSK show/hide | | | |
| Keyboard haptics | | | |
| Exact lockscreen JPG | | | |
| Exact penguin lockhead PNG | | | |
| Lockhead positioned below wallpaper penguin | | | |
| No resting artwork overlap | | | |
| Real lockhead drag movement | | | |
| Incomplete-drag reset | | | |
| Successful swipe unlock | | | |
| Underlying touch blocked while locked | | | |
| Boot directly into lockscreen | | | |
| Power-button lock/wake | | | |
| 60-second display timeout | | | |
| Timeout Settings persistence | | | |
| Real screen power-down | | | |
| Application state preserved | | | |
| Keyboard working after unlock | | | |

Include:

- Keyboard identity and executable.
- Root cause of the original keyboard failure.
- Wayland protocol evidence.
- Modified source paths.
- Deployed files.
- Live service configuration.
- Asset SHA-256 checks.
- Actual lockscreen screenshots.
- Lockhead placement verification.
- Timing and gesture behavior.
- Test results.
- Commit hashes.
- Live deployment evidence.
- Recovery and rollback instructions.
- Outstanding blockers with precise evidence.

Do not mark the lockscreen visually complete without seeing the original background penguin unobstructed and the separate lockhead correctly positioned.

---

# 26. ABSOLUTE NON-NEGOTIABLE RULES

- NO FLASHING.
- NO PARTITION WRITES.
- NO BOOTLOADER CHANGES.
- NO KERNEL IMAGE REPLACEMENT.
- NO LOSS OF LIVE USB RECOVERY.
- NO TWO SIMULTANEOUS KEYBOARDS.
- NO FAKE TEXT INPUT.
- NO FAKE BLINKING CARET.
- NO REPLACEMENT OF OWNER ARTWORK.
- NO GENERIC UNLOCK ICON IN PLACE OF THE PENGUIN LOCKHEAD.
- NO STATIC LOCKHEAD THAT CANNOT BE DRAGGED.
- NO LOCKHEAD RESTING OVER THE WALLPAPER PENGUIN.
- NO FAKE SCREEN OFF USING A BLACK HTML OVERLAY.
- NO TOUCH-THROUGH WHILE LOCKED.
- NO CLAIM THAT SWIPE UNLOCK PROVIDES SECURE AUTHENTICATION.
- NO CLAIMED SUCCESS WITHOUT ACTUAL DEVICE TESTING.
- NO BOOT-TIME LOCK ENFORCEMENT UNTIL A RECOVERY PATH IS VERIFIED.

---

# FINAL EXECUTION INSTRUCTION

**FIRST:** Identify and permanently restore the previously working black/blue/grey smartphone keyboard.

**SECOND:** Disable the original broken keyboard and fix real input focus and caret behavior.

**THIRD:** Build the Nuxel lockscreen using the exact images:

`./assets/nuxel-lockscreen.jpg`

`./assets/nuxel-lockhead.png`

**FOURTH:** Position the penguin lockhead visibly BELOW the penguin in the wallpaper, with proper spacing and zero resting overlap.

**FIFTH:** Make the penguin lockhead itself draggable upward to unlock.

**SIXTH:** Implement real automatic screen-off after 60 seconds, configurable through Home Settings.

**SEVENTH:** Make Power off/wake require the lockscreen and make every normal boot begin locked.

**EIGHTH:** Deploy safely, physically test the S10+, fix failures, and report evidence.

## FINAL TARGET EXPERIENCE

**Boot Nuxel → Penguin Lockscreen → Drag Penguin Lockhead Up → Home → Open App → Tap Field → Working Keyboard → Type → Power Off → Wake → Penguin Lockscreen Again.**

**TWO PENGUINS. ZERO OVERLAP. ONE WORKING KEYBOARD. ONE REAL LOCKSCREEN.**

**GO BUILD IT. 🐧🔐🔥**
