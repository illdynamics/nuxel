# SSP first-light continuation — 2026-11-16

## Status

**BLOCKED: no real motion data.**  This continuation made no firmware, GPIO,
BBD-control, boot, partition, or service-configuration write.  Auto rotation
must remain `blocked_sensor_unavailable`; manual rotation remains the fallback.

| Stage | Status | Evidence / reproducer |
|---|---|---|
| First-light source recovery | PASS | `git show 3d34aef8`; continuation branch is `codex/ssp-first-light-continuation-20261116` |
| Kernel embedded patch identity | PASS (host source) | command below; this is not a live device-node read |
| Android runtime static audit | BLOCKED | 28 unresolved direct dependency occurrences and missing `/system/bin/linker64` |
| Matching Android build/runtime | BLOCKED | no owner-supplied matching `system`/`vendor`/APEX extraction in this workspace |
| Current handset baseline | BLOCKED | read-only SSH to configured `nuxel` endpoint timed out before authentication |
| BBD version reply / validated ACK | NOT TESTED | no live transaction was made |
| Patch upload / service start | REFUSED | downloader deliberately rejects `--download` |
| Physical accel/gyro and auto rotation | FAIL / NOT TESTED | latest directly recorded result is 2026-11-16 first-light: zero vectors and `ssp_down=true`; it is not asserted current |

## Provenance reconciliation

The checkout initially was `feature/v0.8.7-beta-live-fixes` at `5659c20a`.
The purported first-light commit is present locally as `3d34aef8` on
`codex/ssp-first-light-20261116`; this work branches from it.  The supplied
continuation package and other top-level prompt files were already untracked
and were left untouched.

The archive described by the package is not present as a usable
`nuxel-main (2).zip` in this workspace.  Relative to that archive's documented
snapshot, the current tree contains the later first-light commit and its
`reports/SENSORS-FIRST-LIGHT.md`, `reports/SSP-CONTINUATION-20261116.md`,
`tools/s10plus/ssp-native/Makefile`, and downloader test; the archive did not.
The archive's four acquired vendor artifacts do match their documented hashes:
`lhd` `6362e80d…761dfe`, sensorhub HAL `de0110…cd5718`, Exynos HAL
`44b26a…e2ef0`, and `lhd.conf` `1660da…edd46bc4`.

The last hardware report (`SENSORS-FIRST-LIGHT.md`) recorded kernel
`4.14.253-gf7194c1d15ed-dirty #3`; older #48/#78 reports are historical only.
This continuation could not confirm today's kernel or nodes because the
read-only SSH connection timed out.  No connection failure is interpreted as
a sensor failure.

## Patch identity, independently reproduced from kernel source

`verify_embedded_patch.py` decodes only C string literals in
`r_os/bbd_patch_file_beyond.h`.  It never opens `/dev/bbd_patch`.  It proves:

| Field | Value |
|---|---|
| ASIC | `0x004775b0` |
| decoded blob length | `438895` |
| patch address | `0x00800161` |
| header `Crc` | `193` (`0xc1`), algorithm unknown |
| decoded blob IEEE CRC-32 | `0x93d35bb4` |
| kernel-export bytes | `897113` |
| kernel-export SHA-256 | `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72` |

The source string data is 897112 bytes; C array export includes its trailing
NUL, yielding the 897113-byte hash.  The header CRC is intentionally not
compared to IEEE CRC-32.

Reproduce:

```sh
make -C tools/s10plus/ssp-native clean check
python3 -S tools/s10plus/ssp-native/verify_embedded_patch.py \
  kernel/s10plus/.build/src/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h
```

## Runtime blocker and safe staging recipe

The host-only audit passed all seven package tests but returns exit status 3
against this tree: the three ELF seeds have 28 unresolved dependency
occurrences and no `/system/bin/linker64`.  This is expected until an exact,
owner-provided Android runtime is supplied.  Do not mix generic Bionic,
VNDK, APEX, or Android versions, and do not put Bionic in host library paths.

Once an owner extracts the exact matching Android system/vendor/APEX tree,
stage it on the host only:

```sh
python3 -S NUXEL_SSP_CONTINUATION_PACK/ssp_runtime_audit.py \
  --repo-root . --android-root /owner/path/matching-android-root \
  --report-dir /tmp/ssp-audit-with-stock \
  --stage-runtime /tmp/ssp-isolated-runtime
```

A static PASS is only a prerequisite for a separately reviewed Bionic
isolation design.  Before any future trial, establish exact build fingerprints,
recursive library closure/APEX namespaces, syscall and binder/property needs,
and deny access to both `GPS_PWR_EN` and `mcu_power`.  The configured lhd
contains those paths and historic reports tie the GPS control to hard resets.

## Implemented guard

`tools/s10plus/ssp-native/verify_embedded_patch.py` is a stdlib-only,
host-only verifier for the kernel source representation.  Its tests cover
literal handling and bad metadata; `make check` runs them together with the
existing simulated TL/CRC/download-parser tests.  It creates no runtime,
does not contain proprietary blobs, and does not execute vendor binaries.

## Precise external blockers

1. An owner-supplied, exact Android build matching the acquired vendor daemon
   is needed to establish whether an isolated lhd process is viable.
2. A reachable handset and an operator-approved, bounded read-only baseline
   are needed to establish present kernel/node/sensor state.
3. A source-verified protocol transcript including response, ACK/NACK,
   retransmission, and upload boundaries is required before any BBD write.

Until all three are satisfied, firmware upload, power control, auto-restart,
and flashing remain out of scope.
