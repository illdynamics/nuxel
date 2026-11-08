# NUXEL REPAIR 05 — Actual CPU utilization and frequency meter

**Priority:** P1  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

A40 C telemetry collector exists but is omitted from fresh rootfs until image-parity repair; CPU percent must use `/proc/stat` deltas and MHz must be a *current* frequency, not a CPU marketing maximum.

## Inspect these repository paths first

- `services/nuxel-metrics/nuxel-metricsd.c`
- `services/nuxel-metrics/nuxel-metrics.service`
- `services/nuxel-metrics/nuxel-metrics.socket`
- `pwa/nuxel-home/js/system-monitor.js`
- `pwa/nuxel-home/js/home-settings.js`

## Required engineering work — execute all items

1. Audit daemon CPU sampling for first-read invalidity, jiffy wrap, idle/iowait/steal calculation and contention between multiple HTTP clients. Unit test known synthetic `/proc/stat` snapshots.
2. Read Exynos CPUFreq per-cluster sysfs with units and thermal scaling; choose/label a defensible representative displayed MHz, and handle offline cores.
3. Expose a stable read-only JSON schema through the existing local metrics socket, consume it without duplicate intervals and stop when Home hidden.
4. Provide ON/OFF, 1/2/3/5/10-second intervals (3-second default), and persistent settings; do not recreate the widget for each update.
5. Ensure systemd packaging in fresh image and live USB upgrade; compare daemon readings with a diagnostic independent of UI.

## Acceptance gates (all required for completion)

Under idle/load, CPU percent and current MHz change plausibly; unavailable values display N/A, not fabricated 100%; 3-second default; collector single instance and low overhead.

## Evidence to collect

Time-aligned source counters and UI screenshots on S10+; unit test fixture results; power/CPU overhead measurement; service status from fresh-built image.

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
