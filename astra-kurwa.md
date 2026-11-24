# NUXEL — ASTRA FINAL EXECUTION
## LTE AND ALIVE: THE DEEPSEEK PREPPER
### Persistence, production integration and definitive technical handover

## 0. MISSION AND EXECUTION BOUNDARY

You are performing the final consolidation pass following the successful Astra cellular networking breakthrough on Nuxel.

The objective is NOT to repeat the Stage 06 reverse-engineering campaign.

The objective is to turn the already demonstrated cellular internet functionality into a persistent, normally usable Nuxel feature, complete its user-interface integration, and prepare an exceptionally detailed technical handover for DeepSeek V4 Pro Thinking.

Prioritize actual implementation, deployment and physical verification over further exploratory research.

This execution has a strictly limited budget. Create an initial checkpoint immediately and incremental checkpoints throughout execution.

Do not leave documentation and commits until the end.

If the execution is interrupted again, the next agent must be able to resume without losing progress.

---

## 1. RECOVER THE EXACT CURRENT STATE

Inspect the current repository and physical device before changing anything.

Review:

- Current Git branch and HEAD.
- Staged, unstaged and untracked files.
- Recent commits and reflog.
- Previous Astra execution logs.
- DeepSeek's subsequent reconciliation work.
- `/tmp/nuxel-round43/` and relevant deployment artifacts.
- `mobile.md`.
- `CHANGELOG.md`.
- `docs/S5000AP-IPC41-DATA.md`.
- Existing Stage 06 contracts and reports.
- Native radio and CP bootloader implementation.
- Installed executable hashes.
- Active systemd services, overrides and recovery timers.
- Existing network integration.
- Nuxel Settings, Quick Settings and top bar implementation.

Preserve unrelated owner changes.

Do not discard or overwrite Astra's uncommitted implementation.

The latest physical inspection reported:

- Active `rmnet0`.
- Global cellular IPv6 address.
- Cellular routing table 106.
- Source-based routing rule 30600.
- Interface-specific routing rule 30601.
- Cellular default route metric 2100.
- Wi-Fi default route metric 600.
- 5,030 received cellular packets.
- 8,221 transmitted cellular packets.
- Zero interface errors.
- Zero dropped packets.
- NetworkManager-generated resolver configuration.

These are historical observations to reconcile against the current running device, not values to hardcode.

The previous Astra execution also demonstrated cellular-only DNS and HTTPS HTTP 200 with Wi-Fi disabled, and ZeroTier remained reachable through cellular.

Preserve this achievement.

---

## 2. CREATE AN IMMEDIATE RECOVERY CHECKPOINT

Before any disruptive operation:

- Preserve the current working source implementation.
- Preserve deployed executable hashes and corresponding binaries.
- Preserve relevant systemd configuration.
- Preserve network configuration.
- Preserve existing recovery artifacts.
- Verify independent management connectivity.
- Record the exact current modem and cellular session state.
- Create a scoped Git checkpoint without including unrelated owner changes.

Do not restart the modem merely to establish its current state.

Do not sacrifice a working cellular connection for an unnecessary experiment.

---

## 3. PRESERVE ASTRA'S VERIFIED DISCOVERIES

The previous Astra execution corrected multiple foundational errors.

These include:

### Service-domain command

The historical supposed CS+PS configuration actually selected CS-only and disabled packet service.

Preserve the corrected vendor-derived service-domain encoding and CP readback.

This is a critical regression boundary.

### Registration decoding

Raw registration state 1 means not registered.

Previous reports incorrectly interpreted this as registered home.

Preserve the corrected registration conversion and distinguish registration from packet attachment, bearer activation and actual IP connectivity.

### CP initialization

The previous native loader omitted required NV input.

Astra implemented verified NV image handling during native CP initialization.

Preserve the validated input path, corruption rejection, TOC validation and recovery mechanisms.

### Samsung NV checksum

The recovered checksum convention is:

`MD5(image || "Samsung_Android_RIL")`

Preserve this integrity convention without treating it as authorization to modify protected records.

### Firmware and NV metadata

