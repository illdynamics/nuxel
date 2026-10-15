# STATUS — cycle 3 (2026-10-15)

**Mission:** boot Nuxel (Fedora 43 aarch64) on Samsung Galaxy S10+ SM-G975F
(`beyond2lte`), Exynos 9820 rev 26, bootloader G975FXXSEFUL1, TWRP 3.7.0_9-2.

## Headline — cycle 3
**Milestones 3 and 4 are achieved on hardware.** A7's instrumented kernel shows
the built-in initramfs unpacks (`message=(none) state=7`) and that `/init` exists
and is executed (`prepare_namespace()` never ran). It also *measures* the real
reason cycles 1-2 failed: on a normal BOOT-partition boot S-Boot publishes
`/chosen/linux,initrd-start = 0x89000000` with a length taken from our header but
**never loads the payload** — the bytes there are kernel console text or zeros.
And it exposes the reason nothing was ever visible: **`/dev/console` is ENODEV on
this device** (no tty behind `console=ram`), so PID 1 has no stdio. A8 re-routes
all evidence to `/dev/kmsg` (which works) and adds a 45 s watchdog.

## Headline (cycle 2, superseded)
Cycle 2 fixed the *container* and got the Nuxel kernel to execute on hardware
(A2-A5 all produced pstore panic dumps naming `nuxel@nuxel-phosh`). The single
remaining blocker is the **ramdisk handoff**: the kernel is handed the right
*length* of memory that does not contain our initramfs
(`rootfs image is not initramfs (junk in compressed archive)`).

Cycle 3 did three things:

1. **Removed the build regression.** `boot/s10plus/build-debug-candidate.sh`
   defaulted to the hardware-falsified `nuxel-beyond2lte-boot-merged-fixed.img`
   and piped it through `tools/s10plus/patch-boot-from-upload.py`, which emits a
   **gzip kernel** and the **legacy header** (DTB size at offset 40). Both defects
   are hardware-proven fatal (A1: seven silent loads). That path is gone: the
   candidate builder is now `boot/s10plus/build-candidate.sh`, it is fail-closed,
   and every build is checked by `tools/s10plus/verify-boot-image.py`.
2. **Found a second, independent reason no boot ever produced initramfs
   evidence.** `prepare_namespace()` is skipped when the initramfs supplies
   `/init`, so the kernel never mounts devtmpfs and `/dev/console` must come from
   the archive. Our initramfs shipped an *empty* `dev/` directory, and the panic
   chain shows `Warning: unable to open an initial console.` — so even a
   successful `populate_rootfs()` + `/init` would have produced **zero console
   output**, and `grep -c nuxel-init` = 0 was never evidence that `/init` did not
   run. A6 adds `dev/console` (c 5:1) and `dev/null` (c 1:3) to the archive and
   emits the mission's `NUXEL_MARKER` lines from executing code.
3. **A6 is built, gated and flashed.** Nuxel initramfs in the LZMA-alone
   container shape of the one ramdisk this handset is observed to deliver *and*
   unpack (TWRP: props `5d`, dict 8 MiB, unknown size => end-of-stream marker),
   page-aligned so no S-Boot rounding rule can clip the stream.

## Evidence captured this cycle (S-Boot + device-tree forensics)
* The bootloader's own live device tree on the *booting* recovery session:
  `linux,initrd-start = 0x89000000`, `linux,initrd-end = 0x89a66800` =>
  the delivered initrd length is `0xa66800` = **round_up(header ramdisk_size,
  2048)** for TWRP, and the ramdisk is placed at a **fixed** 0x89000000, i.e.
  S-Boot ignores the header's `ramdisk_addr` (0x11000000) on both images.
* 0x89000000 lies inside `/reserved-memory/sec_rdx_bootdev`
  (`0x88000000..0x92d00000`), which this kernel deliberately does **not** reserve
  ("Reserved memory: skip to reserve memory for node 'sec_rdx_bootdev'",
  `CONFIG_SAMSUNG_PRODUCT_SHIP` + `no-ship`). The initrd itself is still
  memblock-reserved in `arm64_memblock_init()`.
* S-Boot log for our images: `[UFDT] BOOT IMG HDR V1.. FINDING DTB ENTRY` ->
  `Little Find DTB Entry[0]: Rev:(S:0, E:255, X:0, D:26)` -> `DT Overlay
  Complete!` -> `Updating device tree @0x8a000000` -> `Starting kernel...`.
  **The appended DTB in our boot image IS used** (it is the UFDT base), so DTB
  changes are effective experiments; `/chosen/linux,initrd-*` and `bootargs` are
  overwritten by S-Boot, so changes to those are **not**.
* `bootmode=` is present as `bootmode=2` only on the recovery boot; a normal
  BOOT-partition boot has no `bootmode=` token, which is why the kernel then runs
  Samsung's `SAR_RD` `mount_sar_ramdisk()` fallback (and fails it: 8 MB kmalloc).

## Milestones

