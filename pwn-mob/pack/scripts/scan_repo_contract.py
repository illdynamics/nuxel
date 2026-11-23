#!/usr/bin/env python3
"""Non-mutating inventory of Nuxel source contract locations and evidence names.

No kernel build, IOCTL, device I/O, reboot, or shell command is invoked.
"""
import argparse
import json
import os
from pathlib import Path

FILE_NAMES = {'sipc5.h', 'modem_prj.h', 'modem_v1.h', 'link_device_shmem.c',
              'sipc5_fmt.c', 'sipc5_fmt.h', 'rfs_proto.c', 'rfs_proto.h',
              'rfs_policy.c', 'rfs_policy.h', 'radiod.c', 'transport.c',
              'ARCHITECTURE-DECISION.md', 'S5000AP-05-RFS-SIPC.md'}
IGNORE = {'.git', '.build', 'node_modules', '.cache', 'dist', 'build', 'target',
          '.venv', 'vendor', 'packs', '__pycache__'}
NEEDLES = ('SIPC5_CH_ID_RFS_0', 'SIPC5_CH_ID_FMT_0', 'struct sipc5',
           'ipc_version', 'DELETE_ALL_VIS', 'AST_POWERON', 'IOCTL_MODEM_STATUS',
           'modem_state', 'nl.nuxel.Radio1')


def scan(root: Path, cap: int = 250000) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Nuxel repo path must be directory')
    found = []
    traversed = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in IGNORE and not (Path(base) / d).is_symlink()]
        for name in files:
            traversed += 1
            if traversed > cap:
                raise ValueError('scanned too many files; specify narrower repo source path')
            if name not in FILE_NAMES:
                continue
            p = Path(base) / name
            if p.is_symlink() or not p.is_file() or p.stat().st_size > 5_000_000:
                continue
            text = p.read_text(errors='replace')
            matches = []
            for i, line in enumerate(text.splitlines(), 1):
                terms = [n for n in NEEDLES if n in line]
                if terms:
                    matches.append({'line': i, 'tokens': terms})
            found.append({'path': str(p.relative_to(root)), 'size': p.stat().st_size,
                          'matching_lines': matches[:100],
                          'total_matching_lines': len(matches)})
    return {'root': str(root), 'visited': traversed,
            'source_files': sorted(found, key=lambda x: x['path']),
            'note': 'Occurrences are not proof of protocol semantics'}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repo_root', type=Path)
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    result = scan(args.repo_root)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for f in result['source_files']:
            print(f"{f['path']} ({f['total_matching_lines']} matched lines)")
        print(f"Found {len(result['source_files'])} contract source files")


if __name__ == '__main__':
    main()
