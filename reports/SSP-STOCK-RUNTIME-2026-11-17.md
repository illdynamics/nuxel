# SSP matched stock runtime — November 17, 2026

The missing Samsung runtime is recovered and executes on Nuxel. **Sensors are
not recovered:** twelve baseline and twelve final accelerometer/gyro readings
remain zero. No reboot, flash, firmware transmission, GPIO write, partition
mount, persistent service installation, or host hardware exposure occurred.
This supersedes the missing-runtime dependency in the earlier recovery report.
The owner's authorization to recover/reflash if necessary remains recorded;
no boot change was technically indicated by these results.

## Matched acquisition — ARCHIVE_REPRODUCED

The supplied AP is
`AP_G975FXXS9DTK9_CL20034833_QB35905779_REV01_user_low_ship_meta_OS10.tar.md5`.
Its SHA-256 is
`bf00219f90f7bfc7612cbabf10992fdad79dd7a6dcc3e279b64817ed444dc68d`.
The Samsung MD5 trailer verifies when hashing all bytes preceding its checksum
line, including the build metadata. Hashing only `original_tar_file_size`
initially mismatched; both attempts are retained, with the correct prefix
check in [archive integrity](evidence/ssp-stock-20261117/archive-integrity-full-prefix.json).
The trailer is an integrity check, not independent authentication of Samsung.

All four acquired vendor anchors match byte-for-byte:
[hash comparison](evidence/ssp-stock-20261117/anchors.json). Vendor fingerprint:
`samsung/beyond2ltexx/beyond2:10/QP1A.190711.020/G975FXXS9DTK9:user/release-keys`.
System and vendor come from the same owner-held AP; SDK is 29. This replaces
the earlier mixed Halium/userdebug provenance for this trial.

Extraction used host `tar`, `lz4`, Android sparse conversion, and read-only
`debugfs` commands. `simg2img` rejected pipe input (seeking error), so system
conversion used a bounded chunk reader writing sparse host output. The
conversion helper remains `/tmp/nuxel-ssp-stock-20261117/unsparse_stream.py`.
No phone partitions were mounted. The initial collector rejected the valid
Android name `android.frameworks.schedulerservice@1.0.so`; its allowlist is
fixed and regression-tested.

The original audit now reports 28 available files, no missing interpreter,
no wrong-architecture ELF, and **zero unresolved DT_NEEDED entries**:
[audit](evidence/ssp-stock-20261117/audit-vndk/ssp-runtime-audit.md).
The expanded collection additionally retains VNDK-29 variants and canonical
Bionic/APEX files. [Complete source/hash manifest](evidence/ssp-stock-20261117/stock-manifest.json).
Proprietary files are owner-local at
`/Users/wicked/.local/share/nuxel-ssp/G975FXXS9DTK9-20261117`, outside Git.
Raw images remain under `/tmp/nuxel-ssp-stock-20261117`.

## Hardware-denied trials — LIVE_VERIFIED

Phone: root SSH at the supplied address, kernel
`4.14.253-gf7194c1d15ed-dirty #3`, November 14 build. Captures carry UTC bounds;
[final phone check](evidence/ssp-stock-20261117/final-phone.txt) records the
session time and service state. Fresh helpers were built with the AArch64 GCC
toolchain; the probe is static and the logging shim has no DT_NEEDED entries.
[Helper hashes](evidence/ssp-stock-20261117/helper-hashes.json).

Each trial had its own output directory and was preceded by an actual probe.
The probes verified UID/GID 65534, no effective capabilities, NoNewPrivs,
read-only runtime, and denied BBD, GPIO, block-device and host filesystem paths.
No host Binder or network namespace was exposed. Runtime and trial scripts
were staged only under the phone's `/run`; no vendor daemon remains running.

| Trial | Result |
|---|---|
| Initial matched runtime | Loads and parses config; exits 255 because sandbox `/tmp/nv` did not exist |
| Private lock/log directories added | Reaches absent `/no-hardware/bbd-control`; asserts, SIGSEGV in trace, wrapper exit 1 |
| Stock namespaces and VNDK-29 | Same BBD assertion/SIGSEGV; wrapper exit 1 in 0.573 seconds |

The final trial uses unmodified stock `ld.config.29.txt` as `ld.config.txt`,
canonical runtime APEX files, and `/vendor/lib64` as the only LD_LIBRARY_PATH.
The trace confirms stock configuration loading and libraries loaded from
`/system/lib64/vndk-29` and `vndk-sp-29`. This is stronger evidence than the
initial broad-library-path trial, but does not prove complete Android service
compatibility. `defaultServiceManager() is null`, several stock configuration
keys are rejected by lhd, and AF_INET socket creation returns EACCES. Those
messages do not prevent it reaching the BBD open in these trials.

Evidence: [final probe](evidence/ssp-stock-20261117/probe-vndk/stdout.log),
[daemon output](evidence/ssp-stock-20261117/trial-vndk/stdout.log),
[syscalls](evidence/ssp-stock-20261117/trial-vndk/syscalls.log),
[trial manifest](evidence/ssp-stock-20261117/trial-manifest.json).
Do not interpret the deliberate missing-device assertion as an ABI crash or
successful hardware initialization. No fake hardware response was supplied.

## Hardware/protocol review and next dependency

The final trace proves lhd tries to open `/sys/bbd/lk_enable` and both configured
power paths before it opens BBD control. Every such open failed inside the
sandbox. The current kernel implements `lk_enable` as a driver watchdog
control and `mcu_power` as a real regulator/GPIO operation. Exposing the full
host `/sys` would therefore change hardware behavior, even with reset retries
set to zero. Preserve the deny policy for these paths.

The native downloader still cannot serve as a fallback: its `transact()`
counts any received TL packet rather than requiring a matched operation ACK;
full ACK/NACK/retry/abort behavior is not established. Its `--download`
refusal remains unchanged. The source verifier still reproduces the embedded
897113-byte patch hash; this is not physical ROM or handshake evidence.

The next missing evidence is a matched BCM47752 initialization/transport
reference or trace establishing response, ACK/NACK, timeout, retry, abort,
and power sequencing, followed by a bounded device-specific hardware trial
and recovery review. The supplied archive resolves acquisition; requesting
another runtime archive would be wrong. The sandbox cannot produce real hub
responses, and repeating this crash cannot establish that protocol. No
hardware-write approval is requested on the basis of these incomplete facts.
A boot flash would not resolve that missing evidence.

## Validation and remaining acceptance

- Recovery toolkit: 14 tests passed, including image-link containment/cycles,
  truncation, flattened APEX mapping and Android `@` dependency collection.
- Isolation contract: 7 tests passed, including stock namespace selection.
- Runtime audit: 6 passed, 1 skipped on macOS.
- Native simulations / patch verifier: passed.
- Orientation and GNSS: 81 pytest tests passed. An initial unittest invocation
  with `-S` could not import pytest; that failed invocation is retained.
- Final live capture: 12/12 zero vectors for each sensor; no failed systemd
  units. The final generic `nuxel-orientation` query used the wrong unit name;
  [follow-up verification](evidence/ssp-stock-20261117/orientation-service.txt)
  confirms `nuxel-orientationd.service` is active and running. See [samples](evidence/ssp-stock-20261117/live-final.json).

Physical six-face correlation, gyro turns, automatic rotation, suspend/resume
and sensor cold/warm boot acceptance remain NOT VERIFIED. No UI change was
made. The pre-existing edit to `SSP-FIRST-LIGHT-RECOVERY-2026-11-17.md` and the
owner's untracked firmware folder were preserved.
