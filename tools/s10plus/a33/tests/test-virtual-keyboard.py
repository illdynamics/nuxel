#!/usr/bin/env python3
# =============================================================================
# tools/s10plus/a33/tests/test-virtual-keyboard.py   (briq-06d, mission area 29)
#
# Offline acceptance test for "NATIVE VIRTUAL KEYBOARD".  It answers, with
# evidence, the only questions a workstation can answer about a keyboard that
# lives on a phone:
#
#   L1 DOCUMENT   the settings document exists, validates against its schema, and
#                 every keyboard setting the Settings model can write exists in it
#                 with the SAME default (no drift between UI, schema and applier).
#   L2 CONSUMER   the applier (the real consumer of that document) passes its own
#                 selftest against a fake root, including every degradation path
#                 (no provider, unparsable document, out-of-range value, dry-run)
#                 and proves it carries no flash/bootloader primitive.
#   L3 WIRING     the launcher host exposes the status channel the Settings probe
#                 needs (`keyboard-state` -> /run/nuxel-keyboard.state), the
#                 systemd units install that consumer, and the requirement list of
#                 mission area 29 is covered by the documents.
#   L4 LAST HOP   the probe page really executes in a DOM engine (jsdom): it builds
#                 its nodes, records deliveries, and — the honesty check that
#                 matters — labels a scripted delivery [synthetic] and refuses to
#                 reach verdict=PASS without a real (isTrusted) key event.
#
# The verdict this test can ever produce is OFFLINE_TESTED.  A green run is NOT
# proof that a keyboard appears on the S10+: that is the VM run of the probe page
# (VERIFIED_IN_VM_ONLY) and the owner's finger test (NEEDS_OWNER_TEST).
#
# Usage:
#   tools/s10plus/a33/tests/test-virtual-keyboard.py
#   NUXEL_JSDOM=/tmp/nuxel-smoke/node_modules tools/s10plus/a33/tests/test-virtual-keyboard.py
#   tools/s10plus/a33/tests/test-virtual-keyboard.py --json
# Exit 0 = all checks pass; 1 = at least one FAIL.
# =============================================================================
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
KBD_DIR = REPO / "configs" / "nuxel" / "keyboard"
DOC = KBD_DIR / "keyboard.json"
SCHEMA = KBD_DIR / "keyboard.schema.json"
README = KBD_DIR / "README.md"
SERVICE = KBD_DIR / "nuxel-keyboard-apply.service"
PATH_UNIT = KBD_DIR / "nuxel-keyboard-apply.path"
APPLIER = REPO / "tools" / "s10plus" / "a33" / "nuxel-keyboard-apply.sh"
PROBE = REPO / "tools" / "s10plus" / "a33" / "keyboard-probe.html"
MODEL = REPO / "pwa" / "nuxel-apps" / "settings" / "settings-model.js"
HOST_C = REPO / "tools" / "s10plus" / "a33" / "nuxel-pwa-host.c"

DOC_PATH = "/etc/nuxel/keyboard/keyboard.json"
STATE_PATH = "/run/nuxel-keyboard.state"

checks = 0
fails = 0
lines: list[str] = []


def ck(cond: bool, name: str, extra: str = "") -> bool:
    global checks, fails
    checks += 1
    if cond:
        lines.append(f"PASS {name}")
    else:
        fails += 1
        lines.append(f"FAIL {name}" + (f"  {extra}" if extra else ""))
    return bool(cond)


def warn(name: str) -> None:
    lines.append(f"WARN {name}")


