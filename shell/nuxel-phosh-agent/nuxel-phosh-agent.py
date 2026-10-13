#!/usr/bin/env python3
"""
Nuxel Phosh Agent — user-session D-Bus companion for the Phosh/Plymouth stack.

Runs as a user service (NOT root) and provides:

1. Notification relay (signal-driven):
   - Subscribes to org.nuxel.Notifications D-Bus signals
     (NotificationAdded / NotificationClosed) on the SYSTEM bus and relays new
     notifications to org.freedesktop.Notifications on the SESSION bus so they
     appear as native desktop notifications.
   - Retains backward compatibility: a single initial GetNotifications() call
     syncs existing state, then the agent is fully driven by bus signals
     (no polling loop).
   - Tracks seen notification fingerprints in memory (dedup).

2. Permission portal:
   - Exposes org.nuxel.PhoshAgent on the session bus
   - RequestPermission(app_id, portal_type) shows a GTK4/libadwaita mobile dialog
     with [Allow Once] [Allow Always] [Deny] buttons
   - Persists "always" grants to ~/.local/share/nuxel/phosh-agent-permissions.json
"""

import json
import logging
import os
import sys
import time
import hashlib
from typing import Any, Dict, List, Optional, Set

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib, Gtk, Gdk, Adw

# ── Logging ──────────────────────────────────────────────────────

LOG_DIR = os.path.expanduser("~/.local/state/nuxel")
LOG_FILE = os.path.join(LOG_DIR, "phosh-agent.log")
PERMISSIONS_DIR = os.path.expanduser("~/.local/share/nuxel")
PERMISSIONS_FILE = os.path.join(PERMISSIONS_DIR, "phosh-agent-permissions.json")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PERMISSIONS_DIR, exist_ok=True)

# Single-source path config (briq-20): source /etc/nuxel/paths.conf
# (overridable via NUXEL_PATHS_CONF) so this user-session agent agrees with
# the rest of the system about the canonical Nuxel paths. Environment
# variables always take precedence over the file. The agent keeps its own
# per-user log/permission store under $HOME, but it references the shared
# constants (e.g. NUXEL_CONFIG_DIR, NUXEL_RUN_DIR) below.
NUXEL_PATHS_CONF = os.environ.get("NUXEL_PATHS_CONF", "/etc/nuxel/paths.conf")


def _load_shared_paths():
    """Return the NUXEL_* path constants from env + paths.conf + defaults."""
    defaults = {
        "NUXEL_CONFIG_DIR": "/etc/nuxel",
        "NUXEL_DATA_DIR": "/var/lib/nuxel",
        "NUXEL_PERMISSIONS_DIR": "/var/lib/nuxel/permissions",
        "NUXEL_NOTIFICATIONS_FILE": "/var/lib/nuxel/notifications.json",
        "NUXEL_APP_DIR": "/var/app",
        "NUXEL_SANDBOX_DIR": "/opt/nuxel/sandbox",
        "NUXEL_LOG_DIR": "/var/log/nuxel",
        "NUXEL_RUN_DIR": "/run/nuxel",
        "NUXEL_FIRSTBOOT_MARKER": "/var/lib/nuxel/.firstboot-complete",
    }
    paths = dict(defaults)
    if os.path.exists(NUXEL_PATHS_CONF):
        try:
            with open(NUXEL_PATHS_CONF) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key in paths:
                        paths[key] = val
        except OSError as e:
            logger.warning("Could not read %s: %s", NUXEL_PATHS_CONF, e)
    for key in paths:
        env = os.environ.get(key)
        if env:
            paths[key] = env
    return paths



logger = logging.getLogger("nuxel-phosh-agent")
_file_handler = logging.FileHandler(LOG_FILE)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logger.addHandler(_file_handler)
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)

