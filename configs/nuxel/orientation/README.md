# `configs/nuxel/orientation/` — orientation policy (A49)

| File | Install to | Purpose |
|---|---|---|
| `orientation.json` | `/etc/nuxel/orientation/orientation.json` | Seven-mode policy, hysteresis, sensor source, mount matrix, compositor transform map |
| `orientation.schema.json` | `/etc/nuxel/orientation/orientation.schema.json` | JSON Schema of the policy/state document |

## Seven modes (exactly; the owner phrase "six" is a count mismatch)

| mode | allowed orientations | rule |
|---|---|---|
| `portrait` | 0° | forced normal portrait |
| `reverse_portrait` | 180° | forced upside-down portrait |
| `landscape` | 90° | forced first landscape direction |
| `reverse_landscape` | 270° | forced opposite landscape direction |
| `auto` | 0/90/180/270 | sensor-based, all four |
| `auto_portrait` | 0/180 | sensor-based, never landscape |
| `auto_landscape` | 90/270 | sensor-based, never portrait |

`default_mode` is `portrait` (safe). Manual modes work with no sensor; auto
modes report `sensor_unavailable` when no verified source exists.

## Honest boundaries

* The mount matrix and gravity reference vectors are **calibration
  unverified**: the S10+ handset must be tilted by an owner to derive them.
  `nuxel-orientationd status` reports `calibration.mount_matrix` and
  `calibration.gravity_reference` as `unverified` until that happens.
* The compositor transform map and touch calibration are **unverified** until
  Phase 3 is exercised on the real device. `nuxel-orientationd set … --apply`
  reports `compositor.applied` honestly and never claims success on a missing
  `wlr-randr` or a failed transform.
* No flashing, no partition writes, no reboot, no second compositor/input
  daemon. The service writes only `/var/lib/nuxel/orientation/state.json`.

## Commands

```sh
nuxel-orientationd status [--json]      # mode, effective, sensor, compositor, calibration
nuxel-orientationd get                  # selected mode
nuxel-orientationd modes                # the seven modes + allowed sets
nuxel-orientationd set landscape --apply
nuxel-orientationd watch 20             # bounded auto-rotation (hardware only)
nuxel-orientationd selftest
```

Owner procedure: `docs/A49/OWNER-TEST-ORIENTATION.md`.
