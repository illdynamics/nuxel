#!/usr/bin/env python3
"""Pin the A34 touch translation fix (real defect, measured 2026-10-17).

Defect: sec_ts emits SLOT, TRACKING_ID, POSITION_X, POSITION_Y, SYN_REPORT.
The A33 daemon emitted NUXEL_FSM_TOUCH_DOWN inside the TRACKING_ID case, i.e.
before the positions of that frame were known.  A centre tap was therefore
presented to the gesture FSM as a contact that started at the stale (0,0)
coordinate, which is inside the left edge zone; the release then produced
"FSM_ACTION source=touch action=back" (live journal, 12:13:01Z).

The fix: latch pending down/up on TRACKING_ID and emit DOWN/MOVE/UP only on
SYN_REPORT, after the coordinates for that frame have been consumed.

This test is source-structural on purpose: the daemon's translation is inline in
main() and cannot be linked without linux/input.h + alsa.  It fails if anyone
reintroduces feed-on-TRACKING_ID or removes the pending-flag state machine.
"""
import os, re, sys

SRC = os.path.join(os.path.dirname(__file__), '..', 'nuxel-button-manager.c')
s = open(SRC).read()
fails = []
total = 0

def need(cond, msg):
    global total
    total += 1
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)

need('touch_pending_down' in s, 'pending-down latch exists')
need('touch_pending_up' in s, 'pending-up latch exists')
need('touch_active' in s, 'active-contact latch exists')
need('int phase;' in s, 'phase is an int (matches nuxel_fsm_event.phase)')

# Isolate the TRACKING_ID case body and the SYN_REPORT branch.
m_tid = re.search(r'case ABS_MT_TRACKING_ID:(.*?)break;', s, re.S)
need(m_tid is not None, 'ABS_MT_TRACKING_ID case present')
if m_tid:
    body = m_tid.group(1)
    need('nuxel_fsm_feed' not in body, 'TRACKING_ID case does NOT feed the FSM')
    need('NUXEL_FSM_TOUCH_DOWN' not in body, 'TRACKING_ID case does NOT emit TOUCH_DOWN')
    need('touch_pending_down = 1' in body, 'TRACKING_ID>=0 sets pending-down')
    need('touch_pending_up = 1' in body, 'TRACKING_ID<0 sets pending-up')

m_syn = re.search(r'EV_SYN && e->code == SYN_REPORT && mt\.slot == 0\)(.*?)\n        \}', s, re.S)
need(m_syn is not None, 'SYN_REPORT branch present')
if m_syn:
    body = m_syn.group(1)
    need('NUXEL_FSM_TOUCH_DOWN' in body, 'SYN_REPORT branch emits TOUCH_DOWN')
    need('NUXEL_FSM_TOUCH_UP' in body, 'SYN_REPORT branch emits TOUCH_UP')
    need('NUXEL_FSM_TOUCH_MOVE' in body, 'SYN_REPORT branch emits TOUCH_MOVE')
    need('nuxel_fsm_feed' in body, 'SYN_REPORT branch feeds the FSM')

# The old defective pattern must not survive anywhere.
need(not re.search(r'case ABS_MT_TRACKING_ID:(?:(?!break;).)*nuxel_fsm_feed', s, re.S),
     'no feed call inside TRACKING_ID case (old defect absent)')

print('SELFTEST: %s (%d assertion(s), %d failed)' % ('PASS' if not fails else 'FAIL', total, len(fails)))
sys.exit(0 if not fails else 1)
