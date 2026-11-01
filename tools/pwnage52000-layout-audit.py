#!/usr/bin/env python3
"""Minimal CDP layout probe used by PWNAGE-52000 evidence.

Launch Chromium/Chrome with --headless=new --remote-debugging-port=9225 and a
temporary --user-data-dir, serve the repo PWA tree over HTTP, then run:

    python3 tools/pwnage52000-layout-audit.py URL WIDTH HEIGHT EXPRESSION

The expression is evaluated with awaitPromise and returned as JSON.  This
script does not start a browser, does not modify the page and does not require
the Nuxel bridge; it is an engineering audit tool, not a runtime dependency.
"""
import json
import os
import sys
import time

import requests
import websocket

port = int(os.environ.get('CDP_PORT', '9225'))
url, width, height, expr = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
tab = requests.put('http://127.0.0.1:%d/json/new?%s' %
                   (port, requests.utils.quote(url, safe=''))).json()
ws = websocket.create_connection(tab['webSocketDebuggerUrl'], timeout=30)
seq = 0


def command(method, params=None):
    global seq
    seq += 1
    ws.send(json.dumps({'id': seq, 'method': method, 'params': params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == seq:
            return msg


try:
    command('Page.enable')
    command('Runtime.enable')
    command('Emulation.setDeviceMetricsOverride', {
        'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': True})
    command('Page.navigate', {'url': url})
    time.sleep(2.0)
    result = command('Runtime.evaluate', {
        'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    value = result.get('result', {}).get('result', {})
    print(json.dumps(value.get('value', result), indent=2))
finally:
    ws.close()
    try:
        requests.get('http://127.0.0.1:%d/json/close/%s' % (port, tab['id']))
    except Exception:
        pass
