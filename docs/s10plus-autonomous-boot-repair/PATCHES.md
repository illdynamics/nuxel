# PATCHES

## P-A2-1 — ship the uncompressed arm64 `Image` in the S10+ BOOT container
**File:** new candidate artifact only (no source edit yet)
`build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A2-uncompressed.img`
**Built by:** `python3 boot/s10plus/pack-boot-v1.sh --kernel <raw Image> …`
(the packer is reused unchanged, so the header layout is identical to A1 —
deliberate single-variable change).

**Reason.** See `HYPOTHESES.md` H-KERNEL-GZIP + `DEVICE-EVIDENCE.md` E2/E4.

**Derivation (reproducible).**
```
A1 = nuxel-beyond2lte-boot-diag-cmdline-free.img   (sha256 eb77d658…)
  kernel (gzip)  = A1[2048 : 2048+16030259]        -> sha256 33cac63a…
  Image          = gunzip(kernel)                   -> 44980232 B, sha256 14b64847…
  ramdisk        = A1[16033792 : +6022352]          (unchanged)
  merged dtb     = A1[22056960 : +376101]           (unchanged, d00dfeed)
  cmdline        = "buildvariant=userdebug nuxel.device=s10plus root=… userdata …"
  addrs          = 0x10008000 / 0x11000000 / 0x10000100, page 2048
```

## KNOWN DEFECT (found, not yet fixed) — `pack-boot-v1.sh` header layout
`boot/s10plus/pack-boot-v1.sh` documents and writes a field it calls `dt_size` at
**header offset 40**. In a real `boot_img_hdr_v1` offset 40 is `header_version`
(must be `1`) and offset 44 is `os_version`. The same mis-layout is duplicated in
`tools/s10plus/patch-boot-from-upload.py` (it reads offset 40 as `dtlen`).
This is left unfixed on purpose for this cycle so A2 tests exactly one variable;
the fix is queued as **P-A3-1** (candidate A3) with the two dependent readers
updated together.

## Unchanged by this cycle
`boot/initramfs/init.sh` (A1's cmdline-independent init is kept; it is correct
for this device — S-Boot really does replace `/chosen/bootargs`).
Kernel binary, merged DTB, load addresses, page size, cmdline: all untouched.

## P-A3-1 — container normalised to the device's own booting format (candidate A3)
**Built by:** `python3 boot/s10plus/pack-boot-v1.sh --kernel <raw Image> --ramdisk
<uncompressed cpio> --dtb <merged.dtb> --v1-spec …`

Three concrete corrections, all in the BOOT container (kernel binary, DTB and
cmdline untouched):

1. **Ramdisk payload: gzip stream -> uncompressed `newc` cpio, zero-padded to an
   exact multiple of 2048 bytes (8,194,048 B).** Removes the decompressor from the
   path and makes any S-Boot sector-size rounding a no-op, because only trailing
   zeros can be affected (the archive's `TRAILER!!!` is followed by 1,144 zero
   bytes and the total size is already 2048-aligned).
2. **Header made spec-compliant `boot_img_hdr_v1`** (`header_version=1` at offset
   40, `os_version=0x18000171` at 44, `header_size=1648` at 1644) — byte-identical
   values to the unit's TWRP recovery image, the only image S-Boot is observed to
   boot. S-Boot logs the field (`[UFDT] BOOT IMG HDR V376101` vs `V1`).
3. **Fix to `boot/s10plus/pack-boot-v1.sh`** (opt-in `--v1-spec`; defaults
   unchanged so existing callers such as `tools/s10plus/patch-boot-from-upload.py`
   keep working). The tool previously wrote the DTB size into offset 40, which is
   `header_version` in the real header; the legacy behaviour is still the default
   and is documented as a defect.

**Still outstanding (queued):** `tools/s10plus/patch-boot-from-upload.py` reads
offset 40 as `dtlen`, so it must be taught about the v1 layout before it is used
with `--v1-spec` images. `--v1-spec` is therefore only used by the explicit
candidate build command, not by the default build path.

