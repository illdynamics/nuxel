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
             'pwa/nuxel-apps/console-wifi', 'pwa/nuxel-apps/maps',
             'pwa/nuxel-apps/doom', 'pwa/nuxel-apps/firewall',
             'pwa/nuxel-apps/permissions', 'pwa/nuxel-apps/network-manager',
             'pwa/nuxel-apps/devmgmt',
             'pwa/nuxel-apps/penguinterface',
             'pwa/nuxel-apps/remote-xrdp', 'pwa/nuxel-apps/remote-vnc',
             'pwa/nuxel-apps/remote-scrcpy', 'pwa/nuxel-common',
             'pwa/nuxel-apps/nuxtore', 'pwa/nuxel-apps/photos',
             'pwa/nuxel-apps/files',
             'services/nuxel-firewall/nuxel_firewall'):
    for path in (root / base).rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name in ('.keep',) or path.name.endswith(('.a59-bak', '.bak', '.pyc', '.pyo')):
            continue
        if '__pycache__' in path.parts or '.pytest_cache' in path.parts:
            continue
        items.add(path.relative_to(root).as_posix())
items.update({
    'pwa/nuxel-common/app-registry.json',
    'pwa/nuxel-common/bridge-version.json',
    'pwa/nuxel-common/back.js',
    'pwa/nuxel-common/bridge.js',
    'pwa/nuxel-common/geolocation.js',
    'pwa/nuxel-common/maps-core.js',
    'services/nuxel-bridge/src/api.py',
    'services/nuxel-bridge/src/bridge.py',
    'services/nuxel-bridge/src/network_manager.py',
    'services/nuxel-bridge/src/doom_assets.py',
    'services/nuxel-bridge/src/firewall_provider.py',
    'services/nuxel-bridge/src/flatpak_provider.py',
    'services/nuxel-firewall/bin/nuxel-firewall',
    'configs/nuxel/firewall/policy.json',
    'configs/nuxel/firewall/policy.schema.json',
    'tools/s10plus/a33/doom-engines/nuxel-doom-engine',
    'services/nuxel-bridge/src/hw_providers.py',
    'services/nuxel-bridge/src/tri_link_status.py',
    'services/nuxel-bridge/src/remote_desktop.py',
    'services/nuxel-zsh/nuxel-banner.sh',
    'services/nuxel-zsh/nuxel.zsh',
    'services/nuxel-remote-desktop/bin/nuxel-vnc-x11',
    'services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl',
    'services/nuxel-remote-desktop/bin/nuxel-xrdp-session',
    'services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync',
    'services/nuxel-remote-desktop/config/xrdp.ini',
    'services/nuxel-remote-desktop/config/sesman.ini',
    'services/nuxel-remote-desktop/config/xorg.conf',
    'services/nuxel-remote-desktop/config/xrdp-sesman.pam',
    'services/nuxel-remote-desktop/config/wayvnc.pam',
    'services/nuxel-remote-desktop/config/wayvnc.conf.example',
    'services/nuxel-remote-desktop/config/launcher.html',
    'services/nuxel-remote-desktop/systemd/nuxel-remote-vnc.service',
    'services/nuxel-s10/systemd/avahi-daemon.service.d/10-nuxel-boot-order.conf',
    'services/nuxel-s10/systemd/zerotier-one.service.d/10-nuxel-tun.conf',
    'services/nuxel-preload-cinema/nuxel-preload-cinema',
    'services/nuxel-bridge/src/media_store.py',
    'services/nuxel-display/bin/nuxel-displayd',
    'services/nuxel-display/bin/nuxel-display-ctl',
    'services/nuxel-display/bin/nuxel-wl-fb-ext.c',
    'services/nuxel-display/bin/build-nuxel-wl-fb-ext.sh',
    'services/nuxel-display/lib/nuxel_display.py',
    'services/nuxel-display/protocol/wlr-screencopy-unstable-v1.xml',
    'services/nuxel-display/systemd/nuxel-displayd.service',
    'services/nuxel-display/systemd/nuxel-wl-fb-ext.service',
    'services/nuxel-display/README.md',
    'services/nuxel-bridge/systemd/nuxel-bridge.service',
    'services/nuxel-bridge/systemd/nuxel-http-bridge.service',
    'services/nuxel-notifications/systemd/nuxel-notifications.service',
    'services/nuxel-notifications/src/notifications.py',
    'services/nuxel-portal/src/portal.py',
    'services/nuxel-portal-chooser/src/nuxel_portal_chooser.py',
    'services/nuxel-portal-chooser/dbus/org.freedesktop.impl.portal.desktop.nuxel.service',
    'services/nuxel-portal-chooser/xdg-desktop-portal/nuxel.portal',
    'services/nuxel-portal-chooser/bin/nuxel-portal-status',
    'services/nuxel-file-handlers/src/nuxel_file_handlers.py',
    'services/nuxel-file-handlers/bin/nuxel-file-handlers',
    'services/nuxel-file-handlers/bin/nuxel-open-file',
    'shell/config/org.nuxel.Photos.desktop',
    'shell/config/org.nuxel.Files.desktop',
    'shell/nuxel-browser-native/nuxel_browser_native.py',
    'services/nuxel-s10/bin/nuxel-flatpak-firefox',
    'configs/nuxel/browser/firefox.json',
    'tools/s10plus/a45/nuxel-session.sh',
    'configs/nuxel/portals.conf',
    'services/nuxel-metrics/nuxel-metrics.service',
    'services/nuxel-metrics/nuxel-metrics.socket',
    'services/nuxel-session/systemd/nuxel-boot-sound.service',
    'services/nuxel-sound/nuxel-soundd.py',
    'services/nuxel-sound/nuxel_audio_outputs.py',
    'services/nuxel-sound/nuxel-soundctl',
    'services/nuxel-sound/nuxel-soundd.service',
    'configs/nuxel/audio/output-policy.example.json',
    'tools/s10plus/a33/nuxel-sound-cue.py',
    'configs/nuxel/permissions/org.nuxel.Home.json',
    'configs/nuxel/permissions/nuxel-settings.json',
    'configs/nuxel/permissions/org.nuxel.Maps.json',
    'configs/nuxel/gnss/gnss.json',
    'configs/nuxel/security/remote-access.json',
    'configs/dbus/org.nuxel.Bridge.conf',
    'services/nuxel-bridge/dbus/org.nuxel.Bridge.conf',
    'assets/nuxel-boot-audio.mp3',
    'assets/nuxel-pow.mp3',
    'assets/nuxel-bottom-bar.jpg',
    'assets/nuxel-bottom-bar2.png',
    'assets/nuxel-applications-icon-pack/05-05_live-console.png',
    'assets/nuxel-applications-icon-pack/06-05_usb-connection.png',
    'assets/nuxel-applications-icon-pack/05-07_web-window.png',
    'assets/nuxel-applications-icon-pack/06-04_casting-screen.png',
    'assets/nuxel-applications-icon-pack/01-12_phone-alternative.png',
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
