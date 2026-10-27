#!/usr/bin/env python3
"""
Nuxel Portal Daemon — System portal WITHOUT GTK.

Mediates ALL hardware access through the user-session PhoshAgent.
No GUI here — this is a system daemon that delegates user dialogs
to the Phosh agent running in the user session.

Architecture:
    Application (PWA/Flatpak)
        → nuxel-portal (system bus, non-GUI)
            → org.nuxel.PhoshAgent.RequestPermission (session bus)
                → GTK4/libadwaita dialog (Phosh agent)
            → nuxel-bridge (capability check)
                → System service (ModemManager, GeoClue, etc.)

Every portal request is forwarded to the PhoshAgent for user consent.
Per-app permission tracking with revocable grants.
"""

import sys
import os
import json
import logging
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import threading
import time
import uuid

# Configure logging
NUXEL_PORTAL_VERSION = "0.7.0-beta"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('nuxel-portal')

# D-Bus configuration
BUS_NAME = 'org.nuxel.Portal'
OBJECT_PATH = '/org/nuxel/Portal'
PHOSH_AGENT_BUS = 'org.nuxel.PhoshAgent'
PHOSH_AGENT_PATH = '/org/nuxel/PhoshAgent'
PHOSH_AGENT_IFACE = 'org.nuxel.PhoshAgent'
BRIDGE_BUS_NAME = 'org.nuxel.Bridge'

# Portal request timeout (seconds). When a permission request is forwarded to
# the PhoshAgent and no response arrives within this window, the request is
# automatically DENIED. Configurable via NUXEL_PORTAL_TIMEOUT_SECONDS.
try:
    PORTAL_TIMEOUT_SECONDS = float(os.environ.get('NUXEL_PORTAL_TIMEOUT_SECONDS', '30'))
except (TypeError, ValueError):
    PORTAL_TIMEOUT_SECONDS = 30.0
if PORTAL_TIMEOUT_SECONDS <= 0:
    PORTAL_TIMEOUT_SECONDS = 30.0

# Portal auto-grant (headless VM smoke test). When set to a truthy value, every
# permission request is granted immediately without prompting the PhoshAgent.
PORTAL_AUTO_GRANT = os.environ.get('NUXEL_PORTAL_AUTO_GRANT', '0') \
    not in ('', '0', 'false', 'False', 'no', 'NO')

# Permission storage - single-source path config (briq-20). Loads
# /etc/nuxel/paths.conf (overridable via NUXEL_PATHS_CONF); the
# NUXEL_PERMISSIONS_DIR environment variable takes highest precedence.
NUXEL_PATHS_CONF = os.environ.get("NUXEL_PATHS_CONF", "/etc/nuxel/paths.conf")
_permissions_override = os.environ.get("NUXEL_PERMISSIONS_DIR")
if _permissions_override:
    PERMISSIONS_DIR = _permissions_override
elif os.path.exists(NUXEL_PATHS_CONF):
    try:
        with open(NUXEL_PATHS_CONF) as _f:
            _paths = {}
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _v = _line.split("=", 1)
                _paths[_k.strip()] = _v.strip().strip('"').strip("'")
        PERMISSIONS_DIR = _paths.get("NUXEL_PERMISSIONS_DIR", "/var/lib/nuxel/permissions")
    except OSError as _e:
        logger.warning("Could not read %s: %s", NUXEL_PATHS_CONF, _e)
        PERMISSIONS_DIR = '/var/lib/nuxel/permissions'
else:
    PERMISSIONS_DIR = '/var/lib/nuxel/permissions'

# Portal types
PORTAL_SMS = 'sms'
PORTAL_CALL = 'call'
PORTAL_CONTACTS = 'contacts'
PORTAL_PHONE_STATUS = 'phone_status'
PORTAL_LOCATION = 'location'
PORTAL_CAMERA = 'camera'
PORTAL_MICROPHONE = 'microphone'
PORTAL_SETTINGS = 'settings'
PORTAL_CALENDAR = 'calendar'
PORTAL_BLUETOOTH = 'bluetooth'
PORTAL_USB = 'usb'
PORTAL_CLIPBOARD_READ = 'clipboard_read'
PORTAL_CLIPBOARD_WRITE = 'clipboard_write'
PORTAL_BACKGROUND = 'background'

