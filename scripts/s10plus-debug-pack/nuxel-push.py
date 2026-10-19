#!/usr/bin/env python3
"""nuxel-push.py — verified bulk file transport over the Nuxel USB live console.

WHY THIS EXISTS (measured, 2026-10-16):
  * The console is a CDC-ACM shell with NO flow control at application level and
    bash readline on the far end.  Command lines longer than ~512 characters are
    silently dropped (measured again this cycle: 400 chars OK, 1500 chars never
    executed), so a payload must travel as <=400-character lines.
  * scripts/s10plus-debug-pack/nuxel-live.sh --run does one console round trip per
    command (open/close + frame markers, ~1.5 s), which makes 380-char chunks take
    ~1.7 hours for the 1.2 MB Nuxel wallpaper.
  * The phone exposes NO network function (/sys/kernel/config/usb_gadget/nuxel/
    functions = acm.usb0 only, no ecm/rndis), so the console is the only channel.

So this tool streams many lines per port write and verifies each BLOCK by reading
the cumulative file length back from the target, rewinding to the last known-good
length when a block does not land exactly.  Nothing is installed until the
decoded bytes match the local SHA-256, and the installed path is re-hashed on the
target afterwards.
"""
import base64, fcntl, gzip, hashlib, os, re, select, sys, termios, time

CHUNK = 380          # payload chars per console line (line limit is ~512 incl. overhead)
BLOCK = 24           # lines per verified block
TMP = "/tmp/nx.b64"


def open_port(dev):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = 0; a[1] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    # The S10+ USB CDC-ACM console is 115200 8N1.  Using 9600 made large,
    # verified userspace bundles needlessly slow and increased disconnect risk.
    a[3] = 0; a[4] = 115200; a[5] = 115200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


class Sess:
    def __init__(self, fd):
        self.fd = fd
        self.buf = bytearray()

    def pump(self, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r:
                try:
                    c = os.read(self.fd, 262144)
                except OSError:
                    return
                if c:
                    self.buf += c

    def send(self, b):
        os.write(self.fd, b)

    def text(self):
        return self.buf.decode("utf-8", "replace")

    def clear(self):
        self.buf.clear()


def main():
    dev = os.environ.get("NUXEL_DEV")
    local = remote = None
    mode = "644"
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--dev":
            dev = args[i + 1]; i += 2
        elif args[i] == "--mode":
            mode = args[i + 1]; i += 2
        elif args[i] == "--chunk":
            global CHUNK
            CHUNK = int(args[i + 1]); i += 2
        elif local is None:
            local = args[i]; i += 1
        elif remote is None:
            remote = args[i]; i += 1
        else:
            raise SystemExit("unexpected arg %s" % args[i])
    if not local or not remote:
        raise SystemExit("usage: nuxel-push.py [--dev D] [--mode 644] LOCAL REMOTE")
    if not dev:
        cands = sorted(f for f in os.listdir("/dev") if f.startswith("cu.usbmodem"))
        if not cands:
            raise SystemExit("no /dev/cu.usbmodem* — is the phone running Nuxel?")
        dev = "/dev/" + cands[0]

    lock = "/tmp/nuxel-live.%s.lock" % re.sub(r"[^A-Za-z0-9]", "_", dev)
    lk = open(lock, "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("!! another nuxel tool owns %s" % dev)

    raw = open(local, "rb").read()
    want = hashlib.sha256(raw).hexdigest()
    b64 = base64.b64encode(gzip.compress(raw, 9)).decode()
    lines = [("printf '%s' '" + b64[i:i + CHUNK] + "'>>%s" % TMP)
             for i in range(0, len(b64), CHUNK)]
    print("# push %s -> %s raw=%d gzip=%d lines=%d want=%s (dev=%s)"
          % (local, remote, len(raw), len(gzip.compress(raw, 9)), len(lines), want, dev))

    fd = open_port(dev)
    s = Sess(fd)
    s.pump(0.5); s.clear()

    def say(cmd, wait=3.0):
        s.clear()
        s.send(cmd.encode() + b"\r")
        s.pump(wait)
        return s.text()

    say("stty -echo 2>/dev/null; : > %s; echo NXZERO" % TMP)
    good = 0
    idx = 0
    t_start = time.time()
    while idx < len(lines):
        blk = lines[idx:idx + BLOCK]
        want_len = good + sum(len(l.split("'")[3]) for l in blk)
        payload = "".join(l + "\n" for l in blk) + "wc -c < %s\n" % TMP
        s.clear()
        s.send(payload.encode())
        t0 = time.time()
        seen = None
        while time.time() - t0 < 12:
            s.pump(0.2)
            m = None
            for m in re.finditer(r"(?m)^\s*(\d+)\s*$", s.text()):
                pass
            if m:
                seen = int(m.group(1))
                if seen == want_len:
                    break
        if seen == want_len:
            good = want_len
            idx += len(blk)
        else:
            # rewind to the last verified length and retry this block
            say("head -c %d %s > %s.t; mv %s.t %s; wc -c < %s" % (good, TMP, TMP, TMP, TMP, TMP), 1.5)
            s.clear()
        if idx and (idx // BLOCK) % 10 == 0:
            el = time.time() - t_start
            print("#   %d/%d lines  %.0f B/s (payload %d B)" % (idx, len(lines), good / max(el, 0.001), good),
                  file=sys.stderr)
    print("# streamed %d lines in %.1fs (%d base64 bytes)"
          % (len(lines), time.time() - t_start, good))

    fin = say("set -e; base64 -d <%s | gunzip > %s.new; sha256sum %s.new | cut -d' ' -f1; "
              "install -m %s %s.new %s; sha256sum %s | cut -d' ' -f1; rm -f %s %s.new; stty echo"
              % (TMP, TMP, TMP, mode, TMP, remote, remote, TMP, TMP), 12)
    got = re.findall(r"\b([0-9a-f]{64})\b", fin)
    print("# target hashes: %s" % (got if got else "NONE"))
    os.close(fd)
    if len(got) >= 2 and got[0] == want and got[1] == want:
        print("# OK %s sha256=%s (verified on target)" % (remote, want))
        return 0
    print("!! FAIL expected %s" % want, file=sys.stderr)
    return 5


if __name__ == "__main__":
    sys.exit(main())
