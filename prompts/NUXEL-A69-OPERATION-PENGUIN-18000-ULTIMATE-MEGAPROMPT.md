# 🐧⚡ NUXEL A69 — OPERATION PENGUIN 18000: COMPLETE THE PHONE

## INSTANT BATTERY • ONE NAV BAR • REAL SOUND • BT SPEAKER • USB-C AUDIO • GPS/MAPS • NFC • SENSOR ROTATION • VLC/MP3 • SPEED • ANIMATION • FOREGROUND APPS

**Execution agent:** DeepSeek-v4-pro-thinking through the owner's configured CodeSeeQ (`csft`) on Fedora laptop; also suitable for GPT-5.6 Sol with equivalent approvals.  
**Physical target:** Samsung Galaxy S10+ **SM-G975F / beyond2lte / Exynos 9820**, Nuxel independent Fedora ARM64 userspace and its *existing working* Samsung downstream Linux 4.14 kernel. Detect actual deployed revision and software versions; historical notes are leads, not verified present state.  
**Mission type:** **Implement, diagnose, safely deploy, and physically verify**. This is **not** a request for only a plan, a UI mockup, or a scripted green test. Do not promise hardware functionality that cannot be validated.  
**Name:** 18000 — *Operation Penguin Complete-the-Phone / Sensory & Media Hyper-Integration*.  
**Owner observation:** Network, TLS, browser, internet and launcher performance improved across 14000–17000. Prior agent(s) have repeatedly failed to finish audio and auto-rotation, and new UI integration failures remain. Do not regress the success.

---

# 0. NON-NEGOTIABLE MISSION CONTRACT

## Reported failures: translate every item into verifiable work

**A69-01 — Cold-boot lockscreen battery:** Lockscreen **incorrectly says 0% for several minutes after reboot**, while unlocked top status bar immediately reports the true value. Fix initialization, source sharing, caching/race/IPC and authoritative status without manufacturing a percentage.

**A69-02 — Double / overlapped triple navigation:** There are **two copies of bottom Back, Penguin Home and Tabs buttons overlaid** (owner references screenshot). Find and eliminate duplicate rendered hosts while preserving the one true global nav service and working touch/haptics, across launcher, apps, browser, OSK, lockscreen and rotation.

**A69-03 — Speaker audio:** **Still NO audible audio.** Trace driver → codec/clock → ALSA/ASoC route → UCM profile → PipeWire/WirePlumber → app output → speaker amplifier; make actual speaker output audible if support exists. Never report success from API-level playback alone.

**A69-04 — Rotation:** **Still NO real sensor-driven auto rotation.** Diagnose gyro/accelerometer/sensor hub, kernel input/IIO/custom interfaces, user-service orientation, compositor transform, framebuffer bridge and touch remap. Fix all feasible pieces without risky kernel swap. Preserve all seven orientation policies from earlier missions.

**A69-05 — GPS & Maps:** Determine whether **real GNSS/GPS** yields a satellite fix. Repair/init GPS data path if present; upgrade **Nuxel Maps** into a genuinely functional map with real online map tiles, attribution, drag/zoom/search, optional route if supported and an explicit location-permission flow; never silently substitute network-IP estimate as hardware GNSS.

**A69-06 — NFC:** Inventory NFC hardware and Linux interface, initialize lawful firmware/driver if available, implement an honest Nuxel NFC panel/toggle/tag-reader, and demonstrate scanning an owner-controlled NFC tag if supported. Do not claim tap-to-pay, secure-element emulation or card emulation without real verified support.

**A69-07 — Bluetooth + manager + speaker:** Initialize HCI, rfkill, BlueZ, firmware and authorization/session integration, implement usable Bluetooth manager (power, scan, device list, pair, trust, connect/disconnect, forget, errors) and **actually pair and play sound through the owner's Bluetooth speaker** when stack supports it. Test A2DP with PipeWire/WirePlumber and switching default sinks.

**A69-08 — USB-C headset & USB-C-to-3.5mm adapter:** Detect/type distinguish **digital USB Audio Class DAC/headset** from a passive analog USB-C adapter. Support real compatible headsets/adapters, automatic safe sink selection, and return-to-speaker on unplug. The S10+ also has a separate native 3.5mm connector; do not confuse these routes.

**A69-09 — Media player + VLC:** Install a genuine usable MP3/music player (prefer a lightweight Fedora ARM64 package that integrates with the Nuxel shell) **AND install VLC**, with .desktop registration, real local media import/play/pause/seek, MP3 decoding, volume, background handling, metadata/art if accessible. Verify genuine runtime, not just RPM presence. Avoid gratuitous packages/codecs.

**A69-10 — Volume latency:** Hardware volume rocker response feels delayed. Measure input event → policy → mixer update → OSD/haptic → audible output. Remove avoidable waits/debounce, fix UI thread stalls; correct key-repeat and race ordering, preserve volume limits and per-route policy.

**A69-11 — More UI responsiveness:** Benchmark app launch latency, navigation, scroll/touch event delay, animation pacing, compositor frame delivery, memory, CPU and thermal budgets. Incrementally optimize real bottlenecks rather than adding empty performance knobs.

**A69-12 — Smooth animations:** Add beautiful restrained Nuxel transitions for desktop swipes, app open/close, returning Home, app drawer, Tabs/recents and approved menus/dialogs without breaking input mapping, kiosk/fullscreen behavior, performance, or low-motion accessibility.

