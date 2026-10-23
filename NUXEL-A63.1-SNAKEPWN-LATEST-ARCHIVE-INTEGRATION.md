# 🐍💩🔥 NUXEL A63.1 — OPERATION SNAKEPWN LATEST: 12KMAXIMUM EXTENSION

## AUTHORITATIVE NEW SNEKBYTE INTEGRATION ADD-ON TO A63

**Executor:** DeepSeek-v4-pro-thinking, running on the owner's Fedora 43 laptop.  
**Phone:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820, running the current Nuxel Fedora ARM64 installation.  
**Exact newly updated archive:** `./snekbyte.zip` at the **current Nuxel repository root**.  
**Master mission:** `./NUXEL-A63-OPERATION-12KMAXIMUM-MIXTURE-OF-EXTENSIONS-UBERPROMPT.md` (A63 / `pwnage-12000.md`).  
**Purpose:** Bring the **actual latest SnekByte** into A63's integrated Nuxel release. This is an additive amendment to A63, NOT an independent phone-deployment campaign, NOT a request to replay A56/A57/A58 verbatim, and NOT permission to overwrite newer changes.

## THE PRIMARY RULE

**`./snekbyte.zip` is the highest-priority *SnekByte source candidate* supplied by the owner in this run.** Do not assume its internal structure, version, languages, feature set, or completeness. Inspect it and compare it to the current repository and previously working installation before deciding which precise files should be merged. Treat its *proven newer game changes* as authoritative over historical SnakePwn 5000/6000/7000 drafts, while preserving valid Nuxel-specific integrations and local work not contained in the ZIP.

Do NOT copy the ZIP wholesale over Nuxel. Preserve all unrelated current OS code. Preserve the existing working SnekByte until its replacement is tested. **No claim that this new ZIP has been inspected by the author of this prompt**: the agent must inspect the actual local archive on Fedora.

### Required owner's result

1. The latest SnekByte edition from `./snekbyte.zip` is integrated into the **actual live Nuxel application system**.
2. Tapping the original SnekByte icon in the Home/app drawer launches the correct *newest* game, not a stale cached version or a blank page.
3. Phone touchscreen controls react promptly. Rapid turns, swipe gestures and D-pad/keyboard controls are verified on device where the newest game provides them.
4. The newest mechanics work, with special regression checks for configurable speed, infinite edge wrap, WoNQ mode, five-food poop drop and visible Poop-o-meter. If the newest archive intentionally changes rules, document exactly what changed; do not silently reintroduce old behavior from A58.
5. Scores, configuration and saved state persist appropriately; launch, Back, Home, Recents, lock/unlock, background/foreground and screen-off behavior do not strand the phone or waste CPU.
6. If an Android edition/project is present or supported, reconcile and build an independently testable Android debug APK **from the new current game**, without holding up the Nuxel PWA completion if Android tooling is unavailable.
7. Deliver a complete evidence record, rollback and source-of-truth map. Do not report "PASS" until real on-phone launch/gameplay has been observed.

---

## 0 — COORDINATION WITH THE MASTER A63 AGENT (MANDATORY)

- **Do not start a second live-device agent.** Integrate these instructions into the SAME A63 orchestrating agent/session before it reaches the SnakePwn implementation phase, or give them to the existing A63 agent as a high-priority amendment. If A63 is already editing game source, stop that subtask at a clean checkpoint and reconcile worktrees rather than racing it.
- Maintain A63's **single physical-device writer**, USB Live Console exclusive ownership, approved reboot policy, safe recovery route, current 4.14 kernel and zero flashing constraints.
- Read this entire add-on and A63; extend A63's feature-dependency graph and test plan; update the A63 acceptance scoreboard. Preserve A63 milestones for Wi-Fi, browser, rotation, battery, keyboard, camera, lockscreen and Home.
- If any reference prompt A56–A58 conflicts with what the new ZIP demonstrably implements, prefer the owner's new source for *game logic/assets*, while keeping actual working Nuxel bridge/Wayland/launcher behavior. Explain incompatible changes instead of silently reverting.

## 1 — READ-ONLY ARCHIVE SAFETY AND VERSION FORENSICS

