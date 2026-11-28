# NUXEL — SMS OR DIE 4 REAL
## ROUND 23 — IMS INTEROPERABILITY ROOT CAUSE AND PHYSICAL SMS ENDGAME
### EVIDENCE-DRIVEN ACTION MODE

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ / beyond2lte

Modem: Shannon S5000AP

Firmware: EFUJ2

Carrier: KPN 204-08

Architecture: Native Linux. ZERO Android runtime dependencies.

Mandatory starting checkpoint: ./sms22.md

Latest implementation commits:

- 70c80644
- f8a30e34

Currently deployed binary: a0195cb1d4cf40eb…

---

## 00. MISSION

The sole successful mission outcome is WORKING PHYSICAL SMS ON NUXEL.

Compilation, unit tests, IMS bearer activation, SIP connectivity and documentation are intermediate milestones.

Do not voluntarily stop at a demonstrated, independently resolvable implementation defect.

Continue through implementation, testing, reversible deployment and physical verification whenever the necessary prerequisites are available.

Maintain the existing approved execution budget, recovery safeguards and legitimate carrier authentication requirements.

---

## 01. CORRECT THE ROUND 22 CONCLUSION

Round 22 established:

- IMSI-derived public identity receives SIP 480.
- MSISDN-derived public identity receives SIP 480.
- Both attempts occurred over the active dedicated IMS bearer.
- No AKA challenge was received.
- No IMS registration occurred.

These observations do NOT conclusively establish that the subscription lacks IMS provisioning.

The actual root cause remains unresolved.

Do not classify the carrier as the definitive blocker without independent supporting evidence.

Investigate whether the native implementation is missing a required initialization step, registration prerequisite, security negotiation capability or supported carrier configuration.

Do not repeat unchanged unsuccessful registration requests.

---

## 02. EXPLICIT OWNER AUTHORIZATION

The owner authorizes the following necessary legitimate and reversible operations:

- Native source modifications.
- Native architecture redesign.
- Supported modem-interface integration.
- Standards-compliant SIP and IMS corrections.
- Supported USIM authentication integration.
- Native IMS security implementation.
- Supported alternative SMS transport integration.
- Native dependency and library integration.
- Host and device testing.
- Build and packaging corrections.
- Reversible deployment.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Guarded normal reboot.
- One previously authorized physical SMS submission.

Do not repeatedly request approval for these operations.

Preserve legitimate carrier entitlement, authentication, subscriber privacy, network backoff and independent recovery access.

Do not bypass carrier restrictions, extract private subscriber keys, fabricate device certification, impersonate another subscriber or perform speculative protected-partition writes.

Do not incur additional unapproved expenses.

---

## 03. SUBSCRIBER AND SMS AUTHORIZATION

The actual subscriber MSISDN of the KPN SIM installed inside Nuxel is:

+31648444066

This is already configured in:

/var/lib/nuxel/subscriber.conf

Preserve the protected mode-0600 runtime configuration.

The owner explicitly authorizes one physical transmission of existing durable message ID 4 to his girlfriend.

Authorized recipient:

Use the girlfriend's previously authorized telephone number stored in message ID 4.

Exact authorized message body:

test SMS van Nuxel voor mijn schatje <3

The ordinary carrier charge for this single submission is approved.

Verify the recipient, exact body and never-transmitted state.

Do not substitute the subscriber's own number.

Do not create another queued message.

Do not transmit historical messages 1–3.

Do not automatically retry ambiguous submissions.

Keep subscriber information and private message contents out of Git and public reports.

---

## 04. P0 — PRESERVE THE WORKING BASELINE

Read ./sms22.md and relevant previous checkpoints.

Verify:

- CP ONLINE.
- LTE REGISTERED_HOME.
- CID1 ordinary internet.
- CID2 dedicated IMS bearer.
- rmnet1 IPv6 configuration.
- P-CSCF routing.
- USB management.
- ZeroTier management.
- Protected subscriber configuration.
- Durable SMS queue.
- Retry-After enforcement.
- Current running binary.
- Verified rollback.

Keep message ID 4 held until genuine SMS transport readiness exists.

Do not unnecessarily rebuild previously verified components.

---

## 05. P1 — ROOT CAUSE DIFFERENTIAL

Create an evidence-based interoperability matrix covering:

- Carrier subscription entitlement.
- USIM-only subscriber identity configuration.
- Required IMS registration prerequisites.
- Modem IMS initialization.
- Carrier-supported access-network configuration.
- IMS bearer parameters.
- P-CSCF discovery.
- SIP registration lifecycle.
- Security negotiation.
- Authentication integration.
- Registration state reporting.
- SMS-over-IMS capability.
- Conventional SMS transport availability.

For each item record:

- What is implemented.
- What is physically verified.
- What is inferred.
- What remains unknown.
- Whether a demonstrated local defect exists.
- What evidence would resolve the uncertainty.

Do not treat modem command rejection as automatic proof of carrier non-provisioning.

Distinguish unsupported modem commands from actual network rejection.

Prioritize investigations that materially change the next engineering decision.

---

## 06. P2 — SAME-SIM REFERENCE EVIDENCE

The most valuable unresolved experiment is a supported stock handset using the same physical SIM.

If owner-provided reference evidence is available, establish:

- Whether ordinary SMS works.
- Whether IMS registration succeeds.
- Whether VoLTE is available.
- Whether SMS actually uses IMS or another transport.
- Which supported carrier configuration is selected.
- Whether relevant registration prerequisites differ from Nuxel.

Use only legitimate diagnostic information.

Do not collect private authentication keys or unnecessary personal information.

Do not automatically reflash Nuxel to Android.

If the owner has not supplied reference evidence, complete all independently achievable local work first.

If the reference test becomes essential, request that specific test rather than starting another speculative investigation.

---

## 07. P3 — AUDIT THE NATIVE IMS IMPLEMENTATION

Perform a complete standards-based review of the current native IMS lifecycle.

Use applicable versions of:

- 3GPP TS 23.003.
- 3GPP TS 24.229.
- 3GPP TS 31.102.
- 3GPP TS 33.203.
- 3GPP TS 24.341.
- Relevant GSMA IMS interoperability profiles.

Review the implementation for demonstrated defects involving:

- Subscriber identity selection.
- Initial registration prerequisites.
- SIP transaction lifecycle.
- Registration headers.
- Access-network information.
- Contact and capability representation.
- Security negotiation.
- Authentication challenge handling.
- Registration refresh.
- Network-imposed backoff.
- Registration rejection interpretation.

Separate mandatory standards requirements from optional carrier-specific behavior.

Do not invent carrier configuration values.

Do not enumerate subscriber identities.

Do not misrepresent device capabilities or certification.

Implement corrections supported by evidence.

Add regression tests.

---

## 08. P4 — IMS SECURITY AND AUTHENTICATION READINESS

Determine whether the current native IMS security implementation is sufficiently complete for legitimate registration.

Audit the existing authentication bridge and security lifecycle.

Verify supported algorithm handling, transaction correlation, security association lifecycle, timeout handling and cleanup.

Where demonstrated implementation gaps exist, complete them using appropriate native Linux facilities or maintained native libraries.

Preserve the actual USIM authentication boundary.

Use synthetic credentials only in offline tests.

Never substitute synthetic authentication results for actual network authentication.

Do not declare security readiness solely because the code compiles.

---

## 09. P5 — MODEM INITIALIZATION AUDIT

Review existing evidence from the exact EFUJ2 modem and corresponding vendor implementation.

Determine whether Nuxel has omitted a supported prerequisite that affects IMS service availability.

Reconcile previous assumptions concerning:

- SDM commands.
- IIL commands.
- IMS capability initialization.
- IMS preferences.
- Dedicated bearer lifecycle.
- Registration state reporting.

Distinguish commands that initiate operations from commands that merely report state.

Do not report fabricated registration state to the modem.

Do not repeat previously rejected commands without new evidence.

Implement and test any demonstrated missing supported prerequisite.

---

## 10. P6 — NATIVE SMS TRANSPORT INDEPENDENCE

IMS registration is a means to the objective, not the objective itself.

Reassess the supported SMS transport possibilities using actual modem and network evidence:

- Conventional circuit-switched SMS.
- SMS over NAS/SGs where supported.
- SMS over IMS.

Do not treat CS registration denial alone as definitive proof that every non-IMS SMS mechanism is unavailable.

Determine actual transport prerequisites and supported capabilities.

If a legitimate alternative transport is available, integrate it into the existing native SMS service.

Do not bypass carrier authorization or attempt unsupported transmission through arbitrary channels.

Maintain a transport-independent durable SMS architecture.

---

## 11. P7 — IMPLEMENT, TEST AND DEPLOY

For every demonstrated locally resolvable defect:

Identify the root cause.

Implement the correction.

