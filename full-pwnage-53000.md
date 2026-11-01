# FULL-PWNAGE-53000
# NUXEL — COMPLETE WEBKITGTK / GTK GPU ACCELERATION, PHOC LINUX-DMABUF CRASH REPAIR, EGL WAYLAND INTEGRATION AND FINAL DISPLAY-PRESENTATION OPTIMIZATION

## Exhaustive source-level engineering, isolated graphics-stack experiments, crash diagnosis, build integration, performance verification and safe S10+ deployment mission

**Mission ID:** PWNAGE-53000  
**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**GPU:** ARM Mali-G76 MP12  
**Kernel baseline:** Samsung vendor kernel with Mali `mali_kbase` driver  
**OS:** Nuxel, custom Fedora-based ARM64 Linux  
**Compositor:** Phoc / wlroots-based Wayland session  
**GPU device:** `/dev/mali0`  
**Memory/buffer facilities observed:** `/dev/udmabuf`, `anon_inode:dmabuf_udmabuf`  
**Display pipeline:** Wayland screencopy → `nuxel-wl-fb` → `/dev/fb0` → Samsung DECON → AMOLED  
**Known panel geometry:** 1440×3040 physical, virtual height 6080 (reconfirm live)  
**Mission type:** crash diagnosis, EGL/Wayland integration, DMA-BUF negotiation/import repair, WebKitGTK/GTK acceleration, staged enablement and performance optimization.

---

# 0. MISSION OBJECTIVE

The previous PWNAGE-48000 work brought up the Mali-G76 vendor kbase path and GPU-accelerated Phoc compositor. The phone boots with a working Wayland session and framebuffer presentation. Do not restart GPU bring-up from zero and do not discard that achievement.

The remaining problem is application graphics acceleration:

- GTK GL initialization fails.
- WebKitGTK accelerated compositing falls back to software.
- A previous Wayland-enabled Mesa experiment failed and was reverted.
- The current Mesa kbase path is surfaceless-only.
- Phoc crashes in the linux-dmabuf path when WebKit attempts accelerated buffers.
- The final screencopy → `/dev/fb0` upscale/copy remains CPU work.

The goal is to repair the exact broken hand-off and enable true hardware-accelerated GTK/WebKitGTK rendering on the physical Nuxel S10+.

The complete path is:

```text
WebKitGTK web process / GTK app
  → Mesa EGL / GLES / OpenGL on Mali-G76
  → GPU buffer allocation and export
  → DMA-BUF FD + format + modifier + planes + stride/offset
  → Wayland linux-dmabuf negotiation
  → Phoc/wlroots validation and import
  → GTK/GDK/WebKit UI-process buffer import and presentation
  → Nuxel screencopy and display bridge
  → /dev/fb0 / Samsung DECON
  → physical AMOLED
```

Every stage must be independently observable. A GPU context, `/dev/mali0`, EGL library on disk or GPU-enabled Phoc does not prove WebKitGTK application acceleration.

The mission succeeds only when WebKitGTK really renders through Mali, buffers are exchanged/imported safely, Phoc stays stable and the physical screen continues working.

---

# 1. KNOWN-GOOD BASELINE — PRESERVE IT

The owner supplied this latest verified state. Re-probe the live phone before edits and save the result as the baseline.

## 1.1 GPU/kernel state

- `phoc` holds three `/dev/mali0` descriptors.
- `phoc` holds one `/dev/udmabuf` descriptor.
- `phoc` holds an `anon_inode:dmabuf_udmabuf`.
- kbase debugfs lists a GPU context owned by `phoc`.
- Physical GPU is Mali-G76 MP12.
- Current kernel exposes no `/dev/dri`; this is expected for the current vendor kbase configuration.
- Active kernel GPU driver is Samsung/ARM vendor `mali_kbase`, not a conventional mainline DRM Panfrost kernel driver.

These facts are evidence of a live GPU-related compositor path, but a process opening a device is not proof that every draw call uses it. Verify actual renderer/context/job evidence.

## 1.2 Services and display

- `nuxel-wayland`: active.
- `nuxel-wl-fb`: active.
- `nuxel-web`: active.
- Bridge: `FRAMES_OK`.
- `decon_pan_failed=0`.
- `/run/nuxel-gpu-fallback`: absent.
- `/dev/fb0`: restored.
- Physical framebuffer: 1440×3040.
- Virtual framebuffer: 1440×6080.
- `nuxel-wl-fb` is the only `/dev/fb0` writer.

