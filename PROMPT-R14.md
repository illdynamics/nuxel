# NUXEL R14 — Audio — real speaker sound, not only mixer values
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r14-real-speaker-audio`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Find and fix the real S10+ speaker path from application audio through ALSA/PipeWire/UCM/DAPM to the CS47L93 codec and CS35L40 amplifiers. This branch must produce either owner-confirmed low-volume sound or an exact missing route/firmware/driver diagnosis, and it must never equate a writable mixer control with audible output.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/audio/audio.json`, `configs/alsa-ucm/beyond-madera/HiFi.conf`, `configs/s10plus/alsa-ucm/SamsungBeyond2/HiFi.conf` where present, `configs/pipewire/asound-nuxel-safe.conf`, `configs/pipewire/nuxel-s10plus-audio.conf.part`, `configs/wireplumber/nuxel-s10plus-audio.conf.d/51-nuxel-s10plus-audio.conf`, `tools/s10plus/a33/nuxel-audio-diag.sh`, `tools/s10plus/a33/nuxel-sound-cue.py`, and the audio fixtures under `tools/s10plus/a33/tests/fixtures-p3/`. Capability manifests explicitly mark audibility NEEDS_OWNER_TEST.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns the built-in speaker route, UCM/cset generation from captured controls, PipeWire/WirePlumber selection, safe test tone, and speaker diagnostics. Does not own headphone/USB-C routing, Bluetooth audio, or boot-animation timing except for the cue invocation contract.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Capture the real `beyond-madera` card, PCM, DAI format, DAPM widgets, codec firmware, and amplifier controls before editing any route.
2. Run the existing pipeline walker and identify the first silent stage: card, PCM, DAI, controls, DAPM, route, or DAC running.
3. Generate UCM/cset sequences only from captured control names; do not invent MADERA/CS35L40 control names or enable empty sequences.
4. Apply a bounded low-volume tone (existing safety cap, not full scale) and record PCM state and DAPM transitions while it plays.
5. Fix the first missing route or firmware/driver dependency and retest the same bounded tone.
6. Audit boot cue and volume-click paths so they use the repaired route and never bypass the 25% cap.
7. Document exactly what is audible versus merely configured, with owner PASS/FAIL and rollback.

## Failure modes and diagnostics
- Do not trust MP3 decoder exit status, a writable mixer control, or a registered codec as audibility. Check `amixer` controls, `/proc/asound`, DAPM debugfs, firmware presence, DAI format, amp reset GPIO/regulator state, and the actual speaker route in order.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The real ALSA card name is confirmed as `beyond-madera` (or the actual observed name) and the report names every PCM/DAPM/control used.
2. The pipeline walker reports the first failing stage with raw evidence; no stage is called OK when unobserved.
3. A bounded low-volume tone leaves the PCM state RUNNING and records DAPM route changes.
4. Owner either confirms audible speaker output at safe volume or the report gives an exact BLOCKED_FIRMWARE/BLOCKED_KERNEL reason.
5. No guessed amplifier register writes, empty UCM sequence, or full-scale mixer restore is used.
6. The 25% protective cap remains enforced after every route change.
7. Headphone/USB-C behaviour is not regressed and remains separately labeled.

## Hardware, privilege and rollback safety
No brute-force amplifier values, no removal of the volume cap, no kernel/partition/flash changes. Test tones must be bounded and low volume. Stop if the amplifier state cannot be changed safely without documented register knowledge.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r14-real-speaker-audio`, with tests and docs for this component only.
- `docs/component-reports/r14.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop and report the exact missing route/driver/firmware if sound remains silent. A silent result is a valid BLOCKED outcome; a claimed PASS without an owner hearing it is not.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
