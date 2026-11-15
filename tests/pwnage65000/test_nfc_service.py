import json
import os
import re
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "services", "nuxel-nfc"))

from nuxel_nfc import abi, defs, ndef, nci  # noqa: E402
from nuxel_nfc.daemon import NfcDaemon  # noqa: E402
from nuxel_nfc.transport import MockTransport, TransportError  # noqa: E402


def test_ioctl_numbers_match_pinned_header():
    header = open(os.path.join(ROOT, "kernel/s10plus/.build/src/drivers/nfc/sec_nfc.h")).read()
    assert "SEC_NFC_MAX_BUFFER_SIZE\t512" in header
    assert "SEC_NFC_MSG_MAX_SIZE\t(256 + 4)" in header
    assert "#define SEC_NFC_GET_MODE\t\t_IOW(SEC_NFC_MAGIC, 0, unsigned int)" in header
    assert abi.SEC_NFC_GET_MODE == 0x40045300
    assert abi.SEC_NFC_SET_MODE == 0x40045301
    assert abi.SEC_NFC_SLEEP == 0x40045302
    assert abi.SEC_NFC_WAKEUP == 0x40045303
    assert abi.SEC_NFC_SET_NPT_MODE == 0x40045304
    assert abi.SEC_NFC_DEBUG == 0x00005363
    assert abi.MODE_FIRMWARE == 1 and abi.MODE_BOOTLOADER == 2


def test_nci_framing_and_reassembly():
    assert nci.command(0, 0, b"\x00") == b"\x20\x00\x01\x00"
    assert nci.build_discover_a() == b"\x21\x03\x04\x01\x00\x01\x00"
    frame = nci.command(0, 0x02, b"abc")
    tr = MockTransport([frame[:2], frame[2:]])
    msg = nci.NciController(tr).receive(1.0)
    assert msg["mt"] == nci.MT_COMMAND and msg["payload"] == b"abc"
    with pytest.raises(nci.NciError):
        nci.parse_header(b"\x30\x00\x00")


def test_nci_rejects_fragmented_and_oversize():
    assert nci.parse_header(b"\x20\x00\x00")["length"] == 0
    with pytest.raises(nci.NciError):
        nci.parse_header(b"\x30\x00\x00")
    with pytest.raises(nci.NciError):
        nci.command(0, 0, b"x" * 256)


def _text_message():
    return bytes([0xD1, 0x01, 0x05]) + b"T" + bytes([0x02]) + b"en" + b"hi"


def test_ndef_valid_text_and_uri():
    doc = ndef.parse_message(_text_message())
    assert doc["record_count"] == 1
    assert doc["records"][0]["kind"] == "text"
    assert doc["records"][0]["preview"] == "hi"
    assert doc["writes_supported"] is False
    uri = bytes([0xD1, 0x01, 0x09]) + b"U" + bytes([0x04]) + b"http://x"
    doc = ndef.parse_message(uri)
    assert doc["records"][0]["kind"] == "uri"
    assert doc["records"][0]["actionable"] is True
    js = bytes([0xD1, 0x01, 0x0D]) + b"U" + bytes([0x00]) + b"javascript:x"
    doc = ndef.parse_message(js)
    assert doc["records"][0]["actionable"] is False


@pytest.mark.parametrize("blob", [
    b"", b"\xd1", b"\x91\x01\x02T\x05", b"\xd1\x01\xffT",
    b"\xd1\x01\x80T" + b"A" * 10,
    b"\xd1\x01\x01T\x00\x00\x00\x00",  # data after ME
])
def test_ndef_rejects_malformed(blob):
    with pytest.raises(ndef.NdefError):
        ndef.parse_message(blob)


def test_ndef_vcard_is_not_imported():
    payload = b"BEGIN:VCARD\nEND:VCARD"
    rec = bytes([0xD1, 0x01, len(payload)]) + b"V" + payload
    doc = ndef.parse_message(rec)
    assert doc["records"][0]["kind"] == "vcard"
    assert "not imported" in doc["records"][0]["preview"]


def test_mock_transport_partial_read_and_write():
    frame = b"\x40\x00\x01\x00"
    tr = MockTransport([frame[:1], frame[1:]])
    assert tr.read_exact(2) == b"\x40\x00"
    assert tr.read_exact(2) == b"\x01\x00"
    tr.write(b"xyz")
    assert tr.writes == [b"xyz"]
    with pytest.raises(TransportError):
        tr.read_exact(1)


def _frames():
    return [
        b"\x40\x00\x03\x00\x01\x00",          # CORE_RESET_RSP
        b"\x40\x01\x02\x00\x00",                # CORE_INIT_RSP
        b"\x41\x00\x01\x00",                    # RF_DISCOVER_MAP_RSP
        b"\x41\x03\x01\x00",                    # RF_DISCOVER_RSP
        b"\x61\x05\x08\x00\x01\x01\x04\x04\x00\x00\x00",  # RF_INTF_ACTIVATED_NTF
    ]


