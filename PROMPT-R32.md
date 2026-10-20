# NUXEL R32 — Privacy and permission manager
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r32-privacy-permission-manager`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make privacy and permissions enforceable Linux policy, not a decorative settings screen. This branch owns permission definitions, app identity, persistence, audit, revocation, portal/polkit/D-Bus enforcement, and user-visible access indicators for camera, microphone, location, files, notifications, USB, Bluetooth, and network.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/security/privacy-config.json`, `configs/apparmor.d/usr.bin.nuxel-permd`, `configs/apparmor.d/usr.bin.nuxel-permissions`, `configs/dbus/org.nuxel.Portal.conf`, `services/nuxel-portal/src/portal.py`, `services/nuxel-portal/test-portal-policy.py`, `shell/nuxel-shell/nuxel-permissions/`, `shell/nuxel-shell/nuxel-permissions/tests/`, and `configs/nuxel/app-registry/app_registry.json`. A permissions UI exists, but enforcement must be proven at the actual API boundary.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns permission schema/state, app-to-permission mapping, grant/revoke semantics, audit, and portal/AppArmor/polkit enforcement integration. Does not own every app's feature implementation. No Android-style permission theater and no silent ambient access.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Inventory every permission and the kernel/D-Bus/portal/AppArmor boundary that enforces it.
2. Define app identity and a durable permission store with default-deny and explicit user grant/revoke.
3. Wire at least camera, microphone, location, filesystem, notification, network, USB, and Bluetooth requests to the real broker/policy.
4. Add audit records for grant, deny, revoke, and access attempts without logging sensitive content.
5. Test denial, revocation during use, app restart, session restart, and malformed policy.
6. Verify the Permissions UI reads/writes the same store the enforcement layer uses.
7. Prove that bypass attempts through a direct device node/D-Bus call fail according to policy.

## Failure modes and diagnostics
- Watch for permission state stored only in localStorage, portal policy bypassed by direct `/dev/video*`/`/dev/snd` access, and broad AppArmor profiles that grant the very access the UI claims to deny. Verify the actual process/user boundary.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every advertised permission has an identified enforcement boundary and a test.
2. Default-deny applies to apps without a grant.
3. Grant/revoke persists across app and session restart and takes effect without a reboot.
4. A revoked permission stops an in-progress access or the next access attempt, as defined.
5. The Permissions UI and enforcement layer share one state source.
6. Audit records prove allow/deny decisions without leaking content.
7. A direct bypass attempt is denied or reported as a known gap, not silently allowed.

## Hardware, privilege and rollback safety
Do not grant broad sudo/polkit rules as a shortcut. Sensitive permission tests need synthetic fixtures, not real personal data. Preserve user privacy in logs.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r32-privacy-permission-manager`, with tests and docs for this component only.
- `docs/component-reports/r32.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if an advertised permission cannot be enforced at a real boundary; report it as NOT ENFORCED rather than exposing a false toggle.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
