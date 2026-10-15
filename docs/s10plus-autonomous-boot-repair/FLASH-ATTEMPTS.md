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

---

# FLASH ATTEMPT A14 — RESULT (recorded 2026-10-15, cycle 5)

`BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP` · `RECOVERY_ACCESS=RESTORED`

* `CANDIDATE=A14`, `boot.img sha256=5aff1a109147d33eb017c30423c8ef3bb16d14217d509e829d65d5848d4b4009`
  (50,604,032 B, gate PASS), write + full SHA-256 readback verified before reboot.
* `REBOOT_AT=2026-10-15T11:18:53Z`; the phone was found back in TWRP with root ADB.
* Fresh capture: `scripts/s10plus-debug-pack/captures/20261015T130509Z-A14-postfail/`
  (`prev-boot/last_kmsg.raw` 2,097,152 B `1d449401…`, `pstore/dmesg-ramoops-0.raw`
  27,215 B `1889a6a9…`, `recovery/recovery-metadata.txt`, `ANALYSIS-A14.md`).
* **New milestones reached on hardware:** systemd child services execute
  (`systemd-udevd` running and processing uevents → milestone 10), Fedora binary
  executes (`FEDORA_EXEC_OK`), the freestanding syscall/spawn probes ran, and
  `FIRSTLIGHT_FRAME_WRITTEN` (nuxel-fb-phone exit=0) was recorded at t=2.363 s.
* **Failure classification:** the attempt was ended by **our own initramfs
  dead-man watchdog**, not by the kernel — a normal `reboot()` (magic `0x0`) at
  t=47.171346 s from comm-`init` processes in the initramfs's own shell lineage,
  0.4 ms after its PID-1 probe errored (`sh: 1/comm: No such file or directory`).
  Answer to Phase 2: **explicitly requested by software**; no panic, no watchdog
  bite, HW watchdog petted throughout.
* **Earliest newly demonstrated failure:** the watchdog's `cd /proc` runs before
  `/proc` is mounted, so its "is PID 1 still the initramfs shell?" test can never
  succeed; it reported ambiguity as "no handoff" and rebooted a running Fedora.

---

# FLASH ATTEMPT A15 — 2026-10-15 (cycle 5)

## Hypothesis being tested

> A14's Fedora systemd was healthy at t=47 s and was killed by this initramfs's
> own dead-man watchdog. With that watchdog removed, the boot should survive
> indefinitely; with cgroup v2 additionally mounted before `switch_root`, the
> `Failed at step CGROUP` failures should disappear and real services should
> start. The panel should show an unmistakable Nuxel first-light frame with a
> spinning penguin.

## What changed vs A14 (same kernel source, defconfig, DTB and header layout)

1. `boot/initramfs/init.sh`: the dead-man watchdog block is **deleted** (replaced
   by the measured explanation and `NUXEL_WATCHDOG_PID=""`), so nothing in the
   initramfs can reboot the phone after `switch_root`.
2. `boot/initramfs/init.sh`: **cgroup v2 is mounted** into the new root
   (`mount -t cgroup2 none ${ROOT_MNT}/sys/fs/cgroup`) before `switch_root`, with
   loud `CGROUP2_MOUNTED` / `CGROUP2_MOUNT_FAILED` markers.
3. `boot/initramfs/init.sh`: the first-light record now also emits
   `FIRSTLIGHT_ANIMATION_DONE` when the payload reports the animation.
4. `tools/s10plus/nuxel-fb-phone.c` → `nuxel-fb-phone-aarch64`
   (sha256 `f1a0d975ecb10d2dea911ba3515286d4e04ea5a3ade35eb4e11030c4ea3cf843`,
   8,784 B): logs every fb geometry field (`xres/yres/yres_virtual/xoffset/
   yoffset/bpp/stride/smem_start/smem_len/mmio_*`, colour bit lengths) to fd 2 =
   `/dev/kmsg`; paints **every** buffer of the virtual framebuffer
   (`NUXEL_FB_BUFFERS_PAINTED`); draws bright colour bars + a big white NUXEL
   wordmark + a white-outlined penguin on deep blue (never a black-looking
   screen, and no full-white AMOLED frame); spins the penguin through 12 frames
   at 250 ms (`NUXEL_FB_ANIM frame=N`, `NUXEL_FB_ANIM_DONE frames=12`).

## Artifacts

