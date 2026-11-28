# NUXEL — SMS OR DIE 4 REAL
## ROUND 22 — SUBSCRIBER NUMBER SUPPLIED
### PHYSICAL SMS ACTION MODE

Repository: /Users/wicked/x/nuxel

Branch: cs/mob-round35-stage06

Device: Samsung Galaxy S10+ / beyond2lte

Modem: Shannon S5000AP

Firmware: EFUJ2

Carrier: KPN 204-08

Architecture: Native Linux. ZERO Android runtime dependencies.

Mandatory starting checkpoint: ./sms21.md

Latest commits:

- 29944772 — USIM EF_MSISDN decoder and MSISDN-derived IMPU identity path.
- d14aaff9 — Read-only EF_MSISDN probe and fixed-echo evidence.

Currently deployed binary: 432187dc…

Previous known-good binary: 3bee657c…

---

## 00. EXTERNAL INPUT NOW PROVIDED

The owner has supplied the missing subscriber telephone number.

Actual MSISDN of the KPN SIM installed inside Nuxel:

+31648444066

This is the subscriber's own telephone number.

It is NOT the recipient of the authorized outgoing SMS.

The missing owner-supplied input identified in Round 21 is now available.

Do not spend additional execution time attempting to retrieve this number from the SIM.

Do not repeat the EF_MSISDN raw APDU investigation unless genuinely new evidence invalidates the existing findings.

Keep the supplied telephone number in protected runtime configuration.

Do not commit it into source code, Git history, test fixtures or public diagnostic reports.

---

## 01. SINGLE MISSION SUCCESS CRITERION

WORKING PHYSICAL SMS ON NUXEL.

This is the sole successful mission outcome.

The owner does not consider any of the following sufficient:

- Successful compilation.
- Passing unit tests.
- Active IMS bearer.
- Successful SIP transmission.
- Authentication challenge alone.
- Generic modem acknowledgment.
- Locally reported registration.
- Queued SMS.
- Documentation-only progress.

The mission requires actual legitimate SMS transport readiness, physical transmission and carrier acceptance, followed by independent recipient confirmation.

Complete every independently achievable engineering operation necessary to achieve this objective.

Do not voluntarily stop at another locally resolvable implementation defect.

---

## 02. EXPLICIT OWNER AUTHORIZATION

The owner authorizes all necessary legitimate and reversible engineering operations within the existing project environment and approved budget, including:

- Native source-code modifications.
- Native architecture redesign where justified.
- Supported modem-interface integration.
- Native subscriber identity integration.
- Supported USIM authentication.
- Standards-compliant SIP and IMS implementation.
- Native security negotiation.
- Supported alternative SMS transport implementation.
- Native library integration.
- Build and packaging corrections.
- Host and on-device testing.
- Reversible deployment.
- Controlled service restarts.
- Controlled modem restarts with verified recovery.
- Temporary cellular connectivity interruption.
- Persistent runtime configuration.
- Guarded normal-reboot verification.
- One authorized physical SMS submission.

Do not repeatedly request approval for these already-authorized operations.

Preserve carrier authentication, legitimate subscription entitlement, network retry restrictions, subscriber privacy and recovery access.

Do not fabricate subscriber identities, authentication results, registration state or device certification.

Do not circumvent carrier restrictions or execution-environment security controls.

Do not extract private subscriber authentication keys.

Do not perform speculative protected-partition writes.

Do not incur additional unapproved expenses.

---

## 03. EXPLICITLY AUTHORIZED OUTGOING SMS

The owner explicitly authorizes the physical transmission of the existing durable SMS message ID 4 to his girlfriend.

Recipient:

Use the girlfriend's previously authorized telephone number already stored in durable message ID 4.

Expected exact message body:

test SMS van Nuxel voor mijn schatje <3

The owner approves the ordinary carrier charge associated with this single physical submission.

Verify that the existing recipient and message body match the authorized record.

Do not substitute the subscriber's own MSISDN as the recipient.

Verify that message ID 4 has never been transmitted.

Reuse the existing durable record.

Do not create a duplicate message.

Do not transmit historical messages 1–3.

Release ID 4 only after genuine transport readiness has been established.

Do not automatically retransmit an ambiguous submission.

Any additional physical submission after this authorization has been consumed requires separate authorization.

The owner will independently confirm whether his girlfriend received the message.

Keep both telephone numbers and private message contents out of Git and public diagnostic reports.

---

## 04. P0 — IMMEDIATE CONTINUATION FROM ROUND 21

Read ./sms21.md.

Inspect commits 29944772 and d14aaff9.

Verify the current repository and deployed daemon.

Preserve the verified production baseline:

- CP ONLINE.
- LTE REGISTERED_HOME.
- CID1 ordinary internet connectivity.
- CID2 dedicated IMS bearer.
- rmnet1 IPv6 configuration.
- P-CSCF discovery and routing.
- USB management.
- ZeroTier management.
- Durable SMS queue.
- Retry-After protection.
- Verified rollback capability.

The new MSISDN implementation has been built and tested but is not yet running in production.

Begin with the new implementation.

Do not restart the previous twenty-one rounds of investigation.

---

## 05. P1 — INTEGRATE THE PROVIDED SUBSCRIBER NUMBER

Integrate the supplied MSISDN through the existing protected subscriber configuration path.

Review the implementation introduced in commit 29944772.

Verify that the selected identity configuration conforms to applicable standards and the actual carrier requirements.

Treat the MSISDN-derived public identity as a new interoperability hypothesis, not an already verified carrier configuration.

Preserve the legitimate USIM-based authentication identity.

Ensure correct subscriber identity separation, normalization, configuration validation and privacy handling.

Correct any demonstrated implementation defects.

Do not invent alternative subscriber identities.

Do not enumerate telephone numbers.

Do not impersonate another subscriber.

Add regression coverage for protected runtime configuration using synthetic test data.

---

## 06. P2 — BUILD, TEST AND DEPLOY

Complete all relevant native host tests.

Complete ASan/UBSan tests.

Complete AArch64 build verification.

Verify complete command exit statuses.

Do not allow grep, head or tail pipelines to conceal build failures.

Create a verified rollback of the existing production binary and configuration.

Deploy the new native implementation reversibly.

Restart the affected service.

Verify the installed and running binary hashes.

Verify that LTE, CID2/rmnet1, USB and ZeroTier remain operational.

Keep message ID 4 held.

---

## 07. P3 — LEGITIMATE IMS REGISTRATION

Review the existing REGISTER gate and its documented prerequisites.

The owner has now supplied the missing subscriber telephone number.

Determine whether all remaining legitimate registration prerequisites have been established.

Preserve network-imposed Retry-After requirements.

Do not blindly disable registration protections.

Permit a standards-compliant registration attempt when the verified prerequisites are satisfied.

Observe and correctly interpret the actual network response.

Distinguish:

- Authentication challenge.
- Registration acceptance.
- Registration rejection.
- Network backoff.
- Unsupported configuration.
- Genuine external restriction.

Do not treat a SIP 401 challenge as completed authentication.

Do not treat a SIP 480 response alone as conclusive proof of missing provisioning.

Do not repeat unchanged unsuccessful requests.

Correct demonstrated local implementation defects.

---

## 08. P4 — COMPLETE THE NATIVE AUTHENTICATION LIFECYCLE

If the network provides a legitimate authentication challenge, continue through the supported subscriber authentication lifecycle.

Reuse the existing native USIM authentication integration where applicable.

Verify correct transaction correlation, supported security negotiation, response interpretation and state transitions.

Correct demonstrated implementation defects.

Keep all authentication material protected.

Do not substitute synthetic test results for actual subscriber authentication.

Do not report REGISTERED to the modem unless genuine network registration has been established.

Verify actual network registration acceptance before enabling SMS-over-IMS.

---

## 09. P5 — COMPLETE THE AVAILABLE NATIVE SMS TRANSPORT

IMS is a means to the mission, not the mission itself.

If legitimate IMS registration succeeds, complete the existing native SMS-over-IMS transport.

If another supported SMS transport becomes available through verified evidence, evaluate it.

Do not assume transport availability without physical evidence.

Reuse the existing native components:

- Radio1 API.
- SMS PDU codec.
- Native modem interface.
- Native SIP backend.
- Native SMS-over-IMS codec.
- Durable SQLite store.
- Native Messages application.

Correct all demonstrated defects in:

- Transport readiness.
- SMS encoding and encapsulation.
- Transaction association.
- Submission-result interpretation.
- Protocol acknowledgment.
- Durable state transitions.
- Delivery-report handling.
- Timeout handling.
- Duplicate prevention.

Do not confuse generic SIP or modem acknowledgments with actual carrier SMS acceptance.

---

## 10. P6 — PHYSICAL SMS FIRST LIGHT

After actual legitimate SMS transport readiness is established:

Verify existing message ID 4.

Verify the previously authorized recipient.

Verify the exact message body.

Release the existing message once.

Capture privacy-preserving evidence of:

- Physical transmission.
- Selected transport.
- Transaction correlation.
- Actual submission result.
- Carrier acceptance.
- Durable message state.
- Delivery report, if available.

Do not automatically retry ambiguous submissions.

Once genuine carrier acceptance has been obtained, report:

SMS SUBMITTED — RECIPIENT CONFIRMATION REQUIRED.

Do not claim delivery until independently confirmed by the owner.

---

## 11. P7 — INCOMING SMS AND APPLICATION INTEGRATION

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

