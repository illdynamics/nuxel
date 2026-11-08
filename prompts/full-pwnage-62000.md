# FULL-PWNAGE-62000 — OPERATION PERMANENT PENGUIN CHROME, LOCKSCREEN SUPREMACY, FAST BOOT & TRUE CONSOLE PRESENCE

**Mission type:** repo-specific implementation, repair, integration, regression and measured S10+ validation  
**Target repository:** `illdynamics/nuxel`  
**Primary device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**Target userspace:** Fedora ARM64 (current repository baseline Fedora 43)  
**Current graphics/session baseline:** Samsung downstream Linux 4.14.253, Phoc 0.54, wlroots 0.19, Wayland headless output, `nuxel-wl-fb` as the sole `/dev/fb0` writer  
**Mission ID:** PWNAGE-62000  
**Companion kickoff:** `pwnage-62000.md`

---

## 0. EXECUTION ORDER — READ THIS FIRST

You are not being asked to write another research report. You are being asked to **inspect, implement, test, document, package and prepare a safe deployment** for the four connected defects below. Work in the actual repository and modify the real code paths used by the S10+ image. Do not stop after proposing fixes.

The user has reported:

1. Stremio (Flatpak) appears to launch, but the Nuxel top bar and the three-button Back / Penguin Home / Tabs navigation disappear behind or are absent over the app. The lockscreen can also be covered by a Flatpak/native application. The lockscreen must remain the highest-priority visible system state, including over GTK, Wayland and Flatpak applications.
2. A reboot leaves the display black for an unnecessarily long time before the handset actually restarts.
3. After the penguin boot animation, `nuxel-preloading-screen.mp4` plays, but its final frame can remain frozen for a long time before the real phone UI appears. Improve the handoff and reduce boot time without showing a blank screen or an unlocked desktop prematurely.
4. The live-console lockscreen indicators are inaccurate. USB serial and the general live-console status currently look closer to correct, but the Wi-Fi console indicator remains active merely because Wi-Fi/SSH is available. It must represent an actual active interactive Wi-Fi SSH console session, and go off when the last such session closes. The base live-console indicator and the transport-specific penguins must have distinct meanings.
5. While implementing these fixes, find and repair closely related defects discovered in the same code paths. Do not turn this into an unrelated wholesale rewrite.

### Required order

- **Phase A — baseline and invariants:** inspect the current branch, current build manifests, packaging and active source paths; run existing tests; establish the exact baseline.
- **Phase B — secure lock and persistent shell chrome:** fix the compositor-level lock behavior first, then integrate a native top bar over native/Flatpak windows and guarantee the Back/Home/Tabs dock remains available while unlocked.
- **Phase C — true console indicators:** separate transport readiness from an active interactive session, add reliable per-session tracking and test opening/closing multiple SSH terminals.
- **Phase D — preload and boot handoff:** remove the stale/final-frame wait, consolidate timing configuration and split presentation readiness from touch readiness.
- **Phase E — reboot black-screen and shutdown latency:** identify the actual shutdown blocker from evidence; make the smallest safe unit-specific repair and improve the visible shutdown transition if technically safe.
- **Phase F — integrate, test, report, package and prepare deployment/rollback.**

Do not reorder the lock enforcement after cosmetic chrome. Do not perform a physical reboot just to see what happens. Use the existing Nuxel live-deploy/reboot safeguards and obtain a recoverable state before any owner-controlled reboot.

---

## 1. REPOSITORY FACTS ALREADY CONFIRMED — DO NOT RE-DISCOVER THEM BY GUESSING

The following facts were inspected in the supplied `nuxel-main (11).zip`. Re-open each file in the live checkout and verify its current contents before editing, because the repository may have moved since the archive was created.

### 1.1 Active phone compositor and window model

- The S10+ session is a **Phoc/Wayland session**, not a traditional X11 desktop and not a full Phosh session.
- `nuxel-wayland.service` starts the Phoc session through the GPU wrapper and `nuxel-session.sh` is run inside that compositor context.
- `nuxel-pwa-host` is the GTK/WebKit host for the Nuxel Home PWA. The Home status bar and lockscreen are DOM elements inside this host's Wayland toplevel.
- Native GTK and Flatpak apps are separate Wayland toplevel surfaces. They can cover the Home PWA's DOM because CSS `z-index` only orders elements inside one WebKit surface; it cannot raise that surface above another Wayland client.
- The compositor exports `zwlr_layer_shell_v1`. Nuxel already uses it for the native navigation dock, so a native layer-shell chrome surface is an established approach on this target.
- `nuxel-wl-fb` is the single display bridge and sole writer to `/dev/fb0`. It mirrors the compositor to the Samsung DECON framebuffer. **Preserve the one-writer invariant.**

Primary sources:

- `services/nuxel-session/systemd/nuxel-wayland.service`
- `services/nuxel-session/systemd/nuxel-wl-fb.service`
- `tools/s10plus/a45/nuxel-session.sh`
- `tools/s10plus/a45/nuxel-pwa-host.c`
- `tools/s10plus/a45/nuxel-navdock.c`
- `tools/s10plus/a45/nuxel-statusbar.c`
- `pwa/nuxel-home/js/app.js`
- `pwa/nuxel-home/js/navigation.js`
- `services/nuxel-bridge/src/api.py`
- `services/nuxel-bridge/src/security_provider.py`

### 1.2 A native status bar already exists in source but is not wired into the S10+ session

`tools/s10plus/a45/nuxel-statusbar.c` is a real native Wayland layer-shell implementation. It:

- creates a `zwlr_layer_shell_v1` surface on the `OVERLAY` layer;
- anchors itself to the top edge;
- draws the status strip into a `wl_shm` buffer;
- leaves an empty input region so taps pass through to the app beneath;
- uses `nuxel-foreign-toplevel list` to determine whether a non-Home native application is foreground;
- reads `/run/nuxel/security/lock-state.json` and fails closed (unreadable/missing means locked);
- hides itself when locked or when Home is foreground;
- shows itself over a non-Home toplevel.

However, the current `tools/s10plus/a45/nuxel-session.sh` explicitly says the Home DOM status bar is the one top bar and **does not start** the old native `nuxel-statusbar` overlay, because the earlier overlay rendered a reduced duplicate over Home. The source is therefore not a functioning solution for the reported Flatpak case in the current session.

`tools/s10plus/a45/build-a45.sh` currently builds `nuxel-navdock` and `nuxel-text-input-probe`; it does not build `nuxel-statusbar`. A repository-wide source search in the supplied archive did not find a current installer or session launch for `nuxel-statusbar`. Verify the current image builder and deployment manifests before concluding that none exists in a newer branch.

**Expected implementation:** finish/build/package/start the native status bar (or replace it with an equivalent integrated native layer-shell shell-chrome manager). It must show only when a native/Flatpak application is actually in front, hide on Home, hide while locked, and never duplicate the DOM Home bar.

Important: the existing C source may need compilation cleanup, additional headers, Cairo/Pango sysroot linkage, orientation/scale fixes, lifecycle supervision and a less expensive foreground watcher. Do not just add a `nohup` line and assume it works.

### 1.3 A native navigation dock already exists and is started

`tools/s10plus/a45/nuxel-navdock.c`:

- creates a bottom-anchored `zwlr_layer_shell_v1` surface on the `OVERLAY` layer;
- draws the three buttons from the supplied artwork into a `wl_shm` buffer;
- handles touch and maps taps to `back`, `home` and `recents` actions;
- accepts `show`, `hide` and `status` commands through `/run/nuxel-navdock.cmd`;
- refuses to show when the authoritative lock state is locked or unknown;
- only shows at startup if the launcher-ready marker exists and the session is unlocked.

`tools/s10plus/a45/nuxel-session.sh` starts `/usr/lib/nuxel/nuxel-navdock` with `nohup`.

`pwa/nuxel-home/js/app.js` calls `_setNavDock(true)` during native app launch. `_setNavDock()` sends `nav-show`/`nav-hide` through the host. `tools/s10plus/a45/nuxel-pwa-host.c` maps these actions to the FIFO.

Despite this intended design, the user sees the dock disappear over Stremio. You must reproduce and instrument the real state transition. Check all of the following instead of assuming the native dock is working merely because the C source exists:

