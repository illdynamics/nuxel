# 🐧🔊🔄 NUXEL A68 — OPERATION PENGUIN 17000: CONTROL, SOUND & SPIN REVIVAL

## BACK IS BACK · PENGUIN HOME IS HOME · DESKTOP DOCK IS DESKTOP ONLY · REAL AUDIO · REAL ROTATION

**Execution agent:** DeepSeek-v4-pro-thinking via CodeSeeQ (`csft`) on the Fedora 43 laptop.  
**Target:** current, *actually deployed* Nuxel Fedora ARM64 phone OS on Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820, Samsung-derived Linux 4.14.x. Verify versions and software architecture rather than treating historical descriptions as facts.  
**Nature of work:** reproduce failures → trace correct ownership → implement minimal coherent fixes → unit/integration tests → safe installation → physical phone tests → evidence-backed report. **Do not stop at an implementation plan or green mocks.**

## OWNER'S NEW OBSERVATIONS — HIGH PRIORITY

1. **Short Back is WRONG.** In an open application, tapping Back currently appears to visually send that app behind the launcher, while the launcher’s four pinned icons are drawn **over the app**. Instead, Back must perform *in-app navigation first* (browser previous page; Settings prior screen; Camera close transient panel; SnekByte back/exit confirmation if applicable). **Only once the app has no remaining meaningful back destination**, the *next* short Back backgrounds/minimizes the app and reveals the actual launcher **Home desktop**. Never show desktop icons as an overlay on top of a still-visible foreground app.
2. **Penguin Home button is STILL BROKEN.** A direct tap must immediately leave any non-system app visually and display the **real Home launcher desktop** with wallpaper, widgets/meters and four pinned icons. It must not merely change CSS, reveal four icons over the current app, launch an Applications drawer, hide the WebView while leaving a fullscreen native surface above it, or kill the app.
3. **Real audio is STILL NONFUNCTIONAL.** Diagnose speaker-output chain from kernel/ALSA through userspace policy to app/browser/game sound and the volume UI; deliver actual safely audible audio if hardware drivers support it. Prove output with real phone speaker or a clearly identified supported headphone route, not just successful playback API calls.
4. **Automatic rotation is STILL NONFUNCTIONAL.** Diagnose on-phone accelerometer/gyro/sensor hub access, orientation policy, compositor output transform, physical display bridge, touchscreen transform, and app orientation/viewport; deliver actual live rotation if supported by accessible hardware. Support the complete 7-mode owner policy, not just two visible choices. Distinguish sensor unavailability from a broken settings interface. Do **not** propose kernel 6.x as a magic fix.

This is an **incremental A68 repair** following A64/A65/A66/A67. It is **not** permission to re-run every mission 2000–16000 or redesign UI. Prior success is a protected baseline: **working Wi-Fi, DNS, TLS, HTTPS, Nuxel Browser, boot, USB Live Console, launcher sizing, correct icon artwork, latest SnekByte, lockscreen graphics, keyboard, native app inventory and any measured 16000 smoothness improvements.** Do not overwrite or regress them.

## 0 — HARD GATES: REPRODUCE, PRESERVE, AND ENSURE RECOVERY

