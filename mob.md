# NUXEL — OPERATION WONQ: THE TRIPLE KILL
## FINAL MOBILE NETWORKING IMPLEMENTATION CAMPAIGN
### LTE + TELEPHONY + SMS

**Repository:** `/Users/wicked/x/nuxel`
**Branch:** `cs/mob`
**Device:** Samsung Galaxy S10+ SM-G975F / beyond2lte
**SoC:** Exynos 9820
**Modem:** Shannon S5000AP
**Architecture:** Native Linux, zero Android runtime dependencies.

# 0. MISSION

Deliver a complete, functional native Linux mobile networking stack on the physical Nuxel phone.

The three mandatory objectives are:

- Fully working LTE mobile internet.
- Fully working incoming and outgoing telephone calls with bidirectional audio.
- Fully working incoming and outgoing SMS.

This is an implementation campaign, not a research-only assignment.

Do not terminate after discovering a defect, writing a report, compiling a candidate, restoring device nodes or obtaining network registration.

Implement the correction, validate it, deploy it through the established safe deployment process and continue with the next functional dependency.

Keep working through all independently actionable tasks.

Do not fabricate success or conceal failures.

# 1. CURRENT ESTABLISHED BASELINE

Read the latest:

- `mob.md`
- `reports/S5000AP-06-LTE-FINAL-EXECUTION.md`
- `reports/S5000AP-06-ROUND25-LIVE-CPBOOT-UNBLOCKED.md`
- `09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`
- All newer mobile networking commits and reports.

Reconcile these documents against the actual running device.

Latest reported findings:

- CP ONLINE.
- Real SIPC5 RSSI frames received by the kernel.
- Running kernel `4.14.253-gf7194c1d15ed-dirty`.
- Missing `/dev/umts_ipc0`.
- Missing `/dev/umts_rfs0`.
- Missing `/dev/umts_boot0`.
- `/dev/multipdp` and `/dev/s5p-smem` exist.
- Radiod has no apparent open modem transport descriptor.
- Live device tree declares `mif,num_iodevs = 22`.
- Live `iodevs` child is reportedly empty.
- Repository DTS contains the complete 22 IO-device definitions.

Relevant source:

`arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_26.dts`

Relevant driver functions:

- `create_io_device()`
- `sipc5_init_io_device()`
- `sipc5_deinit_io_device()`

Relevant expected channels:

- FMT: `umts_ipc0`, ID `0xeb`.
- RFS: `umts_rfs0`, ID `0xf5`.
- BOOT: `umts_boot0`, ID `0xd7`.
- PDP interfaces: `rmnet0..7`.

Treat the malformed live device tree as the immediate defect.

Do not assume the earlier NV/APN hypothesis has been disproven or confirmed.

# 2. PHASE A — RESTORE PERSISTENT MODEM DEVICE REGISTRATION

This is the first mandatory implementation target.

## A1. Identify the actual image construction defect

Compare:

- Original known-good device tree.
- Repository DTS and included DTSI files.
- Compiled DTB.
- Packaged BOOT image.
- Relevant DTBO contents.
- Actual live flattened device tree.
- Boot-image construction scripts.
- Previous known-working deployment artifacts.

Determine precisely where the 22 IO-device children disappear.

Distinguish between:

- Incorrect source selection.
- Incorrect device-tree compilation.
- Incorrect DTB packaging.
- Overlay replacement or merge behavior.
- Bootloader DTB selection.
- An incorrect deployed image.

Do not assume DTBO is responsible merely because the live tree is malformed.

## A2. Implement the smallest permanent correction

Correct the actual build or packaging defect.

Preserve:

- All 22 IO-device definitions.
- Exact channel IDs.
- IO-device types and attributes.
- Modem shared-memory configuration.
- Interrupt definitions.
- Reserved-memory regions.
- Existing CP boot functionality.
- Existing unrelated hardware configuration.

Do not introduce a broad device-tree redesign.

Do not perform unnecessary DTB round trips.

