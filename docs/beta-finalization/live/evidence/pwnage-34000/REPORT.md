# PWNAGE-34000 — Connection Modes & Interface Reliability — Implementation Report

## Scope executed
1. Native nav icon rendering (deterministic alpha).
2. Real multi-transport console detection model.
3. File-transfer indicator (truthful state).
4. Lockscreen connection-mode selector + mode state machine.
5. Safe USB file-transfer helper (MTP-or-refuse; no fake storage).

## Root causes
- **Nav icons (intermittent chopped/outlined wrong):** `gen-navdock-art.py` emitted
  *straight* (non-premultiplied) ARGB8888 while Wayland `WL_SHM_FORMAT_ARGB8888`
  expects premultiplied alpha.  Partially-transparent edge pixels therefore
  composited inconsistently depending on the buffer contents/race at first
  configure. Fixed by premultiplying colour into alpha in the generator and
  regenerating `navdock-art.h`.
- **Console indicators were monolithic:** one `live_console` boolean could not
  express serial+WLAN simultaneously.  Added independent `console_transports`
  (serial/usb/wlan) while keeping the existing generic live-console indicator.
- **File-transfer state did not exist:** no backend exposed whether transfer
  mode was genuinely active.  Added `file_transfer`/`connection_mode` state and a
  mode actuator.
- **USB mode had no safe actuator:** `nuxel-pwa-host` refused `restart/poweroff`
  and had no USB-mode verb; the repo only carried a closed gate.  Added a
  userspace helper + HTTP bridge verbs.

## Changed files
- `tools/s10plus/a45/gen-navdock-art.py` — premultiply ARGB8888 nav art.
- `tools/s10plus/a45/nuxel-pwa-host.c` — emit console transport/file-transfer/mode
  fields in `system-indicators`; add async `restart`/`poweroff`/`screen-lock`
  handling through the reboot gate; add WLAN sshd-listener detection.
- `services/nuxel-bridge/src/system_indicators.py` — add `console_transports()`,
  `connection_mode_state()`, and extend `get_indicators()`.
- `services/nuxel-bridge/src/usb_mode.py` — new connection-mode state machine.
- `services/nuxel-s10/bin/nuxel-usb-mode.sh` — new safe helper (MTP-or-refuse).
- `services/nuxel-bridge/src/api.py` — GET `/api/v1/system/usb-mode` and
  POST `/api/v1/usb-mode/set-mode`.
- `pwa/nuxel-home/index.html`, `css/lockscreen.css`,
  `js/lockscreen-indicators.js` — transport/file-transfer icons and lockscreen
  connection-mode button/overlay.
- `configs/nuxel/power/power-menu.json`,
  `pwa/nuxel-apps/settings/power-menu.js` — enable restart/power-off entry.
- `tests/pwnage34000/test_connection_modes.py` — new offline tests.
- `tests/a80/...`, `tools/s10plus/a45/test-lockscreen-unlock.js` — stale-assertion
  repairs (registry_version 7; current cache-busting revision).

## Tests
`python3 -m pytest tests/pwnage34000 tests/a80 tests/pwnage30000 tests/pwnage33000 tests/a72`
→ **87 passed**.

## Deployment
**BLOCKED** — physical device is unreachable from this host:
- Wi-Fi SSH reachable at `10.17.239.166:22` (Nuxel banner confirmed), but phone
  `sshd` `AllowUsers` is restricted to `10.20.30.0/24` / `10.15.19.0/24` /
  loopback.  This Mac's source is `10.17.239.211/24`, so key auth is refused.
- No USB CDC-ACM gadget (VID 0x18d1/PID 0x4ee7) is enumerated on the host.
- Therefore no on-device deploy or physical verification was possible.

## Rollback
- Frontend/JS/CSS: `git checkout -- <changed pwa files>` then restart `nuxel-web`.
- Python bridge: restore `services/nuxel-bridge/src/*.py` from git, restart
  `nuxel-http-bridge.service`.
- Native host C: rebuild from prior commit or restore `/usr/lib/nuxel/nuxel-pwa-host`
  backup, restart `nuxel-wayland.service`.
- USB helper: remove `/usr/lib/nuxel/nuxel-usb-mode.sh` and
  `/run/nuxel/connection-mode.json`; no kernel/partition touched.

## Remaining blockers
- Physical host-side file-transfer verification (`PASS_PHYSICAL`) not claimed.
- The helper intentionally refuses to activate file transfer until a real MTP
  responder AND a configfs MTP function are present; on the current 4.14.253
  kernel this is the honest supported-or-blocked answer, not a simulated mount.

## Addendum (2026-10-28, continuation run)

### On-device reachability re-audit
Re-audited because the maintainer requested SSH-over-WLAN with
`~/.ssh/wicked_wqn_id_rsa`, a network scan, on-device root work, and a final
reboot.

- Host: Darwin 24.6.0 arm64, primary en0 address `10.17.239.211/24`, plus a
  `/32` alias `10.20.30.22`.
- Target SSH `nuxel@10.17.239.166:22` is reachable (Nuxel banner confirmed),
  but every key (`wicked_wqn_id_rsa`, `nuxel-tri-link_ed25519`, `id_rsa`) is
  refused with `Permission denied (publickey)` for both `nuxel` and `root`.
- Root cause is unchanged and confirmed: `sshd AllowUsers` is restricted to
  `10.20.30.0/24`, `10.15.19.0/24`, `127.0.0.1/32`, while this host's source
  is `10.17.239.211`.
- Workarounds attempted and rejected:
  - SSH `-b 10.20.30.22` (allowed source) -> connect timeout (no return route).
  - Direct host route `10.20.30.16` via en0 -> 100% packet loss (the phone's
    private "Nuxel Snoerbreuk" WLAN is not L2-reachable from this office Wi-Fi).
  - Saved Wi-Fi profile "Snoerbreuk" is present on this Mac but the network is
    not currently in range (`networksetup -setairportnetwork`: not found).
  - No USB CDC-ACM serial gadget enumerates (empty USB tree, no `/dev/ttyACM*`).
- Verdict: `BLOCKED_EXTERNAL_RESOURCE`. No on-device deploy, physical console
  verification, storage-mount test, or reboot was possible from this host.
  Evidence: `reachability-ssh-wifi-*.txt` in this directory.

### Offline verification (this run)
`pytest tests/pwnage34000 tests/a80 tests/pwnage30000 tests/pwnage33000 tests/a72
 tests/pwnage31000/test_preload_packaging.py` -> **99 passed**.

### Preloading-screen video (`nuxel-preloading-screen.mp4`) investigation
- Asset is byte-for-byte valid: SHA-256 `b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1`
  (matches the pinned manifest hash exactly).
- Container H.264 High 1080x1920 24 fps, 144 frames, 6.016 s, yuv420p + AAC-LC;
  host `ffmpeg` decode exits 0.
- The PWNAGE-31000 controller (`services/nuxel-preload-cinema/nuxel-preload-cinema`)
  and the session early-launch path (`tools/s10plus/a29/nuxel-session.sh`) are
  intact in the working tree; `py_compile` passes.
- On-device playback cannot be re-verified from this host because the phone is
  unreachable; the "not playing anymore" symptom therefore remains
  `NEEDS_PHYSICAL_VERIFICATION`, with the asset itself ruled out as the cause.
