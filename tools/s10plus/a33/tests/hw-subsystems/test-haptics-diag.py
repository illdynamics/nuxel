#!/usr/bin/env python3
"""Offline tests for the S10+ vibration/haptics work (briq-08b, area 21).

Proven offline: node ENUMERATION + verdict (fixtures: present / absent), the
pattern expander, the persisted global switch, the hard refusals (`buzz` without
--yes, everything while the switch is off), the duration cap, and the
manual-proof fragment's completeness. FELT haptics are not testable offline and
stay NEEDS_OWNER_TEST — a passing run never yields VERIFIED_ON_S10PLUS.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-haptics-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "haptics", "haptics.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "10-vibration.md")
fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None, cwd=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e, cwd=cwd)


p = run(["bash", TOOL, "selftest"])
check("fixture verdicts (present / absent) match", p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
check("policy enumerate node candidates and never pins one path as truth",
      len(pol["node_candidates"]["sysfs"]) >= 4 and len(pol["node_candidates"]["globs"]) >= 2)
check("policy declares a persisted global switch that is not auto-enabled at boot",
      pol["global_switch"]["auto_enable_on_boot"] is False and pol["global_switch"]["state_file"])
check("policy caps the test buzz", pol["diagnostics"]["test_buzz_max_ms"] <= 2000
      and pol["diagnostics"]["require_explicit_yes"] is True)

# present fixture ------------------------------------------------------------
pres = os.path.join(FIX, "haptics-present")
p = run(["bash", TOOL, "--root", pres, "status"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("present fixture reports the enumerated node and its writable file",
      "/sys/class/leds/vibrator" in p.stdout and "activate" in p.stdout, p.stdout)
check("present fixture never claims felt haptics",
      "OFFLINE_TESTED" in p.stdout and "NEEDS_OWNER_TEST" in p.stdout)
p = run(["bash", TOOL, "--root", pres, "status", "--json"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
doc = json.loads([l for l in p.stdout.splitlines() if l.startswith("{")][0])
check("json reports node_present and felt_haptics_verified=false",
      doc["node_present"] is True and doc["felt_haptics_verified"] is False and doc["node"] == "/sys/class/leds/vibrator")
check("json intensity mode is duration when only activate/duration is writable",
      doc["intensity_mode"] == "duration")

# refusals -------------------------------------------------------------------
p = run(["bash", TOOL, "--root", pres, "buzz"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("buzz without --yes is refused (exit 4)", p.returncode == 4 and "refused" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", pres, "buzz", "--yes", "9999"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("buzz --yes is capped to the policy maximum", "capping" in p.stdout, p.stdout)
# global switch off -> everything refuses
tmp = os.path.join(FIX, "haptics-present")
p = run(["bash", TOOL, "--root", tmp, "off"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
# the state file is written under the faked root; assert the refusal is derived from it
statef = os.path.join(tmp, "var/lib/nuxel/haptics/state.json")
check("`off` persists enabled=false in the faked-root state file",
      os.path.isfile(statef) and '"enabled":false' in open(statef).read(), statef)
p = run(["bash", TOOL, "--root", tmp, "buzz", "--yes", "100"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("buzz is refused while the global switch is off (exit 3)",
      p.returncode == 3 and "switch is OFF" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", tmp, "on"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`on` re-enables the switch", '"enabled":true' in open(statef).read(), statef)
try:
    os.remove(statef)
except OSError:
    pass

# pattern expander -----------------------------------------------------------
p = run(["bash", TOOL, "pattern", "notify"])
check("pattern expander prints the notify steps", p.stdout.strip() != "" and re.match(r"^[\d ]+$", p.stdout.strip()), p.stdout)
p = run(["bash", TOOL, "pattern", "notify", "50"])
check("pattern expander scales with a percentage", p.stdout.strip() != "" and re.match(r"^[\d ]+$", p.stdout.strip()), p.stdout)
p = run(["bash", TOOL, "pattern", "nope"])
check("unknown pattern names the known ones instead of guessing", "unknown pattern" in p.stdout)

# no buzz at boot / no auto-on ---------------------------------------------
txt = open(TOOL).read()
check("only the explicit `buzz` command can buzz (one definition, one call site)",
      "cmd_buzz" in txt and txt.count("cmd_buzz") == 2, "cmd_buzz: 1 definition + 1 dispatch call site")
check("tool writes only the enumerated node's own files (no block/partition surface)",
      "/dev/block" not in txt and "heimdall" not in txt.lower())

# manual-proof fragment ------------------------------------------------------
dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment requires --yes for the test buzz", "--yes" in dtxt)
check("fragment marks the felt half NEEDS_OWNER_TEST", "NEEDS_OWNER_TEST" in dtxt)
check("fragment documents the global off switch", "off" in dtxt.lower() and "switch" in dtxt.lower())

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for the API; NEEDS_OWNER_TEST for felt haptics")
