# GPU acceleration report — Galaxy S10+ (`beyond2lte`)

**Executive verdict:** `PARTIAL` — the compositor renders through the Mali-G76 with Mesa/Panfrost and Phoc GLES2, but the final panel path is still a CPU framebuffer copy, and WebKit/GTK do not have a production dma-buf presentation path. Do not call the UI “fully accelerated.”

- Capture date: 2026-11-08
- Boot ID: `7c9fdaef-9a9d-4968-a76e-c541dbfcea0b`
- Target: SM-G975F, Exynos 9820, Mali-G76 MP12 (`gpuinfo`: `Mali-G76 12 cores r0p0 0x7211`)
- Evidence tier: `PASS_DEVICE_RUNTIME` for node/process/probe observations; `PASS_HOST` for source/config inventory.

## 1. Component inventory

| Layer/component | Current renderer/driver | Allocator/transport | Present path | Hardware evidence | Status | First missing stage | Recommended work |
|---|---|---|---|---|---|---|---|
| Mali-G76 kbase kernel driver | Samsung kbase, `/dev/mali0` | kbase ioctls | n/a | `/sys/class/misc/mali0/device/gpuinfo`; phoc holds 3 `/dev/mali0` fds | WORKS | — | Keep; do not replace with a DRM render node blindly |
| Mesa GLES/EGL userspace | Mesa 26.3.0-devel, Panfrost | EGL/GLES2/3.2 | n/a | `/run/nuxel/graphics-gpu-probe.json`: `renderer=Mali-G76 MC12 (Panfrost)`, `gl_version=OpenGL ES 3.2`, `ok=true` | WORKS | — | Keep pinned build; record hash |
| Phoc/wlroots compositor | Phoc, `WLR_RENDERER=gles2` | SHM/udmabuf | composites in GL | phoc env `MESA_LOADER_DRIVER_OVERRIDE=panfrost`, `MESA_KBASE_NODE=/dev/mali0`, `__EGL_VENDOR_LIBRARY_FILENAMES=/etc/nuxel/egl-kbase.json`; 1.8 % CPU idle | WORKS (partial) | Panel presentation is CPU-copy | Preserve; optimize damage/present path only with proof |
| dma-buf/UDMABUF | `CONFIG_UDMABUF=y` | udmabuf | imported by Phoc | `/dev/udmabuf`; phoc fd 16; `dmabuf_udmabuf` anon inode | WORKS | WebKit lacks `drmMainDevice` | WebKit/GTK WSI research (§4) |
| Display/panel scanout | Exynos DPU20 fbdev `/dev/fb0` | CPU blit | framebuffer pan/update | 1440×3040, 32 bpp, `U:1440x3040p-0` | WORKS (CPU copy) | Zero-copy scanout | Keep stable; benchmark damage/region copy |
| `nuxel-wl-fb` presenter | CPU shm screencopy | wl_shm | copies/scales 720×1520 → 1440×3040 into `/dev/fb0` | `NUXEL_TARGET_FPS=20`; ~0.2 % CPU idle | WORKS (copy-bound) | Damage-region/zero-copy path | Safe R1/R2: measure copy volume; try damage region |
| WebKitGTK | `gpu-rendered-shm-presented` | SHM | compositor presents | profile `graphics-profile.json`; no EGL in web process | PARTIAL | `RendererBufferTransportMode::Hardware` requires `drmMainDevice()` | Isolated WSI experiment |
| GTK3 | `gpu-rendered-shm-presented` | SHM | compositor presents | profile | PARTIAL | same WSI gap | same |
| GTK4/GSK | `GSK_RENDERER=gl` validated | GL | compositor presents | profile evidence | WORKS | — | Keep cairo fallback |
| Flatpak graphics | runtime-selected Mesa | runtime | varies | Flatpak sandbox does not get host kbase EGL by policy | PARTIAL | host/runtime ABI + device exposure | Do not force host stack into sandbox |
| Video decode (MFC) | not proven | — | — | separate hardware media engine; not GPU | UNKNOWN | MFC device/userspace | Investigate separately; never label as GPU |
| Image/text/UI assets | mostly CPU/WebKit | — | — | — | PARTIAL | — | Cache/decode reductions only with measurements |
| External display/casting | not proven | — | — | no `/dev/dri` | NOT_SUPPORTED_TODAY | — | Separate route |

## 2. What is actually proven

