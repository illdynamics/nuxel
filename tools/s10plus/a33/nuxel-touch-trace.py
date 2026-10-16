#!/usr/bin/env python3
"""nuxel-touch-trace — end-to-end touch pipeline tracer for the Nuxel S10+.

THE CHAIN THIS WALKS (mission priority 0):

    1 sec_ts driver binding      dmesg sec_ts/sec_touchscreen, /sys/bus/i2c/devices/4-0048,
                                 the sec_ts_init return path, and the one boot flag that
                                 removes the driver entirely (charger/LPM mode)
    2 IRQ delivery               /proc/interrupts delta for the sec_ts line over a 2 s window
    3 evdev node production      /proc/bus/input/devices + a CAPABILITY scan
                                 (EVIOCGID / EVIOCGNAME / EVIOCGPROP / EVIOCGBIT / EVIOCGABS,
                                 including ABS_MT_SLOT contact-slot capacity)
    4 libinput acceptance        /run/nuxel-libinput-path.state  'accepted=1'
    5 compositor input fds       /proc/<phoc MainPID>/fd -> how many are /dev/input nodes
    6 Wayland seat / focus       bounded WAYLAND_DEBUG / journal capture of wl_touch + seat state
    7 WebKitGTK DOM events       the injected instrumented page logging touchstart/move/end
                                 with coordinates (touch-probe.html + /run/nuxel-touch-dom.log,
                                 and the host's own NUXEL_INPUT diag lines in /run/nuxel-home.state)

For every layer it prints exactly one machine-readable line:

    LAYER=<n> NAME=<name> STATE=<ok|drop|blocked> EVIDENCE=<path> DETAIL=<one line>

and then names the FIRST layer that fails to deliver:

    FIRST_FAIL_LAYER=<n|none>

STATE semantics (stated once, used everywhere):
    ok       this layer provably carried (or is ready to carry) a real touch event
    drop     this layer exists but did not deliver - the pipeline stops HERE
    blocked  this layer could not be evaluated (no evidence / precondition absent),
             which is NOT a pass: a missing capture is never reported as ok

NO FABRICATED EVIDENCE: every verdict names a file in the evidence bundle, and a
layer with no capture is `blocked`, never `ok`.  A passing run of this tool on a
desk with no finger is not a touch verification - it is a pipeline state report.

BOUNDED BY CONSTRUCTION (the live console must never hang):
    --seconds N      wall-clock budget for the whole session   (default 20)
    --max-events M   hard cap on decoded input events          (default 2000)
    --max-bytes B    hard cap on raw bytes read                (default 262144)
    signal.alarm()   hard timeout at --seconds + SLACK; on expiry the bundle is
                     flushed and the verdict is printed for what was collected
    every subprocess runs under its own timeout and is killed on expiry

USAGE
    # on the phone, as root, with the finger ready (bounded capture session)
    nuxel-touch-trace.py --live --out /var/lib/nuxel/touch-trace

    # drive the capture from a Mac over the live console (no interactive shell)
    nuxel-touch-trace.py --live --seconds 30 --expect-finger

    # offline analysis of a captured bundle, or of any archived capture dir
    nuxel-touch-trace.py --analyze /var/lib/nuxel/touch-trace
    nuxel-touch-trace.py --analyze scripts/s10plus-debug-pack/captures/<ts>-A20-live-run

The analyzer works on a bundle produced by --live AND, best effort, on any
directory that contains archived capture text (dmesg/ram-console dumps,
/proc/bus/input/devices dumps, libinput shim state, ...): it searches the tree for
the evidence patterns instead of trusting a fixed name, so an old debug pack can
be graded with the same rules as a fresh bundle.

CAPABILITY DISCOVERY (never a node number)
    Two independent identity sources are read and cross-reported:
      * /sys/class/input/<node>/device/  - name, id/bustype+vendor+product, the
        capability bitmaps (properties / capabilities/abs / capabilities/key) and,
        where the kernel exposes it, per-axis absinfo.  NUXEL_SYSFS_INPUT_ROOT (or
        --sysfs-root) redirects this at a synthetic tree so the same code runs
        offline, and the A33 tests do exactly that.
      * the evdev ioctls (EVIOCGID/EVIOCGNAME/EVIOCGPROP/EVIOCGBIT/EVIOCGABS) on
        every /dev/input node, which is what ACTUALLY decides the selection: the
        node's own input_id (EVIOCGID), the absolute ranges and the contact-slot
        capacity (EVIOCGBIT(EV_ABS)+EVIOCGABS(ABS_MT_SLOT)) are only obtainable
        from the ioctl.
    The raw `properties` value is always printed next to its interpretation.  On
    this handset the panel node reports a raw value whose INPUT_PROP_DIRECT bit
    (used, as everywhere in the A32/A33 baseline, as a BIT INDEX) is set; that
    convention is what the deployed A31 shim shares, so it is reported and never
    silently "corrected" here - a divergence must be visible, not papered over.

COORDINATE VALIDATION (1440x3040 DECON panel)
    fb0 is the DECON framebuffer: /sys/class/graphics/fb0/modes is `U:1440x3040p-0`
    (the panel) and virtual_size is `1440,6080` (two pages, which the animation and
    the bridge flip between).  The tool reads those, composes raw ABS_MT ->
    panel pixels -> compositor output pixels, and every captured point is checked
    against the device's own reported range AND against the panel bounds.

BOUNDED CAPTURE SESSION (--capture SECONDS)
    --capture N is --live with N seconds and a per-event JSONL record stream
    (events.jsonl: kernel timeval timestamp, decoded kind, raw coordinates and the
    mapped panel/output coordinates) plus coordinate-map.json.  It is sized for the
    owner's finger taps and is bounded exactly like --live (hard alarm, caps).
    --archive-dir (or --archive DIR afterwards) copies the finished bundle into
    docs/beta-finalization/live/evidence/touch-<ts>/ so the evidence lands in the
    repository instead of only on the phone.

EXIT STATUS
    Every layer reports its own exit code (`LAYER_EXIT=<n> ... EXIT=<10+n>`), and
    with --layer-exit-codes the process itself exits 10+<first lossy layer> so a
    wrapper can branch on the exact hop instead of parsing text.  The historical
    0/3/4 statuses are unchanged without that flag.
"""
import argparse
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time

# ---------------------------------------------------------------------------
# constants: kernel ABI + the paths this pipeline actually uses
# ---------------------------------------------------------------------------
INPUT_DIR = "/dev/input"
I2C_TOUCH_ADDR = "4-0048"                      # sec_ts on hsi2c-4 (A26/A31/A32 record)
I2C_SYSFS = "/sys/bus/i2c/devices/" + I2C_TOUCH_ADDR
SEC_TS_NAME = "sec_touchscreen"
LIBINPUT_STATE = "/run/nuxel-libinput-path.state"
LAUNCHER_STATE = "/run/nuxel-home.state"
BRIDGE_STATE = "/run/nuxel-wl-fb.state"
DOM_LOG = "/run/nuxel-touch-dom.log"
TOUCH_PROBE_STAGED = "/run/nuxel-touch-probe.staged"
COMPOSITOR_UNIT = "nuxel-wayland"
A32_BITMAP_DECODER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "a32", "tests", "input-bitmap-decode.py")

EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
SYN_REPORT = 0x00
ABS_MT_SLOT = 0x2F
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36
ABS_MT_TRACKING_ID = 0x39
BTN_TOUCH = 0x14A
INPUT_PROP_DIRECT = 1

EV_FMT = "llHHi"                               # struct input_event, arm64 4.14
EV_SIZE = struct.calcsize(EV_FMT)              # 24 bytes

LOCAL_EVCAL = 1                                # EVIOCGNAME(64)
EVIOCGNAME = 0x80000000 | (64 << 16) | (0x45 << 8) | 0x06
EVIOCGBIT = lambda ev, ln: 0x80000000 | (ln << 16) | (0x45 << 8) | (0x20 + ev)
EVIOCGABS = lambda ax: 0x80000000 | (24 << 16) | (0x45 << 8) | (0x40 + ax)
EVIOCGPROP = lambda ln: 0x80000000 | (ln << 16) | (0x45 << 8) | 0x09
EVIOCGID = 0x80000000 | (8 << 16) | (0x45 << 8) | 0x02       # struct input_id = 4 x u16

SLACK_SECONDS = 15                             # hard alarm = --seconds + this

# --- capability discovery + panel geometry (briq-01a) ----------------------
# NUXEL_SYSFS_INPUT_ROOT redirects the sysfs scan so the offline tests drive the
# same code with a synthetic tree (a workstation has no sec_ts).
SYSFS_INPUT_ROOT = os.environ.get("NUXEL_SYSFS_INPUT_ROOT", "/sys/class/input")
SYSFS_FB = os.environ.get("NUXEL_SYSFS_FB", "/sys/class/graphics/fb0")
NODE_PREFIX = "event"                # entries matched by prefix + numeric suffix
# DECON panel measured on the handset (/sys/class/graphics/fb0/modes ->
# `U:1440x3040p-0`).  Used only when the framebuffer is not readable (a host).
PANEL_FALLBACK = (1440, 3040)
# The direct-touch marker, used exactly as the A32/A33 baseline uses it: the
# constant is a BIT INDEX into the printed bitmap, and the panel's raw value is
# reported next to the interpretation so a divergence is visible.
INPUT_PROP_DIRECT_BIT = INPUT_PROP_DIRECT
# The repository's archive root for live evidence; overridden by --archive-dir.
RUN_ROOT_ARCHIVE = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
    "docs", "beta-finalization", "live", "evidence"))

LAYERS = [
    (1, "driver", "sec_ts binding / -ENODEV gate (charger-mode LPM)"),
    (2, "irq", "IRQ delivery (sec_ts line delta over a 2 s window)"),
    (3, "evdev", "evdev node production (capability-selected, never by number)"),
    (4, "libinput", "libinput acceptance through the capability shim"),
    (5, "compositor", "phoc input fds (/proc/<MainPID>/fd -> input nodes)"),
    (6, "wayland", "Wayland seat / focus / wl_touch"),
    (7, "dom", "WebKitGTK DOM touchstart/move/end with coordinates"),
]
LAYER_NAMES = {n: nm for n, nm, _ in LAYERS}

# Exit status vocabulary: 10 + the layer number names the FIRST hop that lost the
# event.  Used for the per-layer LAYER_EXIT lines always, and for the process exit
# status when --layer-exit-codes is given.
LAYER_EXIT_BASE = 10
EXIT_OK = 0
EXIT_GATE_FAIL = 3
LAYER_EXIT_CODES = {n: LAYER_EXIT_BASE + n for n, _nm, _d in LAYERS}


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------
def say(msg):
    print(msg, flush=True)


def read_text(path, limit=262144):
    try:
        with open(path, "rb") as f:
            data = f.read(limit)
        return data.decode("utf-8", "replace")
    except OSError:
        return ""


