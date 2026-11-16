# pwnage-99000.md — Kickstarter: Fix and Fully Verify USB-C HDMI on Nuxel

## Mission

Execute `full-pwnage-99000.md` from beginning to end.

Fix Nuxel's USB-C-to-HDMI external-display functionality on the Samsung Galaxy S10+ (SM-G975F, `beyond2lte`, Exynos 9820).

**Important: an HDMI display is currently connected to the phone. Treat this as the live hardware test setup.** Do not casually disconnect the cable, reboot unnecessarily, restart the entire graphics stack, or change display configuration in a way that loses the active test connection. Inspect the current state first and preserve the working SSH connection.

The objective is not merely to detect an HDMI monitor. The objective is to make the external display genuinely usable, with:

1. A working mirrored-screen mode.
2. A working independent/separate-desktop mode.
3. Correct orientation handling in both modes.
4. An actionable notification whenever an HDMI display is newly connected, offering both modes.
5. Working HDMI audio, physically verified through the connected display.
6. Reliable disconnect/reconnect behavior.
7. No regressions to the built-in phone display, touch input, compositor, navigation, audio, or normal Nuxel operation.

## Execution instructions

1. Read `full-pwnage-99000.md` completely before making changes.
2. Inspect the actual source code, active graphics architecture, current runtime, and connected HDMI hardware.
3. Identify the real cause of the current HDMI failure. Do not guess.
4. Implement the complete solution, including required UI, display-management, input, orientation, and audio integration.
5. Use existing deployment scripts in `./scripts` after inspecting their behavior.
6. Deploy safely to the connected S10+.
7. Keep working until the external display has been physically verified in both modes and HDMI audio has been physically verified.
8. Test a real disconnect/reconnect and verify that the mode-selection notification appears again.
9. Produce `REPORT-PWNAGE-99000.md` with evidence, test results, limitations, and any genuinely unresolved blockers.

## Mandatory live verification

The currently connected HDMI display must be used for testing. Do not mark the task complete based only on source inspection, successful compilation, detected connectors, EDID information, a PipeWire sink, or screenshots from the internal display.

Verify all of the following:

- The external display receives a valid picture.
- Mirroring visibly works.
- Separate-desktop mode visibly works and can be used independently.
- Portrait and landscape orientation changes are handled correctly.
- The built-in screen remains functional.
- The HDMI display receives audio through its speakers or audio output.
- Disconnecting and reconnecting HDMI triggers the Nuxel display-mode notification.
- Both notification actions work.
- Reconnection does not leave stale display state, broken touch input, or a black screen.

If a test cannot be performed, state precisely why and classify it as unverified. Do not fabricate a successful physical test.

## Safety

- Do not flash the bootloader, recovery, modem, firmware, or kernel as a shortcut.
- Do not replace the active compositor or introduce a second framebuffer writer.
- Do not force software rendering or degrade the existing display pipeline.
- Do not blindly apply generic Android, Linux desktop, or Wayland configuration recipes.
- Preserve the existing phone display and SSH access.
- Maintain rollback capability.
- Do not claim completion until the acceptance criteria in the full prompt are met.

**Start now. Read the full specification and carry the implementation through to verified live operation.**
