# PWNAGE-53000 — FINISH MALI-G76 ACCELERATION FOR WEBKITGTK & GTK

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820 / Mali-G76 MP12  
**OS:** Nuxel, custom Fedora-based ARM64 Linux  
**Known-good baseline:** Samsung vendor `mali_kbase` on `/dev/mali0`; Phoc GPU path active; `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web` active; Bridge `FRAMES_OK`; `decon_pan_failed=0`; `/run/nuxel-gpu-fallback` absent; `/dev/fb0` 1440×3040, virtual 1440×6080; no `/dev/dri` on this vendor kernel. Phoc holds `/dev/mali0`, `/dev/udmabuf` and a DMA-BUF object; kbase debugfs shows a Phoc GPU context.

## OBJECTIVE

Finish the remaining application graphics path. **Do not redo GPU detection or replace the working kbase/Phoc/DECON baseline.** The compositor is GPU-accelerated, but GTK GL initialization fails and WebKitGTK uses software compositing. A prior Wayland-enabled Mesa build was tested and reverted. The current Mesa kbase path is surfaceless-only. Phoc crashes in the linux-dmabuf path when WebKit tries accelerated buffers. The final screencopy → `/dev/fb0` scaling/copy remains CPU work.

Implement and prove:

**Mali rendering → EGL Wayland → DMA-BUF export → linux-dmabuf negotiation → safe Phoc import → GTK/GDK/WebKit UI-process import → Nuxel display bridge → DECON/AMOLED.**

Each stage has to be independently tested. `/dev/mali0` open, a kbase context, or a GPU-enabled Phoc is not proof that WebKitGTK is accelerated.

## EXECUTION ORDER

### 1. Capture the exact failure

Determine whether the failing process is Phoc itself, wlroots, WebKit UI process, WebKit web process, GTK/GDK, Mesa or the kbase kernel driver. Capture the exact process exit code, coredump/backtrace, build IDs, journal/kernel logs, Wayland protocol trace, Mesa/EGL loader diagnostics and WebKit/GTK logs. Do not label a client protocol disconnect a Phoc crash.

Reproduce in a controlled local test page. First reproduce with a minimal native Wayland DMA-BUF client without WebKit; this separates compositor import from WebKit's exporter.

### 2. Repair linux-dmabuf safely

Inspect the exact Phoc/wlroots version and its linux-dmabuf implementation. Record protocol version, supported format/modifier feedback, target device, plane count, offsets, strides, FD ownership/lifetime, buffer release, fences and synchronization.

Validate every advertised `(DRM fourcc, modifier)` pair against the actual kbase allocator and Phoc importer. Start with a known-supported linear format. Do not advertise tiled/AFBC/compressed modifiers without proof. Validate buffer dimensions, plane count, offsets, strides and bounds before import. Fix the crash root cause; do not merely disable DMA-BUF globally.

Unsupported formats or runtime import failures must be handled gracefully. Phoc must not crash, dereference invalid planes, use freed buffers, leak FDs, deadlock on fences or corrupt the current visible surface. Add regression tests for malformed metadata, unsupported modifiers, failed imports, delayed fences, client disconnect and repeated buffer creation/destruction.

### 3. Prove EGL Wayland independently

The current Mesa kbase path is surfaceless-only. Determine whether it can support `EGL_PLATFORM_WAYLAND` and a real Wayland window surface using the existing kbase kernel driver. Do not assume that a `/dev/dri/renderD*` node exists or is required; prove the actual device selection, allocator and WSI requirements for installed Mesa/WebKit versions.

Build a minimal EGL Wayland test client under the same user, Wayland socket, environment and libraries as Nuxel apps. It must connect, create a surface/config/context, render a shader pattern, swap repeatedly, show the expected image, prove the renderer is Mali rather than llvmpipe/softpipe, and show kbase activity during the workload.

### 4. Investigate candidate Mesa paths in isolation

Compare:
- the current surfaceless kbase Mesa build;
- a compatible vendor EGL path, if available and licensed;
- upstream Mesa Panfrost (only if its kernel-driver ABI requirements are actually met);
- the experimental `JimVulkan/mali-panfrost` kbase port.

The public kbase port reports Mali-G76 testing on an Exynos 9820 Galaxy S10e, but its documented presentation path is Android gralloc. That is not proof of native Linux Wayland WSI or GTK/WebKit DMA-BUF integration. Inspect its source, commit, license, dependencies, Android/NDK/gralloc requirements, EGL platforms and export path. Build it in a separate prefix; never replace system Mesa until it passes native EGL Wayland and DMA-BUF tests.

Do not symlink `/dev/mali0` to a fake DRM render node. Do not assume generic Panfrost Mesa userspace can speak the Samsung kbase ABI.

### 5. Fix GTK/GDK GL

Inventory exact GTK3/GTK4, GDK Wayland, EGL, libEGL, libGLES, Mesa, WebKitGTK and loader versions. Capture actual renderer/platform selection and all environment overrides. In particular inspect `LIBGL_ALWAYS_SOFTWARE`, `GDK_GL`, `GDK_BACKEND`, `EGL_PLATFORM`, `MESA_LOADER_DRIVER_OVERRIDE`, and WebKit acceleration settings in systemd units, launch wrappers and session files.

