# NUXEL — WoNQ PRIORITY OVERRIDE
## DeepSeek V4 Flash Thinking · CodeSeeQ · S10+ Autonomous Bring-Up
### A19 → A20+ · Original MP4 → Live Console → Fedora → Phone UI

# PRIMARY DIRECTIVE

You are continuing Nuxel development on the Samsung Galaxy S10+ (SM-G975F, Exynos 9820, beyond2lte, EUR OPEN, revision 26).

The user has explicitly changed the development priorities.

**THE NEW PRIORITY ORDER IS ABSOLUTE:**

1. **RESTORE THE ORIGINAL NUXEL MP4 BOOT ANIMATION.**
2. **ESTABLISH A RELIABLE LIVE USB CONSOLE.**
3. **COMPLETE AND STABILIZE THE FEDORA USERSPACE.**
4. **DELIVER THE ACTUAL INTERACTIVE NUXEL PHONE UI.**

This ordering overrides the previous mission's instruction to fix USB connectivity first.

We have already achieved the following hardware milestones:

- ARM64 Linux kernel boots.
- Kernel-embedded initramfs executes.
- Fedora 43 rootfs mounts.
- Fedora systemd starts.
- Systemd service execution was demonstrated in A18.
- Exynos framebuffer drives the physical Samsung AMOLED.
- Nuxel first-light graphics display correctly.
- A spinning penguin animation has been observed by the user.
- USB CDC-ACM enumerates, but console I/O remains nonfunctional.

The user wants the ORIGINAL NUXEL MP4 animation to be the next visible hardware achievement.

**This is a Linux PHONE OS, not a desktop distribution. Preserve Fedora 43, the Nuxel architecture and all hardware-proven functionality.**

Use CodeSeeQ and DeepSeek V4 Flash Thinking to implement, compile, validate, deploy, flash, test and iterate.

Do not merely provide recommendations.

---

# 1. CURRENT ENVIRONMENT

Project root:

`~/x/nuxel`

Debugging tools:

`scripts/s10plus-debug-pack/`

Flashing tools:

`scripts/nuxel-adb-flash-pack/`

Captures:

`scripts/s10plus-debug-pack/captures/`

Engineering journal:

`docs/s10plus-autonomous-boot-repair/`

Candidates:

`build/out/s10plus/debug-candidates/`

Fedora rootfs:

`build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img`

Previous candidate:

`build/out/s10plus/debug-candidates/A19/boot.img`

Relevant source directories:

- `assets/`
- `boot/`
- `images/s10plus/`
- `kernel/s10plus/`
- `device/s10plus/`
- `tools/s10plus/`

The current physical device is expected to be in TWRP with working root ADB.

Verify the actual current device state before performing any hardware operation.

---

# 2. PRIORITY ONE — RESTORE THE REAL NUXEL MP4 BOOT ANIMATION

**DO THIS FIRST.**

We already have hardware-proven framebuffer output.

The temporary spinning penguin has served its purpose: it demonstrated that Nuxel can render onto the real Samsung AMOLED.

Now restore the original Nuxel boot animation.

## Step A — Find the actual source animation

Search the complete repository for:

- `*.mp4`
- `*.webm`
- `*.mov`
- Existing boot-animation sources and scripts

Especially inspect:

`assets/`

and:

`boot/nuxel-boot-animation.mp4`

Previous documentation mentioned an approximately 5.5 MB MP4 asset.

Do not assume that filename or size is still correct.

Use the actual file found.

Inspect it using `ffprobe`.

Record:

- Source path
- SHA-256
- Resolution
- Frame rate
- Duration
- Video codec
- Pixel format
- Audio tracks
- File size

Preserve the visual design.

Do not substitute the diagnostic animation or invent a new one if the original is available.

## Step B — Select the correct playback architecture

The Samsung currently uses a hardware-proven Linux framebuffer path:

- Exynos DECON/DSIM
- AMOLED 1440 × 3040
- 32-bit framebuffer
- Previously observed stride 5760 bytes
- No proven DRM/KMS graphical compositor

Do NOT assume `ffplay` can draw directly onto the framebuffer.

Use FFmpeg on the MacBook for preprocessing when beneficial.

Evaluate two approaches:

**Approach A — Runtime MP4 decoding**

Use a lightweight Fedora userspace decoder and a small framebuffer-compatible player.

Decode frames into the required framebuffer pixel format.

**Approach B — Preprocessed animation**

Use FFmpeg to convert the MP4 to an optimized frame stream or compressed frame sequence.

