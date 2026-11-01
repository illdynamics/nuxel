# PWNAGE-50000 — Finish Mali kbase graphics acceleration for WebKitGTK and GTK apps

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820 / Mali-G76 MP12  
**OS:** Nuxel Fedora ARM64  
**Current graphics milestone:** Phoc is using the vendor Mali `kbase` path; WebKitGTK/GTK GL still falls back to software.  
**Mission:** finish the missing accelerated application-buffer path without regressing the working compositor, DECON panel or boot.

## Mission objective

The kbase GPU breakthrough is real and must be preserved. The remaining problem is that WebKitGTK's accelerated compositing path and GTK GL initialization are not yet working. Implement and prove the best safe, compatible native Wayland path so the Nuxel Home PWA host, WebKit WebProcess and supported GTK apps can use the Mali-G76 rather than always rendering in software.

Do not confuse these separate layers:

1. Phoc/compositor can submit work to Mali through `/dev/mali0`.
2. The WebKitGTK web process can create a hardware EGL/GLES context and composite its page.
3. WebKitGTK can share its accelerated backing-store buffers with the GTK UI process and Wayland compositor (DMA-BUF/Wayland WSI/import path).
4. GTK3/GTK4 native widget rendering may use its own renderer; GTK3 WebKit host and GTK4 GSK are different targets.
5. `nuxel-wl-fb` still performs the final Wayland screencopy-to-fbdev/DECON presentation work. GPU rendering does not automatically eliminate that CPU copy.

A PASS at one layer does not imply a PASS at the next. The primary goal is **real WebKitGTK accelerated compositing on the physical Nuxel screen**, with a reliable per-process software fallback if the accelerated path cannot yet be supported.

## Current owner-reported live state — treat as the new baseline, then re-verify

The owner reports the following after PWNAGE-48000:

- `phoc` holds 3× `/dev/mali0`, 1× `/dev/udmabuf`, and an `anon_inode:dmabuf_udmabuf`.
- kbase debugfs shows a GPU context owned by `phoc`.
- `nuxel-wayland`, `nuxel-wl-fb` and `nuxel-web` are active.
- Bridge reports `FRAMES_OK`; `decon_pan_failed=0`.
- `/run/nuxel-gpu-fallback` is absent.
- `/dev/fb0` is restored; physical panel is 1440×3040 and virtual framebuffer is 1440×6080.
- There is no `/dev/dri`, which is expected for the current vendor-kbase path.
- Honest remaining limitation: GTK reports `failed to initialize GL`; the current Mesa kbase support is surfaceless-only; WebKitGTK's Wayland accelerated-compositing/buffer-sharing path is not working. A Wayland-enabled Mesa build was tried and failed, then reverted.
- Final screencopy → fbdev upscale/copy remains CPU work.
- Recovery backups are reported under `/var/backups/nuxel/kbase-gpu-*`; pre-Wayland-test Mesa EGL backup is `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland`.
- Relevant commits reported by the owner: `90ff0d6` (kbase GPU acceleration), `9340301` (post-reboot BOOT readback), `01cd482` (post-reboot AMOLED capture).
- Full report/evidence: `docs/beta-finalization/live/PWNAGE-48000-KBASE-GPU-REPORT.md` and `docs/beta-finalization/live/evidence/pwnage-48000-kbase-gpu/`.

**Important:** the supplied `nuxel-main (10)(1).zip` predates the latest kbase commits and contains older software-forcing settings. The actual working checkout and live phone after the listed commits are authoritative. Reconcile the archive/source with the current checkout using Git history and live hashes before changing anything.

## Required implementation work

### 1. Preserve the existing working kbase compositor

Reconfirm the live renderer and actual GPU context, not just open file descriptors. Capture Phoc's command line, environment, renderer logs, kbase context owner, GPU job activity if exposed, `/dev/mali0` and udmabuf fds, dmabuf export/import details, process restarts and display-frame receipts.

Keep these invariants:

- `phoc`, `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web` stay healthy.
- `FRAMES_OK` remains true and `decon_pan_failed` remains zero.
- `/dev/fb0` remains the sole DECON/framebuffer owner (`nuxel-wl-fb`).
- Do not require `/dev/dri` merely to recognize the existing vendor-kbase compositor path.
- Do not replace the working kbase driver or compositor backend with Pixman as a shortcut.
- Do not overwrite working Mesa libraries globally with an experimental build.

Inspect commits `90ff0d6`, `9340301`, `01cd482`, the current PWNAGE-48000 report and its evidence before editing. Confirm the live binary/library hashes actually correspond to those builds.

### 2. Remove unconditional software forcing in a controlled, reversible way

The older source snapshot contains explicit software forcing in several places:

- `tools/s10plus/a45/nuxel-session.sh`: `WEBKIT_DISABLE_COMPOSITING_MODE=1`, `LIBGL_ALWAYS_SOFTWARE=1`, `GSK_RENDERER=cairo`.
- `services/nuxel-bridge/src/api.py`: `NATIVE_LAUNCH_ENV` and `systemd-run --setenv` force `GSK_RENDERER=cairo`, `LIBGL_ALWAYS_SOFTWARE=1` and `WEBKIT_DISABLE_COMPOSITING_MODE=1` for native launches.
- GTK4's `GSK_RENDERER` setting is not the same thing as GTK3 WebKitGTK accelerated compositing.

Check whether these are still present in the current checkout and live service environment. Replace unconditional flags with a controlled graphics-profile mechanism. Never simply remove all fallback variables from every process and hope GL works.

Implement a single policy/configuration source, for example `/etc/nuxel/graphics/graphics-profile.json`, with independently controlled settings for:

- Phoc renderer/backend (already working kbase path; do not change casually);
- WebKitGTK compositing (`auto`, `accelerated`, `software`);
- GTK3/GDK GL tests/runtime (`auto`, `enabled`, `software` where supported);
- GTK4 GSK renderer (`auto`, `gl`/`ngl`/supported backend or `cairo` according to actual GTK version);
- native apps (per-app capability override if one app is incompatible);
- `nuxel-wl-fb` presentation optimization mode.

Default must be safe: prefer hardware when a complete tested path exists; otherwise use an explicit software fallback with a visible reason. Use per-process environment injection/wrappers, not blanket global environment that unintentionally affects systemd, compositor, services and diagnostics.

Do not set `WEBKIT_FORCE_COMPOSITING_MODE=1` globally. WebKit documents it as forcing accelerated compositing; it is useful for controlled testing, but can expose unsupported paths or crash loops. Likewise do not set `WEBKIT_DISABLE_COMPOSITING_MODE=1` after acceleration is proven. Use A/B test profiles and preserve an emergency software profile.

### 3. Diagnose and complete WebKitGTK's actual Wayland graphics path

Audit the exact installed runtime and package build:

- GTK3 version and WebKit2GTK 4.1/WebKitGTK version/build features;
- `nuxel-pwa-host` link dependencies and GTK initialization;
- WebKitWebProcess and any WebKit GPU process architecture;
- actual process UID, Wayland socket/session variables, runtime directory and library search path;
- EGL vendor, client extensions, display extensions, GL/GLES versions, renderer strings, driver name and loaded libraries;
- kbase ABI/version and compatibility with the userspace driver being loaded;
- Wayland EGL platform support versus surfaceless-only EGL;
- Wayland `linux-dmabuf` protocol availability and supported fourcc formats/modifiers;
- DMA-BUF export/import, fences/synchronization and buffer ownership across WebKit UI/Web processes and Phoc;
- any dependency on DRM render-node access, GBM, libdrm, DRI loader or renderD node in the **specific Mesa driver path**.

Do not assert that `/dev/dri` is universally required for every EGL Wayland implementation. Mesa EGL supports different window-system platforms, and the implementation selected by the EGL driver determines them. The current Mesa kbase implementation is reported surfaceless-only, so the task is to find a genuine Wayland WSI/buffer-sharing route compatible with kbase, not to fabricate a DRM device node.

