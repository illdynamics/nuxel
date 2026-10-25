#!/usr/bin/env python3
"""Capture Nuxel's existing wlr-screencopy SHM map without opening /dev/fb0.

This is a one-shot A70 evidence helper, not a display owner.  The running
nuxel-wl-fb process remains the only framebuffer owner.
"""

import argparse
import binascii
import os
import struct
import zlib


def png_chunk(kind, data):
    crc = binascii.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    args = parser.parse_args()

    pid = int(os.popen("pgrep -o nuxel-wl-fb").read().strip())
    with open(f"/proc/{pid}/maps", encoding="ascii") as stream:
        mappings = [line for line in stream if "/dev/shm/nuxel-wl-fb-" in line]
    if not mappings:
        raise SystemExit("no nuxel-wl-fb shared-memory mapping")

    # New mappings sort before the prior leaked mapping in the observed process.
    address_range = mappings[0].split()[0]
    map_path = f"/proc/{pid}/map_files/{address_range}"
    source_width, source_height, source_stride = 720, 1520, 2880
    with open(map_path, "rb", buffering=0) as stream:
        source = stream.read(source_stride * source_height)
    if len(source) != source_stride * source_height:
        raise SystemExit(f"short SHM read: {len(source)} bytes")

    # The phone compositor is 720x1520 at scale 2.  Sample one pixel per 2x2
    # CSS pixel and convert little-endian XRGB8888 (B,G,R,X bytes) to PNG RGB.
    width, height = 360, 760
    raw = bytearray()
    for y in range(height):
        src = source[y * 2 * source_stride : y * 2 * source_stride + source_stride]
        row = bytearray(1 + width * 3)
        row[1::3] = src[2:source_stride:8]
        row[2::3] = src[1:source_stride:8]
        row[3::3] = src[0:source_stride:8]
        raw.extend(row)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw, 1))
        + png_chunk(b"IEND", b"")
    )
    with open(args.output, "wb") as stream:
        stream.write(png)
    print(f"captured={args.output} bytes={len(png)} map={address_range}")


if __name__ == "__main__":
    main()
