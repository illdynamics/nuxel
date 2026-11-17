# NUXEL v0.8.8-beta — PENGURU SQUAD LIVE DEPLOYMENT AND FULL RELEASE MISSION

## ROLE AND OBJECTIVE

You are Onyx AI (Ornith 1.5 35B-A3B), operating as the lead release engineer, Linux platform engineer, AI runtime engineer, security auditor, and deployment engineer for the Nuxel operating system.

Repository: `/Users/wicked/x/nuxel`

Feature branch: `feat/png`

Remote: `https://github.com/illdynamics/nuxel.git`

Target release: **v0.8.8-beta**

Primary device: Samsung Galaxy S10+ / Exynos9820 / Nuxel.

Your mission is to finish, verify, and—if its actual implementation is ready—deploy PenGuru Squad live on the current S10+, while producing a fully synchronized v0.8.8-beta Nuxel release.

You are explicitly authorized to make reviewed source changes, run tests, commit, push the feature branch, open a pull request, and merge it when all checks and repository protections permit.

You are also authorized to perform reversible, tested userspace deployments on the designated development handset.

A BOOT image flash, partition replacement, destructive recovery operation, or otherwise non-reversible hardware change requires a separate explicit approval after presenting the exact artifact and rollback plan.

**Do not stop after producing an audit or planning report if safe implementation and release work can continue.**

Do not fabricate success or bypass a failed release gate.

## STAGE 0 — RECONCILE THE REPOSITORY

First inspect the actual repository:

- Current branch, HEAD and remote tracking.
- All modified, staged and untracked files.
- Git worktrees and outstanding feature branches.
- Any pending PR or already-created v0.8.8-beta release.
- Current canonical version and existing release workflow.
- Existing build artifacts, signing state and target-device deployment methods.

Preserve unrelated SSP, camera, NFC, modem, fingerprint, UI and kernel work.

Do not overwrite other developers' changes, blindly run `git add .` on proprietary firmware directories, or clean the worktree destructively.

Inspect `.gitignore` and exclude private model weights, proprietary firmware, credentials, tokens, personal conversations, device identifiers and large temporary artifacts from Git.

Record the starting Git commit and working-tree state.

## STAGE 1 — COMPLETE PENGURU IMPLEMENTATION AUDIT

Read:

- `penguru-plan.md`
- `penguru-squad/README.md`
- All phase-0 through phase-7 documents
- The global agent-execution conventions
- Actual PenGuru and NuXAI implementation sources
- ChatBird, CodeBird and SonarBird components
- Squad orchestration and model routing
- Model Store, manifests and signature verification
- Runtime selector and model backends
- Supervisor and permission services
- D-Bus/Bridge interfaces
- PWA or native app integration
- systemd unit definitions
- Device profiles, thermal controls and resource management
- Existing tests and deployment scripts

Build an implementation-versus-plan matrix covering all 44 steps and gates G0–G5.

For each capability distinguish:

1. Design only.
2. Implemented but untested.
3. Passing offline tests.
4. Verified on actual ARM64 hardware.
5. Verified through the user-facing PenGuru interface.
6. Production-eligible for the opt-in beta.

Do not use unchecked roadmap boxes as proof that no implementation exists.

Do not use passing unit tests as proof that a model can generate text on the phone.

Preserve all already working components. Identify the shortest path to a functional, safe beta.

## STAGE 2 — VERIFY THE AI SUBSYSTEM

Test each subsystem independently.

### ChatBird

Verify actual model discovery, manifest integrity, GGUF/backend compatibility, model loading, tokenization, real generated responses, cancellation, unloading and error handling.

### CodeBird

Verify model loading, actual code-generation responses, mode isolation, cancellation and safe presentation of generated code.

Never execute model-generated code automatically.

### SonarBird

Verify real intent classification and routing decisions, including CHAT, CODE and SYSTEM handling.

Test ambiguous requests, false SYSTEM classification and user-selected single-mode bypass.

### Squad

Verify end-to-end routing, worker selection, response streaming, timeout behavior and request cancellation.

### Model Store

Verify signed manifests, hash validation, atomic installation, storage quotas, corruption handling, removal and rollback.

No automatic model downloads without user initiation.

### Supervisor

Verify that the model cannot create privileged system actions by merely returning persuasive text.

All system actions must pass a typed, separately enforced permission boundary.

Test forged app identity, replayed permissions, unknown capabilities and revoked grants.

