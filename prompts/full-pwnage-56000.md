# FULL PWNAGE-56000 — Complete Nuxel Flatpak Integration
## Repair the previous TWRP boot failure, enable USER_NS, rebuild and safely flash the kernel, finish Bubblewrap, portals, NuXtore and ARM64 application integration

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Device:** Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820  
**OS:** Fedora-based Nuxel ARM64  
**Userspace baseline:** Fedora 43 / systemd 258.11 — verify actual installed versions  
**Known previous kernel baseline:** Downstream Linux 4.14.253 — verify current source and running kernel  
**Priority:** High  
**Deployment starting state:** PHONE ALREADY IN TWRP RECOVERY, CONNECTED OVER USB  
**Required final kernel configuration:** `CONFIG_USER_NS=y`  
**Kernel flash:** Explicitly authorized under Section 3  
**Main objective:** Reliable Flatpak sandboxing and complete native Nuxel desktop integration.

---

# 0. Mission

Finish Flatpak integration throughout Nuxel.

This is a combined recovery, kernel configuration, deployment and userspace integration task.

The phone must boot reliably into Nuxel, support unprivileged user namespaces, run Bubblewrap correctly and provide a complete Flatpak application experience through NuXtore and the native launcher.

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

Verify those symbols in the exact target kernel source and the running device configuration. Preserve all other required kernel options.

The task includes a previous deployment failure that must be repaired.

**The owner will start this task with the phone already in TWRP recovery, connected to the computer over USB.**

The previous kernel/boot deployment resulted in Nuxel bootlooping or hanging after reboot. This is an unresolved issue and must be investigated before another flash.

Do not treat the previous attempt as a successful kernel deployment.

Do not repeat the same build, repackaging or flash procedure blindly.

Do not assume TWRP itself is defective. First establish that recovery is responsive and then determine whether the previous failure affected the Nuxel boot image, DTB, ramdisk, kernel, command line, partition target or another component.

The final outcome must be:

- TWRP remains accessible.
- Nuxel boots reliably.
- The final running kernel has `CONFIG_USER_NS=y`.
- Unprivileged namespace creation works for the normal Nuxel user.
- Bubblewrap works without sudo and without a setuid workaround.
- Compatible ARM64 Flatpak applications install and launch.
- Portals work in the actual Phoc session.
- NuXtore discovers and manages applications.
- Applications appear in the native Nuxel launcher.
- Updates and uninstall work.
- Existing Nuxel graphics, audio, network and display functionality remains intact.

---

# 1. Non-negotiable operating rules

1. Start with the device already in TWRP recovery over USB.
2. Verify the actual recovery state before executing commands that could write to the device.
3. Diagnose the previous bootloop/hang before another flash.
4. Preserve the currently flashed image for forensic analysis.
5. Establish a known-good recovery/boot image and a verified rollback procedure.
6. Use the exact Nuxel S10+ kernel source and build system.
7. Preserve existing proven GPU/DRM/display kernel features.
8. Enable `CONFIG_USER_NS=y` in the tracked kernel configuration.
9. Keep `CONFIG_MODVERSIONS=y` unless there is a separately proven reason not to; there is no reason to disable it for this task.
10. Build the correct complete boot artifact.
11. Flash only the verified kernel-containing target.
12. Do not overwrite TWRP/recovery.
13. Do not wipe or format userdata.
14. Reboot into Nuxel and verify the actual running kernel.
15. Complete the full Flatpak userspace integration.
16. Do not claim success based on package installation alone.
17. Do not bypass sandboxing to make applications appear to work.

---

# 2. Initial operating condition — device is already in TWRP

This section is the first action.

The owner will prepare the phone before starting the agent:

- Phone powered into TWRP recovery.
- USB cable connected to the deployment computer.
- TWRP visible and available.
- Phone left connected throughout the recovery, backup, flash and initial reboot procedure.

The agent must not ask the owner to reboot into TWRP again as an initial step.

The agent must work from the already-running recovery session.

## 2.1 Initial USB/ADB handshake

First enumerate connected USB devices.

Confirm that the expected phone is present.

Verify that ADB sees the device in recovery state.

Determine:

- ADB device identifier.
- Connection state.
- Recovery responsiveness.
- TWRP version.
- Device codename.
- Product/model.
- Board/platform identity.
- Partition map.
- Available storage for diagnostic backups.

Use reliable information from the device itself.

The expected target is:

```text
Device: Samsung Galaxy S10+
Model: SM-G975F
Codename: beyond2lte
SoC: Exynos 9820
Architecture: ARM64
```

Do not trust a single property if other information contradicts it.

Cross-check the device identity against the actual partition layout and known Nuxel build target.

## 2.2 Distinguish recovery health from Android/Nuxel boot health

The previous attempt caused a bootloop or hang after the TWRP deployment/reboot process.

Determine exactly which of these situations applies:

1. TWRP is working, but Nuxel's normal boot image fails.
2. TWRP itself is unstable or cannot remain running.
3. The device cannot reliably enter recovery.
4. TWRP is responsive, but ADB is unavailable.
5. The normal Nuxel boot starts and later hangs.
6. The kernel does not reach the expected init/userspace.
7. The device reboots repeatedly before useful kernel logs are available.

Do not conflate these cases.

The expected starting state for this task is responsive TWRP with USB ADB working.

If the phone does not meet that condition, stop all write operations and identify the recovery transport/recovery failure first.

Do not run another kernel flash against a phone whose recovery state cannot be verified.

---

# 3. TWRP recovery agreement and explicit flash authorization

The owner explicitly authorizes the agent to perform the necessary Nuxel kernel recovery, rebuild and targeted flash.

The authorization is limited to the verified kernel-containing boot artifact/partition required by the existing Nuxel S10+ boot arrangement.

The owner will have the phone already in TWRP with USB connected when this prompt is launched.

## 3.1 Authorized actions

After successful preflight, the agent is authorized to:

- Inspect the running TWRP recovery.
- Inspect the device partition map.
- Read the current kernel-containing boot target.
- Back up the currently flashed image.
- Inspect previous failed images.
- Locate a known-good Nuxel boot image.
- Restore a verified known-good image if required to recover normal boot.
- Build the corrected Nuxel kernel.
- Repackage the appropriate boot artifact.
- Verify the complete image.
- Flash the verified kernel-containing target.
- Reboot into Nuxel.
- Verify the new running kernel.
- Perform the full Flatpak integration work.

