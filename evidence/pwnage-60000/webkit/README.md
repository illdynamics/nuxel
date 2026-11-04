# WebKitGTK 2.54.1 DMA-BUF gate — live evidence

Source: `https://github.com/WebKit/WebKit` tag `webkitgtk-2.54.1`
Tag object: `7696d0bd527da5fe48563a5476c32199087db8cd`
Peeled commit: `628d6ce1850e17225185a5807a9d0aa375bae2be`
Files saved here are verbatim from that commit:
- `Source/WebKit/UIProcess/gtk/AcceleratedBackingStore.cpp`
- `Source/WebKit/UIProcess/glib/DRMMainDevice.cpp`
- `Source/WebKit/UIProcess/glib/DRMMainDevice.h`

## The exact gate

`AcceleratedBackingStore::rendererBufferTransportMode()` (saved file, lines
81–116):

1. `WEBKIT_DISABLE_DMABUF_RENDERER` must be unset/0.
2. The client EGL extensions must contain `EGL_KHR_platform_gbm` **or**
   `EGL_MESA_platform_surfaceless` — both are present on the S10+.
3. It adds `RendererBufferTransportMode::SharedMemory`.
4. `WEBKIT_DMABUF_RENDERER_FORCE_SHM` must be unset/0.
5. Under `USE(GBM)`, `drmMainDevice()` must be non-null.  On the S10+ it is
   null, so the function returns with SHM only and never adds
   `RendererBufferTransportMode::Hardware`.

`drmMainDevice()` (saved `DRMMainDevice.cpp`, lines 188–255) tries:
- `WEBKIT_WEB_RENDER_DEVICE_FILE` (still requires a real render node; see below);
- the current EGL display's `EGL_EXT_device_drm_render_node`;
- `drmGetDevices2(0, ...)` and the first device with `DRM_NODE_RENDER`.

Live probe (`nuxel-drm-main-device-probe.c`) calls the same `drmGetDevices2`
enumeration on the phone:

```
drm_devices=error errno=2
render_nodes=0 webkit_drmMainDevice_is_null=true
WEBKIT_WEB_RENDER_DEVICE_FILE=unset
```

`errno=2` is `ENOENT`: no DRM device exists.  `/dev/dri` is absent and
`CONFIG_DRM_VGEM` is unset (`live-required.config` line 63).

## Why `WEBKIT_WEB_RENDER_DEVICE_FILE` is not a workaround

Setting it to `/dev/mali0` would make `DRMDevice::renderNode` non-null, but the
next WebKit steps call GBM/DRM ioctls that kbase does not implement.  It would
also be exactly the forbidden "fake DRM identity" shortcut.  It is therefore
not set and not proposed as a production path.

## Options evaluated

| Option | Result |
|---|---|
| Bypass only the `drmMainDevice()` check | Rejected: the Hardware path still needs a GBM allocator (`gbm_bo_create`, `DRMDeviceManager::mainGBMDevice`). No real GBM device exists. |
| `WEBKIT_WEB_RENDER_DEVICE_FILE=/dev/mali0` | Rejected: kbase is not a DRM render node; fake identity. |
| Symlink `/dev/mali0` to `/dev/dri/renderD*` | Rejected by mission rule; kbase has no DRM ioctl ABI. |
| `CONFIG_DRM_VGEM=y` alone | Insufficient: VGEM would satisfy enumeration, but its buffers are not kbase-exportable/scanout-capable and the panel path is fbdev/DECON, not DRM/KMS. Building/flashing a kernel is outside this mission. |
| Real Exynos DRM/KMS + kbase export + panel integration | Independent kernel/display project; `CONFIG_DRM_EXYNOS=n` is deliberate because of the DPU20 fbdev ownership conflict. Not attempted. |
| Custom WebKit SHM→udmabuf export transport | Not available in 2.54.1; would require a large WebKit patch plus a kbase-exportable allocator. No production claim. |

**Conclusion:** WebKit DMA-BUF presentation is `BLOCKED` on this kernel.  The
production path remains `gpu-rendered-shm-presented`; the final panel is the
CPU framebuffer bridge.  This is not a "failed experiment" to hide: it is the
truthful ABI boundary.
04cf5db6c78c42ece790d14940780227cd6a270ceef40e43c04edec72739ca84  evidence/pwnage-60000/webkit/AcceleratedBackingStore.cpp
f4ac07386953a171d8ff2a91df2cdf32b98b0a86a4714a733af9ba0dc91f4075  evidence/pwnage-60000/webkit/DRMMainDevice.cpp
64d8147bf66273cf7bd566bed13c1dd2709e321a95839dd789cabf001e7aef88  evidence/pwnage-60000/webkit/DRMMainDevice.h
COMMIT 628d6ce1850e17225185a5807a9d0aa375bae2be
