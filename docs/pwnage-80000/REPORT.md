# PWNAGE-80000 — Nuxel Desktop, Navigation and Application Lifecycle Repair

**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**OS:** Fedora 43 aarch64, kernel `4.14.253-gf7194c1d15ed-dirty`  
**Live host:** `root@192.168.178.167` over Wi-Fi SSH  
**Key:** `~/.ssh/wicked_wqn_id_rsa` (readable, mode 0600, never copied)  
**Host-key verification:** pinned Ed25519 key matched the repository key; `StrictHostKeyChecking=yes` remained enabled.  
**Boot IDs exercised:** `8b2261a3b4d942a58a8185f0277cbb00`, `46e880cd-4595-4271-806b-bb179f098d22`, `06216bf6-9cbf-4b48-b46d-5ad008cf8db6`  
**Final backup sets:** `/var/backups/nuxel/p80000-20261105T150029Z`, `…T150517Z`, `…T145734Z`

## Executive result

The desktop now has one Back dispatcher, one app/window lifecycle manager, one native power-menu instance, a default-deny zoom policy, clean PWA teardown, a working Calendar (including numeric time entry), a complete NuXtore Doom package, and a prompt reboot path. The two controlled restart tests showed selection → gate → `systemctl --no-block` acceptance in **133 ms** and systemd reaching `reboot.target` in about **4 seconds**. The remaining ~30 seconds is bootloader/kernel boot time, not a userspace delay before issuing the reboot.

## Root causes and fixes

### 1. Zoom was not policy-controlled

**Cause:** zoom was largely a browser default; there was no central default-deny policy across WebKit frames, and no single place for a future Permission Manager decision.

**Fix:**
- Added `configs/nuxel/policy/zoom.json` with `"default": "deny"` and an empty `apps` map.
- Added `pwa/nuxel-common/zoom-policy.js` (`NuxelZoomPolicy`) with `allowed()`, `setPolicy()`, `reset()` and default denial.
- `nuxel-pwa-host` injects the policy into **all frames** via `WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES`.
- WebKit `magnification` and `zoom-level` are pinned to 1.0 and reset on change.
- Capture-phase GTK pinch/multi-press/deny handlers and Ctrl/Meta+wheel swallowing are installed.
- Every app viewport now uses fixed scale and `user-scalable=no`.
- No Permission Manager UI toggle was added; the policy document is the integration point.

### 2. Back could click hidden controls or stay on a stale history length

**Cause:** the dispatcher selected the first `[data-action="back"]` even when it was inside a hidden Calendar editor or hidden Doom HUD. It also used monotonic `history.length`, which remains `> baseline` after Back.

**Fix:**
- Central precedence in `pwa/nuxel-home/js/app.js`: keyboard → app-declared Back → real history → visible app control → graceful app close.
- Added `window.NuxelBack = {canGoBack, back}` to Calendar and Doom.
- Added WebKit Navigation API support and a depth-tracking `pushState`/`replaceState`/`popstate` probe.
- Hidden/disabled/zero-size Back controls are ignored.
- Normal Back never calls force-kill.

### 3. Invisible overlay/input-blocking layer after leaving an app

**Cause:** PWA surface teardown did not remove orphaned full-screen iframes, app status/bar nodes, pointer lock, focus, keyboard state, or power-menu DOM nodes. Background PWA closes were also misclassified as native because `appSession.frame` is null for a background app.

**Fix:**
- `_closeAppSurface()` now releases keyboard/focus/pointer lock, removes the exact session surface and every orphaned `.pwa-frame/.pwa-app-status/.pwa-app-bar`, retires the session, clears zoom, and requests a one-shot compositor/framebuffer repaint.
- `gracefulCloseApp()` classifies native vs PWA by app type and stored surface, not by the currently foreground frame.
- After a close, `diag-ui` reported `frames:0, iframes:0, powerMenus:0, folderSheets:0` and the desktop accepted drawer/navigation actions immediately.

### 4. Application lifecycle and Tabs gestures

**Cause:** lifecycle code was split between launcher, Recents and native bridges; swipes and long-Back did not share one state model. Background PWA closes followed the native endpoint.

**Fix:**
- One lifecycle state set: `CLOSED/LAUNCHING/ACTIVE/BACKGROUND/CLOSING/FAILED`.
- Recents cards show `closing…`; swipe left calls graceful close; swipe right calls force-kill.
- Force-kill is the same operation as long Back.
- Background native close is retired only after the compositor backend accepts it.
- Added a bounded root-console `ui-swipe <card-id> left|right` harness that dispatches real pointer events to the real Recents card handlers.

