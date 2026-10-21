#!/usr/bin/env python3
"""A47 regression tests: NetworkManager AP paths, UI owners, heat and metrics.

The D-Bus tests import the real bridge source with a tiny in-process dbus stub;
the UI/heat tests assert the exact source contracts that caused the owner-visible
failures.  No phone, network, or secret is touched.
"""
from pathlib import Path
import importlib.util
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
BRIDGE = ROOT / 'services/nuxel-bridge/src/bridge.py'
API = ROOT / 'services/nuxel-bridge/src/api.py'
NAV = ROOT / 'pwa/nuxel-home/js/navigation.js'
KB = ROOT / 'pwa/nuxel-home/js/touch-keyboard.js'
LOCK = ROOT / 'pwa/nuxel-home/js/lockscreen.js'
LOCKCSS = ROOT / 'pwa/nuxel-home/css/lockscreen.css'
STYLE = ROOT / 'pwa/nuxel-home/css/style.css'
LAUNCHER = ROOT / 'pwa/nuxel-home/css/launcher.css'
STATUS = ROOT / 'pwa/nuxel-home/js/status-bar.js'
STATUSCSS = ROOT / 'pwa/nuxel-home/css/status-bar.css'
MONITOR = ROOT / 'pwa/nuxel-home/js/system-monitor.js'
METRICS = ROOT / 'services/nuxel-metrics/nuxel-metricsd.c'
WLFB = ROOT / 'tools/s10plus/a34/nuxel-wl-fb.c'
SETTINGS = ROOT / 'pwa/nuxel-apps/settings/wifi-settings.js'
API_PY = ROOT / 'services/nuxel-bridge/src/api.py'


def require(cond, label):
    if not cond:
        raise AssertionError(label)
    print('PASS', label)


def install_dbus_stub():
    dbus = types.ModuleType('dbus')
    class Dictionary(dict):
        def __init__(self, *a, signature=None, **kw):
            super().__init__(*a, **kw)
    class ByteArray(bytes):
        pass
    class DBusException(Exception):
        def __init__(self, name='', message=''):
            super().__init__(message or name)
            self._name = name
        def get_dbus_name(self):
            return self._name
    dbus.Dictionary = Dictionary
    dbus.PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
    dbus.INTROSPECTABLE_IFACE = 'org.freedesktop.DBus.Introspectable'
    dbus.ByteArray = ByteArray
    dbus.String = str
    dbus.Boolean = bool
    dbus.UInt32 = int
    dbus.ObjectPath = str
    dbus.Interface = lambda obj, name: obj
    dbus.SystemBus = lambda: None
    dbus.SessionBus = lambda: None
    dbus.exceptions = types.SimpleNamespace(DBusException=DBusException,
                                             NameExistsException=Exception)
    service = types.SimpleNamespace()
    service.method = lambda *a, **k: (lambda fn: fn)
    service.signal = lambda *a, **k: (lambda fn: fn)
    service.Object = object
    service.BusName = lambda *a, **k: None
    dbus.service = service
    dbus.mainloop = types.SimpleNamespace(
        glib=types.SimpleNamespace(DBusGMainLoop=lambda **k: None))
    sys.modules['dbus'] = dbus
    sys.modules['dbus.service'] = service
    sys.modules['dbus.exceptions'] = dbus.exceptions
    sys.modules['dbus.mainloop'] = dbus.mainloop
    sys.modules['dbus.mainloop.glib'] = dbus.mainloop.glib
    gi = types.ModuleType('gi')
    gi.repository = types.SimpleNamespace(GLib=types.SimpleNamespace(MainLoop=object))
    sys.modules['gi'] = gi
    sys.modules['gi.repository'] = gi.repository


