# NUXEL R58 — Reproducible release deliverables
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r58-reproducible-release-deliverables`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Produce reproducible release deliverables for Nuxel: pinned source/build environment, locked package inputs, ARM64 rootfs/bundles, hashes, provenance, deployment/recovery guides, known issues, and CI publication. Artifact integrity must remain distinct from bootability or hardware success.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `images/s10plus/build-phone-rootfs-fedora.sh`, `images/s10plus/packages-manifest.json`, `.github/workflows/release.yml`, `docs/beta-finalization/release/ROLLBACK.md`, `CHANGELOG.md`, `VERSION`, `RELEASE-TRIGGER-v0.6.3-beta.md`, and `docs/beta-finalization/release/evidence/`. The repo has a release workflow and prior artifacts; current reproducibility and artifact contents need verification.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns release build pinning, artifact naming/layout, checksums, provenance, release notes, deployment/recovery docs, and CI publication gates. Does not own device flashing or physical acceptance. No publishing if the source/tag/version mismatch or artifact inspection fails.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Pin the release build to one commit/tag and reject a dirty tree or mismatched VERSION/tag.
2. Resolve and record package/repository metadata for the ARM64 rootfs; avoid unpinned mutable inputs.
3. Produce a documented artifact set (boot/rootfs/bundle as applicable), checksums, manifest, and provenance.
4. Inspect artifacts for required Nuxel files, secrets, stale host paths, and unexpected content.
5. Write deployment and recovery instructions that match the artifacts and explicitly forbid unsafe flashing.
6. Add CI checks for version/tag/SHA, artifact hashes, and manifest completeness before publishing.
7. Generate known-issues/blocker notes from the capability/evidence model.
8. Test a rebuild from the tag and compare hashes/differences.

## Failure modes and diagnostics
- Watch for a double-`v` tag, publishing before all gates pass, artifacts built from a different SHA than the tag, and a manifest that omits large files. Verify the tag-to-commit mapping before publishing.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The release is built from the pinned tag/commit with a clean tree and matching VERSION.
2. The manifest lists every artifact, size, and SHA-256; hashes match the published files.
3. A rebuild from the same inputs produces the same declared artifacts or documents only justified nondeterminism.
4. Artifact inspection confirms required files and no secrets/stale paths.
5. CI refuses publication on a version/tag/SHA mismatch or failed artifact check.
6. Deployment/recovery docs match the artifact layout and do not imply boot/hardware verification.
7. Known issues and unverified hardware remain explicit in the release notes.

## Hardware, privilege and rollback safety
No flashing in the release process. Publishing is gated and reversible. Do not claim bootability from CI artifact checks.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r58-reproducible-release-deliverables`, with tests and docs for this component only.
- `docs/component-reports/r58.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop publication if any version/hash/gate check fails or if the artifact cannot be reproduced. Report the exact mismatch.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
