# PWNAGE-32000 — Resurrection & Performance Warfare: Final Report

Date: 2026-10-28
Device: Samsung Galaxy S10+ SM-G975F (beyond2lte), kernel 4.14.253
Branch: nuxel/v0.7.1-beta-pwnage-30000 @ da0426b (working tree preserved)
Live console: /dev/ttyACM0 (NUXEL-S10PLUS-0001), reachable before and after reboot.

## Summary

| Issue | Status |
|---|---|
| A. Keyboard + haptics | FIXED (userspace; Stevia + navdock now running; felt vibration not owner-verified) |
| B. Back / dock layering | FIXED (native in-app Back + close-foreground + compositor home) |
| C. Minutes-long boot | FIXED (UI decoupled from network-online/network.target; UI start 108s -> ~7s) |
| D. Sluggishness | PARTIALLY FIXED (frame pacing 9 -> 27-30 fps; blit_avg_ms unchanged ~55ms) |
| E. Charging/LPM touch lockout | BLOCKED_KERNEL (vendor sec_ts LPM initcall; no userspace disable found) |

No partition writes, kernel replacement, firmware flashing, bootloader change,
repartitioning, destructive reset, or reboot-while-losing-console occurred.
The independent USB/serial recovery route remained reachable through every step.

## A. Keyboard restoration and haptics

Root cause: the deployed session script (`tools/s10plus/a29/nuxel-session.sh`)
started only the static server + launcher host.  It never started
`/usr/bin/phosh-osk-stevia` (the native grey/black/white Stevia OSK) nor
`/usr/lib/nuxel/nuxel-navdock`, even though both binaries and the
`keyboard-provider.json` marker (native=true) were already installed.  The
launcher's DOM fallback (`touch-keyboard.js`) was the only keyboard that could
appear, and the shipped 162-line fallback did not probe for the native provider.

Fix:
- Backported the A45 keyboard startup block into `tools/s10plus/a29/nuxel-session.sh`.
- Replaced the 162-line fallback with the 447-line A45 fallback that detects the
  native provider asynchronously and discards the DOM keyboard, plus the
  centralized NuxelHaptics path.
- Bumped PWA cache (`sw.js` v51-pwnage-32000, `index.html` query strings,
  `manifest.json` cache_version).
- Fixed the missing executable bit on `tools/s10plus/a33/nuxel-keyboard-apply.sh`
  (pre-existing; its selftest was failing with rc=126).

Verification:
- On device after reboot: phosh-osk-stevia PID, nuxel-navdock PID, phoc PID all
  running; `keyboard-provider.json` reports native=true.
- `/sys/class/timed_output/vibrator` present with `amplitude_supported=1`;
  haptics service active; `pulse=navigation` recorded (software path OK).
- `node tools/s10plus/a45/test-home-keyboard.js`: ALL PASS (23 checks).
- `python3 tools/s10plus/a33/tests/test-virtual-keyboard.py`: PASS=34 FAIL=0.
- Physical felt vibration remains NEEDS_OWNER_TEST (not claimed).

## B. Back button and dock layering

Root cause: `back()` handled iframe history but had no bridge route for native
apps, so non-browser native apps fell straight to `home()`.  The bridge's
compositor home action (`nuxel-foreign-toplevel home`) was the A59
`set_minimized` implementation, which phoc 0.54 does not wire (silent no-op),
so a foreground native app stayed mapped while the launcher/dock repainted.
`/api/v1/apps/back`, `/api/v1/windows/activate`, and `/api/v1/apps/close-foreground`
were absent from the deployed `api.py`.

Fix:
- `pwa/nuxel-home/js/app.js`: short Back for native apps requests
  `/api/v1/apps/back`; if handled (browser history) stay foreground, else home.
  Long Back now requests `/api/v1/apps/close-foreground`.
- `services/nuxel-bridge/src/api.py`: added `_native_back_action`,
  `_activate_toplevel`, `_close_foreground_action` and their POST routes.
