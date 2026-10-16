# NUXEL — RESTORE THE REAL UTM LAUNCHER & FINISH THE S10+ PHONE INTERFACE
## DeepSeek V4 Flash Thinking HIGH · CodeSeeQ · Autonomous LIVE Nuxel Engineering
### Correct Launcher → Static Nuxel Wallpaper → Working Touchscreen → Clean Boot Handoff

# 1. PRIMARY MISSION

You are the lead embedded Linux, Fedora ARM64, graphics, application integration and Samsung Exynos 9820 touchscreen engineer responsible for finishing Nuxel on the physical Samsung Galaxy S10+.

Nuxel is our custom Fedora-based Linux PHONE operating system.

**NUXEL ALREADY BOOTS, RUNS FEDORA, DISPLAYS GRAPHICS, PLAYS ITS ORIGINAL BOOT ANIMATION, AND PROVIDES A WORKING LIVE USB CONSOLE.**

We are extremely close to an interactive phone environment.

However, we have three major outstanding problems.

**PRIORITY 1 — THE WRONG NUXEL LAUNCHER IS RUNNING.**

The physical S10+ is currently displaying a simple launcher with only a handful of mostly placeholder application icons and a different theme.

The correct Nuxel launcher ALREADY EXISTS and ALREADY WORKS inside our UTM VM.

It has the proper application grid, search bar, app icons, launcher behavior and Nuxel styling.

Find that exact implementation and get it running on the physical Samsung.

**PRIORITY 2 — SET THE REAL NUXEL BACKGROUND.**

Use:

`./assets/nuxel-background.png`

as the static wallpaper behind the real launcher.

The wallpaper must be visible during normal Nuxel Home operation, not only during the boot animation.

**PRIORITY 3 — GET THE SAMSUNG TOUCHSCREEN WORKING.**

The kernel previously enumerated `sec_touchscreen`, but physical finger input still does not operate the launcher.

Diagnose and repair the actual input pipeline.

In addition, there are two mandatory boot/display corrections:

- Eliminate the flickering/flashing during the second stage of the original Nuxel boot animation.
- Prevent the animation from continuing to draw through or over the launcher after the UI takes control.

These are required to finish the mission, not optional cosmetic tasks.

**ALL ROUTINE WORK MUST OCCUR THROUGH THE RUNNING NUXEL LIVE CONSOLE. DO NOT PLAN A TWRP FLASH.**

Do real engineering, testing and live deployment.

Do not produce another launcher prototype or another replacement dashboard.

---

# 2. STRICT RULE — DO NOT READ OR ANALYZE IMAGES

The user has supplied screenshots to ChatGPT, not to you for visual interpretation.

Your environment does not provide reliable visual-image understanding.

**DO NOT ATTEMPT TO OPEN, VIEW, DESCRIBE, OCR OR VISUALLY INTERPRET SCREENSHOTS.**

Do not use image analysis to determine the intended layout.

Do not attempt visual comparisons or visual similarity scoring.

The source of truth is:

- Actual UTM VM launcher source code.
- VM startup configurations.
- Launcher executable and service definitions.
- Application manifests.
- CSS and theme definitions.
- Launcher asset references.
- Installed packages.
- Runtime process information.
- Hardware logs.

You MAY programmatically inspect technical asset metadata such as file dimensions, pixel formats and checksums.

You MAY decode, convert, package and deploy existing image assets as part of rendering functionality.

Do not attempt to visually interpret their artwork or replace them with invented graphics.

The user will visually verify the final physical interface.

---

# 3. ABSOLUTE NO-REINVENTION REQUIREMENT

We appear to have multiple Nuxel frontend implementations in the repository.

Potential examples:

1. An early diagnostic framebuffer interface.
2. A simplified phone launcher.
3. The actual fully developed launcher used in UTM.

These are hypotheses until you inspect the repository.

**YOUR JOB IS TO IDENTIFY WHICH IMPLEMENTATION ACTUALLY RUNS IN THE UTM VM.**

Do not assume the correct launcher is the one with the most familiar name or the largest number of files.

Do not simply replace the current launcher with another existing executable without proving that it is the VM implementation.

Do not design a fourth launcher.

Do not generate new fake app icons.

Do not create mock applications to simulate success.

The user wants:

**THE SAME NUXEL LAUNCHER IMPLEMENTATION THAT IS ALREADY WORKING IN UTM.**

If it cannot run unchanged because of a specific graphics incompatibility, build the smallest necessary platform adaptation while preserving the authoritative launcher logic and application model.

Do not quietly substitute another interface.

---

# 4. HARDWARE AND PROJECT ENVIRONMENT

Target hardware:

- Samsung Galaxy S10+
- Model SM-G975F
- Codename beyond2lte
- Exynos 9820
- ARM64 / aarch64
- Samsung downstream Linux 4.14.253
- Fedora 43
- systemd 258 with existing compatibility fixes
- Physical AMOLED 1440 × 3040
- Samsung DECON/DSIM framebuffer
- USB CDC-ACM live development console

Repository:

`~/x/nuxel`

Potential launcher implementations to inspect:

`pwa/nuxel-home/`

`shell/nuxel-home-native/`

`vm/`

`images/`

`configs/`

`assets/`

Existing native framebuffer UI:

`tools/s10plus/nuxel-ui.c`

Exact wallpaper:

`assets/nuxel-background.png`

Original animation:

`assets/nuxel-boot-animation.mp4`

Live tools:

`scripts/s10plus-debug-pack/nuxel-live.sh`

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

Engineering records:

`docs/s10plus-autonomous-boot-repair/`

The paths are investigation starting points.

Inspect the actual current repository structure and runtime state before using them.

---

# 5. LIVE-ONLY WORKFLOW

**THE PHONE IS CURRENTLY RUNNING NUXEL. KEEP IT RUNNING.**

Connect to the live Nuxel shell through the MacBook.

Verify:

- Actual phone identity.
- Fedora version.
- Kernel version.
- Current uptime.
- PID 1.
- Current launcher process.
- Active application/animation services.
- Rootfs read-write state.
- Available graphics/input devices.
- Live console stability.

Use the existing host scripts after checking their supported arguments.

The default development loop is:

`INSPECT → PATCH SOURCE → BUILD ARM64 → TEST OFFLINE → LIVE DEPLOY → VERIFY HASH → RESTART AFFECTED SERVICE → VERIFY`

Do not reboot merely to modify:

- Application source.
- Launcher binary.
- Launcher icons.
- Wallpaper.
- Application registry.
- Font assets.
- Systemd service configuration.
- Touchscreen userspace code.
- Boot-animation userspace player.

Do not write the active BOOT block partition from live Linux.

If a change genuinely requires a kernel or embedded-initramfs update, isolate it as a future separately validated maintenance operation rather than performing an unrequested flash.

TWRP remains an emergency recovery option, not the workflow for this mission.

---

# 6. PHASE ONE — LOCATE THE EXACT CORRECT VM LAUNCHER

THIS IS YOUR HIGHEST PRIORITY.

## 6.1 Trace UTM startup from beginning to end

Inspect:

- UTM/VM boot configuration.
- VM image-building scripts.
- VM rootfs overlay.
- Default graphical session.
- Relevant systemd services.
- Launcher executable.
- Launcher process arguments.
- Desktop/session files.
- Launcher packaging.
- Application registry.
- Styling and theme files.

Establish the complete path:

`UTM BOOT → GRAPHICAL SESSION → ACTUAL NUXEL LAUNCHER EXECUTABLE → APPLICATION GRID`

Determine the exact executable, source directory and startup configuration.

Do not guess from filenames.

If the UTM VM can be launched, retrieve process and service information through the VM shell.

Use commands and logs, not screenshots.

## 6.2 Inventory all existing Nuxel launchers

Create a source-derived inventory of launcher candidates.

For each, record:

- Source path.
- Executable name.
- Build system.
- Graphics framework.
- Runtime dependencies.
- Application registry.
- Supported applications.
- Default theme.
- Startup service.
- Target platforms.
- Current deployment status on the S10+.

Identify which launcher is the authoritative UTM version.

Also identify which launcher is currently running on the S10+.

Explain why they differ.

## 6.3 Find why the wrong launcher starts

Inspect:

- `nuxel-ui.service`
- Graphical targets.
- Launcher startup services.
- Postboot supervisors.
- User session services.
- Rootfs build overlay.
- Environment variables.
- Application launch scripts.
- Previous fallback-launcher logic.

