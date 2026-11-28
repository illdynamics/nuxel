# NUXEL — SMS OR DIE 4 REAL
## ROUND 18 — TOTAL ACTION MODE
### PHYSICAL IMS REGISTRATION AND SMS DELIVERY ENDGAME

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ SM-G975F / beyond2lte

SoC: Exynos 9820

Modem: Shannon S5000AP

Baseband: G975FXXSEFUJ2

Carrier: KPN 204-08

Firmware and vendor artifacts: ./packs/

Latest implementation commits:

- 1f17fdf8
- adbbc9ce
- ecb31eac

Latest rollback:

/var/lib/nuxel/radio-install.round17-1795770284

Architecture: Native Linux. ZERO Android runtime dependencies.

---

## 00. ONE MISSION — WORKING PHYSICAL SMS

This is an ACTION round.

The objective is not another investigation report.

The objective is not another percentage increase.

The objective is not another list of components that should be implemented in a future round.

The objective is actual physical SMS functionality on Nuxel.

The previous execution established real IMS bearer connectivity, usable IMS IP configuration, P-CSCF discovery, native rmnet1 configuration and physical SIP communication with the carrier infrastructure.

The current immediate blocker is SIP 480 before the authentication challenge.

Resolve the actual cause.

Complete legitimate IMS registration.

Exercise the existing native SMS implementation.

Submit the authorized physical SMS.

Whenever another locally resolvable defect is encountered, investigate it, implement the correction, test it, deploy it and continue.

Do not arbitrarily terminate after completing one milestone.

The mission encompasses all remaining locally achievable implementation stages.

---

## 01. EXPLICIT OWNER AUTHORIZATION

The owner authorizes all necessary legitimate and reversible engineering operations within the existing project and approved execution environment, including:

- Native source-code modifications.
- Native radio-stack redesign where justified.
- Native SIP/IMS implementation corrections.
- IMS registration lifecycle corrections.
- Supported subscriber identity retrieval.
- Supported read-only USIM operations.
- Legitimate carrier configuration integration.
- Supported authentication and security integration.
- Native library and dependency integration.
- Native service implementation.
- Modem interface corrections.
- Network interface and routing corrections.
- Native SMS transport corrections.
- Build-system and packaging modifications.
- Host and on-device testing.
- Reversible deployment.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Persistent native configuration.
- Guarded normal-reboot verification.
- One authorized physical SMS submission.

Do not repeatedly request approval for these already-authorized operations.

Use existing project permissions and approved tooling.

Do not disable safety controls or circumvent execution-environment restrictions.

Preserve subscriber security, legitimate carrier authentication and independent recovery access.

Do not extract private SIM keys, fabricate identities, bypass authentication, circumvent carrier entitlement or perform speculative protected-partition writes.

Do not incur additional unapproved expenses.

Do not perform boot-critical modifications outside the established Nuxel recovery agreement.

---

## 02. AUTHORIZED FINAL SMS TEST

The owner explicitly authorizes one genuine physical SMS submission to his previously designated girlfriend.

Use existing durable message ID 4.

Exact expected message body:

test SMS van Nuxel voor mijn schatje <3

Retrieve the recipient from the existing authorized durable message record.

Verify that message ID 4 remains untransmitted.

Reuse this record.

Do not create a duplicate.

Do not release historical messages 1–3.

Keep message ID 4 held until genuine SMS transport readiness is established.

The owner authorizes the ordinary carrier charge for this single submission.

Do not automatically retransmit an ambiguous submission.

Once successful carrier submission is established, immediately report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

The owner will independently confirm reception with his girlfriend.

Do not fabricate recipient confirmation.

Keep recipient details and message contents out of Git and diagnostic reports.

---

## 03. ESTABLISHED ROUND 17 BREAKTHROUGH

The following findings are the current starting point:

- The missing IMS profile was a native regression.
- The qualified IMS APN is present.
- CID2 becomes physically active.
- GPRS_IP_CONFIGURATION supplies IMS IP configuration.
- Two P-CSCF addresses are discovered.
- CID2 is associated with rmnet1.
- Native rmnet1 configuration has been implemented.
- SIP REGISTER physically reaches the P-CSCF.
- Actual SIP responses are received.
- Previously malformed REGISTER formatting has been corrected.
- The IIL receive subcode mapping has been corrected.
- Native SIP-to-USIM authentication integration exists.
- Native SMS-over-IMS implementation exists.
- Current registration receives SIP 480 before AKA.
- Message ID 4 remains queued and untransmitted.
- Ordinary LTE connectivity remains operational.
- USB and ZeroTier management remain operational.

