# ROUND 44 — LTE AND ALIVE
## THE ASTRA RESURRECTION HANDOVER — STAGE 06 FINAL COMPLETION

**Mission: Recover Astra's interrupted execution, preserve the achieved cellular connectivity milestone, and complete Stage 06 to 100% physically verified acceptance.**

You are continuing an existing implementation campaign. You are NOT starting a new investigation from scratch.

The previous GPT-6 Astra MAX execution terminated because its API credit balance was exhausted, after reporting 2,406,550 tokens used.

The termination was financial, not an established technical blocker.

Astra achieved the most important breakthrough of the entire Stage 06 campaign: real cellular internet on physical Nuxel hardware.

Your responsibility is to recover its exact working state, understand its changes, finish any interrupted operations, and complete the remaining acceptance criteria.

---

## 1. MANDATORY INITIAL RECOVERY AND RECONCILIATION

Before modifying anything, inspect:

- Current Git branch, HEAD and complete working-tree status.
- Staged, unstaged and untracked files.
- Recent commits and reflog.
- The complete `hw-mob-run.log`, if present.
- Other Astra execution logs and session artifacts.
- `/tmp/nuxel-round43/` and its deployment scripts, hardware logs, firmware analysis, test results and recovery artifacts.
- Current `mobile.md`.
- Existing Stage 06 reports and acceptance contracts.
- `CHANGELOG.md`.
- `docs/S5000AP-IPC41-DATA.md`.
- Current physical device state.
- Installed executable hashes versus repository build outputs.
- Active systemd services, overrides, timers and recovery jobs.
- Any incomplete deployment or Wi-Fi restoration operation.

Do not assume Astra committed its changes.

Do not reset, clean, stash away, overwrite or discard Astra's implementation.

Do not overwrite the owner's existing changes.

Preserve the current working tree and deployment state in a recoverable checkpoint before continuing.

Establish exactly where Astra stopped, including whether SMS or telephony work was already implemented, deployed or physically tested.

Produce a concise initial reconciliation report, then proceed with implementation and acceptance. Do not stop merely because the reconciliation report is complete.

---

## 2. ESTABLISHED ASTRA BREAKTHROUGH

The previous agent explicitly reported:

- Physical KPN LTE registration.
- Active CID 1.
- CALL_STATUS state 1.
- Cause 0.
- Active PDP context readback.
- Global IPv6 address.
- KPN DNS configuration.
- Successful DNS resolution.
- Successful HTTPS with HTTP 200 over `rmnet0`.
- Wi-Fi radio disabled during cellular-only verification.
- Wi-Fi interface down during cellular-only verification.
- ZeroTier reachable through cellular connectivity.

These constitute the reported successful cellular internet milestone.

Recover the underlying hardware logs and verify the evidence.

Do not discard this milestone or revert the working implementation simply because previous Stage 06 reports describe a nonworking modem.

Historical reports predating Astra's corrections contain materially incorrect assumptions.

---

## 3. ASTRA DISCOVERIES THAT MUST BE PRESERVED

### 3.1 Service-domain correction — CRITICAL

The previous implementation's supposed CS+PS setting actually selected CS-only and disabled packet service.

Astra corrected this command using vendor-derived vectors and CP readback.

This correction was followed by successful LTE registration and cellular internet.

Preserve the corrected service-domain semantics.

Never restore the historical incorrect encoding.

### 3.2 Registration decoder

Raw registration state 1 means NOT REGISTERED, not REGISTERED_HOME.

Previous reports claiming successful registration based on that value were incorrect.

Preserve the corrected vendor-derived registration conversion.

Distinguish:

- Network registration.
- Packet-service state.
- PDP context state.
- Actual IP connectivity.

Never substitute generic command acknowledgment for successful state transition.

### 3.3 Packet-service control

The corrected session flow avoids redundant PS attach when NET already reports successful registration.

GPRS_PS GET control flags must not incorrectly override verified registration state.

Preserve state-aware initial APN configuration, detach verification, bounded recovery and explicit failure reporting.

### 3.4 Native CP initialization

Astra corrected the omitted NV download during CP initialization.

The native loader now accepts a verified device-owned NV snapshot and checksum.

Preserve:

- NV preflight.
- Exact size validation.
- TOC-derived destination validation.
- Fail-closed handling.
- Corruption rejection before physical CP actions.
- Known-good recovery implementation.

The Samsung checksum convention recovered by Astra is:

`MD5(image || "Samsung_Android_RIL")`

This is an integrity convention, not proof of authenticity or authorization to modify protected data.