def run_cmd(argv, timeout=8):
    """Run a command with a hard timeout.  Never raises; returns (rc, out)."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "not found: %s" % argv[0]
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"") if isinstance(e.stdout, bytes) else (e.stdout or "")
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return 124, "timeout after %ss\n%s" % (timeout, out)
    except OSError as e:
        return 126, "exec error: %s" % e


def load_bitmap_decoder():
    """Reuse tools/s10plus/a32/tests/input-bitmap-decode.py (the decode already
    validated against the live gpio_keys line) instead of re-deriving it."""
    path = os.path.normpath(A32_BITMAP_DECODER)
    if not os.path.isfile(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("nuxel_input_bitmap_decode", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


_DECODER = load_bitmap_decoder()


def decode_key_bitmap(line):
    """Decode a `B: KEY=...` line.  Prefers the shared A32 decoder."""
    if not line or "KEY=" not in line:
        return None
    if _DECODER is not None:
        try:
            return _DECODER.decode(line)
        except Exception:
            pass
    words = line.split("KEY=")[1].split()
    words = [int(w, 16) for w in words if w]
    out = set()
    for idx, w in enumerate(words):
        wi = len(words) - 1 - idx
        for bit in range(64):
            if w & (1 << bit):
                out.add(wi * 64 + bit)
    return sorted(out)


# ---------------------------------------------------------------------------
# evidence bundle
# ---------------------------------------------------------------------------
class Bundle:
    """A directory of captured evidence.  The verdict lines all point here."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        os.makedirs(self.path, exist_ok=True)
        self.meta = {"tool": "nuxel-touch-trace", "version": 1,
                     "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def put(self, name, text):
        p = os.path.join(self.path, name)
        with open(p, "w") as f:
            f.write(text if isinstance(text, str) else text.decode("utf-8", "replace"))
        return p

    def put_bytes(self, name, data):
        p = os.path.join(self.path, name)
        with open(p, "wb") as f:
            f.write(data)
        return p

    def ev(self, name):
        return os.path.join(self.path, name)

    def finalize(self):
        self.meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.put("meta.json", json.dumps(self.meta, indent=2) + "\n")


class Result:
    def __init__(self, n, name, state, evidence, detail=""):
        self.n, self.name, self.state, self.evidence, self.detail = n, name, state, evidence, detail

    def emit(self):
        say("LAYER=%d NAME=%s STATE=%s EVIDENCE=%s DETAIL=%s"
            % (self.n, self.name, self.state, self.evidence, self.detail.replace("\n", " ")[:240]))


def summarize(results):
    first = next((r.n for r in results if r.state != "ok"), None)
    first_drop = next((r.n for r in results if r.state == "drop"), None)
    say("FIRST_FAIL_LAYER=%s" % ("none" if first is None else first))
    say("FIRST_DROP_LAYER=%s" % ("none" if first_drop is None else first_drop))
    if first is None:
        say("VERDICT=PIPELINE_DELIVERED end-to-end (driver -> ... -> DOM)")
    else:
        say("VERDICT=PIPELINE_STOPPED_AT_LAYER=%d NAME=%s STATE=%s"
            % (first, LAYER_NAMES.get(first, "?"), next(r.state for r in results if r.n == first)))
    return first


def self_check_limits(seconds, max_events, max_bytes):
    if seconds <= 0 or seconds > 900:
        raise SystemExit("--seconds must be 1..900 (bounded session): got %r" % seconds)
    if max_events <= 0 or max_bytes <= 0:
        raise SystemExit("--max-events/--max-bytes must be positive")


# ---------------------------------------------------------------------------
# live collectors
# ---------------------------------------------------------------------------
# (human explanation, regex, weak)  - `weak` patterns are only accepted when the
# matching LINE also looks like a kernel command line, so prose that merely
# mentions lpcharge cannot be graded as device evidence.
CHARGER_PATTERNS = [
    ("cmdline androidboot.mode=charger", r"androidboot\.mode=charger", False),
    ("cmdline lpcharge=1", r"\blpcharge=1\b", True),
    ("dmesg sec_bat_is_lpm_check: Low power charging mode: 1", r"Low power charging mode:\s*1", False),
    ("dmesg sec_ts_init: Do not load driver due to : lpm 1", r"sec_ts_init:\s*Do not load driver due to", False),
]


def collect_boot(bundle):
    """Everything that decides whether the driver even exists on this boot."""
    cmdline = read_text("/proc/cmdline").strip()
    rc, dmesg = run_cmd(["dmesg"], timeout=8)
    if rc != 0 or not dmesg.strip():
        # Older/limited images: the ram console carries the same record.
        for alt in ("/proc/last_kmsg", "/sys/fs/pstore/console-ramoops-0"):
            if os.path.exists(alt):
                dmesg = read_text(alt, 4 << 20)
                break
        rc = 0 if dmesg else rc
    sysfs = ""
    for p in (I2C_SYSFS, I2C_SYSFS + "/driver", I2C_SYSFS + "/name", "/sys/class/sec/tsp/status"):
        sysfs += "=== %s ===\n" % p
        if os.path.islink(p):
            sysfs += "symlink -> %s\n" % os.readlink(p)
        elif os.path.isdir(p):
            try:
                sysfs += "\n".join(sorted(os.listdir(p))[:40]) + "\n"
            except OSError as e:
                sysfs += "unreadable: %s\n" % e
        else:
            sysfs += read_text(p, 4096) or "(absent)\n"
    acts = "\n".join("/sys/module/%s = %s" % (m, os.path.exists("/sys/module/" + m))
                     for m in ("sec_ts", "sec_ts_y771", "sec_touchscreen"))
    text = ("# /proc/cmdline\n%s\n\n# driver sysfs\n%s\n\n# module presence\n%s\n\n# dmesg/ram-console (sec_ts excerpt)\n%s\n"
            % (cmdline, sysfs, acts,
               "\n".join(l for l in dmesg.splitlines()
                         if re.search(r"sec_ts|sec_touchscreen|sec_input|is_lpm|lpcharge|tsp_", l, re.I))[-20000:]))
    bundle.put("boot-driver.txt", text)
    modes = [why for why, pat, _weak in CHARGER_PATTERNS
             if re.search(pat, cmdline, re.I) or re.search(pat, dmesg, re.I)]
    bundle.meta["boot_mode"] = "charger/LPM" if modes else "normal"
    return {"cmdline": cmdline, "dmesg": dmesg, "charger": modes,
            "i2c_present": os.path.exists(I2C_SYSFS),
            "i2c_driver": os.path.realpath(I2C_SYSFS + "/driver") if os.path.islink(I2C_SYSFS + "/driver") else "",
            "registered": bool(re.search(r"input:\s*" + SEC_TS_NAME + r"\s+as\s+\S+", dmesg)),
            "evidence": bundle.ev("boot-driver.txt")}


def collect_interrupts(bundle, tag):
    """One /proc/interrupts snapshot; the sec_ts line's counters are summed."""
    txt = read_text("/proc/interrupts")
    bundle.put("interrupts-%s.txt" % tag, txt)
    if not txt:
        return None
    hit = None
    for line in txt.splitlines()[1:]:
        head = line.split(":")[0].strip()
        if not head.isdigit():
            continue
        if re.search(r"sec_ts|sec_touchscreen|" + I2C_TOUCH_ADDR, line, re.I):
            counts = [int(x) for x in line.split(":")[1].split() if x.isdigit()]
            hit = {"irq": int(head), "counts": counts, "total": sum(counts), "line": line.strip()}
            break
    return hit


def classify_driver(boot, bundle):
    if boot["charger"]:
        return Result(1, "driver", "blocked", boot["evidence"],
                      "charger/LPM boot (%s): sec_ts returns -ENODEV before i2c_add_driver, so no touch "
                      "device can exist on this boot. userspace mitigation = one NORMAL reboot "
                      "(docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md)" % "; ".join(boot["charger"]))
    if boot["registered"] and boot["i2c_present"]:
        return Result(1, "driver", "ok", boot["evidence"],
                      "sec_touchscreen registered (%s, driver=%s)"
                      % (I2C_TOUCH_ADDR, boot["i2c_driver"] or "?"))
    if boot["i2c_present"] and not boot["i2c_driver"]:
        return Result(1, "driver", "drop", boot["evidence"],
                      "%s present but NO driver bound (no /sys/bus/i2c/devices/%s/driver symlink)"
                      % (I2C_TOUCH_ADDR, I2C_TOUCH_ADDR))
    if boot["registered"]:
        return Result(1, "driver", "ok", boot["evidence"],
                      "sec_touchscreen registered in the kernel log")
    if re.search(r"sec_ts|sec_input", boot["dmesg"], re.I):
        return Result(1, "driver", "drop", boot["evidence"],
                      "sec_ts messages present but no 'input: sec_touchscreen as ...' registration")
    return Result(1, "driver", "blocked", boot["evidence"],
                  "no sec_ts evidence in this capture (dmesg/ram-console empty or unreadable?)")


def classify_irq(before, after, bundle, exercised, charger):
    ev = bundle.ev("interrupts-before.txt")
    if charger:
        return Result(2, "irq", "blocked", ev, "charger/LPM boot: the driver was never added, so it has no IRQ")
    if before is None and after is None:
        return Result(2, "irq", "blocked", ev, "no /proc/interrupts capture available")
    snap = after or before
    if snap is None:
        return Result(2, "irq", "drop", ev, "no sec_ts line in /proc/interrupts (IRQ never registered)")
    delta = (after["total"] - before["total"]) if (before and after) else None
    if delta is None:
        return Result(2, "irq", "blocked", ev, "only one interrupts snapshot taken; delta unavailable")
    if delta > 0:
        return Result(2, "irq", "ok", ev, "irq %d delivered %d event(s) in the window" % (snap["irq"], delta))
    if exercised:
        return Result(2, "irq", "drop", ev,
                      "irq %d present but delivered 0 events in the window while raw events were seen below it"
                      % snap["irq"])
    return Result(2, "irq", "blocked", ev,
                  "irq %d present, 0 events in the 2 s window (no finger activity in this window: "
                  "the layer was not exercised)" % snap["irq"])


def evdev_caps(path):
    """Read a node's identity from the KERNEL, never from its number."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        name = fcntl.ioctl(fd, EVIOCGNAME, b"\0" * 64).split(b"\0")[0].decode("utf-8", "replace")
        prop = bytearray(fcntl.ioctl(fd, EVIOCGPROP(8), b"\0" * 8))
        absb = bytearray(fcntl.ioctl(fd, EVIOCGBIT(EV_ABS, 8), b"\0" * 8))
        keyb = bytearray(fcntl.ioctl(fd, EVIOCGBIT(EV_KEY, 96), b"\0" * 96))
        bit = lambda bits, code: (bits[code // 8] >> (code % 8)) & 1

        # The node's OWN identity, from the node itself: EVIOCGID returns
        # `struct input_id { __u16 bustype, vendor, product, version; }`.  It is
        # reported next to the sysfs id/* values as a second, independent identity.
        try:
            iid = struct.unpack("<4H", fcntl.ioctl(fd, EVIOCGID, b"\0" * 8))
            ident = {"bustype": iid[0], "vendor": iid[1], "product": iid[2], "version": iid[3]}
        except (OSError, struct.error):
            ident = None

        def axis(ax):
            try:
                v = struct.unpack("6i", fcntl.ioctl(fd, EVIOCGABS(ax), b"\0" * 24))
                return (v[1], v[2])
            except OSError:
                return None
        # Contact-slot capacity: is ABS_MT_SLOT claimed by the node at all
        # (EVIOCGBIT(EV_ABS)) and, when it is, what the node's own
        # EVIOCGABS(ABS_MT_SLOT) range says.  max + 1 is the number of
        # simultaneous contacts the panel reports.
        slot_bit = bool(bit(absb, ABS_MT_SLOT))
        slot_range = axis(ABS_MT_SLOT)
        slots = (slot_range[1] + 1) if slot_range else None
        return {"path": path, "name": name, "id": ident,
                "direct": bool(bit(prop, INPUT_PROP_DIRECT)),
                "mt": bool(bit(absb, ABS_MT_POSITION_X) and bit(absb, ABS_MT_POSITION_Y)),
                "btn_touch": bool(bit(keyb, BTN_TOUCH)),
                "x": axis(ABS_MT_POSITION_X), "y": axis(ABS_MT_POSITION_Y),
                "tracking_id": bool(bit(absb, ABS_MT_TRACKING_ID)),
                "slot_bit": slot_bit, "slot_range": slot_range, "slots": slots}
    except OSError:
        return None
    finally:
        os.close(fd)


def scan_input_nodes(bundle):
    """Capability scan of the input directory.  NO node number is assumed: the
    directory is listed, every candidate is probed, and the choice is by capability."""
    lines, nodes = [], []
    try:
        entries = sorted((e for e in os.listdir(INPUT_DIR) if e.startswith("event")),
                         key=lambda e: int(re.sub(r"\D", "", e) or 0))
    except OSError as e:
        entries = []
        lines.append("cannot list %s: %s" % (INPUT_DIR, e))
    for e in entries:
        caps = evdev_caps(os.path.join(INPUT_DIR, e))
        if caps is None:
            lines.append("%-16s unreadable" % e)
            continue
        nodes.append(caps)
        ident = caps["id"]
        lines.append("%-16s name=%-24r direct=%d mt=%d btn_touch=%d abs_mt_x=%s abs_mt_y=%s tracking_id=%d "
                     "ioctl_id=%s slot_bit=%s slot_range=%s slots=%s"
                     % (e, caps["name"], caps["direct"], caps["mt"], caps["btn_touch"],
                        caps["x"], caps["y"], caps["tracking_id"],
                        ("bustype=0x%04x vendor=0x%04x product=0x%04x version=0x%04x"
                         % (ident["bustype"], ident["vendor"], ident["product"], ident["version"]))
                        if ident else "unreadable",
                        caps["slot_bit"], caps["slot_range"], caps["slots"]))
    proc = read_text("/proc/bus/input/devices")
    panel_line = ""
    for block in proc.split("\n\n"):
        if SEC_TS_NAME in block:
            panel_line = block.strip()
            break
    key_decoded = None
    for block in proc.split("\n\n"):
        if SEC_TS_NAME in block:
            for line in block.splitlines():
                if line.startswith("B: KEY="):
                    key_decoded = decode_key_bitmap(line)
    text = ("# capability scan of %s (selection is by EVIOCGPROP/EVIOCGBIT, never by number)\n"
            "# ioctl_id is the node's OWN EVIOCGID (struct input_id = 4 x u16); compare it with the\n"
            "# sysfs id/bustype+vendor+product values in sysfs-input.txt (second, independent identity).\n"
            "# slot_bit / slot_range / slots come from EVIOCGBIT(EV_ABS) + EVIOCGABS(ABS_MT_SLOT);\n"
            "# slots = the panel's contact-slot capacity (EVIOCGABS max + 1), i.e. simultaneous contacts.\n%s\n\n"
            "# /proc/bus/input/devices (full)\n%s\n\n# %s block\n%s\n\n"
            "# decoded KEY bitmap for %s (shared A32 decoder): BTN_TOUCH=%s present=%s\n"
            % (INPUT_DIR, "\n".join(lines), proc, SEC_TS_NAME, panel_line or "(absent)",
               SEC_TS_NAME, BTN_TOUCH, (BTN_TOUCH in key_decoded) if key_decoded else "unknown"))
    bundle.put("evdev.txt", text)
    touch = [c for c in nodes if c["mt"] and (c["direct"] or SEC_TS_NAME in c["name"])]
    panel = next((c for c in nodes if SEC_TS_NAME in c["name"]), None)
    return {"nodes": nodes, "touch": touch, "panel": panel, "proc_block": panel_line,
            "key_decoded": key_decoded, "evidence": bundle.ev("evdev.txt")}


def classify_evdev(scan, driver_state, charger):
    ev = scan["evidence"]
    panel = scan["panel"] or (scan["touch"][0] if scan["touch"] else None)
    if panel is not None and (panel["mt"] and panel["direct"]):
        return Result(3, "evdev", "ok", ev,
                      "panel %s name=%r PROP=DIRECT ABS_MT=present range x=%s y=%s EVIOCGID %s "
                      "contact_slots=%s (EVIOCGBIT claims ABS_MT_SLOT=%s, EVIOCGABS(ABS_MT_SLOT)=%s) "
                      "(selected by capability)"
                      % (panel["path"], panel["name"], panel["x"], panel["y"],
                         ("bustype=0x%04x vendor=0x%04x product=0x%04x"
                          % (panel["id"]["bustype"], panel["id"]["vendor"], panel["id"]["product"]))
                         if panel.get("id") else "unreadable",
                         panel.get("slots"), panel.get("slot_bit"), panel.get("slot_range")))
    if panel is not None and not panel["direct"]:
        return Result(3, "evdev", "drop", ev,
                      "panel node %s exists but INPUT_PROP_DIRECT is absent (PROP bitmap lacks bit %d): "
                      "libinput will not treat it as a touch surface" % (panel["path"], INPUT_PROP_DIRECT))
    if scan["proc_block"]:
        return Result(3, "evdev", "drop", ev,
                      "%s is present in /proc/bus/input/devices but no capability-scannable node was "
                      "found under %s" % (SEC_TS_NAME, INPUT_DIR))
    if charger:
        return Result(3, "evdev", "blocked", ev, "charger/LPM boot: no touch node can exist")
    if driver_state == "ok":
        return Result(3, "evdev", "drop", ev,
                      "driver reported bound but no DIRECT multitouch node exists in %s" % INPUT_DIR)
    return Result(3, "evdev", "blocked", ev,
                  "no touch node found and the driver layer did not establish one either")


def classify_libinput(bundle):
    state = read_text(LIBINPUT_STATE, 262144)
    ev = bundle.ev("libinput-path.state")
    if os.path.exists(LIBINPUT_STATE):
        bundle.put("libinput-path.state", state)
    else:
        bundle.put("libinput-path.state", "(absent: %s does not exist)\n" % LIBINPUT_STATE)
    accepted = [l for l in state.splitlines() if "accepted=1" in l]
    rejected = [l for l in state.splitlines() if "accepted=0" in l]
    assign = [l for l in state.splitlines() if "PATH_ASSIGN_SEAT" in l]
    if accepted:
        return Result(4, "libinput", "ok", ev, "%d accepted device(s); last: %s"
                      % (len(accepted), accepted[-1].strip()[:200]))
    if rejected or assign:
        return Result(4, "libinput", "drop", ev,
                      "shim ran but accepted 0 devices: %s"
                      % ((rejected[-1] if rejected else assign[-1]).strip()[:200]))
    return Result(4, "libinput", "blocked", ev,
                  "%s absent or empty: the shim never ran (or never logged)" % LIBINPUT_STATE)


def compositor_pid(bundle):
    pid, how = 0, ""
    rc, out = run_cmd(["systemctl", "show", "-p", "MainPID", "--value", COMPOSITOR_UNIT], timeout=4)
    if rc == 0 and out.strip().isdigit() and int(out.strip()) > 0:
        pid, how = int(out.strip()), "systemctl show -p MainPID --value %s" % COMPOSITOR_UNIT
    if not pid:
        rc, out = run_cmd(["pgrep", "-f", "phoc"], timeout=4)
        for line in out.split():
            if line.isdigit():
                pid, how = int(line), "pgrep -f phoc"
                break
    bundle.meta["compositor_pid"] = pid
    return pid, how


def classify_compositor(bundle):
    pid, how = compositor_pid(bundle)
    ev = bundle.ev("compositor-fds.txt")
    if not pid:
        bundle.put("compositor-fds.txt", "no compositor process found (%s)\n" % COMPOSITOR_UNIT)
        return Result(5, "compositor", "blocked", ev,
                      "compositor not running: no %s unit MainPID and no phoc process" % COMPOSITOR_UNIT)
    fddir = "/proc/%d/fd" % pid
    rows, inputs = [], []
    try:
        for fd in sorted(os.listdir(fddir), key=lambda x: int(x) if x.isdigit() else 0):
            try:
                tgt = os.readlink(os.path.join(fddir, fd))
            except OSError:
                continue
            rows.append("%s -> %s" % (fd, tgt))
            if tgt.startswith(INPUT_DIR + "/"):
                inputs.append(tgt)
    except OSError as e:
        bundle.put("compositor-fds.txt", "cannot read %s: %s\n" % (fddir, e))
        return Result(5, "compositor", "blocked", ev, "cannot read %s (%s)" % (fddir, e))
    bundle.put("compositor-fds.txt", "pid=%d (%s)\n%s\n\ninput fds: %s\n"
               % (pid, how, "\n".join(rows), ", ".join(inputs) or "(none)"))
    if inputs:
        return Result(5, "compositor", "ok", ev,
                      "phoc pid=%d holds %d input node(s): %s" % (pid, len(inputs), ", ".join(inputs)))
    return Result(5, "compositor", "drop", ev,
                  "phoc pid=%d holds NO %s node (input never reached the compositor)" % (pid, INPUT_DIR))


def classify_wayland(bundle, window, exercised):
    jr = ""
    rc, out = run_cmd(["journalctl", "-u", COMPOSITOR_UNIT, "--since", "-%ds" % window, "--no-pager"], timeout=8)
    if rc == 0:
        jr = out
    bridge = read_text(BRIDGE_STATE, 65536)
    launcher = read_text(LAUNCHER_STATE, 262144)
    env = ""
    rc2, env = run_cmd(["systemctl", "show", "-p", "Environment", COMPOSITOR_UNIT], timeout=4)
    wl_touch = len(re.findall(r"wl_touch", jr))
    seat = len(re.findall(r"seat|focus|keyboard_enter|pointer_enter", jr, re.I))
    text = ("# journal: %s (last %ds)\n# WAYLAND_DEBUG in the compositor environment: %s\n%s\n\n"
            "# %s\n%s\n\n# %s (NUXEL_INPUT lines only)\n%s\n"
            % (COMPOSITOR_UNIT, window,
               "enabled" if "WAYLAND_DEBUG" in env else "NOT enabled",
               jr[-40000:] if jr else "(no journal output; journalctl rc=%d)" % rc,
               BRIDGE_STATE, bridge[-8000:], LAUNCHER_STATE,
               "\n".join(l for l in launcher.splitlines() if "NUXEL_INPUT" in l)[-12000:]))
    bundle.put("wayland-seat.txt", text)
    ev = bundle.ev("wayland-seat.txt")
    if wl_touch:
        return Result(6, "wayland", "ok", ev,
                      "wl_touch activity in the compositor journal (%d lines) => the compositor generated "
                      "Wayland touch events" % wl_touch)
    if not bridge and not launcher and rc != 0:
        return Result(6, "wayland", "blocked", ev,
                      "no compositor journal and no launcher/bridge state: seat state cannot be evaluated")
    if exercised:
        return Result(6, "wayland", "drop", ev,
                      "compositor state present but no wl_touch in the journal window while raw events "
                      "were seen below it (%d seat/focus lines)" % seat)
    return Result(6, "wayland", "blocked", ev,
                  "no wl_touch in the window (%d seat/focus lines): the layer was not exercised. "
                  "Enable WAYLAND_DEBUG=1 on %s (systemctl set-environment + restart) for a protocol-level "
                  "capture; the seat/focus state is in %s" % (seat, COMPOSITOR_UNIT, LAUNCHER_STATE))


def dom_events(bundle):
    """DOM evidence: the instrumented page's own log plus the host's NUXEL_INPUT diag."""
    probe = read_text(DOM_LOG, 262144)
    launcher = read_text(LAUNCHER_STATE, 262144)
    diag = "\n".join(l for l in launcher.splitlines() if "NUXEL_INPUT" in l)
    touch_probe = [l for l in probe.splitlines() if re.search(r"\b(start|move|end)\b", l) and "x=" in l]
    diag_touch = [l for l in diag.splitlines() if re.search(r"EVT (touchstart|touchmove|touchend)", l)]
    text = ("# %s (instrumented page, tools/s10plus/a33/touch-probe.html)\n%s\n\n"
            "# %s NUXEL_INPUT lines (host-injected DOM probe)\n%s\n" % (DOM_LOG, probe[-40000:], LAUNCHER_STATE, diag[-40000:]))
    bundle.put("dom.txt", text)
    return {"probe": touch_probe, "diag": diag_touch, "diag_any": diag.strip(),
            "evidence": bundle.ev("dom.txt"), "probe_raw": probe}


def classify_dom(dom, exercised):
    if dom["probe"]:
        return Result(7, "dom", "ok", dom["evidence"],
                      "instrumented page delivered %d DOM touch event(s); last: %s"
                      % (len(dom["probe"]), dom["probe"][-1].strip()[:200]))
    if dom["diag"]:
        return Result(7, "dom", "ok", dom["evidence"],
                      "WebKitGTK DOM received %d touch event(s) (host probe); last: %s"
                      % (len(dom["diag"]), dom["diag"][-1].strip()[:220]))
    if dom["diag_any"]:
        return Result(7, "dom", "drop" if exercised else "blocked", dom["evidence"],
                      "the DOM probe is installed (diag lines present) but no touch event reached the "
                      "document in this window%s" % (" while raw events were seen below it" if exercised else ""))
    return Result(7, "dom", "blocked", dom["evidence"],
                  "no DOM probe evidence: neither %s nor NUXEL_INPUT diag lines in %s. "
                  "Stage it with --stage-probe and open /touch-probe.html" % (DOM_LOG, LAUNCHER_STATE))


# ---------------------------------------------------------------------------
# raw event capture (the arming trick + a bounded decode loop)
# ---------------------------------------------------------------------------
def arm_node(path):
    """sec_ts on this kernel needs an open -> close -> open cycle.

    Measured A29: sec_ts_probe() leaves ts->power_status = POWER_ON, so the first
    sec_ts_input_open() takes the "already power on" short-circuit in
    sec_ts_start_device() and never re-enables the IRQ (open(2) still returns 0).
    sec_ts_input_close() runs sec_ts_stop_device() (POWER_OFF + disable_irq), so the
    SECOND open runs the real start path: wait_for_ready + reinit + SENSE_ON +
    enable_irq.  That is why the arm is open/close/open and why the reader is held
    open for the whole window.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    os.close(fd)
    time.sleep(0.05)
    return os.open(path, os.O_RDONLY | os.O_NONBLOCK)


def decode_raw(data, log=None):
    """Decode struct input_event records into a touch summary.

    struct input_event on arm64 Linux 4.14 is 24 bytes: timeval (2x8) + u16 type +
    u16 code + s32 value.  TYPE_B multitouch: ABS_MT_TRACKING_ID >= 0 = down,
    ABS_MT_TRACKING_ID < 0 = up, positions per slot, SYN_REPORT closes a frame.
    """
    stats = {"events": 0, "frames": 0, "downs": 0, "ups": 0, "points": 0,
             "btn_touch": 0, "xs": [], "ys": [], "slots": set(), "tracking_ids": set()}
    slot, x, y = 0, {}, {}
    ids = {}
    for off in range(0, len(data) - EV_SIZE + 1, EV_SIZE):
        _, _, typ, code, val = struct.unpack_from(EV_FMT, data, off)
        stats["events"] += 1
        if typ == EV_KEY and code == BTN_TOUCH:
            stats["btn_touch"] += 1
            if log is not None:
                log("BTN_TOUCH=%d" % val)
        elif typ == EV_ABS and code == ABS_MT_SLOT:
            slot = val
            stats["slots"].add(val)
        elif typ == EV_ABS and code == ABS_MT_TRACKING_ID:
            stats["tracking_ids"].add(val)
            if val >= 0:
                ids[slot] = val
                stats["downs"] += 1
                if log is not None:
                    log("TOUCH_DOWN slot=%d id=%d" % (slot, val))
            else:
                ids.pop(slot, None)
                stats["ups"] += 1
                if log is not None:
                    log("TOUCH_UP slot=%d" % slot)
        elif typ == EV_ABS and code == ABS_MT_POSITION_X:
            x[slot] = val
        elif typ == EV_ABS and code == ABS_MT_POSITION_Y:
            y[slot] = val
        elif typ == EV_SYN and code == SYN_REPORT:
            stats["frames"] += 1
            for s in list(ids):
                if s in x and s in y:
                    stats["points"] += 1
                    stats["xs"].append(x[s])
                    stats["ys"].append(y[s])
                    if log is not None:
                        log("TOUCH_POINT slot=%d raw=(%d,%d)" % (s, x[s], y[s]))
    return stats


def capture_raw(bundle, nodes, seconds, max_events, max_bytes):
    """Bounded raw capture from the capability-selected node(s)."""
    ev_log = []
    t0 = time.time()
    def log(msg):
        ev_log.append("%s %s" % (time.strftime("%H:%M:%S"), msg))

    fds = {}
    for n in nodes:
        try:
            fds[arm_node(n["path"])] = n
            log("ARMED %s name=%r (open/close/open: sec_ts_start_device short-circuit bypassed)" % (n["path"], n["name"]))
        except OSError as e:
            log("ARM_FAIL %s errno=%d (%s)" % (n["path"], e.errno, errno.errorcode.get(e.errno)))
    if not fds:
        bundle.put("touch-events.log", "\n".join(ev_log) + "\n")
        bundle.put_bytes("raw-touch.bin", b"")
        return {"armed": 0, "bytes": 0, "stats": decode_raw(b""), "log": ev_log,
                "raw": b"", "evidence": bundle.ev("touch-events.log")}

    raw = bytearray()
    stats = {"events": 0, "frames": 0, "downs": 0, "ups": 0, "points": 0,
             "btn_touch": 0, "xs": [], "ys": [], "slots": set(), "tracking_ids": set()}
    while time.time() - t0 < seconds:
        if stats["events"] >= max_events or len(raw) >= max_bytes:
            log("BOUND reached (events=%d bytes=%d)" % (stats["events"], len(raw)))
            break
        r, _, _ = select.select(list(fds), [], [], 0.25)
        for fd in r:
            try:
                data = os.read(fd, EV_SIZE * 64)
            except OSError as e:
                log("READ_ERR %s errno=%d" % (fds[fd]["path"], e.errno))
                continue
            if not data:
                continue
            raw += data
            part = decode_raw(data)
            stats["events"] += part["events"]
            stats["frames"] += part["frames"]
            stats["downs"] += part["downs"]
            stats["ups"] += part["ups"]
            stats["points"] += part["points"]
            stats["btn_touch"] += part["btn_touch"]
            stats["xs"] += part["xs"]
            stats["ys"] += part["ys"]
            stats["slots"] |= part["slots"]
            stats["tracking_ids"] |= part["tracking_ids"]
    for fd in fds:
        try:
            os.close(fd)
        except OSError:
            pass
    # a detailed per-event log, re-decoded from the bytes we actually kept
    lines = []
    decode_raw(bytes(raw), log=lambda m: lines.append("%s %s" % (time.strftime("%H:%M:%S"), m)))
    head = ("# raw touch capture: %d node(s), %d bytes, %.1fs window\n"
            "# nodes: %s\n" % (len(fds), len(raw), time.time() - t0,
                               ", ".join("%s (%s)" % (n["path"], n["name"]) for n in fds.values())))
    bundle.put_bytes("raw-touch.bin", bytes(raw))
    bundle.put("touch-events.log", head + "\n".join(ev_log + lines) + "\n")
    return {"armed": len(fds), "bytes": len(raw), "stats": stats, "log": ev_log,
            "raw": bytes(raw), "evidence": bundle.ev("touch-events.log")}


def raw_summary(stats, panel):
    xs, ys = stats["xs"], stats["ys"]
    span = ""
    if xs and ys:
        span = "x=%d..%d y=%d..%d (device range x=%s y=%s)" % (
            min(xs), max(xs), min(ys), max(ys),
            panel["x"] if panel else "?", panel["y"] if panel else "?")
    return ("events=%d frames=%d BTN_TOUCH=%d down=%d up=%d points=%d %s"
            % (stats["events"], stats["frames"], stats["btn_touch"], stats["downs"],
               stats["ups"], stats["points"], span))


# ---------------------------------------------------------------------------
# DOM instrumentation: bounded collector + probe staging
# ---------------------------------------------------------------------------
def stage_probe(bundle):
    """Copy the instrumented page into the launcher docroot (on-device only) and
    write the exact, non-automatic instructions to open it.  Never fails the run."""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "touch-probe.html")
    notes = ["# nuxel-touch-trace - DOM probe staging", "source: %s" % src]
    staged = None
    for d in ("/usr/share/nuxel/nuxel-home", "/usr/share/nuxel/pwa/nuxel-home"):
        if os.path.isdir(d):
            try:
                with open(src, "rb") as f:
                    data = f.read()
                dst = os.path.join(d, "touch-probe.html")
                with open(dst, "wb") as f:
                    f.write(data)
                notes.append("STAGED %s (%d bytes)" % (dst, len(data)))
                staged = dst
            except OSError as e:
                notes.append("STAGE_FAIL %s: %s" % (d, e))
    if staged is None:
        notes.append("NOT ON DEVICE (no launcher docroot present) - nothing staged")
    notes += [
        "To measure layer 7 (WebKitGTK DOM) with real coordinates, open the page in a",
        "WebKit view and touch it:",
        "  1. nuxelctl action open-terminal            # opens a second WebKitGTK view",
        "  2. or: systemctl restart nuxel-pwa-host     # with NUXEL_HOME_URL=%s"
        % (staged or "http://127.0.0.1:8000/touch-probe.html"),
        "  3. the host's own DOM probe already logs to /run/nuxel-home.state (NUXEL_INPUT lines)",
        "  4. the standalone page POSTs to the collector started by --live (127.0.0.1:8099)",
        "Write the verdict as NEEDS_OWNER_TEST until a human finger has done this.",
    ]
    text = "\n".join(notes) + "\n"
    bundle.put("probe-staging.txt", text)
    try:
        with open(TOUCH_PROBE_STAGED, "w") as f:
            f.write(text)
    except OSError:
        pass
    return text


