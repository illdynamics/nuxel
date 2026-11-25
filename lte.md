# NUXEL — LTE OR DIE
## FULL PRODUCTION MOBILE INTERNET — FINAL EXECUTION

**Device:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820 / Shannon S5000AP.

**Branch:** `cs/mob-round35-stage06`

**Latest implementation:** `c52726d3`

**Latest documentation:** `e10a0ab8`

**Physical device:** USB connected and unlocked.

**Architecture:** Native Linux. ZERO Android dependencies.

## ABSOLUTE MISSION

Deliver a complete, production-ready native mobile internet experience comparable to the mobile networking capabilities of a regular Android smartphone.

Not another feasibility report.

Not another documentation-only execution.

Not another host-tested implementation without physical internet connectivity.

The actual handset must have working LTE internet, persistent connectivity, functional UI controls and working internet sharing.

### EXECUTION PRIORITIES

- P0 — Restore genuine LTE internet.
- P1 — Make LTE internet survive normal reboots.
- P2 — Make actual LTE connectivity toggleable through Quick Settings and Settings.
- P3 — Complete NetworkManager integration, top bar and mobile-network statistics.
- P4 — Implement fully functional Wi-Fi hotspot.
- P5 — Implement fully functional USB tethering.
- P6 — Verify automatic reconnection and network transitions.
- P7 — Measure actual LTE internet performance.
- P8 — Commit implementation and hand over to DeepSeek.

SMS, telephony, call audio, IMS, VoLTE, VoWiFi, RCS and phone applications are completely OUT OF SCOPE.

Do not work on them.

---

## 0. ACTION-FIRST EXECUTION CONTRACT

Reuse the extensive existing research and implementation.

Do not spend the initial execution budget on:

- Comprehensive repository audits.
- Repeated vendor disassembly.
- Previously disproven theories.
- Comprehensive host regression campaigns.
- Thousands of fuzz iterations.
- Repeated sanitizer campaigns.
- Regenerating existing documentation.
- Unrelated architectural redesigns.

Perform essential safety checks and focused validation of changed components.

Physical functional acceptance is mandatory.

Prioritize implementation, reversible deployment and actual physical functionality.

Do not request additional paid model credits.

---

## 1. RECOVER THE PREVIOUSLY WORKING LTE CONNECTION

LTE internet has already physically worked on this exact handset.

Previously demonstrated:

- Genuine KPN LTE registration.
- Active CID 1 bearer.
- Global IPv6 address.
- Carrier DNS.
- Cellular-only HTTPS HTTP 200.
- Wi-Fi disabled during acceptance.
- ZeroTier connectivity over cellular.

Successful checkpoints:

- `9dc13efd` — establish verified LTE bearer.
- `24e61763` — automatic data ACTIVE.

Current reported blocker:

- CP ONLINE.
- SIM ready.
- Radio ON.
- PS registration UNKNOWN, raw 7.
- Failure at PS_REGIST_VERIFY.
- No active bearer.
- No cellular IP.

The latest production implementation already provides:

- Persistent mobile-data policy.
- Real bearer-release commands.
- Settings and Quick Settings synchronization.
- Enabled/disabled preference persistence.
- Corrected normal-boot EFS readiness.
- NetworkManager handoff.
- Cellular indicators.

Do not recreate these components.

### Recover the known-good runtime

Read the relevant portions of:

- `docs/mobile/DEEPSEEK-STAGE06-HANDOVER.md`
- `docs/mobile/NUXEL-LTE-STATE.md`
- `docs/mobile/NUXEL-LTE-PRODUCTION-ACCEPTANCE.md`
- Existing successful LTE deployment evidence.

Compare the previously successful runtime against the currently installed runtime.

Focus on:

- Executable identities and hashes.
- Production service arguments.
- Runtime configuration.
- CP startup readiness.
- Initialization ordering.
- Network registration sequence.
- Service-domain configuration.
- Network-selection behavior.
- Data-session lifecycle.
- Changes introduced after the successful LTE breakthrough.

Reproduce the known-good userspace configuration through reversible deployment where appropriate.

Do not revert the entire branch.

Preserve newer working implementation and unrelated owner changes.

