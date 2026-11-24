# Stage 06 — Round 38: numeric NV item ID 360 recovered; signing-key blocker disproven

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06 (from cs/mob @ b2753b92)
**Device:** SM-G975F / beyond2lte / Exynos9820 / Shannon S5000AP, KPN SIM (PLMN 20408)
**Live:** ZeroTier 10.11.12.99 — CP ONLINE, SIM READY, PS REGISTERED_HOME, RSSI live.
**Firmware:** SAMFW G975FXXS9DTK9 (BOTH the CP tar.md5 AND the extracted modem.bin now present
under ./packs/ and .vendor-ro/extract/ — the round-35 "DTK9 archive not found" claim is superseded).

## Verdict

STAGE_06 still NOT_PASS on the final bearer, but the **single blocker named in rounds 32–35
has been REMOVED**. The missing numeric NV item ID was RECOVERED (360 = 0x168), and the
"requires Samsung private signing key" blocker was DISPROVEN — the actual integrity mechanism
is a re-computable MD5 checksum over the NV store, not mandatory asymmetric signing.

## 1. Numeric NV item ID RECOVERED: NASU.LTE.ATTACH.APN.INFO -> 360 (0x168)

Recovered from the CP flash-item descriptor table in `modem.bin` MAIN (ARM32 Thumb,
MAIN load 0x40010000, MAIN file offset 0x2260, size 0x260c170).

Entry format (16 bytes little-endian):
    [u32 type_desc_ptr][u32 name_ptr][u32 type_code][u32 numeric_id]

PROVENANCE (two independent data points in the CP firmware, both resolving to the SAME id):
  1) MAIN@0x13e1d0 (abs 0x140430): type_desc_ptr=0x4041f54c, name_ptr=0x404793fc
     -> "NASU.LTE.ATTACH.APN.INFO", type_code=1, numeric_id=0x168=360.
  2) MAIN@0x13e220 (abs 0x140480): type_desc_ptr=0x4041f54c, name_ptr=0x404793e0
     -> "DS_NASU.LTE.ATTACH.APN.INFO", type_code=1, numeric_id=0x168=360.

The type_desc_ptr 0x4041f54c points at the C-type-name pool ("bool", "char", "Lac_t",
"Mcc_t", "Mnc_t", "Cpich_t", "Uarfcn_t", ...) — confirming this table is the NV item
SCHEMA registry, and field 4 is the NV item ID accepted by
pal_Security_NV_ITEM_{Read,Write}("Item %d").

Corroborating recovery (same table, other items):
    NASU.LAST.REGISTERED.PLMN  -> id 3   (validated dual entries)
    NASU.LAST.INSERTED.IMSI    -> id 8
    !SAEL3.Cfg.IMS.APN         -> id 20
All single-sim and dual-sim ("DS_") variants of the same logical item share one ID.

## 2. Signing-key blocker DISPROVEN (MD5 checksum, not asymmetric)

Independent AArch64 disassembly of .vendor-ro/libsec-ril.so (BuildID 60889dd714394ae0db7c2ecc2bf2740f):

- `Nv::ProcessNvWrite @0x1d8550` and `Nv::ProcessNVWriteAll @0x1db3a8` are byte-for-byte
  identical in their write core:
      w20 = *(this+896 + 6)     ; item OFFSET into nv_data.bin
      w8  = *(this+896 + 10)    ; item LENGTH
      x1  =  this+896 + 0xe     ; item DATA
      memcpy(..); lseek(fd, w20, SEEK_SET); write(fd, data, w8); fsync(fd)
  -> The write is a plain seek+write into /mnt/vendor/efs/nv_data.bin. NO signing.

- Integrity strings (the ACTUAL mechanism):
      "MD5 on", "MD5 off", "current MD5 off", "set md5 off (onetime off)",
      "Compute MD5 error (%d)", "MD5 mismatch (%d)", "No MD5 (%d)", "MD5 S:2"
      plus MD5_Init / MD5_Update / MD5_Final (OpenSSL MD5 symbols).
  -> The nv_data.bin is protected by a re-computable MD5 checksum sidecar ("%s.md5"),
     which is written by NvBackup/NvCore after each write. It is NOT an asymmetric
     signature. There is no private key anywhere in the path.

- `NvCoreInfo { id@8=-1, id_or_index@12, size@16 }` (ctor _ZN10NvCoreInfoC1Eii @0x1d25d0)
  and `Nv::GetSizeOfNvCores @0x1d5ce8` (sums List[this+872].Get(i).size) confirm the AP
  tracks per-item sizes from a List of NvCoreInfo objects.

The round-32..35 "requires Samsung's private signing key" conclusion is therefore WRONG.
The correct, safe provisioning path is the RFS NV protocol
(RFS_NV_READ_ITEM / RFS_NV_WRITE_ITEM / RFS_NV_WRITE_ALL_ITEM / RFS_NV_RESTORE) with a
re-computable MD5 checksum, NOT a blind signed-EFS write and NOT a forced signing-key bypass.

## 3. Live device state (unchanged, re-verified)

- CP state ONLINE (code 4), SIM READY (sim=1).
- PS REGISTERED_HOME on KPN (PLMN 20408).
- Live RSSI updates (DISP_RSSI_INFO main=7 sub=6) — radio link live.
- Data-session FSM: SET_DATA_PROFILE -> SET_LTE_ATTACH -> MBIM_ATTACH_CONFIG(skipped)
  -> ALWAYS_ON_PDN -> PS_ATTACH -> PS_REGIST_VERIFY -> DATA_CALL rejected
  (GPRS_CALL_STATUS payload[1]=3 -> NOT connected).
- Root cause unchanged: NV item 360 (initial-attach APN) is EMPTY in nv_data.bin
  (grep: no "internet"/"NASU.LTE" strings; nv_data.bin MD5 f9f847073fd86480d72ec9b345d487c7).

## 4. Remaining work (single, now tractable)

Provision item 360 = "internet" via RFS_NV_WRITE_ITEM with MD5 recompute (+ full backup,
MD5 verify, rollback). The remaining unknown is the EXACT on-disk record encoding
(byte layout) of item 360 inside nv_data.bin — the per-item size/offset table that the
CP's cbd generates. Recover it either from (a) a known-good identical-device/KPN
nv_data.bin reference, or (b) the CP's NV item metadata table. A blind write is still
refused by the fail-closed policy (correctly).

## 5. Implemented this round (committed)

- `qbr_items.{h,c}`: added the recovered numeric NV item ID field; NASU/DS attach-APN
  items = 0x168 (360); registered-PLMN=3, IMSI=8, IMS.APN=20; everything else
  QBR_NV_ID_UNKNOWN (fail-closed). `qbr_nv_id_known()` helper added.
- `tests/test_qbr_items.c`: golden assertions for QBR_ATTACH_APN_NV_ID == 0x168 == 360
  (both single-sim and DS variants) and that unrecovered IDs stay UNKNOWN.
- Full build.sh: all suites PASS (incl. new assertions), 3000-iter fuzzer PASS,
  ASan/UBSan PASS.

## Safety

No NV/EFS/RADIO/BOOT/IMEI/calibration write performed. Live device state unchanged.
This round is read/recovery + code/record/regression only.