class DomCollector:
    """Bounded local collector for the instrumented page (127.0.0.1 only).

    Bounded three ways: max requests, max bytes, and a hard duration.  It is a
    daemon thread; it can never keep the tracer alive, and a failure to bind the
    port downgrades layer 7 to 'blocked' instead of failing the run.
    """

    def __init__(self, bundle, port=8099, max_requests=200):
        self.bundle = bundle
        self.port = port
        self.max_requests = max_requests
        self.count = 0
        self.started = False
        self.error = ""

    def start(self, seconds):
        try:
            from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        except ImportError as e:                       # pragma: no cover
            self.error = "no http.server module: %s" % e
            return False
        probe_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "touch-probe.html")
        coll = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype="text/plain"):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path.startswith("/touch-probe.html") and os.path.isfile(probe_src):
                    with open(probe_src, "rb") as f:
                        self._send(200, f.read(), "text/html")
                elif self.path.startswith("/health"):
                    self._send(200, b"nuxel-touch-dom ok\n")
                else:
                    self._send(404, b"not found\n")

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(min(n, 4096)) if n else b""
                coll.count += 1
                line = "%s %s %s" % (time.strftime("%Y-%m-%dT%H:%M:%S"), self.path,
                                     body.decode("utf-8", "replace").replace("\n", " ")[:400])
                for target in (DOM_LOG, coll.bundle.ev("dom-http.log")):
                    try:
                        with open(target, "a") as f:
                            f.write(line + "\n")
                    except OSError:
                        pass
                self._send(204, b"")

        class Server(ThreadingHTTPServer):
            daemon_threads = True
        try:
            self.httpd = Server(("127.0.0.1", self.port), H)
        except OSError as e:
            self.error = "cannot bind 127.0.0.1:%d (%s)" % (self.port, e)
            return False
        self.started = True
        t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        t.start()
        return True

    def stop(self):
        if self.started:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        return self.count