The physical device reported baseband G975FXXSEFUJ2.

Astra cross-checked EFUJ2 and DTK9.

The recovered APN descriptor indices are 220 and 224, with a value size of 360 bytes.

These are logical descriptor indices, not physical EFS offsets.

Do not reopen arbitrary NV provisioning investigations.

### Session management

Preserve:

- Corrected initial attach profile handling.
- Corrected PDP context definition.
- State-aware detach behaviour.
- Verified registration and attachment handling.
- Strict generic response validation.
- Response correlation.
- Native GetIpInfo.
- IP configuration decoding.
- Vendor-derived golden vectors.
- Bounded recovery.
- Explicit failure states.

Verify these findings against the actual implementation rather than relying exclusively on historical reports.

---

## 4. MAKE CELLULAR INTERNET PERSISTENT

The working cellular implementation must become a normal operating-system capability rather than a manually initiated diagnostic session.

Inspect the complete startup dependency chain:

1. Required filesystems and verified device-owned NV inputs.
2. Native CP initialization.
3. Modem readiness.
4. Radio daemon startup.
5. SIM readiness.
6. Network registration.
7. Mobile-data policy.
8. PDP context establishment.
9. IP configuration.
10. Route and DNS installation.
11. Network integration.
12. UI state publication.

Implement any missing startup ordering, readiness checks or service dependencies.

Use existing Nuxel architecture and systemd conventions.

Avoid arbitrary sleep-based startup sequencing where actual readiness signals are available.

Ensure cellular data automatically reconnects after normal reboot when the user's persisted mobile-data preference is enabled.

When mobile data is disabled, reboot must not silently enable it.

Do not hardcode:

- Current cellular IPv6 address.
- Current serving PLMN.
- Current DNS addresses.
- Current interface counters.
- A specific transient PDP session.
- Temporary deployment paths.

Obtain dynamic network configuration from the supported native modem interface.

Ensure all production files are installed through the normal repository installation mechanism, not merely copied into place manually.

Verify that the implementation survives a subsequent normal installation or update.

---

## 5. IMPLEMENT A PROPER MOBILE DATA TOGGLE

Audit the current mobile-data control architecture.

Establish one authoritative mobile-data policy shared by:

- Native radio daemon.
- Network integration.
- Nuxel Settings.
- Quick Settings.
- Top bar.
- Persisted user preferences.

Do not create separate, conflicting mobile-data configuration stores.

### Mobile data ON

The toggle must:

- Persist the enabled preference.
- Initiate or maintain the appropriate cellular session.
- Wait for actual modem and network state.
- Establish valid IP configuration.
- Install appropriate routes and DNS.
- Publish accurate connecting and connected states.

### Mobile data OFF

The toggle must:

- Persist the disabled preference.
- Stop user mobile-data connectivity through the supported session lifecycle.
- Prevent unwanted automatic data reconnection.
- Remove stale cellular routes and session-specific DNS.
- Publish the correct disabled state.

Disabling mobile data must not unnecessarily power off the entire modem or disable otherwise available SMS and voice functionality.

Keep airplane mode and mobile-data policy distinct.

### State model

Distinguish at least:

- Disabled.
- Initializing.
- Searching.
- Registered without data.
- Connecting.
- Connected.
- Disconnecting.
- Unavailable.
- Failed.

The UI must reflect confirmed backend state.

A successful button press or generic modem acknowledgment must not immediately be presented as working cellular internet.

Handle rapid toggle changes, repeated requests, service restarts and temporary failures without creating duplicate sessions or stale state.

---

## 6. COMPLETE QUICK SETTINGS INTEGRATION

Locate the existing Nuxel Quick Settings implementation and integrate the real mobile-data backend.

The mobile-data tile must:

- Display the current enabled preference.
- Reflect actual connection state.
- Toggle mobile data through the authoritative backend.
- Update when Settings changes the same preference.
- Update when the backend state changes.
- Display connecting and unavailable states appropriately.
- Handle errors without freezing the UI.
- Avoid launching duplicate connection requests.

Follow the existing Nuxel visual language.

Reuse existing components and icons where appropriate.

