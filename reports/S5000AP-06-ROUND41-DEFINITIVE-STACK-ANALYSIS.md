# Stage 06 — Round 41: Definitive native-stack analysis (verified, not research-only)

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06 (HEAD ee6aac61)
**Device:** SM-G975F / beyond2lte / Shannon S5000AP, KPN SIM (PLMN 20408)
**Live:** ZeroTier 10.11.12.99 — CP ONLINE(4), SIM READY(ds_detect=1), PS REGISTERED_HOME,
RSSI live, DATA_CALL rejected with GPRS_CALL_STATUS payload[1]=3 (no default EPS bearer).

## Objective

Round 41 was an *execution* pass: re-verify every recovered contract against the actual
vendor binaries and the live device, and resolve the §2 question
"does IPC41_GPRS_LTE_ATTACH_APN_INFO (sub=20) genuinely provision initial-attach APN or
merely report it". No NV/EFS/RADIO/BOOT/IMEI write was performed. No test was weakened.
Full host suite re-run clean (build+test OK, 3000-iter fuzzers, ASan/UBSan).

## Definitive findings (each independently re-derived this round)

### F1. IPC41_GPRS_LTE_ATTACH_APN_INFO (sub=20) is REPORT-ONLY; SetLteAttachProfile is the only TX.
`nm -D .vendor-ro/libsec-ril.so` shows exactly ONE `IpcTx*Attach*` exporter:
`IpcProtocol41::IpcTxSetLteAttachProfile` @0x320238 (201-byte frame, main=13 sub=20 type=3).
There is NO `IpcTxSetInitialAttachApn`/`IpcTxSetAttachApn` wire exporter. Live log confirms
sub=20 never arrives as a CP->AP request; the only sub=20 traffic is AP->CP (type=3), and
the CP's own GPRS_LTE_ATTACH_APN_INFO is a type=3 NOTIFICATION (report), matching the
command-map classification.

### F2. DataCallManager::DoSetInitialAttachApn @0x22bad8 is a STUB (no-op).
Disassembly:
```
22bae4:  cmp w8, #0x2        ; compare a debug-level flag
22bae8:  b.lt 22bb14          ; return early if < 2
22baf4:  ...                  ; only a __android_log_buf_print (debug logging)
22bb14:  mov w0, wzr          ; return 0
22bb18:  ret
```
The function performs NO provisioning and no FMT write. This closes the §2 question with a
negative: the RIL's `DoSetInitialAttachApn` cannot be the provisioning trigger on this build.
Corroborates round-18 (`SetLteAttachPdnList`/`SetLteAttachtype` = stubs).

### F3. SetLteAttachProfile flag decode is byte-exact 3/4 (NOT 1/2 "define").
`IpcTxSetLteAttachProfile` @0x320238:
```
320270: mov w9, #0xc9            ; total_len = 201
320284: mov w9, #0x140d          ; header bytes: main=13(0x0d), sub=20(0x14)
320294: orr  w9, wzr, #0x3       ; 3
320298: csinc w8, w9, wzr, ne    ; (flag & 1) ? 3 : 4
3202a8: strb w9, [sp+22]         ; cmd_type = 3 (NOTIFICATION)
3202ac: strb w8, [sp+23]         ; payload[0] = 3 or 4
```
The vendor NEVER emits flag 1/2. The committed `fmt_tx_set_lte_attach_profile` matches this
byte-for-byte. Therefore `SetLteAttachProfile` applies the profile IN-MEMORY only; it cannot
persist NV item 360 across a CP reset. This is the live-observed reason DATA_CALL fails:
the CP's persistent initial-attach APN stays empty.

### F4. cbd is a CP BOOTLOADER, not an NV item server.
`.forensics/cbd` (BuildID aa0233da..., 494 KB) contains only "Send MAIN", "bootloader info",
"Wait CP_REQ_NV_DATA", "/mnt/vendor/efs/nv_data.bin", "/mnt/vendor/efs/fsm_data.bin",
"Total_Checksum"/"Verify_Checksum". It loads the modem boot image and pushes nv_data.bin to
the CP during boot via CP_REQ_NV_DATA. The item-level RFS NV serving (`Nv::ProcessNVRead` @0x1d8a10
/ `ProcessNvWrite` @0x1d8550) lives in libsec-ril.so, not cbd. radiod's efs_nv.c is the correct
native replacement for that runtime serving path.

### F5. Live nv_data.bin is the CP QBR item-name/type table; item 360 value is EMPTY.
Pulled /mnt/vendor/efs/nv_data.bin (1,048,576 bytes; MD5 f9f847073fd86480d72ec9b345d487c7).
It contains the full CP QBR symbol table (PDNMGR_GET_PDNCONTEXT_APN, PDNMGR_SET_PDNCONTEXT_APN,
PMPM_*, SAEMM_Attach*, sm_SetApn, etc.). No "internet"/"NASU.LTE.ATTACH.APN.INFO" value record is
present. Stored MD5 sidecar (c665d458...) does NOT match the file (f9f84707...) -> sidecar is
stale on this EFS image, so the vendor MD5 gate is not currently exercising a pre-verified
pre-image. Any write must therefore recompute the sidecar (efs_nv_update_checksum_sidecar) after
a full backup + rollback copy.

## Resolved §2 contract

- IPC41_GPRS_LTE_ATTACH_APN_INFO (sub=20): **report-only** (F1, F2). It does NOT provision.
- Real CP-originated provisioning trigger: the RFS NV_WRITE (opcode 0x15/0x01) with the CP-supplied
  offset+length, serviced by the RIL (and now by radiod/efs_nv). The CP has NOT issued one
  spontaneously in the entire live-log history (only 13x DELETE_ALL_VIS boot markers), because no
  runtime RIL has ever requested it on Nuxel.
- The persistent initial-attach APN can ONLY be populated by: (a) a CP-originated NV_WRITE for
  item 360 (requires a trigger the vendor RIL stubs out), or (b) pre-provisioning nv_data.bin
  before/at CP boot (the vendor carrier path, which cbd would then load). Neither has occurred.

## Remaining single, tractable step (unchanged from round-40, now fully proven)

Provision item 360 = "internet" into /mnt/vendor/efs/nv_data.bin via the corrected RFS NV write
contract, using the CP-supplied (offset,length) — or via a carrier-style nv_data.bin pre-image —
then trigger CP reload (detach/reattach or CP reset via the existing stage-04 guard). Both require
a controlled provisioning operation with backup + MD5 verify + rollback, NOT a research pass.

## Safety

No write performed. Live device unchanged: CP ONLINE, SIM READY, PS REGISTERED_HOME, RSSI live.
wlan0/usb0/ztly5zthnf/SSH/ZeroTier/TWRP all intact. ./wonqed4real NOT created.
