# NUXEL REPAIR 11 — End-to-end IP, DNS, TLS, browser connectivity

**Priority:** P0  
**Prerequisite repair IDs:** 09,10,12  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Connected Wi-Fi does not prove internet. There is no S10+ receipt covering association, DHCP, route, DNS, HTTPS validation and actual browser rendering.

## Inspect these repository paths first

- `services/nuxel-bridge/src/bridge.py`
- `pwa/nuxel-apps/settings/wifi-settings.js`
- `pwa/nuxel-home/js/status-bar.js`
- `pwa/nuxel-apps/browser/`
- `tools/s10plus/a33/nuxel-wifi-diag.sh`

## Required engineering work — execute all items

1. Add an explicit bounded connectivity diagnostic with independent phases: carrier/association/auth, IPv4/IPv6, default routes, local gateway, DNS resolution, TCP/HTTPS TLS certificate verification, HTTP result and Browser navigation.
2. Use safe fixed known endpoints or user-configured probes with reasonable timeouts and no captive-portal credentials; avoid declaring success from a DNS cache or a 302 redirect without interpreting it.
3. Separate status enums radio unavailable / disconnected / authenticating / local only / captive portal / internet verified / certificate failure. Ensure UI refreshes on NM events rather than aggressive polling.
4. Distinguish Wi-Fi connection through NM from USB tether internet, to avoid false success when MacBook supplies network.
5. Write mocked failure-stage tests; capture real on-phone DNS and TLS output for one public HTTPS site and verify WebKit loads it normally.

## Acceptance gates (all required for completion)

After a real AP join, valid gateway/DNS/HTTPS and Browser page load succeed; breaking DNS/TLS produces accurate diagnostics; no false internet status from USB connectivity.

## Evidence to collect

Network device/routes (redacted), resolver result, TLS certificate chain verification, HTTP response and actual Browser screenshot.

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
