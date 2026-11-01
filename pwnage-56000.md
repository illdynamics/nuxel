# PWNAGE-56000 — Finish Nuxel Flatpak Integration
## User namespaces, Bubblewrap, ARM64 applications, portals, NuXtore and TWRP-authorized kernel recovery

**Device:** Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820
**OS:** Nuxel, Fedora-based ARM64
**Kernel:** Inspect actual running/build kernel; previous baseline was downstream Linux 4.14.253
**Priority:** High
**Deployment starting state:** PHONE ALREADY IN TWRP RECOVERY, USB CONNECTED
**Kernel target:** `CONFIG_USER_NS=y`
**Flash authorization:** Explicitly granted within the TWRP agreement below

## Mission

Complete Flatpak integration throughout Nuxel so compatible ARM64 applications install, launch, use the intended sandbox, integrate with the Phoc desktop and appear correctly in NuXtore and the native launcher.

The suspected kernel blocker is:

```text
# CONFIG_USER_NS is not set
```

The required final kernel configuration is:

```text
CONFIG_NAMESPACES=y
CONFIG_USER_NS=y
CONFIG_PID_NS=y
```

Verify the actual source tree and dependencies. Preserve other working kernel options, including any proven Mali, DRM/VGEM and display support.

### Critical recovery context — read first

The previous kernel/boot deployment attempt caused Nuxel to bootloop or hang after reboot. This is an unresolved failure, not a successful deployment.

The owner will start this prompt with the physical phone already booted into TWRP recovery and connected to the computer over USB.

**The first task is recovery and diagnosis, not another flash.**

The agent must:

1. Confirm TWRP is actually running and responsive over ADB.
2. Confirm the target is the S10+ `beyond2lte`.
3. Establish whether the previous failure was caused by the Nuxel boot image, kernel, DTB, ramdisk, command line, packaging, partition selection or another boot dependency.
4. Preserve the currently flashed image for forensic analysis.
5. Locate and verify a known-good boot image or build a corrected image from the exact known-good source baseline.
6. Prepare and verify a rollback route before writing.
7. Fix the boot failure before considering the deployment complete.

Do not assume that TWRP itself is bootlooping. Determine separately whether recovery is healthy and whether the Nuxel boot target is failing.

If TWRP is not responsive, ADB does not identify the device, or the device identity is ambiguous, stop before writing anything.

## Phase 1 — TWRP recovery handshake

The owner explicitly provides authorization for a targeted kernel-containing image repair and flash.

Start with the phone already connected in TWRP.

Verify:

- ADB detects the device in recovery state.
- TWRP responds to commands.
- Device identity is `beyond2lte` / SM-G975F / Exynos 9820.
- USB connection is stable.
- Battery/power state is adequate.
- Actual partition layout is inspected.
- Exact kernel-containing target is identified.
- TWRP/recovery partition is identified and protected.

Do not assume fastboot exists on this Samsung recovery setup.

Do not guess partition names such as `boot`, `boot_a` or `boot_b`. Discover the actual layout.

### Backup and evidence

Before flashing:

- Read and preserve the currently flashed kernel-containing image.
- Preserve the previously failed image for forensic comparison.
- Copy backups off-device.
- Verify file sizes and SHA-256 hashes.
- Record partition names, sizes and paths.
- Locate the previous known-good image.
- Verify that the known-good image is readable and appropriate for this device.
- Record a tested restore procedure.

Do not wipe userdata. Do not format partitions. Do not overwrite TWRP, bootloader, modem, EFS or unrelated partitions.

## Phase 2 — Diagnose the previous bootloop/hang

Inspect available:

- Previous kernel build artifacts.
- Boot image packaging commands.
- Installer scripts.
- TWRP logs.
- `pstore` and `ramoops`, where available.
- `last_kmsg`, where available.
- Kernel logs and boot diagnostics.
- Previous device debug packs.
- Current partition contents.
- Known-good and failed image contents.

Compare the failed and known-good images:

- Android boot image header/version.
- Page size.
- Kernel payload and compression.
- Ramdisk.
- DTB/DTBO placement.
- Load addresses.
- Kernel command line.
- Header metadata.
- Board identity.
- Image size and alignment.
- Partition target.
- Installer behavior.

