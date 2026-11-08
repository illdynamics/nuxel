# NUXEL REPAIR 04 — Custom icon loading and WebKit asset/cache consistency

**Priority:** P0  
**Prerequisite repair IDs:** none  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Icon packs exist and some artwork has appeared on device before, but mismatched active webroots and stale WebKit service workers previously caused source-correct assets not to render.

## Inspect these repository paths first

- `pwa/nuxel-home/sw.js`
- `pwa/nuxel-home/js/apps.js`
- `pwa/nuxel-home/assets/branding/`
- `pwa/nuxel-apps/_shared/`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `tools/s10plus/a39/tests/test_a39_assets.py`

## Required engineering work — execute all items

1. Enumerate active app, navigation and toggle icons from generated registries; assert every URL resolves on the actual phone web server, not just inside repository.
2. Verify filesystem staging, MIME, case sensitivity, transparent pixels and SHA-256 against source icon art. Fix missing registry entries, wrong absolute `/pwa` versus `/assets` URLs, and ignored assets when needed.
3. Trace service-worker fetch strategy and cache names; ensure build versions invalidate *code assets* without deleting layout/credential/user data. Avoid permanently caching broken 404s.
4. Check duplicate old icon renderers, CSS backgrounds and clipped controls after first boot, Home reload, Quick Settings reopen, and app-switching.
5. Add a manifest-based test that opens each registered image URL; instrument WebKit load errors and collect device screenshots for spot checking.

## Acceptance gates (all required for completion)

Every referenced custom icon returns a real image and is visibly correct in launcher, buttons, quick toggles and Browser/Settings without stale or duplicate rendering; no user data loss during cache refresh.

## Evidence to collect

Source + deployed hashes, URL status and MIME table, service-worker cache keys, real screen evidence for representative icons and owner sign-off.

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
