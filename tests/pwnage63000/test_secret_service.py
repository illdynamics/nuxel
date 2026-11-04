#!/usr/bin/env python3
"""PWNAGE-63000 keyring provider/API tests (offline, no real D-Bus).

The fake provider is deliberately in this test file and is never imported by
production code.  It proves the scoped policy, fail-closed errors and the
separation between the Vault and Authenticator secret scopes.
"""
import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/nuxel-bridge/src"))

import keyring_api  # noqa: E402
from keyring_api import KeyringAPI, check_identity  # noqa: E402
from secret_service import SecretService, SecretServiceError, VAULT_APP, AUTH_APP  # noqa: E402


class FakeSecretService:
    """Test-only in-memory Secret Service.  Never selectable in production."""

    def __init__(self):
        self.initialized = True
        self.unlocked = True
        self.items = {}          # item_id -> {app, schema, payload}
        self.auth = None         # stored credential
        self.fail_unlock = False
        self.raise_provider = False
        self.raise_locked = False
        self.calls = []

    def _check(self, app):
        if self.raise_provider:
            raise SecretServiceError("provider_unavailable", "fake provider unavailable")
        if self.raise_locked:
            raise SecretServiceError("collection_locked", "fake collection locked")
        if not self.unlocked:
            raise SecretServiceError("collection_locked", "fake collection locked")

    def status(self):
        if self.raise_provider:
            raise SecretServiceError("provider_unavailable", "fake provider unavailable")
        return {"success": True, "provider": "fake", "available": True,
                "initialized": self.initialized,
                "locked": not self.unlocked,
                "state": "unlocked" if self.unlocked else ("collection_locked" if self.initialized else "not_initialized"),
                "collection": {"label": "Nuxel Vault", "locked": not self.unlocked,
                               "item_count": len(self.items)} if self.initialized else None}

    def initialize(self, password, label="Nuxel Vault"):
        if self.fail_unlock or password != "good-master-password":
            raise SecretServiceError("invalid_credentials", "wrong password")
        self.initialized = True
        self.unlocked = True
        return self.status()

    def unlock(self, password):
        if self.fail_unlock or password != "good-master-password":
            raise SecretServiceError("invalid_credentials", "wrong password")
        self.unlocked = True
        return self.status()

    def lock(self):
        self.unlocked = False
        return {"success": True, "locked": True, "state": "collection_locked"}

    def list_items(self, app=VAULT_APP):
        self._check(app)
        out = []
        for iid, rec in self.items.items():
            if rec["app"] == app and rec["schema"] == "nuxel-vault-item-v1":
                p = dict(rec["payload"])
                p["id"] = iid
                out.append({k: p.get(k) for k in ("id", "type", "title", "url", "username",
                                                   "tags", "favorite", "created_at", "updated_at")})
        return {"success": True, "items": out, "count": len(out)}

    def get_item(self, item_id, app=VAULT_APP):
        self._check(app)
        rec = self.items.get(item_id)
        if not rec or rec["app"] != app:
            raise SecretServiceError("item_not_found", "not found")
        p = dict(rec["payload"]); p["id"] = item_id
        return {"success": True, "item": p}

    def create_item(self, payload, app=VAULT_APP):
        self._check(app)
        iid = "id-%d" % (len(self.items) + 1)
        self.items[iid] = {"app": app, "schema": payload.get("schema", "nuxel-vault-item-v1"),
                           "payload": dict(payload)}
        return {"success": True, "id": iid, "item": dict(payload, id=iid)}

    def update_item(self, item_id, payload, app=VAULT_APP):
        self._check(app)
        rec = self.items.get(item_id)
        if not rec or rec["app"] != app:
            raise SecretServiceError("item_not_found", "not found")
        rec["payload"] = dict(payload)
        return {"success": True, "id": item_id, "item": dict(payload, id=item_id)}

    def delete_item(self, item_id, app=VAULT_APP):
        self._check(app)
        rec = self.items.get(item_id)
        if not rec or rec["app"] != app:
            raise SecretServiceError("item_not_found", "not found")
        del self.items[item_id]
        return {"success": True, "id": item_id}

    def reset_vault(self):
        deleted = 0
        for iid in [k for k, v in self.items.items() if v["app"] == VAULT_APP]:
            del self.items[iid]; deleted += 1
        return {"success": True, "deleted": deleted}

    def authenticator_status(self):
        if self.raise_provider:
            raise SecretServiceError("provider_unavailable", "fake provider unavailable")
        if not self.unlocked:
            return {"success": True, "exists": None, "state": "keyring_locked", "locked": True}
        return {"success": True, "exists": self.auth is not None,
                "state": "linked" if self.auth else "not_linked"}

    def authenticator_store(self, credential):
        self._check(AUTH_APP)
        if not credential or len(credential) < 8:
            raise SecretServiceError("invalid_request", "bad credential")
        self.auth = credential
        return {"success": True, "exists": True, "state": "linked"}

    def authenticator_get(self):
        self._check(AUTH_APP)
        if self.auth is None:
            raise SecretServiceError("item_not_found", "no credential")
        return {"success": True, "credential": self.auth}

    def authenticator_delete(self):
        self._check(AUTH_APP)
        self.auth = None
        return {"success": True, "deleted": True, "state": "not_linked"}

    def diagnostics(self):
        return {"success": True, "provider": "fake"}


