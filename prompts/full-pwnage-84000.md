# FULL-PWNAGE-84000 — Operation Daily Penguin

## Complete source-led implementation specification for Nuxel

**Target system:** Nuxel mobile Linux on Samsung Galaxy S10+ (`SM-G975F`, codename `beyond2lte`, Exynos 9820)  
**Repository baseline:** `nuxel-main (12).zip`, supplied 2026-11-06  
**Expected development checkout:** `~/x/nuxel` (discover the actual working directory; do not assume blindly)  
**Primary device access:** Wi-Fi SSH to the phone's root account through Nuxel's existing Tri-Link helper  
**Private-key path supplied by the owner:** `~wicked/.ssh/wicked_wqn_id_rsa`  
**Short execution prompt:** `pwnage-84000.md`  
**Mission:** Complete, tested, persistent fixes—not cosmetic mock-ups.

---

# 0. Mission command

You are the senior systems engineer responsible for completing this Nuxel repair round. The supplied repository is a mature, functioning phone OS. Do not treat it as a generic web application, do not rewrite working subsystems for convenience, and do not “fix” issues by removing features, changing the device architecture, or disabling security.

Execute every workstream in this document. Start by auditing the checked-out tree and the actual S10+ over Wi-Fi SSH. Establish the real root cause of each symptom. Then implement coherent fixes across UI, service, bridge, persistence, packaging, systemd, theme settings and test coverage. Deploy only through a safe, backed-up procedure. Reboot only when necessary and only after the current state is recoverable. Finally verify the results with real touch interaction, actual sound, actual files, actual microphone recordings, actual package launches and actual scheduler events on the phone.

**There is no acceptable final state in which the UI merely looks correct while the underlying operation remains broken.**

## 0.1 Primary objectives

- Doom: two matched analog-style thumb joysticks, left movement and right aim/turn, reliable multitouch, working fire and preserved working sound.
- Clock: background/system-owned alarms and timers, screen-off alarm audio, visible persistent lockscreen penguins, alarm swipe actions, timer tap-stop, separate sound preferences, independent upcoming alarms and real snooze.
- Settings: no visible horizontal scrollbar in Settings; tab strip remains horizontally scrollable and easy to hit.
- Performance: measurable reduction in GTK and Flatpak app startup latency with no security regression or loss of graphical acceleration.
- Downloader: real `yt-dlp` backend, MP3/MP4 presets, browser cookie source selection, secure cookies, useful progress and completed output files.
- Notes: true on-disk notes in the session user's `~/Notes`, gallery preview, safe import/export, reliable save, and useful Calendar/Clock handoffs.
- Home desktop: widgets and application icons share one position/collision model, snap to grid, can be moved/resized/removed, and can be dragged across desktops while the user's finger continues holding the item.
- Calendar: actual Calendar widget, actual event actions, working alarm and notification reminder scheduling.
- Microphone: diagnose and repair capture quality, add honest mic volume controls and optional noise suppression.
- Appearance: Adwaita dark preference consistently applied to native GTK and Flatpak applications, including Software and Archive.
- Software keyboard: no accidental keyboard on app open; swipe-up reveals system triple buttons; swipe-down dismisses keyboard.
- Legcord and Vesktop: install and integrate correct ARM64 packages, launch them as the session user in Nuxel's Wayland environment, validate their login surfaces and leave authentication for the owner.

## 0.2 Security handling of account credentials

The request included a plaintext account password. **Do not copy it into this document, code, a shell command, a config file, environment variables, issue text, screenshots, logs, test data or evidence. Do not attempt to inject it into Legcord/Vesktop automatically.** The owner must enter credentials interactively in the official application UI. Do not ask for or capture MFA codes. If an application offers a native encrypted Secret Service / keyring integration, use it; never create plaintext credential storage. Avoid screenshots or logs that capture credentials or session tokens. If the owner explicitly wants the account tested, leave the app at its login screen, describe exactly what to tap, and verify the signed-in state only after the owner completes authentication.

The username is not needed in this implementation prompt. Never print or repeat the password.

## 0.3 Engineering posture

1. **Inspect live reality.** The ZIP is a point-in-time source snapshot; the live phone may already have later changes. Compare source, installed files, running services, installed packages and actual UI before deciding whether to port, replace or preserve a change.
2. **Trace ownership.** Every state has one authoritative owner. UI code renders and sends requests; a system or user service owns events, downloads, audio routing and persistence.
3. **Test before deployment.** Run source-level tests and static checks before touching the live root filesystem. Use narrow, atomic deployments with backups.
4. **Prove postconditions.** A command accepted, a toggle changed or a process started is not success. Verify the actual end result.
5. **Preserve existing behavior.** Do not regress the camera stack, MFC, normal playback, Wi-Fi SSH, bluetooth, orientation, launcher, Phoc, framebuffer ownership, Mali EGL or Flatpak sandbox.
6. **Do not silently reduce requirements.** If a capability is hardware-blocked, document exact evidence and implement the strongest safe fallback. Do not label an unavailable capability as working.

---

# 1. Repository and live-phone reconnaissance

## 1.1 Confirm the source tree

Locate the active Nuxel checkout (usually `~/x/nuxel`) and confirm it contains the repository represented by the supplied ZIP. Record:

```bash
pwd
git status --short --branch
git log -1 --oneline
git rev-parse HEAD
find . -maxdepth 2 -type f | sort | head -300
```

Do not overwrite user changes. If the checkout contains uncommitted changes, capture the diff and preserve them. Create a dedicated work branch or clearly separated commit series if repository policy allows. Before edits, record hashes for all files to be touched and make a dated backup of any live config that might be replaced.

Inspect the real `Makefile`, test runner, package build process, rootfs assembly, deployment tools, app registry, bridge protocol, systemd unit install rules and release workflow. Discover actual test targets instead of assuming names from earlier work.

## 1.2 Mandatory Wi-Fi SSH root access

The owner explicitly requires Wi-Fi SSH and the existing key. Use Nuxel's helper, not a guessed raw IP and not a different transport.

```bash
cd ~/x/nuxel
KEY=~wicked/.ssh/wicked_wqn_id_rsa
test -r "$KEY"
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --status --user root --key "$KEY"
```

The helper delegates to `tools/beta/live/nuxel-live-ssh.py`, whose interface supports `--transport wlan`, `--status`/`--discover`, `--host`, `--user`, `--key` and `--shell`. It uses the repository's Tri-Link host-key handling. Discover the configured/reported WLAN host. Do not guess the phone address. If discovery does not have a target, inspect the helper's existing configuration (`~/.config/nuxel/live-ssh.json`, environment and repo docs) and use the known Wi-Fi route. Do not switch silently to USB or serial.

Once the exact reported host is known:

```bash
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_WLAN_HOST" \
  --user root --key "$KEY" --shell
```

Confirm on the remote console:

```bash
id
id -u
uname -a
cat /etc/os-release
printf 'HOME=%s\n' "$HOME"
ps -eo pid,comm,args --sort=pid | tail -100
systemctl --failed --no-pager
systemctl list-units --type=service --state=running --no-pager
```

Require `id -u` == `0`. Record:

- kernel build and boot ID;
- rootfs release/version and image ID;
- active user/session identity, UID, home, `XDG_RUNTIME_DIR`, user DBus address and Wayland socket;
- `phoc`, `nuxel-home`, `nuxel-bridge`, `nuxel-http-bridge`, PipeWire/WirePlumber and notification process state;
- relevant system/user systemd units;
- active Flatpak remotes, installed apps and architecture;
- active audio sinks and sources, `wpctl status`, `pw-cli ls Node`, ALSA cards/PCMs;
- installed GTK/libadwaita, WebKitGTK, Flatpak, yt-dlp, FFmpeg, Legcord/Vesktop packages and versions;
- actual desktop grid, orientation, display geometry, touch device and lockscreen state.

Use the repository helper's normal key checks. Do not set `StrictHostKeyChecking=no`, do not discard a pinned host key, do not echo key contents and do not copy a private key to the phone.

If SSH is unavailable, capture the exact error and keep working on offline repository tasks. State clearly that physical deployment was not possible. Never report physical validation without connecting to the physical device.

## 1.3 Build an evidence directory

Create a unique run path, for example:

`docs/pwnage-84000/evidence/<UTC timestamp>/`

Capture (redact account secrets, tokens, personal messages and browser cookies):

- source revision, worktree status and changed-file checksums;
- device build/kernel/boot ID and package list;
- `systemctl status` and `journalctl` for touched services;
- audio and ALSA inventory, `wpctl` state and mic route state;
- GTK settings (`gsettings get org.gnome.desktop.interface color-scheme`, `gtk-theme`, and Flatpak overrides);
- app launch timing files for selected native and Flatpak apps;
- downloader version/feature check (not cookie material);
- current Notes persistence state, file listing and Calendar state (do not dump private note content into public evidence);
- current widget settings and launcher page assignment schema (no note body content);
- Doom control screenshots and audio state;
- lockscreen and alarm/timer behavior tests.

Keep private user data out of the repository. A metadata-only evidence report is sufficient; never commit recordings containing the owner's speech.

## 1.4 Repo findings that must inform this work

The supplied archive shows the following implementation facts. Verify each one against the active checkout and live phone before changing it:

### Clock

`pwa/nuxel-apps/clock/js/clock.js` currently owns alarm ticking in browser JavaScript:

- alarm configuration uses `nuxel-clock-alarms` and `nuxel-clock-settings` localStorage keys;
- `persistAlarms()` mirrors the list to bridge generic storage key/value storage;
- `hydrateAlarms()` reads the bridge copy;
- `checkAlarms()` is called only by the page's 250 ms `tick()` loop;
- timer completion is polled by a page `setInterval(..., 100)` loop;
- the file explicitly says alarms ring while Clock is open and says no RTC wake-alarm service is provisioned;
- snooze is hard-coded to 5 minutes and only stored in a JavaScript variable;
- the alarm MP3 is `assets/nuxel-alarm.mp3` and is played by an `Audio` object owned by the page.

This page-owned architecture cannot reliably ring when Clock is closed or the WebView is not running. Preserve the Clock UI and migrate event ownership to a durable service.

### Lock screen

`pwa/nuxel-home/js/lockscreen-indicators.js` already has an independent lockscreen indicator controller that reads real system state through the host or `/api/v1/system/indicators`. Add alarm/timer status to that same truth-oriented model or to a separately scoped scheduler-status provider. Do not fake scheduler state into the unrelated power/USB/console fields.

### Doom

`pwa/nuxel-apps/doom/index.html` contains:

- `#joy-zone` / `#joy-base` / `#joy-knob` for the existing left movement joystick;
- `#look-zone` as the right look surface;
- a separate action cluster with Fire, Use, weapon +/- , Run and Menu.

`pwa/nuxel-apps/doom/js/doom.js` has pointer-ID ownership and separate look handling, and `docs/games/doom-touch-controls.md` documents the engine mapping. The current right look surface is horizontal drag-to-turn, not a second stick. Replace it with a real second virtual stick while retaining the working WASM engine and audio setup. Do not remove essential pause/menu functionality.

### Widgets and launcher

`pwa/nuxel-home/js/widgets.js` has schema version 2, persists widgets in `nuxel.widgets`, gives each widget a one-based `desktop` field, and filters rendering by `launcher.currentPage + 1`. Only the Notes widget type is registered. Its resize handler changes spans; its move handler only reorders widgets after a 350 ms hold. It cannot place a widget in grid coordinates alongside app icons, and it cannot transfer an active drag across desktops.

`pwa/nuxel-home/js/launcher.js` persists app page membership through `pageAssignments`, adapts to portrait/landscape grid columns and renders app shortcuts into the app list. Its app-icon interaction must be upgraded alongside widgets so that both share a unified occupancy model.

### Notes

