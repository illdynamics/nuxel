#!/usr/bin/env python3
"""Offline tests for the haptics WIRING (briq-08b, area 21).

Proven offline: the button-manager/notifier event -> pattern mapping, the
programmatic API gate (closed with no session, open when armed), the single
global off switch silencing every consumer, the rate limit, the "no buzz on
start" rule, and the honest integration statement in the README.

NOT provable offline: that any of it is FELT. Felt haptics stay
NEEDS_OWNER_TEST; a passing run never yields VERIFIED_ON_S10PLUS.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "nuxel-haptics-diag.sh")
BRIDGE = os.path.join(HERE, "..", "..", "nuxel-haptics-bridge.py")
FIX = os.path.join(HERE, "fixtures", "haptics-present")

fails = []


def repo_root(start):
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("repo root not found")


ROOT = repo_root(HERE)
HAP = os.path.join(ROOT, "configs", "nuxel", "haptics")
README = os.path.join(HAP, "README.md")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "10-vibration.md")


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, root=None, env=None):
    e = dict(os.environ); e.update(env or {})
    e["NUXEL_DIAG_NO_SYSTEM"] = "1"
    return subprocess.run(args, capture_output=True, text=True, env=e)


def fresh_root():
    td = tempfile.mkdtemp(prefix="nuxel-haptics-bridge-")
    for name in os.listdir(FIX):
        src = os.path.join(FIX, name)
        dst = os.path.join(td, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    return td


# ---- built-in bridge self-checks -------------------------------------------
p = run(["python3", BRIDGE, "--selftest"])
check("bridge selftest passes", p.returncode == 0 and "ALL HAPTICS BRIDGE OFFLINE CHECKS PASS" in p.stdout,
      p.stdout + p.stderr)
check("bridge selftest proves the switch-off silence", "global switch OFF silences notifications" in p.stdout)
check("bridge selftest proves no buzz on start", "no buzz on start" in p.stdout)
check("bridge selftest proves the rate limit", "rate limit engages on a burst" in p.stdout)
check("bridge selftest refuses a sysfs-write fifo line", "rejects a bogus fifo line" in p.stdout)

# ---- policy invariants -----------------------------------------------------
pol = json.load(open(os.path.join(HAP, "haptics.json")))
brg = json.load(open(os.path.join(HAP, "bridge.json")))
check("policy gates the programmatic API", "api" in pol and pol["api"]["gate_file"].startswith("/run/"))
check("policy forbids the API at boot", pol["api"]["never_at_boot"] is True)
check("policy rate-limits the API", pol["api"]["rate_limit"]["max_per_window"] >= 1)
check("bridge mapping covers the button manager actions",
      len(brg["consumers"]["buttons"]["action_patterns"]) >= 8)
check("bridge refuses feedback for the gated menu entries",
      "boot-download-mode" in brg["consumers"]["buttons"]["ignore_actions"]
      and "poweroff" in brg["consumers"]["buttons"]["ignore_actions"])
check("bridge consumes the real button-manager audit log",
      brg["consumers"]["buttons"]["log"] == "/var/log/nuxel/buttons.log")
check("bridge consumes the notification state file",
      brg["consumers"]["notifications"]["state_file"].endswith("notifications.json"))
check("bridge declares the single global switch and only reads it",
      brg["always_on_off_switch"]["read_only_for_bridge"] is True
      and brg["always_on_off_switch"]["path"].endswith("haptics/state.json"))
src = open(BRIDGE).read()
check("the bridge never writes sysfs itself (it asks the gated tool)",
      "/sys/class/leds" not in src and "os.open(path, os.O_WRONLY" not in src)
check("the bridge's only subprocess call is the gated haptics tool",
      src.count("subprocess.run(") == 1 and "cmd = [self.tool," in src)
dev_literals = re.findall(r'"(/dev/[^"]*)"', src)
check("the bridge never references a device node directly (only the gated tool owns the node)",
      all("/dev/block" not in d and "/dev/mmcblk" not in d for d in dev_literals),
      "dev literals: %s" % dev_literals)
check("the bridge contains no formatting/partitioning tool invocation",
      all(t not in src for t in ("mkfs", "fdisk", "parted", "wipefs")))

# ---- gate matrix ----------------------------------------------------------
root = fresh_root()
p = run(["bash", TOOL, "--root", root, "api", "tap", "--source", "buttons"])
check("api refuses while no session armed the gate (exit 7)",
      p.returncode == 7 and "gated OFF" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", root, "arm"])
check("arm creates the gate", "ARMED" in p.stdout)
p = run(["bash", TOOL, "--root", root, "api", "tap", "--source", "buttons"])
check("armed api accepts a pattern (dry-run under a faked root, no write)",
      p.returncode == 0 and "dry-run" in p.stdout, p.stdout)
p = run(["bash", TOOL, "--root", root, "api", "not-a-pattern", "--source", "buttons"])
check("armed api still refuses an unknown pattern (exit 2)", p.returncode == 2, p.stdout)
p = run(["bash", TOOL, "--root", root, "disarm"])
check("disarm closes the gate", "DISARMED" in p.stdout)
p = run(["bash", TOOL, "--root", root, "api", "tap", "--source", "buttons"])
check("api refuses again after disarm (exit 7)", p.returncode == 7, p.stdout)

# ---- one switch silences every consumer -----------------------------------
run(["bash", TOOL, "--root", root, "arm"])
run(["bash", TOOL, "--root", root, "off"])
p = run(["bash", TOOL, "--root", root, "api", "notify", "--source", "notifications"])
check("global switch OFF refuses the notifier path (exit 3)", p.returncode == 3, p.stdout)
b = run(["python3", BRIDGE, "--root", root, "--dry-run", "--once-event", "volume-up"])
check("bridge refuses a button event while the switch is OFF",
      "global haptics switch is OFF" in b.stdout, b.stdout)
run(["bash", TOOL, "--root", root, "on"])
b = run(["python3", BRIDGE, "--root", root, "--dry-run", "--once-event", "volume-up"])
check("bridge emits for a real button action once the switch is ON",
      "pattern=button" in b.stdout, b.stdout)
b = run(["python3", BRIDGE, "--root", root, "--dry-run", "--once-log",
         "2026-10-16T12:00:00Z FSM_ACTION source=key action=screen-lock"])
check("bridge maps a real audit line to the gesture pattern", "pattern=gesture" in b.stdout, b.stdout)
b = run(["python3", BRIDGE, "--root", root, "--dry-run", "--once-log",
         "2026-10-16T12:00:01Z FSM_ACTION source=key action=boot-download-mode"])
check("bridge emits nothing for a refused download-mode menu entry",
      "emit(" not in b.stdout and "no pattern mapped" in b.stdout, b.stdout)

# ---- rate limit through the real tool ------------------------------------
for i in range(8):
    last = run(["bash", TOOL, "--root", root, "api", "tap", "--source", "rate-check"])
check("the tool's API rate limit engages under a burst (exit 8)",
      last.returncode == 8 and "rate limit" in last.stdout, last.stdout)

# ---- honesty of the documentation ----------------------------------------
rd = open(README).read() if os.path.isfile(README) else ""
check("README documents both surfaces and the gate", "Programmatic" in rd and "api-enabled" in rd)
check("README states the button-manager change is NOT applied here",
      "not applied here" in rd and "owned by another in-flight build group" in rd)
check("README documents the FIFO protocol", "/run/nuxel-haptics.cmd" in rd)
dtxt = open(DOC).read() if os.path.isfile(DOC) else ""
check("manual-proof fragment documents the wiring", "bridge" in dtxt.lower())
check("manual-proof fragment keeps the felt half NEEDS_OWNER_TEST", "NEEDS_OWNER_TEST" in dtxt)

print()
if fails:
    print("%d CHECK(S) FAILED: %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("all checks PASS — OFFLINE_TESTED for the wiring/API/gates; NEEDS_OWNER_TEST for felt haptics")
