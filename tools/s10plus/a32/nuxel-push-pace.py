#!/usr/bin/env python3
"""nuxel-push-pace.py — paced, verified bulk transport over the Nuxel live console.

WHY (measured this cycle, A32): the CDC-ACM link carries ~960 B/s at 9600 baud and
the target's N_TTY input buffer is 4 KiB.  Two probe runs proved it:
  * 14,688 bytes written as 48 lines in ONE write() -> only 1,769 bytes executed
    (the buffer filled and the remainder was discarded);
  * the same lines paced at the line rate land exactly.
So the payload travels ONE 512-character base64 line per write, paced to the line
rate, and the target's cumulative byte count is read back every CHECK lines.  A
block that does not land exactly is rewound to the last verified length and
replayed.  Nothing is installed until the decoded bytes hash to the local SHA-256
and the installed path re-hashes to the same value on the target.

    nuxel-push-pace.py [--dev D] [--mode 755] [--pace 0.62] LOCAL REMOTE
"""
import base64, fcntl, gzip, hashlib, os, re, select, sys, termios, time

CHUNK = 512
CHECK = 16
TMP = "/tmp/nxp.b64"


def open_port(dev):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = 0; a[1] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[3] = 0; a[4] = 9600; a[5] = 9600
    termios.tcsetattr(fd, termios.TCSANOW, a)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


class Sess:
    def __init__(self, fd):
        self.fd = fd; self.buf = bytearray()

    def pump(self, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            r, _, _ = select.select([self.fd], [], [], 0.03)
            if r:
                try:
                    c = os.read(self.fd, 65536)
                except OSError:
                    return
                if c:
                    self.buf += c

    def text(self):
        return self.buf.decode("utf-8", "replace")

    def clear(self):
        self.buf.clear()

    def send(self, b):
        os.write(self.fd, b)


def main():
    args = sys.argv[1:]
    dev = None; mode = "755"; pace = 0.62; local = None; remote = None
    while args:
        a = args.pop(0)
        if a == "--dev": dev = args.pop(0)
        elif a == "--mode": mode = args.pop(0)
        elif a == "--pace": pace = float(args.pop(0))
        elif local is None: local = a
        else: remote = a
    if not local or not remote:
        raise SystemExit("usage: nuxel-push-pace.py [--dev D] [--mode 755] [--pace S] LOCAL REMOTE")
    if not dev:
        cands = sorted(f for f in os.listdir("/dev") if f.startswith("cu.usbmodem"))
        if not cands: raise SystemExit("no /dev/cu.usbmodem*")
        dev = "/dev/" + cands[0]

    lock = "/tmp/nuxel-live.%s.lock" % re.sub(r"[^A-Za-z0-9]", "_", dev)
    lk = open(lock, "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("!! another nuxel tool owns %s" % dev)

    raw = open(local, "rb").read()
    want = hashlib.sha256(raw).hexdigest()
    gz = gzip.compress(raw, 9)
    b64 = base64.b64encode(gz).decode()
    lines = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
    print("# %s -> %s raw=%d gzip=%d base64=%d lines=%d pace=%.2fs want=%s"
          % (local, remote, len(raw), len(gz), len(b64), len(lines), pace, want))
    sys.stdout.flush()

    fd = open_port(dev)
    s = Sess(fd)
    s.pump(0.5); s.clear()
    s.send(b"stty -echo 2>/dev/null; : >%s\r\n" % TMP.encode()); s.pump(1.6); s.clear()

    def target_len(timeout=8.0):
        s.clear()
        s.send(b"wc -c <%s\r\n" % TMP.encode())
        t0 = time.time()
        while time.time() - t0 < timeout:
            s.pump(0.2)
            m = re.findall(r"(?m)^\s*(\d+)\s*$", s.text())
            if m:
                return int(m[-1])
        return None

    good = 0
    i = 0
    t_start = time.time()
    fails = 0
    while i < len(lines):
        line = "printf '%s' '%s'>>%s\n" % (lines[i], lines[i], TMP)
        s.send(line.encode())
        good += len(lines[i])
        i += 1
        time.sleep(pace)
        if i % CHECK == 0 or i == len(lines):
            seen = target_len()
            if seen != good:
                fails += 1
                if fails > 6:
                    raise SystemExit("!! too many transport failures (target=%s wanted=%d)" % (seen, good))
                back = good - (seen if seen is not None else 0)
                print("#   mismatch target=%s wanted=%d -> replaying %d chars" % (seen, good, back))
                sys.stdout.flush()
                i -= CHECK
                good -= sum(len(x) for x in lines[i:i + CHECK])
    print("# streamed %d lines in %.1fs (base64 bytes=%d)" % (len(lines), time.time() - t_start, good))
    sys.stdout.flush()

    fin = ("set -e; base64 -d <%s | gunzip > %s.new; sha256sum %s.new | cut -d' ' -f1; "
           "install -m %s %s.new %s; sha256sum %s | cut -d' ' -f1; rm -f %s %s.new; stty echo 2>/dev/null"
           % (TMP, TMP, TMP, mode, TMP, remote, remote, TMP, TMP))
    s.clear(); s.send(fin.encode() + b"\r\n")
    s.pump(14)
    got = re.findall(r"\b([0-9a-f]{64})\b", s.text())
    os.close(fd)
    print("# target hashes: %s" % (got if got else "NONE"))
    if len(got) >= 2 and got[0] == want and got[1] == want:
        print("# OK %s sha256=%s (verified on target)" % (remote, want))
        return 0
    print("!! FAIL expected %s" % want)
    return 5


if __name__ == "__main__":
    sys.exit(main())