- Was the binary built for AArch64, installed at the path the session script executes, and linked to the correct Wayland library?
- Is it alive after the session starts? Does `/run/nuxel-navdock.out` show a connection or protocol error?
- Does `/run/nuxel-navdock.state` contain `NAV_DOCK_READY`, `NAV_DOCK_SHOW`, `NAV_DOCK_HIDE`, `LAYER_CLOSED`, or errors?
- Does `/run/nuxel-navdock.cmd` exist and is the command FIFO readable by the host?
- Does the startup `home_ready()` marker match the actual marker written by the current launcher build?
- Does `lock_state_read()` parse the exact current lock-state format and distinguish locked, unlocked and unknown correctly?
- Does the JS call `nav-show` after a successful app launch and does the host actually write the FIFO?
- Does another launch, lock, recents or focus path send a later `hide` command?
- Does the installed binary match the source? Do not rely on a source-level test alone.

The navigation dock must remain visible over **all native Wayland app surfaces**, including Stremio and GTK apps, whenever the phone is unlocked. It must be hidden on the actual lockscreen and restored only after unlock.

### 1.4 Current lock path does not guarantee that an already-running native app is moved behind Home

`pwa/nuxel-home/js/app.js` `_lock()` currently:

- adds the PWA's lockscreen CSS classes;
- blurs fields and hides the keyboard;
- hides the native navigation dock;
- displays the PWA lockscreen;
- asks `NuxelSecurityLock` to persist the authoritative locked state;
- sends `screen-off` to the display bridge.

`tools/s10plus/a45/nuxel-pwa-host.c` handles `screen-lock` by hiding the native dock and sending `lock` to `/run/nuxel-wl-fb.cmd`.

The bridge's native app launch path in `services/nuxel-bridge/src/api.py` checks the lock state and refuses a **new** app launch while locked. That is good, but it does not by itself minimize or lower an app that was already open when the lock action occurred.

The Home lockscreen is currently a DOM surface within `nuxel-pwa-host`. If Stremio/GTK remains the active full-screen Wayland toplevel, the PWA's `z-index` and `lockscreen-active` CSS cannot put the lockscreen above it. This is a compositor-level ordering problem, not a CSS problem.

**You must fix this at the Wayland/compositor window-management level.**

### 1.5 The Wi-Fi icon has a proven readiness-versus-session bug

`services/nuxel-bridge/src/tri_link_status.py::wifi_status()` determines whether Wi-Fi SSH is *available*. It checks facts such as:

- a usable non-loopback IPv4 interface exists;
- SSH listens on TCP port 22;
- public-key-only authentication policy is configured;
- a host key exists;
- authorized keys are present (or the service cannot inspect them).

When these prerequisites pass, it returns `status: AVAILABLE`. That is a capability/readiness result, not proof that an interactive SSH terminal is connected.

`services/nuxel-bridge/src/system_indicators.py::console_transports()` currently does this:

```python
wifi_detail = facts.get("wifi_status", "unknown")
wifi_ready = wifi_detail == "AVAILABLE"
established = _established_ssh_sessions()
...
"wlan": {
    "active": wifi_ready,
    "source": wifi_detail,
    "sessions": len(established),
}
```

The `sessions` number is reported but ignored when setting `active`. This is the direct reason the WLAN-console icon can stay on when Wi-Fi and sshd are available but no terminal is connected.

There is a second flaw: `_established_ssh_sessions()` currently counts established TCP/22 sockets from `/proc/net/tcp{,6}` globally. It does not reliably associate those sockets with the Wi-Fi interface, a specific authenticated session, the `nuxel` user, or an interactive PTY. Fix the model, not just the final boolean.

`_TRANSPORT_CACHE_TTL_S` is currently five seconds. The lockscreen indicator JavaScript in `pwa/nuxel-home/js/lockscreen-indicators.js` also has a five-second safety refresh. A session-close event may therefore take too long to disappear even after the backend is correct.

### 1.6 The general live-console state and transport state are currently conflated in the UI

`system_indicators.py::live_console()` reports fields including:

- `service_armed` — a `nuxel-console` daemon process exists;
- `transport_connected` — the USB data link is actually up;
- `session_active` — the console owns its TTY or has a validated serving lease;
- `active` — current code's USB-console active predicate.

The frontend `lockscreen-indicators.js::_render()` drives the large live-console indicator from:

```javascript
this.state.liveConsole || this.state.wlanConsole
```

and separately drives serial, USB and WLAN transport icons.

The requested visual contract must be made explicit and consistent:

- **Base live-console indicator penguin:** the Nuxel Live Console service/daemon is running in the background and is ready to accept a session. It may be lit while no transport client is connected.
- **Transport-specific penguins:** only light when an actual live interactive session is currently using that transport.
- With the daemon running and nobody connected: base live-console indicator on; serial/USB/WLAN type icons all off.
- With an actual USB CDC-ACM serial console session: base live-console on and the serial/USB-console type icon on, with the physical USB data-link proof still required.
- With an actual interactive SSH console session arriving over Wi-Fi: base live-console on and WLAN-console type icon on.
- When the final session for a transport closes: that transport icon turns off promptly. If the daemon remains available in the background, the base live-console indicator remains on.
- A Wi-Fi interface being up, sshd listening, a key being configured, or a successful transport preflight is **not** an active console session.
- Do not mark USB-network SSH active on the known-broken 4.14.253 NCM path. If the network gadget is unavailable, keep that transport explicitly unavailable; do not confuse it with USB CDC-ACM serial.

Preserve the existing charging, USB physical-link, file-transfer and Bluetooth indicator semantics.

### 1.7 The preloading video has both a deliberate final-frame hold and conflicting timing sources

The supplied repo includes:

- `services/nuxel-preload-cinema/nuxel-preload-cinema`
- `services/nuxel-preload-cinema/nuxel-preload-cinema.service`
- `services/nuxel-preload-cinema/README.md`
- `configs/nuxel/boot/preload-cinema.json`
- `assets/nuxel-preloading-screen.mp4`
- `tools/s10plus/a45/nuxel-session.sh`
- existing tests under `tests/pwnage31000/`

The configuration inspected in the archive says:

- clip: H.264 High, 1080×1920, 24 fps, 144 frames, around 6.016 seconds, around 7.63 MB;
- audio: AAC-LC, deliberately muted;
- output: `wlshm`;
- `--hwdec=no` is passed by the player;
- `--vo=wlshm` is used;
- `--keep-open=yes` / idle IPC behavior keeps the player around for a final still frame;
- `max_display_ms` is 20,000;
- `hard_timeout_ms` is 25,000;
- `readiness_grace_ms` is 12,000;
- config `early_wait_launcher_ms` is 4,000;
- config `early_map_delay_ms` is 1,200.

In `tools/s10plus/a45/nuxel-session.sh`, the early controller is launched with environment defaults that instead set:

- `NUXEL_PRELOAD_EARLY_WAIT_LAUNCHER_MS` default to 6,000;
- `NUXEL_PRELOAD_EARLY_MAP_DELAY_MS` default to 800.

The controller gives environment settings precedence over JSON. Therefore, the session script can silently override the checked-in 4,000/1,200 values with 6,000/800 values. Reconcile this. Use one authoritative configuration source and only honor explicit operator environment overrides.

The controller's main loop deliberately waits for both video EOF and `readiness.ready`. At EOF, mpv's `--keep-open=yes` may keep displaying the final frame while the code waits for the real lockscreen readiness gate or the 25-second hard timeout.

The readiness model currently includes the launcher/boot mode, a fresh framebuffer/display-on receipt, and a settled touch status (or an explicit touch warning). A slow touch initialization can delay the visible lockscreen even though the launcher and framebuffer are already usable. Split **presentation readiness** from **input readiness** so delayed touch setup does not keep an unnecessary frozen video frame on screen.

The early controller is started by `nuxel-session.sh` with `nohup` and a bounded launcher wait. The systemd unit is intentionally not enabled on the phone session path to avoid a second controller. Preserve that single-owner policy.

### 1.8 Reboot is already partially optimized; do not reintroduce an unbounded global timeout

The source tree already contains measured shutdown-stop work:

- `services/nuxel-s10/systemd/nuxel-wayland.service.d/30-fast-stop.conf` documents a historical 90-second default stop timeout during which Phoc/WebKit/PipeWire remained in final SIGTERM for roughly 46 seconds. It bounds that unit to 8 seconds.
- `services/nuxel-s10/systemd/nuxel-wayland.service.d/40-bounded-stop.conf` further sets a 3-second stop timeout and uses a unit-specific `ExecStop` to signal the wrapper and child processes.
- `services/nuxel-s10/systemd/fast-stop/` contains 5-second stop overrides for the bridge, HTTP bridge, web server, touch-arm, button manager, boot sound and framebuffer bridge.
- `services/nuxel-s10/systemd/nuxel-audio-session.service.d/10-stop-bound.conf` sets a 4-second stop bound for the audio session.
- `tools/s10plus/a45/nuxel-pwa-host.c` already runs `systemctl reboot` asynchronously so the GTK/WebKit UI does not block on the systemd job.

A user-visible long black screen still occurs. This means you must verify whether these drop-ins are actually installed and active on the target and identify the remaining stop job, device/kernel shutdown stage or premature display teardown. Do not merely lower global systemd stop timeouts again.

---

## 2. NON-NEGOTIABLE SAFETY AND ARCHITECTURE INVARIANTS

These are hard acceptance constraints, not suggestions.

1. **One framebuffer writer:** `nuxel-wl-fb` remains the only userspace owner/writer of `/dev/fb0`. Do not let `nuxel-statusbar`, `nuxel-navdock`, the PWA host, mpv, a shutdown splash or a new lock manager open/write `/dev/fb0` directly.
2. **Wayland overlay chrome only:** top bar, nav dock and any new window guard use supported Wayland/Phoc protocols. Do not use a second framebuffer daemon to draw a bar.
3. **Lock is fail-closed:** missing/unreadable lock state means locked. No native/Flatpak app may appear above the lockscreen, receive user touch/keyboard input while locked, or be launchable while locked.
4. **Never defeat app sandboxing:** do not remove Flatpak's sandbox, disable user-namespace controls, add setuid bubblewrap, weaken AppArmor, or bypass the kernel policy to make Stremio appear manageable.
5. **Do not weaken SSH:** preserve key-only authentication, pinned host-key and known_hosts behavior, allowed-user controls, and current firewall rules. Session tracking must not expose private keys or SSH environment details over the public HTTP bridge.
6. **No transport fabrication:** Wi-Fi readiness is not a session. A listener is not a session. A configured USB gadget is not a physically connected host. A stale lease is not a live client.
7. **No unbounded waits:** every readiness wait, IPC request, foreign-toplevel command, process probe and shutdown hook must have a bound and explicit fail-safe behavior.
8. **Boot fail-open:** a bad/slow preloading video must reveal the real locked phone UI within a short bounded interval. It must never block Home/lockscreen construction, unlock or the framebuffer handoff indefinitely.
9. **Do not release the lockscreen early:** the video overlay may be released as soon as the real lockscreen presentation is ready, but the UI must remain locked until authentication/actual unlock succeeds. Touch-not-ready must be visibly degraded, not treated as unlocked.
10. **No blind forced reboot:** do not use `reboot -f`, `systemctl reboot --force`, `echo b > /proc/sysrq-trigger`, `kill -9 1`, or any forced power-cycle path to hide slow service shutdown.
11. **No unrelated kernel/boot flash:** this mission is userspace/session integration. Do not modify BOOT partitions, initramfs binaries, kernel, DTB, modem firmware, bootloader, partitions or recovery image unless you first prove a userspace-only solution is impossible and document that this prompt does not authorize such flashing.
12. **Preserve rotation and touch transforms:** portrait and landscape must keep correct bar/dock anchors, safe areas, button touch geometry and framebuffer ownership. Do not hardcode a single output name or panel resolution.
13. **Build must fail honestly:** if a required native overlay cannot be built, packaged or verified, the build must report a real blocker. Do not silently omit it or say it is deployed when it is only present in source.
14. **No test-only success claims:** distinguish `OFFLINE_TESTED`, `BUILT`, `DEPLOYED`, `OWNER_TESTED` and `VERIFIED_ON_S10PLUS` accurately.

---

## 3. PHASE B — PERMANENT SYSTEM CHROME OVER FLATPAK, GTK AND ALL NATIVE APPS

### 3.1 Define the required chrome behavior as a state machine

Implement and document one authoritative state machine. The desired behavior is:

| Compositor/session state | Home DOM top bar | Native top bar | Native Back/Home/Tabs dock | Lock UI |
|---|---|---|---|---|
| Home visible, unlocked | visible | hidden | visible or existing Home navigation equivalent, never duplicated | hidden |
| Stremio/Flatpak foreground, unlocked | hidden behind Home | visible above app | visible above app | hidden |
| GTK/native app foreground, unlocked | hidden behind Home | visible above app | visible above app | hidden |
| App dialog/popover open, unlocked | hidden behind app | chrome remains visible without blocking dialog input | chrome remains visible and usable | hidden |
| Locked, app was foreground | hidden | hidden | hidden | **always visible above app** |
| Locked, app tries to raise/new app request | hidden | hidden | hidden | **remains visible and locked** |
| Unlock succeeds | returns to canonical Home | hidden until a non-Home app is foreground again | restored after lock UI removal | hidden |

Do not leave a duplicate DOM and native bar visible simultaneously. Do not show the bottom dock on top of the lockscreen. Native app focus must not make the lockscreen appear absent.

### 3.2 Complete and wire the native top bar

Inspect `tools/s10plus/a45/nuxel-statusbar.c` and the current Home status-bar implementation in `pwa/nuxel-home/css/status-bar.css` / `pwa/nuxel-home/js/status-bar.js` (or whatever current files own those functions).

Requirements:

1. Build the native top bar for AArch64 as part of the existing A45 native build or a clearly named successor. Use the repository's cross sysroot and exact target libraries. Ensure Cairo/Pango/Wayland linkage is actually available in the image. Fix all warnings that indicate ABI, ownership, buffer lifetime or missing declaration problems.
2. Add its binary and any protocol headers/data to the real S10+ image build and installation manifest. Confirm file permissions, library linkage, architecture and runtime search paths.
3. Start exactly one native bar instance after Wayland/layer-shell is ready. Prefer a well-defined service/supervisor with bounded restart behavior over an unmanaged `nohup` process if that fits the current service model. Do not accidentally start one from both systemd and the session script.
4. It must use the `OVERLAY` layer and the real active output. Anchor top/left/right. React to orientation/output changes and scale changes without using hardcoded `HEADLESS-1`, `DSI-1`, 360x760 or a stale buffer size.
5. It must show over any foreground non-Home app surface, including Stremio and ordinary GTK3/GTK4 Wayland clients. Confirm layer ordering on the actual Phoc 0.54/wlroots 0.19 build.
6. It must hide on Home, lockscreen, preloading cinema and any boot surface where it would duplicate or cover a higher-priority Nuxel screen. Lock always wins over native foreground detection.
7. Its input region is empty/pass-through, as intended by the existing C source. Verify taps at the top edge still reach the app/quick gestures when appropriate. Do not let a top bar surface swallow touch or keyboard events.
8. Render a full enough native equivalent of the Nuxel top strip to make it feel like the same OS: time, connectivity, battery and relevant current status. Keep the scope small, do not add expensive per-frame stats gathering, and do not show fabricated sensor or network states.
9. Keep the status bar light. Cache read-only sysfs facts at sensible intervals and update time on a low-rate timer. No busy loops, no shell subprocess on every frame, and no unbounded `popen()`.
10. For foreground detection, the existing source calls `nuxel-foreign-toplevel list` from a 500 ms polling loop. Investigate a persistent protocol subscription/event-driven watcher or a bounded low-cost poll. At minimum, remove redundant subprocess invocations and prove the bar does not produce UI lag or process churn.
11. Use one shared definition of the Home toplevel app ID, lock state file and status bar dimensions rather than fragile string matching scattered across C files.
12. Add a `/run/nuxel-statusbar.state` state contract with clear readiness, shown/hidden reason, foreground app ID, lock state and failure reason. Keep it small and per-boot. Do not expose private app command lines.
13. Add a statusbar readiness handshake. App launch must not report a stable shell chrome state until the dock and bar daemons have confirmed readiness or a clear degraded fallback has been selected.

