import base64,gzip,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[1])
rows=json.loads(gzip.decompress((root/'bundle.json.gz').read_bytes()))
receipt={'started_at':time.time(),'files':[],'status':'PREPARING'}
def save():
    (root/'receipt.json.tmp').write_text(json.dumps(receipt,indent=2)+'\n')
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
    receipt['home_state']=Path('/run/nuxel-home.state').read_text()[-16000:]
    receipt['presentation_state']=Path('/run/nuxel-wl-fb.state').read_text()
save()
for row in rows:
    rel=Path(row['path'])
    if rel.is_absolute() or '..' in rel.parts or rel.parts[:2] not in (('pwa','nuxel-home'),('pwa','nuxel-apps'),('pwa','nuxel-common')):
        raise RuntimeError('outside PWA scope')
    dst=Path('/usr/share/nuxel')/rel
    if dst.is_symlink() or not dst.resolve().is_relative_to('/usr/share/nuxel/pwa'):
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
