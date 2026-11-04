# PWNAGE-72000 — Finish/prove PWNAGE-62000 — final report

**Date:** 2026-11-04 (Europe/Amsterdam) / 2026-11-03T23:10Z UTC
**Repository:** `/x/nuxel`, branch `main`, HEAD `0bed35d881ba674a21f67d31501e84f1031992b5`
**Target:** `root@10.20.30.16`, SM-G975F `beyond2lte`, Fedora 43 aarch64
**Kernel:** `4.14.253-gf7194c1d15ed-dirty`
**Boot ID before/after:** `e3b5e426-5c2b-4ac8-ad14-70e2cfb27ab4` (unchanged; no reboot)
**Dirty owner tree:** 154 entries at baseline and at finish; no reset/clean/stash/commit/push.

## Executive result

PWNAGE-62000's live deployment drift was closed over Wi-Fi SSH. The Home manifest
was the Nuxel Clipper manifest on both live install paths and the canonical
wayland unit was stale. The deploy script now stages, backs up, installs and
fail-closed-asserts both files; the rollback script restores them. The atomic
userspace deploy passed (`DEPLOY_OK`, exit 0), the compositor/session restarted
cleanly, source/live hashes now match, and the live shell reports
`FRAMES_OK`, statusbar `ready=true / visible=false / reason=locked`, and navdock
unmapped while locked.

A real locked-screen screenshot was captured and OCR reads **“swipe up to
unlock”**, confirming the lockscreen is the visible surface. The full
native-GTK/Flatpak/WebKit/touch matrix and multi-boot timing statistics were not
performed because they require owner interaction/reboots. No reboot was issued.

**Final status: `PARTIAL_IMPLEMENTATION`** (deployment healthy; physical matrix
and reboot statistics remain `OWNER_ACTION_REQUIRED`).

## What changed

| File | Change |
|---|---|
| `tools/pwnage62000/deploy-pwnage62000.sh` | Backs up, stages, atomically installs `pwa/nuxel-home/manifest.json` to both `/usr/share/nuxel/pwa/nuxel-home/` and `/usr/share/nuxel/nuxel-home/`, and installs `tools/s10plus/a31/nuxel-wayland.service` to `/etc/systemd/system/nuxel-wayland.service`. Added fail-closed content checks for name `Nuxel Home`, `registry_version=12`, registry membership of `org.nuxel.Clipper`/`org.nuxel.Vault`, and `ExecStart=/usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh`. |
| `tools/pwnage62000/rollback-pwnage62000.sh` | Restores the Home manifests and the canonical wayland unit from the timestamped backup. Installed on-phone at `/usr/lib/nuxel/rollback-pwnage62000.sh` (SHA-256 `567cb4cc3bc9855e191f424b2a3fdd9903eafc1ec2eba7e1df7da47bb83933f3`). |
| `tests/pwnage49000/test_pwnage49000.py` | Replaced the stale pinned cache-version assertion with a source-of-truth check (`manifest.nuxel.cache_version` must be non-historical and present in `sw.js`/manifest) and updated the app.js cache-buster to `p62000`. This is shared with the 73000 cleanup. |

No source design was replaced. No live credential, keyring, partition,
bootloader, kernel, DTB, BOOT or firmware state was touched.

## Atomic deployment

- Command: `SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa tools/pwnage62000/deploy-pwnage62000.sh root@10.20.30.16`
- Exit: `0`
- Backup: `/var/backups/nuxel/p62000-20261103T231049Z` (46 files, `SHA256SUMS` present)
- Receipt: `/var/lib/nuxel/diagnostics/pwnage62000-deploy.json` (`deployed_at=2026-11-03T23:11:28Z`)
- Services restarted by the documented deploy script: `nuxel-http-bridge`, `nuxel-button-manager`, `nuxel-wayland`, `nuxel-wl-fb`.
- Result line: `HEALTH manifest/unit parity OK` / `DEPLOY_OK`.

## Source/live parity (post-deploy)