Determine whether the wrong launcher was introduced during S10+ hardware bring-up as a temporary framebuffer fallback.

Find the exact configuration responsible for starting it.

Do not delete it immediately.

Preserve it as an emergency diagnostic fallback.

The final startup should launch the authoritative UTM launcher.

## 6.4 Correct the application registry

The user reports missing applications and placeholder icons.

Check whether the physical launcher is:

- Loading the wrong app manifest.
- Loading an incomplete manifest.
- Looking in incorrect asset directories.
- Missing icon files.
- Missing package dependencies.
- Displaying fallback icons because rendering failed.
- Using a different frontend entirely.
- Silently skipping unavailable applications.

Fix the actual issue.

The existing UTM launcher application definitions are authoritative.

Do not manually create a new small list of fake launcher entries.

**GATE P1-A: THE EXACT UTM LAUNCHER SOURCE AND STARTUP PATH ARE IDENTIFIED AND DOCUMENTED.**

---

# 7. PHASE TWO — MAKE THE ACTUAL VM LAUNCHER RUN ON THE S10+

Determine the graphics framework used by the authoritative launcher.

It may involve:

- PWA/browser technologies.
- GTK.
- libadwaita.
- Wayland.
- X11.
- Software rendering.
- A native mobile UI runtime.

Do not assume which one until source inspection proves it.

Compare those requirements with the Samsung's current Fedora runtime.

## 7.1 Preferred strategy — reuse the actual executable

If the existing launcher can execute using an available, supported framebuffer-compatible backend, use it directly.

Install only the required ARM64 runtime components.

Verify the launcher actually starts, loads its apps and produces graphical output.

Do not assume a graphics runtime works merely because its packages install.

## 7.2 If the launcher needs a display server

Identify the exact missing requirement.

Investigate whether a proven framebuffer-compatible display server or software-rendering backend can run it without replacing the kernel.

Test the compatibility layer independently and with bounded resource use.

Do not assume that Wayland, GTK or Chromium can render directly to `/dev/fb0`.

Do not add a full display-server stack without confirming it is compatible with the kernel, userspace and panel.

## 7.3 If direct execution is impossible

Preserve the existing launcher implementation as the authoritative application layer.

Make the minimal required platform adapter or rendering backend.

Reuse:

- Application data structures.
- Application registry.
- Launcher navigation.
- Search logic.
- Theme definitions.
- Existing assets.
- App activation logic.
- User settings.
- Existing UI components wherever portable.

Do not implement another independently designed frontend.

Do not silently claim that a separately rewritten launcher is the exact VM implementation.

Document what code is shared and what hardware-specific adaptation is unavoidable.

## 7.4 Preserve the working display

The phone has a hardware-proven Samsung framebuffer path.

Previous experiments showed that competing `/dev/fb0` clients can trigger DECON panel shutdown.

Do not start a new framebuffer owner while another remains active.

Prepare an explicit transition between the current temporary launcher and the authoritative launcher.

Use a safe, validated ownership handoff.

Keep the live USB console working throughout.

If the new graphical backend fails, automatically recover to the working fallback.

**GATE P1-B: THE AUTHORITATIVE VM LAUNCHER IS RUNNING, WITH ITS REAL APPLICATION REGISTRY, ON THE PHYSICAL S10+.**

---

# 8. PHASE THREE — SET THE EXACT STATIC NUXEL BACKGROUND

The user explicitly wants:

`./assets/nuxel-background.png`

as the normal home-screen background.

**DO NOT USE THE BOOT ANIMATION AS THE HOME-SCREEN BACKGROUND.**

This must be a static wallpaper.

## 8.1 Inspect asset metadata

Verify:

- File exists.
- Exact path.
- Format.
- Resolution.
- Pixel format.
- Transparency.
- File integrity.
- SHA-256.

The asset's artwork is already approved by the user.

Do not generate a replacement.

Do not edit its visual content.

## 8.2 Integrate into the real launcher

Prefer the existing UTM launcher's native wallpaper/background mechanism.

If it already supports background images, configure it to load the specified asset.

If it uses CSS, GTK or another styling system, integrate the exact asset through the appropriate existing mechanism.

If a framebuffer-native adapter is required, decode the PNG and render it as the background layer.