@pytest.fixture
def api():
    keyring_api._fail_state.clear()
    return KeyringAPI(FakeSecretService())


@pytest.fixture
def fake(api):
    return api.provider


def test_status_and_unavailable(api, fake):
    assert api.handle(VAULT_APP, "status", {})["state"] == "unlocked"
    fake.raise_provider = True
    r = api.handle(VAULT_APP, "status", {})
    assert r["success"] is False and r["error"] == "provider_unavailable"
    assert r["offline"] is True and r["state"] == "unavailable"


def test_collection_locked_blocks_get(api, fake):
    fake.unlocked = False
    r = api.handle(VAULT_APP, "list-items", {})
    assert r["success"] is False and r["state"] == "collection_locked"


def test_crud_and_scope_isolation(api, fake):
    r = api.handle(VAULT_APP, "create-item", {"item": {"type": "login", "title": "Mail",
                                                       "username": "owner", "password": "secret-one"}})
    assert r["success"] is True
    iid = r["id"]
    # an unrelated application item the Vault must never see
    fake.items["other"] = {"app": "org.example.Other", "schema": "x",
                           "payload": {"title": "Unrelated"}}
    listing = api.handle(VAULT_APP, "list-items", {})
    assert listing["count"] == 1 and listing["items"][0]["id"] == iid
    got = api.handle(VAULT_APP, "get-item", {"item_id": iid})
    assert got["item"]["password"] == "secret-one"
    upd = api.handle(VAULT_APP, "update-item", {"item_id": iid, "item": {"type": "login", "title": "Mail2"}})
    assert upd["success"] is True and fake.items[iid]["payload"]["title"] == "Mail2"
    dele = api.handle(VAULT_APP, "delete-item", {"item_id": iid})
    assert dele["success"] is True and iid not in fake.items and "other" in fake.items


def test_reset_vault_never_touches_auth_or_unrelated(api, fake):
    api.handle(VAULT_APP, "create-item", {"item": {"type": "note", "title": "Note"}})
    fake.items["other"] = {"app": "org.example.Other", "schema": "x", "payload": {"title": "Unrelated"}}
    fake.auth = "auth-passphrase"
    r = api.handle(VAULT_APP, "reset-vault", {"confirm": True})
    assert r["success"] is True and r["deleted"] == 1
    assert "other" in fake.items and fake.auth == "auth-passphrase"


def test_authenticator_scope(api, fake):
    assert api.handle(AUTH_APP, "authenticator-credential-status", {})["exists"] is False
    r = api.handle(AUTH_APP, "authenticator-credential-store",
                   {"credential": "auth-passphrase", "consent": True})
    assert r["success"] is True and fake.auth == "auth-passphrase"
    got = api.handle(AUTH_APP, "authenticator-credential-get", {})
    assert got["credential"] == "auth-passphrase"
    # Vault must not be able to read or store the Authenticator credential
    assert api.handle(VAULT_APP, "authenticator-credential-get", {})["error"] == "permission_denied"
    assert api.handle(VAULT_APP, "authenticator-credential-store",
                      {"credential": "x", "consent": True})["error"] == "permission_denied"
    # Authenticator must not be able to enumerate Vault items
    assert api.handle(AUTH_APP, "list-items", {})["error"] == "permission_denied"
    # Explicit consent is mandatory
    assert api.handle(AUTH_APP, "authenticator-credential-store",
                      {"credential": "auth-passphrase"})["error"] == "invalid_request"
    assert api.handle(AUTH_APP, "authenticator-credential-delete", {})["success"] is True
    assert fake.auth is None


def test_home_only_status_and_lock(api):
    assert api.handle("org.nuxel.Home", "status", {})["success"] is True
    assert api.handle("org.nuxel.Home", "lock", {})["success"] is True
    assert api.handle("org.nuxel.Home", "list-items", {})["error"] == "permission_denied"
    assert api.handle("org.example.Evil", "status", {})["error"] == "permission_denied"


