# SSP-05_13 — ROM First-Light Result

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## Status: `ROM_GETVERSION_PASS = FALSE` (no authorized trial was run this session)

## 1. What was NOT performed

No new physical ROM probe was executed this session.  Reasons:
- No device is attached (`adb devices` returned empty).
- The proposed first-light mechanism (assert `GPS_PWR_EN`) is **not
  safety-validated** (see PHYSICAL-TRIAL-DECISION.md §C/D).

## 2. Prior authorized trial (05_12) — unchanged, still the latest evidence

After the corrected symmetric cold-cycle (0028), the ROM probe returned:
```
autobaud sent (32 x 0x80)   -> no GetVersion reply (packets=0)
autobaud sent (36 x 0x80)   -> no GetVersion reply (packets=0)
exit 3 (ROM_HANDSHAKE_TIMEOUT)
```
Transport diagnostics: MISO `0xFF` (SPI slave not driving), `HSI_CTRL=FFFFFFFF`,
SSI TX overflow (`Nread 65535`).  Consistent with the GNSS core power-gated by
`GPS_PWR_EN` = LOW.

## 3. Root-cause refinement (this session)

The prior `05_12` attributed the dead SPI to `GPS_PWR_EN` being "the chip power
gate".  This session refines that: `GPS_PWR_EN` is the **GNSS domain** enable
(specifically gpg0-2, not gpg4), while the sensor-hub MCU is gated by the
regulator alone.  The ROM GetVersion probe targets the **GNSS boot-ROM**, so it
requires `GPS_PWR_EN` HIGH — which the stock kernel leaves LOW and delegates to
`gpsd`.  The conclusion (chip power-gated) is correct; the precise signal
identity is now corrected.

## 4. Acceptance criteria (from prompt §9) — NONE met yet

- Genuine hardware RX: NOT achieved (MISO all-ones).
- ROM framing validated: NOT achieved (no reply).
- Response integrity / GetVersion payload / identity: NOT achieved.
- Raw response preserved: N/A (no response).
- Nuxel & GNSS health verified: N/A (no device attached this session).

## 5. What remains

A single blocker: the safe assertion of `GPS_PWR_EN` (gpg0-2), which requires
the vendor sequence / datasheet evidence enumerated in
PHYSICAL-TRIAL-DECISION.md §D.  No success is claimed from synthetic protocol
tests or SPI TX counters.
