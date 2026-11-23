# SSP-06_00 — Offline Validation Results

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06 preflight
**Scope:** Execute all protocol, firmware-integrity, negative-case, and
fault-injection tests offline (no physical firmware execution), and prove the
proposed execution path cannot accidentally run during ordinary startup.

## 0. Verdict

`OFFLINE = ALL_RUNNABLE_TESTS_PASS`; one suite is owner-proprietary-binary-gated
(documented, not a failure of validation).

## 1. Test execution (this mission)

All suites re-run clean.

### 1.1 Native C suites (`tools/s10plus/ssp-native`)

```
make -C tools/s10plus/ssp-native check
  PASS nuxel_bbd_download framing, CRC, and patch validation
  PASS nuxel_bbd_flash framing + F1 records + RX decode (offline)
  PASS nuxel_bbd_flash negative cases (offline)
  OK   test_verify_embedded_patch (2 tests)
  OK   check_protocol_replay (SIMULATED framing replay, passed)
```

`test_nuxel_bbd_negative.c` (17 tests) coverage:
- F0..F5 malformed/truncated, header decode edge cases, identity/version mismatch
- RPC field boundaries, TL oversize payload, RX wrong-CRC all bit positions
- RX ACK/NACK classification, no-reply timeout, NACK, cancelled, seq rollover
- RX reentrancy, partial transfer/short read, two-instance independence
- **ROM-probe-never-writes-firmware** (and -success variant) — proves `--rom-probe`
  emits ONLY `RPC_GET_VERSION(0)` and never MemoryWrite/StartScratch/ServiceStart
  (via `NUXEL_BBD_TEST_INSTRUMENT` RPC-id recorder)
- **getversion-request-response-id-separation** — id 0 does not classify, id 3 does

### 1.2 Python suites (`tools/s10plus/ssp-runtime`)

```
python3 -m unittest test_kernel_identity test_isolation
  Ran 10 tests ... OK
```

`check_protocol_replay.py --decoder nuxel_bbd_download --summary` →
`{"passed": true, "hardware_verified": false, "operation_completion_verified": false}` —
explicitly and correctly refuses to claim hardware verification.

### 1.3 Independent firmware identity recomputation

`/tmp/verify_fw.py` recomputed SHA-256 `56e8b1ea…`, 479×F1 records, ASIC `0x004775B0`,
entry `0x00800161`, first-dest `0x00800000` — all matching the committed values.

## 2. Test suite requiring the owner-local proprietary binary (documented gap)

`test_lhd_response.py` (58 Unicorn-emulation tests) and the full
`inspect_lhd_init.py` static reader require the owner-local binary at
`packs/sensors/acquired/vendor-bin-hw-lhd` (SHA-256 `6362e80d…`), which is
**gitignored and not present in this environment** (`/packs/` absent, per `.gitignore`
line 111). This is a deliberate, documented ownership boundary, not a validation
failure:

- The RPC-id map those tests assert is **already committed as structured evidence** in
  `inspect_lhd_init.py` (the `rpc_ids` dict, dispatch VAs, state-machine labels, and
  confidence levels), hash-bound to the pinned lhd SHA-256.
- The suite cannot be re-executed here without the owner re-supplying the binary; the
  committed artifacts remain the authoritative, reproducible evidence.

This gap is recorded in the acceptance JSON as `lhd_emulation_tests: OWNER_BINARY_REQUIRED`.

## 3. Proof that the execution path cannot accidentally run during ordinary startup

Four independent guards, all verified this mission:

1. **Gate flag.** `nuxel_bbd_flash.c` performs device I/O only under `--rom-probe` or
   `--flash`. With neither flag it does read-only identity verification and exits
   `EXIT_SUCCESS_VERIFIED` without opening `/dev/ttyBCM` or writing any control string.
2. **Mutual exclusion.** `--flash` and `--rom-probe` are rejected together
   (`EXIT_USAGE`).
3. **Repo-HARDENED service.** `services/nuxel-gnss/src/nuxel_lhd.py run_session()`
   (HEAD) returns a hard refusal `blocker=INITIALIZATION_PROTOCOL_UNVERIFIED` **before**
   any power acquisition, device open, or control write. The on-device deployed copy is
   an older revision that does assert power; the repo version is the one gated for any
   approved trial. (Deployed md5 `4e562874…` vs repo HEAD — discrepancy documented.)
4. **No auto-start of the downloader.** `nuxel_bbd_flash` is not installed as a service,
   not referenced by any systemd unit, and does not self-execute; the on-device fixture
   for it is absent (confirmed this mission: `find / -name nuxel_bbd_flash` returns
   nothing). Ordinary boot cannot trigger firmware download.

## 4. Conclusion

All offline protocol, integrity, negative-case, and fault-injection tests that can run
without the owner-local proprietary binary **PASS**. The runnable tests explicitly and
correctly refuse to claim hardware verification. The execution path is proven incapable
of accidentally running during ordinary startup.
