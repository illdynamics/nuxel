#!/usr/bin/env python3
"""Scoped keyring RPC layer for the Nuxel HTTP bridge.

The browser never receives a generic Secret Service proxy.  Each verb is
allow-listed per app identity, errors are structured and value-free, and the
two secret scopes are deliberately asymmetric:

    org.nuxel.Vault          -> its own vault items (CRUD) + status/lock/unlock
    org.nuxel.Authenticator  -> status/lock/unlock + one named credential
    org.nuxel.Home           -> status/lock only (screen-lock integration)

A request body's app_id is never trusted on its own: api.py checks that the
bearer session token was issued for the same app, that the request Origin is
the local PWA origin and that the Referer path is the app's registered route.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

try:
    from .secret_service import (SecretService, SecretServiceError, VAULT_APP, AUTH_APP)
except ImportError:  # when imported as a top-level module by api.py
    from secret_service import (SecretService, SecretServiceError, VAULT_APP, AUTH_APP)

LOG = logging.getLogger("nuxel-keyring")

VAULT_VERBS = {
    "status", "initialize", "unlock", "lock", "list-items", "get-item",
    "create-item", "update-item", "delete-item", "reset-vault",
    "backup-status", "diagnostics", "authenticator-credential-status",
}
AUTH_VERBS = {
    "status", "unlock", "lock", "diagnostics",
    "authenticator-credential-status", "authenticator-credential-store",
    "authenticator-credential-get", "authenticator-credential-delete",
}
HOME_VERBS = {"status", "lock"}

ALLOWED = {
    VAULT_APP: VAULT_VERBS,
    AUTH_APP: AUTH_VERBS,
    "org.nuxel.Home": HOME_VERBS,
}

KEYRING_APP_PATHS = {
    VAULT_APP: "/pwa/nuxel-apps/vault/",
    AUTH_APP: "/pwa/nuxel-apps/authenticator/",
    "org.nuxel.Home": "/pwa/nuxel-home/",
}
KEYRING_APP_CAPABILITY = {
    VAULT_APP: "secrets:manage",
    AUTH_APP: "secrets:authenticator-unlock",
}

# Failed unlock burst control.  GNOME Keyring applies its own strengthening;
# this is only a bridge-level shield against a PWA retry loop.
_FAIL_WINDOW = 300.0
_FAIL_LIMIT = 5
_fail_state: Dict[str, list] = {}
_fail_lock = threading.Lock()


def _rate_allowed(app_id: str) -> Tuple[bool, int]:
    now = time.time()
    with _fail_lock:
        entries = [t for t in _fail_state.get(app_id, []) if now - t < _FAIL_WINDOW]
        _fail_state[app_id] = entries
        if len(entries) >= _FAIL_LIMIT:
            return False, int(_FAIL_WINDOW - (now - entries[0])) + 1
    return True, 0


def _record_failure(app_id: str) -> None:
    with _fail_lock:
        _fail_state.setdefault(app_id, []).append(time.time())


def _record_success(app_id: str) -> None:
    with _fail_lock:
        _fail_state.pop(app_id, None)


def _error(code: str, message: str = "", **extra) -> Dict[str, Any]:
    doc = {"success": False, "error": code, "detail": message or code}
    doc.update(extra)
    return doc


def check_identity(app_id, headers, session, registry_entry, allowed_origins):
    """Pure app-identity check used by the HTTP layer and its tests.

    A caller-supplied JSON app_id is never proof.  The per-session token must be
    issued for the same app from the app's own route; the current request must
    carry the allowed local Origin and a Referer under that same route; and the
    registry manifest must grant the narrow keyring capability.
    """
    expected_path = KEYRING_APP_PATHS.get(app_id)
    if not expected_path:
        return {"success": False, "error": "permission_denied",
                "detail": "this app has no keyring scope"}
    if session is None:
        return {"success": False, "error": "token_required", "state": "unauthorized",
                "detail": "keyring operations require a per-session app token"}
    if session.get("app_id") != app_id:
        return {"success": False, "error": "identity_mismatch", "state": "denied",
                "detail": "the session token belongs to a different app"}
    origin = headers.get("Origin", "") if hasattr(headers, "get") else ""
    if origin not in allowed_origins:
        return {"success": False, "error": "permission_denied", "state": "denied",
                "detail": "keyring operations require the local PWA origin"}
    # The native PWA host mints a token for the exact iframe the trusted Home
    # page created.  WebKit sends no Referer from those iframes, so the token's
    # server-side issuer is the route proof.  Self-issued /auth/token tokens
    # still require the strict Referer route check.
    if session.get("issuer") != "nuxel-launcher":
        issued_ref = urlparse(session.get("referer") or "").path
        current_ref = urlparse(headers.get("Referer", "") or "").path
        if not issued_ref.startswith(expected_path) or not current_ref.startswith(expected_path):
            return {"success": False, "error": "identity_mismatch", "state": "denied",
                    "detail": "the request did not originate from this app route"}
    cap = KEYRING_APP_CAPABILITY.get(app_id)
    if cap:
        if not isinstance(registry_entry, dict):
            return {"success": False, "error": "permission_denied", "state": "denied",
                    "detail": "the app registry has no entry for this app"}
        caps = registry_entry.get("capabilities")
        if not isinstance(caps, list) or cap not in caps:
            return {"success": False, "error": "permission_denied", "state": "denied",
                    "detail": "the app registry does not grant " + cap}
    return None


class KeyringAPI:
    def __init__(self, provider=None):
        self.provider = provider or SecretService()
        self._lock = threading.RLock()

    def handle(self, app_id: str, verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params if isinstance(params, dict) else {}
        allowed = ALLOWED.get(app_id)
        if not allowed or verb not in allowed:
            LOG.warning("keyring denied app=%s verb=%s", app_id, verb)
            return _error("permission_denied", "this app may not use this keyring operation")
        if not isinstance(verb, str) or not verb:
            return _error("invalid_request", "missing keyring verb")
        if len(repr(params)) > 512 * 1024:
            return _error("invalid_request", "request is too large")

        ok, retry = _rate_allowed(app_id)
        if not ok and verb in ("unlock", "initialize"):
            LOG.warning("keyring rate_limited app=%s verb=%s", app_id, verb)
            return _error("rate_limited", "too many failed unlock attempts", retry_after=retry)

        started = time.monotonic()
        try:
            with self._lock:
                result = self._dispatch(app_id, verb, params)
            if verb in ("unlock", "initialize") and result.get("success"):
                _record_success(app_id)
            status = "ok" if result.get("success") else str(result.get("error"))
            LOG.info("keyring app=%s verb=%s status=%s ms=%d", app_id, verb, status,
                     int((time.monotonic() - started) * 1000))
            return result
        except SecretServiceError as exc:
            if exc.code in ("invalid_credentials",):
                _record_failure(app_id)
            LOG.info("keyring app=%s verb=%s status=%s ms=%d", app_id, verb, exc.code,
                     int((time.monotonic() - started) * 1000))
            extra: Dict[str, Any] = {}
            if exc.code == "provider_unavailable":
                extra.update({"state": "unavailable", "offline": True, "available": False})
            elif exc.code == "collection_locked":
                extra.update({"state": "collection_locked", "locked": True})
            elif exc.code == "invalid_credentials":
                extra.update({"state": "locked", "locked": True})
            elif exc.code == "user_cancelled":
                extra.update({"state": "locked", "cancelled": True})
            elif exc.code == "item_not_found":
                extra.update({"state": "not_found"})
            elif exc.code == "timeout":
                extra.update({"state": "timeout"})
            return _error(exc.code, exc.message, **extra)
        except Exception as exc:  # noqa: BLE001
            # Never include exception text in a secret path: it could contain a
            # D-Bus payload.  Log only the exception class.
            LOG.error("keyring internal error app=%s verb=%s type=%s", app_id, verb,
                      type(exc).__name__)
            return _error("provider_error", "the keyring provider failed")

    def _dispatch(self, app_id: str, verb: str, params: Dict[str, Any]) -> Dict[str, Any]:
        p = self.provider
        if verb == "status":
            return p.status()
        if verb == "initialize":
            return p.initialize(str(params.get("master_password", "")),
                               str(params.get("label") or "Nuxel Vault"))
        if verb == "unlock":
            return p.unlock(str(params.get("master_password", "")))
        if verb == "lock":
            return p.lock()
        if verb == "diagnostics":
            return p.diagnostics()
        if verb == "backup-status":
            st = p.status()
            count = 0
            if st.get("state") == "unlocked":
                try:
                    count = p.list_items(VAULT_APP).get("count", 0)
                except SecretServiceError:
                    count = 0
            return {"success": True, "format": "nuxel-vault-archive-v1",
                    "encrypted": True, "item_count": count,
                    "collection": st.get("collection")}
        if verb == "list-items":
            return p.list_items(VAULT_APP)
        if verb == "get-item":
            return p.get_item(str(params.get("item_id", "")), VAULT_APP)
        if verb == "create-item":
            return p.create_item(params.get("item") or {}, VAULT_APP)
        if verb == "update-item":
            return p.update_item(str(params.get("item_id", "")),
                                 params.get("item") or {}, VAULT_APP)
        if verb == "delete-item":
            return p.delete_item(str(params.get("item_id", "")), VAULT_APP)
        if verb == "reset-vault":
            if params.get("confirm") is not True:
                return _error("invalid_request", "reset requires explicit confirmation")
            return p.reset_vault()
        if verb == "authenticator-credential-status":
            return p.authenticator_status()
        if verb == "authenticator-credential-store":
            if app_id != AUTH_APP:
                return _error("permission_denied", "only the Authenticator may store its credential")
            if params.get("consent") is not True:
                return _error("invalid_request", "explicit consent is required")
            return p.authenticator_store(str(params.get("credential", "")))
        if verb == "authenticator-credential-get":
            if app_id != AUTH_APP:
                return _error("permission_denied", "only the Authenticator may read its credential")
            return p.authenticator_get()
        if verb == "authenticator-credential-delete":
            if app_id != AUTH_APP:
                return _error("permission_denied", "only the Authenticator may delete its credential")
            return p.authenticator_delete()
        return _error("invalid_request", "unknown keyring verb")


_API: Optional[KeyringAPI] = None
_API_LOCK = threading.Lock()


def get_api() -> KeyringAPI:
    global _API
    with _API_LOCK:
        if _API is None:
            _API = KeyringAPI()
        return _API
