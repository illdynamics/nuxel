# NUXEL REPAIR 30 — Evidence-based documentation, progress and feature claims

**Priority:** P1  
**Prerequisite repair IDs:** 01-29  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

README still has v0.6.1-beta heading, historical A39 material in changelog, and `final.md` is a list of acceptance requirements—not proof of completion. Audit report identifies unfinished features.

## Inspect these repository paths first

- `README.md`
- `CHANGELOG.md`
- `VERSION`
- `A43-VERIFICATION.md`
- `docs/beta-finalization/manual-proof/`
- `final.md`

## Required engineering work — execute all items

1. Create a single machine-readable acceptance status table for all 27 final.md rows, with distinct source/build/live-deployed/owner-confirmed statuses and links to evidence; never convert missing test to PASS.
2. Update README current release identity and real supported device matrix, known S10+ limitations, production vs beta claims, setup/install prerequisites and kernel restriction.
3. Normalize CHANGELOG chronological structure and version history while preserving past data; do not rewrite history or invent release dates.
4. Recalculate source-derived counts/percentages only with documented numerator, denominator and rationale; distinguish project milestones/57 prompt-only branches from implemented features and user-confirmed hardware.
5. Generate a self-audit script that fails on inconsistent VERSION/README/release notes, duplicate stats and missing verification receipts; report publication and hardware status honestly.

## Acceptance gates (all required for completion)

Docs correctly say what works, what is unverified, what is blocked, and where proof lives; all percentages reproducible; README/changelog/version consistent and no unsupported production claims.

## Evidence to collect

Document diff, acceptance-data snapshot, calculation script output and receipts to underlying source/build/owner proofs.

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