**A69-13 — App drawer foregrounding:** Tapping an app in the Applications window currently appears to open it **behind that window**. Change shell focus/workspace/surface ordering so selected app appears immediately in front and Applications drawer dismisses. Already-running apps should be raised, not duplicated.

### How to label truth

Only use statuses **`PASS_PHYSICAL`**, **`PASS_DEVICE_RUNTIME`** (narrower evidence with actual device but no owner-observed use), **`PASS_OFFLINE_ONLY`**, **`BLOCKED_HARDWARE`**, **`BLOCKED_DEPENDENCY`**, **`FAILED`**, **`NOT_TESTED`**. A software config, package install or desktop emulator test is never automatically `PASS_PHYSICAL`. Distinguish **owner-reported** and **agent-observed**. Never call a subsystem finished because a spinner stopped.

### Scope protection and hard no-go boundaries

- Keep successful **Wi-Fi, real IP/DNS/TLS/HTTPS Nuxel Browser, native app launching improvements, USB Live Console, boot chain, lockscreen art, penguin controls, SnekByte, A64 launcher sizing, A67 smoothness gains and existing working paths**. Avoid reinstalling the OS, migrating Fedora, doing arbitrary systemwide upgrades, or re-running old missions blindly.
- No flashing, bootloader writes, partition repartition, kernel/dtb/driver/firmware replacement, modem/APN/AT provisioning, non-consensual location collection, NFC payment/security-element tinkering, or broad privileged `chmod`. No kernel v6 migration; it is a different mission.
- If a specific vendor firmware image is missing, identify exact chip, source/provenance/license, ABI and deployment mechanism. **Never silently extract or ship proprietary blobs from random websites.** Owner permission before installing or altering any firmware.
- Never destroy working lockscreen or primary navigation to test a feature; stage changes with reversible deployment and one device writer. Do not remotely close the only usable recovery session. Approve risk before restarts/reboots/privileged package transactions. Keep internet and ssh/USB connectivity working.
- Avoid any location, MAC address, paired-device ID, network credential or file path containing private information in shared evidence; anonymize outputs before publishing.

## Engineering quality requirements

1. Source audit + live state audit first. Confirm current commit, dirty files, PIDs, unit files, deployed hashes, foreground/window stack, existing audio and sensor interfaces, persistent startup ownership, service health and package origins.
2. Preserve current WIP (no `git reset --hard`, no blind zip overwrite). Create feature branch/worktree with a rollback plan and a controlled install manifest. One deploy owner; no parallel agents targeting the phone.
3. For each A69 issue: minimal reproduction → traced code/service/kernel owner → root cause evidence → minimal cohesive fix → unit/integration tests → staged dry validation → scoped on-phone deployment → **physical proof** → cold-boot regression when approved.
4. Instrument exact paths; prefer **one authoritative state owner** for UI nav, battery, volume and app focus. Do not layer another timer/duplicate service on the same symptom.
5. Product stability matters more than a superficial PASS. Subsystem hardware blockers must be explicit, with concrete technical next steps, without breaking unrelated working features.

---

# 1. FIRST: REAL DEVICE PREFLIGHT, SNAPSHOT, INVENTORY AND ROLLBACK

Before changing the phone:

1. On Fedora, establish known-good **USB Live Console**, test independent recovery even if the UI freezes, log transport access and who owns the session. Keep a known-good restore bundle ON THE LAPTOP and prove scripts work on a disposable staging tree. Do not mistake adb/ssh availability on the laptop for proof the phone remains accessible.
2. Identify actual phone kernel, userspace, display pipeline, input control services, audio stack, GNSS/NFC/BT enumeration, kernel logs, systemd/user-session DBus, uncommitted changes. Capture baseline screenshots/video of duplicated nav and app drawer backgrounding if possible. If user screenshot is absent in agent workspace, **do not invent its exact pixels**—reproduce and capture directly.
3. Back up only files involved in planned patches—boot unaffected—plus unit states, related RPM manifest, app registry, launcher assets and last-known-good service configurations. Sha256 each item, record permissions, versions, rollback command and **tested recovery route**.
4. Inventory background app/compositor owners and known performance baseline from A67; do not deploy entire other branches/zip archives.
5. Create `docs/a69/` containing `PREFLIGHT.md`, `LIVE-VS-REPO.md`, `RISK-AND-ROLLBACK.md`, `requirements.csv`, `test-matrix.csv`, `observations/`, `benchmarks/`, sanitized `logs/`, and `FINAL-STATUS.md`.

Read-only commands **on the phone** (execute through the confirmed device console, adapting to installed tools and privileges; these are examples, not a bulk unreviewed script):

```bash
uname -a
cat /etc/fedora-release 2>/dev/null || true
ps -eo pid,ppid,user,stat,pcpu,comm,args | grep -Ei 'nuxel|phoc|wayland|webkit|pipewire|wireplumber|pulse|blue|gps|geoclue|sensor' | head -140
systemctl --user --no-pager --all list-units --type=service 2>/dev/null || true
systemctl --no-pager --all list-units --type=service 2>/dev/null | grep -Ei 'nuxel|blue|gps|geoclue|audio|sensor|nfc|power' || true
find /sys/class/power_supply /dev/snd /sys/class/sound /sys/bus/iio/devices /sys/class/bluetooth /dev/bus/usb -maxdepth 2 -print 2>/dev/null | head -200
ls -l /dev/tty* /dev/nfc* /dev/i2c-* /dev/hci* 2>/dev/null | head -100
rpm -qa | grep -Ei 'alsa|ucm|pipewire|wireplumber|bluez|gpsd|geoclue|nfc|vlc|mpv|player|sensor' | sort || true
```

