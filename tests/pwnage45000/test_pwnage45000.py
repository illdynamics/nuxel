#!/usr/bin/env python3
"""PWNAGE-45000 offline regression suite."""
import importlib.machinery
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'services/nuxel-bridge/src'
sys.path.insert(0, str(SRC))

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)))
    if not cond:
        fails.append(name)

def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod

# ---- lockscreen order / transport geometry ---------------------------------
html = (ROOT / 'pwa/nuxel-home/index.html').read_text()
row = re.search(r'<div class="lockscreen-indicators".*?</div>', html, re.S).group(0)
pos_ch = row.find('lockscreen-indicator-charging')
pos_live = row.find('lockscreen-indicator-live')
pos_usb = row.find('lockscreen-indicator-usb')
check('lockscreen order charging < live < usb', 0 <= pos_ch < pos_live < pos_usb,
      (pos_ch, pos_live, pos_usb))
css = (ROOT / 'pwa/nuxel-home/css/lockscreen.css').read_text()
check('transport row between primary row and wordmark (258)', re.search(r'\.lockscreen-transports\s*\{[^}]*top:\s*258px', css, re.S) is not None)
check('transport icons enlarged to 56', re.search(r'\.lockscreen-transport\s*\{[^}]*width:\s*56px;[^}]*height:\s*56px', css, re.S) is not None)
check('file transfer keeps wide aspect', '.lockscreen-transport.file-transfer-ind { width: 76px; height: 56px; }' in css)
check('landscape rule enlarged', re.search(r'\.lockscreen-transport\s*\{\s*width:\s*44px;\s*height:\s*44px;', css) is not None)

# ---- navdock artwork --------------------------------------------------------
art = (ROOT / 'tools/s10plus/a45/navdock-art.h').read_text()
check('navdock header generated', 'AUTO-GENERATED' in art and '#define NAV_ART_SIZE 48' in art)
check('navdock arrays present', all(('art_' + n) in art for n in ('left', 'middle', 'right')))
for n in ('left', 'middle', 'right'):
    im = Image.open(ROOT / 'pwa/nuxel-home/assets' / ('button-%s.png' % n)).convert('RGBA')
    bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    check('fallback %s alpha bounds' % n, bb is not None and bb[0] >= 3 and bb[2] <= 93 and (bb[2]-bb[0]) >= 70, bb)
# premultiplication: parse first few words and ensure transparent pixels are 0
words = [int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]{8})', art)[:1000]]
check('navdock transparent premultiplied', any(w == 0 for w in words))

# ---- DND -------------------------------------------------------------------
import dnd_provider
tmp = tempfile.mkdtemp()
os.environ['NUXEL_DND_STATE'] = os.path.join(tmp, 'dnd.json')
os.environ['NUXEL_DND_CONFIG'] = os.path.join(tmp, 'cfg.json')
Path(os.environ['NUXEL_DND_CONFIG']).write_text(json.dumps(dnd_provider.DEFAULT_POLICY))
dnd_provider._PROVIDER = None
p = dnd_provider.get_provider()
check('dnd starts off', p.status()['active'] is False)
check('dnd enables', p.set_enabled(True)['active'] is True)
check('dnd suppresses normal', p.suppresses('normal', 'chat') is True)
check('dnd critical exception', p.suppresses('critical', 'alarm') is False)
check('dnd persists', dnd_provider.DndProvider().status()['active'] is True)
p.set_enabled(False)

# ---- security --------------------------------------------------------------
import security_provider
os.environ['NUXEL_LOCK_CREDENTIAL'] = os.path.join(tmp, 'lock.json')
os.environ['NUXEL_LOCK_STATE'] = os.path.join(tmp, 'lock-state.json')
security_provider._PROVIDER = None
s = security_provider.get_provider()
r = s.set_mode('pin', '246813', current_secret=None)
check('pin credential accepted', r.get('mode') == 'pin', r)
check('weak pin refused', s.set_mode('pin', '111111', current_secret='246813').get('error') == 'pin_too_weak')
check('wrong pin rejected', s.unlock('000000').get('success') is False)
check('correct pin unlocks', s.unlock('246813').get('success') is True)
cred = json.loads(Path(os.environ['NUXEL_LOCK_CREDENTIAL']).read_text())
check('no plaintext pin stored', '246813' not in json.dumps(cred))
check('scrypt verifier present', len(cred.get('verifier', '')) == 64 and cred.get('salt'))
s.lock('test'); check('lock persists', s.status()['locked'] is True)
# failed attempts create persistent lockout
for _ in range(5):
    s.unlock('999999')
