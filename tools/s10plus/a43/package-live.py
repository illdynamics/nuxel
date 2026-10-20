#!/usr/bin/env python3
"""Build a hash-manifested userspace payload from the exact checkout.

The payload is the live-update delta for the S10+ userspace: the complete Nuxel
Home PWA, the Settings app (including Wi-Fi), the bridge sources, the
socket-activated metrics service and (when already built) the aarch64 metrics
daemon. It is generated from repository files only; nothing is copied from a
developer-only build tree apart from the explicitly built metrics binary.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile

root = Path(__file__).resolve().parents[3]
version = (root / 'VERSION').read_text().strip()
version = version if version.startswith('v') else 'v' + version
out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (
    root / f'build/out/nuxel-{version}-live-userspace.tar.gz')

items = set()
for base in ('pwa/nuxel-home', 'pwa/nuxel-apps/settings'):
    for path in (root / base).rglob('*'):
        if path.is_file() and not path.is_symlink():
            items.add(path.relative_to(root).as_posix())
items.update({
    'pwa/nuxel-common/app-registry.json',
    'pwa/nuxel-common/bridge-version.json',
    'services/nuxel-bridge/src/api.py',
    'services/nuxel-bridge/src/bridge.py',
    'services/nuxel-metrics/nuxel-metrics.service',
    'services/nuxel-metrics/nuxel-metrics.socket',
    'services/nuxel-session/systemd/nuxel-boot-sound.service',
    'tools/s10plus/a33/nuxel-sound-cue.py',
    'assets/nuxel-bottom-bar.jpg',
    'assets/nuxel-bottom-bar2.png',
})
metrics_binary = root / 'build/a40/nuxel-metricsd'
if metrics_binary.is_file() and not metrics_binary.is_symlink():
    items.add('build/a40/nuxel-metricsd')

manifest = []
out.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='nuxel-live-') as temp:
    stage = Path(temp)
    for rel in sorted(items):
        source = root / rel
        assert source.is_file() and not source.is_symlink(), rel
        dest = stage / 'files' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        manifest.append({
            'source': rel,
            'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
            'bytes': dest.stat().st_size,
        })
    (stage / 'manifest.json').write_text(
        json.dumps({'version': version, 'files': manifest}, indent=2) + '\n')
    with tarfile.open(out, 'w:gz') as tar:
        tar.add(stage / 'manifest.json', arcname='manifest.json')
        for rel in sorted(items):
            tar.add(stage / 'files' / rel, arcname='files/' + rel)
print(out, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest(),
      'version', version, 'files', len(items))
