# Exact failure analysis (PWNAGE-53000)

## What actually failed

The failing process was the **Wayland client** (Mesa's `eglSwapBuffers`), not
Phoc.  In the controlled canary (second headless Phoc on `/run/nuxel-wsi-repro2`,
never the live session):

```
zwp_linux_buffer_params_v1#9.add(fd 8, 0, 0, 2944, 134217728, 98)
zwp_linux_buffer_params_v1#9.create_immed(wl_buffer#10, 720, 1520, 875713089, 0)
wl_surface#5.attach(wl_buffer#10, 0, 0)
wl_surface#5.commit()
<client blocks until timeout; Phoc PID unchanged and still serving>
```

`create_immed` fourcc `875713089 = 0x34324241 = DRM_FORMAT_ABGR8888`.
The modifier is `(134217728 << 32) | 98 = 0x0800000000000062`, i.e.
`ARM_BLOCK_SIZE=32x8, MODE=SPLIT|SPARSE` — a tiled/compressed ARM layout.

The kbase exporter (`NUXEL_KBASE_WSI=1`) allocates a **linear** sealed
memfd + `/dev/udmabuf` buffer.  The compositor advertised every modifier the
renderer could *sample*, including the ARM tiled ones, so Mesa selected a
tiled modifier for a physically linear allocation.  Import/metadata mismatch:
the buffer was never released, so the client stalled on its next swap.

It is therefore **not** a Phoc crash, not a wlroots assertion and not a kbase
fault.  The prior SIGSEGV cores came from a separate forced-advertisement
experiment; the reproducible failure here is a metadata-contract violation.

## Fix

`tools/s10plus/a67/wlroots-kbase-linear-dmabuf.patch` filters the advertised
set to `(fourcc, DRM_FORMAT_MOD_LINEAR)` pairs only.  The exporter allocates
linear memory, so the contract now matches reality.  The same patch also
treats a null `EGLDeviceEXT` as "no DRM identity" on kbase instead of failing
initialisation (Mesa returns a null device while emitting
`EGL_BAD_DEVICE_EXT`).

## Post-fix proof

- `dmabuf/formats.txt`: only LINEAR pairs; RGB `XB24/AB24/XR24/AR24` present.
- `gtk/gtk3-live.log`: GtkGLArea renders on `Mali-G76 MC12 (Panfrost)`.
- `egl/egl-wayland-live.log`: full window-surface create/swap/destroy PASS.
- `deployment/live-test-output.txt`: malformed offset disconnects only that
  client; Phoc PID unchanged; `FRAMES_OK`; `decon_pan_failed=0`.
