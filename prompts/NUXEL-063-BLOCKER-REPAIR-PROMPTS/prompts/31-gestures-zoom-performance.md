# NUXEL REPAIR 31 — Home gesture arbitration, app drawer, zoom and smoothness

**Priority:** P1  
**Prerequisite repair IDs:** 02,04,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Previous user reports bottom-half swipe-up app drawer not reliably opening, unwanted Home zoom/pan, jittery scrolling and inconsistent app/window activation. A43 only passed static source checks; no frame measurements.

## Inspect these repository paths first

- `pwa/nuxel-home/js/gestures.js`
- `pwa/nuxel-home/js/launcher.js`
- `pwa/nuxel-home/js/navigation.js`
- `pwa/nuxel-home/js/recents.js`
- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/js/scroll-indicators.js`

## Required engineering work — execute all items

1. Map gesture recognizers, event capture/bubble and touch-action CSS; define per-screen ownership: upper Home half down Quick Settings, lower Home half up app drawer, second swipe up Settings, reverse swipe closes; horizontal Home pages must not conflict with dock drag/drop.
2. Disable pinch/double-tap page zoom only in launcher Home viewport while preserving deliberate map/browser zoom and accessibility-friendly user scale outside Home. Eliminate unintended panning when Home at natural scale.
3. Fix drawer open/render/close transitions using stable state and focus ownership, not timeout hacks; launching an app must wait for mapped visible window and close drawer without stealing keyboard focus.
4. Implement composited transform/opacity transitions with reduced-motion support and one requestAnimationFrame-driven update path; trim log console DOM refreshes and synchronous touch handlers. Avoid intercepting scrolling inside Settings/list views.
5. Capture S10+ frame times, touch-down→visible drawer latency and user test for long-press drag, screen rotation, Home navigation and app switching. Add test traces for swipe direction, repeated touch sequences, cancellation, two-finger pinch and gesture conflicts.

## Acceptance gates (all required for completion)

Bottom swipe opens drawer on first intentional gesture, desktop swipes animate smoothly, no unwanted Home zoom, independent scroll views work, Home/Back/Recents and drag are not regressed; measured improvement rather than anecdote.

## Evidence to collect

Device frame-time traces before/after, rendered screenshots, touch event logs, owner 90-second gesture PASS/FAIL matrix.

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