The existing statusbar C source checks `FT_BIN` and `session_locked()`, creates an overlay layer and renders. Build on it if correct; do not blindly duplicate it with a second implementation.

### 3.3 Make the navigation dock genuinely persistent over native/Flatpak apps

Audit the complete chain:

`app.js::_launchNative()` → `_setNavDock(true)` → `NuxelHost.action('nav-show')` → `nuxel-pwa-host.c` FIFO writer → `/run/nuxel-navdock.cmd` → `nuxel-navdock.c::dock_show()` → layer-shell configure/map.

Repair it so that:

- `nav-show` is idempotent and returns/records whether the surface is actually mapped;
- a command issued before the native dock has created its FIFO is not silently lost; add a bounded readiness/retry/ack mechanism;
- `dock_show()` logs a clear reason when blocked by lock, launcher readiness, missing layer-shell global, missing output, configure failure or protocol closure;
- showing the dock is tied to the authoritative unlocked state, never just to a UI boolean;
- an unlocked non-Home app foreground state keeps it visible even if the app launch callback returns before the Wayland surface maps;
- a delayed app map does not trigger a later `hide` that races the show;
- native app close/back/home reliably restores the canonical Home behavior;
- the actual bottom bar does not obscure the app content more than its intended exclusive zone, while remaining visually above the app;
- the PNG artwork remains correct and scaled under both portrait and landscape output transforms;
- taps and long-press behavior still map to Back / Penguin Home / Tabs (Recents) and do not accidentally activate the app underneath;
- when the lockscreen is active, the dock is hidden, and no background retry is allowed to make it reappear until unlock is complete.

Add a single shell-chrome state coordinator if the existing FIFO model cannot guarantee ordering. Avoid two separate daemons issuing contradictory commands.

### 3.4 GTK and Flatpak app integration tests

Test at least:

- Stremio Flatpak: launch from Nuxel Home, wait for real Wayland surface, check native top bar and bottom dock are visible above it. Do not merely check that the process is running.
- One GTK app from the image (for example GNOME Software, Settings or another actual installed GTK app): the same chrome must appear.
- One additional native app with dialogs/popovers if available.
- App opens a dialog/popover/context menu: it must remain usable; top status and bottom controls must not intercept it except the intentional bottom dock hit area.
- Rotate to each supported portrait/landscape mode, then return to portrait: top bar and dock maintain geometry and touch accuracy.
- Switch between native app, Home and Recents: no one-frame duplicate, stale dock, missing bar or app remains above Home.
- Lock while Stremio is playing, lock via UI, lock via inactivity/display path and lock via the trusted host command: lockscreen is visible above the app every time.
- While locked, cause an already-running app to request attention/open a second window. It must not cover or receive interaction above the lockscreen.
- Unlock with the real supported gesture/auth path: input goes to the lock UI, unlock completes, Home becomes frontmost and shell chrome returns in the correct state.

A screenshot from the actual handset or a compositor capture correlated with the raw framebuffer must be retained for each key scenario. Do not claim success based only on `systemctl is-active` or the existence of a layer-shell process.

---

## 4. PHASE B2 — MAKE THE LOCKSCREEN COMPOSITOR-LEVEL TOP PRIORITY

This is a security and usability defect, not a cosmetic detail.

### 4.1 Establish a single lock authority

Use `services/nuxel-bridge/src/security_provider.py` and `/run/nuxel/security/lock-state.json` as the existing authoritative state. The existing provider treats missing/invalid state as locked. Preserve that policy.

Do not create a second independent lock boolean in a native C daemon that can diverge from the bridge. Native helpers may cache a read, but must refresh and fail closed. Add a generation/timestamp or atomic write contract only if it is compatible with existing consumers.

### 4.2 On lock, move the Home lockscreen surface above every application

Investigate the existing `nuxel-foreign-toplevel` tool and the actual Phoc-supported foreign-toplevel/activation protocols. Add a fixed, trusted compositor action such as `lock`/`enforce-lock` if supported. It must:

1. Be callable only from the trusted Nuxel host/service; no client-supplied arbitrary app IDs or commands.
2. Minimize or otherwise move every non-Home app to the background without killing its processes.
3. Restore/activate the `nuxel-pwa-host` Home surface so that the actual PWA lockscreen is the visible screen.
4. Hide native status bar and navigation dock.
5. Re-check lock state before and after every asynchronous step. If it becomes unknown or locked during a race, stay locked.
6. Record a receipt such as `/run/nuxel/lock-enforcement.state` with timestamp, lock generation, active surface, hidden/minimized surfaces and errors.
7. Be idempotent and bounded. It must not wait forever for an app to minimize.

Do not assume that asking Home to raise once is enough. A native app can request activation after the initial lock action. Implement a lock enforcement watcher/supervisor or compositor policy that notices a non-Home toplevel becoming active while locked and immediately returns the visible state to the Home lockscreen. Subscribe to foreign-toplevel activation events if possible; otherwise use a small bounded monitor with no busy loop.

### 4.3 Locking from a non-Home application must work

When a native/Flatpak app is foreground, the Home JS code may not receive DOM events in the intuitive way. The trusted button/host/display path must be capable of forcing the lock independently of the app.

Audit:

- `tools/s10plus/a45/nuxel-pwa-host.c::action_perform("screen-lock")`;
- `pwa/nuxel-home/js/app.js::_lock()`;
- display-bridge lock command handling in the source for `nuxel-wl-fb`;
- hardware button / inactivity lock actions;
- native app launch lock gate in `services/nuxel-bridge/src/api.py`.

The screen-lock path must set authoritative lock state, background/minimize apps and activate Home before a stale app can cover the lock. It must not depend solely on a JS CustomEvent sent into a hidden Home view.

### 4.4 Preserve unlock touch and do not introduce an invisible input trap

A tempting implementation is a fullscreen transparent Wayland overlay. Do not add one without proving its input behavior. A full-screen layer-shell surface can intercept touch/keyboard and accidentally prevent the actual lockscreen from receiving its unlock gesture.

Preferred approach: keep the PWA Home surface frontmost and force/minimize external apps while locked. If an additional shell-level shield is necessary, it must either route the real unlock input to the lockscreen correctly or be designed so it does not intercept the touch path. Physical touch tests must prove the unlock swipe, edge gestures and lockscreen buttons still work.

Do not kill Stremio or GTK apps as a shortcut. They should remain backgrounded and may resume after unlock according to the existing Home policy. On successful unlock the requested/default behavior is canonical Home, not re-opening an app over the unlocking transition.

---

## 5. PHASE C — TRUE LIVE-CONSOLE AND WIFI-SSH SESSION INDICATORS

### 5.1 Write the indicator truth table before changing implementation

Implement this exact visual contract unless the real console architecture reveals a necessary distinction; if so, document it and keep the same user-visible semantics.

| Live Console daemon | USB serial interactive session | USB network SSH interactive session | Wi-Fi SSH interactive session | Base live penguin | Serial/USB type icon | USB-network type icon | Wi-Fi type icon |
|---|---|---|---|---|---|---|---|
| stopped | no | no | no | off | off | off | off |
| running/ready in background | no | no | no | **on** | off | off | off |
| running | yes | no | no | on | **on** | off | off |
| running | no | not supported/not active | yes | on | off | off | **on** |
| running | no | yes, if genuinely supported in a future kernel | no | on | off | **on** | off |
| running | no | no | multiple Wi-Fi SSH sessions | on | off | off | **on** |
| running | no | no | last Wi-Fi session closes | **on** | off | off | **off** |

When service is running but no client is connected, show the base `nuxel-live-console-active.png` indicator (the service-ready/available state) and no transport-type icons. The specific transport icon shows only for an actual interactive session. When the last session of a transport closes, only that transport icon turns off; the base background-service icon remains while the service remains ready.

If the current UX artwork has a different active/inactive glow convention, keep the same semantics and test the pixels/classes.

### 5.2 Preserve transport readiness separately from active-session state

