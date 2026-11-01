# PWNAGE-57000 — Bring Nuxel Auto-Rotation to Life
## BCM47752 sensor hub recovery, Samsung LHD/BBD runtime compatibility and genuine accelerometer readings

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**OS:** Nuxel, Fedora-based ARM64  
**Priority:** Critical  
**Starting state:** Boot normally into Nuxel; connect over Wi-Fi SSH  
**Initial TWRP requirement:** NO  
**Kernel flash:** Only if investigation proves a kernel/device-tree correction is necessary

## Mission

Make genuine sensor-driven Auto orientation work on the physical S10+.

All four fixed display orientations are already verified. The orientation implementation now applies the correct transform and geometry:

| Mode | Angle | Transform | Logical |
|---|---:|---|---:|
| Locked (LS) | 90° | `270` | 1520×720 |
| Locked (RLS) | 270° | `90` | 1520×720 |
| Locked (RPT) | 180° | `180` | 360×760 |
| Locked (PT) | 0° | `normal` | 360×760 |

All returned `applied=true` and `success=true`. The phone was returned to Auto (PT).

**Do not modify or regress the working fixed-orientation implementation.**

The remaining blocker is the Samsung sensor hub.

Current kernel evidence:

```text
[SSPBBD] Sensors of MCU are not ready!
[SSPBBD] bbd_do_transfer(): completion is timeout!
[SSP] MCU device ID = 85, reading ID = -1
[SSP]: initialize_mcu - MCU is not working : 0xffffffff
[SSP] lhd is NULL or resetting
```

Current runtime evidence:

- `/vendor/bin/hw/lhd` exists.
- `/vendor/lib64/sensors.sensorhub.so` exists.
- `/vendor` is read-only and contains Samsung proprietary components.
- The Nuxel rootfs lacks the required Android/Bionic runtime, including the expected `/system/bin/linker64` and Bionic dependency libraries.
- The MCU patch/initialization sequence is not completing.
- Sensor `raw_data` remains `0,0,0`.
- The orientation daemon correctly reports unavailable sensor input instead of faking Auto success.

The main objective is to make the actual Samsung LHD/BBD initialization path work, or implement a compatible native Linux alternative.

## Important research lead

Inspect the current LineageOS Exynos9820/beyond1lte implementation.

Its `extract-files.py` applies compatibility fixups to the 32-bit and 64-bit Samsung sensor libraries:

- Removes `libhidltransport.so`.
- Adds `libutils-v32.so`.
- Rewrites the `android::Thread::run` symbol reference to the compatibility implementation.

This applies to `sensors.sensorhub.so` as well as related sensor libraries.

LineageOS also lists these Samsung vendor components:

- `vendor/bin/hw/lhd`
- `vendor/etc/sensor/lhd.conf`
- `vendor/lib/sensors.sensorhub.so`
- `vendor/lib64/sensors.sensorhub.so`

Use these as a source-backed investigation lead. Do not blindly copy their patches or libraries into Nuxel without checking the matching vendor binary and Android ABI.

References:

- https://github.com/LineageOS/android_device_samsung_beyond1lte/blob/lineage-23.2/extract-files.py
- https://github.com/LineageOS/android_device_samsung_beyond1lte/blob/lineage-23.2/proprietary-files.txt

## Phase 1 — Audit the live hardware and driver

Inspect the running Nuxel kernel and actual device tree.

Verify:

- SSP/SensorHub driver is loaded and active.
- Relevant SPI controller and device are registered.
- MCU request/response GPIOs and interrupts are configured.
- Pinctrl state is correct.
- Required regulators and clocks are enabled.
- Reset and wake signals work.
- The expected sensorhub device nodes/sysfs interfaces exist.
- The driver supports the actual BCM47752/BBD protocol used by this device.
- No other service owns or interferes with the SPI device.

Inspect the exact kernel's SSPBBD/SSP implementation, Kconfig, device tree and driver state.

Do not assume an upstream or different Samsung-device sensor driver is compatible.

Determine whether the current errors are caused by:

1. Missing userspace LHD initialization.
2. Missing or incompatible BBD patch.
3. Incorrect daemon/service startup order.
4. Kernel driver/DT configuration.
5. MCU reset/power/SPI communication.
6. A combination of these.

## Phase 2 — Recover the exact Samsung userspace dependency chain

Inspect the actual vendor files on this phone.

At minimum:

```text
/vendor/bin/hw/lhd
/vendor/etc/sensor/lhd.conf
/vendor/lib64/sensors.sensorhub.so
/vendor/lib/sensors.sensorhub.so
```

Inspect other related vendor libraries, firmware and init/service files.

Determine the actual stock vendor firmware build and Android version that supplied these files.

Inspect:

- ELF architecture.
- ELF interpreter (`PT_INTERP`).
- `DT_NEEDED` dependencies.
- SONAME dependencies.
- Undefined symbols.
- Symbol versions.
- Required Android API level.
- Required Bionic runtime.
- Required vendor/system libraries.
- Configuration paths.
- Device-node access.
- Expected properties and services.
- Actual launch sequence.

Do not assume `/system/bin/linker64` is the only missing dependency.

Do not copy a random Android linker or arbitrary Bionic libraries from a different device or Android release.

## Phase 3 — Implement the best compatible runtime

Preferred route: create a minimal, isolated Android/Bionic compatibility runtime matching the actual vendor binaries.

Possible location:

```text
/opt/nuxel/android-compat/
```

Use the exact Android/Bionic linker and required library dependency closure.

Inspect Android linker namespace configuration and reproduce only the required vendor process environment.

AOSP reference:

https://source.android.com/docs/core/architecture/vndk/linker-namespace

Do not assume that glibc `LD_LIBRARY_PATH` can make Android/Bionic binaries run natively.

Do not overwrite Nuxel's glibc libraries.

Do not replace Nuxel's `/lib` or `/usr/lib`.

Do not turn the entire Nuxel rootfs into an Android system.

Use an isolated root/chroot or another proven execution boundary if needed.

Determine whether LHD also requires Android properties, logging, Binder/HIDL services or additional services. Provide only the minimum compatible service infrastructure actually required.

## Phase 4 — Apply proven Samsung blob compatibility fixups where appropriate

Investigate the LineageOS Exynos9820/beyond1lte fixups.

Specifically evaluate:

```text
.remove_needed('libhidltransport.so')
.add_needed('libutils-v32.so')
.binary_regex_replace(
    b'_ZN7android6Thread3runEPKcim',
    b'_ZN7utils326Thread3runEPKcim'
)
```

The exact transformation must be tested against the matching vendor blobs and dependency set.

Do not blindly patch the installed vendor partition in place.

Keep original blobs intact and apply any validated adaptation to a staged Nuxel userspace copy.

Document the source, binary hashes and exact compatibility changes.

## Phase 5 — Start LHD/BBD and prove MCU initialization

Recover the original Android vendor service startup sequence.

Inspect the vendor init scripts and `lhd.conf`.

Determine:

- Exact LHD invocation.
- Arguments.
- Environment.
- Working directory.
- Required privileges.
- Required device nodes.
- Required firmware/patch files.
- Startup ordering.
- Restart behavior.
- Whether a sensor HAL must load `sensors.sensorhub.so`.
- Whether LHD and the sensor HAL are separate processes.
- Which process actually uploads the patch.

Implement an appropriate Nuxel systemd integration.

It must start when required devices and runtime paths are ready.

It must not race the kernel SSP initialization or start repeatedly in an uncontrolled loop.

Prove:

1. LHD starts successfully.
2. Required vendor libraries load.
3. BBD/LHD patch initialization runs.
4. MCU responds.
5. MCU reports ready.
6. Kernel SSP transfers complete without timeout.
7. Sensorhub HAL registers or the correct native interface becomes available.

A running LHD process alone is not success.

## Phase 6 — Native Linux alternative

If the minimal Bionic runtime proves impractical, investigate a native Linux implementation.

Inspect the existing SSP/BBD driver and determine the exact protocol and firmware upload mechanism.

Recover the MCU patch payload and initialization sequence from the matching vendor implementation where legally and technically appropriate.

Investigate:

- Existing firmware payloads.
- Embedded data inside LHD and sensor libraries.
- Driver interfaces.
- SPI protocol.
- MCU command/response format.
- Firmware upload procedure.
- Sensor activation.
- Raw sample extraction.

Implement the narrowest native component necessary.

Do not invent MCU packets or write arbitrary SPI data.

Do not create a competing SPI driver while the existing kernel SSP driver owns the device.

Do not remove or replace the working kernel driver without proof that it is the blocker.

## Phase 7 — Verify real sensor readings

After MCU initialization, enumerate the actual sensor outputs.

Inspect IIO devices, SSP sysfs interfaces and the sensor HAL output.

Identify the real accelerometer stream.

Prove:

- Raw XYZ values are no longer stuck at `0,0,0`.
- Values change when the phone moves.
- Samples are timestamped or have a verifiable update cadence.
- Orientation axes map correctly.
- A flat phone is detected.
- Invalid or stale data is detectable.
- The sensor stream remains alive after suspend/resume and reboot.

Do not inject artificial readings.

Do not use ManualSource for production Auto tests.

## Phase 8 — Connect the sensor stream to Nuxel orientation

Connect the verified sensor source to the existing `nuxel-orientationd` implementation.

Preserve the working fixed modes:

- Locked (PT).
- Locked (LS).
- Locked (RPT).
- Locked (RLS).

Implement or verify:

- Auto (FULL): 0°, 90°, 180°, 270°.
- Auto (PT): 0°, 180°.
- Auto (LS): 90°, 270°.

Use actual gravity-vector data, calibration, stability and hysteresis.

Hold the last good orientation while flat or when readings are invalid.

Do not let Auto PT enter landscape.

Do not let Auto LS enter portrait.

Do not change the display transform mapping that has already passed physical tests.

## Phase 9 — Prove real Auto behavior

Test the phone physically in:

1. Portrait.
2. Landscape.
3. Reverse portrait.
4. Reverse landscape.
5. Flat face-up.
6. Flat face-down, where supported.

Verify:

- Auto FULL follows all four valid orientations.
- Auto PT only uses portrait and reverse portrait.
- Auto LS only uses landscape and reverse landscape.
- Flat orientation retains the last good angle.
- No random transitions occur.
- No fake data is used.
- Display geometry remains correct.
- Touch remains aligned.

Test with real sensor movement and report actual sample values.

## Reflash policy

**Do not start in TWRP. Start in normally booted Nuxel over SSH.**

First complete all userspace, vendor runtime, LHD/BBD and live-kernel diagnostics.

If a kernel or device-tree defect is proven:

- Identify the exact required kernel/DTB modification.
- Preserve the working boot image.
- Prepare a known-good backup.
- Verify the complete boot artifact.
- Then request the owner to enter TWRP over USB for the targeted flash stage.

Do not flash merely because MCU initialization currently fails.

## Mandatory acceptance

- [ ] Existing fixed rotations remain functional.
- [ ] LHD's exact dependency chain is documented.
- [ ] Bionic runtime is compatible with the vendor binaries.
- [ ] Samsung blob compatibility is verified.
- [ ] LHD starts reliably.
- [ ] MCU initializes without SSPBBD timeout.
- [ ] Sensorhub reports ready.
- [ ] Real raw accelerometer readings stream.
- [ ] Values change with physical movement.
- [ ] Auto FULL works.
- [ ] Auto PT works.
- [ ] Auto LS works.
- [ ] Flat and invalid readings retain last good orientation.
- [ ] Suspend/resume preserves sensor operation.
- [ ] Reboot restores sensor service.
- [ ] No simulated sensor data is used.
- [ ] No fixed rotation regression occurs.

## Deliverables

1. Root-cause report.
2. Vendor binary dependency map.
3. Bionic/runtime or native implementation.
4. LHD/BBD service integration.
5. MCU initialization logs.
6. Live sensor data evidence.
7. Auto orientation test matrix.
8. Deployment and rollback instructions.
9. TWRP/kernel flash only if proven necessary.

**Definition of done:** The physical S10+ supplies genuine live sensor data to Nuxel, and Auto modes rotate the real display using that data.