- Ensure **only one agent deploys to the S10+**; coordinate with any running 16000 graphics optimization and do not restart compositor/audio/session while the other agent is editing it.
- Establish authenticated working out-of-band USB Live Console independent of screen, Wi-Fi and browser. Confirm a read-only command succeeds, session stays connected and a known-good userspace restore procedure exists. Keep a backup on Fedora and on phone with hashes, service units, launcher assets, audio config, rotation config and any modified binaries. Never assume a successful file transfer equals a successful runtime deployment.
- Identify checkout branch, dirty state, target commit, installation build/version, running process PIDs, user services, root services, shell/Wayland owners, compositor protocol support, active runtime paths, deployed file hashes. Use a dedicated worktree/branch; never `git reset --hard` or silently replace owner's WIP.
- Before patching, physically record the four reported failures on phone, with logs, timestamps, video or screenshots. Track a `A68-01` to `A68-04` diagnostic/evidence matrix. Distinguish owner-reported vs agent-observed when physical observation is unavailable.
- No boot image/DTB/recovery/kernel/firmware flashing, no unapproved reboot or compositor teardown, no proprietary GPU blobs installed merely for audio/rotation, no turning off security/permissions, no blanket `chmod 777`, no disabling system services to simplify tests, and no synthetic green statuses. Never kill critical services as a substitute for Back/Home.
- Change only navigation state machine, shell layering/foregrounding, audio and rotation, plus minimal supporting test infrastructure; avoid unrelated camera, Wi-Fi, browser engine, GPU performance or UI design changes. Prefer subsystem-scoped patches with independent rollbacks.
- If a hardware subsystem is genuinely blocked on vendor kernel interfaces, **prove the exact blocker** and complete the unaffected UI/policy/control work. Report `BLOCKED_HARDWARE` rather than passing or initiating kernel port.

### Required baseline discovery (adapt commands to installed distro & privileges)

On the **phone**, not the Fedora host, collect read-only evidence; redirect safely to a dated A68 artifact directory and sanitize passwords/network secrets:

```sh
uname -a
cat /etc/fedora-release 2>/dev/null || true
ps -eo pid,ppid,user,stat,comm,args | grep -Ei 'nuxel|phoc|wlroots|wayland|webkit|pipewire|wireplumber|pulseaudio|sensor|iio' | head -150
systemctl --user list-units --type=service --all --no-pager 2>/dev/null || true
systemctl list-units --type=service --all --no-pager 2>/dev/null | grep -Ei 'nuxel|audio|wire|sensor|display|rotation' || true
find /dev/snd /sys/class/sound /sys/bus/iio/devices /dev/input -maxdepth 2 -print 2>/dev/null | head -170
cat /proc/asound/cards 2>/dev/null || true
cat /proc/asound/pcm 2>/dev/null || true
ls -la /usr/share/alsa/ucm2 2>/dev/null | head -55
```

Discover valid authorization before running commands; diagnostic utilities may not be installed. Test any additional packages offline/in staging first, and install only when needed with owner approval if a download/service disruption is possible. Avoid logging secrets, user conversations, private browsing history, or credentials.

## 1 — MAP THE ACTUAL SHELL STACK: ONE FOREGROUND AUTHORITY

Read all current source for: three-button navigation bar, its callbacks/touch gestures, launcher Home surface and four-icon dock, application registry/launcher, shell bridge / IPC, system app switcher / Tabs, WebKit WebView hosts, native GTK apps, Wayland compositor surface stacking, OSK, lockscreen, and app titlebar removal patches. Correlate with running process graph. Answer with code references:

- Who owns global `foreground_app`, `focused_surface`, `active_workspace`, `home_visible`, `desktop_dock_visible`, `app_back_stack`, `keyboard_visible`, and lock state? Are there two independent state stores that can disagree?
- Are Home/dock/nav/task switcher implemented in a compositor-managed surface, separate GTK window, layered shell overlay, WebView content, or a mixture? Record actual Wayland layer, input region, exclusive zone and z-order. A launcher-local CSS `z-index` **cannot** place the Home surface above another Wayland toplevel.
- Where exactly does short Back currently call `minimize`/`show_home` on its first press? Is back handler being lost in a WebKit JS bridge? Are keydown/pointerdown and pointerup both dispatching? Is app history empty due to stale registration? Are browser and native processes different code paths?
- Why do four pinned Home dock icons show over apps after Back? Check app transition sequencing; `home_visible` may be true while app surface is still foregrounded, or a dock window may be globally always-on-top. Determine which state is authoritative.
- Does the global Penguin button receive events even when native fullscreen app is active? If yes, does the handler focus the real Home surface or just toggle overlay visibility? If not, locate compositor hit-test/Wayland surface/input grab boundaries. Examine post-A67 compositor or renderer changes for regressions.

