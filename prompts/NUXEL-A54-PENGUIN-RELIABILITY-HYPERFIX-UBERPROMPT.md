# 🐧⚡ NUXEL A54 — OPERATION PENGUIN RELIABILITY: HYPERFIX 3000
## Five stubborn S10+ bugs, one evidence-driven repair mission
### Wi-Fi association/DHCP · Seven orientation modes · Status-bar layout · Instant startup telemetry · Two real Camera applications

**Executor:** DeepSeek-v4-pro-thinking (recommended). **Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), CURRENT Fedora ARM64 Nuxel installation, Samsung vendor-kernel lineage, Phoc/Wayland + Nuxel user interface. **Hosts:** user's working Fedora development laptop and/or MacBook with proven USB Live Console. **Scope:** reversible userspace repairs and genuine app installation; non-destructive kernel/hardware analysis only. **Status:** this is a prompt for the local agent; do not claim physical PASS without physical proof.

## EXECUTIVE ORDER — WHAT THE OWNER OBSERVES NOW

1. **Wi-Fi:** network scanning and selecting SSID work. After entering password and tapping Connect, interface hangs at **“Associating DHCP...”**. Previous A51 issue `SpecificObjectNotFound: the access point /new was not in the scan list` must not regress. Get connection all the way through authentication → association → IP address → default route → DNS → real HTTPS, and persist credentials for future reboots.
2. **Rotation:** Settings/Quick Settings show only `Locked` or `Auto`; earlier missions required multiple choices. `Auto` does not physically rotate. Restore all requested modes, true display + touch rotation, and persistence.
3. **Top bar:** a Wi-Fi/circular status graphic bleeds into/through the battery icon. Every icon needs its own measured slot, including during resizing, rotation, animation and startup.
4. **Battery/rotation startup:** battery percentage starts missing/incorrect for minutes after boot. Rotation initially reads **`undefined`**, and mode selection is temporarily unavailable. Make startup immediate and deterministically usable, with well-defined loading/unavailable states only if the actual driver isn't ready.
5. **Camera:** UI still says **“No native camera app installed.”** Install an actual Fedora GTK Camera application, launch it inside Nuxel, and deliver/finish our own Nuxel Camera application alongside it. Diagnose the Exynos camera pipeline honestly; sensor enumeration isn't proof of real frames.

**TOP PRIORITY:** ship stable verified fixes for these exact five problems. **No GUI make-believe, no wallpaper changes, no cosmetic redesign outside the status bar and necessary rotation menu.** Prior A51/A52/A53 source changes exist: READ them before editing so you don't overwrite prior work or create a second implementation.

---

# 0. CONSTRAINTS AND DEFINITION OF DONE

**Non-negotiable:**

- Preserve working Nuxel boot visuals, custom penguin lockscreen and drag-to-unlock, native gray/black/blue keyboard, haptics, three-button Back/Home/Recents and long-Back behavior, Wi-Fi scanner, file-backed media storage, app launcher/store, Home docks, USB Live Console and stable boot.
- Preserve A52 `media_store.py`, private `org.nuxel.Camera` API, persisted media files and permissions. Do not impersonate `org.freedesktop.portal.Camera`.
- Work on CURRENT source and actual installed service revisions; historical v0.6.3-beta code and previous prompt claims are only leads, not live proof.
- The owner is asking for software package installs and userspace fixes. Preview RPM operations first, never remove critical packages via an unchecked transaction. Keep USB serial available. No partition writes, kernel flashing, bootloader/recovery changes, hardware register writes, SELinux disabling, blanket permission loosening, fabricated camera devices, or insecure Flatpak workarounds.
- Before reboot or risky recovery-affecting restart, notify owner, provide rollback and obtain approval. No reboot is needed just to fix JS or install an ordinary app unless technically justified.
- **Do not collect, echo, commit or screenshot Wi-Fi passwords, PSKs, private profile secrets, MAC addresses unnecessarily, tokens, or sensitive persistent identifiers.** Protect logs and passwords; redact by default.
- Distinguish **PASS_PHYSICAL**, **PASS_INTEGRATION**, **PASS_OFFLINE_ONLY**, **PARTIAL**, **BLOCKED_KERNEL/HARDWARE**, and **NOT_TESTED**. Never classify a mere package installation as “camera captures images.”
- No infinite retries, tight sensor polling, unnecessary high-frequency metrics polling or always-running animation on screen-off; the phone previously became warm when locked.

**Deliverable:** a real S10+ on which Wi-Fi connects and persists, battery percentage appears promptly after boot, rotation selector has seven correct modes and automatic behavior where sensors work, status icons do not overlap, GNOME Snapshot launches as a native application, and Nuxel's own Camera app is finished/integrated with honest capability status and real capture where supported.

