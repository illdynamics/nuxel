"""Hardened, read-only NDEF parser for untrusted tag payloads.

The parser never opens URLs, imports contacts, executes commands or renders
HTML.  It returns bounded metadata plus a plain-text preview.  Every length is
checked before slicing and malformed input raises :class:`NdefError`.
"""

from __future__ import annotations

import unicodedata

MAX_MESSAGE = 8192
MAX_RECORD = 4096
MAX_RECORDS = 32

TNF_NAMES = {
    0x00: "empty",
    0x01: "well-known",
    0x02: "media",
    0x03: "absolute-uri",
    0x04: "external",
    0x05: "unknown",
    0x06: "unchanged",
    0x07: "reserved",
}

# Only well-known, harmless URI prefixes are expanded. Unknown schemes are
# returned as inert text and never auto-opened.
URI_PREFIXES = (
    "", "http://www.", "https://www.", "http://", "https://", "tel:",
    "mailto:", "ftp://anonymous:anonymous@", "ftp://ftp.", "ftps://",
    "sftp://", "smb://", "nfs://", "ftp://", "dav://", "news:",
    "telnet://", "imap:", "rtsp://", "urn:", "pop:", "sip:", "sips:",
    "tftp:", "btspp://", "btl2cap://", "btgoep://", "tcpobex://",
    "irdaobex://", "file://", "urn:epc:id:", "urn:epc:tag:",
    "urn:epc:pat:", "urn:epc:raw:", "urn:epc:", "urn:nfc:",
)

_SAFE_SCHEMES = ("http:", "https:", "mailto:", "tel:")


class NdefError(ValueError):
    """Malformed or unsupported NDEF input."""


def _clean_text(text: str, limit: int = 512) -> str:
    out = []
    for ch in text[:limit]:
        if ch in "\n\r\t":
            out.append(" ")
        elif unicodedata.category(ch)[0] == "C":
            out.append("?")
        else:
            out.append(ch)
    return "".join(out)


def _decode_uri(payload: bytes) -> tuple[str, bool]:
    if not payload:
        raise NdefError("URI record has no prefix byte")
    code = payload[0]
    if code >= len(URI_PREFIXES):
        return _clean_text(payload[1:].decode("utf-8", "replace")), False
    text = URI_PREFIXES[code] + payload[1:].decode("utf-8", "strict")
    low = text.lower()
    safe = low.startswith(_SAFE_SCHEMES)
    return _clean_text(text), safe


def _decode_text(payload: bytes) -> str:
    if not payload:
        raise NdefError("text record has no status byte")
    status = payload[0]
    lang_len = status & 0x3F
    if 1 + lang_len > len(payload):
        raise NdefError("text record language length exceeds payload")
    try:
        raw = payload[1 + lang_len:]
        if status & 0x80:
            text = raw.decode("utf-16", "strict")
        else:
            text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise NdefError("invalid text encoding: %s" % exc) from exc
    return _clean_text(text)


