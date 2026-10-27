# 🐧⚡ NUXEL A67 — OPERATION HARDWARE ACCEL & SMOOTHNESS SLIDE PENGUIN 16000
## MALI-G76 ACCELERATION · EXYNOS 9820 · FEDORA ARM64 · KERNEL 4.14 · PHOC/WAYLAND · DISPLAY BRIDGE · WEBKITGTK · REAL FRAME PACING

> Mission type: **live-device diagnosis → architecture decision → reversible implementation → measured physical acceptance**. This is not a proposal and not permission to install arbitrary GPU drivers. Run with `deepseek-v4-pro-thinking` through CodeSeeQ `csft` from the Fedora laptop against the **current actual Nuxel checkout** and the **Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820 / Mali-G76 MP12**, presently booting a Samsung-derived Linux 4.14 kernel and Fedora ARM64 userspace. Confirm all details before acting.
>
> Owner's confirmed breakthrough: **Wi-Fi, DNS, TLS, internet and Nuxel Browser now work. Preserve that entirely.** Preserve A64 fixed launcher geometry, A65 and A66 shell/navigation/lock/audio progress, latest `./snekbyte.zip`, custom visuals, boot chain, screen and USB Live Console. This mission changes performance architecture only when measurable and reversible.

## 0. SUCCESS CRITERIA AND RULES

The user reports sluggish touch response, application animations, app launch and web scrolling. Deliver the **smoothest stable, practical UI on the existing 4.14 kernel**, preferably with Mali GPU acceleration if **actual compatible devices, driver userspace and compositor display integration** can be proven. Mesa alone is not acceleration, and a GPU string in `glxinfo`/`eglinfo` alone isn't proof that *Phoc* and *WebKitGTK* really render on the GPU.

Mandatory outcomes:

1. Pinpoint the actual active frame pipeline from app/WebKit → Wayland buffers → compositor renderer → output/backend → any `nuxel-wl-fb` copy/conversion/scaling → framebuffer/panel. Record *real* component source paths, versions, flags, physical and logical geometry, and timing.
2. Profile current live FPS, frame-time p50/p95/p99, dropped frames, end-to-end touch-to-response, launch latency, scrolling jank, CPU/GPU load (when available), temperature, RAM, swap, disk, power and stability. Use comparable reproducible workloads; record provenance and environmental conditions.
3. Distinguish **software rendering / pixman / llvmpipe**, **hardware GLES through proprietary Mali kbase**, **upstream DRM Panfrost**, and **experimental kbase bridge**. Never conflate them.
4. Implement the *best actually compatible stable path*. When hardware acceleration is blocked, implement concrete measurable CPU fallback/framebridge improvements and clearly mark GPU acceleration `BLOCKED_BY_KERNEL_ABI_OR_DISPLAY_INTEGRATION`, not PASS.
5. Solve priority pipeline bottleneck(s): excessive full-frame pixel copies, redundant scaling, color conversion, inefficient damage handling, overdraw, buffer synchronization, busy polling, unnecessary repaints and input/main-loop blocking.
6. Preserve usability, screen safety, audio, haptics, touch mapping, rotation, app sizing, lockscreen, system nav, keyboard, network, browser TLS, camera escape, SnekByte gameplay and thermal protections.
7. Produce a **before/after benchmark CSV + methodology + annotated trace + deployment manifest + rollback instructions + physical acceptance matrix**. One cherry-picked FPS snapshot isn't sufficient.

**No kernel upgrades, DTB/bootloader/recovery/partition flashes, vendor firmware swaps, blind driver module insertion, panel timings/voltage experiments, disabling thermal protection, setting permanently max CPU/GPU frequency, removing browser sandbox/TLS verification, blanket package replacement or unapproved compositor restart/reboot.** High-risk graphics changes require user approval and verified out-of-band USB console first.

### Historical hypothesis (NOT current measured truth)

