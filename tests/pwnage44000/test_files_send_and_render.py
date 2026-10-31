#!/usr/bin/env python3
"""PWNAGE-44000 Files large-directory rendering + Bluetooth send contract."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))
import bluetooth_obex  # noqa: E402

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)))
    if not cond: fails.append(name)

js = (ROOT / 'pwa/nuxel-apps/files/js/files.js').read_text()
html = (ROOT / 'pwa/nuxel-apps/files/index.html').read_text()
check('Send button exists', 'id="send-btn"' in html)
check('Send button is enabled only by selection', 'el.sendBtn.disabled = this.selected.size === 0' in js)
check('future share methods are disabled placeholders', all(x in html for x in ('share-wifi', 'share-nearby')) and 'Coming soon' in html)
check('grid uses ONE delegated click listener', "el.fileGrid.addEventListener('click'" in js and "item.addEventListener('click'" not in js)
check('selection changes do not rebuild the grid', 'updateSelection()' in js and 'node.classList.toggle(\'selected\'' in js)
check('large directories render in progressive batches', 'var batch = 120' in js and 'createDocumentFragment' in js)
check('stale render batches are cancelled', '_renderToken' in js and 'token !== app._renderToken' in js)
check('Bluetooth send uses the backend provider', "bridgeCall('bluetooth', 'send-files'" in js and "bridgeCall('bluetooth', 'send-targets'" in js)
check('success is not claimed before the provider returns', "res.success === false" in js and "Sent ' + res.sent" in js)

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    root = td / 'home'; root.mkdir()
    good = root / 'hello.txt'; good.write_text('hello')
    (root / 'sub').mkdir()
    (root / 'sub' / 'nested.txt').write_text('nested')
    outside = td / 'secret.txt'; outside.write_text('secret')
    (root / 'escape.txt').symlink_to(outside)
    os.environ['NUXEL_CAMERA_ACTIVE'] = str(td / 'none')
    # Path traversal / symlink escape are rejected before touching any daemon.
    r = bluetooth_obex.send_files(root, ['../../etc/passwd'], 'AA:BB:CC:DD:EE:FF')
    check('traversal source rejected', r['success'] is False and r['error_code'] == 'INVALID_SOURCE', r)
    r = bluetooth_obex.send_files(root, ['/escape.txt'], 'AA:BB:CC:DD:EE:FF')
    check('symlink escape rejected', r['success'] is False and r['error_code'] == 'INVALID_SOURCE', r)
    r = bluetooth_obex.send_files(root, ['/hello.txt'], 'not-a-mac')
    check('invalid peer address rejected', r['success'] is False and 'address' in r.get('error', ''), r)
    r = bluetooth_obex.send_files(root, ['/hello.txt'], 'AA:BB:CC:DD:EE:FF')
    check('valid source with no OBEX daemon reports DBUS_UNAVAILABLE honestly',
          r['success'] is False and r.get('error_code') == 'DBUS_UNAVAILABLE', r)
    r = bluetooth_obex.send_files(root, ['/missing.txt'], 'AA:BB:CC:DD:EE:FF')
    check('missing source rejected', r['success'] is False and r['error_code'] == 'INVALID_SOURCE', r)

print('\n%d failing check(s)' % len(fails))
sys.exit(1 if fails else 0)
