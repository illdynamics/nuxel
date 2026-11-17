#!/usr/bin/env python3
"""Compare a saved /sys/kernel/notes capture with an offline AArch64 vmlinux.

Never connects to a handset or opens devices. Build-ID equality selects a build
artifact; it is not a cryptographic attestation of all running kernel memory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

MAX_NOTES = 65536


def build_ids(notes):
    if not notes or len(notes) > MAX_NOTES:
        raise ValueError('empty or oversized notes')
    ids, cursor = set(), 0
    while cursor < len(notes):
        if len(notes) - cursor < 12:
            raise ValueError('truncated note header')
        namesz, descsz, typ = struct.unpack_from('<III', notes, cursor)
        name_start = cursor + 12
        desc_start = name_start + ((namesz + 3) & ~3)
        end = desc_start + ((descsz + 3) & ~3)
        if end > len(notes):
            raise ValueError('truncated note body/padding')
        if notes[name_start:name_start + namesz] == b'GNU\0' and typ == 3:
            if not descsz:
                raise ValueError('empty build ID')
            ids.add(notes[desc_start:desc_start + descsz].hex())
        cursor = end
    return ids


def elf_build_id(path):
    with Path(path).open('rb') as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:6] != b'\x7fELF\x02\x01':
            raise ValueError('requires ELF64 little-endian kernel')
        if struct.unpack_from('<H', header, 18)[0] != 183:
            raise ValueError('requires AArch64 kernel')
        offset = struct.unpack_from('<Q', header, 32)[0]
        size, count = struct.unpack_from('<HH', header, 54)
        if size != 56 or not 0 < count <= 128:
            raise ValueError('unsupported ELF program table')
        ids = set()
        for i in range(count):
            stream.seek(offset + i * size)
            ph = stream.read(size)
            if len(ph) != size:
                raise ValueError('truncated program table')
            typ, _, fileoff, _, _, filesz, _, _ = struct.unpack('<IIQQQQQQ', ph)
            if typ == 4:  # PT_NOTE
                if not 0 < filesz <= MAX_NOTES:
                    raise ValueError('invalid note segment size')
                stream.seek(fileoff)
                notes = stream.read(filesz)
                if len(notes) != filesz:
                    raise ValueError('truncated note segment')
                ids.update(build_ids(notes))
    if len(ids) != 1:
        raise ValueError('requires exactly one distinct GNU build ID')
    return ids.pop()


def compare(kernel, saved_notes):
    with Path(saved_notes).open('rb') as stream:
        notes = stream.read(MAX_NOTES + 1)
    ids = build_ids(notes)
    if len(ids) != 1:
        raise ValueError('capture must contain one distinct GNU build ID')
    live_id = ids.pop()
    local_id = elf_build_id(kernel)
    digest = hashlib.sha256()
    with Path(kernel).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'kind': 'OFFLINE comparison of owner-provided live note capture',
            'kernel_sha256': digest.hexdigest(), 'local_build_id': local_id,
            'saved_live_build_id': live_id, 'build_id_matches': live_id == local_id,
            'notes_sha256': hashlib.sha256(notes).hexdigest(), 'notes_hex': notes.hex(),
            'limit': 'not runtime-memory attestation, source-tree identity, or hardware acceptance'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vmlinux', type=Path)
    parser.add_argument('saved_notes', type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.vmlinux, args.saved_notes)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'identity comparison refused: {exc}\n')
    print(json.dumps(result, indent=2))
    return 0 if result['build_id_matches'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