def test_unlock_failure_and_rate_limit(api, fake):
    for _ in range(5):
        r = api.handle(VAULT_APP, "unlock", {"master_password": "wrong"})
        assert r["success"] is False and r["error"] == "invalid_credentials"
    r = api.handle(VAULT_APP, "unlock", {"master_password": "wrong"})
    assert r["error"] == "rate_limited" and r["retry_after"] > 0
    # A correct password after the burst is still blocked until the window ends.
    assert api.handle(VAULT_APP, "unlock", {"master_password": "good-master-password"})["error"] == "rate_limited"


def test_no_secret_in_logs(api, fake, caplog):
    caplog.set_level(logging.DEBUG, logger="nuxel-keyring")
    secret = "unique-secret-value-63000"
    api.handle(VAULT_APP, "create-item", {"item": {"type": "login", "title": "T", "password": secret}})
    api.handle(AUTH_APP, "authenticator-credential-store", {"credential": secret, "consent": True})
    api.handle(AUTH_APP, "authenticator-credential-get", {})
    assert secret not in caplog.text


def test_identity_contract():
    headers = {"Origin": "http://127.0.0.1:8000",
               "Referer": "http://127.0.0.1:8000/pwa/nuxel-apps/vault/index.html"}
    session = {"app_id": VAULT_APP, "referer": headers["Referer"]}
    entry = {"capabilities": ["secrets:manage"]}
    origins = {"http://127.0.0.1:8000"}
    assert check_identity(VAULT_APP, headers, session, entry, origins) is None
    # spoofing the app_id in the body does not match the token's app
    assert check_identity(VAULT_APP, headers, {"app_id": AUTH_APP, "referer": headers["Referer"]},
                          entry, origins)["error"] == "identity_mismatch"
    assert check_identity(VAULT_APP, headers, None, entry, origins)["error"] == "token_required"
    assert check_identity(VAULT_APP, {"Origin": "http://evil.example", "Referer": headers["Referer"]},
                          session, entry, origins)["error"] == "permission_denied"
    assert check_identity(VAULT_APP, {"Origin": headers["Origin"],
                                      "Referer": "http://127.0.0.1:8000/pwa/nuxel-apps/evil/index.html"},
                          session, entry, origins)["error"] == "identity_mismatch"
    assert check_identity(VAULT_APP, headers, session, {"capabilities": []}, origins)["error"] == "permission_denied"
    assert check_identity(AUTH_APP, {"Origin": headers["Origin"],
                                     "Referer": "http://127.0.0.1:8000/pwa/nuxel-apps/authenticator/index.html"},
                          {"app_id": AUTH_APP,
                           "referer": "http://127.0.0.1:8000/pwa/nuxel-apps/authenticator/index.html"},
                          {"capabilities": ["secrets:authenticator-unlock"]}, origins) is None
    assert check_identity("org.nuxel.Home", {"Origin": headers["Origin"],
                                             "Referer": "http://127.0.0.1:8000/pwa/nuxel-home/index.html"},
                          {"app_id": "org.nuxel.Home",
                           "referer": "http://127.0.0.1:8000/pwa/nuxel-home/index.html"},
                          None, origins) is None
    assert check_identity("org.example.Evil", headers, session, entry, origins)["error"] == "permission_denied"


def test_launcher_minted_token_identity():
    origins = {"http://127.0.0.1:8000"}
    no_ref = {"Origin": "http://127.0.0.1:8000"}
    entry = {"capabilities": ["secrets:manage"]}
    session = {"app_id": VAULT_APP, "issuer": "nuxel-launcher", "referer": ""}
    assert check_identity(VAULT_APP, no_ref, session, entry, origins) is None
    # self-issued tokens still need the app-route Referer; iframe tokens do not.
    self_issued = {"app_id": VAULT_APP, "referer": ""}
    assert check_identity(VAULT_APP, no_ref, self_issued, entry, origins)["error"] == "identity_mismatch"
    assert check_identity(VAULT_APP, {"Origin": "http://evil.example"}, session, entry, origins)["error"] == "permission_denied"
    assert check_identity(VAULT_APP, no_ref, session, {"capabilities": []}, origins)["error"] == "permission_denied"
    assert check_identity(AUTH_APP, no_ref, {"app_id": AUTH_APP, "issuer": "nuxel-launcher"},
                          {"capabilities": ["secrets:authenticator-unlock"]}, origins) is None


def test_provider_without_dbus_fails_closed():
    # Host/CI may not have python3-dbus.  The provider must report unavailable,
    # never start a fake collection.
    svc = SecretService(bus_address="unix:path=/tmp/nuxel-test-no-such-bus-63000")
    st = svc.status()
    assert st["success"] is False
    assert st["state"] == "unavailable"
    assert st["available"] is False
