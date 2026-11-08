# FULL PWNAGE-57000 — Restore Genuine Samsung Sensor-Hub Operation
## BCM47752 MCU initialization, LHD/BBD runtime recovery, Android/Bionic compatibility, native Linux fallback and complete Nuxel Auto-Orientation

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**SoC:** Exynos 9820  
**Sensor hub:** Samsung/Broadcom sensor-hub path involving BCM47752  
**OS:** Fedora-based Nuxel ARM64  
**Known userspace baseline:** Fedora 43 / systemd 258.11 — verify actual running versions  
**Kernel baseline:** Previous downstream Linux 4.14.253 — verify actual source and running build  
**Priority:** Critical  
**Starting state:** Nuxel booted normally with Wi-Fi SSH available  
**TWRP required at start:** NO  
**Kernel flash:** Conditional, only after proof of a kernel/device-tree defect  
**Primary objective:** Real sensor data and fully functional Auto orientation.

---

# 0. Mission

Make Nuxel's three Auto orientation modes genuinely work on the physical S10+.

The display transformation system is already working.

The owner has verified all four fixed rotations physically.

This task is about making the hardware sensor path deliver real readings to the Nuxel orientation daemon.

Do not rewrite the working display rotation stack.

Do not change its transform mapping.

Do not replace the fixed-mode application logic.

Do not fake accelerometer data.

**The objective is to initialize the actual Samsung sensor hub and stream genuine accelerometer readings from the physical phone.**

The current failure is not a generic rotation problem.

It is an MCU/sensor-hub initialization problem.

---

# 1. Verified working display rotation — preserve it

The physical phone has demonstrated all four fixed orientations.

The latest verified table is:

| Mode | Canonical angle | Compositor transform | Logical dimensions |
|---|---:|---|---:|
| Locked (LS) | 90° | `270` | 1520×720 |
| Locked (RLS) | 270° | `90` | 1520×720 |
| Locked (RPT) | 180° | `180` | 360×760 |
| Locked (PT) | 0° | `normal` | 360×760 |

Every tested mode returned:

```text
applied=true
success=true
```

The owner restored Auto (PT) afterward.

These values are real physical-device evidence.

Preserve the exact working mapping.

Do not change it to a theoretically more intuitive transform mapping.

Do not hardcode different geometry without verifying the actual live output.

## 1.1 What already works

- Mode selection.
- Policy handling.
- Fixed angle application.
- Correct compositor transform.
- Correct logical geometry.
- Actual display rotation.
- The daemon's application-result reporting.

The current software defect that previously prevented the daemon from attempting hub initialization has been repaired.

The daemon now attempts the required startup and reports the missing dependency.

Do not undo that work.

## 1.2 What does not work

The automatic orientation source.

The sensor hub is not streaming.

The hardware input path currently returns:

```text
raw_data = 0,0,0
```

No production Auto mode may be reported as working until real live hardware readings exist.

---

# 2. Exact current failure evidence

The physical kernel reports:

```text
[SSPBBD] Sensors of MCU are not ready!

[SSPBBD] bbd_do_transfer(): completion is timeout!

[SSP] MCU device ID = 85, reading ID = -1

[SSP]: initialize_mcu - MCU is not working : 0xffffffff

[SSP] lhd is NULL or resetting
```

The following Samsung vendor components exist on the read-only vendor partition:

```text
/vendor/bin/hw/lhd
/vendor/lib64/sensors.sensorhub.so
```

Also investigate the expected related files:

```text
/vendor/etc/sensor/lhd.conf
/vendor/lib/sensors.sensorhub.so
```

The Nuxel rootfs does not currently provide the Android/Bionic runtime expected by the proprietary vendor binaries.

The expected Android interpreter, likely:

```text
/system/bin/linker64
```

and its required Bionic libraries are not present.

The current diagnosis is that the Android-side LHD/BBD initialization path cannot execute, so the required MCU patch/initialization does not occur.

That is a strong working hypothesis.

It must be verified against the actual binary dependencies and kernel startup path before declaring it the sole root cause.

---

# 3. Technical interpretation of the kernel errors

Interpret the logs separately.

## 3.1 `[SSPBBD] Sensors of MCU are not ready!`

The SSP/BBD driver is reporting that the sensor-hub MCU has not reached the required ready state.

Possible reasons include:

- MCU has not received its patch.
- MCU firmware or patch initialization failed.
- LHD did not run.
- LHD failed to communicate with the kernel driver.
- Sensorhub userspace HAL is missing.
- MCU is resetting.
- SPI communication is unavailable.
- Device-tree GPIO/interrupt/power configuration is wrong.
- The kernel driver is not using the expected protocol.

The log alone does not prove which one applies.

## 3.2 `bbd_do_transfer(): completion is timeout!`

The driver attempted a transfer and did not receive the expected completion.

Investigate:

- Whether the transfer is expected before or after LHD patch loading.
- Whether an MCU-ready signal should have occurred first.
- Whether the SPI transfer itself succeeded.
- Whether the expected completion interrupt is missing.
- Whether MCU reset is asserted.
- Whether the correct SSP driver is active.
- Whether a user-space helper is expected to trigger this stage.

Do not respond by increasing timeouts indefinitely.

Identify what event is not happening.