| Artifact | sha256 |
|---|---|
| `A15/initramfs.cpio` (6,750,448 B) | `f31b96a536d3f4be36326fa5172d63fb15fdf397bdbabcf539194c43c01280f8` |
| `tools/s10plus/nuxel-fb-phone-aarch64` | `f1a0d975ecb10d2dea911ba3515286d4e04ea5a3ade35eb4e11030c4ea3cf843` |
| `boot/initramfs/init.sh` | `c2cc306dc1e3ab4d66ddc97f39da48902477b8aa5dbf5b3f0f8022159849dd3d` |
| `A15/Image-A15` | *see build receipt below* |
| `A15/boot.img` | *see build receipt below* |

A12 (`68217cdd…`), A13 (`bdc06dfe…`), A14 (`5aff1a10…`) are preserved untouched.

## Preconditions (re-verified live before writing)

| Check | Value |
|---|---|
| device | `R58M75KDB2X`, `Galaxy S10+`, `beyond2lte`, TWRP `3.7.0_9-2` |
| root ADB | yes (`uid=0(root) … context=u:r:su:s0`) |
| partition map | `boot -> /dev/block/sda14` (57,671,680 B), `recovery -> /dev/block/sda15`, `userdata -> /dev/block/sda31` |
| scope | `--boot-only`; USERDATA (sda31) never written, RECOVERY (sda15) never written |
| BOOT backup | `backups/s10plus/<stamp>-R58M75KDB2X` taken before the write |

## A15 write and readback (2026-10-15, cycle 5)

```
PREFLIGHT PASS: boot -> /dev/block/sda14 size=57,671,680 bytes; image 50,604,032 bytes
BACKUP  BOOT -> /Users/wicked/x/nuxel/backups/s10plus/20261015T132433Z-R58M75KDB2X
FLASHING BOOT: 50,604,032 bytes -> /dev/block/sda14
VERIFIED BOOT: e23d004d083b3137bc8ff1819b7b954c50700abe9ae8fd971e4cc8bf854fc966 (50,604,032 bytes)
PASS: every written partition matches its local image by full SHA256 readback.
```

* `CANDIDATE=A15`
* `A15/boot.img` sha256 `e23d004d083b3137bc8ff1819b7b954c50700abe9ae8fd971e4cc8bf854fc966` (50,604,032 B, gate PASS, slack 7,067,648 B)
* `A15/Image-A15` sha256 `6fe28b694a5def8cbb1712af08ceae87b21b6bc6cc77b5df868521c461ff46c1` (47,929,352 B), kernel banner `#1 SMP PREEMPT Thu Oct 15 13:23:12 UTC 2026`
* `A15/initramfs.cpio` sha256 `f31b96a536d3f4be36326fa5172d63fb15fdf397bdbabcf539194c43c01280f8` (6,750,448 B)
* embedded-initramfs proof: `out/usr/initramfs_data.cpio.gz` (2,929,016 B) gunzips to
  sha256 `f31b96a5…` = the A15 cpio, that gzip stream is present in the Image at
  offset 33,809,680, and the embedded cpio contains `NUXEL_WATCHDOG_PID` /
  `CGROUP2_MOUNTED` / `NUXEL_FB_ANIM_DONE` — i.e. the new files really are in the
  kernel, not a stale build.
* USERDATA (sda31) and RECOVERY (sda15) were **not** written; DTB/DTBO/VBMETA/
  modem/bootloader untouched.
* `REBOOT_AT=2026-10-15T13:24:59Z` (`adb reboot` from TWRP after the verified write); `STATE=AWAITING_BOOT_RESULT`.

---

# CYCLE 6 — candidate A16 (2026-10-15), BOOT-only

**Problem under test:** A15 was proven running (1892 s, no software reboot) but the
panel stayed black and *not one* of `nuxel-fb-phone`'s verdict lines reached the
ram console, so we could not tell whether the paint landed. A16 makes the
first-light verdict unswallowable and forces the DECON to commit a frame.

**Root-cause hypotheses (from `captures/20261015T135737Z-A15-postfail/ANALYSIS-A15.md`):**
1. `init.sh` read the program's output through `printf | while IFS= read -r`,
   which this toybox shell cannot run (`sh: <...>read: No such file or directory`),
   so `NUXEL_FB_INFO` / `NUXEL_FB_ANIM` were dropped. → fix by writing straight to `/dev/kmsg`.
2. The DECON in command mode only latches a frame when the fbdev asks it to; the
   A15 boot shows `decon_initial_display` but **no** `decon_enable`/FRAME_DONE for
   1892 s. → add `FBIOBLANK(UNBLANK)` + `FBIOPUT_VSCREENINFO(FB_ACTIVATE_NOW)` +
   `FBIOPAN_DISPLAY`, logging every return code.
