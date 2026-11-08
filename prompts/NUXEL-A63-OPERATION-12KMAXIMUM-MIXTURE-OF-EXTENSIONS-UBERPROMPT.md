# 🐧🔥 NUXEL A63 — OPERATION 12KMAXIMUM: MIXTURE OF EXTENSIONS
## The definitive Fedora-hosted integration, completion, anti-regression and physical acceptance campaign

**Agent:** DeepSeek-v4-pro-thinking, with deliberate long-horizon planning and rigorous evidence checks.  
**Development host:** Owner's Fedora 43 laptop, x86_64, NVIDIA RTX 3060 (host GPU is NOT the phone GPU).  
**Physical device:** Owner's Samsung Galaxy S10+ **SM-G975F / beyond2lte / universal9820 / Exynos 9820**, running Nuxel Fedora ARM64 and its existing Samsung-derived Linux 4.14 kernel.  
**Current Nuxel architecture (verify on live device):** Phoc/Wayland, WebKitGTK-based Home/PWAs, Nuxel bridge/D-Bus, native GTK apps, NetworkManager, USB Live Console, custom lockscreen, input-method/keyboard, native and PWA app discovery.  
**No destructive operations:** This mission is userspace integration and diagnosis. NO flashing, kernel swaps, bootloader changes, partition writes, recovery modifications, or unsafe firmware/ISP hacks.

# THE ONE COMMANDING GOAL

Take the **actual current Nuxel repository** and the **actual running S10+**, reconcile all work from **SnakePwn 5000 through Penguin Online 11000**, and advance every feature to its **highest independently verified functioning state**, with no older fixes overwriting newer ones.

This is **NOT** seven parallel copies of earlier missions, not an offline checkbox exercise, and not a fresh OS rewrite. It is an end-to-end integration and reliability campaign with explicit dependency gates, physical evidence, durable fixes, full rollback and a final truthful scoreboard.

**Desired owner's demo:** boot → penguin lockscreen unlocks → Home button returns Home → keyboard opens/closes → SnekByte starts and plays smoothly → Wi-Fi authenticates/associates and gets IP/DNS/HTTPS → Nuxel Browser opens Google.nl → installed native/PWA/Flatpak applications show and launch → battery displays real percentage immediately when its source exists → all rotation modes are present, with actual screen/touch rotation where supported → camera apps launch, remain escapable, and either capture genuine hardware frames or explain exact ISP blocker. Repeat after three authorized cold boots and user-session restarts.

## A. AUTHORITATIVE SOURCES — READ, DO NOT RE-EXECUTE BLINDLY

The following **seven master references** and their owner requests are mandatory reading. Search the current repo root, `reference-prompts/`, project docs, or adjacent prompt archives; this pack includes copies under `reference-prompts/`:

| Mission | Reference document | Feature contracts |
|---|---|---|
| **5000 / A56** | `NUXEL-A56-OPERATION-SNAKEPWN-5000-UBERPROMPT.md` | Real SnekByte PWA, exact pixel-art icon, original Python rule parity, WoNQ poo-meter |
| **6000 / A57** | `NUXEL-A57-OPERATION-SNAKEPWN-6000-ANDROID-APK-UBERPROMPT.md` | Real Android APK, offline packaging, deterministic build, original game preserved |
| **7000 / A58** | `NUXEL-A58-SNAKEPWN-7000-BUTTER-SNEK-UBERPROMPT.md` | Speed settings, seamless edge wrap, early swipe/D-pad response, buffered legal turns, PWA/APK parity |
| **8000 / A59** | `NUXEL-A59-PENGUIN-FULL-STACK-RESCUE-UBERPROMPT.md` | Real browsers, native & custom camera, visible apps, real Penguin Home action |
| **9000 / A60** | `NUXEL-A60-REGRESSION-EXTERMINATOR-9000-UBERPROMPT.md` | Keyboard dismissal, SnekByte launch, Wi-Fi, battery startup, all rotation modes, anti-regression |
| **10000 / A61** | `NUXEL-A61-OPERATION-PENGUIN-EYES-AND-UNLOCK-RECOVERY-UBERPROMPT.md` | Trustworthy swipe unlock, camera never traps user, native/custom camera pipeline, hardware truth |
| **11000 / A62** | `NUXEL-A62-OPERATION-PENGUIN-ONLINE-11000-UBERPROMPT.md` | WPA association, IP/DNS/HTTPS, saved Wi-Fi profiles, real WebKitGTK browser, Firefox/Chromium/Ladybird evaluation |

**Optional supporting history:** A45/A45.1 lockscreen, A47/A48 navigation/metrics, A49 rotation/haptics, A50 frame pacing, A51 Wi-Fi/Flatpak, A52 camera, A53/A54/A55 reliability/GTK/browser. These are **design history**, not instructions to replay stale patches. Read when clarifying a conflict. If an older document says something different from a newer owner request, newer request wins, except safety requirements always stay in force.

If a reference file is missing, record `REFERENCE_MISSING` and recover its contract from current source, user-approved docs and prior code, without hallucinating contents. Do not block every other task because one historical file is absent.

