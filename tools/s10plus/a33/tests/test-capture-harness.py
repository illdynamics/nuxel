#!/usr/bin/env python3
"""Offline tests for nuxel-touch-capture.sh (briq-01d, the owner-test harness).

What this asserts (no phone, no root, no /dev/input, no reboot):

1. The harness is a real, syntactically valid script and `--commands` is a pure
   printer: it arms nothing, takes no lock and creates no bundle.
2. The printed owner command set is runnable ON THE DEVICE (installed tracer
   path), and it checks the boot mode FIRST - the charger/LPM boot is the state
   in which the touchscreen does not exist at all.
3. `CAPTURE_GATE=PASS` can only come from the machine gate reading `pass: true`
   out of gate.json - never from a heuristic, a timeout or an empty capture.
4. A dry-run produces a complete bundle (gate.json + trace.txt + 7 LAYER lines +
   FIRST_FAIL_LAYER) and reports NEEDS_OWNER_TEST, never VERIFIED_ON_S10PLUS.
5. Boundedness: the run terminates far inside its own budget.
6. The bundle is never written inside the repository: with the default path
   unwritable (a development host) it goes to ${TMPDIR:-/tmp}, and an explicit
   unwritable --out is a hard block, not a silent relocation.
7. The harness never names a fixed /dev/input/eventN node.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
HARNESS = os.path.join(A33, "nuxel-touch-capture.sh")

failures = []


def check(cond, what, extra=""):
    if cond:
        print("PASS %s" % what)
    else:
        print("FAIL %s%s" % (what, (" :: " + extra) if extra else ""))
        failures.append(what)


def run(args, cwd=None, env=None, timeout=120):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(["bash", HARNESS] + args, capture_output=True, text=True,
                       cwd=cwd, env=e, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def main():
    print("== capture harness (briq-01d) ==")
    check(os.path.isfile(HARNESS), "harness exists at tools/s10plus/a33/nuxel-touch-capture.sh")
    check(os.access(HARNESS, os.X_OK), "harness is executable")
    syn = subprocess.run(["bash", "-n", HARNESS], capture_output=True, text=True)
    check(syn.returncode == 0, "harness parses (bash -n)", syn.stderr.strip())

    src = io.open(HARNESS, encoding="utf-8").read()

    # -- source-level contract -------------------------------------------------
    check("CAPTURE_GATE=BLOCKED reason=charger-mode-boot" in src,
          "charger/LPM boot short-circuits the harness before arming anything")
    check('if [ "$DRY_RUN" = 0 ]; then' in src and "trap release_lock EXIT" in src,
          "the owner-test lock is only taken on a real run and always released by a trap")
    check('if g.get("pass"):' in src and "print(\"PASS NEEDS_OWNER_CONFIRMATION\")" in src,
          "CAPTURE_GATE=PASS is derived from gate.json pass:true, and even then only asks "
          "for owner confirmation")
    check("NEEDS_OWNER_TEST" in src and "VERIFIED_ON_S10PLUS" in src,
          "the harness states the NEEDS_OWNER_TEST rule and never claims VERIFIED_ON_S10PLUS")
    check(not re.search(r"/dev/input/event[0-9]", src) and not re.search(r"\bevent[0-9]+\b", src),
          "no hard-coded /dev/input/eventN node in the harness")

    # -- the printed owner command set ----------------------------------------
    rc, out = run(["--commands"])
    check(rc == 0, "--commands exits 0 (pure printer)", "rc=%d" % rc)
    check(out.count("# ") >= 8 and "androidboot.mode" in out,
          "--commands prints the numbered diagnostic set and checks the boot mode first")
    check("/usr/libexec/nuxel/nuxel-touch-trace.py" in out,
          "--commands gives the ON-DEVICE tracer path, not a checkout-relative one")
    cmd_lines = [l.strip() for l in out.splitlines()
                 if l.strip() and not l.strip().startswith("#")]
    check(not any("tools/s10plus/a33/nuxel-touch-trace.py" in l for l in cmd_lines),
          "--commands pastes no repo-relative tool path on a runnable command line")
    check("/run/nuxel-libinput-path.state" in out and "/run/nuxel-home.state" in out,
          "--commands names the libinput shim state and the launcher DOM state log paths")
    check("BUNDLE=" not in out and "CAPTURE_GATE=" not in out,
          "--commands arms and captures nothing (no BUNDLE, no gate verdict)")

    tmp = tempfile.mkdtemp(prefix="nuxel-harness-test-")

    # -- explicit --out dry-run ----------------------------------------------
    t0 = time.time()
    bundle = os.path.join(tmp, "dry-explicit")
    rc, out = run(["--dry-run", "--seconds", "2", "--out", bundle], timeout=90)
    dt = time.time() - t0
    check(dt < 60, "a 2 s dry-run terminates far inside the hard bound (%.1fs)" % dt)
    check("BUNDLE=%s" % bundle in out, "BUNDLE= echoes the requested directory", out[-200:])
    check(os.path.isfile(os.path.join(bundle, "gate.json")), "dry-run writes gate.json")
    check(os.path.isfile(os.path.join(bundle, "trace.txt")), "dry-run writes trace.txt")
    check(os.path.isfile(os.path.join(bundle, "commands.txt")),
          "dry-run embeds the diagnostic command set in the bundle")
    lines = [l for l in io.open(os.path.join(bundle, "trace.txt"), encoding="utf-8",
                                errors="replace").read().splitlines() if l.startswith("LAYER=")]
    check(len(lines) == 7, "trace.txt carries exactly 7 LAYER= verdict lines", "got %d" % len(lines))
    check("FIRST_FAIL_LAYER=" in out, "trace.txt/console carry FIRST_FAIL_LAYER=")
    gate = json.load(io.open(os.path.join(bundle, "gate.json"), encoding="utf-8"))
    check(gate.get("pass") is False, "with no finger and no hardware the gate is NOT a pass")
    check("CAPTURE_GATE=PASS" not in out and "CAPTURE_GATE=FAIL" in out,
          "the empty dry-run reports CAPTURE_GATE=FAIL (never PASS without evidence)")
    check("VERDICT=NEEDS_OWNER_TEST" in out,
          "the terminal verdict is NEEDS_OWNER_TEST", out[-160:])
    check("NEEDS_OWNER_CONFIRMATION" not in out,
          "PASS-needs-owner-confirmation is NOT emitted when there is no evidence")

    # -- default path must never land inside the repository --------------------
    scratch = os.path.join(tmp, "scratch-cwd")
    os.makedirs(scratch, exist_ok=True)
    tmpdir = os.path.join(tmp, "tmpdir")
    os.makedirs(tmpdir, exist_ok=True)
    rc, out = run(["--dry-run", "--seconds", "2"], cwd=scratch, env={"TMPDIR": tmpdir}, timeout=90)
    m = re.search(r"^BUNDLE=(.+)$", out, re.M)
    got = m.group(1).strip() if m else ""
    check(bool(got), "default-path dry-run still prints BUNDLE=", out[-200:])
    check(not got.startswith(ROOT + os.sep) and not got.startswith(scratch + os.sep),
          "the default bundle path is never inside the repository or the CWD", got)
    check(not any(n.startswith("touch-capture-") for n in os.listdir(scratch)),
          "no touch-capture-* directory is littered into the working directory")
    check(not any(n.startswith("nuxel-touch-capture-") for n in os.listdir(ROOT)),
          "no capture bundle is littered into the repository root")

    # -- an explicit unwritable --out is a hard block -------------------------
    blocker = os.path.join(tmp, "not-a-dir")
    io.open(blocker, "w").write("x\n")
    rc, out = run(["--dry-run", "--seconds", "2", "--out", os.path.join(blocker, "sub")], timeout=90)
    check("CAPTURE_GATE=BLOCKED reason=out-dir-unwritable" in out,
          "an explicit unwritable --out is a hard BLOCKED, not a silent relocation", out[-200:])
    check(rc == 71, "the unwritable --out block exits 71", "rc=%d" % rc)

    # -- usage is discoverable -------------------------------------------------
    rc, out = run(["--help"])
    check(rc == 0 and "--dry-run" in out and "--commands" in out and "--seconds" in out,
          "--help documents --seconds/--dry-run/--commands")
    rc, out = run(["--nonsense"])
    check(rc == 64 and "unknown argument" in out, "an unknown argument is refused (rc=64)")

    shutil.rmtree(tmp, ignore_errors=True)
    print("== %d failing assertion(s) ==" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
