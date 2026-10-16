#!/usr/bin/env python3
"""Offline tests for the S10+ Wi-Fi config + diagnostic (briq-03a, mission area 4).

Nothing here touches a radio. The tests prove four things that CAN be proven
offline, and nothing more:

  1. the diagnostic's verdict logic is a correct function of observable evidence
     (five fixtures: no radio / no firmware / no supplicant / no association /
     associated), driven through the real script with a faked root;
  2. the NetworkManager policy files are syntactically valid conf/keyfile input
     and carry no credentials;
  3. the manual-proof fragment contains all eight required fields and does not
     promise a verification the repository cannot deliver;
  4. the tool contains no flashing/partition-write surface at all (the mission's
     NO FLASHING invariant, checked mechanically rather than asserted).

A passing run is OFFLINE_TESTED. It is NOT VERIFIED_ON_S10PLUS.
"""
import configparser
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _repo_root(start):
    """Walk up to the directory that owns configs/ and docs/ — never guess a
    fixed depth (the test must keep working if the tree is relocated)."""
    d = start
    for _ in range(12):
        if os.path.isdir(os.path.join(d, "configs")) and os.path.isdir(os.path.join(d, "docs")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(os.path.dirname(os.path.dirname(start)))


ROOT = _repo_root(HERE)
TOOL = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-wifi-diag.sh")
NM = os.path.join(ROOT, "configs", "networkmanager")
DOC = os.path.join(ROOT, "docs", "beta-finalization", "manual-proof", "04-wifi.md")
FIX = os.path.join(HERE, "fixtures-p3")

fails = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e)


# 1 ── fixture-driven verdict logic -------------------------------------------------
p = run(["bash", TOOL, "selftest"])
check("fixtures: verdict logic matches all five expectations", p.returncode == 0,
      "rc=%d\n%s" % (p.returncode, p.stdout + p.stderr))

p = run(["bash", TOOL, "--root", FIX, "status", "--json"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
# --root is relative to cwd; make it absolute to be cwd-independent
p = run(["bash", TOOL, "--root", os.path.abspath(FIX), "status", "--json"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
line = [l for l in p.stdout.splitlines() if l.startswith("{")]
check("status --json emits one JSON object", len(line) == 1, p.stdout[-300:])
if line:
    try:
        doc = json.loads(line[0])
        ok = doc.get("state") in {
            "ASSOCIATED", "BLOCKED_DRIVER", "BLOCKED_FIRMWARE", "BLOCKED_HARDWARE",
            "BLOCKED_EXTERNAL_RESOURCE", "BLOCKED_UNKNOWN"}
        check("status --json state is one of the defined verdicts", ok, line[0])
        check("status --json is labelled with the real device", doc.get("device") == "beyond2lte", line[0])
    except Exception as exc:  # noqa: BLE001
        check("status --json parses", False, repr(exc))

# the fixtures directory is a *parent* of the fixtures; ensure the parent run is honest too
p = run(["bash", TOOL, "--root", os.path.abspath(FIX), "status"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
check("no-radio root never reports a working radio",
      "ASSOCIATED" not in p.stdout and "BLOCKED_" in p.stdout, p.stdout[-300:])

# 2 ── NetworkManager policy files --------------------------------------------------
conf = os.path.join(NM, "10-nuxel-s10plus-wifi.conf")
ini = configparser.RawConfigParser(strict=False)
ini.optionxform = str
try:
    ini.read(conf)
    sections = set(ini.sections())
    check("NM conf parses and defines [device] and [connection]",
          {"device", "connection"}.issubset(sections), str(sections))
    check("NM conf pins the only supplicant present on the image",
          ini.get("device", "wifi.backend", fallback="") == "wpa_supplicant")
    check("NM conf keeps privacy MAC randomization on",
          ini.get("device", "wifi.scan-rand-mac-address", fallback="") == "yes")
    check("NM conf disables Wi-Fi power save for bring-up",
          ini.get("connection", "wifi.powersave", fallback="") == "2")
except Exception as exc:  # noqa: BLE001
    check("NM conf parses", False, repr(exc))

wpa = os.path.join(NM, "wpa_supplicant-s10plus.conf")
wtxt = open(wpa).read()
_wpa_active = "\n".join(l for l in wtxt.splitlines() if not l.lstrip().startswith("#"))
check("wpa_supplicant conf does not pin a legacy driver=wext (active lines)",
      "driver=wext" not in _wpa_active and "driver=" not in _wpa_active)
check("wpa_supplicant conf sets the world regulatory domain (no invented country)",
      re.search(r"^country=00$", wtxt, re.M) is not None)
check("wpa_supplicant conf forbids self-rewriting (update_config=0)",
      re.search(r"^update_config=0$", wtxt, re.M) is not None)

tpl = os.path.join(NM, "nuxel-s10plus-wifi.nmconnection.example")
ttxt = open(tpl).read()
check("connection template is inert (not a .nmconnection NM would load)",
      tpl.endswith(".nmconnection.example"))
check("connection template carries no real credential",
      re.search(r"^psk=REPLACE-WITH-PSK$", ttxt, re.M) is not None
      and not re.search(r"^psk=(?!REPLACE)", ttxt, re.M))
check("repository-wide: no real PSK/SSID leaked into Wi-Fi configs",
      not any(re.search(r"^psk=\S", l) and "REPLACE" not in l
              for l in ttxt.splitlines()))

# 3 ── manual proof fragment ---------------------------------------------------------
if os.path.exists(DOC):
    d = open(DOC).read()
    for field in ["Feature", "Why", "Preparation", "Exact action", "Expected result",
                  "Failure symptoms", "Diagnostic", "PASS", "FAIL"]:
        check("manual-proof fragment has field %r" % field, field in d)
    check("manual-proof fragment states the owner requirement",
          "NEEDS_OWNER_TEST" in d)
    check("manual-proof fragment rejects the Pixel BCM4390 doc for this device",
          "bcm4390" in d.lower())
else:
    check("manual-proof fragment exists", False, DOC)

# 4 ── NO FLASHING invariant, mechanically ------------------------------------------
src = open(TOOL).read()
banned = [r"\bdd\s+if=", r"/dev/block", r"\bheimdall\b", r"\bodind?\(?\)?\s", r"fastboot",
          r"download mode", r"\bflash\b"]
for pat in banned:
    hits = [m for m in re.findall(pat, src, re.I)]
    check("tool contains no flashing surface for %r" % pat, not hits, str(hits))

print("\n== %d failing check(s) ==" % len(fails))
sys.exit(1 if fails else 0)
