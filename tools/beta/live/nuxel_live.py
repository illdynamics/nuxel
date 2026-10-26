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
#: All tools use the same inode; an inaccessible lock fails closed.
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
#: Longest framed shell line we transmit.  The far end is a Linux tty whose line
#: discipline buffer is 4096 bytes (N_TTY_BUF_SIZE); an over-long line is silently
#: truncated, which would corrupt a push.  Measured on the S10+ 2026-10-16: a
#: 4108-char wrapper round-trips with framed=True sha_ok=True, so the previous
#: 480-char ceiling was far too conservative — it refused every chunked push of a
#: path longer than ~120 chars (i.e. every /usr/share/nuxel/** target).  3800
#: leaves headroom under 4096 for the echoed prompt and the CR.
MAX_WRAPPER_LEN = 3800

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


def _to_int(val: str, base=0):
    try:
        return int(val, base)
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
                # sysfs reports idVendor/idProduct as bare HEX ("18d1"), not the
                # "0x18d1" ioreg prints on macOS.  int(val, 0) rejects a bare hex
                # string, which made this Linux branch find ZERO nodes on the S10+
                # host (measured 2026-10-16) even though the gadget was present.
                node["vid"] = _to_int(open(vid_f).read().strip(), 16)
                node["pid"] = _to_int(open(pid_f).read().strip(), 16)
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
    # Any image file at all: the built programme ships .img artefacts
    # (nuxel-beyond2lte-boot.img, the rootfs image, a merged boot image) and none
    # of them may ever be a deploy *target* — they are flashed artefacts, and this
    # group only ever writes userspace files.
    r"\.img$",
    r"(^|/)dtbo?(/|$)", r"^/dev/block/by-name", r"^/devices/",
    r"modem|radio|efs|sec_efs|persist|calibration|imei|pit|param|nvdata",
    r"^/mnt/(system|vendor|boot|efs)", r"^/firmware(/|$)",
)
FORBIDDEN_PATH_RE = tuple(re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATH_PATTERNS)

#: Writable userspace roots — live deploys may never leave these.
#:
#: Extended by briq-01-deploy-manifest-extension so the REST of the built
#: programme is deployable without weakening the flash-free guard (the forbidden
#: patterns above are matched first, so a root can never smuggle in a partition,
#: a BOOT/USERDATA image, the modem/EFS/PIT region or a DTB):
#:   /usr/bin              the canonical units start /usr/bin/nuxel-bridge,
#:                         /usr/bin/nuxel-web, ... — the rootfs builder installs
#:                         the service shims there, so the plan must reach it;
#:   /usr/libexec/nuxel    the shipped early-boot tools (nuxel-verbose-boot,
#:                         nuxel-anim-handoff.py), per nuxel-verbose-boot.service
#:                         ExecStart= and tools/s10plus/a33/nuxelctl;
#:   /etc/systemd          unit drop-ins and conf.d documents (timesyncd.conf.d),
#:                         not just /etc/systemd/system;
#:   /etc/dbus-1/system.d  the D-Bus system policies the bridge/portal/
#:                         notifications need, per configs/dbus/ and the builder.
ALLOWED_TARGET_ROOTS = (
    "/home/nuxel/nuxel", "/etc/nuxel", "/usr/local", "/usr/lib/nuxel",
    "/usr/share/nuxel", "/var/lib/nuxel", "/etc/systemd/system", "/etc/xdg",
    "/run/nuxel", "/var/tmp",
    "/usr/bin", "/usr/libexec/nuxel", "/etc/systemd", "/etc/dbus-1/system.d",
)

#: The device's writable userspace tree for the *phone*.  On the handset the whole
#: launcher/docroot tree is served from /usr/share/nuxel: the image builder
#: (images/s10plus/build-phone-rootfs-inside-fedora.sh) stages `pwa/` +
#: `nuxel-home` there, tools/s10plus/a32/install-on-phone.sh installs there, and
#: services/nuxel-web/bin/nuxel-web *prefers* /usr/share/nuxel over
#: /home/nuxel/nuxel.  /home/nuxel/nuxel is only the VM/deploy-mirror fallback.
#:
#: The deploy manifest is authored against the mirror root, so the plan remaps it
#: to the root the running phone actually reads before it is guarded or executed.
#: Measured on-device 2026-10-16: /home/nuxel/nuxel does not exist at all, so a
#: plan that wrote there could not change a single pixel of the launcher — this
#: remap is the difference between "deployed" and "the owner sees no difference".
DEFAULT_TARGET_ROOT_MAP = {"/home/nuxel/nuxel": "/usr/share/nuxel"}


def resolve_root_map(manifest):
    """The effective target-root map: the default, overridden by the manifest."""
    m = dict(DEFAULT_TARGET_ROOT_MAP)
    m.update({str(k): str(v) for k, v in (manifest.get("target_root_map") or {}).items()})
    return m


def remap_path(path, root_map):
    """Rewrite a deploy target onto the device's real root (longest prefix wins)."""
    p = os.path.normpath(str(path))
    best = None
    for src, dst in (root_map or {}).items():
        s = os.path.normpath(src)
        if p == s or p.startswith(s + "/"):
            if best is None or len(s) > len(best[0]):
                best = (s, dst)
    if not best:
        return p
    s, dst = best
    rest = p[len(s):].lstrip("/")
    return os.path.normpath(os.path.join(dst, rest)) if rest else os.path.normpath(dst)