# --------------------------------------------------------------------- L1 ----
def mini_validate(doc: dict, schema: dict) -> list[str]:
    """The subset of JSON Schema this project actually uses (no dependency)."""
    errs: list[str] = []
    props = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in doc:
            errs.append(f"required key '{key}' missing")
    for key, val in doc.items():
        spec = props.get(key)
        if spec is None:
            continue
        t = spec.get("type")
        if t == "object" and not isinstance(val, dict):
            errs.append(f"{key}: expected object")
            continue
        if t == "array":
            if not isinstance(val, list):
                errs.append(f"{key}: expected array")
            else:
                if isinstance(spec.get("minItems"), int) and len(val) < spec["minItems"]:
                    errs.append(f"{key}: fewer than minItems")
        if t == "boolean" and not isinstance(val, bool):
            errs.append(f"{key}: expected boolean, got {val!r}")
        if t == "integer" and (isinstance(val, bool) or not isinstance(val, int)):
            errs.append(f"{key}: expected integer, got {val!r}")
        if t == "number" and (isinstance(val, bool) or not isinstance(val, (int, float))):
            errs.append(f"{key}: expected number, got {val!r}")
        if t == "string" and not isinstance(val, str):
            errs.append(f"{key}: expected string, got {val!r}")
        if "const" in spec and val != spec["const"]:
            errs.append(f"{key}: must equal {spec['const']!r}, got {val!r}")
        if isinstance(val, int) and not isinstance(val, bool):
            if "minimum" in spec and val < spec["minimum"]:
                errs.append(f"{key}: {val} < minimum {spec['minimum']}")
            if "maximum" in spec and val > spec["maximum"]:
                errs.append(f"{key}: {val} > maximum {spec['maximum']}")
        if isinstance(val, str):
            if "minLength" in spec and len(val) < spec["minLength"]:
                errs.append(f"{key}: shorter than minLength")
            if "maxLength" in spec and len(val) > spec["maxLength"]:
                errs.append(f"{key}: longer than maxLength {spec['maxLength']}")
            if "pattern" in spec and not re.match(spec["pattern"], val):
                errs.append(f"{key}: {val!r} does not match {spec['pattern']}")
    return errs


def model_defaults() -> dict:
    """(key -> (default literal, kind)) for every keyboard.* setting in the model."""
    src = MODEL.read_text()
    block = re.search(r"// Input \(mission 29/30\)(.*?)\n\s*// System", src, re.S)
    if not block:
        return {}
    out = {}
    for m in re.finditer(
        r"'(keyboard\.[a-z_]+)':\s*\{\s*doc:\s*'([a-z\-]+)',\s*kind:\s*'([a-z]+)',\s*default:\s*([^,]+),",
        block.group(1),
    ):
        key, doc, kind, default = m.group(1), m.group(2), m.group(3), m.group(4).strip()
        if default in ("true", "false"):
            val: object = default == "true"
        elif default.isdigit() or (default.startswith("-") and default[1:].isdigit()):
            val = int(default)
        else:
            val = default.strip("'\"")
        out[key] = (val, kind, doc)
    return out


def layer_document(summary: dict) -> None:
    ck(DOC.is_file(), "the keyboard settings document exists", str(DOC))
    ck(SCHEMA.is_file(), "the keyboard document schema exists", str(SCHEMA))
    if not DOC.is_file() or not SCHEMA.is_file():
        return
    doc = json.loads(DOC.read_text())
    schema = json.loads(SCHEMA.read_text())
    errs = mini_validate(doc, schema)
    ck(not errs, "the shipped document validates against its schema", "; ".join(errs))
    ck(doc.get("schema_version") == 1, "the document pins schema_version 1")
    summary["document_keys"] = sorted(k for k in doc if k.startswith("keyboard."))

    defaults = model_defaults()
    ck(len(defaults) >= 8, "the Settings model declares the keyboard settings",
       f"found {len(defaults)}: {sorted(defaults)}")
    missing = sorted(k for k in defaults if k not in doc)
    ck(not missing, "every keyboard setting the Settings UI can write exists in the document",
       str(missing))
    drift = []
    for key, (val, kind, _doc) in defaults.items():
        if key in doc and doc[key] != val:
            drift.append(f"{key}: document={doc[key]!r} model-default={val!r}")
    ck(not drift, "the document defaults equal the Settings model defaults (no drift)", "; ".join(drift))

    # the document's own consumer + probe must agree with the files on disk
    ck("nuxel-keyboard-apply.sh" in str(doc.get("consumer", "")),
       "the document names its real consumer (nuxel-keyboard-apply.sh)",
       str(doc.get("consumer")))
    ck(doc.get("evidence", {}).get("state_file") == STATE_PATH,
       "the document names the evidence file the host probe reads", str(doc.get("evidence")))
    ck(APPLIER.is_file(), "the named consumer exists on disk", str(APPLIER))
    ck(os.access(APPLIER, os.X_OK), "the consumer is executable")

    # the Settings model must point at the same path and the same probe
    model_src = MODEL.read_text()
    ck(f"'{DOC_PATH}'" in model_src,
       "the Settings model reads/writes the same document path", DOC_PATH)
    ck("'keyboard-state'" in model_src,
       "the Settings model probes 'keyboard-state' (the host channel)")
    ck(README.is_file(), "the keyboard README (decision record) exists")
    summary["model_keys"] = sorted(defaults)