## Milestone priorities

- **M0:** Baseline and backups; correlate source to deployed version.
- **M1:** Fix Wi-Fi through real internet connectivity.
- **M2:** Fix the startup readiness path (battery and rotation) before adding visual knobs.
- **M3:** Deliver 7-mode orientation, true sensor-driven rotation, persistence and screen/touch coherence.
- **M4:** Eliminate top-bar icon collisions at all rotations/resolutions.
- **M5:** Install native Snapshot, launch it; implement/complete Nuxel Camera separately.
- **M6:** cold-boot physical regression verification and deployment documentation.

---

# 1. FIRST INSPECT THE CURRENT DEVICE, REPO AND RUNTIME

Create dated A54 diagnostic directory **outside the repository** containing text-only, redacted non-secret evidence. Record git HEAD, dirty working tree, deployment hash, service unit files, D-Bus names/methods, process identities, journal for this boot, actual S10+ environment, UI bundles and source maps where possible. Preserve source changes from A49/A50/A51/A52/A53 rather than reverting entire modules to old archived versions.

Map real files with code search; expect to inspect (adapt to actual layout):

- `services/nuxel-bridge/src/bridge.py` and active bridge process
- UI Wi-Fi list, connection state, password dialog and notification code
- persistent NetworkManager profile storage and secret-agent integration
- Quick Settings rotation tile, Settings rotation panel, orientation controller, IIO sensor reader, compositor/presenter and input calibration
- status bar layout and CSS styles, battery icon components, Wi-Fi signal icon and any legacy duplicate overlays
- battery/power-supply backend, metrics daemon, service startup order, readiness events and frontend hydration
- `pwa/nuxel-apps/camera/` and `photos/`, A52 docs and `media_store.py`, native app launcher, XDG `.desktop` registry
- deployed package manager, GTK4/PipeWire, portal and GStreamer services.

Suggested READ-ONLY probes (run only when present; adapt interface names, avoid secrets):

```sh
uname -a; uname -m
cat /etc/os-release
systemctl --no-pager --failed
systemctl --user --no-pager --failed 2>/dev/null || true
nmcli -f GENERAL.STATE,GENERAL.CONNECTION dev show 2>/dev/null || true
nmcli -t -f DEVICE,TYPE,STATE,CONNECTION dev status
nmcli -t -f ACTIVE,UUID,TYPE,DEVICE con show --active
ip -br link; ip -br addr; ip route
ls -la /sys/class/power_supply
find /sys/bus/iio/devices -maxdepth 2 -type f -name '*raw' 2>/dev/null | head -30
command -v monitor-sensor wlr-randr snapshot flatpak gnome-software gst-inspect-1.0
rpm -q snapshot gtk4 libadwaita pipewire wireplumber gstreamer1-plugin-pipewire 2>/dev/null || true
```

Record device model and active compositor. Determine whether your serial console is host-connected and whether its session differs from the ordinary Wayland app user's environment. Test a lightweight rollback command before changing graphical/rotation settings.

**Physical initial reproduction:** record a video or precisely time-stamped manual observations (owner can assist): connect Wi-Fi, drag/open UI, turn phone in each orientation, inspect battery and rotation within first few seconds of boot, open Camera. Capture only application-level debug events, not credentials.

---

# 2. Wi-Fi: TRACE THE REAL NETWORKMANAGER STATE MACHINE, NOT THE UI SPINNER

**Symptom:** “Associating DHCP...” apparently persists after the password is submitted. That is a UI string, *not* an authoritative NetworkManager state. Split each stage into distinct recorded transitions and show which stage is actually failing:

`SSID selected → secret accepted → AP object current → association/authentication → activated Layer 2 → DHCP or configured IPv4/IPv6 → address → default route → DNS → internet connectivity`.

## 2.1 NetworkManager D-Bus contract (mandatory)

Inspect the exact code calling `AddAndActivateConnection`, `AddAndActivateConnection2`, `ActivateConnection` or `nmcli`:

- Previous archived Nuxel code passed `'/new'` as `specific_object` to `AddAndActivateConnection`, triggering `Device.SpecificObjectNotFound`. **That was invalid**; ensure no copy of that code remains in the deployed backend.
- For **Wi-Fi**, a new `AddAndActivateConnection` must use a **currently valid AccessPoint D-Bus object path from the selected device's current scan list** as `specific_object`. Follow the installed NetworkManager API's documented contract.
- For **existing saved profiles**, prefer the appropriate `ActivateConnection` call with connection object + device + valid AP path or documented `/` selection where applicable. Do not conflate the two API contracts.
- SSIDs can repeat across multiple APs; bind selection to BSSID/object identity without leaking sensitive IDs into publicly shared logs. AP objects can disappear after rescans; validate presence and provide bounded rescan/fallback instead of passing stale paths or hanging indefinitely.
- Check correct D-Bus signatures and field types (`a{sa{sv}}`, `o` object paths), correct security key management and `802-11-wireless-security` fields. Do not confuse a *connection profile path* with an AP-specific object path.
- Ensure one active attempt per user selection. Double taps, animation re-render, password-dialog resubmits and stale async callbacks must not create duplicate profiles/competing activations. Cancellation must cancel only the relevant attempt.