PORTAL_DESCRIPTIONS = {
    PORTAL_SMS: 'Send SMS message',
    PORTAL_CALL: 'Place phone call',
    PORTAL_CONTACTS: 'Access contacts',
    PORTAL_PHONE_STATUS: 'Read phone status',
    PORTAL_LOCATION: 'Access GPS location',
    PORTAL_CAMERA: 'Use camera',
    PORTAL_MICROPHONE: 'Use microphone',
    PORTAL_SETTINGS: 'Change system settings',
    PORTAL_CALENDAR: 'Access your calendar',
    PORTAL_BLUETOOTH: 'Use Bluetooth',
    PORTAL_USB: 'Access USB devices',
    PORTAL_CLIPBOARD_READ: 'Read clipboard contents',
    PORTAL_CLIPBOARD_WRITE: 'Write to clipboard',
    PORTAL_BACKGROUND: 'Run in the background',
}


PORTAL_RISK_LEVELS = {
    PORTAL_SMS: 'high',
    PORTAL_CALL: 'high',
    PORTAL_CONTACTS: 'high',
    PORTAL_PHONE_STATUS: 'low',
    PORTAL_LOCATION: 'high',
    PORTAL_CAMERA: 'high',
    PORTAL_MICROPHONE: 'high',
    PORTAL_SETTINGS: 'medium',
    PORTAL_CALENDAR: 'medium',
    PORTAL_BLUETOOTH: 'medium',
    PORTAL_USB: 'medium',
    PORTAL_CLIPBOARD_READ: 'high',
    PORTAL_CLIPBOARD_WRITE: 'high',
    PORTAL_BACKGROUND: 'medium',
}

PORTAL_ICONS = {
    PORTAL_SMS: 'chat-symbolic',
    PORTAL_CALL: 'call-start-symbolic',
    PORTAL_CONTACTS: 'contacts-symbolic',
    PORTAL_PHONE_STATUS: 'network-cellular-signal-excellent-symbolic',
    PORTAL_LOCATION: 'mark-location-symbolic',
    PORTAL_CAMERA: 'camera-photo-symbolic',
    PORTAL_MICROPHONE: 'audio-input-microphone-symbolic',
    PORTAL_SETTINGS: 'preferences-system-symbolic',
    PORTAL_CALENDAR: 'office-calendar-symbolic',
    PORTAL_BLUETOOTH: 'bluetooth-symbolic',
    PORTAL_USB: 'drive-removable-media-symbolic',
    PORTAL_CLIPBOARD_READ: 'edit-paste-symbolic',
    PORTAL_CLIPBOARD_WRITE: 'edit-paste-symbolic',
    PORTAL_BACKGROUND: 'system-run-symbolic',
}