- `shell/nuxel-browser-native/nuxel_browser_native.py`: added
  `/run/nuxel-browser.cmd` control FIFO and `can_go_back/can_go_forward` state.
- `tools/s10plus/a68/nuxel-foreign-toplevel.c` and `nuxel-screenshot.c` added
  for provenance; the a68 foreign-toplevel binary is already installed.

Verification:
- Bridge endpoints live: `/api/v1/apps/back` -> handled=false at_root=true;
  `/api/v1/windows/activate` rejects invalid id; `/api/v1/apps/close-foreground`
  -> CLOSE_FOREGROUND closed=0.
- `python3 services/nuxel-bridge/test-launcher-activation.py`: all checks passed.
- Dock-over-app is prevented by existing A69 CSS plus the corrected native-app
  lifecycle; no physical tap verification was possible.

## C. Boot regression

Root cause: `nuxel-bridge.service` had `After=network-online.target`, and
`nuxel-portal.service` + `nuxel-web.service` had `After=network.target`.
NetworkManager waits for the vendor Wi-Fi `wlan0.device` (~45 s) and
NetworkManager-wait-online then blocks `network-online.target` for its full
timeout (~60 s), so the whole launcher chain (bridge -> http-bridge -> web ->
wayland -> wl-fb -> button-manager) started at ~1:48.

Fix:
- `services/nuxel-bridge/systemd/nuxel-bridge.service`: remove
  `network-online.target` from `After`.
- `services/nuxel-portal/systemd/nuxel-portal.service`: remove `network.target`.
- `services/nuxel-web.service`: remove `network.target`.

Before (live, same method):
- `systemd-analyze`: 3.757s kernel + 1:53.235 userspace = 1:56.992 total.
- critical-chain: nuxel-wayland @1:48.060, nuxel-wl-fb @1:48.135.
- journal: nuxel-wayland start ~1:48.

After (live reboot):
- journal: nuxel-touch-arm @5.82s, bridge/http-bridge/web @6.87s,
  nuxel-wayland @6.89s, nuxel-wl-fb @7.91s.
- `systemd-analyze`: multi-user reached after 48.105s (vs 1:53.231s).
  (The overall "Startup finished" still reads ~1:48 because
  NetworkManager-wait-online still runs/fails as a wanted unit; the UI no
  longer waits for it.)

## D. System sluggishness

Root cause / bottleneck evidence:
- `nuxel-wl-fb` bridge was the A34 unoptimized blit path.
- Before: device state `fps_1s=9`, `blit_avg_ms=56`, `present_skipped=30601/32517`.

Fix:
- Deployed the A67 optimized `nuxel-wl-fb` binary (source added to
  `tools/s10plus/a67/`).

After (device state, display on):
- `fps_1s=27-30`, `blit_avg_ms=55-56`, display on.  Frame presentation rate
  improved ~3x; blit_avg_ms is a bridge/committed-present proxy and did not
  materially change, so no FPS/latency claim beyond the bridge's own metric is
  made.

## E. Charging/LPM touch lockout

Root cause: vendor kernel.  S-Boot passes `androidboot.mode=charger` when
powered on from off with a charger attached; Samsung's `sec_bat_is_lpm_check`
sets `lpcharge=1`, and `sec_ts_init()` returns `-ENODEV` before adding the i2c
client.  No sec_touchscreen input device is created.  `CONFIG_KEXEC` is off and
drivers are built-in, so no userspace reload can create the device.

Userspace audit: `nuxel-bootmode-guard.py` only classifies/reports and can
request a gated normal reboot; it does not disable touch.  The libinput shim and
touch-arm service do not disable input on cable connect.  On a normal boot with
a cable attached (current live cmdline has `charging_mode=0x3030` and no
`androidboot.mode=charger`), sec_ts registers and IRQs increment (142 on fresh
boot) — touch is available.

