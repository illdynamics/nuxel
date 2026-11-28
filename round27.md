# NUXEL — SMS OR DIE 4 REAL
## ROUND 26 — ARCHITECTURAL CHALLENGE AND PHYSICAL SMS ENDGAME
### DEEPSEEK V4 PRO THINKING — ACTION MODE

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ / beyond2lte

Modem: Shannon S5000AP

Firmware: EFUJ2

Carrier: KPN 204-08

Architecture: Native Linux. ZERO Android runtime dependencies.

Latest checkpoint: ./sms25-continuation.md

Latest commit: e7ed3ec5

Production binary MD5:

51016b78e1ece659fc980ad639968963

---

## 00. SINGLE MISSION SUCCESS CRITERION

WORKING PHYSICAL SMS ON NUXEL.

The sole successful mission outcome consists of:

- Genuine supported SMS transport readiness.
- Physical transmission of existing authorized message ID 4.
- Actual carrier acceptance.
- Independent recipient confirmation.
- Preservation of working LTE and management connectivity.

Do not confuse implementation maturity with actual functionality.

Do not voluntarily stop while meaningful independently achievable engineering work remains.

Do not repeat previous investigations without new evidence.

Work within the existing approved execution budget.

---

## 01. CHALLENGE THE ARCHITECTURE

Previous rounds repeatedly concluded that unresolved issues were external dependencies.

Subsequent investigations discovered genuine local implementation defects.

The most recent example was LTE ECI acquisition, which was previously classified as requiring external reference evidence but was subsequently resolved by Astra.

Therefore, independently challenge the architectural assumptions underlying the current implementation.

Do not assume:

- The current AP-side IMS architecture is necessarily correct.
- The current SIP transport implementation is necessarily complete.
- The current subscriber identity derivation is necessarily correct.
- The current modem initialization lifecycle is necessarily sufficient.
- The current interpretation of SIP 480 is necessarily correct.
- The current SMS transport availability conclusions are necessarily correct.

Establish each conclusion using evidence.

Do not invent another speculative explanation.

---

## 02. EXPLICIT OWNER AUTHORIZATION

The owner authorizes all necessary legitimate and reversible engineering operations within the existing project environment and approved execution budget:

- Native source modifications.
- Native architectural redesign.
- Replacement of incomplete native protocol implementations.
- Integration of suitable established native Linux libraries.
- Offline vendor protocol analysis.
- Supported read-only modem diagnostics.
- Supported modem initialization and configuration.
- Standards-compliant SIP and IMS implementation.
- Supported subscriber authentication.
- Native IPsec integration.
- Supported alternative SMS transport implementation.
- Host and on-device testing.
- Build and packaging corrections.
- Protected runtime configuration changes.
- Reversible deployment.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Guarded normal reboot.
- One previously authorized physical SMS submission.

Do not repeatedly request approval for these already-authorized operations.

Preserve legitimate carrier authentication, subscriber privacy, network-imposed backoff, independent recovery access and rollback capability.

Do not bypass carrier authorization, fabricate subscriber identities, misrepresent device certification, extract private subscriber authentication keys or circumvent execution-environment security controls.

Do not perform speculative protected-partition writes.

Do not incur additional unapproved expenses.

---

## 03. AUTHORIZED PHYSICAL SMS

The actual subscriber MSISDN is already stored in:

/var/lib/nuxel/subscriber.conf

Preserve its mode-0600 configuration.

The owner explicitly authorizes one physical transmission of existing durable message ID 4 to his girlfriend.

Recipient:

Use the exact previously authorized girlfriend's telephone number stored in message ID 4.

Exact message body:

test SMS van Nuxel voor mijn schatje <3

The ordinary carrier charge for this single submission is approved.

Verify the existing recipient, exact message body and never-transmitted state.

Do not substitute the subscriber's own number.

Do not create another queued message.

Do not transmit historical messages 1–3.

Do not automatically retry an ambiguous submission.

Keep private subscriber information and message contents out of Git and public reports.

---

## 04. P0 — RECOVER AND PRESERVE THE BASELINE

Read the latest checkpoints and commits.

Verify:

- CP ONLINE.
- LTE REGISTERED_HOME.
- CID1 internet connectivity.
- CID2 dedicated IMS bearer.
- P-CSCF discovery and routing.
- USB management.
- ZeroTier.
- Protected subscriber configuration.
- Durable SMS queue.
- Network Retry-After enforcement.
- Installed and running binary identity.
- Verified rollback.