Reconfirm after every deployment. Keep the panel visible and the owner able to reach Home/Settings.

## 1.3 Remaining limits

- Phoc compositor path is GPU accelerated.
- GTK GL reports initialization failure.
- WebKitGTK accelerated compositing is not enabled/working.
- GTK/WebKit application UI renders via software fallback.
- Current Mesa kbase implementation is surfaceless-only.
- A Wayland-enabled Mesa build previously failed and was reverted.
- Phoc crashes in the linux-dmabuf path during WebKit accelerated-buffer attempts.
- Final screencopy → framebuffer upscale/copy remains CPU work.

## 1.4 Preserved backups/evidence

Do not delete or overwrite:

- `/var/backups/nuxel/kbase-gpu-*`
- `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland`
- `docs/beta-finalization/live/PWNAGE-48000-KBASE-GPU-REPORT.md`
- `docs/beta-finalization/live/evidence/pwnage-48000-kbase-gpu/`

Owner-reported commits:
- `90ff0d6 feat(pwnage-48000): S10+ kbase GPU acceleration`
- `9340301 docs(pwnage-48000): record post-reboot BOOT partition readback`
- `01cd482 docs(pwnage-48000): add post-reboot AMOLED frame capture`

Verify the current checkout contains these commits before relying on them. Preserve all pre-Wayland library backups.

---

# 2. TECHNICAL MODEL — FOUR DIFFERENT ACCELERATION QUESTIONS

## 2.1 GPU execution versus EGL window-system integration

The current kbase Mesa path can use Mali for surfaceless rendering. That does not automatically provide an EGL Wayland platform, a Wayland window surface or DMA-BUF export.

Determine the exact installed EGL support:

- `EGL_PLATFORM_SURFACELESS_MESA`;
- `EGL_PLATFORM_WAYLAND`;
- `EGL_EXT_platform_base`;
- `EGL_KHR_platform_wayland`;
- EGL device enumeration/query extensions if actually exposed;
- DMA-BUF import/export and modifier extensions if available;
- selected renderer/device and extension set.

Record `EGL_VENDOR`, `EGL_VERSION`, `EGL_EXTENSIONS`, renderer identity, chosen driver and context creation results. A Mesa library existing or `eglinfo` listing EGL does not prove Wayland WSI.

## 2.2 WebKitGTK accelerated backing store uses DMA-BUF

WebKitGTK documents separate GTK rendering modes:

- Non-accelerated: web process shares painted images through shared-memory buffers and the UI process maps/paints them.
- Accelerated: composited frames use DMA-BUF. The web process chooses a supported format/modifier and allocation device, creates buffers and passes buffer metadata to the UI process. The GTK UI process imports the buffer; depending on GTK/GDK version and backend this may use `GdkDmabufTextureBuilder` through EGL or Vulkan.

Potential independent failure points:

- no WebKit EGL Wayland platform;
- no suitable allocator/exporter for kbase;
- incorrect compositor format/modifier feedback;
- import unsupported by Phoc;
- GTK/GDK UI process cannot import texture;
- mismatched GPU/device selection;
- bad buffer metadata;
- missing fence or wrong implicit/explicit synchronization;
- FD ownership/lifetime bug;
- client failure misreported as Phoc crash.

Identify the exact stage. Never assume a working kbase context equals WebKit accelerated compositing.

## 2.3 linux-dmabuf is a protocol contract

`zwp_linux_dmabuf_v1` carries DMA-BUF FDs, DRM fourcc format, modifier, dimensions, planes, offsets and strides. Newer versions use feedback with format/modifier tables, target devices and ordered tranches. Actual protocol semantics depend on the bound version.

A compositor may advertise only formats/modifiers it can import and use. Validate every advertised combination. A non-empty common format list is not proof that every buffer import succeeds. Correct FD lifetime and synchronization are essential.

## 2.4 Phoc renderer and WebKit UI importer are separate

Phoc can render with kbase and still fail to import WebKit-produced buffers. WebKit web process can render on GPU while GTK UI process fails to import the DMA-BUF. Test exporter, compositor importer and GTK importer separately.

## 2.5 Final framebuffer presentation is another independent stage

Even after WebKit is accelerated, `nuxel-wl-fb` may still copy/scale the final Phoc screencopy using CPU. That is acceptable as an intermediate architecture, but it is not zero-copy output. Report GPU rendering, DMA-BUF import and CPU presentation separately.

