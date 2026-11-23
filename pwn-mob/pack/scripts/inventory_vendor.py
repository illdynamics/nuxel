#!/usr/bin/env python3
"""Read-only owner-supplied extracted vendor/AP radio file inventory.

Ignores symbolic links and device nodes. Never copies or executes a vendor binary.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

INTERESTING = ('libsec-ril', 'libril_sem', 'libsecril-client', 'libvndsecril',
               'libsec_semril', 'rild', 'cbd', 'rfs', 'radio.bridge',
               'radio.channel', 'radio.sim', 'radio.data', 'radio.messaging',
               'init.baseband', 'init.vendor.ril', 'plmn_', 'vendor.prop')
IGNORE = {'.git', '.cache', 'node_modules', 'proc', 'sys', 'dev', 'run', 'tmp', '__pycache__'}


def inventory(root: Path, max_files: int = 250000) -> list:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('root must be a directory')
    results = []
    seen = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in IGNORE and not (Path(base) / d).is_symlink()]
        for name in sorted(files):
            seen += 1
            if seen > max_files:
                raise ValueError('scan exceeded file cap; use a narrower extracted vendor directory')
            if not any(term in name.lower() for term in INTERESTING):
                continue
            p = Path(base) / name
            if p.is_symlink() or not p.is_file():
                continue
            h = hashlib.sha256()
            with p.open('rb') as source:
                while chunk := source.read(1024 * 1024):
                    h.update(chunk)
            results.append({'path': str(p.relative_to(root)), 'bytes': p.stat().st_size,
                            'sha256': h.hexdigest()})
    return sorted(results, key=lambda e: e['path'])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('extracted_vendor_root', type=Path)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    found = inventory(a.extracted_vendor_root)
    if a.json:
        print(json.dumps({'files': found, 'count': len(found)}, indent=2))
    else:
        for record in found:
            print(f"{record['sha256']} {record['bytes']:10d} {record['path']}")
        print(f'Found {len(found)} candidate files. Hashes are SHA-256 of local inputs.')


if __name__ == '__main__':
    main()
