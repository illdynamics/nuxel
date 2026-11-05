// PWNAGE-80000: centralized zoom policy is default-deny and only cancels
// multi-touch/browser zoom paths, never one-finger app input.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log('  PASS ' + name); }
  else { fail++; console.log('  FAIL ' + name); }
}

const listeners = {};
const document = {
  querySelector: () => null,
  getElementById: () => null,
  addEventListener: (name, fn) => { listeners[name] = fn; },
};
const window = { document, location: { origin: 'http://127.0.0.1:8000' } };
const sandbox = {
  window, document, console,
  fetch: () => Promise.resolve({ ok: false }),
  CustomEvent: function (name) { this.type = name; },
};
sandbox.globalThis = sandbox;
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', '..', 'nuxel-common', 'zoom-policy.js'), 'utf8'), sandbox);
const policy = window.NuxelZoomPolicy;
check('policy module is published', !!policy);
check('default is deny for an unknown app', policy.allowed('org.nuxel.Calendar') === false);
check('policy declares defaultDeny', policy.defaultDeny === true);

policy.setPolicy({ default: 'deny', apps: { 'org.nuxel.Calendar': { zoom: true } } });
check('explicit app permission is honoured', policy.allowed('org.nuxel.Calendar') === true);
check('another app stays denied', policy.allowed('org.nuxel.Maps') === false);

let prevented = 0, stopped = 0;
const two = { cancelable: true, touches: [{}, {}], preventDefault: () => prevented++, stopPropagation: () => stopped++ };
listeners.touchstart(two);
check('two-finger touch is cancelled', prevented === 1 && stopped === 1);

prevented = stopped = 0;
const one = { cancelable: true, touches: [{}], preventDefault: () => prevented++, stopPropagation: () => stopped++ };
listeners.touchstart(one);
check('one-finger touch passes through', prevented === 0 && stopped === 0);

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
