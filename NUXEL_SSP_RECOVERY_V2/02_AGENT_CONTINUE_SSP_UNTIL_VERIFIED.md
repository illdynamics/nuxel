# SSP FIRST-LIGHT: AGENT CONTINUATION MISSION (Nuxel S10+ BCM47752 / LSM6DSO)

**Priority: actual working sensors, not speculative firmware, a green status flag, or another standalone report.** Execute this on the operator's existing Nuxel Git working tree (for example `/Users/wicked/x/nuxel-ssp-first-light`). The provided `NUXEL_SSP_RECOVERY_V2` folder contains original host tooling, verified offline tests, archive audit, and an updated source map. All scripts are intended to be reviewed, run locally, and integrated with appropriate rollback provisions.

## Non-negotiable mission contract

1. **Do the work.** Inspect, modify, test and commit concrete source changes; do not treat the request as merely a research essay. Continue across bounded safe investigation and implementation iterations without reflexively returning a research report. Escalate only genuinely external prerequisites or an operation that requires owner authorization.
2. **No false success.** Final completion requires a reachable actual SM-G975F/beyond2lte showing physically changing accelerometer and gyroscope sample streams under user movement and functional automatic rotation; real suspend/resume and restart regression results. A green service, a fabricated `available=true`, or synthetic samples do not count.
3. **Don't endanger recoverability.** Hardware firmware writes, boot partition flashes, GPIO/sensor power toggles, changes to the live GNSS power pin or any destructive operation require a separately reviewed, device-specific recovery and rollback plan and explicit owner approval. Maintain no-write defaults. Never read EFS, personal data or calibration secrets just to test this path.
4. **Do not bypass a protocol requirement.** Keep the native downloader's `--download` fail-closed unless reference code and real handshake evidence establish ACK/NACK/retry/address/sequence and failure semantics. No guessed bytes, vendor firmware from unrelated BCM477xx devices, or bulk write to `/dev/ttyBCM` to see if it wakes.
5. **Never suggest time-delayed background work as done.** Work in the current agent execution, with git commits/test evidence and a precise handoff if blocked by real external input.
6. **Provenance for every assertion:** classify `ARCHIVE_REPRODUCED`, `LIVE_VERIFIED(timestamp, uname, command)`, `REPORT_ONLY`, `UPSTREAM_RESEARCH`, `HYPOTHESIS`. Distinguish the previous Nov 13 #48/#78 kernel runs, Nov 14 `#3`, and current kernel.

## Immediate source inspection (must start here)

Read all of these before making changes:

- `NUXEL_SSP_RECOVERY_V2/01_DEEP_AUDIT_2026-11-16.md` and this prompt.
- `reports/SENSORS-FIRST-LIGHT.md`, `reports/SSP-FIRST-LIGHT-CONTINUATION.md`, `reports/SSP-CONTINUATION-20261116.md`, `reports/PWNAGE-SSP-HARDWARE-MAP.md`, `reports/PWNAGE-SSP-RUNTIME-INVENTORY.md`.
- `tools/s10plus/ssp-native/nuxel_bbd_download.c`, `verify_embedded_patch.py`, `Makefile`, all unit tests and the existing `nuxel_bbd_host.c`.
- `tools/s10plus/ssp-runtime/run_isolated.py`, `isolation_probe.c`, `android_log_stderr.c`, `test_isolation.py`.
- `NUXEL_SSP_CONTINUATION_PACK/ssp_runtime_audit.py` and tests, `packs/sensors/acquired/*`, `services/nuxel-orientation/*` and any `services/nuxel-gnss` coupling.
- Current local Git status, branch, commit; compare with `3d34aef8` and the continuation branch. Never discard local changes, cherry-pick over unknown work or trust the ZIP's prebuilt downloader.

**Key updated facts from this ZIP:** first-light downloader source and tests are present, but the shipped `nuxel_bbd_download` binary is unchanged from the older ZIP. Rebuild any production binaries from audited source. The source header `kernel/s10plus/.build/src/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h` was omitted from the archive. Do not claim it was independently verified from this package. Current stock Android `linker64`, system/VNDK/APEX libraries and external matching build identity are absent. The offline audit has 28 unresolved DT_NEEDED occurrences involving 14 distinct library names. `lhd.conf` references the sensor MCU rail and the GNSS `GPS_PWR_EN` pin—historic reset hazard.

## Stage 0: reproduce baseline, refresh current device state