### 5. Keyboard dismissal and stale IME state

**Cause:** Back did not deterministically consult compositor keyboard visibility; the old host “dismiss keyboard” path also raised Home and could background a native app.

**Fix:**
- `nuxel-pwa-host` publishes `/run/nuxel-keyboard.visible` and pushes keyboard visibility to Home.
- Back checks keyboard visibility first.
- `host_hide_keyboard()` blurs the WebKit focus chain and uses a bounded native focus bounce that restores the same foreground app; it does not raise Home.
- `nuxel-button-manager` recognizes a downward swipe in the keyboard region and sends `action hide-keyboard`.
- Graceful close and force-kill blur fields, hide the IME, clear keyboard flags and release focus before teardown.

### 6. Calendar did not initialize; navigation and time input were broken

**Cause:** the Calendar element map stored kebab-case IDs (`prev-month`) while the controller read camelCase (`el.prevMonth`). The first listener binding threw, so no Calendar control was bound. This was a real live failure, not a styling problem.

**Fix:**
- Replaced the map with explicit `ELEMENT_IDS` (camelCase → HTML id) and fail loudly if any target is missing.
- Calendar requests persistent nav triple buttons and exposes `NuxelBack` for editor/keypad navigation.
- Time fields use `inputmode="numeric"`, `data-input-purpose="time"`, `pattern="[0-9:]*"`, and a Nuxel time keypad with digits, colon, clear, now, backspace and done.
- Added stable ids to keypad keys for live acceptance.
- Live: `bound:true`, 42 day cells, editor flex, keypad block, keyboard visible 1, typed `09:30`, keyboard 0 after Done.

### 7. Nuxel Doom / NuXtore

**Architecture:** Nuxel Doom is a PWA containing an unmodified Chocolate Doom 3.0 WebAssembly engine. Native Chocolate Doom 3.1.1 remains an optional internal comparison runtime, not a separate user-facing install. There is no standalone Chocolate Doom package or launcher requirement.

**Fix:**
- Removed the duplicate `doom-chocolate` and UZDoom app/package entries.
- NuXtore exposes one `org.nuxel.Doom` 2.0.0 package with the bundled WASM engine, Freedoom runtime contract, WAD roots, app icon and touch HUD.
- Re-staged and re-signed the full catalog after every source change.
- No commercial WAD is bundled. `freedoom1.wad`, `freedoom2.wad`, `freedm.wad` are the legal default free content; imported WADs require an ownership acknowledgement and are stored privately.
- Live `nuxtore-verify.py` reports every signed package verified; the unsigned demo remains refused.
- Live NuXtore UI install was tested from an unregistered state: the signed install registered `org.nuxel.Doom` as `installed_and_launchable`. The phone WAD catalogue reported 4 valid WADs.

### 8. Rotated app drawer

**Cause:** drawer layout retained old viewport/page-scale dimensions after a compositor transform, allowing the 3-column grid to be zoomed/cropped.

**Fix:**
- Drawer uses `repeat(var(--drawer-columns, 3), minmax(0, 1fr))`, `max-width:100%`, and no hardcoded portrait width.
- Orientation and `visualViewport` resize trigger zoom reset, cached drawer rebuild, explicit grid-template recalculation, and a forced reflow.
- Live matrix: all four poses verified with 3 columns and no horizontal overflow.

### 9. Blue rectangle after app exit / launcher reload / lockscreen

**Cause:** partial framebuffer damage could preserve a stale top region after a surface teardown or transition.

**Fix:**
- `nuxel-pwa-host` requests `force-redraw`/`after-app-close` after close, reload and lock transitions.
- `nuxel-wl-fb` implements a one-shot `repaint` control that forces two full-height frames (`REPAINT_FULL`), including damage reset and full dirty span. It is not a timer.
- Post-close/launcher-reload/lockscreen image samples at 0.15 s, 0.5 s, 1 s, 4–5 s and 11 s found no isolated stale top band. The blue lockscreen samples were the full lockscreen wallpaper, not a stale rectangle.

### 10. Power menu UI and backend

**Cause:** the native layer-shell OSD had an empty input region, so its painted menu could not receive touch; the control parser accepted only a bare `menu-select`, not the row index emitted by a finger tap. Settings also used a separate direct systemctl path.

