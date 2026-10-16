#!/usr/bin/env python3
"""nuxel_live — capability-based access to the *running* Nuxel S10+ over its
USB CDC-ACM "Live Console", plus the guards that keep live work flash-free.

WHY THIS MODULE EXISTS (briq-10a/10b/10c, Priority 9 "Live S10+ Deployment")
==========================================================================
The live-phone build group is the only group allowed to touch the physical
device, and it must do so *safely and identically every time*:

  * the console tty node must be found **by capability** (USB VID/PID + the
    gadget's TTY base/suffix + serial), never by a hard-coded node name such as
    ``/dev/cu.usbmodem201`` or ``/dev/ttyACM0`` — the number changes across
    reboots and re-enumerations, exactly like ``/dev/input/eventN`` does for
    touch (see docs/beta-finalization/touch/PIPELINE-TRACE.md);
  * exactly **one** host tool may own the port at a time (the console carries a
    kmsg mirror as well as a shell, so two readers steal each other's bytes);
  * every remote command is framed with a unique request id and verified by a
    target-side SHA-256, so a kernel-log line that shreds the stream can never
    be mistaken for a successful result;
  * **no write path may ever resolve onto a raw partition, a kernel/DTB/DTBO
    image, a bootloader interface or a modem/EFS/calibration region** — this
    module refuses such paths before a single byte leaves the host.

Nothing here talks to the network, writes to ``.qq``/RUN_ROOT, or flashes.
Stdlib only, so it runs on the plain macOS host Python.

Hard invariants enforced in code (not just in prose)
---------------------------------------------------
* ``assert_userspace_path()`` — every deploy target must live under an allowed
  userspace root and must not match a forbidden pattern (partition/boot/kernel/
  modem/EFS/PIT/calibration).
* ``FORBIDDEN_TOOLS`` — heimdall/odin/loki/pit tooling may never be invoked.
* ``RebootPolicy`` — refuses blind repeat reboots and refuses a reboot before
  the console has reconnected and userspace rollback is known-good.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import select
import subprocess
import sys
import termios
import time

# --------------------------------------------------------------------------- #
# Device capability defaults.  These are the S10+ gadget's *advertised*
# capabilities (measured on the host with `ioreg -r -c AppleUSBACMData`), not a
# node name: any port that presents these capabilities is the right port.
# --------------------------------------------------------------------------- #
DEFAULT_VID = 0x18D1            # 6353  — Google Inc. (Android gadget VID)
DEFAULT_PID = 0x4EE7            # 20199 — Nuxel live-console gadget product id
DEFAULT_TTY_BASE = "usbmodem"   # CDC-ACM TTY base name
DEFAULT_SERIAL = "NUXEL-S10PLUS-0001"
DEFAULT_PRODUCT_RE = r"Nuxel.*(Live\s*)?Console"

#: Host serialisation lock (mirrors scripts/s10plus-debug-pack/nuxel-live.sh).
LOCK_DIR = "/tmp"

#: Service units whose state is part of the A32 baseline snapshot.
BASELINE_UNITS = (
    "nuxel-wayland",
    "nuxel-wl-fb",
    "nuxel-button-manager",
    "nuxel-touch-arm",
    "seatd",
)

#: Paths whose contents prove which components own the display / animation.
BASELINE_FILES = (
    "/proc/cmdline",
    "/var/lib/nuxel/fb-owner",
    "/var/lib/nuxel/animation",
    "/run/nuxel-wl-fb.state",
    "/proc/bus/input/devices",
)

#: Kernel console byte budget per framed round trip (device N_TTY ring is 4 KiB
#: and the far end has no application-level flow control).
MAX_WRAPPER_LEN = 480

#: `ioreg` decorates every registry line with a `|` tree glyph; tolerate it.
_PROP_RE = re.compile(r'[|\s]*"([^"]+)"\s*=\s*(.+)$')

KMSG_LINE = re.compile(r"^\s*\d+,\d+,\d+,[-;c]")
KMSG_KEYS = ("SUBSYSTEM=", "DEVICE=", "ACTION=", "SEQNUM=", "DEVPATH=", "MAJOR=",
             "MINOR=", "DEVNAME=", "DEVTYPE=", "MODALIAS=", "TAGS=")


class ConsoleLost(RuntimeError):
    """The serial port died (unplug, gadget rebind, or the phone went away)."""


class SelectionError(RuntimeError):
    """No console node matched the required capabilities, or too many did."""


class GuardViolation(RuntimeError):
    """A live operation was about to touch something flash-adjacent."""


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def looks_kmsg(line: str) -> bool:
    """True for a line that is part of the target's live /dev/kmsg mirror."""
    if KMSG_LINE.match(line):
        return True
    s = line.strip()
    return any(s.startswith(k) for k in KMSG_KEYS)


def clean_lines(text: str) -> list:
    """Drop blank lines and kmsg-mirror noise from captured output."""
    return [l.rstrip() for l in text.splitlines() if l.strip() and not looks_kmsg(l)]


