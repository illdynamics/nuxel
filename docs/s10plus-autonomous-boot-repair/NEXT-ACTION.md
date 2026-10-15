# NEXT-ACTION (after A5)

## The single remaining blocker (precisely stated)
S-Boot now hands the kernel an initrd of **exactly the right length** (8,323,072 B,
`Freeing initrd memory: 8128K`) whose payload is a **valid, kernel-supported raw
`newc` cpio** (verified offline: 65 records, `TRAILER!!!`, `/init`, `bin/toybox`),
and the kernel still reports
`rootfs image is not initramfs (junk in compressed archive)`.
Per `init/initramfs.c` that message means the bytes at `initrd_start` carried
neither the cpio `'0'` magic nor a compression magic. Since length delivery is now
provably correct, the mismatch is in **what occupies that memory**, not in our file.

## Next candidates, in priority order

### A6 — ramdisk in the device's own proven payload format (LZMA-alone)
The only ramdisk known to be both delivered *and* unpacked on this handset is
TWRP's: `ramdisk.lzma`, LZMA-alone, props `5d 00 00 80 00`, dict 8 MiB, size
`0xffffffffffffffff`, 10,905,577 B, decompressing to a 48,020,736-byte `newc` cpio.
Samsung S-Boot has a format-aware ramdisk path, so a compressed payload is the
shape it demonstrably handles. Build: compress the proven cpio to LZMA-alone with
the same props/dict; **pad inside the compressed stream** (compress a cpio whose
input carries the trailing zeros) rather than appending zeros after the stream -
offline testing showed Python's LZMA decoder rejects a padded LZMA-alone stream,
and TWRP's payload likewise carries no post-stream padding.

### A7 — embed the initramfs in the kernel (`CONFIG_INITRAMFS_SOURCE`)
Removes S-Boot's ramdisk handoff from the dependency chain completely:
`populate_rootfs()` unpacks the built-in initramfs first, and because `/init` then
exists in rootfs, `kernel_init()` skips `prepare_namespace()` - which also bypasses
the `SAR_RD` / `root=PARTUUID=…` fallback that produces the "init group exit"
panic. Feasibility: the exact running config is recoverable (extracted from the
built `Image` via its `IKCFG_ST` block -> `/tmp/nuxel-kernel.config`, 172,839 B);
Homebrew provides `aarch64-linux-gnu-gcc`. Blockers: `kernel/s10plus/.build/src`
is a corrupt clone (`HEAD -> refs/heads/.invalid`, empty worktree) and a Linux-
hosted build is preferable - docker daemon is **down**, `podman` is present but no
machine is configured.

### A8 — header `ramdisk_addr` := 0x89000000
Cheap single-field test of the "kernel reads the initrd from the wrong physical
address" hypothesis, using the address S-Boot is observed to use on its working
(booting recovery) session. Lowest effort, lowest information, last resort.

## Instrumentation to add before further attempts
* The BOOT-slack record (offset 57,606,144) is the only channel that survives a
  boot with no display and no USB - extend `/init` to write a marker *before* the
  first storage access, so a future boot proves `populate_rootfs` succeeded even
  if UFS or the mount fails.
* Nothing in S-Boot's log exposes the ramdisk destination address; do not spend
  more cycles mining it.

## Standing risks
* No real backup of the stock BOOT partition exists (`boot-original.img` is a
  `DUMMY` placeholder). RECOVERY is untouched and backed up, so the recovery path
  is intact - keep it that way (all writes so far were BOOT-only).
* USERDATA (the Fedora rootfs) has never been rewritten in this cycle and has
  never been mounted read-write by the device; the tree is intact.
