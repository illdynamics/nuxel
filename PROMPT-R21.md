# NUXEL R21 — Vibration and haptics
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r21-vibration-haptics`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make haptics a single-owner, truthful subsystem: discover the real vibrator, enforce one API gate/global switch, honor accessibility settings, and deliver bounded tap/scroll/long-press/key patterns without competing services or pulses outliving their request.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/haptics/haptics.json`, `configs/nuxel/haptics/bridge.json`, `configs/nuxel/haptics/nuxel-haptics-bridge.service`, `services/nuxel-haptics/nuxel-hapticsd.py`, `services/nuxel-haptics/nuxel-haptics.service`, `tools/s10plus/a33/nuxel-haptics-diag.sh`, `tools/s10plus/a33/nuxel-haptics-bridge.py`, and `tools/s10plus/a33/tests/hw-subsystems/test-haptics-diag.py`. The manifest warns that a node existing is not proof of a felt buzz; intensity is duration-only if no amplitude control exists.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns vibrator node discovery, the gated haptics API, pattern expansion, rate limiting, global switch, and consumer wiring. Does not own button timing or notification policy; consume their events. There must be exactly one writer to the actuator.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate candidate LED/timed_output/input actuator interfaces and prove which one accepts a bounded pulse.
2. Audit all processes/services that can write the vibrator and eliminate duplicate ownership.
3. Implement/enforce the global switch, session gate, rate limit, max duration, and quiet-hour rules.
4. Map tap, scroll, long-press, key, notification, and gesture events to bounded patterns without blocking the caller.
5. Verify amplitude capability honestly: use duration-only mode when no amplitude/strength control exists.
6. Test cancellation/exit paths so a pulse cannot outlive its request or survive a service restart.
7. Define a physical owner test for each pattern and a log that correlates request to actuator write.

## Failure modes and diagnostics
- Watch for both `nuxel-haptics.service` and `nuxel-haptics-bridge.service` owning the device, `activate` vs `duration`/`brightness` semantics, 0 ms writes, and a request queue replaying stale pulses after resume.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report names the real actuator path and whether amplitude is supported.
2. Only one service/process writes the actuator during the test.
3. The global switch off and closed API gate both refuse every automatic pulse.
4. Duration and rate limits are enforced in tests, including a rejected over-limit request.
5. A cancelled/failed request leaves the actuator off.
6. Keyboard/button/notification patterns are distinguishable and bounded.
7. A felt-buzz owner result is recorded separately from node/API tests.

## Hardware, privilege and rollback safety
No high-amplitude/continuous burn-in test. Preserve accessibility/off switch. Do not change kernel drivers or flash.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r21-vibration-haptics`, with tests and docs for this component only.
- `docs/component-reports/r21.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a second unavoidable ownership path cannot be removed. Report the exact conflicting unit/process; do not enable both and hope.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