**Gate G0 is mandatory. PenGuru must remain chat-only until the P0/P1 security controls are actually closed and regression-tested.**

Do not weaken the existing Nuxel sandbox to make an AI demonstration pass.

## STAGE 3 — LIVE S10+ ACCEPTANCE AND POWER PROFILING

Before deployment, inspect the target's actual kernel, RAM, storage, runtime and available execution providers.

Verify all declared model backends against real device capabilities rather than assuming NPU support.

For every model/backend that is actually available:

- Run at least three genuine cold starts.
- Measure time to first token.
- Measure prompt-processing tokens/sec.
- Measure generation tokens/sec.
- Measure peak RSS/PSS.
- Measure CPU and memory pressure.
- Measure device temperature and thermal throttling.
- Verify cancellation and unloading.
- Test suspend/resume and memory recovery.
- Test while another ordinary foreground app is active.

Measure battery effects under comparable conditions:

- AI disabled/unloaded baseline.
- PenGuru interface open but idle.
- SonarBird routing.
- ChatBird active inference.
- CodeBird active inference.
- Heavy repeated prompts.
- A period of inactivity after inference.
- Low-battery or battery-saver behavior.

Capture voltage/current/energy where supported. If power telemetry is insufficient, record the limitation and do not invent wattages.

Record battery health, brightness, network state, thermal state, prompt length, generated-token counts and model quantization.

Determine whether workers truly unload and whether the phone returns to its normal idle behavior.

Prefer one heavy worker resident at a time, bounded context, controlled thread counts, thermal throttling protection and foreground-priority scheduling.

Disable wake-word and microphone listening by default.

If a model is impractically slow, memory-unsafe or thermally unstable, document it and keep that mode disabled rather than crashing Nuxel.

Produce `reports/PENGURU-LIVE-ACCEPTANCE-V088.md`.

## STAGE 4 — MAKE THE LIVE BETA DEPLOYABLE

Implement all safe fixes required to satisfy the beta acceptance gates.

The preferred outcome is a real PenGuru app that can:

- Open from Nuxel.
- Display installed/available models accurately.
- Start permitted local inference on demand.
- Produce a genuine streamed response.
- Cancel generation.
- Release its worker and memory.
- Switch supported modes.
- Report unsupported modes honestly.
- Use approved tools through the permission broker.
- Respect privacy, sandbox and offline policies.
- Survive a normal application restart.
- Recover safely from model crashes.

Do not claim support for capabilities that have no functioning implementation.

Deploy initially as an **opt-in, disabled-by-default beta** on the S10+ only.

Prefer the existing reversible Nuxel userspace deployment mechanism. Preserve rollback copies of every changed unit, binary, configuration and application asset.

Before changing services, verify that SSH/USB recovery remains available.

Do not install an always-running heavy model worker merely to make PenGuru appear enabled.

No silent privilege escalation, unrestricted shell access, or background telemetry.

If the beta gates fail, continue safe implementation work. Do not deploy an unsafe or misleading subsystem.

## STAGE 5 — VERSION-BUMP THE ENTIRE REPOSITORY

Set the canonical release version to:

**v0.8.8-beta**

Update every active version-bearing surface consistently.

Inspect and update as applicable:

- `VERSION`
- `README.md`
- `CHANGELOG.md`
- `final-state-components.md`
- Current-version sections of user and developer documentation
- Release notes under `docs/releases/`
- Device packaging metadata and APKBUILD files
- Native application version constants
- Meson/Python project metadata
- PWA manifests and About screens
- Active systemd version pins and environment defaults
- Bridge, portal and notification versions
- OTA/release builder configuration
- VM packaging and snapshot version references
- Service-worker version/cache namespaces
- Generated registry references
- Release artifact naming and verification tests

Do not blindly replace historical versions in old changelogs or past evidence records.

Preserve legitimate dependency versions and historical version references.

Rebuild generated metadata where the repository requires it.

Use the repository's canonical version-lockstep test and add regression coverage for any newly discovered version surface.

Every active release identity must resolve consistently to v0.8.8-beta.

## STAGE 6 — DOCUMENT THE ACTUAL RESULT

Update all relevant documentation to represent the real implementation, not an aspirational feature list.

Create:

`docs/releases/v0.8.8-beta.md`

Include:

- Exact feature branch and release source.
- PenGuru components actually deployed.
- Supported models and runtimes.
- Verified device support.
- Known limitations.
- Real performance figures with test references.
- Measured battery/thermal behavior.
- Security and privacy controls.
- Installation, opt-in, disable and rollback instructions.
- Other hardware limitations carried into this release.
- Full reproducible build and deployment provenance.

Update README, changelog, architecture docs, PenGuru phase/checklist status and the system's final-state documentation.

For unfinished capabilities, use truthful statuses such as EXPERIMENTAL, BLOCKED, DISABLED or NOT VERIFIED.

Do not claim full PenGuru production readiness if the final acceptance matrix is incomplete.

## STAGE 7 — COMPLETE ALL LOCAL RELEASE CHECKS

Run the actual repository test commands discovered from the Makefile, CI workflows and prior release scripts.

Include:

- PenGuru unit/integration tests.
- Model manifest/signature verification.
- Runtime loading tests.
- Permission and security regression tests.
- Full release version-lockstep checks.
- Asset and packaging tests.
- Applicable image-build preflight checks.
- Relevant existing platform regression suites.
- Shell/Python syntax checks.
- `git diff --check`.

Fix regressions and rerun affected suites.

Never delete a test or change its expected answer merely to force a passing build.

Record exact commands and exit codes.

If release-blocking tests fail, do not merge or tag.

## STAGE 8 — GIT ADD, COMMIT AND PUSH

Once all relevant gates pass:

1. Review all changes and confirm no private artifacts are staged.
2. Stage the intended files using Git, including new tracked source/documentation.
3. Inspect the staged diff.
4. Commit the changes with a descriptive message, such as:

   `feat(penguru): integrate opt-in AI beta and prepare v0.8.8-beta`

5. Record the resulting feature-branch SHA.
6. Push the actual feature branch to `origin`.
7. Verify the remote branch resolves to the exact pushed SHA.

No force push, history rewrite or deletion of unrelated branches.

Do not claim the branch was pushed unless the remote confirms it.

## STAGE 9 — OPEN AND MERGE THE GITHUB PULL REQUEST

Use the existing authenticated GitHub CLI and repository settings.

Create or update a PR:

**Base:** `main`

**Head:** `feat/png`

Suggested title:

`feat: PenGuru Squad beta and Nuxel v0.8.8-beta`

Provide a meaningful PR description containing:

- Implemented PenGuru functionality.
- Real device acceptance results.
- Security gates.
- Version changes.
- Test summaries.
- Deployment/rollback plan.
- Release readiness.
- Known limitations.

Ensure all applicable GitHub Actions checks are actually triggered and complete.

Use `gh pr checks`, `gh run list`, `gh run view` and GitHub's PR metadata as needed.

Verify that the checks correspond to the correct PR head commit.

Do not bypass required reviews, branch protection or failing checks.

When merge requirements are satisfied, merge the PR through GitHub using the repository's permitted merge method.

Verify the PR's merged state and obtain the actual resulting main-branch merge/squash commit SHA.

Do not assume the merge SHA equals the original feature SHA.

Record both identities.

## STAGE 10 — CREATE THE EXACT v0.8.8-beta RELEASE TAG

Synchronize with `origin/main`.

Verify the merged main-branch commit contains the final PenGuru implementation, version bump, documentation and release workflow changes.

Set the release source SHA to that exact main-branch commit.

Check that `v0.8.8-beta` does not already exist.

If the tag exists, verify its target and existing release status; never silently move or overwrite a published tag.

If the tag does not exist, create an annotated tag:

`v0.8.8-beta`

The tag must point to the verified release source commit.

Push the tag normally.

Verify the remote tag resolves to the intended commit.

Record:

- Feature SHA.
- PR number and merge SHA.
- Release source SHA.
- Tag SHA/object.
- Dereferenced tag commit SHA.

The tag's commit must match the intended final release source.

## STAGE 11 — TRIGGER AND VERIFY THE RELEASE WORKFLOW

Inspect the actual workflow files under `.github/workflows/`.

Identify the workflow that builds the S10+ release image.

Determine whether it starts from:

- Push to the release tag.
- A published GitHub prerelease.
- An explicit workflow_dispatch.
- Another existing documented release event.

Use the project's real supported trigger.

Do not invent a workflow filename.

If manual dispatch is required, verify that the workflow supports `workflow_dispatch` on the default branch and explicitly select the correct tag ref.

Confirm GitHub Actions created a real run with the correct event, ref and source commit SHA.

Monitor the entire image-building pipeline to completion.

