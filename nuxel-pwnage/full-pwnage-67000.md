# FULL-PWNAGE-67000 — Nuxel S10+ Gyroscope / Accelerometer / Automatic Screen Rotation

**Mission class:** hardware bring-up + userspace sensor integration + orientation policy completion  
**Primary device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**Primary outcome:** make real, physical-motion-driven automatic screen rotation work reliably on Nuxel, using the existing Samsung/Broadcom sensor-hub path and the already-working Phoc/output/touch rotation pipeline.  
**Execution rule:** investigate the exact supplied repository and target image first. Modify the real implementation, build it, run tests, produce a deployable patch and a rollback procedure. Do not stop after writing another investigation report.

---

## 0. Mission statement and non-negotiable truths

Nuxel already has a substantial orientation implementation. This is **not** a request to create a new orientation manager or replace the compositor path. The fixed/manual display-rotation path is implemented and was physically validated on the S10+. The policy engine, seven named modes, daemon, compositor transform read-back, presenter coordination, touch-coordinate mapping, persistence, Quick Settings, and Settings UI already exist.

The remaining primary blocker is the **live sensor-hub data path**. The S10+ contains a Broadcom BCM47752 sensor-hub MCU connected to an STMicroelectronics LSM6DSO accelerometer/gyroscope. The kernel exposes Samsung sensor-hub controls and sensor class nodes, but the accelerometer's `raw_data` was still `0,0,0` in the latest evidence included in the repository. The kernel logs show the sensor hub is down and its MCU/BBD initialization is failing. The previous investigation found vendor-side `lhd` components on the read-only Android vendor partition, but the compatible Android/Bionic runtime expected by those components is absent from the Nuxel system root (`/system/bin/linker64` was missing in the recorded image).

The objective is to fix that boundary in a controlled, maintainable way so Nuxel can obtain genuine sensor samples and use them to drive the existing automatic orientation policy.

### Mandatory distinctions

1. **Accelerometer vs gyroscope:** standard auto-rotation is primarily derived from the accelerometer's gravity vector. It does not require gyroscope angular-rate data. The LSM6DSO is a six-axis IMU, so gyro data may improve motion responsiveness or support future fusion, but do not block basic auto-rotation on gyro enablement if real accelerometer gravity samples work. Do not call accelerometer-derived rotation “gyro working” unless gyro measurements are also independently verified.
2. **Detected vs streaming:** an IIO device, sysfs node, IRQ, sensor class entry, or `/dev` node does not prove that the MCU has booted or is delivering changing, physically meaningful samples.
3. **Manual rotation vs Auto:** fixed 0/90/180/270-degree modes already work. Do not break them while fixing Auto. A requested Auto mode must remain visibly degraded/blocked until a verified live sensor source exists.
4. **Real data vs test fixtures:** synthetic values are allowed in unit tests only. They must never be reported by runtime diagnostics as hardware availability, must never make Auto green, and must never reach the compositor in production.
5. **Vendor payloads and licenses:** do not copy proprietary firmware or Android vendor libraries into the Git repository, release image, or generated source archive unless the owner has supplied them and the license/provenance permits redistribution. Prefer using the owner’s mounted read-only vendor partition or a lawful native implementation. Do not invent firmware, patch bytes, chip IDs, protocol commands, or sensor enable bits.
6. **No kernel migration:** the immediate task is the current S10+ kernel/userspace boundary. Do not migrate kernels, replace the working S10+ kernel, flash partitions, alter boot chains, or modify the bootloader as a shortcut. A narrowly-scoped kernel patch is a separate escalation and requires evidence that userspace cannot solve the issue.
7. **Single orientation owner:** `nuxel-orientationd` remains the single authority for mode selection, sensor policy, transform application, rollback, and status. Do not add a second daemon that competes for display rotation.
8. **One display transform and one touch transform:** preserve the established Phoc → libinput-shim → framebuffer-presenter responsibilities. Never rotate pixels twice or touch coordinates twice.

---

## 1. Repository baseline: what exists and what is already working

Before editing, read the actual source tree, including:

- `PWNAGE-54000-REPORT.md`
- `docs/beta-finalization/live/PWNAGE-54000-REPORT.md`
- `docs/a69/ROTATION-HARDWARE-BOUNDARY.md`
- `docs/A49/OWNER-TEST-ORIENTATION.md`
- `docs/a53/ORIENTATION-FIVE-MODE-IMPLEMENTATION.md`
- `docs/a54-reliability/ORIENTATION-MATRIX.md`
- `configs/nuxel/orientation/README.md`
- `configs/nuxel/orientation/orientation.json`
- `configs/nuxel/orientation/orientation.schema.json`
- `configs/nuxel/sensors/README.md` and `sensors.json`
- every file under `services/nuxel-orientation/`
- `services/nuxel-orientation/systemd/nuxel-orientationd.service`
- `services/nuxel-bridge/src/bridge.py` and its orientation/sensor command routes
- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-apps/settings/settings.js`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `tests/pwnage46000/`, `tests/pwnage54000/`, and all orientation-service tests
- the captured evidence under `docs/beta-finalization/live/evidence/pwnage-46000/` and `pwnage-54000/`.

Do not trust a historical report over the currently-built code. Compare reports to the exact files installed in the current image and verify live paths on the phone.

### 1.1 Proven display/rotation architecture

The successful local display path is:

```text
Quick Settings / Settings / nuxelctl
              |
              v
       nuxel-orientationd       (single policy + transaction owner)
              |
              v
         wlr-randr
              |
              v
       Phoc HEADLESS-1           (actual logical output transform)
              |
              +---- libnuxel-libinput-path.so
              |       (exactly one touch calibration matrix)
              |
              v
        screencopy frame
              |
              v
          nuxel-wl-fb            (sole /dev/fb0 writer; no second rotation)
              |
              v
          S10+ AMOLED
