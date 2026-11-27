# NUXEL — SMS OR DIE 4 REAL — Round 25.5 Continuation Checkpoint (updated)

Status: RECOVERED + VERIFIED. No physical SMS. No carrier acceptance. Message 4 held.
This file updates the earlier recovery note with the live-verified evidence gathered
this round (2026-11-27 ~18:10 UTC).

## RECOVERED ASTRA STATE — CONFIRMED, ALL WORK PRESERVED
- Branch cs/mob-round35-stage06 HEAD c5ee8b4b (17:55:10). 106 commits ahead of origin.
  DO NOT push/merge.
- Running/installed binary (live) MD5 51016b78e1ece659fc980ad639968963 at
  /usr/libexec/nuxel/nuxel-radiod (pid 381181), built at 17:56:06. This IS the
  HEAD build: contains both the 423 Min-Expires handler AND the epoch hold-expiry
  fix (verified via `strings`: "Min-Expires" and "ims_hold_expired" both present).
- Rollback dir: /var/lib/nuxel/rollback-sms25-continuation-20261127T175606/
  (nuxel-radiod ad2efe73 = the PRE-hold-expiry binary, the last "known last good
  before this round's fixes"; also /var/lib/nuxel/rollback-sms25-baseline).
- Uncommitted diff preserved: only the 3 rebased test binaries
  (test_ims_init/pdn/service) — owner artifacts; round18..26.md untracked.

## LIVE-REVERIFIED BASELINE (via ZeroTier root 10.11.12.99)
- LTE PS: REGISTERED_HOME raw 2, LTE, reject 0. CS DENIED raw 4 (KPN LTE-only).
- CID1 rmnet0 IPv6 up; CID2 IMS rmnet1 up with IMS IPv6 + P-CSCF
  2a02:a47e:e000:100::116 (route via rmnet1). P-CSCF list had 2 nodes.
- usb0 10.100.10.1/24 UP. ZeroTier ztly5zthnf 10.11.12.99 UP. SSH works.
- NET_CELL_INFO (8/17) live: decoded=true serving_valid=true lte_count 2..3,
  genuine PLMN 20408; ECI 076f31f, TAC 846e (NOT 0000). PANI on-wire:
  3GPP-E-UTRAN-FDD;utran-cell-id-3gpp=20408846e076f31f.
- Message 4 (sms.sqlite3, mode 0600): out, queued, error 0, textlen 39,
  total 1. NEVER transmitted. Messages 1-3: unknown, error -2 (untouched).

## CONFIRMED LOCAL FIXES (all deployed + host/ASan tests PASS)
- Hold-file epoch auto-expiry: FIXED. Live events `ims_hold_expired` at 17:56:21,
  17:59:23 prove the old hold clears without manual deletion.
- 423 "Interval Too Brief" + Min-Expires:3600 -> REGISTER re-sent with
  expires=3600. Host test asserts this. LIVE raw packet (18:08:24) shows
  Contact ...expires=3600 emitted.
- Cell-info ECI/TAC decode + PANI syntax: FIXED (see above).
- AKA security lifecycle, SIP transaction correlation, RP acceptance lifecycle,
  SMS-over-IMS durable store (IIL RP-DATA), CP device-ready semantics: all
  FIXED and host/ASan-tested (build.sh EXIT=0, "IMS SIP transport FSM: PASS",
  "SMS service durability/correlation: PASS", etc.).

## DEFINITIVE LIVE PACKET EVIDENCE (tcpdump rmnet1, 18:08:24 UTC)
- REGISTER sip:ims.mnc008.mcc204.3gppnetwork.org with
  From/To/P-Preferred-Identity <sip:204080121840266@ims.mnc008.mcc204.3gppnetwork.org>
  (the IMSI-derived temporary IMPU), Contact expires=3600,
  Security-Client ipsec-3gpp (no Require/Proxy-Require sec-agree),
  P-Access-Network-Info with genuine cell tuple, empty digest Authorization.
- Response: SIP/2.0 480 Temporarily Unavailable, Via + Retry-After: 180,
  Content-Length: 0. NO 401, NO AKA challenge. journal:
  {"code":480,"reason":"Temporarily Unavailable","headers":"via,retry",
   "p_cscf_no_service":true}.

## ROOT-CAUSE CONCLUSION (evidence-based, NOT an unverified claim)
- The P-CSCF is reachable and parses the REGISTER cleanly (480 not 400/403).
  The 480+Retry-After BEFORE any 401 AKA challenge is KPN's authoritative
  "no IMS service for this public identity" answer.
- Both IMPU variants were physically transmitted in prior rounds and BOTH
  received 480+Retry-After (no 401): the IMSI-derived temporary IMPU (C.2
  fallback) AND the MSISDN-derived IMPU. The deb76cb0 commit reverted the
  REGISTER to the IMSI-derived IMPU precisely because "a subscriber MSISDN
  alone is not a provisioned IMS public identity" (round-25 decision made after
  the MSISDN probe also returned 480).
