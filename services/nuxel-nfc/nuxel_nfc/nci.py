"""Minimal, bounded NCI controller for the Samsung sec-nfc raw transport.

Only normal-mode NCI operations are implemented.  Firmware download, BOOTLOADER
mode, NPT/test mode and secure-element access deliberately do not exist here.

The Samsung misc driver is a raw I2C transport, not a registered Linux NCI
adapter.  Every packet therefore needs explicit framing: the transport reads the
3-octet NCI header first and then exactly the advertised payload length.
"""

from __future__ import annotations

import select
import time

from . import abi

# NCI message types (MT) and groups (GID).
MT_COMMAND = 1
MT_RESPONSE = 2
MT_NOTIFICATION = 3

GID_CORE = 0
GID_RF = 1

CORE_RESET = 0
CORE_INIT = 1
RF_DISCOVER_MAP = 0
RF_DISCOVER = 3
RF_TRANSCEIVE = 4

RF_DISCOVER_NTF = 3
RF_INTF_ACTIVATED_NTF = 5
RF_DEACTIVATE_NTF = 6

# NCI RF technologies / protocols.
NFC_A = 0x01
NFC_A_PASSIVE_POLL = 0x00


class NciError(RuntimeError):
    def __init__(self, message, code="NCI_ERROR"):
        super().__init__(message)
        self.code = code


def packet(mt, gid, oid, payload=b""):
    if mt not in (MT_COMMAND, MT_RESPONSE, MT_NOTIFICATION):
        raise NciError("invalid message type", "NCI_BAD_MT")
    if len(payload) > 255:
        raise NciError("NCI payload too long", "NCI_OVERSIZE")
    return bytes([(mt << 5) | (gid & 0x0F), oid & 0xFF, len(payload)]) + bytes(payload)


def command(gid, oid, payload=b""):
    return packet(MT_COMMAND, gid, oid, payload)


def parse_header(hdr):
    if len(hdr) != 3:
        raise NciError("short NCI header", "NCI_SHORT_HEADER")
    mt = (hdr[0] >> 5) & 0x07
    gid = hdr[0] & 0x0F
    pbf = bool(hdr[0] & 0x10)
    if mt == 0:
        raise NciError("NCI data packets are not accepted on the control path", "NCI_DATA_PACKET")
    if pbf:
        raise NciError("fragmented NCI packets are not supported", "NCI_FRAGMENTED")
    return {"mt": mt, "gid": gid, "oid": hdr[1], "length": hdr[2]}


def build_discover_a():
    # One discovery configuration: NFC-A passive poll.
    return command(GID_RF, RF_DISCOVER, bytes([1, 0x00, NFC_A, NFC_A_PASSIVE_POLL]))


def build_discover_map_a():
    # Map NFC-A protocol to the NFC-A frame interface.
    return command(GID_RF, RF_DISCOVER_MAP, bytes([1, 0x00, NFC_A, NFC_A_PASSIVE_POLL]))


def build_transceive(discovery_id, protocol, data):
    if len(data) > 255:
        raise NciError("transceive payload too long", "NCI_OVERSIZE")
    # NCI RF_TRANSCEIVE_CMD: RF discovery ID, RF protocol, data length, data.
    return command(GID_RF, RF_TRANSCEIVE,
                   bytes([discovery_id & 0xFF, protocol & 0xFF, len(data)]) + bytes(data))