Investigate, in order:

1. Whether a legitimate Exynos/Samsung/ARM vendor Mali userspace matching this exact kbase ABI is available, with native Linux AArch64 Wayland EGL WSI (not Android-only gralloc). Validate redistribution/license/provenance and whether Phoc can import its Wayland buffers.
2. Whether the current Mesa-on-kbase build can be extended with a real Wayland EGL platform and DMA-BUF buffer allocation/export/import without DRM render-node dependencies. Audit the implementation and API assumptions; do not merely build Mesa with `-Dplatforms=wayland` and call it fixed.
3. Whether `udmabuf` can provide a safe, coherent DMA-BUF export path for the relevant WebKit/GTK buffers, including size/alignment, cache synchronization, lifetime, fences and Phoc import. Treat its presence/open fd as a lead, not proof. Never use it to expose arbitrary pages or bypass ownership/security.
4. Whether WebKitGTK's existing accelerated backing-store implementation can use a compatible exported DMA-BUF path with the current compositor and GTK port. Read the installed WebKit version's actual implementation and debug output.
5. If no supported WSI/buffer-sharing combination can be assembled, isolate the blocker precisely and retain the working compositor + software WebKit profile. Do not force unstable experimental code into the default image.

### 4. Build a sequence of real graphics probes

Create small AArch64 probes installed only for diagnostics or run from the build tree. Each probe must emit structured JSON/text with actual renderer and backend, plus exit code and logs.

Required probes:

- kbase device/ABI probe: opens `/dev/mali0`, queries supported version/capability using documented/vendor-supported ioctl only, creates a context and submits a minimal GPU workload if safe. No undocumented destructive ioctls.
- EGL surfaceless probe: demonstrate the already-working path and report renderer/vendor/version.
- EGL Wayland probe: connects to the actual Wayland socket, initializes `EGL_PLATFORM_WAYLAND_KHR`/the supported extension, chooses config, creates `wl_egl_window`, creates GLES2/3 context, renders a deterministic frame, swaps buffers and checks for real GPU execution.
- DMA-BUF probe: test only supported buffer formats/modifiers; export/import round-trip and fences; confirm Phoc can import and display it. Do not accept an FD existing as proof of successful rendering.
- GTK3 GL probe: small GTK3 app using the correct supported GL surface/API (`GtkGLArea`/GDK GL as applicable to the installed GTK release), running on the actual Wayland session.
- GTK4 GSK probe: separate GTK4 app that reports the selected GSK renderer and proves an actual GPU-backed frame if GTK4 GL is supported. Do not use this as a proxy for the GTK3 WebKit host.
- WebKitGTK probe: a minimal GTK3/WebKit2GTK 4.1 app with accelerated compositing enabled in a controlled profile. Load a local deterministic page with CSS transforms, opacity, canvas/WebGL where supported, animation and scrolling. Confirm acceleration is actually active and buffers are shared via the expected DMA-BUF path.
- Full Nuxel PWA host probe: run the real `nuxel-pwa-host` / Home shell, not merely a test app. Verify WebKit child process environment and backing-store mode.

`eglinfo`, `glxinfo`, process fd inspection and renderer strings are diagnostics only. A renderer label or successful EGL context alone does not prove WebKitGTK is using its accelerated DMA-BUF backing store on the physical panel.

### 5. WebKitGTK accelerated compositing acceptance

The exact WebKitGTK graphics architecture distinguishes non-accelerated shared-memory images from accelerated DMA-BUF-backed composited frames. Validate this against the installed WebKit build and its runtime logs.

A WebKitGTK PASS requires all of the following:

- Accelerated compositing is enabled in the real WebKitWebView.
- The WebKit web process successfully creates the required context using a real Mali backend (not llvmpipe/softpipe/cairo fallback).
- WebKit accelerated backing store delivers real GPU-backed DMA-BUF-compatible frames to the GTK UI process.
- The actual Phoc session can import and composite those frames without copy fallback or black/blank surfaces.
- The page remains interactive, scrolls, animates, resizes/rotates and survives app switching.
- No continuous EGL init errors, GPU faults, WebProcess termination loop, stale frames or compositor crash.
- On-screen performance improves measurably against the software baseline at matched workload/thermal state.