- SIM is USIM-ONLY (sim_apps count=1 usim=1 isim=0, live). No ISIM => no
  EF_DOMAIN/EF_IMPI/EF_IMPU. CP never emits iil_registration (no
  network-provisioned IMPU to adopt). SEC_IMS_SUPP_AUTH_TYPES returns 0x0180
  UNSUPPORTED (this firmware/CP does not request IMS AKA via the AP path).
- CS registration DENIED (no conventional SMS, no NAS/SGs SMS). All three SMS
  transports therefore require a bearer KPN does not offer this subscription
  on this LTE-only, USIM-only, non-Samsung-IMS-client configuration.

## EXACT EXTERNAL DEPENDENCY (smallest owner action)
The missing observation that NO local source change can replace:
  With this SAME SIM in a stock KPN handset (or a known-working VoLTE phone),
  record WHICH public identity (IMPU) that phone derives and whether it
  registers IMS/VoLTE and sends an SMS. That reveals (a) the real
  operator-provisioned IMPU/IMPI the HSS expects, and (b) whether IMS is
  provisioned at all for this subscription outside the Samsung IMS client.
  Alternative: ask KPN directly whether this MSISDN is provisioned for
  VoLTE/SMS-over-IMS for a non-Samsung IMS client, and request the
  provisioned IMPU/IMPI (public + private) and security profile.
Without that identity/entitlement evidence, any further REGISTER is an
unchanged repeat that the mission (section 14) forbids, and it would return
the same 480+Retry-After.

## WHAT WAS NOT DONE (correctly, per mission constraints)
- No physical SMS submitted (message 4 held; no transport is physically ready).
- No fabricated carrier acceptance, no fabricated registration, no identity
  fabrication, no speculative protected-partition writes, no key extraction.
- No unchanged REGISTER retry (Retry-After and ethics gate honored).

## NEXT (on owner evidence)
1. Owner reports the stock-phone identity/registration result.
2. If a real provisioned IMPU/IMPI becomes available, wire it (not the
   IMSI-derived or MSISDN-derived fallback) and re-run a genuinely NEW REGISTER.
3. Only after a genuine 401 AKA challenge + IPsec SA + 200 registration may
   message 4 be released ONCE.

## FINAL ACCEPTANCE MATRIX (this round)
- Astra work recovered: YES (all commits, live binary, rollbacks, logs)
- Astra implementation completed: YES (all demonstrated defects fixed+tested)
- USB management restored: PRESERVED (usb0 10.100.10.1/24 UP; no regression)
- LTE preserved: YES (REGISTERED_HOME, CID1/CID2/P-CSCF all up)
- ZeroTier preserved: YES (10.11.12.99 reachable)
- Genuine serving-cell info: YES (ECI 076f31f, TAC 846e, PLMN 20408)
- Network-provided identity handling: NO network IMPU available (no IIL reg)
- Service-Route handling: implemented+tested (not exercised: no 2xx registration)
- Actual authentication challenge: NONE (480 before 401)
- Actual USIM authentication: NONE (no challenge)
- Actual security association established: NONE (no challenge/CK/IK)
- Genuine IMS registration: NONE (480+Retry-After)
- Alternative SMS transport availability: NONE (CS denied, no SGs, no IMS)
- Selected SMS transport: NONE physically available
- Physical SMS readiness: false
- Message ID 4 transmitted: NO
- Actual carrier acceptance: NONE
- Independent recipient confirmation: N/A
- Incoming SMS: NONE (no transport)
- Native Messages integration: codec/store/service complete + tested
- Reboot persistence physically verified: NOT re-run (guarded reboot deferred)
- Final commits: c5ee8b4b (this round); prior round commits preserved
- Verified rollback: /var/lib/nuxel/rollback-sms25-continuation-20261127T175606