### 3.5 NV metadata

The previous item-360 interpretation was incorrect.

Astra recovered:

- APN descriptor index 220.
- Dual-subscription APN descriptor index 224.
- Value size 360 bytes.

These are logical descriptor indices, not physical EFS offsets.

Astra cross-checked DTK9 and EFUJ2 firmware.

The actual baseband reported by the physical device is G975FXXSEFUJ2.

Preserve the corrected metadata and fail-closed provisioning policy.

Do not reopen speculative NV provisioning investigations. Working cellular internet has already been achieved without arbitrary APN record modification.

### 3.6 Other protocol improvements

Preserve and verify Astra's implementation of:

- Complete generic response decoding.
- Response correlation.
- Vendor-derived golden vectors.
- SIM readiness verification.
- Correct RAT decoding.
- Preferred network mode readback.
- Corrected initial attach profile.
- Accepted PDP context definition.
- State-aware detach and recovery.
- Native GetIpInfo.
- IP configuration decoding.
- Bounded retries.
- Explicit failure states.
- Any completed native startup exchanges.

Inspect the status of the DAK certificate exchange. Preserve legitimate device authentication and existing device-owned credentials unchanged. Do not bypass authentication or expose protected material.

Treat all reported discoveries as implementation claims to reconcile against the actual source and hardware evidence.

---

## 4. IMMEDIATE PHYSICAL DEVICE HEALTH CHECK

Before restarting anything, determine:

- Whether the CP is online.
- Whether the SIM is ready.
- Current serving network and RAT.
- Actual registration state.
- Active PDP contexts.
- Current `rmnet` interfaces.
- IPv4 and IPv6 addresses.
- Routes and policy routing.
- DNS configuration.
- Wi-Fi state.
- USB management connectivity.
- ZeroTier connectivity.
- Radio daemon health.
- CP boot daemon health.
- Pending rollback or recovery timers.

The previous agent reported a Wi-Fi restoration timing race.

Verify whether it resolved successfully.

Do not assume the phone is currently in the same state as the last successful LTE test.

Preserve an independent management path before any disruptive test.

Do not restart the CP unnecessarily if the working cellular session is still active.

---

## 5. REPRODUCE AND PRESERVE CELLULAR INTERNET

First reproduce the achieved milestone using the current working implementation.

Verify:

- Correct native modem initialization.
- SIM readiness.
- Successful network registration.
- Active PDP context.
- Valid cellular IP configuration.
- Correct carrier DNS.
- Correct routes through the cellular interface.
- Real HTTPS connectivity.

Perform an isolated cellular-only acceptance test.

Ensure Wi-Fi and any other internet uplinks cannot accidentally satisfy the test.

Keep an independent management path available.

Verify actual traffic traverses the cellular interface using interface counters, routing evidence and interface-specific connectivity tests.

Record:

- Serving PLMN.
- RAT.
- Registration state.
- CID.
- PDP state.
- Address family.
- DNS result.
- HTTPS result.
- Cellular interface traffic evidence.

Do not log subscriber identifiers or protected credentials.

Astra demonstrated IPv6 connectivity. Determine actual IPv4 and dual-stack capabilities independently.

Do not claim IPv4 works merely because IPv6 HTTPS works.

Support the carrier's legitimately provisioned address families and document any carrier-dependent limitations.

Once the successful cellular baseline is reproduced, checkpoint it before making additional changes.

---

## 6. COMPLETE SMS FUNCTIONALITY

Inspect Astra's existing work before implementing anything.

Determine whether native SMS support is:

- Already implemented and verified.
- Implemented but untested.
- Partially implemented.
- Missing required integration.

Complete only what remains necessary.

Verify the supported native SMS path, including:

- Outbound message submission.
- Correct modem response handling.
- Actual message delivery.
- Incoming message notifications.
- Incoming message decoding.
- Delivery status where supported.
- D-Bus integration.
- Messaging application integration.
- Error handling.
- Persistence where applicable.

Use an owner-authorized test recipient and incoming test message.

Do not send unsolicited messages, contact random recipients or generate repeated billable traffic.

A successful submission acknowledgment alone does not establish delivery.

An inbound synthetic fixture alone does not establish physical SMS reception.

Where actual sending or receiving requires owner participation, prepare the test completely and request the minimum necessary action.

Preserve cellular internet while completing SMS integration.

---

## 7. COMPLETE TELEPHONY VERIFICATION

Voice functionality was reportedly working before the latest changes.

Treat this as a regression-sensitive subsystem.

