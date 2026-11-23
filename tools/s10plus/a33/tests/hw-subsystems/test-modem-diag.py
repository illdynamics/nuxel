#!/usr/bin/env python3
"""Offline tests for the S10+ modem / SIM work (briq-08i, area 26).

Proven offline:
  * the honest per-stage verdict chain
    (host_present -> cp_status -> firmware_candidate_verified -> cbd_available
    -> cp_boot_completed -> ipc_responsive -> rfs_responsive -> sim_ready ->
    registered -> bearer_connected -> rmnet_verified)
  * that a missing Shannon ModemManager plugin is NEVER the first blocker when
    the real first blocker is CP OFFLINE (or CP unknown)
  * that `mmcli -L` showing a modem is NOT a ready SIM, and a stale/mock SIM
    file is UNKNOWN rather than "present"
  * that a helper printing signal/operator still cannot leak into the JSON
  * the "never fake signal or registration" contract
  * IMSI/ICCID/IMEI/PIN redaction
  * the refused AT channel
  * the protected-partition denylist and BOOT-only TWRP scope
  * the read-only CP-status C probe's ABI assertions, ioctl encoding and
    absence of any mutating call

Cellular data, calls and SMS stay BLOCKED_FIRMWARE / NOT_SUPPORTED_ON_DEVICE
unless a real hardware observation moves the chain forward. A fixture is
evidence only — a PASS here is OFFLINE_TESTED, not physical success.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-modem-diag.sh")
CPPROBE = os.path.join(HERE, "..", "..", "cp-status", "nuxel-cp-status.c")


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

CHAIN = ["host_present", "cp_status", "firmware_candidate_verified", "cbd_available",
         "cp_boot_completed", "ipc_responsive", "rfs_responsive", "sim_ready",
         "registered", "bearer_connected", "rmnet_verified"]


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + str(detail)) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None, stdin=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e, input=stdin)


def json_of(out):
    return json.loads([l for l in out.splitlines() if l.startswith("{")][0])


def diag(fixture, *extra):
    return json_of(run(["bash", TOOL, "--root", os.path.join(FIX, fixture), "status", "--json"],
                       FAKE, *extra).stdout)


def expect(fixture, **want):
    d = diag(fixture)
    miss = {k: (v, d.get(k)) for k, v in want.items() if d.get(k) != v}
    return d, miss


# ---- selftest + policy --------------------------------------------------===
p = run(["bash", TOOL, "selftest"])
check("fixture verdicts (state= lines) match", p.returncode == 0, p.stdout + p.stderr)

pol = json.load(open(POLICY))
truth = pol["device"]["modem_stack_truth"]
check("policy records the Shannon LTE modem and the missing upstream plugin",
      "Shannon" in pol["device"]["modem"] and truth["upstream_modemmanager_plugin"] is False)
check("generic Samsung ModemManager plugins never satisfy the Shannon backend gate",
      "*samsung*" not in pol["modemmanager"]["plugin_globs"])
check("policy forbids transplanting Pixel/Exynos-5500/Qualcomm instructions",
      "Pixel" in truth["do_not_transplant"])
check("policy default cellular verdict is honest (NOT_SUPPORTED/BLOCKED)",
      truth["default_cellular_verdict"] in ("NOT_SUPPORTED_ON_DEVICE", "BLOCKED_FIRMWARE"))
check("policy states calls/SMS/VoLTE are not available",
      "NOT implemented" in truth["voLTE_posture"] and "NOT available" in truth["voLTE_posture"])
check("policy names cp_status (CP OFFLINE) as the first real blocker, not the plugin",
      "first real blocker is cp_status" in pol["comment"]
      and "later hop" in pol["comment"].lower())
check("policy protects modem/radio/efs/radiobak and forbids flashing tools",
      {"modem", "radio", "radiobak", "efs", "efsg", "sec_efs", "dtbo"}.issubset(
          set(pol["protected_partitions"]["never_read_or_write"]))
      and "heimdall" in pol["protected_partitions"]["flashing_tools_forbidden"])
check("policy documents the BOOT-only TWRP repair scope without weakening the denylist",
      "BOOT/OS repair" in pol["protected_partitions"]["comment"]
      and "does NOT authorize" in pol["protected_partitions"]["comment"])
check("policy names calliope_* as ABOX/audio and forbids using them as CP firmware",
      set(["calliope_sram.bin", "calliope_dram.bin"]).issubset(
          set(pol["firmware"]["must_not_use_as_cp_firmware"]))
      and "ABOX" in pol["firmware"]["must_not_use_reason"])
check("policy declares a single read-only CP-status ioctl source for cp_status",
      pol["cp_status"]["device_node"] == "/dev/umts_boot0"
      and pol["cp_status"]["ioctl"] == "0x6f27")
sim_pol = pol["sim"]
check("policy redaction masks IMSI/ICCID/IMEI/PIN and never logs them",
      set(["IMSI", "ICCID", "IMEI", "PIN", "PUK"]).issubset(set(sim_pol["redaction"]["must_mask"]))
      and sim_pol["redaction"]["never_log"] is True)
check("policy bounds SIM state-file freshness (max_age_s > 0)",
      isinstance(sim_pol.get("state_file_max_age_s"), int) and sim_pol["state_file_max_age_s"] > 0)
check("policy says a listed modem is NOT a ready SIM",
      "NOT a ready SIM" in sim_pol["comment"])
check("policy never prints signal/registration that was not read from a real API",
      "never print signal/registration/operator that was not read from a real API" in pol["diagnostics"]["claim_policy"])
check("AT channel is off by default, read-only-allowlisted, and never auto-probed",
      pol["at_channel"]["enabled_by_default"] is False
      and pol["at_channel"]["require_explicit_flag"] == "--yes-at"
      and pol["at_channel"]["auto_probe_on_boot"] is False
      and all(c in pol["at_channel"]["read_only_allowlist"] for c in ["AT+CGMI", "AT+CSQ"])
      and any("CFUN=1,1" in c for c in pol["at_channel"]["forbidden"]))

# ---- the new state machine: each fixture ----------------------------------
d = json_of(run(["bash", TOOL, "--root", os.path.join(FIX, "modem-absent"), "status", "--json"], FAKE).stdout)
check("no transport and no plugin => NOT_SUPPORTED_ON_DEVICE at host_present",
      d["state"] == "NOT_SUPPORTED_ON_DEVICE" and d["first_failing_stage"] == "host_present")
check("no cellular state is fabricated: signal/operator/registration are null",
      d["signal_quality"] is None and d["operator"] is None and d["registration_state"] is None)
check("cellular_available and registration_verified are always false (absent)",
      d["cellular_available"] is False and d["registration_verified"] is False)
check("JSON exposes every chain stage even when not observed",
      all(k in d for k in CHAIN))

d, miss = expect("modem-cp-offline",
                 state="BLOCKED_FIRMWARE", first_failing_stage="cp_status",
                 cp_status="OFFLINE", cp_boot_completed="no", ipc_responsive="unknown",
                 registered="unknown", bearer_connected="unknown", rmnet_verified="unknown",
                 signal_quality=None, operator=None, registration_state=None,
                 cellular_available=False, registration_verified=False)
check("CP OFFLINE => BLOCKED_FIRMWARE at cp_status, not at modemmanager_plugin",
      not miss, miss)
check("CP OFFLINE never produces a SIM-ready, registered or bearer claim", not miss)

d, miss = expect("modem-cp-booting",
                 state="BLOCKED_FIRMWARE", first_failing_stage="cp_boot_completed",
                 cp_status="BOOTING", cp_boot_completed="no", ipc_responsive="unknown")
check("CP BOOTING must not advance cp_boot_completed nor claim ONLINE", not miss, miss)

d, miss = expect("modem-cp-online-noipc",
                 state="BLOCKED_FIRMWARE", first_failing_stage="firmware_candidate_verified",
                 cp_status="ONLINE", cp_boot_completed="yes", ipc_responsive="unknown")
check("CP ONLINE still requires hash-verified firmware (never inferred)", not miss, miss)

d, miss = expect("modem-cp-only",
                 state="NEEDS_CP_PROBE", first_failing_stage="ipc_responsive",
                 cp_status="ONLINE", firmware_candidate_verified="yes",
                 cbd_available="present", ipc_responsive="unknown")
check("CP ONLINE + firmware + cbd => first failure is ipc_responsive, never the plugin", not miss, miss)

d, miss = expect("modem-sim-unknown",
                 state="BLOCKED_FIRMWARE", first_failing_stage="cp_status",
                 cp_status="OFFLINE", sim_ready="unknown", sim_source="state_file-stale")
check("stale SIM file + CP OFFLINE => sim_ready unknown (never present, never NO_SIM)", not miss, miss)

d, miss = expect("modem-no-bearer",
                 first_failing_stage="cp_status",
                 bearer_connected="unknown", rmnet_verified="unknown")
check("rmnet netdev existence is a transport, never a bearer", not miss, miss)

d, miss = expect("modem-mm-modem-no-sim",
                 sim_ready="unknown", signal_quality=None, operator=None, registration_state=None)
check("mmcli -L listing a modem does NOT make sim_ready yes (real SIM object required)",
      not miss, miss)

d, miss = expect("modem-fake-signal",
                 sim_ready="unknown", signal_quality=None, operator=None,
                 registration_state=None, cellular_available=False, registration_verified=False)
check("a helper printing signal/operator cannot leak into the JSON",
      not miss, miss)

d, miss = expect("modem-nosim",
                 state="NEEDS_CP_PROBE", first_failing_stage="ipc_responsive",
                 sim_ready="no", sim_source="state_file")
check("a real `present:false` SIM file is exposed as NO-SIM readiness, not hidden", not miss, miss)

d, miss = expect("modem-ready",
                 state="NEEDS_CP_PROBE", first_failing_stage="ipc_responsive",
                 sim_ready="yes", registered="unknown",
                 cellular_available=False, registration_verified=False,
                 signal_quality=None)
check("even SIM-ready must NOT claim registered / signal / cellular_available",
      not miss, miss)

# ---- MM plugin is never the first branch ---------------------------------
for fixture in ("modem-cp-offline", "modem-cp-booting", "modem-cp-only", "modem-nosim", "modem-ready"):
    d = diag(fixture)
    check("%s does not pick modemmanager_plugin as first failing stage" % fixture,
          d["first_failing_stage"] != "modemmanager_plugin", d["first_failing_stage"])

# ---- negative controls that MUST fail the old, broken priority ----------
d = diag("modem-cp-offline")
check("NEGATIVE CONTROL: state=BLOCKED_FIRMWARE + ff=modemmanager_plugin would be wrong here",
      not (d["state"] == "BLOCKED_FIRMWARE" and d["first_failing_stage"] == "modemmanager_plugin"),
      d["first_failing_stage"])
d = diag("modem-sim-unknown")
check("NEGATIVE CONTROL: sim present from a stale file would be a false positive",
      d["sim_ready"] != "yes", d["sim_ready"])
d = diag("modem-mm-modem-no-sim")
check("NEGATIVE CONTROL: sim present from `mmcli -L` would be a false positive",
      d["sim_ready"] != "yes", d["sim_ready"])
d = diag("modem-fake-signal")
check("NEGATIVE CONTROL: any signal/operator/registration would be invented",
      d["signal_quality"] is None and d["operator"] is None and d["registration_state"] is None)

# ---- a fake probe under a LIVE root must never be trusted ----------------
with tempfile.TemporaryDirectory() as td:
    os.makedirs(os.path.join(td, "dev"))
    open(os.path.join(td, "dev", "umts_boot0"), "w").close()
    os.makedirs(os.path.join(td, "usr/local/bin"))
    p_ = os.path.join(td, "usr/local/bin/nuxel-cp-status")
    open(p_, "w").write('#!/bin/sh\necho \'{"state":"ONLINE"}\'\n'); os.chmod(p_, 0o755)
    d = json_of(run(["bash", TOOL, "--root", td, "status", "--json"], FAKE).stdout)
    check("fixture probe under a faked root is labelled as a fixture, not hardware",
          d["cp_status_source"].startswith("offline-fixture"), d["cp_status_source"])
    check("a faked root never claims a real ONLINE from the fixture probe",
          d["cp_status"] in ("ONLINE", "unknown"))
    # And the tool refuses to fall back to the live device even with a faked root.
    check("faked root does not invoke a live /dev node",
          d["cp_status_source"].startswith("offline-fixture"))

# ---- interface enumeration still works under an alternate root -----------
with tempfile.TemporaryDirectory() as td:
    os.makedirs(os.path.join(td, "dev"))
    open(os.path.join(td, "dev", "umts_boot0"), "w").close()
    open(os.path.join(td, "dev", "umts_ipc0"), "w").close()
    os.makedirs(os.path.join(td, "sys", "class", "net", "rmnet7"))
    d = json_of(run(["bash", TOOL, "--root", td, "status", "--json"], FAKE).stdout)
    check("globbed umts/rmnet paths enumerate under an alternate root",
          d["cp_nodes"] == ["/dev/umts_boot0", "/dev/umts_ipc0"]
          and d["net_interfaces"] == ["rmnet7"])

p = run(["bash", TOOL, "status", "--json"], {"NUXEL_MODEM_POLICY": POLICY, **FAKE})
check("live-root path expansion never produces a double-slash probe error",
      p.returncode == 0 and "grep: //" not in p.stderr)

p = run(["bash", TOOL, "--root", os.path.join(FIX, "modem-cp-only"), "interfaces"], FAKE)
check("`interfaces` says a node is a transport, not a working modem",
      "not a working modem" in p.stdout and "/dev/cbd0" in p.stdout)
p = run(["bash", TOOL, "--root", os.path.join(FIX, "modem-cp-offline"), "plugin"], FAKE)
check("`plugin` names CP status as the first blocker, not the plugin",
      "first blocker" in p.stdout, p.stdout)

# ---- redaction -----------------------------------------------------------
out = run(["bash", TOOL, "redact"], stdin="IMSI: 310150123456789 ICCID=89014103211118510720 IMEI 353285044917230 PIN: 1234 CSQ: 21\n").stdout
check("redaction masks IMSI/ICCID/IMEI/PIN and keeps only a tail",
      "310150123456789" not in out and "89014103211118510720" not in out
      and "353285044917230" not in out and "1234" not in out)
check("redaction keeps non-identity telemetry (CSQ: 21) intact", "CSQ: 21" in out)

# ---- AT channel is an owner action, allowlisted, never automatic ----------
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
check("tool never writes to a device node",
      " > /dev/" not in txt and "O_RDWR" not in txt and " write(" not in txt)

# ---- source-level assertion for the read-only CP status probe -----------
if os.path.isfile(CPPROBE):
    c = open(CPPROBE).read()
    check("CP probe pins the exact ioctl value (_IO('o',0x27) == 0x6f27)",
          "_IO('o', 0x27)" in c and "0x6f27" in c)
    check("CP probe pins enum modem_state ordering (ONLINE==4, CRASH_WATCHDOG==9)",
          "STATE_ONLINE == 4" in c and "STATE_CRASH_WATCHDOG == 9" in c)
    check("CP probe opens the node O_RDONLY",
          "O_RDONLY" in c and "O_RDWR" not in c)
    for forbidden in ("O_WRONLY", "IOCTL_MODEM_ON", "IOCTL_MODEM_OFF", "IOCTL_MODEM_RESET",
                      "IOCTL_MODEM_BOOT_ON", "IOCTL_MODEM_DOWNLOAD", "IOCTL_MODEM_XMIT_BOOT",
                      "write(fd", "/dev/block", "efs", "mmap("):
        check("CP probe never uses %r" % forbidden, forbidden not in c)
    check("CP probe's only ioctl is IOCTL_MODEM_STATUS",
          re.findall(r"\bioctl\s*\(\s*fd\s*,", c) == ["ioctl(fd, "] or c.count("ioctl(fd, NUXEL_IOCTL_MODEM_STATUS)") == 1)
else:
    check("CP probe source exists", False, CPPROBE)

# ---- fragment ------------------------------------------------------------
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
print("all checks PASS — OFFLINE_TESTED for the state machine/probe; physical SIM, CP boot, "
      "data, SMS and voice remain NEEDS_OWNER_TEST / BLOCKED")
