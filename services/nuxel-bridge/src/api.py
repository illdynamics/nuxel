#!/usr/bin/env python3
"""
Nuxel Bridge - REST API Compatibility Layer

Provides a simple HTTP interface for PWAs that cannot directly use D-Bus.
This wraps the D-Bus calls in a local HTTP server accessible only from localhost.

SECURITY: This API MUST only listen on 127.0.0.1 and MUST validate all requests
against an API key or session token. It is a convenience layer for development
and testing; production PWAs should use D-Bus directly via xdg-desktop-portal.
"""

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

logger = logging.getLogger('nuxel-http-bridge')

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
    logger.warning('tri_link_status unavailable: %s', _e)

# USB connection-mode state machine (Charging / File Transfer). It only
# activates a real endpoint through the dedicated helper and reports the result.
try:
    import usb_mode
except Exception as _e:  # pragma: no cover - optional module
    usb_mode = None
    logger.warning('usb_mode unavailable: %s', _e)

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
BRIDGE_HOST_VERSION = os.environ.get('NUXEL_BRIDGE_VERSION', '0.7.2-beta')

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

TOKEN_DIR = os.path.join(NUXEL_DATA_DIR, 'http-bridge')
TOKEN_FILE = os.path.join(TOKEN_DIR, 'token')

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
        declared = doc.get("bridge_version")
        if declared and declared != BRIDGE_PROTOCOL_VERSION:
            info["version_mismatch"] = {"registry": declared, "host": BRIDGE_PROTOCOL_VERSION}
        return info

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
        "GSK_RENDERER": "cairo",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "WEBKIT_DISABLE_COMPOSITING_MODE": "1",
        "GDK_BACKEND": "wayland",
        # The graphical session units run with a minimal PATH lacking /usr/sbin,
        # where Fedora installs python3/gtk-launch. A `#!/usr/bin/env python3`
        # shebang fails under that PATH, so restore the standard search path.
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": "/root",
    }

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
        "org.mozilla.firefox": ["/usr/lib/nuxel/nuxel-flatpak-firefox"],
        "org.videolan.VLC": ["/usr/lib/nuxel/nuxel-flatpak-vlc"],
        "org.signal.Signal": ["/usr/lib/nuxel/nuxel-flatpak-signal"],
        "com.stremio.Stremio": ["/usr/lib/nuxel/nuxel-flatpak-stremio"],
        "org.gnome.FileRoller": ["/usr/bin/file-roller"],
        "org.gnome.Loupe": ["/usr/bin/loupe"],
        "org.gnome.Papers": ["/usr/bin/papers"],
        "org.gnome.SystemMonitor": ["/usr/bin/gnome-system-monitor"],
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
        "org.signal.Signal", "com.stremio.Stremio",
        "org.gnome.FileRoller", "org.gnome.Loupe",
        "org.gnome.Papers", "org.gnome.SystemMonitor",
    }

    def _session_home(self):
        try:
            store = self._app_store()
            return str(store.files_root)
        except Exception:
            return "/home/nuxel"

    def _exec_native_app(self, target_id):
        """Launch a native app from the fixed allowlist (never a client path)."""
        if not isinstance(target_id, str) or not APP_ID_RE.match(target_id):
            return ({"success": False, "error": "invalid_app_id",
                     "detail": "an app id is an identifier, never a path or a command"}, 400)
        argv = self.NATIVE_LAUNCH.get(target_id)
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
        as_user = target_id in self.NATIVE_AS_SESSION_USER
        runtime = "/run/user/1000" if as_user else "/run/nuxel-wayland"
        cmd = ["/usr/bin/systemd-run", "--unit=%s" % unit, "--collect",
               "--setenv=XDG_RUNTIME_DIR=%s" % runtime,
               "--setenv=WAYLAND_DISPLAY=wayland-0",
               "--setenv=GSK_RENDERER=cairo",
               "--setenv=LIBGL_ALWAYS_SOFTWARE=1",
               "--setenv=WEBKIT_DISABLE_COMPOSITING_MODE=1",
               "--setenv=GDK_BACKEND=wayland",
               "--setenv=QT_QPA_PLATFORM=wayland",
               "--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/nuxel-wayland/bus",
               "--setenv=PULSE_SERVER=unix:/run/nuxel-wayland/pulse/native",
               "--setenv=PIPEWIRE_RUNTIME_DIR=/run/nuxel-wayland",
               "--setenv=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
               "--setenv=HOME=%s" % home,
               "--setenv=XDG_DATA_HOME=%s/.local/share" % home]
        if as_user:
            user = self._app_store().session_user
            if user:
                cmd += ["--uid=%s" % user, "--gid=%s" % user,
                        "--property=SupplementaryGroups=audio"]
        cmd += argv
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
        # The Home surface is a fullscreen toplevel.  A newly launched native
        # app maps behind it unless we (a) leave Home fullscreen/minimize it and
        # (b) maximize the app.  Do that asynchronously once the toplevel exists;
        # the layer-shell top bar and nav dock then remain visible over it.
        try:
            subprocess.Popen(
                ["/usr/lib/nuxel/nuxel-focus-app.sh", target_id],
                env=dict(os.environ, XDG_RUNTIME_DIR="/run/nuxel-wayland",
                         WAYLAND_DISPLAY="wayland-0"),
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            logger.warning("native focus helper failed for %s: %s", target_id, exc)
        logger.info("native app launched id=%s unit=%s argv=%s", target_id, unit, argv)
        return ({"success": True, "launched": True, "app_id": target_id,
                 "unit": unit, "action": "exec", "argv": argv}, 200)

    def _home_action(self):
        """Minimize every non-Home toplevel via wlr-foreign-toplevel (no kill)."""
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
        return ({"success": True, "action": "home", "rc": proc.returncode,
                 "output": out.strip()}, 200)

    def _close_foreground_action(self):
        """Close the activated non-Home toplevel (long Back). Never closes Home
        or the launcher host, and the fixed argv is resolved here (no client
        path). Uses the compositor's foreign-toplevel `close`, not a kill."""
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
        logger.info("close-foreground action rc=%s out=%s", proc.returncode, out.strip())
        return ({"success": True, "action": "close-foreground", "rc": proc.returncode,
                 "output": out.strip()}, 200)

    def _native_back_action(self):
        """Short Back for the foreground native app: navigate the app's own
        history first, and only report at-root when it has no more back step.

        The compositor's foreign-toplevel manager reports the activated
        non-Home toplevel.  Only the native browser owns an in-app history the
        shell can drive (via its control FIFO); any other native app reports
        at-root so the launcher's short Back falls through to Home."""
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

    def _activate_toplevel(self, app_id):
        """Activate a specific native toplevel by app_id (recents switch)."""
        if not app_id or not re.match(r"^[A-Za-z0-9._-]+$", app_id):
            return ({"success": False, "error": "invalid_app_id"}, 400)
        env = dict(os.environ)
        env.update({"XDG_RUNTIME_DIR": "/run/nuxel-wayland",
                    "WAYLAND_DISPLAY": "wayland-0"})
        try:
            proc = subprocess.run(["/usr/lib/nuxel/nuxel-foreign-toplevel", "activate", app_id],
                                  env=env, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("activate action failed: %s", exc)
            return ({"success": False, "error": "activate_failed",
                     "detail": str(exc)}, 500)
        out = (proc.stdout or b"").decode("utf-8", "replace")
        return ({"success": True, "action": "activate", "app_id": app_id,
                 "rc": proc.returncode, "output": out.strip()}, 200)

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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Nuxel-Bridge-Version')
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

        elif path == '/api/v1/apps/registry':
            self._send_json(self._load_app_registry())

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

        elif path == '/api/v1/system/indicators':
            # Lockhead status indicators.  These read real kernel state
            # directly (power_supply, configfs/UDC, android_usb, and the
            # console process's tty fd) so a charging-only cable can never
            # light the PC indicator and root access can never light the
            # live-console indicator.
            if system_indicators is not None:
                try:
                    self._send_json(system_indicators.get_indicators())
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

    def _handle_rpc(self, app_id, body):
        """Dispatch a generic bridge RPC (namespace/verb/params)."""
        namespace = body.get('namespace', '')
        verb = body.get('verb', '')
        params = body.get('params', {}) or {}
        # PWA persistence is served in-process from the root-owned store.  The
        # sandboxed D-Bus bridge has no storage/caldav/contacts implementation,
        # and routing these verbs to it made every calendar/notes/files save
        # fail with a dbus-error.  Handle them here with the same honest error
        # shape instead.
        if namespace in ('storage', 'caldav', 'contacts', 'haptics', 'mail'):
            return self._handle_app_store_rpc(namespace, verb, params)
        # Lockhead indicators are computed in-process from kernel state; they
        # are deliberately NOT routed to D-Bus (the D-Bus bridge has no such
        # method and a dbus-error fallback would make the UI dim real states).
        if namespace == 'system' and verb == 'indicators':
            if system_indicators is not None:
                try:
                    return system_indicators.get_indicators()
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
        # Privileged hardware control.  These verbs are handled in this root
        # process (never forwarded to the sandboxed D-Bus bridge) because they
        # read /dev/snd or write /sys/class/rfkill.
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
                return self._audio_provider.test_audio(
                    asset=params.get('asset', '/usr/share/nuxel/assets/nuxel-pow.mp3') if isinstance(params, dict) else '/usr/share/nuxel/assets/nuxel-pow.mp3',
                    gain_percent=params.get('gain_percent', 50) if isinstance(params, dict) else 50)
        if namespace == 'display' and verb == 'status':
            if hw_providers is None:
                return {'success': False, 'error': 'display provider unavailable'}
            return hw_providers.DisplayProvider().get_status()
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
                return gnss.power_rail(enabled=bool(params.get('enabled', True)),
                                       timeout=params.get('timeout', 5.0))
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
            elif namespace == 'caldav':
                if verb == 'list':
                    return store.caldav_list()
                if verb == 'put':
                    return store.caldav_put(params.get('events') or [])
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

        elif path == '/api/v1/apps/activate':
            # The target is its OWN field: `app_id` in this API is the CALLER (used
            # for capability checks), and conflating the two would let a caller
            # "activate itself" with someone else's identity.
            target = body.get('target') or body.get('activate') or body.get('target_app_id')
            requester = body.get('requester') or app_id
            result, code = self._activate_app(target, requester, body.get('source') or 'launcher')
            self._send_json(result, code)

        elif path == '/api/v1/apps/exec':
            # Launch a native app from the fixed allowlist / canonical registry.
            target = body.get('target') or body.get('app_target')
            result, code = self._exec_native_app(target)
            self._send_json(result, code)

        elif path == '/api/v1/apps/home':
            # Authoritative Penguin Home: minimize native windows, never kill.
            result, code = self._home_action()
            self._send_json(result, code)

        elif path == '/api/v1/apps/close-foreground':
            # Long Back: close the activated non-Home toplevel, never kill.
            result, code = self._close_foreground_action()
            self._send_json(result, code)

        elif path == '/api/v1/apps/back':
            # Short Back: in-app navigation first; only at root may Home follow.
            result, code = self._native_back_action()
            self._send_json(result, code)

        elif path == '/api/v1/windows/activate':
            # Recents/Tabs switch: activate a backgrounded native toplevel.
            result, code = self._activate_toplevel(body.get('app_id'))
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
