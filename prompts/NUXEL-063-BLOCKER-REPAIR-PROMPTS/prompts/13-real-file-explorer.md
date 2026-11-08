# NUXEL REPAIR 13 — Real filesystem File Explorer operations and security

**Priority:** P0  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current Files app caches `storage.list-dir` once, starts at `/`, navigates cached entries only, stores folder/create/delete changes in localStorage, has placeholder previews and unsafe `innerHTML` insertion of filesystem metadata.

## Inspect these repository paths first

- `pwa/nuxel-apps/files/js/files.js`
- `pwa/nuxel-apps/files/index.html`
- `pwa/nuxel-apps/files/css/files.css`
- `services/nuxel-portal/src/portal.py`
- `services/nuxel-bridge/src/bridge.py`

## Required engineering work — execute all items

1. Design and implement permission-scoped filesystem bridge/portal operations for list/stat/read/open/mkdir/rename/copy/move/delete-to-trash/restore; begin in the actual unprivileged user's home, not `/root`. Authenticate app identity at host boundary and do not trust JS-provided app IDs alone.
2. Implement server-side canonical path validation anchored to granted roots, symlink defense, ownership checks, race-safe operations where possible (`openat`/dirfds), bounded reads/uploads, and consistent errors. Never shell-interpolate names.
3. Replace cached path navigation with async per-directory reloads, breadcrumbs, back/forward, show hidden, storage roots, sorting/filtering and keyboard/touch selection. Render filenames using `textContent` or escaped nodes, not interpolated `innerHTML`.
4. Support multi-select mixed files/folders, clipboard copy/cut/paste, progress, conflict resolution, permissions details and basic real previews only for supported types; disable unsupported buttons rather than showing fake success.
5. Implement structured tests with temp dirs, symlinks, escaped names, quotes/HTML markup, non-ASCII filenames, permissions, conflicting writes, rollback of partial copy/move and user-home detection; add a live temp test under the actual user HOME.

## Acceptance gates (all required for completion)

Real files/folders change on disk, are visible after app restart, cannot escape allowed roots; operations have truthful errors, path navigation works, unsafe filename markup never executes.

## Evidence to collect

Filesystem-before/after `stat` and checksums, portal permission log, actual in-app screenshots and tests on disposable user home fixtures.

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
