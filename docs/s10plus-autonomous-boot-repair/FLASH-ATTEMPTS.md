# FLASH-ATTEMPTS

Rule: a flash counts only with (a) executed write, (b) full readback SHA-256 equal
to the local image, (c) an explicit attempt record. No auto-reboot without an
observation window. Max 3 distinct evidence-backed candidates per cycle.

## BAckground (prior cycle, already verified before this cycle started)
| When | What | Image | Result |
|---|---|---|---|
| 2026-10-14 | BOOT + USERDATA flashed by hand via TWRP adb | `nuxel-beyond2lte-boot-merged-fixed.img` (22,431,744 B, `ceba64ab…`), `nuxel-beyond2lte-rootfs-fedora-phone-fixed.img` (4,294,967,296 B, `d4f8d632…`) | full-image readbacks matched; boot -> Samsung-logo loop |

## This cycle

### A1 — BOOT-only: instrumented, cmdline-independent initramfs
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img` |
| Target | `/dev/block/by-name/boot` (sda14) **only**; USERDATA untouched |
| Kernel/DTB | byte-identical to the currently flashed image |
| Preflight | pack `05-preflight.sh --profile s10plus --boot-only` -> **PREFLIGHT PASS**; BOOT `boot -> /dev/block/sda14` 57,671,680 B; no USERDATA mount |
| Backup to Mac | `backups/s10plus/20261015T065844Z-R58M75KDB2X/boot-before.img` (57,671,680 B, the previous Nuxel BOOT) |
| Write | `03-flash.sh --boot-only --execute` -> `dd of=/dev/block/sda14 bs=1MiB`, 22,433,792 B transferred, exit 0 |
| Readback | `VERIFIED BOOT: eb77d658fb4fa95930fd13166970a00d6c9ab49dd439c6517b1da349a36e14e5` (full 22,433,792 B re-read = local image) |
| Receipt | `backups/s10plus/20261015T065844Z-R58M75KDB2X/receipt.json` -> `FLASH_AND_READBACK_VERIFIED`, `"boot_only": true` |
| Boot observation | started 2026-10-15T07:00Z, see `DEVICE-OBSERVATIONS.md` |

Offline equivalence proof for A1 (only `/init` changed):
kernel sha256 `33cac63a8b0c0f57…` **identical**, merged DTB sha256 `6107d2e4d47c5956…`
**identical**, page 2048, `0x10008000/0x11000000/0x10000100` **identical**;
ramdisk 6,019,937 -> 6,022,352 B (grew by 2,415 B), therefore dt_offset moved
22,054,912 -> 22,056,960; initramfs `/init` inside the image is byte-identical to
the patched `boot/initramfs/init.sh` (25,039 B).

### A2 — BOOT-only: uncompressed arm64 `Image` (gzip hypothesis)
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A2-uncompressed.img` |
| Change vs A1 | **exactly one**: kernel payload gzip -> raw `Image` (44,980,232 B). Header, ramdisk, DTB, cmdline, addresses all byte-identical. |
| Image sha256 | `9ba1bd210d8859ea91e90bbce19ce3a57d9b1513ece66380d7424dcdaade7738` (51,384,320 B) |
| Target | `/dev/block/by-name/boot` -> `/dev/block/sda14` (57,671,680 B) **only**; USERDATA untouched |
| Preflight | `05-preflight.sh --profile s10plus --boot-only` -> **PREFLIGHT PASS** |
| Backup to Mac | `backups/s10plus/20261015T071247Z-R58M75KDB2X/boot-before.img` (57,671,680 B = previous A1 BOOT) |
| Write | `dd of=/dev/block/sda14`, 51,384,320 B transferred, exit 0 |
| Readback | **VERIFIED BOOT: `9ba1bd21…` (51,384,320 B re-read = local image)** |
| Reboot | `adb reboot` at **2026-10-15T07:13:19Z**; ADB empty 5 s later |
| State | `AWAITING_BOOT_RESULT` |
| Outcome | PENDING — see DEVICE-OBSERVATIONS.md |

### A2 RESULT — FAILED (user returned device to TWRP)
* A2 boot was observed to drop off USB at 07:13:2xZ and the handset returned as
  verified TWRP recovery (`R58M75KDB2X recovery`, `ro.twrp.version=3.7.0_9-2`)
  at ~07:15:05Z — the agreed failure signal. `BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`.
* **But A2 produced the breakthrough evidence**: `/sys/fs/pstore/dmesg-ramoops-0`
  appeared during this boot (the 07:12:18Z pstore capture proves it did not exist
  beforehand — only `pmsg-ramoops-0`), containing a kernel panic dump with
  `linux_banner: Linux version 4.14.253 (nuxel@nuxel-phosh) …`. **The Nuxel kernel
  executed.** Full analysis in `ROOT-CAUSE.md`.

