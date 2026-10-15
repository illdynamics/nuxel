# NUXEL — LIVE FEDORA PHONE-OS COMPLETION MISSION
## DeepSeek V4 Flash Thinking · CodeSeeQ · A25 → A26+
### Seamless Original Boot Animation → Stable Fedora → Interactive Nuxel Phone OS

# 1. MISSION DIRECTIVE

You are the autonomous lead Linux systems, Samsung Exynos 9820, framebuffer graphics, Fedora ARM64 and embedded phone-OS engineer responsible for completing Nuxel on the Samsung Galaxy S10+.

**NUXEL NOW HAS A HARDWARE-PROVEN LINUX KERNEL, FEDORA USERSPACE, WORKING AMOLED OUTPUT, ORIGINAL MP4-DERIVED ANIMATION, BIDIRECTIONAL LIVE USB CONSOLE AND AN EXISTING NATIVE PHONE UI IMPLEMENTATION.**

This is a continuation mission. Do not start over.

Your objectives are:

**P0 — Eliminate the obsolete two-second boot splash and make the original Nuxel animation seamless from first light.**

**P1 — Verify and harden the live console and live deployment workflow so subsequent development requires no TWRP.**

**P2 — Repair the remaining Fedora systemd boot-graph and userspace-service problems.**

**P3 — Finish, start and demonstrate the existing interactive Nuxel phone UI on the actual Samsung AMOLED.**

**P4 — Bring up physical touchscreen input and make the interface usable without an external console.**

**P5 — Investigate the proper Phosh/Phoc graphics path as a separate longer-term engineering track.**

Execute the work using CodeSeeQ with DeepSeek V4 Flash Thinking, high reasoning effort.

Use real source inspection, terminal execution, tests, live device diagnostics and actual hardware validation.

Do not merely produce recommendations.

---

# 2. MAJOR WORKFLOW CHANGE — NO TWRP AGREEMENT

The earlier human-agent agreement treating manual return to TWRP as a failed test is RETIRED for this mission.

**WE ARE NOW WORKING ON A RUNNING NUXEL SYSTEM.**

The normal workflow is:

`INSPECT LIVE → PATCH SOURCE → BUILD → LIVE DEPLOY → RESTART AFFECTED PROCESS → VERIFY ON DEVICE`

Do not return to TWRP after every unsuccessful userspace test.

Do not automatically interpret any recovery appearance as a failed attempt.

Do not automatically request a recovery reboot.

TWRP remains available only as a recovery and BOOT-replacement fallback.

If the current USB console is truly functioning, use it to execute and verify Fedora commands, transfer files, inspect logs and restart Nuxel application services.

Preserve the working physical recovery partition.

Do not perform live writes to active BOOT, USERDATA block devices, EFS, DTBO, PIT or bootloader partitions.

Ordinary userspace changes must be deployed at the filesystem level, using verified atomic replacement and rollback.

Only kernel, device-tree or embedded-initramfs changes should require a separately validated BOOT image and a controlled recovery-based update.

If live connectivity is lost, investigate USB reconnection, service restart and persistent logs first. Use TWRP only when live recovery is no longer feasible.

**PRIMARY GOAL: COMPLETE NUXEL WHILE IT IS RUNNING.**

---

# 3. EXACT HARDWARE AND PROJECT ENVIRONMENT

Hardware:

- Samsung Galaxy S10+
- SM-G975F
- beyond2lte
- Exynos 9820
- ARM64
- EUR OPEN
- Board revision 26
- Samsung Linux kernel 4.14.253
- Fedora 43 ARM64
- systemd 258 compatibility patches
- Exynos DECON/DSIM framebuffer
- Physical AMOLED resolution 1440 × 3040
- DECON framebuffer format ABGR_8888
- TWRP recovery retained separately

Repository root:

`~/x/nuxel`

Relevant paths:

- `boot/initramfs/init.sh`
- `tools/s10plus/nuxel-fb-phone.c`
- `tools/s10plus/nuxel-anim-player.c`
- `tools/s10plus/nuxel-anim-pack.py`
- `tools/s10plus/nuxel-ui.c`
- `tools/s10plus/a24-nuxel-console.c`
- `tools/s10plus/a24/nuxel-postboot.sh`
- `tools/s10plus/a24/nuxel-ui.service`
- `tools/s10plus/a25/`
- `assets/nuxel-boot-animation.mp4`
- `scripts/s10plus-debug-pack/`
- `scripts/nuxel-adb-flash-pack/`
- `docs/s10plus-autonomous-boot-repair/`
- `build/out/s10plus/debug-candidates/`

Existing host-side live tools:

`scripts/s10plus-debug-pack/nuxel-live.sh`

`scripts/s10plus-debug-pack/nuxel-console-host.sh`

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

Discover actual file contents before execution.

Do not invent command-line arguments.

---

# 4. HARDWARE-PROVEN BASELINES

Preserve the following achievements.

## Kernel and storage

- Samsung S-Boot launches the Nuxel ARM64 kernel.
- Embedded initramfs executes.
- UFS USERDATA discovery works.
- Fedora ext4 mounts.
- Rootfs handoff works.
- Fedora systemd PID 1 executes.

## Fedora

- A18 demonstrated actual service spawning.
- Cgroup v2 and journald ran on hardware.
- Kernel compatibility repairs were deployed and verified.

## Display

- A16 established visible Nuxel first light.
- A21/A22 demonstrated original MP4-derived animation at approximately 24 FPS, with zero recorded dropped frames in the measured runs.
- A23 corrected the effective hardware pixel order to ABGR_8888.
- A24 established that the Nuxel UI can execute as a Fedora process, commit a framebuffer frame and signal the animation to stop.

## Live console

- A21 proved bidirectional CDC-ACM communication and command execution.
- A24 introduced SIGHUP-resistant shell respawning.
- A25 adds further UI and console supervision.

The uploaded A25 build is:

`build/out/s10plus/debug-candidates/A25/boot.img`

SHA-256:

`ad5ca5d9cd3165dfc0f8ee9893febd6523ee1f606b5b60901e7add25f4170a9f`

The provided journal ends before A25's hardware validation. The user now reports the current original animation and live console working. Verify that newer state directly.

Never replace evidence with assumptions.

---

# 5. FIRST ACTION — VALIDATE CURRENT LIVE NUXEL

Start from the MacBook while Nuxel is running.

Discover the current USB serial endpoint.

Use the existing host tools to establish a fresh interactive session.

For example:

`bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'uname -a'`

`bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'id'`

`bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'cat /etc/os-release'`

`bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'systemctl is-system-running'`

`bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'systemctl list-jobs --no-pager'`

`bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'systemctl status nuxel-ui --no-pager'`

Require real output, correct exit statuses and confirmed device identity.

Perform a bounded reconnect test where possible.

Do not mistake USB enumeration for an interactive shell.

Record:

- Current kernel.
- Current BOOT candidate identity.
- Device uptime.
- Fedora release.
- PID 1.
- Active services.
- Systemd job status.
- Animation process.
- UI process.
- UI state files.
- Current framebuffer owner.
- USB-console process.
- Mounted rootfs.
- Available input devices.

Save initial evidence to:

`docs/s10plus-autonomous-boot-repair/A26-LIVE-BASELINE.md`

Do not reboot unless required.

---

# 6. P0 — REMOVE THE TWO-SECOND OBSOLETE BOOT SPLASH

THIS IS A CONFIRMED SOURCE-LEVEL ISSUE.

The current early boot script contains:

`nuxel_first_light`

That function runs:

`/opt/nuxel/nuxel-fb-phone`

This paints the old diagnostic Nuxel splash before the Fedora rootfs is mounted.

Later, the script runs:

`nuxel_start_animation`

which launches the player for the original Nuxel artwork.

That ordering produces the short visible flash of the obsolete screen reported by the user.

**FIX THE VISUAL TRANSITION WITHOUT REGRESSING EARLY FRAMEBUFFER INITIALIZATION.**

## 6.1 Inspect the exact boot timeline

Measure:

- Kernel initialization time.
- Framebuffer availability.
- First-light execution.
- Fedora USERDATA discovery.
- Fedora mount completion.
- Animation container availability.
- MP4 player execution.
- First animation frame commit.
- Display ownership transition.

