# NUXEL A73 / 22000 — FINAL STATUS (honest)

**Date:** 2026-10-25 (session ~18:00–19:30 CEST)
**Branch:** `nuxel/a73-22000-ghostbusters-radio` (off `1aec234`)
**Target:** Samsung Galaxy S10+ SM-G975F, Linux 4.14.253 #15, Fedora 43

## Summary
- **USB truth:** root-caused and fixed in BOTH the Python bridge and the native
  `nuxel-pwa-host` (the lockscreen's primary source of truth). The deployed
  native host was stale (pre-`1aec234`); it was rebuilt on-device from the a45
  source with a new **physical detach veto** (Type-C `data_role` + DWC3
  `link_state`) so a bound gadget / stale `configured` UDC can no longer keep
  the PC or Live Console penguins lit after a physical unplug.
- **Live Console:** now a three-layer truth (`service_armed`,
  `transport_connected`, `session_active`); the icon ON requires all three and
  turns OFF on detach while the daemon stays enabled. The daemon is never
  killed to extinguish its icon.
- **Bluetooth:** real status+control over rfkill/BlueZ. On this S10+ there is
  **no `hci0`** (`CONFIG_BT_BCM43XX=y` but the controller never registers —
  firmware/transport), so the tile truthfully reports `no radio` and refuses a
  fake ON.
- **Location:** real global privacy/provider policy (`enabled` ≠ fix), persisted
  and reboot-safe, with honest `no fix` reporting and Maps policy gating.

## Deployment state
Every changed file is **repo == deployed** (sha256 matched) — see
`REPO-VS-DEPLOYED.md`. Console PIDs 3525/3526 (sole recovery) were never
touched. No kernel/bootloader/firmware flash, no partition change.

## What is PASS and what is NOT
| gate | verdict |
|---|---|
| charging penguin (artwork/size/position/animation preserved) | PASS_DEVICE_RUNTIME |
| PC + Live Console correct **while attached** | PASS_DEVICE_RUNTIME |
| PC + Live Console OFF **after physical unplug** | **PENDING OWNER UNPLUG** (code+offline truth table complete) |
| Bluetooth tile real path + truthful blocker | PASS_DEVICE_RUNTIME (radio = BLOCKED_FIRMWARE) |
| Location tile real global policy | PASS_DEVICE_RUNTIME |
| source == deployed | PASS |
| Wi-Fi / HTTPS / nav dock / launcher reload | PASS_DEVICE_RUNTIME |
| cold-boot visual regression | NOT_TESTED |

**I have NOT declared a hardware PASS.** The physical disconnect gate is
intentionally left to the owner because the USB link is my only channel and
unplugging it interrupts host access.

## Owner's physical unplug check (required to close gate 2/3/4)
1. Confirm the phone shows all three penguins now (PC attached + console).
2. **Unplug the USB cable** from the phone (or the Mac end).
3. Wait ~3 s. Expected: charging penguin off (no power), **PC penguin off,
   Live Console penguin off** — no ghosts.
4. (Optional, recommended) plug in a **wall charger only**: charging penguin
   ON, PC OFF, Live OFF.
5. **Replug the USB cable** to the Mac. Expected: PC ON; Live Console ON once
   the console session re-establishes.
6. Leave it plugged in and tell the agent — the agent then retrieves
   `/var/lib/nuxel/a73-usb-unplug.log` (which recorded the detach/reattach
   timestamps and the backend JSON locally, surviving the disconnect) and
   appends the physical evidence to `TEST-MATRIX.md`.

## Evidence already captured
- `docs/a73/evidence/a73-cable-attached-after-native-rebuild.png` — attached
  lockscreen after the native-host rebuild.
- On-device `/var/lib/nuxel/a73-usb-unplug.log` — continuous state logger
  (detached, PID 14314) recording data_role/link_state/UDC/power/indicators.

## Remaining blockers (exact, not collapsed)
- **Bluetooth radio:** no `hci0` — owner-supplied, licence/provenance-verified
  BCM43xx HCD firmware + working transport is the unblock. Until then the tile
  reports `no radio` honestly. (A2DP audio routing is a further step.)
- **GNSS fix:** sensor-hub present but no GNSS userspace provider is wired;
  location *policy* is fully functional while `location_fix_available` stays
  false. No fake coordinates.

## Rollback
`docs/a73/ROLLBACK.sh` + `/var/lib/nuxel/a73-backup/`. See
`PREFLIGHT-AND-ROLLBACK.md`.

## Commits
- `f24d684` fix(a73/usb): physical detach veto for USB data-link truth
- `39e2fa5` feat(a73/radio): real Bluetooth + Location quick-setting backends
- `5065595` fix(a73/radio): map :manage portal types + bridge-writable policy path
- `cd2d037` chore(a73): bump launcher cache to v43 for qs.js radio/USB changes

**GHOSTS OUT (code-verified; physical unplug pending owner). RADIOS HONEST.
PRIVACY REAL. 🐧🔌📡🛰️**
