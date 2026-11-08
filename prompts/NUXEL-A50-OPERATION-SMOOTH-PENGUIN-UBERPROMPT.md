# 🐧⚡ NUXEL A50 — OPERATION BUTTER-SMOOTH PENGUIN
## Comprehensive latency, rendering, touch, launch, animation, power and display-pipeline optimization mission

**Executor:** DeepSeek-v4-pro-thinking (preferred) or a similarly capable coding agent with access to the current Nuxel checkout, compiler/toolchain, and live Galaxy S10+ diagnostic console.

**Target:** Samsung Galaxy S10+ **SM-G975F**, `beyond2lte` / Exynos 9820, running the existing **Nuxel Fedora ARM64 + Wayland/Phoc + WebKitGTK** environment.

**Objective:** Make Nuxel feel **immediately responsive** to finger movement, taps, app launches, app-switching, Back/Home/Recents, the shade, lockscreen and keyboard. Deliver a visibly fluid phone through **measured, reversible** optimizations to the actual critical path; preserve correctness, battery life, screen-off power state, visuals and recovery access.

**Prime directive:** Optimize *time from physical touch to visible and interactive feedback*, not superficial benchmark scores. No fabricated FPS, no artificial UI delays to hide lag, no infinite CPU/GPU polling, no maximum-frequency governor left enabled, no unsafe mode changes, no made-up hardware acceleration.

**Execution sequence:** inventory → live identity & baseline → stage-by-stage latency analysis → low-risk improvements → pipeline optimization → resolution A/B tests only if worthwhile → benchmark → thermal + sleep acceptance → safe deployment → physical demonstration → rollback.

---

# 0. VERY IMPORTANT PRIOR TECHNICAL EVIDENCE (NOT PROOF OF CURRENT CONFIGURATION)

An **older v0.6.3-beta repository snapshot**, inspected before writing this prompt, includes the following relevant concrete artifacts and technical observations:

- `services/nuxel-session/systemd/nuxel-wayland.service` runs **Phoc** via `WLR_BACKENDS=headless,libinput`, `WLR_RENDERER=pixman`, `WLR_HEADLESS_OUTPUTS=1`, with a `libinput` discovery shim. Its comments say the old vendor kernel had `CONFIG_DRM` unset, making **headless software composition** the supported path on that build.
- `tools/s10plus/a29/phoc-phone.ini` documents an output of **720×1520, scale 2**, intended to yield a mobile layout. **Distinguish compositor pixel dimensions, logical coordinates and CSS viewport width**.
- `configs/s10plus/display/nuxel-s10plus-display.sh` references the S10+ AMOLED physical resolution **1440×3040**, and attempts `wlr-randr`; the physical panel mode **must not** be assumed changeable from an unrelated headless Wayland output.
- `tools/s10plus/a34/nuxel-wl-fb.c` is a Wayland `zwlr_screencopy_manager_v1` → shared memory → `/dev/fb0` presenter, resizing/copying an image to a physically larger panel and converting pixel format. It contains a paced frame loop, `FBIOPAN_DISPLAY` behavior, framebuffer handoff protections and a single-writer contract.
- `docs/s10plus-autonomous-boot-repair/TOUCHDOWN/DISPLAY-REFRESH-ROOT-CAUSE.md` recorded a **previous** ~23.67 FPS with **43 ms** average blit time, `out=720x1520 scale=2 panel=1440x3040`.
- `docs/s10plus-autonomous-boot-repair/BETA-FINALIZER/06-FRAMEBUFFER-OWNERSHIP.md` recorded a later **previous** ~28 FPS, **34 ms** average blit, and exclusive framebuffer ownership. It says the bridge's default target was 30 FPS and documents historic failures when two framebuffer writers overlapped.
- `pwa/nuxel-home/js/launcher.js` implements pointer-driven desktop transitions and contains `void grid.offsetWidth` to force a transition restart at a specific time: audit whether any forced layout causes jank under current usage.
- `pwa/nuxel-home/js/app.js` manages same-origin application iframe lifecycle, and the launcher/home has multiple CSS animations/transitions.
- `docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md` describes existing device soak infrastructure and measurable CPU/memory, WebKit, Phoc, framebuffer bridge and thermal counters. **Reuse it rather than inventing an unrelated, unbounded daemon.**

**These are historic reference points, not confirmation of today's deployed build.** A45–A49 may have changed runtime behavior. First inspect current files, running binary hashes, systemd units, device state, display dimensions and measured FPS. If the live pipeline differs, adapt. Do not overwrite newer fixes with old A34 artifacts.

**Core hypothesis to test:** On this S10+, the bottleneck may be the **software compositor + wlr-screencopy + CPU pixel-format conversion/upscale + fbdev page commit** path, not primarily the PWA UI or panel's native resolution. Trace and measure each stage before choosing optimizations.

---

# 1. SAFETY CONTRACT, WORKTREE AND OWNER VISIBILITY