Do not restart previously completed IMS bearer reverse engineering without contradictory physical evidence.

Do not regress the working qualified IMS APN behavior.

Do not remove the working rmnet1 configuration.

Do not regress to the mandatory-ISIM assumption.

Do not reintroduce unsupported SMS wire-domain values.

Preserve the working physical SIP connectivity.

---

## 04. P0 — ESTABLISH AND PROTECT THE LIVE BASELINE

Read the latest Round 17 checkpoint and relevant preceding handovers.

Inspect commits:

1f17fdf8

adbbc9ce

ecb31eac

Connect to the physical handset.

Verify:

- Current repository checkpoint.
- Installed and running daemon identities.
- Ordinary LTE connectivity.
- CID1 state.
- CID2 state.
- IMS IP configuration.
- P-CSCF discovery.
- rmnet1 configuration.
- Actual IMS-specific routing.
- USB management.
- ZeroTier.
- Rollback availability.
- Durable SMS queue.

Ensure message ID 4 remains held.

Record a concise privacy-preserving baseline.

Immediately proceed to the registration blocker.

---

## 05. P1 — RESOLVE THE ACTUAL SIP 480 CAUSE

The previous report concluded that SIP 480 establishes an IMPU/provisioning problem.

This conclusion is not yet proven.

Investigate the actual SIP response and registration transaction.

Determine whether the response is attributable to:

- Incorrect legitimate subscriber identity selection.
- Incorrect registration request construction.
- Incorrect home-network domain handling.
- Missing required registration parameters.
- Incorrect carrier configuration.
- Missing supported IMS security negotiation.
- Incorrect transport selection.
- Incorrect P-CSCF selection.
- Incorrect registration lifecycle.
- Incorrect interpretation of the network response.
- Genuine subscription or carrier provisioning restrictions.

Inspect relevant response headers and diagnostic information while protecting subscriber privacy.

Compare the existing native registration behavior against the applicable standards and available verified vendor implementation.

Use the matching firmware artifacts under ./packs/ where necessary.

Do not assume that one SIP status code conclusively identifies the underlying cause.

Correct demonstrated local defects immediately.

---

## 06. P2 — VERIFY LEGITIMATE IMS SUBSCRIBER IDENTITY SELECTION

Review the existing USIM-derived identity implementation.

Verify the distinction between:

- Private IMS identity.
- Public IMS identity.
- Home-network domain.
- Subscription-associated telephone number.
- Carrier-provisioned IMS identities.

Use applicable standards, including 3GPP TS 23.003, TS 24.229 and TS 31.102.

Determine the legitimate identity-selection behavior of the inspected Samsung implementation when ISIM is absent.

If required, implement supported read-only retrieval of the subscriber's own EF_MSISDN record through the appropriate USIM interface.

Validate whether the returned record is populated and applicable.

Do not assume EF_MSISDN is necessarily present or authoritative for IMS registration.

Use an MSISDN-based public identity only when supported by the verified subscription configuration and applicable carrier behavior.

Do not invent, enumerate or guess subscriber identities.

Do not impersonate another subscriber.

Keep all private identity information out of logs, commits and reports.

Implement and test the correct legitimate identity-selection mechanism.

Deploy reversible corrections and verify the physical registration outcome.

---

## 07. P3 — COMPLETE THE NATIVE REGISTER IMPLEMENTATION

Audit the existing native SIP REGISTER implementation against the applicable IMS requirements.

The previous round corrected:

- Malformed sip:sip URI construction.
- Incorrect self-referential Route behavior.
- Incorrect access-network indication.

Verify that these corrections remain present.

Review the remaining registration requirements and supported carrier behavior.

Determine whether the current implementation correctly handles:

- Registration identity selection.
- Request construction.
- Contact information.
- Transaction association.
- Supported feature negotiation.
- Security negotiation.
- Network access information.
- Registration expiration.
- Network-provided configuration.
- Authentication continuation.
- Registration refresh and recovery.

Do not fabricate capabilities or claim unsupported device certification.

Do not blindly copy unrelated carrier configurations.

Implement demonstrated corrections.

Add focused regression tests.

Build, deploy and physically verify.

If a new local defect is exposed, fix it and continue.

---

## 08. P4 — ESTABLISH THE LEGITIMATE AUTHENTICATION LIFECYCLE

The existing native SIP-to-USIM AKA bridge reportedly exists but has not been physically exercised.

Once a genuine network authentication challenge is received, exercise the supported authentication interface.

