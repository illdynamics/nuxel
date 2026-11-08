# 🐍💩🔥 OPERATION SNAKEPWN 6000 — SnekByte Android APK

**Executor:** DeepSeek-v4-pro-thinking (preferred); GPT-5.6 Sol High if cross-platform/Gradle blockers need escalation.

**Goal:** Deliver an **actual buildable, signed-for-testing, installable Android `.apk`** of the owner's existing **SnekByte / SnakePwn 5000** game, not an APK-shaped archive, not an installable-PWA shortcut, and not a remote-site WebView. Keep the Fedora/Nuxel PWA working and preserve the original Python project.

**Inputs in the Nuxel or SnekByte repository root:**
- Preferred: `snekbyte-main-SNAKEPWN-5000-dropin.zip` from A56, or its already extracted folder.
- Optional reference: original `snekbyte-main (2).zip`.
- Existing/current SnekByte sources in the repository. If there are more recent user changes, compare and merge; **do not overwrite newer working gameplay**.

**Exact known A56 web app path inside the patched archive:**
` snekbyte-main/nuxel-dropin/pwa/nuxel-apps/snekbyte/ `

Core files: `index.html`, `css/snekbyte.css`, `js/snek-engine.js`, `js/snekbyte.js`, `manifest.json`, `sw.js`, `icons/icon-{48,72,96,128,144,152,192,384,512}.png` and `icons/icon.svg`.

**Existing canonical app ID for Nuxel:** `org.nuxel.SnekByte` (not necessarily a valid Android package ID; keep the Nuxel ID intact in the Nuxel PWA).

**Proposed Android application ID:** `com.illdynamics.snekbyte` (check against any existing installed package or prior signing identity; select exactly one stable valid ID and document it). **Display name:** `SnekByte`.

**End state:** `dist/android/snekbyte-debug.apk` (+ optional owner-signed `dist/android/snekbyte-release.apk`), Android project source, reproducible build script, checksums, install instructions, real-device or emulator evidence, and unchanged Nuxel PWA/Python source behavior.

---

## 0. ACCURATE TECHNICAL APPROACH — REUSE THE EXISTING PWA

The original SnekByte is Python/Pygame. A56 already contains a JavaScript port of its gameplay, previously checked against the Python reference over recorded game ticks. It is a mobile-oriented, dependency-light PWA with swipe/D-pad controls, a five-food Poop-o-meter, persistent poop hazards, scoring, levels, menus and local preferences.

**Do not attempt to package the Python project with Kivy, Chaquopy, or a heavyweight Python runtime as the primary approach.** That adds unnecessary complexity and risks behavior divergence. Instead:

1. Wrap the **existing offline HTML/CSS/JS** with a native Android shell.
2. Prefer a **version-pinned Capacitor Android** wrapper, because it supports bundling web assets into the APK, native app lifecycle and Gradle builds. Check the locally installed Node/Java/Android SDK compatibility with the current Capacitor documentation before choosing/pinning versions; don't blindly use global latest and incompatible Gradle plugins.
3. Use Android Studio / Android SDK / Gradle. Do not require a custom server, internet connection, external browser, PWA installation, or an Nuxel service to play.
4. If Capacitor introduces an unsolvable incompatibility, a small secure Kotlin Android WebView wrapper loading **bundled local assets via WebViewAssetLoader** is a documented fallback, with explicit reasoning and the same functional/security tests. Do not implement both by default.
5. Maintain one source of truth for the game rules. Keep the Android wrapper in a separate `android-app/` (or similarly clear) directory and copy the PWA via a deterministic staging script. Avoid a diverging Android-specific copy of the game engine.

**Prove offline operation with airplane mode on the first installation launch**, not merely a warm cached relaunch.

## 1. FORENSIC SOURCE INVENTORY & CLEAN BASELINE

