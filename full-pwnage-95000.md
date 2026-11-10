# full-pwnage-95000.md
# NUXEL FULL PWNAGE 95000
## MASTER HISTORICAL PWNAGE AUDIT · LIVE DEVICE DEPLOYMENT VERIFICATION · GIT TRACEABILITY · CONTROLLED REMEDIATION

**Project:** Nuxel  
**Repository:** `illdynamics/nuxel`  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**SSH:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167`  
**Deployment scripts:** `./scripts`  
**Audit ID:** PWNAGE-95000  
**Primary objective:** Determine whether every historical Nuxel PWNAGE task is genuinely implemented, built, deployed, running, and verified on the physical device.

---

# 0. THE MISSION

We have been working through a long sequence of Nuxel PWNAGE development tasks.

Each task has generally consisted of two Markdown files:

- `pwnage-#####.md` — Kickstarter prompt.
- `full-pwnage-#####.md` — detailed implementation specification.

We are no longer certain whether all the requested changes have actually made it into the live Nuxel installation.

Some tasks may have been:

- Fully implemented and deployed.
- Implemented but never deployed.
- Built but never installed.
- Installed but never activated.
- Partially implemented.
- Superseded by later changes.
- Accidentally overwritten.
- Regressed by subsequent development.
- Never implemented at all.
- Implemented in a development environment but not in the actual phone installation.

**We need a definitive, evidence-based answer.**

Your job is to reconstruct the history of Nuxel development, inspect every available PWNAGE prompt, trace each requested feature through the source code and deployment pipeline, connect to the physical S10+, and establish the actual live state.

This is not a normal feature implementation task.

It is a comprehensive operating-system deployment audit.

The most important question is:

**Does the Nuxel installation currently running on the S10+ actually contain all the functionality that we previously instructed our development agents to implement?**

Do not guess. Prove it.

---

# 1. NON-NEGOTIABLE RULES

## 1.1 Audit before remediation

The first stage must be strictly observational.

Do not start modifying code or deploying files before completing the initial audit.

You must first determine:

1. What was requested.
2. What was implemented.
3. What was committed.
4. What was built.
5. What was deployed.
6. What is currently installed.
7. What is currently running.
8. What has actually been verified.

Only after this information is available may you begin controlled remediation.

## 1.2 Never confuse source code with live deployment

These are separate states:

| State | Meaning |
|---|---|
| Prompt exists | The requested work was documented |
| Code exists | An implementation is present in the repository |
| Tests pass | Some implementation behavior has been tested |
| Commit exists | The implementation was committed |
| Build exists | A corresponding artifact was generated |
| Deployment attempted | A deployment command was executed |
| Deployment succeeded | The deployment mechanism reported success |
| Installed | The intended files are present on the device |
| Active | The running device is using those files |
| Verified | The requested behavior has been tested |

A Git commit is not proof of deployment.

A successful build is not proof of deployment.

A successful deployment script exit code is not proof that the correct files were installed.

A file existing on the device is not proof that the running service or application is using it.

Only establish the strongest status supported by evidence.

## 1.3 Protect the existing installation

Do not:

- Flash the bootloader.
- Flash recovery.
- Flash the kernel.
- Flash modem firmware.
- Flash device firmware.
- Change partition layouts.
- Perform a factory reset.
- Reinstall the entire OS without explicit necessity.
- Overwrite user data.
- Replace working configuration with defaults.
- Delete uncommitted repository changes.
- Reset Git branches.
- Force-push.
- Disable security checks.
- Blindly restart critical services.

This audit should primarily involve inspection, read-only diagnostics, and controlled testing.

## 1.4 Preserve existing graphics and display architecture

Discover and preserve the current graphics architecture.

Historically relevant components include:

- Phoc/Wayland.
- `zwlr_screencopy`.
- `nuxel-wl-fb`.
- Sole `/dev/fb0` writer.
- Samsung DECON/AMOLED.
- Existing Mali/EGL acceleration.

These are historical architectural references, not assumptions about the exact current implementation.

Do not introduce a second framebuffer writer, force software rendering, replace the compositor, or change global resolution/DPI during this audit.

---

# 2. PHASE A — COMPLETE HISTORICAL PROMPT DISCOVERY

## 2.1 Find every PWNAGE prompt

Search the entire repository, including relevant documentation and project folders, for:

```text
pwnage-*.md
full-pwnage-*.md
```

Search case-insensitively where appropriate.

Also inspect:

- Root directory.
- Documentation directories.
- Task directories.
- Reports.
- Historical backups.
- Archive folders.
- Release documentation.
- Relevant scripts.
- Git history.
- Git branches and tags.

Do not restrict discovery to the current root directory.

Avoid wasting time searching generated dependencies and build directories unless there is a specific reason.

## 2.2 Discover missing historical prompts

Git history may contain prompts that no longer exist in the working tree.

Inspect:

```bash
git log --all --name-status -- '*pwnage-*.md' '*full-pwnage-*.md'
```

Also inspect historical commits, branches, and tags for deleted or renamed prompts.

Where possible, recover the contents of historical prompts from Git history for audit purposes.

Do not restore deleted prompts into the working tree merely to inspect them.

## 2.3 Pair Kickstarter and full specification

Build a complete inventory.

For every discovered number, identify:

- Kickstarter filename.
- Full specification filename.
- Whether both exist.
- Whether one is missing.
- Whether multiple versions exist.
- Whether the contents conflict.
- Whether the full specification contains requirements not mentioned in the Kickstarter.

Do not assume all prompt numbers are sequential.

Do not assume a missing number indicates a missing task.

Do not assume that a Kickstarter and full prompt with matching numbers are necessarily the same version. Compare their contents.

## 2.4 Build the historical task index

Create:

`REPORT-PWNAGE-95000.md`

Include a historical prompt index.

Example:

| PWNAGE ID | Kickstarter | Full spec | Historical availability |
|---|---|---|---|
| 87000 | Found | Found | Both available |
| 88000 | Found | Found | Both available |
| 90000 | Found | Found | Both available |
| 93000 | Found | Found | Both available |
| 94000 | Found | Found | Both available |
| Other IDs | Discover | Discover | Determine from repository/history |

The example IDs are not an exhaustive list. Discover the actual inventory.

---

# 3. PHASE B — EXTRACT ALL REQUESTED REQUIREMENTS

Finding the prompt files is not sufficient.

You must extract the actual requested functionality from them.

## 3.1 Read every full specification

Read every discovered `full-pwnage-#####.md` completely.

Read the corresponding Kickstarter prompts as well.

The full specifications are the primary source of implementation requirements.

The Kickstarter files may contain important additional constraints, execution instructions, or acceptance criteria. Do not discard them.

## 3.2 Break prompts into atomic requirements

Each requested feature must become an independently auditable requirement.

For example, if a prompt asks for:

- A sound mode icon.
- A notification badge.
- Notification persistence.
- Swipe gestures.
- App permissions.

These are five separate requirements, not one task.

A requirement must be specific enough to determine whether it is implemented and deployed.

Assign each requirement a unique identifier:

```text
PWNAGE-93000-REQ-001
PWNAGE-93000-REQ-002
PWNAGE-93000-REQ-003
```

Continue for every prompt and requirement.

## 3.3 Capture acceptance criteria

Extract:

- Requested functionality.
- Expected behavior.
- Required configuration.
- Required UI.
- Required services.
- Required APIs.
- Required scripts.
- Required tests.
- Physical-device requirements.
- Performance requirements.
- Security requirements.
- Rollback requirements.

If a prompt requests a physical test, mark it as requiring physical verification.

If a prompt requires a specific deployment or release process, capture that too.

## 3.4 Build the master requirement matrix

Create a structured requirement matrix.

Recommended fields:

| Field | Description |
|---|---|
| Requirement ID | Unique identifier |
| PWNAGE ID | Original prompt number |
| Original prompt | Source filename |
| Feature | Short description |
| Acceptance criteria | What must work |
| Source files | Relevant implementation files |
| Git commits | Relevant commits |
| Tests | Relevant tests |
| Build artifact | Relevant build |
| Deployment script | Script responsible |
| Device files | Installed files |
| Runtime component | Active service/application |
| Live evidence | Evidence collected |
| Status | Audit classification |
| Confidence | Evidence strength |
| Notes | Missing work/blockers |

Do not omit small requirements.

A tiny icon change is still a requirement if it was explicitly requested.

---

# 4. PHASE C — GIT AND IMPLEMENTATION TRACEABILITY

