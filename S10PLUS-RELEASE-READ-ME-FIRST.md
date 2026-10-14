# Nuxel beyond2lte patched release (2026-10-14)

**Offline validated only; not boot-verified on Samsung hardware.**

See `mac-quickstart-s10plus-flash-finisha.md` before any flash.
Images live under `build/out/s10plus/`. Do not flash until the actual device
model, board revision (merged DTB is EUR OPEN 26), PIT sizes, data backup and
stock recovery path have all been verified. USERDATA flashing destroys data.

Fixes: initramfs UFS USERDATA discovery via /sys/class/block/*/uevent, no
unsafe SYSTEM fallback, /bin/sh build invariant, corrected newc symlink length
writer, build guard against guessed board revision, restricted BOOT/USERDATA
flash script, patched S10+ rootfs PID1 and configuration, offline checker.

Not supplied: complete Nuxel desktop, validated kernel modules/firmware,
actual handset boot logs, confirmed working S-Boot/DTBO integration.
