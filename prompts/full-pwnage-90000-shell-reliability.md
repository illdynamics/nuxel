# FULL-PWNAGE-90000 — Nuxel Shell, Boot Cinema, Launcher, Flatpak and Navigation Reliability Megaprompt

> **Execution target:** the current Nuxel repository and the actual supported device(s), with the Samsung Galaxy S10+ (`beyond2lte`, Exynos 9820) treated as the primary phone target unless the checked-out device configuration says otherwise.
>
> **Mission:** completely diagnose, implement, integrate, test and document the thirteen user-visible defects listed in this prompt. Do not merely write a plan, add TODOs, or make superficial CSS changes. Preserve Nuxel's Linux-native architecture, existing service ownership, recovery paths and app state.

---

## 0. Operating contract — read before touching the code

You are executing a substantial Nuxel engineering mission, not generating another proposal. Work from the actual checked-out repository. Read this entire prompt before making changes and use `pwnage-90000.md` as the kickoff checklist.

### 0.1 Establish the real repository state

1. `pwd`, `git status --short --branch`, `git branch --show-current`, `git log -5 --oneline`, and `cat VERSION`.
2. Inspect the current code, not only historical prompt directories or `.bak` copies. Search for all duplicate implementations, old A33/A34/A45 snapshots, generated bundles, packaging copies, manifests and deployment manifests that may ship the same code.
3. Do not overwrite, reset, stash, checkout, clean, or discard pre-existing working-tree changes. Preserve the user's work. Create a task branch only if the current repository workflow expects it and the branch can be created without disturbing user changes.
4. The source archive used to prepare this prompt reported `VERSION=v0.7.7-beta`. Treat that as an audit observation, not as authority over the live checkout. The current checkout's `VERSION`, changelog, manifests and deployment pipeline are authoritative.
5. Record the active target, architecture, kernel, compositor, WebKitGTK/mpv/FFmpeg/systemd versions and display dimensions before device-specific tuning. Do not assume that the host workstation's timings represent the phone.
6. Identify exactly which deployment target is connected. Do not push files to an unrelated phone or VM. Do not flash a kernel, bootloader, recovery, modem, or partition for this userspace mission.

### 0.2 Engineering rules

- First reproduce and measure each failure. Trace the real event/service/surface path, then repair the cause.
- Prefer one source of truth for each owner. Do not add a second launcher lifecycle manager, duplicate statusbar, second navdock, second preload player, redundant Flatpak manager, or competing systemd service.
- Preserve process and window state across screen lock. Locking the display must not equal app termination, relaunch, navigation reset, or launcher reload.
- Keep lockscreen security, input gating, app sandboxing, privilege boundaries and Wayland isolation intact. Do not solve a visual bug by allowing app input through the lockscreen.
- Use monotonic time for latency measurements and deadlines. Use wall time only for human-readable timestamps.
- Do not invent boot, shutdown, startup, decode, render, launch or input timings. Every measured number in `SYSTEMD-GRAPH.md` and the final report must be backed by captured device evidence.
- Keep fallback paths useful. If an optional feature, service or player fails, release the UI safely instead of leaving a black or frozen screen indefinitely.
- Keep diagnostics privacy-safe. Never dump passwords, tokens, private URLs, environment variables wholesale, Wi-Fi credentials, personal notification bodies or private app data into logs or reports.
- Use structured logs with event names, boot/session IDs, app IDs where appropriate, elapsed monotonic milliseconds, and explicit failure reasons. Do not log every frame at a rate that harms performance.
- Do not use `sleep`-based ordering as a substitute for a readiness signal unless a bounded delay is already an intentional hardware workaround with measured justification.
- Maintain a clean separation between presentation state and service/lock state. A toast saying a reboot was accepted is not proof that the next boot has completed.
- Any new C/Wayland component must compile for the target architecture and be installed by the canonical build/package/deploy route. Do not silently modify only the source checkout while leaving the installed binary stale.
- Any JS/CSS/PWA asset change must update service-worker cache versions, asset manifests, deployment hashes and packaging as required by the repository's real release workflow.
- Do not claim a hardware test passed when only a desktop/browser simulation passed. Label host tests, emulator tests and actual phone tests separately.

### 0.3 No dangerous shortcuts

- Do not kill or restart all Flatpak apps to make unlock appear quicker.
- Do not clear all WebKit caches, all Flatpak caches, all user data or all launcher localStorage as a generic fix.
- Do not disable the screen lock, secure input, compositor layer ordering, app sandbox, or permission manager.
- Do not turn the preload video into a static image, remove it, or reduce it to a one-second splash to hide the freeze.
- Do not make the launcher wait for every network asset before becoming interactive. Use cached immutable resources, immediate placeholders and asynchronous decode.
- Do not make all Flatpak applications use a new rendering backend without testing each supported app and verifying the target GPU/runtime path.
- Do not send a generic key to an unknown application and then assume the Back event was handled or that the application had no back history.
- Do not add arbitrary high `z-index` values until hit-testing and surface ownership are understood.
- Do not restart the phone repeatedly to collect measurements. Use the live boot's data first; perform at most the minimum controlled restart needed for a requested shutdown capture, and only when the connected target and its recovery route are confirmed.

---

## 1. Repository audit and known starting facts

The source snapshot used during prompt preparation is Nuxel v0.7.7-beta. The following paths and behaviors were found. Confirm each against the current checkout before changing it.

### 1.1 Restart / power menu

- `pwa/nuxel-apps/settings/power-menu.js` contains `showRebootOverlay(label)` and `fire(e, node)`.
- `fire()` displays `.nuxel-reboot-overlay` before issuing the host action. When the bridge returns success, the result label is dynamically set to `e.label + ' accepted'`, which produces **“Restart accepted”**.
- `pwa/nuxel-apps/settings/power-menu.css` styles `.nuxel-reboot-overlay` as a fixed full-screen layer with `z-index:9999` and background `#04121f`.
- `tools/s10plus/a45/nuxel-pwa-host.c` handles `restart` / `poweroff`, writes `/run/nuxel/reboot-request` for restart, then asynchronously asks systemd to reboot. Its acknowledgement is `{ok:true, action:"restart", pending:true}`.
- `services/nuxel-s10/bin/nuxel-wl-fb-hold.sh` holds the last valid framebuffer for a bounded two seconds when the per-boot reboot request exists. It is a separate framebuffer-preservation mechanism and must not be removed without proof that doing so is safe.

**Important:** the report “Restart accepted” is a UI acknowledgement generated before the new boot. A notification, DOM node, screenshot, framebuffer overlay, or transient message from the outgoing session must never become part of the incoming boot's visual state. Determine whether the observed text is in the PWA DOM, an OSD/notification, an old retained framebuffer, a stale WebKit surface, a launcher splash layer, or multiple layers. Do not guess.

### 1.2 Preloading cinema

- Asset: `assets/nuxel-preloading-screen.mp4`; installed path is configured as `/usr/share/nuxel/preload/nuxel-preloading-screen.mp4`.
- The inspected asset is H.264 High, 1080×1920, 24 fps, 144 frames, duration about **6.016 seconds**. Audio is AAC but deliberately disabled in the preloading experience.
- Owner: `services/nuxel-preload-cinema/nuxel-preload-cinema`, a Python controller that starts `/usr/bin/mpv` as a fullscreen Wayland client (`wlshm`). Do not create a second player.
- Configuration: `configs/nuxel/boot/preload-cinema.json`, which has `max_display_ms:12000`, `hard_timeout_ms:15000`, `poll_ms:100`, `final_frame_grace_ms:1500`, and other readiness timings.
- The controller polls mpv IPC properties including `eof-reached` and `playback-time`; it only marks the overlay `covered` after a positive playback time and framebuffer readiness. It exits on EOF after the real lockscreen/panel is ready, otherwise uses a bounded grace/hard-timeout fallback. At the maximum moving-video bound it may explicitly pause mpv and hold the final frame while critical readiness remains pending.
- `services/nuxel-s10/bin/nuxel-session.sh` starts the early controller using `--early`. The systemd fallback service is deliberately not enabled by default to avoid two controllers racing.
- `pwa/nuxel-home/js/app.js` and `pwa/nuxel-home/index.html` own a separate boot-splash / poster-cover lifecycle. The actual cinematic video is the native mpv client, not a WebKit `<video>`.

User-visible failure: approximately one second of motion, then a still image for the rest of the roughly six-second loading interval. The current configured 12-second bound does not explain a one-second freeze by itself. Instrument the full decode → mpv playback clock → frame presentation → framebuffer/compositor path and identify the actual point where motion stops.

### 1.3 Launcher icon rendering

- `pwa/nuxel-home/js/apps.js` generates app icons. In the inspected tree the image markup uses `loading="lazy"`, `fetchpriority="low"`, and `decoding="async"`.
- `pwa/nuxel-home/js/launcher.js` rebuilds the desktop/dock markup through `_renderDock()`, `_renderAppGrid()` and `innerHTML` assignment. Rebuilding can discard loaded image nodes and trigger repeat image/decode work.
- `pwa/nuxel-home/js/app.js::_warmLauncherChrome()` warms the hidden drawer and settings, but the inspected version does not fully warm the actually visible desktop page and dock icon set.
- `pwa/nuxel-home/sw.js` uses `CACHE_VERSION='v77000-pw77001'` in the inspected source. It treats launcher artwork as network-first with `{cache:'no-store'}` before putting successful responses into an icon CacheStorage cache. This is intentionally fresh for mutable artwork, but is a poor fit for immutable/versioned application icon assets and also bypasses WebKit's HTTP cache.

