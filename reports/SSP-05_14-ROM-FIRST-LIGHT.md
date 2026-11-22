# SSP-05_14 — ROM First-Light

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking
**Status:** ROM_GETVERSION_PASS = NOT_RUN (no new trial performed this session)

No GPS_PWR_EN assertion / ROM probe was executed, consistent with the safety
boundary (Section 10).  The prior 05_12/05_13 finding stands: with GPS_PWR_EN=0,
MISO reads 0xFF (chip power-gated) and GetVersion returns nothing.

This session delivered the 0029 regulator-core fix and a verified normal Nuxel
boot.  ROM first light remains gated by the separately-authorized GPS_PWR_EN
assertion (S0→S1), which requires the vendor-sequence evidence.
