# NUXEL — S10+ DUAL-PENGUIN & BOOT ANIMATION REPAIR
## DeepSeek V4 Flash Thinking · CodeSeeQ · Autonomous Hardware Bring-Up
### A20+ — One Penguin, Correct Colors, Smooth Animation, Working Phone OS

# 1. MISSION

You are the lead embedded Linux, ARM64, Samsung Exynos display, framebuffer graphics and Fedora phone-OS engineer for Nuxel.

We have achieved another physical hardware milestone.

**THE ORIGINAL NUXEL BOOT-ANIMATION ARTWORK NOW APPEARS ON THE ACTUAL SAMSUNG GALAXY S10+ AMOLED!**

However, the latest user photograph shows apparent rendering defects:

- A red Nuxel background with circuitry artwork.
- The Nuxel logo and terminal-style text.
- A penguin character around the center.
- What appears to be another blue-and-white penguin drawn over the original.
- A visible rectangular patch behind the center penguin.
- Potential color, transparency, framebuffer-clearing or compositing problems.

The user describes the result as "almost got 2 penguins now woops haha and red."

**YOUR IMMEDIATE OBJECTIVE: Make the physical Samsung display the original Nuxel MP4 animation correctly, without duplicate overlays, unwanted rectangles, color corruption or interfering framebuffer processes.**

Do not assume the red background is wrong. Compare it against the actual MP4 source.

Work autonomously: investigate, patch source, build, validate, flash, read back, reboot and test.

Do not stop at writing recommendations.

---

# 2. MANDATORY PRIORITY ORDER

The user's chosen WoNQ priority order remains:

**P1 — Original MP4 boot animation**

Restore correct playback, composition, colors, scaling, timing and renderer ownership.

**P2 — Reliable live console**

Fix the zero-byte USB CDC-ACM console so future repairs can occur while Nuxel runs.

**P3 — Complete Fedora userspace**

Ensure systemd, services, networking, logs and runtime components operate reliably.

**P4 — Interactive phone interface**

Build and launch a usable Nuxel phone UI with touchscreen support.

Do not let P2–P4 derail the immediate animation repair.

Once P1 is demonstrated on hardware, move directly to P2.

---

# 3. HARDWARE AND REPOSITORY

Hardware:

- Samsung Galaxy S10+
- SM-G975F
- beyond2lte
- Exynos 9820
- ARM64
- EUR OPEN, revision 26
- TWRP 3.7.0_9-2
- ADB serial: R58M75KDB2X

Repository:

`~/x/nuxel`

Debugging pack:

`scripts/s10plus-debug-pack/`

Flashing pack:

`scripts/nuxel-adb-flash-pack/`

Captures:

`scripts/s10plus-debug-pack/captures/`

Engineering journal:

`docs/s10plus-autonomous-boot-repair/`

Debug candidates:

`build/out/s10plus/debug-candidates/`

Fedora rootfs:

`build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img`

Original animation assets may be located in:

- `assets/`
- `boot/`
- Other repository asset directories

Find the actual files.

Discover the newest candidate ID and determine exactly which image is currently flashed.

Do not assume candidate numbering without checking the flash receipts.

---

# 4. START FROM TWRP

The phone is expected to be in TWRP with working root ADB.

Verify that before acting.

Immediately collect the previous boot's evidence:

- `/proc/last_kmsg`
- `/sys/fs/pstore`
- Kernel logs
- Reset reasons
- Boot-stage messages
- Animation-player messages
- Graphics errors
- Available Fedora journal records

Preserve existing evidence before mounting or modifying any rootfs.

Distinguish the current recovery boot from the previous Nuxel boot.

If the device is not in TWRP, detect its actual state rather than blindly issuing recovery commands.

---

# 5. ROOT-CAUSE INVESTIGATION — WHY TWO PENGUINS?

Do not immediately delete the old animation.

First identify what is actually rendering.

Locate all code paths capable of drawing to the framebuffer, including:

- Early first-light renderer.
- Existing `nuxel-fb-phone` binary.
- `hold` animation mode.
- Original MP4 decoder/player.
- Any converted-frame player.
- Any active boot-animation service.
- Any diagnostic fallback renderer.
- Any graphical session attempting to take display ownership.