Do not break `tri_link_status.py::wifi_status()` or the Applications connectivity page by redefining `AVAILABLE` to mean “SSH client connected”. That function is correctly describing Wi-Fi SSH capability (IP, sshd listener, key-only policy, host key and authorized key readiness).

Instead, return separate fields, for example:

```json
{
  "wlan": {
    "available": true,
    "active": false,
    "sessions": 0,
    "source": "wifi-ready:no-interactive-session"
  }
}
```

Names may be adapted to the existing API style, but readiness and live activity must be distinct. Preserve compatibility with current consumers and version the shape if needed.

### 5.3 Track actual Wi-Fi interactive SSH sessions reliably

A correct WLAN console session must be proven, not guessed from Wi-Fi `operstate` or sshd LISTEN.

Investigate the current SSH server/PAM configuration and session lifecycle. Choose a robust, auditable approach. A preferred pattern is a root-owned PAM session open/close tracker or an equivalent trusted SSH session hook which writes per-session leases under a private `/run/nuxel/` directory. If using such a hook:

- record only non-secret facts: PID, process start ticks, login user, local IP, transport interface, whether a PTY/interactive terminal was allocated, start timestamp and a random session ID;
- derive `SSH_CONNECTION`/local endpoint and confirm the local IP belongs to the current Wi-Fi interface before labelling it WLAN;
- require the `nuxel` account or the explicit approved console account; do not count every administrative service account automatically;
- require an actual interactive PTY/terminal session for the console icon. Port forwards, SFTP-only transfers, ssh-keyscan probes, short one-shot `ssh true` health checks and sshd's listener must not light the console;
- remove the lease on PAM close/session teardown;
- clean up stale leases safely after crashes using PID existence **and** `/proc/<pid>/stat` start time, not PID alone;
- make the session tracker atomic, race-safe and private to root; no world-writable lease directory;
- never write private keys, authentication material, raw command history or sensitive environment variables into a state file or log;
- do not modify authorized_keys, loosen sshd policy or wrap the user's shell in a way that breaks login behavior;
- do not make a PAM syntax error capable of locking the user out of SSH. Stage and validate the PAM change, retain a tested rollback and keep an existing recovery channel.

Alternative implementation: correlate `/proc/net/tcp{,6}` established sockets with local Wi-Fi addresses, socket inode ownership, sshd child processes and PTY process trees. This can work, but it must correctly distinguish the local interface and actual interactive PTY. A global `ESTABLISHED` count is insufficient.

The existing `/proc/net/tcp` helper may be reused as an independent verification source, but it is not by itself a complete session-tracking model.

### 5.4 Keep USB serial detection intact and prove it

The USB serial path has a single-owner lock (`/run/nuxel-console.lock`), the `nuxel-console` process, a TTY such as `/dev/ttyGS0`, the live physical USB data-link proof and possibly a validated lease. Preserve those safeguards.

Do not read the DWC3 debugfs `link_state` node. The S10+ 4.14.253 driver can hard-lock the reading CPU after detach. The current `system_indicators.py` comments describe this historical hazard. Keep the safe Type-C role / UDC speed / wired-VBUS evidence path.

Do not accidentally change the known-broken USB NCM networking capability into AVAILABLE or active. USB CDC-ACM serial and USB network are different transports.

### 5.5 Frontend mapping and refresh

Modify `pwa/nuxel-home/js/lockscreen-indicators.js` so that:

- the base live penguin follows the background Live Console service-ready state (and/or any currently active transport that itself proves console availability);
- serial, USB-network and WLAN penguins follow their own active-session fields only;
- `wlan.available` never directly drives an active indicator;
- unknown/unavailable is rendered honestly and never optimistically turned on;
- the current `liveConsole || wlanConsole` expression does not double-count or leak transport-ready state into the base indicator;
- the indicator remains accurate when a session starts/closes while the lockscreen is visible.

Reduce the five-second blind stale window using event-driven state updates or a short bounded refresh (target approximately 1 second, not a busy poll). Consider a dedicated runtime state file updated by session hooks and watched by the bridge. If you shorten the existing safety timer, prove that the extra sysfs/proc reads do not harm battery or thermal behavior. Add request de-duplication and visibility-aware polling.

### 5.6 Required indicator regression matrix

Extend `services/nuxel-bridge/test-system-indicators.py` and the lockscreen JS/Python tests. At minimum cover:

1. Wi-Fi off, sshd off: availability false, WLAN active false.
2. Wi-Fi connected, sshd listening and all key-only prerequisites present, zero sessions: availability true, WLAN active false.
3. SSH `ssh-keyscan`/health-check/one-shot command only: WLAN active false.
4. One interactive SSH PTY session over Wi-Fi: WLAN active true, sessions=1.
5. Two interactive Wi-Fi SSH sessions: WLAN active true, sessions=2.
6. Close one of two sessions: WLAN remains active, sessions=1.
7. Close final session: WLAN active false, sessions=0 within the agreed refresh bound.
8. Stale lease for dead PID: ignored and removed.
9. Reused PID with different start ticks: rejected.
10. Session local address belongs to USB/loopback/other interface: not labelled WLAN.
11. Port-forward-only connection with no PTY: not labelled active console.
12. SFTP subsystem/no interactive terminal: not labelled active console unless the user explicitly defines SFTP as a console (default is no).
13. Daemon running in background and no sessions: base indicator on, three type icons off.
14. Daemon stopped and no sessions: all console icons off.
15. USB CDC-ACM connected session: base + serial icon on; WLAN off.
16. Physical USB detach: USB serial transport icon off, without a kernel lockup.
17. Existing charging/PC/Bluetooth/file-transfer combinations remain independent.
18. Read failure or malformed state: no false active session.

---

## 6. PHASE D — REMOVE THE PRELOADING VIDEO FINAL-FRAME HANG AND SPEED UP THE BOOT HANDOFF

### 6.1 Measure the exact boot sequence

Before changing the flow, add or use timestamps for these milestones:

- initramfs starts penguin boot animation;
- animation completes its minimum cycle and writes the ownership receipt;
- `nuxel-wl-fb` takes the single framebuffer owner role and first frame is scanning;
- Wayland/Phoc is ready;
- session script begins;
- PWA host starts and launcher document is ready;
- lockscreen DOM is constructed and visible in Home;
- preload mpv process starts;
- mpv first frame is genuinely presented;
- preload video reaches EOF;
- touch is armed/settled (separate milestone);
- preload overlay releases;
- real lockscreen is visible and usable.

Use monotonic timestamps and one `boot_id` to correlate records. Avoid wall-clock-only measurements before RTC/NTP is valid.

### 6.2 Consolidate the timing configuration

The currently observed config/script mismatch is real:

- JSON `early_wait_launcher_ms`: 4000;
- session script environment fallback: 6000;
- JSON `early_map_delay_ms`: 1200;
- session script environment fallback: 800.

The environment mapping in the controller means the shell fallback can override the JSON. Fix this so there is one default value for each setting. Environment overrides should only apply when explicitly supplied by an operator or deployment, not because the session script repeats a different hard-coded fallback.

Add a test that loads the config with no override and proves the effective values equal the JSON values. Add tests for explicit environment overrides and invalid values. Document the selected final defaults and why.

### 6.3 Split presentation readiness from input readiness

The current README/config describes readiness as including launcher readiness, boot OS, display bridge/frame receipts and touch status. The controller holds the last video frame until `readiness.ready`.

Create explicit readiness objects, for example:

- `presentation_ready`: real Home/lockscreen document exists and is displaying; framebuffer bridge owns the panel and has submitted valid frames; panel is on; receipt belongs to this boot; preloading overlay has a first frame.
- `input_ready`: touch subsystem is armed and reports a real `ARMED_OK`, or its explicit warning state (`NO_TOUCH_DEVICE`, etc.) is known.

The real lockscreen can safely be shown while touch readiness is degraded; it must remain locked and show a truthful warning/disabled interaction state. **Touch readiness must not be a reason to freeze the final video frame for many seconds when the actual lockscreen is already ready to be shown.**

Do not remove the lock requirement. A visible lockscreen is not an unlocked desktop. If no touch device exists, show the supported warning/recovery behavior and keep the phone locked.

### 6.4 Make the final-frame release fast but safe

