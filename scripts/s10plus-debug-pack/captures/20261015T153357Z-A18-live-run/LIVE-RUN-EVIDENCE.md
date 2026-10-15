# A18 live-run evidence (2026-10-15, 15:33:59Z onwards)

`REBOOT_AT=2026-10-15T15:33:59Z` · `BOOT_IMG_SHA256=6a8d2587c4e47cd0d059c80130ba731421a02370490b8c7071b956dd28b24a38`
(readback-verified before reboot)

## PROVEN: the Nuxel USB gadget binds and enumerates on the MacBook

```
        Nuxel S10+ Live Console:
          Product ID: 0x4ee7
          Vendor ID: 0x18d1  (Google Inc.)
          Version: 1.00
          Serial Number: NUXEL-S10PLUS-0001
          Speed: Up to 5 Gb/s
          Manufacturer: Nuxel
```
and macOS created the serial node:
```
crw-rw-rw-  1 root  wheel  0x9000007  /dev/cu.usbmodem201
```

This is the first time any Nuxel boot has offered a USB interface built by its own
userspace. It proves, on hardware:

* the Exynos 9820 UDC `10c00000.dwc3` **is** usable from plain Linux userspace;
* configfs gadget creation works from the initramfs with no rootfs change;
* `nuxel-console` executed far enough to write `idVendor`/`idProduct`/strings and,
  critically, to **bind the UDC**.

## NOT YET WORKING: no data on the console channel

Reads on both `/dev/cu.usbmodem201` and `/dev/tty.usbmodem201` returned **0 bytes**
across several attempts, with and without termios reconfiguration, with DTR/RTS
asserted (`TIOCMBIS`), and with ~12 s of periodic `CR LF` writes to elicit a prompt.

Therefore, on the device side either

* `/dev/ttyGS0` did not appear inside the 6 s window and `nuxel-console` returned
  without forking the shell (the ACM tty should be created at
  `mkdir functions/acm.usb0`, i.e. before the bind), or
* the shell/keeper are attached but nothing they write reaches the host.

Both are visible in the ram console as our own `nuxel-console: …` lines
(`ttyGS0 ready` / `did not appear` / `live shell pid=…`), which is why the
end-to-end test still requires one TWRP round trip.

## What the phone-side evidence will answer (read from TWRP)

1. `/proc/last_kmsg` — did root resolution succeed (the A18 heartbeat lines), did
   `switch_root` happen, did systemd start, how many `Failed to spawn executor`,
   which services reached `active`, and what `nuxel-console` logged.
2. `<userdata>/var/log/nuxel-bootreport.txt` — the **new persistent report** written
   by the reporter child, which starts before any USB work and survives a failed
   gadget bind. It contains `systemctl is-system-running`, `systemctl --failed`,
   running services, `journalctl -b -p warning` and the count of
   `Failed to spawn executor` — i.e. the A17 service-execution verdict, readable
   even if the console never works.
3. `<userdata>/var/lib/nuxel/{boot-stage,animation,fb-hold.pid}` — the boot-stage
   record.
4. Whether the A17 systemd library was deployed and re-verified in the rootfs.

## Honest status

```
USB_GADGET_BIND             = PROVEN (hardware)
LIVE_SHELL_OVER_USB         = NOT YET (0 bytes both directions)
ROOT_RESOLUTION_FIX         = unverified on hardware yet
SYSTEMD_SERVICE_EXECUTION   = unverified on hardware yet
```