Write a minimal framebuffer player that can load and render the frames efficiently.

Choose the approach that offers:

- Fast startup
- Smooth playback
- Low CPU overhead
- Controlled memory use
- Correct pixel format
- Correct orientation
- Minimal boot dependencies
- Reliable operation on the Samsung 4.14 kernel

A preprocessed frame sequence is acceptable as long as it faithfully reproduces the original MP4 animation.

## Step C — Preserve framebuffer safety

Read actual runtime framebuffer information.

Do not assume historical dimensions are necessarily valid on every boot.

Inspect:

- Visible resolution
- Virtual resolution
- Pixel format
- Stride
- Framebuffer length
- Page layout
- Buffer-flipping support

Render within verified memory boundaries.

Avoid allocating the entire animation uncompressed in RAM.

Use streaming, bounded caching or compressed frame storage.

If playback falls behind, drop late frames rather than allowing unbounded lag.

Keep screen brightness and power behavior within supported driver controls.

## Step D — Correct placement of animation assets

The kernel-embedded initramfs should remain small.

Keep the working minimal early first-light renderer as the fallback.

Put the complete MP4, decoder or converted animation assets in the Fedora rootfs unless testing proves another approach is necessary.

The boot sequence should be:

1. Samsung bootloader starts Linux.
2. Nuxel embedded initramfs initializes the display.
3. Minimal first-light appears.
4. Fedora rootfs mounts.
5. Original Nuxel animation player becomes available.
6. Original MP4 animation begins.
7. Playback loops until the interactive phone UI is genuinely ready.

Do not enlarge the kernel image unnecessarily by embedding large animation assets.

## Step E — Implement the MP4-to-UI handoff

Implement an explicit state machine:

`EARLY_FIRST_LIGHT`

→ `FEDORA_MOUNTED`

→ `ORIGINAL_MP4_ANIMATION`

→ `PHONE_UI_STARTING`

→ `PHONE_UI_FRAME_COMMITTED`

→ `PHONE_UI_READY`

→ `ANIMATION_STOPPED`

Do not simply kill the animation after a fixed timeout.

Do not allow the animation and UI to overwrite each other's framebuffer.

The player should stop only after another renderer can reliably take over.

If the phone UI fails, retain a visible diagnostic screen or safe animation fallback.

## Step F — Test the real animation

Before flashing, verify the decoder and framebuffer renderer using offline tests.

Use representative video frames to validate:

- Scaling
- Pixel conversion
- Buffer boundaries
- Frame ordering
- Frame timing
- Memory consumption
- Fallback behavior

Test the animation renderer independently of Phosh and Wayland.

Produce a new validated candidate only after the animation implementation is ready.

**PRIORITY ONE HARDWARE SUCCESS: THE ORIGINAL NUXEL MP4 ANIMATION IS VISIBLY PLAYING ON THE REAL S10+ AMOLED.**

User observation is required to confirm actual visual success.

Once this milestone is demonstrated, proceed to Priority Two.

Do not require the live console to be fixed first, but preserve enough persistent logging to diagnose animation failures.

---

# 3. PRIORITY TWO — FIX THE ZERO-BYTE LIVE USB CONSOLE

The MacBook previously detected the Nuxel CDC-ACM gadget, but the receive count remained zero.

Enumeration is not a working console.

Investigate:

- Samsung DWC3 USB gadget controller
- ACM function setup
- UDC binding
- `/dev/ttyGS0`
- Gadget endpoint behavior
- Host DTR/RTS
- Target-side tty handling
- Shell process lifetime
- Systemd service ordering
- Console stdin/stdout/stderr
- USB disconnect/reconnect behavior
- Target-side blocking writes
- Host-side terminal configuration

Inspect existing A18/A19 USB diagnostics and source.

Implement deterministic host and target test programs.

First prove target-to-host communication with a known message:

`NUXEL_TX_PROBE`

Then prove host-to-target communication:

`NUXEL_RX_PROBE`

Then verify a complete request-response exchange.

Only afterward enable interactive shell access.

The console must correctly handle:

- Standard output
- Standard error
- Command exit status
- Terminal I/O
- Timeouts
- Disconnects
- Reconnects
- Shell restarts

Require successful execution of:

`uname -a`

`id`

`cat /etc/os-release`

`systemctl --failed`

`journalctl -b`

If CDC ACM cannot be repaired efficiently, evaluate USB NCM/ECM networking plus SSH.

Verify kernel support and macOS compatibility before implementing a fallback.

Keep debug access restricted to the trusted physical USB connection, with appropriate authentication.

