// Nuxel Vault encrypted archive tests (offline; WebCrypto only).
const A = require('../js/archive.js');
let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}
const PW = 'correct horse battery staple 63000';
const FAST = { iterations: A.MIN_ITERATIONS };
const ITEM = { type: 'login', title: 'Example', url: 'https://example.org', username: 'owner', password: 'p@ssw0rd', notes: 'local', tags: ['work'], favorite: true };
const ITEM2 = { type: 'note', title: 'Recovery words', notes: 'never in metadata', tags: [] };

(async function main() {
  console.log('vault archive');
  check('weak export passphrase refused', A.checkPassphrase('short').ok === false);
  check('reasonable export passphrase accepted', A.checkPassphrase(PW).ok === true);
  let doc = await A.create([ITEM, ITEM2], PW, FAST);
  check('archive schema/version', doc.schema === A.SCHEMA && doc.version === 1);
  check('archive has no plaintext items', !Object.prototype.hasOwnProperty.call(doc, 'items'));
  check('archive carries KDF parameters', doc.kdf.name === 'PBKDF2' && doc.kdf.iterations === A.MIN_ITERATIONS);
  check('archive carries IV and ciphertext', !!doc.cipher.iv && !!doc.cipher.ct);
  check('archive never contains the password', JSON.stringify(doc).indexOf(ITEM.password) === -1);
  let doc2 = await A.create([ITEM, ITEM2], PW, FAST);
  check('fresh salt and IV on every export', doc.kdf.salt !== doc2.kdf.salt && doc.cipher.iv !== doc2.cipher.iv);
  let opened = await A.unlock(doc, PW);
  check('right passphrase opens the archive', opened.length === 2 && opened[0].title === 'Example');
  let wrong = false;
  try { await A.unlock(doc, 'wrong passphrase 63000'); } catch (e) { wrong = true; }
  check('wrong passphrase fails authentication', wrong);
  let tampered = JSON.parse(JSON.stringify(doc));
  let ct = Buffer.from(tampered.cipher.ct, 'base64'); ct[0] ^= 1;
  tampered.cipher.ct = ct.toString('base64');
  let bad = false;
  try { await A.unlock(tampered, PW); } catch (e) { bad = true; }
  check('one flipped ciphertext bit is caught', bad);
  let weak = JSON.parse(JSON.stringify(doc)); weak.kdf.iterations = 1000;
  let weakRefused = false;
  try { await A.unlock(weak, PW); } catch (e) { weakRefused = true; }
  check('KDF downgrade is refused', weakRefused);
  let plain = { schema: A.SCHEMA, version: 1, kdf: doc.kdf, cipher: doc.cipher, items: [ITEM] };
  let plainRefused = false;
  try { await A.unlock(plain, PW); } catch (e) { plainRefused = true; }
  check('plaintext archive is refused', plainRefused);
  let text = A.encode(doc);
  check('export is JSON text', typeof text === 'string' && text.indexOf('nuxel-vault-archive') !== -1);
  check('importText accepts an encrypted archive', A.importText(text).schema === A.SCHEMA);
  let unknownRefused = false;
  try { A.validateItem(Object.assign({}, ITEM, { evil: true })); } catch (e) { unknownRefused = true; }
  check('unknown item fields are refused', unknownRefused);
  let largeRefused = false;
  try { A.validateItem(Object.assign({}, ITEM, { notes: 'x'.repeat(16385) })); } catch (e) { largeRefused = true; }
  check('oversized fields are refused', largeRefused);
  const fs = require('fs');
  const src = fs.readFileSync(require.resolve('../js/archive.js'), 'utf8');
  check('archive has no network path', !/fetch\(|XMLHttpRequest|WebSocket/.test(src));
  check('archive uses CSPRNG', src.indexOf('getRandomValues') !== -1);
  console.log(pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
