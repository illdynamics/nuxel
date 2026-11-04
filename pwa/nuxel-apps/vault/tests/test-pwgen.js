// Nuxel Vault password generator tests (offline; CSPRNG only).
const P = require('../js/pwgen.js');
let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}
const opts = { length: 24, uppercase: true, lowercase: true, digits: true, symbols: true, excludeAmbiguous: true };
const p1 = P.generate(opts), p2 = P.generate(opts);
check('requested length', p1.length === 24);
check('two calls differ', p1 !== p2);
check('has uppercase', /[A-Z]/.test(p1));
check('has lowercase', /[a-z]/.test(p1));
check('has digit', /[0-9]/.test(p1));
check('has symbol', /[!#$%&*+\-=?@^_]/.test(p1));
check('no ambiguous characters when excluded', !/[Il1O0o]/.test(p1));
let min = null, max = null;
for (let i = 0; i < 200; i++) {
  const p = P.generate({ length: 12, uppercase: false, lowercase: false, digits: true, symbols: false });
  const lo = p.split('').reduce((a, c) => Math.min(a, c.charCodeAt(0)), 999);
  const hi = p.split('').reduce((a, c) => Math.max(a, c.charCodeAt(0)), 0);
  min = min === null ? lo : Math.min(min, lo); max = max === null ? hi : Math.max(max, hi);
}
check('digits-only stays in 0-9', min >= 48 && max <= 57, min + '..' + max);
let none = false;
try { P.generate({ length: 12, uppercase: false, lowercase: false, digits: false, symbols: false }); } catch (e) { none = true; }
check('no class selected is refused', none);
check('strength estimate is numeric', typeof P.strengthBits(p1, opts) === 'number' && P.strengthBits(p1, opts) > 0);
const fs = require('fs');
const src = fs.readFileSync(require.resolve('../js/pwgen.js'), 'utf8');
check('generator never uses Math.random', src.indexOf('Math.random') === -1);
check('generator uses getRandomValues', src.indexOf('getRandomValues') !== -1);
console.log(pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
