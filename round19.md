# NUXEL — SMS OR DIE 4 REAL
## ROUND 19 — TOTAL ACTION MODE
### ISIM FIRST LIGHT, IMS REGISTRATION AND PHYSICAL SMS ENDGAME

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ SM-G975F / beyond2lte

SoC: Exynos 9820

Modem: Shannon S5000AP

Baseband: G975FXXSEFUJ2

Carrier: KPN 204-08

Vendor firmware and artifacts: ./packs/

Mandatory starting checkpoint: ./sms18.md

Latest commits:

- 2663a0b8
- 369076c2

Rollback:

/var/lib/nuxel/radio-install.round18-*

Architecture: Native Linux. ZERO Android runtime dependencies.

---

## 00. ONE MISSION — WORKING PHYSICAL SMS

This is a continuous implementation and physical acceptance mission.

The sole successful outcome is actual working SMS on Nuxel.

Do not consider another investigation report, serializer implementation, host test, registration attempt or intermediate protocol breakthrough sufficient mission completion.

Round 18 identified a concrete unfinished local implementation path:

- The SIM reportedly contains USIM and ISIM applications.
- The UICC logical channel can now be opened.
- The supported TRANSMIT APDU operation remains unfinished.
- The actual provisioned IMS identities have not yet been retrieved.
- The native IMS bearer and SIP transport are already physically operational.

Complete this local implementation immediately.

Use the legitimate provisioned subscriber identities.

Establish actual IMS registration.

Complete the native SMS transport.

Submit the authorized physical SMS.

Whenever another locally resolvable issue is discovered, correct it and continue.

Do not voluntarily defer implementable work to another round.

---

## 01. EXPLICIT OWNER AUTHORIZATION

The owner authorizes the necessary legitimate, reversible engineering operations within the approved project environment, including:

- Native source-code modifications.
- Native radio-stack redesign where justified.
- Supported read-only UICC and ISIM operations.
- Supported logical-channel lifecycle integration.
- Legitimate subscriber identity retrieval.
- Native IMS identity-selection corrections.
- Native SIP registration corrections.
- Legitimate subscriber authentication integration.
- Carrier-supported IMS security integration.
- Native library and dependency integration.
- Native service implementation.
- Native modem-interface corrections.
- Network interface and routing corrections.
- Native SMS transport corrections.
- Build and packaging modifications.
- Host and on-device testing.
- Reversible deployment.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Persistent native configuration.
- Guarded normal-reboot verification.
- One authorized physical SMS submission.

Do not repeatedly request approval for these already-authorized reversible engineering operations.

Use the approved execution environment and existing permissions.

Do not circumvent execution-environment restrictions.

Preserve legitimate carrier authentication, subscriber security and independent recovery access.

No private SIM key extraction.

No fabricated subscriber identities.

No carrier entitlement bypass.

No speculative protected-partition writes.

No unnecessary kernel flashing or DTB/DTBO modifications.

Do not incur additional unapproved expenses or enable automatic spending increases.

---

## 02. AUTHORIZED FINAL SMS TEST

The owner explicitly authorizes one genuine physical SMS submission to his previously designated girlfriend.

Use the existing durable message ID 4.

Exact expected message body:

test SMS van Nuxel voor mijn schatje <3

Retrieve the existing recipient from the authorized durable message record.

Verify that message ID 4 remains untransmitted.

Reuse that record.

Do not create duplicates.

Do not transmit historical messages 1–3.

Keep message ID 4 held until genuine SMS transport readiness is established.

The owner authorizes the ordinary carrier charge for this single submission.

Do not automatically retransmit an ambiguous submission.

Once actual carrier acceptance is established, immediately report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm reception with his girlfriend.

Do not fabricate recipient confirmation.

Keep recipient information and message contents out of Git and diagnostic reports.

---

## 03. P0 — RESUME THE EXACT UNFINISHED ROUND 18 OPERATION

Read ./sms18.md in full.

Inspect commits 2663a0b8 and 369076c2.

Do not restart the entire investigation.

Round 18 explicitly identified the next concrete operation:

Complete the supported TRANSMIT APDU implementation and retrieve the legitimate provisioned IMS identities.

Prioritize this operation above further SIP field-matrix experiments.

Verify the live baseline:

- Installed and running daemon identities.
- LTE connectivity.
- CID1 state.
- CID2 state.
- IMS IP configuration.
- P-CSCF connectivity.
- rmnet1 configuration.
- USB management.
- ZeroTier management.
- Rollback availability.
- Durable SMS queue.

Keep message ID 4 held.

Immediately proceed to UICC integration.

---

## 04. P1 — RESOLVE THE SIM INVENTORY CONTRADICTION

