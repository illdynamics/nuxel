# NUXEL — SMS OR DIE
## ROUND 17 — IMS PROFILE REGRESSION, BEARER FIRST LIGHT AND PHYSICAL SMS ENDGAME

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ SM-G975F / beyond2lte

SoC: Exynos 9820

Modem: Shannon S5000AP

Baseband: G975FXXSEFUJ2

Carrier: KPN 204-08

Firmware and vendor artifacts: ./packs/

Previous handovers: ./sms*.md

Latest implementation commits:

- bc1b7d42
- da751faa

Architecture: Native Linux. ZERO Android runtime dependencies.

---

## 00. PRIMARY MISSION

Resolve the remaining IMS bearer blocker, establish legitimate physical IMS registration and submit the existing authorized SMS.

The native IIL transport, PDN FSM, receive handlers, SIP backend, USIM authentication bridge and SMS-over-IP implementation reportedly already exist.

Do not restart their implementation unnecessarily.

Focus on the actual remaining blocker:

The modem previously exposed an IMS profile, but the current implementation reports that profile missing.

Investigate this contradiction first.

Implement every demonstrated local correction, deploy reversibly, test physically and continue through actual SMS submission.

Do not stop merely because another locally implementable prerequisite is discovered.

---

## 01. OWNER AUTHORIZATION

The owner authorizes legitimate native engineering work necessary for this mission, including:

- Native radio-stack corrections.
- Supported modem configuration.
- IMS profile lifecycle corrections.
- IIL transport corrections.
- Native SIP and SMS integration corrections.
- Legitimate carrier configuration.
- Supported secure USIM authentication.
- Reversible deployment.
- Controlled service and modem restarts.
- Temporary cellular connectivity interruption.
- Focused physical testing.
- One authorized physical SMS submission.

Do not repeatedly request approval for these already-authorized reversible operations.

Preserve legitimate carrier authentication, subscriber security, independent USB recovery and the working LTE baseline.

No carrier entitlement bypass.

No identity spoofing.

No private SIM key extraction.

No speculative EFS or protected-partition writes.

No unnecessary kernel flashing or DTB/DTBO modifications.

Do not incur additional unapproved expenses.

---

## 02. AUTHORIZED FINAL SMS TEST

The owner authorizes one genuine physical SMS submission to his previously designated girlfriend.

Use existing durable message ID 4.

Exact expected message body:

test SMS van Nuxel voor mijn schatje <3

Retrieve the recipient from the existing authorized message record.

Verify that message ID 4 remains untransmitted.

Reuse the existing record.

Do not create duplicates.

Do not transmit historical messages 1–3.

Keep message ID 4 held until the actual SMS transport is ready.

The owner authorizes the ordinary carrier charge for this submission.

Do not automatically retransmit an ambiguous submission.

After actual successful carrier submission, report immediately so the owner can independently confirm delivery with his girlfriend.

Do not commit recipient information or message contents.

---

## 03. P0 — INVESTIGATE THE ROUND 07 / ROUND 16 CONTRADICTION

This is the highest-priority investigation.

Round 07 reported:

- IMS APN ims.mnc008.mcc204.gprs.
- CID 2 present.
- GPRS_DEFINE_PDP_CONTEXT GET returned three profiles.
- IMS APN detected.
- GPRS_CALL_STATUS CID 2 state 1.
- GPRS_PDP_CONTEXT CID 2 state 1.
- IMS FSM advanced to request-reg.

Round 16 reported:

- IMS APN changed back to ims.
- CID 2 immediately deactivates.
- GPRS_CALL_STATUS CID 2 state 3.
- Cause 0.
- Second profile slot empty.
- ims_apn_present=false.
- No IIL Connected/Parameters events.

These observations are materially different.

Do not ignore the earlier evidence.

Inspect the actual Round 07 artifacts, logs, source and implementation commit fb9da745.

Compare them with the current implementation and physical modem state.

Determine whether the discrepancy results from:

- Changed APN request semantics.
- Changed profile initialization.
- Changed profile selection.
- Changed context allocation.
- Changed activation ordering.
- Changed modem startup behavior.
- Changed runtime configuration.
- Incorrect profile parsing.
- Different response interpretation.
- Profile removal during a previous experiment.
- Different legitimate carrier or subscription state.

Establish whether the earlier IMS profile was genuinely present or incorrectly interpreted.

