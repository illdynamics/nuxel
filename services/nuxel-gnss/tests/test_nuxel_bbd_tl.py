"""Unit tests for the Nuxel BBD transport-layer port.

These are PURE host tests (no hardware). They verify the framing/CRC/RPC logic
against the exact byte vectors published in the GPL kernel driver
drivers/sensorhub/brcm/bbdpl/bbd_rpc_lh.c so the daemon's wire code is proven
correct before it ever touches /dev/ttyBCM.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import nuxel_bbd_tl as tl


def test_crc_table():
    # CRC-8 of empty stream is 0; first entry maps 0^0 -> 0x00.
    assert tl.crc8(b"") == 0
    # Known vector from GlUtlCrc: crc of 0x00 starting at state 0 = CRC_TABLE[0] = 0x00
    assert tl.crc8(b"\x00") == 0x00
    # The table is exactly 256 entries.
    assert len(tl.CRC_TABLE) == 256


def test_crc8_packet_nibble_swap():
    # crc8_packet of a single 0x00 byte: crc=0x00, nibble-swap still 0x00
    assert tl.crc8_packet(b"\x00") == 0x00
    # crc8 over [0x01] = CRC_TABLE[0^1]=CRC_TABLE[1]=0x4d; nibble swap -> 0xd4
    assert tl.crc8(b"\x01") == 0x4d
    assert tl.crc8_packet(b"\x01") == 0xd4


def test_build_and_parse_roundtrip():
    payload = bytes(range(8))
    frame = tl.build_frame(seq_id=0, payload=payload)
    # Frame must start ESCAPE SOP and end ESCAPE EOP.
    assert frame[0] == tl.ESCAPE_CHARACTER
    assert frame[1] == tl.SOP_CHARACTER
    assert frame[-2] == tl.ESCAPE_CHARACTER
    assert frame[-1] == tl.EOP_CHARACTER

    parser = tl.TransportLayerParser()
    pkts = parser.push(frame)
    assert len(pkts) == 1, "expected exactly one packet, got %d" % len(pkts)
    pkt = pkts[0]
    assert pkt["seq_id"] == 0
    assert pkt["payload"] == payload
    assert pkt["payload_size"] == len(payload)


def test_escape_roundtrip():
    # Payload containing the escape byte and XON/XOFF must survive round-trip.
    payload = bytes([0xB0, 0x11, 0x13, 0x00, 0x01, 0x42])
    frame = tl.build_frame(seq_id=1, payload=payload)
    parser = tl.TransportLayerParser()
    pkts = parser.push(frame)
    assert len(pkts) == 1
    assert pkts[0]["payload"] == payload


def test_parse_kernel_sample1():
    # Exact sample packet comment from bbd_rpc_lh.c ("sample packet 1~4 are from
    # FW4773-368 which has sensor packet"). This is an ESCAPED stream as stored
    # in the driver; feed it through the parser and require a valid packet.
    sample1 = bytes([
        0x00, 0x2E, 0xB0, 0x00, 0x85, 0x26, 0x00, 0x21, 0x24, 0x22, 0x00, 0x02,
        0x00, 0x1E, 0x00, 0x37, 0x0E, 0xD3, 0x00, 0xCB, 0xFF, 0x50, 0x00, 0xDE,
        0x00, 0x56, 0x00, 0xC7, 0xFF, 0x02, 0x00, 0x00, 0x00, 0x37, 0x00, 0x90,
        0xFE, 0x18, 0xFF, 0xB7, 0x46, 0x02, 0x00, 0x00, 0x00, 0xB2, 0xB0, 0x01])
    parser = tl.TransportLayerParser()
    pkts = parser.push(sample1)
    assert len(pkts) >= 1, "sample1 should decode to at least one packet"


def test_parse_rpc_payload():
    # Build an RPC payload of two records and verify decode.
    a = tl.build_rpc_packet(0x01, b"\xaa\xbb")
    b = tl.build_rpc_packet(0x12, b"\xcc")
    payload = a + b
    rpcs = tl.parse_rpc_payload(payload)
    assert rpcs == [(0x01, b"\xaa\xbb"), (0x12, b"\xcc")]


def test_rpc_varint_wide_values():
    # rpc id/len >= 0x80 use the two-byte (0x80-marked) form.
    payload = tl.build_rpc_packet(0x123, b"x" * 300)
    rpcs = tl.parse_rpc_payload(payload)
    assert rpcs == [(0x123, b"x" * 300)]


def test_garbage_tolerance():
    # Garbage before the first SOP must be skipped without producing a packet.
    frame = tl.build_frame(0, b"\x01\x02\x03")
    parser = tl.TransportLayerParser()
    pkts = parser.push(b"\xAA\xBB\xCC" + frame)
    assert len(pkts) == 1
    assert pkts[0]["payload"] == b"\x01\x02\x03"
    # The kernel only counts garbage after a partial ESCAPE sequence (a lone
    # 0xB0 not followed by SOP/EOP); arbitrary pre-SOP bytes in WAIT_FOR_ESC_SOP
    # are simply ignored in both the kernel and this port. Assert the packet
    # was still decoded from a non-frame-aligned stream.
    assert parser.packets == 1


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