- Re-run `make -C tools/s10plus/ssp-native clean check` on a disposable build area and record compiler version, architecture and outputs; do not run any old bundled binary on a phone. Re-run existing `ssp_runtime_audit.py` and `test_isolation.py`, and `python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_recovery_v2.py'`.
- Connect to current live device using operator-provided SSH/ADB; do not assume historic IP, port, kernel, or node set. The new optional read-only sampler:

  ```bash
  python3 -S NUXEL_SSP_RECOVERY_V2/ssp_live_snapshot.py \
    --host YOUR_PHONE_SSH_HOST \
    --output /tmp/ssp-current-samples.json \
    --samples 12 --interval 0.75 --capture-readonly
  ```

  Collect repeated samples while the owner rotates the phone. It uses only allowlisted `cat`/`uname` reads over SSH, no GPIO or power writes. **If SSH fails, report CONTACT_UNAVAILABLE and try a separately reviewed ADB read-only session; never infer broken hardware solely from failed SSH.** The script classifies zero/static/changing vectors but does not by itself prove a physical sensor.
- Record `uname -a`, model, device nodes (existence only), raw accel/gyro, SSP enable, kernel logs filtered for relevant BBD/SSP initialization, and timestamp, before considering any change. Redact identifiers not relevant to hardware diagnostics from shared logs.

## Stage 1: reuse exact Samsung vendor runtime; recover the matching Android userspace

**This is the primary branch. Do not replace firmware just to avoid missing libraries.** `packs/sensors/acquired/` already contains Samsung `lhd`, `lhd.conf`, `sensors.sensorhub.so`, and `sensors.exynos9820.so`. Public beyond2lte vendor configurations corroborate these components. The missing runtime is an Android system/Bionic/VNDK/APEX closure, not a missing new sensor driver.

A. Determine exact device/vendor/system provenance from owner-held stock records, running build properties, previous recovery manifests, SHA-256s, and source tree. Do not assume Android version from filenames or combine vendor from one build with Bionic from another. Recognize Android linker namespaces/VNDK, and on newer Android `/linkerconfig` generated at boot.

B. If the **matching original stock Android system and vendor partitions are already mounted read-only** in owner-authorized TWRP/recovery, use the new **read-only ADB collector** from the operator's Mac:

```bash
python3 -S NUXEL_SSP_RECOVERY_V2/ssp_stock_collect.py \
  --repo-root . \
  --output /tmp/nuxel-ssp-stock-from-owner \
  --collect-readonly
```

`--serial ...` if necessary. Default without `--collect-readonly` is plan-only. It executes only `cat` on allowlisted vendor/system/product/APEX paths; no handset writes, partition mounts, reboot or daemon execution. It verifies the four acquired vendor anchors by their full hashes and refuses mixing mismatched vendor sets. It follows DT_NEEDED recursively, subject to explicit size/object caps. Its static resolution order is a **candidate selection heuristic, not a VNDK namespace proof**.

C. If recovery does not expose a matched stock `/system/bin/linker64`, STOP THIS EXTRACTION PATH; obtain the exact matching owner-authorized Android stock system archive by original firmware/build identity and perform **offline** extraction of filesystem images/APEX packages in a temporary host directory. Do not retrieve guessed ROM blobs from random mirrors, force-mount unknown partitions, or attempt to reconstruct Bionic via a different phone's library set.

D. Re-run the existing archive's ELF dependency closure audit on that owner-collected directory:

```bash
python3 -S NUXEL_SSP_CONTINUATION_PACK/ssp_runtime_audit.py \
 --repo-root . \
 --android-root /tmp/nuxel-ssp-stock-from-owner \
 --report-dir /tmp/nuxel-ssp-audit-with-stock \
 --stage-runtime /tmp/nuxel-ssp-runtime-isolated
```

Identify all ambiguous `DT_NEEDED` paths, missing APEX mounted contents, RPATH/RUNPATH, VNDK variants, linker config, ABI and architecture; compare lhd/SensorHub HAL build and identity. A status of static closure COMPLETE is **not** proof of runnable Android userspace. Capture a detailed file/source/hash manifest and ensure none of the extracted proprietary binaries are committed or republished to Git without authorization.

## Stage 2: isolated lhd trial with NO handset hardware

The existing `tools/s10plus/ssp-runtime/run_isolated.py` requires missing staged assets not shipped in the ZIP. New helper produces a hardware-denied config and manifest in the host staging tree:

```bash
python3 -S NUXEL_SSP_RECOVERY_V2/ssp_trial_prepare.py \
  --root /tmp/nuxel-ssp-runtime-isolated --prepare
```

That tool intentionally rewrites active `GpioNPowerPath`, `GpioNStdbyPath`, `LhePatch`, `LheBbdPacket`, `LheBbdSensor`, `LheBbdControl` to absent sandbox paths and sets MCU reset retries to zero **in the isolated config only**. The original config remains unchanged. It rejects symlinks and hashes every staged file. It does not execute `lhd`, and does not create the additional target-built `isolation-probe` and `libssp-log-stderr.so`; these require an appropriately configured AArch64 build and exact dependency review. Build them from the existing C sources, test their ELF interpreter/dependencies and rebuild the manifest without overwriting evidence.