Verify the actual end-to-end lifecycle.

Ensure that:

- The network challenge is associated with the correct registration transaction.
- Authentication is performed through the supported secure subscriber interface.
- Private authentication material remains protected.
- Applicable security negotiation is completed.
- The registration transaction continues correctly.
- Authentication failures are handled truthfully.
- Registration acceptance is verified from actual network evidence.

Do not fabricate authentication responses.

Do not extract private SIM authentication keys.

Do not bypass carrier security or entitlement.

If the existing implementation is incomplete, implement the missing legitimate integration.

Do not stop merely because another authentication component requires implementation.

Test, deploy, verify and continue.

---

## 09. P5 — ACHIEVE ACTUAL IMS REGISTRATION

Drive the native registration lifecycle through the working IMS bearer.

Require authoritative physical network evidence of successful registration.

Do not report registration success based on:

- CID2 activation.
- P-CSCF discovery.
- Successful UDP transmission.
- Generic modem acknowledgment.
- A provisional SIP response.
- A local registration-state flag.
- A successful offline test.

When registration succeeds, update the native IMS state and report the verified registration status through the supported modem interface.

Verify registration stability and actual SMS transport availability.

If registration fails, investigate the actual response.

Correct demonstrated local defects.

Continue through the next legitimate registration attempt.

Do not repeat unchanged failed requests.

Respect network retry requirements and backoff.

---

## 10. P6 — EXERCISE THE EXISTING NATIVE SMS-OVER-IMS TRANSPORT

The existing SMS-over-IMS implementation is reportedly code-complete.

Treat that as an implementation checkpoint, not proof of physical interoperability.

Inspect and exercise the existing native transport.

Reuse:

- Native SIP backend.
- Native SMS-over-IMS codec.
- Existing SMS PDU codec.
- Existing SQLite store.
- Existing Radio1 API.
- Existing native Messages application.
- Existing duplicate-prevention mechanisms.

Verify the actual supported transaction lifecycle.

Correct demonstrated defects in:

- SMS encapsulation.
- Transport selection.
- Transaction association.
- Protocol acknowledgments.
- Submission-result handling.
- Delivery-report handling.
- Timeout handling.
- Durable state transitions.
- Registration-loss recovery.
- Incoming SMS handling.

Use applicable 3GPP TS 24.341 requirements.

Do not reintroduce unsupported conventional modem SMS domain values.

Do not confuse a generic SIP response with SMS submission acceptance.

Do not release the authorized message until the transport is genuinely ready.

---

## 11. P7 — SEND THE AUTHORIZED PHYSICAL SMS

After genuine IMS registration and SMS-specific readiness have been established:

Release existing authorized message ID 4.

Expected message:

test SMS van Nuxel voor mijn schatje <3

Use the existing authorized recipient.

Verify that the message remains untransmitted.

Transmit it once through the verified legitimate transport.

Capture privacy-preserving evidence of:

- Native message ID.
- Selected transport.
- Physical transmission.
- Transaction association.
- Actual submission result.
- Carrier acceptance.
- Durable message state.
- Delivery report, if available.

Do not report queued or sending as successful submission.

Do not report generic modem or SIP acknowledgment as carrier acceptance.

If a demonstrated local defect prevents submission, correct it immediately.

Do not automatically retransmit an ambiguous or already-consumed submission.

Any additional physical submission after the authorization is consumed requires separate authorization.

Once actual carrier submission succeeds, report immediately:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

---

## 12. P8 — INCOMING SMS AND NATIVE APPLICATION INTEGRATION

Leave the native SMS transport operational for a voluntary incoming reply.

Verify physical incoming SMS when available.

Confirm:

- Actual network reception.
- Correct protocol acknowledgment.
- Native SMS decoding.
- Durable storage.
- Conversation association.
- Native Messages application update.
- Background notification.
- Duplicate prevention.
- Persistence.

If no incoming reply is available, complete all independently achievable implementation and tests.

Do not fabricate physical incoming evidence.

---

## 13. P9 — PRESERVE AND HARDEN THE WORKING SYSTEM

Verify that the completed implementation preserves:

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
- IMS-specific routing isolation.

Verify controlled service restart recovery.

Verify guarded normal-reboot persistence where appropriate.

Verify IMS registration recovery.

Verify durable SMS state after restart.

Do not confuse persistent configuration files with actual reboot verification.

Maintain verified rollback capability throughout.

Restore the known-good baseline if an experiment destabilizes the handset.

---

## 14. ACTION MODE — MANDATORY CONTINUOUS IMPLEMENTATION

