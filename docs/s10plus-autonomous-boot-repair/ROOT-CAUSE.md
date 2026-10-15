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

---

# ROOT CAUSE — cycle 3 addendum (2026-10-15), from source + device-tree forensics

## 1. The delivered initrd *address* and *length* are now known, and they are not the problem
Read live, from the booting recovery session (the only kernel that unpacks a
bootloader-supplied ramdisk on this unit):

```
/proc/device-tree/chosen/linux,initrd-start = 89 00 00 00   -> 0x89000000
/proc/device-tree/chosen/linux,initrd-end   = 89 a6 68 00   -> 0x89a66800
```

* `0x89a66800 - 0x89000000 = 0xa66800 = 10,905,600` = **round_up(TWRP header
  `ramdisk_size` 10,905,577, 2048)**. For A4/A5 the header value was 8,323,072,
  already 2048- and 4096-aligned, and the kernel printed `Freeing initrd memory:
  8128K` = 8,323,072. The length arithmetic is therefore consistent with a single
  rule: S-Boot declares `round_up(header ramdisk_size, 2048)`.
* `0x89000000` is a **fixed** destination: TWRP's header also says
  `ramdisk_addr = 0x11000000`, and S-Boot still placed the payload at
  0x89000000. The header `ramdisk_addr` is ignored on both images, so hypothesis
  A8 ("set ramdisk_addr := 0x89000000") cannot change anything.
* `0x89000000..0x8a000000` is the 16 MiB window immediately below the device tree
  (`dtb_update: ... Updating device tree @0x8a000000`).

## 2. Why "the archive is junk" is a *content* statement, not a *format* statement
`init/initramfs.c` (this tree, commit f7194c1d) in `unpack_to_rootfs()`:

```c
while (!message && len) {
        if (*buf == '0' && !(this_header & 3)) { state = Start;
                written = write_buffer(buf, len); ... continue; }   /* raw newc */
        if (!*buf) { buf++; len--; this_header++; continue; }        /* skip NULs  */
        this_header = 0;
        decompress = decompress_method(buf, len, &compress_name);
        if (decompress) { ... } else if (compress_name) { ... }
        else error("junk in compressed archive");
        if (state != Reset) error("junk in compressed archive");
        ...
}
```

A4/A5 handed the kernel 8,323,072 bytes of **raw `newc` cpio starting with
`070701`**, 66 records, `TRAILER!!!` at 8,192,904, then 130,168 zero bytes. With
those bytes present the parser takes the `*buf == '0'` branch, walks the whole
archive, `do_reset()` skips the trailing NULs, `state == Reset`, and
`unpack_to_rootfs()` returns NULL — i.e. **success**. It returned an error
instead. Therefore the bytes at `0x89000000` were *not* our cpio.

Corollary: this also explains the A3 truncation result without a second cause —
A3 delivered `round_down(8,194,048, 4096) = 8,192,000`, which cuts the archive
before its `TRAILER!!!` record (8,192,780), so `state != Reset` and the message
is exactly right.

Two further timing data points from the retained ram console: one Nuxel boot
failed 0.21 ms after "Trying to unpack" (immediate junk — nothing parsed) while
two others took ~19-21 ms. An immediate failure is only possible if the very
first non-NUL byte at `0x89000000` is neither `'0'` nor a compression magic.
Hypothesis H-INITRD-MEM (below) is written to explain that.

## 3. A second, independent defect: the kernel had no console for the initramfs
`populate_rootfs()` runs as a `rootfs_initcall`; when it succeeds and `/init`
exists in the initramfs, `kernel_init_freeable()` **does not call
`prepare_namespace()`**, so `devtmpfs_mount("dev")` never happens. The initramfs
must therefore supply `/dev/console` itself. Our archive shipped an empty `dev/`
directory, and every Nuxel panic chain contains:

```
[1.928606] Warning: unable to open an initial console.
```