Identify the cause of the previous hang/bootloop. Do not repeat an unexplained packaging or flashing procedure.

## Phase 3 — Verify the actual namespace blocker

Inspect the running kernel configuration, not merely a source defconfig.

Required final settings:

```text
CONFIG_NAMESPACES=y
CONFIG_USER_NS=y
CONFIG_PID_NS=y
```

Check the exact Linux source tree's `init/Kconfig` and namespace dependencies.

Inspect `CONFIG_MEMCG`; kernel guidance recommends memory cgroup support when enabling user namespaces, provided it is compatible with this Nuxel kernel and cgroup setup.

As the ordinary Nuxel user, test:

```bash
unshare --user true
```

Also test the supported `--map-root-user` form if the installed util-linux provides it.

Inspect runtime controls that actually exist:

```bash
for f in \
  /proc/sys/user/max_user_namespaces \
  /proc/sys/user/max_mnt_namespaces \
  /proc/sys/kernel/unprivileged_userns_clone
do
    if [ -r "$f" ]; then
        printf '%s=' "$f"
        cat "$f"
    fi
done
```

A zero namespace limit or a distribution-specific restriction can block unprivileged namespaces even when the kernel supports them. Only configure `kernel.unprivileged_userns_clone` if this kernel really exposes it.

If `CONFIG_USER_NS=n`, rebuild the kernel. A sysctl cannot enable a feature compiled out of the kernel.

If it is already `y`, fix the actual runtime restriction instead of reflashing unnecessarily.

## Phase 4 — Kernel rebuild if required

Use the exact current Nuxel S10+ source, toolchain, defconfig, config fragments and image builder.

Do not upgrade the kernel family or revert to an older saved configuration.

Set and verify:

```text
CONFIG_NAMESPACES=y
CONFIG_USER_NS=y
CONFIG_PID_NS=y
```

Preserve:

```text
CONFIG_MODVERSIONS=y
```

Also preserve all proven kernel features currently required by Nuxel, including:

- Mali kbase.
- Existing EGL/Wayland functionality.
- DRM/VGEM configuration if deployed and verified.
- DMA-BUF support.
- Existing framebuffer/DECON path.
- Device-tree and ramdisk integration.
- Existing input, audio, Wi-Fi and other required modules.

Build external modules against the exact new kernel output and matching `Module.symvers`. Do not force-load ABI-incompatible modules.

Do not create a `userns.ko`; `CONFIG_USER_NS` is a built-in kernel feature.

## Phase 5 — Repack and verify the boot image

Use the proven Nuxel S10+ image-packaging workflow.

Before any write, verify:

- Kernel architecture.
- Kernel image.
- Exact configuration.
- Boot header.
- DTB/DTBO.
- Ramdisk.
- Kernel command line.
- Compression and alignment.
- Board compatibility.
- Correct target partition.
- Build artifact SHA-256.
- Known-good rollback image.
- No recovery/TWRP overwrite.

Do not use an unverified generic `mkbootimg` command or broad installer.

## Phase 6 — Authorized TWRP flash and reboot

Once recovery, source, image, target, backup and rollback gates have passed, the owner authorizes the agent to:

1. Flash the corrected kernel-containing image to the verified target only.
2. Verify the write and readback where safe.
3. Confirm TWRP remains intact.
4. Reboot normally into Nuxel.
5. Monitor boot and verify the new kernel is actually running.

If Nuxel hangs or bootloops again:

- Return to TWRP.
- Preserve logs and the failed image.
- Do not wipe userdata.
- Restore the known-good image using the verified rollback route.
- Explain the new failure before trying again.

Do not repeatedly flash experimental images.

## Phase 7 — Bubblewrap and Flatpak

The preferred mode is unprivileged Bubblewrap.

Verify the actual executable used by Flatpak; it may be `/usr/bin/bwrap` or a Flatpak-specific helper.

Check owner, group, permissions, setuid/setgid bits, file capabilities, version and SELinux label.

Preferred unprivileged mode:

```text
root:root
0755
not setuid
```

Test Bubblewrap as the ordinary desktop user. It must create the user and mount namespaces required by Flatpak without `sudo`.

