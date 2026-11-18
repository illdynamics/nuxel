#!/usr/bin/env python3
"""Root-only device acceptance via real launcher-token HTTP authentication.

Never prints the device launcher secret or issued token. Leaves PenGuru OFF.
"""
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8080/api/v1'


def post(route, body, headers=None):
    request = urllib.request.Request(BASE + route, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'X-Nuxel-Bridge-Version': '1', **(headers or {})})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def main():
    app = 'org.nuxel.PenGuru'
    secret = Path('/etc/nuxel/keyring-launcher.secret').read_text().strip()
    token = post('/auth/app-token', {'app_id': app}, {'X-Nuxel-Launcher-Secret': secret})['token']
    def call(verb, params=None):
        result = post('/rpc', {'app_id': app, 'namespace': 'penguru', 'verb': verb, 'params': params or {}},
                      {'Authorization': 'Bearer ' + token})['result']
        if not result.get('ok'):
            raise RuntimeError(str(result))
        return result
    try:
        call('set_enabled', {'enabled': True})
        status = call('status')['status']
        assert status['enabled'] and len(status['models']) == 3
        print('PASS launcher-authenticated enable/status; three model cards')
        call('set_mode', {'mode': 'squad'})
        request = call('submit', {'text': 'What is my battery level?'})['request_id']
        for attempt in range(30):
            record = call('get', {'request_id': request})['request']
            if record['status'] in ('done', 'error'):
                break
            time.sleep(.2)
        assert record['status'] == 'done' and record['route'] == 'SYSTEM', record['status']
        print('PASS real read-only battery route through authenticated HTTP, IPC and supervisor')
        try:
            result = post('/rpc', {'app_id': 'nuxel-settings', 'namespace': 'penguru', 'verb': 'status'},
                          {'Authorization': 'Bearer ' + token})
            assert not result.get('result', {}).get('ok'), 'Cross-app identity accepted'
            print('PASS cross-app token rejected')
        except urllib.error.HTTPError as error:
            if error.code != 403:
                raise
            print('PASS cross-app token rejected with HTTP 403')
    finally:
        call('set_enabled', {'enabled': False})
        assert call('status')['status']['enabled'] is False
        print('PASS OFF via authenticated HTTP')


if __name__ == '__main__':
    main()
