# A7 — kernel-embedded initramfs: build record

## Why A7 (from the A6 result)
A6 (LZMA-alone ramdisk in the device's own proven container shape) failed with
`junk in compressed archive` **0.21 ms** after "Trying to unpack", while S-Boot
reported `ramdisk size = 0x5c0000` = A6's ramdisk size exactly. An LZMA stream at
the address the kernel reads cannot produce that message; it would produce
`decompressor failed` or success. So the payload is not at the advertised address
on the normal BOOT-partition path. Embedding the initramfs removes the
bootloader's ramdisk handoff from the critical path.

## Source
* `https://github.com/Linux4/android_kernel_samsung_exynos9820`
  at `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253, Samsung downstream)
* Fetched as a codeload tarball: `.scratch/src/kernel.tar.gz`
  (209,024,302 B -> 1,034,117,120 B). The in-repo `kernel/s10plus/.build/src` is an
  empty partial clone (`HEAD -> refs/heads/.invalid`) and was not used.
* Verified: `init/initramfs.c` (14,702 B), `init/do_mounts.c` (15,781 B),
  `init/main.c` (36,255 B) are byte-identical to the files used for the cycle-3
  source analysis, and `arch/arm64/configs/exynos9820-beyond2lte_defconfig`
  (172,786 B) plus `arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_26.dts`
  are present — **revision 26, the exact board revision this handset reports**
  (`[UFDT] Little Find DTB Entry[0]: Rev:(S:0, E:255, X:0, D:26)`).
* The first extraction was corrupted by a podman VM crash (32,916 of 69,687 files
  became 0 bytes, including `init/main.c`) and was redone with verification
  (25 zero-byte files remain, all legitimately empty).

## Toolchain / host
* macOShost -> podman machine (applehv), raised from 4 CPU/4 GiB to **6 CPU/8 GiB**
  because the VM was repeatedly dying.
* Container `nuxel-kb` = `docker.io/library/fedora:43`, native **aarch64**
  (`CROSS_COMPILE=` empty), with make/gcc/bc/bison/flex/openssl-devel/
  elfutils-libelf-devel/perl/diffutils/findutils/which/tar/xz/gzip/cpio/python3/
  kmod/dtc/rsync/procps-ng.
* Build volume `nuxel-kbuild` -> `/b` (source at `/b/src2`, artifacts at `/b/a7`).
  The Mac's home is *not* mounted into the container, so inputs/outputs go through
  `podman cp`; the kernel is built on the VM disk, not over virtiofs.

## Config changes (deliberately minimal)
| Setting | Value | Reason |
|---|---|---|
| defconfig | in-tree `exynos9820-beyond2lte_defconfig`, **unmodified, no foreign fragment** | preserves all hardware-critical Samsung config (Exynos DRM/DSI, sec_ts, bcmdhd, madera/CS47L93, S3NRN82, FIMC-IS, UFS) |
| `CONFIG_INITRAMFS_SOURCE` | `/b/a7/initramfs.cpio` | built-in initramfs; makes `/init` present in rootfs so `kernel_init()` skips `prepare_namespace()` (and therefore `SAR_RD` / `root=PARTUUID` / "init group exit") |
| `CONFIG_INITRAMFS_COMPRESSION_GZIP` | y | kernel-side compression of the built-in archive |
| `CONFIG_INITRAMFS_FORCE` | **not set** | the external initrd is still attempted first; `init/initramfs.c` restores the built-in archive via `clean_rootfs()` + re-unpack if it is junk, so a bad handoff costs nothing |
| `-Werror` relaxations | via `tools/kernel-relax-werror.sh` | the 4.14 tree predates GCC 15 |

## Embedded diagnostics (`kernel/s10plus/patches/0003-nuxel-initramfs-delivery-diagnostics.patch`)
`pr_alert` (so Samsung's `loglevel=4` cannot filter it) in `init/initramfs.c`:
* `populate_rootfs()` entry: `builtin=<addr> builtin_size=<n> external_initrd=<0|1>
  start=<hex> end=<hex> len=<n>`
* the first 16 bytes at `initrd_start`, hex + ASCII — **only the memory S-Boot
  itself declared as the initrd**, never arbitrary physical memory
* per attempt: first byte, `this_header`, remaining length, and the
  `decompress_method()` name (or `(none)`)
* the final verdict: `message` and the parser `state`

This is the mission's "if both experiments fail, instrument the exact
`init/initramfs.c` code path" step, folded into A7 so that one build both *fixes*
the handoff dependency and *decides* H-INITRD-MEM.

## Embedded initramfs (A7 payload)
`build/out/s10plus/debug-candidates/A7/initramfs.cpio` — 876,344 B, 66 records,
derived from the proven A4 cpio with exactly three changes:
1. `/init` <- `boot/initramfs/init.sh` (the milestone-marker version), mode 0100755
2. added `dev/console` (c 5:1, 0600) and `dev/null` (c 1:3, 0666) — required
   because `prepare_namespace()` (and therefore `devtmpfs_mount`) is skipped
3. **removed** `boot/nuxel-boot-animation.mp4` (5,474,699 B) and
   `boot/nuxel-boot-splash.raw` (1,843,200 B)

Change 3 is a deliberate, documented size reduction for the *diagnostic* build: it
keeps the built-in initramfs at ~0.9 MB so the kernel `Image` stays well below the
BOOT partition and so the external ramdisk also stops tripping Samsung's
`SAR_RD` kmalloc limit (>4 MB -> `mm/page_alloc.c:4258`). The splash and animation
belong to the display milestone (PHASE 5) and must be reintroduced there.
`sha256(initramfs.cpio) = 3117e0d9c21d4818c27d2b109df0ce92e91a6fcdec507c7b9503934e452032d8`

## Status
Build running in container `nuxel-kb`; log `/b/a7/build.log`.
Outputs expected: `arch/arm64/boot/Image` (raw, for the BOOT container) and the
`exynos9820-beyond2lte_eur_open_26.dtb` family (for a DT-compatibility comparison
against the hardware-proven appended DTB).
