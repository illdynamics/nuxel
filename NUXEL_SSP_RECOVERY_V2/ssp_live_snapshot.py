#!/usr/bin/env python3
"""Capture repeatable, READ-ONLY sensor evidence from a reachable SSH phone.

No firmware uploads, GPIO writes, sysfs writes, device-node opens, or flashes.
Use --capture-readonly explicitly and gently rotate the phone during sampling.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

FIELDS={
    'accelerometer':'/sys/class/sensors/accelerometer_sensor/raw_data',
    'gyroscope':'/sys/class/sensors/gyro_sensor/raw_data',
    'ssp_enable':'/sys/class/sensors/ssp_sensor/enable',
    'mcu_name':'/sys/class/sensors/ssp_sensor/mcu_name',
    'mcu_rev':'/sys/class/sensors/ssp_sensor/mcu_rev',
    'mcu_power':'/sys/class/sec/sensorhub/mcu_power',
}
COMMAND='; '.join([
    "printf 'KERNEL='; uname -a",
    *[f"printf 'FIELD:{key}='; cat {shlex.quote(path)} 2>/dev/null || printf UNAVAILABLE; printf '\\n'"
      for key,path in FIELDS.items()]
])

def parse(output: str) -> dict:
    values={'kernel':None, **{k:None for k in FIELDS}}
    for line in output.splitlines():
        if line.startswith('KERNEL='):
            values['kernel']=line[7:].strip() or None
        elif line.startswith('FIELD:') and '=' in line:
            key,value=line[6:].split('=',1)
            if key in FIELDS:
                values[key]=value.strip() if value.strip()!='UNAVAILABLE' else None
    return values


def vector(s):
    if not s:return None
    parts=[x.strip() for x in s.split(',')]
    if len(parts)!=3:return None
    try:
        values=tuple(float(x) for x in parts)
        return values if all(math.isfinite(x) for x in values) else None
    except ValueError:return None


def evaluate(samples):
    result={}
    for name in ('accelerometer','gyroscope'):
        vectors=[vector(s.get(name)) for s in samples]
        valid=[v for v in vectors if v is not None]
        unique=list(dict.fromkeys(valid))
        if not valid:status='NOT_EXPOSED'
        elif all(v==(0,0,0) for v in valid):status='ALL_ZERO'
        elif len(unique)>=2:status='CHANGING_SAMPLES'
        else:status='STATIC_SAMPLES'
        result[name]={'status':status,'valid_samples':len(valid),'distinct_vectors':len(unique)}
    result['real_motion_verified']=False
    result['reason']='Samples changing across a time series are suggestive, but a physical operator must corroborate rotation and axis mapping; no hardware proof in offline environment.'
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host',required=True,help='SSH hostname/IP of Nuxel handset')
    p.add_argument('--ssh-user',default='root')
    p.add_argument('--identity-file',type=Path,help='SSH private key path (passed to ssh, never read or recorded)')
    p.add_argument('--output',required=True,type=Path,help='new HOST JSON file')
    p.add_argument('--samples',type=int,default=8)
    p.add_argument('--interval',type=float,default=0.75)
    p.add_argument('--capture-readonly',action='store_true')
    a=p.parse_args(argv)
    if not (1<=a.samples<=40 and .2<=a.interval<=10):p.error('samples 1..40; interval .2..10')
    if not re.fullmatch(r'[a-zA-Z0-9_.:-]+',a.host) or not re.fullmatch(r'[a-z_][a-z0-9_-]*',a.ssh_user):
        p.error('invalid SSH host/user')
    if not a.capture_readonly:
        print('PLAN ONLY. Use --capture-readonly when SSH works and the phone can be gently rotated.')
        print('Read-only paths:',*FIELDS.values(),sep='\n  ')
        return 0
    if a.output.exists():p.error('refusing to overwrite report')
    samples=[]
    for i in range(a.samples):
        cmd=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5',
             '-o','StrictHostKeyChecking=yes']
        if a.identity_file:
            cmd += ['-i',str(a.identity_file.expanduser())]
        cmd += [f'{a.ssh_user}@{a.host}',COMMAND]
        started=datetime.now(timezone.utc).isoformat()
        try:
            r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        except (OSError,subprocess.TimeoutExpired) as e:
            print('SSH unavailable; no hardware conclusion:',str(e),file=sys.stderr)
            return 4
        if r.returncode:
            print('SSH exited non-zero; no hardware conclusion:',r.stderr.decode('utf8','replace')[:250],file=sys.stderr)
            return 4
        # Retain raw samples as evidence, never claim these prove physical movement.
        sample=parse(r.stdout.decode('utf8','replace'))
        sample['started_utc']=started
        sample['completed_utc']=datetime.now(timezone.utc).isoformat()
        samples.append(sample)
        if i+1<a.samples:time.sleep(a.interval)
    obj={'status':'READONLY_SNAPSHOT','hardware_writes':0,'samples':samples,
         'classification':evaluate(samples)}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf8') as report:
        report.write(json.dumps(obj,indent=2)+'\n')
    print(json.dumps(obj['classification'],indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
