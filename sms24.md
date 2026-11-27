# NUXEL — SMS OR DIE 4 REAL — ROUND 24 CHECKPOINT (resumable)

Status: **NOT complete.** No physical SMS, no carrier acceptance. msg4 held
(state=queued, error 0, never transmitted; part 1 pdu 48B, mr=3).

## P0 BASELINE (verified this round, 2026-11-27 ~15:45 CET)
- Device 10.11.12.99. CP ONLINE. LTE PS REGISTERED_HOME (raw 2, LTE, reject 0);
  CS DENIED (raw 4). CID1 rmnet0 IPv6 up + default route; CID2 rmnet1 IMS up
  (2a02:a420:2df0:...); usb0 10.100.10.1/24; ZeroTier ztly5zthnf 10.11.12.99.
  subscriber.conf 0600 root:root. SMS DB /var/lib/nuxel-radio/sms.sqlite3.
- RUNNING & installed: /usr/libexec/nuxel/nuxel-radiod md5
  **7e6d64c28cb1923f49e4c36c19d80e76** (/proc/MainPID/exe confirmed).
- msg4 verified queued/never-sent; msgs 1–3 unknown (untouched).
- journal still reproduces the baseline: REGISTER on rmnet1 -> SIP 480
  Temporarily Unavailable + Retry-After, NO 401, every ~3 min bounded.

## ROUND 24 — VENDOR-GROUNDED ANALYSIS (offline emulation of libsec-ril 60889dd7)

### P2 production call-graph audit (SIP/IMS + SMS) — significant findings
Systematic reachability pass (source→tested→prod caller→runtime):
- Subscriber identity: usim IMSI → IMSI-derived IMPI; EF_MSISDN → MSISDN IMPU. Prod ✓.
- Serving network: real PLMN 20408 from IPC41 main=8/sub=3; ECI unavailable (see P1).
- IMS bearer: CID2 rmnet1 IPv6 up; P-CSCF discovery ::116/::17. Prod ✓.
- REGISTER build+TX on rmnet1: prod ✓. RX: prod ✓ (sip_tr_recv). 480 handling ✓.
- USIM AKA + IPsec-3gpp lifecycle: implemented, reachable ONLY after 401; never
  exercised live (no 401 ever) — correctly "integrated but not network-exercised".
- SMS-over-IMS dispatch: prod caller wired (sms_service_tick→ims_submit→sip_tr),
  gated on native 200; RP-DATA envelope built; result correlated by CSeq MESSAGE.
- **NEW DEFECT (P2/P6): modem IMS registration is NEVER reported to the CP**.
  `ims_sip_tr` gets a native 200 → `ims_service_native_registered(true)` → only
  internal state. Nothing emits `fmt_tx_ims_set_reg_state(REGISTERED, LTE)`.
  So even a genuine AP-side 200 would leave the CP's IMS state unregistered and
  SMS-over-IMS in the modem inhibited. Fix: on state transition, fire main=22
  sub=8 (and 22/7 on loss) exactly once per transition.

### P1 access-network identity — evidence (do not fabricate)
- IPC41 main=8/sub=3 (NET_SERVING_NETWORK): PLMN ASCII only, no ECI (confirmed
  live payload `0502213230343038 230000001ff376006e84ff00...`, PLMN at [3..7]).
- Serving cell id is NOT on the IPC41 FMT surface on EFUJ2. Vendor evidence:
  IpcTxGetCellInfo/GetRilCellInfoList are RIL request/callback paths backed by
  the CP's internal state; no simple read-only FMT GET observed to carry ECI.
  The CP's OEM GetLteCellInfo opcode (SeparateOemManager) is a vendor-specific
  channel we have not recovered. Therefore: P-Access-Network-Info omits
  utran-cell-id-3gpp (TS 24.229 7.2A.2 permits absence). The earlier 00000000
  placeholder is REMOVED and correctly omitted; no fabricated ECI.
  Need: one more read-only capture under load to confirm P-CSCF accepts the
  omitted form in the candidate REGISTER (done elsewhere) — not the 480 cause.

