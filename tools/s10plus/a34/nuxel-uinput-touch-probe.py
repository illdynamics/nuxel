#!/usr/bin/env python3
"""nuxel-uinput-touch-probe — SYNTHETIC contact injector (diagnostic only).

Creates a virtual Type-B multitouch device via /dev/uinput and emits one tap or
vertical swipe.  It exists to prove or disprove the SOFTWARE path
    libinput -> phoc -> wl_touch -> WebKitGTK -> Nuxel Home
when no human finger is available.

IT IS NOT TOUCHSCREEN ACCEPTANCE.  Every line it prints carries SYNTHETIC=1 and
the result must never be promoted to T8/T9 in the evidence ladder.  The real
Samsung panel is /dev/input/event2 (sec_touchscreen); this device is a separate
virtual node and is destroyed before the process exits.

Usage:
  nuxel-uinput-touch-probe.py --tap 2048 2048
  nuxel-uinput-touch-probe.py --swipe 1800 2400 1800 900
  nuxel-uinput-touch-probe.py --tap 100 100 --hold-ms 150
"""
import argparse, fcntl, json, os, struct, sys, time

EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
SYN_REPORT = 0x00
BTN_TOUCH = 0x14a
ABS_X, ABS_Y = 0x00, 0x01
ABS_MT_SLOT, ABS_MT_TOUCH_MAJOR = 0x2f, 0x30
ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID = 0x35, 0x36, 0x39
INPUT_PROP_DIRECT = 0x01
BUS_VIRTUAL = 0x06
ABS_CNT = 64
UINPUT_MAX_NAME_SIZE = 80

def iow(nr, size=4):
    return (1 << 30) | (size << 16) | (ord('U') << 8) | nr
UI_SET_EVBIT  = iow(100)
UI_SET_KEYBIT = iow(101)
UI_SET_ABSBIT = iow(103)
UI_SET_PROPBIT= iow(110)
UI_DEV_CREATE = (ord('U') << 8) | 1
UI_DEV_DESTROY= (ord('U') << 8) | 2

def emit(fd, etype, code, value):
    os.write(fd, struct.pack('<qqHHi', 0, 0, etype, code, value))

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--tap', nargs=2, type=int, metavar=('X', 'Y'))
    g.add_argument('--swipe', nargs=4, type=int, metavar=('X1', 'Y1', 'X2', 'Y2'))
    ap.add_argument('--hold-ms', type=int, default=120)
    ap.add_argument('--steps', type=int, default=8)
    a = ap.parse_args()

    fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
    for ev in (EV_SYN, EV_KEY, EV_ABS): fcntl.ioctl(fd, UI_SET_EVBIT, ev)
    for key in (BTN_TOUCH,): fcntl.ioctl(fd, UI_SET_KEYBIT, key)
    for ab in (ABS_X, ABS_Y, ABS_MT_SLOT, ABS_MT_TOUCH_MAJOR,
               ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID):
        fcntl.ioctl(fd, UI_SET_ABSBIT, ab)
    fcntl.ioctl(fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT)

    name = b'nuxel-synthetic-touch'
    dev = struct.pack('<80sHHHHI', name, BUS_VIRTUAL, 0x4e58, 0x0001, 1, 0)
    absmax = [0]*ABS_CNT; absmin = [0]*ABS_CNT
    absmax[ABS_X] = absmax[ABS_Y] = 4095
    absmax[ABS_MT_POSITION_X] = absmax[ABS_MT_POSITION_Y] = 4095
    absmax[ABS_MT_SLOT] = 9
    absmax[ABS_MT_TRACKING_ID] = 65535
    absmax[ABS_MT_TOUCH_MAJOR] = 255
    dev += struct.pack('<%di' % ABS_CNT, *absmax)
    dev += struct.pack('<%di' % ABS_CNT, *absmin)
    dev += struct.pack('<%di' % ABS_CNT, *([0]*ABS_CNT))
    dev += struct.pack('<%di' % ABS_CNT, *([0]*ABS_CNT))
    os.write(fd, dev)
    fcntl.ioctl(fd, UI_DEV_CREATE)
    print('SYNTHETIC=1 DEVICE_CREATED name=%s node_hint=/dev/input/eventN' % name.decode())
    time.sleep(0.7)   # let the shim's inotify watcher add it

    if a.tap:
        x1, y1 = a.tap; pts = [(x1, y1)]
    else:
        x1, y1, x2, y2 = a.swipe
        pts = [(round(x1 + (x2-x1)*i/a.steps), round(y1 + (y2-y1)*i/a.steps))
               for i in range(a.steps+1)]

    emit(fd, EV_ABS, ABS_MT_SLOT, 0)
    emit(fd, EV_ABS, ABS_MT_TRACKING_ID, 1)
    for i, (x, y) in enumerate(pts):
        emit(fd, EV_ABS, ABS_MT_POSITION_X, x)
        emit(fd, EV_ABS, ABS_MT_POSITION_Y, y)
        emit(fd, EV_ABS, ABS_X, x)
        emit(fd, EV_ABS, ABS_Y, y)
        emit(fd, EV_ABS, ABS_MT_TOUCH_MAJOR, 8)
        if i == 0:
            emit(fd, EV_KEY, BTN_TOUCH, 1)
        emit(fd, EV_SYN, SYN_REPORT, 0)
        print('SYNTHETIC=1 EVENT kind=%s x=%d y=%d' %
              ('down' if i == 0 else 'move', x, y))
        time.sleep(0.03)
    time.sleep(max(0, a.hold_ms)/1000.0)
    emit(fd, EV_ABS, ABS_MT_TRACKING_ID, -1)
    emit(fd, EV_KEY, BTN_TOUCH, 0)
    emit(fd, EV_SYN, SYN_REPORT, 0)
    print('SYNTHETIC=1 EVENT kind=up x=%d y=%d' % pts[-1])
    time.sleep(0.2)
    fcntl.ioctl(fd, UI_DEV_DESTROY)
    os.close(fd)
    print('SYNTHETIC=1 DEVICE_DESTROYED')
    return 0

if __name__ == '__main__':
    sys.exit(main())
