# NUXEL REPAIR 14 — Secure ZIP create, inspect and extract in Files

**Priority:** P1  
**Prerequisite repair IDs:** 13  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Requested ZIP operations are not implemented end to end in File Explorer; creating a fake archive entry or only manipulating localStorage does not satisfy file management.

## Inspect these repository paths first

- `pwa/nuxel-apps/files/js/files.js`
- `services/nuxel-portal/src/portal.py`
- `pwa/nuxel-apps/downloader/`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Implement archive operations in the Files privileged backend using a maintained library: create ZIP from selected files/folders, validate/open archive listing, Extract Here and Extract to new folder, progress/cancellation and conflict handling.
2. Defend against Zip Slip (`../`, absolute paths, drive prefixes), archive symlink escapes, hard-link tricks, duplicate entries, malformed compression, decompression bombs, sparse filesystem exhaustion and unauthorized destination paths.
3. Enforce per-operation limits for extracted bytes, entry count, path depth and runtime; use staging dirs and atomic rename or roll back incomplete output on failure. Do not overwrite without explicit confirmation.
4. Support UTF-8 names and document handling encrypted ZIP only if a suitable, auditable library actually supports it; otherwise show unsupported.
5. Run adversarial archive fixtures and golden round trips, then create/extract a real ZIP of sample files on the S10+ and verify checksums.

## Acceptance gates (all required for completion)

User can create ZIP and safely extract into intended location; malicious ZIPs cannot escape or exhaust storage unchecked; progress/errors honest and all files verified.

## Evidence to collect

Pre/post file tree and SHA-256, adversarial test logs, storage/cancel tests, live user test and rollback instructions.

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
