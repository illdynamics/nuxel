#!/usr/bin/env python3
"""PWNAGE-63000 source guards for the Vault app, Authenticator integration,
Entra guidance, registry and package manifest."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VAULT = ROOT / "pwa/nuxel-apps/vault"
AUTH = ROOT / "pwa/nuxel-apps/authenticator"


def read(path):
    return path.read_text()


def test_vault_manifest_and_registry_identity():
    m = json.loads(read(VAULT / "manifest.json"))
    assert m["nuxel"]["app_id"] == "org.nuxel.Vault"
    assert m["nuxel"]["bridge_version"] == "1"
    assert m["nuxel"]["network"] == "none"
    assert "secrets:manage" in m["nuxel"]["capabilities"]
    assert (VAULT / "index.html").exists()
    reg = json.loads(read(ROOT / "pwa/nuxel-common/app-registry.json"))
    app = next(a for a in reg["apps"] if a["id"] == "org.nuxel.Vault")
    assert app["capabilities"] == ["secrets:manage"]
    auth = next(a for a in reg["apps"] if a["id"] == "org.nuxel.Authenticator")
    assert "secrets:authenticator-unlock" in auth["capabilities"]


def test_vault_never_persists_secrets_in_browser_storage():
    js = read(VAULT / "js/app.js")
    assert "localStorage.setItem(AUTO_LOCK_KEY" in js
    assert "localStorage.setItem(LOCK_ON_HIDE_KEY" in js
    for bad in ("sessionStorage.", "indexedDB.", "caches.open(", "localStorage.setItem('nuxel-vault-item"):
        assert bad not in js
    # no secrets in the URL/hash
    assert "location.hash" not in js and "history.pushState" not in js


def test_vault_ui_uses_textcontent_for_secret_fields():
    js = read(VAULT / "js/app.js")
    assert "textContent" in js
    assert "innerHTML" not in js
    assert "password" in js and "notes" in js


def test_vault_service_worker_never_caches_api_or_secrets():
    sw = read(VAULT / "sw.js")
    assert "nuxel-vault-v2-p63000" in sw
    assert "/api/" in sw and "/rpc" in sw and "/auth/" in sw
    assert "req.method !== 'GET'" in sw
    assert "c.put" in sw


def test_vault_has_no_external_network_or_cdn():
    production = [VAULT / "index.html", VAULT / "css/vault.css", VAULT / "sw.js",
                  VAULT / "js/app.js", VAULT / "js/archive.js", VAULT / "js/pwgen.js"]
    for path in production:
        text = read(path)
        for bad in ('src="https://', 'href="https://', "http://cdn", "fonts.googleapis",
                    "googletagmanager", "google-analytics", "Math.random"):
            assert bad not in text, (path, bad)
    html = read(VAULT / "index.html")
    assert "Content-Security-Policy" in html
    assert "connect-src http://127.0.0.1:8080" in html


def test_authenticator_keyring_integration_source_guards():
    js = read(AUTH / "js/authenticator.js")
    for needle in ("NuxelBridge.keyring", "authenticator-credential-status",
                   "authenticator-credential-store", "authenticator-credential-get",
                   "authenticator-credential-delete", "kr-consent",
                   "DELETE AUTHENTICATOR VAULT", "clearOtpClipboardIfSame"):
        assert needle in js
    # immediate lock on background; codes are cleared from the DOM
    assert "if (document.hidden && state.key)" in js
    assert "el('codes').textContent = ''" in js
    assert "setTimeout(function () { bgLock" not in js
    # no plaintext credential in localStorage
    assert "nuxel-authenticator-envelope-v1" in js  # ciphertext envelope only
    assert "localStorage.setItem(KEY, JSON.stringify(env))" in js
    assert "authenticator-credential" not in read(AUTH / "js/vault.js")


def test_authenticator_service_worker_never_caches_api():
    sw = read(AUTH / "sw.js")
    assert "nuxel-authenticator-v4-p63000" in sw
    assert "/api/" in sw and "/rpc" in sw and "/auth/" in sw
    assert "req.method !== 'GET'" in sw


def test_entra_guidance_is_truthful():
    html = read(AUTH / "index.html")
    doc = read(AUTH / "ENTRA-OATH.md")
    assert "Standard TOTP only" in html
    assert "push approval" in html and "number matching" in html
    assert "third-party software OATH" in html or "third-party software OATH" in doc
    assert "Conditional Access" in doc and "phishing-resistant" in doc
    for false_claim in ("Push enabled", "Microsoft Authenticator registered", "Device registered"):
        assert false_claim not in html


def test_node_archive_and_generator_tests():
    node = shutil.which("node")
    if not node:
        pytest.skip("node unavailable")
    for script in (VAULT / "tests/test-archive.js", VAULT / "tests/test-pwgen.js"):
        r = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stdout + r.stderr


def test_registry_verifier():
    r = subprocess.run(["python3", str(ROOT / "tools/s10plus/a33/verify-app-registry.py")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "problems=0" in (r.stdout + r.stderr)


def test_nuxtore_catalog_verifier():
    r = subprocess.run(["python3", str(ROOT / "pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert "org.nuxel.Vault" in out and "SIGNED_VERIFIED" in out
    assert "org.nuxel.Authenticator" in out and "SIGNED_VERIFIED" in out


def test_s10plus_package_manifest_has_secret_service():
    doc = json.loads(read(ROOT / "images/s10plus/packages-manifest.json"))
    assert doc["verdict"] == "resolved"
    packages = doc.get("packages") or doc.get("resolved") or {}
    text = json.dumps(doc)
    for name in ("gnome-keyring", "gcr3", "libsecret"):
        assert name in text
    assert doc.get("pin_mismatches") == []


def test_launcher_token_relay_source_guards():
    home = read(ROOT / "pwa/nuxel-home/js/app.js")
    bridge = read(ROOT / "pwa/nuxel-common/bridge.js")
    host = read(ROOT / "tools/s10plus/a45/nuxel-pwa-host.c")
    assert "nuxel-keyring-token-request" in home
    assert "nuxel-keyring-mint" in home
    assert "NuxelKeyringRelay.attach(frame, app.id)" in home
    assert "nuxel-keyring-token-request" in bridge
    assert "_keyringLauncherToken" in bridge
    assert "keyring_mint_attach" in host
    assert "NUXEL_KEYRING_MINT" in host
    assert "WEBKIT_USER_CONTENT_INJECT_TOP_FRAME" in host
    assert "/etc/nuxel/keyring-launcher.secret" in host


def test_bridge_service_has_session_bus_and_keyring_write_paths():
    unit = read(ROOT / "services/nuxel-bridge/systemd/nuxel-http-bridge.service")
    assert "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/nuxel-wayland/bus" in unit
    assert "XDG_RUNTIME_DIR=/run/nuxel-wayland" in unit
    assert "/root/.local/share/keyrings" in unit
    session = read(ROOT / "tools/s10plus/a45/nuxel-session.sh")
    assert "dbus-update-activation-environment" in session
    assert "org.freedesktop.secrets" in session
