# Stage 06 — Round 43: CP-firmware SET_APN_INFO (sub 27) byte-exact trace

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06
**Device:** SM-G975F / beyond2lte / Shannon S5000AP (G975FXXS9DTK9)
**Sources:** ./packs CP modem.bin (46,062,992 B) + .vendor-ro/libsec-ril.so (60889dd7)

## Objective

The Round-43 mission named `IPC41_GPRS_SET_APN_INFO = 27` as the primary lead.
This round recovered the command from the AUTHORITATIVE CP firmware itself
(not from the AP RIL), producing a byte-exact protocol specification below.

## 1. CP firmware extraction (verified this round)

`./packs/SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac/CP_..._tar.md5` -> modem.bin.lz4
-> modem.bin (46,062,992 B, Samsung "TOC" container).

TOC layout (independently re-parsed, matches Round 42):

| seg   | file_off  | load_addr  | size      |
|-------|-----------|------------|-----------|
| BOOT  | 0x420     | 0x40000000 | 0x1e40    |
| MAIN  | 0x2260    | 0x40010000 | 0x260c170 |
| VSS   | 0x260e3e0 | 0x47800000 | 0x5df6a0  |
| NV    | 0x0       | 0x45600000 | 0x100000  |
| OFFSET| 0x7aa00   | 0x0        | 0x85600   |

MAIN is raw 32-bit ARM code (vector table `7cf09fe5` = LDR pc at offset 0).

## 2. CP SIPC GPRS command table (authoritative)

Recovered from MAIN `.data.rel.ro` @0x4034a9e0 (src file
`VARIANT/HIUVar/MCD/HIC/SIPC/Code/Src/sipcGprsCmdHandle.c`). Each entry is
16 bytes: `{const char* src_file; u32 cmd_id; const char* fmt; const char* proc_name}`.

| cmd_id      | proc_name                        | decode format string (CP-authored) |
|-------------|----------------------------------|------------------------------------|
| 0x05130800  | sipcProcGprsDefinePdpContextSet  | `Rx Define PDP Context SET (mode=%s, cid=%d, PDP type=%s, dComp=0x%X, hComp=0x%X, PCSCF req=0x%X, PCO req=0x%X)` |
| 0x05160102  | sipcProcGprsDefinePdpContextSet  | `[SIPC] APN: ` |
| 0x062b0400  | sipcProcGprsPdpContextActDeactSet| `Rx PDP Context Activation SET (state=%s, CID=%d, secondary CID=%d)` |
| 0x07c70800  | sipcProcGprsLteAttachApnInfoSet  | `[%d] LTE Attach APN INFO SET cid:%d PDP type:0x%X APN %X %X %X` |
| 0x08580700  | sipcProcGprsSetApnInfoSet       | `[%d] APN Info SET Profile ID:0x%X APN %X %X %X` |
| 0x085b0700  | sipcProcGprsSetApnInfoSet       | `[%d] APN Info SET Profile ID:0x%X APN %X %X %X` |

The two `sipcProcGprsSetApnInfoSet` entries (0x08580700 vs 0x085b0700) differ
only in the subscription byte (SIM0 vs SIM1, DSDS), matching the
`[SIPC_0_GPRS]`/`[SIPC_1_GPRS]` log prefixes.

### FMT (AP->CP on-wire) mapping

The AP libsec-ril.so sends FMT header `[u16 len][u8 seq][u8 ack][u8 main][u8 sub][u8 type]`
(main=13 GPRS). Verified this round by disassembling:

- `IpcTxSetDataProfile @0x31ff48`: `mov w8,#0x1b0d; strh w8,[sp,#20]` = main=0x0d(13), sub=0x1b(27), type=3, len=203 (196 payload).
- `IpcTxSetLteAttachProfile @0x320238`: `mov w9,#0x140d` = main=13, sub=0x14(20), type=3, len=201 (194 payload).

Therefore: **sub 27 = SET_APN_INFO (CP) == IpcTxSetDataProfile (AP)**, and
**sub 20 = LTE_ATTACH_APN_INFO (CP) == IpcTxSetLteAttachProfile (AP)**. The AP
"SetDataProfile"/"SetLteAttachProfile" names are aliases of the CP SET_APN_INFO /
LTE_ATTACH_APN_INFO commands.

## 3. Persistence path (CP -> DS item -> NV)

CP flow recovered from function names (`.symtab`/log strings):

- `sipcProcGprsSetApnInfoSet` (sub 27) -> `PMPM_UpdateSetInitialAttachApnReq`
  -> `PMPM_HdlrSetInitialAttachApnReq` -> DS item `NASU.LTE.ATTACH.APN.INFO`.
