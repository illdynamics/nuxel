# 🐧🔥 NUXEL A59 — OPERATION PENGUIN FULL-STACK RESCUE
## Real internet in Nuxel Browser · Native browsers · Native + custom Camera · Complete app discovery · Penguin Home button FIXED

**Executor:** GPT-5.6 Sol, High thinking (recommended); DeepSeek-v4-pro-thinking acceptable. **Target:** actual Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820, booting the **current** Nuxel Fedora ARM64 build with Phoc/Wayland, Nuxel Home and USB Live Console. **Host:** Fedora laptop for cross-development; existing proven MacBook/Fedora USB recovery connection for handset deployment. **Execution:** inspect actual CURRENT repo + physical device first, implement incremental fixes, run focused regression tests, install software **ON THE PHONE**, perform physical tests, capture receipts, preserve a rollback.

**Owner's four CURRENT blockers:**

1. **Nuxel Browser does not browse the external internet.** Make our custom browser an actual, interactive, secure WebKitGTK browser: `https://www.google.nl` loads, typing/search works, outbound links load, Back/Forward/Reload work. Install and test genuine **Firefox/Chromium** if available for Fedora AArch64; **Ladybird preferred** if a viable actual build/install runs on this phone. No fake iframe, canned Google screenshot, or proxy trick.
2. **Camera:** native Camera application still says "No native camera app installed". Install and successfully launch an actual Fedora ARM64 native Camera application (GNOME Snapshot is first candidate); also finish, register, integrate and launch the custom Nuxel Camera application. Distinguish "application installed/launches" from "Exynos camera sensor produces frames". Prior A52 result: rear sensor enumerated, real preview/capture blocked by ISP/libcamera handler. Do not pretend the latter has been solved without live frames.
3. **Missing apps:** numerous installed and/or authored apps are absent from Nuxel's app drawer. Inventory all installed Nuxel PWA apps, native RPM `.desktop` apps, verified Flatpaks, application registry and user-visible entries; make every real user-facing launchable app discoverable and launchable, without duplicating helpers or fake icons. Preserve actual app icons and the Home four-shortcut dock policy.
4. **Penguin Home face button still doesn't take us Home.** One tap from ANY active PWA/native GTK/browser/Camera/SnekByte/Recents must reliably return to Home Desktop 1, without terminating the active app. This has regressed repeatedly; diagnose architectural ownership and route at Wayland/window/session level if needed, not just another DOM click handler.

**Non-goals:** unrelated UI redesign, camera kernel firmware flashing, bootloader changes, disabling browser sandbox, destroying working system apps or native keyboard, swapping the penguin artwork, breaking SnekByte 7000 gameplay, uncontrolled package upgrades, or gratuitous rewrites.

**Priority:** get real connectivity/HTTPS/browser working → repair native-app window launching → correct app discovery/visibility → fix Home at the authoritative app/window manager → native Camera install + Nuxel Camera completion → check alternate browsers and Ladybird → cold-boot verification. Keep browser acceptance independent of an experimental Ladybird build.

---

# PHASE 0 — PRE-FLIGHT, EVIDENCE, SNAPSHOTS, NON-REGRESSION

Before editing:

1. Identify currently deployed Git commit, worktree status, live service names and artifact hashes. Do NOT assume the archived Nuxel v0.6.3-beta code or previous A51–A58 prompts represent current device state.
2. Read and preserve A51 Wi-Fi work, A52 camera `media_store.py` + `org.nuxel.Camera` interface, A53/54/55 app and browser updates, A56–A58 SnekByte integration, and present App Registry/Home/native launchers.
3. Confirm correct device is selected, USB console is stable, sufficient storage/RAM is available, graphical session user/UID, SELinux state, `$XDG_RUNTIME_DIR`, `$WAYLAND_DISPLAY`, D-Bus session and `DISPLAY` if relevant.
4. Record reversible backups of modified source, active browser host, launcher/desktop registry, UI bundles, Nuxel bridge configs, service units and camera integration. Create a dated, private evidence directory outside Git. Keep rollback command/path for every deployment.
5. Measure current external network connectivity separately from browser function: NetworkManager state, IP, route, DNS, HTTPS TLS, system clock/CA certificates. Guard Wi-Fi secrets; no passwords in commands/logs/screenshots/commits.
6. Record current app drawer and source/installed app inventories **before** any edits; screenshot or owner photo when possible. Physically reproduce broken Home using (a) PWA, (b) native app if any, and (c) overlay/keyboard.
7. Establish a **working non-graphical recovery path** before restarting Phoc, WebKit host, app manager, or D-Bus. No firmware/boot/recovery/kernel flash, no unapproved reboot, no disabling SELinux or sandbox/security features.
8. Fix one root cause at a time, test each milestone, revert if regression. Version the work coherently rather than blindly mixing old prompts.