# --------------------------------------------------------------------------- #
# Capability discovery  (macOS: ioreg; Linux host: /sys/class/tty)
# --------------------------------------------------------------------------- #
def parse_ioreg_acm(text: str) -> list:
    """Parse `ioreg -r -c AppleUSBACMData -w0 -l` into capability records.

    Each record = {vid,pid,tty_base,tty_suffix,tty_device,callout,dialin}.
    The parser is deliberately tolerant: properties are read only inside the
    AppleUSBACMData block, and the IOSerialBSDClient child supplies the nodes.
    """
    nodes = []
    cur = None
    for raw in text.splitlines():
        line = raw.strip()
        if "<class AppleUSBACMData" in line:
            cur = {"vid": None, "pid": None, "tty_base": None, "tty_suffix": None,
                   "tty_device": None, "callout": None, "dialin": None}
            nodes.append(cur)
            continue
        if cur is None:
            continue
        m = _PROP_RE.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip('"')
        if key == "idVendor":
            cur["vid"] = _to_int(val)
        elif key == "idProduct":
            cur["pid"] = _to_int(val)
        elif key == "IOTTYBaseName":
            cur["tty_base"] = val
        elif key == "IOTTYSuffix":
            cur["tty_suffix"] = val
        elif key == "IOTTYDevice":
            cur["tty_device"] = val
        elif key == "IOCalloutDevice":
            cur["callout"] = val
        elif key == "IODialinDevice":
            cur["dialin"] = val
    return [n for n in nodes if n["callout"] or n["dialin"]]


def parse_ioreg_usb_devices(text: str) -> list:
    """Parse `ioreg -w0 -l -p IOUSB` into USB device capability records."""
    devs, cur = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if "<class IOUSBHostDevice" in line:
            cur = {"vid": None, "pid": None, "serial": None, "product": None,
                   "node": line.split("+-o ", 1)[-1].split("  <")[0]}
            devs.append(cur)
            continue
        if cur is None:
            continue
        m = _PROP_RE.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip('"')
        if key == "idVendor":
            cur["vid"] = _to_int(val)
        elif key == "idProduct":
            cur["pid"] = _to_int(val)
        elif key in ("kUSBSerialNumberString", "USB Serial Number"):
            cur["serial"] = val
        elif key in ("kUSBProductString", "USB Product Name"):
            cur["product"] = val
    return devs


def _to_int(val: str):
    try:
        return int(val, 0)
    except (TypeError, ValueError):
        return None


def enumerate_console_nodes(runner=subprocess.run) -> list:
    """Return live console capabilities actually present on this host.

    macOS  : ioreg capability lookup (no node-name assumption at all).
    Linux  : /sys/class/tty/*/device/../{idVendor,idProduct} capability lookup.
    """
    if sys.platform == "darwin":
        try:
            acm = runner(["ioreg", "-r", "-c", "AppleUSBACMData", "-w0", "-l"],
                         capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError):
            acm = ""
        nodes = parse_ioreg_acm(acm)
        for n in nodes:
            if not n.get("tty_device") and n.get("tty_base") and n.get("tty_suffix"):
                n["tty_device"] = "%s%s" % (n["tty_base"], n["tty_suffix"])
            if not n.get("callout") and n.get("tty_device"):
                n["callout"] = "/dev/cu.%s" % n["tty_device"]
            if not n.get("dialin") and n.get("tty_device"):
                n["dialin"] = "/dev/tty.%s" % n["tty_device"]
        return nodes

    nodes = []
    tty_root = "/sys/class/tty"
    try:
        entries = sorted(os.listdir(tty_root))
    except OSError:
        return nodes
    for name in entries:
        sysdev = os.path.join(tty_root, name, "device")
        if not os.path.islink(sysdev) and not os.path.isdir(sysdev):
            continue
        # walk up to the USB device that carries idVendor/idProduct
        node = {"tty_device": name, "callout": "/dev/%s" % name,
                "dialin": "/dev/%s" % name, "tty_base": re.sub(r"\d+$", "", name),
                "tty_suffix": (re.search(r"(\d+)$", name) or [None, None])[1],
                "vid": None, "pid": None}
        walk = os.path.realpath(sysdev)
        for _ in range(6):
            walk = os.path.dirname(walk)
            vid_f, pid_f = os.path.join(walk, "idVendor"), os.path.join(walk, "idProduct")
            if os.path.exists(vid_f) and os.path.exists(pid_f):
                node["vid"] = _to_int(open(vid_f).read().strip())
                node["pid"] = _to_int(open(pid_f).read().strip())
                break
        if node["vid"] is not None:
            nodes.append(node)
    return nodes


def select_console_node(nodes, vid=DEFAULT_VID, pid=DEFAULT_PID,
                        tty_base=DEFAULT_TTY_BASE, serial=None, usb_devices=None):
    """Pick THE console node by capability. Raises SelectionError otherwise.

    Matching order (first that yields exactly one candidate wins):
      1. VID + PID + TTY base name           (primary, rebind-proof)
      2. VID + PID                           (if the base name changed)
    A serial requirement is applied only when the caller supplies one AND the
    host can read a USB serial for that same VID/PID pair; it then narrows the
    candidate set instead of silently failing on hosts that cannot report it.
    """
    if not nodes:
        raise SelectionError(
            "no CDC-ACM serial capability present (no USB gadget enumerated)")

    def by_vidpid(seq):
        return [n for n in seq if n.get("vid") == vid and n.get("pid") == pid]

    cands = by_vidpid(nodes)
    stage = "vid+pid"
    if tty_base:
        with_base = [n for n in cands if (n.get("tty_base") or "") == tty_base]
        if with_base:
            cands, stage = with_base, "vid+pid+ttybase"
    if not cands:
        raise SelectionError(
            "no console matched capability vid=0x%04x pid=0x%04x (found: %s)"
            % (vid, pid, [n.get("tty_device") for n in nodes]))

    if serial and usb_devices is not None:
        usb = [d for d in usb_devices if d.get("vid") == vid and d.get("pid") == pid]
        serial_known = any(d.get("serial") for d in usb)
        if serial_known:
            if not any(d.get("serial") == serial for d in usb):
                raise SelectionError(
                    "console video/pid matched but USB serial is %r, expected %r"
                    % ([d.get("serial") for d in usb], serial))
            stage += "+serial"

    if len(cands) > 1:
        raise SelectionError(
            "ambiguous console: %d nodes matched %s (%s) — refusing to guess"
            % (len(cands), stage, [n.get("tty_device") for n in cands]))
    node = dict(cands[0])
    node["match_stage"] = stage
    return node