In earlier Nuxel A50 performance work the owner described an old build: **Phoc headless/pixman at approximately 720×1520 logical, scale 2**, with `nuxel-wl-fb` converting/scaling to a **1440×3040** physical panel; old results around **24–28 FPS and 34–43 ms per blit**. Treat these as a high-priority *hypothesis*; do not carry those numbers into a current report as measurements. A full 1440×3040 RGBA buffer is approximately **17.5 MB per frame**; naïve copying one such frame at 60 Hz already moves ~**1.05 GB/s** before reading source surfaces, scaling, conversion or other copies. The compositor need not redraw every pixel every frame if damage tracking works.

The phone’s GPU is **Mali-G76 MP12** (Bifrost v7), not an Intel/AMD desktop GPU. Inspect kernel **`/dev/mali0` vs `/dev/dri/renderD*`**, in-kernel `mali_kbase` vs DRM `panfrost`, availability of Exynos display DRM/KMS vs vendor fbdev, ABI between kernel and userspace, actual Phoc/wlroots renderer options, and Wayland buffer protocols. **`dnf install mesa-*` must NOT be treated as a complete solution.**

### External technical leads to verify, not blindly deploy

- Mesa Panfrost official documentation: https://docs.mesa3d.org/drivers/panfrost.html — G76 support with an upstream DRM-compatible Panfrost GPU kernel/display integration; Mali GPU is 3D-only and depends on display controller and buffer-sharing route. Investigate actual kernel compatibility.
- postmarketOS S10+ hardware/kernel description: https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_%28samsung-beyond2lte%29 — downstream kernel, not mainline-ready; do not assume current Nuxel commit matches any outside release.
- WebKitGTK graphics paths: https://docs.webkit.org/Ports/WebKitGTK%20and%20WPE%20WebKit/Graphics.html — accelerated DMA-BUF vs shared-memory/nonaccelerated frame transfer; compatibility depends on the entire pipeline.
- **Experimental research lead only**: https://github.com/JimVulkan/mesa-unified-drivers — claims Panfrost/PanVK through stock Mali kbase and Mali-G76 testing on **Galaxy S10e Android**. Android gralloc/Vulkan presentation is NOT proof of native Fedora/Phoc EGL/GBM/Wayland support. Do not use an unaudited binary, overwrite libEGL systemwide, or deploy this as default. If promising, maintain as separate offline experiment with dependency/API/license/security audit, unit smoke test and explicit permission before any live use.
- Phoc: https://gautham_x.pages.gitlab.gnome.org/phoc/gettingstarted.html — verify actual installed version and backend flags.

## PHASE 1 — DEVICE ACCESS, BASELINE CAPTURE, SAFETY

**Before touching live graphics**: prove continuous emergency access on the Fedora USB Live Console even when compositor is frozen and browser is fullscreen. Test a read-only command through the actual transport. Record reliable recovery commands, shell process management, service logs, current display and where rollback package resides on-phone and on-host. Back up *every* config/binary/script/unit/file due for change with byte hash. Preserve existing uncommitted Git changes: create branch/worktree and manifest; never destructive-reset.

Read-only device survey (run on **phone**, not Fedora host; tools may be absent; use correct authorization; mask secrets):

```sh
uname -a; cat /etc/fedora-release 2>/dev/null || true
cat /proc/cmdline
ls -l /dev/mali* /dev/dri/* /dev/fb* /dev/dma_heap/* /dev/ion 2>/dev/null || true
find /sys/class/drm /sys/class/graphics /sys/class/devfreq /sys/class/thermal -maxdepth 3 -type f 2>/dev/null | head -180
find /sys/kernel/debug -maxdepth 3 -iname '*mali*' -o -iname '*gpu*' 2>/dev/null | head -80
lsmod 2>/dev/null | grep -Ei 'mali|panfrost|drm|exynos' || true
(cat /proc/modules 2>/dev/null || true) | grep -Ei 'mali|panfrost|drm|exynos' || true
dmesg 2>/dev/null | grep -Ei 'mali|gpu|panfrost|exynos|drm|decon|fb' | tail -120
ps -eo pid,ppid,user,pcpu,pmem,stat,comm,args | grep -Ei 'phoc|wlroots|nuxel-wl-fb|webkit|nuxel|snekbyte|pipewire|weston' | head -140
systemctl --user list-units --type=service --no-pager 2>/dev/null || true
rpm -qa | grep -Ei 'mesa|libdrm|egl|gles|gbm|webkit|phoc|wlroots|pixman|mali' | sort || true
```

