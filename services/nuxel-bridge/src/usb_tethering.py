#!/usr/bin/env python3
"""Physical CDC-ECM networking, independent of ZeroTier and USB serial.

The fixed systemd helper owns address/gadget changes outside the bridge's
read-only mount namespace. Stop removes the USB address, leaving ACM intact.
"""
from pathlib import Path
import json
import os
import subprocess

UNIT = 'nuxel-usb-net-up.service'
HELPER = '/usr/lib/nuxel/nuxel-usb-net-up.sh'
def _usb_config():
    values = {'NUXEL_USB_NET_ADDR': '10.100.10.1/24',
              'NUXEL_USB_NET_HOST_ADDR': '10.100.10.2/24',
              'NUXEL_USB_NET_SUBNET': '10.100.10.0/24'}
    path = os.environ.get('NUXEL_USB_NET_CONFIG', '/etc/nuxel/usb-network.conf')
    try:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            if key.strip() in values:
                values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return values

_USB_CONFIG = _usb_config()
ADDRESS = _USB_CONFIG['NUXEL_USB_NET_ADDR'].split('/', 1)[0]
HOST = _USB_CONFIG['NUXEL_USB_NET_HOST_ADDR']
_MODES = {'off': 'charging', 'charging': 'charging', 'usb-net': 'usb_network',
          'usbnet': 'usb_network', 'usb_network': 'usb_network',
          'tether': 'usb_tethering', 'usb-tether': 'usb_tethering',
          'usb_tethering': 'usb_tethering'}

def _run(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=55)

def normalize_function(function=None):
    return 'ecm' if str(function or 'ecm').lower() in ('ecm', 'auto', '') else ''

def current_state():
    try:
        links = json.loads(_run('ip', '-j', '-4', 'addr', 'show', 'dev', 'usb0').stdout or '[]')
        addressed = any(a.get('local') == ADDRESS for link in links for a in link.get('addr_info', []))
        enabled = _run('systemctl', 'is-enabled', UNIT).stdout.strip() == 'enabled'
        carrier = Path('/sys/class/net/usb0/carrier').read_text().strip() == '1'
    except (OSError, ValueError, subprocess.SubprocessError):
        addressed, enabled, carrier = False, False, False
    try:
        tether = json.loads(Path('/run/nuxel/usb-tether.json').read_text()).get('enabled', False)
    except (OSError, ValueError):
        tether = False
    mode = 'usb_tethering' if tether and addressed else 'usb_network' if addressed else 'charging'
    return {'success': True, 'selected': mode, 'mode': mode, 'active': addressed,
            'enabled': enabled, 'link_connected': carrier, 'interface': 'usb0' if addressed else '',
            'function': 'ecm', 'source': 'gadget:ecm+acm', 'tether_composition': tether,
            'device_ip': ADDRESS + '/24' if addressed else '', 'host_ip': HOST,
            'subnet': _USB_CONFIG['NUXEL_USB_NET_SUBNET'], 'acm_preserved': Path('/dev/ttyGS0').exists(),
            'last_error': None}

def set_mode(mode, function='ecm'):
    target = _MODES.get(str(mode).lower())
    if not target:
        return {'success': False, 'error': 'unknown-mode', 'error_code': 'INVALID_MODE'}
    if not normalize_function(function):
        return {'success': False, 'error': 'Only the validated CDC-ECM function is supported',
                'error_code': 'UNSUPPORTED_FUNCTION'}
    if target == 'charging':
        return disable_all()
    proc = _run('systemctl', 'enable', '--now', UNIT)
    result = current_state()
    result['success'] = proc.returncode == 0 and result['active']
    if not result['success']:
        result['error'] = proc.stderr.strip() or 'USB interface did not acquire its address'
    return result

def preflight(mode='usb_network'):
    return dict(current_state(), requested=_MODES.get(mode), helper_present=Path(HELPER).exists(), mutated=False)

def start_tethering_composition():
    return set_mode('usb_tethering')

def enable_for_host(upstream=None):
    import usb_tether
    link = set_mode('usb_network')
    if not link['success']:
        return dict(link, stage='usb-network')
    return dict(usb_tether.start(upstream, source='usb-net:enable-for-host'), usb=current_state())

def disable_all(source='api'):
    import usb_tether
    tether = usb_tether.stop(source=source)
    ssh = _run('systemctl', 'disable', '--now', 'nuxel-usb-ssh.service')
    proc = _run('systemctl', 'disable', '--now', UNIT)
    return dict(current_state(), success=proc.returncode == 0 and ssh.returncode == 0 and tether.get('success', False),
                tether=tether, error=proc.stderr.strip() or None)

def stop():
    return disable_all()
