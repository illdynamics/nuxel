#!/usr/bin/env python3
"""A39 source-level dock, cache, assets, and no-flash deploy invariants."""
from pathlib import Path
import hashlib
import json
import re
R=Path(__file__).resolve().parents[4]
source=R/'pwa/nuxel-home'
assets=['nuxel-bottom-bar.jpg','nuxel-bottom-bar2.png']
for name in assets:
    a=(R/'assets'/name).read_bytes()
    b=(source/'assets'/name).read_bytes()
    assert len(a)>10000
    assert hashlib.sha256(a).digest()==hashlib.sha256(b).digest(), name
    print('PASS',name,'SHA-256',hashlib.sha256(a).hexdigest())
ui=(source/'js/home-settings.js').read_text()
assert "DEFAULT_DOCK = 'bg2'" in ui
assert "none: null" in ui
assert "nuxel.homeAppearance" in ui
assert "'/pwa/nuxel-home/assets/nuxel-bottom-bar2.png'" in ui
assert "'/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg'" in ui
assert "css/assets/nuxel-bottom-bar" not in ui
assert "dock.setAttribute('data-dock-asset'" in ui
assert "data-dock-choice" in ui and "aria-pressed" in ui
assert "querySelectorAll('#system-navigation')" in ui
assert "homeLocked" in ui and "desktopCount" in ui
css=(source/'css/launcher.css').read_text()
assert '.dock::before{display:none!important' in css
assert 'repeat(4,minmax(0,1fr))' in css
style=(source/'css/style.css').read_text()
assert "url('../assets/nuxel-bottom-bar2.png')" in style
assert 'background-size: 100% auto' in style
assert '.system-navigation[data-background="none"]::before { display: none; }' in style
launcher=(source/'js/launcher.js').read_text()
assert 'pageAssignments' in launcher and 'mainDesktop()' in launcher
assert '_renderDrawerApps()' in launcher and 'addToHome(appId' in launcher
assert 'isHomeLocked()' in launcher
status=(source/'js/status-bar.js').read_text()
assert all(x in status for x in ("style === 'percentage'", "style === 'inside'",'width:' ,'battery-inside-pct'))
manifest=json.loads((source/'manifest.json').read_text())
sw=(source/'sw.js').read_text()
assert "const CACHE_VERSION = '"+manifest['nuxel']['cache_version']+"'" in sw
for name in assets:
    assert "'./assets/"+name+"'" in sw
manifest=json.loads((R/'tools/beta/live/deploy-manifest.json').read_text())
groups={g['id']:{f['source'] for f in g.get('files',[])} for g in manifest['groups']}
for name in assets:
    assert 'assets/'+name in groups['nuxel-branding-sounds-and-icons']
    assert 'pwa/nuxel-home/assets/'+name in groups['nuxel-branding-sounds-and-icons']
for source_name in ['pwa/nuxel-home/js/home-settings.js','pwa/nuxel-home/js/scroll-indicators.js','pwa/nuxel-home/js/gestures.js']:
    assert source_name in groups['nuxel-branding-sounds-and-icons']
assert (R/'assets/nuxel-boot-audio.mp3').exists()
assert (R/'assets/nuxel-pow.mp3').exists()
print('PASS A39 asset packaging, default BG2, selector, persistence, Home lock, desktops, scrollbar, battery, deploy manifest')
