# NUXEL — PORT THE EXISTING WORKING UTM LAUNCHER TO THE GALAXY S10+
## DeepSeek V4 Flash Thinking · CodeSeeQ · Autonomous Live Engineering
### NO REDESIGN · NO IMAGE ANALYSIS · NO NEW LAUNCHER

# 1. ABSOLUTE PRIMARY DIRECTIVE

You are the lead embedded Linux, ARM64, Samsung Exynos 9820, Fedora graphics and touchscreen engineer responsible for completing Nuxel on the physical Samsung Galaxy S10+.

**CRITICAL CORRECTION FROM THE USER:**

THE REAL NUXEL LAUNCHER ALREADY EXISTS.

IT IS ALREADY IMPLEMENTED.

IT ALREADY WORKS ON THE UTM VIRTUAL MACHINE.

**DO NOT CREATE ANOTHER LAUNCHER. DO NOT REDESIGN IT. DO NOT REPLACE IT WITH A DIFFERENT FRAMEBUFFER HOME SCREEN.**

Your task is to locate the exact launcher running successfully in the UTM VM, understand how it is started, and get that same launcher implementation running on the Samsung S10+.

The user has already provided visual references to ChatGPT. You do NOT need to inspect them.

**DO NOT ATTEMPT TO OPEN, READ, DECODE, ANALYZE OR INTERPRET ANY SCREENSHOT OR IMAGE FILE TO UNDERSTAND THE DESIRED LAUNCHER.**

You have full source code, startup scripts, configuration files, application manifests, assets and VM infrastructure available in the repository.

Use those as the authoritative source of truth.

The mission is an engineering port, not a design project.

---

# 2. EXACT OBJECTIVES

Follow this priority order:

**P0 — FIX THE PHYSICAL TOUCHSCREEN.**

Get actual finger taps, gestures and swipes working through Linux input devices.

**P1 — RUN THE EXISTING UTM NUXEL LAUNCHER ON THE S10+.**

Locate the exact working implementation and reuse it rather than developing another launcher.

**P2 — FIX THE REQUIRED GRAPHICS AND RUNTIME COMPATIBILITY.**

Make the real launcher work with the physical phone's ARM64 hardware and available graphical environment.

**P3 — MAKE EXISTING NUXEL APPLICATIONS LAUNCH PROPERLY.**

Restore the launcher-to-application execution path and genuine application functionality.

**P4 — COMPLETE NORMAL STARTUP AND RUNTIME STABILITY.**

Make Fedora automatically transition from the original Nuxel boot animation into the working launcher.

Do not waste development time on unrelated features.

---

# 3. WORK LIVE — DO NOT RETURN TO TWRP UNNECESSARILY

The physical S10+ currently has:

- A working Samsung ARM64 kernel.
- Fedora 43 root filesystem.
- Running systemd.
- Operational AMOLED framebuffer.
- Working Nuxel boot animation.
- An existing basic framebuffer UI.
- A working USB live console.
- Live userspace deployment tools.

Use the running Nuxel environment.

Repository:

`~/x/nuxel`

Live tooling:

`scripts/s10plus-debug-pack/nuxel-live.sh`

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

Current phone UI implementation:

`tools/s10plus/nuxel-ui.c`

The existing framebuffer interface is currently useful as a diagnostic/recovery interface. It is NOT the final launcher requested by the user.

Keep it available as a fallback until the original launcher is running.

Do not reboot into TWRP to update application binaries, assets, launcher configuration or ordinary userspace components.

If a kernel or embedded-initramfs change is genuinely necessary, identify and document the requirement separately.

---

# 4. FIND THE ACTUAL UTM LAUNCHER — FROM SOURCE CODE ONLY

Inspect the repository to determine precisely which launcher runs in UTM.

Start by searching:

`pwa/nuxel-home/`

`shell/nuxel-home-native/`

`vm/`

`images/`

`configs/`

`assets/`

Also inspect:

- UTM boot scripts.
- VM image-building scripts.
- VM systemd services.
- Desktop/session files.
- GTK application entry points.
- Browser/PWA launch commands.
- Launcher configuration.
- Application registry.
- Dependency manifests.
- Packaging scripts.
- Installation scripts.

These are candidate locations, not assumptions about the actual authoritative launcher.

## Mandatory discovery questions

Answer using code and configuration evidence:

1. Which exact executable or application runs as the Nuxel launcher inside UTM?
2. Which process launches it?
3. Which service starts it?
4. Which source directory builds it?
5. Which graphical framework does it use?
6. Which libraries does it require?
7. Which graphics/display backend does it require?
8. Which application manifest does it use?
9. Where are its icons and assets loaded from?
10. Which input handling mechanism does it use?
11. How does it launch applications?
12. What differences exist between the UTM runtime and the S10+ Fedora runtime?

Find the actual VM startup entry point rather than assuming the PWA or GTK launcher is the correct one.

Trace:

**UTM BOOT → USER SESSION → LAUNCHER STARTUP → RUNNING APPLICATION**

Write down the exact service names, commands and dependencies.

Do not build a replacement launcher during this discovery.

---

# 5. STRICT NO-IMAGE-ANALYSIS RULE

You do not have image-reading capabilities in this execution environment.

Do not:

- Open screenshots to inspect their visual appearance.
- Ask image tools to describe the interface.
- Attempt OCR.
- Perform automated visual comparisons requiring image interpretation.
- Infer the UI's design from photographs.
- Build a new design based on descriptions of screenshots.
- Generate replacement UI mockups.

Instead, inspect:

- Source code.
- CSS/GTK styling definitions.
- Configuration files.
- Application registry.
- Icon paths.
- Build scripts.
- Runtime dependencies.
- Service files.
- Input handlers.
- Logs and process state.

You may copy, package, convert or deploy image assets programmatically where needed for compatibility, but do not attempt to interpret their visual content.

The existing VM implementation defines what the launcher should be.

The user can visually confirm the physical result when necessary.

---

# 6. DETERMINE WHETHER THE EXISTING LAUNCHER CAN RUN DIRECTLY

The physical Samsung uses an Exynos framebuffer graphics path.

The VM may use a more complete graphical environment.

Determine exactly what the existing launcher requires.

Investigate:

- GTK version.
- libadwaita dependencies.
- Wayland requirements.
- X11 requirements.
- Chromium/PWA requirements.
- EGL/GBM requirements.
- DRM/KMS requirements.
- Software rendering support.
- Input backend.
- Display server.
- Window/session management.

Compare them against the running S10+:

- Linux 4.14.253.
- Fedora 43 ARM64.
- Samsung DECON framebuffer.
- Available `/dev/fb*` devices.
- Available `/dev/dri/*` devices.
- Installed Mesa components.
- Available graphics libraries.
- Available input devices.

## Decision order

**OPTION A — RUN THE ORIGINAL LAUNCHER DIRECTLY.**

If the required graphics framework can run on the current physical device through a supported backend, use it.

This is the preferred outcome.

**OPTION B — ADD A COMPATIBILITY LAYER.**

If the launcher requires a display/session component missing from the Samsung environment, investigate whether a suitable framebuffer-compatible display bridge can support the original executable.

Examples to evaluate, only when technically justified:

- A framebuffer-compatible X server.
- Software-rendered compositing.
- A verified Wayland-on-fbdev solution.
- An existing supported embedded graphical backend.

Do not assume these work without testing.

Prefer established, maintainable components over custom display-server rewrites.

**OPTION C — REUSE THE ORIGINAL IMPLEMENTATION WITH A MINIMAL PLATFORM ADAPTER.**

If the exact executable cannot run because of unavoidable graphical backend limitations, reuse the real launcher source, application model, styling definitions and assets, introducing only the minimum necessary platform-specific integration.

Do not create an independently designed replacement.

If a full source-level port would require substantial rewriting, document the obstacle and present the precise technical limitation rather than silently producing another unrelated launcher.

**THE RESULT MUST REMAIN THE EXISTING NUXEL LAUNCHER, NOT A THIRD UI DESIGN.**

---

# 7. PRIORITY ZERO — FIX THE TOUCHSCREEN FIRST

The Samsung kernel has previously enumerated:

`sec_touchscreen`

But physical touch input does not yet control the UI reliably.

Investigate the complete pipeline:

TOUCH CONTROLLER → KERNEL INPUT DRIVER → EVDEV → APPLICATION INPUT → GUI

## 7.1 Fix existing evdev ioctl issues

Inspect:

`tools/s10plus/nuxel-ui.c`

Previous review identified incorrectly constructed evdev ioctl requests.

Verify and correct:

- `EVIOCGBIT`
- `EVIOCGABS`
- `EVIOCGNAME`
- `EVIOCGPROP`

Use appropriate Linux input UAPI definitions.

Add tests against the ARM64 target ABI.

Do not rely on guessed ioctl numbers.

## 7.2 Verify the hardware input device

