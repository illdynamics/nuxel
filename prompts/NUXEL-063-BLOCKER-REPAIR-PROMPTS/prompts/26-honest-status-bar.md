# NUXEL REPAIR 26 — Truthful single-instance status icons + battery/sound

**Priority:** P1  
**Prerequisite repair IDs:** 09,10,17,18,19,20,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Owner observed overlapping/double Wi-Fi icon and phantom SIM bars; source-only indicators cannot establish actual radio/battery/charging/sound status.

## Inspect these repository paths first

- `pwa/nuxel-home/js/status-bar.js`
- `pwa/nuxel-home/css/status-bar.css`
- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/`

## Required engineering work — execute all items

1. Create one event-driven state model for Wi-Fi radio/association/internet, cellular modem present vs SIM absent vs registration, BT, GPS, NFC, sound mode, charging/battery and notifications. Ground each field in system service readback and expose unknown/unsupported distinctly.
2. Eliminate duplicate DOM insertion/listeners across reloads; use a responsive, single flex/grid row with safe-area insets instead of overlay hacks. Audit small S10+ status-bar width and rotation.
3. Preserve three battery display modes: percentage inside battery (readable), percentage-only text, proportional fill bar. Do not render a collapsed line in percent-only mode; test 0/50/100/unknown and charging.
4. Do not show cellular signal bars when no modem/SIM registration exists. Never present an icon animation as proof of connectivity.
5. Add DOM tests for repeated initialization, every indicator state and overlapping boxes; capture real top bar with different hardware states.

## Acceptance gates (all required for completion)

No overlapping indicators or duplicate Wi-Fi; battery modes readable and accurate; no-SIM accurate; unsupported features have truthful neutral states; tap opens matching functional setting.

## Evidence to collect

System-state JSON snapshots, bounding-box/DOM dumps, three battery screenshots and owner verification.

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