Current behavior includes:

- `--keep-open=yes`;
- `max_display_ms=20000`;
- `hard_timeout_ms=25000`;
- the loop exits at video EOF only when the full readiness predicate becomes ready;
- otherwise the final frame may stay displayed until the hard timeout.

Change the state machine so:

1. The first actual video frame is presented before the PWA cover is released.
2. The animation clip plays once at its intended frame rate (no added sleep after EOF).
3. If `presentation_ready` becomes true before EOF, let the intended animation finish if it is nearly complete, then reveal the lockscreen immediately.
4. If EOF happens before `presentation_ready`, hold the final frame only for a short, explicitly bounded presentation grace (target roughly 1–2 seconds, tune from measured data), then release to the safe real lockscreen/fallback if the required visual surfaces exist.
5. Input/touch readiness continues in parallel and updates the lockscreen's warning/ready state, but does not hold the video frame once presentation is safe.
6. A hard total deadline remains as a final fail-open guard. It must be shorter and derived from the real boot timeline, not an unexplained 25-second wait.
7. If the real lockscreen surface is not yet present, do not reveal a blank display. Use the existing cover/fallback policy and keep all waits bounded.
8. If mpv stalls, fails, exits unexpectedly or loses the compositor, the overlay releases and the actual lockscreen/fallback remains. No service restart loop.
9. A late touch-ready event cannot re-show the video, hide the lockscreen, unlock the phone or start a second controller.
10. The final state/receipt records exactly why the overlay ended: `video-eof-and-presentation-ready`, `presentation-grace-expired`, `hard-timeout`, `display-off`, `mpv-failed`, etc.

### 6.5 Optimize the clip/player path without making MFC a boot dependency

The inspected player command explicitly forces `--hwdec=no` and `--vo=wlshm`. Do not silently change this to hardware decode or assume MFC is ready merely because a previous MFC prompt exists.

Use a staged optimization:

- benchmark current software decode and presentation on the actual S10+;
- inspect the clip's GOP, keyframe spacing, bitrate, profile, pixel format, fast-start metadata, audio track and actual render dimensions;
- produce an optional optimized boot variant if it materially lowers first-frame latency and decode CPU cost (for example a smaller panel-aspect-aware H.264/yuv420p profile, no audio track, sensible keyframe interval, fast-start MP4);
- preserve all visual elements and test for crop/letterbox distortion on the actual 1440×3040 panel in portrait and landscape;
- use the MFC hardware decoder only after its driver, firmware, V4L2 interface, GStreamer/mpv/FFmpeg path and fallback have been physically demonstrated on this kernel;
- keep software decode as an explicit fallback;
- consider a GPU Wayland output path only if it is compatible with the existing Wayland stack and does not add a new boot-time GL initialization delay;
- avoid four decoder threads competing with phoc/WebKit and other services if fewer threads improve the end-to-end boot timeline;
- do not play the AAC audio track. The existing `audio=never` policy is deliberate until boot audio output is independently verified.

The boot screen is short; reliability and first-frame latency matter more than maximum video fidelity. Keep the artwork looking good and never add a black-frame gap.

### 6.6 Preserve initramfs animation and framebuffer ownership

`configs/nuxel/boot/animation-handoff.json` and `tools/s10plus/a33/nuxel-anim-handoff.py` define receipt-driven boot animation ownership and a single `/dev/fb0` writer. Preserve the handoff state machine, minimum cycle policy, receipt, owner lock and fail-open behavior.

Do not modify `boot/initramfs/init.sh`, repack the initramfs or flash boot images as a quick fix. The current mission should be solved in the user-space session/preload controller and its packaging wherever possible.

### 6.7 Required preload tests

Extend:

- `tests/pwnage31000/test_preload_cinema.py`
- `tests/pwnage31000/test_preload_packaging.py`
- `tools/pwnage31000/verify-preload-cinema.py`
- any boot readiness/ownership contracts currently used by the image builder.

Test with fake mpv/IPC and fake receipts:

1. Config defaults are authoritative; shell does not override them implicitly.
2. Explicit environment overrides are honored and validated.
3. Launcher ready immediately, touch delayed: video ends and real lockscreen appears without waiting for touch.
4. Framebuffer ready late: first-frame cover remains until safe visual presentation.
5. Video EOF before presentation ready: final frame holds only for short bounded grace, then safe fallback if present.
6. Lockscreen not constructed: do not reveal blank/unlocked Home.
7. Touch unavailable: lockscreen appears with warning and remains locked.
8. mpv exits early, IPC unavailable, bad asset hash, decode error, display turns off and compositor disconnects: fail-open with an honest receipt.
9. Stale prior-boot receipt cannot pass a gate.
10. One-shot marker and single controller ownership still work.
11. Only `nuxel-wl-fb` owns framebuffer; no second writer appears.
12. No post-EOF or post-readiness fixed delay remains.

Physical validation: at least 10 cold boots and 10 warm reboots on the S10+. Record median and p95 for each milestone, video freeze/last-frame hold, total time to lockscreen and any blank-frame interval. Capture the screen at the handoff. Keep an owner-test table; do not report simulated timing as physical.

---

## 7. PHASE E — FIX THE BLACK-SCREEN WAIT DURING REBOOT

### 7.1 Diagnose before tuning

The current repository already carries the PWNAGE-37000 and PWNAGE-51000 stop-timeout changes. Recheck the **installed live unit properties**, not just source files:

```sh
systemctl cat nuxel-wayland.service
systemctl show nuxel-wayland.service -p TimeoutStopUSec -p KillMode -p ExecStop -p SendSIGKILL
systemctl cat nuxel-wl-fb.service
systemctl show nuxel-wl-fb.service -p TimeoutStopUSec -p KillMode -p ExecStop -p SendSIGKILL
systemd-analyze time
systemd-analyze blame
systemd-analyze critical-chain
systemctl list-jobs
systemd-inhibit --list
```

For the previous boot, capture the actual shutdown and current boot journal with monotonic timestamps where available. Identify:

- exact time when reboot job begins;
- last visible UI frame / display-off time;
- each service stop start/end and any timeout;
- whether `nuxel-wayland`, `nuxel-wl-fb`, audio, bridge, SSH, NetworkManager or another unit is blocking;
- remaining processes/cgroups after their parent unit stops;
- D-state kernel tasks and whether any device driver is waiting uninterruptibly;
- filesystem sync/unmount and `systemd-shutdown` time;
- actual kernel restart transition.

Distinguish a true slow reboot from a fast reboot preceded by a long black screen. They are separate defects.

### 7.2 Audit the existing bounded-stop logic

The current `40-bounded-stop.conf` for Wayland runs a shell `ExecStop` that signals the unit main PID, polls for a short interval and KILLs wrapper children. Verify that:

- the wrapper's actual child/descendant process tree is fully covered;
- the stop command does not wait on a descendant that cannot be killed;
- systemd is applying the final drop-in (not a stale earlier 8-second override);
- the `ExecStop` itself does not introduce a new timeout or race;
- `KillMode=control-group` does not leave a wrapper zombie or children outside the cgroup;
- no unrelated service has a 60/90-second default stop timeout and a dependency that is triggered by reboot;
- the `nuxel-preload-cinema` process and mpv child are cleaned up promptly and cannot hold the session shutdown open;
- background `nohup` processes do not escape the systemd cgroup or remain alive after the Wayland unit stops.

Do not blindly apply 3–5 second `TimeoutStopSec` to every service. Some services must flush metadata or close databases. Fix only measured blockers, with a correct cleanup path and a bounded timeout suited to that service.

### 7.3 Keep a useful display frame through shutdown if safe

If the existing shutdown order stops `nuxel-wl-fb` early and the panel goes black while systemd continues stopping other services, investigate whether the bridge can display a clear “Nuxel is restarting” / short penguin shutdown animation while it is still the sole framebuffer owner.

Possible design, only if supported by the actual bridge:

- the trusted reboot action writes a small reboot-intent receipt;
- while the current session/compositor is still valid, the existing `nuxel-wl-fb` owner presents a final restart screen or controlled animation;
- the display bridge remains the sole writer and exits cleanly at the normal late shutdown stage;
- systemd continues its normal orderly shutdown; no forced reboot is used.