Live-inspect:

`/proc/bus/input/devices`

`/sys/class/input/`

`/dev/input/event*`

Relevant kernel logs.

Identify the actual touchscreen by capabilities, not only by event number.

Check:

- Device registration.
- Multitouch axes.
- Contact tracking IDs.
- Input permissions.
- Touchscreen power state.
- Normal boot/charger-mode behavior.
- Driver open/resume errors.
- Interrupt behavior.

## 7.3 Capture actual physical touches

Run a bounded raw event capture.

Ask the user to tap several places and perform one swipe when the capture is ready.

Require genuine physical events.

Do not infer successful input merely because the device node exists.

If events are missing, determine whether the failure is in the kernel driver, input-device setup, permissions or userspace event reader.

Do not modify hardware regulators blindly.

## 7.4 Correct touch-event processing

Support Linux multitouch Type B:

- ABS_MT_SLOT.
- ABS_MT_TRACKING_ID.
- ABS_MT_POSITION_X.
- ABS_MT_POSITION_Y.
- SYN_REPORT.
- BTN_TOUCH where applicable.

Track contact lifecycle correctly.

Avoid ghost taps and stale coordinates.

Use the actual axis min/max values.

Apply the correct orientation mapping.

Test portrait and landscape where supported.

## 7.5 Connect touch to the ORIGINAL launcher

Do not fix touch only in the temporary diagnostic UI.

The final touchscreen integration must deliver physical events into the actual UTM-derived launcher.

Verify real taps, swipes and app selection.

Keep the live USB console as a fallback input mechanism.

---

# 8. USE THE ORIGINAL APPLICATION REGISTRY

The existing launcher already knows which applications belong in Nuxel.

Find the original application definitions.

Reuse:

- App identifiers.
- Display names.
- Icons.
- Categories.
- Launch commands.
- Search index.
- Application ordering.
- Settings integration.
- Navigation behavior.

Do not invent a new app grid or replace the app registry.

Verify that applications present in the UTM environment also have the correct dependencies installed on the S10+.

Distinguish:

- App installed and working.
- App installed but missing a compatible graphics backend.
- App installed but hardware functionality unavailable.
- App not installed.
- App currently unsupported.

Restore real functionality wherever possible.

Do not claim telephony, camera or other hardware-dependent functionality works without actual hardware verification.

---

# 9. PRESERVE THE REAL NUXEL DESIGN

The UTM launcher is the design authority.

Use its existing source styles and assets.

Do not:

- Redesign the home screen.
- Create another theme.
- Replace the app grid.
- Replace its icons.
- Change the Nuxel branding.
- Introduce a new diagnostic dashboard as the default home screen.
- Recreate widgets that already exist.

Only modify UI presentation where necessary for:

- Physical resolution.
- ARM64 compatibility.
- Screen cutout.
- Display orientation.
- Touch input.
- Performance.
- Safe areas.
- Mobile device configuration.

The goal is behavioral and visual parity with the existing launcher, subject to the physical display capabilities.

No image-analysis tools are needed to accomplish this.

---

# 10. AUTOMATIC STARTUP

The existing physical boot sequence is:

SAMSUNG BOOTLOADER

→ NUXEL ORIGINAL BOOT ANIMATION

→ FEDORA SYSTEMD

→ BASIC FRAMEBUFFER UI

Change the final stage to:

**ORIGINAL NUXEL UTM LAUNCHER**

Preserve the working animation.

Required behavior:

1. Fedora reaches the appropriate runtime state.
2. The real launcher service starts.
3. The launcher initializes its graphics environment.
4. The launcher loads its existing application definitions.
5. The launcher becomes ready to display.
6. The boot animation relinquishes framebuffer ownership.
7. The original Nuxel launcher becomes visible.
8. Physical touchscreen input reaches the launcher.

Do not stop the animation before the launcher is ready.

Avoid competing framebuffer owners.

Retain the current basic UI as a fallback for failed launcher startup.

---

# 11. LIVE DEVELOPMENT AND TESTING

Use CodeSeeQ and the working USB console.

Workflow:

SOURCE INSPECTION → BUILD → DEPLOY → VERIFY → TEST → FIX

For each deployment:

1. Build for Fedora ARM64.
2. Verify ELF architecture and dependencies.
3. Preserve the previous working version.
4. Transfer through the verified live channel.
5. Verify destination SHA-256.
6. Atomically activate where possible.
7. Restart only affected services.
8. Verify actual runtime behavior.
9. Roll back if startup fails.

