# 🐧 PWNAGE 29000 — NUXEL TOTAL HARDWARE UBERFIXER

**Mission:** Fix and integrate USB-C-to-HDMI display output, Bluetooth, GPS/GNSS and audio on Nuxel, running on the Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820).

## 1. Non-negotiable rules

You are working on a real, partially functional Linux phone port. Diagnose the actual system; do not create a cosmetic simulation.

- Inspect the repository, current branch, working-tree diff, hardware providers, Nuxel bridge, Settings application, Quick Settings, service units and test suites before editing.
- Check for active coding agents, deployment scripts, transactions and serial-console locks. If another PWNAGE task or physical-device deployment is active, perform read-only investigation only until it is safe to proceed.
- Preserve the existing serial Live Console and recovery mechanism. Never allow two processes to write to the phone's serial transport simultaneously.
- Preserve the known-working Wi-Fi/internet, DNS/TLS, browser, shell navigation, lockscreen, charging indicator and existing applications.
- **Do not flash a kernel, boot image, modem, partition or firmware. Do not wipe user data.** Keep the existing Samsung-derived Linux 4.14 baseline.
- Never fake a Bluetooth adapter, GPS fix, audio device, connected monitor or successful hardware operation.
- Clearly distinguish source-code changes, automated test results and tests performed on the physical phone.
- Make small, reversible changes. Record the baseline and provide rollback instructions.

## 2. USB-C to HDMI: Mirror or Desktop

Implement the closest technically supportable equivalent to the external-display experience the user wants from GrapheneOS.

When a compatible USB-C-to-HDMI adapter and monitor are connected:

1. Detect the actual external display and report connection/disconnection.
2. Display its connector name, supported modes, preferred resolution and refresh rate when available.
3. Present a display chooser with **Mirror** and **Desktop** options when those modes are genuinely supported.
4. **Mirror mode:** duplicate the phone's visible interface on the external display.
5. **Desktop mode:** provide an independent external workspace and Nuxel shell, rather than merely stretching or duplicating the phone screen.
6. Support hot-unplug and reconnect without crashing the shell, losing the phone display or disrupting Live Console recovery.
7. Show a useful error when the external display or a particular mode is unavailable.

### Investigate the entire hardware path

The S10+ supports wired external display output in supported configurations. However, that does not prove Nuxel's current Linux port has the required support.

Inspect:

- USB-C connector and DisplayPort Alt Mode negotiation.
- USB-C mux, role switching, extcon and hotplug events.
- Running kernel configuration and available Type-C/Alt Mode drivers.
- DRM/KMS devices, connector state, supported modes and display bridges.
- Relevant device-tree configuration, kernel logs and firmware dependencies.
- The current Wayland compositor, expected to be Phoc unless the repository proves otherwise.
- Compositor output discovery, mirroring support, independent outputs and workspace management.

Use the actual available interfaces; do not assume every device exposes the same sysfs paths or connector names.

**Important:** If the display is not detected below userspace, identify the exact missing kernel, driver, mux, Alt Mode or board-support component. Document a separate, scoped future driver/kernel task if required. Do not fake monitor detection or claim that a UI change fixed a missing driver.

Do not invent compositor APIs. Use the existing stack and dependencies, and implement only modes that can really work.

## 3. Bluetooth: fix `UNCHANGED: NO_ADAPTER`

The screenshot shows the Bluetooth Quick Setting reporting:

`BLUETOOTH UNCHANGED: NO_ADAPTER`

Trace this message to its real source and fix the underlying cause.

Investigate:

- Physical controller enumeration and relevant USB/platform devices.
- Kernel driver binding, firmware loading and kernel logs.
- rfkill and controller power state.
- BlueZ installation, daemon state, D-Bus service availability and permissions.
- Nuxel bridge/provider registration, API contracts and error propagation.

Use available diagnostics such as `rfkill list`, `bluetoothctl list`, `bluetoothctl show`, `btmgmt info`, systemd/journal logs and D-Bus inspection when those tools are installed.

Do not assume a missing command means the hardware is absent. Do not hard-code a chipset or firmware path without evidence.

Implement the following:

- A Bluetooth Settings page showing the real controller name/address when available, service state, power state, paired devices, scanning/pairing status and useful errors.
- A Quick Setting that requests a real enable/disable operation and updates only after observing the authoritative state.
- Scanning, pairing, connecting and disconnecting where supported.
- Clear states for unavailable hardware, unavailable service, blocked adapter, turning on/off, on, off and operation failure.
- Retry/refresh actions that do not leave the UI permanently busy.

