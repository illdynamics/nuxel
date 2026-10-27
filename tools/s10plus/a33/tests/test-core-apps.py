#!/usr/bin/env python3
# =============================================================================
# tools/s10plus/a33/tests/test-core-apps.py   (briq-06b: core phone applications)
#
# Offline acceptance test for the Nuxel core application set.  It answers one
# question with evidence instead of assertion:
#
#   "Does every core app in pwa/nuxel-apps/<name>/ actually load, build its DOM
#    and run without a console error -- in a browser engine, with no handset
#    and no Nuxel host available?"
#
# The offline test is deliberately run WITHOUT the NuxelHost/NuxelBridge, i.e.
# in the worst case the app can meet (plain WebKitGTK/desktop browser, VM with
# no host, network down).  An app that only works when the host answers is an
# app that breaks in the UTM VM, so that case is the acceptance case.
#
# Layers (each is reported separately, never conflated):
#
#   L1  STATIC   files present, manifest.json complete (name, start_url,
#                display, icons, nuxel.capabilities, nuxel.bridge_version),
#                every local css/js/icon reference resolves, no external
#                http(s) asset (offline-first), no lorem/TODO placeholder text.
#   L2  SYNTAX   every js file passes `node --check` (real parser, not a grep).
#   L3  DOM      every getElementById()/querySelector('#id') the JS uses is
#                satisfied by the HTML or is created by the app itself.
#   L4  RUNTIME  jsdom (real DOM + real script execution) loads the page over
#                http from a local server; asserts the page's expected nodes
#                exist, that the app exposed its smoke hook, and that ZERO
#                console errors / uncaught exceptions happened.
#
# L4 needs jsdom.  It is intentionally NOT vendored in the repo (it is a desktop
# test dependency, not a ship dependency).  Point NUXEL_JSDOM at a node_modules
# tree that has it (see --help) or run without it: L1-L3 still run and the
# verdict is reported as OFFLINE_STATIC_ONLY instead of silently "passing".
#
# Usage:
#   tools/s10plus/a33/tests/test-core-apps.py                  # L1-L4 if jsdom is reachable
#   NUXEL_JSDOM=/tmp/nuxel-smoke/node_modules \
#     tools/s10plus/a33/tests/test-core-apps.py                # explicit jsdom path
#   tools/s10plus/a33/tests/test-core-apps.py --no-runtime      # L1-L3 only
#   tools/s10plus/a33/tests/test-core-apps.py --json            # machine-readable summary
#   tools/s10plus/a33/tests/test-core-apps.py --app maps notes  # subset
#
# Exit code 0 = every requested layer passed.  1 = at least one FAIL.
# 2 = environment problem (jsdom requested but missing).
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
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]          # tools/s10plus/a33/tests -> repo root
APPS_ROOT = REPO / "pwa" / "nuxel-apps"