| # | Milestone | State | Evidence |
|---|---|---|---|
| 1 | S-Boot starts Nuxel kernel | **ACHIEVED** | S-Boot records + `Starting kernel...` |
| 2 | Kernel runs, persistent logging works | **ACHIEVED** | pstore `linux_banner: Linux version 4.14.253 (nuxel@nuxel-phosh)` |
| 3 | External or embedded initramfs unpacks | **ACHIEVED (A7, hardware)** | instrumented kernel: built-in archive `unpack verdict: message=(none) state=7` (success), twice |
| 4 | Nuxel `/init` executes | **ACHIEVED (A7, hardware)** | `prepare_namespace()` never ran (`RAMDISK:`=0, `SAR_RD`=0, `init group exit`=0) and `Failed to execute /init`=0 ⇒ `/init` existed and exec succeeded. Output was invisible because `/dev/console` is ENODEV on this handset; A8 re-routes evidence to `/dev/kmsg` |
| 5 | USERDATA rootfs discovered | **ACHIEVED (A12, hardware)** | `USERDATA_FALLBACK /dev/sda31` after the PARTNAME probe failed; logged by executing code |
| 6 | Fedora rootfs mounts | **ACHIEVED (A12, hardware)** | `EXT4-fs (sda31): mounted filesystem with ordered data mode` + `ROOTFS_MOUNTED` marker |
| 7 | Fedora userspace process runs | **HANDOFF STARTED (A12)** | `ROOTFS_HANDOFF_STARTED` + `switching root -> /newroot`; nothing observable after `switch_root` yet |
| 8 | Compatible init system starts | **UNTESTED, known risk** | Fedora 43 systemd 258.11 vs Linux 4.14.253 (see HYPOTHESES H-SYSTEMD-4.14) |
| 9 | Display usable / first light | PARTIAL (drivers only) | A2 kernel dump has `decon0/2`, `dsim0-wq`, `130b0000.displa`, `panel-bl-thread` |
| 10 | Phoc / Phosh / usable interface | NOT YET | greetd is configured as `agreety --cmd /bin/sh` |

## Attempt ledger (cycle 3)
| ID | Change | Gate | Write/readback | Boot result |
|---|---|---|---|---|
| A6 | ramdisk -> LZMA-alone (TWRP-shaped), page-aligned; +`dev/console`,`dev/null`; +`NUXEL_MARKER` instrumentation | PASS | verified `ba4f70c6…` | **FAILED** — S-Boot consumed the new size (`ramdisk size = 0x5c0000`) but the kernel still read junk **0.21 ms** after starting => container format refuted, payload not delivered |
| A7 | **kernel rebuilt with a built-in initramfs (`CONFIG_INITRAMFS_SOURCE`) + `init/initramfs.c` delivery diagnostics (pr_alert)** | PASS | verified `f8587521…` | **FAILED** as a boot, but **milestones 3 + 4 reached**: built-in archive unpacked (`state=7`) and `/init` executed; boot then killed by Samsung's `hard_reset_hook` at 37/68 s and a `hung_task` panic at 242 s |
| A8 | `/dev/kmsg` evidence channel + `/dev/kmsg` node + 45 s watchdog + early BOOT-slack heartbeat | PASS | verified `314d5e53…` | **FAILED** — but `/init`'s own output appeared in the ram console for the first time: **milestone 4 proven** |
| A9 | arm64 DT path, no blocking `dmesg`, vendor-leash sysctls, softdog keeper, fallback device nodes | PASS | verified `10e12641…` | **FAILED** — devtmpfs mounts; identity still unknown, so the generic probe chose `/dev/sda2` |
| A10 | logged mounts, cmdline identity, documented USERDATA fallback, rootfs os-release check | PASS | verified `83aa1ede…` | **FAILED** — identity detected but the dispatch still ran the generic probe |
| A11 | deterministic identity pin + dispatch logging + generic-probe guard on exynos9820 | PASS | verified `be58121b…` | **FAILED** — proved `DEVICE='s10plus'` at the dispatch yet the generic branch ran |
| A12 | `force_s10plus_root()` override + `mknod` re-creation of the fallback nodes (devtmpfs shadows them) + `wc` applet | PASS | verified `68217cdd…` | **FAILED as a boot, but reached milestones 5, 6 and the rootfs handoff** |

## Verification states (kept strictly separate)
* **Source-level fixes:** `boot/s10plus/build-candidate.sh` (new),
  `boot/s10plus/build-debug-candidate.sh` (rewritten), `boot/s10plus/pack-boot-v1.sh`
  (`--strict`), `boot/initramfs/init.sh` (markers + initrd logging),
  `tools/s10plus/verify-boot-image.py` (new), `tools/s10plus/newc.py` (new),
  `tools/s10plus/unpack-boot-image.py` (new),
  `boot/s10plus/tests/test-boot-image-gates.sh` (new).
* **Offline-verified artifacts:** 11/11 gate regression tests pass; A6 passes the
  full gate, and its kernel + DTB are **byte-identical** to the hardware-proven
  A5; its ramdisk decompresses to a 68-record cpio whose `/init` is byte-identical
  to `boot/initramfs/init.sh`.
* **Hardware-proven behaviour:** only milestones 1-2 above. Nothing about A6 is
  hardware-proven yet.

## Standing risks
* `backups/s10plus/boot-original.img` is a `DUMMY` placeholder — there is still
  **no** real stock BOOT backup. RECOVERY is untouched and backed up, so the
  recovery path stays intact. All writes this cycle remain BOOT-only.
* `/dev/console` is now in the initramfs, so the next failure will leave *actual
  text* in the kernel ram console — the observability gap that made A2-A5
  ambiguous is closed.
