#!/usr/bin/env python3
"""Nuxel S10+ touchscreen capture (cycle A29).

WHY THIS EXISTS
  A23..A28 never captured a single finger.  A29 found the reason in the driver
  source (Linux4/android_kernel_samsung_exynos9820, drivers/input/touchscreen/
  sec_ts/y771/sec_ts.c): probe leaves `ts->power_status = SEC_TS_STATE_POWER_ON`,
  and sec_ts_start_device() then takes

      if (ts->power_status == SEC_TS_STATE_POWER_ON) {
              input_err(... "%s: already power on\n", __func__);
              goto out;                       /* ret stays -1            */
      }

  so it skips sec_ts_wait_for_ready(), sec_ts_reinit(), SEC_TS_CMD_SENSE_ON and
  - decisive - enable_irq().  sec_ts_input_open() still *returns 0*, so open(2)
  succeeds and userspace never sees an error: the IRQ simply never fires.
  Measured on the running phone (dmesg):
      sec_ts 4-0048: sec_ts_start_device
      sec_ts 4-0048: sec_ts_start_device: already power on
      sec_ts 4-0048: sec_ts_input_open: Failed to start device

  sec_ts_input_close() -> sec_ts_stop_device() sets POWER_OFF + disable_irq(),
  so an open->close->open cycle re-arms the controller (the second open runs the
  real start path).  This tool performs exactly that, then reads raw events.

NO GUESSING: axis ranges, slot count, DIRECT property and the device node all
come from the kernel (EVIOCG*), never from event numbers or 0..1440/0..3040.

Usage:
  touch-capture.py [--seconds N] [--out FILE] [--node /dev/input/eventN] [--raw FILE]
"""
import argparse, errno, fcntl, os, select, struct, sys, time

EVIOCGNAME_LEN = 0x80084506 | (64 << 16) if False else (0x80000000 | (64 << 16) | (0x45 << 8) | 0x06)
EVIOCGBIT = lambda ev, ln: 0x80000000 | (ln << 16) | (0x45 << 8) | (0x20 + ev)
EVIOCGABS = lambda ax: 0x80000000 | (24 << 16) | (0x45 << 8) | (0x40 + ax)
EVIOCGPROP = lambda ln: 0x80000000 | (ln << 16) | (0x45 << 8) | 0x09

EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
ABS_MT_SLOT, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID = 0x2F, 0x35, 0x36, 0x39
BTN_TOUCH = 0x14A
INPUT_PROP_DIRECT = 1
EV_FMT = "llHHi"           # struct input_event (64-bit): 24 bytes
EV_SIZE = struct.calcsize(EV_FMT)

