# 🐧⚡ NUXEL A73 / 22000 — OPERATION USB GHOSTBUSTER & RADIO REVIVAL

## ZERO GHOST PENGUINS • REAL BLUETOOTH SWITCH • REAL LOCATION SWITCH • KEEP CHARGING WORKING

**Agent:** GPT-5.6 Sol (high reasoning) or DeepSeek-v4-pro-thinking through CodeSeeQ.  **Execution machine:** owner's Fedora laptop or connected development host.  **Target:** Samsung Galaxy S10+ SM-G975F, beyond2lte, Exynos 9820, existing Nuxel Fedora ARM64 userspace and its working downstream Linux 4.14 installation. **This is an implementation mission against the CURRENT working tree and CURRENT phone deployment**. Historical code paths supplied below are reconnaissance leads only; resolve current revisions and deployed hashes before editing. Internet is available, and the browser/Wi-Fi are now working. Preserve them.

## 1. Owner-observed defects — exact acceptance contract

**A73-01 — Ghost USB computer penguin.** On boot, the Live Console penguin appears. When the owner inserts a PC USB cable, charging and PC-connected penguins also appear as expected. **On unplug, the charging penguin disappears correctly, but the PC-connected penguin remains stuck on.** It MUST disappear promptly and stay off when no usable PC data connection exists. A wall charger/power-only cable must NEVER illuminate PC-connected. The owner wants true independent indicators; do not simply tie PC icon CSS to charging icon's state as a shortcut.

**A73-02 — Ghost Live Console penguin.** On boot it may appear even without a PC attached. It stays illuminated after PC unplug. Define the indicator precisely: **ON means an actually usable, host-connected USB Live Console transport/session**, not merely a console daemon listening or a `ttyGS0` node existing. A prestarted console service, open gadget TTY, stale pid/lease or enabled service without attached host is NOT sufficient. After physical detach, turn it OFF promptly. When the owner later reconnects PC and an actual console session or demonstrably connected console transport becomes usable, turn it ON. If the implementation cannot directly observe an interactive attached session, the icon must accurately represent a documented testable state; distinguish `console_service_armed` from `console_transport_connected` from `console_session_active` and choose the display predicate with the owner-observed requirement (disconnected = OFF). Do not terminate the console daemon simply to extinguish its icon.

**A73-03 — Preserve Charging penguin.** Its connect/disconnect behavior is already correct. Keep exactly the current artwork, x/y position, doubled visible size, animation and truth behavior. Do not break it when changing USB detection. Do not reorganize the lockscreen, clock, date, percentage, draggable lockhead, background, or unrelated styles. Keep PC and console penguins' exact size, alignment and animations. No new icon designs.

**A73-04 — Bluetooth Quick Setting actually toggles.** The Quick Settings Bluetooth tile currently says **`bluetooth control is unavailable on this build`**. Remove that placeholder route by implementing its real capability/status/toggle backend end-to-end, with ON/OFF and accurate asynchronous states. Bring up BlueZ and physical radio only if compatible with the current S10+ kernel and hardware; verify rfkill, HCI, firmware, daemon D-Bus and pairing. If controller unavailable, show the concrete blocker in the tile or details page, not generic `unavailable in this build` or a falsely illuminated tile. Bluetooth toggle ON MUST NOT claim powered when adapter is absent. Bluetooth manager UI must remain consistent with tile and allow discovery/pairing of an owner-controlled speaker when actually supported.

**A73-05 — Location Quick Setting actually toggles.** The Quick Settings Location tile currently says **`location control is unavailable on this build`**. Implement a real, persistent, **system-wide location permission/service enable switch**, with truthful state feedback, through the actual bridge and user-session services. This must work even where GNSS hardware is not yet operational: **location enabled** means the permission/provider is enabled, NOT that a satellite fix exists. Keep separate `permission_enabled`, `provider_ready`, `location_fix_available`, `fix_source` and `fix_timestamp`. If permission is OFF, deny new app location requests and notify Maps; if ON, allow consented location and attempt legitimate GeoClue/other real provider. Treat GPS as a separately diagnosed hardware task—never manufacture latitude/longitude or claim a GPS fix from IP geolocation. Make persistence/reboot behavior explicit; honor existing owner privacy settings and per-app grants.

