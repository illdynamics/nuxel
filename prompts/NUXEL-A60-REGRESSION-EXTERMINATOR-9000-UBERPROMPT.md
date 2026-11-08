# 🐧⚡ NUXEL A60 — OPERATION REGRESSION EXTERMINATOR 9000
## Six persistent live-device bugs · Boot-readiness repair · Definitive system integration · No more regressions

**Executor:** GPT-5.6 Sol (High) or DeepSeek-v4-pro-thinking. **Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), running the owner's **CURRENT** Nuxel Fedora ARM64 build with Phoc/Wayland/WebKitGTK, native on-screen keyboard, Nuxel Home, and USB Live Console. **Host:** owner's connected Fedora laptop or MacBook, whichever has the proven reliable console. **Mission:** inspect, repair, integrate, deploy, and prove functionality on the **physical phone**. Not an offline-only exercise.

## The owner's latest symptoms — reproduce exactly

1. **The currently working grey/black/blue keyboard no longer closes** when the user expects it to, including via the system Back button. Do not reintroduce the discarded blue keyboard.
2. **SnekByte icon does nothing when tapped.** The game previously launched and worked, including WoNQ Mode / poo-meter; preserve that game and recent SnakePwn 7000 controls/speed/wraparound changes if present in the CURRENT checkout.
3. **Wi-Fi stays stuck at “authenticating & associating”.** Earlier failures included the invalid NetworkManager AP path `'/new'`, then association/DHCP stalls. Treat the current actual state as new evidence, not proof the former bug is still present.
4. **Rotation says `undefined` if tapped too early after boot.** The menu is not properly initialized/readied.
5. **Battery percentage appears only ~2 minutes after boot.** The icon and numeric percentage should initialize promptly from the true power-supply state.
6. **Rotation still offers only Forced Portrait / Auto, and Auto does not rotate.** The original requested seven choices are: Portrait, Reverse Portrait, Landscape, Reverse Landscape, Auto (all four), Auto Portrait (upright/upside down), Auto Landscape (two landscape directions). At minimum, preserve the five repeatedly requested named modes, and deliver the two reverse fixed modes as part of the original seven-mode contract when technically possible. No fake choices.

### Governing principle

**These are repeated regressions after earlier apparent fixes. Find and repair the common failure mechanisms first:** multiple competing owners for a service, stale deploy artifacts, incomplete install into the rootfs, app registry drift, mismatched frontend/backends, initialization order/races, cache/service-worker cache, incorrect systemd unit dependencies, lost runtime state, old JS running after a new backend, and unsynchronized source/phone revisions.

**Never finish at “code changed / unit tests pass.” The mission closes only with on-phone interactive tests, evidence, and authorized cold-boot persistence checks.**

---

# PHASE 0 — SAFE BASELINE, HARDWARE IDENTITY AND RESTORE PLAN

Before any edit:

1. Identify the real local repository, branch, current commit, dirty files, toolchains and phone rootfs/deployed revision; do not assume the attached historical archive is current. Record `git status`, a staged-file manifest, and the phone-side checksums of all files likely to be changed. Preserve uncommitted owner work and concurrent agents; prefer isolated worktree if needed.
2. Verify the S10+ is booted into Nuxel (NOT TWRP) and reliably reachable over the existing USB Live Console. Record the exact recovery command and serial endpoint. Never start two serial owners simultaneously.
3. Snapshot relevant existing files, unit definitions, configs, application registry, SnekByte assets and home, UI, OSK, bridge and network state. Backups must live outside the files being replaced. Document deterministic rollback with exact files and restart order.
4. Identify whether the phone's current rootfs has writable overlays, immutable/squashfs parts, volatile `/run` layers, and where persistent deployed files actually reside. A change that disappears on reboot is **not** a successful deploy.
5. Save boot ID, uptime, package versions, JS asset fingerprints, WebKit versions, service state, phone architecture, available RAM/storage, CPU temperature and USB continuity. Redact credentials, MAC addresses/BSSIDs/SSIDs from public artifacts where appropriate.
6. Ensure power is stable. **No partition flash, kernel/recovery replacement, bootloader change, `dd` to block storage, forced broad update, unsafe CPU governor, boot-parameter experiment or unapproved reboot.** Obtain owner permission for planned reboot tests; if not given, mark reboot gates pending and don't misreport.
7. Reproduce each of six failures and save timestamped device-side receipts **before making fixes**. Note any feature already fixed; avoid undoing it.