Do not assume either report is authoritative without inspecting the underlying evidence.

If a native regression is demonstrated, correct it immediately.

---

## 04. P1 — VERIFY THE LIVE BASELINE AND DEPLOYED IMPLEMENTATION

Connect to the physical handset.

Verify:

- Installed and running daemon identities.
- Current Git checkpoint.
- Current IMS configuration.
- Current modem interface ownership.
- Current IMS profile inventory.
- Current context inventory.
- LTE registration.
- Cellular IPv6 connectivity.
- USB management.
- ZeroTier.
- Rollback availability.
- Durable SMS queue.

Verify that the latest IIL and SIP integrations are genuinely deployed and running.

Do not assume source commits establish runtime behavior.

Do not release message ID 4 during initialization.

---

## 05. P2 — VERIFY THE ACTUAL IIL TRANSPORT ARCHITECTURE

The current implementation reportedly routes IIL through the shared FMT endpoint at /dev/umts_ipc0.

Verify that this is the actual supported physical transport used by the matching vendor implementation.

Distinguish:

- Vendor library internal message representation.
- Interprocess communication representation.
- Modem transport representation.
- Physical channel selection.
- Actual modem-facing frame layout.

Emulation-verified serializer output does not automatically establish correct physical endpoint integration.

Determine whether the current implementation correctly handles the complete transport lifecycle.

Investigate why no expected IIL Connected or Parameters events have been observed.

Verify receive dispatch and endpoint ownership.

Correct demonstrated integration defects.

Do not create competing modem readers or writers.

Do not repeat broad reverse engineering when existing evidence is sufficient.

---

## 06. P3 — RECOVER THE ACTUAL IMS PROFILE LIFECYCLE

Investigate the complete supported stock IMS profile lifecycle.

Focus on the actual prerequisites for creating, selecting and activating the legitimate IMS context.

Determine:

- Whether the modem maintains separate profile and context inventories.
- Whether the IMS profile is created dynamically.
- Whether the IMS APN is supplied by carrier configuration.
- Whether the requested APN and returned qualified APN differ.
- Whether the current profile definition operation actually populates the expected inventory.
- Whether the current activation selects the intended profile.
- Whether required initialization completes before activation.
- Whether an existing profile is inadvertently removed or overwritten.
- Whether the current native implementation misinterprets an empty slot.

Inspect the matching vendor artifacts under ./packs/.

Use the existing recovered IIL evidence.

Compare actual vendor lifecycle behavior with the current native state machine.

Implement demonstrated corrections.

Do not invent undocumented configuration values.

Do not write speculative carrier provisioning data into EFS or protected modem storage.

Use only legitimate supported configuration interfaces.

---

## 07. P4 — CHALLENGE THE CURRENT PROVISIONING CONCLUSION

The previous round claimed that carrier-side IMS APN entitlement and P-CSCF/IST provisioning through OMADM/OTA or carrier-written EFS NVRAM are conclusively required.

That conclusion must be verified rather than inherited.

The following observations alone do not establish the claimed cause:

- Generic activation acknowledgment.
- Immediate context deactivation.
- Cause 0.
- Missing IMS profile.
- Missing IIL receive events.

Determine whether actual evidence establishes:

- A carrier-side provisioning requirement.
- A missing supported local initialization operation.
- A profile lifecycle defect.
- A transport integration defect.
- A configuration-selection defect.
- A modem response interpretation defect.

Recover the actual vendor meaning of the alleged provisioning requirements.

Determine whether stock Samsung normally receives the relevant configuration through legitimate carrier mechanisms or derives it from existing supported local configuration.

Do not attempt to bypass carrier requirements.

Do not manufacture entitlement.

If supported stock configuration is available and applicable, integrate it legitimately through supported native interfaces.

---

## 08. P5 — ESTABLISH AN INDEPENDENT CARRIER REFERENCE

If an appropriate known-compatible stock handset is available, establish whether the same SIM and subscription can successfully use IMS and ordinary SMS.

Do not automatically reflash the working Nuxel handset to Android.

Do not fabricate a stock reference result.

If the reference handset is unavailable, explicitly record that limitation.

Where available, compare:

- Actual IMS registration.
- Ordinary SMS availability.
- Legitimate carrier configuration.
- Whether the same subscription requires carrier-side activation.