`pwa/nuxel-apps/notes/js/notes.js` currently uses `nuxel-notes` localStorage as its local state and calls bridge generic storage `read`/`write`. `notes-io.js` adds search, pinning and import/export, but it states that notes stay in localStorage plus an optional bridge copy. That is not the requested filesystem contract. `services/nuxel-bridge/src/pwa_store.py` has safe atomic JSON writes, a session-user home-directory root for the Files app and generic application storage, but Notes does not yet own a real `~/Notes` directory with one durable file per note.

### Calendar

`pwa/nuxel-apps/calendar/js/calendar.js` persists event lists using `caldav.list` / `caldav.put` and localStorage fallback. The current event model includes a `reminder` value, but verify whether it is actually scheduled and delivered by an independent background service. Do not assume an event reminder works merely because the value is saved.

### Downloader

`pwa/nuxel-apps/downloader/js/downloader.js` already calls `download.status` and `download.start` through `NuxelBridge`. The source comments say the host performs the transfer, but the repository does not contain a clearly implemented yt-dlp provider in the inspected bridge modules. `download-queue.js` has a rights/consent gate and URL validation that must be preserved. Implement the missing real backend; do not remove safety checks.

### Microphone

The source tree already contains an S10+ capture setup:

- `configs/s10plus/pipewire/51-nuxel-s10-mic.conf` creates a static capture node named `alsa_input.hw_0_13` backed by `hw:0,13` at 48 kHz stereo;
- `services/nuxel-s10/bin/nuxel-mic-route.sh` routes the built-in microphone path through ABOX NSRC0/SIFM0/WDMA1, then CS47L93 LHPF1/ASRC1/ISRC1/AIF1TX1/TX2 and DMIC1;
- the service waits for the audio route to report Calliope MUB0 before configuring the capture crossbar.

This is a specific Samsung route, not a generic USB microphone. Diagnose the actual analog mic path, mute/gain controls, PipeWire source, permissions and capture PCM. Do not overwrite this route without capturing its state and validating the replacement.

### Themes

`pwa/nuxel-common/theme.js` currently implements the Nuxel custom theme palette in localStorage; `theme.css` supplies PWA tokens. `pwa/nuxel-apps/settings/theme-settings.js` only selects those custom themes and haptics. This is not the same as the OS GTK/libadwaita `color-scheme` and legacy GTK `gtk-theme` preferences. Integrate the two theme systems deliberately.

### Legcord and Vesktop

No `Legcord` or `Vesktop` source/config/desktop entry was found in the supplied archive. Treat both as new ARM64 native-app integrations. Do not assume an existing app ID, launcher record or package is already installed.

---

# 2. Cross-cutting architecture and service contracts

## 2.1 Keep web UI out of system scheduling

A PWA/WebView can be destroyed, suspended, reloaded or closed. It cannot be the authoritative owner for alarm/timer/calendar scheduling, wake requests or persistent background work. Move those responsibilities into a system-owned scheduler daemon that survives app closure and is started at boot. The PWA becomes a client.

The same principle applies to downloads: the bridge owns job creation, the user-scoped worker owns execution, and the UI displays the job's actual state. Notes persistence belongs to a native storage service. Desktop positions belong to a single model, not separate CSS overlays.

## 2.2 Design service APIs before UI changes

Document the API schema and version it. The bridge is a compatibility boundary; extend it narrowly with explicit operations. Validate all input on the service side. Every mutating call returns a structured result with:

- `success` boolean;
- stable object/job/event ID;
- state/revision;
- structured `error_code` and human-readable error on failure;
- authoritative postcondition (saved path / scheduled occurrence / process ID / completion status);
- no secret material.

Use bounded timeouts and asynchronous job IDs for long work. Never let the HTTP bridge block on a full media download or Flatpak transaction.

## 2.3 Systemd service ownership

For new services:

- use clear service names such as `nuxel-clockd.service` and a related scheduler interface, consistent with project naming;
- include a dedicated unprivileged runtime account or the active Nuxel session identity where access to PipeWire/user data is required;
- use `After=`/`Wants=` only for actual dependencies;
- provide `Restart=on-failure`, sane restart limits and `TimeoutStopSec`;
- use `StateDirectory=`, `RuntimeDirectory=` and `LogsDirectory=` only where their ownership model is correct;
- use `ProtectSystem=`, `ProtectHome=`, `NoNewPrivileges=`, `PrivateTmp=` and other hardening compatible with actual device/DBus/PipeWire access;
- do not give the scheduler broad filesystem or shell execution access;
- do not run GUI or browser apps as root;
- make service start/stop and DBus ownership idempotent.

A service being `active` is not proof that events fire. Prove event creation, persistence, trigger, audio start, dismissal, reschedule, reboot reload and lockscreen reflection.

## 2.4 User identity and profile access

The root bridge currently has a `PwaStore` that resolves the session user for file-manager operations. Reuse the proven session-user detection, but never use root's `$HOME` for Notes, cookies, user themes, user Flatpak data or GUI app state. Resolve the true session UID/GID/home from passwd and the active graphical session, not from an arbitrary environment variable inherited by a root service.

For commands requiring browser profiles, PipeWire or DBus session bus, spawn as the real session user with a minimal verified environment. Do not copy browser profiles or cookies to root.

---

# 3. Doom: two true virtual joysticks

## 3.1 Desired interaction

Doom must feel like a mobile FPS with two matched on-screen thumbsticks:

- **Left joystick:** move forward/back and strafe left/right.
- **Right joystick:** aim/turn with an analog-feeling response. Use the engine's genuine mouse/relative-motion path if the WebAssembly build exposes one; otherwise translate horizontal deflection into controlled turn key state/timing with ramping and a dead zone. Classic Doom does not support modern vertical pitch by default—do not fake vertical aiming. Decide and document a real useful vertical-axis action only if the engine input model supports one, otherwise keep the second stick visually two-dimensional while horizontal axis drives turn and vertical axis is intentionally neutral/configurable.
- Both sticks must have the same visual diameter, base size, knob size, stroke, opacity and hit target, and be vertically aligned along the same baseline.
- Each thumbstick must be circular, analog-style, and continuously responsive. Do not replace it with a four-button D-pad or four separate arrow buttons.
- Keep the Fire controls below the corresponding stick on both sides so either thumb can fire. The left and right Fire buttons should be equivalent actions and should hold fire only while pressed. If the active viewport cannot fit both without overlapping critical HUD controls, redesign the layout responsively rather than deleting either fire action.
- Keep Pause/Menu and essential gameplay actions accessible. Do not reintroduce the obsolete auxiliary buttons that were explicitly removed in the preceding Doom work. Retain only essential Use/weapon/menu actions that the actual engine/UI still requires, with clean placement outside the stick surfaces.
- Preserve DOOM sound: the owner reports audio now works. Treat sound as a known-good subsystem and do not modify mixer routing, mute flags, WebAudio context ownership or engine audio build flags unless a regression is proven and fixed in the same change.

## 3.2 Audit before coding

Inspect:

- `pwa/nuxel-apps/doom/index.html` controls section;
- `pwa/nuxel-apps/doom/js/doom.js` input adapter, `keyDown`, `keyUp`, `tapKey`, `releaseAllInput`, engine `Module` setup and settings;
- `pwa/nuxel-apps/doom/css/doom.css` stick and action layout;
- `docs/games/doom-touch-controls.md` and existing tests;
- the actual `websockets-doom.wasm` build's available keyboard, mouse, pointer and relative-motion entry points.

Check whether SDL/Chocolate Doom exports browser pointer events or a mouse-motion callback. If true mouse-look is supported, route the right stick's relative movement into that real path. If not, implement calibrated smooth turning by mapping stick X to left/right key hold and turn pulses. Avoid creating a high-frequency timer per animation frame if an animation-frame loop or bounded single timer suffices.

## 3.3 Multitouch state machine

Use independent pointer capture and state for:

- left stick;
- right stick;
- left fire;
- right fire;
- Use / action buttons;
- pause/menu.

The two stick pointer IDs must never steal or cancel one another. A thumb may move and aim while the other fires. The browser must not interpret stick drags as page scroll, text selection, double-tap zoom or a system gesture; scope `touch-action: none` to the actual game HUD only. Do not globally disable touch behavior for the whole OS.

For each stick:

1. `pointerdown`: accept only a valid primary contact; calculate center/radius from the rendered base rect; capture its own pointer ID; immediately establish a neutral input state before applying displacement.
2. `pointermove`: only process the owning pointer; compute vector from center; clamp magnitude to the physical radius; update knob translation; normalize axes; apply a configurable dead zone and smooth response curve; send engine changes only when state changes or the motion adapter needs a new value.
3. `pointerup`, `pointercancel`, `lostpointercapture`, window blur, page hide, visibility loss, pause, Home and exit: release every engine key/button owned by that pointer and return the knob to center.
4. Reset stale pointers if a pointer ID is reused or the app is reloaded.
5. Keep `releaseAllInput()` as the single safety escape and extend it so both sticks and both fire buttons are fully released.

The two Fire controls must use reference counting or source ownership: releasing the left fire finger must not release Fire while the right finger still holds it. Similarly, left/right directional axes must not issue contradictory duplicate key-up events.

## 3.4 Responsiveness and settings

- Retain saved Doom settings and migrate schema without resetting user choices.
- Add left movement sensitivity and right turn/aim sensitivity if needed; provide a tested default.
- Offer dead-zone configuration only if the device touch panel requires it; default around 0.12–0.18, then calibrate on the physical device.
- Normalize diagonal input; do not allow diagonal movement to exceed cardinal maximum unintentionally.
- Keep the knob within the stick base and return it smoothly to center without delayed engine release.
- Support portrait and landscape if the game currently permits both; use safe-area insets and runtime viewport dimensions.
- Do not reduce the game view more than necessary. Both sticks must remain visible without covering the central play area.

## 3.5 Doom tests

Add tests for:

- both sticks exist and match size/alignment;
- no four-direction button cluster substitutes for the sticks;
- separate pointer IDs allow simultaneous movement and aim;
- movement + aim + left-fire + right-fire works;
- release of one of two Fire contacts leaves Fire down until the remaining contact releases;
- `pointercancel` and app exit release every key;
- knob clamps at max radius and respects dead zone;
- right stick maps into actual supported engine input;
- no scroll/zoom is triggered during stick use;
- menu/pause/back and orientation restore continue to work;
- audio still plays on the real phone after control edits.

Physically test with both thumbs. Capture a screenshot and a short non-sensitive video or interaction trace. Verify audio through the actual S10+ speaker/earphones with a known in-game sound.

---

# 4. Clock: background alarms, timer, lockscreen penguins

## 4.1 Replace the page-owned scheduler

Current `clock.js` has browser-only alarm and timer loops. Replace this with a durable scheduler daemon and service API. The web page must no longer be the only process responsible for triggering alarms/timers.

Implement a single authoritative scheduler model with distinct types:

- `alarm`: one-shot or recurring wall-clock schedule;
- `timer`: countdown with a durable absolute end time and explicit running/paused/stopped/completed state;
- `calendar_reminder`: reminder derived from a Calendar event, with one or more offsets before the event.

Each object needs a stable ID, schema version, created/updated timestamps, timezone semantics, enabled state and a revision. Store the source schedule separately from a specific fired occurrence. This prevents snoozing or dismissing one occurrence from deleting or mutating all future recurrences.

The scheduler should persist its state atomically. Use the existing Nuxel app-data convention or a dedicated scheduler state directory with correct ownership and permissions. Keep a migration path from `nuxel-clock-alarms`, `nuxel-clock-settings`, any localStorage timer state and bridge key/value copies. Never discard existing alarms during migration.

## 4.2 Service API

Define and test explicit operations such as:

- `clock.status` — service readiness, next alarm/timer/reminder, audio route readiness, wake capability and state revision;
- `clock.list-alarms`, `clock.create-alarm`, `clock.update-alarm`, `clock.delete-alarm`, `clock.enable-alarm`;
- `clock.start-timer`, `clock.pause-timer`, `clock.resume-timer`, `clock.reset-timer`, `clock.stop-timer`;
- `clock.dismiss-occurrence`, `clock.snooze-occurrence`;
- `clock.get-settings`, `clock.set-settings`;
- `clock.set-sound` or shared audio-settings methods.

