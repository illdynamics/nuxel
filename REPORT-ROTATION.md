# Rotation / accelerometer / gyroscope report — Galaxy S10+ (`beyond2lte`)

## 1. Executive verdict

`BLOCKED_VENDOR_RUNTIME` (first failing stage: **sensor-hub runtime**). The LSM6DSO accelerometer/gyro and the Broadcom BCM4773/BCM47752 SSP are enumerated, `/sys/class/sensors/ssp_sensor/enable` accepts writes, but the SSP MCU is not ready/streaming: accelerometer `raw_data=0,0,0`, `ssp_sensor/enable=0`, and the kernel log repeatedly reports `[SSP]: ... GPS: false` and `[SSPBBD]: ssp_down == true`. Seven orientation modes and manual/locked rotation already work; auto-rotation cannot move the screen until real sensor samples exist.

## 2. Target identity

- SM-G975F `beyond2lte`, Exynos 9820.
- Sensor: LSM6DSO accelerometer/gyro behind a Broadcom BCM47752-family SSP sensor hub (`ssp,BCM4773`-style binding).
- Confidence: **high** for the SSP/IIO exposure and zero samples; **medium** for the exact LSM6DSO part until a raw chip-ID read is proven.

## 3. What already exists

| Area | Source/path |
|---|---|
| Policy/config | `configs/nuxel/orientation/orientation.json` |
| Daemon | `services/nuxel-orientation/nuxel-orientationd`, `nuxel_orientation/{policy,sensors,apply}.py` |
| Service | `services/nuxel-orientation/…` / `nuxel-orientationd.service` |
| UI | Quick Settings / Settings orientation modes; `nuxelctl` |
| Modes | exactly seven: `portrait`, `reverse-portrait`, `landscape`, `reverse-landscape`, `auto`, `auto-portrait`, `auto-landscape` |
| Manual modes | do not require a sensor; compositor transform + touch mapping |
| Test suite | `tests/pwnage54000`, `tests/pwnage65000` orientation tests |

## 4. Latest evidence

| Check | Result | Tier |
|---|---|---|
| `nuxel-sensors-diag.sh status --json` | accelerometer/gyro/magnetometer/proximity/light/barometer/grip/hall all `present-unreadable` | `PASS_DEVICE_RUNTIME` |
| Accelerometer raw data | `/sys/class/sensors/accelerometer_sensor/raw_data = 0,0,0` | `PASS_DEVICE_RUNTIME` |
| SSP enable | `/sys/class/sensors/ssp_sensor/enable = 0` | `PASS_DEVICE_RUNTIME` |
| SSP kernel log | `[SSP]: ... GPS: false`; `[SSPBBD]: ssp_down == true. returning` | `PASS_DEVICE_RUNTIME` |
| IIO devices | `iio:device1` (accel), `iio:device4` (gyro), `iio:device2` (mag), `iio:device11` (proximity) | `PASS_DEVICE_RUNTIME` |
| Observed motion verified | false | `NOT_TESTED` (needs physical tilt) |
| Manual orientation | seven-mode daemon active | `PASS_DEVICE_RUNTIME` |

## 5. Full dependency chain

| Stage | Current state |
|---|---|
| LSM6DSO sensor silicon | physically present (S10+); exact part not independently chip-ID’d |
| SSP/Broadcom hub | `ssp_sensor` class + `/dev/bbd_control` exist; `ssp_down=true` |
| Sensor-hub patch/firmware | no verified runtime patch; vendor `lhd`/sensorhub libraries not executable in Nuxel |
| Kernel driver | IIO nodes and sensor class present; raw reads return zeros |
| Sensor enable | writes accepted but `enable=0`; no streaming |
| Sample decode/scale | no nonzero sample to decode |
| Orientation policy | seven modes implemented, hysteresis/cooldown/flat handling |
| Compositor transform | manual transform path verified; auto requires samples |
| Touch remap | manual remap exists; auto touch matrix unverified |

## 6. First failing stage

**Sensor-hub runtime.** The SSP MCU never reaches a ready/streaming state. Writing the accelerometer enable bit and attempting `ESW:READY` on `/dev/bbd_control` does not produce nonzero samples. The kernel log says the SSP is down. This is not a UI or orientation-policy bug.

