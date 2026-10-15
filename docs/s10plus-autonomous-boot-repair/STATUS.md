# STATUS — cycle 2 (2026-10-15)

**Mission:** boot Nuxel (Fedora 43 aarch64) on Samsung Galaxy S10+ SM-G975F
(`beyond2lte`), Exynos 9820 rev 26, bootloader G975FXXSEFUL1, TWRP 3.7.0_9-2.

## Headline
**Stage B is proven on hardware for the first time.** The Nuxel kernel
(4.14.253, `nuxel@nuxel-phosh`) executed on the handset in attempt A2 and its
panic dump was recovered from pstore. The bootloop had two container-level
causes: a gzip kernel payload S-Boot jumps into as code (**fixed in A2**), and a
ramdisk that the kernel cannot unpack because S-Boot delivers it with its own
sector-rounded length (**A3 fix, boot result pending**).

## Evidence captured this cycle
* `captures/20261015T070500Z-A1-postfail/` — S-Boot boot records proving the
  Nuxel BOOT image was loaded 7x with zero kernel output.
* `captures/20261015T071500Z-A2-postfail/` — the A2 `last_kmsg` (767 KB) with the
  full initramfs/SAR_RD/panic chain **and** `dmesg-ramoops-0.txt`, the kernel panic
  dump whose `linux_banner` names the Nuxel kernel.
* Read-only collectors: `captures/20261015T0712*` (previous-boot overview, pstore,
  partitions, recovery kernel info).

## Milestones

| # | Milestone | State | Evidence |
|---|---|---|---|
| 1 | Previous-boot evidence captured | **DONE** | S-Boot boot records + pstore panic dump + last_kmsg |
| 2 | Failure stage localized | **DONE** | root cause written up in `ROOT-CAUSE.md` |
| 3 | ARM64 Linux kernel executes | **ACHIEVED** | pstore `linux_banner: Linux version 4.14.253 (nuxel@nuxel-phosh)`; kernel log to t=1.96 s with full driver probe |
| 4 | Initramfs mounts the Fedora rootfs | **NOT YET - the single blocker** | the kernel receives an initrd of exactly the right length (8128K) but reports `junk in compressed archive`; see `NEXT-ACTION.md` |
| 5 | Fedora systemd starts | NOT YET | — |
| 6 | Diagnostic connectivity under Nuxel | NOT YET | the Fedora image ships no adbd; the BOOT-slack record is the fallback channel |
| 7 | Samsung display initializes | PARTIAL | display drivers/tasks present in the A2 kernel dump (`130b0000.displa`, `decon0/2`, `dsim0-wq`, `panel-bl-thread`); no userspace evidence yet |
| 8 | Nuxel first-light UI | NOT YET | — |
| 9 | Phoc/Phosh session | NOT YET | — |
| 10 | Usable Nuxel phone interface | NOT YET | — |

## Attempt ledger (this cycle)
| ID | Change | Write/readback | Boot result |
|---|---|---|---|
| A1 | cmdline-independent initramfs (gzip kernel kept) | verified | FAILED (7 silent loads) |
| A2 | uncompressed kernel Image | verified (`9ba1bd21…`) | FAILED — but kernel executed and panicked; root cause found |
| A3 | unmangled ramdisk + v1-spec header | verified (`57ff4d5e…`) | FAILED - S-Boot now parses `BOOT IMG HDR V1` and reports the exact size; kernel's initrd was `round_down(size,4096)` = 8000K |
| A4 | page-floor-proof ramdisk padding | verified (`dcc5186b…`) | FAILED - length now exact (8128K); payload still rejected |
| A5 | DTB `/chosen` initrd placeholder removed | verified (`6950241c…`) | FAILED - identical chain; S-Boot overwrites `/chosen` itself |

## Risks recorded
* `backups/s10plus/boot-original.img` is a `DUMMY` placeholder — there is **no**
  real backup of the stock BOOT partition. RECOVERY was never touched and its
  backup is valid, so the recovery path is intact.
* S-Boot cannot persist its own log on this unit (`UFS Write 10 … CHECK
  CONDITION` at `LBA(79872) LUN(0)`), so S-Boot-side diagnostics are limited to
  what the kernel's ram console retains.
