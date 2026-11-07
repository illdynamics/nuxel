# DEEP ANALYSIS — Nuxel codebase before PWNAGE-88000

**Date:** 2026-11-07  
**Repository:** `/Users/wicked/x/nuxel`  
**Branch at analysis time:** `pwnage-80000`  
**Working tree:** extensively modified (PWA, bridge, configs, assets, build scripts); treat the checkout — not any older ZIP or prior prompt — as the source of truth.  
**Analysis type:** source-led static deep analysis plus review of the most recent on-device engineering reports (`docs/pwnage-87000/evidence/LATEST`, `docs/app-responsiveness-20261107/ENGINEERING-REPORT.md`, `docs/pwnage-85000/...`). No live S10+ session was available during this analysis; every on-device conclusion below is a hypothesis that PWNAGE-88000 must prove or disprove on hardware.

This document records what the current source actually does, the most likely root causes, and the exact places the implementation prompt must send the agent. It is deliberately honest about uncertainty.

---

## 1. High-level architecture relevant to these bugs

| Layer | Main source | Responsibility |
|---|---|---|
| Home PWA | `pwa/nuxel-home/*` | Lockscreen, launcher, app iframe lifecycle, DOM chrome, gestures, widgets, desktop layout |
| Lock-screen clock | `pwa/nuxel-home/js/lockscreen-clock.js`, `css/lockscreen.css`, `index.html` | Alarm/timer penguins and gestures |
| Clock daemon | `services/nuxel-clock/nuxel-clockd.py` | Durable alarms, timer state, occurrences, sound cues |
| Clock app | `pwa/nuxel-apps/clock/*` | Alarm/timer editor, scheduler client, local countdown painting |
| Native shell chrome | `tools/s10plus/a45/nuxel-navdock.c`, `nuxel-statusbar.c`, `nuxel-shell-chrome.sh` | Triple buttons and native top bar as layer-shell surfaces over Flatpak/GTK apps |
| Session/compositor | `tools/s10plus/a45/nuxel-session.sh`, `services/nuxel-session/systemd/*`, `tools/s10plus/a31`/`a67` | Phoc/Wayland, launch order, lockscreen, preload video |
| Display bridge | `tools/s10plus/a67/nuxel-wl-fb.c` | Solo `/dev/fb0` owner, screencopy, panel blank/unblank, wake/present ordering |
| Bridge/API | `services/nuxel-bridge/src/*` | App launch/focus, Flatpak, appearance, service RPCs, clock/audio status |
| Doom | `pwa/nuxel-apps/doom/*` | Chocolate Doom WASM shell, touch HUD, settings |
| Spoof work | `spoof/*`, `pwa/nuxel-apps/penguinterface/*` | Fedora-laptop LD_PRELOAD experiments and the current read-only PenguInterface app |
| Settings | `pwa/nuxel-apps/settings/*` | All device settings tabs; no services tab today |

---

## 2. Display-on → lockscreen: stale/zoomed desktop flash

### What the source does

1. `nuxel-wl-fb.c` owns the panel. On `screen-on`, `display_set()` immediately:
   - writes `bl_power=0` (unblank),
   - calls `panel_assert()` (`FBIOBLANK(UNBLANK)`, `FBIOPUT_VSCREENINFO`, `FBIOPAN_DISPLAY`),
   - restores brightness,
   - sets `display_on=1` and `force_present=1`.
   See `tools/s10plus/a67/nuxel-wl-fb.c:1040-1066`.

2. The presentation loop is blocked while `display_on == 0`; after screen-on it captures the *next* screencopy and blits it. There is a window between panel unblank and the first post-wake frame commit. During that window the DECON can scan out the panel's previous framebuffer contents. See `nuxel-wl-fb.c:1704-1720` and `1744-1768`.

3. The Home PWA detects display state by polling `host.statusRead('wlfb-state')` every **5 seconds**. It toggles `body.display-off`; it only calls `_lock('display-off')` on an observed `false → true` transition; on wake it dispatches `nuxel:display-on` but does **not** re-show/render the lockscreen. See `pwa/nuxel-home/js/app.js:1522-1562`.