Deliver `a60-evidence/00-baseline.md` and a device-tested rollback script or procedure.

---

# PHASE 1 — CROSS-CUTTING ROOT CAUSE: WHICH CODE IS REALLY RUNNING?

This mission should **not** become six unrelated CSS/JS hotfixes. Map the ownership and startup graph of:

- System navigation dock and trusted Home/session controller.
- Native keyboard/input-method process (the working dark grey/black/blue OSK), its visibility/focus API and app focus/Back dispatcher.
- Nuxel Home app registry, native `.desktop` discovery, PWA app-loader/webview or WebKit app surfaces, SnekByte manifest/asset paths.
- NetworkManager, `wpa_supplicant` or iwd as actually present, D-Bus bridge and saved connection profile paths.
- Power/battery reporter, `/sys/class/power_supply`, UPower (if installed), bridge, cached UI state and initialization lifecycle.
- Rotation policy service, accelerometer/IIO, `iio-sensor-proxy` (if present), compositor output transform, renderer/`nuxel-wl-fb` presenter and libinput touchscreen coordinate calibration.

Produce a systemd and process launch graph. Find duplicated or masked units, inconsistent `After=`/`Wants=`/socket or D-Bus activation, incorrect `Type=` or readiness signaling, race-prone sleeps, stale stale JS in service worker/browser cache, old and new bridge protocols, bundled assets not installed, out-of-date manifest and volatile files.

**No arbitrary sleep(120) workaround.** Services must indicate readiness and report an explicit finite error/unknown state if they genuinely cannot initialize.

Establish for each component: canonical source file, on-device installed path, owning systemd unit/process, public API/IPC endpoint, startup dependency, persistence location and observed first-ready timestamp. This map is an enduring debug artifact.

---

# PHASE 2 — THE KEYBOARD MUST DISMISS RELIABLY

## Investigation

1. Determine the **actual** native OSK implementation and how it receives text-focus events, shows/hides, tracks active client and binds into the Phoc/wlroots seat. Identify if a stale duplicate keyboard surface or web fallback still exists.
2. Trace a physical short press on the **left Back** control while the keyboard is visible: touchscreen event → nav surface → unified action router → keyboard visibility query → trusted input method hide/request → actual Wayland surface disappears → underlying app remains active.
3. Look for a focus loop: OSK hidden, focused input immediately requests it again, old keyboard process gets re-spawned, or a stale `focusin` handler reopens the OSK.
4. Check pointer/touch event swallowing, overlays, `pointer-events`, duplicate Back handlers, keyboard shortcuts/Escape events, and app-specific `blur` logic. Long-Back kill must remain distinct from short-Back hide behavior.

## Required behavior

- **Short Back while OSK visible:** dismiss **only** keyboard, preserve app and form text, release focus gracefully and do not navigate away.
- **Short Back when OSK hidden:** perform one legitimate app/Back action (browser history, close modal or navigate out as existing policy), never duplicate actions.
- **Long Back:** preserve owner's kill-foreground-app feature; long press must **not** accidentally hide OSK and trigger app navigation/termination as multiple actions. Define and test priority explicitly.
- OSK closes after an app releases focus; no ghost overlay, no immediately reappearing keyboard when Back is pressed; can be reopened by deliberate tap on a text field.
- Physical key `Escape` where available should use the same trusted keyboard dismissal path, but do not blindly send untrusted key events to all apps.
- No keyboard appears over the lockscreen (unless explicitly allowed by a trusted authentication UI); lock/wake and native GTK/Qt or PWA focus remain correct.
- Preserve haptic settings, artwork and the sole working dark keyboard; don't re-enable old broken blue keyboard.

Implement a **single stateful keyboard dismissal contract** with acknowledgements and bounded timeouts; handle compositor denial/error honestly. Ensure reconnect/restart leaves state consistent, not stuck “visible” forever.

### Keyboard gate

Physically launch Settings text field, Browser address bar, and a second app text field; type → short Back → OSK visibly gone within one interaction → app still running → tap field → OSK returns. Repeat after navigation and authorized cold boot. Verify long-Back separately.

