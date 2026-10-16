// Nuxel Authenticator — RFC 4226/6238 conformance tests (offline, WebCrypto only).
//
//   node pwa/nuxel-apps/authenticator/tests/test-totp-vectors.js
//
// These are the RFC's own vectors. If any of them fail, the app must not present
// codes as trustworthy — which is why the UI runs the same table as an in-app
// self test (AuthVault.selfTest()).
const Totp = require('../js/totp.js');
const V = require('../js/vault.js');
let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}

// RFC 4226 Appendix D — HOTP with the ASCII secret "12345678901234567890".
const HOTP_SECRET = Totp.base32Decode('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ');
const HOTP = ['755224', '287082', '359152', '969429', '338314', '254676', '287922', '162583', '399871', '520489'];

(async function main() {
  console.log('TOTP/HOTP conformance');
  for (let c = 0; c < HOTP.length; c++) {
    const got = await Totp.hotp(HOTP_SECRET, c, { digits: 6, algorithm: 'SHA1' });
    check('RFC 4226 HOTP counter ' + c, got === HOTP[c], got + ' vs ' + HOTP[c]);
  }

  // Base32 round trip.
  check('base32 encodes the RFC secret exactly',
    Totp.base32Encode(Totp.base32Decode('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ')) === 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ');
  check('base32 tolerates lower case and separators',
    Totp.base32Decode('gezd gnbv-gy3tqojq').length === 10);
  let threw = false;
  try { Totp.base32Decode('!!!!'); } catch (e) { threw = true; }
  check('base32 rejects an illegal character', threw);
  check('eight digits are supported',
    (await Totp.totp(HOTP_SECRET, 59, { digits: 8 })) === '94287082');

  // RFC 6238 Appendix B — the shipped self-test table, all 18 vectors.
  const self = await V.selfTest();
  check('every RFC 6238 vector in the shipped table passes', self.ok === true,
    self.results.length + ' vectors');
  check('the table covers all three hashes',
    new Set(V.RFC6238.map(v => v.alg)).size === 3);
  check('the table covers six timestamps',
    new Set(V.RFC6238.map(v => v.t)).size === 6);
  self.results.filter(r => !r.ok).forEach(r => check('vector ' + r.vector, false, r.got + ' vs ' + r.expected));

  // Non-standard but supported parameters.
  check('a 60 s period halves the counter rate',
    (await Totp.totp(HOTP_SECRET, 59, { digits: 6, period: 60 })) === (await Totp.totp(HOTP_SECRET, 0, { digits: 6, period: 60 })));
  check('SHA-256 and SHA-1 differ for the same secret and time',
    (await Totp.totp(HOTP_SECRET, 59, { digits: 8, algorithm: 'SHA256' })) !==
    (await Totp.totp(HOTP_SECRET, 59, { digits: 8, algorithm: 'SHA1' })));

  // verify()/window/pacing.
  const code = await Totp.totp(HOTP_SECRET, 1000, { digits: 6 });
  check('verify accepts the current code', await Totp.verify(HOTP_SECRET, code, 1000, { digits: 6 }) === true);
  check('verify accepts one step of clock skew',
    await Totp.verify(HOTP_SECRET, code, 1000 + 30, { digits: 6 }) === true);
  check('verify rejects a code two steps away by default',
    await Totp.verify(HOTP_SECRET, code, 1000 + 90, { digits: 6 }) === false);
  check('verify ignores spaces a user typed', await Totp.verify(HOTP_SECRET, code.slice(0, 3) + ' ' + code.slice(3), 1000, { digits: 6 }) === true);
  check('secondsRemaining counts down within the period', Totp.secondsRemaining(1000, 30) === 20, String(Totp.secondsRemaining(1000, 30)));
  check('progress is a fraction of the period', Math.abs(Totp.progress(1000, 30) - (20 / 30)) < 1e-9);

  // otpauth URIs (the only import format).
  const uri = 'otpauth://totp/Nuxel:owner%40example.org?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&issuer=Nuxel&algorithm=SHA256&digits=8&period=60';
  const parsed = Totp.parseOtpauth(uri);
  check('otpauth issuer is parsed', parsed.issuer === 'Nuxel');
  check('otpauth account is parsed and decoded', parsed.account === 'owner@example.org');
  check('otpauth algorithm/digits/period are parsed',
    parsed.algorithm === 'SHA256' && parsed.digits === 8 && parsed.period === 60);
  check('otpauth round-trips', Totp.parseOtpauth(Totp.buildOtpauth(parsed)).account === parsed.account);
  check('a hotp:// URI is refused', (function () { try { Totp.parseOtpauth('otpauth://hotp/x?secret=AB'); return false; } catch (e) { return true; } } )());
  check('a URI without a secret is refused', (function () { try { Totp.parseOtpauth('otpauth://totp/x'); return false; } catch (e) { return true; } } )());
  check('a non-otpauth URI is refused', (function () { try { Totp.parseOtpauth('https://example.org/x'); return false; } catch (e) { return true; } } )());

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail === 0 ? 0 : 1);
}()).catch(e => { console.error('suite crashed:', e); process.exit(2); });
