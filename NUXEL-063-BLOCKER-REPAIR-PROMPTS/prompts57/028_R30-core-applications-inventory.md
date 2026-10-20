# NUXEL R30 — Core applications — required inventory
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r30-core-applications-inventory`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make the required application inventory explicit and verifiable: distinguish registered launcher entries, installed packages, and actually usable GUI apps. This branch must reconcile `docs/beta-finalization/apps/APP-INVENTORY.md`, the app registry, launcher tiles, PWA `app.json` manifests, native shell apps, and the package/image manifests, then prove launch/back/home/recents behavior for each required app.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/beta-finalization/apps/APP-INVENTORY.md`, `configs/nuxel/app-registry/app_registry.json`, `configs/nuxel/app-registry/app-registry.schema.json`, `pwa/nuxel-home/js/apps.js`, `pwa/nuxel-home/js/launcher.js`, `pwa/nuxel-apps/*/app.json`, `shell/nuxel-shell/`, `tools/s10plus/a33/tests/generate-app-inventory.py`, and `tools/s10plus/a32/tests/launcher-registry-test.js`. The registry currently contains native and template entries while the PWA tree contains many app manifests; folder presence is not proof of a working app.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the app inventory schema/parity, launcher registration, missing-dependency reporting, and the per-app launch/lifecycle matrix. Does not own each app's internal feature completeness; record those as separate blockers. No empty placeholder icon counted as an installed app.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Reconcile all app sources into one table: required app, app_id, type, executable/start URL, package provider, icon, launcher entry, permissions, and current status.
2. Add schema/parity validation so an app cannot be registered without a real executable/start URL and icon, or shipped without a registry entry.
3. Classify each app as MISSING_PACKAGE, INSTALLED_NOT_REGISTERED, REGISTERED_NOT_LAUNCHABLE, LAUNCHABLE, or FEATURE_COMPLETE with evidence.
4. Run launch/back/home/recents for every required app and capture the first failure per app.
5. Verify app data directories/permissions and no invisible app surface remains after Home.
6. Remove or clearly mark dead placeholder entries without silently deleting owner data.
7. Generate a machine-readable inventory/report and a CI parity check.
8. Document required apps that depend on blocked hardware separately from missing software.

## Failure modes and diagnostics
- Watch for duplicate app IDs, registry entries pointing to old launcher paths, PWA apps with no `app.json`, native binaries absent from the package manifest, and an app iframe that remains full-screen after Home.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The inventory table covers every required app and every registry entry.
2. Registry/schema validation rejects an entry with no real executable/start URL or icon.
3. No launcher tile points to a missing app without an explicit MISSING marker.
4. Every required app is launched and tested for Back/Home/Recents, or has an exact blocker.
5. No dead duplicate/legacy registry entry remains without an owner decision.
6. App package/data providers and permissions are recorded and truthful.
7. The generated report is reproducible from the current tree.

## Hardware, privilege and rollback safety
Do not install untrusted packages or replace apps with placeholders. Preserve working apps and user data. No live-phone write without rollback.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r30-core-applications-inventory`, with tests and docs for this component only.
- `docs/component-reports/r30.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the required-app list is contradictory; report the exact source conflict. Do not invent an app to fill a tile.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