# ---------------------------------------------------------------------------
# hard timeout: the live console must never hang
# ---------------------------------------------------------------------------
_HARD = {"on": False, "results": None, "bundle": None, "reason": "hard timeout"}


def _hard_timeout(signum, frame):                       # pragma: no cover
    if _HARD["bundle"] is not None:
        try:
            _HARD["bundle"].put("HARD-TIMEOUT.txt", "session exceeded its bound: %s\n" % _HARD["reason"])
        except Exception:
            pass
    say("HARD_TIMEOUT %s" % _HARD["reason"])
    if _HARD["results"]:
        for r in _HARD["results"]:
            r.emit()
        summarize(_HARD["results"])
    else:
        for n, nm, _d in LAYERS:
            say("LAYER=%d NAME=%s STATE=blocked EVIDENCE=(none) DETAIL=session hit its hard timeout before "
                "this layer was evaluated" % (n, nm))
        say("VERDICT=PIPELINE_UNKNOWN_HARD_TIMEOUT")
    os._exit(3)



# ---------------------------------------------------------------------------
# capability discovery: /sys/class/input/<node>/device/  (never a node number)
# ---------------------------------------------------------------------------
def _bitmap_words(hexstr):
    """Decode a kernel bitmap string into 64-bit words.

    The kernel prints the HIGHEST word first
    (drivers/input/input.c:input_print_bitmap loops `i = BITS_TO_LONGS(max)-1 ..
    0`), so word 0 of the parsed list is the HIGHEST word.  This is the same
    convention the A32 bitmap decoder and the A33 shim use, which is what makes
    one implementation testable against the other.
    """
    words = []
    for tok in re.split(r"[\s,]+", (hexstr or "").strip()):
        if not tok:
            continue
        try:
            words.append(int(tok, 16))
        except ValueError:
            return []
    return words


