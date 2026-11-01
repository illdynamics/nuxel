# PWNAGE-53000 — Mali → EGL Wayland → DMA-BUF → GTK/WebKit: final report

**Date:** 2026-11-01
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Mali-G76 MP12)
**OS:** Nuxel (Fedora 43 aarch64), kernel `4.14.253-gf7194c1d15ed-dirty #5`
**Compositor:** Phoc 0.54.0 + wlroots 0.19.3 (Nuxel patched)
**Transport:** Wi-Fi SSH `root@192.168.178.167`

---

## 1. Executive summary

The mission started from a **false premise that had to be corrected first**: the
live Phoc was *not* running on Mali. `/usr/lib64/libEGL_mesa.so.0` pointed at
the stock `libEGL_mesa.so.0.0.0.nuxel-bak`; Phoc mapped
`libgallium-25.3.6.so` and ran **eight llvmpipe threads**. It never opened
`/dev/mali0`. A `dnf` transaction during an earlier experiment had reset the
glvnd symlink.

What now works on the physical phone, measured:

| Stage | Result |
|---|---|
| Phoc → Mali kbase | **PASS** — maps `libgallium_dri.so`, 3× `/dev/mali0`, no llvmpipe threads |
| EGL surfaceless GLES2 | **PASS** — `Mali-G76 MC12 (Panfrost)`, GLES 3.2, kbase jobs |
| EGL_PLATFORM_WAYLAND window surface | **PASS** — create/config/context/swap/destroy |
| linux-dmabuf v3 + LINEAR RGB | **PASS** — AB24/XB24/AR24/XR24 with `MOD_LINEAR` only |
| Phoc imports linear DMA-BUF | **PASS** — 20/20 accepted; malformed metadata never crashes Phoc |
| GTK3 GtkGLArea | **PASS** — renders on Mali, 3 frames, clean exit |
| WebKitGTK accelerated compositing | **PASS (GPU-rendered + SHM-presented)** — web process on kbase, `KBASE_IOCTL_JOB_SUBMIT` observed |
| WebKit DMA-BUF export/import | **BLOCKED** — no DRM/GBM node (`CONFIG_DRM_VGEM` unset) |
| Final scanout | CPU copy/scale in `nuxel-wl-fb` (honestly disclosed) |
| Display invariants | `FRAMES_OK`, `decon_pan_failed=0`, 1440×6080, one `/dev/fb0` writer |

**CPU (userspace, 8 cores, idle Home):** 47.0% of one core → **27.8–31.3%**
(phoc 27.5→17%, wl-fb 10.6→8.9%, WebKit 6.5→3.1%). The load average stays
~12 because **11 Samsung TrustZone/secure monitor kthreads sit in D state**
(`tz_worker_thread`, `ree_time`, `tz_iwsock`, `scsi_srpmb_work`); that is not
userspace CPU load. No attempt was made to alter those kernel threads.

---

## 2. Exact failure: metadata mismatch, not a Phoc crash

Controlled canary (second headless Phoc, never the live session):

```
zwp_linux_buffer_params_v1#9.add(fd 8, 0, 0, 2944, 134217728, 98)
zwp_linux_buffer_params_v1#9.create_immed(wl_buffer#10, 720, 1520, 875713089, 0)
wl_surface#5.attach(wl_buffer#10, 0, 0)
wl_surface#5.commit()
<client blocks; probe exit 124; Phoc PID unchanged, still serving>
```

- `875713089 = 0x34324241 = DRM_FORMAT_ABGR8888`
- modifier `(134217728<<32)|98 = 0x0800000000000062`
  = `ARM_BLOCK_SIZE=32x8, MODE=SPLIT|SPARSE`
- the kbase exporter (`NUXEL_KBASE_WSI=1`) allocates **linear** sealed
  memfd + `/dev/udmabuf` memory

The compositor advertised every modifier the renderer could *sample*, including
ARM tiled/compressed ones. Mesa therefore tagged a linear allocation with a
tiled modifier; the compositor could not consume it and never released the
buffer, so the **client** stalled on the next swap. This was previously reported
as "Phoc crashes" — it is not. The earlier SIGSEGV cores belong to a different,
forced-advertisement experiment.

Evidence: `evidence/pwnage-53000/crash/`.

## 3. Repair

`tools/s10plus/a67/wlroots-kbase-linear-dmabuf.patch`:

1. `wlr_linux_dmabuf_v1_create_with_formats()` filters the renderer's table to
   `(fourcc, DRM_FORMAT_MOD_LINEAR)` only. No ARM/AFBC modifier is advertised
   unless an allocator that produces it exists (none does on kbase).
2. A null `EGLDeviceEXT` (Mesa emits `EGL_BAD_DEVICE_EXT` but still returns a
   display) is treated as "no DRM identity" when `MESA_KBASE_NODE` is set.
3. The patch is built into `libwlroots-0.19.so` (sha256 `95e039a7…`), installed
   system-wide and pinned by build ID/hash.

