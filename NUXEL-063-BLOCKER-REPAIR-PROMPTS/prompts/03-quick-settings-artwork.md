# NUXEL REPAIR 03 — Quick Settings shade and notification panel graphics

**Priority:** P1  
**Prerequisite repair IDs:** 01,02,04,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Custom toggles and shade backgrounds are present in assets, but the physical WebKit rendering state is unverified. The full shade must remain scrollable and not obscure control hitboxes.

## Inspect these repository paths first

- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-home/css/style.css`
- `pwa/nuxel-home/index.html`
- `pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/`
- `pwa/nuxel-home/sw.js`

## Required engineering work — execute all items

1. Inventory which surfaces have actual supplied panel artwork; distinguish compact shade, fully expanded shade, per-toggle background and notification panel instead of applying one image everywhere.
2. Audit CSS computed layers after compact and expanded transitions; verify active source asset URLs, opacity, scaling, and noninteractive decorative layers.
3. Preserve 2-stage swipe down/up state transitions, rendering of toggles during screen rotation, and accessibility labels and touch hitboxes.
4. Use crisp scaling for pixel graphics when appropriate, keep transparent regions truly transparent, and measure the effect on repaint/animation cost.
5. Update build/deploy manifests and service-worker caches. Exercise visible panels over Home/Settings and log any missing assets or WebKit errors.

## Acceptance gates (all required for completion)

Compact and expanded Quick Settings art and custom toggles visibly correct, controls clickable, content scrolls, no boring blue fallback in areas designed for artwork, smooth reopen and persistence after reload.

## Evidence to collect

S10+ framebuffer captures for compact/expanded shades; network/HTTP asset receipts; computed CSS and gesture traces; owner confirmation.

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