## 4.1 Establish repository state

Record:

```bash
git status --short
git branch --show-current
git log -1 --oneline
git log --oneline --decorate -30
git tag --list
```

Inspect:

- Current branch.
- Current commit.
- Uncommitted changes.
- Untracked files.
- Recent commits.
- Historical branches.
- Release tags.
- Merges.
- Reverts.
- Cherry-picks.
- Deleted files.

Never discard user changes.

## 4.2 Trace every requirement into source code

For each atomic requirement:

1. Search for the relevant implementation.
2. Inspect the implementation.
3. Follow imports and references.
4. Trace relevant configuration.
5. Trace service and IPC integration.
6. Identify the actual runtime entry point.
7. Identify the test coverage.
8. Identify the commit history.

Do not mark a requirement implemented just because a matching filename or symbol exists.

Check that the implementation is actually connected to the running system.

## 4.3 Detect incomplete and dead implementations

Search for:

- TODO markers.
- FIXME markers.
- Stub implementations.
- Placeholder functions.
- Disabled code paths.
- Feature flags left off.
- Duplicate implementations.
- Deprecated components still active.
- Unused replacement components.
- Configuration that never gets loaded.
- Services that are never enabled.
- UI elements that have no functioning backend.
- Backend functions that have no UI integration.

Determine whether later tasks replaced or superseded earlier implementations.

## 4.4 Detect regressions and overwrites

Compare relevant commits.

Investigate whether:

- A previously working feature was removed.
- A later implementation replaced an earlier one.
- A service was disabled.
- A config file reverted to an older version.
- A deployment script stopped installing a component.
- A build omitted a new asset.
- A UI change broke backend integration.
- A newer task reintroduced an older bug.

A task that was once implemented but is now missing must be classified as a regression.

---

# 5. PHASE D — DEPLOYMENT SCRIPT DISCOVERY

## 5.1 Deployment scripts are in `./scripts`

This is mandatory.

**Find and inspect the existing deployment scripts in `./scripts`.**

Do not assume a script name.

Start by listing the directory and inspecting the available scripts, subdirectories, and documentation.

Determine which scripts handle:

- Full system deployment.
- Partial deployment.
- PWA deployment.
- Native component deployment.
- Service deployment.
- Configuration deployment.
- Asset deployment.
- Flatpak integration.
- App installation.
- Theme configuration.
- Graphics/UI components.
- Device diagnostics.
- Build generation.
- Remote synchronization.
- Restart operations.
- Verification.
- Rollback.

Follow every script's internal references and helper scripts.

## 5.2 Identify the canonical deployment workflow

Determine:

- Which script is currently authoritative.
- Which scripts are legacy.
- Which scripts are experimental.
- Which scripts deploy to the S10+.
- Which scripts deploy to development machines.
- Which scripts build without deploying.
- Which scripts deploy but do not verify.
- Which scripts require specific environment variables.
- Which scripts rely on hardcoded device addresses.
- Which scripts use a manifest or build identifier.
- Whether deployment is atomic or incremental.

Do not run a script until its behavior is understood.

## 5.3 Map requirements to deployment scripts

Every requirement must have an explicit deployment trace.

For example:

```text
Requirement
    |
    v
Source implementation
    |
    v
Build target
    |
    v
Deployment script in ./scripts
    |
    v
Installed device path
    |
    v
Running service/application
    |
    v
Verification
```

If a requirement has no identifiable deployment path, mark it accordingly.

Do not invent a deployment script association.

## 5.4 Detect deployment omissions

Check whether:

- New files are excluded from installation.
- Assets are missing from deployment manifests.
- PWA bundles are stale.
- Native binaries are outdated.
- Systemd units are installed but not enabled.
- Services are enabled but not running.
- Configuration is deployed to the wrong location.
- Old files remain alongside replacements.
- Scripts skip certain application types.
- Deployment scripts use an outdated source directory.
- The build artifact does not correspond to the current Git commit.

---

# 6. PHASE E — CONNECT TO THE LIVE S10+

## 6.1 Required SSH command

Use this exact command:

```bash
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167
```

This is the designated SSH access method for this audit.

Do not substitute an unrelated endpoint without first reporting the connection failure and requesting/establishing the correct endpoint.

## 6.2 Host identity verification

Before making changes:

- Verify the SSH host key.
- Verify the device model.
- Verify the device identity.
- Verify the running kernel.
- Verify the Nuxel installation.
- Verify the active build/version.
- Verify the effective user.
- Verify the device architecture.
- Verify available storage and memory.
- Verify the active display/session.

Do not disable host-key checking.

Do not put private key contents into the report.

Do not copy the private key to the phone.

## 6.3 Capture live device state

Collect relevant read-only information.

Examples include:

```bash
uname -a
cat /etc/os-release
systemctl --failed
systemctl list-units --type=service --state=running
systemctl list-unit-files --type=service
ps aux
findmnt
df -h
free -h
```

Adapt commands to the actual Nuxel environment.

Inspect:

- Installed Nuxel version.
- Build ID.
- Installed package versions.
- Relevant file timestamps and hashes.
- Running service versions.
- Active user session.
- Wayland compositor.
- PWA and native component versions.
- Relevant configuration.
- Flatpak applications and overrides.
- GTK settings.
- Audio services.
- App registry.
- Display geometry.
- Active surfaces where observable.

Do not expose secrets or sensitive tokens in the report.

## 6.4 Verify actual installed files

For every requirement, identify the expected installed paths.

Compare:

- Repository source.
- Built artifact.
- Deployed file.
- Running component.

Where possible, compare SHA-256 hashes.

For example:

```bash
sha256sum /path/to/installed/file
```

Compare against the exact expected build artifact.

Do not compare unrelated source files with compiled artifacts and declare them mismatched.

Use the correct build manifest and artifact provenance.

## 6.5 Verify running state

For services:

- Inspect systemd unit status.
- Inspect active executable.
- Inspect process arguments.
- Inspect service environment.
- Inspect logs.
- Confirm the service is using the expected installed files.

For UI components:

- Confirm the currently served/deployed bundle.
- Confirm the actual runtime entry point.
- Confirm relevant assets are loaded.
- Confirm no stale cached bundle is being displayed.

For native applications:

- Confirm executable path.
- Confirm version.
- Confirm libraries and runtime.
- Confirm application integration.

For Flatpaks:

- Confirm installed application ID.
- Confirm installed commit/version.
- Confirm runtime.
- Confirm overrides.
- Confirm theme environment.

A file existing on disk does not establish that it is active.

---

# 7. PHASE F — VERIFY HISTORICAL REQUIREMENTS AGAINST LIVE BEHAVIOR

This is the most important phase.

For each requirement, determine whether the actual running device behaves as requested.

Do not restrict verification to source code.

## 7.1 UI and interaction requirements

Where a prompt requests UI behavior:

- Verify the actual deployed component.
- Verify the correct interaction.
- Verify the correct visual state.
- Verify the relevant orientation.
- Verify the relevant app context.
- Verify the behavior survives reopening the application.

Use physical interaction where necessary.

## 7.2 Service and backend requirements

Where a prompt requests a backend feature:

- Verify the service exists.
- Verify the service is active.
- Verify its API/IPC endpoint.
- Verify its actual functionality.
- Verify error handling.
- Verify persistence where required.

## 7.3 Hardware-dependent requirements

For hardware-dependent features, distinguish:

- Implemented in source.
- Deployed to device.
- Hardware detected.
- Driver/service initialized.
- Feature operational.
- Physically verified.

For example, a camera implementation must not be called functional just because a camera node exists.

Likewise, hardware video decoding must not be marked working without an actual decoding test.

## 7.4 Previously requested PWNAGE workstreams

Explicitly include all requirements from the discovered historical prompts, including, where present:

- Boot and startup behavior.
- Launcher and desktop.
- Home, Back, and Tabs navigation.
- App drawer.
- Dock and icons.
- Status bar.
- Quick Settings.
- Notifications.
- Sound mode.
- Audio and Doom.
- Alarms and timers.
- Lock screen.
- Display and graphics.
- NEO/NEXUS graphics architecture.
- Permissions manager.
- Native application integration.
- GTK and Flatpak integration.
- App startup performance.
- Remote desktop RDP and VNC.
- scrcpy and GUI tri-link.
- USB networking.
- Console and file transfer.
- Software installation and NuXtore.
- App signing and catalog verification.
- Connectivity.
- Bluetooth.
- Wi-Fi.
- External display.
- Hardware acceleration.
- Device-specific sensors.
- Documentation and release processes.
- Any other requirement discovered in the actual prompts.