---

# PHASE 3 — REPAIR SNEKBYTE ICON AND REAL APP LAUNCH

**Owner confirmation:** SnekByte played successfully before. An icon tap now does nothing. Treat this as a REGRESSION in registry/asset/launcher/session lifecycle until evidence proves otherwise.

## Identify the actual installed variant

Inspect the CURRENT Nuxel tree and phone for relevant paths; the prior SnakePwn 5000 package contained:

```
pwa/nuxel-apps/snekbyte/index.html
pwa/nuxel-apps/snekbyte/js/snek-engine.js
pwa/nuxel-apps/snekbyte/js/snekbyte.js
pwa/nuxel-apps/snekbyte/manifest.json
pwa/nuxel-apps/snekbyte/app.json
pwa/nuxel-apps/snekbyte/icons/icon-192.png
```

The above are **historical hints**, not permission to overwrite current SnakePwn 7000 changes. Detect which actual version is installed and reconcile with any newer Android APK work (separate target; irrelevant to Nuxel launcher).

## Trace the real tap-to-window chain

1. Locate the exact snake-and-poop app icon and its app ID in the active Home menu. Confirm it is not a dead placeholder, stale cache entry or icon for an uninstalled path.
2. Trace touch → icon event → app-registry lookup → app ID mapping → navigation/session launcher action → URL/path resolving → WebKitGTK creation/reuse → app-ready signal → foreground focus. Log the **first broken transition**, along with any console exceptions, denied filesystem/resource access, CSP errors, missing scripts and WebKit crashes.
3. Detect missing/stale game files, wrong relative URLs when served under Nuxel's custom origin, file-scheme/CORS restrictions, service worker caching an old script, origin/storage migration, manifest ID collisions, duplicate app IDs, missing MIME files, and rootfs install path divergence.
4. Trace Nuxel Home's actual app lifecycle, especially if a previous A59 registry update replaced the real runnable SnekByte entry with a decorative native-app record.
5. If broken code is discovered, repair **only the launcher/packaging/lifecycle fault** first. Don't replace the working SnekByte engine with a generic snake clone.
6. Preserve the correct pixel-art icon, WoNQ Mode, poop-o-meter with every fifth snack, scores, pause/resume, touch swipes and D-pad. If new SnakePwn 7000 features (speed slider, wraparound, input buffering) are installed, preserve them.
7. On reload, restore persisted score/settings without corrupting storage or trapping the app in a stale service worker. If using SW cache, version assets appropriately and ensure updates activate safely.

## On-device gate

Tap the **real SnekByte icon from Home** → game UI appears, not blank screen → start game → move snake → eat food → see poo-meter → exit using Penguin Home → relaunch and resume/start → survive UI process restart and authorized reboot. Verify the icon asset shows the right snake artwork and no app drawer duplicate.

Provide `SNEKBYTE-LAUNCH-ROOT-CAUSE.md` with first-broken-stage receipt; do not mark successful based on launching `index.html` on developer PC only.

---

# PHASE 4 — WI-FI AUTHENTICATION / ASSOCIATION HANG: FIX THE NETWORK, NOT THE SPINNER

The UI currently stays at **“authenticating & associating”**. Earlier errors changed between invalid AP `'/new'`, DHCP hangs, and now association. A single label may mask multiple NetworkManager device states. Diagnose the REAL state machine from the handset.

## Read-only collection (run on the S10+, not Fedora host)

Use installed equivalents of:

```
nmcli general status
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
nmcli -f GENERAL,IP4,IP6 device show <verified_wifi_interface>
nmcli -f IN-USE,SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY,DEVICE dev wifi list
nmcli -f GENERAL.STATE,GENERAL.REASON dev show <verified_wifi_interface>
journalctl -b -u NetworkManager --no-pager -n 200
```

Do not print/save raw passwords or connection secrets. First inspect security settings carefully, and protect sensitive BSSIDs and network names in shared logs. Commands are illustrative: verify syntax and installed NM version.

Record AP selection, NM device states/reason codes, supplicant/iwd state, authentication exchange, associated flag, DHCP discovery/offer/request/ack, IPv4/IPv6, default route, DNS, and HTTPS. For non-NM wireless stacks, adapt to the actually running daemon; do not run both wpa_supplicant and iwd controlling the same interface without purpose.

