# NUXEL — SMS OR DIE 4 REAL
## ROUND 20 — TRANSPORT-INDEPENDENT ACTION MODE
### NATIVE PHYSICAL SMS ENDGAME

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ SM-G975F / beyond2lte

SoC: Exynos 9820

Modem: Shannon S5000AP

Baseband: G975FXXSEFUJ2

Carrier: KPN 204-08

Firmware artifacts: ./packs/

Mandatory starting checkpoint: ./sms19.md

Latest commits:

- 82cdedce
- 4bfe2829
- 2a885671

Known-good deployed binary: sha256 3bee657c…

Rollback:

/var/lib/nuxel/radio-install.round19b-1795777070

Architecture: Native Linux. ZERO Android runtime dependencies.

---

## 00. ONE OBJECTIVE — WORKING PHYSICAL SMS

The sole successful mission outcome is actual working physical SMS on Nuxel.

IMS registration is a possible means to that objective, not the objective itself.

Investigate all legitimate supported native SMS transport options.

Select the transport with the strongest evidence of actual availability and interoperability.

Complete every independently achievable implementation stage.

Do not voluntarily stop after discovering another locally resolvable defect.

Do not report intermediate engineering progress as mission completion.

Do not restart previously completed investigations without concrete contradictory evidence.

Do not assume that additional tokens alone will resolve an external dependency.

---

## 01. EXPLICIT OWNER AUTHORIZATION

The owner authorizes the necessary legitimate, reversible engineering operations within the approved project environment:

- Native source-code modifications.
- Native radio-stack redesign where justified.
- Native SMS transport redesign.
- Supported modem-interface integration.
- Supported read-only subscriber application discovery.
- Legitimate subscriber identity selection.
- Supported USIM and ISIM integration.
- Legitimate authentication integration.
- Standards-compliant IMS implementation.
- Supported conventional SMS transport integration.
- Supported SMS-over-NAS integration where available.
- Native library and dependency integration.
- Build-system and packaging corrections.
- Host and on-device testing.
- Reversible deployment.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Persistent native configuration.
- Guarded normal-reboot verification.
- One authorized physical SMS submission.

Do not repeatedly request approval for these already-authorized operations.

Preserve legitimate subscriber authentication, carrier entitlement, privacy and recovery access.

Do not circumvent execution-environment restrictions or carrier security controls.

Do not fabricate subscriber identities, authentication results, modem registration state or device certification.

Do not extract private SIM authentication keys.

Do not perform speculative protected-partition writes.

Do not incur additional unapproved expenses.

Do not modify boot-critical components outside the established recovery agreement.

---

## 02. AUTHORIZED FINAL PHYSICAL SMS

The owner explicitly authorizes one genuine physical SMS submission to his previously designated girlfriend.

Use existing durable message ID 4.

Exact expected body:

test SMS van Nuxel voor mijn schatje <3

Retrieve the existing authorized recipient from the durable message record.

Verify that message ID 4 remains untransmitted.

Reuse that record.

Do not create a duplicate.

Do not transmit historical messages 1–3.

The owner authorizes the ordinary carrier charge for this single submission.

Release message ID 4 only after genuine transport readiness is established.

Do not automatically retransmit an ambiguous submission.

Any additional physical submission after the authorization is consumed requires separate authorization.

Report actual carrier acceptance separately from delivery.

The owner will independently confirm reception with his girlfriend.

Do not fabricate recipient confirmation.

Keep recipient details and message contents out of Git and diagnostic reports.

---

## 03. P0 — PRESERVE THE VERIFIED BASELINE

Read ./sms19.md and the relevant preceding checkpoints.

Inspect the latest commits.

Verify the installed and running daemon identities.

Verify:

- LTE REGISTERED_HOME.
- CID1 ordinary internet connectivity.
- CID2 IMS bearer.
- rmnet1 IPv6 configuration.
- IMS-specific routes.
- P-CSCF discovery.
- USB management.
- ZeroTier management.
- Rollback availability.
- Durable SMS queue.

Preserve the working bearer independently of registration state.

Preserve the corrected Retry-After lifecycle.

Keep message ID 4 held.

