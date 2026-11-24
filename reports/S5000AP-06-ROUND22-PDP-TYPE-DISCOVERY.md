# Stage 06 — Round 22: SetPdpContext wire-byte re-derivation (new evidence)

**Branch:** cs/mob
**Date:** 2026-11-24 CET
**Device:** SM-G975F / beyond2lte / S5000AP

## Verdict

STAGE_06 NOT_PASS. This round produces INDEPENDENT disassembly evidence that
refutes the prior conclusion ("NV/EFS blocker, serialization byte-exact") and
identifies a concrete, previously-untested defect in the SetPdpContext ACTIVATE
frame.

## New finding 1: DoSetInitialAttachApn is a STUB (refutes Round 21)

`DataCallManager::DoSetInitialAttachApn @0x22bad8` is only 0x44 bytes and
disassembles to:

```
  22baec: log level check (gate on global log level)
  22bb0c: bl __android_log_buf_print   ; emit one log line when verbose
  22bb14: mov w0, wzr                 ; always return 0
  22bb18: ret
```

It performs NO call to `ModemProxy::SetAttachApn`, NO call to
`SetLteAttachProfile`, and no wire transmit. Round 21's claim that
`DoSetInitialAttachApn -> SetAttachApn -> SetLteAttachProfile(sub=20)` is the
attach-APN wire path is FALSE. That claim was the basis for the "modem
persistent initial-attach APN" root cause, and it is now demonstrated wrong.

## New finding 2: the real LTE activation path is a DERIVED class

The actual LTE data setup is `LteEpdgDataCallManager::DoSetupDataCall @0x28d0a8`
(0x1a20 bytes), a DERIVED subclass (vtable `_ZTV22LteEpdgDataCallManager`). This
is the concrete object that performs the real PDP activation, matching mob.md §3
("resolve indirect calls using their actual concrete object types").

Relevant concrete symbols recovered this round (full dynsym now indexed):
- ModemProxy::ActivatePdpContext @0x1ce5e8   (Message*,int cid,PdpActDeactState,char* apn,char* user,DataAuth,int,bool)
- IpcModem::ActivatePdpContext @0x2f1be8     (allocates IpcHistory txn, then virtual-calls the Tx serializer)
- IpcProtocol41::IpcTxSetPdpContext @0x31f6e0  (base class serializer, 0x248)
- IpcProtocol41::Iil::IpcTxSetPdpContext @0x357488 (DERIVED "Iil" serializer, 0x1cc, DIFFERENT layout)
- IpcProtocol41::Iil::IpcTxGetPdpContext @0x357658
- ContextActivationDca::AllocateCall* @0x2699e0/@0x268bf8
- Dca::AllocateCall @0x230048
- DataCallSetup::ToAccessNetworkType @0x29fa08 (RadioTechnology -> AccessNetworkType)

Key fact: IpcModem::ActivatePdpContext passes the SAME 6 args to the virtual
IpcTxSetPdpContext: (cid, PdpActDeactState, apn, user, DataAuth, proto). The
2nd wire-serializer arg is the PdpActDeactState, NOT a raw "LTE=3".

## New finding 3: payload[0] wire-byte is a JUMP-TABLE value, not "3"

Base IpcTxSetPdpContext @0x31f6e0 selects payload[0] via a jump table
(@0x149806) indexed by the 2nd arg (0..8):

  arg=0 -> payload[0]=1 (full path: APN+user present)
  arg=1 -> payload[0]=2
  arg=2 -> payload[0]=3
  arg=3 -> payload[0]=4
  arg=4 -> payload[0]=5
  arg=5 -> payload[0]=6
  arg=6 -> payload[0]=7
  arg=7 -> payload[0]=8
  arg=8 -> payload[0]=1 (full path)

The "full path" (payload[0]=1) copies APN (<=32 bytes) and user/password, sets
flag bit0 (APN present) and bit4 (ACTIVATE) only when auth!=0. The simple paths
(payload[0]=2..8) set ONLY payload[0] and payload[1]=cid; flags remain 0.

Nuxel's fmt_tx_set_pdp_context HARDCODES payload[0] = FMT_TX_PDP_TYPE_LTE = 3
and flags = 0x11 (APN|ACTIVATE) with an APN string.

This matches NEITHER the full path (payload[0]=1 + APN) NOR the LTE simple path
(payload[0]=4 + no APN). The value "3" on the wire is what the vendor emits for
2nd-arg==2 (UTRAN/3G), not LTE.

## New finding 4: ToAccessNetworkType maps LTE=14 -> AccessNetworkType=3

DataCallSetup::ToAccessNetworkType @0x29fa08 uses a 20-entry table @0x14708c:
RadioTechnology LTE(14) -> 3 (EUTRAN). So AccessNetworkType EUTRAN = 3.

For the ACTIVATE frame the vendor does NOT encode AccessNetworkType directly as
payload[0]; it encodes the PdpActDeactState/profile selector through the jump
table. The concrete correct payload[0] for a default internet bearer is either
1 (full APN path) or 4 (LTE simple), and must be settled LIVE — it is NOT 3.

## Plan (next)

Add NUXEL_PDP_TYPE runtime selector for payload[0], then live-test candidates
{1,4,3,2} with the existing APN/protocol/auth matrix. This is a genuinely new,
independently-justified candidate (wire-byte correction), not a repeat of the
disproven protocol/auth/attach-flag matrix.

## Safety

No NV/EFS/RADIO/BOOT/IMEI/firmware write. RADIO sda16 and BOOT sda8 unchanged.
Wi-Fi/ZeroTier/USB/SSH intact.
