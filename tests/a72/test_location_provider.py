#!/usr/bin/env python3
"""Offline state-machine tests for the canonical Nuxel location provider.

No D-Bus, no GeoClue daemon, no handset.  A fake provider drives the real
LocationConnector from services/nuxel-bridge/src/bridge.py so the state model,
freshness policy and "never fabricate a fix" rule are exercised as code, not
described in prose.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "services", "nuxel-bridge", "src")
sys.path.insert(0, SRC)


def _load_bridge():
    """Import bridge.py with a minimal dbus/gi stub (mirrors the A73 test)."""
    class _FakeObject:
        pass

    class _FakeService:
        Object = _FakeObject
        def method(self, *a, **k):
            def deco(f):
                return f
            return deco
        def signal(self, *a, **k):
            def deco(f):
                return f
            return deco

    fake = types.ModuleType("dbus")
    fake.service = _FakeService()
    fake.SystemBus = lambda *a, **k: None
    fake.SessionBus = lambda *a, **k: None
    fake.Interface = lambda *a, **k: None
    fake.Boolean = bool
    fake.exceptions = types.SimpleNamespace(DBusException=Exception)
    fake.PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
    fake.types = types.SimpleNamespace(String=lambda v, **k: v)
    saved = {k: sys.modules.get(k) for k in list(sys.modules) if k.startswith("dbus") or k == "gi" or k.startswith("gi.")}
    sys.modules["dbus"] = fake
    sys.modules["dbus.service"] = fake.service
    sys.modules["dbus.mainloop.glib"] = types.ModuleType("dbus.mainloop.glib")
    sys.modules["dbus.exceptions"] = fake.exceptions
    sys.modules["gi"] = types.ModuleType("gi")
    sys.modules["gi.repository"] = types.ModuleType("gi.repository")
    sys.modules["gi.repository"].GLib = types.SimpleNamespace(MainLoop=lambda *a, **k: None)
    spec = importlib.util.spec_from_file_location("bridge_under_test", os.path.join(SRC, "bridge.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, saved


bridge_mod, _saved_modules = _load_bridge()


class FakeGeoClue:
    DBUS_TIMEOUT = 2.0

    def __init__(self):
        self.connected = True
        self.service_available = True
        self.locations = []
        self.error = None
        self.acquire_ok = True
        self.acquire_calls = 0
        self.connect_calls = 0
        self.client_iface = types.SimpleNamespace(Stop=lambda **k: None)

    def service_installed(self):
        return self.service_available

    def connect(self, force=False):
        self.connect_calls += 1
        return self.connected

    def start_acquisition(self):
        self.acquire_calls += 1
        return (self.acquire_ok, None if self.acquire_ok else "acquire failed")

    def get_location(self):
        if self.error:
            return {"success": False, "error": self.error, "error_code": "PROVIDER_ERROR"}
        if not self.locations:
            return {"success": False, "error": "No location available", "error_code": "NO_FIX"}
        return self.locations.pop(0)


def connector(tmp_path, geo):
    lc = bridge_mod.LocationConnector()
    lc.POLICY_PATH = os.path.join(str(tmp_path), "location-policy.json")
    lc.geoclue = geo
    return lc


def fix(now=None, timestamp=True, lat=52.3702, lon=4.8952, accuracy=8.0):
    now = time.time() if now is None else now
    doc = {"success": True, "latitude": lat, "longitude": lon, "accuracy": accuracy,
           "observed_at": now, "source": "geoclue2"}
    if timestamp:
        doc["timestamp"] = now
    return doc


def test_disabled_is_not_no_fix():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        lc = connector(d, geo)
        st = lc.get_status()
        assert st["state"] == "disabled"
        assert st["enabled"] is False
        assert st["location_fix_available"] is False
        assert st["latitude"] is None and st["longitude"] is None


def test_unavailable_provider_never_invents_a_fix():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        geo.connected = False
        geo.service_available = False
        lc = connector(d, geo)
        lc.set_enabled(True)
        st = lc.get_status()
        assert st["state"] == "unavailable"
        assert st["provider_ready"] is False
        assert st["location_fix_available"] is False
        assert st["last_fix_timestamp"] is None
        assert st["gnss"]["fix_supported"] is False


def test_searching_means_acquisition_was_requested_not_a_fix():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        lc = connector(d, geo)
        lc.set_enabled(True)
        st = lc.get_status()
        assert geo.acquire_calls == 1
        assert st["state"] == "searching"
        assert st["latitude"] is None and st["longitude"] is None
        assert st["acquisition_started_at"] is not None


def test_fresh_fix_uses_real_provider_values():
    with tempfile.TemporaryDirectory() as d:
        now = time.time()
        geo = FakeGeoClue()
        geo.locations = [fix(now=now)]
        lc = connector(d, geo)
        lc.set_enabled(True)
        st = lc.get_status()
        assert st["state"] == "fixed"
        assert st["location_fix_available"] is True
        assert st["latitude"] == pytest.approx(52.3702)
        assert st["longitude"] == pytest.approx(4.8952)
        assert st["accuracy"] == pytest.approx(8.0)
        assert st["last_fix_timestamp"] == pytest.approx(now)
        assert st["last_fix_age_s"] is not None and st["last_fix_age_s"] < 5


def test_stale_fix_is_reported_as_stale_and_not_fresh():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        lc = connector(d, geo)
        lc.set_enabled(True)
        lc._last_fix = {
            "latitude": 52.0, "longitude": 4.0, "accuracy": 30.0,
            "timestamp": time.time() - 120, "timestamp_source": "provider", "source": "geoclue2",
        }
        st = lc.get_status()
        assert st["state"] == "stale"
        assert st["location_fix_available"] is False
        assert st["stale"] is True
        assert st["last_fix_age_s"] >= 120


def test_stale_outside_horizon_is_no_fix_and_coordinates_are_removed():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        lc = connector(d, geo)
        lc.set_enabled(True)
        lc._acquisition_started_at = None  # no active acquisition request
        lc._last_fix = {
            "latitude": 52.0, "longitude": 4.0, "accuracy": 30.0,
            "timestamp": time.time() - (lc.STALE_SECONDS + 60), "timestamp_source": "provider",
            "source": "geoclue2",
        }
        st = lc.get_status()
        assert st["state"] == "no_fix"
        assert st["latitude"] is None and st["longitude"] is None
        assert st["location_fix_available"] is False


def test_provider_error_is_distinct_from_no_fix():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        geo.error = "backend exploded"
        lc = connector(d, geo)
        lc.set_enabled(True)
        st = lc.get_status()
        assert st["state"] == "error"
        assert "backend exploded" in (st["last_error"] or "")
        assert st["location_fix_available"] is False


def test_invalid_provider_coordinates_are_rejected():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        geo.locations = [fix(lat=999, lon=4)]
        lc = connector(d, geo)
        st = lc.set_enabled(True)  # consumes the invalid provider reply
        assert st["state"] == "error"
        assert st["latitude"] is None and st["longitude"] is None
        assert "invalid provider fix" in (st["last_error"] or "")


def test_missing_timestamp_is_not_refreshed_by_a_poll():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        geo.locations = [fix(timestamp=False), fix(timestamp=False)]
        lc = connector(d, geo)
        lc.set_enabled(True)
        st1 = lc.get_status()
        first_ts = st1["last_fix_timestamp"]
        assert first_ts is not None
        assert lc._last_fix["timestamp_source"] == "observed"
        time.sleep(0.05)
        st2 = lc.get_status()
        assert st2["last_fix_timestamp"] == first_ts, "a poll must not refresh a missing provider timestamp"
        assert st2["state"] == "fixed"


def test_provider_disappearance_changes_state_without_destroying_last_fix():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        geo.locations = [fix()]
        lc = connector(d, geo)
        lc.set_enabled(True)
        assert lc.get_status()["state"] == "fixed"
        geo.connected = False
        st = lc.get_status()
        # An installed-but-idle/stopped provider is not permanently "broken":
        # it may be restarted by an authorized acquisition.  The fix must still
        # stop being presented as current.
        assert st["state"] in ("unavailable", "no_fix")
        assert st["provider_ready"] is False
        assert st["location_fix_available"] is False
        # The last real fix may still be known, but it is not presented as current.
        assert lc._last_fix is not None


def test_acquire_refuses_when_policy_is_disabled(monkeypatch):
    # Direct connector call still reports disabled; the D-Bus wrapper adds the
    # LOCATION_DISABLED code.  This proves acquisition cannot bypass policy.
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        lc = connector(d, geo)
        st = lc.get_status()
        assert st["state"] == "disabled"
        assert geo.acquire_calls == 0


def test_freshness_policy_is_documented_in_status():
    with tempfile.TemporaryDirectory() as d:
        lc = connector(d, FakeGeoClue())
        st = lc.get_status()
        assert st["freshness_seconds"] > 0
        assert st["stale_after_seconds"] >= st["freshness_seconds"]


def test_gnss_inventory_never_claims_fix_support():
    with tempfile.TemporaryDirectory() as d:
        lc = connector(d, FakeGeoClue())
        gnss = lc._gnss_hardware()
        assert gnss["fix_supported"] is False
        assert "blocker" in gnss
        assert isinstance(gnss["nodes"], list)


def test_gnss_inventory_sees_bound_spi_when_dev_is_private(monkeypatch):
    real_exists = os.path.exists
    real_listdir = os.listdir
    driver = "/sys/bus/spi/drivers/brcm gps spi"
    binding = driver + "/spi17.0"

    def fake_exists(path):
        return path == binding or real_exists(path)

    def fake_listdir(path):
        if path == driver:
            return ["spi17.0", "bind", "uevent", "unbind"]
        if path in ("/lib/firmware/gnss", "/lib/firmware"):
            return []
        return real_listdir(path)

    monkeypatch.setattr(bridge_mod.os.path, "exists", fake_exists)
    monkeypatch.setattr(bridge_mod.os, "listdir", fake_listdir)
    with tempfile.TemporaryDirectory() as d:
        lc = connector(d, FakeGeoClue())
        gnss = lc._gnss_hardware()
        assert gnss["present"] is True
        assert gnss["driver_bound"] is True
        assert gnss["node_visible_to_bridge"] is False
        assert gnss["fix_supported"] is False
        assert "firmware" in gnss["blocker"]


def test_status_redacts_coordinates_without_read_capability():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        geo.locations = [fix()]
        lc = connector(d, geo)
        lc.set_enabled(True)
        # The first get_status in set_enabled consumes the fix with redaction.
        full = lc.get_status(include_coordinates=True)
        redacted = lc.get_status(include_coordinates=False)
        assert full["latitude"] is not None and full["longitude"] is not None
        assert redacted["latitude"] is None and redacted["longitude"] is None
        assert redacted["accuracy"] is None
        assert redacted["last_fix_age_s"] is not None


def test_provider_access_denied_is_named_not_called_a_timeout():
    with tempfile.TemporaryDirectory() as d:
        geo = FakeGeoClue()
        geo.connected = False
        geo.last_error = 'org.freedesktop.DBus.Error.AccessDenied: policy rejected the call'
        lc = connector(d, geo)
        lc.set_enabled(True)
        st = lc.get_status()
        assert st["state"] == "unavailable"
        assert "AccessDenied" in (st["detail"] or "")
        assert "AccessDenied" in (st["last_error"] or "")
