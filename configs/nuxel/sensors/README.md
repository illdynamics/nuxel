# `configs/nuxel/sensors/` — remaining sensors and capability manifest (area 28)

| File | Install to | Purpose |
|---|---|---|
| `sensors.json` | `/etc/nuxel/sensors/sensors.json` | Per-class evidence sources, expected presence, verdicts, owner gestures |

## Honest boundaries

* Evidence is drawn from **three independent sources** — IIO devices
  (`/sys/bus/iio/devices`), the input subsystem (`/proc/bus/input/devices`) and
  the sensor-hub driver set (`/proc/modules`) — and reported **per class**.
* `expected_on_s10plus` is the **documented hardware**, not an observation. A
  class is `readable` only when a real raw channel is read; otherwise it is
  `present-unreadable`, and with no evidence anywhere it is
  `NOT_SUPPORTED_ON_DEVICE`.
* Motion/orientation/cover gestures must be **physically induced**: the owner half
  is `NEEDS_OWNER_TEST` and this briQ never gates another.
* No flashing surface of any kind.

## Commands

```sh
nuxel-sensors-diag.sh status [--json]        # per-class state + evidence sources
nuxel-sensors-diag.sh read accel [gyro ...]  # read raw channels for named classes
nuxel-sensors-diag.sh watch accel 30         # bounded sample while you move the phone
nuxel-sensors-diag.sh manifest               # capability manifest as JSON
nuxel-sensors-diag.sh selftest
```

Owner procedure: `docs/beta-finalization/manual-proof/14-sensors.md`.
