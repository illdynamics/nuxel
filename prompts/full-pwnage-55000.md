# FULL PWNAGE-55000 — The Last WebKit Acceleration Blocker
## Native DRM/VGEM kernel integration, Mali DMA-BUF handoff, exact kernel rebuild, TWRP flash, boot recovery and end-to-end validation

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Device:** Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820  
**Kernel baseline:** Existing Nuxel downstream Linux 4.14.253 unless repository evidence proves a different active kernel  
**Userspace:** Fedora ARM64, Phoc/Wayland, WebKitGTK 2.54.1, Mali-G76 MC12 / kbase  
**Priority:** Critical  
**Deployment:** TWRP recovery over USB, kernel-containing artifact only  
**Flash authorization:** Explicitly granted under Section 4  
**Main objective:** Unlock and prove WebKit's GPU-rendered DMA-BUF presentation path without destabilizing the existing working Mali/Phoc stack.

---

# 0. Mission

Finish the remaining kernel/DRM integration work required to make Nuxel's WebKitGTK rendering pipeline use DMA-BUF transport instead of the current SHM fallback.

The physical device is already substantially accelerated.

Do not waste time rebuilding working EGL, Mali, Phoc or GTK functionality unless the kernel change reveals a regression.

The remaining blocker is the boundary between WebKit's GPU-rendered buffers and the UI/compositor presentation path.

The leading candidate is the missing native kernel VGEM DRM provider, enabled in the exact downstream kernel and built into the kernel image:

```text
CONFIG_DRM=y
CONFIG_DRM_VGEM=y
```

The actual 4.14.253 source must be inspected first. `CONFIG_DRM_VGEM` depends on DRM and MMU. Do not assume modern kernel Kconfig dependencies or source compatibility apply to this tree.

The task is not finished when `/dev/dri` appears.

It is finished when the actual WebKit workload:

1. Renders on the Mali GPU.
2. Produces real exportable DMA-BUF file descriptors.
3. Transfers those descriptors through WebKit's renderer/UI boundary.
4. Imports them through the actual GBM/DRM device selected by WebKit.
5. Presents the buffers correctly through Nuxel's existing compositor path.
6. Does not silently fall back to SHM.

The existing phone must continue booting into Nuxel.

The existing display, Wi-Fi, input, SSH and framebuffer behavior must remain intact.

---

# 1. Current physical-device facts — treat these as the baseline

The following results were observed on the actual physical phone, not merely inferred from source code.

Do not repeat experiments that already passed unless a kernel change regresses them.

## 1.1 Verified working stages

| Stage | Result | Evidence |
|---|---|---|
| Phoc on Mali kbase | **PASS** | Maps `libgallium_dri.so`, 3× `/dev/mali0`, zero llvmpipe threads |
| EGL surfaceless | **PASS** | `Mali-G76 MC12 (Panfrost)`, GLES 3.2 |
| EGL Wayland window surface | **PASS** | Surface creation and swap work |
| linux-dmabuf v3 | **PASS** | AB24/XB24/AR24/XR24, LINEAR only |
| Phoc import of linear DMA-BUF | **PASS** | 20/20; malformed metadata does not crash Phoc |
| GTK3 GtkGLArea | **PASS** | Mali rendering, 3 frames, clean exit |
| WebKit accelerated compositing | **PASS** | GPU-rendered, SHM-presented; web process generated 186 `KBASE_IOC_TL_JOB_SUBMIT` calls in 3 seconds |
| WebKit DMA-BUF export/import | **BLOCKED_KERNEL_ABI** | Zero udmabuf/DMABUF FDs observed |
| Display invariants | **PASS** | `FRAMES_OK`, `decon_pan_failed=0`, 1440×6080, one `/dev/fb0` writer |

## 1.2 The exact missing capability

The current WebKitGTK 2.54.1 implementation gates its Hardware renderer-buffer transport on a discoverable DRM main device.

The previous investigation established:

- No `/dev/dri` node currently exists.
- `CONFIG_DRM_VGEM` is unset.
- `CONFIG_MODVERSIONS=y`.
- The exact matching `Module.symvers` for the currently running image was not available for safely building an out-of-tree VGEM module.
- An out-of-tree `vgem.ko` was therefore not loaded.
- No `/dev/mali0` symlink or fake DRM render node was introduced.
- GPU rendering works, but WebKit currently hands off its composited frames through SHM.
- The final physical framebuffer copy/scale operation still consumes CPU time, measured at approximately 20–38 ms per blit.

The previous work correctly stopped before loading an ABI-unsafe module.

Continue from that point.

## 1.3 Existing acceleration profile status

The profiles:

- `gpu-rendered-dmabuf-presented`
- `fully-accelerated`

are currently marked unavailable and fall back loudly.

Keep this truthful behavior until the actual buffer handoff succeeds.

Do not change profile labels to green merely because a new DRM device node appears.

---

# 2. Important technical interpretation

This section is mandatory reading before changing kernel configuration.

## 2.1 What VGEM actually provides

VGEM is a virtual, non-hardware-backed GEM service.

Its purpose is to provide a DRM GEM/PRIME buffer-sharing interface. It is not:

- A Mali GPU driver.
- A replacement for Mali kbase.
- A hardware GPU execution engine.
- A physical display controller.
- A DECON driver.
- A DRM/KMS implementation for the Samsung AMOLED panel.
- A magic device that converts ordinary CPU memory into physically zero-copy display scanout.

The Linux DRM VGEM driver can provide a DRM device and render-node interface, and its kernel implementation has GEM/PRIME operations.

The Linux DRM PRIME framework uses DMA-BUF file descriptors to exchange buffer objects between drivers and processes.

This makes VGEM relevant to WebKit's GBM path, but does not prove that the Mali rendering buffers can be exported or imported successfully.

**The agent must distinguish between making WebKit's DRM-device discovery succeed and making the actual Mali-rendered buffer transfer succeed.**

## 2.2 The specific WebKit condition

Inspect the exact WebKitGTK 2.54.1 source and the source used to build the installed Nuxel binary.

The previous analysis found the following relevant logic in WebKit's GTK accelerated backing store:

- SHM transport can be available without a DRM device.
- Hardware transport is withheld when `drmMainDevice()` is null.
- Under GBM, WebKit uses the discovered DRM device and a GBM render or primary node.
- It requires the necessary EGL image/DMA-BUF import capabilities.
- The import path uses a GBM FD import operation and requests rendering plus linear buffer usage.

The actual installed build must be checked for:

- `USE(GBM)`.
- `USE(LIBDRM)`.
- EGL support.
- GBM backend.
- Renderer buffer transport mode.
- Whether distro or Nuxel patches modify the relevant path.
- The runtime environment.
- Any `WEBKIT_*` environment variables affecting DMA-BUF behavior.

Do not assume the installed WebKit build matches upstream source exactly.

