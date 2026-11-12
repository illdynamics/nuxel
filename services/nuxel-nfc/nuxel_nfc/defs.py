"""NDEF construction helpers shared by the daemon and its tests.

Records are built as standard NDEF bytes.  The writer layer only ever sends a
single short-record message: it is bounded, easy to verify after read-back, and
never mutates the tag's lock/access pages.
"""

from __future__ import annotations

MAX_TEXT_UTF8 = 512
MAX_URI_UTF8 = 512
MAX_MESSAGE = 2048

# NFC Forum URI Record Type Definition, Appendix A.  Prefix 0x00 is "no
# abbreviation"; only these exact values are encoded.
URI_PREFIXES = (
    "", "http://www.", "https://www.", "http://", "https://", "tel:",
    "mailto:", "ftp://anonymous:anonymous@", "ftp://ftp.", "ftps://",
    "sftp://", "smb://", "nfs://", "ftp://", "dav://", "news:",
    "telnet://", "imap:", "rtsp://", "urn:", "pop:", "sip:", "sips:",
    "tftp:", "btspp://", "btl2cap://", "btgoep://", "tcpobex://",
    "irdaobex://", "file://", "urn:epc:id:", "urn:epc:tag:",
    "urn:epc:pat:", "urn:epc:raw:", "urn:epc:", "urn:nfc:",
)


class NdefBuildError(ValueError):
    """A caller-supplied value cannot be represented safely."""


def _short_record(tnf: int, rtype: bytes, payload: bytes) -> bytes:
    if not rtype or len(rtype) > 255:
        raise NdefBuildError("record type must be 1..255 bytes")
    if len(payload) > 255:
        raise NdefBuildError("record payload must be <= 255 bytes")
    return bytes([0xD1, len(rtype), len(payload)]) + rtype + payload


def text_record(text: str, language: str = "en") -> bytes:
    """One short-record Text RTD.

    The NDEF short-record form carries at most 255 bytes of payload.  For a
    larger text the record uses the normal (4-byte length) header, which the
    parser and Type-2 writer both support.
    """
    if not isinstance(text, str):
        raise NdefBuildError("text must be a string")
    try:
        body = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise NdefBuildError("text is not valid UTF-8") from exc
    if not body:
        raise NdefBuildError("text record cannot be empty")
    if len(body) > MAX_TEXT_UTF8:
        raise NdefBuildError("text exceeds %d UTF-8 bytes" % MAX_TEXT_UTF8)
    lang = (language or "en").encode("ascii", "strict")
    if not lang or len(lang) > 63:
        raise NdefBuildError("language code must be 1..63 ASCII bytes")
    payload = bytes([len(lang)]) + lang + body
    if len(payload) <= 255:
        return _short_record(0x01, b"T", payload)
    if len(payload) > 0xFFFFFFFF:
        raise NdefBuildError("text payload is too large")
    return bytes([0xC1, 0x01]) + len(payload).to_bytes(4, "big") + b"T" + payload


def uri_record(uri: str) -> bytes:
    if not isinstance(uri, str) or not uri:
        raise NdefBuildError("uri cannot be empty")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in uri):
        raise NdefBuildError("uri contains control characters")
    try:
        body = uri.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise NdefBuildError("uri is not valid UTF-8") from exc
    if len(body) > MAX_URI_UTF8:
        raise NdefBuildError("uri exceeds %d UTF-8 bytes" % MAX_URI_UTF8)
    code = 0
    for i, prefix in enumerate(URI_PREFIXES):
        if prefix and uri.startswith(prefix):
            code = i
            body = uri[len(prefix):].encode("utf-8")
            break
    payload = bytes([code]) + body
    if len(payload) <= 255:
        return _short_record(0x01, b"U", payload)
    if len(payload) > 0xFFFFFFFF:
        raise NdefBuildError("URI payload is too large")
    return bytes([0xC1, 0x01]) + len(payload).to_bytes(4, "big") + b"U" + payload


def verify_roundtrip(payload: bytes, expected_text=None, expected_uri=None) -> dict:
    """Parse written bytes and confirm they decode to the requested value."""
    from . import ndef
    doc = ndef.parse_message(payload)
    records = doc.get("records") or []
    if len(records) != 1:
        raise NdefBuildError("read-back has %d records, want 1" % len(records))
    rec = records[0]
    if expected_text is not None:
        if rec.get("kind") != "text" or rec.get("preview") != expected_text:
            raise NdefBuildError("read-back text does not match the write")
    if expected_uri is not None:
        if rec.get("kind") != "uri" or rec.get("preview") != expected_uri:
            raise NdefBuildError("read-back URI does not match the write")
    return doc
