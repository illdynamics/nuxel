# NUXEL — HAPTIC FEEDBACK & 3-BUTTON NAVIGATION 🐧
## Samsung Galaxy S10+ · Fedora 43 ARM64 · Existing Nuxel Home
### Implement → Test → Live Deploy → Physically Verify

You are the autonomous Nuxel engineer working on the current repository at `~/x/nuxel` on the MacBook.

Your mission is to implement two features:

1. **Real hardware haptic feedback**, configurable in Nuxel Settings.
2. **A persistent three-button navigation bar:** Back, Home, Recent Apps.

Use the existing WebKitGTK/Phoc/Nuxel architecture. Read current source and latest engineering changes first.

Do not replace the launcher, build a competing compositor, or regress touchscreen functionality.

## 1. REAL SAMSUNG VIBRATION HARDWARE

First inspect the current kernel and userspace for the S10+'s haptic driver.

Investigate:

- `/sys/class/timed_output/`
- `/sys/class/leds/`
- `/sys/class/input/`
- `/dev/input/event*`
- Force-feedback capabilities (`EV_FF`).
- Existing Samsung haptic/vibrator kernel drivers.
- Kernel configuration and device-tree bindings.
- Existing Nuxel haptic utilities, if any.

Discover the actual supported interface. Do not assume a generic Android vibrator interface exists.

Create a native Nuxel haptics service or extend the existing hardware-control service, whichever fits the current architecture.

Support:

- Enable/disable vibration.
- Vibration duration.
- Vibration intensity, **only if the real driver supports adjustable amplitude**.
- Separate feedback profiles for tapping, scrolling and long presses.
- Safe limits and rate limiting.
- Hardware timeout protection.
- Device suspend/resume handling.
- Clean shutdown.
- No indefinitely running motor.

Do not emulate unsupported intensity by claiming hardware amplitude control exists.

If intensity is unsupported, keep the setting disabled and document the limitation.

Do not attempt undocumented register writes or patch kernel drivers live.

## 2. DEFAULT HAPTIC SETTINGS

Choose these initial profiles:

| Interaction | Duration | Requested intensity |
|---|---|---|
| Normal screen tap | 12 ms | 30% |
| Scrolling snap/detent | 6 ms | 15% |
| Long press | 25 ms | 45% |
| App switcher selection | 14 ms | 35% |
| Error/rejected action | Two short 20 ms pulses | 40% |

Use effective strength values supported by the actual driver.

**Do not vibrate continuously while scrolling.** Trigger only on meaningful scroll snap points, selection changes or discrete actions. Enforce an appropriate cooldown and coalesce repeated events.

Do not generate a vibration from every raw touch-motion event.

Avoid redundant vibrations when a tap also triggers a navigation action.

## 3. NUXEL SETTINGS → SOUND & HAPTICS

Extend the existing Settings application.

Add:

**Haptic Feedback**

- Master vibration toggle.
- Touch feedback toggle.
- Scroll feedback toggle.
- Navigation feedback toggle.
- Long-press feedback toggle.
- Intensity slider: 0–100%, if supported.
- Tap duration slider: 5–40 ms.
- Scroll duration slider: 3–20 ms.
- Long-press duration slider: 10–80 ms.
- Test Vibration button.
- Reset to Defaults button.

Persist settings across restart.

Apply changed settings immediately.

Disable unavailable hardware controls gracefully.

The Test Vibration button must use the actual motor, not synthetic UI feedback.

## 4. IMPLEMENT CLASSIC THREE-BUTTON NAVIGATION

Add a persistent navigation bar at the bottom of Nuxel.

Layout:

`◀           ●           ▢`

Three controls:

**LEFT — BACK**

- Tap: navigate backward inside the current application.
- If the application has no previous navigation state, close it and return Home.
- If already at Home, remain Home.
- Hold for approximately 800 ms: terminate the current foreground application.

IMPORTANT: Holding Back must NEVER terminate:

- Nuxel Home launcher.
- Phoc.
- WebKitGTK host if shared by multiple apps.
- The framebuffer bridge.
- systemd.
- The USB live console.
- Input services.
- Critical operating-system services.

Implement app termination through the existing application/process manager, targeting only the current app session or isolated app process.

For PWA apps sharing the same host process, close their app session/iframe rather than killing the shared WebKit host.

For apps with unsaved data, provide an appropriate warning or confirmation rather than silently destroying work.

Give stronger haptic feedback on long-press activation.

**MIDDLE — HOME**

- Tap: close/minimize the foreground application view and return to Nuxel Home.
- Preserve background applications unless their lifecycle requires closing.
- Never restart Phoc merely to return Home.
- Hold for approximately 800 ms: open Nuxel Home Settings.

Home Settings should use the existing Settings application and include available options for wallpaper, desktop behavior, gestures and navigation.

Do not create a redundant Settings application.

**RIGHT — RECENT APPS / APP SWITCHER**

- Tap: open the Recent Apps switcher.
- Display currently open application sessions/windows as selectable cards or a compact list.
- Show app icon, name and a preview only if previews are already available.
- Permit horizontal or vertical scrolling.
- Tap an application to bring it to the foreground.
- Tapping the Recent Apps button again closes the switcher and activates the currently highlighted application.
- Provide an explicit Close control for individual applications.
- Home exits the switcher and returns to the launcher.

This is similar to desktop task switching, but adapted to a touchscreen.

Do not show every installed application as though it is currently running.

The switcher must distinguish actual active/background applications from app shortcuts.

## 5. RECENT APPS STATE MANAGEMENT

Implement a single authoritative foreground-app and recent-app registry.

Track:

