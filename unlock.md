# 🐧🔓🔥 NUXEL A45.1 — OPERATION FREE THE PENGUIN

## CRITICAL HOTFIX — PENGUIN LOCKHEAD DRAGS BUT LOCKSCREEN NEVER UNLOCKS

**Project:** Nuxel — Linux on the Google Pixel  
**Device:** Samsung Galaxy S10+ SM-G975F · Exynos 9820  
**Runtime:** Fedora ARM64 · Phoc/Wayland · WebKitGTK  
**Execution:** Autonomous root-cause investigation, implementation, tests, safe live USB deployment and physical verification.

## CURRENT STATUS — IMPORTANT

The new Nuxel penguin lockscreen looks fantastic and is already displaying successfully on the physical S10+.

Confirmed functioning:

- Custom lockscreen wallpaper renders correctly.
- `./assets/nuxel-lockscreen.jpg` displays beautifully.
- `./assets/nuxel-lockhead.png` appears correctly.
- The lockhead follows the finger smoothly during dragging.
- The touchscreen is delivering movement events.
- The lockscreen is reachable on the live phone.

**ONLY CURRENT FAILURE: Dragging the penguin lockhead upward does not actually unlock the screen.**

Your task is to fix this last failure without redesigning, replacing or breaking the existing lockscreen.

**DO NOT REBUILD THE LOCKSCREEN FROM SCRATCH.**

---

# PHASE 1 — IDENTIFY THE EXACT ROOT CAUSE

Trace the complete unlock lifecycle:

`Touch lockhead → pointer capture → drag movement → threshold detection → pointer release → unlock request → authoritative lock-state transition → compositor/session unlock → restore application input → dismiss lockscreen`

Inspect the actual implementation and log each stage.

Determine whether the failure occurs because:

1. The unlock-distance threshold is unreachable or computed incorrectly.
2. Screen coordinates and element-local coordinates are being mixed.
3. The logic expects the lockhead to reach a position it physically cannot reach.
4. A CSS transform visually moves the icon but doesn't update the internal drag distance.
5. `pointerup`, `touchend` or an equivalent release event is missing.
6. Pointer capture is lost when the finger leaves the original icon bounds.
7. A drag-completion event is cancelled.
8. The unlock callback executes but throws an exception.
9. The UI visually recognizes the gesture but never calls the session unlock service.
10. A bridge API is missing, disconnected, or returning an error.
11. The compositor remains locked even though frontend state changes.
12. A lockscreen overlay remains mounted after unlocking.
13. A service restarts or resets the lock state immediately after the gesture.
14. An async unlock request is never awaited or its response is ignored.
15. A stale cached WebKit JavaScript bundle is running instead of the newest implementation.

Do not guess. Trace the actual first broken stage.

### Temporary diagnostic instrumentation

Log a short structured record containing:

- Pointer ID.
- Pointer-down coordinates.
- Current pointer coordinates.
- Signed upward displacement.
- Effective threshold.
- Whether the threshold was reached.
- Pointer-up/cancel state.
- Unlock callback invocation.
- Backend acknowledgement or error.
- Authoritative lock state before/after.
- Lockscreen visibility before/after.

Do not record passwords, personal content or unrelated touch data.

Keep the diagnostic logs bounded and remove noisy tracing after successful repair.

---

# PHASE 2 — FIX THE ACTUAL DRAG COMPLETION

The lockhead already follows the finger correctly. Preserve that behavior.

Implement a reliable drag lifecycle:

`IDLE → DRAGGING → THRESHOLD_REACHED → UNLOCK_REQUESTED → UNLOCKED`

And cancellation:

`DRAGGING → CANCELLED → RETURN_TO_REST → IDLE`

### Required behavior

1. Touch the actual penguin lockhead.
2. Capture that pointer.
3. Begin tracking upward displacement.
4. Move the lockhead with the finger.
5. Detect the unlock threshold correctly.
6. On release, if the threshold was reached, request unlock.
7. Wait for the actual unlock result.
8. Dismiss the lockscreen only after a successful authorized state transition.
9. Restore normal Home/application interaction.
10. Ignore duplicate events from the same gesture.

### Coordinate correctness

Use a consistent coordinate system such as viewport CSS pixels derived from `clientY`, converted consistently where compositor scaling requires it.

For a conventional upward gesture:

`upwardDistance = startY - currentY`