### 1.4 Fullscreen and system navigation

- `pwa/nuxel-home/js/immersive.js` owns PWA immersive gestures. In the inspected code a downward top-edge gesture calls `setStatusVisible(true)`; the module has no explicit compact → expanded Quick Settings state. The bottom edge gesture reveals the nav bar.
- `pwa/nuxel-home/js/status-bar.js::_bindQuickSettingsGesture()` dispatches `gesture:qs` from the status-bar gesture.
- `pwa/nuxel-home/js/qs.js::pull()` currently follows this contract: closed + down opens compact; compact + down expands; compact + up closes; expanded + down closes; expanded + up is a no-op. The user specifically requests that upward swipe closes the shade, including the expanded state. This behavior must change.
- `tools/s10plus/a45/nuxel-statusbar.c` is the native top-edge statusbar for native fullscreen clients. It maps a thin top gesture strip while collapsed, reveals the full bar on downward drag, and currently sets an empty input region for the full bar. That means a second swipe on the revealed full bar may not reach the native statusbar to open Quick Settings.
- `tools/s10plus/a45/nuxel-navdock.c` is the native Back/Home/Recents overlay. In app-foreground mode it maps a thin bottom gesture strip and reveals the controls on an upward swipe. The strip currently has `exclusive_zone=0`, which must be checked against the actual on-screen keyboard layer order and touch routing.
- `pwa/nuxel-home/js/navigation.js` owns the DOM navigation fallback. It uses pointer capture and a 700 ms hold for the long-Back action. It must continue to avoid duplicate tap/long-press activation.
- `tools/s10plus/a45/nuxel-session.sh`, `tools/s10plus/a45/nuxel-shell-chrome.sh`, `nuxel-statusbar.c`, `nuxel-navdock.c`, and the compositor/foreign-toplevel helpers jointly own native shell chrome. Preserve the single-owner architecture.

### 1.5 Back navigation behavior

- `pwa/nuxel-home/js/app.js::back()` handles Home overlays, Quick Settings, Recents, folder sheets, drawer, and keyboard before the app surface.
- For same-origin PWA frames it uses `history.length` relative to `frame.__nuxelNavBase`, then tries generic selectors such as `[data-action="back"]`, `[data-nav="back"]` and `.settings-back`, then returns Home.
- For native/Flatpak apps it calls `POST /api/v1/apps/back`.
- `services/nuxel-bridge/src/api.py::_native_back_action()` identifies the active native toplevel. The inspected version sends Alt+Left only to a small allowlist (Firefox, Stremio, etc.), Escape to VLC, uses a special browser-state FIFO for browser cases, and reports `at_root:true` immediately for many other native apps.
- That `at_root:true` fallback is not proof that the app has no internal back step. It can make an ordinary Flatpak app minimize when Back should first navigate inside it.
- Long-Back is separately wired to `terminateForeground()` / foreground close and must remain a deliberate, distinct action. A short Back must never become a force-kill.

The source grep did not find a literal `GTP+` / `GPT+` code name in the static PWA tree. **Do not silently assume what this label means.** Search the live app registry and installed Flatpak inventory for the user-referenced app, resolve its exact desktop ID and display name, and include it in the Back regression matrix. If it is absent from the target, document that fact and still implement the generic Flatpak contract.

---

## 2. Mission goals and acceptance summary

Implement all items below as one coherent shell reliability mission.

| ID | Required outcome | Pass condition |
|---|---|---|
| P90-01 | No stale “Restart accepted” during next boot | A newly booted session displays only the preload video/normal boot UI; no outgoing-session power-menu result, toast or overlay survives. |
| P90-02 | Full moving preload video | The full 6.016 s asset visibly advances through its moving frames at expected cadence; no freeze after the first second. |
| P90-03 | Immediate desktop icons | First unlock draws all visible desktop and dock icons without waiting for a later repaint or network fetch. |
| P90-04 | Flatpak surfaces survive lock/unlock | Existing app processes/windows remain alive and return visually intact without app restart or full reinitialization. |
| P90-05 | Faster Flatpak startup | Time-to-first-visible-frame improves measurably without weakening sandboxing or causing regressions. |
| P90-06 | No blue rectangle after Reload Launcher | Launcher reload completes without a stale power-menu/boot layer or dark blue top rectangle. |
| P90-07 | Drawer always tappable after Back | One short Back from an app reliably returns to Home; drawer can open immediately with no invisible input blocker. |
| P90-08 | Fullscreen edge zones work | Collapsed top and bottom edge strips remain touchable for their gestures in PWA and native fullscreen apps. |
| P90-09 | Two-stage top pull | First downward pull reveals compact bar; second downward pull opens expanded Quick Settings. |
| P90-10 | Upward swipe dismisses | Swipe up dismisses compact or expanded top shade. No extra downward pull required to close. |
| P90-11 | Bottom gesture works with keyboard | Upward swipe from the physical bottom edge reveals the three navigation buttons while the OSK is visible. |
| P90-12 | Real systemd performance report | Repository-root `SYSTEMD-GRAPH.md` contains measured boot timings and, when available, a measured shutdown timeline; no fabricated timings. |
| P90-13 | Back navigates app-first | PWA and native/Flatpak apps use internal navigation first; only a confirmed app-root state backgrounds to Home. Long-Back remains the separate close/terminate action. |

Do not mark the mission complete while any P90 item is merely “implemented” but not tested at the appropriate layer.

---

## 3. P90-01 — Restart acknowledgement and clean next-boot presentation

### 3.1 Reproduce and locate the leaked message

1. Capture a short video or timestamped screenshots of a normal Restart sequence, from tap through the first 10 seconds of the next boot.
2. Inspect the outgoing power-menu document while the request is pending. Record whether `#menu-result`, `.nuxel-reboot-overlay`, or an OSD/notification surface is visible and when it is removed.
3. Capture the initial boot surfaces and their owners: framebuffer, `nuxel-wl-fb`, mpv preload client, WebKit Home window, native statusbar, dock, OSD and any retained top-level surface.
4. Check `/run/nuxel/reboot-request` semantics, whether it is fresh per boot, and whether any service reads it after the reboot has begun. Never use a prior boot's success status as current boot state.
5. Inspect `nuxel-wl-fb-hold.sh` and systemd ordering. Confirm the 2-second bounded hold is the intended old-frame preservation mechanism, and identify if that last frame contains the accepted message.
6. Search the notification history, notification daemon startup, OSD queue, PWA service-worker/localStorage/sessionStorage and WebKit host state for any persistence path that can restore the message.

### 3.2 Required implementation

- Treat restart as a two-stage lifecycle:
  - **Request accepted / pending** belongs exclusively to the outgoing session.
  - **Boot completed** is a new session event and may only be reported after fresh boot readiness evidence. Do not relabel request acceptance as successful reboot completion.
- The power-menu status node must be ephemeral and cleared on all normal exit paths: action failure, menu close, host disconnect, page hide/unload and process restart. The fullscreen overlay must be destroyed/hidden when the outgoing page is not the active visible session; it must never be persisted as a notification or cached UI state.
- The new boot must start from a clean visual state. No previous session's DOM, toast, overlay, message, framebuffer capture or notification should be intentionally redrawn over the new preload cinema.
- If a reboot overlay is required during shutdown, keep it owned by the outgoing power-menu surface only. The boot cinema must have a clear surface/layer ownership and must be mapped above the retained framebuffer while it is playing.
- If a per-boot marker is needed, use `/run` and boot-ID validation. Never reuse a stale marker from `/var/lib` without comparing it to the current boot ID/time. Remove or rotate the restart request marker at the earliest safe new-boot stage after the framebuffer hold no longer needs it.
- Keep the bounded framebuffer-hold safety behavior unless actual measurements establish a safe replacement. Do not remove the last valid frame simply to hide a text leak.
- If the accepted string is still visible because the power menu or OSD is a separate native toplevel, explicitly dismiss/close that old surface at the correct transition boundary. Do not cover it with an arbitrary opaque rectangle.
- Do not create a boot notification named “Restart accepted”. If a new notification is desired, it must say that the reboot completed and be generated only after current-boot readiness is confirmed; default behavior should be no reboot toast at all.

### 3.3 Tests

- Unit test that a successful pending restart response is never written to persistent notifications/history.
- Test offline/failed/refused restart still shows a useful error and does not hide the UI or request reboot.
- Integration test the outgoing `pending=true` flow and prove the result node is not restored after reloading or reconstructing Home.
- Hardware reboot test: first displayed preload frame contains no old menu/status/OSD pixels. Keep timestamped evidence before/after the transition.
- Test poweroff path separately; it must not leave a persistent notification either.

---

## 4. P90-02 — Repair the six-second preload video freeze

### 4.1 Instrument before changing player options

The asset is 6.016 seconds, 24 fps and 144 frames. A 1-second motion window followed by a five-second freeze is not explained by the configured 12-second display bound. Find where time stops advancing.

Capture all of the following during an actual phone boot:

- SHA-256, byte length, container duration, frame count, video codec/profile, coded/display dimensions, pixel format, average and real frame rate, time base and stream start time of the **installed** asset; compare to source `assets/nuxel-preloading-screen.mp4`.
- mpv version, FFmpeg libraries, video output, selected decoder, hwdec setting and the exact argv/environment for the single player process.
- Controller monotonic timestamps for `player_spawn`, `file_loaded`, `playback_started`, first decoded/presented frame, playback clock samples, EOF, pause/unpause, readiness and exit.
- mpv IPC properties at a low sampling rate (e.g. 4–10 Hz during this short diagnostic): `time-pos`, `playback-time`, `eof-reached`, `pause`, `seeking`, `paused-for-cache` if supported, `estimated-vf-fps`, `drop-frame-count`, and `vo-drop-frame-count` where available. Query supported properties rather than assuming all mpv versions expose them.
- mpv log with frame/decoder errors and Wayland output errors. Rotate/bound the log; do not write unbounded debug output to flash storage.
- A device-side capture that can distinguish video frame changes from a frozen compositor/framebuffer. Use frame hashes or sampled screenshots only at measured intervals; do not mistake a still section intentionally authored in the MP4 for a decoder freeze.
- Confirm the installed asset itself really contains moving frames during seconds 1–5. Compare decoded frame hashes/visual samples from the source asset and installed asset.

### 4.2 Identify likely failure classes explicitly

Test and eliminate each before choosing a fix:

1. Incorrect or stale installed MP4 / wrong copy / mismatched hash.
2. Wrong stream duration/time base or an incorrect controller duration parser.
3. mpv reaching EOF early due an incorrect input path, playlist entry, `--length`, `--end`, seek, loop or environment override.
4. Controller or another actor setting `pause=true` unexpectedly.
5. `--keep-open=yes` holding the last decoded frame while the controller believes playback continues.
6. The controller starting more than one mpv process or two early/fallback controllers racing on the same Wayland display/socket.
7. IPC socket collision or stale socket/state receipt causing the controller to monitor the wrong player.
8. Software decode/Wayland `wlshm`/framebuffer contention, dropped frames or a stuck Wayland buffer release.
9. Frame clock advances but the compositor/framebuffer is not presenting new buffers.
10. Video continues but the preloading cover/poster layer is above mpv and masks the moving frames.
11. The video is intentionally static/black/faded in its last authored frames. Confirm rather than trying to “fix” content that is already static.

### 4.3 Required implementation

- Keep exactly one preload player owner: `nuxel-preload-cinema`. Do not re-enable the fallback systemd service if doing so introduces a second controller race. The early session controller and any manual fallback must share a unique owner lock, pid identity, boot ID and IPC endpoint.
- Keep WebKit media out of this path unless the current multimedia stack is proven healthy and the migration is deliberately justified. The inspected system uses mpv because the WebKit multimedia path was previously unreliable.
- Preserve the real lockscreen and display readiness gates. The splash can finish playing while input readiness is pending; do not expose unlocked app input early.
- Do not use readiness as a reason to pause the animation after one second. The intended moving interval is the entire asset, about 6.016 seconds, unless the panel must be turned off or a documented critical failure requires the bounded fail-open path.
- Correct the precise cause: asset packaging, mpv args, duplicate owner, pause command, IPC state, compositor buffer presentation, overlay z-order, or decode performance as evidence dictates.
- If performance is inadequate, test software decode and available hardware decode as separate configurations. Do not enable hardware decode by guesswork; a broken decoder that appears faster but freezes is a regression.
- Ensure video timing is based on monotonic time/actual EOF rather than a wall-clock timer that can pause playback. Keep a hard fail-open timeout so boot can never hang forever.
- The controller must log a concise structured receipt including asset hash, decoded duration, expected frames, player PID, video output, first frame time, EOF time, whether pause was requested, how long the final frame was held, readiness and final stop reason.
- Add a watchdog for a stalled `time-pos`/frame counter. It must distinguish a deliberate static portion from a real decoder or presentation stall. If playback is stalled, make a controlled one-time recovery attempt (restart only the player instance after verifying owner identity); if recovery fails, reveal the actual lockscreen safely and record why.
- The final frame may be held briefly after EOF only as configured, while presentation readiness is waiting. Do not freeze the animation early just because touch input readiness is late.
- Preserve audio-off behavior.

### 4.4 Acceptance tests

- Offline unit tests: media metadata/parser, single-owner locking, IPC time progression, EOF handling, pause watchdog, stale socket recovery, missing asset fallback, and readiness failure.
- A host integration test with a fake mpv process/IPC server that simulates normal 6.016 s playback, unexpected 1 s pause, early EOF, never-EOF, dead IPC and controller restart.
- Actual S10+ hardware test: visually confirm motion throughout the clip. Capture at least the 0s, 1s, 2s, 3s, 4s and 5s moments; report actual measured playback clock and whether each frame changed. A video that plays only its first second and then holds the rest fails.
- Ensure the preload still releases to the lockscreen even when mpv is missing, corrupt, slow or crashes.

---

## 5. P90-03 — Instant desktop and dock icons on unlock

### 5.1 Required visual behavior

The desktop must not show empty icon wells while its image files are fetched or decoded. Every visible app tile must paint a correct icon or a deliberate stable fallback from the first visible desktop frame. Do not make unlock wait for remote assets.

### 5.2 Investigate and implement

1. Record first unlock timings: lockscreen fade start/end, Home desktop first paint, app-grid DOM ready, icon image request start/end, image decode completion and first correct icon paint.
2. Compare cold boot, warm boot, first unlock, second unlock and re-lock/unlock. Separate missing network bytes from repeated DOM construction and image decode work.
3. Separate immutable/versioned built-in app icons from mutable owner artwork, downloaded thumbnails and user-customized icons.
4. Create a canonical icon manifest containing known app ID → local icon URL, expected version/hash, fallback glyph/color and whether the icon is immutable or mutable. Use only verified repository paths; avoid synthesizing arbitrary URLs.
5. For immutable app icons, use cache-first/versioned caching or install-time precache. Do not force a network fetch with `cache:'no-store'` every time a known immutable icon is requested. A version change must invalidate the correct icon cache. Keep mutable artwork's freshness policy separate.
6. Precache the icons of the current primary desktop and fixed dock as critical Home assets. Warm other drawer icons asynchronously after first visible paint. Keep preloading bounded on memory-limited hardware.
7. Use `loading="eager"` and an appropriate high/auto fetch priority for icons above the fold; keep below-fold drawer icons lazy. Do not mark every app image high priority and starve the lockscreen, fonts or essential scripts.
8. Decode visible icons in a bounded idle/background task using `img.decode()` or an equivalent supported cache path. Do not synchronously decode 40 icons on the UI thread. Prioritize dock and current desktop page, then the next desktop/drawer.
9. Keep stable DOM image nodes or reconcile keyed nodes instead of rebuilding them with `innerHTML` on every unlock, status refresh, page show or app state transition. If a render is necessary, retain image elements with the same source/identity and preserve completed decode state.
10. Render a correct fallback icon immediately while image decoding is pending; replace it without layout shift after decode. The fallback must not be a blank/transparent image or the wrong app's icon.
11. Do not trigger `launcher._renderAll()` simply because the lockscreen disappeared if the existing desktop DOM is already correct. Refresh the registry in the background and reconcile only real differences.
12. Keep service worker lifecycle non-blocking: if a new SW is installing/waiting, it must not strand the current desktop or delete the current usable icon cache before the new version is ready.

### 5.3 Tests

- Unit test that visible desktop/dock icons use the correct priority and fallback, and that hidden drawer images remain bounded/lazy.
- Test current-page, dock, folder, drawer and alternate-desktop icons with offline/cold-cache conditions.
- Lock/unlock loop test at least ten times; prove zero missing/blank icons after first paint and no unnecessary repeated image network requests or node replacement.
- Verify icons remain correct after an app registry version change and a custom icon update; do not regress mutable artwork freshness.
- Measure first correct icon paint and include before/after numbers in the final report.

---

## 6. P90-04 — Preserve Flatpak apps and their rendered surfaces across lock/unlock

### 6.1 Establish what “redraw” means

The phrase “redraw” may refer to one of several different failures. Instrument it, do not assume it means relaunch:

- Did the Flatpak PID change?
- Did the systemd transient app unit stop/start?
- Did the Wayland toplevel disappear/unmap and map again?
- Did the app's surface/buffer become invalid or release its last buffer?
- Did the compositor repaint a retained buffer after lockscreen removal?
- Did the app receive a visibility/state event that triggered its own expensive screen reconstruction?
- Did the app remain alive but the UI flash black/blank until its first new frame?
- Is this only one runtime/app (e.g. GTP+ as identified from the real installed registry), or all Flatpaks?

Capture app ID, PID, process start time, systemd unit, foreign-toplevel handle, mapped/minimized state and first-frame/repaint timestamps before lock, during lock and after unlock. Use process start time as well as PID to guard against PID reuse.

### 6.2 Required behavior