On **AArch64 target** with a reviewed runtime, run the isolated probe FIRST using the existing `run_isolated.py --probe` option. Require actual `bwrap` namespace/capability/device restrictions, strace evidence, full manifest verification, no host/phone device handles, no GPIO/rail access, and no exposed block devices. Only then run a short, strictly hardware-denied daemon trial to distinguish dynamic-loader failure from missing Android properties/services or Binder requirements. Use timeout and no persistent services; no GNSS or sensor power paths ever exposed during this phase. If the sandbox cannot operate, improve it with an isolated test fixture, not by granting all device mounts.

**If runtime dependencies prevent this route**, investigate libhybris/Halium/LXC only if a source-informed compatibility layer is technically warranted. Treat shipping a full Android container as a significant new integration project, not a guaranteed drop-in fix.

## Stage 3: settle actual SSP firmware/RPC protocol evidence before any write

If the matching daemon can be isolated, derive the BBD transport and handshake reference using logs and source-backed traces from a matching authorized Samsung environment. Locate exact kernel source for `f7194c1d15eded1c2a1a4dc63825b26103435cc0` and `bbd_patch_file_beyond.h`; rerun the existing source verifier. Confirm physical silicon identity/ROM status and SPI/IRQ behavior on a fresh boot. For each firmware operation, document opcode, frame encoding, sequence behavior, length, checksum, start address, ACK, NACK, retry, timeout, abort and rollback evidence.

The existing `nuxel_bbd_download.c` intentionally refuses `--download`; preserve that gate until the full protocol is independently proven in a deterministic simulated peer and an actual limited, owner-approved test. No speculative send loop, power-cycle brute force, unknown ROM image or generic Broadcom patch. Do not use GPS power toggles as a workaround; repository hardware history describes resets. Any future write requires an operator-approved risk review, verified full backup/recovery path, and separately bounded protocol test. Never auto-flash BOOT just for sensors.

## Stage 4: real sensor data path and software integration

Only once the MCU has verifiably initialized and kernel SSP can register actual samples:

1. Record a timestamped physical six-face accelerometer and gyro turn test: each vector must be valid, nonconstant under movement, consistent with gravity and axis mapping, and independent of fabricated sysfs values. A human operator must correlate orientation/time.
2. Validate sensor timestamp/interrupt flow; read kernel SSP `enable`, `ssp_down`, IIO/sysfs device state, no perpetually zero vectors or lost events. Track cold/warm boot and suspend/resume, reset recovery and power budget.
3. Integrate with existing `services/nuxel-orientation/nuxel_ssp_bridge.py` and orientation daemon without regression of manual rotation or original 7 rotation modes. Preserve touch coordinate mapping under compositor transforms.
4. Verify actual portrait/landscape transitions both directions with touchscreen interaction; deterministic timed physical test cases, debounce/hysteresis and lock behavior. Do not declare completion until the actual handset demonstrates these transitions.
5. Keep component-specific changes isolated in commits with tests, reproducible binaries and a rollback plan. Do not disturb modem, Wi-Fi, NFC, camera or recovery.

## Stage 5: evidence-gated output, repeatability and completion

Produce:
- `reports/SSP-FIRST-LIGHT-RECOVERY-<date>.md` with original baseline, command, host/device identity and time, every encountered error, final physical test table.
- Complete dependency/build manifest for recovered runtime (owner-local; do not embed proprietary binary in public commits), source/license attribution and exact version matching.
- Reviewed patches with tests of every protocol parser/reader and negative/error path; re-run all existing SSP/orientation regression suites.
- A known-good boot image checksum if any kernel work is ever explicitly approved, plus separate readable restore instructions; do not flash without approval.
- For each failure, one specific next required artifact/measurement, not vague 'needs drivers'.

**Never claim 100% success without physical evidence.** If the next stage needs a proprietary stock system image or a reachable phone, exhaust all non-destructive local/web/source discovery, deliver functioning tooling and a precise request for that missing prerequisite, then stop safely rather than inventing an alternative. Avoid endless retries on hardware and avoid any destructive action without explicit approval.

## Verified reuse-first references (consult before writing replacement code)

- https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk
- https://raw.githubusercontent.com/Evolution-X-Devices/vendor_samsung_beyond2lte/bka/proprietary/vendor/etc/sensor/lhd.conf
- https://source.android.com/docs/core/architecture/vndk/linker-namespace
- https://github.com/LineageOS/android_device_samsung_beyond2lte
- https://github.com/libhybris/libhybris
- https://docs.halium.org/en/latest/project/Scope.html

The references guide **source compatibility research**, not a license to replace the firmware or assume drop-in Android runtime compatibility. Prioritize the exact acquired vendor files, live board/kernel identity, and official Android runtime linker rules over non-specific online recipes.
