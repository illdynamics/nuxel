#!/usr/bin/env python3
"""Offline golden-frame corpus builder for the BCM47752 SSI/TL/RPC protocol.

Generates byte-exact golden frames (normal and faulty) that exercise the
vendor framing/CRC/sequence/RPC semantics recovered from bbd_rpc_lh.c +
bcm_gps_regs.c, then optionally replays them through the existing native
decoder (nuxel_bbd_download --replay-stdin).

This is source-derived OFFLINE evidence only.  Nothing here is a hardware
response and no frame proves firmware acceptance.  Every emitted frame is
hashed (SHA-256) so a later on-device capture can be compared byte-for-byte
without trusting this tool's interpretation.

TL packet body layout (bbd_rpc_lh.c / nuxel_bbd_download.c):
    seqId | size | flags | [flag-detail bytes in bit order 0..9] | payload | crc8
  - `size` counts payload bytes ONLY.
  - CRC-8 = GlUtlCrc table over bytes[1..len-2], then nibble-swap.
  - Framing: ESC(0xB0) SOP(0x00) ... ESC EOP(0x01).
  - Escape: 0xB0->0xB0 0x03, 0x11->0xB0 0x04, 0x13->0xB0 0x05.

Flags (bit): ACK=1, RELIABLE=2, REL_ACK=4, REL_NACK=8, MSG_LOST=16,
GARBAGE=32, SIZE_EXT=64, EXT=128, INTERNAL=256, IGN_SEQ=512.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ESC = 0xB0
EOP = 0x01
ESC_ESC = 0x03
ESC_XON = 0x04
ESC_XOFF = 0x05

F_ACK, F_RELIABLE, F_REL_ACK, F_REL_NACK = 1, 2, 4, 8
F_MSG_LOST, F_GARBAGE, F_SIZE_EXT, F_EXT, F_INTERNAL, F_IGN_SEQ = 16, 32, 64, 128, 256, 512

# GlUtlCrc table (identical to the kernel bbd_rpc_lh.c and the native tools).
CRC_TBL = [
0x00,0x4d,0x9a,0xd7,0x79,0x34,0xe3,0xae,0xf2,0xbf,0x68,0x25,0x8b,0xc6,0x11,0x5c,
0xa9,0xe4,0x33,0x7e,0xd0,0x9d,0x4a,0x07,0x5b,0x16,0xc1,0x8c,0x22,0x6f,0xb8,0xf5,
0x1f,0x52,0x85,0xc8,0x66,0x2b,0xfc,0xb1,0xed,0xa0,0x77,0x3a,0x94,0xd9,0x0e,0x43,
0xb6,0xfb,0x2c,0x61,0xcf,0x82,0x55,0x18,0x44,0x09,0xde,0x93,0x3d,0x70,0xa7,0xea,
0x3e,0x73,0xa4,0xe9,0x47,0x0a,0xdd,0x90,0xcc,0x81,0x56,0x1b,0xb5,0xf8,0x2f,0x62,
0x97,0xda,0x0d,0x40,0xee,0xa3,0x74,0x39,0x65,0x28,0xff,0xb2,0x1c,0x51,0x86,0xcb,
0x21,0x6c,0xbb,0xf6,0x58,0x15,0xc2,0x8f,0xd3,0x9e,0x49,0x04,0xaa,0xe7,0x30,0x7d,
0x88,0xc5,0x12,0x5f,0xf1,0xbc,0x6b,0x26,0x7a,0x37,0xe0,0xad,0x03,0x4e,0x99,0xd4,
0x7c,0x31,0xe6,0xab,0x05,0x48,0x9f,0xd2,0x8e,0xc3,0x14,0x59,0xf7,0xba,0x6d,0x20,
0xd5,0x98,0x4f,0x02,0xac,0xe1,0x36,0x7b,0x27,0x6a,0xbd,0xf0,0x5e,0x13,0xc4,0x89,
0x63,0x2e,0xf9,0xb4,0x1a,0x57,0x80,0xcd,0x91,0xdc,0x0b,0x46,0xe8,0xa5,0x72,0x3f,
0xca,0x87,0x50,0x1d,0xb3,0xfe,0x29,0x64,0x38,0x75,0xa2,0xef,0x41,0x0c,0xdb,0x96,
0x42,0x0f,0xd8,0x95,0x3b,0x76,0xa1,0xec,0xb0,0xfd,0x2a,0x67,0xc9,0x84,0x53,0x1e,
0xeb,0xa6,0x71,0x3c,0x92,0xdf,0x08,0x45,0x19,0x54,0x83,0xce,0x60,0x2d,0xfa,0xb7,
0x5d,0x10,0xc7,0x8a,0x24,0x69,0xbe,0xf3,0xaf,0xe2,0x35,0x78,0xd6,0x9b,0x4c,0x01,
0xf4,0xb9,0x6e,0x23,0x8d,0xc0,0x17,0x5a,0x06,0x4b,0x9c,0xd1,0x7f,0x32,0xe5,0xa8]


def crc8(body_slice):
    c = 0
    for b in body_slice:
        c = CRC_TBL[c ^ b]
    return ((c & 0x0F) << 4) | ((c & 0xF0) >> 4)


def rpc_field(v):
    return bytes([v]) if v < 0x80 else bytes([0x80 | (v >> 8), v & 0xFF])


def rpc_record(rpc_id, payload):
    return rpc_field(rpc_id) + rpc_field(len(payload)) + payload


def escape(raw):
    out = bytearray()
    for b in raw:
        if b == ESC:
            out += bytes([ESC, ESC_ESC])
        elif b == 0x11:
            out += bytes([ESC, ESC_XON])
        elif b == 0x13:
            out += bytes([ESC, ESC_XOFF])
        else:
            out.append(b)
    return bytes(out)


def frame(seq, flags, details, payload):
    """Build a byte-exact on-wire frame.  `details` is a dict bit->byte."""
    size = len(payload)
    if size > 0xFF:
        flags |= F_SIZE_EXT
    if flags & ~0xFF:
        flags |= F_EXT
    body = bytearray([seq, size & 0xFF, flags & 0xFF])
    for bit in range(10):
        if not (flags & (1 << bit)):
            continue
        if bit == 6:            # F_SIZE_EXT
            body.append(size >> 8)
        elif bit == 7:          # F_EXT
            body.append(flags >> 8)
        elif bit in details:
            body.append(details[bit])
        else:
            body.append(0)
    body += payload
    crc = crc8(bytes(body[1:]))
    return bytes([ESC, 0x00]) + escape(bytes(body) + bytes([crc])) + bytes([ESC, EOP])


# Standard payloads.
GET_VERSION_REQ = rpc_record(0, b"")            # RPC id 0, empty body
GET_VERSION_REPLY = rpc_record(0, b"\x36\x10\x90\x00")  # example version body
MEM_WRITE_BODY = (0x00).to_bytes(4, "little") + (0x01).to_bytes(2, "little") + b"\x00"
MEM_WRITE_REQ = rpc_record(5, MEM_WRITE_BODY)  # RPC id 5 MemoryWrite
START_SCRATCH = rpc_record(46, (0x00800161).to_bytes(4, "little"))  # RPC 46
SERVICE_START = rpc_record(55, (0x00800161).to_bytes(4, "little") + b"\x00" * 16)  # RPC 55


def build_corpus():
    cases = {}

    # --- normal frames ---
    cases["normal_getversion_request"] = frame(1, 0, {}, GET_VERSION_REQ)
    cases["normal_getversion_reply"] = frame(0, 0, {}, GET_VERSION_REPLY)
    cases["normal_reliable_memwrite"] = frame(1, F_RELIABLE, {1: 1}, MEM_WRITE_REQ)
    cases["normal_start_scratch"] = frame(2, 0, {}, START_SCRATCH)
    cases["normal_service_start"] = frame(3, 0, {}, SERVICE_START)
    cases["normal_reliable_ack"] = frame(0, F_REL_ACK, {2: 1}, b"")       # acceptable ACK

    # --- faulty frames ---
    # short packet (valid CRC but truncated payload vs declared size handled by decoder)
    cases["faulty_missing_detail_bit"] = frame(9, F_ACK, {}, b"")         # flag w/o detail byte
    cases["faulty_unknown_flag"] = frame(9, F_EXT, {}, b"")               # EXT low bit, no detail
    cases["faulty_surplus_payload"] = frame(9, 0, {}, b"\x00")            # size mismatch
    cases["faulty_truncated_rpc"] = frame(9, 0, {}, b"\x01\x02\x00")      # rpc id,len missing body

    # wrong CRC: build a valid frame then flip the CRC byte (last body byte).
    gf = frame(7, F_ACK, {0: 42}, b"")
    # locate crc byte: it's the byte just before ESC EOP
    bad = bytearray(gf)
    # crc is at index len-3 (ESC at -2, EOP at -1)
    bad[-3] ^= 0x01
    cases["faulty_wrong_crc"] = bytes(bad)

    # stale ACK: ACK flag with a seq that does not match the in-flight op.
    cases["faulty_stale_ack"] = frame(0, F_ACK | F_REL_ACK, {0: 200, 2: 200}, b"")

    # seq wrap: seqId 255 -> next expected 0.
    cases["normal_seq_wrap_boundary"] = frame(255, 0, {}, GET_VERSION_REPLY)

    # duplicate reply: two identical reliable ACK frames concatenated.
    cases["faulty_duplicate_reply"] = cases["normal_reliable_ack"] + cases["normal_reliable_ack"]

    # mixed ROM/application version: GetVersion reply with an unexpected w0.
    cases["faulty_mixed_version"] = frame(0, 0, {}, rpc_record(0, b"\xff\xff\xff\xff"))

    # disconnect / electrical idle: all 0xFF is NOT a protocol reply.
    cases["idle_0xff_not_protocol"] = b"\xff" * 32

    # unfinished frame (SOP but no ESC EOP).
    cases["faulty_unfinished_frame"] = cases["normal_getversion_reply"][:-2]

    # embedded escaped bytes round-trip: payload contains ESC/XON/XOFF.
    cases["normal_escaped_payload"] = frame(0, 0, {},
        rpc_record(0x1F, bytes([ESC, 0x11, 0x13, 0x00, 0x01])))

    return {k: hashlib.sha256(v).hexdigest() for k, v in cases.items()}, cases


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("corpus/out"))
    ap.add_argument("--decoder", type=Path, help="nuxel_bbd_download to replay through")
    args = ap.parse_args()

    digests, cases = build_corpus()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"kind": "OFFLINE_GOLDEN_FRAMES",
                "source": "bbd_rpc_lh.c + bcm_gps_regs.c via native decoder",
                "hardware_verified": False,
                "operation_completion_verified": False,
                "frames": {}}
    for name, wire in cases.items():
        f = args.out / f"{name}.bin"
        f.write_bytes(wire)
        manifest["frames"][name] = {
            "sha256": hashlib.sha256(wire).hexdigest(),
            "length": len(wire),
        }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    if args.decoder:
        import subprocess
        replay = {}
        for name, wire in cases.items():
            p = subprocess.run([str(args.decoder), "--replay-stdin"],
                               input=wire, capture_output=True, timeout=5)
            replay[name] = {"returncode": p.returncode,
                            "out": p.stdout.decode(errors="replace").strip()}
            print(f"{name}: rc={p.returncode}  {p.stdout.decode(errors='replace').strip()}")
        (args.out / "replay.json").write_text(json.dumps(replay, indent=2) + "\n")
    else:
        print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    sys.exit(main())
