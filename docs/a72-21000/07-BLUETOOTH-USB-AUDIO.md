# NUXEL A72 / 21000 — 07-BLUETOOTH-USB-AUDIO

## Bluetooth (A69-07)
- DT `bluetooth` node `samsung,bcm43xx`, status=okay.
- Boot journal: `Bluetooth: Core ver 2.22` initialized; `[BT] bcm43xx_bluetooth_probe.`
  and `probe End`; but NO `hci0` registered. rfkill0 `bcm43xx Bluetooth` soft=1 hard=0.
- No BlueZ (`bluetoothctl`/`btmgmt` absent), no BCM43xx `.hcd` firmware under /lib/firmware.
- Distinction: BlueZ install (userspace) ≠ HCI hardware (driver+firmware). Even with
  BlueZ installed, the adapter won't power on until the BCM43xx HCD firmware loads and
  rfkill is unblocked (an RF behavior change requiring owner approval).

## USB-C audio (A69-08)
- Digital USB-C DAC/headset: requires host-role enumeration + `snd-usb-audio`. Not
  exercised — the USB port carries the recovery Live Console and no DAC accessory exists.
- Passive analog USB-C adapter: requires analog accessory-mode mux (cannot be fixed by
  installing a driver). Classified UNSUPPORTED_ACCESSORY until hardware is present.
- Native 3.5 mm jack: `madera-extcon` headset detect present; independent of USB-C.

## Route plan (after dnf5 + audio server + accessory)
1. BlueZ + WirePlumber bluez5 endpoint (needs HCD firmware + unblock, owner-approve).
2. `snd-usb-audio` DAC hotplug + auto-route + return-to-speaker on unplug.
3. Per-route safe volume; never switch USB role over the only recovery console.