- `sipcProcGprsLteAttachApnInfoSet` (sub 20) -> `PMPM_UpdateGprsAttachApnInfoReq`
  -> `PMPM_HdlrGprsAttachApnInfoReq` -> `PMPM_SendEsmApnInfoUpdReq`.
- Downstream `sm_SetApn`/`sm_GetApn`/`sm_SetApnLength` (MAIN @0x400b5bd7+).

DS item string pool (MAIN `.rodata` @0x404793e0): `DS_NASU.LTE.ATTACH.APN.INFO`
and `NASU.LTE.ATTACH.APN.INFO` are adjacent (item 360, numeric id 0x168).

## 4. Item-360 physical offset: NOT statically recoverable (re-confirmed)

`OFFSET` segment (0x85600 B) is a QBR NV template whose per-item `name_ptr`
fields are CP-RUNTIME-RELOCATED addresses (0x416a2xxx). Resolving those
against MAIN yields binary data, NOT the `NASU.LTE.ATTACH.APN.INFO` string.
The item-id -> physical-offset mapping is assigned at CP boot by the vendor
`cbd`/NvCoreInfo list and is not present in the on-flash image. This
independently re-confirms the Round-42 conclusion.

## 5. LIVE round-43 results (deployed + observed)

1. The full data-session sequence is BYTE-CORRECT and runs:
   NET_REGIST (PS REGISTERED_HOME) -> service domain -> preferred net ->
   mobile data ON -> SET_DATA_PROFILE(sub 27) -> SET_LTE_ATTACH(sub 20) ->
   ALWAYS_ON_PDN(sub 34) -> PS_ATTACH(sub 3) -> PS_REGIST_VERIFY -> DATA_CALL(sub 4).
2. sub 27/20/34/3 are ACKed by CP GEN result=0 (`0d...030080`).
3. DATA_CALL (sub 4) returns `GPRS_CALL_STATUS` state=3 (`010300...`): default
   EPS bearer NOT established.
4. Probing DefinePdpContext (sub 1) is LIVE-REJECTED with GEN=1
   (`0d01030180`) — the S5000AP LTE path does NOT use the legacy
   DefinePdpContext/SetPdpContext flow (corrects the prior "insert DEFINE_PDP"
   hypothesis, now reverted + documented in test_data_session.c).
5. `/mnt/vendor/efs/nv_data.bin` contains NO "internet" string and `nv.log`
   shows no post-2024-02-03 NvBackup -> item 360 remains EMPTY even after
   sub 27/20 are ACKed (they set in-memory profiles; they do NOT persist).

## 6. Conclusion

Blocking dependency (unchanged, now harder evidence): the persistent
initial-attach APN (item 360) requires a `(offset,length)` pair that only the
CP can compute at boot, OR a known-good nv_data.bin reference from an identical
KPN-provisioned G975F. The RFS NV serving path is implemented and ready to
provision item 360 the moment a legitimate offset is supplied by the CP.

## 7. NEW: item-360 record-size recovered from OFFSET (CP NV template)

The OFFSET segment (CP `.nv_core` template, 0x85600 B) contains a `{u32 item_id, u32 value}` pair table in its first 0x17000 B. At OFFSET file
offset 0x169be:

```
... item=0x151(337)  item=0x168(360)  value=0x9f(159)  0x00000000   item=0x15e(350)  value=0x5f(95) ...
```

Item 360 (`NASU.LTE.ATTACH.APN.INFO`) therefore has a record size/default of
`0x9f = 159` bytes in the CP-authored NV template. This is the FIRST concrete
size datum for item 360 recovered from the firmware itself (previously the
record size was unknown). It constrains any future RFS NV write of item 360 to
a 159-byte record (APN string NUL-padded to at most 159 bytes).

NOTE: this is the CP firmware's *template* pair table, not the physical live
offset in `/mnt/vendor/efs/nv_data.bin`; the live offset remains CP-runtime-
assigned (see section 4). The size datum removes one unknown (record length)
but not the offset unknown.

## 8. Continuation point

Next concrete operation: cross-reference the 159-byte record size against a
known-good KPN-provisioned G975F `nv_data.bin` (or a CP-supplied RFS
NV_WRITE_ALL offset for item 360) and, once a legitimate (offset,159) is
available, call efs_nv_write_at + efs_nv_update_checksum_sidecar through the
already-implemented rfs_nv serving path (--write-enable + NUXEL_NV_WRITE=1).
