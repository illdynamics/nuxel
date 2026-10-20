# NUXEL R07 — Fix remaining boot instability
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r07-boot-instability`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Eliminate remaining Nuxel boot delays, retries, and boot loops by measuring the real boot chain and fixing the first blocking unit or handoff. The branch must separate kernel-to-userspace delay, initramfs/rootfs issues, systemd ordering, display/compositor startup, and launcher readiness, and must preserve a recoverable rescue/USB-console path.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `boot/s10plus/bringup-init.sh`, `boot/s10plus/recovery.sh`, `boot/s10plus/tests/test-boot-image-gates.sh`, `boot/s10plus/tests/test-init-cmdline-independence.sh`, `services/nuxel-session/systemd/`, `services/nuxel-animation/systemd/nuxel-animation.service`, and `docs/beta-finalization/boot/`. The repo contains boot-mode and charger-mode findings, but no current boot timing proof for every image.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns boot diagnostics, unit ordering, timeout/restart policy, initramfs/rootfs handoff checks, and the measured startup critical chain. Does not own unrelated hardware drivers or a new bootloader. Never modify partition layout or flash from this branch.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Capture boot timing on a normal boot: firmware-to-kernel boundary, initramfs duration, rootfs mount, `systemd-analyze` critical chain, failed units, restart counts, and launcher-first-frame time.
2. Classify boot modes from `/proc/cmdline`, including `androidboot.mode=charger`/LPM, and prove which mode disables input or blocks the UI.
3. Audit every Nuxel unit for `Before/After/Wants/Requires`, retry storms, unbounded timeouts, and services that start before their device/config dependency exists.
4. Add a bounded boot-event recorder that survives reboot and records unit state, journal offsets, and frame-handoff timestamps without flooding storage.
5. Fix the first measured blocker and add a regression test or fixture for the ordering/timeout invariant.
6. Test cold boot, warm reboot, interrupted boot, and one failed-service scenario while preserving recovery console access.
7. Document the exact rollback and rescue path if the change makes boot worse.

## Failure modes and diagnostics
- Look for duplicate display/framebuffer owners, animation waiting on a missing handoff receipt, services requiring network before NetworkManager is ready, rootfs mounts racing udev, and `Restart=always` without a rate limit. A black screen can be a presentation bug rather than a failed boot.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. A normal boot reaches a visible launcher with measured timestamps for each major phase and no unexplained multi-second gap.
2. No Nuxel unit enters a restart loop; failed units and their first error are reported.
3. Boot ordering changes have a cited dependency and a regression test.
4. Charger/LPM boot is detected and reported distinctly from a normal boot.
5. The USB/rescue path remains available after the change, or the branch is stopped.
6. The report distinguishes KERNEL, INITRAMFS, SYSTEMD, COMPOSITOR, and LAUNCHER time.
7. At most one controlled reboot is required for validation, with pre/post evidence and no blind reboot loop.

## Hardware, privilege and rollback safety
Preserve the known-working Samsung BOOT structure and rescue path. No flashing, bootloader, or kernel replacement. A reboot is a live-device action and needs the repository's bounded reboot policy and owner awareness.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r07-boot-instability`, with tests and docs for this component only.
- `docs/component-reports/r07.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if boot failure cannot be observed without risking an unrecoverable device. Do not keep rebooting after repeated failure. Report the exact first failing boot phase and recovery evidence.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
