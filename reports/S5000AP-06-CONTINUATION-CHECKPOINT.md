# S5000AP Stage-06 — Continuation checkpoint (round 14, ~20:26 CET 2026-11-23)

## Verdict
`STAGE_06_NOT_YET_PASS — authoritative PS/data DENIED decode landed; added
SetServiceDomain(CS_PS)+SetPreferredNetType(LTE) and fixed SetPdpContext layout;
PDP still call_state=3; next = recover initial-attach APN (SetAttachApn /
SetLteAttachPdnList) wire frames or confirm carrier-side ESM denial`

## Git
Branch `cs/mob`, HEAD `df3d2c19`.

## This round's decisive corrections
- Fixed `fmt_tx_set_pdp_context`: payload[0]=protocol, payload[1]=pdp_type=3
  (LTE/EUTRAN, from ToAccessNetworkType table), flags=0x11 at [2], APN at [6]
  (was protocol/pdp_type swapped).
- Added `fmt_tx_set_service_domain` (8/8 CS_PS) + `fmt_tx_set_preferred_net_type`
  (8/10 LTE-auto).
- Added authoritative NET_REGIST PS/CS RegState decode → live `ps=3 DENIED`,
  `cs=1 REGISTERED`.
- Added DS_SET_SERVICE_DOMAIN + DS_SET_PREFERRED_NET FSM phases.

## Genuine remaining blocker (honest)
PS/data registration is DENIED (vendor `NetRegState::IsDenied` {3}) while CS/voice
is REGISTERED. Commands byte-exact; SetMobileDataSetting → GEN result 3;
GPRS_CALL_STATUS → state 3. Not a framing defect. Remaining leads: initial-attach
APN (SetAttachApn/SetLteAttachPdnList) unrecovered wire frames, or carrier-side
ESM denial.

## Safety
RADIO /dev/sda16 SHA256 unchanged `9ffa1426…66fc7`; BOOT /dev/sda8 unchanged;
binary `e50b9c82…`; rollback preserved; no protected-partition writes;
Wi-Fi/USB/ZeroTier management preserved.
