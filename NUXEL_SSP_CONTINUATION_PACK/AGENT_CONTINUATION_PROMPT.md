# AGENT CONTINUATION PROMPT — Nuxel S10+ SSP / BCM47752 first-light recovery

## Assignment and expected output

You are the engineering agent responsible for making **real, physical LSM6DSO accelerometer and gyroscope measurements stream through the Samsung/BCM47752 SSP/BBD hub to Nuxel Linux on the SM-G975F / beyond2lte / Exynos 9820**, and then restoring auto-rotation using the project's existing orientation daemon. This is an execution assignment, not merely another research report. Continue until (a) hardware-verified acceptance passes, or (b) a precise, independently reproducible blocking condition remains and you have implemented and tested every safe solution available from the evidence.

**Do not claim a 100% guarantee or manufacture test data.** The phone's behavior, the OEM Android runtime ABI, and the hub's firmware ACK sequence cannot be established from offline tests alone. Never report `working` based only on a service process, sensor device nodes, an `enable=1` write, an MCU-ready string, or a simulated protocol test.

You have been given:
1. The current Nuxel repository on disk and user-provided `nuxel-main (2).zip`.
2. Your previous first-light branch `codex/ssp-first-light-20261116`, claimed commit `3d34aef8`, `reports/SENSORS-FIRST-LIGHT.md`, and `reports/SSP-CONTINUATION-20261116.md`.
3. This package's new **read-only offline** tool `ssp_runtime_audit.py`, tests, and source evidence.

**Reconcile these sources first.** The uploaded archive includes older `packs/sensors/` and `packs/ssp/` extraction utilities and a 2026-11-13 continuation report, but does not include `SENSORS-FIRST-LIGHT.md` or the 2026-11-16 test harness the previous agent claimed. The 2026-11-13 archive report describes kernel `#78`, while the current agent message describes kernel `#3` from Nov 14. These are different snapshots. Verify actual `git branch --show-current`, `git log`, `git status`, `uname -a`, `uname -v`, device-node state, and local vs live checksums. Do not revert, overwrite, or reflash the live device to "match" an old report.

## Non-negotiable safety rules

- No blind `dd`, destructive partition writes, bootchain updates, firmware uploads, voltage/rail resets, GPIO toggles, SPI poking, or automatic retry storms. The repository records **hard device resets after driving `ssp-gps-pwr-en` / `GPS_PWR_EN`**. Treat that control as a known danger, not a debugging shortcut.
- Preserve the original A-only Samsung S10+ partition layout. Do **not** assume an inactive A/B slot. Before any eventual approved flash, independently verify model, boot image, current partition layout, backups, and a working TWRP/ADB recovery path; obtain explicit operator confirmation for that specific disruptive action.
- Perform extraction, ELF parsing, and staging **on the host**. Running `ssp_runtime_audit.py` must never touch the phone. Keep Android libraries in an isolated prefix; do not put Bionic into `/usr/lib*`, overwrite glibc, or replace the host dynamic loader.
- Never run unknown Android vendor binaries with unbounded device access. A later trial requires a scoped isolated runtime, reversible service configuration, minimal device-node access, write restrictions, defined timeout, single exclusive process ownership, explicit logging, and consent. Do not mount or read `/efs` or private `/data/vendor/gps` calibration/NV storage without a separately justified need and approval.
- Never confuse `LhePatch=/dev/bbd_patch` with a normal firmware file, and never use the 2-byte test fixture or a random Pixel BCM47765 `SensorHub.patch` on BCM47752. The patch header `Crc=0xC1` was not shown to be IEEE CRC-32; do not reject the known patch solely on that basis.
- On failure, leave the original manual rotation working and display honest `blocked_sensor_unavailable` or equivalent. Keep existing services rollbackable and keep original proof/logs.

## Phase 0 — pin live evidence and prevent source drift

1. Review the first-light branch/report, local diff, initial firmware patch hash, native downloader's CLI and tests, and current boot/kernel deployment. Explicitly enumerate where current files differ from `nuxel-main (2).zip`.
2. Confirm the purported firmware-patch identity **without uploading**: SHA-256 `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72`, ASIC `0x004775b0`, blob length `438895`, address `0x00800161`, decoded-content IEEE CRC-32 `0x93d35bb4`. Record whether the values can be independently reproduced in the current environment and distinguish the patch header's independent `Crc` field.
3. Reproduce the read-only live baseline: `ssp_down`, `enable`, accelerometer and gyro raw readings, `dmesg`/journal SSP errors, BBD endpoints, kernel build identity, and regulator/power state by reading only. Avoid exposing personal data or device identifiers in shared logs.
4. State stop/go for active tests: no privileged hub transaction or firmware upload until timing, framing, ACK/NACK sequencing, rollback and protection against the observed hard-reset path are verified and user-authorized.

