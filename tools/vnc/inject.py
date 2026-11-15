"""Inject real input events into the phone's input devices.

Touch is written straight to the physical sec_touchscreen node (event2) so the
compositor and WebKit process it exactly like a finger.  Mouse/keyboard can
alternatively go through ydotool on the session's virtual seat.
"""
import os
import struct
import time

EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
ABS_MT_SLOT, ABS_MT_TRACKING_ID = 0x2f, 0x39
ABS_MT_POSITION_X, ABS_MT_POSITION_Y = 0x35, 0x36
ABS_X, ABS_Y = 0, 1
SYN_REPORT = 0


class Touch:
    def __init__(self, path='/dev/input/event2'):
        self.fd = os.open(path, os.O_WRONLY)

    def _event(self, typ, code, val):
        body = struct.pack('<HHi', typ, code, int(val))
        # input_event: timeval(16) + type + code + value
        os.write(self.fd, b'\x00' * 16 + body)

    def _syn(self):
        self._event(EV_SYN, SYN_REPORT, 0)

    def down(self, x, y, slot=0):
        self._event(EV_ABS, ABS_MT_SLOT, slot)
        self._event(EV_ABS, ABS_MT_TRACKING_ID, 10 + slot)
        self._event(EV_ABS, ABS_MT_POSITION_X, x)
        self._event(EV_ABS, ABS_MT_POSITION_Y, y)
        self._event(EV_ABS, ABS_X, x)
        self._event(EV_ABS, ABS_Y, y)
        self._syn()

    def move(self, x, y, slot=0):
        self._event(EV_ABS, ABS_MT_SLOT, slot)
        self._event(EV_ABS, ABS_MT_POSITION_X, x)
        self._event(EV_ABS, ABS_MT_POSITION_Y, y)
        self._event(EV_ABS, ABS_X, x)
        self._event(EV_ABS, ABS_Y, y)
        self._syn()

    def up(self, slot=0):
        self._event(EV_ABS, ABS_MT_SLOT, slot)
        self._event(EV_ABS, ABS_MT_TRACKING_ID, -1)
        self._syn()

    def tap(self, x, y, hold=0.06):
        self.down(x, y)
        time.sleep(hold)
        self.up()

    def swipe(self, x0, y0, x1, y1, steps=16, delay=0.012, hold=0.05):
        self.down(x0, y0)
        time.sleep(hold)
        for i in range(1, steps + 1):
            self.move(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
            time.sleep(delay)
        time.sleep(0.03)
        self.up()