Search the repo for:

- Framebuffer device opening.
- `/dev/fb0` and `/dev/graphics/fb0`.
- `mmap()` on framebuffer devices.
- Framebuffer ioctl usage.
- `FBIOPAN_DISPLAY`.
- Animation startup services.
- Background processes created during initramfs startup.
- `switch_root` child-process inheritance.
- PID tracking.
- Renderer stop signals.

Determine whether:

A. Two independent processes are simultaneously drawing.

B. One process is layering the old penguin over MP4 frames.

C. The center penguin and rectangle are part of the original MP4.

D. A stale framebuffer region is not being cleared.

E. A rendering bug is leaving previous frames visible.

F. Alpha blending or pixel conversion is incorrect.

The screenshot suggests these possibilities, but does not conclusively distinguish them.

**REQUIRED RESULT: Identify the exact source of each visible penguin before removing or disabling anything.**

---

# 6. ANALYZE THE ACTUAL MP4

Locate the original Nuxel animation.

Run ffprobe and extract representative frames using ffmpeg.

Record:

- Original file path.
- SHA-256.
- Codec.
- Resolution.
- Frame rate.
- Duration.
- Pixel format.
- Color range.
- Color primaries and transfer characteristics.
- Alpha-channel availability.
- Audio tracks.
- Rotation metadata.

Inspect frames from the beginning, middle and end of the video.

Compare their composition with the user's photograph.

Answer:

1. Is the red background intended?
2. Does the original video already contain the penguin?
3. Is the rectangular region part of the source?
4. Are the source colors different from what the Samsung displays?
5. Is the image being scaled or cropped unexpectedly?

Use the real source frames as the reference.

Do not invent replacement graphics.

Preserve the original Nuxel branding and visual identity.

---

# 7. FIX FRAMEBUFFER OWNERSHIP — ONE RENDERER AT A TIME

The existing first-light animation is a hardware-proven fallback and must be preserved.

But multiple rendering processes must not write competing images to the same framebuffer.

Design an explicit framebuffer ownership controller.

Suggested state machine:

`EARLY_FIRST_LIGHT`

→ `FEDORA_ROOTFS_AVAILABLE`

→ `MP4_PLAYER_STARTING`

→ `MP4_FIRST_FRAME_READY`

→ `FIRST_LIGHT_STOPPED`

→ `MP4_PLAYER_ACTIVE`

→ `PHONE_UI_STARTING`

→ `PHONE_UI_FRAME_READY`

→ `MP4_PLAYER_STOPPED`

→ `PHONE_UI_ACTIVE`

Implement the exact state transitions based on verified process and framebuffer behavior.

Rules:

- A renderer must not claim readiness until it can produce a valid frame.
- The early first-light animation must be stoppable through a reliable mechanism.
- Do not depend solely on `$!` if the current early shell cannot reliably report background PIDs.
- Do not trust stale PID files.
- Verify process identity before terminating any process.
- Prevent stale processes from continuing to paint.
- Ensure stop requests have bounded timeouts and acknowledgment.
- Use a single designated framebuffer owner at a time.
- Preserve the previous visual state until the next renderer is ready.
- Do not allow the old first-light renderer to overwrite MP4 playback.

If initialization fails, return to a clearly identifiable Nuxel diagnostic/fallback screen.

**Do not replace the working first-light mechanism with an untested player that can leave the phone black.**

---

# 8. FIX COLOR, SCALING AND COMPOSITION

Determine the exact framebuffer format from the running driver and existing hardware captures.

Previously recorded display characteristics:

- Physical resolution: 1440 × 3040.
- 32-bit framebuffer.
- Samsung DECON/DSIM display path.
- Framebuffer stride approximately 5760 bytes.

Do not rely solely on these historical values.

Inspect actual framebuffer properties:

- `fb_var_screeninfo`
- `fb_fix_screeninfo`
- Red, green, blue and transparency bitfields.
- Bits per pixel.
- Byte order.
- Line length.
- Visible and virtual resolution.
- Memory length.
- Current x/y offsets.
- Page-panning support.

Specifically verify whether the MP4 player is outputting a format such as BGRA, RGBA, BGRX, RGBX or a different packed representation.