def load_bridge():
    install_dbus_stub()
    spec = importlib.util.spec_from_file_location('a47_bridge', BRIDGE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ap(path, dev, ssid, sec='wpa2', bssid='AA:AA:AA:AA:AA:01', strength=50):
    return {'ap_path': path, 'device': dev, 'ssid': ssid,
            'ssid_bytes': ssid.encode(), 'ssid_hex': ssid.encode().hex(),
            'bssid': bssid, 'strength': strength, 'frequency': 2412,
            'security': sec, 'flags': 1, 'wpa_flags': 1, 'rsn_flags': 1,
            'record': {'interface': 'wlan0' if dev.endswith('2') else 'wlan1'}}


def main():
    mod = load_bridge()
    conn = mod.NetworkManagerConnector()

    require(mod._wifi_security_from_flags(0x400, 0, 1) == 'wpa3', 'SAE flags map to WPA3')
    require(mod._wifi_security_from_flags(0, 1, 1) == 'wpa2', 'WPA/PSK flags map to WPA2')
    require(mod._wifi_security_from_flags(0, 0, 0) == 'open', 'no security flags map to open')
    require(mod._wifi_key_mgmt('wpa3') == 'sae' and mod._wifi_key_mgmt('wpa2') == 'wpa-psk',
            'security mode maps to the NM key-mgmt value')

    aps = [
        ap('/org/freedesktop/NetworkManager/AccessPoint/2', '/org/freedesktop/NetworkManager/Devices/2',
           'Dup', bssid='AA:AA:AA:AA:AA:01', strength=40),
        ap('/org/freedesktop/NetworkManager/AccessPoint/3', '/org/freedesktop/NetworkManager/Devices/3',
           'Dup', bssid='AA:AA:AA:AA:AA:02', strength=90),
    ]
    picked = conn._match_ap(aps, b'Dup', 'wpa2', 'AA:AA:AA:AA:AA:01')
    require(picked['bssid'] == 'AA:AA:AA:AA:AA:01', 'duplicate SSIDs are disambiguated by BSSID')
    require(conn._match_ap(aps, b'Dup', 'wpa2', '', '')['bssid'] == 'AA:AA:AA:AA:AA:02',
            'without a BSSID the strongest duplicate is selected')
    require(conn._match_ap(aps, b'Dup', 'wpa2', '', '/org/freedesktop/NetworkManager/AccessPoint/999') is None,
            'a wrong/untrusted AP path is rejected')
    require(conn._match_ap(aps, b'Dup', 'wpa3', '', '') is None,
            'security mismatch is rejected instead of downgraded')
    require(conn._match_ap(aps, b'Missing', 'wpa2', '', '') is None,
            'a missing AP is not invented')

    # Async stage mapping: a D-Bus reply is never "online".
    require(mod.NetworkManagerConnector.connection_stage(50, False, False, False, 1) == 'associating',
            'association is reported separately')
    require(mod.NetworkManagerConnector.connection_stage(100, False, False, False, 1) == 'activated',
            'activated without an address is not online')
    require(mod.NetworkManagerConnector.connection_stage(100, True, False, False, 1) == 'ip',
            'address without a route is stage ip')
    require(mod.NetworkManagerConnector.connection_stage(100, True, True, False, 1) == 'route',
            'route without DNS is stage route')
    require(mod.NetworkManagerConnector.connection_stage(100, True, True, True, 1) == 'dns',
            'DNS without NM full connectivity is stage dns')
    require(mod.NetworkManagerConnector.connection_stage(100, True, True, True, 4) == 'online',
            'only NM full connectivity is stage online')
    require(mod.NetworkManagerConnector.connection_stage(120, False, False, False, 1) == 'failed',
            'failed association is reported as failed')

    class WrongKey(Exception):
        def get_dbus_name(self):
            return 'org.freedesktop.NetworkManager.SecretAgent.NoSecrets'
    wrong = conn._wifi_error(WrongKey('psk=supersecret'), 'supersecret')
    require(wrong['error_code'] == 'authentication-failed' and 'supersecret' not in str(wrong),
            'wrong-key errors are classified and the password is redacted')

    src = BRIDGE.read_text()
    require(", '/new')" not in src and ', \"/new\")' not in src and
            'AddAndActivateConnection' in src and "dbus.ObjectPath(ap['ap_path'])" in src,
            'bridge uses the resolved AP object path, never the guessed /new path')
    require('def connection_stage' in src and 'def _resolve_ap' in src,
            'bridge has testable AP resolution and stage logic')

    api = API_PY.read_text()
    require('NetworkWifiConnect2' in api and 'params.get("ap_path"' in api and 'params.get("bssid"' in api,
            'HTTP RPC transports ap_path/bssid/device to the bridge')
    settings = SETTINGS.read_text()
    require('selected.ap_path' in settings and 'selected.ssid_hex' in settings and 'selected.bssid' in settings,
            'Settings transports the selected AP identity, not only SSID text')
    require('selectedAp' in settings and 'ap.ap_path' in settings,
            'duplicate SSIDs stay individually selectable')

    nav = NAV.read_text()
    require('native-nav-present' in nav and 'navdock-state' in nav and 'exactly one DOM fallback' in nav,
            'navigation has one DOM fallback and defers to the native dock')
    kb = KB.read_text()
    require('_showFallback' in kb and '_discardFallback' in kb and 'native-provider-active' in kb,
            'in-page keyboard is only revealed after a native-provider probe')
    require('if (this.nativeProvider) return false;' not in kb,
            'native provider no longer disables the probe itself')
    lock = LOCK.read_text()
    require('lockscreen-active' in lock and '_blurInputs' in lock,
            'locking blurs text-input focus and marks the security surface')
    lockcss = LOCKCSS.read_text()
    require('lockscreen-lockhead-motion' in lockcss and 'animation-play-state: paused' in lockcss,
            'lockhead wiggle is pausable during drag/display-off')
    index = (ROOT / 'pwa/nuxel-home/index.html').read_text()
    require('id="lockscreen-lockhead" class="lockscreen-lockhead-motion"' in index,
            'wiggle transform lives on the nested artwork, not the drag container')
    require('body.display-off *' in STYLE.read_text() and 'animation-play-state: paused' in STYLE.read_text(),
            'screen-off freezes decorative CSS animations')
    require('z-index:40' in LAUNCHER.read_text() and 'data-app-state="ACTIVE"] #dock' in LAUNCHER.read_text(),
            'Home shortcut dock sits behind app content and is not an app-time hit target')
    require('font-size:10.5px' in STATUSCSS.read_text() and 'battery-slot{width:50px' in STATUSCSS.read_text(),
            'inside-battery percentage is legible at phone scale')
    status = STATUS.read_text()
    require('batteryLevel = (Number.isFinite(level)' in status and 'level ?? 100' not in status,
            'status bar never fabricates 100% for an unknown battery')
    wlfb = (ROOT / 'tools/s10plus/a34/nuxel-wl-fb.c').read_text()
    require('while (!display_on)' in wlfb and 'frame_source_hash' in wlfb and 'present_skipped' in wlfb,
            'display bridge stops capture/blit while off and skips unchanged frames when on')
    require('nuxel-swipe-hint 1.8s' not in LOCKCSS.read_text(),
            'the always-on swipe hint no longer forces continuous compositing')
    mon = MONITOR.read_text()
    require('displayOff' in mon and 'N/A (shared RAM)' in mon,
            'system monitor pauses off-screen and labels unavailable shared GPU memory')
    metrics = METRICS.read_text()
    require('rows == 0' in metrics and 'unavailable_shared_memory' in metrics,
            'GPU memory header-only source is unavailable, not fake 0 MiB')
    print('ALL A47 SOURCE/UNIT TESTS PASSED')


if __name__ == '__main__':
    main()