Complete all independently achievable implementation and testing.

Do not fabricate incoming SMS evidence.

---

## 12. P8 — PRESERVE PRODUCTION FUNCTIONALITY

Verify:

- LTE REGISTERED_HOME.
- CID1 ordinary internet connectivity.
- Native IPv6.
- IPv4 through CLAT/NAT64.
- Cellular DNS and HTTPS.
- NetworkManager integration.
- Wi-Fi hotspot.
- USB tethering.
- Independent USB management.
- ZeroTier.
- Dedicated IMS bearer where applicable.
- IMS routing isolation.

Verify controlled service restart recovery.

Verify guarded normal-reboot persistence when appropriate.

Verify SMS queue persistence.

Verify registration backoff persistence.

Maintain rollback capability.

Do not destabilize the working LTE implementation.

---

## 13. CONTINUOUS ACTION MODE

Whenever a demonstrated locally resolvable defect is encountered:

DETECT.

INVESTIGATE.

IDENTIFY ROOT CAUSE.

IMPLEMENT.

TEST.

DEPLOY REVERSIBLY.

VERIFY PHYSICALLY.

CONTINUE.

Do not voluntarily stop at an independently resolvable implementation defect.

Do not repeat investigations whose results are already established.

Do not return documentation-only progress while independently achievable implementation work remains.

Do not perform uncontrolled network experiments.

Use the approved execution budget efficiently.

Prioritize physical evidence that changes the engineering decision.

Maintain incremental commits and resumable checkpoints.

---

## 14. GENUINE EXTERNAL DEPENDENCIES

The missing MSISDN identified in Round 21 has now been supplied.

Do not report it as an unresolved external dependency again.

If another genuine external prerequisite emerges, establish exactly why.

Complete all remaining independent local work.

Distinguish demonstrated carrier restrictions from unproven interoperability hypotheses.

If same-SIM stock-handset evidence is required, identify the exact observation needed.

Do not automatically reflash Nuxel to Android.

Do not fabricate carrier confirmation.

Do not circumvent genuine carrier restrictions.

An external dependency checkpoint is not mission success.

---

## 15. COMMIT AND CHECKPOINT REQUIREMENTS

Create meaningful incremental commits.

Maintain ./sms22.md throughout execution.

Record:

- Implementation changes.
- Completed tests.
- Physical evidence.
- Actual registration state.
- Actual SMS state.
- Installed and running binary hashes.
- Rollback paths.
- Remaining demonstrated defects.
- Exact next operation.

Preserve unrelated owner changes.

Keep subscriber numbers, private message contents and authentication material out of Git.

Do not push or merge without separate authorization.

If a hard execution limit, approved budget limit or genuine external dependency interrupts the mission, leave a fully resumable checkpoint.

---

## 16. FINAL ACCEPTANCE MATRIX

Provide actual evidence for:

- Owner-supplied MSISDN integrated:
- Native subscriber identity configuration verified:
- New implementation deployed:
- Actual network authentication challenge:
- Actual subscriber authentication:
- Actual IMS registration:
- Selected SMS transport:
- Physical SMS transport readiness:
- Message ID 4 transmitted:
- Carrier acceptance:
- Recipient confirmation:
- Incoming SMS:
- Native Messages integration:
- LTE preserved:
- USB management preserved:
- ZeroTier preserved:
- Reboot persistence physically verified:
- Final commits:
- Verified rollback:

Do not declare SMS AND ALIVE before physical SMS acceptance.

Do not declare full Stage 06 complete.

---

## 17. FINAL DIRECTIVE

THE MODEM IS ONLINE.

LTE IS ALIVE.

THE IMS BEARER IS ALIVE.

THE USIM INVENTORY IS VERIFIED.

THE NATIVE SMS INFRASTRUCTURE EXISTS.

THE NEW SUBSCRIBER IDENTITY IMPLEMENTATION EXISTS.

THE MISSING SUBSCRIBER NUMBER HAS NOW BEEN PROVIDED.

CONTINUE FROM ROUND 21.

FIX EVERY DEMONSTRATED LOCAL DEFECT.

COMPLETE LEGITIMATE NETWORK REGISTRATION.

COMPLETE THE NATIVE SMS TRANSPORT.

TRANSMIT AUTHORIZED MESSAGE ID 4 ONCE.

OBTAIN ACTUAL CARRIER ACCEPTANCE.

ALLOW THE OWNER TO CONFIRM DELIVERY.

PRESERVE LTE AND RECOVERY.

NO PREMATURE COMPLETION.

NO FABRICATED SUCCESS.

ONE SUCCESS CRITERION: WORKING PHYSICAL SMS.

SMS OR DIE 4 REAL.

ZERO ANDROID. PURE. IMMUTABLE.

WONQED4REAL.
