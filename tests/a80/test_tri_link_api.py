"""HTTP bridge contract tests for the Tri-Link status endpoint."""
from __future__ import annotations

import importlib.util
import json
import sys
import threading
import types
import urllib.request
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_SRC = ROOT / "services/nuxel-bridge/src/api.py"
SRC_DIR = API_SRC.parent


def install_dbus_stub():
    class Raises:
        def __getattr__(self, name):
            def boom(*a, **k):
                raise RuntimeError("no D-Bus in this test")
            return boom

    dbus = types.ModuleType("dbus")
    dbus.exceptions = types.SimpleNamespace(DBusException=RuntimeError)
    dbus.Interface = lambda *a, **k: Raises()
    dbus.SystemBus = lambda *a, **k: Raises()
    dbus.SessionBus = lambda *a, **k: Raises()
    mainloop = types.ModuleType("dbus.mainloop")
    glib = types.ModuleType("dbus.mainloop.glib")
    glib.DBusGMainLoop = lambda *a, **k: None
    mainloop.glib = glib
    dbus.mainloop = mainloop
    sys.modules["dbus"] = dbus
    sys.modules["dbus.mainloop"] = mainloop
    sys.modules["dbus.mainloop.glib"] = glib


def load_api():
    install_dbus_stub()
    sys.path.insert(0, str(SRC_DIR))
    import os
    os.environ["NUXEL_HTTP_MODE"] = "dev"
    spec = importlib.util.spec_from_file_location("api_tri_link_under_test", API_SRC)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_status_get_and_rpc_are_read_only_and_honest(monkeypatch):
    api = load_api()
    payload = {
        "success": True,
        "transports": {
            "serial": {"status": "AVAILABLE"},
            "wifi": {"status": "UNAVAILABLE"},
            "usb": {"status": "BLOCKED_KERNEL_PANIC"},
        },
    }
    assert api.tri_link_status is not None
    monkeypatch.setattr(api.tri_link_status, "get_status", lambda: payload)
    api.BridgeAPIHandler.server_token = None
    server = HTTPServer(("127.0.0.1", 0), api.BridgeAPIHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % server.server_address[1]

    def get(path):
        with urllib.request.urlopen(base + path, timeout=5) as res:
            return res.status, json.loads(res.read())

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, json.loads(res.read())

    try:
        status, doc = get("/api/v1/system/tri-link")
        assert status == 200
        assert doc["transports"]["usb"]["status"] == "BLOCKED_KERNEL_PANIC"
        status, doc = post("/api/v1/rpc", {
            "app_id": "org.nuxel.WiFiSSHConsole",
            "namespace": "system", "verb": "tri-link", "params": {},
        })
        assert status == 200
        assert doc["result"]["transports"]["wifi"]["status"] == "UNAVAILABLE"
    finally:
        server.shutdown()


def test_missing_status_module_is_an_explicit_error(monkeypatch):
    api = load_api()
    monkeypatch.setattr(api, "tri_link_status", None)
    api.BridgeAPIHandler.server_token = None
    server = HTTPServer(("127.0.0.1", 0), api.BridgeAPIHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    try:
        req = urllib.request.Request(base + "/api/v1/rpc",
                                     data=json.dumps({"app_id": "org.nuxel.LiveConsole",
                                                      "namespace": "system",
                                                      "verb": "tri-link", "params": {}}).encode(),
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=5) as res:
            doc = json.loads(res.read())
        assert doc["result"]["success"] is False
        assert "unavailable" in doc["result"]["error"]
    finally:
        server.shutdown()
