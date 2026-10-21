# 🐧🔥 NUXEL A47 — OPERATION WORKDAY STABILIZATION
## S10+ live hotfix: navigation · NetworkManager Wi-Fi · screen-off heat · OSK · docks · power menu · battery · Mali metrics · physical audio

**Agent:** DeepSeek-v4-pro-thinking recommended for cross-layer orchestration; flash/non-thinking is acceptable for isolated, test-backed UI/NetworkManager fixes.  
**Target:** Samsung Galaxy S10+ SM-G975F (beyond2lte), Exynos 9820, Nuxel Fedora ARM64, WebKitGTK/Phoc/Wayland as actually deployed.  
**Mission mode:** Actually investigate and repair the connected live phone. Preserve USB access and all working features. No reflashing or boot/partition changes.  
**Source caveat:** Concrete filenames and `/new` bug below were inspected in the **previous uploaded v0.6.3-beta archive**. The currently deployed A45/A45.1 checkout may have changed. Inspect live source, active processes, and deployed file hashes before modifying anything. Do not blindly overwrite later fixes.

## 0 — PROTECT WHAT WORKS AND HANDLE THE HEAT FIRST

Owner-confirmed live positives to preserve: beautiful Nuxel penguin lockscreen, draggable lockhead, working grey/black/blue keyboard (when present), actual Wi-Fi network discovery on `wlan0`/`wlan1`, Nuxel dock artwork, working display and USB console. The photo shows scan results including signal strengths and WPA2. The Wi-Fi error is `org.freedesktop.NetworkManager.Device.SpecificObjectNotFound: The access point /new was not in the scan list.` No password is visible in the screenshot; do not store or log Wi-Fi secrets.

**Immediate safety:** Device feels very warm even at lockscreen with screen apparently off. Ask owner to disconnect charging temporarily if safe and stop intensive tests if temperature rises or the case becomes uncomfortably hot. Do not leave the phone in a pocket or unattended while investigating abnormal heat. Capture actual temperature/load rather than declaring the condition normal. Respect kernel thermal throttling and cutoffs; never disable them.

Establish a durable work log and snapshot: `git status`, `git rev-parse HEAD`, active branch, systemd units, Wayland session, active PWA/webroot and source hashes, `cat /proc/uptime`, `free -h`, `top -b -n1`, `ps`, `systemctl --failed`, `journalctl --boot`, `ip -brief link`, `nmcli general status`, `nmcli device status`, `cat /sys/class/power_supply/*/capacity` where valid, hardware thermal sensors and CPU/GPU clocks. Do not publish SSIDs, Wi-Fi keys, or sensitive environment details in Git. Preserve rollback and USB communication before restarting graphical/power services. Do not initiate reboot without owner consent and a known recovery path.

Implement task-sized commits rather than one broad rewrite. Capture baseline temperature, CPU load, GPU state and display/lock state while (a) awake idle, (b) locked display on, and (c) locked display **actually off**. Obtain fresh physical measurements after each repair.

## 1 — CRITICAL: FIX REAL WI-FI CONNECTION (EXACT KNOWN SOURCE BUG)

In the prior source `services/nuxel-bridge/src/bridge.py`, `scan_wifi()` returns per-network `ap_path` from `org.freedesktop.NetworkManager.Device.Wireless.GetAccessPoints()`; `connect_wifi()` instead calls:

```python
mgr.AddAndActivateConnection(dbus.Dictionary(profile, signature='sa{sv}'), path, '/new')
```

**`/new` is not an actual NetworkManager AP object in the scan list.** This directly corresponds to the error photographed on the phone. Inspect this in the **active** bridge first. Replace the flawed AP selection with correct, D-Bus-compatible logic, rather than masking the error in the UI.