## 3.3 `MCU device ID = 85, reading ID = -1`

Determine exactly where this value originates in the target kernel source.

Do not assume that 85 is a valid successful MCU identity.

Find the implementation of the device-ID read and identify:

- Actual transaction.
- Expected response.
- Error conversion.
- Meaning of `-1`.
- Whether the read is attempted before firmware initialization.
- Whether the result is expected to change after LHD/BBD patch loading.

Inspect the exact target source.

Do not infer from a similarly named driver on another Samsung device.

## 3.4 `lhd is NULL or resetting`

This is particularly important.

Inspect the exact source producing this message.

Determine:

- What the `lhd` pointer represents.
- Where it is allocated or registered.
- Which component initializes it.
- Whether it is populated by the LHD userspace process.
- Whether it is populated through a kernel registration interface.
- Whether it indicates a userspace daemon is absent.
- Whether a firmware upload or MCU handshake precedes pointer readiness.
- Which operations are blocked while the pointer is null/resetting.

This message may directly connect the missing userspace runtime to the hardware initialization failure.

Prove the relationship from source and runtime evidence.

---

# 4. Important external research lead — Exynos9820/beyond1lte vendor blobs

The existing LineageOS device support for the Samsung Exynos9820/beyond1lte family provides useful evidence.

The public `android_device_samsung_beyond1lte` repository contains an `extract-files.py` implementation with specific sensor-library compatibility fixups.

It applies to:

```text
vendor/lib/sensors.sensorhub.so
vendor/lib64/sensors.sensorhub.so
```

and related sensor libraries.

The observed fixups are:

```python
blob_fixup()
    .remove_needed('libhidltransport.so')
    .add_needed('libutils-v32.so')
    .binary_regex_replace(
        b'_ZN7android6Thread3runEPKcim',
        b'_ZN7utils326Thread3runEPKcim'
    )
```

The repository also lists these vendor files:

```text
vendor/bin/hw/lhd
vendor/etc/sensor/lhd.conf
vendor/lib/sensors.sensorhub.so
vendor/lib64/sensors.sensorhub.so
```

References:

- https://github.com/LineageOS/android_device_samsung_beyond1lte/blob/lineage-23.2/extract-files.py
- https://github.com/LineageOS/android_device_samsung_beyond1lte/blob/lineage-23.2/proprietary-files.txt

This is an important technical lead.

It indicates that the sensorhub binaries have compatibility requirements when used outside their original vendor environment.

It does **not** mean the patch can be blindly applied to Nuxel's binary.

Inspect the exact blob hashes, dependencies, Android vendor version and target runtime first.

If compatible, reproduce the required adaptations in a staged Nuxel implementation while preserving the original vendor files.

---

# 5. Start from the currently booted Nuxel system

**Do not start this task in TWRP.**

The intended starting environment is a normally booted Nuxel system with Wi-Fi SSH access.

The current problem is primarily the absent userspace runtime needed by vendor sensor-hub components.

TWRP is not required to inspect or repair a userspace dependency.

It may become necessary later if the exact kernel source, device tree, driver or boot integration proves defective.

The agent must complete the userspace investigation first.

## 5.1 Initial device verification

Collect:

```bash
uname -a
cat /proc/version
cat /etc/os-release
id
```

Identify:

- Device identity.
- Kernel version.
- Nuxel release.
- Current orientation daemon.
- Current sensor service.
- Current vendor mount.
- Current service manager state.
- Current Wayland session.

Confirm the phone is the expected SM-G975F/beyond2lte.

## 5.2 Preserve the working rotation state

Before changing anything:

- Record current mode.
- Record applied orientation.
- Record working transform mapping.
- Record display geometry.
- Record orientation daemon version.
- Record fixed-mode test logs.

Do not run broad display experiments.

Do not break the four working manual modes.

---

# 6. Forensic inspection of vendor binaries

The first major task is to understand the proprietary binaries.

Do not immediately copy `linker64` and random `.so` files into Nuxel.

Build a dependency map.

## 6.1 Locate exact vendor files

Inspect the read-only vendor partition.

Verify:

```text
/vendor/bin/hw/lhd
/vendor/etc/sensor/lhd.conf
/vendor/lib64/sensors.sensorhub.so
/vendor/lib/sensors.sensorhub.so
```

Identify all related sensor firmware, configuration and supporting libraries.

Do not assume `/vendor/etc/sensor/lhd.conf` exists merely because it is listed in a community manifest. Verify the file on this exact phone.

## 6.2 Identify exact vendor firmware

Determine:

- Stock vendor build fingerprint.
- Firmware/build number.
- Android version.
- Security patch level.
- Vendor partition version.
- Device model.
- ABI.
- Blob hashes.
- Origin of vendor image.
- Compatibility of each binary with the running hardware.

Do not use arbitrary blobs from another Exynos device.

Prefer the vendor files already present on the physical S10+.

If additional vendor files are needed, extract them from the exact matching SM-G975F firmware package or known-good vendor image.

## 6.3 ELF inspection

For `lhd` and the sensorhub libraries inspect:

- ELF class.
- ELF architecture.
- ELF machine.
- `PT_INTERP`.
- `DT_NEEDED`.
- SONAME.
- RPATH/RUNPATH.
- Undefined symbols.
- Symbol versions.
- Exported symbols.
- GNU hash/symbol table.
- Android-specific dependencies.
- Embedded firmware/patch content.

