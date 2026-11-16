# FULL PWNAGE — Samsung Galaxy S10+ SSP Sensor Runtime, Accelerometer, Gyroscope & Auto-Rotation

**Project:** Nuxel  
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**SoC:** Exynos 9820 (`universal9820`)  
**OS:** Nuxel / Fedora Linux ARM64  
**Kernel baseline:** Linux 4.14.253  
**Acquisition directory:** `./sensors/`  
**Initial connection:** TWRP over USB  
**Execution mode:** Autonomous investigation, implementation, testing, repair and reflashing.

---

# 0. MISSION

Your mission is to make the Samsung Galaxy S10+ sensor hardware work properly under Nuxel.

This is not a research-only task. You must implement the actual kernel/runtime/userspace integration, boot the phone into Nuxel, and physically demonstrate working accelerometer, gyroscope and automatic display rotation.

The operator will:

1. Extract the supplied S10+ SSP Runtime Acquisition Pack into `./sensors/`.
2. Boot the phone into TWRP.
3. Connect the phone to the workstation over USB.
4. Start you.

The operator authorises you to investigate, build, flash the verified boot image and reboot the device.

**CRITICAL BOOT FAILURE RULE:**

If you flash a boot image, reboot the phone, and the phone returns to TWRP, that means the Nuxel boot attempt failed.

The operator did not manually return the device to TWRP.

Treat this as a failed boot. Investigate the cause, collect evidence, fix it, rebuild, and reflash.

Continue until Nuxel boots successfully and the required sensor functionality is demonstrated, subject to the recovery safeguards in this document.

Do not declare success because compilation succeeded, a device node exists, or a sensor reports that it initialized.

The physical hardware must work.

## 0.1 Definition of DONE

The task is complete only when all of these are true:

- [ ] Exact S10+ hardware and sensor data path identified.
- [ ] Supplied `./sensors/` material fully inventoried and verified.
- [ ] Required firmware/runtime components identified and correctly integrated.
- [ ] Kernel support implemented or correctly adapted.
- [ ] Sensor userspace service implemented and running.
- [ ] Accelerometer returns live, changing, physically plausible XYZ data.
- [ ] Gyroscope returns live, changing, physically plausible XYZ data, if hardware path exposes it.
- [ ] Sensor axes and mounting orientation calibrated.
- [ ] Nuxel receives orientation updates.
- [ ] Automatic rotation works in the actual Nuxel graphical session.
- [ ] Physical portrait → landscape → portrait test succeeds.
- [ ] At least three physical rotation cycles pass.
- [ ] No boot instability or unacceptable sensor-service instability.
- [ ] Final reports, logs, hardware map, runtime inventory and checksums saved.

If a feature cannot be made to work, document the exact blocker and evidence. Never fabricate a PASS.

---

# 1. INITIAL SAFETY AND DEVICE IDENTIFICATION

You begin with the phone connected to TWRP over USB.

## 1.1 Establish the connection

Identify the device using available tools:

- `adb devices`
- `fastboot devices`, if applicable
- TWRP shell access
- USB device enumeration
- Relevant recovery logs

Determine which transport is actually available.

Do not assume that ADB, fastboot and TWRP expose the same capabilities.

Record:

- USB device identity.
- Device model.
- Board/platform identity.
- Current recovery state.
- Current boot partition layout.
- Current boot image location.
- Available storage and backup destinations.
- Whether the device is currently responsive.

Verify that this is the intended Galaxy S10+.

If the connected device cannot be positively identified as the intended target, STOP.

## 1.2 Preserve the existing boot image

Before changing anything:

1. Read the current boot partition.
2. Save an untouched backup.
3. Calculate SHA256.
4. Record partition size and image size.
5. Preserve the backup outside the phone.
6. Verify that the backup can be read back and its checksum matches.

Record the original image checksum in the reflash log.

Never overwrite the only known-good recovery image.

## 1.3 Absolute partition safety

You are authorised to modify the verified boot image only.

Do not:

- Flash EFS.
- Flash modem or baseband.
- Flash recovery.
- Flash bootloader.
- Flash PIT.
- Modify userdata.
- Wipe userdata.
- Format partitions.
- Factory reset the phone.
- Change KG, FRP or OEM lock state.
- Modify unrelated partitions.
- Replace vendor or system partitions.
- Perform an uncontrolled full-device flash.