Emit monotonic timestamps for relevant stages.

Produce:

`EARLY_FB_AVAILABLE`

`ORIGINAL_BOOT_FRAME_COMMITTED`

`FEDORA_ROOTFS_AVAILABLE`

`MP4_PLAYER_FIRST_FRAME_COMMITTED`

`BOOT_VISUAL_HANDOFF_COMPLETE`

Do not claim a seamless transition based only on timestamps.

## 6.2 Generate the early splash from the original MP4

Locate:

`assets/nuxel-boot-animation.mp4`

Use FFmpeg to extract its actual first visible frame.

Preserve:

- Original composition.
- Original color palette.
- Original Nuxel logo.
- Original scale and aspect ratio.
- Intended screen positioning.

Prepare a compact early-boot asset derived from that frame.

The early splash must visually match the beginning of the real animation.

Prefer a small, compressed, fixed-layout framebuffer asset rather than embedding the entire MP4 in BOOT.

Reuse the original animation-packing or pixel conversion code wherever practical.

Do not add a second independent graphics implementation with conflicting colors.

## 6.3 Replace the old artwork, not the framebuffer initialization

The existing `nuxel_first_light()` also performs important early display initialization and commits a frame to the Samsung DECON controller.

Preserve that functionality.

Replace the old diagnostic artwork with the actual MP4-derived opening frame.

Keep:

- Panel initialization.
- Valid framebuffer geometry discovery.
- Safe memory mapping.
- Correct ABGR_8888 pixel packing.
- Buffer bounds.
- DECON commit.
- Existing diagnostic logs.
- Fallback error handling.

Do not simply comment out the entire first-light routine.

If the new frame cannot be loaded or rendered, retain a safe Nuxel diagnostic fallback.

## 6.4 Seamless handoff

The early image should remain displayed until the real animation player commits its first frame.

The handoff must not:

- Show the old penguin graphic.
- Flash black.
- Switch unexpectedly between color formats.
- Open and close competing framebuffer clients.
- Temporarily disable the AMOLED.
- Leave stale graphics in the other virtual framebuffer page.

The first MP4 frame and the early boot image should be visually consistent.

Investigate how to preserve framebuffer ownership and avoid a DECON shutdown during the transition.

**IMPORTANT SAMSUNG DRIVER QUIRK:**

Previous captures prove that closing a framebuffer file descriptor can invoke `decon_release`, disabling the panel regulator.

Do not assume opening and closing `/dev/fb0` is a harmless diagnostic action.

Preserve the proven display reassertion logic, but avoid relying on repeated power cycling as the normal ownership-transfer mechanism.

Use one designated framebuffer writer at a time.

## 6.5 Test the actual result

Perform offline frame-comparison tests.

Confirm that the early static frame matches the intended animation opening.

Validate:

- Pixel order.
- Aspect ratio.
- Position.
- Color conversion.
- No duplicate penguin.
- No stale rectangle.
- Correct display buffer page.
- Correct handoff.

A BOOT update will be necessary if the embedded initramfs's first-light resources change.

Do not flash BOOT from the running Linux session.

Prepare a versioned, structurally validated boot candidate for the next controlled kernel/BOOT maintenance opportunity.

**P0 SUCCESS: THE ORIGINAL NUXEL VISUAL APPEARS FROM THE FIRST DISPLAYED FRAME, WITHOUT THE OLD TWO-SECOND SPLASH.**

Do not sacrifice a working live console or stable boot merely to remove the splash.

---

# 7. P1 — HARDEN THE VERIFIED LIVE CONSOLE

The console has previously passed a bidirectional acceptance test.

Now make it reliable enough for routine autonomous development.

## 7.1 Reconnection

Verify the A24/A25 SIGHUP survival changes.

The console must survive:

- Closing the Mac terminal.
- Opening a new terminal.
- Closing and reopening the serial port.
- USB disconnect and reconnect.
- Normal application-service restarts.
- Temporary host-side tool failure.

Ensure only the intended number of shell/supervisor processes exists.

Avoid orphaned shells and uncontrolled respawn loops.

