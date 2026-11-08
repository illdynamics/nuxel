# 🐧 NUXEL A64 — OPERATION PENGUIN LAUNCHER RESURRECTION
## GPT-5.6 Sol / High — emergency UI regression repair for Galaxy S10+ (SM-G975F)

> **MISSION:** The real Nuxel Home / launcher / UI layout is visibly broken after recent 12KMAXIMUM unified work. Restore its polished pixel-art, density-correct mobile launcher *without losing the functional work already completed on Wi-Fi, browsers, SnekByte, battery, apps, or other services*. This is an emergency, **UI-only recovery**, not authorization to repeat A63 or redesign Nuxel. Work until a **new physical S10+ screenshot and touch testing** prove recovery or identify an evidence-backed blocker.

## 0 — Look at the owner's proof FIRST

The reference photograph is bundled at `./evidence/launcher-regression-reference.jpg`. Examine it before any changes. It documents the **broken state**, not the desired design. The owner reported: "the whole UI/launcher is ruined now". From this single photograph, the visible facts are:

1. The home screen is dominated by **massively oversized square app artwork/icons** (Calendar, Camera/Nuxel logo region, Contacts, Files) rather than a compact multi-column mobile launcher/grid.
2. App entries form an enormous **single vertical list** with labels scattered below; much of the list doesn't fit on screen.
3. Raw-looking **GPU / VRAM / memory-performance telemetry** appears beneath or overlapping the status-bar region at the top, crowding out normal Home.
4. The bottom navigation/Home dock is disconnected from the layout, visually overlapping underlying content with a **large dark circular area**.
5. The original neon-blue/pixel-art visual language and real app images are partially present; this suggests a CSS/style/layout/runtime/asset-sizing failure rather than necessarily missing app data. **Do not assume the root cause without measuring it.**
6. The status bar appears to show time, a battery percentage and bell, but this photograph alone **does not establish** whether those readings are accurate, whether taps work, or whether this is a newly started shell versus an old cached bundle.

Do not treat this image as a working-state gold screenshot. Find the last known-good launcher screenshot, source/assets, repository commit, a backup or tagged release, and ask the owner only if absolutely necessary. Infer styling intent from canonical repo design assets and existing tests, NOT generic Android/GNOME defaults. A native screenshot captured from the live framebuffer/compositor, when feasible, is preferred to camera photographs for diagnosing CSS coordinates.

## 1 — EMERGENCY SCOPE FREEZE AND OPERATOR SAFETY

**STOP new 12K feature rollout and live deployment** while repairing the launcher. If A63 is running in another agent, coordinate a pause at a safe boundary, not a forced termination in the middle of file transfers. There must be **one owner** for deployment to the S10+.

- Existing device: independent Nuxel Fedora ARM64, Samsung Galaxy S10+ SM-G975F/beyond2lte/Exynos 9820, legacy downstream kernel 4.14.x, Phoc/Wayland + custom WebKitGTK/PWA shell, USB Live Console. Verify current live versions, paths and sessions rather than assuming those historical facts remain exact.
- Preserve working Linux boot path, display bring-up, compositor process, touch, USB Live Console, and last known working lock/unlock. First verify a live authenticated **wired recovery terminal** to the device and write recovery instructions. Do not break it.
- **NO boot image, rootfs, firmware, kernel, DTB, modem, display-driver, or partition flashing. NO factory reset. NO destructive Git clean/reset.**
- **NO mass revert of 12KMAXIMUM**, no removal of the latest SnekByte archive, no Wi-Fi credential edits, no changing NM or camera drivers, no unrelated Python dependency upgrades. Revert *only* a proven launcher regression, then carry forward necessary later working features.
- Before any changes: capture `git status`, worktree changes, branches, recent commits, original hash of each target file, installed bundle hashes, systemd user units, relevant logs, and **a tarball of the exact live launcher HTML/JS/CSS/assets/entry-point/service configurations** (preserve ownership/perms and symlinks appropriately). Store backups OUTSIDE the replaced path and record restore commands.
- Do not restart Phoc or the whole GUI session casually. Prefer hot reload of the relevant WebKit view/web server after staging files, or controlled restart only with recovery proven. Phone reboot requires explicit owner approval.
- Be careful about active sessions over the Fedora host. Do not assume the MacBook is still connected. Diagnose USB path independently of LAN Wi-Fi.
- Separate the operation into a diagnostic branch and a few isolated, reversible patches. Commit changes coherently; no `git reset --hard` on a dirty worktree or wiping user content.