Do not delete software-forcing variables globally. Replace them with explicit per-process graphics profiles after candidate tests pass.

Build a small GTK test app with GL rendering and, where the installed GTK supports it, DMA-BUF texture import. Test GTK3 and GTK4 separately. Use supported `GDK_DEBUG=dmabuf` / `GDK_DEBUG=offload` diagnostics only after verifying those flags exist in the installed GTK version.

### 6. Fix WebKitGTK accelerated compositing

Trace the installed WebKitGTK version's actual accelerated backing-store implementation. GTK WebKit's accelerated path uses DMA-BUF buffers for composited frames; WebKit's web process chooses an allocator/device and supported format/modifier, while the UI process imports and presents the buffers. Depending on GTK/GDK version and renderer, import may use `GdkDmabufTextureBuilder` with EGL or Vulkan.

Prove separately:
- WebKit web process EGL/GL renderer is Mali;
- accelerated compositing is actually enabled;
- DMA-BUF allocation/export succeeds;
- buffer metadata matches the advertised format/modifier;
- GTK UI process imports the buffer;
- fence/synchronization completes;
- frame becomes visible;
- Phoc remains alive and stable.

Create a local diagnostic PWA with static blocks, scrolling, CSS transforms/opacity, composited layers, Canvas 2D, WebGL only if supported, local video only after basic compositing works, repeated navigation and stress cycles. Do not use internet sites or private user content as test pages.

### 7. Keep per-app fallback

Provide explicit profiles:
- `software-safe`;
- `gpu-rendered-shm-presented`;
- `gpu-rendered-dmabuf-presented`;
- `fully-accelerated`.

The names must reflect measured facts. If rendering is GPU-backed but presentation uses shared memory, do not call it DMA-BUF accelerated. Roll out in order: diagnostic client → GTK test app → WebKit test app → disposable PWA → Settings → Home → remaining apps. Keep lockscreen/Home/Settings able to fall back safely. An import failure must not take down Phoc.

### 8. Optimize final framebuffer bridge only after WebKit works

Profile active `nuxel-wl-fb` source and binary. Measure screencopy latency, allocation/reuse, full-frame versus damage updates, pixel conversion, scaling, memory bandwidth, framebuffer stride and pan/DECON timing. Consider reusable aligned buffers, avoiding unnecessary conversion, bounded damage-region copies and NEON only after correctness tests.

Keep exactly one `/dev/fb0` writer. Do not assume `/dev/fb0` can import DMA-BUF directly; no DRM/KMS node currently exists. Report the remaining CPU copy honestly.

## SAFETY AND ROLLBACK

- Preserve current kbase/Phoc/DECON baseline and `FRAMES_OK`.
- Preserve `/var/backups/nuxel/kbase-gpu-*` and `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland`.
- Create a new hash-verified backup before changing any graphics libraries.
- Build and test in isolated prefixes first; do not replace Mesa/GTK/WebKit/Phoc system-wide for an unproven candidate.
- Keep a known-good software WebKit profile and accelerated-compositor profile.
- Roll back immediately on Phoc crash, blank/frozen display, DECON pan errors, kbase reset, repeated protocol failures or inability to reach Home/Settings.
- Do not flash kernel/boot image, alter partitions, unload kbase or change bootloader in this mission. If a kernel ABI change is proven necessary, stop and prepare a separate owner-approved TWRP plan.
- Do not add another `/dev/fb0` writer or bypass `nuxel-wl-fb`.

## DELIVERABLES

Create:
- `docs/beta-finalization/live/PWNAGE-53000-TODO.md`
- `docs/beta-finalization/live/evidence/pwnage-53000/{baseline,crash,dmabuf,egl,gtk,webkit,performance,deployment}/`

Include crash/backtraces, protocol traces, exact build versions, EGL test outputs, supported format/modifier table, WebKit renderer evidence, performance before/after, binary hashes, deployment and rollback proof. Modify the actual active build/install path, not an unused source copy. Add automated regression tests for the exact crash.

## DEFINITION OF DONE

- EGL Wayland surface works on the Nuxel session and renders on Mali-G76, not llvmpipe.
- GTK GL initializes and renders on Wayland.
- WebKitGTK accelerated compositing is confirmed active.
- WebKit exports DMA-BUF and GTK/GDK imports/presents it correctly.
- Phoc safely imports supported formats and never crashes on unsupported/malformed buffers.
- Fallback remains reliable and per-app.
- `FRAMES_OK`, `decon_pan_failed=0`, `/dev/fb0` geometry and single-owner invariant remain intact.
- CPU cost/latency improvement is measured; remaining CPU screencopy/fbdev work is clearly disclosed.
- All changes are reproducible, packaged and reversible.

**Do not call this done because `/dev/mali0` exists or Phoc alone is accelerated. The target is real WebKitGTK and GTK application acceleration on the physical Nuxel phone.**
