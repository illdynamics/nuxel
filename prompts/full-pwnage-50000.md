# FULL-PWNAGE-50000
# NUXEL — FINAL MALI-G76 / KBASE → WAYLAND EGL → DMA-BUF → WEBKITGTK HARDWARE ACCELERATION INTEGRATION

## Exhaustive source-level engineering, ABI investigation, graphics-path implementation, safe deployment, performance measurement and physical S10+ acceptance mission

**Mission ID:** PWNAGE-50000  
**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820 / Mali-G76 MP12  
**OS:** Nuxel, Fedora ARM64 derivative  
**Kernel:** Samsung downstream 4.14.253 kbase vendor kernel (verify exact live release and commit)  
**Compositor:** Phoc / Wayland, now reported by owner to use Mali kbase acceleration  
**Graphics kernel interface:** vendor `/dev/mali0`, `/dev/udmabuf`, `dmabuf_udmabuf`; no `/dev/dri` in this current kbase architecture  
**Home host:** native GTK3 + WebKit2GTK 4.1 (`tools/s10plus/a45/nuxel-pwa-host.c` in the supplied source snapshot; verify current active build)  
**Display presentation:** Wayland screencopy → `nuxel-wl-fb` → single `/dev/fb0` owner → Samsung DECON/AMOLED  
**Existing metrics:** `services/nuxel-metrics/nuxel-metricsd.c` and socket activation  
**Mission type:** close the application-rendering acceleration gap while preserving the already-working compositor and display pipeline.

---

# 0. MISSION PURPOSE AND SUCCESS DEFINITION

PWNAGE-48000 established a major milestone: Phoc now uses the Mali-G76 through the vendor `mali_kbase` kernel driver. The GPU is no longer merely detected; the owner reports that Phoc owns GPU device descriptors, a kbase debugfs GPU context is attributed to `phoc`, and the display bridge reports healthy frames and zero DECON pan failures.

The remaining problem is application-side rendering:

- WebKitGTK and GTK GL initialization still fail.
- WebKitGTK accelerated compositing is not active.
- The current Mesa kbase path is surfaceless-only.
- A Mesa build configured with Wayland support was tried and reverted because WebKit/GTK still could not initialize the required rendering path.
- The screen is visible because Phoc and `nuxel-wl-fb` work, but WebKit and the GTK host still render through software fallback.
- The final Wayland screencopy → framebuffer upscale/copy still costs CPU.

This mission is the final integration pass for that remaining gap. It must not undo the working kbase compositor, switch the full phone back to Pixman, replace the known-good Mesa stack globally or destabilize the phone to chase an unproven EGL path.

The primary objective is to make the actual Home PWA host and WebKitGTK WebProcess create and use a compatible Mali-backed accelerated compositing path, sharing the resulting accelerated backing-store buffers with the GTK UI process and Phoc on the real Wayland screen.

The secondary objective is to accelerate supported GTK apps independently and optimize the unavoidable or remaining `nuxel-wl-fb` final copy. These are different acceptance axes. A WebKit GPU PASS does not prove the bridge CPU copy is gone; a Phoc GPU PASS does not prove WebKit is accelerated.

The mission may finish with a technically honest partial result if a real kernel ABI/driver/Wayland buffer-sharing blocker cannot be solved safely in the existing userspace. If so, it must leave the working compositor intact, provide the exact upstream/vendor issue and next required component, retain software fallback and never mark WebKit acceleration as complete.

---

# 1. CURRENT STATE — OWNER-REPORTED POST-PWNAGE-48000 BASELINE

The following is the latest owner-provided live-device evidence. Treat it as the starting baseline and re-validate it on the running phone before changes.

## 1.1 Reported working kbase compositor state

- `phoc` holds three file descriptors to `/dev/mali0`.
- `phoc` holds one descriptor to `/dev/udmabuf`.
- `phoc` also holds an `anon_inode:dmabuf_udmabuf` object.
- The kbase debugfs context table reports a GPU context owned by `phoc`.
- `nuxel-wayland`, `nuxel-wl-fb` and `nuxel-web` are all active.
- The local Bridge reports `FRAMES_OK`.
- `decon_pan_failed=0`.
- `/run/nuxel-gpu-fallback` is absent.
- `/dev/fb0` is restored and usable.
- Physical panel geometry: 1440×3040.
- Virtual framebuffer geometry: 1440×6080.
- `/dev/dri` is absent; that is expected for the current vendor-kbase path and is not itself proof of a broken Mali compositor.

## 1.2 Remaining reported limitation

- GTK reports `failed to initialize GL`.
- WebKitGTK does not use the desired accelerated compositing path.
- The tested Mesa-on-kbase driver supports surfaceless EGL but not the working Wayland window-system/buffer-sharing path needed by the existing WebKitGTK setup.
- A Wayland-enabled Mesa build was attempted and still failed WebKit/GTK GL initialization; it was reverted.
- The current Nuxel presentation bridge's final screencopy → `/dev/fb0` upscale/copy remains CPU work.

## 1.3 Recovery assets and history

Owner reports:

- kbase backups under `/var/backups/nuxel/kbase-gpu-*`;
- pre-Wayland-test EGL library backup at `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland`;
- `docs/beta-finalization/live/PWNAGE-48000-KBASE-GPU-REPORT.md`;
- evidence under `docs/beta-finalization/live/evidence/pwnage-48000-kbase-gpu/`;
- commits `90ff0d6` (`feat(pwnage-48000): S10+ kbase GPU acceleration`), `9340301` (post-reboot BOOT partition readback) and `01cd482` (post-reboot AMOLED frame capture).

**Do not overwrite, rename, delete or assume the sufficiency of those backups.** First inventory their exact contents, hashes, architecture, paths and restore procedure. A library backup is not a full bootable kernel/boot partition backup.

## 1.4 Supplied repository archive may be stale

The available `nuxel-main (10)(1).zip` contains useful source references but predates the latest kbase work. In that snapshot:

- `tools/s10plus/a45/nuxel-session.sh` exports software forcing variables;
- `services/nuxel-bridge/src/api.py` forces software for native GUI applications;
- `tools/s10plus/a45/nuxel-pwa-host.c` is a GTK3/WebKit2GTK 4.1 host;
- the rootfs builder compiles `nuxel-wl-fb` from `tools/s10plus/a34/nuxel-wl-fb.c`;
- `services/nuxel-metrics/nuxel-metricsd.c` is already compiled/installed by the rootfs builder with socket activation.

The live working tree and installed binaries after commits above are authoritative. Compare archive, current Git checkout and live phone hashes before any edits. Do not revert the kbase work by copying stale archive files into the current tree.

---

# 2. FUNDAMENTAL GRAPHICS ARCHITECTURE — KEEP THESE LAYERS SEPARATE

A graphics stack is not one boolean. Build an explicit layered model and status for each stage.

## 2.1 Layer A — Mali kernel driver and GPU execution

Current device path: vendor `/dev/mali0` managed by `mali_kbase` on the existing 4.14.253 vendor kernel.

Evidence can include:

- open/owned GPU device file descriptors;
- kbase context objects;
- submitted GPU jobs and hardware completion counters where the driver exposes them;
- GPU frequency/busy accounting where reliable;
- kbase debugfs diagnostic output;
- successful EGL/GLES workload that produces measured activity.

A process holding `/dev/mali0` is not alone proof it submitted useful GPU work. The current user report has a stronger context-owner receipt; reconfirm actual activity during workloads.

## 2.2 Layer B — EGL/GLES user-space driver and WSI

The EGL library is a loader/API entry point. The selected EGL vendor/driver determines the supported platform(s) and rendering backend. The current Mesa kbase integration is reported to support surfaceless contexts only. Surfaceless rendering proves that the GPU can create/execute an offscreen context but not that it can create a Wayland window surface or share buffers with Phoc.

The missing requirement is a valid native Wayland window-system integration and compatible buffer allocation/export/import path. Do not treat `-D platforms=wayland` as a magic switch that automatically converts a surfaceless driver into a working Wayland implementation.

