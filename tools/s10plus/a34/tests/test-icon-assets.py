#!/usr/bin/env python3
"""Verify actual UI art resolves from both repo and S10+ image/web root."""
from pathlib import Path
import json
import re
from urllib.parse import urljoin, urlparse

ROOT=Path(__file__).resolve().parents[4]
INDEX=(ROOT/'pwa/nuxel-home/index.html').read_text()
APPS=(ROOT/'pwa/nuxel-home/js/apps.js').read_text()
BASE='http://127.0.0.1:8000/pwa/nuxel-home/index.html'
paths=re.findall(r'src=["\'](/assets/[^"\']+\.png\?v=a37)',INDEX)
paths+=re.findall(r"'(/assets/[^']+\.png\?v=a37)'",APPS)
assert len(paths)>=20,len(paths)
canonical={urlparse(urljoin(BASE,url)).path for url in paths}
for path in sorted(canonical):
    assert path.startswith('/assets/'),path
    assert (ROOT/path.lstrip('/')).is_file(),path
    assert (ROOT/path.lstrip('/')).stat().st_size>100,path
assert {'/assets/button-left.png','/assets/button-middle.png','/assets/button-right.png'}<=canonical
assert '/assets/nuxel-applications-icon-pack/01-01_terminal.png' in canonical
assert '/assets/nuxel-quicksettings-icon-pack/01-wifi.png' in canonical
manifest=json.loads((ROOT/'tools/beta/live/deploy-manifest.json').read_text())
g=next(g for g in manifest['groups'] if g['id']=='nuxel-branding-sounds-and-icons')
planned={f['source'] for f in g['files']}
for path in canonical:
    assert path.lstrip('/') in planned,path
    assert ('/home/nuxel/nuxel/'+path.lstrip('/')) in {f['target'] for f in g['files']},path
for file in ('assets/nuxel-boot-audio.mp3','assets/nuxel-pow.mp3'):
    assert file in planned,file
builder=(ROOT/'images/s10plus/build-phone-rootfs-inside-fedora.sh').read_text()
assert 'cp -a /nuxel/assets/. "$STAGE/usr/share/nuxel/assets/"' in builder
assert 'nuxel-boot-sound.service' in builder
assert 'mpg123' in builder
assert (ROOT/'pwa/nuxel-home/sw.js').read_text().find('v14-a37-live-assets-and-audio')>=0
print(f'PASS {len(canonical)} live UI icon URLs resolve and are deployable')
print('PASS boot/volume MP3 packaged and sound service installed by S10+ image builder')
