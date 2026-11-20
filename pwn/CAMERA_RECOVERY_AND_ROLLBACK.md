# NUXEL S10+ Camera — Recovery and Rollback

**Date:** 2026-11-20
**Target:** SM-G975F beyond2lte, Exynos9820

## Current known-good state (verified 2026-11-20)

- Device boots Nuxel normally (kernel 4.14.253-gf7194c1d15ed-dirty, build #3).
- No boot/partition/EFS/modem changes made in this session. All camera work this
  session was userspace-only (firmware already deployed prior; capture tools
  in /usr/local/bin) plus one kernel-source clone + offline build (no flash).
- The one camera STREAMON experiment triggered a hardware-watchdog panic
  (pstore "Panic#2") and a clean reboot back into Nuxel. No lasting damage;
  fimc-is re-probed and /dev/video101 returned on the next boot.

## Rollback for Stage A (userspace, already reversible)

- /system/vendor/firmware/{8 blobs} — remove to revert firmware deployment.
- /usr/local/bin/nuxel-fimc-capture* tools — remove to revert capture tools.
- No persistent kernel config was changed by Stage A experiments.

## Rollback for Stage B (future kernel flash)

Once a custom-driver kernel is built and flashed:

1. Preserve the current boot image BEFORE any flash:
   `adb root && adb pull /dev/block/platform/13d60000.ufs/by-name/boot boot.img.known-good`
   record `sha256sum boot.img.known-good`.
2. Flash via TWRP (`adb push new-boot.img /sdcard; adb reboot recovery; twrp install`)
   or `dd` from a root shell, recording the exact image + SHA-256.
3. Recovery path: USB + TWRP to re-flash `boot.img.known-good`; or re-run the
   existing `kernel/s10plus/build-kernel.sh` (vendor FIMC-IS2 defconfig) to
   rebuild the rollback Image.gz.
4. Re-verify boot into Nuxel (SSH root@10.11.12.99 + `uname -a` + `ls /dev/video101`).
5. Do NOT alter EFS/IMEI/modem/keys/unrelated partitions. Do NOT data-destroy.

## TWRP interpretation rule (from cam.md)

If a flash results in a TWRP boot (not Nuxel), that is a failed/hung/crashed boot.
Then: re-investigate the actual failure (kernel log, boot selection, DTB, image
format), fix, and re-flash until Nuxel boots again. Do not re-flash an identical
unmodified image; each retry must change something diagnosable.

## Verified recovery results this session

- Streaming panic -> clean auto-reboot -> Nuxel (SSH restored, fimc-is loaded).
- No TWRP loop encountered. No flash performed this session.
