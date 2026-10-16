#!/usr/bin/env python3
"""Offline tests for the S10+ sensor work (briq-08g, area 28).

Proven offline: per-class enumeration from three sources (fixtures: IIO readable /
input-hub only / nothing), the capability manifest's "expected != observed"
contract, that raw reads print only real channel values, watch bounding, faked-root
safety and the manual-proof fragment. Physically induced motion stays
NEEDS_OWNER_TEST.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-sensors-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "sensors", "sensors.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "14-sensors.md")
CLASSES = ["accelerometer", "gyroscope", "magnetometer", "proximity", "ambient_light", "barometer"]
fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


p = run(["bash", TOOL, "selftest"])
check("fixture verdicts (iio / input-hub / none) match", p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
check("manifest covers the mission's sensor classes",
      set(CLASSES).issubset(set(pol["classes"])))
check("manifest separates expected hardware from observed state (comment + flags)",
      all("expected_on_s10plus" in v for v in pol["classes"].values())
      and "NOT observations" in pol["comment"])
check("manifest declares the three evidence sources",
      set(pol["evidence_sources"]) >= {"iio", "input", "sysfs_class", "hub_drivers"})
check("every class documents an owner gesture",
      all(v.get("owner_gesture") for v in pol["classes"].values()))

p = run(["bash", TOOL, "--root", os.path.join(FIX, "sensors-iio"), "status"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("IIO fixture reports a readable class and a NOT_SUPPORTED_ON_DEVICE for the rest",
      "readable" in p.stdout and "NOT_SUPPORTED_ON_DEVICE" in p.stdout and "verdict: READABLE_SOME" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "sensors-iio"), "read", "accelerometer"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`read` prints the real raw channels and their values",
      "in_accel_x_raw" in p.stdout and "101" in p.stdout and "(raw)" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "sensors-input"), "status"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("input-hub fixture is PRESENT_UNREADABLE, not absent",
      "verdict: PRESENT_UNREADABLE" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "sensors-none"), "read", "proximity"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`read` on an absent class says there is no raw channel (no fabrication)",
      "no raw channel" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "sensors-none"), "watch", "accelerometer", "99999"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`watch` is bounded by the policy cap", "capping" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "sensors-iio"), "watch", "accelerometer", "1"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`watch` under a faked root never samples the real sysfs",
      "offline/faked root" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "sensors-iio"), "status", "--json"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
doc = json.loads([l for l in p.stdout.splitlines() if l.startswith("{")][0])
check("json reports per-class states and never claims observed motion",
      doc["classes"]["accelerometer"]["state"] == "readable" and doc["observed_motion_verified"] is False)
p = run(["bash", TOOL, "manifest"])
check("`manifest` prints the expected/optional/gesture triple",
      "expected_on_s10plus" in p.stdout and "owner_gesture" in p.stdout, p.stdout[:200])

txt = open(TOOL).read()
check("tool has no flashing/partition surface",
      all(t not in txt for t in ("/dev/block", "heimdall", "fastboot")))

dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment gives physical gestures (tilt/rotate/cover)",
      "tilt" in dtxt.lower() and "cover" in dtxt.lower())
check("fragment marks the motion half NEEDS_OWNER_TEST and absent classes NOT_SUPPORTED_ON_DEVICE",
      "NEEDS_OWNER_TEST" in dtxt and "NOT_SUPPORTED_ON_DEVICE" in dtxt)
check("fragment requires a raw value, never a claim from enumeration",
      "raw" in dtxt.lower())

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for enumeration + diagnostic; NEEDS_OWNER_TEST for motion")