Produce a compact state diagram and edge-case table **before** implementing. One shell navigation reducer/controller should authoritatively mutate focus/visibility; frontend widgets send intent rather than maintaining a competing UI-only approximation.

## 2 — REPAIR THE SHORT-BACK CONTRACT PRECISELY

Build an app-routing adapter per app type with an explicit `canNavigateBack` / `navigateBack` result contract. Support both synchronous UI routers and asynchronous WebKit/native IPC. Define outcomes like `HANDLED`, `AT_ROOT`, `BUSY`, `ERROR`, and a bounded timeout; don't confuse “JS bridge message queued” with “navigation succeeded.” Avoid stale event replays after app is backgrounded.

**Required short-Back semantics, in order:**

1. If a system-owned transient element owns Back (OSK, open menu, popover, modal, notification shade), dismiss it **without** minimizing its parent app; test precedence explicitly. A modal that is part of app routing should honor its own handler.
2. Otherwise ask the actual *focused app* to navigate one logical back step. Examples: browser previous website/back history; Settings child page to prior Settings panel; photo/gallery detail to gallery list; app-owned view router to previous view. On native apps use published navigation/action contract where supported. If there is no safe universal native history, provide a consistent app shell close/back contract and distinguish unsupported from root.
3. If app reports an actual back navigation, keep it **foreground, focused and unobscured**. Do not display launcher wallpaper/dock/icons. Update route/history state only on confirmed transition or explicit permitted optimistic state that can roll back if failure.
4. If at app root / no more meaningful back steps, this short-Back press is allowed to **background/minimize the app** and switch to real launcher Home. Do not background apps at the first Back merely because an async history query hasn't answered. The browser case must preserve page history and leave after eventual exhaustion.
5. If launcher Home is already foreground, Back must not kill it, expose stale apps or duplicate overlays; it may close launcher popovers/app drawer or otherwise no-op according to existing design.

**Interpretation of owner's wording:** “when can't go back no more, the next Back minimizes” means a press that successfully navigates to root must *not* also minimize. The **subsequent** press at root minimizes. A press already at root can minimize immediately; no arbitrary extra press is required before doing so. Use tests for this exact distinction.

- Long-Back retains explicit prior policy (gracefully close/kill the focused *non-launcher* app after held threshold and suitable haptic confirmation, guarded against shared-host processes). Suppress short-Back when the long press successfully activates. A lost pointer/gesture cancellation must not accidentally kill an app.
- Ensure native/fullscreen app Back works even when embedded WebKit view, OSK or a modal consumes keys; system nav must have a compositor-backed route or consistent native shell handling.
- Repeated presses and queued taps must be serialized/debounced without dropping intentional distinct presses; avoid history loops, double pops and endless “busy.”
- Preserve strong privacy: Back shouldn't reveal other app private content in the background via translucent layers.

### Mandatory navigation integration tests

Test via automated reducer/bridge contract tests and **physical taps**:

```
App state: browser Page A → Page B → Page C
Back #1: Page B; browser remains foreground; dock HIDDEN
Back #2: Page A; browser remains foreground; dock HIDDEN
Back #3: browser backgrounds; Home desktop FULLY foreground; dock VISIBLE

App state: Settings root → submenu → nested submenu
Back #1: submenu; Settings foreground; dock HIDDEN
Back #2: Settings root; Settings foreground; dock HIDDEN
Back #3: Settings backgrounds; Home foreground; dock VISIBLE

App state: Browser Page A + keyboard open
Back #1: keyboard closes; browser/page unchanged; dock HIDDEN
Back #2: if page root, browser backgrounds; Home foreground; dock VISIBLE
```

Replace sample route names with the actual implemented app navigation semantics. Test at least one *native* application where possible, not only Nuxel WebKit PWAs. Check touch, mouse and keyboard back inputs if all supported; minimize/close must not cause history stack cross-app leaks.

