# PWNAGE-48000 — S10+ DRM/kbase GPU acceleration bring-up

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Mali-G76 MP12)
**Kernel:** Samsung downstream 4.14.253 `gf7194c1d15ed-dirty`
**Userspace:** Fedora 43 aarch64
**Date:** 2026-10-31
**Transport:** TWRP USB (`adb`) for flash, then Wi-Fi SSH (`nuxel@192.168.178.167`, key `~/.ssh/wicked_wqn_id_rsa`)

## Result

The phone now boots a kernel with **`CONFIG_DRM=y`**, **`# CONFIG_DRM_EXYNOS is not set`**, and a backported **`CONFIG_UDMABUF=y`**. The display remains on the proven DPU20 fbdev path (`/dev/fb0`), while the Mali-G76 is driven through ARM kbase (`/dev/mali0`) by Mesa panfrost on an EGL surfaceless display.

`phoc` runs with **`WLR_RENDERER=gles2`**, holds `/dev/mali0` and `/dev/udmabuf` descriptors, and creates compositor output buffers through wlroots' UDMABUF allocator. The `nuxel-wl-fb` bridge continues to present to the AMOLED and reports `FRAMES_OK`.

Verified live:

```
GL_VERSION=OpenGL ES 3.2 Mesa 26.3.0-devel
GL_RENDERER=Mali-G76 MC12 (Panfrost)
GL_VENDOR=Mesa
```

The probe rendered 3923 frames in 3 s into a 256×256 FBO and read back a green pixel (`33cc4dff`) with `glGetError=0x0`.

## What was wrong before

1. The pinned vendor kernel had `CONFIG_DRM` unset, so Mesa/wlroots had no EGL/GBM path at all.
2. Turning `CONFIG_DRM=y` with `CONFIG_DRM_EXYNOS=y` made the Exynos7 DECON DRM driver claim the `exynos-decon` platform driver name from the working DPU20 fbdev driver. `/dev/fb0` disappeared and the panel stayed dark.
3. Even with `CONFIG_DRM=y` and `CONFIG_DRM_EXYNOS=n`, stock wlroots refuses to create a GLES2 renderer without a DRM render node.
4. There is still no `/dev/dri`: the S10+ GPU is exposed only through ARM's proprietary kbase ABI, not DRM panfrost.

## Changes

### Kernel (`kernel/s10plus/`)

- `patches/0005-nuxel-udmabuf-kbase-buffers.patch`
  - Backports the 4.20 `udmabuf` misc driver to 4.14, adapted to this tree:
    - `shmem_get_seals()` instead of `memfd_fcntl()`,
    - adds `map_atomic`/`unmap_atomic`,
    - adds `UAPI linux/udmabuf.h`, Kconfig and Makefile entries.
  - Turns memfd pages into dma-bufs so wlroots can allocate GPU-renderable, CPU-readable output buffers.
- `configs/nuxel-drm-kbase.fragment`
  - `CONFIG_DRM=y`, KMS/FB helpers, MIPI DSI, panel/bridge helpers.
  - `CONFIG_DRM_EXYNOS=n` so DPU20 fbdev keeps the AMOLED.
  - `CONFIG_UDMABUF=y`, `CONFIG_DMA_SHARED_BUFFER=y`, CMA/SYNC_FILE.
  - `CONFIG_MALI_MIDGARD=y`, `CONFIG_MALI_BIFROST_R26P0=y`.
- `build-kernel-kbase.sh`
  - Reproducible wrapper: clone/checkout pinned source, apply patches, apply fragment, verify the three critical config lines, build `Image.gz` + dtbs.

### Mesa (`tools/s10plus/a67/build-mesa-kbase.sh`)

Built the experimental but functional `JimVulkan/mesa-unified-drivers` Mesa 26.3 branch in the podman aarch64 container:

- panfrost gallium driver with the **kbase pan_kmod backend**,
- GLVND EGL vendor library (`libEGL_mesa.so.0.0.0` exporting `__egl_Main`),
- `MESA_KBASE_NODE=/dev/mali0` surfaceless probe,
- EGL/GLES2, no DRM/GBM dependency for the kbase path,
- install RPATH rewritten to `$ORIGIN` with patchelf.

### wlroots (`tools/s10plus/a67/wlroots-kbase-surfaceless.patch`)

Patched upstream wlroots 0.19.3:

1. `wlr_egl_create_with_drm_fd(-1)` tries `EGL_PLATFORM_SURFACELESS_MESA` when `MESA_KBASE_NODE` is set, before the DRM/EGLDevice probe.
2. `egl_init_display()` tolerates a display with no `EGLDevice` (kbase has none).
3. `renderer_autocreate()` chooses GLES2 even with no DRM fd when `MESA_KBASE_NODE` is set.
4. Built with DRM + libinput backends, xwayland symbols, GBM and UDMABUF allocators, so `phoc`'s full symbol set is satisfied.

### Session integration

