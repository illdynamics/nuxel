# SSP — Stage 03 Checkpoint (Vendor Protocol Parity + Cold-Start Contract)

**Date:** 2026-11-22. **Stage:** 03 of 00–08. **Hardware:** untouched (offline).

## What was done
1. Located and recomputed the pinned firmware identity from the recovered
   header/build file
   `kernel/s10plus/.build/src/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h`.
2. Reconstructed the full SSI/TL/RPC framing, CRC-8, flag/record grammar and the
   RPC command set from `bbd_rpc_lh.c`, `bcm_gps_spi.h`, `bcm_gps_regs.c`,
   `ssp_dev.c`, `ssp_i2c.c`, `ssp_bbd.c`, `bcm_gps_spi.c`, `bbd.c`, plus the
   native mirrors `nuxel_bbd_download.c` / `nuxel_bbd_flash.c`.
3. Reused the existing analyzers (`inspect_lhd_init.py`, `replay_lhd_response.py`,
   `check_protocol_replay.py`, `nuxel_bbd_*` tests) — no third protocol stack.

## Deliverables written
- `reports/SSP-VENDOR-PROTOCOL-PARITY.md` — source references + exact semantics.
- `reports/SSP-COLD-START-TIMELINE.md` — measured vs hypothesis split.
- `tools/s10plus/ssp-runtime/corpus/build_golden_frames.py` + `corpus/out/*` —
  reproducible offline golden-frame corpus (normal + faulty).
- `tools/s10plus/ssp-runtime/corpus/README.md`.

## Recomputed facts (deterministic)
- r_os ASIC `0x004775B0`, `BlobLength` 438895, entry `0x00800161`,
  IEEE CRC32 `0x93d35bb4`, vendor `Crc=193` (0xC1, **not** IEEE).
- Blob = **479 × F1 records** (477×916, 1×510, 1×16 bytes), exact EOF,
  first dest `0x00800000`.
- `p_os` (429079) and `q_os` (438983) are distinct, rejected older variants.

## Key separations (no false READY)
- Transport reliable-ACK ≠ RPC operation-level acceptance (§3.2 parity report).
- `mcu_resp=1` ≠ meaningful SPI response (it is a GPIO handshake line).
- SPI `0xFF` = electrical idle, not a protocol reply.
- Autobaud length **32 (kernel)** vs **36 (lhd VA 0xdfe4)** — still unresolved.

## Chosen architecture
Single-owner **kernel-coordinated** firmware load, triggered only from the
bounded operator-initiated cold-cycle recovery path; every placeholder sleep
(120/150/300 ms) must be replaced by an evidence gate before the hardware stage.

## Status
- Offline PASS (identity + framing + replay reproducible). **No hardware PASS.**
- Next stage: 04 (offline test/build/BOOT preflight) — requires resolving the
  autobaud 32-vs-36 reconciliation and converting sleeps to polls first.
- No firmware writes, no flash, no rail/GPIO/reset, no device changes.
