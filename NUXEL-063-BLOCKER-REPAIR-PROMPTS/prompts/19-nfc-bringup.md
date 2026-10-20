# NUXEL REPAIR 19 — Native S10+ NFC NCI and NDEF reader

**Priority:** P2  
**Prerequisite repair IDs:** 28,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

There is configuration/diagnostic groundwork, not proven NFC controller initialization or tag reads. Owner requests a truthful toggle and actual NDEF support, NFC default OFF.

## Inspect these repository paths first

- `configs/nuxel/nfc/nfc.json`
- `tools/s10plus/a33/nuxel-nfc-diag.sh`
- `pwa/nuxel-home/js/qs.js`
- `docs/beta-finalization/manual-proof/12-nfc.md`

## Required engineering work — execute all items

1. Inspect `dmesg`, device-tree/driver bindings, I2C/SPI nodes, firmware loading, NCI device nodes and Linux NFC userspace availability. Confirm controller revision from actual system, not another S10 model.
2. Determine reversible power/enable control with proper permissions and default-off service policy. Never implement UI-only toggles.
3. Where Linux NCI driver works, add service with explicit statuses unavailable/disabled/enabling/ready/tag-detected/error and minimal NDEF read-only parsing; require per-app permission before sharing tag content.
4. Handle malformed/hostile NDEF payloads, rapid tag removal and suspend/resume. Do not claim payments or secure-element emulation.
5. Test with user-supplied benign physical NDEF tag and collect controller state before/after OFF/ON; if driver absent, report exact device ID/missing kernel capability.

## Acceptance gates (all required for completion)

Physical NFC controller toggles and harmless tag is read as NDEF with owner confirmation; otherwise explicitly unavailable with blocker and no fake ON indicator.

## Evidence to collect

Kernel binding/firmware evidence, NCI state, safe test-tag read trace and permission audit.

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