Requirements:
- Select the correct managed NM Wi-Fi device; distinguish `wlan0` and `wlan1`, virtual/P2P interfaces, stale scan results and mismatched device ownership. Don't assume the first wireless device is always right.
- Transport the selected AP's real D-Bus object path from the scan UI, or perform a fresh server-side lookup by SSID **bytes**, BSSID when available and security mode. Verify that the AP belongs to the selected device and still exists when activating. Do not trust arbitrary web-client object paths.
- Use the actual AP path for NetworkManager `AddAndActivateConnection`/the appropriate versioned API. If choosing `/` as the documented non-specific-object value for a supported flow, verify that it is valid for the selected profile and device and test it; never use `/new` as a guessed object path.
- Handle scan-to-connect races: AP disappeared, wifi radio toggled, device disconnected, scan throttled, duplicate SSIDs, empty/hidden SSID, WPA2 vs WPA3/SAE, wrong password, user cancelled. Retry **one safe refresh** if AP path went stale; no infinite retry loops.
- Preserve the NM-managed secret store and polkit authorization. Never pass passwords to shell argv; never log passwords, connection dictionaries containing PSKs, or arbitrary connection secrets.
- Validate D-Bus profile types/signatures (`a{sa{sv}}`, relevant byte arrays and security properties); prefer activating an existing saved connection when one already exists. Do not create duplicate connection profiles on every retry. Implement forget/reconnect behavior if already supported.
- Report the stages accurately: association/authentication → DHCP address → default route → DNS → HTTPS. A successful D-Bus method call means **connecting**, not online. Verify NM device state, active connection, IP4Config/IP6Config, routing, resolver, external TLS, and loading a genuine HTTPS page in Browser.
- Make Settings reflect scan/connect errors intelligibly; preserve the observed working scan list. Hide/reopen OSK correctly for the password field, don't repeatedly focus after connection.
- Add tests for wrong AP path, stale path, two Wi-Fi devices, AP not found, duplicate SSIDs, wrong key, asynchronous state and redacted logs. Test on the actual owner's network with their on-device approval; do not record the passphrase.

Inspect `pwa/nuxel-apps/settings/wifi-settings.js` and all bridge HTTP/D-Bus routes in addition to `services/nuxel-bridge/src/bridge.py`. The old UI receives `ap_path` but may drop it when the Connect action sends only SSID/password/security. Fix the actual whole stack.

**Wi-Fi PASS:** phone associates, obtains IP, resolves DNS, loads HTTPS, stays connected after screen lock/unlock, and NM reports the same connection. Scan-only is NOT PASS.

## 2 — CRITICAL: SINGLE AUTHORITATIVE BACK / HOME / RECENTS NAVIGATION

Owner reports **two Back controls and two Recents/Tab controls on Home**, no Back exit from app, no long-press Back close, Penguin Home does nothing, and OSK does not dismiss with Back.

Inspect actual DOM, compositor surfaces, CSS pseudo-elements, native Phoc/system nav providers and the live `pwa/nuxel-home/js/navigation.js`, `app.js`, `launcher.js`, `recents.js`, `safe-zones.js`, `gestures.js`, app-host/iframe communication, and any newer A45 components. Determine whether duplicates are separate rendered navigation instances, duplicated icons/overlays, multiple startup initializations, or input-handler double binding. **Fix the owner, not only the style.** Render exactly one three-button system nav in unlocked mode.

Establish one state machine/dispatcher across foreground app, OSK, lockscreen and home:

- **Short Back:** if OSK visible, hide it first without destroying typed text; otherwise perform app's internal Back/history action when valid; if app has no navigable history, **minimize app and return Home Desktop 1**, rather than a dead button. Handle native WebKit apps and iframe apps through trusted host messaging. Never allow an ordinary remote webpage to call privileged terminate actions.
- **Long Back (about 650–800 ms, tune empirically):** close/terminate **only the current foreground app** by a graceful request and bounded fallback, remove its live entry from Recents, return Home. Do not terminate compositor, shell, network manager, lockscreen, bridge, or system services. Avoid firing the short-Back action on pointer release after a long hold.
- **Penguin Home:** always foreground Home Desktop 1; minimize background application and hide keyboard, preserve app state and Recents. Works from Settings, Calendar, Browser, File Explorer and other foreground apps.
- **Recents/Tab:** single tap reliably opens switcher and keeps it visible; second tap closes; app selection restores the app; no duplicated overlay.
- **Pointer and touch:** one owner, proper pointer capture, release, cancellation and lost capture; no double-dispatch from synthesized click/touch. Handle event bubbling across app iframe and native host, and long-hold timers. Press haptics once per real action.
- **Locked:** hide all three nav controls (not just make them transparent), remove hit targets and disable behind-lock navigation. Power menu is separately authorized. On unlock restore exactly one nav instance.
- **Visual stacking:** standard foreground apps cover the four-app Home shortcut dock; the three-button nav remains above apps and its hit area remains reserved while unlocked. Keyboard fits above the nav. Preserve supplied Nuxel art.

Add tests reproducing every owner-observed failure. Verify the actual live compositor/WebKit events with timestamps and screenshots. If a second native navigation component is adding duplicates, disable the redundant owner rather than adding CSS hacks.