Use appropriate ELF tooling:

- `readelf`.
- `llvm-readelf`.
- `objdump`.
- `nm`.
- `strings`.
- `xxd` or equivalent binary inspection.

Do not use host `ldd` on Android/Bionic binaries as proof of their runtime dependencies.

Build a complete dependency tree.

Identify missing dependencies by exact filename and ABI.

## 6.4 Identify embedded firmware and patch data

Inspect the LHD executable and sensorhub libraries for:

- Firmware images.
- BBD payloads.
- Patch tables.
- MCU command sequences.
- Version strings.
- Device IDs.
- Expected firmware revision.
- Patch checksums.
- Resource loading.
- Named firmware paths.
- System property dependencies.
- Device-node paths.
- Sysfs paths.

Determine whether the MCU patch is:

- Embedded inside `lhd`.
- Embedded inside `sensors.sensorhub.so`.
- Loaded from an external file.
- Built into a shared component.
- Generated dynamically.
- Received from a vendor service.

Do not guess.

---

# 7. Determine the actual LHD/sensor HAL launch architecture

The files in `/vendor/bin/hw` and `/vendor/lib64` are not necessarily independent executables.

Investigate the real Android startup arrangement.

## 7.1 Recover vendor init configuration

Inspect the matching vendor firmware for:

- `init*.rc`.
- Sensor-related service declarations.
- `lhd.conf`.
- Device permissions.
- SELinux service/domain declarations.
- HAL service registration.
- Startup ordering.
- Firmware paths.
- System properties.
- Service restart policies.

Search for:

- `lhd`
- `sensorhub`
- `sensors`
- `ssp`
- `bbd`
- `MCU`
- `BCM47752`

Determine whether Android starts `lhd` directly, whether the sensor HAL starts it, or whether a separate manager is involved.

## 7.2 Determine who loads `sensors.sensorhub.so`

Establish whether the library is loaded by:

- A Sensors HAL implementation.
- A vendor HAL service.
- LHD itself.
- Another Samsung hardware service.
- A proprietary initialization manager.

Find the precise entry point and registration mechanism.

Do not start the shared object directly as if it were an executable.

## 7.3 Recover the dependency chain

Produce a service graph, for example:

```text
Nuxel systemd
      |
      v
Android compatibility runtime
      |
      +--> LHD executable
      |
      +--> required vendor libraries
      |
      +--> required sensor HAL loader/service
      |
      v
SSP/BBD kernel interface
      |
      v
BCM47752 MCU initialization
      |
      v
Sensor stream
```

This diagram is conceptual.

Replace it with the actual verified process/service relationships.

---

# 8. Preferred implementation: minimal isolated Android/Bionic runtime

The first preferred route is to run the exact Samsung userspace components with their required Android runtime without turning Nuxel into a full Android system.

## 8.1 Why an isolated runtime is necessary

Android vendor binaries are built against Bionic and Android's system libraries.

They are not ordinary glibc Linux executables.

The Nuxel rootfs currently does not contain the required Android dynamic linker and Bionic dependency closure.

Do not expect:

```bash
LD_LIBRARY_PATH=/vendor/lib64
```

to make an Android executable run correctly under glibc.

It will not replace the Android dynamic linker or Bionic ABI.

## 8.2 Runtime location

Use a dedicated path such as:

```text
/opt/nuxel/android-compat/
```

or another appropriate Nuxel-managed runtime location.

Do not replace the Nuxel system libc.

Do not overwrite the host's `/lib` or `/usr/lib`.

Do not change the host's normal ELF interpreter.

Do not turn `/system` into an incomplete, globally visible Android filesystem.

## 8.3 Exact matching Bionic runtime

Acquire the required runtime from a compatible Android build.

Prefer the exact stock firmware version associated with the existing vendor binaries.

Inspect:

- `linker64`.
- `libc.so`.
- `libm.so`.
- `libdl.so`.
- `liblog.so`.
- `libbase.so`.
- `libutils.so`.
- `libcutils.so`.
- `libbinder.so`.
- `libhidlbase.so`.
- `libhidltransport.so`, if actually needed.
- `libhardware.so`.
- Any VNDK/VNDK-SP libraries required by the binaries.
- Additional vendor libraries identified by ELF dependency analysis.

Do not copy all libraries from an arbitrary Android ROM.

Do not assume the same Android release is appropriate without identifying the vendor blob's API and dependencies.

## 8.4 Android linker namespace configuration

Android's dynamic linker uses namespace isolation and configuration, not just a list of shared-library search paths.

Inspect the appropriate matching configuration:

```text
/system/etc/ld.config.txt
```

or the generated:

```text
/linkerconfig/ld.config.txt
```

depending on the Android version.

AOSP references:

- https://source.android.com/docs/core/architecture/vndk/linker-namespace
- https://android.googlesource.com/platform/bionic/+/refs/heads/android14-mainline-permission-release/linker/ld.config.format.md

Determine which linker namespace the vendor executable uses and which system/vendor libraries it can access.

Implement the smallest compatible namespace configuration.

Do not globally disable linker isolation just to get one binary to load.

## 8.5 Isolated execution environment

Use a controlled execution environment.

