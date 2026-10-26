# A75 — USB State Model and Indicators

## Producers
- `services/nuxel-bridge/src/system_indicators.py` computes all three states
  in-process from sysfs/proc (single owner, no mocks). Overridable roots exist
  for offline tests (`NUXEL_SYS_POWER_SUPPLY`, `NUXEL_SYS_UDC`,
  `NUXEL_SYS_TYPEC`, `NUXEL_PROC`, `NUXEL_RUN`, `NUXEL_CONSOLE_TTY`, …).
- The launcher consumes either:
  - `NuxelHost.statusRead('system-indicators')` (native PWA host), or
  - HTTP `GET /api/v1/system/indicators` (HTTP bridge).

## Event flow
sysfs/proc read → `get_indicators()` → JSON → native host message / HTTP → JS
`LockscreenIndicators.normalise()` → DOM classes `active`/`charging` on the
three `.lockscreen-indicator` nodes. A failed read fails **closed** for PC and
Live Console (never leaves a stale ON), while charging keeps its last good
power reading.

## State classes
- `charging-ind` — `active` when external power present; `charging` only when
  battery `status == "Charging"`.
- `usb-ind` — `active` only for a bound gadget + exact UDC `configured`, vetoed
  by Type-C `data_role` after physical detach.
- `live-ind` — `active` only when daemon + transport + open tty fd/valid lease
  are all true.

## Measured detach-to-off latency
`NOT_TESTED` (physical unplug not performed). The offline path is event/poll
driven (3 s safety poll on the lockscreen, generation-guarded, single in-flight
request); on a real host disconnect the backend state switches OFF immediately
after reliable detach confirmation, before any short 120–220 ms exit fade.
