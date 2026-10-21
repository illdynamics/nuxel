# NUXEL A49 — LIVE USB DEPLOYMENT RECEIPT (2026-10-21)

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820,
kernel 4.14.253, Fedora 43 ARM64, Phoc 0.54.0 / wlroots 0.19.3.
**Console:** USB CDC-ACM "Nuxel S10+ Live Console" (`vid 0x18d1 / pid 0x4ee7`,
serial `NUXEL-S10PLUS-0001`), root shell verified via framed SHA-256 channel.
**Mode after deploy:** `portrait` (safe default restored).

Nothing was flashed, no partition/boot/recovery/kernel was written, no reboot
was performed, and no conflicting input daemon / rotation loop / display stack /
keyboard overlay / vibrator owner was introduced.

## What was deployed (22 files + 1 cache-bump, all SHA-256 verified on-device)

| Target | Source | SHA-256 (8) |
|---|---|---|
| /etc/nuxel/orientation/orientation.json | configs/nuxel/orientation/orientation.json | b1158485 |
| /etc/nuxel/orientation/orientation.schema.json | …/orientation.schema.json | 2b9168e8 |
| /etc/nuxel/orientation/README.md | …/README.md | b162d959 |
| /usr/libexec/nuxel/nuxel-orientationd | services/nuxel-orientation/nuxel-orientationd | d097529d |
| /usr/libexec/nuxel/nuxel_orientation/__init__.py | …/__init__.py | cff4e988 |
| /usr/libexec/nuxel/nuxel_orientation/apply.py | …/apply.py | 18b7877b |
| /usr/libexec/nuxel/nuxel_orientation/policy.py | …/policy.py | 9357f96b |
| /usr/libexec/nuxel/nuxel_orientation/sensors.py | …/sensors.py | b161156e |
| /etc/systemd/system/nuxel-orientationd.service | …/systemd/nuxel-orientationd.service | 2d07aed6 |
| /etc/nuxel/keyboard/keyboard.json | configs/nuxel/keyboard/keyboard.json | 83a192b4 |
| /etc/nuxel/keyboard/keyboard.schema.json | …/keyboard.schema.json | 033b7228 |
| /usr/share/nuxel/nuxel-home/js/qs.js | **merged** (phone A45 + A49) | 353c9de0 |
| /usr/share/nuxel/nuxel-home/css/status-bar.css | **merged** (phone A45 + A49) | e31c140b |
| /usr/share/nuxel/pwa/nuxel-apps/settings/index.html | pwa/.../index.html | 12a45ec4 |
| /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js | **merged** (phone A45 + A49) | e4ff9fb9 |
| /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css | pwa/.../settings.css | 13292e21 |
| /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js | pwa/.../settings-model.js | b910cc80 |
| /usr/lib/nuxel/nuxel-bridge/bridge.py | services/nuxel-bridge/src/bridge.py | e61f844c |
| /usr/lib/nuxel/nuxel-bridge/api.py | services/nuxel-bridge/src/api.py | b9c25815 |
| /usr/local/bin/nuxelctl | tools/s10plus/a33/nuxelctl | c0673413 |
| /usr/bin/nuxel-cast-diag.sh | tools/s10plus/a33/nuxel-cast-diag.sh | d2516a57 |
| /usr/bin/nuxel-typec-diag.sh | tools/s10plus/a33/nuxel-typec-diag.sh | 9eaa1818 |
| /usr/share/nuxel/nuxel-home/sw.js | phone sw.js, CACHE_VERSION bumped | 74fcf590 |

`/var/lib/nuxel/orientation/` created `root:nuxel 2775`; `nuxel-orientationd.service`
enabled; `nuxel-bridge` + `nuxel-http-bridge` restarted.

## Drift discovered and handled (NOT clobbered)

Three launcher files had drifted from the A49 base (the running phone carried
A45/A47 work not present in the repo at `9229908`): `qs.js`, `status-bar.css`,
`settings.js`. Each was pulled from the device, the A49 patch applied on top
(`git diff 9229908..HEAD` hunks), syntax-checked with `node --check`, and only
then deployed. The phone's `sw.js` (cache version `v29-a47-workday-stabilization`,
not in the repo) was bumped to `v30-a49-orientation` so the cache-first service
worker stops serving the stale precached `qs.js`/`status-bar.css`.

## Verified live (not simulated)

- `nuxel-orientationd selftest` → **PASS**.
- `nuxel-orientationd modes` → all **seven** modes, correct allowed sets.
- `nuxel-orientationd set portrait|auto|landscape` → `success:true`, state
  persisted to `/var/lib/nuxel/orientation/state.json`.
- `nuxel-orientationd set banana` → rejected (`unknown orientation mode`).
- Full RPC chain: HTTP `POST /api/v1/rpc {orientation.get|modes|set}` →
  D-Bus `OrientationGet|Modes|Set` → daemon → persisted state. Verified with
  curl on the device loopback.
- D-Bus introspection shows `OrientationGet/Modes/Set` registered.
- `qs.js`/`status-bar.css`/`settings.js`/`index.html` served over
  `http://127.0.0.1:8000` with A49 markers.
- Services active: `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-orientationd`,
  `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-haptics`.

## Honest hardware blockers (recorded, not claimed)

| Area | Evidence | Verdict |
|---|---|---|
| Auto-rotation sensors | Samsung SSP hub: `accelerometer_sensor`/`gyro_sensor` IIO devices expose **no** `in_accel_*_raw` channel (only buffer/scan_elements); `iio-sensor-proxy` inactive. 9 sensors `present-unreadable`. | auto modes report `sensor unavailable` |
| Physical rotation | `wlr-randr` absent; Phoc runs **HEADLESS-1** virtual output, pixels written by `nuxel-wl-fb` screencopy→`/dev/fb0`. `apply.py` reports `transform_available:false`. | compositor transform + touch calibration unverified |
| USB-C HDMI/DP | `/sys/class/typec` has port0/port0-partner, no DP altmode, no DRM connector. | `TYPEC_ENUMERATED_NO_DP` |
| Wireless casting | `iw` reports P2P; no grim/wlr-screencopy capture, no H.264 encoder, no gnome-network-displays. | `NO_CAPTURE` |
| Keyboard haptics felt buzz | settings + schema deployed; actuator amplitude + OSK per-key hook not yet proven. | UNVERIFIED |

## Rollback

All pre-deploy bytes are preserved off-device at
`tools/beta/live` evidence + host `/tmp/nuxel-deploy/backup-host/` (11 files,
SHA-256 manifest). On-device `*.nuxel-rollback` copies exist for unchanged files.
Repository rollback for the A49 code is `git reset --hard 9229908` (host only).
Deleting `/var/lib/nuxel/orientation/state.json` returns to the `portrait` default.
`systemctl disable --now nuxel-orientationd` removes the policy service.

## Owner next step

UI changes (QS rotate tile, Settings rotation radios) take effect on the next
launcher reload (service worker reinstall on `v30-a49-orientation`) or an
owner-approved reboot. Physical owner proofs remain:
`docs/A49/OWNER-TEST-ORIENTATION.md`,
`docs/A49/OWNER-TEST-EXTERNAL-DISPLAY.md`, `docs/A49/OWNER-TEST-CAST.md`.
