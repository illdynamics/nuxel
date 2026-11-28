# NUXEL — SMS OR DIE 4 REAL
## ROUND 21 — USIM-ONLY NATIVE SMS ENDGAME
### EVIDENCE-DRIVEN ACTION MODE

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ / beyond2lte

Modem: Shannon S5000AP

Firmware: EFUJ2

Carrier: KPN 204-08

Architecture: Native Linux, ZERO Android runtime dependencies.

Mandatory starting checkpoint: ./sms20.md

Latest implementation commit: e1dccb66

Deployed binary: 432187dc5b56fd91…

Known-good previous binary: 3bee657c…

---

## 00. SINGLE MISSION SUCCESS CRITERION

The sole successful mission outcome is WORKING PHYSICAL SMS on Nuxel.

Do not confuse implementation completeness, modem acknowledgments, bearer availability or locally reported registration with actual SMS functionality.

Complete every independently achievable engineering operation required to reach this objective.

Do not voluntarily terminate upon encountering a locally resolvable defect.

Do not repeat previously completed investigations without new evidence.

Do not declare an external blocker merely because the current implementation fails.

Do not fabricate success or bypass legitimate network requirements.

---

## 01. EXPLICIT OWNER AUTHORIZATION

The owner explicitly authorizes all necessary legitimate and reversible engineering work within the existing project environment and approved budget, including:

- Native source-code modifications and architectural redesign.
- Native library integration.
- Supported modem-interface implementation.
- Standards-compliant USIM authentication integration.
- Legitimate subscriber identity selection.
- Native SIP and IMS implementation.
- Supported alternative SMS transports.
- Carrier configuration corrections supported by evidence.
- Host and physical-device testing.
- Reversible builds and deployment.
- Controlled service and modem restarts.
- Temporary cellular interruption with verified recovery.
- Guarded normal-reboot verification.
- One authorized physical SMS submission.

Do not repeatedly request authorization for these operations.

Preserve LTE, USB management, ZeroTier, rollback capability, subscriber privacy and legitimate carrier security.

Do not bypass carrier entitlement, authentication or execution-environment restrictions.

Do not fabricate registration state, subscriber identities, authentication results or device certification.

Do not extract private subscriber authentication keys.

Do not perform speculative protected-partition writes.

Do not incur additional unapproved expenses.

---

## 02. AUTHORIZED PHYSICAL SMS ACCEPTANCE TEST

Existing durable message ID: 4.

Exact message body:

test SMS van Nuxel voor mijn schatje <3

Use the existing authorized recipient stored in the durable message record.

The owner explicitly authorizes one physical submission and its ordinary carrier charge.

Verify that message ID 4 has never been transmitted.

Reuse the existing message.

Do not create duplicate records.

Do not transmit historical messages 1–3.

Release ID 4 only after genuine transport readiness has been established.

Do not automatically retransmit an ambiguous submission.

The owner will independently confirm reception with his girlfriend.

Do not fabricate delivery confirmation.

---

## 03. P0 — PRESERVE THE VERIFIED BASELINE

Read sms20.md and relevant earlier checkpoints.

Verify the latest implementation and deployed binary.

Preserve:

- LTE REGISTERED_HOME.
- CID1 ordinary internet connectivity.
- CID2 dedicated IMS bearer.
- rmnet1 IPv6 configuration.
- P-CSCF discovery and routing.
- USB management.
- ZeroTier.
- Durable SMS queue.
- Retry-After protection.
- Known-good rollback.

Keep IMS bearer availability independent of SIP registration state.

Keep message ID 4 held until readiness.

---

## 04. P1 — CORRECT THE USIM-ONLY ARCHITECTURE

Round 20 established:

- One reported subscriber application.
- USIM present.
- ISIM absent.
- SIM_ICC_TYPE 02.
- SEC_IMS_SUPP_AUTH_TYPES rejected with 0x0180.
- No demonstrated network AKA challenge.

The absence of ISIM is not automatically a prohibition on IMS registration.

Review the applicable USIM-based IMS architecture using:

- 3GPP TS 23.003.
- 3GPP TS 24.229.
- 3GPP TS 31.102.
- 3GPP TS 33.203.
- Relevant carrier interoperability requirements.

Determine which requirements apply to this subscription and modem generation.

Audit the current native implementation against those requirements.

