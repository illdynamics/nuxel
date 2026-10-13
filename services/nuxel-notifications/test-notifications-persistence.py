#!/usr/bin/env python3
"""Persistence-after-reload smoke test for the Nuxel notification daemon (briq-s2).

Verifies the on-disk JSON persistence contract without needing a live D-Bus
daemon:

  1. Delivered notifications are written to the canonical single-file path
     (/var/lib/nuxel/notifications.json by default, overridable via
     NUXEL_NOTIFICATIONS_FILE).
  2. A simulated service restart re-loads the file so notifications survive.
  3. NOTIFICATION_HISTORY_CAP eviction removes the oldest entries (lowest id)
     on both persist and reload.
  4. The module ID counter is bumped past the largest restored ID so freshly
     created notifications never collide with restored history IDs.

The module under test (notifications.py) imports `dbus` / `gi` at module level
for the live daemon; this test shims those with minimal fakes so the *actual*
persistence code paths (_persist_history / _load_history / _bump_id_counter)
are exercised directly.

Usage:
    python3 test-notifications-persistence.py
Exit code 0 on success, non-zero on failure.
"""

import importlib
import json
import os
import sys
import tempfile
import types

# ── Minimal dbus / gi fakes so notifications.py can be imported ─────────
def _install_shims():
    dbus = types.ModuleType("dbus")
    service = types.ModuleType("dbus.service")
    mainloop = types.ModuleType("dbus.mainloop")
    glib_ml = types.ModuleType("dbus.mainloop.glib")

    class _Object:
        def __init__(self, *a, **k):
            pass

    def _method(*a, **k):
        """Pass-through decorator; the method body is not executed in tests."""
        def deco(fn):
            return fn
        return deco

    def _signal(*a, **k):
        def deco(fn):
            return fn
        return deco

    service.Object = _Object
    service.method = _method
    service.signal = _signal
    mainloop.glib = glib_ml
    glib_ml.DBusGMainLoop = lambda *a, **k: None

    dbus.service = service
    dbus.mainloop = mainloop

    gi = types.ModuleType("gi")
    repository = types.ModuleType("gi.repository")
    glib = types.ModuleType("gi.repository.GLib")
    mainloop_fake = types.SimpleNamespace(MainLoop=lambda *a, **k: object())
    glib.MainLoop = mainloop_fake.MainLoop
    repository.GLib = glib
    gi.repository = repository

    sys.modules["dbus"] = dbus
    sys.modules["dbus.service"] = service
    sys.modules["dbus.mainloop"] = mainloop
    sys.modules["dbus.mainloop.glib"] = glib_ml
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repository
    sys.modules["gi.repository.GLib"] = glib


_install_shims()

# Locate notifications.py next to this test and import it for real.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "src")
sys.path.insert(0, _SRC)

import notifications as notif_mod  # noqa: E402


def _make_service(notifications=None):
    """Build a NuxelNotificationsService without a live D-Bus connection.

    Uses object.__new__ to skip __init__ (which needs a dbus service base),
    then seeds the live store so the persistence methods can be exercised.
    """
    svc = object.__new__(notif_mod.NuxelNotificationsService)
    svc._notifications = notifications if notifications is not None else {}
    return svc


def _make_notif(nid, app_id, summary):
    return {
        "id": nid,
        "app_id": app_id,
        "summary": summary,
        "body": "body-%d" % nid,
        "timestamp": "2026-08-12T00:00:00",
        "urgency": "normal",
    }


