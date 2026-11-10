# PWNAGE-93000 — KICKSTARTER
# Execute FULL-PWNAGE-93000.md

You are executing **PWNAGE-93000** for Nuxel, the custom Fedora-based ARM64 mobile Linux OS.

Your first task is to locate and read `full-pwnage-93000.md` in its entirety. Treat it as the authoritative implementation specification.

## Mission

Deep-analyze the complete current Nuxel codebase, identify the actual active implementations, and implement all four requested improvements:

1. Remove Nuxel's duplicate custom-style launcher icons from GTK and Flatpak applications while preserving their original application icons.
2. Replace the current sound-mode status icon with a clear speaker-based visual system distinguishing Normal, Vibrate and Silent.
3. Implement a complete, persistent notification system, including the notification counter, expanded Quick Settings notification list, swipe-to-archive and swipe-to-mark-read gestures.
4. Fix the intermittent invisible screen/input layer that remains after leaving applications using a single Back-button press and prevents the Home app-drawer gesture from working.

## Mandatory execution rules

- Read the entire full-pwnage-93000.md before modifying anything.
- Deep-analyze the repository, documentation, configuration, runtime services, UI, native components, app registry, tests and build/deployment pipeline.
- Establish which source files and services are actually active on the deployed S10+.
- Do not assume that the highest-numbered source directory is active.
- Trace every requested feature end-to-end, from UI to backend and runtime state.
- Preserve all unrelated functionality.
- Do not replace working implementations unnecessarily.
- Do not introduce mock functionality or UI-only success indicators.
- Add regression tests for every repaired behavior.
- Build and run the relevant test suites.
- Deploy safely to the existing Nuxel S10+ installation when the configured connection is available.
- Physically verify the relevant behavior wherever hardware testing is required.
- Record every blocker honestly.

## Required completion criteria

- GTK and Flatpak launcher entries display their original application icons without an additional Nuxel custom-style duplicate.
- Native Nuxel applications retain their intended custom icons.
- The status bar clearly distinguishes Normal, Vibrate and Silent.
- Notification counts match actual notifications.
- Notifications appear in expanded Quick Settings below the controls and status information.
- Swiping left archives a notification.
- Swiping right marks it read without removing it from the reminder list.
- Notification state survives the appropriate service/UI restarts.
- A single Back press reliably returns to an interactive Home desktop.
- The app drawer can immediately be opened after leaving an application without requiring a forced foreground-app kill.
- No invisible overlay, stale input grab, unmapped-but-intercepting surface or orphaned application state remains.
- Existing lockscreen, Home, Tabs, navigation, app launch, Quick Settings, audio and notifications remain functional.

## Execution

Follow every phase, safety requirement, test and acceptance criterion in `full-pwnage-93000.md`.

Do not stop after producing an analysis report. Implement the fixes, test them, deploy them safely and provide a detailed final report containing:

- Root cause of each issue.
- Files and components changed.
- Architectural decisions.
- Tests added and results.
- Before/after performance measurements where applicable.
- Physical-device test results.
- Remaining blockers.
- Rollback instructions.
- Explicit pass/fail status for every acceptance criterion.

**PWNAGE-93000 is complete only when all four requested improvements work together on the actual Nuxel device.**