def _parse_records(buf: bytes):
    records = []
    pos = 0
    seen_mb = False
    saw_me = False
    while pos < len(buf):
        if len(records) >= MAX_RECORDS:
            raise NdefError("too many NDEF records")
        if pos + 3 > len(buf):
            raise NdefError("truncated record header")
        header = buf[pos]
        mb = bool(header & 0x80)
        me = bool(header & 0x40)
        cf = bool(header & 0x20)
        sr = bool(header & 0x10)
        il = bool(header & 0x08)
        tnf = header & 0x07
        if mb and seen_mb:
            raise NdefError("multiple MB records")
        if mb:
            seen_mb = True
        if saw_me:
            raise NdefError("data after ME record")
        if tnf == 0x07:
            raise NdefError("reserved TNF")
        type_len = buf[pos + 1]
        p = pos + 2
        if sr:
            if p + 1 > len(buf):
                raise NdefError("truncated short payload length")
            payload_len = buf[p]
            p += 1
        else:
            if p + 4 > len(buf):
                raise NdefError("truncated payload length")
            payload_len = int.from_bytes(buf[p:p + 4], "big")
            p += 4
        id_len = 0
        if il:
            if p + 1 > len(buf):
                raise NdefError("truncated ID length")
            id_len = buf[p]
            p += 1
        if type_len > 255 or id_len > 255:
            raise NdefError("type/ID length out of range")
        total = type_len + id_len + payload_len
        if payload_len > MAX_RECORD or total > MAX_RECORD:
            raise NdefError("record exceeds size limit")
        if p + total > len(buf):
            raise NdefError("record length exceeds message")
        rtype = bytes(buf[p:p + type_len])
        p += type_len
        rid = bytes(buf[p:p + id_len])
        p += id_len
        payload = bytes(buf[p:p + payload_len])
        p += payload_len
        if cf and me:
            raise NdefError("chunked record cannot set ME")
        records.append({
            "tnf": tnf,
            "tnf_name": TNF_NAMES.get(tnf, "reserved"),
            "type": rtype,
            "id": rid,
            "payload": payload,
            "chunked": cf,
            "begin": mb,
            "end": me,
        })
        pos = p
        if me:
            saw_me = True
    if not saw_me:
        raise NdefError("message has no ME record")
    if records and not records[0]["begin"]:
        raise NdefError("first record does not set MB")
    return records


def _merge_chunks(records):
    out = []
    pending = None
    for rec in records:
        if pending is None and rec["chunked"]:
            pending = dict(rec)
            pending["payload"] = bytearray(rec["payload"])
            continue
        if pending is not None:
            if rec["tnf"] != pending["tnf"] or rec["type"] != pending["type"]:
                raise NdefError("chunk type mismatch")
            pending["payload"].extend(rec["payload"])
            if len(pending["payload"]) > MAX_RECORD:
                raise NdefError("chunked payload exceeds limit")
            if not rec["chunked"]:
                pending["payload"] = bytes(pending["payload"])
                pending["chunked"] = False
                out.append(pending)
                pending = None
            continue
        out.append(rec)
    if pending is not None:
        raise NdefError("unterminated chunked record")
    return out


def parse_message(buf: bytes):
    if not isinstance(buf, (bytes, bytearray)):
        raise NdefError("NDEF message must be bytes")
    buf = bytes(buf)
    if not buf:
        raise NdefError("empty NDEF message")
    if len(buf) > MAX_MESSAGE:
        raise NdefError("message exceeds %d bytes" % MAX_MESSAGE)
    merged = _merge_chunks(_parse_records(buf))
    out = []
    for rec in merged:
        tnf = rec["tnf"]
        rtype = rec["type"]
        payload = rec["payload"]
        kind = "unknown"
        preview = _clean_text(payload[:256].hex())
        safe_action = False
        if tnf == 0x00:
            kind = "empty"
            preview = ""
        elif tnf == 0x01 and rtype == b"T":
            kind = "text"
            preview = _decode_text(payload)
        elif tnf == 0x01 and rtype == b"U":
            kind = "uri"
            preview, safe_action = _decode_uri(payload)
        elif tnf == 0x01 and rtype == b"Sp":
            kind = "smart-poster"
            preview = "(smart poster; not imported)"
        elif tnf == 0x01 and rtype in (b"V", b"vCard"):
            kind = "vcard"
            preview = "(vCard; not imported)"
        elif tnf == 0x01 and rtype in (b"T", b"U", b"Sp", b"V"):
            kind = "well-known"
        out.append({
            "tnf": tnf,
            "tnf_name": rec["tnf_name"],
            "type": rtype.decode("ascii", "replace")[:32],
            "kind": kind,
            "id_hex": rec["id"].hex(),
            "payload_length": len(payload),
            "preview": preview,
            "actionable": safe_action,
        })
    return {
        "record_count": len(out),
        "records": out,
        "has_text": any(r["kind"] == "text" for r in out),
        "has_uri": any(r["kind"] == "uri" for r in out),
        "writes_supported": False,
    }
