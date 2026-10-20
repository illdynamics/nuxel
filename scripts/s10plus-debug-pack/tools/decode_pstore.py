#!/usr/bin/env python3
"""Best-effort identification/decompression of local pstore records.
Not all kernels use gzip/zlib/bzip2/lzma; cannot decode arbitrary pstore formats.
"""
import argparse
import bz2
import gzip
import lzma
from pathlib import Path
import zlib

MAX_COMPRESSED = 16 * 1024 * 1024
MAX_DECOMPRESSED = 64 * 1024 * 1024

def try_decode(data):
    # Try common wrappers, preserve the original evidence always.
    for label, method in (
        ('gzip', gzip.decompress),
        ('zlib', zlib.decompress),
        ('bzip2', bz2.decompress),
        ('xz', lzma.decompress),
    ):
        try:
            out = method(data)
            if len(out) > MAX_DECOMPRESSED:
                return label, None, 'Result exceeds size cap'
            return label, out, None
        except (OSError, EOFError, ValueError, zlib.error, lzma.LZMAError):
            pass
    return 'unknown-or-plain-text', None, None

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('record', type=Path)
    ap.add_argument('--out', type=Path, default=Path('pstore-decoded'))
    a = ap.parse_args()
    size = a.record.stat().st_size
    if size > MAX_COMPRESSED:
        ap.error(f'Input larger than {MAX_COMPRESSED} bytes; manually inspect it')
    data = a.record.read_bytes()
    a.out.mkdir(parents=True, exist_ok=True)
    label, decompressed, warning = try_decode(data)
    print(f'Input bytes: {size}; format: {label}')
    if warning:
        print('WARNING:', warning)
    elif decompressed is not None:
        name = a.out / (a.record.name + '.decoded.txt')
        name.write_bytes(decompressed)
        print('Decoded into:', name)
    else:
        print('Cannot identify a supported compression wrapper; inspect with file/hexdump and retain the original.')

if __name__ == '__main__':
    main()
