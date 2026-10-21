# NUXEL A49 — FINAL REPORT (orientation, external display, casting, keyboard haptics)

**Branch:** `nuxel/bootscreens-orientation-big-screen`
**Start commit:** `9229908` (clean working tree) → **End commit:** `5d56cfa` (4 commits)

## Executive summary

Repository-side deliverables are implemented and offline-tested. **No live USB
console was reachable during this session**, so every hardware claim below is
explicitly `UNVERIFIED` / `NEEDS_OWNER_TEST`. Nothing was flashed, no partition
was written, no boot/recovery/kernel was replaced, no reboot was performed, and
no second input daemon / rotation loop / display stack / keyboard overlay /
vibrator owner was introduced.

The penguin will rotate on command and by gravity **in policy**, and the
console/UI can ask for it — but the final compositor transform, touch mapping,
sensor mount matrix, HDMI pixels and a felt buzz are all owner-proof steps on the
physical S10+.

---

## Definition of Done

| Feature | Source + tests | Deployed | Hardware/owner proof | Blocker |
|---|---|---|---|---|
| Accelerometer / gyro detection | `nuxel_orientation/sensors.py` (IIO + iio-sensor-proxy adapters), `nuxel-sensors-diag.sh` | not yet | **UNVERIFIED** — needs physical tilt | hardware session absent |
| 0/90/180/270 manual modes | `policy.py` fixed modes + `apply.py` wlr-randr transform | not yet | **UNVERIFIED** — transform+calibration | Phoc transform/touch unproven on-device |
| Auto all orientations | `policy.py` `auto` + hysteresis | not yet | **UNVERIFIED** | sensor mount matrix uncalibrated |
| Auto portrait | `policy.py` `auto_portrait` (0/180 only) | not yet | **UNVERIFIED** | same |
| Auto landscape | `policy.py` `auto_landscape` (90/270 only) | not yet | **UNVERIFIED** | same |
| QS / Settings / persistence | `qs.js`, `settings.js`, `nuxel-orientationd` state file | not yet | OFFLINE_TESTED (39 tests) | device reboot-persistence unproven |
| Touch mapping / keyboard after rotation | `apply.py` marks touch unverified; no change to input daemons | not yet | **UNVERIFIED** | Phase 3 hardware-gated |
| USB-C DP alt mode + HDMI output | `nuxel-typec-diag.sh` (read-only) | not yet | **UNVERIFIED** | requires owner-supervised adapter test + USB recovery assurance |
| Casting actual screen/video | `nuxel-cast-diag.sh` (read-only capability probe) | not yet | **UNVERIFIED** | no verified Phoc screencast pipeline yet |
| Keyboard haptics / real intensity | `keyboard.json`+schema, `touch-keyboard.js` already routes via gated haptics API | not yet | **UNVERIFIED** — felt only | actuator amplitude probe pending |
| Rotation/haptics survive reboot | daemon state file + config (atomic writes) | not yet | **UNVERIFIED** | needs a reboot test after owner permission |
| Lockscreen, nav, USB console preserved | no files on those paths were touched | n/a | no regression surface introduced | not re-verified on device |

---

## What was actually implemented (offline-tested)

1. **Seven-mode orientation policy service** (`services/nuxel-orientation/`):
   pure policy state machine, sensor adapter (IIO + iio-sensor-proxy + manual),
   compositor apply/revert, CLI daemon, systemd unit. 39 pytest tests pass
   (seven-mode exactness, hysteresis, flat/weak rejection, cooldown,
   restricted-auto rules, persistence, honest calibration flags).
2. **One source of truth** wiring: `nuxelctl orientation …`, bridge D-Bus
   (`OrientationGet/Modes/Set`) + HTTP RPC (`orientation.get|modes|set`).
3. **Quick Settings** `qs-rotate` tile is now real (tap portrait/auto,
   long-press seven-mode menu) and reflects effective orientation + sensor
   availability.
4. **Settings → Display → Screen rotation** seven-choice radio group, plus the
   `settings-model.js` orientation + keyboard-haptics settings.
5. **Keyboard haptics** settings (`keyboard.haptics_intensity` low/medium/high,
   `keyboard.haptics_pulse_ms`) in `keyboard.json`+schema, ON by default,
   intensity honestly duration-only when amplitude is unavailable.
6. **Read-only probes** for USB-C/DP (`nuxel-typec-diag.sh`) and wireless
   casting (`nuxel-cast-diag.sh`) with honest verdicts; 7 more tests pass.

## Honest blockers (why not "done" on hardware)

* **No live device session.** `.scratch/` shows device work concluded earlier
  (boot-splash/param work) with no active USB console now. Phase 1 (tilt the
  phone), Phase 3 (compositor transform + touch), Phase 5 (HDMI), Phase 6
  (cast) and Phase 7 (felt buzz) all require the physical handset.
* **Phoc transform + touch calibration.** The S10+ uses Phoc/wlroots; the exact
  `wlr-randr --transform` mapping and the matching touch matrix are
  `calibration_status=unverified`. Rotated pixels without rotated touch are
  explicitly rejected, so this is the Phase 3 gate.
* **Sensor mount matrix.** Uncalibrated until an owner tilts the device and
  records X/Y/Z.
* **USB-C DP Alt Mode.** A missing `/sys/class/typec` is evidence, not proof;
  Samsung's vendor tree may replace the generic class. The read-only probe
  reports what the kernel actually exposes; a physical adapter test is a
  separate, owner-supervised step that must preserve the USB recovery console.

## Rollback

Repository: `git reset --hard 9229908` reverts all four commits (do this only on
the host, and never on the device boot chain). Device rollback for any staged
userspace deploy is `tools/s10plus/a33/nuxel-rollback-home.sh` / the A49 staged
deploy manifest (see BASELINE.md). No boot-critical file was changed, so rollback
is a userspace-only revert.

## Owner test documents

* `docs/A49/OWNER-TEST-ORIENTATION.md`
* `docs/A49/OWNER-TEST-EXTERNAL-DISPLAY.md`
* `docs/A49/OWNER-TEST-CAST.md`