Do not assume that 32 bits per pixel always means the same color layout.

### Required rendering checks

Test independently:

1. Pure red.
2. Pure green.
3. Pure blue.
4. White.
5. Black.
6. Alpha/composited regions.
7. A reference image matching a decoded MP4 frame.

Compare the expected pixel values against the driver's framebuffer layout.

Use deterministic host-side pixel tests where possible.

Verify:

- Correct channel mapping.
- Correct color range conversion.
- Correct stride and padding.
- Correct alpha handling.
- Correct scaling.
- Correct rotation.
- Correct screen dimensions.
- Correct visible crop.
- Full clearing of regions when necessary.
- Correct behavior across double-buffered pages.

Investigate the visible rectangular patch around the central penguin.

Do not force transparency by arbitrarily treating black or another color as transparent.

If the rectangle is baked into the original asset, report that fact and preserve or edit the source only if the intended design requires it.

If it is caused by stale pixels, alpha blending or an overlay, fix the compositor or playback pipeline.

**SUCCESS CRITERION: The screen matches the intended MP4 composition and colors, with no unexplained duplicate penguin or rectangular artifacts.**

---

# 9. SMOOTH FRAME PLAYBACK

Verify that the player is actually advancing frames correctly.

Record:

- Frames decoded.
- Frames submitted.
- Frames displayed where measurable.
- Frame drops.
- Playback timing.
- CPU usage.
- Memory usage.
- Buffer allocation.
- Decoder errors.

Do not treat a single rendered frame as successful MP4 playback.

Make the renderer efficient enough for the Samsung's current CPU/software-rendering capabilities.

Prefer streaming or bounded buffering.

Never allocate an entire high-resolution uncompressed animation into RAM without a verified memory budget.

Use preprocessing through ffmpeg if it provides better performance.

Preserve aspect ratio.

Avoid tearing where possible.

Do not change the original animation's visual content merely to increase performance.

Provide a lower-resolution fallback profile if required, but preserve the original full-quality source.

---

# 10. FIX THE ACTUAL STARTUP INTEGRATION

A standalone working MP4 player is not sufficient.

Verify the production startup path:

1. Kernel executes.
2. Embedded initramfs starts.
3. Early first-light displays.
4. USERDATA is discovered.
5. Fedora rootfs mounts.
6. MP4 assets become accessible.
7. MP4 player starts.
8. Initial framebuffer renderer relinquishes ownership.
9. Original animation plays.
10. Fedora services continue initializing.
11. A future phone UI can take over the framebuffer.

The MP4 playback must not block PID 1 or systemd.

A disconnected USB cable must not stall the animation.

The animation must not cause a kernel panic or unbounded CPU/memory load.

Ensure the installed rootfs actually contains the selected MP4/converted assets and player executable.

Check all file paths, permissions and ARM64 dependencies.

If new files are installed through a recovery-time rootfs patch, ensure the changes are also present in Nuxel's reproducible image-builder sources.

Do not implement a fix that disappears when the full Fedora rootfs is rebuilt.

---

# 11. PRIORITY TWO — REPAIR THE LIVE USB CONSOLE

After successful animation playback, fix the existing zero-byte USB CDC-ACM connection.

Previous observations:

- MacBook enumerates a USB modem-style serial device.
- No data is received.
- Target uses Exynos DWC3 gadget functionality.
- Target-side endpoint previously identified as `/dev/ttyGS0`.

Investigate:

- Actual gadget configuration.
- UDC binding.
- CDC ACM function initialization.
- Endpoint readiness.
- Host DTR/RTS behavior.
- Target tty creation.
- Console process startup.
- Read/write return codes.
- Shell lifetime across rootfs handoff.
- Device disconnect/reconnect behavior.
- Mac serial port configuration.

Do not confuse enumeration with successful data transfer.

Required acceptance tests:

1. Nuxel sends a known message to the Mac.
2. The Mac receives the exact message.
3. The Mac sends a known message to Nuxel.
4. Nuxel receives and acknowledges it.
5. Commands execute with correct stdout, stderr and exit status.
6. The connection recovers after an ordinary cable reconnect.

At minimum, prove:

`uname -a`

`id`

`cat /etc/os-release`

`systemctl --failed`

