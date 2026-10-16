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
# CABLE PULL (A26 open item, fixed in A33): a USB disconnect mid-command used to
# raise `OSError: [Errno 6] Device not configured` and print a Python traceback.
# Every read/write/select/termios call on the port is now translated into a clean
# `!! console lost (…)` report and exit status 4 — never a traceback, never a
# silent success.  `--wait-reconnect <secs>` additionally waits for the gadget to
# re-enumerate (it does so by itself; measured A26) and retries the same command
# once, which is what the mission's "console must stay reachable" rule needs.
#
# SAFETY: never opens /dev/fb0.  Closing a framebuffer fd runs decon_release and
# powers the AMOLED down (measured A21/A24); a screenshot must go through the
# running UI's own command FIFO.
set -euo pipefail
PY=${PY:-python3}
DEV=""; MODE=""; CMD=""; FILE=""; TIMEOUT=""; OUT=""; RECONNECT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dev) DEV="$2"; shift 2 ;;
    --run) MODE=run; CMD="$2"; shift 2 ;;
    --batch) MODE=batch; FILE="$2"; shift 2 ;;
    --watch) MODE=watch; shift ;;
    --pull) MODE=pull; CMD="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --timeout|--wait) TIMEOUT="$2"; shift 2 ;;
    --wait-reconnect) RECONNECT="$2"; shift 2 ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
# The host may be macOS (/dev/cu.usbmodem*) or Linux (/dev/ttyACM*); find either.
[ -n "$DEV" ] || DEV=$(ls -1 /dev/cu.usbmodem* /dev/ttyACM* 2>/dev/null | head -1)
[ -n "$DEV" ] || { echo "no CDC-ACM console node (/dev/cu.usbmodem* or /dev/ttyACM*) — is the phone running Nuxel?" >&2; exit 1; }
case "$DEV" in
  /dev/ttyACM*)
    # Linux: the node is root:dialout 0660.  Say so instead of a bare EACCES.
    if [ ! -r "$DEV" ]; then
      echo "!! $DEV exists but is not readable by $(id -un)." >&2
      echo "!!   it is owned by root:dialout (mode 0660): add yourself to dialout," >&2
      echo "!!   or re-run this tool with sudo.  Never chmod the node." >&2
    fi
    ;;
esac
[ -n "$MODE" ] || MODE=watch
echo "# console $DEV"
exec "$PY" - "$DEV" "$MODE" "${CMD:-}" "${FILE:-}" "${TIMEOUT:-20}" "${OUT:-}" "${RECONNECT:-0}" <<'PYEOF'
import os, re, sys, fcntl, select, termios, time, hashlib, base64, binascii, random, gzip

dev, mode, cmd, path, tmo = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
out = sys.argv[6] if len(sys.argv) > 6 else ""
reconnect = float(sys.argv[7]) if len(sys.argv) > 7 and sys.argv[7] else 0.0


class ConsoleLost(Exception):
    """The serial port went away (cable pull, gadget re-enumeration, host sleep).

    A33: the A26 open item.  Every port operation raises THIS instead of letting
    termios/select/read raise OSError at the top level, so a disconnect is
    reported as a disconnect and never as a Python traceback."""


def lost(what, e):
    return ConsoleLost("%s: %s" % (what, e)
                       if not isinstance(e, str) else "%s: %s" % (what, e))

# ---- one host tool per serial device -------------------------------------------------
# The lock lives in the shared /tmp so that nuxel-live.sh, nuxel-push.py and
# nuxel-console-host.sh mutually exclude each other on one serial device.
# BUG fixed 2026-10-16 (bg-00-preflight): on a Linux host with
# fs.protected_regular=2 (Fedora default) running this tool through sudo made the
# bare open() below raise EACCES — root may not O_CREAT an existing lock file that
# belongs to another user in a sticky world-writable directory.  That surfaced as a
# raw Python traceback, i.e. exactly the class of failure the A33 cable-pull fix
# removed for the serial port.  Now: a genuinely *held* lock is reported as such
# (exit 3) and a lock we merely cannot *open* falls back to a private per-uid lock.
_sanitized_dev = re.sub(r"[^A-Za-z0-9]", "_", dev)
LOCK = os.environ.get("NUXEL_LIVE_LOCK") or "/tmp/nuxel-live.%s.lock" % _sanitized_dev


def _open_lock(path):
    """Open `path` and take the exclusive, non-blocking port lock."""
    f = open(path, "w")
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)      # BlockingIOError when held
    return f


try:
    _lk = _open_lock(LOCK)
except BlockingIOError:
    print("!! another nuxel-live/console-host owns %s (lock %s) — refusing to share the port"
          % (dev, LOCK), file=sys.stderr)
    sys.exit(3)