## 2.2 Determine whether L2 association or DHCP actually fails

Instrument selected device and `ActiveConnection` state signals, reason codes and connectivity changes, with monotonic timestamps and bounded timeouts. Use **sanitized** outputs from:

```sh
nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status
nmcli -f GENERAL,IP4,DHCP4,IP6,DHCP6 device show <detected_wifi_interface>
nmcli -g GENERAL.STATE,GENERAL.CONNECTION device show <detected_wifi_interface>
networkctl status <interface> 2>/dev/null || true
ip -4 address show dev <interface>
ip -4 route
resolvectl status 2>/dev/null || true
journalctl -b -u NetworkManager --no-pager --since '10 minutes ago'
```

For NM logs, temporarily enable targeted runtime Wi-Fi/DHCP logging if required; redact and restore logging level afterward. Use `nmcli general logging` / NetworkManager documented options. If supplicant logs/driver events are needed, collect only bounded relevant excerpts. Never print password, secrets, confidential SSID or unredacted keyfiles.

**Branch diagnosis by first failing stage:**

1. **Authentication/association failure:** PSK/secrets retrieval, WPA2/3 compatibility, supplicant state, duplicate secret-agent prompts, radio rfkill, firmware reset, AP band/channel/regulatory constraints, PMF, mismatched BSSID, stale scan results. Do not call this DHCP.
2. **Associated but no IP:** validate profile `ipv4.method=auto`, DHCP client/NetworkManager internal DHCP support, lease negotiation and server replies, existing lease permissions, IPv4/IPv6 policy, conflicting network daemons, bridge/firewall interference, clock, driver receive/transmit counters. Diagnose DHCP `DISCOVER/OFFER/REQUEST/ACK` **without** packet-capturing secrets or disabling host firewall indiscriminately.
3. **IP assigned but no route:** test default gateway and route metrics; restore correct DHCP-provided route.
4. **Route but DNS broken:** inspect `resolv.conf` chain, resolved/NM plugin integration; fix configuration, don't hard-code public DNS without an explicit reason.
5. **DNS works but HTTPS broken:** test time sync, CA bundle, MTU and TLS independently.
6. **Backend is connected but UI stuck:** fix bridge event subscription, ignored state changes, pending Promise never resolving, stale frontend state; the UI should reflect truth even when user navigates away and returns.

## 2.3 Persistent connection profiles and passwords

Use NetworkManager's native durable connection profile store with restrictive permissions (`0600` as appropriate); user needs to enter passphrase **once**, then reconnect automatically. Avoid localStorage passwords or rolling your own insecure credential store. Inspect permissions/ownership, system vs user secrets, active NM secret agent and whether it survives boot, rather than bypassing permission control.

Verify autoconnect and priority behavior, known-network reconnect, disconnect/reconnect and BSSID roaming. Preserve pre-existing legitimate profiles. Don't overwrite unrelated system network defaults.

**UI:** show `Authenticating`, `Associating`, `Obtaining IP address`, `Connected`, and time-bounded actionable failures only when corresponding authoritative stages occur. Spinner must clear on failure. Password error should allow re-entry without requiring a reboot. Never show `Connected` until a usable route and tested connectivity exist (separate link-connected and internet-reachable statuses).

**Wi-Fi acceptance matrix:** 3 successful fresh connections; 3 disconnect/reconnect cycles; screen off/on; app switch; an authorized reboot with remembered AP/secret; IPv4/address/gateway/DNS/HTTPS test. If authentication, AP config or DHCP server is actually external, provide exact evidence and a safe diagnostic test against a second known network/hotspot—not arbitrary router changes.

---

# 3. BOOT READINESS: ELIMINATE BATTERY DELAY AND `undefined` ROTATION

These two regressions occurring **right after boot** may share an anti-pattern: frontend renders before D-Bus/sysfs services are ready, initial state doesn't have a defined schema, events aren't subscribed until late, or the UI starts polling after a long timer. Diagnose rather than assume they share one root cause.

## 3.1 Define complete initial state, synchronous hydration and truthful fallback

Create ONE authoritative typed state contract per subsystem. Examples (adapt to code conventions):

