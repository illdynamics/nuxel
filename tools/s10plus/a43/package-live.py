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
for base in ('pwa/nuxel-home', 'pwa/nuxel-apps/settings',
             'pwa/nuxel-apps/console', 'pwa/nuxel-apps/console-usb',
             'pwa/nuxel-apps/console-wifi', 'pwa/nuxel-apps/maps'):
    for path in (root / base).rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name in ('.keep',) or path.name.endswith(('.a59-bak', '.bak')):
            continue
        items.add(path.relative_to(root).as_posix())
items.update({
    'pwa/nuxel-common/app-registry.json',
    'pwa/nuxel-common/bridge-version.json',
    'pwa/nuxel-common/bridge.js',
    'pwa/nuxel-common/geolocation.js',
    'pwa/nuxel-common/maps-core.js',
    'services/nuxel-bridge/src/api.py',
    'services/nuxel-bridge/src/bridge.py',
    'services/nuxel-bridge/src/hw_providers.py',
    'services/nuxel-bridge/src/tri_link_status.py',
    'services/nuxel-bridge/src/media_store.py',
    'services/nuxel-bridge/systemd/nuxel-bridge.service',
    'services/nuxel-bridge/systemd/nuxel-http-bridge.service',
    'services/nuxel-notifications/systemd/nuxel-notifications.service',
    'services/nuxel-notifications/src/notifications.py',
    'services/nuxel-portal/src/portal.py',
    'services/nuxel-metrics/nuxel-metrics.service',
    'services/nuxel-metrics/nuxel-metrics.socket',
    'services/nuxel-session/systemd/nuxel-boot-sound.service',
    'tools/s10plus/a33/nuxel-sound-cue.py',
    'configs/nuxel/permissions/org.nuxel.Home.json',
    'configs/nuxel/permissions/nuxel-settings.json',
    'configs/nuxel/permissions/org.nuxel.Maps.json',
    'configs/nuxel/gnss/gnss.json',
    'configs/nuxel/security/remote-access.json',
    'configs/dbus/org.nuxel.Bridge.conf',
    'services/nuxel-bridge/dbus/org.nuxel.Bridge.conf',
    'assets/nuxel-bottom-bar.jpg',
    'assets/nuxel-bottom-bar2.png',
    'assets/nuxel-applications-icon-pack/05-05_live-console.png',
    'assets/nuxel-applications-icon-pack/06-05_usb-connection.png',
    'assets/nuxel-quicksettings-icon-pack/01-wifi.png',
})
# The metrics daemon is compiled into the phone rootfs by the image builder.
# A developer-only build/a40 binary is deliberately NOT packaged: CI does not
# have it, so including it would make the live payload differ from the release.

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