The agent must not treat this authorization as permission to flash unrelated partitions.

## 3.2 Explicitly prohibited writes

Do not overwrite or modify:

- TWRP/recovery.
- Bootloader.
- Modem.
- Radio firmware.
- EFS.
- Userdata.
- Unrelated system partitions.
- Unrelated vendor firmware.
- Unrelated device-tree partitions unless the verified existing Nuxel packaging requires them and the owner separately approves that exact change.

Do not:

- Factory-reset.
- Format data.
- Wipe cache as a blind recovery action.
- Unlock or relock the bootloader.
- Change Samsung bootloader state.
- Install an unrelated ROM.
- Run a broad all-partitions firmware package.

## 3.3 Identify the true boot target

Do not assume the target is named `boot`.

Do not assume an A/B slot arrangement.

Do not guess based on partition sizes.

Inspect the actual block-device map and the current Nuxel installation workflow.

Identify:

- Exact partition name.
- Exact block device.
- Partition size.
- Boot image structure.
- Whether the kernel-containing artifact is a complete Android boot image or another supported format.
- DTB/DTBO location.
- Ramdisk arrangement.
- Whether there are slots.
- Whether the established Nuxel installer writes another required component.

The flash target must match the established Nuxel image format.

## 3.4 Preserve TWRP

TWRP is the recovery mechanism for this operation.

Before flashing:

- Identify its partition or recovery placement.
- Prove that the planned operation will not overwrite it.
- Keep it accessible.
- Avoid broad packages that include recovery.
- Verify the recovery partition remains unchanged after deployment.

Do not flash TWRP again as part of this task.

---

# 4. Repair the previous bootloop/hang before building a new result

The previous kernel/boot attempt failed to produce a reliably booting Nuxel system.

This must be investigated as a priority.

Do not treat the current boot image as known-good merely because TWRP can access the device.

## 4.1 Preserve the current failed state

Before replacing anything, preserve:

- Current kernel-containing partition image.
- Current boot artifact where available.
- Previous failed build artifact.
- Previous known-good build artifact.
- TWRP logs.
- Relevant device logs.
- Current partition metadata.
- Current boot target hash.

Copy the current partition image to the host computer.

Calculate SHA-256.

The currently flashed image may be the failed image. Keep it for forensic investigation even if it must eventually be replaced.

## 4.2 Locate the last known-good boot image

Search:

- Repository history.
- Existing release artifacts.
- Device image build directories.
- Previous deployment bundles.
- Existing diagnostic packs.
- Previous TWRP backup directories.
- Host-side archives.
- Previous known-good firmware packages, if they are actually the Nuxel device build.

Identify the last image known to boot Nuxel on this specific device.

Do not choose a generic Exynos9820 kernel.

Do not choose an image merely because its filename contains `beyond2lte`.

Verify its source, build provenance and compatibility.

## 4.3 Recover the failure evidence

Inspect available:

- TWRP logs.
- `pstore`.
- `ramoops`.
- `last_kmsg`.
- Kernel console output.
- Boot reason.
- Reboot reason.
- Init logs, if available.
- Existing Nuxel debug packs.
- Previous deployment output.
- Kernel build logs.
- Image-repacking logs.
- Partition write logs.

Determine where the failure occurs.

Possible failure areas include:

- Invalid boot image header.
- Wrong header version.
- Wrong page size.
- Incorrect compression.
- Missing or misplaced DTB.
- Incorrect ramdisk.
- Wrong load addresses.
- Wrong command line.
- Wrong partition.
- Wrong slot.
- Malformed image padding.
- Incompatible kernel/module combination.
- Incorrect kernel build target.
- Missing Nuxel init dependencies.
- Broken initramfs integration.
- A kernel configuration change that removed required hardware support.

Do not pick one explanation without evidence.

## 4.4 Compare failed and known-good artifacts

Unpack the images with the appropriate tooling and compare:

- Header version.
- Page size.
- Kernel payload.
- Kernel compression.
- DTB content.
- DTB location.
- DTBO integration.
- Ramdisk.
- Ramdisk compression.
- Kernel load address.
- Ramdisk load address.
- Second-stage payload, if present.
- Command line.
- Header metadata.
- Board information.
- Image size.
- Alignment.
- Installer behavior.
- Partition target.

Identify exactly what differed.

If the failure was introduced by the previous repacking procedure, repair that procedure rather than attempting another generic packaging approach.

## 4.5 Restore known-good Nuxel before further experimentation, if needed

If the currently flashed boot target is the failed image and a verified known-good backup is available, restore the known-good target through TWRP if that is the safest way to establish a working Nuxel baseline.

Before restoring:

- Preserve the failed image.
- Verify the known-good image SHA-256.
- Verify the target partition.
- Verify the image format.
- Verify the restore command.
- Verify TWRP remains untouched.

After restoring, reboot into Nuxel only when the restored image is verified.

If no known-good image can be established, do not blindly flash a guessed replacement.

Use the exact repository source and established Nuxel build process to create a recovery image, then validate the complete boot artifact before writing it.

## 4.6 Do not repeat the failure

Before a new flash, the agent must explain:

- What failed previously.
- Which component caused it or what evidence remains inconclusive.
- What has changed in the new build/package process.
- Why the new image is safer.
- How the previous known-good boot can be restored.

The owner must not be left with an unexplained second bootloop.

---

# 5. Establish the exact current Nuxel kernel baseline

Do not assume the currently running device, source archive and build machine all refer to the same kernel.

Inspect the actual repository and device.

## 5.1 Running kernel

Capture:

```bash
uname -a
cat /proc/version
```

Also inspect:

- Kernel version.
- Compiler identity where visible.
- Build date.
- Kernel command line.
- Boot image information.
- Loaded modules.
- Module vermagic.
- Kernel configuration.

Use the actual device values.

## 5.2 Kernel source

Identify:

- Repository URL.
- Branch.
- Exact commit.
- Downstream patches.
- Local uncommitted changes.
- Defconfig.
- Config fragments.
- Toolchain.
- Cross compiler.
- Build system.
- Output directory.
- Image target.
- Module target.
- DTB/DTBO build.
- Initramfs/ramdisk build.
- Boot image packaging.
- TWRP installer/deployment script.

Do not switch to a new kernel family for this task.