```ts
type LoadState = 'initializing'|'ready'|'temporarily-unavailable'|'unsupported'|'error';
type RotationMode = 'auto'|'auto-portrait'|'auto-landscape'|
  'portrait'|'reverse-portrait'|'landscape'|'reverse-landscape';
type BatteryState = { availability: LoadState; percent: number|null;
  charging: boolean|null; status: string|null; source: string|null;
  sampleTime: number|null; };
type RotationState = { availability: LoadState; mode: RotationMode;
  activeAngle: 0|90|180|270; sensorReady: boolean; reason?: string; };
```

- Battery and rotation states must **never** contain `undefined`, an impossible percentage, a `NaN`, or an unhandled Promise in UI. Initialize from persisted rotation setting and immediate battery probe; use clearly labelled `—` only when no valid hardware value exists.
- Do the first battery sysfs read as soon as the relevant backend starts (ideally before the first status-bar render). Don't depend on expensive network, AppStream, camera, telemetry or database initialization.
- Ensure startup ordering, socket/D-Bus activation, permissions, ownership, user services, initial snapshot IPC and subscriptions. Subscribe first, take an initial state snapshot, then deduplicate races/reconcile sequence numbers so an early event isn't dropped.
- If a subsystem is temporarily initializing, UI may show a short honest loading state, but do not gray out *manual rotation modes* merely because sensor-driven auto mode isn't available. Manual orientation must work independently of IIO.
- Avoid a 30–180 second delayed polling fallback. Add bounded retry with backoff only for the unavailable hardware/service; don't hammer D-Bus or `/sys`.
- Do not keep old startup stale state after service recovery. Keep one state source, not duplicated JS/localStorage/D-Bus flags competing.

## 3.2 Real battery semantics

Enumerate `/sys/class/power_supply/*`, `type`, `present`, `capacity`, `status`, `energy_now/full`, `charge_now/full`, voltage/current and UPower entries where available. Distinguish the internal battery from USB power/charger supply, and use real hardware reading. If `capacity` absent, compute percent **only** from compatible now/full pairs of the same unit with sane denominator; clamp 0..100 and flag anomalous sources. Never fake 100 or 0 while backend initializes.

On first status-bar render show readable percentage (e.g., `68%`) if the sysfs node is readable, with charge indicator and proportionate battery icon fill. Values update on device changes and a modest periodic fallback. If the hardware truly has no readable battery on first boot, log the concrete reason and reflect honest loading/unavailable without waiting minutes silently.

Startup acceptance measurements after each boot: screenshot and backend state at **0 s (earliest UI display), +1 s, +3 s, +5 s, +10 s, +30 s, +60 s**. Target battery percentage by the first interactive frame or within ~3 s if hardware ready; no undefined states ever. Persist and rehydrate chosen rotation mode before the first Quick Settings interaction.

---

# 4. ROTATION: RESTORE ALL SEVEN MODES AND MAKE AUTO REAL

The owner first asked for four forced orientations plus three auto filters; A53 simplified the menu to five and the current phone shows only `Locked`/`Auto`. Implement the full set; present the five primary choices clearly and put reverse forced modes in the same selector or an immediately accessible 'More orientations' submenu. Neither old two-state mode nor a purely visual mock selector is acceptable.

| UI choice | Stored stable key | Behavior |
|---|---|---|
| Auto | `auto` | 0° / 90° / 180° / 270° based on gravity, when available |
| Auto portrait | `auto-portrait` | 0° and 180° only |
| Auto landscape | `auto-landscape` | 90° and 270° only |
| Forced portrait | `portrait` | Fixed 0° upright |
| Forced landscape | `landscape` | Fixed 90° using documented handedness |
| Reverse portrait | `reverse-portrait` | Fixed 180° |
| Reverse landscape | `reverse-landscape` | Fixed 270° |

**4.1 Diagnose source and availability:** find the actual IIO accelerometer input, `monitor-sensor` / iio-sensor-proxy when present, device-tree mounting matrix, scale and orientation semantics, permission denials, wrong user D-Bus connection, service lazy startup and unsupported orientation strings. Record real gravity vector readings at portrait, inverted portrait, landscape-left and landscape-right. A gyro alone doesn't give stable absolute gravity orientation; prioritize accelerometer/gravity and use gyro only if validated to improve latency/hysteresis. Auto must not rotate erratically when the phone lies flat.

**4.2 Unify back and front end:** One rotation service/state model, boot initialization, settings persistence, Quick Settings chooser, visible active mode and current angle, signal subscriptions and error mapping. Remove the old boolean `locked/auto` branching or translate it to the new typed enum at a single migration boundary. No frontend option should resolve to `undefined` because the backend only supports two old values. Ensure frontend and backend protocol versions agree and old deployed JS isn't cached.

