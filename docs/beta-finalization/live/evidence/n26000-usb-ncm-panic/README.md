# NUXEL-26000 — USB CDC-NCM physical result: BLOCKED (kernel panic)

Date: 2026-10-27 (host Europe/Amsterdam)
Target: Samsung Galaxy S10+ SM-G975F / beyond2lte / Fedora 43 aarch64
Kernel: Samsung-derived Linux **4.14.253** (unchanged; nothing flashed or rebuilt)

## Verdict

**USB-network SSH is BLOCKED_KERNEL_PANIC on this kernel.**  The kernel does
compile the NCM function (`CONFIG_USB_F_NCM=y`, `CONFIG_USB_CONFIGFS_NCM=y`),
but the live configfs gadget stack does not survive an NCM function teardown.
This is a hard blocker, not an untested claim.

No USB Ethernet link was established and no USB SSH connection is claimed.

## What was actually run

1. Read-only audit (serial live console, kernel 4.14.253):
   - `CONFIG_USB_CONFIGFS=y`, `CONFIG_USB_DWC3=y`,
     `CONFIG_USB_F_NCM=y`, `CONFIG_USB_CONFIGFS_NCM=y`;
   - `CONFIG_USB_CONFIGFS_ECM` and `CONFIG_USB_CONFIGFS_ECM_SUBSET` are **not**
     set;
   - the live gadget was `usb_gadget/nuxel` with only `acm.usb0`, bound to
     `10c00000.dwc3` at SuperSpeed.
2. The opt-in helper was copied to `/var/tmp/nuxel-usb/` over WLAN SSH and
   executed.  It created the `ncm.usb0` function instance, then failed writing
   the read-only `ifname` attribute.  Its failure path unbound/rebound the UDC.
3. The host then reported `usb 2-3: can't set config #1, error -71` and the
   CDC-ACM `/dev/ttyACM0` disappeared.  A host-side `USBDEVFS_RESET` followed by
   `echo 1 > /sys/bus/usb/devices/2-3/bConfigurationValue` restored ttyACM0.
4. The leftover NCM function directory was removed with `rmdir`.  At that point
   the phone panicked and the watchdog rebooted it.

## Panic evidence

`pstore-dmesg-ramoops-0.txt` begins with `Panic#2 Part1` and the faulting task
`rmdir:77554`.  The backtrace includes:

```
misc_deregister
ncm_free_inst
usb_put_function_instance
ncm_attr_release
```

The previous-boot journal ends with the watchdog keepalive/did-not-stop lines at
15:25:32.  The new boot reports `sec_debug.reset_reason=4`.

- boot ID before: `96f40ab6-e1ea-4952-af24-6f7efae499d2`
- boot ID after:  `a269e14b-2ccd-4f0a-bbeb-088e84daa5a3`
- post-reboot kernel: `4.14.253` (unchanged)
- post-reboot serial: PASS (framed root command)
- post-reboot WLAN SSH: PASS (public-key, pinned host key)
- current gadget after reboot: only `acm.usb0`, bound to `10c00000.dwc3`

## Cleanup and current state

- `/var/lib/nuxel/usb-net` (the failed helper's backup/status directory) was
  removed over the serial console.
- `/var/tmp/nuxel-usb` was removed.
- No NCM function remains in the live gadget.
- The SSH policy drop-ins and the `nuxel` authorized key survived the reboot and
  were re-verified after it.

## Evidence files

| File | What it is |
|---|---|
| `pstore-dmesg-ramoops-0.txt` | full 27,206-byte Samsung pstore panic dump |
| `previous-boot-journal.txt` | journal tail of the boot that panicked (watchdog at 15:25:32) |
| `host-usb-dmesg.txt` | host USB enumeration / `error -71` / reset / re-enumeration |
| `kernel-config-usb.txt` | real `/proc/config.gz` USB gadget/NCM options |
| `current-gadget.txt` | post-reboot gadget state (`acm.usb0` only) |
| `sshd-effective.txt` | post-reboot effective key-only/CIDR SSH policy |
| `boot-id.txt` | post-reboot boot id, uname and uptime |
| `cmdline.txt` | `/proc/cmdline`, including `sec_debug.reset_reason=4` |
| `pstore-list.txt` | pstore file inventory |
| `guard-refusal.txt` | post-reboot status + `--apply` refusal from the updated helper |
| `status.json` | machine-readable summary |

## Rollback / prevention

The helper `tools/beta/live/nuxel-usb-net.py` now refuses `--apply` on
`4.14.253` unless the operator passes the explicit
`--allow-unsafe-kernel` experiment flag, and reports
`BLOCKED_KERNEL_PANIC`.  Do **not** retry NCM on this kernel.  The serial
console and WLAN SSH are the usable links; USB remains a charging/CDC-ACM
console path only.

The phone did not need a manual power cycle: the watchdog rebooted it and the
serial console came back automatically.  The reboot was an unplanned
consequence of the NCM teardown, not a requested reboot.
