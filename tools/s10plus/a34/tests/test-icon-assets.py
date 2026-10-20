#!/usr/bin/env python3
"""Verify active UI artwork from the generated registry, repo and image plan.

A44 supersedes the old `?v=a37` regex: the registry is generated from the same
apps.js/index.html the launcher executes, so a new icon cannot be added to the
UI without also being checked here (and by the HTTP/WebKit tests).
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[4]
REG = json.loads((ROOT / 'pwa/nuxel-home/icon-registry.json').read_text())
assert REG['counts'] == {'app': 12, 'navigation': 3, 'toggle': 8, 'total': 23}, REG['counts']
assert REG['non_image_toggles'] == [{'id': 'qs-verbose-boot', 'reason': 'CSS-only control, no custom raster asset'}]
paths = {a['path'] for a in REG['assets']}
assert {'/assets/button-left.png', '/assets/button-middle.png', '/assets/button-right.png'} <= paths
assert '/assets/nuxel-applications-icon-pack/01-01_terminal.png' in paths
assert '/assets/nuxel-quicksettings-icon-pack/01-wifi.png' in paths
for a in REG['assets']:
    p = ROOT / a['source']
    assert p.is_file() and p.stat().st_size == a['bytes'] and a['bytes'] > 100, a['source']
    assert a['path'].startswith('/assets/'), a
    assert a['url'].endswith('?v=a44'), a['url']

manifest = json.loads((ROOT / 'tools/beta/live/deploy-manifest.json').read_text())
g = next(g for g in manifest['groups'] if g['id'] == 'nuxel-branding-sounds-and-icons')
planned = {f['source'] for f in g['files']}
targets = {f['target'] for f in g['files']}
for a in REG['assets']:
    assert a['source'] in planned, a['source']
    assert ('/home/nuxel/nuxel/' + a['source']) in targets, a['source']
assert 'pwa/nuxel-home/icon-registry.json' in planned

builder = (ROOT / 'images/s10plus/build-phone-rootfs-inside-fedora.sh').read_text()
assert 'cp -a /nuxel/pwa "$STAGE/usr/share/nuxel/pwa"' in builder
assert 'cp -a /nuxel/assets/. "$STAGE/usr/share/nuxel/assets/"' in builder
assert 'nuxel-boot-sound.service' in builder
assert 'mpg123' in builder
print(f'PASS {len(REG["assets"])} active UI icon URLs resolve from the generated registry and are deployable')
print('PASS boot/volume MP3 packaged and sound service installed by S10+ image builder')