- App ID.
- App name.
- Application type (PWA/native).
- Session/window ID.
- Foreground/background state.
- Last focused timestamp.
- Running/closed/failed state.
- Safe close handler.
- Safe foreground activation handler.

Ensure:

- Opening an app registers it.
- Returning Home updates foreground state.
- Switching apps restores correct focus.
- Closing apps removes stale records.
- Crashed apps disappear or show a clear failure state.
- No invisible fullscreen window remains above Home.
- Reopening an app works.

Never call `kill -9` on the shared launcher or compositor to implement Back-long-press.

Use graceful app termination where possible, escalating only for an isolated unresponsive application.

## 6. NAVIGATION BAR AND TOUCH COMPATIBILITY

The bar must:

- Remain accessible in normal application mode.
- Respect the Galaxy S10+ display safe areas.
- Avoid accidental touches near the camera cutout.
- Scale correctly with display resolution.
- Respond immediately.
- Provide subtle visual and haptic feedback.
- Never block application content unnecessarily.

Reserve appropriate bottom screen space or implement safe-area padding.

Make controls large enough for finger input.

Use the existing Nuxel visual style.

Do not create overlapping invisible touch regions.

Preserve existing swipe gestures:

- Swipe left/right: desktop navigation.
- Swipe down: Quick Settings.
- Swipe up: applications drawer.

The navigation buttons take precedence for touches within their own hitboxes.

Ordinary scrolling must continue working.

## 7. PHYSICAL TESTING — 90 SECONDS

Use the existing live-console instrumentation.

When ready, announce:

**NUXEL HAPTICS & NAVIGATION TEST — 90 SECONDS**

Tell the owner to:

1. Tap five app icons and feel for short vibration feedback.
2. Scroll a list and check for subtle feedback at snap points.
3. Hold Back to close a foreground app.
4. Tap Home to return to the launcher.
5. Hold Home to open Home Settings.
6. Open two applications.
7. Tap Recent Apps.
8. Switch between both applications.
9. Tap Recent Apps again to activate the highlighted app.
10. Open Settings and change haptic strength/duration.
11. Tap Test Vibration and confirm the physical result.

Capture the event logs during the full 90-second window.

Then automatically analyze results and continue.

Ask the owner for explicit PASS/FAIL feedback on:

- Physical vibration.
- Vibration strength.
- Navigation bar clickability.
- Back long-press.
- Home.
- App switching.
- Settings persistence.

Do not count successful API calls as proof that the motor physically vibrated.

## 8. SAFE DEPLOYMENT

Before modifying the running phone:

1. Verify live USB-console access.
2. Back up existing binaries/assets/configurations.
3. Record SHA-256 hashes.
4. Implement minimal source changes.
5. Run existing regression tests.
6. Build target-compatible ARM64 userspace binaries where necessary.
7. Deploy through the current live-console deployment tools.
8. Verify destination hashes.
9. Restart only affected userspace services.
10. Verify launcher and touchscreen still work.
11. Run the 90-second physical test.
12. Roll back any broken component.

No flashing.

No partition writes.

No new kernel deployment.

No recovery/download-mode reboot.

Do not interrupt the USB console.

## 9. COMPLETION REQUIREMENTS

The mission succeeds when:

- The physical S10+ motor vibrates on permitted UI actions.
- The user can configure feedback duration.
- Intensity can be adjusted when supported by hardware.
- Scrolling does not cause excessive vibration.
- Back tap navigates correctly.
- Holding Back terminates only the intended foreground application.
- Home returns to the launcher.
- Holding Home opens Home Settings.
- Recent Apps shows real active applications.
- The switcher can foreground selected apps.
- Tapping Recent Apps again confirms the highlighted app.
- All three navigation controls respond to physical touch.
- Existing gestures continue working.
- The GUI updates without Power-button intervention.
- Changes persist after normal application/service restart.
- The owner physically verifies the behavior.

If any capability is unsupported by the current kernel, document the exact blocker and continue implementing everything that works in userspace.

Do not fabricate motor feedback or physical test results.

**ONE MISSION: MAKE NUXEL FEEL AND NAVIGATE LIKE A REAL PHONE.**

**HAPTICS + BACK + HOME + RECENTS.**

**BUILD → DEPLOY → 90-SECOND TEST → FIX → RETEST.**

**EXECUTE NOW. 🐧🔥**


## ADDENDUM — ACTUAL ICONS AND TWO OWNER-PROVIDED MP3 CUES

Use the supplied real assets, never emoji/placeholder art where a matching PNG exists:
- `assets/button-left.png`, `button-middle.png`, `button-right.png` for Back/Home/Recents.
- `assets/nuxel-applications-icon-pack/` for launcher/dock/search/Recents.
- `assets/nuxel-quicksettings-icon-pack/` for Quick Settings.
- `assets/nuxel-boot-audio.mp3`: 7.7-second cue, play ONCE when the *real* `/run/nuxel-anim-handoff` receipt confirms `owner=ui` and `stage=LAUNCHER_DISPLAY_OWNER`, **not** merely when the PWA loads or before the animation ends. Request 44% software PCM gain; preserve the device's existing 25% protective hardware-mixer ceiling until speaker routing is verified.
- `assets/nuxel-pow.mp3`: short cue triggered nonblockingly after a successful physical volume-up/down mixer adjustment, at the *newly selected* real mixer level. Suppress overlapping cues and respect silent/vibrate mode.

Deploy icon packs to the actual `nuxel-web` document root (`/usr/share/nuxel/assets/` on the Fedora image) and verify HTTP 200 for icon paths. Include all source assets and the audio helper/service in image builds, plus a safe live-deployment plan. Do not report audible sound unless the owner hears it. Do not bypass the existing protective ALSA cap or start a second haptics actuator owner.