## B. IMPORTANT KNOWN FACTS — REVALIDATE BEFORE DEPENDING ON THEM

1. The phone is **not** a generic ARM64 Linux device; it has Samsung vendor-dependent display, USB, WLAN, battery, sensor, audio and camera systems. Kernel 6.x migration is **NOT** part of A63.
2. Prior Wi-Fi showed `org.freedesktop.NetworkManager.Device.SpecificObjectNotFound: The access point /new was not in the scan list`; a historical bridge sent `'/new'` into `AddAndActivateConnection`. Later attempts progressed to an **"Authenticating and associating"** hang. **Do not assume the old `/new` defect is the only remaining cause.**
3. Actual camera sensor enumeration previously **passed**, while real Exynos ISP/libcamera frames, JPEG, front preview and recording were **blocked**. Installing GNOME Snapshot does NOT produce sensor frames without a real capture pipeline.
4. GNOME Snapshot is a native Camera application candidate; Nuxel's custom Camera should remain a separate native-aware/PWA app. Both must always be escapable.
5. Earlier battery percentage and rotation controls appeared only minutes after boot, with rotation displaying `undefined` early. Delaying the UI to mask this is not a proper fix.
6. Rotation originally required **seven** modes: fixed portrait, fixed reverse portrait, fixed landscape, fixed reverse landscape, auto all four, auto-portrait (0↔180), auto-landscape (90↔270). At minimum expose all seven consistent, correct values; no two-option menu. Actually rotating output + touch mapping is distinct from changing a label.
7. Penguin Home has repeatedly failed for apps, particularly native GTK windows. It must drive the actual trusted session/window manager, not merely set a JavaScript `page='home'` flag.
8. SnekByte had a working Android APK and Nuxel PWA at different points. The current canonical game mechanics include seamless edge wrapping, configurable speed, responsive swipe/D-pad, WoNQ poo after every five food, self/poop collision, saved scores and proper snake-and-poop icon. Do not revert to wall-death behavior.
9. Browser is only complete after **external HTTPS pages** render and accept links/search/keyboard input. Existing Nuxel Browser may still be an iframe or shell rather than a true WebKit webview.
10. Previous work had an expensive compositor/framebuffer bridge, potentially `nuxel-wl-fb`; performance and heat depend on the **actual** runtime pipeline, not assumed native graphics acceleration.
11. Flatpak on Samsung 4.14 requires kernel sandbox namespace capabilities and portal checks; never disable security to declare success. Ladybird, hardware Camera, native DRM/KMS, and specific vendor capabilities might legitimately remain blocked.
12. The **Fedora laptop is a host only**. All physical acceptance tests must run against the S10+. Installing an RPM on Fedora is NOT equivalent to installing it in Nuxel's Fedora ARM64 rootfs.

---

# PHASE 0 — FEDORA HOST & DEVICE ACCESS: DO THIS FIRST

### 0.1 Identify execution context without assumptions

From the **Fedora laptop**, record (not modify) `uname -a`, architecture, Fedora version, toolchain versions, free space, Git workspace path, mounted repos, existing build containers and the attached USB device. Verify local DeepSeek endpoint/model selection via the user's `csft` wrapper or other configured client; **do not assume a CLI flag sets the remote model unless verified**.

For Linux USB console discovery, examine `lsusb`, `dmesg`/`journalctl -k`, `udevadm`, `/dev/serial/by-id/`, and `/dev/ttyACM*` as appropriate. **Do not reuse macOS-only `/dev/cu.usbmodem*` paths.** Inspect the current repo's existing host-console script and README before invoking; the path may have changed. Only one process may own a USB serial interface. If permission is missing, investigate Fedora dialout/udev configuration; do not disable system security or blindly `chmod 777` a device. `adb` only if device actually offers an ADB endpoint; do not mistake recovery/TWRP ADB for normal Nuxel console.

### 0.2 Preserve alternate recovery

- Establish an authenticated, functioning Nuxel USB Live Console or an equally proven wired out-of-band path **before** changing networking, GUI/session state, lockscreen or launchers.
- Capture a known-good console command (`uname -r`, `cat /etc/os-release`, `systemctl --failed`) **on the S10+**, and record connection/mode without exposing private IDs.
- Confirm a recovery route independent of Wi-Fi and graphics. Do not interrupt the console service in pursuit of a nicer UI.
- If the device is unreachable: **work offline only**, prepare staging/tests, report `AWAITING_DEVICE`; do not claim deployed/physically tested.
- Fedora NetworkManager owns the **host** Wi-Fi. Phone NetworkManager controls the **phone** Wi-Fi. All `nmcli`, `dnf` and `systemctl` examples must explicitly state which machine runs them.

### 0.3 Snapshot before changing anything

Create a private timestamped host directory **outside Git** for sanitized state and backup files, e.g. `$HOME/nuxel-rescue/a63/<timestamp>/`. Log repo HEAD, branch, local modifications, submodules, release version, deployed file hashes, active unit files, startup dependencies, rootfs version, running app assets, package inventory and rollback actions. Back up all files/services about to be edited; protect PSKs, browser cookies, saved connections, system identifiers and cryptographic keys. No full partition backup is required for this **userspace-only** job; do not touch partitions.

