#!/usr/bin/env python3
"""Offline unit tests: NetworkManager Wi-Fi AP activation (A51).

Guards the exact A51 regression: the bridge must never again call
``AddAndActivateConnection`` with the literal ``/new`` specific_object, and it
must select a *verified* AP object path on the same Wi-Fi device, reuse saved
profiles instead of duplicating them, and reject a stale AP with a bounded
re-scan.  No D-Bus daemon, no handset, no network.

Exit status = number of failures.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
BRIDGE_SRC = os.path.join(HERE, "src", "bridge.py")
API_SRC = os.path.join(HERE, "src", "api.py")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


# --------------------------------------------------------------------------- #
# Inert-but-shape-correct dbus / gi stubs so bridge.py can be imported and its
# pure NetworkManagerConnector logic exercised on a host with no dbus package.
# --------------------------------------------------------------------------- #
def install_stubs() -> None:
    dbus = types.ModuleType("dbus")

    class _DBusException(Exception):
        def __init__(self, *a, **k):
            super().__init__(*(a or (k.get("name", "org.freedesktop.DBus.Error.Failed"),)))
            self._dbus_name = k.get("name", "org.freedesktop.DBus.Error.Failed")
        def get_dbus_name(self):
            return self._dbus_name

    exceptions = types.ModuleType("dbus.exceptions")
    exceptions.DBusException = _DBusException
    exceptions.NameExistsException = type("NameExistsException", (_DBusException,), {})
    dbus.exceptions = exceptions
    dbus.DBusException = _DBusException
    dbus.PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
    dbus.types = types.SimpleNamespace(String=lambda *a, **k: str(a[0]) if a else "")
    dbus.ByteArray = bytearray
    dbus.String = str
    dbus.Boolean = bool
    dbus.Int32 = int
    dbus.ObjectPath = str
    dbus.Dictionary = lambda *a, **k: dict(a[0]) if a else {}

    class _Any:
        def __getattr__(self, name):
            def _boom(*a, **k):
                raise RuntimeError("no D-Bus in this test: %s" % name)
            return _boom

    dbus.Interface = lambda obj, name: obj
    dbus.SystemBus = lambda *a, **k: _Any()

    service = types.ModuleType("dbus.service")
    def method(iface, in_signature=None, out_signature=None):
        def deco(fn):
            fn._dbus_in_signature = in_signature
            fn._dbus_out_signature = out_signature
            return fn
        return deco
    def signal(iface, signature=None):
        def deco(fn):
            return fn
        return deco
    class Object:
        def __init__(self, *a, **k):
            pass
    class BusName:
        def __init__(self, *a, **k):
            pass
    service.method = method
    service.signal = signal
    service.Object = Object
    service.BusName = BusName
    dbus.service = service

    mainloop = types.ModuleType("dbus.mainloop")
    glib = types.ModuleType("dbus.mainloop.glib")
    glib.DBusGMainLoop = lambda *a, **k: None
    mainloop.glib = glib
    dbus.mainloop = mainloop

    gi = types.ModuleType("gi")
    repo = types.ModuleType("gi.repository")
    class _GLib:
        class MainLoop:
            def __init__(self, *a, **k):
                pass
            def run(self, *a, **k):
                pass
            def quit(self, *a, **k):
                pass
    repo.GLib = _GLib()
    gi.repository = repo

    sys.modules["dbus"] = dbus
    sys.modules["dbus.exceptions"] = exceptions
    sys.modules["dbus.service"] = service
    sys.modules["dbus.mainloop"] = mainloop
    sys.modules["dbus.mainloop.glib"] = glib
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repo


def load_bridge():
    # bridge.py imports its sibling media_store.py; the module dir must be on
    # sys.path or exec_module raises ModuleNotFoundError (A52 media store).
    src_dir = os.path.dirname(os.path.abspath(BRIDGE_SRC))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    spec = importlib.util.spec_from_file_location("nuxel_bridge_wifi_under_test", BRIDGE_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # type: ignore[union-attr]
    return mod


class FakeNM:
    """Captures AddAndActivateConnection / ActivateConnection arguments."""

    def __init__(self, add_result=("/org/freedesktop/NetworkManager/Settings/1",
                                   "/org/freedesktop/NetworkManager/ActiveConnection/1")):
        self.add_result = add_result
        self.add_calls = []
        self.activate_calls = []

    def AddAndActivateConnection(self, profile, device, specific_object):
        self.add_calls.append((dict(profile), str(device), str(specific_object)))
        return self.add_result

    def ActivateConnection(self, connection, device, specific_object):
        self.activate_calls.append((str(connection), str(device), str(specific_object)))
        return "/org/freedesktop/NetworkManager/ActiveConnection/2"


class FakeConn:
    def __init__(self, cfg):
        self.cfg = cfg
        self.updates = []

    def GetSettings(self):
        return self.cfg

    def Update(self, settings):
        self.updates.append(settings)
        return None


class FakeBus:
    def __init__(self, conns):
        self.conns = conns

    def get_object(self, bus, path):
        return self.conns[path]


def make_ap(path, ssid_bytes, bssid="00:11:22:33:44:55", strength=50,
            rsn=0, wpa=0, flags=0, frequency=2412):
    return {"path": path, "ssid_bytes": ssid_bytes, "bssid": bssid,
            "frequency": frequency, "strength": strength, "rsn": rsn,
            "wpa": wpa, "flags": flags}


def main() -> int:
    install_stubs()
    bridge = load_bridge()
    C = bridge.NetworkManagerConnector

    # ------------------------------------------------------------------ #
    # 1. Source-level: the `/new` sentinel is gone from every activation site.
    # ------------------------------------------------------------------ #
    print("[source] `/new` is never a specific_object / activation path")
    bridge_src = open(BRIDGE_SRC).read()
    api_src = open(API_SRC).read()
    check("'/new'" not in bridge_src, "bridge.py has no '/new' literal")
    check("'/new'" not in api_src, "api.py has no '/new' literal")
    for m in re.finditer(r"AddAndActivateConnection\([^\n]*", bridge_src):
        line = m.group(0)
        check("/new" not in line, "AddAndActivateConnection call site has no /new: %s" % line[:80])
    m = re.search(r"in_signature='ssssssss'.*?NetworkWifiConnect", bridge_src, re.S)
    check(m is not None, "NetworkWifiConnect D-Bus signature widened to carry AP identity")
    check("params.get(\"ap_path\", \"\")" in api_src and "params.get(\"bssid\", \"\")" in api_src,
          "api.py forwards ap_path/bssid to NetworkWifiConnect")

    # ------------------------------------------------------------------ #
    # 2. Pure helpers.
    # ------------------------------------------------------------------ #
    print("[helpers] security classification and SSID byte handling")
    check(C._security(0x400, 0, 0) == "wpa3", "SAE -> wpa3")
    check(C._security(0x8, 0, 0) == "wpa2", "PSK RSN -> wpa2")
    check(C._security(0, 0x4, 0) == "wpa2", "legacy WPA -> wpa2")
    check(C._security(0, 0, 0x1) == "wep", "privacy-only -> wep")
    check(C._security(0, 0, 0) == "open", "open network")
    check(C._ssid_bytes("home", "686f6d65") == b"home", "ssid_hex wins")
    check(C._ssid_bytes("café", None) == "café".encode("utf-8"), "utf-8 fallback")
    check(C._ssid_bytes("x", "not-hex!") == b"x", "bad hex falls back to utf-8")
    check(C._norm_mac("AA:bb:cc-DD") == "aabbccdd", "MAC normalisation")
    check(C._redact("psk secret here", "secret") == "psk [REDACTED] here", "secret redaction")

    # ------------------------------------------------------------------ #
    # 3. AP resolution: verify, never blindly trust.
    # ------------------------------------------------------------------ #
    print("[resolve] selected AP is verified against the current scan list")
    aps = [
        make_ap("/ap/1", b"home", bssid="AA:BB:CC:DD:EE:01", strength=30),
        make_ap("/ap/2", b"home", bssid="AA:BB:CC:DD:EE:02", strength=90),
        make_ap("/ap/3", b"other", bssid="AA:BB:CC:DD:EE:03", strength=100),
    ]
    conn = C()
    conn._access_points = lambda dev: aps

    ap, _ = conn._resolve_ap("/dev/2", b"home", ap_path="/ap/1")
    check(ap is not None and ap["path"] == "/ap/1", "exact verified path + SSID match wins")

    ap, _ = conn._resolve_ap("/dev/2", b"home", bssid="aa:bb:cc:dd:ee:02")
    check(ap is not None and ap["path"] == "/ap/2", "BSSID + SSID match")

    ap, _ = conn._resolve_ap("/dev/2", b"home")
    check(ap is not None and ap["path"] == "/ap/2", "duplicate SSID picks strongest")

    ap, _ = conn._resolve_ap("/dev/2", b"home", ap_path="/ap/999", bssid="aa:bb:cc:dd:ee:01")
    check(ap is not None and ap["path"] == "/ap/1", "stale path falls through to BSSID match")

    ap, _ = conn._resolve_ap("/dev/2", b"missing")
    check(ap is None, "unknown SSID -> None (no fabricated AP)")

    ap, _ = conn._resolve_ap("/dev/2", b"other", ap_path="/ap/3")
    check(ap is not None and ap["path"] == "/ap/3", "path + matching SSID resolves")

    # ------------------------------------------------------------------ #
    # 4. Profile structure.
    # ------------------------------------------------------------------ #
    print("[profile] typed a{sa{sv}} with autoconnect + correct key-mgmt")
    prof = conn._build_profile(b"home", "12345678", "wpa2")
    check(prof["connection"]["autoconnect"] is True, "autoconnect=True by default")
    check(prof["connection"]["type"] == "802-11-wireless", "connection type")
    check(prof["802-11-wireless"]["ssid"] == b"home", "ssid bytes preserved")
    check(prof["802-11-wireless-security"]["key-mgmt"] == "wpa-psk", "wpa2 -> wpa-psk")
    check(prof["802-11-wireless-security"]["psk"] == "12345678", "psk present")

    prof3 = conn._build_profile(b"home", "12345678", "wpa3")
    check(prof3["802-11-wireless-security"]["key-mgmt"] == "sae", "wpa3 -> sae")

    prof_open = conn._build_profile(b"open-net", "", "open")
    check("802-11-wireless-security" not in prof_open, "open network has no security section")

    # ------------------------------------------------------------------ #
    # 5. connect_wifi: no /new, profile reuse, stale-scan error.
    # ------------------------------------------------------------------ #
    print("[connect] AddAndActivateConnection uses the verified AP path")
    fake = FakeNM()
    conn2 = C()
    conn2.nm_proxy = fake
    conn2._select_device = lambda dev: "/org/freedesktop/NetworkManager/Devices/2"
    conn2._resolve_ap = lambda dev, ssid, ap, bssid: (
        make_ap("/org/freedesktop/NetworkManager/AccessPoint/1", b"home"), [])
    conn2._bounded_rescan = lambda *a, **k: None
    conn2._find_saved_connection = lambda ssid: None

    r = conn2.connect_wifi("home", "12345678", "wpa2",
                           ap_path="/org/freedesktop/NetworkManager/AccessPoint/1")
    check(r["success"] is True and r.get("stage") == "associating", "connect returns connecting/associating")
    check(len(fake.add_calls) == 1, "exactly one AddAndActivateConnection")
    _, dev_used, specific = fake.add_calls[0]
    check(specific == "/org/freedesktop/NetworkManager/AccessPoint/1", "specific_object is the real AP path")
    check("/new" not in specific, "specific_object is not /new")
    check(dev_used == "/org/freedesktop/NetworkManager/Devices/2", "device is the selected Wi-Fi device")

    # Existing saved profile -> ActivateConnection, no duplicate profile.
    print("[connect] saved profile is reused, never duplicated")
    fake2 = FakeNM()
    conn3 = C()
    conn3.nm_proxy = fake2
    conn3._select_device = lambda dev: "/org/freedesktop/NetworkManager/Devices/2"
    conn3._resolve_ap = lambda dev, ssid, ap, bssid: (
        make_ap("/org/freedesktop/NetworkManager/AccessPoint/1", b"home"), [])
    conn3._bounded_rescan = lambda *a, **k: None
    conn3._find_saved_connection = lambda ssid: "/org/freedesktop/NetworkManager/Settings/9"
    update_calls = []
    conn3._update_saved_profile = lambda *a, **k: update_calls.append(a)
    r = conn3.connect_wifi("home", "12345678", "wpa2",
                           ap_path="/org/freedesktop/NetworkManager/AccessPoint/1")
    check(r["success"] is True and r.get("reused") is True, "reused saved profile reported")
    check(len(update_calls) == 1, "saved profile is refreshed before reuse")
    check(len(fake2.add_calls) == 0, "no AddAndActivateConnection on reuse")
    check(len(fake2.activate_calls) == 1, "ActivateConnection called once on reuse")
    conn_path, dev_used2, specific2 = fake2.activate_calls[0]
    check(conn_path == "/org/freedesktop/NetworkManager/Settings/9", "reuses the saved settings-connection path")
    check("/new" not in specific2, "ActivateConnection specific_object is not /new")

    # Stale AP -> bounded rescan fails -> human-readable stale_scan, no NM call.
    print("[connect] stale AP is refused with a bounded, human-readable error")
    fake3 = FakeNM()
    conn4 = C()
    conn4.nm_proxy = fake3
    conn4._select_device = lambda dev: "/org/freedesktop/NetworkManager/Devices/2"
    conn4._resolve_ap = lambda dev, ssid, ap, bssid: (None, [])
    conn4._bounded_rescan = lambda *a, **k: None
    r = conn4.connect_wifi("home", "12345678", "wpa2", ap_path="/ap/gone")
    check(r["success"] is False and r.get("error") == "stale_scan", "stale AP -> stale_scan error")
    check(len(fake3.add_calls) == 0 and len(fake3.activate_calls) == 0, "stale AP performs no NM activation")

    # Unsafe inputs rejected before any NM call.
    print("[connect] unsafe inputs are rejected before touching NetworkManager")
    r = conn4.connect_wifi("home", "short", "wpa2")
    check(r["success"] is False and "Passphrase" in r.get("error", ""), "short PSK rejected")
    r = conn4.connect_wifi("home", "12345678", "wep")
    check(r["success"] is False and "Unsupported" in r.get("error", ""), "WEP refused")

    # _update_saved_profile sets autoconnect=true and writes the fresh PSK.
    print("[profile-update] reused profile gets autoconnect + fresh secret")
    saved_cfg = {
        "connection": {"id": "Nuxel home", "type": "802-11-wireless",
                       "autoconnect": False},
        "802-11-wireless": {"ssid": b"home", "mode": "infrastructure"},
    }
    fc = FakeConn(saved_cfg)
    fb = FakeBus({"/org/freedesktop/NetworkManager/Settings/9": fc})
    conn5 = C()
    conn5.bus = fb
    conn5._update_saved_profile("/org/freedesktop/NetworkManager/Settings/9",
                                b"home", "12345678", "wpa2")
    check(len(fc.updates) == 1, "Update called exactly once")
    updated = fc.updates[0]
    check(updated["connection"]["autoconnect"] is True, "autoconnect set to True")
    check(updated["802-11-wireless-security"]["psk"] == "12345678", "fresh PSK written to profile")
    check(updated["802-11-wireless-security"]["key-mgmt"] == "wpa-psk", "key-mgmt set for wpa2")

    print("\n%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