For a full Nuxel Home pass, test launcher, app drawer, Settings, lockscreen, browser, Notes, Quick Settings, video/animated content, long scrolling web page, touch keyboard and all app transitions. The Home PWA host is built with GTK3 + WebKit2GTK 4.1 in the checked source snapshot; do not confuse this with GTK4 native app acceleration.

### 6. Native GTK app rendering

The current Bridge's native-app launch path also forces `GSK_RENDERER=cairo` and `LIBGL_ALWAYS_SOFTWARE=1` in the archive snapshot. Recheck the live code and process environment.

- Implement per-application renderer profiles.
- GTK3 apps: test GDK/GL only where the app/toolkit supports it; GTK3 does not use GTK4's GSK renderer setting.
- GTK4 apps: test the exact installed GTK version's supported GSK renderer choices and only select GL/NG if they actually initialize on Wayland.
- Native Wayland surface presentation must remain functional whether a given app uses GPU or Cairo.
- Keep an app-specific software override for unsupported apps; one app failing GL must not prevent the shell from booting.
- Do not change app launch UID, sandbox, D-Bus session bus or permissions simply to make EGL initialization pass.

Add a per-app diagnosis view to Graphics Settings showing which native apps have proven accelerated rendering, which use a software fallback and why. Do not infer from process-open `/dev/mali0` alone.

### 7. Optimize the remaining screencopy → fbdev CPU work independently

Even if WebKitGTK becomes accelerated, the final presentation bridge may remain CPU-bound. Profile and optimize it as a separate subproject.

Relevant current source from the archive:

- `tools/s10plus/a34/nuxel-wl-fb.c` is the source compiled by the checked rootfs builder (verify current builder/source after the new kbase commits).
- `tools/s10plus/a67/nuxel-wl-fb.c` is a newer historical implementation, not automatically the active image source.
- `services/nuxel-session/systemd/nuxel-wl-fb.service` is the unit to compare with the live process.
- The bridge uses `zwlr_screencopy_manager_v1`, SHM frame buffers and a CPU blit/upscale to `/dev/fb0`.
- Current panel geometry reported by owner: 1440×3040, virtual framebuffer 1440×6080; confirm current output/capture mode and stride live.
- `FBIOPAN_DISPLAY` is required on this command-mode Samsung panel to latch every frame; do not remove it because a benchmark looks faster without it. Earlier work found that removing the per-frame pan made the display appear static until wake.

Tasks:

- Measure capture-to-present pipeline stages separately: screencopy request, frame-ready latency, SHM map/copy, color conversion, upscale/blit, framebuffer commit/pan, end-to-end display latency.
- Measure CPU time per stage, p50/p95/p99 frame time, frame drops, bytes copied, frame damage area and power/thermal behavior.
- Determine whether the compositor output is still logical 720×1520/scale 2 or whether the new kbase configuration changes output size; do not trust historical comments.
- If current capture and physical dimensions differ by integer 2×, use the measured A67 row-expansion approach only after checking which code is already active. Avoid duplicate expansion/color conversion.
- Add correct damage-aware partial updates if screencopy protocol and panel commit behavior support them. Never skip required full repaint after wake, orientation change, palette change or damage invalidation.
- Consider NEON/ARMv8 SIMD for pixel conversion/copy only with byte-identical tests and correct alignment/stride. Benchmark against current compiler-optimized C before adding complexity.
- Avoid extra full-frame buffer allocations and repeated `mmap`; reuse buffers safely with correct Wayland release events.
- Use `MADV_DONTNEED`, cache hints, non-temporal stores or cache maintenance only if measured and supported; do not add speculative cache operations.
- Explore whether the current DMA-BUF path can deliver a frame directly to the bridge or a supported GPU scaling path. Do not add a second framebuffer owner, bypass `nuxel-wl-fb`, or introduce unsafe direct scanout.
- Keep 30 FPS target/pacing and current panel commit invariant unless measurements and hardware evidence support a better stable setting.

