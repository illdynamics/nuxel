"""Nuxel Home — D-Bus Client

Wraps D-Bus calls to:
  - org.nuxel.Bridge     (GetCapabilities, GetAppCapabilities, CheckPermission)
  - org.nuxel.Portal     (GetPortalTypes, CheckPermission)
  - org.nuxel.Notifications (GetNotifications)

All calls are wrapped defensively — if the service isn't running or
the call fails, we log a warning and return sensible defaults.
"""

import json
import logging
from collections import namedtuple


logger = logging.getLogger(__name__)

try:
    from gi.repository import GLib
    HAVE_GLIB = True
except ImportError:
    HAVE_GLIB = False

try:
    import dbus
    import dbus.service  # noqa: F401
    import dbus.mainloop.glib
    HAVE_DBUS = True
except ImportError:
    HAVE_DBUS = False

# ── Typed result containers ──────────────────────────────────────

CapabilityInfo = namedtuple("CapabilityInfo", ["id", "name", "description", "risk"])
NotificationInfo = namedtuple("NotificationInfo", ["app_name", "title", "body", "urgency"])
PortalTypeInfo = namedtuple("PortalTypeInfo", ["name", "available"])

# ── Bus names & paths ────────────────────────────────────────────

BRIDGE_BUS = "org.nuxel.Bridge"
BRIDGE_PATH = "/org/nuxel/Bridge"
BRIDGE_IFACE = "org.nuxel.Bridge"

PORTAL_BUS = "org.nuxel.Portal"
PORTAL_PATH = "/org/nuxel/Portal"
PORTAL_IFACE = "org.nuxel.Portal"

NOTIFY_BUS = "org.nuxel.Notifications"
NOTIFY_PATH = "/org/nuxel/Notifications"
NOTIFY_IFACE = "org.nuxel.Notifications"