---

# 3. FULL SOURCE AND ACTIVE-BUILD AUDIT

Before changing source, identify exact versions and build paths for:

```text
tools/s10plus/
images/s10plus/build-phone-rootfs-inside-fedora.sh
images/s10plus/packages-manifest.json
services/nuxel-session/
services/nuxel-bridge/
services/nuxel-metricsd/
services/nuxel-web/
pwa/nuxel-home/
pwa/nuxel-apps/
configs/nuxel/
Mesa build patches/specs/Meson options
Phoc/wlroots package source and build options
GTK3/GTK4/GDK Wayland packages
WebKitGTK/JavaScriptCore packages
EGL/GLES/GBM/libdrm/Wayland libraries
EGL vendor JSON and GL loader configuration
nuxel-wl-fb source and installed binary
```

Record actual package versions/NEVRAs, git commits, build flags, linked libraries, ELF architecture, installed paths and runtime loaded objects.

Do not patch a source directory that the active rootfs builder does not compile. Confirm the running executable and loaded libraries correspond to the intended artifacts.

## 3.1 Process map

Identify Phoc, wlroots, `nuxel-web`, WebKit UI process, WebKit web process(es), WebKit network process, GTK apps, `nuxel-wl-fb`, metrics daemon and GPU service. For each PID record actual executable, linked libraries, environment graphics profile, relevant device FDs and relevant kbase context. Avoid dumping sensitive process environment variables.

## 3.2 Source/build evidence

For every change record:
- source file and commit;
- build command/options;
- package name/version;
- installed path;
- runtime process/path;
- binary hash/build ID;
- systemd unit/wrapper that starts it.

If a custom Mesa or Phoc build is required, ensure rootfs packaging and reproducible build integration are updated. Do not test a developer-prefix library and then infer the system build uses it.

---

# 4. PHASE ZERO — BASELINE AND ROLLBACK

Create:

`docs/beta-finalization/live/evidence/pwnage-53000/baseline/`

Capture:
- kernel/config identity;
- Phoc/wlroots/Mesa/GTK/WebKit versions and build flags;
- active renderer and EGL device;
- EGL platform support;
- Wayland globals and linux-dmabuf version;
- current DMA-BUF feedback/formats/modifiers if available;
- current kbase context and device ownership;
- `/dev/udmabuf` and exporter evidence;
- `FRAMES_OK`, `decon_pan_failed`, `/dev/fb0` geometry and owner PID;
- fallback marker state;
- Home/Settings/WebKit performance and CPU baseline;
- current safe graphics profile and all environment overrides.

Make a new timestamped, hash-verified backup of all files that may be replaced:
- Mesa/EGL/GLES library set;
- Phoc/wlroots binaries and libraries if modified;
- GTK/GDK modules and settings;
- WebKitGTK/JavaScriptCore libraries and settings;
- EGL vendor JSON/loader config;
- systemd units/drop-ins and app launch wrappers;
- graphics profile/metrics settings;
- `nuxel-wl-fb` binary/config only if touched.

Do not overwrite preserved PWNAGE-48000 backups.

Build a known-good rollback path that can restore the previous software WebKit/GTK profile and the current working kbase Phoc profile without needing the accelerated display to work.

---

# 5. PHASE ONE — EXACT PHOC/DMA-BUF CRASH REPRODUCTION

## 5.1 Determine which process actually fails

Reproduce once under controlled conditions and correlate process PIDs/timestamps. Distinguish:

- Phoc process crash/abort;
- wlroots assertion;
- client protocol error/disconnect;
- WebKit UI process crash;
- WebKit web process crash;
- GTK/GDK import crash;
- Mesa driver failure;
- kbase kernel fault/reset;
- display bridge failure after compositor exit.

Capture coredump/backtrace, exit status, build ID, journal, kernel logs, Phoc/wlroots logs, GTK/GDK logs, Mesa loader logs, WebKit diagnostics and Wayland protocol trace. Do not call a client protocol disconnect a Phoc crash.

## 5.2 Minimal DMA-BUF client before WebKit

Build or use a small diagnostic Wayland client that:
1. connects to actual Nuxel Wayland socket;
2. enumerates globals and linux-dmabuf version;
3. retrieves format/modifier feedback;
4. allocates a small test buffer from a known allocator;
5. exports DMA-BUF FD(s);
6. submits exact metadata;
7. renders an asymmetric pattern with labelled corners;
8. verifies actual panel output;
9. waits for buffer release;
10. destroys resources and repeats.