- Find the actual current SnekByte project. Inspect current Git status, branches, newer work and any Android projects already present.
- Unpack the A56 drop-in **in scratch space**, never blindly over the current repository.
- Confirm the exact entry HTML, relative asset paths, `SnekEngine` script load order, localStorage keys, canvas behavior, service-worker registration, and PWA manifest.
- Validate the correct SnekByte art. It is the **pixel-art green snake plus poop pile**: `nuxel-dropin/assets/nuxel-applications-icon-pack/01-02_snekbyte.png` and the PWA `icons/icon-512.png`. Do not revert to a generic `SB`, Android robot, or random icon.
- Inspect original Python source (`src/game_logic.py`, `src/poop.py`, etc.) and the A56 test fixtures. Record and preserve WoNQ semantics: **poop after every fifth actual food**, obstacle collision, score, speed and direction constraints.
- Keep the Nuxel PWA metadata (`app.json`, `org.nuxel.SnekByte`) and installer as they are, unless a clearly isolated bug fix is justified.
- Back up existing Android project/signing configuration before changes. Don't commit or publish private signing keys.

Write `docs/a57-android/BASELINE.md` with exact source archive/hash, current branch/commit, existing Android project discovery, game engine version and known incompatibilities.

## 2. ANDROID TOOLCHAIN & PINNED DEPENDENCIES

On the **development host** (Fedora laptop or MacBook), check:

```bash
node --version
npm --version
java -version
command -v adb || true
command -v sdkmanager || true
printf 'ANDROID_HOME=%s\nANDROID_SDK_ROOT=%s\n' "$ANDROID_HOME" "$ANDROID_SDK_ROOT"
```

Read the official documentation and determine mutually compatible versions of Node, Capacitor, Android Gradle Plugin, Gradle, Kotlin (if applicable), Java JDK, Android SDK/Build Tools, and target/min/compile SDKs.

- Current Capacitor 8 documentation requires Node >=22 and a recent Android Studio/SDK. Do not hardcode stale versions or force Capacitor 8 if the available environment cannot safely support it; use a supported, **explicitly pinned** release instead.
- Pin `@capacitor/core`, `@capacitor/cli`, and `@capacitor/android` to compatible matching versions; commit `package-lock.json`; use `npm ci` in reproducible builds.
- Pin Gradle wrapper and Android dependencies. Verify any wrapper distributions/hashes through trusted official sources when practical.
- Never put SDK directories, caches, APK signing secrets, local.properties with machine-specific paths, or node_modules in Git.
- Do not download random unsigned build scripts or dependency archives from third-party mirrors.
- Use a dedicated new Android wrapper folder; do **not** change Nuxel system-wide tooling.

If Android SDK packages must be installed, make the changes on the owner's developer laptop, **not on the Nuxel S10+ Fedora operating system**.

## 3. BUILD AN ACTUAL STANDALONE APK

Create:

```
android-app/
  package.json
  package-lock.json
  capacitor.config.ts   # or JSON/JS with documented configuration
  www/                  # generated staged local SnekByte web assets
  android/              # actual Android Studio/Gradle application project
  scripts/
    stage-web-assets.*
    build-debug.*
    verify-apk.*
  README-ANDROID.md
```

Use existing HTML as the root `www/index.html` and preserve relative directories (`css`, `js`, `icons`) so `src="js/snek-engine.js"` etc. continue to resolve. **Never assume** the Nuxel absolute `/pwa/nuxel-apps/snekbyte/` paths work inside an Android package; rewrite Android *packaging metadata only* or adjust with an explicit build-only transformation if required, while keeping the Nuxel PWA unchanged.

Capacitor path:

```bash
npm ci
npx cap sync android
cd android
./gradlew --no-daemon :app:assembleDebug
```

Commands are illustrative: first create/initialize the platform through its supported CLI, choose compatible versions, and capture actual build logs. The APK must contain game HTML/CSS/JS and image assets, not fetch them at runtime.

Copy the successful debug APK from its actual Gradle build output to:

`dist/android/snekbyte-debug.apk`

Include a SHA-256 manifest and `apksigner verify` / `aapt dump badging` or equivalent tool inspection to prove the APK is valid, signed, has the intended Android package identifier and app label, and contains required assets. Do **not** invent an APK filename or success status; confirm the output exists and is nonempty.

A debug APK is allowed for immediate sideload testing. A release APK requires a separately protected owner-managed release signing key; no password/key should be embedded in source, CI logs, prompt output or Git. If no signing key exists, **produce the debug APK now** and document how to create a signed release later. Do not silently create a release identity that the owner cannot recover for updates.

