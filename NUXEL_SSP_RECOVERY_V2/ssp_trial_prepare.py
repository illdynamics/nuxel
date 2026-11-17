#!/usr/bin/env python3
"""Host-only setup/check for an lhd sandbox with NO handset hardware access.

This is NOT a sensor driver and does not execute lhd. The existing
`tools/s10plus/ssp-runtime/run_isolated.py` is the separate runtime trial tool.
Only a newly staged host-directory is modified when --prepare is supplied.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

BLOCKED_PATHS={
    "GpioNPowerPath":"/no-hardware/gpio-power",
    "GpioNStdbyPath":"/no-hardware/gpio-standby",
    "LhePatch":"/no-hardware/bbd-patch",
    "LheBbdPacket":"/no-hardware/bbd-packet",
    "LheBbdControl":"/no-hardware/bbd-control",
    "LheBbdSensor":"/no-hardware/bbd-sensor",
    "LheBbdReliable":"/no-hardware/bbd-reliable",
    "LheSerialControl":"DISABLED_IN_ISOLATION",
    "LheMaxMcuResetTries":"0",
    "NvStorageDir":"/tmp/nv/",
    "LogDirectory":"/tmp/log/",
    "PortName":"tcp:127.0.0.1:300",
}
REQUIRED_FILES=("vendor/bin/hw/lhd", "vendor/etc/sensor/lhd.conf", "system/bin/linker64")
EXEC_TRIAL=("system/lib64/libssp-log-stderr.so",)


def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def safe_conf(source:bytes)->bytes:
    """Replace every active device path; no dangerous original endpoint remains."""
    text=source.decode('utf-8','strict')
    lines=[]; hit=set()
    for line in text.splitlines():
        m=re.match(r'^\s*([a-zA-Z][a-zA-Z0-9]*)\s*=.*$',line)
        if m and m.group(1) in BLOCKED_PATHS:
            key=m.group(1)
            if key not in hit:
                lines.append(key+'='+BLOCKED_PATHS[key])
                hit.add(key)
            continue
        lines.append(line)
    for key,val in BLOCKED_PATHS.items():
        if key not in hit:
            lines.append(key+'='+val)
    conf='\n'.join(lines)+'\n'
    for bad in ('/dev/bbd_patch','/dev/ttyBCM','/dev/bbd_control','/dev/bbd_sensor',
                '/sys/class/sec/gps/GPS_PWR_EN','/sys/class/sec/sensorhub/mcu_power'):
        if any(bad in l for l in conf.splitlines() if not l.lstrip().startswith('#')):
            raise RuntimeError('unexpected active unsafe path '+bad)
    return conf.encode('utf-8')


def walk_files(root:Path)->dict[str,bytes]:
    """No symlinks, special files, or untracked content permitted."""
    root=root.resolve(strict=True)
    data={}
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('symlink in staged runtime: '+str(p))
        if p.is_dir():continue
        if not p.is_file():raise ValueError('non-regular runtime entry: '+str(p))
        rel=p.relative_to(root).as_posix()
        if len(rel)>512:raise ValueError('overlong staged path')
        if p.stat().st_size>128*1024*1024:raise ValueError('oversized staged file: '+rel)
        if rel in ('sha256-manifest.json', 'ssp-stock-collection.json',
                   'ssp-runtime-audit.json', 'ssp-runtime-audit.md'):
            continue
        data[rel]=p.read_bytes()
    return data


def preflight(root:Path)->dict:
    data=walk_files(root)
    absent=[x for x in REQUIRED_FILES if x not in data]
    probe_ready=('isolation-probe' in data)
    shim_ready=(all(x in data for x in EXEC_TRIAL) or
                'vendor/lib64/libssp-log-stderr.so' in data)
    conf=data.get('vendor/etc/sensor/lhd-isolated.conf',b'')
    expected=safe_conf(data.get('vendor/etc/sensor/lhd.conf',b'')) if data.get('vendor/etc/sensor/lhd.conf') else b''
    safe=bool(conf) and conf==expected
    manifest=root/'sha256-manifest.json'
    mismatch=[]
    if manifest.exists():
        saved=json.loads(manifest.read_text())
        generated={rel:digest(b) for rel,b in data.items()}
        for rel in sorted(set(saved)|set(generated)):
            if saved.get(rel)!=generated.get(rel):mismatch.append(rel)
    return {"hardware_access":False,"write_to_phone":False,"missing_required":absent,
            "no_hardware_config_valid":safe,"probe_ready":probe_ready,
            "logshim_ready":shim_ready,"manifest_mismatches":mismatch,
            "runtime_files":len(data),
            "status":"OFFLINE_SANDBOX_PREFLIGHT_COMPLETE" if not absent and safe and not mismatch else "INCOMPLETE"}


def prepare(root:Path):
    root=root.resolve(strict=True)
    src=root/'vendor/etc/sensor/lhd.conf'
    if not src.is_file() or src.is_symlink():
        raise RuntimeError('original lhd.conf is missing or a symlink')
    if not (root/'vendor/bin/hw/lhd').is_file() or not (root/'system/bin/linker64').is_file():
        raise RuntimeError('missing lhd or matching Android linker64')
    target=root/'vendor/etc/sensor/lhd-isolated.conf'
    if target.exists() or target.is_symlink():
        raise RuntimeError('refusing to overwrite isolated config')
    # Scan BEFORE write to reject symlinks and hidden special files.
    walk_files(root)
    with target.open('xb') as f: f.write(safe_conf(src.read_bytes()))
    manifest=root/'sha256-manifest.json'
    if manifest.exists() or manifest.is_symlink():
        raise RuntimeError('refusing to overwrite existing manifest')
    data=walk_files(root)
    manifest.write_text(json.dumps({rel:digest(b) for rel,b in sorted(data.items())},indent=2)+'\n')
    return preflight(root)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path,help='HOST staged Android runtime root only')
    p.add_argument('--prepare',action='store_true',help='write safe isolated config and hash manifest to the HOST staging tree')
    p.add_argument('--report',type=Path,help='optional HOST output JSON')
    a=p.parse_args(argv)
    try:
        if a.prepare and str(a.root.resolve()).startswith(('/sys/', '/proc/', '/dev/')):
            raise ValueError('refusing virtual filesystem as staging root')
        result=prepare(a.root) if a.prepare else preflight(a.root)
        print(json.dumps(result,indent=2))
        if a.report:a.report.write_text(json.dumps(result,indent=2)+'\n')
        return 0 if result['status']=='OFFLINE_SANDBOX_PREFLIGHT_COMPLETE' else 3
    except (OSError,ValueError,RuntimeError,json.JSONDecodeError) as e:
        print('BLOCKED: '+str(e),file=sys.stderr)
        return 4

if __name__=='__main__':raise SystemExit(main())