Correct the first demonstrated regression.

Do not blindly repeat the unsuccessful radio OFF/ON and automatic-selection sequence.

Do not manufacture successful registration by changing decoder semantics.

Do not modify protected modem data or circumvent carrier authentication.

---

## 2. ESTABLISH ACTUAL LTE INTERNET

Once genuine registration is restored, immediately establish the existing native LTE data session.

Use the configured carrier APN.

Verify physically:

- Actual LTE registration.
- Actual packet-service registration.
- Active cellular bearer.
- Cellular interface.
- Valid IP configuration.
- Correct routes.
- Working DNS.
- Successful HTTPS.
- Cellular interface traffic increments.

Exclude Wi-Fi, USB upstream networking and VPN exit routing from the internet acceptance measurement.

Preserve independent management connectivity.

Verify IPv4 and IPv6 independently.

Where the carrier provides IPv6-only connectivity, investigate supported native IPv4 compatibility mechanisms using existing Linux networking components and actual carrier capabilities.

Do not fabricate IPv4 addresses, gateways or DNS configuration.

Do not claim dual-stack support without evidence.

Immediately checkpoint the successful runtime and implementation.

Record exactly what restored connectivity, if established.

This is the overriding first priority.

---

## 3. PRODUCTION STARTUP AND REBOOT PERSISTENCE

Integrate the successful runtime into the normal Nuxel installation.

Reuse the corrected production CP startup and existing mobile-data lifecycle.

Ensure:

- Correct production executables.
- Correct systemd configuration.
- Correct startup dependencies.
- Validated readiness.
- Automatic registration.
- Automatic bearer activation when enabled.
- Automatic reconnection.
- Persistent mobile-data preference.
- Bounded recovery and retry behavior.
- No temporary scripts.
- No manual terminal commands.
- No uncontrolled restart loops.

Perform the established recovery preflight.

Perform a controlled normal reboot.

Without manual intervention, verify actual LTE internet after reboot.

If connectivity fails after reboot, compare the successful live runtime against the normal startup runtime and correct the demonstrated difference.

The previously successful experimental connection must become reproducible production functionality.

---

## 4. NETWORKMANAGER — COMPLETE NATIVE INTEGRATION

Finish the existing NetworkManager handoff.

Use one authoritative cellular backend.

Do not introduce competing modem owners, DHCP servers, DNS managers or route managers.

Complete and verify:

- Native cellular connection representation.
- Persistent connection configuration.
- APN configuration.
- Bearer lifecycle.
- Cellular interface association.
- IPv4 configuration where supported.
- IPv6 configuration where supported.
- DNS management.
- MTU configuration.
- Route metrics.
- Policy routing where necessary.
- Automatic connection.
- Automatic reconnection.
- Clean disconnect.
- Stale address, route and DNS cleanup.
- Accurate connection-state reporting.
- Wi-Fi coexistence.
- VPN coexistence.
- USB networking coexistence.

Ensure NetworkManager and the native radio backend agree about the actual connection state.

Use the established native ModemManager integration if present and appropriate.

Do not fabricate modem or bearer objects merely to satisfy UI expectations.

---

## 5. SHARED MOBILE NETWORKING BACKEND

Reuse the existing persistent mobile-data policy and native radio bridge.

Settings, Quick Settings, top bar, NetworkManager, hotspot and tethering must consume consistent authoritative state.

Distinguish:

- Mobile-data enabled preference.
- Modem availability.
- SIM readiness.
- Carrier registration.
- Actual radio technology.
- Signal strength.
- Bearer activation.
- IP configuration.
- Internet availability.
- Connecting.
- Disconnecting.
- Failure.
- Hotspot availability and state.
- USB tethering availability and state.

Prevent competing connection operations.

Mobile data OFF must deactivate the cellular bearer and clean up its network configuration.

Mobile data OFF must not unnecessarily disable the modem.

Hotspot and USB tethering must respond correctly when the cellular upstream becomes unavailable.

Never report successful internet sharing when the upstream is unavailable.

---

## 6. QUICK SETTINGS — MOBILE DATA

Finish the existing Quick Settings mobile-data tile.

Do not redesign the existing UI.

