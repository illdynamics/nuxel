# NUXEL R17 — Power menu
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r17-power-menu`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Build a trustworthy power menu that uses existing logind/systemd interfaces, has safe defaults, and cannot accidentally reboot, power off, or enter Recovery/Download Mode. This branch owns the menu state machine, selection/navigation, confirmation rules, timeout, and visible/touch/button parity.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/power/power-menu.json`, `configs/nuxel/buttons/reboot-gate.json`, `configs/nuxel/input/button-fsm.json`, `pwa/nuxel-apps/settings/power-menu.js`, `pwa/nuxel-apps/settings/power-menu.html`, `pwa/nuxel-home/js/osd.js`, `tools/s10plus/a33/nuxel-power-diag.sh`, and `configs/nuxel/power/nuxel-power-mode.service`. The current menu includes Recovery and Download Mode entries that are intentionally refused; preserve the refusal, not merely the entry.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns menu entries, selection order, timeout/cancel semantics, confirmation and execution gating. Does not own the button FSM's raw key classification or the display bridge. No bootloader invocation, no Download/Recovery execution, and no reboot without the policy gate.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Validate the menu JSON against the button FSM and settings surface so all consumers read one entry table.
2. Ensure Cancel is first and initially selected; test Up/Down/Select, Back/Home, timeout, and repeated Power.
3. Implement a confirmation step for restart/poweroff with clear wording and a safe default.
4. Hard-refuse Recovery and Download Mode in every execution path and prove no heimdall/odin/fastboot/partition command is reachable.
5. Wire restart/poweroff only through the existing reboot gate and logind/systemd path; test a closed gate.
6. Add a dry-run/action-map test that never executes a destructive action and records what would happen.
7. Verify the menu cannot remain invisible on top of the UI after timeout or an interrupted app surface.

## Failure modes and diagnostics
- Watch for menu state stored in two places, key repeat selecting multiple entries, a stale OSD document, a confirmation auto-accepting on timeout, and button bounce triggering restart. Destructive actions must fail closed.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Cancel is the initial and first entry; Enter/Select on the untouched menu dismisses it.
2. Restart and power-off require explicit confirmation and remain refused when the gate is closed.
3. Recovery and Download Mode are unreachable from automated/touch/keyboard paths.
4. The menu closes on timeout, Back, Home, and a second Power press without dispatching an action.
5. No menu path can invoke flashing, partitioning, or a bootloader interface.
6. A dry run lists every entry's action, gate, and refusal reason.
7. Owner-visible menu navigation is tested separately from unit/FSM tests.

## Hardware, privilege and rollback safety
Poweroff/reboot are live-device actions. Do not execute them during automated tests; use a dry run or mock logind. Keep the USB console and a documented recovery path.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r17-power-menu`, with tests and docs for this component only.
- `docs/component-reports/r17.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a destructive action cannot be gated or confirmed safely. Never test Recovery/Download Mode on hardware. Report a closed gate as a valid outcome, not a bug to bypass.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