Implement a single-authority **device mutation lock**: no A56–A62 agent, separate worktree or automation may deploy to the physical phone concurrently. Use feature branches/worktrees on Fedora for offline source tasks but one orchestrator for approved phone deployments.

**Gate P0:** Device identity confirmed, console verified, reversible staging and rollback documented. If not, remain in host-only inspection mode.

---

# PHASE 1 — INTEGRATION ARCHAEOLOGY, NOT REPLAYING PATCHES

### 1.1 Build the provenance map

Read A56–A62, recent Git history, source files, manifests, systemd unit files, package manifests, application registry, desktop files, frontend bundles, resource hashes, tests and actual S10+ installed versions. Discover hidden duplicate paths and generated assets. For every issue, identify:

- Last known working commit/deployment/time and how it was tested.
- Current source implementation and installed runtime implementation.
- Component owner and authoritative source of state.
- Known failure symptom with physical reproduction steps.
- Shared dependency and conflicting mutations introduced by another mission.
- Existing tests versus absent **real-device** tests.
- Fix option, risk, explicit backup and rollback, expected proof.

Required canonical ownership mapping:

| Domain | One authority to choose and document |
|---|---|
| Lock/unlock | Trusted session-lock controller, with WebKit lock UI as frontend only |
| Home/Back/Recents | Actual shell/window manager and common navigation dispatcher |
| OSK visibility | Native working keyboard and focus/input-method controller |
| Apps | One discovered/registered app catalogue with live installed metadata |
| Wi-Fi | NetworkManager state + one bridge adapter, not frontend guesses |
| Battery | Power-supply/UPower + one state publisher |
| Rotation | Real sensor and orientation-policy service + compositor/touch transformation |
| Camera | Camera capture service/permission broker, distinct from responsive app UI |
| Browser | WebKitGTK browser host, GTK app window lifecycle and network session |
| SnekByte | One canonical engine/assets source shared into Nuxel/Android wrappers |
| Rendering | Current Phoc/Wayland and any framebuffer bridge, not assumptions from A50 |

### 1.2 Create dependency graph and eliminate version drift

Generate `docs/a63/01-mission-inventory.md`, `02-runtime-source-drift.md`, `03-dependency-graph.md`, and `04-work-plan.md`. Compare before applying anything. Test actual extension integration points, event names, object paths, app IDs, registration, service ordering, cache revisions, restart triggers and Wayland seat/focus ownership.

**Very important:** A newer implementation can supersede an older prompt. Do not overwrite current working Nuxel or SnekByte with historical drop-in ZIPs. Cherry-pick the **behavior**, not blindly the files. Never discard dirty user changes. Use atomic commits and smaller verified deployments.

When requirements conflict, preserve proven newer functionality, explain the conflict, and resolve at a single owner/service. Any architectural consolidation must include migration tests for existing settings and app identities.

**Gate P1:** One validated current-state matrix and ordered repair DAG, with no untracked or speculative changes.

---

# PHASE 2 — PRIORITY ZERO: PHONE MUST ALWAYS BE USABLE

This phase runs before browsers, Flatpak, long builds or camera hardware debugging.

## 2.1 Fix penguin lockscreen drag-to-unlock

- Preserve `./assets/nuxel-lockscreen.jpg`, `./assets/nuxel-lockhead.png`, visual composition and idle policy.
- Trace finger down → pointer capture → upward displacement → threshold crossed → pointer release → trusted unlock request → authoritative session unlocked → lock surface dismissed → application receives input.
- Ensure lockhead animation/wiggle does not steal pointer input or distort drag coordinates; handle `pointercancel` and lost capture.
- Short swipe returns lockhead to rest, full swipe unlocks; never let any untrusted browser content call a privileged generic unlock endpoint.
- After a successful unlock Home and app surfaces get touch/focus, the correct idle timeout resets and Power can lock again. Cold boot still displays the lockscreen.

## 2.2 Permanent navigation and keyboard behavior

Implement exactly one bottom navigation owner and common dispatcher; no duplicate Back/Home/Recents bars and **none visible on the lockscreen**. Behavior:

- **Short Back** when OSK visible: dismiss existing working grey/black/blue keyboard, keep app open; first Back prioritizes keyboard dismissal.
- **Short Back** otherwise: app history/back action or return from app as appropriate, never trap user.
- **Long Back (~800 ms)**: close only the current foreground app, not Home, not trusted shell or console; robust hold-vs-click separation.
- **Penguin Home**: return to Home Desktop 1 from PWA, browser, Snapshot/GTK native app, Camera, game or errors **without killing app**; handle actual compositor focus/window stacking and input ownership. No DOM-only fake navigation.
- **Recents**: show correct app windows and let users return/close without duplicating navigation.
- Hardware Power when app hangs: locking/unlocking and screen-off remain usable. Do not hide power menu behind a lockscreen overlay if the owner expects it actionable (but do not expose destructive unlocked actions insecurely).

For each input, demonstrate cold start, app loading state, normal app, failed app, lockscreen and screen wake. Camera timeout must never block Home/Back.

## 2.3 App launch and recovery watchdog

