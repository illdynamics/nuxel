#!/usr/bin/env bash
# nuxel-live.sh — run commands on the RUNNING Nuxel phone over the CDC-ACM live console.
#
#   nuxel-live.sh --run 'systemctl status nuxel-ui --no-pager'
#   nuxel-live.sh --run 'sleep 30; echo hi' --timeout 45
#   nuxel-live.sh --batch file.txt          # one command per line
#   nuxel-live.sh --pull /var/lib/nuxel/ui.ppm --out /tmp/ui.ppm
#   nuxel-live.sh --watch                   # just stream the console
#   nuxel-live.sh --dev /dev/cu.usbmodem201 --run 'id'
#
# WHY THIS IS NOT `screen` (P1 hardening, A26):
#   The console carries BOTH an interactive shell AND a live mirror of the
#   target's /dev/kmsg (see tools/s10plus/a24-nuxel-console.c: pump_kmsg()).  The
#   kernel telemetry (battery, touch, SSP, wlan) is a constant byte flood that
#   interleaves with shell output at arbitrary write() boundaries.  So this tool
#
#     * holds an exclusive flock on the serial device, so two host tools can
#       never fight over one port;
#     * gives every command a UNIQUE request id, so one command's output can
#       never be consumed as another's;
#     * runs the command with stdout+stderr redirected to a file on the target
#       and then emits that file inside @@NXB<id>@@ .. @@NXE<id>@@ markers, so
#       framing does not depend on terminal echo, timing or sleeps;
#     * emits the target-side SHA-256 of the payload and re-verifies it after
#       base64 decoding, so a kmsg line that shredded the stream can NEVER be
#       mistaken for a successful result (retries automatically);
#     * reports the command's real exit status from @@NXR<id>:<rc>@@;
#     * bounds execution with --timeout and cancels a stuck command with Ctrl-C,
#       so the shared shell is never wedged by a long-running command;
#     * sends Ctrl-C before every command to clear any stale foreground job.
#
# SAFETY: never opens /dev/fb0.  Closing a framebuffer fd runs decon_release and
# powers the AMOLED down (measured A21/A24); a screenshot must go through the
# running UI's own command FIFO.
set -euo pipefail
PY=${PY:-python3}
DEV=""; MODE=""; CMD=""; FILE=""; TIMEOUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dev) DEV="$2"; shift 2 ;;
    --run) MODE=run; CMD="$2"; shift 2 ;;
    --batch) MODE=batch; FILE="$2"; shift 2 ;;
    --watch) MODE=watch; shift ;;
    --pull) MODE=pull; CMD="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --timeout|--wait) TIMEOUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$DEV" ] || DEV=$(ls -1 /dev/cu.usbmodem* 2>/dev/null | head -1)
[ -n "$DEV" ] || { echo "no /dev/cu.usbmodem* — is the phone running Nuxel?" >&2; exit 1; }
[ -n "$MODE" ] || MODE=watch
echo "# console $DEV"
exec "$PY" - "$DEV" "$MODE" "${CMD:-}" "${FILE:-}" "${TIMEOUT:-20}" "${OUT:-}" <<'PYEOF'
import os, re, sys, fcntl, select, termios, time, hashlib, base64, binascii, random, gzip

dev, mode, cmd, path, tmo = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
out = sys.argv[6] if len(sys.argv) > 6 else ""