Do not repeat the Round 19 bearer teardown regression.

---

## 04. P1 — CORRECT THE ARCHITECTURAL ASSUMPTIONS

The following previous conclusions have been invalidated or remain unproven:

- ISIM is mandatory for IMS registration.
- The SIM definitely contains ISIM.
- The IMS APN is missing because of carrier provisioning.
- SIP 480 proves carrier entitlement failure.
- An accepted modem registration-state report proves IMS registration.
- The absence of recognizable SIP strings conclusively determines the complete vendor architecture.

Treat these as hypotheses requiring evidence, not established facts.

Audit the current implementation and relevant evidence.

Distinguish actual physical network state from locally reported state.

Remove or correct demonstrated architectural assumptions that prevent legitimate operation.

Never report REGISTERED to the modem unless actual network registration has been established.

---

## 05. P2 — ESTABLISH THE LEGITIMATE TRANSPORT OPTIONS

Produce a concise evidence-based transport availability matrix.

Evaluate:

A. Conventional SMS through the supported Shannon modem interface.

B. SMS over NAS/SGs where supported by the actual modem, network and subscription.

C. Native SMS over IMS.

For each transport, establish:

- Applicable network registration prerequisites.
- Actual subscription and network availability evidence.
- Supported modem interface.
- Existing native implementation completeness.
- Previously observed physical failure.
- Demonstrated local defects.
- Genuine unresolved external prerequisites.

Do not assume LTE packet registration establishes conventional SMS readiness.

Do not assume CS DENIED alone explains every possible SMS transport.

Do not reintroduce unsupported modem wire-domain values.

Do not repeat historical failed experiments without new evidence.

Prioritize the legitimate transport with the strongest evidence and shortest remaining implementation path.

---

## 06. P3 — COMPLETE THE SUBSCRIBER APPLICATION ASSESSMENT

The Round 18 ISIM claim has been invalidated.

The default logical-channel OPEN operation does not establish ISIM presence.

Determine the actual supported application inventory using legitimate read-only interfaces and applicable standards.

Review existing application-discovery parsing.

Distinguish USIM from ISIM accurately.

Determine whether the existing UICC TRANSMIT failure represents:

- Unsupported operation.
- Incorrect application selection.
- Incorrect serialization.
- Incorrect response interpretation.
- A genuinely unavailable interface.

Correct demonstrated local implementation defects.

Do not perform arbitrary SIM operations or subscriber-file modifications.

Do not retrieve private authentication keys.

If valid provisioned ISIM identities are available, integrate them through the supported interface.

If ISIM is absent, use the standards-supported USIM identity and authentication path where applicable.

Do not treat ISIM absence as an automatic mission blocker.

Keep subscriber information protected.

---

## 07. P4 — REVIEW THE REGISTER GATE AND AUTHENTICATION LIFECYCLE

Commit 82cdedce introduced a gate preventing repeated unsuccessful initial REGISTER transmissions.

Preserve its legitimate protection against uncontrolled retries and unverified identities.

Review whether the gate correctly distinguishes:

- Legitimate initial registration.
- Network authentication challenge.
- Authenticated registration continuation.
- Network-imposed Retry-After.
- Terminal registration failure.
- Unsupported or unverified subscriber identity.
- Repeated unchanged unsuccessful requests.

An initial registration request preceding an authentication challenge is part of the normal supported authentication lifecycle.

The absence of a prior authentication challenge must not be mistaken for proof that all initial registration is illegitimate.

Establish the actual supported prerequisites for the initial registration attempt.

Review the documented NUXEL_IMS_ALLOW_UNAUTH_REGISTER configuration and its intended semantics.

Do not blindly override the gate.

Do not disable network backoff or circumvent carrier restrictions.

Correct demonstrated state-machine defects while preserving legitimate security requirements.

Keep CID2/rmnet1 independent of registration transmission state.

Add regression tests for the complete supported lifecycle.

---

## 08. P5 — ESTABLISH THE ACTUAL IMS INTEROPERABILITY BLOCKER

If IMS remains the selected transport, review the existing SIP registration implementation against applicable standards and verified vendor evidence.

Determine whether the observed SIP 480 is attributable to:

