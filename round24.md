# NUXEL — SMS OR DIE 4 REAL
## ROUND 24 — ACCESS NETWORK IDENTITY, COMPLETE IMS INTEROPERABILITY AND PHYSICAL SMS
### NO HALF MEASURES — ACTION MODE

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ / beyond2lte

Modem: Shannon S5000AP

Firmware: EFUJ2

Carrier: KPN 204-08

Architecture: Native Linux. ZERO Android runtime dependencies.

Mandatory starting checkpoint: ./sms23.md

Relevant commits:

- d34f25ec — Modem-supplied IMPU decoder.
- 2ca28e84 — SIP instance, security negotiation and IPsec integration.
- 7804933b — Native SMS-over-IMS dispatch integration.
- 52a84d98 — P-CSCF liveness and failover.
- 250355a8 — Cleanup.

Current production binary MD5:

f7a30b9c1f2bcd863fe847d9ac2f9c4c

Verified rollback:

/var/lib/nuxel/rollback-sms23-20261127T135524

---

## 00. SINGLE SUCCESS CRITERION

WORKING PHYSICAL SMS ON NUXEL.

The mission is not another theoretical investigation.

The mission is not another implementation that compiles but has no production caller.

The mission is not another successful bearer activation.

The mission is not another unsupported conclusion concerning carrier provisioning.

The mission requires:

1. Genuine supported SMS transport readiness.
2. Physical transmission of the authorized SMS.
3. Actual carrier acceptance.
4. Independent recipient confirmation.
5. Preservation of working LTE and recovery functionality.

Continue through every demonstrated independently resolvable defect.

Do not voluntarily stop while meaningful independent engineering work remains.

Maintain the approved execution budget and all existing safety and recovery requirements.

---

## 01. ROUND 23 FINDINGS ARE THE NEW BASELINE

Round 23 demonstrated that previous implementations contained substantial production integration gaps:

- ims_security_install() previously had no production caller.
- ims_sip_tr_submit_sms() previously had no production caller.
- SIP instance identification previously used a placeholder.
- Security negotiation was incomplete.
- P-CSCF failover was incomplete.
- Access-network cell identity remains a placeholder.

The latest implementation reportedly resolves the first five issues.

Do not assume that other components are operational merely because they exist in the source tree.

Verify actual production call paths and runtime state transitions.

The remaining SIP 480 root cause is not conclusively established.

The same SIM working in another phone demonstrates that the subscription supports the observed services on that handset. Establish actual IMS registration and SMS transport before drawing stronger conclusions.

---

## 02. EXPLICIT OWNER AUTHORIZATION

The owner authorizes all necessary legitimate and reversible engineering operations within the existing project environment and approved execution budget:

- Native source modifications.
- Native architectural redesign.
- Supported modem-interface integration.
- Read-only modem protocol investigation.
- Supported access-network information retrieval.
- Native subscriber configuration.
- Standards-compliant SIP and IMS implementation.
- Supported USIM authentication.
- Native IPsec and security integration.
- Native dependency integration.
- Supported alternative SMS transport implementation.
- Host and on-device testing.
- Build and packaging corrections.
- Protected runtime configuration changes.
- Reversible deployment.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Guarded normal reboot.
- One authorized physical SMS submission.

Do not repeatedly request approval for these already-authorized operations.

Preserve legitimate carrier authentication, subscriber privacy, network-imposed backoff, independent management access and verified recovery.

Do not bypass carrier restrictions, fabricate device certification, extract private subscriber keys, impersonate another subscriber or circumvent execution-environment security controls.

Do not perform speculative protected-partition writes.

Do not incur additional unapproved expenses.

---

## 03. SUBSCRIBER AND SMS AUTHORIZATION

The actual subscriber MSISDN of the KPN SIM installed inside Nuxel is:

+31648444066

The protected runtime configuration already exists at:

/var/lib/nuxel/subscriber.conf

Preserve mode 0600 and appropriate ownership.

The owner explicitly authorizes one physical transmission of existing durable SMS message ID 4 to his girlfriend.

Authorized recipient:

Use the exact previously authorized girlfriend's telephone number stored in message ID 4.

Exact message body:

test SMS van Nuxel voor mijn schatje <3

The ordinary carrier charge for this single physical submission is approved.

Verify the existing recipient and exact message body.

Verify that message ID 4 has never been transmitted.

Do not substitute the subscriber's own number.

Do not create a duplicate queued message.

Do not transmit historical messages 1–3.

Do not automatically retransmit an ambiguous submission.