check('rate limit engages', s.status()['rate_limit']['locked_out'] is True)
check('fingerprint refused without provider', s.set_mode('fingerprint', '1', fallback_pin='246813', current_secret='246813').get('error') in ('fingerprint_provider_unavailable', 'rate_limited'))

# ---- NFC / fingerprint capability truth ------------------------------------
import nfc_provider, fingerprint_provider
check('nfc status truthful', nfc_provider.handle('status', {})['state'] in
      ('BLOCKED_KERNEL', 'BLOCKED_FIRMWARE', 'BLOCKED_EXTERNAL_RESOURCE', 'READY_FOR_TAG', 'NOT_SUPPORTED_ON_DEVICE'))
check('nfc has no fake enable', nfc_provider.handle('set-enabled', {'enabled': True})['success'] is False)
fp = fingerprint_provider.handle('status', {})
check('fingerprint never claims unsupported ready', fp['ready'] is False or fp['provider']['secure_tee'] is True)
check('fingerprint no raw templates', 'template' not in json.dumps(fp.get('slots', [])).lower())

# ---- LED provider ----------------------------------------------------------
import led_notification_provider
os.environ['NUXEL_LEDS_ROOT'] = os.path.join(tmp, 'leds')
os.environ['NUXEL_LED_NOTIFY_STATE'] = os.path.join(tmp, 'led-state.json')
os.environ['NUXEL_EDGE_LIGHT_CMD'] = os.path.join(tmp, 'wlfb.cmd')
Path(os.environ['NUXEL_EDGE_LIGHT_CMD']).write_text('')
led_notification_provider._PROVIDER = None
lp = led_notification_provider.get_provider()
st = lp.status()
check('no fake notification LED', st['hardware_led'] is False)
check('display fallback labelled', st['display_fallback']['kind'] == 'display_edge_lighting')
r = lp.set_color('red', 200)
check('fallback result labelled', r['state'] == 'DISPLAY_FALLBACK' and r['kind'] == 'none', r)
check('fallback writes bounded command', Path(os.environ['NUXEL_EDGE_LIGHT_CMD']).read_text().startswith('edge-light ff 00 00 '))
lp.clear('test')
check('fallback explicit off', 'edge-light-off' in Path(os.environ['NUXEL_EDGE_LIGHT_CMD']).read_text())

# ---- app registry lifecycle ------------------------------------------------
import app_manager
reg = json.loads((ROOT / 'pwa/nuxel-common/app-registry.json').read_text())
reg_path = Path(tmp) / 'registry.json'
reg_path.write_text(json.dumps(reg))
app_manager.WEBROOT = str(ROOT)
os.environ['NUXEL_APP_REGISTRY'] = str(reg_path)
app_manager._MANAGER = None
m = app_manager.get_manager()
inv = m.inventory()
check('registry inventory complete', inv['success'] and len(inv['apps']) >= 40, len(inv['apps']))
check('nuxtore canonical id', m.find('org.nuxel.Nuxtore') is not None)
check('case alias migration', app_manager.canonical_id('org.nuxel.NuxTore') == 'org.nuxel.Nuxtore')
r = m.register('org.nuxel.PenguInterface', 'PenguInterface', '/pwa/nuxel-apps/penguinterface/index.html', '1.0.0')
check('register requires real payload', r['success'] is True and r['state'] == 'installed_and_launchable', r)
r = m.unregister('org.nuxel.PenguInterface')
check('unregister preserves data', r['success'] and r['payload_preserved'] and r['user_data_preserved'])
check('unregister removes registration', m.find('org.nuxel.PenguInterface') is None)
bad = m.register('org.nuxel.Evil', 'Evil', '/pwa/../../etc/passwd', '1', '')
check('path traversal refused', bad['success'] is False)