Do not opportunistically move from Linux 4.14.253 to a newer kernel.

Do not replace the current Nuxel device port.

## 5.3 Existing acceleration features must survive

The phone has previously demonstrated working graphics functionality.

Preserve any proven changes from previous acceleration work, including where present:

- Mali kbase.
- GPU/EGL support.
- Phoc's Mali rendering path.
- DRM core.
- Native VGEM.
- DMA-BUF support.
- Existing framebuffer/DECON output.
- Required device-tree configuration.
- Existing framebuffer bridge compatibility.
- Module ABI.
- Existing boot and initramfs support.

Do not revert the kernel to an older configuration merely to add USER_NS.

Merge the required namespace setting into the latest intended Nuxel kernel configuration.

If previous GPU changes were never successfully deployed, distinguish intended configuration from verified running behavior.

---

# 6. Kernel configuration — enable USER_NS correctly

## 6.1 Mandatory final setting

The final running kernel must have:

```text
CONFIG_NAMESPACES=y
CONFIG_USER_NS=y
CONFIG_PID_NS=y
```

`CONFIG_USER_NS` is a Boolean kernel option.

It is not a loadable module.

Do not attempt to create a `userns.ko`.

## 6.2 Inspect exact Linux 4.14 source

If the current source is still Linux 4.14.253, inspect its actual:

```text
init/Kconfig
```

Verify how:

- `CONFIG_NAMESPACES`.
- `CONFIG_USER_NS`.
- `CONFIG_PID_NS`.
- `CONFIG_IPC_NS`.
- `CONFIG_NET_NS`.
- `CONFIG_UTS_NS`.

are defined.

Use the exact target source tree as the authority.

Do not assume current upstream dependencies or defaults are identical to the downstream 4.14 tree.

`CONFIG_USER_NS` must be enabled under the namespace configuration.

If `CONFIG_NAMESPACES` is disabled, enable the required parent option and review all resulting configuration changes.

## 6.3 Additional namespace capabilities

Inspect whether the actual Bubblewrap build and Flatpak invocation require additional namespaces.

Evaluate:

```text
CONFIG_IPC_NS
CONFIG_NET_NS
CONFIG_UTS_NS
```

Preserve already-working namespace support.

Do not enable every namespace feature blindly.

The final configuration must support the namespaces actually requested by the installed Bubblewrap version and target applications.

## 6.4 MEMCG

The kernel's user-namespace Kconfig help text recommends enabling memory cgroups and using userspace memory controls to limit memory available to unprivileged users.

Inspect:

```text
CONFIG_MEMCG
```

If enabled already, preserve it.

If disabled, evaluate whether enabling it is safe and compatible with the current Nuxel kernel and cgroup configuration.

Check:

- Kernel dependencies.
- Existing cgroup hierarchy.
- Memory-controller availability.
- systemd compatibility.
- Available physical RAM.
- Current Nuxel memory policy.
- Existing application resource limits.

Prefer enabling MEMCG when it is supported and appropriate.

Do not introduce an unrelated cgroup redesign.

## 6.5 Preserve module ABI

Preserve:

```text
CONFIG_MODVERSIONS=y
```

Build all required modules from the exact matching kernel build environment.

Verify:

- `Module.symvers`.
- Symbol CRCs.
- Module vermagic.
- Mali kbase compatibility.
- Existing required Nuxel modules.
- Any module loaded during early boot.

Do not force-load mismatched modules.

Do not disable module versioning to get an image to boot.

`CONFIG_USER_NS` does not require an out-of-tree module.

## 6.6 Build configuration

Update the correct tracked Nuxel S10+ kernel config source.

Do not only edit a temporary `.config` on the build machine.

Ensure future Nuxel builds retain:

```text
CONFIG_NAMESPACES=y
CONFIG_USER_NS=y
CONFIG_PID_NS=y
```

Review the full config diff after config resolution.

Reject unexplained changes that would remove existing working functionality.

---

# 7. Prove the kernel capability and runtime requirements separately

`CONFIG_USER_NS=y` is necessary for the preferred Flatpak mode, but it is not sufficient by itself.

The system may still restrict namespace creation at runtime.

The Flatpak maintainers document the following requirements for unprivileged Bubblewrap:

- Kernel user namespace support.
- Suitable namespace limits.
- Non-setuid Bubblewrap.
- Enabling a distribution-specific `kernel.unprivileged_userns_clone` control if the kernel has such a patch.

Reference:

https://github.com/flatpak/flatpak/wiki/User-namespace-requirements

## 7.1 Read the running configuration

Use the actual running device config.

Possible sources:

```text
/proc/config.gz
/boot/config-$(uname -r)
```

If neither is available, use the exact config and build metadata associated with the running image.

Do not infer a running config from a local defconfig that may not have been flashed.

## 7.2 Normal-user namespace test

Run as the ordinary Nuxel graphical user.

Do not use root.

Test the supported form of:

```bash
unshare --user true
```

Where available, also test:

```bash
unshare --user --map-root-user true
```

Record:

- Exact command.
- Exit status.
- stderr.
- UID/GID mapping result.
- Whether the test works as normal user.
- Whether it only works as root.

Root-only success does not prove unprivileged Flatpak operation.

## 7.3 Namespace resource limits

Inspect actual runtime files:

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

Do not assume every sysctl exists in this kernel.

The Flatpak documentation mentions namespace limits including:

- `user.max_user_namespaces`.
- `user.max_mnt_namespaces`.

If the second does not exist, do not create a fake setting.

If `kernel.unprivileged_userns_clone` does not exist, do not configure it.

If it does exist and is disabled, determine the exact kernel patch and enable it through a persistent and appropriate mechanism.

## 7.4 Suitable namespace limits

A value of zero blocks namespace creation.

Set limits high enough for the expected Flatpak workload without using arbitrary unlimited values.

Consider:

- Nuxel device RAM.
- Typical number of concurrent applications.
- Browser process counts.
- Nested sandbox needs.
- Number of concurrent user processes.
- Kernel memory overhead.

The Flatpak documentation notes that defaults are commonly in the tens of thousands, depending on available RAM.

Use a sensible value based on actual device capacity and existing Fedora configuration.

## 7.5 Security-policy diagnosis

Inspect:

- systemd service restrictions.
- `RestrictNamespaces=`.
- `SystemCallFilter=`.
- Seccomp.
- SELinux.
- LSM denials.
- AppArmor, if installed.
- BPF LSM, if present.
- Any Nuxel hardening service.
- Per-user/session restrictions.
- D-Bus proxy failures.

Do not disable SELinux or LSM globally.

Do not mask security services.

Fix the specific policy that prevents the expected Bubblewrap operation.

---

# 8. Bubblewrap — preferred unprivileged mode

## 8.1 Identify the actual executable

Flatpak may use:

- System Bubblewrap, commonly `/usr/bin/bwrap`.
- A Flatpak-specific Bubblewrap executable.

Inspect the actual executable used by Flatpak.

Record:

- Path.
- Package/version.
- Owner/group.
- Permissions.
- Setuid/setgid bits.
- File capabilities.
- SELinux label, if applicable.
- How Flatpak selects it.

Do not assume the system `bwrap` executable is the one being invoked.

## 8.2 Required security model

Use unprivileged Bubblewrap.

The expected executable permissions are normally:

```text
-rwxr-xr-x root root
```

That means:

```text
0755
root:root
not setuid
```

Verify the actual implementation and version.

Do not add the setuid bit as a shortcut.

## 8.3 Why not setuid?

The Flatpak-maintained documentation describes setuid Bubblewrap as a fallback with security trade-offs and limitations.

Some features relying on `flatpak-spawn --share-pids` or `--expose-pids` do not work in the fallback mode, including relevant Chromium and Steam use cases.

The Bubblewrap project also documents the importance of user namespaces in its unprivileged sandbox design.

References:

- https://github.com/flatpak/flatpak/wiki/User-namespace-requirements
- https://github.com/containers/bubblewrap

The required Nuxel result is the unprivileged mode.

Do not mark Flatpak complete if the only workaround is to make `bwrap` setuid root.

## 8.4 Bubblewrap functional tests

As the normal desktop user:

1. Check version.
2. Check the actual Flatpak invocation.
3. Create a user namespace.
4. Create a mount namespace.
5. Run a harmless test command.
6. Inspect the namespace mapping.
7. Check filesystem isolation.
8. Check expected read-only mounts.
9. Check writable app directories.
10. Check clean exit and process termination.

Use command syntax supported by the installed version.

Do not copy options from a different Bubblewrap version without checking.

A test that only works under sudo fails acceptance.

---

# 9. Complete Flatpak installation and package integration

## 9.1 Package inventory

Inspect installed versions of:

- Flatpak.
- Bubblewrap.
- OSTree.
- D-Bus proxy.
- XDG Desktop Portal.
- Portal backends.
- GTK/Qt integration libraries.
- Any installed Flatpak graphics runtime integration.

Determine which components are already present.

Do not install duplicates.

Do not install a full desktop environment merely to obtain one missing portal backend.

## 9.2 Architecture

Nuxel is ARM64.

Confirm Flatpak's actual default architecture with the installed version's supported command.

Inspect:

- Default architecture.
- Supported architectures.
- Installed runtimes.
- Remote architectures.
- App refs.
- Runtime refs.
- Extensions.
- Branch compatibility.

The expected native architecture is AArch64.

Do not claim a Flatpak app supports Nuxel simply because its web catalog entry exists.

A compatible application and all required runtimes must actually have the required ARM64 refs.

## 9.3 Flathub remote

Inspect current remotes.

Do not duplicate a working Flathub remote.

If missing, add the correct official remote using the intended system/user installation scope.

Use the official setup instructions:

https://flatpak.org/setup/

Keep installation scope consistent.

Avoid a situation where:

- NuXtore reads system apps.
- Flatpak CLI installs into the user repository.
- The launcher searches only system exports.
- App status appears inconsistent.

Define a clear Nuxel installation policy and use it throughout the app lifecycle.

## 9.4 OSTree and storage

Inspect:

- Repository integrity.
- OSTree refs.
- App installation directories.
- Runtime directories.
- Download cache.
- Available storage.
- Temporary space.
- Per-user repository.
- System repository.

Nuxel has limited mobile storage compared with a desktop workstation.

Show storage requirements before a large runtime download.

Do not run broad destructive cleanup commands.

Do not remove runtimes still used by applications.

Use Flatpak's supported repair and cleanup operations where necessary.

---

# 10. D-Bus and portal integration

Flatpak needs proper desktop portal integration.

This is independent of user namespace support.

A working `bwrap` is not proof that file pickers, notifications or OpenURI work.

## 10.1 Desktop Portal frontend

Verify:

- `xdg-desktop-portal` is installed.
- The user D-Bus session is available.
- The portal frontend activates successfully.
- The portal D-Bus name is registered.
- The frontend can find the appropriate backend.
- The backend can connect to the actual Phoc session.
- User systemd activation works.
- The service starts at the correct session stage.

The portal must not work only when started manually from an SSH shell.

## 10.2 Backend choice

Inspect available Fedora ARM64 packages.

Potential backends include:

- GTK portal backend.
- wlroots-oriented portal backend.

Select only the backend that actually supports Nuxel's Phoc session and the required interfaces.

Do not install GNOME or KDE in full merely to provide portal functionality.

Do not assume every wlroots-oriented backend supports every Phoc protocol or portal interface.

Inspect the actual portal backend descriptors and runtime dependencies.

## 10.3 Desktop identification

Ensure the graphical session provides a consistent desktop identity.

Inspect:

```text
XDG_CURRENT_DESKTOP
XDG_SESSION_TYPE
WAYLAND_DISPLAY
XDG_RUNTIME_DIR
DBUS_SESSION_BUS_ADDRESS
```

Use the actual Nuxel desktop identifier.

Ensure portal configuration matches it.

Do not leave old or conflicting GNOME/KDE environment values that cause incorrect backend selection.

## 10.4 Interface coverage

Implement and test supported interfaces.

| Portal | Required result |
|---|---|
| FileChooser | Opens/saves selected files |
| OpenURI | Requests external URI opening |
| Settings | Provides supported appearance/desktop settings |
| Notification | Displays supported app notifications |
| Screenshot | Works if supported by the actual backend/compositor |
| ScreenCast | Works if supported by the actual backend/compositor |
| Clipboard | Works only where supported by the actual toolkit/backend |
| Print | Only claim support if an actual print path exists |

Do not claim support for an interface merely because the frontend advertises it.

## 10.5 FileChooser acceptance

This is mandatory.