If the correct boot partition cannot be positively identified, stop before flashing.

Never guess a partition name.

## 1.4 Recovery must remain possible

Before every flash:

- Verify the original boot backup exists.
- Verify the new image is the intended target.
- Verify its checksum.
- Verify the device identity again.
- Verify the flash command targets only the approved boot partition.
- Record the action.

Do not repeatedly flash an identical failing image.

Every new attempt must contain an evidence-based correction.

---

# 2. REPOSITORY AND ACQUISITION-PACK RECONNAISSANCE

The supplied acquisition pack will be extracted into:

`./sensors/`

Start by inspecting the complete Nuxel repository and the complete contents of this directory.

Do not assume the acquisition pack contains all required proprietary files. It may contain collection scripts, metadata, instructions or partial acquisition results.

## 2.1 Inspect the repository

Inspect:

- Kernel source and configuration.
- Device tree sources and compiled DTBs.
- Existing S10+ board support.
- Existing sensor drivers.
- Existing IIO support.
- Existing SSP/BBD support.
- Existing firmware loading code.
- Existing systemd services.
- Existing Nuxel hardware abstraction.
- Existing orientation handling.
- Display rotation support.
- Input/event infrastructure.
- Existing diagnostics and logging.
- Build scripts.
- `REFLASH-PLAN.md`.
- Any other active kernel or hardware integration batches.

Do not overwrite unrelated work.

## 2.2 Inventory `./sensors/`

Recursively inventory every file.

For each relevant file record:

- Relative path.
- File type.
- Size.
- SHA256.
- ELF architecture, if applicable.
- ELF interpreter.
- Dynamic dependencies.
- Version and build metadata.
- Source/provenance, where available.
- Whether it is executable firmware, configuration, a library, a kernel module or a collection artifact.

Inspect ELF files with suitable tools, such as:

- `file`
- `readelf`
- `objdump`
- `strings`
- `lddtree`, if available

Do not execute unknown binaries merely to identify them.

Do not assume that an ARM64 Android binary is directly executable on Fedora Linux.

## 2.3 Specific leads to investigate

The following are investigation leads, not facts to blindly trust:

- Sensor hub may be Broadcom BCM47752KUB1G.
- Vendor identity may reference `ssp,BCM4773`.
- Accelerometer/gyroscope may involve STM LSM6DSO.
- Vendor configuration may reference:
  - `/dev/bbd_patch`
  - `/dev/ttyBCM`
  - `/dev/bbd_control`
  - `/dev/bbd_sensor`
- `LhePatch` may interact with `/dev/bbd_patch`.
- The vendor partition may contain `lhd`.
- The vendor partition may contain `sensors.sensorhub.so`.

Verify all of these against the actual device and supplied acquisition material.

Do not hardcode assumptions into the implementation.

---

# 3. IDENTIFY THE ACTUAL SENSOR ARCHITECTURE

You must establish the real hardware data path.

The key question is:

**Does Nuxel communicate directly with the inertial sensor, or does the Broadcom sensor hub own and expose the sensor data?**

Do not create competing drivers for hardware already controlled by another component.

## 3.1 Identify the inertial sensor

Determine:

- Exact accelerometer model.
- Exact gyroscope model.
- Whether they are integrated in one physical package.
- Bus type: I2C, SPI or sensor hub transport.
- Bus controller.
- Bus address or chip-select.
- Interrupt GPIO.
- IRQ configuration.
- Power regulators.
- Reset GPIO, if present.
- Pinctrl configuration.
- Clock requirements.
- Mounting orientation.
- Axis remapping.
- Calibration data.

Use actual device evidence:

- Device tree.
- Kernel source.
- Existing vendor configuration.
- Sysfs.
- IIO.
- Device enumeration.
- Kernel logs.
- Hardware register information, where safely accessible.

## 3.2 Identify the Broadcom sensor hub

Determine whether the BCM47752 sensor hub is active and required.

Investigate:

- Firmware and patch requirements.
- Boot-time initialization.
- Transport interfaces.
- UART or other bus.
- GPIO/IRQ requirements.
- Power sequencing.
- Reset sequencing.
- Firmware loading.
- Sensor discovery.
- Calibration.
- Runtime communication.
- Suspend/resume behaviour.

If the Broadcom hub is responsible for the accelerometer and gyroscope, implement the correct hub interface.