**4.3 Actually rotate the handset:** trace the physical output through Phoc compositor → headless output / framebuffer presenter (if this remains the rendering path) → phone panel, plus **touchscreen/libinput coordinate transform**, logical viewport, screen dimensions, keyboard layout, app windows, Quick Settings and wallpaper. Don't rotate CSS while touch coordinates stay unrotated; don't set only UI setting and not rotate output. Determine correct rotation convention experimentally. Keep status bar, dock, and touch targets within safe insets.

**4.4 Sensor filtering:** hysteresis/time stability threshold to avoid oscillation, debounce with no arbitrary multi-second lag, ignore near-flat readings, valid orientation pair only for auto-portrait or auto-landscape, last stable orientation behavior, handling of phone wake and sensor reinitialization. Never run high-rate sensor polling while screen off.

**4.5 Safety and persistence:** save last selected **mode** atomically; in auto filters save policy separately from current angle. Forced orientations must work even with sensor driver stopped. If compositor or touch-transform application fails, atomically restore previous known-good mode/angle and retain USB recovery. Provide safe portrait-reset control and documented USB command. New modes persist across restart and authorized reboot. Lock screen and OSK remain usable in all modes or an explicitly documented safe lockscreen orientation if needed.

**Physical verification:** all seven modes selectable, manual four angles respond quickly, auto changes appropriately at all four device positions, auto portrait *never* enters landscape, auto landscape *never* enters portrait, no random turns when face-up, correct touch-target registration in all four directions, return to Home/keyboard interaction, and no `undefined` on cold boot. If sensor driver genuinely missing, forced modes must STILL pass and auto must honestly show blocked with detailed sensor evidence, not a fake PASS.

---

# 5. STATUS BAR: NEVER LET WIFI/CIRCLE ICON OVERLAP BATTERY

Inspect actual top bar DOM and CSS/SVG/canvas compositing on the physical phone. Determine whether the 'Wi-Fi circle thingy' is:
- the correct Wi-Fi icon rendered in the wrong coordinate slot;
- a leftover duplicate legacy status indicator;
- loading animation/spinner left mounted behind the battery icon;
- missing status layout flex constraints / absolute-positioned element;
- CSS transform clipping/scale mismatch between logical 720-class rendering and physical panel;
- hydration transition rendering two elements in the same node;
- an SVG width/height/viewBox issue; or
- a compositor redraw artifact rather than an actual layout collision.

Implement ONE status-bar layout with measured regions and constraints:
- left clock/notifications and right signal/Wi-Fi/battery, direction-sensitive safe inset;
- flex/grid with fixed minimum icon-cell dimensions, stable `gap`, clipping or overflow handling, no overlapping `position:absolute` siblings;
- battery icon, numeric percentage, charging glyph each in owned correctly sized cells;
- icon containers reserve width even when data is absent/loading; animate within their cells only;
- responsive sizing at actual available logical widths, portrait/landscape/reverse, keyboard visible, low signal, 100% battery, system font scaling, accessibility sizing;
- never fake extra status slots or remove actual indicator data to hide the bug.

Detect and remove duplicate DOM nodes, duplicate rendering sources, stale styles and redundant Wi-Fi polling animations. Use computed bounding rectangles/automated overlap assertions; check each pair of visible status items for collisions after layout. Verify screenshot *on device* before and after, including the first seconds after boot and transition from disconnected → connecting → connected. Use CSS grid/flex verified in WebKitGTK, avoiding assumptions from a desktop Chromium preview.

---

# 6. INSTALL GNOME SNAPSHOT NATIVELY ON THE S10+ — PROVE IT

The user sees **“No native camera app installed”**, despite A53 requesting installation. Find *why* prior action didn't yield a usable installed app. Possible causes: A53 executed only offline, package installed on Fedora laptop but not handset, repo/DNF unreachable, wrong architecture, failed RPM transaction, `snapshot` not present in rootfs, missing `.desktop` registry, launcher cannot run native Wayland, missing user D-Bus/PipeWire session, or stale UI detection.

### Mandatory physical preflight

```sh
uname -m
rpm -q snapshot || true
command -v snapshot || true
rpm -ql snapshot 2>/dev/null | grep -E '\.desktop$|/bin/' || true
dnf info snapshot 2>/dev/null || true
dnf repolist
printf 'WAYLAND_DISPLAY=%s\nXDG_RUNTIME_DIR=%s\n' "$WAYLAND_DISPLAY" "$XDG_RUNTIME_DIR"
```

Inspect if package exists in Fedora ARM64 repos for this exact image, disk space, installed package conflicts, GTK4/GStreamer/PipeWire dependencies. Fedora 43 provides `snapshot` RPM, but **that is not proof it is installed on the phone**. Inspect DNF transaction (`--assumeno` where supported); ensure no critical Nuxel removal. If network isn't yet fixed, stage signed compatible AArch64 RPMs and dependency metadata from a trusted Fedora mirror **on the Fedora laptop**, transfer over USB with checksums, and install on the handset with proper dependency resolution. Do not sideload unverified random binaries or install host x86_64 RPMs.

