#!/usr/bin/env python3
"""
Nuxel Notifications — canonical notification hub.

The daemon runs on the SYSTEM bus as ``org.nuxel.Notifications`` and owns the
durable notification store at ``/var/lib/nuxel/notifications.json``.

It has two roles:

1. **System hub** (default): the single authoritative store used by the Home
   launcher, Quick Settings, Recents, the HTTP bridge and every Nuxel app.
2. **Session relay** (``--session``): exposes the freedesktop.org
   ``org.freedesktop.Notifications`` interface on a *session* bus and forwards
   every request to the system hub.  Native GTK and Flatpak (portal) apps call
   ``org.freedesktop.Notifications`` on their session bus, so this relay is what
   makes real application notifications reach Nuxel without creating a second
   competing store.

Canonical model
---------------
Every record supports: stable id, app id, app name, summary, body, timestamp,
received time, read timestamp, archived timestamp, urgency, icon, actions,
hints, source/provider and the freedesktop replacement id.

Lifecycle::

    RECEIVED -> ACTIVE_UNREAD
                  |  swipe right (MarkRead)   -> READ (still visible)
                  +  swipe left  (Archive)    -> ARCHIVED (hidden)
                  +  CloseNotification        -> removed from active store

The badge policy is: **unread, non-archived notifications**.  Read reminders stay
visible in the expanded Quick Settings list until archived.

Persistence survives Home/PWA reloads, the bridge restart, the notification
daemon restart and device reboot.  History is capped (default 200) so the store
cannot grow without bound.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

NUXEL_NOTIFICATIONS_VERSION = "0.9.3-beta"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('nuxel-notifications')

BUS_NAME = 'org.nuxel.Notifications'
OBJECT_PATH = '/org/nuxel/Notifications'
FDO_BUS_NAME = 'org.freedesktop.Notifications'
FDO_OBJECT_PATH = '/org/freedesktop/Notifications'

NUXEL_PATHS_CONF = os.environ.get("NUXEL_PATHS_CONF", "/etc/nuxel/paths.conf")
_LEGACY_NOTIFICATIONS_DIR_DEFAULT = '/var/lib/nuxel/notifications'


def _load_history_file():
    """Resolve the canonical notification history file path.

    Precedence (briq-07):
      1. NUXEL_NOTIFICATIONS_FILE environment variable
      2. legacy NUXEL_NOTIFICATIONS_HISTORY_FILE / NUXEL_NOTIFICATIONS_DIR
      3. NUXEL_NOTIFICATIONS_FILE in /etc/nuxel/paths.conf
      4. built-in default /var/lib/nuxel/notifications.json
    """
    canonical = '/var/lib/nuxel/notifications.json'
    env_file = os.environ.get('NUXEL_NOTIFICATIONS_FILE')
    if env_file:
        return env_file

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
# Hints are application metadata.  A single app (measured: ZapZap) can attach
# multi-megabyte hint payloads; persisting and emitting those as D-Bus signals
# bloats the store and can disconnect the hub.  Bound them at the hub boundary.
MAX_HINTS_BYTES = int(os.environ.get('NUXEL_NOTIFICATIONS_MAX_HINTS_BYTES', '65536') or '65536')


def _bounded_hints(hints):
    """Return JSON-safe hints within MAX_HINTS_BYTES.

    Oversized hints are replaced by a small provenance record so the hub never
    drops the notification itself and never emits a multi-megabyte signal.
    """
    if not isinstance(hints, dict):
        return {}
    try:
        safe = dict(hints)
        raw = json.dumps(safe, default=str)
    except (TypeError, ValueError):
        return {'nuxel.hints_error': 'unserializable'}
    if len(raw) <= MAX_HINTS_BYTES:
        return safe
    return {
        'nuxel.hints_truncated': True,
        'nuxel.hints_bytes': len(raw),
        'nuxel.hints_keys': sorted(str(k) for k in safe)[:24],
    }

DND_STATE_FILE = os.environ.get('NUXEL_DND_STATE', '/var/lib/nuxel/notifications/dnd.json')


def _dnd_active():
    try:
        with open(DND_STATE_FILE, 'r') as fh:
            doc = json.load(fh)
        if not isinstance(doc, dict):
            return False, None
        enabled = bool(doc.get('enabled', False))
        return enabled, (doc.get('reason') or ('manual' if enabled else 'off'))
    except (OSError, ValueError):
        return False, None


URGENCY_MAP = {'low': 0, 'normal': 1, 'critical': 2}
_next_id = 1


def _make_id():
    global _next_id
    nid = _next_id
    _next_id += 1
    return nid


def _bump_id_counter(new_minimum):
    global _next_id
    if new_minimum > _next_id:
        _next_id = new_minimum


def _utcnow_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _normalise_urgency(value):
    if isinstance(value, str):
        value = value.lower()
        if value in URGENCY_MAP:
            return value
    return 'normal'


def notification_dict(app_id, summary, body, urgency='normal', app_name=None,
                      icon=None, actions=None, hints=None, source='app',
                      replaces_id=None):
    """Create the canonical notification record."""
    now = _utcnow_iso()
    return {
        'id': _make_id(),
        'app_id': str(app_id),
        'app_name': str(app_name or app_id),
        'summary': str(summary),
        'body': str(body or ''),
        'timestamp': now,
        'received_at': now,
        'read_at': None,
        'archived_at': None,
        'urgency': _normalise_urgency(urgency),
        'icon': icon or '',
        'actions': list(actions or []),
        'hints': dict(hints or {}),
        'source': source or 'app',
        'replaces_id': replaces_id if isinstance(replaces_id, int) else None,
        'suppressed': False,
    }


class NuxelNotificationsService(dbus.service.Object):
    """System-bus notification hub implementing org.nuxel.Notifications."""

    def __init__(self, bus, object_path):
        dbus.service.Object.__init__(self, bus, object_path)
        self._notifications = {}
        self._load_history()
        logger.info("Nuxel Notifications hub started on system bus")

    # ---- persistence -----------------------------------------------------
    def _persist_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            entries = sorted(self._notifications.values(), key=lambda n: n.get('id', 0))
            if len(self._notifications) > NOTIFICATION_HISTORY_CAP:
                for nid in sorted(self._notifications.keys())[:len(self._notifications) - NOTIFICATION_HISTORY_CAP]:
                    self._notifications.pop(nid, None)
                entries = sorted(self._notifications.values(), key=lambda n: n.get('id', 0))
            tmp = HISTORY_FILE + '.tmp'
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as f:
                json.dump(entries, f, indent=2)
            os.replace(tmp, HISTORY_FILE)
            os.chmod(HISTORY_FILE, 0o600)
        except OSError as e:
            logger.error("Failed to persist notification history: %s", e)

    def _load_history(self):
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, 'r') as f:
                entries = json.load(f)
            if not isinstance(entries, list):
                return
            restored = {}
            max_id = 0
            migrated = False
            for notif in entries:
                if not isinstance(notif, dict):
                    continue
                try:
                    nid = int(notif.get('id', 0))
                except (TypeError, ValueError):
                    continue
                # Migrate pre-0.9 records in place.
                notif.setdefault('app_name', notif.get('app_id', ''))
                notif.setdefault('received_at', notif.get('timestamp'))
                notif.setdefault('read_at', None)
                notif.setdefault('archived_at', None)
                notif.setdefault('icon', '')
                notif.setdefault('actions', [])
                notif.setdefault('hints', {})
                notif.setdefault('source', 'app')
                notif.setdefault('urgency', 'normal')
                old_hints = notif.get('hints') or {}
                new_hints = _bounded_hints(old_hints)
                if new_hints != old_hints:
                    notif['hints'] = new_hints
                    migrated = True
                restored[nid] = notif
                if nid > max_id:
                    max_id = nid
            if max_id >= _next_id:
                _bump_id_counter(max_id + 1)
            total = len(restored)
            if total > NOTIFICATION_HISTORY_CAP:
                for nid in sorted(restored.keys())[:total - NOTIFICATION_HISTORY_CAP]:
                    restored.pop(nid, None)
            self._notifications = restored
            if migrated:
                self._persist_history()
                logger.info("Compacted oversized notification hints in history")
            logger.info("Loaded %d notification(s) from history", len(self._notifications))
        except (json.JSONDecodeError, OSError, ValueError, KeyError, NameError, TypeError) as e:
            logger.warning("Could not load notification history: %s", e)

    # ---- helpers ---------------------------------------------------------
    def _active(self):
        return [n for n in self._notifications.values() if not n.get('archived_at')]

    def _counts(self):
        active = self._active()
        unread = sum(1 for n in active if not n.get('read_at'))
        return {
            'active': len(active),
            'unread': unread,
            'read': len(active) - unread,
            'archived': len(self._notifications) - len(active),
            'total': len(self._notifications),
        }

    def _emit_changed(self):
        try:
            self.NotificationChanged(json.dumps(self._counts()))
        except Exception:  # pragma: no cover - signals must never break a call
            pass

    # ---- D-Bus API -------------------------------------------------------
    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def NotifyHistory(self):
        """Return the durable on-disk history as a JSON array."""
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
        """Simple Nuxel notification entry point."""
        return self.SubmitNotification(json.dumps({
            'app_id': app_id, 'app_name': app_id, 'summary': summary,
            'body': body, 'urgency': 'normal', 'source': 'nuxel-api',
        }))

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def SubmitNotification(self, payload):
        """Create or replace a notification from a JSON document.

        Supported keys: app_id, app_name, summary, body, urgency, icon,
        actions, hints, source, replaces_id, expire_timeout (seconds).
        """
        try:
            doc = json.loads(payload) if isinstance(payload, str) else dict(payload)
        except (TypeError, ValueError) as exc:
            logger.warning("SubmitNotification rejected invalid payload: %s", exc)
            return json.dumps({"success": False, "error": "invalid-json"})
        app_id = str(doc.get('app_id') or '').strip()
        summary = str(doc.get('summary') or '').strip()
        if not app_id or not summary:
            logger.warning("SubmitNotification called with empty app_id or summary")
            return json.dumps({"success": False, "error": "app_id and summary required"})

        replaces = doc.get('replaces_id')
        try:
            replaces = int(replaces) if replaces not in (None, '', 0, '0') else None
        except (TypeError, ValueError):
            replaces = None
        if replaces and replaces in self._notifications:
            notif = self._notifications[replaces]
            # A replacement keeps the id, read/archive state is reset because
            # the application has published new content.
            notif.update({
                'app_id': app_id,
                'app_name': str(doc.get('app_name') or app_id),
                'summary': summary,
                'body': str(doc.get('body') or ''),
                'timestamp': _utcnow_iso(),
                'received_at': _utcnow_iso(),
                'read_at': None,
                'archived_at': None,
                'urgency': _normalise_urgency(doc.get('urgency')),
                'icon': str(doc.get('icon') or ''),
                'actions': list(doc.get('actions') or []),
                'hints': _bounded_hints(doc.get('hints') or {}),
                'source': str(doc.get('source') or 'app'),
                'replaces_id': replaces,
            })
        else:
            notif = notification_dict(
                app_id, summary, doc.get('body') or '',
                urgency=doc.get('urgency') or 'normal',
                app_name=doc.get('app_name'),
                icon=doc.get('icon'),
                actions=doc.get('actions'),
                hints=_bounded_hints(doc.get('hints') or {}),
                source=doc.get('source') or 'app',
                replaces_id=replaces,
            )
            self._notifications[notif['id']] = notif

        dnd, dnd_reason = _dnd_active()
        notif['suppressed'] = bool(dnd)
        if dnd:
            notif['suppression_reason'] = 'dnd'
            notif['dnd_mode'] = dnd_reason
        else:
            notif.pop('suppression_reason', None)
            notif.pop('dnd_mode', None)

        logger.info("Notification #%d from %s: %s%s", notif['id'], app_id, summary,
                    " (DND suppressed)" if dnd else "")
        self.NotificationAdded(json.dumps(notif))
        self._persist_history()
        self._emit_changed()

        # Freedesktop expiry is an archive (history remains available).
        try:
            timeout = int(doc.get('expire_timeout') or 0)
        except (TypeError, ValueError):
            timeout = 0
        if timeout > 0:
            nid = notif['id']

            def _expire():
                rec = self._notifications.get(nid)
                if rec and not rec.get('archived_at'):
                    rec['archived_at'] = _utcnow_iso()
                    rec['expired'] = True
                    self._persist_history()
                    self.NotificationClosed(nid, 1)
                    self._emit_changed()
                return GLib.SOURCE_REMOVE

            GLib.timeout_add(timeout, _expire)

        return json.dumps({"success": True, "id": notif['id'], "suppressed": bool(dnd),
                           "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def GetNotifications(self):
        """Return active (non-archived) reminders, newest first, plus counts."""
        result = sorted(self._active(), key=lambda n: n.get('id', 0), reverse=True)
        return json.dumps({"success": True, "notifications": result,
                           "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def GetAllNotifications(self):
        """Return every durable record, newest first (diagnostics/history)."""
        result = sorted(self._notifications.values(), key=lambda n: n.get('id', 0), reverse=True)
        return json.dumps({"success": True, "notifications": result,
                           "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def GetNotificationCounts(self):
        return json.dumps({"success": True, "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='u', out_signature='s')
    def MarkRead(self, notification_id):
        rec = self._notifications.get(int(notification_id))
        if not rec:
            return json.dumps({"success": False, "error": "Notification not found"})
        if not rec.get('read_at'):
            rec['read_at'] = _utcnow_iso()
        logger.info("Notification #%d marked read", rec['id'])
        self._persist_history()
        self._emit_changed()
        return json.dumps({"success": True, "id": rec['id'], "read_at": rec['read_at'],
                           "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='u', out_signature='s')
    def MarkUnread(self, notification_id):
        rec = self._notifications.get(int(notification_id))
        if not rec:
            return json.dumps({"success": False, "error": "Notification not found"})
        rec['read_at'] = None
        logger.info("Notification #%d marked unread", rec['id'])
        self._persist_history()
        self._emit_changed()
        return json.dumps({"success": True, "id": rec['id'], "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='u', out_signature='s')
    def Archive(self, notification_id):
        rec = self._notifications.get(int(notification_id))
        if not rec:
            return json.dumps({"success": False, "error": "Notification not found"})
        if not rec.get('archived_at'):
            rec['archived_at'] = _utcnow_iso()
        logger.info("Notification #%d archived", rec['id'])
        self._persist_history()
        self.NotificationClosed(rec['id'], 2)
        self._emit_changed()
        return json.dumps({"success": True, "id": rec['id'],
                           "archived_at": rec['archived_at'], "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='u', out_signature='s')
    def Unarchive(self, notification_id):
        rec = self._notifications.get(int(notification_id))
        if not rec:
            return json.dumps({"success": False, "error": "Notification not found"})
        rec['archived_at'] = None
        logger.info("Notification #%d unarchived", rec['id'])
        self._persist_history()
        self._emit_changed()
        return json.dumps({"success": True, "id": rec['id'], "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='u', out_signature='s')
    def CloseNotification(self, notification_id):
        nid = int(notification_id)
        if nid not in self._notifications:
            return json.dumps({"success": False, "error": "Notification not found"})
        rec = self._notifications.pop(nid)
        logger.info("Notification #%d closed", rec['id'])
        self._persist_history()
        self.NotificationClosed(rec['id'], 3)
        self._emit_changed()
        return json.dumps({"success": True, "id": rec['id'], "counts": self._counts()})

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def CloseAllNotifications(self):
        count = len(self._notifications)
        ids = list(self._notifications.keys())
        logger.info("CloseAllNotifications ids=%s", ids)
        self._notifications.clear()
        self._persist_history()
        for nid in ids:
            self.NotificationClosed(nid, 3)
        self._emit_changed()
        return json.dumps({"success": True, "cleared": count})

    @dbus.service.signal(BUS_NAME, signature='s')
    def NotificationAdded(self, notification_json):
        pass

    @dbus.service.signal(BUS_NAME, signature='uu')
    def NotificationClosed(self, notification_id, reason):
        pass

    @dbus.service.signal(BUS_NAME, signature='s')
    def NotificationChanged(self, counts_json):
        pass


class FdoNotificationRelay(dbus.service.Object):
    """Session-bus org.freedesktop.Notifications -> system hub relay."""

    def __init__(self, bus, object_path=''):
        dbus.service.Object.__init__(self, bus, object_path or FDO_OBJECT_PATH)
        self._system = dbus.SystemBus()
        self._hub = dbus.Interface(
            self._system.get_object(BUS_NAME, OBJECT_PATH), BUS_NAME)
        try:
            self._system.add_signal_receiver(
                self._on_hub_closed, signal_name='NotificationClosed',
                dbus_interface=BUS_NAME, bus_name=BUS_NAME, path=OBJECT_PATH)
        except Exception as exc:  # pragma: no cover - best effort signal mirror
            logger.warning("FDO relay could not mirror hub signals: %s", exc)

    def _on_hub_closed(self, notification_id, reason):
        try:
            self.NotificationClosed(int(notification_id), int(reason))
        except Exception:
            pass

    @dbus.service.method(FDO_BUS_NAME, in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        if not summary:
            raise dbus.exceptions.DBusException('summary is required',
                                                name='org.freedesktop.Notifications.Error.Invalid')
        hint_doc = {}
        for key, value in (hints or {}).items():
            try:
                if isinstance(value, dbus.Boolean):
                    hint_doc[str(key)] = bool(value)
                elif isinstance(value, (dbus.Int32, dbus.UInt32, dbus.Int64, dbus.UInt64)):
                    hint_doc[str(key)] = int(value)
                elif isinstance(value, (dbus.Double,)):
                    hint_doc[str(key)] = float(value)
                elif isinstance(value, dbus.String):
                    hint_doc[str(key)] = str(value)
                else:
                    hint_doc[str(key)] = str(value)
            except Exception:
                continue
        doc = {
            'app_id': str(hint_doc.get('desktop-entry') or app_name or 'unknown'),
            'app_name': str(app_name or 'Application'),
            'summary': str(summary),
            'body': str(body or ''),
            'icon': str(app_icon or ''),
            'actions': [str(a) for a in (actions or [])],
            'hints': hint_doc,
            'urgency': str(hint_doc.get('urgency', 'normal')),
            'source': 'freedesktop',
            'replaces_id': int(replaces_id) if replaces_id else None,
            'expire_timeout': int(expire_timeout or 0),
        }
        try:
            result = json.loads(self._hub.SubmitNotification(json.dumps(doc)))
        except Exception as exc:
            logger.error("FDO relay could not submit notification: %s", exc)
            raise dbus.exceptions.DBusException(
                'Nuxel notification hub unavailable',
                name='org.freedesktop.Notifications.Error.Failed')
        if not result.get('success'):
            raise dbus.exceptions.DBusException(
                str(result.get('error') or 'not accepted'),
                name='org.freedesktop.Notifications.Error.Failed')
        return dbus.UInt32(int(result.get('id') or 0))

    @dbus.service.method(FDO_BUS_NAME, in_signature='u', out_signature='')
    def CloseNotification(self, notification_id):
        try:
            self._hub.CloseNotification(dbus.UInt32(int(notification_id)))
        except Exception as exc:
            logger.warning("FDO relay close %s failed: %s", notification_id, exc)

    @dbus.service.method(FDO_BUS_NAME, in_signature='', out_signature='as')
    def GetCapabilities(self):
        return dbus.Array(['body', 'body-markup', 'actions', 'persistence', 'icon-static'],
                          signature='s')

    @dbus.service.method(FDO_BUS_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return (dbus.String('Nuxel'), dbus.String('Nuxel'),
                dbus.String(NUXEL_NOTIFICATIONS_VERSION), dbus.String('1.2'))

    @dbus.service.method(FDO_BUS_NAME, in_signature='', out_signature='s')
    def GetNotifications(self):
        """Non-standard convenience used by Nuxel diagnostics."""
        return json.dumps(json.loads(self._hub.GetNotifications()))

    @dbus.service.signal(FDO_BUS_NAME, signature='uu')
    def NotificationClosed(self, notification_id, reason):
        pass

    @dbus.service.signal(FDO_BUS_NAME, signature='us')
    def ActionInvoked(self, notification_id, action_key):
        pass


def run_hub():
    logger.info("Starting Nuxel Notifications hub v%s...", NUXEL_NOTIFICATIONS_VERSION)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    try:
        # Keep the BusName object referenced for the whole process lifetime.
        # Dropping it releases the well-known name immediately while the service
        # process stays alive (measured: ServiceUnknown after restart).
        bus_name = dbus.service.BusName(BUS_NAME, bus)
        logger.info("Claimed D-Bus name: %s", BUS_NAME)
    except dbus.exceptions.NameExistsException:
        # Another instance is already serving the hub; this is not an error for
        # a restart race, but it must never silently create a second store.
        logger.error("Bus name %s already taken; refusing to start a second store", BUS_NAME)
        return 1
    NuxelNotificationsService(bus, OBJECT_PATH)
    logger.info("Nuxel Notifications hub running on system bus")
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.quit()
    return 0


def run_session_relay():
    logger.info("Starting Nuxel FDO notification relay v%s...", NUXEL_NOTIFICATIONS_VERSION)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    try:
        bus_name = dbus.service.BusName(FDO_BUS_NAME, bus, do_not_queue=True)
        logger.info("Claimed session D-Bus name: %s", FDO_BUS_NAME)
    except dbus.exceptions.NameExistsException:
        logger.error("Session bus %s already owned; the existing provider wins", FDO_BUS_NAME)
        return 1
    FdoNotificationRelay(bus)
    logger.info("Nuxel FDO notification relay running on session bus")
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        loop.quit()
    return 0


def main():
    parser = argparse.ArgumentParser(description='Nuxel notification hub / FDO relay')
    parser.add_argument('--session', action='store_true',
                        help='run the org.freedesktop.Notifications relay on the session bus')
    args = parser.parse_args()
    return run_session_relay() if args.session else run_hub()


if __name__ == '__main__':
    sys.exit(main())
