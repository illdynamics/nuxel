#!/usr/bin/env python3
"""Send commands to the Nuxel live USB console and log everything it returns.

usage: console-cmd.py <outfile> <seconds> [command ...]
"""
import os, select, sys, termios, time

port = None
for p in ("/dev/cu.usbmodem201", "/dev/tty.usbmodem201"):
    if os.path.exists(p):
        port = p; break
if not port:
    import glob
    c = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/tty.usbmodem*"))
    port = c[0] if c else None
if not port:
    print("NO PORT"); sys.exit(1)

out = open(sys.argv[1], "ab", buffering=0)
secs = float(sys.argv[2])
cmds = sys.argv[3:] or ["echo READY"]
out.write(("\n=== console-cmd %s port=%s ===\n" % (time.strftime('%Y-%m-%dT%H:%M:%SZ'), port)).encode())

fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = termios.IGNPAR
a[1] = 0
a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL   # raw 8N1, explicitly NO hardware flow control
a[0] = termios.IGNPAR
a[3] = 0
a[4] = a[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, a)
termios.tcflush(fd, termios.TCIOFLUSH)

# A CDC-ACM gadget (Linux f_acm) only opens its port on the device side once the
# HOST asserts DTR (SET_CONTROL_LINE_STATE).  Without this the port stays "closed"
# in the gadget and everything the phone writes is discarded -- which is exactly
# what a silent console looks like.  macOS: TIOCMBIS=0x8004746c, TIOCM_DTR=0x2,
# TIOCM_RTS=0x4.
import fcntl, struct
TIOCMBIS = 0x8004746C
TIOCM_DTR = 0x0002
TIOCM_RTS = 0x0004
bits = struct.pack("i", TIOCM_DTR | TIOCM_RTS)
try:
    fcntl.ioctl(fd, TIOCMBIS, bits)
except Exception as e:
    print("DTRIOCTL", e)
# give the gadget a moment to see the line state change
time.sleep(1.0)

deadline = time.time() + secs
sent = False
while time.time() < deadline:
    r, _, _ = select.select([fd], [], [], 0.5)
    if r:
        try:
            d = os.read(fd, 65536)
        except OSError:
            break
        if d: out.write(d)
    if not sent and time.time() > deadline - secs + 2:
        for c in cmds:
            os.write(fd, (c + "\n").encode())
            time.sleep(1.2)
        sent = True
out.write(b"\n=== end ===\n")
print("PORT", port, flush=True)
