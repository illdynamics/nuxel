# NUXEL R55 — Manual hardware proof must never block other work
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r55-manual-proof-never-blocks-other-work`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Separate autonomous source progress from owner-only hardware proof. Build an explicit blocker/owner-action model where a missing phone, ear, eye, SIM, tag, or peer device yields BLOCKED/NOT TESTED while independent implementation, tests, and documentation continue.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/beta-finalization/WORK-QUEUE.md`, `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`, `docs/beta-finalization/live/DEPLOYMENTS.md`, `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json`, `docs/beta-finalization/workqueue/`, `tools/beta/tests/test_workqueue.py`, and the manual-proof docs under `docs/beta-finalization/manual-proof/`. The repository already distinguishes owner tests but workqueue records show verdicts can remain null.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns work-item states, owner-action requests, blocker taxonomy, dependency rules, and reporting. Does not own each feature implementation. No fake completion and no hard block on unrelated work.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define states that distinguish SOURCE/BUILD/VM/DEPLOYED/OWNER_PROOF/BLOCKED/NOT_TESTED and the allowed transitions.
2. Add dependency rules so an owner-only step does not block sibling source tasks unless the dependency is truly required.
3. Generate an owner-action packet with exact steps, expected observation, stop condition, and PASS/FAIL/NA fields.
4. Implement a workqueue validator that rejects DONE without required evidence and keeps missing owner proof visible.
5. Test a scenario with no phone: unrelated tasks proceed, hardware tasks stay BLOCKED, and the report is truthful.
6. Add a resume path so an interrupted owner test can be completed without restarting all work.
7. Document how to close a BLOCKED item when evidence arrives.

## Failure modes and diagnostics
- Watch for a single 'blocked' state that stalls everything, null verdicts treated as success, and owner instructions that assume a specific host path or phone serial. Keep dependency edges minimal and explicit.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. An owner-only test does not prevent independent source tasks from progressing.
2. A hardware task with no owner evidence remains BLOCKED/NOT TESTED, not DONE.
3. The owner-action packet is copy-pasteable and records expected/actual/PASS-FAIL.
4. The workqueue validator rejects completion without required evidence.
5. A no-phone run still produces useful, correctly labeled progress.
6. Interrupted owner tests can resume from the last checkpoint.
7. The report clearly separates autonomous progress from owner verified results.

## Hardware, privilege and rollback safety
Do not pressure the owner to perform destructive tests or flash. No fabricated owner feedback. Preserve manual-proof evidence.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r55-manual-proof-never-blocks-other-work`, with tests and docs for this component only.
- `docs/component-reports/r55.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop only the genuinely dependent task; continue unrelated work and report the owner request.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