1. Preserve a known-good USB recovery console throughout. Determine whether the S10+ is currently booted in Nuxel, TWRP or another mode; do not assume it is booted. If TWRP, do read-only checks and ask the owner before rebooting into Nuxel for performance measurements.
2. Confirm device identity (`SM-G975F`, `beyond2lte`/`universal9820`) and capture exact git branch, SHA, dirty changes, target binaries, relevant unit files and running environment values. **Deployed binary may not equal repository source**.
3. Create a dedicated Git branch or isolated worktree for A50. Preserve any concurrent hardware/display/lockscreen mission, especially A49 rotation changes and the A46.x boot artwork.
4. Establish versioned **userspace backups** and SHA-256 for all replaced binaries, CSS/JS, config and service files. Capture the current display/headless mode, scale and parameters. Create a tested, console-executable revert command/script **before** changing the screen.
5. **No flashing**, partition modification, vendor kernel replacement, device-tree flashing, bootloader changes, DRM-driver experiments on the boot partition, boot artwork changes, TWRP work, auto-overclock, voltage modification or bypass of thermal controls.
6. Never disable temperature protection, kernel watchdogs or power-management security. No permanent `performance` cpufreq governor. No disabling SELinux/AppArmor to chase an FPS number. No random `sysctl`/scheduler recipes without measurement and an evidence-backed rollback.
7. Keep the existing correct lockscreen, keypad/OSK, Back/Home/Recents semantics, button long press, Wi-Fi, battery reporting, speaker if functional, sensors/rotation, power menu and custom graphics intact.
8. No high-frequency diagnostics daemon shipped by default; no debug input trace logging always-on; no permanent browser inspector in production mode.
9. If the display becomes blank/frozen, immediately use verified recovery to restore the last known good userspace components. Do not blindly restart the display stack in a loop.
10. **Never make performance change at the cost of persistent warmth in pocket or when locked with screen off.** Locked/screen-off behavior is a pass/fail condition.

**Stop gates:** absent recovery path; unidentifiable display owner; unsafe unsupported display mode; growing thermal load without throttling-safe fallback; a regression causing missed touch or inability to unlock; need for kernel/partition changes; or physical results that cannot be verified.

---

# 2. DEFINE SUCCESS IN NUMBERS BEFORE MODIFYING CODE

Create `docs/performance/A50/` containing scripts and immutable baseline artifacts. Sample under **repeatable** conditions: same battery/charging state when possible, screen brightness, orientation, Wi-Fi, active apps, thermal starting temperature and CPU workload. Record ambient context qualitatively; do not label uncontrolled measurements scientific.

Produce `A50-BASELINE.json`, `A50-BASELINE.md` and unmodified trace files with timestamps and hardware/build identifiers.

Measure, with a reproducible harness and at least **10 repetitions** for user-interaction timings where practical:

### Responsiveness scenarios

| Scenario | Start event | End event |
|---|---|---|
| Home horizontal swipe | physical pointer down / first movement | first visible response, then settled desktop |
| App-grid scroll / drawer open | physical gesture start | first glass update and complete transition |
| Quick Settings swipe | input start | first updated pixels, then fully interactive shade |
| Home app launch (cold) | tap on app icon | application paints meaningful, interactive content |
| Home app launch (warm) | tap | application ready to accept input |
| App switch via Recents | tap | switched app first live frame and input ready |
| Penguin Home | tap | Home frame ready and interactive |
| Back dismiss keyboard | tap | OSK truly hidden and app contents restored |
| Lockhead unlock | swipe/release | unlock acknowledged + Home/previous app accepts touch |
| Settings list scroll | gesture start | response and missed frame distribution |
| 5-minute continuous normal use | session start | stutter, CPU, memory, temperature and responsiveness |

Use **median and p95**; show cold and warm separately; timestamp **touch-to-handler**, handler-to-app-ready, compositor render, screencopy availability, blit, commit, and ideally **glass-visible** with an external high-frame-rate camera / equivalent timing method. Software tracing alone cannot prove glass photon timing. Distinguish exact timestamps from inferred timing; label camera results separately.

### Rendering and system metrics

- Actual displayed frames per second, p50/p95/p99 frame intervals, duplicate frames and long-frame percentage; not merely the requested `NUXEL_TARGET_FPS`.
- Capture, format convert/upscale, page-flip/pan and waiting/idle durations **separately** per frame.
- Screenshot/compositor output dimensions, panel framebuffer dimensions, bytes per pixel, stride, pixel order, physical refresh-rate modes and logical UI width.
- System CPU%, per-process CPU%, per-core load, actual governors/frequencies where readable, GPU driver availability, renderer backend, memory pressure, swap, I/O stalls and service restarts.
- WebKit UI process usage, number of WebKit processes, JS scripting/layout/paint cost and heavy animation assets.
- Display on/locked/screen-off power behavior, temperatures over time, whether compositor/blit loops continue in background.
- Input drop/loss, double-handlers, callback duration, queue depth if measurable.
- Wi-Fi, battery and performance metric refresh rates: stale state can also produce visually laggy interactions.