## Phase 1 — exploit existing work; do not write new firmware yet

The repo already contains:
- `packs/sensors/acquired/vendor-bin-hw-lhd` (AArch64 Android `lhd`; SHA-256 `6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`);
- `vendor-lib64-sensors.sensorhub.so` (SHA-256 `de0110a7065f39723fc7436f4d5451d92572d87fe9a3ae8550cc4e88f3cd5718`);
- `vendor-lib64-hw-sensors.exynos9820.so` (SHA-256 `44b26ae85510b2c4147d0ff8a518211e8a475fd29c002922f53b5a726e4d2ef0`);
- `vendor-etc-sensor-lhd.conf` with the BBD endpoints;
- `tools/s10plus/ssp-native/nuxel_bbd_download.c`, its previously described improvements, and prior host tests;
- pre-existing `packs/sensors/scripts/extract-s10plus-ssp-runtime.sh`, `collect-elf-deps.py`, and `verify-s10plus-ssp-runtime.py`.

Run `readelf` on the exact current files. Archive-verified direct dependencies of `lhd`: `liblog.so`, `libutils.so`, `libz.so`, `libhardware_legacy.so`, `libc++.so`, `libc.so`, `libm.so`, and `libdl.so`. Its interpreter is `/system/bin/linker64`. The sensor HAL has *additional* HIDL/Binder-related dependencies. The new audit tool reports 14 unique missing library **names across three ELF seeds** when no stock Android runtime is provided; do not mistake them for all transitive requirements.

Use the author's **matching, owner-provided stock Android** image or read-only TWRP-mounted system/vendor partition. Prefer the actual build that supplied the vendor binaries; establish fingerprints/Android API/VNDK level and hashes before combining. Source matching Bionic linker and library closure from that build, including appropriate APEX/VNDK namespace layout. Use existing repo extractor if that ADB environment supports `getprop` and mounted partitions. Because TWRP may not expose Android `getprop` values or the correct `/system` path, **do not bypass device identity checks**; instead inspect mount mappings and obtain the stock filesystem offline.

Run this pack's original, offline verifier from a host:

```sh
python3 -S ssp_runtime_audit.py \
  --repo-zip "/path/to/nuxel-main (2).zip" \
  --report-dir ./ssp-audit-before
```

With an owner-extracted stock filesystem tree available:

```sh
python3 -S ssp_runtime_audit.py \
  --repo-zip "/path/to/nuxel-main (2).zip" \
  --android-root "/path/to/EXTRACTED_MATCHING_ANDROID_ROOT" \
  --report-dir ./ssp-audit-with-stock \
  --stage-runtime ./ssp-isolated-runtime-STAGED-ON-HOST-ONLY
```

If the archive isn't accessible as a valid ZIP in your environment, run with `--repo-root /path/to/extracted/nuxel-main` instead. Read the generated `ssp-runtime-audit.json` and `.md`, preserve unresolved dependency and interpreter failures, and verify each staged file's SHA-256. **A static dependency PASS is only permission to design a runtime trial, never proof of ABI or hardware readiness.** If the vendor/system build cannot be established, report that precise blocker and don't mix random libraries.

## Phase 2 — determine whether a bounded Android compatibility runtime is viable

Before writing another downloader, use upstream Android Bionic and its dynamic linker documentation, the device-matching vendor metadata, and the actual ELF to assess:

1. Real interpreter ABI and namespace rules, APEX/VNDK search paths, `DT_NEEDED` and `dlopen` references, symbols, RELRO, and startup requirements.
2. Android property-service calls, Binder/HIDL/service-manager hooks, android logging, wakelocks, `/proc`/`/sys` assumptions, init rc, and any GNSS-specific calls. Do not assume HALs are needed merely to upload SSP firmware; test the narrowest role of `lhd` first.
3. Whether the existing Ubuntu/Fedora Nuxel userspace can host a **separate** Android/Bionic execution environment with a reduced config and minimal, whitelisted BBD endpoints, or whether absent Android IPC makes that approach impractical.
4. Explicitly inspect all currently known dangerous controls: `GpioNStdbyPath=/sys/class/sec/gps/GPS_PWR_EN/value` and `GpioNPowerPath=/sys/class/sec/sensorhub/mcu_power`. Do not let `lhd` invoke those controls in an initial trial: an apparently read-only launch could trigger writes or resets. Instrument or restrict its access first; if that restriction prevents function, treat this as a measured engineering decision.
5. Implement unit/integration tests for ELF analysis and isolation before any on-device trial. Keep a bounded watchdog and complete logs for diagnosis; do not set the vendor daemon to autorestart until a safe first boot and handshake are established.

