# 🐧⚡ NUXEL A66 — OPERATION PENGUIN POLISH 15000
## FULLSCREEN ESCAPE · GLOBAL NAVIGATION · LOCKSCREEN · BATTERY · HAPTICS · AUDIO · ORIENTATION · APP STACKING

**Execution model:** `deepseek-v4-pro-thinking`, via the already-configured `csft`/CodeSeeQ client on the Fedora laptop. **Project:** existing Nuxel checkout and **actual Samsung Galaxy S10+ SM-G975F (beyond2lte, Exynos 9820), Fedora ARM64 userspace with Samsung-derived 4.14.x kernel**. Verify every architecture claim against live code/device before acting. **This is an implementation-and-verification mission, not just planning.**

**Owner's BREAKTHROUGH reported 2026-10-23:** Real Wi-Fi connection, Nuxel Browser, DNS, TLS and Internet now work. **DO NOT REGRESS OR REBUILD THESE.** A65/14000 solved major foundational problems; this mission is a narrow, surgical follow-up. Historical prompts are diagnostic background, not overrides of working live behavior.

## THE TEN OWNER REQUIREMENTS — YOUR ACCEPTANCE CONTRACT

| ID | Observed problem | Required behavior |
|---|---|---|
| A66-01 | Browser occupies fullscreen, captures screen/top swipe/bottom nav; Back/Home/Tabs unusable | Browser cannot trap user. Always operable top notification pull-down and system nav (or intentionally hidden nav with bottom-edge reveal); Back exits browser according to stack; Home goes to Nuxel desktop; Tabs opens system app switcher. Browser stays functionally online and HTTPS-capable. |
| A66-02 | Lockscreen battery reads **0% for minutes on reboot** | Lock and unlocked status surfaces use same live authoritative battery provider. Never display fabricated 0 when unknown; show placeholder (`—%`/loading) until real sample; instant sample at startup and lockscreen mount/resume, push real updates. |
| A66-03 | Turning screen off doesn't immediately engage lockscreen | Default setting `lock_when_screen_off = immediately`; Power/display-off causes actual lock state before wake, and wake shows genuine swipe lockscreen. Home Settings supports alternative lock-after-off timeout (owner-selectable seconds/minutes) and persists/reboots correctly. |
| A66-04 | Home dock's four app icons overlay Settings and other applications | Four pinned desktop icons are visible **only when Home is frontmost**, not in applications, lockscreen, app switcher, or browser. Apps are foreground over desktop dock. |
| A66-05 | Keyboard doesn't vibrate | Native on-device keyboard keypress haptics work where hardware interface supports them; Home Settings toggle + intensity control (e.g. off, low, medium, high, calibrated range) with safe capped durations, persistence and real actuator feedback. |
| A66-06 | Triple nav haptics happen on release and Back hold feels wrong | Back/Penguin Home/Tabs haptics trigger on **touchdown/pointerdown** exactly once, not pointerup; reasonable long-Back feel (down feedback, deliberate hold threshold, optional distinct threshold pulse, cancellation on movement/release). All haptic strength controllable, hardware permitting. |
| A66-07 | Global Back/Home actions don't reliably leave apps | Short Back moves within app history, eventually exits to Home; Penguin Home backgrounds the app and presents launcher **desktop with icons and meters**; Tabs opens app switcher. Long Back force closes focused non-launcher app with clear feedback; **never kill Home/launcher, compositor, lock service or critical OS daemon**. Works even with fullscreen native/WebKit windows. |
| A66-08 | SnekByte and other apps retain redundant top `Home / AppName` bar; game has desktop icons drawn over it | Remove only shell-injected **redundant** per-app Home/title chrome from every application (don't delete important app-local browser address bar, native dialogs or system top status area). SnekByte fills true usable region between system safe areas; no dock over game. |
| A66-09 | Audio not functional / no feedback on volume change | Restore truthful phone speaker/headphones audio through installed codec/mixer/ALSA/PipeWire chain; changing volume produces a **short audible preview** at the **new** volume, when output is unmuted and available, respecting mute/silent/privacy. No surprise high-volume tones or loops. |
| A66-10 | Which kernel is required for accelerometer, gyroscope and camera? | Do **read-only device-specific 4.14 capability audit** of sensors, rotation path and camera ISP; give sourced technical verdict and minimally invasive next steps. Do not flash or upgrade kernel. If drivers missing, identify precise dependencies and testable blockers rather than falsely promising 6.x solves them. |

**Cross-feature success:** fixing browser navigation, haptics, audio and shell layers must not undo working Wi-Fi + Nuxel Browser, launcher grid, touch, SnekByte, boot animation, USB console, unlock gestures, camera app escape, or existing Nuxel styling.

---

## 0 — SAFETY, LIVE TRUTH, AND NON-NEGOTIABLE EXECUTION RULES

**P0:** Preserve a way out of every app. Before any changes, verify the Fedora-to-phone **USB Live Console** is truly accessible while the GUI is locked or fullscreen. Record exact tested transport/command, both users, systemd session owner, current services, and a reversible emergency recovery procedure. If access is not independently verified, **do not restart shell/compositor/input/lock/audio services**; work offline and stop before risky deployment.

- Confirm existing Nuxel Git branch/HEAD/status and phone's actual deployed JS/CSS/HTML/compiled assets, service units, packages, versions, binary hashes, active process tree and runtime config. A patch to a nondeployed source file is not a phone fix. If another 12K/13K/14K agent is running, coordinate for **one** phone deployment owner. Avoid overwriting uncommitted work.
- Create feature branch (unless owner's current workflow requires otherwise), reproducible before state + timestamp, backups of each changed file/service, manifest of reversible deployments. Never blanket `git reset --hard`, wipe profiles, remove working browser libs, overwrite latest `./snekbyte.zip`, or reinstall the entire UI for convenience.
- No bootloader/partition/TWRP flash, kernel image/DTB swaps, unsolicited reboot, firmware writes, unverified `modprobe` touching fragile hardware, or risky register poking. Explicit permission for actual cold reboot and interruptive service restarts. Verify owner remains able to use phone throughout.
- Do not simulate real input without distinguishing desktop automation from physical phone taps; mock unit tests are necessary but not enough. Record physical results; if owner action needed, give minimal exact test procedure and report `AWAITING_OWNER_PHYSICAL` rather than asserting PASS.
- Keep secure HTTPS verification enabled. Don't disable certificate checks, sandbox protection, Wayland access controls or authentication to make apps launch.
- Begin from current **working** connected Wi-Fi+TLS/browser snapshot, including a successful real HTTPS load, then take same test after every shell/browser process change. Internet-related source files are **protected unless concrete evidence of a UI dependency bug requires a minimal change**.

### First-party diagnostic leads, adapt to actual session and hardware

```sh
uname -a
cat /etc/fedora-release 2>/dev/null || true
systemctl --user list-units --type=service --no-pager 2>/dev/null
loginctl list-sessions
ps -eo user,pid,ppid,comm,args | grep -Ei 'nuxel|phoc|wlroots|webkit|gtk|pipewire|wireplumber|lock|keyboard' | head -120
pactl info 2>/dev/null; wpctl status 2>/dev/null
cat /proc/bus/input/devices
find /sys/class/power_supply /sys/bus/iio/devices /sys/class/leds -maxdepth 2 -type f 2>/dev/null | head -140
```

Discover real binaries and input/output paths before issuing commands; no need to install unnecessary tools. Logs/screenshot captures must avoid Wi-Fi PSKs, tokens, chats, browsing history, or personal data. Capture relevant state, not indiscriminate secret dumps.

**Collect phase-0 reproducible evidence:** exact browser process, page, fullscreen mode, touchscreen event and surface layers; top bar & bottom three navigation widgets; WebKit/GTK host window; desktop four-icon dock; lockscreen battery; Power OFF/Wake behavior; haptic actuator path; ALSA/PipeWire state. For every A66-ID record `OWNER_REPORTED`, `REPRODUCED_PHYSICAL` or `NOT_REPRODUCED`, with logs/screenshots and initial hypothesis. Prioritize shared root causes (overlay, compositor subsurface clipping, input grabs, stale deployment, wrong z-order) over ten unrelated workarounds.

---

## 1 — DESIGN ONE AUTHORITATIVE SHELL STACK, NOT PER-APP CSS BAND-AIDS

Map the actual current stack: Wayland compositor (Phoc derivative or equivalent), GTK shell window(s), WebKitGTK surfaces, app-host overlays, keyboard layer, fullscreen native windows, locks, OSD, status panel, Home desktop grid/dock, global nav and app switcher. Diagram the real ownership and layer order from live code and runtime.

**Invariant visual/input layers (implementation-specific, verify Wayland protocol support):**
1. wallpaper + desktop widgets + **four pinned app icons**, rendered and hit-testable **only while Home is current surface**;
2. foreground application surface, allocated usable viewport and actual keyboard focus; not obstructed by desktop dock;
3. shell-owned bottom system navigation/gesture-reveal surface and top status/notification-pull surface as *real compositor-controlled shell layers*, not elements trapped inside the application web document;
4. transient software keyboard, volume OSD, legitimate modal dialogs/notifications, with deliberate nonoverlapping interaction zones;
5. authoritative lockscreen when locked; secure input policy prevents applications drawing/capturing through the lockscreen.

Wayland compositor/layer-shell may supply layer ordering/exclusive zones; study installed compositor capabilities, protocols and any existing Nuxel overlay implementation before introducing new dependencies. Implement in a coherent native/system shell surface or compositor-managed layers with correct input regions, `exclusive_zone`/usable geometry when available, and stable focus transitions. **Do not rely on `z-index: 999999` in the launcher HTML to beat a separate fullscreen Wayland window.** Avoid global transparent overlays intercepting application touch. Always account for curved corners, 1440×3040 physical panel vs actual scaled Wayland logical output, cutout, dynamic viewport, rotations and OSK.

**System nav policies:** `always_visible` (default for now, explicit user preference if existing) and `auto_hide_in_apps` (optional). When hidden, downward? No: **bottom-edge upward swipe** within a narrowly scoped gesture strip reveals controls for a sufficient usable interval; first gesture reveals, doesn't click underlying app. Controls remain operable under true browser/native fullscreen. Respect screen-lock ownership, never overlay locked screen inappropriately. Avoid overriding browser vertical scrolling away from bottom gesture strip. If current compositor cannot reliably draw on top of exclusive fullscreen, implement compositor integration/disable exclusive fullscreen for phone apps and offer genuine maximized-usable-area mode, not a fake CSS fix.

**Status pull-down:** Must start from very top edge in apps/fullscreen and open Nuxel quick settings/notifications. Define input priority and reveal affordance across WebKit and native surfaces. Do not assume adding an HTML listener inside Browser is equivalent to compositor-level pull-down.

**App chrome:** Remove custom redundant top `Home` plus app-name title bars only where Nuxel added them. Real browser's responsive URL/navigation bar is app content and must be preserved. Native app meaningful menus/dialogs remain; maintain safe insets. SnekByte should use app viewport correctly, fit vertically without top-title overhead, and not render behind navbar/keyboard or camera cutout. Do not hide global navigation to make game fit unless owner enabled hidden-nav mode.

---

## 2 — A66-01 & A66-07: GLOBAL BROWSER ESCAPE AND NAVIGATION SEMANTICS

Use compositor-level event trace of *real physical touches* on all three buttons while HTTPS Browser is foreground. Locate the true failure: WebKit fullscreen calls `requestFullscreen`, GTK `fullscreen()`, Wayland fullscreen state, stacking or clipping, input-grabbing focus, overlay unmapped/hit-region stale, dialog, or shell app event hook. Check whether browser takes display keyboard focus and pointer events, whether top/bottom bars are actually beneath an opaque Wayland surface, whether bar is visible yet hit blocked, and if key dispatch reaches a shared navigation dispatcher. Fix actual root cause with minimal safe patch.

Create **one central navigation controller**, not browser-specific custom script, resolving focused app identity/window/task/back-history and system-level events. Required state machine:

- **Short Back:** first dismiss applicable system overlays/keyboard, then in-app navigational history (`canGoBack`/WebKit or native app router), then close the current top-level app *view* or background it and return to Home when at root. Multiple presses must eventually return to Home; avoid loops where browser silently navigates across endless redirects; keep sane backstack and bounded behavior. Do not indiscriminately close every app on first Back if user has browsing history.
- **Penguin Home:** always bring the actual Nuxel **desktop** task/window to foreground (launcher icons, desktop widgets/meters), not Applications grid and not an invisible Home page beneath browser. Background—not kill—the active nonlaunch app; restore its state if reopened. Work from browser, SnekByte, Settings, Camera, native GTK, long-running loaders, OSK active, rotated window.
- **Tabs button:** open Nuxel's **system-wide app switcher/recent apps** and foreground selected task. Do not confuse it with browser tabs unless user selects browser-app-specific UI. Disabled/stale task entries should cleanly disappear.
- **Long Back:** on pointerdown start cancellable monotonic hold timer, threshold e.g. 650–900ms configurable if needed, only for focused non-Home user app. At threshold, distinctly acknowledge with haptic and invoke graceful close, then escalation limited to that app's PID/window/process group after verification, respecting shared GTK/WebKit host processes (avoid killing one shared process hosting Home and multiple apps). Never kill launcher, compositor, Nuxel bridge, lock service, audio, NetworkManager, or whole user session. If focused app cannot be safely isolated, return explicit warning and provide fallback rather than killing shell. Suppress short-Back on long press. Releasing outside/gesture cancel should not kill.
- **Button timing:** trigger normal input feedback and action intention on pointerdown, but differentiate click navigation on valid release from long-press gesture. User specifically demands the **vibration immediately on touch**, not after release; actual app action may use release after tap qualification to avoid accidental launches. Document event sequencing.

Test browser started from launcher, browser background/reforeground, active load, HTTPS scroll, URL focus + keyboard raised, web fullscreen content, new tab, browser with no network, before/after app switch. Verify both top pull-down and nav across fullscreen. Verify no regression in https://www.google.nl and another valid HTTPS origin.

---

## 3 — A66-04 & A66-08: DESKTOP DOCK MUST NEVER OVERLAY APPS

Find the four desktop shortcuts' actual render owner and how their visibility is computed. They may be independent always-on-top GTK/Wayland overlay rather than CSS, or background icons incorrectly retained in a shell overlay while foreground app shows. Do not simply position them lower or force a huge CSS `z-index` on app pages. The fix is **task-dependent presentation** from one authoritative `desktopVisible = (foregroundTask == launcherHome && !locked && !switcherActive)` state, with compositor stacking/input regions matching visibility. Ensure no invisible hitboxes intercept app taps.

Remove Nuxel shell-generated duplicate app title `Home | <AppName>` from browser, Settings, SnekByte, native Camera, installed apps where safe, while maintaining functional app-local toolbars and OS dialogs. Verify SnekByte latest from current deployed source; do not replace newest game with old 5000/7000 versions. Test Full-screen-ish usable viewport in portrait/landscape, nav bottom and dynamic keyboard, status pull-down; touch/gamepad/swipes and retained game pause/resume.

Fix foreground activation when tapping apps/recent entries if still broken: call supported compositor surface-raise/activation, restore from background, transfer input focus and place app above desktop; understand Wayland restrictions and correct activation-token pathway. **No blind global "always-on-top" flags for every app.** Prove correct stack after launching three apps and toggling Home/Tabs.

---

## 4 — A66-02: BATTERY REBOOT 0% IS A DATA/READINESS REGRESSION

Owner says normal meters update correctly after unlock, while lockscreen shows `0%` for minutes. Treat this as separate consumers with divergent initialization/subscribe lifecycle, not necessarily as a battery-driver problem.

Audit actual `power_supply` capacity path, status and read permissions: discover installed devices dynamically (`/sys/class/power_supply/*/type`/`capacity`), detect multiple battery nodes, privileged bridge API, DBus event flow, cache TTL, startup race, JSON default value/coercion (`Number(null) === 0` / `parseInt(undefined) || 0`), stale lockscreen WebKit asset and update timer that starts only once Home is unlocked. Do not assume path `BAT0` or Android HAL or constant battery percentage.

Create **one authoritative battery service/store** with explicit states `UNKNOWN`, `FETCHING`, `VALID` (0–100 real sample), `STALE`, `UNAVAILABLE`, sampled at service readiness and on each new lockscreen mount/wake, publishing last-known-valid reading with age and event subscription. Require prompt read early at boot, before lockscreen first paint if possible, with bounded asynchronous fallback—not a multi-minute timer. Unknown must display `—%` or appropriate indicator, **never fake 0%**. A genuinely measured 0% must still display 0. If live source produces 0 only during initialization, validate presence/status and defer until stable per evidence. Never show outdated value indefinitely.

Verify boot/wake/lockscreen/unlock 10 times, battery % matches same-time physical power source/status bar, charging indicator correct, no elevated CPU/wakeups due to aggressive polling. If first read truly cannot occur until driver initialization, measure the latency, document exact hardware reason and present correct loading state until available.

---

## 5 — A66-03: SCREEN OFF MUST LOCK NOW, WITH DELAY OPTION

Separate `display_off`/DPMS, `suspend`, `idle`, `lock_state` and visual lockscreen map/unmap. Identify real Power button/input path, screen blanking, compositor event callbacks and current lock manager IPC. **Default policy: on any intentional display-off transition, invoke trusted lock manager synchronously (or establish lock commitment) before hiding screen or allowing wake/foreground access.** On wake show existing draggable penguin lockscreen; preserve genuine unlock authorization, tactile/touch interaction and wallpaper. Do not fake lock by overlay animation or setting only JS `locked=true` while apps remain accessible.

Add Home Settings (exact existing settings architecture): `Lock after screen turns off`: `Immediately` (default), 5s, 15s, 30s, 1m, 5m, or owner-configurable safe range. Timers monotonic, restart/reboot persistence. At chosen delay, screen wake **before** deadline may return to session; after deadline it must be locked. Hard lock action/manual `Lock now` always immediate independent of delay; incoming security/session-policy locks override delay if applicable. Define what happens if device suspends (timer doesn't tick in process; use resume timestamp/time source robustly), repeated power presses, wake due to notifications, and service crash (fail secure; never silently leave unlocked when policy requires a lock).

Document **difference** from screen-on idle timeout; do not confuse them or change idle auto-lock unless explicitly required. Test 10 quick off/on cycles immediately, delayed mode 30s, boundary resume, lock/unlock with browser, cold boot default, service restart, existing drag gesture; emergency console recovery preserved.

---

## 6 — A66-05 & A66-06: REAL HAPTICS WITH TOUCHDOWN TIMING

Discover **real** hardware vibrator path in current 4.14 vendor kernel via read-only inspection (`/sys/class/leds`, `/sys/class/timed_output`, `/sys/class/input`, `/dev/input/event*` capabilities `EV_FF`/`FF_RUMBLE`, and specific Samsung vibrator driver if compiled). Inspect kernel config/device tree/driver source in the Nuxel checkout; do not assume Android Vibrator HAL or `/dev/hidraw` exists. If no actuator access, report hardware blocker and implementation interface; never claim visual animation equals vibration.

Implement one safely bounded `HapticService` broker with intensity and duration mapping to actual hardware API, serialized access and permission enforcement. Avoid racing multiple clients, hanging sysfs toggles, long continuous motor drive, permissions `chmod 777` or setuid world-write endpoints. Rate limit typing feedback and auto stop on app death. If linear amplitude isn't exposed, support calibrated discrete patterns where available, with explicit note that duration != physical strength. Never claim intensity scaling when hardware supports only on/off.

On **keyboard pointerdown** deliver perceptible short tick; don't vibrate for every spurious move/scroll/composition event, no ghost repeats. Settings: Keyboard haptic enabled default consistent with owner's choice; intensity `off/low/medium/high` or hardware-calibrated numeric slider, per-user persisted, visual test control. Screen reader/assistive accessibility and silent/haptic policies should be respected where configurable.

On nav buttons (`Back`, `Penguin Home`, `Tabs`) give immediate haptic acknowledgment upon validated initial pointerdown **not pointerup**, then optional second distinct pulse precisely when long-back threshold is reached. Touch `pointercancel`, rapid double taps, slide-away and pointer capture behavior correct. Short Back must not execute after successful long Back. Provide event timestamp instrumentation and test difference between touch-down, pulse-start, release and long-action threshold (target feedback latency <70ms when hardware permits; measure reality, do not invent measured result). Ensure keyboard haptics don't block UI event loop, volume haptics if requested elsewhere stay unaffected.

---

## 7 — A66-09: AUDIO END-TO-END AND PROPORTIONAL VOLUME PREVIEW

The owner specifically wants **hear audio while adjusting volume**, in proportion to the current output level. Diagnose **both actual output ability and volume-preview trigger**—a decorative OSD is insufficient.

Map exact Exynos 9820 vendor ALSA ASoC codec/board paths, UCM profile, ALSA card enumeration (`aplay -l`, `amixer -c <card> scontrols/contents` if present), PipeWire/WirePlumber or PulseAudio equivalent, user-session socket, default sink, application streams, headphone/speaker routing, mixer mute/gain, and policy. Identify whether driver nodes exist but profile/routes are absent versus no working audio kernel path. Avoid random ALSA hardware register pokes, unbounded mixer gain or boot-level kernel changes.

Safe read-only inspection, adapt to installed commands:

```sh
cat /proc/asound/cards 2>/dev/null
cat /proc/asound/pcm 2>/dev/null
aplay -l 2>/dev/null
wpctl status 2>/dev/null
pactl list short sinks 2>/dev/null
systemctl --user --no-pager status pipewire wireplumber 2>/dev/null
journalctl --user -b --no-pager -u pipewire -u wireplumber -n 120 2>/dev/null
```

After safe routing fixed: system volume keys/settings update actual active sink gain; volume UI shows true hardware/software effective percent, speaker/headphone route obeyed, mute applies immediately. On setting volume to a new **nonmuted** value, play short bundled locally-generated/packaged sample at **that new volume** through current output; wait until sink volume committed before tone. Do not fire preview on mute, if audio output isn't ready, during a phone call/recording/quiet policy, on programmatic boot restore, or on every frame of drag; debounce slider preview, cap maximum sound level and duration, no clipping. At 0% hear nothing; low/mid/high audibly distinct, do not artificially normalize volume preview. Test with owner-approved conservative speaker level and optional wired output if detected; avoid loud sine wave at 100%.

Keep playback API nonblocking and resilient to missing codec path. Provide separate truthful status for `(1) mixer and PipeWire operational`, `(2) actual speaker audible`, `(3) 3.5mm headphone output`, `(4) preview proportional`, `(5) volume keys`, each `PASS_PHYSICAL / BLOCKED_HARDWARE / UNVERIFIED`. Never fake `audio working` from service status only.

---

## 8 — A66-10: SENSOR/CAMERA/KERNEL DECISION — READ-ONLY FEASIBILITY AUDIT

**Owner question:** Must Nuxel migrate from 4.14 to v6.x to enable accelerometer, gyroscope, and camera on Samsung Galaxy S10+? **Preliminary answer: NO, a major kernel jump is not a prerequisite and does not guarantee those peripherals.** postmarketOS device listing for `samsung-beyond2lte`, as checked in Oct 2026, still classifies S10+ as **downstream, mainline no, kernel 4.14.309** and sensors untested rather than established working. Official old Exynos4 FIMC support must not be mistaken for full Exynos 9820 FIMC-IS vendor ISP compatibility. Cross-check current upstream/device status at execution time.

Read-only audit of **actual** phone and available kernel/device-tree sources:

1. `uname -r`, module directory/kernel config, kernel logs around Samsung sensorhub/SSC/SPI/I2C and FIMC-IS; enumerate present drivers, relevant DT nodes, regulators, GPIOs, clocks, firmware names and references. Never treat a file existing on disk as proof of loaded hardware.
2. Sensors: list `/sys/bus/iio/devices`, relevant `/dev/input/event*` with decoded axes if `evtest`/`libinput debug-events` available, sensorhub driver character nodes, `iio-sensor-proxy` service status/capability, `monitor-sensor` if installed, sysfs scale/axis orientation and compositor transform. Identify exact IMU chip/sensorhub ownership *from reliable device logs/sources*, not from generic S10 online specs. Determine whether (a) real raw motion samples update, (b) calibration/orientation matrix works, (c) userspace proxy publishes, and (d) Phoc/shell rotation listens. User's prior auto-rotate doesn't work: this may be fully userspace if sensor samples exist.
3. Gyroscope: separate gyro driver data from accelerometer-derived coarse orientation. Auto rotation usually relies on gravity/accelerometer; gyroscope is not necessarily required for basic screen orientation. Record true sensor needed per feature.
4. Camera: enumerate `/dev/media*` topology, `/dev/video*` node caps (capture vs metadata/M2M), live pipeline links, FIMC-IS firmware/load results, sensor binding, libcamera handlers and V4L2 capabilities; determine whether **real hardware frames** are possible on 4.14. Owner's prior screenshot showed "68 V4L2 nodes enumerated" and "Live capture NOT verified"; enumeration alone is not a photo/video. No random streaming register guesses, no dummy frame or software test card presented as camera working. Camera UI shouldn't hang even if hardware pipeline missing.
5. Compare **three options** separately per component: repair 4.14 userspace/driver config; minimally backport missing vendor driver or firmware support to known-working 4.14 (nonflashing research phase only); independent 6.x mainline/forward-port research branch. Estimate port risks to boot, display, touch, USB rescue, Wi-Fi, audio, battery, modem, camera and vendor GPU, and exactly what evidence makes kernel migration justified. Do not assert a vendor module from 4.14 will build/work unchanged on 6.x.
6. Produce `docs/a66-15000/KERNEL-4.14-VS-6X-HARDWARE-DECISION.md` with *real detected sensor part IDs and loaded drivers if available*, evidence paths, actionable next minimal tasks, truthful blocker classification, and firm recommendation to **keep known-good 4.14 live** while 6.x research is isolated from the daily phone.

**Reference starting points for agent to verify, not substitutes for device inspection:**
- postmarketOS Galaxy S10+ device page: https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_%28samsung-beyond2lte%29
- Kernel docs for older EXYNOS4 FIMC: https://www.kernel.org/doc/html/v5.7/media/v4l-drivers/fimc.html
- Samsung Exynos 9820 S10+ Android device specifications: https://doc.e.foundation/devices/beyond2lte/

---

## 9 — DEPLOYMENT: SMALL REVERSIBLE STAGES, DO NOT REBOOT UNTIL REQUESTED

Divide patches into isolated evidence-based commits, dependent only as needed:

- **A66a — shell escape + global compositor/system nav:** fix browser fullscreen overlay, top pull-down and bottom nav layer before styling.
- **A66b — foreground app/task semantics + desktop dock + redundant title bar:** Home and SnekByte content fits, desktop widgets hidden in apps.
- **A66c — lockscreen battery + screen-off lock policy:** startup data race, secure timing, Home Settings persistence.
- **A66d — haptics (keyboard/nav) + long Back gesture:** safe actuator broker, pointerdown timing and Settings.
- **A66e — audio route/volume-preview:** real sample through real sink after correct volume.
- **A66f — read-only sensor/camera/kernel technical verdict:** docs only, no kernel migration.

For each stage: record failure reproduction → root cause → minimal code diff → tests → build artifacts → staging deployment → physical acceptance and screenshot/log receipt → rollback steps. If real device deployment is not safe/available, complete offline code/test changes and mark hardware verification as pending. Avoid changes to Wi-Fi authentication, TLS provider, browser networking, camera driver, vendor kernel, boot images, touchscreen, game mechanics unless absolutely necessary with proven root cause.

Define resource ownership and type-safe event bus for `NavigationController`, `TaskManager`, `ScreenLockManager`, `BatteryProvider`, `HapticService`, `AudioService`; avoid duplicated watchers/intervals, stale bridge IPC, global unguarded event handlers, speculative `systemctl restart` loops, multiple competing background shells. Derive UI visibility from one foreground-task state; make state available reliably after startup/reconnect.

### Test harness / automated tests (necessary but not sufficient)

- Unit tests for navigation stack: keyboard-visible Back → hide OSK; app internal Back → previous route; at root Back → Home; Home backgrounds; Tabs app switcher; Back hold over threshold kills only focused isolated app, not Home; cancel/movement/short press doesn't trigger kill; app crash returns Home.
- Window/compositor integration tests: actual input focus/stacking in browser's true fullscreen, dock hidden if desktop background, 3-button overlay above fullscreen and keyboard, app title chrome gone, status pull-down works; appropriate screenshot geometry. Test native as well as PWA windows.
- Battery readiness with missing, zero, stale and delayed values; no phantom `0%`; lockscreen mounts before Home; wake/remount updates immediately; source permission failures handled.
- Lockscreen state machine with immediate and delay modes, monotonic/wake times, quick off/on, repeated events, service restarts, crash-recovery fail-secure, local prefs persisted and back-compat migration.
- Haptic events with fake actuator implementation validating pointerdown timestamp, 1 pulse/tap, optional threshold pulse, no spurious key repeat, safe max duration and policy; physical confirmation separately.
- Sound volume behavior with mock backend volume sequencing and preview throttle, mute/0% no sound, real ALSA/PipeWire physical audible playback separately.
- Browser remains online and safe HTTPS verified before/after (two sites), back/history and app switch; no network changes.

### Mandatory on-device acceptance grid (report individually)

| Case | Physical action | Passing behavior |
|---|---|---|
| P01 | Open Nuxel Browser and visit HTTPS site | Site renders and navigates, TLS remains valid |
| P02 | In Browser tap Home/Penguin while page loads and after page renders | Home desktop with app icons/meters visible; browser backgrounded |
| P03 | Return to Browser, use Back repeatedly | Web page history works then returns Home, never trapped |
| P04 | In Browser tap Tabs | System app switcher opens; switching foreground succeeds |
| P05 | In Browser swipe down from top edge | System status/quick settings drawer appears |
| P06 | Browser fullscreen; bottom bar always-visible then auto-hide in-app | Controls are visible/tappable OR bottom-edge swipe reveals and makes them tappable |
| P07 | Launch Settings and SnekByte | No pinned desktop dock icons over either app; no redundant Nuxel top Home/AppName header |
| P08 | Switch Apps via Tabs and return Home | Foreground input focus and task order correct; desktop dock reappears only at Home |
| P09 | From Settings press Back multiple times | At root returns to Home, not frozen |
| P10 | Long-Back with disposable user app | Single targeted app closes; Home/daemon alive; on threshold second feedback if chosen |
| P11 | Touch each nav control | Immediate haptic on finger-down, not finger-up; no accidental duplicate |
| P12 | Type in native keyboard | Short palpable haptic; setting off/on/intensity honored on physical device |
| P13 | Cold-boot to lockscreen | No fake `0%`; real battery sample displayed promptly or honest loading until available |
| P14 | Unlock, screen OFF then ON immediately | Genuine lockscreen shown before usable apps (default immediate) |
| P15 | Set delayed lock 30 sec; off/on at 10 sec and 35 sec | Before deadline session; after deadline lock; persistence on reboot |
| P16 | Press volume buttons / change slider conservative speaker volume | Actual level changes and audible short preview matches new level; mute silent |
| P17 | Run audio playback in supported app | Real speaker output at calibrated safe volume, route genuine |
| P18 | SnekByte play for 2 minutes with Home/Back/Tabs navigation | Game viewport fits, touch/swipe functional, no dock/title chrome, no accidental app kill |
| P19 | Open native GTK and WebKit apps and switch between them | All escape functions work, no focus trap |
| P20 | Owner-approved reboot after backed-up deployment | Navigation, locks, battery, haptics, audio and working Internet survive |
| P21 | Read-only sensors and camera audit | Signed-off 4.14-vs-6.x decision with actual device evidence; no kernel change |

For physical acceptance require repeated 5–10 cycles for P02–P06, P13–P15; exact timing and evidence. Service startups must be idempotent, no duplicate hooks or increased battery drain.

---

## 10 — REQUIRED ARTIFACTS / FINAL RESPONSE CONTRACT

Create under `docs/a66-15000/`:

- `LIVE-BASELINE.md` — Git/phone asset hashes, tested USB recovery, provenance, preexisting functional Internet evidence and reproduced symptoms (do not expose secrets).
- `NAVIGATION-STACK-ARCHITECTURE.md` — actual Wayland process/surface stacking + focus controller design + input regions + per-app titlebar/dock policy.
- `CHANGELOG-AND-ROLLBACK.md` — commit hashes, exact edited files, deployment command receipts/status, backed-up paths and tested reversal.
- `TESTS-AND-EVIDENCE.md` — P01–P21 results with timestamps, proof links/logs/screenshots, physical vs mock distinction.
- `KERNEL-4.14-VS-6X-HARDWARE-DECISION.md` — exact sensors/camera/rotation feasibility and independent kernel-port plan if justified.
- `FINAL-A66-SCOREBOARD.md` — one row per A66-ID and physical test; verdicts `PASS_PHYSICAL`, `PASS_OFFLINE_ONLY`, `AWAITING_OWNER_PHYSICAL`, `FAILED`, `BLOCKED_HARDWARE`, `NOT_TESTED`.

Final agent reply must clearly state **what code was changed, where it was deployed, what was physically tested, what is still blocked, and exactly what would reverse it**. Don't declare a feature finished merely because test suite is green, a service is `active`, an input node exists, or browser is online. Never erase the owner's confirmed breakthrough.

## EXECUTE NOW

1. Read current repo + A65/14000 outputs if present, verify actual live phone and USB recovery.
2. Reproduce and instrument the browser fullscreen/input problem and shell stack, without touching network behavior.
3. Fix P0 global navigation/foreground/dock/titlebar.
4. Fix P1 battery/readiness and lock-now policy.
5. Fix P1 keyboard/nav haptics and long-Back semantics.
6. Diagnose and implement real audio/volume preview conservatively.
7. Audit sensors/camera and give the 4.14-vs-6.x verdict **without a kernel migration**.
8. Ship reversible changes, request approval for interruptive live steps/reboots, run real tests, provide P01–P21 evidence and honest blockers.

**PENGUIN POLISH 15000 — INTERNET IS ALIVE. NOW MAKE THE WHOLE PHONE BEHAVE. 🐧⚡**

