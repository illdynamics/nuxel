#!/usr/bin/env python3
"""A84: the launcher's security client (security-lock.js) contract.

Covers the live defect measured on the S10+ after the first A84 deploy: in
swipe mode every swipe reached the unlock threshold and was then rejected with
`credential-required-on-lockscreen`.  The cause was the client:
  * it routed `/security/status` through the shared bridge client, whose failure
    path returns FABRICATED mock data, and
  * `verifyUnlock()` treated any answer without a boolean `locked` as "locked".
So a transient miss looked like a real locked state.

The fix: security RPCs go straight to the root bridge (same pinned header as
the shared client), and a non-answer is reported as `lock-provider-unavailable`
(fail closed, honest reason) instead of "credential required".
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)[:300]))
    if not cond:
        fails.append(name)


LOCK = (ROOT / 'pwa/nuxel-home/js/security-lock.js').read_text()
HTML = (ROOT / 'pwa/nuxel-home/index.html').read_text()

check('security client is versioned a85 (swipe release)', "var VERSION = 'a85';" in LOCK)
check('security RPCs go directly to the root bridge',
      "127.0.0.1:8080/api/v1/rpc" in LOCK and 'function call(ns, verb, params) { return direct(ns, verb, params); }' in LOCK)
check('the shared (mock-fallback) client is not used for security',
      'global.NuxelBridge' not in LOCK and 'bridge().call' not in LOCK)
check('requests carry the pinned bridge-version header',
      "'X-Nuxel-Bridge-Version': bridgeVersion()" in LOCK)
check('a failed HTTP RPC is returned as a failure, never as data',
      "return { success: false, error: 'HTTP ' + res.status" in LOCK)
check('a status without a boolean locked is not treated as locked',
      "if (typeof st.locked !== 'boolean')" in LOCK and
      "security status did not report a lock state" in LOCK)
# The actual unlock decision must come from the bridge's boolean, not a truthy object.
body = LOCK[LOCK.index('async function verifyUnlock(opts)'):]
body = body[:body.index('\n  }')]
check('verifyUnlock unlocks only on an explicit locked === false',
      'st.locked === false' in body and 'st.locked' in body)
check('the index cache-busts the new security client', 'security-lock.js?v=a85' in HTML)

# 2026-11-14 second live defect: a provider-side lock (Settings, console) left
# the launcher showing the desktop while the provider said "locked", so the next
# swipe was judged by a lock screen that was not up.
APP = (ROOT / 'pwa/nuxel-home/js/app.js').read_text()
check('the launcher reconciles a provider-side lock into the overlay',
      '_reconcileLockFromProvider' in APP and "_lock('provider-authority')" in APP)
check('boot settles the overlay against the provider',
      '_startLockReconcile();\n        /* A84: the lock overlay is the boot state.' in APP)
check('the reconciliation runs while unlocked (poll)',
      '_startLockReconcile' in APP and 'setInterval' in APP[APP.index('_startLockReconcile'):APP.index('_startLockReconcile') + 400])
check('reconciliation ignores a non-answer (never paints on undefined)',
      "typeof st.locked !== 'boolean'" in APP)

print()
if fails:
    print('A84 SECURITY CLIENT: %d FAILURE(S): %s' % (len(fails), ', '.join(fails)))
    sys.exit(1)
print('A84 SECURITY CLIENT: ALL PASS')
