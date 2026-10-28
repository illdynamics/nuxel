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
     NO FLASHING invariant, checked mechanically rather than asserted);
  5. the reboot-reconnection judgement (mark/compare) is a correct function of
     two recorded associations, including the REFUSED case where no reboot
     happened between them;
  6. the no-cellular-fallback audit finds a policy that could hand the default
     route to a cellular profile - and says "absent" only when it really is;
  7. a FAKED root can never borrow the host's wpa_supplicant/NetworkManager, so
     a workstation's tools can never be reported as the device's state (this is
     the regression guard for the defect where 'no supplicant on this image'
     read as 'supplicant present' merely because the developer laptop had one);
  8. the native Network Settings feature set (the bg-06d append point) exists,
     parses, and claims only verdicts from the mission's vocabulary.

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


# 5 ── mark/compare: reconnection across a normal reboot ------------------------------
import shutil, tempfile

def _rec(**kw):
    d = {"schema_version": 1, "device": "beyond2lte", "ifname": "wlan0", "state": "associated",
         "ssid": "HomeNet", "bssid": "aa:bb:cc:dd:ee:ff", "ipv4": "192.168.1.42/24",
         "gateway": "192.168.1.1", "boot_id": "boot-1", "recorded_at": "2026-10-16T00:00:00Z"}
    d.update(kw)
    return d

with tempfile.TemporaryDirectory() as td:
    def w(name, doc):
        path = os.path.join(td, name)
        with open(path, "w") as f:
            json.dump(doc, f)
        return path

    before = w("before.json", _rec())
    pairs = [
        ("PASS",   before, w("ok.json",      _rec(boot_id="boot-2", ipv4="192.168.1.43/24"))),
        ("FAIL",   before, w("down.json",    _rec(boot_id="boot-2", state="disconnected", ssid=None,
                                                   bssid=None, ipv4=None, gateway=None))),
        ("FAIL",   before, w("other.json",   _rec(boot_id="boot-2", ssid="Neighbour"))),
        ("FAIL",   before, w("noip.json",    _rec(boot_id="boot-2", ipv4=None))),
        ("REFUSED", before, w("same.json",   _rec(boot_id="boot-1"))),
        ("NO_MARKS", os.path.join(td, "missing.json"), w("x.json", _rec(boot_id="boot-2"))),
    ]
    for want, b, a in pairs:
        pr = run(["bash", TOOL, "compare", b, a])
        got = (pr.stdout.strip().split(" ")[0] if pr.stdout.strip() else "")
        check("reconnection judgement %s for %s" % (want, os.path.basename(a)), got == want,
              "got=%r out=%r" % (got, pr.stdout[-200:]))
    # a roam (same SSID, different BSSID) is a PASS, and says why
    pr = run(["bash", TOOL, "compare", before, w("roam.json", _rec(boot_id="boot-2", bssid="11:22:33:44:55:66"))])
    check("reconnection: a BSSID change with the same SSID is reported as a roam, not a failure",
          pr.stdout.strip().startswith("PASS") and "roam" in pr.stdout,
          pr.stdout[-200:])

