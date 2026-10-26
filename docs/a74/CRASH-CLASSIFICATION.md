# NUXEL A74 / 23000 — Crash classification

## Verdict

| question | answer | evidence |
|---|---|---|
| Failure class | **kernel hard lockup → watchdog reset** | reset record + pstore + previous-boot journal |
| Sub-cause | unsafe DWC3 debugfs register read (`link_state`) after detach | A73 code + FSYS0/SLVERR abort at `0x10C0C000` |
| Kernel panic/oops? | Yes — “Watchdog detected hard LOCKUP on cpu 0” | `/proc/reset_reason_extra_info` |
| Userspace reboot? | No | no reboot syscall/journal; reset FTYPE=PANIC |
| Watchdog reset? | Yes — secondary to the lockup | `s3c2410wdt_panic_handler … reset after 5secs` |
| Power/PMIC reset? | No | battery 100% healthy; abort is a bus read |
| UI-only hang? | No | boot ID changed, watchdog fired |

## Evidence sources
- `/proc/reset_reason_extra_info` → `FTYPE=PANIC`, `PANIC=Watchdog detected hard LOCKUP on cpu 0`, `PC=watchdog_timer_fn+0x3c0/0x68c`, `RSTCNT=4`, `BUS=CPU0 Cluster0 / FSYS0/ 0x10c0c70c / READ / SLVERR`.
- `/sys/fs/pstore/dmesg-ramoops-0` → `Panic#1 Part1`, ITMON `FSYS0 0x10C0C70C SLVERR`, `s3c2410wdt_panic_handler`.
- `journalctl -b -2` tail → `synchronous external abort (0x96000010) … [0x010c0c000]`, ITMON `FSYS0 0x10C0C000 READ SLVERR`.
- `journalctl --list-boots` → boots `-4..-1` form a detach-triggered reboot loop (19:30→19:41), current boot `0` is `c630c24d-5261-486c-8217-82dd8765f4ad`.
- `/var/lib/nuxel/a73-usb-unplug.log` → last sample 19:30:05 then NUL-block (write interrupted by hard reset).

## Kernel facts (read-only)
- `kernel.panic_on_oops = 1`, `kernel.panic = 0`, `kernel.watchdog_thresh = 10`.
- cmdline: `oops=panic softdog.soft_margin=100 softdog.soft_panic=1 sec_watchdog.sec_pet=5`.
- Watchdog: `s3c2410-wdt 10050000.watchdog_cl0` (cluster 0), `watchdogd` PID 1298.
