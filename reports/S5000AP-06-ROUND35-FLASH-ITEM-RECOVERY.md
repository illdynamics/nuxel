# Stage 06 — Round 35: CP flash-item recovery + initial-attach APN key recovered

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06 (from cs/mob @ b2753b92)
**Device:** SM-G975F / beyond2lte / Exynos9820 / Shannon S5000AP, KPN SIM (PLMN 20408)
**Live:** confirmed via ZeroTier 10.11.12.99 — radiod 1e2df783… active, CP ONLINE,
SIM READY, PS REGISTERED_HOME, rmnet0..7 DOWN (no default EPS bearer).

## Verdict

STAGE_06 LTE still NOT_PASS (same evidence-locked blocker, now with the exact
key recovered). This round materially changed the "unrecoverable QBR item-ID
table" conclusion from round 34: **the exact persistent initial-attach APN
storage key was recovered from the matching CP firmware.**

## 1. Firmware extracted and parsed (new tooling-level evidence)

- `./packs/SAMFW…/CP_…tar.md5` → `modem.bin.lz4` → `modem.bin` (46,062,992 B).
- TOC container sections decoded (name/load/size/crc/id):
  - BOOT   load 0x40000000 size 0x1e40
  - MAIN   load 0x40010000 size 0x260c170  (ARM32 Thumb CP OS)
  - VSS    load 0x47800000 size 0x5df6a0
  - NV     load 0x45600000 size 0x100000
  - OFFSET size 0x85600
- MAIN file offset = 0x37000 (solved via SIPC_GPRS_LTE_ATTACH_APN_INFO
  cross-reference at file 0x15c7079 → load 0x40647028).

## 2. Flash item name tables fully recovered

- **PDNMGR_FLASH_*** (14 items, file 0x6c3684 region) — INT_DDS, IMS_DDS,
  CLASS1/3_BACKOFFTIMER_VALUE, LTE_VZW_EXCESSIVE_PDN_MAX_CONN(_T),
  LTE_VZW_EXCESSIVE_PDN_WAIT_TIME, LTE_VZW_INTERNET_ATTACH_ENABLED,
  EQUIV_PLMN_LIST/COUNT, VOICE_DOMAIN_PREF, DOMESTIC/ROAMING_DATA_STATUS,
  IMS_OVER_WLAN_STATUS.
- **SAECOMM_FLASH_*** (24 items, file 0xebb3bc region) — incl. the
  LTE_INTERNET_ATTACH_ENABLED boolean, DETACH_RE_ATTACH_REQUIRED_SUPPORT, etc.
- Source path embedded at 0x6c3220: `../../CALPSS/LteL3/PdnMgr/PDNMGR/Code/…`
  (confirms `PDNMGR_FlashItems.h`).

Each flash item is a {group, ds-name, PDNMGR-id} triple, e.g.
`!SAEL3.Cfg.INTERNET_ATTACH_ENABLED` → `PDNMGR_FLASH_LTE_VZW_INTERNET_ATTACH_ENABLED`.

## 3. THE definitive initial-attach APN storage key (recovered)

`NASU.LTE.ATTACH.APN.INFO`  (dual-sim variant `DS_NASU.LTE.ATTACH.APN.INFO`)

- File offsets 0x46b640 / 0x46b65c (BOOT) and 0x6c31c4 / 0x6c31e0 (MAIN).
- Referenced from the flash-item descriptor table at file 0x171e1c alongside
  handler base 0x4041f54c.
- This is the QBR persistent item the modem reads during LTE INITIAL ATTACH to
  build the default EPS bearer. It is EMPTY in the running modem (rounds 25–34),
  which is exactly why GPRS_CALL_STATUS stays state=3.

## 4. NV subsystem structure recovered

- NV_ITEM0..35 (file 0x41aa9c…0x460564): RF/calibration region
  (`CAL.LTE.CAL_ITEM*`, `ET.COMMON.TX_ET_*`) — PROTECTED, not writable.
- NV_ITEM_Read/Write (0x210542e / 0x5ca4f1), NV_READ/WRITE (0x21a887c / 0x219dcfc),
  NV_READ_RSP/WRITE_RSP/WRITE_NTF — the CP↔AP NV transfer protocol (RFS path).

## 5. Remaining blocker (single, specific, unchanged)

Provisioning `NASU.LTE.ATTACH.APN.INFO` in QBR NV requires Samsung's private
signing key OR a known-good reference image; the QBR container is signed and a
blind write is prohibited by the fail-closed RFS/NV policy (correctly). Numeric
QBR item IDs + signed on-disk encoding remain unproven and are NOT guessed.

## 6. Implemented this round (committed)

New read-only typed module `qbr_items.{c,h}` + golden-vector/safety tests
`test_qbr_items.c`:

- Records the recovered QBR item names (APN / CONFIG / NETWORK / PROTECTED classes).
- `qbr_item_lookup()` is fail-closed (unknown/guessed names → NULL).
- `qbr_class_protected()` deny-classifies RF/cal, IMEI, and unknown.
- Wired into `build.sh` (builds with `-Werror`, full suite + fuzzer + ASan/UBSan).

## 7. Tests

`./build.sh` → all suites PASS (9 prior suites + new test_qbr_items), 3000-iter
fuzzer PASS, ASan/UBSan PASS.

## 8. Safety

No NV/EFS/RADIO/BOOT/DTB/DTBO/IMEI/calibration write performed. Live device
state unchanged. The new module is read-only reference data with no write path.

## Completion

LTE internet: NOT COMPLETE. Single external dependency: QBR signed NV write for
`NASU.LTE.ATTACH.APN.INFO`. Everything recoverable from local assets without the
signing key is now implemented and tested.
