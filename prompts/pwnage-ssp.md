# PWNAGE SSP — S10+ Sensors & Auto-Rotation

You are working on Nuxel, our native Fedora-based Linux phone OS.

Your mission is to get the Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820) accelerometer, gyroscope and automatic display rotation working properly.

## STARTING CONDITIONS

I will:

1. Extract the supplied `S10Plus-SSP-Runtime-Acquisition-Pack.zip` into `./sensors/`.
2. Boot the phone into TWRP.
3. Connect it to this workstation over USB.
4. Start you.

You may flash the verified boot image and reboot the phone.

Read and follow:

`full-pwnage-ssp.md`

That document is your complete technical specification, acceptance criteria and safety policy.

## CRITICAL: KEEP GOING UNTIL IT WORKS

This is an implementation and hardware-validation task, NOT a research-only task.

You must:

1. Inspect the complete Nuxel repository.
2. Inspect every file in `./sensors/`.
3. Identify the exact sensor hardware and actual data path.
4. Determine whether the Broadcom SSP sensor hub or direct Linux sensor drivers should be used.
5. Recover and validate the required firmware/runtime components.
6. Implement the necessary kernel, device-tree and userspace changes.
7. Integrate the sensor service with Nuxel.
8. Implement accelerometer-based orientation detection, with gyroscope assistance where appropriate.
9. Build and test the complete boot image.
10. Flash it through the verified TWRP procedure.
11. Reboot and verify that Nuxel actually starts.
12. Physically test automatic rotation with me.

Do not stop after writing a report or identifying missing components. Investigate alternatives and implement the best viable solution.

## IMPORTANT HARDWARE LEADS

These are leads to verify, not assumptions:

- Broadcom BCM47752KUB1G / `ssp,BCM4773` sensor hub.
- STM LSM6DSO inertial sensor.
- Possible vendor components such as `lhd` and `sensors.sensorhub.so`.
- Possible BBD interfaces:
  - `/dev/bbd_patch`
  - `/dev/ttyBCM`
  - `/dev/bbd_control`
  - `/dev/bbd_sensor`

Do not assume Android/Bionic vendor binaries run natively under Fedora/glibc.

Prefer a native Linux implementation or the smallest possible compatibility layer.

Do not substitute firmware from a different sensor-hub model without verified compatibility.

Do not guess GPIOs, IRQs, bus addresses, power rails or device-tree properties.

## THE TWRP RETURN RULE

I will start you with the phone already in TWRP.

After you flash and reboot:

**If the phone returns to TWRP, that means Nuxel failed to boot. I did not manually put it back into recovery.**

Treat every such return as a failed boot.

Collect logs, diagnose the cause, fix the implementation, rebuild, verify the new image, flash again and reboot.

Continue until Nuxel boots and the sensor functionality works.

Never blindly reflash an identical failing image.

Before every flash:

- Verify device identity.
- Verify TWRP/USB access.
- Preserve the original boot image and checksum.
- Verify the new image and checksum.
- Verify the exact boot partition.
- Flash ONLY the approved boot partition.

Never touch EFS, modem, recovery, bootloader, PIT, userdata or unrelated partitions. Never wipe or factory-reset the device.

If recovery becomes uncertain, the device identity is unclear, or the boot partition cannot be verified, stop.

If three consecutive attempts fail for the same unresolved cause, reassess before continuing.

Read `REFLASH-PLAN.md` and coordinate with other kernel work. Preserve NFC, USBNET and other approved changes. Build a coherent combined image rather than overwriting another agent's work.

## PHYSICAL ROTATION TEST — MANDATORY

Once Nuxel boots and the sensor service is running:

1. Start a live diagnostic showing accelerometer XYZ and gyroscope XYZ.
2. Ask me to hold the phone upright.
3. Verify stable portrait readings and portrait display.
4. Ask me to rotate the phone sideways and hold it.
5. Verify that live sensor values change.
6. Verify that orientation becomes landscape.
7. Verify that the actual Nuxel display rotates into landscape.
8. Ask me to return the phone upright.
9. Verify that the display returns to portrait.
10. Repeat for at least THREE complete cycles.

Test both landscape directions if supported.

Check touch-coordinate mapping as well as display rotation.

Use accelerometer gravity data for absolute orientation. Gyroscope-only orientation will drift.

Implement appropriate axis correction, filtering, hysteresis and debounce to prevent rotation jitter.

Do not simulate this physical test or claim it passed from synthetic data.

If I am not available to rotate the device, report `NOT TESTED — OPERATOR REQUIRED`.

## DELIVERABLES

Create:

- `PWNAGE-SSP-REPORT.md`
- `PWNAGE-SSP-HARDWARE-MAP.md`
- `PWNAGE-SSP-RUNTIME-INVENTORY.md`
- `PWNAGE-SSP-TEST-RESULTS.md`
- `PWNAGE-SSP-REFLASH-LOG.md`
- Final boot image manifest with SHA256.

Record all actual measurements, test outputs, boot attempts, failures and repairs.

Use explicit statuses:

`PASS`, `PARTIAL`, `FAIL`, `NOT TESTED`, `UNSUPPORTED`.

## DEFINITION OF DONE

You are not done when the code compiles.

You are not done when the phone merely boots.

You are not done when a sensor device node exists.

You are not done when you can print some sensor values.

You are done when:

- Nuxel boots successfully.
- Accelerometer supplies real live data.
- Gyroscope supplies real live data, if supported by the verified hardware path.
- The Nuxel sensor service works reliably.
- Orientation detection works.
- The actual Nuxel display rotates in response to physical phone movement.
- Three physical portrait → landscape → portrait cycles pass.
- All reports and evidence are saved.

**Keep working through implementation, testing, diagnosis, repair and verified reflashing until the actual phone works.**

Start by inspecting the repository, `./sensors/`, the current kernel state and `REFLASH-PLAN.md`. Then execute the full specification.