Latest reported genuine serving-cell information:

- ECI: 076f31f.
- TAC: 846e.
- PLMN: 20408.

Validate freshness before using these values.

Do not hardcode historical serving-cell information.

Preserve all previous Astra and DeepSeek implementation improvements.

Do not repeat broad baseline investigations unnecessarily.

---

## 05. P1 — INDEPENDENT IMS ARCHITECTURE REVIEW

Determine whether the existing native implementation follows the correct architecture for this exact modem and firmware combination.

Review available evidence concerning:

- AP-owned IMS registration.
- Modem-owned IMS registration.
- Shared AP/modem IMS responsibilities.
- Modem initialization prerequisites.
- Supported subscriber identity acquisition.
- Supported carrier configuration.
- IMS bearer ownership.
- IMS signaling ownership.
- Authentication ownership.
- Security association ownership.
- SMS transport ownership.

Distinguish actual vendor behavior from assumptions based on symbol names.

Determine whether an essential prerequisite has been omitted from the current native architecture.

Do not report a modem acknowledgment as successful network registration.

Do not fabricate modem registration state.

If a demonstrated architectural defect exists, correct it rather than adding another workaround.

---

## 06. P2 — ESTABLISHED NATIVE IMPLEMENTATION COMPARISON

Investigate established native Linux and standards-compliant IMS/SIP implementations.

Evaluate whether suitable components can improve or replace parts of the current custom implementation.

Potential comparison targets include:

- PJSIP.
- Sofia-SIP.
- Existing Linux telephony frameworks.
- Existing native IMS implementations.
- Applicable 3GPP reference behavior.
- Applicable GSMA interoperability profiles.

These are comparison candidates, not predetermined dependencies.

Evaluate actual support for:

- IMS registration.
- USIM-based authentication.
- IMS security negotiation.
- IPsec integration.
- Network-provided identity handling.
- Service routing.
- SMS-over-IMS.

Do not assume a general-purpose SIP library provides complete IMS functionality.

Preserve ZERO Android runtime dependencies.

Prefer established, maintainable components when they demonstrably improve correctness.

Do not undertake a wholesale rewrite without evidence that it addresses an actual defect.

---

## 07. P3 — COMPLETE INITIAL REGISTRATION COMPARISON

The current physical failure is:

SIP 480 + Retry-After before any AKA challenge.

Review the exact current registration implementation and compare its behavior against applicable requirements:

- 3GPP TS 23.003.
- 3GPP TS 24.229.
- 3GPP TS 31.102.
- 3GPP TS 33.203.
- Applicable GSMA IMS profiles.

Distinguish mandatory requirements, optional behavior and operator-specific requirements.

Review:

- Legitimate subscriber identities.
- Home-network domain.
- Initial registration prerequisites.
- Registration transaction construction.
- Access-network information.
- Contact and device instance lifecycle.
- Supported service capabilities.
- Security negotiation.
- Transport selection.
- P-CSCF selection.
- Response interpretation.

Investigate whether a previously overlooked prerequisite explains the pre-authentication rejection.

Do not repeat unchanged REGISTER attempts.

Do not fabricate identity or capability information.

Only perform new controlled registration attempts after meaningful evidence-supported corrections and satisfaction of network-imposed backoff.

---

## 08. P4 — USIM-ONLY SUBSCRIBER IDENTITY

The physical SIM reportedly contains a USIM application but no ISIM application.

This does not inherently make IMS impossible.

Investigate legitimate standards-compliant identity derivation and supported operator configuration.

Review:

- Public subscriber identity.
- Private subscriber identity.
- Home-network domain.
- Supported USIM authentication.
- Modem-provided identity events.
- Existing protected subscriber configuration.
- Network-provided associated identities.

Determine whether the current identity construction is correct for the available evidence.

Do not assume that the absence of ISIM proves missing IMS entitlement.

Do not enumerate guessed subscriber identities.

Do not impersonate another subscriber.

If operator-specific configuration is indispensable, identify precisely which supported configuration value is missing.

---

## 09. P5 — REFERENCE HANDSET DIFFERENTIAL

The owner has confirmed that the same physical SIM works in another phone.

Obtain or prepare the smallest useful reference-handset diagnostic procedure.

Prioritize:

