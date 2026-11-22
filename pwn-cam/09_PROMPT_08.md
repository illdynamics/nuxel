# PROMPT 08 — FINAL STABILITY, RELEASE ENGINEERING AND BORINGLY SAFE FUTURE BUILDS

**Entry:** expected camera matrix PASS, or explicit bounded unresolved blocker and otherwise healthy Nuxel.

1. Complete 20 start/stop/open-close cycles, front/rear transitions, app kills, privacy revocation, suspend/resume where supported, camera arbitration, USB/network interaction and thermal/CPU/memory endurance. Assess leaks, DMA buffer release, IRQ storms, errors, cache sync, clock gating, power draw and kernel/pstore warnings. After every kernel/DT change retest baseline functional hardware.
2. Record repeat-after-reboot photo, video, microphone and gallery tests. Replay runbooks from clean checkout with pinned kernel, upstream driver, all patches, final FDT selection, native code, libcamera/IPA, PipeWire and services. Audit SBOM/licenses and exclude proprietary blobs/device dumps from public repo or release.
3. Keep golden rescue artifacts off-device, encrypted/private if applicable; recheck SHA and documented TWRP restore. Add automated CI-style pass/fail gating for Kconfig parity, DTB/DTBO semantics, boot container layout, firmware provenance, module build, userspace backend tests, and release packaging. No future general release process should bypass these checks.
4. Update `pwn/CAMERA_DRIVER_ARCHITECTURE.md`, `pwn/CAMERA_IMPLEMENTATION_LOG.md`, `pwn/CAMERA_LIVE_ACCEPTANCE.md`, `pwn/CAMERA_REPRODUCIBLE_BUILD.md`, `pwn/CAMERA_RECOVERY_AND_ROLLBACK.md`, documentation, changelog, relevant packaging and Nuxel app registry.
5. Produce final reproducible changes in small reviewed commits and one `reports/CAMERA-FINAL-STATE.md` table stating each physical gate, reproducibility, image/source hashes, known-good backup hash, active FDT variant, regressions, feature limits and whether **NO additional flash is required**.

**EXIT GATE:** full pass with real measured physical results. If a genuine external blocker remains, preserve healthy Nuxel and give exact error/action and truthful percentage, not a made-up PASS. Never delete the rollback bundle just to clean up a release.

---
