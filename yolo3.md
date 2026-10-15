# NUXEL — S10+ AUTONOMOUS REPAIR MISSION, CYCLE 4
## DeepSeek V4 Flash · CodeSeeQ · A12 → A13+
### Priority: Fedora service execution → first-light display → Phosh phone interface

# 1. YOUR MISSION

You are the lead embedded Linux engineer responsible for bringing Nuxel, our Fedora-based Linux PHONE operating system, to a fully booted and usable state on the Samsung Galaxy S10+.

THIS IS A CONTINUATION MISSION.

Twelve physical boot candidates have already been tested.

**MAJOR BREAKTHROUGH: A12 successfully reached Fedora systemd PID 1 on real hardware.**

Your assignment is no longer to fix the initial ARM64 kernel execution, embedded initramfs or USERDATA discovery. Those milestones are already proven.

Your immediate objective is to fix the Fedora service-execution failure, establish a working diagnostic userspace, initialize the Samsung display, and progress toward Nuxel's Phosh phone interface.

Use CodeSeeQ with DeepSeek V4 Flash, non-thinking mode. Be tool-driven, evidence-driven, systematic and autonomous.

Implement code, run tests, rebuild affected artifacts, test them on the physical handset and repeat based on the actual logs.

Do not merely write recommendations.

---

# 2. ENVIRONMENT

Repository root:

`~/x/nuxel`

Diagnostic tooling:

`scripts/s10plus-debug-pack/`

ADB flashing tooling:

`scripts/nuxel-adb-flash-pack/`

Persistent engineering journal:

`docs/s10plus-autonomous-boot-repair/`

Hardware captures:

`scripts/s10plus-debug-pack/captures/`

Boot candidates:

`build/out/s10plus/debug-candidates/`

Current Fedora rootfs:

`build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img`

Target hardware:

- Samsung Galaxy S10+
- SM-G975F / beyond2lte
- Exynos 9820
- ARM64
- Revision 26, EUR OPEN
- Bootloader G975FXXSEFUL1
- DTBO index 9
- TWRP 3.7.0_9-2
- ADB serial R58M75KDB2X

Live partition mappings, previously established:

- BOOT: `/dev/block/by-name/boot`
- USERDATA: `/dev/block/by-name/userdata`
- RECOVERY: `/dev/block/by-name/recovery`

Reverify paths and sizes before physical writes.

---

# 3. IMPORTANT — UPDATE THE ENGINEERING JOURNAL FIRST

The existing `STATUS.md` and `NEXT-ACTION.md` underreport our newest hardware achievement.

They describe A12 as reaching only the rootfs handoff.

The actual A12 logs prove much more.

Read:

`scripts/s10plus-debug-pack/captures/20261015T100000Z-A12-postfail/last_kmsg.txt`

The kernel records:

`ROOTFS_MOUNTED /dev/sda31 ext4 ro`

`ROOTFS_HANDOFF_STARTED -> /newroot`

Then systemd starts:

`systemd 258.11-1.fc43 running in system mode`

`Detected architecture arm64`

`Queued start job for default target multi-user.target`

`Reached target sysinit.target`

`Reached target basic.target`

These observations establish:

1. Nuxel's ARM64 kernel executes.
2. Its built-in initramfs unpacks.
3. Nuxel `/init` runs.
4. USERDATA is discovered.
5. Fedora ext4 mounts.
6. `switch_root` succeeds sufficiently to execute Fedora PID 1.
7. Fedora systemd begins initializing units and targets.

They do NOT establish successful service launching or a completed multi-user boot.

Update the milestone table accordingly before performing new experiments.

Preserve the original A12 capture.

Also note that `last_kmsg.txt` may contain concatenated records from multiple boot sessions. Identify boot boundaries and associate every claim with the correct kernel instance.

---

# 4. CURRENT ROOT CAUSE — FEDORA SERVICES FAIL TO SPAWN

The primary new blocker is:

`Failed to spawn executor: Function not implemented`

This affects numerous services, including:

