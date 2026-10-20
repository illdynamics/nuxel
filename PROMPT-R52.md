# NUXEL R52 — Release-grade test strategy
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r52-release-grade-test-strategy`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Define and implement a release-grade test pyramid for Nuxel: host unit tests, ARM64 integration, VM boot, service smoke, image/artifact validation, live-device checks, and owner acceptance. The strategy must use deterministic fixtures, failure injection, and non-skippable gates, while marking hardware-dependent results NOT TESTED until observed.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `.github/workflows/release.yml`, `tools/beta/run-all-tests.sh`, `tools/beta/tests/test-release-tools.sh`, `boot/s10plus/tests/test-boot-image-gates.sh`, `vm/`, `ci/validate-build.sh`, `docs/beta-finalization/testing/TEST-STRATEGY.md`, `docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md`, and `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`. Several test suites and evidence sets exist; their coverage and non-skippability need audit.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the test-layer model, gate definitions, fixtures, failure injection, and release acceptance criteria. Does not own each feature implementation. No gate that passes on a missing dependency and no hardware PASS from a mock.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Inventory existing tests and map them to layers: host unit, contract/schema, ARM64 build, VM boot, service smoke, image inspection, live device, owner acceptance.
2. Identify untested critical paths and add tests at the lowest effective layer.
3. Make hardware-dependent gates explicit skips/BLOCKED with owner steps, never silent passes.
4. Add failure injection for missing config, service crash, disk full, network loss, corrupt artifact, and interrupted install.
5. Define release criteria and evidence required for each criterion, including non-skippable protected gates.
6. Run the full suite from a clean checkout and from CI-equivalent conditions; record duration/flakiness.
7. Add a test dashboard/matrix that distinguishes PASS/FAIL/SKIP/BLOCKED/NOT TESTED.

## Failure modes and diagnostics
- Watch for tests that assert the current broken value, shell tests with unset variables, VM tests requiring an unavailable hypervisor, and CI caching artifacts from a previous run. Pin locale/timezone/randomness where results depend on them.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every critical subsystem maps to at least one test layer and a named evidence artifact.
2. The suite runs from a clean checkout with no hidden local state.
3. A missing dependency/phone produces BLOCKED/NOT TESTED, not PASS.
4. Failure-injection cases are covered for artifact, service, storage, and network faults.
5. Protected boot/input/recovery/release gates cannot be skipped without a hard failure.
6. The release evidence records exact commands, environment, durations, and results.
7. A hardware test is never promoted from VM/mock evidence.

## Hardware, privilege and rollback safety
Do not create a test that flashes, partitions, or reboots a live phone without explicit owner policy. Use fixtures and dry runs. Preserve failure logs.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r52-release-grade-test-strategy`, with tests and docs for this component only.
- `docs/component-reports/r52.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the test environment cannot be made deterministic; document the flake source rather than retrying until green.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
