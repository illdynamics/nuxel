# A75 — Test Results

## Automated (offline) — all PASS
Run on the macOS host against the repo at `d545289`:
- `services/nuxel-bridge/test-grant-store.py` — ALL PASS (hardened grant loader:
  object form, legacy boolean, false-not-elevated, policy-not-parsed,
  non-object ignored).
- `services/nuxel-bridge/test-wifi-activation.py` — 0 failures (real AP path,
  no `/new`, saved-profile reuse, stale_scan, PSK/WEP rejection, autoconnect).
- `services/nuxel-bridge/test-bluetooth-location.py` — ALL PASS (policy
  round-trip, no fabricated fix, no-adapter truth, blocker names missing hci0).
- `services/nuxel-bridge/test-system-indicators.py` — ALL PASS (USB state
  model: A74 DWC3 link_state not read, Type-C veto, stale UDC/lease/PID
  rejection, six distinct indicator combinations).

## Device-runtime (live) — verified
| ID | Check | Result |
|---|---|---|
| N1 | Bridge readiness: name/object/interface/methods | PASS_DEVICE_RUNTIME |
| N2 | Wi-Fi toggle once (real backend + readback) | PASS_DEVICE_RUNTIME |
| N3 | Wi-Fi scan | PASS_DEVICE_RUNTIME (real AP list) |
| N4 | Wi-Fi connect to public open network | PASS_DEVICE_RUNTIME (assoc+DHCP+route+DNS) |
| N5 | DNS + HTTP | PASS_DEVICE_RUNTIME |
| N5b | HTTPS/TLS | NOT_TESTED (captive portal intercepted; see 02C) |
| N6 | Wi-Fi disable/enable + disconnect/forget | PASS_DEVICE_RUNTIME |
| N7 | Bluetooth toggle | BLOCKED_HARDWARE (bcm43xx no hci0, truthful NO_ADAPTER) |
| N8 | Location toggle | LOCATION_SERVICE_VERIFIED (policy round-trip) |
| N8b | GNSS fix | BLOCKED_HARDWARE (no GNSS provider/hardware) |
| N9 | Bridge restart/reconnect | PASS_DEVICE_RUNTIME (0.6.5-beta, NRestarts=0) |
| N10 | Missing-backend error path | PASS_DEVICE_RUNTIME (Bluetooth NO_ADAPTER, stale_scan) |
| N11 | Lock/unlock + Quick Settings reopen | NOT_TESTED (screen-off; requires owner touch) |
| N12 | Wi-Fi/BT/Location vs USB indicator independence | PASS_DEVICE_RUNTIME (indicators endpoint) |

## Physical USB unplug / reconnect
| ID | Action | Result |
|---|---|---|
| U1–U13 | boot without cable, attach, detach, reattach ×5, wall charger, etc. | **NOT_TESTED** — USB Live Console is the only recovery path; owner-supervised test required (see `02-USB-DETACH-ROOT-CAUSE.md`) |

No test was upgraded from mocked/offline to physical pass.