## 2.3 Do not confuse these three things

| Capability | Meaning |
|---|---|
| DRM main-device discovery | WebKit can identify a DRM device |
| DMA-BUF transport | WebKit's renderer can hand a buffer FD to the UI process and the UI process can import it |
| Hardware display scanout | The physical display controller consumes the buffer without a CPU copy |

These are separate capabilities.

VGEM may solve the first and help with the second.

VGEM does not provide the third.

---

# 3. Kernel configuration strategy

The current blocker strongly points toward native DRM/VGEM integration.

The safest approach is to build the required component into the exact kernel image, not introduce an independently compiled out-of-tree module.

## 3.1 Inspect the live kernel before touching source

Capture:

```bash
uname -a
uname -r
cat /proc/version
```

Inspect the currently running kernel configuration from the actual phone using the available mechanism:

- `/proc/config.gz`, if enabled.
- Installed kernel build artifacts.
- Nuxel's recorded kernel configuration.
- Existing defconfig.
- Configuration fragments.
- Build logs.
- The exact source commit and patch set.

Also inspect:

- Currently loaded kernel modules.
- Mali kbase driver location.
- Existing module metadata.
- Current boot image version.
- Current device tree and DTB arrangement.
- Current kernel command line.
- Existing boot image header and packaging details.

Save the original configuration and calculate its hash.

Do not start from a generic Exynos9820 or upstream defconfig.

The active Nuxel downstream kernel configuration is the baseline.

## 3.2 Find the exact kernel source tree

Identify the exact source tree used to build the kernel currently installed on the phone.

Determine:

- Repository.
- Branch.
- Commit.
- Local patches.
- Build scripts.
- Toolchain.
- Cross-compilation target.
- Defconfig.
- Configuration fragments.
- Image target.
- Module install target.
- Boot image packaging target.
- DTB/DTBO integration.
- Initramfs integration.
- TWRP installer, if applicable.

Do not silently switch from the currently working downstream Linux4 baseline to an unrelated mainline or postmarketOS kernel.

Do not upgrade the kernel version as an opportunistic part of this task.

The scope is the minimum safe change needed to unblock WebKit.

## 3.3 Inspect the actual `DRM_VGEM` Kconfig entry

In the exact source tree, inspect:

```text
drivers/gpu/drm/Kconfig
drivers/gpu/drm/vgem/
```

Confirm that:

- `CONFIG_DRM_VGEM` exists.
- Its source is compatible with the exact 4.14.253 kernel.
- It can be built as a built-in component.
- Its dependencies are available.
- Its implementation supports the required DRM node and PRIME behavior.
- It is not affected by an incompatible downstream patch.
- It does not rely on helpers unavailable in the target tree.

The known historical Kconfig arrangement defines `DRM_VGEM` as a tristate option requiring DRM and MMU.

The exact source must remain authoritative.

Do not import a modern VGEM implementation into Linux 4.14 merely because the current upstream source looks cleaner.

## 3.4 Preferred setting

If source inspection confirms that the existing driver supports the required functionality, prefer:

```text
CONFIG_DRM=y
CONFIG_DRM_VGEM=y
```

Built-in VGEM avoids the need for a separately versioned `vgem.ko`.

`CONFIG_DRM_VGEM=y` is the leading candidate, not a guaranteed complete fix.

If `CONFIG_DRM` is already enabled, preserve it.

If DRM core is disabled, evaluate the dependency and impact before enabling it.

Do not enable a broad collection of unrelated DRM drivers.

## 3.5 Do not enable unnecessary display drivers

The target phone currently has a working vendor framebuffer/DECON path.

Do not introduce an experimental physical KMS driver simply to make `/dev/dri` appear.

In particular, do not enable unrelated:

- `DRM_VKMS`.
- `DRM_EXYNOS`.
- `DRM_SIMPLEDRM`.
- Experimental KMS components.
- Additional fbdev emulation paths.
- Display-controller drivers that do not match the active panel and device-tree integration.

A virtual GEM render-node provider is not a physical display driver.

Avoid creating a second display stack that conflicts with the working framebuffer path.

## 3.6 Check `CONFIG_DMA_SHARED_BUFFER`

The DMA-BUF framework must be available.

Check the actual configuration:

```text
CONFIG_DMA_SHARED_BUFFER
```

If already enabled, preserve it.

If not enabled, inspect the exact kernel dependencies and the effect of enabling it.

Do not assume that a working Wayland linux-dmabuf import test automatically proves all required kernel interfaces are available to WebKit.

## 3.7 `CONFIG_UDMABUF` and the 4.14 boundary

Do not blindly add:

```text
CONFIG_UDMABUF=y
```

Stock upstream `CONFIG_UDMABUF` is not present in the original Linux 4.14 Kconfig history; the option appears in later kernels.

The existing Nuxel system may have a separately integrated udmabuf/u-dma-buf implementation, a backport or a vendor component.

Inspect the actual source tree and device.

Determine:

- Whether `udmabuf` is present.
- Whether it is a built-in component or module.
- Which kernel source it came from.
- Whether `/dev/udmabuf` exists.
- What API it exposes.
- Whether WebKit actually invokes that API.
- Whether the observed zero-FD condition is caused by its absence.
- Whether the required FD should instead be exported directly by EGL/Mali.

If the installed 4.14 tree has no `CONFIG_UDMABUF`, do not invent a configuration line.

If a later udmabuf implementation genuinely is needed, treat it as a separate porting exercise with source review, ABI analysis and device tests.

Do not blindly transplant Linux 6.x code into Linux 4.14.

---

# 4. TWRP agreement and deployment authorization

The owner explicitly authorizes a targeted Nuxel kernel rebuild and flash under the following agreement.

## 4.1 Owner's preparation

The owner will:

1. Boot the phone into TWRP recovery.
2. Connect the phone by USB to the build/deployment computer.
3. Leave the phone in TWRP while the agent performs the deployment handshake.
4. Keep the device connected during the backup, flash and initial reboot.
5. Allow the agent to reboot the phone into Nuxel after a verified flash.

The agent must not expect the device to be in Android, fastboot or an ordinary Nuxel userspace session.

It must verify the actual recovery state.

## 4.2 Agent's TWRP handshake

At deployment start:

1. Enumerate USB devices.
2. Run the appropriate ADB device discovery.
3. Confirm that the device is listed in the `recovery` state.
4. Confirm TWRP is responding to ADB.
5. Identify the model and board.
6. Confirm `beyond2lte` / SM-G975F / Exynos 9820 identity using reliable device properties and partition/device information.
7. Confirm the device has sufficient battery or stable power.
8. Confirm the USB connection is stable.
9. Confirm the expected boot/partition layout.
10. Confirm the exact kernel-containing partition used by the existing Nuxel deployment workflow.

