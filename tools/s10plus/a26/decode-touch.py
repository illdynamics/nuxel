#!/usr/bin/env python3
"""Decode a raw /dev/input/eventN capture from the S10+ touchscreen.

struct input_event on arm64 Linux 4.14 is 24 bytes: timeval (2 x 8) + u16 type +
u16 code + s32 value.  The S10+ sec_touchscreen is a TYPE_B multitouch device, so
a "tap" is ABS_MT_TRACKING_ID .. ABS_MT_POSITION_X/Y .. SYN_REPORT, then
ABS_MT_TRACKING_ID = -1 for the release.

Usage: decode-touch.py touch-raw.bin [--range]
"""
import struct, sys, collections

EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
SYN_REPORT = 0
ABS_MT_SLOT, ABS_MT_TOUCH_MAJOR, ABS_MT_POSITION_X, ABS_MT_POSITION_Y = 0x2f, 0x30, 0x35, 0x36
ABS_MT_TRACKING_ID = 0x39
ABS_X, ABS_Y = 0x00, 0x01
BTN_TOUCH = 0x14a
NAMES = {ABS_MT_SLOT: "SLOT", ABS_MT_POSITION_X: "MT_X", ABS_MT_POSITION_Y: "MT_Y",
         ABS_MT_TRACKING_ID: "TRACK_ID", ABS_MT_TOUCH_MAJOR: "TOUCH_MAJOR",
         ABS_X: "X", ABS_Y: "Y", BTN_TOUCH: "BTN_TOUCH"}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/var/lib/nuxel/touch-raw.bin"
    d = open(path, "rb").read()
    print("capture %s : %d bytes = %d events" % (path, len(d), len(d) // 24))
    if len(d) < 24:
        print("NO EVENTS YET — nothing has touched the glass in this window.")
        return 1
    ev = [struct.unpack_from("<qqHHi", d, o) for o in range(0, len(d) - 23, 24)]
    xs, ys, ids = [], [], set()
    cur = {}
    frames = 0
    for ts, tu, t, c, v in ev:
        if t == EV_ABS:
            if c in (ABS_MT_POSITION_X, ABS_X):
                xs.append(v); cur["x"] = v
            elif c in (ABS_MT_POSITION_Y, ABS_Y):
                ys.append(v); cur["y"] = v
            elif c == ABS_MT_TRACKING_ID:
                ids.add(v); cur["id"] = v
                print("  %6d.%06d TRACKING_ID %d" % (ts, tu, v))
                if v == -1 and "x" in cur and "y" in cur:
                    print("    -> release at (%d, %d)" % (cur["x"], cur["y"]))
        elif t == EV_KEY and c == BTN_TOUCH:
            print("  %6d.%06d BTN_TOUCH %d %s" % (ts, tu, v, "DOWN" if v else "UP"))
        elif t == EV_SYN and c == SYN_REPORT:
            frames += 1
            if "id" in cur and cur["id"] != -1:
                print("    frame %d touch id=%d at (%s, %s)"
                      % (frames, cur["id"], cur.get("x"), cur.get("y")))
    print("---- summary ----")
    print("SYN_REPORT frames      : %d" % frames)
    print("distinct tracking ids  : %s" % sorted(ids))
    if xs:
        print("X observed range       : %d .. %d" % (min(xs), max(xs)))
        print("Y observed range       : %d .. %d" % (min(ys), max(ys)))
    print("NOTE: derive the scaling from these observed ranges; do not assume "
          "0..1440 / 0..3040.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
