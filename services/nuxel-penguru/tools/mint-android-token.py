#!/usr/bin/env python3
"""Mint a launcher-bound PenGuru token for the Android app.

Run as root on the Nuxel host. The native PWA host's per-device secret proves
that the owner authorized this token; the secret itself is never printed or
sent anywhere except the loopback bridge.

The bridge issues one-hour tokens. Paste the printed token into PenGuru Squad
-> Settings -> Connection. Re-run this tool when the app reports
`launcher_token_required` after expiry. The token is bound to
`org.nuxel.PenGuru` and cannot be used as another app identity.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

SECRET_FILE = '/etc/nuxel/keyring-launcher.secret'
APP_ID = 'org.nuxel.PenGuru'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8080/api/v1',
                        help='bridge API base URL (default: loopback)')
    parser.add_argument('--json', action='store_true', help='emit machine-readable JSON')
    parser.add_argument('--secret-file', default=SECRET_FILE,
                        help='launcher secret file (default: %(default)s)')
    args = parser.parse_args()

    if os.geteuid() != 0:
        parser.error('run as root on the Nuxel host (the launcher secret is root-only)')
    try:
        with open(args.secret_file, 'r') as stream:
            secret = stream.read(256).strip()
    except OSError as exc:
        print(f'cannot read launcher secret: {exc}', file=sys.stderr)
        return 2
    if len(secret) != 64 or any(c not in '0123456789abcdefABCDEF' for c in secret):
        print('launcher secret is absent or malformed', file=sys.stderr)
        return 2

    body = json.dumps({'app_id': APP_ID}).encode()
    request = urllib.request.Request(
        args.url.rstrip('/') + '/auth/app-token', data=body, method='POST',
        headers={'Content-Type': 'application/json',
                 'X-Nuxel-Bridge-Version': '1',
                 'X-Nuxel-Launcher-Secret': secret})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read(1048576))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f'bridge refused the token request: {exc}', file=sys.stderr)
        return 1
    if not payload.get('success') or not payload.get('token'):
        print(f"bridge refused the token request: {payload.get('error', 'unknown')}",
              file=sys.stderr)
        return 1

    expires = float(payload.get('expires_at') or 0)
    ttl = int(payload.get('ttl') or max(0, expires - time.time()))
    if args.json:
        print(json.dumps({'app_id': APP_ID, 'token': payload['token'],
                          'expires_at': expires, 'ttl_seconds': ttl}, indent=2))
    else:
        print('PenGuru Android launcher token')
        print('================================')
        print(f'app:     {APP_ID}')
        print(f'expires: {time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(expires))}'
              f' (~{ttl}s)')
        print()
        print(payload['token'])
        print()
        print('Paste this into PenGuru Squad -> Settings -> Connection, then')
        print('press "Save & reconnect". The token never leaves your devices.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