## 3 — REPAIR THE PENGUIN HOME BUTTON — A TRUE HOME TRANSITION

Home button (the bottom-middle Penguin face) must cause a shell-level task/focus transition, not app-internal back navigation and not an overlay reveal:

- **On touch-down**, preserve the previously specified immediate haptic feedback where hardware supports it; action trigger should be intentional and consistent with existing UI (avoid accidental double firing on release). Home may require a click-confirm gesture for action while haptic is down; don't conflate the two.
- Route a `GO_HOME` intent to the one trusted shell controller. If screen is locked, do **not** bypass lockscreen. Otherwise instruct compositor/shell to foreground/activate the already-running launcher **Home desktop**, bring its surface above the active app, and give it focus using supported Wayland protocols/application activation. Minimize/background active non-system app **without killing it**.
- Only **after the Home surface really owns foreground focus** may the four pinned desktop icons and Home meters/widgets become visible and hit-testable. Hide app-only widgets. Make the compositor layering and the frontend state converge atomically/acknowledged, avoiding a few frames of icons over app content.
- No duplicate Home processes/windows launched per press. Do not send `wmctrl`-style X11 activation to Wayland windows; inspect installed compositor capabilities and use its real mechanisms, app activation or shell-owned surface stack. If no supported API exists, implement a minimal controlled compositor/shell integration rather than fake CSS fixes.
- From Browser fullscreen, SnekByte fullscreen, Settings, Photos/Camera, an unresponsive app, or the on-screen keyboard, Home must work and reveal **actual launcher Home**, not Applications list. Preserve the app for eventual return via Tabs / app switcher.
- Tabs/app switcher should continue to work and task foregrounding must hide the desktop dock until Home is actually focused. Keep persistent global three-button bar accessible in apps. If user-configurable auto-hide nav exists, preserve edge swipe reveal and tests.

### Desktop dock visibility invariant (enforce at renderer/surface level)

```
showDesktopDock =
    (shell.currentTask == HOME_DESKTOP) &&
    (shell.foregroundSurface == HOME_SURFACE) &&
    !shell.locked &&
    !shell.appSwitcherVisible
```

Adapt to actual architecture; key is consistency between task state **and compositor surface reality**. It must not be globally always-on-top. If desktop is underneath a non-Home foreground app, dock must stay hidden and must not capture touches even if visual transparency is involved.

## 4 — AUDIO: TRIAGE PHYSICAL SPEAKER PATH END TO END

**Priority P0/P1**: Owner confirms audio still silent. Treat kernel support as an empirical question. A successful `aplay` or PipeWire client return code **alone does not prove audible output**.

### 4.1 Device driver and hardware topology

On phone, identify actual ASoC audio card, codec, playback PCM, DSP/firmware if applicable, sysfs paths and errors. Inspect:

- `/proc/asound/cards`, `/proc/asound/devices`, `/proc/asound/pcm`, `/dev/snd/*`, `/sys/class/sound/*`, codec/machine driver logs, device-tree audio nodes and vendor-specific controls; do **not** assume codec chip names.
- `aplay -l`, `aplay -L`, `arecord -l` if utilities installed; `amixer -c N controls`, `amixer -c N contents`, `alsactl` dry/read-only state; map routes, mixer paths, DAPM widgets, speaker amplifier enables, clock/mute gates, impedance/headphone switch if present.
- Existing vendor Android/kernel ASoC route descriptions, shipped ALSA UCM2 profile(s), firmware file requirements and compatibility with Fedora userspace; audio clock/amp power management must be correct. Preserve route sequencing for the real codec; do not toggle undocumented kernel mixer registers blindly.
- ALSA direct playback vs PipeWire/SPA ALSA / WirePlumber default sink, nodes, policy, permissions, route selection, resampling, volume, mute, null sink, audio session user/`XDG_RUNTIME_DIR`. PipeWire backend errors and `pw-top`, `wpctl status`, `pactl info` if PulseAudio compatibility available, journal logs.
- Browser/WebKit and PWA media: sound playback path, autoplay and gesture policy, browser mute state, WebKit GStreamer plugins, application audio permissions, sample format/rate. Check after speaker playback is proven, not before.

