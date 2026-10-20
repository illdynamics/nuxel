# NUXEL REPAIR 17 — System-wide Normal/Vibrate/Silent sound behavior

**Priority:** P1  
**Prerequisite repair IDs:** 15,16,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Existing sound-mode UI/settings presence has not been proven to enforce alerts and haptics end-to-end. Do not conflate an existing notification bell icon with sound mode, and do not imply telephony ringtone support works.

## Inspect these repository paths first

- `configs/nuxel/audio/audio.json`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-home/js/status-bar.js`
- `services/nuxel-notifications/`
- `services/nuxel-haptics/`

## Required engineering work — execute all items

1. Trace notification event → category/policy → audio playback/haptic controller and audit current stored sound setting. Define Normal, Vibrate, Silent policies with separate media vs notifications; preserve exceptions only when explicitly allowed.
2. Use a single daemon/policy source for mode state, durable storage and D-Bus change notifications. Prevent duplicate vibrator controllers and never mute media implicitly without documented preference.
3. Integrate Settings, Quick Settings and status bar with real readback: one source of truth and a distinct sound-mode indicator when bell already signals notifications.
4. Handle mode changes while alerts are queued, app restarts, reboots and speaker-hardware unavailability. In unavailable hardware cases report mode policy applied but audio path blocked, not 'audible'.
5. Write test matrix across all 3 modes × alerts/media/haptics × restart; conduct owner haptic/audible validation once task 15 succeeds.

## Acceptance gates (all required for completion)

Mode selection survives restart, alert sound/haptic obey policy, media behavior documented, status icon correct, no contradictory UI states.

## Evidence to collect

Event policy traces, Settings/QS screenshots, notification + audio/haptic logs, owner mode-by-mode confirmation.

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