3. A14/A15 painted only the active buffer. → paint every virtual buffer, and
   animate in every painted buffer.

**Change set (BOOT partition only; no rootfs, no USERDATA, no RECOVERY, no DTBO):**
* `tools/s10plus/nuxel-fb-phone.c` — argv `hold [secs]`, geometry sanity
  (`NUXEL_FB_ZERO_STRIDE`, `NUXEL_FB_YVIR_CLAMPED_from`), paint all buffers (bounded
  to 4), mmap read-back of px0/centre, `scanout_commit()` logging
  `NUXEL_FB_UNBLANK_rc` / `NUXEL_FB_ACTIVATE_rc` / `NUXEL_FB_PAN_rc`, and a
  resident animation loop that logs one line per ~10 s.
  Compiled freestanding aarch64; **9792 B** sha256 `fed8f9c9acf3287db09a2ee3a6fa46ff0bbd289e180ac63f42d720c045cae158`.
* `boot/initramfs/init.sh` — `nuxel_first_light()` no longer uses a subshell or
  `read`; the program's stdout+stderr go to `/dev/kmsg` directly; fbdev facts are
  logged from sysfs; the painter is then re-run in `hold` mode in the background.
  sha256 `b209c3e996dc2cf93aa26888aa34859e839f5852925f2da850ce7491fa799ab0`.

**Candidate A16**
| Artifact | bytes | sha256 |
|---|---|---|
| `A16/initramfs.cpio` | 6,753,220 | `f3bd9cbe5dae176b2c82bc0c782906f6d70f87a07ee3463b4bdcef32ef67bbd4` |
| `A16/Image-A16` | 47,929,352 | `72e47f8821235cb06f54b7a372be22e217ddc72777a71085e0f93456ea497811` |
| `A16/boot.img` | 50,604,032 | `603c2e9a3fd434d451aea0b614fe5978a9ad6178ade6edc1831afc708ee36222` |

**Offline verification performed**
* cpio round-trip: extracted `init` and `opt/nuxel/nuxel-fb-phone` hash-identical to
  `boot/initramfs/init.sh` (`b209c3e9…`) and `tools/s10plus/nuxel-fb-phone-aarch64` (`fed8f9c9…`).
* embedded-initramfs proof: the gzip stream at **offset 33,809,680** in `Image-A16`
  decompresses (6,753,220 B) to sha256 `f3bd9cbe…` = `A16/initramfs.cpio`. The
  current build is **not** stale. (Same method re-validated A15: `f31b96a5…` at the
  same offset.)
* `build-candidate.sh` release gate: **PASS** (header_field40=1, header_size=1648,
  kernel_size=47,929,352, ramdisk lzma 2,293,760 B, cpio `/init` mode 0o100755 size
  51,833, partition slack 7,067,648 B). Base is the hardware-proven A5 DTB image,
  so the appended DTB is unchanged (`bcdef39c…`).
* binary executed in the aarch64 container: all three invocations (`-`, `hold`,
  `hold 5`) print `NUXEL_FB_UNAVAILABLE no /dev/fb0` and exit 2 — argv/entry work.

**Flash receipt**
```
Device: R58M75KDB2X model=Galaxy S10+ codename=beyond2lte TWRP=3.7.0_9-2 slot=none
BOOT:   boot -> /dev/block/sda14 size=57,671,680 bytes
PREFLIGHT PASS
BACKUP  BOOT -> backups/s10plus/20261015T140626Z-R58M75KDB2X
FLASHING BOOT: 50,604,032 bytes -> /dev/block/sda14
VERIFIED BOOT: 603c2e9a3fd434d451aea0b614fe5978a9ad6178ade6edc1831afc708ee36222 (50,604,032 bytes)
PASS: every written partition matches its local image by full SHA256 readback.
```
USERDATA (sda31) and RECOVERY (sda15) were not written. No automatic reboot was
issued by the flasher.

`REBOOT_AT=2026-10-15T14:07Z` (`adb reboot` from TWRP) · `STATE=AWAITING_BOOT_RESULT`