| Source | Live target | SHA-256 |
|---|---|---|
| `pwa/nuxel-home/manifest.json` | `/usr/share/nuxel/pwa/nuxel-home/manifest.json` | `f6d0709ed9974cfc804a60e6ac98ed67f6814d2172dd2cf787da0605ea37b575` |
| same | `/usr/share/nuxel/nuxel-home/manifest.json` | `f6d0709ed9974cfc804a60e6ac98ed67f6814d2172dd2cf787da0605ea37b575` |
| `tools/s10plus/a31/nuxel-wayland.service` | `/etc/systemd/system/nuxel-wayland.service` | `7d00d6754fed7a19af5c4b38f883c1973ba6152eefc692b674b7eee47b7d50a9` |
| `pwa/nuxel-home/index.html` | `/usr/share/nuxel/pwa/nuxel-home/index.html` | `5d93bc8ae0183f0aeb2b2fcfc6c869d0a9e5ffa2c4633c3790bcaf0c1c4ac423` |
| `pwa/nuxel-home/sw.js` | `/usr/share/nuxel/pwa/nuxel-home/sw.js` | `85f7513ef3ee25c19136058b493d9af5706cd1fc4fc1ab13db0d52d0f6a56e69` |
| `pwa/nuxel-home/js/apps.js` | live `js/apps.js` | `aa1666288362f5b68dea8553bc5cce03a7581afa0e83838edc322731c3dc2228` |
| `pwa/nuxel-home/js/app.js` | live `js/app.js` | `a4b69270b5c465fad805d468dad8052d863f0c484504ab23881338d957f24538` |
| `pwa/nuxel-home/js/gestures.js` | live `js/gestures.js` | `dc7e9fec09d81d4f13860c8f9e4b5092794e5dae6d22ad040427a8bed43972e8` |
| `pwa/nuxel-home/js/lockscreen-indicators.js` | live | `d56f9775bd93b2d32f9ce2d35d57bf068dbb111e4f7e765d168e37d95de36827` |
| `pwa/nuxel-home/js/launcher.js` | live | `fdefb18a95fd6129eef19af7d479128ccb4d0478263bc7ed7580d49a6e4f52ed` |
| `pwa/nuxel-home/css/status-bar.css` | live | `d6879a27eaa41434bb81ab727c2cdf297a35fdaa2062c606c7c98297498d9b52` |
| `tools/s10plus/a45/nuxel-session.sh` | `/usr/lib/nuxel/nuxel-session.sh` | `fe61581a46f95b725e90c0f76cd2e2ab4484db0f81cb017c9151bbe2a85ed2e2` |
| `tools/s10plus/a45/nuxel-shell-chrome.sh` | `/usr/lib/nuxel/nuxel-shell-chrome.sh` | `644b564abcb5fb87a9bc30073722fa1889b45cf377a217f2174108b479ad1360` |

The five native binaries rebuilt on the phone are AArch64 (deploy gate passed).
`nuxel-wayland.service` and `nuxel-audio-session.service` both report
`TimeoutStopUSec=2s`.

## Live readiness after deployment

- `/run/nuxel-wl-fb.state`: `FRAMES_OK total=106 ... display=on owner=nuxel-wl-fb`
- `/run/nuxel-statusbar.state`: `ready=true, visible=false, reason=locked, locked=true`
- `/run/nuxel/shell-chrome.json`: supervisor/navdock/statusbar/lock-watch PIDs present
- `/run/nuxel-navdock.json`: `visible=false, mapped=false, lock=locked, home_ready=true`
- `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-http-bridge`, `nuxel-button-manager`, `nuxel-bridge`: all active
- Screenshot: `evidence/screenshots/72000-locked.png` (720×1520, SHA-256 `8d58380d…`), OCR: `swipe up to unlock`

## Physical acceptance matrix