class NciController:
    """Synchronous controller bound to a transport implementing the FD API."""

    def __init__(self, transport, clock=time.monotonic):
        self.t = transport
        self.clock = clock
        self.initialized = False
        self.discovery_id = None
        self.protocol = None
        self.technology = None
        self.activation_params = b""

    # -- low level ---------------------------------------------------------
    def send(self, frame):
        self.t.write(frame)

    def receive(self, timeout_s):
        deadline = self.clock() + max(0.0, float(timeout_s))
        while True:
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise NciError("NCI receive timeout", "NCI_TIMEOUT")
            ready = self.t.poll(min(remaining, 0.25))
            if not ready:
                continue
            hdr = self.t.read_exact(3)
            info = parse_header(hdr)
            body = self.t.read_exact(info["length"]) if info["length"] else b""
            info["payload"] = body
            info["raw"] = hdr + body
            return info

    def await_response(self, gid, oid, timeout_s=2.0):
        """Wait for a matching response, keeping notifications for the caller."""
        deadline = self.clock() + timeout_s
        notifications = []
        while self.clock() < deadline:
            msg = self.receive(max(0.01, deadline - self.clock()))
            if msg["mt"] == MT_NOTIFICATION:
                notifications.append(msg)
                continue
            if msg["mt"] != MT_RESPONSE:
                continue
            if msg["gid"] != gid or msg["oid"] != oid:
                raise NciError("unexpected NCI response %02x/%02x" % (msg["gid"], msg["oid"]),
                               "NCI_UNEXPECTED_RESPONSE")
            return msg, notifications
        raise NciError("NCI response timeout", "NCI_TIMEOUT")

    # -- normal-mode sequence ---------------------------------------------
    def reset(self, timeout_s=2.0):
        self.send(command(GID_CORE, CORE_RESET, b"\x00"))
        rsp, notes = self.await_response(GID_CORE, CORE_RESET, timeout_s)
        if not rsp["payload"] or rsp["payload"][0] != 0:
            raise NciError("CORE_RESET rejected (status=%r)" % (rsp["payload"][:1],),
                           "NCI_RESET_REJECTED")
        return {"response": rsp, "notifications": notes}

    def init(self, timeout_s=2.0):
        self.send(command(GID_CORE, CORE_INIT, b"\x00"))
        rsp, notes = self.await_response(GID_CORE, CORE_INIT, timeout_s)
        if not rsp["payload"] or rsp["payload"][0] != 0:
            raise NciError("CORE_INIT rejected (status=%r)" % (rsp["payload"][:1],),
                           "NCI_INIT_REJECTED")
        self.initialized = True
        return {"response": rsp, "notifications": notes}

    def start_discovery(self, timeout_s=2.0):
        if not self.initialized:
            raise NciError("controller is not initialized", "NCI_NOT_INITIALIZED")
        # Best effort map; controllers that already have a default mapping
        # answer with status 0x09 (already configured) which is acceptable.
        try:
            self.send(build_discover_map_a())
            self.await_response(GID_RF, RF_DISCOVER_MAP, timeout_s)
        except NciError as exc:
            if exc.code not in ("NCI_TIMEOUT", "NCI_UNEXPECTED_RESPONSE"):
                raise
        self.send(build_discover_a())
        rsp, notes = self.await_response(GID_RF, RF_DISCOVER, timeout_s)
        if not rsp["payload"] or rsp["payload"][0] not in (0, 0x09):
            raise NciError("RF_DISCOVER rejected (status=%r)" % (rsp["payload"][:1],),
                           "NCI_DISCOVER_REJECTED")
        return {"response": rsp, "notifications": notes}

    def wait_activation(self, timeout_s):
        deadline = self.clock() + max(0.0, float(timeout_s))
        while self.clock() < deadline:
            msg = self.receive(max(0.01, deadline - self.clock()))
            if msg["mt"] != MT_NOTIFICATION:
                continue
            if msg["gid"] == GID_RF and msg["oid"] == RF_INTF_ACTIVATED_NTF:
                p = msg["payload"]
                if len(p) < 4:
                    raise NciError("short RF_INTF_ACTIVATED_NTF", "NCI_MALFORMED")
                self.discovery_id = p[0]
                self.protocol = p[2]
                self.technology = p[1]
                alen = p[3]
                if len(p) < 4 + alen:
                    raise NciError("activation parameter length overflow", "NCI_MALFORMED")
                self.activation_params = p[4:4 + alen]
                return {"discovery_id": self.discovery_id,
                        "protocol": self.protocol,
                        "interface": self.technology,
                        "activation_params_hex": self.activation_params.hex()}
            if msg["gid"] == GID_RF and msg["oid"] == RF_DISCOVER_NTF:
                continue
            if msg["gid"] == GID_RF and msg["oid"] == RF_DEACTIVATE_NTF:
                raise NciError("RF field deactivated before activation", "NCI_FIELD_LOST")
        raise NciError("no tag activated within timeout", "NO_TAG")

    def transceive(self, data, timeout_s=1.5):
        """NCI 1.0 control-path RF_TRANSCEIVE fallback.

        The production path uses the kernel NCI device (nfc0) through the
        standard netlink/raw-socket ABI.  This helper is retained only for a
        controller exposed via the legacy raw misc transport.
        """
        if self.discovery_id is None or self.protocol is None:
            raise NciError("no activated tag", "NCI_NOT_ACTIVATED")
        self.send(build_transceive(self.discovery_id, self.protocol, data))
        rsp, _ = self.await_response(GID_RF, RF_TRANSCEIVE, timeout_s)
        p = rsp["payload"]
        # The deprecated control-path response opens with a status byte.  Some
        # controllers (including this vendor's NCI 2.x firmware) answer with a
        # DATA packet instead; that is not a valid RF_TRANSCEIVE_RSP.
        if len(p) < 2:
            raise NciError("short RF_TRANSCEIVE_RSP", "NCI_MALFORMED")
        status, n = p[0], p[1]
        if status != 0:
            raise NciError("RF_TRANSCEIVE status 0x%02x" % status,
                           "NCI_TRANSCEIVE_FAILED")
        if len(p) < 2 + n:
            raise NciError("transceive length overflow", "NCI_MALFORMED")
        return p[2:2 + n]