This list is a guide, not a replacement for reading every full specification.

## 7.5 Recent PWNAGE-93000 requirements

Verify all four historical workstreams:

1. GTK/Flatpak duplicate icon handling.
2. Sound-mode icon states.
3. Full notification system and Quick Settings notification behavior.
4. Invisible surfaces after single Back navigation.

Check actual live behavior, not just source implementation.

## 7.6 Recent PWNAGE-94000 requirements

Verify all six historical workstreams:

1. Doom launches with sound enabled by default and actual audio works.
2. Fullscreen uses the standard desktop Nuxel top bar.
3. Progressive top-bar opening and one-swipe complete closing.
4. Native and Flatpak startup performance improvements.
5. System-wide Adwaita dark defaults, including System Monitor.
6. Back lifecycle reliability and desktop vertical-position restoration.

If these tasks have not yet been implemented, do not claim they are deployed.

---

# 8. PHASE G — STATUS CLASSIFICATION

Use the following exact statuses.

| Status | Meaning |
|---|---|
| `PROMPT_NOT_FOUND` | Historical prompt could not be located |
| `SPEC_INCOMPLETE` | Kickstarter/full spec pair is incomplete |
| `NOT_IMPLEMENTED` | No credible implementation exists |
| `PARTIALLY_IMPLEMENTED` | Some requested functionality exists |
| `IMPLEMENTED_UNTESTED` | Code exists but relevant tests are missing |
| `TESTED_NOT_COMMITTED` | Tests pass but changes are not committed |
| `COMMITTED_NOT_BUILT` | Relevant changes committed but no corresponding build |
| `BUILT_NOT_DEPLOYED` | Artifact exists but is not installed on target |
| `DEPLOYMENT_UNKNOWN` | Insufficient deployment evidence |
| `DEPLOYED_NOT_ACTIVE` | Installed but not active |
| `DEPLOYED_UNVERIFIED` | Active deployment established but behavior not verified |
| `PARTIALLY_DEPLOYED` | Some requirements deployed, others missing |
| `REGRESSED` | Previously implemented functionality is now missing or broken |
| `BLOCKED` | Specific technical or external blocker prevents verification |
| `VERIFIED_LIVE` | All required implementation, deployment, runtime, and verification evidence exists |

A full PWNAGE task may contain requirements with different statuses.

Therefore, provide both:

1. Individual requirement statuses.
2. Overall PWNAGE task status.

Never mark an entire task `VERIFIED_LIVE` if even one mandatory acceptance criterion remains unverified.

---

# 9. PHASE H — EVIDENCE AND CONFIDENCE

Every status must have supporting evidence.

## 9.1 Evidence types

Record:

- Prompt filename and relevant section.
- Source filename and relevant line numbers.
- Git commit hash.
- Test name and result.
- Build identifier.
- Build artifact hash.
- Deployment script.
- Deployment record.
- Installed device path.
- Installed file hash.
- Active service/process.
- Runtime logs.
- Physical test result.

## 9.2 Confidence levels

Use:

- `HIGH` — Multiple independent evidence sources agree.
- `MEDIUM` — Good evidence exists but one verification layer is missing.
- `LOW` — Indirect or incomplete evidence.
- `UNKNOWN` — Insufficient evidence.

Examples:

- Matching artifact hash, active process, and physical test: high confidence.
- Installed file and service status but no behavior test: medium confidence.
- Git commit only: low confidence for deployment.
- Prompt file only: no deployment evidence.

## 9.3 No fabricated results

Never fabricate:

- Git commits.
- Deployment timestamps.
- Build IDs.
- Test results.
- Device paths.
- Physical verification.
- Performance improvements.
- Hardware capabilities.

If evidence is unavailable, say so.

---

# 10. PHASE I — BUILD THE MASTER AUDIT REPORT

Create:

`REPORT-PWNAGE-95000.md`

This report is the primary deliverable.

It must be comprehensive, readable, and actionable.

## 10.1 Executive summary

Include:

- Number of historical PWNAGE IDs found.
- Number of Kickstarter prompts found.
- Number of full specifications found.
- Number of atomic requirements extracted.
- Number of requirements implemented.
- Number committed.
- Number built.
- Number deployed.
- Number active.
- Number verified live.
- Number partially deployed.
- Number regressed.
- Number blocked.
- Overall state of the S10+ installation.