- `/dev/mali0` exists and the compositor owns real kbase fds.
- A surfaceless EGL/GLES probe succeeds with `renderer=Mali-G76 MC12 (Panfrost)`, `EGL 1.5`, `OpenGL ES 3.2 Mesa 26.3.0-devel`, in 536 ms (`/run/nuxel/graphics-gpu-probe.json`).
- Phoc runs `WLR_RENDERER=gles2` with the kbase EGL vendor file and `MESA_KBASE_NODE=/dev/mali0`.
- `/dev/udmabuf` exists and Phoc holds a udmabuf fd; `linux-dmabuf` advertises `LINEAR` only.
- The panel is still fed by `nuxel-wl-fb` via `/dev/fb0`; the final copy is CPU, not scanout from a GPU buffer.
- There is no `/dev/dri` render node and `CONFIG_DRM_EXYNOS=n`, `CONFIG_DRM_VGEM=n`, `CONFIG_UDMABUF=y`, `CONFIG_DRM=y`.

## 3. Exact blocker chain

1. **WebKit/GTK WSI:** WebKitGTK 2.54.x selects `RendererBufferTransportMode::Hardware` only when it can obtain a `drmMainDevice()`. This kernel exposes no DRM render node for the display path (`/dev/dri` absent; `CONFIG_DRM_VGEM=n`), so WebKit falls back to SHM. A canary global `zwp_linux_dmabuf_v1` path previously crashed live Phoc during screencopy; production was reverted.
2. **Final presentation:** even with a GPU-rendered WebKit buffer, the panel owner is `nuxel-wl-fb`, which screencopies into SHM and CPU-copies/scales into fb0. The GPU→panel path is not zero-copy.
3. **Format/modifier:** `linux-dmabuf` advertises `LINEAR` only; vendor tiled modifiers are not proven usable by the current Mesa/kbase/Phoc combination.
4. **Sandbox:** Flatpak runtimes do not receive the host kbase EGL stack; that is intentional, so Flatpak acceleration must be solved inside the runtime, not by bind-mounting host GL.

## 4. Recommended architecture and staged work

**Primary:** keep the stable Phoc/Panfrost→SHM→fb0 path as production. Build a **separate, gated WebKit WSI experiment** that provides a DRM-compatible main device or a supported dma-buf feedback path, with an immediate rollback to software-safe. Do not change the production compositor to chase a benchmark.

| Phase | Work | Gate |
|---|---|---|
| 0 (safe, now) | Instrument `nuxel-wl-fb` copy volume/damage regions; record phoc/WebKit CPU and frame pacing | Host + device runtime |
| 1 | Isolated Phoc build with `linux-dmabuf` experimental path and a canary WebKit run | No production switch; crash-free 10-min run |
| 2 | WebKitGTK WSI research: `drmMainDevice`/EGL platform support on this kbase stack; test a minimal WebKit renderer change | Isolated build; screencopy stress |
| 3 | GTK3/GTK4 flatpak runtime validation with the runtime's own GL | Sandbox launch + render proof |
| 4 | Kernel/DRM prerequisite decision: DRM render node vs a supported WebKit transport that does not need one | Kernel team review; no flash in this mission |
| 5 | Zero-copy panel presentation only if the display controller path supports it and the fallback remains | Physical visual + touch/input regression |

## 5. Why generic fixes are insufficient

- “Install Panfrost” is already done: Mesa reports Panfrost on Mali-G76.
- `WEBKIT_DISABLE_COMPOSITING_MODE=0` does not create a DRM main device or a supported dma-buf export path.
- A GPU fd in Phoc does not prove WebKit or the panel path is accelerated.
- MFC video decode is a separate hardware media engine; it is not “GPU acceleration.”

## 6. Verification matrix

| Check | State |
|---|---|
| `/dev/mali0` + kbase GPU info | `PASS_DEVICE_RUNTIME` |
| EGL/GLES probe renderer | `PASS_DEVICE_RUNTIME` |
| Phoc GLES2 + kbase env | `PASS_DEVICE_RUNTIME` |
| Phoc holds mali/udmabuf fds | `PASS_DEVICE_RUNTIME` |
| WebKit hardware buffer transport | `BLOCKED_HARDWARE` (no `drmMainDevice`) |
| Final panel zero-copy | `BLOCKED_HARDWARE` (CPU fb0 copy) |
| Flatpak GPU | `NOT_TESTED` / sandbox policy |
| Video MFC decode | `NOT_TESTED` |

## 7. Conclusion

The compositor is **GPU-rendered but not fully GPU-presented**. The highest-value next step is an isolated WebKit/GTK WSI experiment, not a production swap. Keep the current software-safe fallback and the `nuxel-wl-fb` panel owner until a crash-free, physically verified zero-copy path exists.

**Raw evidence:** `diagnostics/pwnage-91000/hardware/gpu-*`, `/run/nuxel/graphics-gpu-probe.json`, `configs/nuxel/graphics/graphics-profile.json`, `docs/beta-finalization/live/PWNAGE-48000-KBASE-GPU-REPORT.md`, `PWNAGE-60000-GPU-MANIFEST.md`, `GPU-WEBKIT-WSI-DECISION.md`.
