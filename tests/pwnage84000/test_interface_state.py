"""Offline checks for the durable interface ON/OFF document (P84000 follow-up).

Run from the repository root:
    python3 -m pytest -q tests/pwnage84000/test_interface_state.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "nuxel-bridge" / "src"))
import interface_state  # noqa: E402


def test_missing_document_uses_safe_defaults(tmp_path):
    path = tmp_path / "interfaces.json"
    doc = interface_state.read(str(path))
    assert doc["interfaces"]["bluetooth"]["enabled"] is False
    assert doc["interfaces"]["nfc"]["enabled"] is False
    assert doc["interfaces"]["gps"]["enabled"] is False
    assert not path.exists(), "a read must not create a durable decision"


def test_set_is_atomic_and_round_trips(tmp_path):
    path = tmp_path / "interfaces.json"
    entry = interface_state.set_desired("bluetooth", True, source="test", path=str(path))
    assert entry["enabled"] is True
    assert interface_state.get("bluetooth", path=str(path)) is True
    on_disk = json.loads(path.read_text())
    assert on_disk["schema_version"] == interface_state.SCHEMA_VERSION
    assert on_disk["interfaces"]["bluetooth"]["source"] == "test"
    assert on_disk["interfaces"]["nfc"]["enabled"] is False
    assert not list(tmp_path.glob("*.tmp.*")), "atomic write left a temp file"


def test_one_interface_does_not_clobber_another(tmp_path):
    path = tmp_path / "interfaces.json"
    interface_state.set_desired("bluetooth", True, path=str(path))
    interface_state.set_desired("nfc", True, path=str(path))
    interface_state.set_desired("bluetooth", False, path=str(path))
    assert interface_state.get("bluetooth", path=str(path)) is False
    assert interface_state.get("nfc", path=str(path)) is True


def test_unknown_interface_is_rejected(tmp_path):
    try:
        interface_state.set_desired("modem", True, path=str(tmp_path / "x.json"))
    except ValueError:
        pass
    else:
        raise AssertionError("unknown interface must not create an entry")
