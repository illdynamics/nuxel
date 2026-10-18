#!/usr/bin/env python3
"""Install a reviewed PWA bundle using the existing exclusive USB console.

Stages all files first, verifies hashes, backs up originals, atomically replaces
each target, then restarts the Wayland session once. On failed service/readiness
checks the entire bundle is restored. No framebuffer device is opened.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/beta/live'))
import nuxel_live as nl

INSTALLER = '''import base64,gzip,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[1])
rows=json.loads(gzip.decompress((root/'bundle.json.gz').read_bytes()))
receipt={'started_at':time.time(),'files':[],'status':'PREPARING'}
def save():
    (root/'receipt.json.tmp').write_text(json.dumps(receipt,indent=2)+'\\n')
    (root/'receipt.json.tmp').replace(root/'receipt.json')
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def restart():
    subprocess.run(['systemctl','restart','nuxel-wayland'],check=True,timeout=40)
    for _ in range(80):
        ready=Path('/run/nuxel-launcher-ready')
        if ready.exists() and ready.stat().st_mtime>=receipt['started_at']:
            break
        time.sleep(.25)
    else: raise RuntimeError('launcher ready receipt absent/stale')
    subprocess.run(['systemctl','is-active','--quiet','nuxel-wayland','nuxel-wl-fb'],check=True,timeout=5)
    # The bridge reconnects after phoc. ActiveState alone can precede its first
    # presentation; require a fresh successful frame receipt as well.
    for _ in range(80):
        state=Path('/run/nuxel-wl-fb.state').read_text()
        if 'FRAMES_OK' in state and float(state.split()[0])>=receipt['started_at']:
            break
        time.sleep(.25)
    else: raise RuntimeError('no fresh framebuffer presentation receipt')
    receipt['home_state']=Path('/run/nuxel-home.state').read_text()[-16000:]
    receipt['presentation_state']=Path('/run/nuxel-wl-fb.state').read_text()
save()
for row in rows:
    rel=Path(row['path'])
    if rel.is_absolute() or '..' in rel.parts or rel.parts[:2] not in (('pwa','nuxel-home'),('pwa','nuxel-apps'),('pwa','nuxel-common')):
        raise RuntimeError('outside PWA scope')
    dst=Path('/usr/share/nuxel')/rel
    # This handset's pwa/nuxel-home is the measured ../nuxel-home symlink.
    if dst.is_symlink() or not any(dst.resolve().is_relative_to(p) for p in ('/usr/share/nuxel/pwa','/usr/share/nuxel/nuxel-home')):
        raise RuntimeError('unsafe target')
    body=base64.b64decode(row['data'],validate=True)
    if hashlib.sha256(body).hexdigest()!=row['sha256']: raise RuntimeError('payload mismatch')
    dst.parent.mkdir(parents=True,exist_ok=True)
    staged=dst.with_name(dst.name+'.touchable-stage')
    staged.write_bytes(body); staged.chmod(0o644)
    backup=root/'backup'/rel
    existed=dst.exists()
    old=digest(dst) if existed else None
    if existed:
        backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(dst,backup)
        if digest(backup)!=old: raise RuntimeError('backup mismatch')
    receipt['files'].append(dict(target=str(dst),staged=str(staged),backup=str(backup),existed=existed,old_sha256=old,new_sha256=row['sha256']))
save()
changed=[]
try:
    for row in receipt['files']:
        dst=Path(row['target']); staged=Path(row['staged'])
        if digest(staged)!=row['new_sha256']: raise RuntimeError('stage mismatch')
        staged.replace(dst); changed.append(row)
        row['installed_sha256']=digest(dst)
        if row['installed_sha256']!=row['new_sha256']: raise RuntimeError('installed mismatch')
    receipt['status']='INSTALLED'; save()
    restart()
    receipt['status']='DEPLOYED_UNVERIFIED'
except Exception as exc:
    receipt['error']=str(exc)
    for row in reversed(changed):
        dst=Path(row['target'])
        if row['existed']:
            tmp=dst.with_name(dst.name+'.touchable-restore')
            shutil.copy2(row['backup'],tmp); tmp.replace(dst)
            if digest(dst)!=row['old_sha256']: raise RuntimeError('rollback checksum mismatch')
        else: dst.unlink(missing_ok=True)
    receipt['status']='ROLLED_BACK'; save()
    try: restart()
    except Exception as err: receipt['rollback_error']=str(err)
finally:
    receipt['finished_at']=time.time(); save()
print(json.dumps(receipt,indent=2))
sys.exit(0 if receipt['status']=='DEPLOYED_UNVERIFIED' else 5)
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--label', required=True)
    ap.add_argument('files', nargs='+')
    args = ap.parse_args()
    if not re.fullmatch('[a-z0-9-]{1,45}', args.label): ap.error('invalid label')
    evidence = ROOT / 'docs/touchable/evidence' / args.label
    evidence.mkdir(parents=True, exist_ok=False)
    rows = []
    for filename in args.files:
        source = (ROOT / filename).resolve()
        rel = source.relative_to(ROOT)
        if rel.parts[:2] not in [('pwa','nuxel-home'), ('pwa','nuxel-common'), ('pwa','nuxel-apps')]:
            ap.error('only PWA assets may be installed')
        data = source.read_bytes()
        rows.append(dict(path=str(rel),sha256=hashlib.sha256(data).hexdigest(),data=base64.b64encode(data).decode()))
    (evidence / 'plan.json').write_text(json.dumps([{k:v for k,v in row.items() if k!='data'} for row in rows],indent=2)+'\n')
    (evidence / 'install.py').write_text(INSTALLER)
    phone = '/var/tmp/nuxel-' + args.label
    frames = []
    def run(c, cmd, timeout=15):
        r=c.run(cmd,timeout=timeout)
        frames.append(dict(command=cmd,output=r.output,**r.as_dict()))
        (evidence/'console-receipts.json').write_text(json.dumps(frames,indent=2)+'\n')
        if not r.ok: raise RuntimeError('unverified command; inspect phone receipt before retry: '+cmd)
        return r.output
    c,_,_=nl.open_console(serial=nl.DEFAULT_SERIAL,timeout=20)
    with c:
        run(c,'test ! -e /run/nuxel-owner-test.lock && test ! -e '+phone+' && mkdir -p '+phone)
        (evidence/'before.txt').write_text(run(c,'uname -smr; cat /proc/sys/kernel/random/boot_id; systemctl is-active nuxel-wayland nuxel-wl-fb; cat /run/nuxel-wl-fb.state'))
        print('Staging',len(rows),'PWA files; original hashes/backups will be retained at',phone,flush=True)
        pushed = nl.push_bytes(c,gzip.compress(json.dumps(rows).encode(),mtime=0),phone+'/bundle.json.gz',mode='0600')
        nl.push_bytes(c,INSTALLER.encode(),phone+'/install.py',mode='0600')
        (evidence/'push.json').write_text(json.dumps(pushed,indent=2)+'\n')
        # Phone keeps running this bounded install if the USB response is lost.
        run(c,'systemd-run --quiet --unit=nuxel-'+args.label+' --property=RuntimeMaxSec=120 /usr/bin/python3 '+phone+'/install.py '+phone)
        deadline=time.monotonic()+115
        while time.monotonic()<deadline:
            result=run(c,'cat '+phone+'/receipt.json')
            receipt=json.loads(result)
            if receipt.get('finished_at'): break
            time.sleep(1)
        else: raise RuntimeError('deployment deadline reached; inspect '+phone+'/receipt.json')
        (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        for row in receipt['files']:
            actual=run(c,'sha256sum '+row['target']).split()[0]
            row['readback_sha256']=actual
            if actual != row.get('installed_sha256') or receipt['status']!='DEPLOYED_UNVERIFIED':
                raise RuntimeError('deployment not accepted; inspect rollback receipt')
        (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(receipt['status'],len(receipt['files']),'destination hashes verified',flush=True)


if __name__=='__main__': main()