Root-only commands allowed *read-only* when necessary for baseline; avoid unsafe mounting `/sys/kernel/debug` or changing kernel sysctls without explicit approval. Profile services only after identifying service ownership and session. Observe environment per process (avoid revealing secrets): `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, `GDK_BACKEND`, `WLR_RENDERER`, `EGL_PLATFORM`, `LIBGL_ALWAYS_SOFTWARE`, `MESA_LOADER_DRIVER_OVERRIDE`, `GBM_BACKEND`, WebKit debug flags, renderer settings and resolution. Do not dump all environment variables into shared logs.

Verify screenshot versus physical display and logical input coordinates; screen size 1440×3040 is the known panel spec, but actual active mode/scale must be discovered. Read real Wayland output, fb virtual width/height/stride/format, refresh rate, buffer layout, cache behavior and bridge process configuration. Identify compositor session ownership (root vs user), seat/session DRM privileges, display controller API.

Before/after rollback rehearsal: build a non-destructive restore script for modified userspace artifacts; validate it on staged copies before deploying anything. Ensure that an unhealthy graphics service either restarts to last-good userspace or the USB console can restore it. DO NOT set an auto-restart loop that bricks interaction.

## PHASE 2 — OBJECTIVE PERFORMANCE BASELINE, NOT COSMETIC FPS

Define **exact workloads** on physical phone at the same scaling, same display refresh, thermal steady state, battery/power, background services:

- From Home: vertical app grid scroll and 20 item taps, launcher icon grid swipe, repeated app-open/Home/tab recents transition, lock/unlock and wake.
- WebKit/Browser: open known working `https://www.google.nl`, scroll long page (network already loaded), rotate or open OSK, go Home and return. Preserve TLS and sandbox.
- SnekByte: gameplay 90+ seconds, repeated swipes/D-pad at multiple speeds, game exit/re-entry; no visible Home dock in game.
- Static idle: screen on no interaction for 60 seconds; account for frame production where there should be no damage. Excess repaint loops are a defect.
- High load vs typical: 3 app switching cycles with bounded memory; thermals tracked.

Collect frame time distributions, worst stalls, CPU% per process, memory and GPU utilization/frequency if exposed, power if accurately available, wakeups/scheduler contention, thermal readings, kernel log GPU/IOMMU/display errors. Useful tools **if present or safe to install**: `perf` where supported, `pidstat`, `top`, `time`, `strace -c` on isolated dev reproductions, `wlr` renderer logs, Phoc debugging, `eglinfo`, `glmark2-es2-wayland`, `weston-info`/`wayland-info`, `kmscube` when DRM/KMS genuinely available, WebKit GTK FPS debug in a temporary experiment. Some benchmarks may not be valid for this headless/fb bridge path; mark `INAPPLICABLE`, do not spoof data.

For gesture latency, use a phone video in slow motion if owner can record it, or correlate kernel input events through app response/render/send/present timestamps. **Do not claim touch-to-photon measurements using timestamps from only one stage.** Instrument bridge frame queue, memcpy, scaling, rotation, format conversion, cache flush and ioctl commit with monotonic timestamps and actual byte counts. Guard instrumentation behind debug flag, no unbounded logs.

Deliver `docs/a67/BASELINE.md`, `docs/a67/measurements-before.csv`, `docs/a67/live-pipeline.md`, and tests/benchmarks as executable repo-local scripts with robust error handling. Each metric contains methodology, tool, units, timestamps, sample count and trustworthy device context.

## PHASE 3 — GRAPHICS ACCELERATION CAPABILITY DECISION TREE

### PATH A: VENDOR MALI KBASE + PROVEN COMPATIBLE USERSPACE (investigate first if `/dev/mali0` exists)

