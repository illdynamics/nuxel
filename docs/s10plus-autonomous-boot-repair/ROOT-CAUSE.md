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

---

# ROOT CAUSE — cycle 4 (2026-10-15): the systemd "Failed to spawn executor: ENOSYS"

**Status: identified in the exact sources of the *installed* versions, consistent
with every line of the A12 hardware log. Hardware confirmation of the individual
syscalls is prepared (A13 probe).**

## The observed failure (A12, hardware)
```
[14.343739] systemd[1]: dev-mqueue.mount: Failed to spawn executor: Function not implemented
[14.350702] systemd[1]: systemd-journald.service: Failed to spawn executor: Function not implemented
[14.372524] systemd[1]: nuxel-firstlight.service: Failed to spawn executor: Function not implemented
<14.376912> systemd[1]: Too many messages being logged to kmsg, ignoring
```
Every unit spawn fails, with the same errno; PID 1 itself, its generators and
its own in-memory target graph are all fine (`Reached target sysinit.target/basic.target`,
`Queued start job for multi-user.target`). So the incompatibility is **not** in
PID 1's startup, the unit files, the cgroup tree or the rootfs: it is inside
systemd's single process-spawning function.

## The exact call chain (source-level, version-exact)
Fedora 43 rootfs: `systemd 258.11-1.fc43`, `glibc 2.42` (`/usr/lib64/libc.so.6`).

1. `src/core/execute.c:exec_spawn()` → `posix_spawn_wrapper()` (execute.c:580).
2. `src/basic/process-util.c:posix_spawn_wrapper()` compiles **the `HAVE_PIDFD_SPAWN`
   branch** because glibc ≥ 2.39 declares `pidfd_spawn()` (meson.build:590).
   The branch calls **`pidfd_spawn()`** and never calls plain `posix_spawn()`.
3. glibc 2.42 `sysdeps/unix/sysv/linux/spawni.c:__spawni()`:
   ```c
   bool use_pidfd = xflags & SPAWN_XFLAGS_RET_PIDFD;
   /* ...without proper waitid support, pidfd_spawn can not be used... */
   if (use_pidfd && !__clone_pidfd_supported ())
     return ENOSYS;
   ```
4. `__clone_pidfd_supported()` (`sysdeps/unix/sysv/linux/clone-pidfd-support.c`)
   probes **`waitid(P_PIDFD, ...)`** and treats anything but `EBADF` as
   "unsupported". **`P_PIDFD` was added in Linux 5.4.** This kernel is
   **4.14.253**, so the probe sees `EINVAL` ⇒ unsupported ⇒ **`pidfd_spawn()`
   returns `ENOSYS` unconditionally**, before it ever reaches clone3.
5. back in systemd: `ERRNO_IS_NOT_SUPPORTED(ENOSYS)` is true, and because
   `cgtarget != NULL` the `POSIX_SPAWN_SETCGROUP` clause fires. It clears the
   flag and **retries `pidfd_spawn()`** — which is *still* `pidfd_spawn()`
   (glibc's `use_pidfd` is a property of the function, not of the attribute) and
   therefore returns `ENOSYS` again.
6. `if (r != 0) return -r;` ⇒ `execute.c` logs
   `"Failed to spawn executor: %m"` ⇒ **`Failed to spawn executor: Function not
   implemented`**, exactly as captured.

**The comment in that fallback is wrong for this case**: it says the retry
"disables POSIX_SPAWN_SETCGROUP, which is what redirects to clone3()". True for
`posix_spawn()`, but with `HAVE_PIDFD_SPAWN` the retry is still `pidfd_spawn()`,
which needs pidfd support *regardless of any attribute*. There is therefore no
path in 258.11 from `HAVE_PIDFD_SPAWN` back to the plain `posix_spawn()`
implementation — that is the defect.

## Why it is *not* clone3 (verified against the same sources)
Plain `posix_spawn()` works on this kernel: `spawni.c` calls `__clone3()`, and on
`ENOSYS|EINVAL` it falls back to `__clone_internal_fallback()` → `clone()`
(`clone3.c`), clearing clone3-only flags; with `POSIX_SPAWN_SETCGROUP` *not* set
it does not take the "no fallback for POSIX_SPAWN_SETCGROUP" path. So the only
missing kernel feature is `waitid(P_PIDFD)` (Linux 5.4), i.e. **pidfd support** —
*not* `clone3` (5.3) and *not* `CLONE_INTO_CGROUP` (5.7).

Corroboration from the same boot (A12): the parts of systemd that do **not** use
`posix_spawn_wrapper` work on hardware — `systemd-gpt-auto-generator` really
executed (PID 3450, `exynos-ufs ... ufshcd_ioctl` from that process), and systemd
serialized its state (the `memfd`-backed serialization stream succeeded, since
the failure is *after* `finish_serialization_file()`).

## Upstream has already fixed this
systemd `main` `posix_spawn_wrapper()` ends with the same three-step logic, with
the comment *"pidfd_spawn unavailable (libc or kernel missing) — fall back to
plain posix_spawn."* Cycle 4 backports exactly that behaviour to 258.11 (see
PATCHES.md, `nuxel-0001-pidfd-spawn-fallback.patch`).

