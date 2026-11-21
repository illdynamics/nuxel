# NUXEL S10+ — OPERATION SENSOR FIRST LIGHT
## DeepSeek-V4-Pro-Thinking — BCM47752 / LSM6DSO Native Linux Recovery Mission

### PRIMARY OBJECTIVE

You are the principal Linux kernel, embedded firmware, reverse-engineering, sensor driver and Wayland systems engineer for NUXEL.

Our Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos9820) is **FINALLY BOOTING NUXEL AGAIN**, and TWRP recovery also works.

After extensive camera development and emergency boot-chain recovery, we are deliberately suspending all camera and NFC work.

**YOUR NEW MISSION: RESTORE THE REAL ACCELEROMETER AND GYROSCOPE, THEN IMPLEMENT FULL HARDWARE-DRIVEN AUTOMATIC ROTATION THROUGHOUT NUXEL.**

This mission covers two dependent subsystems:

1. Broadcom BCM47752 SSP/BBD sensor-hub firmware initialization and actual LSM6DSO accelerometer/gyroscope streaming.
2. Complete native Nuxel automatic rotation using physical sensor measurements, with correct display, touchscreen, application and lockscreen behavior.

We want a reliable, maintainable native Linux solution.

**No Android userspace dependencies in the finished Nuxel runtime.**

You may study the matching Samsung Android implementation, reverse-engineer compatible protocols, reuse legally obtained firmware and port suitable kernel code.

Do not require Samsung Android services or framework components to be running as part of the final product.

Do not stop after creating device nodes, loading firmware, obtaining an ACK or passing simulated tests.

**The first real success milestone is physical motion data that changes as the actual phone is tilted.**

The final success milestone is stable automatic screen rotation in all supported modes, including after reboot and suspend/resume.

---

# PHASE 0 — PROTECT THE RECOVERED NUXEL INSTALLATION

This phase is mandatory.

We recently suffered a serious boot failure following changes to the kernel and device-tree partitions.

Nuxel and TWRP are now working again.

**DO NOT REPEAT THE CAMERA BOOT-CHAIN FAILURE.**

Before modifying anything, investigate the exact recovered state.

Read:

- `pwn/NUXEL_EMERGENCY_BOOT_RECOVERY.md`
- `pwn/NUXEL_KNOWN_GOOD_BOOT_IMAGES.md`
- Current boot and recovery scripts.
- Current kernel build manifests.
- Current device-tree build configuration.
- Any newer successful recovery reports.
- Actual live-device state.

The archived recovery documentation identifies three tightly coupled normal-boot components:

- DTB — historically `sda12`.
- DTBO — historically `sda13`, with `androidboot.dtbo_idx=9`.
- BOOT — historically `sda14`.

It identifies RECOVERY separately as historically `sda15`.

These values must be reverified against the currently working physical device.

**Do not assume the archived recovery report describes the latest successful repair.**

Identify and preserve the exact currently functioning image set.

Record:

- Live kernel version.
- Git revision.
- Kernel configuration.
- Boot image hash.
- DTB and DTBO hashes, where safely obtainable.
- Recovery image identity.
- Last successful deployment.
- Last known-good recovery procedure.

Preserve verified host copies of the working images and their hashes.

Check whether the phone's current boot is stable before proceeding.

Do not alter the camera or NFC drivers.

Do not introduce changes to modem, fingerprint, EFS or unrelated partitions.

Use userspace-only improvements wherever possible.

Any new boot, DTB, DTBO or recovery flash requires a separate, evidence-backed preflight and explicit owner approval.

No speculative GPIO, reset, watchdog, MCU power or live firmware operations.

---

# PHASE 1 — RECONCILE ALL EXISTING SSP WORK

DO NOT START THE SSP PROJECT FROM SCRATCH.

We have already invested substantial work into the BCM47752 sensor hub.

Locate and read the most recent versions of:

- `ssp.md`
- `hw/NUXEL_03_BCM47752_SENSORS_STANDALONE.md`
- `hw/NUXEL_04_AUTO_ROTATION_STANDALONE.md`
- `NUXEL_SSP_RECOVERY_V2/`
- `NUXEL_SSP_CONTINUATION_PACK/`
- `services/nuxel-orientation/`
- `tools/s10plus/ssp-native/`
- `tools/s10plus/ssp-runtime/`, if present.
- `kernel/s10plus/patches/0013*`
- `kernel/s10plus/patches/0020*`
- `configs/nuxel/sensors/sensors.json`
- `configs/nuxel/orientation/orientation.json`
- Relevant deployment scripts.
- All available SSP reports and previous physical-device evidence.

The archived `ssp.md` references:

Branch: `feat/ssp`

Commit: `6bcbcea6`

Report: `reports/SSP-PROTOCOL-CONTRACT-2026-11-17.md`

Also locate:

`reports/SSP-STOCK-RUNTIME-2026-11-17.md`

`reports/SSP-FIRST-LIGHT-FINAL-RECOVERY.md`

`reports/SSP-CONTINUATION-20261113-2130.md`

Some files may exist only in another local checkout or worktree, because the provided archive does not contain every historical report and recovered binary.

Search the actual development host and existing Git worktrees rather than assuming the files are lost.

Read the most recent committed and uncommitted work.

Preserve all source changes, experimental branches and historical evidence.

## Previously established progress

The existing evidence reports:

- Samsung BCM47752 sensor-hub hardware identified.
- SSP/BBD kernel interfaces present.
- LSM6DSO motion sensors enumerated.
- Correct embedded patch metadata researched.
- Samsung vendor `lhd` runtime and dependencies recovered in later work.
- Native firmware downloader implementation started.
- BBD transport framing and CRC substantially investigated.
- Multiple simulated transport tests passing.
- Samsung initialization-state callbacks partially reverse-engineered.
- Native orientation daemon already implemented.
- Manual screen rotation working.
- Seven orientation modes implemented.
- Physical sensor streaming still unverified.

Revalidate against the live phone.

Do not repeat resolved investigations unless the current device contradicts them.

---

# PHASE 2 — ESTABLISH A FRESH LIVE HARDWARE BASELINE

Connect to the working Nuxel phone using the already configured SSH identity.

Historical connection:

`root@10.11.12.99`

Use the existing owner's SSH-key configuration.

Do not print, upload or commit private key material.

**Begin with read-only diagnostics.**

Record the actual running kernel, active services and device nodes.

Inspect:

- `/dev/ttyBCM`
- `/dev/bbd_control`
- `/dev/bbd_sensor`
- `/dev/bbd_patch`
- `/sys/class/sensors/ssp_sensor/`
- `/sys/class/sensors/accelerometer_sensor/`
- `/sys/class/sensors/gyro_sensor/`
- `/sys/bus/iio/devices/`
- `/run/nuxel-orientation/status.json`

Also inspect kernel logs, SSP probe status, power-management state and BBD transport diagnostics.

Check:

- Actual MCU status.
- `ssp_down`.
- Current firmware revision, if valid.
- Sensor availability bitmask.
- Accelerometer enable state.
- Gyroscope enable state.
- Current accelerometer samples.
- Current gyroscope samples.
- Existing timestamp or sample counters.
- SSP daemon state.
- Orientation daemon state.
- Whether competing processes already own the BBD transport.

Collect a timestamped baseline with the known-good boot identifier.

Use the existing `ssp_live_snapshot.py` or improve it where necessary.

Do not trigger firmware upload, power toggles, reset commands or speculative MCU initialization during baseline collection.

**Never confuse an enumerated device with a functioning sensor.**

---

# PHASE 3 — FIX THE CONFLICTING INITIALIZATION PATHS

Investigate a critical inconsistency in the archived repository.

The following modules contain logic that may write `ESW:READY`:

- `services/nuxel-orientation/nuxel_ssp_bridge.py`
- `services/nuxel-orientation/nuxel_orientation/sensors.py`

However, the newer SSP protocol report states that premature `ESW:READY` publication was removed.

Determine:

1. Which code is currently deployed.
2. Which implementation owns the SSP initialization sequence.
3. Whether multiple daemons attempt to initialize the hub.
4. Whether any code sends `ESW:READY` before the real firmware/application readiness condition.
5. Whether userspace is incorrectly substituting a readiness notification for actual firmware initialization.
6. Whether old orientation code can race with the native BBD client.
7. Whether service restart behavior causes repeated initialization attempts.

Consolidate the system around one authoritative initialization owner.

Remove redundant and premature initialization logic.

Do not emit fake readiness events.

Investigate the existing `nuxel-ssp-bridge.service`, including duplicate `RestartSec` entries, retry behavior, startup dependencies, failure reporting and device ownership.

Do not allow a failed bridge to endlessly restart hardware operations.

Preserve truthful sensor-unavailable status until real samples exist.

---

# PHASE 4 — VERIFY THE ACTUAL RUNNING KERNEL IMPLEMENTATION

Review:

`kernel/s10plus/patches/0020-nuxel-ssp-hub-power-and-pm.patch`

and:

`kernel/s10plus/patches/0013-nuxel-sensorhub-bringup-native-bbd.patch.experimental`

The archived source suggests that:

- Patch 0020 handles some regulator and power-management issues.
- Patch 0013 contains experimental native SSP/BBD functionality.
- Patch 0013 is excluded from the normal build.
- The archived `nuxel_bringup` interface may return `-EOPNOTSUPP`.

The current running kernel may differ.

Determine precisely which code is compiled, installed and executing.

Trace:

- SSP probe.
- Sensor-hub power state.
- Regulator ownership.
- SPI controller initialization.
- BBD transport setup.
- MCU startup state.
- Firmware patch delivery.
- Kernel-to-userspace ownership.
- SSP chip identification.
- Sensor scanning.
- Sensor enabling.
- Interrupt delivery.
- Power-management recovery.

Do not blindly apply patch 0013 over patch 0020.

The old reports warn that the two patches contain overlapping changes.

If a kernel repair is actually necessary, isolate the minimum justified changes, rebase them cleanly, prove that they compile and test them offline first.

Do not include unrelated camera or NFC modifications in the new kernel build.

---

# PHASE 5 — FINISH THE SAMSUNG SSP FIRMWARE PROTOCOL

Prefer reuse of the already recovered matching Samsung implementation.

The newer SSP report identifies the matched vendor `lhd` binary with SHA-256:

`6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`

It also identifies important callback locations:

- Normal version callback: `0x39b9c`.
- Extended version callback: `0x39d08`.
- State transitions: 8 → 9 and 15 → 16.

The report describes metadata writes occurring before state validation.

Investigate this thoroughly.

Trace the complete validated message dispatch chain into those callbacks.

Determine:

- The actual operation identifiers.
- Which messages are emitted by the host.
- Which responses come from the MCU.
- How sequence and session identities work.
- Transport ACK versus operation completion.
- Retry and cancellation behavior.
- Firmware download completion.
- Firmware start confirmation.
- Version readback.
- MCU-ready confirmation.
- Failure-state cleanup.
- Whether unexpected callbacks can mutate state.

Do not infer message IDs from ELF addresses.

Do not invent successful responses.

Use exact matching vendor binaries as read-only behavioral references.

The final native implementation must faithfully reproduce the verified protocol contract.

## Embedded patch identity

Historical evidence identifies:

- BCM47752 ASIC: `0x004775B0`.
- Firmware blob length: 438,895 bytes.
- Patch address metadata: `0x00800161`.
- Decoded blob IEEE CRC-32: `0x93D35BB4`.
- Kernel-export patch SHA-256: `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72`.

Verify these values against the actual matching source and running device.

Do not confuse the vendor header's `Crc=0xC1` metadata with IEEE CRC-32.

Do not substitute BCM47765 or another Broadcom firmware simply because a filename looks similar.

Do not alter the firmware content without strong compatibility evidence.

---

# PHASE 6 — IMPLEMENT THE NATIVE SENSOR-HUB SOLUTION

Determine the smallest complete solution that can initialize the actual BCM47752 and deliver real measurements.

Preferred architecture:

```text
BCM47752 / LSM6DSO hardware
              |
        Exynos SPI / BBD
              |
     Verified SSP MCU startup
              |
    Native Linux kernel driver
              |
      Real accel / gyro data
              |
      Nuxel sensor provider
              |
      Nuxel orientationd
              |
       Wayland compositor
              |
     Display + touch rotation
```

Choose between:

**A. Complete the existing native BBD/SSP implementation.**

Reuse the existing kernel transport, firmware patch and native downloader.

Implement the missing protocol-completion behavior, proper ownership and reliable stream startup.

**B. Adapt a compatible existing Linux driver.**

Research the pinned Samsung Exynos9820 downstream kernel first.

Relevant references:

https://github.com/Linux4/android_kernel_samsung_exynos9820

https://github.com/LineageOS/android_kernel_samsung_exynos9820

https://github.com/torvalds/linux/tree/master/drivers/iio/common/ssp_sensors

Check kernel version, compatible strings, MCU protocol, transport and hardware generation.

The generic upstream Samsung SSP driver is a reference, not automatically drop-in compatible with this Broadcom implementation.

**C. Reconstruct the necessary native runtime behavior from the matching Samsung implementation.**

Use the isolated, matching vendor daemon as a protocol oracle.

Keep it outside the production native Nuxel runtime.

Never substitute a full Android framework for a missing small native hardware interface.

You are authorized to refactor or rewrite the necessary native sensor code, provided the implementation is grounded in the verified device protocol.

Prioritize reliable firmware initialization and sensor streaming over architectural perfection.

Do not introduce a large new framework if a small, maintainable adapter is sufficient.

---

# PHASE 7 — SAFE PHYSICAL FIRST-LIGHT TESTING

Before any hardware-mutating trial, review the exact actions and obtain explicit approval.

This includes:

- MCU firmware upload.
- Power-state changes.
- GPIO or standby changes.
- Hardware resets.
- New kernel deployment.
- Boot/DTB/DTBO changes.

Historical SSP work reports unexpected restarts associated with GNSS/SSP power and standby GPIO experiments.

**Do not repeat those experiments.**

No unrestricted power toggling.

No speculative firmware opcodes.

No unbounded recovery loops.

No repeated writes after an unknown device state.

For a proposed physical trial, present:

- Exact commands or operations.
- Verified device interfaces.
- Expected state transitions.
- Firmware and binary hashes.
- Maximum number of attempts.
- Timeout and abort behavior.
- Risks to current SSH/USB connectivity.
- Recovery path using the restored known-good Nuxel image set.
- Evidence that justifies the trial.

Continue all safe offline engineering before requiring this approval.

Once the physical trial is approved, execute only the approved operations.

Collect logs and exact responses.

Do not mark success based solely on host commands returning zero.

---

# PHASE 8 — PROVE PHYSICAL ACCELEROMETER AND GYROSCOPE STREAMING

Once the MCU is initialized:

1. Read actual sensor scanning information.
2. Verify supported sensor identities.
3. Enable accelerometer and gyroscope streaming using the verified protocol.
4. Read genuine sensor measurements.
5. Verify the samples are correctly timestamped.
6. Verify the measurements change with physical movement.
7. Validate axis signs, scaling and approximate gravity magnitude.
8. Check for frozen, duplicated or malformed samples.
9. Validate clean sensor disable and re-enable behavior.
10. Verify stability over repeated readings.

Use actual handset movement to demonstrate:

- Stationary upright orientation.
- Landscape left.
- Landscape right.
- Upside-down portrait.
- Face-up and face-down states.
- Controlled changes in angular motion.

Do not generate fake nonzero values to satisfy the tests.

Do not accept samples that merely change because of initialization noise.

Require coherent, time-correlated physical measurements.

**GATE 1: ACCELEROMETER_PHYSICAL_STREAMING = PASS**

**GATE 2: GYROSCOPE_PHYSICAL_STREAMING = PASS**

These must be independently verified.

---

# PHASE 9 — COMPLETE NUXEL AUTOMATIC ROTATION

Only after genuine accelerometer streaming succeeds, finish auto-rotation.

Reuse:

- `services/nuxel-orientation/nuxel-orientationd`
- `services/nuxel-orientation/nuxel_orientation/policy.py`
- `services/nuxel-orientation/nuxel_orientation/sensors.py`
- `services/nuxel-orientation/nuxel_orientation/apply.py`
- `configs/nuxel/orientation/orientation.json`

Preserve the seven established modes:

1. `auto` — all four orientations.
2. `auto-portrait` — portrait and reverse portrait.
3. `auto-landscape` — both landscape orientations.
4. `portrait` — locked portrait.
5. `landscape` — locked landscape.
6. `reverse-portrait` — locked reverse portrait.
7. `reverse-landscape` — locked reverse landscape.

Do not change the user-facing mode names or existing configuration contracts unnecessarily.

Complete:

- Physical sensor-axis mapping.
- Correct mount matrix for the S10+.
- Calibration verification.
- Sensor sampling.
- Gravity-vector orientation detection.
- Flat-device handling.
- Hysteresis and debounce.
- Appropriate rotation cooldown.
- Stable transition handling.
- Touchscreen coordinate transformation.
- Wayland compositor transform.
- Application layout updates.
- Lockscreen behavior.
- Rotation-lock behavior.
- Persistent Settings and Quick Settings integration.

Use the existing architecture instead of adding competing orientation daemons.

If `iio-sensor-proxy` is useful for standard Linux consumers, integrate it properly, but do not require it if the existing native sensor source is more accurate.

Prevent conflicting services from fighting over screen rotation.

Ensure video playback, native GTK apps, Flatpak apps and Nuxel PWAs respond correctly to screen orientation.

Do not break manual rotation.

If the physical sensor temporarily becomes unavailable, retain a safe known orientation and report the unavailable state honestly.

---

# PHASE 10 — TEST REBOOT, SUSPEND AND FAILURE RECOVERY

Once physical streaming and rotation work, verify:

- Clean startup after normal reboot.
- No dependency on manually running a shell command after boot.
- Proper suspend/resume behavior.
- Sensor availability after resume.
- No duplicate background services.
- No lost SSP device ownership.
- No stuck sensor interrupts.
- No repeated firmware initialization storm.
- No unexpected reboot.
- No kernel warning or panic.
- No regression in GNSS.
- No USB or SSH regression.
- No display or touchscreen regression.
- No camera or NFC modifications.
- No excessive CPU usage.

Perform bounded repeated tests.

Never claim suspend/resume success without testing an actual suspend/resume cycle.

Keep the latest known-good boot image and recovery path intact.

---

# PHASE 11 — DEPLOY TO THE LIVE PHONE

Inspect `./scripts/` and the established Nuxel deployment procedure.

Use userspace deployment first whenever possible.

For services:

- Install the correct binaries and scripts.
- Update only the required systemd units.
- Validate configuration.
- Verify permissions.
- Ensure startup ordering is correct.
- Keep failed hardware initialization from triggering uncontrolled restart loops.
- Check that rotation works without root access from ordinary applications.

Only request a new kernel flash if source and physical evidence demonstrate that it is necessary.

If kernel changes are required:

- Preserve the current working boot-image set.
- Build against the correct pinned kernel.
- Validate patch application.
- Confirm device-tree compatibility.
- Confirm the exact S10+ revision.
- Produce a matching, verified image set.
- Test the build before proposing installation.
- Obtain authorization before writing boot partitions.
- Never copy experimental camera DT modifications into the working boot configuration.

Do not replace recovery merely because you are rebuilding the kernel.

Do not flash unrelated partitions.

---

# PHASE 12 — REQUIRED TEST MATRIX

Maintain an evidence-backed live acceptance report.