Responses must contain an authoritative state snapshot. A successful API write is not a guarantee that an event is currently scheduled; report scheduler state and next deadline after a successful operation. Use structured errors for permission denied, invalid time, no audio device, unsupported wake source or storage failure.

Use a D-Bus service or the existing Nuxel bridge RPC architecture in the style consistent with the installed OS. If REST compatibility routes are added, bind only to the established loopback interface and validate protocol/session tokens exactly as the current bridge requires. Do not expose an unauthenticated scheduler API on LAN/Wi-Fi.

## 4.3 Alarm semantics

- Store each alarm's local wall-clock time, timezone ID where available, repeat pattern, enabled state, label, sound selection, vibration preference and optional per-alarm snooze override.
- Support one-time and recurring daily/weekday/custom weekday recurrence if the existing UI supports it. Keep the current user-visible daily/once behavior intact.
- Use the system's real local timezone and handle daylight-saving transitions. A recurring 07:00 alarm means 07:00 local time after DST change, not an unchanging UTC timestamp.
- On each trigger, create a unique occurrence key from alarm ID and scheduled local date/time plus timezone/offset or a stable event UUID. Persist `fired` before starting playback so restart/retry cannot duplicate the same occurrence.
- A one-time alarm becomes completed/disabled after its occurrence fires, but remains visible according to the app's history/retention policy. Stopping a ringing occurrence must not delete other alarms.
- Stopping a recurring alarm stops only that occurrence. The next scheduled recurrence remains active.
- If multiple alarms coincide, queue or concurrently represent their occurrences without one dismissal clearing the others. Do not allow one alarm sound stop action to silence an independent timer that is still ringing.
- Keep the Clock app's visible Start/Stop controls as well as lockscreen gestures. Every state transition must be accessible with keyboard/screen reader semantics.

## 4.4 Snooze policy

- Default snooze: **9 minutes**.
- Provide Settings controls for snooze duration (sane range 1–60 minutes; choose increment 1 or 5 minutes and validate it) and a global switch to disable snooze completely.
- If a per-alarm snooze duration exists, it overrides the global default only for that alarm; otherwise use the global duration.
- Snooze means create a new occurrence due at current time + configured minutes. It does not change the original recurring schedule.
- Persist the snoozed deadline immediately. It must survive Clock closure, UI reload, service restart and device reboot.
- When snooze time arrives, the alarm must ring again, animate, notify and offer the same actions.
- When snooze is globally disabled, hide/disable the left-swipe snooze action and any snooze button; swipe-right to dismiss remains available. Do not silently treat a snooze gesture as dismiss.
- Avoid infinite duplicate snooze records: one occurrence may have at most one active snooze deadline; snooze again replaces the current pending snooze for that same alarm occurrence and records an audit timestamp.

## 4.5 Alarm stop and timer stop UI

Clock app:

- Show a prominent **Stop** button whenever an alarm occurrence is ringing. It must stop only the active alarm occurrence; it must not disable or delete other alarms.
- Show a visible **Stop** button whenever the timer is complete/ringing; tapping it stops timer audio and marks that timer run acknowledged.
- Keep existing pause/reset functionality. A paused timer must not fire. Starting a new timer after completion must create a new timer run ID.
- If multiple alarm occurrences ring simultaneously, render a distinct row/control per occurrence or a single list whose Stop/Snooze actions target the selected occurrence explicitly.
- All stop/snooze operations call the scheduler; the UI does not merely pause its local Audio object and lie about service state.

## 4.6 Timer semantics

The current Clock page uses an in-memory object and a 100 ms polling interval. Replace it with a persisted service-owned countdown:

- persist `duration_ms`, `started_at_realtime` / `deadline_realtime`, wall-clock metadata, state, paused remaining time and `run_id`;
- use a monotonic clock for elapsed time while running, but reconcile after reboot/time changes using a documented wall-clock deadline and boot ID;
- make `Start`, `Pause`, `Resume`, `Reset`, `Stop/Acknowledge` idempotent;
- survive page close, WebView reload, app process exit and reboot;
- fire once per run ID; never repeat every daemon polling cycle;
- restore the running/paused/completed state in Clock UI after it opens;
- when it completes, play the independent timer sound, set lockscreen timer indicator and send a notification;
- a tap on the timer penguin dismisses only the timer indicator and stops only the timer alarm audio.

The timer's lockscreen action is a **single tap**, not a horizontal swipe. The timer penguin should animate/shake while ringing, then disappear only after the user taps it. Keep the timer alarm sound independent of alarm occurrences.

## 4.7 Lock screen indicators and gestures

Use the existing lockscreen indicator system in `pwa/nuxel-home/js/lockscreen-indicators.js` and the lockscreen DOM/CSS. Add two assets from the repository's `./assets/` directory:

- `assets/nuxel-alarm.png` for an alarm indicator;
- `assets/nuxel-timer.png` for a timer indicator.

**Inspect the actual tree and installed rootfs for both images.** The supplied archive definitely contains `assets/nuxel-alarm.mp3`; do not assume the two PNGs are present just because the owner says they were added in a newer workspace. If missing from the active checkout, search the actual assets paths and staged deployment. Do not invent a replacement or overwrite another asset. If absent, report the precise missing path and leave a clear asset placeholder reference for the owner to supply; continue implementing the indicator contract.

Persistent upcoming alarm indicator:

- If one or more enabled future alarms exist, show the alarm penguin on the lockscreen at all times, including while no alarm is currently ringing.
- When an alarm fires, the alarm penguin remains visible and begins a strong, clearly perceptible shake/bounce animation.
- If the occurrence is snoozed, keep the penguin visible with a snoozed state/countdown; it must ring again at the scheduled snooze deadline.
- If one occurrence is dismissed but future alarms remain, the persistent alarm penguin remains. Remove it only when there are no enabled future alarms and no active/ringing/snoozed alarm occurrence.
- When multiple alarms remain, the indicator reflects their aggregate status but the service must preserve each ID independently.

Ringing alarm gesture:

- Place the alarm penguin in its own clearly sized swipe lane, separate from the timer lane.
- **Swipe left:** snooze the currently ringing alarm occurrence for configured snooze duration, only when snooze is enabled.
- **Swipe right:** dismiss/stop only the current alarm occurrence.
- The swipe must start on the alarm indicator's hit area (or its dedicated lane), not a full-screen invisible overlay. It must not intercept unlock, PIN/password, quick settings, status bar, notifications, Home or other lockscreen controls.
- Use pointer capture, minimum horizontal movement threshold, direction dominance, velocity/length validation, and release/cancel cleanup. A tap without sufficient swipe distance does not accidentally stop the alarm.
- Visually show a direction hint that is understandable without covering the penguin or other lockscreen controls.

Timer indicator:

- Show the timer penguin only while a timer is running or has completed and is awaiting acknowledgement. Its placement is directly above or below the alarm penguin with enough separation to ensure alarm swipes cannot target the timer.
- When timer completes, shake the timer penguin strongly and play the timer sound.
- **One tap** on the timer penguin stops timer sound, acknowledges the timer completion and removes only the timer indicator. It must not dismiss any alarm or future timer.
- Ensure tapping the timer penguin cannot trigger alarm dismissal or snooze.

If alarm and timer are both active, both indicators must be visible and independently operable. Define a stacking layout responsive to portrait and landscape and device safe-area. Do not overlap either gesture region with the standard lockscreen unlock gesture.

## 4.8 Animation

Use CSS transform animations only on the penguin icon, not layout-affecting properties. Alarm/timer shake should be strong enough to notice but not jitter the whole lockscreen. Respect `prefers-reduced-motion` by reducing the animation without removing the visible ringing state. Stop the animation immediately after authoritative state changes. Avoid infinite JS timers; use CSS keyframes tied to state classes.

## 4.9 Screen-off audio and suspend/wake correctness

This is the most important Clock requirement. The alarm must sound when the device display is off and the Clock app is closed.

Separate the requirements:

1. **Display off, OS awake:** must work through a daemon independent of the WebView. Audio output must remain available when the display blanks.
2. **System suspended:** if the S10+ exposes a usable RTC wakealarm/wakeup source, use it to schedule the next alarm and verify actual resume. If not, investigate supported kernel wake-lock or suspend-inhibitor facilities and decide whether to block suspend while a near-future alarm is armed. Report the exact power trade-off.
3. **Cold boot/reboot:** restore pending alarms and due timers from durable state; do not duplicate an event already acknowledged.

Probe, do not assume:

```bash
cat /sys/class/rtc/rtc0/name 2>/dev/null
cat /sys/class/rtc/rtc0/wakealarm 2>/dev/null
cat /sys/power/state 2>/dev/null
cat /sys/power/wakeup_count 2>/dev/null
find /sys/class/wakeup -maxdepth 2 -type f -name name -o -name power 2>/dev/null
systemctl status systemd-logind --no-pager 2>/dev/null
```

Check all existing Nuxel power/suspend policies and device-specific kernel behavior before changing them. Never blindly write to `wakealarm`; the standard safe procedure is to clear an existing alarm only after proving the node and ownership model, then set the new absolute alarm and read it back. Handle `EINVAL`, permission denial and unsupported sysfs nodes explicitly.

Preferred behavior:

- `nuxel-clockd` computes the earliest relevant pending deadline and programs the actual RTC wake source if proven available;
- it listens for RTC / resume events and re-evaluates the queue;
- it owns a narrowly scoped suspend inhibit/wake lock while necessary if hardware wake cannot otherwise be used, with a documented battery impact and bounded lifetime;
- on wake or timer expiration it activates the audio route, plays the selected sound, updates the event status and notifies the lockscreen;
- it never keeps a permanent high-power wake lock when no event needs it.

If a wake lock or suspend inhibitor is the fallback, prove that the lock remains active only while an upcoming event needs it, releases on cancellation/dismissal, and does not prevent normal sleep forever. Make the fallback visible in Clock's capability diagnostics. Do not tell the user “wake from suspend works” unless a real screen-off suspend/resume test proves it.

## 4.10 Sound settings

Add separate sound selections:

- **Alarm sound**: independent file/selection, default to existing `assets/nuxel-alarm.mp3` if installed and playable;
- **Timer sound**: independent file/selection, own default, never silently reuse alarm selection if user changed it;
- volume can follow the existing notification/alarm output policy where appropriate, but independent alarm/timer selection must persist.

Provide preview buttons. Preview uses the same real audio service/route as the actual event, not a page-only `Audio` path that masks a broken service. A Stop preview action must stop only the preview instance. Keep volume bounded and preserve the user's global output level.

Settings should save selection atomically and expose current sound file, last-tested time and failure reason. Validate file type/size and canonical path under approved sound roots. Do not accept arbitrary root paths.

The asset `assets/nuxel-alarm.mp3` exists in the supplied archive. Detect it, verify playback through the S10+ audio output and retain it as an existing known-good default.

---

# 5. Settings horizontal scrollbar and tab navigation

## 5.1 Desired behavior

Remove the visible horizontal scrollbar on the Settings page. Keep the tab strip horizontally scrollable with touch, trackpad and mouse wheel/shift-wheel. Do not globally hide scrollbars or disable scrolling across every Nuxel app.

## 5.2 Implementation

Inspect `pwa/nuxel-apps/settings/index.html` and `settings/settings.css` (confirm exact path and stylesheets). Identify which element owns the horizontal overflow. Apply scoped styling to the Settings tab strip only:

- `overflow-x: auto` or the currently correct scroll container;
- `overflow-y: hidden` where appropriate;
- `scrollbar-width: none` for Firefox-compatible WebView engines;
- a scoped `::-webkit-scrollbar { display: none; height: 0; }` rule for WebKitGTK;
- preserve `-webkit-overflow-scrolling: touch` only if the installed WebKit version supports it and it improves touch behavior;
- preserve tab hit areas and horizontal swiping; do not disable pointer input.

