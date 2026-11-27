# NUXEL — ROUND 19 RESUME CHECKPOINT (SMS OR DIE 4 REAL)

Status: **NOT** complete. No IMS registration, no SMS submission.
Message ID 4 remains `queued`, error 0, NOT transmitted. Messages 1–3 untouched.
Recipient/body never printed or committed.

## Deployed binary (HEAD 4bfe2829)
- `/usr/libexec/nuxel/nuxel-radiod` sha256 `3bee657c4a8290577a5f0467a007ebc6a9effa7981985988115adfe0a0e4c981`
- Rollbacks (newest first):
  - `/var/lib/nuxel/radio-install.round19b-1795777070` (pre bearer-preserve fix)
  - `/var/lib/nuxel/radio-install.round19-1795776830` (pre ethics-gate; == round-18 binary)
  - `/var/lib/nuxel/radio-install.round18-reg-*`, `/var/lib/nuxel/radio-install.round18-diag-*`

## Baseline (verified live, privacy-preserving, after redeploy)
- CP online, baseband G975FXXSEFUJ2, home PLMN 20408, SIM READY.
- LTE PS: REGISTERED_HOME, RAT LTE, reject 0.
- CID2 IMS PDN active; rmnet1 UP with IMS IPv6 + P-CSCF /128 route; 8 rmnet1
  routes stable over 3 min (1 ims_iface_up, 0 ims_iface_down).
- CS registration: DENIED (no CS/SGs SMS path).
- USB usb0 UP; ZeroTier ztly5zthnf 10.11.12.99 UP.
- Durable SMS store: msg 4 out/queued/error 0.
- **0 REGISTER sends since deploy** (ethics gate active; see below).

## Codex/session outcome vs the user's quoted "SMS SUBMITTED — RECIPIENT
## CONFIRMATION REQUIRED" message
This run did NOT submit a SMS and did NOT see carrier acceptance. The header
"test SMS van Nuxel voor mijn schatje <3" was a PASTED QUOTE of the round
prompt (it also appears verbatim in ./sms18.md). The actual message-4 text in
the durable store is "test SMS van Nuxel voor mijn schatje <3" per the
authorized record; Codex never read/echoed the stored body or the recipient.
No physical submission occurred in this run; do not treat that quoted line as
evidence of any submission.

## SIM / ISIM INVENTORY CONTRADICTION — RESOLVED (negative)
- `OPEN CHANNEL` (PB main=6 sub=6) with payload `01 00 70 00` returns
  `05 06 02 00 02 6e 00` — i.e. status 0 and a channel byte, but with
  **type=0, aid_len=0** (the DEFAULT USIM application). This is the only
  live OPEN ever recorded and it does NOT prove ISIM presence.
- OPEN with the AID `A0 00 00 00 87 10 02 FF FF FF FF FF FF FF FF FF`
  (the string sms18 called "…FF31F0018908…") returns `00 02 6a 81`
  (PB status `0x81` = application not found). That AID is not a valid ISIM
  AID standard form; no EF_DOMAIN/EF_IMPI/EF_IMPU read has ever succeeded.
- => **No live, standards-supported evidence that this SIM carries ISIM.**
  Treat sms18's "USIM + ISIM present" as UNVERIFIED (it was an inference from
  an ambiguous default-application OPEN). The device-side inventory must be
  reconstructed by the on-device daemon (see "Next operations").

