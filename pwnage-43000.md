# PWNAGE-43000 — NUXEL BOOT SPEED, UI PERFORMANCE & USB INTEGRATION

**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte  
**OS:** Nuxel — Fedora-based ARM64  
**Mission:** Optimize boot, eliminate black-screen delays, restore touchscreen behavior while charging, improve UI responsiveness, install Linux applications, and finish USB file transfer.

## P0 — BOOT SPEED AND TRANSITIONS

- Investigate why the spinning penguin boot animation takes so long.
- Measure actual boot time and identify which services delay the transition to the lockscreen.
- Optimize the critical boot path without skipping essential hardware initialization.
- Fix the long black screen after selecting Reboot from the power menu.
- Fix the black screen followed by flashing white between the preloading MP4 and lockscreen.
- Make the preloading-video-to-lockscreen transition seamless.

## P1 — REMOVE UNWANTED LPM / CHARGING TOUCHSCREEN RESTRICTION

When USB-C is connected and the phone is powered on, the touchscreen must remain usable.

- Find the actual service or power-mode handler responsible for LPM/charging-mode behavior.
- Remove or disable the unwanted touchscreen restriction.
- Remove its unnecessary notification if the underlying mode cannot safely be removed.
- Do not disable touch simply because the charger is connected.
- Preserve normal charging, thermal protection and battery safety.

## P2 — UI PERFORMANCE

Optimize:

- Quick Settings opening and closing.
- Home Settings, which is currently noticeably sluggish.
- Lockscreen responsiveness.
- Home navigation while the keyboard is open.

When the Penguin Home button is pressed:

- Dismiss the active keyboard immediately.
- Restore proper input-method state.
- Navigate/minimize to Home normally.
- Do not leave an invisible keyboard intercepting touches.

Keep other applications and settings screens as responsive as they currently are.

## P3 — NATIVE AND FLATPAK APPLICATIONS

Install and verify compatible applications.

Requested Flatpak targets:

- Firefox.
- VLC.
- Signal.
- Stremio.

Also install a small selection of useful native Linux applications suitable for Nuxel.

Requirements:

- Verify ARM64 availability.
- Verify package identity and source.
- Add real launcher icons and desktop entries.
- Verify applications actually start.
- Verify persistence after reboot.
- Do not install an entire desktop environment unnecessarily.
- Do not install unofficial or untrusted packages without clearly identifying their provenance.

## P4 — LOCKSCREEN USB CONNECTION MODE

Use:

`./assets/nuxel-connection-mode.png`

Display the button at the bottom-right of the lockscreen.

When pressed, open a popup with:

1. Charging Mode
2. File Transfer Mode

When File Transfer Mode is selected:

- Configure a genuine USB file-transfer device.
- Make the phone visible and browseable from a connected computer.
- Use a safe protocol such as MTP where supported.
- Show `./assets/nuxel-file-transfer.png` on the lockscreen while the mode is active.
- Detect disconnect/eject and return to a truthful charging state.
- Allow switching back to Charging Mode.

Do not expose the actively mounted root filesystem as writable raw USB Mass Storage.

Preserve USB console and recovery access.

## DEFINITION OF DONE

- Boot and reboot are measurably faster.
- No long unexplained black reboot delay.
- No black/white flashing between preloading video and lockscreen.
- Touchscreen remains usable while charging.
- LPM no longer blocks normal touchscreen interaction.
- Quick Settings, Home Settings and lockscreen are smoother.
- Home closes the open keyboard correctly.
- Firefox, VLC, Signal and Stremio are installed where compatible and genuinely launchable.
- Native Linux applications are integrated into Nuxel.
- Lock-screen connection-mode button works.
- File Transfer Mode is visible and functional from an actual computer.
- Charging/File Transfer indicators reflect real USB state.
- Final reboot succeeds and everything is reverified.

**Do not merely make the UI look functional. Fix the underlying services, input, rendering and USB behavior.**

🐧 NUXEL — FASTER BOOT, SMOOTHER CONTROL, REAL FILE TRANSFER.
