# NUXEL REPAIR 21 — Nuxel Maps online tiles, OSM behavior and GNSS

**Priority:** P2  
**Prerequisite repair IDs:** 11,20,12  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Map has offline grid, IndexedDB tile cache and optional URL template; it does not have verified network tile provider, accurate live GPS or full route/search service behavior.

## Inspect these repository paths first

- `pwa/nuxel-apps/maps/js/maps.js`
- `pwa/nuxel-apps/maps/index.html`
- `pwa/nuxel-apps/maps/css/maps.css`
- `pwa/nuxel-common/geolocation.js`

## Required engineering work — execute all items

1. Inspect current canvas mapping math, tile addressing, caching and drawing; ensure antimeridian/wrap, polar limits, zoom clamping and proper pixel coordinates.
2. Configure a legitimate OpenStreetMap-compatible tile provider respecting its attribution, request rate, user agent and bulk-download rules. Do not assume public OSM tiles can be bulk cached offline.
3. Integrate permission-scoped location provider from task 20 and distinguish real GNSS fix from manual marker/approximate location. Show accuracy circle, last-fix time and unavailable state.
4. Implement touch panning, pinch zoom, markers, coordinate search and search/routing only when real provider configured; expose clear offline error and opt-in tile cache limits.
5. Test no-network maps, provider 429, corrupt tiles, wrong GPS permissions, dateline crossing and app memory under prolonged pan/zoom; test real download after Wi-Fi/HTTPS passes.

## Acceptance gates (all required for completion)

Real licensed/attributed map tiles load over HTTPS; pan/pinch works smoothly, cached tiles survive offline; current-location button uses a permitted, accurately labeled real fix or shows unavailable.

## Evidence to collect

Rendered tile screenshots, provider/attribution settings, permission logs, offline/online test, owner location comparison when available.

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