Test one safe linear format first. Then test other formats/modifiers only after explicit proof. Add controlled negative tests for unsupported format/modifier and invalid metadata. The compositor must remain alive.

## 5.3 Scoped logging

Use diagnostics supported by exact installed versions:
- `WAYLAND_DEBUG=client` on the test process only;
- Phoc/wlroots debug categories for this build;
- `GDK_DEBUG=dmabuf` and `GDK_DEBUG=offload` only if supported by installed GTK;
- Mesa EGL/driver logging appropriate to actual build;
- WebKit logging categories available in installed release;
- kbase debugfs fault/counter data.

Disable verbose logs after reproduction. Do not log user browsing history, account tokens or personal page contents.

---

# 6. PHASE TWO — PROTOCOL/BUFFER CONTRACT REPAIR

## 6.1 Protocol version and feedback

Determine versions independently for outer Phoc, GTK/GDK client and any WebKit nested Wayland compositor. Inspect whether the bound protocol version uses legacy format events or newer feedback objects. Validate:

- default/surface feedback behavior;
- format table structure;
- ordered tranches and flags;
- target/main device identity;
- modifier encoding;
- supported formats;
- explicit versus implicit modifier behavior;
- client selection of a valid pair.

Do not send a mixture of deprecated and current semantics. Do not advertise unsupported formats to encourage clients to try them.

## 6.2 Actual device identity

There is no `/dev/dri` in the current kbase kernel. Do not fake one or symlink `/dev/mali0` to `/dev/dri/renderD*`.

Investigate the actual EGL device selection and WebKit's expected allocation-device reporting:
- EGL device enumeration/query extensions if exposed;
- kbase native allocator;
- DMA-BUF export capability;
- `udmabuf`;
- dma-heap availability;
- GBM only if genuinely supported;
- WebKit GTK port's DRM device selection behavior in installed source;
- whether a custom device/allocator hook is supported without lying about DRM.

The fact WebKit docs discuss a DRM device for allocation does not mean an arbitrary kbase node implements DRM render-node ABI. Prove the exact interface required by this build.

## 6.3 Format/plane metadata

For each format/modifier verify:
- DRM fourcc;
- modifier;
- width/height;
- plane count/order;
- FD validity and duplication;
- offset/stride and object bounds;
- alignment and allocation padding;
- alpha/premultiplication;
- y-invert;
- color interpretation;
- tiling/compression compatibility;
- producer/consumer device compatibility.

Do not advertise AFBC or tiled modifiers without actual allocation and importer proof. Start with a minimal linear format where possible; measure any bandwidth cost honestly.

## 6.4 Lifetime and synchronization

Verify:
- FD remains valid for buffer lifetime;
- buffer object holds necessary references;
- imported EGLImage/texture is destroyed in correct order;
- release event is respected before reuse;
- explicit/implicit fences work for actual kbase kernel;
- no wait blocks compositor main loop indefinitely;
- fence FDs close exactly once;
- client disconnect cleans resources;
- no use-after-free/double-close;
- no stale buffer reused by WebKit after process restart.

If implicit synchronization is used, prove it for kbase/udmabuf. If explicit sync is unavailable, do not invent it.

## 6.5 Failure handling

Validate untrusted metadata before allocation/import. Unsupported or runtime-failing imports must not crash Phoc. Use protocol-defined rejection/failure behavior appropriate to the protocol version. Preserve the prior valid surface until a replacement frame is safe. Avoid half-initialized resource objects and leaked references. Add rate-limited diagnostics.

---

# 7. PHASE THREE — MESA EGL WAYLAND / KBASE SUPPORT

## 7.1 Audit current Mesa

Record exact Mesa source, patches, Gallium driver, build options, LLVM version, kbase ABI implementation, EGL vendor/loader config, extensions and EGL platform support. Test surfaceless and Wayland separately.

A surfaceless EGL test can pass while Wayland WSI fails. Do not describe both as the same milestone.

## 7.2 Experimental kbase Panfrost project