- Locking the phone must protect the screen with the lockscreen/secure overlay, not shut down, terminate, restart, reload, or reset background apps.
- Keep native Flatpak processes and their existing Wayland toplevels alive when locking/unlocking. No `flatpak run` should be triggered by unlock for an app that is already running.
- Preserve the app's current page/document/scroll/form state. No forced refresh, new webview, process restart, `close-foreground`, app-session removal or transient unit recycling as part of lock/unlock.
- Keep the native app surface alive/retained where the compositor and protocol permit. If a panel power-off or driver reset invalidates a hardware buffer, use the least disruptive redraw/repaint request the compositor/app supports; do not fake a preserved surface if it is physically impossible.
- Ensure lockscreen overlay order is above app content while locked, while secure input focus stays on the lockscreen. When unlocking, restore the prior activated app and its z-order before exposing touch input, without displaying stale framebuffer content.
- Do not let background app surfaces intercept touch while Home is in foreground. Restore the app's touch ownership only when it is activated.
- Keep lockscreen notifications and security policy intact.
- Avoid hiding/unmapping app windows if that forces the app or compositor to discard its buffer. If the current lock mechanism unmaps native apps, change that behavior only after the lockscreen remains secure and visible under adversarial test.

### 6.3 Tests

- Keep one Flatpak app open with a nontrivial state (scroll position, open document/view, entered non-sensitive text). Record PID/start time/toplevel handle. Lock and unlock at least ten times.
- Pass: same process instance remains alive, app state remains, no new launch unit, no unexpected window close/map cycle, no app refresh, and no black frame longer than one measured presentation interval unless the device must reacquire a buffer.
- Test at least Firefox, VLC, and every installed Flatpak in the dynamic app registry that can be safely launched. Include the user-referenced GTP+ app if actually installed.
- Verify lockscreen blocks taps/keys to the app throughout the entire locked interval.

---

## 7. P90-05 — Make Flatpak application startup materially faster

### 7.1 Measure a real launch timeline

The inspected `services/nuxel-bridge/src/flatpak_provider.py` launches Flatpaks under a user environment via `systemd-run`, and the bridge's native-app launch path has separate registry probes, transient units and focus polling. The inspected environment also sets `GSK_RENDERER=cairo` and software rendering variables in Flatpak user context. These may be intentional device compatibility choices; do not remove them blindly.

Instrument the complete launch path with `time.monotonic_ns()` or equivalent:

1. App tile tap → JS dispatch.
2. HTTP request creation → bridge receipt.
3. App ID validation / registry resolution.
4. Provider availability and installation check.
5. Environment construction / `systemd-run` request.
6. Flatpak wrapper startup.
7. Bubblewrap / namespace / permission / portal setup.
8. App process exec (record PID/start time).
9. D-Bus activation/portal connection, if relevant.
10. First Wayland surface creation/map.
11. First nonempty/visible frame.
12. Focus/activation confirmation.
13. UI reports app ready.

Report cold-start and warm-start separately, by app ID. Identify whether delay is CPU, flash I/O, disk cache, namespace initialization, D-Bus, portal, app-specific initialization, font/icon discovery, graphics renderer, surface focus, or an arbitrary polling timeout.

### 7.2 Safe performance improvements

- Keep the Flatpak provider as the lifecycle authority. Do not duplicate app launch directly in the PWA, add a second daemon, or bypass the bridge's validated app ID/argv handling.
- Preserve `flatpak run` security, bubblewrap, seccomp/namespace constraints, app permissions, portals, user identity and filesystem permissions. Do not solve performance by launching as root or adding broad `--filesystem=host`, `--device=all`, `--share=network` permissions.
- Avoid repeated synchronous `flatpak info/list` subprocesses on the tap path. Cache an evidence-backed installed-app map with a clear invalidation trigger for install/update/remove; a stale cache must never authorize an app that is no longer installed.
- Cache discovery metadata, desktop file resolution, icon lookup and known runtime information at a safe scope. Do not cache dynamic authorization decisions or user session secrets.
- Check whether `systemd-run --wait --pipe` is holding the bridge's synchronous response or whether launch is correctly asynchronous. Return a launch job/session ID promptly and publish progress without blocking Home.
- Use a stable, bounded asynchronous startup pipeline with per-app state (`requested`, `starting`, `mapped`, `ready`, `failed`) and timeout/retry rules. Prevent duplicate launch taps from starting multiple instances unless that app explicitly supports multiple instances.
- Start the app as the correct user with the correct `/run/user/...` and D-Bus/Wayland environment. Do not hardcode UID 1000 if the repository supports a different user on another device; resolve via canonical account config.
- Test renderer profiles on the real S10+ GPU/runtime. Only change `LIBGL_ALWAYS_SOFTWARE`, `GALLIUM_DRIVER`, `MESA_LOADER_DRIVER_OVERRIDE`, `GSK_RENDERER` or `GDK_BACKEND` when target-specific measurements prove a faster stable configuration and the app still renders correctly. Retain a tested safe fallback and expose diagnostic reason.
- If Flatpak runtime/filesystem caches can be safely warmed after login, warm metadata only and keep it CPU/I/O bounded. Do not prelaunch all apps or hold every runtime in RAM.
- Reduce arbitrary fixed focus polling (e.g. repeated 250 ms checks) only when the compositor can provide an event or a shorter adaptive backoff. Keep a robust final timeout and a visible error for an app that never creates a surface.
- Separate “bridge accepted launch” from “app ready”. Do not claim an app is ready until a real toplevel and first frame exist.
- Persist launch timing summaries in a bounded diagnostics log with private app arguments and paths redacted.

### 7.3 Acceptance targets

- Establish measured baseline for 3 representative Flatpaks: browser, media app and one GTK/tool app. Include cold and warm values for request-to-process, process-to-map and request-to-first-frame.
- Improve median request-to-first-frame by at least 25% for at least two of the baseline apps **or** clearly document the actual irreducible bottleneck and demonstrate the maximum safe measured improvement. Do not optimize one app by making others slower.
- No sandbox regression, no root app process, no broad permission grants, no duplicate process on repeated tap, no app-start freeze in Home.
- All timeout/failure conditions recover to Home and produce useful, nonmodal diagnostic feedback.

---

## 8. P90-06 — Remove the blue rectangle after “Reload launcher”

### 8.1 Reproduce and identify the exact layer

- Trigger Reload launcher from the real Settings/Home control at least ten times, including while a Flatpak app was previously foreground, after a lock/unlock, and after closing Quick Settings.
- Capture the screen and inspect element/surface rectangles and stacking order before, during and after reload.
- Investigate `#boot-splash`, `#preload-cover`, lockscreen background, power-menu `.nuxel-reboot-overlay`, statusbar, navdock, OSD/toast, stale iframe, and any top-level Wayland layer surface. The inspected CSS uses dark navy shades (including `#04121f` in the reboot/lock family and a separate boot-splash color); compare actual sampled pixels and computed styles rather than guessing from color resemblance.
- Identify whether the rectangle is an element, a pseudo-element, an unmapped buffer, a layer-shell client, a stale cached screenshot or the WebKit view's background during load.

### 8.2 Required fix

- Define one explicit launcher reload lifecycle: mark reload in progress; synchronously dismiss only transient overlays/toasts that belong to the old document; keep the lock state and security gate authoritative; keep the valid background/wallpaper; restore the desktop only when the new document has completed its real readiness milestones.
- Ensure no reboot overlay, power-menu status, QS panel, notification shade or splash poster is inadvertently preserved across an ordinary launcher reload.
- Ensure the `#boot-splash`/`#preload-cover` only appears in their intentional boot contexts. An ordinary user-requested launcher reload must not replay the OS boot cinema or expose a stale placeholder rectangle.
- Ensure old hidden iframe/surface nodes are destroyed or made noninteractive without leaving an opaque background/input layer. Release pointer capture and stale gesture state associated with the old document.
- Do not hard-code `display:none` on a broad topbar/container to hide the rectangle. Preserve the actual statusbar and edge gesture area.
- Keep wallpaper and icon cache ready during reload; avoid a visible blank blue interim frame. Use a correct fallback/background drawn immediately.

### 8.3 Tests

- Regression test: reload launcher from Settings, from desktop, after Quick Settings, after app exit and after relock/unlock.
- Assert no stale reboot element, stale splash, opaque unexpected top rectangle, duplicate statusbar, duplicate dock or pointer-intercepting transparent overlay remains after readiness.
- Confirm the topbar/dock are correct and usable after reload, and that keyboard/input remain functional.

---

## 9. P90-07 — Fix the invisible overlay / drawer blocked after one Back press

### 9.1 Reproduce in a state matrix

Test short Back once from:

- A native Flatpak application.
- A native GTK application.
- A PWA with internal history.
- A PWA at its root.
- A PWA that uses an SPA router.
- Fullscreen game/media app.
- App with the OSK open.
- App after Quick Settings or Recents was recently open.

After every short Back, immediately tap the app-drawer control or perform the drawer-opening gesture. Also test a fresh gesture after a `pointercancel`, `lostpointercapture`, `blur`, navigation, iframe removal and keyboard close.

### 9.2 Inspect likely interceptors

- Stale `appSession` state/frame pointer.
- Old iframe or native toplevel still activated above Home.
- `pointer-events` on an invisible iframe, preload cover, lock overlay, Quick Settings panel, Recents surface or toast.
- Transparent overlay with a larger-than-visible bounding rectangle.
- CSS `opacity:0` while `pointer-events:auto`.
- `visibility`, `inert`, `hidden`, transform/animation state not synchronized.
- Active pointer capture not released when the app surface is hidden/removed.
- Incomplete pointer/touch gesture state after event cancellation.
- DOM drawer present but covered by a native surface or layer-shell strip.
- Async `back()` or `home()` response race that restores an old overlay after Home has already been shown.

