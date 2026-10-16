#!/usr/bin/env python3
"""Offline tests for the S10+ NFC work (briq-08e, area 24).

Proven offline: per-stage evidence + verdict (four fixtures: no controller /
no firmware / no userspace stack / ready-for-tag), the honest BLOCKED_KERNEL /
NOT_SUPPORTED_ON_DEVICE posture, no fabricated UID, faked-root safety and the
manual-proof fragment. A real tag read stays NEEDS_OWNER_TEST.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-nfc-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "nfc", "nfc.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "12-nfc.md")
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
check("fixture verdicts (absent / nofw / nostack / ready) match", p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
check("policy names the real controller and its I2C address",
      "S3FWRN5" in pol["device"]["controller"] and "0x27" in pol["device"]["controller"])
check("policy declares the stage order and the full verdict set",
      pol["first_failing_stage_order"] == ["controller", "firmware", "subsystem", "stack", "tag"]
      and set(pol["verdicts"]) >= {"READY_FOR_TAG", "BLOCKED_KERNEL", "BLOCKED_FIRMWARE",
                                   "BLOCKED_EXTERNAL_RESOURCE", "NOT_SUPPORTED_ON_DEVICE"})
check("policy never claims a tag from config alone (tag_required)",
      pol["tag_test"]["tag_required"] is True)

p = run(["bash", TOOL, "--root", os.path.join(FIX, "nfc-ready"), "status", "--json"],
        {"NUXEL_DIAG_NO_SYSTEM": "1"})
doc = jdoc(p.stdout)
check("ready fixture reports controller/firmware/subsystem/stack stages",
      doc["stages"]["controller"].startswith("module:") and doc["stages"]["firmware"].startswith("found:")
      and doc["stages"]["subsystem"].startswith("up:") and doc["stages"]["stack"].startswith("client:"))
check("ready fixture still refuses a tag claim",
      doc["state"] == "READY_FOR_TAG" and doc["tag_read_verified"] is False
      and doc["first_failing_stage"] == "tag")

p = run(["bash", TOOL, "--root", os.path.join(FIX, "nfc-absent"), "status"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("no-controller fixture is BLOCKED_KERNEL on the controller stage",
      "verdict             : BLOCKED_KERNEL" in p.stdout and "first failing stage : controller" in p.stdout, p.stdout)
check("no-controller fixture states that no UID is fabricated",
      "No UID is fabricated" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "nfc-nofw"), "status"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("no-firmware fixture names the firmware stage and says never-a-partition-write",
      "first failing stage : firmware" in p.stdout and "never a partition write" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "nfc-nostack"), "status"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("no-stack fixture is BLOCKED_EXTERNAL_RESOURCE on the stack stage",
      "first failing stage : stack" in p.stdout and "BLOCKED_EXTERNAL_RESOURCE" in p.stdout, p.stdout)

# no UID-like fabrication anywhere in tool or policy
ttxt = open(TOOL).read()
ptxt = open(POLICY).read()
check("no fabricated tag UID constant in the tool",
      not any(s in ttxt for s in ("04:A1:B2", "DE:AD:BE:EF", "00:00:00:00")))
check("the only UID in the policy is a labelled FORMAT example, not a read",
      "expected_uid_format" in ptxt and "(e.g." in ptxt)
check("tool has no flashing/partition surface",
      all(t not in open(TOOL).read() for t in ("/dev/block", "heimdall", "fastboot")))
p = run(["bash", TOOL, "--root", os.path.join(FIX, "nfc-ready"), "read", "5"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("bounded read under a faked root never runs a real client",
      "offline/faked root" in p.stdout, p.stdout)

dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment gives the exact owner tag steps (tap, UID, compare)",
      "tag" in dtxt.lower() and "UID" in dtxt)
check("fragment names BLOCKED_KERNEL / NOT_SUPPORTED_ON_DEVICE honestly",
      "BLOCKED_KERNEL" in dtxt and "NOT_SUPPORTED_ON_DEVICE" in dtxt)
check("fragment marks the tag read NEEDS_OWNER_TEST", "NEEDS_OWNER_TEST" in dtxt)

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for config + diagnostic; NEEDS_OWNER_TEST for a real tag")
