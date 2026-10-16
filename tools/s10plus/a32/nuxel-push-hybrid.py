#!/usr/bin/env python3
"""nuxel-push-hybrid.py — paced raw payload writes + framed verification.

Measured constraints (A32, this handset):
  * the link is ~960 B/s (9600 baud) and the target N_TTY input buffer is 4 KiB,
    so a single bulk write silently loses everything past the buffer;
  * a framed command (nuxel-live.sh) is reliable but costs ~2 s per round trip,
    and commands longer than ~512 characters are dropped by the far-end shell.

So the payload travels as individually paced 512-character base64 lines on the raw
port (throughput), while every ASSERTION (how many bytes landed, decode, hash,
install, re-hash) goes through the framed channel, which is the only transport
this project has proven against the kmsg flood.  Bytes are never trusted: the
decoded file must hash to the local SHA-256 and the installed path must re-hash to
it on the target.

    nuxel-push-hybrid.py [--mode 755] LOCAL REMOTE
"""
import base64, fcntl, gzip, hashlib, os, re, select, subprocess, sys, termios, time

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.normpath(os.path.join(HERE, "../../../scripts/s10plus-debug-pack/nuxel-live.sh"))
CHUNK = 480
TMP = "/tmp/nxh.b64"


def open_port(dev):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = 0; a[1] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[3] = 0; a[4] = 9600; a[5] = 9600
    termios.tcsetattr(fd, termios.TCSANOW, a)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def drain(fd, secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        r, _, _ = select.select([fd], [], [], 0.03)
        if r:
            try:
                os.read(fd, 65536)
            except OSError:
                return


def framed(cmd, timeout=45):
    """Run one command through the framed, SHA-verified channel; return stdout."""
    p = subprocess.run([LIVE, "--run", cmd, "--timeout", str(timeout)],
                       capture_output=True, text=True)
    return p.stdout + p.stderr


def framed_value(cmd, timeout=45, tries=4):
    """One framed command -> its last pure number/hash line, or None.

    The far end interleaves a live /dev/kmsg mirror with shell output, so a frame
    can be mangled; every assertion is therefore retried a bounded number of
    times instead of being trusted or given up on after one attempt."""
    for _ in range(tries):
        out = framed(cmd, timeout)
        if "sha_ok=yes" not in out:
            continue
        vals = [l.strip() for l in out.splitlines() if re.fullmatch(r"\s*[0-9a-f]{64}\s*|\s*\d+\s*", l)]
        if vals:
            return vals[-1].strip()
    return None


def main():
    args = sys.argv[1:]
    mode = "755"; local = None; remote = None; dev = None
    while args:
        a = args.pop(0)
        if a == "--mode": mode = args.pop(0)
        elif a == "--dev": dev = args.pop(0)
        elif local is None: local = a
        else: remote = a
    if not local or not remote:
        raise SystemExit("usage: nuxel-push-hybrid.py [--mode 755] LOCAL REMOTE")
    if not dev:
        cands = sorted(f for f in os.listdir("/dev") if f.startswith("cu.usbmodem"))
        if not cands: raise SystemExit("no /dev/cu.usbmodem*")
        dev = "/dev/" + cands[0]

    raw = open(local, "rb").read()
    want = hashlib.sha256(raw).hexdigest()
    b64 = base64.b64encode(gzip.compress(raw, 9)).decode()
    print("# push %s -> %s raw=%d base64=%d want=%s" % (local, remote, len(raw), len(b64), want))
    sys.stdout.flush()

    framed(": >%s; stty -echo 2>/dev/null; echo RESET" % TMP, 30)

    locked = 0
    lock = "/tmp/nuxel-live.%s.lock" % re.sub(r"[^A-Za-z0-9]", "_", dev)
    pos = 0
    for attempt in range(1, 9):
        # --- paced raw write of everything from `pos` ---------------------------
        lk = open(lock, "w")
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = 1
        except OSError:
            locked = 0
        if not locked:
            print("!! port busy"); return 3
        fd = open_port(dev)
        drain(fd, 0.4)
        t0 = time.time()
        i = pos
        while i < len(b64):
            line = b64[i:i + CHUNK]
            cmd = ("printf '%%s' '%s'>>%s\n" % (line, TMP)).encode()
            os.write(fd, cmd)
            i += len(line)
            time.sleep(len(cmd) / 900.0 + 0.015)   # pace to the line rate
        drain(fd, 0.6)
        os.close(fd)
        fcntl.flock(lk, fcntl.LOCK_UN)
        lk.close()
        print("#   wrote %d base64 chars in %.0fs" % (i - pos, time.time() - t0))
        sys.stdout.flush()

        seen = framed_value("wc -c <%s" % TMP, 40)
        seen = int(seen) if seen is not None else -1
        print("#   target length %d / %d" % (seen, len(b64)))
        sys.stdout.flush()
        if seen == len(b64):
            break
        if seen < 0:
            pos = max(0, pos - 4096)
        else:
            pos = seen if seen > pos else max(0, pos - CHUNK)
        if attempt == 8:
            print("!! transport never converged"); return 4
    else:
        return 4

    # four small framed steps beat one long one: each frame is independently
    # retried, so a single mangled frame can no longer abort a correct deploy
    got = framed_value("base64 -d <%s | gunzip > %s.bin && sha256sum <%s.bin | cut -d' ' -f1" % (TMP, TMP, TMP), 60)
    print("# decoded sha on target: %s" % got)
    if got != want:
        print("!! decoded payload mismatch (want %s) — nothing installed" % want)
        return 5
    got2 = framed_value("install -m %s %s.bin %s && sha256sum <%s | cut -d' ' -f1" % (mode, TMP, remote, remote), 60)
    print("# installed sha on target: %s" % got2)
    framed("rm -f %s %s.bin; stty echo 2>/dev/null" % (TMP, TMP), 45)
    if got2 == want:
        print("# OK %s sha256=%s (verified on target)" % (remote, want))
        return 0
    print("!! FAIL: installed hash %s != %s" % (got2, want))
    return 5


if __name__ == "__main__":
    sys.exit(main())
