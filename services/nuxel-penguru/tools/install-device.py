#!/usr/bin/env python3
"""Install the PenGuru integration on Nuxel, with per-file rollback receipts.

Run as root on the device: install-device.py --source-root /path/to/staged/repo
Does not install model weights, replace trust keys, enable test keys, enable
services at boot, restart the shell, or touch network/modem configuration.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import socket
import subprocess
import time


def merge_registry(existing, incoming):
    entry = next(item for item in incoming['apps'] if item['id'] == 'org.nuxel.PenGuru')
    entries = existing['apps']
    for index, item in enumerate(entries):
        if item['id'] == entry['id']:
            entries[index] = entry
            break
    else:
        entries.append(entry)
    return existing


def merge_settings(existing, incoming):
    """Remove the legacy PenGuru Settings tab from an installed handset.

    PenGuru is now self-contained in its own app: model downloads, runtime
    choice, voice and connection settings all live there.  Existing installs
    may still carry the old tab, section and script, so the installer strips
    exactly those three fragments and leaves every other Settings change alone.
    """
    del incoming  # kept in the signature for the installer/test contract
    existing = re.sub(r'[ \t]*<button\b[^>]*\bdata-tab="penguru"[^>]*>.*?</button>\n?', '',
                      existing, count=1, flags=re.S)
    existing = re.sub(r'[ \t]*<section\b[^>]*\bid="tab-penguru"[^>]*>.*?</section>\n?', '', existing,
                      count=1, flags=re.S)
    existing = re.sub(r'[ \t]*<script type="module" src="penguru-settings.js"></script>\n?', '', existing)
    return existing


ANDROID_ORIGIN = 'https://appassets.androidplatform.net'


def merge_allow_origin(existing):
    """Add the bundled Android APK origin to the bridge CORS allowlist.

    CORS is not authentication: the launcher-bound PenGuru token gate remains
    mandatory.  This only lets the WebView read the bridge's responses.
    """
    match = re.search(r'^Environment=NUXEL_API_ALLOW_ORIGIN=(.*)$', existing, re.M)
    if match:
        origins = [item.strip() for item in match.group(1).split(',') if item.strip()]
        if ANDROID_ORIGIN not in origins:
            origins.append(ANDROID_ORIGIN)
        replacement = 'Environment=NUXEL_API_ALLOW_ORIGIN=' + ','.join(origins)
        return existing[:match.start()] + replacement + existing[match.end():]
    if '[Service]\n' not in existing:
        raise ValueError('Cannot locate [Service] in the bridge unit')
    return existing.replace('[Service]\n', '[Service]\nEnvironment=NUXEL_API_ALLOW_ORIGIN='
                            + ANDROID_ORIGIN + '\n', 1)


def merge_api(existing):
    if "if namespace == 'penguru':" not in existing:
        marker = "        params = body.get('params', {}) or {}\n"
        start = existing.index('    def _handle_rpc(self, app_id, body):')
        insertion = existing.index(marker, start) + len(marker)
        existing = existing[:insertion] + ("        if namespace == 'penguru':\n"
            "            import penguru_api\n"
            "            return penguru_api.handle(app_id, self._session_token(), verb, params)\n") + existing[insertion:]
    # Android WebView requests cross a private-network boundary.  The
    # authorization decision is unchanged; this header only lets the browser
    # surface the bridge's CORS answer instead of blocking the preflight.
    if 'Access-Control-Allow-Private-Network' not in existing:
        marker = ("            self.send_header('Access-Control-Allow-Origin', cors_origin)\n"
                  "        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')")
        replacement = ("            self.send_header('Access-Control-Allow-Origin', cors_origin)\n"
                       "            self.send_header('Access-Control-Allow-Private-Network', 'true')\n"
                       "        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')")
        if marker in existing:
            existing = existing.replace(marker, replacement, 1)
    return existing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run on the device as root')
    source = args.source_root.resolve()
    receipt_dir = Path('/var/backups/nuxel-penguru') / time.strftime('%Y%m%dT%H%M%S')
    receipt_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    files = []
    def save():
        (receipt_dir / 'receipt.json').write_text(json.dumps(files, indent=2) + '\n')
    def install(destination, content, mode=0o644):
        destination = Path(destination)
        if destination.is_symlink():
            raise ValueError('Refusing symlink target: ' + str(destination))
        if isinstance(content, str):
            content = content.encode()
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = receipt_dir / str(len(files))
        existed = destination.exists()
        if existed:
            shutil.copy2(destination, backup)
        row = dict(target=str(destination), backup=str(backup), existed=existed,
                   sha256=hashlib.sha256(content).hexdigest())
        if existed:
            metadata = destination.stat()
            row.update(old_uid=metadata.st_uid, old_gid=metadata.st_gid,
                       old_sha256=hashlib.sha256(backup.read_bytes()).hexdigest())
        files.append(row)
        save()
        staged = destination.with_name(destination.name + '.penguru-stage')
        staged.write_bytes(content)
        staged.chmod(mode)
        staged.replace(destination)
    try:
        for unit in ('nuxel-penguru-download', 'nuxel-penguru'):
            if subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode == 0:
                raise RuntimeError('Stop PenGuru before installing; active workloads are not interrupted')
        service = source / 'services/nuxel-penguru'
        for item in sorted(service.rglob('*.py')):
            if not {'tests', '__pycache__', 'tools'} & set(item.relative_to(service).parts):
                install(Path('/opt/nuxel-penguru') / item.relative_to(service), item.read_bytes())
        if args.worker:
            header = args.worker.read_bytes()[:20]
            if header[:6] != b'\x7fELF\x02\x01' or int.from_bytes(header[18:20], 'little') != 183:
                raise ValueError('Worker must be a little-endian ARM64 ELF')
            install('/opt/nuxel-penguru/runtime/llama_cpp/penguru-llama-worker', args.worker.read_bytes(), 0o755)
        for item in (service / 'systemd').glob('*.service'):
            install(Path('/etc/systemd/system') / item.name, item.read_bytes())
        for item in (service / 'manifests').glob('*.json'):
            destination = Path('/usr/share/nuxel-penguru/manifests') / item.name
            if not destination.exists():
                install(destination, item.read_bytes())
        install('/usr/lib/nuxel/nuxel-bridge/penguru_api.py', (source / 'services/nuxel-bridge/src/penguru_api.py').read_bytes())
        api = Path('/usr/lib/nuxel/nuxel-bridge/api.py')
        install(api, merge_api(api.read_text()))
        for item in (source / 'pwa/nuxel-apps/penguru').iterdir():
            if item.is_file():
                install(Path('/usr/share/nuxel/pwa/nuxel-apps/penguru') / item.name, item.read_bytes())
        settings = Path('/usr/share/nuxel/pwa/nuxel-apps/settings')
        install(settings / 'index.html', merge_settings((settings / 'index.html').read_text(),
                (source / 'pwa/nuxel-apps/settings/index.html').read_text()))
        incoming = json.loads((source / 'pwa/nuxel-common/app-registry.json').read_text())
        for name in ('/etc/nuxel/app-registry/app_registry.json', '/usr/share/nuxel/pwa/nuxel-common/app-registry.json', '/usr/share/nuxel/nuxel-common/app-registry.json'):
            destination = Path(name)
            if destination.exists():
                install(destination, json.dumps(merge_registry(json.loads(destination.read_text()), incoming), indent=2) + '\n')
        install('/usr/share/nuxel/assets/nuxel-penguru-squad.png', (source / 'assets/nuxel-penguru-squad.png').read_bytes())
        try:
            account = pwd.getpwnam('nuxel-penguru')
        except KeyError:
            subprocess.run(['useradd', '--system', '--user-group', '--no-create-home', '--home-dir', '/var/lib/nuxel-penguru', '--shell', '/usr/sbin/nologin', 'nuxel-penguru'], check=True)
            account = pwd.getpwnam('nuxel-penguru')
        state = Path('/var/lib/nuxel-penguru')
        state.mkdir(mode=0o700, exist_ok=True)
        for item in [state, *state.rglob('*')]:
            if item.is_symlink():
                raise RuntimeError('Symlink in PenGuru state; ownership not changed')
        for item in [state, *state.rglob('*')]:
            os.chown(item, account.pw_uid, account.pw_gid)
        unit = Path('/etc/systemd/system/nuxel-http-bridge.service')
        if unit.exists():
            install(unit, merge_allow_origin(unit.read_text()))
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', 'restart', 'nuxel-http-bridge'], check=True)
        for attempt in range(40):
            try:
                with socket.create_connection(('127.0.0.1', 8080), timeout=1):
                    break
            except OSError:
                time.sleep(.25)
        else:
            raise RuntimeError('HTTP bridge did not become ready within 10 seconds')
        print(json.dumps({'installed': True, 'enabled': False, 'rollback_receipt': str(receipt_dir / 'receipt.json')}))
    except Exception:
        for row in reversed(files):
            destination = Path(row['target'])
            if row['existed']:
                shutil.copy2(row['backup'], destination)
                os.chown(destination, row['old_uid'], row['old_gid'])
            elif destination.exists():
                destination.unlink()
        subprocess.run(['systemctl', 'daemon-reload'])
        subprocess.run(['systemctl', 'restart', 'nuxel-http-bridge'])
        raise


if __name__ == '__main__':
    main()