| Test | Required result |
|---|---|
| BCM47752 device recognized | PASS |
| SSP firmware identity verified | PASS |
| Verified MCU initialization | PASS |
| Sensor scanning information received | PASS |
| Physical accelerometer readings | PASS |
| Physical gyroscope readings | PASS |
| Sensor values react to physical movement | PASS |
| Correct sensor-axis calibration | PASS |
| Auto portrait/landscape transitions | PASS |
| Reverse portrait support | PASS |
| Reverse landscape support | PASS |
| Auto-portrait policy | PASS |
| Auto-landscape policy | PASS |
| Manual rotation preserved | PASS |
| Touch coordinates correct after rotation | PASS |
| Nuxel Settings integration | PASS |
| Quick Settings rotation lock | PASS |
| PWA and GTK behavior | PASS |
| Flatpak orientation behavior | PASS where supported by application |
| Reboot persistence | PASS |
| Suspend/resume stability | PASS |
| No unexpected kernel crash | PASS |
| SSH and network remain operational | PASS |

Every hardware test must include timestamp, running kernel, observed sample/output, relevant logs and result.

Use the status labels:

- `PROVED_LIVE`
- `HISTORICAL_LIVE`
- `OFFLINE_TESTED`
- `PRESENT_IN_REPO`
- `INFERRED`
- `BLOCKED`
- `UNKNOWN`

Do not substitute `OFFLINE_TESTED` for `PROVED_LIVE`.

---

# PHASE 13 — DOCUMENTATION AND CODE DELIVERABLES

Maintain or create:

`reports/SSP-FIRST-LIGHT-FINAL-RECOVERY.md`

`reports/SSP-PROTOCOL-CONTRACT.md`

`reports/SSP-PHYSICAL-ACCEPTANCE.md`

`reports/NUXEL-AUTO-ROTATION-ACCEPTANCE.md`

`reports/SSP-BOOT-SAFETY-AND-ROLLBACK.md`

Also update:

- Applicable sensor and orientation source code.
- Native driver build instructions.
- Systemd services.
- Sensor configuration.
- Orientation configuration.
- Unit and integration tests.
- Existing hardware component status documentation.
- Relevant changelog entries.

Record the exact working revision and build hashes.

Preserve existing commits and use isolated, logical changes.

Do not commit proprietary Samsung runtime files or private device data into a public repository.

---

# PHASE 14 — EXECUTION DISCIPLINE

You are an implementation agent, not merely a research assistant.

For every milestone:

1. Identify the exact remaining blocker.
2. Inspect the current source and real evidence.
3. Find and compare viable upstream implementations.
4. Select the least invasive technically sound fix.
5. Implement the fix.
6. Build and test.
7. Deploy safe userspace changes.
8. Run physical tests when authorized.
9. Record evidence.
10. Fix the next demonstrated issue.

Do not repeat old failed experiments.

Do not fabricate sensor readings.

Do not treat kernel-node enumeration as completion.

Do not endlessly rewrite planning documents.

When a hardware operation is required, finish all possible offline preparation, present the precise proposed action and wait for approval.

If an external artifact is genuinely missing, identify it exactly and explain why the current source cannot replace it.

Never guess firmware behavior to force progress.

Preserve the known-good operating system at every stage.

---

# FIRST TASKS — EXECUTE IMMEDIATELY

1. Reconcile the current restored Nuxel boot with the November 21 recovery documentation.
2. Find the newest SSP code, including branch `feat/ssp` and commit `6bcbcea6` if available.
3. Read the November 17 protocol and runtime reports.
4. Determine whether the current `ESW:READY` paths conflict with the latest verified state machine.
5. Determine whether the running kernel's `nuxel_bringup` is implemented or returns `-EOPNOTSUPP`.
6. Establish a fresh read-only physical sensor baseline.
7. Continue the validated native SSP implementation instead of starting another speculative downloader.
8. Fix all software-only blockers.
9. Prepare a controlled first-light trial once the handshake and recovery procedure are proven.
10. After physical streaming succeeds, complete native auto-rotation.

## FINAL DEFINITION OF DONE

**The project is not complete until real accelerometer and gyroscope measurements are verified on the actual S10+, all supported automatic orientation modes work throughout Nuxel, and the system survives reboot and suspend/resume without manual intervention.**

Do not touch the camera or NFC development tracks.

Do not destabilize the newly recovered Nuxel boot chain.

**START WITH THE REAL CURRENT SSP IMPLEMENTATION AND FIX THE FIRST DEMONSTRATED FAILURE.**

BEGIN OPERATION SENSOR FIRST LIGHT.