App launch runs asynchronously with bounded timeouts, cancellation and visible errors; never block the UI event loop or trusted navigation. Build an app-lifecycle supervisor only if the current one is defective; avoid a second competing supervisor. A failed plugin/browser/camera should be closable; no orphan invisible input surfaces, busy loops or stale fullscreen overlays.

**Gate P2:** Owner can always unlock, navigate Home, dismiss OSK, Back/long-Back and escape a hanging Camera through real input on S10+. Verify before any later disruptive tests.

---

# PHASE 3 — WI-FI: CONNECT IN REALITY, THEN INTERNET

This is the highest-priority networking milestone. Fix the actual phone, not merely the spinner.

## 3.1 Reproduce with sanitized evidence

Capture the on-phone interface identity, NetworkManager + supplicant/iwd backend, device state and reason codes, PHY/firmware version, power save, rfkill, dmesg and WPA transitions while connecting to an **owner-authorized** SSID. Keep PSKs and identifiers out of export logs. Time-stamp link selection, 802.11 auth, association, WPA four-way handshake, IP config, DHCP, DNS, HTTPS. Confirm whether reported **"Authenticating and associating"** is a UI stale phase, genuine WPA problem, driver hang or access-point mismatch.

## 3.2 Isolate frontend from system

Compare a carefully controlled known-good `nmcli` connection path on **the phone** with Nuxel Settings activation. Use actual AP object from scan or documented valid `"/"` sentinel according to installed NetworkManager API version and chosen method—**never literal `'/new'`**. Handle AP disappearing/re-scanning, dual-band duplicate SSIDs, stale scan objects, connection object paths, hidden networks, WPA2/WPA3/PMF, regulatory region and signal quality without guessing.

Inspect chosen D-Bus method signatures, signatures of settings dictionaries, supported WPA flags, `802-11-wireless-security.psk` vs secret agent handoff, autoconnect, correct interface, timeout/retry and error mapping. Avoid spawning overlapping activations. A user entering password once should create/update exactly one validated NM profile, with mode `0600` secrets controlled by NetworkManager. Never log the password or write it into the repo/browser localStorage.

## 3.3 Prove physical network layers sequentially

1. Scan discovers genuine APs.
2. Connection reaches actual authenticated and associated state without fallback to fake connected UI.
3. NetworkManager activates device; requested IP assignment completes (DHCP or owner-defined static).
4. On-phone routing/gateway is correct; no accidental Fedora-host routing.
5. On-phone DNS resolves `google.nl` and a second real domain.
6. TLS/HTTPS succeeds with correct phone clock and CA trust; no disabling certificate verification.
7. Disconnect/reconnect, wrong-password recovery, AP loss, screen off/on and repeated authorized reboot retain a valid secure profile and restore connectivity.

Stop exploring exotic firmware fixes if the first failed state is a simple bridge bug. Conversely, if the **driver** is failing authentication independently of UI, record exact kernel/firmware evidence and a contained fallback, not phantom success.

**Gate P3:** Device can consistently connect with the owner-approved credentials and reach real HTTPS; auto-reconnect survives cold boot. If vendor driver blocks it, report exact first failed state and which layers passed.

---

# PHASE 4 — REAL APPLICATION PLATFORM + REAL BROWSERS

## 4.1 Nuxel Browser must browse, not imitate browsing

Audit the existing Browser's WebKitGTK embedding. Eliminate iframe-only pseudo-browser paths; use an actual WebKit web view with a proper session. Fix focus, OSK activation/dismissal, URL parsing, `https://` default, back/forward/reload, real navigation events, link interception, downloads, persistent storage where safe, response errors, TLS validation, remote site rendering, desktop/mobile user agent responsibly, media permissions and Home/Back lifecycle.

Physical acceptance from actual S10+: open `https://www.google.nl`, type a query using the working keyboard, submit, tap a result, use Back, open a second website, lock/wake, return Home and relaunch. Verify pages are remotely fetched while offline state is accurately shown when Wi-Fi drops. Never declare pass from an iframe screenshot or local `file://` page. Do not disable TLS verification or WebKit sandboxing to make one website load.

## 4.2 Native browsing priorities and realistic acceptance

- **Firefox**: inspect actual Fedora 43 ARM64 package/repo for S10+, install on the **phone** if compatible, launch in correct Wayland user session and verify HTTPS, keyboard, Home and memory usage.
- **Chromium**: similarly verify Fedora ARM64 package and Linux sandbox requirements; don't invoke `--no-sandbox` for acceptance.
- **Google Chrome**: investigate the official **target architecture** package actually available; do not download a wrong-architecture RPM or conflate Chromium with Google Chrome. Record availability honestly.
- **Ladybird**: preferred optional experimental browser. Verify current upstream ARM64/Qt/build and realistic S10+ constraints; attempt bounded, source-verified integration **only after** a working Nuxel Browser + at least one viable mainstream native browser. Do not spend the campaign trapped in pre-alpha browser builds.

If actual working Flatpak isolation is available, test one arm64 Flatpak; if kernel namespace features/portal implementation fail under vendor 4.14, mark blocked and keep safe RPM-native functionality. No insecure bypass.