Review and redact command output, including actual Bluetooth device names and sensitive peripherals. Use `/dev/tty*` discovery only to inventory device nodes; don't open random serial ports to probe proprietary modem devices.

## Deliverable: dependency ordering

The audio system is shared by **speaker + Bluetooth A2DP + USB DAC + VLC/media + volume preview**, so build one audio architecture and test routes serially. Fix app focusing/nav first or early so media and settings tests are escapable. GPS and NFC can be parallel **read-only** research, but deployments remain serial. Ensure screen and keyboard accessible throughout.

---

# 2. BATTERY ON LOCKSCREEN: REAL DATA BEFORE FIRST PAINT

Owner-observed discrepancy: the unlocked top bar shows the true battery percentage immediately, but initial lockscreen reads **0%** until minutes later. This strongly suggests divergent initialization or polling, not necessarily an unready kernel battery driver. **Prove instead of assume**.

Trace:
- Which process reads `/sys/class/power_supply/.../capacity`, `upower`, DBus, proprietary battery bridge or cached metrics? Enumerate actual power_supply `type`, `present`, `status`, `capacity`, `voltage_now`, `energy_now`, and valid range. Device may expose multiple supplies; choose battery not charger. Avoid assuming `BAT0` or hardcoded path. Handle permissions carefully.
- At what monotonic timestamps is accurate capacity first available from kernel; battery service; top status bar; and lockscreen JS/GTK? Capture cold boot time series with exit status, values, DBus signal timestamps and process readiness. Distinguish `0`, missing, timeout, `null`, NaN, refused IPC and stale subscription.
- Does lockscreen start before metrics daemon, fail initial IPC, subscribe too late, use a separate placeholder `0`, or defer update until unlock? Inspect JS bridge lifecycle and service startup dependencies.

Fix: single **authoritative battery event/service** consumed by top bar and lockscreen. Read immediately on boot and when lockscreen mounts/wakes, publish event on actual changes, reconnect subscriptions across service restarts, avoid minutes-long polling fallback. If fresh reading not yet available, show neutral **`--%` / `Checking battery…`** (or timestamp-labelled last verified value) rather than dishonest 0%. After first valid reading, update immediately, including while still locked. Never display last-known reading as current without freshness metadata. If actual sensor reports 0, show true 0; do not assume always wrong.

Evidence: cold boot record with lockscreen 0s/2s/5s/10s and matching kernel/topbar values; repeat with screen off/on and battery service restart (owner-approved). Acceptance: correct value as soon as kernel exposes it, with no fake 0 window.

---

# 3. SINGLE GLOBAL NAV BAR, SINGLE SHELL OWNER: ZERO DOUBLE-BUTTON OVERLAPS

The owner reports **two overlapping sets** of triple buttons. Verify whether duplicate appearance is caused by:
- two independent shell processes/Wayland surfaces; repeated app-host embedded footer and globally overlaid nav;
- re-mounted WebKit/GTK DOM fragments, stale cached bundles after startup, listener duplication, or two compositor layer surfaces with same namespace;
- a screenshot showing multiple wallpapers or accidental CSS background icons vs a genuine duplicate service; UI scaling/rotation creating ghost copies; framebuffer bridge stale rects;
- screens switching Home/Apps/Browser/Settings while both shells believe they own navigation.

Map authoritative hosts/surface layers and touch input regions; build a one-row table: **launcher Home**, **app drawer**, **WebKit browser**, **Settings**, **SnekByte**, **native apps**, **system modal**, **OSK visible**, **lockscreen**. Each row must have exactly **one allowed nav host** or an explicit lockscreen policy. Guarantee exactly three physical controls Back / Penguin Home / Tabs with preserved haptics on touch-down. Do not hide both bars to make duplicates disappear. Ensure global shell controls remain above user apps in supported non-kiosk mode and don't create a native-app focus trap.

Use compositor-appropriate surface/layer ownership, stable widget lifecycle and unique event subscriptions; do NOT rely on HTML `z-index` to out-rank unrelated Wayland windows. Introduce automated assertion/instrumentation `nav_host_count == 1` after startup, route changes, app open, OSK show/hide, lock/wake and orientation change. Delete obsolete duplicated injected nav only after confirming global replacement works.

**Back/Home semantics must remain correct (A68):** Short Back first dismisses relevant transient/keyboard, then navigates in focused app; at logical route root, *next* press minimizes that app to real launcher. Penguin Home immediately backgrounds the current app and focuses the actual launcher/wallpaper/widgets/dock, not four icons over a still-visible app. Tabs opens live recents switcher. Long-Back kills **foreground non-system app only** when explicitly intended and cannot kill shell/launcher/lockscreen. Dedicated global controls must work from Nuxel Browser/native apps and not disappear when text input is focused.

Test 20 screen/app transitions and 10 cold lock/wake cycles. Verify touch hit boxes do not double-dispatch, haptics fire on pointerdown and no duplicate GPU surfaces remain.

