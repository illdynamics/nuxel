#!/usr/bin/env python3
"""Nuxel Secret Service provider (freedesktop.org Secret Service).

This module is the ONLY place in Nuxel that talks to ``org.freedesktop.secrets``.
It deliberately implements a narrow, typed surface for two consumers:

    org.nuxel.Vault          -> the Nuxel-owned vault collection items
    org.nuxel.Authenticator  -> exactly one named unlock credential

It never enumerates or returns unrelated application secrets.  D-Bus secrets are
kept in local variables for as short a time as possible and are never logged.

Provider
--------
GNOME Keyring (``gnome-keyring-daemon``) on the root-owned Nuxel Wayland session
bus.  The S10+ image runs the graphical session, PWA host and HTTP bridge as
root, so the user session bus is ``unix:path=/run/nuxel-wayland/bus`` and the
keyring lives under ``/root/.local/share/keyrings``.  This is documented in the
threat model: root compromise is total compromise on this image until the
session is de-privileged.

Unlock model
------------
gcr-prompter (the stock Secret Service prompt) is activated by GNOME Keyring but
does not map a window on Phoc in this image.  We therefore use the provider's
own PAM-compatible login/unlock path: the native Vault UI collects the master
password and the bridge pipes it to ``gnome-keyring-daemon --login --daemonize``
on stdin (never argv, never an environment variable, never a file).  That is the
same supported path pam_gnome_keyring uses.  Both the old daemon and the new one
belong to the current user session; only the current bus owner is replaced.

A locked collection is intentionally NOT discoverable through
``ReadAlias('default')`` after a daemon restart.  ``status()`` therefore reports
``locked`` when a keyring file exists but no default collection is exported.
That is metadata only -- this module never opens, parses or edits a keyring file.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import signal
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

try:  # dbus-python is part of the S10+ image (python3-dbus)
    import dbus
    HAVE_DBUS = True
except Exception:  # pragma: no cover - exercised by the unavailable-provider test
    dbus = None
    HAVE_DBUS = False

LOG = logging.getLogger("nuxel-keyring")

SERVICE = "org.freedesktop.secrets"
SERVICE_PATH = "/org/freedesktop/secrets"
SECRETS_BUS = os.environ.get("NUXEL_SECRETS_BUS", "unix:path=/run/nuxel-wayland/bus")

VAULT_APP = "org.nuxel.Vault"
AUTH_APP = "org.nuxel.Authenticator"

VAULT_SCHEMA = "nuxel-vault-item-v1"
VAULT_META_SCHEMA = "nuxel-vault-meta-v1"
AUTH_SCHEMA = "nuxel-auth-credential-v1"
AUTH_PURPOSE = "vault-unlock-credential"

MAX_VALUE_BYTES = 128 * 1024
MAX_ITEMS_PER_SCOPE = 2000
MAX_TAGS = 24
MAX_TAG_LEN = 48
MAX_TITLE = 200
MAX_URL = 2048
MAX_USERNAME = 320
MAX_PASSWORD = 4096
MAX_NOTES = 16384
MAX_PAYLOAD_BYTES = 96 * 1024

BOUNDED_PROMPT_SECONDS = 20.0
BOUNDED_UNLOCK_SECONDS = 25.0
BOUNDED_START_SECONDS = 12.0


class SecretServiceError(Exception):
    """Structured, non-secret error for the keyring API layer."""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def _text(value: Any, limit: int, field: str, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise SecretServiceError("invalid_request", field + " must be a string")
    value = value.strip() if field != "password" and field != "notes" else value
    if required and not value:
        raise SecretServiceError("invalid_request", field + " is required")
    if len(value) > limit:
        raise SecretServiceError("invalid_request", field + " is too long")
    return value


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def validate_vault_payload(raw: Any) -> Dict[str, Any]:
    """Validate and normalise a Nuxel Vault item.  Unknown fields are refused."""
    if not isinstance(raw, dict):
        raise SecretServiceError("invalid_request", "item must be an object")
    allowed = {"schema", "type", "title", "url", "username", "password", "notes",
               "tags", "favorite", "created_at", "updated_at", "id"}
    extra = set(raw) - allowed
    if extra:
        raise SecretServiceError("invalid_request", "unknown item fields")
    schema = raw.get("schema", VAULT_SCHEMA)
    if schema != VAULT_SCHEMA:
        raise SecretServiceError("invalid_request", "unsupported item schema")
    kind = raw.get("type")
    if kind not in ("login", "note"):
        raise SecretServiceError("invalid_request", "type must be login or note")
    tags = raw.get("tags", [])
    if not isinstance(tags, list) or len(tags) > MAX_TAGS:
        raise SecretServiceError("invalid_request", "tags must be a bounded list")
    clean_tags = []
    for tag in tags:
        t = _text(tag, MAX_TAG_LEN, "tag")
        if t and t not in clean_tags:
            clean_tags.append(t)
    favorite = raw.get("favorite", False)
    if not isinstance(favorite, bool):
        raise SecretServiceError("invalid_request", "favorite must be boolean")
    created = _text(raw.get("created_at") or _iso_now(), 40, "created_at")
    updated = _text(raw.get("updated_at") or _iso_now(), 40, "updated_at")
    item = {
        "schema": VAULT_SCHEMA,
        "type": kind,
        "title": _text(raw.get("title"), MAX_TITLE, "title", required=True),
        "url": _text(raw.get("url"), MAX_URL, "url"),
        "username": _text(raw.get("username"), MAX_USERNAME, "username"),
        "password": _text(raw.get("password"), MAX_PASSWORD, "password"),
        "notes": _text(raw.get("notes"), MAX_NOTES, "notes"),
        "tags": clean_tags,
        "favorite": favorite,
        "created_at": created,
        "updated_at": updated,
    }
    encoded = json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise SecretServiceError("invalid_request", "item payload is too large")
    return item


def validate_auth_credential(raw: Any) -> str:
    if not isinstance(raw, str):
        raise SecretServiceError("invalid_request", "credential must be a string")
    if len(raw) < 8 or len(raw) > 1024:
        raise SecretServiceError("invalid_request", "credential length is invalid")
    return raw


class SecretService:
    """Narrow Secret Service client.  One instance per bridge process."""

    def __init__(self, bus_address: Optional[str] = None, home: Optional[str] = None,
                 runtime_dir: Optional[str] = None, dbus_module=None):
        self.bus_address = bus_address or SECRETS_BUS
        self.home = home or os.environ.get("HOME") or "/root"
        self.runtime_dir = runtime_dir or os.environ.get("XDG_RUNTIME_DIR") or "/run/nuxel-wayland"
        self._dbus = dbus_module if dbus_module is not None else dbus
        self._bus = None
        self._lock = threading.RLock()
        self._session_path: Optional[str] = None

    # ------------------------------------------------------------------ bus

    def _connect(self):
        if not HAVE_DBUS and self._dbus is None:
            raise SecretServiceError("provider_unavailable", "python3-dbus is not installed")
        if self._bus is not None:
            return self._bus
        try:
            # Explicit address: the HTTP bridge runs as a system service and
            # only this environment variable points it at the Wayland session
            # bus.  The system bus must never be used for secrets.
            self._bus = self._dbus.bus.BusConnection(self.bus_address)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("keyring bus unavailable: %s", type(exc).__name__)
            raise SecretServiceError("provider_unavailable", "session D-Bus is not reachable")
        return self._bus

    def _service(self):
        bus = self._connect()
        try:
            obj = bus.get_object(SERVICE, SERVICE_PATH, introspect=False)
            return bus, dbus.Interface(obj, "org.freedesktop.Secret.Service"), \
                dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Secret Service unavailable: %s", type(exc).__name__)
            raise SecretServiceError("provider_unavailable", "org.freedesktop.secrets is not owned")

    def _call(self, fn, *args, timeout: float = 18.0, **kwargs):
        # dbus-python's blocking calls carry their own timeout.  Never let the
        # HTTP thread hang forever on a crashed/absent provider.
        try:
            return fn(*args, timeout=timeout, **kwargs)
        except SecretServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            name = type(exc).__name__
            text = str(exc)[:200]
            if "NoReply" in name or "Timeout" in name or "timeout" in text.lower():
                raise SecretServiceError("timeout", "Secret Service did not answer in time")
            if "IsLocked" in text or "locked" in text.lower():
                raise SecretServiceError("collection_locked", "the keyring collection is locked")
            if "UnknownMethod" in text or "UnknownObject" in text:
                raise SecretServiceError("provider_unavailable", "Secret Service object is unavailable")
            LOG.warning("Secret Service call failed: %s", name)
            raise SecretServiceError("provider_error", "Secret Service call failed")

    def _dispatch_for(self, seconds: float) -> None:
        bus = self._connect()
        end = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end:
            try:
                bus.read_write_dispatch(0.05)
            except Exception:  # noqa: BLE001
                time.sleep(0.05)

    def _await_prompt(self, prompt_path, timeout: float = BOUNDED_PROMPT_SECONDS) -> Any:
        """Invoke a real Secret Service Prompt and wait, bounded, for completion."""
        if prompt_path is None or str(prompt_path) == "/":
            return None
        bus, _svc, _props = self._service()
        state = {"done": False, "dismissed": True, "result": None}

        def on_completed(dismissed, result):
            state["done"] = True
            state["dismissed"] = bool(dismissed)
            state["result"] = result

        bus.add_signal_receiver(
            on_completed, signal_name="Completed",
            dbus_interface="org.freedesktop.Secret.Prompt", path=str(prompt_path))
        pobj = bus.get_object(SERVICE, str(prompt_path), introspect=False)
        piface = dbus.Interface(pobj, "org.freedesktop.Secret.Prompt")
        try:
            piface.Prompt("", timeout=5)
        except Exception:  # noqa: BLE001
            raise SecretServiceError("provider_error", "keyring prompt could not be opened")
        end = time.monotonic() + timeout
        while time.monotonic() < end and not state["done"]:
            self._dispatch_for(0.1)
        if not state["done"]:
            try:
                piface.Dismiss(timeout=2)
            except Exception:  # noqa: BLE001
                pass
            raise SecretServiceError("timeout", "keyring prompt did not complete")
        if state["dismissed"]:
            raise SecretServiceError("user_cancelled", "keyring prompt was cancelled")
        return state["result"]

    # ------------------------------------------------------------- lifecycle

    def _keyring_file(self) -> str:
        return os.path.join(self.home, ".local", "share", "keyrings", "login.keyring")

    def _keyring_exists(self) -> bool:
        try:
            return os.path.isfile(self._keyring_file())
        except OSError:
            return False

    def _name_owner_pid(self) -> Optional[int]:
        bus = self._connect()
        try:
            dbus_iface = dbus.Interface(
                bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus", introspect=False),
                "org.freedesktop.DBus")
            owner = dbus_iface.GetNameOwner(SERVICE, timeout=3)
            return int(dbus_iface.GetConnectionUnixProcessID(owner, timeout=3))
        except Exception:  # noqa: BLE001
            return None

    def _safe_stop_owner(self, pid: Optional[int]) -> bool:
        """Stop only a gnome-keyring-daemon running as this image's root session."""
        self._session_path = None       # a stopped daemon invalidates every session
        if not pid:
            return False
        try:
            if os.stat("/proc/%d" % pid).st_uid != 0:
                return False
            exe = os.readlink("/proc/%d/exe" % pid)
            if not exe.endswith("gnome-keyring-daemon"):
                return False
            with open("/proc/%d/environ" % pid, "rb") as fh:
                env = fh.read().split(b"\0")
            env_text = b"\n".join(env).decode("utf-8", "replace")
            if ("XDG_RUNTIME_DIR=" + self.runtime_dir) not in env_text:
                return False
            os.kill(pid, signal.SIGTERM)
        except (OSError, ValueError):
            return False
        end = time.monotonic() + 6.0
        while time.monotonic() < end:
            if self._name_owner_pid() is None:
                return True
            time.sleep(0.1)
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        time.sleep(0.4)
        return self._name_owner_pid() is None

    def _cleanup_orphans(self, keep_pid: Optional[int] = None) -> None:
        """Remove stale gnome-keyring processes from this exact session home.

        Only processes whose /proc environ matches our HOME and runtime dir are
        touched.  This prevents the duplicate-daemon leak observed while
        validating the PAM unlock path.
        """
        me = os.getpid()
        try:
            names = os.listdir("/proc")
        except OSError:
            return
        for name in names:
            if not name.isdigit():
                continue
            pid = int(name)
            if pid == me or pid == keep_pid:
                continue
            try:
                if os.stat("/proc/%d" % pid).st_uid != 0:
                    continue
                exe = os.readlink("/proc/%d/exe" % pid)
                if not exe.endswith("gnome-keyring-daemon"):
                    continue
                with open("/proc/%d/environ" % pid, "rb") as fh:
                    env_text = b"\n".join(fh.read().split(b"\0")).decode("utf-8", "replace")
                if ("HOME=" + self.home) not in env_text:
                    continue
                if ("XDG_RUNTIME_DIR=" + self.runtime_dir) not in env_text:
                    continue
                # Keep the live bus owner; everything else with our identity is
                # a stale login/unlock process from an earlier attempt.
                if pid == self._name_owner_pid():
                    continue
                os.kill(pid, signal.SIGTERM)
            except (OSError, ValueError):
                continue

    def _run_daemon(self, args: List[str], password: Optional[str] = None,
                    timeout: float = BOUNDED_UNLOCK_SECONDS):
        env = dict(os.environ)
        env.update({
            "HOME": self.home,
            "XDG_RUNTIME_DIR": self.runtime_dir,
            "DBUS_SESSION_BUS_ADDRESS": self.bus_address,
            "GDK_BACKEND": "wayland",
            "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", "wayland-0"),
        })
        data = None
        if password is not None:
            # Only stdin.  Never argv, never the environment, never a temp file.
            data = (password + "\n").encode("utf-8")
        try:
            proc = subprocess.run(
                ["/usr/bin/gnome-keyring-daemon"] + args,
                input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout, env=env, close_fds=True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SecretServiceError("provider_unavailable",
                                     "gnome-keyring-daemon could not be started")
        finally:
            data = None
        return proc

    def _activate_daemon(self) -> None:
        """Make sure a daemon owns the bus name, without prompt interaction."""
        if not HAVE_DBUS and self._dbus is None:
            raise SecretServiceError("provider_unavailable", "python3-dbus is not installed")
        try:
            self._service()
            return
        except SecretServiceError:
            pass
        # A normal --start daemon exposes locked collections as 'not exported'
        # but owns the bus, which is enough for status/diagnostics.
        # D-Bus activation (the shipped org.freedesktop.secrets.service) is the
        # supported path.  Touch the service name and wait for the owner.
        end = time.monotonic() + BOUNDED_START_SECONDS
        last = None
        while time.monotonic() < end:
            try:
                _bus, svc, _props = self._service()
                svc.ReadAlias("default", timeout=3)
                return
            except SecretServiceError as exc:
                last = exc
                time.sleep(0.2)
        raise last or SecretServiceError("provider_unavailable", "Secret Service did not activate")

    def _unlock_via_login(self, password: str) -> None:
        """PAM-compatible unlock: replace the current daemon with --login."""
        if not isinstance(password, str) or not password:
            raise SecretServiceError("invalid_request", "master password is required")
        if len(password) > 1024:
            raise SecretServiceError("invalid_request", "master password is too long")
        with self._lock:
            self._connect()
            self._session_path = None   # the daemon replacement invalidates it
            owner = self._name_owner_pid()
            if owner:
                if not self._safe_stop_owner(owner):
                    raise SecretServiceError("provider_error",
                                             "the running keyring daemon could not be stopped safely")
            self._cleanup_orphans()
            proc = self._run_daemon(["--login", "--daemonize", "--components=secrets"],
                                    password=password)
            password = None  # release the reference as soon as the pipe closes
            if proc.returncode != 0:
                raise SecretServiceError("provider_error", "keyring login daemon failed")
            # --login creates the keyring and unlocks it; --start connects that
            # daemon to the session bus and exits.
            self._run_daemon(["--start", "--components=secrets"], timeout=BOUNDED_START_SECONDS)
            end = time.monotonic() + BOUNDED_START_SECONDS
            while time.monotonic() < end:
                try:
                    _bus, svc, _props = self._service()
                    default = svc.ReadAlias("default", timeout=4)
                    if str(default) != "/":
                        state = self._collection_state(str(default))
                        if state.get("locked") is False:
                            return
                except SecretServiceError:
                    pass
                time.sleep(0.25)
            # Wrong password: the keyring is intact and still locked.  Stop the
            # daemon we just started so a retry starts from a clean state.
            self._safe_stop_owner(self._name_owner_pid())
            self._cleanup_orphans()
            raise SecretServiceError("invalid_credentials",
                                     "the master password did not unlock the keyring")

    def _collection_state(self, path: str) -> Dict[str, Any]:
        bus = self._connect()
        try:
            cobj = bus.get_object(SERVICE, path, introspect=False)
            props = dbus.Interface(cobj, "org.freedesktop.DBus.Properties")
            values = props.GetAll("org.freedesktop.Secret.Collection", timeout=5)
            items = values.get("Items") or []
            return {
                "path": path,
                "label": str(values.get("Label", "")),
                "locked": bool(values.get("Locked", True)),
                "item_count": len(items),
                "created": int(values.get("Created", 0) or 0),
                "modified": int(values.get("Modified", 0) or 0),
            }
        except Exception as exc:  # noqa: BLE001
            raise SecretServiceError("provider_error", "collection properties unavailable")

    # ---------------------------------------------------------------- status

    def status(self) -> Dict[str, Any]:
        with self._lock:
            try:
                self._activate_daemon()
                _bus, svc, _props = self._service()
                default = str(svc.ReadAlias("default", timeout=5))
                exists = self._keyring_exists()
                if default == "/":
                    return {
                        "success": True,
                        "provider": "gnome-keyring",
                        "available": True,
                        "collection": None,
                        "locked": bool(exists),
                        "initialized": bool(exists),
                        "keyring_present": bool(exists),
                        "state": "collection_locked" if exists else "not_initialized",
                    }
                col = self._collection_state(default)
                return {
                    "success": True,
                    "provider": "gnome-keyring",
                    "available": True,
                    "collection": col,
                    "locked": col["locked"],
                    "initialized": True,
                    "keyring_present": True,
                    "state": "unlocked" if not col["locked"] else "collection_locked",
                }
            except SecretServiceError as exc:
                if exc.code == "provider_unavailable":
                    return {"success": False, "available": False, "provider": "gnome-keyring",
                            "state": "unavailable", "error": exc.code,
                            "detail": exc.message}
                raise

    def initialize(self, password: str, label: str = "Nuxel Vault") -> Dict[str, Any]:
        with self._lock:
            had_keyring = self._keyring_exists()
            self._unlock_via_login(password)
            _bus, svc, _props = self._service()
            default = str(svc.ReadAlias("default", timeout=5))
            if default == "/":
                raise SecretServiceError("provider_error", "no default collection after initialization")
            if not had_keyring:
                # Fresh Nuxel-owned keyring: name it explicitly.  If a login
                # keyring already existed we leave its label alone rather than
                # renaming another application's collection.
                try:
                    cobj = self._connect().get_object(SERVICE, default, introspect=False)
                    props = dbus.Interface(cobj, "org.freedesktop.DBus.Properties")
                    props.Set("org.freedesktop.Secret.Collection", "Label",
                              dbus.String(label, variant_level=1), timeout=5)
                    LOG.info("keyring collection label set")
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("keyring collection label could not be set: %s", str(exc)[:160])
            meta = self._find_one(VAULT_APP, VAULT_META_SCHEMA, "meta")
            if meta is None:
                self._create_secret(
                    VAULT_APP, VAULT_META_SCHEMA, "meta",
                    json.dumps({"schema": VAULT_META_SCHEMA, "version": 1,
                                "initialized_at": _iso_now()},
                               separators=(",", ":")).encode("utf-8"))
            return self.status()

    def unlock(self, password: str) -> Dict[str, Any]:
        with self._lock:
            try:
                st = self.status()
                if st.get("state") == "unlocked":
                    return st
            except SecretServiceError as exc:
                if exc.code != "provider_unavailable":
                    raise
            self._unlock_via_login(password)
            return self.status()

    def lock(self) -> Dict[str, Any]:
        with self._lock:
            _bus, svc, _props = self._service()
            try:
                default = str(svc.ReadAlias("default", timeout=4))
            except SecretServiceError:
                default = "/"
            if default == "/":
                # Nothing is exported: either already locked or not initialized.
                return {"success": True, "locked": True, "state": "collection_locked"}
            _locked, prompt = svc.Lock([dbus.ObjectPath(default)], timeout=8)
            self._await_prompt(prompt, timeout=8)
            return {"success": True, "locked": True, "state": "collection_locked"}

    # -------------------------------------------------------------- sessions

    def _ensure_session(self) -> str:
        if self._session_path:
            return self._session_path
        _bus, svc, _props = self._service()
        out, path = svc.OpenSession("plain", dbus.String("", variant_level=1), timeout=5)
        self._session_path = str(path)
        return self._session_path

    def _secret_struct(self, value: bytes):
        return dbus.Struct((dbus.ObjectPath(self._ensure_session()),
                            dbus.ByteArray(b""), dbus.ByteArray(value),
                            "text/plain"), signature="oayays")

    def _read_secret(self, item_path: str) -> bytes:
        bus = self._connect()
        try:
            obj = bus.get_object(SERVICE, item_path, introspect=False)
            iface = dbus.Interface(obj, "org.freedesktop.Secret.Item")
            try:
                struct = iface.GetSecret(dbus.ObjectPath(self._ensure_session()), timeout=8)
            except Exception as exc:  # noqa: BLE001
                if "NoSession" not in str(exc):
                    raise
                # The daemon was replaced (lock/unlock) after the session was
                # opened.  Re-open exactly one fresh session and retry.
                self._session_path = None
                struct = iface.GetSecret(dbus.ObjectPath(self._ensure_session()), timeout=8)
            value = bytes(struct[2])
        except Exception as exc:  # noqa: BLE001
            text = str(exc)
            if "IsLocked" in text or "locked" in text.lower():
                raise SecretServiceError("collection_locked", "the keyring collection is locked")
            raise SecretServiceError("item_not_found", "keyring item is not readable")
        if len(value) > MAX_VALUE_BYTES:
            raise SecretServiceError("invalid_request", "keyring item is too large")
        return value

    def _find_one(self, app: str, schema: str, item_id: Optional[str]) -> Optional[str]:
        attrs = {"application": app, "schema": schema}
        if item_id is not None:
            attrs["item_id"] = item_id
        _bus, svc, _props = self._service()
        try:
            unlocked, locked = svc.SearchItems(dbus.Dictionary(attrs, signature="ss"), timeout=8)
        except SecretServiceError:
            raise
        except Exception:  # noqa: BLE001
            raise SecretServiceError("provider_error", "keyring search failed")
        if unlocked:
            return str(unlocked[0])
        if locked:
            raise SecretServiceError("collection_locked", "the keyring collection is locked")
        return None

    def _create_secret(self, app: str, schema: str, item_id: str, value: bytes,
                       replace: bool = False) -> str:
        attrs = {"application": app, "schema": schema, "item_id": item_id}
        props = {
            "org.freedesktop.Secret.Item.Label": dbus.String("Nuxel item"),
            "org.freedesktop.Secret.Item.Attributes": dbus.Dictionary(attrs, signature="ss"),
        }
        _bus, svc, _props = self._service()
        default = str(svc.ReadAlias("default", timeout=5))
        if default == "/":
            raise SecretServiceError("collection_locked", "the keyring collection is locked")
        try:
            cobj = self._connect().get_object(SERVICE, default, introspect=False)
            ciface = dbus.Interface(cobj, "org.freedesktop.Secret.Collection")
            item, prompt = ciface.CreateItem(
                dbus.Dictionary(props, signature="sv"),
                self._secret_struct(value), bool(replace), timeout=12)
        except SecretServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            if "IsLocked" in str(exc) or "locked" in str(exc).lower():
                raise SecretServiceError("collection_locked", "the keyring collection is locked")
            raise SecretServiceError("provider_error", "keyring item could not be created")
        self._await_prompt(prompt)
        if str(item) == "/":
            raise SecretServiceError("provider_error", "keyring item was not created")
        return str(item)

    # ---------------------------------------------------------- vault items

    def list_items(self, app: str = VAULT_APP) -> Dict[str, Any]:
        if app != VAULT_APP:
            raise SecretServiceError("permission_denied", "only the Vault scope may be listed")
        _bus, svc, _props = self._service()
        try:
            unlocked, locked = svc.SearchItems(
                dbus.Dictionary({"application": app}, signature="ss"), timeout=8)
        except Exception as exc:  # noqa: BLE001
            if "IsLocked" in str(exc) or "locked" in str(exc).lower():
                raise SecretServiceError("collection_locked", "the keyring collection is locked")
            raise SecretServiceError("provider_error", "keyring search failed")
        if locked and not unlocked:
            raise SecretServiceError("collection_locked", "the keyring collection is locked")
        items = []
        for path in list(unlocked)[:MAX_ITEMS_PER_SCOPE]:
            try:
                payload = self._read_item_payload(str(path), VAULT_APP)
            except SecretServiceError:
                continue
            if not payload or payload.get("schema") == VAULT_META_SCHEMA:
                continue
            items.append({
                "id": payload["id"],
                "type": payload["type"],
                "title": payload["title"],
                "url": payload["url"],
                "username": payload["username"],
                "tags": payload["tags"],
                "favorite": payload["favorite"],
                "created_at": payload["created_at"],
                "updated_at": payload["updated_at"],
                "has_notes": bool(payload.get("notes")),
                "has_password": bool(payload.get("password")),
            })
        items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return {"success": True, "items": items, "count": len(items),
                "truncated": len(unlocked) > MAX_ITEMS_PER_SCOPE}

    def _read_item_payload(self, item_path: str, app: str) -> Optional[Dict[str, Any]]:
        bus = self._connect()
        try:
            obj = bus.get_object(SERVICE, item_path, introspect=False)
            props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
            attrs = props.Get("org.freedesktop.Secret.Item", "Attributes", timeout=5)
        except Exception:  # noqa: BLE001
            return None
        attr_map = {str(k): str(v) for k, v in attrs.items()}
        if attr_map.get("application") != app:
            return None
        item_id = attr_map.get("item_id", "")
        if not item_id or not re.match(r"^[A-Za-z0-9._-]{1,80}$", item_id):
            return None
        raw = self._read_secret(item_path)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        payload["id"] = item_id
        return payload

    def get_item(self, item_id: str, app: str = VAULT_APP) -> Dict[str, Any]:
        if app != VAULT_APP:
            raise SecretServiceError("permission_denied", "only the Vault scope is readable")
        item_id = self._validate_item_id(item_id)
        path = self._find_one(app, VAULT_SCHEMA, item_id)
        if path is None:
            raise SecretServiceError("item_not_found", "item does not exist")
        payload = self._read_item_payload(path, app)
        if payload is None:
            raise SecretServiceError("item_not_found", "item is not a Nuxel Vault item")
        try:
            item = validate_vault_payload(payload)
        except SecretServiceError:
            raise SecretServiceError("invalid_request", "stored item failed validation")
        item["id"] = item_id
        return {"success": True, "item": item}

    def create_item(self, payload: Dict[str, Any], app: str = VAULT_APP) -> Dict[str, Any]:
        if app != VAULT_APP:
            raise SecretServiceError("permission_denied", "only the Vault scope is writable")
        item = validate_vault_payload(payload)
        item_id = uuid.uuid4().hex
        item["id"] = item_id
        raw = json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._create_secret(app, VAULT_SCHEMA, item_id, raw, replace=False)
        return {"success": True, "id": item_id, "item": item}

    def update_item(self, item_id: str, payload: Dict[str, Any],
                    app: str = VAULT_APP) -> Dict[str, Any]:
        if app != VAULT_APP:
            raise SecretServiceError("permission_denied", "only the Vault scope is writable")
        item_id = self._validate_item_id(item_id)
        item = validate_vault_payload(payload)
        item["id"] = item_id
        path = self._find_one(app, VAULT_SCHEMA, item_id)
        if path is None:
            raise SecretServiceError("item_not_found", "item does not exist")
        raw = json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        bus = self._connect()
        try:
            obj = bus.get_object(SERVICE, path, introspect=False)
            iface = dbus.Interface(obj, "org.freedesktop.Secret.Item")
            prompt = iface.SetSecret(self._secret_struct(raw), timeout=10)
        except SecretServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            if "IsLocked" in str(exc) or "locked" in str(exc).lower():
                raise SecretServiceError("collection_locked", "the keyring collection is locked")
            raise SecretServiceError("provider_error", "item could not be updated")
        self._await_prompt(prompt)
        return {"success": True, "id": item_id, "item": item}

    def delete_item(self, item_id: str, app: str = VAULT_APP) -> Dict[str, Any]:
        if app != VAULT_APP:
            raise SecretServiceError("permission_denied", "only the Vault scope is writable")
        item_id = self._validate_item_id(item_id)
        path = self._find_one(app, VAULT_SCHEMA, item_id)
        if path is None:
            raise SecretServiceError("item_not_found", "item does not exist")
        prompt = self._delete_path(path)
        return {"success": True, "id": item_id}

    def reset_vault(self) -> Dict[str, Any]:
        """Delete ONLY org.nuxel.Vault items.  Never the Authenticator credential."""
        items = self.list_items(VAULT_APP)["items"]
        deleted = 0
        for item in items:
            try:
                self.delete_item(item["id"], VAULT_APP)
                deleted += 1
            except SecretServiceError as exc:
                if exc.code != "item_not_found":
                    raise
        # Remove the meta marker last.
        path = self._find_one(VAULT_APP, VAULT_META_SCHEMA, "meta")
        if path:
            self._delete_path(path)
        LOG.info("keyring reset_vault deleted=%d", deleted)
        return {"success": True, "deleted": deleted}

    def _delete_path(self, path: str):
        bus = self._connect()
        try:
            obj = bus.get_object(SERVICE, path, introspect=False)
            iface = dbus.Interface(obj, "org.freedesktop.Secret.Item")
            prompt = iface.Delete(timeout=10)
        except Exception as exc:  # noqa: BLE001
            if "UnknownObject" in str(exc) or "UnknownMethod" in str(exc):
                raise SecretServiceError("item_not_found", "item does not exist")
            raise SecretServiceError("provider_error", "item could not be deleted")
        self._await_prompt(prompt)
        return True

    @staticmethod
    def _validate_item_id(item_id: Any) -> str:
        if not isinstance(item_id, str) or not re.match(r"^[A-Za-z0-9._-]{1,80}$", item_id):
            raise SecretServiceError("invalid_request", "invalid item id")
        return item_id

    # --------------------------------------------------- authenticator item

    def _auth_find(self) -> Optional[str]:
        _bus, svc, _props = self._service()
        attrs = {"application": AUTH_APP, "purpose": AUTH_PURPOSE, "schema": AUTH_SCHEMA}
        try:
            unlocked, locked = svc.SearchItems(dbus.Dictionary(attrs, signature="ss"), timeout=8)
        except Exception as exc:  # noqa: BLE001
            if "IsLocked" in str(exc) or "locked" in str(exc).lower():
                raise SecretServiceError("collection_locked", "the keyring collection is locked")
            raise SecretServiceError("provider_error", "keyring search failed")
        if unlocked:
            return str(unlocked[0])
        if locked:
            raise SecretServiceError("collection_locked", "the keyring collection is locked")
        return None

    def authenticator_status(self) -> Dict[str, Any]:
        try:
            path = self._auth_find()
            return {"success": True, "exists": path is not None,
                    "state": "linked" if path else "not_linked"}
        except SecretServiceError as exc:
            if exc.code == "collection_locked":
                return {"success": True, "exists": None, "state": "keyring_locked",
                        "locked": True}
            raise

    def authenticator_store(self, credential: str) -> Dict[str, Any]:
        credential = validate_auth_credential(credential)
        path = self._auth_find()
        raw = credential.encode("utf-8")
        credential = None
        if path is not None:
            bus = self._connect()
            obj = bus.get_object(SERVICE, path, introspect=False)
            iface = dbus.Interface(obj, "org.freedesktop.Secret.Item")
            try:
                prompt = iface.SetSecret(self._secret_struct(raw), timeout=10)
                self._await_prompt(prompt)
            except SecretServiceError:
                raise
            except Exception:  # noqa: BLE001
                raise SecretServiceError("provider_error", "credential could not be updated")
        else:
            attrs = {"application": AUTH_APP, "purpose": AUTH_PURPOSE, "schema": AUTH_SCHEMA}
            props = {
                "org.freedesktop.Secret.Item.Label": dbus.String("Nuxel Authenticator credential"),
                "org.freedesktop.Secret.Item.Attributes": dbus.Dictionary(attrs, signature="ss"),
            }
            _bus, svc, _props = self._service()
            default = str(svc.ReadAlias("default", timeout=5))
            if default == "/":
                raise SecretServiceError("collection_locked", "the keyring collection is locked")
            try:
                cobj = self._connect().get_object(SERVICE, default, introspect=False)
                ciface = dbus.Interface(cobj, "org.freedesktop.Secret.Collection")
                item, prompt = ciface.CreateItem(
                    dbus.Dictionary(props, signature="sv"),
                    self._secret_struct(raw), True, timeout=12)
                self._await_prompt(prompt)
            except SecretServiceError:
                raise
            except Exception:  # noqa: BLE001
                raise SecretServiceError("provider_error", "credential could not be stored")
        # Read back only to verify the write; never log or return the value.
        check = self.authenticator_get()
        if not secrets.compare_digest(str(check.get("credential", "")).encode("utf-8"),
                                      raw):
            self.authenticator_delete()
            raise SecretServiceError("provider_error", "credential verification failed")
        return {"success": True, "exists": True, "state": "linked"}

    def authenticator_get(self) -> Dict[str, Any]:
        path = self._auth_find()
        if path is None:
            raise SecretServiceError("item_not_found", "no saved Authenticator credential")
        raw = self._read_secret(path)
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise SecretServiceError("provider_error", "stored credential is not UTF-8")
        return {"success": True, "credential": value}

    def authenticator_delete(self) -> Dict[str, Any]:
        path = self._auth_find()
        if path is None:
            return {"success": True, "deleted": False, "state": "not_linked"}
        self._delete_path(path)
        return {"success": True, "deleted": True, "state": "not_linked"}

    # --------------------------------------------------------- diagnostics

    def diagnostics(self) -> Dict[str, Any]:
        st = self.status()
        try:
            proc = subprocess.run(["/usr/bin/gnome-keyring-daemon", "--version"],
                                  capture_output=True, text=True, timeout=4)
            version = (proc.stdout or proc.stderr or "").strip().splitlines()[0][:120]
        except Exception:  # noqa: BLE001
            version = "unknown"
        return {
            "success": True,
            "provider": "gnome-keyring",
            "version": version,
            "bus": self.bus_address,
            "runtime_dir": self.runtime_dir,
            "keyring_file_present": self._keyring_exists(),
            "status": st,
            "prompt_model": "pam-login-stdin",
            "notes": ("The stock gcr prompt does not map on Phoc in this image; "
                      "the Vault UI collects the master password and the bridge "
                      "uses gnome-keyring-daemon's PAM login path."),
        }