## RESUME VERIFICATION (continuation re-verified live 2026-11-27 ~18:3x UTC)
Recovered Astra's full state and re-verified every claim against the live device
rather than trusting the checkpoint text alone:
- Live device reachable via ZeroTier root@10.11.12.99; nuxel-radiod pid 381181
  still running; running binary MD5 51016b78e1ece659fc980ad639968963 (matches HEAD).
- usb0 UP 10.100.10.1/24; neighbor 10.100.10.2 lladdr 52:1b:83:97:68:43 STALE
  (resolved). The many FAILED entries are stale IPv4 neighbor-cache rows from
  CLAT/NAT64 traffic, NOT a usb0 route/interface defect — no USB repair needed,
  no regression (P0 = PRESERVED).
- LTE PS REGISTERED_HOME raw 2 LTE reject 0 (live journal); P-CSCF
  2a02:a47e:e000:100::116 route via rmnet1 metric 1024 still present (P1 PRESERVED).
- subscriber.conf mode 600 root:root (19 bytes) at /var/lib/nuxel/subscriber.conf.
- Live SMS DB is /var/lib/nuxel-radio/sms.sqlite3 (mode 0600) — NOT
  /var/lib/nuxel/sms.sqlite3 (that path does not exist on-device; the earlier
  checkpoint shorthand was imprecise but the data is intact at the real path).
- Message 4 LIVE: direction=out state=queued error=0 result=0 status=-1 total=1
  textlen=39, peerlen=12, concat_ref NULL. NEVER transmitted (0 audit/submission
  events for id 4). Messages 1-3: state=unknown error=-2 result=-2, each audited
  "superseded / owner reports non-reception". Verified programmatically:
  message 4 peer != subscriber MSISDN (False), body len 39 == authorized body.
- Rollback dir /var/lib/nuxel/rollback-sms25-continuation-20261127T175606/
  contains pre-hold-expiry nuxel-radiod + sms.sqlite3 backup (VERIFIED on-device).
- ims-register.hold now at /var/lib/nuxel-radio/ims-register.hold (the writable
  namespace fix from this round), plus legacy /var/lib/nuxel/ims-register.hold.
- Working tree: only 3 owner-modified test binaries (unstaged) + round18-26.md
  untracked. Nothing discarded/reset.
- Full host build.sh re-run: `build+test OK`, every suite PASS including
  "IMS SIP transport FSM: PASS", "SMS service durability/correlation: PASS",
  "SMS durable store: PASS", "IMS SIP wire codec: PASS". No remaining local defect.

## CONCLUSION (unchanged, now triple-confirmed)
No physical SMS, no carrier acceptance, message 4 held. The single genuinely
blocking observation is external and precisely identified: KPN returns
SIP 480+Retry-After BEFORE any 401 AKA for both IMPU variants on this
USIM-only (no ISIM) LTE-only (CS denied) subscription, so no SMS transport
(CS / NAS-SGs / IMS) is physically offered. Every locally resolvable defect
has been implemented, tested and deployed. A repeat REGISTER without a new
provisioned IMPU/IMPI identity would be an unchanged experiment (forbidden by
section 14) and would return the same 480. Message 4 must remain held until a
real 401 AKA challenge confirms an authenticated, registered transport.