### Installation and launch acceptance

1. Install `snapshot` on **the phone** with `dnf` or verified offline dependency-resolved RPM workflow.
2. Prove `rpm -q snapshot` succeeds **on the phone**, and inspect the real executable and desktop entry.
3. Verify GNOME Snapshot's actual runtime prerequisites—PipeWire, WirePlumber, GStreamer plugins (including `gstreamer-pipewire`, GTK4 sink) and optional libcamera—using upstream requirements and installed RPM names.
4. Launch Snapshot as the unprivileged **Nuxel graphical-session user**, not as root from serial console. Ensure `XDG_RUNTIME_DIR`, session D-Bus, Wayland environment and appropriate GTK backend are correct.
5. Make the native Camera app appear in Nuxel's installed-app list, with a genuine icon, safe `.desktop` launcher, and a clear default/open-with control; remove **false** 'not installed' message only when the actual executable is present and launchable.
6. Open the native window visibly on the S10+, verify Back/Home/Recents, app close, relaunch and persistence after reboot.
7. Distinguish 'Snapshot opens but no usable camera device' from 'Snapshot not installed'. This handset's A52 reported rear **sensor enumerated** but real preview frames **blocked** by ISP/libcamera path. Installing Snapshot does NOT by itself solve this.

**If Snapshot fails to open:** gather executable stderr/journal, missing libraries, GTK/DRM/EGL/Wayland stack, desktop permissions and session bus failures. Repair reversible userspace environment where possible. If a native Wayland app cannot run, report exact blocker and pursue a verified lightweight alternative, but still repair native-app launch infrastructure.

---

# 7. BUILD/FINISH NUXEL'S OWN CAMERA APP IN PARALLEL

The user requests **both** a native Camera application installed **and** 'our own' Camera application finished. Do not satisfy this by adding two launcher icons to the same placeholder app.

### A. Preserve/complete the existing Nuxel Camera PWA

Audit A52 Camera rewrite and `media_store.py`:
- camera permissions and actual state: `NOT_PRESENT`, `SENSOR_PRESENT_NO_PIPELINE`, `READY`, `BUSY`, `PERMISSION_DENIED`, `DEVICE_ERROR`;
- `status`/`list-captures`/`capture`/`open`/`delete`, persistence and stable media index;
- no fake WebRTC `getUserMedia` device enumeration that purports to be functioning phone hardware;
- no full-resolution image data dumped to `localStorage`;
- front/rear choice persisted before stream teardown; shutter responsiveness, gallery integration, cleanup on lock/Home; saved file timestamps/paths, image/video formats and safe content serving;
- correct native camera unavailable message based on actual installed executable and backend, not an out-of-date hard-coded flag.

### B. Create a genuinely Nuxel-owned native GTK4 Camera app

Where current build supports GTK4 native windows, create a modest Nuxel-branded **`nuxel-camera-native`** application (source controlled, package/service-backed) with its own desktop entry, proper native application identity, adaptive touch GUI and clear lifecycle. Reuse secure Nuxel camera/media backend capabilities rather than making unreviewed root calls from GTK. Preferred stack: **GTK4/libadwaita + GStreamer/PipeWire + optional libcamera**, depending on what actually works on the phone.

Minimum behavior:
- honest camera availability card and clear diagnostic reason; a deliberate 'Camera hardware not yet initialized' view is okay, a fake live preview is not;
- live preview using real decoded frames when available;
- capture photo to A52 durable media store; open media in Nuxel Photos; survive reboot;
- optional video only if genuine sensor frames/encoder/audio path works;
- front/rear selector only when actual capture backends exist, with unavailable state otherwise;
- camera/microphone permissions, active camera indicator, timeout handling, device-busy errors;
- responsive portrait/landscape UI, OSK in any relevant text fields;
- lockscreen/Power state releases camera handle; no constantly running service preventing suspend;
- unit and integration tests for non-camera state flow; actual hardware tests for physical PASS.

If existing PWA + native GTK wrapper architecture is more appropriate, justify that choice explicitly and ensure the **native app is genuinely installed, independently launchable, and not merely a webview with an inert camera button**. Do not rebuild Nuxel Photos from scratch or add a third incompatible media database.

### C. Separate hard camera backend from app installation

Review A52 `docs/a52-camera/HARDWARE-BLOCKERS.md`, media topology, `/dev/media*`, `/dev/video*`, sensor subdevices, Samsung FIMC-IS/ISP firmware, pipeline registration, PipeWire camera node enumeration, GStreamer backend, libcamera handler constraints, and test results. Seek a lawful, real frame route; don't invent hardware success. **Do not install proprietary Android camera blobs blindly, patch security checks, write camera registers, modify firmware or flash a replacement kernel in A54.**