Useful read-only commands (adapt to actual device; do not print secrets):

```sh
uname -m; cat /etc/os-release; uname -r
systemctl --failed --no-pager
ps -eo pid,user,comm,args | grep -E 'phoc|webkit|nuxel|camera|pipewire|wireplumber' | head -60
nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status
ip -br addr; ip route; resolvectl status 2>/dev/null || true
rpm -q snapshot firefox chromium flatpak gtk4 webkitgtk6.0 2>/dev/null || true
command -v firefox chromium snapshot flatpak gnome-software; flatpak list --app 2>/dev/null || true
printf '%s\n' "$XDG_RUNTIME_DIR" "$WAYLAND_DISPLAY" "$XDG_CURRENT_DESKTOP" "$XDG_DATA_DIRS"
find /usr/share/applications /usr/local/share/applications "$HOME/.local/share/applications" -maxdepth 1 -name '*.desktop' -print 2>/dev/null
```

Document the current source-to-device deployment mechanism and avoid changing the Mac/Fedora host packages by accident.

---

# PHASE 1 — MAKE REAL INTERNET AVAILABLE TO REAL PHONE APPS

**Goal:** the phone itself resolves domains and establishes TLS sessions; don't diagnose Browser UI until physical network service is verified.

- From **on-device** NetworkManager, confirm connected SSID, ACTIVE state, IPv4/IPv6 address, default route, DNS servers, resolver and time synchronization. Check captive portals and TLS CA trust store. Use an actual certificate-valid HTTPS request to `https://www.google.nl` and a second independent domain. Do not bypass cert validation.
- If Wi-Fi still stalls at "Associating DHCP...", find the authoritative NM state transition from AP association to IP configuration. Distinguish incorrect AP `specific_object`, authentication, L2 association, DHCP, DNS, profile persistence and captive portal. Previous legacy code passed invalid `'/new'` into `AddAndActivateConnection`; inspect CURRENT code and ensure correct actual AP object paths. The documented `AddAndActivateConnection(2)` Wi-Fi contract requires a real AP object path for new activation; saved `ActivateConnection` can take the documented `/` auto-selection behavior. Never invent a D-Bus path.
- Ensure client is not racing multiple connect attempts, reusing stale scanned AP objects, leaking Wi-Fi credentials, hanging without timeout, or deleting a saved profile. Verify settings survive reboot after owner approval.
- For browser-only failure, trace DNS/TLS/proxy permissions and WebKit subprocess network namespaces under its actual session; compare CLI network access from the **same unprivileged graphical user**.

**Evidence gate NET:** `ip/route/resolver` and validated TLS HTTPS work on phone, then browser loads real page; report root cause separately if network was already fine.

---

# PHASE 2 — NUXEL BROWSER MUST BE A REAL WEBKITGTK BROWSER

The older Nuxel Browser used an HTML iframe. Sites such as Google often refuse embedding; a functional browser requires a **top-level native WebKitGTK WebView**. Do not bypass X-Frame-Options or CSP; do not serve an external page through a privileged Nuxel bridge proxy to hide origin.

## 2.1 Architecture audit

Locate actual browser PWA source and native host: `pwa/nuxel-apps/browser`, Home application registry and bridge, GTK/WebKit dependencies, available GTK3 vs GTK4 bindings, `webkit2gtk-4.1` vs `webkitgtk-6.0` APIs, session launcher and browser rendering/containerization. Avoid casually loading two conflicting WebKit versions into a shared Home process.

Choose one **correctly isolated native browser-window implementation** using WebKitGTK, integrated with Nuxel's application identity and session lifecycle. Reuse the existing Nuxel Browser visual theme. If the system's current WebKit host can safely provide a dedicated independent top-level view, use it; otherwise create a small unprivileged native GTK browser application with a true `WebKitWebView`. Do not use a nested webpage iframe to present external internet.