Physically verify:

1. LTE internet working.
2. Tap mobile data OFF.
3. Actual cellular bearer disconnects.
4. Cellular routes and DNS are cleaned up.
5. Settings reflects OFF.
6. Tap mobile data ON.
7. Actual cellular bearer reconnects.
8. Cellular internet works again.
9. Settings reflects ON.

The tile must control actual connectivity, not merely change a stored preference.

Represent connecting, disconnected, unavailable and failure states accurately.

Verify state synchronization after normal reboot.

---

## 7. TOP BAR — REAL CELLULAR INDICATOR

Finish the existing top bar implementation.

Display actual available information:

- No SIM.
- No service.
- Searching.
- Registered cellular network.
- Actual signal strength.
- Actual serving radio technology.
- LTE/4G indicator.
- Mobile-data connection state.
- Active hotspot indicator.
- Active USB tethering indicator, where consistent with Nuxel design.

Use existing Nuxel iconography.

Do not fabricate signal bars.

Do not display LTE merely because LTE is the preferred network mode.

Do not confuse registration with active internet connectivity.

Update automatically after backend state changes.

Physically verify the rendered top bar.

---

## 8. MOBILE NETWORK SETTINGS — COMPLETE THE PAGE

Finish the existing mobile-network Settings page using existing Nuxel visual components.

### Mobile data

- Functional mobile-data toggle.
- Connection state.
- Automatic connection preference.
- Persistent configuration.
- Actual connection errors.

### SIM and carrier

- SIM availability.
- SIM readiness.
- Serving operator.
- Home operator where available.
- Registration status.
- Home or roaming status.
- Actual network technology.
- Actual signal strength.
- Available RSRP, RSRQ, RSSI and SINR measurements.

### Network configuration

- APN display and supported configuration.
- Automatic network selection.
- Supported network-mode preferences.
- Data-roaming preference where genuinely supported.

Do not silently enable roaming.

Do not expose unimplemented controls as functional.

### Connection statistics

- Cellular interface.
- IPv4 address.
- IPv6 address.
- DNS.
- Connection duration.
- Received bytes.
- Transmitted bytes.
- Current receive/transmit rates.
- Actual connection state.

Distinguish unavailable measurements from zero values.

Use actual native backend data.

### Internet sharing

Add or finish a dedicated hotspot and tethering section.

Include:

- Wi-Fi hotspot toggle.
- Hotspot name.
- Hotspot password.
- Supported frequency-band selection.
- Connected-device count.
- Hotspot connection status.
- USB tethering toggle.
- USB tethering availability.
- USB tethering connection status.
- Actual upstream availability.
- Meaningful failure messages.

All controls must operate real backend functionality.

No mock controls or placeholder statistics.

---

## 9. WI-FI HOTSPOT — NATIVE LTE INTERNET SHARING

Implement fully functional Wi-Fi hotspot capability using the existing Linux Wi-Fi stack.

Reuse NetworkManager shared-mode functionality where supported and appropriate.

Use existing supported native components such as NetworkManager, nl80211, hostapd and native DHCP/DNS services as required by the established architecture.

Do not introduce Android dependencies.

### Hardware capability

Inspect actual Wi-Fi driver capabilities and supported interface combinations.

Verify AP mode support.

Determine whether simultaneous Wi-Fi station and AP operation is supported.

Do not assume unsupported concurrent operation.

If AP mode requires disconnecting from an existing Wi-Fi network, handle that transition explicitly and restore the previous Wi-Fi state when appropriate.

### Hotspot backend

Implement:

- Actual AP startup.
- Actual AP shutdown.
- Configurable SSID.
- Secure WPA2/WPA3 authentication according to hardware support.
- Strong generated default password.
- Supported frequency-band selection.
- Regulatory-domain compliance.
- DHCP address assignment.
- DNS forwarding.
- IP forwarding.
- Appropriate NAT and routing.
- Firewall isolation.
- Cellular upstream association.
- Connected-client discovery.
- Connected-client count.
- Clean shutdown and network cleanup.
- Upstream loss and recovery handling.

Use the existing system firewall architecture.

Do not flush unrelated firewall rules.

