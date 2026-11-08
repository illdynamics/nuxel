# PWNAGE-35000 — BUTTERSMOOTH NUXEL

The full pwnage 35000 prompt is located here: ./full-pwnage-35000.md, use it.

Deeply inspect, optimize, implement, test, and deploy the current Nuxel codebase for the Samsung Galaxy S10+ (SM-G975F / beyond2lte).

**Mission:** Make Nuxel dramatically more responsive, smooth, and dependable while preserving its lightweight 8-bit arcade aesthetic.

Fix these five priority areas:

1. **Performance:** Profile the complete UI and system, find real bottlenecks, eliminate unnecessary blocking work, rendering overhead, excessive polling, and startup contention. Prioritize input latency, frame consistency, fast app switching, and low memory/CPU usage. No heavy transparency or expensive visual effects.
2. **Keyboard haptics:** Restore actual vibration on keypresses. Trace the keyboard-to-hardware haptic path, fix the real failure, and verify physical vibration on the S10+. Do not simulate success in the UI.
3. **Back button:** Repair the global Back action and app lifecycle. Back must perform the correct action inside an app or navigate back according to that app's state; when appropriate, it must minimize the app and return to the home desktop. It must not merely move the four bottom desktop apps over the foreground application. Browser behavior alone is not sufficient.
4. **Reboot:** Fix the long black-screen delay when rebooting through the power menu. Trace the complete shutdown/reboot sequence, identify the exact blocking service, process, timeout, display transition, or systemd job, and fix the root cause without sacrificing orderly shutdown or recovery access.
5. **Wi-Fi and quick settings:** Investigate delayed Wi-Fi startup and autoconnection on the S10+, including the driver, firmware, rfkill, NetworkManager, supplicant/backend, DHCP, service ordering, and logs. Fix the actual cause of the prolonged “Wi-Fi unavailable” state and delayed connection. Make quick-settings actions responsive immediately, without waiting for unrelated initialization.

Inspect the repository and `docs/pwnage-35000.md` if present. Reproduce each failure, profile before and after, implement the smallest reliable fixes, run regression tests, deploy safely, and report evidence.

**Safety:** Do not flash firmware, change partitions or bootloader, replace the kernel, or perform destructive resets. Preserve the current kernel and USB/serial/WLAN recovery routes. Back up modified configuration and provide rollback instructions.

Do not stop after writing a plan. Complete as much of the implementation, testing, and deployment as the environment permits. Clearly identify anything that still requires physical-device verification.

**Definition of done:** Nuxel feels noticeably faster; keyboard presses physically vibrate; Back behaves correctly across apps; reboot no longer has an unexplained minute-long black-screen delay; Wi-Fi connects reliably and promptly; and quick settings respond without waiting for the rest of the system.
