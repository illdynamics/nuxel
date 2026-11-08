# 🐍💩⚡ NUXEL A58 — OPERATION SNAKEPWN 7000: BUTTER-SNEK OVERDRIVE

## Owner's live feedback — authoritative requirements

**The SnekByte game now WORKS. Preserve that.** This mission is a focused gameplay + input-latency + performance update, not a rewrite of the project.

Owner-requested changes:
1. **Adjustable game speed**, with accessible settings, persistently saved, and changes actually taking effect during an active round.
2. **Infinite edge wrap:** crossing the right edge reappears at the left edge, left→right, top→bottom, bottom→top, seamlessly, indefinitely. No death merely from reaching a wall. Wrap is the default gameplay mode.
3. **Fix slow/delayed touch controls** so swipe and on-screen buttons feel immediate and turns are registered reliably, including fast consecutive turns.
4. Preserve **WoNQ Mode**, the **Poop-o-meter** (poop every five actual snacks), food, scoring, self-collision, poop obstacles, the correct snake+poop icon, menus, pause, persistent scores, the offline PWA, and the Android APK.

**Primary platforms:** the now-working Android SnekByte APK and the Nuxel/Fedora SnekByte PWA. Keep the **game engine and assets shared** where practical; do not maintain divergent game rules. The current installed app may be newer than any archived ZIP, so always inspect the *live repository* and preserve newer changes.

**Recommended executor:** DeepSeek-v4-pro-thinking for this scoped mission; GPT-5.6 Sol (High) if architecture, Android packaging, or event handling repeatedly blocks progress.

**Required outcome:** a demonstrably smoother, installable Android SnekByte APK and updated Nuxel game bundle, with passing tests, physical input checks when devices are available, and rollback packages. **No fake installed/tested claims.**

---

## PHASE 0 — AUDIT THE ACTUAL SOURCE, NOT AN ASSUMED VERSION

Find the latest SnekByte game in the repo, its JS engine, touch UI, Python reference game, test suites, and Android wrapper. Record Git revision, dirty files, game version, APK application ID, signing identity, build toolchain, Nuxel PWA manifest, asset/service-worker versions, and current installation paths. Build a read-only baseline and run available tests before changes. Back up the current working PWA and Android artifacts.

### Confirmed findings in older A56 drop-in (verify against current source)

Earlier archive `snekbyte-main-SNAKEPWN-5000-dropin.zip` contained:

- `snekbyte-main/nuxel-dropin/pwa/nuxel-apps/snekbyte/js/snek-engine.js` — grid-based game engine.
- `.../js/snekbyte.js` — canvas renderer, touch/key inputs, rAF scheduler, menus, settings.
- `.../index.html`, `.../css/snekbyte.css`, `.../sw.js`, `.../tests/test-snek-engine.js`.
- `snekbyte-main/src/` — original Python/Pygame implementation, intentionally preserved.

The older engine had a **wall-death check** in `step()` after `move()` (head outside `[0,width) × [0,height)` sets `cause='wall'`). It had five speeds `[5,8,12,16,20]` ticks/s. The UI `sendDirection()` allowed one turn per tick using `directionQueued`. `initSwipe()` interpreted gestures **only on `pointerup`**, after a **22 CSS-pixel** threshold. D-pad buttons bound **`click`**, not immediate press events. A `speed-setting` slider changed `view.settings.speedIndex`, but `startGame()` cloned an independent `view.activeSettings` and `tickMs()` consulted that active copy—so speed changes made while playing could be delayed until next game. The scheduler used `requestAnimationFrame`, accumulator stepping and a three-step catch-up limit.

**These are inspection targets, not assumptions that the latest version is unchanged.** Trace existing event flow and runtime state before modifying code. Keep all newer user fixes.

Write `docs/a58-snakepwn-7000/BASELINE.md` summarizing the actual discovered architecture and reproducible baseline with any physically observed latency.

---

## PHASE 1 — DESIGN THE PLAY EXPERIENCE

### Speed control

