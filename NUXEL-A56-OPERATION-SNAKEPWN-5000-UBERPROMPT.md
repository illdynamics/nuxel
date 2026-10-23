# 🐍🔥 NUXEL A56 — OPERATION SNAKEPWN 5000
## Hyperfocused SnekByte Python → Nuxel PWA integration, correct icon, real WoNQ Poop-o-meter, live S10+ verification

**Executor:** GPT-5.6 Sol (High thinking) or DeepSeek-v4-pro-thinking.
**Device:** Samsung Galaxy S10+ SM-G975F, Fedora ARM64 Nuxel, Phoc/Wayland + WebKitGTK.
**Repository:** owner's **current** Nuxel checkout (not the older v0.6.3-beta reference).
**Input:** root-level SnekByte Python archive (e.g. `snekbyte-main (2).zip` or another name) plus patched `snekbyte-main-SNAKEPWN-5000-dropin.zip` supplied by the owner.
**Required result:** SnekByte visibly installed as a launchable Nuxel app with its exact pixel-art snake-and-poop icon; playable with touch, keyboard, smooth layout; full WoNQ Poop-o-meter and genuine poop obstacles; persistent preferences; no regressions to Home or device stability.

## NON-NEGOTIABLE HONESTY

- **Don't mark installed until it is deployed and opened on the physical S10+.** A PWA in a repository is not a phone installation.
- **Don't invent current Nuxel registry names/paths** from old documents. Inspect the live branch first.
- **Do not silently overwrite newer SnekByte work in current Nuxel.** Compare the supplied patch against the current working files; merge carefully; preserve improvements.
- **Do not replace SnekByte with a generic Snake game.** The Python/Pygame original is the gameplay authority. Its config, speed table, movement, collision, food handling and WoNQ threshold are specifically represented in the JS port.
- If any requirement is blocked by the current host app lifecycle/launcher, fix that integration properly instead of making a disconnected demo.
- **No kernel flashing, raw partition writes, TWRP, bootloader changes, rootfs replacement, insecure privileges or unrelated refactors.** This is a userspace game integration.

---

## PHASE 0 — BASELINE / CURRENT STATE / BACKUP

1. Identify current Nuxel Git branch, commit, dirty files, target device, USB host-console state and deployment method. Respect concurrent agents and worktrees.
2. Locate all current references to `SnekByte`, `org.nuxel.SnekByte`, `pwa/nuxel-apps/snekbyte`, icon `01-02_snekbyte.png`, Nuxtore catalog, Home launcher, app metadata and application registries.
3. Locate the owner-provided Python ZIP and patched drop-in ZIP. Read their contents before copying anything.
4. Back up existing SnekByte PWA files, actual installed SnekByte files and the current launcher/registry records before edits. Preserve separate off-device backups and hashes.
5. Compare old/new JS engine, game UI, icons and metadata. The patched package contains **known offline-tested** code, not an authoritative replacement for all current Nuxel files.
6. Record baseline in `docs/a56-snakepwn/BASELINE.md`. Do not claim Nuxel already has a working game just because an app directory exists.

## PHASE 1 — UNDERSTAND THE UPSTREAM PYTHON GAME

Inspect actual uploaded source, not just README:

- `src/game_loop.py` is the entrypoint gameplay loop via `src/main.py` and `main.py`.
- `src/config.py` declares an 800×600 screen, 20px cells, 40×30 grid, speed levels `[5,8,12,16,20]`, default speed index 2, `WONQ_MODE_POOP_THRESHOLD = 5`.
- `src/snake.py`: one-segment starting snake at (20,15), moving right; blocks opposite turn after growth.
- `src/game_logic.py`: eat food, increase score and length, spawn a new food item avoiding occupied cells, handle wall/self/poop collision, increment/reset the `shit_counter`, and create a persistent poop obstacle each fifth food in WoNQ mode.
- `src/game_state.py`: speed settings and WoNQ mode toggle.
- `src/ui.py`: upstream textual Poop-o-meter.
- `src/poop.py`: persistent brown obstacle; hitting one ends game in WoNQ mode.

**Preserve original behavior**, including the timing quirk where growth appears on the next step. The historical Nuxel JS port was Python-parity-tested over 41 ticks with three endings. Its core is included under `js/snek-engine.js` and must not be rewritten casually. If you change game rules, add explicit unit tests and explain every departure.

The patched Nuxel UI intentionally defaults WoNQ **ON** so the meter is visible, while the Python/JS canonical configuration still defaults OFF. This is an explicitly documented presentation-level preference, not a stealthy rules change.

## PHASE 2 — APPLY THE PATCHED APP WITHOUT REGRESSIONS

Use the provided archive's `nuxel-dropin/pwa/nuxel-apps/snekbyte/` files as the basis for the installed app. The patched PWA uses:

- `index.html` — real mobile game controls, play/pause/retry/settings, accessible help and meter.
- `css/snekbyte.css` — Nuxel cyan/lime arcade styling; phone safe-area spacing and landscape layouts.
- `js/snek-engine.js` — original Python logic, parity reference.
- `js/snekbyte.js` — DOM controls, canvas renderer, state/lifecycle, D-pad, touch swipes, score/settings.
- `app.json` and `manifest.json` — `org.nuxel.SnekByte`, network-free games PWA metadata.
- `sw.js` — optional scoped offline worker; must never delete cache owned by other apps.
- `icons/icon-*.png` — the correct snake-with-poop pixel-art image, NOT the earlier green "SB" placeholders.

**Merge, don't bulk overwrite**, if the current branch has newer capabilities. Keep gameplay data private to this app; no new privileged bridge verbs, network API, backend daemon or package dependencies needed to play.

## PHASE 3 — CORRECT ICON IN EVERY LOCATION

The historical Nuxel art already supplies the exact game icon:

`assets/nuxel-applications-icon-pack/01-02_snekbyte.png`

It depicts a green pixel snake next to a poop pile. The patched ZIP ships it at the above path and optionally at:

`pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-02_snekbyte.png`

It also has appropriately scaled PWA icons in `icons/`.

1. Identify the actual current source of Home/app drawer icons and app metadata.
2. Show the correct SnekByte icon in the Nuxel Home app drawer, recents card, installed-app listing and PWA manifest wherever supported.
3. Use correct scaling (`image-rendering: pixelated` where appropriate), alpha preservation and a clean square viewport; no generic SB initials, emoji in place of the provided art or broken-path placeholders.
4. Do not overwrite unrelated app-pack sprites or change Home icons wholesale.
5. Validate after current branch build and on the S10+ itself.

## PHASE 4 — ACTUALLY REGISTER AND LAUNCH THE GAME

- Inspect current `app.json` discovery rules, launcher manifests, application registry schema, Nuxtore app catalog, application routes and whatever `nuxel-webapp` wrapper exists now.
- Register the actual `org.nuxel.SnekByte` with type `pwa`, category `games`, network access `none`, touch and keyboard capabilities. If an app entry already exists, update it idempotently rather than duplicating an icon or app instance.
- Ensure tapping its Home icon creates **one real SnekByte app instance**, not a preview card/iframe-only simulation or an unrelated web page. The app must enter the existing Recents system, preserve Home/back behavior and reclaim CPU when backgrounded.
- Ensure the URL/path matches the real deployed static server mount; in the old tree it was `/pwa/nuxel-apps/snekbyte/index.html`, but do not assume the live web root is unchanged.
- Verify the app works without internet. Service workers are optional depending on WebKitGTK support, but core assets must all be local and load offline.
- Ensure the game is not displayed behind unclickable overlays and its on-screen D-pad stays above the Nuxel system navigation bar, without duplicating system navigation.

## PHASE 5 — PERFECT REAL MOBILE GAMEPLAY

Required interaction:

1. Launch → responsive Nuxel-styled main menu, not a blank pygame screen or raw HTML directory.
2. Tap **PLAY** → real gameplay starts immediately.
3. Swipe horizontally/vertically on game canvas to steer; one accepted turn per simulation tick to prevent accidental 180-degree reversal. D-pad must also work. Arrow/WASD keyboard remains supported.
4. Pause/Resume works; Back/Escape routes to the appropriate overlay without trapping the entire system or taking over the Nuxel Home button.
5. Score increments when food is consumed; snake grows according to actual Python game semantics.
6. Collisions cause proper Game Over screen. Retry and Menu are touch-operable.
7. Landscape and portrait are responsive; adapt visuals without silently modifying the canonical game grid/rules.
8. Settings contain speed, WoNQ mode, grid toggles and persistence. Changes made during an active round should apply at a clearly defined boundary—prefer next round for rules-changing settings.
9. High score and settings persist through app exit, restart and phone reboot where WebKitGTK storage policy allows, without syncing network state.
10. On Home, Recents, lockscreen, screen off or visibility loss, **stop the active game timer / animation** and resume paused. Do not waste CPU/heat while the screen is off.
11. No mandatory browser audio, microphone, network permissions or API calls.

## PHASE 6 — FULLY IMPLEMENT THE POO-METER, NOT A FAKE COUNTER

Nuxel's funny distinguishing feature must be central to gameplay:

- The HUD says **POOP-O-METER**, has a real five-segment progress bar, shows `0 / 5` through `4 / 5` progress and is readable on an S10+ portrait screen.
- Progress increases **only when food is actually eaten**, not when a timer fires or the snake moves.
- On the fifth meal, the original engine generates a poop obstacle at the snake tail, counter resets to zero, meter flashes and a brief `💩 POO DROP!` feedback appears.
- Poop is visually represented with recognizable brown pixel-art, persists on the board and is a real collision hazard when WoNQ mode is active.
- Game-over from a poop collision is distinguishable from wall/self collisions.
- Turning WoNQ off via Settings has clearly defined effect and does not silently corrupt an existing round. The default-on setting is intentional for the Nuxel demo; can be disabled by the player.
- When WoNQ is off, the UI says disabled; don't show fake progress.
- All meter values derive from `game.shitCounter` and `game.config.wonqModePoopThreshold`. Never maintain a second, inconsistent pseudo-counter.
- If phone font lacks the emoji, numeric bar/text must remain readable and the actual poop hazard must still draw from canvas geometry.

Required tests: 0/5, first meal 1/5, fourth meal 4/5, fifth creates one poop and resets 0/5, repeated cycles create additional obstacles, collision ends run, WoNQ disabled makes obstacles inert as original rules specify.

## PHASE 7 — NO SNAKE-BATTERY-EATER REGRESSION

Check `requestAnimationFrame` ownership and frame budget. The patched shell renders the board after simulation state changes, not uselessly redrawing a static menu at 60 FPS. Only run simulation when playing and foreground. Cap delta after stalls to prevent catch-up storms, and trim event log history.

Measure current phone CPU use, wakeup activity, memory, thermal observations, input latency and display composition in foreground/paused/background/screen-off, without invasive root-level governors or frequency tweaks. Battery improvement must be measured, not asserted from code inspection alone.

## PHASE 8 — TESTS, DOCUMENTATION AND APPLICATION-LEVEL ACCEPTANCE

Execute in the patched SnekByte source:

```bash
node nuxel-dropin/pwa/nuxel-apps/snekbyte/tests/test-snek-engine.js
python scripts/check-snekbyte-bundle.py
node --check nuxel-dropin/pwa/nuxel-apps/snekbyte/js/snekbyte.js
```

Known sandbox result for this supplied patch: **48 passing engine/packaging assertions** including no divergence over 41 upstream parity ticks. The package checker requires Pillow. Re-run tests after merging; do not count prior results as validation of the new branch.

Also test using Nuxel's WebKitGTK application wrapper on ARM64 and run physical S10+ acceptance:

- Home game icon exists with correct image. Tap → SnekByte immediately opens.
- Tap Play → game moves, on-screen arrows and swipes steer correctly. No click-through or duplicate system Back/Home icons.
- Eat five snacks in WoNQ mode, observing each meter increment and actual poop obstacle on #5. Verify actual poop death, retry and controls.
- Change speed and WoNQ setting, close/reopen app, verify persistence.
- Test pause and Home/lock/background behavior; screen-off CPU load should decrease.
- Test portrait/landscape, navigation bar safe areas and two successive launches.
- Reboot only after the owner has authorized an appropriate reboot window; verify icon/game still present and high score/settings retained.

Save results to `docs/a56-snakepwn/`: `BASELINE.md`, `CODE-MERGE.md`, `ICON-CHECK.md`, `PARITY-TESTS.md`, `PWA-ACCEPTANCE.md`, `DEVICE-ACCEPTANCE.md`, `ROLLBACK.md`.

## PHASE 9 — DEPLOYMENT / ROLLBACK

- Stage SnekByte app files and icon only; run current Nuxel application registry validation and URL checks.
- Keep an untouched, independently verified backup of the old installed game and launcher entries before deployment.
- Use the **proven** userspace deployment method over live USB; verify hashes and only restart affected services. Do not reboot or relaunch the compositor unnecessarily.
- If icon, navigation, launcher, WebKitGTK load or game logic regresses, revert the app + minimal changed registry entries using backups, verify Home/other apps unchanged and report the blocker.
- No flash, no kernel alterations, no privileges, no broad upgrades, no fake on-device PASS status.

## FINAL DELIVERABLES / VERDICT

Return exact changed paths and commit, original Python license/provenance caveat, engine test counts, physical phone video/screenshots if available, relevant logs/hashes, on-phone game score and five-food poop evidence, icon match, persistence test, thermal observation, known blockers and rollback path.

Statuses must distinguish `OFFLINE_TESTED`, `INTEGRATED_IN_SOURCE`, `DEPLOYED_TO_S10PLUS`, and `PHYSICALLY_VERIFIED`.

**SUCCESS = Actual S10+ → tap proper pixel-art SnekByte icon → touch-play original snake → five food → Poop-o-meter resets as a poop pile appears → don't step in it → Home/lock works → reopen and saved settings remain.**

**GO MAKE THE PENGUIN PLAY SNEKBYTE. OPERATION SNAKEPWN 5000. 🐧🐍💩🔥**