**Aspirational targets (not fabricated promises):** Aim for **60 FPS** only if the present driver + display pipeline can actually sustain it without increased heat or power cost. If not, deliver a stable **30 FPS** with consistent pacing and low input latency, or **45 FPS** only when measured and supported. Prefer stable frame pacing to a fluctuating nominal 60 FPS. Target >=25% improvement in p95 user-visible latency on bottleneck scenarios when feasible, with no correctness/thermal regressions. Explicitly report hardware ceilings and impossible goals.

**Useful frame budgets:** 60 FPS = 16.67 ms/frame; 45 FPS = 22.22 ms/frame; 30 FPS = 33.33 ms/frame. End-to-end budgets include all pipeline stages and synchronization—not just `memcpy` time. If the whole per-frame bridge remains >33 ms, lifting FPS to 60 is not a solution.

---

# 3. DISCOVER ACTUAL DISPLAY RESOLUTION, NOT A GUESS

The user is open to lowering effective rendering resolution to 720p-class or 1080p-class *if that genuinely makes the device smoother*.

**Important distinction:** The physical Galaxy S10+ OLED panel is specified at **1440×3040** in the previous Nuxel sources. The old Phoc session **already rendered headlessly at 720×1520**, while the bridge upscaled pixels to the native panel. Its Wayland output scale was 2; that's not equivalent to simply running a 1440-pixel-wide full compositor. Check current behavior afresh.

Read-only checks where supported:

```sh
cat /etc/nuxel/phoc-phone.ini 2>/dev/null || true
systemctl cat nuxel-wayland.service nuxel-wl-fb.service 2>/dev/null || true
systemctl show -p MainPID nuxel-wayland.service nuxel-wl-fb.service 2>/dev/null || true
wlr-randr 2>&1 || true
ls -l /dev/fb* /dev/dri/* 2>/dev/null || true
for f in /sys/class/graphics/fb*/virtual_size /sys/class/graphics/fb*/bits_per_pixel /sys/class/graphics/fb*/stride; do test -r "$f" && { echo "$f"; cat "$f"; }; done
cat /run/nuxel-wl-fb.state 2>/dev/null || true
ps -ef | grep -E '[p]hoc|[n]uxel-wl-fb|WebKit' || true
```

Additional diagnostics: inspect real `/dev/fb0` via `FBIOGET_VSCREENINFO` and `FBIOGET_FSCREENINFO` with safe read-only code; inspect wlroots headless output; check which scale and pixel dimensions WebKit actually renders; verify any ARM GPU/DRM path with evidence, never assume one is enabled.

### Controlled comparison matrix — only configurations the actual stack supports

| Candidate | Compositor buffer | Practical interpretation | Cautions |
|---|---|---|---|
| **Current deployed** | measured | **Baseline, must preserve** | Can be already 720×1520 |
| **720-class** | 720×1520 | Historic baseline; ~1.09M compositor pixels | Physical panel still native; bridge has to upscale |
| **1080-class** | 1080×2280 | ~2.46M pixels | May worsen software composition/upscale and change CSS scale |
| **Native-class** | 1440×3040 | ~4.38M pixels | May be substantially slower on CPU/software renderer |
| **540-class** | 540×1140 | ~0.62M pixels | Only experiment if current bridge/render stage is truly constrained; can impair readability |

These are **candidate buffer sizes**, not evidence that a specific physical AMOLED output mode is supported. Modes must preserve the panel aspect ratio. A headless-output mode switch is not a Samsung panel timings change. If the OLED's supported modes differ, do not force timings or power-cycle it experimentally.

**Make an A/B benchmark for the exact active backend**: resolution × scale × FPS cap; measure glass results, text clarity, responsiveness, CPU, blit time, power and temperature. Do not assume lower headless resolution automatically accelerates the bottleneck: the current bridge still writes a ~1440×3040 framebuffer, which can dominate bandwidth and CPU.

Retain a similar **logical CSS viewport** (and safe touch targets) where feasible; carefully set Wayland output scale and/or app UI scaling. Revalidate status bar, keyboard hitboxes, device rotation, Home swipe coordinates, lockhead threshold, wallpaper, app grids and touch calibration whenever sizes change.

**Pick whichever measured profile is objectively better**, not whichever has the smallest number. If no tested mode wins, retain the original.

---

# 4. CRITICAL PATH A — ANALYZE AND OPTIMIZE `nuxel-wl-fb`

Find the **live** source behind `/usr/lib/nuxel/nuxel-wl-fb`, which may be newer than `tools/s10plus/a34/nuxel-wl-fb.c`. Capture exact binary SHA-256, compile flags and any `NUXEL_TARGET_FPS` config. Read previous A31–A35 frame-ownership and panel-specific color/pan notes. This pipeline is especially safety-critical.

### Instrument the real frame lifecycle

Timestamp and profile individually:

1. Time the compositor commits a completed frame (if exposed).
2. Bridge issues screencopy request.
3. Screencopy buffer becomes ready.
4. Optional buffer copy, scaling and pixel format conversion.
5. Framebuffer mmap write completion.
6. `FBIOPAN_DISPLAY` / supported commit, and any blocking time.
7. Page present acknowledgement if driver exposes one, versus approximate timing.
8. Idle interval; CPU active time; screen-off state.

