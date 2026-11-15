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
             'pwa/nuxel-apps/weather',
             'pwa/nuxel-apps/permissions', 'pwa/nuxel-apps/network-manager',
             'pwa/nuxel-apps/devmgmt', 'pwa/nuxel-apps/edge-fx',
             'pwa/nuxel-apps/penguinterface',
             'pwa/nuxel-apps/remote-xrdp', 'pwa/nuxel-apps/remote-vnc',
             'pwa/nuxel-apps/remote-scrcpy', 'pwa/nuxel-common',
             'pwa/nuxel-apps/nuxtore', 'pwa/nuxel-apps/photos',
             'pwa/nuxel-apps/files',
             'services/nuxel-firewall/nuxel_firewall',
             'pwa/nuxel-apps/vault',
             'services/nuxel-nfc'):
    for path in (root / base).rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name in ('.keep',) or path.name.endswith(('.a59-bak', '.bak', '.pyc', '.pyo')):
            continue
        if '__pycache__' in path.parts or '.pytest_cache' in path.parts:
            continue
        items.add(path.relative_to(root).as_posix())
items.update({
    # PWNAGE-CAM: native camera app, private org.nuxel.Camera broker, capture
    # client + diagnostic. The aarch64 nuxel-fimc-capture binary is built by
    # tools/s10plus/fimc-capture/Makefile; the host deployer maps it to
    # /usr/libexec/nuxel/nuxel-fimc-capture.
    'pwa/nuxel-common/app-registry.json',
    # Edge Lighting provider + Home engine (PWNAGE-103000) and the A83 wake
    # work on top of it.
    'services/nuxel-bridge/src/edge_lighting_provider.py',
    'pwa/nuxel-home/js/edge-lighting.js',
    # The daemon tree's copy of the bridge NFC client.  Without it the payload
    # ships only services/nuxel-bridge/src/nfc_provider.py, whose content is
    # byte-identical here — the installer's one-source-one-target rule then
    # never refreshes /usr/lib/nuxel/nuxel-nfc/nfc_provider.py.
    'services/nuxel-nfc/nfc_provider.py',
    'services/nuxel-nfc/nfcd-preflight.py',
    'services/nuxel-nfc/nuxel-nfc',
    'services/nuxel-nfc/90-nuxel-nfc.rules',
    'pwa/nuxel-common/bridge-version.json',
    'pwa/nuxel-common/back.js',
    'pwa/nuxel-common/bridge.js',
    'pwa/nuxel-common/geolocation.js',
    'pwa/nuxel-common/maps-core.js',
    'services/nuxel-bridge/src/api.py',
    'services/nuxel-bridge/src/bridge.py',
    'services/nuxel-bridge/src/network_manager.py',
    'services/nuxel-bridge/src/nfc_provider.py',
    'services/nuxel-bridge/src/mic_provider.py',
    'services/nuxel-bridge/src/privacy_provider.py',
    'services/nuxel-bridge/src/doom_assets.py',
    'services/nuxel-bridge/src/firewall_provider.py',
    'services/nuxel-bridge/src/flatpak_provider.py',
    'services/nuxel-firewall/bin/nuxel-firewall',
    # v0.8.5: the firewall unit + rulesets.  The live device had the provider
    # and binary installed but the unit was never shipped/enabled, so it booted
    # without a ruleset.
    'configs/nftables/systemd/nuxel-firewall.service',
    'configs/nftables/nuxel-firewall-config.json',
    'configs/nftables/nuxel-app-firewall.nft',
    'configs/nftables/nuxel-app-firewall-cgroupv2.nft',
    'configs/nftables/nuxel-console-guard.nft',
    'tools/s10plus/a33/nuxel-firewall.sh',
    'configs/nuxel/firewall/policy.json',
    'configs/nuxel/firewall/policy.schema.json',
    'tools/s10plus/a33/doom-engines/nuxel-doom-engine',
    'services/nuxel-bridge/src/hw_providers.py',
    'services/nuxel-bridge/src/tri_link_status.py',
    'services/nuxel-bridge/src/remote_desktop.py',
    # A80/A81 lockscreen + Vault: these bridge modules were live-deployed
    # earlier but were NOT in the payload, so the phone kept running the
    # image's old copies.  They are part of the userspace delta now.
    'services/nuxel-bridge/src/security_provider.py',
    'services/nuxel-bridge/src/fingerprint_provider.py',
    'services/nuxel-bridge/src/secret_service.py',
    'services/nuxel-bridge/src/keyring_api.py',
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
    # A88: static xrdp drop-ins so the XRDP app's Start can publish a config
    # the sandboxed bridge cannot write into /etc itself.
    'services/nuxel-remote-desktop/systemd/xrdp.service.d/10-nuxel-staged.conf',
    'services/nuxel-remote-desktop/systemd/xrdp.service.d/20-nuxel-config-path.conf',
    # A88: the GNSS bridge unit (SuccessExitStatus for its documented
    # proprietary-boundary exit, so a completed bounded session is not a
    # restart loop).
    'services/nuxel-gnss/systemd/nuxel-gnss-lhd.service',
    # A88: the ABOX post-boot firmware reload must restart the Flatpak Pulse
    # relay it stops (PartOf=nuxel-audio-session.service), otherwise Flatpak
    # apps lose the microphone/Pulse socket after every boot.
    'services/nuxel-s10/bin/nuxel-abox-firmware-reload-boot.sh',
    'services/nuxel-remote-desktop/config/launcher.html',
    'services/nuxel-remote-desktop/systemd/nuxel-remote-vnc.service',
    'services/nuxel-s10/systemd/avahi-daemon.service.d/10-nuxel-boot-order.conf',
    'services/nuxel-s10/systemd/zerotier-one.service.d/10-nuxel-tun.conf',
    'services/nuxel-preload-cinema/nuxel-preload-cinema',
    # A83 wake: the canonical boot cue (started just before the preloading
    # video releases the glass) and the Edge FX provider defaults (wake and
    # unlock play the configured effect).  Both were missing from the payload,
    # so a live deploy silently kept the image's older copies.
    'tools/s10plus/a33/nuxel-sound-cue.py',
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
    'services/nuxel-notifications/dbus/org.nuxel.PhoshAgent.service',
    'services/nuxel-notifications/dbus/org.nuxel.Notifications.service',
    'services/nuxel-consent/nuxel_consentd.py',
    'services/nuxel-consent/systemd/nuxel-consent-agent.service',
    'services/nuxel-consent/dbus/org.nuxel.PhoshAgent.conf',
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
    'services/nuxel-s10/bin/nuxel-audio-perms.sh',
    # A84: the audio session script (Pulse socket + PipeWire session ACL) and
    # the microphone provider were only ever in the image; a live deploy left
    # the old copies running (mic reported "no capture source").
    'services/nuxel-s10/bin/nuxel-audio-session.sh',
    'services/nuxel-bridge/src/mic_provider.py',
    'services/nuxel-s10/bin/nuxel-flatpak-pulse-relay.py',
    # v0.8.5: Flatpak app wrappers, the hotspot owner and the durable routing
    # sysctls are part of the live payload so a deploy reproduces the image.
    'services/nuxel-s10/bin/nuxel-flatpak-stremio',
    'services/nuxel-s10/bin/nuxel-flatpak-signal',
    'services/nuxel-network/nuxel-hotspot.py',
    'services/nuxel-network/nuxel-hotspot.service',
    'configs/nuxel/sysctl/90-nuxel-tether.conf',
    # v0.8.5: ECM owner link for SSH over the plugged-in USB cable.
    'services/nuxel-s10/bin/nuxel-usb-net-up.sh',
    'services/nuxel-s10/systemd/nuxel-usb-net-up.service',
    'services/nuxel-s10/systemd/nuxel-audio-perms.service',
    'services/nuxel-s10/systemd/nuxel-flatpak-pulse-relay.service',
    'configs/nuxel/browser/firefox.json',
    'tools/s10plus/a45/nuxel-session.sh',
    'tools/s10plus/a45/nuxel-shell-chrome.sh',
    # A85: publishes the boot lock state before the nav dock/launcher start.
    'tools/s10plus/a45/nuxel-security-state-rpc',
    'configs/nuxel/portals.conf',
    'services/nuxel-metrics/nuxel-metrics.service',
    'services/nuxel-metrics/nuxel-metrics.socket',
    'services/nuxel-session/systemd/nuxel-boot-sound.service',
    # Required by verify-live.py (boot sound) — it was shipped by the image but
    # missing from the live payload, so a clean payload failed verification.
    'assets/nuxel-boot-audio.mp3',
    'services/nuxel-sound/nuxel-soundd.py',
    'services/nuxel-sound/nuxel_audio_outputs.py',
    'services/nuxel-sound/nuxel-soundctl',
    # PWNAGE-CAM (2026-11-14): camera userspace + FIMC-IS capture client.
    'shell/nuxel-camera-native/nuxel_camera_native.py',
    'shell/nuxel-camera-native/org.nuxel.CameraNative.desktop',
    'shell/nuxel-camera-portal/nuxel_camera_portal.py',
    'shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service',
    'shell/nuxel-camera-portal/nuxel_camera_portal_impl.py',
    'shell/nuxel-camera-portal/xdg-desktop-portal/nuxel-camera.portal',
    'shell/nuxel-camera-portal/dbus/org.freedesktop.impl.portal.desktop.nuxel-camera.service',
    'shell/nuxel-camera-portal/systemd/nuxel-camera-portal-impl.service',
    'tools/s10plus/a33/nuxel-camera-diag.sh',
    # binary: built by tools/s10plus/fimc-capture/Makefile (aarch64, static)
    'tools/s10plus/fimc-capture/nuxel-fimc-capture',
    'configs/nuxel/camera/camera.json',
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