The unlock threshold must be physically reachable on the S10+.

Start with a threshold around **20–25% of the usable lockscreen height**, but clamp it to the available drag travel and tune it through live testing.

If the lockhead starts near the bottom, verify that the threshold fits within the distance to the top safe area.

Do not compare transformed visual coordinates against untranslated original coordinates.

### Pointer release handling

A successful swipe must be evaluated when the user releases the finger.

Handle:

- `pointerdown`
- `pointermove`
- `pointerup`
- `pointercancel`
- `lostpointercapture`

Or the matching supported touch-event APIs, without double-processing the same gesture.

Use pointer capture where appropriate, and do not lose the completion event simply because the lockhead has moved outside its original element rectangle.

When the threshold is reached, visually acknowledge it subtly, then unlock when the release completes.

A deliberate drag that doesn't reach the threshold must return the lockhead smoothly to its starting position.

---

# PHASE 3 — CONNECT THE GESTURE TO THE REAL LOCK STATE

**THIS IS LIKELY THE MOST IMPORTANT STAGE.**

The penguin lockhead cannot merely animate upward. It must cause the actual lockscreen controller to transition from locked to unlocked.

Inspect whether the application uses:

- A native Wayland session-lock protocol.
- A Nuxel lock manager.
- A local D-Bus service.
- An authenticated local IPC bridge.
- A compositor-managed lock surface.
- A WebKit-hosted lockscreen backed by a native session controller.

Identify the authoritative component responsible for locking the graphical session.

Use its existing unlock method instead of creating a competing lock-state variable.

The expected transition is:

`LOCKED_SCREEN_ON → UNLOCKING → UNLOCKED`

On successful swipe, the trusted lockscreen controller must:

1. Verify this is the active lockscreen instance.
2. Accept the completed swipe-only unlock action.
3. Change its authoritative state to `UNLOCKED`.
4. Release the compositor/session lock through the supported mechanism.
5. Restore input focus and ordinary application interaction.
6. Remove the lockscreen surface.
7. Clear stale keyboard/input suppression.
8. Resume normal display-idle tracking.

Do not only set something like `locked = false` in WebKit while leaving the actual session locked.

Do not just hide the DOM while the compositor still blocks underlying input.

### Important security constraint

This is intentionally a convenience-only swipe lockscreen, not PIN authentication.

The unlock request must still originate from the trusted lockscreen controller, not an unrestricted browser API accessible to arbitrary applications or websites.

Do not bypass an existing separate authenticated security lock.

Do not introduce a globally callable privileged unlock endpoint.

---

# PHASE 4 — REMOVE THE LOCKSCREEN COMPLETELY AFTER UNLOCK

After a successful unlock:

- The lockscreen disappears smoothly.
- The penguin lockhead disappears with it.
- No invisible overlay remains.
- Touch events reach the active application or Home.
- The persistent Back/Penguin Home/Recents navigation works.
- The four-app shortcut dock behaves normally.
- The graphical keyboard can activate again.
- No keyboard remains wrongly suppressed by the previous lock state.
- The idle manager returns to normal unlocked operation.

### Correct destination

**After cold boot:** Show Home Desktop 1.

**After Power lock or idle timeout:** Restore the previously active application/session where supported, preserving its state.

Do not reload the entire UI or kill running applications just to dismiss the lockscreen.

---

# PHASE 5 — PREVENT IMMEDIATE RELOCK

Inspect for a second possible failure: unlocking succeeds momentarily but the idle service, Power handler or duplicate lock controller immediately re-locks the display.

Check:

- Multiple lockscreen instances.
- Duplicate lock managers.
- Idle timer expiry during unlock.
- Failure to reset inactivity timestamp.
- Pending Power-button release events.
- Replayed lock requests.
- Session state synchronization.
- Competing frontend/backend state variables.

On a successful unlock, reset the relevant idle timer once, cancel obsolete pending lock transitions and establish a fresh unlocked session state.

Do not disable automatic lock permanently.

The existing one-minute screen timeout must continue working.

---

# PHASE 6 — PRESERVE THE CURRENT DESIGN

Absolutely preserve:

- `./assets/nuxel-lockscreen.jpg`
- `./assets/nuxel-lockhead.png`
- Lockhead position.
- Wallpaper composition.
- Existing penguin graphics.
- Lockhead transparency and glow.
- Current smooth drag motion.
- Current visual styling.
- Clock and date.
- Battery/status indicators.
- Screen timeout settings.
- Power-button lock/wake.
- Boot-to-lockscreen.

