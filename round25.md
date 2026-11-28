# NUXEL — SMS OR DIE 4 REAL
## ROUND 25 — ASTRA PRECISION ENDGAME
### NO HALF MEASURES — PHYSICAL SMS ACTION MODE

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ / beyond2lte

Modem: Shannon S5000AP

Firmware: EFUJ2

Carrier: KPN 204-08

Architecture: Native Linux. ZERO Android runtime dependencies.

Mandatory starting checkpoint: ./sms24.md

Latest commits:

- 35a68c8f
- dcc43c14
- ca59976b
- 8dd782e2
- a0512b29

Current production binary MD5:

0a09e67b82009ef09e528920a32aa387

Verified rollback:

/var/lib/nuxel/rollback-sms24r12-20261127T154133

---

## 00. SINGLE MISSION SUCCESS CRITERION

WORKING PHYSICAL SMS ON NUXEL.

There is exactly one successful mission outcome:

A legitimate native SMS transport becomes operational, the existing authorized message ID 4 is physically transmitted, actual carrier acceptance is established, and the owner can independently confirm recipient delivery.

Compilation is not success.

Passing tests is not success.

A working IMS bearer is not success.

A connected production call graph is not success.

Another theoretical explanation of SIP 480 is not success.

Complete every independently achievable engineering operation required to achieve the mission.

Do not voluntarily stop at a demonstrated locally resolvable defect.

The execution budget is capped at the owner's approved €20 allocation. Do not purchase additional credits or exceed this allocation.

Prioritize high-information engineering operations.

---

## 01. CHALLENGE PREVIOUS BLOCKER CLASSIFICATIONS

Previous rounds repeatedly classified unresolved implementation questions as external carrier dependencies.

Subsequent rounds discovered:

- Incorrect modem command identifiers.
- Disconnected security installation.
- Disconnected outgoing SMS dispatch.
- Disconnected incoming SMS processing.
- Placeholder access-network information.
- Incomplete subscriber identity handling.

Therefore, independently validate the latest external dependency classification.

Round 24 established that NET_CELL_INFO main 8/sub 17 is a supported read-only operation and produces a physical modem response.

The remaining response-layout uncertainty is not automatically an external dependency.

Determine whether existing vendor artifacts, kernel interfaces, documented protocols and offline analysis can resolve it.

Do not assume that the previous agent exhausted every independently achievable engineering avenue.

Equally, do not assume that recovering the cell identity will necessarily resolve SIP 480.

Establish evidence and causality.

---

## 02. EXPLICIT OWNER AUTHORIZATION

The owner authorizes all necessary legitimate and reversible engineering operations within the existing project environment and approved budget:

- Native source-code modifications.
- Native architectural redesign.
- Offline vendor protocol analysis.
- Supported read-only modem operations.
- Supported native modem integration.
- Native access-network information retrieval.
- Standards-compliant SIP and IMS implementation.
- Supported subscriber authentication.
- Native IPsec integration.
- Supported alternative SMS transport integration.
- Native library integration.
- Host and on-device testing.
- Build and packaging corrections.
- Protected runtime configuration changes.
- Reversible deployment.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Guarded normal reboot.
- One explicitly authorized physical SMS submission.

Do not repeatedly request approval for these already-authorized operations.

Preserve legitimate carrier authentication, subscriber privacy, network-imposed backoff, independent recovery access and rollback capability.

Do not bypass carrier restrictions, fabricate subscriber identities, misrepresent device certification, extract private authentication keys or circumvent execution-environment security controls.

Do not perform speculative protected-partition writes.

Do not incur additional unapproved expenses.

---

## 03. SUBSCRIBER INFORMATION AND SMS AUTHORIZATION

Actual subscriber MSISDN of the KPN SIM installed inside Nuxel:

+31648444066

Existing protected configuration:

/var/lib/nuxel/subscriber.conf

Preserve mode 0600 and appropriate ownership.

The owner explicitly authorizes one physical transmission of the existing durable SMS message ID 4 to his girlfriend.

Authorized recipient:

Use the exact previously authorized girlfriend's telephone number stored in message ID 4.

Exact authorized message body:

test SMS van Nuxel voor mijn schatje <3

The ordinary carrier charge associated with this single submission is approved.

Verify the existing recipient, exact body and never-transmitted state.