**PRIORITY TWO SUCCESS: CODESEEQ CAN EXECUTE COMMANDS ON THE RUNNING NUXEL PHONE AND RECEIVE ACTUAL RESULTS WITHOUT TWRP.**

Once this works, use live development and deployment by default.

---

# 4. PRIORITY THREE — COMPLETE THE FEDORA USERSPACE

Preserve the demonstrated A18 systemd service-execution success.

Verify and repair:

- Fedora 43 ARM64 rootfs
- systemd PID 1
- Cgroup v2
- udev
- journald
- D-Bus
- logind
- Service startup dependencies
- Nuxel system services
- User and group permissions
- Rootfs mount configuration
- Writable runtime directories
- Persistent logging
- Power and charging state
- NetworkManager
- USB debug service
- Controlled shutdown and reboot

Do not simply rely on `systemctl --failed` returning zero.

Verify actual service execution and operational behavior.

The existing Samsung kernel remains Linux 4.14.253, so preserve any proven compatibility fixes.

Keep Fedora 43.

Do not switch to Alpine, OpenRC or Android userspace.

Once Priority Two succeeds, perform service repairs through the live console wherever possible.

Do not reflash the 4 GiB rootfs for small configuration changes if a verified live deployment can accomplish the same result.

**PRIORITY THREE SUCCESS: STABLE FEDORA USERSPACE WITH WORKING SERVICES, LIVE LOGS AND NO UNEXPECTED REBOOTS.**

---

# 5. PRIORITY FOUR — BUILD THE ACTUAL INTERACTIVE NUXEL PHONE UI

The final objective is to leave the animation and enter a real Linux phone interface.

The existing Exynos kernel has a working framebuffer but no demonstrated DRM/KMS backend suitable for modern Phoc.

Therefore, prioritize a framebuffer-native phone interface before a speculative large kernel-porting effort.

Create a practical interactive Nuxel home screen using Fedora userspace.

Minimum functionality:

- Nuxel branding
- Clock and date
- Battery status
- Charging information
- Network indicator
- Home screen
- Settings
- Device information
- Logs/diagnostics
- Phone-friendly navigation
- Touch input where supported
- Power controls
- Error reporting

Build a proper service lifecycle.

Support clean startup, shutdown and restart.

Use the verified Samsung framebuffer geometry and safe rendering techniques.

Investigate the Samsung `sec_touchscreen` driver and `/dev/input/event*` devices.

Capture real input events.

Do not claim touchscreen support until actual touches are received and mapped correctly.

If touch input remains unavailable, provide temporary control through the live console or existing hardware keys.

Once a functioning phone UI frame has been committed, let the MP4 animation hand over display ownership.

Only declare the graphical milestone complete when the actual phone visibly displays the home screen.

## Phosh/Phoc

Continue investigating a legitimate DRM/KMS path in parallel, but never regress the working framebuffer.

Treat these as distinct milestones:

`NUXEL_FRAMEBUFFER_PHONE_UI_READY`

`NUXEL_PHOSH_PHONE_UI_READY`

Do not claim Phosh is operational simply because the Fedora RPMs are installed.

---

# 6. PERMANENT TWRP FAILURE AGREEMENT

**THIS AGREEMENT REMAINS ACTIVE.**

The user will manually restore TWRP whenever an autonomous Nuxel test boot fails.

At mission startup, TWRP is the expected starting state.

After a new candidate is flashed and rebooted, enter:

`AWAITING_BOOT_RESULT`

Record its candidate ID, image hashes and reboot time.

**IF THE USER MANUALLY RETURNS THE SAME SAMSUNG TO TWRP AFTER THAT TEST, THE TEST FAILED.**

Automatically record:

`BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`

`RECOVERY_ACCESS=RESTORED`

`NEXT_ACTION=CAPTURE_FRESH_LOGS`

Then:

1. Capture pstore and last_kmsg.
2. Capture reset reasons.
3. Preserve the raw evidence.
4. Correlate logs with the tested candidate.
5. Identify the failure.
6. Patch the next justified problem.
7. Rebuild and verify.
8. Continue the authorized repair cycle.

Do not ask the user whether the test failed.

Do not require permission for every routine authorized follow-up.

TWRP returning is the agreed failed-test signal; it does not independently establish the root cause.

Once live Nuxel console access is proven, stop using TWRP as the default userspace maintenance environment.

Retain TWRP as the recovery and kernel-update fallback.

---

# 7. AUTONOMOUS DEVELOPMENT AND FLASHING