---

# 4. ONE AUDIO PIPELINE: SPEAKER FIRST, THEN BLUETOOTH, USB-C, AND MEDIA PLAYERS

## 4A. Diagnose **physical speaker audio** (not just green audio service statuses)

Previous 15000/17000 missions did not get sound working. **Do not repeat package-reinstall guesses.** Draw current exact path:

`Exynos SoC I2S/PCM and audio DSP? → ASoC card/machine driver → codec/amp/clock/power routes → ALSA card/PCM/control/UCM → PipeWire/WirePlumber (or actual audio server) → application stream → real speaker`.

Identify actual card and codec/chip using `dmesg`, device tree compatible properties, `/proc/asound/cards`, `/proc/asound/pcm`, `aplay -l`, `amixer -c N scontrols`, `alsaucm listcards` and UCM device routes. Avoid asserting a specific Wolfson/Cirrus chip without confirming hardware. Inspect driver probe failures, missing firmware/topology, DAI link binding, mute/amp-enable GPIO, analog routes, mixer volume and permissions. Treat reported route changes as unverified until physically audible.

Safe tests (run on PHONE, with owner-approved moderate volume to avoid speaker/headphone damage):

```bash
cat /proc/asound/cards 2>/dev/null || true
cat /proc/asound/pcm 2>/dev/null || true
aplay -l 2>/dev/null || true
arecord -l 2>/dev/null || true
wpctl status 2>/dev/null || true
pactl list short sinks 2>/dev/null || true
systemctl --user status pipewire wireplumber --no-pager 2>/dev/null || true
```

Then produce a low-level sine/beep/wav with **controlled amplitude** using appropriate hw/plughw backend and documented UCM profile, plus a PipeWire stream, VLC/mpv and browser audio. Record route, device, volume, duration, and human-observed audible result. If no ALSA card or codec route exists, document exact downstream driver/firmware/device-tree blocker; don't promise hardware works. Avoid random `amixer` write scripts that set speaker amp to unsafe gain.

## 4B. Fix hardware volume rocker latency

Trace physical kernel input event or evdev → event dispatcher → Nuxel volume policy → mixer/stream volume → feedback OSD and vibration → audible change. Collect ≥30 presses at idle and app/browser load, log timestamp differences, p50/p95 and dropped/duplicated key events; use properly synchronized monotonic clocks. Correct debounce (avoid hundreds-ms click delay), main-thread blocking, DBus queuing, async awaits and JS `click`/pointerup misuse. Show near-immediate OSD on keydown while real audio stream follows, then reconcile errors. Support press-and-hold repeats without runaway increments. Respect max safe volume and per-route volume memories; avoid blasting Bluetooth on connect.

## 4C. Bluetooth controller and Nuxel pairing manager

**Do not assume Wi-Fi functioning means Bluetooth firmware/transport is automatically initialized.** Inspect kernel transport, device tree, HCI UART/USB/SDIO as actually present, rfkill, `bluetoothctl list`, `btmgmt info`, `hciconfig` when present, journal and `dmesg`, BlueZ daemon startup, DBus adapter objects, firmware provenance, coexistence with Wi-Fi, permissions and discoverable state. Confirm adapter powers on and actual LE/classic scanning sees a known nearby speaker (owner-controlled). Bluetooth identifiers must be sanitized in evidence.

Manager UI: show state `unsupported / initializing / off / scanning / paired / connecting / connected / disconnected / error`; list discoverable devices with category and RSSI if real, pair with honest PIN/confirmation if needed, trust/forget, connect/disconnect, retry and error messages. No perpetual “Connecting”; clean scan start/stop, timeout, adapter power toggle, dynamic connection state after reconnection/reboot. Integrate GTK/DBus app shell, keyboard and navigation.

**Audio acceptance:** owner pairs a real Bluetooth A2DP speaker; `bluez5` endpoints visible to WirePlumber; available A2DP sink selected (SBC as appropriate fallback); play actual MP3/known beep at safe volume; pause/resume, adjust volume, disconnect, default sink returns correctly, reconnect works after reboot if previously trusted. Separate BT *pairing* from BT *audio* statuses—do not mark either done from the other. Optionally exercise AVRCP if supported. Never fake output by playing through phone speaker.

## 4D. USB-C headset and USB-C-to-jack DAC

Classify the **actual accessory** before writing code:
- **Digital USB-C headset / active USB-C-to-3.5mm DAC:** phone must present USB host role; appropriate USB enumeration; kernel `snd-usb-audio` (or actual USB audio driver); ALSA card appears; PipeWire node/sink; button/mic support if provided; hotplug role handling.
- **Passive analog USB-C adapter:** requires physical analog audio accessory mode/Type-C mux support and cannot be made to work by installing `snd-usb-audio`. Report `UNSUPPORTED_ACCESSORY` when hardware lacks analog mode; recommend a compatible active DAC, rather than misrepresenting a missing USB device as a software bug.
- **Separate physical 3.5mm jack:** identify device's actual analog headset path independently and test if a jack is available. It is not equivalent to USB-C.

Implement device-change notifications, safe auto-switch policy, route selection and return-to-speaker upon disconnect; respect per-sink volume, mic permission and no sudden jumps. USB DAC/adapter must not break USB Live Console or phone charging/host roles: **do not switch to host mode if doing so disconnects the ONLY recovery transport**. Reconnect USB console and verify rollback before testing role switches, with owner permission. Test two devices where available and distinguish unavailable test equipment from implementation failure.