```

The known transform mapping in the shipped S10+ configuration is intentionally non-obvious:

| Canonical physical pose | Degrees | `wlr-randr` transform | Portrait scanout logical geometry |
|---|---:|---|---:|
| Portrait | 0 | `normal` | 360×760 at scale 2 |
| Landscape | 90 | `270` | 1520×720 at scale 1 |
| Reverse portrait | 180 | `180` | 360×760 at scale 2 |
| Reverse landscape | 270 | `90` | 1520×720 at scale 1 |

Preserve the existing transform map unless fresh live measurements prove it changed. The selected output is discovered at runtime (`HEADLESS-1` appeared in the evidence); do not hardcode that output name.

The panel is physically portrait (1440×3040 scanout). The framebuffer presenter remains the only `/dev/fb0` owner. The screencopy path is already transformed by Phoc; presenter compensation is `none` in the current verified configuration. The touch input path has a separate, single calibration-matrix owner in `libnuxel-libinput-path.so`; `nuxel-wl-fb` must not rotate touch.

The previous live report recorded strong framebuffer-vs-Phoc image correlation across all four fixed poses. The compositor transform, geometry read-back, fixed-mode persistence, and basic touch-matrix math have already been implemented. Do not regress those results.

### 1.2 Seven orientation modes already implemented

Keep exactly these seven policy modes and labels unless the owner explicitly changes the product requirement:

| Policy key | Label | Allowed effective angles |
|---|---|---|
| `auto` | Auto (FULL) | 0, 90, 180, 270 |
| `auto-portrait` | Auto (PT) | 0, 180 |
| `auto-landscape` | Auto (LS) | 90, 270 |
| `portrait` | Locked (PT) | 0 |
| `landscape` | Locked (LS) | 90 |
| `reverse-portrait` | Locked (RPT) | 180 |
| `reverse-landscape` | Locked (RLS) | 270 |

The `orientation.json` default is currently safe portrait. Quick Settings short tap and long-press behavior, seven choices, Settings choices, degraded Auto styling, and persistent selection already exist. Maintain compatibility aliases in `policy.py` and `nuxelctl`/Bridge routes.

### 1.3 Current sensor-hub facts recorded in the repository

The latest captured investigation establishes:

- Sensor-hub MCU: **Broadcom BCM47752KUB1G**, DT compatible `ssp,BCM4773`.
- Physical inertial sensor behind it: **STMicroelectronics LSM6DSO** (accelerometer + gyroscope).
- Samsung's `/sys/class/sensors/` includes `accelerometer_sensor`, `gyro_sensor`, `rotation_vector_sensor`, `magnetic_sensor`, `barometer_sensor`, and other sensor classes.
- The actual accelerometer node used by the daemon is `/sys/class/sensors/accelerometer_sensor/raw_data`.
- The sensor-hub accelerometer enable mask is `/sys/class/sensors/ssp_sensor/enable`; accelerometer bit 0 is currently configured as `1`.
- MCU power state is exposed at `/sys/class/sec/sensorhub/mcu_power`.
- BBD control endpoint: `/dev/bbd_control`; the service currently writes `ESW:READY` when starting the hub.
- The recorded IIO inventory showed devices such as `iio:device1` named `accelerometer_sensor` and `iio:device14` named `rotation_vector_sensor`, but the devices had no readable `in_accel_x_raw`, `in_accel_y_raw`, `in_accel_z_raw`, or scale attributes. The captured IIO scan elements were timestamp-only. Device numbers can change between boots; never hardcode an `iio:deviceN` index.
- `/sys/class/sensors/accelerometer_sensor/raw_data` was still `0,0,0` in the captured baseline.
- Kernel evidence included `[SSPBBD]: ssp_down == true`, SSP command failures around `0xd1/0xd2`, BBD transfer timeouts, MCU ID/read failures, and a message equivalent to `lhd is NULL or resetting`.
- The mounted read-only vendor side was found to contain `/vendor/bin/hw/lhd` and `/vendor/lib64/sensors.sensorhub.so` on the live Android-derived device. The Nuxel system root in that evidence did not contain `/system/bin/linker64`, and the Android/Bionic runtime was incomplete.
- The source tree/archive does not contain `lhd`, `linker64`, `libsensorhub`, or a verified BCM47752 patch payload. Do not pretend those are in the repository.

The sensor hub controller already attempts real kernel setup and checks real samples. It deliberately avoids doomed control writes when `lhd` or the Android linker is missing. The current implementation correctly refuses to fabricate samples, but it does not yet provide a working compatible runtime or native replacement for the vendor LHD/SSP patch-loading path.

### 1.4 Existing code that must be understood before changing

`services/nuxel-orientation/nuxel_orientation/sensors.py` currently contains:

- `IIOAccelSource` for genuine IIO sysfs channels with a valid scale.
- `SysfsAccelSource` reading the Samsung sensor-hub `raw_data` node.
- `SensorProxySource` as a D-Bus fallback when a real `iio-sensor-proxy` reports an accelerometer.
- `SensorHubControl`, including BBD wake, sensor-enable-bit handling, retry throttle, status and real-sample verification.
- `probe_sources`, `sensor_reading`, and helper functions used by `nuxel-orientationd`.

The `SysfsAccelSource` currently normalizes a nonzero raw sensor vector to 1 g because the Samsung factory node's raw LSB scale is not exposed. That preserves direction but does not prove factory calibration or bias correctness. The mount matrix and gravity references are explicitly marked unverified in the current configuration. This mission must calibrate and validate them on the actual handset before marking them verified.

`services/nuxel-orientation/nuxel_orientation/policy.py` contains the pure orientation/hysteresis state machine. `nuxel-orientationd` owns persistence, auto supervision, applying transforms, commit/rollback and diagnostics. `apply.py` uses `wlr-randr` discovery/read-back and verifies logical geometry. Preserve this structure.

---

## 2. Target deliverable and definition of done

The mission is complete only when all of the following are achieved and supported by evidence:

1. Nuxel identifies the real S10+ sensor stack and distinguishes hardware presence, MCU readiness, streaming, valid samples and calibrated orientation separately.
2. The sensor hub can be initialized from Nuxel without a manual Android boot or ad-hoc terminal command, using a documented and legally usable method.
3. The accelerometer produces real samples which change predictably when the physical phone is rotated. These samples have valid timestamps, stable magnitude/direction, and no fabricated or stale-data interpretation.
4. A physically calibrated sensor-to-display mount matrix maps the actual hardware axes into the canonical Nuxel display axes.
5. `Auto (FULL)`, `Auto (PT)` and `Auto (LS)` reliably drive the already-working rotation pipeline within a sensible settle window (target 300–800 ms after a deliberate pose change), with hysteresis/debounce and no visible flapping.
6. Fixed/manual modes remain fully functional without any sensor service.
7. Flat-face-up/face-down, movement, weak gravity, pocket/occlusion and transient sensor loss preserve the last good legal orientation rather than jumping randomly.
8. Touch input remains aligned after every automatic transform. One and only one transform is applied to visual output and one and only one matching mapping is applied to touch.
9. The UI truthfully distinguishes `selected mode`, `effective angle`, `sensor streaming`, `calibration verified`, and `compositor applied`. No green Auto state before hardware proof.
10. Sensor power is managed sanely. Fixed modes must not needlessly hold the sensor hub awake; Auto enables only the required sensors and shuts down or releases them safely when no longer required, preserving other sensor consumers.
11. Service restart, suspend/resume if supported, screen off/on, and reboot do not leave the MCU stuck, enable bits corrupted, or the orientation daemon fighting itself.
12. Automated tests pass, physical tests are recorded, packaging/build checks pass, and a complete Wi-Fi SSH deployment plus rollback procedure is provided.

**If the actual LHD/firmware boundary cannot be completed with available owner-approved artifacts, do not claim success.** Finish all safe software hardening and diagnostics, report the exact missing artifact/ABI/protocol, keep Auto honestly blocked, and provide the precise next owner action. Partial completion is preferable to false success or a broken sensor hub.

---

## 3. Phase 0 — Freeze the baseline and make a factual inventory

Before modifying anything:

1. Record repository commit, dirty tree, target image version, kernel release, build date and target codename. Confirm the image is for `beyond2lte` / SM-G975F / Exynos 9820.
2. Read the source files listed in §1.1–1.4 in full. Trace the path from Quick Settings and Settings through Bridge, daemon, sensor source, policy, `apply.py`, Phoc, touch shim and framebuffer presenter.
3. Run the current tests before editing:
   - `pytest -q services/nuxel-orientation/tests`
   - `pytest -q tests/pwnage46000 tests/pwnage54000`
   - `node --check pwa/nuxel-home/js/qs.js`
   - `node --check pwa/nuxel-apps/settings/settings.js`
   - `nuxel-orientationd selftest` on device when available.
4. Save exact baseline JSON from `nuxel-orientationd status --json`, `sensor --json`, `modes`, plus `/run/nuxel-orientation/input.json`, `/run/nuxel-touch-calibration.state`, `/run/nuxel-wl-fb-orientation`, and relevant service status/logs.
5. Capture current `dmesg` / `journalctl` messages filtered for `SSP|BBD|BCM|LSM6|sensorhub|sensor`. Capture the relevant live sysfs inventory and read-only IIO device inventory.
6. Record which controls are currently enabled before touching `/sys/class/sensors/ssp_sensor/enable`. Preserve the existing bitmask in every operation; never overwrite unrelated proximity, gyro, magnetic, light or other sensor bits.
7. Confirm manual fixed orientations apply successfully before and after any changes. If they do not, stop and fix/record that pre-existing issue separately; do not attribute it to accelerometer work.

Create a baseline evidence directory under a versioned path such as `docs/pwnage-67000/evidence/baseline/`. Keep raw outputs, timestamps, commands and hashes. Do not overwrite older A49/PWNAGE-46000/PWNAGE-54000 evidence.

---

## 4. Phase 1 — Characterize actual sensor nodes and the sensor-hub ABI

### 4.1 Discover dynamically; never assume device indices

On the actual phone, enumerate:

- `/sys/bus/iio/devices/iio:device*/name`
- each device's `uevent`, `of_node`, `scan_elements`, `buffer`, `in_*_raw`, `in_*_scale`, `in_*_offset`, sampling frequency, poll delay and buffer controls
- `/sys/class/sensors/*/{name,vendor,raw_data,enable,calibration,calibration_info,frequency,poll_delay}` where present
- `/sys/class/sensors/ssp_sensor/*`
- `/sys/class/sec/sensorhub/*`
- `/dev/bbd_*`, `/dev/ssp*`, `/dev/input/event*` only where they are actually present and identified
- device-tree compatible strings for the BCM47752 and LSM6DSO path
- active kernel modules, built-in driver configuration, SPI controller/child device binding, IRQs and regulator/power dependencies.

Read the nodes first. Do not start arbitrary daemons, reset the MCU, change IIO buffer controls, or write calibration values while collecting the initial baseline.

For each sensor endpoint record:

| Field | Required evidence |
|---|---|
| Sensor identity | stable name, vendor, DT node, compatible string |
| Driver binding | sysfs driver symlink, module/built-in state |
| Interface | IIO, input event, Samsung sysfs, BBD char device, or other |
| Channels | actual readable channels and units, not inferred from name |
| Scale/offset | actual exported values or explicit unknown |
| Event rate | timestamps and real rate while moving |
| Power state | runtime PM and MCU state |
| Enable control | exact mask semantics and preservation rules |
| Data liveness | changing values tied to physical movement |
| Failure | exact errno/log/result and stage |

### 4.2 Verify that the exposed “gyro” is real

The current orientation algorithm should use the accelerometer gravity vector. Separately inspect `gyro_sensor` and any rotation-vector/quaternion endpoint.

- Locate the actual gyro data node and its units (`mdps`, `mrad/s`, `rad/s`, degrees/s, raw counts, or vendor-specific). Do not assume the scale.
- Identify the exact Samsung SSP sensor bit or request ID for gyro by reading matching kernel driver source/device tables or verified vendor code. Do not guess the enable bit based on bit ordering.
- Only enable the gyro after proving the accelerometer startup path and only when required by the chosen implementation.
- Test that gyro values change during angular motion, settle to approximately zero when stationary, and return to a documented scale/range.
- Do not confuse an IIO device named `gyro_sensor` or an IRQ with streaming gyro samples.

If the gyro path is not yet functional but accelerometer gravity works, deliver reliable Auto rotation first and report gyro as a separate remaining capability. Do not block Auto rotation on optional gyro fusion.

### 4.3 Validate sensor orientation semantics

Capture raw samples in at least six physical placements:

1. normal upright portrait;
2. upside-down portrait;
3. left-side landscape;
4. right-side landscape;
5. face-up flat;
6. face-down flat.

Also capture smooth rotations between the four useful orientations, with each sample timestamped. Record exact phone pose and direction. Repeat each pose several times after allowing the device to settle. Identify sensor bias, axis polarity, units, offset and whether the raw node is already calibrated.

The mount matrix and gravity references in the current JSON are explicitly unverified. Do not simply flip signs until the UI appears to rotate. Derive the transform mathematically from the measured vectors and verify it with a second independent run.

---

## 5. Phase 2 — Resolve the BCM47752 BBD/LHD startup blocker

This is the main technical workstream. The repository evidence strongly suggests that the hardware sensor is present but the sensor-hub MCU is not running because its BBD/LHD firmware patch handshake is missing or unable to start.

### 5.1 Establish exact vendor runtime requirements

The latest recorded live-device probe found vendor components at paths similar to:

- `/vendor/bin/hw/lhd` (or `/vendor/bin/lhd`)
- `/vendor/lib64/sensors.sensorhub.so`
- possibly other vendor libraries and firmware files which must be enumerated rather than assumed.

The historical Nuxel userspace lacked `/system/bin/linker64` and the required Android/Bionic environment. The current `SensorHubControl.status()` checks for `lhd` and linker presence; `ensure_streaming()` intentionally returns without writing BBD/enable controls when either is missing.

Do a full ABI/dependency inventory of the actual mounted vendor files:

1. Verify vendor partition mount point, filesystem, read-only status, SELinux context if applicable, ABI and architecture.
2. Compute SHA-256 of each referenced executable/library/firmware file and record its origin (device partition, owner-supplied artifact or repository file).
3. Inspect ELF headers, dynamic interpreter, DT_NEEDED entries, symbol versions, SONAMEs, relocations, and all required libraries. Prefer `readelf`/`file`/`objdump` and safe static inspection. Do not blindly execute a proprietary binary to discover dependencies.
4. Identify whether `lhd` is a standalone daemon, a helper, or a service launched by another vendor process. Determine required arguments, environment, Android properties, binder/HIDL dependencies, sockets, permissions, device nodes and expected lifecycle.
5. Verify whether `sensors.sensorhub.so` is actually loaded by `lhd` or a separate sensor HAL and whether additional `libutils`, `liblog`, `libcutils`, `libhardware`, `libbase`, `libbinder`, `libhidl*`, `libc++`, or vendor libraries are required. Do not assume a library based on its name; confirm dependencies.
6. Identify the exact BBD patch-loading mechanism and whether patch bytes are embedded in the vendor ELF/shared object or loaded from a separate file. Verify this from static evidence and safe runtime logs. Do not scrape arbitrary `strings` output and call it a valid patch.
7. Determine whether the MCU firmware upload is volatile (RAM patch per boot) or persistent. Do not perform any persistent firmware write.
8. Confirm compatibility with the current S10+ downstream kernel ABI and device tree. A vendor binary from another Samsung model/firmware revision is not interchangeable merely because the chipset name matches.

### 5.2 Choose one supported runtime strategy

Evaluate these options in order and document the decision:

**Option A — Minimal isolated Android/Bionic compatibility runtime (preferred only if dependencies are fully understood and owner-approved).**

- Provide the minimum Android linker/runtime dependencies required by the exact vendor `lhd` build.
- Use exact matching vendor/system libraries from the same installed firmware build, with hashes and source provenance.
- Keep all Android/Bionic paths isolated under a dedicated directory or mount namespace. Do not replace glibc, `/lib64`, `/usr/lib64`, global `PATH`, or global `LD_LIBRARY_PATH`.
- Do not symlink Bionic `libc.so` over glibc or expose incompatible Android libraries to general Fedora/Nuxel processes.
- Do not bundle copyrighted Android binaries/libraries into the public source repo or release artifacts without explicit owner authorization and a redistribution right. The phone's read-only vendor partition may be referenced in place when legally and technically valid.
- Run the vendor service under a dedicated systemd unit with a documented environment, controlled device access, bounded restart policy, startup timeout, logs, and stop behavior.
- Prove it does not start a whole Android framework stack or require booting Android. If binder/property/HIDL dependencies imply a large hidden Android runtime, stop and reassess instead of silently importing Android init/services.

**Option B — Native Linux BBD/SSP loader or protocol reimplementation.**

- Locate matching open-source Samsung SSP/BBD protocol code and the exact kernel implementation in use. Public upstream references can assist discovery, but they are not proof of compatibility with the S10+ downstream 4.14 kernel/vendor MCU firmware.
- Inspect the actual kernel driver's expected ioctls, write formats, completion semantics, firmware naming, reset state machine, chip-ID checks and timeout behavior.
- Reimplement only protocol elements supported by evidence and allowed by license. Preserve all kernel ABI semantics.
- Provide a small native service/library with explicit state machine, robust timeouts and detailed logs. Do not reverse-engineer by random writes to `/dev/bbd_control` or repeated MCU resets.
- Use the exact patch payload from the owner-provided firmware only when lawful and matching. Validate checksums and protocol version before transfer.

**Option C — Keep Auto safely blocked with exact actionable diagnostic.**

If neither A nor B can be completed with existing artifacts, finish the diagnostic and service hardening, preserve fixed rotations, and produce an owner action list naming the exact missing binary, dependency, ABI, license permission or test evidence. This is an acceptable honest partial result; claiming Auto is fixed is not.

### 5.3 Runtime safety constraints

- Never flash boot, recovery, vendor, modem, EFS, or persist partitions.
- Never write raw bytes to SPI, `/dev/bbd_control`, sensorhub char devices, or MCU memory without a verified protocol implementation and a bounded test.
- Never loop resets or firmware attempts in the background. Use at most one controlled attempt at startup and a conservative retry backoff.
- Save the prior sensor enable mask and power state. Preserve every existing sensor bit. Restore only bits/power references owned by this service.
- Avoid resetting the entire sensor hub if other services depend on proximity, light, magnetometer, barometer or biometric sensors.
- If an MCU reset is unavoidable, require an explicit owner-approved diagnostic mode, stop competing sensor clients, set a timeout, capture before/after state, and restore prior state.
- If the vendor binary is not compatible with the current userspace or kernel, do not force it with fake symlinks, fake linker names, or wrong libraries.
- No device data should be fabricated to satisfy the daemon's `raw_live` check.

### 5.4 Prove that the sensor hub has booted

The runtime must establish more than process existence. Required evidence:

1. The LHD/native provider process is alive and not stuck in an uninterruptible sleep.
2. BBD/SSP handshake returns the expected success state.
3. Kernel log no longer reports `ssp_down`, `MCU is not working`, invalid ID, repeated command `0xd1/d2` failures, or BBD transfer timeouts during normal startup.
4. MCU state/power node is coherent.
5. The accelerometer enable bit is set without clobbering other bits.
6. `raw_data` becomes nonzero and changes when the phone is physically moved.
7. Samples continue at a known rate over at least 60 seconds and recover after service restart.
8. After Auto is disabled, the service releases only the sensors it enabled and does not break other sensor classes.

`raw_data` simply changing once is not enough. Reject stale/repeated, frozen, malformed, NaN, infinite, implausible, or zero vectors.

---

## 6. Phase 3 — Make sensor control and sample decoding robust

### 6.1 Refactor the current `SensorHubControl` carefully

Keep the existing public interface compatibility unless tests prove a safe change. Improve the implementation so status can separately report:

- physical controller present;
- kernel driver bound;
- vendor provider found;
- runtime dependencies complete;
- provider process state;
- BBD transport initialized;
- MCU powered/ready;
- accelerometer enabled;
- gyro enabled (separate flag);
- actual stream active;
- sample age and rate;
- last error/stage;
- calibration status.

Current `status()` reports `lhd_present`, `android_linker_present`, `raw_live`, `streaming`, and a single textual `reason`. Extend compatibly instead of changing field meanings in a way that breaks Settings or Bridge consumers.

The existing startup path writes `ESW:READY` and ORs accelerometer bit 0 into `/sys/class/sensors/ssp_sensor/enable`. Preserve other bits. Before any control write, read and record the complete current mask. When releasing the service's sensor lease, clear only the bit it owns and only if no other client/lease requires it. Never blindly write `0`.

Implement an explicit, tested state machine such as:

```text
UNPROBED
  -> HARDWARE_PRESENT
  -> PROVIDER_DEPENDENCIES_CHECKED
  -> PROVIDER_STARTING
  -> BBD_HANDSHAKE
  -> MCU_READY
  -> ACCEL_ENABLED
  -> STREAM_VALIDATING
  -> STREAMING
  -> CALIBRATED
  -> AUTO_READY
```

Any failure must record the stage and exact reason, e.g. `missing_android_linker`, `vendor_abi_mismatch`, `provider_start_failed`, `bbd_timeout`, `mcu_id_mismatch`, `accelerometer_enable_failed`, `zero_samples`, `stale_samples`, `unstable_magnitude`, `mount_matrix_unverified`, or `touch_transform_unverified`.

### 6.2 IIO probing must not falsely select an unusable stub

The recorded IIO devices expose incomplete timestamp-only scan elements and no readable accelerometer scale. Do not let `IIOAccelSource` select the first device whose *name* matches and then block all other sources.

- Enumerate all devices dynamically.
- Inspect available channels and scale/offset before declaring a source usable.
- If there are separate accel, gyro and rotation-vector devices, identify them by actual channel metadata, not index.
- A timestamp-only IIO device is `detected_but_not_readable`, not `available` and not `auto_capable`.
- If Samsung raw_data becomes live, use that genuine production source even if the normal IIO vector channels remain absent.
- A D-Bus `iio-sensor-proxy` result is eligible only when the service reports `HasAccelerometer=true` and returns a fresh, changing orientation. Do not install it merely to hide the real blocked source.

### 6.3 Sample validation, bias, scaling and calibration

The current raw-data path normalizes nonzero LSB values to one standard gravity. This is only direction normalization; it must not be represented as factory-scale calibration.

Implement:

- strict parse for documented delimiter/format;
- reject NaN/Inf and excessively large values;
- a conservative minimum magnitude threshold determined from real stationary/moving samples, not guessed;
- a configurable maximum magnitude range where the raw units support it;
- freshness check using sample timestamps or measured change/read cadence;
- stale sample detection (same raw sample for too long while the phone is moving);
- median/low-pass filter adequate to suppress vibration without excessive lag;
- magnitude-based flat/weak-gravity handling;
- optional bias/offset correction only from recorded calibration and a documented method;
- explicit unit metadata in diagnostics.

Do not infer SI units unless the interface exposes scale. Do not hardcode 9.80665 as a claim about raw sensor units; normalization to a direction vector may use it internally for policy thresholds, with the fact that the raw units are unknown clearly represented.

### 6.4 Mount matrix and gravity reference calibration

The current identity matrix is only a placeholder. Derive a 3×3 matrix from real measurements so the sensor-space vector maps to the display-native axes. Use at least the six poses in §4.3 and repeatability checks.

- Document axis convention: display-native `x=right`, `y=up`, `z=out of screen` (or update this convention consistently).
- Verify matrix orthogonality and determinant near ±1; reject singular/invalid matrices.
- Determine whether a simple signed axis permutation is sufficient. Avoid arbitrary shearing/scale in the orientation mount transform.
- Verify upright portrait, upside-down, left-side and right-side classifications from a separate capture set.
- Verify face-up/face-down do not accidentally trigger rotation; they should hold the last good orientation.
- Only change `calibration_status` to `verified` after a physical owner test and recorded evidence.
- Include a diagnostic/calibration command that displays raw vector, corrected vector, magnitude, classified angle, matrix and confidence without automatically rotating until the user explicitly enables calibration test mode.

Do not silently overwrite an owner's verified calibration when upgrading configuration. Version and migrate calibration data; preserve backups.

---

## 7. Phase 4 — Finish the automatic-orientation policy using genuine samples

The policy engine already has hysteresis and a 100 ms configured sample interval, with a 450 ms hysteresis window, 250 ms cooldown, 60 ms debounce, flat-gravity handling and `last_good_on_flat=true`. Audit the current values against real data and tune only from measured behaviour.

### 7.1 Classification

Convert the calibrated gravity vector to one of the four canonical angles. Use angular thresholds with hysteresis rather than exact equality. Make thresholds configurable and testable. Preserve legal mode sets:

- `auto`: all four orientations;
- `auto-portrait`: only 0° and 180°;
- `auto-landscape`: only 90° and 270°.

When the sample is between quadrants or confidence is low, retain last good angle. When the phone is flat, retain last good angle. Do not rotate on a noisy sample or a single spike.

### 7.2 Rotation transaction

Keep the established transaction contract:

1. Sensor samples request a new canonical angle.
2. Policy validates allowed angle and cooldown/hysteresis.
3. The daemon applies the existing compositor transform.
4. `apply.py` reads the actual output transform and logical geometry back.
5. Touch shim state is updated from the verified transform exactly once.
6. Presenter state is published with no additional visual rotation.
7. Only after read-back succeeds is the effective angle committed as last-good.
8. On failure, retain or restore the previous verified orientation and expose the exact error.

Do not commit an effective angle merely because `wlr-randr` returned exit code zero. Require the existing read-back contract.

### 7.3 Optional gyro-assisted filtering (only after accel Auto works)

If—and only if—the LSM6DSO gyro stream is independently verified with correct units and timestamps, evaluate a complementary filter or bounded motion predictor to reduce perceived lag during fast rotation. Keep the accelerometer as the absolute gravity reference. The gyro is a short-term angular-rate signal and drifts when integrated; never use gyro integration alone as the persistent orientation truth.

- Add an explicit feature flag defaulting off until calibrated.
- Validate correct axis alignment, sign, scale, timestamps, drift and temperature effects.
- Fall back immediately to accelerometer-only when gyro samples disappear or fail validation.
- Never let gyro fusion make an unverified sensor source `auto_capable`.
- Compare rotation latency, overshoot, oscillation and power draw with and without fusion. Retain fusion only if it materially improves the real phone experience.

---

## 8. Phase 5 — Sensor service lifecycle, power, permissions and reliability

### 8.1 Service ownership

`nuxel-orientationd` is the policy authority. A helper process may load or host the vendor/native sensor-hub provider, but it must be a clearly documented dependency, not a second rotation daemon.

Prefer a dedicated `nuxel-sensorhub` provider unit (or an equivalently well-scoped helper) if the vendor runtime needs a persistent process. It must:

- start only when a real sensor consumer needs it, unless boot-time readiness is proven necessary;
- use a bounded startup timeout;
- be idempotent (repeated requests do not duplicate processes or handshake loops);
- expose health through a local, permission-controlled IPC/API or status file;
- restart only on known recoverable failures with exponential/backoff limits;
- stop cleanly and release owned sensor bits;
- not block system boot indefinitely;
- not hold the display rotation daemon in an uninterruptible wait;
- not consume high CPU while idle.

If the vendor binary must run under Android/Bionic, isolate it in its own runtime and environment as defined in §5.2. Keep the Nuxel Python daemon and all GTK/PWA apps on the normal system C library.

### 8.2 Power leases and bitmask correctness

Implement a single ownership model for sensor-hub enable bits:

- request accelerometer lease when any Auto mode is selected;
- optionally request gyro lease only when gyro-assisted filtering is enabled;
- preserve existing active sensor bits;
- track which bits Nuxel itself enabled;
- release only Nuxel-owned bits when no consumer remains;
- do not power-cycle the MCU if other sensor services hold a lease;
- respect kernel runtime PM and vendor provider ownership;
- record power state before and after each transition.

Do not turn off proximity, light, magnetometer, barometer, biometric or other consumers by writing an assumed zero mask.

### 8.3 Permissions and hardening

- The system sensor provider runs with only the privileges required by actual device-node ownership.
- Keep `/dev/bbd_control` and `/sys/class/sensors/ssp_sensor/enable` protected from normal app users.
- Expose a narrow privileged service API; do not give PWA/GTK processes direct root/sysfs access.
- Add udev rules only for real stable device identifiers, with explicit group and mode. Avoid broad `MODE=0666`.
- Keep vendor partition read-only.
- Ensure service logs do not flood journals or leak sensitive owner/device details unnecessarily.
- Verify systemd sandboxing matches actual device and mount needs; do not weaken hardening globally just to make LHD start.

### 8.4 Suspend/resume and screen lifecycle

Test and handle:

- screen off while Auto is selected;
- screen on and wake;
- suspend/resume if Nuxel's current kernel supports it reliably;
- orientation daemon restart;
- provider crash/restart;
- Wi-Fi/USB deployment while sensor service is active;
- switch from Auto to Locked and back;
- phone boot directly into Auto mode.

No reset loops, no permanent high-rate polling, no stale cached orientation presented as a live sensor update.

---

## 9. Phase 6 — Settings, Quick Settings and truthful diagnostics

Keep the existing seven-mode UI, labels and interaction model. Improve the state display so the owner can diagnose hardware without a terminal.

Settings → Display → Screen Rotation should show:

- selected policy mode;
- current effective orientation;
- sensor hardware detected;
- sensor hub/provider state;
- accelerometer streaming state;
- gyro state separately (if implemented);
- calibration state and last calibration date/version;
- sample rate and sample age;
- compositor transform/read-back state;
- touch matrix/read-back status;
- exact blocked reason and a one-tap diagnostic export.

Quick Settings must:

- preserve existing short-tap and long-press choices;
- mark Auto degraded/amber when the sensor hub is unavailable, not green;
- show a clear reason such as “Sensor hub firmware/runtime missing” rather than simply “Auto”; 
- reflect asynchronous state changes without optimistic UI success;
- never claim the phone rotated because a policy value was saved if the compositor was not applied.

Bridge/API must continue to distinguish `mode`, `effective_orientation`, `sensor.available`, `sensor.auto_capable`, `auto_state`, `compositor.applied`, `display_verified`, and `touch.verified`. Keep JSON shape backward-compatible; add fields rather than removing fields used by QS/Settings.

The diagnostic command should produce a structured report similar to:

```json
{
  "hardware": {"soc": "Exynos 9820", "sensor_hub": "BCM47752", "imu": "LSM6DSO"},
  "provider": {"present": true, "runtime_ready": false, "process_active": false},
  "hub": {"mcu_ready": false, "bbd_ready": false, "power": "unknown", "enable_mask": null},
  "accelerometer": {"detected": true, "streaming": false, "sample_age_ms": null, "source": null},
  "gyroscope": {"detected": true, "streaming": false, "units": "unknown"},
  "calibration": {"mount_matrix": "unverified", "gravity_reference": "unverified"},
  "auto": {"available": false, "state": "blocked_sensor_unavailable", "reason": "..."},
  "display": {"mode": "portrait", "effective_degrees": 0, "verified": true}
}
```

The exact schema may differ; it must accurately report discovered values. This sample is a schema illustration, not values to hardcode.

---

## 10. Phase 7 — Automated test requirements

Build tests around the actual current modules. Do not rely only on source-string assertions; write behaviour tests with temporary filesystem roots, injected process runners and deterministic sample streams.

### 10.1 Sensor discovery and source selection

Test:

- missing IIO sysfs directory;
- several dynamically numbered IIO devices;
- accelerometer name with no raw channels;
- timestamp-only scan elements;
- valid raw channels with real scale;
- missing/invalid scale;
- gyro-only endpoint not mistaken for accelerometer;
- Samsung sensor class present with zero raw data;
- Samsung sensor raw data live and changing;
- malformed/short/NaN/Inf/stale samples;
- D-Bus SensorProxy absent, unavailable, false `HasAccelerometer`, undefined orientation, and fresh valid orientation;
- manual source never marked auto-capable.

### 10.2 Hub control

Use temporary fake sysfs/dev trees and injected provider implementations to test:

- no hardware node;
- no `lhd` binary;
- missing Android linker;
- incomplete dependencies;
- provider launch error and timeout;
- BBD endpoint missing/unwritable;
- `ESW:READY` request made once and bounded;
- current enable mask preserved;
- accelerometer bit enabled only when allowed;
- existing unrelated bits preserved;
- no write when `auto_start=false`;
- existing valid stream not reset;
- MCU handshake timeout;
- zero and stale samples;
- successful live sample stream;
- retry throttle/backoff;
- provider crash/restart;
- ownership release only clears bits owned by this service;
- no concurrent duplicate provider or race between two callers.

### 10.3 Mount matrix and policy

Test all six static poses and transitions between every quadrant. Test:

- all four discrete angles;
- all three Auto policies' allowed sets;
- flat phone holds last good;
- weak gravity holds last good;
- noise near quadrant boundary does not flap;
- brief spikes are ignored;
- sustained pose changes cross hysteresis;
- cooldown prevents rapid toggling;
- stale data causes Auto to degrade safely;
- switching Auto → Locked releases lease;
- switching Locked → Auto requests lease;
- loss of stream during Auto preserves last verified angle;
- recovery from stream loss resumes only after validation window.

Synthetic data is acceptable inside these tests, but all fake streams must be clearly test-only. Add an explicit assertion that no fixture or manual provider is marked as a production hardware source.

### 10.4 Display/touch integration

Retain and extend existing tests:

- `wlr-randr` output is dynamically discovered;
- mapping remains 0→normal, 90→270, 180→180, 270→90;
- portrait scale 2 and landscape scale 1 geometry are verified;
- Phoc output read-back must match requested transform;
- framebuffer presenter stays sole `/dev/fb0` owner;
- `screencopy_already_transformed` continues to prevent double rotation;
- libinput matrix matches the effective transform exactly once;
- failed compositor apply rolls back or retains previous good mode;
- orientation sequence increments once per real successful transition;
- QS and Settings labels/modes are unchanged;
- blocked Auto remains amber/degraded and manual modes remain green/working.

### 10.5 Service and packaging

- daemon `selftest` passes;
- service unit starts with systemd sandboxing intact;
- provider startup is bounded and does not block boot;
- build script installs all source/config/service files and correct ownership/permissions;
- no proprietary binaries accidentally enter source package or RPM/rootfs staging unless explicitly approved;
- fresh image contains correct default orientation configuration and unit enablement;
- package uninstall/rollback leaves manual rotation usable.

---

## 11. Phase 8 — Physical S10+ validation plan

The agent must distinguish automated tests from physical tests. An SSH agent cannot prove glass-side movement or touch accuracy; mark owner-only tests honestly.

### 11.1 Before testing Auto

On the phone, capture:

```sh
/usr/libexec/nuxel/nuxel-orientationd status --json
/usr/libexec/nuxel/nuxel-orientationd sensor --json
/usr/libexec/nuxel/nuxel-orientationd modes
cat /sys/class/sensors/accelerometer_sensor/raw_data
cat /sys/class/sensors/ssp_sensor/enable
cat /sys/class/sec/sensorhub/mcu_power
cat /run/nuxel-orientation/input.json
cat /run/nuxel-touch-calibration.state
journalctl -u nuxel-orientationd -b --no-pager
journalctl -u nuxel-sensorhub -b --no-pager  # if a separate provider unit is created
sudo dmesg | grep -Ei 'SSP|BBD|BCM|LSM6|sensorhub|sensor'
```

Use actual installed command names if they differ; do not fake missing commands.

### 11.2 Sample capture

Create a bounded tool such as `nuxel-orientationd calibrate --capture 10 --json` or extend `nuxel-sensors-diag.sh` to capture:

- monotonic timestamp;
- raw accel x/y/z;
- corrected vector;
- magnitude;
- raw gyro x/y/z and units if available;
- sample freshness and rate;
- current classified angle/confidence;
- current display mode/transform.

The tool must stop on timeout and must not rotate the screen unless an explicit `--apply` or calibration-test option is supplied.

### 11.3 Physical orientation test matrix

With Auto (FULL) selected and phone unlocked:

| Physical pose | Expected effective mode |
|---|---|
| Upright portrait | 0° / portrait |
| Rotate 90° left | 90° / landscape |
| Rotate 180° | 180° / reverse portrait |
| Rotate 270° | 270° / reverse landscape |
| Return upright | 0° / portrait |
| Lay flat face-up | hold last good |
| Lay flat face-down | hold last good |

Repeat the cycle at least five times. Record timestamps and measured transition latency. Target 300–800 ms after a stable deliberate pose, without flapping. Some slower deliberate movements may take longer; report measured values rather than claiming a target was met.

Then validate:

- Auto (PT) never enters landscape;
- Auto (LS) never enters portrait;
- fixed portrait/landscape/reverse modes still work even if provider is stopped;
- touching all four corners, status bar, dock, OSK, browser controls and Settings controls after each rotation hits the expected visual control;
- lockscreen behavior remains as defined by existing product policy. The current owner test says keep lockscreen portrait unless its alternate layout passes full touch/non-overlap tests; do not silently change that policy;
- screen off/on and reboot restore the selected policy safely;
- sensor process failure degrades gracefully to last-good orientation and manual controls.

### 11.4 Gyroscope-specific physical verification (separate)

If the gyro path is implemented, test its raw values while:

1. stationary on a stable surface;
2. rotating around each axis at different speeds;
3. stopping after movement;
4. screen off/on;
5. after service restart.

Confirm correct unit, sign, axis map, zero-rate bias and drift. Do not use “gyro works” in the report unless all these checks pass.

---

## 12. Phase 9 — Performance and battery targets

- Do not poll the sysfs node faster than needed. Use the configured 100 ms sample cadence initially; benchmark before lowering it.
- Prefer IIO buffered events or existing kernel event delivery if they become usable and are verified. Do not open multiple polling loops against the same sensor source.
- Reuse one sample provider and fan out to consumers.
- Avoid importing dbus or starting SensorProxy unless the source is actually selected.
- Do not keep the sensor hub active in a fixed manual mode unless another subsystem requires it.
- Measure idle CPU, wakeups, battery drain/temperature and time to first valid sample with Auto off and Auto on.
- Use `perf`, `top`, `/proc/interrupts`, runtime PM and service stats where available. Report the measurement method and duration.
- If gyro fusion is enabled, quantify its extra power cost and disable it by default if not justified.
- Avoid continuous debug logging for every sample. Use counters and rate-limited state-change logs.

---

## 13. Phase 10 — Integration, build and deployment

### 13.1 Source/build integration

Update the actual S10+ rootfs build at `images/s10plus/build-phone-rootfs-inside-fedora.sh` and only the relevant package definitions. Ensure:

- new provider files, configs and service units are installed;
- Python imports are available from the installed service path;
- config schema and default config are validated at build time;
- unit files have correct dependencies, sandbox and enablement;
- firmware/vendor dependencies are referenced safely and are not copied into source accidentally;
- the existing daemon, Bridge, Settings and QS all use one status/API contract;
- test fixtures and docs are included in the appropriate development package, not bloating the runtime unnecessarily.

If an isolated Android/Bionic runtime is needed, define a separate opt-in package/manifest with exact source provenance and licensing. Do not quietly change the base Fedora runtime libraries.

### 13.2 Deployment

Prefer the established S10+ Wi-Fi SSH deploy conventions. The deploy script must:

1. verify SSH host/device identity and target codename;
2. check sufficient free space and expected source build version;
3. create timestamped backups of every replaced file and unit;
4. stage all files before replacing active files;
5. run offline tests/compile checks first;
6. install service files atomically;
7. reload systemd and start provider/orientation service with bounded timeout;
8. read back status, sample freshness, transform and touch state;
9. leave current manual orientation mode usable even if Auto provider startup fails;
10. save an exact rollback path and provide one-command rollback.

Do not reboot automatically. Do not replace the kernel, boot image, device tree or firmware partition as part of routine deployment.

### 13.3 Rollback

Provide a paired rollback script that restores all backed-up userspace files, configurations, service units and prior enablement. It must stop only the new provider instance and release only Nuxel-owned sensor bits. Never blindly power off or reset the shared MCU. After rollback, prove fixed/manual orientations still work and Auto returns to the previous honest `blocked_sensor_unavailable` state if no source is active.

---

## 14. Documentation and evidence deliverables

Create/update:

- `docs/pwnage-67000/README.md` — mission summary and status;
- `docs/pwnage-67000/HARDWARE-AND-ABI.md` — actual sensor inventory, vendor runtime/ABI and firmware provenance;
- `docs/pwnage-67000/CALIBRATION.md` — measured raw vectors, mount matrix, gravity references and physical pose evidence;
- `docs/pwnage-67000/ACCEPTANCE-MATRIX.md` — all tests and pass/block states;
- `docs/pwnage-67000/DEPLOYMENT-AND-ROLLBACK.md` — safe Wi-Fi SSH deploy/restore;
- `docs/pwnage-67000/evidence/` — raw command output, sample captures, logs, hashes, test results and physical-test feedback.

Update the existing orientation docs only where current facts change. Preserve prior historical reports; do not rewrite history or claim older tests were performed in this mission.

Final report must include:

1. exact root cause(s) found;
2. files changed and why;
3. vendor/runtime dependencies and legal/provenance treatment;
4. kernel/device ABI findings;
5. before/after sensor status JSON;
6. before/after sample capture showing actual physical movement;
7. calibration matrix and measured pose mapping;
8. measured Auto transition latency and false-trigger behavior;
9. all test results (with counts and failures);
10. remaining owner-only tests clearly marked;
11. battery/performance results;
12. deploy command, rollback command and backup path;
13. explicit statement whether Auto (FULL/PT/LS) is fully working, partly working, or blocked.

---

## 15. Explicit out-of-scope items and forbidden shortcuts

Do not:

- redesign the Nuxel Home UI or replace the existing seven orientation modes;
- change the known Phoc transform mapping without fresh proof;
- add a second compositor or input daemon;
- write fabricated sensor samples to sysfs, IIO, a FIFO or the daemon;
- claim Auto capability from node presence alone;
- install `iio-sensor-proxy` as a cosmetic workaround without a real hardware source;
- guess LHD command-line arguments or BBD protocol payloads;
- copy Android proprietary binaries into Git without permission;
- replace glibc with Bionic or alter global linker paths;
- use random firmware from another device/model;
- flash or write persistent partitions;
- reset the shared sensor hub in a retry loop;
- clear the entire sensor enable mask;
- make gyro integration the absolute orientation source;
- report the whole mission as complete when only fixed/manual modes work;
- weaken the security/lockscreen or touch paths to make rotation appear to work.

---

## 16. Required execution order for the agent

1. Read this entire file and current Nuxel orientation/sensor sources.
2. Run baseline tests and capture exact live state.
3. Inventory all IIO/Samsung sensor nodes and actual current kernel/vendor ABI.
4. Resolve the exact LHD/BBD runtime or native implementation path, with licensing and isolation handled.
5. Get a real accelerometer stream and validate sample freshness.
6. Calibrate the mount matrix and gravity references using physical poses.
7. Connect live samples to the existing policy/daemon and prove Auto rotation.
8. Verify touch and presenter one-transform ownership after physical rotation.
9. Add optional gyro support/fusion only if its path is independently verified and useful.
10. Add power/lease management and robust lifecycle handling.
11. Fix Settings/QS diagnostics and truthful status.
12. Run automated tests, build integration, then safe physical deployment and rollback proof.
13. Produce the final evidence package and a concise handoff report.

**Do the implementation, not just research.** If blocked by absent owner-supplied runtime artifacts or legal redistribution constraints, implement all safe parts, preserve the working manual rotation path, and clearly identify the exact blocker and next owner action.

---

## 17. Final acceptance checklist

- [ ] Current fixed/manual four-pose rotation still works.
- [ ] Sensor identity is proven on the actual SM-G975F.
- [ ] BCM47752/SSP/BBD startup path is understood and no unsafe reset/write is used.
- [ ] Compatible LHD/native provider actually starts and is monitored, or exact blocker documented.
- [ ] Accelerometer raw samples are real, fresh and change with physical movement.
- [ ] Mount matrix and gravity references are calibrated and verified by repeat tests.
- [ ] Auto (FULL) rotates all four legal poses.
- [ ] Auto (PT) rotates only portrait/reverse-portrait.
- [ ] Auto (LS) rotates only landscape/reverse-landscape.
- [ ] Flat/weak/noisy/stale samples hold last good orientation.
- [ ] Transition timing and no-flap behavior measured on the phone.
- [ ] Touch maps correctly at four corners in all poses.
- [ ] Presenter/FB path remains sole visual scanout owner and does not double-rotate.
- [ ] Gyro status is reported separately; if enabled, raw units/axis/rate are physically verified.
- [ ] Auto-to-Locked releases the owned sensor lease without disrupting other sensors.
- [ ] Provider failure gracefully degrades without breaking manual rotation.
- [ ] QS and Settings report actual sensor/calibration/compositor state.
- [ ] Unit, integration, build and regression tests pass.
- [ ] S10+ deploy script backs up and installs safely over SSH.
- [ ] Rollback restores the prior working image/userspace state.
- [ ] Docs and evidence are complete and claims match the test evidence.

**Mission success means actual motion-driven rotation on the S10+ glass, not a green Auto toggle.**