## 4.3 Unify installed app discovery and launcher

Inventory actual installed/functional PWAs, installed RPM application `.desktop` files, Flatpak exports, app IDs, icons, main binaries, services and needed packages. Build one deduplicated app catalogue with stable IDs, visibility/capability flags, and truthful install/launch status:

`DISCOVERED → INSTALLED → REGISTERED → LAUNCHABLE → ACTUALLY_FUNCTIONAL`.

Do not show broken icons as functional or hide genuinely installed compatible apps because they aren't hardcoded. Preserve Nuxtore integration where present. Watch for cache/service worker drift, wrong base URLs, permissions, relative paths and app-specific Wayland environment. Link **actual** apps to Home/Recents, launch lifecycle and icon metadata. Native GNOME Software or another real ARM64 app store can be integrated where compatible; prove an install/remove cycle rather than merely opening the store UI.

**Gate P4:** Nuxel Browser loads two real websites; ≥1 mainstream compatible native browser runs if package/runtime available; every installed compatible user app appears once and launches; no regression in Home/keyboard.

---

# PHASE 5 — STARTUP READY ON FIRST INTERACTION: BATTERY AND ROTATION

## 5.1 Real battery percentage at boot

Inspect actual `/sys/class/power_supply`, udev, UPower/DBus availability, bridge read path, systemd startup ordering and frontend subscription handshake. Identify the first timestamp that actual `capacity` is readable, versus when it reaches the UI. The correct behavior is: as soon as the hardware source returns a valid value, publish it promptly, subscribe clients, and render exact percentage and matching icon fill. If hardware capacity is not yet exposed, show a dignified **loading/unknown state**, never invented 0%, a lone line or stale percent from previous boot. No two-minute fixed delay. UI initialization must be idempotent and race-safe; make read, event and reconnect behavior correct on every boot.

## 5.2 Canonical seven-mode orientation policy

Implement one enum and one API shared by Settings and Quick Settings:

- `portrait` — fixed 0°
- `reverse-portrait` — fixed 180°
- `landscape` — fixed 90° (define actual orientation on S10+)
- `reverse-landscape` — fixed 270°
- `auto` — 0°, 90°, 180°, 270°
- `auto-portrait` — 0° and 180° only
- `auto-landscape` — 90° and 270° only

Trace live sensor discovery and first available accelerometer samples (`iio-sensor-proxy`/IIO as actually implemented), runtime orientation policy service, saved settings, quick tile menus, compositor transform, framebuffer bridge/presenter and touchscreen coordinate mapping. This MUST NOT degrade to merely two choices named "Locked" and "Auto"; never display literal `undefined`. Settings menu should populate from local schema immediately, while showing honest sensor-ready/unavailable state. On service readiness, synchronize actual mode without dropping early taps.

Do not falsely demand that gyroscope exists as prerequisite for gravity orientation; accelerometer is usually the primary source. Use hysteresis, minimum dwell/angle gating and no jitter when face-up/flat. Respect lockscreen input, keyboard coordinates and app resizing. Verify each fixed 90°/180°/270° transform visually; test real input target hitboxes. For auto, test physical rotations on the actual phone in both restricted submodes. If compositor/legacy framebuffer cannot implement a mode yet, precisely isolate blocked layer and keep a stable supported fallback—not a fake full PASS.

## 5.3 Layout and status-bar correctness

Prevent Wi-Fi/round connectivity indicator overlapping battery percentage/icon or clock. Every icon has a bounded flex/grid slot, spacing and safe-area handling in portrait/reverse/landscape, early boot, carrier absent, charging and oversized labels. Avoid absolute-positioned overlapping duplicates. Ensure no duplicative nav docks and correct Home-only four-app shortcut dock.

**Gate P5:** Within the first reasonable UI-ready interval battery is accurate when kernel data exists; rotation menu offers seven correct values with zero `undefined`; physical transforms and touch mapping meet tested capabilities; top bar doesn't overlap.

---

# PHASE 6 — CAMERA: SAFE, REAL, ESCAPABLE, HONEST

## 6.1 No camera-related user trapping

On Camera tap, display UI immediately. Enumerate hardware asynchronously with a bounded timeout, retry and clear status. `Back`, `Home`, explicit `Close` always work during loading, failed initialization, preview and capture. Lock/unlock remains functional. Camera never grabs permanent exclusive touchscreen/session focus. Stop streams and release devices on app leave/lock; don't induce thermal runaway with repeated polling.

## 6.2 Deliver *two* genuine apps where compatible

1. **Native GNOME Snapshot**: verify `snapshot` Fedora ARM64 package is actually installed on phone, detect its `.desktop` ID and binary, configure correct PipeWire/portals, launch from the Nuxel app drawer as a native Wayland window. If it shows no camera, say so; no fake green.
2. **Custom Nuxel Camera**: keep the A52 `media_store.py` durable file store, the original camera permissions design and truthful bridge capability states. Fix app loading, camera switching, UI controls, snapshots, video paths and Photos integration as far as real system supports. No full-resolution localStorage pretending to be durable images; no synthetic frames as proof of sensor.

## 6.3 Investigate first missing real image frame