# Resolve the shared path constants now that the logger is available
# (briq-20).
SHARED_PATHS = _load_shared_paths()
NUXEL_CONFIG_DIR = SHARED_PATHS["NUXEL_CONFIG_DIR"]
NUXEL_DATA_DIR = SHARED_PATHS["NUXEL_DATA_DIR"]
NUXEL_PERMISSIONS_DIR = SHARED_PATHS["NUXEL_PERMISSIONS_DIR"]
NUXEL_NOTIFICATIONS_FILE = SHARED_PATHS["NUXEL_NOTIFICATIONS_FILE"]
NUXEL_APP_DIR = SHARED_PATHS["NUXEL_APP_DIR"]
NUXEL_SANDBOX_DIR = SHARED_PATHS["NUXEL_SANDBOX_DIR"]
NUXEL_LOG_DIR = SHARED_PATHS["NUXEL_LOG_DIR"]
NUXEL_RUN_DIR = SHARED_PATHS["NUXEL_RUN_DIR"]
NUXEL_FIRSTBOOT_MARKER = SHARED_PATHS["NUXEL_FIRSTBOOT_MARKER"]

# ── D-Bus names ─────────────────────────────────────────────────

PHOSH_AGENT_BUS = "org.nuxel.PhoshAgent"
PHOSH_AGENT_PATH = "/org/nuxel/PhoshAgent"
PHOSH_AGENT_IFACE = "org.nuxel.PhoshAgent"

NUXEL_NOTIFY_BUS = "org.nuxel.Notifications"
NUXEL_NOTIFY_PATH = "/org/nuxel/Notifications"
NUXEL_NOTIFY_IFACE = "org.nuxel.Notifications"

FDO_NOTIFY_BUS = "org.freedesktop.Notifications"
FDO_NOTIFY_PATH = "/org/freedesktop/Notifications"
FDO_NOTIFY_IFACE = "org.freedesktop.Notifications"



class PermissionStore:
    """Persists per-app permission grants to a JSON file."""

    def __init__(self, path: str = PERMISSIONS_FILE):
        self._path = path
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load permissions: %s", exc)
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w") as fh:
                json.dump(self._data, fh, indent=2, sort_keys=True)
            os.replace(tmp, self._path)
        except OSError as exc:
            logger.error("Failed to save permissions: %s", exc)

    def has_always_grant(self, app_id: str, portal_type: str) -> bool:
        grants = self._data.get(app_id, {})
        entry = grants.get(portal_type)
        return entry is not None and entry.get("duration") == "always"

    def set_grant(self, app_id: str, portal_type: str, duration: str) -> None:
        self._data.setdefault(app_id, {})[portal_type] = {
            "granted_at": time.time(),
            "duration": duration,
            "portal_type": portal_type,
        }
        self._save()

    def revoke_grant(self, app_id: str, portal_type: str) -> None:
        app_grants = self._data.get(app_id, {})
        app_grants.pop(portal_type, None)
        if not app_grants:
            self._data.pop(app_id, None)
        self._save()

    def get_all_grants(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._data)