Useful **conditional** read-only commands (adapt installed tools, no blind indices):

```sh
cat /proc/asound/cards 2>/dev/null
cat /proc/asound/pcm 2>/dev/null
aplay -l 2>/dev/null || true
aplay -L 2>/dev/null | head -90 || true
wpctl status 2>/dev/null || true
pw-cli ls Node 2>/dev/null | head -100 || true
pactl list short sinks 2>/dev/null || true
systemctl --user status pipewire wireplumber --no-pager 2>/dev/null || true
journalctl --user -b --no-pager 2>/dev/null | grep -Ei 'pipewire|wireplumber|alsa|audio|spa.alsa' | tail -130
```

If playback PCM isn't registered, focus on driver/DTS/firmware blocker evidence rather than pretending adding `pipewire` repairs missing kernel audio. If driver exists but route isn't exposed, build/repair the smallest compatible UCM/profile or restore an authoritative backed-up one, with measured speaker function and safe defaults. If direct ALSA works but PipeWire fails, fix policy/session/permissions; if PipeWire works but browser silent, isolate app/media path. Record which exact level first succeeds/fails.

### 4.2 Low-risk safe audio test and volume UX

- Start **muted / low test volume**, owner-approved audible test, short non-startling chime or spoken test. Never default to maximum speaker amplitude or prolonged raw-wave tests; respect silent/mute and headset route selection. Obtain owner confirmation that sound is actually audible; distinguish speaker, earpiece, Bluetooth and wired outputs.
- Make volume +/- control the **correct current/default hardware/user sink**, no arbitrary null/dummy sink. Show honest UI volume/mute; volume changes within expected perceptual range, no sudden blast or speaker crackle. Playback preview must occur at the **new** selected volume when unmuted, and obey user's preview enable/disable setting if present. No volume preview on zero/mute.
- Capture `before/after` mixer/PipeWire settings and persistent clean session boot behavior. Verify speaker audio in a genuine supported app (e.g. local media and WebKit website with a user gesture) plus volume preview. Prevent crackles, busy loops and CPU starvation; keep A67 performance path intact.
- If speakers cannot be made to emit sound from userspace without absent vendor codec/amp support, document `BLOCKED_KERNEL_AUDIO_ROUTE`, exact evidence, minimal required driver/firmware work, and safe alternative testing. Do not suggest random kernel 6.x flashing.

## 5 — ROTATION: SENSOR → POLICY → COMPOSITOR → PANEL → INPUT

Prior missions called for **seven rotation modes**: forced portrait (normal), forced portrait inverted, forced landscape left, forced landscape right, automatic all, auto portrait only, auto landscape only. Confirm intended labels in existing Home quick settings (not invent duplicate controls), and make selection available from quick settings + detailed Home Settings with persistent state. Locked rotation is a **policy** state; live rotation requires an actual sensor event or owner-driven discrete test. Auto modes should not silently remain forced portrait.

### 5.1 Diagnose true sensor availability on 4.14

- Inventory `/sys/bus/iio/devices/`, `/dev/iio:device*`, `/dev/input/event*`, `/sys/class/sensors/` if present, sensor-hub/accelerometer/gyroscope device-tree nodes, kernel config, modules, dmesg/journal probes, udev/input permissions, enabled clocks/regulators and any accessible vendor sensor hub interface. Do not mistake an ordinary touchscreen input device for an accelerometer.
- Compare device events in **four real physical handset positions**, with timestamps, axes and orientation matrices. If `iio-sensor-proxy`, `monitor-sensor` or libinput tools exist, test them in the actual login/user session; check permissions, `has-accelerometer`, source data, udev tags, environmental overrides and D-Bus sensor service readiness. If missing, inspect raw driver interfaces before spending time building a fake sensor daemon.
- Identify vendor Samsung sensor-hub ABI versus generic IIO; build the smallest honest adapter only if genuine data are accessible. Document orientation transform, handedness, axes, calibration and thresholds/debounce. Treat no hardware data as `BLOCKED_SENSOR_INTERFACE` rather than synthesizing device motion.