4. While `body.display-off` is present, CSS hides the lockscreen with `visibility:hidden`:
   `body.display-off #lockscreen, ... { visibility:hidden !important; }`
   See `pwa/nuxel-home/css/style.css:586-606` and duplicate rules in `lockscreen.css` / `status-bar.css`.

5. The orientation/lock boot path may apply a portrait transform and the lockscreen wallpaper uses `background-size: cover`; the wallpaper is not guaranteed to be at the same scale/offset as the stale framebuffer content.

### Most likely root causes (must be instrumented, not assumed)

1. **Wake ordering in `nuxel-wl-fb`:** the panel is unblanked before a fresh, known-lockscreen frame is committed. The stale desktop frame is displayed (possibly at a different capture/scale state), then the first new frame snaps to the lockscreen.
2. **5-second class/poll latency in Home:** the PWA can still consider itself display-off (or still not locked) when the panel wakes. `body.display-off` hides the lockscreen; the first visible WebKit content can therefore be the desktop/compositor's cached frame.
3. **Lock-on-off transition misses:** if the phone is turned off and on faster than the 5 s poll, `_lastDisplayOff` may never observe the OFF sample, so `_lock()` is not called at all. The owner then sees the unlocked desktop until some later event.
4. **Lockscreen is not painted while display-off:** `visibility:hidden` removes the only safe surface from the capture path. On wake, WebKit may need several hundred ms to repaint it, while `nuxel-wl-fb` is already presenting.
5. **Scale/orientation mismatch:** a stale framebuffer captured at one output scale/transform is presented after the panel/scale changes on wake, producing the “zoomed-in” look before the normal frame arrives.

### Required proof

- Timestamped trace from physical Power press: `button-manager` action, `nuxel-wl-fb` `DISPLAY_ON`/`BL_POWER`/`DECON_ASSERT`/`FRAMES_OK`, `nuxel-pwa-host`/Home `display-off` class change, and first lockscreen frame.
- `foreign-toplevel list` / capture evidence at 0 ms, 100 ms, 500 ms, 1 s, 2 s after wake.
- The fix must make wake deterministic: lock synchronously, keep the lockscreen renderable, and do not unblank the panel until a fresh lockscreen frame is ready (or the bridge must cache/present the last known lockscreen frame before unblanking).

---

## 3. Lockscreen penguins: position, shake, duplicates, timer

### Current source

- The two lanes live in `pwa/nuxel-home/index.html:270-283`.
- `.lockscreen-clock-lanes` is anchored **right**, `top: 24%`, vertical stack; not centered. See `css/lockscreen.css:529-539`.
- `.lockscreen-clock-penguin` uses `transform: scale(.72)` for hidden and a `transition`; `.ringing` uses `nuxel-clock-shake` with only ±7° and ±5 px. See `lockscreen.css:551-607`.
- `lockscreen-clock.js`:
  - `render()` shows alarm if `clock.alarm_visible || clock.alarm_ringing`, timer if `clock.timer_visible || clock.timer_ringing` (`:112-133`).
  - Alarm pointer handling follows the finger and clamps to a safe horizontal band (`:135-197`).
  - Timer tap calls `stop-timer` (`:223-235`).
  - Instance starts on `nuxel:lockscreen-shown` and if `body.lockscreen-active` at load (`:237-240`).
- `system_indicators.py:1137-1179` computes `alarm_visible` from *any enabled alarm*, `timer_visible` from timer state `running/paused/completed` or a ringing timer occurrence.

### Likely defects / risks

- **Position:** both lanes are right-aligned, not centered over the wallpaper penguin. The requested placement requires measured wallpaper geometry (the existing `lockscreen.js` already has a `_coverCssY` helper and wallpaper constants; reuse that instead of hardcoded percentages).
- **Duplicate timer penguin:** the DOM contains exactly one timer lane, so a visible duplicate is most likely one of:
  1. two scheduler occurrences both interpreted as the timer (e.g. a `completed` timer plus a `ringing` timer occurrence, or a stale occurrence left after stop/start),
  2. a second rendering path (cached markup / stale lockscreen DOM node / a second script instance) that is not removed on state change,
  3. a visual overlap that looks like two penguins because the alarm lane and timer lane use the same anthropomorphic artwork and the alarm is incorrectly marked visible.
  The fix must instrument DOM node count, occurrences by `run_id`/`id`, and rendered rectangles; enforce exactly one timer penguin per active timer.
