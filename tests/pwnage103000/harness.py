#!/usr/bin/env python3
"""PWNAGE-103000 test harness.

Runs DOM-free JavaScript modules in node with tiny stubs (no browser) and runs
the Edge Lighting / Edge FX / torch contract checks.  Prints PASS/FAIL per check
and exits non-zero on any failure, matching the repository's script tests.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / 'pwa/nuxel-home/js'
FX = ROOT / 'pwa/nuxel-apps/edge-fx'

fails = []


def check(name, cond, extra=''):
    line = ('PASS ' if cond else 'FAIL ') + name
    if not cond and extra:
        line += '  ' + str(extra)
    print(line)
    if not cond:
        fails.append(name)
    return bool(cond)


def node_script(body, modules=None):
    """Evaluate a JS snippet after loading the given module files in order."""
    mods = modules if modules is not None else ['edge-lighting.js', 'edge-panel-gesture.js']
    # The modules attach themselves to the global object (window-like); in
    # node that ends up on globalThis, so bind the test scope to it.
    pre = 'const global = globalThis;\n'
    # A plain script export carries no CommonJS bindings, so require() hides the
    # module's globals; evaluate the source in this scope instead (it attaches to
    # the `global` binding above, exactly like a classic <script> tag).
    pre += ''.join(
        "(function(){var require=undefined,module=undefined,exports=undefined;\n%s\n})();\n"
        % (JS / m).read_text() for m in mods)
    full = pre + body
    proc = subprocess.run(['node', '-e', full], capture_output=True, text=True, timeout=60)
    return proc


def node_json(body, modules=None):
    proc = node_script(body, modules)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])
    tail = proc.stdout.strip().splitlines()[-1]
    return json.loads(tail)


def finish(title):
    print()
    if fails:
        print('%s: %d FAILING CHECK(S): %s' % (title, len(fails), ', '.join(fails)))
        sys.exit(1)
    print('%s: ALL PASS' % title)