If hardware is detected but the provider is broken, repair the provider integration. If the controller or required firmware is genuinely unavailable, report the evidence and blocker rather than changing the message to pretend it works.

## 4. GPS/GNSS: real location, not a map pin

Investigate the actual GNSS implementation in this phone port. Do not assume it is a generic USB GPS device.

Inspect available device nodes, sysfs, kernel drivers and logs, firmware, device-tree configuration, candidate serial/UART or IIO interfaces where supported, vendor services, provider APIs and permissions.

Create a first-class **Location / GPS** page in Settings showing:

- Detected provider and hardware/service information.
- Provider availability and enabled/disabled state.
- Whether it is searching, has no fix, has a stale fix or has a fresh fix.
- Latitude/longitude only when supported by genuine location data.
- Last-fix timestamp and accuracy when available.
- Satellite and signal-quality information if exposed by the actual provider.
- Permission/privacy status, diagnostics and retry/refresh controls.

Wire the Location Quick Setting to the actual supported provider or power policy.

Keep these states distinct:

- Provider unavailable.
- Location disabled.
- Searching for satellites.
- No fix.
- Stale last-known fix.
- Fresh GNSS fix.

Never treat a geocoding result, manually added map pin, cached coordinate or hard-coded Eindhoven location as a live GPS fix. Never invent coordinates.

Where supported, publish location through one canonical provider API so Maps and other Nuxel applications consume the same real data.

Test outside with a reasonable acquisition window. Record the conditions and duration. An indoor failure to acquire satellites is not, by itself, proof of a broken driver.

## 5. Audio: replace the Settings dash with real information

The current Settings screen displays a dash for sound. Trace why device discovery or audio-provider reporting is missing.

Inspect:

- `/proc/asound/cards` and `/proc/asound/pcm`.
- `aplay -l`, `arecord -l` and `amixer`, when available.
- The actual active audio server using `pactl info`, `wpctl status` or the relevant system tools.
- Kernel logs for codec, DSP, firmware, DAI and sound-card failures.
- UCM profiles, mixer routes and device-specific audio configuration where used.
- The Nuxel bridge/API that reports audio devices and state.

Do not assume an empty PulseAudio/PipeWire listing proves there is no kernel audio hardware. Do not install a new audio server blindly if the current image uses another working or partially working stack.

Implement an **Audio** Settings page showing:

- Actual detected sound card/device names.
- Playback and capture endpoints.
- Active output/input route.
- Audio service state.
- Volume and mute state.
- Supported controls and meaningful errors.

Make volume and mute controls affect the real audio backend. If the image uses a lower-level ALSA path, integrate with that existing architecture rather than fabricating a default device.

Verify a local speaker test tone, volume changes, mute/unmute and microphone capture where supported. Keep recordings local, short and non-sensitive. Report the real result of each test.

Distinguish no hardware, driver present but route unavailable, audio service unavailable, muted audio and a working route.

## 6. Settings and Quick Settings: one source of truth

Add or repair these first-class Settings sections:

1. **Bluetooth**
2. **Location / GPS**
3. **Audio**
4. **Displays**

The Bluetooth, GPS and Audio pages must show the actual device or provider discovered for that component, plus its current status. The Displays page must show actual output connectors and external-display capabilities.

Do not maintain one set of fake booleans in Quick Settings and a separate set in Settings. Both must consume the same authoritative provider/state source.

Use the existing Nuxel architecture and dependencies. Trace the flow:

`hardware/kernel → system service/provider → Nuxel bridge/API → Settings + Quick Settings + applications`

Fix missing provider registration, service activation, D-Bus access, permissions or API contracts at the appropriate layer.

Use domain-specific state models. Bluetooth power, GPS fix quality, audio routing and display hotplug are not interchangeable.

Requirements:

- Real operations, followed by confirmation from the underlying service.
- Pending states, timeouts, operation failures and device removal handled explicitly.
- Useful error messages and retry actions.
- No indefinite loading indicators.
- No unnecessary busy polling.
- No shell-command injection or unbounded subprocesses.
- No dependence on internet connectivity for local hardware settings.
- No public-network exposure of diagnostic services.
- Touch-friendly controls and clear labels on the phone display.