- Legitimate identity-selection defects.
- Incorrect carrier configuration.
- Incorrect registration construction.
- Unsupported feature negotiation.
- Incomplete security integration.
- Incorrect authentication lifecycle.
- Incorrect response interpretation.
- Genuine carrier provisioning or interoperability requirements.

Use applicable 3GPP requirements and matching vendor artifacts.

Do not conclude that the carrier requires Android merely because the current native client receives SIP 480.

Do not repeat broad SIP field-matrix experiments.

Do not enumerate or invent subscriber identities.

Do not fabricate device capabilities or certification.

Respect Retry-After and all network restrictions.

Correct demonstrated local defects.

If independent carrier or stock-handset evidence is required, state the precise question that must be answered.

Complete all other independently achievable work.

---

## 09. P6 — COMPLETE THE SELECTED NATIVE TRANSPORT

For the selected legitimate SMS transport, implement every remaining demonstrated local requirement.

Reuse existing native components wherever appropriate:

- Radio1 API.
- SMS PDU codec.
- Native modem transport.
- Native SIP backend.
- Native SMS-over-IMS codec.
- Durable SQLite store.
- Native Messages application.

If IMS is selected, complete legitimate registration, authentication and required security integration before SMS transmission.

If another supported transport is selected, verify its actual registration and SMS-specific prerequisites.

Do not require IMS registration for a transport that legitimately does not depend on IMS.

Implement correct transport selection and fallback behavior.

Do not silently switch transports after an ambiguous submission.

Build, test, deploy reversibly and physically verify.

---

## 10. P7 — COMPLETE THE PHYSICAL SMS TRANSACTION LIFECYCLE

Verify the selected transport's actual SMS-specific readiness.

Correct demonstrated defects in:

- SMS encoding and encapsulation.
- Transport selection.
- Transaction association.
- Submission-result parsing.
- Protocol acknowledgment.
- Delivery-report handling.
- Timeout handling.
- Durable state transitions.
- Duplicate prevention.
- Incoming SMS handling.
- Network-loss recovery.

Do not confuse generic modem acknowledgments or SIP responses with actual SMS submission acceptance.

Do not report queued or sending as successful submission.

Do not release message ID 4 prematurely.

---

## 11. P8 — SEND THE AUTHORIZED SMS

After genuine transport readiness is established:

Verify that existing message ID 4 has never been transmitted.

Release it once through the verified legitimate transport.

Expected message:

test SMS van Nuxel voor mijn schatje <3

Use the existing authorized recipient.

Capture privacy-preserving evidence of:

- Native message ID.
- Selected transport.
- Physical transmission.
- Actual transaction association.
- Actual submission result.
- Carrier acceptance.
- Durable message state.
- Delivery report, if available.

Do not automatically retransmit an ambiguous submission.

If a demonstrated local defect prevents submission, correct it and continue all independently achievable work.

Once actual carrier acceptance has been established, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm delivery.

---

## 12. P9 — INCOMING SMS AND APPLICATION INTEGRATION

Leave the legitimate native SMS transport operational for a voluntary incoming reply.

Verify actual incoming SMS when available.

Confirm:

- Physical network reception.
- Protocol acknowledgment.
- Native decoding.
- Durable storage.
- Conversation association.
- Native Messages application update.
- Background notification.
- Duplicate prevention.
- Persistence.

If no incoming reply is available, complete all independently achievable implementation and tests.

Do not fabricate physical incoming evidence.

---

## 13. P10 — PERSISTENCE AND REGRESSION ACCEPTANCE

Preserve and verify:

- Ordinary LTE registration.
- CID1 internet connectivity.
- Native IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS.
- Cellular HTTPS.
- NetworkManager integration.
- Wi-Fi hotspot.
- USB tethering.
- Independent USB management.
- ZeroTier.
- CID2/rmnet1 where applicable.
- IMS-specific routing isolation.

Verify controlled service restart recovery.

Verify guarded normal-reboot persistence when appropriate.

Verify SMS state persistence.

Verify that registration backoff cannot be accidentally reset by socket reopening or service lifecycle changes.

Maintain rollback capability.

