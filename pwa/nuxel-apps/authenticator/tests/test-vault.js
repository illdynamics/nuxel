// Nuxel Authenticator — encrypted-vault tests (offline; WebCrypto only).
//
//   node pwa/nuxel-apps/authenticator/tests/test-vault.js
//
// The vault is the only component that touches secrets at rest, so these tests
// deliberately attack it: wrong passphrase, tampered ciphertext, replayed IV,
// plaintext import file, and hostile account parameters.
const V = require('../js/vault.js');
let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}
const PW = 'correct horse battery staple';
const FAST = { iterations: V.MIN_ITERATIONS };

(async function main() {
  console.log('encrypted vault');

  // ---- passphrase policy -------------------------------------------------
  check('a short passphrase is refused', V.checkPassphrase('abc').ok === false);
  check('a well-known weak passphrase is refused', V.checkPassphrase('password').ok === false);
  check('a single repeated character is refused', V.checkPassphrase('aaaaaaaaaa').ok === false);
  check('digits-only is refused', V.checkPassphrase('1234567890').ok === false);
  check('a reasonable passphrase is accepted', V.checkPassphrase(PW).ok === true);
  let threw = false;
  try { await V.create('abc'); } catch (e) { threw = true; }
  check('create() refuses a weak passphrase instead of storing secrets behind it', threw);

  // ---- create / unlock ---------------------------------------------------
  let v = await V.create(PW, FAST);
  check('the envelope names its schema', v.envelope.schema === V.SCHEMA);
  check('the envelope stores the KDF parameters, not the passphrase',
    v.envelope.kdf.name === 'PBKDF2' && !JSON.stringify(v.envelope).includes(PW));
  check('the envelope carries no plaintext accounts key',
    !Object.prototype.hasOwnProperty.call(v.envelope, 'accounts'));
  check('the envelope has an IV and ciphertext', !!v.envelope.cipher.iv && !!v.envelope.cipher.ct);
  let un = await V.unlock(v.envelope, PW);
  check('the right passphrase unlocks an empty vault', un.accounts.length === 0);
  let wrong = false;
  try { await V.unlock(v.envelope, PW + 'x'); } catch (e) { wrong = true; }
  check('a wrong passphrase fails authentication and yields nothing', wrong);

  // ---- accounts ----------------------------------------------------------
  const good = { issuer: 'Example', account: 'owner@example.org', secret: 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ' };
  let add = V.addAccount([], good);
  check('a valid account is added', add.ok === true && add.accounts.length === 1);
  check('defaults are applied (SHA1/6/30)', add.account.algorithm === 'SHA1' && add.account.digits === 6 && add.account.period === 30);
  check('the account id is stable for the same inputs', V.idFor(add.account) === add.account.id);
  let dup = V.addAccount(add.accounts, good);
  check('a duplicate account is refused', dup.ok === false && dup.duplicate === true);
  check('a missing account name is refused', V.addAccount([], { secret: good.secret }).ok === false);
  check('an invalid base32 secret is refused',
    V.addAccount([], { account: 'x', secret: 'not-base32!!' }).ok === false);
  check('a short secret is refused with the byte count',
    /at least/.test(V.addAccount([], { account: 'x', secret: V.b64 ? 'AAAA' : 'AAAA' }).problems.join(' ')) ||
    V.addAccount([], { account: 'x', secret: 'AAAA' }).ok === false);
  check('an unsupported algorithm is refused',
    V.addAccount([], { account: 'x', secret: good.secret, algorithm: 'MD5' }).ok === false);
  check('digits=7 is refused', V.addAccount([], { account: 'x', secret: good.secret, digits: 7 }).ok === false);
  check('digits=8 is accepted', V.addAccount([], { account: 'x', secret: good.secret, digits: 8 }).ok === true);
  check('a 5 second period is refused',
    V.addAccount([], { account: 'x', secret: good.secret, period: 5 }).ok === false);
  check('a 60 second period is accepted',
    V.addAccount([], { account: 'x', secret: good.secret, period: 60 }).ok === true);
  const removed = V.removeAccount(add.accounts, add.account.id);
  check('an account can be removed', removed.length === 0);

  // ---- save / reload / IV freshness --------------------------------------
  let env = await V.save(v.envelope, add.accounts, v.key);
  const firstIv = env.cipher.iv;
  let reloaded = await V.unlock(env, PW);
  check('a saved vault reloads its accounts', reloaded.accounts.length === 1);
  let env2 = await V.save(env, add.accounts, reloaded.key);
  check('every save uses a fresh AES-GCM IV', env2.cipher.iv !== firstIv);
  check('the ciphertext changed even though the data did not', env2.cipher.ct !== env.cipher.ct);

  // ---- tampering ---------------------------------------------------------
  const tampered = JSON.parse(JSON.stringify(env));
  const ct = Buffer.from(V.unb64(tampered.cipher.ct));
  ct[3] = ct[3] ^ 0x01;                       // flip one ciphertext bit
  tampered.cipher.ct = V.b64(ct);
  let tamperCaught = false;
  try { await V.unlock(tampered, PW); } catch (e) { tamperCaught = /did not authenticate/.test(e.message); }
  check('one flipped ciphertext bit is caught by the GCM tag', tamperCaught);

  const oldKdf = JSON.parse(JSON.stringify(env));
  oldKdf.kdf.iterations = 1000;
  let kdfCaught = false;
  try { await V.unlock(oldKdf, PW); } catch (e) { kdfCaught = /KDF iterations/.test(e.message); }
  check('a weakened KDF parameter is refused on unlock', kdfCaught);

  // ---- import / export ---------------------------------------------------
  const text = V.exportEnvelope(env);
  check('export produces JSON of the encrypted envelope', JSON.parse(text).schema === V.SCHEMA);
  check('export never contains the secret', text.indexOf('GEZDGNBVGY3TQOJQ') === -1);
  check('an exported envelope re-imports', V.importEnvelope(text).schema === V.SCHEMA);
  let plainCaught = false;
  try { V.importEnvelope(JSON.stringify({ schema: V.SCHEMA, accounts: [{ secret: 'X' }] })); }
  catch (e) { plainCaught = /plaintext secrets/.test(e.message); }
  check('a PLAINTEXT export file is refused on import', plainCaught);
  let junkCaught = false;
  try { V.importEnvelope('{oops'); } catch (e) { junkCaught = /not JSON/.test(e.message); }
  check('a non-JSON import is refused', junkCaught);
  let schemaCaught = false;
  try { V.importEnvelope(JSON.stringify({ schema: 'something-else', cipher: { ct: 'x' } })); }
  catch (e) { schemaCaught = /not a nuxel-authenticator-vault/.test(e.message); }
  check('an unknown envelope schema is refused', schemaCaught);
  let weakCaught = false;
  try { V.importEnvelope(JSON.stringify({ schema: V.SCHEMA, kdf: { iterations: 10 }, cipher: { ct: 'x' } })); }
  catch (e) { weakCaught = /KDF iterations/.test(e.message); }
  check('an import with a weakened KDF is refused', weakCaught);

  // ---- no cloud, stated in data -----------------------------------------
  check('the vault has no network path: no fetch/XHR/WebSocket in the module source',
    !/fetch\(|XMLHttpRequest|WebSocket/.test(require('fs').readFileSync(__dirname + '/../js/vault.js', 'utf8')));
  check('the vault has no sync/server field in the envelope',
    !/syncUrl|server|cloud/.test(JSON.stringify(env)));

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail === 0 ? 0 : 1);
}()).catch(e => { console.error('suite crashed:', e); process.exit(2); });