## 2.2 Features required

- Real address/search field with virtual keyboard support; `google.nl` resolves to `https://www.google.nl/` or redirects legitimately; free text becomes a properly URL-encoded search query (no shell escapes/shell commands).
- Working HTTPS + certificate validation; human-readable DNS/TLS/offline errors; retry, progress indicators, no indefinite spinner.
- Back, Forward, Reload/Stop, Home and external link handling. The Nuxel system Back button should navigate browser history first where appropriate; the **Penguin Home button always goes to Nuxel Home**.
- Touch scroll, tap/click, text selection, real website keyboard focus, pinch zoom when the active compositor/input stack allows; screen rotation and keyboard dismissal compatible with current system.
- Tab handling at least one usable tab; if adding multi-tab, ensure resource control and app history persist. Preserve zoom/history/bookmark settings only if actually implemented; don't add fake toggles.
- Prevent `file://` arbitrary filesystem exposure, untrusted `nuxel://` or bridge commands from websites, unrestricted custom-scheme command execution, unsafe `javascript:` URLs from address field, origin bypasses, and unexpected privileged page-to-host WebKit message handlers.
- Run as ordinary user; use appropriate WebKit process isolation and sandbox. Do not resolve old-kernel compatibility by disabling all web security, using `--no-sandbox`, or running browser as root.
- Restore last page or present a safe homepage; load must be reproducible after reboot, with no missing JS, race condition or stale service worker cache.
- Network outages must show recovery states, not silently render an offline static fake Google page.

## 2.3 Real phone acceptance

Launch **Nuxel Browser** from app drawer; enter `https://www.google.nl`; see live page; tap search field, type with current gray/black/blue OSK; submit query; open search result in real internet; Back returns to results; Forward returns; Reload works; switch Home and resume Browser; reopen after browser termination and after reboot. Repeat with a second HTTPS site. Evidence must include actual URLs and load-event receipts and owner-observed physical result, without personal account/login data.

**Browser milestone cannot be marked PASS by `curl` alone or by rendering a placeholder webpage.**

---

# PHASE 3 — INSTALL AND LAUNCH NATIVE BROWSERS (LADYBIRD PREFERRED IF REALISTIC)

**Mandatory first:** working Nuxel Browser. Then honest installation/verification of external browsers ON THE S10+, not on the development laptop.

