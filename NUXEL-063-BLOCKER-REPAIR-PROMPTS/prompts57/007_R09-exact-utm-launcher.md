# NUXEL R09 — Exact UTM launcher — no substitutes
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r09-exact-utm-launcher`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make the shipping launcher match the exact UTM/reference launcher defined by the repository, rather than inventing a new design. This branch must compare geometry, artwork, icon grid, dock, app drawer, search, status bar, orientation, and keyboard handoff against the project's own reference material and correct only verified deviations.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/s10plus-autonomous-boot-repair/UTM-LAUNCHER-PORT/`, `pwa/nuxel-home/index.html`, `pwa/nuxel-home/css/style.css`, `pwa/nuxel-home/css/launcher.css`, `pwa/nuxel-home/js/launcher.js`, `pwa/nuxel-home/js/layout-model.js`, `pwa/nuxel-home/js/apps.js`, and the original assets under `assets/` and `pwa/nuxel-home/assets/`. The repository also has VM/UTM bootstrap material under `vm/`; use it as reference evidence, not as proof of current phone rendering.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns launcher visual fidelity, layout constants, grid/dock geometry, reference comparisons, and runtime use of existing launcher/compositor interfaces. Does not own a new launcher, a different shell, or hardware bring-up. No arbitrary redesign or replacement artwork.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Locate and hash the authoritative UTM launcher/reference assets and identify exactly which source files produce the shipping launcher.
2. Build a fidelity checklist for screen aspect, safe zones, icon counts/sizes, grid gaps, dock height, search placement, page indicators, status bar, and app-drawer behaviour.
3. Capture the current launcher at the S10+ viewport and compare geometry/pixels with the references; classify each difference as intentional, stale, or bug.
4. Fix layering, scaling, spacing, and asset selection only where the reference and current contract disagree.
5. Verify all four dock slots, desktop paging, app drawer, search, Recents, Home, and keyboard open/close at the reference geometry.
6. Add deterministic layout tests for key rectangles and a screenshot comparison procedure that tolerates only declared rendering differences.
7. Document any intentional deviation with owner approval rather than silently "improving" the design.

## Failure modes and diagnostics
- Common causes: stale CSS overrides, assets copied to both `/assets` and `/pwa/...`, fractional CSS scaling on the phone panel, safe-zone profiles applied twice, and a service-worker cache pinning an older launcher. Verify the active webroot and cache before changing layout.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The authoritative reference files and their hashes are named; no competing launcher source is introduced.
2. Viewport-safe layout matches the reference for the S10+ portrait resolution within stated tolerances.
3. Dock, icon grid, search, page indicators, and status bar have verified non-overlapping geometry.
4. All launcher actions still work after fidelity changes: launch, Home, Back, Recents, app drawer, search, page switch.
5. The two dock backgrounds BG1/BG2 still select correctly and BG2 remains the default where configured.
6. A screenshot or geometry test detects a deliberate 10 px layout regression.
7. Any reference ambiguity is reported as an owner decision, not filled with a guessed design.

## Hardware, privilege and rollback safety
Do not replace the launcher or compositor. Preserve working navigation, touch handling, and existing app registry. Deployment remains userspace-only and needs rollback backups.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r09-exact-utm-launcher`, with tests and docs for this component only.
- `docs/component-reports/r09.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the reference material is contradictory or missing; ask for the exact reference build. Do not invent pixel geometry from a screenshots-only guess and call it exact.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