Read the latest A52 diagnostics and `HARDWARE-BLOCKERS.md` if available. Observe `/dev/video*`, `/dev/media*`, V4L2/media graph, kernel logs, FIMC-IS/ISP drivers, sensor entity links, firmware/DT dependencies, libcamera pipeline handler availability, PipeWire/portal support and GStreamer capture. Distinguish **sensor enumerated** from **frame streaming**, **JPEG file produced** and **native app launched**. If Exynos kernel/userspace pipeline cannot deliver frame, prepare a bounded, evidence-led driver implementation plan for separate future approval. Do not flash 6.x or attempt register pokes now.

**Gate P6:** Both camera apps are installed/registered/launched/escapable if compatible. Mark real capture **PASS only on physical hardware-origin frames and persistent image files**. Otherwise `HARDWARE_BLOCKED` with exact evidence. Never let camera block navigation.

---

# PHASE 7 — SNEKBYTE NUXEL + ANDROID, NO REGRESSIONS 🐍💩

## 7.1 Restore actual Nuxel PWA launcher

Trace SnekByte Home icon → app registry → installed PWA files → WebKit host → JS engine → first rendered game frame. Ensure correct snake-and-poop icon, valid manifest/service worker URLs, cache versioning, origin/security policy and app lifecycle. Fix blank screen/tap-no-action/console errors and restore actual touch gameplay on phone.

## 7.2 Preserve the newer game rules

- Fast swipe recognition **while dragging**, no need to release finger to register first valid turn.
- D-pad `pointerdown`/touch immediacy; no double event firing.
- Legal two-turn queue supported without illegal 180° reversal.
- User-selectable game speed persisted, applied to *currently running* game when changed, with deterministic tick scheduling.
- **Wraparound:** leaving right enters left, left→right, top→bottom, bottom→top with no wall-death; preserve self/poop collision.
- **Poop-o-meter:** every five actual food items, create the proper persistent WoNQ poop obstacle and reset visible meter.
- Working pause/resume, restart, score retention, Home/Back behavior, offline play, no over-rapid frame loop while paused/locked.

## 7.3 Cross-platform Android support is separately scoped

Where an Android SDK and current source exist on Fedora, reconcile SnakePwn 6000/7000 into a deterministic **debug-signed Android APK**, update shared engine, validate architecture and bundle offline assets, run available automated tests. Device installation acceptance requires a separate actual **Android** target/emulator; the Fedora Nuxel S10+ cannot install Android APKs as native apps. If Android target unavailable, mark `BUILT_UNTESTED_ON_DEVICE` rather than claiming APK runs. Do not delay essential S10+ repairs to solve Android Gradle toolchain problems.

**Gate P7:** SnekByte opens and plays on actual Nuxel, with speed and wrap/poop behavior verified. Android APK build is an independent nonblocking deliverable.

---

# PHASE 8 — SMOOTHNESS, THERMALS AND RESILIENCE WITHOUT NEW REGRESSIONS

Only after functionality is restored, measure before and after:

- Swipe-to-render latency, app launch response, frame pacing, worst-case frame stalls (p50/p95/p99 with realistic instrumentation), CPU/RAM/power idle and lockscreen, and screen-off wakeups.
- Whether `nuxel-wl-fb` or any prior blit/copy/upscale path is still active; monitor actual frame dimensions, throughput and CPU utilization. Do not assume 720p or 1080p changes will solve the bottleneck.
- Video/web/camera and SnekByte won't keep rendering when screen off; suspend/resume and thermal behavior remain safe. Keep governors/thermal protection enabled, no forced max clocks or disabling throttling.
- Native browser and WebKit processes clean up on close/lock; no accumulating ghost windows, WebKit GPU/renderer leaks, zombie camera/PipeWire or NetworkManager reattempt loops.

Set **budgets only from measured baseline and device capabilities**, not invented guaranteed 60 FPS. Make targeted reversible improvements; no wholesale compositor/kernel rewrite. A regression in stability blocks promotion even if FPS improves.

---

# PHASE 9 — SYSTEM DESIGN RULES: FIX ONCE, MAKE IT STAY FIXED

1. **Single source of truth** per component; no duplicate controllers, old handlers or extra launch scripts hidden by UI changes.
2. **Version provenance:** installed runtime files/configs get a build ID/content hash; generated PWA/browser assets use versioned cache invalidation, and the agent verifies *device-installed* code matches intended revision.
3. **Service readiness:** systemd dependencies and explicit health signals, state replay on frontend subscription; no blind sleeps or two-minute startup hacks.
4. **State-machine quality:** monotonic event processing, idempotent/retry-safe operations, bounded timeouts, cancellations and errors that accurately describe current stage.
5. **Native/window compatibility:** app lifecycle, Home/Back/focus/OSK all work for both native Wayland and WebKit PWA windows.
6. **Preserve privacy/security:** saved Wi-Fi secrets to NM secure keyfiles, no secrets in logs, no insecure browser flags, no sandbox removal, no unapproved permanent root debug daemon.
7. **Safe concurrency:** background compilation on Fedora is fine; all mutations on S10+ are serialized and rollback-backed. Never run simultaneous risky native app/compositor service experiments while dependent tests are executing.
8. **Scope:** fix shared infrastructure necessary for the seven missions; avoid unrelated redesign, kernel 6.x migration, splash/artwork modifications, repartitioning or camera firmware hacks.
9. **Truth:** any claim "works" must include exact source commit, deployed hash, physical evidence and measured outcome. No `PASS` from mocks alone.