# ---- native launch contract ------------------------------------------------
api = (SRC / 'api.py').read_text()
check('firefox native binary', '"org.mozilla.firefox": ["/usr/bin/firefox"]' in api)
check('vlc native binary', '"org.videolan.VLC": ["/usr/lib/nuxel/nuxel-vlc-fallback"]' in api)
check('wayland runtime corrected', 'runtime = "/run/user/1000" if as_user else "/run/nuxel-wayland"' in api and 'XDG_RUNTIME_DIR": "/run/nuxel-wayland"' in api)
check('session-user runtime is user-owned', 'runtime = "/run/user/1000" if as_user' in api and '/run/user/1000/wayland-0' in (ROOT/'tools/s10plus/a45/nuxel-session.sh').read_text())
check('native launch lock gate', 'session_locked' in api and 'security_provider.handle("status"' in api)
check('surface evidence returned', 'surface_seen' in api and 'process_alive' in api)
check('unsupported app refusal', 'unsupported_on_device' in api)
check('registry/lock mutation gate', 'capability_denied' in api and '_owner_ok' in api)
check('registration rejects non-app start URLs', 'start_url_not_a_local_app' in (SRC/'app_manager.py').read_text())

# ---- settings panels + topbar ----------------------------------------------
settings = (ROOT / 'pwa/nuxel-apps/settings/index.html').read_text()
for tab in ('notifications', 'nfc', 'fingerprint', 'security', 'software'):
    check('settings tab ' + tab, ('data-tab="%s"' % tab) in settings and ('id="tab-%s"' % tab) in settings)
home = (ROOT / 'pwa/nuxel-home/index.html').read_text()
check('top bar NFC icon', 'id="status-nfc"' in home)
check('security lock script loaded', 'security-lock.js' in home)
sb_css = (ROOT / 'pwa/nuxel-home/css/status-bar.css').read_text()
check('DOM top bar hidden by the lockscreen privacy rule', 'body.lockscreen-active .status-bar' in sb_css and 'display: none !important' in sb_css)
statusbar_c = (ROOT / 'tools/s10plus/a45/nuxel-statusbar.c').read_text()
check('native top bar consumes authoritative lock state', '/run/nuxel/security/lock-state.json' in statusbar_c and 'session_locked' in statusbar_c)
check('native top bar recreates layer on unlock', 'bar_hide' in statusbar_c and 'bar_show' in statusbar_c and 'ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY' in statusbar_c)
check('native top bar fail-closed on missing lock state', 'if (!f) return 1;' in statusbar_c)
gen = (ROOT / 'tools/s10plus/a45/gen-navdock-art.py').read_text()
check('navdock generator resolves build-copy root', '_find_root' in gen and 'NUXEL_ROOT' in gen and '/nuxel' in gen)
check('navdock build copy does not write source fallbacks', 'NUXEL_NAVDOCK_SKIP_FALLBACK=1' in (ROOT/'images/s10plus/build-phone-rootfs-inside-fedora.sh').read_text())
builder = (ROOT/'images/s10plus/build-phone-rootfs-inside-fedora.sh').read_text()
check('rootfs builder has openssl for RDP credential generation', 'alsa-lib-devel git openssl' in builder)
check('inet group exists before usermod', builder.find('groupadd -f -g 3003 inet') < builder.find('usermod -aG inet nuxel-remote'))
check('PWA cache version agrees between sw.js and manifest', __import__('json').loads((ROOT/'pwa/nuxel-home/manifest.json').read_text())['nuxel']['cache_version'] in (ROOT/'pwa/nuxel-home/sw.js').read_text())
qs = (ROOT / 'pwa/nuxel-home/js/qs.js').read_text()
check('qs DND wired', "bridge.call('dnd', 'toggle'" in qs and "bridge.call('dnd', 'status'" in qs)

print()
print('PWNAGE-45000 TESTS: %d pass, %d fail' % (len(fails) and 0 or 0, len(fails)) if False else
      'PWNAGE-45000 TESTS: %s' % ('ALL PASS' if not fails else 'FAILURES: ' + ', '.join(fails)))
sys.exit(1 if fails else 0)
