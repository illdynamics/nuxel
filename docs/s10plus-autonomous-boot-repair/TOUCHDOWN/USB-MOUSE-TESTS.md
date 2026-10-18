# USB MOUSE TESTS — A34

Status: **NOT TESTED PHYSICALLY** (same single-port constraint).

## Equipment / preconditions

* Standard USB-A mouse through a USB-A-female to USB-C-male adapter.
* The adapter must be a data adapter, not a charge-only adapter.
* The phone must enter host/DFP mode; see the read-only audit.

## What will be recorded

* `dmesg` role-switch and xHCI lines.
* USB VID/PID/product and HID driver binding.
* `EV_REL REL_X/REL_Y`, `BTN_LEFT`, `BTN_RIGHT` from the new event node.
* libinput seat assignment and Phoc pointer delivery.
* WebKit `pointermove`/`pointerdown` and an actual app activation.

## Verdict

**UNPROVEN.** `/dev/input/mice` alone is not evidence.
