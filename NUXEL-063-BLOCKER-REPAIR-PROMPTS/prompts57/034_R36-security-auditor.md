# NUXEL R36 — Security auditor
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r36-security-auditor`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Build a read-only-first Nuxel security auditor that checks real permissions, exposed services, updates, LSM/SELinux/AppArmor, firewall, verity/immutability, secrets, and configuration drift. Findings must link to evidence and severity; a green checklist is not hardening.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `tools/s10plus/a33/nuxel-security-audit.sh`, `configs/nuxel/security/README.md`, `configs/nftables/nuxel-firewall-config.json`, `configs/apparmor/systemd/nuxel-apparmor-enforce.service`, `images/config/verity.conf`, `configs/hardened-malloc.conf`, `tools/beta/tests/test-regression-guard.sh`, and the A33 security fixtures under `tools/s10plus/a33/security-fixtures/`. Existing hardening configs exist; activation and effectiveness must be measured.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns audit checks, severity/evidence model, drift detection, and reporting. Does not own silent remediation or broad policy changes. No claim that a config being present means it is enforced.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define audit checks for boot integrity/verity, LSM/AppArmor enforcement, SELinux state, firewall rules, exposed listeners, update provenance, SUID/capabilities, secret files, world-writable paths, and service sandboxing.
2. For each check, use a real command/API and record PASS/FAIL/UNKNOWN plus the raw evidence, not just a summary.
3. Verify AppArmor/SELinux profiles are loaded and denials are observable; distinguish permissive/disabled from enforcing.
4. Audit firewall listeners and exposed services against the remote-access policy; identify any unauthenticated surface.
5. Audit update/package provenance and signature verification where applicable.
6. Add drift comparison against the expected Nuxel baseline and a machine-readable report.
7. Test false-positive/false-negative fixtures and a deliberately disabled control.

## Failure modes and diagnostics
- Watch for `systemctl is-active` used as proof of enforcement, AppArmor profiles in complain mode, firewall rules in a different table, and secret scans that print the secret. Redact sensitive values.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every audit finding links to a command, raw output, severity, and owning component.
2. A present-but-not-loaded AppArmor/SELinux/firewall config is reported as not enforced.
3. Exposed/unauthenticated listeners are identified with address, port, process, and policy decision.
4. Disabled/no-op checks produce UNKNOWN, not PASS.
5. The report is machine-readable and can be diffed for drift.
6. At least one negative fixture proves the auditor detects a disabled security control.
7. The auditor performs no destructive change by default.

## Hardware, privilege and rollback safety
Read-only by default. Remediation is out of scope unless explicitly gated and owner-approved; never weaken a security control to make a check pass. Preserve evidence and privacy.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r36-security-auditor`, with tests and docs for this component only.
- `docs/component-reports/r36.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a check requires privileged intrusive probing or could expose secrets. Report UNKNOWN with the exact missing evidence.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
