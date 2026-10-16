// Nuxel Authenticator — encrypted vault (AES-256-GCM, PBKDF2-SHA-256).
//
// THE ENVELOPE IS THE ONLY THING THAT TOUCHES STORAGE.  There is no plaintext
// account list on disk, no cloud sync, no account and no network call of any
// kind: the secrets are decrypted in memory only while the vault is unlocked.
//
// Rules asserted by tests/test-vault.js:
//   1. a wrong passphrase fails the GCM tag check and yields NOTHING (it can
//      never return a partial or empty account list as if it succeeded);
//   2. a fresh IV is generated on every save — reusing an IV with GCM is a
//      catastrophic break, so a re-lock with unchanged data must still differ;
//   3. an import file containing plaintext accounts is REFUSED;
//   4. account validation rejects a secret that is not decodable base32, an
//      unsupported algorithm, digits outside 6..8 and a silly period;
//   5. the vault never reports that a TOTP code is "correct" for a service — it
//      can only say the code matches this device's clock and this secret.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./totp.js'));
  else root.AuthVault = factory(root.NuxelTotp);
}(typeof self !== 'undefined' ? self : this, function (Totp) {
  'use strict';

  var SCHEMA = 'nuxel-authenticator-vault';
  var VERSION = 1;
  var DEFAULT_ITERATIONS = 250000;
  var MIN_ITERATIONS = 100000;
  var ALGORITHMS = ['SHA1', 'SHA256', 'SHA512'];
  var MIN_SECRET_BYTES = 10;      // RFC 4226 recommends >= 128 bits; 10 bytes is the practical floor
  var WEAK = ['password', '12345678', 'qwertyui', 'letmein1', 'iloveyou', 'nuxel', 'authenticator'];

  function cryptoObj() {
    var c = (typeof globalThis !== 'undefined' && globalThis.crypto) ||
            (typeof window !== 'undefined' && window.crypto) || null;
    if (!c || !c.subtle) throw new Error('WebCrypto unavailable — the vault refuses to store secrets unencrypted');
    return c;
  }

  function b64(bytes) {
    var u = new Uint8Array(bytes), s = '';
    for (var i = 0; i < u.length; i++) s += String.fromCharCode(u[i]);
    if (typeof btoa === 'function') return btoa(s);
    return Buffer.from(u).toString('base64');
  }
  function unb64(text) {
    if (typeof atob === 'function') {
      var bin = atob(String(text));
      var out = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
      return out;
    }
    return new Uint8Array(Buffer.from(String(text), 'base64'));
  }
  function randomBytes(n) {
    var o = new Uint8Array(n);
    cryptoObj().getRandomValues(o);
    return o;
  }

  function checkPassphrase(pass) {
    var problems = [];
    var p = String(pass || '');
    if (p.length < 8) problems.push('must be at least 8 characters');
    if (p.length > 1024) problems.push('must be under 1024 characters');
    if (WEAK.indexOf(p.toLowerCase()) !== -1) problems.push('is a well-known weak passphrase');
    if (/^(.)\1+$/.test(p)) problems.push('is a single repeated character');
    if (/^\d+$/.test(p)) problems.push('is only digits');
    return { ok: problems.length === 0, problems: problems };
  }

  async function deriveKey(pass, salt, iterations) {
    var st = cryptoObj().subtle;
    var material = await st.importKey('raw', new TextEncoder().encode(String(pass)), 'PBKDF2', false, ['deriveKey']);
    return st.deriveKey(
      { name: 'PBKDF2', salt: salt, iterations: iterations, hash: 'SHA-256' },
      material, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
  }

  async function create(pass, opts) {
    opts = opts || {};
    var v = checkPassphrase(pass);
    if (!v.ok) throw new Error('passphrase refused: ' + v.problems.join(', '));
    var iterations = Math.max(MIN_ITERATIONS, opts.iterations || DEFAULT_ITERATIONS);
    var salt = randomBytes(16);
    var key = await deriveKey(pass, salt, iterations);
    var env = {
      schema: SCHEMA, version: VERSION,
      kdf: { name: 'PBKDF2', hash: 'SHA-256', iterations: iterations, salt: b64(salt) },
      cipher: { name: 'AES-256-GCM', iv: null, ct: null },
      created: new Date().toISOString()
    };
    var saved = await save(env, [], key);
    return { envelope: saved, key: key, accounts: [] };
  }

  // Serialise + encrypt.  Always a fresh 12-byte IV; GCM IV reuse is fatal.
  async function save(env, accounts, key) {
    var iv = randomBytes(12);
    var payload = JSON.stringify({ accounts: accounts || [] });
    var ct = await cryptoObj().subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, new TextEncoder().encode(payload));
    var out = JSON.parse(JSON.stringify(env));
    out.cipher = { name: 'AES-256-GCM', iv: b64(iv), ct: b64(new Uint8Array(ct)) };
    out.updated = new Date().toISOString();
    if (env.cipher && env.cipher.iv && out.cipher.iv === env.cipher.iv) {
      throw new Error('refusing to write: the AES-GCM IV was reused');
    }
    return out;
  }

  async function unlock(env, pass) {
    if (!env || env.schema !== SCHEMA) throw new Error('not a Nuxel authenticator vault');
    if (Object.prototype.hasOwnProperty.call(env, 'accounts')) {
      throw new Error('this file contains PLAINTEXT accounts — refused (import only encrypted vaults)');
    }
    if (!env.kdf || !env.cipher || !env.cipher.iv || !env.cipher.ct) throw new Error('vault envelope is incomplete');
    if (env.kdf.iterations < MIN_ITERATIONS) {
      throw new Error('vault uses only ' + env.kdf.iterations + ' KDF iterations (minimum ' + MIN_ITERATIONS + ')');
    }
    var key = await deriveKey(pass, unb64(env.kdf.salt), env.kdf.iterations);
    var pt;
    try {
      pt = await cryptoObj().subtle.decrypt({ name: 'AES-GCM', iv: unb64(env.cipher.iv) }, key, unb64(env.cipher.ct));
    } catch (e) {
      // GCM authentication failed: either the passphrase or the data is wrong.
      // We cannot tell which, so we claim neither.
      throw new Error('cannot unlock: the passphrase did not authenticate this vault (or the file was modified)');
    }
    var doc = JSON.parse(new TextDecoder().decode(pt));
    return { key: key, accounts: Array.isArray(doc.accounts) ? doc.accounts : [] };
  }

  /* ---------------- account model ---------------- */

  function validateAccount(a) {
    var problems = [];
    var acct = String(a && a.account || '').trim();
    if (!acct) problems.push('account name is required');
    if (acct.length > 200) problems.push('account name is too long');
    var secret = String(a && a.secret || '').replace(/[\s-]/g, '');
    if (!secret) problems.push('secret is required');
    var bytes = null;
    try { bytes = Totp.base32Decode(secret); } catch (e) { problems.push('secret is not valid base32 (' + e.message + ')'); }
    if (bytes && bytes.length < MIN_SECRET_BYTES) problems.push('secret is only ' + bytes.length + ' bytes; at least ' + MIN_SECRET_BYTES + ' is required');
    var alg = String(a && a.algorithm || 'SHA1').toUpperCase();
    if (ALGORITHMS.indexOf(alg) === -1) problems.push('unsupported algorithm ' + alg);
    var digits = Number(a && a.digits || 6);
    if ([6, 8].indexOf(digits) === -1) problems.push('digits must be 6 or 8');
    var period = Number(a && a.period || 30);
    if (!(period >= 15 && period <= 120)) problems.push('period must be between 15 and 120 seconds');
    return { ok: problems.length === 0, problems: problems, algorithm: alg, digits: digits, period: period, secret: secret };
  }

  function idFor(a) {
    var s = (a.issuer || '') + '|' + a.account + '|' + String(a.secret).slice(0, 6);
    var h = 5381;
    for (var i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0;
    return 'acct-' + h.toString(36);
  }

  function addAccount(accounts, raw) {
    var v = validateAccount(raw);
    if (!v.ok) return { ok: false, problems: v.problems };
    var acct = {
      id: idFor(raw), issuer: String(raw.issuer || '').trim(), account: String(raw.account).trim(),
      secret: v.secret, algorithm: v.algorithm, digits: v.digits, period: v.period,
      added: raw.added || new Date().toISOString(), notes: raw.notes || null
    };
    var dup = (accounts || []).filter(function (x) {
      return x.account === acct.account && (x.issuer || '') === acct.issuer && x.secret === acct.secret;
    })[0];
    if (dup) return { ok: false, problems: ['this account is already in the vault'], duplicate: true };
    return { ok: true, accounts: (accounts || []).concat([acct]), account: acct };
  }

  function removeAccount(accounts, id) {
    return (accounts || []).filter(function (a) { return a.id !== id; });
  }

  function updateAccount(accounts, id, patch) {
    return (accounts || []).map(function (a) { return a.id === id ? Object.assign({}, a, patch, { id: id }) : a; });
  }

  /* ---------------- import / export ---------------- */

  function exportEnvelope(env) {
    // Export is ALWAYS the encrypted envelope.  There is no "export plaintext"
    // button: a plaintext export is how secrets end up in a chat message.
    return JSON.stringify(env, null, 2) + '\n';
  }

  function importEnvelope(text) {
    var doc;
    try { doc = JSON.parse(text); } catch (e) { throw new Error('import failed: not JSON'); }
    if (!doc || doc.schema !== SCHEMA) throw new Error('import failed: not a ' + SCHEMA + ' envelope');
    if (Object.prototype.hasOwnProperty.call(doc, 'accounts') || Object.prototype.hasOwnProperty.call(doc, 'secrets')) {
      throw new Error('import refused: the file contains plaintext secrets — only encrypted vaults may be imported');
    }
    if (!doc.cipher || !doc.cipher.ct) throw new Error('import failed: envelope has no ciphertext');
    if (doc.kdf && doc.kdf.iterations < MIN_ITERATIONS) throw new Error('import refused: KDF iterations below the minimum');
    return doc;
  }

  // The in-app self test: RFC 6238 Appendix B vectors, computed with the same
  // code path the UI uses.  A user can run it without a network and without any
  // third-party service — and if it fails the app says the codes cannot be trusted.
  var RFC6238 = [
    { alg: 'SHA1', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', t: 59, digits: 8, expect: '94287082' },
    { alg: 'SHA256', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZA', t: 59, digits: 8, expect: '46119246' },
    { alg: 'SHA512', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNA', t: 59, digits: 8, expect: '90693936' },
    { alg: 'SHA1', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', t: 1111111109, digits: 8, expect: '07081804' },
    { alg: 'SHA256', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZA', t: 1111111109, digits: 8, expect: '68084774' },
    { alg: 'SHA512', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNA', t: 1111111109, digits: 8, expect: '25091201' },
    { alg: 'SHA1', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', t: 1111111111, digits: 8, expect: '14050471' },
    { alg: 'SHA256', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZA', t: 1111111111, digits: 8, expect: '67062674' },
    { alg: 'SHA512', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNA', t: 1111111111, digits: 8, expect: '99943326' },
    { alg: 'SHA1', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', t: 1234567890, digits: 8, expect: '89005924' },
    { alg: 'SHA256', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZA', t: 1234567890, digits: 8, expect: '91819424' },
    { alg: 'SHA512', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNA', t: 1234567890, digits: 8, expect: '93441116' },
    { alg: 'SHA1', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', t: 2000000000, digits: 8, expect: '69279037' },
    { alg: 'SHA256', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZA', t: 2000000000, digits: 8, expect: '90698825' },
    { alg: 'SHA512', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNA', t: 2000000000, digits: 8, expect: '38618901' },
    { alg: 'SHA1', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', t: 20000000000, digits: 8, expect: '65353130' },
    { alg: 'SHA256', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZA', t: 20000000000, digits: 8, expect: '77737706' },
    { alg: 'SHA512', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQGEZDGNA', t: 20000000000, digits: 8, expect: '47863826' }
  ];

  async function selfTest() {
    var results = [];
    for (var i = 0; i < RFC6238.length; i++) {
      var v = RFC6238[i];
      var got = await Totp.totp(Totp.base32Decode(v.secret), v.t, { algorithm: v.alg, digits: v.digits, period: 30 });
      results.push({ vector: v.alg + ' t=' + v.t, expected: v.expect, got: got, ok: got === v.expect });
    }
    return { ok: results.every(function (r) { return r.ok; }), results: results };
  }

  return {
    SCHEMA: SCHEMA, VERSION: VERSION, DEFAULT_ITERATIONS: DEFAULT_ITERATIONS, MIN_ITERATIONS: MIN_ITERATIONS,
    ALGORITHMS: ALGORITHMS, RFC6238: RFC6238,
    checkPassphrase: checkPassphrase, create: create, save: save, unlock: unlock,
    validateAccount: validateAccount, idFor: idFor, addAccount: addAccount,
    removeAccount: removeAccount, updateAccount: updateAccount,
    exportEnvelope: exportEnvelope, importEnvelope: importEnvelope, selfTest: selfTest,
    b64: b64, unb64: unb64
  };
}));