A chroot or other appropriate isolated runtime may be suitable, depending on the actual LHD dependencies.

Ensure access to only the required host resources:

- SSP/BBD device nodes.
- Required sysfs paths.
- Required `/proc` and `/sys` information.
- Required firmware paths.
- Necessary runtime sockets.
- Required device events.
- Required configuration.

The process must not accidentally see or control unrelated host devices.

If a Binder/HIDL service is required, determine whether it can operate with a minimal standalone compatibility service or requires a larger Android service stack.

Do not launch the entire Android init system inside Nuxel.

Do not run a competing Android framework.

Do not start conflicting Binder, property or logging services without understanding their interaction with Nuxel.

## 8.6 Android properties and logging

Investigate dependencies on:

- Android system properties.
- Vendor properties.
- Property service.
- Android logging (`liblog`).
- Binder.
- HIDL.
- Hardware service manager.
- Runtime config.
- Device service registration.

If LHD needs property reads, implement a minimal compatible property source or a narrow compatibility shim.

If it needs Binder/HIDL service activation, determine the smallest required service dependency.

Do not add a complete Android framework just to satisfy a single property or library dependency.

## 8.7 Runtime acceptance

The runtime is not complete merely because:

```bash
/path/to/linker64 /vendor/bin/hw/lhd
```

does not immediately produce an ELF error.

The real acceptance condition is:

- LHD executes.
- Required vendor libraries load.
- Required interfaces register.
- Device access works.
- MCU patch initialization completes.
- Kernel driver reports readiness.
- Sensor readings start streaming.

---

# 9. Samsung proprietary sensor library compatibility

The LineageOS fixups are a strong lead and must be examined carefully.

## 9.1 Verify the blob hashes

Compare the actual on-device files with:

- Matching stock firmware copies.
- Current LineageOS proprietary-file expectations.
- Any available extracted vendor packages.

Record hashes.

Do not modify the original files on the read-only vendor partition.

## 9.2 Inspect the exact fixups

Evaluate:

```text
.remove_needed('libhidltransport.so')
.add_needed('libutils-v32.so')
.binary_regex_replace(
    b'_ZN7android6Thread3runEPKcim',
    b'_ZN7utils326Thread3runEPKcim'
)
```

Determine why each change is required and whether the matching Nuxel runtime needs it.

The replacement implies an ABI compatibility adjustment involving the Android Thread implementation.

It is not a universal fix.

Test the result against the actual `libutils-v32.so` implementation and expected symbol signatures.

## 9.3 Version compatibility

Check:

- Android framework version.
- Vendor API level.
- VNDK version.
- Bionic version.
- C++ runtime.
- HIDL version.
- Symbol availability.
- ABI compatibility.
- Vendor namespace configuration.

If a proprietary blob requires a different Android symbol implementation, select or build the correct compatibility library.

Do not patch ELF dependencies blindly.

## 9.4 32-bit and 64-bit libraries

Inspect both:

```text
/vendor/lib/sensors.sensorhub.so
/vendor/lib64/sensors.sensorhub.so
```

Determine which one the actual LHD/hal path uses.

Preserve matching ABI dependencies.

Do not mix 32-bit and 64-bit objects.

Only install the required ABI set.

---

# 10. Alternative implementation: native Linux LHD/BBD support

Do not stop if the Android runtime proves impractical.

The second implementation route is a native Nuxel/Linux solution that performs the necessary sensor-hub initialization and MCU patch upload without requiring the Android runtime.

The agent must investigate this seriously.

## 10.1 Inspect the existing SSP/BBD driver

Find the exact source that emits:

```text
Sensors of MCU are not ready
bbd_do_transfer()
MCU device ID
lhd is NULL or resetting
```

Inspect:

- BBD code.
- SSP code.
- MCU initialization.
- Firmware loading.
- Device registration.
- Sysfs interfaces.
- IOCTL interfaces.
- SPI communication.
- GPIO/IRQ handling.
- Reset sequencing.
- LHD registration.
- Sensor data paths.

Identify what userspace interface the kernel expects.

Do not assume the kernel driver expects an ordinary firmware file at `/lib/firmware`.

## 10.2 Native loader possibility

If the current driver exposes a documented or recoverable interface for MCU patch upload, implement a native loader.

The implementation should:

- Use the exact supported kernel interface.
- Validate the patch header.
- Validate size.
- Validate checksum/version where available.
- Perform the expected initialization sequence.
- Handle timeouts and retries safely.
- Verify MCU readiness.
- Report precise failures.
- Avoid writing arbitrary SPI packets.

If the kernel currently requires an `lhd` registration operation rather than only a firmware upload, implement that documented interaction through the correct interface.

## 10.3 Protocol recovery

If the protocol is not documented:

- Inspect the existing vendor binary.
- Inspect kernel calls and structures.
- Inspect available debug output.
- Inspect firmware data.
- Compare working Android service initialization logs.
- Recover exact packet framing.
- Recover the required request/response sequence.
- Determine checksums and version validation.
- Determine reset/retry behavior.

Do not invent undocumented packets.

Do not send experimental commands that could leave the MCU in an unknown state.

Use a controlled sequence and preserve the ability to reset/reinitialize safely.

## 10.4 Do not create a competing SPI driver

The existing SSP driver owns the sensor hub communication path.

