# GPU / WebKit Wayland WSI decision

Date: 2026-11-01. Target: S10+ kbase (`/dev/mali0`), no `/dev/dri`.

## Route A — vendor Mali userspace

Not used. A vendor Android `libmali`/gralloc stack is not a native Linux Wayland WSI
implementation and would require Android binder/gralloc services. No redistributable,
ABI-matched native Linux AArch64 vendor EGL was found on the image. No global EGL/GLES
replacement was attempted.

## Route B — Mesa panfrost on kbase

Chosen for investigation. The existing fork (`JimVulkan/mesa-unified-drivers`) already drives
Mali-G76 through kbase on `EGL_PLATFORM_SURFACELESS_MESA`. Two missing pieces were found and
implemented as patches:

1. `platform_wayland.c` now accepts `MESA_KBASE_NODE` and creates a DRI screen from the kbase
   node without a DRM render node.
2. `pan_kmod`/`kbase_kmod` gained an exportable-BO path: sealed memfd + `UDMABUF_CREATE`,
   imported by kbase, with the dma-buf fd returned for `wl_buffer` creation. This path is
   opt-in (`NUXEL_KBASE_WSI=1`) so the compositor keeps its proven native allocations.

Patch: `tools/s10plus/a67/mesa-kbase-wayland-wsi.patch`.
Build: `tools/s10plus/a67/build-mesa-kbase-wayland.sh` (isolated output; never installed
over the system libraries by default).

## Route C — udmabuf

Used as the exporter inside Route B. A direct 4,583,424-byte memfd→udmabuf test succeeds on
the live kernel. The Mesa path now returns the ioctl result fd correctly (the earlier failure
was treating the returned fd as an error because it was non-zero). No arbitrary pages are
exported: only page-aligned, sealed memfds allocated by the process.

## Route D — WebKit buffer transport

WebKitGTK 2.54.1 uses the accelerated backing store only when the GTK/Wayland EGL stack can
create a window surface and share the resulting buffers. With the live Phoc, the required
`zwp_linux_dmabuf_v1` global is absent, so WebKit correctly remains on software. No WebKit
fork or sandbox change was made.

## Wlroots / compositor

Patch: `tools/s10plus/a67/wlroots-kbase-dmabuf.patch`. When `MESA_KBASE_NODE` is set and the
renderer has no DRM fd, wlroots creates a v3 `zwp_linux_dmabuf_v1` global from the renderer's
format table instead of failing the feedback-device check.

A second headless Phoc using this library advertises `zwp_linux_dmabuf_v1` v3 and the Wayland
EGL probe passes with real Mali rendering and udmabuf export/import. The **live** Phoc with the
same global crashes (SIGSEGV/SIGBUS in `driBindContext`/`gles2_texture_from_buffer` during
screencopy), so the production session was reverted to the proven surfaceless kbase compositor.

## Decision

- Keep Phoc on the surfaceless kbase path.
- Keep WebKitGTK on explicit software fallback by default.
- Keep the Wayland WSI canary available for further compositor-side work.
- Do not claim WebKit acceleration until the live compositor can advertise linux-dmabuf
  without crashing and a real Home PWA frame is observed on the AMOLED.