Add regression coverage.

Run host tests.

Run ASan/UBSan tests.

Verify AArch64 builds.

Check complete command exit statuses.

Create verified rollback snapshots.

Deploy reversibly.

Verify installed and running binary hashes.

Verify physical behavior.

Continue to the next demonstrated defect.

Do not perform a new live registration attempt merely because a build succeeded.

Require a meaningful evidence-supported change and satisfaction of network retry requirements.

---

## 12. P8 — GENUINE REGISTRATION FIRST LIGHT

When legitimate registration prerequisites are satisfied, perform a controlled registration attempt.

Interpret the actual response correctly.

If an authentication challenge arrives, complete the supported native USIM authentication lifecycle.

Correct demonstrated local authentication or security implementation defects.

Verify genuine network registration acceptance.

A SIP 401 is not registration success.

A generic modem acknowledgment is not registration success.

A locally assigned REGISTERED state is not registration success.

A SIP 480 alone is not definitive proof of missing carrier entitlement.

Do not perform uncontrolled retries.

---

## 13. P9 — COMPLETE PHYSICAL SMS

Once a legitimate SMS transport is genuinely ready, complete the existing native SMS transaction lifecycle.

Verify:

- SMS encoding.
- Transport encapsulation.
- Transaction correlation.
- Actual carrier submission result.
- Durable message-state transitions.
- Delivery-report handling.
- Timeout behavior.
- Duplicate prevention.

Release authorized message ID 4 once.

Capture privacy-preserving physical transmission and carrier acceptance evidence.

Do not confuse a generic transport acknowledgment with actual SMS acceptance.

After carrier acceptance, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm whether his girlfriend received the message.

Do not fabricate delivery.

---

## 14. P10 — INCOMING SMS

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

Complete all independently achievable implementation and testing.

Do not fabricate incoming SMS evidence.

---

## 15. P11 — PRODUCTION REGRESSION VERIFICATION

Preserve and verify:

- LTE registration.
- Cellular IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS and HTTPS.
- Wi-Fi hotspot.
- USB tethering.
- Independent USB management.
- ZeroTier.
- IMS bearer isolation.
- Service restart recovery.
- SMS queue persistence.
- Registration backoff persistence.
- Verified rollback.

Perform guarded normal-reboot verification when appropriate.

Do not destabilize the working LTE implementation.

---

## 16. CONTINUOUS ACTION MODE

For every demonstrated locally resolvable issue:

DETECT.

INVESTIGATE.

IDENTIFY ROOT CAUSE.

IMPLEMENT.

TEST.

DEPLOY REVERSIBLY.

VERIFY PHYSICALLY.

CONTINUE.

Do not voluntarily stop while independently achievable engineering work remains.

Do not repeat unchanged experiments.

Do not consume the execution budget on investigations that cannot resolve the missing evidence.

A genuine external dependency is not mission success.

If one becomes unavoidable, document the precise missing evidence and the smallest external action required to obtain it.

---

## 17. CHECKPOINT AND COMMITS

Maintain ./sms23.md throughout execution.

Create meaningful incremental commits.

Record:

- Demonstrated root causes.
- Implementation changes.
- Completed tests.
- Physical evidence.
- Actual registration state.
- Actual SMS state.
- Installed and running binary hashes.
- Rollback paths.
- Remaining demonstrated defects.
- Exact continuation procedure.

Preserve unrelated owner changes.

Keep subscriber information, authentication material and private message contents out of Git.

Do not push or merge without separate authorization.

---

## 18. FINAL ACCEPTANCE MATRIX

Report actual evidence for:

- IMS interoperability root cause established:
- Native initialization verified:
- Subscriber configuration verified:
- Security negotiation verified:
- Actual network authentication challenge:
- Actual subscriber authentication:
- Genuine IMS registration:
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

## 19. FINAL DIRECTIVE

THE MODEM IS ONLINE.

LTE IS ALIVE.

THE IMS BEARER IS ALIVE.

THE SUBSCRIBER NUMBER IS CONFIGURED.

THE NATIVE SMS INFRASTRUCTURE EXISTS.

THE PREVIOUS IDENTITY HYPOTHESIS HAS BEEN TESTED.

NOW ESTABLISH THE ACTUAL INTEROPERABILITY ROOT CAUSE.

FIX EVERY DEMONSTRATED LOCAL DEFECT.

COMPLETE LEGITIMATE SMS TRANSPORT READINESS.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ONE SUCCESS CRITERION: WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
