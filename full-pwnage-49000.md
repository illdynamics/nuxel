# FULL-PWNAGE-49000
# NUXEL — GLOBAL SYSTEM CHROME, NAVIGATION SEMANTICS, NATIVE/FLATPAK APP LIFECYCLE, USB MTP, SOFTWARE CENTER, NUXTORE STATE, AUTHENTICATOR QR ENROLLMENT, NFC, BIOMETRICS & REAL SCREEN SECURITY

## Complete source-level repair, integration, security review, regression testing and physical S10+ verification mission

**Mission ID:** PWNAGE-49000  
**Target device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel — custom Fedora-based ARM64 mobile Linux  
**Primary UI:** `pwa/nuxel-home` + Nuxel app PWAs + Settings + native Wayland layer-shell dock  
**Native host:** A45 Nuxel PWA host and active session services (verify current build path)  
**Bridge:** `services/nuxel-bridge`  
**Display:** Phoc/Wayland + Pixman/software-rendered presentation + `nuxel-wl-fb` single `/dev/fb0` owner  
**USB:** existing USB gadget owner + CDC-ACM recovery console + `nuxel-usb-mode.sh`/`usb_mode.py`  
**App identity:** `pwa/nuxel-common/app-registry.json` + on-device canonical registry  
**Mission type:** real implementation, service/build integration, security-preserving repair, active-image verification and physical user acceptance.

---

# 0. MISSION OBJECTIVE

Repair the Nuxel user experience and integration layer so that the device behaves like a coherent mobile operating system when locked, on Home, inside a PWA, inside a native GTK application and inside a Flatpak application. The three-button navigation and status bar must belong to the operating system shell—not only to the Home web page.

The project already has substantial components: a native bottom Wayland dock, a WebKit Home controller, native app launch via a registry and Bridge, a real compositor toplevel manager, a haptics daemon, a connection-mode state machine, a local Nuxtore catalog, an encrypted TOTP vault, NFC diagnostics and a custom lockscreen. Several user-visible failures are caused by disconnected contracts or stale/inconsistent state rather than a complete lack of code.

Do not rebuild working parts unnecessarily. Reconcile the owners and repair the active path.

## 0.1 Complete requested outcomes

1. Replace the Wi-Fi and Bluetooth top-bar symbols with clearer, recognizable, consistent vector icons; add/repair a Location icon and state from the existing Location provider.
2. Make the top bar visible on the lockscreen, including time and appropriate radio/battery status. The full-screen lockscreen must not cover it.
3. Make the system top bar and three-button Back / Penguin Home / Tabs dock persist above native GTK and Flatpak windows. Avoid duplicate DOM and native bars.
4. Restore Back/long-Back haptics. A long hold must provide a distinct long-press pulse once, not the regular navigation tick.
5. Short Back must perform in-app backward navigation. Home must remain a separate minimize/background action. Holding Back must request foreground-app close/termination safely.
6. Support those navigation semantics for PWA, native GTK and Flatpak apps. Each app must have a real Back contract or honestly report that it has no internal history; do not silently treat all non-browser native apps as already at Home.
7. Fix the false “unlock the phone first to use apps”/locked-gate failure for successfully unlocked users. Trace the exact message and state authority; do not remove real lock checks. Compare the failing native-app path with the Archive Manager path that currently works.
8. Complete a real MTP USB File Transfer mode with accessible internal storage and the mounted removable SD card. Preserve the serial recovery interface and avoid dangerous raw mass-storage export.
9. Make lockscreen and app drawer faster on the actual WebKitGTK + Pixman/fbdev path.
10. Fix drawer gesture arbitration: the swipe that opens the drawer must not also scroll it; scrolling an open drawer or desktop must never launch an application; only a tap launches.
11. Integrate native RPM/GTK and Flatpak management in one Software application. Be truthful about the currently documented lack of package-management and Flatpak sandbox prerequisites.
12. Make Nuxtore accurately reconcile built-in/system-installed apps and package-installed apps, particularly Live Console.
13. Finish the Authenticator experience so an unlocked vault accepts a TOTP account by QR camera scan, QR image, pasted URI or manual code, encrypts it and displays real timed codes.
14. Add Microsoft Entra-compatible standard OATH/TOTP support and guidance where the tenant allows software OATH tokens. Do not claim to clone Microsoft Authenticator push, number matching or broker features.
15. Verify NFC controller/driver/firmware/stack and real tag reading. Fix supported layers and present truthful status.
16. Verify the S10+ ultrasonic fingerprint path and add secure enrollment/verification only if an actual driver and trusted secure provider exist.
17. Audit current screen lock: Swipe, PIN, Pattern and Fingerprint with mandatory PIN fallback should be implemented as real session locks, not cosmetic page overlays. Evaluate optional face recognition but do not ship it as secure unlock without real liveness/anti-spoof protection.

This is an implementation mission. A report-only answer or green mock UI is not completion.

---

# 1. ESTABLISH THE CURRENT SOURCE AND LIVE BUILD

## 1.1 Inspect the complete project and identify active source generations

Start with the current checkout and inspect at least:

```text
pwa/nuxel-home/
  index.html
  js/app.js
  js/apps.js
  js/status-bar.js
  js/launcher.js
  js/lockscreen.js
  js/lockscreen-indicators.js
  js/qs.js
  css/status-bar.css
  css/launcher.css
  css/lockscreen.css

pwa/nuxel-common/
  app-registry.json
  bridge.js
  haptics.js
  theme.css

pwa/nuxel-apps/settings/
pwa/nuxel-apps/nuxtore/
pwa/nuxel-apps/authenticator/
pwa/nuxel-apps/console/
pwa/flatpak/

services/nuxel-bridge/src/
services/nuxel-haptics/
services/nuxel-notifications/
services/nuxel-session/systemd/
services/nuxel-s10/bin/

configs/nuxel/app-registry/
configs/nuxel/usb/
configs/nuxel/nfc/
configs/nuxel/security/
configs/nuxel/haptics/

shell/nuxel-home-native/
tools/s10plus/a33/
tools/s10plus/a34/
tools/s10plus/a45/
images/s10plus/build-phone-rootfs-inside-fedora.sh
```

Also read:

- `NUXEL-26000-TRI-LINK-CONSOLE-REVOLUTION-UBERPROMPT.md`
- `NUXEL-28000-TRI-LINK-UBERFIXER-UBERPROMPT.md`
- `docs/beta-finalization/live/NUXEL-28000-TRI-LINK-UI-REPORT.md`
- `docs/a53/NATIVE-APPLICATION-LAUNCHER.md`
- `docs/a53/GNOME-SOFTWARE-RPM-FLATPAK.md`
- `docs/a59/APP-REGISTRY-DISCOVERY.md`
- `docs/beta-finalization/manual-proof/12-nfc.md`
- the current Authenticator tests and workqueue records.

The archive inspected for this specification was `nuxel-main (10)(1).zip`. The current Git checkout and active phone may have newer fixes. Re-run the audit against the latest files and running binaries; never blindly reapply a historical bug fix to a newer generation.

## 1.2 Active S10+ build path is authoritative

Use `images/s10plus/build-phone-rootfs-inside-fedora.sh` and its current include/package manifests to identify exactly which C files, Python modules, PWA assets, registry and systemd units are installed. Directory numbers such as A33/A34/A45 are revision labels, not automatic proof that a particular source is deployed.

For each component, record:

- source path compiled/copied by the active builder;
- installed runtime path;
- current on-device SHA-256 or build ID;
- service/unit owning it;
- runtime socket/FIFO/API contract;
- test path covering that exact source.

Do not patch only an old A34 source if A45 is active; do not patch A45 if the image builder still installs another revision. Do not create duplicate `nuxel-pwa-host`, dock, haptics or status owners.

## 1.3 Live baseline and evidence

When the existing authenticated SSH path is available, collect read-only evidence first:

- build/version/commit and working tree;
- live Home JS/CSS/service-worker revision;
- active PWA host, Bridge, Phoc, Wayland and `nuxel-wl-fb` PIDs/units;
- actual native dock process and `/run/nuxel-navdock.state`;
- active lock state from UI and host state file/service;
- active/foreground Wayland toplevels and app IDs;
- app registry version and actual application desktop entries/binaries/Flatpak refs;
- haptics service/provider state and current device capability;
- USB UDC/configfs, CDC-ACM and MTP/FunctionFS status;
- mounted internal/SD-card storage paths and permissions;
- package manager, RPM, PackageKit, Flatpak, Bubblewrap, user namespace, portal and polkit status;
- Nuxtore local state and catalog identities;
- Authenticator vault presence/schema/version (never dump the decrypted accounts or secret data);
- NFC diagnostic JSON and first failing stage;
- fingerprint driver/device/TEE evidence;
- current lock method and lock service capability, without collecting credentials.

Write evidence into:

`docs/beta-finalization/live/evidence/pwnage-49000/`

Do not log OTPs, QR secrets, vault passphrases, user PINs, biometric metadata beyond non-secret capability status, private keys or user file contents.

---

# 2. TOP STATUS BAR ICONS — WI-FI, BLUETOOTH AND LOCATION

## 2.1 Current status markup/state

The checked-in `pwa/nuxel-home/index.html` contains:

- `#status-time`
- `#status-signal`
- `#status-wifi`
- `#status-bluetooth`
- `#status-battery`
- `#status-battery-pct`

There is no `#status-location` element in the inspected archive. `StatusBar` in `js/status-bar.js` tracks Wi-Fi and Bluetooth but does not own a Location icon/provider field. The Location tile exists in Quick Settings and has its own Bridge control/state.

Implement Location in the shared system status contract rather than inventing a second Location service.

## 2.2 New icon visual requirements

Replace the current hand-built CSS glyphs with recognizable, balanced vector icons or existing local Nuxel SVG assets. Prefer small inline SVG using `stroke="currentColor"`, consistent 1.8–2 px strokes and 24×24 viewBoxes, scaled to the existing status-cell footprint.

Suggested visual language:

- **Wi-Fi:** three curved signal arcs above a small centre dot. The current glyph uses a partial circular ring that can read like a radar/eye; replace it with a familiar Wi-Fi wedge/arc silhouette.
- **Bluetooth:** the recognizable Bluetooth rune (vertical stem with opposing upper/lower chevrons), not the current angular CSS pseudo-cross.
- **Location:** a map pin/locator glyph (drop-shaped pin with centre circle). When location is enabled, show the appropriate active tint. A separate GPS-fix state must be visually distinguishable only when the provider explicitly reports a real fix.

Do not use emoji; emoji shape differs across fonts/runtime. Do not put both a CSS pseudoelement glyph and an SVG inside one cell. Use one renderer per icon. Preserve the right cluster's measured widths/safe zones and do not let icons overlap the Samsung camera/cutout region.

## 2.3 Truthful states

The three icons should distinguish at least:

| Radio/provider | UI state | Required visual behavior |
|---|---|---|
| Wi-Fi disabled | `disabled` | muted Wi-Fi icon with accessible “Wi-Fi off” label |
| Wi-Fi enabled, disconnected | `enabled_disconnected` | hollow/muted Wi-Fi icon, not green |
| Wi-Fi connecting | `connecting` | restrained amber/connecting state; no expensive animation |
| Wi-Fi connected | `connected` / `internet` | active Wi-Fi color; internet verified only where provider says so |
| Wi-Fi unavailable/unknown | `unknown` | neutral/unknown state; do not invent OFF |
| Bluetooth powered OFF | `off` | show muted/disabled icon or hide only if the product status-bar policy explicitly does so; user should be able to understand radio is off |
| Bluetooth ON | `on` | active icon and accessible label |
| Bluetooth discovering | `discovering` | optional small badge/state; no large continuous animation |
| Bluetooth provider unavailable | `unknown` | neutral state or hidden with diagnostics; do not pretend OFF |
| Location service off | `off` | muted Location pin |
| Location service on | `enabled` | active pin |
| Location fix acquired | `fix` | a separate subtle fix marker only when actual provider fix/accuracy evidence exists |
| Location unknown/error | `unknown` | neutral state, never green ON |

Location service enabled is not necessarily GPS satellite lock. GeoClue may use Wi-Fi/IP or another provider. Do not label it GPS FIX unless the backend explicitly reports a real satellite fix.

## 2.4 One data owner and bounded refresh

Reuse the current Bridge Location provider already called by Quick Settings. Extend `StatusBar` to read the same canonical state, or add a shared status event/API consumed by both QS and the top bar. Do not add another aggressive polling loop that duplicates QS/lockscreen work.

Requirements:

- hydrate quickly after session startup;
- keep the last known state only for a bounded staleness interval;
- show `unknown` after provider data expires or an error occurs;
- update icons only when state changes;
- refresh on wake and Bridge status events;
- pause non-essential polling while display is off or Home is backgrounded if appropriate;
- apply `NuxelSafeZones` layout after dynamic icon visibility changes;
- update `_assertNoOverlap()` and status-zone tests for the new element.

## 2.5 Top bar accessibility and touch

Keep 16–18 CSS pixel icon art with a 36–40px physical touch target if a toggle is provided. The status glyph itself must not accidentally turn a radio on/off unless the design explicitly makes it a button. Use accessible titles/labels and focus behavior for keyboard/remote pointer use.

---

# 3. TOP BAR ON THE LOCKSCREEN — FIX THE LAYER ORDER CORRECTLY

## 3.1 Confirmed CSS stacking cause

In the inspected source:

- `.status-bar` is `position:fixed; top:0; z-index:100` in `pwa/nuxel-home/css/status-bar.css`.
- `#lockscreen` is `position:fixed; inset:0; z-index:500` in `pwa/nuxel-home/css/lockscreen.css`.

The lockscreen is a full-viewport opaque overlay above the status bar. The status bar is not absent; it is hidden beneath the higher z-index lockscreen. Fix this explicitly.

## 3.2 Required presentation

When locked, top status must still show:

- time (clock can coexist with the larger lockscreen clock; choose a compact style so it doesn't become duplicate/confusing);
- battery icon/percentage according to existing preference;
- cellular/signal only if real modem registration is known;
- Wi-Fi and Bluetooth states;
- Location state;
- any existing small system indicator that the user expects on the lockscreen.

Prefer a reusable system-chrome presentation owner. Options:

1. Put a status strip as a child of the lockscreen layer, with the same source/state renderer; or
2. Raise the existing DOM status bar above the lockscreen using a deliberately documented stacking order and ensure it does not block the lockhead/unlock gesture outside its own height.

The choice must not create duplicate bars. When the lockscreen is active, the status strip must be above the wallpaper but below system critical OSD/authorization surfaces where required.

## 3.3 Locked interaction policy

A visible top bar is not permission to open protected applications while locked.

- A pull-down may open a restricted lockscreen-safe QS panel only if the existing security policy permits it.
- Radio status can be viewed; high-impact setting changes must follow the existing lock-safe action policy.
- App launch, Recents, Home navigation into protected content and credential Settings remain blocked until a valid unlock.
- The status bar must not steal the lower-band swipe-to-unlock gesture.
- Top bar taps should not start unlock gestures; preserve the lockscreen's pointer exclusions and event capture.
- On screen-off, the bar/overlay must stop expensive refresh work and resume on real wake.

## 3.4 Lock-screen acceptance

Physically lock the S10+ and confirm top row is visible, no clipping, correct safe-area/camera offset, all state icons are truthful, lockhead remains draggable, swipe-to-unlock works, and touching the top bar does not accidentally unlock or reveal Home.

---

# 4. THREE-BUTTON NATIVE SYSTEM NAVIGATION — BACK / PENGUIN HOME / TABS

## 4.1 Active owner

The native dock is `tools/s10plus/a45/nuxel-navdock.c` in the inspected archive. It is a Wayland `zwlr_layer_shell_v1` surface on the OVERLAY layer, bottom anchored, with exclusive zone. It uses:

- `/run/nuxel-pwa-host.cmd` for logical actions;
- `/run/nuxel-haptics/haptics.cmd` for haptic commands;
- `/run/nuxel-navdock.cmd` for show/hide control.

The DOM dock may still exist as a fallback, but the physical S10+ should use one visible input owner at a time. Do not patch only CSS and assume the native dock changes.

## 4.2 Correct semantics

| Gesture | Required behavior |
|---|---|
| Short tap Back | Navigate back within the active app if there is a valid in-app Back operation. If at root/no Back action, do not unexpectedly close the app; give subtle feedback/no-op. |
| Short tap Penguin Home | Minimize/background active PWA/native/Flatpak app and bring Home to foreground. Do not kill app. |
| Short tap Tabs | Open/toggle Recents and allow activation of a backgrounded PWA/native/Flatpak window. |
| Hold Back | After the long-press threshold, emit a distinct long haptic exactly once and request close/terminate of only the foreground app. Suppress the short Back release action. |
| Hold Home | Preserve existing behavior unless the owner remaps it; must not cause Back/close. |
| Hold Tabs | Preserve current behavior or show a non-destructive Recents action; never terminate an app. |

Keep the long-press threshold deliberate and configurable (existing dock uses 700ms). Add movement slop so a drag/scroll across the dock does not count as a hold. Provide progress/pressed feedback only while stationary; cancel on pointer cancel/lost contact.

## 4.3 Restore long-Back haptics

The `forward()` function in `nuxel-navdock.c` currently sends the `navigation` haptic for every action. The haptics service `services/nuxel-haptics/nuxel-hapticsd.py` supports commands including `navigation` and `long`; the default haptics config also has a `long` pattern.

Implement action-specific haptic behavior:

- regular Back/Home/Tabs tap → the existing short `navigation` pattern;
- Back hold threshold reached → one `long` command, not `navigation` + `long` duplicated;
- no haptic on a cancelled hold;
- no second haptic when pointerup emits the logical `back-long` action;
- respect global haptics switch, rate limit, actuator availability and lock policy.

If physical vibrator is unavailable, retain a visual pressed/long-held affordance and report the hardware limitation. Do not claim haptics physically work from FIFO acceptance alone.

## 4.4 Fix the long-Back close pipeline

The current path is intended to be:

`dock hold >= 700ms -> action back-long -> pwa-host dispatches nuxel:action -> NuxelHome.terminateForeground() -> POST /api/v1/apps/close-foreground -> Bridge _close_foreground_action() -> nuxel-foreign-toplevel close-foreground`.

Audit every hop using a unique action ID and logs that contain no user content. Verify the active A45 PWA host really maps `back-long` correctly. Remove stale comments only after the deployed source is proven.

The current Bridge's close operation is a Wayland foreign-toplevel close request, not a process kill. That is preferable. To satisfy “hold Back kills/closes the app” reliably:

1. Identify the exact foreground toplevel and its owning app ID.
2. Map it to a validated app registry record and, where native/Flatpak, an app-owned systemd unit/cgroup recorded at launch.
3. Send graceful Wayland toplevel close request.
4. Wait a bounded period for the toplevel/process to exit.
5. If the app ignores close and the app manager has a verified app-owned unit/cgroup, request stop for that one unit/cgroup (SIGTERM first).
6. Only after a second bounded grace period, use SIGKILL on the exact remaining process group inside that app-owned cgroup if policy allows. Never kill by broad process name/PID guesses.
7. Confirm the app toplevel is gone, clear its recents/session record, leave Home and system services alive.
8. If there is no app foreground, long Back does nothing except a harmless indication; it must never terminate Home or the host.

Never kill `nuxel-pwa-host`, `nuxel-wayland`, Phoc, `nuxel-wl-fb`, Bridge, systemd, haptics, SSH or other services.

## 4.5 Pointer/touch input correctness

The dock's Wayland touch listener measures `down_ms`, `down_x/y`, `last_x/y`, and classifies a tap if movement is within ±24px. Verify:

- touch IDs are tracked; one finger owns the gesture;
- multiple contacts do not merge into one Back hold;
- hold time uses `CLOCK_MONOTONIC` (already does in the inspected source);
- movement beyond slop cancels long hold;
- pointer/touch cancellation clears timers/state;
- dock hide while a touch is active cancels safely;
- the release triggers exactly one action;
- tap action and `back-long` do not both execute;
- dock still responds with native apps/Flatpak foregrounded.

## 4.6 Tests

Add C-side/unit or event-state tests plus host/Bridge JS/Python tests for:

- Back short → in-app Back;
- Back short at app root → safe no-op, app stays visible;
- Home → app minimized and Home shown;
- Tabs → Recents lists app and reactivates exact toplevel;
- Back long → one long haptic + app close;
- Back long → no short Back after release;
- long hold cancelled by movement/pointercancel → no close/no long haptic;
- no app foreground → no-op;
- native app refusing close → bounded app-owned unit escalation only;
- host/dock/Bridge process remains alive after foreground close.

---

# 5. BACK INSIDE APPS — ONE COMMON PWA / NATIVE / FLATPAK NAVIGATION CONTRACT

## 5.1 Current weakness

`NuxelHome.back()` in `pwa/nuxel-home/js/app.js` currently handles:

- Home search overlay;
- Quick Settings;
- Recents;
- folder sheet;
- app drawer;
- software/native on-screen keyboard and focused editable field;
- same-origin PWA iframe `history.back()` relative to a stored baseline;
- then Bridge `/api/v1/apps/back` for native apps.

The current `api.py:_native_back_action()` enumerates the activated non-Home toplevel, but it only handles an app ID containing `browser` by reading `/run/nuxel-browser.state` and sending `back` to `/run/nuxel-browser.cmd`. For another native app it returns `handled:false`, so `NuxelHome.back()` falls through to `home()`. That is not a universal native-app Back implementation.

## 5.2 Define a shared app-navigation contract

Implement a typed, safe navigation contract with optional capabilities per app. Prefer an explicit app control protocol (for example a user-session D-Bus interface or a restricted per-app Unix socket) and registry-declared actions.

Each app record may declare a validated navigation descriptor such as:

- `back_supported`;
- `back_provider` (`pwa-history`, `browser-control`, `dbus-action`, `app-control-socket`, `desktop-action`, etc.);
- a fixed action/object/interface/method identifier from a closed allowlist;
- foreground app ID and session/unit identity.

Do not accept a client-supplied command, arbitrary URI, binary path or shell string.

Recommended contract:

```json
{
  "app_id": "org.example.App",
  "foreground": true,
  "can_go_back": true,
  "handled": true,
  "at_root": false,
  "provider": "org.nuxel.AppNavigation"
}
```

This is an illustrative contract; adapt to current Bridge conventions.

A native/Flatpak app that supports internal navigation must expose `CanGoBack`/`Back` (or equivalent `GAction`/D-Bus adapter) and return whether it handled Back. The shell sends Back and leaves the app visible when handled. If the app has no prior page, do not silently invoke Home; keep Home semantics separate. Provide a non-intrusive no-history indication if needed.

For browser, preserve its existing control FIFO, but reconcile state from the same browser process that owns the visible toplevel. Avoid stale `/run/nuxel-browser.state` values.

For GTK apps, prefer an app-implemented `GAction` (e.g. `win.go-back`) or an app control object. Do not globally inject `Alt+Left` or Escape into every app; that can trigger unrelated destructive/close actions. An explicit per-app adapter may map keys only when the application contract documents them.

For Flatpak, the host must route the control through the app instance / D-Bus permissions without breaking the sandbox. Do not reach into the Flatpak mount namespace or execute arbitrary app commands.

## 5.3 PWA navigation and iframe behavior

Keep current baseline history semantics:

- when a PWA is first opened, store its navigation baseline;
- Back navigates only when history length is above that baseline;
- at the app root, Back is a safe no-op (Home button remains separate);
- if a PWA declares an app-specific `data-action="back"` control, use it only when history is at baseline and ensure it is not clicked twice;
- cross-origin frames must not be poked with DOM access; use typed Bridge or `postMessage` contract with origin validation.

Do not break app PWA back navigation, Close/return-to-home buttons, forms or the native keyboard.

## 5.4 Recents/Tabs across surfaces

The Recents model must track actual active and backgrounded surfaces:

- PWA iframe surface/session;
- native GTK Wayland toplevel;
- Flatpak Wayland toplevel, including app ID/instance metadata.

On reactivation, use the actual compositor toplevel activation path, not a fake local card selection. Avoid duplicate entries for multiple surfaces belonging to the same app unless the app intentionally has multiple windows.

Test multiple native windows, multiple Flatpak app windows, switching between PWA and native and closing a backgrounded app.

---

# 6. FIX “UNLOCK THE PHONE FIRST” FALSE NATIVE-APP REFUSAL

## 6.1 Do not guess the source

The exact phrase reported by the owner does not appear in the inspected source archive. Authenticator has its own “unlock the vault first” error, but that is an app-vault error and not a screen-lock error. The current Home controller uses `NuxelHome._isLocked()`, which calls `this.lockscreen.isLocked()`, and both `_openPwa()` and `_launchNative()` refuse to launch while that local state is locked.

Therefore, capture the exact on-screen text and trace its source in the live/deployed code. Possibilities include:

- stale cached `app.js` or JS/service-worker bundle;
- Home's local LockScreen state not synchronized after an accepted unlock;
- native host `/run/nuxel-lock.state` and WebKit LockScreen instance disagree;
- a new native-app lock guard in an API/provider not present in this archive;
- individual app/vault security message being interpreted as phone lock;
- registry launch descriptor or native helper refusing for a different reason.

Do not remove the launch gate and do not simply force `locked=false` in JavaScript.

## 6.2 Establish one authoritative lock state

Review the boot lock, user lock, display-off lock, lockscreen gesture and native host lock path. Define one source of truth (host/session lock manager, with a client cache/event) and make all app-launch surfaces consume it consistently.

The status contract should expose:

- `locked` boolean;
- `state` (`locked`, `unlocking`, `unlocked`, `unknown`, `error`);
- generation/revision ID so stale UI state is detected;
- last transition reason/time;
- whether a valid credential/gesture verification was acknowledged by the host.

The Home PWA may cache this state for responsiveness, but before launching a protected native or Flatpak app it must not rely on a stale local boolean. Use the Bridge/session lock state or a synchronized host event. A stale/unknown state should fail closed with a clear retry/refresh message—not falsely claim the user must unlock if the session already accepted unlock.

## 6.3 Unlock-to-Home and launch consistency

Preserve the already documented NUXEL-28000 invariant:

- a successful lockscreen unlock transitions to canonical Home (desktop 1, drawer closed);
- a failed/rejected unlock never transitions to Home;
- stale `#app=` deep links must not reopen protected apps after boot unlock;
- PWA and native launches remain blocked while genuinely locked;
- when the host acknowledges unlocked, local `LockScreen.isLocked()` and lock state API must update in the same transition generation.

Check both event targets and page lifecycle after WebKit reload/resume. Avoid the old stale route/drawer issue.

## 6.4 Compare Archive Manager vs native apps

Use the Archive Manager app as a control:

1. Capture its registry entry/type, start URL/native binary/launcher route, required capabilities and lock guard.
2. Capture one failing native app's equivalent record/path.
3. Compare whether Archive Manager is a PWA and therefore bypasses the native launch handler.
4. Compare app ID, Bridge capability, launch source, session owner, host environment and app lock status.
5. Determine whether the failure comes from the native gate, Bridge authorization, `systemd-run` unit, `WAYLAND_DISPLAY`, `DBUS_SESSION_BUS_ADDRESS`, session user, or app-specific vault/password screen.

A working Archive Manager PWA does not prove native application launch works. Fix the common contract without adding an unsafe per-app exemption.

## 6.5 Native/Flatpak GUI process environment

The existing `_exec_native_app()` uses a systemd transient unit and hard-codes environment settings including:

- `XDG_RUNTIME_DIR=/run/nuxel-wayland`;
- `WAYLAND_DISPLAY=wayland-0`;
- `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/nuxel-wayland/bus`;
- `GDK_BACKEND=wayland`;
- `GSK_RENDERER=cairo`;
- `LIBGL_ALWAYS_SOFTWARE=1`;
- `WEBKIT_DISABLE_COMPOSITING_MODE=1`;
- `HOME` and XDG data paths.

Verify that these are correct for the actual session and that apps run as the intended `nuxel` user. Do not run ordinary GUI apps as root merely because the Bridge runs privileged. Per-app user/group and capabilities must be explicitly declared; privilege belongs in narrow helper services, not the GUI process. Remove forced software-renderer environment only after graphics acceleration path has been independently verified; preserve current safe fallback until then.

---

# 7. SYSTEM-WIDE TOP BAR AND NAV DOCK OVER NATIVE / FLATPAK APPS

## 7.1 Why the DOM top bar is insufficient

The top bar currently lives inside the Home WebKit document. A native GTK or Flatpak application is a separate Wayland toplevel; when it is activated, it occupies the display above/independently from the Home WebView. A DOM status bar cannot remain visible on top of that separate toplevel by merely changing its `z-index` inside the Home page.

The bottom dock already exists as a native overlay-layer Wayland layer-shell client. Extend the OS shell architecture to have a proper top status chrome owner as well.

## 7.2 Native status chrome implementation

Implement a small native layer-shell status-bar surface, or a coordinated native system-chrome process that owns both status and dock. Do not create two independent competing copies of status state.

Requirements:

- top-anchored layer-shell surface above normal application surfaces;
- appropriate exclusive zone so app windows do not render beneath it;
- safe-area/camera-cutout-aware layout based on actual output geometry;
- readable clock/radio/battery status;
- updates from one canonical read-only Bridge/status stream or a trusted local status protocol;
- bounded updates, no per-frame redraw/poll;
- touch targets route to an approved system action (QS/notifications) and obey lock policy;
- no privileged state changes from unauthenticated app messages;
- no access to `/dev/fb0` (Wayland client only);
- does not intercept app content touches outside its own height.

When native chrome is active over a native/Flatpak foreground window, hide the DOM topbar to prevent double display. When the Home WebView is foreground and native chrome isn't needed (e.g. development/fallback), the DOM bar may be used. Use one explicit ownership mode (`native`, `dom`, `transition`, `unavailable`) and never display both simultaneously.

## 7.3 Bottom dock behavior in native windows

Confirm the current OVERLAY layer is actually above regular GTK and Flatpak toplevels in the running Phoc build. Check the exclusive zone, keyboard overlay/OSK stacking and touch ownership. Make the dock visible in all unlocked foreground app states and after app switch. It must not disappear merely because the Home WebView is behind a native toplevel.

Lockscreen policy:

- the top status bar must be visible while locked;
- do not let Back/Home/Recents expose protected content while locked;
- keep bottom nav hidden on lock if that is the current security contract, or show an inert/lock-safe version only if it cannot bypass the lock. Do not sacrifice lock behavior to satisfy “always show” in app windows.

## 7.4 Status chrome lifecycle tests

- Home foreground: exactly one top bar, one dock.
- PWA foreground: top status + dock visible.
- GTK native foreground: top status + dock visible above app.
- Flatpak foreground: top status + dock visible above app.
- Recents open and app switching: no flicker, no duplicate bar, no lost input.
- Lock screen: top bar visible; app navigation cannot bypass lock.
- App exits/closes: overlays remain and Home returns.
- OSK visible: bottom dock and top bar remain in correct positions.
- output rotation/resize: anchors and hitboxes update.

---

# 8. USB FILE TRANSFER — REAL MTP WITH INTERNAL STORAGE AND SD CARD

## 8.1 Confirmed current blocker

`services/nuxel-s10/bin/nuxel-usb-mode.sh` has a `file_transfer_mode()` which probes for possible MTP responders (`umtprd`, `mtp-server`, `jmtpfs`) and configfs MTP/FunctionFS functions. Even if it finds candidates, it deliberately exits with:

`endpoint detected but activation helper is not configured; file transfer was not activated`

It writes `active:false` and `endpoint_state:not_activated`. `services/nuxel-bridge/src/usb_mode.py` only reports success if the helper wrote an actual active transfer state. Keep this truthful model; implement activation, do not falsify status.

## 8.2 MTP—not raw mass storage

Implement a real MTP device function (FunctionFS + MTP responder or a compatible kernel MTP gadget function if the current kernel truly provides one). Do not export the live Nuxel root/home filesystem as USB Mass Storage.

The MTP host should be able to browse:

- user-visible internal shared storage (e.g. Gallery, Downloads, Pictures, Documents, Movies/music where configured);
- the actual mounted external microSD card, if detected and mounted;
- only intentional shared roots, not `/etc`, `/var`, `/root`, service runtime, SSH keys, app credential/vault directories or arbitrary host paths.

MTP is a file-transfer object protocol, not a raw disk mount. Keep the OS filesystem and app data protected.

## 8.3 Preserve CDC-ACM serial console

The existing Nuxel USB recovery/serial console is critical. Keep it intact as a composite gadget interface alongside MTP if the current UDC/kernel/function set permits. Before any gadget rebind:

1. Read the active gadget config, UDC, functions, symlinks, VID/PID, interfaces and `ttyGS0` state.
2. Snapshot the config and prepare a deterministic rollback.
3. Stage the MTP function/responder.
4. Ensure CDC-ACM remains in the composite config.
5. Rebind atomically with bounded service ownership and rollback on failure.
6. Confirm host enumeration and MTP session.
7. Only then publish file transfer active.

Do not terminate the serial recovery console just to make MTP appear. Do not use NCM as a shortcut; the known Samsung 4.14.253 NCM teardown panic remains a hard blocker to that path.

## 8.4 Mac-specific host expectation

Important: generic MTP devices do not normally appear in macOS Finder as mounted disks. macOS typically needs an MTP client application. Test the phone with **OpenMTP** (Apple Silicon/Intel macOS; current official app supports macOS 10.14+ according to its project page) or another owner-approved MTP client. In OpenMTP the phone's storage is browsed in its own window. Do not report “Finder mounted a disk” when the only proof is MTP enumeration in OpenMTP.

If the owner specifically requires a Finder volume, that requires a separate macOS filesystem extension/translator or another Finder-supported protocol/client. Do not replace MTP with a dangerous raw live-filesystem mass-storage export. PTP may be considered for photo import, but it is not a general internal-storage/SD-card bidirectional file manager.

Reference pages for host test planning:

- OpenMTP: https://openmtp.ganeshrvel.com/
- OpenMTP transfer steps: https://openmtp.ganeshrvel.com/how-to-connect-devices
- Homebrew package status: https://formulae.brew.sh/cask/openmtp

## 8.5 SD card and mount logic

- Detect the real mounted removable-media path from the device's mount table/udisks or canonical storage provider.
- Never assume a device node or mount path; use the live mount metadata.
- Expose SD as a separate MTP storage object/volume when the responder supports multiple storage IDs.
- Keep it unmounted from unsafe host/raw ownership while serving MTP.
- Respect filesystem permissions and owner `nuxel` group.
- Handle card absent, unmounted, read-only, filesystem error, eject and insertion.
- If the responder supports only one storage object, design a controlled combined shared tree with an explicit SD subfolder, but do not pretend it is an independently mounted volume.

## 8.6 Bridge state model

Keep `selected`, `transition_in_progress`, and actual `active` distinct. Expose precise `endpoint_state`, e.g. `unsupported_kernel`, `responder_missing`, `staging`, `waiting_for_host`, `enumerated`, `session_active`, `failed`, `stopped`. A USB cable present is not proof of MTP; configfs staged is not proof of host enumeration.

On cable detach or host session loss, close the MTP session, clear active state, release only owned resources and restore the safe previous gadget config. Do not leave stale `file` indicator.

## 8.7 Physical MTP acceptance

1. Connect a data-capable USB-C cable to the MacBook.
2. Unlock Nuxel and select File Transfer through the lockscreen connection-mode selector/Settings.
3. Confirm macOS USB accessory permission if macOS asks.
4. Open OpenMTP and refresh the device list.
5. Confirm Nuxel is enumerated as MTP and internal shared folders appear.
6. Confirm a separate external SD storage object or explicit SD export tree appears when card is mounted.
7. Copy a known file Nuxel → Mac and compare SHA-256.
8. Copy a known file Mac → Nuxel Downloads or another allowed root and compare SHA-256.
9. Confirm Gallery/Files sees the new file.
10. Confirm serial recovery console remains usable if composite mode is claimed.
11. Unplug/replug and verify state cleanup/recovery.

If the current kernel lacks FunctionFS/MTP support, do not make the mode appear active. Record the exact kernel config/driver blocker and required future kernel work.

---

# 9. LOCKSCREEN AND APP DRAWER PERFORMANCE + GESTURE OWNERSHIP

## 9.1 Optimize the real S10+ software-rendered path

The lockscreen CSS source records a previous measured software-raster improvement: removing expensive alpha PNG/filter effects lowered WebKit process CPU from about 440% to about 78% during the earlier test. Preserve this class of win. Do not reintroduce permanent full-screen blur, large drop shadows, saturate filters or infinite idle animation.

Profile before and after:

- lockscreen first paint after boot/wake;
- lockhead drag and unlock feedback;
- app drawer opening and first visible grid;
- scrolling 1–5 screens of apps;
- desktop page swipe;
- app launch tap;
- return Home;
- QS open if it shares gesture arbitration.

Measure `performance.now()` timings, long tasks, `requestAnimationFrame` frame intervals and WebKit process CPU/memory where accessible. Do not claim improvement without a comparable baseline.

## 9.2 Current launcher gesture path

`pwa/nuxel-home/js/launcher.js` currently binds pointerdown/move/up/cancel at `document`, then also binds separate `touchstart`/`touchend` page-swipe logic. `_onPointerDown()` places app tiles into `PRESS_PENDING`, starts a 450ms long-press timer, and `_onPointerUp()` launches if the pointer did not move and was released over the original item. `_onPointerMove()` cancels the timer after movement exceeds roughly 8px.

This is vulnerable to gesture races on WebKitGTK:

- the same finger can be seen by pointer and touch paths;
- a swipe that opens the app drawer may continue over the newly exposed scrollable drawer;
- native panning and launcher page swipe may compete;
- a short scroll with small movement/no pointercancel can be interpreted as a tap;
- global document listeners do not necessarily provide stable pointer capture when surfaces rerender;
- `event.target` changes under the finger during drawer open/scroll.

Fix the state machine; do not merely increase a pixel threshold or add a click delay.

## 9.3 One gesture-arbitration state machine

Implement explicit gesture states such as:

```text
IDLE
  -> PENDING_TAP
  -> OPEN_DRAWER_GESTURE
  -> DRAWER_SCROLL
  -> DESKTOP_PAGE_SWIPE
  -> LONG_PRESS / HOME_EDIT
  -> TAP_COMMIT
  -> CANCELLED
```

Core rules:

- Gesture ownership is chosen at pointerdown and remains stable until release/cancel.
- A swipe that begins on the desktop/home surface and crosses the drawer-open threshold owns the entire pointer sequence. Opening the drawer must not allow the remaining delta to scroll the newly opened drawer.
- The drawer's scroll region becomes eligible only for a new pointerdown that begins inside the already-open drawer.
- A scroll gesture never launches an app, even if the finger ends over an app item.
- An app launches only after a genuine low-motion tap: same original item, short duration, movement below a deliberate slop threshold, primary pointer, no pointercancel/lost capture and no competing scroll/page gesture.
- A drag/scroll ending on another app item must not launch that other app.
- A tap on an app item fires exactly once. Ignore synthetic compatibility click after pointer path.
- Multiple pointers do not hijack app selection.
- Long-press timers cancel on movement/cancel/navigation/hidden screen.
- Pointer capture is owned by a stable root/gesture surface, not a tile likely to be rerendered.
- `touch-action` must be declared before pointerdown. Use appropriate `pan-y`/`none` regions and preserve native scrolling once the drawer is already open.
- Avoid duplicate touch + pointer processing; keep one authoritative gesture route in the embedded WebKit runtime.

## 9.4 Specific bug: drawer opens and immediately scrolls

Implement a recognizer that consumes the full swipe used to open the drawer. Do not set `drawerOpen=true` in the middle of an event and then let the same pointer's remaining movement hit the new scroll container. One robust option is to capture the pointer on the stable Home root and mark the opening gesture as consumed until pointerup; the opened drawer scroll container receives subsequent gestures only.

Test swipe-down from:

- empty desktop background;
- over a docked icon;
- over a non-dock app icon;
- top status area (which has its own QS pull gesture);
- a folder or widget.

Define priorities so status-bar QS pull and drawer-open gesture do not both fire.

## 9.5 Scrolling desktop must not launch apps

Desktop vertical scroll, horizontal desktop page swipe and drawer scroll must never open an app on release. Test movement at 3–7px, 8–15px, 16–40px and long drags; ensure slop/hysteresis is appropriate for physical touch jitter while still allowing normal taps. Also test stylus/mouse/keyboard activation so accessibility is retained.

## 9.6 CSS/software-rendering constraints

- Avoid `backdrop-filter`, full-screen blur, repeated shadows and filter animations.
- Use transform/opacity for short transitions where compositor path allows.
- Cache icon DOM; do not rebuild all app tiles on every scroll/state update.
- Delegate listeners; do not attach a closure for every grid cell on every render.
- Pause nonessential animations/polls while lockscreen/drawer is hidden.
- Use `content-visibility`/lazy work only after verifying WebKitGTK support and scroll geometry; do not break the app grid.
- Avoid synchronous layout read-after-write loops in pointermove.
- Keep the lockscreen and drawer at their actual 360 CSS-pixel layout target and physical display size.

## 9.7 Performance and gesture tests

Add browser-level tests using PointerEvent sequences and physical-device test scripts:

- short tap opens exactly one app;
- long press opens only edit/context behaviour;
- drawer opening swipe does not scroll drawer;
- new gesture inside drawer scrolls normally;
- scroll over an app tile never launches;
- horizontal page swipe never launches;
- scroll cancellation does not leave pressed state;
- long press canceled by movement;
- pointercancel/lostpointercapture cleans up;
- QS/status pull does not collide with drawer gesture;
- app drawer stays responsive with full registry.

Physically verify on the S10+ after deploy; desktop Chrome tests alone are not proof.

---

# 10. ONE SOFTWARE APP FOR NATIVE RPM/GTK + FLATPAK

## 10.1 Existing repository blocker evidence

`docs/a53/GNOME-SOFTWARE-RPM-FLATPAK.md` records a previous S10+ build with:

- no `dnf`, `dnf5`, `microdnf` or PackageKit/`pkcon`;
- no `gnome-software`;
- no Flatpak runtime/executable;
- no `xdg-desktop-portal` or GTK portal;
- no verified graphical polkit authorization agent for the Phoc session;
- no functional package network at that test time;
- `CONFIG_USER_NS` unset, blocking ordinary Flatpak/Bubblewrap sandbox expectations.

Re-probe the live device and current repo. Do not repeat old status as current truth without evidence.

## 10.2 Unified Software UX

Create one Software app and one canonical package transaction backend. The GUI should have sections/filters for:

- Native Fedora/RPM/GTK apps;
- Flatpak apps (only when genuinely supported);
- Installed apps;
- updates;
- local packages where explicitly supported.

Do not build two overlapping app stores. Nuxtore local signed bundles remain a distinct Nuxel package source; Software handles system RPM/Flatpak package management. The user should see the package type, source and capability.

## 10.3 Native RPM backend

Determine actual Fedora version/architecture, repo list, RPM database, package manager availability and network. If prerequisites are missing, implement the integration/build package plan and report the blocker; do not fake transactions.

Preferred supported stack, depending on Fedora release:

- DNF5 or DNF backend;
- PackageKit transaction service/DBus interface if compatible;
- AppStream metadata;
- GNOME Software if ARM64 packages and dependencies are compatible with the Phoc/Wayland session; otherwise a small Nuxel GTK client using the actual transaction backend;
- polkit daemon plus graphical agent integrated into the actual Nuxel session.

Security requirements:

- GUI never runs as root;
- each install/remove/update is a user-authorized transaction;
- preview package IDs, version, repo, architecture, dependencies/removals, disk space and origin;
- verify repository metadata signatures/GPG keys; no disabled signature checking;
- pass validated package IDs through typed DBus or argv APIs, never `shell=True` or arbitrary strings;
- handle offline, dependency conflict, insufficient space, cancellation, authorization denial and backend restart;
- persist real transaction result and logs without exposing secrets.

## 10.4 Flatpak gate

Flatpak must be enabled only after all prerequisites are tested on this exact kernel/image:

1. `CONFIG_USER_NS` or another supported user namespace mechanism exists and ordinary user namespace creation succeeds for the application user.
2. Bubblewrap (`bwrap`) works with the supported sandbox features.
3. Flatpak package/runtime is installed for `aarch64` and repositories/metadata are reachable and trusted.
4. XDG Desktop Portal and the GTK portal backend work in the Nuxel Phoc session.
5. Wayland socket sharing is limited to the intended socket; XDG runtime paths, file chooser and notification portals work.
6. SELinux/permissions remain appropriately confined.
7. A real test Flatpak installs, launches, displays a window, receives input and cannot read an intentionally forbidden host path.

If any prerequisite fails, Flatpak should appear as `Unavailable on this build` with the exact blocker and a disabled install action. Do not use `--no-sandbox`, `--filesystem=host`, `--device=all`, root execution or security-policy disabling to make it appear functional.

## 10.5 Registry and Flatpak launch support

The current app registry schema has types `native`, `pwa`, `system`, `template`; it lacks a first-class Flatpak type. Add a schema-versioned `flatpak` entry type with a validated application ID, installation scope (`user`/`system`), architecture and origin. The Bridge validates the record and invokes `flatpak run <trusted-id>` via safe argv in the actual `nuxel` session, not arbitrary client Exec text.

Flatpak app process environment must use the same real Wayland/D-Bus/portal session as the user. Track the Flatpak instance/window ID in Recents and close only the app-owned instance. Do not step outside the sandbox for navigation or window control.

## 10.6 Software tests

- Package backend absent;
- native RPM repo unavailable/offline;
- signed package installed successfully in an approved test environment;
- polkit authorized/denied/canceled;
- package update/remove preview and results;
- Flatpak user namespace missing => disabled/blocked;
- Bubblewrap error => disabled/blocked;
- portal missing => disabled/blocked;
- real ARM64 test Flatpak confined and launched when prerequisites are satisfied;
- arbitrary package/Exec injection refused.

---

# 11. NUXTORE — LIVE CONSOLE MUST BE RECOGNIZED AS ALREADY INSTALLED

## 11.1 Exact source identity mismatch

The inspected Nuxtore catalog contains an entry:

- package/catalog ID: `org.nuxel.Console`;
- name: `Live Console`;
- bundle: `org.nuxel.Console-1.0.0.bundle.json`;
- install app ID: `org.nuxel.Console`;
- `state_hint: available`.

The canonical Home registry contains:

- app ID: `org.nuxel.LiveConsole`;
- name: `Serial Live Console`;
- type `pwa`;
- URL `/pwa/nuxel-apps/console/index.html`;
- status `implemented`.

The same source tree/path is effectively present under two different IDs. Nuxtore's current state loader reads `nuxtore-state-v1` from localStorage/host config and its render code trusts the local catalog install state. It does not reconcile with the actual app registry inventory. This is why an app can be present and launchable through Home while Nuxtore still shows Available.

## 11.2 Reconciliation rules

Create a canonical package/app identity mapping, not a second uncontrolled registry.

- Canonical runtime app ID should match `org.nuxel.LiveConsole` because that is the Home app ID in the current registry.
- Preserve `org.nuxel.Console` as a versioned legacy Nuxtore package alias.
- Determine whether Live Console is a built-in system app, a catalog-managed package or both. In the current image it is registered in the canonical app registry and included in the Nuxel source tree.
- The UI should show a truthful state such as `Installed (system)` / `Included in Nuxel` rather than `Available`.
- Do not expose an ordinary Remove action for a built-in recovery console if removing it would remove an important recovery capability. It can show `Built-in`/`Managed by system` with no destructive action. If a separate user-managed copy exists, model it distinctly.
- `state_hint` remains descriptive catalog metadata only; runtime inventory overrides it.

## 11.3 Catalog inventory source

The Nuxtore installed tab should reconcile at startup and after install/remove:

1. canonical app registry;
2. built-in/image manifest;
3. package manager inventory for RPM/Flatpak where available;
4. Nuxtore staged package state and payload integrity;
5. start path/manifest availability;
6. current app owner/scope.

Represent `installed-system`, `installed-user`, `staged-unregistered`, `available`, `missing-payload`, `integrity-failed`, `unsupported` and other explicit states. Do not let stale localStorage override a newer registry response.

## 11.4 Tests

- catalog legacy `org.nuxel.Console` maps to canonical `org.nuxel.LiveConsole` exactly once;
- no duplicate Home icons;
- system-installed Live Console shows installed/built-in;
- catalog `state_hint: available` cannot override runtime installed state;
- no unsafe remove of the built-in recovery console;
- Home and Nuxtore reflect state without reboot;
- current app opens from both Home and Nuxtore details.

---

# 12. NUXEL AUTHENTICATOR — REAL ACCOUNT ENROLLMENT, QR SCAN AND RELIABLE TOTP

## 12.1 Existing implementation

The current app is at `pwa/nuxel-apps/authenticator/`:

- `js/totp.js`: RFC 4226/6238 HOTP/TOTP over WebCrypto; Base32 parsing; SHA1/SHA256/SHA512; 6/8 digits; configurable periods; `otpauth://totp/` parse/build; RFC 6238 Appendix B vectors.
- `js/vault.js`: encrypted envelope using AES-256-GCM and PBKDF2-SHA-256-derived key, fresh 12-byte GCM IV per save, encrypted account payload and encrypted-only export/import validation.
- `js/authenticator.js`: vault create/unlock, code rendering/timer, manual Base32 entry and pasted `otpauth://` URI import, copy/delete, encrypted export/import/re-key, self-test UI.

The current HTML describes QR-free manual/pasted entry; there is no real QR scanner implementation in this archive. The user wants normal authenticator enrollment by QR or secret code.

## 12.2 Required user workflow after vault unlock

1. User opens Authenticator.
2. If no vault exists, create it with the existing passphrase policy; if a vault exists, enter its password and successfully decrypt.
3. After unlock, Codes screen appears and Add Account is usable.
4. Add Account offers three local/offline paths:
   - Scan QR with camera (explicit camera permission, local-only decode);
   - Import QR image from Files/Gallery (local-only image decode);
   - Enter Setup Key / Secret or paste `otpauth://` URI manually.
5. Parse and validate data, display issuer/account/algorithm/digits/period preview, and ask for explicit Add confirmation.
6. Add to the encrypted vault, save, verify save success and show the new live code.
7. Copy code via clipboard only; never reveal it in a toast or log when clipboard is unavailable.

## 12.3 QR scanner implementation

Use a maintained QR decoder bundled locally with a pinned version/license and no CDN/network dependency. Inspect current package/runtime support; possible decoder candidates include a locally bundled ZXing implementation or another audited QR decoder. Avoid a remote JS CDN because this app handles authenticator secrets.

Support:

- live camera scanning using `navigator.mediaDevices.getUserMedia()` when WebKitGTK camera permissions and device capture are available;
- image upload (`image/*`) for screenshots/photos of provisioning QR;
- decode entirely in local app memory;
- only accept expected `otpauth://totp/` by default;
- optionally parse `otpauth://hotp/` only if HOTP is deliberately implemented and tested; otherwise refuse clearly rather than silently treating it as TOTP;
- display issuer, account, algorithm, digit count, period and a masked/hidden secret preview before import;
- explicit user action to add;
- stop all camera tracks immediately on success, cancel, tab change, app background or error;
- never transmit the image/QR payload to the Bridge, network, logs, analytics or crash report;
- allow QR scanner fallback to manual URI/Base32 when camera permission is unavailable.

Do not leave a camera preview running under another app or after the QR is read.

## 12.4 Manual secret and URI validation

Keep support for:

- standard Base32 secret (spaces and hyphens may be removed for input);
- `otpauth://totp/Issuer:account?...` URI;
- default SHA1, 6 digits, 30-second step where metadata is omitted;
- optional SHA256/SHA512, 6/8 digits and supported period values.

Validate issuer/account length, URI encoding, algorithm exactly, digits exactly, period bounded, decoded secret minimum entropy/size and duplicates. Do not accept malformed Base32, invalid percent-encoding, duplicate ambiguous query params, unsupported algorithms or truncated secrets. Never infer a period of 30 if the URI explicitly specifies an unsupported period without telling the owner.

## 12.5 Fix current UI/model correctness defects

- In `renderCodes()`, event listeners are created in a loop with `var a`; verify closures capture the correct immutable account ID. Replace with `let`, a factory function or stable `data-account-id` delegation. Copy/Delete for the first account must not act on the last account.
- `copyCode()` currently displays the OTP in a toast if Clipboard API access fails. Remove this. If clipboard fails, say “Clipboard unavailable; try again” without displaying the secret code.
- Ensure `save()` failure rolls back UI state or marks the account unsaved; do not display “Account added” before the encrypted envelope is durably stored.
- Serialize vault writes to avoid rapid Add/Delete/Re-key races. Each save must use a fresh AES-GCM IV and never reuse an IV under the same key.
- If `storeEnv()` localStorage write fails/quota is exceeded, surface failure; do not treat a caught exception as success.
- Use a cryptographically random account ID rather than relying solely on the current weak deterministic `idFor()` hash of issuer/account/secret prefix. Account IDs must not expose part of the secret in any external storage key/DOM ID/log.
- Do not let stale timer promises paint codes for accounts that have since been removed/locked.
- Stop the code ticker and clear the decrypted account/key state when the app is locked, backgrounded for a configured security interval or closed. Use visibility/page lifecycle correctly.
- Keep OTPs hidden from screenshots/recents snapshots if the native host supports sensitive-window treatment; at minimum avoid writing them to application lifecycle logs.

## 12.6 Secure at-rest storage

Preserve the encrypted-vault design. The current envelope is stored in app localStorage; it is encrypted, but a hardened Nuxel implementation should use an OS-owned storage/keyring facility where available:

- Secret Service/libsecret or another real session keyring for a wrapping-key integration, if installed and trusted;
- otherwise keep a strong passphrase-derived AES-256-GCM encrypted envelope and do not persist the plaintext passphrase/key;
- the key must exist only in memory after unlock and be cleared/released on vault lock/app security timeout;
- no secrets in plaintext JSON, localStorage, IndexedDB, service-worker caches, URLs, query strings, logs, crash telemetry or screenshots;
- encrypted export only; no plaintext export button;
- imported vault must be schema/version validated and decrypt only after the user's passphrase;
- ensure backups are user initiated and labelled encrypted;
- do not claim secure erase from browser memory; best-effort clearing is not a guarantee against memory forensics.

If using an OS keyring, a stolen vault file should remain useless without the user's passphrase or protected wrapping key. Do not silently make the vault unlock merely because the screen lock is open.

## 12.7 Microsoft Entra / “Microsoft Authenticator” compatibility

The Nuxel app may support standard third-party OATH TOTP for Microsoft Entra accounts **only if the tenant's authentication-method policy permits software OATH tokens**.

Implement a clearly labelled setup guide:

- “Microsoft Entra / Work account — standard TOTP”;
- explain that the user must register a third-party authenticator/software OATH method in the Entra security-info portal or through the organization's permitted enrollment process;
- scan the `otpauth://` QR or manually enter the provided secret;
- verify by entering a current code when requested;
- make clear that a generated TOTP code is not a push notification.

Do not claim support for Microsoft Authenticator proprietary capabilities:

- push approval;
- number matching;
- passwordless phone sign-in/broker;
- Microsoft Authenticator device registration or PRT issuance;
- Intune compliance or Conditional Access device claims;
- Microsoft Authenticator passkey storage/attestation.

No unofficial Microsoft push protocol reverse engineering, no FCM/MSAL impersonation and no bypass of employer Conditional Access. Link to the existing Nuxel Entra research/report and tell users to confirm tenant policy with IT.

## 12.8 Authenticator test plan

- all 18 existing RFC 6238 vectors still pass;
- Base32 known secret creates expected code;
- pasted `otpauth://totp/` URI produces account with the exact issuer, account, algorithm, digits and period;
- QR image import decodes exactly the same payload;
- live QR camera scan works on actual S10+ if camera provider is available;
- camera track stops after success/cancel/background;
- invalid QR, unsupported HOTP, malformed URI and invalid Base32 are rejected clearly;
- duplicate account detection works;
- add two accounts, copy/delete each and confirm correct rows are affected;
- clipboard failure never prints the OTP;
- vault save failure does not report success;
- re-lock/reload/unlock preserves accounts;
- wrong vault password refuses;
- encrypted export contains no plaintext account/secret fields;
- plaintext import refused;
- no network request/remote script is made by Authenticator.

Use test accounts/secrets generated specifically for tests. Do not ask the owner to paste real work/bank seeds into logs or into this task report.

---

# 13. NFC — VERIFY REAL CONTROLLER AND PHYSICAL TAG READ

## 13.1 Existing diagnostic path

The repo has:

- `configs/nuxel/nfc/nfc.json`;
- `tools/s10plus/a33/nuxel-nfc-diag.sh`;
- `tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py`;
- `docs/beta-finalization/manual-proof/12-nfc.md`.

The diagnostic order is controller → firmware → kernel subsystem → userspace stack → physical tag. The configured S10+ controller is Samsung sec-nfc / S3FWRN5 family, expected I2C address `0x27`. The current manual proof explicitly says physical tag test is `NEEDS_OWNER_TEST`; offline fixture PASS is not real NFC success.

## 13.2 Re-run exact device evidence

- I2C controller presence and driver binding;
- kernel module/driver/device node/sysfs class;
- firmware candidates and load status;
- NFC stack (`neard`/`nfc-list` or compatible current stack);
- antenna power/control status if available;
- bounded tag-read timeout and reader session;
- no fake UID or constant placeholder result.

Preserve the diagnostic's honest verdicts: `READY_FOR_TAG`, `BLOCKED_KERNEL`, `BLOCKED_FIRMWARE`, `BLOCKED_EXTERNAL_RESOURCE`, `PARTIAL`, `NOT_SUPPORTED_ON_DEVICE`.

## 13.3 Physical test

Only when `READY_FOR_TAG`:

1. Use a known first NFC tag at the documented upper-back antenna position.
2. Read the real UID and compare with the known UID.
3. Read a second different tag; it must produce a different correct UID.
4. Remove the tag; no phantom tag should be reported.
5. Repeat after toggling NFC state off/on only if a real safe power provider exists.

Do not claim NFC payments, card emulation, secure-element access or writing support from a tag-read-only test.

## 13.4 UI integration

Add/repair the Settings NFC panel and top-bar/QS status from the same provider. If no actual toggle mechanism exists, show read-only status and an explicit blocker rather than a fake enabled switch. Avoid duplicate provider polls.

---

# 14. FINGERPRINT — VERIFY THE S10+ ULTRASONIC SENSOR, NEVER FAKE ENROLLMENT

## 14.1 Hardware and software facts

The S10+ uses an ultrasonic under-display fingerprint sensor. The supplied source archive contains no demonstrated fingerprint provider, secure enrollment UI, libfprint driver integration or TEE-backed template manager. This task must re-check the actual hardware/kernel/TEE state, not assume it works just because the phone has a sensor.

## 14.2 Capability investigation

Read-only inspection:

- device tree binding and sensor driver probe;
- kernel modules/config and actual bound device/node;
- vendor secure world/TEE driver and required trusted application availability;
- fprintd/libfprint supported-device inventory, if installed;
- system logs for firmware/driver/TEE errors;
- Android vendor interface only as documentation, not as a template extraction path.

Do not read undocumented sensor registers, dump biometric templates, import Android template blobs or bypass the secure-world path.

## 14.3 Secure provider contract

Only if a genuine provider exists, expose safe operations:

- supported/ready state;
- whether the owner has an enrollment;
- opaque enrollment IDs/labels only;
- begin enrollment/cancel/result;
- verify attempt/result/timeout/lockout;
- delete enrollment.

Templates remain in the sensor/TEE/provider-owned protected storage. No raw template bytes are ever returned, stored in PWA state or exported.

If unsupported, show “Fingerprint unavailable in this Nuxel build” and preserve PIN/Pattern lock. Do not show a fake fingerprint setup wizard that stores a photo or fingerprint image in Files.

## 14.4 Physical proof

- enroll one real finger directly on the device through provider;
- verify positive recognition;
- verify wrong finger fails;
- verify timeout/cancel;
- verify rate limiting/lockout;
- remove enrollment;
- verify no template data appears in logs/files/API responses.

Do not mark fingerprint as working from unit fixtures alone.

---

# 15. SCREEN SECURITY — SWIPE, PIN, PATTERN, FINGERPRINT + PIN FALLBACK, OPTIONAL FACE

## 15.1 Current lockscreen is not a full credential manager

The inspected `lockscreen.js` implements a penguin drag/swipe gesture and host acknowledgement. The Settings page in the supplied archive does not include a real credentialed Security tab for PIN/Pattern/Fingerprint. Treat the current swipe as a convenience lockscreen interaction, not as proof of a secure PIN/password credential.

## 15.2 Add a real Security tab and single lock authority

Implement screen lock as a session-level trusted service/manager, with the Home lockscreen as a client UI. It must protect:

- Home and app PWAs;
- native GTK windows;
- Flatpak windows;
- Recents/toplevel activation;
- app deep links/native launch requests;
- screen off/wake, compositor restart and Home WebView reload.

The real lock state must be enforced at a host/session boundary. A JavaScript overlay alone is not enough. While locked, protected app surfaces must remain hidden/backgrounded, and the compositor/system-shell should keep the lock UI above them. Do not let a direct URL or native process launch bypass the lock.

## 15.3 User-selectable methods

Provide Settings → Security with:

1. **Swipe** — the current swipe-to-unlock interaction, explicitly marked lower security/no credential.
2. **PIN** — locally verified numeric PIN, with secure KDF storage and persistent rate limiting.
3. **Pattern** — validated pattern, derived to a salted verifier and protected against trivial patterns.
4. **Fingerprint + PIN fallback** — only if the fingerprint secure provider supports it, at least one fingerprint has been enrolled, and a tested PIN fallback exists.
5. **Face recognition (optional future/convenience)** — disabled by default and only offered if the platform provides robust liveness/anti-spoof capability, trusted local matching and rate-limited credential handling.

Do not make face recognition a secure unlock by merely comparing a webcam/front-camera image or embedding a local face classifier. A static photo/video replay is not strong authentication. If no depth/IR or trusted liveness path exists on this hardware/build, show Face Unlock as unsupported/experimental and do not let it replace PIN.

## 15.4 PIN and Pattern storage

- Use Argon2id/scrypt or a vetted KDF available in the target, with per-credential random salt. Do not invent a hash scheme.
- Verify in constant time.
- Store only salted verifier + algorithm/parameters + metadata in a protected host file or secure store, not plaintext or localStorage.
- Do not log digits/pattern points or include them in URLs/crash dumps.
- Enforce attempt rate-limits/lockout persistently across Home reload and system service restart.
- Credential change requires current credential verification, unless a documented recovery procedure is used.
- Pattern must have minimum complexity/point requirements and avoid obvious trivial patterns; store its derived verifier, not raw path.
- Support accessible PIN fallback when fingerprint fails or times out.

## 15.5 Fingerprint mode selection

Fingerprint may be selectable only if:

- secure provider reports supported and ready;
- enrollment has completed successfully;
- a PIN fallback has been set and verified;
- the lock manager confirms that both methods can be used.

If fingerprint stops working, times out, locks out or the TEE/provider goes unavailable, prompt PIN. Never silently downgrade to Swipe.

## 15.6 Unlock integration

- On successful credential/gesture verification, the session lock manager authorizes unlock and increments a generation.
- PWA LockScreen, native host, Bridge and overlay status receive the same authoritative new state.
- Only then are protected apps enabled.
- Failed credential does not hide lockscreen, show Home or let native apps launch.
- After system resume/host restart, restore lock state from the trusted manager.
- Do not permit direct API call `apps/exec` while the session is locked; the Bridge or app launcher manager should validate the authoritative lock state, not trust only the browser.

## 15.7 Lock tests

- Swipe-only works only if selected.
- PIN correct/incorrect, rate limit and restart persistence.
- Pattern correct/incorrect, trivial patterns rejected.
- Fingerprint enabled only when a real provider and PIN fallback are proven.
- Fingerprint timeout/failure prompts PIN.
- Face path remains unavailable without liveness proof.
- Lock persists across PWA reload, host restart, compositor restart and reboot.
- direct PWA URL/native launch/Flatpak launch/Recents cannot expose protected surfaces while locked.
- successful unlock returns to canonical Home and refreshes state so apps do not falsely claim the phone is still locked.

---

# 16. NATIVE AND FLATPAK LAUNCHER/REGISTRY UNIFICATION

## 16.1 Current registry and Bridge design

The canonical launcher registry is `pwa/nuxel-common/app-registry.json`, copied by the image builder to its on-device registry. `services/nuxel-bridge/src/api.py` has a fixed native allowlist/registry resolver and `apps/exec` route. `_activate_app()` currently recognizes `pwa` and `native`; schema `configs/nuxel/app-registry/app-registry.schema.json` enum is `native`, `pwa`, `system`, `template`.

Add Flatpak support without weakening existing app ID validation:

- new schema type `flatpak` with canonical Flatpak app ID/ref, architecture, user/system installation scope and trusted origin;
- no client-supplied `Exec`, path or command;
- Bridge resolves the app ID from canonical registry, checks it is installed and runnable, then executes a fixed Flatpak launcher with validated arguments;
- use correct per-user D-Bus/Wayland context and permissions;
- capture instance ID/PID/systemd unit and toplevel app ID for Home/Back/Tabs/close.

## 16.2 Native app user/session security

Review the existing `_exec_native_app()` which uses `systemd-run` with `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, D-Bus session bus and GTK backend. Verify the runtime path on the actual handset. Ordinary GUI apps must run as the `nuxel` session user, not root. Use a privileged helper only for operations that genuinely need privilege, under polkit/capability checks.

Per app declare:

- launcher type and trusted app identity;
- executable path or desktop ID from system registry;
- expected user/group;
- Wayland/D-Bus/portal requirements;
- navigation provider/action;
- window close semantics;
- restart/instance policy;
- capabilities.

## 16.3 App visibility and top-level lifecycle

A native or Flatpak app should not be marked foreground merely because `systemd-run` accepted the unit. Observe actual process start and a real Wayland toplevel/app ID. Return an error if the process exits before a surface appears. Register its toplevel in Tabs/Recents once visible. When app closes, clear lifecycle state and restore Home. Do not duplicate a terminal/Archive Manager surface as an iframe and native toplevel simultaneously.

## 16.4 Do not special-case Archive Manager

If Archive Manager works, that is evidence that one route works, not a reason to allow only it. Diagnose the difference among registry type, PWA/native, session user, lock gate and API capability. Use one trustworthy launcher contract and report per-app missing dependency or permission when applicable.

---

# 17. TEST MATRIX — COMPLETE REQUIRED WORK

## 17.1 Top bar and lockscreen

- icon silhouettes recognizably Wi-Fi/Bluetooth/Location;
- states for OFF, ON, CONNECTING, UNKNOWN, service error;
- Location enabled is not mislabelled GPS fix;
- no duplicates/overlap in portrait/landscape and camera safe zones;
- top status bar visible on physical lockscreen;
- lockscreen gesture remains functional;
- restricted QS behavior while locked;
- status data refreshes on wake and stops nonessential polling on display-off.

## 17.2 Navigation and haptics

- short Back within PWA history;
- short Back at PWA root does not minimize app;
- short Back in native browser navigates browser history;
- short Back in native app with declared Back provider is handled;
- short Back in app without provider reports at-root/no-op, does not invoke Home automatically;
- Home minimizes PWA/native/Flatpak;
- Tabs restores exact backgrounded app;
- long Back closes only exact foreground app;
- long Back haptic distinct and one-shot;
- canceled hold produces no close and no long pulse;
- physical haptic works when vibrator exists or state remains unsupported honestly;
- no dock/host/compositor/Bridge process is terminated.

## 17.3 Native and Flatpak app launch

- correct lock state before and after unlock;
- Archive Manager and at least two other installed native apps launch via same validated path;
- no false “unlock phone first” after successful unlock;
- PWA/native/Flatpak deep link blocked while genuinely locked;
- native app surface appears and is registered in Tabs;
- Back/Home/Recents/long-close work on each app type;
- invalid app ID/unknown app/unsupported Flatpak type refused;
- missing binary/package/ref reports clear reason;
- app launch doesn't run GUI as root;
- Flatpak disabled if sandbox prerequisites fail.

## 17.4 USB/MTP

- UDC/configfs/functionfs preflight;
- responder missing or kernel function missing reports unsupported;
- gadget activation and rollback;
- CDC-ACM preserved;
- MTP host enumeration on Mac;
- internal storage visible;
- SD card visible when mounted;
- bidirectional file copy with SHA-256;
- no live root/home raw mass storage;
- detach/reconnect cleanup;
- only one MTP host client owns the connection at a time.

## 17.5 Gesture/performance

- drawer open swipe not also scroll;
- scroll over app tile never launches;
- page swipe never launches;
- tap launches exactly once;
- long hold starts edit only if genuine;
- pointercancel resets state;
- drawer scrolling smooth with complete registry;
- lockscreen drag responsive;
- before/after timings and WebKit CPU/frame data recorded.

## 17.6 Software/Nuxtore

- native RPM backend absent/offline/ready/authenticated/denied;
- Software UI distinguishes RPM vs Flatpak;
- Flatpak sandbox checks;
- Live Console alias `org.nuxel.Console` maps to `org.nuxel.LiveConsole`;
- catalog state hint cannot override real inventory;
- system-installed Live Console shows installed/built-in;
- no duplicate launcher entry;
- no destructive remove of built-in recovery console.

## 17.7 Authenticator

- RFC 6238 test vectors pass;
- account added by manual secret, pasted URI, QR image and physical camera QR;
- valid algorithm/digits/period preserved;
- duplicate/invalid URI/QR rejected;
- Copy/Delete binds correct account;
- clipboard fallback does not show OTP;
- encrypted vault save succeeds or fails truthfully;
- encrypted import/export and wrong password;
- camera stops on cancel/background;
- no network access or secret logging.

## 17.8 NFC/fingerprint/lock

- NFC diagnostic stages run; physical two-tag UID test only if ready;
- fingerprint provider presence tested; actual enrollment/verify if supported;
- PIN/Pattern lock actual session-level enforcement;
- fingerprint requires PIN fallback;
- face recognition not enabled as secure mode without liveness proof;
- no app launch or native surface visible while locked;
- successful unlock synchronizes all lock state and returns to Home.

---

# 18. PERFORMANCE / FBDEV-FRIENDLY RULES

The S10+ is software-rendered through the current Wayland/Pixman/shared-memory framebuffer path unless the actual live graphics stack says otherwise. Optimizations must respect that reality:

- no backdrop blur, large full-screen filters or heavy drop-shadow loops on lockscreen/drawer;
- no permanent animated glow or idle transform;
- transforms/opacity for short transitions only where supported by current WebKit compositor;
- minimize DOM node creation and full-grid `innerHTML` replacement;
- one delegated pointer/click listener where possible;
- stable scroll container; don't disable native momentum scroll in the already-open drawer;
- no layout reads interleaved with writes during pointermove;
- defer thumbnails/icons below fold;
- pause polls/timers when panel/lockscreen hidden or display off;
- avoid launching app initialization for every catalog card;
- keep status/native chrome update frequency modest and event-driven;
- do not allocate/create a new native full-screen surface/buffer for every status tick;
- preserve the existing single framebuffer writer.

Measure p50/p95 for lockscreen ready/gesture, drawer open, drawer scroll, launch tap, Home transition, native app switch and status overlay response. The target is visibly faster and stable—not an arbitrary FPS claim unsupported by the physical bridge.

---

# 19. DEPLOYMENT AND DATA PRESERVATION

Before any live change:

- commit/checkpoint current source or create a patch/branch;
- record active file hashes and service versions;
- back up PWA host, app registry, USB config, lock state/config, Nuxtore state, Authenticator encrypted vault envelope, NFC config and relevant units;
- preserve all existing Authenticator vault data and notes;
- preserve USB CDC-ACM recovery and Wi-Fi SSH;
- stage binaries/assets, verify ARM64 architecture, permissions, owner and hashes;
- replace atomically when possible;
- restart only affected service(s);
- do not restart the entire compositor/framebuffer bridge unless necessary and the display-owner handoff is understood;
- do not guess device IP or credentials;
- do not flash kernel, use Heimdall/Odin/fastboot, write partitions or use forced reboot as a shortcut.

When `nuxel-usb-mode.sh` is changed, preserve the previous known-good gadget configuration and rollback. When a lock manager changes, ensure owner recovery path works before enabling credentials. Never deploy a lock build that might strand the owner without a tested fallback.

---

# 20. REQUIRED DELIVERABLES

Create/update:

1. `docs/beta-finalization/live/PWNAGE-49000-TODO.md` — owner source, status, dependencies, evidence and unresolved blockers for each feature.
2. `docs/beta-finalization/live/evidence/pwnage-49000/` with baseline, test logs, screenshots, host-enumeration hashes, native-app traces, lock state transitions, NFC/fingerprint physical evidence and deployment record.
3. Source changes to Home JS/CSS/HTML, native status chrome/dock C source, PWA host, Bridge/API, app registry/schema, MTP helper/service, Software package backend, Nuxtore catalog/reconciliation, Authenticator JS/HTML/CSS/library/manifest and lock/security provider where supported.
4. Test scripts for navigation lifecycle, haptics, lock gate, native/Flatpak launch, MTP, icon states, gestures, Software, Nuxtore and Authenticator.
5. Updated rootfs package/unit installation and PWA service-worker/cache versions.
6. Exact rollback/deployment instructions and SHA-256 checksums.
7. Final report with each result marked `PASS_PHYSICAL`, `PASS_AUTOMATED_ONLY`, `BLOCKED_KERNEL`, `BLOCKED_FIRMWARE`, `BLOCKED_PACKAGE_SOURCE`, `NEEDS_OWNER_TEST` or `NOT_SUPPORTED_ON_DEVICE` as appropriate.

---

# 21. FINAL DEFINITION OF DONE

## System chrome

- [ ] Wi-Fi icon clearly reads as Wi-Fi.
- [ ] Bluetooth glyph is recognizable and state is accurate.
- [ ] Location pin exists and uses canonical provider state; no false GPS-fix claim.
- [ ] Status bar visible above the lockscreen.
- [ ] Status bar remains above PWA/native/Flatpak windows through a true native system surface.
- [ ] No DOM/native duplicate status strip; safe zones and rotation are correct.

## Navigation

- [ ] Three-button native dock looks/works correctly on unlocked surfaces.
- [ ] Short Back navigates within the current app if it supports Back.
- [ ] Home backgrounds/minimizes and restores Home.
- [ ] Tabs shows/restores PWA/native/Flatpak toplevels.
- [ ] Long Back closes only foreground app.
- [ ] Long Back has a distinct one-shot haptic (physical if hardware supported).
- [ ] No stray short Back follows long hold; canceled holds do not close apps.

## App/lock integration

- [ ] False “unlock phone first” refusal fixed by state synchronization, not by bypassing security.
- [ ] Archive Manager and other native apps launch consistently after unlock.
- [ ] Native GTK and Flatpak apps receive global status/navigation chrome.
- [ ] Native/Flatpak Back contract is implemented or app reports no Back history honestly.
- [ ] Real lock prevents PWA/native/Flatpak/Recents bypass.

## USB/MTP

- [ ] File Transfer activates a real MTP endpoint.
- [ ] Mac MTP client (e.g. OpenMTP) lists internal storage and mounted SD card.
- [ ] Real bidirectional copy succeeds with SHA-256 verification.
- [ ] CDC-ACM serial recovery remains intact.
- [ ] No dangerous raw export of live root/home and no fake Finder mount claim.

## Performance/input

- [ ] Lockscreen visibly faster with measured evidence.
- [ ] App drawer visibly faster with measured evidence.
- [ ] Drawer opening swipe does not immediately scroll.
- [ ] Scrolling desktop/drawer never launches an app.
- [ ] Genuine taps launch once; accessibility keyboard activation remains supported.

## Software/Nuxtore

- [ ] One Software app manages supported native RPM/GTK apps.
- [ ] Flatpak is enabled only with the genuine sandbox prerequisites.
- [ ] Live Console recognized as installed/system-built-in through canonical ID reconciliation.
- [ ] No duplicate IDs/icons and no unsafe removal of built-in recovery functions.

## Authenticator/security hardware

- [ ] TOTP account creation works from QR camera, QR image, URI and manual code.
- [ ] RFC vectors pass; codes rotate and copy correctly; no secret leaks.
- [ ] Entra OATH/TOTP workflow documented accurately; Microsoft push is not falsely claimed.
- [ ] NFC physical test completed or exact blocker shown.
- [ ] Fingerprint physically tested through secure provider or marked unsupported.
- [ ] Swipe/PIN/Pattern/Fingerprint+PIN options are enforced by a real session lock.
- [ ] Face recognition remains disabled unless real liveness and secure local processing are proved.

## Delivery

- [ ] All modified active build paths are included in a clean ARM64 rootfs.
- [ ] Tests and physical evidence saved.
- [ ] User data, encrypted vault, SSH and serial console remain intact.
- [ ] Blockers and unsupported features are accurately labelled.
- [ ] Rollback instructions and final status report exist.

**PWNAGE-49000 is complete only when the actual device behaves correctly across lockscreen, Home, PWA, native GTK and Flatpak surfaces. A mock icon, an API return code, a locally changed flag or an offline fixture is not physical proof. Preserve the phone; keep the security boundaries real; and never turn an unsupported hardware feature into a fake green checkmark.**

🐧 **NUXEL — ONE SHELL. EVERY APP. BACK MEANS BACK. HOME MEANS HOME.**

---

# REFERENCES / MAC HOST COMPATIBILITY NOTES

These links are included to guide the Mac-side USB acceptance process and should be checked at execution time:

- OpenMTP official site: https://openmtp.ganeshrvel.com/
- OpenMTP connection steps: https://openmtp.ganeshrvel.com/how-to-connect-devices
- OpenMTP Homebrew package: https://formulae.brew.sh/cask/openmtp

Generic MTP should be verified with an MTP client window such as OpenMTP. macOS Finder does not ordinarily mount an MTP device as a native disk just because the device enumerates. Do not confuse MTP host enumeration with a Finder-mounted filesystem.
