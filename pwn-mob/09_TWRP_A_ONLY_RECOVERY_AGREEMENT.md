# 09 — TWRP Agreement & DTB/DTBO IMMUTABILITY: Mandatory Before Any Flash

**Standing user agreement (paraphrased):** Reflashing Nuxel in TWRP is allowed where necessary. If, after reflash/reboot, the handset returns to TWRP rather than Nuxel, the flash **FAILED**; agent must examine evidence, correct the cause and use the recovery procedure, ultimately restore a bootable Nuxel. This agreement is NOT authorization for uncontrolled retries, changing protected partitions, or arbitrary DT experiments.

## A. Current known-good checkpoint BEFORE experimentation

Verify actual physical device = Samsung SM-G975F/beyond2lte, confirmed board hardware rev and live partition names via independently verified PIT/by-name map; no assumed A/B slot. Record booted Nuxel health, boot log, Wi-Fi/SSH and USB recovery route, kernel version, config, current DT version/hashes and boot image size/hash. Make at least **two verified, independent host-side copies** of the currently **booting** BOOT image; identify precise recovery pathway and verify backup readability. Record BOOT partition size, image header, embedded base DTB, actual DTBO partition existing hash **read-only only**, stock/rollback identities. Do not assume historical backed-up BOOT image still exists, or that a saved old boot is necessarily current/compatible.

If any backup, identity, partition mapping or recovery preflight fails: NO FLASH. Prefer revertible userspace service deployment which should suffice for modem userspace recovery.

## B. Immutable device tree fence

Current S5000AP probe creates the modem controller, SHMEM, `/dev/umts_boot0`, `umts_ipc0/1`, `umts_rfs0` and rmnet interfaces. It is **already DT-probing**, so there is no justified reason to touch device tree on current evidence. Exact invariant: DTB/DTBO inputs, appended DT payload, S-Boot overlay and board-revision mapping may not be modified, regenerated, replaced or rebased. Do not cherry-pick sensor/camera/NFC/SSP DT experiments when building a modem candidate; do not apply all optional kernel patches. `dtc` decompile/recompile is not harmless byte-preserving round trip and must not be used as 'backup repair'. If BOOT repacking is essential, use a verified **byte-identical existing DT payload**, verify extracted SHA pre/post, compare header sizes/offsets and ensure bootable image fits target; ideally do not repack BOOT at all.

## C. Allowed and forbidden writes

Allowed only after independently reviewed preflight: **BOOT-only** or a specifically selected **OS userspace image/file deployment** that preserves data, with fully verified reversible target and user approval. NO DTBO, RADIO/MODEM/CP, EFS/EFSG/SEC_EFS, NV/calibration, bootloader, PIT, RPMB, TEE/secure stores, carrier keys, device identity, arbitrary rootfs partition or userdata wipe. Treat `boot/s10plus/flash.sh` as an old helper, not proof of safety: it accepts arbitrary `--rootfs-partition`, and its denylist omits `modem`/`radio`/`dtbo` compared with modem policy. Prefer the proven `scripts/nuxel-adb-flash-pack` procedure *after inspecting current code and tests*; never use `--force` to bypass safeguards. Exynos device has no generic fastboot.

## D. Preflight manifest per candidate

`TRIAL_ID`, repo commit/dirty files, physical device model, live boot SHA, boot/embedded-DTB/DTBO current hashes, candidate boot SHA, candidate DT hash (MUST EQUAL proven baseline), kernel/ramdisk hashes, image header/partition size, file/final partition path, owner approval, backup A/B local paths and hashes, tool version, dry-run receipt, rollback command/image/verified path, expected boot evidence and maximum abort time. A user-host known-good image must remain accessible if SSH is lost.

## E. Flash transaction

Use safe, device-verified, partition-scoped existing tool, with TWRP available; verify the **exact intended partition only**. Before operation capture `last_kmsg`/pstore and current partition image hash safely. After write, perform independent readback hash verification with appropriate byte length and read-only hash control. NO catch-all multi-partition flashing. On reboot Nuxel PASS only after shell/UI/network/service identity and `uname`/kernel hash match, with no unexpected DT/CP regressions.

## F. Recovery branch if back in TWRP

**FAILED_BOOT**; do not say 'TWRP reboot was successful'. Capture TWRP device identity, boot log/pstore/last_kmsg, the failed flashed image, signatures of panic/overlay mismatch, exact boot/DT payload hashes. Compare to known-good BEFORE proposing fix. Immediately prioritize restoring known-good BOOT if boot regression blocks normal Nuxel access; keep data and radio partitions untouched. Any next candidate must be **different**, tied to a demonstrated root cause, rebuilt offline and independently preflighted. Do not repeat identical unbootable BOOT. Cap automatic engineering retry to **two distinct, reviewed recovery candidates** then stop and seek owner hands-on assistance or restore known-good. No unattended reboot loops, no sleep-for-an-hour waiting, no speculative fallback stock AP/BL/CP/CSC flash. If known-good restoration fails or recovery mode is lost, STOP rather than improvise device-specific secure flashing.

## G. Proof and closeout

After restoration or success, record BOOT partition readback SHA, embedded DTB SHA (MUST match known-good for this mission), DTBO unchanged SHA (if safe read available), running Nuxel proof, modem driver presence, saved network/USB access and relevant hardware regression. Publish `reports/S5000AP-BOOT-RECOVERY-RECEIPT.md`; mark candidate FAIL even if rollback returned Nuxel successfully. **Recovery working ≠ mobile networking working.**