- systemd-journald
- systemd-udevd
- dbus-broker
- systemd-logind
- polkit
- nuxel-firstlight
- systemd-tmpfiles
- systemd-remount-fs

This is not an isolated Nuxel-firstlight unit failure.

It is a systemic inability to create and execute service processes.

Additional errors include:

`Attaching device control BPF program ... failed: Argument list too long`

The kernel is Linux 4.14.253.

Fedora 43 uses systemd 258.11.

Upstream systemd 258 requires Linux 5.4 or newer, with 5.7 recommended, and removes cgroup v1 support.

**The userspace/kernel version mismatch is established. The exact operation producing ENOSYS is not yet proven.**

Do not assume that every failure is caused by `clone3`, `pidfd_spawn`, BPF or a particular syscall before tracing it.

---

# 5. PHASE ONE — IDENTIFY THE EXACT ENOSYS SOURCE

This is your highest-priority engineering task.

Investigate the systemd 258 process-spawning path, including:

- `exec_spawn()`
- `posix_spawn_wrapper()`
- `pidfd_spawn()`
- glibc's `posix_spawn` implementation
- `clone3`
- `clone`
- `pidfd_open`
- `CLONE_INTO_CGROUP`
- cgroup v2 requirements
- seccomp interactions
- kernel syscall availability
- systemd-executor launch
- `/proc/self/fd` handling

Inspect the relevant Fedora 43 systemd and glibc sources, not only Nuxel code.

Use the exact installed package versions.

Build small ARM64 diagnostic programs where necessary to test:

1. Executing `/bin/sh`.
2. `fork()` followed by `execve()`.
3. `posix_spawn()` of a simple process.
4. Availability of the suspected kernel syscalls.
5. PID-file-descriptor handling.
6. The service executor's prerequisites.

Record syscall return values and errno explicitly.

Use strace, tracepoints, or focused kernel instrumentation where supported.

Because the phone's console is unreliable, emit diagnostic evidence to `/dev/kmsg`, which has already worked on hardware.

Preserve outputs through the existing pstore mechanism where possible.

**Required result:**

Identify exactly which call fails and why.

Do not settle for:

"Probably systemd is too new."

We already know that. Find the concrete incompatibility that prevents service execution.

---

# 6. PHASE TWO — CHOOSE THE SMALLEST VIABLE SYSTEMD REPAIR

Evaluate these approaches against the actual evidence.

## Option A — Compatibility fix

If a small, testable kernel or userspace compatibility fix can restore normal process execution, investigate it.

Examples:

- Correcting an erroneous unsupported-syscall fallback.
- Correcting cgroup2 configuration.
- Backporting narrowly required syscall support if feasible.
- Fixing an incompatible glibc/systemd launch path.

Only implement a compatibility workaround when its precise correctness is demonstrable.

Do not fabricate syscall support by returning success without implementing the required semantics.

Do not blindly disable security mechanisms to suppress errors.

## Option B — A compatible systemd version

Investigate whether a prior systemd release that supports the Samsung 4.14 kernel can operate with the Fedora 43 userspace.

Assess:

- Exact minimum kernel requirements.
- Required systemd components.
- Fedora RPM dependencies.
- libsystemd ABI compatibility.
- udev compatibility.
- logind compatibility.
- service unit compatibility.
- Phosh/Phoc session dependencies.

If feasible, build a complete compatible systemd stack using reproducible ARM64 packages.

Do not replace only the PID 1 executable while leaving an incompatible collection of systemd binaries and libraries.

Fedora must remain the userspace distribution.

## Option C — Newer Exynos kernel

Research and assess a Linux 5.4+ kernel port for the Exynos 9820 and beyond2lte.

Before attempting an upgrade, require evidence that critical hardware support can be retained:

- UFS storage
- Board revision 26 DTB
- Samsung display controller
- AMOLED panel
- Regulators/clocks
- USB
- Touchscreen
- Power management

Do not replace the known-executing 4.14 Samsung kernel with an unverified mainline build merely to satisfy systemd's version requirement.

Kernel upgrade is an engineering project, not a version-number change.

## Selection rule

Choose the approach with the strongest evidence and shortest realistic path to a functional phone.

