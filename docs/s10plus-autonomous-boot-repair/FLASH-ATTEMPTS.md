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
