# PWNAGE-69000 — KICKSTARTER / EXECUTION PROMPT

You are the lead Nuxel USB-C, audio, display and streaming engineer. Read **`full-pwnage-69000.md` from beginning to end** and execute the complete mission against the current repository. This is an implementation task, not a report-only exercise.

## Execute the mission

1. Capture Git, S10+ build, package, kernel, service and test baselines before editing. Preserve all owner changes.
2. Trace the existing headphone/UAC routing, MAX77705 Type-C/USB role, external display/DP path, fbdev/Phoc output architecture, app registry, bridge APIs and S10+ image manifests.
3. Fix USB-C audio for the owner's Samsung USB-C earphones and Beyerdynamic 3.5 mm headphones through their USB-C adapter. Identify each adapter's real transport (UAC DAC vs passive analog); implement event-driven ALSA/PipeWire/WirePlumber routing, safe unplug fallback and recovery. Do not assume the USB-C port can be in host mode while the CDC-ACM live console is active.
4. Diagnose why the USB-C-to-HDMI connection is indicated but the TV remains blank. Prove Type-C partner/DP Alt Mode negotiation, HPD/AUX/EDID, driver/connector/mode/scanout, compositor output and frame commit separately. The current internal fbdev bridge is not proof of an external output path.
5. Build **NuXtream** as a real app + service + typed Nuxel bridge API. Implement direct-display mirror/extend controls only for real outputs; keep them distinct from network screen mirroring.
6. Implement an open, documented casting MVP using standard WebRTC/security primitives and a working browser/reference receiver. Support Wi-Fi and wired LAN; add USB-IP transport only if CDC-ECM/NCM or another real topology can preserve a tested recovery path. Optional Miracast is separate and must be physically interoperable before claimed.
7. Add comprehensive fixture, API, app-registry, packaging, privacy, lifecycle and performance tests. Repair any misleading selftest that passes with zero fixtures. Build and verify the clean S10+ image integration.
8. Keep a findings ledger and continue audit → implement → test → diff review loops until all safe work is complete. Produce every report and owner test guide required by the full prompt.

## Non-negotiable safety

**NO TWRP. NO FLASHING. NO PARTITION/BOOT/DTB/MODEM/EFS/RECOVERY WRITES. NO BOOTLOADER/OEM/FRP CHANGES. NO FACTORY RESET. NO PHONE REBOOT.** Do not blindly switch Type-C roles, detach the only USB console gadget, write DP mux/PHY/CCIC/DECON registers or sysfs controls, force display modes, or expose unauthenticated screen/audio capture. Any hardware role transition, actual UAC playback test, DP modeset or visible casting test must be a bounded owner-approved procedure with a proven alternate management/recovery path. Keep diagnostics read-only by default.

Do not fake device detection, active scanout, audible output or casting success. Keep the internal speaker and AMOLED working. Distinguish repository-tested, built, installed, driver-bound, enumerated, routed, hardware-initialized and physically verified states. Do not publish or push a release.

**Begin with baseline capture. Then investigate, implement, test, audit your diff, and repeat. Do not merely summarize `full-pwnage-69000.md` or return a plan.**
