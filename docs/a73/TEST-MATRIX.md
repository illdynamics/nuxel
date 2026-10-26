# NUXEL A73 — Test Matrix

Status labels: `PASS_PHYSICAL`, `PASS_DEVICE_RUNTIME`, `PASS_OFFLINE_ONLY`,
`BLOCKED_HARDWARE`, `BLOCKED_DEPENDENCY`, `NOT_TESTED`, `FAILED`.

## Offline / unit tests (executed this run)
| test | scope | result |
|---|---|---|
| `services/nuxel-bridge/test-system-indicators.py` | USB truth + physical veto (40 checks) | PASS_OFFLINE_ONLY |
| `tools/s10plus/a45/test-lockscreen-indicators.py` | native C a33+a45 (`-Wall -Wextra -Werror`) | PASS_OFFLINE_ONLY |
| `services/nuxel-bridge/test-bluetooth-location.py` | BT/Location connectors + policy persistence (11 checks) | PASS_OFFLINE_ONLY |
| `tests/a69/test_a69_pwa_invariants.py` | launcher DOM/nav/drawer invariants | PASS_OFFLINE_ONLY (5 passed) |
| `node --check pwa/nuxel-home/js/qs.js` | JS syntax | PASS_OFFLINE_ONLY |
| gcc compile of a45 host (on-device) | no errors (3 pre-existing warnings) | PASS_DEVICE_RUNTIME |

## Device runtime (executed this run, cable attached)
| test | result |
|---|---|
| Deployed `system_indicators.py` smoke (`python3 …/system_indicators.py`) | PASS_DEVICE_RUNTIME (pc_connected true, physical=[typec:device-role, dwc3:link-on]) |
| HTTP `/api/v1/system/indicators` returns enriched payload | PASS_DEVICE_RUNTIME |
| Native host rebuilt + `nuxel-wayland` restart; console PIDs unchanged | PASS_DEVICE_RUNTIME |
| Bluetooth `status` returns concrete `service_unavailable` + `bcm43xx` driver | PASS_DEVICE_RUNTIME |
| Bluetooth `set-powered true` → `success:false` (no fake ON) | PASS_DEVICE_RUNTIME |
| Location `set-enabled` true/false round-trip + persisted policy | PASS_DEVICE_RUNTIME |
| Location `get-status` honest `no fix` / `enabled` state | PASS_DEVICE_RUNTIME |
| phone.status / orientation.get regression | PASS_DEVICE_RUNTIME |
| Wi-Fi operstate up; HTTPS google.nl TLS OK (301) | PASS_DEVICE_RUNTIME |
| navdock running; launcher web 200; qs.js served with new handlers | PASS_DEVICE_RUNTIME |

## Physical USB matrix (owner-performed disconnect)
| case | Charging | PC connected | Live Console | status |
|---|---|---|---|---|
| Boot without cable | Off | Off | Off | NOT_TESTED (needs reboot w/o cable) |
| Wall charger, no data | On | Off | Off | NOT_TESTED (needs wall charger) |
| PC enumeration, no console | On | On | Off | NOT_TESTED |
| PC + active console | On | On | On | PASS_DEVICE_RUNTIME (current attached state) |
| Disconnect PC (daemon armed) | Off | **Off** | **Off** | **PENDING OWNER UNPLUG** |
| Reconnect PC | real | On | On when session active | PENDING |
| Console service only, disconnected | Off | Off | Off | PENDING |

`docs/a73/evidence/a73-cable-attached-after-native-rebuild.png` is the
attached-state screenshot. The detached-state evidence is captured on-device by
`/usr/lib/nuxel/a73-logger.sh` → `/var/lib/nuxel/a73-usb-unplug.log` (survives
the unplug); the owner replug lets the agent retrieve it.

## Regression (owner-facing)
Cold boot, swipe unlock, battery %, clock/date, back/home/tabs, drawer launch,
camera escape, SnekByte launch, screen sleep/wake — **NOT_TESTED** this run
(require physical interaction); no code in those paths was changed and the
launcher-only restart was verified to reload cleanly.
