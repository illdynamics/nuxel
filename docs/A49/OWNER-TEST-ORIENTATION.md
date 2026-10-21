# A49 Owner test — rotation

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for policy + UI).

## Prerequisites
1. Phone booted into Nuxel, USB console reachable, screen on.
2. Confirm the service surface first (do NOT rely on the tile until proven):

   ```sh
   nuxel-orientationd status --json      # mode, effective, sensor.available
   nuxel-orientationd modes
   ```

## 1. Calibrate the accelerometer (Phase 1)
1. `nuxel-sensors-diag.sh watch accelerometer 20` while tilting the phone left,
   right, forward and back; the axis values must change and settle.
2. Record X/Y/Z for the four poses (normal, upside-down, left, right, face-up,
   face-down) and note the sensor identity. If only `ssp_context` hub events are
   exposed (no IIO channels), record that as the exact blocker.
3. Derive the mount matrix + gravity reference from those readings and update
   `orientation.json` (`sensor.mount_matrix`, `sensor.gravity_reference`), then
   set `calibration_status` to `verified` only after a re-run confirms the four
   poses classify correctly (`nuxel-orientationd status`).

## 2. Manual modes
For each fixed mode (`portrait`, `reverse_portrait`, `landscape`,
`reverse_landscape`), `nuxel-orientationd set <mode> --apply` and:
* confirm the compositor applies the transform (or reports exactly why not),
* touch all four corners + the keyboard: **hit boxes must match the visuals**,
* check status bar, dock, OSK, a modal dialog and the camera cutout/safe areas,
* if the display blanks or input becomes unusable, the service must auto-revert
  to the last-good transform within the bounded interval — confirm this.

If the compositor cannot apply the transform, STOP and record it as a Phase 3
blocker; do not ship "rotation" that only rotates pixels.

## 3. Auto modes
1. `nuxel-orientationd set auto --apply`, then turn through all four sides and
   confirm the screen follows with ~300–800 ms settle and no flapping.
2. `auto_portrait`: only upright/upside-down, **never** sideways.
3. `auto_landscape`: only the two sideways positions, **never** portrait.
4. Lay the phone flat: orientation must keep the last good pose, not flap.

## 4. UI
1. Home → QS → long-press Rotate: all seven choices must appear; tap toggles
   portrait/auto; the tile shows Auto/Locked + sensor availability.
2. Settings → Display → Screen rotation: seven radio choices, effective
   orientation and calibration status; no cosmetic toggle success.

## 5. Persistence + no regression
Reboot (with permission) and confirm the saved mode is restored. Confirm
lockscreen unlock, navigation, battery/metrics, Wi-Fi and the USB console still
work, and that the lockscreen stays portrait unless its landscape layout passes
full touch/non-overlap tests.