## 7. Mandatory execution sequence

### Phase 0 — safe audit

Record the Git branch, working-tree diff, existing implementations, relevant services, current tests and available hardware evidence. Check for active agents/deployments and serial ownership. Create a table of each symptom, evidence, likely cause and confirming test.

Do not deploy until there is no competing physical-device transaction.

### Phase 1 — shared provider architecture

Trace Bluetooth, GPS and Audio from hardware/service through the bridge into both Settings and Quick Settings. Fix broken provider registration and state reporting first. Add unit tests for missing services, unavailable devices and operation failures.

### Phase 2 — Bluetooth

Fix the real `NO_ADAPTER` cause where the current hardware/software supports it. Add the Settings page and wire the Quick Setting to actual controller operations. Verify real adapter enumeration and state changes.

### Phase 3 — GPS

Connect the real GNSS provider to the canonical location API. Implement truthful state reporting and Settings diagnostics. Verify a fresh fix outdoors if the device is accessible.

### Phase 4 — Audio

Detect actual hardware and routes, wire volume/mute controls and verify supported playback/capture paths.

### Phase 5 — external display

First prove that the physical connection, Alt Mode path and display connector are detected. Then implement hotplug handling, Mirror and genuine Desktop mode to the extent supported by the kernel and compositor.

If the kernel/driver path is missing, stop at a precise diagnosis and safe follow-up plan rather than making unrelated risky changes.

### Phase 6 — integration and regression testing

Verify that Settings and Quick Settings agree, that device removal and service restart are handled, and that all known-working features remain intact.

## 8. Acceptance tests — do not skip

### Bluetooth
- [ ] Real controller detected, or an evidence-backed reason it is not.
- [ ] Quick Setting changes actual controller state where supported.
- [ ] No `NO_ADAPTER` false negative when a usable controller exists.
- [ ] Settings displays controller, provider/service and actionable errors.
- [ ] Scanning and pairing work where supported.

### GPS
- [ ] Settings identifies the real provider and hardware/service path.
- [ ] Quick Setting distinguishes disabled, unavailable, searching, no fix, stale and fresh fix.
- [ ] Live coordinates appear only after a genuine fix.
- [ ] Search results and manually added pins cannot masquerade as GPS fixes.
- [ ] Outdoor acquisition test and conditions are documented.

### Audio
- [ ] Settings reports actual hardware/routes or a precise explanation of why they are unavailable.
- [ ] Volume and mute operate on the real backend.
- [ ] Local speaker playback tested where supported.
- [ ] Microphone capture tested where supported and safe.
- [ ] No unexplained dash remains where device/status details belong.

### USB-C HDMI
- [ ] Real hotplug and unplug events detected.
- [ ] Actual connector, supported modes and relevant kernel/compositor evidence recorded.
- [ ] Mirror mode tested on a physical monitor if supported.
- [ ] Desktop mode tested as a genuinely independent workspace if supported.
- [ ] Disconnect returns cleanly to phone-only operation.
- [ ] Unsupported modes show a real blocker rather than false success.

### Regressions
- [ ] Tests cover provider missing, service down, stale data, timeout, failure and device removal.
- [ ] Existing Wi-Fi, browser, shell navigation, lockscreen, charging indicator and serial Live Console still work.
- [ ] No kernel/partition flashing or data wiping.
- [ ] Exact commands, test outcomes and remaining limitations are documented.

## 9. Final deliverables

Provide:

1. Root-cause analysis for Bluetooth `NO_ADAPTER`, GPS state, Audio dash and HDMI/display detection.
2. Files changed and explanation of each change.
3. Diagnostics collected and what they prove.
4. Exact tests and pass/fail results.
5. A capability matrix showing hardware detection, provider status, UI integration, physical testing and blockers for Bluetooth, GPS, Audio and USB-C display.
6. Operator instructions to test each feature.
7. Rollback steps and a scoped follow-up for any genuinely missing kernel/driver capability.

**Definition of done:** Settings and Quick Settings reflect real shared hardware state; supported controls operate real services; tests pass; the known-good phone remains recoverable; and every physical-hardware claim is backed by an actual test.

Start with Phase 0. Audit first, preserve recovery, and proceed in small, testable phases. Do not claim full success when the phone or external monitor has not actually been tested.