Keep private telephone numbers, message contents and authentication material out of Git and public diagnostic reports.

---

## 04. P0 — PRODUCTION BASELINE

Read ./sms23.md and inspect the latest commits.

Verify:

- CP ONLINE.
- LTE REGISTERED_HOME.
- CID1 ordinary internet connectivity.
- CID2 dedicated IMS bearer.
- rmnet1 IPv6 configuration.
- P-CSCF discovery and routing.
- USB management.
- ZeroTier management.
- Protected subscriber configuration.
- Durable SMS queue.
- Retry-After enforcement.
- Installed and running binary identity.
- Verified rollback.

Verify the actual process executable rather than relying exclusively on the installed binary hash.

Keep message ID 4 held.

Verify checkpoint existence and repository cleanliness using independent commands with reliable exit statuses.

Do not allow a failed command chain to produce a misleading CLEAN result.

---

## 05. P1 — RECOVER GENUINE ACCESS-NETWORK INFORMATION

The current implementation reportedly uses a placeholder access-network cell identity of 00000000.

This is a demonstrated implementation gap.

Investigate the supported sources of actual serving-cell information.

Review existing EFUJ2 vendor evidence concerning NET_CELL_INFO, main 8/sub 18.

Determine:

- Whether the operation is supported.
- Whether it is read-only.
- The applicable request and response layouts.
- Whether serving-cell information is available through existing native interfaces.
- Whether the current LTE registration lifecycle already provides sufficient information.
- Which fields are required by the applicable IMS access-network information format.

Use existing vendor artifacts, documented interfaces and legitimate diagnostics.

Do not guess modem command payloads.

Do not fabricate cell identifiers.

Do not substitute home-network identifiers for serving-cell identifiers.

Do not invent missing radio information.

Implement bounded native decoding and validation where supported by evidence.

Add regression tests covering malformed, truncated, unavailable and stale information.

Ensure the IMS implementation uses genuine current serving-network information when required.

If a field is unavailable, determine the standards-compliant behavior rather than transmitting fabricated placeholder values.

Treat the access-network identity correction as a hypothesis to verify, not a guaranteed explanation for SIP 480.

---

## 06. P2 — COMPLETE PRODUCTION CALL-GRAPH AUDIT

Round 23 discovered multiple implemented but disconnected components.

Perform a systematic production reachability audit across the entire SMS and IMS lifecycle.

Inspect:

- Subscriber identity acquisition.
- Subscriber identity selection.
- Serving-network information.
- IMS bearer readiness.
- P-CSCF selection.
- Initial registration.
- Authentication challenge parsing.
- USIM authentication dispatch.
- Authentication result processing.
- Security negotiation.
- IPsec installation.
- Authenticated registration.
- Registration acceptance.
- Registration refresh.
- Registration loss.
- SMS readiness propagation.
- SMS queue dispatch.
- SMS protocol encapsulation.
- Submission-result handling.
- Incoming SMS processing.
- Durable state transitions.
- Native Messages integration.

For each component distinguish:

- Source exists.
- Unit tested.
- Production caller exists.
- Runtime path reachable.
- Physically exercised.
- Physically verified.

Correct every demonstrated disconnected production path.

Do not mark an implementation operational merely because a symbol exists or a unit test passes.

---

## 07. P3 — COMPLETE IMS REGISTRATION INTEROPERABILITY AUDIT

Review the actual serialized REGISTER produced by the current native implementation.

Compare against applicable 3GPP and GSMA requirements.

Use legitimate reference-handset evidence when available.

Review:

- Request URI.
- Public and private identity handling.
- Contact construction.
- Persistent device instance identity.
- Access-network information.
- Required capability representation.
- Security negotiation.
- Transaction correlation.
- Registration prerequisites.
- Registration refresh.
- Network rejection handling.
- Network-imposed backoff.

Determine whether mandatory fields are missing, malformed, stale or inconsistent.

Distinguish mandatory requirements from optional carrier-specific behavior.

Do not invent carrier configuration values.

Do not fabricate device capabilities.

Do not perform speculative subscriber identity enumeration.

Correct demonstrated local defects and add regression coverage.

---

## 08. P4 — SAME-SIM REFERENCE EVIDENCE

The owner has confirmed that the SIM works in another phone.

Use any available legitimate reference evidence to determine:

- Actual IMS registration status.
- Actual VoLTE availability.
- Actual outgoing and incoming SMS functionality.
- Actual SMS transport.
- Relevant supported carrier configuration.
- Relevant registration header differences where legitimately observable.

Do not extract protected authentication material.