## What this does **not** claim
* It does not claim the whole Fedora 43 userspace is 4.14-compatible; it claims
  one *specific, source-proven* defect and its minimal repair. The next blocker
  (if any) can only be found by running the repaired stack (milestone: "a core
  systemd service actually runs").
* It does not depend on `CONFIG_DRM` (absent in this kernel: `# CONFIG_DRM is
  not set`) — first light is an **fbdev** path (`/dev/fb0`), not DRM/KMS.


---

# ROOT CAUSE — cycle 4 FINAL: the ENOSYS is `pidfd_spawn()` → `waitid(P_PIDFD)`

**Status: source-exact and independently reproducible. Hardware measurement is
prepared in A13 (the probes are in the image).** Nothing here depends on Nuxel
code; both sides are the *installed* versions.

## The measurement A12 left behind
```
[14.343739] systemd[1]: dev-mqueue.mount: Failed to spawn executor: Function not implemented
[14.350702] systemd[1]: systemd-journald.service: Failed to spawn executor: Function not implemented
[14.372524] systemd[1]: nuxel-firstlight.service: Failed to spawn executor: Function not implemented
```
Every unit, every task type, one errno. PID 1 itself, its generators, its unit
graph and its cgroup tree are all healthy. So the defect is inside the single
process-spawning function.

## The chain, with the exact source lines

1. **systemd 258.11** — `src/core/execute.c:exec_spawn()` →
   `src/basic/process-util.c:posix_spawn_wrapper()` (exported as
   `posix_spawn_wrapper@@SD_SHARED` from `libsystemd-shared-258.11-1.fc43.so`;
   `libsystemd-core-258.11-1.fc43.so` merely imports it
   (`U posix_spawn_wrapper@SD_SHARED`), which is why one file is enough to fix).
2. The `HAVE_PIDFD_SPAWN` branch is compiled because glibc ≥ 2.39 declares
   `pidfd_spawn()`. It calls **`pidfd_spawn()`**, and on failure it clears
   `POSIX_SPAWN_SETCGROUP` and calls **`pidfd_spawn()` again** — not
   `posix_spawn()`. There is no path back to the working implementation.
3. **glibc 2.42** — `sysdeps/unix/sysv/linux/spawni.c:__spawnix()`:
   ```c
   bool use_pidfd = xflags & SPAWN_XFLAGS_RET_PIDFD;
   /* ... ENOSYS is returned because without proper waitid support, pidfd_spawn
      can not be used proporly independently of its arguments. */
   if (use_pidfd && !__clone_pidfd_supported ())
     return ENOSYS;
   ```
4. `sysdeps/unix/sysv/linux/clone-pidfd-support.c:__clone_pidfd_supported()`
   probes **`waitid(P_PIDFD, INT_MAX, NULL, WEXITED|WNOHANG)`** and returns
   "supported" **only** if the result is `EBADF`:
   ```c
   int r = INTERNAL_SYSCALL_CALL (waitid, P_PIDFD, INT_MAX, NULL, WEXITED | WNOHANG);
   state = r == -EBADF ? 1 : -1;
   ```
   `P_PIDFD` was added in **Linux 5.4**. This kernel is **4.14.253**, so the
   syscall returns `EINVAL`, `state = -1`, and `pidfd_spawn()` returns `ENOSYS`
   **before it ever reaches `clone3()`**.

## Why it is *not* `clone3`, `CLONE_INTO_CGROUP` or cgroup v2
Plain `posix_spawn()` works on this kernel: `spawni.c` calls `__clone3()` and, on
`ENOSYS|EINVAL`, takes `__clone_internal_fallback()` → `clone()`
(`clone3.c` clears the clone3-only flags). It only refuses when
`POSIX_SPAWN_SETCGROUP` is set, which the fallback also clears. The *only* missing
kernel feature on the failing path is `waitid(P_PIDFD)`.

Corroboration from the same boot: `systemd-gpt-auto-generator` really executed
(PID 3450), and systemd's memfd-backed serialization stream succeeded.

## The minimal repair (implemented, not hypothetical)
Upstream systemd's own later change — *"pidfd_spawn unavailable (libc or kernel
missing) — fall back to plain posix_spawn."* — is backported onto
`258.11-1.fc43`. The edit is a single, exact-anchor textual replacement in
`src/basic/process-util.c` (`nuxel-pidfd-edit.py`), so no patch fuzz is involved.