Do not expose management services to hotspot clients.

Do not expose inbound cellular services unnecessarily.

Do not disable existing security controls.

Do not enable an unsecured hotspot by default.

### IPv4 and IPv6 sharing

Support the IP families genuinely available through the cellular connection.

If cellular connectivity is IPv6-only, determine the appropriate supported native mechanism for providing compatible downstream internet access.

Do not assume IPv4 NAT alone can provide internet through an IPv6-only upstream.

Report any remaining IP-family limitations accurately.

### Hotspot physical acceptance

Use an actual consenting external client, preferably the connected development laptop if available.

Verify:

1. Enable hotspot through Settings or Quick Settings.
2. Actual Wi-Fi access point appears.
3. External client connects using the configured credentials.
4. Client receives valid network configuration.
5. Client DNS works.
6. Client HTTPS works.
7. Client traffic demonstrably exits through the cellular interface.
8. Connected-client count updates.
9. Disable hotspot.
10. AP stops and associated network state is cleaned up.

Do not claim hotspot success merely because the SSID appears.

An external client must genuinely access LTE internet through Nuxel.

---

## 10. USB TETHERING — NATIVE LTE INTERNET SHARING

Implement proper USB internet sharing through the existing supported Linux USB gadget infrastructure.

Inspect the established USB gadget configuration and available supported network functions.

Reuse existing ECM, NCM or RNDIS functionality where supported.

Prefer native standards-based USB networking and preserve compatibility with supported host operating systems.

Do not modify the kernel or device tree.

### CRITICAL MANAGEMENT REQUIREMENT

The handset is currently USB connected.

The existing USB networking interface may be the active SSH management path.

Do not destroy or reconfigure the only working management connection.

Preserve the existing management interface where supported.

Prefer sharing through the existing USB network function if this can be implemented without disrupting management.

If a USB gadget reconfiguration is genuinely required, first establish and verify an independent recovery and management path.

Do not perform an operation that could leave the handset unreachable.

### USB tethering backend

Implement:

- USB connection detection.
- Tethering availability detection.
- Actual tethering enable/disable.
- Supported USB network function.
- Downstream network configuration.
- DHCP where appropriate.
- DNS forwarding.
- Cellular upstream routing.
- IP forwarding.
- Appropriate NAT.
- Firewall isolation.
- Clean disable.
- USB unplug handling.
- USB reconnect handling.
- Upstream loss and recovery handling.

Preserve existing USB charging, management and unrelated supported USB functions.

Avoid overlapping downstream subnets.

Do not create conflicting DHCP services.

### USB tethering physical acceptance

Use the connected development computer as an external client where safe.

Verify:

1. LTE internet works on Nuxel.
2. Enable USB tethering.
3. Host detects the supported USB network connection.
4. Host receives valid network configuration.
5. Host DNS works through Nuxel.
6. Host HTTPS works through Nuxel.
7. Actual test traffic exits through Nuxel's cellular interface.
8. Host's own Wi-Fi or Ethernet does not invalidate the measurement.
9. Disable USB tethering.
10. Tethered internet sharing stops.
11. Existing USB management remains functional or is safely restored.

Do not globally disrupt the development computer's networking.

Use controlled interface-specific verification where appropriate.

Verify that USB tethering does not expose privileged management services to unauthorized clients.

---

## 11. HOTSPOT AND TETHERING QUICK SETTINGS

Add or finish the existing internet-sharing Quick Settings controls using the established Nuxel design.

### Hotspot tile

- Actual hotspot ON/OFF.
- Active state.
- Starting and stopping states.
- Connected-device count where appropriate.
- Unavailable or failure state.
- Synchronization with Settings.

### USB tethering tile

- Actual USB tethering ON/OFF.
- USB connected or unavailable state.
- Active sharing state.
- Upstream availability.
- Synchronization with Settings.

Reuse existing tile infrastructure.

Do not implement separate configuration stores.

All controls must use the shared native backend.

---

## 12. NETWORK TRANSITIONS AND COEXISTENCE

Verify actual supported combinations:

- LTE only.
- Wi-Fi only.
- Wi-Fi and LTE.
- LTE and Wi-Fi hotspot.
- LTE and USB tethering.
- LTE with hotspot and USB tethering simultaneously, where supported.
- LTE with ZeroTier.
- LTE with existing VPN functionality, where supported.

Verify:

- Wi-Fi to LTE fallback.
- LTE to Wi-Fi transition.
- Mobile-data OFF while sharing.
- Mobile-data ON after sharing interruption.
- Hotspot startup and shutdown.
- USB tethering startup and shutdown.
- USB unplug and reconnect.
- Cellular upstream loss and recovery.
- No stale routes.
- No stale DNS.
- No duplicate cellular sessions.
- No unintended forwarding.
- No management connectivity loss.

Use separate non-overlapping downstream network ranges.

Ensure the sharing implementation does not accidentally bridge private management networks to external clients.

Preserve existing firewall and VPN policies.

Do not route tethered clients through a VPN unless the configured sharing policy explicitly requires it.

---

## 13. PERSISTENT CONFIGURATION

Persist:

- Mobile-data enabled preference.
- APN configuration.
- Supported network preferences.
- Hotspot SSID.
- Hotspot credentials.
- Supported hotspot frequency-band preference.
- Supported sharing configuration.

Protect hotspot credentials appropriately.

Do not commit passwords or sensitive runtime configuration to Git.

Hotspot and USB tethering must not unexpectedly activate after reboot.

Preserve explicit user preferences while requiring appropriate activation policy for internet sharing.

Verify normal reboot with mobile data enabled.

Verify actual cellular internet automatically returns.

Verify disabled mobile-data preference survives reboot.

Verify hotspot and tethering remain usable after reboot without manual backend setup.

Restore mobile data ON as the final state.

Disable test hotspot and tethering sessions unless the owner explicitly requests them to remain enabled.

---

## 14. REAL LTE SPEED MEASUREMENT

Once actual LTE internet is working and the owner has confirmed sufficient mobile data allowance, run one controlled `speedtest-cli` measurement.

Use the existing installed version or a trusted native distribution package.

Ensure actual traffic uses the cellular interface.

Capture machine-readable results where supported.

Report:

- Carrier.
- Actual radio technology.
- Cellular interface.
- IP family.
- Test server.
- Ping in milliseconds.
- Download Mbps.
- Upload Mbps.
- Bytes transferred.
- Cellular interface counters before and after.
- Actual process exit status.

Do not report Wi-Fi, USB upstream or VPN-exit performance as LTE performance.

Do not fabricate results.

Avoid repeated high-volume speed tests.

Hotspot and USB tethering require actual external-client internet acceptance, but separate high-volume benchmarks are not mandatory.

---

## 15. FINAL PHYSICAL ACCEPTANCE

Do not perform another extensive research or regression campaign.

Perform essential focused checks for changed components and the following physical acceptance gates.

### Native mobile internet

- Genuine LTE registration.
- Actual cellular bearer.
- Valid IP configuration.
- Cellular DNS.
- Cellular-only HTTPS.
- Automatic connection.
- Automatic reconnection.
- Normal reboot persistence.
- Enabled/disabled preference persistence.

### Production integration

- NetworkManager live integration.
- Settings mobile-data OFF/ON.
- Quick Settings mobile-data OFF/ON.
- Settings and Quick Settings synchronization.
- Accurate top bar.
- Actual mobile-network statistics.
- Wi-Fi coexistence.

### Wi-Fi hotspot

- Actual AP startup.
- Secure client authentication.
- Client DHCP.
- Client DNS.
- Client HTTPS through LTE.
- Connected-client reporting.
- Functional Settings and Quick Settings controls.
- Clean shutdown.

### USB tethering

- Actual host network connection.
- Valid client network configuration.
- Client DNS.
- Client HTTPS through LTE.
- Functional Settings and Quick Settings controls.
- USB disconnect/reconnect handling.
- Clean shutdown.
- Management connectivity preserved.

### Final state

- Mobile data ON.
- LTE internet working.
- USB management preserved.
- ZeroTier preserved.
- No unintended active sharing sessions.
- No stale routing or firewall configuration.

Do not claim a physical pass for anything that was only host-tested.

---