Install a compatible application with a file-open/save operation.

Test:

1. Launch the application as normal user.
2. Trigger file open.
3. Verify the portal request.
4. Verify the correct backend handles it.
5. Select a file.
6. Verify the app receives access to the selected file.
7. Open the file successfully.
8. Verify that unrelated host files remain inaccessible.

Do not solve file chooser problems by granting unrestricted host filesystem access.

---

# 11. Nuxel graphical session integration

Flatpak apps must launch in the actual Nuxel session.

Inspect how the Nuxel launcher starts applications.

Ensure the process receives the correct environment.

Important values include:

```text
XDG_RUNTIME_DIR
WAYLAND_DISPLAY
DBUS_SESSION_BUS_ADDRESS
XDG_SESSION_TYPE
XDG_CURRENT_DESKTOP
HOME
PATH
XDG_DATA_DIRS
```

Do not copy a developer's SSH environment into the GUI session.

Do not start GUI apps from root.

Do not hardcode a GNOME or KDE session.

## 11.1 Wayland

Verify:

- Correct Phoc Wayland socket.
- Correct user permissions.
- Correct runtime directory.
- Wayland protocol compatibility.
- Application startup.
- Window creation.
- Resize.
- Full-screen.
- Input.
- Close.
- Display rotation.

Grant the normal Flatpak Wayland socket access through supported Flatpak permissions.

Do not expose the whole host filesystem just to make the socket visible.

## 11.2 XWayland

If Nuxel has XWayland and an application requires X11, configure it appropriately.

Do not make X11 mandatory for all applications.

Record whether an app uses Wayland or XWayland.

Do not treat X11 socket access as equivalent to the Wayland sandbox model.

## 11.3 Mobile usability

Nuxel is a phone OS.

Test:

- Portrait dimensions.
- Landscape dimensions.
- Application scaling.
- Font scaling.
- Touch targets.
- Soft keyboard.
- Focus handling.
- Navigation.
- App minimize and restore.
- Back navigation where supported.
- Full-screen behavior.
- Dialog size.
- Display cutout/edge behavior.

A technically launched app that is completely unusable on the S10+ is not an integrated application.

Do not globally change scaling in a way that breaks native Nuxel applications.

Use documented per-app settings where needed.

---

# 12. GPU and graphics integration inside Flatpak

Do not assume that Flatpak runtimes inherit the host's custom Mali acceleration.

The host uses a specialized setup:

- Mali-G76 MC12.
- Mali kbase.
- `/dev/mali0`.
- Phoc/Wayland.
- Existing EGL/GLES support.
- Existing framebuffer/DECON presentation.
- Potential DRM/VGEM integration from previous work.

Inspect the actual runtime environment of each test app.

Verify:

- EGL vendor.
- GL renderer.
- GBM device.
- Loaded graphics libraries.
- Device visibility.
- Driver extension compatibility.
- GPU/CPU renderer.
- Whether the app uses software rendering.

Do not grant `--device=all` to every Flatpak application.

Do not expose `/dev/mali0` globally unless the exact host driver/runtime interface is safe and the tested application requires it.

Use narrow app-specific permission grants when justified.

Do not copy host graphics libraries into Flatpak runtimes.

Do not overwrite host Mesa/vendor libraries.

Report software rendering honestly.

A Wayland window is not proof of GPU acceleration.

---

# 13. Audio integration

Inspect the actual Nuxel audio stack.

Determine whether it uses:

- PipeWire.
- PulseAudio.
- PipeWire's PulseAudio-compatible service.
- Another working audio daemon.

Do not install a second audio server unnecessarily.

Verify that Flatpak applications can access the supported audio socket.

Test a compatible media application:

- Audio playback.
- Volume control.
- Mute.
- Pause/resume.
- App backgrounding.
- App exit.
- Relaunch.
- Speaker output.
- Headphones, if available.

Preserve native Nuxel audio.

Do not fix an app's missing audio by granting unrestricted host access.

---

# 14. Security and sandbox isolation

The goal is to make the actual sandbox work, not to disable it.

## 14.1 Avoid blanket permissions

Do not apply unrestricted global access such as:

- Whole-host filesystem access.
- Entire home directory access for every app.
- All device access.
- Unrestricted session D-Bus.
- Broad system-bus access.
- Unrestricted process visibility.
- Host root filesystem access.

Use the permissions declared by each app and user-approved portal access.

## 14.2 Check existing overrides

Inspect system and user Flatpak overrides.

Identify Nuxel development overrides that may have been added to make earlier apps launch.

For every override, determine:

- Why it exists.
- Which app needs it.
- Whether it is still required.
- Whether it weakens sandbox isolation.
- Whether the app works without it.

Remove stale or unjustified development overrides after testing.

Do not remove legitimate permissions without verifying the app.

## 14.3 SELinux/LSM

Preserve the existing security framework.

Inspect actual denials.

Do not disable SELinux globally.

Do not mask LSM services.

Do not allow all sandbox operations just to make one app pass.

Fix the narrow policy issue.

## 14.4 Verify sandbox behavior

For each tested Flatpak application:

- Check process user.
- Check namespace membership.
- Check mount isolation.
- Check visible filesystem.
- Check device access.
- Check D-Bus proxy.
- Check network access as declared by the app.
- Check app exit and process cleanup.

The app must run under the intended sandbox.

---

# 15. Complete NuXtore integration

NuXtore should become the primary Nuxel UI for managing supported Flatpak applications.

Inspect the existing NuXtore implementation and extend it rather than creating an unrelated package manager.

## 15.1 Application discovery

Use Flatpak metadata and supported CLI/API operations to discover apps.

Do not depend only on one hardcoded export directory.

Consider the intended system and per-user installation scopes.

Collect:

- App ID.
- Name.
- Description.
- Version.
- Branch.
- Architecture.
- Runtime.
- Origin.
- Installation scope.
- Installed state.
- Update state.
- Desktop file.
- Icon.
- Permissions.
- Launch reference.

## 15.2 Catalog filtering

The catalog must distinguish:

1. Exists upstream.
2. Has AArch64 application ref.
3. Has AArch64 runtime.
4. Has compatible dependencies.
5. Is installable on the device.
6. Has been tested on Nuxel.
7. Has known Nuxel-specific limitations.

Do not display an x86_64-only app as installable by default.

Do not silently attempt to install unsupported architecture refs.

## 15.3 Install workflow

