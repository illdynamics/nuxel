"""Launcher-authenticated PenGuru lifecycle and Unix IPC adapter.

Only fixed units and fixed verbs; no model output reaches this module.
The HTTP entry point checks launcher issuer and derives the session from its token.
"""
import hashlib
import json
import os
import socket
import subprocess
import threading
import time

APPS = {'org.nuxel.PenGuru', 'nuxel-settings', 'org.nuxel.Settings'}
OPS = {'status', 'set_enabled', 'set_mode', 'set_runtime', 'submit', 'get', 'cancel',
       'clear_all', 'delete_conversation', 'list_models', 'start_download',
       'download_status', 'cancel_download', 'delete_model', 'diagnostics'}
LOCK = threading.RLock()


def unit(action, download=False):
    name = 'nuxel-penguru-download.service' if download else 'nuxel-penguru.service'
    return subprocess.run(['systemctl', action, name], capture_output=True,
                          text=True, timeout=20)


def ipc(app, session, verb, params, download=False):
    path = '/run/nuxel-penguru-download/control.sock' if download else '/run/nuxel-penguru/control.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(120)
        sock.connect(path)
        sock.sendall((json.dumps({'app_id': app, 'session_id': session}) + '\n' +
                      json.dumps(dict(params, op=verb)) + '\n').encode())
        with sock.makefile('rb') as stream:
            return json.loads(stream.readline(1048576))


def handle(app, token, verb, params):
    if app not in APPS or not token or token.get('issuer') != 'nuxel-launcher':
        return {'ok': False, 'error': 'launcher_identity_required'}
    if token.get('app_id') != app or verb not in OPS or not isinstance(params, dict):
        return {'ok': False, 'error': 'invalid_request'}
    session = hashlib.sha256(json.dumps(token, sort_keys=True).encode()).hexdigest()
    try:
        if verb == 'set_enabled':
            if type(params.get('enabled')) is not bool:
                return {'ok': False, 'error': 'invalid_enabled'}
            with LOCK:
                if not params['enabled']:
                    a, b = unit('stop', True), unit('stop')
                    return {'ok': a.returncode == b.returncode == 0, 'enabled': False,
                            'error': None if a.returncode == b.returncode == 0 else 'stop_failed'}
                result = unit('start')
                if result.returncode:
                    return {'ok': False, 'error': 'service_start_failed', 'detail': result.stderr[-1000:]}
                for _ in range(30):
                    if os.path.exists('/run/nuxel-penguru/control.sock'):
                        break
                    time.sleep(.1)
                return ipc(app, session, 'status', {})
        active = unit('is-active').returncode == 0
        if not active:
            if verb in ('status', 'list_models'):
                return {'ok': True, 'status': {'enabled': False, 'state': 'DISABLED',
                        'mode': 'squad', 'runtime_preference': 'auto', 'models': [],
                        'voice': {'listening': False}}}
            return {'ok': False, 'error': 'disabled', 'detail': 'Enable PenGuru first'}
        download = verb in ('start_download', 'download_status', 'cancel_download')
        if verb == 'start_download':
            result = unit('start', True)
            if result.returncode:
                return {'ok': False, 'error': 'download_service_start_failed', 'detail': result.stderr[-1000:]}
            for _ in range(30):
                if os.path.exists('/run/nuxel-penguru-download/control.sock'):
                    break
                time.sleep(.1)
        return ipc(app, session, verb, params, download)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {'ok': False, 'error': 'penguru_unavailable', 'detail': str(exc)}