- Add an **obvious speed control** in Game Settings and, ideally, a small unobtrusive in-game speed selector or `− / +` buttons accessible without accidentally steering the snake. Display current speed numerically as **cells/ticks per second** with an easy-to-read human label (e.g. Easy, Normal, Fast, Insane). Set a sensible normal default, not an unexpectedly extreme speed.
- At minimum retain old rates; consider levels like **5 / 8 / 12 / 16 / 20 / 24 / 30 ticks per second**, subject to device testing. It may be safer to cap the actual maximum below 30 on weaker devices. Do **not** hardcode unsupported performance claims.
- Users must be able to change speed **mid-game**, without killing the round, changing score, moving the snake unexpectedly, resetting the poo-meter, or waiting for a new game.
- Changes must persist across pause/resume, app background/foreground, app restart and an authorized OS reboot, including inside the Android WebView/Capacitor wrapper.
- Apply a changed speed through the **authoritative active simulation settings**, not only to the settings menu's saved copy. Ensure the simulator reacts on the next scheduled update; reset/rebase timing in a documented, fair way instead of causing an immediate multi-cell jump.
- Update labels and `tickMs()` from the same source of truth; bound invalid/corrupt persisted preferences; migrate any earlier key format without losing high scores or WoNQ settings.
- Keep the UI usable while rotated, and avoid a modal overlay obstructing the D-pad or playfield unless gameplay is automatically paused.

### Wraparound boundaries

- **Default ON: infinite wraparound.** This is the desired normal experience, with no game-over on crossing the board edge.
- Move one logical grid cell per tick and normalize the new head using correct positive modulo:

  `wrappedX = ((x % gridWidth) + gridWidth) % gridWidth`

  `wrappedY = ((y % gridHeight) + gridHeight) % gridHeight`

- Preserve direction and movement cadence through wrap. The snake must emerge from the **opposite side in the same row/column** with no teleport to board center, no skipped cell, no coordinate overflow, and no slow animation that blocks input.
- When the body straddles opposite edges, **render its cells correctly in both places**. Don't draw an incorrect full-screen line joining its head and body across the canvas. If the renderer uses independent grid-cell drawing, retain it.
- Collision detection must compare the **wrapped position**, not the out-of-bounds intermediate position: still die when meeting one's own body or a poop obstacle at the destination. Food eaten on the opposite boundary must increment the score exactly once; spawn food/poop only in valid, unoccupied grid cells.
- Keep the WoNQ poop placement semantics correct when a snake crosses the boundary. No duplicate poop creation and no lost progress on meter reset.
- Optionally offer **Classic Walls** as an explicit *opt-in* retro mode, if cheap to implement without clutter. If offered, default wraparound ON, persist the setting, and show the mode clearly. Never silently switch users back to wall-death behavior.
- Keep 180-degree reversal illegal when the snake has multiple body segments. Do not introduce edge-collision bypass for self- or poop-collisions.
- Distinguish the intended gameplay change from the Python reference: preserve the original Python game unchanged unless the owner explicitly needs the Python version updated too. Keep legacy parity fixtures valid in Classic Walls mode if that mode remains; create *new wrap-mode fixtures/tests* instead of deleting conflicting tests.

---

## PHASE 2 — ROOT-CAUSE AND FIX INPUT LATENCY (TOP PRIORITY)

**Do not just increase tick rate and call it responsive.** Diagnose touch-event recognition latency, queued input handling, simulation cadence, paint/compositor delay and Android WebView touch dispatch separately.

### Instrumentation (development-only)

Collect monotonic timestamps and bounded per-event traces:

`physical gesture → pointerdown/move → recognized direction → queued/accepted command → applied simulation tick → drawn frame`

Where feasible, show event timestamp deltas and median/p95 input-to-recognition and input-to-visible-direction indications. Distinguish immediate *control acknowledgement* from movement that correctly occurs only on a game tick. Do not fabricate physical input-to-photon timings without measuring a real display/camera.

### Immediate D-pad input

- Replace delayed `click`-only steering on D-pad with **primary `pointerdown` handling** or a carefully chosen pointer/touch primitive supported on both WebKitGTK and Android WebView.
- Call the direction-acceptance path on finger *press*, not release. Preserve mouse/keyboard accessibility, but avoid double-applying `pointerdown` plus subsequent compatibility `click` to the same gesture.
- Assign touch action only to game controls (`touch-action: none` where supported). Do **not** disable normal gestures or scrolling across the entire Nuxel shell or Android system navigation areas.
- Support quick distinct consecutive presses, even when they arrive between two simulation ticks. Provide tactile or visual acknowledgement where available without forcing haptics permissions; haptics are optional and must be user-configurable if implemented.
- If long-press direction repeat exists or is added, make it deterministic and never flood the queue with redundant identical inputs.

### Real-time swipe recognition

