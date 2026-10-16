#!/usr/bin/env python3
"""Offline test for the Nuxel Portal permission policy (briq-04c).

The portal is a D-Bus daemon and the S10+ image is the only place it runs for
real, so this test exercises the part that is pure policy and has no bus
dependency: the persistent grant store and the timeout/pin invariants that the
unit file declares.

It imports services/nuxel-portal/src/portal.py with stub `dbus`/`gi` modules so
the file can be loaded on a host without python3-dbus or PyGObject. The stubs
are inert: nothing here is D-Bus, and the test never claims a bus round-trip.

    python3 services/nuxel-portal/test-portal-policy.py
"""

import importlib.util
import json
import os
import re
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
PORTAL_SRC = os.path.join(HERE, "src", "portal.py")
PORTAL_UNIT = os.path.join(HERE, "systemd", "nuxel-portal.service")
BRIDGE_UNIT = os.path.join(ROOT, "services", "nuxel-bridge", "systemd", "nuxel-bridge.service")


def _install_stubs():
    """Make portal.py importable without dbus/gi (inert stubs, no behaviour)."""
    def decorator(*_a, **_k):
        def wrap(fn):
            return fn
        return wrap

    dbus = types.ModuleType("dbus")
    service = types.ModuleType("dbus.service")

    class _Object:  # noqa: D401 - minimal stand-in for dbus.service.Object
        def __init__(self, *a, **k):
            pass

    service.Object = _Object
    service.method = decorator
    service.signal = decorator
    service.property = decorator
    service.BusName = object
    dbus.service = service
    dbus.SessionBus = lambda *a, **k: None
    dbus.SystemBus = lambda *a, **k: None
    dbus.exceptions = types.SimpleNamespace(NameExistsException=Exception)

    mainloop = types.ModuleType("dbus.mainloop")
    glib_loop = types.ModuleType("dbus.mainloop.glib")
    glib_loop.DBusGMainLoop = lambda *a, **k: None
    mainloop.glib = glib_loop
    dbus.mainloop = mainloop

    gi = types.ModuleType("gi")
    repo = types.ModuleType("gi.repository")

    class _GLib:
        @staticmethod
        def MainLoop(*_a, **_k):
            return types.SimpleNamespace(run=lambda: None, quit=lambda: None)

        @staticmethod
        def timeout_add(*_a, **_k):
            return 1

        @staticmethod
        def source_remove(*_a, **_k):
            return True

    repo.GLib = _GLib
    gi.repository = repo

    sys.modules.setdefault("dbus", dbus)
    sys.modules.setdefault("dbus.service", service)
    sys.modules.setdefault("dbus.mainloop", mainloop)
    sys.modules.setdefault("dbus.mainloop.glib", glib_loop)
    sys.modules.setdefault("gi", gi)
    sys.modules.setdefault("gi.repository", repo)