Consequences, both of which invalidated earlier reasoning:
* Even a *successful* initramfs unpack + `/init` would have produced **no console
  text at all** from PID 1, so `grep -c nuxel-init` = 0 in A5 was never evidence
  that `/init` did not run.
* The mission's `INITRAMFS_EXECUTED` / `USERDATA_DISCOVERED` / `ROOTFS_MOUNTED` /
  `ROOTFS_HANDOFF_STARTED` markers would have been invisible.

A6 ships `dev/console` (char 5:1, mode 0600) and `dev/null` (char 1:3, mode 0666)
so the next attempt writes verifiable text into the Samsung ram console.

## 4. What S-Boot actually uses from our image (answers §5 of the mission)
* **Appended DTB: USED.** `[UFDT] BOOT IMG HDR V1.. FINDING DTB ENTRY` ->
  `Little Find DTB Entry[0]: Rev:(S:0, E:255, X:0, D:26)` (revision 26 matches
  this handset) -> `DT Overlay Complete!` with DTBO entry[9] ->
  `Updating device tree @0x8a000000`. The image's DTB is the UFDT *base*, so a
  change to it is a real experiment.
* **`/chosen/linux,initrd-start|end` and `/chosen/bootargs`: OVERWRITTEN.**
  Proven by A5 (removing them changed nothing; the kernel still saw a
  correctly-sized initrd). Changing them is not an experiment.
* **Header load addresses: ignored for the ramdisk.** The ramdisk lands at
  0x89000000 regardless of `ramdisk_addr`.
* **`header_version` at offset 40 is parsed and logged** (`HDR V1` vs
  `HDR V376101`), so the v1 header fix must be preserved.

## 5. Current working hypothesis set (all still to be discriminated on hardware)
* **H-RAMDISK-CONTAINER** — S-Boot's ramdisk load path is format-aware and the
  device's own booting ramdisk is LZMA-alone (props `5d`, dict 8 MiB, size
  unknown => end-of-stream marker). A6 reproduces that shape exactly.
* **H-INITRD-MEM** — S-Boot loads the ramdisk for a *normal* BOOT-partition boot
  through a different code path than a `bootmode=2` recovery boot, and does not
  populate the 0x89000000 window it advertises in `/chosen` (stale or zero
  memory => "junk" in 0.2 ms).
* **H-SAR-RD** — the intended mechanism for a normal Samsung boot is the in-kernel
  `mount_sar_ramdisk()` fallback (`init/do_mounts.c`, gated on
  `android_bootmode != 2`), which re-reads the ramdisk from the BOOT partition and
  currently dies at `SAR_RD: Out of memory` because 8 MB exceeds kmalloc's max
  order. This path is a plausible *intended* route that our image never satisfies.
* **H-SYSTEMD-4.14** — Fedora 43 ships systemd 258.11, which requires Linux >= 5.4
  and cgroup v2; the Samsung 4.14.253 tree predates that. Independent blocker for
  milestone 8, to be assessed only after `/init` runs.

---

# ROOT CAUSE — cycle 3, FINAL (2026-10-15): measured, not inferred

An instrumented kernel (candidate A7, `kernel/s10plus/patches/0003-…`) printed
the whole initramfs handoff at `KERN_ALERT`. The blocker is now *measured*:

```
NUXEL-KDIAG populate_rootfs: builtin=…  builtin_size=550327 external_initrd=1 start=ffffffc009000000 end=ffffffc009080000 len=524288
NUXEL-KDIAG initrd head: 5b 20 20 20 20 31 2e 30 34 35 36 36 35 5d 20 5b     ascii: "[    1.0"
NUXEL-KDIAG unpack attempt: first=0x1f this_header=0 remaining=550327 method=gzip   <- BUILT-IN
NUXEL-KDIAG unpack verdict: message=(none) state=7                                  <- SUCCESS
Trying to unpack rootfs image as initramfs...
NUXEL-KDIAG unpack attempt: first=0x5b this_header=0 remaining=524288 method=(none) <- EXTERNAL
NUXEL-KDIAG unpack verdict: message=junk in compressed archive state=0
… built-in restored (state=7) …
rootfs image is not initramfs (junk in compressed archive); looks like an initrd
Freeing initrd memory: 512K
Warning: unable to open an initial console.
```

