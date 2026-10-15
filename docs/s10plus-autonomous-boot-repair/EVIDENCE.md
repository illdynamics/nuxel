# EVIDENCE INDEX

All captures are read-only and live under `scripts/s10plus-debug-pack/captures/`.
No device partition was written during evidence collection.

| Capture | Content |
|---|---|
| `20261015T065537Z-full-collection-8924/` | This cycle: pack `12-full-diagnostics.sh` (pstore, last_kmsg, TWRP logs, partitions/mounts, recovery kernel info, USB snapshot) + offline boot-image and rootfs audits |
| `20261015T065605Z-readback-9345/` | BOOT partition readback SHA-256 vs local image -> **MATCH** |
| `20261015T063659Z-full-collection-5886/` | Prior cycle: full collection |
| `20261015T063922Z-mission-cybertiel/` | Prior cycle: partition headers (`boot_hdr.bin`, `recovery_hdr.bin`), DT table slices, sysfs uevents, `/proc/device-tree/chosen/bootargs` |
| `20261015T064803Z-boot-image-7315/`, `...064926Z-boot-image-7727/` | Prior cycle: offline boot-image audits (header, FDT, initramfs listing) |

## Key raw files

* `.../20261015T065537Z-full-collection-8924/kernel/cmdline.txt` — proves the
  bootloader-built cmdline: `console=ram loglevel=4 sec_debug.* androidboot.hardware=exynos9820
  androidboot.revision=26 androidboot.dtbo_idx=9 ... root=PARTUUID=52444E41-494F-2044-7379-7374656D0000`.
  **No `nuxel.*`, no UFS by-name root.**
* `.../kernel/pstore-settings.txt` — `ramoops console_size=0`, `pmsg_size=16384`,
  `record_size=16384`, `dump_oops=1`, `mem_size=32768` -> no console log survives a panic.
* `.../previous-boot/last_kmsg.txt` (735 lines) — **recovery** S-Boot log only
  (`Samsung S-Boot 4.0 for SM-G975F`, `bootmode=2`, `make_security_decisions : (RECOVERY)`).
  Not Nuxel evidence.
* `.../previous-boot/boot-reason.txt` — `sec_debug.reset_reason=9` (PIN reset into recovery).
* `.../device/partition-by-name.txt` — boot=sda14, recovery=sda15, userdata=sda31, dtb=sda12, dtbo=sda13.
* `.../device/read-only-block-sizes.txt` — BOOT 57,671,680 B; USERDATA 119,126,622,208 B; RECOVERY 67,633,152 B.
* `.../pstore/NO-PSTORE-FILES.txt` — `/sys/fs/pstore` was empty; the pack did **not** clear it.

## Offline evidence (this cycle)

* Fedora rootfs: `/usr/lib/os-release` -> Fedora Linux 43; `/usr/lib/systemd/systemd`
  = systemd **258.11-1.fc43**, aarch64 ELF, interp `/lib/ld-linux-aarch64.so.1`;
  strings contain "Warning! Reported kernel version %s is older than systemd's
  required baseline kernel version %s" (warning, not abort).
* Kernel payload `Image.gz` 16,030,259 B -> 44,980,232 B ARM64 `Image`,
  sha256 `33cac63a8b0c0f575a2e1bc782c1efe54018658f65ba741679531c113ac0ec57`
  (matches `build/out/s10plus/build-manifest.json`). No embedded `IKCONFIG` blob,
  so kernel features cannot be audited from the image.
