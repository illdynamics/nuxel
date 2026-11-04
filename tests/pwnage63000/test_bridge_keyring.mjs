// PWNAGE-63000: the browser bridge must never mock a keyring operation.
// Run: node tests/pwnage63000/test_bridge_keyring.mjs
const writes = [];
globalThis.localStorage = {
  getItem: () => null,
  setItem: (k, v) => writes.push([k, v]),
  removeItem: () => {},
};
let fetchMode = 'offline';
let captured = null;
globalThis.fetch = async (url, opts) => {
  const u = String(url);
  if (fetchMode === 'offline') throw new Error('offline');
  if (u.endsWith('/bridge-version.json')) {
    return { ok: true, json: async () => ({ bridge_version: '1' }) };
  }
  if (u.endsWith('/auth/token')) {
    return { ok: true, json: async () => ({ token: 'per-app-token', ttl: 3600 }) };
  }
  if (u.endsWith('/rpc')) {
    captured = { url: u, opts };
    return { ok: true, json: async () => ({ result: { success: true, state: 'unlocked' } }) };
  }
  throw new Error('unexpected URL ' + u);
};

const mod = await import('../../pwa/nuxel-common/bridge.js');
const C = mod.NuxelBridgeClient;
let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name + (detail ? '  — ' + detail : '')); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}

const client = new C({ appId: 'org.nuxel.Vault', apiUrl: 'http://127.0.0.1:8080/api/v1' });
let r = await client.keyring('create-item', { item: { title: 'x', password: 'secret' } });
check('disconnected keyring save fails closed', r.success === false);
check('disconnected save reports unavailable', r.state === 'unavailable' && r.offline === true);
check('disconnected save never reports mock', r.mock !== true);
check('disconnected save did not write localStorage', writes.length === 0);
check('keyring never flips the client into mock mode', client.mockMode === false);

r = await client.call('keyring', 'status', {});
check('generic call routes keyring to fail-closed path', r.success === false && r.state === 'unavailable');

r = client._mockCall('keyring', 'create-item', {});
check('generic mock fallback cannot succeed for keyring', r.success === false && r.state === 'unavailable');

fetchMode = 'online';
const c2 = new C({ appId: 'org.nuxel.Vault', apiUrl: 'http://127.0.0.1:8080/api/v1' });
r = await c2.keyring('status', {});
check('online keyring call succeeds', r.success === true && r.state === 'unlocked');
check('online keyring call has no secret in localStorage', writes.length === 0);
const body = captured ? JSON.parse(captured.opts.body) : {};
check('body app_id is the client app id', body.app_id === 'org.nuxel.Vault');
check('body namespace is keyring', body.namespace === 'keyring');
check('Authorization carries the per-app token',
  captured && captured.opts.headers.Authorization === 'Bearer per-app-token');
check('keyring token is not persisted', !writes.some(([k]) => k === 'nuxel-bridge-token'));
console.log(pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