If the LSM6DSO can be accessed directly and safely without the hub, evaluate that as a separate architecture.

Do not assume both access methods can operate simultaneously.

## 3.3 Hardware map deliverable

Create:

`PWNAGE-SSP-HARDWARE-MAP.md`

Include:

- Physical sensor identities.
- Sensor-hub identity.
- Bus topology.
- Device tree nodes.
- GPIOs and IRQs.
- Power dependencies.
- Firmware dependencies.
- Kernel drivers.
- Userspace components.
- Data flow from hardware to Nuxel display rotation.
- Evidence supporting each conclusion.
- Unknowns explicitly marked UNKNOWN.

---

# 4. FIRMWARE AND VENDOR RUNTIME

This is likely to be one of the hardest parts.

The goal is to obtain a working sensor runtime under Fedora/Nuxel without blindly importing the Android operating system.

## 4.1 Inspect acquired vendor components

If present, inspect:

- `lhd`
- `sensors.sensorhub.so`
- Firmware patches.
- Calibration data.
- Sensor configuration.
- Init scripts.
- Related libraries.
- Related configuration files.
- Any BBD/SSP tools.

Determine the exact dependencies and runtime requirements.

## 4.2 Android/Bionic compatibility

Do not copy Android binaries into Nuxel and assume they will work.

Check:

- ELF architecture.
- Dynamic linker.
- libc implementation.
- Android-specific dependencies.
- Binder dependencies.
- Android property dependencies.
- HAL dependencies.
- Required device nodes.
- Required permissions.
- Required system services.
- Required firmware paths.

Evaluate the smallest viable compatibility approach.

Preferred order:

1. Native Linux driver and firmware path.
2. Small, isolated compatibility layer if strictly necessary.
3. Narrow userspace runtime adaptation.
4. Full Android userspace compatibility only if no reasonable alternative exists and evidence demonstrates it is required.

Do not introduce an entire Android framework just to read two inertial sensors.

## 4.3 Firmware compatibility

Do not substitute firmware from a different Broadcom sensor hub without proving compatibility.

In particular:

- BCM47765 firmware is not automatically valid for BCM47752.
- Firmware filenames are not proof of compatibility.
- Similar chip families are not proof of compatibility.
- A file containing a few bytes is not valid sensor firmware merely because it has the right name.

Validate firmware using:

- Device identity.
- Firmware metadata.
- Vendor configuration.
- Expected image structure.
- Expected version.
- Loader behaviour.
- Hardware response.

If the correct firmware cannot be obtained, report the exact missing component and investigate whether a native alternative exists.

---

# 5. KERNEL IMPLEMENTATION

Implement the smallest robust kernel solution that supports the identified hardware.

Kernel baseline:

`Linux 4.14.253`

## 5.1 Inspect existing kernel support first

Before writing drivers:

- Search existing source for the sensor model.
- Search for Broadcom SSP/BBD support.
- Search for existing Samsung sensor-hub drivers.
- Search for IIO support.
- Inspect device tree definitions.
- Inspect existing board configuration.
- Inspect relevant kernel configuration options.

Do not duplicate an existing implementation.

## 5.2 Potential kernel components

Depending on verified hardware topology, investigate:

- Linux IIO.
- I2C/SPI support.
- LSM6DSO support.
- Sensor-hub transport.
- Broadcom BBD/SSP support.
- Firmware loader.
- GPIO and IRQ.
- Regulators.
- Pinctrl.
- Runtime power management.
- Wakeup support.
- Suspend/resume.

Do not add all of these blindly. Only implement what the verified architecture requires.

## 5.3 Backport discipline

If upstream driver code is needed:

- Audit API compatibility with 4.14.253.
- Backport the minimum required functionality.
- Do not blindly copy a modern driver into an old kernel.
- Check locking and lifetime assumptions.
- Check IRQ handling.
- Check power-management callbacks.
- Check firmware-loading behaviour.
- Check IIO ABI compatibility.
- Check error handling and cleanup paths.

## 5.4 Device tree

Verify all hardware properties against real device evidence.

Do not guess:

- I2C addresses.
- GPIO numbers.
- Interrupt polarity.
- Trigger types.
- Regulator names.
- Pinctrl states.
- Clock names.
- Mounting matrices.
- Sensor-hub transport configuration.