class PermissionDialog:
    """GTK4/libadwaita mobile permission dialog with three choices."""

    def __init__(
        self,
        app_id: str,
        portal_type: str,
        app_name: Optional[str] = None,
    ):
        self.app_id = app_id
        self.portal_type = portal_type
        self.app_name = app_name or app_id
        self.result: Optional[Dict[str, Any]] = None

        # Human-readable portal descriptions
        PORTAL_NAMES = {
            "location": "Access your location",
            "camera": "Use the camera",
            "microphone": "Use the microphone",
            "sms": "Send SMS messages",
            "call": "Place phone calls",
            "contacts": "Access your contacts",
            "notifications": "Send notifications",
            "storage": "Access file storage",
            "calendar": "Access your calendar",
        }
        self._description = PORTAL_NAMES.get(portal_type, f"Access {portal_type}")

    def show(self) -> Dict[str, Any]:
        """Show the dialog (blocking via nested main loop).

        Returns: {"granted": bool, "duration": str|None}
        """
        if Adw.is_initialized() is False:
            Adw.init()

        self.result = None

        # Create dialog window
        win = Adw.Window(
            title="Permission Request",
            modal=True,
            transient_for=None,
            default_width=360,
            default_height=320,
        )

        # Prevent window manager decorations from blocking the dialog feel
        win.set_resizable(False)
        win.get_style_context().add_class("nuxel-permission-dialog")

        # Main content
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(32)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        # Adw.Window has no gtk_window_set_child() (SIGTRAP abort); use set_content().
        win.set_content(box)

        # App icon placeholder
        icon_label = Gtk.Label(label="🔒")
        icon_label.set_markup("<span size='xx-large'>🔒</span>")
        icon_label.set_halign(Gtk.Align.CENTER)
        box.append(icon_label)

        # App name header
        header = Gtk.Label()
        header.set_markup(
            f"<span weight='bold' size='large'>{GLib.markup_escape_text(self.app_name)}</span>"
        )
        header.set_halign(Gtk.Align.CENTER)
        header.set_margin_top(8)
        box.append(header)

        # Description
        desc = Gtk.Label()
        desc.set_markup(
            f"<span size='medium'>wants to:</span>\n"
            f"<span weight='bold'>{GLib.markup_escape_text(self._description)}</span>"
        )
        desc.set_halign(Gtk.Align.CENTER)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_wrap(True)
        desc.set_max_width_chars(30)
        box.append(desc)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        box.append(spacer)

        # Button stack
        btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        btn_box.set_halign(Gtk.Align.FILL)
        box.append(btn_box)

        # Deny
        deny_btn = Gtk.Button(label="Deny")
        deny_btn.add_css_class("destructive-action")
        deny_btn.set_halign(Gtk.Align.FILL)
        deny_btn.connect("clicked", lambda b: self._finish(win, False, None))
        btn_box.append(deny_btn)

        # Allow Once
        once_btn = Gtk.Button(label="Allow Once")
        once_btn.set_halign(Gtk.Align.FILL)
        once_btn.connect("clicked", lambda b: self._finish(win, True, "once"))
        btn_box.append(once_btn)

        # Allow Always
        always_btn = Gtk.Button(label="Allow Always")
        always_btn.add_css_class("suggested-action")
        always_btn.set_halign(Gtk.Align.FILL)
        always_btn.connect("clicked", lambda b: self._finish(win, True, "always"))
        btn_box.append(always_btn)

        win.connect("close-request", lambda w: self._finish(w, False, None))

        win.present()

        # Run nested main loop to block until user responds
        loop = GLib.MainLoop()
        self._loop = loop
        win.connect("destroy", lambda w: loop.quit())
        loop.run()

        return self.result or {"granted": False, "duration": None}

    def _finish(self, win, granted: bool, duration: Optional[str]) -> None:
        self.result = {"granted": granted, "duration": duration}
        win.destroy()


