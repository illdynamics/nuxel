# SSP-06_00 — Firmware Compatibility Validation

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06 preflight
**Scope:** Independent validation that the embedded sensor-hub firmware matches
the physical controller and board configuration, prior to any physical execution.

## 0. Verdict

`COMPATIBILITY = PROVISIONALLY_CONFIRMED (structural + identity match)`

The firmware is a **structural and identity match** to the target controller. It is
NOT, however, an end-to-end *proven* match: a matching ASIC identifier does not by
itself establish that the decoded record stream is byte-correct for this exact die
stepping, board wiring, or power domain. That final proof can only come from the
post-download GetVersion handshake in the bounded physical trial. This report
separates what is independently proven from what remains runtime-confirmable-only.

## 1. Independent firmware identity (recomputed this mission)

Source: `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h`
(the `r_os` container selected for beyond2lte by `get_patch_version()` in the deployed kernel).

Header fields decoded directly from the `<...>` text and the `<Blob=...>` hex:

| Field | Value | Verified |
|---|---|---|
| FormatVersion | `0x00010003` | YES (independent decode) |
| Crc (header) | `193` | YES |
| BlobLength | `438895` | YES (decoded blob length == declared) |
| AsicVersion | `0x004775B0` | YES |
| ChangeList | `4294967295` | YES |
| PatchLevel / PostPatchLevel | `0` / `1` | YES |
| Name | `bcm_sensorhub_a1` | YES |
| Type | `Application` | YES |
| PatchAddress (entry) | `0x00800161` | YES |
| Blob SHA-256 | `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d` | YES (recomputed) |
| Record count | `479`, all tag `0xF1` | YES (recomputed) |
| First F1 destination | `0x00800000` | YES (recomputed) |

The SHA-256 was recomputed from the embedded C array by an independent script
(`/tmp/verify_fw.py`) and matches the committed Stage 05_16 value byte-for-byte.

## 2. Controller identity vs firmware identity

| Dimension | Controller (live) | Firmware (embedded) | Match |
|---|---|---|---|
| Part | `BCM47752KUB1G` (live `mcu_name`) | BCM47752 (`bcm_sensorhub_a1`, ASIC `0x4775b0`) | CONFIRMED |
| ASIC version | ASIC `0x004775B0` (header) | — | CONFIRMED (self-consistent) |
| Board | beyond2lte / EXYNOS9820 | `r_os` container (beyond-specified) | CONFIRMED |
| Stock build | `G975FXXS9DTK9` (SM-G975F) | lhd hash `6362e80d…` (DTK9) | CONFIRMED |

Live identity was re-collected this mission: `mcu_name=BCM47752KUB1G`,
`mcu_rev=BR0121080900,BR010`, `nuxel_hub_diag = mcu_probe=1 shutdown=1 resetting=1`
(hub probed but no firmware downloaded — the expected clean-baseline state).

## 3. Container structure integrity

- The patch is a **record stream**, not a contiguous load image: `479 × F1`, where each
  `F1 = LE32 destination + data bytes`. The first destination is `0x00800000`; the entry
  point `0x00800161` lies *after* the first write destination, confirming the downloader's
  critical property that `PatchAddress` is the entry point, NOT the first data address.
- Record parser enforces: tags restricted to `F0..F5`, LE16 length in-bounds, F1 body ≥ 5
  bytes (dest + ≥1 data), total parsed offset == blob length, runaway-loop cap (2000).
- Header `Crc=193` is a container header CRC (not a file-system CRC); the load-integrity
  guarantee at the transport layer is per-record reliable ACK + TL CRC-8, not the header CRC.

## 4. Load-address and entry-metadata assumptions (what compatibility does NOT yet prove)

1. **Load addresses are MCU-host-specific.** `0x00800000..0x0080xxxx` destinations and the
   `0x00800161` entry are assumed to be the BCM47752 RAM/ROM window. The firmware *encoding*
   is self-consistent and ASIC-matched, but the physical RAM window for this die step is
   confirmed only by the vendor board support package, not by an independent measurement.
2. **ASIC match ≠ stepping match.** `0x004775B0` matches the lhd comparison slot
   (`low24(ASIC)==0x4775b0`), but the full application binary is `bcm_sensorhub_a1`; a
   stepping-specific later revision would be indistinguishable until runtime.
3. **No independent die-level inventory** exists in this repo beyond `mcu_name`/`mcu_rev`.
   The `mcu_rev=BR0121080900,BR010` string is live evidence but is not cross-referenced to a
   Broadcom stepping table (proprietary, unavailable).

## 5. What would disprove compatibility at runtime

The bounded trial's **post-download GetVersion (request id 0 → response id 3)** must return
`w0 == 0x4775b0` for the application to be accepted. If the ROM/bootloader rejects any
MemoryWrite (NACK), or the post-start GetVersion returns a mismatched ASIC, that is a
hard, evidence-backed compatibility failure — and it is exactly the signal the downloader
is built to detect and surface (distinct exit codes: `VERSION_MISMATCH`, `TRANSFER_REJECTED`,
`APP_START_MISSING`).

## 6. Conclusion

Compatibility is **structurally and identity confirmed**, with the final die/board
acceptance delegated to the post-download GetVersion check inside the bounded,
owner-authorized trial. A matching ASIC alone is explicitly NOT treated as full
compatibility; this report records the residual, runtime-only items as open until the
trial's confirmation handshake.