def check(cond, msg):
    if not cond:
        print("FAIL: " + msg)
        sys.exit(1)
    print("OK: " + msg)


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        history = os.path.join(tmp, "notifications.json")
        os.environ["NUXEL_NOTIFICATIONS_FILE"] = history
        os.environ.pop("NUXEL_NOTIFICATIONS_DIR", None)
        os.environ.pop("NUXEL_NOTIFICATIONS_HISTORY_FILE", None)
        os.environ["NUXEL_NOTIFICATIONS_HISTORY_CAP"] = "5"
        importlib.reload(notif_mod)

        cap = notif_mod.NOTIFICATION_HISTORY_CAP
        assert cap == 5, "expected cap pulled from env, got %r" % (cap,)
        assert notif_mod.HISTORY_FILE == history, \
            "expected HISTORY_FILE to follow NUXEL_NOTIFICATIONS_FILE, got %r" % (
                notif_mod.HISTORY_FILE,)
        # Canonical single-file default (briq-07): with no env overrides the
        # daemon resolves /var/lib/nuxel/notifications.json.
        for _k in ("NUXEL_NOTIFICATIONS_FILE", "NUXEL_NOTIFICATIONS_DIR",
                   "NUXEL_NOTIFICATIONS_HISTORY_FILE"):
            os.environ.pop(_k, None)
        importlib.reload(notif_mod)
        assert notif_mod.HISTORY_FILE == "/var/lib/nuxel/notifications.json", \
            "expected canonical default /var/lib/nuxel/notifications.json, got %r" % (
                notif_mod.HISTORY_FILE,)
        os.environ["NUXEL_NOTIFICATIONS_FILE"] = history
        os.environ["NUXEL_NOTIFICATIONS_HISTORY_CAP"] = "5"
        importlib.reload(notif_mod)

        # 1. Persist delivered notifications to the canonical file.
        svc = _make_service({
            1: _make_notif(1, "org.nuxel.Mail", "Hello"),
            2: _make_notif(2, "org.nuxel.Calendar", "Meeting"),
            3: _make_notif(3, "org.nuxel.Mail", "World"),
        })
        svc._persist_history()
        check(os.path.exists(history), "history file created at canonical path")
        with open(history) as fh:
            persisted = json.load(fh)
        check(isinstance(persisted, list), "history file is a JSON array")
        check(len(persisted) == 3, "all 3 notifications persisted")

        # 2. Simulated restart: a fresh instance reloads from disk.
        notif_mod._next_id = 1             # fresh counter "before restart"
        svc2 = _make_service()               # empty live store = "after restart"
        svc2._load_history()
        check(len(svc2._notifications) == 3, "restart restored 3 notifications")
        restored_ids = sorted(svc2._notifications.keys())
        check(restored_ids == [1, 2, 3], "restored notification IDs intact: %r" % restored_ids)

        # 3. New notifications after restart do not collide with restored IDs.
        fresh = notif_mod._make_id()
        check(fresh > max(restored_ids), "new ID %d > restored max %d (no collision)" % (
            fresh, max(restored_ids)))

        # 4. Cap eviction on persist removes oldest entries.
        for i in range(4, 10):               # adds ids 4..9 -> 9 entries total
            svc2._notifications[i] = _make_notif(i, "app.%d" % i, "Msg %d" % i)
        svc2._persist_history()
        with open(history) as fh:
            after_cap = json.load(fh)
        check(len(after_cap) == cap, "persist evicted entries down to cap %d" % cap)
        check(min(n["id"] for n in after_cap) == 5, "oldest kept id is 5 (oldest evicted)")
        check(max(n["id"] for n in after_cap) == 9, "newest kept id is 9")

        # 5. Cap eviction on reload also trims an oversized file.
        oversized = [_make_notif(i, "app", "m%d" % i) for i in range(1, 12)]
        with open(history, "w") as fh:
            json.dump(oversized, fh)
        svc3 = _make_service()
        svc3._load_history()
        check(len(svc3._notifications) == cap, "reload trimmed oversized history to cap %d" % cap)
        check(min(svc3._notifications.keys()) == 7, "reload evicted oldest ids, first kept = 7")

        # 6. Live in-memory store stays bounded after persist.
        check(len(svc2._notifications) <= cap, "live store bounded by cap after persist")

    print("\nAll notification persistence smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
