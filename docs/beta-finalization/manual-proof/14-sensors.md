# Area 28 — Remaining sensors (accel, gyro, mag, proximity, light, barometer)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for enumeration + diagnostic).
Owner action required? **Yes** — motion, rotation, covering the screen and changing
altitude can only be physically induced.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820). The A32 baseline observed the hub input devices (`grip_sensor`,
`ssp_context`, `hall`, `certify_hall`) but that is **input-subsystem evidence**,
not a raw value. `nuxel-sensors-diag.sh` enumerates three independent sources —
**IIO** (`/sys/bus/iio/devices`), the **input** subsystem
(`/proc/bus/input/devices`) and the **sensor-hub driver set** — and reports, per
class: `readable` (a real raw channel was read), `present-unreadable`
(enumerated but no raw channel) or `absent` (`NOT_SUPPORTED_ON_DEVICE`).
The `expected_on_s10plus` flags in `sensors.json` are the device's **documented
hardware, not observations**.

---

## 1. Feature

`configs/nuxel/sensors/sensors.json` + `tools/s10plus/a33/nuxel-sensors-diag.sh`:

* a **capability manifest** for accelerometer, gyroscope, magnetometer,
  proximity, ambient light, barometer (plus optional heart-rate, grip and hall),
  each with expected presence, evidence names and an owner gesture;
* per-class **enumeration** across IIO / input / hub drivers, with the evidence
  path printed;
* **raw reads** (`read`) and a **bounded watch** (`watch`, ≤ 120 s) that prints
  first/last values and whether a channel `CHANGED` — the only honest basis for a
  motion claim.

## 2. Why this matters

Sensors drive screen rotation, auto-brightness, proximity-during-call and compass
heading; they are also the subsystem most easily "verified" from a driver name.
The mission's evidence rule forbids that: a class is only `readable` when a real
raw channel returns a value, enumeration without a channel is called
`present-unreadable`, and nothing is reported as working from a flag.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode.
2. Console/SSH or the on-device terminal, so `watch` can run while you move the
   phone.
3. A dark corner + a lit area (for ambient light), and optionally a lift/stairs
   (for the barometer) and a magnet or flip cover (for hall, if present).
4. Snapshot first:

   ```sh
   nuxel-sensors-diag.sh status            # per-class state + evidence source
   nuxel-sensors-diag.sh status --json
   nuxel-sensors-diag.sh manifest          # what the device is expected to expose
   ```

   A class reported `NOT_SUPPORTED_ON_DEVICE` is a real verdict (no IIO/input/hub
   evidence). Record it — do not retry, and do not treat the manifest's
   `expected_on_s10plus` as proof.

## 4. Exact action

For each class you want to prove, first read it, then watch it while you perform
the documented gesture. The gesture text lives in `sensors.json`
(`owner_gesture`) and is printed by `manifest`.

1. **Accelerometer** — `nuxel-sensors-diag.sh read accelerometer`, then
   `nuxel-sensors-diag.sh watch accelerometer 20` and **tilt the phone left,
   right, forward and back**. The axis values must change and settle when still.
2. **Gyroscope** — `watch gyroscope 20` while **rotating** the phone about each
   axis; rates must move and return to ≈ 0 at rest.
3. **Magnetometer** — `read magnetometer`, then `watch magnetometer 30` while
   **turning through a full circle**; the field values must change and the heading
   respond.
4. **Proximity** — `watch proximity 20` while **covering the top of the screen
   with your hand** and removing it; near/far must flip.
5. **Ambient light** — `watch ambient_light 20` while **moving from a dark corner
   to a lit area**; the lux value must rise and fall.
6. **Barometer** — `watch barometer 30` while **changing altitude slightly**
   (stairs or a lift); the pressure must move. A perfectly static value is
   **unproven**, not PASS.
7. **Optional classes** (heart rate / grip / hall) — only if `status` reports them
   as enumerated: follow their `owner_gesture` text; otherwise record
   `NOT_SUPPORTED_ON_DEVICE`.
8. Save the evidence: `nuxel-sensors-diag.sh report` plus the `watch` output for
   each class you tested.

## 5. Expected result

* `status` prints every class with its state and evidence source; at least one
  class is `readable` when the kernel exposes IIO channels.
* `watch <class> <secs>` prints `samples=N`, first/last values and `CHANGED` for at
  least the axis/channel that the gesture moved, and `unchanged` for a channel the
  gesture did not affect.
* `read` prints only channels that really exist; a class with no channel prints
  "no raw channel".
* Classes the device does not expose are `NOT_SUPPORTED_ON_DEVICE` — recorded, not
  faked.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| verdict `BLOCKED_KERNEL` | Nothing enumerated from IIO, input or hub drivers: offline driver work; no raw value exists to claim. |
| verdict `PRESENT_UNREADABLE` | The hub is enumerated (e.g. `ssp_context`) but exposes no raw channel to Linux: the userspace path is missing (a driver/IIO gap, not a gesture problem). |
| A class is `NOT_SUPPORTED_ON_DEVICE` | No IIO/input/hub evidence anywhere. Record it honestly; it must not gate other areas. |
| `watch` shows `unchanged` for every channel | Either the gesture did not reach the sensor or the channel is not live: re-run once with a clearer gesture, and **after three same-mode attempts change strategy** (different class/source), never loop. |
| Values change but wildly/at random | Noise or a wrong channel mapping: capture the raw values and the channel names, report FAIL. |
| Barometer perfectly static | Unproven: pressure changes are small; if a lift/stairwell gives no movement, record `unproven`, not PASS. |
| `status` disagrees with the launcher's rotation/brightness behaviour | Report the enumeration evidence and the observed behaviour separately; the launcher side is a different component. |

## 7. Diagnostic command / log path

* `nuxel-sensors-diag.sh status | read <class…> | watch <class> <secs> | manifest | report`
  (`tools/s10plus/a33/nuxel-sensors-diag.sh`)
* Evidence log: `/var/log/nuxel/sensors-diag.log`
* Kernel side: `ls /sys/bus/iio/devices/`; `cat /sys/bus/iio/devices/*/name`;
  `sed -n 's/^N: Name="\(.*\)"$/\1/p' /proc/bus/input/devices`;
  `dmesg | grep -i -E 'sensor|accel|gyro|magn|prox|illuminance|baro|ssp'`
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-sensors-diag.py`
  and `nuxel-sensors-diag.sh selftest` (3 fixtures: IIO-readable / input-hub-only
  / nothing).

## 8. PASS / FAIL

* **PASS** — for each class you claim: `status` enumerates it, `read` returns real
  raw channels, and `watch` shows the documented gesture changing at least one
  channel with the expected sign/behaviour, with the channel names and first/last
  values recorded.
* **FAIL** — any of: `BLOCKED_KERNEL`, `PRESENT_UNREADABLE` for a class you claim
  works, a `watch` that never changes, or a value you did not read. Record the
  class, the evidence source, the channel names and the first/last values — that
  is what a repair cycle needs.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-sensors-diag.sh selftest` → 3/3 fixtures PASS
  (`fixtures/sensors-iio`, `sensors-input`, `sensors-none`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-sensors-diag.py` → all
  checks PASS (three-source enumeration, per-class states, raw-only reads, watch
  bounding, faked-root safety, manifest contract, fragment completeness).
* Physically induced motion: **not claimed** — every `status --json` emits
  `"observed_motion_verified": false`, and the capability manifest keeps every
  class at `NEEDS_OWNER_TEST` / `present-unreadable` / `absent` exactly as found.
