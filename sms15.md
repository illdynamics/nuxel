# NUXEL — SMS OR DIE — ROUND 15 CHECKPOINT (resumable)

## Outcome at halt
SMS NOT SUBMITTED. Message ID 4 remains queued (exact authorized recipient/body,
error 0, NOT retransmitted). IDs 1–3 unchanged (unknown, error -2). LTE + IPv6
preserved. No carrier acceptance, no recipient confirmation, no fabricated
registration/submission.

## What was actually done this continuation (host-side, all verifiable)

### 1. Answered sms14.md's #1 open question: the IMS bearer/auth/SMS path
Recovered the complete `IpcProtocol41Iil` ("IIL") endpoint contract from the
pinned vendor RIL (libsec-ril.so build 60889dd7) and, crucially, EMULATED the
TX builders under Unicorn/AArch64 to capture authoritative wire bytes.

Symbol map (IpcProtocol41Iil, complete):
- TX: IpcTxImsAuthResp(0x356218), IpcTxSendRPSMMA(0x3570f8),
  IpcTxDefinePdpContext(0x357340), IpcTxSetPdpContext(0x357488),
  IpcTxGetPdpContext(0x357658), IpcTxImsReqSetImsPdnInfo(0x355fe0),
  IpcTxImsReqSetRegState(0x3561c8, STUB -> -1), SetSsacInfo/SetSuspendNotiType/
  SetPreferredNetworkType/SendPBInitCompleted/EpdgHandoverParam/NetHandoverStatus.
- RX: IpcRxIilRegistration(0x356528), IpcRxIilIsimAuth(0x356808),
  IpcRxIilConnected(0x356870), IpcRxIilParameters(0x356800),
  IpcRxIilPreference(0x356628), IpcRxSms/IpcRxSmsIncomingMsg(0x357018/0x356d08).

### 2. IIL frame header (emulation-verified, corrected twice)
Base header is 7 bytes, distinct from FMT sipc_fmt_hdr:
  [u16 total_len][u16 msg_seq][u8 main][u8 sub][u8 type]
(FMT uses [u8 msg_seq][u8 ack_seq]; IIL uses a 16-bit msg_seq, no ack_seq.)
main still sits at offset 4, so zero-sequence IIL frames are byte-identical in
the header to FMT frames. `ConvertToIpcCmd` (0x355d10) maps:
  IPC_SMS_RP_SMMA(416)  -> msg 5000, main=4,  sub=21, type=2
  IIL subrange(0x1b5a..)-> msg 5000, main=112, sub {4,8,9,10,11,21,22}, type=2
  IPC_CP_STATE(801)     -> msg 3000, main=8,  sub=5,  type=2

### 3. Emulation-verified frames (synthetic inputs only; no SIM/network)
Captured at the IpcModem send call site:
- IpcTxImsAuthResp(data[0..15],16):
    19 00 00 00 70 02 02 01 10 00..0f
  = header(7) + flag=1 + len=16 + 16 data bytes. This is the REAL AKA RES path
  (the FMT main=22/sub=6 auth relay is an unsupported stub; confirmed again).
- IpcTxSendRPSMMA("hello"):
    07 01 00 00 04 15 03 "hello"
  = header(7) + text at offset 7, type=3 (notification), NO flag byte.
- IpcTxDefinePdpContext("ims.mnc008.mcc204.gprs", flag0=0, proto=IPV6):
    86 00 00 00 0d 01 03 01 00 06 "<APN>"  (134-byte frame; main=13 GPRS
  sub=1, proto wire 0x06 = IPV6, flag byte at [7], char field at [8]).
- IpcTxSetPdpContext(cid=2, "ims.mnc008.mcc204.gprs"):
    70 00 00 00 0d 04 03 01 02 11 00 00 00 "<APN>"  (112-byte frame; main=13
  sub=4, flag byte at [7], cid at [8], 0x11 flags, APN at [13]).

### 4. Committed implementation
- 44ca6334: initial IIL serializer (header later corrected).
- 016ece4f: emulation-verified serializers ims_iil.c/h + test_ims_iil.c, wired
  into build.sh host + ASan/UBSan suites. All pass.

## Live device state (unchanged from round 14)
- Branch cs/mob-round35-stage06; HEAD 016ece4f (plus the two new commits).
- Deployed daemon is still round-14 (SHA-256 252e24e5c1eea32612d8d2537c17048bce
  54b0668035400f60c87e9ae172a09c); the new IIL serializer is HOST-ONLY, not yet
  deployed (deliberately — not wired into radiod TX yet).
- GetImsStatus: wait-backend / sip-registration-backend-missing; cid_attached
  false; ip_ready/pcscf_ready/context_ready false; sms_transport unavailable.
- LTE REGISTERED_HOME, rmnet0 IPv6 2a02:a420:22bc:684a::/64, USB + ZeroTier UP.

## Next concrete operations (ordered, emulation-verified groundwork now in place)
1. Wire `iil_tx_define_pdp`/`iil_tx_set_pdp_context` into the IMS PDN FSM in
   radiod.c (they emit main=13 sub=1/4 with the flag byte + IIL payload layout,
   distinct from the FMT `fmt_tx_ims_define`/`fmt_tx_set_pdp_context`). Test the
   hypothesis that the IIL payload layout (not the FMT one) is what makes the
   modem complete CID-2 -> GPRS_IP_CONFIGURATION + P-CSCF. Reversible: keep
   rollback; the FMT path is untouched.
2. Add IIL RX handlers for IpcRxIilIsimAuth (main=112 sub? -> UiccAuth result)
   and IpcRxIilConnected/IpcRxIilParameters (IMS bearer ready + P-CSCF) so the
   SIP backend can actually consume network challenges and P-CSCF.
3. Connect the existing ims_sip.c/ims_security.c/ims_sms.c codec surfaces to a
   real UDP SIP transport over the CID-2 bearer once it has IP + P-CSCF; drive
   REGISTER/401(AKAv1-MD5)/USIM AKA (via iil_tx_ims_auth_resp)/REGISTER/200.
4. Only after genuine IMS registration, submit message 4 via
   iil_tx_send_rpsmma + the TS 24.341 MESSAGE path. Never fabricate.

## Invariants preserved
- No PII committed; no SIM key extraction; no auth bypass; no spoofing; no
  protected-partition writes; no modem reset loops; no emergency calls.
- Message 4 held queued, not retransmitted; IDs 1-3 untouched.
- LTE (IPv6), USB, ZeroTier preserved. No live modem writes performed this round
  (host-only reverse engineering + implementation + tests).