**Fix:**
- The native OSD switches its layer-shell input region to the full modal surface while the menu is visible.
- Touch and pointer coordinates are hit-tested against the exact two-column/one-column card geometry actually drawn.
- `menu-select <index|id>` is accepted; touch and pointer both dispatch it.
- Home suppresses its duplicate DOM power menu on the phone; native OSD is the single instance.
- Settings/host restart and power-off both go through the button-manager gate and audit path.
- The OSD logs `OSD_INPUT interactive=1 rows=16`, and Settings polls `/run/nuxel/power-action.result` for a real backend verdict.
- Live lock, screenshot, Back and restart options executed. Recovery/Download Mode remained hard-refused with `NO_FLASH_INVARIANT`. Suspend and power-off were not executed because they would remove remote access; they share the same gate/systemctl path.

### 11. Duplicate power menus / gating

**Cause:** both the Home DOM and native layer-shell OSD could render a menu, and the Settings path read only the first line of pretty-printed gate JSON before bypassing the gate.

**Fix:** native OSD is the single phone instance, duplicate DOM roots are removed, and every power action uses one gate and one audit record. The gate is open with a 10 s debounce and a 10/hour cap; it is not a 30-minute lockout.

### 12. Reboot delay

**Cause:** the visible black period was a mixture of a delayed/incorrect frontend path, synchronous shutdown behaviour, and service stop timeouts. The old service configuration allowed long compositor/audio stops.

**Fix:**
- Reboot runs through `systemctl --no-block` only after the gate.
- Timestamped stages: `REBOOT_ALLOWED`, `REBOOT_SPAWNED`, `/run/nuxel/reboot-exec`, `REBOOT_ACCEPTED`, systemd journal.
- `DefaultTimeoutStopSec=15s`, compositor stop 2 s, display bridge stop 5 s, boot-sound stop 5 s.
- No global inhibitor removal and no kernel/bootloader writes.

**Measured live test:** selection `2026-11-05T15:06:13.753Z`; `REBOOT_SPAWNED at_ms=194401`; `REBOOT_ACCEPTED at_ms=194534` (**133 ms** after spawn); `reboot.target` reached at `16:06:17+01:00` (about 4 s after selection). SSH was back at `15:06:47Z`. The remaining ~30 s is bootloader/kernel boot, not pre-reboot userspace delay.

## Modified source areas

- `pwa/nuxel-home/js/app.js` — Back dispatcher, history probe, surface teardown, lifecycle classification.
- `pwa/nuxel-home/js/recents.js` — split graceful/force swipes, backend-accepted close, stable card ids.
- `pwa/nuxel-home/js/launcher.js`, `css/launcher.css` — three-column drawer reflow.
- `pwa/nuxel-home/js/osd.js` — native OSD coexistence.
- `pwa/nuxel-common/zoom-policy.js`, `configs/nuxel/policy/zoom.json` — central default-deny zoom.
- `pwa/nuxel-apps/calendar/*` — element map, explicit Back, numeric time keypad, cache version.
- `pwa/nuxel-apps/doom/*` — bundled WASM engine contract, Back state, touch HUD, WAD policy.
- `pwa/nuxel-apps/settings/power-menu.js` — backend verdict polling.
- `tools/s10plus/a45/nuxel-pwa-host.c` — all-frame zoom/keyboard injection, central actions, diag hooks, power verdict.
- `tools/s10plus/a45/nuxel-osd.c` — tappable native power menu and input region.
- `tools/s10plus/a45/nuxel-button-manager.c` — keyboard swipe, explicit menu row selection, reboot timing/verdict.
- `tools/s10plus/a67/nuxel-wl-fb.c` — one-shot full repaint.
- `tools/s10plus/a59|a68/nuxel-foreign-toplevel.c` — keyboard dismissal without Home.
- `configs/nuxel/{input,power,buttons}/…` — menu, FSM, gate.
- `services/nuxel-s10/systemd/…` — bounded stop configuration.

## Honest limitations

- Physical finger-on-glass taps could not be synthesized through Phoc’s no-udev hotplug path from this SSH session. Live tests used Nuxel’s real control FIFOs, the native OSD `menu-select` path, and a bounded pointer-event harness that drives the actual Recents listeners. The OSD’s touch/pointer geometry and input region were verified in code and at runtime.
- The accelerometer source remains unavailable; orientation was exercised through the authoritative `nuxel-orientationd` fixed modes (`--apply`), not physical rotation.
- Suspend and power-off were not executed because they would terminate remote access. They share the same gate/back-end path as Restart.
- Bootloader/kernel time (~30 s) is outside userspace and was not modified. No kernel was flashed.