Inspect the current implementation and determine whether Astra already performed physical telephony tests.

Verify:

- Incoming call notification.
- Outgoing call initiation.
- Call state transitions.
- Answer and reject handling.
- Call termination.
- Earpiece audio.
- Microphone audio.
- Speaker routing where supported.
- Correct dialer state.
- Recovery to idle.
- Cellular data recovery after a call.

Use only owner-authorized test numbers and ordinary test calls.

Do not place emergency calls for testing.

Determine whether voice uses VoLTE, circuit-switched fallback or another supported carrier mechanism.

Do not claim VoLTE unless independently demonstrated.

If voice requires fallback from LTE, ensure the radio returns to an appropriate data-capable state afterward.

Do not permanently force LTE-only mode if it breaks ordinary voice functionality.

---

## 8. COMPLETE NATIVE LINUX NETWORK INTEGRATION

Ensure working cellular connectivity is integrated into Nuxel's normal operating environment, rather than depending on manual diagnostic commands.

Inspect and complete the existing architecture for:

- Native radio daemon.
- ModemManager integration or existing native compatibility provider.
- NetworkManager integration.
- Cellular connection lifecycle.
- APN configuration.
- Mobile-data enable and disable.
- SIM status.
- Carrier display.
- Signal reporting.
- Network technology display.
- IP configuration.
- DNS.
- Route management.
- Wi-Fi and cellular coexistence.
- Nuxel Settings integration.
- Status bar indicators.

Use the existing architectural contracts.

Do not introduce Android runtime dependencies.

Do not replace working native components unnecessarily.

Verify that enabling and disabling mobile data behaves correctly without leaving stale routes, stale DNS configuration or incorrect UI state.

Ensure normal applications can use cellular internet without requiring manual interface binding.

---

## 9. AUTOMATIC RECOVERY AND PERSISTENCE

Once the current working baseline is safely checkpointed, verify:

### Session lifecycle

- Mobile data disconnect.
- Mobile data reconnect.
- Repeated connection establishment.
- Correct cleanup of stale PDP and IP state.

### Service lifecycle

- Radio daemon restart.
- Network integration service restart.
- Recovery from temporary service interruption.

### Network lifecycle

- Wi-Fi to cellular transition.
- Cellular to Wi-Fi transition.
- Wi-Fi restoration after isolated testing.
- Cellular fallback when Wi-Fi becomes unavailable.
- Correct route and DNS replacement.

### Device lifecycle

- Controlled normal reboot.
- Native CP initialization after reboot.
- SIM readiness after reboot.
- Network registration after reboot.
- Automatic cellular connectivity after reboot.
- SMS and voice availability after reboot.

Do not intentionally create dangerous or uncontrolled failure conditions.

Use bounded tests and preserve a known-good recovery path.

A normal reboot is permitted only after the current working implementation and management recovery arrangements have been verified.

TWRP is not the default execution environment.

Use the established TWRP recovery agreement only if a genuine boot-related defect or recovery requirement makes it necessary.

Do not modify kernel, DTB or DTBO speculatively.

---

## 10. NON-NEGOTIABLE SAFETY AND REGRESSION CONTRACT

Preserve:

- Known-good BOOT image.
- Existing kernel and device-tree baseline.
- Original firmware.
- Device-owned EFS contents.
- Identity and calibration data.
- Existing security and authentication mechanisms.
- USB management connectivity.
- Wi-Fi management connectivity.
- ZeroTier management connectivity.
- Previously working hardware and applications.

Do not:

- Copy another device's EFS.
- Modify device identity.
- Rewrite calibration data.
- Bypass carrier restrictions.
- Bypass modem authentication.
- Guess NV offsets.
- Perform arbitrary raw NV provisioning.
- Regenerate checksums to conceal corruption.
- Reflash firmware speculatively.
- Disable security controls to make tests pass.
- Revert Astra's successful fixes to satisfy historical assumptions.

Keep direct NV provisioning disabled.

Any experiment must have a specific evidence-supported hypothesis, a bounded execution plan and an appropriate recovery path.

---

## 11. REGRESSION TESTING

Run the complete relevant test suites, including:

- Native CP bootloader tests.
- NV preflight tests.
- Corrupted NV rejection.
- Incorrect NV length rejection.
- Incorrect checksum rejection.
- IPC encoding tests.
- IPC decoding tests.
- Vendor golden-vector tests.
- Registration conversion tests.
- Service-domain tests.
- SIM readiness tests.
- Data-session FSM tests.
- Detach and recovery tests.
- IP configuration tests.
- RFS and NV policy tests.
- SMS tests.
- Telephony tests.
- Network integration tests.
- Sanitizer checks.
- Fuzzing.
- Native AArch64 builds.