# ---- one host tool per serial device -------------------------------------------------
LOCK = "/tmp/nuxel-live.%s.lock" % re.sub(r"[^A-Za-z0-9]", "_", dev)
_lk = open(LOCK, "w")
try:
    fcntl.flock(_lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    print("!! another nuxel-live/console-host owns %s (lock %s) — refusing to share the port"
          % (dev, LOCK), file=sys.stderr)
    sys.exit(3)

# ---- framing constants ---------------------------------------------------------------
B64 = re.compile(r"^[A-Za-z0-9+/=]+$")
KMSG_LINE = re.compile(r"^\s*\d+,\d+,\d+,[-;c]")
KD = ("SUBSYSTEM=", "DEVICE=", "ACTION=", "SEQNUM=", "DEVPATH=", "MAJOR=", "MINOR=",
      "DEVNAME=", "DEVTYPE=", "MODALIAS=", "TAGS=", "SYNTH_UUID=")

def looks_kmsg(l):
    if KMSG_LINE.match(l):
        return True
    s = l.strip()
    return any(s.startswith(p) for p in KD)

def open_port():
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
        self.fd = fd
        self.buf = bytearray()
    def pump(self, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r:
                try:
                    c = os.read(self.fd, 65536)
                except OSError:
                    return
                if c:
                    self.buf += c
    def wait_for(self, needle, secs):
        """Drain continuously until `needle` appears in the stream or secs elapse."""
        nb = needle.encode() if isinstance(needle, str) else needle
        t0 = time.time()
        while time.time() - t0 < secs:
            if nb in self.buf:
                return True
            self.pump(0.15)
        return nb in self.buf
    def send(self, b):
        try:
            os.write(self.fd, b)
        except OSError as e:
            print("!! console lost while writing (%s) — device disconnected?" % e,
                  file=sys.stderr)
            raise SystemExit(4)
    def interrupt(self):
        self.send(b"\x03")
        self.pump(0.4)
        self.send(b"\r")
        self.pump(0.4)
    def text(self):
        return self.buf.decode("utf-8", "replace")

def clean(txt):
    return [l.rstrip() for l in txt.splitlines() if l.strip() and not looks_kmsg(l)]

def run_one(s, command, timeout):
    """Execute `command` on the target inside a verified frame.

    Returns (rid, rc, want_sha, body_text, raw_bytes, framed_ok)."""
    rid = "%04x%04x" % (random.getrandbits(16), int(time.time()) & 0xffff)
    tmp = "/var/tmp/nx-%s" % rid
    s.buf.clear()
    s.interrupt()                      # clear any stale foreground job
    s.buf.clear()
    # Target-side wrapper: run -> capture rc -> sha256 -> base64 -> frame markers.
    # Output goes to a file on the target first, so framing never depends on
    # terminal echo, on sleeps, or on kmsg arriving at a convenient moment.
    wrap = (
        "_NXID=%s; rm -f %s.out; { %s ; } >%s.out 2>&1 </dev/null; _NXRC=$?; "
        "printf '\\n@@NXB%%s@@\\n' \"$_NXID\"; "
        "printf '@@NXR%%s:%%s@@\\n' \"$_NXID\" \"$_NXRC\"; "
        "printf '@@NXH%%s:%%s@@\\n' \"$_NXID\" \"$(sha256sum <%s.out | cut -d' ' -f1)\"; "
        "base64 -w76 %s.out; printf '\\n@@NXE%%s@@\\n' \"$_NXID\""
    ) % (rid, tmp, command, tmp, tmp, tmp)
    s.send(wrap.encode() + b"\r")
    end = "@@NXE%s@@" % rid
    framed_ok = s.wait_for(end, timeout)
    if not framed_ok:
        s.interrupt()                  # cancel the stuck command, keep the shell
        s.pump(1.0)
    txt = s.text()
    m = re.search(r"@@NXR%s:(\d+)@@" % rid, txt)
    rc = int(m.group(1)) if m else None
    hm = re.search(r"@@NXH%s:([0-9a-f]{64})@@" % rid, txt)
    want = hm.group(1) if hm else None
    raw = b""
    if hm and end in txt:
        region = txt[hm.end():txt.index(end)]
        b64 = "".join(l.strip() for l in region.splitlines() if B64.match(l.strip()))
        try:
            raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
        except (binascii.Error, ValueError):
            raw = b""
    return rid, rc, want, raw.decode("utf-8", "replace"), raw, framed_ok


def report(s, command, timeout):
    """Run and report one command.  Never reports success on a mangled frame."""
    for attempt in (1, 2, 3):
        rid, rc, want, body, raw, framed_ok = run_one(s, command, timeout)
        if not framed_ok:
            print("===== %s   [FRAMED-ERROR: no end marker within %.0fs — command cancelled]"
                  % (command, timeout))
            for l in clean(s.text())[-8:]:
                print("   !", l)
            return 1
        got = hashlib.sha256(raw).hexdigest()
        if want and got != want:
            print("   (frame %s integrity mismatch on attempt %d — re-requesting)" % (rid, attempt))
            continue
        if want is None:
            print("   (frame %s had no target-side hash — re-requesting)" % rid)
            continue
        print("===== %s   [rc=%s frame=%s sha_ok=yes]" % (command, rc, rid))
        for l in clean(body)[:400]:
            print("   ", l)
        return 0 if rc == 0 else (rc if rc is not None else 1)
    print("===== %s   [UNVERIFIED: 3 frames all failed integrity/hash checks]" % command)
    return 1


def capture(s, command, timeout):
    """Run `command`, returning its verified stdout bytes, or None on failure."""
    for _ in range(3):
        rid, rc, want, body, raw, framed_ok = run_one(s, command, timeout)
        if not framed_ok or want is None:
            continue
        if hashlib.sha256(raw).hexdigest() != want:
            continue
        if rc != 0:
            print("   ! remote command failed rc=%s: %s" % (rc, command), file=sys.stderr)
            return None
        return raw
    print("   ! frame integrity failed 3x: %s" % command, file=sys.stderr)
    return None


def pull(s, remote, local, timeout):
    """Copy a remote file here, verified by SHA-256 on both sides."""
    r = capture(s, "sha256sum -- %s" % remote, timeout)
    if r is None:
        return 1
    want = r.decode("utf-8", "replace").split()[0]
    print("# remote %s sha256 %s" % (remote, want))
    blob = capture(s, "gzip -9 -c -- %s | base64 -w76" % remote, max(timeout, 120))
    if blob is None:
        return 1
    try:
        text = blob.decode("utf-8", "replace")
        b64 = "".join(l.strip() for l in text.splitlines() if B64.match(l.strip()))
        data = gzip.decompress(base64.b64decode(b64))
    except Exception as e:
        print("!! decode failed: %s" % e, file=sys.stderr)
        return 1
    got = hashlib.sha256(data).hexdigest()
    if got != want:
        print("!! SHA MISMATCH %s != %s — not writing" % (got, want), file=sys.stderr)
        return 1
    with open(local, "wb") as f:
        f.write(data)
    print("# wrote %s (%d bytes) sha256 %s VERIFIED" % (local, len(data), got))
    return 0


def main():
    try:
        fd = open_port()
    except OSError as e:
        print("!! cannot open %s: %s — is the phone running Nuxel?" % (dev, e), file=sys.stderr)
        sys.exit(4)
    s = Sess(fd)
    if mode == "watch":
        while True:
            s.pump(0.5)
            sys.stdout.write(s.text()); sys.stdout.flush(); s.buf.clear()
    if mode == "pull":
        rc = pull(s, cmd, out or os.path.basename(cmd), tmo)
        os.close(fd)
        sys.exit(rc)
    if mode == "run":
        cmds = [cmd]
    else:
        cmds = [l.rstrip("\n") for l in open(path) if l.strip() and not l.lstrip().startswith("#")]
    s.pump(0.8)
    worst = 0
    for c in cmds:
        try:
            rc = report(s, c, tmo)
        except OSError as e:
            print("!! console lost mid-command (%s) — device disconnected?" % e,
                  file=sys.stderr)
            sys.exit(4)
        worst = worst or rc
    os.close(fd)
    sys.exit(0 if worst == 0 else 1)

if __name__ == "__main__":
    main()