Do not modify unrelated hardware nodes.

## A3. Prepare the verified deployment

Follow the established TWRP A-only recovery agreement.

Locate and verify the actual partition mapping using authoritative device-specific information.

Locate the known-good BOOT and relevant recovery artifacts.

Prepare verified rollback copies and validate their integrity.

Produce a candidate image using the established Nuxel image-building process.

Verify the candidate contains the intended modem IO-device subtree and preserves unrelated device-tree content.

Only proceed with a physical deployment when the existing recovery agreement's requirements are satisfied.

Do not guess partition identities or bypass recovery safeguards.

If physical owner interaction with TWRP is required, provide the exact necessary interaction in one concise message. Continue independent implementation work while awaiting it.

## A4. Verify persistent recovery

After deployment, require:

- Nuxel boots normally.
- Live device tree contains all expected IO-device children.
- Kernel registers the expected modem interfaces.
- Real FMT, RFS and BOOT nodes exist.
- Radiod opens its real transport.
- CP remains ONLINE.
- SIM detection works.
- Real FMT TX/RX works.
- RFS requests and responses work.
- Wi-Fi, USB, ZeroTier and SSH remain functional.

Repeat verification after a controlled reboot.

Fix the image-generation pipeline permanently so future builds cannot silently remove these nodes.

Add a build-time regression check that rejects images missing the required modem subtree.

# 3. PHASE B — COMPLETE THE COMMON RADIO FOUNDATION

Before separating LTE, voice and SMS, complete their shared infrastructure.

Implement or repair:

- Persistent CP initialization lifecycle.
- Correct systemd service ordering.
- Real transport discovery.
- FMT request/response correlation.
- Unsolicited indication handling.
- RFS lifecycle.
- SIM state handling.
- Network registration.
- Signal-strength reporting.
- Radio availability reporting.
- Timeout and recovery behavior.
- Modem crash detection.
- Service restart recovery.
- Truthful D-Bus properties and signals.

Do not let radiod report healthy transport merely because its process is running.

Expose explicit distinctions between:

- CP online.
- Transport available.
- SIM ready.
- Network registered.
- Packet-data connected.
- Voice service available.
- SMS service available.

Retain the existing native Shannon/SIPC implementation.

Do not introduce Android runtime dependencies or fake AT ports.

# 4. PHASE C — FINISH STAGE 06: LTE

Restore and execute the complete existing data-session FSM.

Previously established sequence:

`SetServiceDomain → SetPreferredNetType → SetMobileDataSetting → SetDataProfile → SetLteAttachProfile → SetAlwaysOnPdn → PsAttach → SetPdpContext`

Preserve previously validated protocol semantics.

Do not repeat CID, PAP, IPv4/IPv6 or attach-flag experiments unchanged.

## C1. Establish the real bearer

Confirm the SIM has an active cellular data subscription and that the configured APN matches the actual carrier and plan.

Use a known-working reference SIM or reference phone where available.

Trace the complete initial-attach and PDP activation lifecycle.

Fix any demonstrated:

- Missing initialization operation.
- Incorrect profile configuration.
- Incorrect activation parameter.
- Missing unsolicited indication.
- Incorrect state transition.
- Incorrect timeout.
- Missing context-list processing.
- Incorrect interface association.

Do not treat GEN acknowledgement as bearer success.

Do not bypass carrier provisioning or access restrictions.

Do not modify raw NV/EFS records, subscriber identity, IMEI, RF calibration or security configuration.

Use supported carrier and modem configuration mechanisms.

## C2. Finish the Linux networking integration

Once the bearer connects:

- Receive actual modem IP configuration.
- Associate the correct rmnet interface.
- Configure IPv4 and IPv6 as provided.
- Configure routes.
- Configure DNS.
- Implement disconnect and reconnect.
- Integrate with NetworkManager.
- Integrate with ModemManager through a genuine supported native backend where appropriate.
- Synchronize the Nuxel Settings UI with authoritative connection state.

Do not fabricate a ModemManager device.

