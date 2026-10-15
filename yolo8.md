# NUXEL — GALAXY S10+ LIVE PHONE-OS COMPLETION MISSION
## DeepSeek V4 Flash Thinking · CodeSeeQ · A19 → A20+
### Live Nuxel repair, interactive UI, touchscreen and original MP4 boot animation

# 1. PRIMARY OBJECTIVE

You are the lead embedded Linux, Samsung Exynos 9820, Fedora ARM64, framebuffer graphics and phone operating-system engineer for Nuxel.

Nuxel is a custom Fedora-based Linux PHONE operating system.

**THE KERNEL BOOTS. THE FEDORA ROOTFS MOUNTS. SYSTEMD STARTS SERVICES. THE AMOLED DISPLAYS NUXEL AND ITS ANIMATED PENGUIN.**

Your mission is to finish the remaining engineering necessary to transition from the spinning penguin into a stable, responsive Nuxel phone interface.

The current target is a Samsung Galaxy S10+ SM-G975F, beyond2lte, Exynos 9820, board revision 26, EUR OPEN.

You are running in CodeSeeQ using DeepSeek V4 Flash Thinking.

Do real engineering, not merely recommendations.

Your primary objectives, in order:

1. Establish and verify an interactive live Nuxel debugging connection.
2. Diagnose why the spinning penguin never transitions into the phone UI.
3. Confirm Fedora services remain stable.
4. Implement a functional interactive Nuxel phone interface using the hardware-proven framebuffer path.
5. Bring up Samsung touchscreen input.
6. Restore the original Nuxel MP4 boot animation from the repository.
7. Implement a reliable animation-to-interface transition.
8. Investigate DRM/KMS support for a future Phoc/Phosh session.
9. Eliminate unnecessary recovery and full-device flash cycles.
10. Demonstrate a stable, usable Nuxel phone interface on hardware.

**Do not call the mission complete because the penguin spins.**

The final goal is an interactive, visibly working Linux phone system.

---

# 2. CRITICAL CURRENT STATE

Project root:

`~/x/nuxel`

Relevant paths:

- `scripts/s10plus-debug-pack/`
- `scripts/nuxel-adb-flash-pack/`
- `scripts/s10plus-debug-pack/captures/`
- `docs/s10plus-autonomous-boot-repair/`
- `build/out/s10plus/debug-candidates/`
- `build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img`

Current uploaded candidate: A19.

A19 BOOT SHA-256:

`7a24c04a101b93dd7b3df45472f395f85b10d236a2e6a4212b05c2cbee3c1f1b`

A19 introduced device-node creation for `/dev/ttyGS0`, designed to make Nuxel's USB CDC-ACM console interactive.

A18 had already demonstrated:

- Working kernel boot.
- Working embedded initramfs.
- USERDATA mounted as ext4 read-write.
- Fedora rootfs execution.
- Fedora systemd PID 1.
- Actual systemd service spawning.
- systemd-journald active/running.
- No failed systemd units in its captured report.
- Cgroup v2 with memory/pids controllers.
- USB gadget enumeration on macOS.

The A18/A19 captures originally showed a USB console endpoint with no data transfer.

**The user now reports stable Nuxel runtime and a live console. This newer observation must be verified directly.**

Do not assume that seeing `/dev/cu.usbmodem*` means the shell is working.

---

# 3. REPLACE RECOVERY-FIRST WITH LIVE-FIRST ENGINEERING

The old workflow was:

PATCH → REBUILD BOOT → TWRP FLASH → REBOOT → WAIT → MANUAL RECOVERY → LOG COLLECTION

This is no longer the preferred workflow.

The new workflow is:

**LIVE INSPECT → DIAGNOSE → PATCH USERSPACE → DEPLOY → RESTART AFFECTED SERVICE → VERIFY ON DEVICE**

Whenever the running Nuxel system can be accessed safely, perform development through that live connection.

Do not reboot the handset merely to test a changed userspace executable, systemd unit, configuration file, launcher or graphical asset.

Do not flash a 4 GiB rootfs merely because a few application files changed.

Keep the runtime live whenever possible.

Use atomic file replacement, retained backups, service restarts and rollback procedures.

If a change requires the kernel, device tree or embedded initramfs to be rebuilt, prepare a new BOOT candidate and use a verified recovery flashing workflow.

Never write a boot candidate directly onto the running phone's active BOOT partition merely for convenience.

