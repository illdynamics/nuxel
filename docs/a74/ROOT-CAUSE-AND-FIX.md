# NUXEL A74 / 23000 — Root cause and fix

**Date:** 2026-10-25 (CEST)
**Branch:** `nuxel/a74-23000-usb-unplug-pwnage` (off `nuxel/a73-22000-ghostbusters-radio` @ `b804f17`)
**Target:** Samsung Galaxy S10+ SM-G975F, Linux 4.14.253 #15 aarch64, Fedora 43

## Root cause (evidence-backed)

Unplugging the PC cable made the S10+ hard-lock-up and watchdog-reset because the
A73 “physical detach veto” read a **Samsung DWC3 debugfs register node**,
`/sys/kernel/debug/10c00000.dwc3/link_state`, on a fast timer.

- The A73 native host (`nuxel-pwa-host`, commit `f24d684`) calls
  `ind_dwc3_link_on()` from its 250 ms indicator signature timer (4 reads/s) and
  on every USB/typec uevent. The Python bridge
  (`system_indicators._dwc3_link_on()`) reads the same node per HTTP poll.
- After a physical detach the DWC3 controller’s FSYS0 power domain
  (`pd-fsys0a`) is powered off and the controller is runtime-suspended. On this
  downstream 4.14 kernel the `link_state` debugfs read dereferences the
  controller registers anyway.
- That access produces a bus **SLVERR** on FSYS0, which the kernel escalates to a
  hard lockup, then the hardware watchdog fires.

### Proof chain
1. `/proc/reset_reason_extra_info` (Samsung AP boot-record):
   `"FTYPE":"PANIC"`, `"PANIC":"Watchdog detected hard LOCKUP on cpu 0"`,
   `"PC":"watchdog_timer_fn+0x3c0/0x68c"`, `"RSTCNT":"4"`,
   `"BUS":"CPU0 Cluster0 / FSYS0/ 0x10c0c70c / READ/ Error Detect by the Slave(SLVERR)"`.
2. `/sys/fs/pstore/dmesg-ramoops-0` (`Panic#1 Part1`): ITMON report
   `Target: FSYS0`, `Target Address: 0x10C0C70C`, `SLVERR`, followed by
   `s3c2410wdt_panic_handler: watchdog reset is started on panic after 5secs`.
3. Previous boot journal (`journalctl -b -2`, ends 19:38:34):
   `synchronous external abort (0x96000010) at 0xffffff80212b0000[0x010c0c000]`
   then ITMON `Target: FSYS0 / 0x10C0C000 / READ / SLVERR`.
   `0x10C0C000` is the DWC3 controller base (`10c00000.dwc3`), i.e. the exact
   device whose debugfs `link_state` the A73 code was reading.
4. `journalctl --list-boots` shows a reboot loop matching the owner report:
   `-4` 17:57→**19:30:05** (the A73 host was rebuilt on-device at 19:20),
   `-3` 19:30:53→19:34:03, `-2` 19:35:02→19:38:34, `-1` 19:39:32→19:40:40,
   `0` 19:41:39→now. The A73 on-device logger
   `/var/lib/nuxel/a73-usb-unplug.log` ends at 19:30:05 with a block of NUL
   bytes — a write interrupted by the hard reset at detach time.

## Classification

**Kernel hard lockup → hardware watchdog reset**, triggered by an unsafe
userspace read of a DWC3 debugfs register node after detach. It is *not* a
power/PMIC failure, a userspace reboot command, or a UI-only hang.

## Alternative hypotheses ruled out
- *Userspace-initiated reboot*: no `reboot`/`systemctl reboot` in journal; reset
  record is `FTYPE=PANIC`, not a normal shutdown.
- *Power/PMIC/battery reset*: battery was 100% / healthy at every crash; the
  reset record shows a CPU lockup on a USB register read, not a power-fail
  reason.
- *Console teardown race in `nuxel-console`*: the console daemon (PIDs
  3525/3526) has no teardown/reboot path and survived; the abort is a kernel
  register read.
- *Systemd/udev restart loop*: no such loop; `nuxel-console.service` is
  installed-but-not-enabled, and no unit restarts the OS on detach.
- *UI-only hang*: boot ID changed and watchdog fired — a real reset, not a hang.

## Fix (minimal)
Remove the DWC3 debugfs `link_state` read from the physical-detach veto. The
Type-C class `data_role` (max77705-usbc) is retained as the sole independent
physical signal — it is a safe PMIC sysfs attribute and is sufficient to veto a
stale `configured` UDC after detach.

Changed files:
- `services/nuxel-bridge/src/system_indicators.py` — delete `_dwc3_link_on()`;
  `_physical_data_link_veto()` now uses only `_typec_data_role_device()`.
- `tools/s10plus/a33/nuxel-pwa-host.c` — delete `ind_dwc3_link_on()`; drop the
  `link == 0` veto in `ind_pc_connected_ex()`.
- `tools/s10plus/a45/nuxel-pwa-host.c` — same change (the deployed source).
- Tests updated to assert the debugfs node is **not** consulted.

No icon/artwork/layout/animation/size/position was changed. No kernel/bootloader/
firmware/DtB flash. No reboot command, watchdog suppression, or panic suppression.
