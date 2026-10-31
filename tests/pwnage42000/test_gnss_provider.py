#!/usr/bin/env python3
"""PWNAGE-42000: BCM4773 BBD/LHD provider and source-classification tests."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "services", "nuxel-bridge", "src")


sys.path.insert(0, SRC)

def load_bridge():
    class _Obj:
        pass
    class _Service:
        Object = _Obj
        def method(self, *a, **k):
            return lambda f: f
        def signal(self, *a, **k):
            return lambda f: f
    fake = types.ModuleType("dbus")
    fake.service = _Service()
    fake.SystemBus = lambda *a, **k: None
    fake.SessionBus = lambda *a, **k: None
    fake.Interface = lambda *a, **k: None
    fake.Boolean = bool
    fake.UInt32 = lambda v: int(v)
    fake.String = lambda v: str(v)
    fake.exceptions = types.SimpleNamespace(DBusException=Exception)
    fake.PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
    fake.types = types.SimpleNamespace(String=lambda v, **k: v, UInt32=lambda v, **k: int(v))
    sys.modules["dbus"] = fake
    sys.modules["dbus.service"] = fake.service
    sys.modules["dbus.exceptions"] = fake.exceptions
    sys.modules["dbus.mainloop.glib"] = types.ModuleType("dbus.mainloop.glib")
    sys.modules["gi"] = types.ModuleType("gi")
    sys.modules["gi.repository"] = types.ModuleType("gi.repository")
    sys.modules["gi.repository"].GLib = types.SimpleNamespace(MainLoop=lambda *a, **k: None)
    spec = importlib.util.spec_from_file_location("bridge_gnss_under_test", os.path.join(SRC, "bridge.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bridge_mod = load_bridge()
import hw_providers  # noqa: E402


def test_classify_network_is_never_gnss():
    c = bridge_mod.GeoClueConnector
    assert c._classify_source("GeoIP (ichnaea)") == ("network_ip", "network")
    assert c._classify_source("ipf fallback (from WiFi data)") == ("network_wifi", "network")
    assert c._classify_source("WiFi AP") == ("network_wifi", "network")
    assert c._classify_source("GPS") == ("gnss", "satellite")
    assert c._classify_source("Unknown backend") == ("geoclue_unknown", "unknown")
    assert c._classify_source("") == ("geoclue_unknown", "unknown")


def test_power_rail_requires_matching_readback(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        rail = os.path.join(d, "GPS_PWR_EN")
        with open(rail, "w") as f:
            f.write("0")
        p = hw_providers.GnssProvider()
        monkeypatch.setattr(p, "POWER_RAIL", rail)
        out = p.power_rail(True, timeout=0.2)
        assert out["success"] is True
        assert out["requested"] is True and out["actual"] is True
        assert out["write_ok"] is True and out["readback_ok"] is True
        with open(rail) as f:
            assert f.read().strip() == "1"


def test_power_rail_mismatch_is_failure(monkeypatch):
    p = hw_providers.GnssProvider()
    monkeypatch.setattr(p, "POWER_RAIL", "/dev/null")
    monkeypatch.setattr(p, "_read_rail", lambda: (False, None))
    out = p.power_rail(True, timeout=0.05)
    assert out["success"] is False
    assert out["write_ok"] is True
    assert out["readback_ok"] is False
    assert "mismatch" in out["error"]


def test_power_rail_readback_unavailable_is_failure(monkeypatch):
    p = hw_providers.GnssProvider()
    monkeypatch.setattr(p, "POWER_RAIL", "/dev/null")
    monkeypatch.setattr(p, "_read_rail", lambda: (None, "EACCES"))
    out = p.power_rail(False, timeout=0.05)
    assert out["success"] is False
    assert out["readback_ok"] is False
    assert "EACCES" in out["error"]


def test_sample_nmea_never_claims_nmea_or_fix(monkeypatch):
    p = hw_providers.GnssProvider()
    monkeypatch.setattr(p, "inventory", lambda: {
        "protocol": "broadcom-bbd-lhd-rpc", "nodes": ["/dev/ttyBCM"],
        "firmware": [], "firmware_present": False, "vendor_runtime_complete": False,
        "blocker": "no compatible BCM4773 BBD sensor-hub patch firmware",
        "power_rail_state": False, "active_leases": 0,
    })
    monkeypatch.setattr(p, "_observe_bbd", lambda deadline: {
        "bytes": 0, "stream": "no_data", "node": "/dev/ttyBCM",
        "protocol": "broadcom-bbd-lhd-rpc", "nmea": False})
    out = p.sample_nmea(seconds=0.2, timeout=0.2)
    assert out["nmea_stream"] is False
    assert out["fix"] is None
    assert out["protocol"] == "broadcom-bbd-lhd-rpc"
    assert out["bytes"] == 0


def test_acquire_refuses_without_compatible_runtime(monkeypatch):
    p = hw_providers.GnssProvider()
    monkeypatch.setattr(p, "_policy_enabled", lambda: True)
    monkeypatch.setattr(p, "inventory", lambda: {
        "protocol": "broadcom-bbd-lhd-rpc", "nodes": ["/dev/ttyBCM"],
        "firmware": [], "firmware_present": False, "vendor_runtime_complete": False,
        "blocker": "no compatible BCM4773 BBD sensor-hub patch firmware",
        "power_rail_state": False, "active_leases": 0,
    })
    called = []
    monkeypatch.setattr(p, "power_rail", lambda *a, **k: called.append(1) or {"success": True})
    out = p.acquire(seconds=1, timeout=1)
    assert out["success"] is False
    assert out["error_code"] == "UNSUPPORTED_PROTOCOL"
    assert called == [], "must not power a receiver with no consumer"


def test_acquire_refuses_when_policy_off(monkeypatch):
    p = hw_providers.GnssProvider()
    monkeypatch.setattr(p, "_policy_enabled", lambda: False)
    out = p.acquire(seconds=1, timeout=1)
    assert out["success"] is False
    assert out["error_code"] == "LOCATION_DISABLED"


def test_lease_reference_count_restores_only_after_last_owner(monkeypatch):
    hw_providers.GnssProvider._rail_owners.clear()
    hw_providers.GnssProvider._rail_initial_state = None
    p = hw_providers.GnssProvider()
    calls = []
    monkeypatch.setattr(p, "_policy_enabled", lambda: True)
    monkeypatch.setattr(p, "inventory", lambda: {
        "protocol": "broadcom-bbd-lhd-rpc", "nodes": ["/dev/ttyBCM"],
        "firmware": ["fake"], "firmware_present": True, "vendor_runtime_complete": True,
        "blocker": None, "power_rail_state": False, "active_leases": 0,
    })
    monkeypatch.setattr(p, "power_rail", lambda enabled=True, timeout=5.0: (
        calls.append(bool(enabled)) or {"success": True, "enabled": bool(enabled)}))
    monkeypatch.setattr(p, "_observe_bbd", lambda deadline: {
        "bytes": 0, "stream": "no_data", "node": "/dev/ttyBCM",
        "protocol": "broadcom-bbd-lhd-rpc", "nmea": False})
    a = p.acquire(seconds=1, timeout=1)
    b = p.acquire(seconds=1, timeout=1)
    assert a["acquired"] and b["acquired"]
    p.release(a["lease_id"])
    assert calls == [True], "one owner remains -> no power-off"
    p.release(b["lease_id"])
    assert calls == [True, False], "last owner -> verified power-off"
    assert hw_providers.GnssProvider._active_owners() == 0


def test_http_gnss_power_requires_location_manage():
    api = open(os.path.join(SRC, "api.py"), encoding="utf-8").read()
    assert "capability = ('location:manage' if verb == 'gnss-power'" in api
    assert "else 'location:read'" in api
    assert "gnss.probe(" in api
    assert "sample_nmea" not in api