Correct every demonstrated local implementation defect.

Do not require an ISIM application that the actual subscriber card does not contain.

Do not continue speculative ISIM application selection.

---

## 05. P2 — INDEPENDENT SUBSCRIBER AND CARRIER EVIDENCE

The current evidence does not conclusively establish that the subscription lacks IMS or SMS provisioning.

Obtain or consume independent evidence where available:

- Same-SIM stock-handset IMS registration.
- Same-SIM ordinary SMS functionality.
- Actual SMS transport used by the reference handset, if observable.
- Carrier confirmation of VoLTE and SMS-over-IMS provisioning.
- Carrier-supported interoperability requirements.

A successful ordinary SMS on a reference handset does not automatically establish that SMS-over-IMS was used.

Distinguish IMS SMS from alternative transports.

If the owner has not supplied reference results, complete all independently achievable offline implementation and verification work.

Do not fabricate reference evidence.

Do not automatically reflash the Nuxel device to Android.

Do not assume the carrier supports an unapproved configuration.

---

## 06. P3 — NATIVE SUBSCRIBER IDENTITY AUDIT

Audit the existing legitimate subscriber identity implementation.

Determine whether the current USIM-based identity selection conforms to applicable standards and the verified carrier configuration.

Review identity construction, domain selection, subscriber application selection and privacy handling.

Correct demonstrated implementation defects.

Do not enumerate subscriber identities.

Do not guess private subscriber identifiers.

Do not impersonate another subscriber or device.

Do not treat SIP 480 alone as conclusive proof of provisioning failure.

Use independent evidence to distinguish identity-construction errors from genuine carrier restrictions.

---

## 07. P4 — AUTHENTICATION AND REGISTRATION LIFECYCLE

Review the complete native registration state machine.

Distinguish:

- Initial legitimate registration.
- Network authentication challenge.
- Supported subscriber authentication.
- Required security negotiation.
- Authenticated registration.
- Registration refresh.
- Network rejection.
- Retry-After.
- Terminal failure.

The CP is not expected to originate network AKA independently if the AP owns SIP registration.

Do not mistake the absence of unsolicited CP AKA events for proof of unavailable IMS.

Review the existing registration gate.

Preserve its protection against uncontrolled retries and unsupported identities.

Ensure that legitimate standards-compliant registration is possible when the necessary prerequisites have been established.

Do not blindly disable the gate.

Do not bypass network backoff.

Do not send synthetic authentication results or false registration-state reports.

Add regression tests for demonstrated state-machine defects.

---

## 08. P5 — COMPLETE ALL LOCALLY ACHIEVABLE AUTHENTICATION WORK

Audit the existing native authentication integration against supported modem interfaces and applicable standards.

Verify request correlation, response interpretation, failure handling, state transitions and privacy protections.

Use synthetic test vectors for offline validation.

Keep authentication material protected.

Do not treat synthetic authentication success as actual network authentication.

Where genuine network authentication is required, proceed only through the supported subscriber and carrier authentication lifecycle.

Correct, test and deploy every demonstrated local defect.

---

## 09. P6 — TRANSPORT-INDEPENDENT SMS COMPLETION

Reassess the supported SMS transport options:

- Conventional SMS.
- SMS over NAS/SGs.
- SMS over IMS.

Distinguish transport availability from current implementation failure.

Do not conclude that every possible alternative is unavailable solely from one registration status.

Use verified modem, network and carrier evidence.

Select the legitimate supported transport with the strongest evidence.

Complete its native implementation.

Preserve the existing Radio1 API, durable SMS store and Messages application.

Do not switch transports after an ambiguous physical submission.

---

## 10. P7 — COMPLETE THE SMS TRANSACTION LIFECYCLE

Verify and correct all demonstrated defects in:

- Native SMS transport readiness.
- PDU encoding.
- Protocol encapsulation.
- Submission correlation.
- Carrier result interpretation.
- Delivery-report handling.
- Durable state transitions.
- Timeout handling.
- Duplicate prevention.
- Incoming SMS reception.
- Application integration.

Run complete host and sanitizer suites.

Run native-device tests.

Deploy reversibly.

Verify the actual installed and running binary.

Do not report a generic modem ACK as carrier SMS acceptance.

---

## 11. P8 — PHYSICAL SMS ACCEPTANCE

After actual legitimate transport readiness is established:

