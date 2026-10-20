# NUXEL R40 — Casting
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r40-casting`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement casting only where the real capture/encode/discovery stack supports it. This branch must identify protocols, PipeWire/compositor capture, codecs, receiver negotiation, and permissions, and must not display a working Cast switch when capture or codec support is unavailable.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/capabilities/hardware-subsystems.json`, `configs/pipewire/nuxel-phone.conf.part`, `configs/s10plus/pipewire/README.md`, `docs/architecture.md`, `pwa/nuxel-home/js/qs.js`, `pwa/nuxel-apps/media/`, and the casting icon in `assets/nuxel-quicksettings-icon-pack/`. No dedicated casting service is evident; treat the feature as unproven and capability-driven.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns casting protocol selection, capture/encode prerequisites, discovery/negotiation, permission/indicator, and status. Does not own media playback or Wi-Fi itself. No fake receiver list and no screen capture without an indicator.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Determine which casting protocols are realistically supportable (e.g., Miracast/Chromecast/DLNA) and what each requires; document unsupported ones.
2. Verify PipeWire/compositor screen-capture capability and the codec/transport path before exposing a UI toggle.
3. Implement discovery with bounded network scope and a truthful NONE/FOUND/UNSUPPORTED state.
4. Implement capture/stream start only after explicit owner action and a persistent recording indicator.
5. Handle capture denial, receiver disappearance, codec failure, and network change.
6. Test a no-receiver environment and ensure no false connected state.
7. Document privacy and bandwidth/thermal limits.

## Failure modes and diagnostics
- Watch for a Cast tile that only toggles CSS, a capture backend that silently grabs the wrong output, and a receiver list cached from another network. A synthetic test stream proves the pipeline, not device compatibility.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report names supported/unsupported casting protocols and their exact dependencies.
2. No Cast switch reports active when capture or encode is unavailable.
3. Discovery returns real receivers or an explicit NONE/UNSUPPORTED state.
4. Capture/streaming starts only with owner consent and a visible indicator.
5. Receiver loss/codec failure/network change stops the stream cleanly.
6. No fake receiver or synthetic stream is presented as a real cast.
7. Privacy/thermal/bandwidth limits are documented and enforced.

## Hardware, privilege and rollback safety
No capture without consent/indicator, no DRM bypass, no flash/kernel changes. Preserve local playback and network recovery.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r40-casting`, with tests and docs for this component only.
- `docs/component-reports/r40.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if no real capture/codec path exists; report NOT_SUPPORTED_ON_DEVICE instead of shipping a decorative toggle.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
