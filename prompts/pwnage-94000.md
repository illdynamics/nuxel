# pwnage-94000.md
# NUXEL PWNAGE-94000 — KICKSTARTER

**Mission:** Execute `full-pwnage-94000.md` to completion.

You are working on Nuxel, a custom Fedora-based ARM64 mobile Linux operating system. This is a real device and real operating-system engineering task. Do not treat it as a mockup, a visual-only exercise, or a collection of unrelated CSS fixes.

## 1. Read the full specification first

Before changing anything:

1. Locate and read `full-pwnage-94000.md` in its entirety.
2. Inspect the repository structure, project documentation, architecture notes, configuration, scripts, services, PWA code, native components, and existing tests.
3. Identify the actual running implementations on the device and their corresponding source files.
4. Establish the current Git branch, commit, working-tree state, and any user changes. Do not overwrite unrelated work.
5. Establish the current device identity, connection, Nuxel build, and deployment mechanism before attempting device operations.

Do not start implementation until you understand the existing architecture and have documented the relevant source paths and runtime components.

## 2. Required implementation

Complete all six workstreams:

### A. Doom
- Make Nuxel Doom launch reliably.
- Sound must be enabled by default.
- Verify that sound actually plays through the working Nuxel audio stack.
- Test gameplay, controls, audio, exit, and relaunch on the target device.

### B. Fullscreen top bar
- Remove the incorrect fullscreen-only top bar completely.
- Reuse the same default Nuxel top bar that appears on the desktop.
- Implement the required progressive opening gestures:
  - First downward swipe: standard top bar.
  - Second downward swipe: expanded Quick Settings.
  - Third downward swipe: extended Quick Settings.
- One upward swipe must fully close the entire panel.
- Never require multiple upward swipes to collapse individual levels.
- Improve landscape swipe-up hit areas for both the top bar and bottom navigation controls.

### C. Application startup performance
- Investigate and reduce startup delays for both Flatpak and native applications.
- Measure real cold and warm launch times.
- Identify and remove avoidable bottlenecks without weakening sandboxing or compromising reliability.

### D. Global dark theme
- Make Adwaita dark the default for supported GTK applications, including Flatpak applications.
- Fix applications such as System Monitor that still appear light.
- Verify GTK 3, GTK 4, portals, Flatpak overrides, and application-specific behavior.
- Do not rely on users configuring every app individually.

### E. Invisible surfaces after Back
- Fix the intermittent invisible surface/input-blocking problem when leaving applications using the Back arrow in the triple-button navigation.
- Trace the actual lifecycle, surface ownership, focus, input regions, and cleanup.
- A normal Back press must return the user to a fully interactive desktop.

### F. Desktop vertical-position restoration
- Fix the desktop occasionally returning vertically displaced after closing an app.
- Restore the complete desktop viewport, including the top bar, wallpaper, dock, and bottom triple-button navigation.
- Eliminate the unexplained gap below the four docked icons.
- Verify portrait and landscape behavior.

## 3. Engineering requirements

- Discover the active implementation before modifying code.
- Fix root causes, not symptoms.
- Preserve existing Nuxel visual identity and working functionality.
- Do not introduce a second framebuffer writer.
- Do not replace the existing graphics architecture with software rendering.
- Do not blindly change global display resolution, DPI, or scaling.
- Do not use arbitrary sleep-based lifecycle fixes.
- Do not weaken Flatpak sandboxing.
- Do not globally broadcast synthetic input events.
- Preserve existing audio, Bluetooth, Wi-Fi, lockscreen, launcher, and navigation behavior.
- Keep configuration backward-compatible or provide a migration.
- Add regression tests for every identified issue.
- Record actual test results. Never report a physical test as successful unless it was performed.

## 4. Required workflow

1. Deep source-code and runtime analysis.
2. Document architecture, reproduction steps, root causes, and affected components.
3. Record baseline measurements.
4. Implement the six workstreams in independently testable stages.
5. Run unit, integration, regression, and static checks.
6. Deploy safely to the verified Nuxel device.
7. Physically test the required interactions and applications.
8. Run a cross-feature regression pass.
9. Document changed files, test results, performance measurements, limitations, and rollback instructions.

Do not stop after writing a plan. Implement the fixes.

## 5. Definition of done

The task is complete only when:

- Doom starts reliably with sound enabled by default, and sound is physically verified.
- Fullscreen apps reveal the exact same Nuxel top bar used on the desktop.
- The top bar opens progressively through three downward gestures.
- One upward gesture always fully closes it.
- Landscape top and bottom gesture zones are reliably usable.
- Native and Flatpak application startup performance is measured and improved where a real bottleneck exists.
- Supported GTK 3/GTK 4 and Flatpak applications default to Adwaita dark.
- System Monitor and other previously light applications are checked.
- A single Back press reliably restores an interactive desktop.
- No invisible overlay or stale input region remains.
- The desktop always returns to its correct vertical position.
- The top bar, four docked icons, and triple navigation buttons have the correct positions.
- Existing functionality remains intact.
- The final report clearly separates automated results from physical-device verification.

## 6. Final report

Create a detailed `REPORT-PWNAGE-94000.md` containing:

- Executive summary.
- Root cause for each issue.
- Relevant source files and components.
- Implementation details.
- Tests added and executed.
- Before/after launch measurements.
- Doom audio verification details.
- Portrait and landscape gesture test results.
- GTK/Flatpak theme verification matrix.
- Back/navigation lifecycle test results.
- Desktop geometry and restoration test results.
- Physical device verification.
- Remaining blockers.
- Rollback procedure.

**Start now. Read `full-pwnage-94000.md` completely, investigate the real implementation, and carry out the complete engineering task.**
