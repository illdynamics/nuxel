# NUXEL — GALAXY S10+ AUTONOMOUS BOOT & VISUAL BRING-UP
## DeepSeek V4 Flash Thinking · CodeSeeQ · Hardware Repair Mission A15+
### OBJECTIVE: BOOT NUXEL AND GET THE SPINNING PENGUIN ON SCREEN 🐧

# 1. YOUR MISSION

You are the autonomous lead engineer responsible for bringing Nuxel, our Fedora-based Linux PHONE operating system, into a working visual state on the Samsung Galaxy S10+.

This is a continuation of our previous hardware bring-up missions.

**PRIMARY OBJECTIVE: Boot Nuxel successfully on the real S10+, initialize a working graphics output, display the Nuxel first-light screen and spinning penguin, then progress to a usable Phosh phone interface.**

You have full access to CodeSeeQ, DeepSeek V4 Flash Thinking, terminal tools, the Nuxel repository, Podman, TWRP root ADB, debugging scripts and flashing utilities.

Perform actual engineering work.

Do not merely suggest commands. Investigate, modify, rebuild, validate, flash, observe, diagnose and iterate.

Your highest priority is evidence-based progress toward a stable, visible Nuxel system.

Do not introduce unrelated changes or rebuild the complete operating system unless necessary.

---

# 2. CURRENT HARDWARE STATE — IMPORTANT NEW DEVELOPMENT

Target:

- Samsung Galaxy S10+
- Model: SM-G975F
- Codename: beyond2lte
- SoC: Exynos 9820
- ARM64
- Board revision: 26
- Region: EUR OPEN
- Bootloader: G975FXXSEFUL1
- DTBO index: 9
- Recovery: TWRP 3.7.0_9-2
- ADB serial: R58M75KDB2X

**The phone is CURRENTLY BACK IN TWRP, and the user has successfully recovered it manually.**

Recent achievements:

1. Samsung S-Boot executes the Nuxel ARM64 kernel.
2. Persistent Linux kernel logs are available.
3. The embedded initramfs executes.
4. Nuxel discovers its UFS storage.
5. Fedora USERDATA mounts.
6. Nuxel performs its rootfs handoff.
7. Fedora systemd 258 has been observed executing as PID 1.
8. Full ADB flashing and SHA-256 readback verification have previously worked.
9. TWRP remains accessible.

The previous A12 hardware logs showed Fedora systemd service-execution failures, including:

`Failed to spawn executor: Function not implemented`

**NEW OBSERVATION FROM THE MOST RECENT BOOT ATTEMPT:**

- Samsung logo appears.
- Screen subsequently turns completely black.
- Device stays black for a prolonged period.
- Device spontaneously reboots after approximately 1–2 minutes or longer.
- Recovery button timing becomes difficult.
- User has now successfully manually returned the device to TWRP.

This is a FAILED Nuxel boot attempt.

However, the black screen does not prove that graphics initialized, nor does the spontaneous reboot establish a watchdog failure without supporting evidence.

**Do not assume the old A12 errors still describe the newest failure. Capture fresh evidence first.**

---

# 3. EXACT REPOSITORY AND TOOL LOCATIONS

Project root:

`~/x/nuxel`

Debugging pack:

`scripts/s10plus-debug-pack/`

Flashing pack:

`scripts/nuxel-adb-flash-pack/`

Captured hardware logs:

`scripts/s10plus-debug-pack/captures/`

Engineering journal:

`docs/s10plus-autonomous-boot-repair/`

Boot candidates:

`build/out/s10plus/debug-candidates/`

Fedora rootfs:

`build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img`

Known recovery partition mappings:

- BOOT → `/dev/block/by-name/boot`
- USERDATA → `/dev/block/by-name/userdata`
- RECOVERY → `/dev/block/by-name/recovery`

Discover and read the existing scripts, README files, image manifests, current source state and previous agent journals before executing them.

Do not assume the current boot candidate is A14 solely because that was the last candidate discussed. Determine which image was actually flashed using the journal and, if needed, read-only partition readback.