## Possible failure modes to prove or rule out

- Wrong AP object path or stale AP ID: historical `'/new'` in `AddAndActivateConnection`; verify current D-Bus methods, signature, and actual scan-derived AP object rather than guessing.
- Password passed with wrong type/flags/key management; WPA2-PSK vs WPA3-SAE mismatch; missing/incorrect `802-11-wireless-security` settings or secret-agent handshake; missing secret storage.
- Selected SSID contains spaces/non-ASCII; escaping/parsing bug; hidden network; duplicate SSID/BSSID, scan aging, AP roam/channel change.
- iwd/wpa_supplicant config conflicts, driver/firmware association rejection, regulatory-domain mismatch, rfkill and power-save race, disabled bands/channels, random MAC mismatch or AP MAC filtering.
- UI initiates duplicate Connect calls or changes selected AP before activation, leading to repeated profile churn.
- Connection is actually associated but UI still says authenticating because D-Bus state/reason events are not handled or the bridge didn't subscribe/reconnect after boot.
- DHCP/route/DNS failure later mislabelled as auth failure.
- Profile stored only transiently, credentials lost on restart or NM autoconnect disabled.

## Correct activation architecture

Use NetworkManager's documented activation for the actual installed version:

1. Enumerate APs and retain a valid actual AP object path while scan results are fresh.
2. Build correct supported profile for actual security mode and device; use stable connection ID/UUID, interface and autoconnect policy.
3. Use documented `AddAndActivateConnection(2)` or `ActivateConnection` semantics, including the correct specific-object path when required and the documented default path (`/`) when applicable. **Never use `'/new'` as invented AP path.** Handle AP disappearance by rescan/re-resolve rather than reusing stale paths.
4. Use an appropriate NM secret agent/keyring or authorized system connection for safely persisting the password; avoid logging, printing, hardcoding, embedding in JS, storing plaintext in app localStorage, or exposing to public D-Bus APIs.
5. One connection attempt at a time; real UI states `SCANNING → AUTHENTICATING → ASSOCIATING → CONFIGURING_IP → CONNECTED`, or version-appropriate equivalents, with timeout, retry/cancel, truthful reason/error. Do not conflate auth and DHCP.
6. Prefer observable NetworkManager state-change signals instead of polling until timeout. Clear stale timers and retry state after device or bridge restart.
7. Do not fix by disabling TLS verification, weakening Wi-Fi encryption globally, setting a fake static IP, or bypassing a certificate/auth requirement.

## Network acceptance

- Owner enters password once using the working OSK; Connect progresses, real AP association succeeds, DHCP/IPv6 appropriate to network completes, IP/default route/DNS present and real `https://www.google.nl/` fetch succeeds with valid TLS.
- NetworkManager profile persists and autoconnects after Wi-Fi toggle, interface reset if safe, service restart, lock/wake and **approved phone reboot**; credentials not re-entered unless policy requires.
- Wrong password → prompt error; cancel → stops; stale AP → refresh; duplicate tap → one attempt; no secret in logs.
- If the radio/driver/firmware prevents association, produce exact reason code, relevant driver logs, reproduction evidence, and smallest plausible fix, not false PASS.

**Do not let network investigation consume the whole mission**: timebox driver-level dead ends and complete other independent UI fixes.

---

# PHASE 5 — BATTERY PERCENTAGE IMMEDIATELY AFTER BOOT

The owner waits ~2 minutes for percentage. This is unacceptable if battery data is already exposed by the kernel.

## Determine authoritative source

Inspect `/sys/class/power_supply/*/type`, `capacity`, `status`, `present`, `energy_now`, `energy_full`, `charge_now`, `charge_full`, `voltage_now` and UPower state when available. Identify the real battery versus USB/charger/other pseudo-supplies; do not assume a path called `battery` without validating type and backing driver.

At startup, record an exact timeline:

- kernel power-supply entry existence/readability;
- bridge first start;
- first successful battery read;
- first IPC response/subscription event;
- Home app initial hydration;
- first visible numeric percentage and proportional icon fill.

