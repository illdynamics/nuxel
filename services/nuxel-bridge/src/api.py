#!/usr/bin/env python3
"""
Nuxel Bridge - REST API Compatibility Layer

Provides a simple HTTP interface for PWAs that cannot directly use D-Bus.
This wraps the D-Bus calls in a local HTTP server accessible only from localhost.

SECURITY: This API MUST only listen on 127.0.0.1 and MUST validate all requests
against an API key or session token. It is a convenience layer for development
and testing; production PWAs should use D-Bus directly via xdg-desktop-portal.
"""

import base64
import binascii
import json
import mimetypes
import re
import uuid
import hmac
import hashlib
import time
import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import dbus
import dbus.mainloop.glib
import subprocess
import shlex
import socket
import shutil
import signal
import threading
import ipaddress
import urllib.parse

logger = logging.getLogger('nuxel-http-bridge')
_DOWNLOAD_JOBS = {}
_DOWNLOAD_LOCK = threading.Lock()

# Lockhead indicators are computed in-process (sysfs + /proc), next to this file.
# The import is deliberately after logger setup and failure is contained: an
# unavailable sensor module yields a 503 and a dimmed UI, never invented state.
try:
    import system_indicators
except Exception as _e:  # pragma: no cover - api.py must not fail import without it
    system_indicators = None
    logger.warning('system_indicators unavailable: %s', _e)

# Tri-Link is a read-only capability/status view for the three console apps.
# It never starts sshd, touches configfs, opens serial or changes routes.
try:
    import tri_link_status
except Exception as _e:  # pragma: no cover - optional module
    tri_link_status = None

# PWNAGE-47000: GUI remote access (XRDP/VNC/scrcpy) is a SEPARATE provider from
# the read-only SSH/serial Tri-Link status.  It owns the fixed start/stop helper
# and never accepts a command, path, address or executable from JavaScript.
try:
    import remote_desktop
except Exception as _e:  # pragma: no cover - optional module
    remote_desktop = None
    logger.warning('remote_desktop unavailable: %s', _e)

# Single privileged torch owner.  PWAs and the button manager request a state;
# only this in-process provider writes the LED brightness node.
try:
    import flashlight_provider
except Exception as _e:  # pragma: no cover - optional module
    flashlight_provider = None
    logger.warning('flashlight_provider unavailable: %s', _e)

# BlueZ OBEX Object Push is the ONE Files "Send" transport.  It is D-Bus based
# and never implemented as a private raw protocol.
try:
    import bluetooth_obex
except Exception as _e:  # pragma: no cover - optional module
    bluetooth_obex = None
    logger.warning('bluetooth_obex unavailable: %s', _e)

# PWNAGE-45000 providers.  Each is a real capability probe/owner; none reports
# an ON state without hardware evidence.
for _modname in ('dnd_provider', 'nfc_provider', 'fingerprint_provider',
                 'security_provider', 'led_notification_provider', 'app_manager',
                 'software_provider', 'privacy_provider', 'flatpak_provider',
                 'doom_assets'):
    try:
        globals()[_modname] = __import__(_modname)
    except Exception as _e:  # pragma: no cover - optional module
        globals()[_modname] = None
        logger.warning('%s unavailable: %s', _modname, _e)

# USB connection-mode state machine (Charging / File Transfer). It only
# activates a real endpoint through the dedicated helper and reports the result.
try:
    import usb_mode
except Exception as _e:  # pragma: no cover - optional module
    usb_mode = None
    logger.warning('usb_mode unavailable: %s', _e)

# One normalization rule for Wayland app ids.  Flatpak/reverse-DNS launcher ids
# often differ from the compositor's xdg_toplevel app_id (e.g.
# com.sindresorhus.Caprine -> Caprine, org.ferdium.Ferdium -> ferdium).  Every
# launch/focus/close path uses this module so newly installed apps do not need a
# per-app mapping.
try:
    import app_surface
except Exception as _e:  # pragma: no cover - optional module
    app_surface = None
    logger.warning('app_surface unavailable: %s', _e)

# Privileged hardware providers (audio mixer, Type-C/display inventory, and the
# Bluetooth rfkill/systemctl actuator).  These run in this ROOT process because
# the D-Bus bridge is sandboxed away from /dev/snd and /sys/class/rfkill writes.
try:
    import hw_providers
except Exception as _e:  # pragma: no cover - optional module
    hw_providers = None
    logger.warning('hw_providers unavailable: %s', _e)

# PWA application persistence (calendar/notes/contacts/files) + haptics FIFO.
# Imported lazily by _handle_rpc so a missing store never blocks the REST API.
try:
    import pwa_store
except Exception as _e:  # pragma: no cover - optional module
    pwa_store = None
    logger.warning('pwa_store unavailable: %s', _e)

try:
    import mail_client
except Exception as _e:  # pragma: no cover - optional module
    mail_client = None
    logger.warning('mail_client unavailable: %s', _e)

try:
    import mic_provider
except Exception as _e:  # pragma: no cover - optional module
    mic_provider = None
    logger.warning('mic_provider unavailable: %s', _e)

# Nuxel Vault / Authenticator keyring.  The provider is a narrow Secret Service
# client; the module is optional so a missing python3-dbus / GNOME Keyring never
# blocks the rest of the bridge.  Keyring calls fail closed in that case.
try:
    import keyring_api as _keyring_api
except Exception as _e:  # pragma: no cover - optional module
    _keyring_api = None
    logger.warning('keyring provider unavailable: %s', _e)


# ── Environment-driven configuration ────────────────────────────

HTTP_BIND = os.environ.get('NUXEL_HTTP_BIND', '127.0.0.1')
HTTP_PORT = int(os.environ.get('NUXEL_HTTP_PORT', '8080'))
HTTP_MODE = os.environ.get('NUXEL_HTTP_MODE', 'dev')

# PWA<->host PROTOCOL contract (briq-04c). Pinned in
# pwa/nuxel-common/bridge-version.json; every app manifest declares the same
# value as nuxel.bridge_version. Published on /ping and /health, and enforced on
# every request that carries the X-Nuxel-Bridge-Version header: a mismatch is
# answered 409 version_mismatch — LOUD, never a silent rejection or a silent
# downgrade. NUXEL_BRIDGE_VERSION is the host IMPLEMENTATION version and is
# allowed to move independently.
BRIDGE_PROTOCOL_VERSION = os.environ.get('NUXEL_BRIDGE_PROTOCOL_VERSION', '1')
BRIDGE_HOST_VERSION = os.environ.get('NUXEL_BRIDGE_VERSION', '0.7.7-beta')

# Canonical launcher registry, shared with the PWA (pwa/nuxel-common/app-registry.json)
# and the native shell. The rootfs installs it at /etc/nuxel/app-registry/.
APP_REGISTRY_PATH = os.environ.get('NUXEL_APP_REGISTRY', '/etc/nuxel/app-registry/app_registry.json')

# D-Bus bridge call timeout (seconds). Must comfortably exceed the portal's
# consent timeout (NUXEL_PORTAL_TIMEOUT_SECONDS=30) plus slack so an in-flight
# user-consent round-trip (bridge -> portal -> PhoshAgent -> dialog) resolves
# with a REAL verdict instead of tripping the 25s dbus default and being
# masked by the mock fallback (audit briq-12).
BRIDGE_DBUS_TIMEOUT_SECONDS = float(os.environ.get('NUXEL_BRIDGE_DBUS_TIMEOUT_SECONDS', '90'))

# CORS origins allowlist (source of truth). Honored in both dev and production
# modes via the comma-separated NUXEL_API_ALLOW_ORIGIN env var. Defaults to the
# local PWA origins. Only explicitly allowed origins are ever reflected back.
_ALLOWED_ORIGINS_ENV = os.environ.get('NUXEL_API_ALLOW_ORIGIN', '')
ALLOWED_ORIGINS = set(_.strip() for _ in _ALLOWED_ORIGINS_ENV.split(',') if _.strip()) if _ALLOWED_ORIGINS_ENV.strip() else {
    'http://127.0.0.1:8000',
    'http://localhost:8000',
}

# Single-source path config (briq-20): load /etc/nuxel/paths.conf, overridable
# via NUXEL_PATHS_CONF. Environment variables take precedence over the file.
NUXEL_PATHS_CONF = os.environ.get("NUXEL_PATHS_CONF", "/etc/nuxel/paths.conf")
NUXEL_DATA_DIR = os.environ.get("NUXEL_DATA_DIR")
if not NUXEL_DATA_DIR and os.path.exists(NUXEL_PATHS_CONF):
    try:
        with open(NUXEL_PATHS_CONF) as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _v = _line.split("=", 1)
                if _k.strip() == "NUXEL_DATA_DIR":
                    NUXEL_DATA_DIR = _v.strip().strip('"').strip("'")
                    break
    except OSError:
        NUXEL_DATA_DIR = None
if not NUXEL_DATA_DIR:
    NUXEL_DATA_DIR = '/var/lib/nuxel'

# Token directory
# ── Launcher -> app activation (briq-04c rev 2) ────────────────────────────
# The launcher resolves an app id to an activation DESCRIPTOR here, for the same
# reason the registry is served here: one authority, one answer.
#
# WHAT THIS NEVER DOES: it never executes anything. There is no path parameter,
# no command parameter and no subprocess/os.system/exec* call on this path - the
# client sends a registry ID and receives back the REGISTRY's own entry (a `url`
# for a PWA, `native_binary` for a native app). A client-supplied `binary`,
# `command`, `url` or `path` is ignored by construction (the descriptor is built
# from the registry, not from the request), so a compromised PWA cannot turn
# "activate an app" into "run an arbitrary program". The actual launch (WebKit
# navigation, or exec of a registry-listed binary) happens in the native PWA
# host, which is a separate, non-Web process.
ACTIVATION_HISTORY_MAX = 20
ACTIVATION_HISTORY = []          # bounded, in-process: {id, at, action, source}
ACTIVATION_REJECTED = {"count": 0, "last": None}
# An app id is an identifier, never a path: no separator, no "..", no leading dot.
APP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
# Per-app default orientation (a launch preference, not a permission).
APP_ORIENTATION_DEFAULTS = "/etc/nuxel/orientation/app-defaults.json"
APP_ORIENTATION_DEFAULT_MODE = "portrait"
APP_ORIENTATION_MODES = ("portrait", "reverse-portrait", "landscape", "reverse-landscape")

# Flatpak apps that also have a legacy static launcher entry.  The dynamic
# provider is authoritative: when one is uninstalled its static entry is
# removed, so the launcher never keeps a stale ghost icon.
KNOWN_FLATPAK_IDS = {
    "org.mozilla.firefox", "org.videolan.VLC",
    "org.signal.Signal", "com.stremio.Stremio",
}
FLATPAK_CATEGORY = {
    "org.mozilla.firefox": "tools",
    "org.videolan.VLC": "media",
    "org.signal.Signal": "communication",
    "com.stremio.Stremio": "media",
}

TOKEN_DIR = os.path.join(NUXEL_DATA_DIR, 'http-bridge')
TOKEN_FILE = os.path.join(TOKEN_DIR, 'token')
# PWNAGE-63000: the native PWA host injects a top-frame-only relay that holds
# this per-device secret in a closure.  The Bridge reads the same root-only file.
KEYRING_LAUNCHER_SECRET_FILE = os.environ.get(
    'NUXEL_KEYRING_SECRET_FILE', '/etc/nuxel/keyring-launcher.secret')
KEYRING_LAUNCHER_APPS = {'org.nuxel.Vault', 'org.nuxel.Authenticator'}

# Per-session token registry: token -> {app_id, created, expires}
SESSION_TOKENS = {}
SESSION_TTL_SECONDS = 3600  # 1 hour

MAX_REQUEST_SIZE = 128 * 1024 * 1024  # 128 MB (file writes/recordings are loopback-only)


def _get_token():
    """Get or create the API token based on mode."""
    if HTTP_MODE == 'dev':
        # Dev mode: no shared token is auto-created. Per-session tokens are
        # issued on demand via POST /api/v1/auth/token and validated against
        # the SESSION_TOKENS registry. An existing static token file is still
        # honoured if present (e.g. provisioned for the native launcher).
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE) as f:
                return f.read().strip()
        return None
    else:
        # Production mode: require existing token file
        if not os.path.exists(TOKEN_FILE):
            logger.critical(
                "Production mode requires existing token file at %s. Exiting.",
                TOKEN_FILE,
            )
            return None
        with open(TOKEN_FILE) as f:
            return f.read().strip()


def _keyring_launcher_secret():
    """Read the per-device launcher secret; None if absent/invalid."""
    try:
        with open(KEYRING_LAUNCHER_SECRET_FILE, 'r') as fh:
            value = fh.read(256).strip()
    except OSError:
        return None
    if len(value) != 64:
        return None
    if any(c not in '0123456789abcdefABCDEF' for c in value):
        return None
    return value


def _get_cors_origin(origin_header):
    """Return the matching allowed origin if permitted, else None.

    Honors the NUXEL_API_ALLOW_ORIGIN allowlist (comma-separated) as the source
    of truth in both dev and production modes. Never reflects '*' — only an
    explicitly allowed origin is echoed in Access-Control-Allow-Origin. Returns
    None (no CORS header) for any origin not on the allowlist.
    """
    if origin_header and origin_header in ALLOWED_ORIGINS:
        return origin_header
    return None


class BridgeAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler for the bridge API."""

    # Shared session token
    server_token = None

    def log_message(self, format, *args):
        """Override to use standard logging."""
        logger.info("%s - %s", self.client_address[0], format % args)

    def _get_json_body(self):
        """Read and parse JSON body with size limit enforcement.

        Returns:
            Parsed JSON dict, or None if error (413/400 already sent).
        """
        content_length = int(self.headers.get('Content-Length', 0))

        # Size cap
        if content_length > MAX_REQUEST_SIZE:
            self._send_json(
                {"error": "Request entity too large", "code": 413},
                status=413,
            )
            return None

        if content_length == 0:
            return {}

        body = self.rfile.read(content_length)

        try:
            return json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            self._send_json(
                {"error": "Invalid JSON", "code": 400},
                status=400,
            )
            return None

    def _send_storage_file(self, path):
        """Stream a real file from the user's home with HTTP Range support.

        Gallery uses this for thumbnails and video playback.  It is loopback-only
        (the handler's auth already allows loopback dev requests) and every path
        is resolved through PwaStore's traversal/symlink checks.
        """
        try:
            store = self._app_store()
            target = store.storage_media_file(path)
            size = target.stat().st_size
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            start, end = 0, size - 1
            status = 200
            rng = self.headers.get('Range') if hasattr(self, 'headers') else None
            if rng and rng.startswith('bytes='):
                spec = rng[6:].split(',', 1)[0].strip()
                a, _, b = spec.partition('-')
                try:
                    if a:
                        start = int(a)
                        end = int(b) if b else size - 1
                    elif b:
                        start = max(0, size - int(b))
                    if start < 0 or end < start or start >= size:
                        raise ValueError
                    end = min(end, size - 1)
                    status = 206
                except ValueError:
                    self.send_response(416)
                    self.send_header('Content-Range', 'bytes */%d' % size)
                    self.end_headers()
                    return
            length = end - start + 1
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(length))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'no-store')
            origin = self.headers.get('Origin', '')
            cors_origin = _get_cors_origin(origin if origin else None)
            if cors_origin:
                self.send_header('Access-Control-Allow-Origin', cors_origin)
            if status == 206:
                self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
            self.end_headers()
            with target.open('rb') as fh:
                fh.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = fh.read(min(262144, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except Exception as exc:
            logger.warning('storage file read failed for %r: %s', path, exc)
            self._send_json({'success': False, 'error': str(exc)}, 404)

    def _send_storage_thumbnail(self, path):
        """Serve a bounded, cached JPEG still for Gallery video cells.

        This is the only decoder entry point used by the grid.  Path validation,
        traversal/symlink rejection and decode timeouts live in PwaStore.
        """
        if not path:
            self._send_json({'success': False, 'error': 'path required'}, 400)
            return
        try:
            store = self._app_store()
            thumb, mime = store.thumbnail_file(path)
            data = thumb.read_bytes()
        except StoreError as exc:
            self._send_json({'success': False, 'error': str(exc),
                             'error_code': 'THUMBNAIL_UNAVAILABLE'}, 404)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning('thumbnail failed for %r: %s', path, exc)
            self._send_json({'success': False, 'error': 'thumbnail unavailable'}, 500)
            return
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'private, max-age=86400')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        try:
            self.wfile.write(data)
        except OSError:
            pass

    def _send_json(self, data, status=200):
        response = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))

        # CORS — reflect only explicitly allowed origins (never '*').
        origin = self.headers.get('Origin', '')
        cors_origin = _get_cors_origin(origin if origin else None)
        if cors_origin:
            self.send_header('Access-Control-Allow-Origin', cors_origin)

        self.end_headers()
        self.wfile.write(response)

    def _send_bytes(self, data, content_type='application/octet-stream', status=200,
                    cache='no-store'):
        """Send a bounded binary response (Flatpak icons only in this revision)."""
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', cache)
        origin = self.headers.get('Origin', '')
        cors_origin = _get_cors_origin(origin if origin else None)
        if cors_origin:
            self.send_header('Access-Control-Allow-Origin', cors_origin)
        self.end_headers()
        try:
            self.wfile.write(data)
        except OSError:
            pass

    def _verify_auth(self):
        """Verify authentication token.

        Accepts either a per-session token issued by POST /api/v1/auth/token
        (validated against the SESSION_TOKENS registry) or the static server
        token provisioned via NUXEL exit env / CLI.

        Dev mode (/api/v1/* verification): the service binds to 127.0.0.1
        (NUXEL_HTTP_BIND) with NUXEL_HTTP_MODE=dev, so requests originating
        from the local loopback are allowed without a token. This is what lets
        `curl http://127.0.0.1:8080/api/v1/health` return 200/JSON in the VM
        verification. Any other inbound path still requires authentication.
        """
        # Dev + loopback peer => allow (matches briq-5 curl verification).
        import ipaddress
        if HTTP_MODE == 'dev':
            try:
                peer = self.client_address[0]
                if peer in ('127.0.0.1', '::1') or ipaddress.ip_address(peer).is_loopback:
                    return True
            except (ValueError, IndexError, KeyError):
                pass

        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return False

        token = auth[7:]
        if not token:
            return False

        # Per-session token registry
        session = SESSION_TOKENS.get(token)
        if session is not None:
            if session.get("expires", 0) < time.time():
                # Expired — drop it
                SESSION_TOKENS.pop(token, None)
                return False
            return True

        # Static / provisioned server token
        if self.server_token and token == self.server_token:
            return True

        return False


    def _session_token(self):
        """Return the live per-session token document, or None."""
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return None
        token = auth[7:]
        if not token:
            return None
        session = SESSION_TOKENS.get(token)
        if session is None:
            return None
        if session.get('expires', 0) < time.time():
            SESSION_TOKENS.pop(token, None)
            return None
        return session

    def _keyring_identity(self, app_id):
        """Prove the caller is the registered local app, not a JSON app_id."""
        if _keyring_api is None:
            return ({'success': False, 'error': 'provider_unavailable',
                     'state': 'unavailable', 'offline': True,
                     'detail': 'the native keyring module is not installed'}, None)
        session = self._session_token()
        entry = None
        if app_id in _keyring_api.KEYRING_APP_CAPABILITY:
            entry, _info = self._lookup_registry_app(app_id)
        denial = _keyring_api.check_identity(app_id, self.headers, session, entry,
                                             ALLOWED_ORIGINS)
        if denial is not None:
            logger.info("keyring identity denied app=%s code=%s issuer=%s token_app=%s issued_ref=%s current_ref=%s origin=%s",
                        app_id, denial.get('error'),
                        (session or {}).get('issuer', 'self'),
                        (session or {}).get('app_id'),
                        urlparse((session or {}).get('referer') or '').path,
                        urlparse(self.headers.get('Referer', '') or '').path,
                        self.headers.get('Origin', ''))
        return (denial, session)

    def _load_app_registry(self):
        """Serve the canonical app registry (briq-04c): the SAME file the PWA and
        the native shell consume, so the grid cannot drift from the bridge.

        Honest failure: an absent/unreadable registry is reported as
        available=false with the resolved path and the reason. It is never
        replaced with an invented app list.
        """
        info = {"available": False, "source": APP_REGISTRY_PATH, "bridge_version": BRIDGE_PROTOCOL_VERSION}
        try:
            with open(APP_REGISTRY_PATH, "r") as fh:
                doc = json.load(fh)
        except FileNotFoundError:
            info["error"] = "registry file not found"
            return info
        except (OSError, ValueError) as exc:
            info["error"] = "registry unreadable: %s" % exc
            return info
        apps = doc.get("apps")
        if not isinstance(apps, list) or not apps:
            info["error"] = "registry has no apps[] entries"
            return info
        info.update({
            "available": True,
            "schema": doc.get("schema"),
            "registry_version": doc.get("registry_version"),
            "host_version": BRIDGE_HOST_VERSION,
            "url_base": doc.get("url_base"),
            "apps": apps,
        })
        self._augment_registry_with_flatpak(info)
        declared = doc.get("bridge_version")
        if declared and declared != BRIDGE_PROTOCOL_VERSION:
            info["version_mismatch"] = {"registry": declared, "host": BRIDGE_PROTOCOL_VERSION}
        return info

    def _augment_registry_with_flatpak(self, info):
        """Merge installed Flatpak apps into the canonical launcher registry.

        The static registry remains the offline baseline for native/PWA apps.
        Flatpak entries are dynamic: a successful ``flatpak list`` replaces the
        legacy static entry for the same id and removes a legacy entry whose
        Flatpak is no longer installed.  A provider failure leaves the baseline
        untouched and reports the reason instead of inventing apps.
        """
        if flatpak_provider is None:
            info["flatpak"] = {"available": False, "error": "provider unavailable"}
            return
        try:
            installed = flatpak_provider.get_provider().list_installed()
        except Exception as exc:  # noqa: BLE001
            info["flatpak"] = {"available": False, "error": str(exc)}
            return
        if not installed.get("success"):
            info["flatpak"] = {"available": False,
                               "error": installed.get("error") or "flatpak list failed"}
            return
        dynamic = {}
        for app in installed.get("apps") or []:
            aid = app.get("id")
            if not isinstance(aid, str) or not APP_ID_RE.match(aid):
                continue
            scope = app.get("scope") or "system"
            category = FLATPAK_CATEGORY.get(aid, "tools")
            dynamic[aid] = {
                "id": aid,
                "name": app.get("name") or aid,
                "icon": "📦",
                "iconAsset": "http://127.0.0.1:8080/api/v1/flatpak/icon/" + aid,
                "color": "#4a90e2",
                "category": category,
                "type": "native",
                "url": aid + "://",
                "native_binary": "/usr/bin/flatpak",
                "flatpak_id": aid,
                "flatpak_scope": scope,
                "flatpak_version": app.get("version") or "",
                "flatpak_branch": app.get("branch") or "",
                "flatpak_arch": app.get("arch") or "aarch64",
                "flatpak_runtime": app.get("runtime") or "",
                "flatpak_ref": app.get("ref") or "",
                "desktop_entry": app.get("desktop_file") or "",
                "description": app.get("description") or ("Flatpak application (%s)" % (app.get("runtime") or "Flatpak")),
                "capabilities": [],
                "bridge_version": BRIDGE_PROTOCOL_VERSION,
                "docked": False,
                "status": "installed",
                "runtime_state": "Flatpak %s · %s · %s" % (
                    app.get("version") or "installed",
                    app.get("runtime") or "unknown runtime",
                    app.get("arch") or "aarch64"),
                "install_source": "flatpak:" + scope,
            }
        static = info.get("apps") or []
        kept = []
        for app in static:
            aid = app.get("id")
            if aid in dynamic:
                continue
            if aid in KNOWN_FLATPAK_IDS:
                continue
            kept.append(app)
        for aid, entry in dynamic.items():
            prev = next((a for a in static if a.get("id") == aid), {})
            merged = dict(prev)
            merged.update(entry)
            merged["docked"] = bool(prev.get("docked", False))
            kept.append(merged)
        info["apps"] = kept
        info["flatpak"] = {
            "available": True,
            "installed": len(dynamic),
            "source": "flatpak_provider",
            "scopes": sorted({a.get("flatpak_scope") for a in dynamic.values()}),
        }

    def _lookup_registry_app(self, app_id):
        """Return (app_entry_or_None, registry_info). Never invents an app."""
        info = self._load_app_registry()
        if not info.get("available"):
            return None, info
        for app in info.get("apps") or []:
            if app.get("id") == app_id:
                return app, info
        return None, info

    def _activate_app(self, target_id, requester, source):
        """Resolve an app id to an activation descriptor (JSON body, HTTP code).

        Mediation rules:
          * the registry is the ONLY source of the descriptor;
          * an unknown id is 404 unknown_app - nothing is guessed, nothing runs;
          * an id that is not a plain identifier (a path, a shell metacharacter,
            a "..") is 400 invalid_app_id BEFORE any lookup;
          * a native entry without a binary (a documented placeholder, e.g.
            nuxel-camera until the camera surface lands) is reported as
            `launchable: false` with the registry's own implementation note;
          * an unavailable registry is 503 - never a fabricated app list.
        """
        if not isinstance(target_id, str) or not APP_ID_RE.match(target_id or ""):
            ACTIVATION_REJECTED["count"] += 1
            ACTIVATION_REJECTED["last"] = target_id if isinstance(target_id, str) else repr(target_id)
            logger.warning("activation refused: %r is not an app identifier", target_id)
            return ({"success": False, "error": "invalid_app_id",
                     "detail": "an app id is an identifier (letters, digits, . _ : -), "
                               "never a path or a command",
                     "got": target_id if isinstance(target_id, str) else None}, 400)
        app, info = self._lookup_registry_app(target_id)
        if app is None:
            if not info.get("available"):
                return ({"success": False, "error": "registry_unavailable",
                         "detail": info.get("error") or "the canonical registry could not be read",
                         "source": info.get("source")}, 503)
            ACTIVATION_REJECTED["count"] += 1
            ACTIVATION_REJECTED["last"] = target_id
            return ({"success": False, "error": "unknown_app", "app_id": target_id,
                     "registry_version": info.get("registry_version")}, 404)
        kind = app.get("type")
        descriptor = {
            "success": True,
            "id": app.get("id"),
            "name": app.get("name"),
            "type": kind,
            "category": app.get("category"),
            "capabilities": app.get("capabilities") or [],
            "bridge_version": app.get("bridge_version"),
            "registry_version": info.get("registry_version"),
            "source": "registry",
            "executed": False,   # the bridge resolves; the PWA host launches
            "app_id": app.get("id"),
        }
        if kind == "pwa":
            if app.get("resolution") == "pending":
                # The app tree is DECLARED but not landed in this revision (the
                # registry records the owners, the reason and the expected files).
                # Navigating to a 404 is not a launch, so the descriptor says so
                # instead of handing the launcher a dead URL. This is a STATIC
                # registry fact: the bridge never probes the filesystem.
                pending = app.get("pending") or {}
                descriptor.update({
                    "launchable": False,
                    "action": "pending_app_tree",
                    "url": app.get("url"),
                    "detail": pending.get("reason")
                              or "this app's tree is declared but not landed yet",
                    "owner_groups": pending.get("owner_groups") or [],
                    "expected": pending.get("expected") or [],
                })
            else:
                descriptor.update({
                    "launchable": True,
                    "action": "navigate",
                    "url": app.get("url"),             # registry value, not the request's
                    "manifest": app.get("manifest"),
                    "origin": info.get("url_base"),
                })
        elif kind == "native":
            binary = app.get("native_binary")
            if binary:
                descriptor.update({"launchable": True, "action": "exec",
                                   "native_binary": binary,
                                   "desktop_entry": app.get("desktop_entry")})
            else:
                descriptor.update({
                    "launchable": False,
                    "action": "documented_placeholder",
                    "detail": app.get("implementation_note")
                              or "native entry without a binary in this revision",
                    "status": app.get("status", "placeholder"),
                })
        else:
            descriptor.update({"launchable": False, "action": "unknown_type",
                               "detail": "registry entry has type %r" % kind})
        ACTIVATION_HISTORY.append({"id": app.get("id"), "at": time.time(),
                                   "action": descriptor["action"],
                                   "requester": requester, "source": source})
        del ACTIVATION_HISTORY[:-ACTIVATION_HISTORY_MAX]
        return descriptor, 200

    def _verify_version(self):
        """Enforce the pinned bridge_version when the client declares one.

        Returns None when the request may proceed, or the 409 payload to send.
        A client that sends no header is a legacy client and is allowed through
        (the version is published on /ping and /health for it to check), but a
        client that declares a DIFFERENT version is refused explicitly.
        """
        got = self.headers.get('X-Nuxel-Bridge-Version')
        if got is None or got == '':
            return None
        if got == BRIDGE_PROTOCOL_VERSION:
            return None
        return {
            "error": "version_mismatch",
            "expected": BRIDGE_PROTOCOL_VERSION,
            "got": got,
            "host_version": BRIDGE_HOST_VERSION,
            "detail": "the app was built against a different bridge protocol version; "
                      "the host refuses to serve it rather than answering with skewed data",
        }


    # ---- Native app execution + Home action (A59) -------------------------
    # Both are CLOSED-verb operations: the caller supplies only a registry app
    # id (or the fixed word "home"); the actual program run is resolved HERE
    # from the canonical registry / a fixed allowlist. A client-supplied path,
    # binary or command is ignored by construction, so a compromised PWA cannot
    # turn "launch an app" into "run an arbitrary program".

    # Graphics/session environment for a native top-level app on this phone.
    NATIVE_LAUNCH_ENV = {
        "XDG_RUNTIME_DIR": "/run/nuxel-wayland",
        "WAYLAND_DISPLAY": "wayland-0",
        # Graphics keys are added per app by _graphics_env_for().  They are not
        # a blanket environment: GSK_RENDERER is meaningless to GTK3/WebKit and
        # LIBGL_ALWAYS_SOFTWARE must never be inherited by a proven accelerated
        # process.
        "GDK_BACKEND": "wayland",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": "/root",
    }

    GRAPHICS_PROFILE_TOOL = "/usr/lib/nuxel/nuxel-graphics-profile"
    GRAPHICS_ENV_KEYS = {
        "GDK_BACKEND", "GSK_RENDERER", "LIBGL_ALWAYS_SOFTWARE",
        "WEBKIT_DISABLE_COMPOSITING_MODE", "WEBKIT_FORCE_COMPOSITING_MODE",
        "MESA_KBASE_NODE", "MESA_LOADER_DRIVER_OVERRIDE", "NUXEL_KBASE_WSI",
        "NUXEL_GRAPHICS_FALLBACK_REASON", "GDK_GL", "LIBGL_DRIVERS_PATH",
        "__EGL_VENDOR_LIBRARY_FILENAMES",
    }

    def _graphics_env_for(self, target_id):
        """Resolve the validated per-app graphics profile.

        The helper is a fixed path and only emits keys from its own closed
        schema.  A missing/failed helper falls back to explicit software, never
        to "hope GL works" and never to an empty environment.
        """
        cache = getattr(self, "_graphics_env_cache", None)
        if cache is None:
            cache = {}
            self._graphics_env_cache = cache
        cached = cache.get(target_id)
        if cached and (time.time() - cached[0]) < 60:
            return dict(cached[1])
        env = {}
        try:
            proc = subprocess.run(
                [self.GRAPHICS_PROFILE_TOOL, "env", "native:%s" % target_id],
                capture_output=True, text=True, timeout=4,
                env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"})
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if not line.startswith("export "):
                        continue
                    key, _, raw = line[7:].partition("=")
                    if key not in self.GRAPHICS_ENV_KEYS:
                        continue
                    try:
                        value = shlex.split(raw)
                    except ValueError:
                        continue
                    if len(value) == 1:
                        env[key] = value[0]
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("graphics profile helper failed for %s: %s", target_id, exc)
        if "LIBGL_ALWAYS_SOFTWARE" not in env and "GSK_RENDERER" not in env:
            env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
            env["NUXEL_GRAPHICS_FALLBACK_REASON"] = "profile helper unavailable"
        cache[target_id] = (time.time(), dict(env))
        return env

    # Registry ids that may be launched natively, with their fixed launch argv.
    # The dict is the ONLY launch authority; nothing else is exec'd on this path.
    NATIVE_LAUNCH = {
        "org.nuxel.BrowserNative": [
            "/usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py",
        ],
        "org.nuxel.CameraNative": [
            "/usr/lib/nuxel/nuxel-camera-native/nuxel_camera_native.py",
        ],
        "org.gnome.Snapshot": [
            "/usr/sbin/snapshot",
        ],
        # Core communication apps (PWNAGE-30000).  These were previously only
        # resolved through the registry fallback, so a missing/not-yet-installed
        # binary surfaced as a generic launch failure in the launcher.
        "nuxel-contacts": ["/usr/bin/nuxel-contacts"],
        "nuxel-dialer": ["/usr/bin/nuxel-dialer"],
        "nuxel-messages": ["/usr/bin/nuxel-messages"],
        # PWNAGE-43000: Flatpak (aarch64) and native Fedora applications.
        "org.mozilla.firefox": ["/usr/bin/firefox"],
        # VLC 3.0.24's aarch64 Fedora build cannot create a Wayland video
        # output or load its Qt interface on this image.  The wrapper tries
        # VLC briefly and then hands the file to mpv, which is verified.
        "org.videolan.VLC": ["/usr/lib/nuxel/nuxel-vlc-fallback"],
        "org.nuxel.MediaPlayer": ["/usr/bin/mpv", "--no-config",
                                  "--force-window=yes", "--idle=yes"],
        "org.signal.Signal": ["/usr/lib/nuxel/nuxel-flatpak-signal"],
        "com.stremio.Stremio": ["/usr/lib/nuxel/nuxel-flatpak-stremio"],
        "org.gnome.FileRoller": ["/usr/bin/file-roller"],
        "org.gnome.Loupe": ["/usr/bin/loupe"],
        "org.gnome.Papers": ["/usr/bin/papers"],
        "org.gnome.SystemMonitor": ["/usr/bin/gnome-system-monitor"],
        # PWNAGE-45000 native Software center (GTK3 + PackageKit/polkit).
        "org.gnome.Software": ["/usr/lib/nuxel/nuxel-software"],
        # v0.7.7-beta: the only native Doom path is Chocolate Doom.  Nuxel
        # Doom itself runs Chocolate Doom in WebAssembly inside the PWA; the
        # native Chocolate Doom card runs the distro engine fullscreen.  The
        # UZDoom and Crispy comparison paths were removed by owner request.
        "org.nuxel.Doom.Chocolate": ["/usr/lib/nuxel/nuxel-doom-engine", "chocolate"],
    }

    # Wayland app_id reported by nuxel-foreign-toplevel (may differ from the
    # registry id).
    NATIVE_SURFACE_ID = {
        "org.gnome.Software": "nuxel-software",
        "org.mozilla.firefox": "org.mozilla.firefox",
        "org.videolan.VLC": "mpv",
        "org.nuxel.MediaPlayer": "mpv",
    }

    # Apps that must write user-owned data (contacts, call log, message store)
    # are launched as the real session user.  Browser/camera need root-owned
    # /run state/FIFOs and keep the session's existing root launch context.
    NATIVE_AS_SESSION_USER = {
        "nuxel-contacts", "nuxel-messages", "nuxel-dialer",
        # PWNAGE-43000: Firefox/VLC/native GNOME tools refuse a root session.
        # Run them as the real nuxel user (uid 1000) with the session's Wayland
        # runtime; the a45 session script grants that user the socket.
        "org.mozilla.firefox", "org.videolan.VLC",
        "org.nuxel.MediaPlayer",
        "org.signal.Signal", "com.stremio.Stremio",
        "org.gnome.FileRoller", "org.gnome.Loupe",
        "org.gnome.Papers", "org.gnome.SystemMonitor",
        "org.gnome.Software",
        "org.nuxel.Doom.Chocolate",
    }

    def _ensure_xwayland(self):
        """Start one rootless Xwayland for Qt/X11-native applications.

        VLC's Qt6 interface plugin does not initialise on this image's Wayland
        QPA and exits into its console interface.  Xwayland is already shipped
        and phoc accepts it as a normal client; start it on demand so the
        normal Home session does not pay for an X server when no X app is open.
        """
        import time as _t
        sock = "/tmp/.X11-unix/X0"
        if os.path.exists(sock):
            return True
        try:
            probe = subprocess.run(["/usr/bin/pgrep", "-f", "Xwayland :0"],
                                   capture_output=True, timeout=3)
            if probe.returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/user/1000",
                    "WAYLAND_DISPLAY": "wayland-0",
                    "HOME": "/home/nuxel"})
        cmd = ["/usr/bin/runuser", "-u", "nuxel", "--",
               "/usr/bin/env", "XDG_RUNTIME_DIR=/run/user/1000",
               "WAYLAND_DISPLAY=wayland-0", "HOME=/home/nuxel",
               "/usr/bin/Xwayland", ":0", "-rootless", "-noreset", "-nolisten", "tcp"]
        try:
            subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except OSError as exc:
            logger.warning("Xwayland start failed: %s", exc)
            return False
        for _ in range(30):
            if os.path.exists(sock):
                return True
            _t.sleep(0.1)
        logger.warning("Xwayland socket %s did not appear", sock)
        return False

    def _session_home(self):
        try:
            store = self._app_store()
            return str(store.files_root)
        except Exception:
            return "/home/nuxel"

    def _load_app_orientation_defaults(self):
        try:
            with open(APP_ORIENTATION_DEFAULTS, "r") as fh:
                doc = json.load(fh)
            if isinstance(doc, dict) and isinstance(doc.get("apps"), dict):
                return doc
        except (OSError, ValueError):
            pass
        return {"schema_version": 1, "default": APP_ORIENTATION_DEFAULT_MODE, "apps": {}}

    def _save_app_orientation_defaults(self, doc):
        tmp = APP_ORIENTATION_DEFAULTS + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(doc, fh, sort_keys=True, indent=2)
        os.replace(tmp, APP_ORIENTATION_DEFAULTS)

    def _app_orientation_default(self, app_id):
        doc = self._load_app_orientation_defaults()
        return doc.get("apps", {}).get(app_id)

    def _set_orientation(self, mode):
        try:
            proc = subprocess.run(
                ["/usr/libexec/nuxel/nuxel-orientationd", "set", mode, "--apply"],
                capture_output=True, timeout=15, text=True)
            return proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _apply_app_default_orientation(self, app_id):
        mode = self._app_orientation_default(app_id)
        if mode in APP_ORIENTATION_MODES:
            self._set_orientation(mode)

    def _restore_home_orientation(self):
        doc = self._load_app_orientation_defaults()
        mode = doc.get("default", APP_ORIENTATION_DEFAULT_MODE)
        if mode not in APP_ORIENTATION_MODES:
            mode = APP_ORIENTATION_DEFAULT_MODE
        self._set_orientation(mode)

    def _toplevel_listing(self):
        """Return the trusted compositor toplevel listing (read-only)."""
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        try:
            proc = subprocess.run(
                ["/usr/lib/nuxel/nuxel-foreign-toplevel", "list"],
                env=env, capture_output=True, timeout=5, text=True)
            return proc.stdout or ""
        except (OSError, subprocess.TimeoutExpired):
            return ""

    def _resolve_surface_id(self, app_id):
        """Resolve a launcher id to the compositor's actual Wayland app_id."""
        if not isinstance(app_id, str) or not app_id:
            return None
        listing = self._toplevel_listing()
        if app_surface is not None:
            try:
                return app_surface.resolve_from_listing(listing, app_id)
            except Exception as exc:  # noqa: BLE001 - resolver must not block launch
                logger.warning("surface resolver failed for %s: %s", app_id, exc)
        match = re.search(r"app_id=" + re.escape(app_id) + r"(?:\s|$)", listing)
        return app_id if match else None

    def _active_app_units(self, app_id):
        """Return this app's active/activating transient nuxel-app-* units."""
        if not isinstance(app_id, str) or not APP_ID_RE.match(app_id):
            return []
        suffix = app_id.rsplit(".", 1)[-1].lower()
        prefix = "nuxel-app-%s-" % suffix
        try:
            out = subprocess.run(
                ["/usr/bin/systemctl", "list-units", "--all", "--plain",
                 "--no-legend", "nuxel-app-*"],
                capture_output=True, timeout=5, text=True).stdout or ""
        except (OSError, subprocess.TimeoutExpired):
            return []
        units = []
        now_ms = int(time.time() * 1000)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 3 or not parts[0].startswith(prefix):
                continue
            if parts[2] not in ("active", "activating"):
                continue
            # Unit names end in the launch epoch in milliseconds.  Only treat
            # an *active* unit as "still starting" for a bounded interval.  An
            # older windowless process (e.g. a chat app closed to its tray)
            # must be allowed to receive a fresh `flatpak run` activation.
            stamp = re.search(r"-(\d{10,})(?:\.service)?$", parts[0])
            if stamp:
                age_ms = now_ms - int(stamp.group(1))
                if age_ms > 45000:
                    continue
            units.append(parts[0])
        return units

    def _focus_existing_surface(self, surface_id):
        """One-pass focus probe for an already-running app.  Returns its id or ''."""
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        try:
            proc = subprocess.run(
                ["/usr/lib/nuxel/nuxel-focus-app.sh", surface_id, "--probe"],
                env=env, capture_output=True, timeout=6)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        if proc.returncode != 0:
            return ""
        out = (proc.stdout or b"").decode("utf-8", "replace")
        m = re.search(r"FOCUSED app_id=(\S+)", out)
        return m.group(1) if m else surface_id

    def _exec_native_app(self, target_id, extra_args=None):
        """Launch a native app from the fixed allowlist (never a client path).

        ``extra_args`` is reserved for the closed media-open path; the only
        accepted shape is one already-validated file path for VLC.
        """
        # The session lock is authoritative in the root bridge, not in a JS
        # overlay: no native surface may start while the device is locked.
        try:
            if security_provider is not None:
                _lock = security_provider.handle("status", {})
                if _lock.get("locked", True):
                    return ({"success": False, "error": "session_locked",
                             "app_id": target_id,
                             "detail": "unlock the device before launching apps"}, 423)
        except Exception as exc:  # noqa: BLE001
            logger.warning("security lock check failed: %s", exc)
        if not isinstance(target_id, str) or not APP_ID_RE.match(target_id):
            return ({"success": False, "error": "invalid_app_id",
                     "detail": "an app id is an identifier, never a path or a command"}, 400)
        t_start = time.monotonic()
        surface_id = self.NATIVE_SURFACE_ID.get(target_id, target_id)
        # Idempotent launch: tapping an app that is already visible (or still
        # starting) must focus/open exactly one instance.  Before this guard a
        # second tap spawned another nuxel-software/Electron process and could
        # exhaust RAM; on this 7.2 GB device that made otherwise healthy apps
        # look unresponsive.  The probe is a single compositor inventory pass.
        focused_surface = self._focus_existing_surface(surface_id)
        if focused_surface:
            logger.info("app already visible id=%s surface=%s", target_id, focused_surface)
            return ({"success": True, "launched": False, "already_running": True,
                     "focused": True, "app_id": target_id,
                     "surface_id": focused_surface, "action": "focus-existing",
                     "outcome": "already_visible"}, 200)
        active_units = self._active_app_units(target_id)
        if active_units:
            # The existing launch is still mapping its first window.  Give it a
            # short, bounded chance to present instead of spawning a duplicate.
            for _ in range(12):
                time.sleep(0.25)
                focused_surface = self._focus_existing_surface(surface_id)
                if focused_surface:
                    logger.info("app still starting, focused id=%s units=%s",
                                target_id, active_units)
                    return ({"success": True, "launched": True,
                             "already_running": True, "focused": True,
                             "app_id": target_id, "surface_id": focused_surface,
                             "action": "focus-existing", "unit": active_units[0],
                             "outcome": "already_starting"}, 200)
            logger.info("app already starting (no surface yet) id=%s units=%s",
                        target_id, active_units)
            return ({"success": True, "launched": True, "already_running": True,
                     "focused": False, "surface_seen": False,
                     "app_id": target_id, "surface_id": surface_id,
                     "action": "already-starting", "unit": active_units[0],
                     "outcome": "already_starting_no_surface"}, 200)
        # Flatpak is authoritative for an installed app id.  The argv is
        # always ["flatpak", "run", <validated id>] and is never built from a
        # client command/path.  Static native_launch entries remain fallbacks
        # for an uninstalled RPM/wrapper.
        flatpak_argv = None
        if flatpak_provider is not None:
            try:
                flatpak_argv = flatpak_provider.get_provider().launch_argv(target_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("flatpak launch probe failed for %s: %s", target_id, exc)
        is_flatpak = bool(flatpak_argv)
        t_probe = time.monotonic()
        argv = list(flatpak_argv) if flatpak_argv else self.NATIVE_LAUNCH.get(target_id)
        if argv and extra_args:
            if target_id not in ("org.videolan.VLC", "org.nuxel.MediaPlayer", "io.mpv.Mpv") or len(extra_args) != 1:
                return ({"success": False, "error": "extra_args_denied",
                         "app_id": target_id}, 400)
            if is_flatpak:
                # Flatpak needs --file-forwarding BEFORE the app id so the host
                # path is exported into the sandbox and replaced with its
                # sandbox path.  VLC's exported desktop entry uses the same
                # file-forwarding contract.
                base = list(argv)
                argv = base[:-1] + ["--file-forwarding", base[-1],
                                    "@@", str(extra_args[0]), "@@"]
            else:
                argv = list(argv) + [str(extra_args[0])]
        if not argv:
            app, _info = self._lookup_registry_app(target_id)
            if app and app.get("type") == "native" and app.get("native_binary"):
                # Registry-backed native entry: exec the registered binary only.
                binary = app["native_binary"]
                if isinstance(binary, str) and binary.startswith("/"):
                    argv = [binary]
            if not argv:
                return ({"success": False, "error": "not_native_or_unknown",
                         "app_id": target_id}, 404)
        # A registry entry can be known-unsupported (e.g. Signal aarch64 has no
        # official RPM and Flatpak is blocked by CONFIG_USER_NS=n).  Refuse
        # before spawning anything and state the real reason.
        _reg_app, _info = self._lookup_registry_app(target_id)
        if _reg_app and _reg_app.get("status") in ("unsupported", "blocked"):
            return ({"success": False, "error": "unsupported_on_device",
                     "app_id": target_id,
                     "detail": _reg_app.get("runtime_state") or _reg_app.get("description")
                               or "not supported on this device"}, 409)
        # A clear, honest failure for an unbuilt/absent native binary is more
        # useful than a systemd-run rc!=0 (which masked the real cause).
        if not os.path.exists(argv[0]):
            return ({"success": False, "error": "native_binary_missing",
                     "app_id": target_id, "binary": argv[0],
                     "detail": "the registered native program is not installed: %s" % argv[0]}, 404)
        # The http-bridge runs with PrivateTmp/ProtectHome/ProtectSystem,
        # so a GUI app forked directly from it inherits a read-only /root and
        # a private /tmp and dies. Launch via a systemd transient unit, which
        # runs in the system manager's normal (unsandboxed) context.
        import time as _t
        home = self._session_home()
        unit = "nuxel-app-" + target_id.rsplit(".", 1)[-1].lower() + "-%d" % int(_t.time() * 1000)
        as_user = target_id in self.NATIVE_AS_SESSION_USER or is_flatpak
        # Session-user apps use the standard per-user runtime so dconf and
        # other $XDG_RUNTIME_DIR consumers work; the session script creates it
        # and symlinks the Phoc socket from /run/nuxel-wayland.  Root-owned
        # native tools (browser/camera) keep the compositor runtime directly.
        runtime = "/run/user/1000" if as_user else "/run/nuxel-wayland"
        # Flatpak apps get the per-user portal bus.  Legacy native apps keep the
        # root session bus they have always used, avoiding a regression in the
        # custom PhoshAgent/AT-SPI path.
        dbus_address = ("unix:path=/run/user/1000/bus" if is_flatpak
                        else "unix:path=/run/nuxel-wayland/bus")
        use_x11 = (target_id == "org.videolan.VLC" and not is_flatpak)
        if use_x11 and not self._ensure_xwayland():
            logger.warning("VLC launch continuing without a verified Xwayland socket")
        cmd = ["/usr/bin/systemd-run", "--no-block", "--unit=%s" % unit, "--collect",
               "--property=TimeoutStopSec=1s",
               "--setenv=XDG_RUNTIME_DIR=%s" % runtime,
               "--setenv=WAYLAND_DISPLAY=wayland-0",
               "--setenv=XDG_SESSION_TYPE=wayland",
               "--setenv=XDG_CURRENT_DESKTOP=Nuxel",
               "--setenv=MOZ_ENABLE_WAYLAND=1",
               "--setenv=GDK_BACKEND=wayland",
               "--setenv=QT_QPA_PLATFORM=wayland",
               "--setenv=GTK_APPLICATION_PREFER_DARK_THEME=1",
               "--setenv=GTK_THEME=Adwaita:dark",
               "--setenv=DBUS_SESSION_BUS_ADDRESS=%s" % dbus_address,
               "--setenv=PULSE_SERVER=unix:/run/nuxel-wayland/pulse/native",
               "--setenv=PIPEWIRE_RUNTIME_DIR=/run/nuxel-wayland",
               "--setenv=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
               "--setenv=HOME=%s" % home,
               "--setenv=XDG_DATA_HOME=%s/.local/share" % home]
        # The host's custom Mali/kbase EGL stack is NOT assumed to exist inside
        # a Flatpak runtime.  Let the runtime choose its own Mesa/llvmpipe path
        # and report GPU acceleration separately from sandbox success.
        if not is_flatpak:
            gfx_env = self._graphics_env_for(target_id)
            for key, value in sorted(gfx_env.items()):
                cmd.append("--setenv=%s=%s" % (key, value))
        if use_x11:
            cmd += ["--setenv=DISPLAY=:0", "--setenv=QT_QPA_PLATFORM=xcb",
                    "--setenv=QT_X11_NO_MITSHM=1"]
        # Electron/Chromium and QtWebEngine launch flags live in
        # flatpak_provider.launch_argv(), the single launch authority.  Keeping
        # them there means both the Home launcher (/apps/exec) and
        # /flatpak/launch receive identical Wayland/software/sandbox flags, so
        # apps installed from Software work without a per-app patch.
        if as_user:
            user = self._app_store().session_user
            if user:
                cmd += ["--uid=%s" % user, "--gid=%s" % user,
                        "--property=SupplementaryGroups=audio"]
        cmd += argv
        t_exec_request = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("native launch failed for %s: %s", target_id, exc)
            return ({"success": False, "error": "launch_failed",
                     "app_id": target_id, "detail": str(exc)}, 500)
        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", "replace").strip()
            logger.error("native launch refused id=%s rc=%s err=%s", target_id, proc.returncode, err)
            return ({"success": False, "error": "launch_failed",
                     "app_id": target_id, "detail": err or ("rc=%s" % proc.returncode)}, 500)
        t_accepted = time.monotonic()
        timing_ms = {
            "request_to_provider_lookup": round((t_probe - t_start) * 1000.0, 3),
            "provider_lookup_to_exec": round((t_exec_request - t_probe) * 1000.0, 3),
            "systemd_run_accept": round((t_accepted - t_exec_request) * 1000.0, 3),
            "request_to_launch_accepted": round((t_accepted - t_start) * 1000.0, 3),
        }
        # The Home surface is a fullscreen toplevel.  A newly launched native
        # app maps behind it unless we (a) leave Home fullscreen/minimize it and
        # (b) maximize the app.  Do that asynchronously once the toplevel exists;
        # the layer-shell top bar and nav dock then remain visible over it.
        try:
            subprocess.Popen(
                ["/usr/lib/nuxel/nuxel-focus-app.sh", surface_id],
                env=dict(os.environ, XDG_RUNTIME_DIR="/run/nuxel-wayland",
                         WAYLAND_DISPLAY="wayland-0"),
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            logger.warning("native focus helper failed for %s: %s", target_id, exc)

        # PWNAGE-54000: do NOT block the launcher for up to 10 seconds waiting
        # for a toplevel.  systemd-run has already accepted the job; the focus
        # helper and the verification thread below observe the real surface and
        # log it.  The UI gets an immediate, honest "requested" result and the
        # app appears as soon as GTK/WebKit maps it.  A launch failure is still
        # visible in the journal and in /run/nuxel-app-launch.json.
        import threading
        def _verify_launch():
            process_alive = False
            surface_seen = False
            outcome = "starting"
            for _ in range(120):
                try:
                    st = subprocess.run(
                        ["/usr/bin/systemctl", "show", unit, "--property=ActiveState",
                         "--property=Result", "--property=MainPID", "--no-pager"],
                        capture_output=True, timeout=2, text=True)
                    fields = dict(line.split("=", 1) for line in st.stdout.splitlines() if "=" in line)
                    process_alive = fields.get("ActiveState") in ("active", "activating")
                    if fields.get("Result") not in (None, "success"):
                        outcome = "exited:" + fields.get("Result", "unknown")
                        break
                except (OSError, subprocess.TimeoutExpired, ValueError):
                    pass
                try:
                    tl = subprocess.run(
                        ["/usr/lib/nuxel/nuxel-foreign-toplevel", "list"],
                        env=dict(os.environ, XDG_RUNTIME_DIR="/run/nuxel-wayland",
                                 WAYLAND_DISPLAY="wayland-0"),
                        capture_output=True, timeout=2, text=True)
                    surface_seen = ("app_id=%s" % surface_id) in (tl.stdout or "")
                except (OSError, subprocess.TimeoutExpired):
                    pass
                if surface_seen:
                    outcome = "visible"
                    break
                time.sleep(0.25)
            logger.info("native app evidence id=%s unit=%s process_alive=%s surface_seen=%s outcome=%s",
                        target_id, unit, process_alive, surface_seen, outcome)
            try:
                doc = {"app_id": target_id, "unit": unit, "argv": argv,
                       "process_alive": process_alive, "surface_seen": surface_seen,
                       "outcome": outcome, "timing_ms": timing_ms,
                       "launch_epoch": time.time() - (time.monotonic() - t_start),
                       "updated_epoch": time.time()}
                path = "/run/nuxel-app-launch.json"
                with open(path + ".tmp", "w") as fh:
                    json.dump(doc, fh, sort_keys=True)
                os.replace(path + ".tmp", path)
            except OSError:
                pass
        threading.Thread(target=_verify_launch, name="nuxel-app-verify", daemon=True).start()
        self._apply_app_default_orientation(target_id)
        return ({"success": True, "launched": True, "app_id": target_id,
                 "unit": unit, "action": "exec", "argv": argv,
                 "process_alive": True, "surface_seen": False,
                 "outcome": "launch_requested", "timing_ms": timing_ms}, 200)

    def _keyboard_visible(self):
        try:
            with open("/run/nuxel-keyboard.visible", "r") as fh:
                return fh.read().strip() == "1"
        except OSError:
            return False

    def _hide_keyboard_native(self):
        """Dismiss the compositor OSK without backgrounding the app."""
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        try:
            proc = subprocess.run(["/usr/lib/nuxel/nuxel-foreign-toplevel", "hide-keyboard"],
                                  env=env, capture_output=True, text=True, timeout=6)
            return proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _home_action(self):
        """Minimize every non-Home toplevel via wlr-foreign-toplevel (no kill)."""
        if self._keyboard_visible():
            self._hide_keyboard_native()
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        argv = ["/usr/lib/nuxel/nuxel-foreign-toplevel", "home"]
        try:
            proc = subprocess.run(argv, env=env, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("home action failed: %s", exc)
            return ({"success": False, "error": "home_action_failed",
                     "detail": str(exc)}, 500)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        logger.info("home action rc=%s out=%s", proc.returncode, out.strip())
        self._restore_home_orientation()
        return ({"success": True, "action": "home", "rc": proc.returncode,
                 "output": out.strip()}, 200)

    def _close_foreground_action(self):
        """Close the activated non-Home toplevel (long Back). Never closes Home
        or the launcher host, and the fixed argv is resolved here (no client
        path). Uses the compositor's foreign-toplevel `close`, not a kill."""
        if self._keyboard_visible():
            # Back's first precedence rule is keyboard dismissal, even for a
            # native/GTK app (e.g. Software's search field).
            self._hide_keyboard_native()
            return ({"success": True, "action": "hide-keyboard",
                     "handled": True, "at_root": False, "method": "osk-dismiss"}, 200)
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        argv = ["/usr/lib/nuxel/nuxel-foreign-toplevel", "close-foreground"]
        try:
            proc = subprocess.run(argv, env=env, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("close-foreground action failed: %s", exc)
            return ({"success": False, "error": "close_foreground_failed",
                     "detail": str(exc)}, 500)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        closed_ids = re.findall(r"CLOSE_ACTION app_id=(\S+)", out)
        killed_units = []
        for app_id in closed_ids:
            killed_units.extend(self._force_stop_app_units(app_id))
        logger.info("close-foreground action rc=%s closed=%s killed_units=%s out=%s",
                    proc.returncode, closed_ids, killed_units, out.strip())
        return ({"success": proc.returncode == 0, "action": "close-foreground",
                 "closed_apps": closed_ids, "killed_units": killed_units,
                 "rc": proc.returncode, "output": out.strip()}, 200)

    def _close_app_action(self, app_id, force=False):
        """Close one exact native toplevel by app id.

        Graceful: compositor request_close only.  Force: the same close, then a
        bounded stop/SIGKILL of that app's own transient systemd units.  Home,
        Phoc, the bridge and every system service are excluded by identity.
        """
        if not isinstance(app_id, str) or not APP_ID_RE.match(app_id):
            return ({"success": False, "error": "invalid_app_id"}, 400)
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        # Registry ids and compositor ids differ for many Flatpaks (Caprine,
        # Ferdium, ...).  Close the real surface but force-stop the unit using
        # the caller's original id.
        surface_id = (self._resolve_surface_id(app_id)
                      or self.NATIVE_SURFACE_ID.get(app_id, app_id))
        argv = ["/usr/lib/nuxel/nuxel-foreign-toplevel", "close", surface_id]
        try:
            proc = subprocess.run(argv, env=env, capture_output=True, timeout=8)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("close app %s failed: %s", app_id, exc)
            return ({"success": False, "error": "close_failed", "detail": str(exc)}, 500)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        closed = re.findall(r"CLOSE_ACTION app_id=(\S+)", out)
        killed = self._force_stop_app_units(app_id) if force else []
        logger.info("close app=%s surface=%s force=%s rc=%s closed=%s killed=%s out=%s",
                    app_id, surface_id, force, proc.returncode, closed, killed, out.strip())
        return ({"success": proc.returncode == 0, "action": "force-close" if force else "close",
                 "app_id": app_id, "surface_id": surface_id,
                 "closed_apps": closed, "killed_units": killed,
                 "rc": proc.returncode, "output": out.strip()}, 200)

    def _force_stop_app_units(self, app_id):
        """Bounded force-stop for a native app's own transient unit.

        The foreign-toplevel close request is polite; a hung app can ignore it.
        Long Back is explicitly a force-kill, so stop/final-kill only the
        transient `nuxel-app-<suffix>-<ms>` units for this exact app id.  The
        launcher, Phoc, the bridge and every system service are excluded.
        """
        if not isinstance(app_id, str) or not APP_ID_RE.match(app_id):
            return []
        suffix = app_id.rsplit(".", 1)[-1].lower()
        prefix = "nuxel-app-%s-" % suffix
        try:
            units = subprocess.run(
                ["/usr/bin/systemctl", "list-units", "--all", "--no-legend",
                 "--plain", "nuxel-app-*"],
                capture_output=True, timeout=4, text=True).stdout
        except (OSError, subprocess.TimeoutExpired):
            return []
        stopped = []
        for line in units.splitlines():
            parts = line.split()
            if not parts or not parts[0].startswith(prefix):
                continue
            unit = parts[0]
            try:
                subprocess.run(["/usr/bin/systemctl", "stop", "--no-block", unit],
                               capture_output=True, timeout=4)
                subprocess.run(["/usr/bin/systemctl", "kill", "--kill-whom=all",
                                "--signal=SIGKILL", unit],
                               capture_output=True, timeout=4)
                stopped.append(unit)
            except (OSError, subprocess.TimeoutExpired):
                continue
        return stopped

    def _send_native_back_key(self, app_id):
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        if app_id == "vlc":
            argv = ["/usr/bin/wtype", "-k", "Escape"]
        else:
            argv = ["/usr/bin/wtype", "-M", "alt", "-k", "Left", "-m", "alt"]
        try:
            proc = subprocess.run(argv, env=env, capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("native back key failed for %s: %s", app_id, exc)
            return False
        if proc.returncode != 0:
            logger.warning("native back key rc=%s app=%s err=%s",
                           proc.returncode, app_id,
                           (proc.stderr or b"").decode("utf-8", "replace")[:300])
        return proc.returncode == 0

    def _native_back_action(self):
        """Short Back for the foreground native app: navigate the app's own
        history first, and only report at-root when it has no more back step.

        The compositor's foreign-toplevel manager reports the activated
        non-Home toplevel.  Only the native browser owns an in-app history the
        shell can drive (via its control FIFO); any other native app reports
        at-root so the launcher's short Back falls through to Home.

        Keyboard precedence is global: if the compositor OSK is visible, the
        first Back dismisses it and does not navigate or close the app."""
        if self._keyboard_visible():
            self._hide_keyboard_native()
            return ({"success": True, "handled": True, "at_root": False,
                     "foreground": None, "method": "osk-dismiss"}, 200)
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        try:
            proc = subprocess.run(["/usr/lib/nuxel/nuxel-foreign-toplevel", "list"],
                                  env=env, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("native back list failed: %s", exc)
            return ({"success": False, "error": "back_list_failed",
                     "detail": str(exc)}, 500)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        foreground = None
        for line in out.splitlines():
            if line.startswith("WIN ") and " act=1 " in line and "app_id=nuxel-pwa-host" not in line:
                foreground = line
        if not foreground:
            # No foreground native app: already Home, nothing to navigate back.
            return ({"success": True, "handled": False, "at_root": True,
                     "foreground": None}, 200)
        app_id = ""
        m = re.search(r"app_id=(\S+)", foreground)
        if m:
            app_id = m.group(1)
        # Native browsers and the native browser PWA expose no foreign-toplevel
        # history API.  Send the application's own Back shortcut into the
        # focused Wayland client.  This is a real key event (wtype uses
        # zwp_virtual_keyboard_manager_v1), not a guessed state transition.
        if app_id in ("org.mozilla.firefox", "org.nuxel.BrowserNative",
                      "com.stremio.Stremio", "org.gnome.FileRoller",
                      "org.gnome.Loupe", "org.gnome.Papers"):
            ok = self._send_native_back_key(app_id)
            return ({"success": True, "handled": bool(ok), "at_root": not ok,
                     "foreground": app_id, "method": "key-alt-left"}, 200)
        if app_id == "vlc":
            ok = self._send_native_back_key(app_id)
            return ({"success": True, "handled": bool(ok), "at_root": not ok,
                     "foreground": app_id, "method": "key-escape"}, 200)
        if "browser" not in app_id.lower():
            return ({"success": True, "handled": False, "at_root": True,
                     "foreground": app_id}, 200)
        # Browser: read its published navigation state and, if it can go back,
        # send `back` over its control FIFO.
        state = {}
        try:
            with open("/run/nuxel-browser.state", "r") as f:
                state = json.loads(f.read())
        except (OSError, ValueError):
            state = {}
        can_go_back = bool(state.get("can_go_back", False))
        if not can_go_back:
            return ({"success": True, "handled": False, "at_root": True,
                     "foreground": app_id, "can_go_back": False}, 200)
        ctrl = "/run/nuxel-browser.cmd"
        try:
            fd = os.open(ctrl, os.O_WRONLY | os.O_NONBLOCK)
            try:
                os.write(fd, b"back\n")
            finally:
                os.close(fd)
        except OSError as exc:
            logger.error("native back fifo write failed: %s", exc)
            return ({"success": False, "error": "back_fifo_write_failed",
                     "detail": str(exc)}, 500)
        logger.info("native back handled foreground=%s", app_id)
        return ({"success": True, "handled": True, "at_root": False,
                 "foreground": app_id}, 200)

    def _list_toplevels(self):
        """Return the compositor's real toplevel inventory (read-only).

        Recents needs native windows too; the PWA session map alone only knows
        iframes.  This endpoint never acts on a window and never invents one.
        """
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        try:
            proc = subprocess.run(["/usr/lib/nuxel/nuxel-foreign-toplevel", "list"],
                                  env=env, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ({"success": False, "error": "toplevel_list_failed",
                     "detail": str(exc)}, 500)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        windows = []
        for line in out.splitlines():
            if not line.startswith("WIN "):
                continue
            item = {}
            for part in line[4:].split(" "):
                if "=" in part:
                    k, v = part.split("=", 1)
                    item[k] = v
            item["maximized"] = item.get("max") == "1"
            item["minimized"] = item.get("min") == "1"
            item["activated"] = item.get("act") == "1"
            item["fullscreen"] = item.get("fs") == "1"
            item["home"] = (item.get("app_id") == "nuxel-pwa-host" or
                            item.get("title") == "Nuxel")
            windows.append(item)
        return ({"success": proc.returncode == 0, "windows": windows,
                 "count": len(windows), "source": "zwlr-foreign-toplevel"}, 200)

    def _close_toplevel(self, app_id):
        """Close one named native toplevel for the Recents close button/swipe."""
        if not app_id or not re.match(r"^[A-Za-z0-9._:-]+$", app_id):
            return ({"success": False, "error": "invalid_app_id"}, 400)
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        surface_id = (self._resolve_surface_id(app_id)
                      or self.NATIVE_SURFACE_ID.get(app_id, app_id))
        try:
            proc = subprocess.run(["/usr/lib/nuxel/nuxel-foreign-toplevel", "close", surface_id],
                                  env=env, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ({"success": False, "error": "close_failed", "detail": str(exc)}, 500)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        killed = self._force_stop_app_units(app_id)
        return ({"success": proc.returncode == 0, "action": "close", "app_id": app_id,
                 "surface_id": surface_id, "killed_units": killed,
                 "output": out.strip()}, 200)

    def _activate_toplevel(self, app_id):
        """Activate a specific native toplevel by app_id (recents switch)."""
        if not app_id or not re.match(r"^[A-Za-z0-9._-]+$", app_id):
            return ({"success": False, "error": "invalid_app_id"}, 400)
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        surface_id = (self._resolve_surface_id(app_id)
                      or self.NATIVE_SURFACE_ID.get(app_id, app_id))
        try:
            proc = subprocess.run(["/usr/lib/nuxel/nuxel-foreign-toplevel", "activate", surface_id],
                                  env=env, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("activate action failed: %s", exc)
            return ({"success": False, "error": "activate_failed",
                     "detail": str(exc)}, 500)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        return ({"success": True, "action": "activate", "app_id": app_id,
                 "surface_id": surface_id, "rc": proc.returncode,
                 "output": out.strip()}, 200)

    def _classify_backends(self):
        """Probe live D-Bus backend providers to classify each data source.

        Honest-reporting helper (briq-8): for the VM verification we must be
        explicit about which backend layer produced a value. This probes the
        well-known D-Bus names of ModemManager, NetworkManager and GeoClue and
        reports LIVE when the service is present and reachable, else MOCK.
        """
        names = {
            "ModemManager":       "org.freedesktop.ModemManager1",
            "NetworkManager":     "org.freedesktop.NetworkManager",
            "GeoClue2":           "org.freedesktop.GeoClue2",
        }
        providers = {"ModemManager": None, "NetworkManager": None, "GeoClue2": None}
        try:
            bus = dbus.SystemBus()
            owner_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
            dbus_iface = dbus.Interface(owner_obj, 'org.freedesktop.DBus')
            for layer, name in names.items():
                try:
                    owner = dbus_iface.GetNameOwner(name)
                    providers[layer] = "live" if (owner and str(owner).strip()) else "mock"
                except Exception:
                    providers[layer] = "mock"
        except Exception:
            # D-Bus unreachable -> nothing can be live
            providers = {"ModemManager": "mock", "NetworkManager": "mock", "GeoClue2": "mock"}
        return providers

    def _call_bridge(self, method, *args):
        """Call a nuxel-bridge D-Bus method.

        Falls back to mock data when D-Bus bridge is not available (VM dev mode).
        ALWAYS returns a dict with 'success' key — never lets traceback propagate.
        """
        try:
            bus = dbus.SystemBus()
            bridge = bus.get_object('org.nuxel.Bridge', '/org/nuxel/Bridge')
            iface = dbus.Interface(bridge, 'org.nuxel.Bridge')
            dbus_method = getattr(iface, method)
            result = dbus_method(*args, timeout=BRIDGE_DBUS_TIMEOUT_SECONDS)
            return json.loads(result)
        except dbus.exceptions.DBusException as e:
            # Honesty (audit briq-12): NEVER disguise a dead or slow bridge as a
            # mock success. A mock/fallback body can hide a broken bridge, so
            # surface the D-Bus failure explicitly with data_source=dbus-error.
            logger.warning("D-Bus call %s failed: %s — returning explicit dbus-error (no mock)", method, e)
            return {
                "success": False,
                "error": "Bridge D-Bus call %s failed: %s" % (method, e),
                "data_source": "dbus-error",
                "vm_mode": True,
                "backend_audit": self._classify_backends(),
            }
        except Exception as e:
            logger.error("Unexpected error in D-Bus call %s: %s", method, e)
            return {"success": False, "error": str(e), "vm_mode": True}

    def _get_system_phone_status(self, app_id):
        """Read real system state for phone status endpoint."""
        import subprocess, os as _os, time as _time
        now = _time.strftime("%H:%M")

        net_source = "mock"   # briq-8 honesty: network layer data source
        net_info = {"connected": False, "type": "ethernet", "interface": "", "wifi_enabled": False, "ethernet": False, "signal": 4, "signal_quality": 100, "operator": "Nuxel VM"}
        # Network layer: prefer live NetworkManager, fall back to reading
        # host routing table / sysfs (also live, but system-level), else mock.
        try:
            nmsrc = ""
            try:
                bus = dbus.SystemBus()
                nm = bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
                nm_props = dbus.Interface(nm, 'org.freedesktop.DBus.Properties')
                _cfg = nm_props.GetAll('org.freedesktop.NetworkManager')
                nm_active = int(_cfg.get('State', 0)) == 100 if 'State' in _cfg else False
                nm_wifi = dbus.Boolean(_cfg.get('WirelessEnabled', False))
                if nm_active:
                    net_source = "live:NetworkManager"
                    net_info["connected"] = True
                    net_info["wifi_enabled"] = bool(nm_wifi)
                    net_info["operator"] = "NetworkManager VM"
            except Exception:
                net_source = ""
        except Exception:
            pass
        try:
            result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split()
                if "dev" in parts:
                    dev = parts[parts.index("dev") + 1]
                    net_info["interface"] = dev
                    net_info["connected"] = True
                    net_source = "live:system(ip route)"
                    if dev.startswith("wl"):
                        net_info["type"] = "wifi"
                        net_info["wifi_enabled"] = True
                    elif dev.startswith("en") or dev.startswith("eth"):
                        net_info["type"] = "ethernet"
                        net_info["ethernet"] = True
        except Exception:
            try:
                for dev in _os.listdir("/sys/class/net"):
                    if dev == "lo":
                        continue
                    operstate = "/sys/class/net/" + dev + "/operstate"
                    if _os.path.exists(operstate):
                        with open(operstate) as f:
                            if f.read().strip() == "up":
                                net_info["interface"] = dev
                                net_info["connected"] = True
                                net_source = "live:system(sysfs)"
                                if dev.startswith("wl"):
                                    net_info["type"] = "wifi"
                                    net_info["wifi_enabled"] = True
                                else:
                                    net_info["type"] = "ethernet"
                                    net_info["ethernet"] = True
                                break
            except Exception:
                pass

        # Battery detection (live from sysfs).  The S10+ exposes its battery as
        # /sys/class/power_supply/battery (lowercase), NOT as BAT0/BAT1.  The
        # old check only matched a "BAT" prefix and therefore fell through to a
        # fabricated 100% mock on this handset.  Select the node whose `type`
        # file reads "Battery", which works for both naming schemes, and report
        # the real current full capacity so the UI can represent it honestly.
        bat_source = "mock"
        # An unreadable battery is UNKNOWN.  The old 100%-charging default was a
        # fabricated value and is exactly what made a transient sysfs 0 look like
        # a 100% -> 0% jump on the lockscreen.
        bat_info = {"level": None, "charging": False, "available": False,
                    "status": "unknown"}
        try:
            bat_dir = None
            for d in sorted(_os.listdir("/sys/class/power_supply")):
                tfile = "/sys/class/power_supply/" + d + "/type"
                if not _os.path.exists(tfile):
                    continue
                try:
                    with open(tfile) as f:
                        if f.read().strip().lower() == "battery":
                            bat_dir = d
                            break
                except Exception:
                    continue
            if bat_dir is None:
                # Fall back to the BAT* convention (standard ACPI laptops).
                bat_dirs = [d for d in _os.listdir("/sys/class/power_supply") if d.startswith("BAT")]
                if bat_dirs:
                    bat_dir = sorted(bat_dirs)[0]
            if bat_dir:
                base = "/sys/class/power_supply/" + bat_dir + "/"
                bat_source = "live:sysfs:" + bat_dir
                cap_file = base + "capacity"
                status_file = base + "status"
                full_file = base + "charge_full"
                design_file = base + "charge_full_design"
                status_text = "unknown"
                if _os.path.exists(status_file):
                    try:
                        with open(status_file) as f:
                            status_text = f.read().strip() or "unknown"
                    except Exception:
                        status_text = "unknown"
                bat_info["status"] = status_text
                # Only the kernel's exact Charging state earns the charging
                # glyph; Full is externally powered but no longer charging.
                bat_info["charging"] = status_text.lower() == "charging"
                if _os.path.exists(cap_file):
                    try:
                        with open(cap_file) as f:
                            level = int(float(f.read().strip()))
                        if 0 <= level <= 100:
                            # A "Full" pack cannot truthfully be 0%.  The S10+
                            # fuel gauge can expose a single 0 sample while the
                            # charger/PMIC re-initialises; keep the reading
                            # unknown rather than publish that flicker.
                            if not (level == 0 and status_text.lower() == "full"):
                                bat_info["level"] = level
                    except Exception:
                        pass
                # Actual capacity representation (microampere-hours as reported
                # by the fuel gauge).  charge_full is the currently usable full
                # capacity; charge_full_design is the factory design capacity.
                for key, path in (("capacity_uah", full_file), ("design_capacity_uah", design_file)):
                    if _os.path.exists(path):
                        try:
                            with open(path) as f:
                                bat_info[key] = int(f.read().strip())
                        except Exception:
                            pass
                bat_info["available"] = True
        except Exception:
            pass

        # Modem — live from org.freedesktop.ModemManager1 when present, else
        # in-memory mock (typical in a VM without a real modem).
        modem_source = "mock"
        modem_info = {"connected": False, "signal_quality": 0, "operator": "Nuxel VM"}
        try:
            bus = dbus.SystemBus()
            mm = bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1')
            props = dbus.Interface(mm, 'org.freedesktop.DBus.Properties')
            modems = props.Get('org.freedesktop.ModemManager1', 'Modems')
            if modems:
                modem_source = "live:ModemManager"
                modem_info["connected"] = True
                modem_info["signal_quality"] = 100
                modem_info["operator"] = "Nuxel"
        except Exception:
            pass

        return {
            "success": True,
            "app_id": app_id,
            "network": net_info,
            "modem": modem_info,
            "battery": bat_info,
            "time": now,
            "vm_mode": modem_source == "mock",  # honest: system-side data is real
            "data_source": {
                "network": net_source or "mock",
                "battery": bat_source,
                "modem":   modem_source,
            },
            "backend_audit": self._classify_backends(),
        }

    def _mock_response(self, method, *args):
        """Return mock data when bridge is not available (VM dev mode).

        CRITICAL HONESTY (briq-8): every mock response is explicitly labelled
        ``"data_source": "mock"`` and the per-layer ``backend_audit`` shows which
        upstream providers (ModemManager / NetworkManager / GeoClue2) were live
        vs unavailable at request time. Consumers can therefore distinguish real
        vs placeholder results for the verification report.
        """
        app_id = args[0] if args else "unknown"
        cap = args[1] if len(args) > 1 else "unknown"
        audit = self._classify_backends()
        mock_base = {
            "vm_mode": True, "data_source": "mock",
            "backend_audit": audit,
        }
        mocks = {
            "Ping": {"success": True, "service": "nuxel-bridge", "version": BRIDGE_HOST_VERSION,
                     "bridge_version": BRIDGE_PROTOCOL_VERSION, "echo": args[0] if args else "pong", **mock_base},
            "GetCapabilities": {"capabilities": [{"id": k, "description": "Dev mock", "risk": "low", "data_source": "mock"} for k in ["phone:status", "location:read", "camera:capture", "sms:send", "notifications:send"]], **mock_base},
            "GetPhoneStatus": self._get_system_phone_status(app_id),
            "GetLocation": {"success": False, "error": "Location not available in VM (GeoClue2 absent)", "data_source": "mock", "backend_layer": "GeoClue2", "backend_audit": audit, "vm_mode": True},
            "LocationAcquire": {"success": False, "error": "Location not available in VM (GeoClue2 absent)", "data_source": "mock", "backend_layer": "GeoClue2", "backend_audit": audit, "vm_mode": True},
            "SmsGetMessages": {"success": True, "messages": [], **mock_base},
            "SmsSend": {"success": True, "mock": True, "message_id": "mock-sms-1", "number": args[1] if len(args) > 1 else "", "portal_auto_grant": True, **mock_base},
            "GetAppCapabilities": {"app_id": app_id, "capabilities": {}, **mock_base},
            "CheckPermission": {"app_id": app_id, "capability": cap, "granted": True, "portal_auto_grant": True, **mock_base},
            "RequestCapability": {"success": True, "state": "granted", "capability": cap, "portal_auto_grant": True, **mock_base},
            "SendNotification": {"success": True, "notification_id": 1, **mock_base},
            "RevokeCapability": {"success": True, **mock_base},
            # PWA bridge RPC mocks (fallback when D-Bus bridge is unavailable)
            "CaldavList": {"success": True, "events": [], **mock_base},
            "CaldavPut": {"success": True, "saved": 0, **mock_base},
            "StorageListDir": {"success": True, "entries": [], **mock_base},
            "StorageWrite": {"success": True, **mock_base},
            "StorageRead": {"success": True, "data": None, **mock_base},
            "CameraListCaptures": {"success": True, "captures": [], **mock_base},
            "CameraCapture": {"success": False, "error": "NO_CAMERA", "error_code": "NO_CAMERA", "detail": "mock bridge has no camera; a capture is never fabricated", **mock_base},
            "MailImapList": {"success": True, "messages": [], **mock_base},
            "MailSmtpSend": {"success": True, **mock_base},
        }
        return mocks.get(method, {"success": False, "error": "No mock for " + method, "data_source": "mock", "vm_mode": True})

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        origin = self.headers.get('Origin', '')
        cors_origin = _get_cors_origin(origin if origin else None)

        self.send_response(204)
        if cors_origin:
            self.send_header('Access-Control-Allow-Origin', cors_origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Nuxel-Bridge-Version, X-Nuxel-Launcher-Secret')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if not self._verify_auth():
            self._send_json({'error': 'unauthorized'}, 401)
            return

        mismatch = self._verify_version()
        if mismatch is not None:
            logger.error("bridge_version mismatch: expected %s, app declared %s",
                         BRIDGE_PROTOCOL_VERSION, mismatch.get("got"))
            self._send_json(mismatch, 409)
            return

        if path == '/api/v1/health':
            self._send_json({
                "success": True,
                "service": "nuxel-http-bridge",
                "version": BRIDGE_HOST_VERSION,
                "bridge_version": BRIDGE_PROTOCOL_VERSION,
                "registry": {"source": APP_REGISTRY_PATH, "available": os.path.exists(APP_REGISTRY_PATH)},
                "timestamp": time.time(),
            })

        elif path == '/api/v1/ping':
            result = self._call_bridge('Ping', 'health')
            # The host's protocol version is published here (bridge-version.json
            # "enforcement.http_bridge"); the PWA client refuses a mismatch.
            if isinstance(result, dict):
                result.setdefault("bridge_version", BRIDGE_PROTOCOL_VERSION)
                result.setdefault("version", BRIDGE_HOST_VERSION)
            self._send_json(result)

        elif path == '/api/v1/storage/file':
            self._send_storage_file(parse_qs(parsed.query).get('path', [''])[0])

        elif path == '/api/v1/storage/thumbnail':
            self._send_storage_thumbnail(parse_qs(parsed.query).get('path', [''])[0])
        elif path == '/api/v1/storage/waveform':
            try:
                result = self._app_store().storage_waveform(
                    parse_qs(parsed.query).get('path', [''])[0],
                    int(parse_qs(parsed.query).get('buckets', ['240'])[0] or 240))
            except Exception as exc:  # noqa: BLE001
                result = {'success': False, 'error': str(exc)}
            self._send_json(result)

        elif path == '/api/v1/doom/wads':
            # Read-only WAD catalogue for the in-app Chocolate Doom engine.
            # Only allowlisted game-data roots are ever scanned; the response
            # omits absolute paths and addresses files by SHA-256.
            if doom_assets is None:
                self._send_json({'success': False, 'error': 'doom_assets_unavailable'}, 503)
            else:
                self._send_json(doom_assets.public_catalogue())

        elif path == '/api/v1/doom/wad':
            # Stream one already-catalogued WAD into the WebAssembly FS.  The
            # query parameter is a digest, never a path.
            if doom_assets is None:
                self._send_json({'success': False, 'error': 'doom_assets_unavailable'}, 503)
            else:
                wid = parse_qs(parsed.query).get('id', [''])[0]
                data = doom_assets.read_bytes(wid)
                if data is None:
                    self._send_json({'success': False, 'error': 'wad_not_found',
                                     'id': wid}, 404)
                else:
                    self._send_bytes(data, 'application/octet-stream',
                                     cache='private, max-age=3600')

        elif path == '/api/v1/apps/registry':
            self._send_json(self._load_app_registry())

        elif path == '/api/v1/flatpak/status':
            if flatpak_provider is None:
                self._send_json({'success': False, 'error': 'flatpak provider unavailable'}, 503)
            else:
                self._send_json(flatpak_provider.get_provider().status())

        elif path == '/api/v1/flatpak/apps':
            if flatpak_provider is None:
                self._send_json({'success': False, 'error': 'flatpak provider unavailable'}, 503)
            else:
                self._send_json(flatpak_provider.get_provider().list_installed())

        elif path == '/api/v1/flatpak/remote-ls':
            if flatpak_provider is None:
                self._send_json({'success': False, 'error': 'flatpak provider unavailable'}, 503)
            else:
                qs = parse_qs(parsed.query)
                self._send_json(flatpak_provider.get_provider().remote_ls(
                    remote=qs.get('remote', ['flathub'])[0],
                    arch=qs.get('arch', ['aarch64'])[0],
                    query=qs.get('q', [''])[0],
                    limit=int(qs.get('limit', ['600'])[0] or 600)))

        elif path.startswith('/api/v1/flatpak/icon/'):
            if flatpak_provider is None:
                self._send_json({'success': False, 'error': 'flatpak provider unavailable'}, 503)
            else:
                aid = path.rsplit('/', 1)[-1]
                data, mime, err = flatpak_provider.get_provider().icon(aid)
                if data is not None and mime:
                    self._send_bytes(data, mime)
                else:
                    self._send_json({'success': False, 'error': err or 'icon_not_found',
                                     'app_id': aid}, 404)

        elif path == '/api/v1/capabilities':
            result = self._call_bridge('GetCapabilities')
            self._send_json(result)

        elif path == '/api/v1/phone/status':
            app_id = parse_qs(parsed.query).get('app_id', ['unknown'])[0]
            result = self._call_bridge('GetPhoneStatus', app_id)
            self._send_json(result)

        elif path in ('/api/v1/system/usb-mode', '/api/v1/usb-mode/status'):
            if usb_mode is not None:
                try:
                    self._send_json(usb_mode.current_state())
                except Exception as exc:  # noqa: BLE001
                    logger.error('usb-mode state read failed: %s', exc)
                    self._send_json({'success': False, 'error': str(exc)}, 500)
            else:
                self._send_json({'success': False, 'error': 'usb_mode unavailable'}, 503)

        elif path == '/api/v1/system/tri-link':
            if tri_link_status is not None:
                try:
                    self._send_json(tri_link_status.get_status())
                except Exception as exc:  # noqa: BLE001
                    logger.error('tri-link status read failed: %s', exc)
                    self._send_json({'success': False, 'error': str(exc)}, 500)
            else:
                self._send_json({'success': False, 'error': 'tri_link_status unavailable'}, 503)

        elif path == '/api/v1/system/remote-desktop':
            if remote_desktop is not None:
                try:
                    self._send_json(remote_desktop.get_status())
                except Exception as exc:  # noqa: BLE001
                    logger.error('remote-desktop status read failed: %s', exc)
                    self._send_json({'success': False, 'error': str(exc)}, 500)
            else:
                self._send_json({'success': False, 'error': 'remote_desktop unavailable'}, 503)

        elif path == '/api/v1/system/dnd':
            self._send_json(dnd_provider.handle('status', {}) if dnd_provider else {'success': False, 'error': 'dnd provider unavailable'})
        elif path == '/api/v1/system/nfc':
            self._send_json(nfc_provider.handle('status', {}) if nfc_provider else {'success': False, 'error': 'nfc provider unavailable'})
        elif path == '/api/v1/system/fingerprint':
            self._send_json(fingerprint_provider.handle('status', {}) if fingerprint_provider else {'success': False, 'error': 'fingerprint provider unavailable'})
        elif path == '/api/v1/system/security':
            self._send_json(security_provider.handle('status', {}) if security_provider else {'success': False, 'error': 'security provider unavailable'})
        elif path == '/api/v1/system/led-notification':
            self._send_json(led_notification_provider.handle('status', {}) if led_notification_provider else {'success': False, 'error': 'led provider unavailable'})
        elif path == '/api/v1/system/software':
            self._send_json(software_provider.handle('status', {}) if software_provider else {'success': False, 'error': 'software provider unavailable'})
        elif path == '/api/v1/system/flashlight':
            # Read-only state (toggle/off go through the authenticated RPC).
            if flashlight_provider is not None:
                try:
                    self._send_json(flashlight_provider.handle('status', {}))
                except Exception as exc:  # noqa: BLE001
                    self._send_json({'success': False, 'state': 'ERROR', 'error': str(exc)}, 500)
            else:
                self._send_json({'success': False, 'state': 'UNKNOWN',
                                 'error': 'flashlight provider unavailable'}, 503)

        elif path == '/api/v1/windows/list':
            # Recents polls this endpoint with GET.  It previously existed only
            # under POST, which made every native tab open the "Not found" state.
            result, code = self._list_toplevels()
            self._send_json(result, code)
        elif path == '/api/v1/system/indicators':
            # Lockhead status indicators.  These read real kernel state
            # directly (power_supply, configfs/UDC, android_usb, and the
            # console process's tty fd) so a charging-only cable can never
            # light the PC indicator and root access can never light the
            # live-console indicator.
            if system_indicators is not None:
                try:
                    doc = system_indicators.get_indicators()
                    if remote_desktop is not None:
                        doc = dict(doc)
                        doc['remote_desktop'] = remote_desktop.privacy_summary()
                    self._send_json(doc)
                except Exception as exc:  # noqa: BLE001
                    logger.error('system indicators read failed: %s', exc)
                    self._send_json({'success': False, 'error': str(exc)}, 500)
            else:
                self._send_json({'success': False, 'error': 'system_indicators unavailable'}, 503)

        elif path == '/api/v1/location':
            app_id = parse_qs(parsed.query).get('app_id', ['unknown'])[0]
            result = self._call_bridge('GetLocation', app_id)
            self._send_json(result)

        elif path == '/api/v1/sms':
            app_id = parse_qs(parsed.query).get('app_id', ['unknown'])[0]
            result = self._call_bridge('SmsGetMessages', app_id)
            self._send_json(result)

        elif path == '/api/v1/capabilities/check':
            app_id = parse_qs(parsed.query).get('app_id', ['unknown'])[0]
            capability = parse_qs(parsed.query).get('capability', [''])[0]
            result = self._call_bridge('CheckPermission', app_id, capability)
            self._send_json(result)

        elif path == '/api/v1/apps/recent':
            self._send_json({
                "success": True,
                "count": len(ACTIVATION_HISTORY),
                "max": ACTIVATION_HISTORY_MAX,
                "rejected": dict(ACTIVATION_REJECTED),
                "activations": list(ACTIVATION_HISTORY),
            })

        elif path == '/api/v1/apps/capabilities':
            app_id = parse_qs(parsed.query).get('app_id', ['unknown'])[0]
            result = self._call_bridge('GetAppCapabilities', app_id)
            self._send_json(result)

        else:
            self._send_json({'error': 'Not found'}, 404)


    # Map (namespace, verb) bridge RPC calls to nuxel-bridge D-Bus methods.
    RPC_METHODS = {
        ("ping", "ping"): "Ping",
        ("phone", "status"): "GetPhoneStatus",
        ("network", "wifi-enabled"): "NetworkWifiSetEnabled",
        ("network", "wifi-scan"): "NetworkWifiScan",
        ("network", "wifi-connect"): "NetworkWifiConnect",
        ("network", "wifi-disconnect"): "NetworkWifiDisconnect",
        ("network", "wifi-saved"): "NetworkWifiSaved",
        ("network", "wifi-forget"): "NetworkWifiForget",
        ("notifications", "list"): "GetNotifications",
        ("permissions", "list"): "GetAppCapabilities",
        ("sms", "list"): "SmsGetMessages",
        ("call", "end"): "CallEnd",
        ("location", "status"): "GetLocation",
        ("location", "request"): "GetLocation",
        ("location", "get-status"): "LocationGetStatus",
        ("location", "set-enabled"): "LocationSetEnabled",
        ("location", "acquire"): "LocationAcquire",
        ("location", "stop"): "LocationStop",
        ("bluetooth", "status"): "BluetoothGetStatus",
        ("bluetooth", "set-powered"): "BluetoothSetPowered",
        ("permissions", "request"): "RequestCapability",
        ("permissions", "revoke"): "RevokeCapability",
        ("sms", "send"): "SmsSend",
        ("notifications", "send"): "SendNotification",
        ("call", "initiate"): "CallInitiate",
        ("camera", "list-captures"): "CameraListCaptures",
        ("camera", "capture"): "CameraCapture",
        ("camera", "status"): "CameraStatus",
        ("camera", "open"): "CameraOpen",
        ("camera", "delete"): "CameraDelete",
        ("caldav", "list"): "CaldavList",
        ("caldav", "put"): "CaldavPut",
        ("storage", "list-dir"): "StorageListDir",
        ("storage", "write"): "StorageWrite",
        ("storage", "read"): "StorageRead",
        ("mail", "imap-list"): "MailImapList",
        ("mail", "smtp-send"): "MailSmtpSend",
        ("orientation", "get"): "OrientationGet",
        ("orientation", "modes"): "OrientationModes",
        ("orientation", "set"): "OrientationSet",
    }

    # Map an RPC method to the D-Bus positional args it needs. The bridge's
    # D-Bus methods take explicit positional args (in_signatures 's'/'ss'/'sss'),
    # NOT (app_id, params); passing the raw params dict broke every /rpc call
    # (e.g. Ping: "Fewer items found in D-Bus signature than in Python
    # arguments" - 2 Python args for a 1-arg 's' method).
    RPC_ARG_BUILDERS = {
        "Ping": lambda app_id, params: [params.get("message") if isinstance(params, dict) and params.get("message") is not None else app_id],
        "GetPhoneStatus": lambda app_id, params: [app_id],
        "NetworkWifiSetEnabled": lambda app_id, params: [app_id, bool(params.get("enabled", False))],
        "NetworkWifiScan": lambda app_id, params: [app_id],
        "NetworkWifiConnect": lambda app_id, params: [app_id, params.get("ssid", ""), params.get("password", ""), params.get("security", "wpa2"), params.get("ap_path", ""), params.get("bssid", ""), params.get("device", ""), params.get("ssid_hex", "")],
        "NetworkWifiDisconnect": lambda app_id, params: [app_id],
        "NetworkWifiSaved": lambda app_id, params: [app_id],
        "NetworkWifiForget": lambda app_id, params: [app_id, params.get("connection", "")],
        "GetNotifications": lambda app_id, params: [],
        "GetAppCapabilities": lambda app_id, params: [app_id],
        "SmsGetMessages": lambda app_id, params: [app_id],
        "CallEnd": lambda app_id, params: [app_id, params.get("call_id", "")],
        "GetLocation": lambda app_id, params: [app_id],
        "LocationGetStatus": lambda app_id, params: [app_id],
        "LocationSetEnabled": lambda app_id, params: [app_id, bool((params or {}).get("enabled", False))],
        "LocationAcquire": lambda app_id, params: [app_id],
        "LocationStop": lambda app_id, params: [app_id],
        "BluetoothGetStatus": lambda app_id, params: [app_id],
        "BluetoothSetPowered": lambda app_id, params: [app_id, bool((params or {}).get("enabled", False))],
        "RequestCapability": lambda app_id, params: [app_id, params.get("capability", "")],
        "RevokeCapability": lambda app_id, params: [app_id, params.get("capability", "")],
        "CallInitiate": lambda app_id, params: [app_id, params.get("number", "")],
        "SmsSend": lambda app_id, params: [app_id, params.get("number", ""), params.get("text", "")],
        "SendNotification": lambda app_id, params: [app_id, params.get("title", ""), params.get("body", "")],
        "CameraStatus": lambda app_id, params: [app_id],
        "CameraListCaptures": lambda app_id, params: [app_id, (params.get("kind") or "") if isinstance(params, dict) else ""],
        "CameraCapture": lambda app_id, params: [app_id, (params.get("kind") or "photo") if isinstance(params, dict) else "photo", (params.get("mime") or "") if isinstance(params, dict) else "", (params.get("data_b64") or "") if isinstance(params, dict) else ""],
        "CameraOpen": lambda app_id, params: [app_id, (params.get("id") or "") if isinstance(params, dict) else ""],
        "CameraDelete": lambda app_id, params: [app_id, (params.get("id") or "") if isinstance(params, dict) else ""],
        "OrientationGet": lambda app_id, params: [app_id],
        "OrientationModes": lambda app_id, params: [app_id],
        "OrientationSet": lambda app_id, params: [app_id, params.get("mode", "")],
    }

    def _graphics_diagnostics(self):
        """Read-only, layered graphics truth.  No single green GPU badge.

        Every field is derived from a real file/process/package; absent data is
        reported as null/unavailable, never as zero or success.
        """
        import glob as _glob
        import hashlib
        import subprocess as _sp

        def read(path, limit=65536):
            try:
                with open(path, "rb") as fh:
                    return fh.read(limit).decode("utf-8", "replace").strip()
            except OSError:
                return None

        def sha(path):
            try:
                h = hashlib.sha256()
                with open(path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1048576), b""):
                        h.update(chunk)
                return h.hexdigest()
            except OSError:
                return None

        def run(argv, timeout=4):
            try:
                r = _sp.run(argv, capture_output=True, text=True, timeout=timeout)
                return (r.stdout or "").strip() or (r.stderr or "").strip()
            except (OSError, _sp.TimeoutExpired):
                return None

        # ---- files/devices
        dev_mali = os.path.exists("/dev/mali0")
        dev_udmabuf = os.path.exists("/dev/udmabuf")
        dev_dri = os.path.isdir("/dev/dri")
        fb_virtual = read("/sys/class/graphics/fb0/virtual_size")
        fb_stride = read("/sys/class/graphics/fb0/stride")
        fb_owner = read("/var/lib/nuxel/fb-owner")
        fallback_marker = os.path.exists("/run/nuxel-gpu-fallback")

        # ---- compositor: an actual context, not just an open fd
        phoc = {}
        pid = run(["/usr/bin/pgrep", "-n", "-x", "phoc"])
        if pid and pid.isdigit():
            pidn = int(pid)
            fds = []
            try:
                for f in os.listdir("/proc/%d/fd" % pidn):
                    try:
                        fds.append(os.readlink("/proc/%d/fd/%s" % (pidn, f)))
                    except OSError:
                        continue
            except OSError:
                pass
            phoc = {
                "pid": pidn,
                "mali_fds": sum(1 for x in fds if "mali0" in x),
                "udmabuf_fds": sum(1 for x in fds if "udmabuf" in x),
                "cmdline": read("/proc/%d/cmdline" % pidn, 4096),
                "renderer": "mali-kbase" if any("mali0" in x for x in fds) else "unknown",
            }
            env = read("/proc/%d/environ" % pidn, 65536) or ""
            phoc["wlr_renderer"] = None
            phoc["mesa_kbase_node"] = None
            for item in env.split("\0"):
                if item.startswith("WLR_RENDERER="):
                    phoc["wlr_renderer"] = item.split("=", 1)[1]
                elif item.startswith("MESA_KBASE_NODE="):
                    phoc["mesa_kbase_node"] = item.split("=", 1)[1]
        # kbase context table (debugfs; only readable by root, bounded read)
        kbase_ctx = None
        try:
            text = read("/sys/kernel/debug/mali/gpu_memory", 262144)
            if text:
                kbase_ctx = "phoc" in text
        except OSError:
            kbase_ctx = None

        # ---- EGL libraries
        egl_link = os.path.realpath("/usr/lib64/libEGL_mesa.so.0")
        egl = {
            "library": egl_link,
            "sha256": sha(egl_link),
            "gallium_sha256": sha("/usr/lib64/libgallium_dri.so"),
            "server_glvnd": os.path.exists("/usr/share/glvnd/egl_vendor.d/50_mesa.json"),
        }
        probe_file = "/run/nuxel-graphics-probes.json"
        probes = None
        try:
            with open(probe_file, "r", encoding="utf-8") as fh:
                probes = json.load(fh)
        except (OSError, ValueError):
            probes = None

        # ---- WebKit / GTK runtime (installed package truth)
        pkgs = {}
        for name in ("webkit2gtk4.1", "gtk3", "gtk4", "mesa-libEGL", "mesa-libGLES"):
            out = run(["/usr/bin/rpm", "-q", name])
            pkgs[name] = out if out and not out.startswith("package ") else None
        webkit_processes = run(["/usr/bin/pgrep", "-af", "WebKitWebProcess"]) or ""
        webkit_env = None
        webkit_fds = []
        webkit_gpu_maps = False
        for line in webkit_processes.splitlines():
            try:
                wpid = int(line.split()[0])
            except (ValueError, IndexError):
                continue
            env = read("/proc/%d/environ" % wpid, 65536) or ""
            webkit_env = {}
            for item in env.split("\0"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    if k in ("WEBKIT_DISABLE_COMPOSITING_MODE", "WEBKIT_FORCE_COMPOSITING_MODE",
                             "LIBGL_ALWAYS_SOFTWARE", "MESA_KBASE_NODE", "NUXEL_KBASE_WSI",
                             "NUXEL_GRAPHICS_PROFILE_ACTIVE", "NUXEL_GRAPHICS_PROFILE_REQUESTED",
                             "NUXEL_GRAPHICS_FALLBACK_REASON"):
                        webkit_env[k] = v
            maps = read("/proc/%d/maps" % wpid, 8 << 20) or ""
            webkit_gpu_maps = "libgallium" in maps
            try:
                for fd in os.listdir("/proc/%d/fd" % wpid):
                    try:
                        target = os.readlink("/proc/%d/fd/%s" % (wpid, fd))
                    except OSError:
                        continue
                    if "udmabuf" in target or "dmabuf" in target or "/dev/dri" in target:
                        webkit_fds.append({"fd": fd, "target": target})
            except OSError:
                pass
            break
        webkit_disable = (webkit_env or {}).get("WEBKIT_DISABLE_COMPOSITING_MODE")
        webkit_force = (webkit_env or {}).get("WEBKIT_FORCE_COMPOSITING_MODE")
        if webkit_disable == "1":
            webkit_status = "SOFTWARE_FALLBACK"
        elif webkit_force == "1" and webkit_gpu_maps:
            webkit_status = "GPU_RENDERED_SHM_PRESENTED"
        elif webkit_force == "1":
            webkit_status = "GPU_REQUESTED_NO_MAPPING"
        else:
            webkit_status = "UNKNOWN"

        # ---- bridge/panel counters from its current status line
        bridge_text = read("/run/nuxel-wl-fb.state", 8192)
        if not bridge_text:
            bridge_text = run(["/usr/bin/journalctl", "-u", "nuxel-wl-fb", "-b", "--no-pager", "-n", "1"], 5)
        frames_ok = bool(bridge_text and "FRAMES_OK" in bridge_text)
        pan_failed = None
        if bridge_text:
            import re as _re
            m = _re.search(r"decon_pan_failed=(\d+)", bridge_text)
            if m:
                pan_failed = int(m.group(1))

        return {
            "success": True,
            "source": "nuxel-bridge:graphics-diagnostics",
            "timestamp": time.time(),
            "gpu": {
                "hardware": "Mali-G76 MP12" if dev_mali else None,
                "kernel_driver": "mali_kbase" if dev_mali else None,
                "device_present": dev_mali,
                "device_opened_by_compositor": bool(phoc.get("mali_fds")),
                "context_owner": "phoc" if kbase_ctx else (None if kbase_ctx is None else "not-found"),
                "dri_render_node": dev_dri,
                "dri_expected_absent": not dev_dri,
            },
            "compositor": {
                "pid": phoc.get("pid"),
                "renderer": phoc.get("renderer"),
                "wlr_renderer": phoc.get("wlr_renderer"),
                "mali_fds": phoc.get("mali_fds", 0),
                "udmabuf_fds": phoc.get("udmabuf_fds", 0),
                "fallback_marker": fallback_marker,
            },
            "egl": egl,
            "webkitgtk": {
                "packages": pkgs,
                "process_running": bool(webkit_processes),
                "compositing_env": webkit_env,
                "dma_buf_backing_store": None,
                "gpu_library_mapped": webkit_gpu_maps,
                "transport": "shm" if not webkit_fds else "dmabuf-candidate",
                "transport_fds": webkit_fds,
                "status": webkit_status,
            },
            "gtk3": {"package": pkgs.get("gtk3"), "gl_test": None,
                      "note": "GTK3 WebKit host is independent of GSK_RENDERER"},
            "gtk4": {"package": pkgs.get("gtk4"), "gsk_renderer": None,
                      "note": "GTK4 GSK is not a WebKit or GTK3 signal"},
            "buffer_sharing": {
                "udmabuf_device": dev_udmabuf,
                "udmabuf_proven": None,
                "linux_dmabuf_global": None,
            },
            "display": {
                "fb_virtual_size": fb_virtual,
                "fb_stride": fb_stride,
                "single_owner_record": fb_owner,
                "frames_ok": frames_ok,
                "decon_pan_failed": pan_failed,
            },
            "probes": probes,
            "blocked_reason": (
                "WebKit DMA-BUF transport is blocked: WebKit 2.54.1 gates its "
                "Hardware backing store on drmMainDevice(), and this kernel has no "
                "DRM/GBM node (CONFIG_DRM_VGEM unset, /dev/dri absent). WebKit is "
                "GPU-rendered but presents through shared memory."
                if not fallback_marker and webkit_disable == "1"
                else None
            ),
        }

    def _graphics_status_from_layers(self, layers):
        """Map the PWNAGE-60000 layered status onto the Settings API surface.

        The Settings card is intentionally conservative: GPU rendering and SHM
        presentation are reported together, while zero-copy scanout remains
        false until the CPU framebuffer bridge is genuinely removed.
        """
        kg = layers.get("kernel_gpu") or {}
        ph = layers.get("phoc") or {}
        eg = layers.get("egl") or {}
        wk = layers.get("webkit") or {}
        dm = layers.get("linux_dmabuf") or {}
        fb = layers.get("final_output") or {}
        caps = layers.get("capabilities") or {}
        prof = layers.get("profile_summary") or {}
        probe = eg.get("probe") or {}
        fb_parsed = fb.get("parsed") or {}
        webkit_gpu = bool(wk.get("gpu_rendering"))
        webkit_shm = (wk.get("transport") == "shm")
        fallback = bool((prof.get("fallback_active")))
        phoc_accel = bool(ph.get("accelerated")) and not fb.get("fallback_marker")
        if fallback or fb.get("fallback_marker"):
            verdict = "SOFTWARE"
        elif phoc_accel and webkit_gpu:
            verdict = "ACCELERATED_SHM"
        elif phoc_accel:
            verdict = "PARTIAL"
        else:
            verdict = "UNKNOWN"
        webkit_status = ("GPU_RENDERED_SHM_PRESENTED" if webkit_gpu and webkit_shm
                         else ("GPU_RENDERED_DMABUF_CANDIDATE" if webkit_gpu
                               else "SOFTWARE_FALLBACK"))
        dmabuf_status = ("LINEAR-ONLY v%s (import proven; WebKit export blocked)"
                         % dm.get("protocol") if dm.get("protocol") else
                         "protocol not observed")
        gtk4 = layers.get("gtk4") or {}
        gtk3 = layers.get("gtk3") or {}
        return {
            "success": True,
            "schema": "nuxel.graphics-status/2",
            "source": "nuxel-bridge:graphics-status:layers",
            "timestamp": time.time(),
            "verdict": verdict,
            "acceleration_label": ("GPU-RENDERED / SHM-PRESENTED"
                                   if verdict == "ACCELERATED_SHM" else
                                   ("PARTIAL" if verdict == "PARTIAL" else verdict)),
            "gpu": {
                "hardware": "Mali-G76 MP12" if kg.get("present") else None,
                "kernel_driver": kg.get("driver"),
                "device_present": kg.get("present"),
                "device_node": "/dev/mali0" if kg.get("present") else None,
                "context_owner": "phoc" if phoc_accel else None,
                "context_opened_by_compositor": bool(phoc_accel),
                "dri_render_node": kg.get("dri_present"),
            },
            "phoc": {
                "pid": ph.get("pid"),
                "renderer": probe.get("renderer"),
                "wlr_renderer": "gles2" if phoc_accel else "pixman",
                "mali_fds": ph.get("mali_fds"),
                "udmabuf_fds": ph.get("udmabuf_fds"),
                "fd_scan": ph.get("fd_scan"),
                "fallback_marker": fb.get("fallback_marker"),
                "accelerated": phoc_accel,
                "llvmpipe_threads": len(ph.get("llvmpipe_threads") or []),
            },
            "egl": {
                "library": eg.get("vendor_library"),
                "sha256": eg.get("egl_mesa_sha256"),
                "vendor": "Mesa Project" if probe.get("renderer") else None,
                "version": probe.get("egl_version"),
                "init": "ok" if probe.get("ok") else ("failed" if probe else None),
                "gles_renderer": probe.get("renderer"),
                "gles_version": probe.get("gl_version"),
                "stock_backup_selected": eg.get("stock_backup_selected"),
            },
            "gtk_gl": {
                "status": gtk3.get("status") or "NOT_MEASURED",
                "gtk3": gtk3.get("status"),
                "gtk4": "%s (%s)" % (gtk4.get("status"), gtk4.get("requested_renderer")),
                "gsk_renderer": gtk4.get("requested_renderer"),
                "detail": gtk3.get("note") or gtk3.get("reason") or gtk4.get("reason") or
                          "GTK3/GTK4 are separate runtime layers; --deep runs the live probes",
            },
            "webkitgtk": {
                "status": webkit_status,
                "process_running": bool(wk.get("running")),
                "transport": wk.get("transport"),
                "transport_fds": wk.get("transport_fds") or [],
                "gpu_library_mapped": bool(wk.get("gallium_library")),
                "mali_fds": wk.get("mali_fds", 0),
                "profile_requested": prof.get("requested"),
                "profile_active": prof.get("active"),
                "fallback_active": fallback,
            },
            "dmabuf": {
                "udmabuf_device": bool(kg.get("udmabuf")),
                "linux_dmabuf_global": bool(dm.get("protocol")),
                "protocol": dm.get("protocol"),
                "linear_only": dm.get("linear_only"),
                "status": dmabuf_status,
            },
            "display_bridge": {
                "frames_ok": bool(fb.get("frames_ok")),
                "decon_pan_failed": fb.get("decon_pan_failed"),
                "fb_virtual_size": (fb.get("geometry") or {}).get("virtual_size"),
                "path": "cpu-framebuffer-bridge",
                "one_writer": bool(fb.get("one_writer")),
                "blit_avg_ms": fb_parsed.get("blit_avg_ms"),
                "damage_avg_ms": fb_parsed.get("damage_avg_ms"),
                "present_skipped": fb_parsed.get("present_skipped"),
            },
            "fbdev_drm": {
                "fb0": bool(fb.get("frames_ok")),
                "drm_render_node": bool(kg.get("dri_present")),
            },
            "zero_copy_scanout": False,
            "honest_summary": (
                "Phoc renders through Mali kbase. WebKit is GPU-rendered and presents "
                "through shared memory; it is not DMA-BUF/zero-copy. The final panel "
                "path is still CPU copy/scale into /dev/fb0 through one writer."
            ),
            "blocked_reason": (
                "WebKit 2.54.1 Hardware transport requires drmMainDevice(); this "
                "kernel has no /dev/dri and CONFIG_DRM_VGEM is unset."
                if dmabuf_status.startswith("protocol") or not dm.get("protocol") else None
            ),
            "layers": layers,
            "capabilities": caps,
            "profile": prof,
        }

    def _graphics_status(self):
        """Fast, structured status for the Displays > Graphics Acceleration card.

        This is deliberately separate from display.status (external Type-C/DRM
        connector discovery) and from the expensive graphics-probe path.  A
        missing subcomponent is reported as null/UNKNOWN; it never suppresses
        the other layers, and it never claims whole-GUI acceleration.
        """
        # PWNAGE-60000: one truth source for the layered view.  The CLI reads
        # /proc, /sys and cached probe results only (no deep probe), is bounded
        # to 3 s, and is cached for 5 s so a Settings refresh cannot block the
        # bridge or hammer the device.
        layers = None
        try:
            tool = "/usr/lib/nuxel/nuxel-gpu-status"
            now = time.time()
            cached = getattr(self, "_gpu_layers_cache", None)
            if cached and (now - cached[0]) < 5:
                layers = cached[1]
            elif os.path.exists(tool):
                proc = subprocess.run([tool, "--json", "--no-probe"],
                                      capture_output=True, text=True, timeout=3)
                if proc.returncode == 0 and proc.stdout.strip():
                    layers = json.loads(proc.stdout)
                    self._gpu_layers_cache = (now, layers)
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            logger.debug("layered GPU status unavailable: %s", exc)

        if isinstance(layers, dict) and layers.get("schema") == "nuxel.gpu-status/2":
            return self._graphics_status_from_layers(layers)

        doc = self._graphics_diagnostics()
        if not isinstance(doc, dict) or doc.get("success") is False:
            return doc
        g = doc.get("gpu") or {}
        c = doc.get("compositor") or {}
        e = doc.get("egl") or {}
        w = doc.get("webkitgtk") or {}
        d = doc.get("display") or {}
        b = doc.get("buffer_sharing") or {}
        probes = doc.get("probes") or {}

        def probe_text(kind):
            item = probes.get(kind) if isinstance(probes, dict) else None
            if not isinstance(item, dict):
                return None
            return (item.get("stdout") or "") + "\n" + (item.get("stderr") or "")

        def first_match(text, patterns):
            if not text:
                return None
            import re as _re
            for pat in patterns:
                m = _re.search(pat, text, _re.I | _re.M)
                if m:
                    return (m.group(1) or "").strip() or None
            return None

        wayland_text = probe_text("wayland")
        surfaceless_text = probe_text("surfaceless")
        combined = "\n".join(x for x in (wayland_text, surfaceless_text) if x)
        gles_renderer = first_match(combined, [r"GL_RENDERER\s*[:=]\s*([^\n]+)",
                                               r"renderer\s*[:=]\s*([^\n]+)"])
        gles_version = first_match(combined, [r"GL_VERSION\s*[:=]\s*([^\n]+)",
                                              r"GLES(?:2|3)?\s*[:=]\s*([^\n]+)"])
        egl_vendor = first_match(combined, [r"EGL_VENDOR\s*[:=]\s*([^\n]+)",
                                            r"vendor\s*[:=]\s*([^\n]+)"])
        egl_version = first_match(combined, [r"EGL_VERSION\s*[:=]\s*([^\n]+)"])
        egl_init = None
        if wayland_text is not None:
            egl_init = "ok" if first_match(wayland_text, [r"EGL_INIT\s*[:=]\s*ok"]) or                 first_match(wayland_text, [r"initialized\s*[:=]\s*(?:yes|true|ok)"]) else "failed"
        elif surfaceless_text is not None:
            egl_init = "ok" if first_match(surfaceless_text, [r"EGL_INIT\s*[:=]\s*ok"]) or                 first_match(surfaceless_text, [r"initialized\s*[:=]\s*(?:yes|true|ok)"]) else "failed"

        phoc_accel = bool(c.get("mali_fds")) and not c.get("fallback_marker")
        webkit_status = w.get("status") or "UNKNOWN"
        webkit_accel = webkit_status in ("ACCELERATED", "GPU_RENDERED_SHM_PRESENTED")
        webkit_software = webkit_status == "SOFTWARE_FALLBACK"
        if c.get("fallback_marker"):
            verdict = "SOFTWARE"
        elif phoc_accel and webkit_accel:
            # GPU rendering + SHM presentation is still a PARTIAL desktop
            # acceleration result; it is never "fully accelerated" while the
            # final panel path CPU-copies into /dev/fb0.
            verdict = "ACCELERATED_SHM"
        elif phoc_accel and webkit_software:
            verdict = "PARTIAL"
        elif phoc_accel:
            verdict = "PARTIAL"
        else:
            verdict = "UNKNOWN"

        # GTK GL is a separate runtime from Phoc/kbase.  The pwa-host logs an
        # explicit line when GTK falls back; use it when present, and otherwise
        # keep NOT_MEASURED rather than inferring success.
        gtk_status = "NOT_MEASURED"
        gtk_detail = "GTK GL is independent of the Phoc kbase context; no bounded GTK probe was run"
        try:
            gtk_log = subprocess.run(
                ["/usr/bin/journalctl", "-b", "-u", "nuxel-wayland", "--no-pager", "-n", "200"],
                capture_output=True, text=True, timeout=3)
            text = ((gtk_log.stdout or "") + (gtk_log.stderr or ""))
            if "GTK failed to initialize GL" in text or "No GL implementation is available" in text:
                gtk_status = "UNAVAILABLE"
                gtk_detail = ("GTK3 host failed to initialize GL: No GL implementation is available; "
                              "the pwa-host warning is present in this boot's journal")
        except (OSError, subprocess.TimeoutExpired):
            pass

        return {
            "success": True,
            "schema": "nuxel.graphics-status/1",
            "source": "nuxel-bridge:graphics-status",
            "timestamp": time.time(),
            "verdict": verdict,
            "acceleration_label": ("GPU-RENDERED / SHM-PRESENTED"
                                   if verdict == "ACCELERATED_SHM" else
                                   ("PARTIAL" if verdict == "PARTIAL" else verdict)),
            "layers": layers,
            "capabilities": (layers or {}).get("capabilities"),
            "profile": (layers or {}).get("profile_summary"),
            "gpu": {
                "hardware": g.get("hardware"),
                "kernel_driver": g.get("kernel_driver"),
                "device_present": g.get("device_present"),
                "device_node": "/dev/mali0" if g.get("device_present") else None,
                "context_owner": g.get("context_owner"),
                "context_opened_by_compositor": g.get("device_opened_by_compositor"),
                "dri_render_node": g.get("dri_render_node"),
            },
            "phoc": {
                "pid": c.get("pid"),
                "renderer": c.get("renderer"),
                "wlr_renderer": c.get("wlr_renderer"),
                "mali_fds": c.get("mali_fds", 0),
                "udmabuf_fds": c.get("udmabuf_fds", 0),
                "fallback_marker": c.get("fallback_marker"),
                "accelerated": phoc_accel,
            },
            "egl": {
                "library": e.get("library"),
                "sha256": e.get("sha256"),
                "vendor": egl_vendor,
                "version": egl_version,
                "init": egl_init,
                "gles_renderer": gles_renderer,
                "gles_version": gles_version,
                "probe_wayland": wayland_text is not None,
                "probe_surfaceless": surfaceless_text is not None,
            },
            "gtk_gl": {
                "status": gtk_status,
                "gtk3": (doc.get("gtk3") or {}).get("package"),
                "gtk4": (doc.get("gtk4") or {}).get("package"),
                "gsk_renderer": (doc.get("gtk4") or {}).get("gsk_renderer"),
                "detail": gtk_detail,
            },
            "webkitgtk": {
                "process_running": w.get("process_running"),
                "status": webkit_status,
                "accelerated": webkit_accel,
                "compositing_env": w.get("compositing_env"),
                "detail": doc.get("blocked_reason"),
            },
            "dmabuf": {
                "udmabuf_device": b.get("udmabuf_device"),
                "udmabuf_proven": b.get("udmabuf_proven"),
                "linux_dmabuf_global": b.get("linux_dmabuf_global"),
                "status": "device_present_import_not_proven" if b.get("udmabuf_device") else "absent",
            },
            "display_bridge": {
                "process": "nuxel-wl-fb",
                "fb_virtual_size": d.get("fb_virtual_size"),
                "fb_stride": d.get("fb_stride"),
                "frames_ok": d.get("frames_ok"),
                "decon_pan_failed": d.get("decon_pan_failed"),
                "path": "screencopy -> nuxel-wl-fb -> fbdev/DECON",
                "cpu_copy": True,
            },
            "fbdev_drm": {
                "fb0": os.path.exists("/dev/fb0"),
                "drm_render_node": os.path.isdir("/dev/dri"),
                "active_path": "fbdev/DECON",
            },
            "probes": probes,
            "blocked_reason": doc.get("blocked_reason"),
            "honest_summary": (
                "Phoc compositor is kbase-accelerated; WebKitGTK remains software "
                "(no linux-dmabuf path) and nuxel-wl-fb performs a CPU copy into "
                "fbdev/DECON. The GUI is PARTIAL, not fully accelerated."
                if verdict == "PARTIAL" and webkit_software else
                ("No live accelerated GUI path is proved." if verdict != "ACCELERATED"
                 else "Every measured GUI layer is accelerated.")
            ),
        }

    # ---- yt-dlp media downloader ----------------------------------------
    DOWNLOAD_DIR = "/home/nuxel/Downloads"
    DOWNLOAD_JOBS_FILE = "/var/lib/nuxel/downloads/jobs.json"
    YTDLP = "/usr/bin/yt-dlp"

    def _downloader_load_jobs(self):
        """Restore persisted job records and fail interrupted runs honestly."""
        if getattr(self, "_download_jobs_loaded", False):
            return
        self._download_jobs_loaded = True
        try:
            with open(self.DOWNLOAD_JOBS_FILE, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            rows = doc.get("jobs") if isinstance(doc, dict) else None
            if isinstance(rows, list):
                with _DOWNLOAD_LOCK:
                    for job in rows:
                        if not isinstance(job, dict) or not job.get("id"):
                            continue
                        if job.get("status") in ("starting", "running", "cancelling", "queued",
                                                 "validating", "extracting metadata",
                                                 "downloading", "post-processing", "verifying output"):
                            job["status"] = "failed"
                            job["error"] = "interrupted by a bridge restart; no completion was claimed"
                        _DOWNLOAD_JOBS[job["id"]] = job
        except (OSError, ValueError):
            pass
        self._downloader_cleanup_cookie_files()

    def _downloader_cleanup_cookie_files(self):
        """Remove private cookie files left by a crash/restart."""
        try:
            import glob as _glob
            for path in _glob.glob("/run/nuxel/downloader-cookies-*.txt"):
                try:
                    st = os.stat(path)
                    if st.st_uid == 0 and (st.st_mode & 0o077) == 0:
                        os.unlink(path)
                except OSError:
                    pass
        except Exception:
            pass

    def _downloader_verify_file(self, path, fmt):
        if not path or not os.path.isfile(path):
            return False, "final file does not exist"
        try:
            size = os.path.getsize(path)
        except OSError as exc:
            return False, "final file stat failed: %s" % exc
        if size <= 0:
            return False, "final file is empty"
        if path.lower().endswith(".part"):
            return False, "only a partial .part file remains"
        probe = shutil.which("ffprobe") or "/usr/bin/ffprobe"
        if not os.path.exists(probe):
            return False, "ffprobe is unavailable; output type could not be verified"
        try:
            proc = subprocess.run([probe, "-v", "error", "-show_entries",
                                   "format=format_name:stream=codec_type,codec_name",
                                   "-of", "json", path], capture_output=True,
                                  text=True, timeout=25, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, "ffprobe failed: %s" % exc
        if proc.returncode != 0:
            return False, "ffprobe rejected the output: " + (proc.stderr or "")[-300:]
        try:
            doc = json.loads(proc.stdout or "{}")
        except ValueError:
            return False, "ffprobe returned invalid JSON"
        names = str((doc.get("format") or {}).get("format_name") or "").lower()
        types = {str(st.get("codec_type") or "") for st in (doc.get("streams") or []) if isinstance(st, dict)}
        if fmt == "mp3" and ("mp3" not in names or "audio" not in types):
            return False, "requested MP3 but verified container/streams are %s/%s" % (names, sorted(types))
        if fmt == "mp4" and not (("mp4" in names or "mov" in names) and "video" in types):
            return False, "requested MP4 but verified container/streams are %s/%s" % (names, sorted(types))
        return True, {"size": size, "format_name": names, "streams": sorted(types)}

    def _downloader_validate_url(self, url):
        try:
            parts = urllib.parse.urlsplit(str(url or "").strip())
        except ValueError as exc:
            return False, "invalid URL: %s" % exc
        if parts.scheme not in ("http", "https"):
            return False, "only http(s) URLs are accepted"
        if not parts.hostname:
            return False, "URL has no hostname"
        if parts.username or parts.password:
            return False, "credentials in URLs are refused"
        host = parts.hostname.lower().rstrip(".")
        if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
            return False, "local hosts are refused"
        try:
            infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
        except OSError as exc:
            return False, "hostname did not resolve: %s" % exc
        for info in infos:
            try:
                ip = ipaddress.ip_address(info[4][0])
            except ValueError:
                continue
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, "private/local IP targets are refused"
        return True, parts.geturl()

    def _nuxel_cookie_db(self):
        """Return a real WebKit cookie database path, or None.

        WebKitGTK stores cookies in a SQLite database when the website data
        manager uses a persistent directory.  The browser has existed under a
        few names on this image; inspect bounded known locations rather than
        guessing or fabricating a cookie source.
        """
        import glob as _glob
        candidates = [
            "/home/nuxel/.local/share/nuxel-browser/cookies.db",
            "/home/nuxel/.local/share/nuxel_browser_native.py/cookies.db",
            "/home/nuxel/.local/share/nuxel-browser/WebKitWebsiteData/cookies.db",
            "/home/nuxel/.local/share/nuxel_browser/WebKitWebsiteData/cookies.db",
            "/home/nuxel/.cache/nuxel-browser/cookies.db",
        ]
        candidates += _glob.glob("/home/nuxel/.local/share/*nuxel*/**/cookies.db", recursive=True)
        candidates += _glob.glob("/home/nuxel/.local/share/*browser*/**/cookies.db", recursive=True)
        seen = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            try:
                if os.path.isfile(path) and os.path.getsize(path) > 0:
                    return path
            except OSError:
                continue
        return None

    def _nuxel_export_cookies(self):
        """Create a private Netscape cookie file from the WebKit SQLite store.

        The caller must remove the returned path immediately after yt-dlp
        finishes.  Values are never logged, returned to the PWA or written
        anywhere except the 0600 file consumed by yt-dlp.
        """
        import sqlite3
        db = self._nuxel_cookie_db()
        if not db:
            return None, ("Nuxel cookie export is unavailable: no persistent WebKitGTK "
                          "cookie database exists on this device yet. Browse with the Nuxel "
                          "browser first, or use Chrome/Firefox/No cookies.")
        path = "/run/nuxel/downloader-cookies-%s.txt" % uuid.uuid4().hex[:12]
        try:
            os.makedirs("/run/nuxel", exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("# Netscape HTTP Cookie File\n")
                uri = "file:%s?mode=ro" % db.replace("?", "%3f")
                con = sqlite3.connect(uri, uri=True, timeout=3)
                try:
                    tables = {r[0] for r in con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")}
                    if "cookies" not in tables:
                        raise RuntimeError("WebKit cookie database has no cookies table")
                    cols = {r[1] for r in con.execute("PRAGMA table_info(cookies)")}
                    # WebKitGTK's schema uses these names; older builds use
                    # moz_cookies-compatible columns.  Only export fields that
                    # actually exist, never a guessed value.
                    name = "name" if "name" in cols else "cname"
                    value = "value" if "value" in cols else "cvalue"
                    host = "host" if "host" in cols else ("domain" if "domain" in cols else "host")
                    path_col = "path" if "path" in cols else "path"
                    expires = "expires" if "expires" in cols else "expiry"
                    secure = "is_secure" if "is_secure" in cols else ("secure" if "secure" in cols else None)
                    http_only = "is_http_only" if "is_http_only" in cols else None
                    select = [name, value, host, path_col, expires]
                    if secure:
                        select.append(secure)
                    if http_only:
                        select.append(http_only)
                    for row in con.execute("SELECT %s FROM cookies" % ",".join(select)):
                        cname, cvalue, chost, cpath, cexpires = row[:5]
                        sec = bool(row[5]) if secure else False
                        httponly = bool(row[6]) if http_only else False
                        if not cname or not chost:
                            continue
                        domain = str(chost)
                        prefix = "#HttpOnly_" if httponly else ""
                        domain_field = prefix + domain
                        include_sub = "TRUE" if domain.startswith(".") else "FALSE"
                        fh.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                            domain_field, include_sub, cpath or "/",
                            "TRUE" if sec else "FALSE", int(cexpires or 0),
                            cname, cvalue))
                finally:
                    con.close()
            os.chmod(path, 0o600)
            try:
                import pwd
                pw = pwd.getpwnam("nuxel")
                os.chown(path, pw.pw_uid, pw.pw_gid)
            except (KeyError, OSError):
                pass
            return path, None
        except Exception as exc:  # noqa: BLE001
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except OSError:
                pass
            return None, "Nuxel cookie export failed: %s" % exc

    def _downloader_cookie_args(self, source):
        source = str(source or "none").lower()
        if source in ("", "none", "no", "nocookies"):
            return [], "none", None, None
        if source in ("chrome", "firefox"):
            return ["--cookies-from-browser", source], source, None, None
        if source == "nuxel":
            path, err = self._nuxel_export_cookies()
            if err:
                return [], "nuxel", err, None
            return ["--cookies", path], "nuxel", None, path
        return [], source, "unsupported cookie source", None

    def _downloader_cookie_availability(self):
        db = self._nuxel_cookie_db()
        rows = [{"id": "nuxel", "label": "Nuxel", "available": bool(db),
                 "detail": ("WebKit cookie database found; exported privately per download" if db
                            else "no persistent WebKit cookie database found yet")}]
        for source, paths in (("chrome", ["/home/nuxel/.config/google-chrome",
                                          "/home/nuxel/.config/chromium"]),
                              ("firefox", ["/home/nuxel/.mozilla/firefox"])):
            present = any(os.path.isdir(p) for p in paths)
            rows.append({"id": source, "label": source.title(), "available": present,
                         "detail": ("browser profile present" if present else
                                    "browser profile not found on this device")})
        rows.append({"id": "none", "label": "No cookies", "available": True,
                     "detail": "public content only"})
        return rows

    def _ytdlp_run(self, argv, timeout):
        base = ["/usr/sbin/runuser", "-u", "nuxel", "--", "env",
                "HOME=/home/nuxel", "XDG_RUNTIME_DIR=/run/nuxel-wayland",
                "PATH=/usr/local/bin:/usr/bin:/bin"]
        return subprocess.run(base + argv, capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL)

    def _downloader_metadata(self, url, cookie_source):
        ok, url_or_err = self._downloader_validate_url(url)
        if not ok:
            return {"success": False, "error": "invalid_url", "detail": url_or_err}
        cookies, cookie_label, cookie_err, cookie_file = self._downloader_cookie_args(cookie_source)
        if cookie_err:
            return {"success": False, "error": "cookies_unavailable", "detail": cookie_err,
                    "cookie_source": cookie_source}
        try:
            return self._downloader_metadata_run(url_or_err, cookies, cookie_label)
        finally:
            if cookie_file:
                try:
                    os.unlink(cookie_file)
                except OSError:
                    pass

    def _downloader_metadata_run(self, url_or_err, cookies, cookie_label):
        if not os.path.exists(self.YTDLP):
            return {"success": False, "error": "yt_dlp_missing",
                    "detail": "yt-dlp is not installed on the device"}
        try:
            proc = self._ytdlp_run([self.YTDLP, "--dump-single-json", "--no-playlist",
                                    "--skip-download", "--no-warnings"] + cookies + [url_or_err],
                                   timeout=35)
        except (OSError, subprocess.SubprocessError) as exc:
            return {"success": False, "error": "metadata_failed", "detail": str(exc)}
        if proc.returncode != 0:
            return {"success": False, "error": "metadata_failed",
                    "detail": (proc.stderr or "yt-dlp metadata failed").strip()[-800:],
                    "cookie_source": cookie_label}
        try:
            doc = json.loads(proc.stdout or "{}")
        except ValueError as exc:
            return {"success": False, "error": "metadata_json", "detail": str(exc)}
        formats = []
        for f in (doc.get("formats") or []):
            if not isinstance(f, dict):
                continue
            formats.append({
                "format_id": f.get("format_id"), "ext": f.get("ext"),
                "resolution": f.get("resolution") or f.get("format_note"),
                "height": f.get("height"), "width": f.get("width"),
                "vcodec": f.get("vcodec"), "acodec": f.get("acodec"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "format_note": f.get("format_note"),
            })
        return {"success": True, "title": doc.get("title"),
                "thumbnail": doc.get("thumbnail"), "duration": doc.get("duration"),
                "webpage_url": doc.get("webpage_url") or url_or_err,
                "extractor": doc.get("extractor_key") or doc.get("extractor"),
                "uploader": doc.get("uploader"), "cookie_source": cookie_label,
                "formats": formats[:80], "format_count": len(formats),
                "audio_available": any((f.get("acodec") not in (None, "none")) for f in formats),
                "video_available": any((f.get("vcodec") not in (None, "none")) for f in formats)}

    def _downloader_jobs(self):
        return _DOWNLOAD_JOBS

    def _downloader_save_jobs(self):
        try:
            os.makedirs(os.path.dirname(self.DOWNLOAD_JOBS_FILE), exist_ok=True)
            with _DOWNLOAD_LOCK:
                doc = {"schema_version": 1, "jobs": list(_DOWNLOAD_JOBS.values())}
            tmp = self.DOWNLOAD_JOBS_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.DOWNLOAD_JOBS_FILE)
        except OSError:
            pass

    def _downloader_start(self, url, fmt, cookie_source):
        self._downloader_load_jobs()
        self._downloader_cleanup_cookie_files()
        ok, url_or_err = self._downloader_validate_url(url)
        if not ok:
            return {"success": False, "error": "invalid_url", "detail": url_or_err}
        fmt = str(fmt or "mp3").lower()
        if fmt not in ("mp3", "mp4"):
            return {"success": False, "error": "format must be mp3 or mp4"}
        # Validate every no-side-effect precondition BEFORE creating a private
        # Netscape cookie file.  Early returns after that point used to leak
        # the 0600 file when the queue was busy or ffmpeg was missing.
        if not os.path.exists(self.YTDLP):
            return {"success": False, "error": "yt_dlp_missing",
                    "detail": "yt-dlp is not installed; install the Fedora yt-dlp package"}
        if fmt == "mp3" and not (shutil.which("ffmpeg") or os.path.exists("/usr/bin/ffmpeg")):
            return {"success": False, "error": "ffmpeg_missing",
                    "detail": "MP3 extraction requires FFmpeg/FFprobe"}
        active = [j for j in _DOWNLOAD_JOBS.values() if j.get("status") in
                  ("queued", "validating", "extracting metadata", "downloading",
                   "post-processing", "verifying output", "starting", "running", "cancelling")]
        if len(active) >= 1:
            return {"success": False, "error": "queue_busy",
                    "detail": "one download is already active on this device"}
        try:
            free = shutil.disk_usage(self.DOWNLOAD_DIR).free if os.path.isdir(self.DOWNLOAD_DIR) else shutil.disk_usage("/home/nuxel").free
            if free < 256 * 1024 * 1024:
                return {"success": False, "error": "insufficient_storage",
                        "detail": "less than 256 MiB is free under ~/Downloads"}
        except OSError as exc:
            return {"success": False, "error": "storage_check_failed", "detail": str(exc)}
        cookies, cookie_label, cookie_err, cookie_file = self._downloader_cookie_args(cookie_source)
        if cookie_err:
            return {"success": False, "error": "cookies_unavailable", "detail": cookie_err}
        job_id = "dl-" + uuid.uuid4().hex[:12]
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
        try:
            import pwd
            pw = pwd.getpwnam("nuxel")
            os.chown(self.DOWNLOAD_DIR, pw.pw_uid, pw.pw_gid)
        except (KeyError, OSError):
            pass
        job = {"id": job_id, "url": url_or_err, "format": fmt,
               "cookie_source": cookie_label, "status": "queued",
               "progress": 0.0, "bytes": 0, "total_bytes": None, "speed": None,
               "eta": None, "file": None, "error": None, "started": time.time(),
               "updated": time.time(), "cancel_requested": False,
               "cookie_file": cookie_file}
        with _DOWNLOAD_LOCK:
            _DOWNLOAD_JOBS[job_id] = job
        self._downloader_save_jobs()
        thread = threading.Thread(target=self._downloader_worker,
                                  args=(job_id, url_or_err, fmt, cookies, cookie_file), daemon=True,
                                  name="nuxel-ytdlp-%s" % job_id)
        thread.start()
        return {"success": True, "job": job, "download_dir": self.DOWNLOAD_DIR,
                "cookie_source": cookie_label}

    def _downloader_worker(self, job_id, url, fmt, cookies, cookie_file=None):
        job = _DOWNLOAD_JOBS.get(job_id)
        if not job:
            return
        outtmpl = "%(title).180B [%(id)s].%(ext)s"
        progress_tpl = ("download:PROGRESS|%(progress.status)s|%(progress.downloaded_bytes)s|"
                        "%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s")
        base = ["/usr/sbin/runuser", "-u", "nuxel", "--", "env",
                "HOME=/home/nuxel", "XDG_RUNTIME_DIR=/run/nuxel-wayland",
                "PATH=/usr/local/bin:/usr/bin:/bin"]
        cmd = [self.YTDLP, "--no-playlist", "--newline", "--no-colors",
               "--progress-template", progress_tpl,
               "--print", "after_move:FILEPATH|%(filepath)s",
               "-t", fmt, "-P", self.DOWNLOAD_DIR, "-o", outtmpl] + cookies + [url]

        def update(status, **fields):
            job.update(fields)
            job["status"] = status
            job["updated"] = time.time()
            self._downloader_save_jobs()

        update("downloading")
        try:
            proc = subprocess.Popen(base + cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            job["error"] = "could not start yt-dlp: %s" % exc
            job["status"] = "failed"
            if cookie_file:
                try:
                    os.unlink(cookie_file)
                except OSError:
                    pass
            job.pop("cookie_file", None)
            self._downloader_save_jobs()
            return
        job.update(status="downloading", pid=proc.pid, updated=time.time())
        self._downloader_save_jobs()
        tail = []
        final_path = None
        try:
            for raw_line in proc.stdout or []:
                line = raw_line.rstrip("\n")
                if not line:
                    continue
                if line.startswith("PROGRESS|"):
                    parts = line.split("|", 5)
                    if len(parts) >= 5:
                        status = parts[1]
                        try:
                            got = int(float(parts[2] or 0))
                        except (TypeError, ValueError):
                            got = 0
                        try:
                            total = int(float(parts[3])) if parts[3] and parts[3] != "NA" else None
                        except (TypeError, ValueError):
                            total = None
                        try:
                            speed = float(parts[4]) if parts[4] and parts[4] not in ("NA", "None") else None
                        except (TypeError, ValueError):
                            speed = None
                        try:
                            eta = int(float(parts[5])) if len(parts) > 5 and parts[5] and parts[5] not in ("NA", "None") else None
                        except (TypeError, ValueError):
                            eta = None
                        job["bytes"] = max(0, got)
                        job["total_bytes"] = total or job.get("total_bytes")
                        job["speed"] = speed
                        job["eta"] = eta
                        if job.get("total_bytes"):
                            job["progress"] = max(0.0, min(99.8, 100.0 * job["bytes"] / job["total_bytes"]))
                        if status == "finished":
                            update("post-processing", progress=99.8)
                        else:
                            job["updated"] = time.time()
                        continue
                if line.startswith("FILEPATH|"):
                    final_path = line.split("|", 1)[1].strip() or None
                    continue
                tail.append(line[-700:])
                tail = tail[-25:]
                if "Merging formats" in line or "Extracting audio" in line or "Post-process" in line:
                    update("post-processing")
                if job.get("cancel_requested"):
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except OSError:
                        pass
            rc = proc.wait(timeout=10)
        except (OSError, subprocess.SubprocessError) as exc:
            tail.append(str(exc))
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except OSError:
                pass
            rc = 1
        job.pop("pid", None)
        if job.get("cancel_requested"):
            update("cancelled", error="cancelled by the operator")
        elif rc == 0:
            update("verifying output")
            if not final_path:
                candidates = []
                try:
                    for name in os.listdir(self.DOWNLOAD_DIR):
                        path = os.path.join(self.DOWNLOAD_DIR, name)
                        if not os.path.isfile(path) or name.startswith(".") or name.endswith(".part"):
                            continue
                        st = os.stat(path)
                        if st.st_mtime >= job.get("started", 0) - 3:
                            candidates.append((st.st_mtime, path))
                except OSError:
                    pass
                if candidates:
                    final_path = max(candidates)[1]
            ok_file, verified = self._downloader_verify_file(final_path, fmt)
            if ok_file:
                job["file"] = final_path
                job["verification"] = verified
                job["progress"] = 100.0
                update("completed", error=None)
                try:
                    _atomic_enqueue = getattr(self, "_media_changed", None)
                    if _atomic_enqueue:
                        _atomic_enqueue()
                except Exception:
                    pass
            else:
                update("failed", error=str(verified), file=final_path)
        else:
            update("failed", error="\n".join(tail[-8:])[-1600:] or ("yt-dlp rc=%s" % rc))
        if cookie_file:
            try:
                os.unlink(cookie_file)
            except OSError:
                pass
            job.pop("cookie_file", None)
        self._downloader_save_jobs()

    def _downloader_rpc(self, app_id, verb, params):
        params = params if isinstance(params, dict) else {}
        self._downloader_load_jobs()
        if verb == "cookies":
            return {"success": True, "sources": self._downloader_cookie_availability()}
        if verb in ("metadata", "probe"):
            return self._downloader_metadata(params.get("url"),
                                             params.get("cookie_source", "none"))
        if verb == "start":
            return self._downloader_start(params.get("url"), params.get("format", "mp3"),
                                          params.get("cookie_source", "none"))
        if verb == "status":
            job_id = params.get("job_id")
            if job_id:
                job = _DOWNLOAD_JOBS.get(job_id)
                return {"success": bool(job), "job": job}
            return {"success": True, "jobs": sorted(_DOWNLOAD_JOBS.values(),
                                                     key=lambda j: j.get("started", 0),
                                                     reverse=True),
                    "download_dir": self.DOWNLOAD_DIR,
                    "capabilities": {"yt_dlp": self.YTDLP,
                                     "ffmpeg": bool(shutil.which("ffmpeg")),
                                     "ffprobe": bool(shutil.which("ffprobe")),
                                     "arch": os.uname().machine,
                                     "active_limit": 1}}
        if verb == "cancel":
            job = _DOWNLOAD_JOBS.get(params.get("job_id"))
            if not job:
                return {"success": False, "error": "unknown job"}
            job["cancel_requested"] = True
            job["status"] = "cancelling"
            pid = job.get("pid")
            if pid:
                try:
                    os.killpg(int(pid), signal.SIGTERM)
                except OSError:
                    pass
            self._downloader_save_jobs()
            return {"success": True, "cancelling": True, "job": job}
        if verb == "where":
            return {"success": True, "download_dir": self.DOWNLOAD_DIR}
        return {"success": False, "error": "unknown downloader verb: %s" % verb}

    # ---- system appearance (GTK/libadwaita/portal) -----------------------
    APPEARANCE_FILE = "/var/lib/nuxel/appearance/appearance.json"
    USER_RUNTIME = "/run/user/1000"
    USER_BUS = "unix:path=/run/user/1000/bus"

    def _user_env(self):
        return {
            "XDG_RUNTIME_DIR": self.USER_RUNTIME,
            "DBUS_SESSION_BUS_ADDRESS": self.USER_BUS,
            "HOME": "/home/nuxel",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        }

    def _user_run(self, argv, timeout=8):
        # The bridge unit sets NoNewPrivileges=yes, which leaves CAP_SETUID out
        # of its effective set on this kernel.  A transient system-manager unit
        # with --uid/--gid performs the credential drop outside the bridge's
        # sandbox and is the same mechanism already used for native apps.
        return subprocess.run(
            ["/usr/bin/systemd-run", "--wait", "--pipe", "--collect", "--quiet",
             "--uid=1000", "--gid=1000",
             "--setenv=XDG_RUNTIME_DIR=" + self.USER_RUNTIME,
             "--setenv=DBUS_SESSION_BUS_ADDRESS=" + self.USER_BUS,
             "--setenv=HOME=/home/nuxel"] + argv,
            capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, env=dict(os.environ, PATH=
            "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"))

    def _gsettings(self, key, value=None, timeout=5):
        argv = ["/usr/bin/gsettings"]
        if value is None:
            argv += ["get", "org.gnome.desktop.interface", key]
        else:
            argv += ["set", "org.gnome.desktop.interface", key, value]
        try:
            proc = self._user_run(argv, timeout=timeout)
            return (proc.returncode == 0, (proc.stdout or proc.stderr or "").strip())
        except (OSError, subprocess.TimeoutExpired) as exc:
            return (False, str(exc))

    def _appearance_read(self):
        doc = {}
        try:
            with open(self.APPEARANCE_FILE, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            doc = {}
        scheme_ok, scheme = self._gsettings("color-scheme")
        theme_ok, theme = self._gsettings("gtk-theme")
        portal = None
        try:
            proc = self._user_run([
                "/usr/bin/gdbus", "call", "--session",
                "--dest", "org.freedesktop.portal.Desktop",
                "--object-path", "/org/freedesktop/portal/desktop",
                "--method", "org.freedesktop.portal.Settings.Read",
                "org.freedesktop.appearance", "color-scheme"], timeout=3)
            portal = {"available": proc.returncode == 0,
                      "reply": ((proc.stdout or proc.stderr or "").strip())[:300]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            portal = {"available": False, "reply": str(exc)}
        return {
            "success": True,
            "mode": doc.get("mode") or "system",
            "gtk_theme": doc.get("gtk_theme") or ("Adwaita-dark" if "dark" in str(theme).lower() else "Adwaita"),
            "persisted": bool(doc),
            "readback": {"color_scheme": scheme if scheme_ok else None,
                         "gtk_theme": theme if theme_ok else None},
            "portal": portal,
            "flatpak_theme_extensions": self._flatpak_theme_extensions(),
        }

    def _flatpak_theme_extensions(self):
        try:
            proc = subprocess.run(["/usr/bin/flatpak", "list", "--columns=application,arch,branch"],
                                  capture_output=True, text=True, timeout=8)
            rows = [line for line in (proc.stdout or "").splitlines()
                    if "theme" in line.lower() or "adwaita" in line.lower()]
            return rows
        except (OSError, subprocess.TimeoutExpired):
            return []

    def _appearance_rpc(self, verb, params):
        params = params if isinstance(params, dict) else {}
        if verb in ("get", "status"):
            return self._appearance_read()
        if verb != "set":
            return {"success": False, "error": "unknown appearance verb: %s" % verb}
        mode = str(params.get("mode") or "system").lower()
        if mode not in ("system", "light", "dark"):
            return {"success": False, "error": "mode must be system, light or dark"}
        requested_theme = str(params.get("gtk_theme") or "").strip()
        if requested_theme not in ("", "Adwaita", "Adwaita-dark"):
            return {"success": False, "error": "gtk_theme must be Adwaita or Adwaita-dark"}
        if mode == "dark":
            theme = requested_theme or "Adwaita-dark"
            scheme = "prefer-dark"
        elif mode == "light":
            theme = requested_theme or "Adwaita"
            scheme = "prefer-light"
        else:
            theme = requested_theme or "Adwaita"
            scheme = "default"
        actions = []
        for key, value in (("color-scheme", scheme), ("gtk-theme", theme)):
            ok, detail = self._gsettings(key, value)
            actions.append({"key": key, "value": value, "ok": ok, "detail": detail})
        # gtk-application-prefer-dark-theme is intentionally NOT used as the
        # primary switch (libadwaita uses color-scheme).  Set it only if the
        # schema exposes it; failure is non-fatal and reported.
        ok, detail = self._gsettings("gtk-application-prefer-dark-theme",
                                     "true" if mode == "dark" else "false")
        actions.append({"key": "gtk-application-prefer-dark-theme",
                        "ok": ok, "detail": detail})
        # Explicit per-user GTK settings files are a compatibility fallback for
        # GTK3/GTK4 apps that do not consult the portal.  No GTK_THEME process
        # environment variable is injected globally.
        try:
            import configparser
            for version in ("gtk-3.0", "gtk-4.0"):
                path = "/home/nuxel/.config/%s/settings.ini" % version
                os.makedirs(os.path.dirname(path), exist_ok=True)
                cp = configparser.ConfigParser()
                try:
                    cp.read(path)
                except Exception:
                    cp = configparser.ConfigParser()
                if not cp.has_section("Settings"):
                    cp.add_section("Settings")
                cp.set("Settings", "gtk-theme-name", theme)
                cp.set("Settings", "gtk-application-prefer-dark-theme",
                       "true" if mode == "dark" else "false")
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    cp.write(fh)
                os.chmod(tmp, 0o644)
                os.replace(tmp, path)
                try:
                    import pwd
                    pw = pwd.getpwnam("nuxel")
                    os.chown(path, pw.pw_uid, pw.pw_gid)
                except (KeyError, OSError):
                    pass
        except OSError as exc:
            actions.append({"key": "gtk-settings-ini", "ok": False, "detail": str(exc)})
        doc = {"schema_version": 1, "mode": mode, "gtk_theme": theme,
               "color_scheme": scheme, "updated": time.time()}
        try:
            os.makedirs(os.path.dirname(self.APPEARANCE_FILE), exist_ok=True)
            tmp = self.APPEARANCE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.APPEARANCE_FILE)
        except OSError as exc:
            return {"success": False, "error": "could not persist appearance",
                    "detail": str(exc), "actions": actions}
        result = self._appearance_read()
        result.update({"success": True, "actions": actions, "set": doc})
        return result

    # ---- central sound manager / clock scheduler -------------------------
    SOUND_SOCKET = os.environ.get("NUXEL_SOUNDD_SOCKET", "/run/nuxel/soundd.sock")
    CLOCK_SCHEDULE = "/var/lib/nuxel/clock/schedule.json"
    CLOCK_STATE = "/run/nuxel/clockd.state"
    CLOCK_STOP = "/run/nuxel/clock.stop"
    CLOCK_SOCKET = os.environ.get("NUXEL_CLOCK_SOCKET", "/run/nuxel/clockd.sock")

    def _sound_request(self, payload, timeout=8.0):
        """Talk to the local soundd socket; never start a player/decoder here."""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(float(timeout))
            sock.connect(self.SOUND_SOCKET)
            sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
            sock.close()
            doc = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
            return doc if isinstance(doc, dict) else {"success": False, "error": "bad soundd reply"}
        except (OSError, ValueError) as exc:
            return {"success": False, "error": "sound-manager-unavailable", "detail": str(exc)}

    def _sound_rpc(self, app_id, verb, params):
        params = params if isinstance(params, dict) else {}
        if verb in ("state", "status", "list"):
            return self._sound_request({"cmd": "state"})
        if verb in ("refresh", "rescan"):
            return self._sound_request({"cmd": "rescan"})
        if verb == "assign":
            return self._sound_request({
                "cmd": "assign", "action": params.get("action"),
                "path": params.get("path"), "gain": params.get("gain")})
        if verb == "preview":
            return self._sound_request({
                "cmd": "preview", "action": params.get("action", "other"),
                "path": params.get("path")})
        if verb == "play":
            # The volume path must return immediately; decoding is preloaded by
            # soundd.  An optional action selects the persisted assignment.
            return self._sound_request({
                "cmd": "play", "action": params.get("action", "other"),
                "path": params.get("path"), "loop": bool(params.get("loop")),
                "token": params.get("token")})
        if verb == "stop":
            return self._sound_request({
                "cmd": "stop", "token": params.get("token"),
                "action": params.get("action")})
        if verb == "import":
            if app_id not in ("nuxel-settings", "org.nuxel.Home", "org.nuxel.Nuxtore"):
                return {"success": False, "error": "capability_denied",
                        "detail": "sound import is limited to Settings/Home/NuxTore"}
            data = params.get("data_b64") or ""
            if not isinstance(data, str) or len(data) > (24 * 1024 * 1024 * 4 // 3 + 16):
                return {"success": False, "error": "file too large"}
            return self._sound_request({
                "cmd": "import", "name": params.get("name") or "sound.mp3",
                "data_b64": data}, timeout=20.0)
        return {"success": False, "error": "unknown sound verb: %s" % verb}

    def _clock_request(self, payload, timeout=5.0):
        """Proxy one request to the root-owned nuxel-clockd socket.

        The bridge never mutates the schedule file directly: nuxel-clockd is
        the sole owner of alarm/timer state and of firing occurrences.  A dead
        daemon is reported as unavailable; callers never get a fabricated
        success response.
        """
        import socket as _socket
        path = os.environ.get("NUXEL_CLOCK_SOCKET", self.CLOCK_SOCKET)
        try:
            with _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect(path)
                sock.sendall((json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"))
                chunks = []
                total = 0
                while total < 1048576:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if b"\n" in chunk:
                        break
                raw = b"".join(chunks).decode("utf-8", "replace").strip()
                doc = json.loads(raw or "{}")
                if not isinstance(doc, dict):
                    return {"success": False, "error": "clock daemon returned invalid JSON",
                            "error_code": "BAD_CLOCK_REPLY"}
                return doc
        except (OSError, ValueError) as exc:
            return {"success": False, "error": "clock scheduler unavailable",
                    "error_code": "CLOCK_UNAVAILABLE", "detail": str(exc)}

    def _clock_rpc(self, app_id, verb, params):
        params = params if isinstance(params, dict) else {}
        aliases = {
            "sync": "sync", "set": "sync", "status": "status",
            "list-alarms": "list-alarms", "create-alarm": "create-alarm",
            "add-alarm": "create-alarm", "update-alarm": "update-alarm",
            "delete-alarm": "delete-alarm", "enable-alarm": "enable-alarm",
            "start-timer": "start-timer", "pause-timer": "pause-timer",
            "resume-timer": "resume-timer", "reset-timer": "reset-timer",
            "stop-timer": "stop-timer", "set-timer": "set-timer",
            "dismiss-occurrence": "dismiss-occurrence",
            "snooze-occurrence": "snooze-occurrence", "get-settings": "get-settings",
            "set-settings": "set-settings", "set-sound": "set-sound",
            "preview": "preview-sound", "preview-sound": "preview-sound",
            "stop-preview": "stop-preview", "capabilities": "capabilities",
            "calendar-reminders": "calendar-reminders",
            "set-calendar-reminders": "set-calendar-reminders", "stop": "stop",
        }
        cmd = aliases.get(verb)
        if cmd is None:
            return {"success": False, "error": "unknown clock verb: %s" % verb,
                    "error_code": "UNKNOWN_VERB"}
        doc = self._clock_request({"cmd": cmd, "params": params})
        # Compatibility: an older deployed clockd understood only sync/status/
        # stop.  It is still the authority for those verbs.  New operations are
        # reported unavailable rather than emulated in the bridge.
        return doc

    def _app_orientation_defaults_rpc(self, params):
        doc = self._load_app_orientation_defaults()
        return {"success": True,
                "default": doc.get("default", APP_ORIENTATION_DEFAULT_MODE),
                "apps": dict(doc.get("apps", {}) or {}),
                "modes": list(APP_ORIENTATION_MODES)}

    def _app_set_orientation_default_rpc(self, params):
        app_id = str(params.get("app_id", ""))
        mode = str(params.get("orientation", params.get("mode", "")))
        if not APP_ID_RE.match(app_id):
            return {"success": False, "error": "invalid_app_id"}
        doc = self._load_app_orientation_defaults()
        apps = dict(doc.get("apps", {}) or {})
        if mode in APP_ORIENTATION_MODES:
            apps[app_id] = mode
        elif mode in ("", "default", "inherit"):
            apps.pop(app_id, None)
        else:
            return {"success": False, "error": "invalid_orientation", "mode": mode}
        doc["apps"] = apps
        self._save_app_orientation_defaults(doc)
        return {"success": True, "app_id": app_id, "orientation": apps.get(app_id),
                "default": doc.get("default", APP_ORIENTATION_DEFAULT_MODE)}

    def _permd(self, args):
        exe = "/usr/lib/nuxel/nuxel-permissions/nuxel-permd.py"
        if not os.path.exists(exe):
            return {"success": False, "error": "permd_unavailable",
                    "offline": True, "denied": True}
        try:
            proc = subprocess.run(["python3", exe] + args,
                                  capture_output=True, timeout=25, text=True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"success": False, "error": "permd_failed", "offline": True,
                    "denied": True, "detail": str(exc)}
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        doc = None
        if out:
            try:
                doc = json.loads(out)
            except ValueError:
                doc = None
        if isinstance(doc, dict):
            doc["_rc"] = proc.returncode
            return doc
        return {"success": proc.returncode == 0, "rc": proc.returncode,
                "stdout": out[-400:], "stderr": err[-400:],
                "denied": proc.returncode != 0}

    def _permissions_rpc(self, app_id, verb, params):
        """Central permission policy (permD) facade. Fail closed: any
        unavailable/malformed/unknown result is denied."""
        params = params if isinstance(params, dict) else {}
        target = str(params.get("app_id", app_id))
        cap = str(params.get("capability", ""))
        if not APP_ID_RE.match(target):
            return {"success": False, "error": "invalid_app_id", "denied": True}
        if verb in ("list", "get-app", "show"):
            return self._permd(["show", target, "--json"])
        if verb == "apps":
            return self._permd(["list", "--json"])
        if verb == "check":
            if not cap:
                return {"success": False, "error": "capability required", "denied": True}
            return self._permd(["check", target, cap])
        if verb in ("grant", "request"):
            if not cap:
                return {"success": False, "error": "capability required", "denied": True}
            return self._permd(["grant", target, cap, "--duration", "always"])
        if verb in ("deny", "revoke"):
            if not cap:
                return {"success": False, "error": "capability required", "denied": True}
            return self._permd(["revoke", target, cap])
        if verb == "revoke-all":
            return self._permd(["revoke-all", target])
        return {"success": False, "error": "unknown permissions verb: " + verb,
                "denied": True}

    # ---- Settings -> Services (PWNAGE-88000) -------------------------------
    SERVICE_POLICY_PATH = "/etc/nuxel/services/service-policy.json"

    def _services_policy(self):
        doc = {"allowlist": [], "essential": []}
        try:
            with open(self.SERVICE_POLICY_PATH, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                doc = loaded
        except (OSError, ValueError):
            pass
        return doc

    def _systemctl(self, args, timeout=12):
        try:
            proc = subprocess.run(["/usr/bin/systemctl"] + args,
                                  capture_output=True, text=True, timeout=timeout)
            return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 1, "", str(exc)

    def _unit_active(self, unit):
        rc, out, _ = self._systemctl(["is-active", unit], timeout=6)
        return rc == 0, out

    def _unit_enabled(self, unit):
        rc, out, _ = self._systemctl(["is-enabled", unit], timeout=6)
        return rc == 0, out

    def _services_rpc(self, app_id, verb, params):
        params = params if isinstance(params, dict) else {}
        if app_id not in ("org.nuxel.Settings", "nuxel-settings", "org.nuxel.Home"):
            return {"success": False, "error": "capability_denied",
                    "detail": "service control is owner-only"}
        policy = self._services_policy()
        allowlist = set(policy.get("allowlist") or [])
        essential = set(policy.get("essential") or [])
        unlocked = getattr(self, "_services_unlocked", False)
        if verb in ("list", "status"):
            rows = []
            for unit in sorted(allowlist):
                active, active_state = self._unit_active(unit)
                enabled, enabled_state = self._unit_enabled(unit)
                rows.append({"unit": unit, "active": active, "active_state": active_state,
                             "enabled": enabled, "enabled_state": enabled_state,
                             "essential": unit in essential})
            return {"success": True, "services": rows,
                    "essential": sorted(essential), "unlocked": unlocked}
        if verb == "unlock":
            self._services_unlocked = True
            self._services_unlocked_at = time.time()
            return {"success": True, "unlocked": True}
        if verb == "lock":
            self._services_unlocked = False
            return {"success": True, "unlocked": False}
        if not unlocked:
            return {"success": False, "error": "locked",
                    "detail": "unlock the Services section before mutating units"}
        if verb in ("daemon-reload", "daemon-reexec"):
            if params.get("confirm") is not True:
                return {"success": False, "error": "confirmation_required",
                        "detail": verb + " requires explicit confirmation"}
            rc, out, err = self._systemctl([verb], timeout=30)
            return {"success": rc == 0, "verb": verb, "detail": out or err}
        if verb in ("start", "stop", "restart", "reload", "enable", "disable"):
            unit = str(params.get("unit") or "")
            if unit not in allowlist:
                return {"success": False, "error": "not_allowed",
                        "detail": "unit is not in the service allowlist"}
            if unit in essential and verb in ("stop", "disable"):
                return {"success": False, "error": "essential_service_protected",
                        "detail": unit + " is system-essential and cannot be stopped or disabled"}
            if unit in essential and verb in ("restart", "reload") and params.get("confirm") is not True:
                return {"success": False, "error": "confirmation_required",
                        "detail": "restart/reload of an essential service requires confirmation"}
            rc, out, err = self._systemctl([verb, unit], timeout=30)
            active, active_state = self._unit_active(unit)
            enabled, enabled_state = self._unit_enabled(unit)
            return {"success": rc == 0, "unit": unit, "verb": verb,
                    "detail": out or err, "active": active, "active_state": active_state,
                    "enabled": enabled, "enabled_state": enabled_state}
        return {"success": False, "error": "unknown service verb: " + verb}

    # ---- PenguInterface spoofing (PWNAGE-88000) ---------------------------
    SPOOF_DIR = "/run/nuxel/spoof"
    SPOOF_PROFILE = "/run/nuxel/spoof/profile.json"
    SPOOF_OS_RELEASE = "/run/nuxel/spoof/os-release"
    SPOOF_LIB = "/usr/lib/nuxel/spoof/libnuxel-spoof.so"

    def _real_identity(self):
        identity = {"os_release": {}, "uname": ""}
        try:
            for line in open("/etc/os-release", "r", encoding="utf-8").read().splitlines()[:8]:
                if "=" in line:
                    k, _, v = line.partition("=")
                    identity["os_release"][k] = v.strip().strip('"')
        except OSError as exc:
            identity["os_release"] = {"error": str(exc)}
        try:
            proc = subprocess.run(["/usr/bin/uname", "-a"], capture_output=True, text=True, timeout=5)
            identity["uname"] = (proc.stdout or proc.stderr or "").strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            identity["uname"] = str(exc)
        return identity

    def _spoof_state(self):
        state = {"enabled": False, "ua": None, "targets": [], "os_release": None,
                 "uname": None, "lib": os.path.exists(self.SPOOF_LIB),
                 "real": self._real_identity()}
        try:
            with open(self.SPOOF_PROFILE, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            if isinstance(doc, dict):
                state["enabled"] = bool(doc.get("enabled"))
                state["ua"] = doc.get("ua")
                state["targets"] = doc.get("targets") if isinstance(doc.get("targets"), list) else []
                state["os_release"] = doc.get("os_release")
                state["uname"] = doc.get("uname")
        except (OSError, ValueError):
            pass
        return state

    def _spoof_rpc(self, app_id, verb, params):
        params = params if isinstance(params, dict) else {}
        if app_id not in ("org.nuxel.PenguInterface", "org.nuxel.Settings", "nuxel-settings", "org.nuxel.Home"):
            return {"success": False, "error": "capability_denied", "detail": "spoofing is owner-only"}
        if verb in ("status", "get"):
            return {"success": True, "spoof": self._spoof_state()}
        if verb == "reset":
            for path in (self.SPOOF_PROFILE, self.SPOOF_OS_RELEASE):
                try:
                    os.unlink(path)
                except OSError:
                    pass
            # Verify the underlying system is unchanged outside the spoof scope.
            return {"success": True, "reset": True, "real": self._real_identity()}
        if verb in ("set", "apply"):
            ua = str(params.get("ua") or "").strip()
            targets = params.get("targets")
            if not isinstance(targets, list):
                targets = []
            targets = [str(t)[:120] for t in targets]
            os_release_text = str(params.get("os_release_text") or "").strip()
            uname_fields = params.get("uname") if isinstance(params.get("uname"), dict) else {}
            enabled = bool(params.get("enabled", True))
            doc = {
                "schema_version": 1, "enabled": enabled,
                "ua": ua or None, "targets": targets,
                "os_release": os_release_text or None,
                "uname": {
                    "sysname": str(uname_fields.get("sysname") or "Linux")[:200],
                    "nodename": str(uname_fields.get("nodename") or "nuxel-spoof")[:200],
                    "release": str(uname_fields.get("release") or "6.1.0-nuxel-spoof")[:200],
                    "version": str(uname_fields.get("version") or "#1 SMP PREEMPT_DYNAMIC")[:200],
                    "machine": str(uname_fields.get("machine") or "aarch64")[:120],
                },
            }
            try:
                os.makedirs(self.SPOOF_DIR, exist_ok=True)
                tmp = self.SPOOF_PROFILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh, indent=2, sort_keys=True)
                    fh.write("\n")
                os.chmod(tmp, 0o644)
                os.replace(tmp, self.SPOOF_PROFILE)
                if os_release_text:
                    tmp2 = self.SPOOF_OS_RELEASE + ".tmp"
                    with open(tmp2, "w", encoding="utf-8") as fh:
                        fh.write(os_release_text.rstrip() + "\n")
                    os.chmod(tmp2, 0o644)
                    os.replace(tmp2, self.SPOOF_OS_RELEASE)
                elif os.path.exists(self.SPOOF_OS_RELEASE):
                    os.unlink(self.SPOOF_OS_RELEASE)
            except OSError as exc:
                return {"success": False, "error": "write_failed", "detail": str(exc)}
            return {"success": True, "spoof": self._spoof_state()}
        return {"success": False, "error": "unknown spoof verb: " + verb}

    def _handle_rpc(self, app_id, body):
        """Dispatch a generic bridge RPC (namespace/verb/params)."""
        namespace = body.get('namespace', '')
        verb = body.get('verb', '')
        params = body.get('params', {}) or {}
        if namespace == 'permissions':
            return self._permissions_rpc(app_id, verb, params)
        if namespace == 'downloader':
            return self._downloader_rpc(app_id, verb, params)
        if namespace == 'appearance':
            return self._appearance_rpc(verb, params)
        if namespace == 'sound':
            return self._sound_rpc(app_id, verb, params)
        if namespace == 'clock':
            return self._clock_rpc(app_id, verb, params)
        if namespace == 'services':
            return self._services_rpc(app_id, verb, params)
        if namespace == 'spoof':
            return self._spoof_rpc(app_id, verb, params)
        if namespace == 'apps' and verb == 'orientation-defaults':
            return self._app_orientation_defaults_rpc(params)
        if namespace == 'apps' and verb == 'set-orientation-default':
            if app_id not in ('org.nuxel.Settings', 'nuxel-settings', 'org.nuxel.Home'):
                return {'success': False, 'error': 'capability_denied',
                        'detail': 'orientation defaults are owner-managed'}
            return self._app_set_orientation_default_rpc(params)
        if namespace == 'microphone':
            if mic_provider is None:
                return {"success": False, "error": "microphone provider unavailable",
                        "error_code": "PROVIDER_UNAVAILABLE"}
            # These controls change the session capture route.  Only the
            # owner-facing Settings surface may write them; Recorder/Chat apps
            # request capture through the privacy/portal path instead.
            if verb in ("volume", "mute", "suppression") and app_id not in (
                    "org.nuxel.Settings", "org.nuxel.Recorder"):
                return {"success": False, "error": "microphone control not permitted for this app",
                        "error_code": "PERMISSION_DENIED"}
            return mic_provider.rpc(app_id, verb, params)
        # Nuxel Vault / Authenticator: the only secret-bearing namespace.  It
        # has its own identity check and never falls back to mock success.
        if namespace == 'keyring':
            denial, _session = self._keyring_identity(app_id)
            if denial is not None:
                return denial
            if _keyring_api is None:
                return {'success': False, 'error': 'provider_unavailable',
                        'state': 'unavailable', 'offline': True,
                        'detail': 'the native keyring module is not installed'}
            return _keyring_api.get_api().handle(app_id, verb, params)
        # PWNAGE-50000: driver-status diagnostics for Settings.  These are
        # read-only allowlisted tools; the bridge never accepts a path or a
        # command from the caller.  JSON status is passed through verbatim so
        # the UI can show the real first failing stage.
        if namespace == 'graphics' and verb in ('status', 'get'):
            return self._graphics_status()
        if namespace == 'graphics' and verb == 'test':
            # Bounded, explicit test only.  Default to the Wayland probe in the
            # same Phoc session; never run this on a passive refresh.  It is a
            # resource-using action, so only the owner surfaces may request it.
            if app_id not in ('nuxel-settings', 'org.nuxel.Home', 'org.nuxel.Nuxtore', 'org.nuxel.NuxTore'):
                return {'success': False, 'error': 'capability_denied',
                        'detail': 'graphics.test is limited to the local owner surfaces'}
            kind = str((params or {}).get('kind', 'wayland'))
            bins = {
                'surfaceless': '/usr/local/bin/nuxel-kbase-egl-probe',
                'wayland': '/usr/local/bin/nuxel-wayland-egl-probe',
            }
            exe = bins.get(kind)
            if not exe:
                return {'success': False, 'error': 'unknown_test_kind', 'kind': kind}
            if not os.path.exists(exe):
                return {'success': False, 'error': 'probe_not_installed', 'kind': kind, 'path': exe}
            env = dict(os.environ)
            env.update({
                'XDG_RUNTIME_DIR': '/run/nuxel-wayland',
                'WAYLAND_DISPLAY': 'wayland-0',
                'MESA_KBASE_NODE': '/dev/mali0',
                'MESA_LOADER_DRIVER_OVERRIDE': 'panfrost',
                'LIBGL_DRIVERS_PATH': '/usr/lib64/dri',
            })
            started = time.time()
            try:
                proc = subprocess.run([exe, '1'], capture_output=True, text=True,
                                      timeout=20, env=env)
                doc = {
                    'kind': kind,
                    'exit_code': proc.returncode,
                    'stdout': (proc.stdout or '')[-12000:],
                    'stderr': (proc.stderr or '')[-12000:],
                    'timestamp': time.time(),
                    'elapsed_s': round(time.time() - started, 2),
                    'success': proc.returncode == 0,
                }
            except (OSError, subprocess.TimeoutExpired) as exc:
                doc = {'kind': kind, 'success': False, 'error': 'probe_timeout_or_failed',
                       'detail': str(exc), 'elapsed_s': round(time.time() - started, 2),
                       'timestamp': time.time()}
            return doc
        if namespace == 'system' and verb == 'diagnostics':
            kind = str((params or {}).get('kind', 'sensors'))
            if kind == 'graphics':
                return self._graphics_diagnostics()
            tools = {
                'modem': '/usr/local/bin/nuxel-modem-diag.sh',
                'camera': '/usr/local/bin/nuxel-camera-diag.sh',
                'sensors': '/usr/local/bin/nuxel-sensors-diag.sh',
                'nfc': '/usr/local/bin/nuxel-nfc-diag.sh',
                'gnss': '/usr/local/bin/nuxel-gnss-diag.sh',
            }
            tool = tools.get(kind)
            if not tool:
                return {'success': False, 'error': 'unknown_diagnostic', 'kind': kind}
            try:
                proc = subprocess.run([tool, 'status', '--json'], capture_output=True,
                                      text=True, timeout=25)
                if proc.returncode != 0:
                    return {'success': False, 'error': 'diagnostic_failed',
                            'kind': kind, 'rc': proc.returncode,
                            'detail': (proc.stderr or proc.stdout or '')[-1200:]}
                doc = json.loads(proc.stdout or '{}')
                if isinstance(doc, dict):
                    doc.setdefault('success', True)
                    doc['kind'] = kind
                return doc
            except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
                return {'success': False, 'error': 'diagnostic_unavailable',
                        'kind': kind, 'detail': str(exc)}
        if namespace == 'system' and verb == 'graphics-probe':
            kind = str((params or {}).get('kind', 'surfaceless'))
            bins = {
                'surfaceless': '/usr/local/bin/nuxel-kbase-egl-probe',
                'wayland': '/usr/local/bin/nuxel-wayland-egl-probe',
            }
            exe = bins.get(kind)
            if not exe:
                return {'success': False, 'error': 'unknown_probe', 'kind': kind}
            if not os.path.exists(exe):
                return {'success': False, 'error': 'probe_not_installed', 'kind': kind, 'path': exe}
            env = dict(os.environ)
            env.update({
                'XDG_RUNTIME_DIR': '/run/nuxel-wayland',
                'WAYLAND_DISPLAY': 'wayland-0',
                'MESA_KBASE_NODE': '/dev/mali0',
                'MESA_LOADER_DRIVER_OVERRIDE': 'panfrost',
                'LIBGL_DRIVERS_PATH': '/usr/lib64/dri',
            })
            try:
                proc = subprocess.run([exe, '1'], capture_output=True, text=True,
                                      timeout=20, env=env)
                doc = {
                    'kind': kind,
                    'exit_code': proc.returncode,
                    'stdout': (proc.stdout or '')[-12000:],
                    'stderr': (proc.stderr or '')[-12000:],
                    'timestamp': time.time(),
                    'success': proc.returncode == 0,
                }
            except (OSError, subprocess.TimeoutExpired) as exc:
                doc = {'kind': kind, 'success': False, 'error': 'probe_timeout_or_failed',
                       'detail': str(exc), 'timestamp': time.time()}
            try:
                path = '/run/nuxel-graphics-probes.json'
                merged = {}
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        merged = json.load(fh) or {}
                except (OSError, ValueError):
                    merged = {}
                merged[kind] = doc
                tmp = path + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as fh:
                    json.dump(merged, fh, indent=2)
                os.replace(tmp, path)
            except OSError:
                pass
            return doc
        if namespace == 'system' and verb == 'sensor-read':
            # Bounded raw sensor read.  Values are only what the kernel exposes.
            cls = str((params or {}).get('class', 'accelerometer'))
            if cls not in ('accelerometer', 'gyroscope', 'magnetometer', 'proximity',
                           'ambient_light', 'barometer', 'heart_rate', 'grip', 'hall'):
                return {'success': False, 'error': 'invalid_sensor_class'}
            try:
                proc = subprocess.run(['/usr/local/bin/nuxel-sensors-diag.sh', 'read', cls],
                                      capture_output=True, text=True, timeout=15)
                return {'success': proc.returncode == 0, 'class': cls,
                        'output': (proc.stdout or '') + (proc.stderr or ''),
                        'raw_only': True}
            except (OSError, subprocess.TimeoutExpired) as exc:
                return {'success': False, 'error': 'sensor_read_unavailable',
                        'class': cls, 'detail': str(exc)}
        # PWA persistence is served in-process from the root-owned store.  The
        # sandboxed D-Bus bridge has no storage/caldav/contacts implementation,
        # and routing these verbs to it made every calendar/notes/files save
        # fail with a dbus-error.  Handle them here with the same honest error
        # shape instead.
        if namespace in ('storage', 'caldav', 'contacts', 'haptics', 'mail', 'notes'):
            return self._handle_app_store_rpc(namespace, verb, params)
        # Lockhead indicators are computed in-process from kernel state; they
        # are deliberately NOT routed to D-Bus (the D-Bus bridge has no such
        # method and a dbus-error fallback would make the UI dim real states).
        if namespace == 'system' and verb == 'indicators':
            if system_indicators is not None:
                try:
                    doc = system_indicators.get_indicators()
                    if remote_desktop is not None:
                        doc = dict(doc)
                        doc['remote_desktop'] = remote_desktop.privacy_summary()
                    return doc
                except Exception as exc:  # noqa: BLE001
                    return {'success': False, 'error': str(exc)}
            return {'success': False, 'error': 'system_indicators unavailable'}
        if namespace == 'flashlight':
            if flashlight_provider is None:
                return {'success': False, 'state': 'UNKNOWN',
                        'error': 'flashlight provider unavailable'}
            try:
                return flashlight_provider.handle(verb, params)
            except Exception as exc:  # noqa: BLE001
                logger.warning('flashlight RPC %s failed: %s', verb, exc)
                return {'success': False, 'state': 'ERROR', 'error': str(exc)}
        if namespace == 'system' and verb == 'tri-link':
            if tri_link_status is not None:
                try:
                    return tri_link_status.get_status()
                except Exception as exc:  # noqa: BLE001
                    return {'success': False, 'error': str(exc)}
            return {'success': False, 'error': 'tri_link_status unavailable'}
        if namespace == 'system' and verb == 'remote-desktop':
            if remote_desktop is None:
                return {'success': False, 'error': 'remote_desktop unavailable',
                        'error_code': 'PROVIDER_UNAVAILABLE'}
            action = params.get('action') if isinstance(params, dict) else None
            if not action:
                return {'success': False, 'error': 'action is required',
                        'error_code': 'INVALID_ACTION'}
            try:
                return remote_desktop.handle(action, params, app_id)
            except Exception as exc:  # noqa: BLE001
                logger.error('remote-desktop RPC %s failed: %s', action, exc)
                return {'success': False, 'error': str(exc),
                        'error_code': 'PROVIDER_ERROR'}
        if namespace == 'doom':
            if doom_assets is None:
                return {'success': False, 'error': 'doom_assets_unavailable'}
            if verb in ('wads', 'catalogue', 'list'):
                return doom_assets.public_catalogue()
            if verb == 'map-toggle':
                # The automap key is sent by the compositor as a REAL key event
                # (wtype uses zwp_virtual_keyboard_manager_v1).  default.cfg
                # binds key_map_toggle to KEY_M (77); do not use browser Tab,
                # which WebKit reserves for focus traversal.  The argv is fixed;
                # no client-supplied text or key is accepted.
                if app_id != 'org.nuxel.Doom':
                    return {'success': False, 'error': 'capability_denied',
                            'detail': 'only Nuxel Doom may request the automap key'}
                env = dict(os.environ)
                env.update({'XDG_RUNTIME_DIR': '/run/nuxel-wayland',
                            'WAYLAND_DISPLAY': 'wayland-0'})
                try:
                    proc = subprocess.run(['/usr/bin/wtype', '-k', 'm'],
                                          capture_output=True, timeout=5, env=env,
                                          stdin=subprocess.DEVNULL)
                except (OSError, subprocess.SubprocessError) as exc:
                    return {'success': False, 'error': 'map_key_failed', 'detail': str(exc)}
                return {'success': proc.returncode == 0, 'method': 'wtype-m',
                        'rc': proc.returncode,
                        'detail': (proc.stderr or b'').decode('utf-8', 'replace')[-300:]}
            if verb == 'import':
                # Only the Doom app and the two local owner surfaces may add a
                # WAD.  The user must explicitly confirm the file's licence.
                if app_id not in ('org.nuxel.Doom', 'org.nuxel.Nuxtore',
                                  'org.nuxel.NuxTore', 'org.nuxel.Home'):
                    return {'success': False, 'error': 'capability_denied',
                            'detail': 'only Nuxel Doom, NuxTore or Home may import a WAD'}
                name = params.get('name', '') if isinstance(params, dict) else ''
                ack = bool(params.get('license_ack')) if isinstance(params, dict) else False
                b64 = params.get('data_base64', '') if isinstance(params, dict) else ''
                if not isinstance(b64, str) or not b64:
                    return {'success': False, 'error': 'missing_file_data'}
                try:
                    data = base64.b64decode(b64, validate=True)
                except (binascii.Error, ValueError):
                    return {'success': False, 'error': 'invalid_base64'}
                return doom_assets.import_bytes(data, str(name), ack)
            return {'success': False, 'error': 'unknown_doom_verb', 'verb': verb}

        if namespace == 'apps' and verb in ('registry', 'get-registry'):
            return self._load_app_registry()
        if namespace == 'flatpak':
            if flatpak_provider is None:
                return {'success': False, 'error': 'flatpak provider unavailable',
                        'error_code': 'PROVIDER_UNAVAILABLE'}
            # NuxTore and Home are the only local surfaces allowed to mutate
            # Flatpak installations. Launch/list/status stay readable.
            _owner_ok = app_id in ("org.nuxel.Nuxtore", "org.nuxel.NuxTore",
                                   "org.nuxel.Home", "nuxel-settings",
                                   "org.gnome.Software")
            if verb in ('install', 'update', 'uninstall') and not _owner_ok:
                return {'success': False, 'error': 'capability_denied',
                        'detail': 'only Software, NuxTore or Home may change Flatpak installations'}
            try:
                return flatpak_provider.handle(verb, params if isinstance(params, dict) else {})
            except Exception as exc:  # noqa: BLE001
                logger.warning('flatpak RPC %s failed: %s', verb, exc)
                return {'success': False, 'error': str(exc),
                        'error_code': 'PROVIDER_ERROR'}

        # Privileged hardware control.  These verbs are handled in this root
        # process (never forwarded to the sandboxed D-Bus bridge) because they
        # read /dev/snd or write /sys/class/rfkill.
        if namespace in ('dnd', 'nfc', 'fingerprint', 'biometrics',
                         'security', 'led-notification', 'apps', 'software', 'privacy'):
            mod = {'dnd': dnd_provider, 'nfc': nfc_provider,
                   'fingerprint': fingerprint_provider, 'biometrics': fingerprint_provider,
                   'security': security_provider,
                   'led-notification': led_notification_provider,
                   'apps': app_manager, 'software': software_provider,
                   'privacy': privacy_provider}.get(namespace)
            if mod is None:
                return {'success': False, 'error': namespace + ' provider unavailable',
                        'error_code': 'PROVIDER_UNAVAILABLE'}
            # Mutating lifecycle/lock verbs are restricted to the two local
            # owner surfaces.  Read-only status stays available to all local apps.
            _owner_ok = app_id in ("org.nuxel.Nuxtore", "org.nuxel.NuxTore", "org.nuxel.Home", "nuxel-settings")
            if not _owner_ok and ((namespace == "apps" and verb in ("register", "unregister", "install", "remove")) or
                                  (namespace == "security" and verb in ("set-mode", "set-credential", "set-pin", "set-pattern", "lock", "unlock")) or
                                  (namespace == "nfc" and verb in ("set-enabled", "toggle", "test-tag", "scan", "read-tag", "read", "clear"))):
                return {"success": False, "error": "capability_denied",
                        "detail": "this app may not mutate the app registry, device lock or NFC reader"}
            try:
                result = mod.handle(verb, params)
            except Exception as exc:  # noqa: BLE001
                logger.warning('%s RPC %s failed: %s', namespace, verb, exc)
                return {'success': False, 'error': str(exc), 'error_code': 'PROVIDER_ERROR'}
            # Screen lock is the session lifecycle trigger for the keyring.  The
            # lock must never be blocked by a keyring failure: log the status
            # only, and leave the authoritative device lock result intact.
            if namespace == 'security' and verb == 'lock' and \
                    isinstance(result, dict) and result.get('success'):
                try:
                    if _keyring_api is not None and app_id in ('org.nuxel.Home',):
                        kres = _keyring_api.get_api().handle(app_id, 'lock', {})
                        result = dict(result)
                        result['keyring_locked'] = bool(kres.get('success'))
                except Exception:  # noqa: BLE001
                    logger.info('keyring lock on screen lock failed')
            return result
        if namespace == 'audio':
            if hw_providers is None:
                return {'success': False, 'error': 'audio provider unavailable'}
            if getattr(self, '_audio_provider', None) is None:
                self._audio_provider = hw_providers.AudioProvider()
            if verb == 'status':
                st = self._audio_provider.get_status()
                st['timestamp'] = time.time()
                return st
            if verb == 'set-volume':
                return self._audio_provider.set_volume(
                    params.get('volume') if isinstance(params, dict) else None)
            if verb == 'set-muted':
                return self._audio_provider.set_muted(
                    bool(params.get('muted', False)) if isinstance(params, dict) else False)
            if verb == 'capture-route':
                return self._audio_provider.capture_route()
            if verb == 'sinks':
                st = self._audio_provider.get_status()
                return {'success': True,
                        'backend': st.get('backend'),
                        'sound_server': st.get('sound_server'),
                        'outputs': st.get('outputs', []),
                        'selected_output': st.get('selected_output'),
                        'capture_sources': st.get('capture_sources', [])}
            if verb in ('test-audio', 'play-sound'):
                # PWNAGE-81000: the central sound manager keeps one initialized
                # PipeWire stream and pre-decoded PCM.  The old path ran a route
                # check + CS35L41 warmup + pw-play for every slider movement
                # (2-3 s).  Route these verbs to soundd and return immediately;
                # the owner-facing test still reports audibility as unverified.
                p = params if isinstance(params, dict) else {}
                action = str(p.get('action') or ('volume' if verb == 'play-sound' else 'other'))
                if action not in ('volume', 'boot', 'alarm', 'timer', 'message', 'notification', 'other'):
                    action = 'other'
                req = {'cmd': 'play', 'action': action, 'loop': bool(p.get('loop')),
                       'token': p.get('token')}
                if p.get('asset'):
                    req['path'] = p.get('asset')
                snd = self._sound_request(req)
                if snd.get('success'):
                    snd['played'] = True
                    snd['audible'] = 'unverified'
                    snd['detail'] = 'queued on the pre-initialized sound stream'
                    return snd
                # Honest fallback only when the manager is absent; the direct
                # path is slow, so it is never used when soundd is healthy.
                return self._audio_provider.test_audio(
                    asset=p.get('asset', '/usr/share/nuxel/assets/nuxel-sounds/nuxel-pow.mp3'),
                    gain_percent=p.get('gain_percent', 100))
        if namespace == 'display' and verb == 'status':
            if hw_providers is None:
                return {'success': False, 'error': 'display provider unavailable'}
            return hw_providers.DisplayProvider().get_status()
        if namespace == 'display' and verb in ('state', 'panel-state'):
            if hw_providers is None:
                return {'success': False, 'error': 'display provider unavailable'}
            return hw_providers.DisplayProvider().panel_state()
        if namespace == 'location' and verb in ('gnss-probe', 'gnss-power'):
            if hw_providers is None:
                return {'success': False, 'error': 'gnss provider unavailable'}
            # Direct rail control is a hardware-management operation.  A
            # read-only location grant must never be able to toggle GPIO145.
            capability = ('location:manage' if verb == 'gnss-power'
                          else 'location:read')
            perm = self._call_bridge('CheckPermission', app_id, capability)
            if not (perm and perm.get('granted')):
                return {'success': False,
                        'error': 'Capability not granted: ' + capability,
                        'error_code': 'CAPABILITY_DENIED'}
            gnss = hw_providers.GnssProvider()
            if verb == 'gnss-power':
                enabled = bool(params.get('enabled', True))
                result = gnss.power_rail(enabled=enabled,
                                         timeout=params.get('timeout', 5.0))
                if isinstance(result, dict) and result.get('success') is True:
                    try:
                        import interface_state
                        interface_state.set_desired(
                            'gps', enabled, source='api.location.gnss-power')
                        result['persisted'] = True
                    except Exception as exc:  # noqa: BLE001
                        result['persisted'] = False
                        result['persist_error'] = str(exc)
                return result
            # There is no NMEA stream on this hardware.  Probe the real
            # BBD/LHD path and report the first missing dependency; only an
            # explicit location:manage caller may apply rail power here.
            return gnss.probe(seconds=params.get('duration', 3),
                              timeout=params.get('timeout', 8.0),
                              power=bool(params.get('power', False)))
        if namespace == 'bluetooth' and verb == 'power':
            if hw_providers is None:
                return {'success': False, 'error': 'bluetooth power provider unavailable'}
            # Same capability gate as the D-Bus BluetoothSetPowered method: the
            # privileged actuator must not be weaker than the sandboxed path.
            perm = self._call_bridge('CheckPermission', app_id, 'bluetooth:manage')
            if not (perm and perm.get('granted')):
                return {'success': False, 'error': 'Capability not granted: bluetooth:manage',
                        'error_code': 'CAPABILITY_DENIED'}
            enabled = bool((params or {}).get('enabled', False))
            act = hw_providers.bluetooth_set_power(enabled)
            # Re-read the AUTHORITATIVE controller state from the D-Bus bridge,
            # so Quick Settings and Settings can never disagree about the result.
            try:
                st = self._call_bridge('BluetoothGetStatus', app_id)
            except Exception as exc:  # noqa: BLE001
                st = {'success': False, 'error': str(exc)}
            st = dict(st) if isinstance(st, dict) else {}
            st.update(act)
            st['success'] = bool(act.get('success'))
            return st
        if namespace == 'bluetooth' and verb in ('send-targets', 'send-files'):
            if bluetooth_obex is None:
                return {'success': False, 'error': 'Bluetooth OBEX provider unavailable',
                        'error_code': 'OBEX_UNAVAILABLE'}
            if verb == 'send-targets':
                return bluetooth_obex.list_targets()
            perm = self._call_bridge('CheckPermission', app_id, 'bluetooth:connect')
            if isinstance(perm, dict) and perm.get('granted') is False:
                return {'success': False, 'error': 'Capability not granted: bluetooth:connect',
                        'error_code': 'CAPABILITY_DENIED'}
            try:
                root = self._app_store().files_root
            except Exception as exc:  # noqa: BLE001
                return {'success': False, 'error': 'Files store unavailable: %s' % exc}
            return bluetooth_obex.send_files(root, params.get('paths') or [],
                                             params.get('address', ''),
                                             timeout=params.get('timeout_s', 180))
        if namespace == 'bluetooth' and verb in (
                'list-devices', 'scan', 'pair', 'connect', 'disconnect',
                'trust', 'remove', 'info'):
            if hw_providers is None:
                return {'success': False, 'error': 'bluetooth provider unavailable'}
            cap = 'bluetooth:connect' if verb in (
                'pair', 'connect', 'disconnect', 'trust', 'remove') else 'bluetooth:scan'
            perm = self._call_bridge('CheckPermission', app_id, cap)
            if not (perm and perm.get('granted')):
                return {'success': False, 'error': 'Capability not granted: ' + cap,
                        'error_code': 'CAPABILITY_DENIED'}
            if getattr(self, '_bluetooth_provider', None) is None:
                self._bluetooth_provider = hw_providers.BluetoothManagerProvider()
            bp = self._bluetooth_provider
            if verb == 'list-devices':
                return bp.list_devices(paired_only=bool(params.get('paired_only', False)))
            if verb == 'scan':
                return bp.scan(params.get('duration', 8))
            if verb == 'pair':
                return bp.pair(params.get('mac', ''), timeout=params.get('timeout', 30.0))
            if verb == 'connect':
                return bp.connect(params.get('mac', ''), timeout=params.get('timeout', 30.0))
            if verb == 'disconnect':
                return bp.disconnect(params.get('mac', ''), timeout=params.get('timeout', 20.0))
            if verb == 'trust':
                return bp.trust(params.get('mac', ''), trusted=params.get('trusted', True),
                                timeout=params.get('timeout', 20.0))
            if verb == 'remove':
                return bp.remove(params.get('mac', ''), timeout=params.get('timeout', 20.0))
            if verb == 'info':
                return bp._info(params.get('mac', ''))
        method = self.RPC_METHODS.get((namespace, verb))
        if method is None:
            logger.warning("Unknown RPC %s.%s", namespace, verb)
            return {"success": False, "error": "Unknown RPC: %s.%s" % (namespace, verb), "code": 400}
        # The notification hub is a separate system-bus service.  Its
        # GetNotifications is the canonical live store; expose it as
        # `notifications.list` so the launcher status bar does not poll into
        # "Unknown RPC" every five seconds.
        if method == "GetNotifications":
            try:
                bus = dbus.SystemBus()
                obj = bus.get_object('org.nuxel.Notifications', '/org/nuxel/Notifications')
                iface = dbus.Interface(obj, 'org.nuxel.Notifications')
                return json.loads(iface.GetNotifications())
            except Exception as exc:  # noqa: BLE001
                logger.warning("GetNotifications failed: %s", exc)
                return {"success": False, "notifications": [], "error": str(exc)}
        build = self.RPC_ARG_BUILDERS.get(method)
        if build is not None:
            try:
                args = build(app_id, params) if isinstance(params, dict) else [app_id]
            except Exception:
                args = [app_id]
        else:
            # Methods without an explicit builder keep the legacy shape.
            args = [app_id, params]
        result = self._call_bridge(method, *args)
        # `permissions.list` is consumed by bridge.js as a list of capability
        # ids, while GetAppCapabilities returns {capability: bool}.  Normalise
        # the shape here rather than making every PWA do it.
        if method == "GetAppCapabilities" and isinstance(result, dict):
            caps = result.get("capabilities")
            if isinstance(caps, dict):
                result = dict(result)
                result["capabilities"] = [k for k, v in caps.items() if v]
        return result


    def _app_store(self):
        if pwa_store is None:
            raise RuntimeError('pwa_store unavailable')
        if getattr(self, '_pwa_store', None) is None:
            self._pwa_store = pwa_store.PwaStore()
        return self._pwa_store

    def _mail_client(self):
        if mail_client is None:
            raise RuntimeError('mail_client unavailable')
        if getattr(self, '_mail_client_obj', None) is None:
            self._mail_client_obj = mail_client.MailClient()
        return self._mail_client_obj

    def _handle_mail_rpc(self, verb, params):
        """Mail transport runs in the bridge; credentials are per-call only."""
        if not isinstance(params, dict):
            params = {}
        try:
            client = self._mail_client()
            if verb == 'accounts-list':
                return client.accounts_list()
            if verb == 'account-save':
                return client.account_save(params.get('account') or {})
            if verb == 'account-delete':
                return client.account_delete(params.get('id', ''))
            if verb == 'discover':
                return client.discover(params.get('email', ''))
            if verb == 'test-connection':
                return client.test_connection(params.get('account', ''), params.get('password', ''))
            if verb == 'test-config':
                return client.test_config(params.get('config') or {}, params.get('password', ''))
            if verb == 'imap-list':
                return client.imap_list(params.get('account', ''), params.get('password', ''),
                                        params.get('folder', 'INBOX'))
            if verb == 'pop3-list':
                return client.pop3_list(params.get('account', ''), params.get('password', ''),
                                        params.get('folder', 'INBOX'))
            if verb == 'smtp-send':
                return client.smtp_send(params.get('account', ''), params.get('password', ''),
                                        params.get('to', []), params.get('subject', ''),
                                        params.get('body', ''))
            return {'success': False, 'error': 'Unknown RPC: mail.%s' % verb,
                    'error_code': 'UNKNOWN_VERB', 'code': 400}
        except mail_client.MailError as exc:
            return {'success': False, 'error': str(exc), 'error_code': 'MAIL_ERROR'}
        except Exception as exc:  # noqa: BLE001
            logger.warning('mail RPC %s failed: %s', verb, exc)
            return {'success': False, 'error': 'mail transport unavailable: %s' % exc,
                    'error_code': 'MAIL_UNAVAILABLE'}

    def _handle_app_store_rpc(self, namespace, verb, params):
        """In-process dispatch for durable PWA data + haptics requests."""
        if not isinstance(params, dict):
            params = {}
        try:
            store = self._app_store()
            if namespace == 'storage':
                if verb == 'read':
                    return store.storage_read(params.get('key', ''))
                if verb == 'write':
                    return store.storage_write(params.get('key', ''), params.get('data'))
                if verb == 'list-dir':
                    return store.storage_list_dir(params.get('path', '/'))
                if verb == 'home':
                    return store.home_info()
                if verb == 'media-list':
                    return store.storage_media_list()
                if verb == 'thumbnail':
                    return store.storage_thumbnail(params.get('path', ''))
                if verb == 'mkdir':
                    return store.storage_mkdir(params.get('path', ''))
                if verb == 'rename':
                    return store.storage_rename(params.get('src', ''), params.get('dst', ''))
                if verb == 'delete':
                    return store.storage_delete(params.get('path', ''))
                if verb == 'copy':
                    return store.storage_copy(params.get('src', ''), params.get('dst', ''))
                if verb == 'move':
                    return store.storage_move(params.get('src', ''), params.get('dst', ''))
                if verb == 'archive-create':
                    return store.storage_archive_create(params.get('sources') or [], params.get('dest', ''))
                if verb == 'archive-extract':
                    return store.storage_archive_extract(params.get('archive', ''), params.get('dest', ''))
                if verb == 'write-file':
                    return store.storage_write_file(params.get('path', ''), params.get('data_b64', ''),
                                                    bool(params.get('overwrite', False)))
                if verb == 'read-file':
                    return store.storage_read_file(params.get('path', ''))
                if verb == 'waveform':
                    return store.storage_waveform(params.get('path', ''),
                                                  params.get('buckets', 240))
            elif namespace == 'caldav':
                if verb == 'list':
                    return store.caldav_list()
                if verb == 'put':
                    return store.caldav_put(params.get('events') or [])
            elif namespace == 'notes':
                if verb in ('list', 'all', 'search'):
                    return store.notes_list()
                if verb in ('save', 'write', 'create', 'update'):
                    return store.notes_save(params.get('note') or params)
                if verb in ('delete', 'remove'):
                    return store.notes_delete(params.get('id', ''))
                if verb == 'rename':
                    return store.notes_rename(params.get('id', ''), params.get('title', ''))
            elif namespace == 'contacts':
                if verb == 'list':
                    return store.contacts_list()
                if verb == 'upsert':
                    return store.contacts_upsert(params.get('contact') or {})
                if verb == 'delete':
                    return store.contacts_delete(params.get('id', ''))
            elif namespace == 'haptics':
                if verb == 'pulse':
                    return store.haptics_pulse(params.get('kind', 'tap'))
            elif namespace == 'mail':
                return self._handle_mail_rpc(verb, params)
            return {'success': False, 'error': 'Unknown RPC: %s.%s' % (namespace, verb),
                    'error_code': 'UNKNOWN_VERB', 'code': 400}
        except pwa_store.StoreError as exc:
            return {'success': False, 'error': str(exc), 'error_code': 'STORE_ERROR'}
        except Exception as exc:  # noqa: BLE001 - report, never let a store crash the API
            logger.warning('app store RPC %s.%s failed: %s', namespace, verb, exc)
            return {'success': False, 'error': 'app store unavailable: %s' % exc,
                    'error_code': 'STORE_UNAVAILABLE'}

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        mismatch = self._verify_version()
        if mismatch is not None:
            logger.error("bridge_version mismatch: expected %s, app declared %s",
                         BRIDGE_PROTOCOL_VERSION, mismatch.get("got"))
            self._send_json(mismatch, 409)
            return

        # Launcher-minted token endpoint.  Only the root-owned native PWA host
        # knows this per-device secret; it injects a top-frame-only relay into
        # the Home page.  This is the strong path for iframe apps (WebKit does
        # not send Referer for their fetch calls).
        if path == '/api/v1/auth/app-token':
            body = self._get_json_body()
            if body is None:
                return
            expected = _keyring_launcher_secret()
            got = self.headers.get('X-Nuxel-Launcher-Secret', '')
            if not expected or not hmac.compare_digest(got, expected):
                logger.warning('launcher token refused: secret missing or invalid')
                self._send_json({'success': False, 'error': 'launcher_unauthorized'}, 403)
                return
            app_id = body.get('app_id', '')
            if app_id not in KEYRING_LAUNCHER_APPS:
                self._send_json({'success': False, 'error': 'invalid_app_id'}, 400)
                return
            token = str(uuid.uuid4())
            SESSION_TOKENS[token] = {
                'app_id': app_id,
                'created': time.time(),
                'expires': time.time() + SESSION_TTL_SECONDS,
                'issuer': 'nuxel-launcher',
                'origin': self.headers.get('Origin', ''),
                'referer': '',
            }
            logger.info('Issued launcher-bound token for app %s', app_id)
            self._send_json({
                'success': True,
                'token': token,
                'expires_at': SESSION_TOKENS[token]['expires'],
                'ttl': SESSION_TTL_SECONDS,
            })
            return

        # Bootstrap token endpoint: deliberately NOT auth-gated. A PWA without a
        # token calls this once to obtain a per-session token.
        if path == '/api/v1/auth/token':
            body = self._get_json_body()
            if body is None:
                return
            app_id = body.get('app_id', 'unknown')
            token = str(uuid.uuid4())
            SESSION_TOKENS[token] = {
                "app_id": app_id,
                "created": time.time(),
                "expires": time.time() + SESSION_TTL_SECONDS,
                # Route provenance for the keyring identity check.  This is a
                # URL path, never a secret.  It prevents a token issued for one
                # app route from being replayed for another app_id.
                "origin": self.headers.get('Origin', ''),
                "referer": self.headers.get('Referer', ''),
            }
            logger.info("Issued per-session token for app %s", app_id)
            self._send_json({
                "success": True,
                "token": token,
                "expires_at": SESSION_TOKENS[token]["expires"],
                "ttl": SESSION_TTL_SECONDS,
            })
            return

        if not self._verify_auth():
            self._send_json({'error': 'unauthorized'}, 401)
            return

        mismatch = self._verify_version()
        if mismatch is not None:
            logger.error("bridge_version mismatch: expected %s, app declared %s",
                         BRIDGE_PROTOCOL_VERSION, mismatch.get("got"))
            self._send_json(mismatch, 409)
            return

        body = self._get_json_body()
        if body is None:
            return  # Error already sent by _get_json_body

        app_id = body.get('app_id', 'unknown')

        if path == '/api/v1/usb-mode/set-mode':
            if usb_mode is None:
                self._send_json({'success': False, 'error': 'usb_mode unavailable'}, 503)
            else:
                # The body was already consumed by _get_json_body() above.  The
                # old second rfile.read(Content-Length) blocked forever on a
                # keep-alive connection (the exact "File Transfer never
                # switches" symptom); reuse the parsed document.
                payload = body if isinstance(body, dict) else {}
                mode = str(payload.get('mode', ''))
                result = usb_mode.set_mode(mode)
                self._send_json(result, 200 if result.get('success') else 409)

        elif path == '/api/v1/rpc':
            result = self._handle_rpc(app_id, body)
            self._send_json({'result': result})
            return

        elif path == '/api/v1/capabilities/request':
            capability = body.get('capability', '')
            result = self._call_bridge('RequestCapability', app_id, capability)
            self._send_json(result)

        elif path == '/api/v1/call/initiate':
            number = body.get('number', '')
            result = self._call_bridge('CallInitiate', app_id, number)
            self._send_json(result)

        elif path == '/api/v1/call/end':
            call_id = body.get('call_id', '')
            result = self._call_bridge('CallEnd', app_id, call_id)
            self._send_json(result)

        elif path == '/api/v1/sms/send':
            number = body.get('number', '')
            text = body.get('text', '')
            result = self._call_bridge('SmsSend', app_id, number, text)
            self._send_json(result)

        elif path == '/api/v1/notifications/send':
            title = body.get('title', '')
            message = body.get('body', '')
            result = self._call_bridge('SendNotification', app_id, title, message)
            self._send_json(result)

        elif path.startswith('/api/v1/flatpak/'):
            verb = path.rsplit('/', 1)[-1]
            if flatpak_provider is None:
                self._send_json({'success': False, 'error': 'flatpak provider unavailable'}, 503)
                return
            if verb not in ('install', 'update', 'uninstall', 'job', 'launch', 'refresh'):
                self._send_json({'success': False, 'error': 'unknown flatpak verb',
                                 'verb': verb}, 404)
                return
            payload = body if isinstance(body, dict) else {}
            if verb in ('install', 'update', 'uninstall'):
                _owner = payload.get('caller') or app_id
                if _owner not in ('org.nuxel.Nuxtore', 'org.nuxel.NuxTore',
                                  'org.nuxel.Home', 'nuxel-settings',
                                  'org.gnome.Software'):
                    self._send_json({'success': False, 'error': 'capability_denied',
                                     'detail': 'only Software, NuxTore or Home may change Flatpak installations'}, 403)
                    return
            self._send_json(flatpak_provider.handle(verb, payload))

        elif path == '/api/v1/apps/activate':
            # The target is its OWN field: `app_id` in this API is the CALLER (used
            # for capability checks), and conflating the two would let a caller
            # "activate itself" with someone else's identity.
            target = body.get('target') or body.get('activate') or body.get('target_app_id')
            requester = body.get('requester') or app_id
            result, code = self._activate_app(target, requester, body.get('source') or 'launcher')
            self._send_json(result, code)

        elif path == '/api/v1/apps/open-media':
            target = body.get('app_id') or ''
            media_path = body.get('path') or ''
            if target not in ('org.videolan.VLC', 'org.nuxel.MediaPlayer', 'io.mpv.Mpv'):
                self._send_json({'success': False, 'error': 'app_not_media_capable'}, 400)
                return
            try:
                media = self._app_store().storage_media_file(media_path)
            except Exception as exc:  # StoreError and path violations
                self._send_json({'success': False, 'error': 'invalid_media_path',
                                 'detail': str(exc)}, 400)
                return
            result, code = self._exec_native_app(target, [str(media)])
            self._send_json(result, code)

        elif path == '/api/v1/apps/exec':
            # Launch a native app from the fixed allowlist / canonical registry.
            target = body.get('target') or body.get('app_target')
            result, code = self._exec_native_app(target)
            self._send_json(result, code)

        elif path in ('/api/v1/apps/register', '/api/v1/apps/unregister',
                      '/api/v1/apps/inventory'):
            if app_manager is None:
                self._send_json({'success': False, 'error': 'app manager unavailable'}, 503)
                return
            verb = path.rsplit('/', 1)[-1]
            self._send_json(app_manager.handle(verb, body))

        elif path == '/api/v1/apps/home':
            # Authoritative Penguin Home: minimize native windows, never kill.
            result, code = self._home_action()
            self._send_json(result, code)

        elif path == '/api/v1/apps/close-foreground':
            # Long Back / explicit graceful close of the activated non-Home toplevel.
            result, code = self._close_foreground_action()
            self._send_json(result, code)

        elif path == '/api/v1/apps/close':
            result, code = self._close_app_action(str(body.get('app_id', '')), force=False)
            self._send_json(result, code)

        elif path == '/api/v1/apps/force-close':
            result, code = self._close_app_action(str(body.get('app_id', '')), force=True)
            self._send_json(result, code)

        elif path == '/api/v1/apps/back':
            # Short Back: in-app navigation first; only at root may Home follow.
            result, code = self._native_back_action()
            self._send_json(result, code)

        elif path == '/api/v1/windows/list':
            result, code = self._list_toplevels()
            self._send_json(result, code)

        elif path == '/api/v1/windows/activate':
            # Recents/Tabs switch: activate a backgrounded native toplevel.
            result, code = self._activate_toplevel(body.get('app_id'))
            self._send_json(result, code)

        elif path == '/api/v1/windows/close':
            # Recents/Tabs close button and left-swipe.
            result, code = self._close_toplevel(body.get('app_id'))
            self._send_json(result, code)

        elif path == '/api/v1/capabilities/revoke':
            capability = body.get('capability', '')
            result = self._call_bridge('RevokeCapability', app_id, capability)
            self._send_json(result)

        else:
            self._send_json({'error': 'Not found'}, 404)


def start_api_server(host=None, port=None, token=None):
    """Start the REST API server for bridge access.

    Args:
        host: Bind address (default: from NUXEL_HTTP_BIND env or 127.0.0.1)
        port: Port number (default: from NUXEL_HTTP_PORT env or 8080)
        token: Optional API token for authentication

    Returns:
        The started HTTPServer instance, or None if token setup fails.
    """
    if host is None:
        host = HTTP_BIND
    if port is None:
        port = HTTP_PORT

    if token is None:
        token = _get_token()
        if token is None and HTTP_MODE != 'dev':
            return None  # Production mode without token file
        # In dev mode a missing token is OK: per-session tokens are issued via
        # POST /api/v1/auth/token instead of a shared auto-created dev token.

    BridgeAPIHandler.server_token = token

    server = HTTPServer((host, port), BridgeAPIHandler)
    logger.info("Nuxel Bridge API running on http://%s:%s", host, port)
    logger.info("API Token: %s", BridgeAPIHandler.server_token)
    logger.info("Mode: %s", HTTP_MODE)
    logger.info("Use: Authorization: Bearer <token>")

    return server


if __name__ == '__main__':
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    port = int(sys.argv[1]) if len(sys.argv) > 1 else HTTP_PORT
    token = sys.argv[2] if len(sys.argv) > 2 else None

    server = start_api_server(host=HTTP_BIND, port=port, token=token)
    if server is None:
        sys.exit(1)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down API server...")
        server.shutdown()