## P-A5-1 — remove the bogus `/chosen` initrd placeholder from the boot-image DTB (candidate A5)
**Found by:** decompiling the DTB embedded in the boot image
(`build/out/s10plus/debug-candidates/A2/merged.dtb`) with `dtc`:
```
chosen: chosen {
    bootargs = [00];
    linux,initrd-start = <0x84000000>;   /* 0x84000000 == pack-boot-v1.sh
    linux,initrd-end   = <0x841fffff>;      DEFAULT_RAMDISK_ADDR PLACEHOLDER */
    linux,phandle = <0x1e2>;
    phandle = <0x1e2>;
};
```
`0x84000000` is the S10+ packer's *documented placeholder* ramdisk load address, and
`0x841fffff` is a 2 MiB window - nothing to do with a real 6-8 MB initramfs.

**Why it matters:** on this boot path S-Boot merges the boot image's DTB
(`[UFDT] BOOT IMG HDR V1.. FINDING DTB ENTRY`, `dtb_update`, `Updating device tree
@0x8a000000`). The kernel takes its initrd from `/chosen/linux,initrd-start|end`.
A stale placeholder pair in the image is exactly the kind of thing that leaves the
kernel reading the initrd from the wrong physical address while still being told
the right *length* - which is precisely the signature observed in A2/A3/A4
(`Freeing initrd memory: 8128K` = exactly our 8,323,072 B payload, yet
`rootfs image is not initramfs (junk in compressed archive)`).

**Change:** `dtc` decompile -> delete `linux,initrd-start`, `linux,initrd-end` and
the empty `bootargs` from `/chosen` (keeping the phandles) -> recompile
(376,101 -> 376,689 B). Everything else in A5 is identical to A4.

**Candidate:** `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A5-dtb-fix.img`
sha256 `6950241c52320688f28bfc1a0c0426f28e3884e5772934853759354aa97a88d1`.
Write + readback **VERIFIED**; reboot 2026-10-15T07:31:59Z.

## Defects found in the S10+ packer (all confirmed against a booting image)
| # | Defect | Status |
|---|---|---|
| 1 | `pack-boot-v1.sh` wrote the DTB size into header offset 40, where `boot_img_hdr_v1` requires `header_version=1`; `os_version` (offset 44) left 0. S-Boot logs the value (`BOOT IMG HDR V376101` vs `V1`) and even failed `set os_version`. | **fixed** (`--v1-spec`, used by A3+) |
| 2 | The DTB the packer embeds inherits `/chosen/linux,initrd-start/end` placeholders (`0x84000000`/`0x841fffff`) that misdescribe the initrd to the kernel. | **patching DTB in A5** |
| 3 | The packer's example/default kernel input is `Image.gz`; on this unit S-Boot jumps straight to `kernel_addr`, so a gzip payload is executed as code (7 silent loads). Only a raw `Image` works. | **fixed** (A2+); `pack-boot-v1.sh` should reject/warn on gzip kernels |
| 4 | `tools/s10plus/patch-boot-from-upload.py` reads header offset 40 as the DTB length and assumes the legacy layout, so it cannot consume `--v1-spec` images. | **open** |

---

# PATCHES — cycle 3 (2026-10-15)

## P-C3-1 — REMOVE THE REGRESSION GENERATOR from the direct S10+ boot path (source-level)
**Files:** `boot/s10plus/build-debug-candidate.sh` (rewritten),
`boot/s10plus/build-candidate.sh` (new), `boot/s10plus/pack-boot-v1.sh` (`--strict`).

