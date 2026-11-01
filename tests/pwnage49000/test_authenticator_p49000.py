#!/usr/bin/env python3
"""PWNAGE-49000 Authenticator source guards (offline)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "pwa/nuxel-apps/authenticator"


def read(name):
    return (APP / name).read_text()


def test_bundled_qr_decoder_and_controls():
    assert (APP / "vendor/jsQR.js").stat().st_size > 100_000
    assert (APP / "vendor/jsQR.LICENSE.txt").exists()
    html = read("index.html")
    assert "vendor/jsQR.js" in html
    for ctl in ("qr-camera", "qr-image", "qr-image-btn", "qr-preview", "qr-add"):
        assert 'id="%s"' % ctl in html


def test_camera_decode_is_local_and_stopped():
    js = read("js/authenticator.js")
    assert "navigator.mediaDevices.getUserMedia" in js
    assert "window.jsQR(data.data" in js
    assert "tr.stop()" in js
    assert "pagehide" in js and "visibilitychange" in js
    assert "fetch(" not in js and "XMLHttpRequest" not in js and "WebSocket" not in js


def test_clipboard_failure_never_prints_code():
    js = read("js/authenticator.js")
    assert "the code is " not in js
    assert "Clipboard refused; the code was not copied" in js
    assert "Clipboard unavailable; the code was not copied" in js


def test_listeners_bind_per_iteration_account():
    js = read("js/authenticator.js")
    assert "for (let i = 0; i < list.length; i++)" in js
    assert "const a = list[i];" in js
    assert "for (var i = 0; i < list.length; i++)" not in js


def test_account_ids_are_random_and_opaque():
    js = read("js/vault.js")
    assert "getRandomValues" in js
    assert "String(a.secret).slice(0, 6)" not in js
    assert "'acct-' + hex" in js


def test_entra_truthful_labels():
    html = read("index.html")
    doc = read("ENTRA-OATH.md")
    assert "Standard TOTP only" in html
    assert "push approval" in html and "number matching" in html
    assert "software OATH" in doc and "Conditional Access" in doc


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except AssertionError as e:
                fails.append(name); print("FAIL", name, e)
    print("AUTHENTICATOR P49000:", "ALL PASS" if not fails else "FAILURES")
    raise SystemExit(1 if fails else 0)
