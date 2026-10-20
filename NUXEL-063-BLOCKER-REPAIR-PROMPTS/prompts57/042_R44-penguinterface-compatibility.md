# NUXEL R44 — PENGUINTERFACE — device compatibility profiles
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r44-penguinterface-compatibility`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Define and enforce device compatibility profiles keyed to verified hardware identity (DT compatible, board ID, variant), with separate profiles for S10+, G7 Power, and Pixel targets. Drivers, firmware, display, input, audio, and defaults must be capability-driven, and an unknown device must fail closed rather than inheriting a dangerous profile.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/capabilities/hardware-subsystems.json`, `configs/s10plus/display/nuxel-s10plus-display.sh`, `configs/g7power/display/nuxel-g7power-display.sh`, `configs/google-pixel-10-pro-xl/display/nuxel-mustang-start.sh`, `configs/libinput/nuxel-s10plus-touch.conf`, `configs/g7power/libinput/`, `images/config/`, and `docs/hardware-ids.md`. Multiple device trees exist; cross-device contamination is a real risk.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns profile schema, identity detection, profile selection, compatibility gates, and per-device defaults. Does not own each hardware driver. No cross-flashing, no shared firmware symlink that points at another device, and no unknown-device fallback that enables hardware writes.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define a profile schema with identity keys, supported SoC/board/variant, display, input, audio, radio/firmware, power, and forbidden capabilities.
2. Implement identity detection from DT compatible/board ID/model plus an owner-visible override with audit.
3. Select exactly one profile and refuse ambiguous/unknown identities before enabling hardware services.
4. Audit for cross-device file references, especially G7/Pixel UCM, firmware names, display scripts, and libinput transforms.
5. Verify each profile's paths exist and its capability claims are explicit (supported/unsupported/blocked).
6. Test S10+, G7 Power, and Pixel fixtures, an unknown device, and a partially matching device.
7. Document the safe recovery/fallback state when no profile matches.

## Failure modes and diagnostics
- Watch for a broad `s10plus` default applied to every ARM64 device, copied Pixel/G7 audio UCM, shared firmware filenames, and display scripts that assume a framebuffer node. Identity must be verified before privileged actions.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every profile has a schema-valid identity and a complete capability matrix.
2. Detection selects one profile or refuses; no unknown device inherits a writable hardware profile.
3. Cross-device firmware/UCM/display references are absent or explicitly quarantined.
4. An unknown/ambiguous target yields a safe read-only/blocked state.
5. Profile-specific paths and commands existing/working are verified per target, not assumed.
6. Fixture tests cover all supported targets and a mismatched board.
7. The report states which profile was tested on real hardware and which only in fixtures.

## Hardware, privilege and rollback safety
No cross-flashing or cross-device firmware. Unknown targets must fail closed. Do not let an owner override bypass every safety gate.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r44-penguinterface-compatibility`, with tests and docs for this component only.
- `docs/component-reports/r44.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the device identity cannot be verified. Do not select a profile from a marketing name alone; report the mismatch.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
