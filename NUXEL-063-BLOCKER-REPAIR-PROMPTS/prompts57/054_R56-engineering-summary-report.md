# NUXEL R56 — Mandatory final report one — engineering summary
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r56-engineering-summary-report`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Generate the mandatory engineering summary from actual Git changes, build/deployment receipts, logs, hashes, target identity, and test evidence. This is a reporting branch: no source feature implementation is required, and performance/physical results must never be invented.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/beta-finalization/BETA-FINALIZATION-ENGINEERING-REPORT.md`, `docs/beta-finalization/release/evidence/gate-20261016T214620+0200/ENGINEERING-REPORT-INPUTS.md`, `docs/architecture.md`, `docs/beta-finalization/live/DEPLOYMENTS.md`, `docs/beta-finalization/WORK-QUEUE.md`, and the evidence directories under `docs/beta-finalization/`. Existing reports provide structure; the new report must be generated from the execution commit, not copied forward.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the engineering report structure, data collection, traceability, and honest status language. Does not own code changes for failed components. No invented metrics, owner observations, or deployment success.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define the report schema/sections: commit/tree, target, scope, changed files, architecture impact, tests, deployment, evidence classes, blockers, rollback, and next actions.
2. Collect data from Git, workqueue records, CI logs, build artifacts, deployment receipts, and test outputs; record the exact source for each claim.
3. Distinguish SOURCE VERIFIED, BUILT, VM VERIFIED, LIVE-DEVICE DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.
4. Include a dependency/blocker table and a list of owner actions that remain outstanding.
5. Generate a machine-readable companion JSON and validate it against the source evidence.
6. Run a consistency check that rejects a claim with no evidence path or a stale commit SHA.
7. Produce a concise executive summary plus detailed appendices.

## Failure modes and diagnostics
- Watch for copying old pass tables, using a stale deployed SHA, claiming CI success without artifact inspection, and omitting failed tests. The report must be reproducible from the evidence set.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every claim links to a commit, command, artifact hash, or evidence file.
2. The report names the exact execution commit/tree and target model/variant.
3. No physical/hardware/perf claim is made without owner/live evidence.
4. Blocked and NOT TESTED items are visible, not omitted.
5. The JSON companion is schema-valid and agrees with the Markdown.
6. Changed files and tests match `git diff`/the actual run.
7. The report can be regenerated after an interruption without duplicating or losing evidence.

## Hardware, privilege and rollback safety
Read-only reporting; do not modify implementation to make the report look better. Redact secrets/personal data. No flash/reboot.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r56-engineering-summary-report`, with tests and docs for this component only.
- `docs/component-reports/r56.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if required evidence is missing; report a gap instead of filling it with narrative.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