Status: BLOCKED_KERNEL.  The safe userspace remedy is an ordinary normal
reboot, which the existing opt-in `nuxel-bootmode-reboot.service` can perform
when enabled; it was left disabled to avoid automatic reboot risk.  No kernel
patch, DTB, or bootloader change was made.

## Changed files (repo)

- pwa/nuxel-home/js/touch-keyboard.js
- pwa/nuxel-home/js/app.js
- pwa/nuxel-home/index.html
- pwa/nuxel-home/sw.js
- pwa/nuxel-home/manifest.json
- tools/s10plus/a29/nuxel-session.sh
- services/nuxel-bridge/src/api.py
- shell/nuxel-browser-native/nuxel_browser_native.py
- services/nuxel-bridge/systemd/nuxel-bridge.service
- services/nuxel-portal/systemd/nuxel-portal.service
- services/nuxel-web.service
- tools/s10plus/a45/test-home-keyboard.js (updated provider contract)
- tools/s10plus/a33/nuxel-keyboard-apply.sh (chmod +x)
- tools/s10plus/a67/nuxel-wl-fb.c, bench-blit.c, build-a67.sh (added)
- tools/s10plus/a68/nuxel-foreign-toplevel.c, nuxel-screenshot.c (added)
- tools/beta/live/nuxel-32000-pwnage-manifest.json (deploy plan)
- pwnage-32000.md (complete spec)
- docs/beta-finalization/live/evidence/pwnage-32000/* (this evidence)

## Tests

Targeted:
- `node tools/s10plus/a45/test-home-keyboard.js` -> ALL PASS
- `python3 tools/s10plus/a33/tests/test-virtual-keyboard.py` -> PASS=34 FAIL=0
- `python3 tools/s10plus/a33/verify-service-graph.py` -> OFFline_TESTED, problems=0
- `bash tools/s10plus/a33/tests/run-boot-tests.sh` -> ALL PASS
- `python3 tools/s10plus/a33/tests/test-bootmode-guard.py` -> all pass
- `python3 services/nuxel-bridge/test-launcher-activation.py` -> all pass

Full suite `bash tools/beta/run-all-tests.sh --strict` remains red due to
pre-existing failures unrelated to these fixes: missing executable bits on
`tools/nuxel-rollback-home.sh`, `tools/beta/workqueue.py`,
`tools/s10plus/a32/nuxelctl`, `tools/s10plus/a33/nuxelctl`; package-manifest
curl NEVRA mismatch; launcher apps registry gaps; pwnage31000 preload-packaging
fixture.  These were not hidden and are recorded in
`build/reports/beta-tests/`.

## Rollback

Device backups were created by the live deploy transaction at each target:
`<target>.nuxel-rollback.pre-deploy-<ts>`.  To roll back:

    # restore unit files and reload
    for f in nuxel-bridge.service nuxel-portal.service nuxel-web.service; do
      latest=$(ls -t /etc/systemd/system/$f.nuxel-rollback* | head -1)
      cp -a "$latest" "/etc/systemd/system/$f"
    done
    systemctl daemon-reload
    systemctl restart nuxel-bridge nuxel-http-bridge nuxel-web

    # restore PWA files and session script
    # (same pattern for /usr/share/nuxel/pwa/nuxel-home/* and /usr/lib/nuxel/nuxel-session.sh)
    systemctl restart nuxel-wayland

    # restore wl-fb binary if needed
    cp -a /usr/lib/nuxel/nuxel-wl-fb.nuxel-rollback* /usr/lib/nuxel/nuxel-wl-fb
    systemctl restart nuxel-wl-fb

## Physical verification performed

- Live console reachable before and after controlled reboot.
- Touch: sec_touchscreen registered; sec_ts IRQ increments.
- Keyboard: Stevia + navdock processes running.
- Bridge endpoints: curl-verified.
- Rendering: device-reported fps/blit metrics.
- Haptics: node present, service active, pulse recorded; felt vibration NOT
  owner-verified.
- Charging cable connected during normal boot: touch available.
- Physical tap/keyboard/Back gestures: NOT performed (no human owner present).