Preserve all previous candidates.

---

# 4. OUR PERMANENT HUMAN–AGENT TWRP AGREEMENT

## THIS IS A HARD AGREEMENT — DO NOT CHANGE IT

The user has explicitly agreed to handle physical recovery whenever an autonomous Nuxel boot attempt fails.

The procedure is:

1. You prepare a patched boot candidate.
2. You validate it offline.
3. You flash it through TWRP ADB.
4. You verify partition readback.
5. You reboot the Samsung.
6. You monitor the device and available diagnostic channels.
7. If Nuxel bootloops, freezes, goes black indefinitely or fails to reach the agreed success milestone, the USER manually returns the phone to TWRP.
8. You automatically detect that return through ADB.

**WHEN THE SAME SAMSUNG RETURNS TO TWRP AFTER AN AUTONOMOUS TEST REBOOT, THAT NUXEL BOOT ATTEMPT HAS FAILED.**

This is our explicit signal.

Do not ask:

- Did the boot fail?
- Did you get into TWRP?
- Should I continue?
- Do you want me to fix the next issue?
- Can I flash another authorized BOOT candidate?

A verified return to TWRP after a pending boot test is sufficient.

Record:

`BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`

`RECOVERY_ACCESS=RESTORED`

`NEXT_ACTION=CAPTURE_FRESH_BOOT_EVIDENCE`

Then automatically:

1. Reconnect to ADB.
2. Verify the device serial and recovery state.
3. Capture pstore and previous-boot kernel logs immediately.
4. Capture reset reasons and recovery metadata.
5. Save all evidence under a new timestamped capture directory.
6. Correlate logs with the exact previous candidate.
7. Identify the earliest newly demonstrated failure.
8. Develop the next evidence-backed correction.
9. Rebuild and validate.
10. Continue the authorized hardware repair cycle.

The TWRP return proves the attempt failed under our agreement; it does not identify the root cause.

The initial TWRP state at mission startup is normal and must not be mistaken for an additional failed attempt.

If the phone disappears from ADB, allow the user to perform physical recovery. Continue offline analysis and reconnect checks, but do not repeatedly issue reboot commands.

Do not declare success solely because the phone stops responding or leaves recovery.

---

# 5. PHASE ONE — CAPTURE FRESH POST-FAILURE LOGS NOW

**ABSOLUTE FIRST PRIORITY: Collect the newest failed-boot evidence before rebooting again.**

The user has just manually restored TWRP.

Begin by verifying:

```bash
cd ~/x/nuxel
adb devices
adb shell id
adb shell getprop ro.product.device
adb shell getprop ro.twrp.version
```

Then discover the debug-pack entry point and invoke its complete read-only collection procedure.

Capture:

- `/sys/fs/pstore/`
- `/proc/last_kmsg`
- `console-ramoops`
- Samsung persistent kernel logs
- Kernel panic records
- Samsung reset reasons
- Watchdog/reset information
- `/proc/cmdline`
- Bootloader information
- Current boot partition metadata
- TWRP recovery logs
- Relevant device-tree properties

Do not clear pstore.

Preserve the complete raw captures.

Distinguish:

- Logs generated by the previous Nuxel boot.
- Logs generated by the current TWRP session.
- Kernel messages generated by the user's recovery-button actions.

The user was forced to use several Power/Volume button combinations to regain TWRP. Samsung's hard-reset hook may therefore appear in the logs.

**Do not automatically attribute a hard-reset-hook panic to the original boot failure. Correlate it with the user's physical recovery attempts.**

Create a fresh diagnostic report identifying the exact stage reached by the newest candidate.

Compare it with A12, A13 and A14.

Determine whether the newest attempt progressed, regressed or merely changed display behavior.

---

# 6. PHASE TWO — FIND THE SPONTANEOUS REBOOT CAUSE

The phone now enters a prolonged black-screen state before rebooting spontaneously.

Investigate the following independently:

### Kernel watchdog

