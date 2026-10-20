# NUXEL P08 — Remaining live userspace and hardware integration
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/p08-live-userspace-hardware-integration`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Close the remaining gap between Nuxel's staged userspace and real S10+ hardware. This branch must produce an idempotent, evidence-driven deployment and readiness map for services, permissions, device nodes, compositor/display ownership, network, power, sensors, audio, and controls, while clearly refusing to invent capabilities that the running kernel does not expose.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/capabilities/hardware-subsystems.json`, `configs/nuxel/capabilities/connectivity-time-audio-buttons.json`, `tools/beta/live/nuxel_live.py`, `tools/beta/live/tests/`, `scripts/s10plus-debug-pack/nuxel-live-deploy.sh`, `images/s10plus/build-phone-rootfs-fedora.sh`, and `docs/beta-finalization/live/DEPLOYMENTS.md`. The capability manifests explicitly state that many subsystems are `OFFLINE_TESTED` or `NEEDS_OWNER_TEST`, never `VERIFIED_ON_S10PLUS`; treat that as the starting truth.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the deployment/readiness orchestration across existing service units and capability files. Does not own each hardware driver implementation; consume the per-component diagnostics and report missing interfaces as blockers. No Android HAL, no second compositor, no parallel daemon, and no fabricated device node.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Build a service/dependency matrix from installed unit files under `services/`, `configs/`, and `tools/s10plus/a33/`, mapping each unit to device nodes, config files, user/group, D-Bus name, and readiness probe.
2. Extend the live deployment plan so every changed file has source hash, destination hash, atomic replace, rollback receipt, and an explicit service restart boundary.
3. Add an idempotent preflight that detects boot mode (`/proc/cmdline`), target model/variant, USB-console availability, disk space, and conflicting owners before any write.
4. Implement per-subsystem readiness probes that distinguish ABSENT_INTERFACE, NOT_BOUND, PERMISSION_DENIED, SERVICE_FAILED, and READY; wire them to the existing capability manifest states.
5. Add a dry-run mode that emits the full planned action graph and refuses paths outside the verified Nuxel webroot/data/config roots.
6. Test interruption recovery: rerun after a partial deployment and prove convergence without duplicate daemons or lost rollback data.
7. Produce a signed-off live checklist that remains BLOCKED when the phone or a required interface is absent.

## Failure modes and diagnostics
- Watch for duplicate ownership between `nuxel-haptics.service` and the haptics bridge, the historical `/var/lib/nuxel/notifications/history.json` split path, webroot remapping from the repo to `/usr/share/nuxel`, charger-mode boots that disable input, and services that report active while their readiness probe still fails.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The matrix covers every deployed Nuxel service and names its real unit, device dependency, config, user, and probe.
2. A dry run changes no files and prints exact source/destination paths and hashes.
3. A repeated apply is idempotent: no duplicate units, no changed hashes on unchanged files, and no restarted service without need.
4. Every capability state is derived from a probe or cited evidence; no manifest line is promoted to VERIFIED without owner evidence.
5. Rollback restores every touched path and service state from recorded receipts.
6. A missing boot mode, device node, firmware, or permission yields a precise BLOCKED state, not a fake READY.
7. The live checklist separates SOURCE VERIFIED, DEPLOYED, and OWNER-VERIFIED outcomes.

## Hardware, privilege and rollback safety
Use read-only probes and `apply:false` first. Never infer that a Mac/Git checkout path equals the live phone path. Preserve a reconnectable USB console before restarting networking, display, or web services. Never write protected partitions or flash.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/p08-live-userspace-hardware-integration`, with tests and docs for this component only.
- `docs/component-reports/p08.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the real active webroot, boot mode, or target identity cannot be established. Stop if deployment would overwrite an unbacked-up live file or if two components claim the same device/service. Report BLOCKED rather than enabling a guessed capability.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