Do not flatten the wallpaper permanently into UI widgets.

Do not confuse it with the boot-animation asset.

## 8.3 Geometry and performance

Fit the wallpaper appropriately to the physical screen.

Respect:

- Aspect ratio.
- Portrait orientation.
- Cutout safe area.
- Screen boundaries.
- Pixel packing.
- Framebuffer stride.
- Rendering memory limits.

Avoid unnecessary full-resolution decoding on every frame.

Cache the decoded or prerendered wallpaper if appropriate.

Do not introduce repetitive disk reads or unnecessary redraw overhead.

## 8.4 Layer ordering

Implement clear render layers:

1. Static Nuxel wallpaper.
2. Launcher application icons and app grid.
3. Status bar.
4. Search and controls.
5. Notifications/overlays.
6. Interaction feedback.

The wallpaper must not obscure text or icons.

Preserve the UTM launcher's intended contrast and styling.

Do not replace the original launcher colors or layout with a new theme.

**GATE P2: THE EXACT EXISTING WALLPAPER IS CONFIGURED AND RENDERED UNDER THE REAL NUXEL LAUNCHER.**

---

# 9. PHASE FOUR — FIX THE REAL SAMSUNG TOUCHSCREEN

This is the third top-level priority and a mandatory hardware acceptance gate.

Previous evidence established that the Samsung kernel can register a `sec_touchscreen` device.

However, physical touch input still does not control Nuxel.

Fix the complete input path:

`SAMSUNG TOUCH HARDWARE → SEC_TS DRIVER → EVDEV → INPUT BACKEND → UTM LAUNCHER`

## 9.1 Identify the active input path

Live-inspect:

- `/proc/bus/input/devices`
- `/sys/class/input/`
- `/dev/input/event*`
- Kernel touchscreen messages.
- Driver probe status.
- Input-open errors.
- IRQ activity.
- Touchscreen power state.
- Normal/charger boot-mode configuration.

Do not assume the touchscreen is always `event2`.

Discover it from device identity and capabilities.

## 9.2 Fix known evdev ioctl mistakes

Earlier source inspection identified malformed ioctl construction in:

`tools/s10plus/nuxel-ui.c`

Review and correct:

- `EVIOCGBIT`
- `EVIOCGABS`
- `EVIOCGNAME`
- `EVIOCGPROP`

Use verified Linux input UAPI definitions compatible with the target ARM64 ABI.

Do not guess request constants.

Compile and test the definitions against target headers.

If the authoritative UTM launcher has a separate input backend, ensure that backend receives the physical input too.

Do not fix only the obsolete fallback launcher.

## 9.3 Capture real physical touch events

Implement a bounded live touch recorder.

Record:

- EV_ABS events.
- ABS_MT_SLOT.
- ABS_MT_TRACKING_ID.
- ABS_MT_POSITION_X.
- ABS_MT_POSITION_Y.
- SYN_REPORT.
- BTN_TOUCH where applicable.
- Input read errors.
- Event timestamps.

The user will provide physical taps and a swipe when requested.

A zero-byte capture is failure evidence, not success.

Determine whether the failure is:

A. Touch controller not producing events.

B. Kernel driver failing after registration.

C. Permissions preventing reads.

D. Invalid ioctl queries.

E. Incorrect userspace event handling.

F. Incorrect input-device selection.

G. Orientation/coordinate mapping.

H. The launcher not consuming the input events.

Diagnose rather than modifying multiple layers blindly.

## 9.4 Type B multitouch handling

Support real multitouch contact lifecycles.

Track slots and tracking IDs.

Do not generate taps using stale coordinates.

Handle contact-down, move, release and frame synchronization correctly.

Avoid ghost touches.

## 9.5 Orientation

The user has physically held the phone sideways for some observations.

Do not confuse the orientation of a photograph with proof that the framebuffer itself is misconfigured.

Inspect actual framebuffer orientation and input coordinate behavior.

The desired normal phone launcher is portrait.

If the graphics backend requires rotation, apply the same coordinate transformation to touch input.

Use the touchscreen's actual ABS min/max range.

Never assume raw coordinates are already 1440 × 3040.

## 9.6 Real touch acceptance

The user must physically:

1. Tap an application.
2. Return Home.
3. Focus search.
4. Scroll/swipe.
5. Open Settings.
6. Navigate back.
7. Open another available application.

