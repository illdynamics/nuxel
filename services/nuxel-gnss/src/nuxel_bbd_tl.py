"""Nuxel BBD Transport Layer (TL) framing + CRC-8 + RPC helper.

A faithful Python port of the Broadcom BBD Protocol Layer logic found in the
GPLv2 kernel driver drivers/sensorhub/brcm/bbdpl/bbd_rpc_lh.c (Broadcom Bridge
Driver) on the SM-G975F `beyond2lte` 4.14.253 kernel.  This module implements
only the wire format proven by that source: SOP/EOP framing, escape handling,
the 256-entry CRC-8 table, and the packet/rpc header layout.

It is pure Python (no hardware) so it can be unit-tested on the build host and
reused verbatim by the hardware daemon.  It never asserts that a byte stream is
a GNSS fix; it only frames/parses BBD packets.

Wire framing (bbd_rpc_lh.c):
    ESCAPE(0xB0) SOP(0x00) <message> ESCAPE(0xB0) EOP(0x01)
    message = SeqId + PayloadSizeLSB + FlagsLSB + flag-details (including extensions)
              + payload + CRC8 (nibble-swapped)
    escape codes inside message: 0xB0->0xB0 0x03, 0x11->0xB0 0x04, 0x13->0xB0 0x05
"""
from __future__ import annotations

ESCAPE_CHARACTER = 0xB0
SOP_CHARACTER = 0x00
EOP_CHARACTER = 0x01
ESCAPED_ESCAPE = 0x03
ESCAPED_XON = 0x04
ESCAPED_XOFF = 0x05
XON_CHARACTER = 0x11
XOFF_CHARACTER = 0x13

# Transport layer flag bits (bbd_rpc_lh.c)
FLAG_PACKET_ACK = 1 << 0
FLAG_RELIABLE_PACKET = 1 << 1
FLAG_RELIABLE_ACK = 1 << 2
FLAG_RELIABLE_NACK = 1 << 3
FLAG_MSG_LOST = 1 << 4
FLAG_MSG_GARBAGE = 1 << 5
FLAG_SIZE_EXTENDED = 1 << 6
FLAG_EXTENDED = 1 << 7
FLAG_INTERNAL_PACKET = 1 << 8
FLAG_IGNORE_SEQID = 1 << 9