# --------------------------------------------------------------------- L2 ----
def layer_consumer(summary: dict, quick: bool) -> bool:
    if not APPLIER.is_file():
        ck(False, "the applier exists", str(APPLIER))
        return False
    proc = subprocess.run(["bash", str(APPLIER), "selftest"], capture_output=True, text=True, timeout=300)
    tail = [l for l in (proc.stdout or "").splitlines() if l.strip()]
    ck(proc.returncode == 0, "the applier selftest passes (all degradation paths)",
       (proc.stdout or "")[-600:] + (proc.stderr or "")[-300:])
    passed = re.search(r"(\d+)/(\d+) checks passed", proc.stdout or "")
    if passed:
        summary["applier_selftest"] = f"{passed.group(1)}/{passed.group(2)}"
    checks_text = "\n".join(tail)
    for need in ("not_applied:no-osk-installed", "provider-managed:", "delegated:haptics-component"):
        ck(need in checks_text, f"the selftest exercises the '{need}' verdict")
    ck("SELFTEST PASSED" in (proc.stdout or ""), "the applier reports SELFTEST PASSED")

    src = APPLIER.read_text()
    ck(STATE_PATH in src, "the applier writes the evidence file the host serves", STATE_PATH)
    ck("zwp_text_input_manager_v3" in src,
       "the applier records the Wayland text-input protocol it relies on")
    bad = re.search(r"he" + r"imdall|od" + r"in|fast" + r"boot|/dev/bl" + r"ock/", src)
    ck(bad is None, "the applier contains no flash/bootloader primitive", str(bad))
    if quick:
        warn("--quick: the consumer selftest still ran, additional wiring checks are unchanged")
    return True


# --------------------------------------------------------------------- L3 ----
def layer_wiring(summary: dict) -> None:
    if HOST_C.is_file():
        src = HOST_C.read_text()
        m = re.search(r'\{\s*"keyboard-state"\s*,\s*"([^"]+)"\s*,\s*(\d)\s*\}', src)
        ck(m is not None, "the launcher host exposes the 'keyboard-state' status channel")
        if m:
            ck(m.group(1) == STATE_PATH,
               "the host channel reads exactly the applier's evidence file", m.group(1))
            ck(m.group(2) == "0",
               "the host channel is read-only (writable=0): the page cannot forge it", m.group(2))
    else:
        ck(False, "the launcher host source exists", str(HOST_C))

    for unit, must in ((SERVICE, "/usr/libexec/nuxel/nuxel-keyboard-apply"),
                       (PATH_UNIT, DOC_PATH)):
        if not unit.is_file():
            ck(False, f"{unit.name} exists")
            continue
        text = unit.read_text()
        ck(must in text, f"{unit.name} references {must}")
    if SERVICE.is_file():
        ck("WantedBy" not in SERVICE.read_text() or "graphical-session" in SERVICE.read_text(),
           "the apply service is session-scoped (the OSK lives in the Wayland session)")

    # mission area 29's requirement list must be covered by the decision record
    reqs = {
        "appears on field focus": r"focus",
        "hides appropriately": r"hide|blur|auto_show",
        "input method in WebKitGTK": r"WebKitGTK",
        "numeric layout": r"numeric",
        "symbols": r"symbol|emoji",
        "shift / caps": r"capitali[sz]|shift",
        "backspace": r"backspace",
        "enter": r"enter",
        "space": r"space",
        "language/layout selection": r"layout|language",
        "clipboard": r"clipboard",
        "keyboard height": r"height",
        "key repeat": r"repeat",
        "haptics": r"haptic",
        "physical keyboard": r"physical",
        "Wayland text-input protocol": r"text-input|text_input",
        "no fake DOM-only keyboard": r"fake|last resort|fallback",
    }
    if README.is_file():
        text = README.read_text()
        missing = [name for name, pat in reqs.items() if not re.search(pat, text, re.I)]
        ck(not missing, "the decision record covers every mission-area-29 requirement",
           f"uncovered: {missing}")
        summary["area29_requirements"] = len(reqs)