Do not build a competing framebuffer writer or hold systemd's shutdown target waiting on an endless animation. If panel power is removed by the kernel before reboot, say so and keep the UI fallback simple.

### 7.4 Improve shutdown/reboot diagnostics

Add a small per-boot shutdown timing receipt using monotonic time. It should record when reboot was requested, when the reboot UI started, the last frame/display bridge state, and any unit-specific stop failure that can be safely recorded. Avoid relying on writes after filesystems have been unmounted.

Where useful, add `ExecStopPost` or a small systemd helper to record stop duration to `/run` and, while still writable, persist a compact summary under `/var/lib/nuxel/diagnostics/`. Ensure these hooks cannot delay shutdown themselves.

### 7.5 Reboot acceptance

- No forced reboot flags or SysRq shortcuts.
- All stop commands remain bounded and service-specific.
- USB/Wi-Fi SSH deployment/rollback recovery remains usable until the normal network teardown stage.
- A reboot requested through the Home UI acknowledges quickly and does not block GTK/WebKit.
- The display must not remain black for an avoidable service timeout after the frame is blanked.
- Report exact before/after durations, with source log evidence, and identify any remaining hardware/kernel delay explicitly.
- Run offline tests for policy, stop scripts and service graph before live reboot.
- For live tests, use the existing `tools/beta/reboot-policy.sh` and `tools/beta/live/nuxel-live-reboot-verify.py` flow. Preserve its preflight, reachability and rollback gates.

---

## 8. PHASE F — RELATED ISSUES TO AUDIT AND FIX ONLY WHEN DIRECTLY CONNECTED

Inspect these likely integration defects as part of the four main paths:

1. **Unsupervised `nohup` daemons:** navdock and preload controller are started from `nuxel-session.sh`. Confirm they cannot die silently or survive in a stale state. Prefer a single owner and clear bounded restart policy.
2. **FIFO readiness race:** a command can arrive before `/run/nuxel-navdock.cmd` exists. Add acknowledgements or a small retry/queue protocol; do not silently drop `nav-show`.
3. **Stale `/run` state:** clear/reinitialize navdock, bar, lock-enforcement, console-session and preload receipts at the correct per-boot/session boundary. Never use a previous boot's state as fresh proof.
4. **Foreground detection performance:** `nuxel-statusbar.c` currently calls the foreign-toplevel helper in a short polling loop. Reduce overhead while keeping responsive focus updates.
5. **Top-bar/dock orientation:** support all currently supported S10+ rotation modes from the active output geometry. No hardcoded single mode.
6. **Focus race on app launch:** native launch uses `nuxel-focus-app.sh` and returns without waiting for the surface. Ensure shell chrome state updates after the actual native toplevel becomes foreground, not only when the API call is accepted.
7. **Lock race:** a late app launch/focus callback must not override locked state or re-show the dock after lock.
8. **Status semantics:** the large live penguin, serial icon, USB icon and WLAN icon must each have one documented source of truth.
9. **Session close cleanup:** if a user kills a terminal abruptly, closes an SSH connection by losing Wi-Fi, suspends the phone or restarts sshd, stale session icons must clear after bounded stale-lease cleanup.
10. **Boot time config duplication:** environment defaults in shell scripts must not silently override JSON configuration with different values.
11. **Video lifecycle:** mpv child must be cleaned up on lock, session exit and shutdown; no child may hold systemd shutdown open.
12. **Logging:** avoid unbounded per-poll logs and log growth. Record state changes and periodic compact diagnostics, not every successful read.
13. **Fallback UX:** if native bar fails but Home is visible, the Home DOM bar still works. If native dock fails, expose an honest degraded state and provide the existing Home path; do not render duplicate DOM controls over a native dock that is present.
14. **Packaging parity:** fresh S10+ images and Wi-Fi SSH user-space deploys must install the same native binary versions, services, config and assets. A fix only present in a deploy script but absent from image build is incomplete.

Do not begin unrelated feature work (camera, sensors, MFC, HDMI, store, theme overhaul) under “fix any other issues”. Only fix issues that directly break the requested shell, lock, console indicator, boot or shutdown behavior.

---

## 9. AUTOMATED TESTS, BUILD GATES AND ACCEPTANCE

### 9.1 Existing test surfaces to preserve

At minimum run the relevant existing tests before and after changes:

- `tests/pwnage31000/test_preload_cinema.py`
- `tests/pwnage31000/test_preload_packaging.py`
- `tests/pwnage52000/test_lockscreen_privacy.py`
- `tests/pwnage52000/test_lpm_boot.py`
- `services/nuxel-bridge/test-system-indicators.py`
- `tools/s10plus/a45/test-lockscreen-indicators.py`
- `tools/s10plus/a45/test-lockscreen-indicators.js`
- `tools/s10plus/a45/test-lockscreen-layout.js`
- `tools/s10plus/a45/test-lockscreen-unlock.js`
- `tools/s10plus/a45/test-lockscreen-indicators.c`
- `tools/s10plus/a33/tests/run-boot-tests.sh`
- `tools/s10plus/a33/tests/test-service-graph.py`
- `tools/s10plus/a33/tests/test-boot-surface-contract.py`
- `tools/s10plus/a33/verify-service-graph.py`
- `tools/beta/tests/test-rollback-reboot.sh`
- `tools/beta/live/tests/test_live_reboot_verify.py`
- all directly related Nuxel Home JavaScript tests and bridge API tests.

Some paths may have moved; locate the canonical test files in the current repository and update the command list/report. Do not run stale backup files as canonical tests.

### 9.2 Add new PWNAGE-62000 regression suite

Create a well-organized test group such as `tests/pwnage62000/` (or follow the current test naming scheme) with fixtures/mocks for:

- layer-shell top bar/dock state and lifecycle;
- native app launch, focus and layer chrome readiness;
- lock request from Home and from a native app;
- already-running app while lock engages;
- app focus attempt while locked;
- unlock order and touch delivery;
- statusbar hidden on Home/lock, shown only for non-Home app;
- no duplicate Home DOM/native bars;
- Wi-Fi ready/no session false; active SSH PTY true; last session close false;
- per-session lease cleanup and PID reuse protection;
- service-running base live indicator with no transport type icon;
- delayed touch readiness versus preload presentation readiness;
- final-frame hold grace and total hard timeout;
- timing config precedence;
- mpv stop/child cleanup on shutdown;
- unit-specific stop-timeout installation and service graph.

Use fake Wayland/protocol peers where practical. Add a headless compositor integration test if the current VM/test harness supports it. Do not pretend a DOM-only test proves native Wayland layer ordering.

### 9.3 Static/build checks

- `sh -n` every changed shell script.
- Python `py_compile` every changed Python file.
- `node --check` every changed JavaScript file.
- Cross-compile each changed C binary for AArch64 against the shipping sysroot.
- Check linked libraries (`ldd` on target or equivalent ELF inspection); missing Cairo/Pango/Wayland libraries must be caught before image packaging.
- Run protocol scanner generation deterministically and confirm generated headers/objects are not stale.
- Run `git diff --check` and repository formatting/lint targets.
- Validate JSON configuration and systemd units (`systemd-analyze verify` where available).
- Run the current build/test gates for the relevant S10+ targets.

### 9.4 Device acceptance matrix

Record `PASS`, `FAIL`, `BLOCKED` or `NOT TESTED` for every line. A feature is not verified on the phone if it was only run in a VM.

