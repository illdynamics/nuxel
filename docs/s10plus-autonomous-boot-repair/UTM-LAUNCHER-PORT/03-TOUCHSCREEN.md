# 03 — P0: THE TOUCHSCREEN

## 1. Root cause of the "touch never works" defect (found and fixed in A27, verified here)

The A23..A26 reader built its evdev requests by hand and put the wrong fields in
the wrong places:

```c
/* A26 (WRONG): 0x80200320 */
0x80000000u | (((u32)len)<<16) | (((u32)ev)<<8) | 0x20u
```

`_IOC(dir,type,nr,size) = dir<<30 | size<<16 | type<<8 | nr`, and every evdev
request is `_IOR('E', …)`, so `type` must be `'E' = 0x45` and `size` must carry
the buffer length. The A26 expression put the *event type* in the size field and
the padding byte in the nr field: `EVIOCGBIT(EV_ABS,32)` came out as
`0x80200320` instead of `0x80204523`. The ioctl failed, every device was
reported as "no multitouch", and the UI logged `TOUCH_POINTING_DEVICE_NONE`
even though `sec_touchscreen` was enumerating normally.

The fix (in `tools/s10plus/nuxel-ui.c`) encodes every request from the UAPI
definition and pins the result at **compile time**:

```c
#define EVIOCGNAME(len)   (0x80000000u|(((u32)(len))<<16)|(0x45u<<8)|0x06u)
#define EVIOCGBIT(ev,len) (0x80000000u|(((u32)(len))<<16)|(0x45u<<8)|(0x20u+(u32)(ev)))
#define EVIOCGABS(ax)     (0x80000000u|(24u<<16)|(0x45u<<8)|(0x40u+(u32)(ax)))
#define EVIOCGPROP(len)   (0x80000000u|(((u32)(len))<<16)|(0x45u<<8)|0x09u)
_Static_assert(EVIOCGBIT(EV_ABS,32)==0x80204523u, "…");
_Static_assert(EVIOCGABS(ABS_MT_POSITION_X)==0x80184575u, "…");
_Static_assert(EVIOCGABS(ABS_MT_POSITION_Y)==0x80184576u, "…");
_Static_assert(EVIOCGABS(ABS_X)==0x80184540u, "…");
_Static_assert(EVIOCGPROP(8)==0x80084509u, "…");
```

## 2. Independent ABI verification (A28)

`tools/s10plus/a28/evdev-abi-probe.c` is compiled for **aarch64** against the
real kernel headers and asserts the same numbers, plus the struct sizes the
event parser depends on:

```
$ aarch64-linux-gnu-gcc -c -o /dev/null tools/s10plus/a28/evdev-abi-probe.c
   PASS A28_ABI_PROBE_OK (EVIOCGBIT/EVIOCGABS/EVIOCGPROP + 24-byte input_event)
```

checked values: `EVIOCGBIT(EV_ABS,32)=0x80204523`, `EVIOCGABS(ABS_MT_POSITION_X)
=0x80184575`, `EVIOCGABS(ABS_MT_POSITION_Y)=0x80184576`, `EVIOCGABS(ABS_X)
=0x80184540`, `EVIOCGABS(ABS_Y)=0x80184541`, `EVIOCGPROP(8)=0x80084509`,
`sizeof(struct input_event)==24`, `sizeof(struct input_absinfo)==24`,
`ABS_MT_SLOT/ABS_MT_POSITION_X/ABS_MT_POSITION_Y/ABS_MT_TRACKING_ID/BTN_TOUCH`,
`INPUT_PROP_DIRECT==1`. The probe is part of the A28 gate, so a future edit that
breaks the ABI fails the build rather than the phone.

## 3. Device selection by capability (not by event number)

`input_scan()` enumerates `/dev/input/event*`, opens each node, and reads
`EVIOCGNAME`, `EVIOCGBIT(EV_ABS)`, `EVIOCGBIT(EV_KEY)`, `EVIOCGPROP`,
`EVIOCGABS(ABS_MT_POSITION_X/Y)`, `EVIOCGABS(ABS_MT_SLOT)`. `input_primary()`
then picks the panel touchscreen in this order:

1. a multitouch device with `INPUT_PROP_DIRECT`,
2. a multitouch device whose name contains "touch",
3. any multitouch device,
4. any `BTN_TOUCH` device with `INPUT_PROP_DIRECT`.

The event NUMBER is never assumed, and the axis ranges come from the device
(`d->minx/maxx/miny/maxy`), never from 0..1440 / 0..3040.

## 4. Event processing (Type B)

Per-slot state (`slot_on/slot_x/slot_y`, `cur_slot`, `primary_slot`) tracks
`ABS_MT_SLOT`, `ABS_MT_TRACKING_ID`, `ABS_MT_POSITION_X/Y` and `SYN_REPORT`;
`BTN_TOUCH` is used as the edge when the device reports it, and the SYN_REPORT
contact-set path is used when it does not (A27 fix). A release inside 12 design
px of the down point is a tap -> `hit_test()` -> `act_do()`; a larger vertical
move is a log scroll, a larger horizontal move changes page. `touch_map()`
rescales with the device's own range and applies `TOUCH_ORIENT` (0..3), which is
a runtime value (`orient N` on the console) because guessing it is the mistake
this code must not repeat. A non-blocking read that returns `-EAGAIN`/`-EINTR`
is not treated as a lost device (the A27 fix for "TOUCH_DEVICE_LOST every 3 s"),
and a genuine error triggers a capability re-scan.

## 5. What is still outstanding (honest)

* **A real finger has never been captured.** `docs/.../NEXT-ACTION.md` armed a
  900 s raw capture on `/dev/input/event2` (`/var/lib/nuxel/touch-raw.bin`) and
  it stayed 0 bytes. The capture, the decode helper
  (`tools/s10plus/a26/decode-touch.py`) and the `orient N` command all exist;
  what is missing is a human tapping the glass.
* The instrumented UI now writes a ready-to-read record at startup:
  `/var/lib/nuxel/ui-touch-ready` with
  `TOUCH_READY device=… name='sec_touchscreen' mt=1 direct=1 slots=N x=[min.max] y=[min.max] panel=1440x3040 orient=0`,
  so one `nuxel-live.sh --pull` after boot answers the axis-range question
  without a finger, and a `TOUCH_TAP x=… y=… act=…` line in `/var/lib/nuxel/ui-touch`
  will appear on the first real tap.
* If the controller reports a rotated frame, `orient 1|2|3` fixes it live and the
  value can then be baked into the default for the next build.
