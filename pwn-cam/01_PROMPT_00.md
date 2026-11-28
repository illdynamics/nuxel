# PROMPT 00 — POST-INCIDENT DEVICE TRUTH + GOLDEN RECOVERY (READ ONLY)

**Scope:** ZERO device partition writes; no kernel image creation or TWRP flashing yet. The owner reports a scary DTB/DTBO damage incident after the camera reports in the ZIP. We need an authoritative, *fresh* baseline before touching anything.

**Execute:**

1. Identify actual host repo `git HEAD`, branch, dirty files, source clones, build outputs; preserve changes in a new isolated worktree/branch without altering the active installation. Record archive-vs-live divergence and locate incident reports and logs newer than `pwn/cam3.md`.
2. Via SSH if Nuxel is healthy, collect read-only: `uname -a`, `/proc/version`, `/proc/cmdline`, `/proc/config.gz`, initramfs evidence, device identity/board revision, `dmesg`, pstore, `/sys/firmware/devicetree/base`, read-only snapshots of `/proc/device-tree`, root mounts, actual partitions and sizes, `/dev/video*` names, services, working SSP, Wi-Fi, SSH, touch, display, graphics, microphone and camera firmware hashes. Do not run vendor STREAMON or any video stress/probe that can trigger old panic.
3. Check presence, ownership, mount state and content identities of actual by-name `boot`, `dtb`, `dtbo`, `recovery`. **Discover** names, do not assume. Extract the exact current BOOT image off-device, plus readable separate DTB/DTBO images and recovery as applicable; capture a copy of full readback and SHA-256. Capture actual in-memory merged FDT and compare with on-flash candidate selection. Keep backups out of public Git and out of the device.
4. Compare current working kernel, BOOT header/appended DT, separate DTB/DTBO partition tables, base-image selection, module/device topology and board variant with expected `beyond2lte` revision. Include replay of the near-brick incident only through **logs**, not new failing writes.
5. Validate backup integrity from saved image, partition boundaries and readback hashes; document a **concrete restoration workflow that uses already-present TWRP** and targets only BOOT and any specifically proven changed DT partition. No actual restore write while Nuxel is healthy. Check that the backup is accessible off-device and recovery can be entered by owner if needed. Do not enter recovery merely to meet a checklist if read-only evidence suffices.
6. If the phone is already in TWRP rather than Nuxel, first determine whether that was intentional and inspect logs/backups; use **EMERGENCY PROMPT R** before any new experiment. Do not assume every recovery boot is a kernel failure without checking boot control and owner intent.

**Make:** `reports/camera-00-postincident-baseline.md`, `reports/camera-00-artifact-manifest.json`, private off-device backup bundle, read-only snapshot/diff scripts, clear `CURRENT_NUXEL_HEALTHY` and `ROLLBACK_READY` flags. Include snapshot timestamps, actual active FDT hash/board revision and precise `UNKNOWN` fields. Do not claim a dry-run equals a tested restore.

**EXIT GATE:** `PASS` only if device identity and current active boot/tree are established, full BOOT backup and existing DT partition identities are verified, and the recovery route is credible. **No flash and no system modifications in this round.**

---