Do not assume that fastboot is available simply because Android devices commonly use it.

Use the actual transport exposed by this Samsung recovery environment.

Do not run a flash command against an unidentified device.

## 4.3 Explicit write authorization

The owner authorizes a targeted kernel flash once all preflight checks pass.

The authorized write scope is limited to the verified kernel-containing artifact/partition required by the existing Nuxel boot arrangement.

The following remain outside authorization:

- TWRP/recovery.
- Bootloader.
- Modem.
- EFS.
- Radio firmware.
- Userdata.
- System partitions unrelated to the kernel change.
- Device-tree partitions unless the proven Nuxel image format requires them and the owner has separately approved that exact change.

Do not use a broad all-partitions installer.

Do not format or wipe anything.

Do not factory-reset.

Do not unlock anything.

Do not modify Samsung bootloader state.

## 4.4 Preserve TWRP

TWRP is the recovery mechanism for this task.

Do not overwrite it.

Before flashing:

- Identify its actual partition.
- Verify that the planned operation will not write to it.
- Back up the current kernel-containing boot image.
- Preserve a copy of the known-good boot image off-device.
- Verify the backup can be read.
- Record SHA-256.
- Record partition name and size.
- Record the intended restore procedure.

A read-only backup of the recovery/TWRP partition is appropriate where practical, but do not flash or modify it.

## 4.5 Backup requirements

Before the first write, save:

- Current kernel-containing boot image.
- Current device configuration.
- Current kernel version.
- Current boot command line.
- Current DTB/DTBO identity.
- Current partition map.
- Current recovery/TWRP identity.
- Existing relevant kernel module files.
- The last known-good Nuxel kernel artifact, if separately available.

Copy the boot backup off-device.

Do not rely only on a backup stored in the phone's internal userdata.

Verify the host-side backup with SHA-256.

The agent must be able to restore the previous known-good boot image through TWRP without relying on the new kernel booting.

---

# 5. Diagnose the earlier failed boot before reflashing

There was a previous attempt where returning to TWRP did not result in a working Nuxel boot; the device bootlooped or hung.

This must be treated as a real root-cause problem.

Do not repeat the old flash procedure blindly.

## 5.1 Find previous evidence

Inspect the available:

- Failed build artifacts.
- Failed boot images.
- TWRP logs.
- Recovery logs.
- Kernel build logs.
- Boot image repacking commands.
- Installer scripts.
- `pstore`.
- `ramoops`.
- Previous `last_kmsg`, where available.
- Existing Nuxel logs.
- Previous TWRP screenshots or diagnostic packs.
- Git changes around the failed attempt.

Determine exactly what changed between the previously working and failed artifacts.

## 5.2 Boot-image integrity

Verify the complete boot image format and packaging.

Inspect:

- Android boot image header version.
- Page size.
- Kernel payload.
- Compression format.
- Kernel load address.
- Ramdisk.
- Ramdisk load address.
- Second-stage payload, if present.
- DTB placement.
- DTBO handling.
- Kernel command line.
- Board identity.
- Header metadata.
- Boot image signature/verification expectations.
- Required Samsung-specific packaging.

Do not assume a generic `mkbootimg` invocation is correct.

Use the exact packaging method already used by Nuxel, unless there is evidence that this method caused the previous failure.

If the device uses a legacy Android boot image format, preserve its existing format and required metadata.

Do not strip or replace an appended DTB without understanding how the current boot image consumes it.

## 5.3 Compare the known-good and failed images

Where available, unpack both.

Compare:

- Kernel binary.
- DTB.
- Ramdisk.
- Command line.
- Header.
- Compression.
- Payload ordering.
- Image size.
- Page alignment.
- Package contents.
- Installer target.
- Partition selection.

Explain the previous boot failure before repeating the operation.

If the previous failure cannot be conclusively explained, use the most conservative known-good packaging path and introduce only the minimum kernel change.

## 5.4 Do not flash an unverified artifact

Before any device write:

- Verify the kernel build completed.
- Verify the expected image exists.
- Verify image architecture.
- Verify image header.
- Verify DTB presence.
- Verify ramdisk compatibility.
- Verify expected image target.
- Verify image hash.
- Verify flash target.
- Verify recovery rollback image.
- Verify there is no accidental recovery partition write.

If any check fails, stop before the first write.

---

# 6. Build the exact kernel safely

## 6.1 Preserve the existing baseline

Use the source tree and configuration currently used by the physical Nuxel image.

Do not migrate the device to another kernel.

Do not upgrade from 4.14.253 just to obtain a newer VGEM implementation.

Do not replace the existing kernel toolchain without a reason.

Record the exact baseline:

- Kernel version.
- Source commit.
- Patch set.
- Defconfig.
- Config fragments.
- Toolchain version.
- Cross-compiler.
- Build target.
- Existing image packaging tool.

Create a clean working branch or build worktree.

Preserve the original `.config`.

## 6.2 Make a minimal configuration diff

The preferred change should be limited to the DRM core and native VGEM support plus any strictly required dependencies.

Candidate:

```text
CONFIG_DRM=y
CONFIG_DRM_VGEM=y
```

Preserve:

```text
CONFIG_MODVERSIONS=y
```

Preserve the existing working Mali/kbase configuration.

Do not remove existing symbols merely to make the VGEM build pass.

Do not change CPU frequency, memory layout, IOMMU, CMA, Mali scheduling, framebuffer or device-tree configuration without a proven dependency.

Record the complete before/after configuration diff.

## 6.3 Use `olddefconfig` only with review

After changing the configuration:

- Run the correct config resolution process.
- Review every resulting configuration change.
- Inspect any automatically selected dependencies.
- Inspect any disabled options.
- Verify the required options are actually enabled in the final `.config`.
- Verify the target kernel source includes the requested component.

Do not accept unexplained broad config changes.

## 6.4 Built-in VGEM

Prefer building VGEM into the kernel:

```text
CONFIG_DRM_VGEM=y
```

This is the preferred route because it avoids introducing a separately built VGEM module whose symbol CRCs may not match the installed kernel.

The driver still has to be proven to compile and function in this exact downstream 4.14 tree.

Do not merely assume that a modern upstream implementation is compatible.

## 6.5 Module versioning and ABI preservation

The existing kernel uses:

```text
CONFIG_MODVERSIONS=y
```

Keep it enabled.

Do not disable module versioning as a shortcut.

Do not bypass symbol CRC checking.

Do not force-load modules with mismatched version magic or symbol CRCs.

Build the entire relevant module set using the exact output tree and matching `Module.symvers`.

The kernel documentation explains that `Module.symvers` contains exported kernel/module symbols and CRC values; with `CONFIG_MODVERSIONS`, mismatches cause a module to be rejected.

The agent must verify:

- The new kernel's `Module.symvers`.
- The exact build source and configuration used to produce it.
- All installed third-party modules.
- Mali kbase module compatibility, if it is loadable.
- Any other modules that the Nuxel boot depends on.
- Module vermagic.
- Symbol CRC compatibility.
- Built-in versus module placement.

If Mali kbase is built as a module, rebuild it from its exact compatible source against the matching new kernel build.

If the module is vendor-provided and cannot safely be rebuilt, prove its compatibility before flashing.

Do not proceed if the kernel config change breaks the existing Mali driver ABI.

## 6.6 No out-of-tree VGEM module

Do not build an isolated `vgem.ko` using:

- A different kernel source version.
- A generic kernel headers package.
- An unrelated `/lib/modules` tree.
- A guessed `Module.symvers`.
- An incomplete output directory.
- A vendor defconfig from another device.

A module built without the exact symbol CRC context is not an acceptable solution here.

If VGEM is built in, no separate VGEM module load should be necessary.

---

# 7. Verify the VGEM implementation itself

Do not assume the Kconfig option alone tells the whole story.

Inspect the exact local source implementation.

## 7.1 Driver characteristics

Confirm that the local VGEM driver:

- Registers a DRM device.
- Provides the expected DRM driver name.
- Advertises render-node capability if supported by that version.
- Advertises PRIME support if supported by that version.
- Provides required GEM operations.
- Implements required import/export callbacks.
- Uses a memory model compatible with the intended DMA-BUF operations.
- Does not try to control physical display scanout.
- Does not conflict with Mali kbase.
- Does not create a second physical display owner.

## 7.2 Check actual DRM node creation

After boot, discover nodes from the real device:

- `/dev/dri/card*`
- `/dev/dri/renderD*`

Do not hardcode `card0` or `renderD128` until runtime discovery proves those identifiers.

For each node, collect:

- Driver name.
- Sysfs path.
- Device identity.
- Major/minor.
- Permissions.
- Whether it is primary or render.
- DRM capabilities.
- PRIME capabilities.
- Relevant format/modifier capabilities.

The VGEM device must be identified as VGEM.

Do not describe it as a Mali DRM node.

## 7.3 No fake symlink

The existing Mali node is:

```text
/dev/mali0
```

Do not create:

```text
/dev/dri/renderD128 -> /dev/mali0
```

Do not make a symlink, bind mount or fake device-node alias to trick WebKit, GBM, libdrm or Mesa.

Use a real, correctly registered kernel DRM device.

---

# 8. Investigate the actual WebKit DMA-BUF exporter

This is the key point where a successful VGEM build may or may not finish the task.

The report says zero DMA-BUF/udmabuf FDs were observed.

A render node alone cannot make a buffer appear if the producer never exported one.

Trace the FD from origin to destination.

## 8.1 Inspect installed WebKitGTK 2.54.1

Determine how the installed WebKitGTK binary was built.

Inspect:

- Exact WebKitGTK version.
- Build configuration.
- `USE(GBM)`.
- `USE(LIBDRM)`.
- EGL extensions.
- DMA-BUF import extension.
- DMA-BUF export extension.
- `drmMainDevice()` behavior.
- `DRMDeviceManager`.
- `GBMDevice`.
- `RendererBufferTransportMode`.
- `AcceleratedBackingStore`.
- Web process implementation.
- UI process implementation.
- Any Nuxel patches.
- Environment overrides.

Use the actual installed source/build metadata wherever available.

Do not assume the current upstream branch is identical to Nuxel's binary.

## 8.2 Prove DRM main-device discovery

After booting the new kernel:

- Verify `drmMainDevice()` returns a real device.
- Record the selected primary node.
- Record the selected render node.
- Record driver name.
- Record the GBM initialization result.
- Record whether the render node falls back to primary.
- Record any GBM backend errors.

If DRM discovery still returns null, diagnose that before investigating buffer content.

Potential issues include:

- No DRM primary node.
- Missing render node.
- Incorrect device permissions.
- Udev/sysfs enumeration problems.
- Main-device selection choosing an unsuitable node.
- GBM not supporting the selected driver.
- A mismatched libdrm/GBM version.
- Missing runtime dependencies.
- WebKit not compiled with the relevant feature.

Do not fix a DRM discovery error by fabricating a device link.

## 8.3 Verify EGL capabilities

From the same runtime environment used by the WebKit process, inspect:

- `EGL_KHR_image_base`.
- `EGL_EXT_image_dma_buf_import`.
- `EGL_EXT_image_dma_buf_import_modifiers`, if available.
- `EGL_MESA_image_dma_buf_export`, if available.
- Any relevant Mali EGL extensions.

Record the exact EGL vendor, version and extension string.

Test the capabilities in the actual WebKit web process context where possible.

A standalone EGL program passing does not prove WebKit's process has the same environment or driver selection.

## 8.4 Trace the producer

Determine exactly which component should create the DMA-BUF FD.

Possibilities must be tested rather than guessed:

- Mali EGL image export.
- GBM allocation.
- Existing udmabuf integration.
- WebKit's buffer allocation.
- A renderer-specific shared-buffer mechanism.
- A fallback path using SHM.

Instrument the real producer.

Capture:

- Allocation request.
- Pixel format.
- Width and height.
- Stride.
- Modifier.
- Allocation backend.
- DMA-BUF export call.
- Returned file descriptor.
- Failure code.
- Lifetime.
- Ownership.
- Synchronization.

If the actual Mali EGL driver cannot export the relevant render target, enabling VGEM will not magically export it.

Do not claim VGEM solves the producer side without evidence.

## 8.5 Verify the receiving process

In the WebKit GTK UI process:

- Identify the received FD.
- Verify it is a DMA-BUF where possible.
- Check that the FD remains valid.
- Check its format.
- Check dimensions.
- Check stride.
- Check modifier.
- Check synchronization.
- Attempt GBM import.
- Record `gbm_bo_import()` result.
- Record a precise failure code.

The known WebKit GBM path requests an FD import with rendering and linear usage.

Verify that the actual driver stack accepts the required parameters.

## 8.6 Respect the currently tested format boundary

The working Phoc linux-dmabuf path supports:

- AB24.
- XB24.
- AR24.
- XR24.

The proven modifier is LINEAR only.

Do not enable modifier combinations that have not been tested.

Initially target the proven linear format path.

If the producer emits a different format or tiled modifier, identify the conversion or capability-negotiation issue.

Do not silently reinterpret a tiled buffer as linear.

---

# 9. DMA-BUF synchronization and lifetime

A DMA-BUF FD is not by itself proof that the buffer is safe to display.

Test:

- Producer completion.
- Fence signaling.
- Import completion.
- Buffer lifetime.
- Reuse.
- Release.
- Cache synchronization.
- CPU mapping behavior.
- GPU/display consumer ordering.

Do not remove synchronization merely to get a passing import count.