### 9.3 Required implementation

- Add a single `returnToHome`/foreground-exit transition that runs only after the app-first Back contract has confirmed the app is at root. It must atomically reconcile `appSession`, active app state, iframe/native top-level state, overlays, keyboard, immersive flags, nav dock visibility, desktop hit-testing and Recents.
- On exit, clear timers, pending gesture starts, pointer capture, active drags, pending long-presses, pointer IDs, touch fallback tracking and event listeners owned by the departing app surface. Use a generation/session token so late async callbacks from the old app cannot show stale UI over Home.
- Any overlay not visible must be noninteractive (`hidden`/`inert`/`pointer-events:none` plus correct lifecycle), not merely transparent or translated offscreen.
- Avoid removing the shared PWA host itself when only the app iframe should be backgrounded. But the foreground iframe must not intercept desktop input after Home transition.
- Make drawer open state idempotent and independent of the previous app's pointer event chain. A new fresh tap/swipe after Home is shown must work immediately.
- Do not rely on the user's workaround (long-Back kill) to clear invisible state.
- Preserve native app processes when returning Home; short Back at root should background/minimize, not kill.

### 9.4 Tests

- Add a regression test for the exact report: open an app → tap Back once at root → immediately open app drawer → select an app. Repeat at least 50 cycles in automated browser tests if feasible.
- Add `pointercancel`, `lostpointercapture`, keyboard-open, app-iframe-close and rapid Back/Home/drawer race tests.
- Assert after Home transition that only intended Home surfaces receive pointer/touch input and all hidden surfaces have `pointer-events:none` or equivalent input exclusion.
- Long-Back remains the only deliberate close/terminate gesture and does not double-fire short Back.

---

## 10. P90-08 / P90-09 / P90-10 — One coherent topbar + Quick Settings gesture state machine

Do not fix these three requirements independently. The current PWA `immersive.js`, `status-bar.js`, `qs.js`, native `nuxel-statusbar.c`, and compositor layer-shell surfaces currently overlap responsibilities. Implement a single behavioral contract with separate input/rendering adapters for PWA and native clients.

### 10.1 Required state machine

For fullscreen/immersive apps:

```text
HIDDEN (only a transparent/touchable top-edge gesture strip)
  -- downward swipe --> COMPACT_BAR
COMPACT_BAR
  -- downward swipe --> EXPANDED_QUICK_SETTINGS
  -- upward swipe   --> HIDDEN
EXPANDED_QUICK_SETTINGS
  -- upward swipe   --> HIDDEN
  -- tap outside / Back --> follow the standard shade-close behavior
```

For non-immersive Home/normal app presentation:

```text
BAR_VISIBLE
  -- downward pull on bar/top edge --> COMPACT_SHADE
COMPACT_SHADE
  -- downward swipe --> EXPANDED_QUICK_SETTINGS
  -- upward swipe   --> BAR_VISIBLE / CLOSED SHADE
EXPANDED_QUICK_SETTINGS
  -- upward swipe   --> BAR_VISIBLE / CLOSED SHADE
```

The key physical interaction is: **first drag down from the fullscreen top edge reveals the normal top bar; drag down again opens it normally as an expanded shade; swipe up closes the shade/bar.** Do not require a second downward gesture to close it. Upward swipe from the expanded panel must not be swallowed as a no-op.

### 10.2 State machine requirements

- Represent hidden/compact/expanded explicitly, not as a loose combination of unrelated CSS classes and independent timers.
- Keep one authoritative JS state for the Home/PWA surface and one native adapter state for native toplevels; synchronize through a defined bridge/event/IPC contract. Do not let both native C and JS independently toggle the same presentation at the same time.
- Centralize gesture classification: start-zone, direction, minimum distance, diagonal skew, pointer/touch ID, pointer-vs-touch duplicate suppression and cancellation behavior.
- A completed gesture must fire exactly once. If both Pointer Events and Touch Events are reported by WebKit, the two event streams must be de-duplicated by the same gesture ID/source/time window.
- A gesture that starts in the hidden top strip must continue to be recognized after the finger leaves the small strip. Use pointer capture or the native seat touch stream as appropriate.
- Full-screen apps must still receive all non-edge touch input. Do not globally intercept or prevent default for normal app gestures.
- If the first top swipe is short, diagonal, cancelled or started outside the strip, do not reveal the bar.
- A visible bar/panel may auto-hide only as an intentional separate policy. Do not let an auto-hide timer race with the second pull-down or upward dismiss; cancel/restart timers on every state transition.
- If Back is tapped while Quick Settings is open, it must close the overlay first and must not also navigate/exit the app in the same tap.
- If the keyboard is active, topbar and nav gestures still work; the gesture must not cause the keyboard to dismiss unless that is the explicit action.
- The lockscreen behavior remains separately controlled. No protected quick setting or app navigation is accessible through these app gestures while locked.

### 10.3 Native statusbar requirements

- `tools/s10plus/a45/nuxel-statusbar.c` must keep a real top input strip alive while visually collapsed. It may not destroy the entire interactive surface if that makes the edge gesture inaccessible.
- After first pull, show the compact statusbar and make only the intended gesture handle area interactive. The second downward pull must reach the native gesture owner and request expanded Quick Settings through the authoritative Home/bridge route.
- The current full-bar path sets an empty input region. Change the input region deliberately: keep a small top gesture handle region (or a dedicated transparent region/surface) while allowing normal content below to behave as specified. Do not make the entire app surface untouchable.
- Upward swipe from compact or expanded state must dismiss according to the state machine. Native C must issue a close request to the same owner, not independently invent a CSS state.
- Keep layer-shell anchors, exclusive zones and z-order correct. Do not make the top strip reserve app content space while collapsed unless required for correct touch routing; do not let the visible expanded panel cover the bottom nav or the keyboard unexpectedly.
- Recover gracefully if the Home host/bridge is absent: a swipe may reveal/dismiss the basic bar locally, but must not leave a dead visible state.

### 10.4 PWA `immersive.js`, `status-bar.js`, `qs.js`

- Refactor `pwa/nuxel-home/js/immersive.js` to issue a first-level reveal and to route the second down swipe to the real Quick Settings controller.
- Ensure `pwa/nuxel-home/js/status-bar.js::_bindQuickSettingsGesture()` is connected for the newly revealed compact bar and not shadowed by a competing `immersive.js` listener.
- Change `pwa/nuxel-home/js/qs.js::pull()` so upward swipe from the expanded shade closes it as required. Remove contradictory comments/tests that say expanded+up is inert.
- Decide and document whether closing expanded QS returns the bar to visible or completely hidden for fullscreen apps. For this task, fullscreen app context closes back to hidden immersive chrome; normal Home context returns to the normal bar/closed shade.
- Use one state-change event so CSS, accessibility state (`aria-expanded`), overlay stack and focus state are updated consistently.
- QS panel scroll gestures remain usable: upward scrolling inside a scrollable expanded details area should scroll content until it reaches its top, then a deliberate upward edge-dismiss can close the overlay. Do not make ordinary vertical scrolling instantly dismiss it from the middle of a list.
- Keep the active app frame input path and top-edge gesture listener attached to same-origin iframes, and make an explicit native IPC path for native apps. Avoid relying on app frame `postMessage` for native windows.

### 10.5 Tests

- Unit-test every state transition and invalid gesture; test pointer/touch duplicate events, pointercancel, multitouch, horizontal skew and repeated swipes.
- Integration-test PWA fullscreen (including app iframe) and native Flatpak fullscreen separately.
- Hardware test: fullscreen native app → downward edge swipe reveals compact bar → second pull-down opens Quick Settings → swipe up closes it → app receives input normally.
- Repeat from PWA fullscreen, keyboard visible, portrait/landscape and with the shade scrolled.
- Test the top gesture while the screen is unlocked and confirm that the lockscreen still blocks it while locked.

---

## 11. P90-11 — Bottom navigation gesture remains reachable with OSK open

### 11.1 Root-cause checks

- Inspect `tools/s10plus/a45/nuxel-navdock.c` layer, anchors, exclusive zone, keyboard interactivity, mapped strip height, input region, touch seat handling and its relation to Stevia OSK.
- Inspect the actual OSK layer-shell surface and whether it reaches the physical bottom edge, overlaps the nav gesture strip, changes output geometry or intercepts touch before the dock client.
- Inspect the PWA `immersive.js` bottom 34 px zone and the native dock's strip (the inspected C code has a mapped strip while app foreground). Confirm which owner receives the real handset touch.

### 11.2 Required behavior

- With the OSK open and an app active, an upward swipe beginning at the lowest reachable physical edge must reveal Back/Home/Recents.
- The keyboard must remain open unless the user explicitly requests a keyboard-dismiss action. Revealing nav is not a focus-clear command.
- The gesture strip must be above/otherwise reachable around the keyboard in the input stack, without painting opaque pixels over the keyboard or app. Prefer a small transparent edge hit target or an explicitly reserved strip, not a duplicated full-height dock.
- Keep the bottom buttons visible only according to existing temporary-reveal policy. They must remain touchable after reveal and return to hidden strip according to the normal timeout/tap behavior.
- Taps inside the keyboard keys must still go to the keyboard. A tap on app content must still go to the app. Only the narrowly defined bottom-edge upward swipe should be captured by the nav owner.
- When a keyboard expands/repositions the viewport, calculate the edge in physical/output coordinates for the native surface and in correct viewport coordinates for the PWA fallback. Avoid using a stale `innerHeight` measured before OSK appearance.
- Support pointer/touch cancellation and device rotation while OSK is visible.