If no usable capture backend exists, make both applications open cleanly, present truthful diagnostics, and leave a concrete **kernel/ISP follow-on plan**: required driver/interface, reproducible error, log traces and validation criteria. This is `APP_PASS / CAMERA_FRAMES_BLOCKED`, not total failure or fake success.

---

# 8. SERVICE OWNERSHIP, STARTUP ORDER, PERSISTENCE AND CACHE INVALIDATION

These repeated regressions imply deployment/startup integration issues. Audit service startup chain and make it reproducible:

- one authoritative owner per status subsystem: NetworkManager for network, power_supply/UPower for battery, Nuxel orientation service for policy, compositor/presenter for output angle, app registry for native-app presence;
- no simultaneous stale and current frontend bundles, duplicated event handlers, duplicate systems with different setting key names or mismatch of installed `.desktop` files and manifest;
- systemd dependencies (`After`, `Wants`, readiness notification and restart-on-failure) used only where logical; avoid ordering UI behind network connectivity so offline boot remains fast;
- stable D-Bus methods/schema, forwards/backwards compatibility and explicit unknown-enum migration from old `Locked/Auto` setting;
- per-user session services actually run in correct Nuxel session, not just root's `systemctl --user` context;
- installation/boot build manifests include packages/services so hotfixes survive future reimage/rebuild, not only the current live filesystem;
- deploy to the actual live path, verify source vs deployed SHA-256, invalidate service worker/WebKit cache without erasing unrelated user data;
- avoid DBus active-loop reconnect storms and font loading/layout jumps.

Build a per-service readiness timeline from boot until UI first interactive. Show actual ready timestamps for battery, orientation policy, sensor, Wi-Fi, native application registry. If delayed, root cause must be identified rather than hiding it behind longer loading animations.

---

# 9. TESTS — BOTH OFFLINE AND REAL S10+; DO NOT CLAIM MOCK PASS IS DEVICE PASS

Add deterministic tests and retain prior suites. Minimum:

**Wi-Fi:** wrong key, correct key, AP disappears, duplicate SSIDs, BSSID handoff, stale AP path, two rapid Connect presses, cancel, hidden SSID if supported, DHCP timeout, DNS failure, password save/reconnect, real HTTPS, connection survives restart/reboot, UI doesn't conflate association and DHCP.

**Rotation:** enum round-trip across JS/backend and persistence; `Locked/Auto` migration; no `undefined`; all 7 menu entries; forced rotation without IIO; allowed-axis filtering; hysteresis; display vs touch coordinate correctness at four orientations; OSK and lockscreen compatibility; recovery portrait reset.

**Battery:** correct source, percent from 0–100 and unknown, charging, power absent, `capacity` missing, now/full fallback, duplicate power_supply entries, initial synchronous data, no false 0/100, update after resume, first 3 seconds UI.

**Status bar:** horizontal and vertical states, 0/9/10/99/100% labels, disconnected/connecting/connected Wi-Fi, loading spinner removed, scale 1/2 and actual device logical widths, theme/fonts, keyboard shown, safe-area, collision detector with no intersecting icon boxes.

**Camera:** installed Snapshot physically, proper `.desktop` launch, native Nuxel Camera exists and opens; no frames → honest diagnostic; false detection test; media store file integrity, gallery opens persisted file when physical capture exists, permission denial, Home/lock cleanup, restart integration.

**Regressions:** no duplicated navigation icons, long-Back close, Penguin Home, native OSK, lockscreen drag, power menu, system metrics, Wi-Fi scanning, previous boot visuals, idle thermals, USB console.

Use 2–3 independent tests per change where feasible; attach logs/receipts and source hashes. Capture screen evidence for each physical GUI test with owner cooperation; never synthesize device screenshots.

---

# 10. SAFE LIVE DEPLOYMENT

1. Obtain baseline source revision and deployed hashes; preserve uncommitted work and use isolated branch/worktree if another agent is working.
2. Make rollback backups of every userspace file/config touched and record current RPM package manifest and services.
3. Apply one milestone at a time, run checks, and deploy only touched files; do not overwrite unrelated A49–A53 work.
4. Package operations: inspect DNF dry run, verify ARM64 architecture, signed repos and dependency changes; refuse transactions removing essential Phoc, kernel, USB gadget/console, NetworkManager or desktop services.
5. Use existing USB serial host scripts. Retain a method to restore settings if graphical UI becomes unusable.
6. Restart only affected userspace services; avoid intentionally dropping recovery access, restarting compositor during a delicate app session, or interrupting an agent's parallel task.
7. Do user-visible test immediately after each milestone; rollback that milestone if regression occurs.
8. After all pass, request owner approval for **one controlled cold-boot acceptance test**, with console/recovery already verified.
9. Test with power connected and disconnected where safe; do not turn display off indefinitely if it is overheating. Check background CPU and suspend/idle health.

