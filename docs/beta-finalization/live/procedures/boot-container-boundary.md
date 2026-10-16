# Procedure — the BOOT container boundary (why these artefacts are `BLOCKED_FIRMWARE`)

`tools/beta/live/deploy-manifest.json` writes **userspace files only**. Everything
below is outside it on purpose, carries a firmware-adjacent terminal state, and is
listed in `non_deployable[]` with the reason attached to each path.

| Artefact | Why it is not deployable | Terminal state |
|---|---|---|
| The BOOT container (`boot/`, the initramfs `init.sh`, `nuxel-anim-player`, the packed `nuxel-animation.nux`, the kernel `Image.gz`) | installing it means writing the BOOT partition | `BLOCKED_FIRMWARE` |
| `images/s10plus/*.img` (`nuxel-beyond2lte-boot.img`, `-boot-merged.img`, `-rootfs.img`) | flashed artefacts; the plan's guard refuses an `.img` target outright | `BLOCKED_FIRMWARE` |
| `tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch` | a kernel/DTB change; patches are **proposals, never applied** | `BLOCKED_KERNEL` |
| `boot/**` udev/config carried inside the initramfs | replaced by a BOOT update, not by a live write | `BLOCKED_FIRMWARE` |

## What this means for the two items that matter most

**1. Touch in charger/LPM mode.** The established finding is that a charger-mode
boot (`androidboot.mode=charger` in `/proc/cmdline`) makes `sec_ts` refuse to
initialise, so touch cannot exist on that boot. The fix in the repository is a
kernel patch — a BOOT update — and the mission forbids flashing. The correct
on-device answer is therefore: a **permitted normal reboot** (through
`tools/beta/live/nuxel-live-reboot-verify.py`, with a reason, a *different*
diagnostic per reboot, a saved state, a bounded reconnect window and a 3-reboot
budget) to obtain a normal boot; and if charger mode persists after a genuine
normal boot, `NEEDS_OWNER_TEST` with the owner-side power-button procedure
(handset off, on battery, cable out, boot with the power button, ~30 s, then
reattach the cable) — never a flash, never a fake.

**2. The boot animation.** The animation's *policy*, *receipt* and *ownership* are
userspace and **are** deployed (`boot-animation-runtime`: `nuxel-animation-claim`,
`nuxel-animation.service`, the shipping MP4 at
`/usr/share/nuxel/boot/nuxel-boot-animation.mp4`). What is *not* deployed is the
initramfs half — the packed `NUXANM01` container and the player inside the BOOT
container. It is built on a host by `tools/s10plus/nuxel-anim-pack.py` (also
deployed, so the recipe exists on the device) and placed by a BOOT update.
The user-visible claim ("one whole cycle reaches the glass before the launcher
takes the panel") stays `NEEDS_OWNER_TEST` until a human watches a boot; the
receipts in `/run/nuxel-anim-handoff` and `/var/lib/nuxel/fb-owner` are the
machine half of that evidence, and they are captured by the live group.

## The rule, stated once

Nothing in this mission flashes: no BOOT/USERDATA/SYSTEM/RECOVERY/DTB/DTBO/
VBMETA/radio/modem image, no repartitioning, no Heimdall/Odin/wrapper, no
Download Mode/TWRP/adb, no EFS/SEC_EFS/PIT/calibration/IMEI write, no kernel
install, no silent hardware identity change. Any procedure that would need one of
those is replaced by a `BLOCKED_*` verdict with the reason written down — which is
exactly what this file is.