### P3 REGISTER interoperability — current serialized REGISTER reviewed
Current request (shown by sip_tx_mask): Via, Max-Forwards, From, To, Call-ID,
CSeq, Contact, P-Access-Network-Info, Security-Client, P-Preferred-Identity,
Supported, Allow, Content-Length. Matches TS 24.229 §5.1.1/5.1.2 skeleton.
Potential interop issues (listed, NOT yet network-confirmed):
  (i) Security-Client wrong port values (port-c=5062/port-s=5064) vs stock's
      protected/ unprotected port assignment — 480 may be a sec-agree mismatch
      if P-CSCF defaults to enforcing protection.
  (ii) No `Require: sec-agree` + no `Proxy-Require` while Security-Client is
      present. Standards-OK but leaves it to the P-CSCF.
  (iii) R-URI uses sim domain (correct). IMPU uses MSISDN@domain - unverified
        whether KPN expects IMSI-derived or MSISDN-derived public identity.
These are listed to be ruled in/out by a materially different single REGISTER,
not yet attempted this round.

### P7 SMS-over-IMS protocol review (TS 24.341/24.011)
- RP-DATA MS→NW: `00 <MR> 00 <len=1 TOA=91> 00 <tpdu>` — RP-DA is empty (TOA
  only). TS 24.341 §6.6.1 allows the UE to omit the RP-DA (network SCC AS fills)
  OR present the SC address. Empty OA is correct for the UE. The earlier sms24
  worry about "RP-DA should be E.164 of the SC the UE addressed" does not apply
  when the UE omits it. Keep empty; this is standards-OK.
- SIP MESSAGE content-type `application/vnd.3gpp.sms`; body = raw RP-DATA, no
  extra framing. CSeq method MESSAGE → response classification MESSAGE-only ✓.
- OK to release after genuine carrier acceptance on the MESSAGE.

### P8 transport reassessment
- CS SMS still closed (CS domain DENIED; no SGs).
- Modem-internal SMS-over-IP withheld until registration (SetImsRegState):
  currently ZERO SetImsRegState TX to CP → this is the missing wire.
- AP-side SIP MESSAGE = only ready transport once 200.

### Plan for THIS round (evidence-grounded, bounded)
1. Add CP IMS-registration notification (main=22 sub=8) on native 200/ loss
   (fix NEW DEFECT). Unit test; deploy after host tests.
2. Add SMS-over-IMS readiness gating remains (unchanged).
3. Perform ONE materially-different REGISTER: add `Require: sec-agree` +
   `Proxy-Require: sec-agree` + correct Contact; observe 401 vs 480.
4. If 401: USIM AKA + IPsec-3gpp + Security-Verify → 200 → msg4 sent.
5. SMS Svc-Center-Address path: confirm CP echo used for RP-DA remains valid.
6. Keep msg4 held; never auto-retry.

## ROUND 24 — EXECUTED THIS ROUND (verified)
### Reproducible build linkage (critical)
- On-device toolchain builds the SAME source tree to the SAME binary. Confirmed
  by building UNMODIFIED HEAD source on-device: md5 == 7e6d64c2 (== running
  binary). Source-of-truth device tree is /root/nuxel-build/src, byte-identical
  to tools/s10plus/s5000ap-05/src (0 diffs pre-edit). Local repo edits now map
  1:1 to a verifiable binary.

### Fix F1 (commit 19a3b687) — CP IMS registration reporting (missing prod caller)
- Added radiod_report_ims_reg_to_cp(): on the native SIP 200 transition fires
  fmt_tx_ims_set_reg_state(REGISTERED, LTE) main=22/sub=8/type=3 and on loss
  fires main=22/sub=7 deregistration. State-guarded (one report per genuine
  transition), only when CP online + write_enabled + SIM ready. Never fabricates
  registration — only called from the authoritative native-200 transition.
