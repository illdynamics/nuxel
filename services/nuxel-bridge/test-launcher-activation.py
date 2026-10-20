#!/usr/bin/env python3
"""Offline integration test: launcher -> bridge app activation (briq-04c).

The mission's application-infrastructure requirement is a *launcher-to-app
bridge*: the launcher resolves an app id to a launch descriptor through the
narrowly scoped privileged service, the one place app identity is decided, and
it must be impossible to turn that path into arbitrary execution.

This test runs the REAL HTTP bridge handler (services/nuxel-bridge/src/api.py)
against a real localhost socket, with inert `dbus` stubs - no D-Bus, no
hardware, no handset - and the REAL canonical registry
(pwa/nuxel-common/app-registry.json), then asserts:

  1. every registered app id resolves to a descriptor that matches the registry
     (PWA -> `navigate` + the registry's url; native -> `exec` + the registry's
     native_binary; documented placeholder -> `launchable: false` + the
     registry's own note). Nothing in a descriptor is invented;
  2. a client-supplied `binary`, `command`, `url` or `path` NEVER changes the
     descriptor: the bridge reports the registry's values, so activation cannot
     be used to launch an arbitrary program;
  3. a path-shaped or unknown id is refused (`invalid_app_id` / `unknown_app`)
     with NO execution and no filesystem path echoed;
  4. an unavailable registry is a 503, never a fabricated app;
  5. activation is recorded in a BOUNDED history, observable through
     /api/v1/apps/recent (the Live Console app's "activity" view);
  6. the activation path contains no execution primitive at all (source-level
     assertion: no subprocess / os.system / exec / eval / shell=True);
  7. the launcher side is wired for exactly this flow: apps.js dispatches
     app:launch + pwa:open/native:launch, app.js consumes them, the PWA host
     listens for app:launch, and EVERY pwa url resolves to a real file under the
     served docroot (an activation that 404s is not an activation).

NO device, no root, no network. Exit status = number of failures.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import threading
import types
import urllib.error
import urllib.request
from http.server import HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
API_SRC = os.path.join(HERE, "src", "api.py")
REGISTRY = os.path.join(ROOT, "pwa", "nuxel-common", "app-registry.json")
PIN = os.path.join(ROOT, "pwa", "nuxel-common", "bridge-version.json")
APPS_JS = os.path.join(ROOT, "pwa", "nuxel-home", "js", "apps.js")
APP_JS = os.path.join(ROOT, "pwa", "nuxel-home", "js", "app.js")
PWA_HOST = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-pwa-host.c")
BRIDGE_JS = os.path.join(ROOT, "pwa", "nuxel-home", "js", "bridge.js")
BRIDGE_SRC = os.path.join(HERE, "src", "bridge.py")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def install_dbus_stub() -> None:
    """Minimal inert dbus so api.py imports; every bus call raises."""
    class _Raises:
        def __getattr__(self, name):
            def _boom(*a, **k):
                raise RuntimeError("no D-Bus in this test")
            return _boom

    dbus = types.ModuleType("dbus")
    dbus.exceptions = types.SimpleNamespace(DBusException=RuntimeError)
    dbus.Interface = lambda *a, **k: _Raises()
    dbus.SystemBus = lambda *a, **k: _Raises()
    dbus.SessionBus = lambda *a, **k: _Raises()
    mainloop = types.ModuleType("dbus.mainloop")
    glib = types.ModuleType("dbus.mainloop.glib")
    glib.DBusGMainLoop = lambda *a, **k: None
    mainloop.glib = glib
    dbus.mainloop = mainloop
    sys.modules["dbus"] = dbus
    sys.modules["dbus.mainloop"] = mainloop
    sys.modules["dbus.mainloop.glib"] = glib


def load_api(registry_path: str):
    install_dbus_stub()
    os.environ["NUXEL_HTTP_MODE"] = "dev"
    spec = importlib.util.spec_from_file_location("nuxel_api_activation_under_test", API_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # type: ignore[union-attr]
    mod.APP_REGISTRY_PATH = registry_path
    return mod


def main() -> int:
    registry = json.load(open(REGISTRY))
    pin = json.load(open(PIN))
    api = load_api(REGISTRY)
    api.BridgeAPIHandler.server_token = None
    server = HTTPServer(("127.0.0.1", 0), api.BridgeAPIHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % port

    def post(path, payload, headers=None):
        req = urllib.request.Request(base + path, method="POST",
                                     data=json.dumps(payload).encode(),
                                     headers=dict({"Content-Type": "application/json"},
                                                  **(headers or {})))
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, {"raw": raw}

    def get(path):
        try:
            with urllib.request.urlopen(base + path, timeout=10) as res:
                return res.status, json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, {"raw": raw}

    print("[activation] every registered app resolves to its registry descriptor")
    for app in registry["apps"]:
        aid = app["id"]
        status, body = post("/api/v1/apps/activate",
                            {"app_id": "org.nuxel.Home", "target": aid, "source": "launcher"})
        if status != 200 or not body.get("success"):
            check(False, "%s: activation returned %s %s" % (aid, status, body))
            continue
        check(body.get("id") == aid and body.get("type") == app["type"],
              "%s: descriptor identity matches the registry" % aid)
        check(body.get("bridge_version") == pin["bridge_version"],
              "%s: descriptor carries the pinned bridge_version %s" % (aid, pin["bridge_version"]))
        check(body.get("source") == "registry",
              "%s: the descriptor is sourced from the registry" % aid)
        if app["type"] == "pwa":
            check(body.get("url") == app["url"],
                  "%s: the descriptor carries the registry url, not a client url (%s)"
                  % (aid, body.get("url")))
            entry = os.path.join(ROOT, "pwa", app["url"][len("/pwa/"):])
            if app.get("resolution") == "pending":
                check(body.get("action") == "pending_app_tree" and body.get("launchable") is False,
                      "%s: an app tree that is declared-but-not-landed is NOT reported as "
                      "launchable (%s)" % (aid, body.get("action")))
                check(bool(body.get("owner_groups")) and bool(body.get("detail")),
                      "%s: the not-launchable verdict names the owners and the reason" % aid)
                check(not os.path.isfile(entry),
                      "%s: the registry's pending claim is true on disk (%s is absent)"
                      % (aid, os.path.relpath(entry, ROOT)))
            else:
                check(body.get("action") == "navigate" and body.get("launchable") is True,
                      "%s: PWA activation navigates to the registry url (%s)" % (aid, body.get("url")))
                check(os.path.isfile(entry),
                      "%s: the activation url resolves to a real file under the docroot (%s)"
                      % (aid, os.path.relpath(entry, ROOT)))
        else:
            if app.get("native_binary"):
                check(body.get("action") == "exec" and body.get("native_binary") == app["native_binary"],
                      "%s: native activation names the registry binary (%s)" % (aid, body.get("native_binary")))
            else:
                check(body.get("launchable") is False
                      and body.get("action") == "documented_placeholder"
                      and bool(body.get("detail")),
                      "%s: a placeholder without a binary is reported honestly, not launched" % aid)
        check(body.get("executed") is False,
              "%s: the bridge reports that it executed nothing" % aid)

    print("[activation] a client cannot choose what runs")
    status, body = post("/api/v1/apps/activate",
                        {"app_id": "org.nuxel.Home", "target": "nuxel-dialer",
                         "binary": "/bin/sh", "command": "rm -rf /",
                         "url": "http://evil.example/", "path": "/etc/passwd"})
    check(status == 200 and body.get("native_binary") == "/usr/bin/nuxel-dialer",
          "a client-supplied binary/command is ignored; the registry binary wins (%s)"
          % body.get("native_binary"))
    check("/bin/sh" not in json.dumps(body) and "evil.example" not in json.dumps(body)
          and "rm -rf" not in json.dumps(body),
          "nothing from the request is echoed into the descriptor")

    print("[activation] invalid and unknown ids are refused, with no path echo")
    for bad, why in (("../../bin/sh", "a traversal"),
                     ("/bin/sh", "an absolute path"),
                     ("org.nuxel.Mail;rm -rf /", "a shell metacharacter"),
                     ("a" * 100, "an over-long id"),
                     ("", "an empty id")):
        status, body = post("/api/v1/apps/activate", {"app_id": "org.nuxel.Home", "target": bad})
        check(status == 400 and body.get("error") == "invalid_app_id",
              "%s is refused as invalid_app_id (%s %s)" % (why, status, body.get("error")))
    status, body = post("/api/v1/apps/activate", {"app_id": "org.nuxel.Home", "target": "org.nuxel.NotAThing"})
    check(status == 404 and body.get("error") == "unknown_app",
          "an unknown id is 404 unknown_app, not a guess (%s %s)" % (status, body.get("error")))
    status, body = post("/api/v1/apps/activate", {"app_id": "org.nuxel.Home"})
    check(status == 400 and body.get("error") == "invalid_app_id",
          "a missing target is refused rather than defaulting to something (%s)" % status)

    print("[activation] an unavailable registry is reported, never fabricated")
    api.APP_REGISTRY_PATH = os.path.join(HERE, "does-not-exist.json")
    status, body = post("/api/v1/apps/activate", {"app_id": "org.nuxel.Home", "target": "org.nuxel.Mail"})
    check(status == 503 and body.get("error") == "registry_unavailable",
          "an unreadable registry is 503 registry_unavailable (%s %s)" % (status, body.get("error")))
    check("apps" not in body, "no app list is invented when the registry is unreadable")
    api.APP_REGISTRY_PATH = REGISTRY

    print("[activation] activity is recorded in a bounded, observable history")
    status, body = get("/api/v1/apps/recent")
    check(status == 200 and body.get("success") is True, "/api/v1/apps/recent answers (%s)" % status)
    check(body.get("max") == 20 and len(body.get("activations", [])) <= 20,
          "the activation history is bounded (%s/%s)" % (len(body.get("activations", [])), body.get("max")))
    ids = [a["id"] for a in body.get("activations", [])]
    check("org.nuxel.NotAThing" not in ids,
          "a refused activation is not recorded as a launch")
    check(body.get("rejected", {}).get("count", 0) >= 6,
          "refusals are counted for the Console app's view (%s)" % body.get("rejected"))

    print("[activation] there is no execution primitive on this path")
    src = open(API_SRC, errors="replace").read()
    activation_src = src[src.index("def _activate_app"):src.index("def _verify_version")]
    for bad in ("subprocess", "os.system", "popen", "os.exec", "exec(", "eval(", "shell=True"):
        check(bad not in activation_src,
              "the activation handler contains no %r" % bad)
    check("os.path" not in activation_src,
          "the activation handler never touches the filesystem layout (ids are identifiers)")

    print("[activation] the launcher side is wired for this exact flow")
    apps_js = open(APPS_JS, errors="replace").read()
    app_js = open(APP_JS, errors="replace").read()
    host = open(PWA_HOST, errors="replace").read()
    check("app:launch" in apps_js and "pwa:open" in apps_js and "native:launch" in apps_js,
          "apps.js dispatches app:launch + pwa:open/native:launch")
    check("document.addEventListener('app:launch'" in app_js.replace('"', "'")
          and "pwa:open" in app_js and "native:launch" in app_js,
          "app.js consumes the launch events (search/recents and native launch)")
    check("app:launch" in host,
          "the PWA host observes app:launch (so a launch is visible in the live console)")
    check("nuxelDiag" in host, "the host's launch observation is the diagnostics channel, not a synthetic input")

    print("[rpc] every launcher bridge call maps to a real handler")
    bridge_js = open(BRIDGE_JS, errors="replace").read()
    called = set(re.findall(r"shared\(\)\.call\('([^']+)',\s*'([^']+)'", bridge_js))
    # The status bar polls these every 5 s; an unmapped pair produced a
    # repeating "Unknown RPC" warning and left the indicators on defaults.
    required = {("phone", "status"), ("notifications", "list"),
                ("permissions", "list"), ("sms", "list"),
                ("call", "end")}
    check(required <= called,
          "bridge.js calls the expected launcher RPC surface (%s)" % sorted(called))
    for ns, verb in sorted(required):
        method = api.BridgeAPIHandler.RPC_METHODS.get((ns, verb))
        check(method is not None,
              "%s.%s maps to a bridge method (%s)" % (ns, verb, method))
    bridge_src = open(BRIDGE_SRC, errors="replace").read()
    check("org.nuxel.Notifications" in bridge_src and "dbus.SystemBus()" in bridge_src,
          "SendNotification targets the system-bus notification hub, not a missing session daemon")

    server.shutdown()
    if FAILURES:
        print("\nFAILED: %d assertion(s)" % len(FAILURES))
        return 1
    print("\nAll launcher+bridge activation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