## 7. Why prior attempts have not completed the feature

- `docs/a69/ROTATION-HARDWARE-BOUNDARY.md` and PWNAGE-54000/55000 documented `ESW:READY` + enable-bit attempts, SSP MCU-not-ready, and all-zero vectors.
- Vendor `lhd`/sensorhub libraries exist on the read-only vendor partition in some audits, but the Android/Bionic linker/runtime needed to execute them is absent from the Nuxel rootfs.
- Manual/locked modes already work and must not be replaced by a competing rotation daemon.

## 8. Best recommended architecture

**Primary:** a lawful native BBD/SSP handshake + patch protocol implementation that powers the hub, downloads/validates the sensor-hub patch, enables the accelerometer/gyro, and decodes raw samples with correct scale, timestamps and mount matrix. Feed the existing seven-mode policy.

**Fallback:** a narrowly isolated vendor sensor-hub runtime with the exact Bionic/linker dependencies, only if licensing and isolation are acceptable.

**Direct LSM6DSO driver:** only if the DT/schematic proves the sensor is reachable on a host I2C/SPI bus outside the SSP. Do not bind a second driver to an occupied device.

## 9. Required work inventory

| Area | Work |
|---|---|
| Firmware/provenance | exact BCM47752/SSP patch; verify hash/license |
| Kernel/DT | SSP/BBD control ABI, power/reset, IRQ, sensor enable, suspend/resume |
| Userspace | hub handshake, patch load, enable bits, sample decode, scale/units |
| Orientation | mount matrix/calibration, fusion/hysteresis, existing seven modes |
| Compositor/touch | auto transform + matching touch remap |
| Tests | physical tilt matrix, all four poses, lock/wake/suspend |

## 10. Source/upstream research

- No upstream mainline BCM47752 SSP sensor-hub runtime for this vendor ABI in the repo.
- Vendor LHD/sensorhub code is Android/Bionic; it is not directly executable in Fedora ARM64 without an isolated compatibility runtime.
- The existing Nuxel orientation policy is the authoritative consumer and should be kept.

## 11. Buildability

- Native protocol code can be built in the current toolchain if the BBD/SSP ABI is documented.
- The sensor-hub patch and vendor runtime are not in the repo; owner/OEM material is required.
- No kernel/firmware flashing is authorized.

## 12. Risks and constraints

- Wrong hub patch → sensor hub or GNSS/rotation subsystem instability.
- Direct I2C/SPI access to an SSP-owned sensor can conflict with the hub.
- Never synthesize gravity data to make Auto appear enabled.
- Preserve manual modes and touch mapping at all times.

## 13. Phased roadmap

| Phase | Goal | Gate |
|---|---|---|
| 0 | Bounded SSP/BBD handshake trace; confirm hub identity/patch revision | No auto claim |
| 1 | Power hub, reach ready, enable accelerometer | Nonzero raw accel |
| 2 | Decode scale/units/timestamps; physical tilt test | Axis changes match tilt |
| 3 | Gyro streaming + fusion | Gyro samples |
| 4 | Auto transforms + touch remap + hysteresis | All poses, touch aligned |
| 5 | Suspend/resume and calibration persistence | Runtime matrix |

## 14. Acceptance test matrix

| Test | Required evidence |
|---|---|
| Accelerometer | nonzero vectors change with physical tilt, settle correctly |
| Gyro | nonzero rates during rotation |
| Four poses | portrait/landscape/reverse map correctly |
| Auto modes | correct transform and hysteresis |
| Touch | coordinates remain aligned after transform |
| Lock/wake/suspend | samples and orientation resume |
| Manual modes | still work with sensor absent/failing |

## 15. Owner inputs required

- Physical tilt/rotate test.
- Confirmation that the vendor sensor-hub runtime/patch may be used, or protocol documentation.
- Recovery access for any hub experiment.

## 16. Confidence and gaps

- **Proved:** sensor classes/IIO nodes exist, raw accel is zero, SSP is down, manual modes work, auto does not.
- **Inferred:** the missing SSP/BBD runtime is the primary blocker; LSM6DSO may be hub-owned.
- **Unknown:** exact sensor-hub patch revision, LSM6DSO power state, mount matrix/calibration, whether direct host access is physically possible.
