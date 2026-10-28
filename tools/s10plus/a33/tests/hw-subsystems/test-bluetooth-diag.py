#!/usr/bin/env python3
"""Offline tests for the S10+ Bluetooth work (briq-08d, area 23).

Proven offline: per-stage evidence + verdict (four fixtures: absent / firmware
missing / rfkill blocked / ready-for-pairing), the BlueZ drop-in syntax and its
AutoEnable=false promise, the "no pairing from config" rule, the absence of any
flashing surface, and the manual-proof fragment. Pairing with a real peer stays
NEEDS_OWNER_TEST.
"""
import configparser
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-bluetooth-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "bluetooth", "bluetooth.json")
CONF = os.path.join(ROOT, "configs", "nuxel", "bluetooth", "main.conf.d", "60-nuxel.conf")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "11-bluetooth.md")
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
check("fixture verdicts (absent / nofw / blocked / ready) match", p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
check("policy names the real chip and HCD file",
      "BCM4375" in pol["device"]["chip"] and pol["device"]["hcd_filename"] == "bcm4375B1_semco.hcd")
check("policy orders the stages and defines the verdicts",
      pol["first_failing_stage_order"][0] == "adapter"
      and set(pol["verdicts"]) >= {"READY_FOR_PAIRING", "RFKILL_BLOCKED", "BLOCKED_FIRMWARE", "BLOCKED_HARDWARE"})
check("policy refuses auto-enable and requires a peer",
      pol["stack"]["auto_enable_adapter"] is False and pol["pairing_test"]["peer_required"] is True)

ini = configparser.RawConfigParser(strict=False)
ini.optionxform = str
ini.read(CONF)
sec = set(ini.sections())
check("BlueZ drop-in parses with [General] and [Policy]", {"General", "Policy"}.issubset(sec), str(sec))
check("drop-in pins AutoEnable = false (nothing powers the radio at boot)",
      ini.get("Policy", "AutoEnable", fallback="").lower() == "false")
check("drop-in keeps device privacy and no static address",
      ini.get("General", "Privacy", fallback="") == "device"
      and not any("address" in k.lower() for k in ini["General"]))
check("drop-in carries no credential/link key material",
      not any(k.lower() in ("key", "psk", "pin") for k in ini["General"]))

p = run(["bash", TOOL, "--root", os.path.join(FIX, "bluetooth-ready"), "status", "--json"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
doc = jdoc(p.stdout)
check("ready fixture: adapter/rfkill/firmware stages are the real ones",
      doc["stages"]["adapter"] == "present:hci0" and doc["stages"]["rfkill"].startswith("unblocked")
      and doc["stages"]["firmware"].startswith("found:"))
check("ready fixture still refuses to claim pairing",
      doc["state"] == "READY_FOR_PAIRING" and doc["pairing_verified"] is False
      and doc["first_failing_stage"] == "pairing")
p = run(["bash", TOOL, "--root", os.path.join(FIX, "bluetooth-nofw"), "status"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("no-firmware fixture names the firmware stage and says never-flash",
      "first failing stage : firmware" in p.stdout and "never a flash" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "bluetooth-absent"), "status"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("hardware-less fixture names the adapter stage and BLOCKED_HARDWARE",
      "first failing stage : adapter" in p.stdout and "BLOCKED_HARDWARE" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "bluetooth-blocked"), "status"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("rfkill-blocked fixture names the rfkill stage",
      "first failing stage : rfkill" in p.stdout and "RFKILL_BLOCKED" in p.stdout, p.stdout)

# owner-only actions under a faked root must not execute anything real
p = run(["bash", TOOL, "--root", os.path.join(FIX, "bluetooth-ready"), "scan", "99"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("scan is bounded by policy and reports the cap", "capping 99s to the policy maximum 60s" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "bluetooth-ready"), "on"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("on/off under a faked root never runs a real bluetoothctl",
      "offline/faked root" in p.stdout, p.stdout)

txt = open(TOOL).read()
check("tool has no flashing/partition surface",
      all(t not in txt for t in ("/dev/block", "heimdall", "fastboot")))

dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment names the first-failing-stage verdicts",
      "BLOCKED_FIRMWARE" in dtxt and "BLOCKED_HARDWARE" in dtxt and "RFKILL_BLOCKED" in dtxt)
check("fragment gives exact owner pairing steps (peer, scan, pair)",
      "peer" in dtxt.lower() and "scan" in dtxt.lower() and "pair" in dtxt.lower())
check("fragment marks pairing NEEDS_OWNER_TEST", "NEEDS_OWNER_TEST" in dtxt)

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for config + diagnostic; NEEDS_OWNER_TEST for pairing")
