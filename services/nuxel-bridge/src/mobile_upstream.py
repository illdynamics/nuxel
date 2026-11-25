"""Shared read-only cellular upstream gate for hotspot and USB sharing."""
import json
from pathlib import Path
import subprocess
from native_radio import NativeRadio


def status():
    radio = NativeRadio().status()
    result = {'available': False, 'interface': None, 'carrier_interface': 'rmnet0',
              'ipv4_translated': False, 'dns': [], 'error': 'Mobile internet is unavailable'}
    if not radio.get('connected') or not radio.get('registered'):
        return result
    try:
        link = json.loads(Path('/run/nuxel-radio/cellular-link.json').read_text())
        if not link.get('configured'): return result
        config = link['config']; result['dns'] = config['dns']
        result['mtu'] = config['mtu'] - (20 if '4' not in config['sources'] else 0)
        if '4' in config['sources']:
            interface = 'rmnet0'
        else:
            clat = json.loads(Path('/run/nuxel-radio/clat.json').read_text())
            if not clat.get('active') or not Path('/sys/class/net/nuxclat').exists():
                result['error'] = 'IPv6 LTE is connected; IPv4 translation is unavailable'
                return result
            interface = 'nuxclat'; result['ipv4_translated'] = True
        routes = json.loads(subprocess.check_output(['ip','-j','-4','route','show','default','dev',interface],text=True,timeout=3))
        if not routes: return result
        result.update(available=True, interface=interface, error=None)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        pass
    return result
