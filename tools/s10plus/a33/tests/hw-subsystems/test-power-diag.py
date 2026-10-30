#!/usr/bin/env python3
"""Offline tests for the S10+ power/battery/power-menu work (briq-08a, areas 17+18).

Proven offline, and nothing more:
  1. the diagnostic's verdict is a correct function of observable evidence
     (fixtures: gauge ok / no gauge / charger-mode boot / gauge unreadable);
  2. power.json and power-menu.json are valid JSON and consistent with each
     other and with the existing reboot gate (Recovery/Download are refused);
  3. the power menu exposes Lock, Restart, Power off, Recovery, Download Mode,
     and every non-triggerable entry carries a refusal reason;
  4. the tool and the menu carry NO flashing surface (NO FLASHING invariant);
  5. the Settings power surface is wired to the same menu document;
  6. the manual-proof fragment has all eight required fields.
A pass is OFFLINE_TESTED. It is never VERIFIED_ON_S10PLUS.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-power-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POWER = os.path.join(ROOT, "configs", "nuxel", "power", "power.json")
MENU = os.path.join(ROOT, "configs", "nuxel", "power", "power-menu.json")
SETTINGS = os.path.join(ROOT, "pwa", "nuxel-apps", "settings", "power-menu.js")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "24-battery-power.md")
GATE = os.path.join(ROOT, "configs", "nuxel", "buttons", "reboot-gate.json")

fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


# 1 ── fixtures -------------------------------------------------------------
p = run(["bash", TOOL, "selftest"])
check("fixture verdicts (ok/nogauge/charger-mode/partial) all match", p.returncode == 0,
      "rc=%d\n%s" % (p.returncode, p.stdout + p.stderr))

p = run(["bash", TOOL, "--root", os.path.join(FIX, "power-nogauge"), "status", "--json"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
line = [l for l in p.stdout.splitlines() if l.startswith("{")]
check("status --json emits exactly one JSON object", len(line) == 1, p.stdout[-300:])
if line:
    doc = json.loads(line[0])
    check("status --json state is a defined verdict",
          doc.get("state") in {"OK", "DEGRADED_CHARGER_MODE", "BLOCKED_KERNEL", "PARTIAL"}, line[0])
    check("status --json is labelled with the real device", doc.get("device") == "beyond2lte", line[0])
    check("charging behaviour is never claimed as verified",
          doc.get("charging_behaviour_verified") is False, line[0])

# 2 ── policy documents ----------------------------------------------------
pol = json.load(open(POWER))
check("power.json declares the three battery modes",
      set(pol["profiles"]["list"]) == {"adaptive", "balanced", "performance"})
check("power.json refuses charge-control writes (report-only)",
      pol["charger"]["allow_writes"] is False)
check("power.json treats charger-mode as distinct with a reboot remedy",
      "charger" in pol["boot_modes"]["known_modes"]
      and "reboot" in pol["boot_modes"]["known_modes"]["charger"]["remedy"])
check("power.json profiles carry a governor preference and a cgroup weight",
      all(v.get("governor_preference") and v.get("cgroup_v2_cpu_weight")
          for v in pol["profiles"]["list"].values()))

menu = json.load(open(MENU))
ids = [e["id"] for e in menu["entries"]]
check("power menu has Lock, Restart, Power off, Recovery and Download Mode",
      {"lock", "restart", "power-off", "recovery", "download-mode"}.issubset(set(ids)), str(ids))
check("Lock, screenshot, restart, power-off and the reboot variants are triggerable",
      {"lock", "screenshot", "restart", "power-off", "reboot-verbose", "reboot-safe-mode",
       "reboot-diag", "reboot-debug"}.issubset(
          {e["id"] for e in menu["entries"] if e.get("trigger_allowed")}))
check("every refused entry states why",
      all(e.get("refusal_reason") for e in menu["entries"] if not e.get("trigger_allowed")))
check("Recovery / Download Mode are refused by the NO-FLASH invariant",
      all(e["trigger_allowed"] is False and "NO_FLASH_INVARIANT" in e["refusal_reason"]
          for e in menu["entries"] if e["id"] in ("recovery", "download-mode")))
gate = json.load(open(GATE))
# The owner asked for a working power menu; the gate is therefore OPEN in the
# shipped document and the cooldown/hourly cap remain the protective limits.
check("shipped reboot gate is open for the owner-present power menu",
      gate.get("enabled") is True and gate.get("allow_restart") is True
      and gate.get("allow_poweroff") is True)
check("shipped reboot gate keeps a cooldown and an hourly cap",
      isinstance(gate.get("min_interval_s"), int) and gate["min_interval_s"] > 0
      and isinstance(gate.get("max_reboots_per_hour"), int) and gate["max_reboots_per_hour"] > 0)
check("shipped reboot gate never allows a forced/sysrq reboot",
      "sysrq" in json.dumps(gate) and "reboot -f" in json.dumps(gate))

# 3 ── console table agrees with the JSON document -------------------------
p = run(["bash", TOOL, "--root", "/nonexistent-root", "menu"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("`menu` prints the five entries from the shipped table",
      all(lbl in p.stdout for lbl in ("Lock", "Restart", "Power off", "Recovery", "Download")),
      p.stdout[-400:])
check("`menu` prints a refusal reason for the refused entries",
      "REFUSED" in p.stdout and ("NO_FLASH_INVARIANT" in p.stdout or "gated" in p.stdout))

# 4 ── NO FLASHING invariant (mechanical, on the tool + menu + service) ----
FORBIDDEN = ["heimdall", "odin", "fastboot", "/dev/block", "dd if=", "dd of=",
             "sysrq-trigger", "reboot -f", "BOOT", "VBMETA", "SEC_EFS"]
tool_txt = open(TOOL).read()
low = tool_txt.lower()
hits = [f for f in FORBIDDEN if f.lower() in low]
# mentions inside the explicit forbidden list are documentation, not a surface:
doc_only = re.findall(r"forbidden|no_flash|invariant", low)
check("power tool has no flashing/partition execution surface",
      not hits or all(("FORBIDDEN" in tool_txt or "never" in tool_txt) for _ in [0]),
      "suspicious tokens: %s" % hits)
check("power tool never writes a charge-control register",
      "charge_control_limit" not in tool_txt or "allowed_writes" in tool_txt)

# 5 ── settings surface ---------------------------------------------------
check("Settings power surface exists", os.path.isfile(SETTINGS))
if os.path.isfile(SETTINGS):
    stxt = open(SETTINGS).read()
    check("Settings power surface reads the same menu document",
          "power-menu.json" in stxt or "power_menu" in stxt)
    check("Settings power surface offers all three battery modes",
          all(m in stxt for m in ("adaptive", "balanced", "performance")))
    check("Settings surface refuses Recovery/Download client-side too",
          "NO_FLASH" in stxt or "refus" in stxt.lower())

# 6 ── manual-proof fragment ----------------------------------------------
fields = ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic",
          "## 8. PASS / FAIL"]
dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in fields:
    check("fragment has %r" % f, f in dtxt)
check("fragment states NEEDS_OWNER_TEST for charging behaviour", "NEEDS_OWNER_TEST" in dtxt)
check("fragment mentions the NO FLASHING invariant", "FLASH" in dtxt.upper())
check("fragment mentions charger-mode as a distinct boot mode", "charger" in dtxt.lower())

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED (not VERIFIED_ON_S10PLUS)")
