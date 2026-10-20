#!/usr/bin/env python3
"""Read-only manifest verifier of a copied live userspace payload; never installs."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile

root = Path(__file__).resolve().parents[3]
expected_version = (root / 'VERSION').read_text().strip()
expected_version = expected_version if expected_version.startswith('v') else 'v' + expected_version
payload = sys.argv[1]
with tarfile.open(payload, 'r:gz') as tf:
    manifest = json.load(tf.extractfile('manifest.json'))
    assert manifest['version'] == expected_version, manifest['version']
    entries = manifest['files']
    assert entries, 'empty payload'
    seen = set()
    for entry in entries:
        rel = entry['source']
        assert '..' not in rel.split('/') and not rel.startswith('/'), rel
        assert rel not in seen, 'duplicate ' + rel
        seen.add(rel)
        member = tf.getmember('files/' + rel)
        assert member.isfile() and not member.issym(), rel
        data = tf.extractfile(member).read()
        assert len(data) == entry['bytes'], rel
        assert hashlib.sha256(data).hexdigest() == entry['sha256'], rel
    required = {
        'pwa/nuxel-home/index.html',
        'pwa/nuxel-home/sw.js',
        'pwa/nuxel-home/manifest.json',
        'pwa/nuxel-home/js/system-monitor.js',
        'pwa/nuxel-home/js/navigation.js',
        'pwa/nuxel-home/js/launcher.js',
        'pwa/nuxel-home/css/launcher.css',
        'pwa/nuxel-home/css/style.css',
        'pwa/nuxel-apps/settings/wifi-settings.js',
        'pwa/nuxel-common/app-registry.json',
        'services/nuxel-bridge/src/bridge.py',
        'services/nuxel-bridge/src/api.py',
        'services/nuxel-metrics/nuxel-metrics.service',
        'services/nuxel-metrics/nuxel-metrics.socket',
        'services/nuxel-haptics/nuxel-haptics.service',
        'tools/s10plus/a41/nuxel-network-udev-seed.service',
        'tools/s10plus/a41/nuxel-network-udev-seed.sh',
        'build/a40/nuxel-metricsd',
        'pwa/nuxel-apps/browser/index.html',
        'pwa/nuxel-apps/settings/index.html',
    }
    missing = required - seen
    assert not missing, 'missing required payload members: ' + ', '.join(sorted(missing))
    metrics = tf.extractfile('files/build/a40/nuxel-metricsd').read()
    assert len(metrics) > 64 and metrics[:4] == b'\x7fELF', 'metrics payload is not ELF'
    assert metrics[4] == 2 and metrics[5] == 1, 'metrics payload is not 64-bit little-endian ELF'
    assert int.from_bytes(metrics[18:20], 'little') == 183, 'metrics payload is not AArch64'
print('Verified payload hashes, AArch64 metrics ELF and %d safe regular files for %s'
      % (len(entries), expected_version))
