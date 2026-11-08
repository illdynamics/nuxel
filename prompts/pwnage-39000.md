# PWNAGE-39000 — NUXEL STABILITY, CONNECTIVITY & DESKTOP POLISH
## Kickstarter Mission

**Mission:** Fix the newly introduced battery drain, slow reboot initiation, Wi-Fi boot behavior, Flatpak/NuXtore installation problems, desktop rendering performance, navigation icons, status indicators, USB file-transfer mode, and Bluetooth file sending.

**Target:** Nuxel running on the Samsung Galaxy S10+ (SM-G975F / beyond2lte).

**Connection:** Work over Wi-Fi SSH using:

`~wicked/.ssh/wicked_wqn_id_rsa`

Do not switch to USB or serial SSH as a workaround. Preserve the existing Wi-Fi SSH recovery path.

---

## NON-NEGOTIABLE EXECUTION ORDER

1. Connect to the phone over Wi-Fi SSH using the specified private key.
2. Create a complete, prioritized TODO checklist before making changes.
3. Immediately investigate and fix Wi-Fi auto-enable/autoconnect on boot.
4. Reboot immediately after the Wi-Fi fix.
5. Reconnect over Wi-Fi SSH and verify that Wi-Fi is enabled, connected, and correctly represented in the Nuxel UI.
6. If Wi-Fi does not pass, continue fixing Wi-Fi. Do not proceed to unrelated tasks until it passes.
7. Fix the remaining issues in the TODO list.
8. Reboot again after all changes are complete.
9. Reconnect over Wi-Fi SSH and perform a final verification.

There must be TWO deliberate reboots:
- First reboot: immediately after the Wi-Fi boot fix.
- Final reboot: after the entire mission is complete.

## PRIORITY TASKS

### P0 — Wi-Fi automatically enabled at boot
- Wi-Fi radio must be enabled by default after every boot.
- Saved Wi-Fi profiles must autoconnect when available.
- Quick Settings must correctly reflect the actual Wi-Fi radio and connection state.
- The Wi-Fi toggle must start in the ON state when Wi-Fi is enabled.
- Fix discrepancies between NetworkManager and the Nuxel UI.
- Verify this by rebooting immediately after the fix and reconnecting through Wi-Fi SSH.

### P1 — Battery drain during sleep
- Investigate why overnight battery drain changed from approximately 15–20% to a complete battery drain.
- Identify the actual source: wake locks, services, polling, CPU activity, display, radios, or power-management regression.
- Restore sensible suspend/idle behavior without breaking touch, Wi-Fi SSH, or phone functionality.

### P2 — Slow reboot initiation
- Fix the long black screen between selecting Reboot in the power menu and the actual reboot starting.
- Make the UI acknowledge the reboot immediately.
- Find and fix the real delay rather than hiding it with arbitrary sleeps or timeouts.

### P3 — Flatpak applications and software center
- Install and verify Firefox and VLC through Flatpak where compatible.
- Investigate a suitable Wi-Fi and Bluetooth management application.
- Install a proper Linux software center capable of managing Flatpak applications, with a visible Nuxel app icon.
- Verify applications actually launch.

### P4 — NuXtore installation backend
- Detect applications already installed on the device.
- Make NuXtore's Install action actually install applications.
- Show genuine installation progress and completion/failure.
- Refresh the application inventory and make installed applications launchable.

### P5 — Bottom navigation icon quality
- Fix the Back, Penguin Home, and Tabs icons.
- Render the actual supplied images cleanly, without clipping, distortion, low-quality resampling, or incorrect scaling.

### P6 — Main desktop performance
- Profile why the primary desktop is noticeably slower than the second desktop and applications.
- Investigate icon drawing, image decoding, layout, rendering, and unnecessary updates.
- Make the primary desktop as responsive as the other environments without sacrificing its visual identity.

### P7 — Top-bar status indicators
Add accurate indicators for:
- Bluetooth ON/OFF.
- GPS/location availability and state.
- Audio mode: normal sound, vibration-only, and silent/muted.
- Mobile network: disconnected/connected, signal strength, 3G/4G/5G, and roaming.

All indicators must reflect real system state.

### P8 — Lockscreen USB connection-mode button
- Make `./assets/nuxel-connection-mode.png` visible and usable in the bottom-right corner of the lockscreen.
- Add a popup with:
  - Normal Charging
  - File Transfer
- Display `./assets/nuxel-file-transfer.png` while file-transfer mode is genuinely active.
- Safely expose phone files to a connected computer.
- Handle host eject and switching back to charging mode.
- Never expose an actively mounted writable filesystem through unsafe raw USB Mass Storage.

### P9 — Bluetooth file sending
- Add a Send button to the File Explorer.
- Include Bluetooth as a submenu option.
- Allow selecting a paired/discovered device and sending selected files.
- Show actual transfer progress and success/failure.

---

## IMPORTANT SAFETY RULES

- Preserve existing user data and configurations.
- Do not overwrite unrelated changes.
- Do not flash firmware, replace the kernel, change bootloader settings, repartition storage, or perform destructive resets.
- Do not break Wi-Fi SSH or existing recovery access.
- Never claim a feature works merely because an API call or device enumeration succeeded.
- Never fake hardware status or application installation.
- Do not use unsafe USB Mass Storage against a filesystem mounted by Nuxel.
- Back up configuration files before changing them.
- Test every change on the actual phone wherever possible.
- Provide evidence, logs, and a rollback path.

## DEFINITION OF DONE

PWNAGE-39000 is complete only when:

- Wi-Fi automatically enables and reconnects after reboot.
- The Wi-Fi quick setting accurately reflects the real state.
- Overnight power consumption is investigated and materially improved.
- Reboot initiation no longer suffers from the previous long black-screen delay.
- Firefox, VLC, and a suitable software center are genuinely installed and launch.
- NuXtore detects installed applications and actually installs new ones.
- Bottom navigation icons render cleanly.
- The primary desktop is demonstrably smoother.
- Bluetooth, GPS, audio, and cellular indicators reflect real state.
- The lockscreen connection-mode control works.
- File transfer is safe and genuinely accessible from a computer.
- Bluetooth file sending works.
- The phone has been rebooted at the end and all critical features reverified.

**Do not mark the mission complete with unresolved blockers. Document any hardware or platform limitation honestly.**
