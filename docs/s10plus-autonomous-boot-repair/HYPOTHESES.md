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

---

# HYPOTHESES (cycle 3, after source + DT forensics)

## H-HEADER-LEGACY — the packer's offset-40 defect (CONFIRMED, now gated)
`pack-boot-v1.sh` wrote the DTB size at header offset 40, where `boot_img_hdr_v1`
requires `header_version == 1`. S-Boot logs the field
(`[UFDT] BOOT IMG HDR V376101` vs `HDR V1`). Fixed in cycle 2 (`--v1-spec`) and now
**enforced** by `tools/s10plus/verify-boot-image.py` + `--strict`.
Candidates A2 and the legacy diagnostic image fail the gate on exactly this.

## H-KERNEL-GZIP — gzip kernel payload (CONFIRMED, now gated)
S-Boot jumps to `kernel_addr` without decompressing. A gzip payload is executed as
code (A1: seven silent loads, zero console bytes). The gate rejects `1f 8b`
kernels, so A1 and `nuxel-beyond2lte-boot-merged-fixed.img` fail.

## H-INITRD-MEM — for a normal BOOT boot the 0x89000000 window is not populated (STRONG, under test)
* For the **recovery** boot the window is populated: the booting kernel's own DT
  says `linux,initrd-start = 0x89000000`, `end = 0x89a66800`, and that LZMA stream
  decompresses to a complete 48,020,736-byte `070701` cpio with `TRAILER!!!`.
* For our **normal** boots the kernel is told the same fixed base and a length
  that exactly matches our header (`Freeing initrd memory: 8128K` for an
  8,323,072-byte payload) yet reads bytes that are not a cpio at all — and in one
  boot the parser failed 0.21 ms after starting, which is only possible if the
  first non-NUL byte is neither `'0'` nor a compression magic.
* Prediction: with an LZMA ramdisk (A6) the failure *mode* changes if the payload
  is delivered (`decompressor failed` or success) and stays
  `junk in compressed archive` if it is not.
* `bootmode=` is absent on a normal boot and `bootmode=2` on recovery, so S-Boot
  / the kernel really do take different ramdisk paths.

## H-RAMDISK-CONTAINER — S-Boot's ramdisk path is format-aware (UNDER TEST, = A6)
The only ramdisk proven to be both delivered and unpacked on this handset is
TWRP's LZMA-alone stream. A6 rebuilds the Nuxel initramfs in exactly that shape
(props `5d`, dict 8 MiB, size `0xffffffffffffffff`) and additionally aligns the
container to 65,536 bytes so no S-Boot rounding rule (up, down or exact) can clip
the end-of-stream marker. Container bytes after the EOS marker are zeros, which is
exactly what the working TWRP ramdisk already carries (+23 bytes).

## H-NO-DEV-CONSOLE — no initramfs console (CONFIRMED, fixed in A6)
`prepare_namespace()` is skipped for a built-in initramfs, so devtmpfs is never
mounted by the kernel and `/dev/console` must come from the archive. Ours was
missing, hence `Warning: unable to open an initial console.` This made ALL
previous "no initramfs output" observations uninformative. A6 adds
`dev/console` (5:1) and `dev/null` (1:3).

## H-SAR-RD-OOM — Samsung's in-kernel fallback cannot carry our ramdisk
`init/do_mounts.c`: when `android_bootmode != 2` the kernel calls
`mount_sar_ramdisk("/dev/android_boot")`, kmalloc'ing the ramdisk out of the BOOT
partition. 8.3 MB exceeds kmalloc's max order, giving `WARN` at
`mm/page_alloc.c:4258` + `SAR_RD: Out of memory`, then the `root=PARTUUID=...`
fallback mounts SYSTEM (sda25) and its `init` exits -> `init group exit`.
Not a target to fix, but it identifies a *third* route to userspace that does not
depend on `/chosen` at all.

