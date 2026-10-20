# NUXEL R08 — Perfect the original boot animation
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r08-original-boot-animation`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Reproduce the original Nuxel boot animation exactly, including asset fidelity, timing, scaling, audio cue ownership, and the one-shot handoff to the launcher. This branch must remove black frames, double playback, premature sound, flicker, and renderer-start races while keeping the launcher as the sole final display owner.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `assets/nuxel-boot-animation.mp4`, `assets/nuxel-boot-audio.mp3`, `pwa/nuxel-home/assets/nuxel-boot-animation.mp4`, `configs/nuxel/boot/animation-handoff.json`, `services/nuxel-animation/bin/nuxel-animation-claim`, `services/nuxel-animation/systemd/nuxel-animation.service`, `tools/s10plus/a33/nuxel-anim-handoff.py`, `pwa/nuxel-home/js/bootlog.js`, and `docs/beta-finalization/boot/ANIMATION-HANDOFF.md`. The repository contains real assets and a handoff contract, but playback timing and audible cue behaviour on the physical phone are not proven by source.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns animation assets, playback timing, aspect/letterbox policy, frame presentation, handoff receipt, and boot-audio trigger timing. Does not own the speaker route itself or launcher app logic. The boot cue must fire from the real handoff receipt, not from early web load.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Verify the canonical animation asset hashes/geometry and compare repo copies with the rootfs-installed asset so there is one source of truth.
2. Trace the animation service from unit start to first frame and from final frame to launcher ownership; record timestamps for each transition.
3. Implement deterministic one-shot playback with explicit failure/fallback if the animation asset or renderer is unavailable.
4. Fix aspect/scale/crop handling for the S10+ panel and prove no black flash before the first frame or between animation and launcher.
5. Assert the boot cue fires exactly once after the real handoff receipt, respects mute/volume policy, and never on bridge/service restart.
6. Add frame/timing diagnostics that can be enabled without changing the normal visual experience.
7. Test a normal boot, a service restart, and a killed/restarted web layer; confirm the animation does not replay unexpectedly.

## Failure modes and diagnostics
- Likely defects: animation and launcher both claiming the framebuffer, service ordering causing a blank gap, stale service-worker asset, wrong video colour range, audio cue tied to page load, and the display bridge restarting mid-playback.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The installed animation bytes match the canonical asset hash and the expected resolution/format.
2. The first presented frame is measured and no unintended black frame precedes it on a normal boot.
3. The animation-to-launcher handoff occurs once per boot with a recorded receipt and no focus gap.
4. The boot audio cue fires once, only after the handoff, and remains silent/refused when muted.
5. Restarting a downstream service does not replay the animation or sound.
6. A missing/corrupt animation asset yields a controlled fallback, not a hang or repeated retry.
7. Owner-visible timing and audible-cue results are recorded separately from frame-trace results.

## Hardware, privilege and rollback safety
Do not remove the speaker-volume cap or trigger the boot cue at full scale. Preserve the display bridge as the single framebuffer owner. No flashing or kernel changes.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r08-original-boot-animation`, with tests and docs for this component only.
- `docs/component-reports/r08.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the animation requires a different compositor or framebuffer owner than the established Nuxel stack. Report exact asset/handoff evidence instead of guessing timing from prose.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