**Defect.** `build-debug-candidate.sh` defaulted to
`build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img` — the image that
already produced seven silent loads — and piped it through
`tools/s10plus/patch-boot-from-upload.py`, which unconditionally
* re-writes the ramdisk with `gzip_bytes(..., 9)` (**gzip kernel? no — gzip
  ramdisk, but it also copies the input's gzip kernel**), and
* calls `pack-boot-v1.sh` **without** `--v1-spec`, so the DTB size lands at header
  offset 40 again (legacy header).

Together those are exactly the two hardware-proven fatal defects of attempt A1.
`patch-boot-from-upload.py` also *requires* `nuxel.device=s10plus` to be present
in the boot-image cmdline, which S-Boot discards, and it forces `/bin/sh` to be a
toybox symlink.

**Fix.**
* `boot/s10plus/build-candidate.sh` (new, gated) is the only path that produces
  BOOT candidates. It unpacks a **hardware-proven base image**
  (default: the A5 candidate) into kernel / ramdisk / DTB, optionally replaces
  `/init`, inserts device nodes, recompresses the ramdisk, repacks with
  `pack-boot-v1.sh --v1-spec --strict`, and then requires a **PASS** from
  `tools/s10plus/verify-boot-image.py`. It refuses to overwrite an existing
  candidate (so hardware-tested images are never clobbered) and writes a report.
* `build-debug-candidate.sh` is now a thin wrapper over it and no longer calls
  `patch-boot-from-upload.py`.
* `pack-boot-v1.sh --strict` turns a gzip kernel payload into a hard error (and
  warns loudly without `--strict`, so other callers keep working).

## P-C3-2 — `tools/s10plus/verify-boot-image.py`: fail-closed release gates (new, source-level)
Encodes the hardware facts instead of a description of them:

| Gate | Failure it prevents |
|---|---|
| file size <= BOOT partition (57,671,680 B) | unwritable/truncated flashes |
| `ANDROID!` magic, `page_size == 2048` | wrong container family |
| `header_version == 1` at offset 40 (+ names the legacy DTB-size defect when the value is > 4096), `header_size == 1648` | A1/A2 legacy header (S-Boot `HDR V376101`) |
| kernel payload != gzip; `ARM\x64` present at offset 0x38; plausible `text_offset`/`image_size`/`flags` | A1/legacy silent-load class |
| ramdisk offset == `page + round_up(kernel_size, page)`; region inside the image | mis-set offsets S-Boot would read from the wrong place |
| ramdisk container decode: lzma-alone (incl. the EOS-marker variant the device uses), gzip, xz, bzip2, raw cpio | un-decodable payloads |
| cpio: `TRAILER!!!` reached, no absolute/`..` names, trailer padding all zero | A3's truncation and any hand-mangled archive |
| `/init` present, regular, mode & 0111; `#!` interpreter present in the archive | kernel would fall back to `prepare_namespace()` and mount SYSTEM |
| warning when `/dev/console` is absent | the silent-evidence trap (P-C3-3) |
| appended DTB magic + declared size; warns about `/chosen/linux,initrd-*` placeholders | stale-placeholder "experiments" |
| prints SHA-256 of image, kernel, ramdisk, decompressed cpio | provenance |

## P-C3-3 — the initramfs had no console: `dev/console`, `dev/null`, and real milestone markers
**Files:** `boot/initramfs/init.sh`, `boot/s10plus/build-candidate.sh`.

`populate_rootfs()` is a `rootfs_initcall`; when it succeeds and `/init` exists,
`kernel_init_freeable()` skips `prepare_namespace()`, so devtmpfs is never mounted
and `/dev/console` must come from the archive. Our cpio had an **empty** `dev/`
directory while every panic chain shows
`Warning: unable to open an initial console.` — so PID 1 had no working stdio and
no initramfs text could ever be captured. `build-candidate.sh` now inserts
`dev/console` (char 5:1, 0600) and `dev/null` (char 1:3, 0666).

`init.sh` now emits the mission's milestone markers from **executing** code as the
very first statement (shell builtins only, so they work even with a broken PATH):
`INITRAMFS_EXECUTED`, then `USERDATA_DISCOVERED`, `ROOTFS_MOUNTED`,
`ROOTFS_HANDOFF_STARTED`, written to `/dev/console` and to the in-RAM diagnostic
record. It also logs the `chosen/linux,initrd-start|end` the bootloader actually
handed this kernel, which is the single unknown that made A2-A5 ambiguous.

## P-C3-4 — `tools/s10plus/newc.py` (new, source-level)
Dependency-free newc reader/replacer/inserter (macOS has no `cpio`). Guarantees
that replacing a member with identical bytes reproduces the archive
**byte-for-byte** (verified in the test suite) and refuses archives without
`TRAILER!!!`.

## P-C3-5 — candidate A6: the device's own proven ramdisk container shape
**Built by:** `boot/s10plus/build-candidate.sh --compress lzma`
**Candidate:** `build/out/s10plus/debug-candidates/A6/boot.img`
sha256 `ba4f70c6384bd018e5d7d29bf0c28db458f5d0f2671410837649c6ab548ebc49`
(51,390,464 B).

* kernel `Image` and appended DTB: **byte-identical to A5** (the container whose
  kernel is hardware-proven to execute, `14b64847…` / `bcdef39c…`).
* ramdisk: LZMA-alone, properties byte `0x5d` (lc=3 lp=0 pb=2), dictionary
  8 MiB, uncompressed-size field `0xffffffffffffffff` => end-of-stream marker —
  **the exact container shape of the TWRP ramdisk that this S-Boot delivers and
  this kernel unpacks** — zero-padded to an exact multiple of 65,536 bytes
  (6,029,312 B) so that any S-Boot rounding rule (up, down, or exact) yields a
  length that contains the whole stream.
* initramfs: 68 records, decompresses to 8,260,060 B, `TRAILER!!!` record at
  8,194,400 (logical end 8,194,524) followed by exactly 65,536 zero bytes inside
  the stream; `/init` = 26,413 B mode 0100755 **byte-identical to
  `boot/initramfs/init.sh`**; `/bin/sh -> toybox`; `dev/console`, `dev/null`.
* gate: PASS. Report: `build/out/s10plus/debug-candidates/A6/BUILD-REPORT.txt`.

## P-C3-6 — kernel rebuilt with a BUILT-IN initramfs + delivery diagnostics (A7, hardware-proven)
**Files:** `boot/s10plus/build-kernel-a7-embedded-initramfs.sh` (new),
`kernel/s10plus/patches/0003-nuxel-initramfs-delivery-diagnostics.patch` (new),
plus A7 artifacts under `build/out/s10plus/debug-candidates/A7/`.
**Source:** `Linux4/android_kernel_samsung_exynos9820@f7194c1d` (Linux 4.14.253),
in-tree `exynos9820-beyond2lte_defconfig` **unmodified** (no foreign fragment).
**Toolchain:** Fedora 43 container, native aarch64, `gcc 15.3.1 20260722 (Red Hat
15.3.1-1)` — the same compiler as the hardware-proven kernel's banner.
**Config delta:** `CONFIG_INITRAMFS_SOURCE="/b/initramfs.cpio"`,
`CONFIG_INITRAMFS_COMPRESSION=".gz"`, `CONFIG_INITRAMFS_FORCE` **off**.
**Diagnostics:** `pr_alert` in `init/initramfs.c` reporting the built-in and
external initrd addresses/sizes, the first 16 bytes at `initrd_start`,
`decompress_method()` per attempt, and the final `message`/`state`.
**Result (hardware):** built-in archive `state=7` (success); `/init` executed;
the external initrd is published at `0x89000000` with our header's length but was
never loaded (head bytes = kernel console text). Documented in ROOT-CAUSE.md.

## P-C3-7 — evidence channel `/dev/kmsg`, `/dev/kmsg` node, and a boot watchdog (A8)
**Files:** `boot/initramfs/init.sh`, `boot/s10plus/build-candidate.sh` payload.
* `/dev/console` is **ENODEV** on this handset (`console=ram` has no tty), so
  `nuxel_say()`/`nuxel_marker()` now write to `/dev/kmsg` first and fall back to
  `/dev/console` and then stdout. S-Boot's cmdline sets `printk.devkmsg=on`, so
  `/dev/kmsg` writes land in the Samsung ram console and survive the bootloop.
* The initramfs ships `dev/kmsg` (char 1:11, 0600) so the node exists before
  devtmpfs is mounted.
* `NUXEL_BOOT_WATCHDOG` (default **45 s**) persists evidence then `reboot -f`; it is
  disarmed immediately before `switch_root`. Measured requirement: A7's boots were
  killed by the vendor kernel at 37 s / 68 s (`hard_reset_hook`) and 242 s
  (`hung_task`), so the initramfs must finish inside ~40 s.
* An **early heartbeat** runs as soon as `diag_persist()` is defined, writing the
  BOOT-partition slack record and printing the block devices found in `/dev`, so a
  later reset still leaves a readable record (one `dd` from recovery).

## P-C3-8 — repository hygiene from this cycle
* `boot/s10plus/tests/test-boot-image-gates.sh` — 11 regression tests; the gate
  fails the two hardware-falsified images (A1/legacy, gzip kernel + offset-40
  header) and passes the two hardware-proven ones (A5, TWRP recovery).
* `tools/s10plus/{verify-boot-image,newc,unpack-boot-image}.py` — gate, cpio tool,
  section splitter; the cpio tool round-trips byte-identically and the gate now
  also rejects duplicate archive members (a doubled `/init` or `/dev/console`).
* `boot/s10plus/build-debug-candidate.sh` — no longer calls
  `tools/s10plus/patch-boot-from-upload.py` (the gzip-kernel + legacy-header
  regression path); it delegates to the gated builder.

## Verified artifacts produced this cycle
| Artifact | sha256 |
|---|---|
| `A7/Image-A7` (kernel, embedded initramfs + KDIAG) | `d5e64b0fcdf4ede056aeb172fa546deda92b481e56a4170e9033dc0d6a4fce1a` |
| `A7/boot.img` | `f8587521655191b8927ab21f8126864472def6e8f802f17a85da2627b2cf98da` |
| `A8/Image-A8` (adds `/dev/kmsg` initramfs + watchdog init) | `f887030acd5c394b97ccd154db7e6252adc21b457b957177fe56287202d8b876` |
| `A8/boot.img` | `314d5e532f3e0a25d324c87e844110b173db20306d42ca83d67c2684fa6f026a` |


---

# PATCHES — cycle 4 (A13)

## P-C4-1 — systemd 258.11: fall back to plain `posix_spawn()` when `pidfd_spawn()` is unavailable

* **File:** `src/basic/process-util.c` in `systemd-258.11-1.fc43.src.rpm`
* **Applied by:** `.scratch/s10plus-cycle4/a13/nuxel-pidfd-edit.py`, invoked from
  `%prep` immediately after `%autosetup` (an exact textual replacement, **not** a
  context patch — a `--fuzz=0` context patch was attempted first and correctly
  refused; the deterministic edit removes that failure mode).
* **Change:** when `pidfd_spawn()` returns a not-supported errno, call plain
  `posix_spawn()`, register the child with `pidref_set_pid()` and return `0` so the
  caller attaches it to its cgroup (upstream's own behaviour). Previously the same
  `pidfd_spawn()` was retried and the ENOSYS propagated.
* **Delivered as:** `/usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so`
  `sha256 502507a7b6237a03cfcff49e389d2a38836916abdea40e36e5ba4653e9bc1234`,
  *inside the initramfs*, installed by A13's init script into
  `${ROOT_MNT}/usr/lib64/systemd/` (original kept as `…so.nuxel-orig`). Only the
  BOOT partition and that one file inside the mounted rootfs are written.
* **Verified:** disassembly shows two spawn call sites in `posix_spawn_wrapper`
  where the original had one; `nm -D` on the original confirms
  `posix_spawn_wrapper@@SD_SHARED` is defined there and only imported by
  `libsystemd-core`, so no second library needs replacing.

## P-C4-2 — initramfs `init.sh`: watchdog replaced by a signal-free dead-man's switch

* **Files:** `boot/initramfs/init.sh` (A12 baseline preserved as
  `init.sh.bak-A12`, `sha256 85dba795…`), applied by
  `.scratch/s10plus-cycle4/a13/edit-init.py`.
* **Why:** the A12 disarm used the `kill` applet, which this toybox build does not
  have, so the watchdog force-rebooted a *running* Fedora 30 s after
  `switch_root`.
* **How:** the watchdog `cd`s into the procfs (a cwd survives every mount being
  moved away, a path does not), sleeps, then reads `/proc/1/comm` relatively. It
  reboots **only** while PID 1 is still the initramfs shell; once systemd owns PID
  1 it exits silently. No signals, no binaries that may have been deleted by
  `switch_root`.

## P-C4-3 — initramfs `init.sh`: rw root for s10plus, vendor `ro` ignored

* **Why:** A12 mounted `ROOT_MOUNT_MODE=ro` purely because S-Boot's own command
  line carries a bare `ro`; the pattern `*' ro '*` matched the *vendor* cmdline,
  which is not ours to control and describes Android recovery semantics.
* **How:** only an explicit `nuxel.rootmode=ro|rw` can now select read-only.
  Before a rw mount the script still runs `e2fsck -p`; the USERDATA filesystem is
  `Filesystem state: clean` (`dumpe2fs -h`) and was only ever mounted `ro` in A12,
  so no dirty-filesystem remount is being attempted.

## P-C4-4 — initramfs `init.sh`: identity gate made explicit and loud

* **Why:** A12 printed `rootfs os-release: <none>` and then handed off anyway —
  neither the success branch nor the failure branch produced a line, so the gate
  reported nothing at all.
* **How:** the file is chosen by name (`usr/lib/os-release`, then
  `etc/os-release`), its content is logged verbatim in
  `ROOTFS_IDENTITY_RAW file=… text=…`, and each outcome emits a distinct marker
  (`ROOTFS_IDENTITY_OK` / `ROOTFS_IDENTITY_FAIL`). A negative is recorded loudly
  and does **not** stop the boot, because this exact rootfs image is offline-
  verified Fedora/Nuxel and a gate bug must not be able to block the mission.

## P-C4-5 — initramfs `init.sh`: fresh `/proc`, `/sys`, `/dev` instead of `mount --move`

* **Why:** moving our devtmpfs into the new root detached `/dev/kmsg` by path for
  everything still on the old root — that is how A12's watchdog message vanished.
* **How:** `mount -t proc|sysfs|devtmpfs` into `${ROOT_MNT}` with the old
  `mount --move` kept only as a fallback. The initramfs evidence channel survives
  the handoff.

## P-C4-6 — new probes run on the handset

* `tools/s10plus/nuxel-syscall-probe.c` (freestanding aarch64, raw syscalls) —
  writes a `NUXEL-SYSCALL <name> ret=… errno=…` table for `waitid(P_PIDFD)`,
  `waitid(P_PID)`, `clone3`, `pidfd_open`, `clone(CLONE_PIDFD)`,
  `clone(SIGCHLD)+execve(/bin/sh)`, `fsopen`, `fspick`, `open_tree`, `memfd_create`.
* `tools/s10plus/nuxel-spawn-probe.c` (glibc 2.42, static **and** dynamic) — calls
  the same probe glibc uses, then `posix_spawn()` and `pidfd_spawn()`, printing
  each return value and errno.
* Both are measurement only; neither is on the boot-critical path.

## Artifacts produced this cycle
| Artifact | sha256 |
|---|---|
| `A13/Image-A13` (kernel, same source/config as A12, new embedded initramfs) | `aa28769a95303ce42e79ecc212936418f27a5b68a6631ee8f0b95abac7871bd7` |
| `A13/initramfs.cpio` | `f1333d79e403dcd0ad832db6eb6af1184b566eb42913b25b69e7a30ef498bc96` |
| `A13/boot.img` | `bdc06dfe8a8cabe2de904e6224403741eb43fcd1d36eb491e699911f090df086` |
| patched `libsystemd-shared-258.11-1.fc43.so` | `502507a7b6237a03cfcff49e389d2a38836916abdea40e36e5ba4653e9bc1234` |
| `nuxel-syscall-probe` | `c687148cd50f7bac…` (see `A13/` for the full digest) |
| `nuxel-spawn-probe` | `5f72b673aaccf5a16e22808dd35717c0e1fa811377ab43c26002169d2f84836e` |
| `nuxel-spawn-probe-static` | `6adbf30d631f30dc7f83ed6d2afd1971ce367105a7a24f93b1b7771dd4b9cabe` |
| A12 baseline `boot.img` (unchanged, re-verified) | `68217cdd59d047108f9e28de6d008fb8360dc9a5654b338df0c7bad4c26054ed` |