**DO NOT CHANGE THE LOCKHEAD ARTWORK OR MOVE IT BACK OVER THE BACKGROUND PENGUIN.**

This is a functional hotfix, not a visual redesign.

---

# PHASE 7 — ADD AUTOMATED REGRESSION TESTS

Create focused tests verifying:

1. A small drag does not unlock.
2. A sufficient upward drag does unlock.
3. Release outside the original lockhead hitbox still completes the gesture.
4. Pointer cancellation does not unlock.
5. Downward movement does not unlock.
6. A tap without an upward drag does not unlock.
7. Only one unlock request occurs per gesture.
8. Backend unlock errors do not falsely hide the lockscreen.
9. Successful backend acknowledgement dismisses the lockscreen.
10. Locked state blocks interaction with ordinary applications.
11. An unlocked session restores application input.
12. The next Power-button lock still works.
13. Screen timeout still locks after 60 seconds.
14. A subsequent wake shows the lockscreen again.
15. Repeated lock/unlock cycles do not accumulate duplicate handlers.
16. Keyboard focus is usable after unlock.
17. Cold boot still begins at the lockscreen.

Distinguish mocked tests from actual Wayland/compositor integration tests.

---

# PHASE 8 — LIVE USB HOTFIX DEPLOYMENT

The S10+ is already running Nuxel.

Use the existing MacBook USB console.

**NO FLASHING, NO KERNEL CHANGES, NO PARTITION WRITES.**

Required sequence:

1. Verify working USB console.
2. Inspect active lockscreen process and source revision.
3. Identify actual deployed lockscreen JS/backend files.
4. Back up the current working lockscreen and state-controller components.
5. Record rollback steps.
6. Implement the smallest correct root-cause fix.
7. Run regression tests.
8. Deploy the patch through the existing live userspace deployment method.
9. Verify deployed file hashes.
10. Restart only affected userspace services.
11. Ensure the compositor and USB recovery session remain available.
12. Inspect runtime logs.
13. Run the physical unlock test.
14. Repair any remaining failure immediately.
15. Verify Power lock and timeout locking again.

Do not reboot unnecessarily.

---

# PHASE 9 — 60-SECOND OWNER ACCEPTANCE

Announce:

**"🐧🔓 PENGUIN UNLOCK HOTFIX READY — PLEASE TEST!"**

Ask the owner to:

1. Wake the S10+.
2. Observe the lockscreen.
3. Drag the penguin lockhead a short distance up and release.
4. Verify the icon returns to its resting position.
5. Drag the penguin lockhead all the way up.
6. Release.
7. Verify the lockscreen disappears.
8. Verify Home Desktop 1 or the previous application appears.
9. Touch an application.
10. Verify actual interaction works.
11. Press Power to lock.
12. Wake the phone.
13. Unlock again.
14. Verify the keyboard remains functional after unlocking.

Then perform a separate screen-timeout regression test.

Do not claim success based solely on logs or an animated unlock transition.

---

# FINAL ACCEPTANCE GATE

| Requirement | Expected outcome |
|---|---|
| Existing lockscreen appearance | Unchanged |
| Penguin lockhead drag | Smooth and responsive |
| Short drag | Snaps back, remains locked |
| Full upward drag | Unlocks |
| Actual session unlock | Confirmed |
| Lockscreen dismissed | Confirmed |
| Home/app receives touch | Confirmed |
| Keyboard after unlock | Functional |
| Power lock and wake | Functional |
| Boot-to-lockscreen | Preserved |
| 60-second idle lock | Preserved |
| No unlock bypass | Confirmed |

Produce a final report with exact source changes, root cause, commit hash, live deployment logs, physical acceptance results and rollback instructions.

**DO NOT ADD A SECOND LOCKSCREEN. DO NOT REWRITE THE ARTWORK. DO NOT BREAK THE WORKING DRAG.**

## FINAL INSTRUCTION

The penguin already moves beautifully.

**MAKE THE PENGUIN ACTUALLY UNLOCK NUXEL.**

Trace the gesture's release event, repair the unlock threshold/callback, connect it to the authoritative session unlock mechanism, dismiss the lockscreen properly, and physically verify the phone becomes interactive.

**GO FREE THE PENGUIN! 🐧🔓🔥**
