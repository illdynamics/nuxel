#!/usr/bin/env python3
"""Deploy the small privileged haptics/navigation host bundle over live USB.

Each destination is backed up and hash verified before an atomic rename.  This
tool deliberately permits only the five listed userspace paths; it never opens
framebuffer or block devices and it does not restart the Wayland session.
"""
import base64, gzip, hashlib, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/beta/live'))
import nuxel_live as nl

FILES = {
 'build/out/s10plus/haptics/nuxel-pwa-host': '/usr/lib/nuxel/nuxel-pwa-host',
 'services/nuxel-haptics/nuxel-hapticsd.py': '/usr/lib/nuxel/nuxel-hapticsd.py',
 'services/nuxel-haptics/nuxel-haptics.service': '/etc/systemd/system/nuxel-haptics.service',
 'services/nuxel-haptics/nuxel-haptics-sleep': '/usr/lib/systemd/system-sleep/nuxel-haptics-sleep',
 'configs/nuxel/haptics/settings.json': '/etc/nuxel/haptics/settings.json',
}
INSTALL = r'''import gzip,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[1]); rows=json.loads(gzip.decompress((root/'bundle.gz').read_bytes()))
rec={'started_at':time.time(),'files':[],'status':'PREPARING'}
def save(): (root/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
changed=[]
try:
 for r in rows:
  dst=Path(r['target']); dst.parent.mkdir(parents=True,exist_ok=True)
  data=__import__('base64').b64decode(r['data']); assert hashlib.sha256(data).hexdigest()==r['sha256']
  old=sha(dst) if dst.exists() else None; bak=root/'backup'/dst.relative_to('/')
  if old: bak.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(dst,bak); assert sha(bak)==old
  tmp=dst.with_name(dst.name+'.nuxel-stage'); tmp.write_bytes(data); os.chmod(tmp,0o755 if r['executable'] else 0o644)
  assert sha(tmp)==r['sha256']; tmp.replace(dst); assert sha(dst)==r['sha256']; changed.append((dst,bak,old)); rec['files'].append({'target':str(dst),'old_sha256':old,'new_sha256':r['sha256'],'installed_sha256':sha(dst)})
 subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
 subprocess.run(['systemctl','enable','--now','nuxel-haptics.service'],check=True,timeout=20)
 subprocess.run(['systemctl','is-active','--quiet','nuxel-haptics.service'],check=True,timeout=5)
 rec['status']='DEPLOYED'
except Exception as e:
 rec['error']=str(e)
 for dst,bak,old in reversed(changed):
  if old: shutil.copy2(bak,dst)
  else: dst.unlink(missing_ok=True)
 rec['status']='ROLLED_BACK'
finally: rec['finished_at']=time.time(); save()
print(json.dumps(rec)); sys.exit(0 if rec['status']=='DEPLOYED' else 5)
'''
def main():
 rows=[]
 for source,target in FILES.items():
  data=(ROOT/source).read_bytes(); rows.append({'source':source,'target':target,'sha256':hashlib.sha256(data).hexdigest(),'data':base64.b64encode(data).decode(),'executable':source.endswith(('.py','nuxel-pwa-host','nuxel-haptics-sleep'))})
 evidence=ROOT/'docs/touchable/evidence/haptics-navigation-system'; evidence.mkdir(parents=True,exist_ok=True)
 (evidence/'plan.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='data'} for r in rows],indent=2)+'\n')
 phone='/var/tmp/nuxel-haptics-navigation-'+str(int(time.time()))
 c,_,_=nl.open_console(serial=nl.DEFAULT_SERIAL,timeout=20)
 with c:
  def run(cmd,timeout=30):
   r=c.run(cmd,timeout=timeout)
   if not r.ok: raise RuntimeError(cmd+' failed: '+r.output)
   return r.output
  run('test ! -e '+phone+' && mkdir -p '+phone)
  nl.push_bytes(c,gzip.compress(json.dumps(rows).encode(),mtime=0),phone+'/bundle.gz',mode='0600')
  nl.push_bytes(c,INSTALL.encode(),phone+'/install.py',mode='0700')
  out=run('/usr/bin/python3 '+phone+'/install.py '+phone,60); (evidence/'receipt.json').write_text(out+'\n')
  for r in rows:
   actual=run('sha256sum '+r['target']).split()[0]
   if actual != r['sha256']: raise RuntimeError('readback mismatch '+r['target'])
if __name__=='__main__': main()