- **Shake strength:** current shake is subtle and may be masked by the scale transition. Heavier shake must animate the *inner image* or use a wrapper so it cannot conflict with the lane's positioning transform.
- **Alarm visible while enabled:** the backend logic looks correct (`enabled_future` is any enabled alarm), so a missing penguin likely means the projection is stale/unreadable, the client is polling the wrong endpoint, or the UI’s toggle is writing the inverse of what it displays. Test black-box: create a disabled alarm, verify no fire/penguin; enable it, verify penguin immediately; restart clockd and verify persistence.
- **Alarm on/off inversion:** `clock.js:316-321` displays `On` when `a.enabled` is true and sends `enabled: !a.enabled`; that is logically correct. The reported inversion must be reproduced end-to-end; likely sources are a stale `clockd.state`, legacy `sync` overwrites, or the alarm list cache in localStorage being rendered while the daemon says otherwise. Add explicit state-transition tests; do not “fix” by flipping the boolean again.
- **Timer under a minute / “0:00”:** `fmtSw()` returns `HH:MM:SS.cc`; the UI truncates with `.slice(0, 5)` for the toast (`clock.js:417`) and `tm-time` shows the full string, so a 30 s timer can display as `00:00:30.00` and a toast as `00:00`. Also the Set button calls `reset-timer` and then injects a local object, but the next 1 s scheduler poll can overwrite it with the daemon’s default `duration_ms`/`remaining_ms` (300000). This is a real display/state consistency bug. Fix formatting and make reset/set authoritative in the daemon.
- **Sluggish countdown:** `clock.js` calls `tick()` every 500 ms but `paintTimer()` paints from the last scheduler snapshot; the snapshot is refreshed only by a bridge RPC every 1000 ms (`:496-502`). A slow RPC, WebKit throttling, or a paused/busy renderer makes seconds appear in irregular jumps. Use a local deadline-driven `requestAnimationFrame`/250 ms paint loop and reconcile with the daemon at a lower rate.
- **Timer duplicate after expiry:** `nuxel-clockd._check()` sets `timer.state = "completed"` and creates a ringing occurrence, then later `_fire` promotes it. `stop-timer` marks ringing timer occurrences dismissed and sets timer to `acknowledged` if completed. If the UI refreshes in the middle of that transition, it can render both “completed” and “ringing” projections; dedupe by `run_id`.
- **Hands-on layout conflict:** lane `transform`/shake and the inner image/drag transforms must be separated. Current CSS uses scale on the outer element and shake on the same outer element; a drag utility also writes inline transforms. Define one transform owner per element.

---

## 4. App lifecycle / Applications drawer: invisible app still owns foreground

### Current logic

- `appSession` holds `{state, app, frame}` and is cleared only by `_closeAppSurface` / `_finishGracefulClose`.
- `_backgroundForegroundApp()` hides the frame/bar/status, sets `BACKGROUND`, resets chrome and shows nav; `home()` calls `_closeOverlays()` which calls `_backgroundForegroundApp()`.
- `back()`:
  - dismisses keyboard/search/QS/recents/folder/drawer,
  - for an ACTIVE PWA, tries app Back or `gracefulCloseForeground()` at root,
  - for a native app, calls `/api/v1/apps/back` and only closes when it gets `at_root` + `foreground`,
  - otherwise calls `home()`.
  See `app.js:1157-1204`.
- `gestures.js:14` defines state as `APP` only when `appSession.state === 'ACTIVE'`. If an app is invisible but still ACTIVE, upward drawer swipes are refused.
- `body[data-app-state="BACKGROUND"]` / hidden frame CSS exists, but no watchdog checks that an ACTIVE app surface is actually visible or that its compositor window exists.

### Most likely defects

1. A PWA at its root can report `handled` forever (history depth or an app `NuxelBack` handler), so a single Back never reaches `gracefulCloseForeground`; the app is still ACTIVE and no visible content owns the glass.
2. A native app’s `/apps/back` endpoint can return `handled`/`at_root` incorrectly or the window can close while `appSession` remains ACTIVE. Home then treats the foreground as occupied, and the drawer gesture is refused.
3. A hidden/backgrounded iframe can remain in hit-testing because of a CSS/runtime race; the app is visually blank but still intercepts input.
4. The long-Back force-kill works because it explicitly closes the surface and calls `home()`; that bypasses the stale state.