def load_portal(permissions_dir):
    _install_stubs()
    os.environ["NUXEL_PERMISSIONS_DIR"] = permissions_dir
    os.environ.pop("NUXEL_PORTAL_AUTO_GRANT", None)
    spec = importlib.util.spec_from_file_location("nuxel_portal_under_test", PORTAL_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def unit_env(path):
    out = {}
    for m in re.finditer(r"^Environment=([A-Za-z_][A-Za-z0-9_]*)=(.*)$", open(path).read(), re.M):
        out[m.group(1)] = m.group(2).strip()
    return out


def main():
    failures = []

    def check(cond, msg):
        if cond:
            print("  OK   %s" % msg)
        else:
            print("  FAIL %s" % msg)
            failures.append(msg)

    with tempfile.TemporaryDirectory() as tmp:
        portal = load_portal(tmp)
        store = portal.PermissionStore(tmp)

        print("[portal] default timeout + risk model")
        check(portal.PORTAL_TIMEOUT_SECONDS == 30.0,
              "default NUXEL_PORTAL_TIMEOUT_SECONDS is 30s (got %s)" % portal.PORTAL_TIMEOUT_SECONDS)
        check(portal.PORTAL_AUTO_GRANT is False, "auto-grant is OFF unless explicitly enabled")
        types_map = portal.PORTAL_DESCRIPTIONS
        check(isinstance(types_map, dict) and len(types_map) >= 10,
              "portal types declared (%d)" % len(types_map))
        for const in ("PORTAL_SMS", "PORTAL_CALL", "PORTAL_LOCATION", "PORTAL_CAMERA",
                      "PORTAL_MICROPHONE", "PORTAL_CONTACTS", "PORTAL_CALENDAR",
                      "PORTAL_BLUETOOTH", "PORTAL_USB", "PORTAL_BACKGROUND"):
            check(getattr(portal, const) in types_map, "portal type %s exists" % const)
        check(set(portal.PORTAL_RISK_LEVELS) == set(types_map),
              "every portal type carries a declared risk level (no unlabelled capability)")
        check(all(v in ("low", "medium", "high") for v in portal.PORTAL_RISK_LEVELS.values()),
              "risk levels are only low/medium/high")

        print("[portal] grant lifecycle")
        check(store.check_grants("org.nuxel.Mail", portal.PORTAL_SETTINGS) is False,
              "an app with no grants is denied")
        check(store.check_grants("org.nuxel.Mail", portal.PORTAL_SMS) is False,
              "denied on an unrelated portal type too")
        store.set_grant("org.nuxel.Mail", portal.PORTAL_SETTINGS, duration="session")
        check(store.check_grants("org.nuxel.Mail", portal.PORTAL_SETTINGS) is True,
              "a session grant is honoured")
        check(store.check_grants("org.nuxel.Mail", portal.PORTAL_SETTINGS) is True,
              "a session grant is reusable")
        store.set_grant("org.nuxel.Mail", portal.PORTAL_CAMERA, duration="once")
        check(store.check_grants("org.nuxel.Mail", portal.PORTAL_CAMERA) is True,
              "a one-shot grant is honoured once")
        check(store.check_grants("org.nuxel.Mail", portal.PORTAL_CAMERA) is False,
              "a one-shot grant is consumed (denied on second use)")
        store.set_grant("org.nuxel.Notes", portal.PORTAL_LOCATION, duration="always")
        check(store.has_always_grant("org.nuxel.Notes", portal.PORTAL_LOCATION) is True,
              "an 'always' grant is reported as persistent")
        check(store.has_always_grant("org.nuxel.Notes", portal.PORTAL_CAMERA) is False,
              "'always' is per portal type")
        store.revoke_grant("org.nuxel.Mail", portal.PORTAL_SETTINGS)
        check(store.check_grants("org.nuxel.Mail", portal.PORTAL_SETTINGS) is False,
              "revoked grant is denied again")

        print("[portal] persistence + path safety")
        store.set_grant("org.nuxel.Calendar", portal.PORTAL_CALENDAR, duration="always")
        reopened = portal.PermissionStore(tmp)
        check(reopened.check_grants("org.nuxel.Calendar", portal.PORTAL_CALENDAR) is True,
              "grants survive a daemon restart")
        check(reopened.check_grants("org.nuxel.Notes", portal.PORTAL_LOCATION) is True,
              "always grants survive a daemon restart")
        raw = json.load(open(reopened._app_path("org.nuxel.Calendar")))
        check(raw[portal.PORTAL_CALENDAR]["duration"] == "always", "on-disk grant records the duration")
        check("granted_at" in raw[portal.PORTAL_CALENDAR], "on-disk grant records granted_at")
        traversal = store._app_path("../../../etc/passwd")
        check(os.path.dirname(os.path.abspath(traversal)) == os.path.abspath(tmp),
              "an app id cannot escape the permissions directory (%s)" % os.path.basename(traversal))
        store.revoke_all("org.nuxel.Calendar")
        check(store.check_grants("org.nuxel.Calendar", portal.PORTAL_CALENDAR) is False,
              "revoke_all removes every grant for an app")

        print("[portal] request binding (no capability is granted without a decision)")
        svc = portal.NuxelPortalService.__new__(portal.NuxelPortalService)
        svc.permissions = store
        svc._inflight = {}
        try:
            import threading
            svc._inflight_lock = threading.Lock()
        except Exception:  # pragma: no cover
            pass
        raw = svc.CheckPermission("org.nuxel.Mail", portal.PORTAL_LOCATION)
        data = json.loads(raw)
        check(data.get("granted") is False or data.get("state") == "denied",
              "CheckPermission denies a capability that was never granted")

    print("[portal] unit invariants")
    penv = unit_env(PORTAL_UNIT)
    benv = unit_env(BRIDGE_UNIT)
    portal_to = float(penv.get("NUXEL_PORTAL_TIMEOUT_SECONDS", "0") or 0)
    bridge_to = float(benv.get("NUXEL_BRIDGE_DBUS_TIMEOUT_SECONDS", "0") or 0)
    check(portal_to > 0, "the unit pins NUXEL_PORTAL_TIMEOUT_SECONDS=%s" % penv.get("NUXEL_PORTAL_TIMEOUT_SECONDS"))
    if bridge_to:
        check(portal_to < bridge_to,
              "the consent window (%ss) is shorter than the bridge D-Bus timeout (%ss)" % (portal_to, bridge_to))
    active_lines = [ln.strip() for ln in open(PORTAL_UNIT)
                    if ln.strip() and not ln.strip().startswith("#")]
    check(not any(ln.startswith("AppArmorProfile=") for ln in active_lines),
          "no active AppArmorProfile= directive is claimed (4.14 does not provably enforce it)")
    check("WantedBy=multi-user.target" in open(PORTAL_UNIT).read(),
          "the portal is enabled into multi-user.target (a SYSTEM target)")

    if failures:
        print("\nFAILED: %d assertion(s)" % len(failures))
        return 1
    print("\nAll portal policy checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
