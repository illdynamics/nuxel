# PWNAGE-51000 — macOS MTP workflow

## Live gadget

```
acm.usb0
mtp.gs0
/sys/class/udc/10c00000.dwc3/state = configured
current_speed = high-speed
/dev/mtp_usb present
nuxel-mtp.service active
MTP root = /home/nuxel/Shared (Gallery, Pictures, Videos, Downloads)
```

No USB mass-storage LUN, no live rootfs/home export, no NCM. CDC-ACM is preserved
in every mode.

## macOS Finder limitation

macOS Finder does not natively mount MTP devices as volumes. This is a host
protocol limitation, not a Nuxel descriptor bug. The supported workflow is
OpenMTP or MTPLX (or any libmtp client).

The lockscreen connection-mode dialog now says:

> File transfer active. On macOS use OpenMTP or MTPLX; Finder does not mount MTP volumes.

## Verified transfers (libmtp 1.1.23)

Device: `18d1:4ee7`, Manufacturer `Nuxel`, Model `Nuxel S10+`.

Phone → Mac (object ID 17):

```
699b99276f09ec595dab57af3bfa6e25b45dcb4e3973921c05a5f8447a2b43dd  phone-to-mac-nuxel-mtp-test.txt
```

Mac → phone:

```
source: caba21e6766f5ad47a4f75a1bd0702fc812696d495699a6ad657a7f5d3eee5a3
phone:  caba21e6766f5ad47a4f75a1bd0702fc812696d495699a6ad657a7f5d3eee5a3  /home/nuxel/Shared/mac-to-phone-nuxel.txt
```

Commands used (Mac):

```sh
mtp-detect
mtp-files
mtp-getfile 17 phone-to-mac-nuxel-mtp-test.txt
mtp-sendfile mac-to-phone-nuxel.txt /
```

## Persistence

The user's selection is written to `/var/lib/nuxel/usb-mode` and restored by
`nuxel-usb-mode-restore.service` after `nuxel-usb-mode-monitor.service`.
File-transfer mode survived the final reboot (`selected=file_transfer`,
`active=true`, `/dev/mtp_usb` present).

## Not done

- OpenMTP/MTPLX GUI-specific screenshots (libmtp proves the same protocol path).
- microSD export (no mounted removable card in this run).
- SMB/WebDAV Finder share (not implemented; use MTP client).

## OpenMTP on macOS: the config #2 exclusive-access trap

OpenMTP 3.3.0 (Homebrew cask) ships its own `kalam` engine (libusb) at
`/Applications/OpenMTP.app/Contents/Resources/bin/`. It failed with:

```
Device::Find failed:(*_interface)->USBInterfaceOpen(_interface): error 0xe00002c5
no mtp device found
```

`0xe00002c5` is `kIOReturnExclusiveAccess`. The device was present and
`nuxel-mtp.service` was running, so this was **not** a missing-radio or
missing-gadget problem.

### Root cause

The Samsung-derived composite gadget emits **two configurations**:

| Config | Contents | macOS behaviour |
|---|---|---|
| `#1` | MTP only | No kernel driver matches class 255 → libusb can claim it |
| `#2` | CDC-ACM console + MTP | `AppleUSBCDCCompositeDevice` prefers this |

`usb: config_buf skip f->acm` / `usb: set_config_number multi config_num=1`
in `dmesg` shows the synthesis; `high-speed config #2: c` shows the selection.
On config `#2` the ACM interface has a kernel driver attached
(`Interface has a kernel driver attached`, per `mtp-detect`), the composite
DEXT holds the device, and every libusb client is locked out.

libmtp only worked before because it **explicitly sends SET_CONFIGURATION 1**
(`desired configuration different from current, trying to set configuration`).
`kalam` does not, so OpenMTP alone can never connect straight after a replug.

### Fix

Switch the host-side selection to config `#1` once, then start OpenMTP:

```sh
scripts/nuxel-mtp-openmtp.sh          # diagnose, repair if needed
scripts/nuxel-mtp-openmtp.sh --app    # repair + launch the OpenMTP GUI
scripts/nuxel-mtp-openmtp.sh --status # report only, never touches USB
```

The switch is host-only (USB `SET_CONFIGURATION`). No phone-side change, no
reboot, and it survives for the life of the USB connection.

**Tradeoff:** config `#1` has no CDC-ACM, so `/dev/cu.usbmodem*` disappears
while OpenMTP is connected. The USB recovery console and OpenMTP file
transfer are mutually exclusive on macOS. SSH over Wi-Fi is unaffected.

### Verified 2026-11-01

| Check | Result |
|---|---|
| OpenMTP GUI → phone session | `session_open: true`, storage `65537 nuxel`, 18 objects |
| Phone → Mac (`mtp-getfile`, object 18) | sha256 `699b9927…b43dd` matches phone |
| Mac → phone (`mtp-sendfile`) | new object 19, sha256 `a09c3f92…e6bb6` matches phone |
| OpenMTP error log | empty |
| Failure reproduced | unplug/replug → config `#2` → `0xe00002c5` again |
| Helper repair | config `2` → `1`, engine claims device, exit 0 |

### Still open (phone-side, needs a deliberate gadget change)

The durable fix is on the Nuxel side: stop advertising the ACM+MTP composite
as a *separate higher-priority* configuration for macOS, either by making
config `#1` the default selection or by moving the console to a vendor
interface inside a single configuration. That would let OpenMTP connect with
no host-side workaround and keep the serial console at the same time. Not
changed in this run — `nuxel-usb-mode.sh` deliberately preserves ACM.
Also note `/run/nuxel/mtp-media.mounts: No such file or directory` at restore
time (line 154), which means Gallery/Pictures/Videos/Downloads bind mounts are
skipped on the first pass.
