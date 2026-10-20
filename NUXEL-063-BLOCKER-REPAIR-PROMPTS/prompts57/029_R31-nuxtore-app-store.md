# NUXEL R31 — Nuxtore — custom Nuxel app store
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r31-nuxtore-app-store`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make Nuxtore a trustworthy Nuxel app store/catalog rather than an unverified marketplace mirror. This branch must define catalog indexing, provenance/signatures, install/update/remove transactions, dependency handling, permissions, network-failure behaviour, and rollback, grounded in Fedora RPM/Flatpak or an explicitly supported source.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-apps/nuxtore/app.json`, `pwa/nuxel-apps/nuxtore/index.html`, `pwa/nuxel-apps/nuxtore/tests/test-catalog.js`, `pwa/nuxel-apps/nuxtore/tests/test-catalog.py`, `docs/app-store.md`, `docs/architecture.md`, and `images/s10plus/packages-manifest.json`. The current app declares catalog read/install/remove capabilities; a catalog UI existing is not proof of signed packages, atomic install, or rollback.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns catalog schema/indexing, provenance/signature verification, install transaction semantics, update/remove/rollback, and store UX state. Does not own the underlying package manager or arbitrary third-party repositories. No silent unsigned install and no fake catalog success.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define the catalog schema (app id, version, source, hashes, signature/key id, dependencies, permissions, size, compatibility) and validate it before display.
2. Implement provenance verification and refuse unsigned/tampered metadata with a clear error.
3. Implement install/update/remove as staged transactions with lock, free-space check, dependency resolution, atomic activation, and rollback.
4. Handle network loss, interrupted download, disk full, package conflict, signature failure, and cancellation without corrupting the system.
5. Show installed/update/available state from the real package database, not a cached UI guess.
6. Add permission/capability review before install and audit install/remove actions.
7. Test a local fixture catalog and at least one tampered entry in CI.

## Failure modes and diagnostics
- Watch for catalog metadata cached without validation, partial RPM transactions, Flatpak user/system scope confusion, and a store that reports success after downloading but before installing. Never run install commands as an unauthenticated web page.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The catalog schema is documented and invalid/tampered entries are rejected before install.
2. Every install/update has a verified source, hash, and signature/key identity.
3. An interrupted or failed transaction leaves the previous app/system state intact.
4. Remove/update/rollback behaviour is tested with fixtures and reported honestly.
5. UI state follows the real package database and does not show installed when it is not.
6. Permission/capability review occurs before installation.
7. No arbitrary unsigned repository is silently trusted.

## Hardware, privilege and rollback safety
Do not install packages from untrusted sources or grant broad sudo to the store. Use polkit/package-manager mediation. Preserve a rollback path and do not flash/partition.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r31-nuxtore-app-store`, with tests and docs for this component only.
- `docs/component-reports/r31.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if no trustworthy catalog/source exists or if installation needs an unbounded privilege grant. Report BLOCKED_EXTERNAL_RESOURCE instead of inventing a package feed.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
