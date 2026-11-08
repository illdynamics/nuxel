# NUXEL REPAIR 20 — Real GNSS, GeoClue, permissions and location lifecycle

**Priority:** P2  
**Prerequisite repair IDs:** 09,28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

`GeoClueConnector` exists but there is no proof of GNSS-capable device/firmware, fix, accuracy or per-app permission. A correct clock is not GNSS evidence.

## Inspect these repository paths first

- `services/nuxel-bridge/src/bridge.py`
- `pwa/nuxel-common/geolocation.js`
- `configs/nuxel/capabilities/connectivity-time-audio-buttons.json`
- `pwa/nuxel-apps/settings/settings.js`

## Required engineering work — execute all items

1. Inspect `timedatectl`/RTC/NTP first and explicitly separate time-source diagnosis from GNSS. Inventory modem/location interfaces, GNSS device nodes, GPSD/GeoClue providers, firmware logs and actual chip API.
2. Add location default OFF, per-app consent with clear duration/revoke, provider confidence/source, fix timestamp, horizontal accuracy and timeout behavior.
3. Ensure a request returns no coordinates unless authorized and a valid provider has produced them; do not label IP-derived position as GPS fix.
4. Subscribe to changes/suspend/resume with no background constant polling; location OFF must stop updates and revoke UI disclosure. Protect logs against unrequested persistent tracking.
5. Test negative cases missing modem, denied permission, stale fix, wrong timestamps and provider errors; physically verify a current GNSS fix if vendor stack supports it.

## Acceptance gates (all required for completion)

Location OFF at first boot; setting/on request controls real GeoClue provider; GPS fix only claimed with timestamp/accuracy/satellite or provider proof; permissions and revocation work.

## Evidence to collect

Source-labeled GeoClue/gpsd output, permission receipts, owner outside fix confirmation, power impact and refusal tests.

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
