# NUXEL R19 — Display, camera cutouts and status bar
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r19-display-cutouts-status-bar`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make the S10+ cutout/safe-zone geometry, status bar, notification area, Quick Settings, OSK, and dock z-order correct at the real panel resolution and orientation. This branch must remove overlaps and duplicate indicators, preserve touch hit targets, and keep safe zones deterministic across profiles.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/statusbar-safezones.json`, `docs/beta-finalization/launcher/SAFE-ZONES.md`, `configs/s10plus/display/nuxel-s10plus-display.sh`, `pwa/nuxel-home/js/safe-zones.js`, `pwa/nuxel-home/js/status-bar.js`, `pwa/nuxel-home/css/status-bar.css`, `tools/s10plus/a32/tests/safe-zones-test.js`, and `tools/s10plus/a33/nuxel-wl-fb.c`. The safe-zone profile named `s10plus` currently marks portrait zones 9/10; verify against the real cutout rather than assuming the profile is correct.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns safe-zone profiles, status/notification bar layout, battery/Wi-Fi indicator placement, Quick Settings header, OSK/dock stacking, and geometry tests. Does not own the Wi-Fi backend, battery backend, or keyboard input protocol. No arbitrary CSS padding that ignores measured cutout geometry.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Measure the active panel resolution, scale factor, and cutout position from runtime evidence and compare them with the `s10plus` profile.
2. Build a geometry map for status bar items, notification area, Quick Settings header, OSK, dock, and gesture edges with minimum touch target sizes.
3. Fix duplicate Wi-Fi/battery indicators and ensure no indicator overlaps the cutout or another item.
4. Verify portrait and supported landscape mappings, including hit targets after transforms.
5. Test OSK open/close and dock/app layers so no element covers or steals touches from the other.
6. Add deterministic geometry tests for each profile and a screenshot/overlay debug mode.
7. Confirm changes in the active webroot and service-worker cache, not only source.

## Failure modes and diagnostics
- Watch for a safe-zone profile applied twice, CSS `env(safe-area-inset-*)` in a WebKit build that does not provide it, duplicate status modules, and the keyboard resizing the viewport twice. Verify scaling from the actual Wayland output.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The runtime panel resolution/scale matches the documented geometry basis.
2. No status/notification item overlaps the cutout or another indicator in portrait or supported landscape.
3. Each indicator has a distinct, truthful data source and no duplicate Wi-Fi/battery icon appears.
4. Touch hit targets remain at least the documented minimum and map correctly after rotation.
5. Quick Settings, OSK, dock, and app content have a defined z-order with no invisible touch blocker.
6. Safe-zone tests pass for all profiles and a deliberate geometry regression is detected.
7. The owner-visible layout is checked against a captured phone screenshot, separately from CSS tests.

## Hardware, privilege and rollback safety
Do not change panel drivers or display timing for a layout fix. Keep the display bridge single-owner. Userspace-only rollback and no flash.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r19-display-cutouts-status-bar`, with tests and docs for this component only.
- `docs/component-reports/r19.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if cutout geometry cannot be measured reliably. Do not guess padding from a generic phone template; report the missing measurement.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