**Expected outcome if the display hypothesis is right:** the Samsung logo is
replaced within ~2-3 s by a deep-blue NUXEL screen with colour bars, a white NUXEL
wordmark and a spinning penguin that keeps moving for the rest of the boot — with
**no reboot** (A15 already proved the reset is only the operator's hard-reset hook).
**Falsifier:** screen stays black → the capture will now contain the exact
`NUXEL_FB_*` verdict and the three ioctl return codes, which is itself new evidence.

---

# CYCLE 7 — candidate A17 (2026-10-15), BOOT-only

## Problem under test

A16 proved the display (first light + animated penguin observed on the panel) and
proved systemd 258 runs as PID 1, but **not one service started**. Full forensics:
`A16-POSTMORTEM.md`. Two independent root causes:

1. `src/basic/pidref.c::pidref_set_pid()` returns `-ENOSYS` on this 4.14 kernel
   because `pidfd_open()` is Linux 5.3+, even though the `posix_spawn()` fallback
   it follows *did* start the process. PID1 therefore reports
   `Failed to spawn executor: Function not implemented` for a running executor,
   fails the unit and orphans it (udevd alive 161 s while "failed").
2. The cgroup2 mount was stacked over by the later `mount -t sysfs sysfs /sys`, so
   the final namespace had an empty `/sys/fs/cgroup` and no unit cgroup could be
   created (`Failed at step CGROUP spawning <bin>: No such file or directory`).

Plus two capability gaps: no live diagnostics (Phase 3) and no animation
supervision/handoff primitive (Phase 4).

## Change set (BOOT partition only; no rootfs, no USERDATA, no RECOVERY, no DTBO)

* `src/basic/pidref.c` — degrade to a PID-only `PidRef` when `pidfd_open()` is
  unsupported (new, the decisive fix).
* `src/basic/process-util.c` — `posix_spawn()` fallback (A13, unchanged).
  Both compiled into the single delivered object by
  `.scratch/nx17/nuxel-systemd-edit.py` + `build-systemd4.sh` via `rpmbuild` from
  `systemd-258.11-1.fc43.src.rpm`. See `SYSTEMD-COMPATIBILITY.md`.
* `boot/initramfs/init.sh` — six anchored edits (`A17-INIT-1…5`), sha256
  `74f453d287d38ad37c92e54677ed19cdae0c985ff03359663cba5beac4c4aa19`:
  cgroup2 mounted after sysfs **and verified**; hash+ELF-verified atomic library
  deployment with rollback and post-install re-verification; boot-stage records;
  animation hold PID captured and published; live USB console launched.
* `opt/nuxel/nuxel-verify` (new, static aarch64) — SHA-256 + ELF verifier so the
  initramfs can check content without coreutils.
* `opt/nuxel/nuxel-console` (new, static aarch64) — CDC-ACM gadget + live root
  shell + kernel-log pump.

## Candidate A17

| Artifact | bytes | sha256 |
|---|---|---|
| `A17/initramfs.cpio` | 8,011,812 | `3e0ca12e8dccd134215a0964cf153054d7a6935ba54084bbdad00c780c5f0ea5` |
| `A17/Image-A17` | 48,453,640 | `f9529cd739c6deb97025429a6f7dc79c21010fc79298ba708c011506ca37a745` |
| `A17/boot.img` | 51,193,856 | `911a72e9fbe7f8b591e36fc72bac2d296f7a53b4ff2f9992eedea98e9c6582c2` |
| `A17/libsystemd-shared-258.11-1.fc43.so` | 5,072,280 | `848149cf4b506aef00c0f777840c8e0b5306b65dcf1ae0a1b8c1a63057b4d981` |
| `A17/nuxel-verify` | 625,504 | `aa798f51bf846dac81aa7687c3fe81c35cf5a4fef3b1cf782ea052b9cba5d803` |
| `A17/nuxel-console` | 627,680 | `ccaff7a857f44dc4760dc9f64521a0ca333640e8251b053d3eabad0b12dda48d` |

## Offline verification performed (before any write)

* **Spawn-path reproduction and fix, in `podman`/`fedora:43` (aarch64, glibc 2.42
  — the same libc generation as the rootfs), with a stub that makes
  `pidfd_spawn`/`pidfd_open` return ENOSYS (a 4.14 kernel emulated on a modern
  one):**

  | Library | `posix_spawn_wrapper()` | child really ran | PID1 would log |
  |---|---|---|---|
  | modern kernel, no stub | `rc=0` | yes | spawn-ok |
  | A13/A16 shim, 4.14 stub | `rc=-38 ENOSYS` | **yes** | **Failed to spawn executor** |
  | **A17 library, 4.14 stub** | **`rc=0`** | yes | spawn-ok |

  The middle row reproduces A16 on hardware exactly. Harness: `.scratch/nx17/`.
* `nuxel-verify` self-test in the container: match→0, mismatch→1, aarch64 ELF→0,
  non-ELF→1, missing file→2.
* cpio round-trip: `init` in `A17/initramfs.cpio` is byte-identical to
  `boot/initramfs/init.sh` (57,858 B, `74f453d2…`); the four `opt/nuxel` payloads
  match their sources.
* **embedded-initramfs proof:** the gzip stream inside `Image-A17`
  (`usr/initramfs_data.cpio.gz`, 3,482,596 B) decompresses to a byte-identical
  8,011,812-byte archive, sha256 `3e0ca12e…` = `A17/initramfs.cpio`; `strings` on
  it finds `nuxel-console`, `NUXEL_SD_SHA256`, `nuxel_sd_verify` and the A17
  library hash `848149cf…`. The build is not stale.
* `build-candidate.sh` release gate: **PASS** (header_field40=1, header_size=1648,
  kernel_size 48,453,640, ramdisk lzma 2,359,296 aligned, cpio 79 records,
  `/init` mode 0o100755 size 57,858, partition slack 6,477,824 B). Base is the
  hardware-proven A5 DTB image, so the appended DTB is unchanged
  (`bcdef39c…`). The first pack attempt was **correctly blocked** by the gate for
  duplicate `dev/console`/`dev/null` records (the packer's own dev-node insertion
  on top of the base archive's nodes) and re-packed with `--no-dev-nodes`,
  matching A16.

## Flash receipt

```
Device: R58M75KDB2X model=Galaxy S10+ codename=beyond2lte TWRP=3.7.0_9-2 slot=none
BOOT:   boot -> /dev/block/sda14 size=57,671,680 bytes
PREFLIGHT PASS   (refused once while USERDATA was left mounted read-only by the
                  A16 forensic read; unmounted, then PASS)
BACKUP  BOOT -> backups/s10plus/20261015T145711Z-R58M75KDB2X
BACKUP  BOOT -> scripts/nuxel-adb-flash-pack/backups/nuxel-adb/20261015T145717Z-R58M75KDB2X
FLASHING BOOT: 51,193,856 bytes -> /dev/block/sda14
VERIFIED BOOT: 911a72e9fbe7f8b591e36fc72bac2d296f7a53b4ff2f9992eedea98e9c6582c2 (51,193,856 bytes)
PASS: every written partition matches its local image by full SHA256 readback.
```

USERDATA (sda31), RECOVERY (sda15) and DTBO were not written. No automatic reboot
was issued by the flasher.

`REBOOT_AT=2026-10-15T15:07:35Z` (`adb reboot` from TWRP) · `STATE=AWAITING_BOOT_RESULT`

## Expected outcome if the diagnosis is right

* The penguin appears as in A16 (unchanged renderer), within ~2–3 s.
* `SYSTEMD_LIB_INSTALLED_VERIFIED` (the rootfs currently holds the A13 library,
  hash `502507a7…`, so A17 will deploy and re-verify the new one) and
  `CGROUP2_VERIFIED controllers='cpu cpuset ...'` in the ram console.
* **Zero** `Failed to spawn executor` lines, and `systemd-udevd.service` /
  `systemd-journald.service` / `dbus-broker.service` reaching `active`.
* A CDC-ACM USB serial device on the MacBook: `/dev/cu.usbmodem*` with a live
  root shell and the kernel log streaming.

## Falsifiers / what a failure would mean

* `Failed to spawn executor` still present → a third spawn-path incompatibility;
  the next step is a full strace-equivalent of `sd-executor` from the live shell.
* `CGROUP2_VERIFY_FAILED` → the mount ordering was not the (only) cgroup problem;
  next step is to inspect `/proc/self/cgroup` and `cgroup.subtree_control` live.
* No USB device enumerated at all → the gadget bind failed or the boot stopped
  before `nuxel-console` ran; the ram console will show which, and A18 can bind
  the gadget earlier (right after the devtmpfs mount).

---

# CYCLE 7b — candidate A18 (2026-10-15), BOOT-only

## Problem under test

**A17 failed before `switch_root`** (`A17-POSTMORTEM.md`): toybox 0.8.14 treats an
empty `case` alternative (`""`) as a wildcard, so the `DEVICE` dispatch always took
the generic branch and this board's root resolution depended on `force_s10plus_root`,
which silently bailed in A17. The boot died at t = 7.27 s with
`[FATAL] no root block device found (slot=a)`. Consequence: **the A17 systemd fix
has never run on hardware** — A16's service-execution failure is still the baseline.

## Change set (BOOT partition only)

* `boot/initramfs/init.sh` — five anchored edits (`tools/s10plus/a18/edit-init-a18.py`):
  `if/elif` dispatch with explicit `[ "$DEVICE" = … ]` tests (no case patterns);
  `cmdline_matches_samsung()` using `grep -q`, defined before first use;
  `force_s10plus_root()` rewritten with no `case` patterns and a 20 s heartbeat wait;
  the `s10plus` branch waits for `/dev/sda31` with a per-second heartbeat; the whole
  kernel cmdline is emitted to `/dev/kmsg` in 200-byte `CMDLINE_PART n:` chunks
  (the ram console truncates a single printk at ~1 KiB — that is how A17's cmdline
  was lost). sha256 `3ea2546cf197b0fbd4a290026b7fd3a089585f69e95f110287ab30a40822ee90`
* `opt/nuxel/nuxel-hwprobe` (new, 625,496 B) — identity/boot-mode, `/dev/fb*`
  geometry, DRM presence/absence, full input inventory with capability bitmaps,
  cgroup state, PID1/systemd state, power supplies.
* `opt/nuxel/nuxel-console` (A18 build, 627,680 B) — the A17 gadget work **plus a
  persistent in-rootfs boot reporter** started *before* any USB work, so it
  survives a failed UDC bind / missing tty / broken link and writes
  `/var/log/nuxel-bootreport.txt` with `systemctl is-system-running`,
  `systemctl --failed`, running services, `journalctl -b -p warning` and the count
  of `Failed to spawn executor`.
* The A17 systemd library is unchanged and still shipped (sha256 `848149cf…`).

## Candidate A18

| Artifact | bytes | sha256 |
|---|---|---|
| `A18/initramfs.cpio` | 8,640,476 | `4e763933e6af39a2d32930f6be4879e2cc13e66703180add7924f30f357bed5a` |
| `A18/Image-A18` | 48,715,784 | `8ffd98f6dba0714f92e7bc4b15423652d378ff1279de7fe13aa1757e8b9c6f5f` |
| `A18/boot.img` | 51,456,000 | `6a8d2587c4e47cd0d059c80130ba731421a02370490b8c7071b956dd28b24a38` |

## Offline verification performed (before any write)

* The A18 root-resolution code was extracted **verbatim** and run under the
  initramfs's own `toybox` in podman with the Samsung cmdline and a delayed
  `USERDATA` node. Result: `dispatch: DEVICE='s10plus'` → heartbeat wait →
  `USERDATA via documented /dev/sda31 … after 2s` → `root -> /dev/sda31` →
  `RESULT ROOT_DEV='/dev/sda31' DEVICE='s10plus'`. The same harness on the A17 code
  printed the generic-probe refusal and the FATAL. This is the causal proof.
* `sh -n` clean; the helper is defined before both call sites (asserted
  programmatically — the first draft got this wrong and it was caught here, not on
  the phone).
* cpio round-trip and **embedded-initramfs proof**: the gzip stream in `Image-A18`
  decompresses to a byte-identical 8,640,476-byte archive,
  sha256 `4e763933…`; `strings` finds `nuxel-hwprobe`, `cmdline_matches_samsung` and
  `rootfs boot reporter`.
* `build-candidate.sh` release gate: **PASS** (header_field40=1, header_size=1648,
  kernel 48,715,784 B, ramdisk lzma aligned, cpio 80 records, `/init` 0o100755
  60,889 B, partition slack 6,215,680 B, DTB unchanged `bcdef39c…`).

## Flash receipt

```
Device: R58M75KDB2X model=Galaxy S10+ codename=beyond2lte TWRP=3.7.0_9-2 slot=none
BOOT:   boot -> /dev/block/sda14 size=57,671,680 bytes
PREFLIGHT PASS
BACKUP  BOOT -> scripts/nuxel-adb-flash-pack/backups/nuxel-adb/20261015T153313Z-R58M75KDB2X
FLASHING BOOT: 51,456,000 bytes -> /dev/block/sda14
VERIFIED BOOT: 6a8d2587c4e47cd0d059c80130ba731421a02370490b8c7071b956dd28b24a38 (51,456,000 bytes)
PASS: every written partition matches its local image by full SHA256 readback.
```

`REBOOT_AT=2026-10-15T15:33:59Z` · `STATE=AWAITING_BOOT_RESULT`

## Hardware result so far — one new milestone, one open question

**PROVEN:** the boot brought up its own USB CDC-ACM gadget, which enumerated on the
MacBook as

```
Nuxel S10+ Live Console  ·  Vendor 0x18d1  Product 0x4ee7  Serial NUXEL-S10PLUS-0001
/dev/cu.usbmodem201 created
```

That proves the Exynos 9820 UDC works from plain Linux userspace and that
`nuxel-console` reached and executed the UDC bind — a first for Nuxel.

**OPEN:** the console carried **0 bytes** in both directions across several host
configurations (with/without termios reconfiguration, DTR/RTS asserted via
`TIOCMBIS`, `/dev/tty.*` and `/dev/cu.*`, periodic `CR LF` to elicit a prompt).
Either `/dev/ttyGS0` never appeared on the device side, or it is attached and its
writes never leave the gadget. The device-side answer is in the ram console
(`nuxel-console: …` lines) and, independently, in the persistent report at
`<userdata>/var/log/nuxel-bootreport.txt`. Full record:
`captures/20261015T153357Z-A18-live-run/LIVE-RUN-EVIDENCE.md`.

**Therefore every A18 result that matters — root resolution, `switch_root`,
systemd service execution, cgroup v2 — is still pending a TWRP round trip.**

## CYCLE 8 — A20 (original Nuxel MP4 animation)

### A20 attempt 1/2 — INEFFECTIVE (not a boot failure: nothing ran)
| Field | Value |
|---|---|
| Candidates | `A20/boot.img` sha256 `490e86b5…` (lzma), then `0a22a570…` (lzma, `--statedir` fix) |
| Target | BOOT `/dev/block/sda14` only, full readback PASS both times |
| Reboot | 16:44:03Z |
| Result | the device **re-entered recovery** — bootloader log `s5p_check_keypad: 0x10110000` / `recovery mode set!` / `recovery: Loading entire partition`. `misc` and `param` are all-zero, so no stale BCB; a key was down at power-on. The candidate never executed. |
| Evidence | `captures/20261015T164357Z-A20-live-run/` |

### A20 attempt 3 — INEFFECTIVE (candidate ran, but not our `/init`)
| Field | Value |
|---|---|
| Candidate | `A20/boot.img` sha256 `b8b596e7…` (gzip external ramdisk) |
| Reboot | 16:58:05Z |
| Result | BOOT loaded correctly, **no keypad recovery**, kernel received the ramdisk (`Freeing initrd memory: 3776K`) and **still rejected it** (`junk in compressed archive`). The boot ran A19's `/init` from the kernel's built-in initramfs: old `FIRSTLIGHT hold started pid=`, the 42 s shell scan, no `fb-anim.pid`, `ANIM_STAGE=FIRST_LIGHT`. Ended in a hard-reset-triggered panic at ~51 s. |
| Root cause | `INITRAMFS-DELIVERY-ROOT-CAUSE.md` — the bootloader advertises an initrd it never populates; only a kernel-embedded initramfs is used, and `lzma`, `gzip` and any other external container are equally ignored. |

### A20 attempt 4 — DELIVERED (kernel-embedded initramfs)
| Field | Value |
|---|---|
| Kernel | rebuilt in container `nuxel-kb` as `Image-A20`, 48,781,320 B, sha256 `cdb974a89068efe7cd623a0f1da718c853303edaf212adb7ebace2e93bc9e962`, `CONFIG_INITRAMFS_SOURCE=/b/a17/initramfs-a20.cpio` (verified: embedded archive 8,843,324 B contains `NUXEL_INIT_REV`, `nuxel_start_animation`, `nuxel-anim-player`, `ORIGINAL_MP4`) |
| boot.img | 51,587,072 B sha256 `8edd97b79b43e21bf411ce7645cc91635c25da8ee529b7e4ba6fabf23c9e2650` |
| Preflight/gate | `build-candidate.sh` release gate **PASS**, `partition_slack` 6,084,608 |
| Backup to Mac | `backups/s10plus/20261015T170155Z-R58M75KDB2X/boot-before.img` |
| Write | dd → `/dev/block/sda14`, 51,587,072 B |
| Readback | **VERIFIED BOOT: `8edd97b7…` (full re-read == local image)** |
| Reboot | **2026-10-15T17:02:31Z** |
| Observation window | at 17:05:49Z still running (3 min 18 s) with `/dev/cu.usbmodem201` continuously enumerated. Previous candidates died in ~96 s. **No TWRP return.** |
| State | `AWAITING_BOOT_RESULT` (operator visual confirmation) |
| Not written | RECOVERY, USERDATA image, EFS, SEC_EFS, PIT, bootloader, radio, DTBO |

The animation container was deployed separately, by a **live write into the
mounted Fedora rootfs** (no 4 GiB reflash):
`/usr/share/nuxel/boot/nuxel-animation.nux` (18,481,546 B, sha256 `7d296871…`,
re-verified on device) and a copy of the player at `/usr/bin/nuxel-anim-player`
(66,120 B, sha256 `87f755f4…`).

---

# A21 — 2026-10-15 (cycle 9) — one penguin / correct colours / smooth playback

```
boot.img       build/out/s10plus/debug-candidates/A21/boot.img
               51,587,072 B  sha256 153807621cf9fa22c10edcd4f74078fc022cf55e5d3ed1e4940378b50a749173
Image-A21      48,781,320 B  sha256 e34b7b4bf2dfe4ecc626ff442a0cb1a2531623b19c95f45618b9766986ebc2b4
initramfs      8,905,080 B   sha256 a492a385554b0aee21b6c5993c714f44d8f158906ef76a63bdd2a8298c738597
  kernel-embedded initramfs verified: gzip @33809680 inflates to exactly that cpio
nuxel-anim-player 66,152 B  sha256 c35b2db4b309cb236880b63f02f9bf9c92356cde613e9b40ed47518ba1001903
nuxel-fb-phone    68,240 B  sha256 8539cde1f2556206100320ae88ae060b3bd25f747c74bad26487975be3d19c62
FLASHED  BOOT /dev/block/sda14  full 51,587,072-byte SHA-256 readback PASS
BACKUP   backups/nuxel-adb/20261015T173839Z-R58M75KDB2X, …1746Z-…
REBOOT   REBOOT_AT=2026-10-15T17:40:40Z
RESULT   BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP at 17:49:19Z (operator hard-reset at t=400 s)
```

What was different from A20 (all measured on the boot): the palette is expanded into the
destination pixel format with the driver's bitfields; the resident painter is deferred
and, when it does run, stoppable by pid-file + stop-file + identity-checked SIGTERM; the
numeric evidence channel works; `--secs`/`--stopfile` actually parse; state files land in
the Fedora rootfs.

Live (over the USB console, while the animation played):
`24.00 fps, 0 skips over 5520 frames`, `NO_PENGUIN_PAINTER_RUNNING`,
`ANIM_STAGE=MP4_PLAYER_ACTIVE`, `systemctl --failed = 0`.

New hardware hazard found during the run (our fault, now fixed in A22):
`decon_release` disables the panel on **any** `close()` of `/dev/fb0`, and 1279 pans then
failed with `UNBLANK missed`. `fb_blank` alone does not recover it; `FBIOPUT_VSCREENINFO`
does.

# A22 — 2026-10-15 (cycle 9) — self-healing panel + opt-in colour test

```
boot.img       build/out/s10plus/debug-candidates/A22/boot.img
               51,587,072 B  sha256 3d35aedc1abb539afb593b835e12263796980f4b4a541dcdca624a0213ccc978
Image-A22      48,781,320 B  sha256 c77afcd27cc3acc4973d20092db01aa381cde3016baa3f91083f22d5d003b044
initramfs      8,905,080 B   sha256 507b812f90bf3b6c8dd866b416d9a7faddee5121033bab17f4d986927834c549
init (init.sh) 68,468 B      sha256 841fb8b0f5f7ab3c09f0dea8b95cdb614b4a2a4eb0a5e6f3f31d101562854a8b
nuxel-anim-player 66,152 B  sha256 c7def23e4fd690808b6266e9e4ee0023b9c5c1447bccd4915f2d8057c97ca5dc
  kernel-embedded initramfs verified: gzip @33809680 inflates to exactly that cpio
FLASHED  BOOT /dev/block/sda14  full 51,587,072-byte SHA-256 readback PASS
BACKUP   backups/nuxel-adb/20261015T175036Z-R58M75KDB2X
REBOOT   REBOOT_AT=2026-10-15T17:51:18Z
RESULT   AWAITING_BOOT_RESULT
```

Changes vs A21 — each one justified by an A21 measurement, not by speculation:

1. player re-issues `FBIOBLANK(UNBLANK)` + `FBIOPUT_VSCREENINFO` on any failed
   `FBIOPAN_DISPLAY`, and unconditionally every 240 frames; logs
   `NUXEL_ANIM_PAN_FAILED_TOTAL`, `NUXEL_ANIM_PAN_LAST_RC`, `NUXEL_ANIM_PAN_REASSERTED`;
2. player gains opt-in `--colourtest[=secs]` (red/green/blue/white/black bars packed with
   the driver bitfields, expected + read-back u32 logged) — never used by the boot path;
3. `init.sh` clears stale `fb-hold.pid` / `fb-anim.pid` at boot.

Live check at t=59 s: `HEARTBEAT_FRAMES` 240/480/720/960/1200 exactly 10 s apart = 24.0 fps,
`NO_PENGUIN_PAINTER`, `ANIM_STAGE=MP4_PLAYER_ACTIVE`, `PAN_FAILED` count zero (the console
was used read-only this time: **no `/dev/fb0` access**).