A plausible-looking device tree that does not match the actual board is not an implementation.

## 5.5 Kernel test gates

Before flashing:

- Build the kernel.
- Build relevant modules.
- Check DTB compilation.
- Check image generation.
- Check image format.
- Check boot image header and metadata.
- Check kernel command line.
- Check DTB placement.
- Check ramdisk integration.
- Check required modules and firmware installation.
- Run available static and automated checks.

Save build logs.

---

# 6. NUXEL USERSPACE SENSOR SERVICE

A kernel driver alone is not enough.

Implement a reliable Nuxel sensor service that exposes sensor data to the desktop environment.

## 6.1 Required data

Where supported, expose:

### Accelerometer

- X
- Y
- Z
- Timestamp
- Sampling frequency
- Scale/unit
- Accuracy or calibration state
- Device health

### Gyroscope

- X
- Y
- Z
- Timestamp
- Sampling frequency
- Scale/unit
- Accuracy or calibration state
- Device health

Use correct physical units and document them.

Do not silently label raw counts as m/s² or rad/s.

## 6.2 Interface

Prefer the existing Nuxel hardware abstraction and service architecture.

Investigate existing D-Bus and sensor APIs before inventing a new interface.

The interface should expose:

- Sensor availability.
- Live readings.
- Sampling status.
- Orientation state.
- Calibration status.
- Error state.
- Last successful sample time.

## 6.3 systemd integration

Implement a proper systemd service.

Requirements:

- Starts at the correct stage of boot.
- Uses least privilege.
- Has appropriate device permissions.
- Restarts on recoverable failure.
- Does not enter a rapid crash loop.
- Logs meaningful diagnostic information.
- Handles device disappearance.
- Handles suspend/resume.
- Handles service shutdown cleanly.

Do not run the sensor daemon as root unless required and justified.

## 6.4 Diagnostics

Provide a live diagnostic command or application showing:

- Accelerometer XYZ.
- Gyroscope XYZ.
- Sample timestamps.
- Sampling rate.
- Sensor availability.
- Calibration state.
- Current raw orientation.
- Filtered orientation.
- Stability/confidence.
- Current Nuxel display orientation.
- Sensor errors.

The diagnostic must show actual live data, not fabricated or replayed values.

---

# 7. AUTOMATIC ROTATION

Implement reliable automatic rotation in Nuxel.

## 7.1 Orientation calculation

Use accelerometer gravity measurements for absolute orientation.

Gyroscope measurements may be used for smoothing and transition responsiveness.

Do not use the gyroscope alone to determine absolute orientation. Gyroscope integration drifts over time.

Determine the physical mounting orientation and axis mapping.

Correctly handle:

- X/Y/Z axis permutation.
- Axis sign.
- Sensor mounting rotation.
- Portrait orientation.
- Landscape-left.
- Landscape-right.
- Flat or ambiguous orientation.

## 7.2 Stability and hysteresis

Prevent rotation jitter.

Implement:

- Orientation thresholds.
- Hysteresis.
- Debounce.
- Stable-duration requirements.
- Filtering.
- Ambiguous-position handling.
- Sensor-loss handling.

The screen must not rotate repeatedly when the phone is close to a threshold.

Do not rotate while the phone is lying flat unless that behaviour is explicitly intended and stable.

## 7.3 Manual override

If Nuxel has a manual rotation lock:

- Respect it.
- Do not override it.
- Expose automatic/manual state.
- Restore automatic mode when unlocked.

## 7.4 Actual display integration

Do not stop at calculating a landscape state.

Connect orientation events to the actual Nuxel display compositor or display-rotation mechanism.

Verify:

- Display mode changes.
- Touch coordinate transformation.
- Pointer orientation.
- Application layout response.
- Return to portrait.

A sensor reading that says LANDSCAPE while the visible display remains in portrait is a failure.

---

# 8. PHYSICAL VALIDATION — OPERATOR REQUIRED

This section is mandatory.

The operator will physically rotate the phone.

You must coordinate with the operator and verify actual hardware behaviour.

Do not simulate this test.

Do not use prerecorded data.

Do not infer physical success from logs alone.

## 8.1 Start a live diagnostic

Before asking the operator to rotate the phone, show:

- Live accelerometer XYZ.
- Live gyroscope XYZ.
- Current sensor status.
- Raw orientation.
- Filtered orientation.
- Current Nuxel display orientation.
- Last sample timestamp.
- Stability/confidence.