Mesa documentation: `https://docs.mesa3d.org/egl.html`. It explains that EGL is window-system-neutral at the top level and the selected driver determines supported platforms. The driver must implement the actual platform backend.

## 2.3 Layer C — Wayland client surface and buffer sharing

A Wayland EGL client must be able to create a surface backed by the actual EGL driver. The buffer must be transferable to the compositor through a supported protocol/extension, commonly a DMA-BUF path or a supported vendor Wayland-buffer integration. The compositor must import the memory layout and synchronize access correctly.

Things to prove, not assume:

- `EGL_EXT_platform_wayland` or an equivalent supported EGL platform extension is present and actually implemented;
- `eglGetPlatformDisplay(EGL_PLATFORM_WAYLAND_KHR, ...)` or the matching extension path succeeds;
- `wl_egl_window` or an equivalent Wayland surface target can be created;
- a real GLES context can render and `eglSwapBuffers()` submits a frame;
- the buffer is exported/shareable and the compositor imports it;
- the compositor supports the fourcc/modifier/format and synchronization required by that producer;
- fences are honored and buffer lifetime/release is correct;
- the result appears on the physical AMOLED through the current working path.

An `EGLDisplay`, GL context, `wl_surface`, DMA-BUF file descriptor or imported buffer by itself does not prove the whole path.

## 2.4 Layer D — Phoc compositor renderer

The owner reports Phoc is GPU accelerated through kbase. Confirm which renderer is actually selected in the current live process and what buffer import path it uses. If Phoc uses a custom/shared-memory/udmabuf path, document it and do not rewrite it merely because it differs from standard DRM/GBM desktop setups.

Keep Phoc's GPU context and its currently working renderer. Do not change Phoc to Pixman as a way to make WebKit stop crashing.

## 2.5 Layer E — WebKitGTK accelerated compositing

WebKitGTK has separate accelerated and non-accelerated frame transport modes. The WebKitGTK/WPE graphics documentation describes non-accelerated mode as shared-memory bitmap frames that are painted through the GTK UI process, and accelerated mode as DMA-BUF buffers handled by the accelerated backing store (`AcceleratedBackingStoreDMABuf`). See:

`https://docs.webkit.org/Ports/WebKitGTK%20and%20WPE%20WebKit/Graphics.html`

The target is not just WebGL or `canvas` support. It is WebKit's actual page compositing path for CSS transforms, opacity, scrolling, animations, video surfaces where supported and normal PWA content.

The GTK UI process and Wayland compositor must be able to consume WebKit's frames without forcing a readback/copy path that negates acceleration.

## 2.6 Layer F — GTK toolkit drawing

The Nuxel Home host in the supplied source is GTK3 + WebKit2GTK 4.1. GTK3's rendering path and GL context support are not controlled by the GTK4 `GSK_RENDERER` environment setting. GTK4 uses GSK and has its own renderer selection, where `cairo` versus a GL/NGL renderer can be relevant depending on installed GTK version/build.

Test GTK3 and GTK4 independently. Do not call GTK4 GSK acceleration a WebKitGTK success.

## 2.7 Layer G — final physical panel presentation

The current display path ends with Wayland screencopy and the single `nuxel-wl-fb` process writing to `/dev/fb0` and committing with `FBIOPAN_DISPLAY` for this Samsung command-mode panel.

The owner reports current DECON pan failures are zero. Preserve that. A GPU-accelerated compositor/WebKit can still have a CPU copy in the final output stage; this is a separate optimization target.

---

# 3. SOURCE AUDIT AND CURRENT BUILD CONTRACT

## 3.1 Required source paths

Inspect the latest current checkout, not just the supplied archive. Start with:

```text
services/nuxel-metrics/nuxel-metricsd.c
services/nuxel-metrics/nuxel-metrics.service
services/nuxel-metrics/nuxel-metrics.socket
pwa/nuxel-home/js/system-monitor.js

services/nuxel-bridge/src/api.py
services/nuxel-session/systemd/
tools/s10plus/a45/nuxel-session.sh
tools/s10plus/a45/nuxel-pwa-host.c

images/s10plus/build-phone-rootfs-inside-fedora.sh
images/s10plus/packages-manifest.json

 tools/s10plus/a34/nuxel-wl-fb.c
 tools/s10plus/a67/nuxel-wl-fb.c
services/nuxel-session/systemd/nuxel-wl-fb.service

configs/nuxel/graphics/
configs/nuxel/display/
docs/beta-finalization/live/PWNAGE-48000-KBASE-GPU-REPORT.md
docs/beta-finalization/live/evidence/pwnage-48000-kbase-gpu/
```

Additional relevant paths discovered in the provided source snapshot:

- `NUXEL-A67-OPERATION-HARDWARE-ACCEL-SMOOTHNESS-SLIDE-PENGUIN-16000-UBERPROMPT.md` — previous GPU investigation plan.
- `NUXEL-063-BLOCKER-REPAIR-PROMPTS/prompts/07-gpu-meter.md` — truthful GPU utilization/frequency instrumentation.
- `NUXEL-063-BLOCKER-REPAIR-PROMPTS/prompts/08-gpu-shared-memory.md` — shared GPU-memory accounting.
- `NUXEL-063-BLOCKER-REPAIR-PROMPTS/prompts/12-native-webkit-browser.md` — browser implementation background.
- `docs/a53/BASELINE-AND-HARDWARE.md` — older environment baseline; not current runtime truth.
- `docs/performance/A50/02-DISPLAY-RESOLUTION-AND-RENDERING-TRUTH.md` — earlier rendering and copy path.
- `docs/a69/FINAL-STATUS.md` — earlier software-rendering CPU measurements.
- `docs/live/v0.6.3-beta-20261020/27-wayland-unit-session.txt` — old session environment.
- `docs/live/v0.6.3-beta-20261020/28-webkit-processes.txt` and `29-webkit-webproc-reload.txt` — historical process observations.

## 3.2 Existing metrics daemon: extend it

The current rootfs builder already compiles `services/nuxel-metrics/nuxel-metricsd.c` and installs:

- `/usr/lib/nuxel/nuxel-metricsd`;
- `/etc/systemd/system/nuxel-metrics.service`;
- `/etc/systemd/system/nuxel-metrics.socket`;
- socket activation under `sockets.target.wants`.

Do not add a second metrics daemon or bypass this service with a PWA polling `/sys` directly. Extend its schema carefully and keep it bounded/read-only.

The existing daemon uses fixed paths in the source snapshot, including:

- `/sys/devices/platform/18500000.mali/utilization`;
- `/sys/devices/platform/18500000.mali/clock`;
- `/sys/kernel/gpu/gpu_busy`;
- `/sys/kernel/gpu/gpu_memory`.

These paths must be re-checked against the current kbase driver; a path existing or reading a number does not establish a trustworthy metric. The daemon currently tracks CPU/memory/GPU percentage/frequency/memory fields and emits JSON. GPU memory is documented as shared system RAM and should be `null`/N/A unless genuine attribution is available.

The current socket listens on `127.0.0.1:8624` and is socket activated. Preserve that local-only exposure unless the established Bridge contract requires something else. Do not expose unauthenticated GPU diagnostics to LAN.

## 3.3 Existing software-forcing environment — critical

The checked archive explicitly sets software rendering in more than one process launch layer:

### Session launcher

`tools/s10plus/a45/nuxel-session.sh` includes:

```sh
export XDG_SESSION_TYPE=wayland
export GDK_BACKEND=wayland
export WEBKIT_DISABLE_COMPOSITING_MODE=1
export LIBGL_ALWAYS_SOFTWARE=1
export GSK_RENDERER=cairo
```

This older snapshot therefore prevents or discourages the very accelerated process we are trying to enable. Check the current post-PWNAGE-48000 script and running environment; it may have been changed in the current working tree.

### Native application launch

`services/nuxel-bridge/src/api.py` contains `NATIVE_LAUNCH_ENV` with:

```python
"GSK_RENDERER": "cairo",
"LIBGL_ALWAYS_SOFTWARE": "1",
"WEBKIT_DISABLE_COMPOSITING_MODE": "1",
```

The actual `_exec_native_app()` also supplies those values via `systemd-run --setenv`. The same variables may be used by both GTK3 and GTK4 native applications even though their toolkit meanings differ.

Remove or replace these only through the new profile mechanism and after a safe A/B test. Do not remove safety defaults from unrelated services.

## 3.4 Current WebKit host type

The supplied builder compiles `tools/s10plus/a45/nuxel-pwa-host.c` against:

- `gtk+-3.0`;
- `webkit2gtk-4.1`.

Historical logs show WebKitGTK 2.52.5, but the current exact installed version must be queried. The host uses `gtk_init`, `WebKitWebView`, WebKit settings, WebKit content manager and WebKit process supervision. Do not assume it is a GTK4 app.

The `nuxel-pwa-host` C binary is compiled in the rootfs builder; confirm the exact active source and build output. Do not patch a stale A33/A45 file that the current builder no longer compiles.

## 3.5 Framebuffer bridge source selection

The checked archive's rootfs builder compiles `tools/s10plus/a34/nuxel-wl-fb.c`, while `tools/s10plus/a67/nuxel-wl-fb.c` exists as a more recent source in the archive. The live PWNAGE-48000 status may have advanced this. Confirm the current builder, installed binary hash and process path before modifying code. A fix in an unused source generation is not deployed.

---

# 4. PHASE 0 — SAFETY, CHECKPOINT AND REPRODUCIBILITY

## 4.1 Verify current phone identity and state

Read and record:

- `uname -a`, Fedora release, architecture and kernel build ID;
- current booted kernel/boot image identification;
- Git commit, dirty files and the three PWNAGE-48000 commits;
- running Phoc PID, binary path, command line, cgroup, environment profile and GPU file descriptors;
- running `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web`, `nuxel-pwa-host`, WebKitWebProcess and native GTK apps;
- device file and sysfs state for Mali/udmabuf/fb0/dmabuf heaps;
- current `FRAMES_OK`, `decon_pan_failed`, `decon_pan_ok` and fallback marker;
- current framebuffer geometry, physical panel geometry, `line_length`, `smem_len`, pixel format and virtual dimensions;
- EGL/Mesa/GLES/WebKit/GTK package versions and library hashes;
- current environment variables only for the relevant processes (redact unrelated secrets).

Do not assume the archive and live machine match.

## 4.2 Preserve recovery

Before modifying userspace libraries, drivers, host, Phoc config or framebuffer bridge:

- verify all existing `/var/backups/nuxel/kbase-gpu-*` backups;
- hash and preserve the pre-Wayland-test Mesa EGL backup;
- make fresh backups of any changed package/library/config/host binary;
- store a known-good working graphics profile and a tested restore script outside the paths being modified;
- confirm the USB serial console and Wi-Fi SSH route work while Home is running;
- ensure a remote process can restore the software WebKit profile without needing WebKit itself.

Do not rely on `/run` files for persistent rollback. Do not claim a backup is boot-recoverable unless it is a verified exact image of the required partition and has a known restore process.

## 4.3 No destructive operation in this mission

This is a userspace graphics-path mission. No kernel flashing, TWRP flashing, boot partition modification, DTB replacement, raw partition writes, bootloader, Odin, Heimdall, fastboot, Recovery/Download Mode, `dd` to block devices or forced reboot is permitted. If a kernel/DRM/driver change becomes necessary, stop and produce a separate evidence-backed proposal for owner approval.

---

# 5. PHASE 1 — BUILD A COMPLETE LIVE GRAPHICS TOPOLOGY MAP

Create a topology diagram and machine-readable status report with these edges:

```text
Home PWA / WebKitWebView
  -> WebKitWebProcess
  -> WebKit accelerated compositing / backing store
  -> EGL/GLES vendor/driver
  -> native Wayland WSI + buffer producer
  -> Wayland DMA-BUF / supported buffer protocol
  -> Phoc renderer / importer
  -> Wayland screencopy (current bridge contract)
  -> nuxel-wl-fb SHM buffer / copy / scaling / format conversion
  -> /dev/fb0 mmap + FBIOPAN_DISPLAY
  -> Samsung DECON / AMOLED panel
```

For any alternative pipeline (e.g. a direct DMA-BUF path), diagram that separately and identify which existing links it removes and which new protocols/owners it introduces.

## 5.1 Driver identification

Inspect:

- `/dev/mali0` ownership, mode, group and process open fds;
- kbase debugfs context/job/memory counters;
- driver name/version/ABI in sysfs/debugfs/logs if exposed;
- module/built-in status and kernel config where available;
- user-space EGL/GLES driver files and their SONAMEs;
- `ldd`/ELF dependencies for each diagnostic/app (no blind library swapping);
- whether the currently active `libEGL.so`, `libGLESv2.so`, Mesa vendor drivers and any `libmali.so` are consistent versions/ABIs;
- whether the GPU context observed for Phoc is its current live session and whether it receives GPU jobs during compositor work.

Do not use `glxinfo` as a substitute for Wayland/GLES validation; there may be no X server and the relevant path is EGL Wayland.

## 5.2 EGL capability enumeration

Build/read a diagnostic executable that reports:

- `eglGetProcAddress` and available EGL client extensions;
- `eglQueryString(EGL_NO_DISPLAY, EGL_EXTENSIONS)` where supported;
- actual platform extensions (`EGL_EXT_platform_wayland`, `EGL_KHR_platform_wayland`, surfaceless support, DMA-BUF import/export extensions);
- vendor/version/APIs supported;
- `EGL_PLATFORM_SURFACELESS_MESA` context creation;
- Wayland platform display creation against the exact active `WAYLAND_DISPLAY`/`XDG_RUNTIME_DIR`;
- config selection and GLES2/GLES3 context creation;
- `wl_egl_window` creation and buffer swap;
- real renderer string and GPU job evidence during the workload.

Run a separate test under the actual `nuxel` Home session credentials, not only root SSH. Correct Wayland socket permissions and `XDG_RUNTIME_DIR` matter. Use environment snapshots with secrets redacted.

## 5.3 Wayland protocol and buffer capability

Inspect the live compositor registry and supported extensions:

- `zwp_linux_dmabuf_v1` / version;
- supported format/modifier combinations;
- `wl_drm` only if present and supported (do not assume it exists);
- `EGL_WL_bind_wayland_display` and the matching EGL implementation if used;
- explicit/implicit fence protocol support and synchronization mechanism;
- `zwlr_screencopy_manager_v1` capabilities (current bridge);
- whether Phoc can import the exact buffer type returned by the EGL producer.

Use `wayland-info` or a small registry probe where available. Do not assume because `udmabuf` appears in Phoc's fd table that it is the WebKit buffer path; trace actual buffer fds/protocol messages.

---

# 6. PHASE 2 — INVESTIGATE REAL WAYS TO GIVE KBASE A WAYLAND WSI

The key problem is not the GPU kernel driver itself at this stage; the owner has it working in Phoc. The missing component is the application rendering/surface-sharing path compatible with the same GPU and compositor.

## 6.1 Route A — compatible vendor Mali userspace (priority investigation)

Investigate whether a legitimate Samsung/ARM Mali userspace package matching the current Exynos 9820 `mali_kbase` ABI is available and licensed for this Linux rootfs. Candidate components may include vendor EGL/GLES libraries and Wayland WSI implementation.

Required proof:

- correct ARM64 ELF architecture;
- kbase ABI compatibility with this exact kernel's ioctls/ABI version;
- EGL Wayland platform support in the library, not merely Android `EGL_KHR_platform_android` or surfaceless;
- native Linux Wayland WSI implementation;
- buffer format/export/import accepted by Phoc;
- complete dependencies and redistribution rights/provenance;
- no dependency on Android gralloc, Android linker namespaces or Android-only services.

