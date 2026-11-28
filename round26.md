# NUXEL — SMS OR DIE 4 REAL
## ROUND 25.5 — ASTRA CONTINUATION AND PHYSICAL SMS ENDGAME
### DEEPSEEK V4 PRO THINKING — NO HALF MEASURES

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ / beyond2lte

Modem: Shannon S5000AP

Firmware: EFUJ2

Carrier: KPN 204-08

Architecture: Native Linux. ZERO Android runtime dependencies.

---

## 00. MISSION

You are taking over an existing, potentially unfinished GPT Astra execution.

You are NOT starting Round 25 from scratch.

Your mission is to recover Astra's exact execution state, preserve its implementation improvements, finish its remaining work and achieve WORKING PHYSICAL SMS ON NUXEL.

The sole successful mission outcome is:

- Genuine supported SMS transport readiness.
- Physical transmission of authorized message ID 4.
- Actual carrier acceptance.
- Independent recipient confirmation.
- Preservation of LTE and management connectivity.

Continue through every demonstrated independently resolvable implementation defect.

Do not voluntarily stop at compilation, successful tests, documentation or an intermediate implementation milestone.

---

## 01. RECOVER ASTRA'S EXACT WORKING STATE

Before modifying anything, inspect:

- Current Git branch.
- Git status.
- Recent Git history.
- Staged changes.
- Unstaged changes.
- Relevant untracked files.
- Existing sms24.md and sms25.md checkpoints.
- Available Astra execution logs.
- Relevant temporary scripts and test artifacts.
- Installed and running device binaries.
- Existing rollback snapshots.

Astra may have left substantial uncommitted implementation work.

Do not reset, discard, overwrite or blindly revert these changes.

Inspect and preserve them.

Relevant recently observed Astra work includes:

- P-Associated-URI handling.
- Service-Route handling.
- SIP Route header formatting.
- IMS transport FSM modifications.
- SMS PDU validation.
- Potential additional changes not visible in the owner's pasted execution output.

The IMS SIP transport FSM test passed during Astra's execution.

Do not assume the complete implementation has passed every test.

Determine precisely what Astra completed, what it deployed and what remains unfinished.

Create ./sms25-continuation.md as the resumable execution checkpoint.

---

## 02. EXPLICIT OWNER AUTHORIZATION

The owner authorizes all necessary legitimate and reversible engineering operations within the existing project environment and approved execution budget:

- Recovering and completing Astra's modifications.
- Native source modifications.
- Native architectural redesign.
- Supported modem protocol integration.
- Offline vendor protocol analysis.
- Supported read-only modem diagnostics.
- Native IMS and SMS implementation.
- Supported USIM authentication.
- Native IPsec integration.
- Supported alternative SMS transport integration.
- Host and on-device testing.
- Build and packaging corrections.
- Reversible deployment.
- Protected runtime configuration changes.
- Targeted USB networking repairs.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Guarded normal reboot.
- One previously authorized physical SMS submission.

Do not repeatedly request approval for these operations.

Preserve legitimate carrier authentication, subscriber privacy, network-imposed retry restrictions and independent recovery access.

Do not bypass carrier authorization, fabricate subscriber identities or certification, extract private subscriber authentication keys or circumvent execution-environment security controls.

Do not perform speculative protected-partition writes.

Do not purchase additional credits or incur additional unapproved expenses.

---

## 03. AUTHORIZED PHYSICAL SMS

The subscriber MSISDN is already configured in:

/var/lib/nuxel/subscriber.conf

Preserve its protected mode-0600 configuration.

The owner explicitly authorizes one physical transmission of existing durable SMS message ID 4 to his girlfriend.

Recipient:

Use the exact previously authorized girlfriend's telephone number stored in message ID 4.

Exact authorized message body:

test SMS van Nuxel voor mijn schatje <3

The ordinary carrier charge for this single submission is approved.

Verify the recipient, exact message body and never-transmitted state.

Do not substitute the subscriber's own telephone number.

Do not create another queued message.

Do not transmit historical messages 1–3.

Do not automatically retry an ambiguous submission.

Keep private subscriber information and message contents out of Git and public reports.

---

## 04. P0 — RECOVER USB MANAGEMENT CONNECTIVITY

The latest Astra output shows:

MacBook:

- en12 UP.
- IPv4 10.100.10.2/24.
- Route to 10.100.10.1 contains REJECT, LLINFO, WASCLONED and IFSCOPE.

Nuxel:

- usb0 UP.
- IPv4 10.100.10.1/24.
- Neighbor entry for 10.100.10.2 exists in STALE state.
- Numerous unrelated FAILED neighbor entries on usb0.
- ZeroTier SSH remains operational.

The attempted device-side ping returned socket Permission denied.

Do not interpret that failed invocation as definitive evidence of network packet loss.

Investigate:

- Actual USB gadget connectivity.
- ARP and neighbor resolution.
- Host and device routing.
- Interface MAC consistency.
- USB management subnet isolation.
- Unexpected default or on-link routes through usb0.
- Interaction with cellular CLAT.
- Interaction with nuxel-usb-tether.service.
- Firewall and policy-routing behavior.
- SSH reachability over the USB management subnet.

