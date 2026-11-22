# SSP-05_14 — Vendor Power Sequence

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

Carries forward SSP-05_13-VENDOR-POWER-SEQUENCE.md (correct, evidence-backed).

Recovered stock sequence (source-verified):

1. vdd_mcu_1p8 rail ON (LDO21M, regulator core / SSP driver).
2. GPS_PWR_EN = HIGH (gpg0-2) — performed by userspace gpsd, NOT kernel.
3. GNSS boot-ROM starts, waits for autobaud (32 × 0x80).
4. MCU_REQ/RESP wake handshake (bcm477x_hello()).
5. GetVersion RPC → valid framed reply.

Missing in Nuxel: step 2 (GPS_PWR_EN assertion), deferred to userspace gpsd
which is absent in Nuxel.  Kernel-side ROM protocol is correct; it cannot reach
live silicon while GPS_PWR_EN is LOW.

Vendor timing values present in source:
- MCU_RESP poll budget ≈ 100 ms (MAX_RESP_CHECK_COUNT 100).
- MCU_REQ re-toggled every 20 iterations (1 ms deassert/reassert).
- GetVersion poll: 20 ms granularity, delta > 1000 loop bound.
- GPS_PWR_EN rise→ROM-ready delay: NOT in tree (Broadcom datasheet / gpsd
  disassembly required; documented uncertainty, not invented).