## H-INIT-GROUP-EXIT — Samsung panics when PID 1 exits (SYMPTOM)
Fires only downstream of the ramdisk failure (the fallback root's init exits).

## H-SYSTEMD-4.14 — Fedora 43 userspace vs Linux 4.14 (OPEN, milestone 8)
Not diagnosable until `/init` runs. Plan: prove USERDATA mounts, prove a small
Fedora binary executes, then establish a supported init strategy (systemd requires
>= 5.4 + cgroup v2) rather than assuming the systemd ELF existing implies it runs.

## Closed / retired by evidence
* **H-RAMDISK-ADDRESS (was A8):** retired. S-Boot ignores the header
  `ramdisk_addr` and uses the fixed 0x89000000 base for TWRP *and* for us.
* **H-CHOSEN-PLACEHOLDER (was A5):** retired. S-Boot overwrites
  `/chosen/linux,initrd-*`; removing the placeholders changed nothing. Keeping
  them out remains correct hygiene (a change there must never be counted as an
  effective device-tree experiment).
* **H-PADDING-ONLY:** retired by the argument in ROOT-CAUSE.md §2 — with the raw
  cpio present in memory, no padding scheme could have failed.

---

# HYPOTHESES — cycle 3 FINAL (after A7's instrumentation)

## H-INITRD-MEM — CONFIRMED BY DIRECT MEASUREMENT
The instrumented kernel printed the address, the length and the first 16 bytes of
the initrd S-Boot declares:
```
external_initrd=1 start=ffffffc009000000 end=ffffffc009080000 len=524288
initrd head: 5b 20 20 20 20 31 2e 30 34 35 36 36 35 5d 20 5b   ascii "[    1.0"
unpack attempt: first=0x5b this_header=0 remaining=524288 method=(none)
```
`0xffffffc009000000` is the linear alias of `0x89000000`; `len` is exactly our
header's ramdisk size rounded to 2048; and the bytes there are the kernel's own
console text (zeros on another boot). **S-Boot publishes the initrd entry in
`/chosen` without loading the payload on the normal BOOT-partition path.** The
`bootmode=2` recovery path does load it, which is why TWRP's LZMA ramdisk unpacks.
Not fixable from the container; A7 removes the dependency by embedding the
initramfs in the kernel.

## H-RAMDISK-CONTAINER — REFUTED (hardware, A6)
A6 shipped our initramfs as LZMA-alone with the exact properties, dictionary and
unknown-size EOS-marker layout of the TWRP ramdisk, page-aligned to 65536 bytes.
S-Boot consumed the new size (`ramdisk size = 0x5c0000`, `Freeing initrd memory:
5888K`) and the kernel still rejected the payload **0.21 ms** after starting — an
immediate, first-byte rejection that an LZMA stream at that address could not
produce. Container format was never the problem. **No further format experiments.**

## H-NO-CONSOLE — CONFIRMED, and larger than first thought
`/dev/console` (char 5:1) exists but `open()` returns **ENODEV** on this handset
(measured live): `console=ram` registers a `struct console` with no tty. So
`kernel_init` cannot open an initial console, PID 1 has invalid stdio, and **no
initramfs output could ever be captured** — regardless of `/init` running.
Fix: `/dev/kmsg` (1:11) works (S-Boot sets `printk.devkmsg=on`); A8 ships
`dev/kmsg` in the archive and routes every diagnostic through it first.

## H-VENDOR-BOOT-TIMEOUT — NEW, CONFIRMED
A7's boots ended at t=37 s / 68 s (`hard_reset_hook_callback` ->
`Fatal exception in interrupt`) and t=242 s (`hung_task: blocked tasks`, with
EXYNOS thermal `tz_worker_threa`, `scsi_srpmb_work`, `ree_time` blocked). These are
the vendor kernel's "boot never signalled success" mechanisms, not our path.
Consequence: candidates must finish and persist evidence within ~40 s -> A8's
`NUXEL_BOOT_WATCHDOG=45` and the early BOOT-slack heartbeat.

## H-KERNEL-EMBEDDED-INITRAMFS — CONFIRMED (hardware, A7)
`CONFIG_INITRAMFS_SOURCE` works on this device: `unpack verdict: message=(none)
state=7` (success) for the built-in archive, and `/init` is then executed because
`kernel_init_freeable()` finds it and skips `prepare_namespace()` (no `RAMDISK:`,
no `SAR_RD`, no `init group exit`). Also verified offline: the generated
`usr/initramfs_data.cpio.gz` (551,027 B) is embedded **byte-for-byte** in the
`Image` at file offset `0x203E510`, and the archive contains
`dev/console`, `dev/kmsg`, `dev/null`, `bin/sh -> toybox` and `/init` byte-identical
to `boot/initramfs/init.sh`.

## H-SAR-RD-OOM — now moot for the critical path
Unchanged in mechanism (Samsung's `mount_sar_ramdisk()` kmallocs the ramdisk out of
the BOOT partition and 8 MB exceeds kmalloc's max order). With A7/A8 the ramdisk is
512 KB, so even that fallback would now fit — but `prepare_namespace()` is not
reached at all once `/init` exists.

## H-SYSTEMD-4.14 — OPEN (milestone 8)
Fedora 43 ships systemd 258.11 (requires Linux >= 5.4, cgroup v2, no cgroup v1
support); the kernel is 4.14.253. To be attacked only after USERDATA mounts and a
small Fedora process can be shown to execute.

## Retired by evidence (do not retry)
* **H-RAMDISK-CONTAINER** — refuted by A6.
* **H-RAMDISK-ADDRESS / A8-old ("set header ramdisk_addr := 0x89000000")** — S-Boot
  ignores the header address and uses the fixed 0x89000000 for both images.
* **H-CHOSEN-PLACEHOLDER** — S-Boot overwrites `/chosen/linux,initrd-*`.
* **H-PADDING-ONLY** — immaterial: the raw `newc` cpio cannot fail with "junk in
  compressed archive" if it is present in memory at all.