Do not bypass handset security.

Do not automatically reflash Nuxel to Android.

If the reference handset is unavailable, complete all independent local work first.

If specific reference evidence becomes indispensable, identify the exact observation needed and why.

Do not consume another large execution budget repeating investigations that cannot produce the missing evidence.

---

## 09. P5 — VERIFY THE OPERATOR IMPU PATH

Review commit d34f25ec and its integration into the latest production build.

Determine whether the modem-supplied IMPU decoder is actually reachable.

Determine whether the IIL registration event provides identity information before or after successful registration.

Resolve any demonstrated circular dependency.

Verify identity validation, ownership, lifetime and privacy handling.

Do not fabricate registration state to obtain an event.

Do not assume the operator-provisioned IMPU is necessarily the sole remaining blocker.

Preserve the legitimate subscriber authentication identity.

---

## 10. P6 — VERIFY THE SECURITY LIFECYCLE END TO END

Review commit 2ca28e84.

Verify that the security negotiation and IPsec implementation are not merely connected but correctly integrated into the complete registration lifecycle.

Review:

- Supported security mechanism selection.
- Security-Server interpretation.
- Security-Verify handling.
- Authentication transaction correlation.
- USIM authentication result handling.
- Security association lifecycle.
- Socket and routing integration.
- Protected registration traffic.
- Failure cleanup.
- Registration refresh.
- Service restart behavior.

Use synthetic authentication material exclusively in offline tests.

Never substitute synthetic results for actual network authentication.

Never log private authentication material.

Do not report successful IMS registration before genuine network acceptance.

Correct demonstrated local defects.

---

## 11. P7 — SMS-OVER-IMS PROTOCOL CORRECTNESS

Review commit 7804933b.

The report describes dispatching a pure TPDU via SIP MESSAGE.

Do not assume this is sufficient.

Verify the complete SMS-over-IMS protocol requirements against applicable TS 24.341 and TS 24.011 specifications.

Audit:

- TPDU encoding.
- Required RP-layer encapsulation.
- SIP MESSAGE content representation.
- Submission transaction correlation.
- RP acknowledgment and error handling.
- SIP response handling.
- Carrier acceptance interpretation.
- Incoming message processing.
- Delivery-report handling.
- Durable state transitions.
- Timeout and duplicate prevention.

Distinguish SIP transaction acceptance from actual SMS submission acceptance.

Correct any demonstrated protocol integration gaps before releasing message ID 4.

Verify the production dispatch path using offline synthetic transactions and regression tests.

---

## 12. P8 — TRANSPORT-INDEPENDENT SMS

IMS is not the mission.

WORKING SMS is the mission.

Reassess legitimate supported transport availability:

- Conventional circuit-switched SMS.
- SMS over NAS/SGs where supported.
- SMS over IMS.

Do not treat CS registration denial alone as definitive proof that all alternative SMS transports are unavailable.

Use actual supported modem and network evidence.

If another legitimate transport is demonstrated, integrate it into the existing native SMS service.

Preserve the Radio1 API, native PDU codec, durable store and Messages application.

Do not use arbitrary unsupported transmission channels or circumvent carrier authorization.

---

## 13. P9 — BUILD, TEST, DEPLOY AND VERIFY

For every demonstrated locally resolvable defect:

DETECT.

INVESTIGATE.

ESTABLISH ROOT CAUSE.

IMPLEMENT.

ADD REGRESSION TESTS.

BUILD.

TEST.

DEPLOY REVERSIBLY.

VERIFY PHYSICALLY.

CONTINUE.

Run relevant host tests.

Run ASan/UBSan tests.

Verify AArch64 builds.

Check complete command exit statuses.

Create verified rollback snapshots.

Verify installed and running executable hashes.

Verify actual production execution paths.

Preserve LTE and independent management access.

Do not stop merely because compilation succeeds.

---

## 14. P10 — GENUINE IMS REGISTRATION

After meaningful evidence-supported corrections and satisfaction of network retry requirements, perform a controlled legitimate registration attempt.

Observe the actual network response.

If a genuine authentication challenge arrives, continue through the supported USIM authentication and security lifecycle.

Correct demonstrated implementation defects.

Verify actual network registration acceptance.

Do not confuse:

- Active IMS bearer with IMS registration.
- SIP 401 with completed authentication.
- Generic modem acknowledgment with registration.
- Local REGISTERED state with network acceptance.
- SIP 480 with definitive proof of absent carrier entitlement.

Do not perform repeated unchanged registration attempts.

---

## 15. P11 — PHYSICAL SMS FIRST LIGHT