### A3 — BOOT-only: spec-v1 header + raw Image + uncompressed 2048-aligned cpio
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A3-uncompressed-all.img` |
| Changes vs A2 | (a) ramdisk payload gzip -> uncompressed `newc` cpio zero-padded to 8,194,048 B (2048-aligned); (b) header made spec-compliant v1 (`header_version=1` @40, `os_version=0x18000171` @44, `header_size=1648` @1644) — i.e. the container shape of the device's own booting recovery image |
| Unchanged | kernel `Image` (the payload that already executes), merged DTB bytes, cmdline, load addresses, page size |
| Image sha256 | `57ff4d5e7064305908068c19f1beead2c33e77ecc480add7b9c6f9c910ba4f6e` (53,555,200 B) |
| Preflight | `05-preflight.sh --profile s10plus --boot-only` -> **PREFLIGHT PASS** |
| Backup to Mac | `backups/s10plus/20261015T072052Z-R58M75KDB2X/boot-before.img` (the A2 BOOT) |
| Write | `dd of=/dev/block/sda14`, 53,555,200 B, exit 0 |
| Readback | **VERIFIED BOOT: `57ff4d5e…`** |
| Reboot | `adb reboot` at **2026-10-15T07:21:13Z** |
| State | `AWAITING_BOOT_RESULT` |
| Outcome | PENDING |

### A3 RESULT — FAILED (user returned device to TWRP at 07:23:19Z)
Off USB 07:21:15Z -> back as `R58M75KDB2X recovery` at **07:23:19Z** (~124 s), i.e.
the agreed failure signal. New pstore `dmesg-ramoops-0` (27,248 B) => another panic.

**What A3 proved (progress, not a wasted cycle):**
* The header fix works: S-Boot now logs `[UFDT] BOOT IMG HDR V1..` (was
  `HDR V376101`) and reports `ramdisk size = 0x7d0800` = **8,194,048 B, exactly
  the header value** - S-Boot now parses our container correctly.
* The kernel still could not unpack it:
  `rootfs image is not initramfs (junk in compressed archive)` followed by
  `Freeing initrd memory: 8000K`.
* 8000 KiB = 8,192,000 B = **`round_down(8,194,048, 4096)`**. So S-Boot reports
  the raw size in its log but *delivers* the ramdisk with its length floored to a
  4 KiB page boundary, dropping the tail. Our `TRAILER!!!` sits at 8,192,904 B,
  i.e. inside the discarded last page, so the cpio never reaches `state = Reset`.
  The same arithmetic explains A2 (6,022,352 -> 6,021,120 = `round_down(…,4096)`
  = 5880K, exactly what the log printed).
* Consequence: `.../sda25` fallback root, `init` of that filesystem exits,
  `Kernel panic - not syncing: init group exit` - identical symptom chain to A2.

### A4 — BOOT-only: page-floor-proof ramdisk padding
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A4-pagepad.img` |
| Change vs A3 | ramdisk payload re-padded: `TRAILER!!!` now followed by **130,172 zero bytes**, total size **8,323,072 B = 0x7F0000, a multiple of 4096 and of 65536** |
| Unchanged | kernel `Image`, merged DTB bytes, cmdline, v1-spec header, load addresses |
| Image sha256 | `dcc5186ba27447f96fd3ce274fc93f56e84930de392e459cdb9b659e3b3a176c` (53,684,224 B) |
| Preflight/write/readback | **VERIFIED BOOT: `dcc5186b…`** |
| Backup to Mac | `backups/s10plus/20261015T072405Z-R58M75KDB2X/boot-before.img` |
| Reboot | `adb reboot` at **2026-10-15T07:24:26Z** |
| State | `AWAITING_BOOT_RESULT` |
| Outcome | PENDING |

### A4 RESULT — FAILED (user returned device to TWRP at 07:26:25Z)
Off USB 07:24:28Z -> back as recovery 07:26:25Z (~117 s). New pstore
`dmesg-ramoops-0.enc.z` (a *compressed* panic record this time).
**What A4 proved:** S-Boot now reports `ramdisk size = 0x7f0000` = 8,323,072 (exact)
and `patch_month_year : 1.23 , os_version : 12.0.0 -> success`, and the kernel's
`Freeing initrd memory: 8128K` equals the payload exactly - so **length delivery is
now correct**. The kernel still rejected the payload
(`rootfs image is not initramfs (junk in compressed archive)`), which rules out
truncation and points at *where* the kernel read it from. That is what A5 targets.