1. Whether IMS is actually registered.
2. Whether VoLTE is available.
3. Whether ordinary outgoing SMS works.
4. Whether ordinary incoming SMS works.
5. Which SMS transport is actually used, if observable.
6. Supported carrier configuration.
7. Public subscriber identity information, if legitimately exposed.
8. Registration header diagnostics, if legitimately available.

Do not require protected authentication keys or credentials.

Do not bypass reference-handset security.

Do not automatically reflash Nuxel to Android.

If reference evidence is available, use it to establish concrete differences between the working implementation and Nuxel.

If it is unavailable, complete independent local engineering first.

Prepare a concise, device-specific owner procedure if a reference observation becomes indispensable.

Do not spend the execution budget repeatedly attempting to infer information that is not present.

---

## 10. P6 — TRANSPORT-INDEPENDENT SMS ENDGAME

IMS is not the sole objective.

WORKING SMS is the objective.

Reassess legitimate supported transport availability using actual evidence:

- Conventional circuit-switched SMS.
- SMS over NAS/SGs where supported.
- SMS over IMS.

Do not treat CS registration denial as definitive proof that every alternative transport is unavailable.

Do not treat absence of ISIM as proof that IMS is unavailable.

Do not repeat previously exhausted experiments without meaningful new evidence.

If another legitimate supported SMS transport is demonstrated, integrate it into the existing native SMS service.

Preserve:

- Radio1 API.
- Native SMS codec.
- Durable SMS store.
- Messages application.
- Transaction correlation.
- Duplicate prevention.

Do not circumvent carrier authorization.

---

## 11. P7 — COMPLETE AUTHENTICATION AND SECURITY

If an actual network authentication challenge arrives, continue through the entire supported lifecycle.

Verify:

- Challenge processing.
- USIM authentication dispatch.
- Transaction correlation.
- Authentication result processing.
- Security negotiation.
- IPsec security association establishment.
- Protected registration.
- Actual registration acceptance.
- Registration refresh.
- Failure cleanup.

Correct every demonstrated local implementation defect.

Do not stop at the first 401 response.

Use synthetic authentication material only for offline tests.

Never substitute synthetic results for actual network authentication.

Never fabricate successful registration.

---

## 12. P8 — COMPLETE SMS TRANSACTION LIFECYCLE

Verify the actual selected transport's complete submission lifecycle.

For SMS-over-IMS, review applicable TS 24.341 and TS 24.011 requirements.

Verify:

- TPDU encoding.
- RP-layer encapsulation.
- SIP MESSAGE construction.
- Network-provided identity handling.
- Service routing.
- Transaction correlation.
- RP acknowledgment and error handling.
- Durable submission state.
- Delivery-report processing.
- Incoming SMS processing.
- Duplicate prevention.

Verify that the actual selected incoming transport reaches the native durable store and Messages application.

Do not assume the IIL receive path and AP-side SIP receive path are interchangeable.

Correct demonstrated integration gaps.

---

## 13. P9 — CONTINUOUS ENGINEERING ACTION LOOP

For every demonstrated independently resolvable defect:

DETECT.

INVESTIGATE.

ESTABLISH ROOT CAUSE.

IMPLEMENT.

ADD REGRESSION COVERAGE.

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

Preserve LTE and independent management connectivity.

Do not stop merely because compilation succeeds.

Do not repeat previous work without new evidence.

---

## 14. P10 — PHYSICAL SMS FIRST LIGHT

Once a legitimate SMS transport is genuinely ready:

Verify existing durable message ID 4.

Verify the previously authorized recipient.

Verify the exact authorized message body.

Verify that the message has never been transmitted.

Release the existing message once.

Capture privacy-preserving evidence of:

- Actual physical transmission.
- Selected transport.
- Transaction correlation.
- Actual protocol submission result.
- Carrier acceptance.
- Durable message state.
- Delivery report if available.

Do not automatically retry ambiguous submissions.

Do not confuse generic modem acknowledgment or SIP transaction acceptance with actual carrier SMS acceptance.

After genuine carrier acceptance, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm whether his girlfriend received the message.

Do not fabricate delivery.

---

## 15. P11 — INCOMING SMS AND PRODUCTION ACCEPTANCE

Leave the verified SMS transport operational for a voluntary incoming message.

Verify actual incoming reception when available.

Confirm:

- Physical reception.
- Protocol acknowledgment.
- Native decoding.
- Durable storage.
- Conversation association.
- Messages application update.
- Background notification.
- Duplicate prevention.

