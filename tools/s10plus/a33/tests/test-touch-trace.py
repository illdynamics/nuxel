#!/usr/bin/env python3
"""Offline tests for nuxel-touch-trace.py (briq-01a).

Three kinds of assertion:

1. SYNTHETIC BUNDLES — built in a temp directory, one per interesting failure
   mode, and graded by the analyzer.  Each asserts exactly which layer fails
   first, so the "name the first layer that drops an event" contract is tested
   rather than assumed.
2. ARCHIVED CAPTURES — the real captures under scripts/s10plus-debug-pack/ and
   .scratch/beta/ (present in this repository) are graded with the same rules.
   This is the briq's OFFLINE_TESTED acceptance: the tool is run against real
   evidence that was produced on the handset in earlier cycles.  Absent archives
   are reported as SKIP, never silently treated as a pass.
3. BOUNDED SESSION — a live dry-run must terminate inside its own budget, and the
   CLI must refuse an unbounded/zero budget, because the live console must never
   hang.

Nothing here claims a finger touched the glass.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TRACER = os.path.join(A33, "nuxel-touch-trace.py")
CAPTURES = os.path.join(ROOT, "scripts", "s10plus-debug-pack", "captures")
SCRATCH_BETA = os.path.join(ROOT, ".scratch", "beta")

failures = []


def check(cond, what, extra=""):
    if cond:
        print("PASS %s" % what)
    else:
        print("FAIL %s%s" % (what, (" :: " + extra) if extra else ""))
        failures.append(what)


def run_tracer(args, timeout=120):
    p = subprocess.run([sys.executable, TRACER] + args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def layer_state(out, n):
    for line in out.splitlines():
        if line.startswith("LAYER=%d " % n):
            for tok in line.split():
                if tok.startswith("STATE="):
                    return tok.split("=", 1)[1]
    return None


def first_fail(out):
    for line in out.splitlines():
        if line.startswith("FIRST_FAIL_LAYER="):
            return line.split("=", 1)[1]
    return None


# --------------------------------------------------------------------------
# synthetic raw event stream: one down, one up, one point
# --------------------------------------------------------------------------
EV_FMT = "llHHi"
EV_SIZE = struct.calcsize(EV_FMT)


def ev(typ, code, val):
    return struct.pack(EV_FMT, 0, 0, typ, code, val)


def raw_touch(x=700, y=1500):
    b = bytearray()
    b += ev(3, 0x2F, 0)        # EV_ABS ABS_MT_SLOT 0
    b += ev(3, 0x39, 5)        # EV_ABS ABS_MT_TRACKING_ID 5  (down)
    b += ev(3, 0x35, x)        # EV_ABS ABS_MT_POSITION_X
    b += ev(3, 0x36, y)        # EV_ABS ABS_MT_POSITION_Y
    b += ev(1, 0x14A, 1)       # EV_KEY BTN_TOUCH 1
    b += ev(0, 0x00, 0)        # EV_SYN SYN_REPORT
    b += ev(3, 0x39, -1)       # EV_ABS ABS_MT_TRACKING_ID -1 (up)
    b += ev(1, 0x14A, 0)       # EV_KEY BTN_TOUCH 0
    b += ev(0, 0x00, 0)        # EV_SYN SYN_REPORT
    return bytes(b)


def interrupts(count):
    return ("            CPU0       CPU1       CPU2       CPU3\n"
            "431:      %6d          0          0          0     GIC   sec_ts\n"
            % count)


BASE_DMESG = (
    "[    1.633010] [0: swapper/0: 1] [sec_input] sec_ts_init\n"
    "[    1.654761] [0: kworker/u16:1: 42] input: sec_touchscreen as "
    "/devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2\n"
    "[    5.962929] [0: kworker/u16:1: 42] sec_ts 4-0048: [sec_input] ic_status_show: lpm:0\n"
)
EVDEV_TXT = (
    "# capability scan of /dev/input (selection is by EVIOCGPROP/EVIOCGBIT, never by number)\n"
    "touch-panel      name='sec_touchscreen'         direct=1 mt=1 btn_touch=1 abs_mt_x=(0, 1439) abs_mt_y=(0, 3039) tracking_id=1\n"
    "keys             name='gpio_keys'               direct=0 mt=0 btn_touch=0 abs_mt_x=None abs_mt_y=None tracking_id=0\n"
    "\n# /proc/bus/input/devices (full)\n"
    "N: Name=\"sec_touchscreen\"\nB: PROP=2\nB: EV=2b\n"
)
LIBINPUT_OK = "PATH_ADD /dev/input/touch-panel accepted=1 reason=INPUT_PROP_DIRECT+ABS_MT\n"
LIBINPUT_REJECT = "PATH_ADD /dev/input/keys accepted=0 reason=INPUT_PROP_DIRECT absent\n"
COMPOSITOR = "pid=1234 (systemctl show -p MainPID --value nuxel-wayland)\n7 -> /dev/input/touch-panel\n\ninput fds: /dev/input/touch-panel\n"
WAYLAND = "# journal: nuxel-wayland\nwl_touch.down id=0 x=700 y=1500\nseat0: focus=nuxel-home\n"
DOM = "# /run/nuxel-touch-dom.log\ntouchstart x=700 y=1500 id=0\n"


def make_bundle(root, name, *, dmesg=BASE_DMESG, cmdline="console=ttySAC0,115200 root=/dev/sda31\n",
                evdev=EVDEV_TXT, raw=True, libinput=LIBINPUT_OK, compositor=COMPOSITOR,
                wayland=WAYLAND, dom=DOM):
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    files = {
        "boot-driver.txt": "# /proc/cmdline\n%s\n\n# dmesg/ram-console (sec_ts excerpt)\n%s" % (cmdline.strip(), dmesg),
        "evdev.txt": evdev or "",
        "interrupts-before.txt": interrupts(100),
        "interrupts-after.txt": interrupts(140 if raw else 100),
        "libinput-path.state": libinput or "",
        "compositor-fds.txt": compositor or "",
        "wayland-seat.txt": wayland or "",
        "dom.txt": dom or "",
        "meta.json": json.dumps({"tool": "nuxel-touch-trace", "version": 1}),
    }
    for fn, txt in files.items():
        with open(os.path.join(d, fn), "w") as f:
            f.write(txt)
    if raw:
        with open(os.path.join(d, "raw-touch.bin"), "wb") as f:
            f.write(raw_touch())
    return d


def main():
    tmp = tempfile.mkdtemp(prefix="nuxel-touch-trace-tests-")
    print("== synthetic bundles (%s) ==" % tmp)

    # 1. a fully delivered pipeline: every layer ok, first_fail = none
    d = make_bundle(tmp, "full-delivery")
    rc, out = run_tracer(["--analyze", d])
    check(rc == 0, "full-delivery: analyzer exits 0 (no failing layer)", "rc=%d\n%s" % (rc, out[-800:]))
    check(first_fail(out) == "none", "full-delivery: FIRST_FAIL_LAYER=none", out[-600:])
    check(all(layer_state(out, n) == "ok" for n in range(1, 8)),
          "full-delivery: all 7 layers ok",
          " ".join("L%d=%s" % (n, layer_state(out, n)) for n in range(1, 8)))
    check("GATE=pass" in out, "full-delivery: the machine gate passes with down+up+coords+DOM", out[-400:])
    check("'pass': true" in out or '"pass": true' in out, "full-delivery: gate JSON says pass")

    # 2. driver present but nothing above it: the first failure is layer 4
    d = make_bundle(tmp, "libinput-rejects", libinput=LIBINPUT_REJECT)
    rc, out = run_tracer(["--analyze", d])
    check(layer_state(out, 4) == "drop", "libinput-reject: layer 4 is 'drop'", out[-500:])
    check(first_fail(out) == "4", "libinput-reject: FIRST_FAIL_LAYER=4", out[-300:])

    # 3b. ANTI-FABRICATION: a checklist line that merely *mentions* accepted=1 is
    #     not evidence that libinput accepted anything.
    d = make_bundle(tmp, "checklist-not-evidence",
                    libinput=None,
                    compositor="", wayland="", dom="", raw=False)
    with open(os.path.join(d, "checklist.txt"), "w") as f:
        f.write('echo "=== libinput acceptance ==="; grep -a accepted=1 '
                '/run/nuxel-libinput-path.state | tail -3\n'
                'echo "=== input devices ==="; grep -A5 sec_touchscreen /proc/bus/input/devices\n')
    rc, out = run_tracer(["--analyze", d])
    check(layer_state(out, 4) == "blocked",
          "a checklist line mentioning accepted=1 does NOT pass layer 4",
          out[-500:])
    check(layer_state(out, 4) != "ok", "layer 4 is never 'ok' from a shell listing")

    # 3c. REAL state-file output IS evidence (the same tokens, in state-file form)
    d = make_bundle(tmp, "real-state-file")
    with open(os.path.join(d, "libinput-path.state"), "w") as f:
        f.write("2026-10-16T12:00:00 PATH_ASSIGN_SEAT seat=seat0\n"
                "2026-10-16T12:00:00 PATH_ADD node=/dev/input/touch-panel accepted=1 "
                "reason=INPUT_PROP_DIRECT+ABS_MT\n")
    rc, out = run_tracer(["--analyze", d])
    check(layer_state(out, 4) == "ok", "real state-file output passes layer 4", out[-500:])

    # 3. no DOM evidence: the walk reaches the top layer and stops there
    d = make_bundle(tmp, "no-dom", dom="")
    rc, out = run_tracer(["--analyze", d])
    check(layer_state(out, 7) == "blocked", "no-dom: layer 7 is 'blocked' (no capture != pass)", out[-500:])
    check(first_fail(out) == "7", "no-dom: FIRST_FAIL_LAYER=7", out[-300:])
    check("GATE=fail" in out, "no-dom: the gate fails without a DOM event")

    # 4. charger/LPM boot: the first failure is layer 1 and it explains itself
    d = make_bundle(tmp, "charger-boot",
                    cmdline="androidboot.mode=charger charging_mode=0x3030\n",
                    dmesg="[    1.674224] [sec_input] sec_ts_init: Do not load driver due to : lpm 1\n"
                          "[    2.257441] tsp_io: disabling\n")
    rc, out = run_tracer(["--analyze", d])
    check(layer_state(out, 1) == "blocked", "charger-boot: layer 1 is blocked (driver absent)", out[-500:])
    check(first_fail(out) == "1", "charger-boot: FIRST_FAIL_LAYER=1")
    check("charger" in out.lower(), "charger-boot: the verdict names the charger/LPM cause")

    # 5. absence of evidence is never a pass
    empty = os.path.join(tmp, "empty")
    os.makedirs(empty, exist_ok=True)
    rc, out = run_tracer(["--analyze", empty])
    check(rc == 3, "empty bundle: exit 3 (a failing layer exists)", "rc=%d" % rc)
    check(all(layer_state(out, n) == "blocked" for n in range(1, 8)),
          "empty bundle: every layer is 'blocked', none is 'ok'")
    check("GATE=fail" in out, "empty bundle: the gate is not passed by an empty capture")

    # 6. json output
    d = make_bundle(tmp, "json-out")
    jf = os.path.join(tmp, "verdict.json")
    rc, out = run_tracer(["--analyze", d, "--json-out", jf])
    check(os.path.isfile(jf), "analyzer writes --json-out")
    if os.path.isfile(jf):
        data = json.load(open(jf))
        check(len(data.get("layers", [])) == 7, "json: 7 layer records")
        check(data.get("first_fail_layer") is None, "json: first_fail_layer is None for a clean run")

    print("== archived captures (real handset evidence) ==")
    archived = []
    if os.path.isdir(CAPTURES):
        for name in sorted(os.listdir(CAPTURES)):
            p = os.path.join(CAPTURES, name)
            if os.path.isdir(p) and ("live-run" in name or "hardware-attempt" in name):
                archived.append(p)
    graded = 0
    for p in archived[-4:]:
        rc, out = run_tracer(["--analyze", p], timeout=180)
        lines = [l for l in out.splitlines() if l.startswith("LAYER=")]
        ok = (len(lines) == 7 and first_fail(out) is not None and rc in (0, 3))
        check(ok, "archived capture graded: %s" % os.path.basename(p),
              "%d layer lines, rc=%d" % (len(lines), rc))
        graded += 1
    if not graded:
        print("SKIP no archived capture directories under %s" % CAPTURES)
    if os.path.isdir(SCRATCH_BETA):
        rc, out = run_tracer(["--analyze", SCRATCH_BETA], timeout=180)
        lines = [l for l in out.splitlines() if l.startswith("LAYER=")]
        check(len(lines) == 7, "archived capture graded: .scratch/beta (%d layer lines)" % len(lines),
              out[-400:])
    else:
        print("SKIP no .scratch/beta directory")

    print("== bounded session invariants ==")
    t0 = time.time()
    rc, out = run_tracer(["--live", "--dry-run", "--seconds", "2",
                          "--out", os.path.join(tmp, "dry")], timeout=60)
    dt = time.time() - t0
    check(dt < 45, "a 2 s dry-run terminates well inside the hard bound (%.1fs)" % dt)
    check("FIRST_FAIL_LAYER=" in out, "dry-run still prints one verdict per layer + FIRST_FAIL_LAYER")
    check(len([l for l in out.splitlines() if l.startswith("LAYER=")]) == 7,
          "dry-run prints exactly 7 LAYER lines")
    p = subprocess.run([sys.executable, TRACER, "--live", "--seconds", "0"],
                       capture_output=True, text=True, timeout=60)
    check(p.returncode != 0 and "1..900" in (p.stdout + p.stderr),
          "an out-of-range budget is refused instead of running unbounded",
          (p.stdout + p.stderr)[-200:])

    # stage-probe mode exists and is non-destructive on a host with no docroot
    rc, out = run_tracer(["--stage-probe", "--out", os.path.join(tmp, "stage")], timeout=60)
    check(rc == 0 and "NEEDS_OWNER_TEST" in out, "--stage-probe runs, stages nothing on a host, "
          "and states the NEEDS_OWNER_TEST rule", out[-300:])

    # ---------------------------------------------------------------- A33 adds
    print("== host self-test (briq-01a evidence line) ==")
    rc, out = run_tracer(["--self-test"], timeout=60)
    check(rc == 0, "--self-test exits 0 on the host", out[-400:])
    check("SELF-TEST: PASS" in out, "--self-test reports PASS", out[-200:])
    check("not a touch verification" in out,
          "--self-test states it is NOT a touch verification")

    print("== bounded owner-tap capture (--capture) ==")
    cap = os.path.join(tmp, "capture")
    rc, out = run_tracer(["--capture", "2", "--dry-run", "--out", cap], timeout=90)
    check(os.path.isfile(os.path.join(cap, "events.jsonl")),
          "--capture writes the per-event JSONL stream (events.jsonl)")
    check(os.path.isfile(os.path.join(cap, "coordinate-map.json")),
          "--capture writes coordinate-map.json")
    check("EVENTS_JSONL=" in out and "COORD_VALIDATION points=" in out,
          "--capture reports the JSONL path and runs the coordinate validation")
    check("expect-finger" in out,
          "--capture states that a finger is expected (NEEDS_OWNER_TEST until then)")
    check(os.path.isfile(os.path.join(cap, "sysfs-input.txt")),
          "--capture records the /sys/class/input capability scan")
    p = subprocess.run([sys.executable, TRACER, "--capture", "0", "--dry-run",
                        "--out", os.path.join(tmp, "cap0")],
                       capture_output=True, text=True, timeout=60)
    check(p.returncode != 0 and "1..900" in (p.stdout + p.stderr),
          "--capture 0 is refused instead of running unbounded", (p.stdout + p.stderr)[-160:])

    print("== per-layer exit codes ==")
    d = make_bundle(tmp, "layer-exit-clean")
    rc, out = run_tracer(["--analyze", d, "--layer-exit-codes"])
    check(rc == 0, "--layer-exit-codes: a fully delivered pipeline exits 0", "rc=%d" % rc)
    check("EXIT_CODE=0" in out, "--layer-exit-codes: prints EXIT_CODE=0")
    n_exit = len([l for l in out.splitlines() if l.startswith("LAYER_EXIT=")])
    check(n_exit == 7, "--layer-exit-codes: one LAYER_EXIT line per layer (%d)" % n_exit)
    empty2 = os.path.join(tmp, "empty-for-exit")
    os.makedirs(empty2, exist_ok=True)
    rc, out = run_tracer(["--analyze", empty2, "--layer-exit-codes"])
    check(rc == 11, "--layer-exit-codes: no evidence exits 10+1=11 (first lossy layer)", "rc=%d" % rc)
    check("EXIT_CODE=11" in out, "--layer-exit-codes: names layer 1 as the first lossy hop")
    rc, out = run_tracer(["--analyze", empty2])
    check(rc == 3, "without the flag the historical exit status 3 is kept", "rc=%d" % rc)

    print("== capability scan from a synthetic /sys/class/input (no phone) ==")
    fix = os.path.join(A33, "tests", "fixtures", "sec-ts-only", "sys", "class", "input")
    if os.path.isdir(fix):
        sc = os.path.join(tmp, "sysfs-scan")
        rc, out = run_tracer(["--live", "--dry-run", "--seconds", "2",
                              "--sysfs-root", fix, "--out", sc], timeout=90)
        check("selected=" in out and "sec_touchscreen" in out,
              "sysfs scan selects the panel by capability (ABS_MT + direct marker)", out[-400:])
        check("direct=1" in out and "mt=1" in out,
              "sysfs scan reports direct/mt as numbers, not as an assumption")
        check("vendor=" in out and "product=" in out,
              "sysfs scan reports the vendor/product identity fields")
        txt = ""
        p = os.path.join(sc, "sysfs-input.txt")
        if os.path.isfile(p):
            txt = open(p).read()
        check("gpio_keys" in txt and "direct=0" in txt and "mt=0" in txt,
              "sysfs scan records the non-touch node as rejected BY CAPABILITY (direct=0 mt=0)")
        check("SELECTED" in txt and "sec_touchscreen" in txt,
              "the sysfs scan is written into the bundle as evidence")
        check("4095" in out,
              "the raw device range comes from the fixture absinfo (no node was openable)", out[-300:])
        check("mapping=scaled" in out,
              "a 0..4095 device range against the 1440x3040 panel maps as 'scaled'")
    else:
        print("SKIP no fixture at %s" % fix)

    print("== archive into the repository evidence root ==")
    src_bundle = make_bundle(tmp, "archive-me")
    dest = os.path.join(tmp, "archive-root")
    rc, out = run_tracer(["--archive", src_bundle, "--archive-dir", dest], timeout=60)
    check(rc == 0 and "ARCHIVED=" in out, "--archive copies the bundle", out[-300:])
    made = [d for d in os.listdir(dest) if d.startswith("touch-")] if os.path.isdir(dest) else []
    check(len(made) == 1 and made[0].startswith("touch-"),
          "--archive lands under touch-<ts>/ in the archive root", str(made))
    check(os.path.isfile(os.path.join(dest, "INDEX.jsonl")),
          "--archive appends the archive INDEX.jsonl")
    if made:
        check(os.path.isfile(os.path.join(dest, made[0], "meta.json"))
              and os.path.isfile(os.path.join(dest, made[0], "evdev.txt")),
              "--archive copies the bundle contents")
    rc, out = run_tracer(["--archive", os.path.join(tmp, "nope"), "--archive-dir", dest], timeout=60)
    check(rc == 4 and "ARCHIVE_FAILED" in out,
          "--archive of a missing bundle fails loudly with rc=4", out[-200:])

    # ------------------------------------------------------------------ honesty
    print("== honesty regressions found by grading a REAL capture this cycle ==")
    # 1. A live-console command FRAME is a command, not device output.  The real
    #    charger-mode capture contained the header
    #      ===== grep -c sec_touchscreen /proc/bus/input/devices   [rc=1 frame=.. sha_ok=yes]
    #    and the naive match reported "the panel appears in the evidence" for a boot
    #    where the driver never initialised.
    d = make_bundle(tmp, "console-frame-is-a-command",
                    dmesg="[    1.638064] [sec_input] sec_ts_init: Do not load driver due to : lpm 1\n",
                    cmdline="console=ram androidboot.mode=charger\n",
                    evdev='===== grep -c sec_touchscreen /proc/bus/input/devices; echo "x_rc=$?"'
                          '   [rc=1 frame=1eb660d8 sha_ok=yes]\n    0\n',
                    raw=False)
    rc, out = run_tracer(["--analyze", d])
    check(layer_state(out, 1) == "blocked", "framed capture: layer 1 is blocked (charger cause)")
    check("appears in the evidence" not in out,
          "framed capture: a command frame mentioning the panel is NOT read as the panel appearing",
          out[-500:])
    check(layer_state(out, 3) == "blocked", "framed capture: layer 3 is blocked, never ok")

    # 2. A bundle that also carries a previous VERDICT must not grade itself.  The
    #    real capture exposed this: a second analyze run with --json-out inside the
    #    bundle reported LAYER=6 ok from its own earlier sentence.
    d = make_bundle(tmp, "no-self-feeding", wayland="", raw=False)
    with open(os.path.join(d, "previous-verdict.txt"), "w") as f:
        f.write("LAYER=6 NAME=wayland STATE=ok EVIDENCE=x "
                "DETAIL=wl_touch present in the compositor protocol capture\n"
                '{"tool": "nuxel-touch-trace", "layers": []}\n')
    rc, out = run_tracer(["--analyze", d])
    check(layer_state(out, 6) != "ok",
          "a previous verdict inside the bundle is never re-graded as evidence",
          out[-500:])

    # 3. Grade the REAL capture this cycle took on the handset over the live console
    #    (read-only: /proc/cmdline, dmesg, /sys, /dev/input listings).
    live_root = os.path.join(ROOT, "docs", "beta-finalization", "live", "evidence")
    live = []
    if os.path.isdir(live_root):
        live = sorted(os.path.join(live_root, n) for n in os.listdir(live_root)
                      if n.startswith("touch-") and n.endswith("live-run")
                      and os.path.isdir(os.path.join(live_root, n)))
    if live:
        rc, out = run_tracer(["--analyze", live[-1]], timeout=180)
        check(len([l for l in out.splitlines() if l.startswith("LAYER=")]) == 7,
              "live capture graded: 7 layer lines", out[-400:])
        check(first_fail(out) == "1",
              "live capture graded: FIRST_FAIL_LAYER=1 (the driver, absent on this boot)",
              out[-400:])
        check("charger" in out.lower(),
              "live capture graded: the verdict names the charger/LPM cause")
        check("sec_ts_init: Do not load driver due to" in out,
              "live capture graded: the kernel's own -ENODEV line is cited as evidence")
        check("wl_touch present" not in out,
              "live capture graded: no layer is promoted from prose or from a prior verdict")
    else:
        print("SKIP no live capture under %s" % live_root)

    print("== %d failing assertion(s), temp dir %s ==" % (len(failures), tmp))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