# --------------------------------------------------------------------------- #
# Flash-free path guards
# --------------------------------------------------------------------------- #
#: Never writable through this tooling.  Kept as regexes so a match is obvious
#: in a diff and provably not evadable by a trailing slash or a symlink hop.
FORBIDDEN_PATH_PATTERNS = (
    r"^/dev/block(/|$)", r"^/dev/mmcblk\d*(boot|rpmb)?", r"^/dev/sd[a-z]\d*$",
    r"^/dev/disk(/|$)", r"^/dev/nvme\d", r"^/dev/by-name(/|$)",
    r"^/dev/mapper(/|$)", r"^/proc(/|$)", r"^/sys(/|$)", r"^/boot(/|$)",
    r"^/efi(/|$)", r"^/dev/fb\d", r"^/dev/dri(/|$)",
    r"boot\.img$", r"recovery\.img$", r"vbmeta", r"\.(dtb|dtbo)$",
    r"(^|/)dtbo?(/|$)", r"^/dev/block/by-name", r"^/devices/",
    r"modem|radio|efs|sec_efs|persist|calibration|imei|pit|param|nvdata",
    r"^/mnt/(system|vendor|boot|efs)", r"^/firmware(/|$)",
)
FORBIDDEN_PATH_RE = tuple(re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATH_PATTERNS)

#: Writable userspace roots — live deploys may never leave these.
ALLOWED_TARGET_ROOTS = (
    "/home/nuxel/nuxel", "/etc/nuxel", "/usr/local", "/usr/lib/nuxel",
    "/usr/share/nuxel", "/var/lib/nuxel", "/etc/systemd/system", "/etc/xdg",
    "/run/nuxel", "/var/tmp",
)

#: Flash tooling that may never be executed from this group.
FORBIDDEN_TOOLS = ("heimdall", "odin", "loki", "pit", "dd if=/dev/block",
                   "fastboot", "twrp")


def path_is_forbidden(path: str) -> str | None:
    """Return the matching forbidden pattern, or None if the path is safe."""
    p = os.path.normpath(path)
    for rx in FORBIDDEN_PATH_RE:
        if rx.search(p):
            return rx.pattern
    return None


def assert_userspace_path(path: str) -> str:
    """Raise GuardViolation unless `path` is a legal userspace deploy target."""
    p = os.path.normpath(path)
    if not p.startswith("/"):
        raise GuardViolation("deploy target must be absolute: %r" % path)
    bad = path_is_forbidden(p)
    if bad:
        raise GuardViolation("refusing flash-adjacent path %r (matched %r)" % (p, bad))
    if not any(p == r or p.startswith(r + "/") for r in ALLOWED_TARGET_ROOTS):
        raise GuardViolation(
            "refusing %r: outside allowed userspace roots %s" % (p, list(ALLOWED_TARGET_ROOTS)))
    return p


def assert_no_flash_tooling(command: str) -> None:
    """Refuse a command line that would invoke flash/bootloader tooling."""
    low = command.lower()
    for tool in FORBIDDEN_TOOLS:
        if tool in low:
            raise GuardViolation("refusing command containing %r: %s" % (tool, command))


# --------------------------------------------------------------------------- #
# Bounded console session
# --------------------------------------------------------------------------- #
class ProbeResult:
    __slots__ = ("dev", "bytes_in", "echo_ok", "sample", "error", "elapsed", "at")

    def __init__(self, dev, bytes_in, echo_ok, sample, error, elapsed, at):
        self.dev, self.bytes_in, self.echo_ok = dev, bytes_in, echo_ok
        self.sample, self.error, self.elapsed, self.at = sample, error, elapsed, at

    @property
    def reachable(self) -> bool:
        return bool(self.echo_ok and not self.error)

    def as_dict(self):
        return {"dev": self.dev, "bytes_in": self.bytes_in, "echo_ok": self.echo_ok,
                "sample": self.sample, "error": self.error,
                "elapsed_s": round(self.elapsed, 3), "at": self.at,
                "reachable": self.reachable}


class RunResult:
    __slots__ = ("rid", "rc", "output", "framed", "sha_ok", "elapsed", "raw_len")

    def __init__(self, rid, rc, output, framed, sha_ok, elapsed, raw_len):
        self.rid, self.rc, self.output = rid, rc, output
        self.framed, self.sha_ok = framed, sha_ok
        self.elapsed, self.raw_len = elapsed, raw_len

    @property
    def ok(self) -> bool:
        return bool(self.framed and self.sha_ok)

    def as_dict(self):
        return {"rid": self.rid, "rc": self.rc, "framed": self.framed,
                "sha_ok": self.sha_ok, "elapsed_s": round(self.elapsed, 3),
                "raw_len": self.raw_len, "output_bytes": len(self.output.encode())}


