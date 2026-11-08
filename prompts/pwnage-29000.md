# 🐧 PWNAGE 29000 — Quick Launcher

check out ./pwnage-full-29000.md for the full specs

Audit and repair Nuxel's real Bluetooth, GPS/GNSS, audio and USB-C-to-HDMI support on the Samsung Galaxy S10+ SM-G975F / Exynos 9820. Follow the full **NUXEL TOTAL HARDWARE UBERFIXER** specification.

- Fix Bluetooth Quick Setting `UNCHANGED: NO_ADAPTER` at the actual hardware/provider/service layer.
- Add Settings pages for Bluetooth, Location/GPS, Audio and Displays, showing real devices, provider/service states, supported controls and actionable errors.
- Wire Quick Settings to the same authoritative provider state as Settings.
- Fix GPS state reporting without faking coordinates or confusing map pins with GNSS fixes.
- Replace the Audio Settings dash with actual playback/capture devices, routes, service state and working supported volume/mute controls.
- Investigate USB-C DisplayPort Alt Mode, Type-C mux, kernel/DRM connectors and the existing Wayland compositor. Offer Mirror and genuine independent Desktop mode when actually supported.
- Preserve working Wi-Fi, browser, shell, lockscreen, charging indicator and serial Live Console.

First inspect the repo, Git diff, active agents/deployments and serial locks. If another PWNAGE task is still changing the phone, perform read-only investigation until it is safe. Do not flash kernels/partitions, wipe data, invent devices or report untested hardware as working.

Run relevant tests and document exact root causes, changed files, test results, physical-device evidence and remaining blockers. If HDMI or another feature needs missing kernel/driver support, identify the precise limitation and safe next step.

Start with Phase 0 of the full uberprompt and proceed in small, reversible phases.

