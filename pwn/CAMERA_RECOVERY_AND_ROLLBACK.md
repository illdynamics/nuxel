# NUXEL S10+ Camera — Recovery & Rollback

**Date:** 2026-11-20
**Device:** SM-G975F beyond2lte, kernel 4.14.253-gf7194c1d15ed-dirty

## Current known-good state (as of this session)

- **Running kernel:** `4.14.253-gf7194c1d15ed-dirty` (Samsung downstream Exynos9820).
- **Kernel source on device:** `/root/kbuild/src` @ git HEAD `f7194c1d15eded1c2a1a4dc63825b26103435cc0`.
- **Firmware (all hash-verified, owner-stock G975FXXS9DTK9):** `/system/vendor/firmware/`
  and `/usr/lib/firmware/` — `fimc_is_lib.bin`, `fimc_is_rta.bin`, `fimc_is_fw_mcu.bin`,
  `setfile_{2l4,3m3,3p9,3j1,4ha}.bin`.
- **Userspace tools:** `/usr/local/bin/nuxel-fimc-capture{,2}`, `nuxel-ion-capture`,
  `nuxel-fimc-full-capture`, `nuxel-fimc-leader-capture{,2}`.

All this session's changes are **userspace-only and reversible** (file copies + new tools).
No kernel, boot, partition, EEPROM, calibration or bootloader was modified.

## TWRP reflash agreement (authorized)

From `pwn/cam.md` / `cam.md`: flashing via TWRP is authorized for the camera bring-up.
Procedure understood:
- Reboot phone to recovery, flash via `adb` over USB.
- If the phone boots back into TWRP = flash failed / bootloop / hang / crash.
- Re-investigate, fix, reflash, reboot until it boots Nuxel.
- SSH key `~/.ssh/wicked_wqn_id_rsa`, dev `root@10.11.12.99`, also USB-connected.

## Recovery path

1. **Kernel recovery:** last-known-good boot image must be preserved before any
   boot-critical flash. Flash is done via TWRP (adb + dd) or heimdall (BOOT).
2. **USB/TWRP:** phone is USB-connected; recovery bootable via TWRP.
3. **Userspace rollback:** `rm` the created `/system/vendor/firmware/` blobs and
   `/usr/local/bin/nuxel-*` tools (or restore from `/tmp` backups taken before deploy).

## Rollback plan (for the pending Strategy B kernel driver)

- Preserve current boot image + `Image.gz` hash + DTB hash before flash.
- Keep `fimc-is2` vendor driver in-tree (do not remove; the new custom driver must
  coexist or be disabled at runtime via `modprobe.d`/device-tree).
- Record exact installed image path + SHA-256 per the "Phase 10" checklist.
- If a new kernel fails to boot, restore the last-known-good image via TWRP.

## Do NOT modify

EFS, IMEI, modem calibration, protected keys, bootloader, unrelated partitions.
Only camera-related kernel/userspace changes are in scope.