Verify that readings update continuously.

## 8.2 Portrait baseline

Ask the operator to hold the phone upright in normal portrait orientation.

Wait for stable readings.

Record:

- Accelerometer values.
- Gyroscope values.
- Detected orientation.
- Actual display orientation.
- Timestamp.

The phone must remain in portrait.

## 8.3 Landscape test

Ask the operator to physically rotate the phone 90 degrees clockwise and hold it.

Observe the live sensor readings.

Verify that:

1. Accelerometer values change plausibly.
2. The orientation algorithm detects landscape.
3. The state remains stable.
4. Nuxel actually rotates its display.
5. The visible UI is now landscape.
6. Touch input remains correctly mapped.

Hold the phone in landscape for several seconds.

Record the evidence.

## 8.4 Return to portrait

Ask the operator to rotate the phone upright again.

Verify:

- Accelerometer returns to a portrait-consistent gravity vector.
- Orientation returns to portrait.
- Display physically returns to portrait.
- Touch input remains correct.

Record the evidence.

## 8.5 Repeat

Perform at least three complete cycles:

`PORTRAIT → LANDSCAPE → PORTRAIT`

If both landscape directions are supported, test both.

Record each cycle independently.

## 8.6 Failure handling

If the readings do not change:

- Inspect the hardware path.
- Inspect the driver.
- Inspect the sensor hub.
- Inspect firmware.
- Inspect sampling configuration.
- Inspect device permissions.
- Inspect service logs.

If readings change but orientation is wrong:

- Inspect axis mapping.
- Inspect mounting matrix.
- Inspect sign conventions.
- Inspect thresholds.
- Inspect filtering.

If orientation state changes but the display does not:

- Inspect the compositor integration.
- Inspect display rotation support.
- Inspect output configuration.
- Inspect touch transformation.

Do not declare success until the visible Nuxel display actually rotates.

If the operator is unavailable, mark the physical test:

`NOT TESTED — OPERATOR REQUIRED`

Never claim it passed.

---

# 9. AUTOMATED TESTS AND QUALITY GATES

Implement and run relevant tests.

At minimum:

- Driver build test.
- Device tree build test.
- Firmware validation test.
- Sensor service startup test.
- Sensor service restart test.
- Device permissions test.
- Live sample test.
- Timestamp progression test.
- Sampling-rate sanity test.
- Accelerometer range sanity test.
- Gyroscope range sanity test.
- Orientation algorithm unit tests.
- Axis mapping tests.
- Portrait/landscape transition tests using recorded test vectors.
- Hysteresis tests.
- Manual rotation-lock tests.
- Sensor-loss tests.
- Suspend/resume tests, where practical.
- Display integration tests.
- Boot integration tests.

Synthetic orientation vectors are useful for algorithm tests, but they do not replace the physical rotation test.

Record test commands and outputs.

---

# 10. BOOT, FLASH AND REPAIR LOOP

This is an autonomous repair task.

You are expected to continue through implementation, flashing, rebooting, diagnosing and fixing until Nuxel boots successfully and the sensor functionality works.

## 10.1 Read the existing reflash plan

Inspect:

`REFLASH-PLAN.md`

Also inspect any active combined kernel batch.

Coordinate changes so the resulting image includes all approved work.

Do not discard or overwrite unrelated changes.

Preserve NFC, USBNET and other approved kernel/device-tree work.

Build one coherent image from a consistent source tree.

## 10.2 Before every flash

Perform all of these checks:

1. Confirm the connected device is the intended S10+.
2. Confirm the phone is in TWRP.
3. Confirm USB communication works.
4. Confirm the original boot backup exists.
5. Confirm the new boot image was built successfully.
6. Confirm the image format and target are correct.
7. Confirm the image checksum.
8. Confirm only the approved boot partition will be modified.
9. Save the build and flash logs.

Do not flash if any of these checks fail.

## 10.3 Flash and reboot

Flash the verified boot image using the established and verified device procedure.

Reboot the phone.

Wait for the device to enumerate and become accessible.

Determine whether Nuxel has booted.

## 10.4 TWRP-return rule

**If the phone returns to TWRP after your reboot, the Nuxel boot failed.**

The operator did not manually return it to TWRP.

Do not assume it is a successful boot.

Do not mark it as an operator interruption.