class PermissionStore:
    """Manages persistent permission grants."""

    def __init__(self, permissions_dir=PERMISSIONS_DIR):
        self.permissions_dir = permissions_dir
        os.makedirs(permissions_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _app_path(self, app_id):
        """Get the permissions file path for an app."""
        safe_id = app_id.replace('/', '_').replace('..', '_')
        return os.path.join(self.permissions_dir, f"{safe_id}.json")

    def get_grants(self, app_id):
        """Get all granted permissions for an app."""
        path = self._app_path(app_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read permissions for {app_id}: {e}")
            return {}

    def set_grant(self, app_id, portal_type, duration='session'):
        """Grant a permission for an app."""
        with self._lock:
            grants = self.get_grants(app_id)
            grants[portal_type] = {
                'granted_at': time.time(),
                'duration': duration,  # 'once', 'session', 'always'
                'portal_type': portal_type,
            }
            path = self._app_path(app_id)
            with open(path, 'w') as f:
                json.dump(grants, f, indent=2)
            logger.info(f"Granted {portal_type} to {app_id} (duration={duration})")

    def revoke_grant(self, app_id, portal_type):
        """Revoke a specific permission grant."""
        with self._lock:
            grants = self.get_grants(app_id)
            if portal_type in grants:
                del grants[portal_type]
                path = self._app_path(app_id)
                with open(path, 'w') as f:
                    json.dump(grants, f, indent=2)
                logger.info(f"Revoked {portal_type} from {app_id}")

    def revoke_all(self, app_id):
        """Revoke all grants for an app."""
        with self._lock:
            path = self._app_path(app_id)
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Revoked all permissions for {app_id}")

    def check_grants(self, app_id, portal_type):
        """Check if a permission is currently granted."""
        grants = self.get_grants(app_id)
        grant = grants.get(portal_type)
        if grant is None:
            return False
        if grant.get('duration') == 'once':
            # One-time grants are consumed on check
            self.revoke_grant(app_id, portal_type)
            return True
        return True

    def has_always_grant(self, app_id, portal_type):
        """Check if an app has an 'always' grant."""
        grants = self.get_grants(app_id)
        grant = grants.get(portal_type)
        return grant is not None and grant.get('duration') == 'always'


class NuxelPortalService(dbus.service.Object):
    """D-Bus portal service for Nuxel-specific hardware access — NO GTK."""

    def __init__(self, bus, object_path):
        dbus.service.Object.__init__(self, bus, object_path)
        self.permissions = PermissionStore()
        # In-flight permission requests keyed by request_id. Each entry records
        # state ('pending'/'granted'/'denied') and the timeout source id so a
        # per-request GLib.timeout_add can auto-deny after NUXEL_PORTAL_TIMEOUT_SECONDS.
        self._inflight = {}
        self._inflight_lock = threading.Lock()
        logger.info("Nuxel Portal service started (system bus, non-GUI mode)")
        logger.info("Portal request timeout configured: %ss", PORTAL_TIMEOUT_SECONDS)
        logger.info("Portal auto-grant mode: %s", PORTAL_AUTO_GRANT)

    def _call_phosh_agent(self, app_id, portal_type):
        """Call the PhoshAgent on the session bus for user consent, with a
        per-request auto-deny timeout.

        The request is forwarded asynchronously to
        org.nuxel.PhoshAgent.RequestPermission. A GLib.timeout_add is armed for
        each request; if no response arrives within PORTAL_TIMEOUT_SECONDS the
        request is automatically denied (and a warning is logged to the portal
        journal). In-flight requests are tracked in self._inflight keyed by
        request_id.

        Args:
            app_id: Application identifier
            portal_type: Permission type string

        Returns:
            dict with {"granted": bool, "duration": str|None}
        """
        # Check for existing 'always' grant first (no user prompt required)
        if self.permissions.has_always_grant(app_id, portal_type):
            logger.info(f"Auto-granting {portal_type} to {app_id} (always grant exists)")
            return {'granted': True, 'duration': 'always'}

        # Headless smoke-test auto-grant: bypass the PhoshAgent prompt entirely.
        if PORTAL_AUTO_GRANT:
            logger.info(
                "NUXEL_PORTAL_AUTO_GRANT is set — auto-granting %s to %s (no PhoshAgent prompt)",
                portal_type, app_id,
            )
            return {'granted': True, 'duration': 'always'}

        request_id = str(uuid.uuid4())
        ctx = {
            'app_id': app_id,
            'portal_type': portal_type,
            'request_id': request_id,
            'state': 'pending',
            'result': None,
            'timer_id': None,
            'loop': None,
            'timeout_fired': False,
        }
        with self._inflight_lock:
            self._inflight[request_id] = ctx

        deny = {'granted': False, 'duration': None}

        def _finish(result):
            """Record the final result and unblock the waiting method."""
            ctx['result'] = result
            if ctx['timer_id'] is not None:
                try:
                    GLib.source_remove(ctx['timer_id'])
                except Exception:
                    pass
            ctx['timer_id'] = None
            with self._inflight_lock:
                if request_id in self._inflight:
                    del self._inflight[request_id]
            if ctx['loop'] is not None:
                try:
                    ctx['loop'].quit()
                except Exception:
                    pass

        def _reply(raw):
            if ctx['timeout_fired']:
                # A late PhoshAgent reply after the auto-deny timeout fired —
                # keep the already-decided denied outcome and ignore it.
                logger.warning(
                    "PhoshAgent reply arrived after timeout for %s/%s (request %s) — ignored",
                    app_id, portal_type, request_id,
                )
                return
            try:
                result = json.loads(raw)
            except (TypeError, ValueError):
                result = dict(deny)
            ctx['state'] = 'granted' if result.get('granted') else 'denied'
            # Persist grants that the agent returns
            if result.get('granted') and result.get('duration'):
                self.permissions.set_grant(app_id, portal_type, result['duration'])
            logger.info(
                "Portal consent for %s/%s via PhoshAgent: granted=%s, duration=%s",
                app_id, portal_type,
                result.get('granted'), result.get('duration'),
            )
            _finish(result)

        def _error(exc):
            if ctx['timeout_fired']:
                # A late reply after auto-deny — keep the denied outcome.
                logger.warning(
                    "PhoshAgent response arrived after timeout for %s/%s (request %s) — ignored",
                    app_id, portal_type, request_id,
                )
                return
            logger.warning(
                "PhoshAgent call failed for %s/%s: %s — denying by default",
                app_id, portal_type, exc,
            )
            ctx['state'] = 'denied'
            _finish(dict(deny))

        def _on_timeout():
            """Auto-deny callback armed via GLib.timeout_add per request."""
            if ctx['state'] != 'pending':
                return GLib.SOURCE_REMOVE
            ctx['timeout_fired'] = True
            ctx['state'] = 'denied'
            logger.warning(
                "Portal request %s for %s/%s TIMED OUT after %.0fs — auto-denied",
                request_id, app_id, portal_type, PORTAL_TIMEOUT_SECONDS,
            )
            _finish(dict(deny))
            return GLib.SOURCE_REMOVE

        try:
            session_bus = dbus.SessionBus()
            agent_obj = session_bus.get_object(PHOSH_AGENT_BUS, PHOSH_AGENT_PATH)
            agent_iface = dbus.Interface(agent_obj, PHOSH_AGENT_IFACE)

            loop = GLib.MainLoop()
            ctx['loop'] = loop
            ctx['timer_id'] = GLib.timeout_add(
                int(PORTAL_TIMEOUT_SECONDS * 1000),
                _on_timeout,
            )

            # Asynchronous call so the main loop can service the timeout.
            # Explicit reply timeout longer than NUXEL_PORTAL_TIMEOUT_SECONDS so
            # the per-request GLib auto-deny timer (the designed path) fires first;
            # without it the bus' 25s default reply timeout preempts the portal
            # timer with a bare NoReply (verified 2026-08-19, briq-13).
            agent_iface.RequestPermission(
                app_id, portal_type,
                reply_handler=_reply,
                error_handler=_error,
                timeout=PORTAL_TIMEOUT_SECONDS + 60.0,
            )

            # Process events until a response or the timeout resolves the request.
            loop.run()
        except dbus.exceptions.DBusException as e:
            logger.warning(
                "PhoshAgent setup failed for %s/%s: %s — denying by default",
                app_id, portal_type, e,
            )
            _finish(dict(deny))
        except Exception as e:
            logger.error(
                "Unexpected error calling PhoshAgent for %s/%s: %s",
                app_id, portal_type, e,
            )
            _finish(dict(deny))

        result = ctx.get('result')
        return result if result is not None else dict(deny)

    # ---------- D-Bus: Ping ----------

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def Ping(self, message):
        """Health-check used by the OpenRC/systemd start() loops."""
        return json.dumps({
            'status': 'ok', 'service': 'nuxel-portal',
            'version': NUXEL_PORTAL_VERSION,
            'echo': message,
        })


    # ── Portal request methods ──────────────────────────────────

    @dbus.service.method(BUS_NAME, in_signature='ss', out_signature='s')
    def RequestSmsSend(self, app_id, recipient):
        """Request user consent to send an SMS."""
        result = self._call_phosh_agent(app_id, PORTAL_SMS)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='ss', out_signature='s')
    def RequestCall(self, app_id, number):
        """Request user consent to place a phone call."""
        result = self._call_phosh_agent(app_id, PORTAL_CALL)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestContactsAccess(self, app_id):
        """Request user consent to access contacts."""
        result = self._call_phosh_agent(app_id, PORTAL_CONTACTS)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestPhoneStatus(self, app_id):
        """Request user consent to read phone status."""
        result = self._call_phosh_agent(app_id, PORTAL_PHONE_STATUS)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestLocation(self, app_id):
        """Request user consent to access location."""
        result = self._call_phosh_agent(app_id, PORTAL_LOCATION)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestCamera(self, app_id):
        """Request user consent to use the camera."""
        result = self._call_phosh_agent(app_id, PORTAL_CAMERA)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestMicrophone(self, app_id):
        """Request user consent to use the microphone."""
        result = self._call_phosh_agent(app_id, PORTAL_MICROPHONE)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='ss', out_signature='s')
    def RequestSettingsChange(self, app_id, setting):
        """Request user consent to change a system setting."""
        result = self._call_phosh_agent(app_id, PORTAL_SETTINGS)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def GetAppPermissions(self, app_id):
        """Get all current permission grants for an app."""
        grants = self.permissions.get_grants(app_id)
        return json.dumps({'app_id': app_id, 'permissions': grants})

    @dbus.service.method(BUS_NAME, in_signature='ss', out_signature='s')
    def RevokePermission(self, app_id, portal_type):
        """Revoke a specific permission for an app."""
        self.permissions.revoke_grant(app_id, portal_type)
        return json.dumps({'success': True})

    @dbus.service.method(BUS_NAME, in_signature='ss', out_signature='s')
    def CheckPermission(self, app_id, portal_type):
        """Check if a permission is currently granted (non-interactive)."""
        granted = self.permissions.check_grants(app_id, portal_type)
        return json.dumps({'app_id': app_id, 'portal_type': portal_type, 'granted': granted})

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestCalendarAccess(self, app_id):
        """Request user consent to access the calendar."""
        result = self._call_phosh_agent(app_id, PORTAL_CALENDAR)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestBluetoothAccess(self, app_id):
        """Request user consent to use Bluetooth."""
        result = self._call_phosh_agent(app_id, PORTAL_BLUETOOTH)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestUsbAccess(self, app_id):
        """Request user consent to access USB devices."""
        result = self._call_phosh_agent(app_id, PORTAL_USB)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='ss', out_signature='s')
    def RequestClipboardAccess(self, app_id, direction):
        """Request user consent to access the clipboard.

        Args:
            app_id: Application identifier
            direction: 'read' or 'write'
        """
        portal_type = PORTAL_CLIPBOARD_WRITE if direction == 'write' else PORTAL_CLIPBOARD_READ
        result = self._call_phosh_agent(app_id, portal_type)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def RequestBackgroundExecution(self, app_id):
        """Request user consent to run in the background."""
        result = self._call_phosh_agent(app_id, PORTAL_BACKGROUND)
        return json.dumps(result)

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def GetRiskLevels(self):
        """Return risk levels for all portal types."""
        return json.dumps({
            'risk_levels': {k: v for k, v in sorted(PORTAL_RISK_LEVELS.items())}
        })

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def GetPortalIcons(self):
        """Return icon names for all portal types."""
        return json.dumps({
            'icons': {k: v for k, v in sorted(PORTAL_ICONS.items())}
        })

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def GetPortalTypes(self):
        """Return list of all available portal types."""
        return json.dumps({
            'portals': [
                {'type': k, 'description': v}
                for k, v in sorted(PORTAL_DESCRIPTIONS.items())
            ]
        })

    @dbus.service.signal(BUS_NAME, signature='s')
    def PermissionChanged(self, data):
        """Signal emitted when a permission is granted or revoked."""
        pass


def main():
    """Start the nuxel-portal daemon."""
    logger.info("Starting Nuxel Portal (non-GUI system daemon)...")

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    try:
        bus_name = dbus.service.BusName(BUS_NAME, bus)
        logger.info(f"Claimed D-Bus name: {BUS_NAME}")
    except dbus.exceptions.NameExistsException:
        logger.error(f"Bus name {BUS_NAME} already taken")
        sys.exit(1)

    service = NuxelPortalService(bus, OBJECT_PATH)

    logger.info("Nuxel Portal running. Waiting for portal requests...")

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Nuxel Portal shutting down...")
        loop.quit()


if __name__ == '__main__':
    main()