Investigate `https://github.com/JimVulkan/mali-panfrost` as a candidate only. Its public README describes a Mesa-derived Panfrost port for Mali Bifrost on Arm kbase `/dev/mali0`, based on Mesa 26.3.0-devel, reporting tests on a Mali-G76 Galaxy S10e (Exynos 9820). It reports GL/ES rendering and Android gralloc presentation.

Before adoption:
- inspect current commit/tag and change history;
- inspect license and third-party notices;
- validate source provenance;
- inspect Android NDK/LLVM/build requirements;
- inspect use of Android gralloc and Android-specific libraries;
- determine whether native EGL Wayland platform and DMA-BUF export are implemented;
- validate compatibility with this exact kbase kernel ABI;
- build under a private prefix;
- run surfaceless GL test;
- run native Wayland EGL test;
- run DMA-BUF exporter/importer test with Phoc;
- ensure no system-wide replacement until all native Linux tests pass.

A project's Android gralloc success is not native Wayland support. Do not ship Android framework dependencies into Nuxel merely because the experiment works on Android.

## 7.3 Upstream Panfrost path

Official Mesa docs list Mali-G76 as Bifrost v7 hardware for Panfrost, but that does not make upstream DRM Panfrost userspace compatible with Samsung kbase.

If considering mainline Panfrost, verify the required kernel DRM driver and ABI, GEM buffer object handling, scheduling, fault handling, render node, DMA-BUF export and synchronization. Do not treat `CONFIG_DRM=y` as sufficient. Do not bind both kbase and Panfrost simultaneously to the same GPU. Do not unload kbase while it is the known-good live driver.

A kernel/DRM migration is a separate project and requires explicit owner approval and verified recovery. Prefer solving EGL WSI with the already-working kbase driver if feasible.

## 7.4 Minimal native Wayland EGL proof

Use actual Nuxel session user/environment:
- connect to active Wayland socket;
- create Wayland surface;
- create EGL display with Wayland platform;
- choose a compatible config;
- create EGL window surface/context;
- compile shader;
- render asymmetric test pattern;
- swap repeatedly;
- verify visible physical output;
- prove renderer string is Mali hardware;
- correlate with kbase GPU activity;
- observe Phoc DMA-BUF handling;
- cleanly destroy and check FDs/contexts.

Return precise failure stage. Do not hide failures behind fallback or silently use llvmpipe.

---

# 8. PHASE FOUR — GTK/GDK GL

Inventory GTK3 and GTK4 independently, plus GDK backend and graphics APIs used by each actual Nuxel app.

Inspect:
- `GDK_BACKEND`;
- `GDK_GL`;
- `EGL_PLATFORM`;
- `LIBGL_ALWAYS_SOFTWARE`;
- `MESA_LOADER_DRIVER_OVERRIDE`;
- EGL vendor and loader configuration;
- GL/GLES versions;
- GDK Wayland renderer selection;
- available DMA-BUF formats;
- `GdkDmabufTextureBuilder` availability;
- linked `libEGL`, `libGLES`, `libwayland-egl`, GTK and GDK modules.

Search systemd units, session environment, user environment, wrappers and PWA host launch code for global software forcing. Keep it for safe fallback; do not delete all software variables globally.

Build a small GTK diagnostic app with:
- GTK3 test where relevant;
- GTK4 test where relevant;
- `GtkGLArea` or equivalent;
- simple animated textured quad;
- GL/GLES renderer display;
- DMA-BUF texture import when supported;
- supported and unsupported format test;
- ability to force safe software mode.

Test GTK GL initialization, texture rendering, repaint, resize, repeated context creation and cleanup on the real Nuxel Wayland session. Do not infer all GTK widgets accelerate merely because one GLArea test works.

---

# 9. PHASE FIVE — WEBKITGTK ACCELERATED COMPOSITING

## 9.1 Inspect exact installed WebKitGTK implementation

Find exact WebKitGTK version and source/build options. Trace:
- accelerated compositing compile support;
- web-process renderer and EGL platform;
- nested Wayland compositor/connection if used;
- DMA-BUF allocation device;
- format/modifier selection;
- buffer export and message to UI process;
- GTK/GDK import method;
- fence FD handling;
- repaint scheduling;
- software fallback conditions.

Current WebKitGTK documentation says accelerated GTK frames use DMA-BUF, while non-accelerated frames use shared-memory images. Recent GTK/GDK may use `GdkDmabufTextureBuilder` via EGL or Vulkan, depending on version/backend. Verify actual installed source and API; do not assume modern upstream behavior applies unchanged to the packaged release.

