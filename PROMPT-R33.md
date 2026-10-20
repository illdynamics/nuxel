# NUXEL R33 — Live console — full phone application and control center
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r33-live-console-control-center`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Turn the live console into a bounded, authenticated phone control center for processes, units, logs, health, diagnostics, and file transfer without becoming an unauthenticated root backdoor. This branch owns read-only versus privileged actions, session ownership, log bounds, and recovery-safe behaviour.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `services/nuxel-console/README.md`, `services/nuxel-console/bin/nuxel-console-free`, `services/nuxel-console/systemd/nuxel-console.service`, `services/nuxel-console/test-console-ownership.py`, `configs/nftables/nuxel-console-guard.nft`, `configs/nuxel/security/remote-access.json`, `pwa/nuxel-home/js/app.js`, and `tools/s10plus/a33/nuxel-console.c`. The current service and guard exist; authentication/privilege boundaries and UI control paths must be verified rather than assumed.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns console ownership, command allowlist, privilege separation, log streaming bounds, session authentication, and the control-center UI. Does not own SSH/Zerotier or every subsystem's diagnostic tool. No unauthenticated listener, no arbitrary root shell, and no console action that can strand the USB recovery path.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Inventory every console command/action and classify it READ_ONLY, PRIVILEGED, or FORBIDDEN.
2. Enforce a single console owner/session lock and an allowlist; reject arbitrary shell/root execution from the web UI.
3. Add authentication/authorization and CSRF/origin protections for any network-exposed control surface.
4. Bound log/process output and stream it without freezing the UI or exhausting memory.
5. Add a health view sourced from real units/processes/capability probes, with clear UNKNOWN/FAILED states.
6. Test reconnect, concurrent session, malformed command, timeout, and service restart.
7. Prove the USB recovery console remains reachable after every console action tested.

## Failure modes and diagnostics
- Watch for a web endpoint that shells out with user input, a wide `nuxel-console-free` allowlist, missing origin checks, and log streaming that backpressures the entire phone. The console is powerful; default to read-only.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Only one console owner can hold the control session at a time.
2. The web UI cannot execute an arbitrary command outside the documented allowlist.
3. Privileged actions require an explicit authorization path and are audited.
4. Log/process streaming is bounded and the UI remains responsive under a large output.
5. Health status reflects real probes and does not report OPTIMAL from a static list.
6. Concurrent/unauthorized/malformed requests are refused.
7. A recovery/USB path remains available after console operations.

## Hardware, privilege and rollback safety
Do not expose the console on an untrusted network without authentication. No arbitrary root action. Preserve USB console recovery and audit privileged changes.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r33-live-console-control-center`, with tests and docs for this component only.
- `docs/component-reports/r33.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the console currently exposes an unauthenticated privileged surface; that is a security blocker to fix before adding controls. Do not paper over it with UI hiding.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