### Required fix direction

- Maintain a **foreground visibility truth** separate from `appSession.state`: PWA frame connected, not `hidden`, computed display not `none`, non-zero rect intersecting the viewport, and document not `hidden`; native app has an active real foreign-toplevel window.
- Add a bounded watchdog (e.g. 1–2 s) while state is ACTIVE: if no visible surface, background the app and show Home; never silently keep an invisible foreground.
- Make `gestures.js` permit the drawer whenever no visible foreground surface exists, even if a stale state string says ACTIVE.
- Make Back idempotent/bounded: if an in-app Back reports handled but the surface remains invisible or unchanged, background/close after a bounded retry; always allow a subsequent Home/drawer gesture.
- Add tests for: PWA at root, PWA with a history handler that lies, native window closed externally, iframe hidden by lifecycle, and long-Back recovery.

---

## 5. Triple buttons / top bar: gestures, two stripes, opaque chrome, space reclamation

### Current source and concrete bugs

1. **Two bottom stripes in PWAs:**
   - native `nuxel-navdock` strip paints a 3 px translucent handle at the bottom (`nuxel-navdock.c:216-229`);
   - Home CSS also paints a 4 px pill via `body.app-nav-hidden:not(.app-nav-revealed)::after` (`css/style.css:530-543`).
   Both can be visible at once. Pick one owner; remove the CSS pseudo when the native dock is present (or remove the native strip for PWA and use only one).
2. **Swipe direction bug in native dock:**
   - strip reveal: `(down_y - last_y) >= 18` → finger moved up (correct for reveal);
   - full dock intended to collapse when swiped **down**, but code uses the same upward expression: `!strip_mode && !dock_desired && touch_down && (down_y - last_y) >= 18` → only an *upward* movement hides it. See `nuxel-navdock.c:519-531`.
3. **Swipe direction bug in native top bar:**
   - strip reveal: `(last_y - down_y) >= 16` → finger moved down (correct);
   - full bar intended to collapse when swiped **up**, but code also uses `(last_y - down_y) >= 16` → a downward movement hides it. See `nuxel-statusbar.c:507-519`.
4. **Hit band too small / unreliable in messenger apps:** strips are 14 px (nav) and 12 px (top). A touch that begins a few pixels above the strip belongs to the app, not the layer surface. Increase the *input* band to a comfortable 32–40 logical px while keeping the visual handle thin; do not steal normal app content taps outside the edge.
5. **Content visible behind the open triple buttons:** `nuxel-navdock` full mode memsets the buffer transparent and blits only the three button PNGs (`render_frame`, `nuxel-navdock.c:204-240`). The app shows through between/behind the buttons. The full dock must paint an opaque Nuxel surface (or a fully opaque art mat) behind the buttons. The top bar already paints an opaque strip when full (`nuxel-statusbar.c:341-343`).
6. **Space not reoccupied when collapsing:** full dock/top bar set exclusive zone 62/36; strip mode sets exclusive zone 0. Native clients that honor the compositor usable area should grow/shrink, but Electron/Flatpak windows may not. For PWAs the iframe geometry is fixed; the revealed DOM chrome should reserve its band and the collapsed state should return the band to the app.
7. **Gesture ownership on native surfaces:** the strips use `wl_touch` on an overlay layer surface. A finger that starts in the app's window cannot be seen by the strip; that is expected. The fix is a taller transparent input region at the edge, not global input injection.
8. **DOM top bar not resizing the iframe:** when `body.app-status-revealed` the DOM bar paints over the app; when hidden, the app is full height. Verify the intended contract and make the frame top/height follow the actual revealed state.

### Required proof

- One visual affordance only per edge; capture screenshots at 0%/50%/100% gesture.
- Up = reveal nav, down = hide nav; down = reveal top bar, up = hide top bar; verified in Nuxel Home, at least one GTK app (Archive Manager), one Electron/Flatpak app (Signal/Telegram/Legcord/Caprine), and Firefox.
- Full chrome is opaque; no app glyphs visible through the button row; when collapsed, app content reaches the edge and touch at the former band reaches the app.
- Two-stripe regression test: no CSS pseudo strip and native strip simultaneously.