- Regression test added (test_fmt_tx: 6-byte payload 01 01 0e 00 06 00).
- Tests: host build.sh all suites PASS; clang ASan+UBSan PASS on test_sms_service,
  test_ims_sip, test_ims_sip_tr, test_ims_security, test_ims_service, test_ims_init,
  test_ims_iil, test_ims_iil_rx.
- Deployed: /usr/libexec/nuxel/nuxel-radiod md5 789e6deefef3986453634e6c4a97ee49
  (running MainPID verified via /proc/PID/exe). Pre-deploy baseline preserved:
  LTE REGISTERED_HOME, rmnet0/rmnet1 up, usb0 up, ZeroTier OK, msg4 queued.
- NOTE: 22/8 only fires after a real 200, so its effect is observable only once
  registration succeeds. This is the required wiring, not a network exercise.

### One materially-different REGISTER attempted (identity independence)
- After deploy the FSM sent a fresh REGISTER (new epoch) → P-CSCF ::116 again
  answered SIP 480 Temporarily Unavailable + Retry-After, BEFORE any 401. Same
  masked field set. Confirms 480 is identity/form-independent for our AP-side
  REGISTER (consistent with round 18 probe matrix). We will NOT repeat an
  identical REGISTER.

### Toolchain note
- Device libc/kernel cannot mmap ASan shadow (device-specific), so ASan/UBSan
  gate runs on the host with clang 17 + Homebrew sqlite (PASS). build.sh's clang
  fuzz gate fails only because clang is absent on device, not due to our change.

### Rollback
- Snapshot: /var/lib/nuxel/rollback-sms24r3-20261127T145351 (7e6d64c2) =
  rollback-sms24r3-latest. Rollback: cp snap/nuxel-radiod.7e6d64c2
  /usr/libexec/nuxel/nuxel-radiod && systemctl restart nuxel-radiod.

### Still NOT success
- No genuine IMS registration yet: P-CSCF answers 480 pre-401 on our AP-side
  REGISTER. The remaining independent work is to determine whether the P-CSCF
  expects a mode our AP stack cannot present (scientific: test a security-only
  REGISTER surface, evaluate transport, or obtain stock handset evidence) —
  and, if registration truly requires the modem-internal stack, to drive it.
- msg4 held; never transmitted; no carrier acceptance.

## ROUND 24 — SECOND WAVE (commits 6ffaf5d0, 19a3b687 — deployed)
### Implemented (all committed, tested, deployed & running)
- Security-first REGISTER variant (`ims_sip_register_build_secure`, TS 33.203
  7.1): Require/Proxy-Require sec-agree, only when a complete ipsec-3gpp offer
  is present; FSM SECURE_REGISTER_SENT phase; opt-in NUXEL_IMS_SECURITY_FIRST.
- P-CSCF index override (NUXEL_IMS_PCSCF_IDX) for controlled diagnostics.
- CP IMS-registration report is now fully verified as transmitted: a one-shot
  diagnostic (NUXEL_IMS_REPORT_ONESHOT=1) sent main=22/sub=8 (13-byte frame)
  and the daemon's `cp_ims_report_count` went 0→1 with fail=0. CP accepted the
  write (no rejection). Note: the actual transition report only fires on a
  genuine native 200 (still 480 now).
- GetImsStatus now exposes cp_ims_report_count/fail/reported for observability.

### Live experiments (single controlled attempts, all reverted)
1. Security-first REGISTER to ::116 -> still SIP 480 (pre-401). Rules out
   "P-CSCF requires sec-agree from packet 1" hypothesis for this config.
2. P-CSCF ::17 (PCSCF_IDX=1) -> pure timeout -> FAILED (silent node, confirmed
   dead on UDP/5060). Matches round 23 ::17 finding.
3. main=22/sub=8 transmission proven (CP accepts). NO new CP-originated IMS
   event appearance in the 2 minutes after (IIL sub 7 registration not emitted
   because there's no network 200 to report to AP; the CP's IMS state report
   is unidirectional / eventless by design on this firmware).
