# USB KEYBOARD TESTS — A34

Status: **NOT TESTED PHYSICALLY** (requires the owner to unplug the console
cable; no live host-mode switch is exposed, see `USB-C-HOST-CAPABILITY.md`).

## Equipment / preconditions

* Keychron keyboard must be in **wired USB mode** (not Bluetooth, not a
  charge-only cable).
* Use a data-capable USB-C cable or a known-good C-to-A adapter.
* The phone's single port must leave gadget/device mode for the keyboard to
  enumerate as a host-connected HID device.

## What will be recorded

* `dmesg` for `Turn On Host(DFP)`, `xhci-hcd`, `usb 1-1` enumeration.
* `/sys/bus/usb/devices/*/idVendor`, `idProduct`, `product`.
* `hid` binding and a new `/dev/input/eventN` with `EV_KEY`.
* `nuxel-button-manager --capture` / `nuxel-touch-trace` key events.
* libinput/Phoc delivery and WebKit `keydown` if a text field is focused.

## Verdict

**UNPROVEN.** Do not claim keyboard support from `/dev/input` existence or from
a keyboard that is merely charging.