## 3 — FIX SINGLE WORKING KEYBOARD AND BACK-TO-HIDE

User reports an old second **blue** keyboard still appears along with the **working grey/black/blue smartphone-style** OSK. Identify both actual OSK owners by process, startup hook and compositor surface. Keep exactly the previously working grey/black/blue OSK. Disable the redundant older blue WebKit overlay, its startup listeners, focus hooks, and touch hitboxes **only after** verifying the replacement types correctly. In prior archive `pwa/nuxel-home/js/touch-keyboard.js` creates a custom `.nuxel-touch-keyboard`; do not assume that is the current sole owner.

Pressing short Back with OSK visible must dismiss the OSK first (no app exit on that press). No keyboard on lockscreen, including invisible focus stealing; OSK restores after unlock. Validate caret/text input in Wi-Fi password, Calendar, Browser, and Settings. One keyboard, no duplicate synthetic events/haptic pulses, preserve accessible three-button nav.

## 4 — FIX SCREEN-OFF HEAT AND LOCKSCREEN POWER MENU

**Heat:** trace display idle manager, compositor, display DPMS/backlight, CPU frequency/suspend behavior, wakelocks/wakeup sources (if exposed), timer storms, WebKit animation loops, Wi-Fi scans, 3-second GPU/CPU polling, software rendering and duplicated sessions. Gather `journalctl`, cgroup CPU accounting (`systemd-cgtop` if present), `/proc/stat` deltas, `top`, supported `/sys/class/thermal` zones, power supply state, and `/sys/class/devfreq` metrics. Do not rely on a one-time CPU snapshot. Compare temperature, utilization, wakeups and actual display power state across lockscreen visible/off; quantify before/after without assuming a specific normal temperature for this device.

Ensure 60-second inactivity actually changes the display power state and stops rendering/animations/background Home metrics when locked/off. **Do not kill essential USB/network/audio/lock services or disable kernel thermal protection.** Request owner authorization before test reboot or suspend. If the screen is merely painted black instead of powered off, fix via available supported compositor/output power mechanism and check wake/recovery; do not write unverified raw kernel/display registers.

**Power menu while locked:** long Power opens a visible **clickable** power menu at lockscreen level. Inspect lockscreen input shield, native surface layering, pointer capture, and button hitboxes. Permit only menu interactions (cancel, authorized power off/reboot, and other genuinely safe actions). The locked session and underlying apps remain input-blocked. Do not inadvertently unlock when touching the menu. Verify menu works with finger, cancel returns to lockscreen, and an actual power-off command only runs with explicit user confirmation. Preserve current working penguin drag-to-unlock (do not alter wallpaper, lockhead placement or artwork).

**Wiggle animation:** add a gentle low-energy visual wiggle to **`assets/nuxel-lockhead.png` only** while the lockscreen is awake and idle. Place the decorative animation transform on a **nested child element**, not the pointer-captured/drag-transformed container; stop wiggle immediately while user drags; resume on cancel/return to rest. Never change gesture thresholds or pointer handling; pause animation when display off, unlocked, or prefers-reduced-motion. Use CSS compositor-friendly transform with modest amplitude and a long pause, not JS 60fps timers. Retain the unobstructed original wallpaper penguin.

**Lockscreen:** no virtual keyboard and **no system Back/Penguin Home/Recents three-button dock** on the lockscreen. No invisible hit areas. Only correct lockhead drag and authorized Power menu interactions; standard app input is isolated.

## 5 — FOUR-APP DOCK IS HOME-ONLY; REAL BATTERY DATA

Four-app shortcut dock must appear in foreground **Home** only and behind all foreground app content. Hide it or occlude its hit regions while any application is active, when lockscreen is active, or when a modal deliberately covers it. Keep its state/artwork intact when returning Home; do not remove or hide the persistent 3-button nav in unlocked mode. Test with Settings, Calendar and Browser.

Battery: user reports an unreadable **line instead of a number**. Inspect the actual battery source (`/sys/class/power_supply/*/capacity`, UPower, relevant bridge mappings), `pwa/nuxel-home/js/status-bar.js`, `pwa/nuxel-home/css/status-bar.css`, status safe-zone/overflow constraints, icon font rendering and display scaling. The prior UI has 'inside', 'percentage', 'bar' modes; keep all three if present but make each truthful and legible:
- **inside:** actual `NN%` readable inside a recognizable battery outline, with colored fill proportional to measured capacity;
- **percentage:** clear `NN%` text, no clipped glyph or line;
- **bar:** battery icon correctly fills according to `NN` and indicates charging state without fabricating remaining charge.
- Don't silently convert unavailable readings to 0%; show `—`/unavailable and investigate backend source.
- Clamp verified values to 0–100%, handle charging, rounding and out-of-range source failures; update status without re-rendering entire UI or resetting nav focus. Check high-DPI phone display at actual S10+ resolution.

