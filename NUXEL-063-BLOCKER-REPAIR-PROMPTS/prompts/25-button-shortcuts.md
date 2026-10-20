# NUXEL REPAIR 25 — Deterministic Power/Bixby/volume input FSM

**Priority:** P1  
**Prerequisite repair IDs:** 22,23,24,16  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Hardware FSM source exists but the double Power camera, double Bixby torch, screenshot chord and volume responsiveness have not been verified as a coherent physical input pipeline.

## Inspect these repository paths first

- `tools/s10plus/a34/nuxel-button-manager.c`
- `tools/s10plus/a34/nuxel-button-fsm.h`
- `configs/nuxel/input/button-fsm.json`
- `services/nuxel-session/systemd/nuxel-button-manager.service`
- `tools/s10plus/a34/nuxel-button-trace.sh`

## Required engineering work — execute all items

1. Audit single owner of evdev devices and event emission; measure kernel event time vs debounce vs action; prevent double consumption from another UI daemon.
2. Write explicit FSM for single Power = sleep/wake, hold Power = power menu, double Power within calibrated 350–450 ms = camera, double Bixby = flashlight, Power+VolDown = screenshot, and volume auto-repeat; priority should prevent accidental sleep or volume changes when chord matched.
3. Guarantee short vs hold mutually exclusive, handle contact bounce, key rollover, delayed release, simultaneous keys, lost focus and service restart; never kill essential processes through long navigation Back.
4. Route actions to their real backend with readback and bounded retries, not shell strings or fake CSS state; ensure unsuccessful camera/flashlight actions report blocked.
5. Add table-driven input trace fixture suite plus real 90-second user hardware test, measure latency before/after and preserve navigation/haptics.

## Acceptance gates (all required for completion)

Each physical gesture invokes exactly one intended operation, never spurious actions, and works while applications focused; volume shows prompt consistent changes.

## Evidence to collect

Evdev trace anonymized, FSM transition log, timing histogram, app/window state, owner PASS/FAIL for each key combination.

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
