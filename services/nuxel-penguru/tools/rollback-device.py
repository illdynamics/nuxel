#!/usr/bin/env python3
"""Restore a PenGuru file-install receipt; preserve models, trust and accounts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Root required on the handset')
    receipt = args.receipt.resolve()
    if not receipt.is_relative_to('/var/backups/nuxel-penguru'):
        parser.error('Receipt must be from the PenGuru backup directory')
    records = json.loads(receipt.read_text())
    for record in records:
        target = Path(record['target'])
        if target.is_symlink() or not target.is_file():
            raise RuntimeError('Target changed since installation: ' + str(target))
        if hashlib.sha256(target.read_bytes()).hexdigest() != record['sha256']:
            raise RuntimeError('Preserving post-install edits: ' + str(target))
        if record['existed']:
            backup = Path(record['backup']).resolve()
            if backup.parent != receipt.parent or not backup.is_file():
                raise RuntimeError('Invalid backup path')
            if record.get('old_sha256') and hashlib.sha256(backup.read_bytes()).hexdigest() != record['old_sha256']:
                raise RuntimeError('Backup checksum mismatch')
    subprocess.run(['systemctl', 'stop', 'nuxel-penguru-download', 'nuxel-penguru'], check=True)
    for record in reversed(records):
        target = Path(record['target'])
        if record['existed']:
            staged = target.with_name(target.name + '.penguru-restore')
            shutil.copy2(record['backup'], staged)
            if 'old_uid' in record:
                os.chown(staged, record['old_uid'], record['old_gid'])
            staged.replace(target)
        else:
            target.unlink()
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'restart', 'nuxel-http-bridge'], check=True)
    print('Restored files. Model data, trust keys and service account are preserved. PenGuru is OFF.')


if __name__ == '__main__':
    main()