Release existing authorized message ID 4 once.

Expected message:

test SMS van Nuxel voor mijn schatje <3

Use the existing authorized recipient.

Capture privacy-preserving evidence of physical transmission, transaction correlation, actual submission result and durable state.

Do not duplicate the message.

Do not automatically retransmit an ambiguous result.

Once genuine carrier acceptance has been established, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

Wait for independent owner confirmation before claiming delivery.

---

## 12. P9 — INCOMING SMS

Leave the verified native SMS transport operational for a voluntary incoming reply.

Verify actual reception when available.

Confirm native decoding, acknowledgment, durable storage, Messages application integration, notification and duplicate prevention.

Complete all independently achievable implementation and testing if a physical reply is not yet available.

Do not fabricate incoming SMS evidence.

---

## 13. P10 — PRODUCTION REGRESSION ACCEPTANCE

Verify that the completed implementation preserves:

- LTE internet.
- CID1 IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS and HTTPS.
- Wi-Fi hotspot.
- USB tethering.
- USB management.
- ZeroTier.
- IMS bearer and routing isolation where applicable.

Verify controlled service restart recovery.

Verify guarded normal-reboot persistence.

Verify SMS queue persistence and registration backoff behavior.

Maintain a verified rollback path.

---

## 14. CONTINUOUS ACTION MODE

Whenever a demonstrated locally resolvable defect is encountered:

DETECT.

INVESTIGATE.

IDENTIFY ROOT CAUSE.

IMPLEMENT.

TEST.

DEPLOY REVERSIBLY.

VERIFY.

CONTINUE.

Do not voluntarily stop at a locally resolvable defect.

Do not spend another entire round repeating established findings.

Do not run unchanged unsuccessful network experiments.

Do not substitute documentation for achievable implementation.

Maintain reliable command exit-status handling.

Do not allow shell pipelines to conceal failed tests.

Use the approved execution budget efficiently.

Prioritize evidence that changes the technical outcome.

---

## 15. GENUINE EXTERNAL DEPENDENCY HANDLING

If progress requires carrier confirmation or same-SIM reference testing, establish exactly why.

Complete every independent local task first.

Document:

- The demonstrated physical failure.
- The verified local implementation state.
- The precise missing external evidence.
- Why that evidence changes the next engineering decision.
- The exact continuation procedure once it is supplied.

Do not repeatedly label unproven assumptions as external restrictions.

Do not attempt to circumvent genuine restrictions.

An external dependency checkpoint is not mission success.

---

## 16. COMMIT AND CHECKPOINT REQUIREMENTS

Create incremental meaningful commits.

Preserve unrelated owner changes.

Maintain ./sms21.md throughout execution.

Record implementation changes, test results, physical evidence, deployed binary hashes, rollback paths and the exact next operation.

Keep private subscriber information and authentication material out of Git.

Do not push or merge without separate authorization.

If a hard execution limit, approved budget limit or genuine external dependency interrupts execution, leave a fully resumable checkpoint.

---

## 17. FINAL ACCEPTANCE MATRIX

Provide actual evidence for:

- Verified USIM-only subscriber inventory.
- Supported subscriber identity path.
- Legitimate authentication result where applicable.
- Actual network registration.
- Selected SMS transport.
- Physical transport readiness.
- Message ID 4 physical transmission.
- Actual carrier acceptance.
- Recipient confirmation.
- Incoming SMS.
- Native Messages integration.
- LTE preservation.
- USB and ZeroTier preservation.
- Reboot persistence.
- Final commits.
- Verified rollback.

Do not declare Stage 06 complete while physical SMS remains unverified.

---

## 18. FINAL DIRECTIVE

LTE IS ALIVE.

THE IMS BEARER IS ALIVE.

THE NATIVE SMS INFRASTRUCTURE EXISTS.

THE USIM INVENTORY IS VERIFIED.

STOP REPEATING INVALIDATED ISIM ASSUMPTIONS.

RESOLVE THE ACTUAL NATIVE INTEROPERABILITY DEFECTS.

ESTABLISH THE LEGITIMATE AVAILABLE SMS TRANSPORT.

COMPLETE THE IMPLEMENTATION.

TRANSMIT THE AUTHORIZED MESSAGE ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

PRESERVE THE WORKING BASELINE.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ONE SUCCESS CRITERION: WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
