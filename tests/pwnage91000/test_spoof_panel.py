#!/usr/bin/env python3
"""PWNAGE-91000 PenguInterface spoof regressions.

These are host/offline tests for the profile semantics and UI contract.  The
live device RPC is exercised separately by the mission evidence capture.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_api():
    # api.py imports python-dbus and gi at module scope; both are optional for
    # the pure spoof helpers under test, so provide inert stand-ins.
    if "dbus" not in sys.modules:
        dbus = types.ModuleType("dbus")
        mainloop = types.ModuleType("dbus.mainloop")
        glib = types.ModuleType("dbus.mainloop.glib")
        glib.DBusGMainLoop = lambda *a, **k: None
        mainloop.glib = glib
        dbus.mainloop = mainloop
        sys.modules.update({"dbus": dbus, "dbus.mainloop": mainloop,
                            "dbus.mainloop.glib": glib})
    spec = importlib.util.spec_from_file_location(
        "nuxel_api_spoof_test", ROOT / "services/nuxel-bridge/src/api.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def handler(mod, tmp_path):
    h = object.__new__(mod.BridgeAPIHandler)
    state = tmp_path / "state"
    runtime = tmp_path / "runtime"
    state.mkdir()
    runtime.mkdir()
    h.SPOOF_STATE_DIR = str(state)
    h.SPOOF_RUNTIME_DIR = str(runtime)
    h.SPOOF_STATE = str(state / "profile.json")
    h.SPOOF_LEGACY_PROFILE = str(runtime / "profile.json")
    h._real_identity = lambda: {"uname": "real-uname", "os_release": {"NAME": "RealOS"}}
    h._load_app_registry = lambda: {"available": True, "source": "test", "apps": [
        {"id": "org.nuxel.One", "name": "One", "type": "native"},
        {"id": "org.nuxel.Two", "name": "Two", "type": "pwa"},
    ]}
    return h


def test_v1_migration_keeps_targets_as_per_app():
    mod = load_api()
    doc = mod.BridgeAPIHandler._spoof_norm_doc({
        "enabled": True, "ua": "UA-v1", "targets": ["org.nuxel.One"],
        "os_release": "NAME=V1", "uname": {"release": "1.0"}})
    assert doc["global"] is None
    assert set(doc["apps"]) == {"org.nuxel.One"}
    assert doc["apps"]["org.nuxel.One"]["ua"] == "UA-v1"
    assert doc["apps"]["org.nuxel.One"]["uname"]["release"] == "1.0"


def test_v1_without_targets_becomes_global():
    mod = load_api()
    doc = mod.BridgeAPIHandler._spoof_norm_doc({"enabled": True, "ua": "UA", "targets": []})
    assert doc["global"] and doc["global"]["ua"] == "UA"
    assert doc["apps"] == {}


def test_empty_v2_document_stays_empty():
    mod = load_api()
    doc = mod.BridgeAPIHandler._spoof_norm_doc(
        {"schema_version": 2, "global": None, "apps": {}})
    assert doc == {"schema_version": 2, "global": None, "apps": {}}


def test_per_app_wins_over_global():
    mod = load_api()
    doc = mod.BridgeAPIHandler._spoof_norm_doc({
        "global": {"enabled": True, "ua": "global"},
        "apps": {"org.nuxel.One": {"enabled": True, "ua": "app"}}})
    cfg, scope = mod.BridgeAPIHandler._spoof_effective(doc, "org.nuxel.One")
    assert (cfg["ua"], scope) == ("app", "app")
    cfg, scope = mod.BridgeAPIHandler._spoof_effective(doc, "org.nuxel.Two")
    assert (cfg["ua"], scope) == ("global", "global")


def test_reset_app_is_scoped(tmp_path):
    mod = load_api()
    h = handler(mod, tmp_path)
    assert h._spoof_rpc("org.nuxel.PenguInterface", "set", {
        "scope": "app", "app_id": "org.nuxel.One", "ua": "one"})["success"]
    assert h._spoof_rpc("org.nuxel.PenguInterface", "set", {
        "scope": "app", "app_id": "org.nuxel.Two", "ua": "two"})["success"]
    out = h._spoof_rpc("org.nuxel.PenguInterface", "reset", {
        "scope": "app", "app_id": "org.nuxel.One"})
    assert out["success"] and out["existed"] is True
    state = h._spoof_state()
    assert "org.nuxel.One" not in state["apps"]
    assert state["apps"]["org.nuxel.Two"]["ua"] == "two"


def test_reset_global_keeps_apps(tmp_path):
    mod = load_api()
    h = handler(mod, tmp_path)
    h._spoof_rpc("org.nuxel.PenguInterface", "set", {"scope": "global", "ua": "g"})
    h._spoof_rpc("org.nuxel.PenguInterface", "set", {
        "scope": "app", "app_id": "org.nuxel.One", "ua": "one"})
    out = h._spoof_rpc("org.nuxel.PenguInterface", "reset", {"scope": "global"})
    assert out["success"] and out["existed"] is True
    state = h._spoof_state()
    assert state["global"] is None
    assert state["apps"]["org.nuxel.One"]["ua"] == "one"


def test_launch_env_uses_scoped_profile_and_real_os_release(tmp_path):
    mod = load_api()
    h = handler(mod, tmp_path)
    h._spoof_rpc("org.nuxel.PenguInterface", "set", {
        "scope": "global", "ua": "ua", "uname": {"release": "9.9"}})
    env = h._spoof_launch_env("org.nuxel.One")
    assert env["LD_PRELOAD"] == h.SPOOF_LIB
    profile = Path(env["NUXEL_SPOOF_PROFILE"])
    doc = json.loads(profile.read_text())
    assert doc["release"] == "9.9"
    assert Path(doc["os_release"]).is_file()
    # No configured os-release text => the host's real file is copied when it
    # exists (macOS CI hosts have no /etc/os-release, so only existence is
    # guaranteed here).
    host_os = Path("/etc/os-release")
    if host_os.is_file():
        assert Path(doc["os_release"]).read_text() == host_os.read_text().rstrip() + "\n"


def test_launch_env_honours_explicit_os_release(tmp_path):
    mod = load_api()
    h = handler(mod, tmp_path)
    h._spoof_rpc("org.nuxel.PenguInterface", "set", {
        "scope": "app", "app_id": "org.nuxel.One",
        "os_release_text": "NAME=SpoofOS\nVERSION_ID=9"})
    env = h._spoof_launch_env("org.nuxel.One")
    doc = json.loads(Path(env["NUXEL_SPOOF_PROFILE"]).read_text())
    assert Path(doc["os_release"]).read_text().strip() == "NAME=SpoofOS\nVERSION_ID=9"


def test_launch_env_empty_without_spoof(tmp_path):
    mod = load_api()
    h = handler(mod, tmp_path)
    assert h._spoof_launch_env("org.nuxel.One") == {}


def test_app_list_returns_registry_ids(tmp_path):
    mod = load_api()
    h = handler(mod, tmp_path)
    out = h._spoof_rpc("org.nuxel.PenguInterface", "apps", {})
    assert out["success"] and out["available"] is True
    assert [a["id"] for a in out["apps"]] == ["org.nuxel.One", "org.nuxel.Two"]


def test_ui_exposes_global_scope_and_app_selector():
    html = (ROOT / "pwa/nuxel-apps/penguinterface/index.html").read_text()
    assert 'id="spoof-scope-global"' in html
    assert 'id="spoof-app-select"' in html
    assert 'id="spoof-reset-all"' in html
    js = (ROOT / "pwa/nuxel-apps/penguinterface/js/spoof.js").read_text()
    assert "scope: scope()" in js
    assert "params.app_id = appId" in js
    assert "reset" in js and "This app's spoof removed" in js
    assert "spoof-selected" not in js  # no invented selector state


def test_launch_path_injects_spoof_env():
    api = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    assert "_spoof_launch_env(target_id)" in api
    assert '"NUXEL_SPOOF_PROFILE": profile_path' in api
    assert "spoof environment failed for %s" in api