# --------------------------------------------------------------------- L4 ----
JSDOM_HARNESS = r"""
const { JSDOM, VirtualConsole } = require(process.env.NUXEL_JSDOM_MODULE || 'jsdom');
const url = process.argv[2];
const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', (e) => errors.push('jsdomError: ' + (e && (e.message || e))));
vc.on('error', (...a) => errors.push('console.error: ' + a.map(String).join(' ')));
(async () => {
  const dom = await JSDOM.fromURL(url, {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(window) {
      window.alert = () => {}; window.scrollTo = () => {};
      window.matchMedia = window.matchMedia || function (q) {
        return { matches: false, media: q, addEventListener() {}, removeEventListener() {},
                 addListener() {}, removeListener() {}, onchange: null, dispatchEvent() { return false; } };
      };
    },
  });
  await new Promise((r) => setTimeout(r, 900));
  const w = dom.window, d = w.document;
  const probe = w.nuxelKeyboardProbe;
  const out = {
    url,
    hook: typeof probe !== 'undefined',
    ids: ['text', 'numeric', 'log', 'evidence', 'confirm-osk', 'copy', 'clear', 'reload-state']
      .filter((i) => !d.getElementById(i)),
    evidence_before: d.getElementById('evidence') ? d.getElementById('evidence').textContent : '',
    errors,
  };
  if (probe) {
    out.delivered = probe.deliver('ab', 'text');
    out.state_after_synthetic = probe.state();
    out.evidence_after = probe.evidence();
    out.log_has_synthetic = /\[synthetic\]/.test(d.getElementById('log').textContent);
    out.log_text = d.getElementById('log').textContent.slice(0, 2000);
    // the harness-only path: proves a machine-driven run can never be reported
    // as PASS, which is the property this page exists to guarantee.
    out.delivered_harness = probe.harnessTrusted('k', 'text');
    out.state_after_harness = probe.state();
    out.evidence_with_harness = probe.evidence();
    out.html_claims_verified = /VERIFIED_ON_S10PLUS|VERIFIED\b/.test(d.body.innerHTML);
  }
  console.log('__NUXEL_KBD__' + JSON.stringify(out));
  dom.window.close();
  process.exit(0);
})().catch((e) => {
  console.log('__NUXEL_KBD__' + JSON.stringify({ fatal: String(e && (e.stack || e)) }));
  process.exit(0);
});
"""