Earlier rounds concluded that the SIM contained only USIM.

Round 18 reports both USIM and ISIM.

Determine why the earlier inventory differed.

Inspect the actual response structure, application count, slot association and application identifiers.

Verify the correct subscriber application inventory through supported read-only operations.

Do not infer ISIM presence solely from an ambiguous response or application name.

Establish the actual application identity.

Correct demonstrated parser or application-selection defects.

If ISIM is genuinely present, prioritize the legitimate ISIM-based registration path.

Retain the standards-supported USIM fallback for subscriptions without ISIM.

Do not hardcode either application inventory.

---

## 05. P2 — COMPLETE SUPPORTED UICC LOGICAL-CHANNEL INTEGRATION

Round 18 established that the supported OPEN CHANNEL operation succeeds.

The remaining local defect concerns the TRANSMIT APDU serialization and length handling.

Inspect the existing implementation and recovered vendor evidence.

Correct the supported read-only APDU transport implementation.

Verify:

- Correct logical-channel ownership.
- Correct application selection.
- Correct request serialization.
- Correct response parsing.
- Correct length validation.
- Correct transaction association.
- Correct status handling.
- Timeout handling.
- Channel cleanup.
- Service restart recovery.

Use synthetic fixtures for tests.

Do not perform arbitrary SIM operations.

Do not modify subscriber files.

Do not retrieve private authentication keys.

Do not expose subscriber information in logs.

Build, test, deploy reversibly and physically verify the supported read path.

Do not stop after correcting the serializer.

Continue directly to provisioned identity retrieval.

---

## 06. P3 — RETRIEVE THE ACTUAL PROVISIONED IMS IDENTITIES

Use the verified legitimate ISIM application and supported read-only interface.

Retrieve and correctly interpret the applicable provisioned identity records:

- EF_DOMAIN.
- EF_IMPI.
- EF_IMPU.

Determine the actual record formats using the applicable standards and verified implementation evidence.

Handle multiple legitimate public identities correctly.

Do not assume the first record is necessarily the correct registration identity.

Verify that the selected identity belongs to the actual subscription.

Keep all private subscriber information within the necessary runtime components.

Do not print or commit actual identity values.

Use redacted diagnostics and synthetic test fixtures.

Implement the complete native identity-provider integration.

Connect it to the existing SIP registration backend.

Do not continue relying on derived identities when valid provisioned identities are available and applicable.

---

## 07. P4 — COMPLETE THE NATIVE IMS IDENTITY LIFECYCLE

Implement standards-consistent identity selection using:

- Verified ISIM application inventory.
- Provisioned private identity.
- Provisioned public identities.
- Provisioned home-network domain.
- Legitimate carrier configuration.
- Standards-supported USIM fallback where applicable.

Consult the applicable requirements in:

- 3GPP TS 31.103.
- 3GPP TS 31.102.
- 3GPP TS 23.003.
- 3GPP TS 24.229.
- 3GPP TS 33.203.

Ensure that identity selection, application selection and authentication selection remain consistent.

Do not invent identities.

Do not enumerate identities to discover which ones the carrier accepts.

Do not impersonate another subscriber.

Implement appropriate failure handling when provisioned records are unavailable or invalid.

Build, test, deploy and continue directly to physical registration.

---

## 08. P5 — REGISTER USING VERIFIED PROVISIONED IDENTITIES

Preserve the working physical IMS bearer and native SIP connectivity.

Preserve the qualified IMS APN behavior.

Preserve the working rmnet1 configuration.

Preserve the Round 18 SIP formatting corrections and network Retry-After handling.

Use the verified legitimate identity configuration to construct the registration request.

Honor any active network backoff interval.

Physically exercise the existing native registration backend.

Capture privacy-preserving evidence of the actual response.

Determine whether the previously observed SIP 480 changes after legitimate provisioned identity selection.

If registration remains unsuccessful, inspect the actual response and applicable registration requirements.

Do not automatically conclude that the carrier requires a proprietary Android client.

Do not treat SIP 480 alone as proof of an external provisioning restriction.

Correct demonstrated local defects.

Continue through the next legitimate registration attempt.

---

## 09. P6 — RESOLVE ALL REMAINING LOCAL REGISTRATION DEFECTS

Review the existing registration implementation for demonstrated deficiencies in:

- Identity handling.
- Request construction.
- Transaction association.
- Contact handling.
- Supported feature negotiation.
- Security negotiation.
- Access-network information.
- Registration lifecycle.
- Authentication continuation.
- Registration expiration.
- Refresh and recovery.

Use applicable standards and verified vendor behavior.

Do not blindly copy unrelated carrier configuration.

Do not claim unsupported capabilities or device certification.

Do not repeat unchanged failed requests.