The user authorizes routine controlled testing on this expendable Samsung S10+.

Allowed:

- Source edits
- Local builds
- Tool installation
- Offline tests
- Recovery ADB diagnostics
- BOOT image replacement
- USERDATA image replacement when necessary
- Full readback verification
- Controlled reboots
- Post-failure log collection
- Live deployments once connectivity works

Hard boundaries:

- Preserve TWRP RECOVERY.
- Preserve EFS and SEC_EFS.
- Preserve bootloader and PIT.
- Do not repartition.
- Do not flash modem firmware.
- Do not change hardware fuses.
- Do not disable critical battery/thermal safety protections.
- Do not flash unrelated partitions.

Before each flash:

- Verify device serial.
- Verify root ADB.
- Verify partition identity and capacity.
- Verify mount state.
- Verify backups.
- Validate candidate image.
- Record SHA-256.

After each flash:

- Verify write success.
- Verify byte count.
- Perform full readback.
- Compare SHA-256.
- Record a flash receipt.

Do not reboot into a candidate with a mismatched readback.

Prefer updating only the affected partition.

Never overwrite the hardware-proven baseline.

After three attempts without meaningful new evidence, improve the diagnostic strategy rather than continuing speculative flashes.

---

# 8. PERSISTENT PROJECT RECORDS

Continue maintaining:

`docs/s10plus-autonomous-boot-repair/`

Update:

- `STATUS.md`
- `ROOT-CAUSE.md`
- `BOOT-STAGES.md`
- `HYPOTHESES.md`
- `PATCHES.md`
- `TEST-RESULTS.md`
- `FLASH-ATTEMPTS.md`
- `DEVICE-OBSERVATIONS.md`
- `LIVE-DEBUG-CONNECTIVITY.md`
- `DISPLAY-BRINGUP.md`
- `NEXT-ACTION.md`

Create or update:

- `NUXEL-MP4-ANIMATION.md`
- `NUXEL-ANIMATION-HANDOFF.md`
- `USB-CONSOLE-ZERO-BYTES-ROOT-CAUSE.md`
- `NUXEL-FEDORA-RUNTIME.md`
- `NUXEL-INTERACTIVE-UI.md`

Every milestone must be supported by actual hardware observations.

Preserve previous source, images and capture history.

Do not invent command results or mark untested hardware features as complete.

---

# 9. EXECUTION ORDER — MANDATORY

Proceed strictly in this order:

**1. ORIGINAL NUXEL MP4 ANIMATION**

Locate the real asset, build a framebuffer-compatible playback solution, verify it offline, deploy, and demonstrate it on the AMOLED.

**2. BIDIRECTIONAL LIVE CONSOLE**

Repair CDC ACM or establish a verified USB networking alternative. Require actual remote command execution.

**3. COMPLETE FEDORA USERSPACE**

Repair and verify services, logs, runtime health and stability.

**4. INTERACTIVE PHONE UI**

Create the real home screen, enable touchscreen, and connect the completed animation-to-UI handoff.

You may perform lightweight prerequisite checks for later priorities, but do not allow a lower-priority architectural project to consume the mission while the higher-priority milestone remains unfinished.

In particular, do not undertake a full DRM kernel port before restoring the original boot animation.

---

# 10. EXECUTE NOW

Start in:

`~/x/nuxel`

The phone is in TWRP with root ADB.

First preserve any outstanding boot evidence.

Then immediately search for and inspect the original Nuxel MP4 animation.

Use FFmpeg or a suitable equivalent to prepare framebuffer-compatible playback.

Preserve the existing first-light penguin as a fallback.

Build the next independently validated candidate.

Flash only the required partitions.

Verify SHA-256 readback.

Reboot and demonstrate the original Nuxel animation on the physical Samsung AMOLED.

After that, fix the live console, stabilize Fedora and deliver the interactive UI.

**PERMANENT AGREEMENT: MANUAL RETURN TO TWRP AFTER A PENDING TEST = THAT TEST FAILED. AUTOMATICALLY COLLECT LOGS, REPAIR AND CONTINUE.**

Do not claim success without evidence.

Do not destroy the working recovery path.

Do not regress the working AMOLED display.

## THE WoNQ MISSION

**FIRST MAKE NUXEL BOOT BEAUTIFULLY.**

**THEN MAKE IT ACCESSIBLE.**

**THEN MAKE FEDORA SOLID.**

**THEN MAKE IT A REAL INTERACTIVE LINUX PHONE.**

🐧🔥 EXECUTE.
