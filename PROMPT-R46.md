# NUXEL R46 — Safe cleanup application
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r46-safe-cleanup-application`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement cleanup of caches, logs, temporary files, and orphaned downloads with preview, quotas, ownership checks, and reversible operations. The app must protect boot artifacts, home layout, journal evidence, app databases, and any path it cannot prove is safe.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-apps/cleanup/app.json`, `pwa/nuxel-apps/cleanup/index.html`, `pwa/nuxel-apps/cleanup/tests/test-cleanup-plan.js`, `docs/beta-finalization/release/ROLLBACK.md`, `docs/beta-finalization/live/DEPLOYMENTS.md`, `images/s10plus/build-phone-rootfs-fedora.sh`, and `configs/nuxel/paths.conf`. The app declares `storage:cleanup`; the planner must be audited against real Nuxel paths.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns cleanup categorization, preview/plan generation, quotas, protected-path denylist, dry run, cancellation, and receipts. Does not own factory reset, package removal, or broad system optimization. No recursive delete outside an allowlisted root.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Build a path inventory from `configs/nuxel/paths.conf` and classify each cleanup candidate as safe, user-confirmed, or protected.
2. Implement a dry-run plan with exact bytes/files, owner, age, reason, and destination.
3. Enforce a hard denylist for boot, kernel, /etc, /usr, app data, permissions, notifications, journal evidence, vaults, and mounted media.
4. Implement quota/age policy, cancellation, and per-item receipts; no wildcard recursive delete.
5. Test symlink traversal, hardlink, open file, permission denied, and a path that resolves outside the allowed root.
6. Verify cleanup never removes active rollback/evidence data or user documents.
7. Provide an undo story for user-confirmed deletions where feasible.

## Failure modes and diagnostics
- Watch for following symlinks, deleting logs currently open by journald, treating `/var/lib/nuxel` as a cache, and clearing service-worker data that holds the only copy of a layout. Preview must resolve real paths.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The dry run lists every candidate and never mutates the filesystem.
2. Protected paths (boot, kernel, /etc, /usr, app data, vaults, journal, mounted media) are refused.
3. Symlink/path traversal cannot escape the allowed cleanup root.
4. A quota/age policy is enforced and cancellation leaves a consistent state.
5. Each deletion has a receipt and the app can explain what was removed.
6. Active rollback/evidence files and user data are preserved.
7. No wildcard `rm -rf` or equivalent unsafe command is reachable from the UI.

## Hardware, privilege and rollback safety
No destructive cleanup during tests except in a disposable fixture root. No format/partition. Preserve rollback and evidence.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r46-safe-cleanup-application`, with tests and docs for this component only.
- `docs/component-reports/r46.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a candidate path cannot be proven safe. Do not add a 'clean everything' mode; report refused paths instead.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
