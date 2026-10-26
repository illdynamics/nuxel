# NUXEL A72 / 21000 — 07-BLUETOOTH / USB-AUDIO (live, after bluez install)

## Bluetooth (BlueZ installed; HCI still absent)
- `dnf5 install bluez` → bluez 5.87+git (signed, Fedora 43 aarch64). dbus-org.bluez
  + bluetooth.service symlinks created.
- `bluetoothctl list` → empty. `/dev/hci*` → absent.
- `rfkill`: `bluetooth` soft=1 hard=0 (soft-blocked); `wlan` soft=0 hard=0.
- Boot journal: `Bluetooth: Core ver 2.22`, `[BT] bcm43xx_bluetooth_probe.` /
  `[BT] bcm43xx_bluetooth_probe End` — the Samsung BCM43xx driver probed but
  **never registered hci0** and issued no firmware request.

Verdict: BlueZ is now present (userspace dependency resolved), but there is no
HCI controller exposed by the 4.14 kernel/transport. Status:
**BLOCKED_FIRMWARE/DRIVER** (BCM43xx HCD/transport bring-up), NOT merely a
missing BlueZ package. Unblocking rfkill alone will not register an HCI without
the controller firmware/transport path; not attempted without an owner-supplied,
license-verified HCD.

## USB-C audio / headset
- No digital USB-C DAC or active adapter accessory is attached (the USB port
  carries the recovery Live Console). `BLOCKED_EQUIPMENT` — unchanged, and the
  sole recovery transport was never switched to test a host role.
