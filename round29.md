# NUXEL — SMS OR DIE 4 REAL — Round 28 Continuation (Registration-First)
## Genuine New Evidence: 423 eliminated, 480 isolated as the sole blocker

Status (2026-11-27 ~19:12 local): One genuine local defect fixed and deployed.
No 401 AKA challenge. No physical SMS. Message 4 held.

## NEW DEFECT FOUND AND FIXED (not a repeat)

The initial REGISTER used `expires=600` (10 min). KPN's registrar answered
`423 Interval Too Brief` + `Min-Expires: 3600` BEFORE any 401 AKA, because
KPN enforces a minimum registration interval of 3600s (1h).

FIX: `ims_sip_tr.c` now initializes `t->expires_s=3600` (was 600). The RFC
3261 §10.2.1.1 default registration interval is also 3600s, so this is both
a KPN requirement and the standards default. Regression test updated.

## LIVE VERIFICATION (deployed + restarted, pid new)

- New binary MD5 `5b53304f9878facf2bb72b2a49849d64` (old 273a61e2).
- Rollback: `/var/lib/nuxel/rollback-expires3600-20261127T191059/nuxel-radiod`.
- After restart, fresh REGISTER now emits `expires=3600` directly:
  `sip_tr_tx_mask len=1055` -> NO 423 -> **SIP 480 "Temporarily Unavailable"
  + Retry-After:180** (37 sec after restart, confirmed live).

This is new, non-repeated evidence: the 423 was purely the "too short"
correction. With expires=3600 the P-CSCF goes STRAIGHT to 480, never 401.

## DEFINITIVE BLOCKER (isolated)

The 480 "Temporarily Unavailable" + Retry-After:180 with NO WWW-Authenticate,
NO Proxy-Authenticate, NO Reason, NO Warning, NO Server headers is KPN's P-CSCF
answer that it cannot route this public identity to any reachable S-CSCF.

Identities physically transmitted (all -> 480, never 401):
  1. IMSI-derived temporary IMPU `sip:<IMSI>@ims.mnc008.mcc204.3gppnetwork.org`
     (TS 24.229 C.2 USIM-only fallback) — current production identity.
  2. MSISDN-derived IMPU `sip:+<MSISDN>@ims.mnc008.mcc204.3gppnetwork.org`
     (prior rounds, also 480).

Supporting evidence that IMS is NOT provisioned for this subscription:
  - USIM-only: sim_apps count=1 usim=1 isim=0 (live). No EF_IMPI/EF_IMPU/EF_DOMAIN.
  - Modem SDM readbacks ALL rejected (0x8001): IMS mode(sub=32), P-CSCF(sub=34),
    domain(sub=28), SMS-over-IP(sub=27), SMS-fmt(sub=26). => no carrier IMS
    provisioning in modem NVRAM.
  - SEC_IMS_SUPP_AUTH_TYPES -> UNSUPPORTED (this firmware/CP never requests IMS AKA).
  - CS registration DENIED (raw 4) — no CS/SGs SMS path.
  - Modem-internal IIL SIP stack never emits IpcRxIilIsimAuth (sub=17): the CP
    is not running its own REGISTER either (idle; no trigger, only E911 exists).

## WHAT THE ARCHITECTURE REVIEW ESTABLISHED (evidence)

- Samsung vendor RIL (libsec-ril.so 60889dd7) confirms TWO IMS surfaces:
  * IpcTxSetSipParam (main=3 sub=19) configures a modem-internal SIP stack
    (proxy/user/pass/auth/proto).
  * IpcTxImsReqSetRegState (main=22 sub=8) REPORTS already-achieved reg state
    (not a trigger); only ReqImsRegistration**E911** exists for triggering.
  => AP-side raw-socket SIP REGISTER (our path) is a legitimate surface; the
     modem-internal stack is idle because there is no non-E911 trigger and
     no SDM IMS provisioning.
- Our AP REGISTER is standards-complete: correct R-URI (home domain), To/From
  (IMPU), Contact (reachable IPv6 + +sip.instance + +g.3gpp.smsip + expires),
  Security-Client ipsec-3gpp (no Require/Proxy-Require sec-agree, per KPN 400),
  empty initial AKA Authorization, P-Access-Network-Info with genuine
  ECI 076f31f / TAC 846e / PLMN 20408.

## EXACT EXTERNAL DEPENDENCY (smallest owner action)

Put the SAME SIM in a known-good KPN VoLTE phone and report ONLY:
  (a) VoLTE icon yes/no,
  (b) ordinary SMS send works yes/no,
  (c) IMS Registration Registered/Not (dial *#*#4636#*#* -> Phone info),
  (d) the provisioned IMPU/IMPI if visible (public identity, not a secret).

Determines: if (c)=Registered with an IMPU, that exact value replaces our
IMSI-derived fallback. If (c)=Not Registered => KPN truly did not provision
IMS/VoLTE/SMS-over-IMS for this SIM and no local source change can create a
network binding.

## PRESERVATION CONFIRMED
- LTE REGISTERED_HOME (raw 2, LTE, reject 0). CID1 rmnet0 up, CID2 rmnet1 up.
- P-CSCF 2a02:a47e:e000:100::116 routed via rmnet1 (metric 1024).
- usb0 10.100.10.1/24 UP. ZeroTier ONLINE c1ab327d70 10.11.12.99. CP ONLINE.
- subscriber.conf mode 0600. sms.sqlite3 mode 0600. Message 4 = queued (held).
- New rollback + old rollbacks preserved. No push/merge.

## NEXT
1. Owner reports reference-handset observation (a)-(d).
2. On a real provisioned IMPU/IMPI, wire it and run one NEW REGISTER.
3. Only after genuine 401 AKA + IPsec SA + 200 may message 4 be released once.

NOT FULL STAGE 06 COMPLETE. NO FABRICATED SUCCESS.