## 4. ANDROID APP EXPERIENCE

Implement and physically test:

- **Proper native launcher application** with correct title and adaptive launcher icons derived from the actual SnekByte snake/poop artwork; include suitable foreground/background resources and avoid cropped snake/poop at launcher adaptive-mask edges.
- Startup splash consistent with SnekByte visual style, short and nonblocking; no mandatory internet or permission dialogues.
- Full-screen or edge-to-edge play with correctly handled status/nav bars, display cutouts, gesture navigation, safe-area padding and Android WebView viewport sizes. Do not let the D-pad, settings buttons, or Poop-o-meter slide beneath navigation controls.
- Portrait gameplay layout on a typical Android phone; **landscape** gracefully supported too, without distorted canvas, stretched controls or nonfunctional hit areas. Do not unnecessarily force system-wide device rotation.
- Finger swipes + tap D-pad remain responsive. Prevent unwanted page scroll, pinch zoom, long-press selection or double-tap zoom over play controls without disabling accessibility across the whole UI.
- Hardware keyboard arrows/WASD if available; Back button invokes game-appropriate pause/menu/dismiss behavior rather than unexpected app termination or broken navigation. Implement a reasonable double-back/exit policy if necessary, with no intrusive prompts every time.
- Game stops simulation/audio (if any) on background, incoming call, app switch, screen off or activity pause. Resume to paused/game menu and never burn CPU/GPU in background.
- Preferences and best score stay on the device, persist across activity recreation, app relaunch, orientation changes, phone reboot and reinstall-independent **update** of the same signed package. Clarify that uninstall may delete local data; do not promise survival of uninstall without an implemented backup mechanism.
- True offline play. No startup fetches or external analytics. No camera, microphone, location, contacts, storage-root or phone permissions.
- If the app already uses service worker `sw.js`, check that it behaves safely within the embedded Android origin; **offline bundled assets must work even if service workers are unavailable/disabled**. Do not rely on the Nuxel static server or other installed PWAs.
- Enforce safe WebView/Capacitor content access: no arbitrary remote JS injection, no insecure exported debug WebView, no unrestricted JavaScript-to-native privileged bridge, no enabling universal file access. Keep sensitive build debug flags out of release builds.

Use a local app origin supported by the selected wrapper. Don't turn on cleartext HTTP or request network permissions just to load a local game unless the particular runtime demonstrably requires and justifies a narrow exception.

## 5. GAMEPLAY AND POO-METER ACCEPTANCE

Keep the canonical game engine behavior intact. Validate:

1. Main menu loads immediately, tap `PLAY` starts the snake.
2. Swipe steer and D-pad movement match directions; reverse direction is rejected according to canonical engine rules.
3. Food increments score, grows snake, and advances the **real** `POOP-O-METER`.
4. Meter reads `0/5`, `1/5`, `2/5`, `3/5`, `4/5`. On **fifth food**: a real poop obstacle spawns, meter resets, brief visual celebration, and subsequent collision can end game.
5. Distinguish wall, self and poop collision game overs.
6. WoNQ mode enabled by default in the A56 UI, can be toggled and persists; canonical Python-engine defaults and parity logic are not silently rewritten.
7. Pause, resume, retry, score, best score, speed and grid settings work and persist.
8. One full run works with Android device completely offline.
9. Touch targets remain usable on small screens and with system font-size/display scaling adjustments.
10. No visible WebView chrome/address bar, debug UI or accidental duplicate launcher buttons.

Run and keep the existing tests:

```bash
node nuxel-dropin/pwa/nuxel-apps/snekbyte/tests/test-snek-engine.js
python scripts/check-snekbyte-bundle.py
node --check nuxel-dropin/pwa/nuxel-apps/snekbyte/js/snekbyte.js
```

Adapt paths only based on actual extraction/checkout. The original archived A56 test suite recorded **48 passing checks including 41 reference parity ticks**, but **re-run them after any changes**; never claim those historical results validate the new APK.

Add Android-specific smoke tests for packaging, lifecycle, orientation, local storage persistence, offline initial launch, icons, and keyboard/Back behavior. Preserve Nuxel game-engine parity.

## 6. REAL ANDROID INSTALLATION — NO FAKE PASS

