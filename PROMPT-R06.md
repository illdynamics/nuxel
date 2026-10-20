# NUXEL R06 — PRIORITY ZERO — Get the touchscreen fully working
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r06-touchscreen-fully-working`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make the real S10+ touchscreen reliably drive Nuxel from finger contact through the compositor to the WebKit DOM and visible app response. This branch owns the end-to-end touch path, not just driver registration: tap, multitouch, swipe, drag, long-press arbitration, pointer capture, coordinate transforms, overlay interception, and immediate redraw.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/libinput/nuxel-s10plus-touch.conf`, `configs/s10plus/libinput/99-nuxel-beyond2lte-touch.conf`, `pwa/nuxel-home/js/launcher.js`, `pwa/nuxel-home/js/app.js`, `pwa/nuxel-home/js/gestures.js`, `pwa/nuxel-home/js/navigation.js`, `tools/s10plus/a33/nuxel-touch-trace.py`, `tools/s10plus/a33/nuxel-touch-capture.sh`, and `tools/s10plus/a33/nuxel-wl-fb.c`. Historical A34 evidence proves some physical taps reached WebKit, but later user reports still describe unreliable interaction; neither old proof nor a synthetic click may be treated as current success.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns evdev/libinput/Phoc/WebKit touch delivery, touch coordinate mapping, launcher gesture arbitration, pointer capture, and the diagnostic correlation path. Does not own unrelated app business logic or a new compositor. The S10+ uses `sec_ts`/`sec_touchscreen`; charger-mode boot may disable it before userspace runs.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Capture one physical tap and one drag with correlated timestamps at evdev, libinput, Phoc, WebKit `pointerdown`/`touchstart`, DOM handler, app launch, and presented frame.
2. Verify the actual touch device selected by name/capabilities and confirm `INPUT_PROP_DIRECT`, `ABS_MT_POSITION_X/Y`, tracking IDs, and coordinate ranges after any libinput transform.
3. Test tap, double-tap, long-press, horizontal desktop swipe, vertical Quick Settings/drawer gesture, icon drag, drag cancel, and multitouch without creating duplicate clicks.
4. Audit overlays and app iframes for stale full-screen surfaces, `pointer-events`, z-index, focus, and pointer capture that can intercept later touches.
5. Instrument the first failing hop and fix that layer; add deterministic regression tests using recorded event sequences without claiming they prove hardware.
6. Verify immediate visible frame presentation through `nuxel-wl-fb` and ensure a tap does not require a Power press to repaint.
7. Define a bounded owner test that records PASS/FAIL for each required gesture on the physical phone.

## Failure modes and diagnostics
- Distinguish charger-mode/LPM (no `sec_ts` init), missing IRQ, missing `/dev/input` node, libinput transform mismatch, Phoc surface/focus bugs, WebKit touch-action/capture bugs, invisible overlay, stale service-worker cache, and framebuffer presentation failure. Do not call hardware-button events touch events.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. A physical tap on one launcher icon opens exactly that app and produces a visible frame without a Power-key workaround.
2. A drag that leaves the drawer/grid does not drop early, duplicate a click, or leave a captured pointer behind.
3. Quick Settings and app-drawer gestures obey zone/direction rules and do not steal normal scrolling.
4. Coordinate mapping is correct at all four edges and in the supported orientation(s); the reported transformed range matches the hit target.
5. Long-press opens the intended edit/menu state once, and release/cancel produces no accidental launch.
6. A failed touch stage is identified by name with raw evidence, and the owner test remains NOT TESTED until the owner confirms it.
7. Offline event-replay tests cover tap, drag, cancel, multitouch, and stale-overlay regression cases.

## Hardware, privilege and rollback safety
Touch testing requires physical finger input; never claim OWNER-VERIFIED from `evemu` or synthetic events. Preserve the USB console and the working A32/A34 input floor. No kernel replacement, flashing, or partition writes; if the vendor kernel has a proven charger-mode blocker, document the normal-reboot remedy.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r06-touchscreen-fully-working`, with tests and docs for this component only.
- `docs/component-reports/r06.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the physical touch node is absent in a normal boot or if the first failing layer requires kernel/driver work beyond userspace. Do not widen into a launcher rewrite; report the precise blocker and the smallest safe next step.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