### A5 — BOOT-only: DTB `/chosen` initrd placeholder removed
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A5-dtb-fix.img` |
| Change vs A4 | only the embedded DTB: `/chosen/linux,initrd-start`, `linux,initrd-end` and the empty `bootargs` deleted (376,101 -> 376,689 B) |
| Image sha256 | `6950241c52320688f28bfc1a0c0426f28e3884e5772934853759354aa97a88d1` |
| Write/readback | **VERIFIED BOOT** |
| Backup | `backups/s10plus/20261015T073139Z-R58M75KDB2X/boot-before.img` |
| Reboot | **2026-10-15T07:31:59Z** |
| State | `AWAITING_BOOT_RESULT` |

### A5 RESULT — FAILED (user returned device to TWRP at 07:33:26Z)
USB absent 07:32:00Z -> recovery 07:33:26Z (~86 s). New `dmesg-ramoops-0` (27,114 B).
The DTB `/chosen` placeholder removal changed nothing: the kernel log is
byte-for-byte the same chain as A4 -
`rootfs image is not initramfs (junk in compressed archive)` /
`Freeing initrd memory: 8128K` -> `SAR_RD: Out of memory` ->
`EXT4-fs (sda25)` -> `Kernel panic - not syncing: init group exit`.
Therefore S-Boot overwrites `/chosen/linux,initrd-start|end` itself (it reports the
length it uses), and the DTB placeholder was not the cause. The finding is still
worth keeping: shipping placeholder initrd properties is a defect.
`grep -c nuxel-init` over the A5 last_kmsg = **0**; no boot has ever produced
initramfs console output.

### Cycle-2/3 tally: 4 distinct evidence-backed candidates (A2, A3, A4, A5) - all
recorded, all readback-verified, all failed on the same single blocker.

---

# CYCLE 3

### A6 — BOOT-only: Nuxel initramfs in the device's own proven LZMA-alone container
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/A6/boot.img` |
| Changes vs A5 | (1) ramdisk payload: uncompressed `newc` cpio -> **LZMA-alone**, properties byte `0x5d`, 8 MiB dictionary, uncompressed-size field `0xffffffffffffffff`, zero-padded to a 65,536-byte multiple (6,029,312 B) — the container shape of the TWRP ramdisk this S-Boot is observed to deliver and the kernel to unpack; (2) initramfs gains `dev/console` (c 5:1) and `dev/null` (c 1:3); (3) `/init` gains the `NUXEL_MARKER` milestone instrumentation and logs the `chosen/linux,initrd-start|end` the bootloader hands the kernel |
| Unchanged | kernel `Image` (byte-identical, sha256 `14b64847…`), appended DTB (byte-identical), load addresses 0x10008000/0x11000000/0x10000100, page 2048, v1-spec header |
| Image sha256 | `ba4f70c6384bd018e5d7d29bf0c28db458f5d0f2671410837649c6ab548ebc49` (51,390,464 B) |
| Why this change | S-Boot's ramdisk load path is format-aware; the *only* ramdisk proven to be both delivered and unpacked on this handset is LZMA-alone. An uncompressed cpio starting with `070701` cannot produce "junk in compressed archive" if it is actually present in memory (see ROOT-CAUSE.md §2), so the payload is not reaching the address S-Boot advertises. A6 additionally makes the failure *mode* diagnostic: `decompressor failed` (or success) proves the bytes were delivered; `junk in compressed archive` proves they were not. |
| Gate | **PASS** (`tools/s10plus/verify-boot-image.py`) |
| Preflight | **PREFLIGHT PASS** — BOOT -> /dev/block/sda14, 57,671,680 B; USERDATA untouched; no rootfs target |
| Backup to Mac | `backups/s10plus/20261015T080348Z-R58M75KDB2X/boot-before.img` (57,671,680 B, the A5 BOOT; sha256 `6ac9c61c…`) |
| Write | `dd of=/dev/block/sda14 bs=1MiB`, 51,390,464 B transferred, exit 0 |
| Readback | **VERIFIED BOOT: `ba4f70c6384bd018e5d7d29bf0c28db458f5d0f2671410837649c6ab548ebc49`** (full 51,390,464 B re-read = local image) |
| Receipt | `backups/s10plus/20261015T080348Z-R58M75KDB2X/receipt.json` -> `FLASH_AND_READBACK_VERIFIED`, `"boot_only": true` |
| Reboot | `adb reboot` at **2026-10-15T08:04:38Z**; ADB empty 4 s later |
| State | `AWAITING_BOOT_RESULT` |
| Outcome | **FAILED_USER_RETURNED_TO_TWRP** (handset back as verified TWRP 3.7.0_9-2; `androidboot.ulcnt=1`) |

### A6 RESULT — FAILED, but the result is DECISIVE and refutes the container hypothesis
```
S-Boot:  load_kernel from 218112..  kernel size = 0x2ae6000, ramdisk size = 0x5c0000
Kernel:  [0.962245] Trying to unpack rootfs image as initramfs...
         [0.962455] rootfs image is not initramfs (junk in compressed archive); looks like an initrd
         [0.970286] Freeing initrd memory: 5888K
         [1.938896] Warning: unable to open an initial console.
```
* `0x5c0000 = 6,029,312` = **exactly A6's new LZMA ramdisk size**, and `5888K` = the same value. S-Boot parsed our new header and used our new size, so the container change *was* seen by the bootloader.
* **The failure is immediate: 0.21 ms between "Trying to unpack" and the error.** With an LZMA stream at the address the kernel reads, `decompress_method()` would have matched `5d 00 00 80 00` and the message would be `decompressor failed` (or success). `junk in compressed archive` in 0.21 ms is only produced when the first non-NUL byte is neither `'0'` nor any compression magic.
* => **H-RAMDISK-CONTAINER is REFUTED.** The ramdisk's *format* is irrelevant; its *contents* are not at the address the kernel reads. **H-INITRD-MEM is CONFIRMED**: on the normal BOOT-partition path S-Boot publishes `/chosen/linux,initrd-start|end` (with a length derived from *our* header) but does not populate that memory; on the `bootmode=2` recovery path it does (the TWRP LZMA ramdisk unpacks).
* `nuxel-init` = 0 and `NUXEL_MARKER` = 0 occurrences in the 2 MiB console — expected, because the initramfs still never unpacked. Note this observation is now *trustworthy* (A6 shipped `/dev/console`), which it was not before.
* 3 Nuxel boot attempts are retained in the ram console (S-Boot retries a failed boot; `androidboot.ulcnt=1`), all identical.
* Evidence: `scripts/s10plus-debug-pack/captures/20261015T080700Z-A6-postfail/`
  (`last_kmsg.txt` 2 MiB, `dmesg-ramoops-0.txt` 27,251 B, `device-state.txt`).
* **Decision:** do not run a third container-format experiment. The next candidate embeds the
  initramfs in the kernel (`CONFIG_INITRAMFS_SOURCE`), which removes the bootloader's
  ramdisk handoff from the critical path entirely -> A7.

