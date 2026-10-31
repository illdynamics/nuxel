#!/usr/bin/env python3
"""PWNAGE-44000 active-build power-menu parity.

The S10+ image builder compiles tools/s10plus/a34/nuxel-button-fsm.h into the
live nuxel-button-manager.  The pre-existing FSM test inspected A33 only, so an
11-entry A34 table passed while the shipped image silently lacked Back/Forward/
Stop/Reload.  This test drives the REAL A34 header (the same file the builder
compiles) and compares its menu table with configs/nuxel/input/button-fsm.json.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
HEADER = os.path.join(ROOT, 'tools/s10plus/a34/nuxel-button-fsm.h')
CONFIG = os.path.join(ROOT, 'configs/nuxel/input/button-fsm.json')
MANAGER = os.path.join(ROOT, 'tools/s10plus/a34/nuxel-button-manager.c')

failures = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else ('  ' + str(extra))))
    if not cond:
        failures.append(name)

with open(CONFIG) as fh:
    cfg = json.load(fh)
entries = cfg['power_menu']['entries']

with tempfile.TemporaryDirectory() as td:
    exe = os.path.join(td, 'fsm-sim')
    cc = os.environ.get('CC', 'cc')
    r = subprocess.run([cc, '-std=c11', '-O1', '-DNUXEL_FSM_MAIN', '-x', 'c', HEADER, '-o', exe],
                       capture_output=True, text=True)
    check('active A34 FSM compiles', r.returncode == 0, r.stderr[-800:])
    if r.returncode != 0:
        sys.exit(1)
    dump = subprocess.run([exe, '--menu-dump'], capture_output=True, text=True, check=True).stdout
    menu = []
    count = None
    for line in dump.splitlines():
        if line.startswith('MENU_COUNT '):
            count = int(line.split()[1])
        if line.startswith('ENTRY '):
            parts = line.split()
            # ENTRY <i> <id> allowed=<0|1> action=<a> refusal=<r>
            menu.append({
                'id': parts[2],
                'allowed': parts[3].split('=', 1)[1] == '1',
                'action': parts[4].split('=', 1)[1],
                'refusal': parts[5].split('=', 1)[1],
            })

check('configured menu has 15 entries', len(entries) == 15, len(entries))
check('active A34 MENU_COUNT is 15', count == 15, count)
check('active A34 table length is 15', len(menu) == 15, len(menu))
for i, (want, got) in enumerate(zip(entries, menu)):
    check('entry %d id %s' % (i, want['id']), want['id'] == got['id'], got['id'])
    check('entry %d action %s' % (i, want['action']), want['action'] == got['action'], got['action'])
    check('entry %d allowed %s' % (i, want['trigger_allowed']), bool(want['trigger_allowed']) == got['allowed'], got['allowed'])
    # Allowed entries may carry descriptive refusal metadata that is only
    # consulted when trigger_allowed is false; the executable contract is the
    # allowed flag plus the action mapping above.
    if not want['trigger_allowed']:
        check('entry %d carries NO_FLASH_INVARIANT' % i, got['refusal'] == 'NO_FLASH_INVARIANT', got['refusal'])

# The active dispatcher must actually forward the restored browser controls and
# must never turn Recovery/Download into a reboot/bootloader operation.
with open(MANAGER) as fh:
    src = fh.read()
forwarded = ('!strcmp(action, "back") || !strcmp(action, "forward") ||\n'
             '      !strcmp(action, "stop") || !strcmp(action, "reload-launcher")')
check('dispatcher forwards the four browser controls to the host',
      forwarded in src and 'fifo_send(HOST_FIFO, l)' in src)
check('dispatcher keeps NO_FLASH_INVARIANT refusal',
      'NO_FLASH_INVARIANT' in src and 'enter-recovery' in src and 'enter-download-mode' in src)

print('\n%d failing check(s)' % len(failures))
sys.exit(1 if failures else 0)
