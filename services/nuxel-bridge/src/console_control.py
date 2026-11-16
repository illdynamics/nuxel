"""Persistent controls for physical USB serial/SSH and ZeroTier SSH."""
from pathlib import Path
import json
import os
import signal
import subprocess
import time

ADDRESS = '10.11.12.99'
USB_ADDRESS = '10.100.10.1'
UNITS = {'wifi': 'sshd.service', 'usb': 'nuxel-usb-ssh.service', 'serial': 'nuxel-console.service'}
PREF = Path('/var/lib/nuxel/consoles/preferences.json')
APPS = {'org.nuxel.Home', 'org.nuxel.Settings', 'org.nuxel.LiveConsole', 'org.nuxel.USBSSHConsole', 'org.nuxel.WiFiSSHConsole'}

def run(*args):
    return subprocess.run(list(args), capture_output=True, text=True, timeout=12)

def legacy_pids():
    found = []
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            cmd = (proc/'cmdline').read_bytes().split(b'\0')
            if cmd and cmd[0] == b'/opt/nuxel/nuxel-console': found.append(int(proc.name))
        except OSError: pass
    return found

def stop_legacy():
    # The initramfs daemon has a different /run and cannot share the rootfs
    # flock. Retire only that exact executable before handing the tty to systemd.
    pids = legacy_pids()
    for pid in pids:
        try: os.kill(pid, signal.SIGTERM)
        except ProcessLookupError: pass
    for _ in range(20):
        if not legacy_pids(): return
        time.sleep(.05)
    for pid in legacy_pids():
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass

def status():
    transports = {}
    for mode, unit in UNITS.items():
        active = run('systemctl','is-active',unit).stdout.strip()
        enabled = run('systemctl','is-enabled',unit).stdout.strip() == 'enabled'
        port = 2022 if mode == 'usb' else 22
        address = USB_ADDRESS if mode == 'usb' else ADDRESS
        target = '/dev/ttyGS0' if mode == 'serial' else f'{address}:{port}'
        legacy = mode == 'serial' and bool(legacy_pids())
        ready = active == 'active' or legacy
        transports[mode] = {
            'status': 'READY' if ready else ('STARTING' if active in ('activating','reloading') else 'OFF'),
            'enabled': enabled, 'active': ready, 'unit': unit, 'target': target,
            'auth': 'exclusive local USB serial' if mode == 'serial' else 'public key',
            'host_command': './scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport serial --shell' if mode == 'serial' else f'ssh -p {port} -i ~/.ssh/wicked_wqn_id_rsa root@{address}',
            'detail': 'Start and Stop persist across reboot. ' + ('Serial has no IP listener.' if mode == 'serial' else 'USB SSH binds only to the physical USB address 10.100.10.1:2022.' if mode == 'usb' else 'Network SSH binds only to ZeroTier 10.11.12.99:22.'),
            'checks': []}
    return {'success': True, 'transports': transports}

def control(action, transport, app_id):
    if action == 'status': return status()
    if app_id not in APPS: return {'success': False, 'error': 'app_not_authorized'}
    if action not in ('start','stop') or transport not in UNITS:
        return {'success': False, 'error': 'invalid_console_action'}
    unit = UNITS[transport]
    if transport == 'serial': stop_legacy()
    # Enable/disable the service before requesting an asynchronous job. Stop
    # remains responsive while ZeroTier is absent or an ExecStartPre is waiting.
    result = run('systemctl', 'enable' if action == 'start' else 'disable', unit)
    if result.returncode: return {'success': False, 'error': result.stderr.strip()}
    if transport == 'serial':
        PREF.parent.mkdir(parents=True, exist_ok=True)
        temp = PREF.with_suffix('.tmp')
        temp.write_text(json.dumps({'serial': action == 'start'})+'\n')
        os.replace(temp, PREF)
    result = run('systemctl', '--no-block', action, unit)
    if result.returncode: return {'success': False, 'error': result.stderr.strip()}
    return dict(status(), action=action, persisted=True)

def restore_serial():
    stop_legacy()
    try: enabled = json.loads(PREF.read_text()).get('serial', True)
    except (OSError, ValueError): enabled = True
    return run('systemctl','--no-block','start' if enabled else 'stop', UNITS['serial']).returncode

if __name__ == '__main__':
    raise SystemExit(restore_serial())