If a scrollbar is generated by the page body rather than the tab row, find and correct the actual layout overflow instead of hiding it. Keep intentional horizontal content panes scrollable. Ensure active tabs automatically scroll into view without changing selected panel unexpectedly.

## 5.3 Tests

- No visible Settings horizontal scrollbar at 360×760 and 760×360 logical viewports.
- Tabs can still be moved horizontally by a thumb swipe and selected reliably.
- Fast swipe does not accidentally activate a tab.
- Vertical page scroll remains functional.
- No global scrollbar CSS regression in Files, Software, Calendar or other PWAs.

---

# 6. Native GTK and Flatpak startup performance

## 6.1 Do not tune blind

The owner reports native GTK and Flatpak apps still start very slowly. Do not add speculative preload services or disable sandboxing. Measure first-open and warm-open latency for a representative matrix:

- native GTK app: Settings or Archive/File Roller;
- Flatpak GTK app: Software/Archive equivalent if packaged Flatpak, plus another known-good simple Flatpak;
- Electron app: Vesktop/Legcord only after installed, tracked separately from GTK;
- PWA: Nuxel app launch for comparison.

Collect at least 5 launches per state where practical. Record:

- tap/activation timestamp;
- process spawn timestamp;
- first app window/frame timestamp;
- first interactive frame timestamp;
- time until first successful input;
- CPU time and RSS at 1, 3 and 10 seconds;
- process tree, dynamic library load and DBus/portal waits;
- cold-cache vs warm-cache result;
- whether the launcher, session DBus, PipeWire, portal or app itself was not ready.

Use available tools only if installed: `systemd-analyze`, `strace`, `perf`, `time`, `busctl`, `dbus-monitor`, `flatpak run -vv`, process accounting. Do not add a heavyweight tracing dependency to the phone merely for aesthetics. Avoid leaking private paths, tokens or personal data in traces.

## 6.2 Inspect actual launch path

Inspect:

- `services/nuxel-bridge/src/app_manager.py`;
- `services/nuxel-bridge/src/flatpak_provider.py`;
- `services/nuxel-bridge/src/software_provider.py`;
- PWA bridge launch methods and desktop entries;
- user/system D-Bus activation files;
- the actual session `XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`, `WAYLAND_DISPLAY`, `XDG_DATA_DIRS`, `XDG_CONFIG_HOME` and `HOME` values;
- installed GTK/GLib/Pango/Fontconfig/ld.so caches;
- Flatpak deployment refs, runtimes, portals and sandbox startup behavior.

The current Flatpak provider already spawns Flatpak work through a systemd-backed user context and exposes real lifecycle jobs. Preserve this separation. Do not run Flatpak GUI apps from the root HTTP bridge with an incomplete environment.

## 6.3 Diagnose common root causes

Test for:

- app manager performs a blocking app inventory or metadata refresh on every launch;
- launch call waits for status polling or unrelated hardware providers;
- service startup ordering serializes all unrelated services;
- app process starts under the wrong user and blocks waiting for a session bus;
- D-Bus activation is slow because no user bus is present or a service times out;
- XDG portal startup/permission dialog blocks the first window;
- Flatpak metadata refresh or remote discovery happens synchronously at app launch;
- icon lookup or theme scanning performs full filesystem traversal;
- fontconfig cache missing/invalid;
- GLib/GIO module or MIME cache absent/stale;
- dynamic linker cache stale;
- WebKit process launch is serialized or web process cache disabled;
- repeated cold sandbox creation due to an avoidable configuration issue;
- CPU governor/thermal or storage I/O bottleneck—but do not change governors or thermal controls without a proven bottleneck and an explicit user-visible rollback.

Check environment for the known dark-theme integration trap: a Flatpak override can contain an empty `GTK_THEME=` variable. An empty value is not the same as an unset variable and can disrupt GTK/libadwaita rendering. Inspect `flatpak override --show --user`, system overrides and actual `flatpak run --command=env <app-id>`. Remove only a proven bad empty override; never blindly reset all per-app overrides.

## 6.4 Improvements allowed

Implement only changes supported by measured evidence, such as:

- cache app registry and desktop metadata; refresh in background rather than on every launch;
- lazy-load nonessential app metadata after the first frame;
- reduce synchronous D-Bus calls from the launch critical path;
- improve session environment propagation;
- use DBus activation for services where it removes unnecessary waits;
- rebuild only genuinely missing or corrupted fontconfig/GIO/MIME/linker caches;
- remove duplicate startup waits and polling from app activation;
- avoid launching a second bridge/portal process for each app;
- correct system/user Flatpak runtime selection and architecture;
- fix an incorrectly inherited empty `GTK_THEME` or stale theme override;
- retain Flatpak's user namespace/bwrap isolation and permissions;
- keep the application visible and responsive as soon as the actual window exists, while showing honest loading status for ongoing app work.

Do not use `--no-sandbox`, broad filesystem grants, root GUI execution, `flatpak override --reset` as a blind first step, software rendering, disabling compositing or global `GTK_THEME` forcing as a shortcut.

## 6.5 Performance acceptance

Set explicit measured targets after baseline. Aim for materially faster first frame and no worse warm launch; target at least 25–30% reduction in the dominant measured wait where a fix is actionable. If hardware/CPU/IO sets a lower bound, report the actual bottleneck and measured improvement. Do not manufacture a numeric target result.

For each tested application, provide baseline median/p95 and after-change median/p95; launch success rate; first-frame latency; time to input; CPU/RSS. A performance fix must not regress appearance, sandbox status, audio, touch or notifications.

---

# 7. Downloader: real yt-dlp integration

## 7.1 Current architecture and required result

The existing Downloader is a PWA with `download-queue.js` and `downloader.js`. The UI already calls `NuxelBridge.call('download', 'status', {})` and `download.start`. Preserve its consent/rights notice, queue and URL policy, but implement an actual native backend. The UI must not pretend a transfer happened merely because a bridge request was accepted.

The desired UI lets the user:

1. paste a URL;
2. choose output type **MP3** or **MP4**;
3. choose cookie source **Chrome**, **Firefox** or **Nuxel**;
4. start download;
5. see actual progress and status;
6. find the completed file in the existing Downloads folder / Files app.

Persist the user's selected output type and cookie source. Default to a valid source that is actually available. Prefer Nuxel only after its cookie adapter has been implemented and proven; otherwise default to Chrome if detected, then Firefox if available, and clearly show the selected source. Never claim Nuxel is supported by yt-dlp's native `--cookies-from-browser` parser unless the actual installed yt-dlp version accepts that browser identifier.

## 7.2 Verify installed tools and official CLI behavior

On the live phone inspect:

```bash
command -v yt-dlp || true
yt-dlp --version 2>/dev/null || true
yt-dlp --help 2>/dev/null | grep -E -- '--cookies-from-browser|--progress-template|--newline|--audio-format|--merge-output-format|--remux-video' || true
command -v ffmpeg || true
command -v ffprobe || true
uname -m
```

The device is ARM64. Install a trustworthy ARM64-compatible yt-dlp and FFmpeg build through the project's package conventions. Prefer distro packaging when it is sufficiently current; if the Fedora package is too old for the required extractor behavior, use a pinned, checksum-verified upstream release or a documented self-update mechanism. Do not blindly run `pip install` into the system Python or replace `/usr/bin/python3` dependencies.

At time of writing, yt-dlp documents `--cookies-from-browser` for supported browsers and its preset aliases include `-t mp3` and `-t mp4`. Verify the installed version's `--help` and `--list-extractors` at implementation time rather than assuming every version accepts the same flags.

## 7.3 Correct MP3/MP4 presets

Use actual yt-dlp preset aliases only after checking the installed version:

- MP3: `-t mp3` (audio-only selection/extraction and MP3 conversion; requires compatible FFmpeg/ffprobe support).
- MP4: `-t mp4` (MP4-oriented merge/remux and selection behavior; it does not guarantee a compatible MP4 stream exists for every extractor). If unsupported in the installed version, use the equivalent documented explicit options and record the exact mapping.

Do not use `-x` alone and then name an arbitrary extension `.mp3`. Do not label WebM/Opus as MP3 or Matroska as MP4. If a remux/recode is necessary, distinguish remux from lossy re-encode and show a clear error when a requested format cannot be produced.

## 7.4 Cookie source selection

### Chrome and Firefox

Use yt-dlp's documented native options:

```text
yt-dlp --cookies-from-browser chrome <URL>
yt-dlp --cookies-from-browser firefox <URL>
```

The worker must run under the Nuxel session user with a valid user DBus/keyring environment when browser cookie decryption requires it. Do not run cookie extraction as root. Do not read a different user's profile. Do not print cookie contents or browser database rows into logs.

### Nuxel browser

Nuxel's native browser may use a WebKitGTK cookie database. `nuxel` is not automatically a valid yt-dlp browser key. Implement an explicit adapter only after identifying the actual browser profile directory, SQLite schema/version, session-cookie representation and any encryption/keyring dependencies.

The adapter must:

- read the real Nuxel WebKit cookie store read-only;
- select cookies according to the URL's host/scope and necessary path/domain/secure/expiry fields;
- convert to a temporary Netscape cookie file only when semantically valid;
- preserve HttpOnly and secure semantics where the supported format allows;
- create the file with mode `0600`, in a private per-job directory;
- never persist cookies into `~/Downloads`, repository, app logs or shared app data;
- pass that temporary file to yt-dlp with `--cookies <tempfile>`;
- unlink it on success, error, cancellation and service restart (with a safe cleanup sweep);
- report `Nuxel cookie source unavailable` if the browser profile is not real, not readable or the conversion cannot preserve the required session data.

Do not decrypt or extract secrets with custom code if the OS keyring API is unavailable. In that case provide Chrome/Firefox and a clear unsupported reason for Nuxel.

## 7.5 Native backend and security

Create an allowlisted `download` provider/service consistent with the bridge architecture. The job runner:

- validates the URL through the existing `DownloadQueue`/host policy and revalidates server-side;
- permits only HTTP(S) URLs allowed by current policy; reject `file:`, shell, data URI, local network/private address targets and dangerous redirects according to the project's current security contract;
- accepts only enum output types `mp3` / `mp4` and cookie sources `chrome` / `firefox` / `nuxel`;
- builds argv arrays; never concatenates a shell command or invokes `shell=True`;
- passes the URL as one argv element after flags; safely handles shell metacharacters in query strings;
- writes output only inside the session user's allowed `~/Downloads` directory;
- generates unique output names or applies a clear collision policy; never silently overwrites user files;
- stores job metadata under a private runtime/state directory with a UUID;
- returns a job ID immediately and exposes `download.job` / `download.status` polling or event updates;
- supports cancel by job ID and kills the child process group safely;
- enforces bounded concurrency appropriate for the S10+; default 1 active download is acceptable;
- preserves actual exit code, stderr tail and final file verification;
- parses yt-dlp progress from a stable machine-oriented progress template (not fragile localized text); throttles UI updates;
- marks a job completed only after process exit 0 and actual final file existence/size/type validation;
- reports post-processing errors accurately; a partially downloaded `.part` file is not a completed file;
- checks free storage and enforces reasonable maximum file/timeout limits;
- avoids recording full private URLs in public logs when they contain authentication tokens; redact query values known to be secrets.

Install and run the backend under the session user for profile and Downloads access. If a root bridge must broker jobs, use a narrow systemd-run or DBus method that explicitly drops privileges and only accepts the validated job description. Do not grant the PWA arbitrary process execution.

## 7.6 Progress UI

Represent distinct states:

- `queued`;
- `validating`;
- `extracting metadata`;
- `downloading` (bytes/percent/speed/ETA when reported);
- `post-processing`;
- `verifying output`;
- `completed`;
- `failed` (human-readable reason and safe stderr excerpt);
- `cancelled`.

