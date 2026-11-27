# NUXEL — SMS OR DIE 4 REAL — Round 26 Architectural Challenge Checkpoint

Status (2026-11-27 ~18:30 UTC): ARCHITECTURE CHALLENGED AND VALIDATED.
No physical SMS, no carrier acceptance. Message 4 held and never transmitted.

## ARCHITECTURAL REVIEW (P1) — WHAT WAS CHALLENGED AND THE VERDICT

This round independently challenged every architectural assumption. Evidence.

### Q1: Is AP-side IMS registration correct, or should the modem (CP) register?
VERDICT: AP-side SIP REGISTER is CORRECT on EFUJ2.

Evidence chain:
- Vendor RIL (`/Users/wicked/x/nuxel/.vendor-ro/libsec-ril.so`, build 60889dd7)
  exposes TWO IMS families:
    * `IpcProtocol41` (plain FMT): IpcTxImsReqSetRegState (main=22 sub=8),
      IpcTxImsReqDeregistration (22/7). These are AP->CP REPORTS of an already
      achieved registration state, NOT triggers.
    * `IpcProtocol41Iil` (IIL endpoint): IpcTxImsAuthResp (sub=2),
      IpcRxIilIsimAuth (sub=17 RK), IpcRxIilRegistration (sub=7),
      IpcRxIilPreference (sub=2), IpcRxSmsIncomingMsg (sub=1).
- Round 24 live evidence (sms24.md): "With NUXEL_IIL_IMS_REGISTER=1 the daemon
  fired the CP-internal trigger (IIL main=112 sub=8 type=1, empty payload —
  exact vendor form). The CP did NOT respond to it (no IsimAuth sub 17, no IIL
  registration event) over 40s. This confirms the IMS registration MUST be
  driven by our AP SIP client (which we do); the modem is a relay, not a
  registrar initiator, on EFUJ2."
- Therefore the native AP-side raw-socket SIP REGISTER (`ims_sip.c` +
  `ims_sip_tr.c`) over the CID-2 IMS bearer is the correct owner of SIP
  signaling on this firmware. The modem-internal IIL endpoint only RELAYS
  USIM AKA (IsimAuth -> SEC 5/9 -> ImsAuthResp) and reports the resulting
  registration state / SMS-over-IP preference back to the AP.

### Q2: Is subscriber-identity derivation correct?
VERDICT: Identity derivation is correct; BOTH legitimate variants were tried.

- Domain: SIM home network PLMN 20408 -> MCC 204, MNC 08 (2-digit).
  `ims_identity_from_usim(...mnc_digits=2)` builds
  `ims.mnc008.mcc204.3gppnetwork.org` (3-digit MNC 008 per TS 23.003 13.3).
  Correct for this USIM-only subscription.
- IMPU variants physically transmitted in prior rounds (git history proves it):
    * IMSI-derived temporary IMPU `sip:<IMSI>@ims.mnc008.mcc204.3gppnetwork.org`
      (TS 24.229 C.2 fallback for USIM-only). Commit range 70c80644..deb76cb0
      shows this was the registration identity.
    * MSISDN-derived IMPU `sip:+316xxxxxxxx@ims.mnc008.mcc204.3gppnetwork.org`
      (TS 23.003 13.3). Commit 70c80644 added the MSISDN-preference path; it
      was in the register until deb76cb0 reverted to IMSI-derived.
  BOTH received SIP 480 + Retry-After BEFORE any 401 AKA challenge.
  (sms25.md "both IMPU variants" statement is therefore accurate.)

### Q3: Is SIP transport complete?
VERDICT: All previously demonstrated local defects are fixed and host-tested.
- ECI/TAC decode (NET_CELL_INFO 8/17): fixed, genuine ECI 076f31f TAC 846e.
- P-Access-Network-Info: `3GPP-E-UTRAN-FDD;utran-cell-id-3gpp=20408846e076f31f`
  (correct TS 24.229 7.2A.4.3 MCC+MNC+4hex-TAC+7hex-ECI).
- Contact: `+g.3gpp.smsip` feature tag, 600s expiry, `+sip.instance` UUID.
- Security: Security-Client ipsec-3gpp offer (hmac-sha-1-96/aes-cbc/esp/trans),
  absent Require/Proxy-Require sec-agree (per round-18 live: KPN 400s on it).
- Initial AKA Authorization: empty nonce/response (TS24.229 5.1.1.2.2a).
- AKA digest: RFC3310 binary-RES, AKAv1-MD5, correlated Call-ID/CSeq/branch.
- IPsec: xfrm netlink SA/policy install (ims_security.c) AFTER 401 (correct:
  the initial plaintext REGISTER is standard; IPsec is installed from CK/IK
  derived during AKA, then the authenticated REGISTER is protected).

### Q4: Is the SIP 480 interpretation correct?
VERDICT: The 480 is a GENUINE P-CSCF answer, but it does NOT prove IMS
entitlement is missing. It proves the P-CSCF cannot route the registration
for THIS identity to a reachable S-CSCF/registrar.

Evidence:
- The 480 response source IP is verified equal to the configured P-CSCF
  (radiod.c sip_tr_recv filters by peer == cfg.pcscf), so it is not spoofed.
- The response is 480 "Temporarily Unavailable" + Retry-After:180, NOT
  403/404 (identity malformed/forbidden) and NOT 401 (challenge wanted).
- A 480 from a P-CSCF means "the registrar/S-CSCF for this public identity is
  currently unreachable or the identity is not served here". It is NOT a
  definitive "no IMS subscription exists".

### Remaining unresolved question with an available evidence source (P5)
The single genuinely-blocking missing observation is the reference-handset
differential. The owner confirmed the SAME SIM works in another phone.
That phone reveals:
  - whether IMS/VoLTE is actually registered for this subscription,
  - whether ordinary SMS works (and over which transport), and
  - the operator-provisioned public identity (IMPU) if legitimately exposed.
