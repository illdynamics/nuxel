# NUXEL — LTE PRODUCTION FINISHER
## FINISH THE EXISTING WORK. NO DISTRACTIONS.

Branch: `cs/mob-round35-stage06`

Last checkpoint: `56b35c9d5b7a`

Target: Samsung Galaxy S10+ / beyond2lte / Shannon S5000AP.

Native Linux. Zero Android dependencies.

## MISSION

Finish the existing mobile networking implementation and physically deliver:

1. Working LTE internet.
2. Automatic LTE connectivity after normal reboot.
3. Functional mobile-data ON/OFF in Quick Settings.
4. Accurate cellular signal and LTE icon in the top bar.
5. Updated, functional mobile-network Settings page.
6. Correct NetworkManager integration.
7. Persistent mobile-data preference.
8. Updated DeepSeek handover.

SMS, telephony, call audio, IMS and VoLTE are entirely OUT OF SCOPE.

Do not send messages or initiate calls.

## 1. FINISH THE EXISTING UNCOMMITTED IMPLEMENTATION

Start with `git status` and inspect the existing diffs.

The previous execution left substantial implementation work in:

- `pwa/nuxel-apps/settings/index.html`
- `pwa/nuxel-apps/settings/driver-diagnostics.js`
- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-home/js/status-bar.js`
- `services/nuxel-bridge/src/api.py`
- `services/nuxel-bridge/src/bridge.py`
- `services/nuxel-bridge/src/native_radio.py`
- `tools/s10plus/s5000ap-05/src/mobile_data.c`
- `tools/s10plus/s5000ap-05/src/mobile_data.h`
- `tools/s10plus/s5000ap-05/src/radiod.c`
- Existing build, installation, systemd and test changes.

Do not discard or unnecessarily rewrite this work.

Identify which changes belong to the current implementation and preserve unrelated owner modifications.

Finish the existing implementation, build it, run focused tests and deploy it reversibly.

Do not commit generated test binaries.

Do not start another comprehensive repository audit.

## 2. RESTORE THE PREVIOUSLY WORKING LTE CONNECTION

LTE internet has already physically worked on this exact handset.

Relevant successful checkpoints:

- `9dc13efd` — establish verified LTE bearer.
- `24e61763` — automatic data ACTIVE.

The latest production CP startup correction is installed and committed.

Current blocker:

- CP ONLINE.
- SIM ready.
- Radio enabled.
- PS registration UNKNOWN, raw 7.
- Session fails at PS_REGIST_VERIFY.

Read only the relevant sections of:

- `docs/mobile/NUXEL-LTE-STATE.md`
- `docs/mobile/DEEPSEEK-STAGE06-HANDOVER.md`
- `docs/mobile/NUXEL-LTE-PRODUCTION-ACCEPTANCE.md`
- `docs/mobile/evidence/finalizer-20261125/registration-events.json`
- `docs/mobile/evidence/finalizer-20261125/final-state.json`

Compare the previously successful runtime against the current installed runtime.

Prioritize executable identity, service configuration, initialization ordering, configuration differences and session lifecycle regressions.

Preserve the newly corrected production CP startup path.

Do not reverse-engineer LTE from scratch.

Do not blindly repeat the already unsuccessful radio OFF/ON and automatic-selection operations.

Correct demonstrated regressions using bounded, reversible userspace changes.

Verify genuine carrier registration, active bearer, cellular IP, DNS and HTTPS through the cellular interface.

If registration remains blocked after a focused investigation, preserve the exact blocker and continue all independently achievable UI and NetworkManager work.

## 3. NETWORKMANAGER

Finish the existing native cellular integration.

Ensure:

- Actual cellular interface and bearer association.
- Correct IPv4/IPv6 configuration according to available carrier support.
- Carrier DNS and route management.
- Automatic connection and reconnection.
- Clean disconnect.
- Removal of stale cellular addresses, routes and DNS.
- Correct Wi-Fi coexistence.
- Accurate NetworkManager connection status.

Reuse the established native architecture.

Do not introduce competing modem owners or route managers.

## 4. MOBILE-DATA BACKEND

Finish the existing `mobile_data.c`, `mobile_data.h` and native radio bridge implementation.

Use one authoritative state and policy source for Settings, Quick Settings, top bar and NetworkManager.

Mobile data ON must establish the actual cellular connection.

Mobile data OFF must deactivate the actual data bearer and clean up network configuration.

Mobile data OFF must not unnecessarily disable the modem itself.

Persist the user's preference.

Distinguish:

- Enabled preference.
- Connecting.
- Registered.
- Connected.
- Disconnected.
- No service.
- Failure.

Prevent competing connection requests.

Never report a successful connection based solely on the enabled preference.

## 5. QUICK SETTINGS

Finish the existing mobile-data tile in `qs.js`.

Make it genuinely functional.

Tapping must enable or disable mobile data through the native backend.

The tile must reflect actual backend state and synchronize automatically with Settings.

Represent connecting, connected, disconnected and unavailable states accurately.

Verify the actual rendered tile on the handset.

## 6. TOP BAR

Finish the existing cellular indicator in `status-bar.js`.

Display:

- Actual cellular signal strength.
- Actual network technology.
- No service or no SIM when appropriate.
- Mobile-data availability and connection state.

Use existing Nuxel iconography.

Do not fabricate signal bars or show an LTE indicator based solely on preferred network mode.

Keep cellular registration distinct from active internet connectivity.

Update automatically following backend state changes.

## 7. SETTINGS

Finish the existing mobile-network Settings page.

Use existing Nuxel styling.

Include:

- Functional mobile-data toggle.
- Actual operator.
- SIM availability.
- Registration status.
- Actual network technology.
- Signal strength.
- APN information.
- Connection status.
- Available IP information.
- Meaningful connection errors.

All controls and displayed values must use the real native backend.

Settings and Quick Settings must remain synchronized.

Do not leave placeholder or mock controls.

## 8. REBOOT PERSISTENCE

Install the verified implementation through the normal production installation path.

No temporary scripts or manually launched processes may be required.

Verify correct service ordering and dependencies.

After the existing recovery preflight passes, perform a controlled normal reboot with mobile data enabled.

Verify automatic startup, registration, bearer activation, IP configuration, DNS and cellular-only HTTPS.

Verify Settings, Quick Settings and top bar state.

Then test mobile data OFF and ON through the actual UI.

Verify that the disabled preference also survives reboot when safe to perform the second controlled reboot.

Restore the intended final preference.

## 9. PHYSICAL ACCEPTANCE

Verify independently:

- LTE registration.
- Cellular-only HTTPS with Wi-Fi excluded.
- Automatic LTE connection after reboot.
- Quick Settings OFF and ON.
- Settings OFF and ON.
- Settings/Quick Settings synchronization.
- Accurate top bar signal and LTE status.
- NetworkManager integration.
- Wi-Fi coexistence.
- USB SSH and ZeroTier preservation.

Run one `speedtest-cli` measurement if cellular internet is working and the owner has confirmed sufficient mobile data allowance.

Report actual download Mbps, upload Mbps and latency.

Do not invent results if registration remains blocked.

Run focused regression tests for changed components. Run the relevant broader suite after implementation if resources permit.

## 10. SAFETY

Preserve existing recovery agreements.

No kernel, DTB, DTBO, BOOT, firmware, protected partition, EFS, NV, identity or calibration modifications.

No flashing.

No carrier authentication bypass.

No uncontrolled modem restart loops.

Maintain independent USB or serial management connectivity.

Use reversible userspace deployment and essential pre-deployment checks.

Do not request additional paid credits.

## 11. COMMIT AND HAND OVER

Commit completed implementation changes separately from documentation.

Update:

- `docs/mobile/NUXEL-LTE-STATE.md`
- `docs/mobile/NUXEL-LTE-PRODUCTION-ACCEPTANCE.md`
- `docs/mobile/NUXEL-LTE-SPEEDTEST.md`
- `docs/mobile/DEEPSEEK-STAGE06-HANDOVER.md`

Preserve the existing SMS and telephony documentation.

Add a concise handover for DeepSeek covering:

- Current LTE implementation and physical state.
- Production installation.
- NetworkManager integration.
- Mobile-data backend and UI interfaces.
- Verified reboot behavior.
- Remaining LTE blockers, if any.
- Existing SMS backend and outstanding physical tests.
- Existing call-control backend.
- Outstanding ABOX VoiceCall audio integration.
- Existing IMS limitations.

Do not perform SMS or telephony work.

Do not regenerate existing extensive documentation.

Do not merge or push unless separately authorized.

## TERMINATION

If all LTE acceptance criteria pass, output:

LTE AND ALIVE — PERSISTENTLY WONQED.

If LTE registration remains blocked, complete and commit the independently achievable UI, NetworkManager and lifecycle work, report its actual verification level and hand over the precise registration blocker.

Do not declare full Stage 06 complete.

Do not spend the entire execution documenting instead of implementing.

FINISH THE EXISTING CODE.
MAKE THE TOGGLES WORK.
MAKE THE ICON REAL.
MAKE LTE PERSIST.
HAND OVER.
STOP.