## TRANSMIT APDU — real CP status word
- PB/OPEN works because OPEN is accepted over the FMT/SIPC path (the reply
  `05 06 02 00 02 6e 00` is even mirrored to radiod's FMT log as main=5/sub=6).
- Every TRANSMIT/READ over the same channel returns GEN error `0x0180`, both
  with the daemon up and fully stopped (so it is NOT channel contention).
- SEC `IMS AUTH` (main=5 sub=9) with a synthetic RAND/AUTN also returns
  `05 05 02 01 80` (`0x0180`): the CP refuses synthetic AKA and does not
  initiate network AKA on its own.
- Vendor reference: `IpcRxTransmitApdu` @0x3429c8 builds Apdu(type=data,u16@7,
  data@9) — the recovered serialization matches what the probe sends; the
  0x0180 is a CP-side rejection, not a serializer bug.

## IDENTITY / AUTH ARCHITECTURE — decisive architectural finding
From `libsec-ril.so` EFUJ2 (read-only, emulated):
- `IpcProtocol41Iil::IpcTxImsAuthResp` @0x356218 and the AP-facing
  `IpcProtocol41::IpcTxImsAuthResp` @0x34ce10 share ONE transport byte
  (main 0x16/sub 8 via ConvertToIpcCmd) and the latter is a stub that
  returns -1. The AP IMS service in Samsung's Android stack owns SIP+AUTH.
- CP `modem.bin` (CP_G975FXXS9DTK9): NO SIP, NO IPsec, NO AKAv1; it parses
  P-CSCF/IMPI/IMPU/domain from the ISIM/SIM and reports IMS state.
- Genuine SIP REGISTER test this round: the impl sent an IMSI-derived REGISTER
  and received 480+Retry-After (backoff fix in place), no 401.
- The CP `SetRegState`(REGISTERED) with a plausible IMS-engine frame was
  ACKed (`03 01 01 03 80`) but the CP issued NO ISIM AKA and NO state change
  in the following window: the AP IMS service is the authoritative party.
- => **A legitimate authenticated IMS REGISTER cannot be completed on this
  native path yet without the CP AP-KEY/AKA material being exposed to the
  AP IMS engine; that was previously judged outside authorized scope.**

## Code corrections implemented + deployed this session (commits)
1. `82cdedce` — `ims_sip_tr`: absolute Retry-After hold carried across a
   transport re-open; refuses REGISTER before the hold. New regression
   test in `tests/test_ims_sip_tr.c` (re-open carry-over). Host + ASan pass.
2. `82cdedce` — `radiod`: ETHICS GATE. When a well-formed REGISTER
   gets 480+Retry-After with NO 401, and no ISIM/USIM AKA is available,
   the impl must NOT auto-retry the carrier with an unverified IMPU.
   Gate: `NUXEL_IMS_ALLOW_UNAUTH_REGISTER=1` re-enables the probe for an
   owner-verified IMS provisioning environment. SMS stays held.
3. `4bfe2829` — `radiod`: bearer preserve. The gate only suppresses REGISTER,
   NOT the CID2/rmnet1 iface + P-CSCF route; the earlier gating also disabled
   the iface apply and dropped rmnet1 (regression caught live and fixed).

## Exact next concrete operations
1. **Determine SIM entitlement (owner question, highest priority)**:
   Confirm with KPN whether this subscription is IMS/SMS-over-IMS enabled
   for a third-party (non-Samsung) stack, OR place this same SIM in a
   stock KPN handset and observe whether it registers IMS and receives
   normal SMS. This adjudicates "interoperability" from "carrier restriction".
2. **Authoritatively re-enumerate SIM application inventory** in the
   daemon (not via ad-hoc probe): add a bounded read-only daemon module that
   issues SIMAPPS_INFO via FMT/SIPC SEC main=5 sub=15, parses application
   count + AIDs + slot and logs REDACTED IDs. That is the standards-supported
   way to settle USIM-vs-ISIM without relying on the ambiguous OPEN defaults.
3. **If owner says KPN is IMS-enabled**: re-enable the REGISTER probe with
   `NUXEL_IMS_ALLOW_UNAUTH_REGISTER=1` only after (2) shows a real ISIM or
   after the owner confirms. Capture whether a 401/AKA is ever returned.
4. Keep message 4 held. Only release after genuine 200 OK + SMS-specific
   readiness. Any physical submission needs separate authorization (already
   granted once; the once-remains-unused in this run).

## Notes / hygiene
- No PII, no SIM keys, no authentication material, no firmware artifacts
  committed. `round18.md`,`round19.md`,`probe_uicc.c` remain untracked
  (pre-existing). Pre-existing modified binaries (test_ims_init/test_ims_pdn/
  test_ims_service, .gitignore) are untouched.
- Rollback: restore the pre-round-19 binary from
  `radio-install.round19-1795776830/nuxel-radiod` (sha 5416254f…).
- LTE, CID1, rmnet1 IMS, USB, ZeroTier verified preserved after redeploy.