Document tradeoffs, tests, and remaining compatibility risks.

If full systemd compatibility cannot be achieved immediately, continue with the independent first-light diagnostic path below.

---

# 7. PHASE THREE — GET FEDORA PROGRAMS RUNNING INDEPENDENTLY

**DO THIS EVEN IF SYSTEMD REMAINS BLOCKED.**

We must not allow systemd compatibility to prevent testing whether the Samsung can execute Fedora applications and initialize its display.

Create an optional diagnostic handoff mode.

After Nuxel mounts the Fedora rootfs, allow the initramfs to launch a minimal diagnostic userspace instead of immediately starting systemd.

Requirements:

- Keep Fedora 43 as the mounted rootfs.
- Use actual Fedora ARM64 binaries.
- Confirm the ELF interpreter and shared libraries resolve.
- Execute `/bin/sh` or another small test program.
- Emit a positive execution marker to `/dev/kmsg`.
- Enumerate the relevant device files.
- Run the Nuxel first-light diagnostic directly when possible.
- Record the result.
- Distinguish a process-execution failure from a graphics-driver failure.

This may require a diagnostic PID 1 wrapper, switch_root-compatible handoff, or a small statically linked supervisor.

Ensure PID 1 does not exit accidentally.

The first successful direct launch of a Fedora userspace executable must be recorded as a separate hardware milestone.

**Do not require all systemd services to work before beginning display tests.**

---

# 8. PHASE FOUR — FIX ROOTFS MOUNT AND IDENTITY VALIDATION

A12 reports:

`ROOTFS_MOUNTED /dev/sda31 ext4 ro`

It also reports:

`rootfs os-release: <none>`

Yet Fedora systemd subsequently executes.

Investigate why the identity check failed.

Verify:

- `/etc/os-release`
- `/usr/lib/os-release`
- Relative and absolute path handling
- Symlinks
- Whether the rootfs is fully mounted
- Whether the diagnostic parser is faulty
- Whether `/usr` is part of the mounted filesystem

Fix the validation so it correctly identifies the Fedora rootfs.

For normal operation, prepare a validated writable-root configuration.

Before enabling read-write root:

- Verify ext4 consistency.
- Confirm filesystem capacity.
- Check mount flags.
- Check fstab.
- Check systemd remount behavior.
- Check `/var`, `/run`, `/tmp`, `/etc/machine-id` and journal storage.

Do not blindly remount read-write over a dirty filesystem.

Do not erase the existing rootfs.

Preserve its original version and build manifest.

---

# 9. PHASE FIVE — FIRST-LIGHT DISPLAY

The ultimate aim is a PHONE interface.

Start with the simplest observable display milestone.

Inspect:

- Exynos DECON
- DSIM/DSI
- Samsung AMOLED panel
- Kernel framebuffer
- DRM/KMS
- `/dev/fb0`
- `/dev/dri/card*`
- Panel power/regulators
- Display clocks
- Backlight state
- Reserved framebuffer memory
- Samsung graphics initialization logs

Do not assume a driver probe means the display is operational.

First investigate whether the current kernel has a functioning framebuffer or DRM scanout path.

Then test the included `nuxel-fb-phone` program directly from the diagnostic userspace.

If the required framebuffer does not exist, make that failure explicit.

Do not write arbitrary physical framebuffer addresses.

Where practical, build a minimal screen diagnostic that produces a visually distinctive Nuxel first-light pattern.

**First target: a visible Nuxel screen.**

It does not need to be Phosh yet.

After first-light, progress to:

1. Working input enumeration.
2. DRM/KMS device availability.
3. Phoc startup.
4. Correct Phosh graphical session.
5. Nuxel Home integration.
6. Touchscreen use.
7. Fully usable phone interface.

The previously inspected greetd configuration used:

`agreety --cmd /bin/sh`

That is not a working graphical phone-session configuration.

Correct it when a viable compositor path exists.

---

# 10. IMPORTANT — DO NOT BREAK THE WORKING BOOT CHAIN

A12 is the new hardware-proven baseline.

Do not regress it.