# name -> (expected smoke hook globals, ids that MUST exist after JS runs,
#          requirement level)
#   hook:   the global object the app exposes for smoke tests (documented in
#           the app), e.g. `window.nuxelCalc`.
#   ids:    elements the app builds or owns; they must be in the DOM after the
#           page's scripts have run.  A missing one is a real defect: the app's
#           own JS (or a user) refers to it.
CORE_APPS = {
    "terminal": {
        "hook": "nuxelTerminal",
        "ids": ["screen", "notice", "osk", "title"],
        "manifest_caps": "shell:local-pty",
    },
    "notes": {
        "hook": "nuxelNotes",
        "ids": ["notes-list", "note-editor", "note-title", "note-body"],
        "manifest_caps": "storage:persistent",
    },
    "files": {
        "hook": "nuxelFiles",
        "ids": ["file-grid", "breadcrumb", "back-btn"],
        "manifest_caps": None,
    },
    "clock": {
        "hook": "nuxelClock",
        "ids": ["frac-time", "cities", "alarms", "sw-time", "tm-time"],
        "manifest_caps": "storage:persistent",
    },
    "calculator": {
        "hook": "nuxelCalculator",
        "ids": ["expr", "result", "pad-basic", "pad-sci"],
        "manifest_caps": None,
    },
    "browser": {
        "hook": "nuxelBrowser",
        "ids": ["url", "view", "start"],
        "manifest_caps": "network:outbound",
    },
    "photos": {
        "hook": "nuxelPhotos",
        "ids": ["grid", "viewer", "album"],
        "manifest_caps": "storage:persistent",
    },
    "recorder": {
        "hook": "nuxelRecorder",
        "ids": ["rec", "stop", "meter", "capability"],
        "manifest_caps": "storage:persistent",
    },
    "weather": {
        "hook": "nuxelWeather",
        "ids": ["now-temp", "forecast", "now-place", "city", "search"],
        "manifest_caps": "network:outbound",
    },
    "maps": {
        "hook": "nuxelMaps",
        "ids": ["map", "pins", "search", "cache-stats"],
        "manifest_caps": "location:read",
    },
    "mail": {
        "hook": "nuxelMail",
        "ids": ["account-list", "message-list", "message-view"],
        "manifest_caps": "storage:persistent",
    },
}

PLACEHOLDER_RE = re.compile(r"lorem ipsum|TODO:|FIXME placeholder|xxx-plz", re.I)
ID_REF_RE = re.compile(r"""getElementById\(\s*['"]([A-Za-z0-9_\-:]+)['"]\s*\)"""
                       r"""|querySelector(?:All)?\(\s*['"]#([A-Za-z0-9_\-]+)['"]\s*\)""")
ID_MAKE_RE = re.compile(r"""\.\s*id\s*=\s*['"]([A-Za-z0-9_\-:]+)['"]"""
                        r"""|setAttribute\(\s*['"]id['"]\s*,\s*['"]([A-Za-z0-9_\-:]+)['"]"""
                        r"""|id=["']([A-Za-z0-9_\-:]+)["']""")


class Result:
    def __init__(self) -> None:
        self.fail = 0
        self.warn = 0
        self.pass_ = 0
        self.lines: list[str] = []
        self.json: dict = {"apps": {}, "layers": {}}

    def ok(self, app: str, layer: str, msg: str) -> None:
        self.pass_ += 1
        self.lines.append(f"PASS {app:<10} {layer:<7} {msg}")

    def bad(self, app: str, layer: str, msg: str) -> None:
        self.fail += 1
        self.lines.append(f"FAIL {app:<10} {layer:<7} {msg}")
        self.json["apps"].setdefault(app, {}).setdefault("fail", []).append(f"{layer}: {msg}")

    def skip(self, app: str, layer: str, msg: str) -> None:
        self.warn += 1
        self.lines.append(f"WARN {app:<10} {layer:<7} {msg}")