def test_daemon_default_off_and_enable_scan(tmp_path):
    tr = MockTransport(_frames())
    d = NfcDaemon(transport=tr, root=str(tmp_path), state_path=str(tmp_path / "state.json"))
    assert d.status()["state"] == "OFF"
    assert d.status()["enabled"] is False
    out = d.enable()
    assert out["success"] is True and out["state"] == "READY"
    assert tr.open_count == 1
    out = d.scan(timeout_s=2, read_ndef=False)
    assert out["success"] is True
    assert out["tag"]["technology"] == "NFC-A"
    assert tr.writes[0] == b"\x20\x00\x01\x00"
    assert tr.writes[1] == b"\x20\x01\x01\x00"
    out = d.disable()
    assert out["state"] == "OFF" and tr.close_count == 1


def test_daemon_scan_requires_enable(tmp_path):
    d = NfcDaemon(transport=MockTransport([]), root=str(tmp_path),
                  state_path=str(tmp_path / "s.json"))
    out = d.scan()
    assert out["success"] is False and out["error_code"] == "NOT_ENABLED"


def test_daemon_busy_maps_to_structured_error(tmp_path):
    tr = MockTransport([])
    tr.fail_next = "open"
    d = NfcDaemon(transport=tr, root=str(tmp_path), state_path=str(tmp_path / "s.json"))
    out = d.enable()
    assert out["success"] is False and out["error_code"] == "BUSY"
    assert d.status()["state"] == "ERROR"


def test_type2_ndef_read_is_bounded():
    cc = bytes([0xE1, 0x10, 0x02, 0x00] + [0] * 12)
    page4 = bytes([0x03, 0x09, 0xD1, 0x01, 0x05, 0x54, 0x02, 0x65, 0x6E, 0x68, 0x69] + [0] * 5)
    frames = [
        b"\x61\x05\x08\x00\x01\x01\x04\x04\x00\x00\x00",
        b"\x41\x04\x12\x00\x10" + cc,
        b"\x41\x04\x12\x00\x10" + page4,
    ]
    ctrl = nci.NciController(MockTransport(frames))
    ctrl.initialized = True
    ctrl.wait_activation(1.0)
    raw = nci.read_type2_ndef(ctrl)
    doc = ndef.parse_message(raw)
    assert doc["records"][0]["preview"] == "hi"


def test_service_never_uses_vendor_bootloader_or_npt():
    src = open(os.path.join(ROOT, "services/nuxel-nfc/nuxel_nfc/daemon.py")).read()
    assert "MODE_BOOTLOADER" not in src
    assert "SET_NPT_MODE" not in src


def test_ndef_text_and_uri_encoder_roundtrip():
    rec = defs.text_record("Nuxel NFC")
    doc = ndef.parse_message(rec)
    assert doc["records"][0]["kind"] == "text"
    assert doc["records"][0]["preview"] == "Nuxel NFC"
    uri = defs.uri_record("https://nuxel.local/tag")
    doc = ndef.parse_message(uri)
    assert doc["records"][0]["kind"] == "uri"
    assert doc["records"][0]["preview"] == "https://nuxel.local/tag"


def test_ndef_encoder_rejects_too_long_payloads():
    with pytest.raises(defs.NdefBuildError):
        defs.text_record("x" * 600)
    with pytest.raises(defs.NdefBuildError):
        defs.text_record("")
    with pytest.raises(defs.NdefBuildError):
        defs.uri_record("https://example.test/" + "a" * 600)


def test_type2_ndef_image_layout_short_and_long():
    rec = defs.text_record("Nuxel NFC")
    img = nci.build_type2_ndef_image(rec, 180)
    assert img[:2] == bytes([0x03, len(rec)])
    assert len(img) % 4 == 0
    assert img[len(rec) + 2] == 0xFE
    long_rec = defs.text_record("x" * 300)
    img = nci.build_type2_ndef_image(long_rec, 888)
    assert img[:2] == b"\x03\xff"
    assert int.from_bytes(img[2:4], "big") == len(long_rec)


class _Type2Mock:
    def __init__(self, cc=None, read_only=False):
        self.pages = {3: bytearray(cc or (bytes([0xE1, 0x10, 0x12,
                                                0xC2 if read_only else 0x00]) +
                                         b"\x00" * 12))}
        self.writes = 0

    def transceive(self, cmd, timeout_s=1.5):
        if cmd[0] == 0x30:
            out = bytearray()
            for p in range(cmd[1], cmd[1] + 4):
                out += self.pages.get(p, bytearray(4))
            return bytes(out)
        if cmd[0] == 0xA2:
            self.writes += 1
            self.pages[cmd[1]] = bytearray(cmd[2:6])
            return b"\x0a\x00\x00\x00"
        raise AssertionError("unexpected command %r" % (cmd,))


def test_type2_write_and_readback_match():
    mock = _Type2Mock()
    msg = defs.text_record("hello tag")
    nci.write_type2_ndef(mock, msg)
    assert nci.verify_type2_write(mock, msg)["verified"] is True


