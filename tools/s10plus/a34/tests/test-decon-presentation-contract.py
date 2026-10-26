#!/usr/bin/env python3
"""Offline source/integration assertions guarding the A35 stale-panel regression."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
bridge = (ROOT / 'tools/s10plus/a34/nuxel-wl-fb.c').read_text()
rootfs = (ROOT / 'images/s10plus/build-phone-rootfs-inside-fedora.sh').read_text()
unit = (ROOT / 'services/nuxel-session/systemd/nuxel-wl-fb.service').read_text()

assert 'return panel_commit_frame("frame");' in bridge, 'blit must commit each frame'
# A65 wrapped the steady-state blit in `if (changed)`: unchanged frames are
# skipped on purpose, but EVERY changed frame must still be committed.  Assert
# the invariant, not one historical brace layout (the old regex required the
# comment to sit directly after `else {`, which stopped matching and turned
# every release run red).
assert re.search(r'if \(changed\) \{.*?/\* Command-mode Samsung DECON:.*?frame_blit_once\(\)',bridge,re.S), 'live steady loop must use committed frame'
assert 'panel_assert("post-stop");' in bridge and 'bl_power_write(0, "launcher-first-frame");' in bridge
assert re.search(r'panel_assert\("post-stop"\);.*?frame_blit_once\(\)',bridge,re.S), 'initial frame must pan'
assert 'panel_blank_powerdown("screen-off");' in bridge, 'real panel blank must be attempted'
assert 'FBIOPAN_DISPLAY' in bridge and 'decon_pan_failed' in bridge
assert '/nuxel/tools/s10plus/a34/nuxel-wl-fb.c' in rootfs, 'rootfs CI build must compile the patched source'
assert '-I/nuxel/tools/s10plus/a33' in rootfs, (
    'rootfs CI build must include the shared A33 handoff-logic header used by the A34 bridge'
)
assert 'ExecStart=/usr/lib/nuxel/nuxel-wl-fb' in unit
assert 'fbio_pan_display' not in unit.lower(), 'service must not launch another fb writer'
print('PASS A35 source-to-rootfs commit/blank/startup contract')