## 6 — MALI GPU AND SHARED GPU MEMORY MUST BE HONEST

Both GPU and VRAM show 0. The Exynos Mali GPU has shared/system memory; its memory is **not a discrete dedicated VRAM pool**. Diagnose the live `/sys/class/devfreq/*`, GPU driver debugfs/sysfs, mali utilization counters, busy/total clocks, supported allocator/DRM memory accounting and permissions. Do not assume Exynos Mali driver exposes the same counters as another board. In the prior `pwa/nuxel-home/js/system-monitor.js`, the GPU-memory meter intentionally sets `meter('gpu-memory', null, false)` and can display `shared memory`.

- Report GPU **utilization** % only from genuine sampled busy/total counters over a defined interval, with wrap/reset validation. 0% is valid only if the source is real and measured idle; otherwise show `N/A`.
- Show the verified *current* GPU frequency from a real clock/devfreq interface if available. Frequency is not utilization.
- Show GPU-attributed **shared-memory bytes** only if the driver gives credible per-GPU accounting. Display units and source; otherwise `GPU MEM N/A (shared RAM)` rather than 0 MB or fake VRAM.
- Ensure the metrics daemon is actually installed/running in the current image, robust to disconnect/lock, and stops sampling when Home hidden/display off. Remove any unnecessarily aggressive polling contributing to heat.
- Tests: mock valid 0, missing counters, counter wrap, shared memory unavailable, and actual live sample over time.

## 7 — PHYSICAL S10+ SPEAKER AUDIO

Speaker is still silent. Investigate live full playback chain **without dangerous mixer guesses**: application event → WAV/MP3 decode → PipeWire/WirePlumber or ALSA client → actual playback PCM card → ASoC DAPM routes → Madera/CS47L93 codec → amplifier(s) where fitted → speaker. Inspect `aplay -l`, `aplay -L`, `amixer -c`, `alsaucm`, `/proc/asound`, supported `pactl`/`wpctl`, relevant `journalctl -k`, existing `beyond-madera` UCM, firmware readiness and audio services. The prior audit found empty speaker routing sequences; confirm against the **current** device and source before changing anything.

If necessary, compare the real machine driver, DTS, codec and validated reference route to the exact S10+ variant. Never invent an amplifier register value, override thermal/current limits, or randomly toggle opaque controls. Use low-volume controlled PCM/sine tests only with owner present; verify physical audible output, not merely decoder exit 0. Preserve the existing boot MP3 / `nuxel-pow.mp3` behavior and wired/Bluetooth routes. Distinguish native speaker driver limitation from volume/UI faults; if missing proprietary firmware or kernel support, provide exact evidence and a repair plan without claiming sound works.

## 8 — IMPLEMENTATION ORDER AND DEMO-READY GATES

Proceed in small verified milestones, while maintaining independent tasks if hardware is blocked:

**Gate 0: thermal safety** — establish whether screen-off heat is real/unsafe; stop or limit CPU-intensive work if concerning. **Gate 1: Wi-Fi connect** — patch `/new`, connect, IP/DNS/HTTPS and preserve scan. **Gate 2: navigation/OSK** — one triple-dock, one working keyboard, short/long Back, Home, Recents. **Gate 3: lock/power** — lockscreen hides nav/keyboard, power menu clickable, lower-energy screen-off, lockhead wiggle. **Gate 4: visuals** — four-app dock behind apps, battery numeric and correctly filled. **Gate 5: metrics** — GPU real readings or honest N/A. **Gate 6: audio** — physically audible speaker or evidence-backed hardware blocker.

Every gate must include specific source diff, tests, actual deployed file hash, real runtime screenshot/log where useful, and owner-observed pass/fail. Preserve all functioning Nuxel features. Do not burn the available time on an unverified speaker register tweak while navigation/Wi-Fi demo functionality is still broken.

## 9 — SAFE LIVE USB EXECUTION (NO FLASHING)

