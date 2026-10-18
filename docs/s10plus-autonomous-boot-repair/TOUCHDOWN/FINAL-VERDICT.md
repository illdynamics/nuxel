# FINAL VERDICT — A34 (interim, pending owner tests)

## Touchscreen

**TOUCHSCREEN_READY_FOR_OWNER_TEST**

* T1 driver: PASS
* T2 IRQ: PASS (count 146 at 10:38:22Z; real increments)
* T3 raw evdev: PASS (67 records at the first capture, 106 by 10:25:39Z)
* T4 libinput: PASS (event2 accepted, seat0)
* T5 Phoc: PASS (holds event2; forwarded contact)
* T6 WebKit: PASS (pointerdown + touchstart at 10:13:01Z)
* T7 handler: PASS (`app:launch id=org.nuxel.Mail`)
* T8 action: PASS twice (Mail at 10:13:01Z, Calendar at 10:23:39Z; both rendered)
* T9 owner normal use: **PENDING** (Test B)

The engine is not allowed to promote this to `TOUCHSCREEN_VERIFIED` until the
owner confirms normal taps, swipes and app interaction.

## GUI / presentation

**WORKING IN THE CURRENT STATE.** Frame counter 23.67 fps, failures 0; Home
rendered after a service restart; a physical tap produced a visible Mail app;
volume OSD appeared within 2 s without a Power press. The "frozen" experience
was a fullscreen, almost-empty app iframe plus the small close button, not a
dead compositor. Cold-boot persistence is still to be tested.

## Power button

**FIXED IN SOFTWARE / OWNER TEST PENDING.** The A34 manager fixes the spurious
touch `back`, and A34 now cancels a pending deferred Bixby short when Power is
pressed (deterministic regression passes). Screen-off now reaches `bl_power=4`
and screen-on restores in one FIFO cycle. Physical Power acceptance (Test C)
is still required.

## USB keyboard / mouse

**UNPROVEN.** The phone is currently a USB device (console gadget). Type-C
advertising is dual-role, but xHCI is not bound and no writable role switch is
exposed. The adapter/keyboard test has not been performed. This does not affect
the built-in touchscreen verdict.

## Forbidden operations

No flash, raw partition write, bootloader change, TWRP/Download Mode entry,
modem/EFS write, device-tree rewrite or `dnf upgrade` was performed.
