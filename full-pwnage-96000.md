# FULL-PWNAGE-96000 — Nuxel Global UX, File-Picker, Shell Chrome & 30 FPS Responsiveness Fix

**Mission ID:** PWNAGE-96000  
**Target repository:** `nuxel-main`  
**Repository baseline supplied for this mission:** `VERSION=v0.8.1-beta` (verify the actual checkout before changing anything)  
**Primary physical target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820 / Mali-G76  
**Mission type:** end-to-end source audit, implementation, tests, deployment and physical-device verification  
**Priority:** high; user-visible regressions and performance  
**Core principle:** fix the real shared system layer where appropriate; do not add duplicate services, duplicate bars, duplicate fetch loops, fake UI or unsafe compatibility workarounds.

---

## 0. EXECUTION ORDER — READ THIS FIRST

You are executing this mission, not merely writing a plan. Inspect the current repository and the running phone, reproduce the reported behaviours, trace each issue to its actual owner, implement the smallest correct architecture-wide fixes, test them, deploy them through the repository's existing deployment mechanism, and verify the result on the physical S10+ wherever possible.

Do not ask the user to restate information already present in the repository or this mission. Do not stop after producing recommendations. If one item is blocked by a genuine hardware/kernel/application limitation, complete every independent item, document the exact blocker and evidence, and leave the blocked route safe and explicit.

### 0.1 Repository-first rules

1. Start with `pwd`, `git status --short --branch`, `git rev-parse HEAD`, `git log -1 --oneline`, `cat VERSION`, and the project README/architecture docs.
2. Inspect current source before editing. The paths named below are known starting points from the supplied archive, not permission to assume every file is still unchanged. Search the whole repository for the live owner and deployment source of each feature.
3. Find the established deployment/build scripts under `./scripts`, `./tools`, `./images`, and the relevant device directories. Use the canonical scripts and manifests. Do not invent an alternate deploy path.
4. Identify whether the checkout contains uncommitted user work. Never overwrite or reset user changes. Make a timestamped backup or a patch/branch before modifying deployed files.
5. Keep source, generated release copies, package manifests, hashes, cache-busters and tests synchronized. A source-only fix is not complete if the phone image still ships an old copy.
6. Do not claim that a service/app is installed or a portal is operational until the live device proves it.
7. Do not pull in a full desktop environment or replace the working compositor merely to solve a chooser or layout issue.
8. Do not perform a kernel replacement, repartition, bootloader operation, firmware flashing or unrelated system upgrade in this mission.

### 0.2 Existing graphics path is protected

The current framebuffer presenter remains the known-good fallback and must remain installed, buildable, deployable and recoverable. Do not delete or replace `nuxel-wl-fb`, the A67 presenter, its owner lock, animation handoff, panel commit logic or recovery scripts.

The supplied source audit identifies these relevant facts to verify again on the live device:

- `tools/s10plus/a67/nuxel-wl-fb.c` is the current reference presenter.
- It uses Wayland screencopy into reusable SHM, retains a previous frame, compares rows, has NEON row expansion/scaling, supports partial-row writes and skips unchanged presents.
- `FBIOPAN_DISPLAY` is required for the S10+ command-mode panel to latch changed framebuffer content. Never remove it as a supposed VSync/performance fix.
- `services/nuxel-s10/systemd/nuxel-wl-fb.service.d/15-idle-fps.conf` currently overrides active output to 20 FPS; the C program default is 30 FPS and idle backoff is 8/3/1 FPS.
- The current production route is GPU-composited Phoc → Wayland SHM screencopy → CPU bridge → `/dev/fb0` → Exynos panel. Do not claim end-to-end DMA-BUF/KMS scanout.
- The current code has no proven S10+ DRM/KMS scanout path. Do not enable the old Exynos7 DECON DRM driver or claim that a Mali node implies panel direct scanout.

The mission's 30 FPS work must be a measured improvement to the existing route, with a reversible policy and preserved idle/screen-off behaviour. Do not activate NEO/DMA-BUF/KMS as part of this mission.

### 0.3 Security and privacy rules

- Do not solve file picker failures with `--filesystem=host`, `--device=all`, `--no-sandbox`, broad home access or unrestricted root file browsing.
- Do not weaken Flatpak, AppArmor, SELinux, D-Bus policy, portal permissions or browser network defaults to make a test pass.
- File selection must return the expected URI/document handle through the supported portal or toolkit contract. Do not silently pass unrestricted host paths to sandboxed apps.
- Do not log message contents, selected private filenames, cookies, full URLs containing credentials, Wi-Fi SSIDs or other personal content in performance logs.
- Keep the existing external-navigation opt-in policy in Nuxel Browser. Do not silently turn on external network access.

---

## 1. MISSION OBJECTIVES

Implement and physically verify all of the following:

1. **Attachment file picker:** In Ferdium, WhatsApp and Signal, pressing the attachment/image button must open a working selection flow where the user can choose **Gallery** or **Files / File Manager**, select an image (and other supported files where appropriate), return to the messaging app and see the selected attachment/preview. It must not launch a separate file manager process that opens an empty/unrelated window and loses the selection request.
2. **Battery/USB icon truth:** battery charging lightning remains the charging indicator. The separate USB connection icon must not appear merely because an external charger is supplying power. Show the USB icon only for a real PC USB data/host connection or an explicitly active USB data function such as file transfer/USB console.
3. **Nuxel Browser controls and layout:** add a proper top-right vertical three-dot menu. Add persistent Phone/Mobile site and Desktop site modes. Phone mode must render responsive mobile pages correctly on the S10+ viewport; Desktop mode must request the desktop site through the actual browser engine, not merely change Nuxel's own CSS. Keep the user's choice across app restarts and apply it to the correct browser WebView only.
4. **Firefox responsiveness:** make Firefox usable on the S10+ display and touch input. Diagnose whether any shared GTK/Wayland/output-scale issue is causing the same failure in other native apps. Fix a true global system issue once, while retaining app-specific configuration only where needed.
5. **One correct fullscreen top bar:** when a native GTK or Flatpak app is fullscreen/immersive and the user swipes down from the top, show the same canonical Nuxel top-bar design and truthful system status used by default. Remove the incorrect/obsolete alternate top-bar implementation from the live code path completely. Do not remove the only working bar or create two bars.
6. **Quick Settings responsiveness:** profile and optimize opening, closing, expanding, collapsing, tile interactions and first interaction after open. Remove redundant polling/fetching/rendering only when proven redundant. Preserve cache-first immediate interaction and truthful provider states.
7. **App drawer responsiveness:** profile and optimize drawer opening/closing, first paint, scrolling, icon rendering and gestures. Preserve the existing cached drawer DOM/signature optimisation; do not regress it by rebuilding all tiles on every open.
8. **Global phone responsiveness:** profile Home, desktop transitions, top bar, Quick Settings, drawer, native GTK apps, Flatpak apps and browser interactions. Identify real main-thread stalls, duplicate provider calls, synchronous IPC, expensive layout/paint, image decode, input delays and renderer/compositor bottlenecks. Fix common root causes globally and app-specific causes locally.
9. **30 FPS frame pacing / VSync:** safely move the active presentation target to 30 FPS where sustained frame times, input latency and temperature support it, and synchronize presentation to real display refresh/vblank if the current driver exposes a real supported mechanism. Do not falsely label a timer-based 30 FPS cap as VSync.