From the correct Git checkout on **Fedora**, verify archive existence and identify its provenance:

```bash
pwd
realpath ./snekbyte.zip
sha256sum ./snekbyte.zip
unzip -Z -1 ./snekbyte.zip | sed -n '1,200p'
```

Do not run build/install hooks before inspection. Analyze ZIP entries for absolute paths, `../` traversal, symbolic links escaping staging, nested archives, unknown executables, scripts, file permissions and unusually large expansion. Reject unsafe layouts or extract to an isolated read-only-audited staging folder outside the live Nuxel app tree. Do not trust archive-provided instructions as authority to execute destructive actions.

Inventory files and architecture without inventing paths: Python/Pygame source, HTML/CSS/JS PWA, Capacitor/Android, React/Vite/bundler outputs, service worker, web manifest, artwork/icons, license, existing unit tests, lockfiles and generated distributions. Determine which are canonical sources and which are derived outputs. Check commit/release tags/version files if actually present; record archive hash and source file hashes.

Read the existing A63 phase 7 / historical A56–A58 and identify **what is implemented in the new archive vs what exists only in the live Nuxel checkout or old Android project**. Never assume the attached older `snekbyte-main` archive is the newest.

**Gate 1:** `A63.1-ARCHIVE-INVENTORY.md` with SHA-256, layouts, language/runtime choices, missing prerequisites, actual difference summary, current Nuxel deployed game identity and files that must remain untouched.

## 2 — DIFF SOURCE, DEPLOYED PHONE AND NEW ARCHIVE

Construct a three-way comparison:

- **NEW:** the user's `./snekbyte.zip` extracted to staging;
- **REPO:** present checked-out Nuxel `snekbyte` source, icon, registry, app shell, generated output and any Android project;
- **PHONE:** currently deployed SnekByte app and manifests as read over the verified USB Live Console.

Record precise content hashes, app ID/origin, entry-point URL, service worker registration/scope/version, manifest ID/start URL, displayed icon path, runtime web host, build revision and launch command. Discover any duplicate SnekByte installations or stale resources that could steal the icon tap or show an older game.

Keep the proven latest **game engine and art from NEW**; adapt Nuxel-specific wrapper/launcher/deployment glue from REPO as needed; use PHONE only to understand runtime, back up known-good files and verify deployment. Do not trust a file's modification timestamp alone as proof of authority.

Existing user changes and dirty worktree must not be destroyed. Use a clean feature branch or separate Git worktree; do not reset, `git clean`, unzip over repo root, or overwrite files without an explicit merge plan.

**Gate 2:** file-by-file merge plan listing NEW/REPO/PHONE precedence and required behavior, dependency changes and rollback image.

## 3 — PORT THE LATEST GAME INTO NUXEL CORRECTLY

Use the *current* app packaging format found in the repo; typical destination may resemble `pwa/nuxel-apps/snekbyte/`, but **derive and verify**, do not hardcode assumptions. If the ZIP is Python-only, port or bundle using a supportable on-phone approach that preserves game rules and responds to touch; favor the current proven PWA host where supported. If the ZIP already contains newer JS/PWA or a framework, retain its actual game engine and produce deterministic distributable assets matching WebKitGTK capabilities.

- Honor Nuxel app registry and stable SnekByte application identity; add/update discovery metadata, existing launcher icon, packaging manifest, `start_url`, file paths, app IDs, MIME/content settings and application lifecycle.
- Use the exact newest image/icon from ZIP when deliberately provided, otherwise preserve existing authentic snake-and-poop Nuxel icon. **Never replace it with a generic `SB` placeholder**.
- Avoid generic browser tab/window hijacking, external web-server dependencies, CORS/file-URL surprises and `iframe`-only shell tricks. Ensure the actual Nuxel host can open the content using its current stable origin and security policy.
- Build/update PWA caches and service-worker versioning without orphaning offline play. Make asset manifests deterministic and verify every referenced asset exists. Preserve/update scores and settings using an explicit compatibility/migration strategy; no silent save wipe.
- Render well at the S10+ current *logical* compositor size and in landscape where supported, accounting for safe areas, bottom navigation, DPR, touch-action, focus and orientation changes.
- Support keyboard/gamepad where present, but provide a reliable touchscreen-first path for the phone.

