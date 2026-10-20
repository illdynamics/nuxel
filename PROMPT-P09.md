# NUXEL P09 — Clean image and workflow preparation
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/p09-clean-image-workflow-preparation`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make Nuxel's clean Fedora ARM64 image workflow reproducible and auditable without booting or flashing a phone. The branch must define host prerequisites, rootfs composition, package manifests, staging, provenance, checksums, cache behaviour, and artifact inspection, and must clearly separate a generated artifact from a device-verified image.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `images/s10plus/build-phone-rootfs-fedora.sh`, `images/s10plus/build.sh`, `images/s10plus/packages-manifest.json`, `images/mkrootfs.sh`, `images/config/packages.yml`, `images/build-ota.sh`, `ci/validate-build.sh`, and `.github/workflows/release.yml`. Existing rootfs builders and manifests are source evidence; no current artifact should be described as boot-tested merely because it was built.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the image build recipe, package manifest validation, staging layout, reproducibility metadata, artifact hashing, and CI invocation. Does not own device-side hardware acceptance or partition/flash procedures. No kernel replacement, no bootloader interaction, and no claim of bootability from file presence.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Audit host prerequisites (architecture, Fedora version, required tools, loop/mount capabilities) and encode them in a preflight that fails with exact missing packages.
2. Trace `build-phone-rootfs-fedora.sh` end to end and record every input, generated file, copied source tree, package transaction, and output artifact.
3. Validate `packages-manifest.json` against `images/config/packages.yml`, checking duplicate packages, unpinned versions, unavailable ARM64 packages, and packages pulled implicitly by services.
4. Make the build reproducible: pin source SHA, record package repository metadata and resolved NEVRA, sort archive entries, normalize timestamps where safe, and emit SHA-256 plus provenance.
5. Add a staged artifact inspection that verifies required launcher/service/config paths and rejects hidden host paths, credentials, or stale A32/A34 files.
6. Wire a clean-build smoke job into CI and keep its outcome distinct from a physical boot result.
7. Document a recovery path for cache corruption and a deterministic clean rebuild command.

## Failure modes and diagnostics
- Likely failures include host package drift, ARM64 RPM repository outages, caching a partially extracted rootfs, `rsync` carrying deleted files forward, timestamps/UIDs breaking reproducibility, and CI using a different Fedora release from the documented host.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. A clean host can run the documented build command from the pinned commit and produce the same declared artifact set and checksums, excluding explicitly documented nondeterministic metadata.
2. The preflight reports every missing host tool/package and stops before modifying the workspace.
3. The package manifest and resolved transaction agree; no required runtime package is missing and no unintended host-specific package appears.
4. Artifact inspection proves the expected launcher, configs, services, and rootfs entries are present with expected modes/owners.
5. No secret, SSH key, IMSI/IMEI, Wi-Fi credential, or host-only absolute path is present in the artifact.
6. CI publishes a build provenance record and hash, and labels the output BUILD VERIFIED only, never BOOT VERIFIED.
7. Failure of a clean rebuild is actionable from the retained log and does not require reading an interactive shell history.

## Hardware, privilege and rollback safety
Never loop-mount, partition, format, or write a removable/phone block device in this branch. Build into a workspace path with explicit cleanup. If privileged operations are required, document them and stop for owner approval rather than silently using sudo on the host.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/p09-clean-image-workflow-preparation`, with tests and docs for this component only.
- `docs/component-reports/p09.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the build cannot be pinned to a source commit or package repositories. Stop if verification would require booting/flashing hardware. Do not mark an artifact bootable from checksum or archive inspection alone.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
