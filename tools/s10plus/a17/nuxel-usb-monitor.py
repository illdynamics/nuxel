#!/usr/bin/env python3
"""Watch the Mac for the Nuxel live USB console and log everything it emits.

Waits for a new /dev/{cu,tty}.usbmodem* node, opens it raw at 115200 8N1, logs
all bytes to <outdir>/usb-console.log and optionally injects a command list.
"""
import glob, os, select, sys, termios, time, subprocess

outdir = sys.argv[1] if len(sys.argv) > 1 else "."
deadline = time.time() + float(sys.argv[2] if len(sys.argv) > 2 else 900)
cmds = sys.argv[3:] if len(sys.argv) > 3 else []

before = set(glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*'))
log = open(os.path.join(outdir, 'usb-console.log'), 'ab', buffering=0)
log.write(b"\n=== nuxel-usb-monitor start %s ===\n" % time.strftime('%Y-%m-%dT%H:%M:%SZ').encode())

port = None
while time.time() < deadline:
    now = set(glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*'))
    new = sorted(p for p in now if p.startswith('/dev/cu.') or p not in before)
    if new:
        port = new[0]
        break
    time.sleep(1)

if not port:
    log.write(b"=== no usbmodem device appeared within the window ===\n")
    print("NO_PORT")
    sys.exit(1)

log.write(("=== port %s ===\n" % port).encode())
print("PORT", port, flush=True)

fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
attrs = termios.tcgetattr(fd)
iflag, oflag, cflag, lflag, ispeed, ospeed, cc = attrs
cflag &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
cflag |= termios.CS8 | termios.CREAD | termios.CLOCAL
iflag = termios.IGNPAR
oflag = 0
lflag = 0
attrs = [iflag, oflag, cflag, lflag, termios.B115200, termios.B115200, cc]
termios.tcsetattr(fd, termios.TCSANOW, attrs)
termios.tcflush(fd, termios.TCIOFLUSH)

sent = False
while time.time() < deadline:
    r, _, _ = select.select([fd], [], [], 5)
    if r:
        try:
            data = os.read(fd, 65536)
        except OSError:
            break
        if data:
            log.write(data)
    if not sent and time.time() < deadline:
        # give the phone a moment to be ready, then ask for state
        time.sleep(3)
        for c in (cmds or ["uname -a", "cat /var/lib/nuxel/boot-stage",
                           "systemctl is-system-running",
                           "systemctl --failed --no-pager | head -40"]):
            os.write(fd, (c + "\n").encode())
            time.sleep(1.5)
        sent = True
log.write(b"\n=== nuxel-usb-monitor end ===\n")
print("DONE", flush=True)
