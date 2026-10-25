# NUXEL A69 (18000) — FINAL STATUS

**Date:** 2026-10-24 (evening CEST)
**Agent:** DeepSeek-v4-pro-thinking via CodeSeeQ (`csft`), macOS host
**Connection:** USB CDC-ACM Live Console (`/dev/cu.usbmodem2201`, VID 0x18d1 PID 0x4ee7)
**Target:** Samsung Galaxy S10+ SM-G975F (beyond2lte), Linux `4.14.253 #15 aarch64`, Fedora 43 ARM64
**Repo commit:** `37bc270` (WIP preserved, not reset)

> **Honest summary:** the shell/launcher truth fixes (battery, single nav, app
> foregrounding) are implemented, deployed to the live phone and evidenced on a
> real cold boot. **Real speaker/rotation/GPS/NFC/Bluetooth are all currently
> blocked by missing vendor firmware/daemons/connectivity**, and VLC/MP3 install
> is blocked by the absence of `dnf` plus no network. None of those are being
> faked as PASS. Details and exact blockers follow.

---

## 1. What was physically modified on the phone
| Path | Change | Status |
|---|---|---|
| /usr/share/nuxel/pwa/nuxel-home/css/style.css | hide DOM nav when native navdock present; hide dock/drawer when an app is foreground/launching | deployed, hash-verified |
| /usr/share/nuxel/pwa/nuxel-home/js/app.js | dismiss launcher chrome (drawer/search/recents) before app launch | deployed, hash-verified |
| /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js | read battery from host FIRST + immediate 1s/3s re-check | deployed, hash-verified |

Pre-patch copies + hashes: `/var/lib/nuxel/a69-backup/` (see RISK-AND-ROLLBACK.md).
No kernel/firmware/boot/partition/package/service-unit change. No agent-initiated reboot.

---

## 2. A69-01 … A69-13 — root cause, fix, status

### A69-01 — Cold-boot lockscreen battery (FIXED on device)
- **Root cause:** the lockscreen only polled the HTTP bridge `phone/status` on a
  20s interval and treated a not-yet-ready bridge as unknown; the host direct
  `battery-capacity` read (which the status bar uses) was the fallback branch only.
- **Fix:** the lockscreen now reads the **host** `battery-capacity` first (available
  the instant the launcher document is alive) and re-checks at 1s and 3s; the HTTP
  bridge still supplies the charging glyph. A missing reading stays `—`, never 0%.
- **Evidence:** cold-boot `/run/nuxel-home.state` shows `battery-capacity` read at
  +3s and `BATTERY_HOST_READY level=100 charging=0` on the 19:49:14 boot (battery
  was genuinely Full). **Status: PASS_DEVICE_RUNTIME** (agent-observed via logs;
  owner visual confirmation still invited).

### A69-02 — Duplicated/overlapped nav bars (FIXED on device)
- **Root cause:** two nav hosts exist by design — the native layer-shell
  `nuxel-navdock` (the S10+ authoritative strip that sits above the Stevia OSK)
  and the DOM `#system-navigation` fallback. `navigation.js` added a
  `native-nav-present` class when the dock is up, **but no CSS rule consumed it**,
  so the DOM copy never hid → two overlapping Back/Penguin/Tabs bars.
- **Fix:** added `.native-nav-present #system-navigation { display: none; }`.
  The DOM fallback remains the one true nav when the native dock is absent
  (VM/desktop), so this never hides both hosts.
- **Evidence:** live log `NAVOWNER native-dock=present` + the CSS rule deployed.
  **Status: PASS_DEVICE_RUNTIME** (owner visual confirmation invited).

### A69-03 — Speaker audio (BLOCKED_FIRMWARE)
- Exact chain: Exynos ABox → `beyond-madera` ALSA card → Cirrus **CS47L93** codec
  → **CS35L40 ×2** amps. `nuxelctl audio status` verdict `BLOCKED_FIRMWARE`: the
  codec/amp DSP blobs are absent (`cs47l93-dsp{,1,2}.wmfw/.bin`,
  `cs35l40-dsp1/2.wmfw/.bin`), UCM `HiFi.conf` absent, and there is no PipeWire/
  WirePlumber/PulseAudio server or `aplay`/`amixer`. Headset detect (madera-extcon)
  and the volume mixer path are present. No sound can be produced without the
  Cirrus firmware (proprietary; not fetched — needs owner-provided provenance).