The progress bar must track real `yt-dlp` output. Show output type, cookie source, URL host, file name, speed and estimated time only when values are valid. No made-up 0→100 progress. Offer cancel and open-in-Files actions after verifying the output path. Keep a completed job record so the UI does not revert to “pending” on reload.

## 7.7 Tests

Use local/mock HTTP test servers for unit tests and a lawful public test media asset for physical end-to-end testing. Do not download copyrighted content as a test fixture. Verify:

- valid/invalid URL behavior;
- shell metacharacter safety;
- MP3 output is actually MP3 and playable;
- MP4 output is actually MP4 and playable;
- cookie source option selected and passed correctly;
- unavailable Nuxel adapter fails clearly;
- cookie temporary file permissions and cleanup;
- process cancel, timeout, failure and disk-full behavior;
- no success status until file is on disk;
- downloader app can reload and recover job statuses.

---

# 8. Notes: durable `~/Notes` files and Calendar/Clock integration

## 8.1 The actual requirement

Notes must be saved to the phone's session user's home directory:

`~/Notes/`

This is a real directory and real files visible in Files and accessible after reboot, not only localStorage or a root-owned JSON file under `/var/lib/nuxel`.

Retain the current Notes UI, search, pinning, autosave, Markdown/JSON import/export and Notes widget compatibility. Fix data ownership rather than throwing away functionality.

## 8.2 Storage format and migration

Choose a robust per-note file format. Recommended:

- one `.md` file per note with a small metadata front-matter block or sidecar JSON containing stable ID, title, created/updated timestamps, pinned state and schema version;
- body in Markdown/text;
- deterministic safe filename using a slug plus stable ID (not just title; titles can collide and change);
- atomic write using temp file + fsync + `os.replace`;
- safe path validation; reject traversal/symlink escape;
- ownership `session_uid:session_gid`, directory mode private to the user (typically `0700`) and files `0600` unless existing Nuxel policy demands otherwise.

