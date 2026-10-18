# NUXEL — OPERATION TOUCHABLE 🐧🔥

You are Cyber-Tiel 35B, continuing the existing Nuxel project on the Samsung Galaxy S10+.

**Your ONLY mission is to make Nuxel fully controllable through the physical touchscreen.**

## Requirements

1. **Clickable apps:** Tapping app icons must actually open them. Apps must respond to touch and support closing/returning Home.
2. **Second desktop:** Add a second home-screen page. Swipe left/right to switch desktops, with smooth animations and clickable icons on both pages.
3. **Swipe down:** Open the existing notification/Quick Settings panel from anywhere on the screen.
4. **Swipe up:** Open the applications drawer from anywhere on the screen.
5. **Responsiveness:** Every action must update the display immediately, without pressing Power to force a redraw.

Preserve normal scrolling and avoid gesture conflicts.

## Mandatory 90-second testing loop

**You must actively test with me, not just tell me to verify later.**

1. Prepare live touchscreen, Wayland, WebKitGTK and application-event diagnostics.
2. Announce **"90-SECOND TOUCH TEST STARTING NOW"** and tell me exactly what to tap/swipe.
3. Record my physical touchscreen interactions for 90 seconds.
4. Automatically stop recording and analyze which events reached each layer.
5. Find the first failing stage.
6. Fix the actual root cause.
7. Run automated tests and **deploy the fixes to the real phone** through the USB live console.
8. Start another 90-second test.
9. Repeat until I confirm everything works.

Use actual finger events, not simulated clicks or hardware-button events, as proof. Collect my PASS/FAIL feedback after each round.

## Execution rules

- Continue from existing code, A34/Codex changes and current checkpoints.
- Do not rewrite the launcher or touchscreen driver without proven necessity.
- Do not flash, repartition, change the kernel or enter recovery/download mode.
- Preserve the USB console and create rollback backups.
- Do not stop after planning, compiling, dry runs or unverified deployments.
- Keep a persistent TODO and test log.
- If three identical attempts fail, change diagnostic strategy.
- Only declare success after **real physical owner verification**.

**Model:** Cyber-Tiel 35B  
**Context:** 131,072 tokens  
**Maximum output:** 65,536 tokens  
**Temperature:** 0.0  
**Concurrency:** 1

**FINAL GOAL:**

**TAP → APP OPENS.**

**SWIPE LEFT/RIGHT → SWITCH DESKTOPS.**

**SWIPE DOWN → QUICK SETTINGS.**

**SWIPE UP → APP DRAWER.**

**90-SECOND TEST → FIX → DEPLOY → RETEST UNTIL VERIFIED.**

**EXECUTE NOW.**