Do not use setuid Bubblewrap or privileged launchers as the default workaround. The Flatpak maintainers document limitations in the setuid fallback, including features needed by some Chromium and Steam use cases.

Verify:

- Flatpak package and version.
- Bubblewrap package and version.
- OSTree.
- D-Bus proxy.
- Flathub remote.
- Correct ARM64 architecture.
- Runtime refs.
- User/system installation consistency.
- Storage availability.
- Install, update, repair, uninstall and launch.

Never assume a Flathub listing means an `aarch64` app/runtime exists. Check real refs and dependencies.

## Phase 8 — Portals and Phoc integration

Complete the XDG Desktop Portal frontend/backend configuration for Nuxel/Phoc.

Inspect available ARM64 packages and select only suitable backends. Do not install a full GNOME or KDE desktop merely to obtain portals.

Verify:

- `xdg-desktop-portal`.
- Suitable GTK and/or wlroots backend, if compatible.
- User D-Bus session activation.
- `XDG_CURRENT_DESKTOP`.
- `WAYLAND_DISPLAY`.
- `XDG_RUNTIME_DIR`.
- FileChooser.
- OpenURI.
- Settings.
- Notifications.
- Screenshot and ScreenCast only where actually supported.

A portal service that starts but returns errors is not working.

## Phase 9 — NuXtore and native launcher

Complete Flatpak discovery and lifecycle integration.

NuXtore must:

- Discover installed Flatpak applications from the intended installation scopes.
- Discover compatible ARM64 catalog entries.
- Show app name, ID, icon, description, runtime, version, architecture and installation state.
- Install with progress.
- Launch using the correct app ID.
- Update apps and runtimes.
- Uninstall cleanly.
- Refresh application discovery.
- Remove stale launcher entries.
- Prevent duplicate app entries.
- Report failures clearly.

Use safe argument arrays or a proper Flatpak API. Do not build shell commands from untrusted UI strings.

Flatpak apps must appear in the normal Nuxel launcher beside native applications.

## Phase 10 — Real application testing

Discover currently available AArch64 refs before selecting test apps.

Test at least:

- One GTK app with a file chooser.
- One browser or browser-like app, if ARM64 compatible.
- One media/audio app, if compatible.
- One additional lightweight GUI application.

For each app verify:

- Install.
- Launch as ordinary user.
- Wayland connection to Phoc.
- File chooser portal.
- Audio, where relevant.
- URI opening.
- Display scaling and touch usability.
- Close and relaunch.
- Update.
- Uninstall.
- Reboot persistence.

Report GPU acceleration separately from sandbox success. Do not assume the host's custom Mali stack is automatically available inside Flatpak runtimes.

## Mandatory acceptance

- [ ] Prompt starts with device in TWRP over USB.
- [ ] TWRP/ADB handshake is verified.
- [ ] Previous bootloop/hang is investigated.
- [ ] Failed and known-good images are compared.
- [ ] Known-good rollback image is backed up and hashed.
- [ ] Correct boot target is identified.
- [ ] TWRP/recovery is preserved.
- [ ] Running kernel has `CONFIG_USER_NS=y`.
- [ ] Normal user can create user namespaces.
- [ ] Bubblewrap works without sudo and is not setuid.
- [ ] Compatible ARM64 Flatpak installs and launches.
- [ ] Portals work in the Phoc session.
- [ ] NuXtore discovers and launches installed apps.
- [ ] Updates and uninstall work.
- [ ] Reboot persistence works.
- [ ] Existing Mali/Phoc/framebuffer functionality remains intact.
- [ ] TWRP rollback route remains available.

## Deliverables

1. Root-cause report for the previous bootloop/hang.
2. TWRP recovery and device-identification record.
3. Current and failed boot image hashes.
4. Known-good backup and restore instructions.
5. Kernel config diff and build artifact, if needed.
6. Flash and reboot evidence.
7. Namespace and Bubblewrap test results.
8. Flatpak/portal/NuXtore source changes.
9. ARM64 application compatibility matrix.
10. Full userspace deployment and rollback instructions.

**Definition of done:** The S10+ boots reliably into Nuxel, unprivileged Flatpak sandboxing works with `CONFIG_USER_NS=y`, and supported ARM64 Flatpak applications are properly integrated into NuXtore and the native Nuxel desktop.