Preserve a known recoverable image.

---

# 4. FIRST TASK — VERIFY THE ACTUAL LIVE CONSOLE

Check the current Mac USB device inventory.

Find the interface corresponding to:

`Nuxel S10+ Live Console`

Previous observations:

- USB vendor: 0x18d1
- USB product: 0x4ee7
- Host serial endpoint: `/dev/cu.usbmodem201`
- Gadget function: CDC ACM
- Target-side port: `/dev/ttyGS0`
- Target UDC: `10c00000.dwc3`

These are previously observed values; rediscover the current interface rather than assuming fixed device paths.

Read:

`docs/s10plus-autonomous-boot-repair/LIVE-DEBUG-CONNECTIVITY.md`

`docs/s10plus-autonomous-boot-repair/NEXT-ACTION.md`

Inspect:

`tools/s10plus/a19/nuxel-console.c`

Verify, using a safely executed command on the actual phone, that the console supports:

- Interactive input.
- Reliable output.
- Command execution.
- Correct Fedora filesystem access.
- Root or appropriate administrative permissions.
- Working process exit statuses.
- Stable connectivity during service restarts.

Run non-destructive diagnostics such as:

`uname -a`

`id`

`cat /etc/os-release`

`ps -p 1 -o pid,comm,args`

`systemctl is-system-running`

`systemctl --failed`

`systemctl status systemd-journald`

`cat /proc/mounts`

`cat /proc/cmdline`

If the serial port enumerates but commands cannot execute, DO NOT mark the live-console milestone complete.

Diagnose:

- Creation and ownership of `/dev/ttyGS0`.
- ACM function initialization.
- Host DTR/RTS state.
- tty open/close and hangup behavior.
- Termios configuration.
- Gadget-to-host byte delivery.
- Shell lifetime after `switch_root`.
- File-descriptor inheritance.
- Read/write error codes.

If CDC ACM remains unreliable, investigate a USB NCM networking gadget with SSH as an alternative.

Verify kernel support before implementing it.

When live access works, record:

`LIVE_NUXEL_SHELL=VERIFIED`

Only then promote live repair to the primary workflow.

---

# 5. UPDATE THE HUMAN–AGENT TWRP AGREEMENT

We are changing the normal workflow, not deleting recovery safeguards.

## NORMAL CASE: LIVE NUXEL IS RUNNING

When Nuxel is stable and the live shell is functioning:

- Do not return to TWRP.
- Do not reflash BOOT.
- Do not reflash USERDATA.
- Do not reboot unnecessarily.
- Apply supported userspace repairs live.
- Restart the minimum affected service.
- Verify the result immediately.
- Continue developing the interface.

TWRP is not required for routine userspace debugging.

## FALLBACK CASE: A NEW BOOT TEST FAILS

The previous agreement remains active for failed boot candidates.

The user will manually return the phone to TWRP if a new boot attempt fails.

**WHEN THE USER MANUALLY RETURNS THE S10+ TO TWRP AFTER A PENDING NUXEL BOOT TEST, THAT TEST FAILED.**

Automatically:

1. Detect verified TWRP recovery.
2. Record the attempted candidate as failed.
3. Capture pstore and previous-boot logs.
4. Preserve diagnostic evidence.
5. Determine the new failure cause.
6. Apply the next justified correction.
7. Continue autonomous engineering.

Do not ask the user whether that pending boot attempt failed.

A deliberate recovery reboot for maintenance, diagnostics or an explicitly planned recovery flash is not automatically a boot failure. Distinguish it from the user's manual failed-boot recovery signal.

If there is no pending boot test, recovery arrival is not sufficient to classify a failure.

Keep the agent's state persistent across USB disconnects.

Never sacrifice TWRP access.

---

# 6. INVESTIGATE WHY THE PENGUIN NEVER EXITS

A16–A19 include a first-light renderer designed to keep the panel alive.

The renderer may continue indefinitely even while Fedora is healthy.

Investigate the running animation process.

Determine:

- Its actual PID.
- Its parent process.
- Whether it survives switch_root.
- Which framebuffer it owns.
- Which buffer/page it writes.
- Whether it continues to draw over later applications.
- Whether the intended stop signal works.
- Whether the recorded animation PID is valid.
- Whether the animation readiness files are stale.
- Whether a real UI launcher exists.
- Whether a graphical service ever attempted startup.

Relevant state files:

`/var/lib/nuxel/boot-stage`