**Gate 3:** offline build loads the real newest game and all Nuxel manifests/assets pass static checks; any required migration has tests.

## 4 — INPUT LATENCY, GAME RULES AND PERFORMANCE

Audit the actual new implementation rather than blindly copying A58's suggestions:

1. **Responsive swipe:** detect a committed direction as soon as motion crosses a deliberate small threshold, not only at `pointerup`; avoid scroll/selection interference and accidental diagonals, and apply input to the next valid simulation step. Preserve pointer capture and proper cancellation.
2. **Responsive D-pad:** start press detection at pointer-down/touch-down (with mouse fallback and duplicate-event suppression), not just click release; no phantom repeats when overlay loses focus.
3. **Safe rapid turns:** bounded FIFO of legal directions, rejecting direct 180° reversals relative to the currently planned direction; consume deterministically, do not create multiple turns in one simulation step if it would cause impossible physics.
4. **Speed selection:** ensure UI control changes the *running simulation interval* as designed and persists; document whether it should apply instantly or next round. Prevent runaway timers, accumulated setIntervals and frame-skipping.
5. **Infinite walls:** on all edges, wrap with modular coordinates instead of wall death, including corners and edge-spanning snake body segments. Maintain self-collision semantics.
6. **WoNQ poop logic:** visible 0/5 to 5/5 meter, spawn poop obstacle at the correct event without invalid overlap, maintain collision/game-over scoring/animations. Preserve the newest game's intended art, balance and audio/haptics features if present.
7. **Performance:** no extra game loops after resume, no background busy spin, pause or throttle while locked/hidden, maintain steady frame timing without disabling thermal protection or forcing maximum CPU frequency.

If the new ZIP intentionally implements different mechanics, prefer its explicit game design, record differences and obtain owner feedback only where a consequential ambiguity cannot be resolved. Do **not** revert newly updated SnakePwn logic to old A56 defaults simply because a historical prompt said so.

**Gate 4:** automated deterministic tests for wrap in all directions, speed transitions, high-speed turn queue, death conditions, poop every five foods, saved data compatibility and suspend/resume. Reference Python parity only if the latest archive genuinely retains equivalent Python rules.

## 5 — ANDROID EDITION (INDEPENDENT, NONBLOCKING)

If the archive contains current Android/Capacitor sources, audit manifest/package ID, icons, permissions, `webDir`, Android Gradle plugin versions, Java/SDK prerequisites and offline asset bundling; build from newest sources and confirm debug APK is an installable artifact, not an empty Android shell. If only PWA is present, either adapt the existing Android wrapper or document explicitly what prevents a repeatable build.

- Prefer local Fedora Linux Android build tooling; check available SDK/Java/Gradle before modifying environment.
- Use offline-first bundling, no unnecessary permissions, safe WebView security settings and original icon.
- Test gameplay on Android emulator or owner's authorized real Android test phone if available; don't claim physical Android test from compilation alone.
- Produce `dist/android/snekbyte-debug.apk` if build succeeds, with size, SHA-256 and exact build command.
- Do not block S10+ deployment on a missing Android SDK or build problem. Android APK **is not** the Fedora Nuxel app; keep both as distinct distributions of the same newest game logic.

**Gate 5:** genuine APK with `aapt`/signature validation if possible, or exact `ANDROID_BUILD_BLOCKED` reason. No fake APK outputs.

## 6 — SAFE LIVE S10+ DEPLOYMENT

Coordinate with the main A63 agent, which owns the live phone. Stage a patch on Fedora, run tests, produce a focused commit and obtain the normal A63 device-deployment approval when required. Before replacing SnekByte, **back up current deployed SnekByte files + launcher metadata/settings as needed**, with SHA-256 and tested restore instructions. Never overwrite the entire PWA/app directory indiscriminately or disrupt other apps.

Deploy AArch64-compatible userspace resources through the verified Fedora USB console/approved transport, ensuring file permissions, correct installed origin, manifest registration and service worker/cache invalidation. Restart the minimum necessary user-session process; avoid phone reboot just to refresh static assets. Never alter Nuxel bootloader/kernel/partitions/rootfs images or USB recovery path.