Do not:

- Bind a second driver to the same SPI device.
- Open the same SPI controller behind the kernel driver's back.
- Toggle SSP GPIOs from a separate service.
- Compete with the kernel driver for IRQs.
- Bypass the driver without a verified architecture.

A native userspace loader should use the actual kernel-provided interface.

If the correct interface does not exist, the kernel interface may need a small supported extension, which should be a separate controlled kernel patch.

---

# 11. Kernel and device-tree investigation

The current evidence points primarily to userspace initialization, but kernel/device-tree correctness must be verified.

Do not assume that all failures are solved by Bionic.

## 11.1 Kernel source

Inspect the exact running source/build.

Search for:

- `SSPBBD`.
- `bbd_do_transfer`.
- `lhd`.
- MCU device ID.
- `initialize_mcu`.
- `SENSORS_SSP`.
- `SENSORS_SSP_BBD`.
- Sensorhub firmware handling.
- SSP SPI driver.
- Sensor IRQ handling.

Find the exact configuration symbols in the actual kernel.

Do not enable Kconfig options from unrelated Samsung devices without verifying compatibility.

## 11.2 Device tree

Inspect the active S10+ device tree for:

- SSP SPI instance.
- Sensor hub SPI frequency.
- SPI mode.
- MCU reset GPIO.
- MCU request GPIO.
- MCU response GPIO.
- Sensor hub interrupt.
- Pinctrl.
- Pull-ups/pull-downs.
- Voltage regulators.
- Wake signals.
- Device enable state.
- MCU power sequencing.

Compare against the exact known-good S10+ stock device tree and an appropriate Exynos9820 reference.

Do not substitute an Exynos9825 tree or another Samsung device tree without checking the hardware differences.

## 11.3 Live driver state

During testing inspect:

- SPI devices.
- Bound driver.
- IRQ count.
- GPIO state where safely exposed.
- Regulator state.
- Device-tree properties.
- MCU reset status.
- Kernel messages.
- Sensor interfaces.
- Firmware request events.

Determine whether the hardware is correctly powered and physically communicating.

A driver reporting a transfer timeout may indicate an absent MCU patch, but it may also reveal a communication or reset issue.

Do not treat the Bionic diagnosis as proven until these possibilities are checked.

---

# 12. Startup orchestration and reliability

Once the LHD/BBD path works manually, integrate it into Nuxel.

Do not build a new competing orientation service.

Use the existing orientation service architecture.

## 12.1 Service responsibilities

Create or repair the minimal required sensor-hub initialization service.

Potential responsibilities:

- Prepare the isolated Android runtime.
- Check required device nodes.
- Start LHD or native loader.
- Perform MCU initialization.
- Verify MCU readiness.
- Verify the sensor HAL/stream.
- Report health to Nuxel.
- Restart/recover when safe.
- Provide logs.

Do not make the service responsible for deciding which display orientation to apply.

That remains `nuxel-orientationd`'s responsibility.

## 12.2 Systemd ordering

Use the actual available devices and runtime dependencies.

Ensure the service starts after:

- Vendor partition is mounted.
- Required device nodes exist.
- Kernel SSP driver is registered.
- Required runtime files are accessible.
- Any prerequisite device services are ready.

Do not start before required components exist.

Do not create an infinite restart loop if the MCU is not responding.

Use bounded retries, meaningful delays and explicit degraded status.

## 12.3 Recovery after failure

If LHD or the native loader exits:

- Record exit reason.
- Determine whether the MCU is still ready.
- Retry only the required initialization.
- Do not repeatedly reset a healthy MCU.
- Avoid repeated firmware uploads.
- Preserve current readings while they remain valid.
- Report degraded status accurately.

## 12.4 Suspend/resume

The phone must retain sensor functionality after:

- Display off.
- Screen lock.
- Suspend.
- Resume.
- Long idle.
- Wi-Fi/SSH disconnect.
- Desktop session restart.

Determine whether the sensor hub remains powered or needs reinitialization after resume.

The orientation daemon must detect stale readings and recover appropriately.

---

# 13. Expose genuine sensor readings

The hub must produce actual data.

Do not count an initialized MCU as a working accelerometer.

## 13.1 Discover all sensor interfaces

Inspect:

```text
/sys/bus/iio/devices/
/sys/class/sensors/
/sys/devices/
/dev/
```

Also inspect any Samsung-specific SSP sensor sysfs paths.

Determine which interfaces expose:

- Accelerometer XYZ.
- Gyroscope XYZ.
- Magnetometer.
- Sampling frequency.
- Timestamp.
- Sensor availability.
- Calibration.
- Batch/wakeup state.

## 13.2 Verify live changes

Collect raw values while the physical phone is held in:

1. Normal portrait.
2. Landscape.
3. Reverse portrait.
4. Reverse landscape.
5. Flat face-up.
6. Flat face-down where supported.

Values must change with physical movement.

Collect a sample history with timestamps.

Record:

- Sample count.
- Frequency.
- Minimum.
- Maximum.
- Mean.
- Stability.
- Missing/stale intervals.
- Raw XYZ.
- Sensor identity.
- Active source.

The previous zero stream must be replaced by actual nonzero readings during physical movement.

## 13.3 Sensor identification

Do not assume the sensor axes are aligned to the screen.