def read_type2_ndef(ctrl, timeout_s=1.5):
    """Read the first NDEF TLV from an NFC-A Type 2 tag (READ page 3, then 4+).

    This is intentionally narrow: NFC Forum Type 2 only, no MIFARE Classic,
    no writes, no lock/access bytes.  The returned bytes are parsed by the
    hardened NDEF layer, never executed.
    """
    cc_page = ctrl.transceive(b"\x30\x03", timeout_s)
    if len(cc_page) < 16:
        raise NciError("Type 2 READ page 3 returned %d bytes" % len(cc_page),
                       "TYPE2_SHORT_READ")
    if cc_page[0] != 0xE1:
        raise NciError("not a Type 2 tag: CC magic 0x%02x" % cc_page[0],
                       "TYPE2_NOT_NDEF")
    # The CC size byte is units of 8 bytes; cap the read to 8 KiB.
    size = max(0, min(int(cc_page[2]) * 8, 8192))
    if size < 16:
        raise NciError("Type 2 CC advertises no usable data area", "TYPE2_EMPTY")
    data = bytearray()
    page = 4
    while len(data) < size and page < 64:
        chunk = ctrl.transceive(bytes([0x30, page]), timeout_s)
        if not chunk:
            raise NciError("empty READ response", "TYPE2_SHORT_READ")
        data.extend(chunk)
        page += 1
    blob = bytes(data)
    # TLV: 0x03 length value, 0xFE terminator, 0x00 NULL.
    i = 0
    while i < len(blob):
        tag = blob[i]
        if tag == 0x00:
            i += 1
            continue
        if tag == 0xFE:
            break
        if i + 1 >= len(blob):
            raise NciError("truncated TLV", "TYPE2_MALFORMED")
        ln = blob[i + 1]
        i += 2
        if ln == 0xFF:
            if i + 2 > len(blob):
                raise NciError("truncated long TLV", "TYPE2_MALFORMED")
            ln = int.from_bytes(blob[i:i + 2], "big")
            i += 2
        if i + ln > len(blob):
            raise NciError("TLV length exceeds tag data", "TYPE2_MALFORMED")
        if tag == 0x03:
            return blob[i:i + ln]
        i += ln
    raise NciError("no NDEF TLV on tag", "TYPE2_NO_NDEF")


# ---------------------------------------------------------------------------
# NFC Forum Type 2 tag operations (NTAG21x / MIFARE Ultralight EV1 family).
#
# Only page-aligned, bounded operations are exposed.  The lock and OTP pages
# (0..2) and manufacturer block (0..2) are never written; the CC page (3) is
# never modified, so a write cannot accidentally mark the tag read-only.
# A write is read back and verified by the caller before it is reported as
# successful.
# ---------------------------------------------------------------------------

TYPE2_CC_PAGE = 3
TYPE2_FIRST_DATA_PAGE = 4
TYPE2_MAX_PAGES = 60
TYPE2_MAX_MESSAGE = 888       # NTAG216 data area, 4-byte pages
TYPE2_DEFAULT_PAGES = 45      # 8-byte capacity field of an NTAG215 (180 B)


