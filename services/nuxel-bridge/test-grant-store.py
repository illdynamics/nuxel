#!/usr/bin/env python3
"""Regression test for mixed grant and location-policy files.

No D-Bus daemon or phone is required.  The test calls the real loader with a
temporary permission directory and proves an unrelated boolean location policy
cannot stop the shared bridge provider from starting.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
sys.path.insert(0, SRC)


def install_stubs():
    dbus = types.ModuleType('dbus')
    dbus.PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
    dbus.Boolean = bool
    dbus.SystemBus = lambda *a, **k: None
    dbus.Interface = lambda *a, **k: None
    dbus.types = types.SimpleNamespace(String=lambda value, **kwargs: value)
    dbus.exceptions = types.SimpleNamespace(DBusException=Exception,
                                             NameExistsException=Exception)
    service = types.ModuleType('dbus.service')
    service.Object = object
    service.BusName = object
    service.method = lambda *a, **k: (lambda fn: fn)
    service.signal = lambda *a, **k: (lambda fn: fn)
    dbus.service = service
    mainloop = types.ModuleType('dbus.mainloop')
    glib = types.ModuleType('dbus.mainloop.glib')
    glib.DBusGMainLoop = lambda *a, **k: None
    mainloop.glib = glib
    sys.modules.update({
        'dbus': dbus, 'dbus.service': service, 'dbus.exceptions': dbus.exceptions,
        'dbus.mainloop': mainloop, 'dbus.mainloop.glib': glib,
        'gi': types.ModuleType('gi'), 'gi.repository': types.ModuleType('gi.repository'),
    })
    sys.modules['gi.repository'].GLib = types.SimpleNamespace(MainLoop=lambda *a, **k: None)


def load_bridge():
    spec = importlib.util.spec_from_file_location(
        'nuxel_bridge_grant_store_under_test', os.path.join(SRC, 'bridge.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(condition, message, failures):
    print(('  OK   ' if condition else '  FAIL ') + message)
    if not condition:
        failures.append(message)


def main():
    install_stubs()
    bridge = load_bridge()
    failures = []
    with tempfile.TemporaryDirectory(prefix='nuxel-grants-') as directory:
        def write(name, value):
            with open(os.path.join(directory, name), 'w') as stream:
                json.dump(value, stream)

        write('location-policy.json', {'enabled': True, 'updated': 1.0})
        write('org.nuxel.Home.json', {
            'network:manage': {'duration': 'always'},
            'bluetooth:manage': True,
            'location:manage': False,
            'corrupt': 42,
        })
        write('not-an-object.json', ['not', 'a', 'grant-store'])
        original_dir = bridge.PERMISSIONS_DIR
        original_policy = os.environ.get('NUXEL_LOCATION_POLICY')
        try:
            bridge.PERMISSIONS_DIR = directory
            os.environ['NUXEL_LOCATION_POLICY'] = os.path.join(directory, 'location-policy.json')
            # The loader has no instance state: using an uninitialised object
            # proves only persisted data parsing, not D-Bus construction.
            got = bridge.NuxelBridgeService._load_all_grants(object())
        finally:
            bridge.PERMISSIONS_DIR = original_dir
            if original_policy is None:
                os.environ.pop('NUXEL_LOCATION_POLICY', None)
            else:
                os.environ['NUXEL_LOCATION_POLICY'] = original_policy

        check(got.get('org.nuxel.Home', {}).get('network:manage') == 'always',
              'object-form network grant is retained', failures)
        check(got.get('org.nuxel.Home', {}).get('bluetooth:manage') == 'always',
              'legacy true grant is retained safely', failures)
        check('location:manage' not in got.get('org.nuxel.Home', {}),
              'false grant is not elevated', failures)
        check('location-policy' not in got and 'enabled' not in got,
              'location policy is never parsed as an application grant', failures)
        check('not-an-object' not in got,
              'non-object JSON is ignored without aborting bridge startup', failures)
    print('\n' + ('ALL PASS' if not failures else '%d FAILURES' % len(failures)))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