Restore the known-good baseline if an experiment destabilizes the device.

---

## 14. ACTION MODE — CONTINUOUS LOCAL IMPLEMENTATION

Whenever a demonstrated locally resolvable defect is encountered:

DETECT.

INVESTIGATE.

IDENTIFY THE ROOT CAUSE.

IMPLEMENT THE CORRECTION.

TEST.

DEPLOY REVERSIBLY.

VERIFY PHYSICALLY.

CONTINUE.

Do not voluntarily terminate merely because another component requires implementation.

Do not return documentation-only reports while independently achievable implementation remains.

Do not repeat unchanged failed operations.

Do not spend an entire execution re-establishing previously verified findings.

Prioritize measurable physical progress.

Use the approved execution budget efficiently.

Maintain incremental commits and resumable checkpoints.

Run complete build and test commands with reliable exit-status handling.

Do not allow grep, head or tail pipelines to mask failed builds or aborted tests.

---

## 15. GENUINE EXTERNAL DEPENDENCIES

Previous rounds repeatedly misclassified native implementation defects as external provisioning restrictions.

Do not repeat that pattern.

However, do not pretend that every external dependency can be resolved through additional source-code changes.

Before declaring a carrier restriction:

- Establish the actual physical failure.
- Verify the legitimate subscription identity path.
- Correct demonstrated local implementation defects.
- Verify the deployed implementation.
- Evaluate supported alternative SMS transports.
- Identify the precise unresolved external prerequisite.
- Obtain independent carrier or stock-handset evidence where available.

If the same SIM requires independent stock-handset testing, specify exactly what must be observed.

Do not automatically reflash the working Nuxel handset to Android.

Do not fabricate carrier confirmation.

Do not bypass genuine carrier requirements.

If further progress depends on external evidence, checkpoint the exact requirement and complete all remaining independent local work.

A checkpoint is not mission success.

---

## 16. CHECKPOINT AND COMMIT REQUIREMENTS

Create meaningful incremental commits.

Preserve unrelated owner changes.

Keep private subscriber information, authentication material and firmware artifacts out of Git.

Do not merge or push unless separately authorized.

Maintain ./sms20.md throughout execution.

Record:

- Current implementation state.
- Actual physical evidence.
- Deployed binary identity.
- Verified rollback.
- Completed tests.
- Remaining demonstrated local defects.
- Exact next operation.
- Any genuinely required external evidence.

If a hard execution limit, approved spending limit or external dependency interrupts the mission, leave a fully resumable checkpoint.

---

## 17. FINAL ACCEPTANCE MATRIX

Provide actual evidence for:

- Conventional SMS availability:
- SMS-over-NAS/SGs availability:
- SMS-over-IMS availability:
- Selected native transport:
- Verified subscriber application inventory:
- Legitimate identity selection:
- Actual authentication result, where applicable:
- Actual network registration:
- Native SMS transport readiness:
- Message ID 4 physically transmitted:
- Actual submission result:
- Carrier acceptance:
- Recipient confirmation:
- Incoming SMS:
- Native Messages integration:
- LTE preserved:
- USB management preserved:
- ZeroTier preserved:
- Reboot persistence physically verified:
- Final commits:
- Remaining conclusively demonstrated external requirements:

Do not declare full Stage 06 complete.

Do not declare SMS AND ALIVE before actual physical acceptance.

---

## 18. FINAL DIRECTIVE — SMS OR DIE 4 REAL

THE MODEM IS ONLINE.

LTE IS WORKING.

THE DEDICATED IMS BEARER IS WORKING.

THE NATIVE SMS INFRASTRUCTURE EXISTS.

THE WORKING BASELINE IS STABLE.

DO NOT CONFUSE ONE TRANSPORT WITH THE ENTIRE MISSION.

ESTABLISH THE LEGITIMATE AVAILABLE SMS TRANSPORT.

FIX EVERY DEMONSTRATED LOCAL DEFECT.

COMPLETE THE NATIVE IMPLEMENTATION.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY WITH HIS GIRLFRIEND.

PRESERVE LTE AND RECOVERY.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

NO UNCONTROLLED RETRIES.

ONE SUCCESS CRITERION: WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
