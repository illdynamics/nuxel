# NUXEL R57 — Mandatory final report two — owner manual test report
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r57-owner-manual-test-report`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Create the separate owner-facing hardware test report and procedure for touch, navigation, keyboard, audio, torch, network, battery, sensors, camera, and reboot. It must capture expected/observed/PASS/FAIL/timestamp and remain NOT TESTED without physical feedback.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`, `docs/beta-finalization/live/LIVE-TOUCH-20261018.md`, `docs/beta-finalization/live/DEPLOYMENTS.md`, `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json`, and the per-area docs under `docs/beta-finalization/manual-proof/`. These provide existing procedures but must be reconciled with the current build and owner evidence.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the owner test plan, step wording, result capture, and report. Does not own implementation fixes. No fabricated PASS and no ambiguous 'looks good' result.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Reconcile the manual-proof checklist with the current feature/capability set and remove obsolete steps.
2. Write short, unambiguous steps for each physical area with expected observation, stop condition, and PASS/FAIL/NA.
3. Include setup prerequisites (boot mode, USB, volume cap, test media/peer/tag/SIM) and safety boundaries.
4. Provide a capture template for timestamp, device build, observed result, and notes.
5. Run the owner test where possible and record exact feedback; otherwise leave NOT TESTED with the request pending.
6. Add a summary matrix per subsystem and a list of blockers/bugs found.
7. Ensure no destructive step (flash/recovery/format) is included.

## Failure modes and diagnostics
- Watch for vague steps ('check audio'), tests that assume a peer/SIM/tag is available, and an overall PASS computed from only the successful rows. Make each step independently executable.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every manual area has a clear expected observation and PASS/FAIL/NA field.
2. The report records build/commit, target, timestamp, and prerequisites per test.
3. No result is marked PASS without owner observation.
4. Blocked/not-run areas remain visible and are not averaged into a misleading overall pass.
5. The instructions do not require flashing, partitioning, or unsafe volume.
6. The summary matrix matches the detailed results.
7. The report distinguishes a software/tooling pass from physical proof.

## Hardware, privilege and rollback safety
Do not ask the owner to perform destructive or high-volume tests. No flash/partition. Preserve privacy in recorded observations.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r57-owner-manual-test-report`, with tests and docs for this component only.
- `docs/component-reports/r57.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a step cannot be made safe or reversible. Leave it NOT TESTED and state why.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