**A73-06 — Deploy and physically prove.** A source edit is not an actual repair. The agent MUST show exact repo revision, deployed hashes and runtime processes, install corrected code/services in the correct phone locations, restart only necessary processes safely, then collect fresh live measurements and screen results. If the owner cannot perform a disconnect test while the agent depends on USB as the only access, schedule owner-performed unplug/replug steps with console-independent evidence collection and automatic local logging so observations survive the disconnect. Do not end with offline tests alone.

## 2. Preflight, safety, recovery and scope

1. Inspect `git status`, active branch/HEAD, staged/uncommitted code, current device installed file hashes, version metadata, bridge/service units, console transport, runtime directories and web/PWA cache versions. The phone **may be newer than the previous uploaded archive**. List drift as `repo path → deployed path → sha256 → process/service → reload method`.
2. Do not blindly `git reset`, overwrite `snekbyte.zip`, alter prior fix branches, or wholesale deploy old ZIPs. Make a feature branch or worktree, create limited backups of modified files/units and a tested rollback method. Maintain a host-side recovery path (owner must approve a deliberate detach that interrupts sole console access). Consider a locally-running diagnostics logger that writes to durable on-device storage for later retrieval.
3. No flashing of bootloader/kernel, dtb replacement, vendor radio firmware guessing, partition changes, and no mass OS upgrades. No restarting or stopping the sole USB Live Console while dependent on it. Prefer read-only probes first; if a gadget config mutation is required, obtain owner approval and establish an alternate recovery route before execution.
4. Working Wi-Fi, Ethernet if present, TLS, Nuxel Browser, shell/navigation, battery, animations, custom penguin art and lockscreen, graphical performance, Camera, and SnekByte are regression-protected. Do not touch them unless strictly required for targeted integrations.
5. A73 work can span host and phone, but **only one agent may write to or deploy to the phone** at a time. Commit in small batches: (a) USB truth, (b) Bluetooth tile backend, (c) Location tile backend, (d) physical matrix + rollback.
6. Internet access permits checking the phone's genuine Fedora aarch64 packages for `bluez`, relevant services, GeoClue, systemd, D-Bus utilities and udev rules. First inspect existing packages and repos; perform dry-run, package signature/provenance checks and request owner approval before disruptive installation. Never claim installing BlueZ alone initializes missing HCI driver/firmware.

## 3. Historical source reconnaissance leads (DO NOT assume they match current HEAD)

These findings come from the owner's earlier `nuxel-main (4)(1).zip` snapshot. Re-read the corresponding files in **the current repo** and compare deployed bytes and behavior. Historical paths:

- `services/nuxel-bridge/src/system_indicators.py`: `usb_connection()` calls `_bound_gadgets()`, `_udc_states()`, `_android_usb_state()`; a gadget's UDC state `configured` **or `addressed`** is accepted for PC, with an Android USB `CONFIGURED` fallback. These may be stale/ambiguous on Samsung downstream 4.14; gadget binding alone survives detach. `live_console()` scans for `nuxel-console` holding a console TTY and checks gadget-bound + tty registered—none intrinsically proves a host is still connected. It even accepts a live lease PID without necessarily confirming a current established remote session.
- `pwa/nuxel-home/js/lockscreen-indicators.js`: maps `charging.external_power`, `usb_data.pc_connected`, `live_console.active` to three classes. Its `_tick()` skips refresh while display is off, and on read errors it logs but retains prior state. Check fetch caching, failed reads, wake refresh and whether state changes require a forced class removal. Its `stop()`/start lifetime and `_generation` logic must not drop a detach event.
- `pwa/nuxel-home/js/qs.js`: `_toggle(id)` only actively implements `wifi` and `rotate`; others fall through to ```${id} control is unavailable on this build``` (historically around lines 261–273). `_syncState()` updates Wi-Fi and modem only; Bluetooth/Location are initialized false and never synchronized. This is an actual missing Quick Settings integration in the old snapshot, independent of whether kernel peripherals work.
- `services/nuxel-bridge/src/bridge.py`: includes a `GeoClue` getter and capability names for Bluetooth scan/connect and location read but does **not necessarily expose a privileged status+toggle method** through the same host bridge used by Quick Settings. Inspect current `api.py`, `capabilities.py`, JS `bridge.js`, `host-bridge.js`, phone host transport, and D-Bus services before choosing changes.
- `configs/nuxel/bluetooth/`, `tools/s10plus/a33/nuxel-bluetooth-diag.sh`, and Quick Settings icon artwork `pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png`, `09-location.png` may help. Preserve exact artwork.

## 4. USB truth: build a genuine physical/link/session state model

### 4.1 Record kernel evidence across **all** cable transitions

On the actual phone, determine the real UDC controller(s), USB gadget configuration(s), cable/power/Type-C extcon or role signals, and host-visible function(s). Collect timestamped snapshots while: (1) **no cable**, (2) wall charger only, (3) PC attached but unconfigured, (4) PC enumerated and data active, (5) console session active, (6) PC unplugged, (7) reconnect, (8) idle/locked and (9) optional boot with no cable.

Sample tools **read-only only**, adjusted to actual paths and permissions:

```sh
uname -r
find /sys/class/udc -maxdepth 2 -type f \( -name state -o -name is_otg -o -name soft_connect \) -print -exec cat {} \; 2>/dev/null
find /sys/kernel/config/usb_gadget -maxdepth 3 -name UDC -print -exec cat {} \; 2>/dev/null
for p in /sys/class/android_usb/android0/state /sys/class/power_supply/*/online /sys/class/power_supply/*/type /sys/class/typec/*/data_role /sys/class/typec/*/power_role; do [ -r "$p" ] && printf '%s: %s\n' "$p" "$(cat "$p")"; done
ip -br link
ls -l /dev/ttyGS* 2>/dev/null || true
journalctl -k --since '-10 min' --no-pager | grep -Ei 'usb|gadget|udc|type.?c|vbus|dwc|configured|disconnect' | tail -100
```

Do not assume every path is implemented. Avoid treating a bound UDC, registered gadget function, Android legacy `CONFIGURED` string or tty node as authoritative **without verifying behavior on real unplug/replug**. Check whether UDC reports stale `addressed/configured` after detach, whether `not attached` signals are observable in extcon/Type-C/charger, whether gadget network `carrier` or serial DCD reflects host detach, and whether the bus reset/disconnect uevent arrives. Check `ttyGS0` disconnect semantics safely (not by writing random bytes to a possibly interactive console).

**Disambiguation:** USB wall charger may provide power but no host data. A real PC may leave charge status `not charging` when battery full. Do not use `charging == true` as the only PC predicate. Evaluate **data-capable physical link + enumeration + host confirmation** using signals demonstrated reliable on *this kernel*; prefer a small adapter interface that exposes raw signal ages, exact source and a decisional reason, so future kernels can use alternatives. If a sensor is stale or contradictory, return `unknown`/OFF rather than hold an old ON indefinitely.

### 4.2 Model distinct states, propagate detaches, and make UI fail closed

Implement/readjust a single authoritative status object with e.g.:

```json
{
  "charging": {"external_power": false, "charging": false, "source": "..."},
  "usb_data": {"pc_connected": false, "link_state": "disconnected", "source": "...", "sample_age_ms": 0},
  "live_console": {"active": false, "service_armed": true, "transport_connected": false, "session_active": false, "source": "..."},
  "observed_at": "...",
  "generation": 0
}
```