Console-injected taps are useful for testing but DO NOT prove touchscreen functionality.

**GATE P3: REAL FINGER INPUT CONTROLS THE AUTHORITATIVE NUXEL LAUNCHER.**

---

# 10. MANDATORY FIX — BOOT ANIMATION FLICKERING

The user reports two separate animation stages.

The original early two-second splash mismatch was fixed.

However, during the second loading stage, the display flashes or flickers noticeably.

Do not rework the already-solved early splash unless new evidence proves regression.

Focus on the second-stage MP4-derived playback and its transition into the launcher.

## 10.1 Determine the actual flicker source

Investigate:

- More than one framebuffer writer.
- MP4 player competing with the launcher.
- Repeated framebuffer opens/closes.
- Samsung DECON release/power behavior.
- Buffer page alternation.
- Incomplete frame clears.
- Inconsistent pixel formats.
- Framebuffer panning.
- Incorrect virtual-resolution offsets.
- Renderer restarts.
- Process crash/restart loops.
- Panel blank/unblank calls.
- Excessive frame timing jitter.
- Display power-management changes.

Do not treat all visible flashing as a video-decoding problem.

Check the actual kernel and application logs.

## 10.2 Single framebuffer owner

Implement or verify exclusive display ownership.

The system must never allow the MP4 animation player and launcher to actively draw conflicting frames.

Use a robust ownership lock or supervisor.

Prevent stale PID files or competing services from creating duplicate writers.

Verify process identity before sending termination signals.

Do not run a second framebuffer diagnostic application while the screen is active.

## 10.3 Correct framebuffer handoff

Use explicit stages:

`EARLY_FIRST_FRAME`

→ `ORIGINAL_ANIMATION_RUNNING`

→ `LAUNCHER_STARTING`

→ `LAUNCHER_READY`

→ `ANIMATION_STOP_REQUESTED`

→ `ANIMATION_STOP_CONFIRMED`

→ `LAUNCHER_DISPLAY_OWNER`

Do not assume an application is ready because its process exists.

Require actual graphical readiness.

Do not stop the animation solely after an arbitrary delay.

Do not let the player continue displaying frames after ownership transfers.

If the launcher fails, maintain a controlled fallback display and usable live console.

## 10.4 Smooth playback

Measure:

- Source frame rate.
- Actual frame submission intervals.
- Dropped frames.
- Decoder timing.
- CPU utilization.
- Memory allocation.
- Framebuffer buffer transitions.
- Repeated hardware blank/unblank.
- Player process restarts.

Use monotonically scheduled playback.

Avoid unnecessary panel reinitialization.

Preserve correct aspect ratio and color packing.

Do not redesign or replace the original MP4.

**ANIMATION SUCCESS: SMOOTH PLAYBACK, NO UNEXPLAINED FLASHING, AND NO FRAMES APPEARING OVER THE LAUNCHER.**

---

# 11. MANDATORY FIX — ANIMATION VISIBLE THROUGH THE LAUNCHER

The user reports that portions of the animation appear to continue through or behind the launcher.

Possible causes include:

- Animation process not actually stopping.
- Framebuffer pages retaining old data.
- Wrong display page selected.
- Launcher not repainting opaque background regions.
- Incomplete framebuffer clearing.
- Animation/launcher sharing memory without exclusive ownership.
- Rendering synchronization errors.
- A transparent UI layer exposing previous frames.

Investigate the actual implementation.

Do not assume which of these is responsible.

Once the launcher becomes the active display owner:

- The original static Nuxel wallpaper should occupy the home background.
- No boot-animation content should be visible.
- No stale frames should remain in other virtual pages.
- No second renderer should write to the framebuffer.
- Launcher redraws must be deterministic.
- The animation should not restart behind the UI.

Test the handoff repeatedly without rebooting whenever the active runtime allows it.

Capture process state and framebuffer ownership logs.

Do not use a second framebuffer client as a diagnostic shortcut.

---

# 12. KEEP THE AUTHORITATIVE LAUNCHER'S APPS

Do not produce another small list of placeholder icons.

Find the VM's actual application registry.

For each application, preserve:

- ID.
- Name.
- Existing icon asset.
- Launch command.
- Ordering.
- Categories.
- Availability conditions.
- Search metadata.
- Application behavior.

