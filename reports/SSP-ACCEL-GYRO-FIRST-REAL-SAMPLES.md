# SSP-06 — Accelerometer + Gyroscope First Real Samples

**Date:** 2026-11-23 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (`beyond2lte`), serial `R58M75KDB2X`, Exynos9820
**Transport:** SSH `root@10.11.12.99` (read-only)
**Commit:** `8e2f47254d189babaea989d6da50c013744c2d97` (`cs/ssp`)

## 0. Gate 06 result

```
GATE_06 = BLOCKED_MCU
SENSOR_ACCEL_PHYSICAL = NOT_RUN   (no real MCU app / SSP handshake established)
SENSOR_GYRO_PHYSICAL  = NOT_RUN   (no real MCU app / SSP handshake established)
```

Task 06 states explicitly: **"proceed only after 05 proves a real MCU app and the normal
SSP handshake; otherwise finish non-hardware tests and report `BLOCKED_MCU`."** Neither
prerequisite is satisfied. All non-hardware (offline) tests have been completed and pass;
the physical sensor demonstration is correctly gated out. This report records the decisive
live evidence and the offline verification, and does **not** fabricate any sample,
timestamp, enable bitmap, IRQ count, or axis matrix.

## 1. Decisive live MCU condition (read-only, 2026-11-23)

Captured directly from the live device (full transcript in
`evidence/pwnage-ssp-06/live-baseline.txt`):

| Attribute | Live value | Interpretation |
|---|---|---|
| `nuxel_hub_diag` | `mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443` | hub probe done but **shutdown/reset loop**; firmware app NOT running; **all sensors disabled (enable=0x0)** |
| `mcu_name` | `BCM47752KUB1G` | controller identity confirmed at runtime |
| `mcu_rev` | `BR0121080900,BR010` | revision confirmed |
| `mcu_test` | `NG,NG,NG` | MCU self-test **fails** (no firmware app) |
| `enable` | `0` | sensor enable bitmap = 0 (nothing enabled) |
| `sensor_state` | *(empty)* | no runtime sensor state published |
| `mcu_reset` | `OK` | reset is attainable but hub is not started |
| `reset_info` / `bcm_minidump` | `GPS OFF` | GNSS domain never energized |
| IRQ 441 `ttyBCM` | `0` | SSI transport never fired (no handshake I/O) |
| IRQ 443 `ssp-shub-int` | `1` (edge) | single host-req edge; **no data stream** |
| `accelerometer_sensor/raw_data` | `0,0,0` | no accel samples |
| `gyro_sensor/raw_data` | `0,0,0` | no gyro samples |
| IIO `iio:device1` channels | none (`in_*` absent; only `current_timestamp_clock`) | SSP virtual accel wrapper present but **no data channel populated** |

The BCM47752 sensor hub is the sole source of accel+gyro on `beyond2lte`. Those samples
are delivered over the SSP/BBD packet pipeline (`/dev/ttyBCM` SSI → kernel RPC decode → SSP
state machine → `/sys/class/sensors/*/raw_data`). Because the hub is in a shutdown/reset
loop and `enable=0`, **zero samples flow** — IRQ 441 = 0 is the direct proof that no
interrupt-driven sensor event has ever arrived.

### Why 05 has not proven a real MCU app / SSP handshake

`reports/SSP-05_16-STAGE-06-HANDOFF.md` and `reports/SSP-06_00-ACCEPTANCE.json` show:

- `READY_FOR_06 = false`; blocking gates `POWER_TRANSITION_SAFETY` + `ROM_GETVERSION`
  folded into the Stage-06 **firmware-download trial**.
- `SSP-06_00` decision = `READY_FOR_SPECIFIC_OWNER_APPROVAL`, `physical_trial_performed = false`,
  `physical_trial_success_claimed = false`.
- The minimal correct trial (GPS_PWR_EN → MCU handshake → autobaud → GetVersion →
  MemoryWrite×479 → StartScratch → ServiceStart → post-download GetVersion) **has NOT been run**;
  it awaits owner RF authorization + timing artifact + bounded-trial grant.

Consequently there is **no MCU firmware application running**, **no `ESW:READY`**, and **no
normal SSP handshake** — the exact prerequisites task 06 requires before enabling or
recording accel+gyro.

## 2. Offline (non-hardware) verification — ALL PASS

Per the task instruction to "finish non-hardware tests" before reporting `BLOCKED_MCU`:

| Suite | Result |
|---|---|
| `make -C tools/s10plus/ssp-native check` | PASS (framing + F1 + RX decode; 17 negative cases; embedded-patch 2 tests) |
| `tools/s10plus/ssp-runtime` unittest (`test_kernel_identity`, `test_isolation`) | 10/10 OK |
| `services/nuxel-orientation/tests/` (pytest) | 77 passed |
| `tests/pwnage_ssp/test_sensor_hub_native.py` | 0 failing (bridge never fabricates samples; gyro 700 LSB == 0.07 dps scale; sign preserved) |
| `tests/pwnage_ssp/test_app_orientation_force.py` | 0 failing |
| `check_protocol_replay.py` | `{"passed": true, "hardware_verified": false, "operation_completion_verified": false}` (correctly refuses HW claim) |

All runnable offline protocol/firmware/negative/fault-injection tests pass, and the bridge
source is instrumented to **never** synthesize samples or readiness
(`services/nuxel-orientation/nuxel_ssp_bridge.py`: bring-up uses kernel `nuxel_bringup`;
`_streaming()` requires non-zero hub-delivered raw_data; no `ESW:READY` synthesis).

