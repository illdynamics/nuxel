# NUXEL P11 — Durable evidence and truthful checkpoint
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/p11-durable-evidence-checkpoint`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Create an append-only, machine-checkable evidence model for Nuxel work. This branch must make every deployment, test, reboot, owner interaction, and rollback reconstructable from commit/tree state, target identity, hashes, commands, exit codes, timestamps, service state, and raw logs, without allowing a mock or a service-active state to be promoted into physical proof.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/beta-finalization/live/BASELINE-CAPTURE.md`, `docs/beta-finalization/live/DEPLOYMENTS.md`, `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json`, `docs/beta-finalization/release/evidence/`, `tools/beta/live/nuxel_live.py`, `tools/beta/tests/test_workqueue.py`, and `tools/beta/live/tests/test_live_lib.py`. Existing evidence directories show both useful raw captures and the historical `apply:false`/`results:[]` failure mode that must never be counted as deployment.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the evidence schema, checkpoint writer, hash/receipt conventions, append-only history, and reporting validator. Does not own the actual subsystem implementation or decide that a component works; it records and validates what was observed.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define a versioned JSON schema for evidence records covering source SHA, dirty-tree status, target model/variant, boot mode, deployment plan hash, per-file before/after hashes, commands, exit codes, durations, service states, raw log paths, owner observation, and rollback receipt.
2. Implement an append-only checkpoint writer with monotonic timestamps, unique run IDs, and atomic rename so interruption cannot corrupt prior history.
3. Add a validator that rejects a record claiming OWNER-VERIFIED without an owner observation field and rejects LIVE-DEVICE DEPLOYED when `apply` is false or results are empty.
4. Integrate the writer with the existing live deployment and test harness at clean boundaries without changing their safety semantics.
5. Add redaction for credentials, IMEI/IMSI/ICCID, SSIDs, tokens, and personal identifiers before any evidence is committed.
6. Add query/report commands that reconstruct the latest known-good state per component and show contradictory or missing evidence.
7. Exercise corruption, truncated JSON, duplicate run IDs, clock regression, and interrupted-write cases.

## Failure modes and diagnostics
- Watch for clock/timezone ambiguity, branch ambiguity, dirty working trees, reused run IDs, evidence copied from an archive without its source commit, redaction applied after logs are written, and records that treat `systemctl is-active` as proof of user-visible behaviour.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The schema is documented and validated by a test with valid and invalid fixtures.
2. Every deployment record includes `apply:true`, non-empty results, per-file hashes, and a rollback reference before it can claim DEPLOYED.
3. A mock/test result cannot acquire the OWNER-VERIFIED or LIVE-DEVICE DEPLOYED label through any schema or validator path.
4. Append-only history survives an interrupted write and a duplicate-ID attempt.
5. A reviewer can reconstruct the exact deployed file hashes, service state, and rollback commands from the record alone.
6. Secrets and personal identifiers are absent from committed evidence in a redaction test.
7. A report command lists stale, contradictory, and missing evidence instead of silently choosing one.

## Hardware, privilege and rollback safety
Evidence collection must be read-only on the phone by default. Do not include live secrets or unsanitized logs in Git. Do not make evidence writing depend on network access or a single host path.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/p11-durable-evidence-checkpoint`, with tests and docs for this component only.
- `docs/component-reports/p11.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if evidence cannot identify the source commit or target unit. Do not backfill a claimed observation. Report missing evidence as NOT TESTED rather than manufacturing a checkpoint.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
