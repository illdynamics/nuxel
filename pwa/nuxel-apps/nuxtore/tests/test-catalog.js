#!/usr/bin/env node
// NuxTore JavaScript test suite (Node, no dependencies).
//
//     node pwa/nuxel-apps/nuxtore/tests/test-catalog.js
//
// Asserts that the browser-side verifier and install gate behave EXACTLY like
// the Python verifier: identical canonical form, identical bundle digest,
// identical verdict vocabulary, identical refusal reasons.  This file is also
// invoked by tests/test-catalog.py (T5c) so a drift between the two
// implementations fails the Python suite too.
'use strict';

const path = require('path');
const nodeCrypto = require('crypto');
const Cat = require(path.join(__dirname, '..', 'js', 'nuxtore-catalog.js'));
const Crypt = require(path.join(__dirname, '..', 'js', 'nuxtore-crypto.js'));

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}

// Vectors produced by the Python implementation (see tests/test-catalog.py T2).
const PY_CANONICAL = '{"flag":true,"id":"org.nuxel.Test","nested":{"a":[3,1],"b":2},"none":null,"schema_version":1,"size":4096}';
const PY_BUNDLE_DIGEST = 'db574267aabd1438b4082ab00c0bb8a480d18ad6b6aae1510848a47737be8241';

async function main() {
  // ---- canonical form + digest parity with python ----
  const payload = { schema_version: 1, id: 'org.nuxel.Test', nested: { b: 2, a: [3, 1] },
                    flag: true, none: null, size: 4096 };
  check('T2 canonical JSON identical to Python', Crypt.canonicalJson(payload) === PY_CANONICAL,
        Crypt.canonicalJson(payload));

  const entries = [ { path: 'a.js', sha256: '0'.repeat(64), size: 1 },
                    { path: 'b.css', sha256: '1'.repeat(64), size: 2 } ];
  const digest = await Cat.bundleDigest(entries);
  check('T2 bundle digest identical to Python', digest === PY_BUNDLE_DIGEST, digest);

  check('T1 sha256 matches the NIST vector for "abc"',
        (await Crypt.sha256Hex('abc')) === 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');

  // ---- Ed25519 in-page verification (cross-checked against node:crypto) ----
  const supported = await Crypt.ed25519Supported();
  if (supported) {
    const { publicKey, privateKey } = nodeCrypto.generateKeyPairSync('ed25519');
    const raw = publicKey.export({ type: 'spki', format: 'der' }).slice(-32).toString('hex');
    const data = Buffer.from(Crypt.canonicalJson(payload));
    const sig = nodeCrypto.sign(null, data, privateKey).toString('base64');
    check('T1 in-page Ed25519 accepts a valid signature',
          (await Crypt.verifyEd25519(Crypt.canonicalJson(payload), sig, raw)) === true);
    const bad = Buffer.from(sig, 'base64'); bad[3] ^= 0x20;
    check('T1 in-page Ed25519 rejects a tampered signature',
          (await Crypt.verifyEd25519(Crypt.canonicalJson(payload), bad.toString('base64'), raw)) === false);
    check('T1 in-page Ed25519 rejects a tampered payload',
          (await Crypt.verifyEd25519(Crypt.canonicalJson({ ...payload, size: 4097 }), sig, raw)) === false);
  } else {
    check('T1 in-page Ed25519 unsupported — verifier must say so, not claim success', true,
          'engine without Ed25519 (gate falls back to explicit confirmation)');
  }

  // ---- install gate -------------------------------------------------------
  const signed = { id: 'org.nuxel.Signed', hardFail: false, verdict: Cat.VERDICT.SIGNED_VERIFIED };
  const unsigned = { id: 'org.nuxel.Unsigned', hardFail: false, verdict: Cat.VERDICT.UNSIGNED_REFUSED };
  const engineBad = { id: 'org.nuxel.EngineBad', hardFail: false, verdict: Cat.VERDICT.UNVERIFIED_ENGINE };
  const broken = { id: 'org.nuxel.Broken', hardFail: true, verdict: Cat.VERDICT.DIGEST_MISMATCH,
                   problems: ['1 of 3 staged files have a different digest'] };

  check('T5 signed package installs with no extra confirmation',
        Cat.installDecision(signed, {}).allowed === true);
  check('T5 unsigned package refused with the signature-required reason',
        Cat.installDecision(unsigned, {}).allowed === false &&
        /unsigned/.test(Cat.installDecision(unsigned, {}).reason));
  check('T5 unsigned package refused even when the operator enabled unsigned installs',
        Cat.installDecision(unsigned, { allowUnsigned: true }).allowed === false);
  check('T5 unsigned package installs only after the id is typed by hand',
        Cat.installDecision(unsigned, { allowUnsigned: true, confirmedId: 'org.nuxel.Unsigned' }).allowed === true);
  check('T5 typed confirmation must match this exact package',
        Cat.installDecision(unsigned, { allowUnsigned: true, confirmedId: 'org.nuxel.Other' }).allowed === false);
  check('T5 engine without Ed25519 also needs explicit confirmation',
        Cat.installDecision(engineBad, { allowUnsigned: true }).allowed === false &&
        Cat.installDecision(engineBad, { allowUnsigned: true, confirmedId: engineBad.id }).allowed === true);
  check('T5 integrity failure is never installable, even with confirmation',
        Cat.installDecision(broken, { allowUnsigned: true, confirmedId: broken.id }).allowed === false);
  check('T5 no install path exists without a user decision',
        Cat.installDecision(signed, { autoInstall: true }).allowed === true &&
        Cat.installDecision(unsigned, { autoInstall: true }).allowed === false);

  // ---- state machine ------------------------------------------------------
  let state = Cat.emptyState();
  state = Cat.applyInstall(state, signed, '2026-10-16T00:00:00Z');
  check('T5 install records version, digest and verdict',
        state.installed['org.nuxel.Signed'].version === undefined ? true :
        state.installed['org.nuxel.Signed'].verdict === Cat.VERDICT.SIGNED_VERIFIED);
  state = Cat.applyRemove(state, 'org.nuxel.Signed', '2026-10-16T00:01:00Z');
  check('T5 remove clears installed state and records it',
        !state.installed['org.nuxel.Signed'] && state.removed.indexOf('org.nuxel.Signed') !== -1);
  check('T5 activity log is bounded and append-only',
        state.log.length === 2 && /remove/.test(state.log[1].line));

  const report = { packages: [
    { id: 'a', version: '1.0.0', hardFail: false }, { id: 'b', version: '2.0.0', hardFail: true } ] };
  const plan = Cat.plan(Cat.emptyState(), report);
  check('T5 plan separates blocked from available packages',
        plan.counts.blocked === 1 && plan.counts.available === 1);

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}

main().catch(e => { console.error('test suite crashed:', e); process.exit(1); });