If vendor `libmali` supports native Wayland and can share its buffers with Phoc, it may be a better match than forcing Mesa's DRI-based path to operate without a DRM render node. However, do not mix vendor `libEGL` with an incompatible Mesa `libGLES` or loader. Treat the whole driver library group as one ABI-tested set.

## 6.2 Route B — Mesa kbase Wayland WSI implementation

Investigate the current Mesa-on-kbase integration source/patches. Determine why it is surfaceless-only. Identify which pieces are missing:

- DRI image/buffer allocation interface;
- Wayland platform support in EGL;
- DMA-BUF allocation/export;
- modifiers/format negotiation;
- implicit/explicit synchronization/fences;
- Wayland `wl_buffer`/linux-dmabuf creation;
- Phoc import capability.

A Mesa build option that enables the `wayland` platform is necessary in some configurations but not sufficient: the driver must implement the required platform and buffer interfaces. Mesa docs: `https://docs.mesa3d.org/egl.html` and `https://docs.mesa3d.org/systems.html`.

If modifying Mesa is feasible:

- branch from the exact known-good Mesa commit/patchset used by the kbase success;
- record subprojects/meson options/build flags and all patches;
- add Wayland WSI without changing the working surfaceless path;
- preserve other drivers and software fallback;
- create an isolated prefix and run all probes against it;
- do not replace `/usr/lib64` libraries until the isolated tests pass completely;
- confirm `ldconfig` and RPATH do not accidentally load a mixed stack.

## 6.3 Route C — udmabuf integration

The owner observed `/dev/udmabuf` and `anon_inode:dmabuf_udmabuf` open in Phoc. Investigate whether the current Phoc kbase renderer uses udmabuf for its own buffers and whether it can accept WebKit/GTK memory from an udmabuf export.

Check:

- exact kernel udmabuf implementation/API and documentation;
- memory pinning/contiguity/SG constraints;
- supported allocation size/alignment;
- cache coherency requirements on Exynos/Mali;
- DMA mapping/IOMMU ownership and lifetime;
- format and stride negotiation;
- fences/sync semantics;
- import path into Phoc and GPU job submission.

Do not map arbitrary process memory or another process's pages into GPU-visible buffers. Only use well-defined allocated memory with correct pinning and synchronization. Presence of udmabuf is a research lead, not a green light to write a custom allocator without understanding memory ownership.

## 6.4 Route D — alternative WebKit buffer transport

Inspect the installed WebKit GTK port's accelerated backing-store implementation. Determine whether its exact build can consume a non-DRM vendor Wayland EGL implementation or whether it hard-depends on its DMA-BUF accelerated backing-store configuration.

If no compatible native DMA-BUF import/export path exists, consider a scoped, well-defined integration proposal only if it can preserve WebKit process isolation and avoid large CPU readbacks. Do not fork WebKit or patch its compositing backend blindly. An experimental shared-memory/udmabuf path must demonstrate end-to-end ownership/synchronization and be compared against normal software fallback; it must not silently be labelled accelerated if all buffers are copied through CPU memory.

## 6.5 Route decision gate

At the end of the investigation, create `GPU-WEBKIT-WSI-DECISION.md` with:

- each route evaluated;
- exact missing symbol/protocol/ABI/driver element;
- evidence and logs;
- complexity/risk;
- feasibility on current 4.14 kbase kernel;
- whether user-space-only implementation is safe;
- whether separate kernel/driver work is truly unavoidable.

Do not stop at the first failed Mesa Wayland build. Test vendor WSI and the actual Wayland buffer-sharing contract before concluding there is no path. Conversely, do not spend days forcing a known unsupported interface if the missing ABI is proven absent.

---

# 7. PHASE 3 — CONTROLLED SOFTWARE PROFILE AND PER-PROCESS ENVIRONMENT

## 7.1 Do not leave global software forcing in place after acceleration works

The older archive has these explicit overrides in the session path and native launch path:

- `WEBKIT_DISABLE_COMPOSITING_MODE=1` disables WebKit accelerated compositing;
- `LIBGL_ALWAYS_SOFTWARE=1` forces Mesa software rendering;
- `GSK_RENDERER=cairo` selects GTK4 Cairo renderer where applicable.

These values must be audited in:

- `tools/s10plus/a45/nuxel-session.sh`;
- `services/nuxel-bridge/src/api.py` `NATIVE_LAUNCH_ENV`;
- `systemd-run --setenv` arguments in `_exec_native_app()`;
- systemd service Environment/EnvironmentFile entries;
- app-specific desktop Exec wrappers;
- any PWA host C code calling `setenv()` before `gtk_init()`.

Do not merely delete all values. Replace the old hardcoded environment with a validated graphics-profile policy.

## 7.2 Proposed profile schema

Implement a small versioned config, e.g. `/etc/nuxel/graphics/graphics-profile.json`, with per-process/per-API policies. Example conceptual state:

```json
{
  "schema_version": 1,
  "compositor": {"profile": "kbase-working", "allow_change": false},
  "webkitgtk": {"mode": "auto", "accelerated_candidate": "kbase-wayland", "fallback": "software"},
  "gtk3": {"mode": "auto", "fallback": "cairo"},
  "gtk4": {"mode": "auto", "renderer": "auto", "fallback": "cairo"},
  "presentation": {"mode": "current-wl-fb", "allow_dma_path": false},
  "diagnostics": {"last_probe": null}
}
```

Example only. Align with Nuxel config schema and API patterns.

Requirements:

- validate against a schema; reject unknown/unsafe modes;
- no client-supplied environment key/value injection;
- select only pre-defined known-good profiles;
- provide `auto`, `accelerated`, `software` modes as appropriate;
- support per-app fallback override;
- preserve a safe software profile for recovery;
- write atomically and back up prior profile;
- expose read-only state via Bridge;
- privileged profile changes require the existing authorized Settings/Bridge flow.

## 7.3 WebKit environment variables

WebKit documents `WEBKIT_FORCE_COMPOSITING_MODE=1` and `WEBKIT_DISABLE_COMPOSITING_MODE=1` as controls for accelerated compositing. See `https://trac.webkit.org/wiki/EnvironmentVariables`.

- Use `WEBKIT_FORCE_COMPOSITING_MODE=1` only in an isolated diagnostic trial if needed and only after the Wayland EGL/buffer path has passed its prerequisite probes.
- Do not set both force and disable.
- Do not set either globally for all processes.
- Default `auto` should let the installed WebKit choose the path when capabilities are present, and use known-good software mode when not.
- A forced mode that causes WebProcess crashes, black content or unsupported-buffer errors must auto-disable and revert.

## 7.4 `LIBGL_ALWAYS_SOFTWARE`

- Remove `LIBGL_ALWAYS_SOFTWARE=1` only from the process profile that has a proven hardware EGL driver.
- Do not remove it from a diagnostic fallback process where software rendering is deliberately required.
- Do not use `MESA_LOADER_DRIVER_OVERRIDE` or `EGL_PLATFORM` values blindly; set them only if the validated driver requires them and the probe confirms them.
- Verify the loaded `libEGL`, `libGLESv2`, DRI/vendor driver and WebKit WebProcess actually match the chosen profile.

## 7.5 `GSK_RENDERER`

- GTK3/WebKit2GTK 4.1 host is separate from GTK4 GSK renderer selection.
- GTK4 supports a GSK renderer setting, but valid choices depend on the installed GTK build/version and available backend. Query runtime diagnostics and test each supported mode.
- Do not claim a GTK3 WebKit acceleration fix because a GTK4 Adwaita demo uses GL.
- Do not force all native GTK4 apps to GL; per-app `auto` with Cairo fallback is safer.

## 7.6 Bridge launch contract

Extend `services/nuxel-bridge/src/api.py` launch logic to resolve a validated graphics profile for each registered app. Keep fixed executable/desktop ID resolution, existing UID/GID, D-Bus, Wayland socket, `HOME`, `PATH`, sandbox and capabilities unchanged unless a separate justified issue exists.

For the Home PWA host:

- apply the selected WebKitGTK profile before `gtk_init()` and WebKit initialization;
- ensure WebKit child processes inherit only intended display/graphics settings;
- record a redacted effective graphics profile in host diagnostics;
- keep restart limits and existing WebProcess supervision;
- if accelerated initialization fails, record precise reason and reload under software profile without entering an infinite restart loop.

For standalone native apps:

- set only the environment required by that app/toolkit;
- no arbitrary user-provided env overrides;
- maintain current user/session security and Wayland presentation;
- show the app's actual renderer status in Graphics Settings when it can be queried.

---

# 8. PHASE 4 — BUILD PROBES THAT PROVE EACH STAGE

Create a diagnostic suite, preferably under `tools/s10plus/graphics/` or the repo's existing hardware diagnostic conventions. All native binaries must be ARM64 and build reproducibly against the target Fedora packages.

## 8.1 Probe output contract

Every probe returns:

- unique probe ID/version;
- timestamp;
- device/kernel/user-space versions;
- process UID/GID and relevant display environment (redacted);
- detected device/driver/library versions;
- capability booleans with provenance;
- tested operation and result;
- specific failure code/message;
- exit code;
- whether it submitted GPU workload;
- whether a frame was physically displayed (only if verified).

Do not collapse `detected`, `opened`, `context_created`, `gpu_work_submitted`, `buffer_exported`, `compositor_imported`, `surface_presented` and `owner_visible` into one `success` boolean.

## 8.2 Kbase probe

- Open `/dev/mali0` using the documented supported kbase interface.
- Query available ABI/version/capabilities through safe supported ioctl calls.
- Create a context and submit a bounded, deterministic test workload if supported.
- Observe job completion and relevant counters.
- Close context/device cleanly.
- No raw kbase register access, undocumented destructive ioctl, arbitrary memory mapping or debugfs write.

## 8.3 Surfaceless EGL probe

This should preserve the known-good Mesa kbase surfaceless path as a control. It must report EGL vendor/version, GLES version, renderer string, context success, workload success and real kbase activity. Save output as a baseline and rerun after every experimental library change.

## 8.4 Wayland EGL probe

Run as the actual Nuxel session user under the actual Phoc session. Do not run solely as root over SSH.

1. Connect to the actual `WAYLAND_DISPLAY` using `XDG_RUNTIME_DIR`.
2. Enumerate relevant EGL extensions and Wayland globals.
3. Create an EGL platform display with the supported Wayland platform path.
4. Choose a compatible EGL config.
5. Create `wl_surface` and `wl_egl_window` (or the driver-supported equivalent).
6. Create GLES2/GLES3 context.
7. Draw a non-symmetric test pattern with colored corners and frame counter.
8. Swap buffers repeatedly.
9. Confirm Wayland compositor receives and imports the produced buffer.
10. Confirm the pattern visibly appears on the physical AMOLED and kbase activity changes during the test.
11. Destroy every resource correctly and repeat 100 times to detect leaks.

If failure occurs, report exact EGL error, library path/vendor, Wayland protocol state and likely missing extension. Do not just return `GL init failed`.

## 8.5 DMA-BUF export/import probe

Test real memory sharing independently:

- allocate only through the supported producer API;
- query fd identity, size, format, stride, modifier and plane metadata;
- export through the actual supported path;
- import in a test compositor path compatible with Phoc;
- render/read a deterministic image and verify all pixels;
- exercise fence/sync behavior;
- cycle buffer reuse and destroy/release;
- run under memory pressure and disconnect/restart tests.

Do not infer a DMA-BUF from the presence of an `anon_inode` alone. Determine whether it is a Linux DMA-BUF object and which exporter created it. Prove whether it is actually consumed by WebKit/Phoc.

## 8.6 GTK3 and GTK4 probes

Build two separate tests:

- GTK3/GDK GL test, matching the host runtime and API supported by the installed GTK3.
- GTK4 GSK GL/NGL test for the installed GTK4 runtime.

Both should show a deterministic animated GPU test pattern, report renderer/backend and run for 60 seconds. A GTK4 GL demo does not prove the GTK3 WebKit host works.

## 8.7 WebKitGTK probe

Build a minimal standalone GTK3 + WebKit2GTK 4.1 test harness that:

- sets the exact graphics profile before WebKit initialization;
- opens a local test page (no network dependence);
- runs CSS transform/opacity animation;
- scrolls a long page;
- renders a 2D canvas and WebGL test separately if available;
- reports WebKit version and compositing mode via supported debug/log introspection;
- captures WebProcess/possible GPU process state;
- exercises resize and close/reopen;
- compares `accelerated`, `auto` and `software` profiles.

Use WebKit debug logging/version-appropriate diagnostics to confirm accelerated backing-store mode. Do not rely only on `window.WebGLRenderingContext` existing; WebGL is not equivalent to accelerated page compositing.

## 8.8 Full Home PWA host test

Run the actual `nuxel-pwa-host` build with the accelerated profile. Test:

- Home icons and grid;
- app drawer and transitions;
- browser page scroll/transform/animations;
- Notes editor and keyboard;
- Quick Settings and Settings;
- lockscreen/wake;
- app switching and return;
- page reload and WebProcess termination recovery.

A minimal harness pass is prerequisite, not final proof.

---

# 9. PHASE 5 — WEBKITGTK SUCCESS CRITERIA AND KNOWN FAILURE MODES

## 9.1 What counts as true WebKitGTK accelerated compositing

All of these must be established:

1. Actual `WebKitWebView` accelerated compositing is on.
2. `WEBKIT_DISABLE_COMPOSITING_MODE` is not forcing the non-accelerated path.
3. The WebKit rendering/Web process creates a working hardware EGL/GLES context through the intended kbase-compatible driver.
4. The reported renderer is Mali/G76 or the verified kbase driver, not `llvmpipe`, `softpipe`, SwiftShader, Cairo or another software renderer.
5. WebKit uses its accelerated DMA-BUF backing store or a separately documented and proven GPU-shared buffer path.
6. Phoc can import the buffers and composite them through its working GPU renderer.
7. The real content appears on the AMOLED with no black surfaces, flicker, stale frame or color corruption.
8. Scrolling, CSS transforms, opacity, canvas, resize, orientation and multitouch remain correct.
9. GPU activity changes during a controlled accelerated workload; CPU reduction/performance improvement is measured.
10. The same host can revert to software without reboot if GL fails.

## 9.2 Failure classes to identify

Do not lump every failure into “Mesa doesn't support it”. Classify:

- EGL loader picks wrong vendor driver;
- library ABI mismatch with `mali_kbase`;
- surfaceless-only EGL platform;
- missing `EGL_EXT_platform_wayland` / platform implementation;
- inability to create Wayland EGL window surface;
- no compatible buffer allocator/exporter;
- DMA-BUF format/modifier mismatch;
- importer can't import buffers into Phoc;
- fence/synchronization deadlock or unsupported fence model;
- WebKit build has acceleration disabled/not compiled;
- WebKit accelerated backing store selects DRM/GBM code path unavailable in the current stack;
- GTK UI process cannot import/render a buffer;
- sandbox prevents safe access to a required device/socket (fix narrow policy, never disable sandbox);
- incorrect process environment/library path;
- EGL thread/context ownership issue;
- compositor GL import issue;
- GPU context reset/fault or memory pressure;
- WebKit WebProcess crash/restart loop.

For each failure record exact log/error and first failing function/protocol boundary if traceable.

## 9.3 WebKit's software fallback must remain first-class

If the accelerated path is not stable:

- use the known-good software mode for that process;
- continue preserving accelerated Phoc;
- show WebKit as `SOFTWARE_FALLBACK` with reason and last failed probe;
- never use `/run/nuxel-gpu-fallback` to downgrade the entire display merely because WebKit EGL failed;
- do not continuously retry the failed EGL initialization on every page or create log storms;
- permit a manually triggered diagnostic attempt and an explicit canary profile.

---

# 10. PHASE 6 — NATIVE GTK APP ACCELERATION