## 9.2 Do not blindly toggle env vars

Audit existing WebKit settings/environment variables and confirm each is supported by this version. Do not copy undocumented switches from forums. Make graphics mode an explicit Nuxel launch profile and record it in diagnostics.

Do not enable accelerated mode by default until:
- web-process GPU rendering is proven;
- DMA-BUF export is proven;
- Phoc import is proven;
- GTK UI import is proven;
- frame presentation is proven;
- no crash/fault occurs in stress test.

## 9.3 Diagnostic WebKit test page

Create a local no-network test PWA:
- plain static background;
- large text/list and scroll;
- CSS transforms/opacity;
- composited layers;
- Canvas 2D;
- WebGL only if actual renderer supports it;
- large image texture;
- local video after core compositing works;
- repeated navigation;
- resize/rotation;
- hidden/visible state changes;
- long stress animation.

Collect:
- UI/web process PID and renderer;
- EGL vendor/version/extensions;
- GL renderer/version;
- compositing mode;
- DMA-BUF allocation/export/import state;
- format/modifier/plane metadata;
- fence and release behavior;
- fallback reason;
- CPU/memory/FD usage;
- frame time and dropped frames.

Test from a diagnostic page before Home, Notes or production PWAs.

## 9.4 Per-app graphics profiles

Implement truthful profiles:
- `software-safe`;
- `gpu-rendered-shm-presented`;
- `gpu-rendered-dmabuf-presented`;
- `fully-accelerated`.

Only use each label when proven. A GPU-rendered WebKit process that copies through SHM is not DMA-BUF-presentation acceleration. A DMABUF imported by Phoc but copied by `nuxel-wl-fb` is not zero-copy to the panel.

Roll out:
1. standalone EGL Wayland test;
2. GTK diagnostic app;
3. WebKit diagnostic host;
4. disposable test PWA;
5. Settings;
6. Home;
7. remaining WebKit/GTK apps.

Keep per-app fallback and quick restoration. Lock screen/Home/Settings must remain usable if accelerated mode is disabled.

---

# 10. PHASE SIX — UDMABUF AND ALLOCATION STRATEGY

The observed `/dev/udmabuf` and `anon_inode:dmabuf_udmabuf` prove an udmabuf path exists, not that it is the correct WebKit GPU allocator.

Inspect:
- kernel udmabuf implementation/config/version;
- memory pinning and alignment;
- linear layout/offset/stride;
- CPU cache coherency;
- DMA attachment/map behavior;
- whether kbase can import udmabuf for GPU jobs;
- whether kbase can export GPU-native allocations as DMA-BUF;
- whether Phoc can import those allocations;
- whether every frame incurs CPU copy;
- memory pressure and fragmentation.

A linear host-memory DMA-BUF is not automatically a GPU-native tiled/compressed buffer. Do not call it zero-copy because both processes pass the same FD. Test changing patterns and high-rate updates to reveal cache-coherency errors.

Use small linear buffers for protocol diagnostics first, then separately test native GPU buffer allocation/export. Do not force unsupported modifiers or assume allocator/importer compatibility.

---

# 11. PHASE SEVEN — PHOC/WLROOTS IMPORTER REPAIR

Inspect the exact Phoc/wlroots commit linked in the live binary. Patch that version, not a random newer checkout.

Trace:
- protocol bind;
- feedback/format advertisement;
- params validation;
- DMA-BUF FD import;
- EGLImage/texture creation;
- surface attachment;
- synchronization;
- buffer release;
- resource destruction;
- runtime failure handling.

Investigate possible defects:
- wrong format/modifier;
- modifier high/low swapped;
- plane count/order wrong;
- stride/offset/dimensions out of bounds;
- FD closed early/double closed;
- stale reference/use-after-free;
- unsupported modifier advertised;
- no fence/implicit sync mismatch;
- cross-device import mismatch;
- incomplete cleanup on client disconnect;
- client uses `create_immed` and server mishandles failure;
- feedback target device wrong;
- kbase driver fault misclassified as Phoc bug.

Do not assume these are present; prove the exact failure.

Defensive behavior:
- validate metadata;
- advertise only confirmed pairs;
- preserve current surface if replacement fails;
- do not crash on recoverable import errors;
- no use-after-free;
- bounded fence wait;
- one owner of each FD;
- complete cleanup on disconnect;
- rate-limited errors;
- safe fallback/retry path.

