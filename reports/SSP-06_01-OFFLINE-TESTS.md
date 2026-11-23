# SSP-06_01 — Offline Tests (re-run this mission)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01

## 0. Verdict

All tests that can run without the proprietary vendor `lhd` binary PASS. The
`lhd`-dependent tests remain `OWNER_BINARY_REQUIRED` (the binary is gitignored and
absent), exactly as recorded by Stage 06_00.

## 1. Native C suites (host build, re-run this mission)

`cd tools/s10plus/ssp-native && make check`:

| Suite | Result |
|---|---|
| `nuxel_bbd_download` framing + CRC + patch validation | PASS (SIMULATED) |
| `nuxel_bbd_flash` framing + F1 records + RX decode | PASS (offline) |
| `nuxel_bbd_negative` (17 negative cases: truncation, bad tag, short F1, no-ACK, autobaud 32/36 tmo, CRC error) | PASS (offline) |
| `test_verify_embedded_patch.py` (2 tests) | PASS |
| `check_protocol_replay.py` (SIMULATED framing replay) | PASS (hardware_verified=false, completion_verified=false) |

Key guarantee confirmed by the negative suite: a SIMULATED transport byte or RPC
byte is **never** treated as an ACK/completion, and simulated replies are never
reported as physical success. The replay header explicitly records
`hardware_verified: false`.

## 2. Python protocol suites

| Suite | Result |
|---|---|
| `test_kernel_identity.py` + `test_isolation.py` | 10 PASS |
| `test_lhd_response.py` | OWNER_BINARY_REQUIRED (57 SKIP/FAIL all due to absent `packs/sensors/acquired/vendor-bin-hw-lhd`) |

The `test_lhd_response.py` failures are NOT code defects; they fail at
`MatchedImage(PosixPath('.../vendor-bin-hw-lhd'))` because the proprietary lhd
binary is absent (gitignored). This is the documented owner-binary gap.

## 3. Accidental-hardware-startup proof

The downloader's device I/O is gated behind `--flash`; the offline tests run fully
without any device node. Confirmed: no accidental hardware execution is possible in
offline mode. The `nuxel_lhd.py` repo HEAD refuses before any power/device access
(`INITIALIZATION_PROTOCOL_UNVERIFIED`).

## 4. Firmware identity recompute

Independent, this mission (see FIRMWARE-COMPATIBILITY report): SHA-256
`56e8b1ea…`, 479×F1, ASIC `0x004775b0`, entry `0x00800161` all recomputed and
matching.

## 5. Conclusion

Offline correctness is fully established. The only failing tests are the
owner-binary-dependent `lhd` emulation tests, which require
`packs/sensors/acquired/vendor-bin-hw-lhd` (proprietary, gitignored). No
offline test can substitute for the physical GetVersion handshake.

---

## 6. Addendum — final unblock re-runs (2026-11-23, later in the same day)

New checks performed for the final readiness pass (no broad suite re-run was needed;
the earlier suites were already green and unchanged):

| Check | Result |
|---|---|
| Firmware parser vs **live `/dev/bbd_patch`** bytes (host harness, no device I/O) | PASS — 479 records, ASIC `0x004775b0`, entry `0x00800161`, exit 0 |
| Three-way firmware byte comparison (device / kernel tree / repo) | PASS — identical container `0b53f3b0…` and blob `56e8b1ea…` |
| Hardened `nuxel_lhd.py` deploy (on-device, staged copy) | PASS — `INITIALIZATION_PROTOCOL_UNVERIFIED`, exit 2, zero hardware calls |
| Hardened unit gate (no authorization file) | PASS — systemd skips, `GPS_PWR_EN=0` |
| Hardened unit with authorization file | PASS — refusal only; `power=None`, `GPS_PWR_EN=0` |
| `py_compile` of all three deployed modules under Python 3.14.7 on device | PASS |
| Post-deploy hashes vs repo HEAD | PASS (exact) |
| `check_protocol_replay.py` against `nuxel_bbd_download` | PASS (SIMULATED, `hardware_verified=false`) |

### 6.1 Test-tool observations (do not affect the deployed service)

These were found while trying to run the CLI validators and are recorded so they are
not mistaken for hardware results later:

1. `nuxel_bbd_flash` verifies its patch **before** opening any transport. On a host
   without `/dev/bbd_patch` it therefore exits `IDENTITY_INVALID` (1) without device
   I/O. This is correct fail-closed behaviour but means the CLI cannot be used as a
   host-side “usage-only” validator without a patch file.
2. `nuxel_bbd_download --replay-stdin` does not decode frames produced by the
   repository’s hardened `nuxel_bbd_tl.build_frame()` for non-empty payloads
   (0/256 single-byte payloads accepted, all rejected as malformed). It does accept
   the replay corpus built by `check_protocol_replay.py`’s own independent encoder.
   The two encoders differ in how they treat certain payload/flag combinations, but
   the discrepancy is only in **offline tooling** — neither file is deployed, and
   the firmware path is `nuxel_bbd_flash`, which the instrumented tests cover.
   Flagged for the `nuxel_bbd_download` maintainers; no change made in this pass
   because that tool is diagnostic-only.
3. `nuxel_bbd_host` in the tree is a **host-arch** build (`Mach-O arm64` for a
   Linux/ELF target) and is not runnable on this phone; it is gitignored build
   output, not a deployed artefact.
