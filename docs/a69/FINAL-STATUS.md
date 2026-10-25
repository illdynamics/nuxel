# NUXEL A69 (18000) — FINAL STATUS (re-verified 2026-10-25)

**Date:** 2026-10-24 evening (original run) + 2026-10-25 re-verification session
**Agent:** DeepSeek-v4-pro-thinking via CodeSeeQ (`csft`), macOS host
**Connection:** USB CDC-ACM Live Console `/dev/cu.usbmodem101` (VID 0x18d1
PID 0x4ee7, serial NUXEL-S10PLUS-0001) — verified `REACHABLE`
**Target:** Samsung Galaxy S10+ SM-G975F (beyond2lte), Linux `4.14.253 #15
aarch64`, Fedora 43 ARM64
**Repo commit:** `fe3ccd0` (main). Working-tree A70 WIP preserved, not reset.

> **Honest summary:** the shell/launcher truth fixes (battery, single nav, app
> foregrounding) are implemented, committed, deployed and **re-verified live**
> (device hashes == repo HEAD; runtime logs show `BATTERY_HOST_READY` at +3s and
> `NAVOWNER native-dock=present`). **Network is UP again this session** (it was
> down on 2026-10-24), so the Internet baseline (T30) is now PASS and the Maps
> app's real HTTPS tile path is verified reachable. **Speaker, rotation, GNSS,
> NFC and Bluetooth remain blocked by absent vendor firmware/daemons**, and
> VLC/MP3 remain blocked by the absence of `dnf` on the phone. None of these are
> faked as PASS. Details and exact blockers follow.

---

## 1. What was physically modified on the phone

### 2026-10-24 (original run — committed as `b3ee7a9`/`fe3ccd0`)
| Path | Change | Status |
|---|---|---|
| /usr/share/nuxel/pwa/nuxel-home/css/style.css | hide DOM nav when native navdock present; hide dock/drawer when an app is foreground/launching | deployed, hash-verified |
| /usr/share/nuxel/pwa/nuxel-home/js/app.js | dismiss launcher chrome (drawer/search/recents) before app launch | deployed, hash-verified |
| /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js | read battery from host FIRST + immediate 1s/3s re-check | deployed, hash-verified |

### 2026-10-25 (re-verification session — low-risk Maps improvement)
| Path | Change | Status |
|---|---|---|
| /usr/share/nuxel/pwa/nuxel-apps/maps/index.html | added opt-in "Use OpenStreetMap standard tiles" preset button + explanatory hint | deployed, hash-verified |
| /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js | added OSM preset handler (fills template only, never enables downloads / no network call) | deployed, hash-verified |
| /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js | cache name bumped `nuxel-maps-v1` → `nuxel-maps-v2` | deployed, hash-verified |

Pre-patch copies + hashes: `/var/lib/nuxel/a69-backup/` (home PWA) and
`/var/lib/nuxel/a69-backup-maps/` (maps PWA). No kernel/firmware/boot/partition/
package/service-unit change. No agent-initiated reboot. Launcher reload via the
documented `action reload-launcher` (non-disruptive).

---

## 2. A69-01 … A69-13 — root cause, fix, status

### A69-01 — Cold-boot lockscreen battery (FIXED, re-verified live)
- **Root cause:** lockscreen polled the HTTP bridge `phone/status` on a 20s
  interval and treated a not-yet-ready bridge as unknown; the host direct
  `battery-capacity` read (which the status bar uses) was only the fallback.
- **Fix:** lockscreen reads **host** `battery-capacity` first (available the
  instant the launcher document is alive) and re-checks at 1s and 3s; a missing
  reading stays `—`, never a fake 0%.
- **Evidence (current boot):** `HOST_CONFIG_GET battery-capacity` at +0s →
  `BATTERY_HOST_READY level=99 charging=1` at +3s. Device `lockscreen.js`
  sha256 `94849e33…c517` == repo HEAD. Battery node itself is healthy
  (capacity=100, status=Full, voltage 4 316 000 µV).
- **Status: PASS_DEVICE_RUNTIME.**

### A69-02 — Duplicated/overlapped nav bars (FIXED, re-verified live)
- **Root cause:** two nav hosts exist by design — native layer-shell
  `nuxel-navdock` (S10+ authoritative strip) and DOM `#system-navigation`
  fallback. `navigation.js` added `native-nav-present`, **but no CSS rule
  consumed it**, so the DOM copy never hid → two overlapping bars.
- **Fix:** `.native-nav-present #system-navigation { display: none; }`. The DOM
  fallback remains the one true nav when the native dock is absent (VM/desktop),
  so this never hides both hosts.