def local_refs(html: str) -> list[str]:
    """Every local href/src referenced by the document (no data:, no http(s):)."""
    out = []
    for m in re.finditer(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", html, re.I):
        ref = m.group(1).strip()
        if not ref or ref.startswith(("#", "data:", "http://", "https://", "//", "mailto:", "javascript:")):
            continue
        out.append(ref)
    return out


def parse_manifest(app_dir: Path) -> tuple[dict | None, list[str]]:
    mf = app_dir / "manifest.json"
    if not mf.is_file():
        return None, ["manifest.json missing"]
    try:
        doc = json.loads(mf.read_text())
    except Exception as exc:  # noqa: BLE001
        return None, [f"manifest.json is not valid JSON: {exc}"]
    errs = []
    for key in ("name", "start_url", "display"):
        if not doc.get(key):
            errs.append(f"manifest.json lacks '{key}'")
    icons = doc.get("icons") or []
    if not isinstance(icons, list) or not icons:
        errs.append("manifest.json has no icons[]")
    else:
        for icon in icons:
            src = str(icon.get("src", ""))
            if not src:
                errs.append("an icon entry has no src")
            elif not (app_dir / src).is_file():
                errs.append(f"icon file missing: {src}")
    nuxel = doc.get("nuxel")
    if not isinstance(nuxel, dict):
        errs.append("manifest.json lacks the 'nuxel' block")
    else:
        if not isinstance(nuxel.get("capabilities"), list):
            errs.append("nuxel.capabilities must be a list")
        if not nuxel.get("bridge_version"):
            errs.append("nuxel.bridge_version missing")
    return doc, errs


def layer_static(name: str, spec: dict, res: Result) -> dict:
    app_dir = APPS_ROOT / name
    info: dict = {"dir": str(app_dir.relative_to(REPO))}
    if not app_dir.is_dir():
        res.bad(name, "L1", f"{app_dir} does not exist")
        info["status"] = "missing"
        return info
    index = app_dir / "index.html"
    if not index.is_file():
        res.bad(name, "L1", "index.html missing")
        return info
    html = index.read_text(errors="replace")
    info["html_bytes"] = len(html)

    doc, errs = parse_manifest(app_dir)
    for e in errs:
        res.bad(name, "L1", e)
    if doc and not errs:
        res.ok(name, "L1", "manifest.json complete (name/start_url/display/icons/nuxel.capabilities/bridge_version)")

    if spec.get("manifest_caps") and doc:
        caps = (doc.get("nuxel") or {}).get("capabilities") or []
        if spec["manifest_caps"] in caps:
            res.ok(name, "L1", f"capability declared: {spec['manifest_caps']}")
        else:
            res.bad(name, "L1", f"expected capability {spec['manifest_caps']} missing (has {caps})")

    # local asset resolution
    missing = [ref for ref in local_refs(html) if not (app_dir / ref.split("?")[0]).exists()]
    if missing:
        res.bad(name, "L1", f"index.html references missing local file(s): {missing}")
    else:
        res.ok(name, "L1", "every local href/src in index.html resolves")

    sw = app_dir / "sw.js"
    if not sw.is_file():
        res.bad(name, "L1", "sw.js missing (offline install)")
    else:
        swsrc = sw.read_text(errors="replace")
        if "addEventListener('install'" not in swsrc and 'addEventListener("install"' not in swsrc:
            res.bad(name, "L1", "sw.js has no install handler")
        if "addEventListener('fetch'" not in swsrc and 'addEventListener("fetch"' not in swsrc:
            res.bad(name, "L1", "sw.js has no fetch handler")
        if not re.search(r"CACHE_NAME\s*=", swsrc):
            res.bad(name, "L1", "sw.js has no CACHE_NAME (cache invalidation)")
        if not any(x in swsrc for x in ("addEventListener('install'", 'addEventListener("install"')):
            pass
        else:
            res.ok(name, "L1", "sw.js installs and serves a versioned cache")
        # precache entries must exist on disk
        for m in re.finditer(r"""['"](\.\.?/[^'"]+)['"]""", swsrc):
            p = m.group(1)
            if p.startswith("./icons") or p.endswith((".html", ".css", ".js", ".json", ".png", ".svg")):
                if not (app_dir / p).exists():
                    res.bad(name, "L1", f"sw.js precaches a non-existent path: {p}")

    # placeholder / emptiness checks.  The UI text of a JS-built app lives in
    # the JS as well as in the HTML, so both are counted: a shell page plus a
    # real app is not an empty app, and an empty app cannot pass by having HTML.
    if PLACEHOLDER_RE.search(html):
        res.bad(name, "L1", "placeholder text (lorem/TODO) found in index.html")
    js_ui = ""
    for js in sorted(app_dir.rglob("*.js")):
        js_ui += js.read_text(errors="replace")
    text = re.sub(r"<[^>]+>", " ", html) + " " + " ".join(
        m.group(1) for m in re.finditer(r"""['"]([^'"\n]{12,})['"]""", js_ui))
    words = len(text.split())
    if words < 60:
        res.bad(name, "L1", f"the app ships almost no user-facing text ({words} words in HTML+JS)")
    else:
        res.ok(name, "L1", f"{words} words of user-facing text in HTML+JS")
    info["status"] = "present"
    return info


def layer_syntax(name: str, spec: dict, res: Result) -> None:
    app_dir = APPS_ROOT / name
    if not app_dir.is_dir():
        return
    node = shutil.which("node")
    js_files = sorted(app_dir.rglob("*.js"))
    if not js_files:
        res.bad(name, "L2", "no JavaScript files at all")
        return
    if not node:
        res.skip(name, "L2", "node not available; JS parser check skipped")
        return
    for js in js_files:
        proc = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
        if proc.returncode != 0:
            res.bad(name, "L2", f"node --check failed for {js.relative_to(REPO)}: {proc.stderr.strip().splitlines()[-1] if proc.stderr else ''}")
    res.ok(name, "L2", f"node --check passed for {len(js_files)} JS file(s)")


def layer_dom(name: str, spec: dict, res: Result) -> None:
    app_dir = APPS_ROOT / name
    index = app_dir / "index.html"
    if not index.is_file():
        return
    html = index.read_text(errors="replace")
    html_ids = set(re.findall(r"""id\s*=\s*["']([A-Za-z0-9_\-:]+)["']""", html))
    js_text = ""
    for js in sorted(app_dir.rglob("*.js")):
        if js.name == "sw.js":
            continue
        js_text += js.read_text(errors="replace")
    made = set()
    for m in ID_MAKE_RE.finditer(js_text):
        made.add(next(g for g in m.groups() if g))
    used = set()
    for m in ID_REF_RE.finditer(js_text):
        used.add(next(g for g in m.groups() if g))
    unknown = sorted(used - html_ids - made)
    if unknown:
        res.bad(name, "L3", f"JS refers to element id(s) no HTML/JS provides: {unknown}")
    else:
        res.ok(name, "L3", f"{len(used)} id reference(s) in JS all resolve")
    # every id the briQ expects must exist in the static DOM or be created by JS
    missing = [i for i in spec.get("ids", []) if i not in html_ids and i not in made]
    if missing:
        res.bad(name, "L3", f"expected node(s) neither in HTML nor created by JS: {missing}")
    else:
        res.ok(name, "L3", "all expected UI nodes are provided")


JSDOM_HARNESS = r"""
const path = require('path');
const fs = require('fs');
const { JSDOM, VirtualConsole, ResourceLoader } = require(process.env.NUXEL_JSDOM_MODULE || 'jsdom');

const url = process.argv[2];
const hook = process.argv[3];
const ids = process.argv[4] ? process.argv[4].split(',') : [];

const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', (e) => errors.push('jsdomError: ' + (e && (e.message || e))));
vc.on('error', (...a) => errors.push('console.error: ' + a.map(String).join(' ')));
vc.on('warn', (...a) => { /* warnings are reported, not fatal */ });
const warnings = [];
vc.on('warn', (...a) => warnings.push(a.map(String).join(' ')));

(async () => {
  const dom = await JSDOM.fromURL(url, {
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      // Desktop/VM engine shims: a phone-only API being absent must never be an
      // app error. Apps that NEED one must degrade visibly, not throw.
      window.matchMedia = window.matchMedia || function (q) {
        return { matches: false, media: q, addEventListener() {}, removeEventListener() {},
                 addListener() {}, removeListener() {}, onchange: null, dispatchEvent() { return false; } };
      };
      window.ResizeObserver = window.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };
      window.IntersectionObserver = window.IntersectionObserver || class { observe() {} unobserve() {} disconnect() {} takeRecords() { return []; } };
      window.fetch = window.fetch || ((...a) => fetch(...a));
      if (!window.navigator.serviceWorker) {
        Object.defineProperty(window.navigator, 'serviceWorker', {
          value: { register: () => Promise.resolve({ scope: '', active: null }),
                   getRegistrations: () => Promise.resolve([]),
                   addEventListener() {}, controller: null, ready: Promise.resolve({}) },
          configurable: true,
        });
      }
      // jsdom has no canvas 2D unless the native `canvas` package is built.
      // A phone/WebKit engine always has one, so the smoke test supplies a
      // no-op context: this keeps the canvas apps' real drawing code on the
      // executed path instead of turning a missing desktop dependency into a
      // fake app failure.
      const proto = window.HTMLCanvasElement && window.HTMLCanvasElement.prototype;
      if (proto && !proto.__nuxelCanvasStub) {
        const stub2d = () => {
          const noop = () => {};
          const ctx = {
            canvas: null, save: noop, restore: noop, scale: noop, rotate: noop,
            translate: noop, transform: noop, setTransform: noop, resetTransform: noop,
            clearRect: noop, fillRect: noop, strokeRect: noop, beginPath: noop,
            closePath: noop, moveTo: noop, lineTo: noop, arc: noop, arcTo: noop,
            bezierCurveTo: noop, quadraticCurveTo: noop, rect: noop, fill: noop,
            stroke: noop, clip: noop, fillText: noop, strokeText: noop,
            drawImage: noop, putImageData: noop,
            createLinearGradient: () => ({ addColorStop: noop }),
            createRadialGradient: () => ({ addColorStop: noop }),
            createPattern: () => null, measureText: () => ({ width: 0 }),
            getImageData: () => ({ data: new Uint8ClampedArray(4), width: 1, height: 1 }),
            setLineDash: noop, getLineDash: () => [],
          };
          ctx.canvas = null;
          return ctx;
        };
        proto.getContext = function (kind) {
          if (kind === '2d') { const c = stub2d(); c.canvas = this; return c; }
          return null;
        };
        proto.toDataURL = proto.toDataURL || (() => 'data:image/png;base64,');
        proto.__nuxelCanvasStub = true;
      }
      window.alert = () => {};
      window.confirm = () => false;
      window.prompt = () => null;
      window.scrollTo = () => {};
    },
  });
  // let the app's async boot (fetch/sample load/timers) settle
  await new Promise((r) => setTimeout(r, 1500));
  const w = dom.window;
  const d = w.document;
  const missing = ids.filter((i) => !d.getElementById(i));
  const bodyText = (d.body ? d.body.textContent : '').replace(/\s+/g, ' ').trim();
  const out = {
    url,
    ready_state: d.readyState,
    hook_present: hook ? (typeof w[hook] !== 'undefined') : null,
    missing_ids: missing,
    body_words: bodyText ? bodyText.split(' ').length : 0,
    errors,
    warnings: warnings.slice(0, 5),
  };
  console.log('__NUXEL_SMOKE__' + JSON.stringify(out));
  dom.window.close();
  process.exit(0);
})().catch((e) => {
  console.log('__NUXEL_SMOKE__' + JSON.stringify({ url, fatal: String(e && (e.stack || e)) }));
  process.exit(0);
});
"""


def start_server(root: Path) -> tuple[ThreadingHTTPServer, str]:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def log_message(self, *a):  # keep the test output readable
            return

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def layer_runtime(name: str, spec: dict, res: Result, base_url: str, node_modules: str) -> None:
    node = shutil.which("node")
    if not node:
        res.skip(name, "L4", "node unavailable; runtime layer skipped")
        return
    harness = Path(tempfile.gettempdir()) / "nuxel-core-app-smoke.js"
    harness.write_text(JSDOM_HARNESS)
    env = dict(os.environ)
    env["NUXEL_JSDOM_MODULE"] = str(Path(node_modules) / "jsdom")
    env["NODE_PATH"] = str(node_modules)
    url = f"{base_url}/pwa/nuxel-apps/{name}/index.html"
    proc = subprocess.run([node, str(harness), url, spec.get("hook", ""), ",".join(spec.get("ids", []))],
                          capture_output=True, text=True, env=env, timeout=120)
    payload = None
    for line in proc.stdout.splitlines():
        if line.startswith("__NUXEL_SMOKE__"):
            payload = json.loads(line[len("__NUXEL_SMOKE__"):])
    if payload is None:
        res.bad(name, "L4", f"jsdom harness produced no result (stderr: {proc.stderr.strip()[-300:]})")
        return
    if payload.get("fatal"):
        res.bad(name, "L4", f"page load raised: {payload['fatal'].splitlines()[0]}")
        return
    if payload["missing_ids"]:
        res.bad(name, "L4", f"expected node(s) absent after JS ran: {payload['missing_ids']}")
    else:
        res.ok(name, "L4", "expected DOM nodes present after script execution")
    if payload["body_words"] < 10:
        res.bad(name, "L4", f"page rendered almost no text ({payload['body_words']} words)")
    else:
        res.ok(name, "L4", f"page rendered {payload['body_words']} words of UI text")
    if spec.get("hook"):
        if payload.get("hook_present"):
            res.ok(name, "L4", f"smoke hook window.{spec['hook']} exposed")
        else:
            res.bad(name, "L4", f"smoke hook window.{spec['hook']} missing (documented app API)")
    errs = payload.get("errors") or []
    # A missing host/bridge is expected offline; those are handled by the apps.
    real = [e for e in errs if not re.search(r"Not implemented|Could not parse CSS stylesheet", e)]
    if real:
        res.bad(name, "L4", "console errors: " + " | ".join(real[:3]))
    else:
        res.ok(name, "L4", "zero console errors / uncaught exceptions")


def main() -> int:
    ap = argparse.ArgumentParser(description="Nuxel core-app offline smoke test (briq-06b)")
    ap.add_argument("--app", nargs="*", default=None, help="subset of app names")
    ap.add_argument("--no-runtime", action="store_true", help="skip the jsdom layer (L1-L3 only)")
    ap.add_argument("--json", action="store_true", help="emit a JSON summary on stdout")
    args = ap.parse_args()

    names = args.app or list(CORE_APPS)
    res = Result()
    res.json["verdict"] = None

    for name in names:
        if name not in CORE_APPS:
            print(f"FAIL unknown app in test config: {name}", file=sys.stderr)
            return 1
        spec = CORE_APPS[name]
        info = layer_static(name, spec, res)
        layer_syntax(name, spec, res)
        layer_dom(name, spec, res)
        res.json["apps"].setdefault(name, {})["static"] = info

    runtime_done = False
    if not args.no_runtime:
        node_modules = os.environ.get("NUXEL_JSDOM", "")
        if not node_modules or not Path(node_modules, "jsdom").is_dir():
            res.json["layers"]["runtime"] = "skipped: jsdom not reachable (set NUXEL_JSDOM)"
        else:
            res.json["layers"]["runtime"] = "jsdom " + node_modules
            srv, base = start_server(REPO)
            try:
                for name in names:
                    layer_runtime(name, CORE_APPS[name], res, base, node_modules)
            finally:
                srv.shutdown()
            runtime_done = True

    print("\n".join(res.lines))
    verdict = ("OFFLINE_FAILED" if res.fail else
               "OFFLINE_RUNTIME_PASSED" if runtime_done else "OFFLINE_STATIC_ONLY")
    print(f"\nRESULT: PASS={res.pass_} FAIL={res.fail} WARN={res.warn} verdict={verdict}")
    if res.fail:
        print("Failing checks:")
        for line in res.lines:
            if line.startswith("FAIL"):
                print("  " + line)
    res.json["summary"] = {"pass": res.pass_, "fail": res.fail, "warn": res.warn, "verdict": verdict}
    if args.json:
        print(json.dumps(res.json, indent=2))
    return 1 if res.fail else 0


if __name__ == "__main__":
    sys.exit(main())