When the user selects Install:

1. Validate the application ID/ref.
2. Confirm the architecture.
3. Confirm remote.
4. Confirm branch.
5. Resolve runtime.
6. Resolve dependencies.
7. Check storage.
8. Explain additional permissions where relevant.
9. Request authorization for the operation where required.
10. Start the Flatpak transaction.
11. Show progress.
12. Preserve useful error output.
13. Verify installed state.
14. Refresh NuXtore.
15. Refresh the native launcher.

Do not concatenate untrusted UI input into a shell command.

Use safe argument arrays or appropriate Flatpak APIs.

## 15.4 Launch workflow

Launch by app ID/ref using the correct Flatpak launch mechanism.

Do not hardcode runtime paths.

Do not use `sudo`.

Do not invoke a privileged helper to bypass sandboxing.

Capture launch errors and expose them to the UI.

Test the same app through:

- NuXtore.
- Native launcher.

Both paths must work.

## 15.5 Update workflow

NuXtore should:

- Refresh remote metadata.
- Show updates.
- Update individual applications.
- Update selected applications.
- Update runtimes.
- Update extensions.
- Show progress.
- Report failures.
- Verify resulting refs.

Do not remove in-use runtimes.

Do not destructively clean OSTree during ordinary updates.

## 15.6 Uninstall workflow

Support:

- App uninstall.
- Appropriate confirmation.
- User data retention or explicit removal choices.
- Correct installation scope.
- Launcher refresh.
- NuXtore refresh.
- Safe handling of shared runtimes.

Do not delete unrelated user data.

Do not remove shared runtimes still required by other applications.

## 15.7 Duplicate app handling

An application may exist as both a native RPM and Flatpak.

Define deterministic behavior:

- Avoid confusing duplicate entries.
- Identify package source.
- Allow the user to see which is installed.
- Do not replace a native app silently.
- Do not confuse an RPM install with a Flatpak install.

Use the app ID and package source as reliable identity.

---

# 16. Native Nuxel application launcher integration

Installed Flatpak apps must appear in the normal Nuxel launcher.

Inspect:

- Existing desktop file parsing.
- Application discovery.
- Icon lookup.
- Launch mechanism.
- Running app tracking.
- Category handling.
- Duplicate suppression.
- Cache refresh.

Use Flatpak's exported desktop files where appropriate.

Do not duplicate entries unnecessarily.

Do not assume every desktop file's `Exec` line can be split into a simple shell command.

Use desktop-entry-aware handling or a safe Flatpak application ID launch.

## 16.1 Desktop entry details

Respect:

- Desktop entry ID.
- App ID.
- Name.
- Generic name.
- Comment.
- Categories.
- Icon.
- Exec.
- DBusActivatable.
- Terminal flag.
- Startup notification metadata, where relevant.

## 16.2 Icon resolution

Support:

- Flatpak exported icons.
- Themed icons.
- Scalable SVG icons where supported.
- PNG icons.
- Fallback icons.

Do not download a new icon from an unrelated website just because the installed application icon cannot be resolved.

Use the actual exported app metadata.

## 16.3 Launcher cache

After installing or uninstalling:

- Refresh exported desktop metadata.
- Refresh app discovery.
- Refresh icon cache if required.
- Remove stale entries.
- Avoid restarting Phoc.
- Avoid restarting unrelated native applications.

If the Nuxel launcher caches app metadata, invalidate the appropriate cache.

---

# 17. ARM64 application compatibility

Select actual application refs from the configured remote.

Do not assume Firefox, VLC or another named application is currently available for AArch64.

Check the live metadata.

For each test app record:

- App ID.
- Branch.
- Architecture.
- Runtime.
- Runtime architecture.
- Version.
- Remote.
- Install status.
- Launch status.
- Graphics status.
- Audio status.
- Portal status.

Potential candidates, only if compatible refs actually exist, include:

- Firefox.
- VLC.
- A GTK application with file chooser support.
- A Qt application.
- A lightweight utility.
- A graphics test application.
- A browser/Electron-based app.

If an app has no ARM64 ref, report it as unsupported for native Nuxel Flatpak operation.

Do not install an x86_64 ref as if it were native.

Do not add emulation frameworks to this task.

---

# 18. systemd, cgroups and session integration

The device may combine newer Fedora/systemd userspace with an older Linux kernel.

Verify that combination instead of assuming workstation defaults.

## 18.1 User manager

Check:

- User systemd manager.
- Session D-Bus.
- Runtime directory.
- Correct login/session state.
- User services.
- Flatpak portal activation.
- Transient unit behavior.
- App launch and cleanup.

A Flatpak app must not work only when manually launched from a debugging terminal.

## 18.2 cgroups

Identify:

- cgroup v1.
- cgroup v2.
- Hybrid configuration.

Check actual controllers.

Do not assume every modern systemd cgroup feature exists on the kernel.

If a feature is optional and not required for normal Flatpak operation, document the limitation rather than making an unnecessary kernel change.

If a specific required feature is absent, prove the dependency before adding another kernel change.

## 18.3 App lifecycle

Test:

- Launch.
- Normal exit.
- Crash.
- Reopen.
- User-session restart.
- Portal restart.
- Desktop restart.
- Reboot.

Do not leave orphaned Bubblewrap processes after normal app exit.

Do not solve app lifecycle issues by killing every user process.

---

# 19. Real application test plan

Automated package checks are not enough.

Use actual ARM64-compatible Flatpak apps.

## 19.1 Basic application

Install a lightweight GTK app.

Verify:

- Install.
- Launcher entry.
- Icon.
- Window creation.
- Wayland connection.
- Input.
- Close.
- Relaunch.
- Uninstall.

## 19.2 File chooser

Use an app with a file-open/save operation.

Verify the portal and user-approved access.

The app must not gain full host filesystem access.

## 19.3 Browser

If a compatible ARM64 browser ref exists:

- Install.
- Launch.
- Load a web page.
- Test address bar.
- Test keyboard.
- Test file chooser.
- Test downloads.
- Test URI opening.
- Test audio/video where supported.
- Test rotation.
- Test background/resume.
- Close and relaunch.

## 19.4 VLC or media application

If a compatible ARM64 ref exists:

- Install.
- Launch.
- Open local media.
- Test audio.
- Test video.
- Test controls.
- Test screen rotation.
- Test background/resume.
- Close and relaunch.