---

## 6. Doom: audio, top control layout, sensitivity, button behavior

### Concrete source facts

- `DEFAULT_SETTINGS = { sound: true, haptics: true, leftHanded: false }` (`doom.js:18-22`); persisted settings may contain `sound:false`.
- The engine argv **always** includes `-nomusic` (`doom.js:503-507`), and adds `-nosound` only when `settings.sound` is false. Thus music is always disabled even when the UI says SOUND ON.
- Sound starts after WAD fetch/engine compile; `callMain(args)` is invoked asynchronously. WebKit/WebAudio may require a trusted user gesture; an AudioContext created after a multi-second async chain can remain suspended. The WASM SDL code has `autoResumeAudioContext`, but that is not proof it ran or that the output route works.
- `hud-menu` calls `pauseEngine()` (app-level overlay), not the engine's own menu. `bindTap('use-button', tapKey('Space',32,' ')); weapon prev/next use BracketLeft/BracketRight`; `look-map` calls bridge `doom.map-toggle` or `tapKey('KeyM',77,'m')`. Mapping may not match the engine's expected scan codes.
- `doom.css` centers `-`/`+`/USE/MENU in `.twin-actions` at the bottom center; MAP is centered near the top. The requested layout is Use/Map top-left and −/+/Menu top-right (or two top clusters), away from the HUD.
- No sensitivity setting exists in the source; aiming is digital turn pulses in `applyAim`/`aimPulse`. “Default x3” must be implemented as a real multiplier on turn rate/duty cycle, persisted and adjustable.
- The engine is the Cloudflare WebSockets Chocolate Doom 3.0 WASM build (`engine/websockets-doom.js/.wasm`, provenance pinned). Do not replace it with a mock.

### Required proof

- Remove unconditional `-nomusic` when sound is on; test both a gameplay sound effect and music.
- Synchronously create/resume an `AudioContext` on the first Play gesture, or expose a truthful “tap to enable audio” if WebKit still blocks; never claim sound if the context is suspended.
- Verify each button end-to-end in-game: Use opens a door/switch, −/+ changes weapon, Map toggles automap, Menu opens the pause menu; Resume/Return/Exit work; no stuck keys.
- Verify default aim sensitivity multiplier is 3×, is persisted, and changes actual turn rate (measure pulses/time).
- Move controls to top-left/top-right with safe-area layout; do not cover the engine's HUD.

---

## 7. Waydroid: feasibility, integration, apps

### Source facts

- No Waydroid implementation exists in the current repository except historical notes that it is “not installed and not installed automatically” (`configs/nuxel/security/remote-access.json:114`).
- The live-required kernel config (`kernel/s10plus/configs/live-required.config`) does **not** list `CONFIG_ANDROID_BINDER_IPC`, `CONFIG_ANDROID_BINDERFS`, `CONFIG_ASHMEM`, or `CONFIG_PSI`. The S10+ kernel is a downstream 4.14.253 Samsung tree; its in-tree defconfig may still contain some Android pieces, but that must be read from the actual running `/proc/config.gz` and device nodes, not assumed.
- Waydroid needs binder/ashmem (or binderfs + memfd workarounds), user namespaces/namespacing, cgroups, and a compatible Android image. Flatpak already struggles with unprivileged user namespaces on this vendor kernel; Waydroid may be blocked by the same kernel gates.
- No ServiceNow, Microsoft Authenticator, or Aegis APKs/images are present in the repository.

### Required decision gate

1. On the live phone, prove `/dev/binder`, `/dev/binderfs`, `/dev/ashmem`, `binder`/`ashmem` modules, `CONFIG_ANDROID_BINDER_IPC`, `CONFIG_ANDROID_BINDERFS`, `CONFIG_ASHMEM`, `CONFIG_PSI`, and `unshare` behavior.
2. If prerequisites are absent, do **not** fake Waydroid. Mark it `BLOCKED_KERNEL` with exact missing configs/device nodes and prepare a separate kernel-change plan; do not flash a kernel as part of this userspace round without explicit owner approval and recovery gate.
3. If prerequisites are present, install the Fedora Waydroid package and official images, run it as the real `nuxel` user on the existing Wayland session, and create a launcher entry.
4. Install/test the requested Android apps from owner-provided official APKs or official stores; never log credentials. Microsoft Authenticator likely needs GAPPS/Play Integrity and may refuse; Aegis should work without GMS; ServiceNow Agent depends on its Android WebView/Play services requirements. Report exact behavior.
5. Test touch, keyboard, network, audio, rotation, lock/unlock, triple buttons/top bar over the Waydroid window, and recovery.