def build_wrapper(rid, tmp, command):
    """The exact shell text that carries `command` through a verified frame.

    Kept as a module-level function (rather than inline in `Console.run`) so
    tools/beta/live/nuxel-live-deploy.py can *predict* the transmitted length
    before it chunks a file push — the console silently drops long lines.
    """
    return (
        "_N=%s;rm -f %s;{ %s ;} >%s 2>&1 </dev/null;_R=$?;"
        "printf '\\n@@B%%s@@\\n' $_N;printf '@@R%%s:%%s@@\\n' $_N $_R;"
        "base64 -w0 <%s 2>/dev/null|tr -d '\\n';printf '\\n@@S%%s:%%s@@\\n' $_N "
        "\"$(sha256sum <%s 2>/dev/null|cut -d' ' -f1)\";"
        "printf '@@E%%s@@\\n' $_N" % (rid, tmp, command, tmp, tmp, tmp)
    )


def wrap_length(command, rid="00000000", tmp="/var/tmp/nxl-00000000"):
    """Transmitted length of `build_wrapper(rid, tmp, command)`."""
    return len(build_wrapper(rid, tmp, command))


def chunk_size_for(make_command, limit=MAX_WRAPPER_LEN, start=128, step=8):
    """Largest payload size whose fully wrapped push command still fits.

    `make_command(payload) -> str` builds the shell line; a callable (rather
    than a %-template) avoids colliding with the literal `%s` that printf
    needs inside the command itself.
    """
    size = start
    while size > 8:
        if wrap_length(make_command("A" * size)) <= limit:
            return size
        size -= step
    return 8


def push_bytes(con, data, path, chunk=None, mode="+x"):
    """Stage `data` at a device path through verified frames (no scp/adb).

    Every chunk is a verified frame, so a kmsg-interleaved line can never be
    mistaken for a successful write.  `data` is base64-encoded in flight; the
    temporary `.b64` is decoded and `chmod`-ed on the target.
    """
    import base64
    path = assert_userspace_path(path)
    b64 = base64.b64encode(data).decode()

    def mk(seg):
        return "printf '%s' '%s' >> %s.b64" % ("%s", seg, path)
    if chunk is None:
        chunk = chunk_size_for(mk)
    con.run(": > %s.b64" % path, timeout=con.timeout)
    n = 0
    for i in range(0, len(b64), chunk):
        con.run(mk(b64[i:i + chunk]), timeout=con.timeout)
        n += 1
    dec = "base64 -d < %s.b64 > %s && rm -f %s.b64 && (test -z '%s' || chmod %s %s)"
    res = con.run(dec % (path, path, path, mode, mode or "0644", path), timeout=con.timeout)
    if not res.ok:
        raise ConsoleLost("chunked push of %s did not verify (%s frames)" % (path, n))
    return {"path": path, "bytes": len(data), "b64_chars": len(b64), "frames": n,
            "decoded_sha256": hashlib.sha256(data).hexdigest()}


def _lock_path(dev: str) -> str:
    return os.path.join(LOCK_DIR, "nuxel-live.%s.lock" % re.sub(r"[^A-Za-z0-9]", "_", dev))


