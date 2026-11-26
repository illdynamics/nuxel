# NUXEL — SMS OR DIE — ROUND 14 CONTINUATION CHECKPOINT (resumable)

## Outcome at halt
SMS NOT SUBMITTED. Message ID 4 remains queued (+31649353067, exact authorized
body, error 0, NOT retransmitted). IDs 1-3 unchanged (unknown, error -2).
No carrier acceptance, no recipient confirmation. LTE + IPv6 preserved.

## What was actually done this continuation (verified on live CP)
Read sms12.md, USIM-IMS-CORRECTION, and the in-flight codec work. Recovered the
exact IIL vs FMT wire contract for the IMS PDN from the pinned vendor RIL
(build 60889dd7) with the Unicorn emulator, then fixed TWO real local defects
that the previous continuation had left unresolved.

### Fix 1 — DefinePdpContext payload[1] is AccessNetworkType, not profile id
- Stock `IpcTxDefinePdpContext` (both FMT 0x31f580 and IIL 0x357340) stores
  AccessNetworkType in payload[1]. The prior `fmt_tx_ims_define` wrote DataProfile
  id 2 there.
- `fmt_tx_ims_define` now emits EUTRAN(1), matching stock. Commit 09980a02.

### Fix 2 — DefinePdpContext must use IPv6, not the dual-stack wire byte
- CP validator 0x41219fe4 rejects wire byte 0x04 (IPV4V6) with 0x8001; it accepts
  0x05 (IP) and 0x06 (IPV6). The prior IMS PDN used IPv4v6 -> 0x04 -> rejected.
- ims_pdn now uses IPv6 (0x06) for the DEFINE/ACTIVATE context while the profile
  layer keeps IPv4v6. Commit 10984c4d.

### Result on the live CP (verified)
After the fixes, the IMS PDN FSM on the device advances and the CP ACCEPTS every
step (GEN result 0x8000 = OK):
- SetDataProfile(ims, sub=27)  -> 0x8000 OK
- DefinePdpContext(ims, sub=1) -> 0x8000 OK  (previously 0x8001)
- SetPdpContext ACTIVATE CID 2 (sub=4) -> 0x8000 OK
- GPRS_CALL_STATUS cid=2 state=3 (connecting) is emitted once, then the context
  transitions to state=0 (not connected). NO GPRS_IP_CONFIGURATION for CID 2 and
  NO P-CSCF ever arrive, so the IMS bearer does not complete.

## Verified remaining blocker (unchanged, now precise)
1. The modem accepts the ims profile + DEFINE + ACTIVATE but never completes the
   CID-2 bearer (state 3 -> 0, no IP, no P-CSCF).
2. `SDM_IMS_MODE` (MISC sub=32, mode=ON) is REJECTED with GEN 0x8001
   (hex 0a20030180). This was re-tested and confirmed; the prior revert was correct.
3. SMS-over-IP format (sub=26) and SMS-over-IP enable (sub=27) remain rejected
   with 0x8001 (pre-existing).
4. The modem does not autonomously bring up the IMS PDN, and the AP-side SDM arm
   is rejected. The exact supported mechanism by which stock Samsung establishes
   the "ims" APN + IP + P-CSCF on this CP is still not identified in native code.

## Current deployed device state
- Branch cs/mob-round35-stage06; HEAD 0f72df0b (SDM re-arm reverted; two PDN
  fixes retained).
- Installed nuxel-radiod SHA-256 252e24e5c1eea32612d8d2537c17048bce54b0668035400f60c87e9ae172a09c.
- Rollback: /var/lib/nuxel/radio-install.TBZ4K9/rollback.sh.
- GetImsStatus: state wait-backend; reason sip-registration-backend-missing;
  usim_identity_ready true; profile_phase verify; cid_attached false;
  ip_ready false; pcscf_ready false; context_ready false; init_phase done;
  auth_pending false; registered false; sms_transport unavailable.
- LTE REGISTERED_HOME preserved; rmnet0 global IPv6 2a02:a420:22bc:684a::/64.
- Message 4 held queued, not retransmitted; IDs 1-3 untouched.

## Next concrete operations (ordered)
1. Determine how stock Samsung actually establishes the IMS APN/IP/P-CSCF:
   the FMT SDM arm (sub=32) is rejected, and manual DEFINE/ACTIVATE is accepted
   but the CID-2 bearer never reaches IP. The remaining candidate is the IIL
   (`IpcProtocol41Iil`, main=112) registration/PDN endpoint that stock
   `imsservice` drives (`IpcRxIilConnected`/`IpcRxIilParameters`). Verify against
   libsec-ril 60889dd7 before any new modem write.
2. Once a modem-reported CID-2 GPRS_IP_CONFIGURATION with a P-CSCF appears, it is
   already wired into `ims_pdn_report_ip` -> pcscf_ready/context_ready.
3. Connect the already-implemented `ims_sip`/`ims_security`/`ims_sms` codec
   surfaces to `ims_service` (USIM AKA broker) to perform REGISTER/401/AKA/200,
   then install ipsec-3gpp and submit RP-DATA over the registered bearer.
4. Only release message 4 after genuine IMS registration + SMS-over-IP transport
   readiness. Never fabricate registration or submission.

## Invariants preserved
- No PII committed; no SIM key extraction; no auth bypass; no spoofing; no
  protected-partition writes; no modem reset loops; no emergency calls.
- Message 4 held queued, not retransmitted; IDs 1-3 untouched.
- LTE (IPv6), USB, ZeroTier preserved.