# CRC-8 table (GlUtlCrc::ucCrcTable) - exact copy from bbd_rpc_lh.c
CRC_TABLE = (
    0x00, 0x4d, 0x9a, 0xd7, 0x79, 0x34, 0xe3, 0xae, 0xf2, 0xbf, 0x68, 0x25, 0x8b, 0xc6, 0x11, 0x5c,
    0xa9, 0xe4, 0x33, 0x7e, 0xd0, 0x9d, 0x4a, 0x07, 0x5b, 0x16, 0xc1, 0x8c, 0x22, 0x6f, 0xb8, 0xf5,
    0x1f, 0x52, 0x85, 0xc8, 0x66, 0x2b, 0xfc, 0xb1, 0xed, 0xa0, 0x77, 0x3a, 0x94, 0xd9, 0x0e, 0x43,
    0xb6, 0xfb, 0x2c, 0x61, 0xcf, 0x82, 0x55, 0x18, 0x44, 0x09, 0xde, 0x93, 0x3d, 0x70, 0xa7, 0xea,
    0x3e, 0x73, 0xa4, 0xe9, 0x47, 0x0a, 0xdd, 0x90, 0xcc, 0x81, 0x56, 0x1b, 0xb5, 0xf8, 0x2f, 0x62,
    0x97, 0xda, 0x0d, 0x40, 0xee, 0xa3, 0x74, 0x39, 0x65, 0x28, 0xff, 0xb2, 0x1c, 0x51, 0x86, 0xcb,
    0x21, 0x6c, 0xbb, 0xf6, 0x58, 0x15, 0xc2, 0x8f, 0xd3, 0x9e, 0x49, 0x04, 0xaa, 0xe7, 0x30, 0x7d,
    0x88, 0xc5, 0x12, 0x5f, 0xf1, 0xbc, 0x6b, 0x26, 0x7a, 0x37, 0xe0, 0xad, 0x03, 0x4e, 0x99, 0xd4,
    0x7c, 0x31, 0xe6, 0xab, 0x05, 0x48, 0x9f, 0xd2, 0x8e, 0xc3, 0x14, 0x59, 0xf7, 0xba, 0x6d, 0x20,
    0xd5, 0x98, 0x4f, 0x02, 0xac, 0xe1, 0x36, 0x7b, 0x27, 0x6a, 0xbd, 0xf0, 0x5e, 0x13, 0xc4, 0x89,
    0x63, 0x2e, 0xf9, 0xb4, 0x1a, 0x57, 0x80, 0xcd, 0x91, 0xdc, 0x0b, 0x46, 0xe8, 0xa5, 0x72, 0x3f,
    0xca, 0x87, 0x50, 0x1d, 0xb3, 0xfe, 0x29, 0x64, 0x38, 0x75, 0xa2, 0xef, 0x41, 0x0c, 0xdb, 0x96,
    0x42, 0x0f, 0xd8, 0x95, 0x3b, 0x76, 0xa1, 0xec, 0xb0, 0xfd, 0x2a, 0x67, 0xc9, 0x84, 0x53, 0x1e,
    0xeb, 0xa6, 0x71, 0x3c, 0x92, 0xdf, 0x08, 0x45, 0x19, 0x54, 0x83, 0xce, 0x60, 0x2d, 0xfa, 0xb7,
    0x5d, 0x10, 0xc7, 0x8a, 0x24, 0x69, 0xbe, 0xf3, 0xaf, 0xe2, 0x35, 0x78, 0xd6, 0x9b, 0x4c, 0x01,
    0xf4, 0xb9, 0x6e, 0x23, 0x8d, 0xc0, 0x17, 0x5a, 0x06, 0x4b, 0x9c, 0xd1, 0x7f, 0x32, 0xe5, 0xa8,
)


def crc8(data: bytes, state: int = 0) -> int:
    """CRC-8 over ``data`` continuing from ``state`` (GlUtlCrc::GlUtlCrcCalc)."""
    st = state & 0xFF
    for b in data:
        st = CRC_TABLE[st ^ b]
    return st


def crc8_packet(body_without_crc: bytes) -> int:
    """Compute the on-wire CRC for a packet whose body excludes the CRC byte.

    Reproduces bbd_rpc_lh.c TransportLayer_PacketReceived: CRC is computed over
    message[1..len-2] (i.e. everything after the SeqId and before the CRC), the
    nibbles are then swapped for anti-all-zero robustness.
    """
    st = crc8(body_without_crc)
    return ((st & 0x0F) << 4) | ((st & 0xF0) >> 4)


def encode_escape(payload: bytes) -> bytes:
    """Escape the message body between SOP and EOP (bbd rpc framing)."""
    out = bytearray()
    for b in payload:
        if b == ESCAPE_CHARACTER:
            out += bytes((ESCAPE_CHARACTER, ESCAPED_ESCAPE))
        elif b == XON_CHARACTER:
            out += bytes((ESCAPE_CHARACTER, ESCAPED_XON))
        elif b == XOFF_CHARACTER:
            out += bytes((ESCAPE_CHARACTER, ESCAPED_XOFF))
        else:
            out.append(b)
    return bytes(out)