Identify:

- Accelerometer orientation.
- Physical mounting matrix.
- Axis swaps.
- Sign inversions.
- Sensor bias.
- Calibration.
- Device-specific rotation.

Determine the mapping empirically and compare with the matching Samsung vendor implementation where available.

Document it.

## 13.4 Data freshness

The orientation service must know when the sensor has stopped streaming.

Use timestamps or reliable update monitoring.

Report:

- Connected.
- Initialized.
- Streaming.
- Stale.
- Unavailable.
- Recovering.

These are different states.

Do not report `sensor_available=true` merely because the sensor device node exists.

---

# 14. Integrate sensor data into Nuxel orientation

The orientation daemon already has a sensor abstraction and policy logic.

Use that implementation.

Inspect:

```text
services/nuxel-orientation/nuxel_orientation/sensors.py
services/nuxel-orientation/nuxel_orientation/policy.py
services/nuxel-orientation/nuxel_orientation/apply.py
services/nuxel-orientation/nuxel-orientationd
services/nuxel-orientation/systemd/nuxel-orientationd.service
```

Verify current exact paths in the repository.

Do not build another separate orientation daemon.

## 14.1 Sensor source

Implement the actual production sensor source.

It may consume:

- Verified IIO readings.
- Verified Samsung SSP sensor interface.
- A verified sensor HAL adapter.
- A native BBD/LHD data bridge.

Prefer a clean Nuxel sensor adapter with a stable interface.

For example, it may publish:

```json
{
  "source": "samsung-ssp-bcm47752",
  "status": "streaming",
  "accelerometer": {
    "x": 0.12,
    "y": -9.78,
    "z": 0.35
  },
  "timestamp": "runtime-generated timestamp"
}
```

This is a schema example only.

The values must be read from the physical sensor.

## 14.2 Policy modes

Preserve all seven modes:

| User-facing mode | Stable key | Allowed orientations |
|---|---|---|
| Auto (FULL) | `auto` | 0°, 90°, 180°, 270° |
| Auto (PT) | `auto-portrait` | 0°, 180° |
| Auto (LS) | `auto-landscape` | 90°, 270° |
| Locked (PT) | `portrait` | 0° |
| Locked (LS) | `landscape` | 90° |
| Locked (RPT) | `reverse-portrait` | 180° |
| Locked (RLS) | `reverse-landscape` | 270° |

Do not alter stable keys.

Do not change the fixed-mode functionality.

## 14.3 Orientation algorithm

Use the verified accelerometer gravity vector.

Implement:

- Axis calibration.
- Device mounting correction.
- Angle classification.
- Angular hysteresis.
- Stable sample count.
- Debounce.
- Transition cooldown.
- Flat-device detection.
- Invalid sample detection.
- Last-good orientation.
- Stale sensor handling.

Do not rotate on one noisy sample.

Do not rotate while flat.

Retain the last good orientation during invalid or missing readings.

## 14.4 Auto PT

Auto PT may select:

- 0°.
- 180°.

It must never select:

- 90°.
- 270°.

## 14.5 Auto LS

Auto LS may select:

- 90°.
- 270°.

It must never select:

- 0°.
- 180°.

## 14.6 Auto FULL

Auto FULL may select any of the four orientations.

Do not force reverse orientations unless real physical movement indicates them.

## 14.7 Locked modes

Locked modes must ignore sensor events completely.

The sensor service may continue streaming for other applications, but it must not change a Locked display orientation.

---

# 15. Calibration and physical orientation acceptance

A live sensor stream is not enough.

The mapping must be correct.

## 15.1 Calibration

Use real physical measurements.

Collect samples in all four orientations and determine the gravity-vector mapping.

Account for the phone's actual sensor mounting.

Avoid assuming standard portrait axes.

Persist only a verified calibration matrix or mapping.

Do not invent sensor calibration constants.

## 15.2 Test orientation transitions

Run physical transition sequences:

```text
Portrait → Landscape
Landscape → Reverse portrait
Reverse portrait → Reverse landscape
Reverse landscape → Portrait
```

Also test:

```text
Portrait → Flat → Landscape
Landscape → Flat → Portrait
```

The orientation should remain stable while flat and change when a new stable pose is reached.

## 15.3 Latency

Measure:

- Sensor update delay.
- Stability/debounce delay.
- Orientation decision delay.
- Display-application delay.
- End-to-end time from physical movement to final display.

The previous owner tests used a 300–800 ms settling window as an initial reference.

Tune based on real sensor sample stability and avoid jitter.

---

# 16. Preserve the working display and touch stack

Do not treat this as a display rotation rewrite.

The existing fixed-mode results are the reference.

After the sensor stream becomes active, use the existing apply path.

Verify all four transforms again:

| Angle | Expected transform |
|---:|---|
| 0° | `normal` |
| 90° | `270` |
| 180° | `180` |
| 270° | `90` |

Only if physical tests show the existing mapping has changed should it be revised.

Keep geometry correct:

- Portrait logical: 360×760.
- Landscape logical: 1520×720.

These are the currently reported values, not a licence to hardcode them into a new driver.

Discover actual active output geometry.

Verify:

- Physical display.
- Touchscreen alignment.
- Dock.
- Navigation.
- Status bar.
- OSK.
- Application windows.
- Quick Settings.
- Remote desktop, if active.

