# NUXEL REPAIR 02 — Four-app dock BG1/BG2 invisible or unswitchable

**Priority:** P0  
**Prerequisite repair IDs:** 04,31  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Owner reports no bottom app-dock artwork, and dock setting cannot switch correctly; A39/A43 asset hash tests pass but do not establish WebKit presentation. `.dock::before` had stacking fixes but still lacks on-device proof.

## Inspect these repository paths first

- `assets/nuxel-bottom-bar.jpg`
- `assets/nuxel-bottom-bar2.png`
- `pwa/nuxel-home/assets/nuxel-bottom-bar.jpg`
- `pwa/nuxel-home/assets/nuxel-bottom-bar2.png`
- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/js/launcher.js`
- `pwa/nuxel-home/js/home-settings.js`
- `pwa/nuxel-home/js/settings-store.js`

## Required engineering work — execute all items

1. Trace Home Settings selected dock ID → persistent store → render state → `.dock` CSS class/style → before pseudo-element → live resource path → WebKit compositor. Capture computed `content`, `background-image`, opacity, z-index, width/height, and parent `overflow` on phone.
2. Confirm BG1 is `nuxel-bottom-bar.jpg`, BG2 is `nuxel-bottom-bar2.png`, and BG2 is default when no saved preference. Validate PNG alpha and avoid an opaque wrapper over its transparent corners.
3. Correct stylesheet specificity and actual app-dock layer, keeping background above wallpaper but behind four tappable app icons; never use negative z-index inside an opaque stacking context without proof.
4. Make switch immediate, preserve user layouts, prevent service-worker stale CSS, and deploy identical assets to the active webroot. If loaded image differs from screenshot, inspect WebKit repaint and compositing, not just source references.
5. Write tests for default/migration, toggling, persistence, URL/hash resolution, missing-asset fallback and no pointer interception.

## Acceptance gates (all required for completion)

Physical app dock displays BG2 after fresh preferences; BG1 immediately replaces it via Home Settings; both survive reload/reboot; four apps remain correctly positioned, responsive and stationary when pages slide.

## Evidence to collect

Two real phone screenshots BG1/BG2, actual computed styles and image HTTP fetches, source/deployed hashes, owner PASS/FAIL, preference value before/after reboot.

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
