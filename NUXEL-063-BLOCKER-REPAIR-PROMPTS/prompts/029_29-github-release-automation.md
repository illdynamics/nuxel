# NUXEL REPAIR 29 — Main-merge CI, tag, prerelease and verified S10+ artifacts

**Priority:** P0  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current workflow listens for `main` pushes, tags `v*`, and manual dispatch; publication skips a main push if canonical VERSION tag already exists. No remote successful release run or bootable image proof exists.

## Inspect these repository paths first

- `.github/workflows/release.yml`
- `images/s10plus/build.sh`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `tools/verify-artifacts.sh`
- `tools/package-release.sh`
- `VERSION`

## Required engineering work — execute all items

1. Audit prepare/build/release job outputs and secrets/tokens permissions under GitHub branch protections. Define release behavior: each merged PR to main runs build/test; only a new valid `VERSION` creates a new tag/prerelease. Decide separately whether unchanged-version merges should publish nightly artifacts, but never replace an immutable tag.
2. Validate canonical tag `v0.6.3-beta` for VERSION match, checked-out SHA reachable from protected main, tag creation races, workflow_dispatch source SHA and tag-push duplicate triggers. Use concurrency, immutable artifacts, no force pushes or rewrite old published release.
3. Ensure S10+ image build includes verified Fedora rootfs from task 28, current launcher/service components, boot image checks, checksums, release notes and artifact download smoke test. Never claim release succeeded because YAML parsed.
4. Write local workflow-contract tests and actionlint; exercise GitHub Actions on an authorized test PR; capture logs, final check status, generated tag, published release URL and artifact SHA after PR merge.
5. If bot token cannot create tag under ruleset, return explicit permissions/required administrator setup; do not bypass protections or silently mutate main.

## Acceptance gates (all required for completion)

Every merge runs verified CI; a valid version-bumping merge publishes exactly one canonical tag and GitHub prerelease with downloadable S10+ artifacts; failures block publish and report precise cause.

## Evidence to collect

Actual GitHub run IDs/conclusions, tag→main SHA, release URL, downloadable archive hash and included image manifest; no fabricated remote success.

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