## 2 — SOURCE-TO-RUNTIME RECONCILIATION: WHY DID THIS REGRESS?

Before designing a patch, identify EXACT live launcher architecture and trace:

`boot → systemd/session → Phoc/Wayland → WebKitGTK host → origin/base URL/file location → HTML entry point → linked CSS → JS boot → app registry/icons → status bar → Home layout → navigation dock → touch hitboxes`.

Inspect actual repository tree and deployment scripts for likely locations (names may vary): `pwa/`, `shell/`, `launcher/`, `frontend/`, `services/nuxel-bridge/`, `assets/`, `web/`, user service definitions, application manifests, CSS bundles, WebKitGTK WebView host. Find real paths via `rg --files`, CSS and JS imports, `git log`, `git diff`, `journalctl`, WebKit logs, GTK session environment, `find`, and deployed file hash comparisons.

**Investigate the regression window:** compare latest known-good live screenshot/commit/deployed hash with changes from A63.1/A63.2 and any concurrent fixes. Look for:

- Missing, stale, 404, blocked, or incorrectly MIME-served stylesheets; CSS imports mismatched with deployment base URL; references to an older build directory; stale cached HTML referencing renamed CSS/JS bundles; broken service worker cache, content hashing or asset URLs; a launcher accidentally falling back to unstyled legacy template.
- `meta name="viewport"`, WebKitGTK `WebKitWebView` zoom level, `deviceScaleFactor`, compositor output scale, `devicePixelRatio`, `window.innerWidth`, `document.documentElement.clientWidth`, `visualViewport.width/height/scale`, forced orientation/rotation, custom user-agent style overrides; viewport dimension units vs physical 1440×3040 display and historical 720×1520 logical rendering. Measure, do not hardcode 720 or 1440 as universally correct.
- CSS layout mode changed from `grid`/`flex` to block list because of selector collision, invalid CSS, new wildcard rules, higher-specificity global CSS, or different DOM structure; accidental `.app`/`.icon`/`img` global classes collision; `width:100%`, `height:auto`, viewport percentage-based sizing, huge `rem` root font-size, `transform:scale`, `zoom`, broken responsive media query thresholds, global image reset, icon `object-fit` regression, unbounded intrinsic asset dimensions.
- Dynamic injected `<style>` or JS inline style overrides after startup; duplicate component mounts, status widget moved into wrong parent, debug overlay toggled, multi-render shell due to DOM reconciling, debug runtime environment variables, stale CSS custom properties.
- A migrated app registry renderer or imported PWA card CSS reused for small Home icons; wrong app-icon dimensions, `srcset` density inference, fallback image component styles, incorrect DOM or flex basis.
- Bottom Home dock `position: fixed/absolute` with wrong containing block or `z-index`, root height/viewport resize mishandling, safe-area inset ignored, touch keyboard `vh` shrink, transform stacking context and overlays.
- Screen transform/scaling approach changed by orientation controller, framebuffer bridge or compositor; differentiate **everything huge at system scale** from **only launcher images huge**, and **CSS missing entirely** from a single bad selector.

Use structured observations, not guesswork. At minimum, collect source vs device sizes/hashes/versions and a DOM/computed-style report from the **actual live WebKit page**, if a WebKit debugging attachment can be enabled safely. If remote inspection can't run, instrument a short-lived diagnostic report into a file and remove it after diagnosis. Capture widths, computed `display/grid-template-columns`, icon bounding rects, parent widths, relevant stylesheets load status, debug overlay state, viewport, DPR, zoom, root font size, scrollbar count and first JS errors. Never leak private tokens/URLs/credentials in diagnostics.

## 3 — FIRST RESPONSE: RESTORE KNOWN-GOOD LAUNCHER, MINIMUM BLAST RADIUS

