#!/usr/bin/env python3
"""nuxel-touch-trace — end-to-end touch pipeline tracer for the Nuxel S10+.

THE CHAIN THIS WALKS (mission priority 0):

    1 sec_ts driver binding      dmesg sec_ts/sec_touchscreen, /sys/bus/i2c/devices/4-0048,
                                 the sec_ts_init return path, and the one boot flag that
                                 removes the driver entirely (charger/LPM mode)
    2 IRQ delivery               /proc/interrupts delta for the sec_ts line over a 2 s window
    3 evdev node production      /proc/bus/input/devices + a CAPABILITY scan
                                 (EVIOCGNAME / EVIOCGPROP / EVIOCGBIT / EVIOCGABS)
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
"""
import argparse
import errno
import fcntl
import importlib.util
import json
import os
import re
import select
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

SLACK_SECONDS = 15                             # hard alarm = --seconds + this

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

        def axis(ax):
            try:
                v = struct.unpack("6i", fcntl.ioctl(fd, EVIOCGABS(ax), b"\0" * 24))
                return (v[1], v[2])
            except OSError:
                return None
        return {"path": path, "name": name,
                "direct": bool(bit(prop, INPUT_PROP_DIRECT)),
                "mt": bool(bit(absb, ABS_MT_POSITION_X) and bit(absb, ABS_MT_POSITION_Y)),
                "btn_touch": bool(bit(keyb, BTN_TOUCH)),
                "x": axis(ABS_MT_POSITION_X), "y": axis(ABS_MT_POSITION_Y),
                "tracking_id": bool(bit(absb, ABS_MT_TRACKING_ID))}
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
        lines.append("%-16s name=%-24r direct=%d mt=%d btn_touch=%d abs_mt_x=%s abs_mt_y=%s tracking_id=%d"
                     % (e, caps["name"], caps["direct"], caps["mt"], caps["btn_touch"],
                        caps["x"], caps["y"], caps["tracking_id"]))
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
    text = ("# capability scan of %s (selection is by EVIOCGPROP/EVIOCGBIT, never by number)\n%s\n\n"
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
                      "panel %s name=%r PROP=DIRECT ABS_MT=present range x=%s y=%s (selected by capability)"
                      % (panel["path"], panel["name"], panel["x"], panel["y"]))
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
                "evidence": bundle.ev("touch-events.log")}

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
            "evidence": bundle.ev("touch-events.log")}


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
    say("== nuxel-touch-trace --live  budget=%ds max_events=%d max_bytes=%d dry_run=%s =="
        % (args.seconds, args.max_events, args.max_bytes, args.dry_run))
    bundle.meta["mode"] = "dry-run" if args.dry_run else "live"
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

    raw = {"armed": 0, "bytes": 0, "stats": decode_raw(b""), "log": []}
    if not args.dry_run:
        budget = max(3.0, args.seconds - (time.time() - t0) - 2.0)
        say("CAPTURE window=%.1fs armed_nodes=%s"
            % (budget, ", ".join(n["path"] for n in scan["touch"]) or "(none - nothing to arm)"))
        raw = capture_raw(bundle, scan["touch"], budget, args.max_events, args.max_bytes)
        say("RAW %s" % raw_summary(raw["stats"], scan["panel"]))
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
    say("EVIDENCE_BUNDLE=%s" % bundle.path)
    signal.alarm(0)
    if args.expect_finger and not gate["pass"]:
        say("NOTE: --expect-finger was set and the gate did not pass; write the result as "
            "NEEDS_OWNER_TEST (a human finger is the only acceptable proof) - never VERIFIED_ON_S10PLUS.")
    return 0 if first is None else 3


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

# The analyzer's OWN conclusions must never be mistaken for evidence.
OWN_OUTPUT = ("verdict.txt", "gate.json", "meta.json", "probe-staging.txt", "HARD-TIMEOUT.txt")

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

    def named(self, name):
        """A bundle file by name (any depth, exact basename)."""
        for rel, _p, txt in self.files:
            if os.path.basename(rel) == name:
                return rel, txt
        return None, ""

    def first(self, pattern, prefer=None):
        rx = re.compile(pattern, re.I)
        order = self.files
        if prefer:
            order = [f for f in self.files if os.path.basename(f[0]) in prefer] + \
                    [f for f in self.files if os.path.basename(f[0]) not in prefer]
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
            if os.path.basename(rel) in OWN_OUTPUT:
                continue
            for line in txt.splitlines():
                if rx.search(line):
                    q = evidence_quality(rel)
                    # A shell-command *listing* is not device output.  A line that
                    # carries its own kernel timestamp/prefix is device output even
                    # if a shell-ish token happens to appear in it.
                    if q != "prose" and SHELL_LINE.match(line) and not PRINTK_PREFIX.search(line):
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


def analyze(root, json_out=None):
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
    rej = re.search(r"accepted=0|PATH_ASSIGN_SEAT", li_txt)
    if acc:
        r4 = Result(4, "libinput", "ok", li_rel or ev.root,
                    "shim accepted the panel: %s" % (re.search(r"[^\n]*accepted=1[^\n]*", li_txt).group(0)[:200]))
    elif rej:
        r4 = Result(4, "libinput", "drop", li_rel or ev.root,
                    "shim ran and rejected every candidate: %s"
                    % (re.search(r"[^\n]*accepted=0[^\n]*", li_txt).group(0)[:200]))
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
    say("NOTE: an archived capture is graded against the same rules as a live bundle. A layer with no "
        "capture is reported 'blocked' (not ok) on purpose, so absence of evidence is never a pass.")
    return 0 if first is None else 3


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
    args = ap.parse_args(argv)
    if args.stage_probe:
        return run_stage_probe(args)
    if args.live:
        return run_live(args)
    return analyze(args.analyze, args.json_out)


if __name__ == "__main__":
    sys.exit(main())