Verify preservation of:

- LTE REGISTERED_HOME.
- Ordinary cellular internet.
- Native IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS and HTTPS.
- Wi-Fi hotspot.
- USB tethering.
- Independent USB management.
- ZeroTier.
- IMS bearer isolation.
- Service restart recovery.
- Durable SMS queue persistence.
- Registration backoff persistence.
- Verified rollback.

Perform guarded normal-reboot verification when appropriate.

---

## 16. STRICT ANTI-LOOP REQUIREMENTS

Do not spend another execution repeating:

- USIM inventory discovery.
- Failed EF_MSISDN retrieval.
- Unchanged IMSI-derived REGISTER attempts.
- Unchanged MSISDN-derived REGISTER attempts.
- Previously rejected SDM commands.
- Already completed ECI/TAC reconstruction.
- Already completed broad production call-graph audits.
- Already completed Astra implementation recovery.

Every substantial investigation must have:

- A specific unresolved question.
- An available evidence source.
- A defined engineering decision that the result could change.

If none exists, do not repeat the investigation.

---

## 17. EXTERNAL DEPENDENCY STANDARD

An unresolved issue is not automatically an external dependency.

Before making that classification, establish:

- The demonstrated physical failure.
- The exact missing information.
- Which independent approaches have already been evaluated.
- Why those approaches cannot establish the missing fact.
- Why the missing evidence changes the engineering decision.
- The smallest specific owner action required.
- The exact continuation procedure.

Do not claim that obtaining a particular IMPU guarantees registration success.

Do not claim that SIP 480 conclusively proves missing entitlement.

Do not claim that every conceivable local defect has been eliminated.

Complete all independently achievable engineering.

An external dependency checkpoint is not mission success.

If genuinely blocked, preserve a resumable state instead of wasting resources on unchanged experiments.

---

## 18. PREPARE SHARED VOLTE FOUNDATION

Do not begin physical voice-call testing during this SMS mission.

Ensure that any IMS architectural improvements remain reusable for future native VoLTE implementation.

Keep these shared components modular:

- Subscriber identity.
- IMS bearer.
- SIP transaction engine.
- Authentication.
- Security negotiation.
- IPsec lifecycle.
- Registration.
- Service routing.
- Network state.

Do not introduce SMS-specific architectural shortcuts that would prevent future voice integration.

---

## 19. CHECKPOINTS AND COMMITS

Maintain ./sms26.md throughout execution.

Create meaningful incremental commits.

Record:

- Architectural review findings.
- Demonstrated implementation defects.
- Established implementation comparison.
- Subscriber identity findings.
- Reference-handset evidence.
- Implemented corrections.
- Completed tests.
- Actual registration evidence.
- Actual SMS evidence.
- Installed and running executable hashes.
- Rollback paths.
- Exact continuation procedure.

Preserve unrelated owner changes.

Keep subscriber information and authentication material out of Git.

Do not push or merge without separate authorization.

---

## 20. FINAL ACCEPTANCE MATRIX

Provide actual evidence for:

- Native IMS architecture validated:
- Genuine serving-cell information:
- Subscriber identity validated:
- Reference-handset IMS evidence:
- Initial registration prerequisites:
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
- LTE preserved:
- USB preserved:
- ZeroTier preserved:
- Reboot persistence physically verified:
- Shared VoLTE foundation preserved:
- Final commits:
- Verified rollback:

Do not declare full Stage 06 complete.

---

## 21. FINAL DIRECTIVE

THE MODEM IS ONLINE.

LTE IS ALIVE.

THE IMS BEARER IS ALIVE.

GENUINE ECI AND TAC HAVE BEEN RECOVERED.

THE SECURITY PIPELINE IS CONNECTED.

THE OUTGOING SMS PIPELINE IS CONNECTED.

THE INCOMING SMS PIPELINE IS CONNECTED.

NOW CHALLENGE THE REMAINING ARCHITECTURAL ASSUMPTIONS.

ESTABLISH ACTUAL INTEROPERABILITY.

RESOLVE EVERY DEMONSTRATED LOCAL DEFECT.

COMPLETE LEGITIMATE SMS TRANSPORT READINESS.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY.

PRESERVE LTE AND RECOVERY.

NO REPEATED SPECULATION.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ONE SUCCESS CRITERION:

WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