Preserve:

- Raw ARM64 kernel Image.
- Correct Android boot v1 header.
- Board revision 26 device tree.
- Kernel-embedded initramfs.
- Functional `/init`.
- USERDATA fallback logic.
- Successful Fedora ext4 mount.
- Successful switch_root.
- Working kernel logging.

Existing images:

`build/out/s10plus/debug-candidates/A10/boot.img`

`build/out/s10plus/debug-candidates/A11/boot.img`

`build/out/s10plus/debug-candidates/A12/boot.img`

A12 SHA-256:

`68217cdd59d047108f9e28de6d008fb8360dc9a5654b338df0c7bad4c26054ed`

Use A12 as the regression baseline.

Rebuild only affected components.

If changes are required to initramfs scripts that are embedded in the kernel, rebuild the embedded-initramfs kernel correctly; merely changing the external ramdisk will not update the running built-in `/init`.

Use:

`build/out/s10plus/debug-candidates/A13/`

and increment subsequent candidate identifiers.

Never overwrite A12.

---

# 11. TWO ADDITIONAL WARNINGS

## Samsung hard-reset hook

Earlier logs show panic traces through:

`drivers/samsung/sec_hard_reset_hook.c`

The user manually operates hardware buttons to recover the phone from failed boot attempts.

These recovery actions may trigger the kernel's hard-reset mechanism.

Correlate timestamps and inputs before attributing a boot failure to this hook.

Do not simply remove Samsung's hardware recovery functionality.

If an independent spontaneous reset defect is proven, address it narrowly while preserving a working manual recovery path.

## Host storage space

Previous investigation logs report the MacBook's data volume nearly full.

This caused truncated or corrupted kernel build files during Podman operations.

Check host and Podman VM free space before building.

Maintain sufficient headroom for the kernel tree, intermediates and image output; target at least 20 GiB free before large kernel builds.

Verify sizes and hashes after copying artifacts out of Podman.

Do not interpret a truncated build artifact as a kernel regression.

---

# 12. OUR PERMANENT TWRP = FAILED BOOT AGREEMENT

**THIS AGREEMENT REMAINS ACTIVE AND MUST NOT BE CHANGED.**

The user will manually return the Galaxy S10+ to TWRP whenever Nuxel fails to boot.

At mission startup, an already-running TWRP session is the normal starting condition.

After you flash a new candidate and reboot:

1. Record candidate ID, hashes and reboot timestamp.
2. Enter `AWAITING_BOOT_RESULT`.
3. Monitor the device.
4. Do not infer successful boot merely because ADB disconnected.
5. Allow the user to operate the physical recovery buttons.

**WHEN THE SAME DEVICE RETURNS TO TWRP AFTER THE TEST REBOOT, THE PREVIOUS NUXEL BOOT ATTEMPT FAILED.**

This is the user's deliberate failure signal.

Verify the expected serial and TWRP environment.

Then immediately record:

`BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`

`RECOVERY_ACCESS=RESTORED`

`NEXT_ACTION=CAPTURE_FRESH_LOGS`

Automatically:

- Reconnect to ADB.
- Capture pstore.
- Capture last_kmsg.
- Capture reset reasons.
- Preserve evidence.
- Compare with the previous attempt.
- Determine the new highest confirmed boot stage.
- Investigate the remaining blocker.
- Prepare the next evidence-backed repair.

Do not ask the user whether the boot failed.

Do not ask for confirmation of this signal.

Do not ask for approval before another routine authorized BOOT/USERDATA repair iteration.

The TWRP return proves the attempted Nuxel boot failed under this agreement. It does not independently identify its technical cause.

If the phone is inaccessible, stop physical operations and continue offline analysis until the user restores TWRP.

Keep the monitoring process alive and the mission state persisted across ADB disconnections.

---

# 13. AUTONOMY AND DEVICE SAFETY BOUNDARIES

The user authorizes autonomous development and repeated controlled test flashes on this expendable S10+.

Allowed:

- Source-code modification.
- Local tool installation.
- Kernel and rootfs builds.
- Read-only diagnostics.
- BOOT flashing.
- USERDATA flashing when needed.
- Readback verification.
- Controlled reboots.
- Recovery monitoring.
- Iterative repair.

Do not request routine approval for these authorized operations.

Absolute boundaries:

- Preserve TWRP RECOVERY.
- Preserve EFS and SEC_EFS.
- Preserve the bootloader and PIT.
- Do not repartition.
- Do not modify hardware fuses.
- Do not disable thermal protection.
- Do not flash unrelated partitions.
- Do not flash DTB, DTBO, VBMETA, modem or bootloader.

Before writes:

- Verify device identity.
- Verify root ADB.
- Verify partition mapping.
- Verify available capacity.
- Verify relevant mount state.
- Verify artifact integrity.
- Verify backups.
- Preserve a known-good recovery path.

After writes:

- Require successful write exit status.
- Require expected byte counts.
- Require exact SHA-256 readback.
- Record all results.

Prefer BOOT-only iterations whenever the Fedora rootfs itself is unchanged.

Do not repeatedly flash identical candidates without new evidence.

After three hardware attempts without meaningful diagnostic progress, change the investigation strategy.

---

# 14. DELIVERABLES AND PROGRESS TRACKING

Update:

`docs/s10plus-autonomous-boot-repair/`

Maintain:

- `STATUS.md`
- `ROOT-CAUSE.md`
- `BOOT-STAGES.md`
- `HYPOTHESES.md`
- `PATCHES.md`
- `TEST-RESULTS.md`
- `FLASH-ATTEMPTS.md`
- `DEVICE-OBSERVATIONS.md`
- `NEXT-ACTION.md`

For each attempted repair, document:

- Exact source change.
- Evidence.
- Tests.
- Built images.
- SHA-256 hashes.
- Device writes.
- Readback results.
- Boot observations.
- Newly reached milestone.
- Remaining failure.
- Next experiment.

Do not mark a stage complete solely because its binaries are present offline.

The following new milestones matter most:

1. Fedora systemd PID 1 runs — **PROVEN A12**.
2. Precise ENOSYS cause identified.
3. Fedora child process successfully launched on hardware.
4. A core systemd service actually runs.
5. A compatible init strategy works reliably.
6. Nuxel first-light directly executes.
7. Actual AMOLED screen output appears.
8. Phoc starts.
9. Phosh starts.
10. Nuxel phone interface becomes usable.

Keep the evidence-backed milestone table current.

---

# 15. START NOW — A13

Perform the following sequence:

1. Review the A12 previous-boot logs and update the milestone table.
2. Determine the exact reason systemd service spawning returns ENOSYS.
3. Create a minimal Fedora process-execution probe.
4. Determine the smallest viable compatibility repair.
5. Prepare an independent first-light diagnostic handoff.
6. Rebuild only the affected images.
7. Run offline checks and regression tests against A12.
8. Flash the verified candidate using the existing ADB tools.
9. Verify complete readback.
10. Reboot into Nuxel.
11. Monitor for Fedora execution, service startup and display signals.
12. If the user returns to TWRP, classify that attempt as failed, collect fresh evidence and continue automatically.

**DO NOT START OVER AT THE BOOTLOADER.**

**DO NOT REBUILD A WORKING KERNEL WITHOUT A JUSTIFIED CHANGE.**

**DO NOT REFLASH THE UNCHANGED 4 GiB ROOTFS WITHOUT REASON.**

**DO NOT CLAIM DISPLAY SUCCESS WITHOUT ACTUAL OUTPUT.**

## FINAL OBJECTIVE

Get Fedora-based Nuxel running reliably on the Samsung Galaxy S10+, bring the display online, and launch its usable Linux phone interface.

**TWRP RETURN AFTER REBOOT = FAILED NUXEL BOOT. NO ADDITIONAL CONFIRMATION NECESSARY.**

**CONTINUE AUTONOMOUSLY FROM A12. FIX THE SYSTEMD EXECUTION BLOCKER, GET FIRST LIGHT, AND FINISH THE PHONE BRING-UP.**

EXECUTE NOW.
