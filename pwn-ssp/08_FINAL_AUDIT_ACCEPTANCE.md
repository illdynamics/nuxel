# 08 — FINAL HARDENING, ENDURANCE, REPRODUCIBILITY AND OWNER HANDOFF

DeepSeek-V4-Pro-Thinking: only declare this mission complete if stages 05, 06, 07 **all** genuinely passed on the physical phone and an intact boot/DT recovery manifest exists. Keep MASTER 00 constraints. Do not quietly reduce PASS criteria or substitute synthetic data.

1. Verify repeated normal Nuxel **cold boots** and warm reboots bring up genuine MCU firmware/SSP accel+gyro automatically with no manual download, no first-boot race, no recurring `regulator_force_disable`, no infinite restart/reflash loop, and no detour to TWRP. Verify service failures recover gracefully without stale `ESW:READY`, IRQ mismatches or transport contention. Repeat actual auto-sideways test at least once after reboot.
2. Verify suspend/resume, screen off/on, lock/unlock, service restart/crash, disconnected sensors, abandoned firmware transfer cleanup, kernel dmesg/warnings, SPI PM, IRQ and memory behavior, CPU and battery load; no GNSS shared-rail, audio, network/SSH, camera/NFC, touchscreen, Wayland or remote-desktop regressions. Keep user configuration persistent; restore original mode after controlled tests.
3. Re-read and hash BOOT, external DTB/DTBO, embedded/appended DT tail and selected dtbo index; compare to the exact immutable baseline. If DT changed unexpectedly or Nuxel health regressed, **FAIL** and restore verified BOOT-only rollback through the approved TWRP route. **Never change DT/DTBO to rescue a failed candidate.**
4. Clean up experimental duplicate patches and dead code; lock down only one SSP initializer; make actual required SSP patch manifest a build stop gate; add a reproducible firmware-identity verifier; link offline tests to on-device physical acceptance. Document kernel/source/branch/commit, BBD ABI, validated vendor protocol state machine, actual calibration/matrix and auto policy, service ownership, timings and safe failure behavior.
5. Deliver a **single authoritative engineering report** and evidence folder: `reports/SSP-AUTO-ROTATION-FINAL-2026-11-22.md`, working kernel/BOOT+source hashes, DT/no-DT-change receipts, full hardware protocol transcript, real accel and gyro datasets across poses, auto-sideways acceptance and screenshot/touch checks, cold/warm reboot and suspend/resume results, exact TWRP recovery runbook and negative-case test summaries. Update relevant docs without falsely claiming a hardware PASS.
6. Commit clean staged changes only after tests; preserve history and unrelated work. Do not create a release or push/merge externally unless that was specifically authorized for the branch. Respect Nuxel's zero-Android-userspace design.

**Final PASS conditions:**

- `NUXEL_HEALTHY=PASS` normal system, not TWRP.
- `DTB_UNCHANGED=PASS`, `DTBO_UNCHANGED=PASS`, `BOOT_EMBEDDED_DT_TAIL_UNCHANGED=PASS`.
- `ROM_GET_VERSION_PHYSICAL=PASS`, `FIRMWARE_COMPLETE=PASS`, `APP_START_CONFIRMED=PASS`, `SSP_WHOAMI=PASS`.
- `ACCELEROMETER_PHYSICAL=PASS`, `GYROSCOPE_PHYSICAL=PASS` with true motion data.
- `AUTO_SIDEWAYS_LANDSCAPE_PHYSICAL=PASS`, `ALL_SEVEN_MODES=PASS`, `DISPLAY_AND_TOUCH_ALIGNMENT=PASS`.
- `COLD_BOOT=PASS`, `WARM_BOOT=PASS`, `SUSPEND_RESUME=PASS`, `REGRESSIONS=PASS`, `ROLLBACK_READY=PASS`.

If any fail, give precise failure state, source-evidence links, minimal next corrective patch, and safe Nuxel/TWRP device condition. **No unsupported 100% claim.**
