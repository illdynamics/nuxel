# FULL-PWNAGE-60000 — Finish the S10+ Mali GPU pipeline, production acceleration, video decode, external display and casting readiness

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Mission ID:** PWNAGE-60000  
**Primary target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Mali-G76 MP12)  
**OS baseline:** Fedora 43 aarch64 Nuxel  
**Known live kernel baseline:** downstream Samsung/Exynos `4.14.253` (verify exact running build; do not assume the report's dirty build is still active)  
**Latest known graphics evidence:** `docs/beta-finalization/live/PWNAGE-53000-GRAPHICS-REPORT.md`, dated 2026-11-01  
**Mission type:** implementation, hardening, measured rollout and capability investigation — not a research-only report  

---

## 0. Mission order

Finish the remaining GPU acceleration work on the physical Galaxy S10+ and make the accelerated path the normal Nuxel desktop path **only after it passes the same on-device safety and regression gates as the known-good baseline**.

The GPU is partially working. Do not restart from zero, replace the graphics stack with a different stack, or treat this as a generic Panfrost enablement task. The latest evidence already proves that the Mali-G76 can execute GLES work through the vendor kbase driver and the Nuxel Mesa build. The unfinished work is now concentrated in:

1. production Home/Settings/WebKit profile selection — the known-good GPU-rendered profile is not yet the default;
2. a truthful and resilient GPU profile/telemetry contract;
3. WebKit's remaining shared-memory presentation path and the real kernel/DRM/GBM ABI boundary;
4. the CPU-based final framebuffer bridge and whether any safe hardware presentation path is available;
5. a separate, currently unproven hardware video decoder path using the Exynos MFC;
6. separately scoped USB-C DisplayPort Alt Mode / HDMI and wireless casting investigations.

These are **different subsystems**. Do not claim that GPU compositing automatically enables hardware video decode, HDMI output, Miracast, or 4K streaming. Prove each pipeline independently.

The required outcome is a working implementation with reproducible builds, measured before/after results, an honest capability matrix, tests, rollback, and a deployable image/runtime update. A polished report without code and tests is not mission completion.

## 1. Repository entry and source-of-truth rules

Start from the repository root. Before edits:

```sh
git status --short --branch
git rev-parse HEAD
git log -8 --oneline --decorate
find docs/beta-finalization/live -maxdepth 1 -type f -iname '*53000*' -o -iname '*54000*' | sort
sha256sum docs/beta-finalization/live/PWNAGE-53000-GRAPHICS-REPORT.md
```

Read these files before changing anything:

- `docs/beta-finalization/live/PWNAGE-53000-GRAPHICS-REPORT.md`
- `docs/beta-finalization/live/PWNAGE-53000-TODO.md`
- `configs/nuxel/graphics/graphics-profile.json`
- `tools/s10plus/a45/nuxel-graphics-profile`
- `tools/s10plus/a45/nuxel-session.sh`
- `tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh`
- `tools/s10plus/a67/build-mesa-kbase-wayland.sh`
- `tools/s10plus/a67/build-wlroots-kbase-linear.sh`
- `tools/s10plus/a67/mesa-kbase-wayland-wsi.patch`
- `tools/s10plus/a67/wlroots-kbase-linear-dmabuf.patch`
- `tools/s10plus/a67/nuxel-wl-fb.c`
- `tools/s10plus/a67/deploy-pwnage53000.sh`
- `tools/s10plus/a67/rollback-pwnage53000.sh`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `kernel/s10plus/configs/live-required.config`
- `tools/s10plus/a29/nuxel-gstreamer-guard.sh`
- `tools/s10plus/a33/nuxel-typec-diag.sh`
- `tools/s10plus/a33/nuxel-cast-diag.sh`
- `docs/A49/OWNER-TEST-EXTERNAL-DISPLAY.md`
- `docs/A49/OWNER-TEST-CAST.md`
- `tools/s10plus/a52/nuxel-v4l2-probe.py`

Search the repository for all consumers of the graphics profile, all WebKitGTK launchers, all session environment overrides, all GStreamer plugin guard installation points, and every reference to `/dev/fb0`, `/dev/mali0`, `/dev/dri`, `MESA_KBASE_NODE`, `NUXEL_KBASE_WSI`, `WEBKIT_FORCE_COMPOSITING_MODE`, `GSK_RENDERER`, and `LIBGL_ALWAYS_SOFTWARE`.

Do not trust generated build output or an old report over the current source. Do not trust source configuration over the actual running device. Record all three independently: source, image, live device.

## 2. Ground-truth baseline: what already works

The PWNAGE-53000 report documents the following physical-phone results. Re-run the critical checks to establish that the current checkout/image/device still matches this baseline.

| Layer | Known result | Required interpretation |
|---|---|---|
| Mali hardware | Mali-G76 MP12 in Exynos 9820 | Real GPU hardware exists; it is not an emulated renderer |
| Kernel GPU interface | ARM vendor kbase driver, `/dev/mali0` | This is not the mainline DRM Panfrost kernel driver |
| Mesa EGL/GLES | Nuxel Mesa kbase build, renderer `Mali-G76 MC12 (Panfrost)`, GLES 3.2 | GPU work has been submitted to kbase |
| Phoc/wlroots | Phoc renders through the Mali path | Compositor GPU rendering is working |
| EGL Wayland | Surface/context/swap/destroy passed | Actual Wayland window rendering has been tested |
| linux-dmabuf | Protocol v3, tested LINEAR formats | Tested linear DMA-BUF import works; not general tiled/compressed support |
| Phoc import validation | 20/20 valid linear buffers accepted; malformed client metadata isolated | Preserve validation and per-client failure containment |
| GTK3 GL | `GtkGLArea` passed on Mali | GTK3 can run GL work on the GPU |
| WebKitGTK | Accelerated compositing and kbase job submissions observed | WebKit can render through Mali, but presentation remains SHM-based |
| WebKit DMA-BUF transport | Blocked | WebKit does not yet export/present hardware DMA-BUF buffers through this ABI |
| Final panel output | CPU copy/scale through `nuxel-wl-fb` | Current display path still performs a CPU-side final presentation copy |
| Panel safety | `FRAMES_OK`, `decon_pan_failed=0`, one `/dev/fb0` writer | This is a hard invariant; never introduce a second owner |

### 2.1 Performance baseline already reported

The PWNAGE-53000 report measured active UI userspace CPU consumption, normalized to one CPU core:

| Process | llvmpipe baseline | Mali-enabled result |
|---|---:|---:|
| Phoc | 27.5% | 13.8–17.2% |
| `nuxel-wl-fb` | 10.6% | 6.4–8.9% |
| WebKitWebProcess | 6.5% | 3.1–4.7% |
| UI host | 2.4% | 2.1–2.9% |
| **Active UI total** | **47.0%** | **27.8–31.3%** |

That is approximately **33–41% lower active UI userspace CPU use** against the measured llvmpipe run. It is not a claim that all applications run 33–41% faster, that the full-device CPU load falls by that amount, or that battery life improved by that amount. Do not convert CPU utilization reductions into FPS, battery, or app-launch speed claims without separate measurements.

The report also measured framebuffer-bridge blit average around 45 ms before and 20–38 ms after the changes. The current bridge skips unchanged frames and uses a NEON row-expansion path. The active Home clock legitimately changes the display every second, so it creates more damage/capture work than a completely static page.

### 2.2 Current profile configuration has a production gap

The checked-in `configs/nuxel/graphics/graphics-profile.json` currently declares:

- `default_profile: software-safe`
- WebKitGTK profile: `software-safe`
- GTK3 profile: `software-safe`
- `gpu-rendered-shm-presented`: available and measured
- diagnostic app `pwnage53000-diagnostic`: explicitly assigned `gpu-rendered-shm-presented`
- `gpu-rendered-dmabuf-presented`: unavailable
- `fully-accelerated`: unavailable

`tools/s10plus/a45/nuxel-session.sh` asks `nuxel-graphics-profile env webkit` for the process environment. Therefore, passing the diagnostic app is not enough: the normal Home/Settings process can still be on the safe software profile.

**Primary deliverable:** after revalidation, make the measured `gpu-rendered-shm-presented` path the normal production WebKit/GTK3 profile, with automatic per-process fallback to `software-safe` if a startup or runtime validation fails. Do not advertise the blocked DMA-BUF or “fully accelerated” modes as available.

## 3. Non-negotiable safety boundaries

1. **No bootloader, recovery, modem, EFS, partition-table, PIT, radio, or firmware changes.** This mission does not authorize flashing any partition.
2. Do not run `fastboot flash`, `heimdall flash`, `dd` to a block device, `mkfs`, `sgdisk`, or equivalent destructive commands.
3. Do not flash a candidate kernel or DTB. Kernel experiments must remain in a separately built, reviewable artifact until the owner explicitly authorizes a recovery-backed hardware test.
4. Do not remove the working kbase driver, replace its ABI, or switch to mainline Panfrost as a shortcut.
5. Do not create a fake `/dev/dri/renderD*` node or symlink `/dev/mali0` to a DRM node. kbase does not implement the DRM render-node ioctl ABI.
6. Do not enable `CONFIG_DRM_EXYNOS=y` in the live kernel configuration as an experiment. The repo documents an ownership/name collision with the current Exynos DPU20 fbdev path and a panel-blanking failure in earlier tests. Investigate first, isolate candidate kernels, and do not flash.
7. Do not assume `CONFIG_DRM_VGEM=y` alone provides a real GBM allocator, a kbase-exportable buffer, or a scanout-capable buffer. VGEM is not a substitute for a real GPU/display integration.
8. Keep the **single `/dev/fb0` writer** invariant. `nuxel-wl-fb` is currently the sole final panel presenter. No experimental second process may open the framebuffer for writing.
9. Do not change panel rotation, touch orientation/calibration, the fixed-rotation mapping, the 2× NEON expansion semantics, or the display owner contract without a separate measured task and regression suite.
10. Keep the known-good `software-safe` fallback available. A bad GPU environment must never prevent Home or Settings from starting.
11. Do not remove or weaken `nuxel-gstreamer-guard.sh` before a separate, non-blocking MFC/V4L2 proof. The guard exists because vendor video-device `open()` has previously blocked in firmware requests and wedged GStreamer/WebKit processes in uninterruptible sleep.
12. Never call an untested V4L2/MFC device from the general plugin scanner, WebKit process, normal user session, or boot-critical service.
13. No permanent world-writable access to sensitive graphics/video device nodes. Audit wrapper permissions and use a dedicated group/udev policy with least privilege where possible.
14. Do not modify thermal throttling, safety limits, watchdogs, TrustZone, secure monitor threads, or kernel power management to make a benchmark look better.
15. No unverified claims. A feature is `PASS` only after the complete real pipeline has worked on the physical phone.

## 4. Mission workstream A — make the already-proven GPU profile production-default

### A1. Revalidate the baseline on the live S10+

Capture a fresh, timestamped baseline before edits:

```sh
date -Is
uname -a
cat /etc/os-release
cat /proc/cmdline
systemctl --failed --no-pager
pgrep -a -f 'phoc|nuxel-wl-fb|WebKit|nuxel-home|nuxel-session' || true
readlink -f /usr/lib64/libEGL_mesa.so.0
readlink -f /usr/lib64/dri/panfrost_dri.so
sha256sum /usr/lib64/libEGL_mesa.so.0.0.0 /usr/lib64/libgallium_dri.so /usr/lib64/libwlroots-0.19.so 2>/dev/null || true
ls -l /dev/mali0 /dev/udmabuf /dev/dri 2>&1 || true
```

Collect process-level evidence, not just `glxinfo` from an unrelated shell:

- phoc maps the intended `libEGL_mesa.so.0.0.0` and `libgallium_dri.so`;
- phoc opens `/dev/mali0` and submits kbase jobs;
- no llvmpipe worker pool exists in the live compositor;
- no Fedora transaction has reset the GLVND vendor library/symlinks;
- the expected Wayland socket and `nuxel-wl-fb` process are healthy;
- the panel is still being presented by one process only.

A renderer string from a different user, shell, or headless probe does not prove that Home uses the GPU.

### A2. Fix the production profile without making GPU startup brittle

Implement a clear profile contract in `graphics-profile.json` and `nuxel-graphics-profile`:

- `software-safe`: known-good, no GPU compositing requirement; always available.
- `gpu-rendered-shm-presented`: measured production candidate; Mali rendering, shared-memory presentation; may be selected as default once all A-workstream acceptance tests pass.
- `gpu-rendered-dmabuf-presented`: unavailable until real WebKit hardware-buffer transport is proven end-to-end.
- `fully-accelerated`: unavailable until the actual final output copy is removed or a truthful definition of “fully accelerated” is met. Do not leave the label available because EGL works.

Required behavior:

1. `nuxel-graphics-profile validate` validates schema, profile IDs, application overrides, fallback references, and incompatible combinations.
2. `nuxel-graphics-profile env webkit` emits only valid, shell-safe assignments. Avoid `eval` of unchecked config content; if the current interface requires shell output, constrain values to a strict allowlist and add tests for quote/newline/metacharacter injection.
3. Profile selection is per process. Do not set a global `LIBGL_ALWAYS_SOFTWARE=1` that leaks into all applications when only one app needs software fallback.
4. Startup checks are bounded and have timeouts. No process should wait indefinitely for EGL or a GPU device.
5. If EGL initialization or the required Wayland surface test fails, launch Home/Settings using `software-safe`, log one concise reason, and keep the desktop usable.
6. Do not run an expensive GPU probe on every app launch. Cache a validated result for the current boot/session, with invalidation on library/profile hash changes.
7. The diagnostic app remains available as an explicit troubleshooting mode, but normal user operation must not require launching it first.
8. Ensure lockscreen, Home, Settings, browser/PWA hosts and any embedded WebKit clients use the intended production profile. Preserve explicit software-only exceptions if evidence justifies them.
9. GTK3 GL should be enabled for the validated GPU-capable apps. GTK4 must remain `auto` until the existing GTK4/GSK probe passes on the live device; do not force a nonfunctional renderer.
10. Audit `nuxel-session.sh`: its current `GSK_RENDERER` default/fallback can force Cairo. Remove global forced Cairo only if GTK4 auto/GL tests pass, otherwise scope Cairo to the apps that need it. The desired state is `auto` with a verified fallback, not a cosmetic environment variable that creates a false GPU claim.

Add structured status fields that distinguish:

```json
{
  "profile_requested": "gpu-rendered-shm-presented",
  "profile_active": "gpu-rendered-shm-presented",
  "fallback_active": false,
  "compositor_gpu": true,
  "gtk3_gpu": true,
  "gtk4_gpu": "unverified-or-fallback",
  "webkit_gpu_rendering": true,
  "webkit_presentation_transport": "shm",
  "phoc_dmabuf_import": "linear-tested",
  "final_panel_presenter": "cpu-framebuffer-bridge",
  "zero_copy_scanout": false,
  "reason": null
}
```

This is an illustrative data contract, not a demand to hard-code sample values. Values must come from measured runtime evidence.

### A3. Release image integration must be fail-closed

The rootfs builder currently installs the GPU set from `release/s10plus/gpu` when files exist, otherwise it may fall back to software unless `NUXEL_REQUIRE_KBASE=1` is set. For release builds, require the exact GPU asset set and fail if a required artifact is absent or hash-mismatched.

Implement:

- a single canonical GPU manifest containing file path, exact SHA-256, source commit, build ID/version and target ABI;
- validation before and after installation;
- explicit GLVND vendor JSON installation and symlink checks;
- an image verifier that checks the EGL vendor JSON, EGL library, gallium driver, wlroots library, profile config and executable helper;
- a post-package-transaction check, because a DNF update previously reset the GLVND symlink;
- an image-level test that proves the generated image contains the accelerated default profile and the safe fallback.

No silent fallback in a release build. A developer build may opt into software fallback explicitly, but the final report must say that GPU acceleration was omitted.

### A4. Pin and reproduce the build chain

`build-mesa-kbase-wayland.sh` currently uses a moving upstream checkout (`git clone --depth 1` from `JimVulkan/mesa-unified-drivers`). Replace floating-source assumptions with a pinned commit and recorded patch stack. The report identifies Mesa `26.3.0-devel (git-a5010bb447)` as the tested baseline. Verify whether that abbreviated revision resolves unambiguously in the current upstream repository; record the full commit SHA and source tree identity.

For Mesa, wlroots, EGL vendor JSON, helper scripts and generated libraries:

- pin full commit IDs;
- record compiler/toolchain versions and configure options;
- apply patches with `git apply --check` and fail on fuzz/conflicts;
- build in a clean worktree;
- record library SONAME, ELF architecture, GLIBC symbol requirements and build IDs;
- compare artifact hashes to the known-good manifest where byte-identical reproducibility is expected;
- if the output legitimately differs, explain the compiler/source delta and rerun the complete live test matrix.

Never use `latest`, a branch name, or a shallow moving head as the only build identity.

## 5. Mission workstream B — finish DMA-BUF/WebKit transport honestly

### B1. Keep the proven linear-only DMA-BUF contract

The PWNAGE-53000 fix correctly restricts the wlroots DMA-BUF advertised table to formats the Nuxel kbase WSI allocator really produces: LINEAR RGB buffers. Preserve this.

The earlier client stall was caused by advertising tiled/compressed ARM modifiers the allocator did not actually create. A linear sealed-memfd + udmabuf allocation must never be labeled as ARM block-linear/split/sparse/AFBC. Do not add a modifier just because the renderer can sample it.

Required regression coverage:

- accepted LINEAR formats and correct fourcc/stride/offset/plane validation;
- invalid FDs, invalid plane count, invalid offset, short buffer, huge dimensions and unsupported modifiers;
- repeated import/release cycles, including at least 100 cycles in stress tests;
- client disconnect during pending buffer use;
- buffer release under compositor load;
- Phoc PID remains stable after malformed client input;
- no leaked fd, buffer, memfd, udmabuf allocation or unreleased wl_buffer after the test;
- no permanently blocked client on swap.

Keep linux-dmabuf v3 semantics accurate. The tested protocol does not negotiate explicit sync fences; do not invent fence FDs or claim explicit synchronization. Preserve the implicit-sync and `wl_buffer.release` lifetime contract unless the protocol version and both endpoints are deliberately upgraded and fully tested.

### B2. Understand the actual WebKitGTK 2.54.1 gate

The latest report explains why WebKit is still `gpu-rendered-shm-presented`:

- client EGL prerequisites are present;
- WebKit's Hardware buffer transport requires `USE(GBM)` and a non-null `drmMainDevice()` in the WebKit build/runtime path;
- the live phone has no `/dev/dri` node and no supported DRM render-device identity;
- GTK/WebKit GL rendering can submit kbase jobs, but the WebKit web process has no DMA-BUF/udmabuf output FDs in the tested trace;
- `CONFIG_DRM_VGEM` is unset, but turning it on alone is not proof of a usable kbase-backed GBM allocator.

Inspect the exact WebKitGTK 2.54.1 source and the downstream Fedora build flags, then produce a technical design with at least these options evaluated:

1. Can the WebKit UI process import a real DMA-BUF exported by the web process through an EGL image on this stack without `drmMainDevice()`?
2. Can the actual kbase allocation/exporter produce a DMA-BUF that WebKit's buffer transport can use, with correct modifiers, ownership and implicit/explicit synchronization?
3. Is a narrow WebKit patch with a real, validated kbase buffer transport possible without falsely emulating GBM/DRM APIs?
4. Is a compatible DRM/GBM device driver path realistically available for the Exynos 9820/S10+ downstream DPU20 + kbase combination, or is that an independent kernel/display project?
5. Would a candidate VGEM device help only with the identity check, and what is still missing for real allocation, import and scanout?

Do not remove the WebKit GBM/drmMainDevice gate and call the result Hardware mode unless a real allocatable/exportable DMA-BUF crosses the process boundary and the compositor safely imports it. Do not fabricate a DRM device node, stub DRM ioctls, fake an EGL device, or turn a shared-memory buffer into a DMA-BUF by renaming it.

### B3. Use a bounded, isolated experiment for WebKit DMA-BUF

If a genuine solution is plausible, create a separate feature branch/build flavor. Do not make production Home depend on this experimental path.

Acceptance for WebKit DMA-BUF requires all of the following on the physical phone:

- WebKit web process allocates or receives a genuine DMA-BUF from a documented allocator;
- process trace shows the actual FD and buffer lifecycle;
- buffer fourcc, dimensions, stride, offsets, modifier and planes are all correct;
- WebKit UI process and Phoc import the same real buffer without CPU-copy staging;
- explicit or implicit synchronization is supported end-to-end and documented;
- no buffer stalls, stale frames, flicker, leaks, process deadlocks or Phoc crashes after at least 100 repeated page/resize/swap cycles;
- recovery to SHM presentation works when allocation/import fails;
- the final panel still updates through the currently supported display path;
- measurable CPU and latency improvements exceed run-to-run noise.

If no safe implementation is available on the current kernel, stop and report the exact ABI blocker. Retain GPU-rendered SHM as the production profile. A truthful limitation is better than a fragile fake “zero-copy” feature.

## 6. Mission workstream C — optimize final panel presentation without breaking the phone

### C1. Establish current output ownership and geometry from the live kernel

The PWNAGE-53000 report identifies `nuxel-wl-fb` as the sole `/dev/fb0` owner. Its measured pipeline is:

```text
Phoc screencopy
  -> CPU damage/memcmp
  -> NEON 2x row expansion
  -> /dev/fb0 mmap
  -> FBIOPAN_DISPLAY
  -> Exynos DECON/DPU20 panel output
```

The report records a framebuffer virtual geometry of 1440×6080 while the physical S10+ panel is 1440×3040. Do not confuse `yres_virtual`/buffer allocation geometry with the physical active panel mode or logical compositor dimensions. Query the device instead of assuming:

```sh
cat /sys/class/graphics/fb0/virtual_size 2>/dev/null || true
cat /sys/class/graphics/fb0/modes 2>/dev/null || true
cat /sys/class/graphics/fb0/name 2>/dev/null || true
fbset -i 2>/dev/null || true
cat /sys/class/graphics/fb0/bits_per_pixel 2>/dev/null || true
```

Also capture `FBIOGET_VSCREENINFO`, `FBIOGET_FSCREENINFO`, stride, offsets, pixel format, active var/fix structs, panel mode and any vendor DECON state. Identify who opens `/dev/fb0` read/write and prove there is exactly one writer.

### C2. Improve the existing bridge before attempting a new kernel display architecture

Audit `tools/s10plus/a67/nuxel-wl-fb.c` and optimize only where measurements justify it:

- damage-region coalescing and correct partial rectangle tracking;
- row-wise compare to avoid scanning unchanged bytes twice;
- SIMD/NEON conversion with alignment-safe tails;
- reduce unnecessary full-frame memory reads/writes;
- reuse persistent buffers rather than allocate per frame;
- keep source/destination cache behavior correct;
- pace captures against actual panel refresh and compositor damage;
- avoid forcing 24/30/60 fps when no pixels changed;
- instrument capture, compare, convert, copy and pan as separate phases;
- bound CPU usage on static screens;
- keep the UI clock and animations correct without overcapturing.

Do not blindly optimize by skipping regions without validating that damage coordinates survive transform, rotation and scale. A missed dirty rectangle is a visible stale pixel bug.

### C3. Investigate real zero-copy scanout only as a separate, gated design

The current kernel configuration includes `CONFIG_DRM=y`, `CONFIG_DMA_SHARED_BUFFER=y`, `CONFIG_UDMABUF=y`, Mali kbase and `CONFIG_EXYNOS_DPU20=y`, but `CONFIG_DRM_EXYNOS=n` and `CONFIG_DRM_VGEM=n`. The current working display path is fbdev/DECON, not a known DRM/KMS output stack.

Research and document:

- the exact DPU20/DECON driver and panel connector implementation in the current downstream kernel;
- whether it exposes any documented dma-buf import or framebuffer pan API;
- whether its scanout engine can import a kbase-exported buffer with the actual modifier/format/stride it produces;
- whether a DRM bridge/connector driver can be integrated without taking ownership away from the working fbdev path;
- whether kbase has a compatible buffer export path and cache/sync contract;
- whether the panel pipeline needs a DRM/KMS atomic modeset device or an in-kernel vendor ABI;
- precise conflict points with the existing DPU20 fbdev driver.

Do not assume that an available DMA-BUF import in Phoc means the panel can scan out that buffer. Those are different edges in the pipeline.

A DRM/KMS candidate must be built in isolation, with static analysis and kernel unit/config checks before any owner-supervised hardware test. The active `/dev/fb0` route must remain intact until the new driver has proved panel initialization, hot reboot, rotation, suspend/resume as supported, touch mapping, hotplug (if applicable), and reliable recovery.

Until a real hardware scanout path is used and CPU copy/scale is absent from the measured frame path, status must say `zero_copy_scanout=false`.

## 7. Mission workstream D — make GPU status and diagnostics trustworthy

Add a single inspectable status command and API integration. It must report separate layers, not a single green “GPU: on” lamp.

Suggested sections:

1. Kernel GPU driver: kbase presence, device node, permissions, loaded driver/version.
2. EGL/GLES: vendor library path/hash, active renderer, GLES version, initialization result.
3. Phoc: loaded renderer libraries, kbase FDs, llvmpipe presence, recent job submissions where observable.
4. GTK3: GtkGLArea result and renderer.
5. GTK4/GSK: requested renderer, actual renderer and fallback reason.
6. WebKit: accelerated compositing requested/active, actual renderer, process library mappings, job submissions, profile name.
7. WebKit transport: SHM, true DMA-BUF, failed attempt and reason.
8. linux-dmabuf: protocol version and supported LINEAR formats; clearly mark importer test vs exporter support.
9. Final output: `nuxel-wl-fb` status, one writer, capture/compare/copy/pan timings, skipped frames, panel geometry.
10. Video: MFC driver/firmware readiness independently of the GPU status.
11. External display: Type-C/DP Alt Mode / DRM connector detection independently.
12. Casting: Wi-Fi P2P, capture and encoder candidates independently.

Use evidence such as open FDs, process mappings, EGL renderer strings, KBASE job-submit counters, and known kernel driver state. GPU sysfs frequency/utilization attributes can be missing or unreliable on this vendor kbase stack. A `0` or unavailable value is not proof that the GPU is idle. Do not invent a utilization metric. If the driver does not expose utilization, say `not exposed` and use a transparent proxy such as kbase job submissions with caveats.

The bridge and graphics status must not claim `fully accelerated` when the final output still performs CPU damage/copy/scale/pan.

Add JSON output for automation and human-readable output for Settings/diagnostics. The API must never block the UI thread while reading sysfs, probing devices or running a benchmark.

## 8. Mission workstream E — hardware video decode is a separate subsystem

### E1. Hardware capability vs Nuxel driver capability

Samsung's Exynos 9820 silicon specification lists an MFC capable of 8K 30 fps and 4K UHD 150 fps encode/decode, including HEVC/H.265, H.264 and VP9, with 10-bit video support. These are silicon/media-engine specifications, **not proof that the current Nuxel kernel exposes a usable Linux decoder path**.

The current Nuxel tree explicitly carries `tools/s10plus/a29/nuxel-gstreamer-guard.sh`. Its comment records that opening the vendor MFC `/dev/video*` nodes has blocked in `request_firmware()`/`mfc_open`, wedging plugin scanning or WebKit media processes in D state. The guard disables V4L2, V4L2 codec, KMS and OpenGL GStreamer plugins to keep the desktop from probing those devices. Do not remove this guard simply to make `gst-inspect` list a decoder.

### E2. Identify the exact S10+ MFC hardware/firmware ABI

Before changing kernel or userspace:

- locate the exact MFC driver source in the currently used Samsung/Exynos 9820 kernel tree;
- identify SoC revision, MFC IP version, firmware filename, firmware format and loading path;
- inspect matching device-tree nodes, clocks, regulators, IOMMU, power domains, reserved memory, interrupts and interconnects;
- compare the driver with the S10+ stock kernel's actual vendor implementation and known matching versions;
- identify whether this is the older s5p-mfc ABI or a later Exynos MFC generation; do not apply a driver for a different MFC generation;
- verify where firmware is expected to live and its licensing/redistribution constraints;
- document every kernel/user ABI difference from modern upstream V4L2 stateless/codec interfaces.

Do not blindly cherry-pick an unrelated upstream Exynos MFC series or assume a driver aimed at a later MFC IP generation supports the S10+ hardware. A kernel series targeting newer Exynos MFC firmware/command interfaces is not automatically compatible with the 9820.

### E3. Device-open safety gate

Do not execute `open()` on a suspect MFC node from the main session. Build a dedicated probe that can be supervised and terminated, and only use it once kernel/firmware behavior is understood.

Required gate before general userspace probing:

1. Driver's `open()` path is audited and cannot wait indefinitely on missing firmware or uninitialized hardware.
2. Firmware is present and a missing/invalid firmware error returns promptly.
3. Device nodes are permission-restricted and not probed by general GStreamer/WebKit scanners.
4. A child test process can be timed out and killed without wedging critical UI services; a timeout alone does not free a task stuck in uninterruptible D state, so prove the kernel path itself does not hang.
5. Repeated open/close works at least 100 times, including clean failure paths.

### E4. Decoder pipeline proof

Once the kernel path is safe, implement or enable the correct GStreamer V4L2 M2M decoder. Test a staged matrix:

| Stage | Test |
|---|---|
| A | H.264 720p30, short local file |
| B | H.264 1080p30 |
| C | HEVC Main 1080p30 |
| D | VP9 1080p30, if the exposed decoder supports it |
| E | 4K UHD 30 fps H.264/HEVC/VP9 as advertised by actual decoder caps |
| F | 4K60 only if actual V4L2 caps and thermal tests support it |
| G | 10-bit/HDR only if decoder output format, EGL/display and panel/TV path all support it |

Do not use marketing specs as the test matrix's pass criteria. Derive supported formats, profiles, levels, bit depth, output formats and resolution limits from the actual MFC driver and decoder caps.

For each test record:

- decoder element and device used;
- negotiated input/output caps;
- proof of hardware decode (driver logs, device activity, perf counters or other reliable evidence);
- whether buffers are exported as DMA-BUF or copied into system memory;
- CPU use per process and total normalized CPU use;
- dropped frames, decode latency, A/V sync and playback smoothness;
- memory bandwidth/allocations where observable;
- SoC thermal state and throttling over a 20–30 minute run;
- battery current/energy only if actual measurement hardware or a trustworthy supported sensor exists.

Compare hardware decode with software decode on the same file under matched conditions. A smooth 4K video on the display does not prove hardware decode if software decode was actually used.

### E5. Desktop integration and safe fallbacks

Only after the tests pass:

- restore only the V4L2 plugin(s) that were specifically disabled for the MFC path;
- keep generic scanner probing controlled and bounded;
- do not re-enable KMS plugin merely because V4L2 decode works;
- configure VLC, GStreamer and browser playback to select hardware decode only when supported;
- fall back to software decode for unsupported codecs/resolutions;
- make the app expose an honest “Hardware decoding” diagnostic state;
- test that invalid streams, unsupported formats, seek, pause/resume and device disconnect do not wedge the phone.

If no safe matching driver exists in the current 4.14 kernel, deliver a separate driver-port feasibility report and keep the guard active. A safe `NOT YET AVAILABLE` state is preferable to bricking the desktop media path.

## 9. Mission workstream F — USB-C to HDMI / external monitor feasibility

The S10+ hardware is documented by Samsung as supporting a wired HDMI/DeX connection using a DeX cable or compatible USB-C-to-HDMI adapter. Nuxel Linux does not inherit Samsung Android's DeX software or driver stack. The repo's current external-display task is marked `NEEDS_OWNER_TEST`, and its correct first step is a read-only capability probe.

### F1. First phase: diagnostics only

Run and capture:

```sh
nuxel-typec-diag.sh status --json
```

Inspect the exact Type-C controller, DP Alt Mode state, mux/PHY, USB-C orientation, regulators, connector/EDID interfaces, DRM devices, device-tree properties and relevant kernel modules. Record whether the phone exposes the generic `/sys/class/typec` interfaces or vendor-specific equivalents. Missing generic sysfs alone does not prove the hardware cannot do DP Alt Mode.

Distinguish:

- USB-C DisplayPort Alt Mode + passive HDMI adapter;
- active USB-C-to-HDMI conversion;
- DisplayLink USB graphics (a completely different driver/protocol path).

Do not claim those are interchangeable.

### F2. Hardware owner test is explicitly gated

The S10+ has one USB-C port. Before connecting an adapter, retain an alternate Wi-Fi SSH path or a powered recovery-capable USB hub. Collect logs before plugging in and keep the test owner-supervised. Do not change mux/PMIC/PHY settings experimentally. Do not touch the live USB console's only recovery path.

Acceptance stages:

1. Exact adapter chipset and power behavior are recorded.
2. DP Alt Mode negotiation is positively observed, or a precise blocker is documented.
3. A real DRM connector and EDID/modes are discovered (or a driver gap is established).
4. Real Nuxel pixels appear on the external monitor.
5. Hotplug/disconnect/reconnect works without panel blanking, UI crash or SSH loss.
6. Internal panel, rotation, touch and audio remain functional.

### F3. Implementation target order

- first target: 1920×1080 at 60 Hz;
- then: 2560×1440 if EDID, link bandwidth, controller and compositor prove it;
- 4K output is **not a commitment**. Only claim a mode if the actual DP PHY/link training, controller, bridge/adapter, kernel driver and monitor all negotiate and sustain it.

External display is an independent DRM connector/compositor/output task, not an effect of enabling GLES. Do not try to solve it by increasing the internal phone framebuffer resolution.

## 10. Mission workstream G — wireless casting

The S10 series supports Wireless DeX/Miracast under Samsung's stock software, but that is not a working Miracast implementation in Nuxel. The Nuxel repository currently has a read-only `nuxel-cast-diag.sh` and owner-test document. The diagnostics can identify candidates; they do not prove a screen is being cast.

### G1. Two explicitly separate products

**Path A: Miracast / Wi-Fi Display**

Prove each stage:

1. Wi-Fi chipset/driver exposes P2P capability;
2. NetworkManager/wpa_supplicant can create and manage a P2P group;
3. receiver discovery and P2P association work;
4. RTSP session setup succeeds;
5. real Phoc capture/portal source is available;
6. H.264 hardware or software encoder accepts the real frame stream;
7. RTP packetization/timing reaches a real receiver;
8. receiver shows current, moving Nuxel pixels with stable frame pacing;
9. audio, if added, is separately negotiated and synchronized.

**Path B: authenticated LAN screen sharing / WebRTC**

This is not Miracast. Label it “Share screen” or “LAN screen share”, never as Chromecast/Miracast discovery. Require explicit user start, single-use pairing code/token, authenticated session, scoped network access, visible stop control, no unauthenticated LAN endpoint, no automatic background broadcast, and pause/redaction on lockscreen or privacy-sensitive state.

### G2. First useful casting milestone

Target 720p30 first, then 1080p30 if the encoder and Wi-Fi path sustain it. Keep resolution/frame rate adaptive to real measured throughput and thermal behavior. 4K wireless casting is a later optional milestone; do not promise it based on the MFC silicon spec alone.

### G3. Privacy and performance

- No screen capture while casting is off.
- No capture of lockscreen, password dialogs, privacy settings or protected content.
- Require user-visible active-cast indicator and immediate stop.
- Disconnect cleanly when Wi-Fi changes, screen locks or the session is revoked.
- Prove no persistent CPU/GPU/network drain after stop.
- Include test coverage for authentication, token replay, LAN isolation, session expiry, lockscreen redaction and disconnect/reconnect.

## 11. Measurement contract — matched, reproducible, multi-layer

Use the same image, same boot state, same brightness, same Wi-Fi state, same open applications, same clock/animation state where possible, same thermal starting window, and same benchmark duration for A/B runs.

### 11.1 Benchmark cases

Run at least three repeated 60-second runs for each supported profile:

1. `software-safe` baseline;
2. `gpu-rendered-shm-presented` production candidate;
3. experimental WebKit DMA-BUF profile only if safely implemented;
4. idle static Home;
5. Home with one-second clock changes;
6. scroll-heavy Settings and browser page;
7. window/app switching and transitions;
8. video playback separately (software vs hardware decoder); do not mix into compositor-only numbers.

### 11.2 Record for each run

- exact profile requested and actually active;
- kernel/image/build IDs and binary hashes;
- process CPU per PID and normalized total;
- phoc CPU and kbase job submission evidence;
- WebKit process CPU and renderer/transport evidence;
- `nuxel-wl-fb` CPU and separate capture/compare/convert/copy/pan timing;
- achieved frame rate, frame-time p50/p95/p99, dropped/stale frames;
- number of frames captured, frames presented and skipped unchanged frames;
- context switches and memory/RSS where available;
- thermal readings and reported throttling;
- errors, stalls, display corruption, process restarts and fallback events;
- battery current/energy only if a validated measurement exists.

Preserve raw logs/CSV under a unique `evidence/pwnage-60000/` run folder, with a README documenting collection commands and environment.

### 11.3 What qualifies as a win

The GPU production profile should:

- remain stable across at least 3 repeated runs and one cold boot;
- show no renderer fallback to llvmpipe during normal Home/Settings use;
- lower active UI CPU usage by a statistically credible amount versus the matched software-safe baseline, or materially improve p95 frame timing without higher CPU cost;
- have no new visual artifacts, touch lag, stuck frames, memory leak or crash;
- keep CPU usage bounded on static Home;
- have no more than 5% regression in any critical UI responsiveness metric unless a clearly justified quality trade-off is approved;
- always recover to software-safe after a deliberate GPU startup failure.

Do not claim FPS improvement unless FPS/frame-time data is collected. Do not claim battery savings unless battery energy/current data is trustworthy and repeated. Report medians and spread rather than choosing the best single run.

## 12. Tests and automation

Create or update tests in the existing test structure. Include at least:

### Config/profile tests

- valid schema accepted;
- unknown profile rejected;
- invalid app override rejected;
- missing fallback rejected;
- malformed JSON and malicious shell strings rejected;
- default profile points to measured GPU-SHM only after validation gate;
- software-safe remains available;
- unavailable modes stay unavailable;
- per-app environment never leaks to sibling processes.

### GPU diagnostic tests

- missing `/dev/mali0`;
- incorrect EGL vendor symlink;
- stock Mesa selected accidentally;
- llvmpipe detected;
- kbase opens denied;
- EGL init timeout/failure;
- valid GPU startup;
- runtime GPU process failure;
- fallback reason and status correctly reported.

### DMA-BUF tests

- LINEAR allowlist only;
- bad FDs and geometry;
- unsupported modifier rejection;
- release and disconnect behavior;
- repeated buffer cycles and resource leak checks;
- Phoc survives malformed client input.

### Bridge tests

- dirty rectangle correctness;
- rotations/transforms;
- stride/alignment/tail handling;
- unchanged frame skip;
- full damage fallback;
- pan failure recovery;
- one writer invariant;
- no stale regions after resize/rotation.

### Video tests

- keep guard installed by default;
- do not probe the MFC in ordinary unit CI;
- use mocked/fixture device discovery for tests;
- isolate real hardware probes behind explicit flags;
- verify scanner does not touch disabled nodes.

### Type-C/casting tests

- diagnostics stay read-only;
- missing sysfs is reported as unknown rather than unsupported;
- no mux/PMIC writes;
- cast remains unavailable until capture/transport/encoder/receiver proof exists;
- auth and privacy controls covered.

Run the complete targeted suite, existing related regression suites and project golden/smoke gates. Record exact commands and results. Do not modify fixtures just to make the tests green.

## 13. Deployment and rollback

Use the existing PWNAGE-53000 deployment/rollback scripts as structural references, but audit them before reuse. The new deployment must be atomic and reversible.

Before any live change:

1. confirm Wi-Fi SSH works and an alternate recovery path is available;
2. record live Git/image/kernel identity and current display health;
3. back up every replaced file with permissions, owner/group and SHA-256;
4. create a deployment manifest listing old/new hash, target path and rollback action;
5. stage files to a temporary location and validate all hashes/ELF dependencies first;
6. install atomically with same-filesystem rename where possible;
7. restart only the minimum required user-space service(s);
8. do not restart/replace the framebuffer owner or compositor in a way that risks permanent panel loss unless a timed recovery mechanism is tested;
9. never flash a kernel/DTB/boot image;
10. verify Home, Settings, lockscreen, touch, rotation, SSH and frame updates immediately after deployment.

Rollback must restore prior files and profile state, restore GLVND symlinks, restart the safe session path, and prove the phone is usable. If the new profile fails, the helper must automatically select software-safe without requiring SSH intervention.

## 14. Required final deliverables

1. **Working code changes** for production GPU profile, fallback, diagnostics and any safe DMA-BUF/bridge improvements.
2. **Video decode implementation or exact blocker**. Do not remove the guard without proof.
3. **External display implementation or hardware/driver readiness report** with owner-test steps.
4. **Casting implementation or clearly labelled candidate/blocker report**.
5. Updated graphics profile schema and documentation.
6. Reproducible build scripts with pinned source commits and asset hashes.
7. Rootfs/image verifier that fails on missing or wrong GPU libraries.
8. Automated tests and regression results.
9. Live S10+ evidence folder with raw before/after measurements.
10. Deployment manifest and rollback script.
11. Updated `docs/beta-finalization/live/PWNAGE-60000-REPORT.md` with a PASS / PARTIAL / BLOCKED / NOT TESTED matrix for every workstream.
12. A short owner handoff stating exactly what needs physical cable/receiver/adapter tests and what must not be attempted without explicit approval.

## 15. Required final capability matrix

The final report must complete this table using evidence, not aspiration:

| Capability | Required final label | Evidence required |
|---|---|---|
| Phoc Mali rendering | PASS / FAIL | Live renderer, kbase FD/job evidence, no llvmpipe |
| GTK3 accelerated widgets | PASS / FAIL | GtkGLArea on live session |
| GTK4/GSK acceleration | PASS / FALLBACK / UNTESTED | Actual GSK renderer and real UI test |
| Home/Settings WebKit GPU rendering | PASS / FALLBACK / FAIL | Actual production process mappings/job evidence |
| WebKit SHM presentation | PASS / FAIL | Buffer transport trace |
| WebKit DMA-BUF presentation | PASS / BLOCKED | Real exported FD/import evidence, no false DRM identity |
| Final panel zero-copy scanout | PASS / NOT AVAILABLE | Proven scanout path with CPU copy absent |
| Framebuffer bridge optimization | PASS / PARTIAL | Timings, correctness and regression tests |
| Exynos MFC hardware decode | PASS / BLOCKED / NOT TESTED | Safe open, driver/firmware, real playback and CPU comparison |
| USB-C DP Alt Mode / HDMI | PASS / NEEDS OWNER TEST / BLOCKED | Negotiation, connector/EDID and real external pixels |
| Wireless Miracast | PASS / CANDIDATE / BLOCKED | P2P, RTSP, real capture, encode and receiver |
| LAN/WebRTC screen share | PASS / CANDIDATE / BLOCKED | Authenticated live stream and privacy tests |

## 16. Reference material to consult

Start with repository evidence, then verify upstream/vendor material relevant to the exact S10+ device:

- Samsung Exynos 9820 official specifications: <https://semiconductor.samsung.com/processor/mobile-processor/exynos-9-series-9820/> — MFC, supported codecs and silicon capability only.
- Samsung DeX wired display compatibility: <https://www.samsung.com/us/support/answer/ANS10001955/> — device/adapter support under Samsung software; not evidence that Nuxel Linux already has a driver.
- Samsung DeX external display modes: <https://developer.samsung.com/samsung-dex/how-it-works.html> — documented FHD/WQHD modes for supported DeX configurations.
- Samsung Wireless DeX/Miracast compatibility: <https://www.samsung.com/us/support/answer/ANS10001955/> — stock Samsung feature; Nuxel must implement its own P2P/capture/encode stack.
- Exact Samsung S10+ vendor kernel source, device tree, MFC driver and firmware provenance — use the matching S10+ Exynos 9820 source, not a driver for a different Exynos generation.
- Exact WebKitGTK 2.54.1 source and Fedora build flags for the `AcceleratedBackingStore` path described in PWNAGE-53000.

## 17. Execution order — no scope drift

Execute in this order:

1. **Audit current baseline** and re-run critical PWNAGE-53000 tests on phone.
2. **Production GPU profile** with safe fallback and release-image verification.
3. **GPU telemetry and regression tests** proving that normal Home/Settings processes are actually on Mali.
4. **WebKit DMA-BUF design/prototype** isolated from production; stop if a true kbase buffer path cannot be built safely.
5. **Framebuffer bridge optimization** while preserving one writer and existing display behavior.
6. **MFC driver/firmware safety investigation**; only then attempt the isolated hardware decode pipeline.
7. **Type-C/HDMI diagnostics and owner test plan**; no mux/PMIC experiments.
8. **Wireless casting architecture and implementation**; do not add a button before it works.
9. Full A/B measurements, physical smoke tests, atomic deploy and rollback.
10. Publish the PWNAGE-60000 report and explicit remaining blockers.

Do not let HDMI, casting or a speculative DRM kernel port delay the main deliverable: the production desktop must use the already-proven Mali GPU-rendered profile reliably, while keeping the existing framebuffer presentation stable.

## 18. Definition of DONE

This mission is **not** done because `glxinfo` says Panfrost, because one diagnostic app renders a triangle, because `gst-inspect` lists a decoder, because a USB-C adapter is detected, or because a Cast tile appears.

PWNAGE-60000 is done when:

- the normal Home/Settings UI actually uses the tested Mali-rendered profile;
- startup fallback is automatic, fast and reliable;
- release images cannot silently drop to software GL;
- GPU/transport/presenter status is individually truthful;
- the safe LINEAR DMA-BUF contract remains stable;
- any WebKit DMA-BUF improvement is proven with genuine cross-process buffers, or is explicitly documented as blocked;
- the framebuffer bridge is measurably improved without display/touch/rotation regressions;
- MFC decode is either genuinely implemented and measured or safely left guarded with a precise driver blocker;
- HDMI and casting are either proven end-to-end or explicitly marked as requiring further hardware work;
- all tests pass, all live evidence is recorded, deployment is reversible, and no boot-critical partition or firmware was touched.

**Build it, test it on the real phone, measure it, and tell the truth. No fake acceleration badges. No pretend zero-copy. No speculative kernel flash.**