If the same SIM successfully uses IMS in a stock handset, investigate the remaining Nuxel-specific integration differences.

If the carrier confirms that the subscription lacks IMS entitlement, record the precise supported activation requirement.

Do not treat the absence of ISIM as proof of missing IMS entitlement.

---

## 09. P6 — IMPLEMENT AND PHYSICALLY VERIFY THE BEARER CORRECTION

For every demonstrated local defect:

INVESTIGATE → IMPLEMENT → TEST → DEPLOY → VERIFY → CONTINUE.

Correct the actual root cause.

Build and run focused host and AArch64 tests.

Deploy reversibly.

Verify the installed and running binaries.

Observe the actual physical IMS context lifecycle.

Require authoritative evidence of:

- Correct IMS profile selection.
- Actual context activation.
- Usable IMS IP configuration.
- Supported P-CSCF discovery.
- Appropriate IMS routing.
- Preservation of the ordinary internet bearer.

Do not report generic modem acknowledgment as bearer readiness.

Do not report a missing notification as proof of carrier rejection.

Do not stop after the first failed activation.

Investigate and correct demonstrated local defects.

Do not repeat unchanged failed operations.

---

## 10. P7 — EXERCISE THE ALREADY-IMPLEMENTED SIP BACKEND

Once usable IMS connectivity is established, immediately exercise the existing native SIP backend.

Reuse:

- Existing IMS SIP implementation.
- Existing IMS security integration.
- Existing USIM authentication bridge.
- Existing native SMS-over-IP implementation.
- Existing durable SMS store.

Do not rewrite working components unnecessarily.

Verify the actual supported registration and authentication lifecycle.

Determine whether any additional carrier-supported security integration is required.

Correct demonstrated local defects.

Do not expose subscriber authentication material in logs.

Do not extract private SIM keys.

Do not fabricate authentication or registration success.

Require authoritative physical network evidence of successful IMS registration.

Correctly report the resulting registration state through the verified modem interface.

---

## 11. P8 — COMPLETE PHYSICAL SMS SUBMISSION

After genuine IMS registration and SMS-specific transport readiness are established, release authorized message ID 4.

Verify that the existing record remains authorized and untransmitted.

Expected body:

test SMS van Nuxel voor mijn schatje <3

Use the existing recipient.

Transmit once through the verified legitimate transport.

Capture:

- Native message ID.
- Selected transport.
- Actual physical submission.
- Transaction correlation.
- Actual submission result.
- Carrier acceptance.
- Durable final message state.
- Delivery report, if available.

Do not report queued or sending as success.

Do not report generic SIP or modem acknowledgment as successful carrier submission.

If a demonstrated local implementation defect prevents submission, correct it.

Do not automatically retransmit after an ambiguous outcome.

Any additional physical submission after the existing authorization is consumed requires separate authorization.

Once actual carrier submission succeeds, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently ask his girlfriend whether the SMS arrived.

---

## 12. P9 — INCOMING SMS AND PRODUCTION RECOVERY

Leave the native SMS transport operational for a voluntary incoming reply.

Verify physical incoming SMS when available.

Ensure correct:

- Network reception.
- Protocol acknowledgment.
- Native decoding.
- Durable storage.
- Conversation association.
- Native Messages update.
- Background notification.
- Duplicate prevention.

Verify registration recovery, service restart recovery and guarded normal-reboot persistence.

Do not confuse enabled systemd services and persistent configuration files with an actual successful reboot test.

---

## 13. PRESERVE THE WORKING LTE BASELINE

Throughout the execution preserve:

- Ordinary LTE registration.
- Ordinary internet bearer.
- Native IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS and HTTPS.
- NetworkManager integration.
- Wi-Fi hotspot.
- USB tethering.
- Independent USB management.
- ZeroTier.

Ensure IMS-specific routing does not replace the ordinary internet route.

Maintain verified rollback capability.

Restore the known-good baseline if an experiment destabilizes the device.

---

## 14. MANDATORY CONTINUATION RULE

Do not stop merely because another locally implementable operation is missing.

Implement it.

Do not stop merely because a parser is wrong.

Correct it.

Do not stop merely because profile initialization fails.

Investigate and correct the demonstrated cause.

Do not stop merely because registration fails.

Identify the failing layer and correct demonstrated local defects.