`/var/lib/nuxel/animation`

`/var/lib/nuxel/fb-hold.pid`

Read the current source and verify these paths against the actual running image.

Previously observed toybox shell defects:

- Empty case alternative matches unexpectedly.
- Some if/elif/else constructs execute the wrong branch.
- `$!` is not reliably assigned.

Do not reintroduce these defects into early boot.

Do not kill the working animation before an alternative visual process is ready.

Implement a proper state machine:

`FIRST_LIGHT → FEDORA_READY → PHONE_UI_STARTING → PHONE_UI_FRAME_COMMITTED → PHONE_UI_READY → ANIMATION_STOPPED`

Require actual readiness signals, not fixed delays.

The phone interface must demonstrate a real framebuffer commit and remain responsive before the animation relinquishes display ownership.

If UI startup fails, return to a visible Nuxel diagnostic screen.

Never leave the user with a permanent black screen because the animation stopped too early.

---

# 7. BUILD A REAL FRAMEBUFFER-NATIVE NUXEL PHONE UI

The currently proven S10+ kernel is Samsung Linux 4.14.253.

Existing hardware evidence:

- Samsung DECON/DSIM display path operates.
- AMOLED display works.
- Framebuffer can display custom Nuxel graphics.
- Physical resolution: 1440 × 3040.
- 32-bit framebuffer.
- Previously observed stride: 5760 bytes.
- Virtual framebuffer height: 6080.
- No working DRM/KMS device was observed.
- Kernel configuration recorded `# CONFIG_DRM is not set`.

**Phoc/Phosh should not be expected to work on the existing kernel without a suitable supported graphics backend.**

Do not waste time repeatedly launching an unsupported compositor.

The immediate deliverable is a transitional framebuffer-native Nuxel phone UI, implemented as a real Linux userspace service.

Reuse the existing Nuxel code and graphical assets wherever practical.

## Required first interactive screen

Build an interface with:

- Nuxel branding.
- Status bar.
- Current clock and date.
- Battery percentage and charging state.
- Basic power/USB status.
- Home screen.
- Touch-friendly navigation.
- Settings page.
- System information page.
- Debug/log viewer.
- Controlled reboot and shutdown actions.
- Clear error/status reporting.

Prioritize a usable native phone interface over elaborate visual effects.

It must execute as a real process under Fedora, not merely draw a static frame during early boot.

Prefer a lightweight, maintainable architecture.

Evaluate using an existing suitable embedded UI library versus extending the hardware-proven renderer.

Do not add a large toolkit without testing its framebuffer compatibility.

The UI must:

1. Render at the correct Samsung resolution.
2. Respect actual framebuffer stride and pixel format.
3. Correctly handle double-buffering or framebuffer page flips.
4. Avoid out-of-bounds writes.
5. Handle screen rotation and touch coordinate transformation.
6. Recover gracefully from rendering errors.
7. Operate with controlled resource usage.
8. Start and stop through a verified service mechanism.

### User-visible milestone

`INTERACTIVE_NUXEL_PHONE_UI=PROVEN`

Only when the user can see and interact with the actual interface.

A static screen or animation alone does not satisfy this milestone.

---

# 8. TOUCHSCREEN BRING-UP

The S10+ touchscreen is not an entirely unknown device.

Previous Nuxel logs proved:

`input: sec_touchscreen`

on a normal boot.

However, the driver has also failed during initialization or opening in other attempts.

There is a documented low-power charging-mode distinction.

The Samsung driver checks `lpcharge`.

When `androidboot.mode=charger` is set, touchscreen initialization can be skipped.

A17 proved the touchscreen input device could enumerate in normal boot mode.

A18 documented:

`sec_ts_input_open: Failed to start device`

with indications involving TSP power state and the Samsung sensor subsystem.

## Required investigation

Read the actual kernel source for:

`drivers/input/touchscreen/sec_ts/`

Inspect:

- Low-power charging boot mode.
- sec_ts probe.
- Touchscreen initialization.
- Input-device registration.
- Panel power state.
- I2C communication.
- Interrupt registration.
- Touchscreen firmware state.
- Runtime resume.
- TSP sysfs diagnostics.
- Samsung sensor-hub dependencies.

When testing touch, distinguish charger-mode from normal-mode boots.

Do not disable battery protections or arbitrarily force hardware power registers.

Verify real `/dev/input/event*` entries.

Read actual multitouch capabilities and supported coordinate ranges.