Sampling only totals is insufficient. Trace p50/p95 and hotspots while swiping and when idle, using low-overhead logging in a bounded benchmark configuration. Distinguish *real* new frames from loops copying identical buffers. Use monotonic timestamps. Avoid `fprintf`/file open per frame in release builds.

### Explore optimizations in order of measured payoff

**A. Avoid work when nothing changed.** Inspect screencopy protocol support/version and damage callbacks, but do not assume that a damage notification maps directly to safe partial AMOLED commits. If no valid changed content, avoid redundant conversion/upscale/FB commits where the phone still displays the last frame correctly. Measure wakeup and responsiveness afterward. No sleeping through the next genuine touch frame.

**B. Correct buffer lifetime and reuse.** Reuse allocated shared-memory buffers, precomputed scaling tables and compatible output buffers if protocol and synchronization permit. Avoid reallocating an entire per-frame buffer, copying stale memory or racing a buffer still owned by the compositor. Verify all stride/format and dimension changes; only reuse when size/format compatibility is proven.

**C. Optimize scaling and colors in the actual inner loop.** Preserve the **measured Samsung DECON pixel byte order** and opaque alpha semantics; do not break the already-correct colors. Consider optimized row reuse, nearest-neighbor 2× expansion, pointer/stride arithmetic, precomputation, efficient conversions and CPU-compatible ARM NEON **only if measured safe on this SoC**. Verify output pixels against original using deterministic test frames including red, green, blue, alpha, gradients, full-screen text, portrait/landscape and partial updates. Measure runtime performance and temperature. Do not trade correctness for SIMD speed or rely on misaligned/undefined accesses.

**D. Reduce framebuffer bandwidth if driver actually supports it.** Full panel at 1440×3040×4 bytes is about **17.5 MB/frame decimal**. At 30 FPS, that is ~525 MB/s of framebuffer writes alone, before compositor, read, format conversion and memory traffic; at 60 FPS it's over ~1 GB/s. Investigate actual DMA/framebuffer constraints. Partial damage writes, tiled updates, dirty regions, alternate allocation or more efficient format are valid only with proven driver support and no tearing/ghost pixels. Do not assume `FBIOPAN_DISPLAY` accepts safe partial commits.

**E. Pacing and freshness.** Investigate current frame acquisition and throttling strategy. A stale queued frame can make swipes feel delayed even when average FPS is acceptable. Prefer the newest complete frame as soon as the physical stack can show it, with bounded buffer ownership and no skipping intermediate state transitions the UI actually requires. Evaluate double/triple buffering only with safe synchronization and measured benefit. No unbounded busy loop.

**F. Hardware acceleration feasibility — research only unless supported live.** Verify whether currently deployed kernel exposes usable Mali DRM/render nodes and a compositor backend. Historic source says `WLR_RENDERER=pixman`, `WLR_BACKENDS=headless,libinput`, kernel `CONFIG_DRM` absent. If that's still true, don't flip `WLR_RENDERER=gles2` or attempt `WLR_BACKENDS=drm` and brick the display. A native direct-DRM/KMS path may require a future kernel migration and is **not authorized** in this userspace mission. Document it as A50 future architecture if appropriate.

**G. Validate single display owner.** Respect boot animation → launcher handoff and panel brightness/power transitions. Exactly one process is allowed to own `/dev/fb0` in normal operation; confirm with live evidence. Do not revive old competing writers or repeated `FBIOPUT_VSCREENINFO` calls. Preserve the boot animation and correct display color even through service restarts.

### Profile promotion rules

After each change: compile with target AArch64 flags, run unit/ASan/UBSan-style checks where feasible on host test harness, run test frames and alpha/color comparisons, validate error handling, deploy as one reversible change, physically test. Keep optimizations only if a statistically credible improvement and no visual/power regression. Compare `before vs after` performance under the same thermal conditions.

---

# 5. CRITICAL PATH B — TOUCH INPUT → UI FEEDBACK

Trace actual libinput/evdev arrival to Phoc/wl_touch to WebKit DOM event to launcher handler to rendered frame. The touchscreen **already works**; don't rewrite its driver. Find whether latency comes from touch sampling, input queueing, a long-running main-thread task, animation timing or display-presentation latency.

Look for:

- Pointermove dispatched but rendered response delayed by an animation backlog.
- Duplicate pointer/touch listeners or passive/non-passive event misuse.
- Excessive per-move DOM queries, `elementsFromPoint`, expensive tracing, forced layout and synchronous style measurements.
- `preventDefault()` or `touch-action` rules causing input arbitration delay or breaking scroll.
- Excessive handlers for the same swipe that trigger duplicate actions.
- Visible response only on `pointerup` when a drag should follow movement immediately.
- Heavy work inside click handlers before the pressed state or loading affordance paints.
- Gesture recognition after a blocking WebKit bridge request.

**Implementation constraints**:

- UI feedback to finger should happen on next presentable frame where possible; use `requestAnimationFrame` for visual position updates, `transform: translate3d` where measurably useful, and coalesce pointer-move work to at most one visual update per frame. Do not coalesce away state needed for gesture threshold accuracy.
- Avoid layout thrash: separate DOM reads/writes; cache stable dimensions and refresh after rotation/resizes rather than reading layout after every write.
- Correct capture/release/cancel handling for touch; preserve long Back vs short Back vs OSK-dismiss interaction and Penguin Home action.
- Don't globally disable scrolling inside apps just to speed Home gestures.
- React quickly when tapping an icon, but never claim it opened until interactive; show honest immediate visual feedback if actual app initialization takes time.

**Critical regression protection:** The penguin lockhead drag and unlock must still work; no invisible overlay over the Home dock; physical Back/Home/Recents behaviors unchanged; keyboard appears and dismisses as intended.

---

# 6. CRITICAL PATH C — NUXEL HOME, WEBKITGTK, JS AND CSS

Inspect actual current implementations, especially:

- `pwa/nuxel-home/js/launcher.js`
- `pwa/nuxel-home/js/app.js`
- `pwa/nuxel-home/js/apps.js`
- `pwa/nuxel-home/css/style.css`, associated launcher, dock, Quick Settings and lockscreen styles
- `shell/nuxel-home-native/` and its WebKitGTK host/webview lifecycle
- service-worker/cache-version logic and app routes
- Nuxel Bridge system queries and polling cadences.

### Optimize deliberate work, not visual identity

1. Inspect WebKit console logs, JavaScript error frequency, main-thread long tasks (where supported) and layout/repaint cost. Remove accidental heavy work; don't disable needed functionality.
2. Profile desktop wallpaper, bottom bar background art and app icon sizes. **Decode once and reuse**; resize enormous image assets to appropriate effective display dimensions only when verified lossless-enough visually, keep original assets in source, retain transparency/pixel-art styling and existing branding. Verify memory and visual before/after.
3. Use `transform`/`opacity` transitions rather than animating costly layout properties where appropriate; test compositing behavior under pixman/software rendering since GPU promotion may not be available.
4. Reduce unnecessary box-shadow/filter/backdrop-filter/fullscreen blur and massive overlapping translucent elements only if profiling proves costly; preserve visual style with measured alternatives.
5. Eliminate synchronous layout reads immediately after writes in hot paths; review the known `void grid.offsetWidth` launcher transition restart, replacing or constraining it if proven costly.
6. Consolidate repeated timers/polling. When the phone is idle, lockscreen shown, or display off, suspend UI animations and non-essential refresh loops. Avoid continuous CSS animations with no user-facing benefit on the locked screen; if the penguin lockhead wiggles, pause it when screen is off, and keep the lock gesture responsive.
7. De-duplicate event handlers and service-worker version conflicts that can revive stale code after restart; synchronize code/cache version so deployed optimization survives cold boot.
8. Prevent large synchronous JSON parsing, blocking bridge requests, filesystem scans or network fetches on the UI input thread; use async work plus real cancellation/timeout.
9. Make Quick Settings, status bar and meters update only at sane rates and only while needed. CPU/RAM percentage should not cost more CPU than the feature displays. Battery percentage must remain real and persist through reboot (recent A48 regression protection).
10. Audit WebKitGTK rendering options supported on this actual package/runtime; don't set obsolete or undocumented flags or enable experimental features just because a blog says they're fast.

### Preserve existing UX exactly

- Home icon arrangement, wallpaper, lockscreen, lockhead art, boot splash/spinning penguin, navigation buttons, four Home-only app dock shortcuts, and current keyboard theme must not be restyled or substituted.
- No removing haptics, navigation, sound, Wi-Fi, sensors, casting or power controls to improve FPS numbers.
- Maintain accessibility/touch target sizes, readable text and high-contrast status indicators.

---

# 7. CRITICAL PATH D — APP OPENING, WARM START AND TASK SWITCHING

Audit the real app lifecycle and routing before proposing caching/preload changes. Older `app.js` uses same-origin iframe-based app surfaces; newer versions may differ. Detect cold startup causes such as iframe creation, HTML/CSS asset fetching, blocking initialization, repeated imports, system state fetches, service worker cache misses and unnecessary teardown/recreation.

### User-visible success properties

- **Tap acknowledgment** is immediate, without blocking the UI thread.
- **Meaningful first paint** comes as soon as available; no long black/blank app frame when data has not loaded.
- **Interactive ready** occurs after actual app initialization, measured independently from first paint.
- A previously opened app should resume quickly **without losing its current state** when practical.
- Closing via long Back actually terminates only the foreground app, not all applications or the Home controller.
- Recents and Home switching must not spawn duplicate app views or leave invisible blockers.
- If apps are kept in memory, choose bounded policies based on measured RAM/memory pressure; no unbounded background iframes or eager loading of every app.

### Candidate optimizations