If the current stack has limitations around fences, establish the exact limitation and implement the supported synchronization path.

The current linear-only path must remain deterministic.

Malformed or incomplete metadata must fail safely.

Phoc must not crash.

The Nuxel UI must not display corrupted or torn buffers.

---

# 10. WebKit transport selection

After the new kernel boots, verify the actual `RendererBufferTransportMode` selected by WebKitGTK.

The desired result is:

```text
Hardware DMA-BUF transport available
```

The required evidence is stronger than a log message saying acceleration is enabled.

Verify:

1. `drmMainDevice()` is non-null.
2. The expected GBM device is initialized.
3. EGL exposes the required extensions.
4. The WebKit renderer chooses Hardware rather than only SharedMemory.
5. A real DMA-BUF FD is produced.
6. The UI process receives it.
7. GBM imports it.
8. The GTK/WebKit UI path presents it.
9. The compositor receives the correct output.
10. SHM is not the active fallback.

Do not force a Hardware mode in source code if the required buffer export/import capability is unavailable.

Do not disable the SHM fallback globally merely to make the tests look accelerated.

During development, force-Hardware/disable-SHM experiments may be useful as isolated diagnostics, but they must not become production defaults unless every prerequisite has been proven.

Report the final production environment variables and build options.

---

# 11. Preserve Phoc and Mali acceleration

The existing working Phoc/Mali state is a critical invariant.

After the kernel rebuild and flash, verify all of the following again.

## 11.1 Mali kbase

- `/dev/mali0` exists.
- Correct owner/group/permissions.
- Mali kbase module or built-in driver is active.
- No symbol CRC failures.
- No module version mismatch.
- No unexpected reset.
- No GPU fault.
- No new kernel warning or panic.

## 11.2 Phoc

Verify:

- Phoc maps `libgallium_dri.so`.
- Phoc retains the existing Mali kbase device access.
- Three expected `/dev/mali0` handles or their actual current equivalent remain present.
- No llvmpipe worker threads appear.
- No software rendering fallback occurs.
- Output remains visible.
- Wayland clients still connect.
- `zwlr_screencopy` remains functional.
- linux-dmabuf v3 remains available.

## 11.3 EGL

Repeat the proven EGL tests:

- Surfaceless display.
- Mali-G76 MC12.
- GLES 3.2.
- Wayland window surface.
- Swap.
- Basic rendering.
- Clean teardown.

If any previously working test now fails, stop the acceleration rollout and diagnose the regression.

## 11.4 GTK3

Repeat GtkGLArea:

- Create.
- Render.
- Swap.
- Destroy.
- Exit cleanly.

Record GPU activity.

The kernel change must not regress the existing GPU-rendered GTK test.

---

# 12. Preserve the physical display architecture

The Nuxel physical display path currently works.

The known architecture is:

```text
Phoc / Wayland
      |
      v
zwlr_screencopy
      |
      v
nuxel-wl-fb
      |
      v
/dev/fb0
      |
      v
Samsung DECON / AMOLED
```

The invariant remains:

**`nuxel-wl-fb` is the sole `/dev/fb0` writer.**

Do not introduce a second framebuffer writer.

Do not start an additional KMS display server.

Do not allow VGEM to become a physical display owner.

Do not change the physical output configuration merely to make WebKit's GBM importer happy.

## 12.1 Post-flash display checks

Verify:

- `FRAMES_OK`.
- `decon_pan_failed=0`.
- Existing 1440×6080 virtual framebuffer state, or the verified current dimensions.
- One `/dev/fb0` writer.
- Correct framebuffer pitch/stride.
- Correct scanout.
- No black frame.
- No stale output.
- No visual corruption.
- No regression in Nuxel UI responsiveness.

## 12.2 Keep the framebuffer bridge stable

The new DRM/VGEM device must not interfere with:

- `nuxel-wl-fb`.
- The DECON framebuffer driver.
- Existing fbdev mapping.
- Existing panel configuration.
- Existing Phoc screencopy.
- Existing Wayland output state.

If enabling DRM core introduces a conflict, investigate and correct the cause rather than disabling the existing physical display path.

---

# 13. Separate WebKit DMA-BUF success from final physical scanout

The report measured the final `/dev/fb0` copy/scale step at approximately 20–38 ms per blit.

That is an important remaining performance boundary.

Do not hide it.

There are at least two distinct milestones:

## 13.1 WebKit DMA-BUF presentation

This task's main target is to enable the actual WebKit renderer/UI DMA-BUF path.

The corresponding profile should become available only when:

- Hardware transport is selected.
- Real FDs are exported.
- GBM imports them.
- The UI process successfully presents them.
- SHM is not being used as the active WebKit backing-store transport.

Phoc's existing linear DMA-BUF import can then be tested as the next stage.

## 13.2 Zero-copy physical display

The physical AMOLED is currently driven through the framebuffer/DECON path.

The existence of a VGEM render node does not turn this framebuffer architecture into a DRM/KMS scanout implementation.

If `nuxel-wl-fb` still copies or scales pixels on the CPU, the whole display pipeline is not zero-copy.

Do not mark `fully-accelerated` as achieved until the final physical display stage is also proven to avoid the CPU copy.

A later separate project may be required to investigate:

- A compatible DMA-engine blit.
- A safe DMA-BUF-to-framebuffer transfer.
- A supported display-controller import mechanism.
- A real Exynos DRM/KMS integration for the exact panel and device tree.

Do not opportunistically port or enable a new display driver in this task.

Keep PWNAGE-55000 focused on WebKit's missing DMA-BUF transport and the necessary kernel support.

---

# 14. Build and pre-flash validation gates

The agent must pass these gates before using TWRP to write the device.

## Gate A — Source and configuration

- [ ] Exact active Linux source identified.
- [ ] Exact running config captured.
- [ ] Existing config backed up.
- [ ] `CONFIG_DRM_VGEM` exists in the exact source.
- [ ] Dependencies understood.
- [ ] VGEM implementation audited.
- [ ] Candidate configuration diff is minimal.
- [ ] `CONFIG_MODVERSIONS=y` preserved.
- [ ] Mali kbase ABI impact understood.

## Gate B — Kernel build

- [ ] Kernel build succeeds.
- [ ] VGEM is built in if selected.
- [ ] Expected kernel image exists.
- [ ] Expected kernel configuration is embedded or otherwise verifiable.
- [ ] `Module.symvers` generated.
- [ ] Required modules built from the exact output.
- [ ] No module ABI mismatch.
- [ ] DTB is present.
- [ ] Ramdisk is compatible.
- [ ] Kernel command line is preserved.
- [ ] Build artifact hash recorded.

## Gate C — Boot artifact