### 11.3 Tests

- Test all three navigation actions with OSK visible. Verify the keyboard remains open after revealing the bar.
- Test normal app input and OSK key input before and after a reveal.
- Repeat with a Flatpak app, PWA app and Home search/text field.

---

## 12. P90-12 — Generate the real systemd boot and shutdown report at `./SYSTEMD-GRAPH.md`

This is a deliverable, not an optional suggestion. Create and commit to the repository worktree a root-level `SYSTEMD-GRAPH.md` describing the target device's measured boot timeline and shutdown timing where the available journal permits it. Also add a reusable diagnostic collector so the report can be regenerated after future updates.

### 12.1 Important measurement limits

- `systemd-analyze time`, `blame`, `critical-chain` and `plot` are boot-oriented diagnostics. `systemd-analyze plot` emits an SVG with system service startup times; it is not by itself a complete shutdown timeline. Its measurements can also show the most recent activation of a unit, not necessarily every restart cycle. See the systemd manual: <https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html>.
- `systemd-analyze blame` can mislead if read as a pure performance ranking: a unit may be waiting on a dependency, and `Type=simple` units do not expose the same activation-duration data. Do not optimize a unit just because it is at the top of `blame`.
- Shutdown analysis must be derived from shutdown journal events/monotonic timestamps, supported manager timestamps, or a dedicated bounded shutdown recorder. If the previous boot's journal is volatile or missing, say **“shutdown timing not captured on this boot”** and provide the exact safe capture command for the next normal shutdown. Never fabricate a shutdown SVG or claim that a boot plot shows shutdown.

### 12.2 Collect evidence from the actual Nuxel phone

First establish that the target is the Nuxel phone (prefer the connected S10+ session) and not the build host. Capture:

- Collection timestamp/timezone, hostname/device model/board, kernel release, architecture, systemd version, current boot ID, uptime, root filesystem type and whether journal persistence is enabled.
- `systemd-analyze time`.
- `systemd-analyze blame` (retain raw output and a parsed table with caveat).
- `systemd-analyze critical-chain` for default target and relevant Nuxel targets/services (`nuxel-wayland.service`, `nuxel-wl-fb.service`, bridge, web, session/chrome supervisor, lockscreen dependencies, preload-related units, networking only where it gates the UI). Determine actual unit names on the device; do not assume every repository service is installed or enabled.
- `systemd-analyze plot` as raw SVG and keep it in the repo, preferably `diagnostics/systemd/SYSTEMD-BOOT.svg`.
- `systemd-analyze dot` limited to relevant Nuxel/display/session targets if useful, rendered as an additional dependency diagram when Graphviz exists. Avoid a huge unreadable all-system graph.
- Current `systemctl list-units --all`, `systemctl --failed`, and selected `systemctl show` properties including `ActiveState`, `SubState`, `Result`, `ExecMainStartTimestampMonotonic`, `ExecMainExitTimestampMonotonic`, `ActiveEnterTimestampMonotonic`, `InactiveExitTimestampMonotonic`, `TimeoutStartUSec`, `TimeoutStopUSec`, `Before`, `After`, `Wants`, `Requires`, `Conflicts` and `NRestarts` where present. These properties may be missing for inactive/unloaded units; mark them unavailable rather than substituting zero.
- Journal excerpts for the current boot around the Nuxel graphical session startup. Prefer monotonic timestamps and structured JSON where available. Preserve event order and avoid parsing localized strings as the only source of timing truth.
- Optional user-manager (`systemctl --user`) timing if user services materially affect time-to-desktop.

### 12.3 Shutdown capture

1. Inspect `journalctl --list-boots` and `journalctl -b -1` if a prior boot exists.
2. Extract relevant stop/start/shutdown events with monotonic timestamp fields, including “Stopping…”, “Stopped…”, stop timeouts, failed units, SIGTERM/SIGKILL events, unmount/crypt/udev/network teardown and the systemd shutdown handoff. Identify the longest observed stop intervals and distinguish a unit's own stop execution from time waiting on its dependencies.
3. If `systemd-analyze time` on the target reports carried shutdown phases (for example a live-update/kexec environment), include those exact phases as manager-reported data. Do not expect this feature on an ordinary reboot.
4. If the previous boot journal does not exist or the available events cannot reconstruct a reliable timeline, create a bounded, low-write shutdown evidence collector for the next normal reboot only if the existing journald configuration cannot safely provide it. Keep persistent logging privacy-safe and rotate it. Do not change journald from volatile to persistent without documenting storage cost and making the change through Nuxel's configuration/consent process.
5. Never invoke a reboot merely to collect a graph without checking that the device is accessible and the user has an established recovery path. Use a normal user-approved restart only when required. After restart, read the previous boot and update the report.

### 12.4 Files and report structure

Create:

```text
SYSTEMD-GRAPH.md
 diagnostics/systemd/
   SYSTEMD-BOOT.svg
   SYSTEMD-SHUTDOWN.svg        # only when an honest event-derived graph can be built
   boot-systemd-analyze.txt
   boot-blame.txt
   boot-critical-chain.txt
   boot-units.tsv              # sanitized measured fields
   shutdown-journal-summary.txt
   collector-metadata.json     # no secrets or private environment
 tools/diagnostics/nuxel-systemd-graph.py
```

Adapt paths to existing repository conventions if they already provide a better diagnostics directory, but keep the report at exactly `./SYSTEMD-GRAPH.md`.

`SYSTEMD-GRAPH.md` must contain:

1. Device and collection context, actual capture date/time and boot ID (boot ID may be shortened).
2. A large readable boot summary: firmware/bootloader timing if available, kernel, initrd, userspace, graphical/session readiness and measured time-to-Nuxel desktop. Clearly separate platform measurements from Nuxel UI milestones.
3. A service timing table: unit, activation start, finish/elapsed, state/result, dependencies, critical-path membership, and interpretation.
4. The embedded/linkable `SYSTEMD-BOOT.svg` graph and a note about `systemd-analyze plot` limitations.
5. A critical path narrative: what blocks the graphical session/desktop, not just the slowest `blame` entries.
6. A shutdown graph/table with absolute and relative timestamps, unit stop duration where trustworthy, long waits/timeouts and final handoff. If not captured, show an explicit `NOT CAPTURED` section with reason and next capture steps.
7. A shortlist of optimizations ranked by evidence, risk and expected benefit. Do not automatically change boot dependencies to improve a number.
8. Methodology and reproduction commands.
9. Data integrity statement: identify unavailable timestamps and how values were calculated; no zero-filled missing times.
10. Privacy note identifying any redactions.

### 12.5 Collector requirements