Respect network retry requirements.

For each demonstrated local defect:

IMPLEMENT → TEST → DEPLOY → VERIFY → CONTINUE.

Do not defer independently achievable corrections.

---

## 10. P7 — COMPLETE LEGITIMATE AKA AUTHENTICATION

When a genuine network authentication challenge arrives, exercise the existing native authentication integration.

Determine the correct supported authentication application and interface for the selected legitimate IMS identity.

Verify the complete authentication lifecycle.

Ensure:

- Correct challenge association.
- Supported secure subscriber authentication.
- Correct transaction continuation.
- Applicable security negotiation.
- Proper failure handling.
- Correct network acceptance verification.

Do not extract private SIM authentication keys.

Do not fabricate authentication responses.

Do not expose authentication material in logs.

Do not bypass carrier authentication.

If the existing bridge requires corrections, implement them immediately.

If another native security component is required, integrate it legitimately.

Build, test, deploy and continue.

---

## 11. P8 — ACHIEVE PHYSICAL IMS REGISTRATION

Require actual network acceptance of the native registration transaction.

Do not report registration success based on:

- Physical bearer connectivity.
- P-CSCF connectivity.
- Successful request transmission.
- Generic modem acknowledgment.
- A provisional SIP response.
- A local state flag.
- Host-test success.

Verify actual registration acceptance.

Update the native registration state correctly.

Report the verified registration status through the supported modem interface.

Verify registration stability.

Verify actual SMS transport availability.

Proceed directly to physical SMS integration.

---

## 12. P9 — COMPLETE NATIVE SMS-OVER-IMS

Reuse the existing native SMS infrastructure.

Inspect the actual implementation completeness of:

- Native SIP backend.
- Native SMS-over-IMS codec.
- SMS PDU codec.
- Durable SQLite store.
- Radio1 API.
- Native Messages application.

Exercise the complete supported SMS transaction lifecycle.

Correct demonstrated defects in:

- SMS encapsulation.
- Transport selection.
- Transaction association.
- Protocol acknowledgment.
- Submission-result handling.
- Delivery-report handling.
- Durable state transitions.
- Duplicate prevention.
- Timeout handling.
- Registration-loss recovery.
- Incoming SMS handling.

Follow applicable 3GPP TS 24.341 requirements.

Do not reintroduce previously disproved conventional SMS wire-domain assumptions.

Do not confuse generic SIP acknowledgment with actual SMS submission acceptance.

Do not release message ID 4 prematurely.

---

## 13. P10 — PHYSICAL SMS TO THE OWNER'S GIRLFRIEND

After actual IMS registration and SMS-specific readiness are established, release the existing authorized message ID 4.

Expected body:

test SMS van Nuxel voor mijn schatje <3

Use the existing authorized recipient.

Verify the message remains untransmitted.

Transmit once through the verified legitimate transport.

Capture privacy-preserving evidence of:

- Native message ID.
- Selected transport.
- Physical transmission.
- Transaction association.
- Actual submission result.
- Carrier acceptance.
- Durable final message state.
- Delivery report, if available.

Do not report queued or sending as successful submission.

Do not report generic protocol acknowledgment as carrier acceptance.

If a demonstrated local defect prevents submission, correct it and continue all independently achievable work.

Do not automatically retransmit an ambiguous or already-consumed submission.

Any additional physical submission after the authorization is consumed requires separate authorization.

Once actual carrier acceptance is established, immediately report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm reception with his girlfriend.

---

## 14. P11 — INCOMING SMS AND NATIVE APPLICATION ACCEPTANCE

Leave the native SMS transport operational for a voluntary incoming reply.

Verify actual physical incoming SMS when available.

Confirm:

- Network reception.
- Required protocol acknowledgment.
- Native decoding.
- Durable storage.
- Conversation association.
- Native Messages application update.
- Background notification.
- Duplicate prevention.
- Persistence.

If no incoming reply is available, complete all independently achievable implementation and testing.

Do not fabricate physical reception evidence.

---

## 15. P12 — PRESERVE THE WORKING NUXEL BASELINE

Throughout execution preserve:

- Ordinary LTE registration.
- CID1 internet connectivity.
- Native IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS and HTTPS.
- NetworkManager integration.
- Wi-Fi hotspot.
- USB tethering.
- Independent USB management.
- ZeroTier.
- IMS-specific routing isolation.

Maintain verified rollback capability.

Verify service restart recovery.

Verify guarded normal-reboot persistence when appropriate.

Verify registration recovery and durable SMS state.

Do not confuse persistent configuration with a successful physical reboot test.

Restore the known-good baseline if an experiment destabilizes the device.

---

## 16. ACTION MODE — NO VOLUNTARY PREMATURE COMPLETION

