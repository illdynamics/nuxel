# NUXEL REPAIR 10 — Full NetworkManager-backed Wi-Fi Settings

**Priority:** P0  
**Prerequisite repair IDs:** 09,28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Existing `NetworkWifiScan/Connect/Disconnect/SetEnabled` D-Bus methods and a Wi-Fi tab cover only a subset of requested flows; saved networks, forget, hidden SSIDs and connection details are missing/incomplete.

## Inspect these repository paths first

- `pwa/nuxel-apps/settings/wifi-settings.js`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-apps/settings/index.html`
- `services/nuxel-bridge/src/bridge.py`
- `services/nuxel-bridge/polkit/50-nuxel-bridge-network.rules`

## Required engineering work — execute all items

1. Extend existing `NetworkManagerConnector`, not a competing manager. Enumerate active + saved connections, AP BSSID/SSID/signal/security, grouped SSIDs, connection state/error, IPv4/IPv6/gateway/DNS and autoconnect flags.
2. Add per-app-scoped, validated D-Bus methods for forget/deactivate, connect existing profile, hidden SSID/profile creation, connection details; ensure access control via existing bridge permissions and polkit. Return structured errors rather than subprocess stderr.
3. Use NM secure settings agent/keyring mechanism; never log, echo, query-string, or store passphrases in localStorage. Treat WPA3 capability honestly and never silently downgrade authentication.
4. Finish Settings UI with scan/refresh, password prompt, connect/disconnect, saved/forget, hidden option, retry, progress and clear Wi-Fi-disabled/unavailable states. No credentials embedded in DOM logs.
5. Add fake D-Bus/NM integration tests for 401/access-denied, failed auth, wrong password, SSID collision, 2.4/5 GHz, hidden network, disconnect/reconnect, and redaction tests; live-test against an authorized AP.

## Acceptance gates (all required for completion)

Users can manage real network lifecycle in Settings, including saved/hidden entries and truthful IP/DNS details; no duplicate supplicant; password safe; reconnect survives reboot.

## Evidence to collect

NM connection metadata without secrets, UI screenshots, scan/connect/forget logs with redaction, saved profile lifecycle and live owner PASS/FAIL.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.
