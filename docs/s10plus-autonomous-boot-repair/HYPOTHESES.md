# HYPOTHESES (cycle 2, after the A2 result)

## H-KERNEL-GZIP — CONFIRMED (hardware)
S-Boot branches to `kernel_addr` (0x10008000) without decompressing. With the
gzip payload (`1f 8b 08 …`) the CPU took an immediate UNDEFINED-instruction
exception: 7 identical loads -> zero console bytes. With the raw `Image` (A2) the
kernel ran until t≈1.96 s and its panic dump is in pstore.
**Evidence:** E1/E2 (7 silent loads) + A2 panic with
`linux_banner: Linux version 4.14.253 (nuxel@nuxel-phosh)`.

## H-RAMDISK-DELIVERY — the ramdisk handed to the kernel is unusable  (CONFIRMED mechanism, A3 = fix)
`unpack_to_rootfs()` returned "junk in compressed archive", which per
`init/initramfs.c` means the buffer had no recognisable magic or never reached
`TRAILER!!!`. S-Boot reports `ramdisk size = 0x5be800` = 6,022,144 while our
payload is 6,022,352 B, and the live DT shows S-Boot relocates the initrd to
`0x89000000` with `initrd-end = 0x89a66800` = its own rounded length. A 6,022,352
B gzip stream delivered as 6,022,144 B is truncated; `lib/decompress_inflate.c`
does not treat `Z_BUF_ERROR` as fatal, so the partial cpio parse ends in
`state != Reset` = "junk in compressed archive".
**Fix under test (A3):** uncompressed `newc` cpio zero-padded to exactly
8,194,048 B (multiple of 2048/512). No decompressor, and any S-Boot size
rounding can only discard trailing zeros.

## H-CONTAINER-VERSION — the packer wrote the DTB size where `header_version` lives (FIXED in A3)
S-Boot logs `[UFDT] BOOT IMG HDR V376101` for our image and `V1` for the
recovery image, so it really does branch on offset 40. A3 writes a real v1
header. Kept in the same candidate as the ramdisk fix because both are
"make the container match the device's own booting image", and the mission's
cycle budget is 3 hardware candidates.

## H-SAR-OOM — Samsung's in-kernel ramdisk fallback cannot load a >4 MB ramdisk (EXPLAINED, not a target)
`init/do_mounts.c`: when `android_bootmode != 2` the kernel calls
`mount_sar_ramdisk("/dev/android_boot")`, which kmallocs the ramdisk from the
boot partition. `mm/page_alloc.c:4258` WARN + `SAR_RD: Out of memory` for
6.0 MB (order > MAX_ORDER-1 = 4 MB). A3's uncompressed cpio is 8 MB, which is
**larger**, so this fallback would fail again - which is fine: A3 must succeed
via the *initramfs* path, and that is what the diagnostics will show.

## H-INIT-GROUP-EXIT — Samsung panics when PID 1 exits (SYMPTOM)
`Kernel panic - not syncing: init group exit` fires when PID 1's group exits;
here PID 1 was the init of the *fallback* root (sda25, from S-Boot's
`root=PARTUUID=…`), i.e. downstream of the ramdisk failure. It is a symptom and
does not indicate a Fedora or systemd defect.

## Still open
* H-DISPLAY: the Nuxel kernel *did* initialise display drivers (`130b0000.displa`,
  `decon0/2`, `dsim0-wq`, `panel-bl-thread`, `decon_devfreq_change_task` appear
  in the A2 task dump), so DRM should exist; whether fbdev/`/dev/fb0` exists for
  `nuxel-firstlight.service` is untested.
* H-FEDORA: systemd 258.11 on a 4.14 kernel warns about the version baseline; it
  is not fatal. Untested until the rootfs handoff succeeds.
