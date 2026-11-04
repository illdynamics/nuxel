# PWNAGE-64000 — Kickoff prompt for the Nuxel GNSS mission

Read `full-pwnage-64000.md` in the repository root **completely before editing**. Treat it as the authoritative implementation specification for finishing GPS/GNSS on the Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820).

This is a continuation, not a fresh generic GPS setup. The repo already detects the BCM4773 SPI/BBD path and exposes `/dev/ttyBCM`, `/dev/bbd_patch`, `/dev/bbd_control`, `/dev/bbd_sensor` and `/dev/bbd_urgent_patch`; the SPI driver has been observed bound and the GPS power rail can be controlled. The actual blocker is the matching BCM4773 BBD/LHD patch firmware and a compatible userspace protocol provider. **No genuine satellite fix has yet been proven.** `/dev/ttyBCM` is BBD/LHD RPC transport, not NMEA. Do not point stock `gpsd` at it, do not parse it as NMEA, and do not fabricate a fix.

## Execute the full specification

1. Inspect the current branch, worktree and all existing GNSS source/config/tests. Preserve user changes.
2. Establish a trustworthy build-host versus physical-phone baseline. Re-run the focused provider tests and fix the existing GNSS diagnostic self-test hang.
3. Reconcile the firmware inventory across `gnss.json`, `GnssProvider`, bridge inventory, `nuxel-gnss-diag.sh` and `nuxel-gps-status`. In particular, inspect the referenced `/system/bin/bcm_sensorhub_a1.patch`; do not treat `/dev/bbd_patch` as a firmware file or let generic GPS-named blobs pass compatibility checks.
4. Investigate the exact BCM4773 BBD/LHD protocol and firmware-loader ABI from verified source/device evidence. Prefer a native Linux provider. Preserve Nuxel's Android-dependency-zero architecture; no AOSP, Waydroid, Halium, libhybris or copied Android binaries as a shortcut.
5. Implement all safe repository-side work: canonical manifest/status schema, accurate diagnostics, bounded tests, least-privilege provider/service and API integration where evidence supports it, source-aware network fallback, privacy/permission preservation, packaging, deployment and rollback.
6. Keep GPS power OFF by default and when no authorized lease exists. Never weaken the main bridge sandbox to access device nodes. Use a narrow dedicated service/helper if hardware access is genuinely needed.
7. Do not stop at a research report. Make real code changes, build and test them. If authentic firmware or protocol information is absent, do not invent it: finish the safe work and report the exact missing artifact/ABI as a blocker, including a safe owner-controlled extraction/verification path.
8. Do not flash bootloader, modem, EFS/NV, radio or kernel partitions. Do not run an unbounded monitor or leave the GPS rail enabled.

## Required completion report

Return the implementation diff/file list, build and test results, the GNSS stage-by-stage status, firmware provenance/compatibility findings, deployment and rollback commands, and a precise list of anything still requiring physical-phone owner action. A mock or detected device node is not proof. Only mark GPS fully working after a real outdoor satellite fix on the target S10+, with provider timestamp and accuracy, a cross-check, warm/cold-start tests, and a no-sky control that proves network fallback is not being mislabeled as GNSS.

**Start now: read the complete specification, inspect the repo, establish the baseline, and execute the work in its prescribed phases.**