## 10.1 Separate toolkit semantics

Nuxel currently has GTK3 WebKit host, GTK3 native apps and GTK4/libadwaita apps. Treat them individually:

- GTK3 uses its GDK rendering/GL facilities and Cairo fallback; `GSK_RENDERER` is not a GTK3 rendering selector.
- GTK4 uses GSK and may support Cairo or GL/NGL depending on exact compiled toolkit version/platform.
- WebKitGTK has its own accelerated compositing/backing-store logic.

## 10.2 Per-app renderer profile

The Bridge should decide graphics env from registry app type and tested capability:

- `webkitgtk-home`: use the tested WebKit profile;
- `gtk3-gl-verified`: use verified GTK3 GL profile;
- `gtk3-software`: use safe Cairo fallback;
- `gtk4-gl-verified`: use verified GSK GL/NGL profile;
- `gtk4-cairo`: use Cairo fallback;
- non-GUI/headless utilities: do not receive irrelevant graphics environment.

Do not set a universal `GSK_RENDERER=gl` or universal `LIBGL_ALWAYS_SOFTWARE=1` for all apps. Preserve user identity, D-Bus, Wayland socket, audio and sandbox constraints.

## 10.3 Tests

- GTK3 GLArea/texture test on Wayland;
- GTK4 GSK render test;
- GTK apps with and without GL profile;
- app startup when GPU driver unavailable;
- app-specific forced software fallback;
- no app hangs due to context initialization;
- no extra GPU context leak after app exit;
- existing Archive Manager, Settings, Files and all system-native apps still open and receive input.

---

# 11. PHASE 7 — OPTIMIZE `nuxel-wl-fb` FINAL CPU COPY/UPSCALE

## 11.1 Understand the active path

The current bridge captures a composited Wayland frame via `zwlr_screencopy_manager_v1`, receives SHM pixels and writes the result into `/dev/fb0`. On this Samsung command-mode DECON, a per-frame `FBIOPAN_DISPLAY` commit is required to latch the frame. The owner confirms `decon_pan_failed=0`; preserve the exact ioctl/ownership behavior.

In the supplied archive:

- image builder compiled `tools/s10plus/a34/nuxel-wl-fb.c`;
- `tools/s10plus/a67/nuxel-wl-fb.c` contained a newer optimized row-expansion implementation;
- the code contains an A67 fast path for exact integer 2× scaling (historically 720×1520 to 1440×3040), with one converted/expanded row reused for two destination rows;
- physical panel size is 1440×3040; virtual fb is 1440×6080 for two framebuffer pages;
- frame presentation uses `FBIOPAN_DISPLAY` every frame; removing this breaks panel update behavior.

Re-validate the live builder/source after PWNAGE-48000 and do not assume A34 or A67 is currently active.

## 11.2 Measure each stage

Instrument bounded, low-overhead timing counters for:

- screencopy request→buffer received;
- frame-ready callback;
- shared-memory map/ready wait;
- source-frame copy;
- colorspace/pixel-order conversion;
- horizontal/vertical upscale;
- fb mapped-memory write;
- `FBIOPAN_DISPLAY` commit;
- total capture→commit latency.

Collect p50/p95/p99, frames/sec, dropped frames, bytes copied, area damaged, CPU time per stage, bridge process CPU and temperature.

Do not log every frame synchronously to disk. Use in-memory histograms/periodic summary and a bounded diagnostic mode.

## 11.3 Optimize while preserving byte-accurate output

Candidate optimizations, only after measurement:

- reuse existing SHM/fb mappings and output row buffers;
- avoid repeated allocation/re-mmap when frame dimensions/format unchanged;
- use the proven two-times row expansion path if the actual captured dimensions confirm it;
- use ARMv8 NEON for color conversion/duplicated pixel writes only if it beats compiler-optimized code and preserves exact channel order;
- minimize full-screen repaint where damage can safely be applied;
- invalidate cached content on wake, output rotation, scale/format change, full damage or buffer reset;
- avoid redundant scale and color conversion;
- skip no required panel commits: preserve `FBIOPAN_DISPLAY` every needed frame on the measured command-mode panel;
- bound screencopy loop to actual target FPS and back off under unchanged/idle content only if panel behavior permits it;
- test double-buffering/page flips with existing virtual height and commit semantics;
- evaluate whether a GPU scaling or direct DMA-BUF route is actually supported before building it.

Do not:

- create a second `/dev/fb0` writer;
- bypass Wayland and blit from WebKit directly to the framebuffer;
- remove the pan ioctl because it appears expensive;
- assume damage rectangles can be committed independently without understanding screencopy/DECON constraints;
- introduce unsynchronized DMA-BUF or cache operations;
- alter pixel format/endian order without corner/color test patterns.

## 11.4 Acceptance

Bridge optimization must show repeatable reduction in CPU/frame time for matched workload, with `FRAMES_OK`, zero pan failures, no flicker/tearing, correct color, touch latency intact and no regressions after screen-off/wake. Report bridge CPU costs separately from WebKit's CPU/GPU costs.

---

# 12. PHASE 8 — GRAPHICS SETTINGS AND STATUS TELEMETRY

The prior PWNAGE-48000 mission called for a Graphics Settings page. Complete it rather than implementing a second status source.

## 12.1 Data architecture

Use the existing `nuxel-metricsd` socket service and the Bridge. The existing rootfs builder already compiles/installs `nuxel-metricsd` and socket activation. Extend current metrics output, tests and UI.

- Metrics daemon remains read-only and low privilege.
- Any privileged debugfs read must be narrowly exposed via a bounded helper/provider, not general arbitrary file reading.
- No PWA directly reads sysfs/debugfs.
- Use a single current capability/status provider and cache with timestamp/staleness.
- Distinguish unavailable from zero.
- Do not expose arbitrary GPU controls/frequency writes.

## 12.2 Separate status cards/rows

Show:

**GPU hardware and kernel**
- Mali-G76 MP12 detected;
- kernel driver name (`mali_kbase`), version/ABI if available;
- `/dev/mali0` access and context evidence;
- `/dev/udmabuf` and DMA-BUF status;
- `/dev/dri` availability separately, with “not expected for current vendor-kbase path” when absent.

**Compositor**
- Phoc backend/renderer (current real mode);
- GPU context/job evidence;
- compositor session health;
- last error.

**EGL / GLES**
- EGL library/vendor/version;
- GLES version;
- surfaceless probe result;
- Wayland EGL probe result;
- tested renderer string;
- supported extensions only when verified.

**WebKitGTK**
- WebKitGTK/WebKit2GTK version;
- GTK version of the active Home host;
- WebKit accelerated compositing preference;
- actual backing-store mode (DMA-BUF accelerated vs shared-memory software);
- WebProcess/GL init state;
- last failure/fallback reason.

**GTK apps**
- GTK3 GL test status;
- GTK4 GSK renderer/test status;
- per-app profile status where available.

**Display bridge**
- `nuxel-wl-fb` active;
- panel/virtual geometry;
- frame rate/time summary;
- frame receipt status;
- DECON pan success/failure counts;
- bridge copy/upscale CPU time.

**GPU telemetry**
- utilization only if real hardware busy/total counters exist and sampling semantics are documented;
- frequency only if read from actual clock interface;
- GPU memory only if attributable to Mali and not global shared RAM/dma-buf allocations double-counted;
- otherwise display `N/A` with reason.

## 12.3 Actions

- Run read-only diagnostic suite.
- Run bounded EGL Wayland probe.
- Run GTK3 GL probe.
- Run GTK4 GSK probe.
- Run WebKitGTK accelerated compositing canary.
- Switch WebKit profile to safe software fallback.
- Restore auto/last-known-good profile.

Only the appropriate administrator/owner authorization should enable system-wide graphics profile changes. Test actions must be bounded and must not alter kernel clocks, voltages, thermal settings or `/dev/fb0` ownership.

## 12.4 UI truthfulness

Use statuses such as:

`DETECTED`, `DEVICE_OPENED`, `KBASE_CONTEXT`, `GPU_JOB_VERIFIED`, `SURFACELESS_EGL`, `WAYLAND_EGL`, `DMABUF_EXPORT`, `PHOC_IMPORT`, `WEBKIT_ACCELERATED`, `GTK3_GL`, `GTK4_GSK`, `BRIDGE_FRAMES`, `SOFTWARE_FALLBACK`, `BLOCKED`, `UNKNOWN`, `STALE`.

Avoid one green “GPU acceleration: ON” if only Phoc is accelerated while WebKit uses software. The page should say, for example:

- Compositor: hardware accelerated (Mali kbase)
- WebKitGTK: software fallback (Wayland EGL/buffer-sharing unavailable)
- GTK3: GL unavailable
- GTK4: Cairo renderer
- Display bridge: CPU copy/upscale

That is a valuable and accurate status, not a failure to hide.

---

# 13. PHASE 9 — PERFORMANCE EXPERIMENT DESIGN

## 13.1 Workloads

Use deterministic workloads on the same phone and identical screen mode, thermal conditions, refresh cadence and power state:

1. Home idle, 60 seconds.
2. Home app drawer scroll, 30 seconds.
3. Home desktop scroll/drag, 30 seconds.
4. WebKit local synthetic benchmark page with CSS transforms, opacity, animated gradients, large image decode, long text scroll and canvas.
5. Real HTTPS long page (after network load completes) with scroll only; no network latency included in rendering score.
6. Browser tab switch and back/Home transitions.
7. Notes editor with keyboard open and cursor movement.
8. Quick Settings open/close and scroll.
9. Native GTK3 test app and GTK4 test app separately.
10. SnekByte or another known UI/game workload, if it remains stable.
11. Screen-off/idle workload to ensure GPU process does not spin.

## 13.2 Metrics

- input-to-first-response latency;
- frame-time p50/p95/p99;
- dropped frames and frame callback misses;
- WebKitWebProcess CPU/RSS;
- GTK host CPU/RSS;
- Phoc CPU/RSS and GPU activity;
- `nuxel-wl-fb` CPU/RSS and per-stage timing;
- GPU frequency/utilization if trustworthy;
- RAM/dma-buf allocation trends;
- temperature and throttling state;
- battery/power behavior where measurable;
- crash/restart count and log errors.

## 13.3 A/B profiles

Compare:

- known-good software WebKit profile;
- current canary/auto profile;
- proposed accelerated WebKit profile;
- each per-app GTK profile.

Use at least three runs after warm-up; capture median and p95 rather than a single best result. Avoid changing compositor, WebKit and bridge at once; isolate variables.

## 13.4 Performance claim standard

A WebKit acceleration claim requires both technical proof (actual backing-store mode + GPU context/job + buffer import) and measurable/visible benefit. A 3D canvas rendering on Mali does not prove normal HTML page compositing is accelerated. A GPU renderer string alone does not prove DMA-BUF presentation.

---

# 14. PHASE 10 — SAFE CANARY, FALLBACK AND ROLLBACK

## 14.1 Canary sequence

1. Build experimental libraries/apps in a separate directory/prefix.
2. Run unit and binary/ABI checks.
3. Run surfaceless EGL control probe.
4. Run Wayland EGL probe.
5. Run DMA-BUF export/import probe.
6. Run GTK3 test app.
7. Run GTK4 test app.
8. Run standalone WebKitGTK test.
9. Run actual Nuxel Home host canary with temporary profile.
10. Observe the actual screen and stability for at least 10 minutes.
11. Only then consider enabling it for all Home starts.

## 14.2 Fallback behavior

If WebKitGL initialization fails:

- revert only the WebKit process to software mode;
- keep Phoc's kbase renderer unchanged;
- do not create `/run/nuxel-gpu-fallback` unless the compositor's own documented fallback condition has been proven;
- do not force the whole Wayland session to Pixman;
- record a precise code/error/reason;
- suppress repetitive retry loops;
- allow manual retry from Graphics Settings.

If Phoc itself becomes unhealthy:

- use its existing explicit fallback/recovery path only;
- preserve `nuxel-wl-fb` ownership handoff;
- never let two writers overlap on DECON;
- restore the exact known-good kbase config after the test.

## 14.3 Atomic package/library management

- Never replace only `libEGL` while leaving incompatible vendor/mesa GLES/GLdispatch components.
- Record package ownership and `rpm -qf` equivalent for every library.
- Use an isolated prefix or a complete atomic package transaction.
- Preserve symlinks/SONAMEs and loader config.
- Confirm the active process loads the intended library via `/proc/<pid>/maps` (redact paths if sensitive) or loader diagnostics.
- Rollback package set/config together.
- Verify after service restart and after a full normal boot if needed; no boot flash required.

---

# 15. TEST MATRIX

## 15.1 Existing regression tests

Run all current project checks relevant to:

- PWA host build and AArch64 link;
- GTK/WebKit package verification;
- rootfs package and image verification;
- Phoc/service startup;
- framebuffer ownership/handoff;
- metrics JSON/schema and socket activation;
- Home/browser end-to-end;
- system monitor/Bridge wiring;
- thermal/power-safe idle behavior.

The archive contains previous GPU meter/shared-memory and WebKit repair prompts; use their tests/findings but do not assume tests already exist or pass in the current branch.

## 15.2 New required tests

- graphics profile JSON schema and invalid-mode rejection;
- per-process environment selection and fallback;
- no global `LIBGL_ALWAYS_SOFTWARE=1` accidentally passed to accelerated WebKit canary;
- no global `WEBKIT_DISABLE_COMPOSITING_MODE=1` in accelerated profile;
- WebKit software profile still launches on no-GL/unsupported devices;
- no `WEBKIT_FORCE_COMPOSITING_MODE=1` leaked into all apps;
- EGL surfaceless probe success baseline;
- EGL Wayland success/failure fixtures;
- exact EGL error reporting;
- DMA-BUF format/modifier and lifetime tests;
- GTK3 vs GTK4 renderer independence;
- WebKit backing-store mode reporting;
- PWA host WebProcess startup and renderer recovery;
- native app launch preserves D-Bus/Wayland/user/session behavior;
- metrics daemon bounded CPU/memory and correct null/N/A semantics;
- GPU utilization counter wrap/reset tests;
- GPU memory attribution/double-count prevention tests;
- fb bridge pixel-byte correctness for ARGB/XRGB and channel order;
- row expansion tests at 2× and generic scales;
- frame pacing and pan ioctl regression;
- no second framebuffer owner;
- fallback doesn't downgrade Phoc due solely to WebKit failure.

## 15.3 Live acceptance requirements

On physical phone:

- verify Phoc remains on Mali after all changes;
- verify Home PWA host accelerated compositing status;
- display the synthetic WebKit page and observe smooth transforms/scroll;
- navigate real web pages;
- test Notes and keyboard;
- test app transitions/lock/unlock/QS;
- run GTK3/GTK4 apps separately;
- capture logs and performance metrics;
- repeat after Home/host restart;
- idle for five minutes and check no runaway GPU/process activity;
- extended ten-minute stability run with no black surface/crash/thermal problems.

---

# 16. SECURITY, RELIABILITY AND PERFORMANCE GUARDRAILS

- Preserve WebKit web-process sandbox, seccomp and process isolation. Do not disable sandbox to grant `/dev/mali0` or `/dev/udmabuf` access; use a narrowly scoped, tested broker/device permission only if the design truly requires it.
- Preserve `nuxel-pwa-host` current app privileges/session model; do not run web content as root merely to open the GPU device.
- Never pass arbitrary EGL/GL environment keys from a PWA or app manifest.
- Restrict device file permissions to the exact required processes/groups.
- Do not expose kbase ioctls via Bridge.
- Do not permit a web page to trigger arbitrary GPU workloads or debugfs access.
- Do not put GPU driver logs with sensitive process data into public diagnostics.
- Keep GPU workload duration/memory bounded.
- Preserve thermal management and normal devfreq scaling; no max-clock pinning.
- Do not change CPU governor or voltage/power profile merely to show better FPS.
- Do not create a second `/dev/fb0` writer or bypass the existing panel owner.
- Do not change kernel config/driver/module/DTB/boot partition within this mission.
- Do not silently alter output resolution/scale to make benchmarks look faster; retain user experience and record geometry.
- Do not report utilization from frequency, context count or process fd count.
- Do not report dedicated VRAM from shared system RAM or count shared DMA-BUF pages twice.
- Do not claim all GTK applications accelerated because one probe works.