Distinguish:

- Flatpak sandbox success.
- Audio integration success.
- Video decoding support.
- GPU rendering support.

Do not claim GPU decoding merely because video plays.

## 19.5 Multiple simultaneous apps

Run more than one compatible Flatpak application.

Verify:

- Isolated sandboxes.
- Independent user processes.
- Wayland windows.
- Audio handling.
- Portal consistency.
- Namespace limits.
- Memory behavior.
- Clean process exit.

Do not run a stress test that risks exhausting phone memory without monitoring.

---

# 20. Regression protection for existing Nuxel features

This task must not break the existing Nuxel system.

Verify after deployment:

## Kernel/hardware

- Correct kernel boots.
- `CONFIG_USER_NS=y`.
- Existing module ABI intact.
- Mali kbase works.
- Existing DRM/VGEM configuration remains where previously deployed and required.
- Existing DMA-BUF tests remain stable.
- Framebuffer/DECON path works.
- Wi-Fi works.
- Audio works.
- Touchscreen works.
- Existing device-tree support remains intact.

## Desktop

- Phoc starts.
- Native launcher works.
- Quick Settings work.
- Navigation works.
- Native applications launch.
- Native app discovery still works.
- Nuxel Bridge works.
- Existing WebKit host path remains operational.
- Existing display rotation remains functional if already implemented.

## Networking and access

- Wi-Fi networking remains functional.
- SSH remains available.
- Existing connection modes remain intact.
- No new broad bind/listen exposure is introduced.
- No unrelated firewall rule changes are introduced.

---

# 21. Automated test suite

Add or repair automated tests for:

## Kernel config

- `CONFIG_NAMESPACES=y`.
- `CONFIG_USER_NS=y`.
- `CONFIG_PID_NS=y`.
- MEMCG status.
- No unexpected config regression.
- Build configuration persists across releases.

## Namespace tests

- `unshare --user`.
- User mapping.
- Mount namespace creation.
- PID namespace operation where required.
- Repeated namespace creation.
- Namespace limit behavior.
- Ordinary-user operation.

## Bubblewrap

- Correct executable.
- Correct ownership.
- No unintended setuid.
- Namespace setup.
- Mount isolation.
- Writable path isolation.
- Process execution.
- Clean teardown.

## Flatpak

- Remote discovery.
- AArch64 detection.
- Runtime resolution.
- Installation.
- Launch.
- Update.
- Uninstall.
- Repair.
- Reboot persistence.

## Portals

- Frontend activation.
- Backend activation.
- FileChooser.
- OpenURI.
- Settings.
- Notifications.
- Screenshot/ScreenCast where supported.

## NuXtore

- Installed app discovery.
- Catalog filtering.
- Architecture validation.
- Installation.
- Progress.
- Error handling.
- Launch.
- Update.
- Uninstall.
- Icon handling.
- Duplicate handling.
- Native launcher refresh.

---

# 22. TWRP-authorized deployment sequence

This is the mandatory deployment workflow.

The owner starts the session with the phone already in TWRP recovery and connected over USB.

Do not ask for another recovery reboot unless the current recovery session itself is defective and the owner needs to intervene.

## Stage A — Recovery readiness

- Confirm ADB recovery state.
- Confirm TWRP responsive.
- Confirm S10+ identity.
- Confirm actual partition map.
- Confirm sufficient power.
- Confirm stable USB.

No writes yet.

## Stage B — Preserve current state

- Read current boot target.
- Save current image.
- Save failed image for diagnostics.
- Save hashes.
- Save build/deployment metadata.
- Locate known-good image.
- Verify restore procedure.

No writes until the recovery route is known.

## Stage C — Diagnose failure

- Inspect prior artifacts and logs.
- Compare working and failed boot images.
- Identify boot packaging or kernel failure.
- Explain the previous bootloop/hang.
- Determine whether a known-good image can safely restore normal boot.

## Stage D — Kernel configuration/build

- Use exact source.
- Preserve all working kernel options.
- Set `CONFIG_USER_NS=y`.
- Verify dependencies.
- Build exact modules.
- Generate `Module.symvers`.
- Verify ABI.
- Package full boot image.
- Inspect image and metadata.
- Hash artifact.

## Stage E — Pre-flash gate

Do not write unless:

- Source is verified.
- Configuration is correct.
- Image is built.
- Image format is correct.
- DTB is correct.
- Ramdisk is correct.
- Target is correct.
- Backup is verified.
- Rollback is ready.
- TWRP is protected.

## Stage F — Flash

The owner authorizes the targeted kernel-containing image write under this agreement.

Write only the exact verified target.

Verify write result.

Read back where safe.

Do not touch unrelated partitions.

## Stage G — Reboot and verify

Reboot into Nuxel.

Monitor boot.

Verify:

- Actual new kernel.
- Correct config.
- Mali.
- Phoc.
- Framebuffer.
- Network.
- SSH.
- User session.

If the device hangs or bootloops again, return to TWRP, preserve logs and restore the known-good image.

Do not wipe userdata.

## Stage H — Finish userspace integration

With Nuxel booted:

- Configure namespace runtime.
- Verify unprivileged `unshare`.
- Verify Bubblewrap.
- Configure Flatpak.
- Configure portals.
- Finish NuXtore.
- Test actual applications.
- Verify persistence.

---

# 23. Rollback and recovery requirements

A known-good kernel image must remain available until the final acceptance suite passes.

## 23.1 Failed boot

If Nuxel fails to boot:

1. Return to TWRP.
2. Verify ADB recovery.
3. Preserve logs.
4. Preserve the failed image.
5. Restore the verified known-good boot image.
6. Verify the restore operation.
7. Reboot into the previous working Nuxel state.

Do not wipe userdata.

Do not overwrite TWRP.

Do not flash multiple alternative images without understanding the failure.

## 23.2 Userspace failure

If Flatpak integration breaks the graphical session:

- Revert only the affected portal/session configuration.
- Preserve app data.
- Preserve OSTree repository.
- Preserve the kernel.
- Preserve TWRP access.
- Restore native launcher functionality.

Do not rebuild or reflash the kernel for a portal-only problem.

## 23.3 Flatpak repository failure

Use supported Flatpak repair operations.

Do not manually delete OSTree repository contents.

Preserve installed app data unless explicitly authorized for removal.

---

# 24. Documentation