Inspect whether downstream kernel ships a functioning mali_kbase device, ABI version, memory sharing interface, job submission and regulators/clocks. Probe access permissions, SELinux rules, compatible built-in Samsung/Arm userspace (`libmali.so`, EGL, GLES, GBM, Wayland WSI). Locate legitimate existing artifacts in kernel/vendor images or packages, with version, license, hashes and ELF architecture; do **not** pull random unverified `.so` files or assume Android-linked gralloc works under Fedora. Study whether the installed Phoc/wlroots can create EGL contexts and share DMA-BUF buffers with display bridge. Vendor EGL acceleration can render 3D while the display compositor still copies CPU frames; distinguish the two.

For each possible compatible EGL/GLES route, prototype only in **isolated userspace test** (separate library path/process, no systemwide replacement) and test a full draw → buffer export → import/compositor → display cycle; capture rendered GPU name, software fallback checks, GPU job activity, frame hash and frame timing. If no compatible native Fedora ABI/vendor stack is available, conclude blocked with a precise documented gap and leave live libs untouched.

### PATH B: UPSTREAM DRM PANFROST + MESA (only when actual supported kernel stack exists)

Check presence and usable permissions of `/dev/dri/renderD*`, driver name via sysfs, required Panfrost GPU kernel ioctl and display DRM/KMS, buffer sharing and fence synchronization. **Panfrost user-space in Mesa alone cannot talk to proprietary kbase as though it were DRM Panfrost.** A non-DRM vendor framebuffer does not become kmsro merely because Mesa is installed. Verify version/ABI support for Mali-G76 and DRM display controller. Install Fedora AArch64 Mesa packages (`mesa-libEGL`, `mesa-libGLES`, `mesa-dri-drivers`, `mesa-libgbm`, `libdrm` names dependent on current repo) only if compatible and as transactional, rollback-capable deployment. These packages may be present already, are not proof of acceleration, and must not replace GPU libraries indiscriminately.

Run EGL/GL reports **inside both isolated smoke test and compositor process context**; require real GPU and no llvmpipe/softpipe/swrast fallback. Verify `eglSwapBuffers` actually uses GPU, dmabuf import/export, frontend performance and that the display path does not negate GPU speed gains. If full stack unavailable on kernel 4.14, do NOT force random Panfrost module/DTB. Document exact future kernel-port prerequisite separately.

### PATH C: EXPERIMENTAL OPEN-SOURCE MESA-ON-KBASE (research-only unless proved compatible)

Review maintained upstream current code, licenses, device/kbase versions, Linux userspace ELF support vs Android gralloc-only WSI, GLES/OpenGL vs Vulkan, GBM/EGL/Wayland integration, data-plane security, graphics buffer ownership, failed-probe behavior. An Exynos 9820 S10e Android test is not equivalent to full native Fedora Galaxy S10+ Phoc support. Prototype in detached offline worktree/emulated environment and if feasible **opt-in separate process** with explicit owner approval; no release of systemwide experimental driver as default. A staging test that outputs an image offscreen does not satisfy on-screen compositor acceleration.

### PATH D: NO SAFE ACCELERATION YET → OPTIMIZE SOFTWARE + BRIDGE (MANDATORY WORK, not failure)

Identify achievable speedups under kernel 4.14 without hazardous driver actions. Focus on bridge and compositor hot paths and retaining correct visual output; preserve fast rollback. Record exact `BLOCKED` reasons for hardware route and real CPU wins. No hiding debug widgets as “FPS optimization” unless expensive instrumentation itself is at fault.

Prepare architecture decision record `docs/a67/GPU-ACCEL-DECISION.md` comparing safety, kernel ABI, userspace ABI, compositor support, actual on-panel latency, packages, dependencies and fallback for all four paths. Choose proven result, not novelty.

## PHASE 4 — ELIMINATE FRAMEBRIDGE BOTTLENECKS

Source-audit actual `nuxel-wl-fb`/compositor or successor driver, including framebuffer/stride/pitch/pixel format, source buffers, processing thread and output ioctl. Prioritize measured offenders:

1. **No redundant scaling or copies:** Stop duplicating complete frames if no damage, try direct matching pixel-format/stride buffers where safe, avoid extra intermediate RGBA conversion, retain real correct panel orientation/scale and input coordinate transforms. Do not regress launcher icon sizing or touch hit boxes.
2. **Damage-aware updates:** Track Wayland damage, composite output damage and minimum updated rectangles. Respect opaque regions and changed surfaces, clip damage appropriately, correctly handle fullscreen/rotation/lockscreen. If vendor fbdev forces full-flush, avoid expensive recomposition for unchanged frames and document hardware limitation.
3. **Frame scheduling/pacing:** Use actual vsync/page-flip notification when available; avoid busy loops and unsynchronized `sleep(16ms)` blindly imposing fictitious 60Hz. Bound pending frames; apply drop/replace policy to outdated frames to reduce input latency while preserving app animation correctness. Never queue 3 seconds of stale frames.
4. **Memory mapping:** Audit mmap correctness, CPU cache coherence, DMA buffer sync, double/triple buffers based on actual interface. Never reinterpret physically noncontiguous buffers as contiguous; don't disable synchronization to improve FPS.
5. **Parallel and SIMD work cautiously:** If scaling/conversion cannot be avoided, benchmark optimized memory access, NEON vectorization where toolchain/ABI appropriate, cache locality, line-stride alignment, tile or row partition with a bounded worker pool. Compare gain versus battery/thermal cost. Avoid code for a CPU architecture never used on phone.
6. **Refresh and display:** Respect panel's actual reported safe mode, output scale, orientation, aspect and notch/cutout; verify frame drops vs input correctness. Do not overclock hardware or write panel registers.
7. **Compositor:** Identify `pixman` renderer vs GLES renderer; adjust only supported backend flags and initialization order. Prefer authenticated one-owned compositor route; avoid starting a second compositor or duplicating headless bridge without proper handoff and rollback.

Instrument each candidate *before and after*, including full frame bytes copied/sec, number of copies, active/presented frames, average and worst blit duration, CPU. A full-frame bridge optimization without reliable hitbox mapping is a regression and must be rolled back.

## PHASE 5 — PHOC / WLROOTS / WAYLAND RENDERER INTEGRATION

Audit compositor logs and source for renderer/backend selection, DRM vs headless/pixman, supported GLES/EGL/GBM entry points, DMA-BUF linux-dmabuf protocol, SHM fallback, presentation timing, output damage tracking. Confirm whether Phoc's actual runtime backend *can* talk to the phone's vendor fbdev/Exynos display or only to Nuxel's software framebuffer bridge. Do not blindly set `WLR_RENDERER=gles2` and assume it works: in an unsupported stack it can prevent shell boot. Stage and smoke-test with a supervised opt-in renderer profile; default remains last-known-good until proven stable.

Profile input-event dispatch, JS bridge synchronous calls, UI thread blocking, and remote IPC. Any blocking HTTP requests or camera service timeouts in the main loop are reliability bugs; decouple them without changing semantics. Native dialogs, app switcher focus, nav overlay priorities and OSK must remain functional. Inspect whether a 4.14 vendor display driver exposes fence/page-flip events suitable for presentation feedback, and report absence honestly.

## PHASE 6 — WEBKITGTK BROWSER / PWA PERFORMANCE WITHOUT BREAKING TLS

Now that HTTPS browsing works, instrument page startup/paint/layout and scroll: browser process startup, WebKit web process CPU, Skia render path, accelerated DMA-BUF vs SHM, network idle, script tasks, layout thrash, image decode, GPU process faults. WebKitGTK official documentation distinguishes accelerated DMA-BUF from shared-memory fallback; require compatible platform before enabling acceleration.

