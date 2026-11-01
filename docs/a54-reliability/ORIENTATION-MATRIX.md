# A54 Orientation Matrix

## Stable mode keys (A54 canonical)

| UI choice | Stored key | Allowed poses |
|---|---|---|
| Auto (FULL) | `auto` | 0/90/180/270 |
| Auto (PT) | `auto-portrait` | 0/180 |
| Auto (LS) | `auto-landscape` | 90/270 |
| Locked (PT) | `portrait` | 0 |
| Locked (LS) | `landscape` | 90 |
| Locked (RPT) | `reverse-portrait` | 180 |
| Locked (RLS) | `reverse-landscape` | 270 |

## What was wrong
- Backend `policy.py`, `qs.js`, `settings.js` and `settings-model.js` all used
  legacy underscore keys (`auto_portrait`, …), so the frontend and the stable
  A54 contract disagreed and older persisted state could surface as an unknown
  enum (the reported `undefined` startup state).
- The Quick Settings tile collapsed the label to `Auto`/`Locked`, masking the
  five primary + two advanced modes.

## Fix applied
- `policy.py`: canonical hyphen keys + `MODE_ALIASES` migration boundary —
  `validate_mode()`/`mode_from_document()` normalise every legacy underscore key
  to its hyphenated equivalent (single migration point).
- `nuxel-orientationd`: `modes`/`status` now return the seven hyphenated keys;
  `do_set` rejects anything outside the seven.
- `qs.js` long-press menu + `settings.js` radio set + `settings-model.js` option
  list all use hyphen keys; the QS tile label now shows the **real** selected
  mode name, not `Auto`/`Locked`.
- On-device `/etc/nuxel/orientation/orientation.json` `modes`/`mode_order`
  re-keyed in place (preserving device/panel/compositor fields).
- Orientation test suite updated + legacy-migration test added: **40 passed**.

## Live evidence (device)
- `nuxel-orientationd modes --json` → `['auto','auto-portrait','auto-landscape',
  'portrait','landscape','reverse-portrait','reverse-landscape']`.
- `status` → `mode=auto`, `effective_orientation=0`, `sensor.available=false`,
  `compositor.transform_available=false`.

## Hardware gate (honest)
- **Sensors:** no IIO accelerometer with a readable scale is exposed
  (`iio-accel` "device present but no readable scale"); `iio-sensor-proxy` is not
  installed. Auto modes therefore cannot drive physical rotation today.
- **Compositor transform (historical note only):** an earlier archive reported
  `wlr-randr` absent. That is no longer true on the current image: `wlr-randr`
  is installed and HEADLESS-1 accepts the four transforms. The old missing
  binary was one cause of preference-only rotation.

## Gate
- **ROT-MENU:** PASS_INTEGRATION (all seven entries, real persisted state, no
  `undefined`, legacy migration).
- **ROT-FORCED:** PASS_LIVE — all four transforms applied and were read back;
  framebuffer-vs-Phoc captures prove the 0/90/180/270 physical relationships.
- **ROT-AUTO:** BLOCKED_HARDWARE — no auto-capable gravity sensor source is
  exposed on this kernel (detailed per-source reason in `status.sensor.sources`).


## PWNAGE-54000 live result

The active output is `HEADLESS-1` (720x1520). The historical transform map is
restored: `0→normal`, `90→270`, `180→180`, `270→90`. Portrait poses use scale 2
(360x760 logical); landscape poses use scale 1 (1520x720 logical). A successful
transform is committed after live readback, not auto-reverted by a hidden trial.
All four fixed poses verified live. Touch is owned exactly once by
`libnuxel-libinput-path.so`, which applies a libinput calibration matrix selected
from the verified transform and records read-back evidence in
`/run/nuxel-touch-calibration.state`. Phoc 0.54 does not transform touch itself.
`nuxel-wl-fb` performs no presenter rotation. Auto remains blocked by the SSP
sensor hub, and status reports the hub's MCU/raw_data reason instead of a green
fake Auto. Quick Settings short-tap rotates through the four Locked poses; the
seven-mode chooser is long-press. VNC uses `wayvncctl detach`/`attach` then `output-set` to re-read the
live transform without restarting the server.

## PWNAGE-55000 Auto-path repair (2026-11-01)

The auto policy and hysteresis were already correct; the missing link was that
the sensor hub was never started. `nuxel-orientationd` now calls
`sensors.SensorHubControl` when an Auto mode is selected (and at Auto startup),
which:

1. writes `ESW:READY` to `/dev/bbd_control`,
2. ORs accelerometer bit 0 into `/sys/class/sensors/ssp_sensor/enable`, and
3. waits for a real non-zero `accelerometer_sensor/raw_data` sample.

It never injects a reading. The same path is exposed as
`nuxel-orientationd sensor --start --json`.

Live result after deploy and reboot: the four Locked modes still apply and
verify (`transforms normal/270/180/90`, logical `360x760`/`1520x720`). Auto
remains `blocked_sensor_unavailable` with the specific reason
`vendor Android lhd daemon is not installed; the BCM47752 MCU cannot receive
its BBD/LHD patch`. The accelerometer bit stays 0 because the MCU never answers
(`initialize_mcu ... MCU is not working`); therefore no genuine Auto rotation
can be claimed on this image yet. The difference from the earlier defect is
that the daemon now performs the start sequence instead of only reading a zero
node, and reports the exact missing runtime.
