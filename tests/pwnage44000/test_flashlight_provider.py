#!/usr/bin/env python3
"""PWNAGE-44000 safe flashlight owner tests (offline fixture)."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))
os.environ.setdefault('NUXEL_LED_POLICY', str(ROOT / 'configs/nuxel/leds/leds.json'))
import flashlight_provider  # noqa: E402

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)))
    if not cond: fails.append(name)

def fixture(tmp, max_on_ms=60000):
    leds = Path(tmp) / 'leds'
    led = leds / 'torch-sec1'
    led.mkdir(parents=True)
    (led / 'brightness').write_text('0')
    (led / 'max_brightness').write_text('15')
    state = Path(tmp) / 'state.json'
    policy = json.loads((ROOT / 'configs/nuxel/leds/leds.json').read_text())
    policy['safety']['max_on_ms'] = max_on_ms
    pol = Path(tmp) / 'leds.json'
    pol.write_text(json.dumps(policy))
    os.environ.update({
        'NUXEL_LEDS_ROOT': str(leds),
        'NUXEL_LED_POLICY': str(pol),
        'NUXEL_FLASHLIGHT_STATE': str(state),
        'NUXEL_CAMERA_ACTIVE': str(Path(tmp) / 'camera-active'),
        'NUXEL_THERMAL_ROOT': str(Path(tmp) / 'thermal'),
    })
    os.makedirs(Path(tmp) / 'thermal', exist_ok=True)
    flashlight_provider._PROVIDER = None
    return leds, led, Path(tmp)

with tempfile.TemporaryDirectory() as td:
    import shutil
    shutil.copy(ROOT / 'configs/nuxel/leds/leds.json', Path(td) / 'orig.json')
    leds, led, tmp = fixture(td)
    p = flashlight_provider.get_provider()
    check('fixture torch is discovered', p.status()['supported'] is True)
    check('no auto-on at boot', (led / 'brightness').read_text() == '0')
    st = p.set_enabled(True, 'test')
    check('ON writes max brightness', st['state'] == 'ON' and (led / 'brightness').read_text() == '15')
    st = p.force_off('test-off')
    check('explicit OFF writes zero', st['state'] == 'OFF' and (led / 'brightness').read_text() == '0')
    # camera arbitration
    (tmp / 'camera-active').write_text('1')
    st = p.set_enabled(True, 'test')
    check('camera owns the LED -> BLOCKED_CAMERA', st['state'] == 'BLOCKED_CAMERA' and (led / 'brightness').read_text() == '0')
    (tmp / 'camera-active').unlink()
    # thermal
    tz = tmp / 'thermal' / 'thermal_zone0'; tz.mkdir()
    (tz / 'temp').write_text('75000')
    st = p.set_enabled(True, 'test')
    check('thermal guard -> THERMAL_LIMIT', st['state'] == 'THERMAL_LIMIT' and (led / 'brightness').read_text() == '0')

with tempfile.TemporaryDirectory() as td:
    leds, led, tmp = fixture(td, max_on_ms=1000)
    p = flashlight_provider.get_provider()
    p.set_enabled(True, 'timeout-test')
    check('ON before timeout', (led / 'brightness').read_text() == '15')
    time.sleep(1.35)
    check('policy timeout forces an explicit OFF', p.status()['state'] == 'OFF' and (led / 'brightness').read_text() == '0')

with tempfile.TemporaryDirectory() as td:
    leds = Path(td) / 'leds'; leds.mkdir()
    os.environ.update({'NUXEL_LEDS_ROOT': str(leds), 'NUXEL_LED_POLICY': str(ROOT / 'configs/nuxel/leds/leds.json'),
                       'NUXEL_FLASHLIGHT_STATE': str(Path(td) / 'state.json'),
                       'NUXEL_CAMERA_ACTIVE': str(Path(td) / 'none')})
    flashlight_provider._PROVIDER = None
    st = flashlight_provider.get_provider().set_enabled(True, 'test')
    check('missing LED class is NOT_SUPPORTED_ON_DEVICE', st['state'] == 'NOT_SUPPORTED_ON_DEVICE' and st['supported'] is False)

# No PWA may write a raw LED node.
js = '\n'.join(p.read_text(errors='ignore') for p in (ROOT / 'pwa').rglob('*.js'))
check('JavaScript contains no LED brightness write', '/sys/class/leds' not in js or 'brightness' not in js)

print('\n%d failing check(s)' % len(fails))
sys.exit(1 if fails else 0)
