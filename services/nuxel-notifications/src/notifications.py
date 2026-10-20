#!/usr/bin/env python3
"""
Nuxel Notifications — System notification daemon (Nuxel contract on system bus).

This daemon runs on the SYSTEM bus as org.nuxel.Notifications.
It stores notifications in memory and provides a simple JSON-based API
for the HTTP bridge and Phosh agent to consume.

No FDO spec methods. No PWA relay code. No threading.

## On-disk persistence (briq-07)

Delivered/active notifications are persisted to a single canonical JSON file so
a service restart does not lose history:

    /var/lib/nuxel/notifications.json

The canonical single-file location is documented in `configs/nuxel/` and
defaults to `/var/lib/nuxel/notifications.json`. It is resolved from (in order
of precedence):

  1. `NUXEL_NOTIFICATIONS_FILE` environment variable (highest precedence)
  2. legacy `NUXEL_NOTIFICATIONS_HISTORY_FILE` / `NUXEL_NOTIFICATIONS_DIR`
     (migration fallback for existing installs; kept so previously persisted
     history remains readable while it is re-written to the canonical file)
  3. built-in default `/var/lib/nuxel/notifications.json`

The store is capped at `NOTIFICATION_HISTORY_CAP` (default 200) entries, oldest
evicted first, on both persist and reload. Restart survival is guaranteed by
`_load_history()` on startup.
"""

import sys
import json
import logging
import os
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from datetime import datetime

NUXEL_NOTIFICATIONS_VERSION = "0.6.1-beta"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('nuxel-notifications')

BUS_NAME = 'org.nuxel.Notifications'
OBJECT_PATH = '/org/nuxel/Notifications'

# On-disk notification history store. Persists delivered/active notifications
# to a single canonical JSON file so that a service restart does not lose
# history. Capped at NOTIFICATION_HISTORY_CAP entries (oldest evicted first) to
# bound disk usage. The canonical single-file location (single source, briq-07)
# is /var/lib/nuxel/notifications.json. It is resolved via:
#   NUXEL_NOTIFICATIONS_FILE -> (legacy NUXEL_NOTIFICATIONS_HISTORY_FILE /
#   NUXEL_NOTIFICATIONS_DIR migration fallback) -> default
#     /var/lib/nuxel/notifications.json.
NUXEL_PATHS_CONF = os.environ.get("NUXEL_PATHS_CONF", "/etc/nuxel/paths.conf")

# Canonical single-file path (briq-07). Overridable via NUXEL_NOTIFICATIONS_FILE.
_LEGACY_NOTIFICATIONS_DIR_DEFAULT = '/var/lib/nuxel/notifications'


def _load_history_file():
    """Resolve the canonical notification history file path.

    Precedence (briq-07):
      1. NUXEL_NOTIFICATIONS_FILE environment variable
      2. legacy NUXEL_NOTIFICATIONS_HISTORY_FILE / NUXEL_NOTIFICATIONS_DIR
         (kept for migration so previously persisted history.json under
         /var/lib/nuxel/notifications/ remains readable)
      3. built-in default /var/lib/nuxel/notifications.json
    """
    canonical = '/var/lib/nuxel/notifications.json'
    env_file = os.environ.get('NUXEL_NOTIFICATIONS_FILE')
    if env_file:
        return env_file

    # Migration fallback: an existing install pinned the dir/history file.
    legacy_file = os.environ.get('NUXEL_NOTIFICATIONS_HISTORY_FILE')
    if legacy_file:
        return legacy_file
    legacy_dir = os.environ.get('NUXEL_NOTIFICATIONS_DIR')
    if legacy_dir:
        return os.path.join(legacy_dir, 'history.json')
    if os.path.exists(NUXEL_PATHS_CONF):
        try:
            with open(NUXEL_PATHS_CONF) as _f:
                for _line in _f:
                    _line = _line.strip()
                    if not _line or _line.startswith("#") or "=" not in _line:
                        continue
                    _k, _v = _line.split("=", 1)
                    if _k.strip() == "NUXEL_NOTIFICATIONS_FILE":
                        return _v.strip().strip('"').strip("'")
                    if _k.strip() == "NUXEL_NOTIFICATIONS_DIR":
                        legacy_dir = _v.strip().strip('"').strip("'")
        except OSError as _e:
            logger.warning("Could not read %s: %s", NUXEL_PATHS_CONF, _e)
        if legacy_dir:
            return os.path.join(legacy_dir, 'history.json')
    return canonical