Add tests for every negative case, including unsupported formats/modifiers, malformed dimensions, stride/offset, missing/duplicate planes, invalid FDs, delayed fences, client disconnect, pending buffer destruction, repeated import cycles and stress animation.

---

# 12. PHASE EIGHT — NUXEL GRAPHICS STATUS AND SETTINGS

Extend the existing `nuxel-metricsd` and its current socket/provider. The active rootfs builder already installs this infrastructure; do not create a second metrics daemon.

Expose separate capabilities/status for:
- GPU identity and kernel driver;
- GPU execution/context/activity;
- EGL surfaceless;
- EGL Wayland;
- actual GL renderer;
- Phoc renderer;
- linux-dmabuf protocol/version;
- supported format/modifier feedback;
- Phoc DMA-BUF import;
- GTK GL;
- GTK/GDK DMA-BUF texture import;
- WebKit accelerated compositing;
- WebKit DMA-BUF export;
- WebKit UI-process DMA-BUF import;
- final screencopy;
- `nuxel-wl-fb` CPU copy/scale;
- DECON result;
- fallback marker/reason.

Each reading needs source, timestamp, error and status. Do not fabricate acceleration because a node exists or a process holds an FD.

Graphics Settings must have independent, bounded cards for:
1. GPU/kernel driver;
2. EGL/GL;
3. Phoc/compositor;
4. GTK;
5. WebKitGTK;
6. final display bridge.

Connector enumeration or another slow diagnostic must not block this panel. Use independent async Bridge requests, timeouts, request IDs and stale-response cancellation.

Provide safe actions:
- Refresh;
- run EGL test;
- run GTK diagnostic;
- run local WebKit test;
- collect diagnostics;
- restore safe profile.

Do not expose arbitrary shell execution to the UI. Use fixed Bridge operations.

---

# 13. PHASE NINE — OPTIMIZE THE FINAL CPU PRESENTATION PATH

After WebKit acceleration is confirmed, profile active `nuxel-wl-fb` source and binary:
- screencopy round-trip;
- frame allocation/reuse;
- damage region support;
- full-frame copy frequency;
- pixel conversion;
- upscale/scaling cost;
- memory bandwidth;
- stride/padding;
- DECON pan timing;
- frame pacing/dropped frames;
- `FRAMES_OK` and `decon_pan_failed`.

Potential safe optimizations:
- reusable aligned staging buffers;
- skip unnecessary pixel format conversion;
- partial damage updates only when the source damage contract is reliable;
- optimized row/copy/scaling implementation;
- NEON vectorization if measured and tested;
- avoid multiple intermediate copies;
- bounded frame queue/drop stale frames rather than accumulating latency;
- avoid blocking Wayland processing on framebuffer pan.

Do not assume `/dev/fb0` can consume a DMA-BUF directly. No DRM/KMS node currently exists. Do not invent hardware overlay or zero-copy scanout.

Measure p50/p95 frame time, `nuxel-wl-fb` CPU, Phoc CPU, WebKit UI/web CPU, Mali usage, memory/FD count, thermal behavior and battery impact before and after. Acceleration that raises CPU/battery without improving responsiveness must be reconsidered.

---

# 14. STABILITY AND ROLLOUT

Do not change every application at once. A test app passes before a production PWA is changed.

Immediate rollback triggers:
- Phoc crash/restart;
- blank/frozen/corrupt panel;
- DECON pan error;
- `FRAMES_OK` loss;
- unexpected framebuffer owner;
- kbase reset/fault;
- repeated Wayland protocol errors;
- WebKit/GDK import crash;
- uncontrolled CPU/GPU load or thermal condition;
- owner cannot reach lockscreen/Home/Settings.

Restore the safe graphics profile first; do not reboot as the default recovery action. Keep current kbase/Phoc/DECON path intact.

No kernel/bootloader/partition flashing in this task. If a kernel/driver ABI change is proven necessary, stop and propose a separate owner-approved TWRP mission with a verified boot image, partition map and rollback test.

---

# 15. AUTOMATED ACCEPTANCE MATRIX

## GPU/EGL
- kbase device healthy/access controlled;
- real GPU workload creates job activity;
- surfaceless EGL;
- native Wayland EGL platform;
- GL/GLES context and swap;
- renderer is Mali, not llvmpipe/softpipe;
- cleanup/context recreation;
- no FD/context leaks.

