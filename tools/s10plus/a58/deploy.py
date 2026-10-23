#!/usr/bin/env python3
"""Stage/verify only SnekByte on the existing Nuxel USB console, then promote.
No services, shell registry, system settings, partitions or player data are changed.
Usage: python3 tools/s10plus/a58/deploy.py --deploy
"""
import argparse,hashlib,io,json,shlex,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/beta/live'))
import nuxel_live as nl
SOURCE=ROOT/'pwa/nuxel-apps/snekbyte'
LIVE='/usr/share/nuxel/pwa/nuxel-apps/snekbyte'
BACKUP='/var/lib/nuxel/snekbyte-a58-before'
FILES=[p for p in SOURCE.rglob('*') if p.is_file() and 'tests' not in p.relative_to(SOURCE).parts]
def command(c,script):
    r=c.run('python3 -c '+shlex.quote(script),timeout=25)
    if r.rc!=0 or not r.sha_ok:raise RuntimeError(r.output)
    return r.output.strip()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--deploy',action='store_true');args=parser.parse_args()
    manifest={str(p.relative_to(SOURCE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    if not args.deploy:print(json.dumps(manifest,indent=2));return
    stage=LIVE+'-a58-stage-'+str(int(time.time()));old=stage+'-previous'
    c,node,notes=nl.open_console(timeout=10)
    try:
        c.open()
        print(command(c,'import shutil,pathlib; src='+repr(LIVE)+'; backup='+repr(BACKUP)+'; '
                        'shutil.copytree(src,backup) if not pathlib.Path(backup).exists() else None; '
                        'shutil.copytree(src,'+repr(stage)+'); print("backup and stage ready")'),flush=True)
        # Hash before sending: identical icons and runtime files need no write.
        existing=json.loads(command(c,'import pathlib,hashlib,json; root=pathlib.Path('+repr(stage)+'); '
                  'print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}))'))
        payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as archive:
            for p in FILES:
                rel=str(p.relative_to(SOURCE))
                if existing.get(rel)!=manifest[rel]:archive.writestr(rel,p.read_bytes())
            archive.writestr('.a58/manifest.json',json.dumps(manifest))
            promote='''import pathlib,hashlib,json,os,shutil
stage=pathlib.Path(__file__).resolve().parents[1]
expected=json.loads((stage/'.a58/manifest.json').read_text())
assert all(hashlib.sha256((stage/p).read_bytes()).hexdigest()==h for p,h in expected.items())
live=stage.parent/'snekbyte'
old=pathlib.Path(str(stage)+'-previous')
os.rename(live,old)
try: os.rename(stage,live)
except Exception:
 os.rename(old,live)
 raise
shutil.rmtree(live/'.a58')
print('PROMOTED '+hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest())
'''
            archive.writestr('.a58/promote.py',promote)
        data=payload.getvalue();archive_path=stage+'.zip'
        # Same conservative, verified USB transport, fewer bytes. A failed
        # stage never replaces the working game; retries are idempotent.
        for attempt in range(3):
            try:
                r=nl.push_bytes(c,data,archive_path,mode='0644')
                if r['decoded_sha256']!=hashlib.sha256(data).hexdigest():raise RuntimeError('Archive hash mismatch')
                break
            except nl.ConsoleLost:
                if attempt==2:raise
                c.interrupt()
        print(command(c,'import zipfile; zipfile.ZipFile('+repr(archive_path)+').extractall('+repr(stage)+'); print("staged archive verified")'),flush=True)
        r=c.run('python3 '+stage+'/.a58/promote.py',timeout=25)
        want='PROMOTED '+hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
        if not r.sha_ok or r.rc or want not in r.output:raise RuntimeError(r.output)
        print(want,flush=True)
        r=c.run('curl -fsS http://127.0.0.1:8000/pwa/nuxel-apps/snekbyte/js/snek-controls.js | sha256sum',timeout=15)
        if r.rc or manifest['js/snek-controls.js'] not in r.output:raise RuntimeError('HTTP verification failed: '+r.output)
        print('HTTP verified '+r.output.strip(),flush=True)
        (ROOT/'docs/a58-snakepwn-7000/evidence/deployed-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    finally:c.close()
if __name__=='__main__':main()
