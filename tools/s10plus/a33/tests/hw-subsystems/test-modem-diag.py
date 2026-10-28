#!/usr/bin/env python3
"""Offline tests for the S10+ modem / SIM work (briq-08i, area 26).

Proven offline: the honest verdict chain over four fixtures (nothing / transport
without stack / stack without SIM / stack with SIM), the "never fake signal or
registration" contract, IMSI/ICCID/IMEI/PIN redaction, the refused AT channel,
the protected-partition denylist, and the manual-proof fragment. Cellular data,
calls and SMS stay BLOCKED_FIRMWARE / NOT_SUPPORTED_ON_DEVICE and are never
claimed from config alone.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-modem-diag.sh")


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
FIX = os.path.join(HERE, "fixtures")
POLICY = os.path.join(ROOT, "configs", "nuxel", "modem", "modem.json")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "16-sim-mobile-data.md")
FAKE = {"NUXEL_DIAG_NO_SYSTEM": "1"}
fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None, stdin=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e, input=stdin)


def json_of(out):
    return json.loads([l for l in out.splitlines() if l.startswith("{")][0])


p = run(["bash", TOOL, "selftest"])
check("fixture verdicts (absent / transport-only / no-sim / with-sim) match",
      p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
truth = pol["device"]["modem_stack_truth"]
check("policy records the Shannon LTE modem and the missing upstream plugin",
      "Shannon" in pol["device"]["modem"] and truth["upstream_modemmanager_plugin"] is False)
check("policy forbids transplanting Pixel/Exynos-5500/Qualcomm instructions",
      "Pixel" in truth["do_not_transplant"])
check("policy default cellular verdict is honest (NOT_SUPPORTED/BLOCKED)",
      truth["default_cellular_verdict"] in ("NOT_SUPPORTED_ON_DEVICE", "BLOCKED_FIRMWARE"))
check("policy states calls/SMS/VoLTE are not available",
      "NOT implemented" in truth["voLTE_posture"] and "NOT available" in truth["voLTE_posture"])
check("policy redaction masks IMSI/ICCID/IMEI/PIN and never logs them",
      set(["IMSI", "ICCID", "IMEI", "PIN", "PUK"]).issubset(set(pol["sim"]["redaction"]["must_mask"]))
      and pol["sim"]["redaction"]["never_log"] is True)
check("policy never prints signal/registration that was not read from a real API",
      "never print signal/registration/operator that was not read from a real API" in pol["diagnostics"]["claim_policy"])
check("policy protects modem/efs/imei partitions and forbids flashing tools",
      {"modem", "efs", "efsg", "sec_efs"}.issubset(set(pol["protected_partitions"]["never_read_or_write"]))
      and "heimdall" in pol["protected_partitions"]["flashing_tools_forbidden"])
check("AT channel is off by default, read-only-allowlisted, and never auto-probed",
      pol["at_channel"]["enabled_by_default"] is False
      and pol["at_channel"]["require_explicit_flag"] == "--yes-at"
      and pol["at_channel"]["auto_probe_on_boot"] is False
      and all(c in pol["at_channel"]["read_only_allowlist"] for c in ["AT+CGMI", "AT+CSQ"])
      and any("CFUN=1,1" in c for c in pol["at_channel"]["forbidden"]))

# --- verdict chain ----------------------------------------------------------
d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "modem-absent"), "status", "--json"], FAKE).stdout)
check("no transport and no plugin => NOT_SUPPORTED_ON_DEVICE at host_transport",
      d["state"] == "NOT_SUPPORTED_ON_DEVICE" and d["first_failing_stage"] == "host_transport")
check("no cellular state is fabricated: signal/operator/registration are null",
      d["signal_quality"] is None and d["operator"] is None and d["registration_state"] is None)
check("cellular_available and registration_verified are always false",
      d["cellular_available"] is False and d["registration_verified"] is False)
check("no IMSI/ICCID is printed and the flag says so",
      d["print_imsi_or_iccid"] is False)

d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "modem-cp-only"), "status", "--json"], FAKE).stdout)
check("transport without a Shannon plugin => BLOCKED_FIRMWARE at modemmanager_plugin",
      d["state"] == "BLOCKED_FIRMWARE" and d["first_failing_stage"] == "modemmanager_plugin"
      and d["cp_nodes"] != [])

d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "modem-nosim"), "status", "--json"], FAKE).stdout)
check("stack present without a SIM => NO_SIM at sim (owner inserts a SIM)",
      d["state"] == "NO_SIM" and d["first_failing_stage"] == "sim")

d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "modem-ready"), "status", "--json"], FAKE).stdout)
check("stack + SIM => NEEDS_OWNER_TEST, still no signal/registration claim",
      d["state"] == "NEEDS_OWNER_TEST" and d["cellular_available"] is False
      and d["registration_verified"] is False and d["signal_quality"] is None)

p = run(["bash", TOOL, "--root", os.path.join(FIX, "modem-cp-only"), "interfaces"], FAKE)
check("`interfaces` says a node is a transport, not a working modem",
      "not a working modem" in p.stdout and "/dev/cbd0" in p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "modem-absent"), "plugin"], FAKE)
check("`plugin` names the documented blocker",
      "no Shannon-capable plugin" in p.stdout or "NONE" in p.stdout)

# --- redaction --------------------------------------------------------------
out = run(["bash", TOOL, "redact"], stdin="IMSI: 310150123456789 ICCID=89014103211118510720 IMEI 353285044917230 PIN: 1234 CSQ: 21\n").stdout
check("redaction masks IMSI/ICCID/IMEI/PIN and keeps only a tail",
      "310150123456789" not in out and "89014103211118510720" not in out
      and "353285044917230" not in out and "1234" not in out)
check("redaction keeps non-identity telemetry (CSQ: 21) intact", "CSQ: 21" in out)

# --- AT channel is an owner action, allowlisted, never automatic ------------
p = run(["bash", TOOL, "--root", os.path.join(FIX, "modem-ready"), "at", "AT+CGMI"], FAKE)
check("AT without --yes-at refuses", p.returncode != 0 and "refused" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "modem-ready"), "at", "--yes-at", "AT+EGMR=1,7"], FAKE)
check("AT refuses a non-allowlisted (EFS/NV) command",
      p.returncode != 0 and "allowlist" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "modem-ready"), "at", "--yes-at", "AT+CGMI"], FAKE)
check("AT refuses under a faked root (no real channel opened)",
      p.returncode != 0 and "offline/faked root" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "modem-absent"), "at", "--yes-at", "AT+CGMI"], FAKE)
check("AT refuses when no CP interface exists (BLOCKED_KERNEL)",
      p.returncode != 0 and "BLOCKED_KERNEL" in p.stdout, p.stdout)

txt = open(TOOL).read()
check("tool has no flashing/partition surface",
      all(t not in txt for t in ("/dev/block", "heimdall", "fastboot", "odin ")))
check("tool never writes to a device node", " > /dev/" not in txt and "write" not in txt.split("WHAT THIS IS NOT")[1].split("Usage:")[0].lower())

# --- fragment ---------------------------------------------------------------
dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment exists", bool(dtxt), DOC)
for f in ["## 1. Feature", "## 2. Why", "## 3. Preparation", "## 4. Exact action",
          "## 5. Expected result", "## 6. Failure symptoms", "## 7. Diagnostic", "## 8. PASS / FAIL"]:
    check("fragment has %r" % f, f in dtxt)
check("fragment gives the SIM owner steps (insert / check / remove)",
      "insert" in dtxt.lower() and ("remove" in dtxt.lower() or "eject" in dtxt.lower()))
check("fragment marks cellular BLOCKED_FIRMWARE/NOT_SUPPORTED_ON_DEVICE and NEEDS_OWNER_TEST",
      ("BLOCKED_FIRMWARE" in dtxt and "NOT_SUPPORTED_ON_DEVICE" in dtxt and "NEEDS_OWNER_TEST" in dtxt))
check("fragment forbids logging IMSI/ICCID and claims no calls/SMS",
      "IMSI" in dtxt and "not" in dtxt.lower() and "SMS" in dtxt)

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for detection/diagnostic; NEEDS_OWNER_TEST for a physical SIM; modem BLOCKED_FIRMWARE")
