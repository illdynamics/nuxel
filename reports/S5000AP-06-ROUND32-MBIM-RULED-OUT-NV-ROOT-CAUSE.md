# Stage 06 — Round 32: MBIM-over-SIPC ARCHITECTURALLY RULED OUT; NV initial-attach APN root-caused

**Date:** 2026-11-24 CET
**Branch:** cs/mob
**Device:** SM-G975F / beyond2lte / S5000AP, KPN SIM (PLMN 20408), live via ZeroTier
**Authoritative reference:** .vendor-ro/libsec-ril.so (BuildID 60889dd714394ae0db7c2ecc2bf2740f)

## Verdict (honest, code-proven, not hypothesized)

This round performed FRESH independent aarch64 disassembly AND a live hardware test
that together **disprove MBIM-over-SIPC as the LTE data path on the S5000AP**. The
correct path is the native FMT GPRS/PDP path plus an NV-provisioned persistent
initial-attach APN. The modem's initial-attach APN is **verified empty**, which is
the precise reason the default EPS bearer never establishes.

## 1. MBIM is architecturally disabled for this modem (vendor code proof)

`MbimManager::Initialize @0x27baf8` (libsec-ril.so) contains:

```asm
27bb90: bl  ModemProxy::GetIntfType        ; returns intf type from [modem+16]+36
27bb98: cmp w0, #0xa                        ; 0xa = SIPC interface type
27bb9c: b.eq 27bbb0                         ; == SIPC -> SKIP
27bba4: mov w2, #0x6d                       ; #109
27bbac: bl  ModemProxy::RegisterForRawIpc   ; register MBIM raw-IPC ONLY if != SIPC
```

`ModemProxy::GetIntfType @0x1cb470`:
```asm
ldr x8, [x0, #16]
ldr w0, [x8, #36]     ; interface type enum
```