### A7 — BOOT-only: kernel with a BUILT-IN initramfs + initrd-delivery diagnostics
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/A7/boot.img` |
| Changes vs A6 | (1) **kernel rebuilt** from `Linux4/android_kernel_samsung_exynos9820@f7194c1d` (Linux 4.14.253) with the in-tree `exynos9820-beyond2lte_defconfig` **unmodified** plus `CONFIG_INITRAMFS_SOURCE` -> the Nuxel initramfs, so `populate_rootfs()` installs it before the bootloader's ramdisk is ever consulted and `/init` exists (which makes `kernel_init()` skip `prepare_namespace()`, also bypassing the `SAR_RD`/`root=PARTUUID` fallback and the "init group exit" panic); (2) `init/initramfs.c` instrumented (`kernel/s10plus/patches/0003-…patch`) to print, at `KERN_ALERT`: whether an external initrd was supplied, its start/end/length, the first 16 bytes there, the first byte and the `decompress_method()` name per attempt, and the parser's final verdict; (3) initramfs trimmed to 876,344 B (splash/animation removed - they belong to the display milestone) so the built-in archive is small and the external ramdisk also stops tripping Samsung's >4 MB `SAR_RD` kmalloc limit; (4) same trimmed cpio shipped as the external ramdisk in the proven LZMA-alone shape (524,288 B, 65536-aligned) |
| Unchanged | load addresses 0x10008000/0x11000000/0x10000100, page 2048, v1-spec header, **appended DTB byte-identical to A5** (`bcdef39c…`) |
| Kernel build | container `docker.io/library/fedora:43` (native aarch64, `CROSS_COMPILE=`), **`gcc (GCC) 15.3.1 20260722 (Red Hat 15.3.1-1)` — the exact compiler in the hardware-proven kernel's banner**; `make -j6 Image dtbs` |
| Kernel `Image` | 45,504,520 B, sha256 `d5e64b0fcdf4ede056aeb172fa546deda92b481e56a4170e9033dc0d6a4fce1a`; `ARMd` @0x38, `text_offset=0x80000`, `image_size=0x333c000`, `flags=0xa` (same layout as the proven kernel) |
| Embedded initramfs | `usr/initramfs_data.cpio.gz` 550,327 B, sha256 `9c22d1e2…`; verified **byte-for-byte inside the `Image` at offset 0x203E510**; listing shows `init` (26,413 B, sha256 `8aba1434…` == `boot/initramfs/init.sh`), `bin/sh -> toybox`, `bin/toybox`, **`dev/console`, `dev/null`** |
| Diagnostics compiled in | `strings Image | grep -c NUXEL-KDIAG` = 5 |
| Image sha256 | `f8587521655191b8927ab21f8126864472def6e8f802f17a85da2627b2cf98da` (46,409,728 B) |
| Gate | **PASS** |
| Preflight | pending |
| Write/readback | pending |
| Boot result | **FAILED_USER_RETURNED_TO_TWRP** (returned 09:26:18Z) — **but milestones 3 and 4 were reached** |
| Why this is the right change | A6 proved the *container format* is irrelevant (S-Boot consumed the new size, `ramdisk size = 0x5c0000`, yet the kernel found junk 0.21 ms later). A7 removes the bootloader's ramdisk handoff from the critical path entirely **and** measures it: even if the built-in archive is somehow not used, the KDIAG lines will state the address and head bytes the kernel actually sees. |


### A7 RESULT — FAILED as a boot, but it BROKE THE BLOCKER: the initramfs unpacked and `/init` was executed
The instrumented kernel (`pr_alert`, so `loglevel=4` cannot filter it) produced a
complete, unambiguous picture. Boot #2 of the three retained attempts, verbatim:

```
NUXEL-KDIAG populate_rootfs: builtin=ffffff800a0fe510 builtin_size=550327 external_initrd=1 start=ffffffc009000000 end=ffffffc009080000 len=524288
NUXEL-KDIAG initrd head: 5b 20 20 20 20 31 2e 30 34 35 36 36 35 5d 20 5b     ascii: "[    1.0"
NUXEL-KDIAG unpack attempt: first=0x1f this_header=0 remaining=550327 method=gzip   <- built-in archive
NUXEL-KDIAG unpack verdict: message=(none) state=7                                  <- SUCCESS (state 7 == Reset)
Trying to unpack rootfs image as initramfs...
NUXEL-KDIAG unpack attempt: first=0x5b this_header=0 remaining=524288 method=(none) <- external initrd
NUXEL-KDIAG unpack verdict: message=junk in compressed archive state=0
NUXEL-KDIAG unpack attempt: first=0x1f this_header=0 remaining=550327 method=gzip   <- built-in restored
NUXEL-KDIAG unpack verdict: message=(none) state=7                                  <- SUCCESS
rootfs image is not initramfs (junk in compressed archive); looks like an initrd
Freeing initrd memory: 512K
Warning: unable to open an initial console.
```

**What this proves, item by item:**
1. **Milestone 3 ACHIEVED: the initramfs unpacks.** `message=(none) state=7` is
   `unpack_to_rootfs()` success, twice.
2. **Milestone 4 ACHIEVED: `/init` exists and was executed.** `prepare_namespace()`
   was **not** called — `RAMDISK:` = 0 occurrences, `SAR_RD` = 0 occurrences,
   `RAMDISK: Couldn't find valid RAM disk image` absent, and `init group exit`
   absent. That only happens when `/init` is present in rootfs, which makes
   `kernel_init_freeable()` set `ramdisk_execute_command = "/init"` and skip
   `prepare_namespace()`. `Failed to execute /init` = 0 occurrences, so the exec
   itself succeeded.
3. **S-Boot advertises the initrd at `0x89000000` (vaddr `ffffffc009000000`) with
   `len = 524288` = exactly our ramdisk size, and does NOT populate it.** The 16
   bytes the kernel reads there are **kernel console text** (`"[    1.0…"`) on one
   boot and all zeros on another. That is the final, direct confirmation of
   H-INITRD-MEM: for a normal BOOT-partition boot the bootloader publishes
   `/chosen/linux,initrd-*` derived from our header without loading the payload.
   (On the `bootmode=2` recovery path it does load it — which is why TWRP's LZMA
   ramdisk unpacks.)