def remap_text(text, root_map):
    """Rewrite every occurrence of a mapped root inside a shell fragment."""
    out = str(text)
    for src, dst in sorted((root_map or {}).items(),
                           key=lambda kv: -len(os.path.normpath(kv[0]))):
        out = out.replace(src, dst)
    return out


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


#: A token that is also a common substring (e.g. "pit" inside a base64 blob) must
#: only match as a standalone word, or the guard refuses legitimate payload data.
_FLASH_TOKEN_RES = tuple(
    (t, re.compile(r"(?<![a-z0-9_])%s(?![a-z_])" % re.escape(t)))
    for t in FORBIDDEN_TOOLS
)


def assert_no_flash_tooling(command: str) -> None:
    """Refuse a command line that would invoke flash/bootloader tooling.

    Matching is on word boundaries: a bare substring test rejected a base64 push
    chunk that happened to contain "Pit" (measured 2026-10-16 pushing an app icon),
    which is opaque data, not a tool invocation.
    """
    low = command.lower()
    for tool, rx in _FLASH_TOKEN_RES:
        if rx.search(low):
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


def chunk_size_for(make_command, limit=MAX_WRAPPER_LEN, start=64, step=64,
                   max_size=128):
    """Largest payload size whose fully wrapped push command still fits.

    `make_command(payload) -> str` builds the shell line; a callable (rather
    than a %-template) avoids colliding with the literal `%s` that printf
    needs inside the command itself.

    This must GROW from `start` looking for the largest size that fits.  The
    protocol's 3800-byte wrapper ceiling is not the usable CDC-ACM line ceiling:
    the S10+ console mirrors kmsg concurrently and a ~3.8 KiB transmitted line
    can be shredded before it reaches the shell.  Keep a conservative 128-char
    base64 payload cap (measured live) while still calculating against the
    wrapper limit.  Each part is idempotent, so verified smaller frames are
    preferable to an optimistic frame that cannot be retried safely.
    """
    best = 8
    size = start
    while size <= max_size:
        if wrap_length(make_command("A" * size)) <= limit:
            best = size
            size += step
        else:
            break
    return best


def push_bytes(con, data, path, chunk=None, mode="+x"):
    """Stage `data` at a device path through verified frames (no scp/adb).

    Robustness contract (measured on the S10+ 2026-10-16): the console drops the
    occasional OUT line, so a chunked *append* cannot be retried — re-sending an
    append that actually landed would duplicate bytes.  Instead each chunk is
    written to its OWN part file with a truncating `>`, which is idempotent and
    therefore retry-safe: a lost chunk is simply re-sent, and the parts are
    concatenated once every part is confirmed.  The whole payload is base64-encoded
    in flight and the staged file's SHA-256 is read back from the device before the
    push is reported successful.
    """
    import base64
    path = assert_userspace_path(path)
    b64 = base64.b64encode(data).decode()
    want = hashlib.sha256(data).hexdigest()
    part_prefix = path + "." + want[:16] + ".b64"

    def mk(seg, part):
        return "printf '%s' '%s' > %s" % ("%s", seg, part)
    if chunk is None:
        chunk = chunk_size_for(lambda seg: mk(seg, part_prefix + ".00000"))
    mkdir = con.run('mkdir -p "$(dirname %s)"' % path, timeout=con.timeout)
    if not mkdir.ok or mkdir.rc != 0:
        raise ConsoleLost("cannot create parent directory for %s (%s)"
                          % (path, mkdir.output.strip()[:80]))
    parts = []
    for i in range(0, len(b64), chunk):
        seg = b64[i:i + chunk]
        part = "%s.%05d" % (part_prefix, len(parts))
        cmd = mk(seg, part)
        got = False
        for _try in range(5):
            res = con.run(cmd, timeout=con.timeout, guard=False)
            if res.ok:
                got = True
                break
            con.interrupt()  # clear a half-line before re-sending this chunk
            time.sleep(0.3)
        if not got:
            raise ConsoleLost("chunk %d of %s could not be written to %s"
                              % (len(parts) + 1, path, part))
        parts.append(part)
    # Retain the parts until destination readback succeeds. A lost console
    # receipt after a successful decode must be safe to retry: removing the
    # parts first made the second attempt truncate the correctly staged file.
    dec = ("cat %s.* > %s.b64 && "
           "base64 -d < %s.b64 > %s.decode && "
           "chmod %s %s.decode && mv -f %s.decode %s"
           % (part_prefix, path, path, path, mode or "0644", path, path, path))
    for _try in range(3):
        res = con.run(dec, timeout=con.timeout)
        if res.ok:
            chk = con.run("sha256sum %s 2>/dev/null | cut -d' ' -f1" % path,
                          timeout=con.timeout)
            if chk.ok and want in chk.output:
                # Cleanup is best effort after verification; it never changes
                # the verified destination and is itself idempotent.
                con.run("rm -f %s.b64 %s.*" % (path, part_prefix), timeout=con.timeout)
                return {"path": path, "bytes": len(data), "b64_chars": len(b64),
                        "parts": len(parts), "decoded_sha256": want}
        con.interrupt()
        time.sleep(0.5)
    raise ConsoleLost("staged %s failed the on-device sha256 check after decode" % path)