1. Confirm the MacBook-to-S10+ USB console is resilient and available; confirm remote user's current unlocked/locked state and screen mode.
2. Make byte-preserving backups of every changed deployed file and OSK/lock/power configuration; include a single-command rollback script and hashes.
3. Inspect actual current branch/commit and live rootfs service installation before edits; avoid overwriting newer A45/A45.1 revisions with stale v0.6.3-beta source.
4. Implement isolated fixes in repository. Run JS/Python syntax validation, focused unit tests, documented S10+ regression suite and available native integration tests.
5. Build compatible AArch64 artifacts only where needed; don't unnecessarily reflash, rebuild whole rootfs or replace kernel.
6. Stage and deploy userspace files atomically; verify SHA-256 and actual HTTP/WebKit resource versions. Reload/restart the smallest affected services. Preserve original USB console.
7. Capture actual on-phone proof using logs, compositor/window/surface introspection and user-visible actions. For power-off and audio tests coordinate with owner; never power off remotely without authorization.
8. On failure, roll back the last milestone while retaining evidence; preserve previous working keyboard and lockscreen.
9. After each milestone record PASS / PARTIAL / BLOCKED with exact reason, not generic "done". No unauthorized reboot or bootloader/partition work.

## 10 — 90-SECOND OWNER ACCEPTANCE WALKTHROUGH

Ask owner to physically test:
1. Scan networks; connect to their chosen network and browse real HTTPS. Verify no `/new` error.
2. Open Calendar → Back once returns Home (or navigates within Calendar when appropriate); long Back closes only active app and removes its Recents entry.
3. Open Browser → Penguin Home always returns to Desktop 1; Recents restores Browser; exactly one Back, Home and Recents on Home and apps.
4. Tap Wi-Fi password text field → only grey/black/blue working keyboard appears; Back hides keyboard first; next Back navigates/leaves app.
5. Launch Settings → four app shortcuts do not float above Settings; Home restores four-app dock.
6. Lock/wake → no system triple nav and no keyboard on lockscreen; penguin lockhead subtly wiggles and still drags/unlocks normally.
7. Hold Power while locked → menu is tappable, cancel works, lock remains secure from accidental touch-through.
8. Observe battery `NN%` and physical proportional fill. Check GPU frequency/utilization and shared memory source/N/A.
9. Allow screen to time out with logs monitoring temperature/load; verify the display actually powers down and no excessive wake/CPU work persists.
10. Play safe test sound; confirm *audible speaker output*, or report precise hardware blocker.

Retest locks, Back/Home/Recents and keyboard **after** each display/service restart. Avoid claiming production quality without real acceptance data.

## REQUIRED FINAL REPORT

| Requirement | Source test | Live deployment | Physical owner confirmation | Evidence / remaining blocker |
|---|---|---|---|---|
| Overheating while locked/off | | | | |
| Wi-Fi association + DNS + HTTPS | | | | |
| Single nav dock | | | | |
| Short Back and long Back | | | | |
| Penguin Home and Recents | | | | |
| Single working keyboard; Back hides | | | | |
| Lockscreen no nav or OSK | | | | |
| Locked power menu clickable | | | | |
| Lockhead subtle wiggle | | | | |
| Four-app dock behind apps | | | | |
| Battery readable % and proportional fill | | | | |
| GPU measured value or honest N/A | | | | |
| GPU-attributed shared-memory or honest N/A | | | | |
| Audible physical speaker | | | | |

Include changed files, test commands, commit SHA, deployed hashes, service status, backup/rollback paths, thermal before/after in measured units, NM device/AP association evidence (without credentials), image/screenshot evidence, and precise unsupported-hardware blockers. If remote publication is requested separately, use normal branch/PR discipline; do not force-push to protected main.

### NONNEGOTIABLE

**NO FLASHING, NO PARTITION WRITES, NO KERNEL REPLACEMENT, NO DESTRUCTIVE AUDIO REGISTER EXPERIMENTS, NO UNAUTHORIZED POWER-OFF/REBOOT, NO FAKE GPU/VRAM VALUES, NO DUPLICATE KEYBOARDS/NAVIGATION CONTROLS, NO STALE-SOURCE OVERWRITES, NO LOSING USB ACCESS.**

**FINAL GOAL:** The real Nuxel S10+ stays cool enough in standby, connects to Wi-Fi, shows exactly one usable nav system, types on exactly one OSK, locks cleanly, displays real battery/GPU state, and preserves the penguin experience. Repair and verify on the live device; don't just make source tests green. 🐧🔥