- Confirm build and GTK/WebKit version, GPU and compositing debug output, and owner-visible smoothness while scrolling an already loaded site.
- Keep TLS/certificate verification, DNS, glib-networking/GTls backend, network sandbox, security, site isolation and working bookmarks/storage intact. No disabling sandbox for frames.
- Avoid forced `WEBKIT_FORCE_COMPOSITING_MODE=1`, `WEBKIT_DISABLE_DMABUF_RENDERER`, Mesa overrides, or other environment flags globally without A/B tests and crash checks. If accelerated path is unstable, prefer a reliable software mode and optimize content/update loop.
- Use responsive browser address bar without offscreen buttons. Ensure compositor/system-owned global nav and top pull still work even in fullscreen. Browser shouldn't be capable of trapping user by grabbing all touch surfaces.
- For SnekByte, use browser frame timing and application animation logs, CSS transform efficiency, requestAnimationFrame loops with visibility pause, damage avoidance, nonblocking input and frame pacing, not fake animation speed. Preserve latest game mechanics, icon, highscores and WoNQ theme.

## PHASE 7 — CPU, MEMORY, THERMAL AND STARTUP LATENCY

Instrument process priority and scheduling issues, DVFS CPU frequency and GPU devfreq/thermal if exported, thermal throttling, CPU pinning, kswapd pressure, zram/swap, excessive log loops, filesystem I/O, service timers, polling frequency, background scans, compositor redraw and JS event overhead. Before changing service priorities, identify actual bottlenecks and ensure critical input/display/lock paths won't starve.

Explore safe options only where measurements justify them: reduce redundant work and startup contention, consolidate overlapping polling timers, coalesce shell sensor updates, cache immutable icons/assets, lazy-initialize optional app processes, bound browser process count if user-configurable and safe, cap low-value animation work on inactive windows, defer noncritical probes until UI ready. Smoothness must not come from disabling working telemetry/battery/locking or killing important services. Do not alter Linux governor/thermals permanently or force performance mode without power and heat analysis and explicit owner consent. Include power tradeoffs.

## PHASE 8 — ENGINEERING IMPLEMENTATION / DEPLOYMENT ORDER

Make small independent, revertible commits (example phases):

- **A67a** Inventory + accurate instrumentation/benchmark harness; zero live behavior changes.
- **A67b** Fast low-risk loop, animation and unnecessary frame-copy reductions; run on-device A/B comparisons.
- **A67c** Framebridge dirty-rect and pacing optimization with full input geometry tests; rollback if any misrender, crash or lock issue.
- **A67d** GPU EGL/GBM vendor or Panfrost staging only after proof of ABI and actual on-screen ability; keep last-good fallback. If no safe route, leave no experimental live changes.
- **A67e** WebKit/PWA and compositor tuning after baseline and without breaking network/TLS or app nav.
- **A67f** Power/thermal tuning and regression tests on real phone.

For each commit/deployment: record SHA, changed files, checksum vs phone, symlinks/install paths, owner/mode, service restart effects, before/after benchmark, rollback path. **Only one device deployment owner.** Owner approves disruptive test/comp restart/reboot. Test first in host or supervised nested compositor where meaningful, but **physical phone proof remains required**.

## PHASE 9 — PHYSICAL ACCEPTANCE GATES (NO FAKE PASSES)

Must complete and record for each test: `PASS_PHYSICAL / IMPROVED_WITH_NUMBERS / PASS_OFFLINE_ONLY / BLOCKED_KERNEL_OR_ABI / FAILED / NOT_TESTED / AWAITING_OWNER`, evidence path and log/time.