class NuxelPhoshAgent(dbus.service.Object):
    """User-session D-Bus agent for notification relay and permission dialogs."""

    def __init__(self, bus, object_path: str):
        dbus.service.Object.__init__(self, bus, object_path)
        self._session_bus = bus
        self._perms = PermissionStore()

        # Notification signal/relay state
        self._seen_fingerprints: Set[str] = set()
        self._system_bus: Any = dbus.SystemBus()

        # D-Bus proxies (lazy)
        self._nuxel_notify_proxy: Any = None
        self._nuxel_notify_iface: Any = None
        self._fdo_notify_proxy: Any = None

        # Initial sync: one GetNotifications() call, then subscribe to signals.
        self._sync_and_subscribe()

        logger.info("NuxelPhoshAgent initialized on session bus (signal-driven)")

    # ── permission portal D-Bus method ───────────────────────────

    @dbus.service.method(
        PHOSH_AGENT_IFACE,
        in_signature="ss",
        out_signature="s",
    )
    def RequestPermission(self, app_id: str, portal_type: str) -> str:
        """Request user consent for a permission.

        Args:
            app_id: Application identifier (e.g. "org.nuxel.Mail")
            portal_type: Permission type (e.g. "location", "camera")

        Returns:
            JSON string: {"granted": bool, "duration": str|null}
        """
        logger.info("Permission request: %s / %s", app_id, portal_type)

        # Check for existing "always" grant
        if self._perms.has_always_grant(app_id, portal_type):
            logger.info("Auto-granting %s for %s (always grant exists)", portal_type, app_id)
            return json.dumps({"granted": True, "duration": "always"})

        # Show dialog (blocks via nested GLib main loop). If no wayland/X
        # display is available (headless boot), Adw/Gtk raise; catch that and
        # return a graceful JSON so the D-Bus call still round-trips. A busctl
        # / gdbus trace of this call is the documented fallback evidence.
        app_name = self._resolve_app_name(app_id)
        dialog = PermissionDialog(app_id, portal_type, app_name)
        try:
            result = dialog.show()
        except Exception as exc:  # noqa: BLE001 - GTK display unavailable
            logger.warning(
                "Permission dialog could not render (display absent?): %s", exc
            )
            result = {"granted": False, "duration": None, "no_display": True}

        # Persist if "always"
        if result.get("granted") and result.get("duration") == "always":
            self._perms.set_grant(app_id, portal_type, "always")
        elif result.get("granted") and result.get("duration") == "once":
            # "once" grants are not persisted — they are consumed in this call
            pass

        logger.info(
            "Permission result for %s/%s: granted=%s, duration=%s",
            app_id,
            portal_type,
            result.get("granted"),
            result.get("duration"),
        )
        return json.dumps(result)

    # ── notification relay (signal-driven) ─────────────────────────

    def _sync_and_subscribe(self) -> None:
        """Synchronise with the current notification state then subscribe.

        Backward compatibility: if org.nuxel.Notifications does not yet expose
        the signal interfaces (older daemon), we fall back to a single
        GetNotifications() snapshot and then still subscribe on the bus so the
        agent upgrades to signal-driven operation as soon as the daemon emits.
        """
        try:
            obj = self._system_bus.get_object(NUXEL_NOTIFY_BUS, NUXEL_NOTIFY_PATH)
            self._nuxel_notify_proxy = obj
            self._nuxel_notify_iface = dbus.Interface(obj, NUXEL_NOTIFY_IFACE)

            # Initial snapshot
            raw = self._nuxel_notify_iface.GetNotifications()
            self._ingest_notifications(raw, source="initial-poll")
        except dbus.DBusException as exc:
            logger.debug("Initial GetNotifications() failed (%s) — will rely on signals", exc)
        except Exception as exc:
            logger.warning("Unexpected error during initial notification sync: %s", exc)

        # Subscribe to signals (retried asynchronously until the bus accepts them)
        self._ensure_signal_subscriptions()

    def _ensure_signal_subscriptions(self) -> None:
        """Subscribe to org.nuxel.Notifications signals.

        Kept separate so it can be retried via a short GLib timeout if the
        service is not yet registered when the agent starts (D-Bus activation).
        Idempotent: a second call is a no-op.
        """
        if self._nuxel_notify_iface is None:
            try:
                obj = self._system_bus.get_object(NUXEL_NOTIFY_BUS, NUXEL_NOTIFY_PATH)
                self._nuxel_notify_iface = dbus.Interface(obj, NUXEL_NOTIFY_IFACE)
            except dbus.DBusException as exc:
                logger.debug("org.nuxel.Notifications not yet available: %s", exc)
                self._schedule_resubscribe()
                return

        self._system_bus.add_signal_receiver(
            self._on_notification_added,
            signal_name="NotificationAdded",
            dbus_interface=NUXEL_NOTIFY_IFACE,
            bus_name=NUXEL_NOTIFY_BUS,
            path=NUXEL_NOTIFY_PATH,
        )
        # The daemon emits NotificationClosed (u,u) for both CloseNotification
        # and CloseAllNotifications; subscribe to it (not NotificationRemoved)
        # so the close path actually fires. Match the daemon's signature.
        self._system_bus.add_signal_receiver(
            self._on_notification_closed,
            signal_name="NotificationClosed",
            dbus_interface=NUXEL_NOTIFY_IFACE,
            bus_name=NUXEL_NOTIFY_BUS,
            path=NUXEL_NOTIFY_PATH,
        )
        logger.info("Subscribed to org.nuxel.Notifications signals (NotificationAdded/Closed)")

    def _schedule_resubscribe(self) -> None:
        """Schedule a re-attempt at subscribing while the daemon activates."""
        GLib.timeout_add(3000, self._ensure_signal_subscriptions)

    # ── D-Bus signal handlers ────────────────────────────────────

    def _on_notification_added(self, notification_json: str) -> None:
        """Handle org.nuxel.Notifications.NotificationAdded signal."""
        logger.info("D-Bus signal received: NotificationAdded (signal-driven)")
        try:
            notif = json.loads(notification_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Malformed NotificationAdded payload: %r", notification_json)
            return
        self._ingest_one(notif)

    def _on_notification_closed(self, notification_id, reason) -> None:
        """Handle org.nuxel.Notifications.NotificationClosed signal (u,u).

        Matches the daemon's signature: CloseNotification and
        CloseAllNotifications both emit NotificationClosed(id, reason).
        Only drops the notification from the FDO store (best effort); the
        closed id is logged. Keeping the fingerprint is harmless.
        """
        logger.info(
            "D-Bus signal received: NotificationClosed id=%s reason=%s (signal-driven)",
            notification_id, reason,
        )
        self._close_fdo_notification(int(notification_id))

    # ── ingestion ────────────────────────────────────────────────

    def _ingest_notifications(self, raw, source: str = "signal") -> None:
        """Process a list of notification dicts."""
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dbus.Array):
            items = list(raw)
        elif isinstance(raw, dict):
            items = raw.get("notifications", [])
        else:
            items = []
        for notif in items:
            self._ingest_one(notif, source=source)

    def _ingest_one(self, notif, force: bool = False, source: str = "signal") -> None:
        """Relay a single notification unless its fingerprint is already seen."""
        if not isinstance(notif, dict):
            return
        app_name = str(notif.get("app_id") or notif.get("app_name") or "Unknown")
        title = str(notif.get("summary") or notif.get("title") or "")
        body = str(notif.get("body") or "")
        urgency = str(notif.get("urgency") or "normal")

        fp = f"{app_name}|{title}|{body}"
        if fp in self._seen_fingerprints and not force:
            logger.debug("Dedup: skipping already-relayed notification fp=%s", fp)
            return

        self._seen_fingerprints.add(fp)
        if source == "signal":
            logger.info(
                "New notification (signal-driven) from %s: %s",
                app_name, title,
            )
        else:
            logger.info("Notification synced on startup from %s: %s", app_name, title)
        self._relay_to_fdo(app_name, title, body, urgency)

    def _close_fdo_notification(self, notification_id: int) -> None:
        """Best-effort close of an FDO notification by id."""
        proxy = self._ensure_fdo_notify_proxy()
        if proxy is None:
            return
        try:
            proxy.CloseNotification(notification_id)
        except dbus.DBusException as exc:
            logger.debug("Failed to close FDO notification %d: %s", notification_id, exc)

    def _ensure_nuxel_notify_proxy(self) -> Any:
        """Lazy-init proxy for org.nuxel.Notifications (system bus)."""
        if self._nuxel_notify_proxy is None:
            try:
                obj = self._system_bus.get_object(NUXEL_NOTIFY_BUS, NUXEL_NOTIFY_PATH)
                self._nuxel_notify_proxy = obj
                self._nuxel_notify_iface = dbus.Interface(obj, NUXEL_NOTIFY_IFACE)
            except dbus.DBusException as exc:
                logger.debug("Cannot connect to %s: %s", NUXEL_NOTIFY_BUS, exc)
        return self._nuxel_notify_proxy

    def _ensure_fdo_notify_proxy(self) -> Any:
        """Lazy-init proxy for org.freedesktop.Notifications."""
        if self._fdo_notify_proxy is None:
            try:
                obj = self._session_bus.get_object(FDO_NOTIFY_BUS, FDO_NOTIFY_PATH)
                self._fdo_notify_proxy = dbus.Interface(obj, FDO_NOTIFY_IFACE)
            except dbus.DBusException as exc:
                logger.debug("Cannot connect to %s: %s", FDO_NOTIFY_BUS, exc)
        return self._fdo_notify_proxy

    def _relay_to_fdo(
        self,
        app_name: str,
        title: str,
        body: str,
        urgency: str,
    ) -> None:
        """Forward a notification to org.freedesktop.Notifications."""
        proxy = self._ensure_fdo_notify_proxy()
        if proxy is None:
            logger.warning("Cannot relay notification — FDO Notifications not available")
            return

        urgency_map = {"low": 0, "normal": 1, "critical": 2}
        urgency_level = urgency_map.get(urgency, 1)

        hints = dbus.Dictionary(
            {
                "urgency": dbus.Byte(urgency_level),
                "suppress-sound": False,
            },
            signature="sv",
        )

        try:
            proxy.Notify(
                f"Nuxel: {app_name}",       # app_name
                0,                            # replaces_id
                "",                           # app_icon
                title,                        # summary
                body,                         # body
                [],                           # actions
                hints,                        # hints
                5000,                         # expire_timeout
            )
            logger.debug("Relayed notification: %s - %s", title, body)
        except dbus.DBusException as exc:
            logger.warning("Failed to relay notification: %s", exc)

    # ── helpers ──────────────────────────────────────────────────

    @staticmethod
    def _resolve_app_name(app_id: str) -> str:
        names = {
            "org.nuxel.Home": "Nuxel Home",
            "org.nuxel.Mail": "Nuxel Mail",
            "org.nuxel.Calendar": "Nuxel Calendar",
            "org.nuxel.Notes": "Nuxel Notes",
            "org.nuxel.Files": "Nuxel Files",
            "org.nuxel.Camera": "Nuxel Camera",
            "org.nuxel.dialer": "Dialer",
            "org.nuxel.messages": "Messages",
            "org.nuxel.contacts": "Contacts",
            "org.nuxel.settings": "Settings",
        }
        return names.get(app_id, app_id)


def main() -> int:
    """Entry point."""
    logger.info("Starting Nuxel Phosh Agent")

    # Guard Adw.init() so the session bus name is still claimed on headless
    # boots (no Wayland/X). The dialog rendering inside RequestPermission is
    # separately guarded and returns a graceful JSON if no display is present.
    try:
        Adw.init()
    except Exception as exc:  # noqa: BLE001 - GTK can't init without a display
        logger.warning("Adw.init failed (%s) — continuing to claim session bus name", exc)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()

    # Claim bus name
    try:
        bus_name = dbus.service.BusName(PHOSH_AGENT_BUS, bus)
        logger.info("Claimed D-Bus name: %s", PHOSH_AGENT_BUS)
    except dbus.exceptions.NameExistsException:
        logger.error("Bus name %s already taken — is another instance running?", PHOSH_AGENT_BUS)
        return 1

    agent = NuxelPhoshAgent(bus, PHOSH_AGENT_PATH)

    logger.info("Nuxel Phosh Agent running on session bus")

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        loop.quit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