Do not redesign unrelated Quick Settings functionality.

Verify the tile physically on the device.

---

## 7. COMPLETE TOP BAR CELLULAR INDICATORS

Audit the existing Nuxel top bar and status indicator architecture.

Implement or correct the cellular indicator using actual modem-derived state.

Display, where supported:

- SIM availability.
- Signal strength.
- Serving radio technology.
- LTE/4G indicator.
- Mobile-data availability.
- Mobile-data disabled state.
- No-service state.
- Searching state.
- Roaming state.

Keep signal availability separate from active internet connectivity.

A device can have cellular signal while mobile data is disabled.

Likewise, an LTE camping indication does not establish successful internet connectivity.

Never display fabricated signal bars or a permanent LTE label.

Use verified RAT and signal-strength conversions.

Ensure the top bar reacts to backend changes without requiring a UI restart.

Verify:

- Wi-Fi enabled with cellular registered.
- Wi-Fi disabled with cellular active.
- Mobile data disabled.
- Mobile data reconnecting.
- Cellular data connected.
- Service restart and reboot.

Capture screenshots or equivalent UI evidence where practical.

---

## 8. COMPLETE NUXEL MOBILE NETWORK SETTINGS

Inspect and finish the existing mobile-network Settings section.

Expose actual supported functionality through the established Nuxel Settings architecture.

Include, where supported:

- Mobile-data enable/disable.
- SIM status.
- Carrier name.
- Network registration status.
- Current radio technology.
- Signal strength.
- APN configuration.
- Current connection status.
- IPv4 and IPv6 availability.
- Preferred network mode.
- Roaming preference, if implemented and supported.

Unsupported functionality must be clearly identified rather than simulated.

APN changes must use the supported native modem configuration path.

Do not modify protected NV records to implement Settings.

Avoid permanently forcing LTE-only mode when that could interfere with supported telephony behaviour.

Settings, Quick Settings and top bar must remain synchronized through the same authoritative state provider.

Preserve existing Nuxel styling and navigation conventions.

Do not expand into unrelated Settings categories.

---

## 9. NETWORKMANAGER AND CONNECTIVITY INTEGRATION

Audit the actual existing native networking architecture.

Determine whether Nuxel uses:

- ModemManager.
- A native compatibility provider.
- NetworkManager integration.
- A dedicated native cellular network manager.
- A combination of these components.

Preserve the working architecture unless a specific defect requires correction.

Ensure ordinary applications can access cellular internet without manually binding sockets to `rmnet0`.

Verify:

- Cellular route installation.
- Source-based routing.
- Interface-specific routing.
- Route removal after disconnect.
- Dynamic address changes.
- DNS integration.
- Wi-Fi preference.
- Cellular fallback.
- Wi-Fi restoration.
- ZeroTier continuity or reconnection.

Do not mistake the current Wi-Fi resolver configuration for verified cellular DNS integration.

Verify cellular DNS independently.

The previous physical acceptance established IPv6 internet.

Determine whether IPv4 is available, whether the carrier supplies IPv6-only connectivity, and whether additional supported address-family integration is required.

Document limitations accurately.

Do not invent IPv4 addresses or claim dual-stack success without physical evidence.

---

## 10. PHYSICAL LTE ACCEPTANCE

After implementing the required persistence and UI integration, perform a bounded physical acceptance campaign.

### Test A — Existing connectivity

Verify the current LTE baseline before making disruptive changes.

### Test B — Mobile-data toggle

Verify:

- ON establishes cellular internet.
- OFF removes cellular internet.
- ON restores cellular internet.
- Settings and Quick Settings remain synchronized.
- Top bar reflects actual state.
- Voice and SMS availability are not unnecessarily disabled.

### Test C — Cellular-only internet

With an independent management path available:

- Disable Wi-Fi.
- Verify cellular DNS.
- Verify actual HTTPS.
- Verify traffic traverses the cellular interface.
- Record routing and interface counter evidence.
- Restore Wi-Fi and confirm recovery.

### Test D — Wi-Fi/cellular coexistence

