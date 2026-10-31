#!/usr/bin/env python3
"""PWNAGE-44000 screenshot helper packaging contract.

Host SHOT_BIN, source CLI contract and the rootfs install path must agree.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
host = (ROOT / 'tools/s10plus/a45/nuxel-pwa-host.c').read_text()
build = (ROOT / 'images/s10plus/build-phone-rootfs-inside-fedora.sh').read_text()
helper = (ROOT / 'tools/s10plus/a68/nuxel-screenshot.c').read_text()

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)))
    if not cond: fails.append(name)

m = re.search(r'#define SHOT_BIN "([^"]+)"', host)
path = m.group(1) if m else ''
check('host SHOT_BIN is the installed path', path == '/usr/lib/nuxel/nuxel-screenshot', path)
check('build compiles the screenshot helper from source', 'tools/s10plus/a68/nuxel-screenshot.c' in build)
check('build installs the exact SHOT_BIN path', '"$STAGE/usr/lib/nuxel/nuxel-screenshot"' in build)
check('helper takes the destination PPM as argv[1]', 'argc > 1 ? argv[1]' in helper)
check('helper emits P6 PPM (host conversion contract)', 'P6\\n' in helper)
check('helper never opens /dev/fb0', 'open("/dev/fb0"' not in helper)
check('host never opens /dev/fb0 for screenshots', 'open("/dev/fb0"' not in host)
check('host writes PNG under the Gallery directory', '#define SHOT_DIR "/home/nuxel/Gallery"' in host)
check('host bounds the helper and kills only its child', 'kill(pid, SIGKILL)' in host and 'waitpid(pid' in host)

print('\n%d failing check(s)' % len(fails))
sys.exit(1 if fails else 0)