A WebKit GPU PASS and bridge CPU optimization PASS are separate result fields. Do not claim the final CPU copy disappeared merely because the WebKit web process uses Mali.

### 8. Graphics Settings and truthful telemetry

Complete or extend the Graphics Settings tab created by the previous graphics mission. Use the existing `nuxel-metricsd` service/socket and Bridge conventions. The checked repository already compiles/installs `nuxel-metricsd` and socket activation; extend it rather than deploying a second metrics daemon.

Show separate statuses:

- GPU: Mali-G76 / detected hardware.
- Kernel driver: `mali_kbase`, version/ABI if known.
- Compositor: Phoc renderer (kbase/Mali vs Pixman/software), confirmed context and job activity.
- WebKitGTK: accelerated compositing enabled/disabled/failed; renderer; DMA-BUF backing store status.
- GTK3: GL context test status (not inferred from GTK4).
- GTK4: GSK renderer and GL test status if GTK4 is installed.
- EGL: vendor/version, surfaceless support, Wayland platform support and actual probe result.
- Buffer sharing: udmabuf/DMA-BUF export/import/fence capability, with source/proof.
- Display path: Wayland screencopy → fbdev/DECON, frame receipts and pan errors.
- `/dev/dri`: report absent as expected for vendor-kbase; do not flag it as generic GPU failure. Show DRM render-node availability as a separate capability.
- GPU utilization/frequency/memory only where trustworthy driver counters exist. Frequency is not utilization. Shared system RAM is not dedicated VRAM. Preserve `null`/N/A when attribution is impossible.
- Last probe timestamp, software fallback reason and copy/renderer error count.

Use exact source/provenance fields and distinguish `DETECTED`, `OPENED`, `CONTEXT_CREATED`, `GPU_JOB_SUBMITTED`, `WAYLAND_SURFACE_PRESENTED`, `WEBKIT_DMABUF_ACTIVE`, `OWNER_VISIBLE` and `BLOCKED`. Avoid a single green “GPU accelerated” badge that collapses all layers.

### 9. Stability, fallback and recovery

- Keep a known-good bootable graphics profile and working kbase compositor path.
- No global library replacement without a complete staged backup and verified ABI.
- Keep the previously restored Mesa EGL library backup intact; record hashes and do not overwrite `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland`.
- Keep `/var/backups/nuxel/kbase-gpu-*` intact.
- Preserve the current `/run/nuxel-gpu-fallback` contract: absence means no fallback trigger; if any probe fails, restore software WebKit env/profile without downgrading the Phoc kbase renderer.
- A WebKit GL failure must not create a compositor fallback marker or switch Phoc back to Pixman unless the compositor itself has failed and its own recovery policy explicitly requires it.
- Do not update all EGL/GLES libraries as a set unless ABI/version/dependency mapping is proven and rollback includes the entire set.
- Use a staged test launcher/profile and bounded canary session before switching the default Home process.
- Watch for WebKitWebProcess termination, GPU reset, kbase page fault, DMA-BUF import errors, memory leaks, fence timeouts, black surfaces, stuck frame callbacks and thermal instability.
- Preserve WebKit sandboxing, application isolation, TLS and session security. Do not disable sandbox to make GPU access possible.

### 10. Iterative physical testing

After automated checks and a staged deployment, physically use the S10+:

1. Boot to Home and confirm display remains healthy and responsive.
2. Open Graphics Settings and run each diagnostic probe.
3. Open Nuxel Home PWA; ensure all UI elements paint correctly.
4. Scroll through the app drawer and Home grid for at least 30 seconds.
5. Open the WebKit Browser and a known working HTTPS site; scroll a long page, animate transforms and open the keyboard.
6. Open Notes and type; switch away and back.
7. Open Quick Settings, Settings and lock/unlock.
8. Open a GTK3 native test app and a GTK4 test app separately.
9. Run a bounded reproducible GPU workload and inspect kbase activity while each workload is active.
10. Leave the phone active for 10 minutes and then idle for 5 minutes; check thermal stability, process restarts and fallback marker.

