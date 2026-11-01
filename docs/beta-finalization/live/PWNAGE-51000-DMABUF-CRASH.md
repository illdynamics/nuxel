# PWNAGE-51000 — Phoc linux-dmabuf / WebKitGTK crash analysis

## Live result

- Phoc is on the kbase GPU path: 3× `/dev/mali0`, `/dev/udmabuf`,
  `anon_inode:dmabuf_udmabuf`, kbase context owned by `phoc`.
- `nuxel-wl-fb.state` is `FRAMES_OK … decon_pan_failed=0`.
- The live Wayland global list contains **no `zwp_linux_dmabuf_v1`**.
- `/dev/dri` is absent (expected for vendor kbase).

## Why no dmabuf global is advertised

The patched wlroots creates the kbase dmabuf global only when
`wlr_renderer_get_texture_formats(r, WLR_BUFFER_CAP_DMABUF)` is non-NULL.
The Mali/Panfrost kbase GLES2 renderer on this stack returns no DMA-BUF texture
formats, so wlroots correctly skips the global. It logs:

```
drmGetDevices2 failed: No such file or directory
Failed to get DRM FD from renderer
Failed to get renderer DRM FD
```

in `types/wlr_linux_dmabuf_v1.c`. This is a renderer capability limit, not a
protocol version typo.

## Crash evidence

Preserved in `evidence/pwnage-51000/dmabuf/`:

- `coredumps/core.phoc…1793525508…zst` (SIGSEGV)
- `coredumps/core.phoc…1793525522…zst` (SIGSEGV)
- `coredumps/probe-33821.zst` (Wayland EGL probe, SIGSEGV)
- journal files from the crash window
- exact `phoc`, `libwlroots-0.19.so`, `libwayland-server` build IDs

Core backtrace (newest Phoc core, symbolised against the live libraries):

```
#0 wlr_seat_set_capabilities+448 (libwlroots-0.19.so)
#1 wl_client_destroy (libwayland-server.so.0.26.0)
```

The compositor also produced SIGBUS cores in the same test series.
The Wayland EGL probe crashes in Mesa:

```
#0 0x…  (libgallium/EGL)
#1 dri2_destroy_surface (libEGL_mesa.so.0)
```

This is a Mesa kbase Wayland-EGL surface teardown fault, below Phoc.

## Decision

- Keep the live compositor's proven kbase path; do **not** enable a live
  linux-dmabuf global by force.
- Keep WebKitGTK accelerated backing store **disabled**; `nuxel-pwa-host`
  continues to report the shared-memory/software fallback.
- A future fix must first make the kbase renderer report a valid, importable
  format/modifier set, then pass a minimal export/import/attach/commit/release
  stress client, then repeat with real WebKit frames. A protocol advertisement
  alone is not acceptance.

## GPU regression repaired during this run

The stock Mesa gallium and EGL symlink had replaced the kbase set. Restored and
verified:

```
libEGL_mesa.so.0.0.0       3800718931c0b359be31374c8ab0ce10ee6b1926992a7d8646a8746176a0f71e
libgallium_dri.so          b5e167ef0bd0479a797d1e38c6704fec7cfd3fb99a6bc4e6ad8a461aa777f5b1
libwlroots-0.19.so         2ccada1a6fb4cbf4b371567754efaed2ee6266daf8320c0b6791f7b61c58247c
panfrost_dri.so -> ../libgallium_dri.so
exynos_dri.so   -> ../libgallium_dri.so
```

Probe result after restore:
`GL_RENDERER=Mali-G76 MC12 (Panfrost)`, `Mesa 26.3.0-devel`, rendered pixel
`33cc4dff`, `glGetError=0x0`.
