#!/usr/bin/env python3
"""Verify a coherent owner-stock set and prepare a HOST-only deployment proposal.

No SSH, device access, installation, networking or firmware execution. The stock
pin was independently reproduced from the owner-held AP; it is not the public
manifest, and hash validity does not establish the kernel's executable DDK ABI.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PIN = ROOT / 'firmware/s10plus/camera-stock-DTK9.json'

def verify(source, manifest):
    if source.is_symlink() or not source.is_dir():
        raise ValueError('source must be a real directory')
    if manifest['build'] != 'G975FXXS9DTK9' or manifest['device'] != 'SM-G975F':
        raise ValueError('wrong source provenance')
    rows = []
    for row in manifest['files']:
        name = row['name']
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('invalid source path')
        p = source / name
        if p.is_symlink() or not p.is_file():
            raise ValueError('missing or nonregular source: '+name)
        if p.stat().st_size != row['size']:
            raise ValueError('size mismatch: '+name)
        b = p.read_bytes()
        if hashlib.sha256(b).hexdigest() != row['sha256']:
            raise ValueError('hash mismatch: '+name)
        rows.append(dict(row))
    names = [r['name'] for r in rows]
    if len(names) != 9 or len(set(names)) != 9 or 'build.prop' not in names:
        raise ValueError('incomplete or duplicate source inventory')
    return rows

def prepare(source, destination):
    manifest = json.loads(PIN.read_text())
    rows = verify(source, manifest)
    if destination.exists() or destination.is_symlink():
        raise ValueError('destination must not exist')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.camera-stage-',dir=destination.parent) as d:
        stage = Path(d)/'candidate'
        stage.mkdir()
        for row in rows:
            shutil.copyfile(source/row['name'], stage/row['name'])
        verify(stage, manifest)  # catch changed source or truncated copy
        plan = {
            'status': 'BLOCKED_DDK_ABI_NOT_VERIFIED',
            'build': manifest['build'], 'archive_sha256': manifest['archive_sha256'],
            'physical_frame_verified': False,
            'hardware_authorized': False,
            'files': [dict(r, proposed_targets=[
                '/system/vendor/firmware/'+r['name'], '/vendor/firmware/'+r['name']],
                owner='root:root',mode='0644') for r in rows if r['name']!='build.prop'],
            'prerequisites': [
                'Resolve DTK9 Android 10 DDK versus FUBD-derived Android 11 kernel ABI',
                'Owner reviews exact bounded trial; no automatic hardware execution',
                'All target camera files absent; refuse overwrite or symbolic-link parents',
                'Confirm calibration-cache reset procedure and owner-present recovery'],
            'rollback': 'Remove only transaction-created files after verifying hashes; remove created empty directories. No BOOT write.',
        }
        (stage/'deployment-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        stage.rename(destination)
    return plan

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--destination',type=Path,required=True)
    args=ap.parse_args()
    try:
        print(json.dumps(prepare(args.source,args.destination),indent=2))
    except (OSError,ValueError,KeyError) as exc:
        ap.exit(2,str(exc)+'\n')
