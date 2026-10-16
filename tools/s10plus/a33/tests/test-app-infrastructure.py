#!/usr/bin/env python3
"""Offline test for the Nuxel application infrastructure (briq-04c).

Runs the REAL HTTP bridge handler (services/nuxel-bridge/src/api.py) against a
real localhost socket, with inert `dbus` stubs: no D-Bus, no hardware, no
handset. It proves the two contract-level properties the mission cares about:

  * the canonical app registry is served by the bridge, and an ABSENT registry
    is reported as unavailable instead of being replaced by an invented list;
  * the pinned bridge_version is published and a mismatching client is refused
    with an explicit 409 version_mismatch (never silently rejected).

Usage:  python3 tools/s10plus/a33/tests/test-app-infrastructure.py
"""

import importlib.util
import json
import os
import sys
import threading
import types
import urllib.error
import urllib.request
from http.server import HTTPServer

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
API_SRC = os.path.join(ROOT, "services", "nuxel-bridge", "src", "api.py")
REGISTRY = os.path.join(ROOT, "pwa", "nuxel-common", "app-registry.json")
PIN = os.path.join(ROOT, "pwa", "nuxel-common", "bridge-version.json")
BRIDGE_JS = os.path.join(ROOT, "pwa", "nuxel-common", "bridge.js")


def install_dbus_stub():
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


def load_api(registry_path):
    install_dbus_stub()
    os.environ["NUXEL_HTTP_MODE"] = "dev"
    spec = importlib.util.spec_from_file_location("nuxel_api_under_test", API_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.APP_REGISTRY_PATH = registry_path
    return mod


def main():
    failures = []

    def check(cond, msg):
        print(("  OK   " if cond else "  FAIL ") + msg)
        if not cond:
            failures.append(msg)

    pin = json.load(open(PIN))
    registry = json.load(open(REGISTRY))
    api = load_api(REGISTRY)
    api.BridgeAPIHandler.server_token = None

    server = HTTPServer(("127.0.0.1", 0), api.BridgeAPIHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % port

    def get(path, headers=None):
        req = urllib.request.Request(base + path, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            try:
                body = json.loads(body)
            except ValueError:
                pass
            return exc.code, body

    try:
        print("[infra] /api/v1/health publishes the pinned protocol version")
        status, body = get("/api/v1/health")
        check(status == 200, "health returns 200 (got %s)" % status)
        check(body.get("bridge_version") == pin["bridge_version"],
              "health bridge_version == pin %r (got %r)" % (pin["bridge_version"], body.get("bridge_version")))
        check(body.get("version") == pin["host_version"],
              "health version == host_version %r (got %r)" % (pin["host_version"], body.get("version")))
        check("registry" in body, "health reports the registry source")

        print("[infra] the bridge serves the canonical registry")
        status, body = get("/api/v1/apps/registry")
        check(status == 200, "registry endpoint returns 200 (got %s)" % status)
        check(body.get("available") is True, "registry is reported available")
        served = [a["id"] for a in body.get("apps", [])]
        expected = [a["id"] for a in registry["apps"]]
        check(served == expected, "served app ids == canonical registry ids (%d)" % len(expected))
        check(body.get("registry_version") == registry["registry_version"],
              "registry_version %r is served" % registry["registry_version"])
        check(body.get("bridge_version") == pin["bridge_version"],
              "the registry payload carries the pinned bridge_version")
        check("version_mismatch" not in body,
              "the served registry does not report a pin mismatch")

        print("[infra] an ABSENT registry is honest, not invented")
        api.APP_REGISTRY_PATH = os.path.join(ROOT, "does", "not", "exist.json")
        status, body = get("/api/v1/apps/registry")
        check(status == 200 and body.get("available") is False,
              "missing registry => available=false")
        check("apps" not in body, "missing registry => no fabricated apps[] list")
        check("not found" in (body.get("error") or ""), "missing registry => explicit error (%r)" % body.get("error"))
        api.APP_REGISTRY_PATH = REGISTRY
        print("[infra] a malformed registry is reported, not guessed")
        bad = os.path.join(ROOT, "build", "pkgmeta-test-bad-registry.json")
        os.makedirs(os.path.dirname(bad), exist_ok=True)
        with open(bad, "w") as fh:
            fh.write("{ this is not json")
        try:
            api.APP_REGISTRY_PATH = bad
            status, body = get("/api/v1/apps/registry")
            check(body.get("available") is False and "unreadable" in (body.get("error") or ""),
                  "malformed registry => available=false with an unreadable reason")
        finally:
            os.unlink(bad)
            api.APP_REGISTRY_PATH = REGISTRY

        print("[infra] the version gate refuses a mismatching client loudly")
        header = pin["http_header"]
        status, body = get("/api/v1/health", {header: pin["bridge_version"]})
        check(status == 200, "a client declaring the pinned version is served (200)")
        status, body = get("/api/v1/health", {header: "999"})
        check(status == 409, "a client declaring another version gets 409 (got %s)" % status)
        check(body.get("error") == "version_mismatch", "409 body names version_mismatch (%r)" % body.get("error"))
        check(body.get("expected") == pin["bridge_version"], "409 body names the expected version")
        check(body.get("got") == "999", "409 body echoes what the client declared")
        status, body = get("/api/v1/health")
        check(status == 200, "a legacy client without the header is still served (documented)")

        print("[infra] /api/v1/ping carries the protocol version")
        status, body = get("/api/v1/ping")
        check(status == 200, "ping returns 200 (got %s)" % status)
        check(isinstance(body, dict) and body.get("bridge_version") == pin["bridge_version"],
              "ping publishes bridge_version even when D-Bus is absent")

        print("[infra] the PWA client sends the pin and refuses a mismatch")
        js = open(BRIDGE_JS).read()
        check("options.headers['X-Nuxel-Bridge-Version'] = NUXEL_BRIDGE_VERSION" in js,
              "bridge.js sends the %s header" % header)
        check("export const NUXEL_BRIDGE_VERSION = '%s'" % pin["bridge_version"] in js,
              "bridge.js pins the protocol version to %r" % pin["bridge_version"])
        check("NuxelBridgeVersionError" in js, "bridge.js exposes a named version error")
        check("mockMode = true" in js, "bridge.js keeps an explicit mock mode for an unreachable host")
    finally:
        server.shutdown()
        server.server_close()

    if failures:
        print("\nFAILED: %d assertion(s)" % len(failures))
        return 1
    print("\nAll application-infrastructure checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