- **Evidence (current boot):** `NAVOWNER native-dock=present` ×7 in
  `/run/nuxel-home.state`; CSS rule present on device; `nuxel-navdock` process
  running under `nuxel-pwa-host`. Exactly one DOM nav element (offline test).
- **Status: PASS_DEVICE_RUNTIME.**

### A69-03 — Speaker audio (BLOCKED_FIRMWARE — unchanged)
- Exact chain: Exynos ABox → `beyond-madera` ALSA card → Cirrus **CS47L93**
  codec → **CS35L40 ×2** amps. `nuxelctl audio status` = `BLOCKED_FIRMWARE`:
  DSP blobs absent (`cs47l93-dsp{,1,2}.wmfw/.bin`, `cs35l40-dsp1/2.wmfw/.bin`),
  UCM `HiFi.conf` absent, no PipeWire/WirePlumber/PulseAudio daemon, no
  `aplay`/`amixer`. Headset detect (madera-extcon) and the volume mixer path are
  present. No sound without the Cirrus firmware (proprietary; not fetched).
- **Status: BLOCKED_FIRMWARE.**

### A69-04 — Auto rotation (BLOCKED_HARDWARE — unchanged)
- Sensor hub **BCM47752KUB1G** (`ssp,BCM4773`) is down: `ssp_down == true`,
  `ssp_send_cmd failed -1`, `accelerometer_sensor/raw_data = 0,0,0`. No
  BCM4775x sensor-hub firmware, no Samsung `libsensorhub` userspace. IIO stubs
  expose only timestamps. All seven orientation policies + the offline state
  machine are intact (40 tests pass). See `ROTATION-HARDWARE-BOUNDARY.md`.
- **Status: BLOCKED_HARDWARE.**

### A69-05 — GPS/GNSS + Maps (GNSS blocked; Maps improved + tile path verified)
- **GNSS:** no `/dev/gnss*`/`gps*`; GNSS rides the down SSP (`[SSP] GPS: false`).
  Network-IP (geoclue2) would be a **fallback, not GPS** and is labelled as such.