Implement service-owned `notes.list`, `notes.get`, `notes.save`, `notes.delete` (or the project's equivalent explicit API). Do not make the PWA guess filesystem paths or open arbitrary paths through a privileged root bridge. The service maps note IDs to files under the exact session user's `~/Notes`, never outside it.

Migration:

1. Read the existing bridge key `nuxel-notes` and localStorage `nuxel-notes` snapshots.
2. Merge by stable note ID, with deterministic conflict handling based on updatedAt and a user-safe conflict copy where both versions differ.
3. Never overwrite a newer filesystem note with stale localStorage.
4. Write all migrated notes atomically and verify count/hash/IDs.
5. Keep localStorage as a transient cache/offline queue only, not the authoritative save location.
6. Preserve legacy data for rollback until successful verification; do not delete source copies during migration.

If user data exists in both browser stores, produce a migration report with counts and conflict IDs only—do not dump note bodies.

## 8.3 Save behavior

- Keep debounced autosave, but always show `Saving…`, `Saved`, `Saved locally/offline`, or a clear failure.
- The UI may say `Saved` only after the Notes backend confirms atomic write and returns the final note ID/revision.
- Save button must remain useful and explicit. Closing an editor with dirty content must save or ask the user; never silently discard it.
- Use a serial write queue or revision numbers to prevent older async writes overwriting a newer note.
- If the service is offline, queue pending writes locally and retry safely; show the content remains locally cached but is not yet saved to `~/Notes`.
- Add `Open in Files` or folder action to navigate to `~/Notes`.
- Delete should require confirmation and remove only the selected note file; use trash/recovery if Nuxel's Files infrastructure supports a safe trash path.

## 8.4 Gallery-style UI

Implement a responsive gallery/list hybrid that works at 360×760 portrait and landscape:

- cards show title, a short sanitized preview, updated date/time, pin state and optional category/color;
- consistent card dimensions and a clean empty state;
- tap to open editor;
- accessible action menu for pin, delete, export, convert to event/alarm;
- search filters cards without unsafe HTML interpolation;
- sorting by pinned then recent update;
- preserve long note readability; no forced lossy preview truncation in saved body;
- avoid rendering note text with raw `innerHTML`; use text nodes or robust sanitization.

## 8.5 Note-to-event and note-to-alarm

Add contextual actions inside Notes:

- **Create Calendar event** — opens a prefilled Calendar event form with note title/body as initial title/description. The user chooses or confirms date/time and reminder.
- **Create alarm** — opens Clock's alarm creation form with a prefilled label; the user chooses/validates time and recurrence. Do not parse ambiguous note prose and silently schedule an alarm.
- **Attach to existing event** — optional if Calendar has a suitable stable event-ID association; preserve the note's ID as a reference.

On completion, show the actual Calendar event or alarm ID and status. If the destination service fails, keep the note unchanged and show the exact error.

---

# 9. Desktop widgets and app icons: unified movable grid

## 9.1 Root cause to address

The current `widgets.js` keeps widgets in a separate layer and gives each widget only `w` and `h` spans. It filters by a one-based desktop number. The launcher separately renders apps and stores app page membership in `pageAssignments`. This split model makes it impossible to guarantee that a half-screen widget leaves the correct cells available for icons, and it complicates drag/drop, page transfer, snapping and resizing.

Do not patch another overlay offset into CSS. Build one unified grid-layout model for **both widgets and app shortcuts**.

## 9.2 Unified persisted model

Introduce a versioned layout document with:

- `schema_version`;
- `desktop_count`;
- per-desktop grid definition (portrait/landscape effective columns and rows);
- entity records for app shortcuts, folders and widgets;
- stable entity ID and type;
- desktop index (use one canonical index convention—prefer zero-based in storage and convert at UI boundary only);
- grid position `x`, `y`;
- span `w`, `h`;
- z-order only where overlap is explicitly allowed (default: no overlap);
- optional widget-specific configuration (note ID, calendar view, etc.);
- migration metadata.

Persist one authoritative document, either through a dedicated backend or the existing Nuxel settings storage. Avoid having widget state in `nuxel.widgets`, app state in `pageAssignments` and rendered DOM order all competing. Provide a lossless schema migration from current `nuxel.widgets` v2 and current launcher `pageAssignments`.

The canonical layout model must preserve:

- all installed app shortcuts and their launch identity;
- current desktop assignments;
- all Notes widgets and their note selection;
- widget size where it is valid;
- grid order and user's existing app placement;
- configured number of desktops.

Do not silently discard user shortcuts or widgets during migration. If an old layout has more items than can fit, add a desktop or place them in the next free cell and report it.

## 9.3 Occupancy/collision engine

Implement a pure layout engine that computes occupied cells from `(x,y,w,h)` and current effective grid geometry.

Requirements:

- no app icon or widget may occupy the same cell unless the product deliberately supports a defined overlay;
- a widget spanning half the screen must leave remaining cells available for app icons;
- snap drag coordinates to grid cell centers/edges;
- fit spans inside grid limits after rotation and reflow;
- choose nearest valid location on collision; never place an item under another invisible item;
- preserve logical desktop ownership while the phone rotates;
- handle orientation-specific columns without writing a destructive migration for every rotate;
- when grid changes, deterministically reflow by preserving relative order and preferred coordinates where possible;
- use a stable algorithm with unit tests; do not rely on browser CSS Grid's implicit auto-placement as the source of truth.

Use DOM CSS Grid to render the already-computed model. CSS is a view, not the authority for placement.

## 9.4 Moving a widget

User must be able to long-press anywhere on a widget's non-interactive surface, then move it around:

- a short tap still opens/interacts with the widget;
- begin drag after an intentional long-press threshold (approximately 300–400 ms) and small movement slop;
- once active, create a visual ghost/placeholder and keep the pointer captured by a stable drag layer attached to the desktop shell, not by the widget element that will be re-rendered;
- moving over a new cell previews the proposed snap position;
- invalid collision positions are visibly rejected or nearest valid cell is previewed;
- release commits to the current desktop and saves once;
- cancel/blur/lostpointercapture reverts cleanly;
- do not fire the widget's normal tap action after a drag;
- provide a remove action through its control/context menu.

## 9.5 Resizing widgets

- Keep a dedicated resize handle with a clear hit target.
- Support drag to expand/contract width/height by grid cells.
- Preview new size while dragging; apply only a valid collision-free size.
- Never let resizing push an app shortcut off-grid without reflow.
- Save once on release; cancel restores previous size.
- Use same grid geometry as icons.
- Add accessible Resize larger / smaller actions for non-touch or assistive use.

## 9.6 Per-widget desktop ownership

Each widget must belong to exactly one desktop. The same note widget must not appear on all desktops just because Notes is updated or a shared storage event fires.

- `widget.desktop`/layout desktop field is the sole ownership authority.
- Rendering must filter by the active zero-based desktop, after one conversion point.
- On page switch, old widgets are removed/hidden and only widgets for the target desktop render.
- `nuxel:notes-updated` should refresh note content in widgets but must never clone or move a widget across desktops.
- Provide a widget config action to select Desktop 1/2/... and persist the choice.
- Switching a widget's desktop from its menu should move that one widget, leaving it invisible on all other desktops.

## 9.7 Edge-drag between desktops

Implement Android-style drag-to-another-desktop behavior for both widgets and app icons:

- during an active drag, moving the pointer within an edge activation strip (roughly 24–36 CSS px at the left/right screen edge) starts a dwell timer;
- after **1 second** continuously at that edge, switch to previous/next desktop;
- preserve the same drag entity, pointer ID, ghost, pointer capture and current finger position across the desktop transition;
- show an unobtrusive target-desktop preview;
- keep dragging as the new desktop content renders underneath the finger;
- allow the user to drop into a valid free cell on the new desktop;
- moving away before one second cancels edge dwell;
- enforce desktop bounds and do not wrap from last to first unless Nuxel already has an explicit wrap policy;
- if the destination is full, show no-placement feedback and allow returning to the previous desktop without losing the item;
- avoid accidental page switching on ordinary horizontal swipes or taps.

A drag ghost should live in a stable overlay/drag layer, not be destroyed by `renderPage()` when the page changes.

## 9.8 App-icon movement

The owner can add, resize and delete desktop icons but still cannot reliably move application icons. Fix the actual launcher input state machine:

- long-press an app icon to start drag;
- move it across the desktop grid;
- snap it to a free cell;
- avoid collision with widgets and folders;
- move across desktops using the same 1-second edge dwell mechanism;
- persist the app's desktop and coordinates;
- after release, tapping must still launch the correct app;
- dragging must not accidentally launch app or open context menu;
- locked-home mode must disable movement while still allowing launch;
- maintain dock items separately from desktop app icons; don't allow fixed dock items to become desktop entities accidentally.

## 9.9 Icon alignment repair

Fix intermittent desktop app-icon alignment:

- establish one consistent icon cell height and label region;
- use explicit icon boxes with fixed dimensions and `object-fit: contain`;
- reserve the icon and text height before image decode to prevent reflow;
- use consistent margins/gaps and baseline alignment;
- clamp multi-line labels consistently, preserving full accessible names;
- avoid mixing percentage positions, old absolute transforms and new grid placement;
- ensure touch target bounds align with visible icon bounds;
- handle missing/broken app icons with a stable placeholder that does not alter grid geometry;
- recalculate from `visualViewport` / actual logical viewport after orientation change and transition completion;
- do not use fractional transforms to compensate for a wrong grid model.

## 9.10 Removal and context UI

Widgets must be removable. Provide a visible remove control and long-press context menu with:

- Open / Configure;
- Move to Desktop…;
- Resize…;
- Remove widget.

Remove must delete exactly one widget instance, not the underlying note or calendar event. Confirm only where the widget contains user-created configuration that would otherwise be lost. The Notes content itself remains untouched.

## 9.11 Tests and physical validation

Pure tests for occupancy/collision, schema migration, reflow, desktop filtering, per-widget ownership, resize, remove, page-edge dwell and drag cancellation. DOM tests for no accidental click-through. Physical tests at portrait/landscape orientations, two desktops, with widgets occupying 1/2 and 2/3 of the grid. Verify icons can be dropped into remaining free cells. Verify Notes widget exists on Desktop 1 only, not Desktop 2. Drag a widget and an app icon across the edge; ensure the ghost remains under the finger and drop succeeds. Verify no icon jump/flicker after app launches, lock/unlock and Home return.

---

# 10. Calendar: widget, alarms and event notifications

## 10.1 Calendar widget

Register a `calendar` widget type in the unified widget system. It must be a real widget, not a screenshot or static date tile.

Recommended widget sizes:

- small: date/day plus next upcoming event;
- medium: compact week agenda or date strip plus 2–3 events;
- large: compact month calendar with event markers and upcoming agenda.

Make the widget configurable: choose compact/week/month view, show/hide agenda, choose the target desktop, and select a starting day/week convention consistent with Nuxel Calendar. Tap an event opens that event in Calendar. Tap a date opens Calendar on that date. Keep widget content refreshed by a Calendar event change signal without duplicating widget records.

Respect the device's local timezone and existing Calendar data model. Avoid rendering private event descriptions in the lockscreen or public notifications.

## 10.2 Event reminder model

Audit current `calendar.js` and its `reminder` field. Determine whether that field is merely persisted or actually scheduled. Add a real reminder model for timed events:

- event ID;
- reminder ID;
- offset before event (e.g. at event time, 5/10/15/30/60 minutes before, or a custom duration if already supported);
- notification channel/sound/vibration preference;
- enabled/dismissed state;
- last-fired occurrence key;
- timezone and event recurrence metadata if recurrence exists.

Use the scheduler service from Section 4. Do not create a second independent timer implementation in Calendar.

## 10.3 Quick actions

For every eligible event, provide simple actions:

- **Add alarm**: opens Clock prefilled with event title/time; user confirms recurrence/time. A Calendar event is not automatically a recurring alarm unless user explicitly asks.
- **Add notification**: enables a scheduled notification at selected offset(s). A reminder can be changed/removed later.
- **Open event**: open editor.
- **Mark reminder done/dismiss** where appropriate.

Event-to-alarm and event-to-notification handoffs must use stable IDs and service status. Deleting or moving the original event should update or cancel reminders consistently; do not leave orphaned reminders.

## 10.4 Trigger and notification behavior

- Notification service must handle missed events after reboot and decide whether to show a “missed reminder” notification based on a documented, bounded grace window.
- Never fire an old event reminder hours/days late as if it were on time.
- Deduplicate by reminder ID + event occurrence ID.
- Respect Do Not Disturb and notification settings, while preserving a separately configured alarm policy.
- Calendar reminder notification and Clock alarm are separate event types and separate sound assignments.

## 10.5 Tests

- Calendar widget shows only current desktop;
- widget updates after event create/edit/delete;
- event tap opens correct stable event ID;
- date tap deep-links to correct date;
- reminder is scheduled and survives Calendar close/reboot;
- reminder fires once at correct offset;
- timezone/DST changes are handled;
- event delete cancels its reminders;
- add-alarm shortcut creates a real Clock alarm only after confirmation;
- multiple events/reminders do not overwrite one another.

---

# 11. S10+ microphone: intelligible voice and controls

## 11.1 Current route to preserve until proven defective

The repo contains a specific built-in mic route for the S10+:

- PipeWire static source in `configs/s10plus/pipewire/51-nuxel-s10-mic.conf` named `alsa_input.hw_0_13`, `hw:0,13`, S16LE, 48 kHz, stereo;
- route helper `services/nuxel-s10/bin/nuxel-mic-route.sh` configures ABOX NSRC0/SIFM0/WDMA1 and CS47L93 capture controls;
- systemd `nuxel-mic-route.service` waits for the ABOX playback/firmware state before capture configuration.

The user hears only noise-like background, not voice. Possible causes include wrong physical mic, muted/incorrect DMIC or analog input, route to the wrong channel, bad gain, channel mapping, PipeWire source misselection, permissions or the wrong ALSA PCM. Diagnose systematically.

## 11.2 Evidence-first capture diagnostics

Collect:

```bash
cat /proc/asound/cards
arecord -l
arecord -L
amixer -c 0 controls
amixer -c 0 contents
wpctl status
pw-cli ls Node
pactl list sources short 2>/dev/null || true
cat /run/nuxel-mic-route.state 2>/dev/null
journalctl -u nuxel-mic-route.service -b --no-pager
```

Use the actual device indexes and controls from live output; do not assume card 0 if enumeration changed. Check `hw:0,13` and every plausible built-in mic PCM; compare their data. Capture short raw PCM test recordings at 48 kHz, 16-bit with explicitly selected source and channel count. Analyze peak, RMS, clipping, DC offset, channel asymmetry and voice-band energy. Do not store actual speech samples in the repository. Have the owner speak a known phrase at a close, normal phone distance while a separate test records; silence/noise tests alone cannot prove the mic works.

Compare:

- top/main microphone vs bottom mic if each is exposed;
- left/right channels individually;
- unprocessed ALSA direct capture vs PipeWire source;
- current mixer route vs a documented alternative only after saving mixer state;
- source selection in Recorder and any native app.

Listen to the test recording through the actual phone output or transfer it securely for inspection. A graph with signal energy is not proof that speech is intelligible.

## 11.3 Fix the actual signal path

Inspect kernel/device-tree exposed controls, ABOX route state, codec mixer path, microphone bias/switch settings and static PipeWire source. Confirm that `WDMA1` is the capture PCM and not the monitor/reference path. Verify each control's available enum/range before setting it. Read back after every change.

Do not run random `amixer set Capture 100%` commands or set playback volume as if it were mic gain. Use the actual source/input gain control, if hardware exposes one. Preserve the known working speaker path and don't restart/reconfigure ABOX during critical playback without checking dependencies.

If an existing vendor route is incomplete, reconstruct the needed path from the matching Samsung codec configuration and kernel driver source, not from unrelated devices.

## 11.4 Microphone volume UI

Add a Microphone section to Settings → Sound:

- selected capture source;
- real input volume/gain slider with current range and units;
- mute/unmute state;
- live peak/level meter based on current captured PCM or the PipeWire source monitor;
- Test microphone / Record short sample;
- optional noise suppression on/off.

Map the slider to real hardware capture gain when a valid ALSA control exists. If the only workable gain is software PipeWire volume, label it honestly as digital input gain. Never claim the hardware preamp was raised when only digital gain changed. Include clipping indication and preserve headroom.

Volume changes should persist in the user's settings and reapply after service/device restart. The UI must report failure for unsupported controls instead of showing a fake value.

## 11.5 Optional noise cancellation / suppression

Investigate an ARM64-compatible PipeWire/WebRTC/RNNoise filter path supported by the installed PipeWire version and Fedora packages. Choose the most maintainable supported module; do not vendor an unmaintained binary without provenance.

Noise suppression should be a real processing node between capture source and application consumers, with a toggle in Settings. When disabled, apps use the direct mic source. When enabled, apps use the processed source, with correct source priority/description. Keep a low-latency mode for calls and avoid aggressive gating that cuts off speech beginnings or quiet words.

Tests must compare recordings with suppression OFF and ON using the same voice/noise conditions. Report SNR/noise-floor change and confirm speech remains intelligible. If Nuxel's current PipeWire build cannot load a compatible suppression filter, do not simulate it; report the exact module/package/ABI blocker and keep the toggle disabled with an explanation.

## 11.6 Permissions and privacy

Ensure microphone access uses Nuxel's permission manager and current `configs/nuxel/privacy/microphone.json` policy. Mic level meters and recording tests must not start unless the user grants/has mic access. A persistent capture indicator should reflect actual active capture, not merely a source being available. On Stop, close the stream and return the mic indicator to idle.

---

# 12. Adwaita-dark across native GTK and Flatpak

## 12.1 Separate the two theme systems

Nuxel has a custom PWA theme (`NuxelTheme`, `nuxel-theme`, `theme.js`, `theme.css`) and a desktop GTK theme preference. Do not conflate them.

Implement a three-way OS appearance preference:

- **System** — follow the Nuxel/system color-scheme policy;
- **Light** — use `prefer-light` and the correct GTK3 light theme;
- **Dark** — use `prefer-dark` and the correct GTK3 dark theme (`Adwaita-dark` if actually installed).

Preserve Nuxel's accent/theme settings separately. Dark mode must not reset Nuxel's Grove accent or custom app layout.

## 12.2 GTK4/libadwaita

Modern GTK4/libadwaita apps generally follow the standard `org.gnome.desktop.interface color-scheme` preference, when the correct Settings portal/session integration is available.

Use the active session user's settings backend. Validate schemas and keys first:

```bash
gsettings list-schemas | grep -F org.gnome.desktop.interface
gsettings list-keys org.gnome.desktop.interface
gsettings get org.gnome.desktop.interface color-scheme
gsettings get org.gnome.desktop.interface gtk-theme
```

Apply the correct `color-scheme` preference (`prefer-dark`, `prefer-light` or `default`) through the user session. Do not run `gsettings` as root against root's dconf and then claim the user's apps changed.

## 12.3 GTK3

Legacy GTK3 apps commonly use `gtk-theme`. Select the installed dark theme name and verify it exists under `/usr/share/themes` or the active user's theme directory. Use `Adwaita-dark` only if installed and functional. If the distro's installed GTK3 theme package uses a different exact name, use the real name.

Do not globally force `GTK_THEME=Adwaita-dark` for every process. That environment override can produce incorrect behavior for GTK4/libadwaita and Flatpak. Let each toolkit follow its supported preference path.

## 12.4 Flatpak theming

- inspect user and system Flatpak overrides before changing them;
- inspect for an empty `GTK_THEME=` variable and remove that specific broken override if proven to be the cause;
- verify the Settings portal exposes the color-scheme preference to sandboxed apps;
- verify the correct GTK3 theme extension is installed for each actual runtime branch if a GTK3 app needs it;
- verify user theme access is provided by the Flatpak platform's supported theme-extension or filesystem integration;
- do not use blanket `--filesystem=host` or broad override changes;
- avoid blindly installing a GTK theme for every runtime version without checking installed branches.

The official Flatpak/GTK guidance and current GNOME discussions distinguish libadwaita's color-scheme preference from GTK3 theme settings. Use that distinction rather than forcing one global environment variable.

## 12.5 Required app verification

Test at minimum:

- Nuxel Software app;
- Archive/File Roller;
- one additional native GTK3 app;
- one GTK4/libadwaita native app if installed;
- one GTK3 Flatpak app;
- one GTK4/libadwaita Flatpak app.

Switch System → Dark → Light → Dark and restart each app. Verify dark surfaces, readable contrast, icons, dialogs, file pickers and popovers. Software and Archive must no longer stay white/light after the system dark setting is selected.

Add a theme diagnostic panel to Settings that reports the effective user `color-scheme`, GTK theme, portal response and known Flatpak override state without exposing private app data.

---

# 13. Software app: keyboard and triple-button gestures

## 13.1 Current failure

Software opens with the keyboard already visible, and the user cannot reliably dismiss it or reveal the Back/Home/Tabs triple buttons by swiping up. Diagnose the actual focus and gesture event path; do not just hide the keyboard with a timer.

## 13.2 Correct app startup focus

- Inspect Software app HTML/JS and any auto-focus attribute on search inputs.
- Do not autofocus the search field on launch unless the user explicitly invokes Search.
- Restore search text without automatically opening the keyboard.
- Only focus and show the keyboard after a deliberate tap on the search field.
- Preserve the cursor and typed text when a keyboard gesture is used.
- If a modal installs autofocus, ensure modal behavior is intentional and reversible.

## 13.3 Triple-button swipe up

Nuxel's system triple buttons are Back/Home/Tabs. Their bottom-edge reveal gesture must remain available while the keyboard is open.

- Determine the actual bottom-edge sensor/gesture recognizer and how the on-screen keyboard overlays it.
- Ensure the system gesture has a reserved edge region above or outside the keyboard's hit target; do not let the keyboard consume every pointer event.
- Swipe-up should reveal triple buttons with the exact existing visual and action contract.
- Back should first dismiss the keyboard if it is open; only a second Back should navigate/close the app according to Nuxel navigation policy.
- Home minimizes to desktop; Tabs opens Recents; none of these actions should insert characters into the search field.

## 13.4 Swipe down to dismiss keyboard

Provide a reliable downward swipe on the keyboard surface or a dedicated top handle to dismiss the keyboard. The recognizer must:

- begin only in a defined keyboard dismiss region or on the keyboard surface when not interacting with a key;
- distinguish vertical dismissal from horizontal keyboard gestures and normal scroll;
- release pointer/touch capture correctly;
- not dismiss when the user is selecting text or scrolling a result list;
- preserve typed text and current focus state;
- leave keyboard hidden until the user taps an input again.

## 13.5 Tests

Open Software from Home: keyboard must be hidden. Tap search: keyboard opens. Swipe up from bottom: triple buttons appear. Tap Back: keyboard closes before any app navigation. Open keyboard again; swipe down: keyboard closes. Search query remains. Install/search content does not shift the layout. Verify after orientation change and app relaunch.

---

# 14. Legcord and Vesktop: native ARM64 app integration

## 14.1 Current state

Neither app was found in the supplied ZIP. Add them cleanly through the existing Nuxel app installation/registry architecture; do not create ad-hoc binaries in the Home directory without app metadata or lifecycle handling.

Both clients are Electron-based Discord-compatible apps. The device is Fedora ARM64, so install native `aarch64` builds only. Current official release pages show ARM64 Linux artifacts for both projects; verify the latest version and exact asset names at execution time because releases can change.

Official references checked for this prompt:

- Vesktop install guide: https://vesktop.org/install/ and https://vesktop.dev/install/linux/
- Vesktop latest releases: https://github.com/Vencord/Vesktop/releases
- Legcord README: https://github.com/Legcord/Legcord
- Legcord releases: https://github.com/Legcord/Legcord/releases

At research time, Vesktop's current release page listed a Linux ARM64 AppImage and tarball; its official Linux guide also offers native RPM ARM64 and recommends native packages over Flatpak where possible because the Flatpak build has feature limitations. Legcord's current release page listed Linux ARM64 RPM/AppImage artifacts. These are observations, not hardcoded version pins: re-check official releases before installation.

## 14.2 Prefer correct native RPM artifacts

On Fedora ARM64, prefer the official RPM if current and dependency-compatible. If the project's current release does not publish an ARM64 RPM, use its official ARM64 AppImage or tarball and package it through Nuxel's native app integration. Do not use Flatpak as a reflex if native packages are available and work; compare tradeoffs.

For each downloaded artifact:

- verify architecture with `file`, `rpm -qp --qf '%{ARCH}\n'` or equivalent;
- verify official source, release tag and SHA-256 / signature / provenance metadata;
- verify package content and runtime dependencies;
- ensure Electron binary is AArch64;
- do not use x86_64 or x86 translation/emulation;
- do not run arbitrary install scripts downloaded from unofficial mirrors;
- record source URL, exact version, checksum and installed package ID in evidence.

Before installing, inspect disk space, RPM transaction plan, dependencies and conflicts. Preserve existing Discord-compatible clients and user data. Do not wipe config directories as a troubleshooting shortcut.

## 14.3 Desktop integration

Add correct desktop files/app registry entries and icons using the package's actual desktop ID, executable path and icon name. Integrate with Nuxel Software/NuXtore if project conventions support it. Ensure:

- launch runs as the Nuxel session user, not root;
- Wayland session variables and user DBus bus are correct;
- notification permission, notification daemon and sound integration are tested;
- microphone permission is routed through Nuxel's permission manager;
- camera permission (if supported and requested) is routed through Nuxel's permission manager;
- file picker and downloads open the correct user directories;
- window size and startup geometry fit portrait/landscape;
- maximize/minimize, Home, Tabs and Back semantics are sane;
- no stale launch process leaves a black/blank window;
- user data remains in the app's documented config directory;
- autostart is not enabled unless the owner requests it.

Inspect Wayland and Electron support flags for the exact installed versions. Do not add obsolete Electron flags blindly. Do not disable Chromium sandboxing with `--no-sandbox` as a quick fix. If hardware acceleration causes a reproducible issue, isolate it with a per-app reversible switch and keep a record; do not globally change Mali/Phoc/WLR configuration.

## 14.4 Runtime validation

For each app, validate separately:

1. launcher icon is present and correct;
2. app process starts as the correct user and correct ARM64 executable;
3. first window appears in Nuxel and receives touch input;
4. login view displays correctly;
5. owner can manually complete login; do not inject or store credentials;
6. after user authentication, app reload/relaunch preserves its session using the app's supported protected storage;
7. notifications are visible and obey DND;
8. microphone can be granted through Nuxel's permission manager and is intelligible;
9. audio playback works;
10. window can be hidden/restored and removed through Tabs/Recents;
11. Home/Back does not leave a stuck transparent overlay or ghost input grab;
12. no unbounded CPU/RAM usage while idle.

If a login request fails for Discord server/client-version checks, identify that exact issue rather than claiming the client works because its login form appeared. Do not bypass account restrictions, client checks or MFA.

---

# 15. Integration details and regression boundaries

## 15.1 Sound system

The owner reports Doom sound and Clock alarm/timer playback work now. Preserve this progress. Extend sound preferences to alarm/timer and microphone volume/noise suppression; do not replace the current working speaker route. Test before/after with `nuxel-pow.mp3` and a real Doom audio event. Separate sound ownership:

- app preview playback;
- timer sound;
- alarm sound;
- calendar notification sound;
- normal notification sound;
- game audio.

Stopping one class must not stop every PipeWire stream. Use stream IDs or tagged event IDs to stop the correct stream.

## 15.2 Nuxel permission manager

Downloader cookie access, mic input, Calendar/Clock background scheduling and app notifications must follow Nuxel permission policy. Reuse the permission manager and portal. Do not add broad permissions to every app. In particular:

- Recorder and Legcord/Vesktop need microphone only when user enables it;
- Downloader cookie source requires a clearly documented browser-session access capability/consent;
- Notes only accesses its own `~/Notes` data;
- Calendar/Clock background scheduling uses a Nuxel service capability, not unrestricted process execution;
- no app obtains unrestricted home directory access just to save one file.

## 15.3 Existing backend compatibility

Keep bridge protocol versions synchronized between the app manifests, host implementation, `pwa/nuxel-common/bridge-version.json` and installed runtime. Add tests for protocol mismatch and missing provider. Do not silently mock a successful Clock, Notes, Downloader or Calendar operation when the real provider is absent.

## 15.4 Performance and security preserve list

Do not:

- disable Flatpak user namespaces or bubblewrap isolation;
- setuid bwrap or make it privileged as a performance hack;
- open Nuxel HTTP bridge to LAN;
- run native GUI apps as root;
- disable SELinux or AppArmor;
- set global environment variables that break apps;
- change the framebuffer owner or start another `/dev/fb0` writer;
- change Mali rendering or Phoc backend flags without proof;
- alter kernel or boot partitions for pure UI/application fixes;
- remove user Notes, Calendar events, browser profiles or app configs;
- log passwords/cookies/tokens or commit private recordings;
- claim a feature is done based only on static code or unit tests.

---

# 16. Implementation sequence

Work in this dependency order. Parallelize only workstreams that do not touch shared files or live system services at the same time.

## Phase A — audit, backup and measurement

- connect over Wi-Fi SSH as root using the specified key;
- capture live baseline and current working status;
- map touched files, APIs, services, test suites and package rules;
- baseline app launch latency;
- capture mic route status and short private test sample;
- capture existing Clock/Calendar/Notes state counts;
- capture Doom audio/control behavior;
- capture widget/app icon layout and settings/theme state;
- produce evidence index.

**Gate A:** no user data loss risk; working services identified; all relevant tests known.

## Phase B — service contracts and persistence foundations

- implement Clock scheduler service/API with atomic state and migrations;
- extend Notes service to real `~/Notes` files, migration and API;
- implement Downloader backend job manager using yt-dlp;
- implement unified launcher layout model and migration engine;
- define Calendar reminder API on top of Clock scheduler;
- add service/API tests first.

**Gate B:** services pass unit/integration tests off-device; schemas and rollback paths documented.

## Phase C — Clock UI and lockscreen

- replace page-owned ticking with scheduler API;
- add Stop buttons, snooze setting and independent timer state;
- add alarm/timer assets and independent lockscreen render/gestures;
- integrate sound selection and audio service;
- test screen-off and suspend/wake behavior.

**Gate C:** two independent event types ring and can be independently dismissed; screen-off behavior proved; no recurrence data loss.

## Phase D — desktop layout and widgets

- migrate old widget and launcher placement into unified grid;
- add Notes and Calendar widget types;
- implement widget/app drag, resize, remove, edge dwell and orientation handling;
- verify per-desktop filtering and icon alignment.

**Gate D:** collision-free coexistence and working drag across desktops on hardware.

## Phase E — app and platform fixes

- Doom dual-joystick UI and input engine adapter;
- downloader UI and actual job/progress states;
- Software keyboard startup/gesture repair;
- GTK/Flatpak startup diagnosis and supported fixes;
- system dark theme integration;
- microphone source diagnosis, gain and suppression.

**Gate E:** each feature passes its own unit and device test without breaking existing audio/display/touch.

## Phase F — Legcord/Vesktop packaging

- verify current official ARM64 releases;
- install through Fedora-native packages where supported;
- add metadata/launcher integration;
- validate launch/input/audio/mic/notifications/Back/Home/Tabs;
- leave login to owner.

**Gate F:** both applications launch with correct architecture and render their official login surfaces; no false claim of authenticated operation.

## Phase G — full regression and release evidence

- run repo-wide required tests and all new tests;
- restart relevant services;
- perform one controlled phone reboot if needed;
- verify persisted state after reboot;
- run user-level and root-level service health checks;
- compare performance against baseline;
- record final git diff and checksums;
- prepare rollback scripts and a release-ready change summary.

**Gate G:** every pass/fail statement is backed by a test, log, screenshot or physical action.

---

# 17. Testing matrix and acceptance criteria

## 17.1 Doom

- [ ] Two circular analog-style joysticks rendered, same size and aligned.
- [ ] Left stick moves/strafe; right stick provides real engine aim/turn behavior.
- [ ] Not a four-button D-pad replacement.
- [ ] Fire available from both sides and supports simultaneous multitouch.
- [ ] Pointer cancel/blur/pause exits release all inputs.
- [ ] No page scrolling or unintended OS gesture during game control.
- [ ] Menu/Use/weapon action remain functional where required.
- [ ] Doom audio still works on real phone speaker and configured output.

## 17.2 Alarms and timer

- [ ] Alarm list and settings survive Clock close/reload/reboot.
- [ ] Alarm triggers with Clock closed.
- [ ] Alarm sounds while lockscreen visible and display off (awake path).
- [ ] Suspend/wake path is physically tested, or explicitly reports fallback and battery/power policy.
- [ ] Stop button stops current occurrence only.
- [ ] Other future alarms remain set and the lockscreen alarm penguin stays visible.
- [ ] Swipe left snoozes by configured minutes; default is 9 minutes.
- [ ] Snooze can be disabled; when disabled no snooze swipe/button is offered.
- [ ] Snoozed alarm rings again at correct time.
- [ ] Swipe right dismisses only the current occurrence.
- [ ] Timer survives Clock close and fires once per run.
- [ ] Timer penguin appears while running/completed according to defined state.
- [ ] Timer penguin shakes when complete; one tap stops timer sound and removes only timer indicator.
- [ ] Alarm/timer penguins appear in separate non-overlapping gesture lanes.
- [ ] Alarm and timer sound settings are independent and preview real output.
- [ ] Simultaneous alarm + timer events remain independently controllable.

## 17.3 Settings scrollbar

- [ ] Settings scrollbar visually hidden.
- [ ] Tab strip still horizontally scrolls and all tabs are reachable.
- [ ] Touch hit accuracy improved; page vertical scroll intact.
- [ ] No unintended global scrollbar regression.

## 17.4 GTK/Flatpak launch

- [ ] Baseline and post-fix launch timings measured for native and Flatpak apps.
- [ ] GTK native app first frame improves or bottleneck is truthfully isolated.
- [ ] Flatpak first frame improves or bottleneck is truthfully isolated.
- [ ] Security/sandbox status unchanged and healthy.
- [ ] Correct session user/DBus/Wayland environment.
- [ ] No software rendering or global unsafe override introduced.
- [ ] Theme still correct after launch optimization.

## 17.5 Downloader

- [ ] Paste URL triggers genuine yt-dlp job.
- [ ] MP3 option creates verified playable MP3.
- [ ] MP4 option creates verified playable MP4.
- [ ] Chrome, Firefox cookie options work where browser profiles exist.
- [ ] Nuxel cookie adapter works with a real profile or reports exact unsupported reason.
- [ ] Cookie files are mode 0600 and removed on completion/cancel/failure.
- [ ] Progress is real; job lifecycle survives UI reload.
- [ ] Cancel works; partial file is not called completed.
- [ ] File is present in correct `~/Downloads` and openable in Files.
- [ ] No shell injection, local-file read, arbitrary path write or DRM/access-control bypass.

## 17.6 Notes

- [ ] Notes folder exists at session user's `~/Notes`.
- [ ] Each saved note has a durable file on disk with correct permissions.
- [ ] Save status reflects real atomic write.
- [ ] Notes survive app close, WebView reload, service restart and reboot.
- [ ] Existing note IDs/content and pin state preserved by migration.
- [ ] Gallery/search/pin/import/export/delete work.
- [ ] Note-to-event creates correct Calendar draft/event after confirmation.
- [ ] Note-to-alarm opens Clock prefilled and only schedules after confirmation.

## 17.7 Desktop widgets and icons

- [ ] Unified grid is authoritative for apps and widgets.
- [ ] Widget and app icon can occupy separate cells in same desktop.
- [ ] A widget only exists on its selected desktop.
- [ ] Notes widget content refresh does not clone it across desktops.
- [ ] Calendar widget supports compact and larger layout and responds to events.
- [ ] Widgets can be moved by long-press and dropped on valid cell.
- [ ] Widgets can resize and remove.
- [ ] App icons can move and snap to grid.
- [ ] One-second edge dwell switches desktop with drag ghost still held.
- [ ] Full desktop rejects invalid placement without losing item.
- [ ] Icons remain aligned after rotation, app close, lock/unlock and Home return.

## 17.8 Calendar

- [ ] Calendar widget displays correct local date/event data.
- [ ] Event changes update widget.
- [ ] Event-to-alarm and event-to-notification shortcuts work.
- [ ] Reminders fire at expected offset.
- [ ] Delete/edit reschedules or cancels associated reminder correctly.
- [ ] No duplicate/late reminder after reboot.

## 17.9 Microphone

- [ ] Correct built-in mic path identified from actual PCM/codec route.
- [ ] Real voice is intelligible in a short recording.
- [ ] Left/right channels tested and mapping documented.
- [ ] Microphone level is measurable and not only background noise.
- [ ] Sound Settings shows real capture source and gain.
- [ ] Input gain can be raised safely without clipping.
- [ ] Noise suppression toggle selects a real filter or is honestly unavailable.
- [ ] Mic access follows permissions; active-capture indicator reflects real capture.

## 17.10 Dark theme

- [ ] System preference switches System/Dark/Light correctly.
- [ ] GTK4/libadwaita apps follow color-scheme.
- [ ] GTK3 apps follow actual gtk-theme.
- [ ] Flatpak portal/theme integration works with installed runtimes.
- [ ] Software and Archive are dark in Dark mode.
- [ ] Light and System modes still work.
- [ ] No empty GTK_THEME override remains where it broke dark preference.
- [ ] Nuxel PWA accent theme is not destroyed by OS theme selection.

## 17.11 Software keyboard

- [ ] Software opens with keyboard hidden.
- [ ] Search tap opens keyboard.
- [ ] Swipe up exposes Back/Home/Tabs while keyboard is open.
- [ ] Back closes keyboard before app navigation.
- [ ] Swipe down closes keyboard without deleting input.
- [ ] No accidental text entry, page navigation or drag on gesture.

## 17.12 Legcord and Vesktop

- [ ] Official ARM64 package versions and checksums recorded.
- [ ] Both run native AArch64 executables, not x86_64/emulation.
- [ ] Desktop/app-registry launch works as the Nuxel user.
- [ ] Login view is correct and touch-capable.
- [ ] Owner can manually sign in; no credentials are recorded or injected.
- [ ] Audio, mic permission, notifications and file picker work.
- [ ] Back/Home/Tabs and hide/restore behave correctly.
- [ ] No stuck overlay or high-CPU idle loop.

---

# 18. Deployment, rollback and data protection

## 18.1 Never overwrite blindly

Before each live deployment:

1. Copy the currently installed file/unit/config to a timestamped backup directory.
2. Verify backup hash and owner/mode.
3. Install new files to a staging path.
4. Run syntax/import/test checks against staged content.
5. Atomically install or switch symlink where appropriate.
6. Run `systemctl daemon-reload` only if unit files changed.
7. Restart only the affected service/app—not the entire session unless necessary.
8. Verify health and real postcondition.

For multi-file feature changes, deploy compatible service and client versions together, with an explicit bridge protocol version. Keep the old service/client pair ready to restore.

## 18.2 Do not flash

This PWNAGE round is userspace and application focused. Do not write boot, recovery, modem, vendor, super, userdata or other partitions. Do not use Heimdall/Odin/TWRP for any requested item. Do not replace the running kernel. If a real kernel limitation is discovered (e.g. an actual inability to wake from suspend), document the source evidence and propose a separate controlled kernel work item; still complete the userspace awake/display-off alarm path.

## 18.3 Rollback requirements

Provide one explicit rollback command/script per deployment group:

- Clock service/bridge/UI;
- Notes file migration/service/UI;
- unified desktop layout migration;
- downloader provider/package;
- audio/microphone settings and PipeWire changes;
- GTK/Flatpak theme settings;
- native chat clients and desktop entries.

Rollback must restore code/config, not delete user data. For Notes, preserve any newly created `~/Notes` content even if the UI rollback is needed. For alarms, preserve new alarm records in a compatible export before restoring previous service code. For widgets, preserve the migrated layout JSON and provide reverse migration if safe.

## 18.4 Reboot policy

Avoid rebooting after every edit. Reboot only when service initialization/udev/system config requires it or to prove reboot persistence. Before reboot:

- verify root console/SSH availability;
- verify rollback files are present;
- verify no long download or data migration is in progress;
- capture current boot configuration and boot ID;
- ensure Clock alarms and Notes data are durably committed.

After reboot reconnect over Wi-Fi SSH using the same key and re-run all persistence checks. If the phone does not reconnect, do not keep issuing blind restarts or destructive recovery actions; use the documented recovery path and report exactly what happened.

---

# 19. Final deliverables

Commit or stage the implementation with clear commit boundaries. Add/update documentation under `docs/pwnage-84000/` covering:

1. `README.md` — scope, architecture and completion status;
2. `ROOT-CAUSES.md` — actual reproduced causes with paths/log references;
3. `SERVICE-APIS.md` — Clock scheduler, Notes, Downloader and Calendar reminder schemas;
4. `DESKTOP-LAYOUT.md` — grid model, migration and drag state machine;
5. `AUDIO-MICROPHONE.md` — actual S10+ input route, gain, processing and measurement;
6. `THEMING.md` — system/GTK/Flatpak integration;
7. `PERFORMANCE.md` — before/after timing methodology and raw numeric results;
8. `DEVICE-TEST-MATRIX.md` — each physical test and pass/fail;
9. `ROLLBACK.md` — exact restore commands;
10. `evidence/` — redacted, non-sensitive screenshots/log snippets/checksums.

Final response must summarize:

- what was broken and the proven root cause for each item;
- every code/config/unit/package path changed;
- service/API schema changes and migrations;
- how root SSH was established (never show private key contents);
- exact package versions and architecture for yt-dlp/FFmpeg/Legcord/Vesktop;
- tests run and results;
- real launch-latency before/after table;
- mic recording metrics and whether owner-confirmed speech was intelligible;
- screen-off and suspend alarm test results, distinguishing the two;
- a list of items needing the owner to manually sign into chat apps or provide missing image assets;
- rollback commands and any remaining hardware limitation.

A green UI, process existence or accepted API call is insufficient. Every “working” claim needs a measured or physically observed postcondition.

---

# 20. Technical reference notes verified for this prompt

These references guide implementation but do not replace checking the versions actually installed on Nuxel.

## yt-dlp

- Official project README / CLI reference: https://github.com/yt-dlp/yt-dlp
- Official FAQ on browser cookies: https://github.com/yt-dlp/yt-dlp/wiki/FAQ
- Current documented post-processing options include `--extract-audio`, `--audio-format`, `--remux-video`, and `--merge-output-format`. The official FAQ documents `--cookies-from-browser` and warns that exported cookie files contain broad browser session data and must be protected.
- The current manpage reference documents preset aliases `-t mp3` and `-t mp4`; verify the installed build with `yt-dlp --help` because CLI presets can vary with version.

## Vesktop

- Official install guide: https://vesktop.dev/install/linux/
- Official release page: https://github.com/Vencord/Vesktop/releases
- Official packaging metadata: https://github.com/Vencord/Vesktop/blob/main/package.json
- Official Linux docs currently identify ARM64 native packages and say native packages are preferred where possible; Flatpak has limitations including rich-presence and drag/drop access tradeoffs. Recheck the current release and package metadata before installing.

## Legcord

- Official source/README: https://github.com/Legcord/Legcord
- Official releases: https://github.com/Legcord/Legcord/releases
- Project docs describe ARM64 Linux support and native package artifacts. Recheck current ARM64 RPM/AppImage asset, release checksum and metadata before installing.

## GTK / libadwaita / Flatpak appearance

- GNOME appearance convention: `org.gnome.desktop.interface color-scheme` (`prefer-dark`, `prefer-light`, `default`) is the modern appearance preference used by GTK4/libadwaita when session/portal settings are wired correctly.
- Older GTK3 apps commonly need a GTK theme setting such as `Adwaita-dark`.
- Flatpak GTK3 theming may require the correct runtime theme extension; GTK4/libadwaita should generally follow the appearance preference through the settings portal. Do not force all apps with `GTK_THEME`.
- Inspect Flatpak overrides for an empty `GTK_THEME=` environment override, which can interfere with normal toolkit theme selection.

## Linux power / alarms

- RTC wake and suspend behavior is device/kernel specific. The existence of `/sys/class/rtc/rtc0/wakealarm` or a successful write is not proof that the phone wakes from its actual suspend state. Test the physical device with screen off and real suspend/resume, record the result and implement a bounded fallback if the S10+ firmware/kernel does not deliver the requested wake.

---

# 21. Final instruction

Do not negotiate the scope down to a mock, design-only pass or “future work” document. Execute the changes in a controlled order and get Nuxel closer to a dependable daily phone OS. At the same time, do not lie about hardware behavior, bypass security, leak the owner's credentials, or put the phone at risk with unreviewed flashing or destructive commands.

**Connect over Wi-Fi SSH as root with `~wicked/.ssh/wicked_wqn_id_rsa`, inspect the actual Nuxel phone, implement the complete workstreams above, test on hardware, preserve all working functionality, and deliver evidence-backed results.**
