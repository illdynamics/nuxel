// PWNAGE-30000 shared theme + haptics client unit tests (node sandbox).
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '../../..');

let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}
function load(file, extra) {
  const store = {};
  const sandbox = Object.assign({
    console: { log() {}, warn() {} },
    localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
    dispatchEvent() {}, addEventListener() {},
    CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
    document: { documentElement: { setAttribute() {} }, querySelector() { return null; } },
    Date: Date,
  }, extra || {});
  sandbox.window = sandbox;
  sandbox.__store = store;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(file, 'utf8'), sandbox);
  return sandbox;
}

// theme: default + invalid fallback + persistence
const t = load(path.join(ROOT, 'pwa/nuxel-common/theme.js'));
check('theme default is nuxel-grove', t.NuxelTheme.current().id === 'nuxel-grove');
check('theme exposes both themes', t.NuxelTheme.THEMES.length === 2);
t.__store[t.NuxelTheme.KEY] = 'test-theme';
check('theme persist/read round-trips', t.NuxelTheme.current().id === 'test-theme');
t.__store[t.NuxelTheme.KEY] = 'not-a-real-theme';
check('invalid stored theme falls back to default', t.NuxelTheme.current().id === 'nuxel-grove');
check('apply rejects unknown theme ids by falling back', t.NuxelTheme.apply('bogus').id === 'nuxel-grove');

// haptics: enabled default, rate limiting, disable, alarm path through bridge
const calls = [];
const fakeBridge = { call: (ns, verb, params) => { calls.push({ ns, verb, params }); return Promise.resolve({ success: true, dispatched: true }); } };
const h = load(path.join(ROOT, 'pwa/nuxel-common/haptics.js'), { NuxelBridge: fakeBridge });
Promise.resolve(h.NuxelHaptics.tap()).then(() => {
  check('haptics dispatches tap through bridge', calls.length === 1 && calls[0].verb === 'pulse' && calls[0].params.kind === 'tap');
  return h.NuxelHaptics.tap();
}).then(() => {
  check('haptics rate-limits a second tap within cooldown', calls.length === 1);
  h.NuxelHaptics.update({ enabled: false });
  return h.NuxelHaptics.navigation();
}).then(() => {
  check('disabled haptics make no request', calls.length === 1);
  process.exit(failures ? 1 : 0);
}).catch(e => { console.error(e); process.exit(2); });