Verify ordinary application connectivity during Wi-Fi loss and restoration.

Ensure no stale route or DNS state prevents connectivity.

### Test E — Normal reboot

After verifying the working deployment and recovery arrangements:

- Perform a controlled normal reboot.
- Confirm native CP initialization.
- Confirm SIM readiness.
- Confirm registration.
- Confirm persisted mobile-data preference.
- Confirm automatic cellular connection.
- Confirm real cellular-only internet.
- Confirm Settings state.
- Confirm Quick Settings state.
- Confirm top bar state.
- Confirm management connectivity.

No manual session-start command may be required for the automatic-connect acceptance test.

### Test F — Disabled preference persistence

Verify that the mobile-data disabled preference is persisted correctly and respected by startup logic.

Restore the owner's intended preference after testing.

Record which persistence scenarios were physically tested and which were only verified through automated tests.

Do not perform unnecessary repeated reboots if the remaining budget is limited.

---

## 11. DEFINITIVE LTE STATE DOCUMENT

Create:

`docs/mobile/NUXEL-LTE-STATE.md`

This must be the authoritative technical reference for the current LTE implementation.

Include:

### Executive state

- What physically works.
- What is implemented but unverified.
- Known limitations.
- Current production readiness.
- Exact remaining tasks.

### Hardware and firmware

- Device model.
- Modem model.
- Actual baseband version.
- Relevant kernel interfaces.
- Native modem transport architecture.
- Relevant firmware compatibility boundaries.

### Native CP initialization

- Startup lifecycle.
- Required verified inputs.
- Readiness conditions.
- Systemd dependencies.
- Recovery behaviour.
- Relevant source files and symbols.

### Protocol implementation

- Corrected command semantics.
- Registration decoding.
- Service-domain encoding.
- SIM readiness.
- RAT conversion.
- Response correlation.
- APN configuration.
- PDP context handling.
- IP configuration.

Reference existing detailed protocol documentation rather than unnecessarily duplicating every wire-format table.

### Cellular session lifecycle

- Complete state-machine diagram.
- Connection initiation.
- Registration prerequisites.
- Session activation.
- Disconnect.
- Automatic reconnection.
- Failure recovery.
- Backend state publication.

### Linux networking

- Interface lifecycle.
- Address acquisition.
- Routing.
- Policy routing.
- DNS.
- NetworkManager integration.
- IPv4/IPv6 capabilities.
- Wi-Fi coexistence.

### UI integration

- Authoritative mobile-data preference.
- Settings components.
- Quick Settings components.
- Top bar components.
- D-Bus interfaces or other IPC contracts.
- State synchronization.
- Relevant source files and functions.

### Persistence

- Installed files.
- Services.
- Configuration.
- Startup ordering.
- Reboot behaviour.
- Physical acceptance results.

### Evidence and recovery

- Relevant hardware log locations.
- Test results.
- Build and deployed executable hashes.
- Known-good checkpoint.
- Recovery procedure.
- Remaining issues.

Include exact file paths and function names wherever verified.

Do not include private credentials, subscriber identifiers, certificate contents or sensitive NV data.

---

## 12. DEFINITIVE TELEPHONY STATE DOCUMENT

Create:

`docs/mobile/NUXEL-TELEPHONY-STATE.md`

Perform a comprehensive source and evidence audit of current telephony functionality.

Determine exactly how far Astra and previous agents progressed.

Document:

### Current functionality matrix

- Outgoing calls.
- Incoming calls.
- Answer.
- Reject.
- Hang up.
- Call-state notifications.
- Caller identification.
- Earpiece audio.
- Microphone audio.
- Speaker routing.
- Bluetooth call audio, if supported.
- Dialer integration.
- Call history.
- Cellular data recovery following calls.

Classify every item as:

- Physically verified.
- Implemented but not physically verified.
- Partially implemented.
- Missing.
- Blocked.
- Unsupported.

### Architecture

- Native telephony backend.
- Relevant modem protocol components.
- Call-state machine.
- D-Bus or other IPC contracts.
- Audio subsystem integration.
- Dialer application integration.
- Relevant files and functions.

