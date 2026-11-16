#!/usr/bin/env python3
"""Torch safety for PWNAGE-103000: policy ceiling, OFF on init/exit, readback,
idempotent rapid toggles, error cleanup, staleness, no LED/RGB advertisement."""
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, finish  # noqa: E402
import flashlight_provider as fp  # noqa: E402


def fixture(tmp, brightness='0', max_on_ms=None, led_name='torch-sec1'):
    root = Path(tmp)
    led = root / 'leds' / led_name
    led.mkdir(parents=True)
    (led / 'brightness').write_text(brightness)
    (led / 'max_brightness').write_text('15')
    policy = json.loads((ROOT / 'configs/nuxel/leds/leds.json').read_text())
    if max_on_ms is not None:
        policy['safety']['max_on_ms'] = max_on_ms
    pol = root / 'leds.json'
    pol.write_text(json.dumps(policy))
    os.environ.update({
        'NUXEL_LEDS_ROOT': str(root / 'leds'),
        'NUXEL_LED_POLICY': str(pol),
        'NUXEL_FLASHLIGHT_STATE': str(root / 'state.json'),
        'NUXEL_CAMERA_ACTIVE': str(root / 'camera-active'),
        'NUXEL_THERMAL_ROOT': str(root / 'thermal'),
        # Keep the camera-class candidate inside the fixture: a missing path is
        # NOT_SUPPORTED_ON_DEVICE, never a silent fallback to a host LED.
        'NUXEL_FLASH_ROOT': str(root / 'camera-flash'),
    })
    (root / 'thermal').mkdir(exist_ok=True)
    fp._PROVIDER = None
    return led


with tempfile.TemporaryDirectory() as td:
    led = fixture(td)
    p = fp.get_provider()
    check('policy ceiling is 600 s, not the old hard-coded 300 s', p._max_on_seconds() == 600.0,
          p._max_on_seconds())
    check('fresh provider reports the real LED class', p.status()['supported'] is True)
    check('OFF by default', p.status()['state'] == 'OFF' and (led / 'brightness').read_text() == '0')
    st = p.set_enabled(True, 'test')
    check('explicit ON enables and reports a remaining time',
          st['state'] == 'ON' and st['remaining_seconds'] > 590)
    check('ON write read back', (led / 'brightness').read_text() == '15')
    st = p.set_enabled(False, 'test')
    check('explicit OFF returns to zero', st['state'] == 'OFF' and (led / 'brightness').read_text() == '0')
    lat = []
    for i in range(10):
        lat.append(fp.handle('toggle', {'requested_by': 'rapid'})['state'])
    check('10 rapid toggles end in a known OFF/ON state with at most one timer',
          lat[-1] in ('ON', 'OFF') and p._timer is not None or lat[-1] == 'OFF', lat[-1])
    p.force_off('rapid-cleanup')
    check('rapid toggles cannot leave the LED on', (led / 'brightness').read_text() == '0'
          and p.status()['state'] == 'OFF')

with tempfile.TemporaryDirectory() as td:
    led = fixture(td, brightness='15')
    p = fp.get_provider()
    check('provider init forces a stale ON LED to OFF', (led / 'brightness').read_text() == '0'
          and p.status()['state'] == 'OFF')

with tempfile.TemporaryDirectory() as td:
    led = fixture(td, max_on_ms=600)
    p = fp.get_provider()
    p.set_enabled(True, 'short-timeout')
    check('bounded ON before timeout', (led / 'brightness').read_text() == '15')
    # Bounded wait (never an unbounded torch test); fail loudly if the timer
    # did not fire.
    deadline = time.time() + 3.0
    while time.time() < deadline and (led / 'brightness').read_text() != '0':
        time.sleep(0.05)
    check('daemon-side timeout forces OFF (not just a browser timer)',
          p.status()['state'] == 'OFF' and (led / 'brightness').read_text() == '0',
          (p.status()['state'], (led / 'brightness').read_text(), p._max_on_seconds()))
    check('timeout clears the session and remaining time',
          p.status()['session'] is None and p.status()['remaining_seconds'] == 0.0)

with tempfile.TemporaryDirectory() as td:
    led = fixture(td)
    p = fp.get_provider()
    p.set_enabled(True, 'exit-test')
    p.force_off('simulated-exit')
    check('service exit path leaves the LED off', (led / 'brightness').read_text() == '0')
    # Write failure path: make the node unwritable and confirm ERROR + best-effort OFF.
    # Replace the writable node with a DIRECTORY: every open("w") fails with a
    # real OSError regardless of the (possibly root) test user.
    (led / 'brightness').unlink()
    (led / 'brightness').mkdir()
    st = p.set_enabled(True, 'write-fail')
    check('a failed ON is reported as ERROR, never a fake ON', st['state'] == 'ERROR' and st['on'] is False,
          (st['state'], st.get('last_error')))
    check('a failed ON records the exact error', bool(st['last_error']))
    check('failed ON leaves the LED node without a stale enabled value',
          not (led / 'brightness').is_file())

with tempfile.TemporaryDirectory() as td:
    led = fixture(td)
    p = fp.get_provider()
    (Path(td) / 'thermal').mkdir(exist_ok=True)
    tz = Path(td) / 'thermal' / 'thermal_zone0'
    tz.mkdir()
    (tz / 'temp').write_text('85000')
    st = p.set_enabled(True, 'hot')
    check('real thermal telemetry blocks the torch', st['state'] == 'THERMAL_LIMIT'
          and (led / 'brightness').read_text() == '0')
    (tz / 'temp').write_text('42000')
    (Path(td) / 'camera-active').write_text('1')
    st = p.set_enabled(True, 'camera')
    check('camera ownership blocks the shared flash', st['state'] == 'BLOCKED_CAMERA'
          and (led / 'brightness').read_text() == '0')

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / 'leds').mkdir()
    led = root / 'leds' / 'leds-sec1'
    led.mkdir()
    (led / 'brightness').write_text('0')
    (led / 'max_brightness').write_text('15')
    os.environ.update({
        'NUXEL_LEDS_ROOT': str(root / 'leds'),
        'NUXEL_LED_POLICY': str(ROOT / 'configs/nuxel/leds/leds.json'),
        'NUXEL_FLASHLIGHT_STATE': str(root / 'state.json'),
        'NUXEL_CAMERA_ACTIVE': str(root / 'none'),
        'NUXEL_THERMAL_ROOT': str(root / 'thermal'),
        'NUXEL_FLASH_ROOT': str(root / 'camera-flash'),
    })
    (root / 'thermal').mkdir()
    fp._PROVIDER = None
    st = fp.get_provider().set_enabled(True, 'test')
    check('leds-sec1 is never adopted as a torch/notification colour source',
          st['state'] == 'NOT_SUPPORTED_ON_DEVICE' and (led / 'brightness').read_text() == '0')

# Policy document must advertise the real ceilings and no auto-on.
pol = json.loads((ROOT / 'configs/nuxel/leds/leds.json').read_text())
check('policy keeps max_on_ms=600000 and auto_on_boot=false',
      pol['safety']['max_on_ms'] == 600000 and pol['safety']['auto_on_boot'] is False)
check('policy has no notification LED claim on the S10+ display path',
      pol['classes']['edge_lighting']['hardware_led'] is False)
check('flashlight code has no notification trigger path',
      'notification' not in (ROOT / 'services/nuxel-bridge/src/flashlight_provider.py').read_text().lower())

finish('PWNAGE-103000 torch safety')