- Do **not** wait for `pointerup` to recognize a completed steering gesture. Detect a meaningful direction during `pointermove` as soon as a modest **device-appropriate movement threshold** is crossed (e.g. initially 12–18 CSS px, tune on real touchscreen).
- Prevent accidental micro-jitter and taps from changing direction. Use dominant-axis detection, appropriate hysteresis, and lock/renew the swipe origin only after an accepted directional segment.
- Support multiple intentional turns from distinct swipe segments when a user keeps dragging, without allowing one noisy motion to trigger a dozen turns.
- Manage `pointerdown`, `pointermove`, `pointerup`, `pointercancel` and `lostpointercapture` robustly with stable pointer IDs. Never confuse pointer capture loss with a completed gesture; avoid `pointerup` duplicate turns after one was recognized on move.
- Handle orientation changes, canvas resizing, CSS/device pixel ratios, and taps over controls correctly. Avoid blocking the main thread with costly listeners; use passive vs. non-passive listeners purposefully rather than globally calling preventDefault.

### Deterministic direction buffering

The earlier `directionQueued` boolean silently dropped inputs while waiting for the next tick. Replace it with a **small bounded direction queue** (typically 2 commands; tune through testing) that:

1. Buffers a meaningful rapid sequence such as Right → Up → Left across consecutive ticks, preserving the order.
2. Applies **at most one valid turn per simulation tick** to keep standard Snake rules and avoid impossible movements.
3. Validates against the **projected heading of the last queued accepted command**, not just the current physical heading, preventing Right → Up → Down from sneaking in an illegal instant reversal.
4. Rejects duplicates and opposite/reversal inputs deterministically.
5. Drops or coalesces stale inputs with an explicit policy rather than piling up commands and causing a “delayed snake” seconds later.
6. Clears the queue on new game, pause, game over, background, lock, input-mode reset or explicit game reset as appropriate.
7. Does not consume a command on a simulation tick that never actually occurs.

Write unit tests for the queue independently of the DOM. **The desired feel is immediate acknowledgement and a turn on the next valid grid tick, never a hidden multi-tick input backlog.**

### Isolate a true application-level delay

- Check Android WebView / Capacitor `touch-action`, viewport, click-delay compatibility, focus and gesture recognizers. Ensure the application is not accidentally intercepting input via outer overlays, SVG pointer regions, scroll containers, click handlers or Android back gestures.
- Inspect whether canvas is CSS-scaled and if hit regions become tiny. Increase button touch targets to **approximately 44–48 CSS px minimum**, within available screen space.
- Inspect Nuxel-specific display pipeline: older Nuxel builds used a Phoc/Wayland screencopy-to-framebuffer bridge; if delay is measured *below* the game (compositor/display pipeline), report exact evidence and avoid hacks in SnekByte that cannot solve it. **Do not change Nuxel's system-wide display pipeline as part of this game mission.**

---

## PHASE 3 — GAME TICK VS. RENDER LOOP: SMOOTHNESS WITHOUT GAMEPLAY DRIFT

- Keep a fixed-step, deterministic grid simulation separated from painting. The player chooses **simulation ticks per second**; rendering may occur at the display's available cadence without changing logical speed.
- Prefer `requestAnimationFrame` for foreground painting; use a bounded time accumulator with monotonic timestamps for engine ticks.
- Do not change movement speed based on frame rate or network availability. Never use naive `setInterval` as the sole clock if background tabs, missed frames, and timers produce drift.
- Prevent **speed-slider changes** from producing accumulator catch-up bursts or long pauses. Reset/rebase the accumulator safely and make one speed authoritative.
- Use an explicit maximum catch-up budget; don't turn a temporary WebView stall into 10 instant unintended snake moves or a hot CPU loop. Report if a high selected rate cannot be sustained.
- Make pause, backgrounding, screen-lock, app-switching, Android lifecycle callbacks and visibility changes **pause simulation immediately**, clear input queues, and resume deliberately. Never let a hidden game silently keep moving or drain battery.
- **Avoid redraw storms:** do not repaint when menu/game state is static. Cache invariant grid/background artwork; update DOM HUD only when values actually change. Reuse drawing objects and avoid unnecessarily allocating objects on every frame.
- Preserve crisp pixel-art rendering and correct logical board dimensions/aspect ratio on S10+ and Android phones, including portrait, landscape, high-DPI and safe-area insets.
- If interpolation/animation is introduced, it must not compromise collision correctness or show a visually misleading snake head; favor low-latency rendering of accepted moves over cosmetic interpolation.
- Keep core runtime offline. Do not add remote analytics, ads, account requirement, unnecessary dependencies, or background network traffic.

---

## PHASE 4 — UI/UX: MAKE SPEED + WRAP DISCOVERABLE

Update the Nuxel and Android versions consistently:

- Menu and Settings show a clear **Speed** slider/selector with label and exact numeric tick rate.
- A concise help line explains: **“Walls wrap around — leaving one side enters the opposite side.”**
- Optional `Wrap Walls` toggle, if implemented, is **ON by default** and clearly distinguished from Classic mode.
- During active play, the selected speed is shown in the HUD. If changes during play are permitted via a compact control, it must respond immediately and not occlude the snake canvas.
- Preserve the existing **Poop-o-meter**, score, best score, WoNQ switch, retry/pause, correct green-snake-and-poop app icon, and Nuxel game aesthetics. No generic Snake clone.
- Update Game Over text to remove “The wall won” in wrap mode. Keep accurate `SELF`, `POOP`, and other game-over reasons.
- Persist and migrate preferences atomically where possible; don't clobber the high score when preferences version changes.
- Accessibility: keyboard arrows/WASD, clear buttons, focus labels, UI readable on phone, no audible/haptic effects without respecting system/user settings.

---

## PHASE 5 — TESTS THAT ACTUALLY CATCH THE OLD BUGS

Add/extend automated tests before considering success.

### Wraparound tests

- Right edge → left edge same Y; left → right; bottom → top; top → bottom.
- Multiple consecutive wraps with no game-over, invalid coordinates or phantom walls.
- Food eaten immediately after wrap increments score once.
- Destination cell containing own body **still kills**; destination containing poop **still kills** in WoNQ.
- Tail and body across wrapped seam render in-bounds and collision correctly.
- Poop-o-meter progresses 0/5, 1/5 … 4/5, triggers a single poop on fifth food, resets to 0/5, then repeats.
- Optional Classic mode retains wall-death behavior if implemented.

### Control/input tests

- D-pad `pointerdown` changes/queues direction without waiting for `click`/release; no duplicate on later `click`.
- Swipe command emitted once threshold crossed on `pointermove`, not only on `pointerup`.
- Diagonal and tiny jitter handled consistently; pause/menu controls not hijacked by game steering.
- Rapid Right→Up→Left executes in order over successive ticks.
- Right→Up→Down is not accepted as an impossible reverse; no queued command reverses into the snake's neck.
- Bounded queue, deterministic discard policy, repeat events, pointercancel/lostpointercapture behavior, orientation changes, repeated play/retry/pause sequences.
- Physical Android back button and Nuxel Back retain working application behavior.

### Speed/timing tests

- Speed changes while playing and takes effect on the next scheduled update (not just the next round).
- All supported presets yield correct tick periods, bounded FPS-independent simulation, and no unexpected score/position reset.
- Paused game remains motionless; background/lock stops work; resume doesn't teleport.
- Changing speed repeatedly does not spawn multiple `requestAnimationFrame` loops.
- Corrupt/old settings migrate safely, best score unchanged, new settings survive relaunch.
- Browser/PWA version changes and Android WebView package rebuilds use fresh assets—not stale cached JS.

### Game rule integrity

- Keep original Python parity tests for unchanged behavior; add explicit wrap-enabled expected fixtures and document intentional divergence from the original wall-death rule.
- Maintain offline build/check scripts, JS syntax linting, JavaScript unit tests and any existing Python suites. Report real counts and failures; do not hide missing dependencies.

---

## PHASE 6 — TEST ACTUAL TOUCH RESPONSE & PERFORMANCE

On actual hardware where available:

**Android device:** update the already-installed APK using the same application ID and appropriate signing identity, or document why a migration/reinstall is unavoidable. Do not silently uninstall and lose user scores/preferences.

**Nuxel S10+:** update only the SnekByte PWA files and app metadata using the existing safe userspace deployment route. No partitions/kernel/bootloader changes.

Run these physical acceptance cases:

1. Cold-open SnekByte offline. Press Play; game loads promptly with no loading spinner hanging.
2. Touch an arrow and **observe an immediate input acknowledgement**, with grid movement by the next valid tick.
3. Make three quick, legal turns and verify none are randomly dropped.
4. Swipe without lifting your finger; observe recognition during movement.
5. Repeatedly cross **all four edges**; never die from the border itself.
6. Eat 5 food items in WoNQ Mode; Poop-o-meter fills and drops a real hazard; collision with it still kills.
7. While playing, switch slow → fast → normal; movement changes promptly without reset or teleport.
8. Pause/resume, background/foreground, Android back/Nuxel back, rotate if supported; no phantom inputs.
9. Relaunch the game and check speed, wrap selection (if toggle exists), WoNQ and best-score persistence.
10. Lock display / leave game and check no sustained CPU activity or runaway rAF loop.