Do not substitute the subscriber's own telephone number.

Do not create another message.

Do not transmit historical messages 1–3.

Do not automatically retry an ambiguous submission.

Keep telephone numbers, private message contents and authentication material out of Git and public diagnostic reports.

---

## 04. P0 — VERIFY THE PRODUCTION BASELINE

Read ./sms24.md.

Inspect the latest implementation commits.

Verify:

- CP ONLINE.
- LTE REGISTERED_HOME.
- CID1 ordinary internet connectivity.
- CID2 dedicated IMS bearer.
- P-CSCF routing.
- USB management.
- ZeroTier management.
- Protected subscriber configuration.
- Durable SMS queue.
- Retry-After enforcement.
- Installed and running executable identity.
- Verified rollback.

Keep message ID 4 held.

Preserve unrelated owner changes.

Do not spend substantial execution time repeating previously verified baseline investigations.

---

## 05. P1 — RESOLVE NET_CELL_INFO RESPONSE STRUCTURE

The correct read-only NET_CELL_INFO operation has been recovered:

Main 8, sub 17, type 2.

The exact EFUJ2 vendor implementation contains:

IpcTxNetCellInfoList @0x3378d0

The CP physically responds to this operation.

The remaining uncertainty concerns the response structure and actual LTE cell identity field.

Prioritize offline analysis of the exact matching vendor receive-side implementation.

Investigate:

- Response dispatch.
- Receive-side decoding.
- Structure sizes and offsets.
- RAT-specific record layouts.
- Serving versus neighboring cell records.
- Field widths.
- Endianness.
- Validity indicators.
- Status fields.
- PCI.
- TAC.
- ECI.
- PLMN.

Use existing matching vendor artifacts and documented interfaces.

Determine whether existing native kernel interfaces or supported modem information surfaces expose the same genuine serving-cell information.

Do not invent offsets.

Do not infer field meaning merely because a numerical value appears plausible.

Do not fabricate ECI values.

Do not transmit speculative modem commands.

Establish independently supported field semantics before using decoded values in network signaling.

Implement bounded native decoding and regression coverage.

---

## 06. P2 — VALIDATE TAC AND ACCESS-NETWORK INFORMATION

Round 24 reports:

3GPP-E-UTRAN-FDD;utran-tac=0000

Independently validate that the decoded value genuinely represents the serving TAC rather than an unrelated status field.

Validate the applicable access-network information syntax against relevant standards.

Determine whether the current implementation uses the appropriate serving-network identity, access technology and cell identity representation.

Distinguish mandatory requirements from optional fields.

When genuine information is unavailable, use standards-compliant handling rather than fabricated values.

Do not substitute home-network information for serving-network information.

Correct demonstrated local defects.

Add regression tests covering unavailable, stale, malformed and contradictory serving-cell information.

---

## 07. P3 — REFERENCE EVIDENCE WITHOUT CIRCULAR INVESTIGATION

The owner has confirmed that the same physical SIM works in another phone.

This establishes that the observed services work on that reference handset.

It does not independently establish the exact SMS transport or IMS registration configuration.

Use legitimate reference evidence if available:

- Actual IMS registration status.
- Actual VoLTE availability.
- Actual SMS transport.
- Serving-cell information.
- Authorized registration header diagnostics.
- Supported carrier configuration.

Do not bypass handset security.

Do not extract protected credentials or authentication material.

Do not automatically reflash Nuxel to Android.

If a specific reference observation is genuinely indispensable, identify precisely what is needed.

Do not consume the approved budget repeatedly investigating a question that cannot be answered from available evidence.

---

## 08. P4 — ACTUAL SIP 480 ROOT CAUSE

The network currently returns SIP 480 before any AKA challenge.

Previous rounds tested:

- IMSI-derived IMPU.
- MSISDN-derived IMPU.
- Different security negotiation configurations.
- Access-network information variations.
- Discovered P-CSCF endpoints.

Do not repeat these unchanged experiments.

A SIP 480 does not conclusively establish:

- Missing subscription entitlement.
- Incorrect IMPU.
- Missing operator provisioning.
- Incorrect ECI.
- An unsupported handset.
- Any other single specific root cause.

Audit the actual current registration implementation against applicable standards and verified carrier requirements.

Prioritize demonstrated differences that could affect initial registration.

Review:

- Legitimate subscriber identity configuration.
- Registration prerequisites.
- Access-network information.
- Contact representation.
- Device instance lifecycle.
- Supported capabilities.
- Security negotiation.
- SIP transaction lifecycle.
- P-CSCF selection.
- Network response interpretation.

Correct demonstrated local defects.

Only perform a new controlled registration attempt after a meaningful evidence-supported correction and satisfaction of network retry requirements.

---

## 09. P5 — DO NOT ASSUME IMS IS THE ONLY SMS PATH

The mission is working native SMS.

IMS is one possible transport.

Reassess legitimate supported transport availability using existing evidence:

- Conventional circuit-switched SMS.
- SMS over NAS/SGs where supported.
- SMS over IMS.

Do not interpret CS registration denial alone as conclusive proof that every alternative SMS transport is unavailable.

Determine actual supported transport prerequisites.

If a legitimate alternative transport is demonstrated, integrate it into the existing native SMS service.

Do not bypass carrier authorization or attempt transmission through arbitrary unsupported channels.

Preserve the transport-independent Radio1 API, durable store, native codec and Messages application.

---

## 10. P6 — VERIFY COMPLETE AUTHENTICATION AND SECURITY PATH

Round 23 connected previously disconnected authentication and security components.

Round 24 reports production reachability.

Production reachability is not equivalent to physical correctness.

Verify the complete lifecycle through offline synthetic integration tests:

- Challenge processing.
- Supported USIM authentication dispatch.
- Transaction correlation.
- Authentication result processing.
- Security negotiation.
- IPsec lifecycle.
- Protected registration.
- Registration acceptance.
- Registration refresh.
- Failure cleanup.

Use synthetic authentication material only in offline tests.

Do not substitute synthetic results for actual network authentication.

Do not report successful registration to the modem before genuine network acceptance.

Correct demonstrated implementation defects.

---

## 11. P7 — COMPLETE SMS PROTOCOL INTEGRATION

Verify the complete native SMS-over-IMS lifecycle against applicable TS 24.341 and TS 24.011 requirements.

Confirm:

- Correct TPDU encoding.
- Required RP-layer encapsulation.
- SIP MESSAGE integration.
- Submission transaction correlation.
- RP acknowledgment and error handling.
- Actual carrier acceptance interpretation.
- Incoming SMS decoding.
- Durable storage.
- Delivery-report handling.
- Timeout behavior.
- Duplicate prevention.
- Native Messages integration.

Round 24 implemented incoming IIL RP-DATA processing.

Verify that incoming messages through the actual selected native SMS transport reach the same durable application pipeline.

Do not assume the modem IIL receive path and AP-side SIP receive path are interchangeable.

Correct any demonstrated disconnected receive or result-processing paths.

---

## 12. P8 — CONTINUOUS IMPLEMENTATION AND VERIFICATION

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

Run relevant host tests, ASan/UBSan tests and AArch64 build verification.

Verify complete command exit statuses.

Create verified rollback snapshots.

Verify installed and running executable hashes.

Preserve LTE and independent recovery access.

Do not voluntarily stop at an independently resolvable implementation defect.

Do not repeat broad audits already completed in previous rounds without new evidence.

---

## 13. P9 — GENUINE REGISTRATION FIRST LIGHT

When legitimate registration prerequisites are established, perform a controlled registration attempt.

If an actual authentication challenge arrives:

Continue through the supported USIM authentication lifecycle.

Complete genuine security negotiation.

Correct demonstrated local defects.

Verify actual network registration acceptance.

Do not stop merely because the first AKA challenge arrives.

Do not confuse a SIP 401, generic modem acknowledgment or local registration state with actual network registration.

Do not enable SMS-over-IMS before genuine transport readiness.

---

## 14. P10 — PHYSICAL SMS FIRST LIGHT

Once an actual legitimate SMS transport is ready:

Verify the existing durable message ID 4.

Verify the previously authorized recipient.

Verify the exact message body.

Verify that the message has never been transmitted.

Release the existing message once.

Capture privacy-preserving evidence of:

- Physical transmission.
- Selected transport.
- Transaction correlation.
- Protocol submission result.
- Actual carrier acceptance.
- Durable message state.
- Delivery report if available.

Do not automatically retry an ambiguous submission.

Do not confuse generic SIP or modem acknowledgment with carrier SMS acceptance.

