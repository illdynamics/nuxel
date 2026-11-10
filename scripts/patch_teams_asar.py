#!/usr/bin/env python3
"""Patch files inside an Electron ASAR without Node/npm.

Electron's ASAR container is:
    uint32le(4) | uint32le(header_pickle_len) | header_pickle | file data

The header pickle is:
    uint32le(payload_len) | uint32le(json_len) | json | zero padding

File offsets in the JSON are relative to the start of the file-data section.
This tool rewrites the archive, preserves ``unpacked`` entries, and recomputes
SHA-256 integrity for every packed file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
from typing import Dict, Tuple

BLOCK_SIZE = 4194304


def _u32(value: int) -> bytes:
    return struct.pack("<I", value)


def _read_header(fh) -> Tuple[dict, int]:
    first = fh.read(8)
    if len(first) != 8:
        raise ValueError("not an ASAR archive")
    size_pickle_len, header_pickle_len = struct.unpack("<II", first)
    if size_pickle_len != 4:
        raise ValueError("unsupported ASAR size-pickle length %d" % size_pickle_len)
    header_pickle = fh.read(header_pickle_len)
    if len(header_pickle) != header_pickle_len:
        raise ValueError("truncated ASAR header")
    payload_len = struct.unpack("<I", header_pickle[:4])[0]
    json_len = struct.unpack("<I", header_pickle[4:8])[0]
    payload = header_pickle[4:4 + payload_len]
    json_bytes = payload[4:4 + json_len]
    header = json.loads(json_bytes.decode("utf-8"))
    return header, 8 + header_pickle_len


def _walk(node: dict, prefix: str = ""):
    for name, entry in node.get("files", {}).items():
        path = prefix + "/" + name
        if "files" in entry:
            yield from _walk(entry, path)
        else:
            yield path, entry


def _integrity(data: bytes) -> dict:
    digest = hashlib.sha256(data).hexdigest()
    blocks = [hashlib.sha256(data[i:i + BLOCK_SIZE]).hexdigest()
              for i in range(0, len(data), BLOCK_SIZE)]
    return {"algorithm": "SHA256", "blockSize": BLOCK_SIZE,
            "blocks": blocks, "hash": digest}


def patch(asar_path: str, replacements: Dict[str, bytes]) -> bool:
    with open(asar_path, "rb") as fh:
        header, data_start = _read_header(fh)
        packed = []
        for path, entry in _walk(header):
            path = path.lstrip("/")
            if entry.get("unpacked"):
                continue
            offset = int(entry.get("offset", 0))
            size = int(entry.get("size", 0))
            fh.seek(data_start + offset)
            data = fh.read(size)
            if len(data) != size:
                raise ValueError("truncated file data: %s" % path)
            packed.append((path, entry, data))

    by_path = {path: (entry, data) for path, entry, data in packed}
    missing = sorted(set(replacements) - set(by_path))
    if missing:
        raise ValueError("target(s) not packed in ASAR: %s" % ", ".join(missing))

    st = os.stat(asar_path)
    new_chunks = []
    cursor = 0
    for path, entry, data in packed:
        if path in replacements:
            data = replacements[path]
            entry["integrity"] = _integrity(data)
        entry["offset"] = str(cursor)
        entry["size"] = len(data)
        new_chunks.append(data)
        cursor += len(data)

    json_bytes = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload = _u32(len(json_bytes)) + json_bytes
    payload += b"\x00" * ((4 - len(payload) % 4) % 4)
    header_pickle = _u32(len(payload)) + payload
    out_prefix = _u32(4) + _u32(len(header_pickle)) + header_pickle

    directory = os.path.dirname(os.path.abspath(asar_path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".asar-patch-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(out_prefix)
            for chunk in new_chunks:
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(tmp_path, st.st_mode)
        try:
            os.chown(tmp_path, st.st_uid, st.st_gid)
        except (AttributeError, PermissionError):
            pass
        os.replace(tmp_path, asar_path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    print("PATCHED %s (%d file(s), %d bytes)" % (asar_path, len(replacements), os.path.getsize(asar_path)))
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asar", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="PATH:SOURCE")
    ap.add_argument("--check", action="append", default=[], metavar="PATH")
    ap.add_argument("--backup", action="store_true")
    args = ap.parse_args()

    replacements: Dict[str, bytes] = {}
    for item in args.set:
        path, source = item.split(":", 1)
        with open(source, "rb") as fh:
            replacements[path.lstrip("/")] = fh.read()

    if args.backup:
        backup = args.asar + ".nuxel-orig"
        if not os.path.exists(backup):
            shutil.copy2(args.asar, backup)
            print("BACKUP %s" % backup)

    if args.check:
        with open(args.asar, "rb") as fh:
            header, data_start = _read_header(fh)
            entries = {p.lstrip("/"): e for p, e in _walk(header)}
            for path in args.check:
                path = path.lstrip("/")
                entry = entries.get(path)
                if not entry:
                    print("MISSING " + path)
                    return 1
                fh.seek(data_start + int(entry.get("offset", 0)))
                data = fh.read(int(entry.get("size", 0)))
                print(("OK " if data == replacements.get(path) else "DIFF ") + path)
        return 0

    if not replacements:
        raise SystemExit("nothing to do")
    patch(args.asar, replacements)
    return 0


if __name__ == "__main__":
    sys.exit(main())
