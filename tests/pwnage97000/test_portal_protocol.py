"""PWNAGE-97000 portal protocol / live-dispatch contract tests.

The live physical evidence is under docs/pwnage-97000/evidence/<stamp>/.
These checks keep the exact frontend/backend contract, document grant path and
the no-fake-success rules from regressing on a clean checkout.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def test_frontend_dispatch_is_the_xdg_filechooser_not_the_private_broker():
    session = read("tools/s10plus/a45/nuxel-session.sh")
    assert "/usr/libexec/xdg-desktop-portal" in session
    assert "/usr/libexec/nuxel/nuxel-portal-chooser" in session
    chooser = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    policy = read("services/nuxel-file-handlers/src/nuxel_file_handlers.py")
    assert "org.freedesktop.portal.FileChooser" in policy
    assert "org.freedesktop.impl.portal.FileChooser" in chooser
    assert "org.nuxel.Portal" in chooser
    assert "FileChooser" not in read("services/nuxel-portal/src/portal.py")


def test_portal_signatures_and_response_codes_are_real():
    chooser = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    for token in ('in_signature="osssa{sv}"', 'out_signature="ua{sv}"',
                  'async_callbacks=("reply", "error")',
                  'reply(dbus.UInt32(2 if code not in (0, 1) else 1)',
                  'reply(dbus.UInt32(0), dbus.Dictionary(results, signature="sv"))'):
        assert token in chooser, token


def test_document_portal_is_started_and_grants_are_per_request():
    session = read("tools/s10plus/a45/nuxel-session.sh")
    assert "xdg-document-portal" in session
    assert "/run/user/1000/doc" in session or "$USER_RUNTIME/doc" in session
    chooser = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    assert "writable" in chooser
    assert "file_uri(path)" in chooser


def test_no_fake_media_or_hung_request_paths():
    chooser = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    assert "never fabricates a file URI" in chooser
    assert "REQUEST_TIMEOUT_S" in chooser
    assert "MAX_ACTIVE_REQUESTS" in chooser
    for forbidden in ("data:image", "sample.png", "sample.jpg"):
        assert forbidden not in chooser


def test_live_evidence_records_frontend_app_ids_and_grants():
    roots = sorted((ROOT / "docs/pwnage-97000/evidence").glob("*/portal"))
    assert roots, "no live portal evidence directory"
    text = "\n".join(p.read_text(errors="replace") for p in roots[-1].glob("*.txt"))
    for app_id in ("org.ferdium.Ferdium", "org.signal.Signal", "com.rtosta.zapzap"):
        assert app_id in text
    assert "/run/user/1000/doc/" in text
