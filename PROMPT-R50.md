# NUXEL R50 — System resource and performance quality
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r50-resource-performance-quality`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Measure and improve Nuxel resource/performance quality on the S10+: CPU/GPU, memory pressure, storage I/O, compositor pacing, startup, app switching, long log scrolling, and thermal behavior. Optimize only from measurements and protect against regressions in touch latency and battery life.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md`, `docs/beta-finalization/testing/TEST-STRATEGY.md`, `docs/beta-finalization/testing/evidence/soak-device-20261017T005131+0200/`, `services/nuxel-metrics/`, `pwa/nuxel-home/js/system-monitor.js`, `pwa/nuxel-home/js/bootlog.js`, `pwa/nuxel-home/js/recents.js`, and `tools/s10plus/a33/nuxel-wl-fb.c`. Existing soak evidence exists; current values must be re-measured.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns measurement methodology, budgets, profiling, and scoped optimizations. Does not own unrelated feature behavior. No optimization based on a single sample and no disabling safety/telemetry-required diagnostics to improve a score.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define baseline budgets for boot-to-launcher, tap-to-frame, app switch, log scroll, memory, CPU idle, and temperature.
2. Instrument reproducible workloads using existing metrics/soak tools and record device state, governor, brightness, and thermal zone.
3. Profile the launcher/WebKit/compositor and services to identify the top measured bottlenecks.
4. Optimize only the measured hotspot; add a before/after benchmark and verify no functional regression.
5. Test long-running soak, memory pressure, storage writes, and repeated app switching.
6. Check that logging/diagnostics do not grow without bounds or themselves cause jank.
7. Document thermal/battery trade-offs and rollback if a change regresses responsiveness.

## Failure modes and diagnostics
- Watch for benchmark results affected by charger mode, thermal throttling, background services, or a different brightness/governor. Do not compare a cold boot with a warm one. Use p50/p95, not a single best sample.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Baseline and after values use the same workload, device state, and measurement method.
2. At least one measured bottleneck is improved or the report proves no safe improvement is available.
3. Tap-to-frame and app-switch latency do not regress beyond the declared budget.
4. Memory/CPU/temperature stay within documented limits during a soak.
5. Logs and metrics remain bounded.
6. No safety or diagnostic feature is disabled merely to improve a benchmark.
7. Measurements are labeled LIVE-DEVICE vs VM/SIMULATED.

## Hardware, privilege and rollback safety
No aggressive thermal/voltage changes, no disabling safety caps, no unbounded profiling in production. Preserve recovery and logging.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r50-resource-performance-quality`, with tests and docs for this component only.
- `docs/component-reports/r50.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the workload cannot be reproduced or the device is thermally unstable. Report the measurement limitation rather than an invented improvement.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