- **Status: BLOCKED_FIRMWARE** (not API-claimed).

### A69-04 — Auto rotation (BLOCKED_HARDWARE)
- Sensor hub **BCM47752KUB1G** (`ssp,BCM4773`) is **down**: `[SSPBBD]: ssp_down == true`,
  `ssp_send_cmd failed -1`, `accelerometer_sensor/raw_data = 0,0,0`. No BCM4775x
  sensor-hub firmware in `/lib/firmware`, no Samsung `libsensorhub` userspace.
  IIO devices expose only timestamps, no raw axes. All seven orientation policies
  and the offline state machine are intact (40 tests pass); forced/manual modes do
  not need a sensor. See `ROTATION-HARDWARE-BOUNDARY.md`.
- **Status: BLOCKED_HARDWARE.**

### A69-05 — GPS/GNSS + Maps (BLOCKED_HARDWARE / BLOCKED_DEPENDENCY)
- No `/dev/gnss*`/`/dev/gps*`; GNSS rides the down SSP (`[SSP] GPS: false`).
  `geoclue2` is installed but is network-IP-only and the network is off. A usable
  Maps app needs real HTTPS tiles; Wi-Fi is currently disconnected (T30 FAILED),
  so tiles/search cannot be validated this session. A network-IP fix would be a
  **fallback, not GNSS** and is labelled as such.
- **Status: BLOCKED_HARDWARE** (GNSS), **BLOCKED_DEPENDENCY** (Maps needs network).

### A69-06 — NFC (BLOCKED_HARDWARE)
- DT `sec-nfc@27` present; `sec-nfc` I2C driver registered, but **no bound device**,
  no `/sys/class/nfc`, no NCI device node, no firmware. No tag reader can run.
- **Status: BLOCKED_HARDWARE.**

### A69-07 — Bluetooth (BLOCKED_DEPENDENCY)
- `rfkill` shows `bcm43xx Bluetooth` **soft-blocked (soft=1)**, hard=0; **no
  `/dev/hci*`**, no BlueZ (`bluetoothctl/btmgmt/hciconfig` absent), no A2DP stack.
  BCM BT firmware absent. Cannot power/scan/pair without BlueZ + BT firmware.
- **Status: BLOCKED_DEPENDENCY.**

### A69-08 — USB-C headset / DAC (NOT_TESTED)
- No digital DAC/headset accessory was available this session, and the USB port
  is occupied by the recovery Live Console. Classifying active vs passive would
  risk the only recovery transport, so it was deliberately not exercised.
- **Status: NOT_TESTED** (documented, not a fake PASS).

### A69-09 — VLC + MP3 player (BLOCKED_DEPENDENCY)
- `dnf` is **absent** on the phone (`sh: dnf: command not found`); only `rpm`
  (463 pkgs) exists and there is **no network**. Fedora ARM64 VLC/mpv cannot be
  installed or verified as genuine runtime. No fake player UI was added.
- **Status: BLOCKED_DEPENDENCY.**

### A69-10 — Volume rocker latency (limited, audio-blocked)
- The button manager already drives the real `beyond-madera` ALSA mixer with an
  OSD + bounded volume preview cue and a 25% bring-up cap. Latency is not
  meaningfully measurable end-to-end while the DAC/amp firmware is absent (no
  audible output), so this is not being scored as PASS.
- **Status: PASS_DEVICE_RUNTIME (visual/OSD path only); audible latency BLOCKED_FIRMWARE.**

### A69-11 — Performance (PASS_OFFLINE_ONLY)
- Removed two real costs: the always-visible duplicate DOM nav (now hidden when the
  native dock owns nav) and the drawer/dock painting above app content during
  launch. No FPS/input-latency benchmark could be run to a meaningful conclusion
  with the launcher locked and no touch driver emulation; a measured before/after
  table is therefore not fabricated. Load average ~12 is dominated by the
  software-rendered WebKitGTK/Phoc path (no DRM/EGL on this kernel).
- **Status: PASS_OFFLINE_ONLY.**

