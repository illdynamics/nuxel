#!/usr/bin/env python3
"""A84: microphone capture path.

Measured on the live S10+ (2026-11-14): the WDMA1 source is present and
captures real audio (pw-cat peak 4711), `wpctl status` lists it, yet the bridge
answered `"no capture source"` - the parser dropped the row - and native
PipeWire was reachable only by root because /run/nuxel-wayland/pipewire-0 is
0750 root:root while the Pulse socket is 0660 root:nuxel.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))

fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)[:300]))
    if not cond:
        fails.append(name)


import mic_provider as mic

# --- the exact live `wpctl status` shape ---------------------------------
LIVE = """PipeWire 'pipewire-0' [1.4.11, root@host, cookie:1]
 └─ Clients:
        34. WirePlumber
Audio
 ├─ Devices:
 │
 ├─ Sinks:
 │  *   31. S10+ speaker (RDMA1, 48 kHz)        [vol: 0.50]
 │
 ├─ Sources:
 │  *   32. S10+ microphone (WDMA1, 48 kHz)     [vol: 1.00]
 │
 ├─ Filters:
 │
 └─ Streams:
        36. pw-cat
Video
Settings
 └─ Default Configured Devices:
         0. Audio/Sink    alsa_output.hw_0_1
         1. Audio/Source  alsa_input.hw_0_13
"""


class Proc:
    returncode = 0
    stderr = ''
    stdout = LIVE


orig = mic._run
mic._run = lambda argv, timeout=5.0, binary=False: Proc()
try:
    rows, err = mic._sources()
finally:
    mic._run = orig
check('live wpctl output yields the WDMA1 microphone', len(rows) == 1 and rows[0]['id'] == 32, rows)
check('microphone row is the default source', bool(rows and rows[0]['default']))
check('microphone volume is reported (100%)', bool(rows and rows[0]['volume'] == 1.0))
check('speaker row is not mistaken for a source', all('speaker' not in r['name'] for r in rows))
check('no parse error is reported', err is None)

# --- a muted / volume-different source still parses ----------------------
LIVE_MUTED = LIVE.replace('[vol: 1.00]', '[vol: 0.30 MUTED]')
mic._run = lambda argv, timeout=5.0, binary=False: type('P', (), {'returncode': 0, 'stderr': '', 'stdout': LIVE_MUTED})()
try:
    rows, _ = mic._sources()
finally:
    mic._run = orig
check('MUTED suffix parses as muted', bool(rows and rows[0]['muted'] and rows[0]['volume'] == 0.3), rows)

# --- no source at all -----------------------------------------------------
mic._run = lambda argv, timeout=5.0, binary=False: type('P', (), {'returncode': 0, 'stderr': '', 'stdout': 'Audio\n ├─ Sources:\n │\n'})()
try:
    rows, _ = mic._sources()
finally:
    mic._run = orig
check('an empty Sources section yields no rows (honest)', rows == [])

# --- status never invents a source ---------------------------------------
mic._sources = lambda: ([], 'wpctl unavailable')
try:
    st = mic.status()
finally:
    pass
check('status without a source reports available=false', st.get('available') is False)
mic._sources = lambda: ([], None)
lvl = mic.level(120)
check('level without a source is an honest NO_MIC error',
      lvl.get('success') is False and lvl.get('error_code') == 'NO_MIC', lvl)

# --- level() on the live capture path ------------------------------------
# pw-cat is a continuous stream: subprocess.run raises TimeoutExpired with the
# captured bytes on the exception.  The provider must measure those bytes
# instead of reporting "capture failed" (measured live after the A84 deploy).
import struct as _struct
_raw = _struct.pack('<%dh' % 9600, *([2000, -1000] * 4800))
orig_sources = mic._sources
orig_run = mic.subprocess.run


def _timed_out(argv, capture_output=True, timeout=None, stdin=None, env=None):
    raise mic.subprocess.TimeoutExpired(argv, timeout, output=_raw, stderr=b'')


mic._sources = lambda: ([{"default": True, "id": 32, "name": "S10+ microphone",
                          "volume": 1.0, "muted": False}], None)
mic.subprocess.run = _timed_out
try:
    lvl = mic.level(120)
finally:
    mic._sources = orig_sources
    mic.subprocess.run = orig_run
check('level() measures the captured window when pw-cat times out', lvl.get('success') is True, lvl)
check('level() reports peak/rms per channel', bool(lvl.get('metrics', {}).get('left', {}).get('peak')))
check('level() never returns raw audio', 'data' not in lvl and '_raw' not in str(lvl)[:0])

# An immediate failure (no samples at all) is still an honest error.
def _empty_timeout(argv, capture_output=True, timeout=None, stdin=None, env=None):
    raise mic.subprocess.TimeoutExpired(argv, timeout, output=b'', stderr=b'no node')


mic._sources = lambda: ([{"default": True, "id": 32, "name": "m", "volume": 1.0, "muted": False}], None)
mic.subprocess.run = _empty_timeout
try:
    lvl2 = mic.level(120)
finally:
    mic._sources = orig_sources
    mic.subprocess.run = orig_run
check('level() with no samples stays an honest error',
      lvl2.get('success') is False and lvl2.get('error_code') == 'NO_SAMPLES', lvl2)

# --- live session plumbing (static contract) -----------------------------
AUDIO = (ROOT / 'services/nuxel-s10/bin/nuxel-audio-session.sh').read_text()
PKG = (ROOT / 'tools/s10plus/a43/package-live.py').read_text()
DEPLOY = (ROOT / 'scripts/nuxel-deploy-live.py').read_text()
check('audio session grants the session user the PipeWire socket (ACL)',
      'setfacl -m u:nuxel:rw "$RUNTIME/pipewire-0"' in AUDIO)
check('the grant is re-applied when PipeWire recreates the socket',
      'watch_session_socket' in AUDIO and 'grant_session_socket' in AUDIO)
check('mic provider ships in the live payload', 'services/nuxel-bridge/src/mic_provider.py' in PKG)
check('audio session script ships in the live payload', 'services/nuxel-s10/bin/nuxel-audio-session.sh' in PKG)
check('deployer maps the audio session script to /usr/lib/nuxel',
      'nuxel-audio-session.sh' in DEPLOY)
check('deployer maps mic_provider to the bridge tree',
      '/usr/lib/nuxel/nuxel-bridge/mic_provider.py' in DEPLOY)
check('mic level still returns metrics only (no raw audio in the answer)',
      '"metrics": metrics' in (ROOT / 'services/nuxel-bridge/src/mic_provider.py').read_text())

print()
if fails:
    print('A84 MIC: %d FAILURE(S): %s' % (len(fails), ', '.join(fails)))
    sys.exit(1)
print('A84 MIC: ALL PASS')
