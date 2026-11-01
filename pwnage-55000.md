# PWNAGE-55000 — Unlock WebKit DMA-BUF Presentation
## Kernel DRM/VGEM integration, exact kernel rebuild, TWRP-authorized flash and boot recovery

**Target:** Nuxel on Samsung Galaxy S10+ (`beyond2lte`, Exynos 9820)  
**Priority:** Critical  
**Task type:** Kernel configuration, kernel rebuild, WebKit DMA-BUF integration and physical-device deployment  
**Flash authorization:** Explicitly granted under the TWRP agreement below.

### Mission

Remove the remaining kernel/DRM integration blocker preventing WebKitGTK 2.54.1 from selecting its Hardware DMA-BUF transport.

The current physical-phone results already prove:

- Phoc runs on Mali kbase.
- EGL surfaceless and Wayland rendering work on Mali-G76.
- Linear linux-dmabuf v3 import works in Phoc.
- GTK3 GtkGLArea renders on Mali.
- WebKit's web process performs genuine Mali GPU work.
- WebKit currently presents through SHM rather than the desired DMA-BUF transport.

The leading kernel candidate is enabling the existing kernel's native VGEM DRM driver **built into the kernel**:

```text
CONFIG_DRM=y
CONFIG_DRM_VGEM=y
CONFIG_MODVERSIONS=y
```

These are candidate settings, not permission to blindly change the configuration. Verify their exact availability, dependencies, source compatibility and ABI consequences in the actual Linux 4.14.253 tree before building.

Do not build or load an out-of-tree `vgem.ko` without the exact matching kernel build and `Module.symvers`.

### Critical technical distinction

VGEM is a virtual, non-hardware-backed GEM/PRIME provider. It can provide a DRM render-node/PRIME interface, but it is not the Mali GPU, not a Mali render driver and not a physical display controller.

Prove that WebKit can:

1. Discover a valid DRM main device.
2. Select a usable GBM device.
3. Receive real DMA-BUF file descriptors from its GPU-rendered buffers.
4. Import them successfully through GBM.
5. Present them through the existing Nuxel Wayland/Phoc path.
6. Avoid the SHM fallback.

Do not claim full acceleration simply because `/dev/dri` or `renderD128` appears.

### TWRP agreement

The owner will place the phone in **TWRP recovery with USB connected before the implementation agent starts the deployment phase**.

The owner explicitly authorizes the agent to:

- Inspect the connected recovery environment.
- Back up the existing kernel-containing boot target.
- Build the required Nuxel kernel.
- Flash the verified kernel-containing artifact.
- Keep TWRP/recovery intact.
- Reboot the phone into Nuxel.
- Diagnose and roll back a failed boot using the saved known-good image.

The agent must verify that the connected device is the intended `beyond2lte` device in TWRP before writing anything.

**Do not flash until the exact target partition, image format, backup and rollback route are verified.**

Never overwrite TWRP/recovery, userdata, bootloader, modem, EFS or unrelated partitions.

### Requirements

1. Inspect the exact kernel source, build scripts, active kernel configuration and installed kernel before changing anything.
2. Verify `CONFIG_DRM_VGEM` and all dependencies in that exact Linux 4.14.253 source tree.
3. Prefer `CONFIG_DRM_VGEM=y` built in, avoiding an independently compiled VGEM module and its unresolved ABI problem.
4. Preserve `CONFIG_MODVERSIONS=y`. Generate the correct `Module.symvers` from the exact build and verify any affected external modules, especially Mali kbase.
5. Do not blindly port `CONFIG_UDMABUF` or later-kernel code into 4.14. Trace the actual DMA-BUF exporter required by WebKit.
6. Do not symlink `/dev/mali0` to a fake DRM render node.
7. Do not introduce a fake Mali DRM driver, fake KMS device or misleading capability report.
8. Preserve the existing working Phoc/Mali EGL, kbase, linear DMA-BUF import and framebuffer bridge.
9. Diagnose the previous failed TWRP/kernel boot attempt. Do not repeat the same unverified image or repacking process.
10. Build the complete boot artifact using Nuxel's actual device packaging process. Preserve the correct DTB, ramdisk, boot image header and kernel command line.
11. Back up the current boot target to the host and verify its SHA-256 before flashing.
12. Flash only the verified kernel-containing partition/artifact.
13. Reboot into Nuxel and verify the device boots, Mali works and the new DRM/VGEM device is real and operational.
14. Test WebKit's actual DMA-BUF exporter, FD handoff and GBM importer.
15. Measure the final display path separately. A CPU copy into `/dev/fb0` is not zero-copy physical presentation.

### Required acceptance tests

- [ ] Device boots into Nuxel after the flash.
- [ ] TWRP remains intact and accessible.
- [ ] Mali kbase loads and works.
- [ ] Phoc remains on Mali, with zero llvmpipe fallback.
- [ ] EGL Wayland rendering works.
- [ ] Linear DMA-BUF v3 Phoc import remains 20/20 or better.
- [ ] A real DRM device and render node appear through the native driver.
- [ ] VGEM is identified as VGEM, not misreported as Mali.
- [ ] WebKit sees `drmMainDevice()`.
- [ ] WebKit selects Hardware DMA-BUF transport.
- [ ] Real DMA-BUF FDs are exported by the WebKit rendering path.
- [ ] GBM imports the buffers successfully.
- [ ] SHM fallback is not silently used.
- [ ] GTK/WebKit presentation remains correct.
- [ ] Framebuffer invariants remain intact.
- [ ] The four acceleration profiles report truthful capabilities.
- [ ] A safe rollback image and procedure are available.

### Performance and truthful completion

Keep these stages separate:

1. Mali GPU rendering.
2. WebKit renderer-to-UI DMA-BUF transport.
3. GTK/GBM DMA-BUF import.
4. Phoc DMA-BUF import.
5. Physical display presentation.

The existing physical framebuffer path still incurs a measured 20–38 ms CPU copy/scale operation per blit. Do not label the entire pipeline zero-copy or fully accelerated until that final stage is also addressed.

### Deliverables

- Root-cause analysis of the missing kernel capability.
- Exact kernel configuration diff.
- Build and module ABI evidence.
- Complete rebuilt kernel/boot artifact.
- TWRP backup and verified flash record.
- Successful Nuxel boot evidence.
- DRM/VGEM device and capability evidence.
- WebKit DMA-BUF FD/export/import proof.
- Performance measurements.
- Updated acceleration profile definitions.
- Complete rollback instructions.

**Definition of done:** WebKit uses real, verified DMA-BUF transport on the Mali-rendered workload, the physical S10+ boots reliably into Nuxel, and no unsupported acceleration capability is reported as working.
