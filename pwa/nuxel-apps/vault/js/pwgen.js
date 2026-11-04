// Nuxel Vault — CSPRNG password generator.
//
// Uniform selection uses rejection sampling (no modulo bias), every requested
// character class is guaranteed at least once, and the final string is shuffled
// with a CSPRNG Fisher-Yates.  The non-cryptographic PRNG is never used for a secret.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.NuxelPwgen = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  var LOWER = 'abcdefghijklmnopqrstuvwxyz';
  var DIGITS = '0123456789';
  var SYMBOLS = '!#$%&*+-=?@^_';
  var AMBIGUOUS = 'Il1O0o';

  function rng() {
    var c = (typeof globalThis !== 'undefined' && globalThis.crypto) ||
            (typeof window !== 'undefined' && window.crypto) || null;
    if (!c || !c.getRandomValues) throw new Error('CSPRNG unavailable — refusing to generate a password');
    return c;
  }
  function randomInt(maxExclusive) {
    if (!(maxExclusive > 0)) throw new Error('invalid range');
    var c = rng();
    var limit = Math.floor(0x100000000 / maxExclusive) * maxExclusive;
    var buf = new Uint32Array(1);
    for (;;) {
      c.getRandomValues(buf);
      if (buf[0] < limit) return buf[0] % maxExclusive;
    }
  }
  function shuffle(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = randomInt(i + 1), t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    return arr;
  }
  function classes(opts) {
    var out = [];
    if (opts.uppercase !== false) out.push(UPPER);
    if (opts.lowercase !== false) out.push(LOWER);
    if (opts.digits !== false) out.push(DIGITS);
    if (opts.symbols !== false) out.push(SYMBOLS);
    if (!out.length) throw new Error('select at least one character class');
    if (opts.excludeAmbiguous) {
      out = out.map(function (set) {
        return set.split('').filter(function (ch) { return AMBIGUOUS.indexOf(ch) === -1; }).join('');
      }).filter(function (set) { return set.length > 0; });
    }
    return out;
  }
  function generate(opts) {
    opts = opts || {};
    var length = Math.max(8, Math.min(128, Number(opts.length) || 20));
    var sets = classes(opts);
    if (length < sets.length) throw new Error('length is too short for the selected classes');
    var all = sets.join('');
    var chars = [];
    sets.forEach(function (set) { chars.push(set[randomInt(set.length)]); });
    while (chars.length < length) chars.push(all[randomInt(all.length)]);
    return shuffle(chars).join('');
  }
  function strengthBits(password, opts) {
    opts = opts || {};
    var sets = classes(opts), alphabet = sets.join('').length || 1;
    return Math.round(String(password || '').length * (Math.log(alphabet) / Math.log(2)));
  }
  function strengthLabel(bits) {
    if (bits < 50) return 'weak';
    if (bits < 70) return 'fair';
    if (bits < 95) return 'strong';
    return 'very strong';
  }
  return { generate: generate, strengthBits: strengthBits, strengthLabel: strengthLabel };
}));