1. **Firefox:** check Fedora ARM64 repo/provenance and package architecture, available memory/storage, dependencies. Preview DNF transaction, install signed RPM if safe; launch on target Wayland session as normal user; load `https://www.google.nl`, type, tap, navigate, return Home. Record package NEVRA/arch and actual window PID/desktop identity.
2. **Chromium:** same process for Fedora `chromium` ARM64. Inspect sandbox support (user namespaces, seccomp, zygote, shared memory, GPU, `/dev/shm`). Do not pass `--no-sandbox` or make it run as root to claim victory; if it cannot run securely with current vendor kernel, record precise kernel dependency and block.
3. **Ladybird (OWNER'S PREFERENCE):** inspect upstream build docs, genuine AArch64 toolchain requirements and release status; test approved package/official build when supported, or build from source in an off-device separate build tree targeting AArch64. Ladybird is currently pre-alpha/developer-oriented; don't ship it as stable merely because it compiles. Confirm it is *actual Ladybird*, not Firefox/Epiphany renamed. Bound compilation time and storage; do not block other milestones on a multi-hour/unsupported build. If successful, make it visible and launchable like any other native app; otherwise show a precise build/runtime blocker without a fake install.
4. **Optional GNOME Web/Epiphany:** consider as a pragmatic native WebKitGTK browser if the custom browser cannot immediately reach native stability. It does not replace the required custom Nuxel Browser milestone.

Use RPM packages from trusted repos where possible. Flatpak is valid **only if its bubblewrap/user namespace/portal sandbox works on this Exynos 4.14 kernel**; do not loosen kernel security to force it. Never install a random third-party ARM binary from an unverified site.

**Per browser statuses:** `NOT_PRESENT`, `PACKAGE_AVAILABLE`, `INSTALLED`, `LAUNCHES`, `NETWORK_VERIFIED`, `BLOCKED_ARCH`, `BLOCKED_SANDBOX`, `BLOCKED_GPU`, `UPSTREAM_PREALPHA`, `FAILED_TEST`. Record separately.

---

# PHASE 4 — CAMERA: AN ACTUAL NATIVE APP + COMPLETE NUXEL CAMERA

**Known previous A52 evidence:** the rear camera sensor enumerates, but real camera frames/JPEG/front/video were `BLOCKED` because the Exynos camera driver/ISP/libcamera pipeline was not yet functional. This is not solved by installing Snapshot. Fix the confusing "No native camera app installed" message as an *application availability problem*; report hardware unavailability separately.

## 4.1 Install a native camera application

- Inspect current target package state: `rpm -q snapshot`, `command -v snapshot`, installed `.desktop`, graphical-session environment and Flatpak state. The Fedora package is **`snapshot`** (GNOME Camera). Use trusted Fedora repo RPM for exact AArch64 target. Preview dependency transaction and available disk/RAM; do not remove system packages blindly.
- Check GNOME Snapshot runtime dependencies as documented upstream: PipeWire, WirePlumber, GStreamer PipeWire, GTK4 plugin, gst-plugins-bad, and libcamera/GStreamer libcamera components when available. Restore missing session sockets/portals rather than creating fake camera devices.
- Launch as real GUI user in Phoc/Wayland using correct `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`, session D-Bus and appropriate desktop integration; capture stdout/stderr/journal startup errors. Prove visible native Camera window on S10+, not just successful DNF.
- Register app so launcher says `Camera (GNOME Snapshot)` or sensible name/icon and launches from Nuxel Home. Ensure original "No native camera app installed" indicator is based on checked install/launch capability and isn't a stale hardcoded flag. If missing, show Install action only if installation is implemented and permitted.
- Test opening application **even if it says No camera available**; that counts as native-app-installed/launchable but not hardware-ready.

## 4.2 Nuxel's own Camera app (separate app, separate identity)

- Inspect A52 app and backend. Preserve file-backed `media_store.py`, atomic saves, real `camera.status`, `camera.capture`, `camera.list-captures`, `camera.open`, `camera.delete`, private `org.nuxel.Camera`, camera/microphone access controls, privacy indicator and Photos integration.
- Ensure Nuxel Camera has a standalone Home icon, an actual launcher entry and a properly rendered UI. It must not be a renamed Snapshot window; provide its own native or WebKitGTK app front-end tied to Nuxel's existing capability bridge.
- Correct detection: UI should say `Camera hardware unavailable — rear sensor found, image pipeline not ready` when true, with a clear **Open native Camera** option if Snapshot is installed; not `No native Camera app installed` when Snapshot is launchable.
- If real frame sources exist, integrate an actual V4L2/media-controller/PipeWire/libcamera path, with device-node, caps, ISP handler and errors corroborated. Capture a real JPEG and persist it through `/var/lib/nuxel/media` (or current confirmed location), browse in Photos, test video only when actual frame/audio path available.
- Do not use synthetic video/test pattern, USB webcam, random image file, browser fake preview or arbitrary `getUserMedia()` success to claim the Exynos sensor works. Provide truthful detailed hardware-blocker report if no lawful, working driver path exists.
- Camera input focus, permissions, indicator, Home button behavior, lockscreen privacy, pause/resume and process cleanup must work. Camera must release device on lock/Home where appropriate.
- No kernel/firmware/boot/recovery writing, proprietary blob substitution, security weakening, destructive ISP experiments or `modprobe` guesswork without independent risk assessment.

## 4.3 Camera result gates

`SNAPSHOT_INSTALLED` = package exists. `SNAPSHOT_LAUNCHABLE` = native GUI visible. `NUXEL_CAMERA_LAUNCHABLE` = custom application appears and handles operations. `CAMERA_SENSOR_DETECTED` = hardware enumerates. `LIVE_REAL_FRAMES` = genuine physical sensor frames captured. `REAL_JPEG_PERSISTED` = photo survives app restart; only then claim usable camera functionality.

---

# PHASE 5 — EVERY ACTUAL APPLICATION VISIBLE AND LAUNCHABLE

**Problem:** app drawer omits lots of applications even if installed. Need a single authoritative app-discovery and lifecycle architecture, not more hardcoded icons in HTML.

## 5.1 Build evidence inventory (mandatory)

Inventory and reconcile **four sources**:

A. Nuxel apps/PWAs in repo/current deployed package tree (Browser, Camera, Photos, SnekByte, Calendar, Contacts, Phone, Messages, Mail, Notes, Calculator, Clock, Files, Settings, Maps, Weather, Terminal, Nuxtore, etc. if actually present).

B. Nuxel's own app registration/config JSON, internal application IDs, icons and launch routes.

C. Native RPM `*.desktop` entries in XDG application directories, respecting real `XDG_DATA_DIRS`, user/system precedence, `Type=Application`, `Exec`, `TryExec`, `DBusActivatable`, `NoDisplay`, `Hidden`, `OnlyShowIn`/`NotShowIn`, startup and locale names.

D. Flatpak-exported desktop entries for verified installed Flatpaks under system/user export paths, respecting sandbox limits. Do not invent a `flatpak` entry if runtime is missing; do not present uninstalled apps as installed.

Create machine-readable `app-inventory-before.json` and final counterpart with: app ID, source, package, executable/route, icon, actual installed/launchable status, user-facing visibility reason, permissions, desktop entry path and validation result. Do not log private env values.

## 5.2 One registry, no duplicates

- Implement/update **one discoverer/registry** for Nuxel PWA/native/Flatpak apps. Use stable canonical IDs (e.g. desktop-file IDs), deterministic conflict resolution and no duplicate Browser/Camera/SnekByte icons when one app has multiple manifest entries.
- Correct stale cached app index, old JS bundles, service worker caches, app installation events and race conditions. Update list on package installation/removal and user session start; bounded event-driven refresh instead of high-frequency polling.
- Reconcile `NoDisplay` helper packages: not every `.desktop` file is intended as a user-visible app. Respect `Hidden`/tombstones, shell helper programs, app-specific preferences and security boundaries. Provide an explicit **Show compatible desktop apps** setting if an environment filter hides valid native apps that are launchable on Nuxel; avoid silently exposing setup tools or unsupported privileged launchers.
- Correct icons: use each app's real packaged icon, Nuxel-designed icon when available, and sensible generic fallback only as last resort; preserve SnekByte snake/poop artwork. No invisible/blank icon if asset load fails.
- Avoid exposing raw root terminal commands as clickable app launches. Validate desktop `Exec` and args using proper desktop-file parsing, **never shell-concatenate untrusted text**; run in actual unprivileged Wayland user session with appropriate environment, not root.
- Keep app drawer scrollable/searchable; support many entries, landscape, stable sorting, folders/categories if already present, and accurate empty/loading states.
- **Home four-app shortcut dock** appears only on Home, not over open applications; bottom triple Back/Home/Recents controls remain the existing system navigation dock and not duplicated.
- Add visual unavailable/broken states where software is present but a binary or driver is missing; don't silently hide it as if never installed.

## 5.3 Launch reality check

For each valid visible app choose at least one physical launch test per category: Nuxel PWA, native GTK, native browser, Flatpak (if supported), SnekByte. Verify proper app identity/window, foreground focus, Back/Recents/Home, and close behavior. Save registry-to-process/window mappings for debugging and deduplication.

**Never call this complete only because an icon grid is populated.**

---

# PHASE 6 — FIX THE PENGUIN HOME BUTTON ONCE AND FOR ALL

The owner has repeatedly reported **Penguin face button does not return Home**. Treat this as an architectural **navigation ownership and event-routing bug**. The repair must work from every managed app, not only from the launcher DOM.

## 6.1 Trace gesture → compositor → shell action

1. Inspect bottom navigation markup, JS event handlers, touch/pointer capture, duplicate overlays, CSS `pointer-events`, app fullscreen/scroll containers, z-index, Wayland native surfaces and current `nuxel-home` session-controller process.
2. Trace actual taps with timestamps: physical touch → compositor/libinput → navigation dock → dispatch → shell action → active window transition → Home Desktop 1 visible and focused. Instrument failures without verbose permanent logging.
3. Determine whether the nav dock lives in Nuxel Home, a WebKit overlay, a layer-shell surface or a separate native process. A DOM click handler cannot reliably minimize/focus external native GTK/Firefox/Snapshot windows if it does not own their window lifecycle.
4. Build **one authoritative `go_home()` command** in the Nuxel session/window manager that resolves the active window, restores/focuses Home, and deactivates/minimizes/lowers the previous application **without killing it**. Use actual supported Phoc/wlroots/phosh/window-management APIs. Wayland does not allow arbitrary client-side window control: if the current compositor offers no supported mechanism, implement this narrowly in the trusted shell/controller or a compatible compositor extension, not an insecure unrestricted network/D-Bus endpoint.
5. Connect the Penguin tap action and any keyboard/accessibility Home shortcut to that same trusted command. Promise only what the actual compositor capabilities allow; document integration blockers if genuine permission/protocol support is missing.
6. Preserve app state when returning Home; app remains available in Recents; foreground focus returns appropriately when reopened. No forced global UI reload. No killing native apps to fake minimizing.
7. De-duplicate handlers and remove conflicting/redundant navigation strips. One tappable Penguin face button with correct hitbox and no hidden overlay intercepting touches.
8. Treat virtual keyboard specially: pressing **Back** dismisses OSK first (existing behavior); pressing **Home** returns to Home even if OSK is showing, with focus cleaned up. Back long-press app kill remains supported without accidental Home action.
9. When lockscreen is visible, triple nav should remain **hidden**. When screen is off, no ghost navigation events; no network-exposed global unlock.
10. Register Home action for Nuxel Browser, Firefox, Chromium, Ladybird if installed, Snapshot, Nuxel Camera, Files, SnekByte, Settings, and all normal PWAs.

## 6.2 Required test matrix

- Home button from Nuxel Camera
- Home from native Snapshot
- Home from Nuxel Browser on an external website
- Home from Firefox/Chromium if launchable
- Home from SnekByte while mid-game (app should pause/resume per design)
- Home from Files, Settings and Terminal
- Home with keyboard open and while page is scrolling
- Home from app drawer, Quick Settings and Recents
- Home after closing an app, after session resume, after an owner-approved reboot
- Repeated taps/long touch and quick switching; no duplicate app opens, no stuck overlay

**FAIL if a tap merely closes a modal or routes to an inert in-app "home" page while Nuxel Home Desktop 1 remains inaccessible.**

---

# PHASE 7 — INCREMENTAL IMPLEMENTATION, SAFE DEPLOYMENT, ROLLBACK

Use staged commits / rollback artifacts:

- **M0:** Sources, system/service inventory and backups; compile cross-target packages if needed; ensure target is AArch64.
- **M1:** Phone network tests + top-level custom Nuxel Browser loads live Google homepage and interacts securely.
- **M2:** Native app launch mechanism and complete installed-app inventory/registry; show genuine icons and restore newly installed apps automatically.
- **M3:** Fix authoritative Penguin Home action and deep regression-test navigation across native + PWA apps.
- **M4:** Install/launch Snapshot and ensure custom Nuxel Camera is registered and functional to its actual hardware capabilities.
- **M5:** Install Firefox, Chromium, then evaluate Ladybird; prioritize install/launch/network evidence and reasonable power/RAM impact.
- **M6:** One owner-approved cold boot and end-to-end demo with service persistence, no Wi-Fi profile loss and no hidden apps.

At each step: staged source + unit/integration tests → safe deployment over working USB → verify installed version/hashes → restart only required userspace service → observe physical phone → rollback on regression. Preview DNF/Flatpak install transactions; ensure services are not inadvertently installed only on host. Keep recoverability after any Wayland/Phoc restart. Do not flash kernel, partitions, camera firmware or boot assets. Do not reboot without owner's permission and recovery instructions. Avoid leaving test-pattern or mock services enabled.

### Testing requirements

**Automated:** browser URL normalization and escaping, navigation history, URI scheme allowlist, TLS error reporting, app registry XDG desktop spec parsing, deduplication, app discovery changes, icon fallback, Home state transitions/one-dispatch semantics, camera package detection and capability-status separation, keyboard focus, no elevated native app launches, installer rollback, saved Wi-Fi profile handling.

**On-device live:** HTTPS browsing / Google interaction / second site, native browser app launch, Snapshot GUI opening, Nuxel Camera GUI opening, all installed app categories present, Home from each, history/app state persistence, browser security isolation, camera privacy, screen-off CPU/heat, reboot persistence. Test at normal screen orientation and any working landscape mode without expanding this mission into orientation driver repair.

Performance guard: app drawer first open not blocked by synchronous package scanning; WebKit navigation UI remains interactive while loading; avoid elevated CPU when idle/off, unbounded frame loops, busy polling and expensive background Ladybird compilation on the phone. Do not fake FPS or latency numbers.

---

# PHASE 8 — STOP CONDITIONS, EVIDENCE, DELIVERABLES

Stop and report a precise blocker if:

- no valid internet/DNS/TLS path, and physical Wi-Fi/network diagnostics identify a hardware/kernel or authentication issue outside safe userspace repair;
- WebKitGTK sandbox cannot run without disabling browser security;
- native Firefox/Chromium/Ladybird requires unsupported kernel/security primitives;
- Snapshot installation would remove critical phone packages, or GTK session cannot support its window requirements;
- Exynos ISP produces no real frames (report camera app separately installed/launchable);
- Wayland compositor API cannot focus/restore Home safely without trusted shell changes outside approved scope;
- USB recovery path or phone temperature/battery condition makes deployment unsafe.

Record honest completion categories: `PASS_PHYSICAL`, `PASS_ON_DEVICE_INTEGRATION`, `PASS_OFFLINE_ONLY`, `PARTIAL`, `BLOCKED_KERNEL`, `BLOCKED_CAMERA_ISP`, `BLOCKED_WAYLAND`, `BLOCKED_PACKAGE_ARCH`, `BLOCKED_SANDBOX`, `NOT_TESTED`. Do not mark unmet requirements green.

### Mandatory documents

- `docs/a59/BASELINE-AND-ROOT-CAUSES.md`
- `docs/a59/NETWORK-AND-HTTPS.md`
- `docs/a59/NUXEL-BROWSER-REAL-WEB.md`
- `docs/a59/NATIVE-BROWSERS-INSTALL-RESULTS.md`
- `docs/a59/CAMERA-NATIVE-AND-CUSTOM.md`
- `docs/a59/APP-INVENTORY-BEFORE.json`
- `docs/a59/APP-INVENTORY-AFTER.json`
- `docs/a59/APP-REGISTRY-DISCOVERY.md`
- `docs/a59/PENGUIN-HOME-ROOT-CAUSE-AND-FIX.md`
- `docs/a59/ON-DEVICE-ACCEPTANCE.md`
- `docs/a59/ROLLBACK.md`

Evidence must contain exact implemented files, change summary, package architecture/version and trusted source, service/process IDs when relevant, sanitized commands + exit codes, automated test counts, real S10+ window/GUI observations, actual HTTPS target results, tests after reboot, explicit unresolved hardware constraints, and rollback paths. No source-only claim of real device success.

## FINAL PHYSICAL ACCEPTANCE — OWNER'S DEMO

1. Unlock S10+ into Nuxel Home.
2. Open Nuxel Browser via visible app drawer icon.
3. Enter `https://www.google.nl`; real homepage appears, enter search with on-screen keyboard, open result.
4. Press **Penguin Home**; immediately see Home Desktop 1. Reopen Browser; tab/page history remains as implemented.
5. Open installed **Firefox** and **Chromium** (or report concrete sandbox/architecture blocker for each); open real external HTTPS page; Home button again works.
6. Open **Ladybird** if genuine working binary exists; if not, show exact honest current status and keep stable browser working.
7. Show complete app drawer: Nuxel apps, SnekByte, Camera/Photos, native Snapshot, browsers, compatible installed RPM/Flatpak apps all appear, deduplicated, with correct icons. Scroll/search and launch examples.
8. Open **GNOME Snapshot** as its actual native GUI; show whether camera feed exists or honest sensor/ISP unavailability.
9. Open **Nuxel Camera** as a separate custom app; show capability diagnostics/media list, no mock feed; Home always works.
10. Switch to SnekByte, start game, press Penguin Home, reopen and verify proper pause/resume; Back/Recents continue functioning.
11. Obtain approval, reboot once, repeat Browser external HTTPS + app visibility + native Camera launch + Penguin Home checks. Saved Wi-Fi connects and app registration persists.

**Definition of DONE:** the phone performs the demonstrated actions; no invented apps, fake camera streams, inert Home button or mock browsing. If an actual camera sensor pipeline remains blocked, native Camera *installation* may pass while real capture clearly remains blocked. Same for experimental Ladybird or unsupported secure Chromium execution.

**GO RESCUE THE PENGUIN — ONLINE, CAMERA-EQUIPPED, APP-FILLED, AND FINALLY HOME. 🐧🌐📸🏠🔥**
