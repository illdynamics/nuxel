#!/usr/bin/env python3
"""G0 privilege-safety regressions for the root-owned HTTP bridge.

These tests are offline: they import the real identity and capability code
with lightweight D-Bus stubs. They fail closed on the exact defects the
PenGuru dual-runtime guide records:

  P0  development loopback bypass / unbound body app_id
  P1  once and session grants reusable from an in-memory cache
  P1  malformed once records elevated to a permanent grant
  P1  capability ids outside the canonical registry accepted
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, SRC)
CANONICAL = os.path.join(REPO, 'shell', 'nuxel-shell', 'nuxel-permissions',
                         'capabilities.json')

FAILURES = []


def check(condition, message):
    print(('  OK   ' if condition else '  FAIL ') + message)
    if not condition:
        FAILURES.append(message)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SRC, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_identity_boundary():
    print('[P0] body app_id is bound to the authenticated token identity')
    keyring = load_module('g0_keyring_api', 'keyring_api.py')
    good = {'app_id': 'org.nuxel.PenGuru', 'issuer': 'nuxel-launcher'}
    check(keyring.bind_request_identity(good, 'org.nuxel.PenGuru') is None,
          'launcher token and request identity agree')
    bad = keyring.bind_request_identity(good, 'org.nuxel.Home')
    check(isinstance(bad, dict) and bad.get('error') == 'identity_mismatch',
          'forged body app_id is rejected')
    unk = keyring.bind_request_identity(good, '')
    check(isinstance(unk, dict) and unk.get('error') == 'identity_required',
          'a request without an app identity is rejected')
    no_token = keyring.bind_request_identity(None, 'org.nuxel.PenGuru')
    check(isinstance(no_token, dict) and no_token.get('error') == 'token_required',
          'an unauthenticated request is rejected with token_required')
    check(isinstance(keyring.bind_request_identity('not-a-dict', 'x'), dict),
          'a malformed identity document is rejected')

    # Launcher-only app ids cannot be minted through the unauth bootstrap.
    check(keyring.bootstrap_app_allowed('org.nuxel.Vault') is False,
          'launcher-only Vault token cannot be self-bootstrapped')
    check(keyring.bootstrap_app_allowed('org.nuxel.Terminal') is True,
          'a normal first-party app may bootstrap a token')
    check(keyring.bootstrap_app_allowed('') is False,
          'empty app id cannot bootstrap a token')
    check(keyring.bootstrap_app_allowed('unknown', {'org.nuxel.PenGuru'}) is False,
          'an app id not present in the canonical registry is refused')


def test_http_auth_defaults():
    print('[P0] loopback is not an authentication bypass')
    src = open(os.path.join(SRC, 'api.py')).read()
    check("NUXEL_HTTP_MODE', 'dev'" not in src,
          'HTTP mode defaults to production, not dev')
    check('DEV_LOOPBACK_BYPASS' in src,
          'dev loopback bypass is explicit and double-gated')
    auth = src.split('def _verify_auth')[1][:1600]
    check("HTTP_MODE == 'dev' and DEV_LOOPBACK_BYPASS" in auth,
          'loopback is only trusted when both dev switches are set explicitly')
    check('self._bind_identity(app_id)' in src,
          'every POST binds body app_id to the token identity')
    check('_is_authority_rpc(body)' in src,
          'authority RPCs additionally require a launcher-bound token')


def _bridge_stub():
    dbus = types.ModuleType('dbus')
    dbus.PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
    dbus.Boolean = bool
    dbus.SystemBus = lambda *a, **k: None
    dbus.SessionBus = lambda *a, **k: None
    dbus.Interface = lambda *a, **k: None
    dbus.types = types.SimpleNamespace(String=lambda value, **kwargs: value,
                                       Boolean=bool)
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
    sys.modules['gi.repository'].GLib = types.SimpleNamespace(
        MainLoop=lambda *a, **k: None)
    return load_module('g0_bridge_under_test', 'bridge.py')


class FakePortal:
    def __init__(self, duration):
        self.duration = duration
        self.calls = 0

    def check_permission(self, app_id, capability):
        self.calls += 1
        if self.calls == 1:
            return {'granted': True, 'duration': self.duration}
        return {'granted': False, 'duration': None}


class FakeService:
    def __init__(self, portal):
        self.portals = portal
        self.capability_grants = {}
        self.capability_denies = {}
        self.session_id = 'daemon-session'
        self.capability_grant_info = {}

    def _grant_live(self, app_id, capability):
        return bridge.NuxelBridgeService._grant_live(self, app_id, capability)

    def _consume_once_grant(self, app_id, capability):
        return bridge.NuxelBridgeService._consume_once_grant(self, app_id, capability)

    def _save_grant(self, app_id, capability, duration='always'):
        return bridge.NuxelBridgeService._save_grant(self, app_id, capability, duration)

    def reload_grants(self):
        # Re-reads the real store with the same parser the daemon uses, then
        # refreshes the in-memory view; this mirrors the real method's shape
        # without constructing D-Bus state.
        self.capability_grants = bridge.NuxelBridgeService._load_all_grants(self)
        self.capability_denies = {
            app: {cap for cap, value in caps.items() if value == 'deny'}
            for app, caps in self.capability_grants.items()
        }
        return self.capability_grants


def test_grant_semantics():
    print('[P1] once/session grants are not reusable from the cache')
    global bridge
    bridge = _bridge_stub()

    portal = FakePortal('once')
    once = FakeService(portal)
    with tempfile.TemporaryDirectory() as d:
        old = bridge.PERMISSIONS_DIR
        old_seed = bridge.SEED_FIRST_PARTY_GRANTS
        bridge.PERMISSIONS_DIR = d
        bridge.SEED_FIRST_PARTY_GRANTS = False
        try:
            first = bridge.NuxelBridgeService._check_capability(
                once, 'org.nuxel.PenGuru', 'system:inspect')
            second = bridge.NuxelBridgeService._check_capability(
                once, 'org.nuxel.PenGuru', 'system:inspect')
            check(first is True, 'first once-granted action succeeds')
            check(second is False, 'second once-granted action fails in the same daemon lifetime')
            check('system:inspect' not in once.capability_grants.get('org.nuxel.PenGuru', {}),
                  'once grant is never installed in the reusable cache')
            on_disk = {}
            path = os.path.join(d, 'org.nuxel.PenGuru.json')
            if os.path.exists(path):
                on_disk = json.load(open(path))
                # refresh the in-memory view as a live daemon would before the
                # next request, so the second call proves persistence-level
                # non-reuse and not only the absence of a cache entry.
                once.reload_grants()
            check((on_disk.get('system_inspect') or on_disk.get('system:inspect') or {}).get('consumed') is True,
                  'once grant is persisted as consumed (auditable, not reusable)')
        finally:
            bridge.PERMISSIONS_DIR = old
            bridge.SEED_FIRST_PARTY_GRANTS = old_seed

    portal = FakePortal('session')
    sess = FakeService(portal)
    sess.session_id = 'session-A'
    with tempfile.TemporaryDirectory() as d:
        old = bridge.PERMISSIONS_DIR
        old_seed = bridge.SEED_FIRST_PARTY_GRANTS
        bridge.PERMISSIONS_DIR = d
        bridge.SEED_FIRST_PARTY_GRANTS = False
        try:
            check(bridge.NuxelBridgeService._check_capability(
                      sess, 'org.nuxel.PenGuru', 'system:inspect') is True,
                  'session grant succeeds in its session')
            check(bridge.NuxelBridgeService._check_capability(
                      sess, 'org.nuxel.PenGuru', 'system:inspect') is False,
                  'session grant is not treated as always within the cache')
            st = bridge.NuxelBridgeService._now_monotonic(sess)
            sess.session_id = 'session-B'
            sess._session_ended_at = {**getattr(sess, '_session_ended_at', {}),
                                      'session-A': st}
            check(bridge.NuxelBridgeService._check_capability(
                      sess, 'org.nuxel.PenGuru', 'system:inspect') is False,
                  'session grant cannot be replayed in another session')
        finally:
            bridge.PERMISSIONS_DIR = old
            bridge.SEED_FIRST_PARTY_GRANTS = old_seed

    portal = FakePortal('always')
    always = FakeService(portal)
    with tempfile.TemporaryDirectory() as d:
        old = bridge.PERMISSIONS_DIR
        old_seed = bridge.SEED_FIRST_PARTY_GRANTS
        bridge.PERMISSIONS_DIR = d
        bridge.SEED_FIRST_PARTY_GRANTS = False
        try:
            bridge.NuxelBridgeService._check_capability(
                always, 'org.nuxel.PenGuru', 'system:inspect')
            check(bridge.NuxelBridgeService._check_capability(
                      always, 'org.nuxel.PenGuru', 'system:inspect') is True,
                  'an explicit always grant remains reusable')
        finally:
            bridge.PERMISSIONS_DIR = old
            bridge.SEED_FIRST_PARTY_GRANTS = old_seed

    with tempfile.TemporaryDirectory() as d:
        old = bridge.PERMISSIONS_DIR
        old_seed = bridge.SEED_FIRST_PARTY_GRANTS
        bridge.PERMISSIONS_DIR = d
        bridge.SEED_FIRST_PARTY_GRANTS = False
        try:
            open(os.path.join(d, 'org.nuxel.PenGuru.json'), 'w').write(json.dumps({
                'system:inspect': True,
                'system:inspect-once': {'duration': 'once'},
                'system:inspect-session': {'duration': 'session'},
                'system:inspect-bogus': {'duration': 'sometimes'},
                'unknown:capability': {'duration': 'always'},
            }))
            got = bridge.NuxelBridgeService._load_all_grants(object())
            app = got.get('org.nuxel.PenGuru', {})
            check('system:inspect-once' not in app,
                  'persisted once grant is not loaded as reusable')
            check('system:inspect-session' not in app,
                  'ownership/session grant is not loaded as a permanent grant')
            check('system:inspect-bogus' not in app,
                  'unknown duration is denied, not elevated to always')
            check('unknown:capability' not in app,
                  'capability id outside the canonical registry is dropped')
            check(app.get('system:inspect') == 'always',
                  'legacy boolean grant remains a positive grant')
        finally:
            bridge.PERMISSIONS_DIR = old
            bridge.SEED_FIRST_PARTY_GRANTS = old_seed


def _canonical_ids():
    doc = json.load(open(CANONICAL))
    out = set()
    if isinstance(doc, dict):
        for entry in doc.get('capabilities') or []:
            if isinstance(entry, str):
                out.add(entry)
            elif isinstance(entry, dict) and isinstance(entry.get('id'), str):
                out.add(entry['id'])
                out.update(a for a in entry.get('aliases') or [] if isinstance(a, str))
    return out, doc


def test_capability_registry():
    print('[P1] one canonical capability registry')
    ids, _ = _canonical_ids()
    check(bool(ids), 'canonical capabilities.json is readable')
    for required in ('system_inspect', 'network', 'microphone'):
        check(required in ids, 'canonical registry declares %s' % required)
    api = open(os.path.join(SRC, 'api.py')).read()
    bridge_src = open(os.path.join(SRC, 'bridge.py')).read()
    check('NUXEL_PERMISSIONS_CAPABILITIES' in bridge_src and 'capabilities.json' in bridge_src,
          'bridge validates capability names against the canonical registry')
    check('_capability_known' in bridge_src,
          'unknown capability ids are denied explicitly')


def test_live_http_identity():
    print('[P0] live HTTP boundary (root bridge, forged/replayed identity)')
    import importlib.util as _ilu
    import threading
    import urllib.request
    import urllib.error
    from http.server import HTTPServer

    # DBus/GI/keyring stubs: this test exercises the HTTP authorization layer
    # and never claims a bus round-trip.
    _bridge_stub()
    stub = types.ModuleType('dbus')
    stub.PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
    stub.Boolean = bool
    stub.Interface = lambda *a, **k: None
    class _Bus:
        def get_object(self, *a, **k):
            raise RuntimeError('no bus')
    stub.SystemBus = lambda *a, **k: _Bus()
    stub.SessionBus = lambda *a, **k: _Bus()
    service = types.ModuleType('dbus.service')
    service.Object = object
    service.method = lambda *a, **k: (lambda fn: fn)
    service.signal = lambda *a, **k: (lambda fn: fn)
    stub.service = service
    stub.exceptions = types.SimpleNamespace(
        DBusException=Exception, NameExistsException=Exception)
    sys.modules['dbus'] = stub
    sys.modules['dbus.service'] = service
    sys.modules['dbus.exceptions'] = stub.exceptions
    sys.modules['gi'] = types.ModuleType('gi')
    sys.modules['gi.repository'] = types.ModuleType('gi.repository')
    sys.modules['gi.repository'].GLib = types.SimpleNamespace(
        MainLoop=lambda *a, **k: None, timeout_add=lambda *a, **k: 1)

    os.environ['NUXEL_HTTP_MODE'] = 'production'
    os.environ.pop('NUXEL_HTTP_DEV_LOOPBACK_BYPASS', None)
    spec = _ilu.spec_from_file_location('g0_api_live', os.path.join(SRC, 'api.py'))
    api = _ilu.module_from_spec(spec)
    spec.loader.exec_module(api)
    api.APP_REGISTRY_PATH = os.path.join(REPO, 'pwa', 'nuxel-common', 'app-registry.json')
    api._REGISTRY_APP_ID_CACHE = {'path': None, 'ids': set()}
    api.BridgeAPIHandler.server_token = None
    api.SESSION_TOKENS.clear()
    secret = 'a' * 64
    secret_file = tempfile.NamedTemporaryFile('w', delete=False)
    secret_file.write(secret)
    secret_file.close()
    api.KEYRING_LAUNCHER_SECRET_FILE = secret_file.name
    server = HTTPServer(('127.0.0.1', 0), api.BridgeAPIHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:%d' % port

    def call(path, payload, headers=None):
        req = urllib.request.Request(base + path, method='POST',
                                     data=json.dumps(payload).encode(),
                                     headers=dict({'Content-Type': 'application/json'},
                                                  **(headers or {})))
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, {'raw': raw}

    try:
        status, body = call('/api/v1/apps/activate',
                            {'app_id': 'org.nuxel.Home', 'target': 'org.nuxel.Terminal'})
        check(status == 401, 'unauthenticated loopback request is 401 (%s)' % status)

        status, body = call('/api/v1/auth/token', {'app_id': 'org.nuxel.Vault'})
        check(status == 403, 'Vault cannot self-bootstrap a token (%s)' % status)

        status, bootstrap = call('/api/v1/auth/token', {'app_id': 'org.nuxel.Terminal'})
        check(status == 200 and bool(bootstrap.get('token')),
              'first-party app bootstraps a token (%s %s)' % (status, bootstrap.get('error')))
        self_token = bootstrap.get('token')
        status, body = call('/api/v1/apps/activate',
                            {'app_id': 'org.nuxel.Home', 'target': 'org.nuxel.Terminal'},
                            {'Authorization': 'Bearer ' + self_token})
        check(status == 403 and body.get('error') == 'identity_mismatch',
              'self-bootstrapped token replayed as another app is rejected (%s %s)'
              % (status, body.get('error')))
        status, body = call('/api/v1/rpc',
                            {'app_id': 'org.nuxel.Terminal', 'namespace': 'keyring',
                             'verb': 'status', 'params': {}},
                            {'Authorization': 'Bearer ' + self_token})
        check(status == 403 and body.get('error') == 'launcher_token_required',
              'authority RPC refuses a self-bootstrapped token (%s %s)'
              % (status, body.get('error')))

        status, launched = call('/api/v1/auth/app-token', {'app_id': 'org.nuxel.Home'},
                                {'X-Nuxel-Launcher-Secret': secret})
        check(status == 200 and launched.get('token'),
              'launcher-secret token is issued (%s)' % status)
        launcher_token = launched.get('token')
        status, body = call('/api/v1/apps/activate',
                            {'app_id': 'org.nuxel.PenGuru', 'target': 'org.nuxel.Terminal'},
                            {'Authorization': 'Bearer ' + launcher_token})
        check(status == 403 and body.get('error') == 'identity_mismatch',
              'launcher token for Home cannot act as PenGuru (%s %s)'
              % (status, body.get('error')))
        status, body = call('/api/v1/apps/activate',
                            {'app_id': 'org.nuxel.Home', 'target': 'org.nuxel.NotAThing'},
                            {'Authorization': 'Bearer ' + launcher_token})
        check(status == 404 and body.get('error') == 'unknown_app',
              'the correctly bound launcher token reaches the handler (%s)' % status)
        # Native launch authority: a launcher token bound to a PWA may not
        # hand the host a native binary descriptor.
        status, launched_pwa = call('/api/v1/auth/app-token', {'app_id': 'org.nuxel.Terminal'},
                                    {'X-Nuxel-Launcher-Secret': secret})
        check(status == 200 and bool(launched_pwa.get('token')),
              'PWA launcher token is issued (%s %s)' % (status, launched_pwa.get('error')))
        pwa_token = launched_pwa.get('token')
        status, body = call('/api/v1/apps/activate',
                            {'app_id': 'org.nuxel.Terminal', 'target': 'org.mozilla.firefox'},
                            {'Authorization': 'Bearer ' + pwa_token})
        check(status == 403 and body.get('error') == 'launch_not_authorized',
              'a PWA-bound launcher token cannot start a native app (%s %s)'
              % (status, body.get('error')))
        check(api.launch_authorized('org.nuxel.Home',
                                    {'app_id': 'org.nuxel.Home', 'issuer': 'nuxel-launcher'},
                                    'production', False) is True,
              'Home with a launcher token may start native apps')
        check(api.launch_authorized('org.nuxel.Home',
                                    {'app_id': 'org.nuxel.Home', 'issuer': 'self-bootstrap'},
                                    'production', False) is False,
              'a self-bootstrapped Home token cannot start native apps')
        check(api.launch_authorized('org.nuxel.Terminal',
                                    {'app_id': 'org.nuxel.Terminal', 'issuer': 'nuxel-launcher'},
                                    'production', False) is False,
              'a PWA token cannot start native apps')

        status, body = call('/api/v1/usb-mode/set-mode', {'app_id': 'org.nuxel.Terminal',
                                                          'mode': 'charging'},
                            {'Authorization': 'Bearer ' + pwa_token})
        check(status == 403 and body.get('error') == 'capability_denied',
              'USB mode change requires the usb:access capability (%s %s)'
              % (status, body.get('error')))
    finally:
        server.shutdown()
        os.unlink(secret_file.name)


if __name__ == '__main__':
    test_identity_boundary()
    test_http_auth_defaults()
    test_grant_semantics()
    test_capability_registry()
    test_live_http_identity()
    print('\nALL PASS' if not FAILURES else '\n%d FAILURES' % len(FAILURES))
    raise SystemExit(1 if FAILURES else 0)
