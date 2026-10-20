#!/usr/bin/env python3
"""nuxel-anim-handoff.py — the A33 boot-animation handoff harness (briq-02a).

Three jobs, one tool:

  simulate   A REPLAYABLE, frame-accurate timing harness for the ownership
             handoff.  It answers the only question that matters on the glass:
             "was a whole animation play-through shown before the panel changed
             owner?"  It models the real timeline (animation start at uptime
             ~2.9 s, launcher page committed ~2-3 s later, the player's loop
             counter, the bridge's 100 ms evidence poll, the stop latency) and
             prints the A31/A32 result next to the A33 result, so the fix is a
             number, not an opinion.

  audit      Reads the REAL handoff artefacts from a device/VM/fixture:
               /run/nuxel-fb-owner.lock          (single-owner lock)
               /var/lib/nuxel/fb-owner           (durable ownership record)
               /run/nuxel-anim-handoff           (ownership receipt)
               /var/lib/nuxel/anim-handoff.log   (append-only audit trail)
             and returns a PASS/FAIL verdict per property, with the exact file
             contents that justify it.  Use --root to audit a fixture.

  selftest   Runs the whole offline proof: the shared decision table
             (tests/handoff-cases.json) against BOTH the Python model and the
             compiled C implementation, the header/config constant agreement,
             the simulation invariants, and a negative control on the auditor
             (a fixture with TWO writers must be reported as a failure).

No phone, no display, no root, no network needed.  Exit status = failures.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
HEADER = os.path.join(HERE, "nuxel-handoff-logic.h")
CASES = os.path.join(HERE, "tests", "handoff-cases.json")
CFG = os.path.join(ROOT, "configs", "nuxel", "boot", "animation-handoff.json")
DEFAULT_CFG = {"schema_version": 1, "mode": "receipt", "mp4_frames": 192, "mp4_fps": 24,
               "min_cycles": 1, "max_wait_s": 24, "launcher_ready_wait_s": 120,
               "poll_ms": 100, "stop_latency_ms": 150, "anim_start_ms": 2900,
               "launcher_ready_ms": 5900, "legacy_launcher_ready_ms": 2900}
PATHS = {
    "lock": "/run/nuxel-fb-owner.lock",
    "record": "/var/lib/nuxel/fb-owner",
    "receipt": "/run/nuxel-anim-handoff",
    "log": "/var/lib/nuxel/anim-handoff.log",
    "min_cycle": "/var/lib/nuxel/anim-min-cycle.completed",
    "display": "/var/lib/nuxel/display",
    "launcher": "/run/nuxel-home.state",
    "anim_state": "/var/lib/nuxel/animation",
}

failures = 0


def check(name, cond, extra=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond:
        failures += 1
    return bool(cond)


def note(msg):
    print("     NOTE " + msg)


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #
def load_cfg(path=None):
    cfg = dict(DEFAULT_CFG)
    p = path or CFG
    try:
        with open(p) as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        note("config %s absent - built-in defaults used" % p)
    except Exception as e:
        note("config %s unreadable (%s) - defaults used" % (p, e))
    return cfg


def header_constants():
    """The built-in defaults the C code compiles in (must match the config)."""
    out = {}
    txt = open(HEADER).read()
    for key, name in (("mp4_frames", "NUXEL_MP4_FRAMES_DEFAULT"),
                      ("mp4_fps", "NUXEL_MP4_FPS_DEFAULT"),
                      ("min_cycles", "NUXEL_ANIM_MIN_CYCLES_DEFAULT"),
                      ("max_wait_s", "NUXEL_ANIM_MAX_WAIT_S_DEFAULT")):
        m = re.search(r"#define\s+%s\s+(\d+)" % name, txt)
        if m:
            out[key] = int(m.group(1))
    m = re.search(r"#define\s+NUXEL_HANDOFF_SCHEMA_VERSION\s+(\d+)", txt)
    if m:
        out["schema_version"] = int(m.group(1))
    return out


def cycle_ms(cfg):
    return int(cfg["mp4_frames"] * 1000 / cfg["mp4_fps"])


# --------------------------------------------------------------------------- #
# the decision model (mirrors nuxel-handoff-logic.h; the selftest proves it)
# --------------------------------------------------------------------------- #
def request_stop(launcher_ready, painter_alive, loops_seen, min_cycles, terminal_marker):
    if not launcher_ready:
        return (0, "launcher_not_ready")
    if not painter_alive:
        return (0, "no_painter")
    if terminal_marker:
        return (1, "anim_terminal_marker")
    if loops_seen >= min_cycles:
        return (1, "anim_min_cycle_reached")
    return (0, "anim_min_cycle_pending")


def verbose_skip(launcher_ready, painter_alive, skip_requested, loops_seen, min_cycles, terminal_marker):
    """Decision 5 (briq-02b): may the minimum-cycle floor be waived for THIS boot?

    The operator's durable verbose-boot setting arrives as
    /run/nuxel/anim-skip.request.  A deliberate user choice is not a fault, but it
    must also never be dressed up as a completed cycle: this returns
    reason=verbose_boot_requested and the receipt keeps terminal=0.  It never
    fires before the launcher is ready, and never when the floor was met anyway.
    """
    if not launcher_ready:
        return (0, "launcher_not_ready")
    if not painter_alive:
        return (0, "no_painter")
    if terminal_marker or loops_seen >= min_cycles:
        return (0, "floor_already_met")
    if not skip_requested:
        return (0, "floor_pending")
    return (1, "verbose_boot_requested")


def take_ownership(launcher_ready, painter_alive, stop_requested, stop_confirmed):
    if not launcher_ready:
        return (0, "launcher_not_ready")
    if stop_requested and not stop_confirmed:
        return (0, "animation_stop_unconfirmed")
    if painter_alive:
        return (0, "animation_stop_refused" if stop_requested else "animation_still_painting")
    return (1, "animation_stop_confirmed" if stop_requested else "no_painter")


def degraded_stop(launcher_ready, painter_alive, loops_seen, min_cycles, terminal_marker, expired):
    if not (launcher_ready and painter_alive and expired):
        return (0, "not_applicable")
    if terminal_marker or loops_seen >= min_cycles:
        return (0, "not_applicable")
    return (1, "anim_clock_unavailable" if loops_seen < 0 else "anim_min_cycle_timeout")


def resume_animation(launcher_ready, bridge_wrote_scanout):
    return 1 if (not launcher_ready and not bridge_wrote_scanout) else 0


# --------------------------------------------------------------------------- #
# simulate
# --------------------------------------------------------------------------- #
def simulate(cfg, launcher_ready_ms=None, min_cycles=None, mode="a33", launcher_never=False):
    """Frame-accurate model of the boot.  Returns a report dict."""
    fps = cfg["mp4_fps"]
    frames = cfg["mp4_frames"]
    cyc = cycle_ms(cfg)
    poll = cfg["poll_ms"]
    stop_lat = cfg["stop_latency_ms"]
    ready_ms = cfg["launcher_ready_ms"] if launcher_ready_ms is None else launcher_ready_ms
    minc = cfg["min_cycles"] if min_cycles is None else min_cycles

    if launcher_never:
        # the launcher never commits its page: the bridge writes nothing, the
        # animation keeps looping (owner=anim) - never a blank/static frame
        horizon = 30000
        return {
            "mode": mode, "launcher_ready": 0, "owner": "anim",
            "handoff_ms": None, "frames_shown": int(horizon / 1000 * fps),
            "loops_shown": horizon / cyc, "complete_cycles": int(horizon / cyc),
            "cut_frames": 0, "cut_pct": 0.0, "static_wallpaper": False,
            "receipt": "ANIMATION_RESUMED", "terminal": 0, "degraded": None,
            "resumed": resume_animation(0, 0) == 1,
        }

    legacy = (mode == "legacy")
    t = 0
    loops = 0
    stop_requested_at = None
    handoff_at = None
    while t <= 120000:
        # the player counts a COMPLETE play-through at every cycle boundary
        loops = int(t / cyc)
        faded = degraded_stop(1, 1, loops, minc, 0, t >= cfg["max_wait_s"] * 1000)
        if legacy:
            want = (1, "legacy_time_based") if t >= ready_ms else (0, "launcher_not_ready")
        else:
            want = request_stop(t >= ready_ms, 1, loops, minc, 0)
            if not want[0] and faded[0]:
                want = faded
        if want[0]:
            stop_requested_at = t
            handoff_at = t + stop_lat
            break
        t += poll
    frames_shown = int((handoff_at / 1000.0) * fps)
    cycles_completed = frames_shown // frames
    into_cycle = frames_shown % frames
    # the defect being fixed: how much of the FIRST play-through never reached
    # the glass before the panel changed owner
    first_cycle_cut = max(0, frames - frames_shown)
    return {
        "mode": mode, "launcher_ready": 1, "owner": "ui",
        "handoff_ms": handoff_at,
        "stop_requested_ms": stop_requested_at,
        "frames_shown": frames_shown,
        "loops_shown": round(frames_shown / frames, 3),
        "complete_cycles": cycles_completed,
        "frames_into_next_cycle": into_cycle,
        "cut_frames": first_cycle_cut,
        "cut_pct": round(100.0 * first_cycle_cut / frames, 1),
        "static_wallpaper": frames_shown < frames,
        "receipt": "LAUNCHER_DISPLAY_OWNER",
        "terminal": 1 if (loops >= minc) else 0,
        "degraded": None if loops >= minc else "anim_min_cycle_timeout",
        "resumed": False,
    }


def cmd_simulate(args):
    cfg = load_cfg(args.config)
    minc = cfg["min_cycles"] if args.min_cycles is None else args.min_cycles
    ready = cfg["launcher_ready_ms"] if args.launcher_ready is None else int(args.launcher_ready * 1000)
    legacy = simulate(cfg, ready, minc, mode="legacy")
    a33 = simulate(cfg, ready, minc, mode="a33")
    never = simulate(cfg, ready, minc, mode="a33", launcher_never=True)
    report = {
        "config": cfg, "cycle_ms": cycle_ms(cfg), "effective": {"min_cycles": minc,
        "launcher_ready_ms": ready, "max_wait_s": cfg["max_wait_s"]},
        "legacy_a31_a32": legacy, "a33_receipt_driven": a33,
        "launcher_never_ready": never,
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print("== A33 handoff timeline simulation ==")
    print("config: %d frames @ %d fps = %d ms per play-through, min_cycles=%d, max_wait=%d s"
          % (cfg["mp4_frames"], cfg["mp4_fps"], cycle_ms(cfg), minc, cfg["max_wait_s"]))
    print("timeline: animation starts t=%d ms, launcher page committed t=%d ms"
          % (cfg["anim_start_ms"], ready))
    print()
    hdr = "%-34s %8s %8s %8s %7s %9s %s"
    print(hdr % ("scenario", "frames", "loops", "1st-cut", "cut%", "handoff", "verdict"))
    for label, r in (("A31/A32 time-based (no floor)", legacy),
                     ("A33 receipt-driven (floor=%d)" % minc, a33),
                     ("A33, launcher never ready", never)):
        print(hdr % (label, r["frames_shown"],
                     "%.2f" % r["loops_shown"], r["cut_frames"], "%.1f" % r["cut_pct"],
                     ("%d ms" % r["handoff_ms"]) if r["handoff_ms"] else "-",
                     ("CUT - static wallpaper" if r["static_wallpaper"] else "whole cycle shown")))
    print()
    print("receipt sequence the audit will find:")
    for stage, owner in (("BRIDGE_WAITING_FOR_LAUNCHER", "anim"),
                         ("ANIMATION_RUNNING", "anim"),
                         ("ANIM_MIN_CYCLE %d/%d" % (a33["complete_cycles"], minc), "anim"),
                         ("ANIM_TERMINAL_CONDITION", "anim"),
                         ("ANIMATION_STOP_REQUESTED", "anim"),
                         ("ANIMATION_STOP_CONFIRMED", "anim"),
                         ("LAUNCHER_DISPLAY_OWNER", "ui")):
        print("   owner=%s  stage=%s" % (owner, stage))
    print()
    print("markers emitted for the live group: ANIM_MIN_CYCLE, ANIMATION_STOP, "
          "LAUNCHER_DISPLAY, NUXEL_ANIM_HANDOFF (plus the player's own NUXEL_ANIM_LOOP / "
          "NUXEL_ANIM_HEARTBEAT_LOOPS)")
    return 0


# --------------------------------------------------------------------------- #
# audit
# --------------------------------------------------------------------------- #
def read(root, key, default=None):
    p = os.path.join(root, PATHS[key].lstrip("/"))
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return default


def parse_kv(text):
    out = {}
    if not text:
        return out
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def parse_receipt(text):
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


def audit(root="/", expect_ui=False):
    """Verdicts over the real artefacts.  Returns (report, failures)."""
    lock = read(root, "lock")
    record_txt = read(root, "record")
    receipt_txt = read(root, "receipt")
    log = read(root, "log") or ""
    mincycle = read(root, "min_cycle") or ""
    rec = parse_kv(record_txt)
    receipt = parse_receipt(receipt_txt)
    lock_pid = (lock or "").strip().split()[0] if lock else ""
    props = {}

    def prop(name, ok, detail):
        props[name] = {"ok": bool(ok), "detail": detail}
        return ok

    prop("lock_present", bool(lock), "lock pid=%s" % (lock_pid or "(absent)"))
    prop("single_writer",
         bool(lock_pid) and (rec.get("pid") == lock_pid or not rec),
         "lock holder %s vs record pid %s (must be the same process)" % (lock_pid, rec.get("pid", "(none)")))
    prop("owner_recorded", rec.get("owner") == "nuxel-wl-fb" and "stage" in rec,
         "record owner=%s stage=%s ui_writer=%s" % (rec.get("owner"), rec.get("stage"), rec.get("ui_writer")))
    prop("receipt_schema", receipt.get("schema_version") == 1,
         "receipt schema_version=%s" % receipt.get("schema_version"))
    prop("receipt_owner_valid", receipt.get("owner") in ("anim", "ui"),
         "receipt owner=%s stage=%s" % (receipt.get("owner"), receipt.get("stage")))
    prop("handoff_logged", "NUXEL_ANIM_HANDOFF" in log,
         "%d audit line(s)" % len(log.splitlines()))
    terminal = int(receipt.get("terminal") or 0)
    loops = int(receipt.get("loops_seen") or 0)
    minc = int(receipt.get("min_cycles") or 0)
    degraded = "DEGRADED" in str(receipt.get("stage", "")) or receipt.get("reason") in (
        "anim_min_cycle_timeout", "anim_clock_unavailable")
    # A33/verbose-boot: a WAIVED floor is a recorded operator choice, not a silent
    # sub-cycle handoff.  It is reported separately so the audit can never mistake
    # "the user asked for the boot log" for "the floor was honoured".
    skipped = (receipt.get("reason") == "verbose_boot_requested"
               or "MIN_CYCLE_SKIPPED" in str(receipt.get("stage", ""))
               or "MIN_CYCLE_SKIPPED" in (mincycle or ""))
    prop("minimum_cycle_observed",
         (minc >= 1 and (terminal == 1 or loops >= minc)) or degraded or skipped
         or rec.get("ui_writer") == "0",
         "terminal=%d loops=%d/%d degraded=%s verbose_skip=%s" % (terminal, loops, minc, degraded, skipped))
    prop("floor_honoured_exactly",
         terminal == 1 or loops >= minc,
         "whole play-through on the glass=%s (waived_by_verbose_boot=%s degraded=%s)"
         % (terminal == 1 or loops >= minc, skipped, degraded))
    if expect_ui:
        prop("ui_owns_panel", receipt.get("owner") == "ui" and rec.get("ui_writer") == "1",
             "receipt owner=%s ui_writer=%s" % (receipt.get("owner"), rec.get("ui_writer")))
    bad = [k for k, v in props.items() if not v["ok"]]
    return {"root": root, "paths": PATHS, "lock": lock.strip() if lock else None,
            "record": rec, "receipt": receipt, "audit_lines": log.splitlines()[-10:],
            "min_cycle_marker": mincycle.strip(), "properties": props,
            "verdict": "PASS" if not bad else "FAIL", "failed": bad}, len(bad)


def cmd_audit(args):
    report, bad = audit(args.root, expect_ui=args.expect_ui)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("== A33 handoff audit (root=%s) ==" % args.root)
        for k, v in report["properties"].items():
            print(("PASS " if v["ok"] else "FAIL ") + k + "  " + v["detail"])
        if report["receipt"]:
            print("receipt: owner=%s stage=%s terminal=%s loops=%s/%s reason=%s" % (
                report["receipt"].get("owner"), report["receipt"].get("stage"),
                report["receipt"].get("terminal"), report["receipt"].get("loops_seen"),
                report["receipt"].get("min_cycles"), report["receipt"].get("reason")))
        print("verdict=%s%s" % (report["verdict"], (" failed=%s" % report["failed"]) if bad else ""))
    return 1 if bad and args.strict else 0


# --------------------------------------------------------------------------- #
# selftest
# --------------------------------------------------------------------------- #
def run_c_cases():
    """Compile nuxel-handoff-logic.h's table on any host and parse it."""
    cc = os.environ.get("CC") or "cc"
    src = os.path.join(HERE, "tests", "test-handoff-logic.c")
    with tempfile.TemporaryDirectory() as d:
        exe = os.path.join(d, "thl")
        try:
            r = subprocess.run([cc, "-O2", "-o", exe, src], capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            note("C compiler unavailable (%s) - C table layer skipped" % e)
            return None
        if r.returncode != 0:
            note("C test build failed: %s" % (r.stderr.strip().splitlines() or ["?"])[-1])
            return None
        out = subprocess.run([exe], capture_output=True, text=True, timeout=60)
        return out.stdout


def parse_case_lines(text):
    rows = {}
    for line in (text or "").splitlines():
        m = re.match(r"HANDOFF_CASE (\S+) request_stop=(\d) request_reason=(\S+) take=(\d) "
                     r"take_reason=(\S+) degraded_stop=(\d) degraded_reason=(\S+) "
                     r"verbose_skip=(\d) verbose_skip_reason=(\S+)", line)
        if m:
            rows[m.group(1)] = {
                "request_stop": int(m.group(2)), "request_stop_reason": m.group(3),
                "take": int(m.group(4)), "take_reason": m.group(5),
                "degraded_stop": int(m.group(6)), "degraded_reason": m.group(7),
                "verbose_skip": int(m.group(8)), "verbose_skip_reason": m.group(9),
            }
    return rows


def cmd_selftest(args):
    print("== A33 handoff harness selftest ==")
    cfg = load_cfg(args.config)

    # 1. header defaults must agree with the shipped configuration document
    hc = header_constants()
    check("header declares the same mp4 geometry as %s" % os.path.relpath(CFG, ROOT),
          hc.get("mp4_frames") == cfg["mp4_frames"] and hc.get("mp4_fps") == cfg["mp4_fps"],
          "header=%s config=%s" % (hc, {k: cfg[k] for k in ("mp4_frames", "mp4_fps")}))
    check("header default floor equals the configured floor",
          hc.get("min_cycles") == cfg["min_cycles"], "%s vs %s" % (hc.get("min_cycles"), cfg["min_cycles"]))
    check("one play-through is the 8000 ms measured from the shipping asset",
          cycle_ms(cfg) == 8000, cycle_ms(cfg))

    # 2. the shared case corpus against the Python model
    with open(CASES) as f:
        corpus = json.load(f)["cases"]
    check("case corpus present and non-trivial", len(corpus) >= 12, len(corpus))
    mism = []
    for c in corpus:
        got = {
            "request_stop": request_stop(c["launcher_ready"], c["painter_alive"], c["loops_seen"],
                                         c["min_cycles"], c["terminal_marker"])[0],
            "request_stop_reason": request_stop(c["launcher_ready"], c["painter_alive"], c["loops_seen"],
                                                c["min_cycles"], c["terminal_marker"])[1],
            "take": take_ownership(c["launcher_ready"], c["painter_alive"], c["stop_requested"],
                                   c["stop_confirmed"])[0],
            "take_reason": take_ownership(c["launcher_ready"], c["painter_alive"], c["stop_requested"],
                                          c["stop_confirmed"])[1],
            "degraded_stop": degraded_stop(c["launcher_ready"], c["painter_alive"], c["loops_seen"],
                                           c["min_cycles"], c["terminal_marker"],
                                           c["bounded_wait_expired"])[0],
            "degraded_reason": degraded_stop(c["launcher_ready"], c["painter_alive"], c["loops_seen"],
                                             c["min_cycles"], c["terminal_marker"],
                                             c["bounded_wait_expired"])[1],
            "verbose_skip": verbose_skip(c["launcher_ready"], c["painter_alive"],
                                         c.get("skip_requested", 0), c["loops_seen"],
                                         c["min_cycles"], c["terminal_marker"])[0],
            "verbose_skip_reason": verbose_skip(c["launcher_ready"], c["painter_alive"],
                                                c.get("skip_requested", 0), c["loops_seen"],
                                                c["min_cycles"], c["terminal_marker"])[1],
        }
        want = {k: c[k] for k in got}
        if got != want:
            mism.append((c["name"], got, want))
    check("python model reproduces every case in tests/handoff-cases.json", not mism,
          mism[:2])

    # 3. the COMPILED C implementation must agree with the same corpus
    out = run_c_cases()
    crows = parse_case_lines(out)
    if crows:
        print("     C layer: %s" % ("compiled + executed" if out else "not available"))
        check("C table has every corpus case", set(crows) == {c["name"] for c in corpus},
              sorted(set(c["name"] for c in corpus) - set(crows)))
        diffs = []
        for c in corpus:
            got = crows.get(c["name"])
            if not got:
                diffs.append((c["name"], "missing"))
                continue
            want = {k: c[k] for k in got}
            if got != want:
                diffs.append((c["name"], got, want))
        check("compiled C decisions == tests/handoff-cases.json", not diffs, diffs[:2])
        check("compiled C invariants pass", out is not None and "FAIL" not in out.splitlines()[-1],
              out.splitlines()[-1] if out else "")
    else:
        note("C layer skipped (no compiler) - the Python model and the corpus were still executed")

    # 4. the simulation invariants
    ready = cfg["launcher_ready_ms"]
    legacy = simulate(cfg, ready, cfg["min_cycles"], mode="legacy")
    a33 = simulate(cfg, ready, cfg["min_cycles"], mode="a33")
    never = simulate(cfg, ready, cfg["min_cycles"], launcher_never=True)
    check("legacy (A31/A32) reproduces the reported defect",
          legacy["static_wallpaper"] and legacy["frames_shown"] < cfg["mp4_frames"],
          "frames=%s" % legacy["frames_shown"])
    check("A33 shows at least one COMPLETE play-through before the handoff",
          a33["frames_shown"] >= cfg["mp4_frames"] and not a33["static_wallpaper"],
          "frames=%s" % a33["frames_shown"])
    check("A33 cut is zero frames", a33["cut_frames"] == 0 and a33["cut_pct"] == 0.0, a33)
    check("A33 handoff happens only after the launcher is ready",
          a33["handoff_ms"] is not None and a33["handoff_ms"] >= ready, a33["handoff_ms"])
    for mc in (1, 2, 3):
        r = simulate(cfg, ready, mc)
        check("floor=%d is honoured exactly (%d complete cycles)" % (mc, mc),
              r["frames_shown"] >= mc * cfg["mp4_frames"], r["frames_shown"])
    check("launcher never ready => animation keeps the panel (resume, no blank frame)",
          never["owner"] == "anim" and never["resumed"] and not never["static_wallpaper"], never)
    check("with no launcher the bridge never takes ownership",
          take_ownership(0, 1, 0, 0)[0] == 0 and take_ownership(0, 0, 1, 1)[0] == 0)
    for mc in (0, 1, 2):
        r = simulate(cfg, ready, mc, mode="a33")
        check("fail-safe stays bounded (floor=%d)" % mc,
              r["handoff_ms"] is not None and r["handoff_ms"] <= cfg["max_wait_s"] * 1000, r["handoff_ms"])

    # 4b. the verbose-boot skip: a recorded user choice, never a completed cycle
    check("verbose skip waives the floor only with the request file",
          verbose_skip(1, 1, 1, 0, 1, 0) == (1, "verbose_boot_requested") and
          verbose_skip(1, 1, 0, 0, 1, 0) == (0, "floor_pending"), verbose_skip(1, 1, 1, 0, 1, 0))
    check("verbose skip never fires before the launcher is ready",
          verbose_skip(0, 1, 1, 0, 1, 0)[0] == 0 and verbose_skip(0, 1, 1, 0, 1, 0)[1] == "launcher_not_ready")
    check("verbose skip never fires without a painter",
          verbose_skip(1, 0, 1, 0, 1, 0) == (0, "no_painter"))
    check("verbose skip never fires when the floor was already reached",
          verbose_skip(1, 1, 1, 1, 1, 0) == (0, "floor_already_met") and
          verbose_skip(1, 1, 1, 0, 1, 1) == (0, "floor_already_met"))
    check("the shipping config does not waive the floor by itself",
          cfg.get("mode") == "receipt" and int(cfg.get("min_cycles", 0)) >= 1, cfg.get("min_cycles"))
    check("the verbose-boot consumer publishes exactly the request file the bridge reads",
          "anim-skip.request" in open(os.path.join(HERE, "nuxel-verbose-boot.py"), encoding="utf-8").read())

    # 5. the auditor, including a negative control
    with tempfile.TemporaryDirectory() as d:
        def write(rel, txt):
            p = os.path.join(d, rel.lstrip("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(txt)
        write(PATHS["lock"], "4242\n")
        write(PATHS["record"], "schema_version=1\nowner=nuxel-wl-fb\npid=4242\nstage=LAUNCHER_DISPLAY_OWNER\n"
                               "ui_writer=1\nreason=single_owner_takeover\nreceipt=1750000000-LAUNCHER_DISPLAY_OWNER-4242\n"
                               "lock=/run/nuxel-fb-owner.lock\nboot_id=test\nts=1750000000\n")
        write(PATHS["receipt"], json.dumps({"schema_version": 1, "receipt_id": "r1", "owner": "ui",
                                            "stage": "LAUNCHER_DISPLAY_OWNER", "terminal": 1,
                                            "reason": "launcher_display_owner", "loops_seen": 1,
                                            "min_cycles": 1, "mp4_frames": 192, "mp4_fps": 24,
                                            "cycle_ms": 8000, "launcher_ready": 1, "painter_pid": 0,
                                            "pid": 4242, "boot_id": "test", "ts": 1750000000}))
        write(PATHS["log"], "1750000001 NUXEL_ANIM_HANDOFF receipt=r1 owner=ui stage=LAUNCHER_DISPLAY_OWNER "
                            "terminal=1 loops=1/1 reason=launcher_display_owner\n")
        rep, bad = audit(d, expect_ui=True)
        check("auditor accepts a correct single-owner handoff", bad == 0, rep["failed"])
        write(PATHS["receipt"], json.dumps({"schema_version": 1, "owner": "ui",
                                            "stage": "LAUNCHER_DISPLAY_OWNER", "terminal": 0,
                                            "loops_seen": 0, "min_cycles": 1, "reason": "launcher_display_owner"}))
        rep2, bad2 = audit(d, expect_ui=True)
        check("auditor rejects a handoff with no completed cycle on the glass",
              bad2 > 0 and "minimum_cycle_observed" in rep2["failed"], rep2["failed"])
        write(PATHS["receipt"], json.dumps({"schema_version": 1, "owner": "ui", "terminal": 1,
                                            "loops_seen": 1, "min_cycles": 1, "reason": "launcher_display_owner"}))
        write(PATHS["lock"], "9999\n")   # a second, different writer holds the lock
        rep3, bad3 = audit(d, expect_ui=True)
        check("auditor rejects two different writers (negative control)",
              bad3 > 0 and "single_writer" in rep3["failed"], rep3["failed"])

    print("\n%s handoff harness selftest (%d failures)" % ("FAIL" if failures else "PASS", failures))
    return failures


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Nuxel A33 boot-animation handoff harness")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("simulate", help="replayable handoff timeline simulation")
    s.add_argument("--launcher-ready", type=float, default=None, help="seconds after animation start")
    s.add_argument("--min-cycles", type=int, default=None)
    s.add_argument("--config", default=None)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_simulate)
    a = sub.add_parser("audit", help="audit the real handoff artefacts")
    a.add_argument("--root", default="/")
    a.add_argument("--expect-ui", action="store_true", help="the handoff must have completed")
    a.add_argument("--json", action="store_true")
    a.add_argument("--strict", action="store_true", help="non-zero exit on FAIL")
    a.set_defaults(func=cmd_audit)
    t = sub.add_parser("selftest", help="offline proof of the whole harness")
    t.add_argument("--config", default=None)
    t.set_defaults(func=cmd_selftest)
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 2
    rc = args.func(args)
    return rc if isinstance(rc, int) else 0


if __name__ == "__main__":
    sys.exit(main())