Find the two-minute delay at its first occurrence: systemd ordering, optional waits on Wi-Fi or sensor, throttled polling, initial subscription never sent, cached `null`, frontend not requesting until timer, unhandled boot event, wrong permissions or stale service instance.

## Implement correct startup

- If `/sys/class/power_supply` is readable early, perform immediate synchronous/first-query snapshot before periodic updates (without blocking Home forever).
- Expose one typed schema: `{available, percentage, charging, source, updated_at, error?}` and validate percent in 0..100. For UPower, verify unit conversion to percent, no raw fraction mistake.
- Frontend fetches initial state on UI mount and subscribes to updates. On bridge restart or D-Bus reconnect, re-query snapshot. No dependence on a prior battery change event.
- Display correct percentage and proportionally filled battery icon; charging indication only when real. Keep exact UI ownership to avoid two overlapping battery icons.
- If kernel exposes no battery data yet, show `—`/unavailable immediately and log first-ready reason; **never fabricate 0%, 50%, 100% or show `undefined`**.
- Persistent startup mechanism must survive cold boot; no fragile 120-second wait, boot-only cache or developer-console command.

### Battery gate

At each authorized cold boot, observe initial lockscreen/Home immediately after UI appears: first valid percentage within a few seconds **if sysfs data is already readable**, icon fill accurate, no later two-minute transition, correct charging/uncharging and after service restart/lock/wake. Record elapsed time from first sysfs readability and first interactive UI, not merely total boot duration.

---

# PHASE 6 — ROTATION: SEVEN REAL MODES, NEVER `undefined`, ACTUAL SENSOR AUTO

## Original requested policy, canonical values

| Visible setting | Stable internal value | Allowed orientations |
|---|---|---|
| Portrait | `portrait` | 0° |
| Reverse Portrait | `reverse_portrait` | 180° |
| Landscape | `landscape` | 90° |
| Reverse Landscape | `reverse_landscape` | 270° |
| Auto | `auto` | 0°, 90°, 180°, 270° |
| Auto Portrait | `auto_portrait` | 0°, 180° |
| Auto Landscape | `auto_landscape` | 90°, 270° |

Mapping of 90°/270° to left/right must be calibrated against the actual S10+ panel orientation and compositor conventions. Don't invert arbitrary sensor axes by assumption. If current policy historically encoded `locked` or `rotate-auto`, provide explicit migration and backwards compatibility; ensure all menus display correct saved values and round-trip through bridge.

## A: Fix first-tap `undefined` and missing menu choices

1. Inspect CURRENT Quick Settings and Settings source, compiled/installed bundles, current app schema, and live bridge/API. Identify whether the 2-choice menu is leftover hardcoded UI, a disabled feature flag, backend enum restriction, stale asset bundle, or a deployment mismatch.
2. UI menu must contain all seven items with clear labels, exactly one selected, and no `undefined`, `null`, or unrecognized value. If sensors don't work, *manual fixed modes are still selectable*, and auto modes show truthful capability status rather than silently disappearing.
3. Initialize rotation policy synchronously from a validated persisted preference (or safe default portrait), **before** sensor readiness. Distinguish `{policy_ready, sensor_ready, output_ready, current_angle, available_modes}`. Sensor auto may not be ready yet; UI can still display options immediately.
4. Repair systemd/D-Bus/bridge launch order and IPC response handshake; avoid waiting for NetworkManager, battery, camera or other unrelated services before exposing rotation policy.
5. Persist choice durably (appropriate `/var/lib/nuxel` config with ownership/atomic write). Run startup migrations from previous two-choice policy only once with explicit versioning and tests.

## B: Actually rotate the panel and touch input