Do not count a task as fully deployed merely because some of its files are present.

## 10.2 Historical prompt inventory

List every discovered PWNAGE pair and any missing counterpart.

## 10.3 Master PWNAGE deployment matrix

Provide one row per PWNAGE task.

| PWNAGE ID | Requirements | Implemented | Built | Deployed | Active | Verified | Overall status |
|---|---:|---:|---:|---:|---:|---:|---|

Use actual counts.

## 10.4 Atomic requirement matrix

Provide a detailed requirement-by-requirement matrix.

This is essential because one PWNAGE prompt can contain many independent requirements.

## 10.5 Deployment infrastructure findings

Document:

- Existing scripts in `./scripts`.
- Canonical deployment entry point.
- Legacy deployment scripts.
- Build process.
- Deployment process.
- Verification process.
- Rollback mechanism.
- Any gaps in the deployment infrastructure.

## 10.6 Live device findings

Document:

- Device identity.
- OS version.
- Nuxel version.
- Active build ID.
- Kernel.
- Active services.
- Installed components.
- File/hash comparisons.
- Relevant runtime state.
- Deployment discrepancies.

## 10.7 Missing and regressed features

Provide a prioritized list:

- Critical: breaks core usability or safety.
- High: major requested feature absent.
- Medium: partial implementation or significant regression.
- Low: cosmetic or minor incomplete requirements.

Explain each finding and its evidence.

---

# 11. PHASE J — CONTROLLED REMEDIATION

After the audit is complete, determine which tasks actually need attention.

**Do not blindly redeploy every historical PWNAGE task.**

## 11.1 Create a remediation plan

Create:

`REMEDIATION-PWNAGE-95000.md`

For every incomplete requirement, include:

- Original PWNAGE ID.
- Requirement ID.
- Expected behavior.
- Actual behavior.
- Root cause.
- Missing source implementation.
- Missing build.
- Missing deployment.
- Required deployment script.
- Dependencies.
- Risk.
- Recommended remediation.
- Verification steps.
- Rollback method.

## 11.2 Prioritize

Recommended order:

1. Core system stability.
2. Broken Home/Back/Tabs navigation.
3. Display and compositor issues.
4. Missing or broken permissions/security controls.
5. Missing core connectivity.
6. Audio and hardware integration.
7. App launcher and Flatpak/native integration.
8. Notifications and Quick Settings.
9. Performance.
10. Cosmetic refinements.
11. Documentation and release housekeeping.

Adapt the priority to actual findings.

Do not assume an older task is less important if it affects core functionality.

## 11.3 Resolve dependency conflicts

Some historical tasks may depend on later architecture changes.

Before redeploying an old implementation:

- Check whether a later PWNAGE task superseded it.
- Check whether the old implementation is incompatible with the current architecture.
- Check whether its configuration has migrated.
- Check whether a later fix intentionally removed it.
- Check whether restoring it would reintroduce a bug.

The objective is to satisfy the latest valid intended behavior, not blindly restore every historical code change.

## 11.4 Remediation authorization

The audit phase must not automatically make changes.

After the audit, present the remediation plan and its risks.

If the execution environment explicitly authorizes implementation and deployment as part of this task, proceed only with narrowly scoped, reversible userspace fixes that are clearly required and supported by evidence.

Do not perform destructive operations or firmware/partition changes.

For anything that risks data loss, bootability, security, or major system downtime, stop and report the exact issue before proceeding.

## 11.5 Deploy through existing scripts

Use the appropriate existing deployment scripts from `./scripts`.

Before running any script:

1. Read its implementation.
2. Identify its effects.
3. Confirm its target.
4. Confirm its rollback.
5. Confirm that it deploys the expected commit/build.
6. Preserve a known-good state.

After deployment, independently verify the result on the phone.

---

# 12. PHASE K — PREVENT THIS UNCERTAINTY FROM HAPPENING AGAIN

One of the main findings may be that Nuxel does not have sufficiently reliable deployment traceability.

If so, recommend and, where safely authorized, implement a deployment manifest.

## 12.1 Proposed deployment manifest

A structured manifest could contain:

```json
{
  "project": "Nuxel",
  "build_id": "actual-build-id",
  "git_commit": "actual-commit-hash",
  "git_branch": "actual-branch",
  "build_timestamp": "actual-timestamp",
  "device_target": "beyond2lte",
  "deployment_script": "actual-script",
  "components": [
    {
      "name": "actual-component",
      "version": "actual-version",
      "source_commit": "actual-commit",
      "installed_path": "actual-path",
      "sha256": "actual-hash"
    }
  ]
}
```

This is a schema example, not a real deployment record.

Populate values only from verified sources.

## 12.2 Deployment verification

Recommend a standard post-deployment verification step that checks:

- Expected build ID.
- Expected Git commit.
- Installed component versions.
- File hashes.
- Service activation.
- Runtime executable paths.
- Critical application availability.

## 12.3 PWNAGE traceability

Recommend a mechanism to associate future PWNAGE requirements with:

- Source changes.
- Tests.
- Commits.
- Build IDs.
- Deployment records.
- Live verification.

The aim is to make it immediately clear whether a future task has reached the actual phone.

Do not add an unnecessarily complex framework if a simple manifest and deployment report solve the problem.

---

# 13. FINAL ACCEPTANCE CRITERIA

The audit is complete only when:

- [ ] Every discoverable historical PWNAGE prompt has been inventoried.
- [ ] Kickstarter and full-specification files have been paired.
- [ ] Missing or deleted prompts have been investigated through Git history.
- [ ] Every full specification has been read.
- [ ] Every requested feature has been broken into atomic requirements.
- [ ] Every requirement has an implementation status.
- [ ] Relevant source files have been identified.
- [ ] Relevant Git commits have been identified where possible.
- [ ] Relevant tests have been identified and evaluated.
- [ ] Build artifacts have been traced.
- [ ] Deployment scripts in `./scripts` have been inspected.
- [ ] The canonical deployment process has been identified.
- [ ] SSH connection to the designated S10+ has been attempted using the specified command.
- [ ] Device identity has been verified if accessible.
- [ ] Installed files have been inspected.
- [ ] Running services and processes have been inspected.
- [ ] Live behavior has been verified where possible.
- [ ] Regressions have been identified.
- [ ] Missing deployment steps have been identified.
- [ ] Every status has evidence and confidence.
- [ ] A complete master audit report exists.
- [ ] A prioritized remediation plan exists.
- [ ] No unapproved destructive operation has been performed.

---

# 14. FINAL RESPONSE FORMAT

When finished, report:

## A. Overall result

Choose one:

- `AUDIT_COMPLETE`
- `AUDIT_PARTIALLY_COMPLETE`
- `AUDIT_BLOCKED`

## B. Device deployment verdict

Choose one:

- `ALL_REQUIREMENTS_VERIFIED_LIVE`
- `MOSTLY_DEPLOYED`
- `PARTIALLY_DEPLOYED`
- `SIGNIFICANT_DEPLOYMENT_GAPS`
- `DEVICE_UNREACHABLE`
- `DEPLOYMENT_STATE_UNKNOWN`

## C. Key numbers

Provide:

- Historical PWNAGE tasks found.
- Kickstarter prompts found.
- Full specifications found.
- Atomic requirements extracted.
- Verified live.
- Partially deployed.
- Not deployed.
- Regressed.
- Blocked.

## D. Most important findings

List the most serious gaps and the impact on the live system.

## E. Artifacts

Create and identify:

- `REPORT-PWNAGE-95000.md`
- `REMEDIATION-PWNAGE-95000.md`

Optionally create a machine-readable JSON or CSV requirement inventory if it materially improves future traceability.

## F. Next step

State precisely what needs to be done to get the live S10+ installation aligned with the intended Nuxel implementation.

---

# 15. FINAL DIRECTIVE

We have invested a substantial amount of development effort into Nuxel.

We do not want to discover that large portions of that work only exist in source code, old commits, development builds, or unfinished deployment scripts.

We need to establish the real state of the operating system.

**Inspect every historical `pwnage-#####.md` and `full-pwnage-#####.md`. Read the actual deployment scripts in `./scripts`. Connect to the S10+ using the exact SSH command supplied. Trace every requirement from specification to source, build, deployment, installed files, running processes, and physical behavior.**

Do not assume. Do not guess. Do not fabricate.

**Give us the definitive Nuxel deployment audit.**