Use an owner-approved Android emulator or physical **Android** phone (not the Nuxel/Fedora S10+), with USB debugging as needed:

```bash
adb devices -l
adb install -r dist/android/snekbyte-debug.apk
```

- Confirm the device is actually running Android and supports the app's minSDK and System WebView; do not attempt `adb install` into the independent Fedora Nuxel installation.
- Launch using the verified application ID, inspect `adb logcat` for JavaScript, WebView, Capacitor, crash and lifecycle exceptions.
- Turn **airplane mode ON before the first launch** following clean installation. Prove all game assets, graphics, settings and menus load without internet.
- Perform real touch/swipe gameplay. Eat five foods and photograph or capture the meter plus poop hazard if possible.
- Home → resume; lock/wake; rotate; background for a minute; force-stop/relaunch; phone reboot (only if device owner approves); verify local preferences/high score persist and no unusual battery or process wake behavior.
- If a real Android phone is unavailable, use an emulator and **explicitly label hardware acceptance as unverified**. Never present simulator success as physical-phone success.
- Use `adb shell dumpsys package <appId>` and artifact inspection to confirm installation and permissions. Validate debug APK install/update on the intended Android-version range.

## 7. BUILD SCRIPTS, CI, AND DELIVERY

Deliver these artifacts inside the owner's workspace:

1. **`dist/android/snekbyte-debug.apk`**: actual existing debug-signed APK, validated by Android build tools.
2. **`dist/android/snekbyte-debug.apk.sha256`** or a manifest file.
3. **`android-app/`**: complete Gradle/Capacitor source and pinned dependency files.
4. **`android-app/README-ANDROID.md`**: prerequisites, host setup (Fedora preferred; macOS supported), build commands, offline run, install/update/uninstall instructions, package ID and signing documentation.
5. **`android-app/scripts/build-debug.*`**: idempotent repeatable build, staging the current web assets and copying/validating the output.
6. **`docs/a57-android/`**: `SOURCE-AUDIT.md`, `GAME-PARITY.md`, `BUILD-RECEIPTS.md`, `APK-CONTENTS.md`, `ANDROID-TESTS.md`, `SECURITY.md`, `ROLLBACK.md`.
7. Optional signed release APK only if a private owner-controlled release keystore is available and deliberately configured. Optional GitHub CI artifact build with secrets kept safe; don't break existing Nuxel CI.

**Deliver the actual APK file to the owner**, not just source files, screenshots, a build plan, or an empty `dist` folder. If unable to build due to Android SDK/network restrictions, document the precise blocker and provide the full source, automated build, and honest `BLOCKED` result. Never fabricate an APK.

If the sources are in a separate SnekByte repo, keep Android packaging scoped there. Do not modify Nuxel's boot images, Fedora kernels, camera, modem, display drivers or system update pipeline.

## 8. ACCEPTANCE CHECKLIST

| Gate | Required evidence |
|---|---|
| Current Python and Nuxel versions preserved | Diff and game parity tests |
| Android project builds | Real `assembleDebug` success + pinned inputs |
| Valid signed `.apk` exists | File bytes, SHA-256, Android signature check |
| Launcher icon | Correct actual snake-with-poop artwork shown on Android |
| Offline first launch | Clean install with airplane mode ON |
| Touch controls | Physical/emulator swipe, buttons and back tests |
| WoNQ Poop-o-meter | Five meals trigger real obstacle, collision works |
| High scores/preferences persist | Relaunch, lifecycle and update tests |
| No Android privilege creep | Permissions reviewed and minimized |
| Nuxel app remains functional | Re-run Nuxel PWA tests and confirm no unwanted edits |
| Physical Android phone install | PASS only with actual-device evidence; otherwise UNVERIFIED |

Return **PASS / FAIL / BLOCKED / UNVERIFIED per gate**, plus all build artifacts and exact commands/logs.

---

## FINAL ORDER

**Make the real SnekByte SnakePwn 5000 PWA into a standalone Android game APK. Keep the poop. Keep the snake. Keep the icon. Keep the original Nuxel game intact. Build it, sign the debug APK, verify it, install it on Android, test it offline, and deliver the actual `.apk`.** 🐍💩🔥
