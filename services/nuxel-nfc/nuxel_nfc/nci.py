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
        if self.discovery_id is None or self.protocol is None:
            raise NciError("no activated tag", "NCI_NOT_ACTIVATED")
        self.send(build_transceive(self.discovery_id, self.protocol, data))
        rsp, _ = self.await_response(GID_RF, RF_TRANSCEIVE, timeout_s)
        p = rsp["payload"]
        # status, data length, data
        if len(p) < 2:
            raise NciError("short RF_TRANSCEIVE_RSP", "NCI_MALFORMED")
        status, n = p[0], p[1]
        if status != 0:
            raise NciError("RF_TRANSCEIVE status 0x%02x" % status, "NCI_TRANSCEIVE_FAILED")
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
