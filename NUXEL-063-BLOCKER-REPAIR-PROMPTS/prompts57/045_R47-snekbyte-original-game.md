# NUXEL R47 — SNEKBYTE — port the original game
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r47-snekbyte-original-game`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Port the original SNEKBYTE game faithfully from the repository's upstream/provenance material, preserving rules, visuals, scoring, input, pause/resume, and saved state. Do not replace it with an invented generic Snake clone.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `tools/s10plus/a33/snekbyte/UPSTREAM-PROVENANCE.md`, `tools/s10plus/a33/snekbyte/upstream-manifest.json`, `tools/s10plus/a33/snekbyte/upstream/`, `tools/s10plus/a33/snekbyte/fixtures/parity.json`, `tools/s10plus/a33/snekbyte/parity-run.js`, `tools/s10plus/a33/snekbyte/tests/test-snek-parity.py`, `pwa/nuxel-apps/snekbyte/`, and `pwa/nuxel-apps/snekbyte/tests/test-snek-engine.js`. Upstream source and parity fixtures already exist; this branch must preserve them.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns SNEKBYTE game parity, rendering/input adaptation, scoring/state persistence, and touch/keyboard UX. Does not own the launcher or a new game design. No invented rules or assets that contradict upstream.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Verify upstream provenance, license, source hash, and parity fixture version before changing the game.
2. Map upstream rules/state transitions to the PWA engine and run the existing parity suite.
3. Preserve original visuals/audio where applicable, with responsive scaling for the S10+.
4. Implement touch controls (swipe/dpad) and hardware keyboard input without changing game timing.
5. Implement pause/resume, app backgrounding, and saved high score/state consistently.
6. Test collision, food spawning, growth, wrap/death rules, score, pause, restart, and corrupted saved state.
7. Perform a play-through on the phone or a faithful browser session and record differences.

## Failure modes and diagnostics
- Watch for a tick loop tied to rendering frame rate, double input on touch+pointer events, and a rewritten game that no longer matches the parity fixtures. Preserve upstream semantics.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Upstream provenance/license and fixture hashes are recorded.
2. The parity suite passes for game rules, scoring, collision, food, and state transitions.
3. Touch and keyboard controls produce the same game actions without double-stepping.
4. Pause/resume/background/restart preserve the intended state and do not corrupt the score.
5. Visual scaling preserves the original look without touch targets outside the viewport.
6. Saved state corruption is handled safely.
7. An owner/browser play-through is recorded separately from parity tests.

## Hardware, privilege and rollback safety
No untrusted asset/code import, no hidden network dependency. Keep the game offline and safe.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r47-snekbyte-original-game`, with tests and docs for this component only.
- `docs/component-reports/r47.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the upstream license/provenance is unclear. Do not claim a faithful port without parity evidence.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