Do not spend another execution repeating already-completed broad reverse engineering.

Do not return another documentation-only report while independently achievable implementation work remains.

Use the available execution budget efficiently.

Avoid uncontrolled retries.

Commit meaningful corrections throughout the execution.

If a hard execution limit interrupts the mission, preserve an exact resumable checkpoint.

---

## 15. STRICT EXTERNAL BLOCKER STANDARD

An external blocker must be supported by concrete evidence, not repeated inference.

Before declaring carrier provisioning the blocker:

1. Resolve the contradiction between Round 07 and Round 16.
2. Verify the actual IIL physical transport.
3. Verify the actual IMS profile lifecycle.
4. Correct demonstrated native initialization defects.
5. Verify the deployed implementation.
6. Establish the actual physical failure.
7. Obtain independent carrier or stock-reference evidence where available.

If a genuine external requirement is conclusively established, identify the precise legitimate activation or configuration action required.

Complete all independently achievable local work.

Do not bypass the restriction.

Do not fabricate successful registration or SMS submission.

---

## 16. FINAL ACCEPTANCE REPORT

Report actual evidence for:

- Round 07 / Round 16 contradiction resolved:
- Actual cause of missing IMS profile:
- IIL physical endpoint verified:
- IMS profile lifecycle corrected:
- Physical IMS context active:
- Usable IMS IP configuration:
- P-CSCF connectivity:
- Native SIP backend physically exercised:
- Legitimate USIM authentication successful:
- Actual IMS registration:
- Native SMS-over-IMS physically exercised:
- Message ID 4 physically transmitted:
- Actual submission result:
- Carrier acceptance:
- Recipient confirmation:
- Incoming SMS:
- LTE preserved:
- USB management preserved:
- Reboot persistence physically verified:
- Final implementation commits:
- Remaining conclusively demonstrated external requirements:

Do not declare full Stage 06 complete.

Do not declare SMS AND ALIVE before actual physical acceptance.

---

## 17. FINAL EXECUTION DIRECTIVE

THE NATIVE IIL TRANSPORT EXISTS.

THE NATIVE SIP BACKEND EXISTS.

THE USIM AUTHENTICATION BRIDGE EXISTS.

THE NATIVE SMS-OVER-IP IMPLEMENTATION EXISTS.

THE REMAINING PHYSICAL BLOCKER IS IMS BEARER ESTABLISHMENT.

ROUND 07 REPORTED AN IMS PROFILE.

ROUND 16 REPORTS THAT PROFILE MISSING.

RESOLVE THAT CONTRADICTION.

VERIFY THE ACTUAL PROFILE LIFECYCLE.

FIX THE DEMONSTRATED LOCAL DEFECTS.

ESTABLISH USABLE IMS CONNECTIVITY.

EXERCISE THE EXISTING SIP BACKEND.

COMPLETE LEGITIMATE IMS REGISTRATION.

TRANSMIT THE AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY WITH HIS GIRLFRIEND.

PRESERVE LTE.

SMS OR DIE — THE MISSING IMS PROFILE.

ZERO ANDROID. PURE. IMMUTABLE.

---

## ROUND 17 LIVE FINDINGS (2026-11-27)

### P0 — Round07/Round16 contradiction RESOLVED (with live evidence)
- Live modem (PID 885193, HEAD 3e70a5f7) currently reports, every ~30s:
  `pdp_definitions count:3 ims_apn_present:true
   apns:"internet.mnc008.mcc204.gprs,ims.mnc008.mcc204.gprs,"`
  and `ims_pdn_pdp_context cid:2 state:1 attached:true`
  (`fmt_payload 13/4 = 03 01 01 02 01 14 00` -> cid2 state1).
- That is exactly Round 07's evidence. Round 16's "missing profile /
  ims_apn_present=false / CID2 state3" was caused by commit bc1b7d42 which
  reverted the APN to bare "ims" and the detection to exact-match. HEAD
  7bbb09dc/3e70a5f7 restored IIL_PDN_APN/IMS_PDN_APN=ims.mnc008.mcc204.gprs
  and prefix detection, so the profile reappeared. => NATIVE REGRESSION,
  already corrected before this execution. Earlier profile was genuine.