---

# 5. REAL ORIENTATION / ACCELEROMETER / GYRO: COMPLETE THE 4.14 PATH

The phone physically has motion sensors, but Linux 4.14 Nuxel may lack active vendor sensor-hub userspace and compositor transform. Trace these separately:

1. Kernel/device tree and vendor sensor service: actual `iio`/`input`/`sensors_class`/`/dev` exposures, interrupts, device probes, firmware and CAL offsets. Check accelerometer raw axis changes when owner rotates phone, and whether gyro data changes; distinguish accel orientation (gravity vector) from gyro angular velocity.
2. Detect whether sensor hub is supported but only exposed through legacy Samsung interfaces or Android-specific HAL that Fedora services don't consume. Investigate lawful compatibility integration on existing kernel, safe read-only first. Do not issue undocumented control IOCTLs or load random binary HALs.
3. Sensor event service: produce normalized orientation states with calibrated axes for S10+ chassis, debounce/hysteresis, stable 90/180/270 transitions, no false rotations from brief movement; respect lockscreen and app policies.
4. Wayland/Phoc/compositor output transform, custom 720×1520 software bridge vs 1440×3040 panel (verify current mode), pixel buffer aspect/stride/scale; touchscreen coordinate transforms for each orientation; OSK, status/nav bars, browser and game viewports.
5. Quick Settings/Home Settings must expose **seven coherent modes**: Forced Portrait, Forced Portrait Inverted, Forced Landscape Left, Forced Landscape Right, Auto All, Auto Portrait, Auto Landscape. Correctly distinguish forced vs automatic. Persist selected mode across wake/reboot. Detect nonrotatable native apps and expose honest limitations.
6. Test forced orientation even if physical sensors blocked; test actual live auto flips by physically rotating phone if readings exist; verify touch targets, audio controls, nav, lockscreen, map and text keyboard after rotation. Do not use an “accelerometer simulation” to certify physical rotation.

Deliver `docs/a69/ROTATION-HARDWARE-BOUNDARY.md` listing sensor driver, device, raw sample proof, normalized event, compositor/bridge results and failure stage. **Do not start kernel v6.x migration.** It does not inherently fix legacy Samsung firmware/ISP/sensor integration.

---

# 6. GPS/GNSS AND NUXEL MAPS: REAL FIX, REAL MAP, PRIVACY BY DESIGN

## 6A. Detect existing hardware & data path

Inspect kernel GNSS drivers, systemd units, GPS device nodes, relevant DT entries, firmware loader, vendor GNSS transport/protocol, GNSS HAL use, gpsd package/service and a potential geoclue provider. Hardware type is **unknown until device inventory**; don't guess chip. Check `gpsd -V`, `gpspipe` if present, serial authorization (only **identified** GNSS device, not arbitrary modem tty), debug logs and time/location sources. Do not enable cellular data, dial a modem, write baseband settings or issue unexplained AT commands.

For satellite fix: with explicit owner permission and ideally outdoors, record valid NMEA/GNSS positions with fix state, accuracy/HDOP, satellites/time and timestamps. Establish TTL, stale-fix handling, permission and data path. A Wi-Fi/IP geolocation result is **not GPS**; network location can be a separately labeled fallback only with consent. Without hardware GNSS access, mark `BLOCKED_HARDWARE` with transport/firmware specifics and complete map functionality independently.

## 6B. Deliver a usable Maps app

- Maintain existing Nuxel app identity/icon and registry or fix broken entry; choose an existing embedded WebKitGTK app or native implementation based on actual architecture, not a new duplicate app.
- Show real map tiles from a lawful provider (with license attribution); don't hardcode an unapproved public service into an unthrottled crawler. Validate tiles via real HTTPS on phone, use proper User-Agent/policies/cache. For OpenStreetMap data, honor attribution and the tile service usage policy; distinguish OSM data license from specific tile host terms.
- Support pan/zoom, tap point, location search/geocoding using lawful API/rate limits, center-on-me when permission granted, an accuracy ring only when accuracy reported, loading/offline/error status. Optional directions/routing only if a real API/engine is configured—never draw fabricated turn-by-turn directions.
- Location permission must be user-facing, scoped and revocable; avoid background geolocation by default. No location log leaks.
- Make Home, Back, recents, keyboard, focus and app titlebar policies work. On Back, navigate within Maps where possible, then return Home at route root in accordance with global shell semantics.
- Acceptance: real world tiles load and pan/zoom, search returns real result, taps work, location permission can be denied without crashing, physical GNSS position shown only with a genuine fix; tested on S10+.

---

# 7. NFC: CORRECT DEVICE DRIVER, TRUSTED TAG SUPPORT, HONEST LIMITS

Detect chip and bus from DT/sysfs (I2C, SPI, UART as relevant), kernel NCI driver and device nodes, firmware/probe/reset GPIO, power rails, RF field state, service conflict with vendor Android components. **Do not assume a specific NXP/Samsung chipset**. Use `rfkill`, dmesg, sysfs, `nfc-list` only if `libnfc` setup is correct; Linux kernel NCI and userspace libnfc do not automatically mean the same transport is supported. Investigate and select supported protocol/daemon/API path.