### 5.2 Orientation policy and compositor output

- Trace quick-settings selector → persisted config → orientation policy controller → input event mapping → compositor Wayland output transform → physical framebuffer scaler/`nuxel-wl-fb` bridge and touch coordinate matrix → app viewport/keyboard/OSK. A CSS `rotate(90deg)` alone is **not** whole-device rotation.
- Check for stale startup state (UI shows Auto while policy remains forced portrait), duplicate providers, DBus signal subscriptions, hard-coded portrait backend, exception swallowing, missing transform support in old renderer, and loss of events while apps are fullscreen.
- Implement seven modes with correct filtering and user override precedence. Four forced orientations must work **without sensor** if compositor/display/input permits; three auto modes consume real sensor orientation. Apply hysteresis/dwell time to avoid oscillation when phone held diagonally, but do not freeze Auto forever.
- Coordinate with A67 hardware acceleration: any output transform and physical framebuffer bridge optimizations must preserve full framebuffer bounds, stride, clipping, redrawing and touch/gesture mapping. Prevent display tearing, loss of global nav, sideways touch regions, letterboxing, wrong WebKit viewport, cutout infringement and stuck apps. Portrait ↔ landscape rotation should apply to browser, launcher, Settings and SnekByte safely, or correctly report per-app orientation constraints; don't silently override owner policy.
- When accelerometer data are blocked, still repair forced-mode selector, persist settings, provide clear truthful status (`Auto: sensor unavailable`) and a precise diagnostic for future driver work. No simulated gyro passed as physical rotation.

### 5.3 Physical orientation acceptance

- Verify each of the four forced modes with timestamped screenshot/geometry/input tests at real active panel output.
- Hold phone upright, upside down, rotate left, rotate right: record sensor readings and event timestamp; verify all three auto mode policy constraints **with actual physical motion**, without a manual transform in the test path.
- Test portrait/landscape interactive taps (top left, right, nav, OSK), status/notification shade, SnekByte touch, browser address bar, camera navigation, minimize/Home. Test after resume/screen off/lock/unlock and owner-approved cold reboot.
- If a driver is not present: produce `SENSOR-HARDWARE-GAP.md` with expected DT/driver/firmware interface, evidence and controlled separate implementation proposal; do not claim auto-rotation passes.

## 6 — CROSS-SUBSYSTEM INTEGRATION: A68 MUST NOT REGRESS A67

Back/Home, audio and rotation can all change **focus**, **session ownership**, **Wayland surface state**, or the main loop. Audit shared root causes rather than stitching three independent hacks:

- If pressing Back visually reveals four icons over the app, record the renderer/layer ordering and patch the authoritative task transition, **not** a per-app `z-index` or CSS opacity.
- The compositor must retain focus and input responsiveness after app-to-Home transitions; audio preview and sensor D-Bus handlers must **not** block the UI event loop (avoid synchronous sleeps, blocking process invocations or poll loops).
- Preserve accelerated software/GPU render path established by 16000, `nuxel-wl-fb` output scaling, frame pacing, CPU idle and thermal safety. Test FPS/jank before and after with the same workload if performance changes are material.
- Preserve A65/A66 fullscreen browser escape and bottom-nav compositor visibility while rotating; do not allow fullscreen WebKit surfaces to intercept global Back/Home/Tabs or pull-down gesture.
- Existing SnekByte latest must stay intact; Home should background/pause according to existing policy, return should restore gameplay and audio if available, not relaunch or reset the save. Four desktop icons must **never** overlay the game or Settings.
- Keep power/lockscreen semantics, battery percent, working DNS/TLS/Wi-Fi, Camera app escape, app switcher, native package manager/Flatpak launcher, onscreen keyboard and haptics.