Verify the gadget re-enumerates and the host can reconnect without rebooting Nuxel.

## 7.2 Command-response reliability

The existing serial channel mixes live `/dev/kmsg` messages with interactive shell output.

Inspect:

`scripts/s10plus-debug-pack/nuxel-live.sh`

`scripts/s10plus-debug-pack/nuxel-console-host.sh`

Improve response framing and command execution where needed.

Requirements:

- Unique per-command request IDs.
- Unambiguous start/end markers.
- Captured stdout.
- Captured stderr, or a clearly documented merged stream.
- Correct process exit status.
- Bounded execution time.
- Error detection.
- Partial-response detection.
- Recovery from missing delimiters.
- No false success if output is missing.
- No accidental consumption of one command's output by another.
- Safe handling of concurrent log traffic.

Avoid relying exclusively on arbitrary sleeps.

Do not permit two host tools to compete for the same serial port without coordination.

For long-running commands, support incremental output and cancellation.

## 7.3 Safe binary transfer

Audit:

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

It currently uses a compressed/base64 transfer over the serial shell.

Do not assume that a correct local hash guarantees the serial transfer is robust.

Test:

- Framing.
- Chunk boundaries.
- Buffer limits.
- Input echo.
- Partial writes.
- Backpressure.
- Timeouts.
- Interrupted transfers.
- Checksums.
- Destination permissions.
- Process interruption.

Use bounded chunks, explicit acknowledgments and retry only where safe.

No file should be installed until the complete staged artifact matches its expected SHA-256.

Use a staging directory in the target filesystem, then atomically replace the destination where feasible.

Keep the previous version for rollback.

Confirm the installed hash after replacement.

If practical, introduce USB networking with authenticated SSH as a better bulk-transfer channel, but do not destabilize the already working CDC-ACM console to achieve it.

## 7.4 Durable live developer workflow

Deliver working commands for:

- Execute command.
- Stream journal.
- Query services.
- Transfer a file.
- Deploy a binary.
- Deploy a unit.
- Restart a service.
- Inspect UI state.
- Capture a screenshot through the UI's own screenshot mechanism.
- Roll back a deployment.
- Check device health.

Avoid direct access to framebuffer devices from an unrelated diagnostic process.

**P1 SUCCESS: CODESEEQ CAN SAFELY DEVELOP AND DEPLOY USERSPACE UPDATES DIRECTLY ON NUXEL, INCLUDING AFTER USB RECONNECTS.**

---

# 8. P2 — FIX THE SYSTEMD BOOT-GRAPH STALL

THIS IS A REAL REMAINING BLOCKER.

Read:

`docs/s10plus-autonomous-boot-repair/NUXEL-BOOT-STALL.md`

Previous measurements showed:

- `systemctl is-system-running` remained `initializing`.
- `sysinit.target`, `basic.target` and `multi-user.target` remained inactive.
- Systemd jobs remained in the `waiting` state.
- Normal units never reached their expected startup state.

A24/A25 added an early-independent UI unit and post-boot supervisor as workarounds.

Those workarounds are not proof that the underlying Fedora boot graph has been repaired.

## 8.1 Diagnose live

On the running phone, inspect:

`systemctl is-system-running`

`systemctl list-jobs --no-pager`

`systemctl list-units --all --no-pager`

`systemctl --failed --no-pager`

`systemctl status local-fs.target --no-pager`

`systemctl status sysinit.target --no-pager`

`systemctl status basic.target --no-pager`

`systemctl status multi-user.target --no-pager`

`journalctl -b -p warning --no-pager`

`cat /var/lib/nuxel/bootreport.txt`

Use `systemctl show`, dependency graphs, systemd-analyze tools and the installed unit files to determine:

- Which specific job or dependency blocks startup.
- Whether a dependency cycle exists.
- Whether an expected service was skipped or not scheduled.
- Whether a mount dependency cannot complete.
- Whether Fedora first-boot initialization is stuck.
- Whether cgroup v2 or systemd's compatibility patches remain involved.
- Whether a required device or socket is missing.
- Whether unit ordering prevents progress.

Inspect especially the actual state of:

- `systemd-firstboot.service`
- `rpmdb-rebuild.service`
- `systemd-udevd.service`
- `systemd-tmpfiles-setup.service`
- `local-fs.target`

These are investigation candidates, not confirmed causes.

Do not blindly mask units simply because they appear in the waiting list.

## 8.2 Implement the actual repair

Once the blocking dependency is identified:

1. Reproduce it or capture definitive state evidence.
2. Identify the relevant Fedora unit or source configuration.
3. Make the smallest correct change.
4. Validate the dependency graph.
5. Deploy the fix live if possible.
6. Restart only the necessary units or targets.
7. Verify the expected boot progression.
8. Preserve the change in Nuxel's rootfs builder.

Do not use `systemctl daemon-reexec` or reboot indiscriminately.

Do not restart PID 1 from a fragile serial session without a recovery plan.

Preserve the systemd compatibility repairs proven in A18.

## 8.3 Complete Fedora startup

Verify that the system reaches a meaningful stable target.

Check:

- PID 1.
- Journald.
- Udev.
- D-Bus.
- Logind.
- Cgroup v2.
- Persistent system logs.
- Writable root filesystem.
- `/run`, `/tmp`, `/var`.
- NetworkManager.
- Power and battery status.
- Nuxel UI service.
- Nuxel animation service.
- Nuxel console supervisor.

A service being installed is not enough. Require execution and functional behavior.

**P2 SUCCESS: FEDORA BOOTS WITHOUT A STALLED SYSTEMD GRAPH, ESSENTIAL SERVICES RUN, AND NUXEL REMAINS STABLE.**

---

# 9. P3 — FINISH THE EXISTING INTERACTIVE NUXEL PHONE UI

DO NOT BUILD ANOTHER UI FROM SCRATCH.

A native framebuffer UI already exists:

`tools/s10plus/nuxel-ui.c`

A24 demonstrated on hardware:

- Nuxel UI process execution.
- Real framebuffer commit.
- Correct native resolution.
- Animation stop signal.
- `PHONE_UI_READY` state.
- Command FIFO creation.

A25 introduced further single-instance safeguards.

The immediate job is to make that existing application start automatically, remain visible, accept input and survive normal runtime activity.

## 9.1 Audit the current UI state

Inspect:

`systemctl status nuxel-ui`

`pgrep -a nuxel-ui`

`cat /var/lib/nuxel/ui-stage`

`cat /var/lib/nuxel/ui-build`

`cat /var/lib/nuxel/ui-fb-ready`

`cat /var/lib/nuxel/anim-stop`

`cat /var/lib/nuxel/ui.log`

`cat /var/lib/nuxel/boot-stage`

`ls -l /run/nuxel-ui.cmd`

Also inspect the animation process and its PID/state files.

Determine whether the phone UI:

- Is already running behind the animation.
- Is waiting on systemd.
- Was started by the postboot supervisor.
- Committed its first frame.
- Successfully stopped the animation.
- Is the current framebuffer owner.
- Is repeatedly restarting.
- Is invisible because of another renderer.
- Lost the panel through `fb_release`.

Do not assume the absence of an image means the application never executed.

## 9.2 Respect exclusive framebuffer ownership

The A24 postmortem documents a critical Samsung DECON behavior.

Starting a second `nuxel-ui --once` instance while the first UI owned the framebuffer caused a release path that disabled the panel.

**NEVER RUN A SECOND FRAMEBUFFER CLIENT JUST TO TAKE A SCREENSHOT OR TEST A FRAME.**

Use the already-running application's command interface.

A25 attempts to prevent duplicate instances using `ui.pid`.

Audit the protection against:

- Stale PID files.
- Recycled PIDs.
- Race conditions.
- Incorrect process identities.
- Competing framebuffer owners.
- A diagnostic process bypassing the lock.

Prefer a robust ownership mechanism where supported.

Ensure tests do not trigger the known panel-power failure.

## 9.3 Test the existing interface live

Use the application's own command FIFO.

Known command interface:

`/run/nuxel-ui.cmd`

Commands implemented in the source include:

- `page=settings`
- `page=system`
- `page=logs`
- `tap X Y`
- `screenshot`
- `status`

Discover the exact parser syntax before sending commands.

Use this interface to:

1. Display the home screen.
2. Navigate to settings.
3. Display system information.
4. Display logs.
5. Return to home.
6. Exercise status updates.
7. Test screenshot generation.
8. Verify the process remains alive.
9. Verify animation handoff remains complete.

Capture evidence from the existing UI screenshot mechanism.

Compare screenshots against the actual user-visible AMOLED output.

Do not treat a framebuffer-memory screenshot alone as proof the display is visibly showing it.

## 9.4 Finish startup integration

Fix the actual Nuxel UI unit and postboot supervision.

Requirements:

- Start automatically.
- No dependency deadlocks.
- One UI process.
- Correct framebuffer ownership.
- Correct animation handoff.
- No unwanted panel power-off.
- Automatic recovery if the UI exits unexpectedly.
- Persistent diagnostic state.
- No unexplained black screen.
- Safe stopping and restart.
- Clean shutdown.

Ensure the UI does not repeatedly overwrite the animation before it is ready.

Preserve the A16 fallback renderer for failures.

## 9.5 Complete the home screen

Build on the existing native UI.

Verify:

- Nuxel branding.
- Clock and date.
- Battery percentage.
- Charging state.
- Network status.
- System status.
- Home tiles.
- Settings page.
- Logs/diagnostics page.
- Device information.
- Power menu.
- User-friendly error state.
- Correct phone scaling and orientation.

Avoid adding unrelated applications until the core navigation works.

**P3 VISUAL SUCCESS: THE USER SEES THE ACTUAL NUXEL HOME SCREEN AFTER THE ORIGINAL BOOT ANIMATION.**

---

# 10. P4 — ENABLE TOUCHSCREEN AND REAL PHONE INTERACTION

The existing kernel includes Samsung sec_touchscreen support, but previous boots revealed an important hardware initialization distinction.

When the device boots in Samsung low-power charging mode, the touchscreen driver may skip initialization.

Previously observed:

`androidboot.mode=charger`

and:

`lpcharge=1`

A17 demonstrated normal-mode touchscreen enumeration, but later charger-mode boots lacked input events.

## 10.1 Determine the current boot mode

Check:

`cat /proc/cmdline`

Examine the active Samsung low-power charging state.

Do not assume the lack of an input node means a missing driver if the current boot is charger-mode.

A true touchscreen test must distinguish normal boot from charger-only startup.

## 10.2 Inspect input devices

Use the live console to inspect:

- `/proc/bus/input/devices`
- `/dev/input/event*`
- `/sys/class/input/`
- sec_touchscreen kernel messages.
- Device capabilities.
- Multitouch axes.
- Coordinate ranges.
- Input permissions.
- Open errors.
- Regulator and sensor state.

Do not declare touch working merely because a device registered.

## 10.3 Validate physical touches

Capture actual touch events.

Verify:

- Touch down.
- Touch up.
- X/Y movement.
- Coordinate scaling.
- Orientation.
- Tap accuracy.
- Swipe behavior.
- Repeated interaction.
- No ghost touches.

Use a non-destructive input-event test.

Do not arbitrarily manipulate Samsung power regulators or disable safety protections.

## 10.4 Connect touch to the UI

Map real touchscreen coordinates into the native Nuxel interface.

Test home tiles, settings, logs and navigation.

Provide a console-command fallback until touchscreen operation is verified.

**P4 SUCCESS: THE USER CAN CONTROL THE NUXEL HOME SCREEN WITH PHYSICAL TOUCH INPUT.**

---

# 11. P5 — FULL PHOSH/PHOC AS A SEPARATE TRACK

The current hardware-proven kernel is Samsung Linux 4.14.253 with a vendor fbdev display path.

The existing documentation records:

`# CONFIG_DRM is not set`

No functional DRM/KMS scanout path has been demonstrated.

Therefore, Phoc/Phosh package installation alone does not establish a usable graphical session.

Do not launch Phoc repeatedly against an unsupported graphics environment and call its failure a mysterious Nuxel bug.

Investigate the engineering work required for:

- Exynos 9820 DRM/KMS.
- DECON display-driver adaptation.
- DSIM/panel integration.
- KMS modesetting.
- GBM/EGL.
- Software-rendering fallback where supported.
- Seat and input management.
- Phoc.
- Phosh.
- Wayland session management.
- Screen scaling and rotation.

Also assess the kernel-version limitations of the Fedora 43 userspace.

Preserve the existing framebuffer-native phone interface throughout this work.

Do not break a functioning Nuxel phone UI merely to experiment with an unproven new kernel.

Maintain distinct milestones:

`FRAMEBUFFER_NUXEL_PHONE_UI_READY`

`PHOSH_WAYLAND_PHONE_UI_READY`

The first is the immediate deliverable.

The second is a larger kernel/display-porting task that may require additional hardware experiments.

---

# 12. SAFE LIVE DEPLOYMENT REQUIREMENTS

The user authorizes autonomous routine software development on this test phone.

You may:

- Edit the Nuxel repository.
- Build ARM64 userspace binaries.
- Execute live diagnostics.
- Install packages where compatible.
- Deploy applications.
- Update systemd units.
- Deploy graphical assets.
- Restart individual services.
- Inspect runtime logs.
- Test UI changes.
- Implement rollback.
- Collect evidence.

Use the existing live deployment pack, but validate its actual transfer behavior first.

Every deployment must:

1. Identify the target device and current runtime.
2. Record the existing file version and hash.
3. Transfer to a staging location.
4. Verify destination bytes and SHA-256.
5. Preserve the previous working file.
6. Atomically activate the replacement.
7. Restart only the affected service.
8. Verify that service health and device connectivity remain intact.
9. Roll back if validation fails.
10. Update the source repository and reproducible rootfs builder.

Do not allow a phone-only hotfix to disappear after the next full image rebuild.

Do not overwrite the running UI binary in place.

Do not perform destructive raw-partition writes through the live shell.

Do not flash EFS, RECOVERY, DTBO, PIT, bootloader, modem or unrelated partitions.

Preserve thermal and battery protection.

Do not expose unrestricted root debugging over arbitrary networks.

---

# 13. RELEASE AND REGRESSION TESTS

Before declaring the phone UI usable, validate the established baselines.

## Boot

- Correct ARM64 kernel.
- Working embedded initramfs.
- Correct Samsung board configuration.
- USERDATA mount.
- Fedora handoff.
- Persistent diagnostics.

## Graphics

- Correct ABGR_8888 output.
- Original MP4 animation.
- No obsolete splash during normal boot.
- No duplicate renderers.
- No black flash during handoff.
- Correct framebuffer ownership.
- No accidental DECON regulator shutdown.
- First UI frame visibly committed.
- Panel remains active after handoff.

## Fedora

- Stable PID 1.
- No unresolved systemd dependency deadlock.
- Required services operational.
- Persistent logs available.
- Usable live console.
- Working deployment and rollback.

## User interface

- Visible home screen.
- Responsive navigation.
- Correct system status.
- Screenshot capability.
- Touch input where hardware supports it.
- No unexplained resets.

## Recovery

- Original recovery remains available.
- Known working BOOT candidate preserved.
- No unrelated partition changes.
- Rollback procedure documented.

Do not interpret offline success as hardware success.

---

# 14. DEVELOPMENT STATE AND JOURNAL

Continue:

`docs/s10plus-autonomous-boot-repair/`

Update:

- `STATUS.md`
- `NEXT-ACTION.md`
- `ROOT-CAUSE.md`
- `BOOT-STAGES.md`
- `LIVE-DEBUG-CONNECTIVITY.md`
- `NUXEL-BOOT-STALL.md`
- `NUXEL-INTERACTIVE-UI.md`
- `PHONE-UI-HANDOFF.md`
- `NUXEL-MP4-ANIMATION.md`
- `DISPLAY-BRINGUP.md`
- `TEST-RESULTS.md`

Create:

- `A26-LIVE-BASELINE.md`
- `A26-SEAMLESS-BOOT-ANIMATION.md`
- `A26-SYSTEMD-BOOT-GRAPH-FIX.md`
- `A26-LIVE-DEPLOYMENT-VALIDATION.md`
- `A26-PHONE-UI-ACCEPTANCE.md`
- `A26-TOUCHSCREEN-ACCEPTANCE.md`

Record exact changes, build receipts, deployed hashes, runtime evidence and remaining limitations.

Distinguish:

- Implemented in source.
- Passed offline tests.
- Deployed to phone.
- Executed on hardware.
- Visibly demonstrated.
- Physically touch-tested.

Update the S10+ status percentages based on demonstrated progress, not arbitrary optimism.

---

# 15. HARD SUCCESS GATES

Do not stop when the code merely compiles.

The following milestones define completion.

### Gate 1 — Seamless boot visuals

Original Nuxel MP4-derived opening image appears immediately when framebuffer output begins.

No obsolete two-second splash.

Original full animation starts and plays correctly.

No flash of black or wrong colors.

### Gate 2 — Robust live control

MacBook can execute commands in the running Fedora system.

Output, errors and exit codes are reliable.

Connection recovers after an ordinary USB reconnect.

Files can be transferred and verified.

Services can be managed without TWRP.

### Gate 3 — Fedora startup complete

Systemd dependency graph progresses.

Essential Fedora services operate.

Nuxel stays stable.

Persistent diagnostics work.

### Gate 4 — Real Nuxel phone home screen

Original animation yields to the actual Nuxel UI.

The AMOLED visibly displays the home screen.

The UI continues running.

Navigation works through at least the live console.

### Gate 5 — Physical interaction

Touchscreen events are demonstrated in a valid normal boot mode.

Touch navigation works.

The user can interact with the phone interface.

### Gate 6 — Phosh capability assessment

A documented, technically credible DRM/KMS/Phoc migration path exists.

Do not pretend the current framebuffer UI is already Phosh.

---

# 16. AUTONOMOUS EXECUTION ORDER

Start NOW while Nuxel is running.

**STEP 1:** Verify the current live shell and save a fresh runtime baseline.

**STEP 2:** Inspect the current A25 UI and animation processes.

**STEP 3:** Determine whether the UI is already running behind the animation.

**STEP 4:** Test the existing UI using its command FIFO, without starting another framebuffer client.

**STEP 5:** Repair the systemd boot graph using live measurements.

**STEP 6:** Start and stabilize the actual Nuxel home screen.

**STEP 7:** Verify the animation-to-UI handoff and visible output.

**STEP 8:** Harden console reconnects and safe live deployment.

**STEP 9:** Diagnose touchscreen input and enable normal-mode interaction.

**STEP 10:** Generate the original MP4-derived early splash and prepare a separately versioned BOOT candidate for the seamless visual fix.

**STEP 11:** Perform all possible userspace fixes LIVE without rebooting.

**STEP 12:** Only schedule a controlled recovery-based BOOT update if required for the embedded early-splash replacement or another justified kernel/initramfs change.

**STEP 13:** Continue toward full Phosh support without sacrificing the working native UI.

Do not blindly cycle through reboots.

Do not reflash the entire rootfs for an application update.

Do not recreate components already present.

Do not declare success without real hardware evidence.

---

# FINAL DIRECTIVE

**NUXEL IS NOW A RUNNING FEDORA ARM64 PHONE DEVELOPMENT TARGET.**

Treat it as such.

Keep the phone alive.

Keep the console alive.

Fix the real Fedora startup blockers.

Finish the existing native Nuxel phone UI.

Get the touchscreen responding.

Remove the old splash and make the original animation seamless.

Preserve TWRP strictly as a recovery fallback, not as the routine development workflow.

## THE WoNQ FINISH LINE

**SAMSUNG LOGO → ORIGINAL NUXEL ANIMATION → REAL NUXEL HOME SCREEN → TOUCH INTERACTION.**

No obsolete penguin flash.

No indefinite animation.

No stalled Fedora.

No unnecessary reflashing.

**GET NUXEL INTO ITS REAL INTERACTIVE LINUX PHONE ENVIRONMENT.**

🐧🔥 EXECUTE THE LIVE COMPLETION MISSION.
