#!/usr/bin/env python3
"""v0.8.5-beta live regressions.

These pin the behaviours the owner exercised on the handset on 2026-11-14:

  * nuxel-pow.mp3 is the default cue for notifications AND messages, and the
    notification hub asks soundd to play that assignment for every accepted
    notification (the "swipe the top bar open and see the alerts" path depends
    on the hub accepting the record; the cue must never block that);
  * the sound player survives a route-heal failure: live, the first broken
    pipe after a cold boot raised AttributeError(_last_route_heal) and ended
    the ONLY player thread, so every later notification was silent;
  * Lifecycle Edge FX: screen wake (unlock) is on by default and a stored
    document cannot accidentally disable it, while notification edge lighting
    keeps polling even when a settings load is slow or rejected;
  * the live installer keeps the firewall enabled across deploys/reboots.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond or not extra else '  ' + str(extra)))
    if not cond:
        fails.append(name)


def read(rel):
    return (ROOT / rel).read_text(errors='replace')


soundd = read('services/nuxel-sound/nuxel-soundd.py')
notif = read('services/nuxel-notifications/src/notifications.py')
engine = read('pwa/nuxel-home/js/edge-lighting.js')
installer = read('scripts/nuxel-live-install.py')
firewall_unit = read('configs/nftables/systemd/nuxel-firewall.service')

check('notification cue is nuxel-pow.mp3', '"notification": "nuxel-pow.mp3"' in soundd)
check('message cue is nuxel-pow.mp3', '"message": "nuxel-pow.mp3"' in soundd)
check('notification hub asks soundd for the notification action',
      "SOUND_ACTION = os.environ.get('NUXEL_NOTIFICATION_SOUND_ACTION', 'notification')" in notif
      and "_play_notification_cue()" in notif)
check('hub cue is best-effort and never raises into delivery',
      'Never raises' in notif or 'never raises' in notif and 'def _play_notification_cue' in notif)
check('route heal reads the rate-limit attribute defensively',
      'getattr(self, "_last_route_heal", 0.0)' in soundd)
check('broken-pipe repair cannot kill the player loop',
      'audio route repair crashed; restarting stream' in soundd
      and 'except Exception:  # noqa: BLE001 - a repair must never kill the loop' in soundd)
check('player loop catches every exception and continues',
      'sound player loop error; continuing' in soundd)
check('wake lifecycle default has unlock + screen_on enabled',
      "lifecycle: { screen_on: true, screen_off: false, lock: false, unlock: true }" in engine)
_boot = engine.split('function boot()')[1]
_boot = _boot[:_boot.find('\n    }')]
_boot_start = _boot.find('startPolling();')
_boot_load = _boot.find('loadSettings().then')
check('notification journal poll starts before settings load (A85)',
      _boot_start >= 0 and (_boot_load < 0 or _boot_start < _boot_load))
check('focus visibility is not display sleep (A85)',
      'if (global.document.hidden) return true;' not in engine
      and 'A85' in engine)
check('firewall unit remains enabled at boot', 'WantedBy=multi-user.target' in firewall_unit)
check('live installer enables the firewall persistently', 'nuxel-firewall.service' in installer)

# Syntax gate for the edited Python modules.
for rel in ('services/nuxel-sound/nuxel-soundd.py',
            'services/nuxel-notifications/src/notifications.py',
            'scripts/nuxel-live-install.py'):
    try:
        ast.parse(read(rel))
        ok = True
    except SyntaxError as exc:  # pragma: no cover
        ok = False
        print(exc)
    check('syntax: ' + rel, ok)

print(f"{len(fails)} failed")
raise SystemExit(0 if not fails else 1)
