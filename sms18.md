# NUXEL — ROUND 18 RESUME CHECKPOINT (SMS OR DIE 4 REAL)

Status: **NOT** complete. No IMS registration, no SMS submission.
Message ID 4 remains `queued`, error 0, NOT transmitted. Messages 1–3 untouched.

## Deployed binary (== git HEAD 2663a0b8 + phase-name fix)
- `/usr/libexec/nuxel/nuxel-radiod` sha256 `5416254f9f82180a63e47e9193879a659d74daa8274ba61e1a6d61bf69755548`
  (retry-wait observable: a 480 leaves the FSM in `retry-wait`, not instant fail).
- Rollbacks created this round (newest first):
  - `/var/lib/nuxel/radio-install.round18-reg-*`
  - `/var/lib/nuxel/radio-install.round18-diag-1795772081`
- Rollbacks created this round:
  - `/var/lib/nuxel/radio-install.round18-diag-1795772081` (pre-round-18)
  - `/var/lib/nuxel/radio-install.round18-reg-*` (pre REGISTER-fix)

## Baseline (verified live, privacy-preserving)
- LTE PS: REGISTERED_HOME, RAT LTE, reject 0; rmnet0 IPv6 global present.
- CID2 IMS PDN active: rmnet1 IPv6 global, 2 P-CSCF discovered, ims_iface_up
  addr/route rc=0.
- CS registration: DENIED (raw 4) — no CS/SGs path; SMS must be IMS.
- USB usb0 UP; ZeroTier ztly5zthnf 10.11.12.99 UP.
- Durable SMS: /var/lib/nuxel-radio/sms.sqlite3, msg 4 out/queued/error 0.

## Architecture established (evidence)
- Vendor `libsec-ril.so`: NO SIP engine (`SIP/2.0`=0, no REGISTER/MESSAGE
  method, no `3gppnetwork` domain, no DIGEST/AKAv1).
- CP `modem.bin` (CP_G975FXXS9DTK9): NO SIP (`SIP/2.0`=0, `AKAv1`=0, no
  IPsec, no SMSoIP). It DOES read EF-IMPU/EF-IMPI/EF-DOMAIN/EF-SMSP and parse
  PCO P-CSCF, and tracks IMS registration (`NS_IMS_REG_*`, `IMS_REGI_TIMEOUT`).
  => modem is an IMS *state* endpoint; it does not run the SIP client.
- Android system partition (system.img) contains the real IMS SIP client
  (`SIP/2.0`, `AKAv1-MD5`, `IMPU`/`IMPI`, `P-CSCF`, `sip.instance`) = the AP
  oFono-style IMS stack (not present natively in Nuxel).
- SIM application inventory (live, read-only, SEC 5/15): **USIM + ISIM**
  present (AIDs `A0000000871002…` and `…FF31F0018908…`).
- USIM AUTH (SEC 5/9) works on this transport (solicited reply observed).

## Round-18 demonstrated SIP facts
- 480 arrives ~1.0 s after send over rmnet1; conntrack shows the matching
  P-CSCF reply (sport 5060 -> dport 5062). Genuine over-the-air response.
- A fully standards-compliant REGISTER (valid Contact URI `sip:user@domain;
  transport=udp`, `+sip.instance` valid URN, `+g.3gpp.icsi-ref`, Security-Client,
  P-Preferred-Identity, Supported, Allow) and a bare OPTIONS-behaving REGISTER
  receive **480 Temporarily Unavailable + Retry-After: 180** before any 401.
- Probe matrix: every IMPU (anonymous, IMSI-like, tel, arbitrary) → same 480.
  No P-CSCF TLS service on 5061/5060.

## Demonstrated local defect FIXED this round
- REGISTER asserted `Require: sec-agree` + `Proxy-Require: sec-agree` together
  with Security-Client → P-CSCF answered **400 Bad Request** (parse-level
  reject). Removing the two Require headers (keep the Security-Client OFFER)
  makes the REGISTER parse cleanly → 480 Retry-After. This 400→480 change was
  reproduced and is fixed in `ims_sip.c`. Retry-After backoff added to
  `ims_sip_tr.c` (`IMS_SIP_TR_RETRY_WAIT`, bounded). Host suites pass (ASan).
- Codec also corrected: Contact is now a parseable SIP URI (was bracketed-IPv6
  contact), valid `+sip.instance` URN, `P-Preferred-Identity`,
  `Supported: path,outbound,100rel`, RFC-3329 key=value Security-Client.

## Genuine remaining failure (not yet an established external blocker)
- Every well-formed AP REGISTER is answered 480 + Retry-After before the 401
  AKA challenge. This is the P-CSCF/registrar's application-level decision, not
  a transport/parser defect (parser defect already fixed).
- Standards-derived IMPU `sip:<IMSI>@ims.mnc008.mcc204.3gppnetwork.org` is
  *one* correct fallback (TS 24.229 5.1.1.1A), but the SIM has a real ISIM
  whose EF_IMPU/EF_IMPI/EF_DOMAIN may carry KPN's actual identities. Reading
  those EF records read-only (UICC TRANSMIT, main=6 sub=5 type=2, recovered
  layout) is the next legitimate identity step. Note: the CP rejected our
  OPEN CHANNEL attempts (GEN 0x8001) — the exact OPEN CHANNEL payload byte
  offsets must be re-derived before EF_IMPU can be read.

## UICC channel breakthrough (round 18)
- Vendor `IpcProtocol41Iil::IpcTxOpenUiccChannel` wire decoded from rodata
  @0x142048: FMT `main=5 sub=6 type=2`, payload `01 00 70 00` (card/type 0x01,
  aid-len 0x00). Sent live: **accepted**, reply `05 06 02 00 02 6e 00`
  (status 0, channel 0x6e). Previous `0x8001` was a wrong payload.
- `IpcTxTransmitEcccccbhPci` (main=6 sub=5 type=2) wire:
  payload = `[aid_len_p2][aid_p4][file_id u16][p1][p2][p3][data...]`; the
  APDU is allocated from the *source* length, not transmitted length.
  Remaining local step: pin the exact transmit length field so the CP stops
  returning 0x8001, then SELECT/READ EF_DOMAIN(6F03), EF_IMPI(6F04),
  EF_IMPU(6F02) read-only and compare with the IMSI-derived IMPU.

## Exact next concrete operations
1. Fix TRANSMIT APDU length/command per the read handler (0x3429c8); read
   ISIM EF_DOMAIN, EF_IMPI, EF_IMPU read-only using channel 0x6e.
2. If EF_IMPU/domain differ from the derived IMSI IMPU, use them for REGISTER
   and re-test. If identical, the 480 is a carrier/P-CSCF service decision for
   this AP-originating registration.
3. To conclusively separate "Nuxel SIP" from "carrier requires stock IMS AP
   client": register the SAME SIM in a stock/known-good IMS handset (owner
   action) OR confirm with KPN whether IMS is provisioned for this SIM.
4. Keep message 4 held; only release after genuine 200 OK + SMS readiness.

## Preservation
- LTE, CID1 internet, rmnet1 IMS iface, USB, ZeroTier preserved.
- No protected-partition writes; no identity/keys extracted; no fabricated
  success. Recipient/body not recorded here.
