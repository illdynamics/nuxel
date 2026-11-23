#!/usr/bin/env python3
"""Pure read-only, standard-library triage for an owner-supplied AP-side RIL ELF.

Does not disassemble commands, infer semantics, load libraries, use a phone,
connect to networks, or export raw firmware. Review output before sharing.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

KEYWORDS = re.compile(r'(?i)(?:sipc|rfs|ipcprotocol|secril|rild|\buicc\b|\bsim\b|\bpdp\b|\blte\b|apn|bearer|regist|/dev/umts|ril_|cass|efs|shmem|network)')
ASCII_RUNS = re.compile(rb'[\x20-\x7e]{5,200}')
MACHINES = {40: 'ARM', 183: 'AArch64', 62: 'x86_64', 3: 'i386'}


def inspect(path: Path, limit: int = 40, max_bytes: int = 128 * 1024 * 1024) -> dict:
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError('input must be a regular file')
    if path.stat().st_size > max_bytes:
        raise ValueError(f'file exceeds read cap of {max_bytes} bytes')
    blob = path.read_bytes()
    out = {'filename': path.name, 'bytes': len(blob),
           'sha256': hashlib.sha256(blob).hexdigest(),
           'reads_only': True, 'note': 'String matches are hints, NOT decoded CP commands'}
    if len(blob) < 20 or blob[:4] != b'\x7fELF':
        out.update({'is_elf': False, 'error': 'not a valid ELF identification header'})
        return out
    elf_class = {1: 'ELF32', 2: 'ELF64'}.get(blob[4], 'UNKNOWN')
    endian = {1: 'little', 2: 'big'}.get(blob[5], 'unknown')
    out.update({'is_elf': True, 'elf_class': elf_class, 'endian': endian})
    if endian != 'unknown':
        machine = struct.unpack_from('<H' if endian == 'little' else '>H', blob, 18)[0]
        out['machine'] = MACHINES.get(machine, f'e_machine={machine}')
    hits = []
    total = 0
    # No raw binary bytes are printed; only ASCII strings containing selected terms.
    for match in ASCII_RUNS.finditer(blob):
        string = match.group(0).decode('ascii')
        if KEYWORDS.search(string):
            total += 1
            if len(hits) < limit:
                hits.append({'file_offset': f'0x{match.start():x}', 'ascii': string[:140]})
    out.update({'keyword_strings_total': total,
                'keyword_strings_shown': len(hits), 'keyword_string_examples': hits})
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf', type=Path)
    p.add_argument('--max-hits', type=int, default=40)
    p.add_argument('--max-mib', type=int, default=128)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    if not 0 <= a.max_hits <= 500 or not 1 <= a.max_mib <= 1024:
        p.error('max-hits must be 0..500; max-mib 1..1024')
    result = inspect(a.elf, a.max_hits, a.max_mib * 1024 * 1024)
    if a.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2))
        print('\nReview output for sensitive identifiers before sharing. No semantics inferred.')


if __name__ == '__main__':
    main()
