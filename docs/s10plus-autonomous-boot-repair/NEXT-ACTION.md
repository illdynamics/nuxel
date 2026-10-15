# NEXT-ACTION — cycle 12 (2026-10-15): A25 IS ON THE PHONE, WAITING FOR A POWER CYCLE

```
STATE              = A25 FLASHED + READBACK VERIFIED, NOT YET REBOOTED
CANDIDATE          = A25   "single-instance UI + console-owned postboot supervisor"
BOOT.img sha256    = ad5ca5d9cd3165dfc0f8ee9893febd6523ee1f606b5b60901e7add25f4170a9f
KERNEL sha256      = 48b9810fbbcbac0e5ce3159c7750f0b96e1335039d1c245579baad3d87f3c27d (Image-A25)
INITRAMFS sha256   = 88e9b60f528cd9e48f08fc9f71988e34a6bc78b5191863193857f0f6bfc4210d
UI sha256          = 0673023f3b620707b1baa0ced886b89e5ff95f9eacae16ff0e292ff476d906c9
CONSOLE sha256     = 25986d1fe101b60dcccc1b3160e1cfd00a9eddccc191c3eb818facca127d2dc1
FLASH              = BOOT-only, dd in place, full 51,718,144-byte SHA-256 readback PASS
BOOT backup        = backups/nuxel-adb/20261015T184133Z-R58M75KDB2X
A23                = FAILED_USER_RETURNED_TO_TWRP (UI never started: stalled boot graph)
A24                = FAILED_USER_RETURNED_TO_TWRP (UI RAN and reached PHONE_UI_READY, but a
                     SECOND renderer -- my own diagnostic `--once` run -- powered the panel
                     down through fb_release; the operator saw black and reset)
PERMANENT AGREEMENT: if the operator has returned the phone to TWRP after a pending test,
that test FAILED -- capture, classify, continue. No confirmation question is needed.
```

## 1. THE ONE THING NEEDED FROM THE OPERATOR: a power cycle

The phone is sitting in TWRP with A25 flashed. Nothing else can proceed without a boot,
and there is no software path to start one (the Nuxel gadget is CDC-ACM only, no adb).

**Both options boot A25; they differ only in whether the touchscreen can come up:**

| Action | Boot mode | Consequence |
|---|---|---|
| unplug USB, then hold POWER + VOL-UP + BIXBY to reset **and do not re-plug until the Nuxel screen appears, then plug USB back in** | normal (non-LPM) | touchscreen CAN initialise (A17 proved `input: sec_touchscreen` on a normal boot) and the live console comes up when USB is re-attached |
| reset with USB attached | `androidboot.mode=charger` (measured on A23/A24) | UI + console + handoff all work, but there is NO touch input device at all |

Recommendation: the first option, because touch is the next milestone. If the phone shows
the Nuxel UI on the panel, say nothing and it is a pass; if it looks wrong, a photo settles
the colour question in one glance.

## 2. What A25 fixes, and what the next boot must prove

| A25 change | Why | Next-boot check |
|---|---|---|
| UI is **single-instance** (respects `/var/lib/nuxel/ui.pid`) | A24: a second renderer's exit ran `fb_release` -> `disable regulator(1:vdd2)` -> dark panel | `NUXEL_UI_ALREADY_RUNNING` in dmesg if a second instance is attempted; the panel must never go dark again |
| `nuxel-console` **spawns the post-handoff supervisor** after chrooting into the new root | A24: `/init`'s detached subshell died at `switch_root` (its toybox helpers no longer resolved), so `bootreport.txt` was never written and the UI was never auto-started | `/var/lib/nuxel/bootreport.txt` must exist and name the stalled systemd job |
| (A24 carry-over) UI unit with **no ordering, no conditions**, enabled in `sysinit.target` **and** `multi-user.target` | A24: the unit stayed inactive behind the stalled graph | `systemctl is-active nuxel-ui` = active |
| (A24 carry-over) console **respawns its shell** after any disconnect | A23: one host disconnect killed live debugging for the whole boot | unplug/replug the Mac end; the prompt must come back |

Regression baselines that must still hold: A16 first light, A18 service execution +
cgroup2 + journald, A21/A22 MP4 at 24.00 fps with 0 skips, A23 ABGR colour order.

## 3. Then, in order

1. Read `/var/lib/nuxel/bootreport.txt` and **name the stalled systemd job** (the open
   root cause in `NUXEL-BOOT-STALL.md`); candidates are `systemd-firstboot.service` and
   `rpmdb-rebuild.service`. Fix it in the rootfs build sources, not just on the device.
2. Verify the UI visually and by screenshot: `echo 'screenshot small' > /run/nuxel-ui.cmd`,
   then pull `/var/lib/nuxel/ui.ppm` (PPM P6, written in the panel's real channel order).
3. Touch: `ls /dev/input/event*`, `cat /sys/class/input/event*/device/name`, and only then
   the multitouch capabilities. The A23/A24 boots were charger-mode, so their input
   evidence measures nothing about the hardware.
4. MP4 handoff: already exercised on A24 (`ANIMATION_STOP_SIGNALLED pid=3525`); re-confirm
   that the animation is the *original* artwork with the correct colours before it hands off.
5. DRM/Phosh: unchanged, tracked separately in `PHONE-UI-HANDOFF.md` §3 -- the existing
   kernel has no DRM/KMS, so this is a kernel-porting project, not a config flag.

## 4. Rules unchanged

* RECOVERY is never written. EFS/SEC_EFS, PIT, bootloader, radio, Kn x: untouched.
* USERDATA is never rewritten for a userspace change: the UI ships inside the BOOT
  candidate and `/init` installs it into the rootfs (previous binary kept as
  `/usr/lib/nuxel/nuxel-ui.prev`); after that, live deployment over the console
  (`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`) is the normal path.
* Never run a second framebuffer client while the UI owns the panel (A24's lesson).
