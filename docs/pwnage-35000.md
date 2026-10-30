# PWNAGE-35000 — Buttersmooth Nuxel — Implementation Report

## Summary
Offline-reachable work completed. On-device deploy and physical verification
remain **BLOCKED** from this host (phone SSH is source-IP gated and no USB
console enumerates — see Deployment).

Offline tests: **99 passed** (`tests/pwnage34000 tests/a80 tests/pwnage30000
tests/pwnage33000 tests/a72 tests/pwnage31000/test_preload_packaging.py`).

## 1. Performance
- No new polling introduced. Transport facts (`tri_link_status`) are cached for
  5 s inside `system_indicators.py` so the 3 s indicator tick never re-reads
  `/proc/config.gz` on every pass.
- Navdock premultiplied-alpha change removes one source of non-deterministic
  edge compositing (`tools/s10plus/a45/gen-navdock-art.py`).
- No heavy transparency/effects were added; the lockscreen additions use
  `image-rendering: pixelated/crisp-edges`, tiny flex cells and no filters.

## 2. Keyboard haptics
- Traced: fallback keyboard → `NuxelHaptics.tap()` → `NuxelBridge.call('haptics',
  'pulse')` → `pwa_store.haptics_pulse()` writes `/run/nuxel-haptics/haptics.cmd`;
  daemon writes `/sys/class/timed_output/vibrator/enable`. No code defect found
  in the userspace chain on this branch; physical vibration still requires
  on-device confirmation. Not simulated in the UI.

## 3. Back button / app lifecycle
- Fixed a real same-origin iframe history bug: Back used `history.length > 1`,
  which navigated a freshly-opened app back to `about:blank`/a stale entry
  instead of minimizing it, so the desktop dock painted over the foreground app.
  `app.js` now records a per-surface history baseline and only dispatches an
  in-app Back when the app has actually advanced beyond it; otherwise it falls
  through to the existing minimize-to-Home path.

## 4. Reboot
- Root cause candidate: the GTK host ran `systemctl reboot` synchronously inside
  `action_perform`, so systemd could not stop `nuxel-wayland`/the host while the
  host was still blocked, hitting shutdown timeouts.  Added forked
  `systemctl reboot|poweroff` with gate validation and immediate acknowledgement
  (`tools/s10plus/a45/nuxel-pwa-host.c`).
- `restart`/`power-off` menu entries are now `trigger_allowed: true` (the reboot
  gate already allows them in this repo).

## 5. Wi-Fi / quick settings
- `nuxel-wifi-up.sh` remains event-bounded (no arbitrary long sleeps added).
- Quick-settings handlers already acknowledge via `dataset.pending`; no blind
  change was made without hardware logs. On-device journal is required to
  confirm the remaining "Wi-Fi unavailable" delay.

## 6. Preloading-screen video (`nuxel-preloading-screen.mp4`)
- Asset ruled out: SHA-256 `b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1`
  matches the pinned manifest hash; `ffmpeg` decode exits 0; metadata is
  H.264 High 1080x1920 24 fps, 144 frames, 6.016 s, yuv420p + AAC-LC.
- The PWNAGE-31000 controller and `tools/s10plus/a29/nuxel-session.sh` early
  launch path are intact in the tree and `py_compile` passes.
- On-device playback re-verification is `NEEDS_PHYSICAL_VERIFICATION` (the phone
  is unreachable from this host). The asset is not the cause of "not playing".

## Changed files
- `pwa/nuxel-home/js/app.js`
- `tools/s10plus/a45/nuxel-pwa-host.c`
- `configs/nuxel/power/power-menu.json`
- `pwa/nuxel-apps/settings/power-menu.js`
- `services/nuxel-bridge/src/system_indicators.py`
- `tools/s10plus/a45/gen-navdock-art.py`
- `tools/s10plus/a45/test-lockscreen-unlock.js`
- `tests/a80/test_tri_link_console.py`
- (34000 additions also listed in the 34000 report)

## Tests
- `python3 -m pytest tests/pwnage34000 tests/a80 tests/pwnage30000 tests/pwnage33000 tests/a72 tests/pwnage31000/test_preload_packaging.py` → **99 passed**.
- `node --check` passed for changed PWA JS.
- `python3 -m py_compile` passed for changed Python.

## Deployment
**BLOCKED** — no reachable device channel from this host.

Reachability audit (sanitized):
- SSH `nuxel@10.17.239.166:22` reaches the Nuxel banner, but every available key
  is refused `Permission denied (publickey)` for `nuxel` and `root`.
- Cause: `sshd AllowUsers` allows only `10.20.30.0/24`, `10.15.19.0/24`,
  `127.0.0.1/32`; this host's source is `10.17.239.211`.
- Source bind to the allowed `10.20.30.22/32` alias times out (no return route).
- The phone's private "Nuxel Snoerbreuk" WLAN (`10.20.30.16/24`) is not
  L2-reachable from this office Wi-Fi; the saved "Snoerbreuk" profile is not in
  range.
- No USB CDC-ACM gadget is enumerated on the host.
- Verdict: `BLOCKED_EXTERNAL_RESOURCE`. No physical vibration, reboot timing,
  Wi-Fi association/DHCP timing, Back behaviour across native apps, or preload
  video playback could be verified on hardware from this session.

## Rollback
`git checkout --` the listed files, then restart affected services on-device:
`nuxel-http-bridge`, `nuxel-wayland`, `nuxel-web`. Rebuild `nuxel-pwa-host` from
the previous commit if the C change was compiled on-device.

## Remaining hardware verification
Physical vibration, real reboot timing, real Wi-Fi association/DHCP timing, Back
behaviour across native apps, and preloading-screen playback all remain
`NEEDS_PHYSICAL_VERIFICATION`.