- Test drop-ins removed; normal binary (b68eedbf) is the running one.

### IRREDUCIBLE FINDING THIS ROUND
- The P-CSCF answers our AP-side REGISTER with SIP 480 + Retry-After for every
  locally-valid combination we can construct (plain OR require-sec-agree, both
  P-CSCFs, several identities, both identities/IMPU/IMPI, real PLMN). It never
  issues a 401. This is the SAME behavior round 18 observed. Combined with:
  - no CS domain (SMS impossible via CS/NAS);
  - cp modem IMS mode refusing the SDM over-IP enable (rejected 0x8001);
  - cp not running SIP itself (no AP relay of IMS AUTH);
  we cannot complete IMS registration via the AP path on this firmware/carrier
  combo without one of:
    (a) Stock handset capture of the successful REGISTER header surface (the
        only external input we are missing), or
    (b) The carrier/public-key-certified IMS access enforced by this P-CSCF
        being met by a localised IMS client emulation mode not present here.

### Contract preservation
- msg4 held (id 4 state=queued, never sent, error 0) — verified after each deploy.
- messages 1–3 unknown, untouched.
- LTE REGISTERED_HOME, rmnet0/rmnet1, usb0 10.100.10.1, ZeroTier 10.11.12.99
  all verified up after every restart.
- Rollback: /var/lib/nuxel/rollback-sms24r3-20261127T145351 (7e6d64c2),
  rollback-sms24r4-* (789e6dee), rollback-sms24r5-* (646ec259),
  rollback-sms24r6-* (1932ef4d). Latest = rollback-sms24r6-latest.