## DMA-BUF
- supported format/modifier enumeration;
- valid linear buffer;
- each advertised modifier;
- correct plane metadata;
- explicit/implicit sync;
- FD lifecycle;
- unsupported modifier safely rejected;
- invalid dimensions/stride/offset/planes safely rejected;
- failed runtime import no Phoc crash;
- client disconnect cleanup;
- repeated buffer stress.

## GTK
- GTK3/GTK4 where installed;
- Wayland backend;
- EGL/GL initialization;
- GLArea render;
- GDK DMA-BUF import if available;
- unsupported import fallback;
- window resize/repaint;
- repeated context creation;
- no crash/blank window.

## WebKit
- exact build supports accelerated compositing;
- web process uses Mali;
- accelerated backing store selected;
- DMA-BUF allocation/export;
- supported metadata;
- Phoc import;
- UI process/GDK import;
- fence signals;
- frame visible;
- scroll/transform/canvas/video tests;
- long-duration stability;
- fallback on failure.

## Display bridge
- `FRAMES_OK` stays true;
- `decon_pan_failed=0`;
- `/dev/fb0` geometry unchanged;
- one writer only;
- fallback marker accurately reflects state;
- physical AMOLED visible across profile change/rollback;
- CPU presentation cost measured.

---

# 16. DEPLOYMENT AND RECOVERY

- Build candidates in isolated prefixes.
- Verify architecture, ABI, dependencies and hashes.
- Stage replacements atomically.
- Keep the current known-good library set and backups.
- Restart only diagnostic/test processes initially.
- Test Phoc/wlroots patch in a separate/nested session if possible before applying to the live display session.
- Preserve Wi-Fi/SSH and serial console recovery.
- Confirm `FRAMES_OK`, `decon_pan_failed=0`, framebuffer owner and panel after every live deploy.
- Do not flash a kernel/boot image or write partitions.
- Do not remove software fallback.
- Do not delete old backups until a new known-good state has passed extended testing.

---

# 17. REQUIRED DELIVERABLES

Create:
- `docs/beta-finalization/live/PWNAGE-53000-TODO.md`;
- `docs/beta-finalization/live/evidence/pwnage-53000/baseline/`;
- `.../crash/`;
- `.../dmabuf/`;
- `.../egl/`;
- `.../gtk/`;
- `.../webkit/`;
- `.../performance/`;
- `.../deployment/`.

Deliver active source changes, rootfs/package integration, diagnostic applications, test runner, Phoc regression tests, per-app profiles, rollback script and a final report.

The report must state:
- exact crashing process and root cause;
- Phoc/wlroots/Mesa/GTK/WebKit versions;
- exact EGL platforms supported;
- renderer evidence;
- GTK GL result;
- WebKit compositing result;
- DMA-BUF export/import status;
- accepted formats/modifiers;
- synchronization method;
- CPU presentation work still remaining;
- before/after performance;
- deployment hashes;
- rollback test result;
- unresolved blockers with concrete evidence.

---

# 18. FINAL DEFINITION OF DONE

- [ ] EGL Wayland surface works in the real Nuxel session.
- [ ] EGL/GL renderer is Mali-G76 hardware, not software rasterizer.
- [ ] A controlled GPU workload is visible in kbase activity.
- [ ] GTK GL initializes and renders correctly.
- [ ] WebKitGTK accelerated compositing is actually active.
- [ ] WebKit allocates and exports valid DMA-BUF buffers.
- [ ] Phoc safely imports and samples supported buffers.
- [ ] GTK/GDK UI process imports and presents the buffers.
- [ ] linux-dmabuf crash root cause is fixed and regression-tested.
- [ ] Invalid/unsupported buffers fail safely without crashing Phoc.
- [ ] Home, Settings, lockscreen and apps retain a reliable software fallback.
- [ ] Existing kbase compositor and DECON/fbdev path remain healthy.
- [ ] `FRAMES_OK`, `decon_pan_failed=0`, framebuffer geometry and single-owner invariant remain intact.
- [ ] Performance improvement is measured; CPU copy stages are honestly documented.
- [ ] All changes are reproducible, packaged, deployed and reversible.

**PWNAGE-53000 is complete only when actual WebKitGTK and GTK applications use the Mali-G76 on the physical Nuxel phone, DMA-BUF exchange no longer crashes Phoc, the AMOLED display remains stable, and the previous known-good path can be restored.**