def start_server(root: Path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def log_message(self, *a):
            return

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def layer_last_hop(summary: dict) -> None:
    html = PROBE.read_text()
    ck("nuxelKeyboardProbe" in html, "the probe page exposes the smoke/operator hook")
    ck("[synthetic]" in html, "the probe page labels scripted deliveries as synthetic")
    ck("zwp_text_input_manager_v3" in html,
       "the probe page documents the protocol path it is the last hop of")
    ck(not re.search(r"https?://(?!127\.0\.0\.1)", html),
       "the probe page fetches no external asset (single self-contained file)")
    ck(not re.search(r"lorem ipsum|TODO", html, re.I), "the probe page contains no placeholder text")

    node = shutil.which("node")
    if not node:
        warn("node unavailable: the jsdom last-hop layer was skipped")
        summary["jsdom"] = "skipped (no node)"
        return
    modules = os.environ.get("NUXEL_JSDOM", "")
    if not modules or not Path(modules, "jsdom").is_dir():
        warn("jsdom not reachable (set NUXEL_JSDOM): the last-hop layer ran as a static check only")
        summary["jsdom"] = "skipped (no jsdom)"
        return
    harness = Path(tempfile.gettempdir()) / "nuxel-keyboard-probe-smoke.js"
    harness.write_text(JSDOM_HARNESS)
    srv, base = start_server(REPO)
    try:
        env = dict(os.environ, NUXEL_JSDOM_MODULE=str(Path(modules) / "jsdom"), NODE_PATH=str(modules))
        proc = subprocess.run([node, str(harness), f"{base}/tools/s10plus/a33/keyboard-probe.html"],
                              capture_output=True, text=True, env=env, timeout=120)
    finally:
        srv.shutdown()
    payload = None
    for line in proc.stdout.splitlines():
        if line.startswith("__NUXEL_KBD__"):
            payload = json.loads(line[len("__NUXEL_KBD__"):])
    if payload is None:
        ck(False, "the probe page executes in jsdom", proc.stderr[-400:])
        return
    if payload.get("fatal"):
        ck(False, "the probe page executes in jsdom", str(payload["fatal"])[:300])
        return
    summary["jsdom"] = "executed"
    ck(payload.get("hook") is True, "the probe page executes and exposes its hook")
    ck(not payload.get("ids"), "every probe node exists after script execution", str(payload.get("ids")))
    ck(not payload.get("errors"), "the probe page raises no console error", str(payload.get("errors")))
    ck(payload.get("delivered") == "ab", "a delivery reaches the text field", str(payload.get("delivered")))
    st = payload.get("state_after_synthetic") or {}
    ck(st.get("synthetic", 0) >= 2, "a scripted delivery is counted as synthetic", str(st))
    ck(st.get("trusted", 0) == 0, "a scripted delivery is never counted as a real key", str(st))
    ck(payload.get("log_has_synthetic") is True, "the log marks the scripted delivery [synthetic]")
    ev = payload.get("evidence_after", "")
    ck("verdict=SYNTHETIC_ONLY" in ev or "verdict=VOIDED_BY_SYNTHETIC" in ev,
       "evidence cannot reach PASS from scripted events alone", ev)
    ev2 = payload.get("evidence_with_harness", "")
    ck("verdict=VOIDED_BY_HARNESS" in ev2,
       "a harness-driven run is reported as VOIDED_BY_HARNESS and can never be PASS", ev2)
    sth = payload.get("state_after_harness") or {}
    ck(sth.get("harness", 0) >= 1, "harness deliveries are counted separately from real keys", str(sth))
    ck(payload.get("delivered_harness") == "abk",
       "the harness delivery reached the field through the real focus/input path",
       str(payload.get("delivered_harness")))
    ck(payload.get("html_claims_verified") is False,
       "the page never claims VERIFIED_ON_S10PLUS (that verdict needs the phone)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Nuxel virtual-keyboard offline acceptance (briq-06d)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quick", action="store_true", help="accepted for symmetry; all layers still run")
    args = ap.parse_args()

    summary: dict = {"layers": {}}
    layer_document(summary)
    layer_consumer(summary, args.quick)
    layer_wiring(summary)
    layer_last_hop(summary)

    print("== Nuxel virtual-keyboard offline acceptance (briq-06d / mission area 29) ==")
    print("\n".join(lines))
    verdict = "OFFLINE_FAILED" if fails else (
        "OFFLINE_TESTED" if summary.get("jsdom") == "executed" else "OFFLINE_STATIC_ONLY")
    print(f"\nRESULT: PASS={checks - fails} FAIL={fails} verdict={verdict}")
    summary["summary"] = {"pass": checks - fails, "fail": fails, "verdict": verdict}
    if args.json:
        print(json.dumps(summary, indent=2))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
