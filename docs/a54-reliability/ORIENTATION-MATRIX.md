# A54 Orientation Matrix

## Stable mode keys (A54 canonical)

| UI choice | Stored key | Allowed poses |
|---|---|---|
| Auto | `auto` | 0/90/180/270 |
| Auto Portrait | `auto-portrait` | 0/180 |
| Auto Landscape | `auto-landscape` | 90/270 |
| Forced Portrait | `portrait` | 0 |
| Forced Landscape | `landscape` | 90 |
| Reverse Portrait | `reverse-portrait` | 180 |
| Reverse Landscape | `reverse-landscape` | 270 |

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
- **Compositor transform:** `wlr-randr` is absent, so `apply.py` has no transform
  backend; the fixed portrait screencopy→`/dev/fb0` path cannot be rotated by a
  compositor transform. Rotating CSS while leaving touch coordinates unrotated is
  explicitly forbidden by the mission, so a CSS-only "rotation" is not shipped.

## Gate
- **ROT-MENU:** PASS_INTEGRATION (all seven entries, real persisted state, no
  `undefined`, legacy migration).
- **ROT-FORCED:** PARTIAL — mode selection/persistence works and would drive the
  transform, but physical output+touch rotation is blocked by the missing
  compositor transform backend (`transform_available=false`).
- **ROT-AUTO:** BLOCKED_HARDWARE — no auto-capable gravity sensor source is
  exposed on this kernel (detailed per-source reason in `status.sensor.sources`).
