// RFC 4226 (HOTP) and RFC 6238 (TOTP) over WebCrypto — no third-party code, no
// network, no account.  Verified against the RFC 6238 Appendix B vectors in
// tests/test-totp.js.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.NuxelTotp = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var ALGS = { SHA1: 'SHA-1', SHA256: 'SHA-256', SHA512: 'SHA-512' };
  var B32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

  function subtle() {
    var c = (typeof globalThis !== 'undefined' && globalThis.crypto) || null;
    if (!c || !c.subtle) throw new Error('WebCrypto unavailable — TOTP cannot be computed honestly');
    return c.subtle;
  }

  function base32Decode(input) {
    var s = String(input || '').toUpperCase().replace(/=+$/, '').replace(/[\s-]/g, '');
    if (!s.length) throw new Error('empty base32 secret');
    var bits = 0, value = 0, out = [];
    for (var i = 0; i < s.length; i++) {
      var idx = B32.indexOf(s.charAt(i));
      if (idx === -1) throw new Error('invalid base32 character "' + s.charAt(i) + '"');
      value = (value << 5) | idx;
      bits += 5;
      if (bits >= 8) {
        out.push((value >>> (bits - 8)) & 0xff);
        bits -= 8;
      }
    }
    return new Uint8Array(out);
  }

  function base32Encode(bytes) {
    var bits = 0, value = 0, out = '';
    for (var i = 0; i < bytes.length; i++) {
      value = (value << 8) | bytes[i];
      bits += 8;
      while (bits >= 5) {
        out += B32.charAt((value >>> (bits - 5)) & 31);
        bits -= 5;
      }
    }
    if (bits > 0) out += B32.charAt((value << (5 - bits)) & 31);
    while (out.length % 8) out += '=';
    return out;
  }

  function counterBytes(counter) {
    var buf = new Uint8Array(8);
    var v = BigInt(counter);
    for (var i = 7; i >= 0; i--) { buf[i] = Number(v & 0xffn); v >>= 8n; }
    return buf;
  }

  async function hmac(alg, keyBytes, msgBytes) {
    var st = subtle();
    var key = await st.importKey('raw', keyBytes, { name: 'HMAC', hash: ALGS[alg] || alg }, false, ['sign']);
    return new Uint8Array(await st.sign('HMAC', key, msgBytes));
  }

  function dynamicTruncate(mac, digits) {
    var off = mac[mac.length - 1] & 0x0f;
    var bin = ((mac[off] & 0x7f) << 24) | ((mac[off + 1] & 0xff) << 16) |
              ((mac[off + 2] & 0xff) << 8) | (mac[off + 3] & 0xff);
    var mod = Math.pow(10, digits);
    return String(bin % mod).padStart(digits, '0');
  }

  // RFC 4226 HOTP.
  async function hotp(secretBytes, counter, opts) {
    opts = opts || {};
    var alg = opts.algorithm || 'SHA1';
    var digits = opts.digits || 6;
    var mac = await hmac(alg, secretBytes, counterBytes(counter));
    return dynamicTruncate(mac, digits);
  }

  // RFC 6238 TOTP.  `at` is a unix time in seconds.
  async function totp(secretBytes, at, opts) {
    opts = opts || {};
    var period = opts.period || 30;
    var counter = Math.floor(Number(at) / period);
    return hotp(secretBytes, counter, opts);
  }

  // Verify a code within +/- window steps (default 1) — used for import checks
  // and for the "did I type the current code" self test.
  async function verify(secretBytes, code, at, opts) {
    opts = opts || {};
    var period = opts.period || 30;
    var window = opts.window === undefined ? 1 : opts.window;
    var digits = opts.digits || 6;
    for (var d = -window; d <= window; d++) {
      var c = await totp(secretBytes, Number(at) + d * period, opts);
      if (c === String(code).replace(/\s+/g, '')) return true;
    }
    return false;
  }

  function secondsRemaining(at, period) {
    period = period || 30;
    return period - (Math.floor(Number(at)) % period);
  }

  function progress(at, period) {
    period = period || 30;
    return secondsRemaining(at, period) / period;
  }

  // otpauth://totp/Issuer:account?secret=...&issuer=...&algorithm=SHA1&digits=6&period=30
  function parseOtpauth(uri) {
    var s = String(uri || '').trim();
    if (!/^otpauth:\/\/totp\//i.test(s)) throw new Error('only otpauth://totp/ URIs are supported');
    var rest = s.replace(/^otpauth:\/\/totp\//i, '');
    var qIdx = rest.indexOf('?');
    var label = decodeURIComponent(qIdx === -1 ? rest : rest.slice(0, qIdx));
    var params = {};
    if (qIdx !== -1) {
      rest.slice(qIdx + 1).split('&').forEach(function (kv) {
        var p = kv.split('=');
        if (p[0]) params[p[0].toLowerCase()] = decodeURIComponent((p[1] || '').replace(/\+/g, ' '));
      });
    }
    var issuer = params.issuer || (label.indexOf(':') !== -1 ? label.split(':')[0] : '');
    var account = label.indexOf(':') !== -1 ? label.split(':').slice(1).join(':') : label;
    if (!params.secret) throw new Error('otpauth URI has no secret parameter');
    return { issuer: issuer, account: account.trim(), secret: params.secret, algorithm: (params.algorithm || 'SHA1').toUpperCase(),
             digits: Number(params.digits || 6), period: Number(params.period || 30) };
  }

  function buildOtpauth(acct) {
    var label = (acct.issuer ? acct.issuer + ':' : '') + acct.account;
    var q = ['secret=' + encodeURIComponent(acct.secret)];
    if (acct.issuer) q.push('issuer=' + encodeURIComponent(acct.issuer));
    q.push('algorithm=' + (acct.algorithm || 'SHA1'));
    q.push('digits=' + (acct.digits || 6));
    q.push('period=' + (acct.period || 30));
    return 'otpauth://totp/' + encodeURIComponent(label) + '?' + q.join('&');
  }

  return { base32Decode: base32Decode, base32Encode: base32Encode, hotp: hotp, totp: totp,
           verify: verify, secondsRemaining: secondsRemaining, progress: progress,
           parseOtpauth: parseOtpauth, buildOtpauth: buildOtpauth, counterBytes: counterBytes,
           ALGS: ALGS };
}));
