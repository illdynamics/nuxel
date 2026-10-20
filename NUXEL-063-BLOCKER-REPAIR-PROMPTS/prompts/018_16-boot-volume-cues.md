# NUXEL REPAIR 16 — Boot cue and rapid volume feedback through verified output

**Priority:** P0  
**Prerequisite repair IDs:** 15,25  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Boot and volume cues exist in source but remain inaudible. This prompt must not treat a clean decoder exit as pass; first ensure physical speaker path has a verified route (task 15).

## Inspect these repository paths first

- `assets/nuxel-boot-audio.mp3`
- `assets/nuxel-pow.mp3`
- `services/nuxel-session/systemd/nuxel-boot-sound.service`
- `services/nuxel-session/systemd/nuxel-button-manager.service`
- `tools/s10plus/a34/nuxel-button-manager.c`
- `configs/nuxel/audio/audio.json`

## Required engineering work — execute all items

1. Trace the true boot animation → Home-ready event → one-shot playback semantics, including service restarts and launcher page reload; prevent multiple/replayed cues. Verify 7.7-second source and 44% software PCM request through an audio gain control that respects the proven protective physical cap.
2. Separate volume input event processing from playback, using a bounded nonblocking cue queue or debounce so successive presses remain responsive; avoid hundreds of overlapping `mpg123` processes.
3. Ensure volume step reflects effective selected mixer output and per-mode sound policies, and cue starts only after successful volume change. Do not spam during long key hold.
4. Add mocked transition tests for boot twice/restart, no sound device, stalled decoder, rapid 50 events, and system mute state. Include device timing logs for keydown→mixer confirmation→sound onset.
5. Use only the verified ALSA playback device/routes from speaker mission; test after one safe normal reboot with owner listening.

## Acceptance gates (all required for completion)

One and only one startup cue after real handoff; audible low-volume `nuxel-pow.mp3` on each intentional volume step; immediate responsive buttons, no runaway processes or unsafe gain.

## Evidence to collect

Boot event timestamps, systemd journal and audio route receipt, input latency numbers, real owner audible confirmation.

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
