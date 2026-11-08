# NUXEL REPAIR 23 — Real LED torch backend and fail-honest toggle

**Priority:** P1  
**Prerequisite repair IDs:** 25,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Button manager sends a flashlight request while actual LED is owned by another backend; Quick Settings flashlight action reports unavailable. There is no physically demonstrated torch.

## Inspect these repository paths first

- `tools/s10plus/a34/nuxel-button-manager.c`
- `pwa/nuxel-home/js/qs.js`
- `services/nuxel-bridge/src/bridge.py`
- `configs/nuxel/buttons.json`

## Required engineering work — execute all items

1. Identify rear flash/torch hardware and kernel exposure through LED class or V4L2 flash subdevice, not guessed GPIO/registers. Check camera flash resource ownership and vendor driver capability.
2. Implement a single broker service with on/off readback, permission checking, bounded torch duration, automatic OFF on crash/suspend/thermal alarms and safe brightness.
3. Wire both Quick Settings and double-Bixby request to that same backend; UI state must reflect actual LED power and error states, not optimistic CSS only.
4. Do not use photo flash/strobe commands as a continuous torch, disable thermal/current limits or write unknown sysfs nodes.
5. Test toggling while camera open, rapid presses, screen lock, power suspend, service crash and owner observation; report exact hardware limitation if torch API missing.

## Acceptance gates (all required for completion)

Physical rear LED visibly turns on/off on request and state syncs in QS/Bixby; auto-off and thermal safety work; otherwise unavailable with exact driver evidence.

## Evidence to collect

Kernel LED/V4L2 node dump, output state, structured logs and owner physical confirmation.

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