def build_frame(seq_id: int, payload: bytes, flags: int = 0,
                details: dict[int, int] | None = None) -> bytes:
    """Encode framing only; this does not establish an RPC completion contract.

    Detail keys are flag masks. Extension details are generated automatically;
    every other set bit requires its own detail, including INTERNAL/IGNORE.
    """
    details = {} if details is None else details
    if not 0 <= seq_id <= 255 or not 0 <= flags <= 0x3ff:
        raise ValueError("invalid sequence or unsupported flags")
    if len(payload) > 2048:
        raise ValueError("payload exceeds source transport limit")
    flags &= ~(FLAG_SIZE_EXTENDED | FLAG_EXTENDED)
    if len(payload) > 255:
        flags |= FLAG_SIZE_EXTENDED
    if flags >> 8:
        flags |= FLAG_EXTENDED
    required = {1 << i for i in range(10) if flags & (1 << i)} - {
        FLAG_SIZE_EXTENDED, FLAG_EXTENDED}
    if set(details) != required or any(not 0 <= v <= 255 for v in details.values()):
        raise ValueError("missing, surplus or invalid flag details")
    msg = bytearray((seq_id, len(payload) & 255, flags & 255))
    for i in range(10):
        bit = 1 << i
        if flags & bit:
            msg.append(len(payload) >> 8 if bit == FLAG_SIZE_EXTENDED else
                       flags >> 8 if bit == FLAG_EXTENDED else details[bit])
    msg += payload
    msg.append(crc8_packet(bytes(msg[1:])))
    return bytes((ESCAPE_CHARACTER, SOP_CHARACTER)) + encode_escape(msg) + bytes((ESCAPE_CHARACTER, EOP_CHARACTER))


def build_rpc_packet(rpc_id: int, data: bytes) -> bytes:
    """Encode a single RPC {RpcId, RpcLen, data} record into wire bytes.

    Mirrors the reverse of BbdBridge_OnPacketReceived: rpc_id and rpc_len use a
    7/8-bit encoding where bit7 of a byte signals a following low/high byte.
    """
    out = bytearray()

    def put_varint_style(v):
        # Fields are one byte below 0x80, otherwise high seven bits
        # with the marker followed by the low eight bits.
        hi = (v >> 8) & 0x7F
        lo = v & 0xFF
        if hi or lo & 0x80:
            out.append(hi | 0x80)
            out.append(lo)
        else:
            out.append(lo)

    if not 0 <= rpc_id <= 0x7fff or len(data) > 0x7fff:
        raise ValueError("RPC id/length exceeds 15-bit encoding")
    put_varint_style(rpc_id)
    put_varint_style(len(data))
    out += data
    return bytes(out)