Determine why the current phone launcher appears to have only a few applications with placeholder graphics.

Possible causes:

- Wrong launcher.
- Wrong app registry.
- Missing icon assets.
- Missing asset loader.
- Missing runtime dependencies.
- Incomplete rootfs installation.
- Failed icon decoding.
- Incorrect path prefixes.
- Unsupported graphics backend.

Fix the underlying cause.

Do not invent substitute icons.

Do not silently claim applications work because an icon appears.

Launch actual available applications and verify their processes and user-visible functionality.

Apps requiring unsupported hardware should report that limitation rather than pretend to function.

---

# 13. LIVE DEPLOYMENT REQUIREMENTS

All launcher, wallpaper, touchscreen userspace and animation player fixes should be deployed through the functioning live console.

For each update:

1. Preserve the currently working application.
2. Record its SHA-256.
3. Build a new ARM64 artifact.
4. Run tests.
5. Transfer into a staging directory.
6. Verify complete target-side SHA-256.
7. Atomically activate.
8. Restart only the affected services.
9. Verify the live console remains functional.
10. Verify runtime health.
11. Roll back if needed.

Do not replace running executables in place.

Do not flash the complete 4 GiB rootfs for a small application update.

Keep all live fixes represented in repository source and Fedora rootfs build scripts.

If launcher assets are stored in a separate path, preserve correct permissions and ownership.

---

# 14. AUTOMATED TESTS WITHOUT IMAGE INTERPRETATION

You may run deterministic tests.

Examples:

- Launcher source identification.
- Startup service checks.
- ELF architecture checks.
- Runtime dependency checks.
- App registry consistency.
- Icon asset existence.
- Image-format metadata.
- Wallpaper decode success.
- Input ioctl ABI tests.
- Raw evdev capture.
- Display ownership tests.
- Service start/stop tests.
- Framebuffer bounds tests.
- Pixel-format conversion tests.
- Boot-animation stop acknowledgment.
- Live-console reconnection.
- Atomic deployment rollback.

Do not perform visual screenshot interpretation.

Do not claim visual success from framebuffer memory alone.

For physical appearance, ask the user for a concise visual confirmation after deployment.

Limit questions to genuine manual hardware checks.

---

# 15. RELEASE ACCEPTANCE GATES

## GATE 1 — REAL LAUNCHER

The exact UTM launcher implementation has been identified and made operational on the S10+ through a verified compatible graphics path.

The correct application registry loads.

No fabricated placeholder launcher replaces it.

## GATE 2 — WALLPAPER

`assets/nuxel-background.png` is used as the static home wallpaper.

No boot-animation frames appear behind the launcher.

## GATE 3 — TOUCHSCREEN

Physical finger taps and swipes reach the real launcher.

Coordinate mapping and navigation are correct.

## GATE 4 — ANIMATION

Original animation plays smoothly.

No second-stage flickering.

No renderer collision.

Clean stop before launcher ownership.

## GATE 5 — APPS

Available Nuxel applications launch through the original launcher.

Unavailable hardware functionality is honestly reported.

## GATE 6 — LIVE RUNTIME

Fedora remains running.

Live USB console remains accessible.

Launcher survives normal use.

No unexpected resets or panel shutdown.

No routine TWRP requirement.

---

# 16. PROGRESS DOCUMENTATION

Create:

`docs/s10plus-autonomous-boot-repair/REAL-LAUNCHER-PORT/`

Maintain:

- `LAUNCHER-INVENTORY.md`
- `UTM-AUTHORITATIVE-LAUNCHER.md`
- `S10PLUS-LAUNCHER-ROOT-CAUSE.md`
- `GRAPHICS-BACKEND-COMPATIBILITY.md`
- `APP-REGISTRY.md`
- `WALLPAPER-INTEGRATION.md`
- `TOUCHSCREEN-DIAGNOSIS.md`
- `TOUCHSCREEN-HARDWARE-TESTS.md`
- `ANIMATION-FLICKER-ROOT-CAUSE.md`
- `FRAMEBUFFER-OWNERSHIP.md`
- `LIVE-DEPLOYMENT-RESULTS.md`
- `HARDWARE-ACCEPTANCE.md`
- `REMAINING-BLOCKERS.md`