- [ ] Correct Android boot image format.
- [ ] Correct header version.
- [ ] Correct page size.
- [ ] Correct kernel compression.
- [ ] Correct addresses and metadata.
- [ ] Correct DTB/DTBO handling.
- [ ] Correct initramfs.
- [ ] No accidental recovery image.
- [ ] Image can be unpacked and inspected.
- [ ] Rebuilt artifact matches expected contents.

## Gate D — Recovery and rollback

- [ ] TWRP detected.
- [ ] Correct physical device identified.
- [ ] USB transport stable.
- [ ] Partition map verified.
- [ ] Exact write target verified.
- [ ] Existing boot image backed up off-device.
- [ ] SHA-256 verified.
- [ ] TWRP partition protected.
- [ ] Restore procedure prepared.
- [ ] No unrelated partition write planned.

Only after all four gates pass may the agent perform the authorized flash.

---

# 15. TWRP flash procedure

## 15.1 Confirm the actual recovery environment

Use the connected recovery environment.

Verify device identity and ADB state.

Do not assume the device is in fastboot.

Do not run generic fastboot commands against a Samsung recovery environment that does not expose fastboot.

Confirm that ADB commands are executing inside TWRP.

## 15.2 Identify the kernel-containing partition

Use the current Nuxel installation and the live recovery partition map.

Determine:

- Exact partition name.
- Exact partition block device.
- Partition size.
- Whether the artifact is a complete boot image or a kernel payload.
- How the existing Nuxel installation writes it.
- Whether the device uses slot suffixes.
- Whether the existing boot layout includes the DTB or ramdisk.
- Whether another partition is involved in the actual boot chain.

Do not assume the target is named `boot` without verifying it.

Do not assume `boot_a`/`boot_b` unless the device proves that layout.

Do not guess by matching partition sizes.

## 15.3 Make the backup

Back up the existing target.

Store the backup on the deployment computer.

Verify:

- File exists.
- Expected size is plausible.
- Hash is recorded.
- Backup is readable.
- Restore command/path is ready.

If the backup cannot be verified, stop.

## 15.4 Flash the verified artifact

Use the existing Nuxel/S10+ install or packaging workflow where possible.

Use only the exact verified kernel-containing image.

Do not flash recovery/TWRP.

Do not use a broad installer if the image is intended for only one partition.

Do not erase partitions first.

Do not format userdata.

Do not flash bootloader, modem, EFS or unrelated firmware.

Do not use `dd` against an unverified block device.

If the existing package installs more than the authorized kernel target, inspect and restrict it before proceeding.

## 15.5 Verify the write

After flashing:

- Check the flash operation exit status.
- Read back the affected partition when safely possible.
- Compare the result against the expected artifact.
- Verify that the intended image was written to the intended target.
- Confirm TWRP/recovery remains untouched.
- Confirm no unrelated partition was modified.

## 15.6 Reboot into Nuxel

Once the write is verified:

- Reboot the phone normally into Nuxel.
- Monitor the boot.
- Confirm the device is not stuck in a bootloop.
- Confirm the Nuxel boot process reaches its expected userspace.
- Verify SSH/network availability.
- Verify the running kernel version and configuration.
- Verify Mali kbase.
- Verify Phoc.
- Verify the framebuffer bridge.

Do not immediately run the full acceleration stress tests before proving the base OS is stable.

---

# 16. Recovery if Nuxel fails to boot

A failed boot is not permission to repeatedly flash variations of the same image.

Use the prepared recovery route.

## 16.1 Re-enter TWRP

If the phone hangs or bootloops:

1. Return to TWRP using the device's established recovery key sequence.
2. Reconnect USB.
3. Verify ADB recovery state.
4. Preserve available logs.
5. Do not erase userdata.
6. Do not flash a second experimental image.

## 16.2 Collect evidence

Where available, collect:

- TWRP logs.
- `pstore`.
- `ramoops`.
- Kernel console output.
- `last_kmsg`.
- Boot reason.
- Partition readback.
- Failed artifact hash.
- Current boot image.
- Relevant device properties.

Compare these with the previous known-good state.

## 16.3 Restore the known-good boot image

Use the pre-verified backup.

Restore only the original kernel-containing target.

Do not overwrite TWRP.

Verify the restore.

Reboot into the previous known-good Nuxel image.

The objective is to recover the device, not to continue experimenting while it is in an unstable state.

## 16.4 Explain the failure

The agent must record:

- What failed.
- At which boot stage.
- Whether the kernel started.
- Whether the ramdisk/init path started.
- Whether a DTB or partition mismatch occurred.
- Whether a module ABI problem occurred.
- Whether the boot artifact was malformed.
- Which change caused the failure.
- What must be corrected before another authorized flash.

Do not declare the issue fixed until the cause is understood.

---

# 17. Post-boot kernel verification

After the successful Nuxel boot, verify that the phone is running the intended kernel.

Collect:

```bash
uname -a
cat /proc/version
```

Inspect the actual running configuration.

Verify:

```text
CONFIG_DRM=y
CONFIG_DRM_VGEM=y
CONFIG_MODVERSIONS=y
```

Only report the settings that are actually present.

Check:

- DRM core initialized.
- VGEM registered.
- `/dev/dri` created.
- DRM primary node.
- DRM render node.
- Driver names.
- Device permissions.
- DRM capabilities.
- PRIME import/export support.
- Kernel logs.
- No unexpected KMS driver.
- No Mali regression.

If a configuration value is absent or differs from the build artifact, investigate whether the wrong image booted.

Do not assume that the newly built kernel is running merely because the flash operation reported success.

---

# 18. Post-boot VGEM verification

Verify the actual VGEM instance.

Expected characteristics:

- Driver identifies as `vgem`.
- DRM node is registered by the kernel driver.
- Render-node capability is real.
- PRIME support is present where implemented.
- The node can be opened by the intended service/user.
- GBM can initialize it where supported.

Record actual paths rather than assuming:

```text
/dev/dri/card0
/dev/dri/renderD128
```

Inspect sysfs and DRM capability information.

Do not create symlinks.

Do not rename the node to `mali`.

Do not make a udev rule that disguises VGEM as a physical GPU.

The actual driver must remain identifiable.

---

# 19. WebKit verification after the kernel change

This is the principal functional acceptance stage.

## 19.1 WebKit runtime evidence

Run the same WebKit test workload that generated the prior 186 Mali job submissions in three seconds.

Collect:

- WebKit version.
- Process IDs.
- Web process environment.
- UI process environment.
- EGL vendor/version.
- EGL extensions.
- DRM main device.
- GBM device.
- Renderer buffer transport mode.
- Buffer format.
- Modifier.
- FD counts.
- Import results.
- Errors.
- Fallback selection.

## 19.2 Prove Hardware transport

The test must demonstrate that Hardware DMA-BUF transport is selected.

A message such as:

```text
Hardware acceleration enabled
```

is not sufficient.

The test must demonstrate:

1. GPU renderer produces buffer.
2. Producer exports DMA-BUF FD.
3. FD crosses process boundary.
4. UI process receives that FD.
5. GBM imports it.
6. Buffer can be used by GTK/WebKit.
7. Correct pixels are displayed.
8. The SHM fallback is not being used for the same backing-store frames.

## 19.3 FD count

The previous report showed:

```text
0 udmabuf/dmabuf FDs
```

The new test must record actual FD production and consumption.

Do not merely count open descriptors whose names contain `dmabuf`.

Verify the nature and ownership of the descriptor.

Where possible, identify:

- DMA-BUF FD.
- Exporter.
- Importer.
- Backing storage.
- Size.
- Format.
- Dimensions.
- Stride.
- Modifier.
- Lifetime.
- Synchronization behavior.

A random FD number or an opened DRM node is not proof of buffer export.

## 19.4 Correct fallback behavior

If Hardware transport remains unavailable:

- Preserve the known-working SHM fallback.
- Record the exact reason.
- Identify whether failure occurred at device discovery, EGL capability, allocation, export, transfer, import or presentation.
- Do not disable normal WebKit rendering.
- Do not show a false green result.

A failed experimental import must not crash the web process or Phoc.

---

# 20. Phoc import and malformed-buffer tests

The existing test is:

```text
Phoc import of linear DMA-BUF: 20/20
Malformed metadata: no Phoc crash
```

Repeat this after the kernel change.

Use the actual formats the current Mali and compositor stack supports:

- AB24.
- XB24.
- AR24.
- XR24.

Initially restrict to LINEAR modifier.

Test:

- Valid import.
- Repeated import.
- Reuse.
- Release.
- Invalid FD.
- Truncated metadata.
- Incorrect dimensions.
- Incorrect stride.
- Incorrect format.
- Unsupported modifier.
- Premature FD close.
- Invalid synchronization.
- Rapid buffer replacement.

Phoc must remain alive.

The framebuffer bridge must keep presenting valid frames.

Malformed metadata must fail safely.

Do not enable unsupported tiling modifiers just to improve a benchmark.

---

# 21. Preserve and retest the framebuffer bridge

The current final presentation path still includes a CPU copy/scale step.

The target must preserve:

```text
Phoc
  → Wayland screencopy
  → nuxel-wl-fb
  → /dev/fb0
  → DECON
```

Verify:

- One `/dev/fb0` writer.
- `FRAMES_OK`.
- `decon_pan_failed=0`.
- No new framebuffer errors.
- Correct 1440×6080 virtual state or verified current geometry.
- Correct physical panel image.
- No tearing or corruption.
- Correct buffer size.
- Correct stride.
- Correct damage handling.
- Correct recovery after WebKit restarts.

Do not introduce a second framebuffer presentation process.

Do not start a new DRM/KMS compositor.

Do not route physical scanout through VGEM.

---

# 22. Performance measurement

Collect measurements before and after the kernel change using the same workload.

At minimum measure:

| Metric | Before | After |
|---|---:|---:|
| Mali GPU job submissions | 186 / 3 s baseline | Measure |
| WebKit transport mode | SHM | Measure |
| DMA-BUF FDs exported | 0 baseline | Measure |
| DMA-BUF FDs imported | 0 baseline | Measure |
| GBM import success | Blocked | Measure |
| Phoc linear import | 20/20 baseline | Measure |
| Framebuffer copy/scale | 20–38 ms baseline | Measure |
| Frame presentation rate | Measure | Measure |
| CPU load during scroll | Measure | Measure |
| GPU load during scroll | Measure | Measure |
| Memory bandwidth/load | Measure | Measure |

Use an identical test page, dimensions, animation, scroll workload and duration.

Test:

- Scrolling.
- CSS transforms.
- Large image content.
- Canvas.
- Video where already supported.
- Multiple windows.
- Application switching.

Do not infer performance improvements from a log message alone.

The final physical framebuffer copy must be measured separately from WebKit's renderer-to-UI transport.

---

# 23. Acceleration profiles

Keep the profiles truthful.

The existing profile names include:

- `gpu-rendered-dmabuf-presented`
- `fully-accelerated`

Inspect the exact existing profile definitions and their capability gates.

Do not delete or weaken existing checks.

## 23.1 GPU-rendered

May report PASS when:

- WebKit renderer performs GPU work on Mali.
- No llvmpipe is used.
- GPU execution evidence is present.

This stage already passes on the current physical device.

## 23.2 GPU-rendered DMA-BUF presented

May report PASS only when:

- WebKit uses Hardware DMA-BUF transport.
- Real DMA-BUFs are exported.
- The GTK/UI process receives them.
- GBM imports succeed.
- Correct content reaches the compositor.
- SHM is not the active WebKit backing-store fallback.

Do not mark this profile available merely because `/dev/dri` exists.

## 23.3 Fully accelerated

Only report full end-to-end acceleration if every required stage is actually accelerated, including physical display handoff.

If the final `/dev/fb0` copy remains CPU-based, the report must say so.

Do not label a pipeline fully zero-copy while the framebuffer bridge still copies and scales the image in CPU memory.

If the WebKit DMA-BUF path passes while the physical framebuffer copy remains, expose that intermediate result accurately and leave the strict full-acceleration profile unavailable.

A later direct-scanout/DMA-engine project may be necessary.

---

# 24. Build integration and reproducibility

The kernel config change must survive the normal Nuxel build system.

Identify the actual source of truth for:

- S10+ defconfig.
- Config fragments.
- Kernel build script.
- Device image builder.
- Kernel image packaging.
- TWRP installation package.
- Release build.

Do not make a manual `.config` modification that disappears during the next build.

Add the minimal config change to the correct tracked source.

Record:

- Exact config diff.
- Exact source commit.
- Toolchain version.
- Build command.
- Output filenames.
- Image hashes.
- Module hashes.
- Module `vermagic`.
- `Module.symvers` hash.
- Boot image hash.
- Flash target.

The build must be reproducible.

A future Nuxel build must not silently remove VGEM again.

---

# 25. Documentation

Update the existing GPU acceleration documentation and device build documentation.

Include:

- Previous working GPU state.
- The identified kernel blocker.
- The selected kernel option(s).
- Why built-in VGEM was selected or rejected.
- Exact kernel ABI considerations.
- Actual DRM nodes.
- Actual driver names.
- Actual WebKit transport mode.
- Actual DMA-BUF producer.
- Actual DMA-BUF importer.
- Exact formats and modifiers.
- Synchronization behavior.
- Fallback behavior.
- TWRP flash record.
- Boot validation.
- Rollback details.
- Performance before/after.

Update the acceleration profile documentation to distinguish:

- GPU render.
- WebKit DMA-BUF handoff.
- GBM import.
- Phoc import.
- Physical framebuffer presentation.

Do not update a capability to PASS without its supporting evidence.

---

