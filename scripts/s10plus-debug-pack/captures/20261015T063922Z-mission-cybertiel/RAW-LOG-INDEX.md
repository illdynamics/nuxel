# Raw log index

All paths relative to `scripts/s10plus-debug-pack/captures/`.

## `20261015T063659Z-full-collection-5886/` (pack run)

| File | What it is | Trust |
|---|---|---|
| `device/boot-properties.txt` | codename, bootloader, revision, hw | device fact |
| `device/partition-by-name.txt` | by-name → `/dev/block/sdaN` map | device fact |
| `device/read-only-block-sizes.txt` | BOOT/RECOVERY/USERDATA/DTB/DTBO byte sizes | device fact |
| `device/proc-partitions.txt` | kernel partition table | device fact |
| `device/fstab.txt`, `device/mounts.txt` | TWRP fstab / live mounts | device fact |
| `device/recovery-dtb-identity.txt` | recovery DTB model/compat | device fact |
| `kernel/cmdline.txt` | **the cmdline the kernel actually got** | device fact |
| `kernel/uname.txt` | recovery kernel version/build | device fact |
| `kernel/pstore-settings.txt` | ramoops params (`console_size=0`) | device fact |
| `kernel/kernel-last-reset.txt` | reset-related nodes | device fact |
| `kernel/recovery-config.gz` | recovery kernel config | device fact |
| `previous-boot/last_kmsg.txt` | **S-Boot log of the *recovery* boot** (NOT Nuxel) | device fact, wrong boot |
| `previous-boot/boot-reason.txt` | reset reason 9 / bootmode 2 | device fact |
| `previous-boot/boot-environment.txt` | TWRP identity/root | device fact |
| `pstore/NO-PSTORE-FILES.txt`, `pstore/listing.txt` | pstore empty | device fact |
| `recovery/tmp/recovery.log` | TWRP log (no partition writes; /data never mounted) | device fact |
| `recovery/current-recovery-dmesg.txt` | **TWRP's** dmesg — not Nuxel evidence | device fact, wrong boot |
| `boot-image/boot-analysis.json` | header, DTBs, initramfs listing of the flashed image | offline host |
| `boot-image/INITRAMFS-init.txt` | extracted `/init` from the flashed image | offline host |
| `boot-image/fdt-00-at-22054912.dtb` | the merged DTB inside the flashed image | offline host |
| `rootfs-image/e2fsck-readonly.txt` | `e2fsck -fn` on the Fedora rootfs (clean, exit 0) | offline host |
| `rootfs-image/stat_*.txt`, `list_*.txt`, `cat_*.txt` | rootfs metadata audit | offline host |
| `TRIAGE.md` / `TRIAGE.json` | pack pattern triage (not a verdict) | derived |

## `20261015T063922Z-mission-cybertiel/` (targeted reads)

| File | What it is |
|---|---|
| `device/boot_hdr.bin` | first 2 KiB of BOOT (`sda14`) = the flashed header |
| `device/recovery_hdr.bin` | first 2 KiB of RECOVERY (`sda15`) = TWRP header incl. `cmdline='buildvariant=eng'` |
| `device/dtb_hdr.bin`, `device/dtb_part_256k.bin` | `dtb` partition (sda12) dt_table: 1 wildcard entry, 239,644 B |
| `device/dtbo_hdr.bin`, `device/dtbo_part_1920k.bin` | `dtbo` partition (sda13) dt_table: 10 entries; entry[9] = rev 26 |
| `device/uevent-partname.txt` | `/sys/class/block/sd*/uevent` — proves `PARTNAME=userdata` |
| `device/chosen-bootargs.txt` | `/proc/device-tree/chosen/bootargs` vs `/proc/cmdline` — the cmdline proof |
| `device/display-state.txt` | no `/dev/dri`, no `/sys/class/drm`; fbdev only |

Derived extractions (scratch, `/tmp`): `merged.dtb`, `dtbpart0.dtb`, `dtbo9.dtb`,
`base_plus_dtbo9.dtb`, `merged_plus_dtbo9.dtb` (the idempotence test).
