# NUXEL A74 / 23000 — FINAL STATUS (in progress)

**Date:** 2026-10-25 (CEST)
**Branch:** `nuxel/a74-23000-usb-unplug-pwnage`
**Boot ID (pre-test):** `c630c24d-5261-486c-8217-82dd8765f4ad`

## Root cause
**Kernel hard lockup → hardware watchdog reset**, caused by the A73 physical
detach veto reading the Samsung DWC3 debugfs `link_state` register node
(`/sys/kernel/debug/10c00000.dwc3/link_state`) after detach, while the FSYS0
power domain was power-gated. The bus SLVERR from that read escalates to
`Watchdog detected hard LOCKUP on cpu 0` and an s3c2410-wdt reset.

Evidence: `/proc/reset_reason_extra_info` (`FTYPE=PANIC`, `BUS=FSYS0/0x10c0c70c
READ SLVERR`), `/sys/fs/pstore/dmesg-ramoops-0` (`Panic#1`), previous-boot journal
(`synchronous external abort … 0x010c0c000`), and the 19:30→19:41 reboot loop in
`journalctl --list-boots`.

## Fix
Removed the DWC3 debugfs `link_state` read from both indicator producers
(Python `system_indicators.py` and native `nuxel-pwa-host.c` a33+a45). The
Type-C class `data_role` remains the sole safe physical detach veto. Deployed,
hashes verified, services restarted. Automated regression tests ALL PASS.

## Status
- Code fix + offline tests + deploy: **DONE**.
- Alternate recovery (SSH over Wi-Fi): **DONE** (verified working).
- Durable on-device detach logger (A74, no debugfs read): **RUNNING**.
- **Physical unplug/replug cycles: PENDING OWNER ACTION.**

The agent cannot physically pull the USB cable. The owner must run the
P2–P5 cycles (and optionally P6–P11) from TEST-MATRIX.md, then the agent
retrieves `/var/lib/nuxel/a74-usb-unplug.log` over SSH (or USB after re-plug)
and records `PASS_PHYSICAL` / failure per cycle. **No physical success is
claimed from the automated tests.**
