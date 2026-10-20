# NUXEL R48 — Sensible Settings completion
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r48-sensible-settings-completion`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Complete the Settings app around real backends and persistence: Wi-Fi, audio, power, Bluetooth, display, keyboard, privacy, accessibility, Home layout, and app permissions. Remove decorative/dead controls and make each visible control read/write the same service/config the rest of the system uses.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-apps/settings/`, `pwa/nuxel-apps/settings/settings-model.js`, `pwa/nuxel-apps/settings/settings.js`, `pwa/nuxel-apps/settings/wifi-settings.js`, `pwa/nuxel-apps/settings/power-menu.js`, `pwa/nuxel-home/js/settings-store.js`, `configs/nuxel/buttons/settings-surface.json` where present, and the per-subsystem configs under `configs/nuxel/`. The app is the shared Settings surface but several backends are still OFFLINE_TESTED/IMPLEMENTED_NOT_DEPLOYED.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns Settings information architecture, backend bindings, persistence, validation, error states, and accessibility. Does not own each subsystem's driver. No decorative toggle and no local-only state that disagrees with the service.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Inventory every Settings row and map it to a backend API/config/state source.
2. Remove or mark dead controls; add real validation and error feedback for each write.
3. Verify persistence across reload/restart for Wi-Fi, audio, power profile, Bluetooth, display, keyboard, privacy, and Home layout.
4. Handle unavailable hardware/permission denial by disabling or labeling the row truthfully.
5. Test rapid toggles, service failure, stale state, and conflicting changes from another surface.
6. Add accessibility labels, focus order, touch target sizes, and scroll behavior.
7. Run an end-to-end owner test across each settings category.

## Failure modes and diagnostics
- Watch for a settings model that writes only localStorage, duplicate Wi-Fi controls, a power profile that says applied before the governor changes, and a keyboard setting with no applier. Verify the backend after each write.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every visible Settings control maps to a real backend and has a documented effect.
2. Unavailable/denied features are disabled or labeled, not silently accepted.
3. Settings persist across reload and restart and match the service/config source of truth.
4. A service/write failure is shown to the user and does not leave a false toggle state.
5. Concurrent changes from the console or Quick Settings do not diverge.
6. Accessibility labels/focus/touch targets are verified.
7. The report lists each setting as VERIFIED, OFFLINE-TESTED, or BLOCKED.

## Hardware, privilege and rollback safety
Do not grant broad privilege or fake a successful setting. Preserve user preferences during migration. No hardware write without confirmation.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r48-sensible-settings-completion`, with tests and docs for this component only.
- `docs/component-reports/r48.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a setting cannot be bound to a real backend; remove/mark it instead of pretending.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