def log(fh, msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    fh.write(line + "\n"); fh.flush()

def dev_name(fd):
    try:
        return fcntl.ioctl(fd, EVIOCGNAME_LEN, b"\0" * 64).split(b"\0")[0].decode("utf-8", "replace")
    except OSError:
        return "?"

def bit(bits, code):
    return (bits[code // 8] >> (code % 8)) & 1

def caps(fd):
    d = {}
    d["name"] = dev_name(fd)
    absb = bytearray(fcntl.ioctl(fd, EVIOCGBIT(EV_ABS, 8), b"\0" * 8))
    keyb = bytearray(fcntl.ioctl(fd, EVIOCGBIT(EV_KEY, 12), b"\0" * 12))
    prop = bytearray(fcntl.ioctl(fd, EVIOCGPROP(8), b"\0" * 8))
    d["mt"] = bool(bit(absb, ABS_MT_POSITION_X) and bit(absb, ABS_MT_POSITION_Y))
    d["btn"] = bool(bit(keyb, BTN_TOUCH))
    d["direct"] = bool(bit(prop, INPUT_PROP_DIRECT))
    for key, ax in (("x", ABS_MT_POSITION_X), ("y", ABS_MT_POSITION_Y), ("slot", ABS_MT_SLOT)):
        try:
            v = struct.unpack("6i", fcntl.ioctl(fd, EVIOCGABS(ax), b"\0" * 24))
            d[key] = (v[1], v[2])       # minimum, maximum
        except OSError:
            d[key] = None
    return d

def arm(path, fh):
    """open -> close -> open: sec_ts_input_close() runs sec_ts_stop_device()
    (POWER_OFF + disable_irq), so the second open runs the real start path."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    os.close(fd)
    time.sleep(0.05)
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    return fd

def tsp_status():
    try:
        return open("/sys/class/sec/tsp/status").read().strip()
    except OSError as e:
        return "unavailable (%s)" % e

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--out", default="/var/lib/nuxel/touch-capture.log")
    ap.add_argument("--node", default="")
    ap.add_argument("--raw", default="")
    a = ap.parse_args()
    fh = open(a.out, "a", buffering=1)

    cand = []
    for ev in sorted(os.listdir("/dev/input")):
        if not ev.startswith("event"):
            continue
        p = "/dev/input/" + ev
        try:
            fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            continue
        try:
            c = caps(fd); c["path"] = p; c["ev"] = ev
            cand.append(c)
        finally:
            os.close(fd)

    log(fh, "SCAN devices=%d" % len(cand))
    for c in cand:
        log(fh, "DEV %-18s name=%-18s mt=%d direct=%d btn=%d slots=%s x=%s y=%s" % (
            c["path"], c["name"][:18], c["mt"], c["direct"], c["btn"], c["slot"], c["x"], c["y"]))

    if a.node:
        target = [c for c in cand if c["path"] == a.node]
    else:
        # capability-first: a DIRECT multitouch panel, then a name match.
        target = ([c for c in cand if c["mt"] and c["direct"]] or
                  [c for c in cand if c["mt"] and "touchscreen" in c["name"].lower()] or
                  [c for c in cand if c["mt"]])
    if not target:
        log(fh, "NO_TOUCHSCREEN"); return 3
    t = target[0]
    log(fh, "TARGET %s name=%s mt=%d direct=%d slots=%s x=%s y=%s" % (
        t["path"], t["name"], t["mt"], t["direct"], t["slot"], t["x"], t["y"]))
    log(fh, "TSP_STATUS_BEFORE %s" % tsp_status())

    raw = open(a.raw, "wb") if a.raw else None
    fds = {}
    for c in target:
        try:
            fds[arm(c["path"], fh)] = c
        except OSError as e:
            log(fh, "ARM_FAIL %s errno=%d (%s)" % (c["path"], e.errno, errno.errorcode.get(e.errno)))
    if not fds:
        log(fh, "ARM_FAILED_ALL"); return 4

    slot_x, slot_y, slot_on = {}, {}, {}
    cur, taps, ev_count = 0, 0, 0
    down = None
    t0 = time.time()
    log(fh, "READY seconds=%g fds=%d" % (a.seconds, len(fds)))
    while time.time() - t0 < a.seconds:
        r, _, _ = select.select(list(fds), [], [], 0.5)
        for fd in r:
            try:
                data = os.read(fd, EV_SIZE * 64)
            except OSError as e:
                log(fh, "READ_ERR %s errno=%d" % (fds[fd]["path"], e.errno)); continue
            if raw:
                raw.write(data); raw.flush()
            for off in range(0, len(data) - EV_SIZE + 1, EV_SIZE):
                _, _, typ, code, val = struct.unpack_from(EV_FMT, data, off)
                ev_count += 1
                if typ == EV_ABS and code == ABS_MT_SLOT:
                    cur = val
                elif typ == EV_ABS and code == ABS_MT_TRACKING_ID:
                    if val >= 0:
                        slot_on[cur] = True
                        log(fh, "TOUCH_DOWN slot=%d" % cur)
                    else:
                        slot_on.pop(cur, None)
                        log(fh, "TOUCH_UP slot=%d" % cur)
                elif typ == EV_ABS and code == ABS_MT_POSITION_X:
                    slot_x[cur] = val
                elif typ == EV_ABS and code == ABS_MT_POSITION_Y:
                    slot_y[cur] = val
                elif typ == EV_KEY and code == BTN_TOUCH:
                    log(fh, "BTN_TOUCH=%d" % val)
                elif typ == EV_SYN and code == 0:
                    for s in slot_on:
                        if s in slot_x and s in slot_y:
                            if down is None:
                                down = (slot_x[s], slot_y[s])
                            log(fh, "TOUCH_POINT slot=%d raw=(%d,%d)" % (s, slot_x[s], slot_y[s]))
                            taps += 1
                    if not slot_on and down is not None:
                        log(fh, "TOUCH_RELEASE last_down=%s" % (down,)); down = None
    log(fh, "DONE events=%d points=%d tsp_status=%s" % (ev_count, taps, tsp_status()))
    for fd in fds:
        os.close(fd)
    return 0

sys.exit(main())
