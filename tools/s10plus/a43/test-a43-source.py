#!/usr/bin/env python3
"""A43 smoke: source contracts, not hardware-verified claims."""
from pathlib import Path
import re,json,hashlib,sys
r=Path(__file__).resolve().parents[3]
assert (r/'VERSION').read_text().strip()=='v0.6.3-beta'
assert 'v0.6.3-beta' in (r/'CHANGELOG.md').read_text()
assert 'branches: [main]' in (r/'.github/workflows/release.yml').read_text()
assert '--prerelease' in (r/'.github/workflows/release.yml').read_text()
for ext in ('jpg','png'):
    fn='nuxel-bottom-bar'+ ('2' if ext=='png' else '')+'.'+ext
    a=r/'assets'/fn;b=r/'pwa/nuxel-home/assets'/fn
    assert a.exists() and b.exists(),fn
    assert hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest(),fn
js=(r/'pwa/nuxel-home/js/apps.js').read_text()
assert 'org.nuxel.Browser' in js
assert '/pwa/nuxel-apps/browser/index.html' in js
assert (r/'pwa/nuxel-apps/settings/wifi-settings.js').exists()
settings=(r/'pwa/nuxel-apps/settings/index.html').read_text()
assert 'data-tab="network"' in settings and 'wifi-settings.js' in settings
bridge=(r/'services/nuxel-bridge/src/bridge.py').read_text()
api=(r/'services/nuxel-bridge/src/api.py').read_text()
for method in ('NetworkWifiScan','NetworkWifiConnect','NetworkWifiDisconnect','NetworkWifiSetEnabled'):
    assert 'def '+method in bridge and method in api
assert 'z-index:0' in (r/'pwa/nuxel-home/css/launcher.css').read_text()
assert 'gesturestart' in (r/'pwa/nuxel-home/index.html').read_text()
print('A43 source contract checks: PASS (hardware not tested)')