## 16. NON-NEGOTIABLE SAFETY

Preserve the working Nuxel installation.

Forbidden:

- Flashing.
- Kernel modifications.
- DTB or DTBO modifications.
- BOOT partition modifications.
- Protected partition writes.
- Modem firmware modifications.
- EFS/NV/identity/calibration modifications.
- Carrier authentication or entitlement bypass.
- Uncontrolled modem reset loops.
- Destructive Git operations.
- Unsecured default hotspot configuration.
- Unnecessary inbound network exposure.
- Disabling existing security controls.
- Loss of independent management connectivity.
- SMS submission.
- Telephone calls.
- IMS or VoLTE implementation.

Use bounded, reversible userspace changes.

Preserve unrelated owner changes.

Do not request additional paid credits.

If the registration blocker cannot be resolved through focused, evidence-backed recovery, stop speculative modem experimentation.

Complete independently achievable integration work and report its actual verification level.

---

## 17. COMMIT AND DEEPSEEK HANDOVER

Commit verified implementation milestones separately.

Suggested checkpoints:

1. LTE connectivity recovery.
2. Production persistence and NetworkManager integration.
3. Mobile-network UI completion.
4. Native Wi-Fi hotspot.
5. Native USB tethering.
6. Physical acceptance and handover.

Do not commit generated binaries, credentials or sensitive runtime information.

Update:

- `docs/mobile/NUXEL-LTE-STATE.md`
- `docs/mobile/NUXEL-LTE-PRODUCTION-ACCEPTANCE.md`
- `docs/mobile/NUXEL-LTE-SPEEDTEST.md`
- `docs/mobile/DEEPSEEK-STAGE06-HANDOVER.md`

Create concise documentation:

- `docs/mobile/NUXEL-INTERNET-SHARING.md`

Document:

- Actual LTE recovery changes.
- Known-good runtime configuration.
- Production startup.
- NetworkManager architecture.
- Mobile-data backend.
- Settings and Quick Settings integration.
- Top bar integration.
- Hotspot architecture.
- USB tethering architecture.
- Routing, DNS and firewall ownership.
- Physical client acceptance.
- Actual hardware limitations.
- Actual LTE benchmark.
- Exact final Git checkpoint.

Preserve the existing SMS and telephony documentation.

Hand over all remaining SMS, ordinary voice, ABOX call audio and IMS work to DeepSeek.

Do not implement them.

Do not merge or push without separate authorization.

---

## 18. COMPLETION CONTRACT

Only declare full mobile internet functionality complete when the required physical acceptance gates genuinely pass.

Final report:

```
NUXEL — FULL MOBILE INTERNET ACCEPTANCE

LTE registration:
LTE internet:
IPv4:
IPv6:
Automatic reconnection:
Reboot persistence:
Mobile-data preference persistence:
NetworkManager:
Settings:
Quick Settings:
Top bar:
Mobile-network statistics:
Wi-Fi coexistence:
Wi-Fi hotspot:
Hotspot external-client internet:
USB tethering:
USB tethering external-client internet:
Simultaneous sharing:
USB management:
ZeroTier:

LTE PERFORMANCE

Carrier:
Technology:
Ping:
Download Mbps:
Upload Mbps:

Final commit:
Remaining limitations:
DeepSeek handover:
```

Populate every field with actual results.

Use PASS, FAIL, BLOCKED, UNSUPPORTED or NOT VERIFIED accurately.

If all required LTE and internet-sharing acceptance gates pass, output:

**LTE AND ALIVE — CONNECTED, PERSISTENT, SHAREABLE, WONQED4REAL.**

This marker applies exclusively to the mobile internet subsystem.

Do not declare full Stage 06 complete.

SMS and telephony remain separate work for DeepSeek.

RESTORE THE INTERNET.
MAKE IT PERSISTENT.
MAKE IT TOGGLEABLE.
MAKE IT SHAREABLE.
PHYSICALLY VERIFY IT.
COMMIT IT.
HAND IT OVER.

ZERO ANDROID DEPENDENCIES.

ACTION FIRST.



## 14. REAL LTE PERFORMANCE — CLI AND BOTH BROWSERS

