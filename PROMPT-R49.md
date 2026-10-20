# NUXEL R49 — No mandatory Google, Apple or Android services
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r49-no-mandatory-google-apple-android`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Audit and enforce Nuxel independence: build, boot, login, apps, updates, and default services must not require Google, Apple, Android, Play Services, or proprietary cloud accounts. Separate optional interoperability from hard dependencies and provide a Linux/Fedora alternative for every mandatory function.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `docs/architecture.md`, `images/s10plus/packages-manifest.json`, `images/s10plus/build-phone-rootfs-fedora.sh`, `configs/nuxel/app-registry/app_registry.json`, `pwa/nuxel-apps/`, `services/nuxel-bridge/src/capabilities.py`, and `.github/workflows/release.yml`. The project claims no mandatory Android framework; verify the actual package/service/app graph rather than trusting the README.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns dependency audit, default-service/app policy, account/cloud requirements, and independence documentation. Does not own optional user-installed third-party apps. No hidden Google/Apple/Android runtime and no mandatory account for core functions.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Scan packages, services, binaries, scripts, and app manifests for Android runtime/HAL, Play Services, Google account, Apple services, or proprietary SDK dependencies.
2. Classify each dependency as MANDATORY, OPTIONAL, BUILD_ONLY, or ABSENT and name the replacement for mandatory functions.
3. Verify boot/login/network/time/app-install/update paths work without any external account.
4. Audit default app URLs/telemetry calls and remove mandatory cloud endpoints.
5. Add a CI check that fails if a forbidden mandatory dependency is introduced.
6. Test a clean install with networking disabled after setup, and one with an unavailable third-party service.
7. Document optional interoperability clearly.

## Failure modes and diagnostics
- Watch for packages that pull Android libraries transitively, an app registry entry pointing at a cloud-only PWA, and a default update check that phones home. Also distinguish build-time tooling from runtime dependencies.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The dependency report classifies every Google/Apple/Android/proprietary reference found.
2. No core boot/login/network/time/app/update path requires an external account or Android runtime.
3. A network-disabled clean install still reaches the supported local baseline.
4. A CI check rejects a new forbidden mandatory dependency.
5. Optional services are labeled optional and have a Linux/Fedora fallback.
6. Telemetry/cloud endpoints are absent or explicit opt-in.
7. The report distinguishes source-level absence from runtime confirmation.

## Hardware, privilege and rollback safety
Do not break optional user-configured services. No credentials/telemetry in repo. Do not replace one mandatory cloud with another.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r49-no-mandatory-google-apple-android`, with tests and docs for this component only.
- `docs/component-reports/r49.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a mandatory function has no independent implementation; report the exact gap instead of hiding it behind an optional label.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
