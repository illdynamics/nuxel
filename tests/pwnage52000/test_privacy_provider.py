import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))
import privacy_provider as pp  # noqa: E402


def test_camera_gate_roundtrip(monkeypatch, tmp_path):
    doc = tmp_path / 'camera.json'
    monkeypatch.setattr(pp, 'CAMERA_DOC', str(doc))
    p = pp.PrivacyProvider()
    assert p.camera_status()['blocked'] is False
    st = p.set_camera_blocked(True)
    assert st['blocked'] is True and st['state'] == 'BLOCKED'
    assert pp.camera_capture_blocked() is True
    st = p.set_camera_blocked(False)
    assert st['blocked'] is False
    assert pp.camera_capture_blocked() is False


def test_microphone_gate_persists_even_without_sources(monkeypatch, tmp_path):
    doc = tmp_path / 'microphone.json'
    monkeypatch.setattr(pp, 'MIC_DOC', str(doc))
    p = pp.PrivacyProvider()
    monkeypatch.setattr(p, '_sources', lambda: ([], None))
    monkeypatch.setattr(p, '_apply_mute', lambda muted: 0)
    st = p.set_microphone_muted(True)
    assert st['muted'] is True
    assert st['supported'] is False
    assert st['state'] == 'UNSUPPORTED_NO_CAPTURE_SOURCE'
    assert doc.exists()


def test_camera_status_never_claims_capture_verified():
    p = pp.PrivacyProvider()
    st = p.camera_status()
    assert st['capture_supported'] is False
    assert st['scope']