## 3. Bring-up path inspected (prepared for the gated trial)

- **Native bridge:** `services/nuxel-orientation/nuxel_ssp_bridge.py` — owns the
  `/dev/bbd_sensor` peer contract, asks kernel to bring the hub up via write-only
  `nuxel_bringup` (1) and start accel+gyro via `nuxel_stream` (1). It truthfully reports
  "hub unavailable" if `initialize_mcu` fails; no duplicate owner, no firmware application,
  no synthesized readiness.
- **Sysfs ABI (live):** `/sys/devices/virtual/sensors/ssp_sensor/`
  `nuxel_bringup` (`--w-------`, write-only), `nuxel_stream` (`--w-------`),
  `enable` (`-rw-rw-r--`), `sensor_state` (`-r--r--r--`), `nuxel_hub_diag` (read).
- **Sensor enable bitmap:** centralized on `ssp_sensor/enable` (currently `0`). Individual
  `accelerometer_sensor`/`gyro_sensor` have no `enable` node; they follow the hub bitmap.
- **Raw data path:** `gyro_lsm6dsl.c` / `accel_lsm6dsl.c` (Broadcom SSP factory layer) and
  `st_lsm6dsx` IIO driver. Gyro scale convention recovered:
  `DEF_GYRO_FULLSCALE=2000` dps, `DEF_GYRO_SENS=70` (`0.07 * 1000`) → **raw LSB × 0.07 dps**,
  sign-preserved (this is the STM LSM6DSO/DSL DPS2000 convention). No live counts exist to
  apply the calibration to, and none are invented.
- **Axis conventions / mount matrix:** recorded as *pending physical calibration*. The task
  requires recomputing the mount matrix and gravity references **from real multi-pose data**;
  with `raw_data = 0,0,0` in every pose there is no data from which to derive signs, scale or
  a 90-vs-270 landscape prediction. Nothing here fabricates a matrix.

## 4. Required real measurements — NOT performed (correctly gated)

- Multiple samples across ≥4 physical poses: **not obtainable** (hub down, 0,0,0).
- One physical movement (gyro burst → decay to rest): **not obtainable**.
- Gravity direction/magnitude agreement across portrait/L-L/R-L/reverse-portrait:
  **not obtainable**.
- Auto-sideways (90 vs 270) derivation: **deferred** — requires real signed gravity vectors.

Rejection criteria the recorder enforces (and would reject): hardcoded constant nonzero
data, stale timestamp, fake node, generated fixtures, IIO timestamp-only devices. All
current live values are the truthful `0,0,0` / `0` (not accepted as samples — treated as
"no stream").

## 5. Diagnostics summary

| Check | Status |
|---|---|
| Sensor disabled | YES — `enable=0`, bitmap empty |
| Inactive MCU | YES — `shutdown=1 resetting=1`, `mcu_test=NG,NG,NG` |
| Timeout (transport) | implicit — SSI never fires (IRQ 441 = 0) |
| Bad scale | N/A (no samples) — scale convention documented (×0.07 dps) |
| Jitter | N/A |
| CRC | N/A |
| Interrupt loss | N/A — no IRQ-driven stream (IRQ 443 edge count 1) |
| Stale data | raw_data = 0,0,0 (no stream, not stale) |
| GNSS/shared power | `GPS OFF`; GNSS domain never energized (RF authorization withheld) |

## 6. No kernel flash / no boot change

No BOOT/DTB/DTBO/recovery write. No regulator change. No GPIO assertion. No firmware
application. No `ESW:READY`. Known-good Nuxel boot, DTB, DTBO and all services preserved.
Rollback images (5+ BOOT) remain intact.

## 7. Deliverables

- This report: `reports/SSP-ACCEL-GYRO-FIRST-REAL-SAMPLES.md`
- Raw live log: `evidence/pwnage-ssp-06/live-baseline.txt`
- Calibrated axis matrix: **not produced** (would require real multi-pose samples; refused rather than fabricated)
- Actual sample timestamps: **none** (no samples)
- Gyro physical-movement evidence: **none** (no stream)
- Source: `services/nuxel-orientation/nuxel_ssp_bridge.py`, `kernel/.../gyro_lsm6dsl.c`, `tools/s10plus/ssp-native/`
- Tests: all offline suites PASS (see §2)

## 8. Blocking condition & minimum owner action

Repeated, unchanged blocking condition across the prior missions: **Stage-06 firmware
download + app start has not been authorized** (RF + timing + bounded-trial), so no MCU
firmware app exists and the SSP handshake cannot establish. Until that trial is authorized
and produces a verified post-download `GetVersion` (`w0 == 0x4775b0`) followed by
`ESW:READY` and `enable` bitmap with accel+gyro, the physical accel/gyro stream is
unreachable and Gate 06 remains `BLOCKED_MCU`.

Minimum owner action (unchanged from `SSP-06_00-PHYSICAL-TRIAL-AUTHORIZATION.md`):
1. RF authorization (bounded GNSS-domain energisation), and
2. Timing artifact (datasheet VDD→ROM-ready, or explicit bounded settle instruction), and
3. Explicit bounded-trial grant (MCU wake + MemoryWrite×479 + StartScratch + ServiceStart +
   post-download GetVersion, recovery bound MCU_REQ=0 / GPS_PWR_EN=0 / `bbd_mcu_reset`).