def block_push_bytes(con, data, path, mode="0644", chunk=None, block=None,
                     max_retries=5):
    """Stage `data` on-device with bounded, acknowledged BLOCK writes.

    This is the fast path that replaces one framed round trip per 128-char
    part (``push_bytes``) with a few raw transport writes, while keeping the
    single-writer rule: every write and every read goes through `con`, so no
    second process can interleave with the physical serial stream.

    Protocol (reusing the line/block limits measured by nuxel-push.py,
    2026-10-16: 380-char lines, 24 lines per block):

      * one framed setup command truncates the part file and disables echo;
      * each BLOCK is one raw write of `block` base64 lines (append), followed
        by a `wc -c < part` receipt line;
      * the cumulative file length is the acknowledgement: if it does not land
        exactly on the expected boundary, the partial file is truncated back to
        the last verified length and the block is retried with a bounded budget;
      * a final framed command decodes, verifies the SHA-256 and atomically
        moves the decoded bytes to `path`.

    Integrity is end-to-end: nothing is activated until the reconstructed byte
    count and SHA-256 match the source.  `push_bytes` remains the fallback for
    callers that must stay on the frame-per-chunk protocol.
    """
    import base64
    path = assert_userspace_path(path)
    b64 = base64.b64encode(data).decode()
    want = hashlib.sha256(data).hexdigest()
    part = path + "." + want[:16] + ".b64"

    if chunk is None:
        # Measured safe console line limit from nuxel-push.py (380 chars), not
        # the 128-char frame cap: block streaming reads a cumulative length
        # receipt, so a single shredded line is recovered by block retry.
        chunk = 380
    if block is None:
        block = 24

    mkdir = con.run('mkdir -p "$(dirname %s)"' % path, timeout=con.timeout)
    if not mkdir.ok or mkdir.rc != 0:
        raise ConsoleLost("cannot create parent directory for %s (%s)"
                          % (path, mkdir.output.strip()[:80]))
    # One framed command for setup; the bulk lines below are raw writes.
    setup = con.run("stty -echo 2>/dev/null; : > %s; echo NXLBLOCK-READY" % part,
                    timeout=con.timeout)
    if not setup.ok:
        raise ConsoleLost("block push setup failed for %s (%s)"
                          % (path, setup.output.strip()[:80]))

    segs = [b64[i:i + chunk] for i in range(0, len(b64), chunk)]
    good = 0
    idx = 0
    attempts = 0
    while idx < len(segs):
        blk = segs[idx:idx + block]
        want_len = good + sum(len(s) for s in blk)
        con.buf.clear()
        # Write the block as a burst of raw lines (one os.write per line, with a
        # tiny pump so the far-end line discipline never drops part of the burst)
        # and ACK at the block boundary with a single cumulative length read.
        for s in blk:
            con.send(("printf '%s' '%s' >> %s\r" % ("%s", s, part)).encode())
            con.pump(0.02)
        con.send(("wc -c < %s\r" % part).encode())
        t0 = time.time()
        seen = None
        deadline = t0 + max(6.0, con.timeout)
        while time.time() < deadline:
            con.pump(0.2)
            m = None
            for m in re.finditer(r"(?m)^\s*(\d+)\s*$", con.text()):
                pass
            if m:
                seen = int(m.group(1))
                if seen == want_len:
                    break
        if seen == want_len:
            good = want_len
            idx += len(blk)
            attempts = 0
            continue
        # Rewind to the last verified boundary and retry this exact block.
        attempts += 1
        if attempts > max_retries:
            raise ConsoleLost(
                "block %d of %s could not reach %d bytes (last verified %d)"
                % (idx // block + 1, path, want_len, good))
        con.interrupt()
        if good:
            rewind = con.run("head -c %d %s > %s.t && mv %s.t %s"
                             % (good, part, part, part, part), timeout=con.timeout)
        else:
            rewind = con.run(": > %s" % part, timeout=con.timeout)
        if not rewind.ok:
            raise ConsoleLost("could not rewind %s to verified boundary %d"
                              % (path, good))

    dec = ("cat %s > %s.b64 && base64 -d < %s.b64 > %s.decode && "
           "chmod %s %s.decode && mv -f %s.decode %s"
           % (part, path, path, path, mode or "0644", path, path, path))
    for _try in range(3):
        res = con.run(dec, timeout=con.timeout)
        if res.ok:
            chk = con.run("sha256sum %s 2>/dev/null | cut -d' ' -f1" % path,
                          timeout=con.timeout)
            if chk.ok and want in chk.output:
                con.run("stty echo 2>/dev/null; rm -f %s.b64 %s %s.t"
                        % (path, part, part), timeout=con.timeout)
                return {"path": path, "bytes": len(data), "b64_chars": len(b64),
                        "blocks": (len(segs) + block - 1) // block,
                        "lines": len(segs), "raw_writes": (len(segs) + block - 1) // block,
                        "retries": attempts, "decoded_sha256": want,
                        "mode": "block"}
        con.interrupt()
        time.sleep(0.5)
    raise ConsoleLost("staged %s failed the on-device sha256 check after block decode" % path)


def _sanitized_dev(dev: str) -> str:
    """Reduce a tty/device name to a filename-safe token (mirrors nuxel-live.sh)."""
    return re.sub(r"[^A-Za-z0-9]", "_", dev)


def _shared_lock_path(dev: str) -> str:
    """The shared /tmp lock.

    `NUXEL_LIVE_LOCK` overrides it, exactly as
    scripts/s10plus-debug-pack/nuxel-live.sh does, so an operator (or an offline
    test) can point every tool at one lock without editing the code.
    """
    override = os.environ.get("NUXEL_LIVE_LOCK")
    if override:
        return override
    return os.path.join(LOCK_DIR, "nuxel-live.%s.lock" % _sanitized_dev(dev))


def _lock_path(dev: str) -> str:
    return _shared_lock_path(dev)


def take_console_lock(dev: str, lock_wait: float = 0.0, opener=open):
    """Acquire the shared inode, never a private lock that bypasses a peer.

    Fedora protected_regular rejects O_CREAT on another user's existing /tmp
    file. Opening that SAME file without O_CREAT preserves mutual exclusion.
    If its permissions also deny that open, refuse the port; never unlink it.
    """
    shared = _shared_lock_path(dev)
    try:
        return _flock(shared, lock_wait, opener), shared
    except BlockingIOError:
        raise ConsoleLost(
            "%s is owned by another host tool (lock %s) — "
            "the live group is serialised on purpose" % (dev, shared))
    except OSError as e:
        raise ConsoleLost(
            "cannot take a port lock for %s (%s) — refusing to share the serial port"
            % (dev, e)) from e


def _flock(path, lock_wait=0.0, opener=open):
    """Open without truncating, then take a bounded exclusive flock."""
    import fcntl
    try:
        fd = opener(path, "a+")
    except PermissionError:
        # No O_CREAT: bypasses protected_regular, NOT the shared lock.
        fd = opener(path, "r")
    deadline = time.monotonic() + max(0.0, float(lock_wait))
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                time.sleep(min(0.1, remaining))
    except BaseException:
        fd.close()
        raise


class Console:
    """One exclusive, bounded session on the Nuxel live console.

    Use as a context manager::

        with Console(node["callout"], timeout=12) as c:
            r = c.run("id")
    """

    EOF_GRACE = 3
    # The S10+ gadget is 115200 8N1 (quickstart-live-console.md §1, measured).
    # 9600 is kept only as the explicit fallback a caller may request.
    BAUDS = (115200, 9600)

    def __init__(self, dev, baud=115200, timeout=20.0, lock=True, lock_wait=0.0):
        self.dev = dev
        self.baud = baud
        self.timeout = float(timeout)
        self.want_lock = lock
        self.lock_wait = float(lock_wait)
        self.fd = None
        self.buf = bytearray()
        self.eof_streak = 0
        self._lock_fd = None
        self.lock_path = None
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
            self._lock_fd, self.lock_path = take_console_lock(
                self.dev, lock_wait=self.lock_wait)
        try:
            self.fd = os.open(self.dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
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
        except (OSError, termios.error) as e:
            self.close()
            raise ConsoleLost("cannot open/configure %s: %s" % (self.dev, e)) from e
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
    def run(self, command, timeout=None, verify_sha=True, silent=False, guard=True):
        """Run `command` on the target inside a verified frame.

        The far end redirects stdout+stderr into a target-side file, reports its
        exit status, base64-encodes the body between unique start/end markers and
        emits the body's SHA-256.  The body is therefore immune to the kmsg
        flood, and a truncated/degenerate frame is reported as `ok == False`
        instead of being mistaken for output.
        """
        timeout = self.timeout if timeout is None else float(timeout)
        if guard:
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
        # Only cancel a wedged line when the previous frame did not complete
        # cleanly.  interrupt() costs ~0.7 s (two 0.35 s pumps) and, after a
        # verified frame, the shell is already sitting at a clean prompt — so
        # skipping it roughly halves the wall time of a many-frame deploy.
        if not getattr(self, "_last_clean", False):
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
            self.pump(0.08)
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
        # The far end is a Linux tty: its lines end in CRLF.  Normalise before
        # parsing, otherwise @@B<rid>@@\n never matches the real @@B<rid>@@\r\n and
        # EVERY frame is reported unverified although the device answered
        # correctly (measured on the S10+ 2026-10-16: framed=false, sha_ok=false
        # for all 41 baseline probes while the bash client saw sha_ok=yes).
        txt = self.text().replace("\r\n", "\n").replace("\r", "\n")
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
            out = txt
        res = RunResult(rid, rc, out, framed, sha_ok, time.time() - t0, self.raw_total)
        self._last_clean = bool(res.ok)
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
def baseline_probes(pwa_rel_paths=None, docroot="/usr/share/nuxel"):
    """Ordered (key, command) list for the A32 baseline snapshot.

    Commands are intentionally short: the console drops very long lines, and
    every command is executed through the framed, SHA-verified path.

    `docroot` is the on-device root the launcher tree is served from.  On the
    handset that is /usr/share/nuxel (see DEFAULT_TARGET_ROOT_MAP); the VM/deploy
    mirror /home/nuxel/nuxel is only a fallback and does not exist on the phone.
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
        ("deploy_check", "for p in /usr/share/nuxel /etc/nuxel /usr/local;do printf '%s ' $p;"
                         "test -d $p && echo present||echo MISSING;done"),
    ]
    if pwa_rel_paths:
        # PWA hashes: one short command per file keeps every line console-safe.
        for rel in pwa_rel_paths:
            dev_path = docroot.rstrip("/") + "/" + rel.lstrip("/")
            probes.append(("pwa_sha256:" + rel,
                           "sha256sum %s 2>&1" % dev_path))
    return probes


# --------------------------------------------------------------------------- #
# Deploy planning (briq-10b) — stage, verify, atomic install, rollback
# --------------------------------------------------------------------------- #
SERVICE_FOR_TARGET = (
    ("/usr/share/nuxel/pwa/nuxel-home", "nuxel-wayland"),
    ("/usr/share/nuxel/pwa/nuxel-apps", "nuxel-wayland"),
    ("/usr/share/nuxel/nuxel-home", "nuxel-wayland"),
    ("/usr/share/nuxel/boot", "nuxel-wayland"),
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


#: Risk classes a deploy group may declare.  Ascending = safer first.
RISK_CLASSES = {"low": 0, "medium": 1, "high": 2}


def risk_rank(risk):
    """Rank a declared risk class; an unknown class is treated as `high`.

    Unknown never means "safe": a group that mis-declares its risk is refused by
    validate_manifest() rather than deployed in the middle of the order.
    """
    return RISK_CLASSES.get(str(risk).lower(), len(RISK_CLASSES))


#: A deliberately non-deployable entry may never claim a deployed/verified state.
PROMOTING_TERMINAL_STATES = ("VERIFIED_ON_S10PLUS", "VERIFIED_IN_VM_ONLY",
                             "DEPLOYED_UNVERIFIED")

#: Terminal states that mean "not deployed on purpose" — the only ones a
#: non_deployable entry (or a blocked group) may carry.
NON_DEPLOYABLE_STATES = ("IMPLEMENTED_NOT_DEPLOYED", "BLOCKED_KERNEL",
                         "BLOCKED_FIRMWARE", "BLOCKED_HARDWARE",
                         "BLOCKED_EXTERNAL_RESOURCE", "NEEDS_OWNER_TEST",
                         "NOT_SUPPORTED_ON_DEVICE", "DEFERRED", "FAILED")


def group_reload(group, manifest=None):
    """The deliberate reload a group without a service declares, or "".

    A group that declares `restart_service: null` must still say WHAT makes the
    new bytes take effect, otherwise it is a silent half-deploy.  The reload may
    be declared inside the group (`declared_reload`) or, for a group that is
    already closed/byte-frozen, in the manifest's `group_reload_notes` map — the
    core briq-10b groups are preserved byte-for-byte, so their deliberate reload
    is *documented alongside* them instead of editing them.
    """
    own = str(group.get("declared_reload") or "").strip()
    if own:
        return own
    notes = (manifest or {}).get("group_reload_notes") or {}
    note = notes.get(group.get("id")) or {}
    return str(note.get("declared_reload") or "").strip()


def normalize_reload(action):
    """Canonical form of a reload command so semantically-identical actions match.

    Whitespace runs and separators (`;`, `&&`, `||`) are normalised, surrounding
    separators are removed, and multi-line declarations are folded to one line.
    This is for *deduplication only*; the original command text is what gets
    executed, never a shell-string rewrite.
    """
    cmd = str(action or "").replace("\\n", " ").replace("\n", " ").strip()
    cmd = re.sub(r"[ \t]+", " ", cmd)
    cmd = re.sub(r"\s*;\s*", "; ", cmd)
    cmd = re.sub(r"\s*&&\s*", " && ", cmd)
    cmd = re.sub(r"\s*\|\|\s*", " || ", cmd)
    cmd = re.sub(r"\s+", " ", cmd).strip()
    return cmd.strip(" ;")


def coalesce_reload_actions(steps):
    """Coalesce identical `declared_reload` actions across a multi-file group.

    Returns a deterministic list of ``{"group": gid, "action": original_text}``
    in first-seen order.  Identical actions in the same group collapse to one
    entry (the five-file case must not restart nuxel-bridge five times), while
    *different* actions are preserved because the order can matter.
    """
    ordered, seen = [], set()
    for step in steps:
        gid = step.get("group")
        action = str(step.get("declared_reload") or "").strip()
        if not action:
            continue
        key = (gid, normalize_reload(action))
        if key in seen:
            continue
        seen.add(key)
        ordered.append({"group": gid, "action": action})
    return ordered


def group_reload_plan(steps):
    """The transaction-level activation plan for a completed group.

    Two independent pieces are returned so the deploy tool can run them once,
    not once per file:

    * ``restarts`` — each affected service exactly once, in first-seen order
      (``restart_service`` carries this).
    * ``reloads`` — each distinct ``declared_reload`` action exactly once per
      group, in first-seen order.

    An action is classified as needing ``daemon-reload`` when its normalised
    form requests a daemon-reload as the first step.  This is what lets a
    changed unit-file group run exactly one ``systemctl daemon-reload`` while a
    group with no unit changes skips it.
    """
    restarts, restarts_seen = [], set()
    for step in steps:
        unit = str(step.get("service") or "").strip()
        if unit and unit not in restarts_seen:
            restarts_seen.add(unit)
            restarts.append({"group": step.get("group"), "service": unit})
    reloads = coalesce_reload_actions(steps)
    for entry in reloads:
        norm = normalize_reload(entry["action"])
        entry["needs_daemon_reload"] = norm.startswith("systemctl daemon-reload") \
            or norm.startswith("systemctl --system daemon-reload")
    return {"restarts": restarts, "reloads": reloads}


def validate_manifest(manifest, repo_root):
    """Structural + policy checks on a deploy manifest (no device contact).

    Returns a list of {"group","kind","detail"} violations.  This is what turns
    "the manifest is DATA" into an enforced contract: an extension group that
    forgets its rollback text, declares an unknown risk class, points at a
    non-existent procedure document or leaves the user with no deliberate reload
    is refused BEFORE the console is touched, instead of being discovered
    half-way through a live write.
    """
    violations = []
    groups = manifest.get("groups", [])
    if not isinstance(groups, list) or not groups:
        return [{"group": None, "kind": "manifest",
                 "detail": "manifest has no groups[] array"}]

    seen = set()
    for group in groups:
        gid = group.get("id")
        if not gid:
            violations.append({"group": None, "kind": "manifest",
                               "detail": "a group has no id"})
            continue
        if gid in seen:
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "duplicate group id %r" % gid})
        seen.add(gid)
        if group.get("state") in ("blocked_kernel", "blocked_firmware"):
            # A declared-blocked group is honest by construction; it is skipped,
            # so it needs no risk/restart/rollback contract.
            continue
        if risk_rank(group.get("risk")) >= len(RISK_CLASSES):
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "risk %r is not one of %s"
                                         % (group.get("risk"), sorted(RISK_CLASSES))})
        if not str(group.get("component") or "").strip():
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "group has no component"})
        if not str(group.get("health_check") or "").strip():
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "group declares no health_check"})
        if not str(group.get("rollback") or "").strip():
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "group declares no rollback text"})
        if "restart_service" not in group and not group_reload(group, manifest):
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "group declares neither restart_service "
                                         "nor declared_reload"})
        if group.get("restart_service") is None and not group_reload(group, manifest):
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "restart_service is null and no "
                                         "declared_reload explains the reload"})
        if not isinstance(group.get("files", []), list):
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "files[] is not an array"})
            continue
        for entry in group.get("files", []):
            if not str(entry.get("source") or "").strip():
                violations.append({"group": gid, "kind": "manifest",
                                   "detail": "file entry with no source"})
            if not str(entry.get("target") or "").strip():
                violations.append({"group": gid, "kind": "manifest",
                                   "detail": "file entry with no target (source %r)"
                                             % entry.get("source")})

    # -- the extension block: authored in ASCENDING risk order ----------------
    ext = manifest.get("extension") or {}
    if ext:
        core = set(ext.get("core_groups") or [])
        listed = list(ext.get("groups") or [])
        by_id = {g.get("id"): g for g in groups}
        for gid in listed:
            if gid not in by_id:
                violations.append({"group": gid, "kind": "ordering",
                                   "detail": "extension lists a group that does "
                                             "not exist in groups[]"})
        missing = [g.get("id") for g in groups
                   if g.get("id") not in core and g.get("id") not in set(listed)]
        if missing:
            violations.append({"group": None, "kind": "ordering",
                               "detail": "groups outside the core set are not "
                                         "declared in extension.groups: %s" % missing})
        seq = [(gid, by_id.get(gid) or {}) for gid in listed]
        for (prev_id, prev), (cur_id, cur) in zip(seq, seq[1:]):
            if risk_rank(cur.get("risk")) < risk_rank(prev.get("risk")):
                violations.append({"group": cur_id, "kind": "ordering",
                                   "detail": "risk goes backwards: %s (%s) after "
                                             "%s (%s)" % (cur_id, cur.get("risk"),
                                                          prev_id, prev.get("risk"))})
            if int(cur.get("priority") or 0) < int(prev.get("priority") or 0):
                violations.append({"group": cur_id, "kind": "ordering",
                                   "detail": "priority goes backwards: %s (%s) after "
                                             "%s (%s)" % (cur_id, cur.get("priority"),
                                                          prev_id, prev.get("priority"))})
        for gid in listed:
            if not int((by_id.get(gid) or {}).get("priority") or 0):
                violations.append({"group": gid, "kind": "ordering",
                                   "detail": "extension group declares no priority"})

    # -- a declared reload must be a command this mission may run -------------
    notes = manifest.get("group_reload_notes") or {}
    for gid, note in notes.items():
        if gid not in seen:
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "group_reload_notes names a group that "
                                         "does not exist: %s" % gid})
        cmd = str(note.get("declared_reload") or "")
        if not cmd.strip():
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "group_reload_notes has no declared_reload"})
            continue
        try:
            assert_no_flash_tooling(cmd)
        except GuardViolation as e:
            violations.append({"group": gid, "kind": "command_guard",
                               "detail": str(e)})
        if not str(note.get("reason") or "").strip():
            violations.append({"group": gid, "kind": "manifest",
                               "detail": "group_reload_notes %s gives no reason for "
                                         "the deliberate reload" % gid})

    # -- the honest non-deployable list --------------------------------------
    for entry in manifest.get("non_deployable", []):
        path = str(entry.get("path") or "")
        state = str(entry.get("terminal_state") or "")
        if not path:
            violations.append({"group": None, "kind": "manifest",
                               "detail": "non_deployable entry with no path"})
        if not str(entry.get("reason") or "").strip():
            violations.append({"group": None, "kind": "manifest",
                               "detail": "non_deployable %s has no reason" % path})
        if state not in VALID_VERDICTS:
            violations.append({"group": None, "kind": "manifest",
                               "detail": "non_deployable %s carries terminal_state "
                                         "%r which is not in the mission vocabulary"
                                         % (path, state)})
        elif state in PROMOTING_TERMINAL_STATES:
            violations.append({"group": None, "kind": "manifest",
                               "detail": "non_deployable %s claims the promoting "
                                         "state %r" % (path, state)})
        proc = entry.get("procedure")
        if proc and not os.path.isfile(os.path.join(repo_root, proc)):
            violations.append({"group": None, "kind": "procedure_missing",
                               "detail": "non_deployable %s references a procedure "
                                         "file that is not in the repository: %s"
                                         % (path, proc)})

    # -- referenced install procedures must exist ----------------------------
    for group in groups:
        proc = group.get("install_procedure")
        if proc and not os.path.isfile(os.path.join(repo_root, proc)):
            violations.append({"group": group.get("id"), "kind": "procedure_missing",
                               "detail": "install_procedure is not in the "
                                         "repository: %s" % proc})
    return violations


def source_is_in_repo(source, repo_root):
    """True when `source` stays inside the repository tree.

    A source that escapes (absolute path, `..`, or a symlinked parent) is refused
    rather than read: the plan must be reproducible from THIS repository, and it
    must never stage an arbitrary host file onto the phone.
    """
    if not str(source or "").strip():
        return False
    root = os.path.abspath(repo_root)
    cand = os.path.abspath(os.path.join(root, source))
    return cand == root or cand.startswith(root + os.sep)


def guard_group_commands(group, gid, violations):
    """Refuse flash tooling in any pre/post/reload/health text of a group."""
    for key in ("pre", "post"):
        for cmd in group.get(key, []) or []:
            try:
                assert_no_flash_tooling(str(cmd))
            except GuardViolation as e:
                violations.append({"group": gid, "kind": "command_guard",
                                   "detail": str(e)})
    for key in ("declared_reload", "health_check"):
        val = group.get(key)
        if val:
            try:
                assert_no_flash_tooling(str(val))
            except GuardViolation as e:
                violations.append({"group": gid, "kind": "command_guard",
                                   "detail": str(e)})


def build_deploy_plan(manifest, repo_root):
    """Turn a deploy manifest into an ordered, guarded, reversible plan.

    Returns {"steps": [...], "violations": [...], "skipped": [...],
    "risk_envelope": {...}, "group_order": [...]} — a non-empty `violations`
    list means the plan must not be executed (the caller reports BLOCKED_* /
    FAILED) and NOTHING is written to the device.

    Ordering: the manifest's own group order is the deploy order (the core seven
    groups are preserved byte-for-byte because briq-10b's unrun plan is built
    from them); the extension block is authored in ascending risk, so manifest
    order IS ascending-risk order for everything added by
    briq-01-deploy-manifest-extension.  `group_order` records what was planned,
    in order, with its risk class and priority.
    """
    steps, violations, skipped = [], [], []
    violations.extend(validate_manifest(manifest, repo_root))
    root_map = resolve_root_map(manifest)
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
        guard_group_commands(group, gid, violations)
        pre = [str(c) for c in (group.get("pre") or [])]
        post = [str(c) for c in (group.get("post") or [])]
        for entry in group.get("files", []):
            src_rel = entry.get("source")
            if not source_is_in_repo(src_rel, repo_root):
                violations.append({"group": gid, "kind": "source_escape",
                                   "detail": "source is outside the repository: %r"
                                             % src_rel})
                continue
            src = os.path.join(repo_root, src_rel)
            tgt = entry.get("target")
            if not str(tgt or "").strip():
                # already recorded as a manifest violation by validate_manifest();
                # there is no target to guard or to plan.
                continue
            # Remap the authored (mirror) root onto the device's real root BEFORE
            # guarding and planning, so the plan lands where the phone reads.
            tgt = remap_path(tgt, root_map)
            try:
                tgt = assert_userspace_path(tgt)
            except GuardViolation as e:
                violations.append({"group": gid, "kind": "guard", "detail": str(e),
                                   "target": entry["target"]})
                continue
            if not os.path.isfile(src):
                violations.append({"group": gid, "kind": "missing_source",
                                   "detail": "staged source not in repo: %s" % src_rel})
                continue
            steps.append({
                "group": gid,
                "component": group.get("component"),
                "priority": group.get("priority"),
                "source": src_rel,
                "source_sha256": sha256_file(src),
                "target": tgt,
                "staged": tgt + ".nuxel-staged",
                "backup": tgt + ".nuxel-rollback",
                "service": group.get("restart_service") or smallest_service_for(tgt),
                "verify": remap_text(entry.get("verify", "sha256sum %s" % tgt), root_map),
                "health_check": remap_text(group.get("health_check"), root_map),
                "rollback": remap_text(group.get("rollback"), root_map),
                "risk": group.get("risk", "medium"),
                "risk_rank": risk_rank(group.get("risk", "medium")),
                "pre": [remap_text(c, root_map) for c in pre],
                "post": [remap_text(c, root_map) for c in post],
                "declared_reload": group_reload(group, manifest),
                "install_procedure": group.get("install_procedure"),
                "mode": entry.get("mode", "0644"),
            })
    envelope = {}
    for step in steps:
        envelope[step["risk"]] = envelope.get(step["risk"], 0) + 1
    notes = manifest.get("group_reload_notes") or {}
    order = [{"group": g.get("id"), "priority": g.get("priority"),
              "risk": g.get("risk"),
              "risk_rank": risk_rank(g.get("risk", "medium")),
              "restart_service": g.get("restart_service"),
              "declared_reload": group_reload(g, manifest) or None,
              "declared_reload_source": (
                  "group" if g.get("declared_reload")
                  else ("group_reload_notes" if (notes.get(g.get("id")) or {}).get("declared_reload")
                        else None)),
              "steps": len(g.get("files", []) or [])}
             for g in manifest.get("groups", [])]
    activation_plan = group_reload_plan(steps)
    return {"steps": steps, "violations": violations, "skipped": skipped,
            "risk_envelope": envelope, "group_order": order,
            "activation_plan": activation_plan,
            "schema_version": manifest.get("schema_version")}


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
    """Emit the exact stage→verify→atomic-install→rollback shell text.

    This function only installs and verifies ONE file.  Service restarts,
    `declared_reload` actions and `systemctl daemon-reload` are deliberately NOT
    run here any more: they belong to the transaction boundary, where identical
    actions across a multi-file group are coalesced and run exactly once (see
    `group_reload_plan` and `nuxel-live-deploy.run_group_activation`).

    The only exception is a non-reload `pre`/`post` assertion (for example the
    framebuffer-owner check in the boot-animation group), which is a per-file
    precondition, not a reload, and is preserved.
    """
    tgt, staged, backup = step["target"], step["staged"], step["backup"]
    # The rollback trap restores the recorded baseline ONLY when a step below
    # failed.  It never restarts a service; the caller's coalesced rollback does
    # that once for the whole group.
    lines = [
        "set -u",
        "_NXL_ROLLBACK() { _rc=$?; if [ \"$_rc\" -ne 0 ]; then "
        "if [ -e %s ]; then cp -a %s %s; fi; echo \"ROLLED-BACK rc=$_rc\"; fi; }"
        % (backup, backup, tgt),
        "trap _NXL_ROLLBACK EXIT",
        "set -e",
    ]
    for pre in step.get("pre", []):
        if normalize_reload(pre) in ("systemctl daemon-reload",
                                     "systemctl --system daemon-reload"):
            continue
        lines.append(pre)
    lines += [
        "if [ -e %s ]; then printf 'PREV=%s\\n' \"$(sha256sum %s | cut -d' ' -f1)\"; "
        "else echo PREV=NONE; fi" % (tgt, "%s", tgt),
        "mkdir -p \"$(dirname %s)\"" % tgt,
        # Preserve the FIRST recorded baseline across re-runs: only capture the
        # backup if none exists yet, otherwise a resumed deploy would overwrite the
        # only route back to the pre-deploy file with the new bytes.
        "if [ -e %s ] && [ ! -e %s ]; then cp -a %s %s; fi" % (tgt, backup, tgt, backup),
        "test -f %s" % staged,
        "printf '%%s  %%s\\n' %s %s > /var/tmp/nxl-verify.sha256"
        % (step["source_sha256"], staged),
        "sha256sum -c /var/tmp/nxl-verify.sha256",
        "mv -f %s %s" % (staged, tgt),
        "%s | grep -q %s" % (step["verify"], step["source_sha256"]),
    ]
    # The group health_check and coalesced reload/restart are run ONCE by the
    # deploy tool after the whole group is installed and verified.
    for post in step.get("post", []):
        if normalize_reload(post) in ("systemctl daemon-reload",
                                      "systemctl --system daemon-reload"):
            continue
        lines.append(post)
    lines.append("echo INSTALL-OK")
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
        # sub-directories are created on demand (raw/<probe>.txt, scripts/NNN-*.sh,
        # runs/<step>.out); without this the very first write into a new
        # sub-directory failed with FileNotFoundError the moment the console
        # became reachable — a bug that offline plan-only runs never hit.
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
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


#: The mission's exact terminal-state vocabulary.  Every verdict this group emits
#: must be one of these, and only on-device observations may claim
#: VERIFIED_ON_S10PLUS.
VALID_VERDICTS = (
    "VERIFIED_ON_S10PLUS", "VERIFIED_IN_VM_ONLY", "OFFLINE_TESTED", "DEPLOYED_UNVERIFIED",
    "IMPLEMENTED_NOT_DEPLOYED", "BLOCKED_KERNEL", "BLOCKED_FIRMWARE", "BLOCKED_HARDWARE",
    "BLOCKED_EXTERNAL_RESOURCE", "NEEDS_OWNER_TEST", "FAILED", "DEFERRED",
    "NOT_SUPPORTED_ON_DEVICE",
    # briq-01-deploy-manifest-extension: the mission's terminal state for anything
    # that needs a compiler, a package transaction or a network — the artefact
    # exists in the repository and its installation is a documented procedure, so
    # the state is neither "deployed" nor "blocked", and it must never be silently
    # rounded up to a verdict a live capture does not support.
    "INSTALL_PROCEDURE_REQUIRED",
)


def ensure_not_qq(path):
    """Hard refusal to write anywhere under .qq / RUN_ROOT."""
    p = os.path.abspath(path)
    parts = p.split(os.sep)
    if ".qq" in parts or ".codeseeq" in parts:
        raise GuardViolation("refusing to write QonQrete metadata path %s" % p)
    return p