## Cause 1 (was the blocker) — the bootloader advertises an initrd it never loads
For a **normal BOOT-partition boot** S-Boot writes `/chosen/linux,initrd-start =
0x89000000` and `initrd-end = start + round_up(header ramdisk_size, 2048)` — the
length tracks our header exactly, and A7's dump shows `len=524288`, our ramdisk to
the byte — but the memory at that address is **not our ramdisk**. It held kernel
console text (`"[    1.0"`) on one boot and zeros on another, and
`decompress_method()` found nothing there (`method=(none)`, `first=0x5b`).

Consequences: every container-format experiment (gzip, uncompressed `newc`, extra
page padding, LZMA-alone, page-aligned LZMA) was doomed — the bytes were never
going to be there. This also explains A6's 0.21 ms rejection and the fact that
`Freeing initrd memory: <N>K` always tracked our size: the *length* comes from our
header, the *content* does not follow it.

Why the recovery path differs: on a `bootmode=2` recovery boot the same S-Boot
delivers the ramdisk to that same address correctly (TWRP's 10,905,577-byte
LZMA-alone stream is there and unpacks into a 48,020,736-byte `070701` cpio). The
normal-boot ramdisk path is therefore the defect, and it is in the bootloader, not
in our image — we cannot fix it by changing the container.

**This is why A7 embeds the initramfs in the kernel**: it removes the defective
handoff from the critical path, and it works.

## Cause 2 (was hiding everything) — this device has no usable `/dev/console`
Measured from the running recovery: `/dev/console` exists as a char device 5:1 but
`open()` returns **ENODEV** ("`can't create /dev/console: No such device`"), while
`/dev/kmsg` (1:11) accepts writes. With `console=ram`, Samsung registers a
`struct console` that provides no tty, so `kernel_init_freeable()` cannot open an
initial console and PID 1 gets invalid stdio. Therefore:
* `printf … > /dev/console` from `/init` can never produce output on this handset;
* the kernel's `Warning: unable to open an initial console.` is **not** evidence
  about the initramfs at all;
* every cycle-1/2 conclusion of the form "no `nuxel-init:` output ⇒ `/init` did not
  run" was unsupported. `/init` was never observable.
**Fix:** route evidence to `/dev/kmsg` (permitted by S-Boot's
`printk.devkmsg=on`) and ship `/dev/kmsg` in the initramfs — implemented in A8.

## Cause 3 (now the gating problem) — the boot is killed by a timeout, not a crash
With A7 the kernel ran to t=37 s, 68 s and 242 s (vs ~2 s for A2-A5) and then died
of Samsung's own mechanisms:
* `hard_reset_hook_callback+0x144/0x150` from `hrtimer_interrupt` →
  `Kernel panic - not syncing: Fatal exception in interrupt` (37 s, 68 s);
* `Kernel panic - not syncing: hung_task: blocked tasks` (242 s) with
  `tz_worker_threa` (EXYNOS thermal), `scsi_srpmb_work` and `ree_time` blocked —
  kernel threads waiting on hardware/secure-world handshakes that a non-Android
  userspace never satisfies.
This is a *watchdog-style* limit on a boot that does not signal success, not a
defect in our kernel path. A8 therefore carries an explicit
`NUXEL_BOOT_WATCHDOG=45` so the attempt persists its evidence and reboots on our
terms instead of racing the vendor reset.

## Cause 4 (relevant to milestone 8) — Fedora systemd vs Linux 4.14
Unchanged and still open: the rootfs ships systemd 258.11, which requires
Linux >= 5.4 and cgroup v2; this tree is 4.14.253 and predates eBPF/cgroup-v2
features systemd now assumes. Not addressable until `/init` is observable.
