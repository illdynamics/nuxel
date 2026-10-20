// A34 TOUCHDOWN — deterministic test of the status-bar Quick Settings gesture.
// The existing qs.js listened for `gesture:qs`, but nothing dispatched it.  This
// test loads the REAL status-bar.js in a minimal DOM shell and drives the same
// pointer events WebKitGTK produced for the owner's finger.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const SRC = path.join(__dirname, '../../../../pwa/nuxel-home/js/status-bar.js');

let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra || '')));
  if (!cond) failures++;
}
function makeEl(tag) {
  const listeners = {};
  const e = {
    tagName: tag, id: '', className: '', textContent: '', innerHTML: '',
    style: { setProperty(k, v) { this[k] = v; } }, dataset: {}, children: [], title: '', attrs: {},
    classList: { add() {}, remove() {}, toggle() { return false; }, contains() { return false; } },
    appendChild(c) { this.children.push(c); c.parentNode = this; return c; },
    replaceChildren(...children) { this.children = children; },
    removeChild(c) { this.children = this.children.filter((x) => x !== c); },
    setAttribute(k, v) { this.attrs[k] = v; },
    getAttribute(k) { return this.attrs[k]; },
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    removeEventListener() {},
    dispatch(t, ev) { (listeners[t] || []).forEach((f) => f(ev)); },
    contains() { return false; },
  };
  return e;
}
const bar = makeEl('div');
const ids = {};
for (const id of ['status-time', 'status-signal', 'status-wifi', 'status-battery', 'status-battery-pct']) ids[id] = makeEl('span');
ids['status-bar'] = bar;
const docListeners = {};
const dispatched = [];
const document = {
  readyState: 'complete',
  body: makeEl('body'),
  getElementById(id) { return ids[id] || null; },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  createElement(t) { return makeEl(t); },
  addEventListener(t, f) { (docListeners[t] = docListeners[t] || []).push(f); },
  removeEventListener() {},
  dispatchEvent(ev) { dispatched.push(ev.type); (docListeners[ev.type] || []).forEach((f) => f(ev)); return true; },
};
const window = {
  addEventListener() {}, removeEventListener() {},
  devicePixelRatio: 2, innerWidth: 360, innerHeight: 760,
};
const sandbox = {
  console: { log() {}, warn() {}, error() {} },
  document, window,
  CustomEvent: function (t, o) { this.type = t; Object.assign(this, o || {}); },
  setInterval() { return 0; }, clearInterval() {}, setTimeout() { return 0; }, clearTimeout() {},
  requestAnimationFrame(fn) { return 0; },
  localStorage: { getItem() { return null; }, setItem() {} },
  Promise,
};
sandbox.window = window;
sandbox.self = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(SRC, 'utf8') + '\nthis.StatusBar = StatusBar;', sandbox);
const sb = new sandbox.StatusBar();
check('StatusBar constructed', !!sb);
check('status-bar version is current beta', sb.constructor.VERSION === '0.6.3-beta', sb.constructor.VERSION);

// A real downward pull on the status bar opens QS exactly once.
bar.dispatch('pointerdown', { clientX: 100, clientY: 8, button: 0 });
bar.dispatch('pointermove', { clientX: 103, clientY: 50 });
check('vertical pull dispatches gesture:qs', dispatched.filter((x) => x === 'gesture:qs').length === 1,
      JSON.stringify(dispatched));
// Further motion in the same contact must not double-open.
bar.dispatch('pointermove', { clientX: 104, clientY: 80 });
bar.dispatch('pointerup', {});
check('one contact = one gesture', dispatched.filter((x) => x === 'gesture:qs').length === 1,
      JSON.stringify(dispatched));

// A short tap must not open it.
dispatched.length = 0;
bar.dispatch('pointerdown', { clientX: 100, clientY: 8, button: 0 });
bar.dispatch('pointermove', { clientX: 101, clientY: 20 });
bar.dispatch('pointerup', {});
check('short tap does not open QS', dispatched.filter((x) => x === 'gesture:qs').length === 0,
      JSON.stringify(dispatched));

// A diagonal drag that is not a pull-down must not open it.
dispatched.length = 0;
bar.dispatch('pointerdown', { clientX: 10, clientY: 8, button: 0 });
bar.dispatch('pointermove', { clientX: 300, clientY: 60 });
bar.dispatch('pointerup', {});
check('diagonal drag is rejected', dispatched.filter((x) => x === 'gesture:qs').length === 0,
      JSON.stringify(dispatched));

if (failures) process.exit(1);
console.log('PASS: Quick Settings pull-down gesture wired and single-fire');
