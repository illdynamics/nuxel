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