### Voice technology

Determine whether existing evidence establishes:

- Circuit-switched voice.
- Circuit-switched fallback.
- VoLTE.
- IMS registration.
- Another supported carrier voice mechanism.

Do not claim VoLTE based solely on LTE data connectivity.

### Remaining work

For each incomplete capability, provide:

- Exact current implementation state.
- Evidence supporting the assessment.
- Relevant source locations.
- Known failure or missing component.
- Recommended next implementation step.
- Required physical verification.
- Dependencies on other subsystems.

### Regression concerns

Document how telephony interacts with:

- Corrected service-domain configuration.
- Mobile-data toggle.
- Preferred network mode.
- LTE connectivity.
- Modem initialization.
- Network recovery.

Recover previous physical call evidence where available.

Do not initiate extensive new telephony reverse engineering during this final consolidation round.

Only perform straightforward authorized physical tests if the required recipient and equipment are available.

Leave substantial unfinished telephony implementation to DeepSeek.

---

## 13. DEFINITIVE SMS STATE DOCUMENT

Create:

`docs/mobile/NUXEL-SMS-STATE.md`

Determine the exact current SMS implementation and evidence state.

Document:

### Current functionality matrix

- Outbound SMS.
- Actual outbound delivery.
- Incoming SMS.
- Incoming notifications.
- Message decoding.
- Message encoding.
- Delivery reports.
- Unicode handling.
- Multipart SMS.
- Message persistence.
- Messaging application integration.
- Error handling.
- Retry behaviour.

Classify every item using the same evidence categories as the telephony document.

### Architecture

- Native SMS backend.
- Supported modem protocol paths.
- Message encoding and decoding.
- Relevant command handlers.
- D-Bus or other IPC contracts.
- Messaging application integration.
- Storage architecture.
- Notification integration.

### Current implementation

For each relevant component, identify:

- Exact source path.
- Relevant functions.
- Existing tests.
- Existing physical evidence.
- Missing implementation.
- Known defects.

### Remaining work

Provide DeepSeek with an ordered implementation plan covering only unfinished functionality.

Distinguish successful modem submission from confirmed recipient delivery.

Distinguish synthetic incoming fixtures from real network-delivered SMS.

Document any dependence on IMS, carrier provisioning or network registration.

Do not initiate repeated billable SMS experiments.

Only send messages to explicitly authorized test recipients.

Leave extensive unfinished SMS implementation to DeepSeek.

---

## 14. MASTER DEEPSEEK HANDOVER

Create:

`docs/mobile/DEEPSEEK-STAGE06-HANDOVER.md`

This is the first document DeepSeek must read.

Include:

### Current milestone

State whether persistent LTE internet is physically verified.

State whether mobile-data toggling, Settings, Quick Settings and top bar integration are physically verified.

### Required reading order

1. NUXEL-LTE-STATE.md
2. NUXEL-TELEPHONY-STATE.md
3. NUXEL-SMS-STATE.md
4. Existing Stage 06 acceptance contract
5. S5000AP-IPC41-DATA.md
6. Relevant implementation and test files

### Astra's discoveries

List all important corrected assumptions and their actual evidence.

Explicitly identify historical reports that are superseded or materially incorrect.

### Exact repository state

- Branch.
- Commit.
- Relevant changed files.
- Remaining uncommitted owner changes.
- Deployed executable hashes.
- Installed service configuration.
- Relevant test results.

### Exact physical device state

- CP state.
- SIM state.
- Registration.
- Cellular connectivity.
- Current address-family support.
- Wi-Fi state.
- Management connectivity.
- Pending recovery timers or temporary configuration.

### Remaining Stage 06 acceptance matrix

For every outstanding criterion, specify:

- Status.
- Evidence.
- Relevant files.
- Exact remaining task.
- Dependencies.
- Recommended next action.
- Required acceptance test.

### DeepSeek execution order

Prioritize:

1. Preserve verified LTE functionality.
2. Finish any explicitly outstanding LTE integration.
3. Complete remaining SMS functionality.
4. Complete remaining telephony functionality.
5. Perform final combined regression and persistence acceptance.
6. Complete Stage 06 documentation and checkpoint.

