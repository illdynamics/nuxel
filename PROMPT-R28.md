# NUXEL R28 — Other sensors
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r28-other-sensors`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Enumerate and use the S10+'s non-camera sensors truthfully: accelerometer, gyroscope, magnetometer, proximity, ambient light, hall, grip, barometer, and any other present IIO/input classes. This branch must provide units, calibration, sampling/hysteresis and rotation logic, and must report absent or present-but-unreadable sensors instead of inventing values.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/sensors/sensors.json`, `tools/s10plus/a33/nuxel-sensors-diag.sh`, `tools/s10plus/a33/tests/hw-subsystems/test-sensors-diag.py`, the `sensors-*` fixtures, `configs/s10plus/display/nuxel-s10plus-display.sh`, `pwa/nuxel-home/js/safe-zones.js`, and the sensor capability entry in `configs/nuxel/capabilities/hardware-subsystems.json`. Expected hardware is documented; readable values, calibration, and motion-triggered behavior are not proven.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns IIO/input sensor discovery, raw-to-unit conversion, calibration status, orientation/rotation logic, sampling policy, privacy, and diagnostics. Does not own camera sensors or GNSS. No synthetic sensor value and no orientation change that bypasses touch/display transforms.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate IIO devices, input sensor names, hub drivers, and sysfs classes; produce a per-class state: readable, present-unreadable, absent, or permission-denied.
2. Define raw-to-unit scales, offsets, and calibration sources for each class; reject implausible values.
3. Implement bounded sampling with hysteresis/debounce for orientation, proximity, and ambient light to avoid UI thrash.
4. Verify rotation/orientation transforms agree with the display and touch coordinate system, including landscape if supported.
5. Test all four device orientations, cover/uncover proximity, light/dark transitions, and stationary/moving gyro/accel data.
6. Handle sensor-hub present but no IIO channel, permission denied, and a sensor that returns constant/stale values.
7. Expose truthful per-class status in Settings/diagnostics and document absent classes.

## Failure modes and diagnostics
- Watch for sensor hub input events without IIO channels, raw values with undocumented scales, a compass requiring hard-iron calibration, and rotation logic applied twice. Verify the actual input/IIO names rather than the expected marketing names.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report lists each class as readable, present-unreadable, absent, or denied, with evidence.
2. Raw values convert to documented units and pass plausibility/calibration checks.
3. Orientation changes only at hysteresis thresholds and matches the display/touch transform.
4. Proximity/light transitions update the intended UI without flicker.
5. Stationary gyro/accel settles near zero within the stated tolerance.
6. No sensor value is fabricated when a class is absent or unreadable.
7. Physical motion/cover/light tests are owner-labeled and separate from fixtures.

## Hardware, privilege and rollback safety
Do not change kernel sensor drivers or calibration partitions. Motion tests need owner action. Preserve privacy and avoid logging sensitive behavioral data.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r28-other-sensors`, with tests and docs for this component only.
- `docs/component-reports/r28.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a class cannot be read safely or requires a kernel change. Report the precise absent/unreadable state and do not block unrelated sensor classes.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