**Preferred recovery path:** recover the exact Home UI layout contract from a previous confirmed-working Nuxel version. Locate via tags, `git reflog`, deployment receipts/backup, previous PWA release, recorded screenshot or `git show`. Restore/forward-port ONLY the styling, Home DOM component and associated correct assets; preserve newer launcher registrations, app IDs, working activity dispatch, bridge ABI, network/browser integrations and status data feeds. Perform an explicit **three-way merge**, not a blind overwrite.

If good code is unavailable, fix measured root cause in place. Aim for focused patches: stylesheet path/cache/manifest, CSS selectors/sizing, viewport/scale, Home renderer, dock positioning. Never disguise the broken UI by hiding all cards or shrinking everything with a single top-level transform.

Stage first on Fedora and render at representative logical sizes. The desired visual behavior is grounded in the repo's established Nuxel aesthetic: compact pixel/neon-blue icons; polished Home wallpaper/background; legible label once per icon; consistent alignment and gutters; original launcher/app artwork remains recognizable; stable centered/appropriate bottom navigation; status bar is a separate compact layer; intentional scroll/pagination when too many apps are installed.

### Non-negotiable layout invariants

- Root page and WebKit window must have a valid measured logical viewport; no horizontal scroll caused by oversized cards/icons or accidental physical-pixel scaling.
- **App launcher uses a responsive compact grid** appropriate to screen width (e.g., 3–4 columns in portrait IF that matches existing design; determine actual historical grid). It must never fall back to a one-item-wide image wall at the target S10+ portrait viewport.
- All app icon boxes have a consistent constrained CSS width/height and `aspect-ratio: 1 / 1`; actual `<img>` is sized to its box with suitable `object-fit`, no stretching or cropping of essential logos; pixelated rendering as appropriate to native artwork. App labels are bounded, consistent, single/dual line per original design, don't collide with neighbors. Icons may be visual PNG/WebP/SVG assets but preserve native file sizes and transparency.
- The header has a reserved, safe-area aware statusbar height. Render only intentional clock, battery, Wi-Fi, notification icons, etc.; no raw CPU/GPU/VRAM text overflowing the top unless the historical design intentionally supports a separate diagnostics panel. Even if debugging widget remains supported, it must be behind an explicit developer toggle, in its own responsive panel, OFF by default, never leak into Home statusbar.
- Bottom dock/nav lives in an explicitly reserved, stable safe-area-aware region. No oversized opaque circular mask, content bleed-through, duplication, clipping, or arbitrary icon offset. It must not obscure last-row icons or intercept touches to the app grid. Restore original Home button/icon semantics; don't invent a generic Android launcher.
- Screen rotates/resizes correctly in available orientations without invalid hitboxes, clipping or keyboard overlap. Statusbar, Home, app list, persistent dock, lockscreen and application window layers are independently arranged; no global CSS styling leaking across pages via broad selectors.
- When many apps are installed, use bounded scrolling or pagination **inside the content region**, not a whole-page scroll that shoves bottom navigation away. Preserve scroll position as appropriate. Virtualized app list only if demonstrably necessary and not a regression risk.
- Per-app click/pointer targets line up with visible icon rectangles, not pre-scaled rectangles. Clicking Calendar must launch Calendar; clicking SnekByte must launch SnekByte, etc. Tap does not accidentally activate neighboring icon or hidden overlay.
- Home, Back and multitask/overview (where implemented) remain operable from a native GTK app as well as a PWA. Home should be reachable from any app as before, but avoid interfering with lockscreen unlock mechanics.

## 4 — APP REGISTRY + COMPONENT COMPATIBILITY (DO NOT SOLVE APPEARANCE BY BREAKING FUNCTIONS)

Reconcile current application catalogue (actual native `.desktop` apps, Flatpak exports, Nuxel PWAs, system apps) with the Home renderer. Ensure one visually consistent icon type/scale for all entries, with special cases for native icons only when justified. Images must be served from correct origins with permissions and cache busting. Handle missing icons gracefully with a consistent compact fallback, not an image sized 512px or 1024px into normal layout.

Validate app launch for visible entries (as installed): Browser, Settings, Camera, Calendar, Contacts, Files, Photos, SnekByte, Nuxtore/Software, and native third-party applications. The photograph does not prove all these are currently installed: detect and test only actual ones; report missing/uninstalled honestly. Preserve latest `./snekbyte.zip` integration and don't overwrite its game's own CSS/logic while fixing launcher CSS. Verify launcher uses the proper snake icon, not a camera icon or old placeholder.