Determine whether the unrelated FAILED neighbor entries indicate an incorrect route or interface-selection defect.

Use targeted, reversible corrections.

Do not indiscriminately flush routing tables or firewall configuration.

Preserve the working ZeroTier connection throughout.

Do not restart unrelated services unnecessarily.

Verify bidirectional USB management connectivity and actual SSH access.

---

## 05. P1 — PRESERVE THE LTE BASELINE

The latest physical journal evidence shows:

- PS REGISTERED_HOME.
- raw_state=2.
- RAT LTE.
- reject_cause=0.
- service_domain_readback wire=1.
- packet_service_enabled=true.

Verify the actual current state.

Preserve:

- CP ONLINE.
- CID1 internet connectivity.
- Native IPv6.
- IPv4 through CLAT/NAT64.
- DNS and HTTPS.
- CID2 dedicated IMS bearer.
- P-CSCF discovery and routing.
- ZeroTier.
- USB management.
- Durable SMS queue.
- Protected subscriber configuration.
- Network Retry-After enforcement.

Do not regress working LTE while completing SMS.

---

## 06. P2 — COMPLETE ASTRA'S IMPLEMENTATION

Review all changes made during the interrupted or unfinished Astra execution.

Specifically verify:

- Network-provided public identity handling.
- P-Associated-URI parsing.
- Service-Route parsing.
- Route header serialization.
- Correct distinction between SIP routing headers and actual transport next-hop selection.
- Multiple route handling where required.
- Header bounds and validation.
- Registration state transitions.
- SMS PDU and RP-layer integration.
- Any additional access-network identity changes.

Do not assume that replacing a P-CSCF value with a Service-Route URI automatically produces correct socket routing.

Validate the actual protocol semantics.

Complete demonstrated unfinished implementation work.

Add regression tests.

Preserve correct existing functionality.

---

## 07. P3 — FINISH THE NET_CELL_INFO INVESTIGATION

Round 24 recovered the supported read-only operation:

NET_CELL_INFO main 8, sub 17, type 2.

The modem physically responds.

Determine whether Astra established the actual receive-side layout and LTE ECI field.

Inspect its existing findings before repeating any analysis.

If unresolved, continue targeted offline analysis of the exact matching EFUJ2 vendor implementation and supported native information surfaces.

Validate:

- Serving versus neighboring cell records.
- Actual serving PLMN.
- PCI.
- TAC.
- ECI.
- RAT-specific structure layout.
- Validity and freshness.

Independently validate the previously reported TAC value 0000.

Do not assume it is genuine merely because it was decoded.

Do not fabricate access-network information.

Do not guess modem response offsets or speculative command payloads.

Implement demonstrated corrections and regression coverage.

---

## 08. P4 — RESOLVE THE INITIAL REGISTRATION BLOCKER

Previous physical registration attempts received SIP 480 before any AKA challenge.

Determine whether Astra obtained any genuinely new physical registration evidence.

Do not confuse synthetic SIP test fixtures with actual KPN responses.

Audit demonstrated remaining differences involving:

- Initial registration prerequisites.
- Legitimate subscriber identity configuration.
- Access-network information.
- Supported capabilities.
- SIP transaction construction.
- Security negotiation.
- P-CSCF selection.
- Actual carrier response interpretation.

Do not repeat unchanged registration experiments.

Do not assume SIP 480 conclusively proves missing carrier entitlement, incorrect IMPU or incorrect ECI.

The owner has confirmed that the same SIM works in another phone.

Establish the actual reference transport when legitimate diagnostic evidence is available.

Use meaningful evidence-supported corrections and honor all network-imposed retry requirements.

---

## 09. P5 — COMPLETE THE AUTHENTICATION AND SECURITY LIFECYCLE

If a genuine authentication challenge arrives, continue through the complete supported native lifecycle.

Verify:

- Actual challenge processing.
- USIM authentication dispatch.
- Transaction correlation.
- Authentication result processing.
- Security negotiation.
- IPsec security association lifecycle.
- Protected registration.
- Actual network registration acceptance.
- Registration refresh.
- Failure cleanup.

Correct demonstrated implementation defects.

Do not stop merely because the first authentication challenge arrives.

Use synthetic authentication material exclusively in offline tests.

Never substitute synthetic authentication results for actual network authentication.

Never fabricate registration state.

---

## 10. P6 — TRANSPORT-INDEPENDENT SMS

IMS is a possible means to the objective.

WORKING SMS is the objective.

Evaluate supported alternative SMS transports if meaningful new evidence exists:

- Conventional circuit-switched SMS.
- SMS over NAS/SGs where supported.
- SMS over IMS.

Do not repeat previously exhausted investigations without new evidence.

If a legitimate alternative transport is demonstrated, integrate it into the existing native SMS service.

Preserve Radio1, the durable message store, native codec and Messages application.

