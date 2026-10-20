# NUXEL REPAIR 24 — Power+VolumeDown authentic live-frame screenshots

**Priority:** P1  
**Prerequisite repair IDs:** 25,28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Wayland snapshot and button FSM code exists but there is no real screenshot from the current compositor proven to match the current display.

## Inspect these repository paths first

- `tools/s10plus/a34/nuxel-wl-snapshot.c`
- `tools/s10plus/a34/nuxel-wl-fb.c`
- `tools/s10plus/a34/nuxel-button-manager.c`
- `services/nuxel-session/systemd/`
- `pwa/nuxel-apps/files/`

## Required engineering work — execute all items

1. Map Power+VolumeDown chord priority over standalone buttons and verify its path into the current Phoc/Wayland capture utility; ensure supported screencopy is bound to *current* output rather than old framebuffer.
2. Implement secure screenshot request with explicit screenshot target under the actual current user's `~/Pictures/Screenshots/`, correct permissions, atomic file creation and timestamp collision handling.
3. Exclude secrets/protected lock-screen content according to existing OS policy and prevent arbitrary app process from screen-capturing without authorization.
4. Ensure capture output is decoded correctly, oriented/rotated correctly, not stale, and user gets bounded completion feedback. Handle missing wlroots protocol and damaged buffers honestly.
5. Run pixel/content comparisons against a screen with deliberate visible timestamp/text change, portrait and landscape, two captures in succession, storage full and input chord bounce.

## Acceptance gates (all required for completion)

One chord captures current visible screen to an actual PNG, differs when screen content changes, and no unintended sleep/volume event escapes; file visible in Files.

## Evidence to collect

Two timestamped actual PNG files and checksums, compositor protocol logs, process status and owner screenshot confirmation.

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