- Samsung Exynos watchdog
- Kernel watchdog timeout
- Watchdog petting
- Kernel panic timeout
- Emergency reset paths
- Hardware reset reason
- Watchdog-related persistent logs

### Initramfs watchdog

Inspect recent Nuxel initramfs code for:

- Hard-coded boot timeouts
- Shell background watchdog loops
- USERDATA discovery deadlines
- `switch_root` deadlines
- Forced reboot paths
- Commands triggered when boot progress markers are absent

A previous build reportedly used an approximately 45-second startup watchdog. Verify whether such logic still exists in the current candidate.

### systemd failure

Inspect:

- PID 1 startup
- Service spawn failures
- Failed dependencies
- Boot target progression
- Emergency mode
- Reboot policies
- Service restart loops
- Kernel/userspace compatibility

### Display failure

Investigate whether panel initialization, backlight, framebuffer or DRM faults contribute to the black-screen state.

### Power-state behavior

The user previously saw a low-battery-looking icon, despite TWRP reporting a full battery.

Inspect available charger, battery and power-management logs.

Do not assume the battery is depleted or healthy solely from the icon or reported percentage.

Do not disable thermal protection, battery safety or essential hardware safeguards.

**Required outcome: Identify whether the restart is explicitly requested by software, caused by a kernel panic, initiated by a watchdog, or still undetermined.**

Use real log evidence.

---

# 7. PHASE THREE — FIX FEDORA SERVICE EXECUTION

The earlier proven boot state reached Fedora systemd 258 on Samsung Linux 4.14.253.

Systemd services previously failed with:

`Failed to spawn executor: Function not implemented`

This remains a known compatibility blocker unless the newest evidence proves it was resolved.

Investigate:

- Exact failing syscall and errno.
- Fedora systemd 258 process spawning.
- `clone3`, `clone`, `fork` and `execve`.
- `posix_spawn`.
- pidfd APIs.
- cgroup configuration and availability.
- seccomp behavior.
- Kernel namespace support.
- systemd-executor compatibility.
- Fedora 43 glibc behavior.

Important:

Systemd 258 officially requires a newer kernel baseline than Linux 4.14.

Do not merely suppress error messages or make unsupported syscalls falsely return success.

Choose an evidence-supported repair strategy:

1. A narrowly scoped, correct kernel compatibility implementation.
2. A properly built compatible init/userspace stack.
3. A verified newer Exynos kernel port, if feasible.
4. A temporary diagnostic supervisor to reach independent first-light testing.

Keep Fedora 43 as the rootfs distribution.

Do not switch to Alpine.

Do not call the problem fixed because systemd PID 1 itself starts. Require successful execution of real child services.

Build and execute focused ARM64 process-spawning probes where useful.

---

# 8. PHASE FOUR — MAKE FIRST LIGHT INDEPENDENT OF SYSTEMD

**THIS IS A HIGH-PRIORITY FEATURE FOR THIS MISSION.**

We want to see the spinning Nuxel penguin even if Phosh or some systemd services remain broken.

Create a minimal and reliable first-light boot path that does not depend on a complete graphical desktop session.

Nuxel is a PHONE OS. The visual target is the real Samsung AMOLED display.

Investigate and use the simplest verified graphics path available:

- Existing Samsung framebuffer interface.
- Exynos display controller.
- DECON / DSIM.
- DRM/KMS if supported.
- Panel power sequencing.
- Regulator and clock dependencies.
- Existing kernel console/display initialization.
- Preserved bootloader framebuffer where valid.

The rootfs contains a `nuxel-fb-phone` diagnostic executable.

Inspect its actual functionality and supported framebuffer format.

Do not assume `/dev/fb0` exists.

### First-light requirements

If a working framebuffer or DRM scanout path exists:

1. Determine display dimensions and pixel format.
2. Validate memory bounds and stride.
3. Initialize the display through supported kernel interfaces.
4. Draw an unmistakable Nuxel first-light screen.
5. Animate the spinning penguin if basic graphics output works.
6. Record successful display initialization in logs.
7. Ensure the screen persists long enough for human observation.