# 26. Final acceptance matrix

| Requirement | PASS condition |
|---|---|
| Source integrity | Exact active 4.14.253 source/config identified |
| VGEM build | Native driver builds successfully |
| ABI integrity | No unsafe module loading; correct Module.symvers |
| Boot artifact | Correct complete image and DTB/ramdisk packaging |
| TWRP backup | Known-good boot image backed up off-device and hashed |
| TWRP integrity | Recovery remains intact |
| Flash | Only verified kernel-containing target written |
| Boot | Phone boots successfully into Nuxel |
| Mali | kbase remains operational |
| Phoc | Continues rendering on Mali |
| EGL | Existing surfaceless and Wayland tests pass |
| DRM | Real kernel DRM node appears |
| VGEM | Correctly identified as a virtual GEM provider |
| PRIME | Actual relevant import/export interfaces work |
| WebKit discovery | `drmMainDevice()` is valid |
| GBM | Correct device initializes |
| WebKit producer | Real DMA-BUF FD exported |
| WebKit transfer | FD crosses renderer/UI process boundary |
| WebKit importer | GBM import succeeds |
| WebKit transport | Hardware selected, SHM not silently active |
| Phoc | Linear DMA-BUF import remains stable |
| Display | `FRAMES_OK`, no DECON errors |
| Framebuffer | Exactly one `/dev/fb0` writer |
| Profiles | Capability labels match real behavior |
| Performance | Before/after measurements recorded |
| Recovery | Known-good image and restore route proven |

---

# 27. Mandatory stop conditions

Stop before flashing if:

- The exact kernel source cannot be established.
- The active kernel configuration cannot be recovered.
- The source does not contain a compatible VGEM implementation.
- The required dependency would introduce an unacceptable ABI break.
- Mali kbase compatibility cannot be established.
- The correct boot image format is unknown.
- The previous failed image's packaging problem remains unresolved.
- The exact boot target cannot be identified.
- The TWRP device identity is ambiguous.
- A verified backup cannot be created.
- The rollback route is not available.

Stop the acceleration claim if:

- DRM device discovery succeeds but GBM cannot initialize.
- Hardware transport is selected but no real FD is exported.
- FDs are exported but the UI process cannot import them.
- Import works only for a test program but not WebKit.
- WebKit continues to use SHM.
- The physical display path becomes unstable.
- Mali starts falling back to software rendering.

Do not hide a failed gate by weakening the acceptance test.

---

# 28. Expected final report

Return a concise executive summary followed by detailed evidence.

## 28.1 What changed

- Kernel source commit.
- Kernel configuration changes.
- Files modified.
- Build artifacts.
- Module rebuilds.
- Packaging changes.
- Userspace changes, if any.

## 28.2 TWRP flash record

Include:

- Detected device identity.
- Recovery state.
- ADB status.
- Boot target partition.
- Backup path.
- Backup SHA-256.
- New image SHA-256.
- Flash command/tool.
- Write result.
- Readback verification.
- Reboot result.
- TWRP preservation check.

Do not include sensitive credentials.

## 28.3 Boot result

Include:

- Running kernel version.
- Running configuration proof.
- Mali kbase status.
- Phoc status.
- EGL status.
- DRM/VGEM status.
- Module ABI status.
- Framebuffer status.

## 28.4 WebKit result

Include:

- `drmMainDevice()` result.
- DRM primary/render node.
- Driver identity.
- GBM initialization.
- EGL extensions.
- WebKit transport mode.
- DMA-BUF export count.
- DMA-BUF import count.
- Supported formats/modifiers.
- Fallback status.
- Actual presentation result.

## 28.5 Performance result

Include before/after:

- GPU activity.
- CPU use.
- FD counts.
- Import time.
- Presentation time.
- Frame rate.
- Framebuffer copy/scale cost.

## 28.6 Remaining blockers

State clearly whether the remaining issue is:

- Missing kernel DRM/VGEM.
- Missing Mali DMA-BUF export.
- GBM device selection.
- WebKit build configuration.
- DMA-BUF synchronization.
- Phoc import compatibility.
- Physical framebuffer CPU copy.
- Actual display-controller scanout limitations.

Do not group these into one generic "GPU acceleration" status.

---

# 29. Reference material

Use these as starting points, then verify against the exact target source and installed binaries.

- Linux 4.14 DRM memory management and PRIME documentation:  
  https://www.kernel.org/doc/html/v4.14/gpu/drm-mm.html

- Linux kernel VGEM source:  
  https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/%2B/63fc9c23488d6cf34e4c233e24ba59b7e5548412/drivers/gpu/drm/vgem/vgem_drv.c

- `CONFIG_DRM_VGEM` configuration history and dependencies:  
  https://cateee.net/lkddb/web-lkddb/DRM_VGEM.html

- `CONFIG_UDMABUF` configuration history:  
  https://cateee.net/lkddb/web-lkddb/UDMABUF.html

- Kernel external module and `Module.symvers` documentation:  
  https://docs.kernel.org/kbuild/modules.html

- Android kernel module versioning and ABI documentation:  
  https://source.android.com/docs/core/architecture/kernel/loadable-kernel-modules

- WebKit GTK graphics documentation:  
  https://docs.webkit.org/Ports/WebKitGTK%20and%20WPE%20WebKit/Graphics.html

- WebKitGTK 2.54.1 release:  
  https://webkitgtk.org/2026/10/02/webkitgtk2.54.1-released.html

- WebKit GTK accelerated backing-store source:  
  https://fossies.org/linux/www/webkitgtk-2.53.90.tar.xz/webkitgtk-2.53.90/Source/WebKit/UIProcess/gtk/AcceleratedBackingStore.cpp

The target tree and installed WebKit build remain authoritative over external reference versions.

---

# 30. Final instructions

This is a targeted kernel integration and deployment task.

Do not redesign Nuxel.

Do not replace Mali kbase.

Do not migrate to a different kernel.

Do not build an unrelated DRM/KMS display stack.

Do not create a fake Mali render node.

Do not disable `CONFIG_MODVERSIONS`.

Do not force-load an ABI-unsafe module.

Do not repeat an unexplained failed boot image.

Do not overwrite TWRP.

Do not flash unrelated partitions.

The owner has explicitly authorized the TWRP-based kernel operation under the agreement in Section 4.

The agent is expected to perform the complete source inspection, kernel build, pre-flash validation, verified backup, targeted flash, reboot into Nuxel and post-boot acceleration tests during the authorized session.

**First recover the exact current kernel/build/boot arrangement. Then make the minimum proven change. Then flash the verified artifact through TWRP. Then prove the real WebKit DMA-BUF handoff.**

The goal is not a `/dev/dri` directory.

The goal is an actually working Mali-rendered WebKit DMA-BUF presentation path on the physical S10+, without losing the stable Nuxel system already working underneath it.