This is the smallest owner action that unblocks an otherwise-exhausted local
investigation. See PROCEDURE below.

## NO REMAINING INDEPENDENTLY-RESOLVABLE LOCAL DEFECT
- Full host build+test (build.sh) EXIT=0. All suites PASS including:
  IMS SIP transport FSM, SMS durability/correlation, SMS durable store,
  IMS SIP wire codec, IMS IIL wire contract, IMS security negotiation, etc.
- AArch64 build and ASan/UBSan suites were verified in prior rounds; source
  unchanged since then (HEAD e7ed3ec5).
- Live device binary MD5 51016b78e1ece659fc980ad639968963 == HEAD build.

## REFERENCE HANDSET PROCEDURE (P5 — smallest owner action)
Put the SAME SIM in a known-working phone that supports VoLTE on KPN NL.
On that phone:
1. Enable mobile data + VoLTE (Settings -> Connections -> Mobile networks).
2. Observe the status bar: is there a "VoLTE" or "HD Voice" icon?
   -> This single boolean is the most valuable evidence: IMS IS provisioned.
3. Make one ordinary outgoing SMS to a known recipient; confirm delivery.
   -> Proves an SMS transport exists for this subscription.
4. Optionally dial *#*#4636#*#* -> Phone information -> IMS Service Status:
   - IMS Registration: Registered / Not Registered
   - if "Registered", note the IMPU/IMPI shown (if visible) — this is the
     operator-provisioned public identity KPN's HSS expects; it is public,
     not a secret, and is exactly the value Nuxel must present.
5. Report back ONLY: (a) VoLTE icon yes/no, (b) SMS send worked yes/no,
   (c) IMS Registration Registered/Not, (d) the IMPU string IF shown.
Do NOT send any secret/PIN/credential. Do NOT reflash Nuxel.

## CONTINUATION PROCEDURE (once reference evidence is available)
1. If the stock phone shows VoLTE Registered with an IMPU:
   - Wire that exact operator-provisioned IMPU (not the IMSI-derived or
     MSISDN-derived fallback) into `g.ims.identity.impu` via a protected
     config or the IIL REGISTRATION adoption path.
   - Re-run a genuinely NEW REGISTER (after clearing the existing hold only
     once the new identity is deployed, honoring Retry-After).
2. If the stock phone shows IMS Registered but SMS fails, or shows CS-only:
   - Record which SMS transport the stock phone actually uses (IMS vs CS).
3. If the stock phone also shows "Not Registered" for IMS:
   - The SIM has NO IMS entitlement; the only legitimate SMS transport would
     be CS, which KPN NL does not offer on LTE-only (CS DENIED confirmed).
   - This genuinely confirms the external dependency.
Message 4 STAYS HELD in all cases until a genuine 401 AKA challenge +
IPsec SA + 200 registration proves an authenticated transport is ready.

## PRESERVATION CONFIRMED (P0)
- CP ONLINE, LTE REGISTERED_HOME, CID1/CID2, P-CSCF 2a02:a47e:e000:100::116
  routed via rmnet1, USB usb0 10.100.10.1/24, ZeroTier 10.11.12.99.
- subscriber.conf mode 600 (19 bytes). SMS DB mode 0600.
- Message 4 verified NEVER transmitted: 0 audit, 0 submission_results,
  body 39 bytes == authorized body, peer 12 digits != subscriber.
- Production binary MD5 51016b78e1ece659fc980ad639968963 (HEAD).
- Rollback dirs preserved: /var/lib/nuxel/rollback-sms25-continuation-*,
  /var/lib/nuxel/rollback-sms25-baseline.
- No push/merge. Working tree only owner artifacts + untracked round*.md.

## FINAL ACCEPTANCE MATRIX (this round)
- Native IMS architecture validated: YES (AP-side SIP; modem is relay on EFUJ2)
- Genuine serving-cell info: YES (ECI 076f31f TAC 846e PLMN 20408, live-verified)
- Subscriber identity validated: YES (both legit variants physically tried)
- Reference-handset IMS evidence: PENDING owner procedure (below)
- Initial registration prerequisites: ALL verified present
- Actual authentication challenge: NONE (480 before 401)
- Actual USIM authentication: NONE (no challenge)
- Actual security association established: NONE (no challenge/CK/IK)
- Genuine IMS registration: NONE
- Alternative SMS transport availability: NONE demonstrated (CS denied, no SGs)
- Selected SMS transport: NONE physically ready
- Physical SMS readiness: false
- Message ID 4 transmitted: NO
- Actual carrier acceptance: NONE
- Independent recipient confirmation: N/A
- Incoming SMS: NONE (no transport)
- Native Messages integration: codec/store/service complete + tested
- LTE preserved: YES
- USB preserved: YES
- ZeroTier preserved: YES
- Reboot persistence physically verified: deferred (guarded reboot when appropriate)
- Shared VoLTE foundation preserved: YES (modular identity/bearer/SIP/auth/etc.)
- Final commits: none this round (no local defect required a change)
- Verified rollback: preserved

## CONCLUSION
The architecture is validated: AP-side SIP REGISTER over the CID-2 IMS bearer
is correct; the modem is a relay. Both legitimate IMPU variants (IMSI-derived
and MSISDN-derived) have been physically transmitted and both receive SIP 480
+ Retry-After BEFORE any 401 AKA. Every locally resolvable defect has been
fixed, tested, and deployed. The single genuinely-blocking observation is the
reference-handset differential; the concise owner procedure is provided above.
Message 4 remains held and never transmitted. THIS IS NOT FULL STAGE 06 COMPLETE.
