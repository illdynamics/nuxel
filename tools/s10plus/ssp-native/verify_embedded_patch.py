#!/usr/bin/env python3
"""Read-only verifier for the kernel-embedded BCM47752 patch source.

This consumes the C string literals from bbd_patch_file_beyond.h on the host.
It neither opens a BBD device nor executes the vendor daemon.  The kernel
exports the C array including its terminating NUL, so the device-node SHA-256
is deliberately calculated over ``payload + b'\\0'``.  The textual ``Crc``
field is retained as metadata only: its algorithm is not established here.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
import zlib
from pathlib import Path


EXPECTED_ASIC = "0x004775b0"
EXPECTED_LENGTH = 438_895
EXPECTED_ADDRESS = "0x00800161"
EXPECTED_BLOB_CRC32 = 0x93D35BB4
EXPECTED_KERNEL_EXPORT_SHA256 = (
    "0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72"
)
_C_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def decode_c_string_literals(path: Path) -> bytes:
    """Return the concatenated string literal data, excluding C's final NUL."""
    text = path.read_text(encoding="ascii")
    literals = _C_STRING.findall(text)
    if not literals:
        raise ValueError("no C string literals found")
    try:
        return b"".join(ast.literal_eval(item).encode("ascii") for item in literals)
    except (SyntaxError, UnicodeEncodeError) as exc:
        raise ValueError("cannot decode C string literals") from exc


def field(payload: bytes, name: bytes) -> bytes:
    match = re.search(rb"<" + re.escape(name) + rb"=([^>]+)>", payload)
    if not match:
        raise ValueError("missing patch field " + name.decode("ascii"))
    return match.group(1)


def verify(payload: bytes) -> dict[str, object]:
    asic = field(payload, b"AsicVersion").decode("ascii").lower()
    declared_length = int(field(payload, b"BlobLength"), 0)
    address = field(payload, b"PatchAddress").decode("ascii").lower()
    header_crc = field(payload, b"Crc").decode("ascii")
    blob_text = field(payload, b"Blob").replace(b"\n", b"")
    if len(blob_text) % 2:
        raise ValueError("odd-length patch hex")
    try:
        blob = bytes.fromhex(blob_text.decode("ascii"))
    except ValueError as exc:
        raise ValueError("invalid patch hex") from exc
    blob_crc = zlib.crc32(blob) & 0xFFFFFFFF
    exported = payload + b"\0"
    result = {
        "source_payload_bytes": len(payload),
        "kernel_export_bytes": len(exported),
        "kernel_export_sha256": hashlib.sha256(exported).hexdigest(),
        "asic": asic,
        "header_crc": header_crc,
        "blob_length": len(blob),
        "patch_address": address,
        "blob_crc32_ieee": f"{blob_crc:08x}",
        "blob_sha256": hashlib.sha256(blob).hexdigest(),
    }
    if asic != EXPECTED_ASIC:
        raise ValueError(f"unexpected ASIC {asic}")
    if declared_length != EXPECTED_LENGTH or len(blob) != declared_length:
        raise ValueError(f"unexpected blob length declared={declared_length} decoded={len(blob)}")
    if address != EXPECTED_ADDRESS:
        raise ValueError(f"unexpected patch address {address}")
    if blob_crc != EXPECTED_BLOB_CRC32:
        raise ValueError(f"unexpected IEEE blob CRC-32 {blob_crc:08x}")
    if result["kernel_export_sha256"] != EXPECTED_KERNEL_EXPORT_SHA256:
        raise ValueError("unexpected kernel-export SHA-256")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("header", type=Path, help="kernel bbd_patch_file_beyond.h")
    args = parser.parse_args(argv)
    try:
        result = verify(decode_c_string_literals(args.header))
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    print("PASS: host-only embedded patch identity verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