def test_type2_refuses_lock_otp_and_read_only():
    mock = _Type2Mock()
    with pytest.raises(nci.NciError) as exc:
        nci.type2_write_pages(mock, 2, b"\x00" * 4)
    assert exc.value.code == "TYPE2_PROTECTED_PAGE"
    ro = _Type2Mock(read_only=True)
    with pytest.raises(nci.NciError) as exc:
        nci.write_type2_ndef(ro, defs.text_record("nope"))
    assert exc.value.code == "TYPE2_READ_ONLY"
    assert ro.writes == 0


def test_type2_write_verifies_mismatch():
    mock = _Type2Mock()
    msg = defs.text_record("hello tag")
    nci.write_type2_ndef(mock, msg)
    with pytest.raises(nci.NciError) as exc:
        nci.verify_type2_write(mock, defs.text_record("different"))
    assert exc.value.code == "TYPE2_VERIFY_FAILED"


def test_daemon_write_requires_confirmation_and_tag(tmp_path):
    d = NfcDaemon(transport=MockTransport([]), root=str(tmp_path),
                  state_path=str(tmp_path / "state.json"))
    out = d.write_tag("text", "x", confirmed=False)
    assert out["success"] is False and out["error_code"] == "CONFIRMATION_REQUIRED"
    out = d.write_tag("text", "x", confirmed=True)
    assert out["success"] is False and out["error_code"] == "NO_TAG"


def test_daemon_dispatch_rejects_unconfirmed_write(tmp_path, monkeypatch):
    # dispatch() is the socket entry point: it authorises the caller against the
    # shared grant store first (fail closed without an app_id), then applies the
    # write confirmation policy.  Grant a test app so this test exercises the
    # confirmation path, and assert the unauthenticated case separately.
    from nuxel_nfc import policy
    monkeypatch.setattr(policy, "PERMISSIONS_DIR", str(tmp_path), raising=False)
    (tmp_path / "org.nuxel.Test.json").write_text(json.dumps(
        {"nfc": {"duration": "always", "granted": True}}))
    d = NfcDaemon(transport=MockTransport([]), root=str(tmp_path),
                  state_path=str(tmp_path / "state.json"))
    out = d.dispatch("write", {"kind": "text", "value": "hello"},
                     app_id="org.nuxel.Test")
    assert out["success"] is False and out["error_code"] == "CONFIRMATION_REQUIRED"
    out = d.dispatch("write", {"kind": "text", "value": "hello", "confirm": True},
                     app_id="org.nuxel.Test")
    assert out["success"] is False and out["error_code"] == "NO_TAG"


def test_daemon_dispatch_without_app_id_fails_closed(tmp_path):
    d = NfcDaemon(transport=MockTransport([]), root=str(tmp_path),
                  state_path=str(tmp_path / "state.json"))
    out = d.dispatch("write", {"kind": "text", "value": "hello"})
    assert out["success"] is False and out["error_code"] == "EPERM"


def test_nfc_uapi_numbers_match_pinned_header():
    header = open(os.path.join(ROOT, "kernel/s10plus/.build/src/include/uapi/linux/nfc.h")).read()
    assert "NFC_CMD_START_POLL," in header
    assert "NFC_CMD_GET_TARGET," in header
    from nuxel_nfc import kernel_nci
    assert kernel_nci.NFC_CMD_START_POLL == 6
    assert kernel_nci.NFC_CMD_STOP_POLL == 7
    assert kernel_nci.NFC_CMD_GET_TARGET == 8
    assert kernel_nci.NFC_ATTR_DEVICE_INDEX == 1
    assert kernel_nci.NFC_ATTR_IM_PROTOCOLS == 13
    assert kernel_nci.NFC_ATTR_TARGET_NFCID1 == 7


def test_daemon_uses_kernel_nci_path(tmp_path):
    class FakeNci:
        def __init__(self):
            self.calls = []
            self.target_idx = None
        def open(self):
            self.calls.append("open")
        def start_poll(self, timeout_s=10.0):
            self.calls.append("start_poll")
            return {"polling": True}
        def targets(self, timeout_s=2.0):
            return [{"target_index": 0, "protocols": 16, "uid": "04:A1:B2:C3"}]
        def close(self):
            self.calls.append("close")
        def transceive(self, data, timeout_s=1.5):
            raise AssertionError("kernel NCI target transceive is exercised on device")
    fake = FakeNci()
    d = NfcDaemon(transport=None, root=str(tmp_path), kernel=fake,
                  state_path=str(tmp_path / "state.json"))
    st = d.status()
    assert st["kernel_nci"]["present"] is True
    assert st["tag_writes_supported"] is True and st["write_requires_confirmation"] is True
    out = d.enable()
    assert out["success"] is True and fake.calls[:2] == ["open", "start_poll"]
    out = d.disable()
    assert out["state"] == "OFF" and "close" in fake.calls
