# SSP-05_16 — LHD Static Analysis

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Object under analysis

Stock `vendor/bin/hw/lhd` from the matched SM-G975F build `G975FXXS9DTK9`.

- SHA-256: `6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`
- ELF64 AArch64 (little-endian).
- Proprietary; owner-local (`packs/`, gitignored); NOT executed on live Nuxel.

## 1. Method (safe, offline)

- `inspect_lhd_init.py` — read-only ELF64 segment/relocation reader; refuses any other
  hash; records dispatch addresses and per-range SHA-256 receipts.
- `replay_lhd_response.py` — Unicorn emulation of the matched instructions for decoder/
  callback ranges; synthetic inputs; instruction budget; fail-closed on unknown code.
- `test_lhd_response.py` — unit suite (30+) asserting recovered semantics.

## 2. Confirmed behaviors (static + emulated)

- Entry state machine (17 states, VA 0x389fc dispatch, table VA 0xdfc4) — see
  `SSP-05_16-VENDOR-STARTUP-SEQUENCE.md`.
- RPC map: request id 0 (GetVersion), response id 3 (3×LE32), id 4 (LE32), id 5
  (MemoryWrite), id 59 (multi-field), id 46 (StartScratch), id 55 (ServiceStart).
- Transport: CRC-8 nibble-swap, ESC/SOP/EOP framing, reliable ACK/NACK, duplicate
  suppression OFF by default.
- Patch parser: tags F0..F5, F1 = LE32 dest + data, body limit 950 per chunk.

## 3. Inferred (multiple observations, not directly asserted on-wire)

- The GNSS solution RPCs are distinct from the sensor-hub patch/version RPCs; full GNSS
  position decode is beyond the recovered map (proprietary gpsd layer), OUT OF SCOPE
  for Stage 06 (firmware download only).

## 4. Unknown / not proven

- Physical ROM/application response identity end-to-end (no live capture).
- Exact `GPS_PWR_EN` rise → ROM-ready settle delay (Broadcom datasheet).
- Memory-write acceptance on real hardware (emulation only).

## 5. Confidence model

| Claim | Status |
|---|---|
| GetVersion request id = 0 | CONFIRMED (lhd + unit test) |
| GetVersion response id = 3 (3×LE32) | CONFIRMED (lhd + unit test) |
| MemoryWrite id = 5 | CONFIRMED |
| StartScratch id = 46, ServiceStart id = 55 | CONFIRMED |
| Patch = 479 × F1 records, ASIC 0x4775b0 | CONFIRMED (kernel + independent decode) |
| Handshake gating (`bcm477x_hello`) | CONFIRMED (GPL source + live journal) |
| ROM-only GetVersion reachable without MCU wake | INFERRED FALSE (dead helper = zero callers) |