Schema illustration only—adhere to the current bridge compatibility contract and preserve existing client keys. A daemon running is a *service state*; the **Live Console icon predicate** requires both active USB data and actual transport/session proof. Where the platform cannot expose the requested distinction, return an explicit unknown/unverified state and show OFF rather than lie.

- On disconnect, invalidate old state **immediately** from reliable kernel/netlink/udev/host event; use a bounded poll fallback. Events are preferred but must reconcile with full refresh on wake, lockscreen show, host bridge reconnect, UI renderer remount and app restart.
- Avoid long debounce for OFF: target disappearance within ~1 second after observed detach (hardware permitting); use modest debounce for ON to suppress USB enumeration flapping.
- For asynchronous reads, ensure stale in-flight results and HTTP/browser cache cannot resurrect an earlier ON state. Include timestamps/generation IDs and reject out-of-order results. If read timeout or bridge failure leaves last known state older than bounded TTL, **fail off for PC/Live**, even while charging state remains independently valid. Do not hide the icons using a one-off DOM patch while backend still reports true.
- Maintain exact existing penguin placement, dimensions, image resources and animations. Show a physically accurate icon state before or at first lockscreen frame. If an icon is intentionally suppressed on lockscreen while unlocked, explain policy and ensure no re-appear-on-wake bug.
- If the owner unplugs the only console cable, diagnostic capture MUST continue locally without relying on host RPC; verify subsequent files contain unlink timestamps. Do not claim real detach passed from logs that necessarily stop at disconnect.

### 4.3 USB physical test matrix

| Test | Charging | PC connected | Live Console |
|---|---|---|---|
| Boot without USB cable | Off | Off | Off |
| Wall charger, data absent | On | Off | Off |
| PC USB enumeration, no active console | On or real power status | On | Off |
| PC with confirmed active Live Console transport/session | On or real power status | On | On |
| Disconnect PC, daemon remains enabled | Off if no charger | **Off promptly** | **Off promptly** |
| Reconnect PC and console restored | Real power status | On | On when transport/session actually active |
| Console service only, disconnected PC | Off | Off | Off |
| Console stopped while USB data still active | Real power status | On | Off |

Charging means **external power icon**, not necessarily active battery charging animation; if battery full, respect its distinct actual status. Do not destroy console availability to test the last two cases; change service only if reversible and owner-approved.

## 5. Bluetooth Quick Settings: wire the real control path

### 5.1 Audit runtime before introducing new toggle endpoints

Read current source and service graph: Quick Settings JS, bridge facade, host runtime, Nuxel D-Bus API, capability grants and authorization, BlueZ service, rfkill, kernel driver, firmware source, local manager app, paired/trusted devices. Inspect `rfkill list`, `/sys/class/bluetooth`, `bluetoothctl list/show` if installed, `systemctl status bluetooth`, `busctl tree org.bluez`, `dmesg` firmware/BT lines. Do not assume an adapter exists because a tile exists. Existing historical A69 report noted Bluetooth soft-blocked with BlueZ absent; treat it as *dated evidence*, not current truth.

### 5.2 Actual behavior and permissions