---

## 8. Services section in Settings

### Source facts

- Settings has 20 tabs (`pwa/nuxel-apps/settings/index.html:21-41`) but no Services tab.
- No generic service-control RPC exists in `api.py`; there are only targeted `systemctl` calls for app units and power/reboot.
- The bridge runs as root with systemd sandboxing; any new service-control endpoint must be allowlisted and must not execute client-supplied unit names/commands.
- Essential units include at least `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-button-manager`, `nuxel-touch-arm`, `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-web`, `nuxel-soundd`, `nuxel-clockd`, `nuxel-orientationd`, `nuxel-device-permissions`, `nuxel-audio-route`, `nuxel-audio-session`, `seatd`, and the USB/Wi-Fi restore units. Stopping several of these can blank the phone, kill input, or lose audio/alarms.

### Required design

- Read-only service inventory + explicit unlock gate.
- Server-side token/acknowledgement, not merely disabled HTML buttons.
- Essential flags in a shipped policy file; stop/disable of essential services blocked from the GUI, restart/reload additionally confirmed.
- Safe actions: start, stop, restart, reload, enable, disable; `daemon-reload`; `daemon-reexec` (highest risk, extra hold).
- Verify results with `systemctl is-active`/`is-enabled`; audit log; no secrets; no arbitrary units.

---

## 9. PenguInterface spoofing

### Source facts

- `pwa/nuxel-apps/penguinterface` is currently a **read-only device compatibility profile** viewer (`js/pengu.js`, `profile.json`); it has no spoof controls.
- `spoof/` contains the owner's Fedora-laptop experiments:
  - `fake_uname.c` — overrides `uname()` fields;
  - `fake_os.c` — overrides `uname()` and redirects `/etc/os-release` via `fopen`/`open`;
  - `fake_windows.c` — also spoofs hostname, `getaddrinfo`, `/proc/version`, and `/etc/os-release` via a temporary file;
  - `fake_os.js` / `teams-spoofer.js` — Puppeteer user-agent/stealth experiments;
  - prebuilt x86_64 `.so` files (not usable on the aarch64 phone).
- The current `fake_os.c` `open()` wrapper mishandles varargs (passes a `va_list` to `real_open`), lacks `openat`/`open64`/`fopen64`/`stat` coverage, and uses a fixed `/srv/fake-os-release`; it is a prototype, not a production implementation.
- No spoof API exists in the bridge, and no launch path injects app-scoped `LD_PRELOAD`.

### Required design

- Add a real PenguInterface spoof panel: current UA, UA editor, os-release fields, uname fields, target-app selector, apply/off/reset.
- Build a separately named aarch64 `libnuxel-spoof.so` with correct symbol interposition and recursion-safe `dlsym`; generate `/run/nuxel/spoof/os-release` and a profile JSON.
- Apply only to explicitly selected app launches by default; never to system services, the bridge, Phoc, the display bridge, or root shells. Global/system-wide spoofing requires an explicit warning/unlock and is out of scope unless the owner insists.
- User agent: per-app WebKit setting for Nuxel Browser/PWA host; Chromium/Electron `--user-agent`; Firefox profile/policy; verify the target app actually sees the spoofed UA.
- Reset removes the profile, environment injection and config; restarts affected apps; verifies native `uname`/os-release unchanged outside the spoof.
- Do not store credentials or break TLS/security; document anti-cheat/ToS and app-breakage risk.

---

## 10. GTK/Flatpak dark theme, browsers, DevMgmt tabs

### GTK/Flatpak