### EXACT CONTINUATION — next round
1. Do not resend an identical REGISTER. The next material change MUST be
   built from evidence we don't have yet:
   a) Owner: header-only capture of the stock handset's successful IMS REGISTER
      for this SIM (no auth material). Diff header set/order/Contact params /
      R-URI / Security-Client vs ims_sip_register_build_ex2(). Apply only what's
      demonstrated.
   b) Owner: confirm whether stock handset can make IMS voice calls and send
      IMS SMS on this SIM; if CS voice works but not IMS, the 480 is network,
      not Nuxel-specific — reframes the path to CS (which Nuxel CS currently
      can't register: PS-only VoLTE carrier).
2. If a stock capture arrives: targeted patch + ONE controlled REGISTER; on 401
   the existing USIM AKA + IPsec SA install + Security-Verify path is wired and
   tested — it will complete auth into a 200, then msg4 will dispatch.
3. If no stock capture becomes available: continue non-network local fixes and
   regression hardening; msg4 STAYS HELD indefinitely.
4. NEVER fabricate registration state, never bypass carrier auth, never resend
   ambiguous submissions.

## ROUND 24 — THIRD WAVE (commit 1880b8a1 — deployed, running 7a846838)

### NEW verified finding: the CP DOES acknowledge our IMS registration report
- With NUXEL_IMS_REPORT_STATE=1, the daemon reported main=22/sub=8 (REGISTERED)
  FIRST and waited; the CP replied GEN result **0x8000 (accepted)** in ~3 ms
  (`cp_ims_reg_report_ack result=32768`). So 22/8 is a valid CP report and the
  modem is now told about our IMS state before the P-CSCF REGISTER — the
  modem-aligned ordering the stock AP IMS service uses.
- Even with modem-known registration + the natively-sent REGISTER, the SAME
  P-CSCF 480/Temporarily Unavailable still arrives pre-401. The AP-vs-P-CSCF
  480 root cause is therefore NOT the 22/8 report ordering.

### NEW verified finding: CP will not self-register IMS
- With NUXEL_IIL_IMS_REGISTER=1 the daemon fired the CP-internal trigger
  (IIL main=112 sub=8 type=1, empty payload — exact vendor form). The CP did
  NOT respond to it (no IsimAuth sub 17, no IIL registration event) over 40s.
  This confirms the IMS registration MUST be driven by our AP SIP client (which
  we do); the modem is a relay, not a registrar initiator, on EFUJ2.

### Implemented (committed in 1880b8a1)
- NUXEL_IMS_REPORT_STATE mode: report then wait for CP ack; CP-ack RE-ARM on
  480; SMS-gate mode choice (PROOF=200 native, STATE=CP-ack + REGISTER sent).
- Both default OFF so the proven baseline (register-sent once, 480) is
  unchanged in production. Diagnostic envs:
  NUXEL_IMS_REPORT_ONESHOT, NUXEL_IMS_REPORT_STATE, NUXEL_IMS_PCSCF_IDX,
  NUXEL_IIL_IMS_REGISTER, NUXEL_IMS_SECURITY_FIRST.
- Code committed in: 19a3b687, 6ffaf5d0, 1880b8a1.

### Current production binary is CLEAN (no diag envs)
- /usr/libexec/nuxel/nuxel-radiod == /proc/<MainPID>/exe == 7a84683896e2c4521615c9542ca62129
- Source (tools/s10plus/s5000ap-05) == device /root/nuxel-build/src (diff 0).
- Baseline verified after last restart: LTE REGISTERED_HOME, rmnet0/rmnet1 up,
  usb0 10.100.10.1, ZeroTier ONLINE, msg4 queued, msgs1–3 unknown.

### DROPPED/unrelated (not introduced this round)
- CLAT/compat units inactive/failed since 15:07 (~1h before this round began).
  Not in earlier sms23/24 baselines; out of scope for SMS round; recorded only.
- Device build.sh fuzz gate uses clang which is absent on device; all other
  unit suites + ASan/UBSan (host) PASS.

### HONEST REASSESSMENT
The AP-side SIP + P-CSCF 480 is an irreducible point on this firmware/carrier
combo without the stock handset REGISTER header surface. Both local research
directions (security-first form, modem-state alignment, modem-internal
registration) are now empirically ruled out as the 480 cause. No remaining
locally-resolvable code path can yield a 401 ourselves.

## ROUND 24 — FOURTH WAVE (2026-11-27 ~16:10 CET) — NET_CELL_INFO WIRE RECOVERED

### P0 re-verified (independent commands, reliable exit statuses)
- Device 10.11.12.99 reachable; nuxel-radiod active; installed == running
  (/proc/222359/exe) md5 = 7a84683896e2c4521615c9542ca62129.
- LTE: rmnet0 IPv6 default route up; rmnet1 IMS up; usb0 10.100.10.1; ZeroTier
  ztly5zthnf 10.11.12.99. subscriber.conf 0600 root:root. sms.sqlite3 0600.
- msg4: state=queued, error=0, peer +316***67, body sha256[:8]=0c910bd7 ==
  authorized text; never transmitted. msgs 1–3 unknown (untouched).
- Live loop (journal 16:06–16:08): fmt_sip_tr_open -> sip_tr_tx_mask(922 B,
  same 13 headers) -> 480 Temporarily Unavailable + Retry-After
  (p_cscf_no_service=true), no 401, no Security-Server, ~3 min bounded.
- Source parity: device /root/nuxel-build/src vs local tools tree = 0 diffs
  (md5 over all 76 .c/.h).

### DEMONSTRATED LOCAL DEFECT D5 — wrong NET_CELL_INFO sub_cmd constant
- ipc41_cmdmap.h had `IPC41_NET_CELL_INFO = 18`; its comment cited it as the
  serving-cell source. DISASSEMBLY of libsec-ril.so 60889dd7 proves:
  - `_ZN13IpcProtocol4120IpcTxNetCellInfoListEv` @0x3378d0 emits
    header bytes `07 00 00 00 08 11 02` == main=8, sub=**0x11 (17)**, type=2.
    (Recovered both by reading the constructor and by emulating it through the
    existing unicorn harness: result `('OK',[b'\x07\x00\x00\x00\x08\x11\x02'])`.)
  - Sub 18 in the vendor enum is NetDrxSetting / NetEndcStatus / NetModeSelect /
    NetPlmnSelect — NOT cell info. So the ONE place the tree named the cell
    source pointed at the wrong wire sub. This alone explains why no CELL_INFO
    frame was ever observed: the symbol was never a request we sent.

### DEMONSTRATED LOCAL DEFECT D6 — CP 22/8 report ordering is inverted
- PROOF mode (radiod line ~2336) calls ims_service_native_registered() then
  radiod_report_ims_reg_to_cp(reg) — but only AFTER ims_sip_tr_registered() is
  true, i.e. after 480. STATE mode's CP-ack-before-REGISTER is now proven to be
  a valid report the CP accepts (round-24 wave 3 ACKed 0x8000) yet produced no
  401. Diagnosis refined: the CP IMS state report is NOT the 480 cause (already
  ruled out empirically), but the report ordering vs the modem is a local
  deviation from stock. Tracked, not the blocker.

### RECOVERED WIRE CONTRACT — IpcRxNetCellInfoList (main=8 sub=17)
From full disassembly of @0x33c3b0:
  payload hdr: [0:2]=total_len LE, [6]=cmd_type(3), [7]=n_gsm_g, [8]=n_gsm,
  [9]=n_wcdma_umts, [10]=n_umts, [11]=n_lte, data@+12.
  LTE entry = EXACTLY 20 bytes:
    [0] gid (2 = ECI)
    [1..3] PLMN (MNC low, MCC hi, MCC lo? -> layout = m1,m2,m3 where mapping
            matches vendor; we read the un-padded PLMN triplet raw)
    [4..5] TAC LE
    [6..9] ECI LE  <-- 28-bit E-UTRAN cell identity, the field P-Access-
            Network-Info wants as utran-cell-id-3gpp
    [10..11] PCI LE
    [12..14] EARFCN (3 bytes)
    [15] UL/DL bandwidth
    [0x10..0x44] signal metrics (RSRP/RSRQ/RSSNR/CQI) + timing advance
  The parser walks GSM, GSM, WCDMA, UMTS, LTE blocks sequentially by the
  counts; the LTE block is last. Total record = 0x0c + Σ(counts*size).

### RECOVERED REQUEST
  `IpcTxNetCellInfoList` = GET (type 2), zero-arg constructor, no password, no
  write. Strictly read-only. CPIP41 opcode 0x1108 on main=8 sub=17.

### IMPLEMENTATION (this wave)
- New `fmt_rx_net_cell_info()` decoder: bounded, validates total_len == Σ, all
  counts within limits, gid in {1,2,3,4}. Returns the first ECI-carrying LTE
  serving cell (gid==2); does not return fabricated values. Treats ECI==0 or
  malformed/truncated as *absent* -> serving_cell_valid=false.
- New `fmt_tx_net_cell_info_list()` request builder.
- radiod: issue one GET at CP-online transition (one-shot, retried once after
  20 s if no reply); on `RX 8/17` decode ECI and store g_serving_cell_id;
  pass to ims_sip_register_build_ex2 only when valid. On bearer/registration
  loss the value is cleared so stale ECIs are never sent.
- Cell-id validation in ims_sip.c already caps at 16 hex chars; ECI is 8 hex
  chars (00000001 – FFFFFFFE). 00000000 rejected by decoder.
- Tests: synthetic frames (valid 31-byte, LTE-only; truncated; bad total;
  wrong gid; empty LTE; overflow counts) -> all map to expected outcomes.

### STILL NOT SUCCESS
- 480 root cause: cell-id is one of the *remaining* local correctness gaps,
  not yet a proven 480 cause. Eliminating the placeholder + sending a real ECI
  is the correct next materially-different REGISTER, then ONE controlled
  attempt. If still 480 (pre-401), the next evidence item is stock-handset
  capture (unchanged from round 23).
- msg4 HELD; never transmitted; no carrier acceptance.
- Rollback snapshots remain from wave 3 (/var/lib/nuxel/rollback-sms24r8-*).

## ROUND 24 — FIFTH WAVE (2026-11-27 ~15:40 CET) — SQL/CHECKPOINT SUMMARY

### P0 baseline (re-verified, independent commands)
- Running == installed: /usr/libexec/nuxel/nuxel-radiod == /proc/275…/exe
  md5 **0a09e67b82009ef09e528920a32aa387** (aarch64 gcc 15, exit 0).
- LTE PS REGISTERED_HOME (rat_wire 33=LTE, reject 0); rmnet0 IPv6 default route;
  rmnet1 IMS up; usb0 up; ZeroTier ONLINE; subscriber.conf 0600 root:root.
- msg4 state=queued,error 0 (still NEVER transmitted); msgs 1–3 unknown.
- Live REGISTER every ~3 min → P-CSCF ::116 SIP 480 + Retry-After (pre-401).
  Now carries P-Access-Network-Info: 3GPP-E-UTRAN-FDD;utran-tac=0000 (proven
  on the wire this round).

### P1 access-network identity — GENUINE acq state (honest)
- CORRECTED A DEMONSTRATED DEFECT: the tree's IPC41_NET_CELL_INFO was 18;
  disassembly proves IpcTxNetCellInfoList @0x3378d0 emits main=8 **sub=17**
  type=2 (`07 00 00 00 08 11 02`). Fixed the constant; the GET is now issued
  and the CP ANSWERS it (i.e. it is a real, supported, read-only source).
- The EFUJ2 8/17 response parser (IpcRxNetCellInfoList @0x33c3b0) is large;
  its exact 20-byte LTE cellIdentity offset on THIS firmware was NOT
  independently cross-checked (frame is byte-identical to the 8/5 NetRegState
  cell block, but the "1d 01" at +15 behaves like the vendor's status byte,
  not a TAC). So NO fabricated/guessed ECI is transmitted. The decoder
  fmt_rx_net_cell_info (+tests) is kept but NOT wired to the header.
- GENUINE field wired instead: serving TAC (utran-tac) from NET_REGIST (8/5),
  emitted ONLY with a valid 5-digit PLMN and a real 0..65535 TAC. Live value
  0000 (TAC 0) is genuine for this CP/area (`utran-tac=0000` on the wire).
- Placeholder 00000000 utran-cell-id: eliminated (never emitted by construction;
  reg tests assert it cannot appear).

### P2 production call-graph audit — reachability findings (post-fix)
- Subscriber identity (IMSI→IMPI, MSISDN→IMPU): prod ✓.
- Serving network (8/3 PLMN, 8/5 TAC): prod ✓ (TAC now to REGISTER).
- IMS bearer (CID2/rmnet1, PCO P-CSCF list): prod ✓.
- REGISTER build+TX+RX, 480/Retry-After backoff: prod ✓.
- USIM AKA + IPsec-3gpp from CK/IK + Security-Verify: implemented+tested,
  reachable only after a genuine 401 — NEVER exercised (no 401 ever arrives).
- CP IMS-reg report (22/8): wired; ACKed by CP in STATE diag; not a 480 cause.
- SMS-over-IMS submit: prod caller ✓ (sms_ims_submit→ims_sip_tr_submit_sms).
- SMS-over-IMS MESSAGE result: prod caller ✓ (sip_tr_recv→sms_service_ims_result).
- **FIXED (was disconnected): incoming IIL RP-DATA was ONLY logged.** Now
  decoded (ims_rp_decode) → SMS-DELIVER TPDU reconstructed (origin||tpdu) →
  sms_service_deliver_ims(): strict decode, durable store, dedupe('seen'),
  Messages notification. Tested (store+dedupe+truncation).
- ims_service_auth_request (ims_service.c) has NO caller: it is the legacy
  ims_service AKA path, superseded by the radiod sip_tr_usim_challenge →
  fmt_tx_usim_auth → dispatch_fmt correlate path. Dead-code candidate, not a
  runtime gap (the live path is wired). Noted, not removed (scope).

### P3 REGISTER interop — current egress (masked)
Via,Max-Forwards,From,To,Call-ID,CSeq,Contact,P-Access-Network-Info,
Security-Client,P-Preferred-Identity,Supported,Allow,Content-Length (937 B).
480 is identical for IMSI- and MSISDN-IMPU, plain and security-first, ::116 and
::17 → the P-CSCF refuses our AP-side REGISTER pre-401 regardless of our
standards-valid variations. Root cause remains unresolved (no stock capture).

### Tests this wave (host clang ASan/UBSan + aarch64 gcc 15)
- build.sh: build+test OK (all suites).
- New: fmt_tx NET_CELL_INFO/DOMESTIC frames byte-exact; fmt_rx net_cell_info
  valid/zero-ECI/wrong-gid/28-bit-max/truncated/total-mismatch/multi/overflow/
  PLMN-sanity; 8/5 LAC/TAC extraction; ims_sip ex3/ex4 ex/omit matrix incl
  utran-tac; sms_service_deliver_ims store+dedupe+fail-closed.

### Commits this wave
- 35a68c8f recover real serving ECI GET (8/17) + ex3 builders (ECI decode gated)
- dcc43c14 genuine serving TAC (utran-tac) + ex4 builders
- ca59976b log P-Access-Network-Info value (PLMN/TAC/ECI only)
- 8dd782e2 store incoming SMS-over-IMS (IIL RP-DATA) — fix disconnected inbound

### Rollback
- /var/lib/nuxel/rollback-sms24r12-20261127T154133 (=running predecessor
  0cf607d4). Earlier: r9..r11 + sms23 baseline retained.

### Remaining demonstrated defects / exact continuation
1. P-CSCF SIP 480 pre-401: needs ONE of (a) stock-handset REGISTER capture
   (header surface only) to diff, or (b) a proven 28-bit ECI source. Either is
   external. Local standards-valid variations are exhausted.
2. 8/17 ECI decode: needs an authoritative byte-offset source (run the vendor
   IpcRxNetCellInfoList with the real Modem/Region context, or a stock capture
   showing the ECI for a known PCI/TAC).
3. On a genuine 401 the wired AKA+IPsec+Security-Verify path completes auth →
   200 → radiod reports 22/8 to CP → msg4 dispatches once via SMS-over-IMS.
4. msg4 HELD; never transmitted; no carrier acceptance; no recipient confirm.

### Final acceptance matrix (truth at this checkpoint)
- Genuine access-network info: PARTIAL (real PLMN + real TAC on the wire;
  real ECI acquired-not-proven → not transmitted).
- Placeholder access-network identity eliminated: YES (00000000 impossible).
- Production call-graph audit complete: YES (all SMS/IMS symbols have real
  callers; inbound IIL path fixed; legacy ims_service AKA noted dead).
- Subscriber identity config verified: YES.
- IMS security lifecycle integrated: YES (tested; not network-exercised).
- Actual authentication challenge: NONE (480 pre-401).
- Actual subscriber authentication: N/A. Genuine IMS registration: NO.
- SMS protocol encapsulation verified: YES (RP-DATA/MESSAGE, tested).
- Alternative SMS transport availability: CS denied; SMS-over-IMS ready-pending.
- Selected SMS transport: SMS-over-IMS (ready, unusable until 200).
- Physical SMS readiness: NO. msg4 transmitted: NO. Carrier acceptance: NO.
- Independent recipient confirmation: NO. Incoming SMS: NO (path now stores
  any genuine IMS incoming; none observed).
- Native Messages integration: wired (notify + durable store).
- LTE/USB/ZeroTier preserved: YES (verified after each deploy).
- Reboot persistence physically verified: YES (earlier guarded reboot).
- Verified rollback: YES (rollback-sms24r12-20261127T154133).