- Implement `tools/diagnostics/nuxel-systemd-graph.py` (or the repository's equivalent) with standard library Python where possible; call systemd tools as argv arrays, never shell-evaluate unit names or journal content.
- Provide `--output SYSTEMD-GRAPH.md`, `--assets-dir diagnostics/systemd`, `--boot current|previous`, and `--include-shutdown` options or an equivalent documented CLI.
- Check commands/tools/permissions. On unsupported options or old systemd versions, gracefully omit that data and state why.
- Sanitize host-specific sensitive fields, credentials, environment values and unneeded command lines. Do not export full `systemctl show-environment`.
- Use locale-stable commands for textual output where possible but preserve original raw source artifacts alongside the parsed interpretation.
- Store raw timing data with checksums and collection metadata; do not silently reuse an old graph after a new boot.
- A parser test must use fixture journals with known timestamps, missing events, reordered messages, stop timeouts, repeated starts and absent previous boot.
- Do not derive service duration by subtracting values from different boots or clock domains.

### 12.6 Required execution outcome

Run the collector against the actual target during this mission and generate `./SYSTEMD-GRAPH.md`. If the live phone is not reachable from the execution environment, still add and test the collector plus a clearly marked report skeleton, but say that actual target timings could not be collected. Never substitute the development laptop's boot timings and label them as Nuxel phone timings.

---

## 13. P90-13 — Correct universal Back: in-app navigation first, Home only at app root

This is a core system-navigation contract. Short Back must attempt a real in-app Back operation for the foreground PWA/native/Flatpak app. Only a verified “at root” response may background it to Home. Long-Back remains the separate close/terminate gesture; the Penguin/Home button always invokes Home immediately.

### 13.1 Fix the current false-root behavior

The inspected `services/nuxel-bridge/src/api.py::_native_back_action()` has a small app allowlist and otherwise returns `handled:false, at_root:true` for many non-browser native apps. This incorrectly treats “no adapter” as “no internal navigation”. Replace this with a truthful result model.

The bridge must return a typed result such as:

```json
{
  "success": true,
  "foreground": "desktop.app.Id",
  "status": "handled | at_root | unsupported | pending | failed",
  "handled": true,
  "at_root": false,
  "method": "app-adapter | a11y-action | app-protocol | explicit-shortcut",
  "detail": "optional non-sensitive reason"
}
```

The exact schema may differ, but it must distinguish confirmed root, unsupported app, transient failure and actual handled navigation.

### 13.2 PWA app contract

- Create a documented Nuxel Back API that PWA apps can implement. Provide a shared helper/module so app authors do not invent their own protocol.
- The launcher sends a correlated `nuxel:back-request` message (or an agreed same-origin event) to the active frame and waits for a response indicating `handled`, `at_root`, or `unsupported`. Validate `event.source`, origin and session/request ID.
- For an SPA, the app's router must answer from its real navigation stack. For a normal document/navigation history, use browser history only when the entry is confirmed to belong to the current app session. Never navigate back into `about:blank`, a stale app, the Home document or an external origin accidentally.
- Replace arbitrary selector guessing (`[data-action=back]`, `.settings-back`, etc.) with declared app-level handlers. Existing back buttons can be registered with the helper during migration.
- An app that does not implement internal navigation may explicitly declare `backBehavior:"at-root"`. Lack of a response is **not** the same as at root.
- Add timeouts that return `unsupported`/`failed`, not false `at_root`. Avoid multiple concurrent pending Back requests.
- Keep Quick Settings, overlays, keyboard and launcher drawer as system-level Back targets before the active app receives Back.

### 13.3 Native and Flatpak app contract

- Enumerate the actual foreground toplevel through the existing foreign-toplevel API, including the exact desktop app ID and app-session mapping. Do not infer foreground from an arbitrary first process in a cgroup.
- Build a native back-adapter registry keyed by verified desktop app ID, not display name or a substring. The registry must support at minimum each currently installed Flatpak/native app where an internal Back concept exists.
- For an app with a supported D-Bus/API back operation, use that. For an app exposing an accessible Back action via the desktop accessibility bus, query and invoke the actual action with bounded timeouts. For apps with a well-documented Back shortcut, use an explicit app-specific adapter and report only that the action was sent; do not claim that a history step was confirmed unless the app exposes state.
- Do not send Alt+Left to all Flatpaks indiscriminately. It is appropriate only to apps known to use it. Keep existing confirmed adapters (Firefox, Stremio, VLC Escape, etc.) where device tests prove them correct.
- If a known app has no internal navigation, declare its adapter as `at_root` intentionally. If an app has no adapter and no reliable state API, return `unsupported` and keep it foreground rather than pretending it is at root and unexpectedly backgrounding it. A user-configurable generic fallback shortcut may exist, but must be opt-in and visibly identified as unverified.
- Do not use `xdotool`/X11-only assumptions on Wayland. If using `wtype`/virtual-keyboard injection, validate the protocol is available, the correct client is focused, and the key is restricted to the trusted Nuxel bridge path. A successful key injection only proves delivery, not that the app had a prior page.
- Add an application manifest field for Back capability where appropriate: `back_mode` (e.g. `web-history`, `spa-protocol`, `a11y-action`, `shortcut`, `none`, `unknown`), `back_shortcut`, and optional adapter ID. Validate and document the schema; do not let an installed app supply arbitrary shell strings.
- Implement a reusable adapter interface with `can_go_back()` where possible and `go_back()` returning a typed result. Bound calls and log sanitized app ID/method/result.
- Discover the user-mentioned “GTP+” app from the device's installed Flatpak inventory/registry. Verify exact ID and behavior. If its internal state is navigable, add its adapter and regression test. Do not invent its ID if not installed.

### 13.4 Home transition semantics

- When the app explicitly responds `at_root`, call the same safe Home transition used by the Penguin/Home button: dismiss keyboard according to existing policy, close transient overlays, show desktop 1, minimize/background the native toplevel, reset immersive chrome and make Home touchable.
- Short Back at root must not kill the process. Native Flatpak PID and data remain alive.
- The Home button does not try in-app Back; it goes Home immediately.
- Long-Back remains the dedicated graceful close-foreground request and only uses force termination after the existing explicitly designed safety timeout / policy. Do not accidentally turn a short tap into a long press or double-fire both actions.
- On `unsupported` or transient `failed`, leave the app in foreground and show subtle truthful feedback (e.g. “Back isn't supported in this app”), rather than minimizing it without evidence. Do not endlessly trap the user; document a user-accessible Home action.
- Prevent duplicate Back actions while one is pending; reset the busy flag on success, failure, timeout and rejected HTTP request. Use request IDs and app-session generation to ignore stale responses.

### 13.5 Tests

- PWA: static page with 2 history entries, SPA with 2 internal routes, app root, stale `about:blank` history, app that has no back handler, cross-origin frame, malformed response and timed-out response.
- Native/Flatpak: Firefox, Stremio, VLC and all installed apps with internal back affordance. Test one ordinary GTK/Flatpak screen with no back stack, one navigable settings/file stack, and the live-discovered GTP+ app.
- Verify: first Back changes app view where possible; next Back at app root returns to Home; app process persists; Home button always goes Home; long-Back closes only when held intentionally.
- Security test: an untrusted PWA cannot send fake Back responses for another app/session or request arbitrary key injection.

---

## 14. Cross-cutting diagnostics and observability

Implement a small, documented tracing vocabulary shared by JS, bridge, C shell clients and preload controller. Do not create a general logging framework if one already exists.

Suggested events:

```text
P90_RESTART_REQUESTED / P90_RESTART_ACCEPTED / P90_BOOT_SESSION_STARTED
P90_PRELOAD_PLAYER_STARTED / P90_PRELOAD_FILE_LOADED / P90_PRELOAD_FRAME
P90_PRELOAD_TIMEPOS / P90_PRELOAD_EOF / P90_PRELOAD_STALL / P90_PRELOAD_DONE
P90_HOME_FIRST_PAINT / P90_ICON_REQUEST / P90_ICON_DECODED / P90_ICON_PAINTED
P90_FLATPAK_LAUNCH_STAGE / P90_FLATPAK_WINDOW_MAPPED / P90_FLATPAK_FIRST_FRAME
P90_LOCK_BEGIN / P90_LOCK_SURFACE_COVERED / P90_UNLOCK_BEGIN / P90_UNLOCK_SURFACE_RESTORED
P90_NAV_BACK_REQUEST / P90_NAV_BACK_RESULT / P90_HOME_TRANSITION_BEGIN / P90_HOME_TRANSITION_DONE
P90_TOP_GESTURE / P90_QS_STATE / P90_BOTTOM_GESTURE / P90_EDGE_INPUT_RESULT
P90_OVERLAY_AUDIT / P90_SYSTEMD_GRAPH_COLLECTED
```

Rules:

- Include monotonic timestamp or elapsed ms, boot ID/session generation, app ID where relevant and result. Use a shared correlation ID for a Back or launch request across JS → bridge → native.
- Rate-limit repeating frame events and keep a bounded ring buffer. Avoid per-frame disk writes.
- Diagnostics must not block the UI or video playback. If a logging destination is unavailable, drop diagnostic detail without blocking the owner.
- Provide a `tools/diagnostics` command to collect a short support bundle with redaction. Do not include personal messages, secrets, tokens or private file content.

---

## 15. Test and verification plan — mandatory

### 15.1 Offline / unit layer

Run relevant existing tests first to establish baseline. Add new tests in the current preferred test hierarchy (do not invent a parallel test runner). At minimum:

- Power-menu transient status and reboot overlay lifecycle.
- Preload media metadata, IPC progression/stall, single-owner and readiness/EOF logic.
- Launcher icon manifest/cache policy, eager/lazy priority, fallback and DOM reconciliation.
- Flatpak lock/unlock lifecycle model and launch stage timings.
- Reload launcher layer/overlay lifecycle and hit-testing.
- App Back protocol, native result model, app adapter mapping and session-generation race handling.
- Edge gesture state machine with compact/expanded state, up/down, pointer+touch duplicate, cancellation, multitouch, iframe and OSK cases.
- Systemd graph collector parsing fixtures and unsupported/missing data.

### 15.2 Static and build checks

- Python: compile and lint changed Python modules; validate JSON schema/config; run security checks for subprocess argument handling and path injection.
- C: compile all changed Wayland clients with the canonical A45 build flags for target AArch64; run sanitizers/host tests where available; check all callback lifetimes and Wayland object destruction.
- JS: syntax-check modules, run existing browser/Node tests and add deterministic DOM test fixtures. Use the repository's actual tooling.
- CSS/HTML: validate asset URLs, ARIA state and duplicate IDs. Verify no hidden overlay retains active pointer events.
- PWA: run service-worker/static-asset validation; ensure new cache version and asset manifests are in lockstep.
- Packaging: verify source files land at the actual installed locations and packaged systemd unit dependencies remain correct.
- Run the full relevant `make`/beta test gates, not only new tests. Record pre-existing failures separately from regressions.

### 15.3 Device / hardware tests

Run on the actual phone when available:

1. Cold boot and observe all 6.016 seconds of preload motion.
2. Restart from Settings and confirm “Restart accepted” is not visible on the next boot's laser penguin image.
3. First unlock: check desktop/dock icons paint immediately.
4. Re-lock and unlock ten times with Firefox/VLC/other representative Flatpaks running; confirm no process or state reset.
5. Cold and warm Flatpak launches; capture stage metrics and first visible frame.
6. Reload launcher repeatedly; confirm no blue rectangle and no stale surface.
7. Short Back from native Flatpak/PWA at root, immediate drawer open, app launch and repeat.
8. PWA fullscreen: top pull one reveals compact bar, second pull opens QS, upward swipe dismisses.
9. Native Flatpak fullscreen: same top gesture flow.
10. With OSK visible, swipe up from physical bottom and tap Back/Home/Recents; keyboard keys must still work.
11. Verify no gesture path leaks app input onto the lockscreen.
12. Capture current boot graph and previous shutdown timeline where possible.

Keep a record with device build hash, software versions, test date, exact steps and evidence. A host browser simulation is not a substitute for the native S10+ tests.

### 15.4 Performance acceptance

For all timing metrics, publish baseline and after values captured under equivalent conditions:

- preload first motion, full video motion duration, video EOF and first lockscreen-ready time;
- first Home paint, first desktop icon paint and last visible icon paint;
- Flatpak tap-to-process, process-to-window, window-to-first-frame;
- lock start/unlock finish to existing app frame visible;
- nav top/bottom gesture start-to-controls-visible;
- systemd boot path and shutdown stop intervals.

Do not report fabricated percentages. If hardware availability prevents before/after comparison, label the measurements not collected and still include the collector/test infrastructure.

---

## 16. Implementation order and coordination

Follow this order unless the live reproduction shows a dependency that requires a safe adjustment:

### Phase A — Baseline and reproduction

- Verify source and target versions.
- Run current relevant tests.
- Capture current restart/preload bug, icon paint timing, Flatpak lock/unlock state, reload rectangle, Back/drawer failure and fullscreen gesture matrix.
- Collect initial systemd boot data before changing service ordering.

### Phase B — Fix transition and surface ownership

- Fix restart transient state and clean boot presentation.
- Fix launcher reload overlay teardown.
- Fix Home/app transition cleanup and invisible touch interceptors.
- Confirm stable Flatpak window retention across lock/unlock.

### Phase C — Fix first paint and startup

- Repair immutable icon cache and stable icon DOM rendering.
- Add launch stage instrumentation.
- Optimize Flatpak discovery/launch only with measurement and security preserved.

### Phase D — Implement unified Back + gesture contract

- Introduce PWA Back contract and native adapter/result model.
- Implement app-first Back and explicit confirmed-root Home fallback.
- Coordinate PWA/native topbar and Quick Settings state machine.
- Guarantee nav gesture strip with keyboard.

### Phase E — Fix and verify preload cinema

- Instrument and root-cause 1-second freeze.
- Fix player/decode/presentation/overlay issue.
- Validate full 6-second playback on hardware.

### Phase F — Systemd graph, full verification and release consistency

- Generate `SYSTEMD-GRAPH.md` from the target phone.
- Run every test gate and hardware case possible.
- Check packaging/deployment, cache version, manifests and changelog/version policy.
- Produce a concise final P90 report with completed, blocked and not hardware-verified status.

Do not reorder phases in a way that loses the pre-change baseline measurements.

---

## 17. Files and areas expected to be touched (verify before editing)

Likely code surfaces include, but are not limited to:

**Power/restart/boot**
- `pwa/nuxel-apps/settings/power-menu.js`
- `pwa/nuxel-apps/settings/power-menu.css`
- `tools/s10plus/a45/nuxel-pwa-host.c`
- `services/nuxel-s10/bin/nuxel-wl-fb-hold.sh`
- `tools/s10plus/a45/nuxel-session.sh`
- `services/nuxel-preload-cinema/nuxel-preload-cinema`
- `services/nuxel-preload-cinema/nuxel-preload-cinema.service`
- `configs/nuxel/boot/preload-cinema.json`
- preload asset packaging and checksum manifests

**Home/launcher/icons**
- `pwa/nuxel-home/js/app.js`
- `pwa/nuxel-home/js/apps.js`
- `pwa/nuxel-home/js/launcher.js`
- `pwa/nuxel-home/sw.js`
- `pwa/nuxel-home/css/style.css`
- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/css/lockscreen.css`
- `pwa/nuxel-home/index.html`
- app/icon registries, asset manifests and deployment manifests

**Back/navigation/gestures**
- `pwa/nuxel-home/js/navigation.js`
- `pwa/nuxel-home/js/immersive.js`
- `pwa/nuxel-home/js/status-bar.js`
- `pwa/nuxel-home/js/qs.js`
- `services/nuxel-bridge/src/api.py`
- native foreign-toplevel helper/source (locate actual current path)
- `tools/s10plus/a45/nuxel-navdock.c`
- `tools/s10plus/a45/nuxel-statusbar.c`
- `tools/s10plus/a45/nuxel-button-manager.c`
- `tools/s10plus/a45/nuxel-shell-chrome.sh`
- `tools/s10plus/a45/nuxel-session.sh`

**Flatpak**
- `services/nuxel-bridge/src/flatpak_provider.py`
- `services/nuxel-bridge/src/api.py`
- app registry/provider and native app launch/session management

**Diagnostics/tests**
- existing `tests/pwnage31000/`
- existing `tests/pwnage49000/`
- existing `tests/pwnage54000/`
- existing `tests/pwnage62000/`
- existing `tests/pwnage63000/`
- `tools/diagnostics/` (or canonical diagnostics folder)
- root `SYSTEMD-GRAPH.md`
- new `diagnostics/systemd/` evidence and graph assets

Do not edit generated copies without identifying their source-of-truth relationship. Update source, generated output, package manifests and installed payload consistently.

---

## 18. Versioning, cache version and deployment discipline

- Follow the repository's current version policy. Do not invent a new semantic version or roll back to the source snapshot's observed version.
- If the task is considered a release-sized change, update all canonical version files and public version metadata in the exact manner already used in the current checkout. Do not version-bump archived historical docs or logs that intentionally preserve provenance.
- Bump the Home service-worker cache namespace for changed PWA code/assets. Ensure every relevant static asset manifest, `CACHE_VERSION`, desktop/PWA version marker and deployment checksum is consistent.
- Run package/build/install staging and verify installed file hashes against the source payload.
- Do not restart system-wide services, compositor, Home or the device in the middle of a destructive operation without a tested rollback. For native C shell changes, stage the new binary, validate it, retain the last-known-good binary and have a recovery route before activating it.
- Keep systemd unit changes validated using `systemd-analyze verify` for all modified unit files.
- If remote deploy is used, confirm the SSH/session remains alive and the target is the correct device; deploy atomic bundles where supported. Do not blindly replace all active services at once.
- Do not push, merge, open a PR, or trigger a public release unless the operator's actual task/workflow explicitly requests those GitHub actions. This prompt authorizes implementation and verification only.

---

## 19. Definition of done

The mission is complete only when:

1. “Restart accepted” is confined to the outgoing request session and never appears over the next boot's laser penguin/preload video.
2. The preloading MP4 is confirmed to move throughout its complete ~6.016-second duration on the target phone, or an honestly documented hardware blocker remains.
3. All visible desktop and dock icons are painted immediately on first unlock and after re-lock/unlock, with no unnecessary refetch/redecode.
4. Existing Flatpak apps remain alive and visually/statefully intact across lock/unlock, with evidence from PID/toplevel comparisons.
5. Flatpak time-to-first-frame is measured and improved without weakening sandbox or runtime compatibility.
6. Reload launcher has no stale blue rectangle, old splash or invisible overlay.
7. A single Back from app root returns to Home and the drawer can be opened immediately. The invisible-overlay regression test passes repeatedly.
8. In both PWA and native fullscreen, the top edge is interactive; first pull reveals compact bar; second pull opens Quick Settings; upward swipe closes it.
9. Bottom nav can be revealed by an upward swipe while OSK is open, without losing keyboard input/focus.
10. PWA and Flatpak Back first perform app-internal navigation wherever supported. Unknown capability does not masquerade as a confirmed root state. The identified GTP+ app is included if installed.
11. Short Back, Home and long-Back have distinct, tested behavior.
12. `./SYSTEMD-GRAPH.md` exists in the repository root and contains real device data or a plainly marked capture limitation, with the collector and SVG/raw data stored alongside it.
13. All relevant unit, integration, packaging, static, security and hardware tests are reported accurately; no new regressions have been hidden behind broad warning suppression.
14. The final handoff includes changed files, root causes found, tests executed, measured before/after metrics, known limitations and rollback notes.

**Do not declare FULLY_DONE while a required hardware test is merely assumed, while a Back adapter returns an unverified `at_root`, or while the systemd graph contains invented timing data.**

---

## 20. Final response format from the executing agent

Return a structured engineering report:

1. **Status:** `FULLY_DONE`, `PARTIAL` or `BLOCKED` — use `FULLY_DONE` only when every required acceptance gate passes.
2. **Root causes:** one paragraph per issue, clearly separating confirmed cause from remaining hypothesis.
3. **Implementation:** concise list of what changed, with source paths.
4. **Validation:** commands/tests and exact pass/fail counts.
5. **Hardware verification:** device, build, steps, results and evidence. State `NOT RUN` where not run.
6. **Performance:** before/after measurements for icons, Flatpak launch, preload and lock/unlock. Do not invent unavailable values.
7. **Systemd graph:** path to `SYSTEMD-GRAPH.md`, boot SVG, shutdown evidence and any data not captured.
8. **Back adapter coverage:** list installed native/Flatpak app IDs with verified adapter behavior, unsupported ones and the GTP+ identification result.
9. **Risks/limitations:** only material remaining issues.
10. **Rollback:** exact safe rollback path for any native binaries, service units, JS bundles or PWA cache changes.

Proceed with implementation. Do not stop after producing a plan.
