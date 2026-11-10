"""PWNAGE-93000 regression tests.

Covers the four requested improvements without requiring the physical device:
icon-origin policy, speaker sound-mode rendering, the persistent notification
lifecycle/gesture contract, and the single-Back Home input cleanup.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Notification hub: real model/persistence/read/archive semantics
# ---------------------------------------------------------------------------

def _install_shims():
    dbus = types.ModuleType("dbus")
    service = types.ModuleType("dbus.service")
    mainloop = types.ModuleType("dbus.mainloop")
    glib_ml = types.ModuleType("dbus.mainloop.glib")
    exceptions = types.ModuleType("dbus.exceptions")

    class _Object:
        def __init__(self, *a, **k):
            pass

    def _deco(*a, **k):
        def deco(fn):
            return fn
        return deco

    class _DBusException(Exception):
        def __init__(self, *a, **k):
            super().__init__(*a)

    service.Object = _Object
    service.method = _deco
    service.signal = _deco
    mainloop.glib = glib_ml
    glib_ml.DBusGMainLoop = lambda *a, **k: None
    exceptions.DBusException = _DBusException

    dbus.service = service
    dbus.mainloop = mainloop
    dbus.exceptions = exceptions
    dbus.UInt32 = int
    dbus.Int32 = int
    dbus.Int64 = int
    dbus.UInt64 = int
    dbus.Boolean = bool
    dbus.Double = float
    dbus.String = str
    dbus.Array = list
    dbus.SystemBus = lambda *a, **k: None
    dbus.SessionBus = lambda *a, **k: None

    gi = types.ModuleType("gi")
    repository = types.ModuleType("gi.repository")
    glib = types.ModuleType("gi.repository.GLib")
    glib.MainLoop = lambda *a, **k: object()
    glib.timeout_add = lambda *a, **k: 1
    glib.timeout_add_seconds = lambda *a, **k: 1
    glib.SOURCE_REMOVE = 0
    repository.GLib = glib
    gi.repository = repository

    for name in list(sys.modules):
        if name == "notifications" or name.startswith("dbus") or name.startswith("gi"):
            sys.modules.pop(name, None)
    sys.modules.update({
        "dbus": dbus,
        "dbus.service": service,
        "dbus.mainloop": mainloop,
        "dbus.mainloop.glib": glib_ml,
        "dbus.exceptions": exceptions,
        "gi": gi,
        "gi.repository": repository,
        "gi.repository.GLib": glib,
    })


def _notif_module(history_path):
    _install_shims()
    os.environ["NUXEL_NOTIFICATIONS_FILE"] = str(history_path)
    os.environ["NUXEL_NOTIFICATIONS_HISTORY_CAP"] = "200"
    sys.path.insert(0, str(ROOT / "services" / "nuxel-notifications" / "src"))
    module = importlib.import_module("notifications")
    importlib.reload(module)
    return module


def _service(module, records=None):
    svc = object.__new__(module.NuxelNotificationsService)
    svc._notifications = records or {}
    return svc


def test_notification_lifecycle_and_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        history = Path(tmp) / "notifications.json"
        mod = _notif_module(history)
        svc = _service(mod)

        res = json.loads(svc.SubmitNotification(json.dumps({
            "app_id": "org.example.GtkApp",
            "app_name": "Example GTK",
            "summary": "Build finished",
            "body": "All targets built",
            "icon": "/usr/share/icons/hicolor/scalable/apps/org.example.GtkApp.svg",
            "source": "freedesktop",
        })))
        assert res["success"] is True
        nid = res["id"]
        assert res["counts"]["unread"] == 1
        assert res["counts"]["active"] == 1

        listed = json.loads(svc.GetNotifications())
        assert [n["id"] for n in listed["notifications"]] == [nid]
        assert listed["notifications"][0]["app_name"] == "Example GTK"

        # Read keeps the reminder visible and drops the unread badge count.
        read = json.loads(svc.MarkRead(nid))
        assert read["success"] is True
        assert read["counts"]["unread"] == 0
        assert read["counts"]["active"] == 1
        remaining = json.loads(svc.GetNotifications())["notifications"]
        assert len(remaining) == 1 and remaining[0]["read_at"]

        # Archive hides it from the active list but keeps the durable record.
        archived = json.loads(svc.Archive(nid))
        assert archived["success"] is True
        assert archived["counts"]["active"] == 0
        assert archived["counts"]["archived"] == 1
        assert json.loads(svc.GetNotifications())["notifications"] == []
        assert len(json.loads(svc.GetAllNotifications())["notifications"]) == 1

        # A simulated daemon restart restores the read+archived state.
        svc2 = _service(mod)
        svc2._load_history()
        restored = json.loads(svc2.GetNotifications())
        assert restored["notifications"] == []
        all_restored = json.loads(svc2.GetAllNotifications())["notifications"]
        assert len(all_restored) == 1
        assert all_restored[0]["read_at"]
        assert all_restored[0]["archived_at"]


def test_notification_replacement_and_invalid_payload():
    with tempfile.TemporaryDirectory() as tmp:
        mod = _notif_module(Path(tmp) / "notifications.json")
        svc = _service(mod)
        first = json.loads(svc.SubmitNotification(json.dumps({
            "app_id": "org.example.App", "summary": "One", "body": "old",
        })))
        nid = first["id"]
        replaced = json.loads(svc.SubmitNotification(json.dumps({
            "app_id": "org.example.App", "summary": "Two", "body": "new",
            "replaces_id": nid,
        })))
        assert replaced["id"] == nid
        assert replaced["counts"]["total"] == 1
        assert json.loads(svc.GetNotifications())["notifications"][0]["summary"] == "Two"

        bad = json.loads(svc.SubmitNotification("{"))
        assert bad["success"] is False
        missing = json.loads(svc.SubmitNotification(json.dumps({"app_id": "", "summary": ""})))
        assert missing["success"] is False


def test_fdo_relay_is_present_and_forwards_to_hub():
    src = (ROOT / "services/nuxel-notifications/src/notifications.py").read_text()
    assert "class FdoNotificationRelay" in src
    assert "org.freedesktop.Notifications" in src
    for method in ("Notify", "CloseNotification", "GetCapabilities", "GetServerInformation"):
        assert "def " + method in src
    assert "SubmitNotification" in src
    assert "'replaces_id':" in src or '"replaces_id":' in src
    # One relay per real session bus is launched from the session script.
    session = (ROOT / "tools/s10plus/a45/nuxel-session.sh").read_text()
    assert "start_notification_relay" in session
    assert "notifications.py --session" in session
    assert "DBUS_SESSION_BUS_ADDRESS" in session


def test_bridge_exposes_read_archive_rpc():
    src = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    assert '("notifications", "mark-read")' in src
    assert '("notifications", "archive")' in src
    assert "def _notification_hub_call" in src
    assert "MarkRead" in src and "Archive" in src
    assert "GetNotifications" in src


# ---------------------------------------------------------------------------
# Icon-origin policy
# ---------------------------------------------------------------------------

def test_icon_policy_node_harness():
    script = ROOT / "tests/pwnage93000/test_icon_policy.js"
    proc = subprocess.run(["node", str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_registry_gtk_icons_point_at_original_desktop_icons():
    doc = json.loads((ROOT / "pwa/nuxel-common/app-registry.json").read_text())
    by_id = {a["id"]: a for a in doc["apps"]}
    for aid in ("org.gnome.FileRoller", "org.gnome.Loupe",
                "org.gnome.Papers", "org.gnome.SystemMonitor"):
        assert by_id[aid]["iconAsset"] == "/api/v1/apps/icon/" + aid
    # Native Nuxel artwork is still present for Nuxel's own apps.
    apps_js = (ROOT / "pwa/nuxel-home/js/apps.js").read_text()
    assert "'nuxel-dialer': '/assets/nuxel-applications-icon-pack/01-08_phone.png" in apps_js
    assert "'org.nuxel.Clock': '/assets/nuxel-applications-icon-pack/06-03_clock.png" in apps_js


def test_bridge_resolves_original_desktop_icon():
    src = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    assert "def resolve_desktop_icon" in src
    assert "/api/v1/apps/icon/" in src
    assert "mtime_ns" in src  # package update invalidates the cache
    apps_js = (ROOT / "pwa/nuxel-home/js/apps.js").read_text()
    assert "candidate.startsWith('/api/v1/')" in apps_js
    assert "'http://127.0.0.1:8080' + candidate" in apps_js
    assert "f.hidden=true;f.remove();" in apps_js


# ---------------------------------------------------------------------------
# Sound-mode icon
# ---------------------------------------------------------------------------

def test_sound_icon_is_speaker_with_three_distinct_modes():
    html = (ROOT / "pwa/nuxel-home/index.html").read_text()
    css = (ROOT / "pwa/nuxel-home/css/status-bar.css").read_text()
    js = (ROOT / "pwa/nuxel-home/js/status-bar.js").read_text()
    assert 'class="sound-glyph"' in html
    assert 'class="speaker-body"' in html
    for cls in ("vibrate-waves", "forbidden-line", "silent-cross", "sound-wave"):
        assert cls in html
    assert '#status-sound[data-mode="normal"] .sound-wave' in css
    assert '#status-sound[data-mode="vibrate"] .vibrate-waves' in css
    assert '#status-sound[data-mode="vibrate"] .forbidden-line' in css
    assert '#status-sound[data-mode="silent"] .forbidden-line' in css
    assert '#status-sound[data-mode="silent"] .silent-cross' in css
    assert 'Sound normal' in js and 'Vibrate mode' in js and 'Silent mode' in js
    sound_block = css[css.index('.status-right #status-sound {'):]
    sound_block = sound_block[:sound_block.index('/* Compact USB cable glyph')]
    assert 'background: currentColor' not in sound_block


# ---------------------------------------------------------------------------
# Notification UI placement + gestures
# ---------------------------------------------------------------------------

def test_notifications_render_below_qs_controls_in_expanded_panel():
    html = (ROOT / "pwa/nuxel-home/index.html").read_text()
    assert html.index('id="qs-details"') < html.index('id="qs-notifications"')
    assert 'id="qs-notifications-list"' in html
    assert "You're all caught up." in html
    qs = (ROOT / "pwa/nuxel-home/js/qs.js").read_text()
    sb = (ROOT / "pwa/nuxel-home/js/status-bar.js").read_text()
    assert "const notifications = document.getElementById('qs-notifications')" in qs
    assert "notifications.hidden = !on" in qs
    assert "data-notification-action" in sb
    assert "_markNotificationRead" in sb and "_archiveNotification" in sb
    assert "swipe left to archive · swipe right to mark read" in sb.lower()
    assert "Math.abs(gesture.dx) > Math.abs(gesture.dy) * 1.25" in sb
    assert "{ passive: true }" in sb  # never blocks panel scrolling


# ---------------------------------------------------------------------------
# Single-Back Home/input cleanup
# ---------------------------------------------------------------------------

def test_home_action_clears_fullscreen_before_minimizing():
    c = (ROOT / "tools/s10plus/a59/nuxel-foreign-toplevel.c").read_text()
    home = c[c.index('if (!strcmp(mode, "home"))'):]
    home = home[:home.index('if (!strcmp(mode, "focus")')]
    assert '/* unset_fullscreen */' in home
    assert '/* unset_maximized */' in home
    assert '/* set_minimized */' in home
    assert 'left_active' in home and 'left_fullscreen' in home


def test_bridge_home_action_verifies_convergence():
    src = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    assert "def _toplevel_snapshot" in src
    assert "converged" in src and "input_clear" in src
    assert "/run/nuxel/home-transition.json" in src
    assert "for attempt in range(3)" in src


def test_single_home_request_and_dom_input_check():
    app = (ROOT / "pwa/nuxel-home/js/app.js").read_text()
    assert "if (replacing) {" in app
    assert "home:backend converged=" in app
    assert "nuxel:home-ready" in app
    assert "def _verifyHomeInput" not in app  # JS, not Python
    assert "_verifyHomeInput()" in app
    assert "offenders=" in app


def test_single_back_falls_back_to_home_without_killing_app():
    app = (ROOT / "pwa/nuxel-home/js/app.js").read_text()
    assert "'back:native-' + status + '-home'" in app
    assert "_returnToHome('back-native-' + status)" in app
    assert "back:pwa-unsupported-home" in app
    assert "_returnToHome('back-pwa-unsupported')" in app
    # The fallback must never call the force-kill path.
    segment = app[app.index("'back:native-' + status + '-home'"):]
    segment = segment[:segment.index("back:native-pending")]
    assert "forceKill" not in segment and "terminateForeground" not in segment


def test_drawer_gesture_depends_on_visible_foreground_truth():
    gestures = (ROOT / "pwa/nuxel-home/js/gestures.js").read_text()
    assert "window.nuxel.isForegroundVisible && window.nuxel.isForegroundVisible()" in gestures
    assert "openDrawer" in gestures