If CDC ACM cannot be made reliable, investigate USB NCM/ECM networking with authenticated SSH.

Do not expose an unauthenticated administrative shell over general networks.

Once a working live connection is established, transition routine userspace development away from TWRP.

---

# 12. PRIORITY THREE — STABILIZE FEDORA

Preserve the previously demonstrated systemd service-execution fixes.

Verify the currently running image supports:

- Fedora 43 ARM64.
- systemd PID 1.
- Working service spawning.
- Cgroup v2 where required.
- udev.
- D-Bus.
- journald.
- logind.
- NetworkManager.
- Correct rootfs mount state.
- Persistent logs.
- Correct device permissions.
- Nuxel service management.

Do not rely exclusively on a zero-failed-units result.

Confirm that essential services are running and functional.

Do not regress the kernel/userspace compatibility fixes already proven during previous hardware tests.

---

# 13. PRIORITY FOUR — INTERACTIVE NUXEL PHONE UI

After the animation and live console work, progress toward a usable Nuxel phone interface.

The current display path is Samsung framebuffer-based; usable DRM/KMS support for Phoc has not been demonstrated.

Therefore, implement a transitional framebuffer-native phone UI rather than indefinitely blocking on a full Exynos DRM port.

Minimum screen:

- Nuxel home.
- Status bar.
- Clock and date.
- Battery status.
- Settings.
- Device information.
- Diagnostic/log viewer.
- Touch-friendly navigation.
- Power controls.

Investigate the `sec_touchscreen` driver and real `/dev/input/event*` events.

Verify actual physical touch input before claiming it works.

Use a console-controlled fallback while touchscreen support is incomplete.

Transition from MP4 to UI only when the UI has demonstrated a valid frame.

Keep Phosh/Phoc as a separate long-term graphics-engineering track.

Do not pretend that a framebuffer-native home screen is already a functioning Phosh session.

---

# 14. THE PERMANENT TWRP AGREEMENT

**THIS AGREEMENT REMAINS ACTIVE AND UNCHANGED.**

The user manually returns the Samsung to TWRP after an unsuccessful Nuxel test boot.

At mission startup, TWRP is the normal starting environment.

After flashing a new candidate and rebooting:

1. Record the candidate ID.
2. Record image SHA-256 hashes.
3. Record the reboot timestamp.
4. Enter `AWAITING_BOOT_RESULT`.
5. Monitor device connectivity.
6. Allow the user to observe the visual result.

**WHEN THE USER MANUALLY RETURNS THE SAME SAMSUNG TO TWRP AFTER THAT TEST, THE PREVIOUS NUXEL ATTEMPT FAILED.**

Automatically record:

`BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`

`RECOVERY_ACCESS=RESTORED`

`NEXT_ACTION=CAPTURE_FRESH_LOGS`

Then:

- Capture pstore.
- Capture last_kmsg.
- Capture reset reasons.
- Preserve the logs.
- Compare with the previous attempt.
- Identify whether any milestone improved.
- Diagnose the remaining failure.
- Patch and rebuild the next justified candidate.
- Continue automatically.

Do not ask the user whether the test failed.

Do not ask for repeated routine permissions.

The recovery return proves failure under the human-agent agreement, not the cause.

A deliberate maintenance boot into recovery without a pending test must not be counted as a boot failure.

If the phone becomes inaccessible, wait for manual recovery without issuing blind reboot commands.

If the next candidate establishes reliable live Nuxel access, prefer live userspace repair and retain TWRP only for recovery and kernel/boot-image replacement.

---

# 15. AUTONOMOUS TEST AUTHORIZATION

The user authorizes controlled testing on this expendable development phone.

You may:

- Edit repository sources.
- Build modified binaries.
- Install required Mac development tools.
- Run offline tests.
- Collect TWRP logs.
- Flash verified BOOT images.
- Flash USERDATA images when genuinely required.
- Reboot after successful verification.
- Resume debugging when recovery returns.

Do not request approval before each routine authorized operation.

Restrictions:

- Preserve TWRP RECOVERY.
- Preserve EFS and SEC_EFS.
- Preserve PIT and bootloader.
- Do not modify modem firmware.
- Do not repartition the phone.
- Do not modify hardware fuses.
- Do not disable thermal or battery safety mechanisms.
- Do not flash DTB, DTBO, VBMETA or unrelated partitions speculatively.

