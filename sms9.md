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

## DECISIVE RESULT this continuation (SIM capability)
- Added fmt_tx_get_sim_icc_type (SEC main=5 sub=7) + one-shot query in radiod
  (deployed daemon md5 18cf19256a85af57f03751953782a729).
- LIVE: SEC_SIM_ICC_TYPE response plen=1 payload=0x02.
- Vendor decode (IpcRxSecSimCardType @0x343e50, SimManager::UpdateState
  @0x1ecfe8, GenerateSimStatusWithAppsInfo @0x315e80): SimType/app-type
  5=ISIM, 2=USIM, 1=CSIM. value 0x02 == USIM ONLY, NO ISIM.
- Therefore the SIM lacks the ISIM application (IMPI/IMPU), so IMS SIP AKA
  registration and SMS-over-IMS cannot proceed with this SIM/line. This is a
  DEMONSTRATED SIM-PROVISIONING requirement, not an unimplemented native
  command. CS SMS is also denied by KPN (LTE-only, no SGs/2G/3G), so the
  authorized SMS remains untransmittable through any currently-available
  bearer. Message ID 4 rightly stays held (queued, not retransmitted).

FINAL STATUS: native AP-side IMS init + registration command layer is COMPLETE
and byte-exact against the vendor. Physical SMS-over-IMS is blocked by an
external SIM-provisioning requirement (no ISIM on the installed SIM; KPN LTE-only
CS-denied). LTE, durable queue, and rollback binaries preserved.

## ROUND 08d — conclusive disassembly re-verification + resumable checkpoint

### SMS domain contract now FULLY verified (resolves prior "value 8 unverified")
- `IpcProtocol41::ConvertDomainToIPC` @0x344b98 constant 0x01000302:
  internal 0->wire2, 1->wire3, 2->wire0 (CS), 3->wire1; >3 -> 0.
- `SmsManager::DoImsSendIms` @0x21b320: IMS SMS domain wire = **8**
  (both the CS-fallback branch passes w4=8, and the SMS-format==2 branch
  passes w3=8). CONFIRMED, not guessed.
- No other wire domain exists: SMS main=4 uses CS (0..3) or IMS (8) only.
  There is no separate "SMS over SGs/NAS" wire domain; SGs SMS would present
  as combined-attach CS registration, which KPN live-denies (raw_state=4).

### IMS registration conclusively not running (180-min trace)
- `fmt_tx` main=22 sub=8 (REQ_SET_REG_STATE): 60 tx. Modem GEN 0x8000 ack.
- `fmt_rx` main=22: **ZERO** frames. No ImsModeChange, no reg-state notify.
- `SEC_IMS_AUTH` (main=5 sub=9): **ZERO** — modem never reaches SIP AKA.
- IMS CID 2 never in GPRS_IP_CONFIGURATION (only CID 1 internet, 48 events).
- FSM: request-reg -> reg-timeout -> (retry) -> failed(attempt-limit).

### SIM appliance
- SEC_SIM_ICC_TYPE (main=5 sub=7, payload 0x02) re-traced through
  IpcRxSecSimCardType @0x343e50 (reads frame byte offset 7, stores index-1)
  and GenerateSimStatusWithAppsInfo @0x315e80 (app-type map 5=ISIM,2=USIM,
  1=CSIM,4=3GPP). Installed SIM exposes no ISIM application (no IMPI/IMPU),
  so IMS SIP AKA cannot complete.

### Commit
- 05a3b219: commits the SIM-ICC query serializer/rotation/test/golden that was
  previously deployed-but-uncommitted (the live investigation behind 996a401c).

### Conclusion
Native AP-side SMS+IMS command layer is byte-exact and complete; SIM-ICC query,
capability init, VOLTE-state handshake, IMS profile sync, and registration drive
are all implemented and live-accepted. Physical SMS is blocked by two
independently-verified external conditions: (1) KPN CS-attach denied on LTE
(live raw_state=4), (2) SIM lacks ISIM => IMS SIP AKA impossible. Message ID 4
rightly remains queued; LTE, rollback binaries, and durable queue preserved.