Make a Nuxel Settings NFC section with truthful `unavailable / off / ready / scanning / tag found / error` states, toggle only when actual control exists, optional user-initiated NFC tag-reader app for *owner-controlled* NTAG/NDEF tag. Do not continuously poll RF without battery consideration. Parse safely, bound payload, reject malicious URL auto-open; show content and ask before opening externally. Never store private tag data in logs.

Physical acceptance: discover real controller, see relevant tag while held near correct antenna, show protocol/UID only if necessary and authorized, read a known NDEF text or URL, remove tag and return to idle, lock/unlock app remains responsive. If driver, firmware or controller unexposed under 4.14: identify exact missing link; mark `BLOCKED_HARDWARE`. **No secure-element emulation, payment credential operation, bank card transactions, cloning or bypasses**.

---

# 8. INSTALL ACTUAL MP3 PLAYER AND VLC, REGISTER AS REAL NUXEL APPS

Perform package capability check on the **phone's Fedora ARM64 system**, not the Fedora x86 laptop:

```bash
uname -m
rpm -q vlc mpv 2>/dev/null || true
dnf list --available vlc mpv 2>/dev/null || true
which vlc mpv 2>/dev/null || true
```

- **VLC is mandatory** where a compatible, installable repository package exists. Fedora lists VLC for Fedora 43; actual phone repo and architecture must be checked. Use `dnf --assumeno`/transaction preview and owner approval; do not blindly enable unknown third-party repos or import random RPM keys. Fedora VLC may use Qt GUI dependencies. Confirm `vlc` actual GUI starts within Wayland session, accepts input and plays supported local content with working exit/Home/Back. If broken due to genuine no GPU/codec/Qt plugin/audio limitations, record exact errors and workable fallback while keeping VLC installed if safe.
- **Separate usable MP3/music player**: prefer lightweight, genuinely available ARM64 player compatible with current GTK/Wayland stack, e.g. package present in repo; pick based on measured startup, memory and support rather than name alone. Alternatives include a small Nuxel GTK/GStreamer player if stock offerings unsuitable, but do not implement a fake player UI. Install actual decoding backend, play/pause/next/prev/seek/queue and folder import with proper sandbox permissions. Keep file paths private.
- Integrate both into Nuxel app registry, correct desktop IDs, icons, launch focus, task switcher, MIME handlers (`audio/mpeg`, etc.), media notifications and headset/Bluetooth output where supported. Avoid manually creating duplicate desktop entries if package already provides one.
- Owner-provided MP3/WAV content only; build a safe unlicensed test sine WAV when needed. Playback correctness requires audible sound, time/progress actually changing, seek works and no background launch trap.
- When speaker hardware blocked, separately test genuine decode/playback pipeline with observable PCM frames and clearly mark `AUDIO_HARDWARE_BLOCKED`; do not label media playback fully functional unless end-to-end output verified on a supported route.

---

# 9. VOLUME CONTROL AND AUDIO POLICY IN ONE PLACE

Consolidate hardware rocker, global slider/quick panel, onscreen preview, media stream, Bluetooth sink and USB DAC into **one audio state/controller**, with per-sink tracked volume and actual default sink selection. Implement immediate visible response to event receipt and deliver actual volume change promptly; on errors show route failure rather than lying.

Measure in multiple states: no app, browser fullscreen, SnekByte, video playback, music player, BT connected, DAC hotplug, screen lock/wake, rapid 10 taps and hold. Distinguish GUI redraw delay from mixer DBus delay and kernel/input autorepeat. Avoid volume preview causing unbounded audio-play queue or feedback recursion. Haptic click on press, if supported. Safety guard near max levels, especially headsets.

---

# 10. PERFORMANCE PASS 18000 — PROVE *MORE* SMOOTHNESS, DON'T BREAK 16000

Treat A67 hardware acceleration analysis as baseline, **not permission** to install random Mesa/Mali drivers, upgrade kernel, or patch systemwide `libEGL`. Record current rendering stack and whether hardware acceleration actually works. Measure 30–60s replicable workloads before/after:

- Home desktop swipe across workspaces, 20 app opens/closes, app drawer scroll/open, settings menu switches, typing in browser, notification bar, 3 SnekByte plays, map pan/zoom, volume repeat.
- Physical touch → input event → shell handler → buffer composition → present stages where visible. FPS, p50/p95/p99 frame times and input latency, CPU, memory, thermal steady-state; hardware stats only if exposed; note sample size.
- Identify redundant full-frame copies, CSS layout thrashing, giant icons/assets, blocking synchronous file/DBus calls, re-render loops, high-frequency battery/sensor polling, slow D-Bus replies and duplicate nav surfaces. Prefer damage tracking, cached images, bounded processes, async DBus, conditional repaints and efficient scaling.

Make improvements **only with reproducible before/after measurements and rollback**; refuse placebo animation if it hurts p95 latency, game FPS, UI consistency or battery/thermals. Prefer real physical performance over prettier loading spinners. If audio/kernel work conflicts with A67 path, isolate feature regressions, compare commits and revert only affected patch.

---

# 11. NUXEL ANIMATION DESIGN SYSTEM — RESPONSIVE, NOT PSYTRANCE

Implement restrained, crisp, pixel-friendly motion consistent with Nuxel Penguin aesthetics. Preserve existing app artwork and layout, especially SnekByte fullscreen and bottom global nav.