Capture actual process exit statuses.

Do not hide build failures behind `grep`, `head`, `tail` or `tee` pipelines.

Distinguish mock tests, host tests, native builds and physical acceptance.

Never change expected test values merely to accommodate incorrect implementation behaviour.

---

## 12. AUTONOMOUS EXECUTION WITHOUT REPEATING HISTORY

Work continuously through the remaining acceptance criteria.

For each incomplete criterion:

1. Inspect existing implementation.
2. Establish the actual failure.
3. Identify the smallest evidence-supported correction.
4. Implement it.
5. Test it.
6. Deploy safely where necessary.
7. Verify physical behaviour.
8. Checkpoint the result.
9. Proceed to the next criterion.

Do not stop after producing a plan or report when implementation remains possible.

Do not spend millions of tokens rediscovering Astra's completed work.

Do not reopen previously disproven theories without contradictory new evidence.

If an experiment fails repeatedly without producing new information, stop repeating it and reconsider the underlying hypothesis.

If an external blocker requires owner participation, complete all independent work first and request only the necessary intervention.

Checkpoint after every major physical milestone so another interrupted execution cannot lose the current state.

---

## 13. STAGE 06 FINAL ACCEPTANCE MATRIX

Every applicable criterion must have explicit evidence.

### Native modem

- CP initializes reliably.
- Correct NV input is validated.
- SIM becomes ready.
- Native radio services start successfully.
- No Android runtime dependencies are introduced.

### Cellular data

- Real network registration.
- Active PDP context.
- Valid cellular IP configuration.
- Carrier DNS.
- Cellular routing.
- Cellular-only HTTPS.
- Ordinary application connectivity.
- Mobile-data toggle.
- Automatic reconnection.

### Messaging

- Physical outgoing SMS delivery.
- Physical incoming SMS reception.
- Native messaging integration.

### Telephony

- Physical outgoing call.
- Physical incoming call.
- Two-way audio.
- Correct call lifecycle.
- Cellular data recovery after calls.

### Integration and persistence

- Correct Wi-Fi/cellular transitions.
- Correct UI status.
- Normal reboot persistence.
- Automatic service startup.
- Automatic cellular reconnection after reboot.
- Management connectivity preserved.
- Relevant regression tests pass.

Use the existing Stage 06 acceptance contract as the authoritative scope. Reconcile this matrix with that contract rather than silently expanding or reducing it.

---

## 14. FINAL DELIVERABLES

Create:

`reports/S5000AP-06-ROUND44-FINAL-ACCEPTANCE.md`

Include:

- Recovered Astra implementation state.
- Exact changes preserved from Astra.
- Additional changes made during this execution.
- Corrected root causes.
- Physical test evidence.
- Firmware version.
- Final deployed executable hashes.
- Network integration status.
- SMS results.
- Telephony results.
- Reconnection results.
- Reboot persistence results.
- Regression results.
- Recovery instructions.
- Remaining limitations, if any.
- Final acceptance matrix.

Update relevant architecture documentation and `CHANGELOG.md`.

Commit the completed implementation, tests and documentation.

Preserve unrelated owner changes.

Do not merge or push unrelated work without authorization.

---

## 15. TERMINATION CONDITION

This is a completion campaign, not an unlimited research campaign.

When all Stage 06 acceptance criteria are physically verified:

- Finalize documentation.
- Confirm repository and deployed implementation consistency.
- Commit the final changes.
- Confirm management connectivity.
- Report the final acceptance matrix.
- Output the completion marker:

**wonqed4real**

Then TERMINATE.

Do not start Stage 07.

Do not expand into NFC, fingerprint, sensors, camera, hotspot or unrelated subsystems.

If a genuine external blocker prevents complete acceptance, preserve every working milestone, document the exact outstanding requirement and terminate with an actionable handover instead of entering an endless investigation.

Never output the completion marker while required acceptance criteria remain unverified.

---

## FINAL MISSION STATEMENT

Astra already demonstrated real cellular internet on Nuxel.

Your job is to protect that breakthrough, recover the interrupted execution, finish the remaining native mobile networking functionality, and turn the demonstrated success into a reliable, persistent, fully verified Stage 06 implementation.

No regression.
No speculative reinvention.
No false completion.
No unnecessary scope expansion.

**LTE OR DIE is over.**

**LTE AND ALIVE — FINISH THE MISSION.**
