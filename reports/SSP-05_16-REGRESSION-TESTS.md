# SSP-05_16 — Regression & Fault-Injection Tests

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Result — ALL PASS

All offline suites re-run clean after the version-id fix.

## 1. Coverage inventory

| Concern | Covered by |
|---|---|
| Correct protocol identifiers (id 0 vs id 3) | `test_getversion_request_response_id_separation` (NEW) |
| ROM/runtime protocol separation | `test_rom_probe_*never_writes_firmware`, `check_protocol_replay` |
| Invalid framing | `test_rx_wrong_crc_all_bit_positions`, replay suite |
| CRC errors | CRC table + inv bit flip tests + replay |
| Partial reads / short reads | `test_rx_partial_transfer_and_short_read`, fragmentation replay |
| Empty reads / no reply | `test_reliable_rpc_no_reply_times_out` |
| Timeouts | `test_reliable_rpc_no_reply_times_out`, `test_rom_probe_never_writes_firmware` (→ TIMEOUT) |
| Unexpected/unrelated responses | `test_ack_only_does_not_invoke_version_callback`, replay |
| Transport contention | `test_two_instances_independent` |
| Service shutdown / cleanup | `test_reliable_rpc_cancelled` |
| Failed initialization | `test_entity_version_mismatch`, `test_header_decode_edge_cases` |
| Recovery cleanup | patch_free + finally semantics (nuxel_lhd.py) |
| Repeated service startup | `test_seq_rollover`, reentrancy test |
| Firmware identity mismatch | `test_identity_version_mismatch`, `test_verify_embedded_patch` |
| RPC field boundaries | `test_rpc_field_boundaries` |

## 2. Firmware-download isolation (safety)

`test_rom_probe_never_writes_firmware` and `test_rom_probe_success_never_writes_firmware`
prove the `--rom-probe` path emits ONLY `RPC_GET_VERSION` (id 0) and never
`RPC_MEM_WRITE`/`RPC_START_SCRATCH`/`RPC_SERVICE_START` — via the
`NUXEL_BBD_TEST_INSTRUMENT` RPC-id recorder. The ROM-only diagnostic cannot initiate
firmware download or app start.

## 3. Replay (lhd response decoder, host-side)

`check_protocol_replay.py --decoder nuxel_bbd_download` exercises ACK/NACK framing,
extended lengths, malformed RPC rejection, CRC failure, and stream resync with simulated
bytes. `test_lhd_response.py` (Unicorn) additionally asserts the recovered lhd version
callback only for id 3.