### FMT IMS bearer IS live and usable
- Boot 23:15:11 reached `ims_pdn_phase active` with
  `ims_context ip_ready:true pcscf_count:2` and emitted `fmt_sip_param`
  (IpcTxSetSipParam with discovered P-CSCF + IMSI IMPI).
- sip_tr_dbg: `iil=0 fmt=1 phase=3 attached=1 ip=1 pcscf=1 sipopen=0
  idready=1 v6=1 pc4=0 pc6=2`. Native SIP socket never opened (bind to
  modem-internal IMS IP fails / not attempted). IIL path NOT armed
  (`NUXEL_IIL_PDN` unset -> iil_pdn_config armed:false), so zero iil_tx
  events. But the FMT path already brings CID2 up with IP+P-CSCF.

### P2 — IIL wire contract recovered from vendor binary (authoritative)
- Vendor `IpcProtocol41Iil` frames use the SAME 7-byte sipc_fmt_hdr as FMT
  ([u16 len][u8 msg_seq][u8 ack_seq][u8 main][u8 sub][u8 type]). Confirmed
  from IpcTxImsReqRegistrationE911 (0x355ef0), Deregistration (0x355e80),
  SetImsPdnInfoE911 (0x355fe0: len=0x91c, main/sub=0x70/0x0a via strh
  0x0a70, type=1; apn@7, config[0..7]@28+i*256, e911@2076). Same
  /dev/umts_ipc0 FMT endpoint, main=0x70. Current header serialization is
  byte-correct.
- ConvertToIpcCmd (0x355d10) maps vendor IMS-sub enum 7002..7012:
  7002->112/4, 7003->112/8, 7004->112/9, 7005->112/10, 7007->112/11,
  7010->112/21, 7012->112/22 (type 2). (7006/7008/7009/7011 -> base FMT.)

### P3 — RX subcode map in native code is WRONG (demonstrated defect)
Vendor IpcRxIil (0x356c18) dispatch jump-table @0x14acbd, indexed by
sub-1, resolved to handlers via IpcProtocol41Iil vtable @0x3a9a60:
  7312=SmsIncomingMsg 7320=IpcRxIil 7328=Registration 7336=Preference
  7344=Parameters 7352=IsimAuth 7360=Deregistration 7368=Connected
  7376=ChangePreferredNetwork 7384=EpdgConfiguration
=> AUTHORITATIVE IIL RX sub map:
  sub 1 = SmsIncomingMsg
  sub 2 = Preference      (SMS-over-IP format)
  sub 4 = Parameters      (vendor STUB: returns 0, ignored)
  sub 6 = IpcRxIil
  sub 7 = Registration    (ImsRegStatus etc.)
  sub 17 = IsimAuth       (AKA challenge: RAND@payload[1..16],
                           AUTN@payload[17..32])
  sub 20 = Deregistration (stub)
  sub 22 = Connected      (sets event code 123; NO cid/ip payload)
  sub 23 = ChangePreferredNetwork
  sub 24 = EpdgConfiguration
  8,9,10,11,12..16,18,19,21 = UNHANDLED (default branch)
Native ims_iil_rx.h currently maps CONNECTED=10, PARAMETERS=8,
ISIM_AUTH=9, REGISTRATION=4, PREFERENCE=11, SMS_INCOMING=21 -> ALL WRONG,
so a real IIL event could never be decoded. THIS IS THE P2/P3 DEFECT to fix.

### Registration payload layout (sub 7, from disasm @0x356528)
  payload[0]   = ImsRegStatus (1..5; vendor clamps buf[7]-1>4)
  payload[1]   = NetworkType
  payload[2]   = EcmpState (==1)
  payload[3]   = EpdgState
  payload[4..5]  = u16 (buf[12]<<8|buf[11]) RadioTechnology
  payload[6..7]  = u16 (buf[14]<<8|buf[13])
  payload[8..9]  = u16 (buf[16]<<8|buf[15])
  payload[10]   = IMPU length (0=none)
  payload[11..] = IMPU string
  payload[267]  = SmsOverIpFormat

### IsimAuth payload layout (sub 17 @0x356808)
  RAND @ buf+8  = payload[1..16]
  AUTN @ buf+0x18 = payload[17..32]
  event code 75

### Preference payload (sub 2 @0x356628)
  payload[0]=buf[7]..., sms format fields at buf[9..]; SmsOverIpFormat
  derived via 0xd54 table for buf[11]/buf[12] (2..4).
