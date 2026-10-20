# NUXEL REPAIR 27 — Actual Quick Settings toggles with synchronized backend

**Priority:** P0  
**Prerequisite repair IDs:** 09,10,17,18,19,20,23,26  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

`qs.js` `_toggle()` currently routes Wi-Fi to `_setWifiEnabled()` but other tile IDs emit an unavailable message, failing Phase 13. Functional logic must use existing backends or report unsupported—not fake tile state.

## Inspect these repository paths first

- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-home/js/bridge.js`
- `services/nuxel-bridge/src/bridge.py`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-home/css/style.css`

## Required engineering work — execute all items

1. Inventory each tile and its actual privileged owner: Wi-Fi via NetworkManager, BT via BlueZ, location via GeoClue, NFC via NCI, torch via verified LED broker, sound mode via notifications policy, cellular via ModemManager and rotation/power via real compositor/power service.
2. Design a narrow typed RPC/status contract for state, supported capabilities, permitted actions, in-progress and errors. Check backend before enabling a tile; enforce permissions and prohibit the PWA calling arbitrary commands.
3. Implement read→request change→verify readback→update UI with explicit timeouts, rollback of optimistic visual state and error copy. Subscribe to D-Bus events instead of continual polling.
4. Integrate with Settings using the same state source and avoid conflicting toggles/parallel radio managers. Preserve compact/expanded shade gestures and original supplied icons.
5. Automate per-tile state transition tests including permission failure, absent driver, rfkill, subprocess crash, concurrent toggle and UI restart; physically validate independent supported toggles.

## Acceptance gates (all required for completion)

No tile claims ON unless real backend says ON; supported functions change physical device state and Settings mirror them; unavailable ones are clearly disabled with exact reason.

## Evidence to collect

Per-tile API and daemon receipts, live device state before/after, UI screenshots and owner confirmations.

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
