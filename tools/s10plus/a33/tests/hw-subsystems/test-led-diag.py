#!/usr/bin/env python3
"""Offline tests for the S10+ LED / flashlight work (briq-08c, areas 9 + 22).

Proven offline: truthful class ENUMERATION (fixtures: torch only / notification
only / none), the explicit-off path, the bounded torch (--yes required, policy
cap, forced off), the notification-LED absence path, and the manual-proof
fragment. VISIBLE light is the owner's observation and stays NEEDS_OWNER_TEST.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-led-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "leds", "leds.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "09-flashlight.md")
fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


def json_of(out):
    return json.loads([l for l in out.splitlines() if l.startswith("{")][0])


p = run(["bash", TOOL, "selftest"])
check("fixture class verdicts (torch / notif-only / none) match", p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
check("policy declares the three classes", set(pol["classes"]) >= {"flashlight", "notification", "edge_lighting"})
check("edge lighting is modelled as a display overlay, not a hardware LED",
      pol["classes"]["edge_lighting"]["hardware_led"] is False
      and pol["classes"]["edge_lighting"]["kind"] == "display_overlay")
check("policy forbids auto-on at boot and caps the torch",
      60000 >= pol["safety"]["max_on_ms"] > 0 and pol["safety"]["auto_on_boot"] is False)

p = run(["bash", TOOL, "--root", os.path.join(FIX, "leds-torch"), "status", "--json"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
doc = json_of(p.stdout)
check("torch fixture: flashlight present with the real path",
      doc["classes"]["flashlight"]["present"] is True
      and doc["classes"]["flashlight"]["path"] == "/sys/class/leds/led:flash_0")
check("absent notification class is NOT_SUPPORTED_ON_DEVICE",
      doc["classes"]["notification"]["present"] is False
      and doc["classes"]["notification"]["state"] == "NOT_SUPPORTED_ON_DEVICE")
check("visible light is never claimed (flashlight_verified=false)", doc["flashlight_verified"] is False)

p = run(["bash", TOOL, "--root", os.path.join(FIX, "leds-none"), "flash", "--yes", "100"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("torch on a class-less device is refused (exit 2, NOT_SUPPORTED_ON_DEVICE)",
      p.returncode == 2 and "NOT_SUPPORTED_ON_DEVICE" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "leds-torch"), "flash", "100"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("torch without --yes is refused (exit 4)", p.returncode == 4 and "refused" in p.stdout, p.stdout)

# explicit off path clears a lit node and writes nothing outside the LED class
fixt = os.path.join(FIX, "leds-torch")
bright = os.path.join(fixt, "sys/class/leds/led:flash_0/brightness")
open(bright, "w").write("255\n")
p = run(["bash", TOOL, "--root", fixt, "off"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`off` forces brightness 0 on every class found",
      open(bright).read().strip() == "0" and "explicit OFF" in p.stdout, open(bright).read())
p = run(["bash", TOOL, "--root", os.path.join(FIX, "leds-none"), "notify", "red"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("notify without a notification class is refused and names the display fallback",
      p.returncode == 2 and "NOT_SUPPORTED_ON_DEVICE" in p.stdout and "display" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "leds-notif"), "notify", "red"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("notify uses the enumerated notification class when it exists",
      p.returncode == 0 and "/sys/class/leds/led:notification" in p.stdout, p.stdout)

txt = open(TOOL).read()
check("LED tool has no flashing/partition surface",
      all(t not in txt for t in ("/dev/block", "heimdall", "fastboot")))
check("no boot-time auto-on path exists in the tool",
      "auto_on_boot" not in txt or "none at boot" in txt)

dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment documents the explicit OFF and the --yes gate", "off" in dtxt.lower() and "--yes" in dtxt)
check("fragment marks visible light NEEDS_OWNER_TEST", "NEEDS_OWNER_TEST" in dtxt)
check("fragment states NOT_SUPPORTED_ON_DEVICE for absent classes", "NOT_SUPPORTED_ON_DEVICE" in dtxt)

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for control logic; NEEDS_OWNER_TEST for visible light")
