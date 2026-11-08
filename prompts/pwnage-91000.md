# PWNAGE-91000 — Kickstarter / Execution Prompt

You are now executing the Nuxel PWNAGE-91000 systems optimization and hardware-roadmap mission.

**Read the entire `full-pwnage-91000.md` first.** It is the authoritative specification. This kickoff file does not shorten, replace or waive any requirement in it.

## Mission

Deep-analyze the actual checked-out Nuxel repository, live deployment and connected device to the maximum useful detail. Then safely optimize boot/shutdown and compositor performance, remove genuinely obsolete implementation code, and create the required hardware completion reports.

### Required deliverables

Create/update these files in the repository root:

1. `SYSTEMD-GRAPH.md` — actual boot timing/critical-chain graph, service dependency audit, and shutdown timeline only where backed by real shutdown evidence.
2. `GPU-ACCEL-REPORT.md` — every remaining software/partial graphics layer, precise blocker and best path to complete acceleration.
3. `REPORT-CAMERA.md` — exact camera sensor/FIMC-IS/firmware/userspace pipeline blocker and best route to real integrated camera frames.
4. `REPORT-GPS.md` — exact BCM4773/BCM47752 BBD/LHD/GNSS blocker and best route to a real GeoClue GNSS fix.
5. `REPORT-NFC.md` — exact S3NRN82/sec-nfc firmware/transport/NCI blocker and best route to physical tag read and further NFC functions.
6. `REPORT-ROTATION.md` — exact LSM6DSO/BCM47752 SSP/LHD blocker and best route to real accelerometer/gyro-based auto-rotation.
7. `REPORT-FINGERPRINT.md` — exact qbt2000 driver/TEE/trusted-provider blocker and secure enrollment/authentication roadmap.
8. `REPORT-MOBILE-NETWORKING.md` — exact Shannon LTE CP transport/plugin/firmware blocker and roadmap for SIM, registration, LTE data, SMS, voice and IMS/VoLTE.
9. `REPORT-LEDS.md` — actual rear flash, physical notification/RGB LED and display edge-lighting capability, driver path and color roadmap.
10. `PWNAGE-91000-REPORT.md` — execution results, before/after measurements, cleanup ledger, tests, blockers and rollback.

## Execution rules

1. Inspect `git status`, branch/commit if available, `VERSION`, selected device profile, live device identity, kernel/systemd version and deployed source hashes before editing. Preserve existing user changes. The source archive used during prompt preparation contained `v0.7.7-beta`, but the live checkout is authoritative.
2. Read `./SYSTEMD-GRAPH.md` if it exists and verify its capture date/boot ID/target. The supplied source archive did not contain a root `SYSTEMD-GRAPH.md`; if the real checkout also lacks it or the graph is stale, collect fresh live boot evidence before optimizing. Shutdown timing must come from real journal/stop evidence; otherwise label it `NOT_CAPTURED`.
3. Map systemd units and dependencies, actual service/process owners, D-Bus activation, session startup, compositor, framebuffer presenter, bridge, WebKit/GTK/Flatpak and build/package inclusion. Do not equate `systemd-analyze blame` duration with critical-path contribution.
4. Do not disable or remove a service just because it looks slow or inactive. Preserve every existing service/functionality. Fix redundant ownership at its source; do not create a service that starts another process only to stop it. Keep readiness, fallback, restart and graceful shutdown semantics.
5. Profile the complete Phoc/wlroots → buffer → `nuxel-wl-fb`/panel path and WebKit/GTK separately. Measure frame pacing/input latency, CPU, copies/conversions, buffer transport, GPU context and thermal behavior. The historical S10+ reports show Mali kbase/Phoc acceleration with a remaining WebKit/GTK WSI and framebuffer-presentation gap; verify the newest runtime before acting.
6. Create a removal ledger from explicit earlier Nuxel “remove/obsolete/replaced/do not ship” decisions. Delete only proven dead executable/config/package code. Remove all active references and packaging copies, then prove the code is absent from the built image. Keep historical reports and tests where they serve as evidence.
7. Implement only safe, reversible, evidence-backed R0/R1/R2 improvements. Do not flash, reboot into Download Mode, write partitions, alter EFS/IMEI, deploy experimental camera/GNSS/NFC/sensor/fingerprint/modem drivers, or install unverified firmware/TEE components. The hardware tasks in this mission are investigations and reports, not authorization for hazardous bring-up.
8. Re-run all relevant test suites, systemd verification, image/package checks and protected-function regression tests. Distinguish `PASS_PHYSICAL`, `PASS_DEVICE_RUNTIME`, `PASS_HOST`, `PASS_FIXTURE`, `BLOCKED_HARDWARE`, `NOT_TESTED`, `FAILED` and `ROLLED_BACK` accurately.
9. Do not claim `FULLY_DONE` if a service has regressed, a hardware report is missing, the boot graph is fabricated/stale, shutdown is claimed without evidence, or obsolete code remains packaged after being marked removed.

