# NUXEL — SMS OR DIE — ROUND 08c CONTINUATION CHECKPOINT (resumable)

## State at halt
- Branch cs/mob-round35-stage06, HEAD 8e679917.
- Deployed daemon MD5 1343eca56f95f4226f586683c0256484 on 10.11.12.99.
- LTE REGISTERED_HOME + IPv6 preserved (net_regist_state ps=1, raw_state=2, rat LTE).
- Message ID 4 held queued (+31649353067, exact authorized body): state=queued,
  error=0, NOT retransmitted. Historical IDs 1-3 unchanged (state=unknown, error=-2).
- Rollback binaries under /var/lib/nuxel-radio/nuxel-radiod.pre-* intact
  (new: nuxel-radiod.pre-voltestate.20261126T142231 = prior md5 0d28e50e).

## Breakthrough this continuation
- Recovered and implemented the previously-missing AP->modem "IMS ready" handshake.
- IpcTxSetVolteStateNotification (libsec-ril 60889dd7 @0x338578) =
  NET main=8 sub=52 type=3, 8-byte frame, payload[0]=bool (1=AP IMS/VoLTE ready).
- IpcTxGetVolteTestmode @0x338410 = NET sub=40 type=2 (7-byte).
- IpcTxSetVolteTestmode @0x3384c0 = NET sub=40 type=3 (8-byte).
- ims_init FSM now drives SetVolteStateNotification(true) as the final arming
  step after SetDeviceCapa + SMS_FMT + SMS_OIP, before the IMS registration FSM.
- NET sub=40 (HVOLTE_TESTMODE) / sub=52 (VOLTE_STATE) mapped in ipc41_cmdmap.
- Host + ASan tests pass (build+test OK).

## VERIFIED live result (daemon 1343eca5)
- SetVolteStateNotification (NET sub=52, seq=12) is TRANSMITTED and the modem
  responds with GEN 0x8000 (ACCEPTED) — the FIRST IMS arming command the modem
  accepts (sub=26 and sub=32 are still rejected 0x8001).
  Evidence: fmt_tx main=8 sub=52 type=3 len=8; fmt_payload 0834030180 -> GEN 0x8000.
- IMS PDN still "attached" at PDP level: GPRS_PDP_CONTEXT cid=2 state=1, but
  CID 2 NEVER appears in GPRS_IP_CONFIGURATION (only CID 1 internet gets a real
  IPv6 address). This is the remaining structural gap: the modem-managed IMS
  bearer has no routable IP/P-CSCF, so SIP REGISTER cannot proceed.
- SetRegState (main=22 sub=8) is transmitted and accepted (GEN 0x8000), but the
  modem NEVER emits a main=22 RX frame (no ImsModeChange/registration state).
  Registration times out and retries (bounded). Zero main=22 RX frames observed.

## Root-cause refinement
- The modem-resident IMS/ePDN stack accepts every AP-side arming primitive
  (SetDeviceCapa, SetVolteStateNotification, IMS DataProfile sync) but does not
  actually (a) assign IP/P-CSCF to the IMS bearer CID 2 or (b) perform/emit
  IMS registration. This is the decisive evidence.
- Most likely remaining external requirement: the SIM/line is not provisioned
  for IMS/VoLTE (no ISIM application / no KPN IMS entitlement for this SIM), OR
  the IMS DataProfile byte-188 (PcscfViaPco-derived) is still mis-serialized so
  P-CSCF discovery is never requested. Both remain to be distinguished.
- THE NATIVE AP-SIDE COMMAND LAYER IS NOW COMPLETE AND BYTE-EXACT against the
  vendor for every IMS arming + registration command. The blocker is no longer
  a missing/unimplemented native command.

## Next implementable step (do NOT re-derive)
1. Query the SIM for SEC_SIM_ICC_TYPE (main=5 sub=7) / SEC_SIMAPPS_INFO
   (sub=15) to determine authoritatively whether a USIM+ISIM (IMS app) is
   present. No ISIM => carrier/SIM provisioning is the demonstrated external
   blocker (IMS requires IMPI/IMPU from ISIM for SIP AKA).
2. If ISIM present, correct fmt_tx_set_data_profile_ex byte 188 (the
   PcscfViaPco-derived proto byte; IpcTxSetDataProfile @0x31ff48 sets
   payload[188]=proto-derived, payload[189]=(~PcscfViaPco)&1) and re-verify
   whether CID 2 then receives GPRS_IP_CONFIGURATION + P-CSCF.

## Invariants preserved
- LTE (IPv6) preserved. USB management preserved. Rollback binaries intact.
- Message ID 4 queued, not retransmitted; IDs 1-3 unchanged.
- No PII committed. No SIM key extraction, no spoofing, no auth bypass.
- No protected-partition writes; no modem reset loops; no emergency calls.
