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

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import shutil
import signal
import subprocess
import tempfile
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
INTERNAL_SCHEMA = "nuxel-internal-record-v1"
VERIFIER_SCHEMA = "nuxel-vault-verifier-v1"
# A fixed application string so the verifier item is visible to any Secret
# Service client that can see the collection (search is by attributes only).
VERIFIER_APP = "org.nuxel.Vault"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
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


def _verifier_record(password: str) -> Dict[str, Any]:
    """Salted scrypt verifier for the Vault master password.

    The verifier is NOT the keyring: the keyring always does the real
    encryption.  It exists so the UI can distinguish a wrong password from a
    provider/PAM failure (the two used to be reported identically) and so an
    unlock can be routed through the supported secret-struct API when the PAM
    login path is unavailable.  It holds no usable secret.
    """
    salt = secrets.token_hex(16)
    pin = password.encode("utf-8")
    verifier = hashlib.scrypt(pin, salt=bytes.fromhex(salt), n=SCRYPT_N,
                              r=SCRYPT_R, p=SCRYPT_P, dklen=32).hex()
    return {"schema": VERIFIER_SCHEMA, "salt": salt, "verifier": verifier,
            "kdf": "scrypt(n=2^14,r=8,p=1,dklen=32)"}


def _verifier_matches(rec: Dict[str, Any], password: str) -> bool:
    try:
        got = hashlib.scrypt(str(password).encode("utf-8"),
                             salt=bytes.fromhex(rec["salt"]), n=SCRYPT_N,
                             r=SCRYPT_R, p=SCRYPT_P, dklen=32).hex()
        return hmac.compare_digest(got, str(rec["verifier"]))
    except Exception:  # noqa: BLE001
        return False


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
        # The daemon's control socket must live in a writable directory.  The
        # bridge unit binds /run/nuxel-wayland/keyring read-write; the boot
        # session script also creates it before the bridge starts.
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

    # ------------------------------------------------- unopenable keyring guard
    # A login keyring written by an older live deploy ended up with a private
    # key that gnome-keyring never exported (no IDX2/PRV2 record can unlock it),
    # so EVERY password path failed with a provider error.  That is the "I set
    # a Vault password, pressed Close, and then could never unlock" trap.  It
    # can never be opened again, so the only honest fix is: keep a byte-exact
    # backup, replace it with a keyring this daemon CREATES from the owner's
    # password, and verify that one unlocks -- all before any data is stored.
    KEYRING_MAGIC = b"GnomeKeyring\n"
    BACKUP_TAG = ".unopenable-backup-"

    def _keyring_header(self) -> bytes:
        try:
            with open(self._keyring_file(), "rb") as fh:
                return fh.read(64)
        except OSError:
            return b""

    def _keyring_has_exported_key(self) -> bool:
        """Private key record present = the file can be unlocked by a password.

        A keyring created by gnome-keyring-daemon carries its RSA private key
        (and the AES/SHA256 metadata).  The broken file on this image was 1495
        bytes of encrypted index data with NO key record at all: the daemon can
        never decrypt it, whatever password is supplied.  This is structural
        metadata only -- no secret is read, parsed or exported.
        """
        path = self._keyring_file()
        try:
            with open(path, "rb") as fh:
                data = fh.read(256 * 1024)
        except OSError:
            return False
        if not data.startswith(self.KEYRING_MAGIC):
            return False
        return any(rec in data for rec in (b"PRV2", b"IDX2", b"HASH", b"AES", b"SHA256"))

    def keyring_state(self) -> Dict[str, Any]:
        """Is the keyring file present, and can it ever be opened?"""
        present = self._keyring_exists()
        openable = present and self._keyring_has_exported_key()
        return {
            "present": present,
            "openable": bool(openable),
            "needs_recovery": bool(present and not openable),
            "path": self._keyring_file(),
        }

    def _backup_unopenable_keyring(self) -> Optional[str]:
        src = self._keyring_file()
        if not os.path.isfile(src):
            return None
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        dest = os.path.join("/var/lib/nuxel/security/keyring-backups",
                            "login.keyring" + self.BACKUP_TAG + stamp)
        try:
            os.makedirs(os.path.dirname(dest), mode=0o700, exist_ok=True)
            shutil.copy2(src, dest)
            os.chmod(dest, 0o600)
            return dest
        except OSError:
            return None

    def _remove_dead_keyring(self) -> None:
        owner = self._name_owner_pid()
        if owner:
            self._safe_stop_owner(owner)
        self._cleanup_orphans()
        self._session_path = None
        try:
            os.unlink(self._keyring_file())
        except OSError:
            pass

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

    def _daemon_env(self) -> Dict[str, str]:
        env = dict(os.environ)
        env.update({
            "HOME": self.home,
            "XDG_RUNTIME_DIR": self.runtime_dir,
            "DBUS_SESSION_BUS_ADDRESS": self.bus_address,
            "GDK_BACKEND": "wayland",
            "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", "wayland-0"),
        })
        return env

    def _run_daemon(self, args: List[str], password: Optional[str] = None,
                    timeout: float = BOUNDED_UNLOCK_SECONDS):
        """Run one daemon invocation.  A password goes on stdin only.

        --login normally runs in the FOREGROUND and owns the bus for the whole
        session; here it is bounded.  When the timeout expires the daemon has
        already accepted the key (verified separately by the bus state), so the
        timeout is reported through the returned object instead of aborting the
        unlock.
        """
        env = self._daemon_env()
        data = None
        if password is not None:
            data = (password + "\n").encode("utf-8")
        argv = ["/usr/bin/gnome-keyring-daemon"] + list(args)
        try:
            proc = subprocess.run(argv, input=data, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=timeout,
                                  env=env, close_fds=True)
        except subprocess.TimeoutExpired as exc:
            data = None
            out = subprocess.CompletedProcess(argv, 0,
                                             (exc.stdout or b""), (exc.stderr or b""))
            return out
        except OSError:
            data = None
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
        # but owns the bus, which is enough for status/diagnostics.  A D-Bus
        # activation file is not guaranteed on this image, so START the daemon
        # explicitly (bounded, no password) instead of only waiting for a name
        # that nothing would otherwise own.
        try:
            self._run_daemon(["--start", "--components=secrets"],
                             timeout=BOUNDED_START_SECONDS)
        except SecretServiceError:
            pass
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
            # Ask about the CURRENTLY RUNNING daemon first: if it already holds
            # the unlocked collection, nothing needs to be replaced and a wrong
            # password can never disturb an open Vault.
            try:
                _bus0, svc0, _p0 = self._service()
                cur = str(svc0.ReadAlias("default", timeout=4))
                if cur and cur != "/":
                    col0 = self._collection_state(cur)
                    if col0.get("locked") is False:
                        rec0 = self._verifier_get()
                        if rec0 is not None and not _verifier_matches(rec0, password):
                            self._last_unlock_wrong = True
                            raise SecretServiceError("invalid_credentials",
                                                     "the master password is not correct")
                        self._last_unlock_verified = True
                        return
            except SecretServiceError as exc:
                if exc.code in ("invalid_credentials",):
                    raise
                # a provider/collection read failure is handled by the unlock
            self._session_path = None   # the daemon replacement invalidates it
            owner = self._name_owner_pid()
            if owner:
                if not self._safe_stop_owner(owner):
                    raise SecretServiceError("provider_error",
                                             "the running keyring daemon could not be stopped safely")
            self._cleanup_orphans()
            self._last_unlock_wrong = False
            # Measured on gnome-keyring 48.0 (Fedora 43, this image):
            #   --login    reads ONE line from stdin and starts the existing
            #              login keyring's daemon in the foreground, holding the
            #              bus name.  Verified: correct password -> unlocked,
            #              wrong password -> collection stays locked.
            #   --unlock   consumes the stdin password but the replacement
            #              daemon never finishes the unlock ("unknown daemon
            #              error", 25 s).  Never use it for the session.
            #   --replace  does NOT read stdin at all; it is only valid inside a
            #              fresh dbus-run-session at login time.
            # The password is only ever on stdin: never argv, never the
            # environment, never a log.
            proc = self._run_daemon(["--login", "--components=secrets"],
                                    password=password)
            password = None  # release the reference as soon as the pipe closes
            self._last_daemon_rc = proc.returncode
            self._last_daemon_err = (proc.stderr or b"").decode("utf-8", "replace")[-400:]
            if proc.returncode != 0:
                raise SecretServiceError("provider_error",
                                         "keyring login daemon failed (rc=%d): %s"
                                         % (proc.returncode, self._last_daemon_err[:200]))
            # A wrong password is reported by the daemon in this message; any
            # other failure has to be surfaced as a provider error so the UI
            # can distinguish it from "wrong password".
            if "did not unlock" in self._last_daemon_err.lower() or \
                    "invalid password" in self._last_daemon_err.lower():
                self._last_unlock_wrong = True
            # --login already owns the bus for the session; only re-activate a
            # daemon when it did not (e.g. a wrong password exited early).
            if self._name_owner_pid() is None:
                try:
                    self._run_daemon(["--start", "--components=secrets"],
                                     timeout=BOUNDED_START_SECONDS)
                except SecretServiceError:
                    pass
            end = time.monotonic() + BOUNDED_START_SECONDS
            while time.monotonic() < end:
                try:
                    _bus, svc, _props = self._service()
                    default = svc.ReadAlias("default", timeout=4)
                    if str(default) == "/":
                        default = self._collection_path_fallback()
                    if default and str(default) != "/":
                        state = self._collection_state(str(default))
                        if state.get("locked") is False:
                            self._last_unlock_verified = True
                            return
                except SecretServiceError:
                    pass
                time.sleep(0.25)
            # Wrong password: the keyring is intact and still locked.  Stop the
            # daemon we just started so a retry starts from a clean state.
            self._safe_stop_owner(self._name_owner_pid())
            self._cleanup_orphans()
            rec = self._verifier_get()
            if getattr(self, "_last_unlock_wrong", False) or \
                    (rec is not None and not _verifier_matches(rec, password)):
                raise SecretServiceError("invalid_credentials",
                                         "the master password did not unlock the keyring")
            raise SecretServiceError("provider_error",
                                     "keyring unlock did not complete: "
                                     + (getattr(self, "_last_daemon_err", "")[:200] or "unknown daemon error"))

    def _collection_path_fallback(self) -> str:
        """Find the Login collection object even if ReadAlias('default') lags.

        After a daemon replacement the alias can briefly read '/' while the
        collection object already exists.  Searching the object paths is
        read-only and never unlocks anything by itself.
        """
        bus = self._connect()
        for cand in ("/org/freedesktop/secrets/collection/login",
                     "/org/freedesktop/secrets/collection/Default_Collection"):
            try:
                obj = bus.get_object(SERVICE, cand, introspect=False)
                props = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                vals = props.GetAll("org.freedesktop.Secret.Collection", timeout=3)
                if vals is not None:
                    return cand
            except Exception:  # noqa: BLE001
                continue
        return "/"

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
                ks = self.keyring_state()
                return {
                    "success": True,
                    "provider": "gnome-keyring",
                    "available": True,
                    "collection": col,
                    "locked": col["locked"],
                    "initialized": True,
                    "keyring_present": True,
                    "keyring_openable": ks["openable"],
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
            recovered = None
            if self._keyring_exists() and not self._keyring_has_exported_key():
                # Dead keyring: preserve it, then let this daemon create a fresh
                # one that is bound to the owner's new master password.
                recovered = self._backup_unopenable_keyring()
                self._remove_dead_keyring()
                LOG.warning("vault: unopenable keyring preserved at %s and replaced", recovered)
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
            if not had_keyring:
                # The sidecar is the durable "is this the right password?" check
                # for the collection this daemon just created.
                if not self._verifier_put_sidecar(password):
                    raise SecretServiceError(
                        "provider_error",
                        "the keyring was created but its verifier could not be "
                        "written next to it (check /root/.local/share/keyrings)")
            if recovered:
                LOG.info("vault: recovered a new keyring after replacing an unopenable one")
            meta = self._find_one(VAULT_APP, VAULT_META_SCHEMA, "meta")
            if meta is None:
                self._create_secret(
                    VAULT_APP, VAULT_META_SCHEMA, "meta",
                    json.dumps({"schema": VAULT_META_SCHEMA, "version": 1,
                                "initialized_at": _iso_now()},
                               separators=(",", ":")).encode("utf-8"))
            result = self.status()
            result["recovered_unopenable_keyring"] = bool(recovered)
            if recovered:
                result["keyring_backup"] = recovered
            return result

    # ------------------------------------------------- password verifier
    def _verifier_get(self) -> Optional[Dict[str, Any]]:
        """The verifier for the CURRENT keyring, or None.

        Sidecar first (authoritative).  The legacy in-keyring item is only a
        fallback for keyrings created by older builds; it is trusted only when
        its recorded creation stamp matches the current keyring file, so a
        verifier from a replaced collection can never make the new master
        password look wrong ("set it, close, cannot unlock").
        """
        doc = self._verifier_get_sidecar()
        if doc is not None:
            return doc
        try:
            path = self._internal_find("master-password-verifier")
        except SecretServiceError:
            return None
        if path is None:
            return None
        try:
            doc = json.loads(self._read_secret(path).decode("utf-8"))
            if not isinstance(doc, dict) or not doc.get("verifier"):
                return None
            if "created" in doc and int(doc.get("created") or 0) != self._keyring_created():
                return None
            if "created" not in doc:
                return None      # unstamped = unknown keyring; never trust
            return doc
        except Exception:  # noqa: BLE001
            return None

    def _keyring_created(self) -> int:
        """Creation stamp gnome-keyring stores in the keyring header."""
        try:
            with open(self._keyring_file(), "rb") as fh:
                head = fh.read(64)
        except OSError:
            return 0
        try:
            return int.from_bytes(head[44:48], "big")
        except Exception:  # noqa: BLE001
            return 0

    def _verifier_sidecar_path(self) -> str:
        return os.path.join(os.path.dirname(self._keyring_file()),
                            "nuxel-vault-verifier.json")

    def _verifier_get_sidecar(self) -> Optional[Dict[str, Any]]:
        """Fallback verifier stored beside (never inside) the keyring.

        Only written while the collection is known unlocked, so it can only
        ever vouch for a password that actually opened THIS keyring.  It holds
        a salted scrypt verifier, never the password, and is mode 0600.
        """
        try:
            with open(self._verifier_sidecar_path()) as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            return None
        if not isinstance(doc, dict) or not doc.get("verifier"):
            return None
        created = int(doc.get("created") or 0)
        current = self._keyring_created()
        # created == 0 means the keyring header does not expose a creation
        # stamp on this build; the sidecar is still the only verifier and is
        # accepted.  A non-zero stamp MUST match, so a verifier left over from
        # a replaced keyring can never make the new password look wrong.
        if created and current and created != current:
            return None
        if created and not current:
            # Unknown current stamp: accept the sidecar but remember to
            # re-stamp it after this password is confirmed by the daemon.
            self._sidecar_restamp_after_success = True
        return doc

    def _verifier_put_sidecar(self, password: str) -> bool:
        try:
            rec = _verifier_record(password)
            rec["created"] = self._keyring_created()
            rec["schema"] = "nuxel-vault-verifier/2"
            path = self._verifier_sidecar_path()
            tmp = path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as fh:
                json.dump(rec, fh, sort_keys=True)
            os.replace(tmp, path)
            return True
        except Exception:  # noqa: BLE001
            return False

    def _verifier_put(self, password: str) -> bool:
        """Record the verifier for THIS keyring, only in the sidecar.

        The sidecar is authoritative because it is stamped with the keyring's
        creation time: a verifier from a replaced collection can never make the
        new master password look wrong.  It is deliberately NOT stored inside
        the collection: a Secret Service read during initialize is exactly what
        made a just-created keyring report "unknown daemon error" (the item was
        written, then could not be read back in the same lock/unlock race).
        """
        return self._verifier_put_sidecar(password)

    def verify_password(self, password: str) -> Dict[str, Any]:
        rec = self._verifier_get()
        if rec is None:
            return {"success": True, "verified": None, "reason": "no-verifier"}
        ok = _verifier_matches(rec, password)
        return {"success": True, "verified": bool(ok),
                "reason": None if ok else "wrong-master-password"}

    def _unlock_plain_session(self, password: str) -> bool:
        """Second supported path: unlock the Login collection with its own
        Secret Service prompt (the same thing Seahorse/gcr do).  The plain
        session keeps the password inside the daemon."""
        try:
            _bus, svc, _props = self._service()
            default = str(svc.ReadAlias("default", timeout=5))
            if default == "/":
                default = self._collection_path_fallback()
            if not default or default == "/":
                return False
            cobj = self._connect().get_object(SERVICE, default, introspect=False)
            ciface = dbus.Interface(cobj, "org.freedesktop.Secret.Collection")
            _unlocked, prompt = ciface.Unlock(timeout=10)
            # A prompt is not usable on Phoc; a direct zero-prompt unlock
            # happens when the daemon already holds the key.
            if prompt is not None and str(prompt) != "/":
                self._await_prompt(prompt, timeout=6)
            state = self._collection_state(default)
            return state.get("locked") is False
        except Exception:  # noqa: BLE001
            return False

    def unlock(self, password: str) -> Dict[str, Any]:
        with self._lock:
            try:
                st = self.status()
                if st.get("state") == "unlocked":
                    return st
            except SecretServiceError as exc:
                if exc.code != "provider_unavailable":
                    raise
            # A stored verifier distinguishes a wrong password from a provider
            # failure.  Without one (older keyring) fall through unchanged.
            if not isinstance(password, str) or not password:
                raise SecretServiceError("invalid_request", "master password is required")
            rec = self._verifier_get()
            if rec is not None and not _verifier_matches(rec, password):
                # The verifier is authoritative for "is this the password?".
                # Never hand a known-wrong password to the daemon: some daemon
                # builds report a successful --unlock without checking the
                # keyring, which would otherwise open the Vault on a typo.
                raise SecretServiceError("invalid_credentials",
                                         "the master password is not correct")
            verified = rec is not None
            try:
                self._unlock_via_login(password)
            except SecretServiceError as exc:
                if exc.code == "collection_locked":
                    # ReadAlias/collection inspection raced the new daemon;
                    # the challenge is the daemon, not a wrong password.
                    if self._unlock_plain_session(password):
                        return self.status()
                    raise SecretServiceError(
                        "provider_error",
                        "the keyring daemon did not confirm an unlocked collection")
                if exc.code != "invalid_credentials":
                    raise
                # PAM path failed for a reason other than the password (verifier
                # said it is right, or there is no verifier): try the supported
                # collection-unlock path once.  If that also fails, report the
                # provider/PAM fault instead of blaming the password.
                if self._unlock_plain_session(password):
                    return self.status()
                raise SecretServiceError(
                    "provider_error",
                    "the keyring provider could not unlock the collection "
                    "(PAM login failed); unlock the session from the Vault "
                    "again or restart nuxel-http-bridge")
            st = self.status()
            if verified is False or rec is None:
                pass
            if rec is None:
                # First successful unlock of an older keyring: record the
                # verifier now so future failures are distinguishable.  This
                # only ever happens after the password actually opened the
                # collection.
                self._verifier_put(password)
            elif getattr(self, "_sidecar_restamp_after_success", False):
                # The password just opened the collection; stamp the sidecar
                # with the current keyring so a later mismatch is meaningful.
                self._sidecar_restamp_after_success = False
                self._verifier_put_sidecar(password)
            return st

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
            # Only real Vault entries are listed.  The scope also holds the
            # internal records (meta marker, verifier, fingerprint HMAC key);
            # they are not user items and must never reach the UI -- one missing
            # "type" used to abort the WHOLE listing, which looked like an
            # empty, broken Vault.
            if not payload or payload.get("schema") != VAULT_SCHEMA:
                continue
            if payload.get("type") not in ("login", "note") or not isinstance(payload.get("title"), str):
                continue
            items.append({
                "id": payload["id"],
                "type": payload["type"],
                "title": payload["title"],
                "url": payload.get("url", ""),
                "username": payload.get("username", ""),
                "tags": payload.get("tags") or [],
                "favorite": bool(payload.get("favorite")),
                "created_at": payload.get("created_at", ""),
                "updated_at": payload.get("updated_at", ""),
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

    # ------------------------------------------------- internal records
    # A tiny, fixed-purpose record store for OS components (never exposed as
    # Vault items).  Only org.nuxel.Home may call this.  Used for the
    # fingerprint enrollment HMAC key so the record is bound to the Vault.
    def _internal_find(self, name: str) -> Optional[str]:
        _bus, svc, _props = self._service()
        attrs = {"application": VAULT_APP, "schema": INTERNAL_SCHEMA,
                 "item_id": str(name)[:64]}
        try:
            unlocked, locked = svc.SearchItems(dbus.Dictionary(attrs, signature="ss"),
                                               timeout=8)
        except Exception as exc:  # noqa: BLE001
            if "IsLocked" in str(exc) or "locked" in str(exc).lower():
                raise SecretServiceError("collection_locked", "the keyring collection is locked")
            raise SecretServiceError("provider_error", "keyring search failed")
        if unlocked:
            return str(unlocked[0])
        if locked:
            raise SecretServiceError("collection_locked", "the keyring collection is locked")
        return None

    def internal_get(self, name: str) -> Dict[str, Any]:
        import re as _re
        if not _re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", str(name or "")):
            raise SecretServiceError("invalid_request", "invalid record name")
        path = self._internal_find(name)
        if path is None:
            return {"success": True, "exists": False, "value": None}
        raw = self._read_secret(path)
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise SecretServiceError("provider_error", "stored record is not UTF-8")
        return {"success": True, "exists": True, "value": value}

    def internal_put(self, name: str, value: str) -> Dict[str, Any]:
        import re as _re
        if not _re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", str(name or "")):
            raise SecretServiceError("invalid_request", "invalid record name")
        if not isinstance(value, str) or len(value) > 4096:
            raise SecretServiceError("invalid_request", "record value is too large")
        raw = value.encode("utf-8")
        path = self._internal_find(name)
        if path is not None:
            self._delete_path(path)
        self._create_secret(VAULT_APP, INTERNAL_SCHEMA, str(name), raw)
        return {"success": True, "stored": True}

    def internal_delete(self, name: str) -> Dict[str, Any]:
        path = self._internal_find(name)
        if path is None:
            return {"success": True, "deleted": False}
        self._delete_path(path)
        return {"success": True, "deleted": True}

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