Disassembly of the rebuilt library proves the change is present: in the original,
`posix_spawn_wrapper` had exactly one spawn call site (`pidfd_spawn@plt`); in the
rebuilt one it has two:
```
24e008:  bl  77290 <pidfd_spawn@plt>
24e07c:  bl  7a920 <posix_spawn@plt>     <- the fallback
```
`sha256 502507a7b6237a03cfcff49e389d2a38836916abdea40e36e5ba4653e9bc1234`
(vs the installed original `3d0da20f68bdcdeac3ef900cfeaa990f4df3df3d7ab29d9591ce00649eb888a5`).

## Why a glibc-side workaround is not viable
Making `__clone_pidfd_supported()` return true would not help: `__spawnix()`
then passes `CLONE_PIDFD` and `.parent_tid = &args.pidfd`, and since `clone3()`
is `ENOSYS` on 4.14 the `clone()` fallback cannot produce a pidfd at all, so
`pidfd_spawn()` could not satisfy its own contract. `pidfd_open()` (Linux 5.3) is
also absent, so no shim can synthesise one. **The fallback belongs in systemd.**

## What this does not claim
It does not claim the whole Fedora 43 userspace is 4.14-compatible — only that
this specific, source-proven defect is fixed. Whatever the *next* blocker is can
only be found by running the repaired stack, which is what A13 does.

---

# CYCLE 6 — ROOT-CAUSE LEDGER (A15 evidence)

## RC-6.1 — The A15 "spontaneous reboot" is the operator's Samsung hard-reset hook. CLOSED.

```
[1891.962448] kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!
[1891.962635] Internal error: Oops - BUG: 0 [#1] PREEMPT SMP
[1891.971066] CPU: 0 PID: 0 Comm: swapper/0 Tainted: G S  4.14.253 #1
[1891.971169] pc : hard_reset_hook_callback+0x144/0x150
             hard_reset_hook_callback -> el1_dbg -> do_debug_exception -> brk_handler
             -> call_break_hook -> bug_handler -> die -> panic
             (invoked from __hrtimer_run_queues / exynos4_mct_tick_isr, i.e. a timer)
```

`drivers/samsung/sec_hard_reset_hook.c` deliberately executes a BRK when the PMIC
power key is held together with the volume key, which panics and resets the AP.
Everything else in the 1892 s log is healthy: HW watchdog keepalives every 10 s,
systemd alive, `debug-snapshot: normal reboot starting` ABSENT, `Restarting system`
ABSENT. The mission's "prolonged black screen, then reboot after 1–2 min or
longer" is therefore: black screen from t≈2.1 s + operator forcing recovery.
**Do not attribute this to the boot; do not treat it as a watchdog failure.**

## RC-6.2 — The panel never lights during a Nuxel boot. OPEN (instrumented in A16).

Panel/DSIM/DECON probe correctly, framebuffer registers, and the S-Boot-drawn
samsung logo is on the panel at handoff. Then the Nuxel boot never performs
`decon_enable` / UNBLANK / FRAME_DONE, unlike the TWRP session which does. Three
candidate mechanisms, all now instrumented:
(a) DECON in command mode needs an explicit fbdev commit (`FBIOPAN_DISPLAY` /
`FBIOPUT_VSCREENINFO`) that A14/A15 never issued;
(b) the paint went to the wrong buffer of the 1440×6080 virtual framebuffer;
(c) the paint never happened and the program's output was lost by the shell.
Mechanism (c) is proven to have corrupted the *evidence* even if the paint was fine:
`init.sh` used `printf … | while IFS= read -r`, and this toybox shell cannot run
`read` (`sh: <...>read: No such file or directory` appears in the A15 log exactly
where the verdict lines should be).

## RC-6.3 — systemd 258 cannot spawn any service on Linux 4.14. OPEN.

