# LIVE DEBUG CONNECTIVITY FOR NUXEL RUNTIME (Phase 3)

Goal: stop having to lose a boot, hand-recover into TWRP and read
`/proc/last_kmsg` in order to learn anything.

## 1. What is technically available on this board

Read live from TWRP on the handset (`adb shell`) and from the A16 ram console:

```
/sys/class/udc/10c00000.dwc3                 <- the UDC exists (TWRP, live)
/config/usb_gadget ... configfs mounted      <- `usb_gadget` present in /sys/kernel/config
dwc3 10c00000.dwc3: Binding gadget dwc3-gadget       (A16 boot log, t=1.523)
dwc3 10c00000.dwc3: dwc3_otg_init / exynos-dwc3 ... dwc3_exynos_rsw_start
```

Kernel configuration (A16/A17 `.config`, i.e. the kernel we actually boot):

```
CONFIG_USB_GADGET=y                 CONFIG_USB_CONFIGFS=y
CONFIG_USB_CONFIGFS_ACM=y           CONFIG_USB_CONFIGFS_RNDIS=y
CONFIG_USB_CONFIGFS_NCM=y           CONFIG_USB_CONFIGFS_F_FS=y
CONFIG_USB_DWC3=y                   CONFIG_USB_DWC3_DUAL_ROLE=y
CONFIG_USB_DWC3_EXYNOS=y            CONFIG_USB_CONFIGFS_UEVENT=y
```

So a **CDC-ACM USB serial gadget** is fully supported and can be created from
Linux userspace through configfs. `CONFIG_USB_CONFIGFS_F_FS=y` also means a real
ADB (or any FunctionFS protocol) endpoint is *possible*, but it would need an
`adbd`-equivalent daemon in the Fedora rootfs — CDC-ACM gives a live console for
a fraction of the work and no rootfs change.

**Android recovery's ADB does not transfer.** TWRP's `adbd` + its own
`init.usb.rc` set the gadget up; the Fedora rootfs has neither. Nothing in the
Fedora userspace was creating a gadget before A17.

## 2. What A17 implements

`opt/nuxel/nuxel-console` (static aarch64, 627,680 B, sha256
`ccaff7a857f44dc4760dc9f64521a0ca333640e8251b053d3eabad0b12dda48d`), launched by
`init.sh` **after** the pseudo-filesystem mounts and **before** `switch_root`:

1. mounts `configfs` and creates a gadget `nuxel` (idVendor `0x18d1`,
   idProduct `0x4ee7`, ACM function `acm.usb0`), binds it to the UDC;
2. waits for `/dev/ttyGS0` (up to ~6 s) and logs the result;
3. forks a **kernel-log pump**: non-blocking `/dev/kmsg` reader → `ttyGS0`;
4. forks an **interactive root shell**: `chdir($ROOT_MNT)` → `chroot(".")` →
   `setsid` → `TIOCSCTTY` → `exec /bin/sh -i`.

Because it runs from the initramfs and only needs `chroot()`, **no rootfs file is
modified** — the channel is delivered by the BOOT partition alone (same property
the A13 systemd library delivery had). The shell's root is the ext4 rootfs it
chroots into, so it survives `switch_root` (which only re-roots PID1).

On the MacBook:

```
screen /dev/tty.usbmodemXXXX 115200      # or: cu -l /dev/cu.usbmodemXXXX
```

The port gives a root shell *inside the running Fedora/Nuxel system* plus the
live kernel ring buffer streamed above the prompt, so `journalctl -b`,
`systemctl --failed`, `lsmod`, `cat /dev/fb0`-adjacent inspections and controlled
`reboot`/`poweroff` are all available without ever entering recovery.

## 3. Why this is safe

* Failure is caught and logged; the program returns a status and `init.sh`
  continues. A gadget that cannot bind never costs a boot.
* It runs before `switch_root`, so PID1 is still the initramfs shell and the
  evidence path (`/dev/kmsg`) is guaranteed alive.
* Nothing is written to USERDATA, RECOVERY, DTBO or the system partition.
* The USB role is untouched: no writes to `/sys/class/usb_role`, no
  `extcon` manipulation. If the controller is not already in device mode, bind
  fails with a logged errno and the boot proceeds exactly as before.

## 4. Fallback if the gadget cannot bind

Already in place and unchanged: the persistent boot record. `init.sh` writes

* `/run/nuxel-diag.log` (in-RAM),
* `<rootfs>/nuxel-boot-diag.log` (survives the failed boot; read it from TWRP),
* a raw copy in the unused tail of the BOOT partition (readable with `dd` alone),

and the kernel ram console (`/proc/last_kmsg`) keeps the full kernel + systemd
record.

## 5. Status

```
MILESTONE_LIVE_USB_DIAGNOSTICS=IMPLEMENTED_NOT_YET_PROVEN_ON_HARDWARE
```

The very first A17 boot is the test: the phone must enumerate on the MacBook as a
CDC-ACM device and produce a shell. See `NEXT-ACTION.md`.