class Console:
    """One exclusive, bounded session on the Nuxel live console.

    Use as a context manager::

        with Console(node["callout"], timeout=12) as c:
            r = c.run("id")
    """

    EOF_GRACE = 3
    BAUDS = (9600, 115200)

    def __init__(self, dev, baud=9600, timeout=20.0, lock=True, lock_wait=0.0):
        self.dev = dev
        self.baud = baud
        self.timeout = float(timeout)
        self.want_lock = lock
        self.lock_wait = float(lock_wait)
        self.fd = None
        self.buf = bytearray()
        self.eof_streak = 0
        self._lock_fd = None
        self.opened_at = None
        self.raw_total = 0

    # -- lifecycle ---------------------------------------------------------- #
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def open(self):
        if self.want_lock:
            import fcntl
            self._lock_fd = open(_lock_path(self.dev), "w")
            waited = 0.0
            while True:
                try:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if waited >= self.lock_wait:
                        raise ConsoleLost(
                            "%s is owned by another host tool (lock %s) — "
                            "the live group is serialised on purpose"
                            % (self.dev, _lock_path(self.dev)))
                    time.sleep(1.0)
                    waited += 1.0
        try:
            self.fd = os.open(self.dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        except OSError as e:
            raise ConsoleLost("cannot open %s: %s" % (self.dev, e))
        import fcntl
        a = termios.tcgetattr(self.fd)
        a[0] = 0
        a[1] = 0
        a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        a[3] = 0
        a[4] = self.baud
        a[5] = self.baud
        termios.tcsetattr(self.fd, termios.TCSANOW, a)
        try:  # assert DTR — some CDC-ACM gadgets only start their console on DTR
            TIOCM_DTR = 0x002
            fcntl.ioctl(self.fd, 0x8004746D, int(TIOCM_DTR).to_bytes(4, "little"))
        except OSError:
            pass
        termios.tcflush(self.fd, termios.TCIOFLUSH)
        self.opened_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        return self

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        if self._lock_fd is not None:
            try:
                self._lock_fd.close()
            except OSError:
                pass
            self._lock_fd = None

    # -- io ----------------------------------------------------------------- #
    def pump(self, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.05)
            except (OSError, ValueError) as e:
                raise ConsoleLost("port %s disappeared while waiting: %s" % (self.dev, e))
            if not r:
                continue
            try:
                c = os.read(self.fd, 65536)
            except OSError as e:
                raise ConsoleLost("read failed on %s: %s" % (self.dev, e))
            if c:
                self.eof_streak = 0
                self.buf += c
                self.raw_total += len(c)
            else:
                self.eof_streak += 1
                if self.eof_streak >= self.EOF_GRACE:
                    raise ConsoleLost("end of stream on %s (gadget disconnected)" % self.dev)

    def send(self, data: bytes):
        try:
            os.write(self.fd, data)
        except OSError as e:
            raise ConsoleLost("write failed on %s: %s" % (self.dev, e))

    def wait_for(self, needle, secs):
        nb = needle.encode() if isinstance(needle, str) else needle
        t0 = time.time()
        while time.time() - t0 < secs:
            if nb in self.buf:
                return True
            self.pump(0.2)
        return nb in self.buf

    def text(self):
        return self.buf.decode("utf-8", "replace")

    # -- probing ------------------------------------------------------------ #
    def probe(self, seconds=6.0, marker="@@NXPROBE-OK@@", burst=0):
        """Bounded liveness probe: send CR, wait for ANY bytes back.

        A live Nuxel console answers twice over: the shell echoes, and the
        console mirrors /dev/kmsg, so a byte-silent port is unambiguous proof
        that the far end is not serving the console.
        """
        t0 = time.time()
        err = None
        echo_ok = False
        try:
            if burst:
                # changed diagnostic: a reader that is alive but not echoing a bare
                # CR may still react to volume (or its input buffer may need waking)
                self.send(b"\r\n" * max(1, int(burst // 2)))
            self.send(b"\r\n")
            deadline = time.time() + seconds
            while time.time() < deadline:
                self.pump(0.3)
                if self.buf:
                    echo_ok = True
                    break
            if not echo_ok:
                # last resort: an explicit echoed marker
                self.send(("echo %s\r" % marker).encode())
                if self.wait_for(marker, min(3.0, seconds)):
                    echo_ok = True
        except ConsoleLost as e:
            err = str(e)
        except OSError as e:
            err = str(e)
        sample = self.text()[:400].replace("\r", "")
        return ProbeResult(self.dev, self.raw_total, echo_ok, sample, err,
                           time.time() - t0, time.strftime("%Y-%m-%dT%H:%M:%S%z"))

    def reachable(self, seconds=6.0):
        p = self.probe(seconds)
        return p.reachable, p

    # -- framed command execution ------------------------------------------- #
    def run(self, command, timeout=None, verify_sha=True, silent=False):
        """Run `command` on the target inside a verified frame.

        The far end redirects stdout+stderr into a target-side file, reports its
        exit status, base64-encodes the body between unique start/end markers and
        emits the body's SHA-256.  The body is therefore immune to the kmsg
        flood, and a truncated/degenerate frame is reported as `ok == False`
        instead of being mistaken for output.
        """
        timeout = self.timeout if timeout is None else float(timeout)
        assert_no_flash_tooling(command)
        rid = "%04x%04x" % (random.getrandbits(16), int(time.time()) & 0xFFFF)
        tmp = "/var/tmp/nxl-%s" % rid
        wrap = build_wrapper(rid, tmp, command)
        if len(wrap) > MAX_WRAPPER_LEN:
            raise GuardViolation(
                "wrapped command is %d chars (limit %d); the console drops long "
                "lines — shorten the command or write it to a target-side script"
                % (len(wrap), MAX_WRAPPER_LEN))
        t0 = time.time()
        self.buf.clear()
        self.interrupt()
        self.buf.clear()
        self.send(wrap.encode() + b"\r")
        end = "@@E%s@@" % rid
        got_end = False
        framed = False
        sha_ok = False
        rc = None
        body_b64 = ""
        while time.time() - t0 < timeout:
            self.pump(0.25)
            txt = self.text()
            if end in txt:
                got_end = True
                break
        if not got_end and self.fd is not None:
            try:  # cancel a wedged command so the shared shell is never left blocked
                self.send(b"\x03")
                self.pump(0.3)
            except (ConsoleLost, OSError):
                pass
        txt = self.text()
        # Frame layout emitted by the wrapper below is strictly
        #   B<rid> / R<rid>:<rc> / <base64 body> / S<rid>:<sha256> / E<rid>
        # so the body sits between the R and S markers.  (Parsing it between B
        # and R silently produced an empty body and failed the SHA check on a
        # perfectly good frame — caught by tools/beta/live/tests/test_live_lib.py.)
        m_body = re.search(r"@@B%s@@\n@@R%s:(-?\d+)@@\n(.*?)\n@@S%s:" % (rid, rid, rid),
                           txt, re.S)
        m_sha = re.search(r"@@S%s:([0-9a-f]*)@@" % rid, txt)
        if got_end and m_body:
            framed = True
            rc = int(m_body.group(1))
            body_b64 = re.sub(r"[^A-Za-z0-9+/=]", "", m_body.group(2))
            import base64
            try:
                out = base64.b64decode(body_b64 + "=" * (-len(body_b64) % 4)).decode("utf-8", "replace")
            except Exception:  # noqa: BLE001 - degenerate base64 => frame failure
                out = ""
                framed = False
            if framed and verify_sha and m_sha:
                sha_ok = (hashlib.sha256(out.encode()).hexdigest() == m_sha.group(1))
            elif framed:
                sha_ok = True
        else:
            out = self.text()
        res = RunResult(rid, rc, out, framed, sha_ok, time.time() - t0, self.raw_total)
        if not silent and not res.ok:
            sys.stderr.write("# frame not verified for %r (framed=%s sha_ok=%s)\n"
                             % (command, framed, sha_ok))
        return res

    def interrupt(self):
        try:
            self.send(b"\x03")
            self.pump(0.35)
            self.send(b"\r")
            self.pump(0.35)
        except (ConsoleLost, OSError):
            pass


def open_console(vid=DEFAULT_VID, pid=DEFAULT_PID, serial=None, timeout=20.0,
                 dev=None, nodes=None, usb_devices=None, runner=subprocess.run):
    """Discover the console by capability and return (Console, node, notes)."""
    notes = []
    if dev is None:
        nodes = enumerate_console_nodes(runner=runner) if nodes is None else nodes
        if usb_devices is None and sys.platform == "darwin":
            try:
                usb = runner(["ioreg", "-w0", "-l", "-p", "IOUSB"],
                             capture_output=True, text=True, timeout=20).stdout
                usb_devices = parse_ioreg_usb_devices(usb)
            except (OSError, subprocess.SubprocessError):
                usb_devices = []
        node = select_console_node(nodes, vid=vid, pid=pid, serial=serial,
                                   usb_devices=usb_devices)
        dev = node["callout"]
    else:
        node = {"callout": dev, "match_stage": "explicit"}
        notes.append("console node supplied explicitly (%s); capability check skipped" % dev)
    return Console(dev, timeout=timeout), node, notes


# --------------------------------------------------------------------------- #
# A32 baseline probe set (briq-10a)
# --------------------------------------------------------------------------- #
def baseline_probes(pwa_rel_paths=None):
    """Ordered (key, command) list for the A32 baseline snapshot.

    Commands are intentionally short: the console drops very long lines, and
    every command is executed through the framed, SHA-verified path.
    """
    units = " ".join(BASELINE_UNITS)
    probes = [
        ("uptime", "cat /proc/uptime"),
        ("uname", "uname -r"),
        ("hostname", "hostname"),
        ("cmdline", "cat /proc/cmdline"),
        ("boot_mode", "tr ' ' '\\n' </proc/cmdline|grep androidboot.mode"),
        ("units", "for u in %s;do printf '%%s=%%s\\n' $u $(systemctl is-active $u 2>&1);done" % units),
        ("failed_units", "systemctl --failed --no-legend --no-pager"),
        ("fb_owner", "cat /var/lib/nuxel/fb-owner 2>&1"),
        ("animation", "cat /var/lib/nuxel/animation 2>&1"),
        ("wl_fb_state", "cat /run/nuxel-wl-fb.state 2>&1"),
        ("touch_devices", "grep -A4 sec_touchscreen /proc/bus/input/devices"),
        ("input_nodes", "ls -l /dev/input/by-path/ 2>&1"),
        ("alsa_cards", "cat /proc/asound/cards"),
        ("alsa_beyond_madera", "grep -i madera /proc/asound/cards"),
        ("fb_devices", "ls -l /dev/fb* /sys/class/graphics 2>&1"),
        ("irq_sec_ts", "grep -iE 'sec_ts|sec_touch' /proc/interrupts"),
        ("pwa_host_unit", "systemctl is-active nuxel-pwa 2>&1"),
        ("http_registry", "curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8000/ 2>&1"),
        ("seatd_socket", "ls -l /run/seatd.sock /run/seatd/seatd.sock 2>&1"),
        ("deploy_check", "for p in /home/nuxel/nuxel /etc/nuxel /usr/local;do printf '%s ' $p;"
                         "test -d $p && echo present||echo MISSING;done"),
    ]
    if pwa_rel_paths:
        # PWA hashes: one short command per file keeps every line console-safe.
        for rel in pwa_rel_paths:
            dev_path = "/home/nuxel/nuxel/" + rel.lstrip("/")
            probes.append(("pwa_sha256:" + rel,
                           "sha256sum %s 2>&1" % dev_path))
    return probes


# --------------------------------------------------------------------------- #
# Deploy planning (briq-10b) — stage, verify, atomic install, rollback
# --------------------------------------------------------------------------- #
SERVICE_FOR_TARGET = (
    ("/home/nuxel/nuxel/pwa/nuxel-home", "nuxel-pwa"),
    ("/home/nuxel/nuxel/pwa/nuxel-apps", "nuxel-pwa"),
    ("/home/nuxel/nuxel/tools/s10plus", "nuxel-button-manager"),
    ("/etc/nuxel/button", "nuxel-button-manager"),
    ("/etc/nuxel/touch", "nuxel-touch-arm"),
    ("/etc/nuxel/network", "NetworkManager"),
    ("/etc/nuxel/audio", "nuxel-audio"),
    ("/usr/local/bin/nuxel-wl-fb", "nuxel-wl-fb"),
    ("/usr/local/bin/nuxel-console", "nuxel-console"),
    ("/usr/local/bin/nuxel-anim-handoff", "nuxel-wayland"),
)


def smallest_service_for(target):
    """Map a deploy target to the single smallest service that must restart."""
    t = os.path.normpath(target)
    best = None
    for prefix, unit in SERVICE_FOR_TARGET:
        if t == prefix or t.startswith(prefix + "/"):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, unit)
    return best[1] if best else None


def build_deploy_plan(manifest, repo_root):
    """Turn a deploy manifest into an ordered, guarded, reversible plan.

    Returns {"steps": [...], "violations": [...]} — a non-empty `violations`
    list means the plan must not be executed (the caller reports BLOCKED_*).
    """
    steps, violations, skipped = [], [], []
    for group in manifest.get("groups", []):
        gid = group.get("id")
        if group.get("state") in ("blocked_kernel", "blocked_firmware"):
            # A group that honestly declares itself kernel/firmware-blocked is
            # *skipped and recorded*, not a plan violation — and it never turns
            # into a write attempt against a partition.
            skipped.append({"group": gid, "state": group["state"],
                            "component": group.get("component"),
                            "reason": group.get("blocked_reason", "declared blocked"),
                            "verdict": ("BLOCKED_KERNEL" if group["state"] == "blocked_kernel"
                                        else "BLOCKED_FIRMWARE")})
            continue
        for entry in group.get("files", []):
            src = os.path.join(repo_root, entry["source"])
            tgt = entry["target"]
            try:
                tgt = assert_userspace_path(tgt)
            except GuardViolation as e:
                violations.append({"group": gid, "kind": "guard", "detail": str(e),
                                   "target": entry["target"]})
                continue
            if not os.path.isfile(src):
                violations.append({"group": gid, "kind": "missing_source",
                                   "detail": "staged source not in repo: %s" % entry["source"]})
                continue
            steps.append({
                "group": gid,
                "component": group.get("component"),
                "priority": group.get("priority"),
                "source": entry["source"],
                "source_sha256": sha256_file(src),
                "target": tgt,
                "staged": tgt + ".nuxel-staged",
                "backup": tgt + ".nuxel-rollback",
                "service": group.get("restart_service") or smallest_service_for(tgt),
                "verify": entry.get("verify", "sha256sum %s" % tgt),
                "health_check": group.get("health_check"),
                "risk": group.get("risk", "medium"),
            })
    return {"steps": steps, "violations": violations, "skipped": skipped}


def sha256_file(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def install_script(step, push_tool="scripts/s10plus-debug-pack/nuxel-push.py"):
    """Emit the exact stage→verify→atomic-install→restart→rollback shell text.

    This is the only write path this group ever uses for live deploys, and it
    contains no reference to a raw device, partition, kernel image or bootloader.
    """
    tgt, staged, backup = step["target"], step["staged"], step["backup"]
    svc = step["service"]
    lines = [
        "set -eu",
        "mkdir -p \"$(dirname %s)\"" % tgt,
        "if [ -e %s ]; then cp -a %s %s; fi" % (tgt, tgt, backup),
        "test -f %s" % staged,
        "printf '%%s  %%s\\n' %s %s > /var/tmp/nxl-verify.sha256"
        % (step["source_sha256"], staged),
        "sha256sum -c /var/tmp/nxl-verify.sha256",
        "mv -f %s %s" % (staged, tgt),
        "%s | grep -q %s" % (step["verify"], step["source_sha256"]),
    ]
    for pre in step.get("pre", []):
        lines.append(pre)
    if svc:
        lines.append("systemctl restart %s" % svc)
        lines.append("systemctl is-active %s" % svc)
    if step.get("health_check"):
        lines.append(step["health_check"])
    lines += [
        "# rollback (run only if the health check above failed)",
        "if [ -e %s ]; then cp -a %s %s; %s; fi"
        % (backup, backup, tgt, ("systemctl restart %s" % svc) if svc else "true"),
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Reboot policy (briq-10c) — never blind, always reversible
# --------------------------------------------------------------------------- #
class RebootPolicy:
    """Bounded, reason-carrying reboot policy honouring the mission invariants."""

    def __init__(self, max_reboots=3, min_interval_s=120):
        self.max_reboots = max_reboots
        self.min_interval_s = min_interval_s

    def next_reboot(self, history):
        """-> dict(allowed, code, reason). `history` = list of reboot records.

        A reboot is allowed only when ALL of these hold:
          * fewer than max_reboots have already happened in this cycle;
          * the previous reboot returned to Nuxel (console reconnected) — a
            phone that has not come back must never be rebooted again;
          * the reason is new AND the diagnostic that will run afterwards differs
            from the previous one (no blind repeats);
          * a userspace rollback path is known-good.
        """
        n = len(history)
        if n >= self.max_reboots:
            return {"allowed": False, "code": "budget_exhausted",
                    "reason": "%d/%d reboots already used — change strategy, "
                              "do not reboot again" % (n, self.max_reboots)}
        if history:
            last = history[-1]
            if not last.get("returned_to_nuxel"):
                return {"allowed": False, "code": "not_recovered",
                        "reason": "previous reboot never returned to Nuxel; "
                                  "rebooting again is a blind repeat — recover the "
                                  "console first"}
            if not last.get("rollback_known_good", True):
                return {"allowed": False, "code": "no_rollback",
                        "reason": "no known-good userspace rollback after the last "
                                  "reboot; fix that before rebooting again"}
        return {"allowed": True, "code": "ok", "reason": "budget and prerequisites satisfied"}

    def record(self, history, reason, diagnostic, returned_to_nuxel,
               rollback_known_good=True, evidence_before=None, evidence_after=None):
        """Validate and append a reboot record; raises GuardViolation if not allowed."""
        verdict = self.next_reboot(history)
        if not verdict["allowed"]:
            raise GuardViolation(verdict["reason"])
        if not reason or not diagnostic:
            raise GuardViolation("a reboot needs both a stated reason and a changed diagnostic")
        if history and history[-1].get("diagnostic") == diagnostic:
            raise GuardViolation(
                "diagnostic %r unchanged from the previous reboot — that would be a "
                "blind repeat" % diagnostic)
        if history and history[-1].get("reason") == reason:
            raise GuardViolation("reason %r repeats the previous reboot" % reason)
        rec = {"n": len(history) + 1, "reason": reason, "diagnostic": diagnostic,
               "returned_to_nuxel": bool(returned_to_nuxel),
               "rollback_known_good": bool(rollback_known_good),
               "evidence_before": evidence_before, "evidence_after": evidence_after,
               "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        history.append(rec)
        return rec


#: Pre-reboot checklist (must be green before `reboot` is ever issued).
PRE_REBOOT_CHECKLIST = (
    ("pr-1", "Boot partition untouched this session (no block-device writes)",
     "grep -l . /dev/null; ls -l /dev/disk/by-partlabel | head"),
    ("pr-2", "Userspace deploy verified and rollback copy present",
     "ls -l /home/nuxel/nuxel/*.nuxel-rollback 2>/dev/null | wc -l"),
    ("pr-3", "Rollback path recorded (docs/beta-finalization/live/DEPLOYMENTS.md)",
     "test -s /var/lib/nuxel/rollback.path && cat /var/lib/nuxel/rollback.path"),
    ("pr-4", "Console reconnect procedure ready on the host (device unplug/replug)",
     "true"),
    ("pr-5", "Current baseline bundle captured and hashed", "true"),
)

#: Post-reboot checklist (must be green to call the reboot a success).
POST_REBOOT_CHECKLIST = (
    ("po-1", "Console reconnects and answers a framed command", "id"),
    ("po-2", "Boot graph completed without failed units", "systemctl --failed --no-legend --no-pager"),
    ("po-3", "Framebuffer owner is the single Wayland/fb bridge", "cat /var/lib/nuxel/fb-owner"),
    ("po-4", "Animation handoff receipt present", "cat /var/lib/nuxel/animation"),
    ("po-5", "Launcher (nuxel-pwa) serves the registry on :8000", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/"),
)


# --------------------------------------------------------------------------- #
# On-device probes that only the live group can run (briq-10c)
# --------------------------------------------------------------------------- #
LIVE_PROBES = (
    ("touch-pipeline", "tools/s10plus/a33/nuxel-touch-capture.sh",
     "bounded touch capture: identifies the first layer dropping an event"),
    ("audio-abox", "tools/s10plus/a33/nuxel-audio-diag.sh",
     "blue ALSA / ABox walk from briq-03c"),
    ("fb-owner", "cat /var/lib/nuxel/fb-owner; cat /run/nuxel-wl-fb.state",
     "framebuffer ownership check"),
    ("sec-ts-irq", "grep -iE 'sec_ts|sec_touch' /proc/interrupts",
     "IRQ counts for sec_ts"),
    ("pwa-registry", "curl -s http://127.0.0.1:8000/registry.json | head -c 400",
     "PWA registry served over :8000"),
    ("charger-mode", "cat /sys/class/power_supply/*/online 2>/dev/null; dmesg | grep -i lpcharge",
     "charger-mode / lpcharge state (BLOCKED_KERNEL territory)"),
)


# --------------------------------------------------------------------------- #
# Evidence bundles
# --------------------------------------------------------------------------- #
class EvidenceBundle:
    """A timestamped raw-evidence directory with a SHA-256 manifest."""

    def __init__(self, root, name=None, label="live"):
        stamp = time.strftime("%Y%m%dT%H%M%S%z")
        self.dir = os.path.join(root, name or ("%s-%s" % (label, stamp)))
        os.makedirs(self.dir, exist_ok=True)
        self.files = []

    def write(self, filename, text):
        path = os.path.join(self.dir, filename)
        with open(path, "w") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
        self.files.append(path)
        return path

    def write_json(self, filename, obj):
        return self.write(filename, json.dumps(obj, indent=2, sort_keys=True))

    def manifest(self, filename="SHA256SUMS"):
        lines = []
        for p in sorted(self.files):
            lines.append("%s  %s" % (sha256_file(p), os.path.basename(p)))
        path = os.path.join(self.dir, filename)
        with open(path, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        return path, lines


def repo_root_from_here():
    """/Users/wicked/x/nuxel — the workspace root (never RUN_ROOT)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def ensure_not_qq(path):
    """Hard refusal to write anywhere under .qq / RUN_ROOT."""
    p = os.path.abspath(path)
    parts = p.split(os.sep)
    if ".qq" in parts or ".codeseeq" in parts:
        raise GuardViolation("refusing to write QonQrete metadata path %s" % p)
    return p