- `api.py:3376-3520` applies `gsettings color-scheme`, `gtk-theme`, `gtk-application-prefer-dark-theme`, and writes `/home/nuxel/.config/gtk-{3,4}.0/settings.ini`.
- It never injects `GTK_THEME` per process, and it only *lists* Flatpak theme extensions; it does not install `org.gtk.Gtk3theme.Adwaita-dark`. Flatpak GTK apps may therefore remain light, and Firefox is not GTK-themed in content.
- `flatpak_provider.launch_argv()` (`:1016-1056`) adds renderer, Wayland, Electron and QtWebEngine flags but no dark-theme or scale/UA environment.

### Browsers

- `shell/nuxel-browser-native/nuxel_browser_native.py` creates a GTK3/WebKit2 window with `set_default_size(360,760)`, no maximize/fullscreen, no mobile UA override, a fixed horizontal toolbar with a status label and entry, and no responsive/narrow-width layout. It can look unresponsive/desktop-sized on the phone.
- Firefox is launched natively (`api.py:891`) with `MOZ_ENABLE_WAYLAND=1`; there is no `user.js`/`policies.json` in the source to set device pixel ratio, dark system theme, compact UI, or responsive behavior. Flatpak Firefox has a separate renderer policy but no theme/scale prefs.
- Both need measurement of actual `window.innerWidth`, `devicePixelRatio`, toolbar overflow, and touch scrolling; then a generic, documented scale/UA/theme profile.

### DevMgmt

- `.tabs` already has `overflow-x:auto; scrollbar-width:none;` and hides WebKit scrollbars (`devmgmt.css:15-18`). The reported overlap is likely due to `min-width:max-content` + flex sizing/line-height at DPI/font scale, or the active tab not being scrolled into view. Add `flex-shrink:0`, explicit line-height/padding, `min-width:0` on the parent, `scroll-padding`, and `scrollIntoView({inline:'center'})`; verify at narrow widths and with long labels.

---

## 11. Software-app installs and future-app responsiveness

- `flatpak_provider.py` already has generic Electron/QtWebEngine detection and `launch_argv()` used by both `/apps/exec` and `/flatpak/launch`; `app_surface.py` normalizes compositor IDs; `api.py` has idempotent launch/focus. That is the correct foundation.
- Missing: a post-install integration hook. After a Flatpak/RPM install, Nuxel must refresh the Flatpak app list and desktop entries, update the launcher app registry, and create a generic launch profile (toolkit, WM class, scale, theme, UA, focus/maximize policy). Today, a newly installed app can be invisible to the launcher or need manual flags.
- `flatpak_provider` caches Electron/QtWebEngine detection per app id; new installs are cold and may not get a profile until a later probe. Make detection metadata-based and persist the result.
- Responsiveness: set generic display scale/theme/UA for GTK/Electron/Qt from measured output scale; do not add per-app flags. For unknown toolkits, use `flatpak run` + generic Wayland/software fallback, then focus/maximize and verify a real surface.
- `nuxel-software` launches only installed Flatpaks (`:482-510`); RPM installs are not followed by a launcher refresh. Add both.

---

## 12. Desktop/app/widget move and desktop assignment

- `launcher.js` already has drag state, ghost, grid hit-testing, edge dwell, `desktopLayout.move()`, and persisted layout (`:879-1100`). The long press at `:771-776` enters edit mode **and** starts a drag automatically; this makes the action-row interaction fragile.
- `_renderEditToolbar()` (`:1116-1129`) currently renders `Resize`, `Remove`, `Home settings`, `Done`; no `Move`, no desktop selector.
- `widgets.js` has resize/remove controls and its own long-press drag (`:207-227`, `:318-421`), but no widget action bar, no explicit Move, no desktop assignment button.
- `desktop-layout.js`/`layout-model.js` own the shared occupancy model; all changes must go through it, not a second collision map.

### Required behavior

- App action row: `Resize`, `Remove`, `Move`, `Desktop N`, `Done` (replace `Home settings`). Move arms a real drag (or a grid picker) and persists snapped cell/desktop; Desktop N opens a desktop picker and moves the app to a free cell.
- Widget long-press: same action row with Move/Resize/Remove/Desktop N/Done; child controls inside a widget must still work normally.
- Direct drag must follow the finger, snap, handle collisions, cancel/rollback, and survive reload/reboot.
- Exactly one instance/identity per app/widget; no duplicate after moving across desktops.

---

## 13. Performance and boot time