- Preload a *small measured subset* of core Home/app assets after the launcher is responsive, not at the cost of delaying first interactive Home.
- Cache-bust correctly when deploying changed assets. Preserve offline operation; no hidden cloud dependencies.
- Reuse mounted app surface or warm process when it is safe and meaningfully faster; suspend hidden application timers/network animations where practical. Verify lifecycle and state restoration.
- Use atomic app lifecycle transitions `CLOSED`, `STARTING`, `ACTIVE`, `BACKGROUND`, `STOPPING` (adapt to actual code) rather than multiple competing flags; ensure no duplicate opens from tap and fallback synthetic click.
- Optimize app registry lookup and DOM insertion. Avoid huge synchronous file read on each launch.
- Add real timeouts and visible retry/error states for apps that cannot load; never report a blank iframe as success.
- Optimize Settings, Browser, Files and other actual apps with the slowest measured p95 separately; don't blanket-defer functionality.

---

# 8. FRAME PACING AND MOTION DESIGN — FAST WITHOUT FEELING JITTERY

Smooth UX requires *consistent frame intervals and immediate gesture response*, not animations that merely take longer.

- Tune desktop swipe motion for correct finger tracking and a short, coherent settling animation. Avoid unnecessarily long spring or ease-out tails that block subsequent taps.
- Standardize typical UI transition times based on measured responsiveness (e.g. ~120–220 ms for simple panels), but do not blindly impose fixed animation length when a component needs a different affordance.
- Support reduced-motion settings and ensure touch processing never waits for a decorative transition to end.
- Use rAF for active movement; disable continuous animations when covered, backgrounded or screen-off.
- Do not force 60Hz rendering if the bridge is capped to 30 FPS; choose animation steps and updates that avoid visible duplicate/jitter frames.
- Investigate animation vsync and screen update timestamps; record delivered vs requested frame rate and frame-time variance.
- No CSS/JS visual tricks to pretend content is ready while input remains blocked. A subtle honest progress affordance is acceptable.

---

# 9. KERNEL-SAFE CPU, MEMORY, STORAGE AND NETWORK TUNING

Apply only measured, scoped and reversible tuning without destabilizing the aging vendor kernel.

### CPU and scheduler

- Inventory `scaling_governor`, available governors, cpufreq policy clusters, temperatures and throttling states. Do not force full clocks permanently or keep CPUs awake during screen-off.
- If the current governor causes excessive wake-to-first-frame latency, evaluate **short-lived interaction boosts** only if an existing safe facility supports them and a cold-start A/B benchmark justifies them; limit boost durations and preserve thermal protections. Otherwise prefer reducing CPU work over forcing clocks.
- Investigate compositor, bridge and WebKit process affinity/priority only when CPU trace evidence shows starvation. Do not indiscriminately apply `chrt -f`, `nice -20` or realtime priorities that can starve input, audio and core services.
- Consider actual SoC memory/cache behavior when optimizing hot loops; do not copy x86 compiler flags to ARM64.

### Memory

- Check that the ~800 MB RAM baseline remains reasonable; record **MemAvailable**, cgroup pressure, WebKit processes and framebuffer allocations, not naive sum of per-process RSS.
- Avoid leaking `wl_buffer`, mapped shm pages and WebKit subprocesses across app switches.
- Eliminate repeated full-size intermediate buffers only with correct ownership/lifetime tests.
- Don't disable zram/swap blindly or introduce aggressive OOM policies that kill foreground apps.

### Storage and file access

- Profile actual FS reads, synchronous `fsync`, logging and asset fetches in cold app launches. Cache assets when justified; don't disable persistence or data safety to make opens appear fast.
- Ensure logs are rate-limited and bounded. Avoid a per-frame write to `/var` or a high-frequency JSON filesystem poll.

### Network

- Only tune Wi-Fi/network-dependent apps after separating local launch from DNS/TLS/network delays. Preserve working Wi-Fi association and avoid needless background polling or reconnect loops.

---

# 10. SCREEN-OFF, THERMAL AND BATTERY: MUST GET BETTER OR STAY SAFE

This phone previously became **very warm at the lockscreen or with display off**. Therefore:

1. Measure baseline idle (Home), locked-screen-on, locked-screen-off and waking/return states. Use device thermal sensors where interpretable; if calibrated sensors are absent, state that limitation and use qualitative caution.
2. Determine whether `nuxel-wl-fb` continues requesting/copying frames while the panel is blanked; whether Phoc/WebKit render continuously; whether lockhead wiggle or wallpaper animation keeps the CPU active; and whether fast service retries prevent suspend.
3. If safe and supported, make panel blanking **stop unnecessary frame acquisition/copy/pan** while retaining reliable immediate wake and correct frame re-presentation. Do not assume `brightness=0` means hardware powered off; historic bridge comments note the panel's `bl_power` behavior.
4. Ensure lockscreen state/idle clock services continue functioning during screen-off without generating unbounded graphical work.
5. Wake validation: first frame correct (no stale black frame), touch/key response immediate, lockscreen remains locked until valid unlock, no restart storm.
6. Stop/rollback if sustained device warmth or verified thermal behavior worsens. Do not raise thermal thresholds, disable governors, or bypass throttling.
7. Soak test for bounded **15 minutes screen-on interactive** and **15 minutes screen-off locked** when practical; longer owner-approved soak later. Compare per-process CPU, thermal curves and battery trend under controlled comparable conditions.
8. If immediate overheating risk is present, suspend performance experiments and diagnose thermal/power first.