Use non-destructive event capture to confirm physical touches.

Map the verified input coordinates to the UI.

Test:

- Tap.
- Drag.
- Swipe.
- Multitouch, if supported.
- Rotation mapping.
- Responsiveness.
- Input recovery.

If full touch is not yet possible, make the UI testable through the live USB console or hardware keys while continuing the touchscreen driver repair.

Do not claim touch functionality based only on an input device's existence.

---

# 9. RESTORE THE ORIGINAL MP4 NUXEL BOOT ANIMATION

The user specifically requests the original Nuxel MP4 animation.

Search the entire repository, including:

`assets/`

`boot/`

`images/`

`configs/`

for the intended MP4 file.

Previous engineering documentation references:

`boot/nuxel-boot-animation.mp4`

The A7 build notes record that this MP4, approximately 5.5 MB, was removed from the minimal embedded initramfs to reduce BOOT size.

Do not assume the file still exists at the original path.

Locate and inspect the actual media first.

Check its:

- Duration.
- Dimensions.
- Frame rate.
- Video codec.
- Pixel format.
- Audio streams.
- File size.
- SHA-256.

Use ffprobe/ffmpeg on the MacBook where useful.

## Important: avoid bloating the kernel-embedded initramfs

Prefer placing the full animation in the Fedora rootfs.

The early boot image should contain only the minimal code/assets necessary for first-light.

After the Fedora rootfs mounts, the runtime animation player can load the MP4 or a preprocessed stream.

Build a practical renderer using the already proven Samsung framebuffer path.

Possible approaches:

- Decode the MP4 through Fedora's available multimedia stack.
- Preconvert the MP4 on the Mac using ffmpeg.
- Store optimized raw/RLE/compressed frames in the Fedora rootfs.
- Implement a small, efficient framebuffer player if necessary.

Choose based on real CPU, memory and framebuffer requirements.

Do not blindly use `ffplay` and assume an SDL desktop display exists.

Do not require X11 or Wayland merely to show the boot animation.

### Playback requirements

- Preserve the original Nuxel visual design.
- Adapt to the 1440 × 3040 display without unwanted distortion.
- Respect screen geometry and cutouts.
- Scale frames efficiently.
- Honor source timing.
- Drop late frames rather than allowing unbounded queues.
- Avoid unnecessary full-screen frame copies.
- Avoid writing beyond framebuffer memory.
- Avoid decoding enormous uncompressed frame sequences entirely into RAM.
- Suppress or remove audio unless explicitly needed.
- Render the first frame promptly.
- Loop while the actual UI is not ready.
- Hand off cleanly when the UI is ready.

Use a lower-resolution decoded stream with controlled upscaling if required by available CPU performance.

Record actual performance measurements.

A static/animated framebuffer fallback must remain available if MP4 decoding fails.

The MP4 is a visual upgrade, not an excuse to regress the working Fedora boot.

---

# 10. FULL FEDORA RUNTIME HEALTH

A18 already proved systemd service execution.

Preserve that fix.

Check the current system:

`systemctl is-system-running`

`systemctl --failed`

`systemctl list-units --type=service --state=running`

`journalctl -b -p warning`

`findmnt /`

`findmnt /sys/fs/cgroup`

`cat /sys/fs/cgroup/cgroup.controllers`

Verify that:

- PID 1 is systemd.
- D-Bus works.
- udev works.
- journald works.
- The main rootfs is correctly mounted.
- Required writable directories exist.
- The Nuxel UI service starts.
- User ownership and permissions are correct.
- The device is not spontaneously rebooting.
- The power/charging state is coherent.

Do not conclude everything is healthy merely because `systemctl --failed` shows zero units. Also check whether essential services are active, the boot has reached its intended target, and a login/UI session is running.

Retain Fedora 43 as the operating system.

Do not switch to Alpine or OpenRC.

Do not undo the systemd 258 compatibility changes that have already been proven on hardware.

---

# 11. LIVE REPAIR AND DEPLOYMENT

Whenever an interactive Nuxel shell is confirmed, use it for ordinary userspace modifications.

Implement a small, reliable deployment workflow with:

- Image/source version identification.
- Build artifact checksums.
- Atomic target replacement.
- Backup of replaced files.
- Service restart.
- Health verification.
- Automatic rollback on a failed service start.
- Persistent logging.
- Reproducible updates in the source repository.

Avoid modifying running executables in place.

