# NUXEL REPAIR 07 — Mali GPU utilization and frequency

**Priority:** P1  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

GPU metrics are conditional: driver instrumentation may not expose true utilization; the current UI may show N/A. Frequency is not utilization.

## Inspect these repository paths first

- `services/nuxel-metrics/nuxel-metricsd.c`
- `pwa/nuxel-home/js/system-monitor.js`
- `docs/s10plus-autonomous-boot-repair/`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Inventory live Mali GPU driver implementation, `/sys/class/devfreq`, thermal/devfreq counters, busy/idle accounting, debugfs availability and permissions. Identify exact live interface and sampling units before writing a parser.
2. When driver exposes monotonic active/total time, compute percent from deltas with wrap/reset detection. Show per-GPU current frequency in MHz only if read from real clock interface.
3. Do not elevate daemon privileges or expose arbitrary debugfs unnecessarily. If no hardware busy counters exist, leave usage N/A and document precise kernel driver limitation without calculating an invented percentage.
4. Separate GPU utilization field from frequency status in collector schema/UI. Add fixtures for zero counters, missing nodes, wraparound and thermal scale changes.
5. Test while animating UI or a reproducible GPU load, comparing rate/trend with system instrumentation where available.

## Acceptance gates (all required for completion)

Actual utilization varies on load only if live driver provides trustworthy busy accounting; correct frequency displayed; honest N/A and specific blocker when instrumentation unavailable.

## Evidence to collect

Device sysfs/debugfs paths and contents, schema samples, bench trace, screenshots; no claim of driver support from file names alone.

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
