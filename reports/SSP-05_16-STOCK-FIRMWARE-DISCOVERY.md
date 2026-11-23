# SSP-05_16 — Stock Firmware Discovery

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Result

The matching stock sensor-hub firmware is **embedded in the deployed kernel itself**
as a C array, served by the `/dev/bbd_patch` char device. No external `vendor/bin/hw/lhd`
binary was required to establish the firmware identity, record count, or protocol
identifiers — the evidence is fully recoverable from GPL kernel source that is now
present in this repository plus the hash-bound lhd reverse-engineering already checked
in under `tools/s10plus/ssp-runtime/`.

## 1. Firmware identity (authoritative, computed this mission)

Source: `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h`
(the `r_os` build selected for beyond2lte by `get_patch_version()` in `ssp_dev.c`).

Decoded `<Blob=...>` hex:

| Field | Value |
|---|---|
| FormatVersion | `0x00010003` |
| Crc (hdr) | `193` |
| **BlobLength** | **438895** bytes |
| **AsicVersion** | **`0x004775B0`** |
| ChangeList | 4294967295 |
| PatchLevel / PostPatchLevel | 0 / 1 |
| CustomerVersion | None |
| Name | `bcm_sensorhub_a1` |
| Type | Application |
| **PatchAddress (entry)** | **`0x00800161`** |
| **Blob SHA-256** | **`56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d`** |
| **Record count** | **479**, all tag `0xF1` (LE32 dest + data) |

This matches the native `nuxel_bbd_flash.c` expectations exactly
(`EXPECT_ASIC=0x004775B0`, `EXPECT_BLOB_LEN=438895`, `EXPECT_ENTRY=0x00800161`),
and its header comment "479 x F1 records" is independently re-derived.

## 2. Where the firmware lives / how it is served

`bbd.c`:
- `static unsigned char bbd_patch[]` = the `r_os/bbd_patch_file_beyond.h` C array.
- `bbd_patch_read()` selects among `bbd_patch_old` (hw_rev <20), `bbd_patch_new_old`
  (20..23), `bbd_patch` (current), chosen by `get_patch_version(ap_type, hw_rev)`.
- Served read-only via `/dev/bbd_patch` (major 236 minor 3) with EOF-rewind when the
  file position passes the end.

## 3. Stock lhd (proprietary userspace) — recovered, hash-bound, NOT in-tree

The owner-acquired `vendor/bin/hw/lhd` from **G975FXXS9DTK9** has SHA-256
`6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`. It is a
proprietary binary, intentionally kept owner-local (`packs/`, gitignored) and NOT
redistributed. Its behavior is recovered via these already-committed, hash-bound
artifacts:

- `tools/s10plus/ssp-runtime/inspect_lhd_init.py` — ELF64 static reader; records
  dispatch addresses, RPC id map, state machine, transport CRC/framing semantics.
- `tools/s10plus/ssp-runtime/replay_lhd_response.py` — Unicorn emulation of the matched
  AArch64 instructions for the RPC decoder/callback (synthetic inputs only).
- `tools/s10plus/ssp-runtime/test_lhd_response.py` — 30+ unit tests asserting the
  recovered protocol semantics.

## 4. Provenance / build identity

- `firmware/s10plus/camera-stock-DTK9.json` records the owner AP re-extraction of
  `G975FXXS9DTK9` (archive SHA-256 `bf00219f90f7bfc7612cbabf10992fdad79dd7a6dcc3e279b64817ed444dc68d`).
- The camera/firmware files in that manifest are camera-only (fimc_is_*, setfile_*);
  the sensor-hub *patch* is kernel-embedded (per above), and the *lhd* daemon is the
  owner-local `packs/` asset.

## 5. Compatibility

- Device build: `G975FXXS9DTK9` (SM-G975F, beyond2lte, EXYNOS9820) — exact match.
- Controller: BCM47752 (live `mcu_name=BCM47752KUB1G`), ASIC `0x4775b0`.
- Firmware: `bcm_sensorhub_a1`, Application type, entry `0x00800161`.

## 6. Remaining proprietary dependency (documented, not guessable)

The RPC id map (GetVersion request=0/response=3, MemoryWrite=5, StartScratch=46,
ServiceStart=55) is recovered from the hash-bound lhd analysis. The only thing not
derivable without the live binary executing is the exact `GPS_PWR_EN` rise → ROM-ready
settle delay and any further GNSS-solution RPCs beyond patch download; those remain
documented as OUT OF SCOPE for Stage 06 (which is firmware-download only).