For each change record:

- Actual defect.
- Supporting source or hardware evidence.
- Files changed.
- Build commands.
- Exit codes.
- Installed artifact hash.
- Test results.
- Physical hardware result.
- Rollback method.

Do not claim completion based only on source-code edits.

---

# 17. EXACT EXECUTION ORDER

**START NOW ON THE LIVE-BOOTED SAMSUNG.**

Follow this order:

### PRIORITY 1 — THE REAL LAUNCHER

1. Verify live console.
2. Preserve current working state.
3. Discover all launcher implementations.
4. Trace the exact UTM startup process.
5. Identify the authoritative launcher.
6. Identify the current physical launcher.
7. Determine why the wrong launcher starts.
8. Identify actual graphics dependencies.
9. Select the smallest compatible execution path.
10. Deploy the authoritative launcher or necessary platform adaptation.
11. Restore original application registry.
12. Restore actual application icons.
13. Verify launcher startup and app availability.

### PRIORITY 2 — STATIC BACKGROUND

14. Locate `assets/nuxel-background.png`.
15. Verify metadata and integrity.
16. Integrate it into the authoritative launcher.
17. Preserve aspect ratio and geometry.
18. Render as a static wallpaper behind launcher content.
19. Prevent stale animation pixels from appearing beneath it.

### PRIORITY 3 — TOUCHSCREEN

20. Inspect `sec_touchscreen` status.
21. Correct known evdev ioctl issues.
22. Discover actual input device.
23. Capture raw physical touch events.
24. Diagnose missing events if necessary.
25. Implement correct multitouch handling.
26. Calibrate orientation and coordinate mapping.
27. Connect touch events to the real launcher.
28. Verify physical application selection and swiping.

### MANDATORY DISPLAY/BOOT CLEANUP

29. Trace animation and launcher framebuffer ownership.
30. Identify the cause of the second-stage flicker.
31. Eliminate competing renderers.
32. Correct buffering or power transitions as evidence requires.
33. Require clean animation-stop acknowledgment.
34. Ensure the static wallpaper replaces every stale animation page.
35. Verify smooth playback and clean launcher handoff.

### FINAL VALIDATION

36. Verify the correct launcher is the default at startup.
37. Verify original app entries and icons.
38. Verify the static wallpaper persists.
39. Verify the touchscreen.
40. Verify actual application launch behavior.
41. Verify live-console access and Fedora health.
42. Preserve all fixes in reproducible builds.
43. Document any remaining true kernel/graphics blockers.

Do not stop after installing a package.

Do not stop after making a substitute launcher look similar.

Do not stop after registering a touchscreen device.

Do not stop after recording a single successful animation frame.

**THE TARGET IS A WORKING NUXEL PHONE ENVIRONMENT, NOT ANOTHER BRING-UP DEMONSTRATION.**

---

# 18. FINAL DIRECTIVE

We already have the correct launcher in UTM.

We already have the correct wallpaper.

We already have the original boot animation.

We already have Fedora and a working AMOLED display.

We already have a live USB console.

**STOP RECREATING COMPONENTS THAT ALREADY EXIST.**

Use the original launcher.

Use the original application registry.

Use the original assets.

Set `assets/nuxel-background.png` as the static background.

Fix the Samsung touchscreen.

Fix the remaining boot-animation flickering.

Make the animation stop before it can overwrite the launcher.

Do everything possible directly through live Nuxel without TWRP.

## FINAL WoNQ OBJECTIVE

**SAMSUNG BOOT → SMOOTH ORIGINAL NUXEL ANIMATION → REAL UTM NUXEL LAUNCHER → STATIC NUXEL WALLPAPER → REAL APPS → PHYSICAL TOUCHSCREEN CONTROL.**

NO FAKE ICONS.

NO EXTRA LAUNCHERS.

NO BOOT ANIMATION BLEED-THROUGH.

NO GLITCHY FLICKERING.

NO UNNECESSARY FLASHING.

NO SCREENSHOT ANALYSIS.

**MAKE THE EXISTING NUXEL PHONE OS WORK AS THE SAME SYSTEM ON UTM AND ON THE REAL GALAXY S10+.**

🐧🔥 EXECUTE THE LIVE ENGINEERING MISSION.