Record before/after metrics and actual visible behavior. A command returning success or Phoc owning `/dev/mali0` does not prove WebKitGTK acceleration.

## Non-negotiable safety rules

- No kernel, boot, DTB, initramfs, vendor firmware, partition or bootloader flash in this mission unless separately approved after a complete plan and verified recovery image. The current kbase state is precious; do not risk it casually.
- Never use TWRP to flash an unverified image. If a future kernel-level change is truly required, stop after producing an independently reviewable proposal, image hash, verified original boot backup, exact partition map and tested recovery plan. The current backup files are userspace/library backups, not automatically a valid full boot recovery.
- No `/dev/fb0` second writer; no direct framebuffer writes from PWA/WebKit/GTK/metrics service.
- No fabricated `/dev/dri` node or fake renderD symlink.
- No disabling SELinux, WebKit sandbox, seccomp, TLS checks, DMA-BUF validation or file permissions to force a renderer.
- No arbitrary debugfs writes, undocumented kbase ioctls or GPU register writes.
- No permanent max GPU/CPU clock, thermal limit changes or power-management bypass.
- Preserve USB console, Wi-Fi SSH, rootfs integrity, Notes/home data and current working screen.

## Required tests and deliverables

Create/update:

- `docs/beta-finalization/live/PWNAGE-50000-TODO.md`;
- `docs/beta-finalization/live/PWNAGE-50000-GRAPHICS-REPORT.md`;
- `docs/beta-finalization/live/evidence/pwnage-50000/` with baseline, probe output, WebKit traces, GPU context evidence, screenshots, performance CSV, process env snapshots (secrets redacted), library hashes, deployment record and rollback receipts;
- AArch64 EGL Wayland, GTK3 GL, GTK4 GSK and WebKitGTK probe source/tests;
- unit/integration tests for driver discovery, graphics profile policy, fallback selection and metrics parsing;
- updated Settings Graphics panel and Bridge/metrics schema;
- per-process graphics profile/wrapper implementation;
- optimized `nuxel-wl-fb` code only if benchmark proves a real improvement;
- rootfs integration for all required binaries/configs/units and cache/version bumps.

Run all existing relevant tests plus new probes. Report each layer separately with these statuses: `SOURCE_VERIFIED`, `DEPLOYMENT_VERIFIED`, `GPU_CONTEXT_VERIFIED`, `WAYLAND_EGL_VERIFIED`, `DMABUF_PRESENTATION_VERIFIED`, `WEBKIT_ACCELERATION_VERIFIED`, `GTK3_GL_VERIFIED`, `GTK4_GL_VERIFIED`, `BRIDGE_PERFORMANCE_VERIFIED`, `OWNER_VISIBLE`, `BLOCKED` or `NOT_TESTED`.

## Definition of done

- Phoc's existing kbase GPU acceleration remains intact; `FRAMES_OK` remains true and DECON pan failures remain zero.
- The real WebKitGTK accelerated compositing path works on the physical handset with genuine Mali execution and working DMA-BUF/Wayland presentation, or a precise technical blocker is proven after the valid paths have been tested.
- WebKit Home/Browser content is visibly correct, interactive and stable with acceleration enabled.
- GTK3 and GTK4 are diagnosed independently; supported native apps use hardware rendering, unsupported ones retain safe per-app software fallback.
- No global forced-software env remains where it prevents a proven accelerated process; no unsupported GL forcing causes startup failures.
- Bridge final-copy performance is measured and improved independently where possible.
- Graphics Settings accurately reports each layer, not just GPU detection.
- The default boot and working compositor survive repeated restarts and extended testing.
- All user data, working backups, USB console and network recovery paths remain intact.

**Do not stop at removing `LIBGL_ALWAYS_SOFTWARE=1`. Do not stop at an EGL context. Finish the entire WebKitGTK Wayland accelerated-buffer path and prove it on the physical Nuxel screen.**