## Priority findings to re-check (not pre-approved conclusions)

- S10+ target: Galaxy S10+ `beyond2lte`, Exynos 9820, Mali-G76 MP12, Fedora ARM64, historical downstream Linux 4.14.253. Verify current device and kernel first.
- GPU: `docs/beta-finalization/live/PWNAGE-48000-KBASE-GPU-REPORT.md`, `PWNAGE-60000-GPU-MANIFEST.md`, `GPU-WEBKIT-WSI-DECISION.md`, `tools/s10plus/a67/`, `configs/nuxel/graphics/graphics-profile.json`.
- Camera: A53 reports private Exynos FIMC-IS V4L2 behavior and no proven integrated sensor frames. Re-run diagnostics and inspect exact matching kernel source/DT/firmware.
- GNSS/rotation: BCM4773/BCM47752 BBD/SSP/LHD path; `/dev/ttyBCM` is documented as packet transport, not generic NMEA. LSM6DSO samples historically remained zero because the sensor hub did not start/respond.
- NFC: PWNAGE-65000 reports `/dev/sec-nfc`, firmware and offline ABI/NCI/NDEF tests, but no verified protocol or physical tag read. Verify S3NRN82 identity and current hardware state.
- Fingerprint: qbt2000 sensor path may be detected, but no verified secure TEE enrollment provider is established. Preserve PIN fallback and biometric template protection.
- Cellular: Shannon LTE is not currently documented as ModemManager-ready; verify CP transport/plugin/firmware. Never touch EFS, IMEI or modem partitions.
- LEDs: separate rear flashlight, any genuinely enumerated colored notification LED, and software edge-lighting overlay. Preserve OFF-by-default and torch timeout.

## Required execution order

**A. Audit:** inspect all source, build, package, service and runtime references; collect baseline metrics and tests; reconcile old reports with current evidence.

**B. Systemd:** create/validate `SYSTEMD-GRAPH.md`; identify safe critical-path and shutdown improvements; apply one reversible change at a time; verify all protected services.

**C. Compositor:** profile actual frame/input path; fix the highest measured inefficiency while preserving GPU fallback, panel, touch, keyboard, orientation and app rendering.

**D. Cleanup:** process only proven obsolete code from the removal ledger; remove source plus runtime/build/package copies; run image tests proving absence and replacement functionality.

**E. Hardware reports:** investigate GPU, camera, GNSS, NFC, rotation, fingerprint, modem and LEDs independently; produce all seven root-level reports with the full blocker chain and realistic staged roadmap.

**F. Final gate:** build/test, compare before/after numbers, inspect deployed package contents, check all services, document limitations and rollback. Execute safe work now; do not stop after writing a plan.

## Final status

Use `FULLY_DONE` only if every applicable acceptance gate in `full-pwnage-91000.md` passes. Otherwise report `PARTIAL`, `BLOCKED` or `ROLLED_BACK` with exact reasons. Include changed files, services preserved/modified/removed, boot and shutdown evidence, compositor measurements, cleanup proof, report paths, hardware verdicts, exact test counts and rollback commands.

**Begin by reading `full-pwnage-91000.md` in full and inspecting the real current checkout. Execute the complete mission.**