`pidfd_spawn()` in glibc ≥ 2.39 requires `waitid(P_PIDFD)` (Linux ≥ 5.4) and
returns ENOSYS unconditionally below that, which is what
`NUXEL-SPAWN-PROBE pidfd_spawn(...) rc=38 ENOSYS` measures. `exec_spawn()` in
systemd's `src/core/execute.c:599` reports it as
`Failed to spawn executor: %m`. The A13 backport of upstream's own
`posix_spawn` fallback (`.scratch/s10plus-cycle4/nuxel-0001-pidfd-spawn-fallback.patch`)
is deployed to the handset's rootfs (tag `.nuxel-patches/pidfd-spawn-fallback-A13`
present → `SYSTEMD_PATCH_PRESENT`), **yet the failure is unchanged in A15**.
Newly observed inconsistency to resolve: the *local* rootfs image
`build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img` contains
**neither** that tag **nor** a `.nuxel-orig` backup, and its
`usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so` is neither the pristine
nor the patched build (`3d0da20f…` vs patched `502507a7…`). So either the
handset's USERDATA has diverged from the local image, or the patch is present but
does not cover the failing path. Both can be settled by (i) a read-only USERDATA
readback and (ii) dumping the on-device library and diffing it against
`502507a7…`.

## RC-6.4 — WHY the A13 systemd patch never worked: it patches the wrong library. FOUND.

Offline inspection of the Fedora 43 rootfs (read-only, via `tools/s10plus/ext4lite.py`):

| file in `nuxel-beyond2lte-rootfs-fedora-phone-fixed.img` | bytes | contains `posix_spawn_wrapper` | contains `exec_spawn` | contains `pidfd_spawn` |
|---|---|---|---|---|
| `usr/lib64/systemd/libsystemd-core-258.11-1.fc43.so` | 2,585,568 | **yes** | **yes** | no |
| `usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so` | 5,071,376 | yes | no | yes |
| `usr/lib/systemd/systemd` | 201,024 | no | no | no |
| `usr/lib/systemd/systemd-executor` | 1,400,024 | no | no | no |

Fedora's `libsystemd-core.so` is linked against the **static** shared library, so it
carries its **own compiled copy** of `posix_spawn_wrapper()` next to `exec_spawn()`.
PID 1 calls `exec_spawn()` → `posix_spawn_wrapper()` **inside libsystemd-core**, not
through `libsystemd-shared.so`.

The A13/A14/A15 repair installs only
`usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so`
(`boot/initramfs/init.sh`, `NUXEL_SD_LIB`). `libsystemd-core-*.so` is therefore
**never replaced**, so the unpatched double-`pidfd_spawn()` retry is what actually
runs — which is exactly the measured behaviour:

```
NUXEL-SPAWN-PROBE pidfd_spawn(...) rc=38 ENOSYS
systemd[1]: <unit>: Failed to spawn executor: Function not implemented   (28 units)
```

and it explains why `SYSTEMD_PATCH_PRESENT` is logged while nothing changes.

Supporting source facts (all checked in `.scratch/s10plus-cycle4/src/systemd-258.11`):

* `src/core/execute.c:581` calls `posix_spawn_wrapper(...)` for the pinned
  `systemd-executor`; `:599` is the `Failed to spawn executor: %m` line.
* `src/basic/process-util.c` (unpatched) retries **`pidfd_spawn()` again** after
  clearing `POSIX_SPAWN_SETCGROUP` — it never falls back to `posix_spawn()`.
  glibc's `pidfd_spawn()` returns ENOSYS for any flags when the kernel lacks
  `waitid(P_PIDFD)`, so the retry is guaranteed to fail on Linux 4.14.
* `ERRNO_IS_NOT_SUPPORTED()` is **not** the problem: `_DEFINE_ABS_WRAPPER` expands to
  `ERRNO_IS_NEG_##name(-ABS(r))` and `ERRNO_IS_NEG_NOT_SUPPORTED()` includes
  `-ENOSYS`, so a positive 38 is correctly classified. (H-C6-H is REFUTED.)

### Fix for the next cycle (do not flash the rootfs yet)

1. Rebuild the patched systemd **and keep all four artifacts**, specifically
   `libsystemd-core-258.11-1.fc43.so` — that is the file that matters.
2. Ship it in the initramfs as `opt/nuxel/libsystemd-core-258.11-1.fc43.so` and
   extend the Phase-2 installer to replace **both** libraries under one tag
   (`pidfd-spawn-fallback-A16`), keeping a `.nuxel-orig` backup of each and
   verifying each replacement by SHA256 before `switch_root`.
3. Because the tag `pidfd-spawn-fallback-A13` already exists on the handset, the
   new tag must be **different** — the old one will otherwise short-circuit the
   install exactly as it did in A15.
4. Alternative, lower-risk variant worth considering: build with
   `HAVE_PIDFD_SPAWN` forced to 0, which removes the whole pidfd path at compile
   time and therefore cannot regress; either way `libsystemd-core` must be replaced.
5. Either approach still touches USERDATA, so it is a separate, explicitly versioned
   rootfs change with a clean ext4 verification — not part of the BOOT-only A16 test.