1. Enumerate `/sys/bus/iio/devices`, `/dev/iio:*`, kernel accel/gyro modules, permissions, `udevadm`, and `iio-sensor-proxy` monitor output (if installed). Real automatic screen rotation ordinarily needs **accelerometer/gravity** orientation; a gyroscope alone is not sufficient for stable orientation relative to gravity. Record true sensor axes and device mount offset. Do not synthesize fake sensor events.
2. Calibrate motion thresholds/hysteresis, orientation stability/debounce (~300–600 ms as suitable), and avoid toggling when laid flat or during animation. Auto Portrait must NEVER enter landscape; Auto Landscape must NEVER enter portrait; Auto may use all four calibrated orientations.
3. Implement correct **Phoc/wlroots output transform** using supported compositor APIs/config. Also correct Nuxel framebuffer bridge/presenter and input-device transformation if current Nuxel still uses headless → Samsung framebuffer path. Rotation is not merely CSS `transform: rotate(...)`.
4. Verify compositor logical width/height and scaling, status bar/keyboard/layout constraints, touch coordinates and screen edges after changing orientation. Native GTK/Qt, WebKit apps, Home, lockscreen, camera viewport (where supported) must remain usable. Preserve virtual keyboard dismissal and triple-button positioning.
5. Handle lockscreen policy: no accidental rotation loops during boot/wake; preserve intended security behavior. If auto rotation is not available because the kernel doesn't expose working accelerometer data, keep manual modes working and mark auto BLOCKED with sensor logs and a concrete driver plan rather than claim success.

## C: Tests

- Seven backend/frontend enum choices; saved preference survives restart/reboot; no `undefined` on first tap within first seconds after Home interactive.
- All four manual modes visually rotate real output and preserve touch accuracy; owner verifies left/right naming on hardware.
- Auto: rotate physical handset through each valid direction; record recognized sensor event, chosen angle, committed compositor transform and screenshot/owner observation.
- Auto Portrait: only 0/180; Auto Landscape: only 90/270; no inadmissible orientation.
- Full keyboard, navigation buttons and app layout after rotation; touch near all four corners; no phantom extra status bar icons.

---

# PHASE 7 — IMPLEMENTATION DISCIPLINE / ANTI-REGRESSION ARCHITECTURE

For each issue use a common lifecycle: **REPRODUCED → ROOT CAUSE VERIFIED → SMALL FIX → UNIT TESTED → ON-DEVICE DEPLOYED → PHYSICALLY TESTED → RESTART PERSISTENT → REBOOT VERIFIED**.

- Fix authoritative code, not multiple copies of the symptom. Use one event dispatcher for Back/OSK and one source of truth per subsystem.
- Cleanly version frontend bundles/assets; invalidate outdated WebKit caches/service workers deliberately without deleting user game saves or browser storage.
- Align deployed JS, Python/service code, D-Bus method names, manifests and rootfs install steps; ensure the exact same reproducible release artifacts are installed. No mismatched host/phone source checkouts.
- Add dependency/readiness signaling and reconnection logic, not sleeps. Startup UI must never render raw `undefined`.
- Write test suites for previous regression classes and run existing A45–A59 tests. In particular: keyboard Back precedence; app registry launches SnekByte from Home; live NM activation/success and invalid AP `'/new'` contract; battery immediate first snapshot; rotation menu and persisted mode; cold-boot readiness.
- Any feature with real hardware dependencies needs an integration test on the actual S10+; host mocks are not physical success.
- Check no extra rendering or high-frequency polling keeps phone warm when screen is off. Display rendering/input/sensor updates should settle appropriately on screen-off. No permanent busy loops.
- Preserve and regression-test: Penguin Home button, triple navigation Back/long Back/Recents, Nuxel app drawer, SnekByte 7000 features, grey/black/blue keyboard, custom lockscreen graphics and gesture, USB Live Console, current Nuxel boot art, browser functionality, status-bar layout, Wi-Fi scans, and all other working apps. If Penguin Home is still broken, report it explicitly rather than silently claiming system-wide navigation PASS.

---

# PHASE 8 — SAFE LIVE DEPLOYMENT

1. Stage independently reviewable patches in CURRENT Nuxel worktree. Do not blindly overwrite with old v0.6.3 or A56 ZIPs.
2. Back up corresponding on-device files and units, hashes, configs and game data. Validate service restart/rollback order and keep a live USB console.
3. Deploy in small groups so a broken UI package does not take down networking and vice versa. Install the **real target** paths with correct SELinux/permissions/ownership if applicable; do not confuse host Fedora filesystem with handset Fedora rootfs.
4. Avoid broad `dnf upgrade`, kernel changes, partition writes, bootloader operations or restarting the USB console itself. Restart only impacted components with owner awareness; ensure no other agent owns the phone.
5. Verify hashes of installed files, service status, launch logs and current application bundle cache version. Reopen apps and test before considering any reboot.
6. With explicit owner authorization, perform a genuine **cold reboot** or power-cycle test; capture USB logs, first-ready events and physical screen observation. If something regresses, restore previous verified files and repeat one bounded attempt.

