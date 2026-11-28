# 07 — AUTONOMOUS SIDEWAYS LANDSCAPE DETECTION AND ALL-SEVEN-MODE TESTS

DeepSeek-V4-Pro-Thinking: MASTER 00 still applies. If stage 06 has no real accelerometer stream, preserve `auto_state=blocked_sensor_unavailable` and do **not** count simulated UI rotation as PASS. The owner confirms: **they will put the phone physically SIDEWAYS** for the self-driven landscape acceptance test. Your job is to *automatically detect* it and confirm Nuxel rotated, without spoofed readings or a manual landscape transform.

## Primary sideways physical acceptance — run first

1. Start from a healthy Nuxel normal boot, verified real accel sample stream and gyro response. Capture current orientation status, effective degrees, compositor `wlr-randr --json` output (actual wayland runtime env), `nuxel-wl-fb` presenter's state, touch transform state and Settings/Quick Settings selected mode. Preserve prior user mode for restoration.
2. Request **`auto` mode** using the existing single authority (preferred `nuxelctl orientation set auto` or `nuxel-orientationd set auto --apply` after verifying exact supported syntax). Do not ever call `set landscape`, `wlr-randr --transform`, a fake `manual` sensor, or write fabricated gravity to force the test. If `auto` is unavailable, report hardware integration failure.
3. While the physical phone is sideways, sample accel gravity/time continuously and determine whether a stable sideways angle was detected. Identify 90 or 270 from **real measured signed vectors**, not from assumption about left/right. Respect 450ms default hysteresis and other configured timers; if unchanged after a bounded window, report FAIL with raw vector and timer/policy state.
4. Compare independent evidence: `nuxelctl orientation status` / `/run/nuxel-orientation/status.json` says `mode=auto`, `sensor.available=true`, fresh sample age, effective orientation **90 or 270**; `wlr-randr --json` reports the expected *mapped transform* (the existing config maps effective 90 to transform 270 and vice versa); logical geometry width > height; framebuffer compositor/physical scanout expected; screenshot/viewport actual landscape; no double rotation. Confirm touch target positions/corners, gestures, onscreen keyboard and lockscreen. No successful physical claim based only on a stored status JSON key.
5. Capture a one-page **sideways acceptance receipt** containing real sensor xyz/time, requested mode, detected pose, applied compositor transform, logical resolution, screenshot if captureable, input transform state, measured orientation latency and a timestamped verification from the phone. If one part fails, mark `SIDEWAYS_AUTO=FAIL` and fix the narrow pipeline stage.

## Full rotation regression matrix

- `auto`: portrait 0, reverse portrait 180, side landscape 90 and 270; each transition at least 3 times; stable at rest.
- `auto-portrait`: only 0/180 despite sideways; `auto-landscape`: only 90/270 despite portrait.
- Four fixed locks `portrait`, `reverse-portrait`, `landscape`, `reverse-landscape`: apply immediately then remain unchanged on physical tilt.
- Flat phone, shake, angular boundary, weak gravity, delayed/stale samples, service restart, phone lock/unlock, orientation changes inside apps, switching apps, browser/PWA/GTK viewport, remote desktop, external display when attached, keyboard and touch.
- Screen-off/suspend/resume (no high CPU wake storm), cold boot, warm reboot, acceleration/gyroscope stream recovery, wall clock changes, malformed or missing data. Preserve user mode and apply the correct transform on session recovery. Verify GNSS, camera, NFC, modem/network, UI and touch unaffected.

**Refinement rules:** Keep the existing seven-mode `nuxel-orientationd` and one source of truth, update unverified `mount_matrix` and `gravity_reference` only from actual physical evidence, tune hysteresis instead of brute-force polling, and preserve `auto` refusal on stale data. `68 pytest tests` is a useful baseline but is not physical proof. No DT touches, no boot flash unless staged all previous gates again.

**Deliverables:** `reports/NUXEL-AUTOROTATION-SIDEWAYS-PHYSICAL-PASS.md` only if measured truly passing, `reports/NUXEL-SEVEN-MODE-ROTATION-MATRIX.md`, screenshots/telemetry/touch evidence, test updates, clear regression and suspend/resume results. Gate 07 PASS only when physical sideways **automatically** causes landscape and user input alignment is independently confirmed.