---

## 2. REQUIRED BASELINE AND REPRODUCTION

Create `docs/pwnage-96000/` and a timestamped evidence directory, for example `docs/pwnage-96000/evidence/YYYYMMDDTHHMMSSZ/`. Preserve raw logs and screenshots. Before changing anything, collect:

### 2.1 Platform/runtime baseline

- device model, board, kernel release/config, boot ID, output modes, physical resolution, compositor output resolution and scale;
- `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, `XDG_CURRENT_DESKTOP`, session D-Bus address and running session user;
- Phoc/wlroots/Mesa/WebKit/GTK/Firefox versions and renderer identification;
- active systemd units relevant to Nuxel Home, bridge, portal, browser, shell chrome, Wayland and framebuffer presenter;
- installed packages and running processes for `xdg-desktop-portal`, `xdg-desktop-portal-gtk`, GTK3/GTK4, Flatpak, bubblewrap, Ferdium, Signal and Firefox;
- `nuxel-wl-fb` service environment, `NUXEL_TARGET_FPS`, idle backoff thresholds, frame counters, capture/compare/blit/pan timings and panel pan failures;
- current CPU/memory/temperature/battery sample while Home is idle and while opening Quick Settings/drawer.

### 2.2 Reproduce each issue

Record exact sequence, expected result, actual result, foreground app ID, window role/state, relevant logs and screenshot/video where possible.

- Ferdium: open a conversation, attach image, observe chooser, choose Gallery, select a real test image, verify preview and send to a test destination only if safe. Also test Files selection.
- WhatsApp: use the installed supported route (Ferdium web app or separately installed WhatsApp wrapper); identify its process and app ID. Do not invent a separate WhatsApp package if absent.
- Signal: repeat only if installed and genuinely runnable. If sandbox/kernel prevents it, report the precise prerequisite and test the same portal path with an instrumented client.
- Battery: test wall charger only, PC USB connected, PC connected without data transfer, MTP/file transfer, USB console, unplugged and unknown provider state.
- Browser: test Phone and Desktop settings against representative responsive sites that explicitly return different mobile/desktop content; verify actual server-delivered layout/UA. Test browser rotation and reload.
- Firefox: test launch, first useful frame, toolbar visibility, keyboard, scrolling, pinch zoom (where permitted), file chooser and safe-area clearance.
- GTK/Flatpak fullscreen: open at least one native GTK app and one Flatpak app. Hide chrome if currently immersive, swipe down from top, record which layer-shell surface appears, its owner PID, dimensions, style and input region. Verify no duplicate or dead overlay.
- Quick Settings: measure open latency, first usable tile time, state hydration latency, duplicate provider calls and close-stop behaviour.
- Drawer: measure open latency, render duration, scroll frame pacing and number of DOM nodes/images created on each open.
- General: compare Home idle, app launch/restore, desktop switch, QS open/close, drawer open/close and a native/Flatpak app interaction.

Never treat a source-level unit test or emulator screenshot as proof that the physical display works.

---

## 3. WORKSTREAM A — FIX THE SYSTEM FILE-CHOOSER / ATTACHMENT FLOW

### 3.1 Understand the current portal architecture first

Known source starting points:

- `services/nuxel-portal/src/portal.py`
- `services/nuxel-portal/systemd/nuxel-portal.service`
- `services/nuxel-portal/test-portal-policy.py`
- `configs/nuxel/portals.conf`
- `configs/dbus/org.nuxel.Portal.conf`
- `docs/a53/FLATPAK-SANDBOX-PORTALS.md`
- `pwa/nuxel-apps/files/`
- `pwa/nuxel-apps/photos/` and/or the canonical Gallery app found in the current registry
- native app launch, Flatpak installation and desktop-entry manifests

**Critical distinction:** `services/nuxel-portal/src/portal.py` is the Nuxel hardware-permission broker (`org.nuxel.Portal`). It is not automatically the FreeDesktop `org.freedesktop.portal.Desktop` service and does not implement `org.freedesktop.portal.FileChooser` merely because its name contains “portal”. Do not conflate the custom permission broker with XDG Desktop Portal.

`configs/nuxel/portals.conf` in the supplied tree routes the FileChooser implementation to `gtk`. Verify whether the frontend and selected GTK backend are actually installed, activatable, registered on the correct *user session bus*, and usable on the live Phoc session. Historical `docs/a53` evidence says the portal frontend/backend were absent at an earlier point; that report may be stale. The live runtime is authoritative.

### 3.2 Audit the real call path

For each app, determine whether attachment opens:

- `org.freedesktop.portal.FileChooser.OpenFile` via XDG Desktop Portal;
- GTK `GtkFileChooserNative` / `GtkFileChooserDialog` directly;
- Electron's native dialog API;
- Chromium/CEF/Qt file chooser integration;
- an app-specific helper that launches `org.nuxel.Files` without an active selection/response contract.

Trace D-Bus request handle → portal frontend → selected backend → visible chooser → response signal → URI/document grant → application. Record app ID, sender, parent window handle and portal request path without logging private file contents.

Inspect the actual process/session environment. A portal service on the system bus is not enough; `org.freedesktop.portal.Desktop` and its backend must be on the correct user session bus and use the right runtime directory and Wayland display. Check user service activation, D-Bus service files, portal backend descriptors, desktop selection and `XDG_CURRENT_DESKTOP`/`XDG_DATA_DIRS`.

### 3.3 Required user experience

When an application asks to attach an image, the selection flow must visibly provide two clear sources:

- **Gallery** — the Nuxel Gallery/Photos media collection, initially focused on images and videos appropriate to the request (respect MIME filters and `accept` constraints).
- **Files** — the Nuxel file manager / normal file hierarchy for selecting documents, downloads and arbitrary permitted files.

The source choice must remain part of one active selection request. The original requesting app must receive the selected item via the file chooser response; do not simply open Gallery or Files as a disconnected app and expect the chat app to infer the selection.

If an integrated Nuxel chooser is necessary, implement it as a real supported FileChooser backend/adapter or as the appropriate native GTK chooser integration. It must satisfy the XDG portal contract. A custom visual dialog that cannot complete the original portal request is not a fix.

If the GTK portal backend is the correct safe solution, configure it properly and add Nuxel Gallery and Files locations/shortcuts in the backend's supported mechanism. If GTK backend cannot provide the required source switch, implement a small Nuxel FileChooser backend that is protocol-correct. Do not build a second independent file-picker service that competes with XDG portals.

### 3.4 Portal correctness requirements

- Implement/verify OpenFile, OpenFile multiple-selection, and SaveFile only to the extent required by clients and backend contract. Do not advertise unsupported interfaces.
- Correctly handle request object paths, caller unique names, cancellation, response codes, parent handles, filters, current name, current folder, choices, multiple selection and MIME types.
- Keep document/file access limited to selected files. For Flatpak use the document portal or backend-provided FD/URI grant semantics; do not hand out `--filesystem=host`.
- Preserve filenames with Unicode, spaces, apostrophes and non-ASCII characters.
- Verify file URI encoding and correct response format. Use the portal's returned URIs or open FDs according to the protocol; never manually concatenate unescaped file paths.
- Keep chooser ownership and focus correct above the invoking native/Flatpak window, including app-modal and fullscreen clients.
- On cancel, return a normal cancelled response and leave the chat app usable. On backend crash/timeout, fail closed and display a useful diagnostic rather than an empty invisible window.
- Support image filters (`image/*`, PNG, JPEG, WebP, GIF, HEIC where the installed stack supports it), generic documents and file types requested by the application.
- Verify `GtkFileChooserNative` fallback for native GTK apps and Electron/Chromium/Signal wrappers where the app does not use the portal. Apply `GTK_USE_PORTAL=1` only when supported and only in the intended session/app environment; do not add it blindly to all processes if it breaks native dialogs.
- Do not break the camera portal or the permission broker `org.nuxel.Portal`; they are separate subsystems.

### 3.5 Deployment and diagnostics

Add read-only portal status output showing frontend/backend service names, D-Bus owner, version, selected FileChooser backend, readiness, last request outcome and error count. Do not expose private paths or user data. Ensure it identifies:

- XDG Desktop Portal frontend available/unavailable;
- FileChooser backend available/unavailable;
- backend activation success/failure;
- request reached backend;
- chooser was presented;
- selected response/cancel/error.

Use the repository's package/build/deploy scripts. If installing missing packages is required, inspect the package transaction and dependencies first. Do not silently install an entire desktop environment.

### 3.6 File-chooser tests

Create automated tests for portal request/response and a small real client using the same path as the messaging app. Test:

1. Gallery source opens and shows actual media files.
2. Selecting a test image returns one valid file and the app receives it.
3. Files source opens and selects a document/image.
4. Multiple selection works only when requested.
5. MIME filters and `accept` restrictions are respected.
6. Cancel closes the chooser and returns a cancelled response.
7. Unicode and spaces in filenames work.
8. Flatpak sandbox can read the selected file but not unrelated host files.
9. Parent-window transiency/focus works from GTK and Electron/Flatpak.
10. Closing/relaunching apps does not leave orphaned chooser windows, portal requests or document grants.

Physical acceptance: test image attach in Ferdium, WhatsApp and Signal if each is installed/runnable. Confirm preview appears in the chat composer. Do not send to a real contact; use a self/test conversation.

---

## 4. WORKSTREAM B — CORRECT BATTERY LIGHTNING VS USB CONNECTION ICON

Known source starting points:

- `pwa/nuxel-home/js/status-bar.js` — `StatusBar._renderUsb()` and `_renderBattery()`.
- `pwa/nuxel-common/statusbar-icons.js` — canonical icon definitions/preferences.
- `services/nuxel-bridge/src/api.py` — canonical battery/USB/charging provider state.
- USB mode monitor and MTP/console services under `services/nuxel-s10/systemd/`.
- corresponding status bar HTML/CSS and tests.

The supplied `status-bar.js` currently has this precedence:

1. active file transfer;
2. active USB console;
3. active charging where `usb.pc_connected === true OR charging.external_power === true`;
4. PC-connected data link.

The `charging.external_power` condition is the likely reason a charger-only power connection renders the separate USB icon. Verify live state and do not assume the source condition is the only contributor.

### 4.1 Required state semantics

The battery icon's lightning glyph is the charging indicator and remains the single visual indicator that the battery is charging.

The separate USB icon represents a USB *data/host connection or an active USB function*, not external power.

Required display matrix:

| State | Battery lightning | Separate USB icon |
|---|---|---|
| Wall charger only / external power / `pc_connected=false` | Yes if battery provider says charging | **Hidden** |
| Charging + real PC USB data connection | Yes | Visible |
| PC USB data connection, not charging | No | Visible |
| MTP/file transfer active | As battery state says | Visible with file-transfer state |
| USB console active | As battery state says | Visible with console state |
| Wireless charging only | As battery state says | Hidden |
| Unknown/missing USB state | As battery state says | Hidden unless a separate active data function is explicitly proven |
| Cable unplugged | No unless another charging provider says charging | Hidden |

No external-power-only status may promote `usb.pc_connected` to true. Do not invent PC connection from `charging`, `external_power`, USB VBUS or cable presence.

### 4.2 Implementation

- Make provider truth canonical in the bridge/API; UI may render only explicit booleans and valid active transport state.
- Remove the `charging.external_power` branch from USB icon visibility. Keep charging exclusively in battery state.
- Preserve explicit active file-transfer and USB-console indications, even if the normal PC connection field is transiently unavailable, provided those services themselves prove an active USB data session.
- Preserve user icon visibility preferences from `NuxelStatusBarIcons`.
- Add a stable render key so unchanged state causes no DOM/style churn.
- Keep accessible labels truthful: “USB data connection”, “USB file transfer active”, “USB console active”. Never label a charging-only connection as USB data.

### 4.3 Tests

Add table-driven tests for every row above at both bridge/provider and JS renderer layers. Include malformed/missing fields, stale data, charging status `Full`, null battery state and event-order permutations (USB arrives before battery, battery before USB, unplug occurs during MTP). Test physical charger-only and PC connection cases. Confirm the separate USB glyph is absent with a wall charger while the battery lightning remains.

---

## 5. WORKSTREAM C — NUXEL BROWSER THREE-DOT SETTINGS + PHONE/DESKTOP SITE MODE

Known source starting points:

- `pwa/nuxel-apps/browser/app.json`
- `pwa/nuxel-apps/browser/index.html`
- `pwa/nuxel-apps/browser/css/browser.css`
- `pwa/nuxel-apps/browser/js/browser.js`
- `pwa/nuxel-apps/browser/manifest.json`
- `shell/nuxel-browser-native/nuxel_browser_native.py`
- app registry, launcher mapping, native browser packaging and browser install scripts.

**Important existing architecture:** the repository contains two browser implementations:

1. A PWA page viewer (`pwa/nuxel-apps/browser/`) with an iframe, local-first pages, opt-in external navigation and local bookmarks/history.
2. A native GTK3/WebKit2GTK 4.1 browser (`shell/nuxel-browser-native/nuxel_browser_native.py`) using a real top-level `WebKit2.WebView`. This native view currently sets a mobile Android/S10+ User-Agent directly in WebKit settings.

The agent must identify which browser entry is actually launched on the S10+, whether both are installed/visible, and whether one is a fallback. Do not implement an attractive three-dot menu in an unused browser while the user launches the other one. Consolidate the user-facing route or ensure both supported routes expose the same persisted settings contract without creating two competing browser apps.

### 5.1 Three-dot menu

- Put a vertical three-dot button (`⋮`) at the top-right of the browser's own toolbar, with accessible label “Browser settings”.
- Use a compact native-feeling popup/sheet that fits the portrait phone display, respects top/bottom safe areas and is dismissible by Back, outside tap and explicit close.
- Menu items must include a clearly labelled site mode: **Mobile site** / **Desktop site**. Show the active selection (checkmark or radio state).
- Keep other existing browser functionality (Back, Forward, Reload, URL/search, bookmarks, history, external-navigation policy) intact.
- The menu must not be obscured by the system topbar or nav dock; account for the shell's safe areas and keyboard.
- Avoid emoji hamburger/three-line ambiguity: it must be a recognizable three-vertical-dot overflow control.

### 5.2 Phone / Mobile site mode

- Default to the current mobile/S10+ UA behavior unless the user has previously selected Desktop.
- Use the actual current viewport dimensions and device scale; no fixed 360×760 assumptions.
- Ensure `meta viewport`, orientation, safe areas, responsive controls and WebKit viewport handling work on the actual 720×1520 compositor output/1440×3040 physical panel configuration as appropriate.
- Touch targets, address bar, menu, scrollbars, keyboard and bottom/top system chrome must fit without horizontal clipping.
- Do not apply a global User-Agent override to Home, GTK apps, WebKit shell host or other app WebViews.

### 5.3 Desktop site mode — must be genuine

- Set a desktop User-Agent on the **browser's own WebKitWebView** (not globally) using the supported WebKit API. Remove mobile indicators such as `Android`, `Mobile` and `Mobile Safari` from the desktop UA, while using a truthful Linux desktop UA appropriate to the actual architecture/engine.
- Apply the new UA before reloading the current page. Provide a clear “Reload to apply” option if safe in the UI; switching modes should not silently lose form state without warning.
- Persist mode per browser profile using the existing config/settings persistence policy. Validate/migrate malformed values safely.
- Do not implement desktop mode by shrinking Nuxel's toolbar, changing only outer CSS or spoofing a DOM property while requests still carry a mobile UA.
- Where WebKit's mobile viewport handling keeps the desktop page artificially narrow, implement a tested fit-to-width/page zoom policy or the correct native viewport handling. Avoid hardcoded zoom that clips content. Keep user zoom independent from the Phone/Desktop mode.
- Keep per-origin behavior optional only if a clear design is supported; the minimum requirement is a global browser mode, not a complicated rules UI.
- Test sites that actually provide desktop and mobile variants. Verify request UA, server response/layout and screenshot. Test reload, Back/Forward, tabs/restart and orientation.

### 5.4 Browser architecture / security

- Preserve `network: opt-in` and the default blocked external-navigation policy in the PWA browser if that route remains supported.
- Preserve TLS verification; do not accept invalid certificates globally.
- Do not disable WebKit sandboxing or inject host filesystem access.
- The current native browser's FIFO command interface (`/run/nuxel-browser.cmd`) and state (`/run/nuxel-browser.state`) must remain compatible with the system Back contract; extend its command/state schema in a backwards-compatible way if needed.
- If moving the user-facing browser to the native WebKit implementation, update app registry, desktop files, manifests, service/launch scripts and uninstall path atomically. Do not leave both duplicate entries.
- Avoid adding multiple periodic status polling loops. The native browser currently refreshes a compact status text every 15 seconds; use shared cached system status if the real browser chrome needs status, or remove duplicate polling if system chrome already owns it.

### 5.5 Browser tests

- PWA/browser test for menu open/close, active mode display, persistence and no external fetch on startup.
- Native WebKit test that the UA changes only for that browser WebView and the current URI reloads under the selected mode.
- Physical S10+ test in portrait and landscape; check toolbar not clipped and browser content uses available area.
- Regression test external navigation remains opt-in, history/bookmarks remain local and Back FIFO still works.

---

## 6. WORKSTREAM D — FIREFOX AND GLOBAL NATIVE/FLATPAK RESPONSIVENESS

Known source starting point for Firefox:

- `services/nuxel-s10/bin/nuxel-flatpak-firefox`

This wrapper uses Flatpak only when unprivileged user namespaces work; otherwise it executes the genuine Fedora `/usr/bin/firefox` RPM. Preserve this security fallback. Do not force `--no-sandbox`, `--filesystem=host`, software rendering or a host-library override.

### 6.1 Determine the common cause first

Inspect:
- actual Firefox binary/package/runtime selected at launch;
- Wayland vs XWayland connection, GTK backend and scale factor;
- compositor output geometry/scale and input coordinate mapping;
- `GDK_BACKEND`, `GDK_SCALE`, `GDK_DPI_SCALE`, `MOZ_ENABLE_WAYLAND`, Firefox touch/zoom preferences and app-specific environment from current scripts;
- GTK3/GTK4 theme, font metrics, header bars, dialog sizing, safe areas and virtual keyboard integration;
- Flatpak runtime's access to the intended Wayland socket, fonts, theme and portal services (without broad filesystem privileges).

Use evidence to decide whether the issue is global (output scale, GTK theme/DPI, Wayland seat/input, safe-area or touch-coordinate transform) or Firefox-specific. Fix a global defect once. Keep per-app overrides only for proven exceptions.

### 6.2 Firefox acceptance

- Launch via the existing wrapper and report which path is selected (Flatpak or RPM).
- Full-window usable content area fits the current phone output and global shell bars; no clipped top controls, bottom controls or horizontal overflow in Firefox chrome.
- Address bar and tabs/buttons are touch-sized and reachable; scrolling and keyboard do not cause focus/viewport loss.
- Web content supports mobile responsive sites, desktop site functionality if Firefox already exposes it, pinch/zoom and orientation.
- File chooser invoked from Firefox uses the same working global chooser path.
- Test page refresh, history, tab switching, text entry, link interaction, file upload and fullscreen video if supported.

### 6.3 GTK and Flatpak global rules

- Make native app toplevels use the correct Wayland display, output geometry and device scale. Avoid per-app hardcoded sizes where maximization/fullscreen or compositor sizing is correct.
- GTK apps must remain touch-usable at the handset's actual logical size. Set a global GTK scaling policy only if the measured output scale and real runtime show it is needed. Do not stack `GDK_SCALE` and `GDK_DPI_SCALE` blindly.
- Preserve accessibility and keyboard support.
- Respect app-specific title bars where an app needs one; ensure Nuxel's system chrome remains independent and does not duplicate titlebars.
- Fix common XDG portal theme/chooser integration globally when it is genuinely common.
- Test at least two GTK native apps and two Flatpak apps with different toolkits when available.

---

## 7. WORKSTREAM E — ONE CANONICAL TOP BAR FOR FULLSCREEN GTK/FLATPAK APPS

Known source starting points:

- `tools/s10plus/a45/nuxel-statusbar.c`
- `tools/s10plus/a45/nuxel-shell-chrome.sh`
- `tools/s10plus/a45/nuxel-session.sh`
- `tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml`
- `pwa/nuxel-home/index.html`
- `pwa/nuxel-home/js/status-bar.js`
- `pwa/nuxel-home/css/status-bar.css`
- `pwa/nuxel-home/js/immersive.js`
- `pwa/nuxel-home/js/gestures.js`
- `pwa/nuxel-home/js/navigation.js`
- `services/nuxel-bridge/src/api.py`
- foreign-toplevel/focus helpers and existing shell-chrome state contract.

### 7.1 Understand the actual architecture

A DOM status bar inside Nuxel Home cannot appear above an independently activated GTK/Flatpak Wayland toplevel merely by increasing CSS `z-index`. The system must use one trusted native layer-shell surface (or a single equivalent native shell-chrome owner) while native/Flatpak apps are foreground. The Home DOM status bar may be canonical for Home, but the native statusbar surface must visually and semantically match it when Home is not the foreground surface.

The supplied repository includes `nuxel-statusbar.c` and a `nuxel-shell-chrome.sh` supervisor. The supervisor starts `nuxel-statusbar` if the binary exists, and `nuxel-session.sh` starts the supervisor. Historical prompts describe older builds where the native statusbar was not built or launched. Do not rely on those historical claims: inspect the *current build output, installed executable, live PID, layer surface and visible screenshot*.

The wrong fullscreen bar may be the old native C bar, a legacy overlay, an application-provided title/status bar, an obsolete alternate surface or duplicated logic. Trace the real visible surface to its binary and source. Do not delete code by filename guess.

### 7.2 Required single-owner model

Create/retain one explicit chrome ownership mode/state, e.g. `home-dom`, `native-app`, `locked`, `transition`, `unavailable`. It must be atomic and observable. Exactly one visible status-bar implementation at a time:

- Home PWA foreground: canonical Home DOM status bar; no duplicate native top bar.
- Native GTK or Flatpak foreground, unlocked: one canonical native Nuxel top bar above the app.
- Fullscreen native/Flatpak app with top chrome hidden: a narrow trusted top-edge gesture strip only; swipe down reveals the same canonical native top bar.
- Lockscreen: lockscreen/security layer owns top-level presentation according to current tested lock contract; a native app/topbar must never cover or bypass it.
- Transition/app launch/close: preserve exactly one correct state; no flicker, ghost, wrong bar, or stacked topbar surfaces.

The Nuxel bottom Back/Home/Tabs dock remains the existing authoritative nav owner. Do not create another dock while fixing the top bar.

### 7.3 Visual parity requirement

The native bar shown over GTK/Flatpak apps must match the default Nuxel bar in:

- layout, height, spacing, padding, icons, font/weight, background/opacity and colors;
- time/date formatting, battery lightning and percentage;
- Wi-Fi, signal, Bluetooth, location, NFC, sound, USB data and remote indicators as applicable;
- status icon preference visibility and safe-zone/camera cutout handling;
- orientation, logical resolution, input/gesture regions and reserved content space.

Use one shared state model/provider contract. The native renderer may be C/Cairo/Pango while Home is HTML/CSS, but they must consume the same normalized data and design tokens/assets. Do not add duplicate high-frequency polling. Reuse the existing bridge/state events or shared status snapshot.

### 7.4 Swipe behaviour

- When immersive: downward pull from the top edge reveals the canonical Nuxel top bar.
- A controlled upward gesture hides the revealed bar according to the existing gesture contract.
- No second alternative bar may appear after a second swipe.
- Swipe must not steal normal app content touches except the reserved top gesture strip.
- Native bar's visible touch/input region must match the gesture design. Empty/pass-through regions must not swallow application taps.
- Bar auto-hide timing and top-edge gesture strip must be consistent across GTK, Flatpak, Firefox, Ferdium, Signal and browser native windows.
- Orientation changes recalculate geometry and hit regions.

### 7.5 Remove the wrong implementation safely

After identifying the wrong renderer:
1. Promote/rewrite the canonical native bar implementation so it matches the default Nuxel statusbar.
2. Redirect the shell supervisor/session/launcher to that one implementation.
3. Remove the obsolete alternate bar implementation, old UI assets, duplicated CSS/JS/C, redundant service startup and dead deployment copies from the live code/build/package path.
4. Update release manifests/tests so the removed code cannot be silently reintroduced by an old build script.
5. Keep compatibility shims only if a supported branch still needs them; mark them deprecated and ensure they cannot launch concurrently.
6. Do not delete Home's DOM bar; it remains correct for Home when native chrome is not in use.
7. Do not delete `nuxel-statusbar.c` simply because it is native; it may be the implementation that needs to become the correct canonical native version.

### 7.6 Tests

Test: Home; one GTK app; one Flatpak app; Firefox; Ferdium; Signal if installed; native browser; fullscreen; non-fullscreen; app switch; lock while app foreground; unlock; OSK shown/hidden; rotation; app close; shell chrome child crash/restart. At every point count visible bar surfaces and confirm exactly one correct surface (or none when locked/hidden by contract). Capture actual panel screenshots and verify status values.

---

## 8. WORKSTREAM F — QUICK SETTINGS OPEN/CLOSE AND PROVIDER EFFICIENCY

Known source starting points:

- `pwa/nuxel-home/js/qs.js`
- Quick Settings CSS/markup in `pwa/nuxel-home/index.html` and `pwa/nuxel-home/css/style.css` / other current CSS files
- `pwa/nuxel-home/js/bridge.js` / host bridge
- `services/nuxel-bridge/src/api.py`
- NetworkManager/BlueZ/GeoClue/audio/power/permission provider services.

### 8.1 Preserve improvements already present

The supplied `qs.js` already has several important performance behaviours:

- cached state is rendered before asynchronous refresh;
- opening uses a bounded refresh after two animation frames;
- `_stateSyncPromise` prevents overlapping complete status refreshes;
- the panel owns its visible-only timer and stops it in `close()`;
- location refresh is bounded while the panel is open;
- stale responses are invalidated with generation counters;
- provider unknown/unavailable values are not fabricated as OFF.

Do not remove or regress these behaviours. The task is to profile and improve the remaining critical path, not to rewrite Quick Settings from scratch.

### 8.2 Measure the complete interaction

Instrument:
- gesture start → overlay state update;
- overlay state update → first visible panel frame;
- first visible frame → first interactive tile;
- provider request start/end per provider;
- cache hit/miss and stale response discarded;
- time spent in DOM render/layout/style/paint;
- tile press → action dispatch → confirmed provider state;
- close gesture → timer cancellation/panel hidden.

Use performance marks/measures and a bounded diagnostic buffer. No per-frame console logging.

### 8.3 Optimize data fetching

- Build a provider dependency map. Identify fields already delivered by the one `bridge.getPhoneStatus()` response and do not query the same property again through multiple endpoints unless a separate action/status owner is genuinely required.
- Coalesce simultaneous panel-open and startup requests; keep one in-flight promise per provider, not only one top-level promise if independent provider updates still duplicate.
- Use a consistent cached snapshot for initial render. Refresh only fields that are stale or event-invalidated.
- Parallelize independent provider reads only when that reduces open latency and doesn't saturate the bridge/DBus/event loop. Avoid serial N× round-trips when safe batching is possible.
- Prefer event/subscription updates for stateful radios/services where the existing bridge can provide them reliably. Do not create a permanent fast polling loop for the panel.
- Keep timers stopped when Quick Settings is closed, Home is hidden, display is off or the session is locked, except for a documented safety reason.
- Use request generations/cancellation so late responses cannot repaint a closed or reopened panel with stale state.
- Distinguish action command acknowledgement from observed final state. Do not mark a toggle active before the provider confirms it.
- Maintain tri-state/unknown truth; performance changes must not fabricate values.

### 8.4 Optimize rendering/animation

- First frame must appear immediately from cached state; provider waits must not block the gesture or opacity/transform animation.
- Use compositor-friendly transform/opacity transitions. Avoid animating expensive layout properties (width/height/top/left) when translate/scale is suitable.
- Avoid rebuilding all tile DOM or decoding tile icons on every open. Keep stable nodes and update only changed attributes/text/classes.
- Batch all DOM writes in one animation frame after provider results; do not interleave layout reads/writes per tile.
- Respect touch scrolling inside expanded details and avoid accidental shade-dismiss gestures.
- Preserve swipe direction contract and hit targets.
- Check for redundant duplicate CSS animations, filters, shadows, large blur, forced layout, synchronous JSON parsing and expensive icon SVG/PNG replacement.
- Reduce/reuse animations when hidden; do not keep animating invisible content.

### 8.5 Acceptance criteria

- Quick Settings panel is visibly responsive before providers finish.
- Measure and report open-to-first-paint and open-to-interactive p50/p95 over repeated physical tests.
- No duplicate provider request from opening during startup refresh.
- Close stops visible-only timers and prevents stale results from mutating hidden state.
- Toggle state always reflects the provider, including unsupported/unknown/error states.
- No visual/input regressions in compact, expanded, portrait, landscape, locked or OSK-visible modes.

---

## 9. WORKSTREAM G — APP DRAWER, HOME DESKTOP AND OVERALL RESPONSIVENESS

Known source starting points:

- `pwa/nuxel-home/js/launcher.js`
- `pwa/nuxel-home/js/apps.js`
- `pwa/nuxel-home/js/desktop-layout.js`
- `pwa/nuxel-home/js/layout-model.js`
- `pwa/nuxel-home/js/widgets.js`
- `pwa/nuxel-home/js/gestures.js`
- `pwa/nuxel-home/js/navigation.js`
- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/css/style.css`
- current shared app registry and status provider.

### 9.1 Preserve existing launcher performance work

The supplied `launcher.js` already:

- caches the drawer container (`drawerList`);
- stores `_drawerSignature` and avoids rebuilding when app registry data has not changed;
- builds the drawer once and opens/closes by changing state/classes;
- avoids reparsing approximately 30 tiles and image nodes on every open (older measured cost 39–57 ms);
- uses stable node identity to avoid destroying decoded icons;
- has a 250 ms opening-gesture settle guard so the opening swipe is not reinterpreted as drawer scrolling;
- keeps dock entries out of the drawer.

Preserve and extend these optimizations. Do not replace the drawer cache with `innerHTML` on every open or invalidate the signature on unrelated status updates.

### 9.2 Profile the actual slow path

Measure drawer gesture → visible state → first paint, DOM nodes touched, images decoded, JS time, forced style/layout, long tasks, scroll frame time, pointer event frequency, bridge requests, icon registry calls, widget rendering and layout persistence. Determine whether the bottleneck is WebKit main-thread JS, image decode, CSS paint, compositor capture/pan, provider polling or a combination.

### 9.3 Drawer requirements

- Open/close begins immediately and remains smooth under touch.
- Build/cache app tile nodes only when the app registry actually changes (install/remove/rename/icon edit/category change).
- Use one canonical app snapshot and one signature per registry revision; do not run repeated filtering/sorting/serialization during animation.
- Cache icon rendering and image decode. Lazy-load offscreen icons if the catalogue is large; preserve correct icon state and avoid flashes when scrolling.
- Keep search/category filtering responsive. Debounce text input only enough to avoid redundant renders; do not make taps feel delayed.
- Use stable IDs and delegated event handlers rather than rebinding handlers to every node on every render.
- Avoid rendering hidden widgets underneath the drawer unless the design requires it.
- Preserve drag/drop, long press, page assignment, folders, dock exclusion, settings and scroll restoration.
- On close, return the user to their prior desktop scroll/page position.

### 9.4 Home desktop and global responsiveness

Audit and fix:
- repeated full desktop render from unrelated status or app registry updates;
- redundant widget rendering on every drawer transition;
- duplicate `requestAnimationFrame` or timers;
- expensive CSS filters, shadows, blur or animated layout on the lockscreen/Home;
- image decode and large PNG scaling;
- pointer handlers that trigger synchronous layout reads/writes;
- event listeners registered more than once after app resume/rotation;
- repeated bridge API/status calls from statusbar, QS, lockscreen and system monitor;
- stale timers continuing while an overlay/app is foreground or screen is off;
- layout thrash from dynamic viewport/orientation/safe-area updates;
- app launch/focus delays unrelated to rendering.

Use one normalized state source/event fan-out for status when possible. Do not add yet another polling timer. Reuse existing bridge caches and visibility-aware polling.

### 9.5 Tests

- cold and warm drawer open/close;
- repeated 20× open/close;
- fast scrolling through all installed apps;
- drawer search while opening/closing;
- install/remove/rename app while drawer cache is alive;
- app icons loaded/error fallback;
- drag app to desktop, folder operations and page switching;
- Quick Settings open during/after drawer gestures;
- rotation and display resize;
- Home hidden behind native app, then resumed;
- screen off/wake while drawer state exists.

No touch regression, lost pointer capture, duplicate event handling or unbounded DOM growth.

---

## 10. WORKSTREAM H — 30 FPS FRAME PACING AND TRUE VSYNC

Known source starting points:

- `tools/s10plus/a67/nuxel-wl-fb.c`
- `services/nuxel-s10/systemd/nuxel-wl-fb.service.d/15-idle-fps.conf`
- `services/nuxel-session/systemd/nuxel-wl-fb.service`
- display/panel runtime probes and kernel source/config.

### 10.1 What 30 FPS means here

The C presenter currently defaults `fps_target` to 30 if no environment override is applied, but the S10+ systemd drop-in currently sets `NUXEL_TARGET_FPS=20`. The existing adaptive idle policy drops to 8 FPS after 500 ms, 3 FPS after 2 s and 1 FPS after 6 s without visual change. Screen-off stops capture/render work. Preserve those idle and screen-off behaviours.

30 FPS is the requested active target (one present every two refresh intervals if the panel is truly operating at 60 Hz). It is a higher output cadence than 20 FPS, not automatically a CPU-performance improvement. The work must make the phone feel smoother while measuring the increased active rendering/presenter cost and thermal/battery impact honestly.

### 10.2 Distinguish target FPS from actual VSync

- Inspect the actual running kernel's fbdev/panel driver, framebuffer ioctls, sysfs and vendor display interfaces for a supported VSync/vblank wait or timestamp mechanism.
- The supplied `nuxel-wl-fb.c` contains `FBIOPAN_DISPLAY` commit logic and pacing via monotonic clock/poll; the source search did not find an existing `FBIO_WAITFORVSYNC` implementation. Verify the current branch/runtime independently.
- A `FBIOPAN_DISPLAY` return proves that the ioctl completed; it is not automatically a precise vblank/presentation timestamp.
- `wl_display`/screencopy completion is not automatically the same as physical panel VSync.
- If the driver exposes a supported reliable vsync/vblank facility, implement it in a non-blocking/event-aware manner with timeouts and retain a safe timed fallback.
- If no real VSync mechanism is exposed, implement an accurate 30 FPS deadline pacer aligned to measured display cadence where possible, and report it as **30 FPS frame pacing, VSync unavailable/unverified**. Do not claim true VSync.
- Do not add an unsupported ioctl guessed from another SoC; confirm header/driver implementation before use.

### 10.3 Required implementation

1. Make the active target 30 FPS via the canonical systemd configuration only after baseline and A/B tests. Do not leave conflicting environment overrides in multiple unit drop-ins.
2. Preserve a configurable target with validation and documented safe range. Reject zero, malformed or extreme values.
3. Keep adaptive idle backoff 8/3/1 and zero screen-off capture. Do not poll faster while static.
4. Use monotonic deadlines and account for work already consumed in the frame. Avoid drift from `sleep(period)` after each frame; calculate absolute deadlines or a robust phase-locked schedule.
5. Keep the poll on the Wayland socket/control channels so changed content and screen-off/wake requests are processed immediately. Do not reintroduce a long `nanosleep` wake delay.
6. Avoid unbounded in-flight screencopy requests or frame queues. Maintain one current capture/present lifecycle unless code evidence supports otherwise.
7. Record frame interval p50/p95/p99, present cadence, `fps_1s`, `capture_avg_ms`, `compare_avg_ms`, `blit_avg_ms`, `pan_avg_ms`, skipped presents, pan failures, input response, CPU, temperature and battery current.
8. Test 30 FPS for sustained 10–15 minute workloads. If p95 frame completion misses the 33.3 ms budget, thermal throttling appears, pan failures increase or touch becomes worse, identify the bottleneck and fix it; do not blindly force the cap.
9. Do not attempt 60 FPS as part of this mission. Do not change the kernel display driver or enable DRM/KMS.
10. Keep the single `/dev/fb0` owner and `FBIOPAN_DISPLAY` after each changed frame. Do not let the bar, dock, animation player or apps write directly to the framebuffer.

### 10.4 Acceptance

- Active interaction aims for 30 presented updates per second, measured rather than inferred from the configured cap.
- No tearing or visibly uneven cadence in controlled motion tests. If true VSync isn't available, state the exact limitation.
- p95 frame interval should remain within the 33.3 ms target for a workload that is claimed to sustain 30 FPS; provide raw p50/p95/p99.
- No increased panel pan failures; no missed screen-off/wake; no touch latency regression.
- 10–15 minute thermal run does not trigger sustained throttling or unacceptable power drain relative to the 20 FPS baseline. Report measured difference.
- 20 FPS rollback remains a one-command/systemd-config option.

---

## 11. CROSS-SYSTEM PERFORMANCE RULES

Across all workstreams:

1. Use one owner per responsibility: one app registry, one status snapshot owner, one FileChooser portal path, one system topbar owner, one framebuffer owner, one foreground/focus authority.
2. Prefer event-driven state and cache-first UI; poll only where required and only while visible.
3. Never block the compositor, Wayland event loop, GTK main loop or Home JS main thread on slow hardware/DBus/file operations.
4. Use request coalescing and generation tokens to discard stale responses.
5. Batch DOM reads/writes and avoid sync layout after every element change.
6. Keep frame-critical data on the render loop; diagnostics use bounded buffers and sampled logs.
7. Avoid launching a whole file manager or browser process in response to a portal file chooser unless it is a proper portal-backend integration with a correlated request/response.
8. Do not improve a UI metric by lying about state, suppressing failure, dropping user input or turning off security.
9. Keep unsupported provider state as UNKNOWN/UNAVAILABLE, not OFF/ON fabricated.
10. Do not perform broad “disable services” changes without dependency and workload evidence.

---

## 12. TEST MATRIX AND DEFINITION OF DONE

### 12.1 Automated tests

Add/update tests in the existing project test structure. Discover the current conventions first. Include:

- portal D-Bus contract tests, request lifecycle and selected file response;
- GTK/Electron test client integration;
- battery/USB table-driven truth tests;
- Browser menu state, mode persistence, per-WebView User-Agent and navigation-policy tests;
- Firefox environment/launch-wrapper checks;
- global shell chrome single-owner and foreground/lock state tests;
- top gesture reveal/hide direction and pass-through tests;
- QS single-flight provider, timer cleanup, cache-first and stale-response tests;
- drawer cache/signature/node identity/perf regression tests;
- presenter pacing/deadline/idle/screen-off/ownership tests;
- package/release manifest hash consistency and deployment checks.

Run targeted tests, JavaScript syntax checks, Python tests, C builds, static checks and the repo's relevant `make`/CI targets. Report exact pass/fail/skip counts. Never hide existing failures by weakening assertions.

### 12.2 Physical S10+ acceptance checklist

- [ ] Charger-only: battery lightning visible while USB data icon hidden.
- [ ] PC USB data connection: USB icon appears.
- [ ] MTP and USB console states remain correctly represented.
- [ ] Ferdium image attachment opens the chooser; Gallery source works; Files source works; selected image preview is returned.
- [ ] WhatsApp attachment works if installed/runnable.
- [ ] Signal attachment works if installed/runnable.
- [ ] Cancel path returns cleanly to app.
- [ ] Nuxel Browser shows a top-right ⋮ menu.
- [ ] Phone mode sends mobile UA and responsive layout is correct.
- [ ] Desktop mode sends desktop UA and renders desktop site; mode persists after restart.
- [ ] Firefox opens and is touch-usable without clipping; file picker works.
- [ ] Native GTK fullscreen top swipe reveals exactly one canonical Nuxel bar.
- [ ] Flatpak fullscreen top swipe reveals exactly one canonical Nuxel bar.
- [ ] Home shows only the Home DOM bar; no native duplicate.
- [ ] Lock state always wins; no application or topbar can cover/bypass lockscreen.
- [ ] Quick Settings first frame and first tile interaction are responsive; no repeated requests.
- [ ] App drawer opens and scrolls smoothly; cache survives close/reopen.
- [ ] Home desktop gestures/transitions remain correct.
- [ ] Active presentation targets 30 FPS if it passes the thermal and cadence gates; otherwise fallback and blocker are documented.
- [ ] Screen-off stops capture; wake immediately presents correct screen.
- [ ] All existing framebuffer fallback/recovery and boot animation handoff tests pass.

### 12.3 Performance report

Create `REPORT-PWNAGE-96000.md` and `docs/pwnage-96000/PERFORMANCE-RESULTS.md` with:

- initial reproduced failures and root causes;
- files changed and why;
- service/package configuration changes;
- tests and exact results;
- physical-device screenshots/log excerpts (no personal content);
- before/after QS open p50/p95, drawer open p50/p95, touch-to-first-visible-feedback, native app resize/launch, bridge timing and 30 FPS cadence;
- CPU/RSS/temperature/battery impact;
- unsupported/blocked applications and exact evidence;
- rollback steps for each workstream;
- release manifest/hashes and deployed build identity.

Do not invent percentage improvements. Attribute gains only to controlled before/after runs under comparable conditions.

---

## 13. DEPLOYMENT, ROLLBACK AND FINAL REPORT

### 13.1 Deployment

- Use the existing deployment scripts and their target manifests. Do not hand-copy a few changed files while leaving staged release copies stale.
- Deploy small groups in dependency order: portal stack; status icon rule; browser; shell chrome; QS/drawer/Home; presenter 30 FPS config.
- Back up every deployed target before replacement and verify source/destination hashes.
- Do not restart the whole phone or compositor until the needed deployment step requires it and a recovery route is confirmed.
- Check service readiness and D-Bus ownership after restart.
- Keep the active framebuffer backend unchanged.

### 13.2 Rollback

Provide separate rollback for:
- XDG portal config/backend;
- USB/battery indicator JS/API;
- browser PWA/native browser package/settings;
- native topbar/shell chrome;
- Quick Settings/drawer JS/CSS;
- 30 FPS service override.

Rollback must restore a known-good state, not merely disable the new feature. Preserve data/settings where possible. Confirm one framebuffer owner after recovery.

### 13.3 Final completion report

At completion, state every objective as one of:

- `FIXED_AND_PHYSICALLY_VERIFIED`
- `FIXED_HOST_TESTED_PHYSICAL_TEST_PENDING`
- `PARTIALLY_FIXED`
- `BLOCKED_WITH_EVIDENCE`
- `NOT_REPRODUCED`

For any blocked app (e.g. Signal not installed, sandbox unavailable or an app-specific native dialog bypasses portals), give exact process/package/runtime evidence and the test substitute used. Do not claim the app is fixed merely because the portal unit test passes.

**Success means the user can attach a real image in the supported messaging apps, see truthful USB/battery indicators, use real mobile/desktop browser modes, reveal one consistent system top bar over native apps, and operate Home/QS/drawer smoothly with a validated 30 FPS pacing policy—without losing the tested framebuffer graphics fallback or weakening system security.**
