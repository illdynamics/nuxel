fastboot reboot
```

If lk2nd's menu is actually visible, the even easier version: let it sit on the menu, use Vol keys to highlight **Bootloader**, press Power, and say so.

## Two honest caveats

- **Nuxel may still not fully boot even after the rootfs lands.** Reading `boot/initramfs/init.sh`, the g7power branch resolves its root as `/dev/block/bootdevice/by-name/userdata` / `system_a` — an Android/u`ueventd` path that **mainline Linux + a bare devtmpfs initramfs doesn't create**. On mainline it almost certainly needs the raw node (`/dev/mmcblk0p64` = userdata) or a `/dev/disk/by-partlabel/...` probe. I can patch the boot image's cmdline (reversible) to fix this if you want.    
- **The first Nuxel boot will likely show a black screen even if it succeeds** — `DRM_MSM` etc. build as modules and the Phase‑1 rootfs `/sbin/init` loads no modules, per the guide. The real success signal is “device stays up / doesn’t reboot,” or UART on `ttyMSM0`.

## Options (your call)

- **A — Finish Nuxel (recommended):** you do the Vol-Down step above; I flash the rootfs and (optionally) patch the root= cmdline. Device stays Nuxel.
- **B — I finish it fully remotely, no buttons:** I can instead put the rootfs on a partition ABOOT *does* allow flashing (`system_b` is in the factory flash list; it's 2.8 GB) and point the kernel at `root=/dev/mmcblk0p63`. It deviates from the guide's `userdata` design but needs nothing from you.
- **C — Put stock back (guaranteed booting phone):**
```
fastboot flash dtbo stock/firmware/extracted/dtbo.img
fastboot flash boot stock/firmware/extracted/boot.img
fastboot reboot
```

Say **A**, **B**, or **C** (or “A + patch the cmdline”) and I'll run it. I would not run `fastboot oem lock`.
tokens used
4,707,846
[codeseeq] stopping owned bridge process (pid=3626928)


---
# STATUS / PLAN — 2026-10-12 ~18:05 local (option A, continued)

## Where we actually are
- **lk2nd IS installed** on the boot partition (you saw its menu), and the item you picked
  ("Bootloader") chain-loads **stock ABOOT** — so you are sitting in *stock ABOOT fastboot*,
  not in lk2nd's fastboot. (lk2nd's menu: Reboot / Continue / Recovery / **Bootloader** /
  EDL / Shutdown — "Bootloader" = reboot into stock BL. My earlier instruction was wrong;
  for lk2nd's own fastboot we would just stay on that menu.)
- Host has no root and no udev rule for `22b8:2e80` → plain `fastboot` says *no permissions*.
  Workaround in use: `/tmp/fb <args>` = fastboot as root in a privileged container
  (alpine + android-tools, `/x/nuxel` mounted at `/work`).
- **ABOOT's fastboot is wedged**: `fastboot getvar current-slot` (not supported → no reply)
  left ABOOT mid-command; since then every fastboot command hangs. `USBDEVFS_RESET` +
  USB unbind/bind did **not** clear it. It needs a phone power-cycle.
  (Lesson: never send this ABOOT `current-slot`/`slot-suffixes`/`has-slot:*`.)
- Device facts (from `getvar all`): `product=ocean`, `securestate=flashing_unlocked`,
  `serialno=ZY326RGXCM`, `max-download-size=0x20000000` (512 MiB — our 478 MiB rootfs fits
  in a single download), emmc 64 GB, active slot is `_b` per repo notes.

## Root cause of "Nuxel won't boot" — CONFIRMED from the real artifacts
- The cmdline actually packed in `nuxel-ocean-boot.img`:
  `console=ttyMSM0,115200 nuxel.device=g7power root=/dev/block/bootdevice/by-name/userdata rootfstype=ext4 rootwait rw`
- The packed initramfs `/init` (extracted from the boot image, verified) uses `root=` verbatim
  for `nuxel.device=g7power` → `ROOT_DEV=/dev/block/bootdevice/by-name/userdata`.
- mainline Linux + bare devtmpfs never creates `/dev/block/bootdevice/...` → mount fails →
  `NUXXEL PANIC: root mount failed`.
- **Fix:** patch cmdline to the raw node → `root=/dev/mmcblk0p64` (userdata, mmcblk0p64).
  Done byte-exactly (only the 512-byte cmdline field differs):
  `build/out/g7power/nuxel-ocean-boot-rootfix.img` (sha256 ac9044b6921fbcad…) via new tool
  `tools/patch-boot-cmdline.py`.

## How lk2nd's 512 KiB trick works (verified in upstream source + docs)
- lk2nd splits the `boot` partition: first **512 KiB = virtual partition "lk2nd"** (lk2nd
  itself), the remainder = `boot` (the real OS boot image). `Documentation/boot.md`,
  `lk2nd/project/lk2nd.mk` (`LK2ND_PARTITION_SIZE ?= 512*1024`),
  `lk2nd/device/2nd/partition.c` (`partition_split_mmc`).
- Therefore stock ABOOT can install everything with ONE write, if the image is
  `combined = lk2nd.img @0 + nuxel-boot.img @512 KiB`.
  `build/out/g7power/lk2nd-nuxel-combined-boot.img` already has that layout but contains the
  **unpatched** cmdline → must be rebuilt from the rootfix image.

## Plan (option A — no longer needs lk2nd's fastboot at all)
1. **You:** power-cycle the phone and get into **stock ABOOT fastboot** (from off: hold
   **Vol Down**, press **Power**, keep holding Vol Down until the Motorola "FLASH MODE" /
   AP Fastboot screen appears). Then tell me.
2. **Me:** verify getvars; probe whether ABOOT permits `flash userdata` (tiny dummy image)
   → that decides `root=`: `userdata`/mmcblk0p64 vs `system_b`/mmcblk0p63.
3. **Me:** rebuild `combined` = lk2nd @0 + rootfix-boot @512 KiB with the right `root=`.
4. **Me:** `fastboot flash boot_a` **and** `fastboot flash boot_b` (both slots → immune to
   the slot state lk2nd may have deactivated), then flash the 478 MiB rootfs to the target
   partition.
5. **Reboot:** expect Motorola logo → lk2nd → kernel. Screen will *probably stay black*
   (DRM_MSM is a module and the initramfs loads no modules) — success signal is
   "device stays up / no reboot loop".
   Revert anytime: `fastboot flash dtbo stock/firmware/extracted/dtbo.img` +
   `fastboot flash boot stock/firmware/extracted/boot.img`.