class TransportLayerParser:
    """Incremental BBD TL parser producing validated packets.

    Port of bbd_parse_asic_data() + TransportLayer_PacketReceived() parse states
    (WAIT_FOR_ESC_SOP, WAIT_FOR_SOP, WAIT_FOR_MESSAGE_COMPLETE, WAIT_FOR_EOP).
    """

    def __init__(self):
        self.state = 0  # WAIT_FOR_ESC_SOP
        self.rx_len = 0
        self.msg = bytearray()
        self.garbage_bytes = 0
        self.packets = 0
        self.parser_state_names = ('ESC_SOP', 'SOP', 'MSG', 'EOP')

    def push(self, data: bytes, on_packet=None):
        """Feed raw (escaped stream) bytes; returns list of decoded packets.

        Each decoded packet is a dict {seq_id, payload_size, flags, payload,
        reliable, ack, ...} after CRC + flag decode. ``on_packet``, if given, is
        called for each valid packet before it is appended.
        """
        out = []
        for uc in data:
            out += self._feed_byte(uc, on_packet)
        return out

    def _reset(self):
        self.rx_len = 0
        self.msg = bytearray()

    def _feed_byte(self, uc, on_packet):
        out = []
        if uc in (XON_CHARACTER, XOFF_CHARACTER):
            return out
        if self.state == 0:  # WAIT_FOR_ESC_SOP
            if uc == ESCAPE_CHARACTER:
                self.state = 1
        elif self.state == 1:  # WAIT_FOR_SOP
            if uc == SOP_CHARACTER:
                self.state = 2
                self._reset()
            elif uc != ESCAPE_CHARACTER:
                self.state = 0
                self.garbage_bytes += 1
            else:
                self.garbage_bytes += 2
        elif self.state == 2:  # WAIT_FOR_MESSAGE_COMPLETE
            if uc == ESCAPE_CHARACTER:
                self.state = 3
            elif self.rx_len < 2048 + 14:
                self.msg.append(uc)
                self.rx_len += 1
            else:
                self.state = 0
                self._reset()
        elif self.state == 3:  # WAIT_FOR_EOP
            if self.rx_len >= 2048 + 14 and uc in (ESCAPED_ESCAPE, ESCAPED_XON, ESCAPED_XOFF):
                self.state = 0
                self._reset()
                return out
            if uc == EOP_CHARACTER:
                pkt = self._decode_packet(self.msg)
                if pkt is not None:
                    self.packets += 1
                    if on_packet:
                        on_packet(pkt)
                    out.append(pkt)
                self.state = 0
                self._reset()
            elif uc == ESCAPED_ESCAPE:
                self.msg.append(ESCAPE_CHARACTER)
                self.rx_len += 1
                self.state = 2
            elif uc == ESCAPED_XON:
                self.msg.append(XON_CHARACTER)
                self.rx_len += 1
                self.state = 2
            elif uc == ESCAPED_XOFF:
                self.msg.append(XOFF_CHARACTER)
                self.rx_len += 1
                self.state = 2
            elif uc == SOP_CHARACTER:
                self.state = 2
                self._reset()
                self.garbage_bytes += 1
            elif uc == ESCAPE_CHARACTER:
                self.state = 1
            else:
                self.state = 0
                self.garbage_bytes += 1
        return out

    def _decode_packet(self, msg):
        if len(msg) < 4:
            return None
        body = bytes(msg)
        crc = crc8_packet(body[1:-1])
        if crc != body[-1]:
            return None
        p = 0
        seq_id = body[p]; p += 1
        payload_size = body[p]; p += 1
        flags = body[p]; p += 1
        original_flags = flags
        reliable_ack_seq = reliable_nack_seq = None
        reliable = False
        reliable_seq = None
        ack = False
        ack_seq = None
        internal = False
        flag_bytes = []
        i = 0
        while i < 16 and flags != 0 and p < len(body) - 1:
            bit = 1 << i
            if flags & bit == 0:
                i += 1
                continue
            flags &= ~bit
            detail = body[p]; p += 1
            flag_bytes.append((bit, detail))
            if bit == FLAG_PACKET_ACK:
                ack = True; ack_seq = detail
            elif bit == FLAG_RELIABLE_PACKET:
                reliable = True; reliable_seq = detail
            elif bit == FLAG_RELIABLE_ACK:
                reliable_ack_seq = detail
            elif bit == FLAG_RELIABLE_NACK:
                reliable_nack_seq = detail
            elif bit == FLAG_MSG_LOST:
                pass
            elif bit == FLAG_MSG_GARBAGE:
                pass
            elif bit == FLAG_SIZE_EXTENDED:
                payload_size |= detail << 8
            elif bit == FLAG_EXTENDED:
                flags |= detail << 8
                original_flags |= detail << 8
            elif bit == FLAG_INTERNAL_PACKET:
                internal = True
            elif bit == FLAG_IGNORE_SEQID:
                pass
            else:
                flags |= bit
                break
        payload = body[p:len(body) - 1]
        if flags or len(payload) != payload_size or payload_size > 2048:
            return None
        return {
            "seq_id": seq_id,
            "payload_size": payload_size,
            "flags": original_flags,
            "reliable_ack_seq": reliable_ack_seq,
            "reliable_nack_seq": reliable_nack_seq,
            "payload": payload,
            "reliable": reliable,
            "reliable_seq": reliable_seq,
            "ack": ack,
            "ack_seq": ack_seq,
            "internal": internal,
        }


def parse_rpc_payload(payload: bytes):
    """Decode an RPC payload into a list of (rpc_id, data) tuples.

    Port of BbdBridge_OnPacketReceived rpc header walking (7/8-bit id/len).
    """
    out = []
    i = 0

    def take_field():
        nonlocal i
        if i >= len(payload):
            raise ValueError("truncated RPC field")
        value = payload[i]
        i += 1
        if value & 0x80:
            if i >= len(payload):
                raise ValueError("truncated extended RPC field")
            value = ((value & 0x7f) << 8) | payload[i]
            i += 1
        return value

    while i < len(payload):
        rpc_id, rpc_len = take_field(), take_field()
        if rpc_len > len(payload) - i:
            raise ValueError("truncated RPC payload")
        out.append((rpc_id, bytes(payload[i:i + rpc_len])))
        i += rpc_len
    return out