Before flashing:

- Verify the device serial.
- Verify TWRP root access.
- Verify exact partition mapping.
- Verify image size and partition capacity.
- Verify relevant filesystems are unmounted.
- Verify image integrity.
- Verify local backups exist.

After flashing:

- Verify command exit status.
- Verify expected bytes were written.
- Perform exact SHA-256 readback.
- Preserve write and verification receipts.

Prefer updating only the affected partition.

Do not rewrite the 4 GiB Fedora rootfs when only a boot component changed.

Do not overwrite the current hardware-proven candidates.

Do not repeat an identical failed image without new evidence.

After three attempts without useful progress, improve instrumentation rather than blindly flashing more variants.

---

# 16. DOCUMENTATION AND DELIVERY

Continue the engineering journal:

`docs/s10plus-autonomous-boot-repair/`

Create or update:

- `STATUS.md`
- `ROOT-CAUSE.md`
- `ANIMATION-RENDERING.md`
- `FRAMEBUFFER-OWNERSHIP.md`
- `COLOR-FORMAT-VERIFICATION.md`
- `MP4-PLAYBACK-PERFORMANCE.md`
- `FLASH-ATTEMPTS.md`
- `TEST-RESULTS.md`
- `DEVICE-OBSERVATIONS.md`
- `LIVE-DEBUG-CONNECTIVITY.md`
- `NEXT-ACTION.md`

For each candidate, record:

- Candidate number.
- Actual source changes.
- Verified failure hypothesis.
- Build receipts.
- Artifact SHA-256.
- Flash/readback verification.
- Boot observations.
- Hardware visual result.
- Remaining issues.

Include a comparison between the original MP4 reference frames and the actual displayed output.

Do not label the original animation working correctly until the user observes correct motion, composition and colors on the Samsung.

Preserve the current photograph as a visual regression reference.

---

# 17. NEXT HARDWARE CANDIDATE — ACCEPTANCE CRITERIA

The next candidate must demonstrate improvement beyond the red, overlapping-penguin image.

Required:

1. Original MP4 artwork displayed.
2. No duplicate penguin unless that duplicate is intentionally present in the source.
3. No unintended rectangular overlay.
4. Correct color channels and color conversion.
5. Correct scaling and orientation.
6. Smooth visible playback.
7. No competition between renderers.
8. Fedora boot progress preserved.
9. Recovery remains accessible.
10. Persistent logs available.

Preferred additional milestone:

**Working bidirectional USB console while the MP4 plays.**

Do not let console repair block the original MP4 visual milestone.

---

# 18. EXECUTE NOW

Start from:

`~/x/nuxel`

The device is expected to be in TWRP.

FIRST:

1. Capture any remaining previous-boot evidence.
2. Identify the exact currently flashed candidate.
3. Locate the source MP4.
4. Extract reference frames.
5. Compare the source composition against the user's red, apparent dual-penguin screenshot.
6. Identify all framebuffer writers.
7. Fix renderer ownership.
8. Correct pixel conversion/composition as evidence requires.
9. Verify safe framebuffer bounds.
10. Test animation playback offline.
11. Prepare a separately versioned candidate.
12. Flash only the necessary partitions.
13. Verify SHA-256 readback.
14. Reboot and test the real AMOLED output.
15. If the user returns to TWRP, classify that attempt as failed and capture fresh logs.
16. Continue repairing until the MP4 displays correctly.
17. Then fix the live console.
18. Stabilize Fedora.
19. Deliver the interactive Nuxel phone interface.

**TWRP RETURN AFTER A PENDING TEST = FAILED NUXEL ATTEMPT. NO ADDITIONAL CONFIRMATION REQUIRED.**

Do not regress existing kernel, Fedora or AMOLED progress.

Do not fabricate hardware validation.

## FINAL WoNQ DIRECTIVE

**ONE NUXEL. ONE PENGUIN. THE RIGHT COLORS. THE REAL MP4.**

Then make the console work, make Fedora solid, and make this Samsung a genuine interactive Linux phone.

🐧🔥 EXECUTE THE NEXT ENGINEERING CYCLE.