- `tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh`
  - tries GPU first (`WLR_RENDERER=gles2`, `MESA_LOADER_DRIVER_OVERRIDE=panfrost`, `MESA_KBASE_NODE=/dev/mali0`, `LIBGL_DRIVERS_PATH=/usr/lib64/dri`);
  - chmods `/dev/udmabuf` (misc default 0600) so the session user can allocate DMA-BUFs;
  - on a failed GPU start, writes `/run/nuxel-gpu-fallback` and systemd's next restart uses the proven pixman path;
  - `/run` is per-boot, so the device retries GPU acceleration on the next boot.
- `services/nuxel-session/systemd/nuxel-wayland.service` runs the wrapper.
- `tools/s10plus/a29/nuxel-session.sh` sets `GSK_RENDERER=gl` and `WEBKIT_DISABLE_COMPOSITING_MODE=0` only when `NUXEL_GPU=1`; the fallback keeps the old cairo/software settings.

## Flash and TWRP recovery

Built boot image:

```
build/out/s10plus/nuxel-beyond2lte-boot-drm-kbase.img
52,445,184 bytes, sha256 3751ae4121a78d7c67ce332f2536be2bece5bd6a81e49bb5236bfba20ad0b670
```

Flashed from TWRP with `dd` to `by-name/boot`, read back exactly 52,445,184 bytes and matched the hash byte-for-byte. The new kernel booted on the first attempt; the phone was not left in a bootloop. The TWRP fallback agreement remains in force: if a future flash hangs or bootloops, re-enter TWRP and reflash/rollback.

## Live evidence

- `evidence/pwnage-48000-kbase-gpu/01-kernel-and-nodes.txt`
- `evidence/pwnage-48000-kbase-gpu/02-gpu-probe.txt`
- `evidence/pwnage-48000-kbase-gpu/03-phoc-gpu-context.txt`
- `evidence/pwnage-48000-kbase-gpu/04-session-and-bridge.txt`
- `evidence/pwnage-48000-kbase-gpu/05-dmesg-gpu.txt`

Key facts from those files:

- `/dev/fb0` exists, `/dev/mali0` and `/dev/udmabuf` exist, `/dev/dri` does not.
- `phoc` has `/usr/lib64/libgallium_dri.so`, `/usr/lib64/libEGL_mesa.so.0.0.0`, patched `/usr/lib64/libwlroots-0.19.so`, three `/dev/mali0` fds, one `/dev/udmabuf` fd and an `anon_inode:dmabuf_udmabuf`.
- `/sys/kernel/debug/mali/gpu_memory` lists a kbase context owned by `phoc`.
- `nuxel-wayland`, `nuxel-wl-fb` and `nuxel-web` are active; no `/run/nuxel-gpu-fallback` marker exists.
- The bridge state reports `FRAMES_OK ... decon_pan_failed=0`.
- dmesg shows `Kernel DDK version r26p0-01eac0`, `GPU identified as ... arch 7.2.1`, `Probed as mali0`.

## Honest limitations

- There is still **no `/dev/dri`**. This is a kbase device, not DRM panfrost; software that hard-requires DRM/KMS cannot use it.
- `phoc` composes on the Mali GPU; the final `nuxel-wl-fb` screencopy → `/dev/fb0` conversion/upscale is still CPU work because the AMOLED is owned by the vendor fbdev DPU20 path.
- **WebKitGTK/GTK GL remains on its software fallback** (`GTK failed to initialize GL: No GL implementation is available`). Mesa's kbase support is surfaceless-only; the Wayland EGL platform still expects a DRM render node. A Wayland-enabled `libEGL_mesa` was built and tested too: GTK still failed for the same reason and the library was reverted. The session therefore leaves WebKit on the proven software path instead of pretending it is GPU-composited.
- The Mali kbase userspace is the experimental `JimVulkan/mesa-unified-drivers` Mesa fork. It is deployed as `libEGL_mesa`/`libgallium_dri` with a boot-time fallback, not as a kernel or bootloader change beyond the requested DRM/kbase config.

## Rollback

On the phone:

```sh
B=$(ls -d /var/backups/nuxel/kbase-gpu-* | tail -1)
sudo cp -a "$B/libEGL_mesa.so.0.0.0" /usr/lib64/
sudo cp -a "$B/libwlroots-0.19.so" /usr/lib64/
sudo cp -a "$B/50_mesa.json" /usr/share/glvnd/egl_vendor.d/
sudo cp -a "$B/nuxel-wayland.service" /etc/systemd/system/
sudo cp -a "$B/nuxel-session.sh" /usr/lib/nuxel/
sudo systemctl daemon-reload
sudo systemctl restart nuxel-wayland nuxel-wl-fb
```

To force the proven software path without restoring files:

```sh
sudo touch /run/nuxel-gpu-fallback
sudo systemctl restart nuxel-wayland nuxel-wl-fb
```

To restore the previous boot image (TWRP): reflash the saved image from `build/backup/` or the previous artifact, then `twrp reboot`.
