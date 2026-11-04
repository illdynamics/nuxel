// Nuxel Vault — encrypted export/import archive.
//
// This is deliberately the same envelope discipline as the Authenticator vault:
// AES-256-GCM, PBKDF2-HMAC-SHA-256, a fresh 16-byte salt and 12-byte IV per
// export, and authenticated ciphertext.  It is NOT a new cipher or KDF.  A
// plaintext archive is refused, and a downgraded KDF is refused on import.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.NuxelVaultArchive = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var SCHEMA = 'nuxel-vault-archive';
  var VERSION = 1;
  var DEFAULT_ITERATIONS = 250000;
  var MIN_ITERATIONS = 210000;
  var MAX_BYTES = 8 * 1024 * 1024;
  var WEAK = ['password', '1234567890', 'qwertyuiop', 'letmein123', 'nuxel', 'vault', 'changeme'];

  function cryptoObj() {
    var c = (typeof globalThis !== 'undefined' && globalThis.crypto) ||
            (typeof window !== 'undefined' && window.crypto) || null;
    if (!c || !c.subtle) throw new Error('WebCrypto unavailable — refusing to export/import secrets');
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
      var bin = atob(String(text)), out = new Uint8Array(bin.length);
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
    var p = String(pass || ''), problems = [];
    if (p.length < 10) problems.push('must be at least 10 characters');
    if (p.length > 1024) problems.push('must be under 1024 characters');
    if (WEAK.indexOf(p.toLowerCase()) !== -1) problems.push('is a well-known weak passphrase');
    if (/^(.)\1+$/.test(p)) problems.push('is a single repeated character');
    if (/^\d+$/.test(p)) problems.push('is only digits');
    return { ok: problems.length === 0, problems: problems };
  }

  async function deriveKey(pass, salt, iterations) {
    var st = cryptoObj().subtle;
    var material = await st.importKey('raw', new TextEncoder().encode(String(pass)),
      'PBKDF2', false, ['deriveKey']);
    return st.deriveKey(
      { name: 'PBKDF2', salt: salt, iterations: iterations, hash: 'SHA-256' },
      material, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
  }

  function validateItem(raw) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error('archive contains an invalid item');
    var allowed = ['schema', 'type', 'title', 'url', 'username', 'password', 'notes', 'tags', 'favorite', 'created_at', 'updated_at', 'id'];
    Object.keys(raw).forEach(function (k) {
      if (allowed.indexOf(k) === -1) throw new Error('archive item has an unknown field');
    });
    if (raw.type !== 'login' && raw.type !== 'note') throw new Error('archive item type is invalid');
    var title = String(raw.title || '').trim();
    if (!title || title.length > 200) throw new Error('archive item title is invalid');
    var tags = Array.isArray(raw.tags) ? raw.tags : [];
    if (tags.length > 24 || tags.some(function (t) { return typeof t !== 'string' || t.length > 48; })) {
      throw new Error('archive item tags are invalid');
    }
    ['url', 'username', 'password', 'notes'].forEach(function (k) {
      if (raw[k] != null && typeof raw[k] !== 'string') throw new Error('archive item ' + k + ' is invalid');
    });
    if ((raw.password || '').length > 4096 || (raw.notes || '').length > 16384 ||
        (raw.username || '').length > 320 || (raw.url || '').length > 2048) {
      throw new Error('archive item field is too large');
    }
    return {
      schema: 'nuxel-vault-item-v1', type: raw.type, title: title,
      url: String(raw.url || ''), username: String(raw.username || ''),
      password: String(raw.password || ''), notes: String(raw.notes || ''),
      tags: tags.slice(0, 24), favorite: raw.favorite === true,
      created_at: String(raw.created_at || new Date().toISOString()),
      updated_at: String(raw.updated_at || new Date().toISOString())
    };
  }

  async function create(items, passphrase, opts) {
    opts = opts || {};
    var v = checkPassphrase(passphrase);
    if (!v.ok) throw new Error('export passphrase refused: ' + v.problems.join(', '));
    var list = (items || []).map(validateItem);
    var iterations = Math.max(MIN_ITERATIONS, Number(opts.iterations) || DEFAULT_ITERATIONS);
    var salt = randomBytes(16), iv = randomBytes(12);
    var key = await deriveKey(passphrase, salt, iterations);
    var payload = JSON.stringify({ schema: SCHEMA, version: VERSION, items: list });
    if (payload.length > MAX_BYTES) throw new Error('archive is too large');
    var ct = await cryptoObj().subtle.encrypt({ name: 'AES-GCM', iv: iv }, key,
      new TextEncoder().encode(payload));
    return {
      schema: SCHEMA, version: VERSION,
      kdf: { name: 'PBKDF2', hash: 'SHA-256', iterations: iterations, salt: b64(salt) },
      cipher: { name: 'AES-256-GCM', iv: b64(iv), ct: b64(new Uint8Array(ct)) },
      item_count: list.length,
      created_at: new Date().toISOString()
    };
  }

  function validateEnvelope(doc) {
    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) throw new Error('not a Nuxel Vault archive');
    if (Object.prototype.hasOwnProperty.call(doc, 'items')) {
      throw new Error('archive contains PLAINTEXT items — refused');
    }
    if (doc.schema !== SCHEMA) throw new Error('not a Nuxel Vault archive');
    if (doc.version !== VERSION) throw new Error('unsupported archive version');
    if (!doc.kdf || doc.kdf.name !== 'PBKDF2' || doc.kdf.hash !== 'SHA-256') {
      throw new Error('archive uses an unsupported KDF');
    }
    if (!Number.isInteger(doc.kdf.iterations) || doc.kdf.iterations < MIN_ITERATIONS) {
      throw new Error('archive KDF parameters were weakened — refused');
    }
    if (!doc.cipher || doc.cipher.name !== 'AES-256-GCM' || !doc.cipher.iv || !doc.cipher.ct) {
      throw new Error('archive cipher parameters are incomplete');
    }
    var salt, iv, ct;
    try { salt = unb64(doc.kdf.salt); iv = unb64(doc.cipher.iv); ct = unb64(doc.cipher.ct); }
    catch (e) { throw new Error('archive contains invalid base64'); }
    if (salt.length < 16 || iv.length !== 12 || ct.length < 16) throw new Error('archive crypto parameters are invalid');
    return { salt: salt, iv: iv, ct: ct };
  }

  async function unlock(doc, passphrase) {
    var p = validateEnvelope(doc);
    var key = await deriveKey(passphrase, p.salt, doc.kdf.iterations);
    var pt;
    try {
      pt = await cryptoObj().subtle.decrypt({ name: 'AES-GCM', iv: p.iv }, key, p.ct);
    } catch (e) {
      throw new Error('cannot open archive: the passphrase did not authenticate it (or it was modified)');
    }
    var parsed;
    try { parsed = JSON.parse(new TextDecoder().decode(pt)); } catch (e) { throw new Error('archive payload is not JSON'); }
    if (!parsed || parsed.schema !== SCHEMA || parsed.version !== VERSION || !Array.isArray(parsed.items)) {
      throw new Error('archive payload schema is invalid');
    }
    return parsed.items.map(validateItem);
  }

  function encode(doc) { return JSON.stringify(doc, null, 2) + '\n'; }

  function importText(text) {
    var doc;
    try { doc = JSON.parse(text); } catch (e) { throw new Error('import failed: not JSON'); }
    validateEnvelope(doc);
    return doc;
  }

  return {
    SCHEMA: SCHEMA, VERSION: VERSION, MIN_ITERATIONS: MIN_ITERATIONS,
    DEFAULT_ITERATIONS: DEFAULT_ITERATIONS,
    checkPassphrase: checkPassphrase, validateItem: validateItem,
    create: create, unlock: unlock, encode: encode, importText: importText
  };
}));
