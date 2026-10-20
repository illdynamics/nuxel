# NUXEL R53 — Autonomous reboot policy
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r53-autonomous-reboot-policy`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Create a bounded autonomous reboot policy for Nuxel agents: define when a reboot is allowed, battery/USB/rescue prerequisites, pre/post evidence, retry limits, cooldowns, and refusal conditions. An agent request is not sufficient approval for an unsafe reboot.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/buttons/reboot-gate.json`, `configs/nuxel/touch/nuxel-bootmode-reboot.service`, `configs/nuxel/bootmode/bootmode-guard.json`, `configs/nuxel/touch/nuxel-bootmode-guard.service`, `tools/s10plus/a33/nuxel-bootmode-guard.py`, `tools/s10plus/a33/nuxel-reboot-mode.sh`, `docs/beta-finalization/release/REBOOT-ROLLBACK.md`, and `boot/s10plus/recovery.sh`. Gates and scripts exist; the policy must be enforceable and testable.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns reboot prerequisites, approval/audit, retry/cooldown, pre/post evidence, and refusal semantics. Does not own the power menu UI. No reboot when rollback/USB recovery is unavailable and no reboot loop.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define policy fields: minimum battery, charger/USB state, target boot mode, rollback artifact, pre/post evidence set, max attempts, cooldown, and owner-approval requirement.
2. Implement a gate evaluator that returns ALLOW/REFUSE with the exact failing prerequisite.
3. Capture pre-reboot state and schedule one post-reboot verification with a unique run ID.
4. Enforce max attempts and stop permanently after the configured failure threshold.
5. Handle charger/LPM boot and ensure the next boot is intended to return to Nuxel.
6. Test low battery, no USB, missing rollback, failed preflight, and repeated-failure scenarios with mocks.
7. Document the emergency recovery path and owner override with audit.

## Failure modes and diagnostics
- Watch for a policy that checks battery percent without checking charger state, a rollback file that is never validated, and a post-reboot script that repeats the reboot on failure. Charger mode can return with input disabled.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The policy returns ALLOW only when every prerequisite is satisfied; otherwise it names the refusal.
2. A simulated low-battery/no-rollback/no-USB case refuses the reboot.
3. Max-attempt/cooldown rules prevent reboot storms.
4. Pre/post evidence is captured and linked by one run ID.
5. The policy cannot be bypassed by a plain `systemctl reboot` from an agent without the gate check (or the bypass is documented as an owner-only action).
6. Recovery/USB availability is checked before reboot.
7. Real reboots are owner-approved and labeled separately from mock policy tests.

## Hardware, privilege and rollback safety
A reboot is a live-device action. Never loop reboots. No flash/kernel changes. Preserve USB recovery and rollback artifacts.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r53-autonomous-reboot-policy`, with tests and docs for this component only.
- `docs/component-reports/r53.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the rollback artifact or rescue path is unverified. Refusal is the correct outcome.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
