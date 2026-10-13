So I patched just the 512‑byte cmdline field → `root=/dev/mmcblk0p64` (the raw userdata node). Byte‑exact, reversible, new tool + artifact:
- `tools/patch-boot-cmdline.py` → `build/out/g7power/nuxel-ocean-boot-rootfix.img` (only the cmdline field differs; kernel/ramdisk/dtb identical).

I also verified from upstream lk2nd source/docs why the 512 KiB trick works (`boot` is split: first 512 KiB = lk2nd, rest = real boot image), so **stock ABOOT alone can install lk2nd + the Nuxel payload in one write** — I don't actually need lk2nd's own fastboot, which removes the mode you had trouble with.

**2. Bad news — my fault: ABOOT's fastboot is now wedged.**
I asked this old ABOOT for `getvar current-slot`; it doesn't implement it, never replies, and left ABOOT mid‑command. Since then every fastboot command hangs (USB reset didn't clear it). It needs a power cycle from you.

**What I need from you (one step):**

1. Hold **Power ~15 s** until the screen goes black (force off).
2. From off: hold **Volume Down**, press **Power**, keep holding Vol Down until the Motorola **"AP Fastboot Flash Mode" / FLASH MODE** screen appears.
3. If your Mac still can't see it, unplug/re‑plug the USB‑C cable.
4. Tell me "ready".

Then I'll do the rest headlessly: verify the device, probe whether ABOOT allows `fastboot flash userdata` (it has a factory allow‑list — that decides `root=` = `userdata`/`mmcblk0p64` vs `system_b`/`mmcblk0p63`), rebuild the combined `lk2nd@0 + rootfix‑boot@512 KiB` image, flash **both** `boot_a` and `boot_b` (so it doesn't matter which slot lk2nd deactivated), write the 478 MiB rootfs, and reboot. Revert path back to stock is in `fb.md` and unchanged.


---
# STATUS / PLAN — 2026-10-12 ~18:30 local (black-screen root cause FIXED offline)

## Root cause of "lk2nd menu then black" (CONFIRMED from lk2nd source)
lk2nd validates the **payload boot image's DT region** with
`dev_tree_validate()` + `dev_tree_get_entry_info()` (platform/msm_shared/dev_tree.c).
That path requires a **QCDT table using lk2nd's own header layout**:
`struct dt_table { u32 magic; u32 version; u32 num_entries; }` = **12-byte header**
(`DEV_TREE_HEADER_SIZE 12`), entries begin at offset **12**, V3 entry = **40 bytes**
(`DEV_TREE_DT_ENTRY_SIZE_V3`). Field order per `struct dt_entry`:
`platform_id, variant_id, board_hw_subtype, soc_rev, pmic_rev[4], offset, size`.

What we actually flashed:
- `nuxel-ocean-boot(-rootfix).img`: raw FDT (`0xd00dfeed`) after the ramdisk →
  lk2nd: **"ERROR: Bad magic in device tree table"**.  (oemlog.txt)
- `nuxel-ocean-boot-qcdt*-sysb.img`: a **20-byte Qualcomm header**
  (`magic,version,num_entries,entry_size,total`) with `entry_size=0x15d` and a
  byteswapped entry → lk2nd read entries from the wrong offset →
  **"Unable to find suitable device tree for device (349/0x00010000/0x00010008/0)"**.
  (oemlog2.txt)  Device identity from that print: `board_platform_id=349 (0x15d)`,
  `board_soc_version=0x00010000`, `board_target_id=0x00010008`
  ⇒ `board_hardware_id & 0xff = 0x08`, `board_hardware_subtype = 0`.

## Fix built + validated offline
- New tool `tools/build-qcdt-boot.py` — rewrites ONLY the DT region of a v1 boot
  image into a lk2nd QCDT v3 table (12-byte header, 40-byte entries) wrapping the
  **unchanged** mainline `sdm632-motorola-ocean` DTB (`msm-id=<0x15d 0x0>`,
  `board-id=<0x141 0xc100>`). Emits a 136-entry matrix (variant_id 0x008..0x1008 ×
  board_hw_subtype 0x000..0x700) all pointing at the same DTB so lk2nd's
  `platform_dt_absolute_match()` succeeds for any plausible hw-id/DDR subtype.
- Artifacts:
  - `build/out/g7power/nuxel-ocean-boot-lk2nd-qcdt.img` (21651456 B)
    sha256 `2e4c4f957154788def058e379c6555b3c535788e90d3daa6c8c929ffe80440b0`
  - `build/out/g7power/lk2nd-nuxel-qcdt-combined-boot.img` (22175744 B)
    = lk2nd@0 + boot@512KiB, sha256 `462f04d987b5d4663638275417b95b4e81010bc289339cfd27d1110e5f964157`
  - payload cmdline unchanged: `... root=/dev/mmcblk0p64 rootfstype=ext4 rootwait rw`
- Verified: embedded DTB is byte-identical to the original mainline DTB
  (`sha256 43632158…9797`); QCDT passes a faithful re-implementation of
  `dev_tree_validate()` + `platform_dt_absolute_match()` for every hw-id in
  {0x008..0x1008} and every HLOS subtype {0x000..0x700}.

## BLOCKER — phone is NOT connected
`dmesg`: `usb 3-2: ... idVendor=22b8 idProduct=2e80 Product "Fastboot ocean S"
SerialNumber ZY326RGXCM` connected at ~t+926093s then `USB disconnect` at
~t+926126s. It has not re-enumerated since. `fastboot devices` and `lsusb` show
nothing → the device is physically unplugged (or its port is dead). Nothing can
be flashed until it re-enumerates.

## Flash plan (once it re-enumerates) — avoids the ABOOT-wedging getvars
```
# safe verification only (NEVER current-slot/slot-suffixes/has-slot:*)
/tmp/fb getvar product ; /tmp/fb getvar securestate ; /tmp/fb getvar max-download-size
/tmp/fb flash dtbo   build/out/g7power/stock/firmware/extracted/dtbo.img   # stock dtbo
/tmp/fb flash boot_a build/out/g7power/lk2nd-nuxel-qcdt-combined-boot.img
/tmp/fb flash boot_b build/out/g7power/lk2nd-nuxel-qcdt-combined-boot.img
/tmp/fb flash userdata build/out/g7power/nuxel-ocean-rootfs.img           # 478 MiB
/tmp/fb reboot
```
Revert to stock: `flash dtbo <stock dtbo.img>` + `flash boot <stock boot.img>`.