Update the existing Nuxel docs.

Document:

### Recovery/kernel

- Starting TWRP state.
- ADB handshake.
- Device identity.
- Previous boot failure.
- Root cause.
- Known-good image.
- Failed image.
- Kernel source and commit.
- Kernel config changes.
- Module ABI.
- Boot image packaging.
- Flash target.
- Backup hashes.
- Recovery procedure.

### Flatpak

- Flatpak version.
- Bubblewrap version.
- Unprivileged mode.
- Namespace config.
- Namespace limits.
- Flathub remote.
- ARM64 architecture.
- Runtime branches.
- Installation scope.
- Storage.
- Update/repair workflow.

### Portals

- Portal frontend.
- Selected backend.
- Desktop identity.
- D-Bus activation.
- Supported interfaces.
- Unsupported interfaces.
- File chooser test.

### NuXtore

- Discovery.
- Catalog.
- Architecture filtering.
- Install.
- Launch.
- Update.
- Uninstall.
- Error handling.
- Launcher refresh.

### Compatibility

- Tested apps.
- App IDs.
- Runtime versions.
- ARM64 availability.
- Audio behavior.
- Graphics behavior.
- Known limitations.

Do not document a feature as working until the actual physical phone has passed the corresponding test.

---

# 25. Mandatory acceptance matrix

| Area | Required result |
|---|---|
| Initial state | Phone already in responsive TWRP over USB |
| Recovery handshake | ADB and TWRP identity verified |
| Previous failure | Bootloop/hang investigated and explained |
| Backup | Current and failed images preserved |
| Known-good boot | Verified recovery image available |
| Boot target | Exact partition identified |
| TWRP | Preserved, not overwritten |
| Kernel source | Exact current Nuxel source identified |
| Config | `CONFIG_USER_NS=y` |
| Namespace parent | `CONFIG_NAMESPACES=y` |
| PID namespace | Enabled where required |
| MEMCG | Status verified and decision documented |
| ABI | No unsafe module mismatch |
| Boot image | Correct complete image/DTB/ramdisk |
| Flash | Targeted verified write |
| Boot | Nuxel boots reliably |
| Runtime namespace | Normal user can create namespaces |
| Bubblewrap | Non-setuid unprivileged mode works |
| Flatpak | CLI and remotes work |
| Architecture | AArch64 refs correctly identified |
| App install | Compatible ARM64 app installs |
| App launch | Works as ordinary user |
| Portal | FileChooser works |
| Audio | Tested app plays audio |
| NuXtore | Discovers and manages installed apps |
| Launcher | App appears normally |
| Update | App/runtime update works |
| Uninstall | App removes cleanly |
| Persistence | Reboot preserves installations |
| Security | Sandbox remains intact |
| Regression | Existing Nuxel functionality remains working |

---

# 26. Required final report

Return an evidence-based report.

## 26.1 Previous failure

Explain:

- What happened during the previous reboot.
- Whether recovery itself worked.
- Whether the Nuxel boot target was malformed.
- Whether the kernel started.
- Whether initramfs started.
- Whether DTB/ramdisk/header/partition issues existed.
- What changed to prevent recurrence.

## 26.2 Recovery and flash record

Include:

- TWRP version.
- ADB state.
- Device identity.
- Partition map evidence.
- Current image hash.
- Failed image hash.
- Known-good image hash.
- New image hash.
- Exact target partition.
- Flash method.
- Readback result.
- Reboot result.
- TWRP preservation verification.

## 26.3 Kernel

Include:

- Kernel source commit.
- Kernel version.
- Config diff.
- `CONFIG_USER_NS` proof.
- MEMCG status.
- Module ABI.
- `Module.symvers`.
- Required module versions.

## 26.4 Flatpak

Include:

- Flatpak package version.
- Bubblewrap version.
- Bubblewrap executable path and permissions.
- Namespace test.
- Runtime namespace values.
- Remote list.
- Architecture.
- Installed refs.
- Runtime refs.
- Portal status.

## 26.5 Application results

For every tested app, provide:

- App ID.
- Architecture.
- Runtime.
- Version.
- Install result.
- Launch result.
- Wayland result.
- Portal result.
- Audio result.
- Graphics result.
- Update result.
- Uninstall result.

Clearly label any test not performed on the physical S10+.

---

# 27. Reference material

Use the exact target source and installed binaries as the final authority.

- Flatpak user namespace requirements:  
  https://github.com/flatpak/flatpak/wiki/User-namespace-requirements

- Bubblewrap project:  
  https://github.com/containers/bubblewrap

- Linux 4.14 namespace Kconfig source:  
  https://chromium.googlesource.com/chromiumos/third_party/kernel/+/refs/heads/v4.14/init/Kconfig

- Kernel configuration help and USER_NS history:  
  https://cateee.net/lkddb/web-lkddb/USER_NS.html

- XDG Desktop Portal documentation:  
  https://flatpak.github.io/xdg-desktop-portal/docs/

- Flatpak official setup:  
  https://flatpak.org/setup/

- TWRP backup guidance:  
  https://twrp.me/faq/whattobackup.html

---

# 28. Final instructions to the implementation agent

The owner is starting this session with the phone already in TWRP recovery, connected by USB.

Do not ask the owner to repeat that preparation.

**Your first responsibility is to inspect the recovery session and repair the previous failed boot/deployment path.**

The prior attempt left Nuxel hanging or bootlooping after reboot. You must not ignore that history, and you must not simply flash another build using the same unverified packaging procedure.

Preserve the failed image, identify the cause, establish a known-good rollback image and correct the boot artifact before another write.

Then enable:

```text
CONFIG_USER_NS=y
```

in the correct tracked Nuxel kernel configuration, preserving the current working kernel features and module ABI.

Perform the authorized targeted TWRP flash only after every pre-flash gate passes.

Reboot into Nuxel and prove that the new kernel is running.

Then complete unprivileged Bubblewrap, Flatpak, portals, NuXtore and native launcher integration.

Do not bypass the sandbox.

Do not launch applications as root.

Do not setuid Bubblewrap as the final solution.

Do not claim an app is supported until its actual ARM64 ref and runtime have been verified.

**PWNAGE-56000 is complete only when the phone reliably boots into Nuxel, the running kernel supports unprivileged user namespaces, and compatible Flatpak applications install, launch, update and uninstall through the normal Nuxel desktop experience.**
