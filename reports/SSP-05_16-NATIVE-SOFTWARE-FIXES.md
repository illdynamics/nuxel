# SSP-05_16 — Native Software Fixes

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Summary

One demonstrated correctness defect fixed (and regression-covered), plus documentation
corrections and a prepared (not-applied) transport-arbitration guard. ZERO-ANDROID-DEPS
architecture preserved; no Android HAL/framework introduced; no kernel rebuild/flash.

## 1. FIXED — GetVersion request/response RPC id conflation

File: `tools/s10plus/ssp-native/nuxel_bbd_flash.c`

- **Before:** `on_pkt()` treated `RPC_GET_VERSION (0)` as the *response* id. RPC id 0
  is the *request*; a real firmware version reply is RPC id 3 (3×LE32).
- **After:**
  - `#define RPC_GET_VERSION 0` (request, empty body)
  - `#define RPC_GET_VERSION_RESPONSE 3` (response, 3×LE32)
  - `on_pkt()` sets `got_version`/`version_w0` only for id 3.
- **Regression:** `test_getversion_request_response_id_separation` asserts id 0 does
  NOT classify and id 3 does (with correct LE32 `version_w0`).

## 2. FIXED — test fixtures that encoded the same bug

- `tests/test_nuxel_bbd_flash.c test_rx_decode()`: fixture now uses id 3 for the version
  response (comment corrected).
- `tests/test_nuxel_bbd_negative.c test_rom_probe_success_never_writes_firmware()`:
  child now replies with id 3 in the payload.

## 3. Verified NOT a defect (documented)

- `nuxel_control.py GPS_POWER_RAIL = "/sys/devices/virtual/sec/gps/GPS_PWR_EN/value"`
  resolves (via symlink) to gpio145; live-verified both `/sys/class/sec/gps/GPS_PWR_EN`
  and `/sys/devices/virtual/sec/gps/GPS_PWR_EN` exist. Correct.
- `RPC_SENSOR_RESPONSE = 33` is correct (kernel enum: SensorRequest=32, SensorResponse=33).
  The adjacent comment "SensorResponse=34" is stale text only.

## 4. Prepared (not applied) — advisory transport lock

Recommendation folded into the Stage 06 downloader: take an exclusive `flock` on
`/dev/ttyBCM` and refuse to start if held, so no two services interleave TL framing.
Deferred: not required to complete Stage 05; reversible userspace-only.

## 5. Deployed-vs-repo reconciliation (recommendation, not applied)

The on-device `/usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py` (md5 `4e562874…`) is an older
revision that asserts GPS_PWR_EN at boot. Repo HEAD refuses power/device access until a
verified protocol+timing contract exists. Deploy the repo-HARDENED version before any
approved Stage 06 trial.

## 6. Regression receipts

```
make -C tools/s10plus/ssp-native OUT=/tmp/nuxel-ssp-fix check
  PASS nuxel_bbd_download framing, CRC, and patch validation
  PASS nuxel_bbd_flash framing + F1 records + RX decode (offline)
  PASS nuxel_bbd_flash negative cases (offline)  [incl. new id-0/id-3 test]
  OK   test_verify_embedded_patch (2 tests)
  OK   check_protocol_replay (SIMULATED framing replay, passed)
```
