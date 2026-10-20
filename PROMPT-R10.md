# NUXEL R10 — Wallpaper and color pipeline
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r10-wallpaper-color-pipeline`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make wallpaper, dock artwork, transparency, scaling, and colour conversion correct across desktop pages and orientations. This branch must keep the wallpaper stationary while icon grids slide, preserve the original BG1/BG2 artwork, and prevent alpha/colour/framebuffer conversion from producing dark, washed-out, shifted, or cropped output.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `assets/nuxel-background.png`, `assets/nuxel-bottom-bar.jpg`, `assets/nuxel-bottom-bar2.png`, `pwa/nuxel-home/assets/`, `pwa/nuxel-home/css/style.css`, `pwa/nuxel-home/css/launcher.css`, `pwa/nuxel-home/js/launcher.js`, `pwa/nuxel-home/colour-test.html`, `docs/beta-finalization/boot/COLOUR-CONVERSION.md`, and `tools/s10plus/a33/nuxel-wl-fb.c`. The repo includes a colour-test page and dock assets; it does not prove the current panel output is colour-accurate.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns wallpaper/dock compositing, alpha handling, CSS layer separation, source-image fidelity, and framebuffer colour-format assumptions. Does not own boot animation video timing or unrelated launcher actions. Do not redesign the artwork.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Record source dimensions, colour profiles, alpha channels, and hashes for background, BG1 JPG, and BG2 PNG.
2. Trace how desktop pages are panned while wallpaper and dock remain stationary; identify the transformed element and confirm it does not carry the wallpaper.
3. Test BG2 alpha compositing over the wallpaper at the real S10+ panel resolution, checking black fringes, halos, and premultiplication artifacts.
4. Compare the colour-test page and a real wallpaper through the display bridge to detect RGB/BGR, limited/full range, gamma, or stride errors.
5. Verify portrait and any supported landscape mode for scaling, cropping, and safe-area alignment.
6. Add deterministic image/layout checks for alpha, dimensions, and dock placement; keep visual comparison evidence separate.
7. Document the intended colour pipeline from CSS/WebKit to the framebuffer in one diagram or table.

## Failure modes and diagnostics
- Look for `background-attachment: fixed` behaving differently in WebKit, double-applied transforms, JPEG dock background used where transparency is required, CSS `filter`/opacity creating a new compositing layer, and framebuffer stride/format mismatch.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The wallpaper remains stationary while switching desktop pages; only the icon layer moves.
2. BG2 renders with correct transparency and no black/white edge halo on the phone.
3. BG1 and BG2 source hashes match the canonical assets and both remain selectable.
4. Desktop scaling preserves aspect/coverage without unintended cropping of icons or dock.
5. The colour-test page shows the expected primaries and gradients without channel swap or range clipping.
6. No duplicate background layers cause memory/GPU waste or flicker during page changes.
7. A captured phone image is compared against the expected reference with differences classified, not hand-waved.

## Hardware, privilege and rollback safety
Userspace-only changes. Do not alter panel drivers, kernel modes, or flash. Keep the display bridge single-owner and preserve a rollback copy of every deployed asset/CSS file.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r10-wallpaper-color-pipeline`, with tests and docs for this component only.
- `docs/component-reports/r10.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the panel output cannot be captured without disturbing the running UI. Report the exact colour/format evidence and the first unverified hop.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
