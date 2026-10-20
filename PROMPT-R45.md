# NUXEL R45 — Root/sudo control app
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r45-root-sudo-control-app`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement a root/sudo control surface using real sudoers/polkit boundaries, time-limited authorization, explicit prompts, and audit. The app must not grant privilege from UI confirmation alone, must not expose a generic root shell, and must preserve the existing recovery workflow.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-apps/rootcontrol/app.json`, `pwa/nuxel-apps/rootcontrol/index.html`, `pwa/nuxel-apps/rootcontrol/tests/test-privilege-model.js`, `services/nuxel-console/`, `configs/nftables/nuxel-console-guard.nft`, `configs/apparmor.d/usr.bin.nuxel-permd`, and `configs/nuxel/security/remote-access.json`. The app declares `system:inspect`; privileged action design and current sudo/polkit policy must be inspected.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the privilege-request model, allowed actions, authorization prompts, audit, and UI state. Does not own a root shell or arbitrary command execution. No credential caching that outlives the authorization window.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Inventory current sudoers/polkit rules and identify which privileged actions the app actually needs.
2. Replace any UI-only authorization with a real polkit/sudo broker decision tied to the user/session.
3. Define a narrow action allowlist with explicit arguments, time limits, and one-shot grants where possible.
4. Implement confirmation, denial, expiry, audit, and revocation paths.
5. Ensure the app cannot read/store the user's password or a root token in web storage.
6. Test unauthorized user, denied polkit prompt, expired grant, malformed action, and concurrent requests.
7. Document and preserve the USB/recovery path if the privilege service fails.

## Failure modes and diagnostics
- Watch for a web page that calls a helper running as root with a command string, polkit rules that allow any action for the active user, and a UI 'remember me' that effectively grants permanent root. Verify the actual D-Bus/polkit policy.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. No privileged action executes based only on a UI confirmation.
2. Each action maps to a real sudoers/polkit rule and an auditable request/decision.
3. Authorization expires and cannot be replayed beyond its window.
4. The app cannot execute arbitrary commands or open a generic root shell.
5. Password/token material is not stored in web storage or logs.
6. Denied/expired/malformed requests fail closed.
7. Recovery access remains available if the privilege service stops.

## Hardware, privilege and rollback safety
Do not add a broad root helper or disable polkit/AppArmor. Privileged tests use isolated fixtures. No partition/flash changes.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r45-root-sudo-control-app`, with tests and docs for this component only.
- `docs/component-reports/r45.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a needed action cannot be mediated safely. Report the missing policy design instead of adding a root backdoor.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