The Mesa side keeps the opt-in `NUXEL_KBASE_WSI=1` sealed-memfd + udmabuf
exporter; the compositor keeps its proven native allocations.

## 4. Exact versions

| Component | Version |
|---|---|
| Mesa (kbase, Wayland WSI) | `26.3.0-devel (git-a5010bb447)` |
| Mesa (Fedora stock) | `25.3.6-3.fc43` |
| EGL loader | glvnd `libEGL.so.1.1.0` |
| GTK3 / GTK4 | `3.24.52` / `4.20.4` |
| WebKitGTK | `2.54.1-1.fc43` (webkit2gtk4.1) |
| Phoc | `0.54.0-1.fc43` |
| wlroots | `0.19.3-1.fc43` + Nuxel patches |
| `nuxel-wl-fb` | A67 adaptive-pacing build, sha256 `dbb1c214…` |

## 5. EGL proof

`evidence/pwnage-53000/egl/egl-wayland-live.log`:

```
STEP display=... err=0x3000
STEP eglInitialize 1.5 vendor=Mesa Project version=1.5
STEP chooseConfig n=4
STEP windowSurface=... err=0x3000
STEP context=... err=0x3000
STEP renderer=Mali-G76 MC12 (Panfrost) version=OpenGL ES 3.2 Mesa 26.3.0-devel
STEP clear ok err=0x0
PASS
```

Client EGL platforms: `EGL_EXT_platform_base`, `EGL_KHR_platform_wayland`,
`EGL_EXT_platform_wayland`, `EGL_EXT_platform_device`,
`EGL_MESA_platform_surfaceless`.

## 6. linux-dmabuf contract

Protocol `zwp_linux_dmabuf_v1` **v3** (legacy format/modifier table; no
feedback-device tranches because kbase has no DRM device identity).

Advertised RGB pairs (`evidence/.../dmabuf/formats.txt`):

```
0x34324241 AB24 LINEAR
0x34324258 XB24 LINEAR
0x34325241 AR24 LINEAR
0x34325258 XR24 LINEAR
```

YUV pairs are also LINEAR. No ARM tiled/SPARSE pair is advertised.

Validation performed by wlroots before import: plane count, fd validity,
offset, stride and bounds. Invalid offset/dimensions produce a Wayland protocol
error that closes **only the offending client**; Phoc keeps the same PID and
continues presenting. `evidence/.../dmabuf/` and `deployment/live-test-output.txt`.

## 7. GTK3 / GTK4

- GTK3 `GtkGLArea` on the live session:
  `{"gtk3_gl":"PASS","gl_renderer":"Mali-G76 MC12 (Panfrost)"}`.
- GTK4 4.20.4 is installed; its GSK renderer selection remains `auto` with
  `cairo` fallback. No GTK4 DMA-BUF claim is made.
- The Wayland-capable kbase Mesa set is installed system-wide
  (`libEGL_mesa.so.0.0.0` sha256 `eba18f34…`, `libgallium_dri.so`
  sha256 `818bc380…`) and pinned with
  `/etc/systemd/system/nuxel-wayland.service.d/50-kbase-egl.conf` +
  `/etc/nuxel/egl-kbase.json` so a package update cannot silently reset the
  glvnd symlink again.

## 8. WebKitGTK

WebKitGTK 2.54.1 `AcceleratedBackingStore::rendererBufferTransportMode()`
requires, in order:

1. client EGL extension `EGL_KHR_platform_gbm` **or**
   `EGL_MESA_platform_surfaceless` — present;
2. `USE(GBM)` and `drmMainDevice()` non-null — **absent** (no `/dev/dri`);
3. UI-process GL display with `KHR_image_base` +
   `EXT_image_dma_buf_import` — present.

Because step 2 is false, WebKit only adds `SharedMemory`; it never adds
`Hardware`, even though Phoc now imports LINEAR DMA-BUF correctly.

Measured result with `WEBKIT_FORCE_COMPOSITING_MODE=1` and the kbase EGL set:

- web process maps `libgallium_dri.so` and `libEGL_mesa.so.0.0.0`
- 3× `/dev/mali0`, 4 `ThreadedCompositor` threads
- **186 `KBASE_IOCTL_JOB_SUBMIT`** (`_IOW(0x80,0x02,0x10)`) in a 3 s strace
- **0** udmabuf/dmabuf FDs in the web process → presentation is shared memory

This is truthfully labelled **`gpu-rendered-shm-presented`**, not DMA-BUF
acceleration. Evidence: `evidence/pwnage-53000/webkit/`.

## 9. Why WebKit DMA-BUF is blocked on this kernel

- `/dev/dri` does not exist; `CONFIG_DRM_VGEM` is **not set**.
- `CONFIG_MODULES=y` and `modules_disabled=0`, but `CONFIG_MODVERSIONS=y` and
  the exact kernel's `Module.symvers` is not on the device. An out-of-tree
  `vgem.ko` cannot be loaded without rebuilding the exact kernel tree and
  matching symbol CRCs.