**Conclusion:** the Samsung RIL registers the MBIM raw-IPC forward handler
(`RegisterForRawIpc`, register #109) ONLY when the modem interface type is NOT
SIPC (0xa). The Shannon S5000AP is a SIPC modem, so the MBIM host is deliberately
never wired up. MBIM (`/vendor/bin/libsecmbim` reference in `.rodata` @0x1007a0)
is for the USB-CDC-MBIM modem interface type, which this device does not expose.
The round-28/30/31 "MBIM is the initial-attach path" conclusion was WRONG: the
vendor's own branch proves it is a non-path for a SIPC modem.

## 2. Live hardware test (this round) confirms the CP ignores MBIM

Recovered + implemented the full MBIM control session (USB-IF MBIM v1.0 §10.5):
OPEN -> MS LTE Attach Config COMMAND (CID 0x0A) -> MS LTE Attach Status QUERY
(CID 0x0B) -> CLOSE, each wrapped in the byte-exact `IpcTxRawIpc` FMT frame
(main=0x16/sub=0x0c/type=0x05, forward-flag 0x01) recovered from
`IpcProtocol41::IpcTxRawIpc @0x3180f0`.

Live TX (all byte-correct, session-complete):
```
fmt_tx main=22 sub=12 type=5 len=24   (OPEN,  16B MBIM + 8B FMT/flag)
fmt_tx main=22 sub=12 type=5 len=124  (attach-config COMMAND)
fmt_tx main=22 sub=12 type=5 len=28   (attach-status QUERY, 20B MBIM)
fmt_tx main=22 sub=12 type=5 len=20   (CLOSE, 12B MBIM)
```

**CP response: ZERO.** No MBIM raw-IPC response, no GEN echo for main=22, no
modem state change, rmnet0..7 unchanged DOWN. This is the same silent result as
round-31's single-command test, now with a complete OPEN/CLOSE envelope. The CP
simply does not implement MBIM-over-SIPC raw-IPC on the RIL channel (ch 235).

## 3. NV initial-attach APN is EMPTY (root cause of "state=3" / no bearer)

Mounted read-only `/tmp/efs_inspect/nv_data.bin` (1 MiB, AP EFS) and
`/tmp/cpefs_inspect/.nv_core.bak` (546 KiB, CP EFS). Integrity MD5 verified.

- `grep -abo "internet" nv_data.bin` -> **no occurrences**
- `grep -abo "ims"` -> none, no other APN string present

The modem registers (PS=1 REGISTERED_HOME) but has **no stored initial-attach
APN**, therefore the default EPS bearer is never established
(`GPRS_CALL_STATUS state=3` = not-connected is the direct consequence).

The NV item NAME is recoverable (below); the numeric item-ID table is not.

## 4. Recovered NV item names (from nv_data.bin symbol table)

| offset | NV item name |
|---|---|
| 0x14402 | PDNMGR_SET_PDNCONTEXT_UEREQAPNLENGTH |
| 0x144dd | PDNMGR_SET_PDNCONTEXT_APN |
| 0x1452f | PDNMGR_SET_PDNCONTEXT_UEREQAPN |
| 0x15462 | PDNMGR_SET_STATELESSINFO_ATTACHINFO |

Plus the full PDNMGR/PMPM function table (`PMPM_UpdateSetInitialAttachApnReq`,
`PMPM_UpdateGprsAttachApnInfoReq`, `PMPM_UpdateLteAttachMode`, `PDNMGR_SET_STATELESSINFO_ATTACHINFO`,
etc.). The **numeric NV item-ID <-> string-name mapping** is a proprietary `cbd`
table not present in-repo, in `nv_data.bin`, in `nv_core.bak`, or in any available
firmware/header artifact. Writing the APN via RFS_NV_WRITE_ALL (op 0x15) without
an authoritative item ID would be a blind EFS write and is refused by the existing
RFS fail-closed policy (correctly).

## 5. Implementation delivered this round (in-tree, gated OFF, tested)

1. `src/mbim_tx.{c,h}` — added MBIM session primitives (OPEN/CLOSE/CAPS-query/
   generic-query builders), cross-checked against `IpcProtocol41::IpcTxRawIpc`
   and the USB-IF MBIM v1.0 spec. Byte-exact, fail-closed on overflow/empty.
2. `src/data_session.h` / `src/radiod.c` — MBIM sub-session state machine
   (OPEN->COMMAND->STATUS->CLOSE) under `NUXEL_MBIM_ATTACH=1` (still OFF by
   default). Correctly emits the full envelope then advances the FSM.
3. `tests/test_mbim_tx.c` — golden-vector tests for the new primitives.
4. `tests/test_data_session.c` — fixed a stale round-31 regression (test was not
   updated for the inserted MBIM_ATTACH_CONFIG phase).

All host tests PASS; aarch64 on-device build (gcc 15.3.1 -Werror) PASS.
Deployment rolled back to known-good `80d7220ae1ef0947...` (MBIM OFF); no
Wi-Fi/ZeroTier/USB/SSH regression.

## 6. Definitive remaining requirement (single, precise)

To establish the default EPS bearer, the modem's NV `PDNMGR_SET_STATELESSINFO_ATTACHINFO`
(initial-attach APN) item must be set to `internet`. This requires ONE of:

1. The Samsung `cbd` NV item-ID table (string->numeric-ID mapping for the
   S5000AP), so the APN can be written via RFS_NV_WRITE_ALL with full backup +
   rollback, OR
2. A known-good `nv_data.bin` from an IDENTICAL SM-G975F on the SAME carrier
   (KPN) with the attach APN already present, as an authoritative reference for
   the exact item ID + encoding.

Neither is guessable from available artifacts; guessing the item ID would risk
NV/EFS corruption, which the safety contract forbids. This is a precise external
asset dependency, not an unresolved software defect.

No NV/EFS/RADIO/BOOT/IMEI/calibration write was performed. No fabricated success.
Wi-Fi/ZeroTier/USB/SSH preserved. CP online, SIM ready, PS registered (unchanged).