Do not hardcode a fake cellular IP.

## C3. LTE acceptance

Require:

- Real connected EPS bearer.
- Valid cellular IP.
- Correct rmnet interface UP.
- Cellular routing.
- Cellular DNS.
- Successful fresh HTTPS connection over cellular.
- Increasing rmnet TX/RX counters.
- Disconnect and reconnect.
- Recovery after reboot.

Perform cellular-isolated verification while preserving an independent USB management connection.

Only then mark Stage 06 PASS.

# 5. PHASE D — COMPLETE TELEPHONY

Audit the existing call-control implementation and complete missing functionality.

Use the actual native SIPC call-control protocol.

## D1. Call lifecycle

Implement and verify:

- Outgoing call initiation.
- Incoming call indications.
- Ringing state.
- Answer.
- Reject.
- Hang up.
- Remote hangup detection.
- Call-state synchronization.
- Busy and failure reporting.
- Cleanup after disconnected calls.
- DTMF where supported.

Do not report a call as active until the modem confirms it.

## D2. Voice audio

Complete the actual modem-to-Linux voice audio path.

Verify:

- Microphone uplink.
- Earpiece downlink.
- Bidirectional speech.
- Speakerphone.
- Mute/unmute.
- Call volume.
- Audio route restoration after hangup.
- Existing media audio remains functional.

Integrate with the existing Nuxel audio stack rather than introducing a second competing audio architecture.

## D3. LTE voice and IMS

Determine the carrier-supported voice mechanism.

Distinguish:

- Circuit-switched voice.
- Circuit-switched fallback.
- IMS registration.
- VoLTE.

Do not assume working LTE internet automatically provides VoLTE.

Implement the supported native voice path using legitimate modem interfaces and carrier provisioning.

If IMS is required, complete the actual supported IMS registration and call integration.

Do not fabricate IMS registration or bypass carrier entitlement.

Do not place emergency calls as part of testing.

## D4. Nuxel phone application

Connect the existing phone application to the authoritative radio backend.

Require:

- Dial pad.
- Incoming call screen.
- Answer/reject controls.
- Active call screen.
- Call duration.
- Mute and speaker controls.
- Call history.
- Correct error reporting.

Ensure all UI state reflects actual modem state.

## D5. Telephony acceptance

Using a consenting test recipient and ordinary test numbers, demonstrate:

- Outgoing call connects.
- Incoming call rings.
- Incoming call can be answered.
- Both parties can hear each other.
- Hangup works from either side.
- Repeated calls work.
- Calls recover after reboot.
- LTE data resumes or remains available as supported by the carrier.

Record the actual voice technology used.

Do not claim VoLTE success if only fallback voice works.

# 6. PHASE E — COMPLETE SMS

Implement the full native Shannon SMS lifecycle.

## E1. Outgoing SMS

Complete:

- Destination validation.
- Message encoding.
- GSM 7-bit encoding.
- UCS-2 encoding.
- Multipart messages.
- Modem submission.
- Submission acknowledgements.
- Failure reporting.
- Delivery reports where supported.

## E2. Incoming SMS

Complete:

- Unsolicited SMS indications.
- PDU decoding.
- Sender extraction.
- Timestamp extraction.
- GSM 7-bit decoding.
- Unicode decoding.
- Multipart reassembly.
- Duplicate suppression.
- Required modem acknowledgement.
- Persistent message storage.
- Notification delivery.

## E3. Messaging application

Connect the existing Nuxel messaging application to the actual radio backend.

Require:

- Conversation list.
- Message history.
- Send and receive.
- Pending/sent/failed state.
- Incoming notifications.
- Persistent storage.
- Correct timestamps.
- Multipart and Unicode support.

Do not create fake received messages or synthetic delivery confirmations.

## E4. SMS acceptance

Using a consenting test recipient, demonstrate:

- Outgoing SMS received by another phone.
- Incoming SMS received by Nuxel.
- Reply works.
- Unicode works.
- Multipart messages work.
- Message history persists after reboot.
- Failure states are truthful.

