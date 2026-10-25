#!/usr/bin/env python3
"""Offline tests for the A73 Bluetooth/Location connectors (no device, no D-Bus).

Imports the real bridge module with dbus absent (macOS/offline host) and proves:

  * LocationConnector persists the global policy atomically and survives a
    fresh instance (reboot-equivalent readback);
  * get_status reports `enabled` as a policy fact independent of a fix, and
    never manufactures coordinates;
  * BluetoothConnector reports a concrete `service_unavailable` blocker (not a
    generic 'unavailable on this build') when no adapter is present.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

# Offline host has no dbus: inject a minimal stub so the dbus.service
# decorators/base used at class-definition time resolve without a bus.
import types as _types
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
_fake_dbus = _types.ModuleType("dbus")
_fake_dbus.service = _FakeService()
_fake_dbus.SystemBus = lambda *a, **k: None
_fake_dbus.SessionBus = lambda *a, **k: None
_fake_dbus.Interface = lambda *a, **k: None
_fake_dbus.Boolean = bool
_fake_dbus.exceptions = _types.SimpleNamespace(DBusException=Exception)
_fake_dbus.PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
_fake_dbus.types = _types.SimpleNamespace(String=lambda v, **k: v)
sys.modules["dbus"] = _fake_dbus
sys.modules["dbus.service"] = _fake_dbus.service
sys.modules["dbus.mainloop.glib"] = _types.ModuleType("dbus.mainloop.glib")
sys.modules["dbus.exceptions"] = _fake_dbus.exceptions
sys.modules["gi"] = _types.ModuleType("gi")
sys.modules["gi.repository"] = _types.ModuleType("gi.repository")
sys.modules["gi.repository"].GLib = _types.SimpleNamespace(MainLoop=lambda *a, **k: None)
MODULE = os.path.join(SRC, "bridge.py")
spec = importlib.util.spec_from_file_location("bridge", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILURES: list = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="nuxel-loc-policy-")
    policy_path = os.path.join(tmp, "policy.json")

    lc = mod.LocationConnector()
    lc.POLICY_PATH = policy_path
    lc.geoclue = None  # no GeoClue on the offline host

    st = lc.get_status()
    check(st["enabled"] is False, "fresh policy defaults to disabled (privacy-safe)")
    check(st["permission_enabled"] is False, "permission_enabled mirrors enabled")
    check(st["location_fix_available"] is False, "no fix is ever fabricated")
    check(st["fix_source"] is None, "no fix source is invented")

    r = lc.set_enabled(True)
    check(r["success"] is True, "set_enabled(True) confirms a round trip")
    check(r["enabled"] is True, "policy reads back enabled after set")

    # Reboot-equivalent: a fresh connector instance must read the persisted value.
    lc2 = mod.LocationConnector()
    lc2.POLICY_PATH = policy_path
    lc2.geoclue = None
    check(lc2.get_status()["enabled"] is True, "policy persists across instances (reboot)")

    lc2.set_enabled(False)
    check(lc2.get_status()["enabled"] is False, "policy can be turned back off")

    # Bluetooth: no adapter anywhere on an offline host -> concrete blocker.
    bc = mod.BluetoothConnector()
    bst = bc.get_status()
    check(bst["adapter_present"] is False, "offline host has no Bluetooth adapter")
    check(bst["state"] == "service_unavailable",
          "no-adapter state is a concrete 'service_unavailable', not generic build placeholder")
    check(isinstance(bst.get("detail"), str) and "no hci0" in (bst.get("detail") or ""),
          "blocker names the missing hci0 controller")

    print("\n" + ("ALL PASS" if not FAILURES else "%d FAILURES" % len(FAILURES)))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