---

# PHASE 10 — EXECUTION SCHEDULE WITH HARD GATES (NOT ESTIMATES)

Follow dependency-aware order, with checkpoints saved before moving forward:

**Wave 0 — Recovery + evidence:** P0, P1. Confirm Fedora console transport, current runtime and audit.

**Wave 1 — Phone usability:** P2. Unlock/Back/Home/keyboard, camera escape, no navigation duplicates.

**Wave 2 — Real network:** P3. Wi-Fi association + NM auth + IP/DNS/HTTPS, persistent profile.

**Wave 3 — App/browser integration:** P4. Browser real website and app discovery; Firefox and Chromium where compatible; bounded Ladybird investigation.

**Wave 4 — Boot readiness:** P5. Battery and seven rotation modes, status bar.

**Wave 5 — Camera:** P6. Two apps, camera diagnosis, real capture if possible without prohibited kernel work.

**Wave 6 — SnekByte:** P7. Nuxel icon/launch/game input/wrap/speed/poo, optional cross-platform Android build.

**Wave 7 — Reliability/quality:** P8/P9. Thermal/memory/rendering; cross-system regressions; final release gate.

Do not chase any one low-level driver blocker indefinitely. If a task is genuinely constrained by existing vendor kernel, present strongest working partial result and move to the next independent workstream. Never trade a functioning phone for one optional hardware feature.

### Safe deployment discipline

1. All source modifications on isolated Fedora branch/worktree; meaningful atomic commits with unit tests and rollback instructions.
2. For each wave: stage builds/packages in host, verify AArch64 target, back up exact on-device affected paths/configs, transfer over authenticated USB console, verify hashes, restart *minimum necessary* service(s) while keeping out-of-band console alive.
3. Verify physical behavior immediately, before taking the next dependent step. If broken, revert latest wave, verify restoration and record a blocker.
4. Cold boot tests only with owner authorization and proven restore path. No boot/kernel/recovery partition writes.
5. At end, confirm all changes integrated onto one clear release branch; no orphan feature branches or undocumented manual patches on phone. Prepare explicit upstream PRs/commits if requested; do not publish private data.

---

# PHASE 11 — REQUIRED TEST PLAN: USER-OBSERVABLE, PERSISTENT, NO MOCK GREEN

### Automated tests on Fedora (supporting evidence)

- Python bridge tests for NM D-Bus call signature/AP path, state/errors, credentials secure handling, wrong password and delayed events.
- JS/UI tests for initial state, rotation enum, battery source replay, keyboard/back dispatcher and Home native/PWA integration contract.
- Screenshot/layout tests for portrait/landscape status bar and Home-only shortcut dock, plus PWA registry caches.
- SnekByte engine tests for edge wrap all axes, self/poop collision, five-food meter, speed change at runtime, input queue and game suspension; original Python parity where applicable.
- Camera tests with fake/missing device produce honest unavailable UI while navigation remains accessible; file-store durability tests.
- Browser feature tests in authentic WebKit runtime plus native GTK Wayland launch integration.
- Service/systemd dependency ordering, readiness and restart regression tests; no secret leakage in logs.

### Required physical S10+ tests (not substitutable)

| Gate | Physical PASS evidence |
|---|---|
| UNLOCK | 10 real drag-unlocks and short-cancel test, across screen wake and fresh boot |
| NAVIGATION | 10 Penguin Home cycles from WebKit and native windows; Back hides keyboard; long-Back closes only active app |
| SNEKBYTE | Tap actual launcher, play 5 foods / poo spawn, speed adjustment, all 4 edge wraps, input latency visibly improved |
| WIFI | Authorized SSID works 5 connect/disconnect trials; secure saved profile and reconnect after cold boot; wrong-password UI responds |
| INTERNET | On-phone DNS + HTTPS and WebKit `https://www.google.nl` + second HTTPS site, type/search/link/back, browser relaunch |
| NATIVE APPS | Installed compatible Firefox/Chromium/Camera show in Home, launch and escape; Flatpak/Store measured if supported |
| CAMERA | Snapshot and custom Camera responsive + closable; genuine frames only PASS if sourced from sensor and saved media works |
| BATTERY | From boot, record timestamps to first valid kernel capacity and UI percentage; no unexplained 2-minute delay |
| ROTATION | Seven modes selectable from UI; 4 fixed output+touch transforms; auto and restricted modes physically rotated if sensor/pipeline supports |
| STATUS | No overlapping top icons across lock/Home/apps, portrait/landscape and startup |
| THERMAL | No new persistent lockscreen/screen-off heat or runaway loops; explicit measured observations |
| RESTART | At least **3 authorized cold boots** with the core UI/service/network/app tests repeated |

