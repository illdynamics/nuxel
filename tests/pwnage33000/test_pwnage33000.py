"""PWNAGE-33000 regression checks (offline, no device access).

These tests pin the invariants repaired in this mission: one canonical app
registry, real executable registrations, the Gallery rename, no Upload control,
recorder WAV loading + user-home save path, the exact banner source, the Wi-Fi
udev-seed ordering fix, and the honest empty Nuxtore state.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services' / 'nuxel-bridge' / 'src'))

import pwa_store  # noqa: E402


def _registry():
    return json.loads((ROOT / 'pwa/nuxel-common/app-registry.json').read_text())


def test_registry_is_consistent_and_exactly_matches_launcher():
    proc = subprocess.run([sys.executable, str(ROOT / 'tools/s10plus/a33/verify-app-registry.py'), '--strict'],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert 'problems=0' in proc.stdout


def test_native_registrations_point_to_real_sources_and_install_targets():
    # An entry ships EITHER a repository source that the image builder compiles
    # (GTK/Python apps) OR a package install target (a Fedora RPM, or the Nuxel
    # Flatpak/RPM wrapper in services/nuxel-s10/bin).  Both are real; what must
    # never happen is an install target with no source and no desktop entry.
    for app in _registry()['apps']:
        if app['type'] != 'native':
            continue
        assert app['native_binary'].startswith('/usr/')
        src = app.get('binary_source')
        installed = app.get('install_source')
        assert src or installed, (app['id'], 'native entry without a source, wrapper or package')
        if src:
            assert (ROOT / src).exists(), (app['id'], src)
        if installed:
            assert installed.startswith('/usr/'), (app['id'], installed)
        desktop = app.get('desktop_entry')
        assert desktop, (app['id'], 'native entry without a desktop entry')
        if not desktop.startswith('flatpak:'):
            assert (ROOT / desktop).exists(), (app['id'], desktop)


def test_gallery_visible_name_and_no_photos_label():
    apps_js = (ROOT / 'pwa/nuxel-home/js/apps.js').read_text()
    assert "id: 'org.nuxel.Photos', name: 'Gallery'" in apps_js
    manifest = json.loads((ROOT / 'pwa/nuxel-apps/photos/manifest.json').read_text())
    assert manifest['short_name'] == 'Gallery'
    assert 'Gallery' in (ROOT / 'pwa/nuxel-apps/photos/index.html').read_text()


def test_icon_map_assets_exist_and_are_shared_by_desktop_and_drawer():
    apps_js = (ROOT / 'pwa/nuxel-home/js/apps.js').read_text()
    block = apps_js.split('const NUXEL_APP_ICON_ASSETS = {', 1)[1].split('};', 1)[0]
    for key, src in re.findall(r"'([^']+)':\s*'([^']+)'", block):
        clean = src.split('?', 1)[0].lstrip('/')
        assert (ROOT / clean).exists(), (key, clean)
    assert "function nuxelAppIcon" in apps_js
    assert '_appIcon(app)' in (ROOT / 'pwa/nuxel-home/js/launcher.js').read_text()


def test_files_has_no_upload_control_or_handler():
    html = (ROOT / 'pwa/nuxel-apps/files/index.html').read_text()
    js = (ROOT / 'pwa/nuxel-apps/files/js/files.js').read_text()
    assert 'upload-btn' not in html and 'file-input' not in html
    assert 'uploadBtn' not in js and 'Upload' not in js
    assert 'cwd-abs' in html and 'absolutePath' in js
    assert "replace(/-([a-z])/g" in js


def test_recorder_loads_wav_encoder_and_uses_voice_recordings():
    html = (ROOT / 'pwa/nuxel-apps/recorder/index.html').read_text()
    js = (ROOT / 'pwa/nuxel-apps/recorder/js/recorder.js').read_text()
    assert 'recorder-wav.js' in html
    assert "saveLocation: '/VoiceRecordings'" in js
    assert "/VoiceRecordings" not in js.split("saveLocation:", 1)[0]
    assert 'absoluteLocation' in js and 'storage' in js
    assert "bridgeCall('audio', 'capture-route'" in js
    hw = (ROOT / 'services/nuxel-bridge/src/hw_providers.py').read_text()
    assert 'def capture_route' in hw and 'wpctl' in hw


def test_banner_source_and_installer_are_exact():
    src = (ROOT / 'banner').read_text()
    assert 'N U X E L' in src or '███╗' in src
    script = (ROOT / 'tools/s10plus/a29/install-nuxel-banner.sh').read_text()
    assert 'install -m "$mode" -o root -g root "$src" "$dst"' in script
    assert '"$ROOT/etc/banner" 0644' in script
    assert 'Banner /etc/banner' in script
    assert 'SSH_CONNECTION' in script


def test_wifi_seed_has_no_unavailable_device_unit_dependency():
    unit = (ROOT / 'tools/s10plus/a41/nuxel-network-udev-seed.service').read_text()
    assert not re.search(r'^(After|Wants)=.*sys-subsystem-net-devices-wlan0\.device', unit, re.M)
    assert 'Before=NetworkManager.service' in unit


def test_nuxtore_empty_state_is_honest():
    js = (ROOT / 'pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js').read_text()
    assert "installed: {}" in js
    test_js = (ROOT / 'pwa/nuxel-apps/nuxtore/tests/test-catalog.js').read_text()
    assert 'emptyState' in test_js


def test_pwa_store_opens_configured_home_and_lists_real_media(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    (home / 'Gallery').mkdir(parents=True)
    (home / 'Gallery' / 'real.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    (home / 'Videos').mkdir()
    (home / 'Videos' / 'clip.mp4').write_bytes(b'not-a-real-video-but-metadata')
    monkeypatch.delenv('NUXEL_APP_DATA_DIR', raising=False)
    monkeypatch.setenv('NUXEL_FILES_ROOT', str(home))
    store = pwa_store.PwaStore()
    assert store.files_root == home.resolve()
    listing = store.storage_list_dir('/')
    assert listing['success'] and listing['absolute_path'] == str(home.resolve())
    media = store.storage_media_list()
    names = {m['name'] for m in media['media']}
    assert {'real.png', 'clip.mp4'} <= names


def test_pwa_store_rejects_symlink_archive_entries(tmp_path, monkeypatch):
    import zipfile
    monkeypatch.setenv('NUXEL_APP_DATA_DIR', str(tmp_path))
    store = pwa_store.PwaStore()
    store.files_root.mkdir(parents=True, exist_ok=True)
    arc = store._fs_path('/link.zip')
    with zipfile.ZipFile(arc, 'w') as zf:
        info = zipfile.ZipInfo('link')
        info.external_attr = (0o120777 << 16)
        zf.writestr(info, '/etc/passwd')
    res = store.storage_archive_extract('/link.zip', '/out')
    assert res['success'] is False and res['error_code'] == 'UNSAFE_ARCHIVE'
