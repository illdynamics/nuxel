# NUXEL R54 — Reliable autonomous rollback
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r54-reliable-autonomous-rollback`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement reliable userspace rollback for Nuxel deployments: staged/hash-verified artifacts, last-known-good releases, health probes, watchdog rollback, and power-loss recovery. Normal rollback must not flash or write partitions.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/beta-finalization/release/ROLLBACK.md`, `docs/beta-finalization/release/REBOOT-ROLLBACK.md`, `images/build-ota.sh`, `boot/s10plus/recovery.sh`, `tools/beta/live/`, `tools/beta/tests/test-rollback-reboot.sh`, and `docs/beta-finalization/live/DEPLOYMENTS.md`. Rollback documentation and tests exist; a real interrupted deployment/rollback path needs proof.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns deployment receipts, last-known-good metadata, atomic activation, health checks, watchdog decision, and rollback receipts. Does not own OTA image signing beyond the interface used. No rollback that overwrites an unverified backup.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define a deployment transaction with staged files, hashes, metadata, activation marker, and last-known-good pointer.
2. Implement power-loss-safe state transitions (prepare -> activate -> verify -> commit/rollback) using atomic rename.
3. Add health probes appropriate to the deployed component and a watchdog that triggers rollback on failed readiness.
4. Verify rollback restores exact prior hashes, permissions, service state, and config, not a reconstructed approximation.
5. Test interruption at each phase, corrupt staged file, failed probe, and repeated rollback failure.
6. Prevent rollback from writing boot/partition/radio data and preserve the USB console.
7. Record a machine-readable rollback receipt and last-known-good version.

## Failure modes and diagnostics
- Watch for backup files created after overwrite, non-atomic copies, health checks that pass while the old process is still running, and service-manager state not restored. Verify with hashes and probes.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. A deployment is only marked committed after all staged hashes and health probes pass.
2. Interruption at every phase leaves either the old known-good state or a deterministic recovery path.
3. Automatic rollback restores exact hashes/permissions/config and service readiness.
4. A corrupt backup is detected and refused, not installed.
5. Repeated rollback failure stops and reports instead of thrashing.
6. No rollback path touches bootloader/partitions/radio firmware.
7. A real rollback or an equivalent controlled fixture proves the transaction state machine.

## Hardware, privilege and rollback safety
No flashing or partition writes. Preserve rescue/USB access. Do not delete the previous known-good copy until the new state is verified.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r54-reliable-autonomous-rollback`, with tests and docs for this component only.
- `docs/component-reports/r54.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a power-loss-safe transaction cannot be implemented for a path. Report the component as non-atomic rather than claiming reliability.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