After genuine carrier acceptance, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm whether his girlfriend received the message.

Do not fabricate delivery.

---

## 15. P11 — INCOMING SMS AND PRODUCTION FUNCTIONALITY

Leave the verified native SMS transport operational for a voluntary incoming reply.

Verify actual incoming SMS when available.

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
- CID1 ordinary internet connectivity.
- Native IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS and HTTPS.
- Wi-Fi hotspot.
- USB tethering.
- Independent USB management.
- ZeroTier.
- IMS bearer isolation.
- Controlled service restart recovery.
- SMS queue persistence.
- Registration backoff persistence.
- Verified rollback.

Perform guarded normal-reboot verification when appropriate.

---

## 16. ASTRA EXECUTION EFFICIENCY

This execution has a strict owner-approved budget ceiling of €20.

Use it for high-information reasoning and demonstrated implementation defects.

Do not consume it on:

- Repeating previous reports.
- Repeating USIM inventory discovery.
- Repeating failed EF_MSISDN retrieval.
- Repeating unchanged REGISTER requests.
- Repeating rejected SDM commands.
- Repeated full repository audits without a specific hypothesis.
- Documentation that does not change the engineering decision.

Maintain incremental checkpoints so another agent can continue without repeating Astra's analysis.

Prioritize offline response-layout reconstruction, demonstrated protocol corrections and actual physical verification.

If the execution environment cannot expose remaining monetary budget, do not assume unlimited funds. Use an available execution limit and preserve a resumable checkpoint.

---

## 17. GENUINE EXTERNAL DEPENDENCY STANDARD

An unresolved question is not automatically an external dependency.

Before classifying an issue as external, establish:

- The demonstrated physical failure.
- The exact missing evidence.
- Which independent local approaches were evaluated.
- Why those approaches cannot establish the missing fact.
- Why the external evidence changes the engineering decision.
- The smallest specific owner action needed.
- The exact continuation procedure.

Do not claim that ECI acquisition guarantees successful IMS registration.

Do not claim that a successful reference REGISTER guarantees Nuxel interoperability.

Complete all independently achievable work.

An external dependency checkpoint is not mission success.

---

## 18. COMMITS AND CHECKPOINTS

Maintain ./sms25.md throughout execution.

Create meaningful incremental commits.

Record:

- NET_CELL_INFO response-layout findings.
- Genuine serving-cell information status.
- Access-network information corrections.
- Demonstrated interoperability defects.
- Implementation changes.
- Completed tests.
- Physical evidence.
- Actual IMS registration state.
- Actual SMS state.
- Installed and running executable hashes.
- Rollback paths.
- Remaining demonstrated defects.
- Exact continuation procedure.

Preserve unrelated owner changes.

Do not commit private subscriber information or authentication material.

Do not push or merge without separate authorization.

---

## 19. FINAL ACCEPTANCE MATRIX

Provide actual evidence for:

- NET_CELL_INFO response layout established:
- Genuine ECI acquired:
- Genuine TAC validated:
- Standards-compliant access-network information:
- Initial registration prerequisites verified:
- Actual authentication challenge:
- Actual subscriber authentication:
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
- Final commits:
- Verified rollback:

Do not declare full Stage 06 complete.

---

## 20. FINAL DIRECTIVE

THE MODEM IS ONLINE.

LTE IS ALIVE.

THE IMS BEARER IS ALIVE.

THE OUTGOING SMS PIPELINE IS CONNECTED.

THE INCOMING SMS PIPELINE IS CONNECTED.

THE SAME SIM WORKS IN ANOTHER PHONE.

THE CORRECT CELL INFORMATION COMMAND IS KNOWN.

THE MODEM PHYSICALLY ANSWERS IT.

NOW RESOLVE THE REMAINING DEMONSTRATED IMPLEMENTATION DEFECTS.

ESTABLISH GENUINE ACCESS-NETWORK INFORMATION.

ESTABLISH ACTUAL INTEROPERABILITY.

COMPLETE LEGITIMATE SMS TRANSPORT READINESS.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY.

PRESERVE LTE AND RECOVERY.

NO REPEATED SPECULATION.

NO DISCONNECTED IMPLEMENTATIONS.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ONE SUCCESS CRITERION:

WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.

check ./packs for firmware reference
