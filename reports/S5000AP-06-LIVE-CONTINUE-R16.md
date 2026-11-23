# S5000AP Stage-06 — Round 16 live checkpoint (corrected NET_REGIST decode + SetLteAttachProfile layout)

**Date:** 2026-11-23 CET (later evening)
**Branch:** cs/mob
**HEAD at start:** 727dfe1e... (working tree mob.md modified)

## Verdict
STAGE_06_NOT_YET_PASS — but TWO authoritative corrections landed and the truth
contract now reports PS registration = REGISTERED_HOME (not "NOT_REGISTERED" or
"DENIED" as prior rounds falsely concluded). Data call still GPRS_CALL_STATUS
state=3 (no bearer), no ESM reject cause.

## Correction 1 — NET_REGIST decode was reading the wrong offsets
ROOT CAUSE (proven this round): every IpcRx* receive handler takes `char* data`
= the FULL FMT frame (7-byte header + payload), NOT the payload. Verified from
IpcRxGeneral @0x32b0f0 (reads data[7]=echo_main, data[8]=echo_sub) and the
kernel `struct sipc_fmt_hdr` (modem_prj.h: [u16 len][msg_seq][ack_seq][main][sub][type]).

IpcRxNetRegState @0x339818 therefore maps:
  data[7]  = payload[0] = RAT marker
  data[8]  = payload[1] = service-domain selector (int map @0x14a0b8: 1->0,2->2,3->1)
  data[9]  = payload[2] = RegState raw enum
  data[10] = payload[3] = reject cause
  data[11..12]= payload[4..5] LAC/TAC; data[13..16]=payload[6..9] cell id; data[17]=payload[10] LtePsVoiceIndication

Live NET_REGIST payload 01030100980dc036000000feff020200ffff0000:
  payload[1]=0x03 => service domain PS_ONLY (selector 3 -> 1)
  payload[2]=0x01 => RegState REGISTERED_HOME (IsRegistered: (r|4)==5 => r in {1,5})
  payload[3]=0x00 => no reject

=> PS/data registration is ALREADY SUCCESSFUL. The FSM was falsely failing at
PS_REGIST_VERIFY because it read payload[8]/payload[9] (cell-id bytes). Fixed.

## Correction 2 — SetLteAttachProfile auth flag / protocol roaming offsets
Re-derived IpcTxSetLteAttachProfile @0x320238 byte-exact. Correct payload layout:
  [0]=flag(3) [1]=cid [2]=proto home [3..103]=APN(101B)
  [104..119]=extra [120..123]=int [124..126]=reserved
  [127..158]=username [159..190]=password
  [191]=auth flag  [192]=proto roaming  [193]=reserved

Prior code put auth flag at [168] (inside password region) and pco at [169],
and omitted proto roaming at [192]. Fixed; unit test updated.

## Remaining blocker (honest)
Data call (SetPdpContext main=13 sub=4, ACKed GEN 0) returns GPRS_CALL_STATUS
(main=13 sub=16) payload 050300000000000000 => cid=5, state=3 (NOT connected),
no cause. Vendor IpcRxGprsCallStatus @0x321ab0 confirms state 1/10/11 = connected,
anything else (3) = not connected.

PS registration is now confirmed good; the remaining failure is default-bearer/
PDP activation. Candidate root cause: missing initial-attach APN step. Vendor
DataCallManager::OnPsAttachDone @0x22c448 calls ModemProxy::SetAttachApn after
PS attach, and DataCallManager::SetLteAttachProfile @0x22b518 issues TWO vtable
calls (offsets 712 and 728). There is NO separate IpcTxSetAttachApn; SetAttachApn
converges to IpcTxSetLteAttachProfile. The FSM only sends SetLteAttachProfile
once (flag=3); it likely needs a second attach-APN variant after PS attach.

## Deployed binary
- Current: /usr/libexec/nuxel/nuxel-radiod SHA256 3727d7b7dee8298bfeecc18efa2751787c271989f623c67034f9ce8c9bad036b
- Prior rollback preserved (e4aa6b27..., e50b9c82..., plus timestamped .bak files).

## Next action
Determine the second SetLteAttachProfile flag/variant for the initial-attach APN
(SetAttachApn path) and add it to the FSM after PS_ATTACH, then re-test live.
