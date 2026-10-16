// NuxTore cryptography helpers (offline, WebCrypto, no third-party code).
//
// Used by the NuxTore verifier for two independent checks:
//   1. SHA-256 of every staged file + of the bundle file list (content addressing)
//   2. Ed25519 verification of each package's signature
//
// Ed25519 in the WebCrypto API is *newer* than SHA-256.  When the engine does
// not implement it we do NOT pretend the signature was checked: the verifier
// returns null and the catalog marks those packages "unverified (engine cannot
// verify Ed25519)", which the install gate treats as not-installable unless the
// operator explicitly confirms.  The authoritative offline check is
// tools/nuxtore-verify.py; a passing in-page check never upgrades a package to
// "verified" on its own.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.NuxToreCrypto = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function subtle() {
    var c = (typeof globalThis !== 'undefined' && globalThis.crypto) || null;
    return c && c.subtle ? c.subtle : null;
  }

  function bytesOf(input) {
    if (input instanceof Uint8Array) return input;
    if (typeof input === 'string') return new TextEncoder().encode(input);
    if (input instanceof ArrayBuffer) return new Uint8Array(input);
    throw new TypeError('sha256Hex expects a string, Uint8Array or ArrayBuffer');
  }

  function bytesToHex(buf) {
    var b = new Uint8Array(buf), out = '';
    for (var i = 0; i < b.length; i++) out += (b[i] < 16 ? '0' : '') + b[i].toString(16);
    return out;
  }

  function hexToBytes(hex) {
    var clean = String(hex).replace(/\s+/g, '');
    var out = new Uint8Array(clean.length / 2);
    for (var i = 0; i < out.length; i++) out[i] = parseInt(clean.substr(i * 2, 2), 16);
    return out;
  }

  function bytesToB64(buf) {
    var b = new Uint8Array(buf), s = '';
    for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return (typeof btoa === 'function') ? btoa(s) : Buffer.from(b).toString('base64');
  }

  function b64ToBytes(b64) {
    var s = String(b64).replace(/\s+/g, '');
    if (typeof atob === 'function') {
      var bin = atob(s), out = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
      return out;
    }
    return new Uint8Array(Buffer.from(s, 'base64'));
  }

  async function sha256Hex(input) {
    var st = subtle();
    if (!st) return null;                        // no crypto: caller must say so
    var d = await st.digest('SHA-256', bytesOf(input));
    return bytesToHex(d);
  }

  var _ed25519 = null;
  async function ed25519Supported() {
    if (_ed25519 !== null) return _ed25519;
    var st = subtle();
    if (!st) { _ed25519 = false; return false; }
    try {
      // A one-byte round trip is the only portable capability probe.
      var kp = await st.generateKey({ name: 'Ed25519' }, true, ['sign', 'verify']);
      var sig = await st.sign({ name: 'Ed25519' }, kp.privateKey, new Uint8Array([7]));
      _ed25519 = await st.verify({ name: 'Ed25519' }, kp.publicKey, sig, new Uint8Array([7]));
    } catch (e) {
      _ed25519 = false;
    }
    return _ed25519;
  }

  // Returns true / false / null ("this engine cannot verify Ed25519").
  async function verifyEd25519(payload, sigB64, pubHex) {
    if (!(await ed25519Supported())) return null;
    var st = subtle();
    try {
      var key = await st.importKey('raw', hexToBytes(pubHex), { name: 'Ed25519' }, false, ['verify']);
      return await st.verify({ name: 'Ed25519' }, key, b64ToBytes(sigB64),
                             typeof payload === 'string' ? new TextEncoder().encode(payload) : payload);
    } catch (e) {
      return false;
    }
  }

  // Canonical JSON: recursively sorted keys, compact separators.  Byte-identical
  // to the Python side's json.dumps(sort_keys=True, separators=(",",":"),
  // ensure_ascii=True) because every signature-covered string in the catalog
  // schema is printable ASCII (enforced by the schema and by verify-catalog.py).
  function canonicalJson(obj) {
    return JSON.stringify(sortDeep(obj));
  }

  function sortDeep(v) {
    if (Array.isArray(v)) return v.map(sortDeep);
    if (v && typeof v === 'object') {
      var out = {};
      Object.keys(v).sort().forEach(function (k) { out[k] = sortDeep(v[k]); });
      return out;
    }
    return v;
  }

  return {
    sha256Hex: sha256Hex,
    ed25519Supported: ed25519Supported,
    verifyEd25519: verifyEd25519,
    canonicalJson: canonicalJson,
    bytesToHex: bytesToHex,
    hexToBytes: hexToBytes,
    bytesToB64: bytesToB64,
    b64ToBytes: b64ToBytes
  };
}));