Deploy new files under separate paths, then switch versions atomically where appropriate.

Keep critical system services running unless a restart is required.

For every live patch, prove that the source repository and deployed files remain synchronized.

Changes applied on the phone must also be reflected in the rootfs build sources so that future flashed images do not revert them.

If live deployment requires transferring files over CDC-ACM, verify that the connection supports binary transfer correctly.

Prefer a checked USB-network/SSH transfer route when available.

Do not stream binary artifacts through a terminal without a reliable framing and checksum mechanism.

---

# 12. DRM/KMS AND PHOSH — PARALLEL ENGINEERING TRACK

The long-term target is a full Phosh/Phoc Linux phone experience.

But the current Samsung kernel is downstream Linux 4.14 and uses a vendor framebuffer display path.

Investigate:

- Exynos display driver architecture.
- Samsung DECON/DSIM.
- Existing DRM/KMS support for Exynos 9820.
- Panel sequencing requirements.
- Suitable kernel porting approaches.
- Atomic modesetting and GBM requirements.
- wlroots/Phoc compatibility.
- Touch and seat management.
- EGL/software rendering viability.

Do not claim that merely enabling `CONFIG_DRM=y` is enough.

Preserve the hardware-proven framebuffer first-light path.

Maintain two independent milestones:

`FRAMEBUFFER_NATIVE_PHONE_UI_READY`

and

`PHOSH_PHONE_SESSION_READY`

Do not confuse them.

Prioritize delivering the framebuffer-native interactive UI before attempting a wholesale kernel upgrade.

If kernel modernization is necessary for a true Phosh session, prepare a separate scoped kernel-porting plan with concrete dependencies and regression tests.

Do not sacrifice the already working phone interface to make an experimental DRM kernel boot.

---

# 13. AUTONOMY AND FLASHING BOUNDARIES

The user authorizes autonomous software development and controlled testing on this expendable S10+.

You may:

- Edit Nuxel source.
- Install build/debug tools.
- Build phone userspace applications.
- Deploy userspace changes through verified live access.
- Restart affected services.
- Rebuild verified BOOT/rootfs images.
- Use TWRP ADB to flash authorized BOOT/USERDATA candidates when necessary.
- Perform controlled reboots.
- Collect logs.
- Continue testing after manual recovery.

No routine permission prompt is required for already authorized activities.

Hard boundaries:

- Do not overwrite TWRP RECOVERY.
- Do not alter EFS or SEC_EFS.
- Do not modify bootloader, PIT or modem firmware.
- Do not repartition.
- Do not modify hardware fuses.
- Do not disable battery or thermal safety protections.
- Do not flash unrelated partitions.
- Do not silently disable security measures as a debugging shortcut.

Before any partition write, verify the actual device, root permissions, target, capacity, mount state, image integrity and backups.

After writing, verify full readback integrity before rebooting.

Keep A16 first-light and A18 service-execution successes as regression baselines.

Do not reflash the same candidate repeatedly without a new reason.

---

# 14. REQUIRED DEVELOPMENT MILESTONES

Track these independently:

| Milestone | Initial status |
|---|---|
| Nuxel kernel executes | PROVEN |
| Fedora rootfs mounts | PROVEN |
| systemd PID 1 runs | PROVEN |
| systemd services execute | PROVEN A18 |
| Cgroup v2 usable | PROVEN A18 |
| Nuxel renders on AMOLED | PROVEN A16 |
| Spinning penguin visible | PROVEN A16 |
| USB CDC-ACM enumerates | PROVEN A18 |
| Interactive live shell | USER REPORTED; VERIFY DIRECTLY |
| Stable live repair workflow | NOT YET PROVEN |
| Fedora userspace UI process | NOT YET PROVEN |
| Interactive framebuffer UI | NOT YET PROVEN |
| Touchscreen events | NOT YET PROVEN |
| MP4 animation playback | NOT YET PROVEN |
| Animation-to-UI handoff | NOT YET PROVEN |
| DRM/KMS | NOT AVAILABLE IN CURRENT KERNEL |
| Phoc/Phosh | NOT YET PROVEN |
| Stable usable Nuxel phone | NOT YET PROVEN |

Do not mark achievements without actual hardware observations.

---

# 15. PROGRESS JOURNAL

Continue using:

`docs/s10plus-autonomous-boot-repair/`

Update:

- `STATUS.md`
- `ROOT-CAUSE.md`
- `BOOT-STAGES.md`
- `HYPOTHESES.md`
- `PATCHES.md`
- `TEST-RESULTS.md`
- `DEVICE-OBSERVATIONS.md`
- `DISPLAY-BRINGUP.md`
- `PHONE-UI-HANDOFF.md`
- `LIVE-DEBUG-CONNECTIVITY.md`
- `NEXT-ACTION.md`

Create:

- `A19-LIVE-RUNTIME-VERIFICATION.md`
- `NUXEL-LIVE-DEPLOYMENT.md`
- `NUXEL-MP4-ANIMATION.md`
- `NUXEL-INTERACTIVE-UI.md`
- `NUXEL-TOUCHSCREEN.md`
- `NUXEL-DRM-PHOSH-ROADMAP.md`

Every substantial change must have:

- Evidence.
- Files changed.
- Build/test receipts.
- Deployed artifact hash.
- Result from actual hardware.
- Rollback plan.
- Remaining uncertainty.

Preserve previous kernel, build and boot candidates.

---

# 16. EXECUTION STRATEGY

Use DeepSeek V4 Flash Thinking with high reasoning for:

- Exynos touchscreen troubleshooting.
- Framebuffer architecture.
- Graphics/input synchronization.
- Kernel compatibility.
- UI handoff design.
- Evidence-based root-cause analysis.

Use deterministic tools for:

- Runtime inspection.
- Binary compilation.
- Service management.
- MP4 metadata inspection.
- ffmpeg conversion.
- Framebuffer validation.
- Hardware input diagnostics.
- SHA-256 checks.
- Image regression tests.

Do not overload model context with massive logs.

Keep complete evidence on disk.

Avoid broad speculative rewrites.

Avoid unnecessary restarts and repeated flashes.

If three identical attempts fail without new evidence, change the diagnostic strategy.

---

# 17. FIRST ACTIONS — BEGIN IMMEDIATELY

Start in:

`~/x/nuxel`

**Step 1 — Verify the A19 live console.**

Confirm an actual interactive shell, not just USB enumeration.

**Step 2 — Inspect running Fedora.**

Check systemd, services, cgroup, rootfs mounts and the current UI/animation processes.

**Step 3 — Find the real Nuxel MP4.**

Search `assets/` and `boot/`. Inspect with ffprobe. Determine the optimal framebuffer playback implementation.

**Step 4 — Build a minimal native phone screen.**

Start with a home screen, clock, battery and diagnostics.

Do not wait for DRM/KMS to build the first interactive interface.

**Step 5 — Test live deployment.**

Build on the MacBook, deploy through the verified live connection, restart only the UI service, and confirm the phone displays the new screen.

**Step 6 — Fix touchscreen input.**

Use normal boot mode, inspect sec_ts logs and input events, and connect touch events to the new UI.

**Step 7 — Restore the MP4 animation.**

Implement efficient decoding and seamless animation-to-UI handoff.

**Step 8 — Continue toward Phosh.**

Investigate an actual DRM/KMS solution without regressing the working framebuffer-based phone.

---

# 18. FINAL DIRECTIVE

**STOP TREATING NUXEL AS A PHONE THAT MUST BE REFLASHED FOR EVERY SOFTWARE CHANGE.**

If the live console is verified, treat Nuxel as a running Fedora ARM64 system capable of live software development and deployment.

Maintain TWRP only as the recovery and kernel-replacement fallback.

**OUR AGREEMENT STILL APPLIES WHEN NEEDED: IF THE USER MANUALLY RETURNS THE DEVICE TO TWRP AFTER A FAILED TEST REBOOT, THAT TEST FAILED. COLLECT LOGS AND CONTINUE WITHOUT ASKING.**

Do not reboot or reflash merely to test UI changes.

Do not remove the working spinning penguin until the replacement UI actually renders successfully.

Do not claim Phosh works without a real graphics backend.

Do not claim a full phone OS is complete before touch interaction, display ownership and runtime stability are demonstrated.

## FINAL MISSION

**GET NUXEL FROM A SPINNING PENGUIN TO A REAL INTERACTIVE LINUX PHONE INTERFACE ON THE SAMSUNG GALAXY S10+.**

Then restore the original MP4 boot animation and make the transition into Nuxel seamless.

**THE PENGUIN BOOTS. NOW MAKE THE PHONE LIVE.**

EXECUTE THE NEXT ENGINEERING CYCLE.
