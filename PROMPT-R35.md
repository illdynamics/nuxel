# NUXEL R35 — DEVMGMT — Linux power-user application
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r35-devmgmt-linux-power-user`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement DEVMGMT as a scoped power-user app for packages, processes, services, devices, logs, and diagnostics, built on the existing console/portal rather than a second privilege daemon. The branch must define authorization, command provenance, output parsers, and recovery-safe actions.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-apps/devmgmt/app.json`, `pwa/nuxel-apps/devmgmt/index.html`, `pwa/nuxel-apps/devmgmt/tests/test-parsers.js`, `pwa/nuxel-apps/_shared/sysinfo.js`, `pwa/nuxel-home/js/system-monitor.js`, `services/nuxel-console/`, and `configs/nuxel/security/remote-access.json`. The app declares `system:inspect`; provider/authorization paths must be checked end to end.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns DEVMGMT feature scope, parser tests, read-only diagnostics, and authorized actions. Does not own a second terminal/daemon, and must not grant broad root. No command injection and no destructive action without explicit confirmation and rollback.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Inventory DEVMGMT features and map each to an existing read API or authorized console action.
2. Define a command allowlist and structured output parsers for packages, units, processes, devices, and logs.
3. Implement read-only views first: system info, failed units, top processes, storage, network, and recent logs.
4. Add privileged actions one at a time with confirmation, audit, timeout, and refusal when no authorization path exists.
5. Prevent command injection by using argument arrays/structured RPC, never shell string concatenation from user input.
6. Test parser edge cases, empty output, permission denied, timeout, and large output.
7. Verify the UI remains usable on a phone viewport and does not freeze while collecting data.

## Failure modes and diagnostics
- Watch for shelling out with `exec(userInput)`, parsing human output without locale pinning, duplicate system-monitor polling, and a privileged action that reports success from an exit code while producing no effect. Verify the phone's actual process/unit names.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every DEVMGMT feature maps to a real provider and authorization decision.
2. Read-only views return real system data with clear UNKNOWN/ERROR states.
3. No user-controlled string reaches a shell unescaped.
4. Privileged actions require explicit authorization and are audited.
5. Timeout/permission-denied/large-output cases are handled without UI lockup.
6. No second daemon or duplicate terminal is introduced.
7. The app remains usable in the phone viewport and has an honest offline/no-console state.

## Hardware, privilege and rollback safety
Do not add a root helper with broad commands. Reuse the console/portal authorization boundary. Destructive actions (kill/remove/restart) need confirmation and recovery-safe scope.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r35-devmgmt-linux-power-user`, with tests and docs for this component only.
- `docs/component-reports/r35.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a feature requires unmediated root or would let the UI kill essential services. Report the missing authorization design instead of adding a privileged backdoor.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
