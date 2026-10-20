# NUXEL REPAIR 06 — Real RAM usage, percentage and quantities

**Priority:** P1  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

RAM meter currently depends on metrics daemon; final.md requires MemTotal/MemAvailable-based used/total GiB and a truthful percentage on the Home widget.

## Inspect these repository paths first

- `services/nuxel-metrics/nuxel-metricsd.c`
- `pwa/nuxel-home/js/system-monitor.js`
- `pwa/nuxel-home/js/home-settings.js`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Audit `/proc/meminfo` parser robustness for missing/reordered fields and kB units, use MemTotal−MemAvailable rather than naive MemFree, and bound 0–100%.
2. Ensure process/OS reservations are not accidentally presented as independent physical GPU VRAM. Mark unavailable when procfs cannot be read rather than guessing.
3. Update widget layout to show `RAM xx% · used/total GiB` without truncating on the S10+ resolution; review screen rotation.
4. Integrate with the shared 3-second metrics refresh and Home-hidden pause; validate no extra subprocesses/timers.
5. Run deterministic parser tests, live stress test and fresh-image systemd installation verification.

## Acceptance gates (all required for completion)

Reported utilization agrees within rounding with `/proc/meminfo`, updates under real workload, stays readable and persists preferences without growing CPU consumption.

## Evidence to collect

Meminfo snapshots, numerical calculations, device screenshots, service boot logs, and test outputs.

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