Whenever a locally resolvable problem is encountered:

DETECT.

INVESTIGATE.

IDENTIFY THE ROOT CAUSE.

IMPLEMENT THE CORRECTION.

TEST.

DEPLOY REVERSIBLY.

VERIFY PHYSICALLY.

CONTINUE.

Do not terminate merely because:

- A source-code defect is discovered.
- A parser is incomplete.
- A supported USIM read interface is missing.
- A legitimate identity-selection mechanism requires correction.
- A registration parameter is incorrect.
- A native SIP component requires implementation.
- Authentication integration requires correction.
- A supported security mechanism requires integration.
- A library or build dependency is missing.
- A test fails.
- A deployment fails.
- A state machine requires redesign.
- A physical registration attempt fails.
- An SMS transaction requires correction.

Implement the necessary local solution.

Do not deliberately defer independently achievable work to another execution.

Do not return another documentation-only report when implementation remains possible.

Do not repeat broad reverse engineering without a concrete unresolved question.

Do not repeat unchanged failed operations.

Use meaningful incremental commits.

Use the approved execution budget efficiently.

Do not treat arbitrary intermediate milestones as mission completion.

---

## 15. GENUINE EXTERNAL BLOCKERS

Previous rounds repeatedly attributed local defects to carrier provisioning.

Those conclusions were subsequently disproved.

Do not repeat that pattern.

The following alone do not establish an external blocker:

- SIP 480.
- SIP 403.
- Missing AKA challenge.
- Registration timeout.
- Absence of ISIM.
- Missing local configuration.
- Incomplete native implementation.
- Unverified assumptions about carrier policy.

Before declaring a genuine external requirement:

1. Verify the actual physical failure.
2. Inspect the applicable legitimate registration requirements.
3. Correct demonstrated local implementation defects.
4. Verify the deployed implementation.
5. Establish the precise unresolved external prerequisite.
6. Obtain independent carrier or compatible stock-handset evidence where available.

Do not automatically reflash the working Nuxel handset to Android.

Do not fabricate a stock reference result.

If an external carrier requirement is conclusively established, identify the precise supported action required from the owner or carrier.

Complete all independently achievable local work.

Do not bypass the requirement.

---

## 16. IMPLEMENTATION CHECKPOINTS

Create meaningful commits for all actual corrections.

Expected areas include:

- Registration diagnostics and root-cause identification.
- Legitimate subscriber identity selection.
- Native SIP registration corrections.
- Supported authentication and security integration.
- Physical registration corrections.
- Native SMS-over-IMS corrections.
- Physical acceptance.
- Persistence and recovery.

Combine commits where technically appropriate.

Preserve unrelated owner changes.

Keep temporary extraction files, firmware artifacts, subscriber information and authentication material out of Git.

Do not merge or push unless separately authorized.

If a hard execution limit or genuine external dependency interrupts the mission, create an exact resumable checkpoint in ./sms18.md.

Include completed work, deployed binary identity, actual physical evidence, remaining defects and the next concrete operation.

---

## 17. FINAL ACCEPTANCE REPORT

Provide actual evidence for:

- IMS bearer remains physically active:
- IMS IP configuration:
- P-CSCF connectivity:
- Actual cause of SIP 480:
- Legitimate IMS identity selection:
- Native REGISTER corrections:
- Genuine authentication challenge received:
- Legitimate USIM authentication successful:
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
- Final commits:
- Remaining conclusively demonstrated external requirements:

Do not declare full Stage 06 complete.

Do not declare SMS AND ALIVE before actual physical acceptance.

---

## 18. FINAL DIRECTIVE — SMS OR DIE 4 REAL

THE MODEM IS ONLINE.

LTE IS WORKING.

THE IMS PROFILE IS PRESENT.

CID2 IS PHYSICALLY ACTIVE.

RMNET1 IS OPERATIONAL.

THE P-CSCF IS REACHABLE.

THE CARRIER IS RESPONDING TO NATIVE SIP.

THE NATIVE SMS INFRASTRUCTURE EXISTS.

RESOLVE THE ACTUAL REGISTRATION BLOCKER.

FIX EVERY DEMONSTRATED LOCAL DEFECT.

COMPLETE LEGITIMATE USIM AUTHENTICATION.

ESTABLISH ACTUAL IMS REGISTRATION.

EXERCISE THE NATIVE SMS TRANSPORT.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY WITH HIS GIRLFRIEND.

PRESERVE LTE AND RECOVERY.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ACTION MODE.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