Do not circumvent carrier authorization.

---

## 11. P7 — COMPLETE BUILD AND DEPLOYMENT

For every demonstrated independently resolvable defect:

DETECT.

INVESTIGATE.

ESTABLISH ROOT CAUSE.

IMPLEMENT.

TEST.

DEPLOY REVERSIBLY.

VERIFY PHYSICALLY.

CONTINUE.

Run relevant host tests.

Run ASan/UBSan tests.

Verify AArch64 builds.

Verify complete command exit statuses.

Create verified rollback snapshots.

Verify installed and running executable hashes.

Verify production runtime reachability.

Do not discard Astra's useful work.

Do not stop merely because compilation succeeds.

---

## 12. P8 — PHYSICAL SMS FIRST LIGHT

Once a legitimate SMS transport is genuinely ready, verify:

- Correct TPDU encoding.
- Required transport encapsulation.
- Submission transaction correlation.
- Actual carrier acceptance interpretation.
- Durable state transitions.
- Delivery-report handling.
- Timeout behavior.
- Duplicate prevention.

Verify existing authorized message ID 4.

Release it once.

Capture privacy-preserving evidence of actual physical transmission and carrier acceptance.

Do not confuse a generic modem acknowledgment or SIP transaction response with actual SMS acceptance.

Do not automatically retry an ambiguous submission.

After actual carrier acceptance, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm whether his girlfriend received the message.

Do not fabricate delivery.

---

## 13. P9 — INCOMING SMS AND PRODUCTION VERIFICATION

Leave the verified SMS transport operational for a voluntary incoming message.

Verify actual incoming SMS when available.

Confirm:

- Physical reception.
- Protocol acknowledgment.
- Native decoding.
- Durable storage.
- Conversation association.
- Messages application integration.
- Background notification.
- Duplicate prevention.

Verify preservation of:

- LTE internet.
- IPv6 and CLAT/NAT64.
- USB management.
- ZeroTier.
- Wi-Fi hotspot.
- USB tethering.
- IMS bearer isolation.
- Service restart recovery.
- Durable SMS persistence.
- Network backoff persistence.
- Verified rollback.

Perform guarded normal-reboot verification when appropriate.

---

## 14. NO MORE REPEATED INVESTIGATIONS

Do not spend another execution repeating:

- USIM inventory discovery.
- Failed EF_MSISDN retrieval.
- Unchanged IMSI-derived REGISTER attempts.
- Unchanged MSISDN-derived REGISTER attempts.
- Previously rejected SDM commands.
- Broad production call-graph audits already completed.
- Astra's completed offline analysis.

Recover and reuse existing evidence.

Prioritize findings that materially change the next engineering decision.

Continue through every demonstrated independently achievable implementation defect.

If a genuine external dependency remains unavoidable, identify the exact missing observation, why local engineering cannot replace it and the smallest owner action required.

Do not classify an unresolved implementation question as external merely because it is difficult.

An external dependency checkpoint is not mission success.

---

## 15. CHECKPOINT AND COMMITS

Maintain ./sms25-continuation.md.

Create meaningful incremental commits.

Record:

- Astra's recovered implementation state.
- USB connectivity root cause.
- USB repair and physical verification.
- Preserved LTE baseline.
- Completed Astra modifications.
- Additional demonstrated defects.
- Genuine access-network information.
- Actual IMS registration evidence.
- Actual SMS submission evidence.
- Completed tests.
- Installed and running binary hashes.
- Rollback paths.
- Exact continuation procedure.

Preserve unrelated owner changes.

Keep subscriber information and authentication material out of Git.

Do not push or merge without separate authorization.

---

## 16. FINAL ACCEPTANCE MATRIX

Report actual evidence for:

- Astra work recovered:
- Astra implementation completed:
- USB management restored:
- LTE preserved:
- ZeroTier preserved:
- Genuine serving-cell information:
- Network-provided identity handling:
- Service-Route handling:
- Actual authentication challenge:
- Actual USIM authentication:
- Actual security association established:
- Genuine IMS registration:
- Alternative SMS transport availability:
- Selected SMS transport:
- Physical SMS readiness:
- Message ID 4 transmitted:
- Actual carrier acceptance:
- Independent recipient confirmation:
- Incoming SMS:
- Native Messages integration:
- Reboot persistence physically verified:
- Final commits:
- Verified rollback:

Do not declare full Stage 06 complete.

---

## 17. FINAL DIRECTIVE

DO NOT START FROM SCRATCH.

RECOVER ASTRA'S WORK.

FINISH ASTRA'S IMPLEMENTATION.

RESTORE USB MANAGEMENT.

PRESERVE WORKING LTE.

RESOLVE EVERY DEMONSTRATED LOCAL DEFECT.

COMPLETE LEGITIMATE SMS TRANSPORT READINESS.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY.

NO DISCARDED PROGRESS.

NO REPEATED SPECULATION.

NO HALF-INTEGRATED COMPONENTS.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ONE SUCCESS CRITERION:

WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