---

# PHASE 9 — HARD ACCEPTANCE GATE: ZERO FAKE GREEN

| Gate | Actual phone acceptance | May pass from offline test only? |
|---|---|---|
| `OSK-HIDE` | Short Back hides native OSK promptly; reopened by text-focus; long Back semantics preserved | NO |
| `SNEK-LAUNCH` | Tap actual icon → working game, controls, poo-meter; Home and relaunch work | NO |
| `WIFI-AUTH` | Correct password authenticates, associates, real IP/default route/DNS and HTTPS | NO |
| `WIFI-PERSIST` | Saved profile reconnects after authorized reboot | NO |
| `ROT-READY` | Menu shows real modes without `undefined` on first early interaction | NO |
| `ROT-MODES` | All seven choices listed; fixed modes perform output + input transform | NO |
| `ROT-AUTO` | Actual accelerometer events rotate output correctly within policy constraints | NO |
| `BAT-BOOT` | Accurate percent on first interactive UI when kernel already exposes battery; no 2-minute delay | NO |
| `PERSISTENCE` | All above still work after service restart and authorized cold boot | NO |
| `NO-REGRESSIONS` | No duplicated OSK/navigation, no lost SnekByte scores, Home, lockscreen and USB console preserved | NO |

Run at least **three cold starts if the owner approves**, spaced sufficiently for comparable cold state, and test early (<5 s from first interactive UI) plus 30 s, 2 min, post lock/wake, and after an app restart. If full test count isn't authorized, be truthful about remaining coverage. Measure **first authoritative state available** and **first displayed state** for battery/rotation; do not measure success by waiting arbitrarily two minutes.

For any blocked gate, state **BLOCKED** and include the exact first failing stage, error/log/firmware evidence, earliest reproducible condition and next patch required. Do not downgrade scope silently, use placeholder sensor events, store fake Wi-Fi success, claim the camera works, or declare victory because all unit tests passed.

---

# PHASE 10 — MANDATORY REPORTS AND HANDOFF

Provide within `docs/a60-regression-exterminator/` (or sensible project-conformant location):

1. `BASELINE-AND-DEPLOYMENT-MAP.md` — actual current repo vs live phone revision, owning services and on-device paths.
2. `BOOT-READINESS-TIMELINE.md` — measured first sysfs battery, bridge battery, frontend battery; policy-ready, sensor-ready and first rotation menu render.
3. `KEYBOARD-BACK-FIX.md` — cause, event flow and on-device tests.
4. `SNEKBYTE-ICON-RECOVERY.md` — app registry/click/launch first-broken stage, preserved game package and game tests.
5. `WIFI-AUTHENTICATION-REPAIR.md` — real NetworkManager states/reason codes, safe secret persistence, IP/DNS/TLS verification and reboot tests (with secrets redacted).
6. `ROTATION-SEVEN-MODE-REPAIR.md` — schema/menu, calibration, actual sensor readings, compositor/input transforms and unresolved driver issues.
7. `A60-REGRESSION-MATRIX.md` — each gate PASS / BLOCKED / PARTIAL / NOT TESTED, commands, process IDs, relevant timestamps, screenshots or owner observation, reboot IDs.
8. `A60-ROLLBACK.md` — exact backed-up files, hashes and restore commands; what changes persisted into a built rootfs.
9. A concise owner-friendly summary: **what is actually fixed, what only passes offline, what still needs hardware work**. Include git diff/commit hash, verified device build revision and next small actionable blocker.

**NO invented success. NO blind refactor. NO broad rewrite of working Nuxel.**

## FINAL DIRECTIVE

🐧🔧 **Recover the native keyboard dismissal, launch SnekByte from its actual icon, get Wi-Fi beyond authentication into usable HTTPS internet, eliminate both battery and rotation startup delays, restore all seven rotation modes and real accelerometer-driven Auto. Diagnose why these features kept regressing and make the fixes survive actual S10+ cold boots.**

**GO EXTERMINATE THE REGRESSIONS. PENGUIN PWNAGE 9000. 🐧⚡🔥**