The mission is working physical SMS.

Whenever a locally resolvable defect is encountered:

DETECT.

INVESTIGATE.

IDENTIFY THE ROOT CAUSE.

IMPLEMENT THE CORRECTION.

TEST.

DEPLOY REVERSIBLY.

VERIFY PHYSICALLY.

CONTINUE.

Do not voluntarily terminate because:

- A serializer is incomplete.
- A supported read interface is missing.
- An application inventory parser is incorrect.
- A native identity provider is incomplete.
- A legitimate authentication interface needs integration.
- A registration request is incorrect.
- A security component is missing.
- A build dependency is missing.
- A test fails.
- A deployment fails.
- A physical registration attempt fails.
- An SMS transaction needs correction.

Fix the demonstrated local issue.

Continue through the next implementation stage.

Do not return another report that identifies an implementable next operation without attempting to implement it.

Do not repeat completed broad reverse engineering.

Do not repeat unchanged failed experiments.

Respect carrier backoff requirements.

Use the approved execution budget efficiently.

Maintain meaningful incremental commits.

---

## 17. STRICT EXTERNAL BLOCKER STANDARD

The previous rounds repeatedly identified supposed external provisioning restrictions that were later resolved through native corrections.

Do not repeat that pattern.

The following alone do not prove an external blocker:

- SIP 480.
- SIP 403.
- SIP 400.
- Missing AKA challenge.
- Registration timeout.
- Missing local identity retrieval.
- Missing local security integration.
- Incomplete native registration implementation.
- Absence of recognizable SIP strings in vendor binaries.

Complete the legitimate ISIM identity retrieval path first.

Verify the actual native registration behavior.

Correct demonstrated local defects.

If registration remains unsuccessful, establish the precise unresolved prerequisite.

Use independent carrier confirmation or a compatible stock-handset reference for the same SIM where available.

Do not automatically reflash the working Nuxel handset to Android.

Do not fabricate a stock reference.

If independent evidence is unavailable, explicitly distinguish an unresolved interoperability problem from a proven carrier restriction.

Do not bypass carrier requirements.

---

## 18. CHECKPOINT AND COMMIT REQUIREMENTS

Create meaningful commits for actual implementation corrections.

Expected areas include:

- SIM application inventory verification.
- Supported UICC logical-channel integration.
- TRANSMIT APDU corrections.
- Native ISIM identity provider.
- Legitimate identity-selection integration.
- Native registration corrections.
- Authentication and security integration.
- Physical registration acceptance.
- Native SMS transport corrections.
- Physical SMS acceptance.
- Persistence and recovery.

Preserve unrelated owner changes.

Keep private subscriber information, authentication material and firmware artifacts out of Git.

Do not merge or push unless separately authorized.

If a hard execution limit, approved budget limit or genuine external dependency prevents further progress, create an exact resumable checkpoint in ./sms19.md.

Include the actual completed implementation, deployed binary identity, physical evidence, remaining defects and precise next operation.

Do not label a checkpoint as mission success.

---

## 19. FINAL ACCEPTANCE REPORT

Report actual evidence for:

- IMS bearer preserved:
- P-CSCF connectivity:
- USIM/ISIM inventory verified:
- Supported UICC read interface operational:
- Provisioned IMS identities retrieved:
- Legitimate identity selection integrated:
- Physical REGISTER using provisioned identities:
- Actual SIP 480 root cause:
- Genuine AKA challenge received:
- Legitimate authentication successful:
- IMS security integration:
- Actual IMS registration:
- Native SMS transport ready:
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
- Final implementation commits:
- Remaining conclusively demonstrated external requirements:

Do not declare full Stage 06 complete.

Do not declare SMS AND ALIVE before actual physical acceptance.

---

## 20. FINAL EXECUTION DIRECTIVE

THE MODEM IS ONLINE.

LTE IS WORKING.

THE IMS BEARER IS WORKING.

THE P-CSCF IS RESPONDING.

THE NATIVE SIP TRANSPORT IS WORKING.

THE UICC LOGICAL CHANNEL HAS BEEN OPENED.

ISIM HAS REPORTEDLY BEEN DISCOVERED.

COMPLETE THE UNFINISHED READ IMPLEMENTATION.

RETRIEVE THE LEGITIMATE PROVISIONED IMS IDENTITIES.

FIX EVERY DEMONSTRATED LOCAL DEFECT.

ESTABLISH ACTUAL IMS REGISTRATION.

COMPLETE LEGITIMATE AUTHENTICATION.

EXERCISE THE NATIVE SMS TRANSPORT.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY WITH HIS GIRLFRIEND.

PRESERVE LTE AND RECOVERY.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ONE SUCCESS CRITERION: WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
