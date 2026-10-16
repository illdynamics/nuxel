#!/usr/bin/env node
// Safe Cleanup offline tests.   node pwa/nuxel-apps/cleanup/tests/test-cleanup-plan.js
//
// Proves the three safety properties the briQ demands: an exact dry-run byte
// count, an allowlist that cannot be escaped, and a hard confirmation gate.
'use strict';
const fs = require('fs');
const path = require('path');
const C = require(path.join(__dirname, '..', 'js', 'cleanup-plan.js'));

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail !== undefined ? '  — ' + detail : '')); }
}

const scan = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'js', 'sample-scan.json'), 'utf8'));
const plan = C.plan(scan);

const expected = [41287680, 204800, 3145728, 8765440, 134217728, 2621440,
                  52428800, 15728640].reduce((a, b) => a + b, 0);
check('dry run reports the exact reclaimable bytes', plan.totalBytes === expected,
      plan.totalBytes + ' vs ' + expected);
check('dry run reports an exact file count', plan.totalFiles === 312 + 4 + 7 + 41 + 18 + 12 + 618 + 214,
      plan.totalFiles);
check('dry run is flagged as a dry run', plan.dryRun === true);
check('reclaimable bytes are human formatted from the same number',
      plan.reclaimable === C.formatBytes(expected), plan.reclaimable);

const skippedPaths = plan.skipped.map(s => s.path);
check('user Downloads are never part of the plan', skippedPaths.indexOf('/home/nuxel/Downloads') !== -1);
check('persistent state /var/lib/nuxel is never part of the plan',
      skippedPaths.indexOf('/var/lib/nuxel') !== -1);
check('the RPM database is never part of the plan', skippedPaths.indexOf('/var/lib/dnf') !== -1);
check('the Trash directory is left to the user', skippedPaths.indexOf('/home/nuxel/.local/share/Trash') !== -1);
check('every skipped path carries a reason', plan.skipped.every(s => typeof s.reason === 'string' && s.reason.length > 10));
check('the plan can only contain allowlisted paths',
      plan.entries.every(e => !!C.isAllowed(e.path)));
check('plan entries are sorted largest first', plan.entries[0].path === '/var/log/journal');
check('entries carry their real consequence, not a generic warning',
      plan.entries.every(e => e.consequence && e.consequence.length > 10));

// gate
check('gate refuses an empty confirmation', C.gate('', plan).ok === false);
check('gate refuses a near-miss phrase', C.gate('delete cache please', plan).ok === false);
check('gate refuses the phrase in the wrong case-neutral form only when wrong',
      C.gate('delete cache', plan).ok === true);
check('gate accepts the exact phrase (case-insensitive, trimmed)', C.gate('  DELETE CACHE ', plan).ok === true);
check('gate refuses when there is nothing to clean', C.gate('DELETE CACHE', C.plan({ entries: [] })).ok === false);

// delete application is pure + allowlist-bound
const results = [
  { path: '/var/log/journal', ok: true, bytes: 134217728 },
  { path: '/home/nuxel/Downloads', ok: true, bytes: 734003200 },
  { path: '/var/cache/nuxel', ok: false, error: 'permission denied' }
];
const summary = C.applyDelete(plan, results);
check('delete refuses an out-of-allowlist path even if the caller says it succeeded',
      summary.failed.some(f => f.path === '/home/nuxel/Downloads' && /outside the allowlist/.test(f.error)));
check('delete counts only allowlisted successes', summary.freedBytes === 134217728, summary.freedBytes);
check('delete reports real per-path failures', summary.failed.some(f => /permission denied/.test(f.error)));
check('applyDelete does not mutate the plan', plan.entries.length === 8 && plan.dryRun === true);

// allowlist audit
const problems = C.auditAllowlist();
check('allowlist audit finds no over-broad or protected-prefix entries', problems.length === 0,
      problems.join('; '));
check('allowlist never contains a raw device or partition path',
      C.ALLOWLIST.every(a => !/^\/dev\//.test(a.path) && !/mmcblk|by-name/.test(a.path)));
check('the never-touch list names the direct-write prohibition',
      C.NEVER_TOUCH.some(n => /raw partition|block device/i.test(n.reason)));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
