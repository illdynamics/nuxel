#!/usr/bin/env bash
# nuxel-console-host.sh — drive the Nuxel S10+ live USB console from the Mac.
#
# The handset's CDC-ACM gadget ("Nuxel S10+ Live Console") appears as
# /dev/cu.usbmodem<N>.  It carries an interactive root shell AND a live mirror of
# the target's /dev/kmsg, so this is the fastest way to inspect a running Nuxel.
#
#   nuxel-console-host.sh --list
#   nuxel-console-host.sh --watch                 # stream the console (Ctrl-C to stop)
#   nuxel-console-host.sh --run 'systemctl --failed'
#   nuxel-console-host.sh --accept                # the mission's acceptance suite, with rc
#   nuxel-console-host.sh --say hello             # write one line to the target
#
# SAFETY RULE (measured on A21): never open()/close() /dev/fb0 from this or any other
# process while the panel is being observed.  fb_release DISABLES the DECON and only
# FBIOPUT_VSCREENINFO brings it back; a single `dd if=/dev/fb0` left 1279 pans failing.
# This script therefore never touches the framebuffer.
set -euo pipefail
PY=${PY:-python3}
DEV=""
while [ $# -gt 0 ]; do
  case "$1" in
    --list)  ls -1 /dev/cu.usbmodem* 2>/dev/null || echo "(no Nuxel console enumerated)"; exit 0 ;;
    --dev)   DEV="$2"; shift 2 ;;
    --watch) MODE=watch; shift ;;
    --run)   MODE=run; CMD="$2"; shift 2 ;;
    --accept) MODE=accept; shift ;;
    --say)   MODE=say; CMD="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$DEV" ] || DEV=$(ls -1 /dev/cu.usbmodem* 2>/dev/null | head -1)
[ -n "$DEV" ] || { echo "no /dev/cu.usbmodem* — is the phone running Nuxel?" >&2; exit 1; }
echo "# console $DEV"
exec "$PY" - "$DEV" "${MODE:-watch}" "${CMD:-}" <<'PYEOF'
import os, sys, termios, time, select
dev, mode, cmd = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd); a[0]=0; a[1]=0
a[2]=termios.CS8|termios.CREAD|termios.CLOCAL; a[3]=0; a[4]=9600; a[5]=9600
termios.tcsetattr(fd, termios.TCSANOW, a); termios.tcflush(fd, termios.TCIOFLUSH)
def drain(secs):
    out=b""; t0=time.time()
    while time.time()-t0 < secs:
        r,_,_ = select.select([fd],[],[],0.2)
        if r:
            try: c=os.read(fd,65536)
            except OSError: break
            if c: out+=c
    return out
def run(line, wait=2.5):
    os.write(fd, b"echo @@B@@\r"); time.sleep(0.3); drain(0.3)
    os.write(fd, line.encode()+b"\r"); time.sleep(wait)
    os.write(fd, b"echo @@rc=$?@@\r"); time.sleep(0.3)
    return drain(1.0).decode("utf-8","replace")
if mode == "watch":
    while True:
        sys.stdout.write(drain(0.5).decode("utf-8","replace")); sys.stdout.flush()
elif mode == "say":
    os.write(fd, cmd.encode()+b"\r"); time.sleep(0.5)
    sys.stdout.write(drain(2.0).decode("utf-8","replace"))
elif mode == "run":
    sys.stdout.write(run(cmd, 4.0))
elif mode == "accept":
    tests = [("uname -a",), ("id",), ("cat /etc/os-release | head -2",),
             ("systemctl --failed --no-pager --no-legend | wc -l",),
             ("false; echo rc-of-false=$?",),
             ("findmnt -no SOURCE,FSTYPE,OPTIONS /",),
             ("cat /var/lib/nuxel/animation",),
             ("cat /var/lib/nuxel/fb-anim.pid",),
             ("pgrep -a nuxel-fb-phone || echo NO_PENGUIN_PAINTER",),
             ("dmesg | grep -a NUXEL_ANIM_HEARTBEAT | tail -5",)]
    for (t,) in tests:
        print("\n##### %s" % t); sys.stdout.write(run(t)); sys.stdout.flush()
os.close(fd)
PYEOF