- Add a typed, idempotent **status read** method: hardware adapter availability, rfkill hard/soft blocks, BlueZ daemon readiness, `Powered` actual value, `Discovering`, error and timestamp. Separate `unsupported`, `hardware_blocked`, `service_unavailable`, `off`, `turning_on`, `on`, `turning_off`, `error`. Use one authoritative BlueZ/rfkill state.
- Add an authorized **set-powered** method, restricted to trusted Quick Settings/system service; use BlueZ `org.bluez.Adapter1.Powered` (plus rfkill when appropriate) on the correct adapter. Do not expose an unauthenticated arbitrary-power control over a public HTTP server. Return actual readback after applying; Bluetooth UI must display `ON` only when actual adapter is Powered.
- If BlueZ is missing and available from signed Fedora ARM64 repo, inspect installation plan, ask owner approval and install/restart safely. If HCI/firmware/driver is absent, produce a precise blocker and build working error state rather than fake a radio, unknown BIOS edits, or random firmware blobs. Do not disable MAC randomization/security simply for convenience.
- Toggle behavior: a tap switches; pending state visible; actionable service/hardware/permission error; quick panel refresh and restart read real adapter value. Reconcile external changes (rfkill, CLI, other manager) via DBus subscription + bounded refresh; avoid local-only stale booleans. Persistence across reboot should follow explicit owner setting and safe default, not an invented `true` flag.
- Integrate Bluetooth Manager (the actual installed one, if present) so a long press or settings action opens manager, not duplicate screens. Physical validation ideally with an owner-controlled speaker: power, scan, see, pair/authorize/trust, connect, disconnect, observe real connection. **Audio pairing does not prove audio routing**; if A2DP/ALSA is blocked, report separately.

## 6. Location Quick Settings: real privacy switch, not pretend GPS

### 6.1 Define system and app policy properly

Discover existing Nuxel settings, geolocation JS, app portal grants, GeoClue D-Bus, location privacy config, GNSS and optional network-based provider. The Location tile is a **global enable/disable permission/provider policy**; it is not a claim that physical GNSS sensor works. Make it possible to turn the policy ON even where GPS hardware is blocked, while clearly indicating `No position fix` separately.

- Expose typed `location.getStatus()` with global enabled/policy, GeoClue/provider presence and readiness, real last fix source/age/accuracy, per-app permission state (without dumping user coordinates into logs), service error. Expose authorized `location.setEnabled(bool)` and verify round trip. Honor owner persistent policy; clarify behavior across boot and system suspend.
- Turn OFF: deny future position requests to all applications through Nuxel bridge AND relevant provider/portal path, revoke/cancel active subscriptions, notify Maps/browser clients, clear stale displayed fix or mark invalid per privacy policy. Audit native apps/GeoClue API access to avoid falsely claiming global privacy when clients can bypass the bridge. If policy enforcement cannot be complete yet, clearly communicate the limitation rather than advertising a global privacy kill switch. Do not sever emergency functionality unexpectedly.
- Turn ON: register availability to actual GeoClue/authorized provider, preserve app-specific consent requirements, and permit only legitimate location reads. A GPS fix is a distinct readiness state and may remain unavailable. Do NOT substitute fake coordinates or conflate IP-estimated location with GNSS.
- Tile states should say `Location off`, `Location on — locating`, `Location on — location unavailable`, `Permission needed`, `Provider unavailable`, etc. A policy-on/off tile should not be stuck behind generic `unavailable in this build` just because a GNSS driver is missing.
- Ensure Maps' locate button obeys the toggle and handles denied/unknown states gracefully. Any browser geolocation requires user consent and correct permission handling. Privacy-sensitive coordinate and device identifiers must be masked in evidence.

### 6.2 Wire actual Quick Settings markup and synchronization

In current Quick Settings JS, replace the generic `bluetooth` and `location` unavailable dispatch only **after** real handlers exist. Initialize tile states asynchronously from authoritative backend; bind taps once, track pending/error/disabled, reconcile service restarts and backend changes, prevent duplicate requests on rapid taps, expose accessible messages and long-press details when appropriate. Preserve icons/animation, layout and all existing Wi-Fi/rotation controls. No decorative fake toggles; status must survive reboot and match CLI/DBus sources.

## 7. Engineering and test coverage

Add substantive tests rather than only mocked happy-path APIs:

### USB
- Fixture/read-only sysfs-based tests: unplug while gadget remains bound, UDC still `configured` but external verified data-link signal goes down, Android state stale, `ttyGS0` remains registered/open, console daemon still alive, lease PID valid but host gone, wall charger, active PC, host enumeration flap, missing sysfs files, UDC state unknown, stale cached HTTP payload, fetch failure/TTL expiry, rapid detach/replug/read races, lock/wake.
- Test indicator semantics independently: no charger→PC dependency hack, no size/position changes, animations preserved, console ON only for appropriate active host state.
- Physical USB disconnect/reconnect test with locally persisted timestamps, image screenshots/owner observation and backend JSON before/after; do not claim success without actual cable changes.

### Bluetooth
- Status reads with adapter missing/hard-blocked/soft-blocked, BlueZ service down/up, permission denied, adapter power fails/succeeds, external CLI state flips; actual `Powered` readback required. Real device discovery/pairing only if a physical BT device is available.

### Location
- Global policy persistent across UI/bridge restart and reboot, privacy OFF denies app request, policy ON with no GNSS still reports enabled but no fix, provider unavailable state, per-app consent, Maps receives on/off, external service changes reflected accurately. Don't leak location in logs.

### Regression
- Wi-Fi reconnect, real HTTPS Google.nl, battery, lockhead unlock, charging indicator, animations, navigation/Home/Back, Camera escapability, SnekByte launch, screen sleep/wake, normal boot, USB recovery.

Use a traceability table in `docs/a73/REQUIREMENTS-AND-TESTS.md` and a final per-gate matrix. Strong status labels: `PASS_PHYSICAL`, `PASS_DEVICE_RUNTIME`, `PASS_OFFLINE_ONLY`, `BLOCKED_HARDWARE`, `BLOCKED_DEPENDENCY`, `NOT_TESTED`, `FAILED`.

## 8. Required output artifacts

Write under `docs/a73/`:

- `PREFLIGHT-AND-ROLLBACK.md`: host/phone versions, transport, backups, rollback commands, safe detach plan, authorized service restart list.
- `REPO-VS-DEPLOYED.md`: current source path, real deployed file, sha256 and service owner for USB indicator and Quick Settings/bridge components.
- `USB-PHYSICAL-STATE-MATRIX.md`: exactly what kernel signal changes for each unplug/replug event, sample values, time stamps, algorithm truth table, worst-case stale TTL, screenshot evidence references.
- `BLUETOOTH-STATUS.md`: HCI, firmware, BlueZ, rfkill, Powered, errors, Quick Settings event path, pairing result.
- `LOCATION-PRIVACY-STATUS.md`: global policy, provider, app permissions, Maps integration, fix-source caveats, what is actually enforceable.
- `TEST-MATRIX.md`: PASS/FAIL/BLOCKED per physical and unit test, logs, screenshots, timestamps.
- `FINAL-STATUS.md`: exactly what changed and was deployed, boot regression results, remaining blockers, explicit owner's unplug checks, and complete rollback.

### Final acceptance (release gate)

**PASS only when**: (1) battery/charging penguin continues working; (2) both ghost PC + Live Console icons go OFF on physical USB disconnect and stay off on wall charger; (3) PC returns ON with genuine data connection; (4) console ON reflects actually live host-connected console; (5) Bluetooth tile has a real status+control path and accurately powers the device **if a usable controller exists**, otherwise truthfully diagnoses the blocker without generic build placeholder; (6) Location tile actually switches global provider/policy and has explicit privacy guarantees/limits, independent of hardware GPS fix; (7) current source matches deployed phone; (8) boot, Wi-Fi, browser, lockscreen layout and navigation remain good.

**Do not declare all of 22000 complete if Bluetooth hardware/firmware is still blocked.** Report honest partial completion and precise next dependency. No speculation, no synthetic success, no unsafe console shutdown, no old-branch overwrites. Deliver real fixes wherever feasible and verified limitations where not.

**PENGUIN 22000: GHOSTS OUT. RADIOS ON. PRIVACY REAL. 🐧🔌📡🛰️**