Once actual LTE internet is restored, perform three independent physical internet speed tests on the Nuxel handset.

These are mandatory functional acceptance gates, subject to sufficient mobile data allowance.

### 14.1 — Cellular-only preflight

Before benchmarking:

- Disable Wi-Fi.
- Exclude USB upstream internet.
- Exclude VPN exit-node routing.
- Preserve USB SSH management.
- Verify actual LTE registration.
- Verify active cellular bearer.
- Verify cellular IP, DNS and routing.
- Record cellular interface traffic counters.
- Confirm sufficient mobile data allowance for all three measurements.

All benchmark traffic must genuinely traverse the native LTE connection.

### 14.2 — Native CLI speed test

Execute `speedtest-cli` directly on the physical Nuxel handset.

Use the existing installation or install it through trusted native package management.

Run:

```bash
speedtest-cli --json
```

Capture:

- Download speed in Mbps.
- Upload speed in Mbps.
- Ping in milliseconds.
- Test server.
- IP family.
- Actual cellular interface.
- Bytes transferred.
- Process exit status.

Verify cellular interface traffic counters before and after the measurement.

### 14.3 — Nuxel Browser speed test

Launch the actual native Nuxel Browser on the physical handset.

Navigate to:

https://www.speedtest.net/run

If that URL redirects or is unavailable, use the official Speedtest homepage and initiate the test using its GO button.

Perform the actual browser-based speed test.

Verify:

- DNS resolution.
- HTTPS connectivity.
- Website rendering.
- JavaScript execution.
- Speedtest initialization.
- Actual download measurement.
- Actual upload measurement.
- Latency measurement.
- Successful result rendering.

Capture a screenshot of the completed result.

Record the measured values.

Do not substitute curl, a headless browser or a desktop browser running on the development computer.

The actual Nuxel Browser must perform the test.

### 14.4 — Firefox speed test

Launch the actual Firefox installation on the physical Nuxel handset.

Navigate to:

https://www.speedtest.net/run

Perform the same browser-based speed test.

Verify actual website functionality, download, upload and latency measurement.

Capture a screenshot of the completed result.

Record the measured values.

Do not substitute another browser.

### 14.5 — Benchmark comparison

Where possible, use the same Speedtest server for all three measurements.

Run measurements sequentially, not simultaneously.

Record signal strength and actual serving radio technology during each measurement where available.

Produce the following comparison table:

| Measurement | Download Mbps | Upload Mbps | Ping ms | Server | Result |
|---|---:|---:|---:|---|---|
| Native speedtest-cli | | | | | |
| Nuxel Browser | | | | | |
| Firefox | | | | | |

Report meaningful differences between the measurements without assuming that all differences are caused by browser performance.

### 14.6 — Evidence

Store actual benchmark evidence under:

`docs/mobile/evidence/lte-speedtest/`

Include:

- CLI JSON result.
- Nuxel Browser result screenshot.
- Firefox result screenshot.
- Cellular routing evidence.
- Cellular interface counters.
- Relevant timestamps.
- Available signal measurements.
- Actual data consumption.

Redact sensitive identifiers and public IP addresses from committed evidence.

Update:

`docs/mobile/NUXEL-LTE-SPEEDTEST.md`

### 14.7 — Failure handling

If CLI internet works but either browser fails, investigate the demonstrated application-networking defect.

Check the existing DNS, proxy, TLS, IPv4/IPv6 compatibility and application networking configuration.

Do not disable browser security controls or certificate verification to manufacture a pass.

If Speedtest itself is incompatible with a browser, distinguish that limitation from an actual LTE networking failure.

Do not fabricate results.

Do not repeatedly consume mobile data through uncontrolled benchmark retries.

### 14.8 — Completion criteria

The mobile internet subsystem must demonstrate:

- Real native CLI internet.
- Real Nuxel Browser internet.
- Real Firefox internet.
- Actual measured LTE download performance.
- Actual measured LTE upload performance.
- Actual measured LTE latency.
- Cellular-only routing evidence.
- Functional graphical internet applications.

Restore the intended networking configuration afterward.

Leave mobile data enabled.

SMS, telephony and VoLTE remain entirely out of scope.