### Motion requirements

1. **Desktop/workspace swipes:** touch-following movement while dragging; smooth snap with short natural easing after release; no duplicate panels, no input-coordinate discontinuity, no giant parallax surfaces.
2. **App launch:** focused icon-to-app or subtle fade/scale transition only if compositor stack can support it. Most importantly the app must become **the actual focused foreground surface** before completion. Never let animation merely overlay an unraised app.
3. **Return Home / Back / app close:** small reverse transition; preserve app background process, keyboard state, Home wallpaper/widgets and dock layering.
4. **App drawer:** subtle slide/fade with correct surface ownership; app selection dismisses/demotes drawer, raises chosen app, then animation ends. Never leave drawer on top, never show dock over active fullscreen app.
5. **Tabs/recents:** coherent card slide/opacity transitions; never animate controls into untouchable overlay.
6. **Quick settings / menus:** minimal motion that does not delay interaction or fight an OSK or native GTK surface.
7. **Accessibility & preference:** provide a setting `Animations: Off / Reduced / Normal` (or honor desktop reduce-motion conventions where available); reduced/no motion must be instant, all app functions unchanged.
8. Use transforms/opacity on appropriate composited layers, avoid expensive full-screen blur/pixel overlays and forced reflow, guard animation cancellation and rapid repeated swipes/Back/Home, adapt to actual rendering path with explicit capability fallback.

As an initial *design target*, test roughly 120–220ms for most transitions, not a hard-coded requirement: device responsiveness beats animation duration. Never claim 60 FPS unless measured and physically delivered. Confirm no graphical stutter during mp3 playback, maps, or notification rendering.

---

# 12. APP DRAWER FOREGROUND LAUNCH: TRANSITION MUST BE ATOMIC

Current symptom: choosing an app in Applications window apparently launches it **behind Applications**. This is a focus/z-order and shell state bug, not necessarily an app crash. Trace launch controller → process/toplevel creation → Wayland surface map/focus → compositor raise/activation → app-drawer dismissal → global nav ownership → dock visibility. Determine exact source of truth; don't mask with arbitrary `sleep(1)`.

On application choice:

1. Validate registry entry, app id and launch permission; do not start duplicates when existing app can be raised.
2. Reserve desired focus target / pending activation token according to compositor protocols; on actual map/activation, **raise target to foreground**, focus keyboard/touch correctly, **dismiss App drawer behind it**, hide desktop four-icon dock, keep one global nav strip.
3. If app never maps/launch times out, stay in Applications with a truthful actionable error and allow retry. Never silently close app drawer on failed app launch.
4. If app is running in background, focus that same task reliably. If launched directly from Home dock, same contract applies. Handle both WebKit and native GTK/Qt windows.
5. Back from foreground respects in-app history, root returns launcher; Home always returns launcher; Tabs provides reselecting running apps. When an app closes, restore predictable Home/previous task, not an empty background or lost focus.
6. Test apps: Settings, Browser, SnekByte, Maps, Bluetooth manager, VLC, MP3 player and Camera (Camera must remain escapable even with unsupported capture).

Track compositor/window activation timestamp, target PID, surface id and before/after stack; verify actual phone visually and via compositor events. A DOM overlay alone is not a foreground fix.

---

# 13. REGRESSION GATES, SAFE DEPLOYMENT & RESTART ORDER

Suggested *reversible* implementation batches with explicit owner approvals:

**A69a** — cold-boot battery events + nav duplication + app foreground owner (stabilizes UI access).  
**A69b** — sound hardware diagnostics and safe ALSA/UCM/PipeWire routes + volume latency, without boot/kernel modifications.  
**A69c** — BlueZ HCI manager + A2DP + USB audio endpoints, built on verified A69b.  
**A69d** — rotation input/transform and seven modes, then GPS/Maps + NFC driver-aware app integration.  
**A69e** — real media packages/install/launch and music playback.  
**A69f** — verified performance improvements, animation design system and full cross-feature regression.

This order is flexible only with evidence; no deploying unfinished app dependencies, no simultaneous phone writers. Keep the phone connected to a recoverable console throughout. Device reboots occur **only after owner authorization**, with precise rollback and confirmation that status+navigation+USB path remain available.

### Physical acceptance matrix — implement automated capture plus human checks

Use IDs and evidence paths. Every item must be one of statuses defined above:

| ID | Requirement | Required physical proof |
|---|---|---|
| T01 | Battery at boot | Within first lockscreen render, real capacity or honest unknown; when top bar value known lockscreen matches promptly |
| T02 | Battery wake | Ten sleep/wake cycles, no minutes-long 0% bug |
| T03 | Single nav | No two copies over Home, Apps, Settings, Browser, SnekByte, VLC, Maps, keyboard or orientation |
| T04 | Back | In-app navigates; only at logical root next Back returns Home |
| T05 | Home | Penguin shows real launcher, app backgrounded, no desktop dock over app |
| T06 | Tabs | Recents foreground switch works, one nav bar throughout |
| T07 | App drawer | Click app -> correct foreground over drawer, on already-running and cold launch |
| T08 | Speaker | Owner can hear low-volume test on PHONE speaker; logs support route |
| T09 | Volume press | Hardware volume immediate visual response and measured/audio effective change |
| T10 | Volume hold | Repeated keys update correctly without stuck/lagging commands |
| T11 | Bluetooth adapter | Controller powered, scan and device listing work without fake device data |
| T12 | Bluetooth pairing | Owner speaker paired/trusted/connected and reflects true state |
| T13 | Bluetooth audio | Actual MP3 heard from BT speaker, switch/disconnect/reconnect |
| T14 | USB-C digital audio | Real detected DAC/headset works, plug/unplug routing, no recovery transport lost |
| T15 | Analog adapter | Actual adapter classified; works if hardware supports or precisely marked unsupported |
| T16 | VLC | Genuine VLC installed on phone, icon opens native app, correct focus and exit |
| T17 | MP3 player | Separate actual music player imported MP3, seek/pause/volume work |
| T18 | Audio output routes | Speaker, BT, DAC transitions honor per-route safe volume |
| T19 | Accelerometer/gyro | Real changing sensor readings on physical movement, or precise blocker |
| T20 | Auto rotation | Two actual orientations switch with correctly mapped touch, or documented hardware blocker |
| T21 | Seven rotation options | All policies selectable/persistent; forced modes work where display can rotate |
| T22 | GPS/GNSS | Genuine satellite fix outdoors with permission, or driver/path blocker documented |
| T23 | Maps | Real HTTPS tiles, attribution, pan/zoom/search; location consent truthful |
| T24 | NFC | Controller diagnosed, owner-controlled tag read, or concrete blocker reported |
| T25 | Desktop swipe animation | Responsive smooth snapping, cancel/reverse, no input drop |
| T26 | App transition animation | App focused before/during completion, no stale overlays |
| T27 | App drawer animation | Drawer dismisses when target launches; foreground correct |
| T28 | Motion settings | Off/Reduced/Normal preserve usable actions |
| T29 | Smoothness | Before/after quantitative p50/p95/p99 and CPU/battery/thermal constraints |
| T30 | Baseline Internet | Wi-Fi reconnect + DNS + TLS + https://www.google.nl in Nuxel Browser still works |
| T31 | Baseline game | SnekByte icon/fullscreen, input, speed and game navigation not regressed |
| T32 | Lockscreen | Penguin swipe/wake, screen-off lock, battery, exit routes remain correct |
| T33 | Native app access | Settings, Camera, browser and native GTK/Qt can always be exited |
| T34 | Reboot | Owner-approved 3 cold boots: key fixes persist; USB Live Console remains recoverable |
| T35 | Install health | RPM signature/dependency audit and app registry stable after refresh |

No imaginary metrics. Use `NOT_TESTED` where no physical speaker, USB audio accessory, NFC tag or outdoor GPS access is available. `PASS_OFFLINE_ONLY` for unit tests is valuable but not release success. If owner must run the test, state exact one-line action and expected confirmation. Never execute a massive system upgrade just because DNF is present.

### Final status to owner

Create `docs/a69/FINAL-STATUS.md` with:

- Live phone model/kernel/userspace/commit, connection method, stage timeline and list of actual modified files and RPM installs.
- `A69-01` through `A69-13` **root cause, implemented fix, tests, physical evidence, status, blockers and next action**.
- Exact sound chain state: ALSA card, UCM route, PipeWire sink, audible speaker/BT/DAC result; Bluetooth controller/firmware status; audio device-switch behavior.
- GPS GNSS-vs-network-location distinction, NFC controller/reader distinction, rotation real-vs-simulated sensor state.
- Performance table with frame times/input latency **before/after**; no unexplained speed-up percentages.
- Screenshots/video evidence: screen lock battery and nav single ownership, app drawer raise, maps, Bluetooth manager, music player and animation capture.
- Regression matrix incl. Wi-Fi/browser/TLS and latest SnekByte.
- Fully tested rollback steps, reference to backups/hashes, cold boot observations, and outstanding dependency/hardware limitations.

**Explicit final discipline:** Do not conclude *“Nuxel 18000 completed”* when any requested item is still blocked; instead say what physically works now, what works in offline tests, what is hardware-blocked, and what evidence would unblock it. Continue iterating safely within requested scope until stable results or a technically justified blocker.

---

# 14. REFERENCE AND REASONING NOTES (do not confuse with live evidence)

Consult bundled prior mission descriptions **15000, 16000, 17000** for architecture history but verify all implementation details against current live branch; don't reapply old patches. Public reference URLs for later detailed review:

- postmarketOS S10+ device status: https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_%28samsung-beyond2lte%29 — downstream 4.14 kernel, Bluetooth/GPS/NFC/audio and sensors not established working in that project; this isn't proof these are impossible on Nuxel.
- LineageOS S10+ hardware list: https://github.com/LineageOS/lineage_wiki/blob/main/_data/devices/beyond2lte.yml — device peripherals list and 4.14 kernel lineage; this isn't proof their Linux userspace integration is available.
- Fedora VLC: https://packages.fedoraproject.org/pkgs/vlc/vlc/ — genuine Fedora package; inspect `aarch64` and actual enabled repository build before install.
- Fedora mpv: https://packages.fedoraproject.org/pkgs/mpv/mpv/ — media player option subject to actual phone dependencies and GTK/Qt shell compatibility.

**DO THE WORK. KEEP THE PENGUIN ALIVE. ONE NAV BAR. ONE AUDIO ROUTER. REAL HARDWARE PROOFS. 🐧🔊🛰️📻⚡**