class Type2TagInfo:
    __slots__ = ("capacity_bytes", "pages", "writable", "read_only",
                 "ndef_message_length")

    def __init__(self, capacity_bytes, writable=True, read_only=False,
                 ndef_message_length=None):
        self.capacity_bytes = int(capacity_bytes)
        self.pages = max(TYPE2_FIRST_DATA_PAGE,
                         min(TYPE2_MAX_PAGES,
                             (self.capacity_bytes + 3) // 4 + TYPE2_FIRST_DATA_PAGE))
        self.writable = bool(writable)
        self.read_only = bool(read_only)
        self.ndef_message_length = ndef_message_length


def type2_info(ctrl, timeout_s=1.5):
    # READ page 3 (CC) and page 4 (the first data/NDEF page).  Some controllers
    # only return the requested page; an NTAG returns four pages from the
    # 0x30 read, so both layouts are accepted.
    cc = ctrl.transceive(b"\x30\x03", timeout_s)
    if len(cc) < 16:
        raise NciError("Type 2 READ page 3 returned %d bytes" % len(cc),
                       "TYPE2_SHORT_READ")
    if cc[0] != 0xE1:
        raise NciError("not a Type 2 tag: CC magic 0x%02x" % cc[0],
                       "TYPE2_NOT_NDEF")
    capacity = max(0, min(int(cc[2]) * 8, TYPE2_MAX_MESSAGE))
    access = cc[3] if len(cc) > 3 else 0
    read_only = bool(access & 0x0F) or bool(access & 0xF0)
    return Type2TagInfo(capacity, writable=not read_only, read_only=read_only)


def type2_read_pages(ctrl, start_page, count, timeout_s=1.5):
    if start_page < TYPE2_CC_PAGE or count < 1:
        raise NciError("refusing page range %d+%d" % (start_page, count),
                       "TYPE2_PAGE_RANGE")
    if start_page + count > TYPE2_MAX_PAGES:
        raise NciError("page range exceeds Type 2 limit", "TYPE2_PAGE_RANGE")
    out = bytearray()
    p = start_page
    while p < start_page + count:
        chunk = ctrl.transceive(bytes([0x30, p & 0xFF]), timeout_s)
        if len(chunk) < 4:
            raise NciError("short READ at page %d (%d bytes)" % (p, len(chunk)),
                           "TYPE2_SHORT_READ")
        out.extend(chunk[:4])
        p += 1
    return bytes(out)


def type2_write_pages(ctrl, start_page, data, timeout_s=1.5):
    """Write whole Type-2 pages and ACK-verify each 4-byte block."""
    data = bytes(data)
    # Type 2 starts the NDEF TLV in page 4.  A partial-page image needs its
    # first (zero) prefix page 3, and write_tag() copies page 3's existing CC
    # bytes verbatim; lock/OTP pages are still never writable.
    if start_page < TYPE2_CC_PAGE:
        raise NciError("refusing to write page %d (manufacturer/lock/OTP area)"
                       % start_page, "TYPE2_PROTECTED_PAGE")
    if not data or len(data) % 4:
        raise NciError("write length must be a non-zero multiple of 4",
                       "TYPE2_WRITE_LENGTH")
    if start_page + len(data) // 4 > TYPE2_MAX_PAGES:
        raise NciError("write exceeds Type 2 data area", "TYPE2_WRITE_LENGTH")
    for i in range(0, len(data), 4):
        page = start_page + i // 4
        block = data[i:i + 4]
        # WRITE (0xA2) is a 6-byte frame; the controller returns a 4-byte ACK.
        rsp = ctrl.transceive(b"\xA2" + bytes([page & 0xFF]) + block,
                              timeout_s)
        if len(rsp) < 4:
            raise NciError("short ACK for page %d" % page, "TYPE2_WRITE_NOACK")
        # NTAG: ACK is 0x0A then the nibble (page & 0x0F).  MIFARE Ultralight
        # returns 0x0A + 0x00, so accept both but require the 0x0A prefix.
        if rsp[0] != 0x0A:
            raise NciError("page %d NAK 0x%02x" % (page, rsp[0]),
                           "TYPE2_WRITE_NAK")
    return True


def build_type2_ndef_image(message, capacity_bytes):
    """Return the complete data area (starting at page 4) to write.

    Layout follows the NFC Forum Type 2 Tag NDEF mapping:
      0x03 <len> <NDEF message> 0xFE [0x00 pad]
    Short TLV length is used for messages <= 254 bytes; the 3-byte form is
    used otherwise.  A 4-byte page-aligned zero prefix keeps every write page
    aligned even when the message starts in the middle of a page.
    """
    msg = bytes(message)
    if not msg:
        raise NciError("refusing to write an empty NDEF message",
                       "TYPE2_EMPTY_MESSAGE")
    if len(msg) > TYPE2_MAX_MESSAGE - 8:
        raise NciError("NDEF message too large for Type 2 tag",
                       "TYPE2_OVERSIZE")
    if len(msg) <= 254:
        tlv = b"\x03" + bytes([len(msg)]) + msg
    else:
        tlv = b"\x03\xFF" + len(msg).to_bytes(2, "big") + msg
    image = tlv + b"\xFE"
    usable = max(0, min(capacity_bytes, TYPE2_MAX_MESSAGE) - 4)
    if len(image) > usable:
        raise NciError("message does not fit the Type 2 data area",
                       "TYPE2_OVERSIZE")
    image += b"\x00" * (_align4(len(image)) - len(image))
    if len(image) % 4:
        raise NciError("internal Type 2 image alignment error", "TYPE2_LAYOUT")
    return image


def _align4(n):
    return (n + 3) & ~3


def read_type2_ndef_info(ctrl, timeout_s=1.5):
    """Return (info, NDEF bytes or None, error_code or None)."""
    info = type2_info(ctrl, timeout_s)
    if info.capacity_bytes < 16:
        return info, None, "TYPE2_EMPTY"
    blob = type2_read_pages(ctrl, TYPE2_FIRST_DATA_PAGE,
                            max(1, (info.capacity_bytes + 3) // 4), timeout_s)
    i = 0
    while i < len(blob):
        tag = blob[i]
        if tag == 0x00:
            i += 1
            continue
        if tag == 0xFE:
            return info, None, None
        if i + 1 >= len(blob):
            raise NciError("truncated TLV", "TYPE2_MALFORMED")
        ln = blob[i + 1]
        i += 2
        if ln == 0xFF:
            if i + 2 > len(blob):
                raise NciError("truncated long TLV", "TYPE2_MALFORMED")
            ln = int.from_bytes(blob[i:i + 2], "big")
            i += 2
        if i + ln > len(blob):
            raise NciError("TLV length exceeds tag data", "TYPE2_MALFORMED")
        if tag == 0x03:
            info.ndef_message_length = ln
            return info, blob[i:i + ln], None
        i += ln
    return info, None, "TYPE2_NO_NDEF"


def write_type2_ndef(ctrl, message, timeout_s=1.5):
    """Write an NDEF message starting at the Type-2 NDEF TLV.

    Page 4 onward is overwritten as a single page-aligned Type-2 image.  Page 3
    is preserved byte-for-byte except that the NDEF TLV tag/length prefix is
    placed in its existing CC-mandated NDEF area when the image starts there.
    Returns a dict with the tag info and the exact bytes the caller must read
    back; it does NOT claim success on its own.
    """
    info = type2_info(ctrl, timeout_s)
    if info.read_only or not info.writable:
        raise NciError("tag CC marks the data area read-only",
                       "TYPE2_READ_ONLY")
    if info.capacity_bytes < 16:
        raise NciError("Type 2 tag has no usable data area", "TYPE2_EMPTY")
    image = build_type2_ndef_image(message, info.capacity_bytes)
    # The TLV begins at page 4 for a Type 2 tag; write the image there.
    # Pad pages that are not part of the message with 0x00 so a shorter write
    # cannot leave an old TLV terminator before the new one.
    max_pages = max(1, min(TYPE2_MAX_PAGES - TYPE2_FIRST_DATA_PAGE,
                           (info.capacity_bytes + 3) // 4))
    image += b"\x00" * (max_pages * 4 - len(image))
    type2_write_pages(ctrl, TYPE2_FIRST_DATA_PAGE, image, timeout_s)
    return {"capacity_bytes": info.capacity_bytes, "pages": max_pages,
            "message_length": len(message), "written_bytes": len(image),
            "expected_readback": bytes(message)}


def verify_type2_write(ctrl, expected_message, timeout_s=1.5):
    """Read back the Type-2 NDEF TLV and require byte-identical content."""
    info, raw, err = read_type2_ndef_info(ctrl, timeout_s)
    if err:
        raise NciError("read-back failed: %s" % err, err)
    if raw != bytes(expected_message):
        raise NciError("read-back differs from written NDEF", "TYPE2_VERIFY_FAILED")
    return {"verified": True, "capacity_bytes": info.capacity_bytes,
            "bytes": len(raw)}
