#!/usr/bin/env node
// Root & Sudo offline tests.   node pwa/nuxel-apps/rootcontrol/tests/test-privilege-model.js
//
// These assertions are the point of the app: it must describe the REAL mechanism
// on Linux 4.14 and it must never claim unbypassable root protection.
'use strict';
const fs = require('fs');
const path = require('path');
const PM = require(path.join(__dirname, '..', 'js', 'privilege-model.js'));

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail !== undefined ? '  — ' + detail : '')); }
}

const snap = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '..', '_shared', 'samples', 'sys-snapshot.json'), 'utf8'));
const f = snap.files;

// ---- sudoers parsing (real text from the device snapshot) ----
const sudoers = PM.parseSudoers(f['/etc/sudoers']);
check('sudoers: Defaults lines are recorded', sudoers.defaults.length === 2, sudoers.defaults.length);
check('sudoers: the #includedir directive is found', sudoers.includeDirs.length === 1 &&
      sudoers.includeDirs[0] === '/etc/sudoers.d', JSON.stringify(sudoers.includeDirs));
check('sudoers: root and %wheel full-sudo rules are parsed', sudoers.userSpecs.length === 2,
      JSON.stringify(sudoers.userSpecs.map(s => s.user)));
check('sudoers: a bare ALL command list is recognised as full sudo',
      sudoers.wildcards.length === 2 && sudoers.userSpecs.every(s => s.allCommands));

const dropin = PM.parseSudoers(f['/etc/sudoers.d/50-nuxel-installer']);
check('sudoers.d: the installer drop-in is NOPASSWD and limited to two commands',
      dropin.nopasswd.length === 1 && /stage-update/.test(dropin.userSpecs[0].commands) &&
      !/^\s*ALL\s*$/.test(dropin.userSpecs[0].commands.trim()));

const combined = PM.parseSudoers(f['/etc/sudoers'] + '\n' + f['/etc/sudoers.d/50-nuxel-installer']);
const summary = PM.sudoSummary(combined);
check('sudo summary: one passwordless rule in total', summary.passwordless === 1, summary.passwordless);
check('sudo summary: full-sudo accounts are named explicitly (root, %wheel)',
      summary.fullSudoAccounts.join(',') === 'root,%wheel', summary.fullSudoAccounts.join(','));
check('sudo summary: no passwordless rule grants ALL', summary.dangerous === 0, summary.dangerous);

const wheel = PM.parseGroupMembers(f['/etc/group'], 'wheel');
check('group: wheel membership is read from /etc/group', wheel.join(',') === 'nuxel', wheel.join(','));

// ---- mechanism on this kernel ----
const mech = PM.mechanism({ kernelRelease: '4.14.253-g2b2e5a0a1b2c',
                            lsm: f['/sys/kernel/security/lsm'].trim(), seccomp: true });
check('mechanism: DAC and capabilities are the primary confinement', mech.dac.enabled && mech.capabilities.enabled);
check('mechanism: seccomp is reported as active when the unit installs a filter', mech.seccomp.enabled);
check('mechanism: Landlock is NOT claimed on 4.14', mech.landlock.enabled === false && /5.13/.test(mech.landlock.detail));
check('mechanism: AppArmor and SELinux are not claimed', !mech.apparmor.enabled && !mech.selinux.enabled);
check('mechanism: overall MAC is reported as absent', mech.macEnabled === false, mech.lsmRaw);

// ---- claims: complete, classed, evidence-backed, never absolute ----
const claims = PM.enforcementClaims(mech);
check('claims: every claim names an attacker class', claims.every(c => !!PM.ATTACKER_CLASSES[c.attackerClass]));
check('claims: every claim has evidence and a limitation',
      claims.every(c => c.evidence.length > 40 && c.limitation.length > 20));
check('claims: every status is in the allowed vocabulary',
      claims.every(c => PM.CLAIM_STATUS.indexOf(c.status) !== -1));
check('claims: MAC confinement is marked not-enforced', 
      claims.filter(c => c.id === 'mac')[0].status === 'not-enforced');
check('claims: the service sandbox is honestly marked partial, not enforced',
      claims.filter(c => c.id === 'service-sandbox')[0].status === 'partial');
check('claims: root and physical access are out of scope',
      claims.filter(c => c.id === 'root')[0].status === 'out-of-scope' &&
      claims.filter(c => c.id === 'physical')[0].status === 'out-of-scope');
check('claims: the root claim says in words that no unbypassable protection is claimed',
      /does NOT claim unbypassable root protection/.test(claims.filter(c => c.id === 'root')[0].limitation));

const violations = PM.auditClaims(claims.map(c => c.claim + ' ' + c.evidence + ' ' + c.limitation))
  .concat(PM.auditClaims(PM.PRIVILEGED_OPS.map(o => o.op + ' ' + o.needs + ' ' + o.note)));
check('claims: no shipped claim or privileged-op note uses a forbidden absolute phrase',
      violations.length === 0, JSON.stringify(violations));
check('audit: a forbidden phrase is detected when it really appears',
      PM.auditClaims(['this protection is unbypassable']).length === 1);

// ---- privileged operations table ----
check('privileged ops: raw block device writes are listed as requiring CAP_SYS_RAWIO and being forbidden',
      PM.PRIVILEGED_OPS.some(o => /raw block device/.test(o.op) && /CAP_SYS_RAWIO/.test(o.needs) &&
                                  /forbids all direct writes/.test(o.via)));
check('privileged ops: clock setting does not claim to be done by the app',
      /never sets the clock itself/.test(PM.PRIVILEGED_OPS.filter(o => /clock/.test(o.op))[0].note));

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
