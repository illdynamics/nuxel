#!/usr/bin/env python3
"""Build safe A43 userspace-only update with SHA256 manifest; no phone contact."""
from pathlib import Path
import tarfile,hashlib,json,sys,tempfile,shutil
root=Path(__file__).resolve().parents[3]
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'build/out/nuxel-v0.6.3-beta-live-userspace.tar.gz'
items=['pwa/nuxel-home/index.html','pwa/nuxel-home/manifest.json','pwa/nuxel-home/sw.js',
'pwa/nuxel-home/css/style.css','pwa/nuxel-home/css/launcher.css',
'pwa/nuxel-home/js/launcher.js','pwa/nuxel-home/js/gestures.js',
'pwa/nuxel-home/js/home-settings.js','pwa/nuxel-home/js/apps.js',
'pwa/nuxel-home/assets/nuxel-bottom-bar.jpg','pwa/nuxel-home/assets/nuxel-bottom-bar2.png',
'assets/nuxel-bottom-bar.jpg','assets/nuxel-bottom-bar2.png',
'pwa/nuxel-apps/settings/index.html','pwa/nuxel-apps/settings/settings.css',
'pwa/nuxel-apps/settings/wifi-settings.js',
'pwa/nuxel-common/app-registry.json',
'services/nuxel-bridge/src/api.py','services/nuxel-bridge/src/bridge.py']
manifest=[];out.parent.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='nuxel-a43-') as temp:
    stage=Path(temp)
    for rel in items:
        source=(root/rel)
        assert source.is_file() and not source.is_symlink(), rel
        dest=stage/'files'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dest)
        manifest.append({'source':rel,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size})
    (stage/'manifest.json').write_text(json.dumps({'version':'v0.6.3-beta','files':manifest},indent=2)+'\n')
    with tarfile.open(out,'w:gz') as tar:
        tar.add(stage/'manifest.json',arcname='manifest.json')
        for rel in items:tar.add(stage/'files'/rel,arcname='files/'+rel)
print(out,'sha256',hashlib.sha256(out.read_bytes()).hexdigest(),'files',len(items))