Measure at least: event recognition time (software timestamps), accepted-command-to-simulation-step interval, per-frame work cost in instrumented builds, long tasks/frame drops if tooling exists, CPU and memory during 5 minutes play, and qualitative physical touchscreen response. Compare against baseline. **Do not describe input-to-photon as measured unless it really is measured on-device.**

If the Nuxel phone's system-wide display bridge still dominates latency, report `GAME INPUT FIXED / SYSTEM DISPLAY LATENCY REMAINS` honestly rather than introducing false-pass results.

---

## PHASE 7 — BUILD AND DELIVER BOTH PLATFORMS

### Android APK

- Locate the existing A57 Capacitor/Gradle (or actual current native wrapper) project and keep its selected technology.
- Bundle the latest verified PWA source into the Android project's assets through a **reproducible build step**; preserve the correct application ID, signing identity, offline capabilities, existing icon and state.
- Build a real **debug-signed installable APK**; if the user already has an owner-signed release app, do not replace its signing identity or expose keystore secrets.
- Verify APK structure, package ID, launch activity, bundled game assets, install/update behavior and SHA-256.
- Never claim an APK exists until the actual artifact is present and verified.
- If no Android SDK or matching signing key is available, deliver verified source/build scripts and report the exact blocker; don't fabricate a package.

### Nuxel PWA

- Preserve canonical Nuxel app ID `org.nuxel.SnekByte` if still in use, the existing launcher icon and integration.
- Bump PWA asset/service worker cache version (when applicable) **without breaking offline launch**. Ensure Android and Nuxel use the same tested engine revision.
- Do not overwrite newer Nuxel UI/navigation/dock changes. Provide a minimal deployable patch and rollback backup; verify that opening SnekByte from the launcher works.

### Deliverables

1. Modified, complete SnekByte source project with **clean Git diff**.
2. `dist/android/snekbyte-snakepwn-7000-debug.apk` (if built) and SHA-256.
3. Updated Nuxel PWA drop-in folder / ZIP, plus staging/deploy instructions.
4. `docs/a58-snakepwn-7000/CHANGELOG.md` — exact game changes, speed defaults, wrap rule.
5. `docs/a58-snakepwn-7000/INPUT-LATENCY-ROOT-CAUSE.md` — measured/observed reasons for slowness and actual fixes.
6. `docs/a58-snakepwn-7000/TEST-RESULTS.md` — pass/fail with counts and device-tested vs offline-only distinctions.
7. `docs/a58-snakepwn-7000/ROLLBACK.md` — how to restore current working Android and Nuxel variants without losing scores.

---

## PHASE 8 — MANDATORY PASS/FAIL TABLE

| Acceptance gate | Required evidence |
|---|---|
| Game launches on Android | Installed launch test or clearly marked unverified |
| Game launches on Nuxel | Real S10+ launch or clearly marked unverified |
| Four-edge wrap | Deterministic tests + physical observation |
| No phantom wall deaths | Explicit collision tests |
| Self/poop collisions intact | Deterministic engine tests |
| Adjustable speed | During-play test, persisted value, actual tick rate |
| D-pad latency corrected | Press-time event trace, physical feel check |
| Swipe latency corrected | Move-time event trace; no release dependency |
| Rapid turns handled safely | Queue/reversal tests |
| WoNQ 5-food meter | Repeat-cycle tests |
| Offline play | Launch with connectivity disabled |
| Scores/settings persist | Relaunch and update tests |
| No background drain | Verify loop stops and CPU quiet when hidden |
| Existing working game intact | Android/PWA regression tests and rollback |

### STOP CONDITIONS

- Never destroy the working installation or erase high scores as an undocumented side effect.
- Never relax collision safety or allow physically impossible 180° instant reversals to make steering "fast".
- Never speed up the game just to hide touch latency; fix event dispatch and queueing first.
- Never modify other Nuxel services, kernel, firmware, partitions or boot splash.
- Do not claim 60 FPS or sub-20ms touch latency without actual measurements.
- If the current source differs from A56, adapt the plan to reality and document differences.

## FINAL ORDER

**Diagnose input → repair immediate events + bounded turn queue → implement infinite edge wrap → make speed control live and persistent → optimize render loop → test physics and WoNQ → build Android update + Nuxel drop-in → verify on actual devices.**

The owner's experience must be:

**Launch SnekByte → select speed → tap/swipe and turn instantly-feeling → disappear off one edge and emerge from the opposite edge → eat five snacks → 💩 POO DROP! → keep going forever until self/poop collision.**

**GO MAKE THE SNEK BUTTERY SMOOTH. 🐍💩⚡🔥**