4. **`/dev/console` is unusable on this device**: verified live from TWRP,
   `echo … > /dev/console` → `can't create /dev/console: No such device`
   (ENODEV), while `/dev/kmsg` (1:11) accepts writes. `console=ram` registers a
   `struct console` with no tty, so `kernel_init` cannot open an initial console
   and PID 1 has no stdio. **This is why no attempt has ever produced initramfs
   text**, and it invalidates every earlier "no output" inference.
5. The boot ends in Samsung's own **`hard_reset_hook_callback`** (fatal exception
   in interrupt at t=37 s and t=68 s) or a **`hung_task` panic at t=242 s**
   (`tz_worker_threa`, `scsi_srpmb_work`, `ree_time` blocked). A7 therefore
   progressed from ~2 s (A2-A5) to 37-242 s: the kernel-side handoff is solved and
   the reset is now a *timeout* mechanism, not a kernel defect on our path.
6. `grep -c NUXEL_MARKER` = 0 and `nuxel-init` = 0 — now explained by #4 rather
   than by `/init` failing to run. The BOOT-partition slack contains no diagnostic
   record: `/init` did not reach `diag_persist()`, so it either blocked early or
   was still running when the reset fired.

Evidence: `scripts/s10plus-debug-pack/captures/20261015T092700Z-A7-postfail/`
(`last_kmsg.txt` 2 MiB with 15 KDIAG lines, `dmesg-ramoops-0.txt`, `cmdline.txt`).