Check display-order, label deduplication, delayed app scan, app icon MIME types/paths, PWA versioned assets, stale service worker and absence of broken raw technical widget cards. If launcher defaults to a fallback debug/list view on application-discovery failure, fix that failure **and** make fallback state visually bounded, keyboard/touch navigable and clearly informative.

## 5 — STATUS BAR, WALLPAPER, LOCKSCREEN, OSK AND INPUT REGRESSION CHECKS

The current photograph shows status text at the top and a dock at the bottom, so test layering explicitly. Preserve original wallpaper and Nuxel theme. Confirm status bar displays clock/battery/Wi-Fi without collision at normal startup and after network updates, battery updates and rotation. Battery percentage must be read from actual source; no fake fixed 100% just because screenshot shows 100%. CPU/GPU metrics must be valid or absent rather than strings like `0%0 MHz` / `0 MiB0 MiB`.

Verify lockscreen remains visually distinct and trusted: `./assets/nuxel-lockscreen.jpg`, `./assets/nuxel-lockhead.png` where still used, upward penguin lock swipe, 10 touch unlocks, no bypass by hiding DOM. `Back` hides OSK in app, `Home` returns to coherent launcher, and opening+closing Camera does not trap input. Rotation must preserve touch-coordinate mapping at 0, 90, 180, 270 where currently supported; restoring CSS must not break orientation policy service.

Avoid changing lower-level power/rotation or camera behavior unless the launcher regression is conclusively coupled; document external bugs separately, don't expand into A63 again.

## 6 — ENGINEERING TESTS (BEFORE TOUCHING THE PHONE)

1. Save a failing baseline test that reproduces this issue at the measured S10+ logical viewport, with full computed-style dimensions, screenshot, and relevant WebKit console errors.
2. Add or update screenshot/layout tests for Home portrait, landscape, statusbar and bottom nav at 360×760, 412×915, 720×1520 CSS px **as illustrative matrix values**, plus one case **from the real phone's measured viewport**. Do not infer CSS logical size solely from 1440×3040 panel resolution.
3. Verify app icon bounding boxes: sane size relative to cell, no image larger than parent/cell, bounded label height, no overflow beyond content-region top/bottom, no overlap with statusbar/dock, portrait grid with expected columns, finite scroll area.
4. Unit/integration tests for application registry mapping, icon fallback, PWA/native launch dispatch, Home/Back keyboard handling, runtime CSS asset hash/version, debug widgets default-off. Test landscape and display changes.
5. Inspect both CSS assets loaded and console output under the actual WebKitGTK engine if possible; Chromium desktop screenshots can support but **not replace** real WebKit/S10+ testing.
6. Check package/build pipeline preserves correct relative paths and deploys all CSS and icon files atomically. Bust stale WebKit service-worker/HTTP cache narrowly, with data-preserving migration; do not wipe all app profiles, browser bookmarks, SnekByte highscores, saved Wi-Fi passwords, or users' data.
7. Run package lint, existing test suite in relevant launcher modules and a small restart/resume regression. Capture stdout/stderr and exit status of commands; avoid declaring `PASS` from skipped tests.

## 7 — PHYSICAL S10+ ACCEPTANCE: GATE BEFORE SAYING "FIXED"

Ensure USB Live Console is functional before deployment. Back up exact installed files and hash them. Copy new UI assets atomically to staging under same filesystem, validate permissions and checksum, then switch safely. Restart only the minimal affected UI service, with a documented rollback path.

Required owner-visible checks:

- **A64-P1 FIRST FRAME:** On launching/reloading Home, app icons are compact, aligned in original grid, original theme visible, no oversized 512px images, no giant dark circle and no debug telemetry over the header. Capture a new on-phone screenshot and compare side-by-side with the attached broken-state photo and any historical good screenshot.
- **A64-P2 STATUS:** clock, battery and connectivity visually fit together on boot, after status changes; no overlapping/undefined debug strings.
- **A64-P3 NAV:** tap Home/Back/overview icons 10 times across different apps; UI doesn't have stuck overlays and each touch lands correctly. Check native GTK and PWA window cases.
- **A64-P4 ICON LAUNCH:** Calendar, Camera, Contacts, Files plus installed Browser/Settings/SnekByte/Photos apps each open from their *actual icon* and Home returns every time. A camera-frame hardware blocker cannot justify freezing the launcher or preventing exit.
- **A64-P5 SCROLL:** view and launch apps below first screen; scroll doesn't move the dock/statusbar. Last row not hidden beneath nav or OSK. No horizontal scroll in portrait.
- **A64-P6 ROTATION:** test upright portrait, landscape and return to portrait, with correct labels/hitboxes. Test other supported forced orientations if available.
- **A64-P7 LOCK:** press Power/lock/wake, perform ten real penguin drag unlocks; lockscreen and home are not CSS-contaminated.
- **A64-P8 RESTART:** restart launcher/UI only if safe; optionally owner-approved full cold reboot. Home appears correctly after fresh start and with status/app registry ready or pending, no flash of enormous unstyled icons.
- **A64-P9 NONREGRESSION:** Wi-Fi/Browser/SnekByte/Camera navigation remain at pre-patch baseline or better. Record any currently broken unrelated feature as pre-existing; don't silently mark it fixed.

A device screenshot without actual touch and app launch results is insufficient. Do not infer a functional UI from Fedora headless rendering.

## 8 — FAILURE PATHS AND ROLLBACK

If patch still renders giant icons or app controls are untappable, **immediately revert only changed launcher files** using verified live backups, minimize number of UI restarts, and retain recovery terminal. Compare baseline with candidate and establish why the original CSS/style resources didn't load. If good working Home can only be restored by a larger partial revert, perform change-by-change dependency audit first and explain which new functionality might be affected.

If old known-good launcher assets are present but incompatible with new app schema, create a targeted compatibility adapter to preserve current app catalogue while restoring old presentation. Distinguish `CSS_NOT_LOADED`, `VIEWPORT_DENSITY_MISMATCH`, `APP_CARD_REGRESSION`, `GLOBAL_STYLE_COLLISION`, `STALE_UI_BUNDLE`, `DOCK_STACKING_ERROR`, `WEBKIT_RENDERER_ERROR`, `DEPLOYMENT_MISMATCH`, or `UNKNOWN` based on evidence, not guesses.

## 9 — REQUIRED ARTIFACTS AND FINAL RESPONSE

Under `docs/a64-launcher-resurrection/` produce:

- `00-SAFETY-BASELINE.md`: USB console, worktree state, backups, exact live paths/hashes, rollback instructions.
- `01-VISUAL-DIAGNOSIS.md`: photograph observations, measured live viewport/DPR/computed styles, CSS asset load, root-cause evidence, before screenshot and status.
- `02-CHANGE-MAP.md`: file-by-file diff, reasons, what was preserved from A63/12K and latest SnekByte.
- `03-TEST-RECEIPTS.md`: test commands, outputs, failures and skipped tests.
- `04-PHYSICAL-PASS-MATRIX.md`: A64-P1 to A64-P9, `PASS_PHYSICAL`, `PASS_OFFLINE_ONLY`, `FAIL`, `BLOCKED`, `NOT_TESTED`; links to fresh on-device screenshots and logs.
- `05-ROLLBACK.md`: tested commands returning exactly the changed launcher to the previous state.
- Before-after screenshots under `evidence/` with time, device and app version; keep owner photo as original unedited evidence.

Report: (a) concise precise root cause, (b) exact files changed and commits, (c) what was deployed vs merely staged, (d) links/paths to screenshot evidence, (e) actual icon/navigation tests, (f) untouched existing services, (g) any remaining blockers, (h) rollback procedure.

### FINAL DIRECTIVE

**Restore the beautiful, usable Nuxel launcher FIRST. This is a surgical visual/interaction regression repair, NOT a greenfield desktop, NOT a new Android clone, and NOT a fresh 12KMAXIMUM feature march.** Use the photographed failure as your reproducible input; finish when the real S10+ once again has a compact, clean, touch-correct Home UI with no accidental status telemetry or swollen dock. Don't claim an on-device PASS without seeing and testing the deployed output. 🐧⚡
