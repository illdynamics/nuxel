# A55 Boot Readiness (battery + rotation first-ready)

## Live battery
- `/sys/class/power_supply/battery/capacity` = `100`, `status` = `Full`.
- A54 bridge fix (distinguish `Full` vs `Charging`) remains deployed; the status
  bar shows a numeric percent on the first status poll, never `undefined`.
- Gate: **BATTERY PASS_INTEGRATION** (real numeric value synchronously readable;
  first-frame visual timing is owner-observable, NOT_TESTED by hand).

## Rotation first-ready
- `nuxel-orientationd` initializes to a defined mode (portrait fallback) and the
  A54 legacy-key migration removed the `undefined` enum path.
- Manual orientation selection is independent of the (absent) IIO sensor.
- Gate: **ROT no-undefined PASS_INTEGRATION** (policy/state); physical rotation
  remains blocked (see ORIENTATION-MATRIX.md).

## Startup service chain
All 10 critical units active, 0 failed. Load average ~12 is kernel D-state thread
noise (tz_worker/shd/dhd/scsi workers), not a runaway userspace process
(top userspace consumers are phoc 1.4% and WebKit 1.2%).
