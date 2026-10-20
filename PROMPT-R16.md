# NUXEL R16 — Hardware button manager and gestures
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r16-hardware-buttons-gestures`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make the S10+ physical button state machine and screen-edge gestures correct and non-duplicating. This branch owns Power/Volume/Bixby timing classes, Home/Back/Recents dispatch, short/long/double/chord arbitration, volume repeat, screenshot/sound-mode chords, and the interaction between the button observer and the launcher's own touch gestures.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `tools/s10plus/a33/nuxel-button-manager.c`, `tools/s10plus/a33/nuxel-button-fsm.h`, `configs/nuxel/input/button-fsm.json`, `configs/nuxel/buttons.json`, `configs/nuxel/buttons/reboot-gate.json`, `tools/s10plus/a33/tests/test-button-fsm.py`, the 20 traces under `tools/s10plus/a33/tests/fixtures-p3/button-fsm/`, `services/nuxel-session/systemd/nuxel-button-manager.service`, and `pwa/nuxel-home/js/recents.js`. A32 button behaviour is a protected baseline; A33 additions are offline-tested but not all live-verified.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns gpio_keys selection, the button finite state machine, action dispatch to the launcher FIFO/host, volume stepping, Recents/Home/Back semantics, and button diagnostics. Does not own kernel input drivers or the launcher's full gesture recognizer. No second writer to gpio_keys and no EVIOCGRAB on the touch device.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Verify the real key device by name/capabilities and record KEY_POWER, KEY_VOLUMEUP, KEY_VOLUMEDOWN, and Bixby codes.
2. Replay all existing FSM traces and add cases for duplicate press, bounce, interrupted hold, chord precedence, and volume autorepeat.
3. Audit dispatch so Home goes to desktop 1, Recents is a persistent view, short Back uses app history, and long Back closes only the foreground app without killing services.
4. Fix duplicate actions between the button manager and launcher touch/gesture handlers; ensure the button manager is a read-only observer except for its explicit dispatch channel.
5. Verify volume steps use the real mixer range and preserve the 25% safety cap, with bounded repeat cadence.
6. Verify screenshot and sound-mode chords dispatch once and do not leak into the emergency reset combo.
7. Test one physical button sequence set and capture button log, launcher action log, and visible result.

## Failure modes and diagnostics
- Look for stale event nodes, repeated key-down from hold, chord suppression firing after a component release, a launcher listener attached twice, and Recents flickering because it is recreated instead of persisted. A hardware key event is not evidence that touch works.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The selected input device, key codes, and timing windows match `button-fsm.json` at the execution commit.
2. All 20 existing FSM traces plus new negative cases pass.
3. Home returns to Desktop 1, Recents persists, short Back follows app history, and long Back does not terminate system services.
4. No action is dispatched twice for one press/chord, and touch gestures do not fire the same action again.
5. Volume repeat reaches the expected level without exceeding the protective cap.
6. The emergency Power+VolumeDown behavior remains owned by hardware/bootloader and is not intercepted.
7. Physical owner results are recorded per button/gesture and remain NOT TESTED until confirmed.

## Hardware, privilege and rollback safety
Do not grab the touchscreen or take exclusive ownership of gpio_keys. No kernel, partition, or flash changes. Long-press destructive actions require the reboot gate and explicit confirmation.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r16-hardware-buttons-gestures`, with tests and docs for this component only.
- `docs/component-reports/r16.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the real key map differs from the protected A32 floor or if fixing dispatch requires changing kernel input handling. File a separate kernel blocker rather than widening this branch.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