Record whether SMS uses the supported circuit-switched, NAS or IMS mechanism.

# 7. PHASE F — INTEGRATED MOBILE NETWORKING

Once the individual functions work, verify them together.

Required scenarios:

1. LTE browsing while receiving SMS.
2. Incoming call during LTE data activity.
3. Outgoing call followed by LTE recovery.
4. SMS after a completed telephone call.
5. Wi-Fi-to-cellular transition.
6. Cellular-to-Wi-Fi transition.
7. Mobile-data disable and enable.
8. Temporary network loss and recovery.
9. Radiod restart and recovery.
10. Controlled cold boot and automatic recovery.

Fix any cross-subsystem state conflicts.

Ensure there is one authoritative radio state machine and consistent connection lifecycle.

Avoid competing services independently controlling the modem.

# 8. CONTINUOUS IMPLEMENTATION MODE

For every identified defect:

1. Implement the smallest justified correction.
2. Build.
3. Run focused regression tests.
4. Deploy through the established safe process.
5. Verify on physical hardware.
6. Fix any regression.
7. Continue immediately to the next dependency.

No separate research-only rounds.

No unnecessary reports between implementation steps.

No repeated unchanged failed experiments.

No blind flashing, raw partition writes or destructive recovery shortcuts.

Do not weaken device security to make a feature appear functional.

Do not sacrifice existing working hardware.

Keep progressing on independent tasks if a physical interaction or external carrier dependency is temporarily unavailable.

# 9. BUILD-TIME REGRESSION PROTECTION

Add automated checks covering:

- Required modem IO-device definitions in compiled DTB.
- Correct modem channel IDs.
- Boot-image device-tree preservation.
- SIPC frame encoding and decoding.
- Data-session transitions.
- Call-state transitions.
- SMS encoding and decoding.
- Timeout and recovery behavior.
- Truthful D-Bus state.
- Network interface lifecycle.

Run the existing unit, fuzz and sanitizer suites.

Build with strict warnings.

Ensure the deployed binary corresponds to the committed source.

# 10. FINAL DELIVERABLES

Commit all completed implementation work to `cs/mob`.

Create:

`reports/S5000AP-MOBILE-NETWORKING-FINAL-ACCEPTANCE.md`

Include:

- Exact device-tree defect and permanent correction.
- Image build and deployment identity.
- Actual live modem device registration.
- CP and SIM status.
- LTE bearer and cellular-only HTTPS evidence.
- Incoming/outgoing call evidence.
- Bidirectional audio verification.
- Incoming/outgoing SMS evidence.
- Unicode and multipart SMS results.
- Reboot and reconnect results.
- Regression-test results.
- Source commits and deployed binary hashes.
- Remaining limitations, if any.

Do not merge unrelated changes.

Do not mark incomplete functionality as implemented.

# 11. THE WONQ VICTORY CONTRACT

Display `./wonqed` when persistent modem device registration and real IPC transport are restored.

Display `./wonqed4real` ONLY when ALL THREE physical acceptance targets pass:

- LTE INTERNET: PASS.
- TELEPHONY WITH BIDIRECTIONAL AUDIO: PASS.
- INCOMING AND OUTGOING SMS: PASS.

Final output:

CP:
IPC/RFS/BOOT:
SIM:
NETWORK REGISTRATION:
LTE BEARER:
CELLULAR IP:
CELLULAR HTTPS:
OUTGOING CALL:
INCOMING CALL:
BIDIRECTIONAL AUDIO:
OUTGOING SMS:
INCOMING SMS:
REBOOT RECOVERY:
REGRESSION TESTS:
FINAL COMMIT:

OVERALL RESULT: PASS / NOT YET PASS

No fabricated victory.

ONE NATIVE LINUX PHONE.

THREE WORKING MOBILE NETWORKING FUNCTIONS.

ZERO ANDROID RUNTIME DEPENDENCIES.

OPERATION WONQ — EXECUTE.