- `nuxel-wl-fb` is the single fb owner and already has damage tracking, static-frame skipping, idle capture pacing, and display-off sleep. Preserve these.
- `nuxel-preload-cinema` hashes the full 7.6 MB preload asset on every boot (`:866-889`), runs up to a 4 s launcher wait plus 1.2 s map delay, and the Home cover has a 40 s poll/backstop; these are measurable boot/perceived-boot costs.
- `nuxel-session.sh` may run a 10 s HTTP fallback wait; `NetworkManager-wait-online` and optional services can serialize boot; many services have broad `After`/`Wants` chains.
- Home/clock/status/lockscreen have multiple polling loops (1 s, 5 s, 10 s, 0.5 s); display-off guards exist but must be audited and made event-driven where possible.
- Performance work must be measurement-driven: `systemd-analyze`, `blame`, `critical-chain`, `/run/nuxel-wl-fb.state` frame timings, process CPU/RSS, WebKit/Phoc load, app launch times, and idle wakeups before/after. Do not add a GPU/DRM path that the kernel does not support.

---

## 14. Preloading video / boot handoff

- The asset is real: H.264 High 1080×1920, 24 fps, 144 frames, 6.016 s, AAC audio unused (`ffprobe`).
- Current controller: verifies SHA-256, starts `mpv` with `vo=wlshm`, fullscreen, no audio, `keep-open=yes`, `idle=yes`, IPC; waits for `launcher_ready`, a 1.2 s map delay, and display bridge readiness; publishes `starting` → `covered` → `done`/`fallback`; releases on EOF + readiness (or bounded grace/hard timeout). See `services/nuxel-preload-cinema/nuxel-preload-cinema:612-644`, `:887-1169`.
- The Home `#preload-cover` is opaque and is removed only when the controller reports `covered`/`terminal`; the controller may be below WebKit in z-order, in which case the owner sees a still/partial clip or the lockscreen before the clip ends.
- The 6 s clip “not playing fully” is most likely a z-order/visibility race, not a decoder duration bug: the controller can play while WebKit/cover hides it, and the user sees only the visible tail. It can also be cut short if the controller's `readiness.ready` path or hard timeout fires early (the source requires EOF, so prove the actual timeline).
- Fix must verify at least 6.0 s of advancing `playback-time`, frame changes, topmost surface ownership, and a clean handoff to a rendered lockscreen; no static poster or early release.

---

## 15. Static-analysis limitations and unknowns that PWNAGE-88000 must resolve

1. No live S10+ was attached during this analysis; all device behavior is hypothesis until the prompt's live reconnaissance.
2. The checkout is on `pwnage-80000` with many uncommitted changes. The live phone may be newer/different; live state and deployed hashes win.
3. Waydroid may be fundamentally blocked by the vendor 4.14 kernel; confirm before installing anything.
4. Flatpak/GTK dark mode may depend on packages/extensions not present in the image; confirm installed package and Flatpak extension inventory.
5. The duplicate timer penguin may be a daemon occurrence duplication, a DOM duplication, or a visual overlap; instrument all three before changing layout.
6. The zoomed wake frame may be a framebuffer ordering bug, a Home polling/lock race, or an output scale race; fix the ordering and the state machine together, then measure.

---

## 16. Recommended implementation order

1. Live/repo baseline + exact reproduction scripts for wake flash, gestures, clock, Doom, app drawer.
2. Display wake ordering + lock-state event/zero-flash gate (highest visual severity).
3. Lockscreen penguin layout/shake/duplicate + timer scheduler/format/state consistency.
4. App foreground-visibility truth + drawer/Back recovery.
5. Native chrome opaque surface, gesture-direction fixes, one stripe owner, space reclamation.
6. Doom audio/menu/layout/sensitivity.
7. Services policy/backend/UI.
8. PenguInterface spoof core and reset.
9. GTK/Flatpak dark theme + browser/Firefox responsiveness + DevMgmt tabs.
10. Software post-install profiles + desktop/widget move/Desktop N.
11. Performance/boot-time measurement and safe tuning.
12. Preload video z-order/full-duration proof.
13. Waydroid feasibility gate and, only if possible, installation/app tests.
14. Full regression, physical acceptance, evidence and rollback.