| ID | Test | Required proof |
|---|---|---|
| A67-T01 | Baseline GPU identity | Physical GPU/driver ioctl, actual `/dev` path, backend, compositor renderer, source of real acceleration |
| A67-T02 | End-to-end renderer | Wayland app → Phoc renderer → bridge/backend → panel, with evidence of software or GPU stages |
| A67-T03 | Launcher scroll | Comparable repeatable 20 interactions; p50/p95/p99 frame-time and visual responsiveness |
| A67-T04 | App opening | 10 launches across Settings, Camera, Browser and SnekByte, latency before/after |
| A67-T05 | Home/Back/Tabs | Each system nav works from browser, native app, fullscreen and OSK conditions |
| A67-T06 | Browser HTTPS | Reopen working `https://www.google.nl`, type, scroll, back, Home; TLS not regressed |
| A67-T07 | Browser scrolling | Stable scrolling/presentation timings over cached content, no WebKit crash |
| A67-T08 | SnekByte | Smooth gameplay, preserved mechanics, no dock/title overlays, correct touchscreen swipes |
| A67-T09 | App switcher | No frames drawn behind/over shell unexpectedly, input-to-response measured |
| A67-T10 | Lock/wake | Real lockscreen, no black output/0% battery regression, wake responsive |
| A67-T11 | Rotation | Portrait/auto states remain functional where actual sensors permit; accurate input mapping |
| A67-T12 | Idle power | No unnecessary full frame refresh busy loop, idle CPU measured; thermals safe |
| A67-T13 | Input mapping | Physical taps/cutout/swipes at edges and every orientation correctly hit UI elements |
| A67-T14 | Bridge CPU load | Real CPU time per process + copy count/bytes vs baseline |
| A67-T15 | Renderer truth | EGL/GLES accelerated only if phone GPU activity and compositor on-panel path proven |
| A67-T16 | 10-minute workload | No leaks, watchdog restart loops, GPU hangs, main-thread stalls, unacceptable heat |
| A67-T17 | On-device rollback | Reversible patch demonstrated with backed-up config/files and USB recovery |
| A67-T18 | Owner-approved cold boot | Same stable renderer, Wifi/TLS/browser/desktop, no display lockout |

No invented FPS claims or universal 60 FPS promise. If native acceleration impossible, optimize and report measured achievable frame rate. If phone lacks reliable frame-present timestamps, report `PROXY_METRIC` and label method accurately. **No pass by unit mock**; if owner cannot perform physical test, give exact short validation instruction and mark pending.

## PHASE 10 — FINAL HANDOFF REQUIRED

Create complete `docs/a67/` directory with:

- `BASELINE.md`, `measurements-before.csv`, `measurements-after.csv`, `TEST-METHODOLOGY.md` and scripts/commands for reproducing performance tests on Fedora laptop and phone.
- `GPU-ACCEL-DECISION.md`: reality of `/dev/mali0`, `/dev/dri/`, kernel ABI, hardware path shortlist, what was implemented vs blocked, CPU fallback and whether a future kernel branch is justified **by specific driver evidence**, not speculation.
- `PIPELINE-BEFORE-AFTER.md`: diagram and exact change impact, CPU/GPU load, frame time distributions and idle costs.
- `DEPLOYMENT-AND-ROLLBACK.md` including verified USB emergency steps and staged checkpoint.
- `PHYSICAL-ACCEPTANCE.md`: all 18 acceptance rows with evidence IDs and physical status.
- `CHANGELOG.md`: real files/commits, correctness notes, security/thermal/energy tradeoffs, remaining blockers.

Final owner-facing response must succinctly answer: **(a) was the GPU actually enabled? (b) which kernel/userspace driver path? (c) what caused sluggishness? (d) baseline vs after with p50/p95 frame timing, CPU and battery/thermals? (e) what is still limited by kernel 4.14? (f) exactly how to roll back?** If a GPU path is not compatible, honestly report **'No native GPU path verified yet; software/display bridge optimized'**. A 4.14 kernel can be fast under a well-engineered vendor stack; moving to 6.x is not a guaranteed performance solution, and never part of this mission.

## EXECUTE NOW

Start with read-only inspection of actual current source, connected physical device and reliable USB console. Establish benchmark baseline **before** changing package installations or graphics config. First investigate `nuxel-wl-fb` historical 720×1520→1440×3040 path and actual renderer; do **not** start by `dnf install mesa` or arbitrary experimental Panfrost `.so` files. Implement and test the fastest safe route supported by hard evidence. Maintain known-good internet, browser, shell controls and game.

**SLIDE PENGUIN 16000 — REAL ACCELERATION OR MEASURED SMOOTHNESS, NEVER FAKE FRAMES. 🐧⚡**