| Case | Result | Evidence |
|---|---|---|
| Home | `NOT_TESTED` — requires unlock/owner interaction | — |
| Locked over Home | `PARTIAL` — lockscreen visibly on screen; statusbar/navdock report hidden/unmapped; app activation not tapped | screenshot + state files |
| Native GTK app | `OWNER_ACTION_REQUIRED` | — |
| Flatpak app (Stremio) | `OWNER_ACTION_REQUIRED` | — |
| WebKit/PWA surface | `OWNER_ACTION_REQUIRED` | — |
| Lock attempt from foreground app | `OWNER_ACTION_REQUIRED` | — |
| Unlock | `OWNER_ACTION_REQUIRED` (owner PIN/gesture) | — |
| Drawer swipe / touch fallback | `OWNER_ACTION_REQUIRED` | — |
| Long-press Back / navigation gesture | `OWNER_ACTION_REQUIRED` | — |
| Console indicators, zero sessions | Host-tested only; live `wlan_active=false, sessions=0` | `system_indicators.get_indicators()` |
| Console indicators, one Wi-Fi SSH session | `OWNER_ACTION_REQUIRED` — the indicator intentionally counts only UID 1000 interactive shells; the run used root SSH commands | live health output |
| Console indicators, serial/USB | `NOT_TESTED`/`BLOCKED_EXTERNAL` — no gadget session present | — |

## Boot/shutdown results

**NOT PERFORMED.** No reboot, power-cycle, forced reboot, SysRq or compositor
replacement was issued. The boot ID is unchanged. The 3-cold-boot/3-reboot
measurement and the 10× statistic remain `OWNER_ACTION_REQUIRED` / `PARTIAL`.

## Host test results

All commands were run from `/x/nuxel`; full output is in
`evidence/72000-host-gates.txt`.

| Command | Exit | Result |
|---|---:|---|
| `python3 tools/s10plus/a33/verify-service-graph.py` | 0 | units=17 problems=0 warnings=5 `OFFLINE_TESTED` |
| `python3 tools/s10plus/a33/tests/test-boot-surface-contract.py` | 0 | all PASS |
| `node tools/s10plus/a33/tests/launcher-registry-test.js` | 0 | all PASS |
| `python3 -m pytest -q tests/pwnage62000` | 0 | 4 passed |
| `node tools/s10plus/a45/test-lockscreen-indicators.js` | 0 | all PASS |
| `node tools/s10plus/a45/test-lockscreen-layout.js` | 0 | all PASS |
| `node tools/s10plus/a45/test-lockscreen-unlock.js` | 0 | 66/66 |
| `node tests/pwnage62000/test_drawer_gesture.js` | 0 | 6/6 |
| `python3 tools/s10plus/a45/test-lockscreen-indicators.py` | 0 | all PASS, a33+a45 C builds |
| `bash tools/beta/tests/test-rollback-reboot.sh` | 0 | PASS=22 FAIL=0 |
| `python3 -m pytest -q tests/pwnage31000/test_preload_cinema.py tests/pwnage31000/test_preload_packaging.py` | 0 | 49 passed |
| `python3 -m pytest -q tests/pwnage49000/test_pwnage49000.py` | 0 | 10 passed |

## Rollback

```sh
/usr/lib/nuxel/rollback-pwnage62000.sh /var/backups/nuxel/p62000-20261103T231049Z
```

The script restores the prior Home manifests, wayland unit, PWA, shell scripts,
native binaries and drop-ins, then restarts the bridge/button/wayland units. It
was syntax-checked and its backup contains the prior manifest/unit hashes, but
a live rollback was **not executed** (would undo the verified deployment).
Rollback state: `NOT_TESTED_LIVE`.

## Remaining owner actions

1. Unlock the phone and run the physical matrix: Home, locked-over-Home, native
   GTK, Flatpak/Stremio, WebKit/PWA, lock attempt, unlock, drawer and long-back.
2. Exercise a real UID-1000 interactive Wi-Fi SSH console and confirm the WLAN
   indicator follows the PTY/session, not interface readiness.
3. Perform owner-approved normal boots/reboots and record the 3×/10× timing
   statistics; do not use forced reboot/SysRq.
4. Re-run the fail-closed GPU image verifier if the 60000/70000 deployment state
   is ever changed.
