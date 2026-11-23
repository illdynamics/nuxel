# 07 — DEEPSEEK PRO THINKING: SMS, Calls, IMS/VoLTE, Nuxel UI as Independent Deliverables

Read `00_MASTER_SAFETY_AND_TRUTH.md`. **First require real LTE data PASS from round 06; do not collapse all telephony features into one “modem working” badge.** Freeze DTB/DTBO and BOOT except clearly approved regression repair. Use consented normal tests only; no emergency dialing.

## SMS gate

Research proven same-generation Samsung radio protocol/API for SMS send, receive, delivery callbacks, encoding, multipart, queue retry, dual-SIM if truly relevant, storage and receive event dispatch. Implement only source-validated commands, never invent SIPC request IDs from other generations. Label any offline/mock local message app as offline; mock local storage is not radio SMS. With consent of two actual non-premium non-emergency test numbers, validate bidirectional SMS and correct application updates using redacted payloads. Keep logs free of phone numbers and message bodies.

## Voice gate

Study incoming/outgoing call control over actual radio stack and two-way audio path (Exynos ABOX, ALSA/UCM, PipeWire and SCO/Bluetooth where proven) independent of microphone/audio recording permissions. Use consenting normal non-emergency number only and no automatic dialing loops. Verify outgoing dial/ring/connect/hangup; incoming ring/answer/hangup; real uplink/downlink intelligibility; routing earpiece/speaker if supported; call audio teardown on radio loss. Negative test airplane/no-SIM/no-service. Calls might require IMS/VoLTE and/or legacy circuit-switched availability; don't conflate data connectivity with voice support.

## IMS / VoLTE gate

Treat IMS as a distinct challenging subsystem requiring carrier provisioned entitlement and a compatible vendor or FOSS stack, secure native signaling and audio path. Research whether stock Samsung IMS components can lawfully run in isolated supported runtime; pin versions and identify independently necessary components. Do not claim support because the modem is LTE registered or VoLTE toggle exists. If carrier policy or proprietary vendor binaries prevent real IMS, report `IMS_BLOCKED_PROVISIONING`, `IMS_BLOCKED_VENDOR_STACK`, or `IMS_UNSUPPORTED`, not failure of basic LTE.

## UI and permissions

Provide honest modem/SIM/network status in Nuxel Settings, quick settings, status bar, dialer, contacts and messages; request user confirmation for chargeable data/call/SMS state changes; secure DBus access and local app permissions; ensure no false signal bars or enabled buttons. No subscriptions, private identity data or SS7 diagnostics in logs. Preserve desktop/mobile shell, Wi-Fi, audio, cameras, sensors, NFC, GNSS and TWRP bootability.

## Exit receipts

Generate `reports/S5000AP-07-TELEPHONY.md` containing three **independent** PASS/BLOCKED/FAIL entries (SMS, ordinary voice, IMS) plus redacted physical evidence, exact carrier preconditions, licensing and limitations. Commit only genuinely supported functionality and add negative tests. Do not promise that a few thinking rounds can replace missing secure vendor IMS interoperability.

### Flash subjobs

A. SMS parser/state tests. B. Dialer audio permissions and call event tests. C. IMS feasibility research matrix. D. UI offline/no-SIM negative fixtures. Owner approves every real call/SMS trial.