---

# 11. BUILD AND DEPLOY SAFELY ON THE LIVE PHONE

### Preferred host workflow

Fedora laptop is a convenient Linux development/build environment; MacBook can remain the known-good USB recovery host. Choose the currently connected, trusted console rather than trying to give two host programs the same serial endpoint. Native Linux userspace and target binaries are ARM64/AArch64; cross-build with matching sysroot/ABI if host is x86-64.

### Deployment strategy

1. Confirm exact source → binary mapping and currently running service versions.
2. Back up files and document exact restart/rollback sequence.
3. Build/test locally with strict compiler warnings and format/stride/ownership tests.
4. Apply changes by one small subsystem at a time, beginning with **read-only instrumentation**.
5. Deploy the minimum user-space files via verified console/file-transfer method. Confirm SHA-256 and executable permissions.
6. Restart only relevant services; warn the owner before graphics interruption. Leave the USB console intact.
7. Verify Home, lock/unlock, keyboard, navigation and physical display within seconds. If display is inaccessible, restore immediately and restart the known-good stack.
8. Repeat the same benchmark. Reject changes that only look faster while FPS or latency metrics worsen.
9. Validate one clean boot/restart **only after explicit owner approval**. No reflashing. Check settings, service units, executable paths and cache survive restart.
10. Keep a production configuration containing only evidence-supported knobs; diagnostics off by default.

### Reproducible perf mode

Create a clearly marked, opt-in bounded diagnostics script, e.g. `tools/perf/a50-benchmark.sh` with:

- `--duration` and hard max.
- `--baseline` or `--candidate` modes.
- Safe read-only default; no kernel adjustments.
- CPU, bridge, WebKit, app lifecycle, frame pacing and thermal snapshots.
- Machine-readable JSON/CSV and Markdown human report.
- Missing sensor/perf API outputs as `UNAVAILABLE`, never zero unless measured zero.
- Exit code that distinguishes `PASS`, `REGRESSION`, `BLOCKED` and `INCOMPLETE`.
- No uncontrolled USB log flood or background processes after exit.

If safe automated touch injection is not available, use manual physical gesture tests with consistent instructions and external footage; do not fake events then call them physical proof.

---

# 12. A/B PLAN AND SELECTION LOGIC

Use a small **evidence matrix** rather than turning everything on at once:

| Experiment | Independent variable | Keep constant | Promotion condition |
|---|---|---|---|
| E0 | Baseline | all known conditions | establishing truth |
| E1 | Bridge hot-loop optimization | display size, FPS cap | faster blit, same pixels and thermals |
| E2 | Screencopy/buffer reuse | resolution, UI assets | lower p95 frame cost, no stale frames |
| E3 | UI gesture/layout changes | display path | lower input-to-first-paint latency |
| E4 | Warm-app lifecycle improvements | memory/power ceiling | faster interactive launches, no app state loss |
| E5 | 720/1080/native/540 buffer trials | renderer and workload | objectively best responsiveness/clarity/power |
| E6 | 30/45/60 FPS cap if available | resolution and apps | stable frame pacing and thermal safety |
| E7 | idle/wake scheduling | graphics correctness | less locked/off CPU, fast wake |

Change one variable per experiment, collect evidence, and merge only winners. Where performance effects interact, run a final consolidated test to detect regressions. Do not cherry-pick a single best benchmark run; use median, p95, and reproducibility.

### Minimum performance criteria

- Baseline/after report includes an honest, measured breakdown of the largest bottleneck.
- For representative navigation and app-opening tasks, either record a credible meaningful reduction (aim for >=25% p95 on problematic paths) **or** explain the limiting hardware/software stage.
- No lower glass-visible frame pacing quality, accidental input lag, text blurriness severe enough to impair usability, stutter or torn frames.
- No regression in average/peak CPU under screen-off, thermal behavior, suspend/resume or battery service reliability.
- No missing frames during unlock, app open, rotation or keyboard appearance.
- Memory doesn't grow without bound across repeated open/close/switch actions.
- Boot artwork, spinning penguin and lockscreen visual fidelity remain unchanged.

---

# 13. PHYSICAL REGRESSION MATRIX — REQUIRED

On the actual Galaxy S10+, prove:

1. Unlock penguin lockhead gesture is still smooth and functional; return to previous app/Home correctly.
2. Swipe Home left/right across all desktops; never get stuck mid-swipe.
3. Tap ten app icons in a row; accurate tap target, instant feedback, usable app views, no duplicate loads.
4. Open/close app drawer five times; no ghost click or blocked scroll.
5. Open Quick Settings, toggle a harmless verified function and close; responsiveness and z-order correct.
6. Short Back performs expected application/keyboard behavior; long Back closes only current app; Home returns home; Recents opens correctly; no double nav strip.
7. Keyboard focus and typing operate normally; haptic settings preserved if A49 already deployed.
8. Battery numeric percentage and icon fill still work after relevant service restarts, and after an approved reboot.
9. Wi-Fi scans/connects as before; network events do not freeze Home.
10. Locked screen hides navigation; power menu remains clickable as currently intended; screen turns off.
11. After locked screen-off dwell, device does not stay hot from framebuffer/UI polling; wake works without black, stale or corrupted frames.
12. Confirm display orientations that are currently working; rotated touch coordinates and keyboard safe zones align.
13. Boot first Nuxel splash, cosmetic warning art and spinning penguin animation remain unchanged.
14. Run a stress cycle (e.g. 30 desktop swipes, 20 app launches, 20 Home/Back/Recents, 10 lock/unlock) without crash, restart storm, delayed buttons or buildup of inactive app surfaces.
15. If wired HDMI/casting is actually working, test it; if unsupported, do not regress Nuxel phone display attempting to optimize external display.

**Evidence:** device logs, screen recordings/external video, process metrics, exact code hash/commit, before/after tables and owner's observed experience.

---

# 14. DELIVERABLES

Create within `docs/performance/A50/`:

1. `00-LIVE-ENVIRONMENT-AND-VERSIONS.md` — device, deployed binary hashes, systemd state, versions and clean recovery path.
2. `01-BASELINE-AND-MEASUREMENT-METHOD.md` + raw data — timings, variance, p50/p95/p99 and confounders.
3. `02-DISPLAY-RESOLUTION-AND-RENDERING-TRUTH.md` — actual native panel, actual compositor/headless resolution and scale, actual frame bridge, available modes, attempted/prohibited modes, selected final setting.
4. `03-ROOT-CAUSE-AND-PROFILES.md` — touch→handler→render→screencopy→convert→fb commit→glass path, credible evidence for bottlenecks.
5. `04-CHANGES-AND-SAFETY-REVIEW.md` — exact patches and justifications, binaries built, color/stride/damage invariants, user-visible feature preservation.
6. `05-AB-BENCHMARK-RESULTS.md` + JSON/CSV — table of each experiment with p50/p95 latencies, frame pacing, CPU, thermals and clear keep/reject reasons.
7. `06-SCREEN-OFF-THERMAL-AND-IDLE.md` — power-state observations, whether busy loops stopped and wake resumption proof.
8. `07-PHYSICAL-ACCEPTANCE.md` — itemized PASS/FAIL/BLOCKED with real evidence; no simulated tests mislabeled as device checks.
9. `08-ROLLBACK.md` and executable rollback helper — restore known-good binaries/services/config/assets and prove recovery possible.
10. `A50-PERFORMANCE-SUMMARY.md` — one-page human-readable results, current best settings, remaining ceilings and future architecture roadmap.
11. `tools/perf/a50-benchmark.sh` and any supporting tests with documentation.

If direct KMS/DRM/GPU acceleration cannot work on the installed vendor kernel, create `A50-FUTURE-RENDERER-MIGRATION.md` noting its dependencies (kernel 6.x migration, KMS/panel bridge, GPU userspace) **without undertaking that kernel effort as part of A50**.

---

# 15. FINAL STATUS AND REPORT FORMAT

Finish with a concise factual verdict for each:

- **Touch feedback:** measured improvement and p95.
- **Desktop swipe:** measured frame pacing and user-visible change.
- **App launch:** cold/warm interactive readiness timings.
- **Presentation bridge:** before/after capture, conversion, blit, commit and actual FPS.
- **Resolution:** before, candidate modes, final chosen buffer + scale, and why.
- **CPU/memory:** costs and regressions.
- **Thermals/screen-off:** behavior, measurement availability and safety.
- **Preserved features:** lockscreen, keyboard, Back/Home/Recents, battery, app dock, Wi-Fi, boot artwork.
- **Live deployment:** performed / blocked, with receipts.
- **Reboot persistence:** verified / owner approval pending / not tested.
- **Overall:** `VERIFIED_ON_DEVICE`, `IMPROVED_BUT_LIMITED`, `NO_MEASURABLE_GAIN`, `BLOCKED`, or `ROLLED_BACK`.

Do not claim 60 FPS because a config variable says 60. Do not claim 720p is new when the deployed build was already rendering at that size. Do not claim GPU acceleration with pixman. Do not claim touch-to-glass latency based solely on JS timestamps. Do not claim lower heat until actually measured. Do not substitute smooth CSS animation for an unresponsive system.

## FINAL DIRECTIVE 🐧⚡

**Make Nuxel FEEL buttery smooth.** Diagnose current live rendering and input end-to-end, optimize the measured bottleneck, avoid unnecessary work, make taps and swipes respond immediately, choose the best tested render resolution, keep applications warm only when beneficial, and make the screen-off state genuinely quiet. Preserve the existing Nuxel personality and all recovery routes.

**Measure → change one thing → prove it → keep or revert → repeat. Never sacrifice thermal safety or working phone behavior for a screenshot of a higher FPS number.**