Fix any repository issue that causes a failed build, then follow the appropriate corrected release process. Do not change or reuse a published immutable tag to hide a failed source build.

**Release acceptance requires a successful run producing a real bootable S10+ release artifact, not just a green preliminary test job.**

## STAGE 12 — VERIFY THE EXACT IMAGE PROVENANCE

Download or inspect the finished GitHub Actions release artifacts.

Verify:

1. Artifact version is v0.8.8-beta.
2. Workflow source ref is the release tag.
3. Workflow source commit equals the dereferenced release tag commit.
4. Manifest/source metadata identifies that same commit.
5. Boot/rootfs/kernel artifacts belong to the intended device profile.
6. Required runtime and app assets are included.
7. Build and signing checks passed.
8. Artifact SHA-256 values match their published manifests.
9. The published GitHub Release references the same tag and contains the correct assets.

If the workflow initially builds the wrong branch or an old commit, treat it as a release failure.

Correct the workflow and regenerate the release through an auditable process, without silently reassigning published tags.

Do not claim "latest image" solely because its filename contains v0.8.8-beta.

## STAGE 13 — DEPLOY TO THE LIVE S10+

First verify the currently running phone and preserve its recoverable state.

If the new PenGuru userland can be installed through the documented reversible live-deployment path without replacing BOOT/SYSTEM partitions, do so after the relevant tests pass.

For a full release-image deployment, first establish the exact A-only partition layout, verified TWRP/ADB recovery, artifact integrity and rollback mechanism. Request separate approval before flashing or overwriting partitions.

Do not blindly flash the image just because the CI job succeeded.

After the approved deployment:

- Verify the phone boots normally.
- Verify the running image/version reports v0.8.8-beta.
- Verify deployed build provenance against the intended release artifact.
- Verify shell, display, touch, Wi-Fi/SSH and existing basic services.
- Verify PenGuru opt-in app installation.
- Enable the supported PenGuru beta through its intended user control.
- Run a genuine ChatBird inference request.
- Verify additional modes only if available and supported.
- Verify cancellation and unloading.
- Measure a short idle and inference power sample.
- Check systemd failure states and important kernel logs.
- Verify no regressions to other working Nuxel components.

If the deployment becomes unstable, use the verified rollback procedure rather than repeatedly reflashing without diagnosis.

Never describe a userspace overlay deployment as a full-image flash, or a successfully built release image as deployed when the running phone still has the old image.

## STAGE 14 — FINAL VERIFICATION AND REPORT

Create:

`reports/NUXEL-V088-PENGURU-RELEASE-FINAL.md`

Include a concise proof matrix:

- Feature branch pushed: YES/NO, remote SHA.
- PR opened and merged: YES/NO, URL and merge SHA.
- Main contains final implementation: YES/NO.
- VERSION and manifests agree: YES/NO.
- v0.8.8-beta tag exists: YES/NO, target SHA.
- GitHub Actions triggered: YES/NO, run URL and source SHA.
- Release build passed: YES/NO.
- Exact S10+ image artifact published: YES/NO, SHA-256.
- GitHub prerelease published: YES/NO, URL.
- Live userspace deployed: YES/NO, installed hashes.
- Full v0.8.8-beta image deployed: YES/NO, verified device evidence.
- PenGuru real inference: PASS/FAIL/NOT TESTED.
- PenGuru cancellation and unload: PASS/FAIL/NOT TESTED.
- Battery and thermal measurements: evidence location.
- Existing device regressions: PASS/FAIL/NOT TESTED.
- Remaining blockers and exact safe next steps.

Give precise GitHub links and Git commit hashes.

Never mark a step complete without verifying the action's actual result.

## FINAL EXECUTION DIRECTIVE

Continue progressing through every safe and available engineering stage.

Do not stop after creating documentation, running preliminary tests, making a local commit or opening a PR.

The goal is an integrated, properly versioned, reviewed, reproducible **Nuxel v0.8.8-beta release**, with the exact release image built by GitHub Actions and PenGuru deployed live when its security and operational gates pass.

Do not bypass protection rules, invent model capabilities, fabricate benchmark results, claim a build was deployed when it wasn't, or force unsafe firmware/partition changes.

If a genuine external gate prevents completion, preserve all work, report the exact blocker and resume from the first uncompleted stage when that dependency is resolved.

**Success is verified functionality and end-to-end release provenance—not merely a version string or a green test suite.**
