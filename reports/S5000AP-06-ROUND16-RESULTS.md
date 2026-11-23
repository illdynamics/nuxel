# Stage 06 — Round 16 results: PS registration unblocked; default bearer still pending

**Branch:** cs/mob
**Commits:** 87c1b62d (NET_REGIST + SetLteAttachProfile), 45a677e7 (flag param)
**Deployed binary SHA256:** 37c90ab5117f62fb3b9e5ef4ab30a439208c22531433765d4973de5c6d5137ae
**Date:** 2026-11-23 CET

## Verdict
STAGE_06_NOT_YET_PASS — but the PS-registration blocker is RESOLVED and the truth
contract now reports `PS=REGISTERED_HOME`. The remaining failure is the default
EPS bearer / PDP activation (GPRS_CALL_STATUS state=3, no ESM cause), which is
unchanged across every wire-format correction tested this round.

## Delivered corrections (committed, live-verified)
1. **NET_REGIST decode** (radiod.c). Prior code read payload[8]/payload[9]
   (cell-id bytes) and falsely reported PS=NOT_REGISTERED(0). The IpcRx* receive
   handlers take `char* data = FULL FMT frame (header+payload)`, proven from
   IpcRxGeneral @0x32b0f0 and kernel `sipc_fmt_hdr`. Correct offsets:
   payload[1]=service-domain selector, payload[2]=RegState, payload[3]=reject.
   Live payload 0103... now decodes to domain PS_ONLY + RegState REGISTERED_HOME.
2. **SetLteAttachProfile layout** (fmt_tx.c). Auth flag is payload[191], protocol
   roaming is payload[192]; prior code put auth at [168] + spurious pco at [169].
   Byte-exact per IpcTxSetLteAttachProfile @0x320238.

## Hypotheses tested and disproven (live)
- SetLteAttachProfile flag=1 (attach-APN variant): GEN result 4 (rejected).
- SetLteAttachProfile flag=4: GEN result 1 (rejected, prior round).
- SetMobileDataSetting extra byte true vs false: GEN result 3 in both (stable;
  consistent with idempotent "already enabled", not a rejection).
- Attach/PDP CID 5 vs 1: GPRS_CALL_STATUS state=3 in both (cid echoed correctly).

## Reconstructed vendor attach flow (from disassembly)
- DataCallManager::DoAttach @0x22b490 -> SetLteAttachProfile.
- OnSetLteAttachProfileDone @0x22c098 (success) -> PsAttach (vtable 704)
  + SetAttachApn (vtable 720, property-gated).
- OnPsAttachDone @0x22c448 -> ModemProxy::SetAttachApn.
- IpcModem::SetAttachApn @0x2f1410 only STORES APN (offsets 0x9c/0x101/0x165);
  there is NO IpcTxSetAttachApn. It converges to IpcTxSetLteAttachProfile.
- GetAttachCid @0x1e4500 => CID=5 only when ModemType==1, else 1. The device's
  runtime ModemType is not yet confirmed; CID 5 vs 1 makes no live difference.
- ConvertProfileId @0x22c890 maps DataProfile enum -> 1/5/11 (separate from attach CID).

## Blocker (honest, evidence-backed)
Data call (SetPdpContext main=13 sub=4, byte-correct, GEN 0) -> GPRS_CALL_STATUS
(main=13 sub=16) payload [cid][03][00...] => state=3 (NOT connected, per
IpcRxGprsCallStatus @0x321ab0), no cause, no GPRS_IP_CONFIGURATION, rmnet DOWN.

PS registration (EPS attach) succeeds; default-bearer activation fails. Remaining
leads: (a) the initial-attach APN / LTE attach-PDN-list path via the
IpcProtocol41Iil subclass (SetLteAttachPdnList / SetLteAttachtype concrete
implementations, not yet recovered to wire frames), or (b) a carrier-side ESM
denial with no cause surfaced to the AP (SIM data-service provisioning).

No PASS claimed. No fabricated success. No protected-partition/NV/EFS write.
Management (WiFi 10.20.30.16, USB 10.100.10.1, ZeroTier 10.11.12.99) preserved;
rollback binaries retained.
