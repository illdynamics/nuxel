# NUXEL R11 — Complete the full Fedora userspace
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r11-full-fedora-userspace`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Complete and audit the Fedora ARM64 userspace required by Nuxel: packages, RPM services, D-Bus policy, users/groups, locales, SELinux/AppArmor posture, system configuration, updates, and mobile components. The branch must replace brittle missing-dependency assumptions with an explicit manifest and clean-install smoke checks, without turning the phone image into an indiscriminate package dump.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `images/s10plus/packages-manifest.json`, `images/config/packages.yml`, `images/s10plus/build-phone-rootfs-fedora.sh`, `configs/dbus/`, `configs/apparmor.d/`, `configs/hardened-malloc.conf`, `services/`, and `docs/architecture.md`. Existing manifests and unit files show intended components, but an installed RPM is not proof that its service, D-Bus name, or user-facing feature works.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the package/service/user/config dependency inventory and clean-install validation. Does not own each subsystem's hardware behaviour. No Android runtime, no mandatory cloud account, and no unverified third-party repository.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Build an inventory of every expected package, binary, systemd unit, D-Bus name, user/group, directory, and config file referenced by Nuxel source and units.
2. Diff that inventory against `packages-manifest.json`/`packages.yml` and flag missing providers, duplicate packages, retired names, and packages pulled only transitively.
3. Audit Fedora ARM64 availability and repository provenance for every required package; pin or document versions that can break the image.
4. Validate users, groups, ownership, modes, tmpfiles, polkit rules, AppArmor/SELinux policy, locales, timezone, and machine-id handling in a clean rootfs.
5. Add a clean-install smoke test that starts the minimal Nuxel service set and verifies D-Bus/HTTP readiness without requiring a phone.
6. Separate optional desktop/app packages from boot-critical ones and document the minimal supported image.
7. Add removal/upgrade behaviour checks so an updated package cannot silently delete a required config or service.

## Failure modes and diagnostics
- Watch for packages that exist only in x86_64, renamed Fedora subpackages, services enabled but unable to resolve users, `/usr/lib` vs `/usr/lib64` path assumptions, and configs shipped by RPM that conflict with Nuxel-owned files.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every required binary/unit/config in the inventory has a named provider and appears in the manifest.
2. A clean ARM64 rootfs can install the manifest transaction without unresolved dependencies.
3. Required users/groups, directories, modes, and D-Bus policies exist after installation.
4. The minimal service set starts and reaches its readiness probe in a VM/container or equivalent clean environment.
5. No boot-critical component depends on an optional app, cloud account, Android API, or unpinned external repository.
6. Upgrade/removal simulation preserves Nuxel-owned config and reports conflicts instead of overwriting silently.
7. The report distinguishes installed, configured, started, and functionally verified states.

## Hardware, privilege and rollback safety
No live-phone requirement. Do not install from untrusted repositories, disable SELinux/AppArmor to make a service start, or grant broad sudo as a shortcut. Preserve a reproducible manifest and rollback.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r11-full-fedora-userspace`, with tests and docs for this component only.
- `docs/component-reports/r11.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a required package has no trustworthy ARM64/Fedora source. Report BLOCKED_EXTERNAL_RESOURCE instead of adding a random COPR or vendored binary.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