---

# 17. ROOTFS, PACKAGE AND RELEASE INTEGRATION

After a working accelerated path is proven:

- Add only required runtime package(s) and exact ARM64 libraries to `images/s10plus/packages-manifest.json` and `build-phone-rootfs-inside-fedora.sh`.
- Keep package source/license/provenance documented.
- Ensure the Home host is rebuilt with exact GTK3/WebKitGTK headers and runtime libraries matching the deployed stack.
- Install per-process graphics profile defaults and schema.
- Install probe binaries only if their security/size justify inclusion; otherwise keep them in a developer diagnostics package.
- Update `nuxel-metricsd` and UI assets via rootfs build and versioned cache changes.
- Add build-time checks that no experimental library silently replaces the software fallback or the working kbase driver.
- Verify clean ARM64 rootfs build, package manifest dependency graph and service units.
- Ensure rollback script remains packaged or recoverable through USB console.

---

# 18. EVIDENCE AND REQUIRED DELIVERABLES

Create/update:

1. `docs/beta-finalization/live/PWNAGE-50000-TODO.md` — task/source/test/evidence/status tracker.
2. `docs/beta-finalization/live/PWNAGE-50000-GRAPHICS-REPORT.md` — final architecture, decision, implementation and blocker report.
3. `docs/beta-finalization/live/GPU-WEBKIT-WSI-DECISION.md` — vendor vs Mesa vs udmabuf vs other WSI decision with technical evidence.
4. `docs/beta-finalization/live/evidence/pwnage-50000/` with:
   - `baseline/` live version, processes, fds, output/framebuffer geometry, library hashes;
   - `egl/` surfaceless and Wayland probe results;
   - `dmabuf/` formats, modifiers, exports/imports, synchronization and buffer screenshots;
   - `gtk3/` test logs and physical frame captures;
   - `gtk4/` test logs and physical frame captures;
   - `webkit/` accelerated/software profile logs, backing-store proof, screenshots and WebProcess/GPU process state;
   - `bridge/` per-stage latency histograms, copy bytes, pan counts and frame screenshots;
   - `benchmarks/` raw CSV and methodology;
   - `deployment/` binary/library hashes, service state, profile changes and rollback test.
5. A reproducible probe suite and tests.
6. Updated Graphics Settings UI and Bridge/metrics data model.
7. The per-process graphics profile policy and safe fallback implementation.
8. Optimized active `nuxel-wl-fb` source only if measured and required.
9. Rootfs integration and package/source provenance.
10. A final status table showing each feature separately: `SOURCE_VERIFIED`, `DEPLOYMENT_VERIFIED`, `KBASE_GPU_VERIFIED`, `WAYLAND_EGL_VERIFIED`, `DMABUF_VERIFIED`, `PHOC_IMPORT_VERIFIED`, `WEBKIT_ACCELERATED_VERIFIED`, `GTK3_GL_VERIFIED`, `GTK4_GSK_VERIFIED`, `BRIDGE_OPTIMIZED_VERIFIED`, `OWNER_VISIBLE`, `BLOCKED`, `NOT_TESTED`.

Include exact command and exit code for every automated check. Include raw logs or a compact excerpt plus a file pointer. Redact secrets and unnecessary user data.

---

# 19. EXECUTION SEQUENCE — DO NOT SKIP THE PROOF LADDER

1. Read the current PWNAGE-48000 report and all relevant evidence. Inspect Git history for `90ff0d6`, `9340301`, `01cd482`; determine what changed afterward.
2. Read-only re-verify live kbase compositor, Bridge frame status, fb0 state, panel geometry, libraries and process environment.
3. Create checkpoint/branch, preserve backups and test rollback via USB console.
4. Map full pipeline and establish software WebKit performance baseline.
5. Reproduce surfaceless Mesa EGL success and WebKit Wayland GL failure with exact logs.
6. Audit native Wayland EGL WSI and buffer sharing, compare vendor Mali userspace, Mesa kbase WSI and udmabuf pathways.
7. Write architecture decision report; choose one minimal, evidence-based candidate.
8. Build isolated ARM64 probes and run surfaceless → Wayland EGL → DMA-BUF → Phoc import → GTK3 → WebKit in order.
9. If probes pass, enable a canary WebKit process/profile only; keep Home software fallback available.
10. Run real Home/browser/Notes/touch/OSK/session tests on physical handset.
11. If the canary fails, capture exact first failing boundary, rollback and choose the next evidence-supported route. Do not repeat same failed config with different global env flags.
12. Implement per-process production profile and expose truthful status through existing metrics/Bridge/Graphics Settings.
13. Independently profile/optimize final bridge CPU copy/upscale if it still limits UI performance.
14. Integrate packages/config/service/UI into clean ARM64 rootfs builder.
15. Run full regression and ten-minute physical stability test.
16. Produce evidence, status matrix, deployment hashes and rollback procedure.

---

# 20. FINAL DEFINITION OF DONE

## Compositor/kbase baseline preserved

- [ ] `phoc` continues to use the Mali kbase path and shows its valid GPU context.
- [ ] No unintentional Pixman fallback or GPU fallback marker.
- [ ] `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web` remain active.
- [ ] Bridge `FRAMES_OK` remains healthy and `decon_pan_failed=0`.
- [ ] `/dev/fb0` remains restored and has exactly one writer.
- [ ] Panel and virtual framebuffer geometry remain correct.

## Application acceleration

- [ ] Surfaceless EGL baseline continues to pass.
- [ ] Actual Wayland EGL probe passes with correct vendor/renderer and visible swap buffers, or its missing WSI element is documented exactly.
- [ ] DMA-BUF or another real zero-/low-copy Wayland buffer-sharing route is proved and imported by Phoc.
- [ ] GTK3 test app creates and presents a hardware GL surface if the driver path supports it.
- [ ] GTK4 GSK renderer is tested separately and accurately reported.
- [ ] WebKitGTK accelerated compositing is active in the real Nuxel Home host, with accelerated backing-store/DMA-BUF proof, visible content and stable input/scroll/animation; or is honestly classified blocked by a proven missing component.
- [ ] No global software-forcing variable disables an accelerated process after success.
- [ ] No unstable force-GL variable is left globally enabled.
- [ ] Software fallback remains reliable and process-scoped.

## Bridge/performance

- [ ] Per-stage `nuxel-wl-fb` timing measured.
- [ ] Any optimization yields repeatable gains without image corruption, flicker or skipped DECON pan.
- [ ] CPU cost of WebKit and final display copy are reported separately.
- [ ] GPU metrics are based on genuine driver counters, otherwise N/A.

## Delivery/recovery

- [ ] Graphics Settings/metrics show compositor, EGL, GTK3, GTK4, WebKit, DMA-BUF, bridge and fallback separately.
- [ ] Current source/build/live binary hashes match.
- [ ] Clean ARM64 rootfs build contains the complete tested stack.
- [ ] Full physical stability test passes.
- [ ] Existing recovery backups untouched; new rollback tested.
- [ ] No kernel/boot/partition/firmware operation occurred without a separate approved mission.
- [ ] Final evidence and blocker report is complete.

**The task is not complete because Phoc opens `/dev/mali0`; that is the already-achieved PWNAGE-48000 milestone. PWNAGE-50000 is complete when the actual WebKitGTK page-compositing buffer path runs on Mali and is presented by the working Wayland compositor on the real AMOLED, with measurable improvement and a safe software fallback.**