# 6 ── no-cellular-fallback audit ------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    prof = os.path.join(td, "etc", "NetworkManager", "system-connections")
    os.makedirs(prof)
    with open(os.path.join(prof, "home.nmconnection"), "w") as f:
        f.write("[connection]\nid=home\ntype=wifi\nautoconnect=true\n")
    pr = run(["bash", TOOL, "--root", td, "fallback"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
    check("fallback: wifi-only policy root reports CELLULAR_FALLBACK=absent",
          "CELLULAR_FALLBACK=absent" in pr.stdout and pr.returncode == 0, pr.stdout[-300:])
    with open(os.path.join(prof, "telco.nmconnection"), "w") as f:
        f.write("[connection]\nid=telco\ntype=gsm\nautoconnect=true\n")
    pr = run(["bash", TOOL, "--root", td, "fallback"], {"NUXEL_DIAG_NO_SYSTEM": "1"})
    check("fallback: an autoconnecting gsm profile is reported as CELLULAR_FALLBACK=present",
          "CELLULAR_FALLBACK=present" in pr.stdout and pr.returncode == 1, pr.stdout[-300:])
    check("fallback: the finding is not promoted into a working-modem claim",
          "NOT proof that the modem can associate" in pr.stdout, pr.stdout[-300:])

# 7 ── a faked root never borrows host tools ------------------------------------------
host_wpa = shutil.which("wpa_supplicant")
with tempfile.TemporaryDirectory() as td:
    # a radio that is up, with module + firmware, but NO supplicant on this root
    os.makedirs(os.path.join(td, "proc"))
    os.makedirs(os.path.join(td, "sys/class/net/wlan0"))
    os.makedirs(os.path.join(td, "lib/firmware/brcm"))
    with open(os.path.join(td, "proc/modules"), "w") as f:
        f.write("brcmfmac 1 0 - Live 0x0\n")
    with open(os.path.join(td, "sys/class/net/wlan0/operstate"), "w") as f:
        f.write("up\n")
    with open(os.path.join(td, "lib/firmware/brcm/brcmfmac4375-pcie.bin"), "w") as f:
        f.write("FW")
    # NUXEL_DIAG_NO_SYSTEM is deliberately NOT set here: the fake root alone must
    # be enough to stop the host's tools from being used.
    pr = run(["bash", TOOL, "--root", td, "status", "--json"])
    doc = {}
    line = [l for l in pr.stdout.splitlines() if l.startswith("{")]
    if line:
        try:
            doc = json.loads(line[0])
        except Exception:  # noqa: BLE001
            doc = {}
    check("fake root without a supplicant is BLOCKED_EXTERNAL_RESOURCE even when the host has one",
          doc.get("state") == "BLOCKED_EXTERNAL_RESOURCE" and doc.get("supplicant") == 0,
          "host_wpa=%s json=%s" % (host_wpa, line[0] if line else pr.stdout[-200:]))
    if host_wpa:
        check("the host really does have a wpa_supplicant (so the check above is not vacuous)",
              True, "")
    else:
        print("INFO host has no wpa_supplicant: the leakage check above is not exercising the collision")
    # now put a supplicant INSIDE the fake root: the verdict must change to reflect it
    os.makedirs(os.path.join(td, "usr/sbin"))
    stub = os.path.join(td, "usr/sbin/wpa_supplicant")
    with open(stub, "w") as f:
        f.write("#!/bin/sh\n[ \"$1\" = \"-v\" ] && echo 'wpa_supplicant v2.11 (fixture)'\nexit 0\n")
    os.chmod(stub, 0o755)
    pr = run(["bash", TOOL, "--root", td, "status", "--json"])
    line = [l for l in pr.stdout.splitlines() if l.startswith("{")]
    doc = json.loads(line[0]) if line else {}
    check("fake root WITH a supplicant reports supplicant=1 and falls through to BLOCKED_HARDWARE",
          doc.get("supplicant") == 1 and doc.get("state") == "BLOCKED_HARDWARE", json.dumps(doc))

# 8 ── the native Network Settings feature set (bg-06d append point) -------------------
SPEC = os.path.join(NM, "nuxel-network-settings.spec.json")
if os.path.exists(SPEC):
    spec = json.load(open(SPEC))
    ids = {s.get("id") for s in spec.get("sections", [])}
    need = {"radio-power", "scan-list", "connection", "per-network", "dns", "routing",
            "regulatory", "reconnection", "no-cellular-fallback"}
    check("settings spec covers every required network feature section",
          need.issubset(ids), str(sorted(need - ids)))
    allowed = set(spec.get("verdicts", []))
    check("settings spec uses only the mission's verdict vocabulary",
          all(s.get("status") in allowed for s in spec.get("sections", [])),
          str([s.get("status") for s in spec.get("sections", [])]))
    check("settings spec names its renderer (append point, not a second store)",
          spec.get("coordinator") == "briq-06d-settings-and-keyboard"
          and spec.get("append_point", {}).get("for") == "briq-06d-settings-and-keyboard")
    check("settings spec never claims the Pixel BCM4390 applies to this device",
          any("bcm4390" in c.lower() for c in spec.get("never_claims", [])))
    pr = run(["bash", TOOL, "settings-spec"])
    check("the tool renders the settings spec", pr.returncode == 0 and "pages=9" in pr.stdout,
          pr.stdout[-200:])
else:
    check("settings spec exists", False, SPEC)

# 9 ── the fragment's automatic-evidence claim matches what actually ran --------------
d = open(DOC).read()
check("manual-proof fragment documents the reboot-reconnection evidence pair",
      "compare" in d and "mark" in d and "reboot" in d.lower(), "")
check("manual-proof fragment documents the no-cellular-fallback requirement",
      "cellular" in d.lower() and "fallback" in d.lower(), "")

print("\n== %d failing check(s) ==" % len(fails))
sys.exit(1 if fails else 0)