- **Maps:** the genuine offline-first `org.nuxel.Maps` PWA (canvas Web-Mercator,
  IndexedDB tile cache, pins/import/export, OSM attribution, honest location
  permission via NuxelBridge) is deployed and hash-verified. This session added a
  one-tap OSM standard-tile preset that only fills the template — downloads stay
  OFF until the owner opts in, so the app never crawls. Real HTTPS tiles verified
  reachable from the phone: `tile.openstreetmap.org` → HTTP 200 `image/png`,
  `access-control-allow-origin: *` (so the app's CORS fetch works). Offline
  acceptance 8/8 PASS; owner tap/zoom physical check still pending.
- **Status:** GNSS **BLOCKED_HARDWARE**; Maps **PASS_OFFLINE_ONLY** (real tile
  path reachable; physical touch test NOT_TESTED).

### A69-06 — NFC (BLOCKED_HARDWARE — unchanged)
- DT `sec-nfc@27` present; `sec-nfc` I2C driver registered, but no bound device,
  `/sys/class/nfc` only has an empty `nfc_support` sysfs node, no NCI device, no
  firmware. No tag reader can run.
- **Status: BLOCKED_HARDWARE.**

### A69-07 — Bluetooth (BLOCKED_DEPENDENCY — unchanged)
- `rfkill`: bcm43xx Bluetooth **soft-blocked (soft=1)**, hard=0; no `/dev/hci*`;
  no BlueZ (`bluetoothctl`/`btmgmt`/`hciconfig` absent); no BCM BT firmware in
  `/lib/firmware`. Cannot power/scan/pair without BlueZ + BT firmware.
- **Status: BLOCKED_DEPENDENCY.**

### A69-08 — USB-C headset / DAC (NOT_TESTED — unchanged)
- No digital DAC/headset accessory was available; the USB port is occupied by the
  recovery Live Console. Classifying active vs passive would risk the only
  recovery transport, so it was deliberately not exercised.
- **Status: NOT_TESTED.**

### A69-09 — VLC + MP3 player (BLOCKED_DEPENDENCY — unchanged)
- `dnf`/`yum` are **absent** on the phone (`sh: dnf: command not found`); only
  `rpm` (463 pkgs) exists. `rpm -q vlc mpv` → not installed. Network is UP now,
  but without a package manager there is no safe, non-blind install path; a
  manual RPM transaction is a blind package upgrade and is out of scope. No fake
  player UI was added.
- **Status: BLOCKED_DEPENDENCY.**

### A69-10 — Volume rocker latency (limited, audio-blocked)
- Button manager drives the real `beyond-madera` ALSA mixer with an OSD + bounded
  volume preview and a 25% cap. End-to-end latency is not measurable while the
  DAC/amp firmware is absent (no audible output), so this is not scored PASS.
- **Status: PASS_DEVICE_RUNTIME (visual/OSD path only); audible BLOCKED_FIRMWARE.**

### A69-11 — Performance (PASS_OFFLINE_ONLY — unchanged)
- Removed two real costs: duplicate DOM nav (hidden when native dock owns nav)
  and drawer/dock over-painting during launch. Measured device state this
  session: load ~12.3–13.6 dominated by the software-rendered WebKitGTK/Phoc
  path (no DRM/EGL); WebKitWebProcess ~93% CPU, ~247 MB RSS. No placebo knobs.
  A real before/after FPS/p95 table needs an unlocked touch-interactive owner
  session and a frame-capture harness (not fabricated).
- **Status: PASS_OFFLINE_ONLY.**

### A69-12 — Animations / reduced motion (PASS_OFFLINE_ONLY — unchanged)
- Existing restrained drawer/shade animations (~0.20–0.22s cubic-bezier) and
  `prefers-reduced-motion` disable are preserved. No new motion added that could
  hurt latency. Physical swipes need owner touch confirmation.
- **Status: PASS_OFFLINE_ONLY.**

### A69-13 — App drawer foregrounding (FIXED, re-verified live)
- **Root cause:** the Applications drawer opened with `z-index:80` while a
  launched PWA iframe is `z-index:60`; the launcher never dismissed the drawer
  on launch, so the app opened **behind** it.
- **Fix:** `_dismissLauncherChrome()` runs before every PWA and native launch;
  `body[data-app-state="ACTIVE"|"LAUNCHING"]` hides the drawer + dock so the
  chosen surface is the foreground.
- **Evidence:** `_dismissLauncherChrome` called ≥3× in device `app.js` (hash
  `ed800ef0…ee4` == repo HEAD); `body[data-app-state=…]` rules present in device
  `style.css` (hash `acfb751e…cb5` == repo HEAD). Offline invariant tests 5/5.
- **Status: PASS_DEVICE_RUNTIME.**

---

## 3. Sound chain state (exact, re-verified)
- ALSA: `beyond-madera` (index 0, codec CS47L93), `abox_vdma` (1), `abox_dump` (2).
- `nuxelctl audio status`: `BLOCKED_FIRMWARE`; UCM `HiFi.conf` absent.
- PipeWire/WirePlumber/PulseAudio daemon: **none**. alsa-utils: **none**.
- Speaker/BT/DAC audible result: **none possible** (firmware + server + tools absent).

## 4. Rotation / GNSS / NFC truth (re-verified)
- Rotation: no real sensor data (SSP down; raw `0,0,0`). Simulated/manual only.
- GNSS: no hardware fix possible (SSP GNSS down); network-IP is a separately
  labelled fallback, not GPS.
- NFC: no controller/reader exposed (driver registered, no device/firmware).

## 5. Performance / thermal snapshot (measured 2026-10-25, not fabricated)
| Metric | Value |
|---|---|
| Load average | 12.3 → 13.6 (software-rendered WebKitGTK/Phoc; no DRM/EGL) |
| WebKitWebProcess | ~93% CPU, ~247 MB RSS (single snapshot) |
| nuxel-pwa-host / nuxel-wl-fb / phoc | 42.9% / 35.7% / 28.6% CPU |
| Memory | 7 598 MB total, 6 728 MB available, 0 swap |
| Thermal | BIG 59°C, MID/LITTLE 51°C, G3D 46°C, battery 26.6°C (normal) |

## 6. Rollback
Home PWA: `cp -a /var/lib/nuxel/a69-backup/{style.css,app.js,lockscreen.js} …`
Maps PWA: `cp -a /var/lib/nuxel/a69-backup-maps/{index.html,maps.js,sw.js} …`
then `printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd`.
Full details in `RISK-AND-ROLLBACK.md` and `observations/live-reverify-20261025.md`.

## 7. What would unblock the remaining hardware items
1. **Speaker:** owner-provided Cirrus CS47L93 + CS35L40 DSP firmware (license/
   provenance verified) + a Fedora ARM64 audio server (PipeWire/WirePlumber) +
   alsa-utils; then generate the UCM HiFi.conf on-device.
2. **Rotation:** owner-provided BCM4775x SSP sensor-hub firmware + a lawful
   sensor-hub userspace on the existing 4.14 kernel.
3. **GNSS/NFC:** same SSP firmware for GNSS; NFC driver/firmware bring-up for
   `sec-nfc`.
4. **Bluetooth:** BlueZ + BCM43xx HCD firmware; then WirePlumber bluez5 endpoint.
5. **VLC/MP3:** a package manager (`dnf`) on the phone (network is now UP, but
   `dnf` itself is absent — the blocker is the missing tool, not connectivity).