Only with reviewed syscall/device access, a verified stock ABI, and operator approval should you run one isolated, bounded `lhd` trial on the handset. Collect evidence of a **real kernel BBD handshake and the MCU responding**. Do not run a daemon on the Mac/x86_64 host as if it could communicate directly with the phone.

## Phase 3 — alternative native downloader if and only if justified

If matching `lhd` cannot be made runnable without disproportionate Android framework dependencies, continue the native glibc downloader already in the current first-light branch. Do not rewrite from zero.

1. Verify the receiver/transmitter TL frame format, escape handling, fragmentation, sequence wrap, CRC-8 rejection, RPC IDs, retransmission rules, reliable ACK and NACK semantics, upper bounds, length validation, timeouts, and IRQ ordering from the exact Samsung kernel and matching `lhd` implementation. No inferred protocol constant is trusted without evidence.
2. Your recent patch verifier is read-only. Retain its bounded reads, identity checks, strict patch validation, and firmware upload refusal until the state machine is proven.
3. Build a **deterministic simulated peer** for transcript replay, ACK/NACK/timeout/sequence errors, unexpected replies, CRC failures, interrupted upload, duplicate reply, and recovery without write-after-failure. Validate AArch64 build and run host sanitizers. If a test can only pass with fabricated "ACK" packets, label it simulated, not hardware proof.
4. Establish whether the hub has a recoverable cold-boot communication window and whether existing kernel power/suspend behavior allows uninterrupted transaction. Read, inspect and reason first. The older repository logs describe SPI MISO returning `0xFF` after suspend and a documented reset hazard; never defeat safety by cycling power GPIO blindly.
5. Seek approval for **one** bounded live handshake trial only when the exact behavior and recovery have been reviewed. Increase privileges and enable writes incrementally after actual peer responses. Do not upload firmware or write hub memory without confirmed ACK boundaries and a known-good backup/recovery path.
6. Only after the patch download is accepted and firmware service successfully starts should you enable sensor streams using verified kernel interfaces. No invented BBD packet handlers or fictitious progress.

## Phase 4 — demonstrate real SSP readiness and motion data

Do not declare success until all of these pass, with timestamps, raw logs and physical manipulation:

- MCU reliably enumerates and positively acknowledges its actual firmware/bootstrap state.
- Real accelerometer data changes with X/Y/Z physical tilts; stationary gravity magnitude and axis signs are plausible after scale/mount corrections.
- Gyro values move in response to physical rotation, settle toward stationary baseline, and retain consistent timestamp/axis mapping.
- `ssp_down` clears genuinely and sample availability survives a reasonable idle period, device sleep/wake and full reboot.
- The existing `nuxel-orientationd` consumes actual samples; preserve all seven modes. Prove every portrait/landscape/reverse pose using real gravity and correct compositor/touch mapping; manual and locked modes regress zero tests.
- Document actual bus errors, retry caps, loss/recovery of sensor service, and kernel errors. Do not use mocks or forced screen transforms as proof of automatic mode.
- Maintain accurate capability status until complete.

## Deliverables and decisions

Commit a reviewed implementation on a dedicated continuation branch with:
- `reports/SSP-FIRST-LIGHT-CONTINUATION.md`: git & kernel provenance, current live state vs archive differences, exact hashes and traces, dependency graph, runtime trial results, firmware protocol proof, risk controls, reproducer.
- A reproducible host runtime staging recipe (no bundled proprietary binaries; owner-local extraction), unit tests and target builds, and the smallest reversible service/daemon/driver changes that actually fix the problem.
- Explicit `PASS / PARTIAL / BLOCKED` status per step and a complete reproduction command for each verified result.
- Any required flashing change as a **separate, reviewed, owner-approved** operation with verified A-only layout and TWRP/ADB rollback. **Never** combine a speculative new firmware protocol with an unattended boot flash.
- A human-readable blocker report if the matching runtime cannot be obtained or hardware does not reply. Specify precisely what external artifact, protocol observation, or hardware evidence is missing, what was tried, and what remains safe.

Make progress independently where evidence allows. Prioritize a correct, reusable implementation over merely reporting "no firmware" or asking to write a new one. But no amount of persistence justifies guessing around an unknown OEM ACK, an unsafe GPIO, or an incompatible runtime.