HISTORY_FILE = _load_history_file()
NOTIFICATION_HISTORY_CAP = int(os.environ.get('NUXEL_NOTIFICATIONS_HISTORY_CAP', '200') or '200')

# Notification urgency map
URGENCY_MAP = {
    'low': 0,
    'normal': 1,
    'critical': 2,
}

# Auto-incrementing notification ID counter
_next_id = 1


def _make_id():
    global _next_id
    nid = _next_id
    _next_id += 1
    return nid


def _bump_id_counter(new_minimum):
    """Advance the module-level notification ID counter past a floor.

    Used when loading persisted history so freshly-created notification IDs
    never collide with IDs that were assigned before a restart. The counter is
    only ever moved forward; it is never reset below a previously-seen ID.
    """
    global _next_id
    if new_minimum > _next_id:
        _next_id = new_minimum


def notification_dict(app_id, summary, body, urgency='normal'):
    """Create a notification dictionary."""
    return {
        'id': _make_id(),
        'app_id': app_id,
        'summary': summary,
        'body': body,
        'timestamp': datetime.now().isoformat(),
        'urgency': urgency,
    }


class NuxelNotificationsService(dbus.service.Object):
    """System bus notification daemon implementing org.nuxel.Notifications."""

    def __init__(self, bus, object_path):
        dbus.service.Object.__init__(self, bus, object_path)
        self._notifications = {}  # {id: notification_dict}
        # Load any previously persisted history so a restart does not lose it.
        self._load_history()
        logger.info("Nuxel Notifications service started on system bus")

    def _persist_history(self):
        """Write the current notification store to the on-disk history file.

        Notifications are stored as a JSON array, capped at
        NOTIFICATION_HISTORY_CAP entries (oldest evicted first).
        """
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            entries = sorted(
                self._notifications.values(),
                key=lambda n: n.get('id', 0),
            )
            if len(entries) > NOTIFICATION_HISTORY_CAP:
                entries = entries[-NOTIFICATION_HISTORY_CAP:]
            # Evict oldest (lowest id) entries from the live store too so memory
            # stays bounded in agreement with the on-disk cap.
            if len(self._notifications) > NOTIFICATION_HISTORY_CAP:
                for nid in sorted(self._notifications.keys())[:len(self._notifications) - NOTIFICATION_HISTORY_CAP]:
                    self._notifications.pop(nid, None)
            tmp = HISTORY_FILE + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(entries, f, indent=2)
            os.replace(tmp, HISTORY_FILE)
        except OSError as e:
            logger.error("Failed to persist notification history: %s", e)

    def _load_history(self):
        """Load persisted notification history on startup (best effort)."""
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, 'r') as f:
                entries = json.load(f)
            if not isinstance(entries, list):
                return
            restored = {}
            max_id = 0
            for notif in entries:
                if not isinstance(notif, dict):
                    continue
                nid = int(notif.get('id', 0))
                restored[nid] = notif
                if nid > max_id:
                    max_id = nid
            # Advance the module-level counter past any restored id so new
            # notifications never collide with history.
            if max_id >= _next_id:
                _bump_id_counter(max_id + 1)
            total = len(restored)
            if total > NOTIFICATION_HISTORY_CAP:
                for nid in sorted(restored.keys())[:total - NOTIFICATION_HISTORY_CAP]:
                    restored.pop(nid, None)
            self._notifications = restored
            logger.info("Loaded %d notification(s) from history", len(self._notifications))
        except (json.JSONDecodeError, OSError, ValueError, KeyError, NameError, TypeError) as e:
            logger.warning("Could not load notification history: %s", e)

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def NotifyHistory(self):
        """Return the persisted notification history as a JSON array.

        This is the persisted on-disk history, capped at NOTIFICATION_HISTORY_CAP
        entries, and is NOT cleared by CloseAllNotifications (which only clears
        the live/active store).
        """
        entries = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    entries = json.load(f)
                if not isinstance(entries, list):
                    entries = []
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to read notification history: %s", e)
                entries = []
        return json.dumps({"success": True, "history": entries})

    @dbus.service.method(BUS_NAME, in_signature='sss', out_signature='s')
    def Notify(self, app_id, summary, body):
        """Send a notification.

        Args:
            app_id: Application identifier (e.g. 'org.nuxel.Calendar')
            summary: Notification title/summary
            body: Notification body text

        Returns:
            JSON string with success and notification id
        """
        if not summary or not app_id:
            logger.warning("Notify called with empty app_id or summary")
            return json.dumps({"success": False, "error": "app_id and summary required"})

        notif = notification_dict(app_id, summary, body)
        self._notifications[notif['id']] = notif

        logger.info("Notification #%d from %s: %s", notif['id'], app_id, summary)

        # Emit signal
        self.NotificationAdded(json.dumps(notif))
        self._persist_history()

        return json.dumps({"success": True, "id": notif['id']})

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def GetNotifications(self):
        """Return all stored notifications as a JSON list."""
        result = sorted(
            list(self._notifications.values()),
            key=lambda n: n['id'],
            reverse=True,
        )
        return json.dumps({"success": True, "notifications": result})

    @dbus.service.method(BUS_NAME, in_signature='u', out_signature='s')
    def CloseNotification(self, notification_id):
        """Close (remove) a single notification.

        Args:
            notification_id: Integer notification ID

        Returns:
            JSON string with success status
        """
        if notification_id in self._notifications:
            del self._notifications[notification_id]
            self.NotificationClosed(notification_id, 3)
            self._persist_history()
            logger.debug("Notification %d closed by request", notification_id)
            return json.dumps({"success": True, "id": notification_id})
        else:
            return json.dumps({"success": False, "error": "Notification not found"})

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def CloseAllNotifications(self):
        """Clear all stored notifications.

        Returns:
            JSON string with success status
        """
        count = len(self._notifications)
        for nid in list(self._notifications.keys()):
            self.NotificationClosed(nid, 3)
        self._notifications.clear()
        self._persist_history()
        logger.info("All notifications cleared (%d removed)", count)
        return json.dumps({"success": True, "cleared": count})

    @dbus.service.signal(BUS_NAME, signature='s')
    def NotificationAdded(self, notification_json):
        """Signal: a new notification was added."""
        pass

    @dbus.service.signal(BUS_NAME, signature='uu')
    def NotificationClosed(self, notification_id, reason):
        """Signal: a notification was closed.

        Args:
            notification_id: The ID of the closed notification
            reason: 1=expired, 2=dismissed by user, 3=closed by request
        """
        pass


def main():
    """Start the nuxel-notifications daemon on the system bus."""
    logger.info("Starting Nuxel Notifications v%s...", NUXEL_NOTIFICATIONS_VERSION)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    try:
        bus_name = dbus.service.BusName(BUS_NAME, bus)
        logger.info("Claimed D-Bus name: %s", BUS_NAME)
    except dbus.exceptions.NameExistsException:
        logger.error("Bus name %s already taken", BUS_NAME)
        sys.exit(1)

    service = NuxelNotificationsService(bus, OBJECT_PATH)

    logger.info("Nuxel Notifications running on system bus...")

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.quit()


if __name__ == '__main__':
    main()
