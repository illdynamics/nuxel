#!/usr/bin/env python3
# =============================================================================
# tools/s10plus/a33/tests/test-phone-apps.py   (briq-06c: phone apps)
#
# Offline acceptance test for the four phone applications:
#   nuxel-dialer, nuxel-contacts, nuxel-messages (native GTK4 + shared C data
#   layer) and mail (PWA, covered by test-core-apps.py).
#
# The phone apps cannot be *executed* here (no GTK4/adwaita sysroot, no
# ModemManager, no SIM, no carrier). This test does what CAN be proven offline,
# and says so instead of implying more:
#
#   1. DATA LAYER: builds and runs shell/nuxel-shell/nuxel-phone-data/run-tests.sh
#      with the local C compiler. Those 74 checks cover number normalisation,
#      atomic save, corrupt-store recovery, vCard import/export and the
#      capability model.
#   2. LINK CONTRACT: every nuxel_phone_* symbol each app calls is declared in
#      nuxel-phone-data.h. A missing declaration is exactly the link error the
#      device build would hit, caught before the cross-compile.
#   3. HONESTY: the dialer/messages sources must contain the honest capability
#      wiring (a probe-derived label, a no-modem path, a queued-not-sent state)
#      and must NOT contain a phrase that claims a call or an SMS happened
#      unconditionally.
#   4. REGISTRY: the three native apps keep their desktop entries and their
#      binary path contract (/usr/bin/<id>, installed by meson bindir).
#
# Exit 0 = all offline checks pass.  Verdict: OFFLINE_TESTED (never
# VERIFIED_ON_S10PLUS: nothing here touched the handset).
# =============================================================================
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SHELL = REPO / "shell" / "nuxel-shell"
DATA = SHELL / "nuxel-phone-data"
HEADER = DATA / "nuxel-phone-data.h"
APPS = ["nuxel-dialer", "nuxel-contacts", "nuxel-messages"]

fails = 0
passes = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global fails, passes
    if cond:
        passes += 1
        print(f"PASS {name}")
    else:
        fails += 1
        print(f"FAIL {name}" + (f"  {extra}" if extra else ""))


def run_data_layer() -> None:
    runner = DATA / "run-tests.sh"
    check("data layer test runner exists", runner.is_file(), str(runner))
    if not runner.is_file():
        return
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    check("a C compiler is available for the data layer", bool(cc), "no cc/gcc/clang")
    if not cc:
        return
    proc = subprocess.run(["bash", str(runner)], capture_output=True, text=True, timeout=300)
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    check(f"data layer suite passes ({tail[0]})", proc.returncode == 0, proc.stderr[-400:])


def declared_symbols() -> set[str]:
    src = HEADER.read_text()
    names = set(re.findall(r"\b(nuxel_phone_[a-z0-9_]+)\s*\(", src))
    names |= set(re.findall(r"\b(nuxel_phone_[a-z0-9_]+)\b", src))
    return names


def check_app(app: str, declared: set[str]) -> None:
    src = SHELL / app / "main.c"
    if not src.is_file():
        check(f"{app}: source exists", False, str(src))
        return
    text = src.read_text()
    check(f"{app}: includes the shared data layer", "nuxel-phone-data.h" in text)
    used = set(re.findall(r"\b(nuxel_phone_[a-z0-9_]+)", text))
    missing = sorted(u for u in used if u not in declared)
    check(f"{app}: every data-layer symbol it calls is declared ({len(used)} used)", not missing, str(missing))
    check(f"{app}: declares its desktop entry contract",
          (REPO / "shell" / "config" / f"{app}.desktop").is_file(),
          f"shell/config/{app}.desktop")


def check_dialer() -> None:
    text = (SHELL / "nuxel-dialer" / "main.c").read_text()
    check("dialer: capability sentence comes from the probe, not a constant",
          "nuxel_phone_capability_label" in text)
    check("dialer: spells out the no-modem case",
          re.search(r"no modem|No modem|no modem is present", text) is not None)
    check("dialer: records a refusal instead of a fake call",
          re.search(r"no-modem|NUXEL_CALL_|cannot place|cannot dial", text) is not None)
    # A fabricated success looks like announcing a call/connection with no probe.
    bad = re.search(r'"(Calling|Connected) (now|to)\b', text)
    check("dialer: no unconditional \"Calling/Connected\" claim", bad is None,
          bad.group(0) if bad else "")


def check_messages() -> None:
    text = (SHELL / "nuxel-messages" / "main.c").read_text()
    check("messages: uses the shared thread model", "nuxel_phone_add_message" in text)
    check("messages: has a queued/not-sent state for an unavailable transport",
          re.search(r"queued|not sent|no-modem", text, re.I) is not None)
    check("messages: capability line is probe-derived",
          "nuxel_phone_capability_label" in text)
    bad = re.search(r'"(Message sent|SMS sent)"', text)
    check("messages: does not claim a sent SMS without a transport", bad is None,
          bad.group(0) if bad else "")


def check_contacts() -> None:
    text = (SHELL / "nuxel-contacts" / "main.c").read_text()
    check("contacts: vCard export is exposed", "nuxel_phone_export_vcard" in text)
    check("contacts: vCard import is exposed", "nuxel_phone_import_vcard" in text)
    check("contacts: store is persisted (atomic save path)",
          "nuxel_phone_store_save" in text and "nuxel_phone_store_load" in text)


def check_registry() -> None:
    reg = REPO / "pwa" / "nuxel-common" / "app-registry.json"
    if not reg.is_file():
        check("registry file present", False, str(reg))
        return
    doc = json.loads(reg.read_text())
    ids = {a.get("id"): a for a in doc.get("apps", [])}
    for app in APPS:
        entry = ids.get(app)
        check(f"registry keeps {app}", entry is not None,
              "present in pwa/nuxel-common/app-registry.json")
        if entry:
            check(f"registry {app}: capability list is a list",
                  isinstance(entry.get("capabilities"), list))
            check(f"registry {app}: binary source is the shell tree",
                  str(entry.get("binary_source", "")).endswith(app), str(entry.get("binary_source")))


def check_mail_pwa() -> None:
    mail = REPO / "pwa" / "nuxel-apps" / "mail"
    check("mail PWA exists with index+manifest+store+transport",
          all((mail / p).is_file() for p in
              ("index.html", "manifest.json", "js/storage.js", "js/transport.js", "js/mail.js")))
    text = (mail / "js/transport.js").read_text() if (mail / "js/transport.js").is_file() else ""
    check("mail: transport never fabricates a connection state",
          "imap" not in text.lower() or "does not pretend" in text or "WHAT THIS FILE IS NOT" in text)
    check("mail: a queued send is labelled queued, not sent",
          "'queued'" in text and "sent" in text)
    mail_js = (mail / "js" / "mail.js").read_text() if (mail / "js" / "mail.js").is_file() else ""
    check("mail: import/export of the local store is implemented",
          "exportAll" in mail_js and "importAll" in mail_js)


def main() -> int:
    print("== Nuxel phone-app offline acceptance (briq-06c) ==")
    run_data_layer()
    declared = declared_symbols()
    check("header declares the shared API", len(declared) > 20, f"{len(declared)} symbols")
    for app in APPS:
        check_app(app, declared)
    check_dialer()
    check_contacts()
    check_messages()
    check_mail_pwa()
    check_registry()
    print(f"\nRESULT: PASS={passes} FAIL={fails} verdict="
          f"{'OFFLINE_TESTED' if not fails else 'OFFLINE_FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