Collect evidence immediately:

- TWRP logs.
- Kernel logs, where accessible.
- `pstore` / `ramoops`, if available.
- Bootloader or recovery messages.
- Last boot image identity and checksum.
- Kernel panic information.
- Initramfs errors.
- Root filesystem errors.
- Module-loading errors.
- Firmware-loading errors.
- Device tree errors.
- SELinux or permission failures, if applicable.

Identify the actual failure mechanism.

## 10.5 Repair and retry

After a failed boot:

1. Preserve logs.
2. Identify the most likely root cause.
3. Verify the diagnosis against evidence.
4. Modify the source.
5. Rebuild.
6. Run all relevant gates.
7. Generate a new image.
8. Calculate and record its checksum.
9. Reverify the device and backup.
10. Reflash the approved boot partition.
11. Reboot.
12. Repeat.

Never blindly reflash the same failing image.

Never make unrelated speculative changes just to get past a failure.

Make targeted, evidence-based corrections.

## 10.6 Recovery safety limit

Continue repairing and retrying while:

- TWRP remains accessible.
- USB communication is reliable.
- The original boot backup remains available.
- The approved boot partition is positively identified.
- The next image passes the build and verification gates.

If three consecutive attempts fail for the same unresolved cause, stop and reassess rather than repeating the same approach.

If recovery access becomes uncertain, STOP.

If the phone cannot be positively identified, STOP.

If the correct partition cannot be verified, STOP.

Never sacrifice recoverability to satisfy the completion requirement.

## 10.7 Boot success

A successful boot means:

- Nuxel actually starts.
- The device is not merely sitting in recovery.
- The expected root filesystem is mounted.
- The system reaches the intended userspace.
- Relevant logs show no fatal boot failure.
- Sensor integration can be tested.

Only then proceed to final physical sensor validation.

---

# 11. DELIVERABLES

Create the following files in the repository:

### `PWNAGE-SSP-REPORT.md`

Executive summary:

- What was implemented.
- What works.
- What does not work.
- Final boot status.
- Final sensor status.
- Final auto-rotation status.
- Outstanding limitations.

### `PWNAGE-SSP-HARDWARE-MAP.md`

Exact hardware topology, bus mapping, GPIOs, IRQs, device tree, drivers and data flow.

### `PWNAGE-SSP-RUNTIME-INVENTORY.md`

Complete inventory of `./sensors/` and all runtime dependencies.

Include file hashes and compatibility findings.

### `PWNAGE-SSP-TEST-RESULTS.md`

Automated tests and physical validation results.

Include actual measurements and timestamps.

### `PWNAGE-SSP-REFLASH-LOG.md`

Every build, image checksum, flash attempt, reboot result, failure diagnosis and repair.

### Image manifest

Include:

- Final boot image filename.
- SHA256.
- Kernel version.
- Build configuration.
- DTB identity.
- Included modules.
- Included firmware.
- Build timestamp.
- Source revision.

Do not delete the original boot backup.

---

# 12. FINAL REPORTING RULES

Use these statuses consistently:

- `PASS` — verified working.
- `PARTIAL` — some functionality works, but acceptance criteria are incomplete.
- `FAIL` — tested and failed.
- `NOT TESTED` — not physically or automatically verified.
- `UNSUPPORTED` — verified hardware/software limitation prevents implementation.

Distinguish between:

- Source code implemented.
- Kernel compiled.
- Kernel booted.
- Device detected.
- Live data received.
- Nuxel integration working.
- Physical rotation verified.

These are separate milestones.

Do not collapse them into one generic SUCCESS status.

## FINAL COMPLETION CONDITION

You are not finished when the code compiles.

You are not finished when the phone boots.

You are not finished when `/dev/iio:deviceX` appears.

You are not finished when sensor values are printed.

You are finished when:

1. Nuxel boots successfully on the S10+.
2. The actual sensor hardware supplies live readings.
3. The Nuxel sensor service operates reliably.
4. The orientation algorithm works.
5. The actual Nuxel display rotates in response to physical phone movement.
6. At least three physical portrait/landscape/portrait cycles pass.
7. Evidence and final reports are saved.

**Keep investigating, implementing, testing, repairing and reflashing until these conditions are met, unless a defined recovery safety condition requires you to stop.**

The goal is working hardware, not a convincing-looking implementation.
