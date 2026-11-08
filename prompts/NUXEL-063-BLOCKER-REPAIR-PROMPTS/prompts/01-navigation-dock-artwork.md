# NUXEL REPAIR 01 — Bottom navigation dock artwork and layering

**Priority:** P0  
**Prerequisite repair IDs:** 04,31  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

The three-button Back/Home/Recents region has supplied custom artwork; the owner reports dock backgrounds absent on the live screen. Source image presence is not proof of visible rendering. Do not confuse navigation bar background with the separate four-app dock.

## Inspect these repository paths first

- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/index.html`
- `pwa/nuxel-home/assets/branding/button-left.png; button-middle.png; button-right.png`
- `pwa/nuxel-home/sw.js`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Trace which DOM element encloses the *navigation* three-button bar, and its height, stacking contexts, z-index, clipping and transforms in WebKitGTK. Determine whether custom navigation artwork is separately supplied; do not accidentally paint BG1/BG2 behind system buttons.
2. Identify the actual active webroot and image URL; compare source/deployed SHA-256, HTTP status/MIME and computed CSS background-image. Audit parent backgrounds, safe-area inset and overscan with portrait/landscape.
3. Use a dedicated noninteractive pseudo-element behind the three button hitboxes, preserving SVG/PNG crisp edges and transparent space. Do not use an opaque blue rectangle as a default when custom artwork is configured.
4. Preserve pointer ownership for short Back, long Back, Home and Recents; test taps at boundaries. Ensure animations and page transitions do not send the bar behind another surface.
5. Add a DOM/CSS integration test and a diagnostic capture of computed style, element bounding boxes and visible framebuffer. Deploy only userspace web assets via the existing USB path with cache-version bump.

## Acceptance gates (all required for completion)

Artwork actually visible across full intended bottom width on S10+; Back/Home/Recents accept single touches and long-hold; no clipping, accidental scroll or overlapping panel in either desktop; survives launcher restart/reboot.

## Evidence to collect

Phone screenshot plus owner confirmation; asset SHA-256, resource HTTP 200, computed DOM stacking report, and recorded three-button event sequence.

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
