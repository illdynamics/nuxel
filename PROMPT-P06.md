# NUXEL P06 — Repair current hard-red regression gates
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/p06-hard-red-regression-gates`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Restore trustworthy regression signal for Nuxel. This branch must inventory every hard-red gate in CI, host tests, smoke tests, boot-image checks, and release tooling; classify each as a genuine regression, an obsolete assertion, or a missing prerequisite; and repair the gate without weakening it. The deliverable is a reproducible before/after matrix and a protected set of boot, input, recovery, and release checks that future branches cannot quietly skip.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `tools/beta/run-all-tests.sh`, `tools/beta/tests/test-regression-guard.sh`, `tools/beta/tests/test-release-tools.sh`, `tools/beta/tests/test-rollback-reboot.sh`, `boot/s10plus/tests/test-boot-image-gates.sh`, `.github/workflows/release.yml`, and the release evidence under `docs/beta-finalization/release/evidence/gate-20261016T214620+0200/`. The repo contains previous RAW-VERDICTS/JSON gate records, but a recorded failure is historical evidence and must be reproduced at the execution commit before being classified.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns test discovery, gate classification, CI invocation, fail/skip policy, and the machine-readable gate matrix. Does not own product fixes for unrelated components; file a blocker instead of hiding their failures. Do not rewrite tests merely to match current output unless the assertion is proven obsolete against a documented contract.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Capture the current baseline by running `bash tools/beta/run-all-tests.sh` and each individually named gate, saving stdout, stderr, exit code, duration, commit SHA, and environment.
2. Enumerate CI jobs from `.github/workflows/release.yml` and map each job to a local command and the source contract it protects.
3. Classify every red gate as REGRESSION, OBSOLETE_ASSERTION, MISSING_DEPENDENCY, ENVIRONMENT_BLOCKED, or FLAKY with evidence and a named owner.
4. Repair real regressions or obsolete assertions in the smallest scope; add a regression test proving the repaired contract.
5. Add a machine-readable gate matrix (`docs/component-reports/p06-gates.json` or equivalent) consumed by `tools/beta/tests/test-regression-guard.sh` so missing/skipped protected gates fail loudly.
6. Run the complete gate set twice from a clean checkout and compare results to detect order dependence and flakiness.
7. Document any unresolved hard failure with the exact first failing assertion and stop; never mark the branch green by skipping it.

## Failure modes and diagnostics
- Common causes to separate: tests assuming `/x/nuxel` or Fedora-only paths, tests requiring a live phone or `git` metadata absent from an archive, stale expected hashes, tests written for the pre-A34 launcher, and scripts that return 0 after a failed subcommand. Inspect pipeline exit status and `set -e` boundaries before changing assertions.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The before/after matrix names every gate, command, prior result, new result, classification, owner, and evidence file.
2. Boot, input, touch, USB-console recovery, rollback, and release-artifact gates remain non-skippable.
3. No test assertion is weakened solely to make CI green; any obsolete assertion has a cited contract change and replacement check.
4. `bash tools/beta/run-all-tests.sh` passes on a clean checkout with no network-dependent surprise or hidden local state.
5. `bash tools/beta/tests/test-regression-guard.sh` fails when a protected gate is deleted, renamed, or skipped.
6. CI uses the same command names and semantics as the local runner, and a missing tool yields a clear BLOCKED result rather than a pass.
7. An unresolved failure is reported explicitly; the branch is not declared complete while a hard-red protected gate remains.

## Hardware, privilege and rollback safety
Gate repair must not require flashing or a live-phone reboot. Any test that touches the phone must be read-only by default and gated behind an explicit owner flag. Preserve evidence and never delete failing logs to make the tree look clean.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/p06-hard-red-regression-gates`, with tests and docs for this component only.
- `docs/component-reports/p06.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a protected gate depends on unavailable hardware or an external service; record BLOCKED_EXTERNAL_RESOURCE with the exact command. Do not silently remove the gate from CI. Stop if repairing a gate would require implementation work owned by another branch.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