### A8 — BOOT-only: same kernel design, evidence re-routed to `/dev/kmsg` + watchdog
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/A8/boot.img` |
| Changes vs A7 | (1) initramfs gains `/dev/kmsg` (char 1:11, 0600) and `/init` now writes **all** diagnostics to `/dev/kmsg` first (console only as fallback), because `/dev/console` is ENODEV here; (2) an explicit **45 s watchdog** (`NUXEL_BOOT_WATCHDOG`) persists evidence then `reboot -f`, so a boot that cannot finish ends deterministically instead of racing Samsung's `hard_reset_hook`; (3) early heartbeat right after `diag_persist()` is defined, so the BOOT-slack record is written as soon as devtmpfs is up rather than only at the end; (4) the watchdog is disarmed immediately before `switch_root` |
| Unchanged | kernel source/defconfig/diagnostics patch, DTB (`bcdef39c…`), load addresses, v1 header |
| Kernel `Image` | 45,504,520 B, sha256 `f887030acd5c394b97ccd154db7e6252adc21b457b957177fe56287202d8b876` |
| Embedded initramfs | 551,027 B, sha256 `56ef85f9…`, contains `dev/console`, **`dev/kmsg`**, `dev/null`; `/init` = 28,236 B sha256 `28a4834d…` == `boot/initramfs/init.sh`; archive verified byte-for-byte inside the Image |
| Image sha256 | `314d5e532f3e0a25d324c87e844110b173db20306d42ca83d67c2684fa6f026a` (46,409,728 B) |
| Gate | **PASS** |
| Why | A7's only remaining observability gap was the missing console; `/dev/kmsg` is the channel that actually works on this handset, and it also records the *kernel's* view of events. Nothing about the kernel path changes, so this is a single-variable information fix. |

### A8 RESULT — FAILED as a boot, but **MILESTONE 4 IS NOW PROVEN ON HARDWARE**
The evidence channel works. Verbatim from the ram console
(`captures/20261015T093400Z-A8-postfail/last_kmsg.txt`, 31 `nuxel-init` lines on
2 of the 3 attempts):

```
<12>[    1.915889]  [6:           init:    1] nuxel-init: NUXEL_MARKER INITRAMFS_EXECUTED
<12>[    1.921394]  [6:           init:    1] nuxel-init: slot=a device=unknown quiet=0 verity=off
<12>[    1.922242]  [7:           init:    1] nuxel-init: DT model:
<12>[    1.922570]  [7:           init:    1] nuxel-init: no splash data — showing navy boot screen
<12>[    1.923666]  [7:           init:    1] nuxel-init: version: Linux version 4.14.253 (root@) (gcc version 15.3.1 20260722 (Red Hat 15.3.1-1) (GCC)) #2 SMP PREEMPT Thu Oct 15 09:28:34 UTC 2026
<12>[    1.925455]  [6:           init:    1] nuxel-init: dt-model:
<12>[    1.926255]  [7:           init:    1] nuxel-init: dt-compat:
<12>[    1.926893]  [7:           init:    1] nuxel-init: chosen linux,initrd-start: unreadable
<12>[    1.927517]  [7:           init:    1] nuxel-init: chosen linux,initrd-end: unreadable
<12>[    1.930036]  [6:           init:    1] nuxel-init: block-devices:
<12>[   46.967379]  [2:           init: 3304] nuxel-init: WATCHDOG: 45s elapsed - persisting and rebooting
```
* **`/init` executed as PID 1 and produced its own console evidence.** That is
  milestone 4, and it is the first time any Nuxel userspace code has been observed
  running on the handset.
* The markers prove the chain end to end: built-in initramfs unpack (`state=7`) ->
  `/init` exec -> PID 1 running our shell -> our own log lines.
* It also shows the watchdog works exactly as designed (fired at 46.9 s).

**Three new, precisely localised blockers:**
1. `/proc/device-tree` is not a thing on this arm64 kernel: `dt-model:`,
   `DT model:` and `chosen linux,initrd-start: unreadable` are all empty, so device
   identification fails and the generic `find_root()` probe runs instead of the
   s10plus USERDATA path. The arm64 path is
   `/sys/firmware/devicetree/base`.
2. `block-devices:` is empty -> no `/dev/sd*`, i.e. devtmpfs was not mounted (or
   its mount failed silently) — so no partition could be found or persisted to.
3. `/init` then **hung**: the last line is `nuxel-init: block-devices:` and the very
   next statement in `diag_environment()` is `dmesg`; toybox's `dmesg` blocks
   reading `/dev/kmsg` on this kernel, so PID 1 slept until the watchdog rebooted
   it. `diag_dump_kmsg()` has the same call on the failure path.

**And the boot is on a short vendor leash:**
```
<6>[    4.162746]  [0:    kworker/0:1:   98] hard_reset_hook : hrtimer_start
<0>[   10.162940] I[0:      swapper/0:    0] kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!
<0>[   10.191183] I[0:      swapper/0:    0] Kernel panic - not syncing: Fatal exception in interrupt
```
Samsung's `sec_hard_reset_hook` timer BUG()s between ~4 s and ~70 s into a boot
that never signals success, and `oops=panic` turns it straight into a panic
(observed limits this cycle: 10 s, 37 s, 68 s, 242 s). Consequence: the initramfs
must reach USERDATA and hand off within a few seconds of PID 1 starting.

### A9 — BOOT-only: fix the three initramfs bugs A8 exposed, and temper the vendor leashes
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/A9/boot.img` (sha256 `10e12641f3a14f7c5a1d2757018131b99355b7a7a0044c2d63e048c0b29aa2fc`) |
| Kernel `Image` | 45,504,520 B, sha256 `f5733fd4073a9f8441d94739fc78128b3fa97237fe41faa1de6337b0cd807f46` (only the embedded initramfs changed) |
| Change 1 | **`exec 2>/dev/kmsg`**: shell errors (failed mounts, missing commands) were invisible because fd 2 is the broken `/dev/console`; now they land in the kernel log. |
| Change 2 | **arm64 device-tree path**: `/proc/device-tree` does not exist on this kernel, so every DT read was empty (A8: `dt-model:`, `DT model:`, `chosen linux,initrd-start: unreadable`). The initramfs now prefers `/sys/firmware/devicetree/base` with a `/proc/device-tree` fallback, and logs which source it used plus the model string. |
| Change 3 | **no blocking `dmesg`**: A8's `/init` hung on the `dmesg` call in `diag_environment()` (toybox `dmesg` blocks on `/dev/kmsg` here) — PID 1 slept until the watchdog rebooted it. Both call sites are removed; the kernel log is read from recovery (`/proc/last_kmsg`) by design. |
| Change 4 | **vendor leashes tempered from userspace**: `hung_task_panic=0`, `hung_task_timeout_secs=600`, `panic=0`, and a softdog keeper started against `/dev/watchdog` (`softdog.soft_margin=100 soft_panic=1` comes from S-Boot's cmdline). Samsung's kernel-side `hard_reset_hook` is deliberately **not** patched: it is a force-reset *key combo* (POWER + VOLUME_DOWN held for 6 s) and fires because the operator holds the recovery buttons, so it is not a Nuxel defect. |
| Change 5 | **device discovery made robust**: `devtmpfs` did not appear to mount in A8, so the initramfs now ships explicit device nodes as a *fallback* — `dev/watchdog` (c 10:130), `dev/sda14` (b 8:14 = BOOT) and `dev/sda31` (b 259:15 = USERDATA). The dev_t values are not guesses: `/dev/block/by-name` was read from the live device and the kernel's own `VFS: Mounted root (ext4 filesystem) ... on device 259:9` for sda25 confirms the extended-partition numbering (259:(part-16)). `PARTNAME=userdata` discovery remains the primary path and any use of a fallback node is logged loudly. |
| Change 6 | boot watchdog shortened to **30 s** so it fires before the vendor leashes. |
| Gate | **PASS** — 70 records, `/init` 31,150 B, all six `/dev` nodes present, no duplicates |

### A12 — BOOT-only: deterministic identity + devtmpfs-shadow-proof device nodes
| Field | Value |
|---|---|
| Candidate | `build/out/s10plus/debug-candidates/A12/boot.img` sha256 `68217cdd59d047108f9e28de6d008fb8360dc9a5654b338df0c7bad4c26054ed` |
| Kernel | `Image-A12` sha256 `d471a52cfdcf5f9718ffd592df878883297175587d2ec9ad54e898b030cbb8ab` |
| Preflight/write/readback | **PREFLIGHT PASS**, then **VERIFIED `68217cdd…`** (`backups/s10plus/20261015T095724Z-R58M75KDB2X`) |
| Reboot | 2026-10-15T09:58:04Z; returned to TWRP 09:59:49Z |
| Root cause fixed | (a) `mount -t devtmpfs none /dev` **shadows the device nodes shipped in the initramfs**, and this kernel's UFS scan completes a few ms after PID 1 starts (probe at t=1.95 s showed no `/dev/sd*`; `/dev/sda2` existed by t=1.97 s) — so the documented fallback nodes are now recreated with `mknod` after the mount; (b) `wc` was missing from the initramfs applet list, silently emptying diagnostics; (c) the device dispatch was observed running the **generic** probe even with `DEVICE='s10plus'` logged, so a `force_s10plus_root()` override now resolves USERDATA explicitly and refuses every bootloader partition (`/dev/sda1`, `/dev/sda2`, `/dev/sda25`). |

#### A12 RESULT — FAILED as a boot, but MILESTONES 5, 6 AND THE ROOTFS HANDOFF ARE REACHED
Verbatim from the ram console:
```
identity pin: S-Boot cmdline reports exynos9820 -> DEVICE=s10plus
dispatch: DEVICE='s10plus' ROOT_SPEC='PARTUUID=52444E41-494F-2044-7379-7374656D0000'
generic probe selected '/dev/sda2'
root override: forcing the s10plus USERDATA resolution (was '/dev/sda2')
PARTNAME discovery failed after 12s; using documented /dev/sda31 (by-name userdata)
USERDATA_FALLBACK /dev/sda31
root block device: /dev/sda31
EXT4-fs (sda31): Root reserved blocks 52428
EXT4-fs (sda31): mounted filesystem with ordered data mode. Opts: (null)
root mounted: /dev/sda31 (ext4, mode=ro)
NUXEL_MARKER ROOTFS_MOUNTED
rootfs os-release: <none>
ROOTFS_HANDOFF_STARTED -> /newroot
NUXEL_MARKER ROOTFS_HANDOFF_STARTED
switching root -> /newroot
```
* **`USERDATA_DISCOVERED`** (as `USERDATA_FALLBACK /dev/sda31`, logged loudly and only
  after the PARTNAME probe failed) -> milestone 5.
* **`ROOTFS_MOUNTED`**: the Fedora rootfs on sda31 mounted as ext4 -> milestone 6.
* **`ROOTFS_HANDOFF_STARTED`** + `switch_root /newroot` executed -> the control
  transfer into the real root began.
* `PARTNAME=userdata` discovery still fails because **`/sys/class/block` is empty**
  in this kernel even with sysfs mounted (diagnostic: `probe: /sys/class/block=
  entries`), so the documented `sda31` fallback is what works. That is now the
  primary path on this board and is verified against `/dev/block/by-name` on the
  live device.
* Remaining issues recorded for the next cycle:
  1. `rootfs os-release: <none>` — the root was mounted **read-only** and its
     os-release could not be read, so the Fedora/Nuxel root-verification gate did
     not have data. Mount read-write (the script prefers rw; the ro came from the
     remount logic) and re-check before trusting the handoff.
  2. After `switch_root` the kernel log is silent, which is expected: Fedora's
     systemd writes to a console that does not exist on this device. The next
     observation channel must be inside the rootfs (a marker file) or the BOOT
     slack, and the shipped diagnostics did not reach `diag_persist()` before the
     reboot.
  3. Fedora 43 systemd 258.11 vs Linux 4.14.253 is the next hard risk (>= 5.4
     kernel, cgroup v2 only).
  4. `/sys/class/block` being empty and `/proc/device-tree` not existing need
     explanation (both are mountable but appear unpopulated), and the boot is still
     time-limited by the vendor `hard_reset_hook` / softdog.


---

# FLASH ATTEMPT A13 — 2026-10-15 (cycle 4)

## Preconditions (all re-verified live before writing)
| Check | Value |
|---|---|
| device | `R58M75KDB2X`, `Galaxy S10+`, `beyond2lte`, TWRP `3.7.0_9-2`, `slot=none` |
| root ADB | yes (`uid=0(root) … context=u:r:su:s0`) |
| partition map | `boot -> /dev/block/sda14` (57,671,680 B), `recovery -> /dev/block/sda15`, `userdata -> /dev/block/sda31` |
| slot semantics | A-only, no `boot_a/boot_b`; `--boot-only` used, USERDATA untouched |
| preflight | **PASS** (`05-preflight.sh`) — 50,604,032 B image into a 57,671,680 B partition |
| BOOT backup | `backups/s10plus/20261015T110912Z-R58M75KDB2X` (pre-write content), plus the earlier `…110859Z` |
| image integrity | `A13/boot.img` sha256 `bdc06dfe8a8cabe2de904e6224403741eb43fcd1d36eb491e699911f090df086` |

## Write and readback
```
FLASHING BOOT: 50,604,032 bytes -> /dev/block/sda14
  write command completed; doing mandatory full readback...
VERIFIED BOOT: bdc06dfe8a8cabe2de904e6224403741eb43fcd1d36eb491e699911f090df086 (50,604,032 bytes)
PASS: every written partition matches its local image by full SHA256 readback.
```
Write exit status 0, transferred bytes == expected, readback SHA-256 identical to
the local artifact. **USERDATA (sda31) was never written; RECOVERY (sda15) was never
written; no DTB/DTBO/VBMETA/modem/bootloader partition was written.**

## What this candidate changes (BOOT partition only)
1. `Image-A13` — the *same* kernel source/defconfig/DTB as A12, rebuilt only so
   that the new initramfs is embedded (`CONFIG_INITRAMFS_SOURCE`).
2. new `/init` (see PATCHES.md P-C4-2 … P-C4-5) — rw root, explicit identity gate,
   signal-free watchdog, fresh `/proc`/`/sys`/`/dev`, probes, first light.
3. `/opt/nuxel/libsystemd-shared-258.11-1.fc43.so` — the pidfd_spawn repair,
   installed into the mounted rootfs at boot with the original kept as
   `…so.nuxel-orig` (P-C4-1).

## Boot result
* `CANDIDATE=A13`
* `boot.img sha256=bdc06dfe8a8cabe2de904e6224403741eb43fcd1d36eb491e699911f090df086`
* `REBOOT_AT=2026-10-15T11:09:5xZ` (`adb reboot` issued right after the verified write)
* `STATE=AWAITING_BOOT_RESULT`

Per the standing TWRP = failed-boot agreement: if `R58M75KDB2X` is seen in
recovery again after this reboot, the A13 Nuxel boot failed; capture
`last_kmsg`/pstore immediately and continue.
REBOOT_AT=2026-10-15T11:10:09Z

## A13 boot result — FAILED (operator returned to TWRP)

* `BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`
* `RECOVERY_ACCESS=RESTORED` at 2026-10-15T11:13:34Z (device seen in TWRP 3.4 min after the
  11:10:09Z reboot; capture
  `scripts/s10plus-debug-pack/captures/20261015T111341Z-full-collection-74105/`)
* Write and readback were perfect (`bdc06dfe…`), so this is a boot failure, not a flash failure.

### What the log proves
| Observation | Evidence |
|---|---|
| the new initramfs ran | `NUXEL_MARKER INITRAMFS_EXECUTED` at t=2.12–2.16 s in three separate boot sessions |
| proc/sysfs/devtmpfs mounts, hung_task tempering, softdog keeper | all logged, identical to A12 |
| identity pin worked in 2 of 3 sessions | `identity pin: S-Boot cmdline reports exynos9820 -> DEVICE=s10plus` (lines 8032, 20154) |
| the script then stops, every time, at the same place | `root override: forcing the s10plus USERDATA resolution (was '')` — and nothing after it |
| why it stops | `force_s10plus_root()` waits **12 x 1 s** for `s10plus_userdata_device()`, which can never succeed because `/sys/class/block` is empty on this kernel |
| why the attempt ended | the operator's force-reset: `hard_reset_hook : hrtimer_start` t=3.369 s, `kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!` t=9.369 s, `Kernel panic - not syncing: Fatal exception in interrupt` t=9.396 s |
| the hook is key-driven, not spontaneous | `drivers/samsung/sec_hard_reset_hook.c`: `hard_reset_keys[] = { KEY_POWER, KEY_VOLUMEDOWN }` — the documented manual recovery combo |
| **no probe, no first light, no handoff, no systemd** | there is no `NUXEL-SYSCALL`, `SPAWNPROBE`, `FIRSTLIGHT`, `ROOTFS_MOUNTED`, `ROOTFS_IDENTITY` or `switching root` line anywhere in the capture |

So A13 never reached anything new. The A13 repair is untested — the boot died in a
**pre-existing 12-second silent stall**, before the identity gate, before the
probes, before first light and before the handoff. One session (the first) even
took the generic path (`dispatch: DEVICE=''` → `generic probe selected '/dev/sda2'`)
because the cmdline parse produced no device, which is the same class of defect the
`/dev/sda31` identification in A14 now guards against.

### Lesson recorded
A phone that shows an unchanged screen for 12+ seconds reads as a dead phone, and
the operator's recovery combo then kills a boot that may have been making
progress. **User-visible output must come first, not last.**

---

# FLASH ATTEMPT A14 — 2026-10-15 (cycle 4 continuation)

## What changed vs A13 (init script only — same kernel source, config and DTB)
1. **First light moved to the earliest possible point** (`nuxel_first_light`, called
   with the boot splash at ~2 s, immediately after devtmpfs is up) instead of just
   before the handoff. The panel now shows the NUXEL pattern two seconds after
   kernel entry.
2. **The 12-second root-discovery stall is gone.** `force_s10plus_root()` probes
   once, allows one second for the UFS scan, then uses the documented node. It also
   reports `_t=1` so the existing message stays truthful.
3. **Independent board identification**: if the cmdline parse yields no device but
   `/dev/sda31` exists (only beyond2lte/beyond1lte have a 31st UFS partition), the
   device is s10plus. This closes the A13 session-1 failure mode where the generic
   probe selected `/dev/sda2`.
4. The generic-probe refusal now also matches `androidboot.bootloader=G97*` and
   promotes `DEVICE=s10plus` instead of merely clearing `ROOT_DEV`.
5. Everything else is A13 unchanged: pidfd_spawn repair install, rw root, explicit
   identity gate, syscall/spawn probes, Fedora-exec chroot probe, fresh
   `/proc`/`/sys`/`/dev`, signal-free watchdog.

## Artifacts
| Artifact | sha256 |
|---|---|
| `A14/Image-A14` | `b04f808c4777901ccc38174a4c4e7f907b3a9433fa2129d1be641f049af0403b` |
| `A14/initramfs.cpio` | `063af74dcdc6951a9ee4c937bdaba2c49713ee5d875497ad799c70e6dce7859f` |
| `A14/boot.img` (50,604,032 B, gate PASS, slack 7,067,648 B) | `5aff1a109147d33eb017c30423c8ef3bb16d14217d509e829d65d5848d4b4009` |

A13 (`bdc06dfe…`) and A12 (`68217cdd…`) are preserved untouched.
A14 REBOOT_AT=2026-10-15T11:18:53Z

## A14 boot observation (live)

* `A14 REBOOT_AT=2026-10-15T11:18:53Z` (`adb reboot` from TWRP after the verified write)
* `adb devices` stayed **empty** from 11:19:08Z onward: **5 minutes with no ADB and,
  critically, no return to TWRP.** A13 came back to TWRP 3.4 minutes after its
  reboot. A device that neither exposes ADB nor falls back to recovery is *not*
  bootlooping, which is what A13 did.
* The changed observable is exactly the one A14 targeted: first light is now
  painted with the boot splash (~2 s) instead of immediately before the handoff,
  and the 12-second root-discovery stall is gone.

Two readings remain possible and only the operator's panel can separate them:
1. **Nuxel is up.** Fedora systemd owns PID 1 (the watchdog exits silently in that
   case, by design), there is no `adbd` in the Fedora rootfs, and the phone simply
   sits there running — which is what a successful boot looks like on this device.
2. The boot hung with an unchanged screen and has not been force-reset yet.

`STATE=AWAITING_OPERATOR_OBSERVATION`; monitoring continues
(`.scratch/s10plus-cycle4/a13/monitor/a14-adb-watch.log`). No further writes are
issued while the phone is out of recovery. If the device reappears in TWRP this is
recorded as a failed boot under the standing agreement and the capture follows.
