# ROOT CAUSE — cycle 2 (2026-10-15)

## Summary
The Samsung-logo bootloop had **two independent, now-identified causes**, both in
the BOOT container, not in the kernel, the initramfs contents, or Fedora:

1. **FIXED (A2): the kernel payload was gzip.** S-Boot jumped to `kernel_addr`
   (0x10008000) which held a gzip stream (`1f 8b 08 …` = `0x00088B1F`, an
   unallocated ARM64 encoding) -> immediate exception before any console output.
   Replacing the payload with the raw 44,980,232-byte `Image` made the kernel
   execute for the first time. **Stage B proven on hardware.**
2. **A3 TARGET: the ramdisk was not usable by the kernel.** With a real kernel
   we captured the actual failure at t=0.965 s:
   ```
   Trying to unpack rootfs image as initramfs...
   rootfs image is not initramfs (junk in compressed archive); looks like an initrd
   Freeing initrd memory: 5880K
   ```

## The A2 panic is fully explained (from `last_kmsg` + pstore)
```
[0.965408] Trying to unpack rootfs image as initramfs...
[0.965767] rootfs image is not initramfs (junk in compressed archive); looks like an initrd
[0.973302] Freeing initrd memory: 5880K
[1.928606] Warning: unable to open an initial console.
[1.928667] RAMDISK: Couldn't find valid RAM disk image starting at 0.
[1.928678] Waiting for root device /dev/sda14...
[1.933927] SAR_RD: Trying to load Ramdisk at offset 44984320      <- our header's ramdisk offset
[1.934047] SAR_RD: Out of memory          (mm/page_alloc.c:4258 in mount_sar_ramdisk->kmalloc)
[1.934049] SAR_RD: Failed to load ramdisk
[1.938296] EXT4-fs (sda25): Root reserved blocks 38400
[1.938468] VFS: Mounted root (ext4 filesystem) readonly on device 259:9
[1.954491] [init] trap before init(1) group exit, exit_code:512
[1.954531] Kernel panic - not syncing: init group exit
```
So the kernel: (a) could not unpack the bootloader-supplied ramdisk, so it treated
it as an old-style initrd; (b) tried Samsung's `mount_sar_ramdisk()` fallback
(`init/do_mounts.c`), which re-reads the ramdisk from the boot partition
(`/dev/android_boot` = sda14) at the header-derived offset and - because our 6.0 MB
ramdisk exceeds kmalloc's max order (4 MB) - hit `WARN_ON` + `SAR_RD: Out of
memory`; (c) mounted the fallback `root=` (`root=PARTUUID=…` -> sda25) read-only;
(d) ran that filesystem's init, which exited, and Samsung's kernel panics on
"init group exit". The panic is therefore a *symptom of the ramdisk handoff*,
not a kernel or Fedora defect.

## Why the ramdisk unpack failed — the evidence
* `init/initramfs.c` (commit f7194c1d) shows the message comes from
  `unpack_to_rootfs()`: either the first bytes carry no recognised compression
  magic / no `'0'` cpio magic, or `state != Reset` after the decompressor, i.e.
  **the archive never reached its `TRAILER!!!`**.
* **Our initramfs is not at fault**: A2's `initramfs.cpio.gz` decompresses to
  8,193,024 B of clean `newc` cpio, 65 records, ends in `TRAILER!!!` + 120 zero
  bytes, contains `/init` and `bin/toybox`. The kernel supports every candidate
  format (`CONFIG_RD_GZIP=y, RD_LZMA=y, RD_LZ4=y, RD_XZ=y, RD_LZO=y, RD_BZIP2=y`,
  recovered from the built `Image` via its embedded `IKCFG_ST` config).
* **S-Boot passes a length that does not match the payload.** S-Boot reports
  `ramdisk size = 0x5be800` = 6,022,144 B while our payload is 6,022,352 B
  (its low byte zeroed / floored to 512). For the working TWRP image it reports
  `0xa66800` = 10,905,600 = 10,905,577 rounded **up** to 2048. Either way S-Boot
  does its own sector arithmetic on the ramdisk length.
* **The live device tree proves where S-Boot puts the initrd**: on the current
  (booting) recovery session
  `linux,initrd-start = 0x89000000`, `linux,initrd-end = 0x89a66800` ->
  S-Boot **ignores the header's `ramdisk_addr` (0x11000000)** and relocates the
  ramdisk to a safe high address; the passed length equals its rounded size.
  Therefore the gzip payload was delivered **truncated** (6,022,144 of 6,022,352
  B): `lib/decompress_inflate.c` tolerates the incomplete stream
  (`Z_BUF_ERROR` is not fatal), the partially unpacked cpio never reaches
  `TRAILER!!!`, and `unpack_to_rootfs()` returns exactly
  "junk in compressed archive".
* The device's own booting image uses **LZMA** (`5d 00 00 80 00 …`), i.e. a
  *different* container shape from ours. A truncated *stream* format is fragile
  in every case, so A3 removes the dependency on the stream entirely.

## Why A3 should boot
A3 keeps the proven kernel and changes only the ramdisk payload to an
**uncompressed `newc` cpio zero-padded to an exact multiple of 2048 bytes**
(8,194,048 B). Consequences:
* `TRAILER!!!` is followed exclusively by 1,144 zero bytes, so it does not
  matter whether S-Boot floors, ceils or passes the size verbatim - nothing but
  padding can be lost (the size is already 512- and 2048-aligned, so its own
  rounding is a no-op).
* No decompressor is involved, so the `initramfs.c` state machine takes the
  `*buf == '0'` raw-cpio path and reaches `state = Reset`.
* The header now matches the only known-booting container on this device:
  `header_version=1` (offset 40), `os_version=0x18000171` (offset 44),
  `header_size=1648` (offset 1644) - S-Boot prints and branches on this value
  (`[UFDT] BOOT IMG HDR V376101` vs `[UFDT] BOOT IMG HDR V1`).

## Refinement after A3 — S-Boot floors the delivered initrd to 4 KiB
A3's S-Boot record finally showed a *correct* header parse
(`[UFDT] BOOT IMG HDR V1`, `ramdisk size = 0x7d0800` = 8,194,048 exactly), yet the
kernel still reported `Freeing initrd memory: 8000K` = 8,192,000 =
`round_down(8,194,048, 4096)`. S-Boot therefore **reports** the header value but
**delivers** `round_down(size, 4096)` bytes. With A2 the same rule gives
`round_down(6,022,352, 4096) = 6,021,120` = exactly the `5880K` printed.

Since a `.cpio` archive's `TRAILER!!!` is its logically last record, any tail loss
breaks `unpack_to_rootfs()` (`state != Reset` -> "junk in compressed archive").
A3's 2,048-byte alignment was therefore insufficient: its trailer ended at
8,192,904 B, i.e. beyond the 8,192,000 B floor.

**A4 remedy:** keep at least one full page of zeros after the trailer and make the
payload a multiple of both 4096 and 65536 (8,323,072 B, trailer followed by
130,172 zeros). Whatever page size S-Boot floors to, only zeros can be discarded.


## Final piece — the boot image's `/chosen` initrd placeholder (A5)
`dtc` on the DTB embedded in every Nuxel boot image so far shows
`/chosen/linux,initrd-start = <0x84000000>` and `linux,initrd-end = <0x841fffff>`
- the packer's own documented **placeholder** ramdisk address, describing a 2 MiB
window. The kernel derives its initrd from those properties, so a stale pair can
make it read the initrd from the wrong physical address while still being told a
correct *length*. A2/A3/A4 all show exactly that combination:
`Freeing initrd memory: 5880K / 8000K / 8128K` (the last one exactly our
8,323,072-byte payload) together with
`rootfs image is not initramfs (junk in compressed archive)`.

A5 removes those properties (and the empty `bootargs`) from `/chosen`; everything
else matches A4, whose length delivery is already proven exact.