class NuxelDBusClient:
    """Thin wrapper around D-Bus calls to Nuxel services."""

    def __init__(self):
        self._system = None   # System bus
        self._session = None  # Session bus
        self._initialized_system = False
        self._initialized_session = False
        self._init_dbus()

    def _init_dbus(self):
        if not HAVE_DBUS or not HAVE_GLIB:
            logger.warning("dbus/GLib not available — D-Bus calls disabled")
            return
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            # Initialize system bus
            try:
                self._system = dbus.SystemBus()
                self._initialized_system = True
                logger.debug("D-Bus system bus connected")
            except Exception as exc:
                logger.warning("Failed to connect to D-Bus system bus: %s", exc)
            # Initialize session bus as fallback
            try:
                self._session = dbus.SessionBus()
                self._initialized_session = True
                logger.debug("D-Bus session bus connected")
            except Exception as exc:
                logger.warning("Failed to connect to D-Bus session bus: %s", exc)
        except Exception as exc:
            logger.warning("Failed to set up D-Bus main loop: %s", exc)

    def _get_bus(self, prefer_session=False):
        """Return the appropriate bus, trying system first then session."""
        if prefer_session and self._initialized_session:
            return self._session
        if self._initialized_system:
            return self._system
        if self._initialized_session:
            return self._session
        return None

    def _json_decode(self, data):
        """Safely JSON-decode a D-Bus result that may be a string."""
        if isinstance(data, str):
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return data
        if isinstance(data, dbus.String):
            try:
                return json.loads(str(data))
            except (json.JSONDecodeError, TypeError):
                return str(data)
        # For other D-Bus types, try to convert
        try:
            return json.loads(str(data))
        except (json.JSONDecodeError, TypeError):
            return {}

    # ── Bridge ───────────────────────────────────────────────────

    def bridge_get_capabilities(self):
        """Return list of CapabilityInfo from org.nuxel.Bridge."""
        bus = self._get_bus()
        if bus is None:
            return []
        try:
            proxy = bus.get_object(BRIDGE_BUS, BRIDGE_PATH)
            iface = dbus.Interface(proxy, BRIDGE_IFACE)
            raw = iface.GetCapabilities()
            decoded = self._json_decode(raw)
            if isinstance(decoded, dict) and "capabilities" in decoded:
                raw = decoded["capabilities"]
            results = []
            for item in raw:
                if isinstance(item, dict):
                    results.append(CapabilityInfo(
                        id=str(item.get("id", "")),
                        name=str(item.get("name", item.get("id", ""))),
                        description=str(item.get("description", "")),
                        risk=str(item.get("risk", "medium")),
                    ))
            return results
        except Exception as exc:
            logger.debug("Bridge.GetCapabilities failed: %s", exc)
            return []

    def bridge_get_app_capabilities(self, app_id):
        """Return dict of {capability: state} for a given app."""
        bus = self._get_bus()
        if bus is None:
            return {}
        try:
            proxy = bus.get_object(BRIDGE_BUS, BRIDGE_PATH)
            iface = dbus.Interface(proxy, BRIDGE_IFACE)
            raw = iface.GetAppCapabilities(app_id)
            decoded = self._json_decode(raw)
            if isinstance(decoded, dict):
                return {str(k): str(v) for k, v in decoded.items()}
            return {}
        except Exception as exc:
            logger.debug("Bridge.GetAppCapabilities(%s) failed: %s", app_id, exc)
            return {}

    def bridge_check_permission(self, app_id, capability):
        """Return True if permission is granted, False otherwise."""
        bus = self._get_bus()
        if bus is None:
            return False
        try:
            proxy = bus.get_object(BRIDGE_BUS, BRIDGE_PATH)
            iface = dbus.Interface(proxy, BRIDGE_IFACE)
            raw = iface.CheckPermission(app_id, capability)
            decoded = self._json_decode(raw)
            if isinstance(decoded, dict):
                return bool(decoded.get("granted", False))
            return bool(raw)
        except Exception as exc:
            logger.debug("Bridge.CheckPermission(%s, %s) failed: %s", app_id, capability, exc)
            return False

    def bridge_request_permission(self, app_id, capability):
        """Request a permission from the user via the portal."""
        bus = self._get_bus()
        if bus is None:
            return False
        try:
            proxy = bus.get_object(BRIDGE_BUS, BRIDGE_PATH)
            iface = dbus.Interface(proxy, BRIDGE_IFACE)
            raw = iface.RequestPermission(app_id, capability)
            decoded = self._json_decode(raw)
            if isinstance(decoded, dict):
                return bool(decoded.get("granted", decoded.get("success", False)))
            return bool(raw)
        except Exception as exc:
            logger.debug("Bridge.RequestPermission(%s, %s) failed: %s", app_id, capability, exc)
            return False

    # ── Portal ───────────────────────────────────────────────────

    def portal_get_types(self):
        """Return list of PortalTypeInfo."""
        bus = self._get_bus()
        if bus is None:
            return []
        try:
            proxy = bus.get_object(PORTAL_BUS, PORTAL_PATH)
            iface = dbus.Interface(proxy, PORTAL_IFACE)
            raw = iface.GetPortalTypes()
            decoded = self._json_decode(raw)
            if isinstance(decoded, dict) and "portals" in decoded:
                raw = decoded["portals"]
            results = []
            for r in raw:
                if isinstance(r, dict):
                    results.append(PortalTypeInfo(
                        name=str(r.get("type", r.get("name", ""))),
                        available=bool(r.get("available", True)),
                    ))
            return results
        except Exception as exc:
            logger.debug("Portal.GetPortalTypes failed: %s", exc)
            return []

    def portal_check_permission(self, app_id, portal_type):
        """Check a portal-style permission by app_id and portal_type."""
        bus = self._get_bus()
        if bus is None:
            return False
        try:
            proxy = bus.get_object(PORTAL_BUS, PORTAL_PATH)
            iface = dbus.Interface(proxy, PORTAL_IFACE)
            raw = iface.CheckPermission(app_id, portal_type)
            decoded = self._json_decode(raw)
            if isinstance(decoded, dict):
                return bool(decoded.get("granted", False))
            return bool(raw)
        except Exception as exc:
            logger.debug("Portal.CheckPermission(%s, %s) failed: %s", app_id, portal_type, exc)
            return False

    # ── Notifications ────────────────────────────────────────────

    def notifications_get_all(self):
        """Return list of NotificationInfo from Notifications service."""
        bus = self._get_bus()
        if bus is None:
            return []
        try:
            proxy = bus.get_object(NOTIFY_BUS, NOTIFY_PATH)
            iface = dbus.Interface(proxy, NOTIFY_IFACE)
            raw = iface.GetNotifications()
            decoded = self._json_decode(raw)
            if isinstance(decoded, list):
                raw = decoded
            results = []
            for item in raw:
                if isinstance(item, dict):
                    results.append(NotificationInfo(
                        app_name=str(item.get("app_name", item.get("app_id", ""))),
                        title=str(item.get("title", item.get("summary", ""))),
                        body=str(item.get("body", "")),
                        urgency=str(item.get("urgency", "normal")),
                    ))
            return results
        except Exception as exc:
            logger.debug("Notifications.GetNotifications failed: %s", exc)
            return []

    def send_notification(self, app_id, summary, body):
        """Send a notification via the Notifications service. Returns success bool."""
        bus = self._get_bus()
        if bus is None:
            return False
        try:
            proxy = bus.get_object(NOTIFY_BUS, NOTIFY_PATH)
            iface = dbus.Interface(proxy, NOTIFY_IFACE)
            raw = iface.Notify(app_id, summary, body)
            decoded = self._json_decode(raw)
            if isinstance(decoded, dict):
                return bool(decoded.get("success", False))
            return bool(raw)
        except Exception as exc:
            logger.debug("Notifications.Notify failed: %s", exc)
            return False

    # ── New methods ──────────────────────────────────────────────

    def get_app_permissions(self, app_id):
        """Get all permissions for an app from the Portal service. Returns dict."""
        bus = self._get_bus()
        if bus is None:
            return {}
        try:
            proxy = bus.get_object(PORTAL_BUS, PORTAL_PATH)
            iface = dbus.Interface(proxy, PORTAL_IFACE)
            raw = iface.GetAppPermissions(app_id)
            decoded = self._json_decode(raw)
            if isinstance(decoded, dict):
                return decoded
            return {}
        except Exception as exc:
            logger.debug("Portal.GetAppPermissions(%s) failed: %s", app_id, exc)
            return {}

    def check_capability(self, app_id, capability):
        """Alias for bridge_check_permission — check if a capability is granted."""
        return self.bridge_check_permission(app_id, capability)

    def get_portal_types(self):
        """Alias for portal_get_types."""
        return self.portal_get_types()

    def check_portal_permission(self, app_id, portal_type):
        """Alias for portal_check_permission."""
        return self.portal_check_permission(app_id, portal_type)

    def get_notifications(self):
        """Alias for notifications_get_all."""
        return self.notifications_get_all()

    # ── Convenience ──────────────────────────────────────────────

    @property
    def connected(self):
        return (self._initialized_system and self._system is not None) or \
               (self._initialized_session and self._session is not None)