### Test regressions systematically

Build deterministic automated tests for shell navigation state machine, race/ordering, app history handoff, Home focus ack, dock visibility invariant, audio sink selection and volume/mute transitions, orientation policy filters, matrix math, sensor-loss fallback and launch/service restart. Avoid hard-coded sleep-dependent tests. Where appropriate, use fake app routers for tests **but physical PASS requires actual S10+ verification**.

## 7 — SAFE PATCH/DEPLOY STRATEGY

Implement in independent, rollbackable batches. For each, run lint/static tests, unit tests, integration tests, then scoped live service deployment with Fedora USB transport; validate actual installed bytes/config with checksums and read-back. Explicitly identify whether a particular process is running new vs stale code. Do not break currently working HTTPS browser or audio/device session on service restart.

- **A68a Navigation/focus/dock**: restore true in-app Back, Home transition, visual/hit-test dock gating, browser/native routing contracts.
- **A68b Sound path**: ALSA/codec route (if possible), PipeWire/WirePlumber session, volume preview, persistence.
- **A68c Rotation**: sensor diagnostics, seven-mode UI/policy, compositor/output/touch transform, persistent settings.
- **A68d Integration**: cross-feature tests, manual acceptance, owner-approved reboot, performance checks and evidence packaging.

On a dangerous service restart, ask approval and ensure USB console stays alive independently. Never alter kernel modules, proprietary drivers or boot partitions as an unreviewed opportunistic fix. If a change causes launcher/input regression, rollback immediately via out-of-band connection and annotate the cause.

## 8 — PHYSICAL ACCEPTANCE MATRIX (REQUIRED)

Each row must include `baseline reproduction`, `code change`, `test command`, `actual physical result`, `evidence file`, `PASS_PHYSICAL | PASS_OFFLINE_ONLY | FAILED | BLOCKED_HARDWARE | NOT_TESTED`, and precise blocker if any. **No generic PASS.**

| ID | Real S10+ acceptance test | Expected result |
|---|---|---|
| A68-P01 | Browser A→B→C, Back once | Browser to B; stays foreground; Home dock invisible |
| A68-P02 | Browser Back again | Browser to A; stays foreground; Home dock invisible |
| A68-P03 | Browser Back at root | Browser backgrounds, true Home desktop and four icons frontmost |
| A68-P04 | Settings root→child→grandchild, two Back taps | Return to root in foreground with dock hidden |
| A68-P05 | Settings Back at root | Settings backgrounds, true Home shown |
| A68-P06 | Browser with OSK visible, Back | Keyboard closes first; app stays visible |
| A68-P07 | Penguin Home from browser fullscreen | Actual wallpaper/widgets/icons launcher foreground; browser preserved |
| A68-P08 | Penguin Home from Settings, SnekByte, native app | Always Home frontmost, never a dock-over-app artifact |
| A68-P09 | Tabs switch back to background browser | Existing browser state returns and dock disappears |
| A68-P10 | Long Back on non-Home app | Only targeted app closes safely; no shared-host or Home kill |
| A68-P11 | Long Back while Home frontmost | Home and critical shell continue running |
| A68-P12 | Repeated quick Back/Home/Tabs changes | No mixed layers, duplicate apps, input lock or compositor crash |
| A68-P13 | Read audio card and PCM topology | Proven devices and chosen physical speaker route, or precise blocked status |
| A68-P14 | Local test sound at low, then medium volume | Owner hears real sound at corresponding physical output; no sudden blast |
| A68-P15 | Volume keys +/- and mute | Actual sink changes, audible preview only if enabled and unmuted |
| A68-P16 | Browser/app sound playback | Actual audible output via same sink after user action |
| A68-P17 | Power cycle audio service/session as safely approved | Sound route and volume persist; no busy loops |
| A68-P18 | All four forced orientations | Real output and touch coordinates rotate appropriately |
| A68-P19 | Automatic all modes while physically turning phone | Actual sensor-controlled rotation, or explicitly blocked with proof |
| A68-P20 | Auto portrait/landscape filters | Correct allowed orientation pairs, no false forced lock |
| A68-P21 | Rotate while browser or SnekByte is foreground | Responsive rendering, insets and global navigation; no desktop dock leak |
| A68-P22 | Rotate then lock/wake / keyboard | Correct viewport, touch, keyboard, battery and unlock |
| A68-P23 | Wi-Fi/Google.nl HTTPS regression | Working Internet, DNS, TLS and browser retained |
| A68-P24 | Before/after render/latency check | No meaningful new compositor stall or sluggishness |
| A68-P25 | Owner-approved reboot / resume | Back/Home/dock, audio config and orientation setting survive; USB console recoverable |