Do not apply CSS rotation.

Do not rotate the framebuffer a second time.

Do not introduce another `/dev/fb0` writer.

---

# 17. Orientation daemon health and honest status

The current software change correctly makes the daemon attempt hub startup and report the missing dependency.

Preserve that.

Expose clear health states.

Recommended diagnostic concepts:

| State | Meaning |
|---|---|
| `not-probed` | Sensor stack has not been checked |
| `runtime-missing` | Required Android/Bionic dependency unavailable |
| `loader-starting` | LHD/native loader starting |
| `loader-failed` | LHD/native loader could not start |
| `mcu-initializing` | Patch/MCU initialization in progress |
| `mcu-not-ready` | MCU has not acknowledged readiness |
| `sensor-hal-ready` | Required sensor interface registered |
| `streaming` | Genuine samples are arriving |
| `stale` | Stream stopped updating |
| `degraded` | Sensor subsystem partly functional |
| `unavailable` | No valid hardware input |

Do not report Auto as working unless the sensor stream is actually alive.

## 17.1 Diagnostic command

Provide a useful diagnostic interface through the existing daemon.

For example:

```bash
nuxel-orientationd status
```

It should report:

- Selected policy.
- Effective angle.
- Sensor source.
- LHD runtime status.
- LHD PID and service state.
- Required libraries.
- MCU readiness.
- SSP/BBD transfer state.
- Sensor HAL state.
- Raw accelerometer values.
- Sample timestamp.
- Sample rate.
- Data age.
- Calibration.
- Last error.
- Last recovery attempt.
- Display apply status.

Use actual live data.

Do not expose secrets.

## 17.2 Structured logs

Provide meaningful logs such as:

```text
orientation: fixed display path verified
sensorhub: vendor build identified
sensorhub: lhd dependency inspection complete
sensorhub: Bionic runtime available
sensorhub: lhd started
sensorhub: sensor HAL registered
sensorhub: MCU patch initialization requested
sensorhub: MCU ready
sensorhub: SSP/BBD transfers completing
sensorhub: accelerometer stream active
sensorhub: first valid sample received
orientation: production sensor source streaming
```

Only emit success after each corresponding action is verified.

Failure examples:

```text
sensorhub: LHD cannot load required library
sensorhub: unresolved symbol
sensorhub: MCU transfer timed out
sensorhub: MCU still resetting
sensorhub: sensor data stale
orientation: Auto unavailable; fixed orientations remain operational
```

---

# 18. Deployment plan

## Phase A — Investigation in normal Nuxel

Start with Nuxel booted and SSH available.

Perform:

- Kernel/source audit.
- Device-tree audit.
- Vendor file discovery.
- ELF dependency mapping.
- Android/Bionic runtime investigation.
- LHD startup discovery.
- Sensor HAL loading investigation.
- Live kernel and hardware diagnostics.

No TWRP required.

## Phase B — Userspace implementation

Implement the isolated Bionic runtime or native loader.

Use safe staging.

Preserve original vendor files.

Create the appropriate service and sensor adapter.

Deploy over Wi-Fi SSH using the established Nuxel deployment method.

Test without kernel changes.

If successful, no TWRP flash is needed.

## Phase C — Conditional kernel/device-tree work

Only proceed if evidence proves a missing or incorrect kernel component.

Possible causes:

- Wrong SSP driver configuration.
- Wrong sensor hub device-tree properties.
- Missing required GPIO/IRQ configuration.
- Incorrect reset/power sequence.
- Missing BBD kernel interface.
- Wrong driver protocol.
- Missing required kernel firmware interface.

Before kernel deployment:

1. Document the exact required source change.
2. Identify the current known-good kernel artifact.
3. Back up the existing boot target.
4. Verify the correct device/partition.
5. Verify the new boot image format.
6. Verify DTB/ramdisk integration.
7. Prepare a tested rollback path.

Only then request TWRP.

## Phase D — TWRP agreement if required

If a kernel/DTB flash is proven necessary, the owner will place the phone in TWRP recovery with USB connected for the targeted flash phase.

The owner authorizes a verified, limited kernel/DTB deployment within this task's scope.

The agent must:

- Detect TWRP over ADB.
- Verify SM-G975F/beyond2lte.
- Identify the exact target.
- Back up the current kernel-containing image off-device.
- Hash the backup.
- Preserve TWRP.
- Flash only the verified authorized image/target.
- Verify the write.
- Reboot into Nuxel.
- Verify the sensor driver and Auto path.

Do not overwrite recovery, bootloader, modem, EFS or userdata.

Do not factory-reset or format partitions.

If the device bootloops or hangs, return to TWRP, preserve logs and restore the known-good image.

Do not repeatedly flash unverified builds.

---

# 19. Test plan

## 19.1 Runtime

- [ ] Exact vendor build identified.
- [ ] LHD binary dependencies resolved.
- [ ] Sensorhub library dependencies resolved.
- [ ] Correct Bionic runtime selected.
- [ ] Linker namespace behavior understood.
- [ ] Required Android properties/services provided where necessary.
- [ ] LHD launches.
- [ ] LHD remains stable.
- [ ] No host glibc conflict.
- [ ] No vendor file modification required.

## 19.2 MCU