Do not write arbitrary physical display memory addresses.

Do not guess hardware register values.

Do not disable display safety or power controls.

Do not equate successful userspace writes to a buffer with confirmed visible output.

**The milestone is a visibly rendered Nuxel screen on the physical phone.**

A static penguin is a valid intermediate milestone.

An animated penguin is the next milestone.

Phosh comes afterward.

If framebuffer/DRM support is missing, identify the exact missing kernel component or initialization dependency and implement the smallest technically justified correction.

---

# 9. PHASE FIVE — RESTORE A STABLE FEDORA BOOT

Once kernel and direct userspace execution work:

- Correct rootfs mount behavior.
- Verify required writable runtime directories.
- Configure `/run` and `/tmp`.
- Validate `/var` and journal storage.
- Verify systemd compatibility.
- Verify udev startup.
- Verify D-Bus.
- Verify logind.
- Verify user session handling.
- Verify network initialization.
- Verify Nuxel service dependencies.
- Verify stable startup without spontaneous reboots.

Do not repeatedly reflash the Fedora rootfs if the issue lives only in the kernel or embedded initramfs.

If a rootfs change is necessary, modify the original build source and produce a separately versioned image.

Require a clean ext4 verification.

Test process execution, service startup and graphical initialization independently.

---

# 10. PHASE SIX — PHOSH PHONE INTERFACE

Only after establishing a viable graphics path and userspace startup, configure the full Nuxel phone session.

Inspect and repair:

- Phoc compositor startup.
- Phosh session environment.
- greetd configuration.
- PAM/session initialization.
- D-Bus user session.
- Seat/input permissions.
- Wayland socket creation.
- Touchscreen device enumeration.
- Display scaling and orientation.
- Nuxel Home launcher.
- On-screen keyboard.
- User permissions and home directory.

The previous Fedora rootfs was found to have a greetd configuration launching:

`agreety --cmd /bin/sh`

This is not a configured Phosh session.

Fix the session configuration at the appropriate stage.

Test graphical login independently from background system services where possible.

Do not assume Phosh is functional simply because the ARM64 binaries exist.

**Final objective: a real, visible, responsive Nuxel phone interface.**

---

# 11. PRESERVE THE ALREADY-WORKING BOOT CHAIN

Earlier hardware testing established a functioning:

- Samsung S-Boot handoff.
- Raw ARM64 Linux Image.
- Kernel-embedded initramfs.
- Nuxel `/init`.
- UFS USERDATA discovery.
- Fedora ext4 mount.
- Root filesystem transition.
- Fedora systemd PID 1 execution.

Preserve those achievements.

Before making a kernel or initramfs change, compare the proposed candidate against the last hardware-proven baseline.

Verify:

- Android boot header.
- Raw ARM64 Image structure.
- Embedded initramfs.
- Correct board device tree.
- Valid `/init`.
- Rootfs discovery.
- Correct kernel command line behavior.
- Image capacity.
- SHA-256.

Prevent regressions back to gzip kernel packaging or malformed Android header fields.

When rebuilding an embedded-initramfs kernel, confirm the actual embedded files changed in the resulting kernel.

Do not accidentally package a stale boot image.

---

# 12. AUTONOMOUS FLASH–TEST–REPAIR LOOP

You are authorized to run controlled, repeated hardware bring-up cycles on this expendable S10+.

The workflow is:

**CAPTURE → ANALYZE → PATCH → BUILD → VERIFY → FLASH → READBACK → REBOOT → OBSERVE → TWRP RETURN → CAPTURE AGAIN**

For each iteration:

1. Create a uniquely numbered candidate.
2. Preserve the previous candidate.
3. Record the specific problem being tested.
4. Apply minimal source-level corrections.
5. Run targeted offline tests.
6. Verify image integrity.
7. Confirm device identity and root ADB.
8. Verify live partition paths and capacity.
9. Verify affected filesystems are unmounted.
10. Verify recovery backups are available.
11. Flash only the authorized partitions that actually changed.
12. Verify readback hashes.
13. Record attempt ID, image hashes and reboot time.
14. Perform a controlled reboot.
15. Monitor connectivity and available progress markers.
16. If the user manually returns the phone to TWRP, mark the attempt FAILED.
17. Immediately capture fresh logs.
18. Compare the new hardware outcome against the previous candidate.
19. Continue with the next evidence-backed correction.