### A69-12 — Animations / reduced motion (PASS_OFFLINE_ONLY)
- Existing restrained drawer/shade animations (~0.20–0.22s cubic-bezier) and
  `prefers-reduced-motion` disables are preserved. No new motion was added that
  could hurt latency. Physical swipes need owner touch confirmation.
- **Status: PASS_OFFLINE_ONLY.**

### A69-13 — App drawer foregrounding (FIXED on device)
- **Root cause:** the Applications drawer opens with `z-index:80` (dock `z-index:90`)
  while a launched PWA iframe is `z-index:60`; the launcher never dismissed the
  drawer on launch, so the app opened **behind** it.
- **Fix:** `_dismissLauncherChrome()` (closes drawer/search/recents/folder/edit
  mode) runs before every PWA and native launch, and
  `body[data-app-state="ACTIVE"|"LAUNCHING"]` now hides the drawer + dock so the
  chosen surface is the foreground.
- **Status: PASS_DEVICE_RUNTIME** (deployed; owner visual confirmation invited).

---

## 3. Sound chain state (exact)
- ALSA: `beyond-madera` (index 0, codec CS47L93), `abox_vdma`, `abox_dump`.
- `nuxelctl audio status`: `BLOCKED_FIRMWARE`; UCM `HiFi.conf` absent.
- PipeWire/WirePlumber/PulseAudio server: **none**. alsa-utils: **none**.
- Speaker/BT/DAC audible result: **none possible** (firmware + server + packages absent).

## 4. Rotation / GNSS / NFC truth
- Rotation: real-vs-simulated = **no real sensor data** (SSP down). Simulated/manual only.
- GNSS: **no hardware fix possible** (SSP GNSS down); network-IP is a separately-labelled fallback, not GPS.
- NFC: **no controller/reader** exposed (driver registered, no device/firmware).

## 5. Regression matrix
| Item | Result |
|---|---|
| T30 Wi-Fi/DNS/TLS/google.nl | **FAILED** — wlan0/wlan1 disconnected, no route/DNS. Owner must reconnect Wi-Fi; credentials untouched. |
| T31 SnekByte | NOT_TESTED (unchanged) |
| T32 Lockscreen artwork/swipe | unchanged; battery bug fixed |
| T33 Native app escapable | unchanged |
| T34 Reboot persist | One physical 19:49 reboot observed (button-manager power menu, `source=key`, not agent-initiated); A69 PWA fixes present after it. |
| T35 Install health | No RPM installs this mission (safe). |

## 6. Performance
No fabricated speed-up percentages. Concrete change: duplicate DOM nav no longer
renders on the phone, and drawer/dock no longer over-paint launching apps. A real
device FPS/p95 table needs an unlocked, touch-interactive session (owner) and a
proper frame-capture harness; see `benchmarks/` (currently empty by design).

## 7. Evidence files
- `PREFLIGHT.md`, `LIVE-VS-REPO.md`, `RISK-AND-ROLLBACK.md`
- `requirements.csv`, `test-matrix.csv`
- `ROTATION-HARDWARE-BOUNDARY.md`
- `logs/boot-state-home.log` (sanitized cold-boot evidence)
- `observations/`, `benchmarks/` (benchmarks intentionally empty)

## 8. Rollback
See `RISK-AND-ROLLBACK.md`. Restore is a 3-file copy from `/var/lib/nuxel/a69-backup/`
plus `action reload-launcher`. Recovery console verified alive across the physical reboot.

## 9. What would unblock the remaining hardware items
1. **Speaker:** owner-provided Cirrus CS47L93 + CS35L40 DSP firmware (license/provenance verified) + a Fedora ARM64 audio server (PipeWire/WirePlumber) + alsa-utils; then capture controls and generate the UCM HiFi.conf on-device.
2. **Rotation:** owner-provided BCM4775x SSP sensor-hub firmware + a lawful sensor-hub userspace on the existing 4.14 kernel.
3. **GNSS/NFC:** same SSP firmware for GNSS; NFC driver/firmware bring-up for `sec-nfc`.
4. **Bluetooth:** BlueZ + BCM43xx HCD firmware; then WirePlumber bluez5 endpoint for A2DP.
5. **VLC/MP3:** a package manager (`dnf`) and network (or a signed offline repo/ostree) on the phone.
6. **Wi-Fi/T30:** owner reconnects a saved network (credentials not in agent scope).
