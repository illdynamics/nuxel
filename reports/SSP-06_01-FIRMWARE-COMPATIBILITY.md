# SSP-06_01 — Firmware Compatibility Validation (independently recomputed)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01

## 0. Verdict

`COMPATIBILITY = STRUCTURALLY_AND_IDENTITY_CONFIRMED` (runtime acceptance
delegated to trial). Every identity fact was **recomputed this mission** from the
kernel-embedded header, not taken from prior reports.

## 1. Independent recomputation (this mission)

Source: `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h`

Ran `tools/s10plus/ssp-native/verify_embedded_patch.py` plus an independent
record-walk. Results:

| Field | Recomputed value | Mission-reported | Match |
|---|---|---|---|
| ASIC version | `0x004775b0` | `0x004775B0` | ✅ |
| PatchAddress (entry) | `0x00800161` | `0x00800161` | ✅ |
| Blob length | `438895` | `438895` | ✅ |
| Blob SHA-256 | `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d` | `56e8b1ea…` | ✅ |
| Blob CRC-32 (IEEE) | `93d35bb4` | n/a | ✅ (self-consistent) |
| Record count | `479`, all tag `0xF1` | `479 F1` | ✅ |
| First F1 destination | `0x00800000` (distinct from entry) | same | ✅ |
| Record-walk offset == blob length | `True` (438895 == 438895) | — | ✅ (clean stream) |

### Note on the two hashes

There are **two** SHA-256 values in the verifier, and they are different on
purpose:

- `blob_sha256 = 56e8b1ea…` — SHA-256 of the `<Blob=…>` hex (the actual firmware
  record stream that gets downloaded). This is the mission's firmware hash.
- `kernel_export_sha256 = 0b53f3b0…` — SHA-256 of the full C string-literal
  payload plus its terminating NUL (the `r_os` C-array export as the kernel sees
  it). This is a *container* hash, not the firmware hash.

Both are correct for their respective definitions. The firmware identity is
`56e8b1ea…`.

## 2. Controller vs firmware identity

| Dimension | Controller (live) | Firmware | Match |
|---|---|---|---|
| Part | `BCM47752KUB1G` (live `mcu_name`) | BCM47752 (`bcm_sensorhub_a1`, ASIC `0x4775b0`) | ✅ |
| ASIC | `0x004775B0` | self-consistent | ✅ |
| Board | beyond2lte / EXYNOS9820 | `r_os` container (beyond) | ✅ |
| Stock build | `G975FXXS9DTK9` | lhd hash `6362e80d…` | ✅ |

## 3. What compatibility does NOT yet prove (runtime-only)

1. **Load addresses** (`0x00800000..`) are assumed to be the BCM47752 RAM window
   for this die stepping; confirmed only by vendor BSP, not measurement.
2. **ASIC match ≠ stepping match.** Full application `bcm_sensorhub_a1`; a
   stepping-specific revision is indistinguishable offline.
3. **Physical acceptance** — a matching ASIC does not establish the decoded record
   stream is byte-correct for this exact die/board/power domain. That is the
   post-download GetVersion check, which only the bounded physical trial performs.

## 4. What would disprove compatibility at runtime

- MemoryWrite NACK → `TRANSFER_REJECTED`
- post-start GetVersion mismatch → `VERSION_MISMATCH`
- no post-download GetVersion → `APP_START_MISSING`

These are distinct, evidence-backed exit codes, already implemented.

## 5. Conclusion

Structural + identity compatibility is independently confirmed. Final die/board
acceptance is delegated to the post-download GetVersion handshake in the bounded,
owner-authorized physical trial. A matching ASIC alone is NOT treated as full
compatibility.
