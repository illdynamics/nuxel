# NUXEL R51 — Security threat model and enforcement proof
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r51-threat-model-enforcement-proof`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Produce a Nuxel threat model for boot trust, unlock, USB/console, apps, supply chain, remote access, secrets, updates, and physical access, and prove each advertised mitigation links to code or executable evidence. Record residual trust assumptions and unsupported mechanisms honestly.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/architecture.md`, `images/config/verity.conf`, `configs/nuxel/security/README.md`, `configs/nuxel/security/privacy-config.json`, `configs/nftables/`, `configs/apparmor/`, `configs/hardened-malloc.conf`, `configs/dbus/`, `services/nuxel-console/`, and `docs/beta-finalization/release/ROLLBACK.md`. Hardening configs exist; enforcement must be demonstrated.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the threat model, asset/trust-boundary inventory, mitigation-to-evidence map, and residual-risk register. Does not own every implementation fix. No green checklist without executable evidence.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define assets, adversaries, trust boundaries, and attack surfaces for boot, recovery, USB, console, apps, updates, radios, and secrets.
2. Map each claimed mitigation to a code path/command/test and mark it ENFORCED, CONFIGURED_NOT_VERIFIED, or ABSENT.
3. Verify boot integrity/verity, signed artifacts, update provenance, LSM enforcement, firewall, sandbox, and privilege boundaries where claimed.
4. Analyze the USB/live-console path as a privileged surface, including authentication and recovery.
5. Add executable checks/fixtures for the most important mitigations.
6. Record residual risks and unsupported trust assumptions (e.g., vendor kernel/firmware, unlocked bootloader).
7. Produce a machine-readable mitigation matrix plus a human report.

## Failure modes and diagnostics
- Watch for AppArmor profiles in complain mode, SELinux permissive, verity configured but not active, unsigned local update paths, and a console service that bypasses firewall/polkit. Verify runtime state.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The model covers assets, adversaries, boundaries, and the USB/console/update paths.
2. Every advertised mitigation links to code or a command/test and has an enforcement status.
3. A configured-but-not-enforced control is not marked ENFORCED.
4. Boot/update/sandbox/firewall claims are tested or marked UNKNOWN.
5. Residual risks and vendor/firmware trust assumptions are explicit.
6. At least one negative test proves a claimed boundary denies unauthorized access.
7. The report does not equate source presence with runtime enforcement.

## Hardware, privilege and rollback safety
Read-only analysis and fixtures by default. Do not weaken controls to make a test pass. No secret exposure in the threat model.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r51-threat-model-enforcement-proof`, with tests and docs for this component only.
- `docs/component-reports/r51.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a claimed mitigation cannot be observed; report UNKNOWN/ABSENT rather than assuming enforcement.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