| Test | Required result |
|---|---|
| Home idle | One Home DOM top bar, no native duplicate; correct nav behavior |
| Stremio foreground | Native top bar + three-button dock above actual Flatpak surface |
| GTK app foreground | Same native chrome above GTK toplevel |
| App dialog/popover | Dialog stays usable, chrome remains correct |
| Back | Returns/closes according to Nuxel semantics; no lost dock |
| Penguin Home | App backgrounds, Home raises, Home DOM top bar becomes visible, no duplicate |
| Tabs/Recents | Correct recents behavior over native app |
| Lock with Stremio foreground | Lockscreen appears above it, native chrome hidden |
| Lock with GTK foreground | Lockscreen appears above it, native chrome hidden |
| Attempted app activation while locked | App cannot cover or receive input above lockscreen |
| Unlock | Touch gesture works, lock removed only after auth, Home canonical, dock returns |
| Portrait/landscape | Bar and dock geometry/touch hitboxes remain correct |
| WLAN ready, no SSH terminal | Wi-Fi availability may be true; WLAN console icon false |
| First interactive WLAN SSH shell | WLAN icon becomes active promptly |
| Two WLAN shells, one closes | WLAN icon remains active |
| Last WLAN shell closes | WLAN icon disappears within target bound |
| SSH command / keyscan / port-forward only | No interactive console indicator |
| Live Console daemon idle | Base indicator on; all transport icons off |
| USB serial client connects | Base + correct serial transport icon on |
| USB physical detach | USB serial transport off promptly; no DWC3 debugfs read |
| Cold boot 1–10 | No long final-frame stall; lockscreen visible when presentation-ready |
| Touch delayed at boot | Lock UI shown with truthful input warning; no frozen video wait |
| Reboot 1–10 | No unexplained black-screen dwell; shutdown timings documented |

Capture at least:

- a screenshot/photo of Stremio with top bar and bottom dock visible;
- a screenshot/photo of a GTK app with both controls visible;
- a lockscreen screenshot while Stremio is running behind it;
- a lockscreen screenshot of base live penguin only with no transport icon;
- a lockscreen screenshot with an active Wi-Fi SSH console and WLAN penguin;
- a log/timeline showing the WLAN icon turns off after the last session closes;
- boot timeline showing final frame and lockscreen presentation timestamps;
- reboot timeline showing which units were stopped and total black-screen time.

---

## 10. DEPLOYMENT, ROLLBACK AND RELEASE HYGIENE

### 10.1 Safe deployment design

Follow the existing live deploy manifest/tooling and the proven Wi-Fi SSH deploy path. Do not invent a new deployment mechanism if a current one already stages, hashes, atomically installs and rolls back files.

The deploy package must include only the necessary userspace components for this mission:

- native statusbar binary and any protocol dependencies;
- updated navdock/foreign-toplevel/lock enforcement code;
- required systemd/session units and drop-ins;
- updated PWA JS/CSS and service worker cache version;
- updated indicator backend and session tracking hook/config;
- updated preload controller/config/asset if changed;
- shutdown diagnostic helper/units if changed;
- tests, reports and rollback manifest.

No kernel, DTB, BOOT partition, modem firmware or recovery writes.

### 10.2 Backup and rollback

Before deploying, create a timestamped target-side backup under `/var/backups/nuxel/p62000-<timestamp>/` or the repository's established equivalent. Record the backup path in `/run/nuxel-p62000-backup-dir` and in the deployment receipt.

Rollback must be exact and self-contained:

- restore prior native binaries and service files;
- restore previous config and PAM/session tracking files if modified;
- restore previous PWA assets/cache manifests or trigger the correct cache invalidation;
- daemon-reload and restart only the relevant units in dependency-safe order;
- recover old shell behavior if new statusbar/dock fails;
- return previous preload behavior or disable only the new optimization while retaining the safe old lockscreen flow;
- remove new state files only after proving they are generated by PWNAGE-62000;
- never remove user data, app data, SSH keys, authorized_keys, known_hosts or unrelated settings.

PAM/sshd changes require an extra rollback verification before the current SSH session is allowed to close. Keep the existing authenticated Wi-Fi connection alive while testing a second independent connection.

### 10.3 Reboot authorization and recovery

Before any physical reboot:

- prove the current Wi-Fi SSH connection is healthy;
- prove the USB serial console/recovery path status and single-owner lock;
- run the repository's reboot pre-checklist and rollback status;
- ensure the exact rollback command is saved and readable from the host;
- ensure there is a known-good recovery route if SSH drops;
- use the existing `tools/beta/reboot-policy.sh` reason/diagnostic/execute/confirm flow and `nuxel-live-reboot-verify.py` rather than an ad-hoc reboot;
- issue no more than the approved test count, and stop after the first unexplained failure.

### 10.4 No false completion

The final report must mark each item accurately:

- `IMPLEMENTED` — source code changed;
- `OFFLINE_TESTED` — unit/integration tests pass;
- `BUILT_AARCH64` — native binaries build for the target;
- `PACKAGED` — fresh S10+ image/deploy package contains it;
- `DEPLOYED` — installed on the phone;
- `OWNER_TESTED` — physical test performed by the owner/agent with evidence;
- `VERIFIED_ON_S10PLUS` — all relevant physical acceptance criteria pass.

Do not upgrade a status based on intention or a successful compile.

---

## 11. REQUIRED DELIVERABLES

Complete all that are possible in the current repository/environment and clearly state any live-device blocker.

1. **Actual code changes** implementing the four main repair areas.
2. `PWNAGE-62000-REPORT.md` with:
   - root cause per defect;
   - files changed and why;
   - architecture/state diagrams;
   - before/after timings and indicator truth table;
   - tests run with exact commands and actual results;
   - AArch64 build results;
   - package/deploy parity status;
   - physical S10+ evidence and any not-tested blockers;
   - known residual limitations.
3. `PWNAGE-62000-DEPLOY.md` or the existing canonical deploy plan with exact safe deployment steps and rollback commands.
4. A clean PWNAGE-62000 patch manifest listing every source-to-target file mapping, checksum strategy, service reload/restart and health check.
5. Updated test suite and any test fixture documentation.
6. A concise operator-facing status guide for the four user-visible states: Home, native app foreground, lockscreen, live-console transport indicators.
7. An updated changelog/version/cache identifier only if the repository's release process expects it. Do not arbitrarily bump the release version or create a GitHub release.

---

## 12. FINAL REPORT FORMAT

The final response to the owner must contain:

### A. What was broken
Explain each confirmed root cause, especially:

- why top bar was absent (native bar exists in source but is explicitly not launched and is not in the current A45 build; verify live packaging);
- why the bottom dock was absent (the exact failing link in the runtime command/state sequence, not a guess);
- how already-running native apps could cover the Home DOM lockscreen;
- why Wi-Fi readiness incorrectly lit a live console indicator;
- why the preloading video held a final frame and which exact gate delayed release;
- what actual unit/device stage caused the reboot black screen.

### B. What changed
List the specific files, binary builds, service changes, state contracts and rollback.

### C. Performance/boot timings
Give before/after median and p95 measured values. Do not present estimates as results. If live hardware timing was unavailable, mark `NOT TESTED`.

### D. Test results
Give pass/fail counts and exact commands. Include native Wayland integration tests separately from DOM tests.

### E. Live phone status
Separate offline-tested, built, packaged, deployed and verified states.

### F. Deploy instructions
Provide the exact Wi-Fi SSH deploy command/agent command and rollback path. No guessed IP addresses or invented credentials.

### G. Remaining issues
List every blocker honestly.

---

## 13. DEFINITION OF DONE

This mission is only complete when:

- Stremio Flatpak and GTK apps display the Nuxel native top bar and Back/Penguin Home/Tabs dock over their actual Wayland windows while unlocked;
- Home displays only its own DOM top bar, with no duplicate native top bar;
- locking while any native app is open always moves the Home lockscreen to the visible foreground, blocks app focus/interaction above it, hides normal chrome and preserves working unlock touch;
- the base Live Console indicator means “service running/ready”, while serial/USB/WLAN penguins mean “an actual interactive session over this transport”; Wi-Fi availability alone never lights the WLAN icon;
- the WLAN icon appears when the first real interactive Wi-Fi SSH console session starts and disappears promptly after the last session ends, including abrupt disconnect and stale lease cases;
- the boot video no longer gets stuck on its final frame waiting for touch readiness, config defaults are not overridden by duplicate script defaults, and the real locked UI appears as soon as presentation readiness is true;
- reboot no longer contains an avoidable long black-screen service-stop wait, or the remaining delay is conclusively attributed to an unavoidable hardware/kernel phase with evidence and a safer visible shutdown state where possible;
- all single-framebuffer-owner, lock fail-closed, SSH security, rollback and release invariants remain intact;
- all automated tests pass and all physical tests are accurately reported.

**Execute the mission. Inspect first, implement second, prove third, deploy only when recovery is ready. Never substitute a report for the fixes.**