Do not send DeepSeek back into disproven NV provisioning theories or completed modem initialization investigations.

Include a concise ready-to-use DeepSeek continuation prompt at the end of the handover document.

---

## 15. SAFETY AND RECOVERY CONTRACT

Preserve:

- Existing kernel.
- Known-good BOOT image.
- DTB and DTBO.
- Original firmware.
- Device-owned EFS.
- Identity and calibration data.
- Existing authentication mechanisms.
- Management connectivity.
- Previously working hardware.

Keep direct NV provisioning disabled.

Do not:

- Guess NV offsets.
- Modify protected device records.
- Bypass carrier or modem authentication.
- Copy another device's EFS.
- Reflash firmware speculatively.
- Modify kernel or device tree without an established requirement.
- Disable security checks to obtain successful tests.
- Expose sensitive device data in documentation.

Use normal Nuxel operation for this campaign.

TWRP is a recovery mechanism, not the default execution environment.

Follow the established recovery agreement if recovery becomes necessary.

---

## 16. REGRESSION AND FINAL CHECKPOINT

Run the relevant existing test suites and new tests covering:

- CP boot and NV preflight.
- IPC encoding and decoding.
- Service-domain semantics.
- Registration conversion.
- Session lifecycle.
- IP configuration.
- Mobile-data policy.
- Persisted preferences.
- Settings integration.
- Quick Settings integration.
- Top bar state mapping.
- Network lifecycle.
- Native AArch64 build.
- Relevant sanitizers.

Record actual exit statuses.

Do not confuse mock tests with physical acceptance.

Update CHANGELOG.md.

Ensure the normal installation mechanism contains all required production changes.

Commit implementation, tests and documentation.

Preserve unrelated owner changes.

Do not merge or push without authorization.

---

## 17. EXECUTION PRIORITY AND HARD STOP

Execute in this order:

P0 — Preserve the current working LTE baseline and create the initial handover skeleton.

P1 — Complete persistent startup and cellular connection lifecycle.

P2 — Complete mobile-data toggle, Settings, Quick Settings and top bar integration.

P3 — Physically verify cellular-only connectivity and normal reboot persistence.

P4 — Complete the LTE, telephony and SMS state documents.

P5 — Finalize DeepSeek handover, regression evidence and Git checkpoint.

Maintain the documentation incrementally throughout execution.

Do not defer all documentation to P4.

If a substantial unexpected blocker emerges, checkpoint the current implementation, document the precise blocker and terminate rather than launching another open-ended reverse-engineering campaign.

Do not consume the remaining execution budget on unrelated work.

Do not request additional API credits.

Do not start Stage 07.

Do not expand into camera, NFC, fingerprint, sensors, hotspot or other unrelated functionality.

---

## 18. FINAL OUTPUT

Return a concise acceptance matrix containing:

- LTE internet.
- Cellular-only HTTPS.
- Automatic reconnection.
- Reboot persistence.
- Mobile-data toggle.
- Settings integration.
- Quick Settings integration.
- Top bar integration.
- Wi-Fi/cellular transitions.
- Regression tests.
- LTE documentation.
- Telephony documentation.
- SMS documentation.
- DeepSeek handover.
- Final Git checkpoint.

Include the exact paths to all four documentation files.

If all LTE consolidation criteria are verified, output:

**LTE-PERSISTENT-WONQED**

If some criteria remain incomplete, explicitly identify them instead.

Do not output the full Stage 06 completion marker unless every original Stage 06 acceptance criterion, including required SMS and telephony functionality, is verified.

Then TERMINATE.

---

## FINAL MISSION

Turn Astra's demonstrated LTE breakthrough into a persistent, integrated Nuxel smartphone capability.

Make mobile data behave like a normal phone feature.

Make the UI reflect reality.

Make reboot persistence demonstrable.

Make DeepSeek's remaining mission completely unambiguous.

Preserve the breakthrough.

Document everything.

Finish the consolidation.

**LTE AND ALIVE — THE DEEPSEEK PREPPER.**