Do not reflash the rootfs for ordinary application changes.

Do not rebuild BOOT for icon, CSS, launcher configuration or input-userland changes.

Do not interrupt the live console unnecessarily.

Preserve all changes in the repository and reproducible image builders.

---

# 12. INPUT AND LAUNCHER ACCEPTANCE TESTS

Test the following on the physical Samsung.

## Touchscreen

- Physical tap detected.
- Tap position correct.
- Swipe detected.
- Release detected.
- No ghost taps.
- No incorrect rotated coordinates.

## Launcher

- Original launcher process starts.
- Application registry loads.
- Launcher home displays.
- Application search works.
- App icons are selectable.
- At least the existing supported applications can launch.
- Home/back behavior works.
- Settings opens.
- The launcher remains responsive.

## Runtime

- Fedora remains running.
- Nuxel live console remains accessible.
- No duplicate display processes.
- No unexpected framebuffer shutdown.
- No uncontrolled reboot.
- Launcher starts automatically after boot.

## Consistency with UTM

Verify from source and configuration that the physical phone uses the same authoritative launcher implementation, app registry, theme and assets.

Do not invent a visual similarity score.

The user will confirm the physical visual result.

---

# 13. DOCUMENTATION

Create:

`docs/s10plus-autonomous-boot-repair/UTM-LAUNCHER-PORT/`

Document:

- Exact VM launcher executable.
- Exact source path.
- VM startup configuration.
- Graphical framework.
- Required dependencies.
- S10+ compatibility gaps.
- Changes needed to run on ARM64 hardware.
- Shared launcher assets and application registry.
- Touchscreen root cause.
- Live deployment results.
- Physical test results.
- Remaining limitations.

Only document facts established through source, tool output or hardware logs.

---

# 14. AUTONOMY AND HARDWARE LIMITS

You may autonomously:

- Inspect repository code.
- Build packages.
- Install development dependencies.
- Modify userspace.
- Deploy changes live.
- Restart application services.
- Capture input logs.
- Test launcher functionality.
- Iterate until the defined acceptance criteria pass.

Do not request routine permission for these authorized development steps.

Do not:

- Flash unrelated partitions.
- Overwrite recovery.
- Modify EFS or radio calibration.
- Modify the bootloader or PIT.
- Disable battery or thermal protections.
- Replace the working kernel speculatively.
- Start destructive recovery operations without a justified need.

If a genuine kernel-level blocker is discovered, document the exact evidence and propose a separately validated update.

---

# 15. EXACT EXECUTION ORDER

**START NOW ON THE BOOTED NUXEL PHONE.**

1. Verify the live console.
2. Identify the exact UTM launcher process and source.
3. Trace its startup and runtime dependencies.
4. Determine whether it can run unchanged on the S10+.
5. Fix the known touchscreen ioctl defects.
6. Capture real physical touchscreen input.
7. Correct input mapping and multitouch handling.
8. Choose the minimum required graphics compatibility solution.
9. Install any compatible runtime dependencies.
10. Build/deploy the actual launcher.
11. Reuse its original application registry and assets.
12. Connect real touchscreen input.
13. Launch available Nuxel applications.
14. Replace the basic framebuffer UI as the default screen.
15. Preserve the existing animation handoff.
16. Test automatic launcher startup.
17. Verify the physical phone remains stable.
18. Document remaining unsupported hardware functions.

Do not stop after creating another launcher mockup.

Do not generate an alternative UI.

Do not attempt screenshot analysis.

Do not recreate a system that already exists.

---

# FINAL DIRECTIVE

**THE NUXEL LAUNCHER IS ALREADY DONE.**

**IT ALREADY WORKS ON THE UTM VM.**

YOUR JOB IS TO GET THAT SAME IMPLEMENTATION WORKING ON THE GALAXY S10+.

Reuse the code.

Reuse the apps.

Reuse the icons.

Reuse the UI.

Fix the missing graphics compatibility.

Fix the physical touchscreen.

Make the real launcher start automatically.

Keep the existing Fedora system stable.

## FINAL ACCEPTANCE

**SAMSUNG BOOTS → NUXEL ANIMATION PLAYS → ORIGINAL UTM LAUNCHER STARTS → TOUCHSCREEN WORKS → REAL APPLICATIONS OPEN.**

**NO NEW LAUNCHER. NO REDESIGN. NO IMAGE ANALYSIS.**

PORT THE EXISTING WORKING SYSTEM.

🐧🔥 EXECUTE.