**Two categories of evidence:** `AUTOMATED_TESTED` and `PHYSICALLY_VERIFIED`. Tests performed on an emulator, x86 Fedora host, build container, or synthetic camera do NOT count as S10+ acceptance.

### Final status vocabulary

- `PASS_PHYSICAL` — real device meets requirement.
- `PASS_OFFLINE_ONLY` — source/host tests pass but no physical verification.
- `PASS_PARTIAL` — real subset works; list exact omissions.
- `BLOCKED_DRIVER` — current kernel/device driver cannot provide functionality; cite first failing layer and diagnostics.
- `BLOCKED_DEPENDENCY` — missing package/desktop portal/build runtime, not silently waived.
- `REGRESSION` — feature worked before, new patch broke it; rollback/pause.
- `NOT_TESTED` — no evidence.
- `AWAITING_OWNER` — approval, credential or physical interaction needed.
- `NOT_APPLICABLE` — e.g. Android APK install on Nuxel Linux handset.

Never conflate app presence with genuine hardware capture, menus with rotation, association with internet, or an emulator run with actual S10+ testing.

---

# PHASE 12 — OUTPUT ARTIFACTS AND FINAL RELEASE / STOP CONDITIONS

Write version-controlled nonsecret integration docs under `docs/a63-12kmaximum/`:

1. `00-HOST-AND-DEVICE-IDENTITY.md` — Fedora host and phone evidence, out-of-band recovery, known-good baseline.
2. `01-REFERENCE-CONTRACT-MATRIX.md` — mission 5000 through 11000, exact source files and current implementation status.
3. `02-SOURCE-VS-LIVE-DRIFT.md` — installed hashes, service owners, stale bundles, duplicate handlers and root causes.
4. `03-DEPENDENCIES-AND-REPAIR-ORDER.md` — phase DAG and accountable subsystem owners.
5. `04-IMPLEMENTATION-CHANGELOG.md` — actual diffs, commits, tests and rollback per wave.
6. `05-WIFI-AND-BROWSER-EVIDENCE.md` — sanitized auth/association/IP/DNS/HTTPS and on-phone browser tests.
7. `06-APP-REGISTRY-AND-CAMERA-EVIDENCE.md` — installed/registered/functional app inventory, Snapshot, custom camera, genuine image pipeline findings.
8. `07-ROTATION-BATTERY-STARTUP-EVIDENCE.md` — timestamps, seven mode tests, touchscreen mapping and status bar screenshots.
9. `08-SNEKBYTE-INTEGRATION-EVIDENCE.md` — canonical engine, gameplay tests, real phone and separate Android APK evidence.
10. `09-LOCK-NAV-KEYBOARD-TESTS.md` — recovery/UI input/camera escape.
11. `10-THERMAL-PERFORMANCE-REGRESSIONS.md` — measured before/after and remaining risks.
12. `11-PHYSICAL-ACCEPTANCE.md` — owner test checklist, per-gate status and supporting logs/screenshots, 3-boot validation.
13. `12-ROLLBACK-RUNBOOK.md` — exact verified restore commands, service order and host backup location.
14. `13-RELEASE-READINESS.md` — no invented 100% score; blocker severity, owner acceptance and next-step roadmap.
15. `acceptance.json` — machine-readable gate IDs, `status`, `evidence`, `source_commit`, `deployed_hash`, `physical_test`, `blocker` and `rollback` fields.

Before final handoff show a concise matrix with all seven mission numbers (5000–11000), plus the cross-cutting 12K reliability gates. Each row must include **real state, next action, evidence, owner impact**. Do not mark a feature "complete" when only its service compiles or UI button renders.

## HARD STOP / ROLLBACK CONDITIONS

Stop the relevant operation and restore its last-known-good userspace state if:

- USB Live Console / trusted alternate access is at risk.
- Nuxel cannot unlock or return Home.
- A service restart causes GUI/phone to hang with no proven recovery route.
- Wi-Fi changes compromise host Fedora connectivity or erase saved connections.
- Any step requires kernel/bootloader/partition flashing, disabling real security boundaries, or private signing keys.
- Camera/graphics/network experiments produce dangerous heat or continuous CPU wake loops.
- A full-screen native app traps the user, or a new patch regresses the already-working SnekByte game.
- A claimed `PASS_PHYSICAL` cannot be supported by an actual phone observation.

When an owner action is essential (unlock, type their Wi-Fi password, inspect HDMI/camera physically, approve controlled reboot), pause only that affected action and continue independent safe work. Never claim owner input was received without it.

## FINAL EXECUTOR DIRECTIVE

**Don't make me another seven impressive reports with broken buttons on the phone. Make Nuxel actually behave as one coherent operating system.**

Read the reference prompts, inspect the live S10+, identify integration and deployment drift, fix shared roots first, apply small reversible changes, physically validate and keep each improvement after reboot. Integrate all feasible components from **SnakePwn 5000 → Penguin Online 11000** under one verified Nuxel release. Report kernel/ISP/vendor blockers without pretending they are solved. Keep the proven 4.14 baseline and recovery console untouched.

**OPERATION 12KMAXIMUM — ONE PENGUIN, ONE STACK, ZERO FAKE GREENS. 🐧🔥🐍💩🌐📸**
