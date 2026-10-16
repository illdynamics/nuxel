#!/usr/bin/env python3
"""Offline tests for the S10+ headphone-jack / USB-C audio detection and routing
(briq-03d, mission area 7).

WHAT IS PROVEN HERE (OFFLINE_TESTED)
  1. The REAL diagnostic decides the route from observable evidence only: seven
     faked roots (no card / jack removed / headphones / headset / USB-C digital /
     USB-C analog / no jack control) are driven through the shipped script, and
     each verdict is checked against its EXPECTED file.
  2. The microphone rule is classified BEFORE the playback-jack rule. A control
     named "Headset Mic Jack" also contains the substring "headset...jack"; if it
     were matched as the output jack a plugged headset would be reported as a
     plain headphone (or as removed). The fixture that carries both controls
     locks the corrected ordering in place.
  3. Route switching is revert-aware and safe: an unknown accessory is REFUSED,
     a route is never applied without --yes, a route is never applied at all
     when the UCM tool is not installed (BLOCKED_EXTERNAL_RESOURCE), and the
     policy keeps the on-unplug revert rule and the low-volume cap.
  4. The tool contains no flashing/partition-write surface (NO FLASHING
     invariant, checked mechanically).
  5. The manual-proof fragment has all eight required fields, marks audibility
     NEEDS_OWNER_TEST, and states that this test must never gate another briQ.

WHAT IS NOT PROVEN HERE — and therefore NEEDS_OWNER_TEST: that a human hears
sound through a plugged accessory. Insertion is a state machine; audibility is
not. A passing run is OFFLINE_TESTED, never VERIFIED_ON_S10PLUS.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(os.path.dirname(os.path.dirname(start)))


ROOT = _repo_root(HERE)
TOOL = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-headphone-diag.sh")
AUDIO_TOOL = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-audio-diag.sh")
POLICY = os.path.join(ROOT, "configs", "nuxel", "audio", "jack-routes.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "07-headphones.md")
FIX = os.path.join(HERE, "fixtures-p3")

fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ)
    e["NUXEL_DIAG_NO_SYSTEM"] = "1"
    e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


def temp_root(name):
    """A writable copy of a fixture. Evidence writes are redirected by the tool
    through its fake root, so a case that writes must run on a copy: a test must
    never create files inside the committed fixtures."""
    d = tempfile.mkdtemp(prefix="nuxel-hp-test-")
    dst = os.path.join(d, "root")
    shutil.copytree(fixture(name), dst)
    return dst


def fixture(name):
    return os.path.abspath(os.path.join(FIX, name))


def status_json(name, extra=None):
    env = {"NUXEL_DIAG_ROOT": fixture(name)}
    env.update(extra or {})
    p = run(["bash", TOOL, "status", "--json"], env)
    line = [l for l in p.stdout.splitlines() if l.strip().startswith("{")]
    if not line:
        return None, p
    return json.loads(line[-1]), p


# 1 ── fixture-driven route logic ----------------------------------------------------
p = run(["bash", TOOL, "selftest"])
check("fixtures: all jack/USB-C route expectations match", p.returncode == 0,
      "rc=%d\n%s" % (p.returncode, p.stdout + p.stderr))

CASES = [
    ("jack-none", "UNKNOWN", "none"),
    ("jack-nocontrol", "UNKNOWN", "none"),
    ("jack-removed", "Speaker", "jack-remove"),
    ("jack-inserted-headphones", "Headphones", "jack-insert-headphones"),
    ("jack-inserted-headset", "Headset", "jack-insert-headset"),
    ("jack-usbc-digital", "USB-C Headset (UAC)", "usbc-digital-headset"),
    ("jack-usbc-analog", "UNKNOWN_USBC_ACCESSORY", "usbc-analog-headset"),
]
for name, route, rule in CASES:
    doc, p = status_json(name)
    if doc is None:
        check("fixture %s -> %s" % (name, route), False, p.stdout[-300:])
        continue
    ok = doc.get("route") == route and doc.get("rule") == rule
    check("fixture %s -> %s" % (name, route), ok,
          "route=%s rule=%s" % (doc.get("route"), doc.get("rule")))
    check("%s: audibility is NEEDS_OWNER_TEST (never inferred)" % name,
          doc.get("audibility") == "NEEDS_OWNER_TEST", json.dumps(doc))

# 2 ── the microphone-before-jack ordering fix --------------------------------------
doc, p = status_json("jack-inserted-headset")
check("a TRRS headset with a 'Headset Mic Jack' control is NOT misread as headphones",
      doc is not None and doc.get("route") == "Headset", p.stdout[-300:])
check("the headset fixture reports the mic as present",
      doc is not None and doc.get("mic") == "PRESENT", json.dumps(doc or {}))
check("the detection rule only uses NAMES OBSERVED on the card (policy flag)",
      json.load(open(POLICY))["detection"]["jack_kcontrols"]["require_observed_name"] is True)

# 3 ── route switching: refused, dry-run, revert-aware -------------------------------
p = run(["bash", TOOL, "route"], {"NUXEL_DIAG_ROOT": fixture("jack-none")})
check("an unproven accessory state is REFUSED (nothing is changed)",
      p.returncode == 1 and "REFUSED" in p.stdout, p.stdout[-300:])

p = run(["bash", TOOL, "route"], {"NUXEL_DIAG_ROOT": fixture("jack-usbc-analog")})
check("an unknown USB-C accessory is REFUSED rather than routed blindly",
      p.returncode == 1 and "REFUSED" in p.stdout, p.stdout[-300:])

p = run(["bash", TOOL, "route"], {"NUXEL_DIAG_ROOT": fixture("jack-inserted-headphones")})
check("a proven route is NOT applied without --yes (dry run, rc=2)",
      p.returncode == 2 and "would select UCM device 'Headphones'" in p.stdout, p.stdout[-300:])

d = os.path.join(fixture("jack-inserted-headphones"), "var", "lib", "nuxel", "audio")
p = run(["bash", TOOL, "route", "--yes"], {"NUXEL_DIAG_ROOT": fixture("jack-inserted-headphones")})
check("with --yes but no UCM tool, the switch is reported BLOCKED_EXTERNAL_RESOURCE",
      p.returncode == 1 and "BLOCKED_EXTERNAL_RESOURCE" in p.stdout, p.stdout[-300:])
check("a BLOCKED route writes no jack-state file",
      not os.path.exists(os.path.join(d, "jack-state.json")))

pol = json.load(open(POLICY))
check("policy keeps the on-unplug revert rule",
      pol["revert"]["on_unplug"] is True
      and pol["revert"]["never_leave_routed_to_absent_device"] is True
      and "Speaker" in pol["revert"]["always_restore"])
check("policy re-applies the low-volume cap on every route change",
      pol["safety"]["low_volume_only"] is True
      and pol["safety"]["cap_on_route_change"] is True
      and int(pol["safety"]["volume_cap_percent"]) <= 25)

# bounded watch: logs transitions and applies NOTHING (runs on a writable copy,
# because watch appends to its evidence log)
p = run(["bash", TOOL, "watch", "2"], {"NUXEL_DIAG_ROOT": temp_root("jack-inserted-headphones")})
check("watch is bounded and applies no route by itself",
      p.returncode == 0 and "watch complete" in p.stdout and "No route was applied" in p.stdout,
      p.stdout[-300:])

# the tone is delegated to the single low-volume implementation and refuses --less
p = run(["bash", TOOL, "tone", "500"], {"NUXEL_DIAG_ROOT": fixture("jack-inserted-headphones")})
check("tone without --yes is refused (no unbounded burst, no accidental audibility claim)",
      p.returncode == 2 and "tone" in p.stdout, p.stdout[-300:])
check("one single implementation of the low-volume tone (headphone tool delegates)",
      "nuxel-audio-diag.sh" in open(TOOL).read() and os.path.exists(AUDIO_TOOL))

# 4 ── manual proof fragment --------------------------------------------------------
if os.path.exists(DOC):
    d = open(DOC).read()
    for field in ["Feature", "Why", "Preparation", "Exact action", "Expected result",
                  "Failure symptoms", "Diagnostic", "PASS", "FAIL"]:
        check("manual-proof fragment has field %r" % field, field in d)
    check("manual-proof fragment marks audibility NEEDS_OWNER_TEST", "NEEDS_OWNER_TEST" in d)
    check("manual-proof fragment covers the 3.5 mm jack and the USB-C adapter",
          "3.5 mm" in d and "usb-c" in d.lower())
    check("manual-proof fragment states this test must not gate other work",
          "must not gate" in d.lower() or "never gate" in d.lower())
else:
    check("manual-proof fragment exists", False, DOC)

# 5 ── NO FLASHING invariant, mechanically ------------------------------------------
src = open(TOOL).read()
banned = [r"\bdd\s+if=", r"/dev/block", r"\bheimdall\b", r"\bodind?\b", r"fastboot",
          r"download mode", r"\bflash\b"]
for pat in banned:
    hits = re.findall(pat, src, re.I)
    check("tool contains no flashing surface for %r" % pat, not hits, str(hits))

print("\n== %d failing check(s) ==" % len(fails))
sys.exit(1 if fails else 0)