- [ ] MCU patch load attempted.
- [ ] MCU readiness acknowledged.
- [ ] `bbd_do_transfer()` completes without repeated timeout.
- [ ] `MCU device ID` read returns expected value.
- [ ] LHD is no longer null/resetting.
- [ ] SSP driver reports ready.
- [ ] Firmware/patch version validated where available.

## 19.3 Sensors

- [ ] Sensor HAL/driver registered.
- [ ] IIO or verified sensor interface appears.
- [ ] Accelerometer raw values are nonzero when physically moved.
- [ ] Values change with rotation.
- [ ] Timestamp/sample cadence verified.
- [ ] No stale samples.
- [ ] Flat-device behavior verified.
- [ ] Axis mapping calibrated.

## 19.4 Auto

- [ ] Auto FULL follows all four orientations.
- [ ] Auto PT follows only 0° and 180°.
- [ ] Auto LS follows only 90° and 270°.
- [ ] Flat phone holds last orientation.
- [ ] No jitter.
- [ ] No random transitions.
- [ ] Locked modes ignore sensors.
- [ ] Reboot restores Auto policy and sensor startup.

## 19.5 Reliability

- [ ] LHD starts on boot.
- [ ] MCU initializes after boot.
- [ ] Sensor stream recovers after suspend/resume.
- [ ] Stream loss is detected.
- [ ] Service recovery is bounded and safe.
- [ ] SSH disconnect does not affect sensors.
- [ ] Fixed modes still work.
- [ ] No framebuffer or touch regression.

---

# 20. Required deliverables

1. **Root-cause report**
   - Why the MCU is not ready.
   - Whether LHD is absent, unable to execute, unable to load libraries or unable to communicate.
   - Whether kernel/device-tree changes are required.

2. **Vendor compatibility map**
   - Actual vendor build.
   - LHD ELF dependencies.
   - Sensor HAL ELF dependencies.
   - Bionic version.
   - Required libraries.
   - Required Android services.
   - Exact blob compatibility patches.

3. **Working sensor-hub integration**
   - Isolated Android/Bionic runtime or native Linux implementation.
   - Correct LHD/BBD execution.
   - Systemd service.
   - Startup ordering.
   - Recovery behavior.

4. **Hardware evidence**
   - MCU ready output.
   - Successful SSP/BBD communications.
   - Live raw sensor values.
   - Physical movement correlation.

5. **Orientation evidence**
   - Auto FULL.
   - Auto PT.
   - Auto LS.
   - All fixed modes preserved.
   - Flat/stale handling.
   - Reboot and resume.

6. **Deployment**
   - SSH deployment if userspace-only.
   - TWRP flash record if kernel changes were proven necessary.
   - Backup and rollback instructions.

7. **Documentation**
   - Sensor architecture.
   - Vendor runtime requirements.
   - Build integration.
   - Service configuration.
   - Diagnostics.
   - Known limitations.

---

# 21. Stop conditions and recovery

Stop before a kernel flash if:

- Exact kernel source is unknown.
- Device-tree target is uncertain.
- Current boot image is not backed up.
- Target partition is ambiguous.
- TWRP is not responsive.
- Proposed artifact has not been validated.

Stop vendor runtime integration if:

- Bionic version is incompatible.
- Binary dependency closure is incomplete.
- Required libraries are from an unrelated Android release.
- Runtime would overwrite Nuxel's glibc libraries.
- Required service architecture is unknown.
- The process would need unrestricted access to the host.

Do not stop the project merely because the first compatibility attempt fails.

Use the native Linux route if the proprietary runtime approach proves incompatible.

Do not fake successful Auto behavior.

---

# 22. Final definition of done

PWNAGE-57000 is complete only when:

- Fixed display rotations continue working.
- The actual Samsung LHD/BBD initialization path is restored or replaced by a validated native implementation.
- The MCU reports ready.
- Kernel SSP/BBD communication completes.
- Real accelerometer values stream.
- Nuxel consumes those physical values.
- Auto FULL works.
- Auto PT works.
- Auto LS works.
- Flat and invalid sensor states retain the last good orientation.
- Sensor operation survives reboot and suspend/resume.
- The physical touchscreen remains aligned.
- No fake readings or manual test injection are involved.
- The existing Nuxel kernel/display stack remains stable.

---

# 23. Final instruction to the implementation agent

The phone already knows how to rotate.

We have proved that the four manual display transforms work on the physical S10+.

Do not waste time rewriting them.

The missing piece is the real sensor-hub initialization and data path.

Start with Nuxel running and SSH available.

Inspect the existing Samsung vendor LHD executable, sensorhub library, matching firmware and Android/Bionic dependencies.

Investigate the Exynos9820/beyond1lte community compatibility fixups.

Build a minimal, isolated Android compatibility runtime if that is the cleanest route.

If that cannot work reliably, implement the native Linux BBD/LHD initialization path using the actual kernel interface and recovered vendor protocol.

Prove that the MCU accepts its patch, becomes ready and streams real accelerometer data.

Connect those readings to the already-working Nuxel orientation daemon.

Only request TWRP if a proven kernel or device-tree defect makes a flash necessary.

**Do not mark Auto successful until the physical phone has been moved through real orientations and Nuxel has automatically followed them using genuine hardware readings.**