Where genuine hardware cannot be made functional, leave precise `BLOCKED_HARDWARE` and a non-destructive next-step investigation—not an unverified fake demo.

## 9 — OUTPUT CONTRACT / REQUIRED ARTIFACTS

Save under repo-relative `docs/a68-17000/` (or established Nuxel diagnostics structure) and provide links/paths:

1. `BASELINE-REPRODUCTIONS.md` — screenshot/video references, running builds/hashes, four owner-reported failures, service/process owners.
2. `NAVIGATION-STATE-MACHINE.md` — single source of truth, Back precedence/return semantics, Home foreground activation, dock invariant, native/WebKit IPC, app focus diagrams and failure fixes.
3. `AUDIO-SPEAKER-ROUTE.md` — driver/card/PCM/codec evidence; ALSA/UCM/PipeWire routing, exact audible tests, volume and any blockers.
4. `ROTATION-SENSOR-TO-PANEL.md` — actual sensor nodes/events, mode UI/state mapping, compositor transforms, panel bridge and input matrix, seven-mode tests or hardware blocker.
5. `TEST-MATRIX.csv` and `TEST-MATRIX.md` — the full 25 physical acceptance cases with evidence; clearly separate offline tests.
6. `DEPLOYED-ARTIFACTS.sha256`, `CHANGES.md`, executable/safe `rollback` instructions, and a brief next-actions summary.
7. Committed changes in logically separated commits/patches A68a–A68d, excluding owner-unrelated working tree modifications.

Final user-facing report must begin with **what is physically fixed** and **what remains blocked**, not a list of code files. Include exact actual test results and sample command outputs without fabricating evidence. Say when the physical phone was unavailable or owner did not confirm audio.

## 10 — EXECUTION ORDER — BEGIN NOW

1. Confirm USB Live Console & backups, exclusive device ownership, and currently working Wi-Fi/browser.
2. Reproduce **wrong Back / broken Home / dock overlay**; identify navigation source-of-truth and compositor stacking problem.
3. Implement **A68a** and physically verify P01–P12. Do not proceed if launcher becomes inaccessible.
4. Diagnose real **audio output** from ASoC/ALSA up through PipeWire and apps, apply minimal root-cause patch; physical sound check P13–P17.
5. Diagnose **rotation** from sensor/input to compositor and bridge, restore seven-mode policy and live transforms if supported; P18–P22.
6. Verify existing networking, responsiveness, lockscreen, latest SnekByte and owner-approved reboot (P23–P25); package evidence and rollback.

**NO MORE HOME ICONS FLOATING OVER APPS. NO MORE FAKE BACK. NO MORE “AUDIO WORKS” WITHOUT SOUND. NO MORE “AUTO” WITHOUT REAL SENSOR DATA.**

**🐧 NUXEL 17000 — BACK. HOME. SOUND. SPIN. PENGUIN PWNAGE.**
