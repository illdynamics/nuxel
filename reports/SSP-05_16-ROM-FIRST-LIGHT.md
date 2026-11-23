# SSP-05_16 — ROM First Light

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## Status: NOT_RUN (and not runnable as a standalone ROM-only probe)

No physical ROM GetVersion was performed, because this mission established (source-proven)
that a standalone boot-ROM GetVersion is not reachable through `/dev/ttyBCM` while the
kernel `bcm477x_hello()` MCU handshake gates all SSI I/O, and the raw-SSI ROM helper
(`bcm477x_rpc_get_version()`) is dead code with zero callers.

## Genuine first light therefore folds into the Stage 06 firmware-download trial

A valid, attributable, reproducible ROM/identity confirmation requires (in order):
1. MCU rail on, MCU out of reset.
2. MCU_REQ→MCU_RESP handshake success.
3. Firmware patch download (479 × MemoryWrite RPC id 5) + StartScratch(46) +
   ServiceStart(55).
4. Post-download GetVersion: request id 0 → response id 3 (3 × LE32), w0 == ASIC `0x4775b0`.

When authorized, the *first light* evidence is the id-3 GetVersion response validating
controller identity — captured, framed-CRC-validated, attributable, and reproducible.

## Prepared but not executed (correct, safe state)

- `--rom-probe` now emits autobaud + RPC id 0 and decodes the id-3 reply correctly
  (fixed this mission).
- It remains read-only; it cannot write firmware or start the app (proven by
  instrumentation test).
