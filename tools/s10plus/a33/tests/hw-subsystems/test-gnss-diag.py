#!/usr/bin/env python3
"""Offline tests for the S10+ GNSS/GPS + offline-OSM work (briq-08f, area 25).

Proven offline: per-stage evidence + verdict (five fixtures: no receiver /
no firmware / BCM4773 ttyBCM without firmware / node-without-module / stream-ready), that no coordinate is ever
fabricated by `monitor` or `stream`, the offline-first map contract, faked-root
safety and the manual-proof fragment. A real fix stays NEEDS_OWNER_TEST.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-gnss-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "gnss", "gnss.json")
MAP = os.path.join(ROOT, "configs", "nuxel", "gnss", "osm-tiles.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "13-gps.md")
fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


def jdoc(out):
    return json.loads([l for l in out.splitlines() if l.startswith("{")][0])


p = run(["bash", TOOL, "selftest"])
check("fixture verdicts (absent / nofw / partial / ready) match", p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
check("policy declares the stage order and verdict set",
      pol["first_failing_stage_order"][:3] == ["device_node", "module", "firmware"]
      and pol["first_failing_stage_order"][-2:] == ["stream", "fix"]
      and set(pol["verdicts"]) >= {"READY_FOR_SKY", "BLOCKED_KERNEL", "BLOCKED_FIRMWARE",
                                   "BLOCKED_EXTERNAL_RESOURCE", "NO_FIX", "PARTIAL",
                                   "BLOCKED_PROTOCOL", "BLOCKED_VENDOR_RUNTIME"})
check("policy requires an OUTDOORS owner test and never a fabricated fix",
      pol["fix_test"]["outdoors_required"] is True and "no coordinate" in pol["comment"].lower())
check("policy states the offline map is network-optional and cached-area capable",
      pol["offline_map"]["network_optional"] is True)

mp = json.load(open(MAP))
check("map contract carries the OSM attribution and the tile layout",
      "OpenStreetMap" in mp["attribution"] and mp["tiles"]["layout"] == "{z}/{x}/{y}.png")
check("map contract forbids a fixed coordinate in the repository",
      mp["geolocation"]["no_fixed_coordinate_in_repo"] is True)
check("map contract requires cached areas to work without network",
      mp["offline_first"]["requires_network_for_cached_area"] is False)

p = run(["bash", TOOL, "--root", os.path.join(FIX, "gnss-ready"), "status", "--json"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
doc = jdoc(p.stdout)
check("ready fixture reports node/module/firmware/stream/stack stages",
      doc["stages"]["device_node"].startswith("node:") and doc["stages"]["module"].startswith("loaded:")
      and doc["stages"]["firmware"].startswith("found:") and doc["stages"]["stream"].startswith("readable:"))
check("ready fixture refuses a fix claim from a stream alone",
      doc["state"] == "READY_FOR_SKY" and doc["fix_verified"] is False and doc["first_failing_stage"] == "fix")

for name, state, stage in (("gnss-absent", "BLOCKED_KERNEL", "device_node"),
                           ("gnss-nofw", "BLOCKED_FIRMWARE", "firmware"),
                           ("gnss-bcm-nofw", "BLOCKED_FIRMWARE", "firmware"),
                           ("gnss-partial", "PARTIAL", "module")):
    p = run(["bash", TOOL, "--root", os.path.join(FIX, name), "status"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
    check("%s names stage=%s and verdict=%s" % (name, stage, state),
          ("first failing stage : %s" % stage) in p.stdout and ("verdict             : %s" % state) in p.stdout, p.stdout)

# no fabricated coordinates: monitor/stream under a faked root must print dry-run text only
for cmd in ("stream", "monitor"):
    p = run(["bash", TOOL, "--root", os.path.join(FIX, "gnss-ready"), cmd, "2"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
    check("%s under a faked root never prints a coordinate" % cmd,
          "no coordinate is fabricated" in p.stdout
          and not any(any(x in l for x in ("N,", "S,", "E,", "W,"))
                      for l in p.stdout.splitlines()), p.stdout)
    check("%s is bounded by the policy cap" % cmd,
          "capping" in run(["bash", TOOL, "--root", os.path.join(FIX, "gnss-ready"), cmd, "99999"],
                           {"NUXEL_DIAG_NO_SYSTEM": "1"}).stdout)
    check("%s refuses with no readable node" % cmd,
          run(["bash", TOOL, "--root", os.path.join(FIX, "gnss-absent"), cmd, "2"],
              {"NUXEL_DIAG_NO_SYSTEM": "1"}).returncode == 2)

txt = open(TOOL).read()
check("tool has no coordinate constant and no flashing surface",
      "/dev/block" not in txt and "heimdall" not in txt.lower()
      and not any(s in txt for s in ("52.3", "4.89", "N 5", "51.5")))
p = run(["bash", TOOL, "map"])
check("`map` prints the attribution, layout and offline rules",
      "OpenStreetMap" in p.stdout and "{z}/{x}/{y}.png" in p.stdout and "must load offline" in p.stdout, p.stdout)

dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment requires standing outdoors and waiting for a fix",
      "outdoors" in dtxt.lower() and "fix" in dtxt.lower())
check("fragment verifies coordinates on the offline map",
      "OpenStreetMap" in dtxt or "OSM" in dtxt)
check("fragment marks the fix NEEDS_OWNER_TEST and forbids a fabricated fix",
      "NEEDS_OWNER_TEST" in dtxt and "fabricat" in dtxt.lower())

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for config + diagnostic; NEEDS_OWNER_TEST for a real fix")