- A DRM/GBM node would have to come from a kernel change (`CONFIG_DRM_VGEM=y`
  or equivalent), which is outside this mission's no-flash boundary. Symlinking
  `/dev/mali0` to a fake `/dev/dri/renderD*` was explicitly not done: kbase
  does not implement the DRM ioctl ABI.

## 10. Performance

| Metric | Before (llvmpipe) | After (Mali + linear dmabuf + new bridge) |
|---|---|---|
| Phoc CPU | 27.5% | 13.8–17.2% |
| `nuxel-wl-fb` CPU | 10.6% | 6.4–8.9% |
| WebKitWebProcess CPU | 6.5% | 3.1–4.7% |
| UI host CPU | 2.4% | 2.1–2.9% |
| **sum (one core)** | **47.0%** | **27.8–31.3%** active UI |
| **sum, post-reboot idle** | — | **16.0%** (phoc 7.9, wl-fb 3.5, WebKit 1.7, host 2.1) |
| blit average | 45 ms | 20–38 ms |
| idle capture (static) | fixed 24 fps | 1 fps after 12 s (verified 10/10 s) |

Post-reboot verification (15:33, `evidence/.../performance/postreboot.txt`): all
five services active, Phoc on kbase Mesa with 3× `/dev/mali0`, linux-dmabuf v3
LINEAR RGB, `FRAMES_OK`, `decon_pan_failed=0`, one `/dev/fb0` writer, no fallback
marker, and two snapshots 2 s apart differ (the live clock is updating).

Remaining CPU work, disclosed: every changed frame is still
`screencopy → CPU memcmp/damage → NEON 2× row expansion → `/dev/fb0` mmap →
FBIOPAN_DISPLAY`. There is no DRM/KMS scanout node, so this copy cannot be
removed on the current kernel. The bridge skips blits for unchanged frames
(`present_skipped`), and the A67 NEON path converts each source pixel once.

The live Home clock changes once per second, which legitimately keeps the
capture cadence around 7 fps; a truly static screen settles to 1 fps.

## 11. Profiles and rollback

`/etc/nuxel/graphics/graphics-profile.json` (schema 2) and
`/usr/lib/nuxel/nuxel-graphics-profile` expose:

- `software-safe` — measured, default; WebKit SHM, no EGL in the web process
- `gpu-rendered-shm-presented` — measured; Mali EGL rendering + SHM transport
- `gpu-rendered-dmabuf-presented` — **unavailable**, loud fallback reason
- `fully-accelerated` — **unavailable**, loud fallback reason

Home/Settings/lockscreen stay on `software-safe`. The diagnostic app
`pwnage53000-diagnostic` is the only entry using the GPU-SHM profile.

Deploy: `tools/s10plus/a67/deploy-pwnage53000.sh` (hash-verified backup,
atomic install, restart, state check).
Rollback: `tools/s10plus/a67/rollback-pwnage53000.sh`.

**Rollback was executed and verified live:** it restored the pre-change
llvmpipe set (stock EGL symlink, old wlroots, old `nuxel-wl-fb`), Phoc came back
with 8 llvmpipe threads, and `FRAMES_OK` / `decon_pan_failed=0` held. The
accelerated set was then redeployed and the full acceptance suite passed again.

## 12. Deployment hashes

| Artifact | SHA-256 |
|---|---|
| `libEGL_mesa.so.0.0.0` (kbase Wayland WSI) | `eba18f340e519bbd04765c0744bb7f554df99ca328f3dd7921698600d3477b0f` |
| `libgallium_dri.so` | `818bc380242006c158455241099b3b5185dfc70630f6f4c9cda5602a9196b800` |
| `libwlroots-0.19.so` (linear-only) | `95e039a783bf4e9263542a01f9609e03ffb4b2f8d47ca9ec23c60a6803d2d4cc` |
| `nuxel-wl-fb` | `dbb1c2149706f76c508f56a40433ee82df2fe338a4907fae26ac660141af1258` |
| `nuxel-graphics-profile` | `10a66e8431a118abfdbef307773eab8d724a90fbecf069c2b038a64d1188c04b` |
| pre-change backup | `/var/backups/nuxel/p53000-20261101T143813` |
| post-rollback backup | `/var/backups/nuxel/p53000-20261101T152336` |

## 13. Honest definition-of-done status

Met on the physical phone: EGL Wayland on Mali; GTK GL; WebKit GPU-rendered
compositing; Phoc safe against malformed DMA-BUF; LINEAR import; per-app
fallback; display invariants; measured CPU reduction; rollback proven.

**Not met, blocked by the kernel ABI boundary:** WebKit DMA-BUF export/import
and true zero-copy presentation. This needs a DRM/GBM allocation node
(e.g. `CONFIG_DRM_VGEM=y` or an equivalent) in a separately approved kernel
build. No fake `/dev/dri`, no kbase unload, no flash, no bootloader change was
attempted.
