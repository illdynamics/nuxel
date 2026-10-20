# NUXEL R20 — Screen gestures
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r20-screen-gestures`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Centralize screen gesture ownership so upper-half Quick Settings, lower-half app drawer, horizontal desktop paging, long-press drag, scrolling, and dismissal do not fight each other. This branch must define direction/zone/velocity thresholds, prevent one gesture from firing twice, and preserve normal app scrolling.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-home/js/gestures.js`, `pwa/nuxel-home/js/launcher.js`, `pwa/nuxel-home/js/app.js`, `pwa/nuxel-home/js/qs.js`, `pwa/nuxel-home/js/search.js`, `pwa/nuxel-home/js/scroll-indicators.js`, and `pwa/nuxel-home/js/status-bar.js`. Historical reports describe accidental dismissal, missing pull-down dispatch, and scroll/drag conflicts, but current source and behavior must be re-measured.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns gesture recognition, zone/direction arbitration, pointer capture, gesture cancellation, and animation triggering in the launcher. Does not own hardware-button gestures or the Quick Settings backend controls. No duplicate global listeners and no gesture that swallows every touch.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Map every active pointer/touch listener and identify overlaps between drawer, Quick Settings, desktop paging, icon drag, search, and app frames.
2. Define a priority table: system edge gesture vs launcher paging vs long-press drag vs scroll vs tap.
3. Implement a single recognizer/state machine with direction, distance, velocity, zone, and cancel thresholds.
4. Fix accidental click/dismissal when a drag begins, pointer capture across drawer unmount, and duplicate open/close animations.
5. Test scrolling inside long app lists and nested scrollable panels while gesture recognizers are active.
6. Add deterministic gesture traces for tap, horizontal swipe, vertical swipe from both halves, diagonal ambiguity, long-press-then-drag, and cancel.
7. Verify no gesture action is emitted twice for one physical sequence.

## Failure modes and diagnostics
- Common defects: listeners on both `document` and `window`, `touchstart` calling `preventDefault` too early, pointer capture lost when a drawer is removed from the DOM, animationend not removing a transparent overlay, and scroll indicators intercepting touches.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. A single documented recognizer owns each gesture and there are no duplicate global listeners.
2. Upper-half pull-down opens Quick Settings; upward collapse closes it; lower-half swipe opens the drawer/settings progression as specified.
3. Horizontal paging works without stealing vertical scroll.
4. Long-press drag claims the pointer only after the threshold and cancels cleanly.
5. A diagonal/ambiguous gesture resolves by the documented priority and cannot fire two actions.
6. Normal app scrolling and text selection remain usable.
7. Recorded trace tests cover at least eight gesture scenarios and pass.

## Hardware, privilege and rollback safety
Do not replace the launcher gesture system or add a second gesture daemon. Preserve touch usability and the three gesture zones. No hardware or flashing changes.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r20-screen-gestures`, with tests and docs for this component only.
- `docs/component-reports/r20.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a required gesture cannot coexist with app scrolling without a product decision. Document the trade-off and leave the conflict explicit rather than stealing all input.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