**Do not require user approval for every routine authorized BOOT or USERDATA flash.**

However, preserve absolute hardware boundaries:

- Never erase or overwrite TWRP RECOVERY.
- Never modify EFS or SEC_EFS.
- Never modify bootloader or PIT.
- Never repartition.
- Never modify modem/radio firmware.
- Never change hardware fuses or Knox state.
- Never disable critical thermal/power safety protections.
- Never flash DTB, DTBO, VBMETA or unrelated partitions as a speculative workaround.
- Never operate on an unverified device or guessed partition.

Prefer BOOT-only repairs when only the kernel or embedded initramfs changes.

Do not rewrite the 4 GiB Fedora rootfs unnecessarily.

If write or readback verification fails, stop that boot attempt.

After three hardware tests that provide no new evidence, stop speculative testing and improve observability instead.

---

# 13. WATCHDOG AND RECOVERY HANDLING

The phone's most recent boot left the screen black and then spontaneously restarted.

Because recovery entry temporarily became difficult, this mission must treat recovery preservation as a primary engineering requirement.

Before rebooting a new candidate:

- Verify the current recovery environment.
- Verify existing recovery backups.
- Verify the test candidate.
- Avoid uncontrolled reboot loops.
- Add bounded diagnostics where technically appropriate.
- Avoid overly aggressive software watchdogs that obscure the original problem.
- Preserve Samsung's physical recovery key combinations.

Do not disable legitimate hardware safety watchdogs merely to conceal failures.

If ADB disconnects:

- Do not assume boot success.
- Monitor for verified Nuxel or TWRP connectivity.
- Allow the user to return the device to TWRP.
- Avoid infinite reboot commands.
- Persist the current engineering state.

If the phone returns to TWRP, our agreement applies: the test failed.

---

# 14. PROGRESS TRACKING

Continue the existing engineering journal:

`docs/s10plus-autonomous-boot-repair/`

Maintain:

- `STATUS.md`
- `BOOT-STAGES.md`
- `ROOT-CAUSE.md`
- `HYPOTHESES.md`
- `PATCHES.md`
- `TEST-RESULTS.md`
- `FLASH-ATTEMPTS.md`
- `DEVICE-OBSERVATIONS.md`
- `DISPLAY-BRINGUP.md`
- `NEXT-ACTION.md`

Every candidate must record:

- Candidate identifier.
- Exact changes.
- Root-cause hypothesis.
- Evidence supporting the change.
- Tests run.
- Artifact sizes.
- SHA-256 hashes.
- Flash/write receipts.
- Readback results.
- Physical boot observations.
- New boot milestones.
- Failure classification.
- Next justified step.

Preserve full logs on disk.

Do not fill model context with irrelevant raw output.

Update the S10+ integration progress table using demonstrated hardware behavior, not unsupported percentage estimates.

---

# 15. REQUIRED MILESTONES

Track the following independently:

| Milestone | Starting status |
|---|---|
| Samsung bootloader launches Nuxel kernel | PROVEN |
| Embedded initramfs executes | PROVEN |
| USERDATA discovery and Fedora ext4 mount | PROVEN |
| Fedora systemd PID 1 executes | PROVEN |
| Normal Fedora child service execution | NOT PROVEN |
| Stable boot without spontaneous reset | NOT PROVEN |
| Functional framebuffer or DRM scanout | NOT PROVEN |
| Visible Nuxel first-light screen | NOT PROVEN |
| Spinning penguin animation | NOT PROVEN |
| Phoc compositor starts | NOT PROVEN |
| Phosh phone shell starts | NOT PROVEN |
| Touch-enabled Nuxel phone UI | NOT PROVEN |