except OSError as e:
    _alt = "%s/nuxel-live.%s.%d.lock" % (os.environ.get("TMPDIR", "/tmp").rstrip("/"),
                                         _sanitized_dev, os.getuid())
    try:
        _lk = _open_lock(_alt)
    except BlockingIOError:
        print("!! another nuxel-live/console-host owns %s (lock %s) — refusing to share the port"
              % (dev, _alt), file=sys.stderr)
        sys.exit(3)
    except OSError as e2:
        print("!! cannot take a port lock for %s (%s; %s) — refusing to share the serial port"
              % (dev, e, e2), file=sys.stderr)
        sys.exit(3)
    print("# shared lock %s is not usable by uid %d (%s) — using private lock %s"
          % (LOCK, os.getuid(), e, _alt), file=sys.stderr)
    LOCK = _alt

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
    try:
        fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        a = termios.tcgetattr(fd)
        a[0] = 0; a[1] = 0
        a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        a[3] = 0; a[4] = 9600; a[5] = 9600
        termios.tcsetattr(fd, termios.TCSANOW, a)
        termios.tcflush(fd, termios.TCIOFLUSH)
        return fd
    except OSError as e:
        raise lost("cannot configure %s" % dev, e)

class Sess:
    """One exclusive session on the console.

    Any port error becomes ConsoleLost.  EOF is treated as a disconnect too, but
    only after EOF_GRACE consecutive empty reads, so a momentary gap on a real
    USB CDC-ACM port is not mistaken for an unplug."""
    EOF_GRACE = 3
    def __init__(self, fd):
        self.fd = fd
        self.buf = bytearray()
        self.eof_streak = 0
        self.lost = None
    def pump(self, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.05)
            except OSError as e:
                raise lost("port disappeared while waiting for data", e)
            except (ValueError, TypeError) as e:
                raise lost("serial fd is no longer usable", e)
            if not r:
                continue
            try:
                c = os.read(self.fd, 65536)
            except OSError as e:
                raise lost("read failed", e)
            if c:
                self.eof_streak = 0
                self.buf += c
            else:
                # read() == 0 means EOF: the gadget is gone (Linux) or the port was
                # closed (macOS reports EIO above instead).
                self.eof_streak += 1
                if self.eof_streak >= self.EOF_GRACE:
                    raise ConsoleLost("end of stream (device disconnected)")
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
            raise lost("write failed", e)
    def interrupt(self):
        self.send(b"\x03")
        self.pump(0.4)
        self.send(b"\r")
        self.pump(0.4)
    def text(self):
        return self.buf.decode("utf-8", "replace")
    def close(self):
        try:
            os.close(self.fd)
        except OSError:
            pass

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


def wait_for_device(secs):
    """Wait for the console to re-enumerate after a disconnect.

    A26 measured that the gadget comes back by itself on the same
    /dev/cu.usbmodem* name; this just waits for that to happen instead of
    guessing a sleep.
    """
    deadline = time.time() + secs
    while time.time() < deadline:
        if os.path.exists(dev):
            time.sleep(0.6)                  # let the fresh gadget settle
            return True
        time.sleep(0.5)
    return False


def lost_report(where, e):
    print("!! console lost %s (%s)" % (where, e), file=sys.stderr)
    print("!!   the phone's USB console is gone (unplugged, or the gadget is "
          "re-enumerating).", file=sys.stderr)
    print("!!   no result is claimed for the interrupted command.", file=sys.stderr)
    if not reconnect:
        print("!!   re-run when it is back, or pass --wait-reconnect 60 to wait "
              "automatically.", file=sys.stderr)


def main():
    try:
        s = Sess(open_port())
    except ConsoleLost as e:
        print("!! cannot open %s (%s) — is the phone running Nuxel?" % (dev, e),
              file=sys.stderr)
        return 4

    if mode == "watch":
        while True:
            try:
                s.pump(0.5)
            except ConsoleLost as e:
                lost_report("while streaming", e)
                if not reconnect:
                    return 4
                s.close()
                if not wait_for_device(reconnect):
                    print("!! console did not come back within %.0fs" % reconnect,
                          file=sys.stderr)
                    return 4
                print("# console came back — resuming the stream")
                s = Sess(open_port())
                continue
            sys.stdout.write(s.text()); sys.stdout.flush(); s.buf.clear()

    if mode == "pull":
        while True:
            try:
                rc = pull(s, cmd, out or os.path.basename(cmd), tmo)
                break
            except ConsoleLost as e:
                lost_report("during --pull", e)
                if not reconnect:
                    return 4
                s.close()
                if not wait_for_device(reconnect):
                    print("!! console did not come back within %.0fs" % reconnect,
                          file=sys.stderr)
                    return 4
                print("# console came back — retrying the pull")
                s = Sess(open_port())
        s.close()
        return rc

    if mode == "run":
        cmds = [cmd]
    else:
        cmds = [l.rstrip("\n") for l in open(path) if l.strip() and not l.lstrip().startswith("#")]
    try:
        s.pump(0.8)
    except ConsoleLost as e:
        lost_report("before the first command", e)
        return 4
    worst = 0
    for c in cmds:
        while True:
            try:
                rc = report(s, c, tmo)
                break
            except ConsoleLost as e:
                lost_report("mid-command", e)
                if not reconnect:
                    s.close()
                    return 4
                s.close()
                if not wait_for_device(reconnect):
                    print("!! console did not come back within %.0fs — re-run when "
                          "the phone enumerates" % reconnect, file=sys.stderr)
                    return 4
                print("# console came back — retrying the interrupted command")
                s = Sess(open_port())
                continue
        worst = worst or rc
    s.close()
    return 0 if worst == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
PYEOF