Once a legitimate SMS transport is genuinely ready:

Verify existing message ID 4.

Verify the previously authorized recipient.

Verify the exact message body.

Verify that the message has never been transmitted.

Release the existing message once.

Capture privacy-preserving evidence of:

- Actual physical transmission.
- Selected SMS transport.
- Transaction correlation.
- Protocol submission result.
- Actual carrier acceptance.
- Durable message state.
- Delivery report if available.

Do not automatically retry ambiguous submissions.

After genuine carrier acceptance, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm whether his girlfriend received the message.

Do not fabricate delivery.

---

## 16. P12 — INCOMING SMS AND NATIVE APPLICATION INTEGRATION

Leave the verified SMS transport operational for a voluntary incoming message.

Verify actual reception when available.

Confirm:

- Physical reception.
- Protocol acknowledgment.
- Native decoding.
- Durable storage.
- Conversation association.
- Messages application update.
- Background notification.
- Duplicate prevention.

Complete all independently achievable implementation and testing.

Do not fabricate incoming SMS evidence.

---

## 17. P13 — PRODUCTION REGRESSION VERIFICATION

Verify:

- LTE REGISTERED_HOME.
- CID1 internet connectivity.
- Native IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS and HTTPS.
- Wi-Fi hotspot.
- USB tethering.
- Independent USB management.
- ZeroTier.
- IMS bearer routing isolation.
- Controlled service restart recovery.
- Guarded normal reboot recovery.
- SMS queue persistence.
- Registration backoff persistence.
- Verified rollback.

Do not destabilize the working LTE implementation.

---

## 18. NO MORE HALF-INTEGRATED COMPONENTS

A component is not complete because it exists.

A component is not complete because it compiles.

A component is not complete because it passes an isolated unit test.

For every critical component establish its actual production caller, runtime reachability and integration into the complete state machine.

Do not voluntarily stop while demonstrated independent implementation defects remain.

Do not repeat investigations whose results are already established.

If a genuine external dependency becomes unavoidable, establish exactly what evidence is missing and why local engineering cannot replace it.

An external dependency checkpoint is not mission success.

Maintain the approved execution budget.

---

## 19. CHECKPOINT AND COMMIT REQUIREMENTS

Maintain ./sms24.md throughout execution.

Create meaningful incremental commits.

Record:

- Genuine access-network information acquisition state.
- Production call-graph findings.
- Demonstrated implementation defects.
- Implemented corrections.
- Completed tests.
- Physical evidence.
- Actual registration state.
- Actual SMS state.
- Installed and running executable hashes.
- Rollback paths.
- Remaining demonstrated defects.
- Exact continuation procedure.

Keep private subscriber information and authentication material out of Git.

Preserve unrelated owner changes.

Do not push or merge without separate authorization.

---

## 20. FINAL ACCEPTANCE MATRIX

Provide actual evidence for:

- Genuine access-network information:
- Placeholder access-network identity eliminated:
- Production call-graph audit complete:
- Subscriber identity configuration verified:
- IMS security lifecycle integrated:
- Actual authentication challenge:
- Actual subscriber authentication:
- Genuine IMS registration:
- SMS protocol encapsulation verified:
- Alternative SMS transport availability:
- Selected SMS transport:
- Physical SMS readiness:
- Message ID 4 transmitted:
- Carrier acceptance:
- Independent recipient confirmation:
- Incoming SMS:
- Native Messages integration:
- LTE preserved:
- USB preserved:
- ZeroTier preserved:
- Reboot persistence physically verified:
- Final commits:
- Verified rollback:

Do not declare full Stage 06 complete.

---

## 21. FINAL DIRECTIVE

THE MODEM IS ONLINE.

LTE IS ALIVE.

THE IMS BEARER IS ALIVE.

THE SECURITY IMPLEMENTATION IS NOW CONNECTED.

THE SMS DISPATCH IMPLEMENTATION IS NOW CONNECTED.

THE SAME SIM WORKS IN ANOTHER PHONE.

NOW ELIMINATE THE REMAINING PLACEHOLDERS.

AUDIT EVERY CRITICAL PRODUCTION EXECUTION PATH.

FIX EVERY DEMONSTRATED LOCAL DEFECT.

COMPLETE LEGITIMATE NETWORK REGISTRATION OR ANOTHER SUPPORTED SMS TRANSPORT.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY.

PRESERVE LTE AND RECOVERY.

NO DISCONNECTED IMPLEMENTATIONS.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ONE SUCCESS CRITERION:

WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