If the newest logs demonstrate additional progress, update these immediately.

If they reveal a regression, record it rather than preserving outdated success claims for the current candidate.

---

# 16. PRIORITY ORDER FOR THIS MISSION

Do not scatter effort across unrelated tasks.

**Priority 0:** Capture fresh boot logs from the newest black-screen/reboot failure.

**Priority 1:** Determine why the device spontaneously restarts.

**Priority 2:** Restore reliable child-process execution or provide a compatible diagnostic userspace.

**Priority 3:** Establish actual Samsung display output.

**Priority 4:** Display static Nuxel first-light.

**Priority 5:** Animate the spinning penguin.

**Priority 6:** Achieve stable Fedora service startup.

**Priority 7:** Start Phoc and Phosh.

**Priority 8:** Deliver a usable touchscreen Linux phone interface.

It is acceptable to complete the first-light path before all background services are functioning.

Do not call the entire mission complete until the required visual milestone is physically demonstrated.

---

# 17. MODEL AND TOOL EXECUTION STRATEGY

You are running DeepSeek V4 Flash Thinking.

Use high reasoning effort for:

- Kernel compatibility analysis.
- Syscall failures.
- Device-tree behavior.
- Samsung display initialization.
- Root-cause correlation.
- Patch review.

Use deterministic terminal tools for:

- Parsing kernel logs.
- Comparing images.
- Building kernels.
- Inspecting ELF dependencies.
- Verifying filesystem structures.
- Capturing ADB evidence.
- Computing SHA-256 checksums.

Keep reasoning and execution separated by reproducible tests.

Avoid broad speculative source rewrites.

Do not repeatedly execute failing commands without investigating why.

Maintain a persistent engineering journal so the mission can resume after context resets.

---

# 18. FINAL DELIVERABLES

Produce:

1. Analysis of the latest spontaneous reboot.
2. Evidence-backed root cause or precisely documented uncertainty.
3. Updated Nuxel source.
4. Rebuilt and validated boot/rootfs candidates where needed.
5. Full build and verification receipts.
6. Kernel and userspace compatibility findings.
7. Display initialization findings.
8. First-light execution results.
9. Hardware test history.
10. Current remaining blockers.
11. Updated S10+ status and milestone table.

If a visual Nuxel screen appears, record the exact candidate, image SHA-256, kernel log evidence and user's observation.

Do not claim the animation is visible from software logs alone.

---

# 19. START EXECUTION NOW

You are in:

`~/x/nuxel`

The Samsung is currently in TWRP with root ADB available.

The user has successfully recovered the handset after the latest black-screen boot failure.

**FIRST ACTION: CAPTURE THE FRESH PREVIOUS-BOOT LOGS.**

Then:

1. Analyze the reboot cause.
2. Compare the newest candidate with previous working boot stages.
3. Patch the smallest confirmed blocker.
4. Restore reliable diagnostic userspace execution.
5. Bring up the Exynos display.
6. Render Nuxel first-light.
7. Animate the penguin.
8. Stabilize Fedora systemd and services.
9. Launch Phosh/Phoc.
10. Continue toward a fully usable Linux phone.

You are authorized to conduct verified BOOT/USERDATA test flashes and controlled reboots without requesting approval for each routine iteration.

**PERMANENT AGREEMENT: WHEN THE USER MANUALLY RETURNS THE DEVICE TO TWRP AFTER A TEST REBOOT, THE PREVIOUS NUXEL BOOT ATTEMPT FAILED. AUTOMATICALLY CAPTURE THE NEW LOGS AND CONTINUE.**

Do not repeat identical failed candidates.

Do not overwrite recovery.

Do not claim success without hardware evidence.

## FINAL MISSION

**GET NUXEL BOOTED ON THE REAL SAMSUNG GALAXY S10+, MAKE ITS DISPLAY WORK, AND PUT THAT SPINNING PENGUIN ON THE PHONE.**

🐧 EXECUTE THE NEXT ENGINEERING CYCLE.
