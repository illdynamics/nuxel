# A54 Boot Readiness (battery + rotation first-ready)

## Root cause
The bridge's `read_battery_status()` treated the sysfs `status` value `Full` as
a *charging* state (`status in ('Charging','Full')`). On the S10+ the fuel gauge
reports `Full` once the charger holds the battery at 100%, so the status bar
showed a charging glyph and misleading charging flag immediately after boot —
the "battery looks wrong" regression. The value itself was already readable
synchronously from `/sys/class/power_supply/battery`.

## Fix applied
- `bridge.py::read_battery_status()` now distinguishes `Charging` (charging=true)
  from `Full` (charging=false) and adds an honest `status` word
  (`charging|full|discharging|not-charging|unknown`).
- The frontend already polls phone status on `StatusBar` construction (not on a
  delayed timer), so the first numeric percentage is available in the first
  status poll; no `undefined`/NaN is ever rendered (the em dash is only used
  when a sysfs value is genuinely absent/out of range).

## Live evidence (device)
- HTTP bridge `/api/v1/phone/status` battery payload **before fix**:
  `{"level":100,"charging":true,"source":"sysfs:battery"}`.
- **After fix:** `{"level":100,"charging":false,"status":"full",
  "source":"sysfs:battery","capacity_uah":4000000,"design_capacity_uah":4000000}`.

## Rotation first-ready
- `nuxel-orientationd` initializes `mode`/`effective_orientation` to a defined
  value (portrait fallback) and `status` always returns a concrete `mode`; the
  A54 key migration removes the legacy underscore/unknown enum that could make a
  frontend label fall through to a bare `undefined`.

## Gate
- **BATTERY:** PASS_INTEGRATION (real numeric percent immediately via bridge;
  charging/full semantics corrected). First-frame UI timing is a visual check the
  owner can confirm; no fabricated 0/100 fallback exists.