def _bitmap_has(words, bit):
    """True when `bit` is set in a printed bitmap (first printed word = highest)."""
    if not words or bit is None or bit < 0:
        return False
    printed = len(words) - 1 - (bit // 64)
    if printed < 0 or printed >= len(words):
        return False
    return bool((words[printed] >> (bit % 64)) & 1)


def _parse_mode(text):
    m = re.search(r"(\d+)\s*[x,]\s*(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def sysfs_inputs(bundle):
    """Capability inspection of /sys/class/input/*/device (briq-01a).

    Reads the kernel's own device metadata: name, id/bustype+vendor+product, the
    capability bitmaps (properties, capabilities/abs, capabilities/key) and the
    per-axis absinfo when the kernel exposes it.  A node NUMBER is parsed from the
    directory entry at runtime and is never assumed.  Nothing here decides the
    selection on its own: it is reported next to the ioctl result so the two
    independent identities can be compared.
    """
    root = SYSFS_INPUT_ROOT
    rows = []
    try:
        entries = sorted((e for e in os.listdir(root) if e.startswith(NODE_PREFIX)),
                         key=lambda e: int(re.sub(r"\D", "", e) or 0))
    except OSError as e:
        bundle.put("sysfs-input.txt", "# capability scan of %s\ncannot list: %s\n" % (root, e))
        return {"root": root, "rows": [], "selected": None, "error": str(e),
                "evidence": bundle.ev("sysfs-input.txt")}
    lines = ["# capability scan of %s/ (selection by capability, never by number)" % root]
    selected = None
    for e in entries:
        dev = os.path.join(root, e, "device")
        name = read_text(os.path.join(dev, "name")).strip().strip('"')
        props = _bitmap_words((read_text(os.path.join(dev, "properties")).strip().splitlines() or [""])[0])
        absb = _bitmap_words((read_text(os.path.join(dev, "capabilities", "abs")).strip().splitlines() or [""])[0])
        keyb = _bitmap_words((read_text(os.path.join(dev, "capabilities", "key")).strip().splitlines() or [""])[0])
        row = {
            "entry": e, "path": os.path.join(INPUT_DIR, e), "name": name,
            "bustype": read_text(os.path.join(dev, "id", "bustype")).strip(),
            "vendor": read_text(os.path.join(dev, "id", "vendor")).strip(),
            "product": read_text(os.path.join(dev, "id", "product")).strip(),
            "properties_raw": (read_text(os.path.join(dev, "properties")).strip().splitlines() or [""])[0],
            "direct": _bitmap_has(props, INPUT_PROP_DIRECT_BIT),
            "abs_raw": (read_text(os.path.join(dev, "capabilities", "abs")).strip().splitlines() or [""])[0],
            "mt": (_bitmap_has(absb, ABS_MT_POSITION_X) and _bitmap_has(absb, ABS_MT_POSITION_Y)),
            "tracking_id": _bitmap_has(absb, ABS_MT_TRACKING_ID),
            "btn_touch": _bitmap_has(keyb, BTN_TOUCH),
            "absinfo": {},
        }
        for line in read_text(os.path.join(dev, "absinfo")).splitlines():
            f = line.split()
            if len(f) >= 3 and f[0] in ("ABS_MT_POSITION_X", "ABS_MT_POSITION_Y",
                                        "ABS_X", "ABS_Y", "ABS_MT_SLOT"):
                try:
                    row["absinfo"][f[0]] = [int(f[1]), int(f[2])]
                except ValueError:
                    pass
        rows.append(row)
        lines.append("%-12s name=%-22r bustype=%s vendor=%s product=%s direct=%d mt=%d "
                     "tracking_id=%d btn_touch=%d properties=%s abs=%s absinfo=%s"
                     % (e, row["name"], row["bustype"] or "?", row["vendor"] or "?", row["product"] or "?",
                        row["direct"], row["mt"], row["tracking_id"], row["btn_touch"],
                        row["properties_raw"] or "(unreadable)", row["abs_raw"] or "(unreadable)",
                        row["absinfo"] or "(none)"))
    cand = [r for r in rows if r["mt"] and r["direct"]]
    if not cand:
        cand = [r for r in rows if SEC_TS_NAME in r["name"]]
    if cand:
        selected = cand[0]
        lines.append("")
        lines.append("SELECTED %s name=%r by %s"
                     % (selected["path"], selected["name"],
                        "capability (ABS_MT + direct marker)" if (selected["mt"] and selected["direct"])
                        else "name fallback (capability not proven: direct=%d mt=%d)"
                             % (selected["direct"], selected["mt"])))
    else:
        lines.append("")
        lines.append("SELECTED (none): no node proves a direct multitouch surface in %s/" % root)
    bundle.put("sysfs-input.txt", "\n".join(lines) + "\n")
    return {"root": root, "rows": rows, "selected": selected,
            "evidence": bundle.ev("sysfs-input.txt")}


# ---------------------------------------------------------------------------
# panel geometry + coordinate validation (1440x3040 DECON)
# ---------------------------------------------------------------------------
def panel_geometry(bundle):
    """Panel size, framebuffer page geometry and the output the bridge feeds.

    Read, never assumed: fb0 is the DECON framebuffer, `modes` carries the panel
    mode (`U:1440x3040p-0`) and `virtual_size` carries the allocated surface
    (`1440,6080` = TWO panel pages, because the animation and the Wayland bridge
    flip between them).  PANEL_FALLBACK is only for a host with no framebuffer.
    """
    modes = read_text(os.path.join(SYSFS_FB, "modes"))
    virtual = read_text(os.path.join(SYSFS_FB, "virtual_size"))
    name = read_text(os.path.join(SYSFS_FB, "name")).strip()
    bpp = read_text(os.path.join(SYSFS_FB, "bits_per_pixel")).strip()
    panel = _parse_mode(modes) or _parse_mode(virtual) or PANEL_FALLBACK
    vpage = _parse_mode(virtual) or panel
    pages = int(round(vpage[1] / panel[1])) if panel[1] else 1
    out = detect_output()
    geo = {
        "panel": panel,
        "panel_source": ("%s/modes" % SYSFS_FB) if _parse_mode(modes) else "PANEL_FALLBACK (no readable mode)",
        "framebuffer_name": name or "(unreadable)",
        "bits_per_pixel": bpp or "(unreadable)",
        "virtual_size": vpage,
        "pages": max(1, pages),
        "output": out,
    }
    bundle.put("panel-geometry.txt",
               "# framebuffer + Wayland output geometry\n"
               "fb_name=%s bpp=%s modes=%s virtual_size=%s\npanel=%dx%d (from %s) pages=%d\n"
               "output=%s\n"
               % (geo["framebuffer_name"], geo["bits_per_pixel"], modes.strip() or "(unreadable)",
                  virtual.strip() or "(unreadable)", panel[0], panel[1], geo["panel_source"],
                  geo["pages"], json.dumps(out, sort_keys=True)))
    return geo


def detect_output():
    """The Wayland output behind the framebuffer bridge.

    Read from the bridge/launcher state; the A32 measurement is a headless output
    at HALF the panel resolution with scale 2, so a scale-mismatched coordinate
    mapping must show up as a number.  Nothing is hard-coded as a fact: an
    unreadable state yields scale 1 and an explicit `source` saying so.
    """
    bridge = read_text(BRIDGE_STATE, 65536)
    launcher = read_text(LAUNCHER_STATE, 131072)
    txt = bridge + "\n" + launcher
    scale, name, geo, tf = 1, None, None, "normal"
    m = re.search(r"scale[\s=:]+(\d+)", txt)
    if m:
        scale = max(1, int(m.group(1)))
    m = re.search(r"\b(HEADLESS[-\w]*)\b", txt)
    if m:
        name = m.group(1)
    m = re.search(r"\b(\d{3,4})x(\d{3,4})\b", txt)
    if m:
        geo = [int(m.group(1)), int(m.group(2))]
    m = re.search(r"transform[\s=:]+([A-Za-z0-9_]+)", txt)
    if m:
        tf = m.group(1)
    return {"name": name, "scale": scale, "geometry": geo, "transform": tf,
            "source": ("%s + %s" % (BRIDGE_STATE, LAUNCHER_STATE)) if txt.strip()
                      else "(no bridge/launcher state readable: scale defaults to 1)"}


def coord_map(scan, geo, sysfs=None):
    """raw ABS_MT device range -> panel pixels -> compositor output pixels.

    The range comes from EVIOCGABS when the node is openable (the authority) and
    falls back to the sysfs absinfo tree, which is what makes the validation
    testable offline with the checked-in fixtures.  The source is recorded, so a
    fallback range is never mistaken for a measured one.
    """
    dev = scan.get("panel") or (scan.get("touch") or [None])[0] or {}
    pw, ph = geo["panel"]
    rx = list(dev.get("x") or [])
    ry = list(dev.get("y") or [])
    range_source = "ioctl EVIOCGABS on %s" % (dev.get("path") or "?") if (rx and ry) else None
    if (not rx or not ry) and sysfs and sysfs.get("selected"):
        ai = sysfs["selected"].get("absinfo") or {}
        fx = ai.get("ABS_MT_POSITION_X") or ai.get("ABS_X")
        fy = ai.get("ABS_MT_POSITION_Y") or ai.get("ABS_Y")
        if fx and fy:
            rx, ry = list(fx), list(fy)
            range_source = "sysfs absinfo of %s (no openable node)" % sysfs["selected"]["entry"]
    if not rx or not ry:
        rx, ry = [0, pw - 1], [0, ph - 1]
        range_source = "PANEL_FALLBACK (no range was readable: not a measurement)"
    dev = dict(dev, x=tuple(rx), y=tuple(ry))
    out = geo["output"]
    scale = max(1, int(out.get("scale") or 1))
    m = {
        "panel": {"width": pw, "height": ph, "source": geo["panel_source"]},
        "framebuffer": {"virtual_size": geo["virtual_size"], "pages": geo["pages"],
                        "bits_per_pixel": geo["bits_per_pixel"]},
        "device": {"name": dev.get("name"), "path": dev.get("path"),
                   "range_x": rx, "range_y": ry, "range_source": range_source},
        "output": {"name": out.get("name"), "scale": scale, "transform": out.get("transform"),
                   "width": max(1, pw // scale), "height": max(1, ph // scale),
                   "geometry": out.get("geometry"), "source": out.get("source")},
        "mapping": ("identity" if (rx == [0, pw - 1] and ry == [0, ph - 1]) else "scaled"),
    }
    return m


def map_coords(m, x, y):
    """Map one raw ABS_MT point to panel pixels and to compositor output pixels."""
    dx0, dx1 = m["device"]["range_x"]
    dy0, dy1 = m["device"]["range_y"]
    pw, ph = m["panel"]["width"], m["panel"]["height"]
    sx = ((pw - 1) / (dx1 - dx0)) if dx1 > dx0 else 1.0
    sy = ((ph - 1) / (dy1 - dy0)) if dy1 > dy0 else 1.0
    px, py = (x - dx0) * sx, (y - dy0) * sy
    sc = max(1, int(m["output"].get("scale") or 1))
    return {"raw_x": x, "raw_y": y, "panel_x": round(px, 2), "panel_y": round(py, 2),
            "out_x": round(px / sc, 2), "out_y": round(py / sc, 2)}


def validate_mapping(m, xs, ys):
    """Every captured point must be inside the DEVICE's own range and inside the
    PANEL bounds.  A number, not an opinion - and no points is not a pass."""
    dx0, dx1 = m["device"]["range_x"]
    dy0, dy1 = m["device"]["range_y"]
    pw, ph = m["panel"]["width"], m["panel"]["height"]
    n = min(len(xs), len(ys))
    pts = [map_coords(m, xs[i], ys[i]) for i in range(n)]
    inside_dev = bool(n) and all(dx0 <= v <= dx1 for v in xs) and all(dy0 <= v <= dy1 for v in ys)
    inside_panel = bool(n) and all(0 <= p["panel_x"] <= pw - 1 and 0 <= p["panel_y"] <= ph - 1
                                  for p in pts)
    return {
        "points": n,
        "device_range_x": [dx0, dx1], "device_range_y": [dy0, dy1],
        "observed_x": [min(xs), max(xs)] if n else [],
        "observed_y": [min(ys), max(ys)] if ys else [],
        "inside_device_range": bool(inside_dev),
        "inside_panel_bounds": bool(inside_panel),
        "panel": {"width": pw, "height": ph},
        "verdict": ("NO_POINTS" if not n else
                    ("OK" if (inside_dev and inside_panel) else "OUT_OF_RANGE")),
    }


# ---------------------------------------------------------------------------
# JSONL per-event stream (the owner-tap capture format)
# ---------------------------------------------------------------------------
def decode_jsonl(data, m, source=""):
    """One JSON object per input_event, plus one `point` object per frame.

    struct input_event carries its OWN timeval (the kernel timestamp), which is
    the only timestamp that reflects when the controller was read rather than when
    this tool happened to be scheduled.  Both the kernel timeval (ts) and an ISO
    form are written; the `point` records add the mapped coordinates.
    """
    recs, slot, ids = [], 0, {}
    xs, ys = {}, {}
    for off in range(0, len(data) - EV_SIZE + 1, EV_SIZE):
        sec, usec, typ, code, val = struct.unpack_from(EV_FMT, data, off)
        iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(sec)) + ".%06dZ" % usec
        rec = {"ts": round(sec + usec / 1e6, 6), "iso": iso, "source": source,
               "type": typ, "code": code, "value": val, "kind": "evdev"}
        if typ == EV_KEY and code == BTN_TOUCH:
            rec.update(kind="btn_touch", button_state=val)
        elif typ == EV_ABS and code == ABS_MT_SLOT:
            slot = val
            rec.update(kind="slot", slot=val)
        elif typ == EV_ABS and code == ABS_MT_TRACKING_ID:
            if val >= 0:
                ids[slot] = val
                rec.update(kind="down", slot=slot, tracking_id=val)
            else:
                ids.pop(slot, None)
                rec.update(kind="up", slot=slot)
        elif typ == EV_ABS and code == ABS_MT_POSITION_X:
            xs[slot] = val
            rec.update(kind="axis", axis="ABS_MT_POSITION_X", slot=slot)
        elif typ == EV_ABS and code == ABS_MT_POSITION_Y:
            ys[slot] = val
            rec.update(kind="axis", axis="ABS_MT_POSITION_Y", slot=slot)
        elif typ == EV_SYN and code == SYN_REPORT:
            rec.update(kind="frame")
            for s in sorted(ids):
                if s in xs and s in ys:
                    p = {"kind": "point", "slot": s, "tracking_id": ids[s],
                         "ts": rec["ts"], "iso": iso, "source": source}
                    p.update(map_coords(m, xs[s], ys[s]))
                    recs.append(p)
        recs.append(rec)
    return recs


def write_events_jsonl(bundle, raw, m, source):
    recs = decode_jsonl(raw, m, source)
    bundle.put("events.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    pts = [r for r in recs if r.get("kind") == "point"]
    return {"path": bundle.ev("events.jsonl"), "records": len(recs),
            "frames": len([r for r in recs if r.get("kind") == "frame"]),
            "points": len(pts)}


# ---------------------------------------------------------------------------
# archive the evidence into the repository (never only on the phone)
# ---------------------------------------------------------------------------
def archive_bundle(src, dest_root, label="touch"):
    """Copy a finished bundle into <dest_root>/<label>-<ts>/ and append INDEX.jsonl.

    Creating dest_root is attempted explicitly so an unwritable target is a hard
    error with a message rather than a silent relocation.
    """
    if not os.path.isdir(src):
        raise OSError("no such bundle to archive: %s" % src)
    os.makedirs(dest_root, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S%z")
    dest = os.path.join(dest_root, "%s-%s" % (label, ts))
    if os.path.exists(dest):
        dest = dest + "-%d" % int(time.time() % 1000)
    os.makedirs(dest)
    n = 0
    for name in sorted(os.listdir(src)):
        s = os.path.join(src, name)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(dest, name))
            n += 1
    with open(os.path.join(dest_root, "INDEX.jsonl"), "a") as f:
        f.write(json.dumps({"dir": os.path.basename(dest), "files": n, "source": os.path.abspath(src),
                            "archived_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, sort_keys=True) + "\n")
    return dest, n


def emit_exit_codes(results, use_layer_codes):
    """Print one LAYER_EXIT line per layer and the process status this run means.

    The per-layer code (10 + layer) is always printed.  The process exit status
    only becomes that code with --layer-exit-codes; otherwise the historical
    0/3/4 contract is kept so nothing that already parses this tool changes.
    """
    first = next((r.n for r in results if r.state != "ok"), None)
    for r in results:
        say("LAYER_EXIT=%d NAME=%s STATE=%s EXIT=%d" % (r.n, r.name, r.state, LAYER_EXIT_CODES[r.n]))
    if first is None:
        say("EXIT_CODE=0 (ALL_LAYERS_PASS)")
        return EXIT_OK
    st = next(r.state for r in results if r.n == first)
    if use_layer_codes:
        say("EXIT_CODE=%d (first lossy layer %d %s is %s)"
            % (LAYER_EXIT_CODES[first], first, LAYER_NAMES.get(first, "?"), st))
        return LAYER_EXIT_CODES[first]
    say("EXIT_CODE=%d (gate fail; first lossy layer %d %s is %s - pass --layer-exit-codes "
        "to get %d here)" % (EXIT_GATE_FAIL, first, LAYER_NAMES.get(first, "?"), st,
                             LAYER_EXIT_CODES[first]))
    return EXIT_GATE_FAIL

# ---------------------------------------------------------------------------
# live session
# ---------------------------------------------------------------------------
def gate_json(stats, panel, dom_state):
    """The machine gate: >=1 BTN_TOUCH down/up with plausible ABS_MT coordinates
    propagated to the TOP layer (DOM)."""
    xs, ys = stats["xs"], stats["ys"]
    plausible = bool(xs and ys)
    rng_x = panel.get("x") if panel else None
    rng_y = panel.get("y") if panel else None
    if plausible and rng_x and rng_y:
        plausible = (all(rng_x[0] <= v <= rng_x[1] for v in xs) and
                     all(rng_y[0] <= v <= rng_y[1] for v in ys))
    ok = (stats["downs"] >= 1 and stats["ups"] >= 1 and stats["btn_touch"] >= 1
          and plausible and dom_state == "ok")
    return {"btn_touch_events": stats["btn_touch"], "down": stats["downs"], "up": stats["ups"],
            "points": stats["points"],
            "coords_x": [min(xs), max(xs)] if xs else [],
            "coords_y": [min(ys), max(ys)] if ys else [],
            "device_range_x": list(rng_x) if rng_x else None,
            "device_range_y": list(rng_y) if rng_y else None,
            "coords_plausible": plausible, "dom_layer_state": dom_state, "pass": bool(ok)}


def run_live(args):
    self_check_limits(args.seconds, args.max_events, args.max_bytes)
    bundle = Bundle(args.out)
    _HARD.update({"on": True, "bundle": bundle, "results": None,
                  "reason": "live session exceeded --seconds %d + %d s slack" % (args.seconds, SLACK_SECONDS)})
    signal.signal(signal.SIGALRM, _hard_timeout)
    signal.alarm(int(args.seconds) + SLACK_SECONDS)
    t0 = time.time()
    label = "--capture" if getattr(args, "capture", None) else "--live"
    say("== nuxel-touch-trace %s  budget=%ds max_events=%d max_bytes=%d dry_run=%s =="
        % (label, args.seconds, args.max_events, args.max_bytes, args.dry_run))
    bundle.meta["mode"] = "%s%s" % (label.lstrip("-"), "-dry-run" if args.dry_run else "")
    bundle.meta["budget_seconds"] = args.seconds
    bundle.meta["expect_finger"] = bool(args.expect_finger)

    boot = collect_boot(bundle)
    say("BOOT_MODE=%s (%s)" % (bundle.meta.get("boot_mode"),
                               "; ".join(boot["charger"]) or "no charger/LPM marker present"))
    before = collect_interrupts(bundle, "before")

    collector = None
    if not args.dry_run:
        stage_note = stage_probe(bundle)
        say("PROBE_STAGE=%s" % (stage_note.splitlines()[1] if len(stage_note.splitlines()) > 1 else "?"))
        collector = DomCollector(bundle, args.dom_port)
        if collector.start(args.seconds):
            say("DOM_COLLECTOR listening on 127.0.0.1:%d (bounded: 200 requests, daemon thread)" % args.dom_port)
        else:
            say("DOM_COLLECTOR unavailable (%s) - layer 7 falls back to the host DOM probe" % collector.error)
    else:
        say("DRY_RUN: no arming, no DOM collector, no writes outside the evidence bundle")

    scan = scan_input_nodes(bundle)
    say("EVDEV_SCAN nodes=%d touch_candidates=%d (%s)"
        % (len(scan["nodes"]), len(scan["touch"]),
           ", ".join("%s=%r" % (c["path"], c["name"]) for c in scan["touch"]) or "none"))

    # INDEPENDENT identity, from the kernel's own sysfs metadata.  The selection
    # above came from the evdev ioctls; this is what the kernel says the node is,
    # including the vendor/product and the capability bitmaps.
    sysfs = sysfs_inputs(bundle)
    sel = sysfs["selected"]
    say("SYSFS_INPUT root=%s entries=%d selected=%s"
        % (sysfs["root"], len(sysfs["rows"]),
           ("%s name=%r direct=%d mt=%d vendor=%s product=%s"
            % (sel["path"], sel["name"], sel["direct"], sel["mt"], sel["vendor"] or "?", sel["product"] or "?"))
           if sel else "none"))
    node = scan["panel"]
    if node:
        nident = node.get("id")
        say("NODE_ID ioctl EVIOCGID %s (the node's own answer) | sysfs id bustype=%s vendor=%s product=%s"
            "; ABS_MT_SLOT claimed=%s EVIOCGABS(ABS_MT_SLOT)=%s -> contact_slots=%s"
            % (("bustype=0x%04x vendor=0x%04x product=0x%04x version=0x%04x"
                % (nident["bustype"], nident["vendor"], nident["product"], nident["version"]))
               if nident else "unreadable",
               (sel or {}).get("bustype") or "?", (sel or {}).get("vendor") or "?",
               (sel or {}).get("product") or "?",
               node.get("slot_bit"), node.get("slot_range"), node.get("slots")))
    disagreement = None
    if sel and scan["panel"]:
        if (sel["name"] != scan["panel"]["name"]) or (bool(sel["mt"]) != bool(scan["panel"]["mt"])):
            disagreement = ("sysfs says name=%r mt=%d, the ioctl says name=%r mt=%d"
                            % (sel["name"], sel["mt"], scan["panel"]["name"], scan["panel"]["mt"]))
    if sel and scan["panel"] and bool(sel.get("direct")) != bool(scan["panel"].get("direct")):
        disagreement = (disagreement or "") + (" [direct: sysfs=%d ioctl=%d]"
                                               % (sel["direct"], scan["panel"]["direct"]))
    if disagreement:
        say("SYSFS_IOCTL_DISAGREEMENT %s (the ioctl is authoritative for selection; the raw "
            "properties value is %s)" % (disagreement.strip(), sel["properties_raw"]))

    # PANEL + coordinate mapping: read the DECON framebuffer geometry and the
    # output the bridge feeds, then map raw ABS_MT -> panel -> output.
    geo = panel_geometry(bundle)
    cmap = coord_map(scan, geo, sysfs)
    say("PANEL=%dx%d source=%s fb=%s bpp=%s virtual_size=%s pages=%d output=%s scale=%s transform=%s"
        % (geo["panel"][0], geo["panel"][1], geo["panel_source"], geo["framebuffer_name"],
           geo["bits_per_pixel"], "x".join(str(v) for v in geo["virtual_size"]), geo["pages"],
           geo["output"].get("name") or "(unknown)", geo["output"].get("scale"),
           geo["output"].get("transform")))
    say("COORD_MAP mapping=%s device_range_x=%s device_range_y=%s range_source=%s -> panel %dx%d -> output %dx%d"
        % (cmap["mapping"], cmap["device"]["range_x"], cmap["device"]["range_y"],
           cmap["device"]["range_source"], cmap["panel"]["width"], cmap["panel"]["height"],
           cmap["output"]["width"], cmap["output"]["height"]))

    raw = {"armed": 0, "bytes": 0, "stats": decode_raw(b""), "log": []}
    if not args.dry_run:
        budget = max(3.0, args.seconds - (time.time() - t0) - 2.0)
        say("CAPTURE window=%.1fs armed_nodes=%s"
            % (budget, ", ".join(n["path"] for n in scan["touch"]) or "(none - nothing to arm)"))
        raw = capture_raw(bundle, scan["touch"], budget, args.max_events, args.max_bytes)
        say("RAW %s" % raw_summary(raw["stats"], scan["panel"]))
    jsonl = write_events_jsonl(bundle, raw.get("raw", b""), cmap,
                               ", ".join("%s (%s)" % (n["path"], n["name"]) for n in scan["touch"]) or "(none)")
    say("EVENTS_JSONL=%s records=%d frames=%d points=%d"
        % (jsonl["path"], jsonl["records"], jsonl["frames"], jsonl["points"]))
    cmap["validation"] = validate_mapping(cmap, raw["stats"]["xs"], raw["stats"]["ys"])
    cmap["events_jsonl"] = {"path": jsonl["path"], "records": jsonl["records"], "points": jsonl["points"]}
    bundle.put("coordinate-map.json", json.dumps(cmap, indent=2, sort_keys=True) + "\n")
    say("COORD_VALIDATION points=%d inside_device_range=%s inside_panel_bounds=%s verdict=%s"
        % (cmap["validation"]["points"], cmap["validation"]["inside_device_range"],
           cmap["validation"]["inside_panel_bounds"], cmap["validation"]["verdict"]))
    while time.time() - t0 < 2.0:            # the IRQ window is at least 2 s, always
        time.sleep(0.05)
    after = collect_interrupts(bundle, "after")

    exercised = (raw["stats"]["points"] > 0 or raw["stats"]["btn_touch"] > 0 or bool(args.expect_finger))
    dom = dom_events(bundle)
    r1 = classify_driver(boot, bundle)
    results = [
        r1,
        classify_irq(before, after, bundle, exercised, bool(boot["charger"])),
        classify_evdev(scan, r1.state, bool(boot["charger"])),
        classify_libinput(bundle),
        classify_compositor(bundle),
        classify_wayland(bundle, window=max(5, int(time.time() - t0)), exercised=exercised),
        classify_dom(dom, exercised),
    ]
    _HARD["results"] = results
    gate = gate_json(raw["stats"], scan["panel"], results[6].state)
    bundle.put("verdict.txt", "\n".join(
        ["LAYER=%d NAME=%s STATE=%s EVIDENCE=%s DETAIL=%s" % (r.n, r.name, r.state, r.evidence, r.detail)
         for r in results] + ["GATE=%s" % ("pass" if gate["pass"] else "fail")]) + "\n")
    bundle.put("gate.json", json.dumps(gate, indent=2) + "\n")
    if collector is not None:
        say("DOM_COLLECTOR requests=%d" % collector.stop())
    bundle.finalize()
    for r in results:
        r.emit()
    say("RAW_SUMMARY %s" % raw_summary(raw["stats"], scan["panel"]))
    say("GATE=%s %s" % ("pass" if gate["pass"] else "fail", json.dumps(gate)))
    first = summarize(results)
    rc = emit_exit_codes(results, args.layer_exit_codes)
    say("EVIDENCE_BUNDLE=%s" % bundle.path)
    signal.alarm(0)
    if args.expect_finger and not gate["pass"]:
        say("NOTE: --expect-finger was set and the gate did not pass; write the result as "
            "NEEDS_OWNER_TEST (a human finger is the only acceptable proof) - never VERIFIED_ON_S10PLUS.")
    dest_root = args.archive_dir
    if dest_root:
        try:
            dest, n = archive_bundle(bundle.path, dest_root, "touch")
            say("ARCHIVED=%s files=%d" % (dest, n))
            say("ARCHIVE_INDEX=%s" % os.path.join(dest_root, "INDEX.jsonl"))
        except OSError as e:
            say("ARCHIVE_FAILED %s (the bundle is still at %s)" % (e, bundle.path))
            rc = max(rc, EXIT_GATE_FAIL)
    elif args.capture:
        say("ARCHIVE_HINT=python3 %s --archive %s --archive-dir docs/beta-finalization/live/evidence"
            % (os.path.basename(__file__), bundle.path))
    return rc


# ---------------------------------------------------------------------------
# offline analysis
# ---------------------------------------------------------------------------
def _is_text(path, sniff=4096):
    """Text = NUL-free.  A ram-console/last_kmsg dump is full of stray high bytes
    on this vendor kernel and is still text; a raw image or an event capture has
    NULs and is not."""
    try:
        with open(path, "rb") as f:
            head = f.read(sniff)
    except OSError:
        return False
    return b"\0" not in head


def collect_texts(root, max_files=800, max_size=4 << 20):
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(p) > max_size:
                    continue
            except OSError:
                continue
            if not _is_text(p):
                continue
            out.append((os.path.relpath(p, root), p, read_text(p, max_size)))
            if len(out) >= max_files:
                return out
    return out


DEVICE_OUTPUT_HINTS = ("last_kmsg", "dmesg", "cmdline", "kernel", "bootreport",
                       "pstore", "console", "ramoops", "journal")
PRINTK_PREFIX = re.compile(r"(<\d>\[|^\[ *\d+\.\d+\]|kernel:|\[sec_input\]|sec_ts \d-)")

# The analyzer's OWN conclusions must never be mistaken for evidence.  A bundle that
# also carries a previous verdict would otherwise be graded against its own sentences:
# a real charger-mode capture proved it - a second `--analyze` run with `--json-out`
# inside the bundle reported LAYER=6 ok from the *sentence* "wl_touch present in the
# compositor protocol capture" that the first run had written there.  Name-based
# exclusion is backed by a STRUCTURAL check (below) so a copy under any name is still
# recognised as a conclusion, not as an observation.
OWN_OUTPUT = ("verdict.txt", "gate.json", "meta.json", "probe-staging.txt", "HARD-TIMEOUT.txt",
              "analysis.json", "layer-verdicts.txt", "trace.txt")

_OWN_VERDICT_RX = re.compile(r"^\s*LAYER=1 NAME=\w+ STATE=(ok|drop|blocked)", re.M)
_OWN_TOOL_TAG = '"tool": "nuxel-touch-trace"'


def looks_like_own_verdict(txt):
    return bool(_OWN_VERDICT_RX.search(txt)) or (_OWN_TOOL_TAG in txt)

# A line that is a *shell command listing* rather than device output.  The debug
# packs and the .scratch notes contain lists of commands to run ("grep -a
# 'accepted=1' /run/nuxel-libinput-path.state"); grading those as evidence would
# manufacture a pass, so command listings are ranked with prose and skipped.
SHELL_CMDS = ["#", "echo", "cat", "grep", "ls", "tr", "tail", "head", "systemctl", "journalctl",
              "curl", "sed", "awk", "printf", "setsid", "timeout", "chmod", "mkdir", "rm", "cp",
              "mv", "dd", "sha256sum", "python3", "python", "bash", "sh ", "while ", "for ",
              "if ", "exit", "true", "false", "mount", "umount", "modprobe", "insmod", "kill",
              "sleep ", "sync", "find", "wc ", "file", "stat", "date", "uname", "p="]
# Built WITHOUT re.X on purpose.  The previous verbose-form regex began with an
# unescaped "#", which in verbose mode starts a COMMENT: every alternative on that
# line (echo, cat, grep, ls, tr, ...) was silently dead, so a checklist line like
#   echo "..."; grep -a 'accepted=1' /run/nuxel-libinput-path.state | tail -3
# was graded as libinput evidence.  That is a fabricated observation and it is
# exactly what the evidence discipline forbids, so the pattern is now constructed
# from an explicit token list and self-tested below.
SHELL_LINE = re.compile(r"^\s*(?:%s)" % "|".join(re.escape(t) for t in SHELL_CMDS))

# The live-console harness frames every command as the command text followed by its
# own status: `===== grep -c sec_touchscreen /proc/bus/input/devices   [rc=0 frame=ab12 sha_ok=yes]`.
# That header is a COMMAND WRAPPER, and the command text inside it must not be
# graded as device output.  A real charger-mode capture proved the point: the naive
# match found `sec_touchscreen` inside that header and reported "the panel appears
# in the evidence" for a boot on which sec_ts_init returned -ENODEV.  The OUTPUT
# lines that follow a header carry no frame marker, so they stay device output.
CONSOLE_FRAME = re.compile(r"\[\s*rc=-?\d+\s+frame=[0-9a-f]+\s+sha_ok=(yes|no)\s*\]")

_SHELL_SELF_TEST = [
    (True, 'echo "=== libinput acceptance ==="; grep -a accepted=1 /run/nuxel-libinput-path.state | tail -3'),
    (True, "cat /proc/bus/input/devices"),
    (True, "# a comment line"),
    (False, "<6>[    1.654761] input: sec_touchscreen as /devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2"),
    (False, "[    1.654761] [0: kworker/u16:1: 42] input: sec_touchscreen as /devices/.../input2"),
    (False, "2026-10-16T12:00:00 PATH_ADD node=/dev/input/touch-panel accepted=1 reason=INPUT_PROP_DIRECT+ABS_MT"),
    (False, "sec_ts 4-0048: [sec_input] mode:0202 tc:0 noise:0 wet:0"),
]
for _expect, _line in _SHELL_SELF_TEST:
    _got = bool(SHELL_LINE.match(_line))
    if _got != _expect:                                # pragma: no cover
        raise SystemExit("SHELL_LINE self-test failed (%r -> %s, expected %s)" % (_line, _got, _expect))

# NOTE: a leading "[" used to be in SHELL_LINE, which silently discarded every
# dmesg line captured with its own timestamp ("[    1.654761] input: ...") and
# turned real kernel evidence into "no evidence".  Kernel-printk lines are now
# recognised explicitly (PRINTK_PREFIX) and never treated as a command listing.


def evidence_quality(rel):
    """Rank evidence: real device output beats a log excerpt beats prose.

    Quoting a dmesg line in a Markdown document must never be graded as if the
    device had produced it, so prose is ranked last and, for the strongest
    claims (the charger-mode gate, driver registration), it is not accepted at
    all unless the quoted line still carries its kernel prefix.
    """
    r = rel.lower()
    base = os.path.basename(r)
    if base.endswith((".md", ".markdown")):
        return "prose"
    if any(h in r for h in DEVICE_OUTPUT_HINTS):
        return "device"
    return "text"


class Evidence:
    """Best-effort evidence lookup inside a bundle OR an archived capture dir."""

    def __init__(self, root, files):
        self.root, self.files = root, files
        self.index = {rel: txt for rel, _p, txt in files}

    @staticmethod
    def _is_own(rel, txt):
        """The analyzer's own conclusions are not observations.  `named()` reads a
        specific evidence file by name and stays unfiltered; every PATTERN search
        goes through here, otherwise a bundle that also carries a previous verdict
        grades itself (measured: LAYER=6 reported ok from the sentence
        "wl_touch present in the compositor protocol capture" written by an earlier
        run of this very tool into the same directory)."""
        return os.path.basename(rel) in OWN_OUTPUT or looks_like_own_verdict(txt)

    def named(self, name):
        """A bundle file by name (any depth, exact basename)."""
        for rel, _p, txt in self.files:
            if os.path.basename(rel) == name:
                return rel, txt
        return None, ""

    def first(self, pattern, prefer=None):
        rx = re.compile(pattern, re.I)
        order = [f for f in self.files if not self._is_own(f[0], f[2])]
        if prefer:
            order = [f for f in order if os.path.basename(f[0]) in prefer] + \
                    [f for f in order if os.path.basename(f[0]) not in prefer]
        for rel, _p, txt in order:
            for line in txt.splitlines():
                if rx.search(line):
                    return rel, line.strip()
        return None, None

    def any(self, pattern):
        return self.first(pattern)[0] is not None

    def matches(self, pattern):
        """All matches with their evidence quality, best quality first."""
        rx = re.compile(pattern, re.I)
        out = []
        for rel, _p, txt in self.files:
            if self._is_own(rel, txt):
                continue
            for line in txt.splitlines():
                if rx.search(line):
                    q = evidence_quality(rel)
                    # A shell-command *listing* is not device output.  A line that
                    # carries its own kernel timestamp/prefix is device output even
                    # if a shell-ish token happens to appear in it.
                    if q != "prose" and (SHELL_LINE.match(line) or CONSOLE_FRAME.search(line)) \
                       and not PRINTK_PREFIX.search(line):
                        q = "command"
                    out.append((q, rel, line.strip()))
        order = {"device": 0, "text": 1, "command": 2, "prose": 3}
        out.sort(key=lambda m: order.get(m[0], 4))
        return out

    def best(self, pattern, allow_prose=False, require_printk_in_prose=True, allow_command=False):
        """The best-quality match for a pattern, or None.

        A prose match is only returned when it carries its kernel prefix (so a
        document that quotes `<6>[ 1.5] input: sec_touchscreen as ...` counts as a
        quotation of real output, while a document merely *mentioning*
        `sec_touchscreen` does not).
        """
        for q, rel, line in self.matches(pattern):
            if q == "command" and not allow_command:
                continue
            if q == "prose":
                if not allow_prose:
                    continue
                if require_printk_in_prose and not PRINTK_PREFIX.search(line):
                    continue
            return (rel, line, q)
        return None


def parse_interrupts(text):
    for line in text.splitlines()[1:]:
        head = line.split(":")[0].strip()
        if not head.isdigit():
            continue
        if re.search(r"sec_ts|sec_touchscreen|" + I2C_TOUCH_ADDR, line, re.I):
            counts = [int(x) for x in line.split(":")[1].split() if x.isdigit()]
            return {"irq": int(head), "total": sum(counts), "line": line.strip()}
    return None


def analyze(root, json_out=None, layer_codes=False):
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        say("ANALYZE_ERROR no such directory: %s" % root)
        return 4
    files = collect_texts(root)
    ev = Evidence(root, files)
    is_bundle = os.path.basename(root) and os.path.isfile(os.path.join(root, "meta.json"))
    say("== nuxel-touch-trace --analyze %s (%s, %d text file(s)) =="
        % (root, "nuxel-touch-trace bundle" if is_bundle else "archived capture / loose evidence", len(files)))

    # raw events, if a raw capture travelled with the evidence
    stats = decode_raw(b"")
    rel_raw = None
    raw_path = os.path.join(root, "raw-touch.bin")
    if os.path.isfile(raw_path):
        try:
            with open(raw_path, "rb") as f:
                stats = decode_raw(f.read(4 << 20))
            rel_raw = "raw-touch.bin"
        except OSError:
            pass
    exercised = stats["points"] > 0 or stats["btn_touch"] > 0

    # --- 1 driver ----------------------------------------------------------
    # The charger/LPM gate is the one finding that invalidates everything else, so
    # it needs the strongest evidence and it is reported with the file it came from.
    charger = []
    for why, pattern, weak in CHARGER_PATTERNS:
        for q, rel, line in ev.matches(pattern):
            if q == "prose":
                continue
            if weak and not re.search(r"androidboot\.|console=|sec_debug|root=", line):
                continue          # a bare `lpcharge=1` only counts inside a real cmdline
            charger.append("%s [%s]" % (why, rel))
            break
    reg = ev.best(r"input:\s*sec_touchscreen\s+as\s+\S+")
    reg_rel, reg_line = (reg[0], reg[1]) if reg else (None, None)
    nodrv = ev.best(r"sec_ts_init:\s*Do not load driver due to")
    lpm_nodrv_rel = nodrv[0] if nodrv else None
    sec = ev.best(r"\[sec_input\]|sec_ts 4-0048|sec_ts_init")
    sec_ts_rel, sec_ts_line = (sec[0], sec[1]) if sec else (None, None)
    if charger:
        r1 = Result(1, "driver", "blocked", ev.root,
                    "charger/LPM boot evidence: %s" % "; ".join(charger))
    elif reg_rel:
        r1 = Result(1, "driver", "ok", reg_rel, "stage-2/3 evidence: %s" % reg_line)
    elif lpm_nodrv_rel:
        r1 = Result(1, "driver", "blocked", lpm_nodrv_rel,
                    "sec_ts_init refused to load (LPM gate) - charger-mode boot")
    elif sec_ts_rel:
        r1 = Result(1, "driver", "drop", sec_ts_rel,
                    "sec_ts messages present but no input-device registration: %s" % sec_ts_line)
    else:
        r1 = Result(1, "driver", "blocked", ev.root,
                    "no sec_ts evidence found in %d text file(s)" % len(files))

    # --- 2 irq ------------------------------------------------------------
    _bn, before_txt = ev.named("interrupts-before.txt")
    _an, after_txt = ev.named("interrupts-after.txt")
    b_snap, a_snap = parse_interrupts(before_txt), parse_interrupts(after_txt)
    if b_snap and a_snap:
        delta = a_snap["total"] - b_snap["total"]
        if delta > 0:
            r2 = Result(2, "irq", "ok", "interrupts-before.txt / interrupts-after.txt",
                        "irq %d delivered %d event(s) across the window" % (a_snap["irq"], delta))
        elif exercised:
            r2 = Result(2, "irq", "drop", "interrupts-before.txt / interrupts-after.txt",
                        "irq %d present, delta 0 while raw events were captured below it" % a_snap["irq"])
        else:
            r2 = Result(2, "irq", "blocked", "interrupts-before.txt / interrupts-after.txt",
                        "irq %d present, delta 0, no raw events in the window (not exercised)" % a_snap["irq"])
    elif b_snap or a_snap:
        r2 = Result(2, "irq", "blocked", "interrupts-%s.txt" % ("before" if b_snap else "after"),
                    "only one interrupts snapshot available: a delta cannot be computed")
    else:
        irq_rel, irq_line = ev.first(r"sec_ts.*\d+:\s|irq/\d+-sec_ts|request_irq")
        if irq_line:
            r2 = Result(2, "irq", "blocked", irq_rel,
                        "sec_ts IRQ exists in the log but no /proc/interrupts delta capture: %s" % irq_line)
        else:
            r2 = Result(2, "irq", "blocked", ev.root, "no interrupts evidence in this capture")

    # --- 3 evdev ----------------------------------------------------------
    _n, dev_txt = ev.named("evdev.txt")
    panel_ev = ev.best(r"sec_touchscreen")
    has_panel = panel_ev is not None
    cap_line = ev.best(r"direct=1 mt=1|mt=1 .*direct=1|direct=0 mt=")
    prop_txt = dev_txt or "\n".join(t for _r, _p, t in files)
    direct_prop = re.search(r"B:\s*PROP=([0-9a-fA-F]+)", prop_txt) or re.search(r"\bPROP=([0-9a-fA-F]+)", prop_txt)
    if stats["points"] > 0 or stats["btn_touch"] > 0:
        r3 = Result(3, "evdev", "ok", rel_raw or ev.root,
                    "raw capture decoded %d point(s) / %d BTN_TOUCH event(s) from the capability-selected node"
                    % (stats["points"], stats["btn_touch"]))
    elif cap_line and "direct=1" in cap_line[1] and "mt=1" in cap_line[1]:
        r3 = Result(3, "evdev", "ok", cap_line[0],
                    "capability scan selected a DIRECT multitouch node: %s" % cap_line[1][:200])
    elif has_panel and direct_prop and (int(direct_prop.group(1), 16) & (1 << INPUT_PROP_DIRECT)):
        r3 = Result(3, "evdev", "ok", dev_txt and "evdev.txt" or ev.root,
                    "sec_touchscreen present with PROP=%s (INPUT_PROP_DIRECT) - node production proven"
                    % direct_prop.group(1))
    elif has_panel and direct_prop:
        r3 = Result(3, "evdev", "drop", ev.root,
                    "sec_touchscreen present but PROP=%s lacks INPUT_PROP_DIRECT" % direct_prop.group(1))
    elif has_panel and reg_rel:
        r3 = Result(3, "evdev", "ok", reg_rel,
                    "node production proven by the kernel's own registration line (%s); the PROP bitmap "
                    "itself needs a live EVIOCGPROP read to re-confirm INPUT_PROP_DIRECT" % reg_line)
    elif has_panel:
        r3 = Result(3, "evdev", "blocked", ev.root,
                    "sec_touchscreen appears in the evidence without a decodable PROP bitmap")
    elif r1.state == "ok":
        r3 = Result(3, "evdev", "drop", ev.root,
                    "driver layer is ok in this evidence but no sec_touchscreen node was produced")
    else:
        r3 = Result(3, "evdev", "blocked", ev.root, "no evdev evidence in this capture")

    # --- 4 libinput -------------------------------------------------------
    _ln, li_txt = ev.named("libinput-path.state")
    # Quality-graded fallback: a *shell command listing* that merely mentions
    # 'accepted=1' (e.g. the verify-touch.txt checklist) must never be graded as
    # libinput having accepted a device.  Only real state-file output counts.
    li_hit = ev.best(r"accepted=1") or ev.best(r"accepted=0|PATH_ASSIGN_SEAT|PATH_ADD")
    li_rel, li_line = (li_hit[0], li_hit[1]) if li_hit else (None, None)
    if not li_txt and li_line:
        li_txt, li_rel = li_line, li_rel
    acc = re.search(r"accepted=1", li_txt)
    # A candidate the shim actually REJECTED (it had something and turned it down)
    rej = re.search(r"accepted=0", li_txt)
    # The shim ran but had NOTHING to decide about: ZERO_DEVICES / direct_devices_seen=0
    # / added=0 without a PATH_ADD line.  That is a blocked layer, not a drop - the
    # compositor's discovery step never received a device to accept.  (Found by
    # grading a real charger-mode capture: the old code crashed on
    # `added=0` with no `accepted=0` line because it assumed the two always co-occur.)
    empty_scan = re.search(r"direct_devices_seen=0|added=0|ZERO_DEVICES", li_txt) and not re.search(r"PATH_ADD\b", li_txt)

    def _line(rx):
        m = re.search(rx, li_txt)
        return m.group(0)[:200] if m else (li_txt.strip().splitlines() or [""])[-1][:200]
    if acc:
        r4 = Result(4, "libinput", "ok", li_rel or ev.root,
                    "shim accepted the panel: %s" % _line(r"[^\n]*accepted=1[^\n]*"))
    elif rej:
        r4 = Result(4, "libinput", "drop", li_rel or ev.root,
                    "shim ran and rejected a candidate: %s" % _line(r"[^\n]*accepted=0[^\n]*"))
    elif empty_scan:
        r4 = Result(4, "libinput", "blocked", li_rel or ev.root,
                    "the shim ran but the capability scan found NO direct touch device "
                    "(nothing for libinput to accept): %s" % _line(r"[^\n]*(direct_devices_seen|added|ZERO_DEVICES)[^\n]*"))
    elif li_txt.strip():
        r4 = Result(4, "libinput", "blocked", li_rel or ev.root,
                    "libinput-path.state is present but records neither an acceptance nor a "
                    "rejection: %s" % _line(r"[^\n]+"))
    else:
        r4 = Result(4, "libinput", "blocked", ev.root, "no libinput-path.state evidence in this capture")

    # --- 5 compositor -----------------------------------------------------
    _cn, fds_txt = ev.named("compositor-fds.txt")
    m = re.search(r"input fds:\s*(.*)", fds_txt)
    cf_rel, cf_line = ev.first(r"/dev/input/event")
    if fds_txt and m:
        if m.group(1).strip() and m.group(1).strip() != "(none)":
            r5 = Result(5, "compositor", "ok", "compositor-fds.txt",
                        "phoc holds input fds: %s" % m.group(1).strip()[:200])
        else:
            r5 = Result(5, "compositor", "drop", "compositor-fds.txt",
                        "phoc holds NO input node (the compositor never opened the panel)")
    elif fds_txt and "no compositor process" in fds_txt:
        r5 = Result(5, "compositor", "blocked", "compositor-fds.txt",
                    "no compositor process at capture time: the layer cannot be evaluated")
    elif cf_line:
        r5 = Result(5, "compositor", "blocked", cf_rel,
                    "input node references exist in the evidence but no /proc/<pid>/fd capture: %s" % cf_line)
    else:
        r5 = Result(5, "compositor", "blocked", ev.root, "no compositor fd evidence in this capture")

    # --- 6 wayland --------------------------------------------------------
    _wn, wl_txt = ev.named("wayland-seat.txt")
    wl_rel, wl_line = ev.first(r"wl_touch")
    if re.search(r"wl_touch", wl_txt) or wl_line:
        r6 = Result(6, "wayland", "ok", wl_rel or "wayland-seat.txt",
                    "wl_touch present in the compositor protocol capture")
    elif re.search(r"NUXEL_INPUT EVT touch", wl_txt):
        r6 = Result(6, "wayland", "ok", "wayland-seat.txt",
                    "touch events reached the launcher document (which requires a Wayland touch client event)")
    elif exercised:
        r6 = Result(6, "wayland", "drop", ev.root,
                    "raw events exist in this evidence but no wl_touch / DOM propagation was captured")
    else:
        r6 = Result(6, "wayland", "blocked", ev.root,
                    "no seat/focus/wl_touch evidence in this capture (WAYLAND_DEBUG was not enabled?)")

    # --- 7 dom ------------------------------------------------------------
    _dn, dom_txt = ev.named("dom.txt")
    probe_hit = re.search(r"\b(touchstart|touchmove|touchend)\b.*\bx=\d+", dom_txt or "")
    diag_hit = re.search(r"NUXEL_INPUT EVT (touchstart|touchmove|touchend)", "\n".join(t for _r, _p, t in files))
    diag_any = re.search(r"NUXEL_INPUT", "\n".join(t for _r, _p, t in files))
    if probe_hit or diag_hit:
        r7 = Result(7, "dom", "ok", "dom.txt" if probe_hit else ev.root,
                    "DOM touch events with coordinates observed: %s"
                    % ((probe_hit or diag_hit).group(0)))
    elif diag_any:
        r7 = Result(7, "dom", "drop" if exercised else "blocked", ev.root,
                    "the DOM probe is installed but no touch event reached the document%s"
                    % (" while raw events exist below it" if exercised else " in this window"))
    else:
        r7 = Result(7, "dom", "blocked", ev.root,
                    "no DOM evidence in this capture (the instrumented page never ran)")

    results = [r1, r2, r3, r4, r5, r6, r7]
    for r in results:
        r.emit()
    panel = {"x": None, "y": None}
    gate = gate_json(stats, panel, r7.state)
    if rel_raw:
        say("RAW_SUMMARY %s" % raw_summary(stats, None))
    say("GATE=%s %s" % ("pass" if gate["pass"] else "fail", json.dumps(gate)))
    first = summarize(results)
    if json_out:
        with open(json_out, "w") as f:
            json.dump({"root": root, "layers": [r.__dict__ for r in results],
                       "first_fail_layer": first, "gate": gate,
                       "raw": {k: (sorted(v) if isinstance(v, set) else v) for k, v in stats.items()}},
                      f, indent=2, default=str)
        say("JSON_OUT=%s" % json_out)
    rc = emit_exit_codes(results, layer_codes)
    say("NOTE: an archived capture is graded against the same rules as a live bundle. A layer with no "
        "capture is reported 'blocked' (not ok) on purpose, so absence of evidence is never a pass.")
    return rc


def run_stage_probe(args):
    """Stage the instrumented DOM page and print the one manual step that is left.

    Layer 7 is the only layer a script cannot exercise by itself: someone has to
    open the page in a WebKit view and put a finger on the glass.  This mode does
    the half that a script CAN do (copy the page into the launcher docroot, write
    the staging receipt) and prints the other half verbatim.  It never arms a
    node, never reboots and never touches the panel.
    """
    bundle = Bundle(args.out)
    bundle.meta["mode"] = "stage-probe"
    say("== nuxel-touch-trace --stage-probe ==")
    note = stage_probe(bundle)
    for line in note.splitlines():
        say("  " + line)
    bundle.finalize()
    say("STAGE_RECEIPT=%s" % TOUCH_PROBE_STAGED)
    say("NOTE: staging the probe is NOT a touch verification.  Until a human finger has "
        "produced a DOM touch event the verdict for layer 7 is NEEDS_OWNER_TEST.")
    say("EVIDENCE_BUNDLE=%s" % bundle.path)
    return 0


# ---------------------------------------------------------------------------
# host self-test (briq-01a evidence line: python3 ... --self-test)
# ---------------------------------------------------------------------------
def self_test():
    """Assert the tool's own logic, with no phone, no libinput, no /dev/input, no root.

    Every assertion here is about a decision this tool makes.  A wrong ioctl
    number reads the wrong struct silently, a wrong bitmap order selects the wrong
    device silently, and a wrong coordinate scale puts the touch in the wrong place
    silently - so those are exactly the three things asserted.
    """
    checks = []

    def ck(cond, what, detail=""):
        checks.append(bool(cond))
        say("%s %s%s" % ("PASS" if cond else "FAIL", what, (" :: " + str(detail)) if (detail and not cond) else ""))

    # 1. kernel ABI: the ioctl request numbers this tool issues, computed by the
    #    same formula the kernel's _IOC() uses, checked against the numeric value.
    ck(EVIOCGNAME == 0x80404506, "EVIOCGNAME(64) == 0x80404506 (arm64 _IOC tuple)", hex(EVIOCGNAME))
    ck(EVIOCGBIT(EV_ABS, 8) == 0x80084523, "EVIOCGBIT(EV_ABS,8) == 0x80084523", hex(EVIOCGBIT(EV_ABS, 8)))
    ck(EVIOCGABS(ABS_MT_POSITION_X) == 0x80184575,
       "EVIOCGABS(ABS_MT_POSITION_X) == 0x80184575", hex(EVIOCGABS(ABS_MT_POSITION_X)))
    ck(EVIOCGPROP(8) == 0x80084509, "EVIOCGPROP(8) == 0x80084509", hex(EVIOCGPROP(8)))
    ck(EVIOCGID == 0x80084502, "EVIOCGID == 0x80084502 (struct input_id = 4 x u16, 8 bytes)",
       hex(EVIOCGID))
    ck(EVIOCGABS(ABS_MT_SLOT) == 0x8018456f,
       "EVIOCGABS(ABS_MT_SLOT) == 0x8018456f (contact-slot capacity read from the node)",
       hex(EVIOCGABS(ABS_MT_SLOT)))
    ck(struct.unpack("<4H", struct.pack("4H", 0x18, 0x04e5, 0x0001, 0x0000)) == (0x18, 0x04e5, 0x0001, 0),
       "EVIOCGID payload decodes as 4 x u16 (bustype/vendor/product/version)")
    ck(EV_SIZE == 24, "struct input_event is 24 bytes (arm64 Linux 4.14)", EV_SIZE)
    ck((EV_KEY, EV_ABS, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID, BTN_TOUCH)
       == (1, 3, 53, 54, 57, 330), "evdev codes match the kernel ABI")

    # 2. the event decoder: one down, one up, one point from a known byte stream
    stream = b"".join([
        struct.pack(EV_FMT, 0, 0, EV_ABS, ABS_MT_SLOT, 0),
        struct.pack(EV_FMT, 0, 0, EV_ABS, ABS_MT_TRACKING_ID, 5),
        struct.pack(EV_FMT, 0, 0, EV_ABS, ABS_MT_POSITION_X, 700),
        struct.pack(EV_FMT, 0, 0, EV_ABS, ABS_MT_POSITION_Y, 1500),
        struct.pack(EV_FMT, 0, 0, EV_KEY, BTN_TOUCH, 1),
        struct.pack(EV_FMT, 0, 0, EV_SYN, SYN_REPORT, 0),
        struct.pack(EV_FMT, 0, 0, EV_ABS, ABS_MT_TRACKING_ID, -1),
        struct.pack(EV_FMT, 0, 0, EV_KEY, BTN_TOUCH, 0),
        struct.pack(EV_FMT, 0, 0, EV_SYN, SYN_REPORT, 0),
    ])
    st = decode_raw(stream)
    ck(st["downs"] == 1 and st["ups"] == 1 and st["points"] == 1 and st["btn_touch"] == 2 and st["frames"] == 2,
       "decode_raw: 1 down, 1 up, 1 point, 2 BTN_TOUCH, 2 frames",
       "downs=%d ups=%d points=%d btn=%d frames=%d"
       % (st["downs"], st["ups"], st["points"], st["btn_touch"], st["frames"]))

    # 3. the bitmap decoder.  `4263800000000003` is the panel's OWN reported ABS
    #    bitmap from the A32 record: ABS_X/Y (0,1) + MT_TOUCH_MAJOR/MINOR (48,49)
    #    + MT_POSITION_X/Y (53,54) + MT_TRACKING_ID (57) + MT_TOOL_PRESSURE? (62).
    abs_words = _bitmap_words("4263800000000003")
    ck(_bitmap_has(abs_words, ABS_MT_POSITION_X) and _bitmap_has(abs_words, ABS_MT_POSITION_Y)
       and _bitmap_has(abs_words, ABS_MT_TRACKING_ID) and _bitmap_has(abs_words, ABS_MT_SLOT),
       "bitmap: the panel's own 4263800000000003 carries ABS_MT_POSITION_X/Y, TRACKING_ID and SLOT")
    ck(not _bitmap_has(abs_words, 0x37),
       "bitmap: the panel's ABS bitmap does NOT claim ABS_MT_TOOL_TYPE (no over-reading)")
    KEY_LINE = "B: KEY=8000000000000000 0 0 0 0 0 0 0 0 1c000000000000 0"
    key_words = _bitmap_words(KEY_LINE.split("KEY=")[1])
    mine = [k for k in range(0, 768) if _bitmap_has(key_words, k)]
    ck(mine == [114, 115, 116, 703],
       "bitmap: the live gpio_keys line decodes to VOLUMEDOWN/VOLUMEUP/POWER/Bixby",
       str(mine))
    ck(not _bitmap_has(key_words, BTN_TOUCH),
       "bitmap: that key node does not claim BTN_TOUCH (BTN_TOUCH belongs to the panel)")
    if _DECODER is not None:
        want = sorted(_DECODER.decode(KEY_LINE))
        ck(want == mine,
           "bitmap: this decoder agrees with the A32 device-validated decoder",
           "a32=%s tracer=%s" % (want, mine))
    else:
        say("SKIP bitmap cross-check: %s is not present" % A32_BITMAP_DECODER)
    # The A32/A33 convention, stated as an assertion so a change is deliberate:
    # INPUT_PROP_DIRECT is used as a BIT INDEX and the panel's raw properties value
    # is 2, so the marker is bit 1 of the printed word.
    ck(_bitmap_has(_bitmap_words("2"), INPUT_PROP_DIRECT_BIT),
       "bitmap: the observed panel properties=2 sets the direct marker bit (A32 convention)")

    # 4. coordinate mapping against the 1440x3040 DECON panel
    g = {"panel": (1440, 3040), "panel_source": "self-test", "framebuffer_name": "self-test",
         "bits_per_pixel": "32", "virtual_size": (1440, 6080), "pages": 2,
         "output": {"name": "HEADLESS-1", "scale": 2, "geometry": [720, 1520], "transform": "normal",
                    "source": "self-test"}}
    m = coord_map({"panel": {"name": SEC_TS_NAME, "path": "/dev/input/<capability-selected>",
                             "x": [0, 1439], "y": [0, 3039]}, "touch": []}, g)
    ck(m["device"]["range_source"] and "EVIOCGABS" in m["device"]["range_source"],
       "coord_map: the range source names the ioctl when the node is openable",
       m["device"]["range_source"])
    ck(m["mapping"] == "identity", "coord_map: full-range device -> identity mapping", m["mapping"])
    p = map_coords(m, 700, 1500)
    ck(p["panel_x"] == 700 and p["panel_y"] == 1500, "coord_map: identity keeps panel pixels",
       json.dumps(p))
    ck(p["out_x"] == 350 and p["out_y"] == 750, "coord_map: scale 2 halves the output coordinates",
       json.dumps(p))
    half = coord_map({"panel": {"name": SEC_TS_NAME, "path": "x", "x": [0, 719], "y": [0, 1519]}, "touch": []}, g)
    ck(half["mapping"] == "scaled", "coord_map: half-range device is 'scaled', not 'identity'")
    q = map_coords(half, 719, 1519)
    ck(q["panel_x"] == 1439 and q["panel_y"] == 3039,
       "coord_map: half-range raw maps to the last panel pixel", json.dumps(q))
    ck(validate_mapping(m, [700], [1500])["verdict"] == "OK", "validate_mapping: in-range point is OK")
    ck(validate_mapping(m, [99999], [1500])["verdict"] == "OUT_OF_RANGE",
       "validate_mapping: an out-of-range point is OUT_OF_RANGE")
    ck(validate_mapping(m, [], [])["verdict"] == "NO_POINTS",
       "validate_mapping: no points is NO_POINTS, never OK")
    ck(validate_mapping(m, [700], [1500])["panel"] == {"width": 1440, "height": 3040},
       "validate_mapping: validates against the 1440x3040 panel")

    # 5. JSONL: per-event records with a kernel timestamp and a mapped point
    recs = decode_jsonl(stream, m, "self-test")
    pts = [r for r in recs if r.get("kind") == "point"]
    ck(len(pts) == 1 and pts[0]["raw_x"] == 700 and pts[0]["out_x"] == 350.0,
       "decode_jsonl: one point record with raw and mapped coordinates",
       json.dumps(pts[0]) if pts else "no points")
    ck(all("ts" in r and "iso" in r for r in recs), "decode_jsonl: every record carries a timestamp")
    ck(any(r.get("kind") == "btn_touch" and r.get("button_state") == 1 for r in recs),
       "decode_jsonl: the BTN_TOUCH down is recorded")

    # 6. evidence discipline: a shell command listing is not device output, while
    #    the same tokens in a state file ARE device output.
    checklist = ("echo \"=== libinput ===\"; grep -a accepted=1 /run/nuxel-libinput-path.state")
    real = "2026-10-16T12:00:00 PATH_ADD node=/dev/input/<sel> accepted=1 reason=INPUT_PROP_DIRECT+ABS_MT"
    ev_cl = Evidence("<selftest>", [("checklist.txt", None, checklist)])
    ev_rf = Evidence("<selftest>", [("libinput-path.state", None, real)])
    ck(ev_cl.best(r"accepted=1") is None,
       "evidence: a checklist line mentioning accepted=1 is NOT accepted as libinput evidence")
    ck(ev_rf.best(r"accepted=1") is not None, "evidence: real state-file output IS accepted")

    frame = ("===== grep -c sec_touchscreen /proc/bus/input/devices; echo \"secreg_rc=$?\""
             "   [rc=1 frame=1eb660d8 sha_ok=yes]")
    ev_fr = Evidence("<selftest>", [("console-probe.txt", None, frame)])
    ck(ev_fr.best(r"sec_touchscreen") is None,
       "evidence: a live-console command frame is not graded as device output")
    real_out = "[    1.638064] [sec_input] sec_ts_init: Do not load driver due to : lpm 1"
    ev_ro = Evidence("<selftest>", [("console-probe.txt", None, real_out)])
    ck(ev_ro.best(r"sec_ts_init") is not None,
       "evidence: the real kernel line in the same capture IS device output")

    own = ("LAYER=1 NAME=driver STATE=ok EVIDENCE=x DETAIL=registration line\n"
           "LAYER=6 NAME=wayland STATE=ok EVIDENCE=y DETAIL=wl_touch present in the compositor\n")
    ev_own = Evidence("<selftest>", [("capture-notes.txt", None, own)])
    ck(ev_own.best(r"wl_touch") is None,
       "evidence: a previous VERDICT is never re-graded as evidence (no self-feeding pass)")
    ck(looks_like_own_verdict(own), "evidence: a verdict file is recognised structurally, whatever it is called")

    # 7. the exit-code contract
    ck(sorted(LAYER_EXIT_CODES) == list(range(1, 8)) and len(set(LAYER_EXIT_CODES.values())) == 7,
       "exit codes: one distinct code per layer, all 7 layers covered")
    ck(all(v == LAYER_EXIT_BASE + k for k, v in LAYER_EXIT_CODES.items()),
       "exit codes: code == 10 + layer number")

    # 8. the invariant this whole area exists for: no node number in this file
    own = read_text(os.path.abspath(__file__), 1 << 20)
    bad = re.findall(r"/dev/input/" + NODE_PREFIX + r"[0-9]|\b" + NODE_PREFIX + r"[0-9]+\b", own)
    ck(not bad, "no hard-coded input node number in this tool's own source", ", ".join(bad[:5]))

    # 9. the bound is enforced, not advisory
    try:
        self_check_limits(0, 2000, 262144)
        refused = False
    except SystemExit:
        refused = True
    ck(refused, "an out-of-range budget is refused instead of running unbounded")
    try:
        self_check_limits(20, 2000, 262144)
        allowed = True
    except SystemExit:
        allowed = False
    ck(allowed, "a 20 s budget is accepted")

    # 10. the gate cannot be passed without a DOM event
    gd = gate_json({"downs": 1, "ups": 1, "btn_touch": 1, "points": 1, "xs": [700], "ys": [1500],
                    "events": 9, "frames": 2, "slots": {0}, "tracking_ids": {5}},
                   {"x": [0, 1439], "y": [0, 3039]}, "blocked")
    ck(gd["pass"] is False, "gate: down+up+coords without a DOM event does NOT pass")
    gd2 = gate_json({"downs": 1, "ups": 1, "btn_touch": 1, "points": 1, "xs": [700], "ys": [1500],
                     "events": 9, "frames": 2, "slots": {0}, "tracking_ids": {5}},
                    {"x": [0, 1439], "y": [0, 3039]}, "ok")
    ck(gd2["pass"] is True, "gate: down+up+coords at the DOM layer DOES pass")
    ck(gd2["device_range_x"] == [0, 1439] and gd2["coords_plausible"] is True,
       "gate: coordinates are validated against the device's own range")

    good = sum(1 for c in checks if c)
    say("SELF-TEST: %s (%d/%d assertions)" % ("PASS" if good == len(checks) else "FAIL", good, len(checks)))
    say("SELF-TEST NOTE: this proves the TOOL's logic on a workstation. It is not a touch "
        "verification and it never becomes VERIFIED_ON_S10PLUS.")
    return 0 if good == len(checks) else 1


def run_self_test(args):
    return self_test()


def run_archive(args):
    """Copy a finished bundle into the repository's live-evidence archive."""
    src = os.path.abspath(args.archive)
    dest_root = args.archive_dir or RUN_ROOT_ARCHIVE
    say("== nuxel-touch-trace --archive %s -> %s ==" % (src, dest_root))
    try:
        dest, n = archive_bundle(src, dest_root, "touch")
    except OSError as e:
        say("ARCHIVE_FAILED %s" % e)
        return 4
    say("ARCHIVED=%s files=%d" % (dest, n))
    say("ARCHIVE_INDEX=%s" % os.path.join(dest_root, "INDEX.jsonl"))
    say("NOTE: archiving copies evidence. It does not grade it and it does not touch the device. "
        "Grade the archived copy with --analyze %s" % dest)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="nuxel-touch-trace.py",
        description="End-to-end touch pipeline tracer for the Nuxel S10+ "
                    "(sec_ts -> IRQ -> evdev -> libinput -> phoc -> Wayland -> WebKitGTK DOM).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--live", action="store_true", help="run a bounded capture session on this device")
    g.add_argument("--analyze", metavar="DIR", help="analyse a bundle or any archived capture directory")
    g.add_argument("--stage-probe", action="store_true",
                   help="stage touch-probe.html into the launcher docroot and print the exact "
                        "manual steps to measure layer 7 (does not arm anything)")
    g.add_argument("--self-test", dest="self_test", action="store_true",
                   help="assert this tool's own logic on the HOST (no phone, no /dev/input, no root)")
    g.add_argument("--capture", type=float, metavar="SECONDS",
                   help="bounded owner-tap capture session: --live for SECONDS seconds with the "
                        "per-event JSONL stream (events.jsonl) and coordinate-map.json")
    g.add_argument("--archive", metavar="DIR",
                   help="copy a finished evidence bundle into the repository archive "
                        "(docs/beta-finalization/live/evidence/touch-<ts>/) and append INDEX.jsonl")
    ap.add_argument("--out", default="/var/lib/nuxel/touch-trace", help="evidence bundle directory (--live)")
    ap.add_argument("--seconds", type=float, default=20.0, help="wall-clock budget for --live (1..900)")
    ap.add_argument("--max-events", type=int, default=2000, help="hard cap on decoded input events")
    ap.add_argument("--max-bytes", type=int, default=262144, help="hard cap on raw bytes read")
    ap.add_argument("--expect-finger", action="store_true",
                    help="a finger will touch the glass in this window: a silent layer becomes 'drop'")
    ap.add_argument("--dry-run", action="store_true",
                    help="collect what is readable without arming or writing outside the bundle")
    ap.add_argument("--dom-port", type=int, default=8099, help="port for the bounded DOM collector")
    ap.add_argument("--json-out", metavar="FILE", help="write a machine-readable verdict JSON")
    ap.add_argument("--archive-dir", metavar="DIR",
                    help="with --live/--capture: archive the finished bundle here (default for "
                         "--archive: %s)" % RUN_ROOT_ARCHIVE)
    ap.add_argument("--layer-exit-codes", action="store_true",
                    help="exit with 10 + the first lossy layer (11..17) instead of the historical 3")
    ap.add_argument("--sysfs-root", metavar="DIR",
                    help="override /sys/class/input for the capability scan (offline tests)")
    args = ap.parse_args(argv)
    if args.sysfs_root:
        globals()["SYSFS_INPUT_ROOT"] = os.path.abspath(args.sysfs_root)
    if args.capture is not None:
        # --capture N is the bounded owner-tap window: --live for N seconds, JSONL
        # always, and a finger is expected in that window.
        args.live = True
        args.seconds = args.capture
        args.expect_finger = True
    if args.self_test:
        return run_self_test(args)
    if args.archive:
        return run_archive(args)
    if args.stage_probe:
        return run_stage_probe(args)
    if args.live:
        return run_live(args)
    return analyze(args.analyze, args.json_out, args.layer_exit_codes)


if __name__ == "__main__":
    sys.exit(main())
