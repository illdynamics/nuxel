# NUXEL S10+ — Known-Good Boot Image Set (verified provenance)

**Device:** SM-G975F (beyond2lte, Exynos9820) · **Kernel:** 4.14.253-gf7194c1d15ed-dirty #3
**Document date:** 2026-11-21

This records the single verified-booting Nuxel boot-image set and how to reproduce it.

---

## The verified image set (three partitions, matched)

| Partition | by-name | Expected bytes | Contents |
|---|---|---|---|
| BOOT (kernel) | sda14 | 57,671,680 (partition), image ≈ 48 MB | raw ARM64 `Image` + LZMA ramdisk, boot header v1, `dt_size=1` |
| DTB (base)   | sda12 | 8,388,608 | stock base `exynos9820.dtb` (+ zero padding) |
| DTBO (overlay) | sda13 | 8,388,608 | 10-entry table; entry[9] = `exynos9820-beyond2lte_eur_open_26.dtbo` |

S-Boot assembles the DT from `dtb`+`dtbo[dtbo_idx=9]` and jumps into the raw Image in `boot`.

---

## Known-good component SHA-256 (verified on macOS)

Kernel (the image that actually booted, from live `boot-current.img`):
- **raw ARM64 Image** `45,717,512` B
  `d5e4fe656b7dda319f2e301b82f8dbd51597151dee8d2d47dd4bbae02671a5a4`
  (source: `~/Downloads/nuxel-main 2/packs/work/bootloop-fix/boot-unpacked/Image`)
- Rebuilt known-good #3 raw Image `45,848,584` B
  `71be6f282afebc12138f5eb7b610641e7edb48666bcac5750fd7824151537498`
  (source: `.../fix2/Image-raw`) — same kernel, size differs only by rebuild.

Ramdisk: **LZMA** `2,424,832` B
  `0dd0fb5a3d6895f28d8861d967382a0b87182d0f9c63b1d560393818b290f407`
  (uncompressed cpio `8,791,372` B, 84 records:
   `f19b369303ede99e7e4a8360c3a83a66abb690b2df6c0854bf6897862f8ef215`)

Merged reference DTB (inner FDT `376,101` B; NOT appended to the booting image):
  `0e308eee67c90d54b635b375de7af573dc204c1e9d5cc3e12464ff4a92c6294b`

---

## Boot header (the only proven values)

```
magic       = "ANDROID!"
kernel_size = 45717512          (raw Image, NOT gzip — S-Boot does not decompress)
kernel_addr = 0x10008000
ramdisk_size= 2424832          (LZMA ramdisk)
ramdisk_addr= 0x11000000
tags_addr   = 0x10000100
page_size   = 2048
header v1   = dt_size=1 (header_field40 == 1)   # NO appended DTB
os_version  = 0x18000171
cmdline     = buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw
```

> The device tree is **NOT** in the boot image. S-Boot reads it from the `dtb`
> partition and applies `dtbo` entry `androidboot.dtbo_idx=9`. Do not append a DTB
> to the boot image: a fully-appended DTB makes the image exceed the 57,671,680-byte
> `boot` partition and gets truncated.

---

## Reproduce the matched set (rebuild procedure)

1. **DTB partition (sda12, 8,388,608 B):** take the base DTB and pad to 8 MiB:
   ```
   base=.../kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/exynos9820.dtb
   # 238,880 B; dd to 8,388,608 B (8 MiB) for the dtb partition
   ```
   (Stock provenance: this is what S-Boot expects; do NOT merge the camera overlay into it.)

2. **DTBO partition (sda13, 8,388,608 B):** 10-entry Samsung DTBO table with the
   vendor `exynos9820-beyond2lte_eur_open_{00..29}.dtbo` overlays from the checked-out
   downstream tree at `f7194c1d15ed`, entry index 9 = `..._open_26.dtbo`
   (`181,684` B). Rebuild the partition table exactly like `rebuild_dtbo.py` but
   keeping every entry as-built (NO no-op replacement).

3. **BOOT partition (sda14):** pack the raw Image + LZMA ramdisk with
   `boot/s10plus/pack-boot-v1.sh` using `--v1-spec`, `dt_size=1` (no `--dtb`),
   the header values above, and the exact cmdline. Output < 57,671,680 B.

4. Verify each image SHA-256 and size against its partition capacity **before**
   flashing; flash `dtb`+`dtbo`+`boot` as a matched set (Download Mode heimdall, or
   TWRP `dd`), then verify readback byte-identical before rebooting.

---

## Provenance / source of truth

- Kernel source: `https://github.com/Linux4/android_kernel_samsung_exynos9820`
  @ `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253 downstream,
  `exynos9820-beyond2lte_defconfig`).
- DTBO overlays: same tree, `arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_*.dtbo`.
- Nuxel flash policy (`boot/s10plus/flash-heimdall.sh`): only BOOT + USERDATA are
  sanctioned via heimdall; DTB/DTBO/RECOVERY are **denied** — the session-7 `dd`
  that replaced sda12/sda13 violated this and caused the failure.

## Safety invariants (never change)

- Never touch: `efs efsg efs/-related persist param up_param steady keystorage
  carrier cp_debug misc`, `vbmeta`, bootloader lock state, IMEI/device-unique data.
- Never repartition, never replace the PIT, never relock/restore Knox (already tripped).
- Never wipe `userdata` (sda31) — it holds the Nuxel rootfs and all camera work.
