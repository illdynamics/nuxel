#!/usr/bin/env python3
"""
test_sipc5_differential.py — pytest differential test: a clean-room Python
reimplementation of the SIPC5 link-header decode is compared, byte-for-byte,
against the C parser via a stable JSON bridge. This is the "compare each byte
meaning against pinned source" step for the framing layer.

SPDX-License-Identifier: GPL-2.0-only
"""
import json
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))

SIPC5_START_MASK = 0xF8
SIPC5_EXT_FIELD_MASK = 0x03
SIPC5_PADDING_EXIST = 0x04
SIPC5_MULTI_FRAME_CFG = 0x03
SIPC5_EXT_LENGTH_CFG = 0x02

def py_hdr_len(cfg):
    ext = cfg & SIPC5_EXT_FIELD_MASK
    if ext == SIPC5_MULTI_FRAME_CFG: return 5
    if ext == SIPC5_EXT_LENGTH_CFG:  return 6
    return 4

def py_frame_len(cfg, b):
    ext = cfg & SIPC5_EXT_FIELD_MASK
    if ext == SIPC5_EXT_LENGTH_CFG:
        return int.from_bytes(b[2:6], 'little')
    return int.from_bytes(b[2:4], 'little')

# The C program prints JSON lines for a set of canned headers.
C_BRIDGE = ("#include \"sipc5_fmt.h\"\n""#include <stdio.h>\n""int main(void){\n""  u8 cases[][6] = {{0xF8,10,14,0,0,0}, {0xFB,245,20,0,0x81,0}, {0xFA,235,0x34,0x12,0,0}, {0xF9,35,1,0,0,0}};\n""  int i;\n""  for(i=0;i<4;i++){\n""    struct nuxel_sipc5_link l;\n""    int r=sipc5_parse_link_header(cases[i], 6, &l);\n""    printf(\"%d %u %u %u %d %d %d\\n\", r,l.hdr_len,l.frame_len,l.ch,l.multi_frame,l.ext_len,l.padding_exist);\n""  }\n""  return 0;\n""}\n")

def test_differential(tmp_path):
    # write bridge
    bridge = tmp_path / "bridge.c"
    bridge.write_text(C_BRIDGE)
    src = os.path.join(HERE, "..", "src")
    exe = tmp_path / "bridge"
    subprocess.run(["gcc", "-O2", "-std=gnu11", "-I", src, str(bridge),
                    str(src)+"/sipc5_fmt.c", "-o", str(exe)], check=True)
    out = subprocess.run([str(exe)], capture_output=True, check=True).stdout.decode()

    # Python reference cases (must match C cases exactly)
    cases = [
        {"cfg":0xF8, "ch":10, "b":bytes([0xF8,10,14,0,0,0])},
        {"cfg":0xFB, "ch":245, "b":bytes([0xFB,245,20,0,0x81,0])},
        {"cfg":0xFA, "ch":235, "b":bytes([0xFA,235,0x34,0x12,0,0])},
        {"cfg":0xF9, "ch":35, "b":bytes([0xF9,35,1,0,0,0])},
    ]

    lines = [l for l in out.splitlines() if l.strip()]
    got = []
    for l in lines:
        parts = l.split()
        got.append({"r":int(parts[0]), "hdr_len":int(parts[1]),
                    "frame_len":int(parts[2]), "ch":int(parts[3]),
                    "mf":int(parts[4]), "ext":int(parts[5]), "pad":int(parts[6])})
    assert len(got) == 4, f"bridge emitted {len(got)} lines"

    for (c, g) in zip(cases, got):
        assert g["hdr_len"] == py_hdr_len(c["cfg"]), f"hdr_len mismatch {c}"
        assert g["frame_len"] == py_frame_len(c["cfg"], c["b"]), f"frame_len mismatch {c}"
        assert g["ch"] == c["ch"]
        assert g["mf"] == ((c["cfg"] & 0x03) == 0x03)
        assert g["ext"] == ((c["cfg"] & 0x03) == 0x02)
        assert g["pad"] == bool(c["cfg"] & SIPC5_PADDING_EXIST)

if __name__ == "__main__":
    # standalone fallback
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        import pathlib
        test_differential(pathlib.Path(d))
    print("DIFFERENTIAL=PASS")
