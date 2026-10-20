# NUXEL REPAIR 08 — Mali shared GPU allocation accounting

**Priority:** P2  
**Prerequisite repair IDs:** 28,07  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current collector deliberately emits `gpu_memory_kib:null`; display says N/A because Mali uses shared system RAM. `final.md` asks for GPU-attributed allocation if genuinely exposed, not fictitious dedicated VRAM.

## Inspect these repository paths first

- `services/nuxel-metrics/nuxel-metricsd.c`
- `pwa/nuxel-home/js/system-monitor.js`
- `services/nuxel-metrics/README.md`

## Required engineering work — execute all items

1. Identify driver-specific allocation accounting (e.g. supported Mali memory data, dma-buf heap statistics, DRM GEM/cgroup mappings) and document whether it is attributable to the GPU rather than global shared memory.
2. Carefully distinguish reserved GPU heaps, dma-buf allocations used by several subsystems, total system RAM and genuinely GPU-attributable pages. Do not double-count.
3. If a defensible per-GPU measure exists, implement read-only sampling with supported units, provenance/source label and unavailable fallbacks. If not, preserve N/A and explain why a numeric meter is impossible without new instrumentation.
4. Implement counter and overflow tests and verify runtime permissions without privileged broad filesystem access.
5. Show `GPU MEM` as GiB/MiB only when metric is real; never imply the chip contains dedicated VRAM.

## Acceptance gates (all required for completion)

A numeric value is shown only with documented live allocation evidence and behaves under GPU memory pressure; otherwise honest N/A and explicit driver blocker are accepted as technically correct.

## Evidence to collect

Driver docs, runtime node/data samples, ownership accounting assumptions, baseline/load comparisons and owner-visible fallback.

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
