# NUXEL P09 — Clean image and workflow preparation
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED

## Mission

This is a future implementation mission for `nuxel/p09-clean-image-workflow-preparation`. Do not execute it merely by reading this file. A future agent may modify code, tests, documentation, images, services, or configuration only after an owner explicitly authorizes execution of this branch prompt. Keep the change limited to this component; do not merge, cherry-pick, deploy, flash, reboot, replace a kernel, or start an unrelated component.

## Repo-grounded current state

**SOURCE VERIFIED:** at source base `e2aaf66951570a8e86211cb8b48060e6cd6773dd`, the following repository paths exist and are directly relevant to the investigation: `images/s10plus/build-phone-rootfs-fedora.sh, images/s10plus/build.sh, images/s10plus/packages-manifest.json, images/mkrootfs.sh`. Their presence establishes maintained configuration, code, test, asset, or evidence locations; it does *not* prove a built image or a live-device result. `docs/architecture.md` and `docs/beta-finalization/DEVICE-CAPABILITY-MANIFEST.md` (where present) are context, not a substitute for inspecting the cited owners and their callers at the execution commit.

The current target is Fedora ARM64 for Galaxy S10+ SM-G975F / Exynos 9820, without a mandatory Android framework. Start by re-reading the cited files at the implementation commit, `git log`, `git grep`, manifests, unit files and existing A34–A40/beta-finalization evidence. Record what is observed separately from proposed work. Existing repository captures are historical evidence only: label outcomes as `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, or `NOT TESTED`. In particular, S10+ speaker audio remains unverified unless later evidence proves it; user-reported Home/Back/Recents, virtual-keyboard, icon-drag and torch issues require fresh verification only when this component touches them.

This component’s intended result is: Audit the clean Fedora ARM64 image path: host prerequisites, rootfs composition, reproducibility, provenance, staging, checksums, cache behaviour and release packaging. Keep artifact creation distinct from a verified boot and never partition or flash a phone.

## Precise component boundaries

Own the smallest end-to-end path needed for this mission, including its configuration/schema, runtime consumer, status/reporting surface and tests. Preserve the established Nuxel launcher/WebKit/compositor approach, touch UI, three-button navigation, haptics, BG1/BG2 dock selection (BG2 is default), Fedora ARM64 compatibility and USB-console recoverability. Do not silently introduce Android APIs, a second competing daemon, a generic replacement UI, fictitious kernel nodes, unsafe amplifier/LED/radio control, or a capability claim based solely on a mock.

Out of scope without a separate owner-approved task: bootloader/partition writes, flashing, kernel replacement, radio firmware changes, live-phone reboot, factory reset, destructive cleanup, and merge/release activity. If investigation finds no suitable owner, state **“Not found—locate or add the smallest appropriate module”** and document why rather than fabricating a path.

## Implementation work packages

1. Establish a component evidence baseline. Trace every cited path to its producer and consumer, enumerate service/unit/package/schema boundaries, and make a state table with source evidence, runtime prerequisite, owner and current status. Preserve command lines, stderr and content hashes in the future report.
2. Reproduce the component-specific failure or missing capability with deterministic host/VM-safe fixtures first. Define the exact observable state transition and invariant for: Audit the clean Fedora ARM64 image path: host prerequisites, rootfs composition, reproducibility, provenance, staging, checksums, cache behaviour and release packaging. Keep artifact creation distinct from a verified boot and never partition or flash a phone. Do not label a UI rendering, a mock, or an archive member as a device pass.
3. Design the smallest integration change after the trace is complete. Specify data ownership, lifecycle/ordering, error propagation, privilege boundary, persistence and compatibility with existing launcher/compositor and Fedora services. Resolve duplicate state sources rather than adding a parallel control path.
4. Implement guarded diagnostics and observability. Produce actionable logs/structured status that expose interface identity, readiness, selected backend, failure reason and fallback without leaking secrets. Add rate/size bounds where event, log, media or sensor streams are involved.
5. Add component-focused tests and negative cases alongside the implementation. Use existing project tests where applicable (for example `tools/beta/tests/test-release-tools.sh` and `boot/s10plus/tests/test-boot-image-gates.sh` only when their scope applies); add no meaningless skip. Record commands, environment and output hashes.
6. Write `docs/component-reports/p09.md` when execution is authorized. Include a source inventory, change list, matrix of result labels, commands/exit codes, test evidence, owner-facing live steps, known gaps, rollback receipt and explicit distinction between simulated and physical evidence.

## Failure modes and diagnostics

Treat absent nodes, firmware, permissions, services, IPC endpoints, package dependencies, display/input focus, route ownership and stale cached state as separate hypotheses. Capture the exact interface name, udev/sysfs/proc or service evidence, version, timestamp and first failure; do not infer hardware from a nominal configuration file. Guard against races during boot/suspend/resume, duplicate events, stale UI state, partial writes, interrupted updates and privilege escalation. If a hardware-dependent prerequisite is missing, collect the relevant kernel configuration/device-tree/log evidence and report the smallest grounded next step as `BLOCKED` rather than widening scope.

## Verification and acceptance

All checks below are required before declaring this component complete; report each with its evidence class.

1. A traceable before/after matrix names each owned input, consumer, expected state, actual state, command/log and result label for this mission.
2. The implementation has a focused deterministic test or inspection procedure covering the normal path and an injected unavailable/malformed/denied path specific to the selected backend.
3. The UI/service exposes truthful readiness and error state: no optimistic success, duplicate status indicator, synthetic hardware reading, or silent fallback is accepted.
4. Compatibility is demonstrated for the stated Fedora ARM64 target and existing Nuxel interaction model; unrelated navigation, touch focus, BG2 dock and USB recovery invariants are not regressed.
5. A reviewer can reproduce the result from the report using exact commands, artifacts/hashes and exit codes; source/VM evidence remains labeled separately from live-device proof.
6. For any physical validation, the owner gets short explicit steps, expected observation, stop condition and a place to record PASS/FAIL/timestamp. Missing phone access remains `NOT TESTED` or `BLOCKED`.

## Hardware/privilege/rollback safety

Never surprise-flash, write bootloader/partitions, replace the kernel, reboot a live phone, change radio firmware, brute-force amplifier controls, strobe a torch/LED, or remove the established speaker-volume protection. Obtain explicit owner approval before any live-device action. Prefer read-only discovery, dry runs and mock fixtures. Design rollback as a reversible userspace/config change with a documented pre-state, atomic or staged apply where possible, health check, and USB-console/rescue path. Stop immediately on uncertainty about target identity, power, boot mode, mounted filesystem, privileged authorization or rollback availability.

## Deliverables

Deliver the narrowly scoped implementation, focused tests, and `docs/component-reports/p09.md` only after execution authorization. The report must contain: repo commit/tree state; changed files; source versus design decisions; command receipts and hashes; test matrix; device model/variant evidence; any owner observations; rollback procedure/receipt; and unresolved blockers. Do not claim release readiness, live deployment, audible output, sensor operation, radio operation, or physical control without direct evidence.

## Stop conditions / known blockers

Stop and ask the owner if implementation requires another component, an unverified driver/firmware/interface, destructive data mutation, sensitive credentials, external service/account, target access, or a security policy exception. Stop if results depend on unavailable S10+ hardware and leave a precise owner request rather than manufacturing a pass. A failed assertion must be triaged as stale versus regression with evidence—never weakened to skip. This prompt itself changes nothing and authorizes no deployment.