---

# 11. COLD-BOOT ACCEPTANCE — THE FIX MUST STAY FIXED

Run a controlled cold boot (with owner approval); do NOT infer success solely from hot-restarted services.

**Immediately after boot:**
- Battery is numeric, correct and proportional to icon within ~3 seconds of UI being interactive if capacity is readable.
- Rotation menu doesn't say `undefined`, and manual forced portrait/landscape choices are immediately actionable.
- 7 modes available; current saved mode visible.
- Top status icons have independent slots and no collision.
- Snapshot app is detected as **installed**, selectable and actually opens as a native window.
- Nuxel Camera opens and correctly reports camera hardware status; neither app lies about available real frames.
- Wi-Fi reconnects to the remembered network with correct saved credentials, gets an IP, route and DNS, and verifies HTTPS.

**Endurance:** Repeat manual settings/rotation tests after 1 minute, 5 minutes and after lock/wake; app quit/reopen; reconnect Wi-Fi; check no high CPU when screen dark. Ideally repeat 2–3 boots (only with owner approval) to catch startup races. Track PASS/PARTIAL/BLOCKED with timestamps and evidence.

### Acceptance gates

| Gate | PASS_PHYSICAL only when |
|---|---|
| WIFI-L2 | Actual selected AP association and auth complete |
| WIFI-IP | Valid assigned IP + route + DNS + real HTTPS |
| WIFI-PERSIST | Reconnects after cold boot without password prompt |
| ROT-MENU | All seven entries exposed, real state, persistence, no `undefined` |
| ROT-FORCED | 0/90/180/270 output and touch mapping both work |
| ROT-AUTO | Actual sensor-driven correct permitted rotations |
| STATUS | Never any icon overlap during startup, network changes or rotation |
| BATTERY | Correct percent promptly upon interactive UI and after reboot |
| CAMERA-NATIVE | Fedora Snapshot installed on handset and native window visibly opens |
| CAMERA-NUXEL | Distinct Nuxel Camera installed, usable UI, honest status, Photos integration |
| CAMERA-FRAMES | Real hardware frame/photo if and only if proven; else BLOCKED_HARDWARE |
| BOOT-PERSIST | All supported functions survive an approved reboot |
| RECOVERY | USB console and rollback stay usable |

**If sensors or Exynos ISP are truly blocked by current kernel, ship all independent gates and describe exact limitation. Don't slow down Wi-Fi, battery or GUI fixes while trying to write a brand-new ISP driver.**

---

# 12. REQUIRED OUTPUTS

Create under `docs/a54-reliability/` (no private credentials):

1. `BASELINE.md` — current source/deployed revisions, initial statuses, reproduction, redacted logs.
2. `WIFI-ROOT-CAUSE.md` — exact NM state failure, before/after traces, DHCP reason, API fix, profile persistence, real HTTPS receipts.
3. `BOOT-READINESS.md` — battery and rotation first-ready timeline, service/unit repairs and no-undefined contract.
4. `ORIENTATION-MATRIX.md` — 7 enum modes, sensor calibration, compositor+touch transforms, sensor-blocker details, physical results.
5. `STATUSBAR-LAYOUT.md` — collision root cause, layout measurements, screenshots, regression tests.
6. `CAMERA-INSTALL.md` — Snapshot RPM manifest, installed `Exec`/desktop files, launch evidence, native Nuxel Camera implementation, media integration, real frame limitations.
7. `DEPLOYMENT-AND-ROLLBACK.md` — commands, exact paths, package changes, backup receipts, hashes, safe recovery.
8. `COLD-BOOT-RESULTS.md` — timestamped acceptance table, real vs offline tests, reboots and failures.
9. All code and tests in repo under existing conventions, with separated, reviewable commits and concise final status.

**Report with evidence:** exact root cause for *each* of five issues; changes applied; on-phone installed versions; outcome by gate; physical test results; any blockers remaining; rollback command. Don't say "all fixed" if any on-device gate didn't pass.

---

# 13. FINAL OPERATOR INSTRUCTION

**Fix the real Nuxel S10+, not just a mock UI and not just the Fedora laptop.** Prioritize Wi-Fi connection first, then startup readiness, then orientation and statusbar, then Snapshot + a genuine Nuxel Camera application. Verify each milestone on the handset and preserve everything else already working.

**GO MAKE THE PENGUIN RELIABLE — ONLINE, ROTATING, STATUS CLEAN, BATTERY INSTANT, CAMERA INSTALLED. 🐧⚡🔥**
