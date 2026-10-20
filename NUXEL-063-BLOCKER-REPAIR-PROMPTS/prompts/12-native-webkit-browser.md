# NUXEL REPAIR 12 — Full native WebKit multi-tab Nuxel Browser

**Priority:** P0  
**Prerequisite repair IDs:** 10,11,28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current Browser is an iframe using `view.src=target`, which fails framing-restricted sites and does not provide native top-level browser contexts, downloads or private sessions.

## Inspect these repository paths first

- `pwa/nuxel-apps/browser/index.html`
- `pwa/nuxel-apps/browser/js/browser.js`
- `pwa/nuxel-apps/browser/css/browser.css`
- `tools/s10plus/a33/nuxel-pwa-host.c`
- `pwa/nuxel-home/js/apps.js`
- `services/nuxel-portal/`

## Required engineering work — execute all items

1. First inspect actual GTK/WebKit host capabilities and existing app launch contracts. Design privileged native Browser UI/controller with real `WebKitWebView` (one per tab), proper signals (`load-changed`, title, progress, can-go-back/forward, download-started, TLS errors) and a narrow IPC surface—not general root/bridge access to sites.
2. Migrate Browser UI to address/search bar, tabs create/switch/close, history/bookmarks, find-in-page, refresh/stop, download status, user agent preference, mobile viewport and touch gestures.
3. For private mode create ephemeral WebKit data manager/context, no persistence of cookies/cache/history; ensure regular-profile state isolation and session clearing on close.
4. Implement download destination through a permission-scoped file portal, confirmation, filename validation and safe handling. Deny or request permissions for camera/location/mic; do not bypass TLS errors by default.
5. Test top-level sites with X-Frame-Options/CSP denial, TLS-valid/TLS-invalid pages, downloads, process crashes, back/forward, multi-tab, private cookies and OSK text entry.
6. Ensure fresh rootfs installs native host changes and browser exposes no privileged Nuxel JS APIs to arbitrary websites.

## Acceptance gates (all required for completion)

User opens a real HTTPS site that forbids framing, multiple tabs work and persist appropriately, private cookies vanish, downloads produce usable local files, TLS errors fail closed.

## Evidence to collect

Native window list/signal logs, real site screenshots, download SHA-256, browser privacy test and validated S10+ AArch64 binary.

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