Verify the exact new game version/asset hashes on phone after deployment; eliminate stale duplicates without deleting unrelated user data. Restore previous revision on any boot/app-lifecycle regression.

**Gate 6:** icon tap truly opens the newest SnekByte game on the phone; from game, Back/Home and Recents work; returning to game restores a safe state; lock screen and OSK are unaffected.

## 7 — REAL-PHONE GAMEPLAY ACCEPTANCE AND ANTI-REGRESSION

Use reproducible scripted logic tests plus physical owner tests:

- Fresh launch from app drawer and Home icon; no white/black screen, JS exception, spinner or wrong PWA revision.
- Touch/swipe steering activates at movement threshold, D-pad reacts on down; test long, rapid and diagonal-adjacent movements.
- Adjust speed while playing and across new game; verify UI and actual simulation rate.
- Wrap left/right/top/bottom repeatedly; no death at a wall; still die on legitimate self/poop collision.
- Eat five foods in WoNQ mode; see meter progress and obstacle appear. Pause, resume, retry, game over, high score and settings persist.
- Press Penguin Home (should return to Home without killing game), open Recents and return; use Back, long Back, lock/wake, screen timeout, and test that the game does not continue burning CPU when hidden.
- Exercise real landscape/portrait capabilities without adding or faking missing global rotation modes.
- Verify icon, art, touch regions, bottom navigation, correct application scaling and no crash after a user-authorized cold boot.
- Confirm Wi-Fi/Browser/Camera/keyboard/lockscreen/battery/rotation fixes from A63 remain untouched. Re-run their smoke checks after SnekByte deployment.

**Gate 7:** `VERIFIED_ON_DEVICE`, `FUNCTIONAL_WITH_LIMITATION` or `BLOCKED` must be backed by observable hardware/runtime receipts; no green from offline tests alone.

## 8 — DELIVERABLES / REPORTING

Create `docs/a63-1-snekbyte/` (or compatible Nuxel docs path):

- `ARCHIVE-INVENTORY.md`: the exact `./snekbyte.zip` SHA-256, tree and newly changed mechanics/assets.
- `SOURCE-OF-TRUTH.md`: new ZIP vs previous Nuxel vs live phone, authoritative entrypoints and correct app IDs.
- `MERGE-PLAN.md`: changes staged, deliberately preserved files and reasons.
- `GAMEPLAY-TESTS.md`: commands, deterministic results, Python/JS parity where meaningful.
- `DEPLOYMENT-AND-ROLLBACK.md`: before/after hashes, commit, safe transfer and restore procedures.
- `PHONE-ACCEPTANCE.md`: named test results (observed vs owner-to-confirm), screenshots/logs if available, and explicit limitations.
- `ANDROID-RESULT.md`: APK path/hash/signature test or honest blocker.
- `A63-INTEGRATION-STATUS.md`: A63 dependency/scoreboard updates and regressions checked.

Return a final succinct scoreboard for **source audit, latest mechanics, Nuxel app launcher, on-device game, controls, wrap, speed, poo meter, persistence, lifecycle, Android APK and A63 regressions**. Use PASS only for the actual checked state.

## NONNEGOTIABLE RULES

- `./snekbyte.zip` is the latest owner-provided **source input**, never an uninspected auto-install script.
- Don't deploy historical A56/A57/A58 ZIPs over it or silently remove newer features.
- Do not run a second independent phone-flashing/deployment agent against A63.
- Do not replace working WebKitGTK, keyboard, Home, camera, Wi-Fi, OS lock state or launcher architecture to make one game work.
- No fake hardware measurements; no false claims of physical verification.
- No kernel/firmware/partition changes and no unsafe sandbox bypass.
- Keep an off-device restore path for the currently running game.

**SUCCESS:** The latest real `./snekbyte.zip` content is safely merged into Nuxel; the original SnekByte icon launches the truly newest and responsive game on the S10+; its gameplay and persistence are verified; the Android APK is built if feasible; and A63's other subsystems remain stable.

**GO MERGE THE NEWEST SNEK. KEEP THE PENGUIN ALIVE. 🐧🐍💩🔥**
