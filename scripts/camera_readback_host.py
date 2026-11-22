#!/usr/bin/env python3
"""Read-only Nuxel partition + active-FDT capture to a PRIVATE host directory.

This tool never executes device-side writes, reboots, or flashes. It does not
identify partitions for you; authoritative labels must be verified separately.
Use only on a verified SSH target with trusted host keys.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PARTITION_RE = re.compile(r'^/dev/(?:sd[a-z]+\d+|mmcblk\d+p\d+|nvme\d+n\d+p\d+)$')
TARGET_RE = re.compile(r'^[A-Za-z0-9_.@:\[\]-]+$')
SHA_RE = re.compile(r'^[0-9a-f]{64}$')


def ssh(target, command, *, stdout=subprocess.PIPE, timeout=300):
    # Strict verification prevents automatically accepting unexpected SSH identities.
    return subprocess.run(['ssh', '-T', '-o', 'BatchMode=yes',
                           '-o', 'StrictHostKeyChecking=yes',
                           '-o', 'ConnectTimeout=15', target, command],
                          stdout=stdout, stderr=subprocess.PIPE, timeout=timeout)


def remote_text(target, command):
    res = ssh(target, command)
    if res.returncode:
        raise RuntimeError(f'read-only SSH command failed: {command}: {res.stderr.decode(errors="replace")[-500:]}')
    return res.stdout.decode(errors='replace').strip()


def remote_sha(target, path):
    out = remote_text(target, f'sha256sum {path}')
    h = out.split()[0].lower() if out.split() else ''
    if not SHA_RE.fullmatch(h):
        raise RuntimeError(f'no parseable SHA256 returned for {path}')
    return h


def capture_stream(target, path, outfile, expected_size=None):
    tmp = outfile.with_name(outfile.name + '.partial')
    if tmp.exists() or outfile.exists():
        raise RuntimeError(f'refusing to overwrite existing capture: {outfile}')
    before = remote_sha(target, path)
    remote_cmd = f'dd if={path} bs=1048576 status=none' if path.startswith('/dev/') else f'cat {path}'
    proc = subprocess.Popen(['ssh', '-T', '-o', 'BatchMode=yes',
                             '-o', 'StrictHostKeyChecking=yes',
                             '-o', 'ConnectTimeout=15', target, remote_cmd],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    h = hashlib.sha256()
    n = 0
    try:
        with tmp.open('xb') as out:
            os.chmod(tmp, 0o600)
            while True:
                chunk = proc.stdout.read(1048576)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                n += len(chunk)
            out.flush()
            os.fsync(out.fileno())
        error = proc.stderr.read().decode(errors='replace')
        rc = proc.wait()
        if rc:
            raise RuntimeError(f'SSH read failed for {path} (exit {rc}): {error[-500:]}')
        after = remote_sha(target, path)
        if before != after or before != h.hexdigest():
            raise RuntimeError(f'source/host SHA256 disagreement for {path}')
        if expected_size is not None and n != expected_size:
            raise RuntimeError(f'capture size mismatch for {path}: {n} != {expected_size}')
        tmp.rename(outfile)
        return {'path': str(outfile), 'sha256': h.hexdigest(), 'size_bytes': n,
                'source_sha256_before': before, 'source_sha256_after': after}
    except Exception:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        raise


def private_dir(path):
    p = Path(path).expanduser().resolve()
    if not p.is_absolute():
        raise RuntimeError('output directory must resolve to an absolute private host path')
    if p.exists() and list(p.iterdir()):
        raise RuntimeError('choose a NEW EMPTY private output directory; never overwrite old captures')
    for anc in (p, *p.parents):
        if (anc / '.git').exists():
            raise RuntimeError('private readback output must not be anywhere inside a Git repository')
    p.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(p, 0o700)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--device', required=True, help='Verified SSH target, e.g. root@10.11.12.99')
    ap.add_argument('--private-dir', required=True, help='NEW EMPTY host-only folder OUTSIDE the repo')
    for name in ('boot', 'dtb', 'dtbo', 'recovery'):
        ap.add_argument('--' + name, required=True, help='CONFIRMED partition block path, not a guess')
    ap.add_argument('--confirm-mapping', action='store_true',
                    help='I have independently reviewed the partition map and SSH host identity')
    a = ap.parse_args()
    if not a.confirm_mapping:
        ap.error('requires --confirm-mapping after independent partition identification')
    if not TARGET_RE.fullmatch(a.device) or not a.device.startswith('root@'):
        ap.error('device must be a validated root@host SSH target; shell metacharacters refused')
    partition_map = {name: getattr(a, name) for name in ('boot', 'dtb', 'dtbo', 'recovery')}
    if not all(PARTITION_RE.fullmatch(x) for x in partition_map.values()):
        ap.error('all partition paths must be explicit and match known block-device syntax')
    if len(set(partition_map.values())) != len(partition_map):
        ap.error('partition device paths must be distinct')
    # Preflight before touching output directory.
    cmdline = remote_text(a.device, 'cat /proc/cmdline')
    if 'androidboot.revision=26' not in cmdline or 'androidboot.dtbo_idx=9' not in cmdline:
        raise RuntimeError('current cmdline does not independently corroborate rev26 + selected DTBO index9; STOP')
    model = remote_text(a.device, 'tr "\\000" " " </proc/device-tree/model')
    if 'BEYOND2LTE' not in model.upper():
        raise RuntimeError('device does not identify as beyond2lte; STOP')
    root_source = remote_text(a.device, 'findmnt -n -o SOURCE /')
    # Any root-device mapping ambiguity should be reviewed before capture.
    if root_source in partition_map.values():
        raise RuntimeError('a selected partition appears to be the active root filesystem; STOP')
    part_detail = remote_text(a.device, 'lsblk -b -o NAME,TYPE,SIZE,PARTLABEL,PARTUUID,MOUNTPOINTS')
    size_map = {}
    for name, path in partition_map.items():
        exists = remote_text(a.device, f'test -b {path} && printf PRESENT')
        if exists != 'PRESENT':
            raise RuntimeError(f'not a block device: {path}')
        sz = remote_text(a.device, f'blockdev --getsize64 {path}')
        if not sz.isdigit() or int(sz) <= 0:
            raise RuntimeError(f'unknown/nonpositive partition size: {path}')
        size_map[name] = int(sz)
    if remote_text(a.device, 'test -r /sys/firmware/fdt && printf PRESENT') != 'PRESENT':
        raise RuntimeError('raw active /sys/firmware/fdt not readable; STOP')
    out = private_dir(a.private_dir)
    meta = out / 'metadata'
    meta.mkdir(mode=0o700)
    details = {'capture_utc': datetime.now(timezone.utc).isoformat(),
               'status': 'RAW_CAPTURE_NOT_YET_OWNER_APPROVED',
               'device': a.device, 'cmdline': cmdline,
               'model': model, 'root_source': root_source,
               'partition_map': partition_map, 'partition_bytes': size_map,
               'artifacts': {}}
    (meta / 'cmdline.txt').write_text(cmdline + '\n')
    (meta / 'model.txt').write_text(model + '\n')
    (meta / 'lsblk.txt').write_text(part_detail + '\n')
    (meta / 'uname.txt').write_text(remote_text(a.device, 'uname -a') + '\n')
    for name, path in partition_map.items():
        print(f'Capturing {name} from {path} (READ ONLY)', file=sys.stderr, flush=True)
        details['artifacts'][name] = capture_stream(a.device, path,
            out / ('current-' + name + '.img'), size_map[name])
    print('Capturing active merged FDT (READ ONLY)', file=sys.stderr, flush=True)
    details['artifacts']['merged_fdt'] = capture_stream(a.device,
        '/sys/firmware/fdt', out / 'active-merged.fdt')
    (out / 'raw-capture.NOT_SIGNED.json').write_text(json.dumps(details, indent=2, sort_keys=True) + '\n')
    for path in (out / 'raw-capture.NOT_SIGNED.json', *meta.iterdir()):
        path.chmod(0o600)
    print(json.dumps({'output_dir': str(out), 'status': details['status'],
                      'artifacts': {k: {'sha256': v['sha256'], 'size_bytes': v['size_bytes']}
                                    for k, v in details['artifacts'].items()}}, indent=2))
    print('NOTE: this is a readback, NOT signed Prompt00, partition semantic proof, or TWRP proof.', file=sys.stderr)

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print('FAIL CLOSED: ' + str(exc), file=sys.stderr)
        sys.exit(1)
